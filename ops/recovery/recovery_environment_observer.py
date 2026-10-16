"""W05 read-only terminal resource observer for explicitly registered tasks.

The selected native profile/configuration must already be provisioned. This
program does not discover resources by prefix, infer paths, stop processes,
probe business writes, or treat a successful CLI exit as resource termination.
"""
import argparse
import os
from pathlib import Path
import sys
import time

from recovery_environment_contract import (EnvironmentFailure, atomic_json, decode, digest, exact,
    pin_file, read_bytes, read_pin, require, safe_path, utc_now, verify_large_pin)
from recovery_environment_runtime import CommandRunner, NativeDocker, sanitize_inspect

CONFIG_ENV = "RECOVERY_RESOURCE_OBSERVER_CONFIG_PIN"
BOUND = ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain", "pid",
         "processStartedAt", "originalExitPin")
REQUEST_FIELDS = ("schemaVersion", *BOUND, "sourceOrTargetRef", "selectedPointPin", "operationResultPath", "deadlineMilliseconds")


def container_fact(item):
    """Keep identity and status; health output/error text may contain secrets."""
    observed = sanitize_inspect(item)
    observed["state"] = {key: item["State"][key] for key in
                         ("Status", "Running", "Paused", "Restarting", "OOMKilled", "Dead", "Pid", "ExitCode", "StartedAt", "FinishedAt")}
    if "Health" in item["State"]:
        observed["state"]["healthStatus"] = item["State"]["Health"]["Status"]
    return observed


def result_container(binding, result, original, runner, input_pins, fact, guard):
    """Resolve newly created IDs from this request's original W05 artifact."""
    exact(binding, ("bindingKind", "role", "name"), "RESOURCE_OBSERVER_RESULT_BINDING_INVALID")
    config = read_pin(original["sourceOrTargetRef"])
    input_pins.extend([original["sourceOrTargetRef"], original["policyPin"], *config["imagePins"], *config["secretRefs"]])
    require(config["schemaVersion"] == "RecoveryEnvironmentConfig/v1", "RESOURCE_OBSERVER_RESULT_CONFIG_INVALID")
    service = next(service for service in config["services"] if service["role"] == binding["role"])
    require(service["name"] == binding["name"], "RESOURCE_OBSERVER_RESULT_SERVICE_MISMATCH")
    data = result["data"]
    require(data["targetIdentityPin"] == config["targetIdentityPin"] and data["configurationPin"] == config["configurationPin"],
            "RESOURCE_OBSERVER_RESULT_TARGET_MISMATCH")
    if original["action"] == "PREPARE_TARGET":
        require(data["schemaVersion"] == "RecoveryTarget/v1", "RESOURCE_OBSERVER_RESULT_ARTIFACT_INVALID")
        ref = data["resourcesProofPin"]; proof = read_pin(ref)
        require(proof["schemaVersion"] == "RecoveryEnvironmentProof/v1" and
                proof["configurationRef"] == original["sourceOrTargetRef"] and
                proof["planPin"] == original["inputPins"]["restorePlan"] and proof["leaseRef"] == original["leaseRef"],
                "RESOURCE_OBSERVER_RESULT_PROOF_MISMATCH")
        rows = proof["services"]
    else:
        require(original["action"] == "START_APPLICATION" and data["schemaVersion"] == "ApplicationStartResult/v1" and
                data["state"] == "SUCCEEDED", "RESOURCE_OBSERVER_RESULT_ARTIFACT_INVALID")
        refs = [ref for ref in data["originalStartResultPins"] if Path(ref["path"]).name == "application-launch.json"]
        require(len(refs) == 1, "RESOURCE_OBSERVER_RESULT_LAUNCH_REQUIRED")
        ref = refs[0]; proof = read_pin(ref)
        require(proof["schemaVersion"] == "RecoveryApplicationLaunch/v1" and
                proof["restoreResultPin"] == original["inputPins"]["restoreExecutionResult"] and
                proof["configurationPin"] == config["configurationPin"], "RESOURCE_OBSERVER_RESULT_PROOF_MISMATCH")
        rows = proof["started"]
    require(proof["operationId"] == original["operationId"] and proof["targetIdentityPin"] == config["targetIdentityPin"],
            "RESOURCE_OBSERVER_RESULT_PROOF_MISMATCH")
    matches = [row for row in rows if row["name"] == "/" + binding["name"]]
    require(len(matches) == 1, "RESOURCE_OBSERVER_RESULT_SERVICE_MISSING")
    row = matches[0]
    input_pins.append(ref)
    verify_large_pin(ref, guard)
    fact("result-container-" + binding["role"], {"artifactPin": ref, "id": row["id"], "name": row["name"]})
    runtime = NativeDocker(config, read_pin(original["policyPin"]), runner, original["operationId"])
    return row, runtime, service


def native_identity():
    require(sys.platform == "linux" and os.geteuid() == 0, "RESOURCE_OBSERVER_NATIVE_LINUX_ROOT_REQUIRED")
    return {"hostId": read_bytes("/etc/machine-id").decode("ascii").strip(),
            "bootId": read_bytes("/proc/sys/kernel/random/boot_id").decode("ascii").strip(), "uid": os.geteuid(),
            **{name + "Namespace": os.readlink("/proc/self/ns/" + name) for name in ("pid", "mnt", "net")}}


def process_stat(pid, boot):
    path = Path("/proc") / str(pid) / "stat"
    try:
        raw = path.read_text(encoding="ascii")
    except FileNotFoundError:
        return None
    tail = raw[raw.rfind(")") + 2:].split()
    require(len(tail) >= 20, "PROCESS_STAT_INCOMPLETE")
    return {"pid": pid, "state": tail[0], "parentPid": int(tail[1]), "processGroup": int(tail[2]),
            "sessionId": int(tail[3]), "processStartedAt": "linux:" + boot + ":" + tail[19]}


def process_scope(pid, started, boot):
    current = process_stat(pid, boot)
    # A reused PID makes the original session membership unobservable, even
    # with a known old exit. Keep it unknown instead of assuming absence.
    require(current is None, "ORIGINAL_PID_ACTIVE_OR_REUSED")
    members = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        row = process_stat(int(path.name), boot)
        if row is not None and (row["processGroup"] == pid or row["sessionId"] == pid):
            members.append(row)
    require(not members, "ORIGINAL_PROCESS_SCOPE_ACTIVE")
    return {"pid": pid, "processStartedAt": started, "currentPidAbsent": True, "sessionAndGroupMembers": members}


def pinned_config():
    raw = os.environ.get(CONFIG_ENV)
    require(raw is not None, "RESOURCE_OBSERVER_CONFIG_REQUIRED")
    ref = decode(raw.encode("utf-8"))
    return ref, read_pin(ref)


def observe(request, config_ref, config, root, *, identity_reader=native_identity, process_reader=process_scope):
    exact(request, REQUEST_FIELDS, "RESOURCE_OBSERVER_REQUEST_INVALID")
    require(request["schemaVersion"] == "RecoveryControlResourceObservationRequest/v1" and
            type(request["deadlineMilliseconds"]) is int and request["deadlineMilliseconds"] > 0,
            "RESOURCE_OBSERVER_REQUEST_INVALID")
    deadline = time.monotonic() + request["deadlineMilliseconds"] / 1000
    def guard():
        require(time.monotonic() < deadline, "RESOURCE_OBSERVER_DEADLINE_EXCEEDED")
        verify_large_pin(config_ref, lambda: None)
    runner = CommandRunner(root, deadline, guard)
    facts = []
    input_pins = []
    def fact(name, value):
        path = root / ("resource-fact-" + name + ".json")
        require(not path.exists(), "RESOURCE_OBSERVER_FACT_EXISTS")
        atomic_json(path, {"schemaVersion": "RecoveryControlResourceFact/v1", **{key: request[key] for key in BOUND},
                           "observedAt": utc_now(), "monotonicNs": time.monotonic_ns(), "wallNs": time.time_ns(),
                           "fact": value})
        facts.append(pin_file(path))
    try:
        exact(config, ("schemaVersion", "sourceProfilePin", "hostIdentity", "pythonPin", "observerPin", "moduleSourcePins",
                       "dockerPin", "dockerEngineId", "registrations"), "RESOURCE_OBSERVER_CONFIG_INVALID")
        require(config["schemaVersion"] == "RecoveryResourceObserverConfig/v1", "RESOURCE_OBSERVER_CONFIG_INVALID")
        actual = identity_reader()
        fact("native-host", actual)
        require(actual == config["hostIdentity"] and request["clockDomain"] ==
                {key: actual[key] for key in ("hostId", "bootId")}, "RESOURCE_OBSERVER_HOST_MISMATCH")
        require(config["observerPin"] == pin_file(__file__) and Path(config["pythonPin"]["path"]) == Path(sys.executable).resolve(),
                "RESOURCE_OBSERVER_EXECUTABLE_MISMATCH")
        for ref in [config["pythonPin"], config["dockerPin"], *config["moduleSourcePins"]]:
            verify_large_pin(ref, guard)
        require(len(config["moduleSourcePins"]) == 4 and {Path(ref["path"]).name for ref in config["moduleSourcePins"]} ==
                {"recovery_environment_observer.py", "recovery_environment_contract.py", "recovery_environment_runtime.py",
                 "recovery_environment_supervisor.py"} and
                all(Path(ref["path"]).parent == Path(__file__).parent for ref in config["moduleSourcePins"]),
                "RESOURCE_OBSERVER_SOURCE_CLOSURE_REQUIRED")
        profile = read_pin(config["sourceProfilePin"])
        require(profile["schemaVersion"] == "RecoveryLocalEnvironmentRegistration/v1" and
                profile["usableForExecution"] is True and profile["host"]["selectedExecutionHost"] is not None,
                "RESOURCE_OBSERVER_ENVIRONMENT_NOT_USABLE")
        registration_ref = config["registrations"].get(request["requestPin"]["sha256"])
        require(registration_ref is not None, "RESOURCE_OBSERVER_TASK_REGISTRATION_REQUIRED")
        inventory = read_pin(profile["resourceManifestPin"])
        registered = read_pin(registration_ref)
        exact(registered, ("schemaVersion", "operationId", "requestId", "requestPin",
                           "sourceOrTargetRef", "selectedPointPin", "operationResultPath",
                           "containers", "networks", "volumes", "files", "journalPaths", "nativeProcesses"),
              "RESOURCE_OBSERVER_REGISTRATION_INVALID")
        require(registered["schemaVersion"] == "RecoveryTaskResourceRegistration/v1" and
                all(registered[key] == request[key] for key in ("operationId", "requestId", "requestPin",
                    "sourceOrTargetRef", "selectedPointPin", "operationResultPath")),
                "RESOURCE_OBSERVER_REGISTRATION_MISMATCH")
        require(inventory["schemaVersion"] == "RecoveryTaskResourceManifest/v1" and
                inventory["ownerThreadId"] == "01a124c0-a5fa-7e22-bd17-f37908b4827e" and
                all(entry in inventory[kind] for kind in ("containers", "networks", "volumes") for entry in registered[kind]) and
                all(path in inventory["journalPaths"] for path in registered["journalPaths"]),
                "RESOURCE_OBSERVER_RESOURCES_NOT_REGISTERED")
        require(all(type(registered[key]) is list for key in ("containers", "networks", "volumes", "files", "journalPaths", "nativeProcesses")) and
                all(resource.get("bindingKind") in ("PINNED_EXISTING", "W05_RESULT") for resource in registered["containers"]),
                "RESOURCE_OBSERVER_REGISTRATION_INVALID")
        original = read_pin(request["requestPin"])
        require(all(original[key] == request[key] for key in ("operationId", "requestId", "sourceOrTargetRef", "selectedPointPin")),
                "RESOURCE_OBSERVER_ORIGINAL_REQUEST_MISMATCH")
        exit_record = read_pin(request["originalExitPin"])
        require(exit_record["schemaVersion"] == "RecoveryControlNativeExit/v1" and
                all(exit_record[key] == request[key] for key in BOUND if key != "originalExitPin") and
                type(exit_record["cliExitCode"]) is int and exit_record["processTerminal"] is True and
                exit_record["timedOut"] is False, "RESOURCE_OBSERVER_ORIGINAL_EXIT_UNKNOWN")
        intent = read_pin(exit_record["intentPin"])
        require(intent["schemaVersion"] == "RecoveryControlNativeIntent/v1" and
                all(intent[key] == request[key] for key in ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain")) and
                intent["startedMonotonicNs"] <= exit_record["observedMonotonicNs"] <= time.monotonic_ns() and
                exit_record["observedWallNs"] <= time.time_ns(), "RESOURCE_OBSERVER_NATIVE_INTENT_MISMATCH")
        binding = read_pin(pin_file(Path(request["originalExitPin"]["path"]).with_name("native-process-binding.json")))
        require(binding["schemaVersion"] == "RecoveryControlObservationBinding/v1" and
                all(binding[key] == request[key] for key in BOUND if key != "originalExitPin") and
                binding["intentPin"] == exit_record["intentPin"] and binding["profilePin"] == intent["profilePin"],
                "RESOURCE_OBSERVER_PROCESS_BINDING_MISMATCH")
        native_profile = read_pin(intent["profilePin"])
        require(native_profile["sourceProfilePin"] == config["sourceProfilePin"] and
                native_profile["resourceObserverPin"] == config["observerPin"] and
                native_profile["pythonPin"] == config["pythonPin"] and
                decode(native_profile["environment"][CONFIG_ENV].encode("utf-8")) == config_ref and
                all(native_profile[key] == actual[key] for key in ("hostId", "bootId", "uid")),
                "RESOURCE_OBSERVER_PROFILE_MISMATCH")
        require(root.parent.parent == Path(native_profile["evidenceRoot"]) and
                Path(request["operationResultPath"]).parent == root and
                Path(request["originalExitPin"]["path"]).parent == root,
                "RESOURCE_OBSERVER_EVIDENCE_SCOPE_MISMATCH")
        require(type(request["pid"]) is int and request["pid"] > 0 and request["processStartedAt"].startswith("linux:" + actual["bootId"] + ":"),
                "RESOURCE_OBSERVER_NATIVE_PID_REQUIRED")
        fact("process-scope", process_reader(request["pid"], request["processStartedAt"], actual["bootId"]))
        result_ref = pin_file(request["operationResultPath"])
        result = read_pin(result_ref)
        require(result["schemaVersion"] == "backup-restore-operation-result/v1" and
                result["operationId"] == original["operationId"] and result["requestId"] == original["requestId"] and
                result["action"] == original["action"] and result["state"] in ("SUCCEEDED", "FAILED_RETAINED") and
                exit_record["cliExitCode"] == {"SUCCEEDED": 0, "FAILED_RETAINED": 1}[result["state"]],
                "RESOURCE_OBSERVER_OPERATION_OUTCOME_UNKNOWN")
        require(registered["containers"], "RESOURCE_OBSERVER_REGISTERED_CONTAINER_REQUIRED")
        require(registered["journalPaths"], "RESOURCE_OBSERVER_TERMINAL_JOURNALS_REQUIRED")
        journal_pins = []
        for index, path in enumerate(registered["journalPaths"]):
            require(Path(path).is_relative_to(Path(profile["privateNativePath"])), "RESOURCE_OBSERVER_JOURNAL_OUTSIDE_TASK")
            ref = pin_file(path)
            journal_pins.append(ref)
            journal = read_pin(ref)
            require(journal["operationId"] == original["operationId"] and
                    journal["schemaVersion"] in ("RecoveryEnvironmentJournal/v1", "RecoveryEnvironmentTargetJournal/v1", "RecoveryRequestJournal/v1") and
                    journal["requestId"] == original["requestId"] and journal["requestSha256"] == digest(original) and
                    journal["state"] == result["state"] and journal["resultPin"] is not None and
                    read_pin(journal["resultPin"]) == result, "RESOURCE_OBSERVER_JOURNAL_UNKNOWN")
            fact("journal-%03d" % index, {"journalPin": ref, "state": journal["state"]})
        for index, process in enumerate(registered["nativeProcesses"]):
            process_record, waited = read_pin(process["processPin"]), read_pin(process["exitPin"])
            require(process_record["schemaVersion"] == "RecoveryTaskNativeProcess/v1" and
                    waited["schemaVersion"] == "RecoveryTaskNativeExit/v1" and
                    process_record["operationId"] == original["operationId"] and
                    process_record["clockDomain"] == request["clockDomain"] and
                    all(process_record[key] == request[key] for key in ("requestId", "requestPin", "attemptId", "observerEpoch")) and
                    all(waited[key] == request[key] for key in ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain")) and
                    waited["originalProcessPin"] == process["processPin"] and waited["processTerminal"] is True and
                    type(waited["actualExitCode"]) is int and waited["timedOut"] is False and
                    waited["pid"] == process_record["pid"] and waited["processStartedAt"] == process_record["processStartedAt"],
                    "RESOURCE_OBSERVER_CHILD_EXIT_UNKNOWN")
            fact("child-%03d" % index, process_reader(process_record["pid"], process_record["processStartedAt"], actual["bootId"]))
        docker = [config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock"]
        engine = decode(runner.run(docker + ["info", "--format", '{{json .}}']))
        require(engine["ID"] == config["dockerEngineId"] and engine["OSType"] == "linux", "RESOURCE_OBSERVER_DAEMON_MISMATCH")
        data_root = safe_path(engine["DockerRootDir"], directory=True)
        fact("daemon-filesystem", {"dockerEngineId": engine["ID"], "path": str(data_root), "device": data_root.stat().st_dev})
        container_ids = []
        for index, expected in enumerate(registered["containers"]):
            require(expected["name"].startswith("br20261010-w01w07-"), "RESOURCE_OBSERVER_UNOWNED_CONTAINER")
            generated = expected["bindingKind"] == "W05_RESULT"
            if generated:
                require(result["state"] == "SUCCEEDED", "RESOURCE_OBSERVER_RESULT_BINDING_NOT_SUCCEEDED")
                row, runtime, service = result_container(expected, result, original, runner, input_pins, fact, guard)
                state = row["state"]
                expected = {"name": expected["name"], "id": row["id"], "imageId": row["imageId"], "labels": row["labels"],
                    "envSha256": row["envSha256"], "hostConfigSha256": row["hostConfigSha256"], "mountsSha256": digest(row["mounts"]),
                    "expectedRunning": True, "startedAt": state["StartedAt"], "restartCount": row["restartCount"], "expectedHealth": None}
            require(expected["name"].startswith("br20261010-w01w07-") and
                    expected["labels"]["intruoyi.recovery.operation"] == original["operationId"], "RESOURCE_OBSERVER_UNOWNED_CONTAINER")
            rows = decode(runner.run(docker + ["inspect", expected["id"]]))
            require(len(rows) == 1, "RESOURCE_OBSERVER_CONTAINER_MISSING")
            item = rows[0]; observed = container_fact(item)
            container_ids.append(observed["id"])
            if generated:
                runtime.check_service(service, item, running=True)
            fact("container-%03d" % index, {"observed": observed, "execIds": item["ExecIDs"]})
            require(observed["id"] == expected["id"] and observed["name"] == "/" + expected["name"] and
                    observed["imageId"] == expected["imageId"] and observed["labels"] == expected["labels"] and
                    observed["envSha256"] == expected["envSha256"] and observed["hostConfigSha256"] == expected["hostConfigSha256"] and
                    digest(observed["mounts"]) == expected["mountsSha256"] and
                    item["State"]["Running"] is expected["expectedRunning"] and
                    item["State"]["StartedAt"] == expected["startedAt"] and item["RestartCount"] == expected["restartCount"] and
                    not item["State"]["Restarting"] and not item["State"]["Paused"] and not item["State"]["Dead"] and
                    not item["ExecIDs"], "RESOURCE_OBSERVER_CONTAINER_ACTIVE_OR_CHANGED")
            if expected["expectedHealth"] is not None:
                require(item["State"]["Health"]["Status"] == expected["expectedHealth"], "RESOURCE_OBSERVER_HEALTH_UNSETTLED")
            if expected["expectedRunning"]:
                pid = item["State"]["Pid"]
                native = process_stat(pid, actual["bootId"])
                require(native is not None, "RESOURCE_OBSERVER_CONTAINER_PID_NOT_VISIBLE")
                namespaces = {name: os.readlink("/proc/%s/ns/%s" % (pid, name)) for name in ("pid", "mnt", "net")}
                fact("container-native-%03d" % index, {"process": native, "namespaceIds": namespaces})
                if generated:
                    require(pid == state["Pid"], "RESOURCE_OBSERVER_CONTAINER_NATIVE_IDENTITY_MISMATCH")
                    native_before = native
                else:
                    require(native["processStartedAt"] == expected["nativeProcessStartedAt"] and
                            namespaces == expected["namespaceIds"], "RESOURCE_OBSERVER_CONTAINER_NATIVE_IDENTITY_MISMATCH")
            # A second inspect catches resource changes during the readback;
            # neither file hashes nor the preceding CLI exit substitute for it.
            repeated = decode(runner.run(docker + ["inspect", expected["id"]]))[0]
            require(container_fact(repeated) == observed and repeated["ExecIDs"] == item["ExecIDs"],
                    "RESOURCE_OBSERVER_CONTAINER_CHANGED_DURING_READBACK")
            if generated:
                require(process_stat(pid, actual["bootId"]) == native_before and
                        {name: os.readlink("/proc/%s/ns/%s" % (pid, name)) for name in ("pid", "mnt", "net")} == namespaces,
                        "RESOURCE_OBSERVER_CONTAINER_NATIVE_CHANGED")
        for kind in ("networks", "volumes"):
            for index, expected in enumerate(registered[kind]):
                name = expected["name"]
                require(name.startswith("br20261010-w01w07-") and
                        expected["labels"]["intruoyi.recovery.operation"] == original["operationId"], "RESOURCE_OBSERVER_UNOWNED_RESOURCE")
                row = decode(runner.run(docker + ["network" if kind == "networks" else "volume", "inspect", name]))[0]
                if kind == "networks":
                    observed = {"id": row["Id"], "name": row["Name"], "labels": row["Labels"], "containerIds": sorted(row["Containers"])}
                else:
                    observed = {"name": row["Name"], "labels": row["Labels"], "mountpoint": row["Mountpoint"]}
                fact(kind + "-%03d" % index, observed)
                binding_kind = expected["bindingKind"]
                if binding_kind == "W05_CONFIG":
                    config_value = read_pin(original["sourceOrTargetRef"])
                    require(config_value["schemaVersion"] == "RecoveryEnvironmentConfig/v1" and
                            observed["labels"] == expected["labels"], "RESOURCE_OBSERVER_RESOURCE_CHANGED")
                    if kind == "networks":
                        network = config_value["network"]
                        require(name == network["name"] and observed["containerIds"] == sorted(container_ids) and
                                row["Internal"] is True and row["EnableIPv6"] is False and row["Driver"] == "bridge" and
                                row["IPAM"]["Config"] == [{"Subnet": network["subnet"], "Gateway": network["gateway"]}] and
                                row["Options"]["com.docker.network.bridge.name"] == network["bridge"], "RESOURCE_OBSERVER_RESOURCE_CHANGED")
                    else:
                        approved = {mount["volume"] for service in config_value["services"] for mount in service["mounts"]}
                        require(name in approved and row["Driver"] == "local" and not row["Options"] and
                                safe_path(row["Mountpoint"], directory=True).is_relative_to(data_root),
                                "RESOURCE_OBSERVER_RESOURCE_CHANGED")
                else:
                    require(binding_kind == "PINNED_EXISTING" and observed == {key: value for key, value in expected.items()
                            if key != "bindingKind"}, "RESOURCE_OBSERVER_RESOURCE_CHANGED")
        # Read back the exact operation label to reject omitted resources. This
        # is a completeness check, not permission to adopt discovered objects.
        label = "label=intruoyi.recovery.operation=" + original["operationId"]
        for kind, command, expected_names in (
                ("containers", ["ps", "-aq", "--no-trunc"], container_ids),
                ("networks", ["network", "ls", "--format", "{{.Name}}"], [row["name"] for row in registered["networks"]]),
                ("volumes", ["volume", "ls", "--format", "{{.Name}}"], [row["name"] for row in registered["volumes"]])):
            actual_names = runner.run(docker + command + ["--filter", label]).decode("ascii").splitlines()
            fact("complete-" + kind, {"registered": sorted(expected_names), "observed": sorted(actual_names)})
            require(len(actual_names) == len(set(actual_names)) and sorted(actual_names) == sorted(expected_names),
                    "RESOURCE_OBSERVER_REGISTRATION_INCOMPLETE")
        for index, ref in enumerate(registered["files"]):
            path = safe_path(ref["path"])
            require(path.is_relative_to(Path(profile["privateNativePath"])), "RESOURCE_OBSERVER_FILE_OUTSIDE_TASK")
            verify_large_pin(ref, guard)
            fact("file-%03d" % index, {"actualFilePin": pin_file(path)})
        # Inputs/journals/files stay byte-identical across the entire readback.
        for ref in [registration_ref, config["sourceProfilePin"], request["requestPin"], request["originalExitPin"],
                    exit_record["intentPin"], binding["profilePin"], result_ref, profile["resourceManifestPin"],
                    *journal_pins, *input_pins, *registered["files"],
                    *(ref for child in registered["nativeProcesses"] for ref in child.values())]:
            verify_large_pin(ref, guard)
        fact("final-process-scope", process_reader(request["pid"], request["processStartedAt"], actual["bootId"]))
        return {"schemaVersion": "RecoveryControlResourceObservation/v1", **{key: request[key] for key in BOUND},
                "resourceTerminal": True, "originalPins": [*facts, *runner.pins], "failureCode": None}, 0
    except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, EnvironmentFailure) else "RESOURCE_OBSERVER_" + type(error).__name__.upper()
        fact("unknown", {"state": "TERMINAL_UNKNOWN", "failureCode": code})
        return {"schemaVersion": "RecoveryControlResourceObservation/v1", **{key: request[key] for key in BOUND},
                "resourceTerminal": None, "originalPins": [*facts, *runner.pins], "failureCode": code}, 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        request = decode(read_bytes(args.request))
        output = Path(args.output)
        require(output.is_absolute() and not output.exists() and output.parent == Path(args.request).parent,
                "RESOURCE_OBSERVER_OUTPUT_SCOPE_INVALID")
        safe_path(str(output.parent), directory=True)
        if os.name == "posix":
            require(output.parent.stat().st_uid == os.geteuid() and output.parent.stat().st_mode & 0o077 == 0,
                    "RESOURCE_OBSERVER_PRIVATE_EVIDENCE_REQUIRED")
        exact(request, REQUEST_FIELDS, "RESOURCE_OBSERVER_REQUEST_INVALID")
        try:
            ref, config = pinned_config()
        except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as error:
            code = error.code if isinstance(error, EnvironmentFailure) else "RESOURCE_OBSERVER_CONFIG_INVALID"
            fact_path = output.parent / "resource-fact-configuration-unknown.json"
            require(not fact_path.exists(), "RESOURCE_OBSERVER_FACT_EXISTS")
            atomic_json(fact_path, {"schemaVersion": "RecoveryControlResourceFact/v1", **{key: request[key] for key in BOUND},
                "observedAt": utc_now(), "monotonicNs": time.monotonic_ns(), "wallNs": time.time_ns(),
                "fact": {"state": "TERMINAL_UNKNOWN", "failureCode": code}})
            atomic_json(output, {"schemaVersion": "RecoveryControlResourceObservation/v1", **{key: request[key] for key in BOUND},
                "resourceTerminal": None, "originalPins": [pin_file(fact_path)], "failureCode": code})
            return 2
        observation, code = observe(request, ref, config, output.parent)
        atomic_json(output, observation)
        return code
    except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as error:
        print(error.code if isinstance(error, EnvironmentFailure) else "RESOURCE_OBSERVER_INPUT_INVALID", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
