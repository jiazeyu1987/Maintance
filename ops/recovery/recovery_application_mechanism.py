"""Concrete v3 application protection executor, selected by both W05 policy pins.

Runs a finite cold JVM in the actual pinned backend image before launch; probes
the actual protected HTTP/service boundaries after launch. No runtime is created
until an independently provisioned mechanism configuration and real credentials
have been supplied. Raw process/inspect output and secrets are never persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

SCOPES = {"BUSINESS_DATABASE", "BUSINESS_OBJECTS", "BUSINESS_DERIVED",
          "APPLICATION_MUTATIONS", "SCHEDULERS", "EXTERNAL_DISPATCH"}
REQUEST_FIELDS = {"schemaVersion", "phase", "operationId", "restoreId", "targetIdentityPin", "recoveryPoint",
                  "policyPin", "configurationPin", "imagePins", "containers", "deadlineMilliseconds"}
BINDINGS = ("operationId", "restoreId", "targetIdentityPin", "recoveryPoint", "policyPin", "configurationPin", "imagePins")


class ProtectionFailure(RuntimeError):
    def __init__(self, code, unknown=False, executor=None):
        super().__init__(code)
        self.code, self.unknown = code, unknown
        self.executor = executor


def require(value, code):
    if not value:
        raise ProtectionFailure(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def decode(raw):
    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, "PROTECTION_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ProtectionFailure("PROTECTION_NONFINITE_JSON")))


def safe_file(path):
    file = Path(path)
    require(file.is_absolute() and "," not in str(file), "PROTECTION_ABSOLUTE_PATH_REQUIRED")
    for ancestor in (file, *file.parents):
        require(not ancestor.is_symlink(), "PROTECTION_SYMLINK_REJECTED")
    info = file.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "PROTECTION_FILE_NOT_REGULAR")
    return file


def read_pin(pin, *, binary=False):
    require(type(pin) is dict and set(pin) == {"path", "bytes", "sha256"} and type(pin["bytes"]) is int
            and pin["bytes"] > 0 and re.fullmatch("[0-9a-f]{64}", pin["sha256"]), "PROTECTION_PIN_INVALID")
    file = safe_file(pin["path"])
    before = file.stat()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(file, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        chunks, length = [], 0
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk); length += len(chunk)
            if not binary:
                require(length <= 4 * 1024 * 1024, "PROTECTION_JSON_TOO_LARGE")
                chunks.append(chunk)
        after = os.fstat(stream.fileno())
    current = file.stat()
    def stamp(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
    require(stamp(before) == stamp(current) and stamp(opened) == stamp(after)
            and (before.st_dev, before.st_ino, before.st_size) == (opened.st_dev, opened.st_ino, opened.st_size)
            and length == pin["bytes"] and digest.hexdigest() == pin["sha256"], "PROTECTION_PIN_CHANGED")
    return None if binary else decode(b"".join(chunks))


def pin_file(path):
    raw = safe_file(str(path)).read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def write_json(path, value):
    require(not path.exists(), "PROTECTION_EVIDENCE_ALREADY_EXISTS")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".protection-", suffix=".tmp")
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    return pin_file(path)


def select_configuration(request):
    require(type(request) is dict and set(request) == REQUEST_FIELDS and
            request["schemaVersion"] == "RecoveryApplicationWriteProtectionRequest/v1" and
            request["phase"] in ("BEFORE_START", "AFTER_START") and type(request["deadlineMilliseconds"]) is int
            and request["deadlineMilliseconds"] > 0, "PROTECTION_REQUEST_INVALID")
    provisioned = os.environ.get("RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN")
    require(provisioned, "APPLICATION_MECHANISM_CONFIG_NOT_PROVISIONED")
    configuration_pin = decode(provisioned)
    config = read_pin(configuration_pin)
    fields = {"schemaVersion", *BINDINGS, "targetId", "applicationConfigPin", "dockerPin", "backendImagePin",
              "networkName", "mounts", "javaPath", "jarPath", "backendPort", "evidenceRoot"}
    require(set(config) == fields and config["schemaVersion"] == "RecoveryApplicationMechanismConfig/v1"
            and all(config[key] == request[key] for key in BINDINGS), "PROTECTION_MECHANISM_BINDING_MISMATCH")
    application = read_pin(config["applicationConfigPin"])
    require(application["schemaVersion"] == "RecoveryProtectionConfig/v1" and
            all(application[key] == request[key] for key in BINDINGS), "PROTECTION_APPLICATION_BINDING_MISMATCH")
    policy = read_pin(request["policyPin"])
    selected = "enforceScriptPin" if request["phase"] == "BEFORE_START" else "observeScriptPin"
    require(policy["mechanismId"] == "INT_RUOYI_RECOVERY_PROTECTION_V3" and set(policy["requiredScopes"]) == SCOPES
            and policy[selected] == pin_file(Path(__file__).absolute()), "PROTECTION_EXECUTOR_NOT_SELECTED")
    for pin in policy["sourceEvidencePins"]:
        read_pin(pin, binary=True)
    read_pin(config["dockerPin"], binary=True)
    image = read_pin(config["backendImagePin"])
    require(config["backendImagePin"] in request["imagePins"] and image["role"] == "backend"
            and re.fullmatch("sha256:[0-9a-f]{64}", image["imageId"]), "PROTECTION_BACKEND_IMAGE_UNBOUND")
    for key in ("javaPath", "jarPath"):
        require(type(config[key]) is str and config[key].startswith("/") and "\x00" not in config[key], "PROTECTION_IMAGE_PATH_REQUIRED")
    require(type(config["backendPort"]) is int and 0 < config["backendPort"] <= 65535, "PROTECTION_BACKEND_PORT_REQUIRED")
    require(type(config["mounts"]) is list and config["mounts"], "PROTECTION_MOUNTS_REQUIRED")
    mounted = {}
    for mount in config["mounts"]:
        require(set(mount) == {"pin", "target"} and mount["target"].startswith("/") and "," not in mount["target"]
                and mount["target"] not in mounted, "PROTECTION_MOUNT_INVALID")
        read_pin(mount["pin"], binary=True); mounted[mount["target"]] = mount["pin"]
    application_paths = [path for path, pin in mounted.items() if pin == config["applicationConfigPin"]]
    require(len(application_paths) == 1, "PROTECTION_CONFIG_MOUNT_UNBOUND")
    for owner in [application, application["businessRedis"], application["temporaryRedis"],
                  *application["jdbcTargets"], *application["objectClients"]]:
        for key, value in owner.items():
            if key in ("passwordFile", "accessKeyFile", "probeSecretFile"):
                require(value in mounted, "PROTECTION_SECRET_MOUNT_MISSING")
    root = Path(config["evidenceRoot"])
    require(root.is_absolute() and root.is_dir() and not root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700 and root.stat().st_uid == os.geteuid(), "PROTECTION_PRIVATE_EVIDENCE_ROOT_REQUIRED")
    return config, application, image, policy, configuration_pin, application_paths[0], mounted


class Executor:
    def __init__(self, request, config, root):
        self.request, self.config, self.root = request, config, root
        self.deadline = time.monotonic() + request["deadlineMilliseconds"] / 1000
        self.invocations = []
        self.evidence_pins = []
        self.pending_effects = set()
        supervised = os.environ.get("RECOVERY_ENVIRONMENT_SUPERVISED_GROUP")
        require(supervised is None or (supervised == "v1" and os.name == "posix" and
                os.getpgrp() == os.getpid() and os.getsid(0) == os.getpid()),
                "PROTECTION_SUPERVISED_GROUP_INVALID")
        self.supervised_group = supervised is not None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ProtectionFailure("PROTECTION_DEADLINE_EXPIRED", True)
        return remaining

    def finish_local(self, process):
        """Bounded observation of this task's local child; says nothing about a daemon."""
        if process.poll() is None:
            try:
                if os.name == "posix" and not self.supervised_group:
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass  # communicate still must observe the actual exit.
        return process.communicate(timeout=5)

    def run(self, argv, *, mutation=False, stdin=None, effect_kind="LOCAL", failure_observer=None):
        sequence = len(self.invocations)
        receipt = {"schemaVersion": "RecoveryEnvironmentInvocation/v1", "argvSha256": sha(canonical(argv)), "pid": None, "mutation": mutation,
                   "startedAt": utc(), "actualExitCode": None, "state": "TERMINAL_UNKNOWN",
                   "effectKind": effect_kind, "localProcessTerminated": False}
        process, output, error = None, b"", b""
        try:
            self.remaining()
            self.evidence_pins.append(write_json(self.root / ("intention-%03d.json" % sequence), receipt))
            self.remaining()  # Immediately before Popen, after potentially slow evidence I/O.
            # Under CommandRunner, every finite Docker/HTTP child inherits the
            # task's supervised session. A standalone executor owns a new group.
            # Never signal the inherited group here: it includes our supervisor.
            process = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=os.name == "posix" and not self.supervised_group,
                                       env={"PATH": os.defpath, "LANG": "C.UTF-8"})
            receipt["pid"] = process.pid
            if mutation and effect_kind != "LOCAL":
                self.pending_effects.add(sequence)
            self.evidence_pins.append(write_json(self.root / ("running-%03d.json" % sequence), receipt))
            output, error = process.communicate(input=stdin, timeout=self.remaining())
            receipt["actualExitCode"] = process.returncode
            receipt["localProcessTerminated"] = True
            if process.returncode != 0 and failure_observer is not None:
                observed = failure_observer(output)
                receipt["failureObservation"] = observed
                self.evidence_pins.append(write_json(self.root / ("failure-observation-%03d.json" % sequence), observed))
                if observed["state"] == "FAILED_RETAINED":
                    self.pending_effects.discard(sequence)
                raise ProtectionFailure(observed["code"], observed["state"] == "TERMINAL_UNKNOWN")
            if process.returncode != 0 and mutation and effect_kind != "LOCAL":
                raise ProtectionFailure("PROTECTION_NATIVE_EFFECT_TERMINAL_UNPROVEN", True)
            receipt["state"] = "SUCCEEDED" if process.returncode == 0 else "FAILED_RETAINED"
            require(process.returncode == 0, "PROTECTION_NATIVE_EXECUTION_FAILED")
            require(not error, "PROTECTION_NATIVE_STDERR_PRESENT")
            return output
        except BaseException as failure:
            # Every post-spawn exception goes through a bounded wait, including
            # deadline and recording failures. Only this local PID is controlled.
            if process is not None:
                try:
                    output, error = self.finish_local(process)
                    receipt["actualExitCode"] = process.returncode
                    receipt["localProcessTerminated"] = process.returncode is not None
                except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
                    failure = ProtectionFailure("PROTECTION_CHILD_TERMINATION_UNKNOWN", True)
            if isinstance(failure, ProtectionFailure):
                code = failure.code
                unknown = failure.unknown if process is not None else False
            else:
                code = "PROTECTION_CHILD_TIMEOUT_RETAINED" if isinstance(failure, subprocess.TimeoutExpired) else "PROTECTION_CHILD_EXECUTION_OR_RECORDING_FAILED"
                unknown = process is not None and mutation
            if process is not None and not receipt["localProcessTerminated"]:
                unknown = True
            if sequence in self.pending_effects:
                unknown = True
            receipt["state"] = "TERMINAL_UNKNOWN" if unknown else "FAILED_RETAINED"
            receipt["failureCode"] = code
            raise ProtectionFailure(code, unknown, self) from None
        finally:
            receipt.update(finishedAt=utc(), stdoutBytes=len(output), stderrBytes=len(error),
                           stdoutSha256=sha(output), stderrSha256=sha(error))
            try:
                self.invocations.append(write_json(self.root / ("invocation-%03d.json" % sequence), receipt))
            except BaseException:
                # Previously saved intention/running records remain originals.
                unknown = (receipt["state"] == "TERMINAL_UNKNOWN"
                           or (process is not None and (mutation or not receipt["localProcessTerminated"])))
                try:
                    self.evidence_pins.append(write_json(self.root / ("termination-%03d.json" % sequence), receipt))
                except BaseException:
                    # No effect is classified safe when persistence itself fails.
                    raise ProtectionFailure("PROTECTION_TERMINATION_EVIDENCE_NOT_PERSISTED", unknown, self) from None
                raise ProtectionFailure("PROTECTION_FINAL_EVIDENCE_NOT_PERSISTED", unknown, self) from None

    def docker(self, arguments, *, mutation=False):
        read_pin(self.config["dockerPin"], binary=True)
        return self.run([self.config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock", *arguments], mutation=mutation, effect_kind="DAEMON")

    def inspect_targets(self):
        ids = self.request["containers"]
        require(type(ids) is dict and {"mysql", "minio", "redis"}.issubset(ids)
                and all(re.fullmatch("[0-9a-f]{64}", value) for value in ids.values()), "PROTECTION_CONTAINER_IDS_REQUIRED")
        actual = decode(self.docker(["inspect", *ids.values()]))
        by_id = {item["Id"]: item for item in actual}
        require(set(by_id) == set(ids.values()), "PROTECTION_CONTAINER_IDENTITY_MISMATCH")
        network = decode(self.docker(["network", "inspect", self.config["networkName"]]))
        require(len(network) == 1 and network[0]["Internal"] is True, "PROTECTION_NETWORK_NOT_INTERNAL")
        records, hosts = {}, {}
        for role, identifier in ids.items():
            item = by_id[identifier]
            labels = item["Config"]["Labels"]
            require(item["State"]["Running"] is True and labels.get("intruoyi.recovery.operation") == self.request["operationId"]
                    and labels.get("intruoyi.recovery.target") == self.config["targetId"]
                    and set(item["NetworkSettings"]["Networks"]) == {self.config["networkName"]}, "PROTECTION_CONTAINER_SCOPE_MISMATCH")
            address = item["NetworkSettings"]["Networks"][self.config["networkName"]]
            ipaddress.IPv4Address(address["IPAddress"])
            hosts[role] = {address["IPAddress"], item["Name"].lstrip("/"), *(address.get("Aliases") or [])}
            records[role] = {"id": identifier, "imageId": item["Image"], "labels": labels,
                             "ip": address["IPAddress"], "networkId": address["NetworkID"],
                             "restartCount": item["RestartCount"], "startedAt": item["State"]["StartedAt"],
                             "commandSha256": sha(canonical([item["Path"], item["Args"]])),
                             "envSha256": sha(canonical(item["Config"]["Env"]))}
        observed = self.docker(["ps", "-aq", "--no-trunc", "--filter", "label=intruoyi.recovery.operation=" + self.request["operationId"]])
        require(set(observed.decode("ascii").splitlines()) == set(ids.values()), "PROTECTION_UNTRACKED_OPERATION_CONTAINER")
        return records, hosts

    def http(self, host, port, path, body, secret=None):
        def observe_failure(raw):
            value = decode(raw)
            require(set(value) == {"schemaVersion", "state", "code", "dispatchState"}
                    and value["schemaVersion"] == "RecoveryProtectionHttpFailure/v1"
                    and ((value["state"], value["dispatchState"], value["code"]) in
                         {("FAILED_RETAINED", "NOT_DISPATCHED", "PROTECTION_HTTP_PRE_DISPATCH_FAILED"),
                          ("TERMINAL_UNKNOWN", "MAY_HAVE_DISPATCHED", "PROTECTION_HTTP_EFFECT_TERMINAL_UNPROVEN")}),
                    "PROTECTION_HTTP_FAILURE_INVALID")
            return value
        original = self.run([sys.executable, "-I", str(Path(__file__).absolute()), "--http-worker"], mutation=True, effect_kind="HTTP",
                failure_observer=observe_failure,
                stdin=canonical({"host": host, "port": port, "path": path, "body": body, "secret": secret,
                                 "seconds": self.remaining()}))
        result = decode(original)
        require(set(result) == {"status", "body"}, "PROTECTION_HTTP_ORIGINAL_INVALID")
        return result["status"], result["body"]


def validate_observation(observation, configuration_pin):
    require(set(observation) == {"schemaVersion", "configurationSha256", "state", "scopes", "beforeFingerprints", "afterFingerprints"}
            and observation["schemaVersion"] == "RecoveryProtectionNativeProbe/v1" and observation["state"] == "REFUSED"
            and observation["configurationSha256"] == configuration_pin["sha256"]
            and len(observation["scopes"]) == 6 and set(observation["scopes"]) == SCOPES, "PROTECTION_NATIVE_COVERAGE_INVALID")
    before, after = observation["beforeFingerprints"], observation["afterFingerprints"]
    require(set(before) == SCOPES and before == after and all(type(value) is str and re.fullmatch("[0-9a-f]{64}", value)
            for value in before.values()), "PROTECTION_NATIVE_BUSINESS_STATE_CHANGED")


def validate_redis_domains(application, redis_identity, redis_hosts):
    domains = []
    for key in ("businessRedis", "temporaryRedis"):
        target = application[key]
        require(target["host"] in redis_hosts, "PROTECTION_REDIS_ENDPOINT_OUTSIDE_TARGET")
        domains.append((redis_identity, target["port"], target["database"]))
    require(domains[0] != domains[1], "PROTECTION_TEMP_REDIS_NATIVE_DOMAIN_ALIAS")


def execute_protection(request, context):
    require(sys.platform == "linux" and os.geteuid() == 0, "PROTECTION_NATIVE_LINUX_ROOT_REQUIRED")
    config, application, image, policy, config_pin, application_path, mounts = select_configuration(request)
    root = Path(tempfile.mkdtemp(prefix="application-protection-" + request["phase"].lower() + "-", dir=config["evidenceRoot"]))
    executor = Executor(request, config, root)
    context["executor"] = executor
    before, hosts = executor.inspect_targets()
    for target in application["jdbcTargets"]:
        require(urlsplit(target["url"].removeprefix("jdbc:")).hostname in hosts["mysql"], "PROTECTION_DATABASE_ENDPOINT_OUTSIDE_TARGET")
    for target in application["objectClients"]:
        require(urlsplit(target["endpoint"]).hostname in hosts["minio"], "PROTECTION_OBJECT_ENDPOINT_OUTSIDE_TARGET")
    validate_redis_domains(application, before["redis"]["id"], hosts["redis"])
    if request["phase"] == "BEFORE_START":
        require(set(before) == {"mysql", "minio", "redis"}, "PROTECTION_APPLICATION_ALREADY_STARTED")
        jar = executor.docker(["run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
                               "--security-opt=no-new-privileges:true",
                               "--label", "intruoyi.recovery.operation=" + request["operationId"],
                               "--label", "intruoyi.recovery.target=" + config["targetId"],
                               "--entrypoint", "sha256sum", image["imageId"], config["jarPath"]], mutation=True)
        require(jar.decode("ascii").split()[0] == application["artifactSha256"], "PROTECTION_ACTUAL_ARTIFACT_MISMATCH")
        argv = ["run", "--rm", "--name", "protection-cold-" + root.name, "--network", config["networkName"],
                "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--label", "intruoyi.recovery.operation=" + request["operationId"],
                "--label", "intruoyi.recovery.target=" + config["targetId"]]
        for mount in config["mounts"]:
            argv += ["--mount", "type=bind,source=" + mount["pin"]["path"] + ",target=" + mount["target"] + ",readonly"]
        argv += ["--entrypoint", config["javaPath"], image["imageId"],
                 "-Dintruoyi.recovery.protection.path=" + application_path,
                 "-Dintruoyi.recovery.protection.sha256=" + config["applicationConfigPin"]["sha256"],
                 "-Dintruoyi.maintenance.boot.artifactSha256=" + application["artifactSha256"],
                 "-Dloader.main=cn.iocoder.yudao.server.RecoveryProtectionColdProbe", "-cp", config["jarPath"],
                 "org.springframework.boot.loader.launch.PropertiesLauncher"]
        output = executor.docker(argv, mutation=True)
        lines = [line for line in output.splitlines() if line.startswith(b"RECOVERY_PROTECTION_RESULT=")]
        require(len(lines) == 1, "PROTECTION_COLD_ORIGINAL_RESULT_MISSING")
        observation = decode(lines[0].split(b"=", 1)[1])
    else:
        require("backend" in before and before["backend"]["imageId"] == image["imageId"], "PROTECTION_RUNNING_BACKEND_IMAGE_MISMATCH")
        mounted_secret = mounts[application["probeSecretFile"]]
        read_pin(mounted_secret, binary=True)
        secret = safe_file(mounted_secret["path"]).read_text(encoding="utf-8")
        require(secret and not any(char in secret for char in "\r\n\x00"), "PROTECTION_PROBE_SECRET_INVALID")
        status, refusal = executor.http(before["backend"]["ip"], config["backendPort"], "/admin-api/infra/file/upload", {})
        require(status == 403 and refusal == {"code": 403, "msg": "RECOVERY_WRITE_DENIED", "scope": "APPLICATION_MUTATIONS"},
                "PROTECTION_REAL_HTTP_MUTATION_NOT_REFUSED")
        status, observation = executor.http(before["backend"]["ip"], config["backendPort"], "/admin-api/infra/recovery-protection/probe",
                {**{key: request[key] for key in BINDINGS}, "phase": "AFTER_START", "configurationSha256": config["applicationConfigPin"]["sha256"]}, secret)
        require(status == 200, "PROTECTION_LIVE_PROBE_FAILED")
    validate_observation(observation, config["applicationConfigPin"])
    after, _ = executor.inspect_targets()
    require(before == after, "PROTECTION_TARGET_CHANGED_DURING_PROBE")
    read_pin(config_pin)
    read_pin(config["applicationConfigPin"])
    for mount in config["mounts"]:
        read_pin(mount["pin"], binary=True)
    original = write_json(root / "native-observation.json", {**observation, "containers": before, "observedAt": utc()})
    scopes = []
    for scope in sorted(SCOPES):
        fingerprint = sha(canonical({"business": observation["beforeFingerprints"][scope], "containers": before}))
        enforcement = write_json(root / (scope.lower() + "-enforcement.json"), {
            "schemaVersion": "RecoveryProtectionMechanismEnforcement/v1", **{key: request[key] for key in BINDINGS},
            "phase": request["phase"], "scope": scope, "mechanismConfigurationPin": config_pin,
            "applicationConfigPin": config["applicationConfigPin"], "sourceEvidencePins": policy["sourceEvidencePins"],
            "nativeObservationPin": original, "originalInvocationPins": executor.invocations})
        rejection = write_json(root / (scope.lower() + "-refusal.json"), {
            "schemaVersion": "RecoveryApplicationWriteRefusal/v1", "scope": scope, "phase": request["phase"],
            "operationId": request["operationId"], "targetIdentityPin": request["targetIdentityPin"],
            "recoveryPoint": request["recoveryPoint"], "containers": request["containers"], "denied": True,
            "beforeFingerprint": fingerprint, "afterFingerprint": fingerprint,
            "originalInvocationPins": [pin for pin in executor.invocations if read_pin(pin)["mutation"]],
            "nativeObservationPin": original})
        scopes.append({"scope": scope, "enforcementPin": enforcement, "beforeFingerprint": fingerprint,
                       "afterFingerprint": fingerprint, "rejectionObservationPins": [rejection]})
    executor.pending_effects.clear()  # Actual refusal/readback and its originals are now retained.
    return {"schemaVersion": "RecoveryApplicationWriteProtectionObservation/v1", "phase": request["phase"],
            **{key: request[key] for key in ("operationId", "restoreId", "targetIdentityPin", "recoveryPoint", "policyPin", "containers")},
            "state": "ENFORCED", "observedAt": utc(), "scopeObservations": scopes}


def protect(request):
    context = {}
    try:
        return execute_protection(request, context)
    except BaseException as failure:
        executor = context.get("executor")
        unknown = bool(executor and executor.pending_effects)
        code = failure.code if isinstance(failure, ProtectionFailure) else "PROTECTION_EXECUTION_OR_INPUT_FAILED"
        raise ProtectionFailure(code, unknown or (isinstance(failure, ProtectionFailure) and failure.unknown), executor) from None


def http_worker():
    connection = None
    may_have_dispatched = False
    try:
        spec = decode(sys.stdin.buffer.read(4 * 1024 * 1024 + 1))
        require(set(spec) == {"host", "port", "path", "body", "secret", "seconds"}
                and type(spec["seconds"]) in (float, int) and spec["seconds"] > 0,
                "PROTECTION_HTTP_WORKER_INPUT_INVALID")
        address = ipaddress.IPv4Address(spec["host"])
        require(address.is_private and not address.is_loopback and not address.is_unspecified,
                "PROTECTION_HTTP_PRIVATE_TARGET_REQUIRED")
        require(spec["path"] in ("/admin-api/infra/file/upload", "/admin-api/infra/recovery-protection/probe"),
                "PROTECTION_HTTP_WORKER_ROUTE_INVALID")
        connection = http.client.HTTPConnection(str(address), spec["port"], timeout=spec["seconds"])
        headers = {"Content-Type": "application/json", "tenant-id": "122", "Connection": "close"}
        if spec["secret"] is not None:
            headers["X-Recovery-Probe-Authorization"] = spec["secret"]
        body = canonical(spec["body"])
        connection.connect()  # A connection failure here cannot have sent this POST.
        may_have_dispatched = True  # request itself may fail after sending only part.
        connection.request("POST", spec["path"], body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        require(len(raw) <= 4 * 1024 * 1024, "PROTECTION_HTTP_RESPONSE_TOO_LARGE")
        sys.stdout.buffer.write(canonical({"status": response.status, "body": decode(raw)}) + b"\n")
        return 0
    except (ProtectionFailure, OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        sys.stdout.buffer.write(canonical({"schemaVersion": "RecoveryProtectionHttpFailure/v1",
            "state": "TERMINAL_UNKNOWN" if may_have_dispatched else "FAILED_RETAINED",
            "code": "PROTECTION_HTTP_EFFECT_TERMINAL_UNPROVEN" if may_have_dispatched else "PROTECTION_HTTP_PRE_DISPATCH_FAILED",
            "dispatchState": "MAY_HAVE_DISPATCHED" if may_have_dispatched else "NOT_DISPATCHED"}) + b"\n")
        return 2
    finally:
        if connection is not None:
            connection.close()


def main():
    request = None
    try:
        request = decode(sys.stdin.buffer.read(4 * 1024 * 1024 + 1))
        result = protect(request)
    except ProtectionFailure as failure:
        executor = failure.executor
        result = {"schemaVersion": "RecoveryApplicationProtectionFailure/v1", "state": "TERMINAL_UNKNOWN" if failure.unknown else "FAILED_RETAINED", "code": failure.code,
                  "bindings": {key: request[key] for key in ("phase", *BINDINGS, "containers")} if isinstance(request, dict) and REQUEST_FIELDS == set(request) else None,
                  "originalInvocationPins": executor.invocations if executor else [],
                  "failureEvidencePins": executor.evidence_pins if executor else []}
        sys.stdout.buffer.write(canonical(result) + b"\n")
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        # Retain a failed result, never a successful observation. Exception text may contain secrets.
        sys.stdout.buffer.write(canonical({"schemaVersion": "RecoveryApplicationProtectionFailure/v1", "state": "TERMINAL_UNKNOWN", "code": "PROTECTION_EXECUTION_OR_INPUT_FAILED"}) + b"\n")
        return 2
    sys.stdout.buffer.write(canonical(result) + b"\n")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--http-worker"]:
        raise SystemExit(http_worker())
    if sys.argv[1:]:
        raise SystemExit(2)
    raise SystemExit(main())
