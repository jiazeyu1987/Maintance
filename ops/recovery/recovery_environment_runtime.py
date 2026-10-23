"""Native local Linux/Docker executor. Never chooses another host or image.

Only dedicated resources labelled with the current target and operation are
created. Failures retain those resources. There is deliberately no cleanup,
automatic pull, remote transport, source-material retrieval or source restart.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

from recovery_environment_contract import (EnvironmentFailure, atomic_json, canonical, decode,
    digest, exact, pin_file, read_bytes, read_pin, require, safe_path, utc_now, verify_large_pin)


SUPERVISED_GROUP_ENV = "RECOVERY_ENVIRONMENT_SUPERVISED_GROUP"


# This selected Linux model retains direct-child ownership until signal/reap.
from recovery_environment_supervisor import (OwnedChildSupervisor, SupervisionFailure,
                                             prepare_local_supervision)


class CommandRunner:
    def __init__(self, evidence_root, deadline, guard):
        self.root = safe_path(str(evidence_root), directory=True)
        self.deadline = deadline
        self.authority_guard = guard
        self.pins = []
        self.last_exit = None
        self.sequence = 0
        self.effects = {}
        self.operation_proof_confirmed = False
        self.admission_valid_until = None

    def guard(self):
        self.remaining()
        self.authority_guard()
        self.remaining()

    def confirm_effects(self, sequences):
        """Called only after native identity/readback validates these effects."""
        self.guard()
        for sequence in sequences:
            require(self.effects.get(sequence) == "UNCONFIRMED", "EFFECT_CONFIRMATION_WITHOUT_DISPATCH")
            self.effects[sequence] = "CONFIRMED"

    def unconfirmed_effects(self):
        return any(value == "UNCONFIRMED" for value in self.effects.values()) or (
            not self.operation_proof_confirmed and any(value == "CONFIRMED" for value in self.effects.values()))

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, "DEADLINE_EXCEEDED")
        return remaining

    def run(self, argv, *, mutation=False, stdin=None, pass_fds=(), environment_bindings=None, failure_observer=None):
        self.guard()
        self.remaining()
        self.sequence += 1
        record_path = self.root / f"invocation-{self.sequence:04}.json"
        record = {"schemaVersion": "RecoveryEnvironmentInvocation/v1", "sequence": self.sequence,
                  "argvSha256": digest(argv), "mutation": mutation, "pid": None,
                  "startedAt": utc_now(), "finishedAt": None, "actualExitCode": None,
                  "state": "TERMINAL_UNKNOWN", "stdoutBytes": 0, "stdoutSha256": None,
                  "stderrBytes": 0, "stderrSha256": None, "dispatchState": "NOT_STARTED"}
        # Intention precedes Popen: an interrupted system call is never zero effect.
        atomic_json(record_path, record)
        process = None
        group = None
        effect_failure_proven = False
        output = error = b""
        try:
            bindings = {} if environment_bindings is None else environment_bindings
            require(type(bindings) is dict and set(bindings).issubset({"RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN"})
                    and all(type(value) is str and value and "\x00" not in value for value in bindings.values()),
                    "EXECUTOR_ENVIRONMENT_BINDING_INVALID")
            prepare_local_supervision()
            # Intent persistence and supervision may have consumed the same
            # shortened proof budget. No dispatch is recorded before this gate.
            self.guard()
            record["dispatchState"] = "ATTEMPTING_LOCAL_SPAWN"
            if mutation:
                self.effects[self.sequence] = "UNCONFIRMED"
            environment = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C", "LANG": "C",
                     "PYTHONUTF8": "1", **({SUPERVISED_GROUP_ENV: "v1"} if os.name == "posix" else {}),
                     **bindings}
            if os.name == "posix":
                process = OwnedChildSupervisor(argv, env=environment, stdin=stdin, pass_fds=pass_fds)
                group = process
                process.spawn()
                record["supervisorPid"] = process.supervisor_pid
                record["supervisionModel"] = "linux-owned-child-subreaper-v1"
                process.start(min(5, self.remaining()), guard=self.guard, deadline=self.deadline)
            else:
                process = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
            record["pid"] = process.pid
            record["dispatchState"] = "LOCAL_PROCESS_STARTED"
            atomic_json(record_path, record)
            pending_input = stdin
            while True:
                try:
                    output, error = process.communicate(pending_input, timeout=min(0.25, self.remaining()))
                    break
                except subprocess.TimeoutExpired:
                    pending_input = None
                    self.guard()
                    self.remaining()
            record["actualExitCode"] = process.returncode
            self.last_exit = process.returncode
            if group is not None:
                require(not group.members(), "LOCAL_TASK_CHILDREN_STILL_RUNNING")
            record["localTaskTreeState"] = "TERMINATED"
            require(len(output) <= 16 * 1024 * 1024 and len(error) <= 1024 * 1024, "COMMAND_OUTPUT_LIMIT")
            if failure_observer is not None and process.returncode != 0:
                observed = failure_observer(output, record)
                record["mechanismFailurePin"] = observed["evidencePin"]
                record["localProcessState"] = "TERMINATED"
                effect_failure_proven = observed["unknown"] is False
                raise EnvironmentFailure(observed["code"], unknown=observed["unknown"])
            require(process.returncode == 0, "EXECUTOR_NONZERO_EXIT")
            # Warnings cannot be swallowed; they can describe partially applied operations.
            require(not error, "EXECUTOR_STDERR_PRESENT")
            record["state"] = "SUCCEEDED"
            self.guard()
            return output
        except BaseException as failure:
            if isinstance(failure, SupervisionFailure):
                failure = EnvironmentFailure(failure.code, unknown=failure.unknown)
            # A local CLI exit proves no daemon/HTTP effect state. Only the
            # selected, validated observer may establish a known effect failure.
            unknown = (isinstance(failure, EnvironmentFailure) and failure.unknown) or (
                mutation and process is not None and not effect_failure_proven and
                getattr(process, "worker_dispatched", True) is not False)
            code = failure.code if isinstance(failure, EnvironmentFailure) else (
                "EXECUTOR_INTERRUPTED" if isinstance(failure, KeyboardInterrupt) else "EXECUTOR_EXECUTION_OR_IO_FAILED")
            if process is not None:
                try:
                    if group is not None and process.process is not None:
                        output, error = group.terminate(process)
                    elif group is not None:
                        require(isinstance(failure, EnvironmentFailure) and not failure.unknown,
                                "LOCAL_SPAWN_UNPROVEN")
                    else:
                        if process.poll() is None:
                            process.kill()
                        output, error = process.communicate(timeout=5)
                        require(os.name != "posix", "LOCAL_TASK_GROUP_IDENTITY_UNPROVEN")
                    record["localTaskTreeState"] = "TERMINATED"
                except BaseException as termination_failure:
                    unknown, code = True, "LOCAL_TASK_TREE_TERMINATION_UNPROVEN"
                    record["localTaskTreeState"] = "TERMINATION_UNPROVEN"
                    record["localTerminationFailureType"] = type(termination_failure).__name__
                    record["localTerminationFailureCode"] = getattr(termination_failure, "code", None)
                record["pid"] = process.pid
                if group is not None and group.worker_dispatched is False:
                    record["dispatchState"] = "NOT_STARTED"
                    if record.get("localTaskTreeState") == "TERMINATED":
                        unknown = isinstance(failure, EnvironmentFailure) and failure.unknown
                elif group is not None and group.worker_dispatched is True:
                    record["dispatchState"] = "LOCAL_PROCESS_STARTED"
                elif group is not None:
                    record["dispatchState"] = "LOCAL_SPAWN_UNPROVEN"
                record["actualExitCode"] = process.returncode
                self.last_exit = process.returncode
                if group is not None and group.terminal is not None and group.terminal["unknown"]:
                    unknown = True
                    if record.get("localTaskTreeState") == "TERMINATED":
                        code = group.terminal["failureCode"]
            elif record["dispatchState"] == "ATTEMPTING_LOCAL_SPAWN" and not isinstance(
                    failure, (FileNotFoundError, PermissionError, ValueError, TypeError)):
                # Interrupted/failed process creation has no observed PID; it is
                # not affirmative native evidence that no local child was born.
                unknown = True
                record["dispatchState"] = "LOCAL_SPAWN_UNPROVEN"
            else:
                record["dispatchState"] = "NOT_STARTED"
            record["effectState"] = ("TERMINAL_UNPROVEN" if unknown else
                                     "PROVEN_FAILURE" if effect_failure_proven else
                                     "NO_MUTATION_DISPATCHED" if process is None or
                                     getattr(process, "worker_dispatched", True) is False else "READ_ONLY_LOCAL_FAILURE")
            if mutation and not unknown:
                self.effects[self.sequence] = "PROVEN_FAILURE" if effect_failure_proven else "NOT_DISPATCHED"
            record["state"] = "TERMINAL_UNKNOWN" if unknown else "FAILED_RETAINED"
            record["failureCode"] = code
            raise EnvironmentFailure(code, unknown=unknown) from None
        finally:
            record.update(finishedAt=utc_now(), stdoutBytes=len(output), stderrBytes=len(error),
                          stdoutSha256=hashlib.sha256(output).hexdigest(),
                          stderrSha256=hashlib.sha256(error).hexdigest())
            record["localProcessState"] = ("START_UNPROVEN" if record["dispatchState"] == "LOCAL_SPAWN_UNPROVEN" else
                                           "NOT_STARTED" if process is None or record["dispatchState"] == "NOT_STARTED" else
                                           "TERMINATED" if record["actualExitCode"] is not None else
                                           "TERMINATION_UNPROVEN")
            if group is not None:
                record["localTaskGroupId"] = group.pid
                record["localTaskProcesses"] = group.proof(record.get("localTaskTreeState") == "TERMINATED")
                record["supervisorTerminal"] = group.terminal
                record["actualSupervisorExitCode"] = None if group.process is None else group.process.returncode
                group.close()
            # Raw stdout/stderr can contain inspect Env and secrets. Preserve
            # safe original observations, exit and hashes, never those bytes.
            persistence_stage = "WRITE"
            try:
                atomic_json(record_path, record)
                persistence_stage = "PIN"
                self.pins.append(pin_file(record_path))
            except BaseException as persistence_failure:
                # A receipt failure cannot revoke uncertainty already established
                # by the selected producer or an unconfirmed local termination.
                original_state, original_code = record["state"], record.get("failureCode")
                unknown = (original_state == "TERMINAL_UNKNOWN"
                           or (process is not None and record["actualExitCode"] is None)
                           or (mutation and original_state == "SUCCEEDED"))
                code = original_code if original_state == "TERMINAL_UNKNOWN" and original_code else (
                    "INVOCATION_TERMINAL_" + persistence_stage + "_FAILED")
                fault = {"schemaVersion": "RecoveryEnvironmentInvocationPersistenceFailure/v1",
                         "invocationPath": str(record_path), "stage": persistence_stage,
                         "persistenceFailureType": type(persistence_failure).__name__,
                         "originalState": original_state, "originalFailureCode": original_code,
                         "state": "TERMINAL_UNKNOWN" if unknown else "FAILED_RETAINED",
                         "failureCode": code, "receipt": record}
                try:
                    fault_path = self.root / f"invocation-persistence-failure-{self.sequence:04}.json"
                    atomic_json(fault_path, fault)
                    self.pins.append(pin_file(fault_path))
                except BaseException:
                    # Existing originals and the operation's actual exit remain;
                    # failed fault recording is never reported as completion.
                    if original_state != "TERMINAL_UNKNOWN" or not original_code:
                        code = "INVOCATION_TERMINAL_EVIDENCE_NOT_PERSISTED"
                raise EnvironmentFailure(code, unknown=unknown) from None


@contextmanager
def exclusive_lock(path):
    path = safe_path(str(path), exists=False)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    locked = False
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_nlink == 1, "LOCK_FILE_INVALID")
        if os.name == "posix":
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise EnvironmentFailure("TARGET_ALREADY_EXECUTING") from None
        else:
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\x00")
                os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                raise EnvironmentFailure("TARGET_ALREADY_EXECUTING") from None
        locked = True
        yield fd
    finally:
        if locked:
            if os.name == "posix":
                fcntl.flock(fd, fcntl.LOCK_UN)
            else:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        os.close(fd)


def ensure_material_path(path, config):
    resolved = safe_path(path)
    roots = [safe_path(root, directory=True) for root in config["materialRoots"]]
    require(any(resolved.is_relative_to(root) for root in roots), "MATERIAL_NOT_IN_INDEPENDENT_CUSTODY")
    source = read_pin(config["sourceScopePin"])
    require(all(not resolved.is_relative_to(Path(root)) for root in source["materialPaths"]),
            "SOURCE_MATERIAL_PATH_REJECTED")
    return resolved


def service_labels(config, operation_id):
    return {"intruoyi.recovery.target": config["targetId"], "intruoyi.recovery.operation": operation_id}


def sanitize_inspect(item):
    """Keep the observed runtime identity without serializing secret Env."""
    return {"id": item["Id"], "name": item["Name"], "imageId": item["Image"],
            "labels": item["Config"]["Labels"], "envSha256": digest(item["Config"]["Env"]),
            "commandSha256": digest([item["Path"], item["Args"]]),
            "hostConfigSha256": digest(item["HostConfig"]), "mounts": item["Mounts"],
            "networks": item["NetworkSettings"]["Networks"], "ports": item["NetworkSettings"]["Ports"],
            "state": item["State"], "restartCount": item["RestartCount"]}


def capacity_observation(temporary_path, data_path, temporary_bytes, data_bytes):
    """Account for simultaneous peaks on the actual underlying filesystems."""
    requirements = {}
    paths = {}
    for label, path, required in (("temporary", temporary_path, temporary_bytes), ("data", data_path, data_bytes)):
        resolved = safe_path(str(path), directory=True)
        identity = resolved.stat().st_dev
        free = shutil.disk_usage(resolved).free
        requirements.setdefault(identity, {"filesystemDevice": identity, "requiredBytes": 0, "freeBytes": free, "paths": []})
        group = requirements[identity]
        group["requiredBytes"] += required
        group["freeBytes"] = min(group["freeBytes"], free)
        group["paths"].append(str(resolved))
        paths[label] = {"path": str(resolved), "filesystemDevice": identity, "freeBytes": free, "requiredBytes": required}
    require(all(group["freeBytes"] >= group["requiredBytes"] for group in requirements.values()),
            "TARGET_SPACE_INSUFFICIENT")
    return {"paths": paths, "filesystems": list(requirements.values())}


class NativeDocker:
    def __init__(self, config, policy, runner, operation_id):
        self.config, self.policy, self.runner = config, policy, runner
        self.operation_id = operation_id
        self.labels = service_labels(config, operation_id)
        self.identities = {}
        self.image_labels = {}
        self.image_records = {record["role"]: record for record in map(read_pin, config["imagePins"])}

    def native_preflight(self):
        require(os.name == "posix" and hasattr(os, "setns") and hasattr(os, "geteuid") and
                os.geteuid() == 0, "NATIVE_LINUX_ROOT_WITH_SETNS_REQUIRED")
        for key in ("dockerPin", "pythonPin", "iptablesPin"):
            ensure_material_path(self.config[key]["path"], self.config)
            verify_large_pin(self.config[key], self.runner.guard)
        identity = read_pin(self.config["targetIdentityPin"])
        machine = read_bytes("/etc/machine-id").decode("ascii").strip()
        require(machine == identity["machineId"], "TARGET_MACHINE_ID_MISMATCH")
        info = decode(self.docker(["info", "--format", "{{json .}}"]))
        version = decode(self.docker(["version", "--format", "{{json .Server}}"]))
        require(info["ID"] == identity["dockerEngineId"] and version["Version"] == self.policy["dockerServerVersion"]
                and version["Arch"] == self.policy["architecture"] and info["OSType"] == "linux",
                "DOCKER_RUNTIME_ID_OR_VERSION_MISMATCH")
        require(not info.get("Swarm", {}).get("LocalNodeState") == "active", "SWARM_TARGET_REJECTED")
        source = read_pin(self.config["sourceScopePin"])
        capacity = capacity_observation(self.config["privateRoot"], info["DockerRootDir"],
            self.policy["requiredTemporaryBytes"], self.policy["requiredDataBytes"])
        memory = int(read_bytes("/proc/meminfo").decode("ascii").split("MemAvailable:", 1)[1].split()[0]) * 1024
        require(memory >= self.policy["requiredMemoryBytes"], "TARGET_MEMORY_INSUFFICIENT")
        return {"machineId": machine, "dockerEngineId": info["ID"], "dockerVersion": version["Version"],
                "architecture": version["Arch"], "hostArchitecture": info["Architecture"],
                "temporaryFreeBytes": capacity["paths"]["temporary"]["freeBytes"],
                "dataFreeBytes": capacity["paths"]["data"]["freeBytes"], "capacity": capacity, "availableMemoryBytes": memory,
                "sourceScopePin": self.config["sourceScopePin"], "sourceMachineId": source["machineId"]}

    def docker(self, args, *, mutation=False, pass_fds=()):
        # A single explicitly selected local daemon. No ambient Docker context.
        verify_large_pin(self.config["dockerPin"], self.runner.guard)
        return self.runner.run([self.config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock", *args],
                               mutation=mutation, pass_fds=pass_fds)

    def inspect(self, container_id):
        require(re.fullmatch("[0-9a-f]{64}", container_id), "CONTAINER_ID_INVALID")
        items = decode(self.docker(["inspect", container_id]))
        require(type(items) is list and len(items) == 1 and items[0]["Id"] == container_id, "CONTAINER_ID_MISMATCH")
        return items[0]

    def inventory_absent(self):
        names = {service["name"] for service in self.config["services"]}
        source = read_pin(self.config["sourceScopePin"])
        require(not names.intersection(source["containerNames"]) and self.config["network"]["name"] not in
                source["networkNames"], "SOURCE_RESOURCE_OVERLAP")
        containers = self.docker(["ps", "-a", "--format", "{{json .}}"])
        for line in containers.splitlines():
            require(decode(line)["Names"] not in names, "TARGET_CONTAINER_ALREADY_EXISTS")
        networks = self.docker(["network", "ls", "--format", "{{json .}}"])
        for line in networks.splitlines():
            require(decode(line)["Name"] != self.config["network"]["name"], "TARGET_NETWORK_ALREADY_EXISTS")
        volumes = self.docker(["volume", "ls", "--format", "{{json .}}"])
        approved = self.volume_names()
        require(not approved.intersection(source["volumeNames"]), "SOURCE_VOLUME_OVERLAP")
        for line in volumes.splitlines():
            require(decode(line)["Name"] not in approved, "TARGET_VOLUME_ALREADY_EXISTS")

    def volume_names(self):
        return {mount["volume"] for service in self.config["services"] for mount in service["mounts"]}

    def prepare_images(self):
        identities = []
        for pin in self.config["imagePins"]:
            record = read_pin(pin)
            ensure_material_path(record["archivePin"]["path"], self.config)
            verify_large_pin(record["archivePin"], self.runner.guard)
            # Always consume the approved offline archive; never pull a tag.
            with safe_path(record["archivePin"]["path"]).open("rb") as archive:
                info_before = os.fstat(archive.fileno())
                loaded_sha = hashlib.sha256()
                loaded_bytes = 0
                while chunk := archive.read(1024 * 1024):
                    self.runner.guard()
                    loaded_bytes += len(chunk)
                    loaded_sha.update(chunk)
                require(loaded_bytes == record["archivePin"]["bytes"] and loaded_sha.hexdigest() == record["archivePin"]["sha256"],
                        "OPENED_ARCHIVE_PIN_MISMATCH")
                archive.seek(0)
                effect = self.runner.sequence + 1
                self.docker(["image", "load", "--input", f"/proc/self/fd/{archive.fileno()}"], mutation=True,
                            pass_fds=(archive.fileno(),))
                info_after = os.fstat(archive.fileno())
                require((info_before.st_ino, info_before.st_size, info_before.st_mtime_ns, info_before.st_ctime_ns) ==
                        (info_after.st_ino, info_after.st_size, info_after.st_mtime_ns, info_after.st_ctime_ns), "LOADED_ARCHIVE_CHANGED")
            items = decode(self.docker(["image", "inspect", record["imageId"]]))
            require(len(items) == 1 and items[0]["Id"] == record["imageId"] and
                    items[0]["Architecture"] == record["architecture"] and items[0]["Os"] == "linux",
                    "LOADED_IMAGE_IDENTITY_MISMATCH")
            identities.append({"imagePin": pin, "imageId": record["imageId"], "role": record["role"],
                               "architecture": items[0]["Architecture"]})
            self.image_labels[record["role"]] = items[0]["Config"]["Labels"] or {}
            self.runner.confirm_effects([effect])
        return identities

    def label_args(self):
        return [part for key, value in self.labels.items() for part in ("--label", f"{key}={value}")]

    def create_network(self):
        network = self.config["network"]
        effect = self.runner.sequence + 1
        network_id = self.docker(["network", "create", "--internal", "--ipv6=false", "--driver", "bridge",
            "--subnet", network["subnet"], "--gateway", network["gateway"], "--opt",
            "com.docker.network.bridge.name=" + network["bridge"], *self.label_args(), network["name"]],
            mutation=True).decode("ascii").strip()
        if not re.fullmatch("[0-9a-f]{64}", network_id):
            raise EnvironmentFailure("CREATED_NETWORK_ID_UNKNOWN", unknown=True)
        self.check_network(network_id, [])
        self.runner.confirm_effects([effect])
        return network_id

    def firewall_rules(self):
        bridge = self.config["network"]["bridge"]
        comment = "recovery-" + digest(self.labels)[:20]
        states = ["-m", "conntrack", "--ctstate", "NEW,INVALID,UNTRACKED"]
        return [["INPUT", "-i", bridge, *states, "-m", "comment", "--comment", comment, "-j", "DROP"],
                ["DOCKER-USER", "-i", bridge, "!", "-o", bridge, *states, "-m", "comment", "--comment", comment, "-j", "DROP"]]

    def enforce_firewall(self):
        verify_large_pin(self.config["iptablesPin"], self.runner.guard)
        # Dedicated rules at the head of the effective host chains, never flush
        # or replace shared rules. Internal bridge traffic stays usable.
        effects = []
        for rule in self.firewall_rules():
            effects.append(self.runner.sequence + 1)
            self.runner.run([self.config["iptablesPin"]["path"], "-w", "5", "-I", rule[0], "1", *rule[1:]],
                            mutation=True)
        proof = self.check_firewall()
        self.runner.confirm_effects(effects)
        return proof

    def check_firewall(self):
        verify_large_pin(self.config["iptablesPin"], self.runner.guard)
        for rule in self.firewall_rules():
            self.runner.run([self.config["iptablesPin"]["path"], "-w", "5", "-C", *rule])
            raw = self.runner.run([self.config["iptablesPin"]["path"], "-w", "5", "-S", rule[0]])
            lines = raw.decode("utf-8").splitlines()
            actual = next((line for line in lines if line.startswith("-A ")), None)
            import shlex
            require(actual and shlex.split(actual) == ["-A", *rule], "FIREWALL_RULE_NOT_FIRST")
        return {"state": "ENFORCED", "rules": self.firewall_rules(), "observedAt": utc_now()}

    def create_volumes(self):
        values = []
        for volume in sorted(self.volume_names()):
            effect = self.runner.sequence + 1
            self.docker(["volume", "create", *self.label_args(), volume], mutation=True)
            items = decode(self.docker(["volume", "inspect", volume]))
            require(len(items) == 1 and items[0]["Name"] == volume and items[0]["Labels"] == self.labels
                    and items[0]["Driver"] == "local" and not items[0]["Options"], "VOLUME_IDENTITY_MISMATCH")
            path = safe_path(items[0]["Mountpoint"], directory=True)
            require(not any(path.iterdir()), "CREATED_VOLUME_NOT_EMPTY")
            values.append({"name": volume, "mountpoint": str(path), "labels": items[0]["Labels"], "empty": True})
            self.runner.confirm_effects([effect])
        return values

    def private_env(self, service, private_dir):
        env = dict(service["env"])
        secrets = [read_pin(pin) for pin in self.config["secretRefs"]]
        require(not any(secret["service"] == service["role"] == "backend" and secret["environment"] in
                    {"JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "JAVA_OPTS"} for secret in secrets),
                "APPLICATION_PROTECTION_SECRET_JVM_OPTIONS_REJECTED")
        for secret in secrets:
            if secret["service"] == service["role"] and secret["environment"] != "RECOVERY_MYSQL_CLIENT_CNF":
                ensure_material_path(secret["filePin"]["path"], self.config)
                raw = read_bytes(secret["filePin"]["path"], limit=65536)
                require(len(raw) == secret["filePin"]["bytes"] and hashlib.sha256(raw).hexdigest() ==
                        secret["filePin"]["sha256"], "SECRET_MATERIAL_CHANGED")
                value = raw.decode("utf-8")
                require(value and not any(char in value for char in "\r\n\x00"), "SECRET_ENV_FORMAT_INVALID")
                require(secret["environment"] not in env, "SECRET_ENV_COLLISION")
                env[secret["environment"]] = value
        path = private_dir / (service["role"] + ".env")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in sorted(env.items())).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        return path, env

    def create_service(self, service, private_dir):
        env_path, expected_env = self.private_env(service, private_dir)
        argv = ["create", "--name", service["name"], *self.label_args(), "--network", self.config["network"]["name"],
                "--ip", service["ip"], "--network-alias", service["role"], "--restart=no", "--cap-drop=ALL",
                "--dns=127.0.0.1", "--dns-search=.",
                "--security-opt=no-new-privileges:true", "--memory", str(service["memoryBytes"]),
                "--cpus", str(service["cpuMillis"] / 1000), "--pids-limit", "512", "--no-healthcheck", "--env-file", str(env_path)]
        for capability in service["capabilities"]:
            argv.extend(["--cap-add", capability])
        for mount in service["mounts"]:
            argv.extend(["--mount", f"type=volume,source={mount['volume']},target={mount['target']},volume-nocopy" +
                         (",readonly" if mount["readOnly"] else "")])
        for mount in service["configurationMounts"]:
            ensure_material_path(mount["pin"]["path"], self.config)
            verify_large_pin(mount["pin"], self.runner.guard)
            argv.extend(["--mount", f"type=bind,source={mount['pin']['path']},target={mount['target']},readonly"])
        for secret in map(read_pin, self.config["secretRefs"]):
            if secret["service"] == service["role"] and secret["environment"] == "RECOVERY_MYSQL_CLIENT_CNF":
                argv.extend(["--mount", f"type=bind,source={secret['filePin']['path']},target=/run/recovery/mysql-client.cnf,readonly"])
        for port in service["ports"]:
            argv.extend(["--publish", f"127.0.0.1:{port['hostPort']}:{port['containerPort']}/tcp"])
        argv.extend([self.image_records[service["role"]]["imageId"], *service["command"]])
        effect = self.runner.sequence + 1
        container_id = self.docker(argv, mutation=True).decode("ascii").strip()
        if not re.fullmatch("[0-9a-f]{64}", container_id):
            raise EnvironmentFailure("CREATED_CONTAINER_ID_UNKNOWN", unknown=True)
        item = self.inspect(container_id)
        actual_env = dict(entry.split("=", 1) for entry in item["Config"]["Env"])
        require(all(actual_env.get(key) == value for key, value in expected_env.items()), "CONTAINER_ENV_MISMATCH")
        self.check_service(service, item, running=False)
        self.identities[service["role"]] = container_id
        self.runner.confirm_effects([effect])
        return sanitize_inspect(item)

    def check_service(self, service, item, *, running):
        if service["role"] not in self.image_labels:
            image = decode(self.docker(["image", "inspect", self.image_records[service["role"]]["imageId"]]))
            require(len(image) == 1 and image[0]["Id"] == self.image_records[service["role"]]["imageId"], "IMAGE_IDENTITY_MISMATCH")
            self.image_labels[service["role"]] = image[0]["Config"]["Labels"] or {}
        expected_labels = {**self.image_labels[service["role"]], **self.labels}
        require(item["Name"] == "/" + service["name"] and item["Config"]["Labels"] == expected_labels and
                item["Image"] == self.image_records[service["role"]]["imageId"], "SERVICE_IDENTITY_MISMATCH")
        host = item["HostConfig"]
        require(host["NetworkMode"] == self.config["network"]["name"] and host["Privileged"] is False
                and set(host["CapDrop"] or []) == {"ALL"} and set(host["CapAdd"] or []) == set(service["capabilities"]) and not host["Devices"]
                and "no-new-privileges:true" in host["SecurityOpt"] and host["RestartPolicy"]["Name"] == "no"
                and host["PidMode"] == "" and host["IpcMode"] != "host" and not host["ExtraHosts"]
                and host["Dns"] == ["127.0.0.1"] and host["DnsSearch"] == ["."], "SERVICE_UNSAFE_HOST_CONFIG")
        require(item["Config"].get("Healthcheck", {}).get("Test") == ["NONE"], "UNAPPROVED_IMAGE_HEALTHCHECK")
        expected = {(mount["volume"], mount["target"], not mount["readOnly"]) for mount in service["mounts"]}
        actual = {(mount["Name"], mount["Destination"], mount["RW"]) for mount in item["Mounts"] if mount["Type"] == "volume"}
        require(expected == actual, "SERVICE_VOLUME_MISMATCH")
        allowed_binds = {(mount["pin"]["path"], mount["target"]) for mount in service["configurationMounts"]}
        allowed_binds.update((secret["filePin"]["path"], "/run/recovery/mysql-client.cnf")
                             for secret in map(read_pin, self.config["secretRefs"])
                             if secret["service"] == service["role"] and secret["environment"] == "RECOVERY_MYSQL_CLIENT_CNF")
        actual_binds = {(mount["Source"], mount["Destination"]) for mount in item["Mounts"] if mount["Type"] == "bind"}
        require(actual_binds == allowed_binds and all(not mount["RW"] for mount in item["Mounts"]
                if mount["Type"] == "bind") and all(mount["Type"] in ("bind", "volume") for mount in item["Mounts"]),
                "SERVICE_BIND_MISMATCH")
        ports = host["PortBindings"] or {}
        expected_ports = {f"{port['containerPort']}/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(port["hostPort"])}]
                          for port in service["ports"]}
        require(ports == expected_ports and not host["PublishAllPorts"], "SERVICE_PORT_MAPPING_MISMATCH")
        networks = item["NetworkSettings"]["Networks"]
        require(set(networks) == {self.config["network"]["name"]}, "SERVICE_FOREIGN_NETWORK")
        attached = networks[self.config["network"]["name"]]
        require(attached["IPAMConfig"]["IPv4Address"] == service["ip"], "SERVICE_STATIC_IP_MISMATCH")
        if running:
            state = item["State"]
            require(state["Running"] is True and all(state[key] is False for key in ("Paused", "Restarting", "Dead", "OOMKilled"))
                    and item["RestartCount"] == 0 and state["Pid"] > 0, "SERVICE_NOT_STABLY_RUNNING")
            require(attached["IPAddress"] == service["ip"] and attached["EndpointID"], "SERVICE_ENDPOINT_MISMATCH")
        else:
            require(item["State"]["Running"] is False and item["State"]["Status"] == "created", "SERVICE_ALREADY_STARTED")

    def start_service(self, service, container_id):
        self.check_firewall()
        self.check_service(service, self.inspect(container_id), running=False)
        effect = self.runner.sequence + 1
        self.docker(["start", container_id], mutation=True)
        item = self.inspect(container_id)
        self.check_service(service, item, running=True)
        self.runner.confirm_effects([effect])
        return sanitize_inspect(item)

    def check_network(self, network_id, expected_containers):
        items = decode(self.docker(["network", "inspect", network_id]))
        require(len(items) == 1, "NETWORK_INSPECT_INVALID")
        item = items[0]
        network = self.config["network"]
        require(item["Id"] == network_id and item["Name"] == network["name"] and item["Labels"] == self.labels
                and item["Driver"] == "bridge" and item["Internal"] is True and item["EnableIPv6"] is False
                and item["IPAM"]["Config"] == [{"Subnet": network["subnet"], "Gateway": network["gateway"]}]
                and item["Options"]["com.docker.network.bridge.name"] == network["bridge"], "NETWORK_IDENTITY_MISMATCH")
        require(set(item["Containers"]) == set(expected_containers), "NETWORK_FOREIGN_OR_MISSING_ENDPOINT")
        all_ids = self.docker(["ps", "-aq", "--no-trunc"]).decode("ascii").splitlines()
        for identity in all_ids:
            observed = self.inspect(identity)
            member = observed["NetworkSettings"]["Networks"].get(network["name"])
            if member is not None:
                require(identity in self.identities.values() and member["NetworkID"] == network_id,
                        "NETWORK_REVERSE_MEMBERSHIP_MISMATCH")
                if observed["State"]["Running"]:
                    endpoint = item["Containers"].get(identity)
                    require(endpoint and endpoint["EndpointID"] == member["EndpointID"] and
                            endpoint["IPv4Address"].split("/")[0] == member["IPAddress"] and
                            endpoint["Name"] == observed["Name"].lstrip("/"), "NETWORK_ENDPOINT_MISMATCH")
        return {"networkId": network_id, "name": network["name"], "subnet": network["subnet"],
                "internal": True, "containers": item["Containers"], "observedAt": utc_now()}

    def namespace_probe(self, role, spec, *, allow_not_ready=False):
        container_id = self.identities[role]
        item = self.inspect(container_id)
        service = next(service for service in self.config["services"] if service["role"] == role)
        self.check_service(service, item, running=True)
        pid = item["State"]["Pid"]
        require(os.name == "posix", "NATIVE_NAMESPACE_REQUIRED")
        fd = os.open(f"/proc/{pid}/ns/net", os.O_RDONLY)
        try:
            probe_path = Path(__file__).with_name("recovery_environment_probe.py")
            verify_large_pin(self.config["pythonPin"], self.runner.guard)
            probe_pins = [pin for pin in self.policy["moduleSourcePins"] if Path(pin["path"]) == probe_path]
            require(len(probe_pins) == 1, "NATIVE_PROBE_SOURCE_NOT_PINNED")
            verify_large_pin(probe_pins[0], self.runner.guard)
            raw = self.runner.run([self.config["pythonPin"]["path"], "-I", str(probe_path), "--namespace-fd", str(fd)],
                stdin=canonical({**spec, "seconds": min(self.runner.remaining(), self.policy["probeTimeoutSeconds"])}),
                pass_fds=(fd,))
            result = decode(raw)
            require(result["state"] == "OBSERVED" or allow_not_ready and result["state"] == "NOT_READY", "NATIVE_PROBE_FAILED")
            require(self.inspect(container_id)["State"]["Pid"] == pid, "PROBE_CONTAINER_PID_CHANGED")
            return {"containerId": container_id, "pid": pid, "observedAt": utc_now(), "result": result["result"]}
        finally:
            os.close(fd)

    def mysql_tables(self):
        for reference in map(read_pin, self.config["secretRefs"]):
            if reference["service"] == "mysql" and reference["environment"] == "RECOVERY_MYSQL_CLIENT_CNF":
                verify_large_pin(reference["filePin"], self.runner.guard)
        service = next(service for service in self.config["services"] if service["role"] == "mysql")
        query = f"SHOW TABLES FROM `{self.config['database']}`; SELECT 'RECOVERY_SQL_EXECUTED';"
        raw = self.docker(["exec", self.identities["mysql"], self.policy["mysqlClientPath"],
                          "--defaults-extra-file=/run/recovery/mysql-client.cnf", "--batch", "--skip-column-names", "-e", query])
        rows = raw.decode("utf-8").splitlines()
        require(rows and rows[-1] == "RECOVERY_SQL_EXECUTED", "MYSQL_SQL_EXECUTION_NOT_PROVEN")
        return {"containerId": self.identities[service["role"]], "tableCount": len(rows) - 1,
                "tableNamesSha256": digest(rows[:-1]), "sqlExecutionMarker": rows[-1]}

    def minio_buckets(self):
        secrets = {record["environment"]: record for record in map(read_pin, self.config["secretRefs"])
                   if record["service"] == "minio"}
        require("MINIO_ROOT_USER" in secrets and "MINIO_ROOT_PASSWORD" in secrets, "S3_SECRET_REFERENCES_REQUIRED")
        values = {}
        for key in ("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"):
            pin = secrets[key]["filePin"]
            raw = read_bytes(pin["path"], limit=65536)
            require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], "SECRET_MATERIAL_CHANGED")
            values[key] = raw.decode("utf-8")
        access, secret = values["MINIO_ROOT_USER"], values["MINIO_ROOT_PASSWORD"]
        return self.namespace_probe("minio", {"protocol": "s3", "port": 9000, "access": access, "secret": secret,
                                             "region": self.policy["s3Region"]})

    def health(self, service, *, allow_not_ready=False):
        role = service["role"]
        if role == "mysql":
            return self.mysql_tables()
        if role == "redis":
            return self.namespace_probe(role, {"protocol": "redis", "port": 6379}, allow_not_ready=allow_not_ready)
        health = service["health"]
        require(health is not None, "SERVICE_HEALTH_CONFIG_REQUIRED")
        return self.namespace_probe(role, {"protocol": "http", "port": health["port"], "path": health["path"],
                                            "expected": health["expected"]}, allow_not_ready=allow_not_ready)

    def isolation_probes(self):
        results = []
        self.check_firewall()
        for target in self.policy["blockedEndpoints"]:
            results.append(self.namespace_probe("redis", {"protocol": "blocked", "host": target["host"], "port": target["port"]}))
        results.append(self.namespace_probe("redis", {"protocol": "dnsBlocked", "name": self.policy["blockedDnsName"]}))
        return results
