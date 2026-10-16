"""Observer protocol tests; engineered records do not prove runtime recovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from test_recovery_environment_fixtures import LocalRecords, MODULE
from recovery_environment_contract import atomic_json, pin_file, read_pin, digest, EnvironmentFailure
import recovery_environment_observer as observer_module
from recovery_environment_observer import observe, process_scope, process_stat, container_fact, result_container
from recovery_environment_fence import controlled_handoff
from recovery_environment import check_controlled_preconditions


def observer_inputs(tmp_path):
    r = LocalRecords(tmp_path)
    root = r.root/"evidence"
    actual = dict(hostId="unit-host", bootId="unit-boot", uid=0,
                  pidNamespace="unit-pid", mntNamespace="unit-mnt", netNamespace="unit-net")
    request_pin = r.write("observer-original-request.json", r.request)
    request = dict(schemaVersion="RecoveryControlResourceObservationRequest/v1", operationId="unit-op", requestId="unit-request",
        requestPin=request_pin, attemptId="unit-attempt", observerEpoch="unit-epoch", clockDomain={"hostId": "unit-host", "bootId": "unit-boot"},
        pid=987654321, processStartedAt="linux:unit-boot:123", originalExitPin=r.sample,
        sourceOrTargetRef=r.request["sourceOrTargetRef"], selectedPointPin=r.point_pin,
        operationResultPath=str(root/"observer-operation-result.json"), deadlineMilliseconds=5000)
    profile = r.write("observer-native-profile.json", {"sourceProfilePin": r.sample,
        "resourceObserverPin": pin_file(MODULE/"recovery_environment_observer.py"), **{k: actual[k] for k in ("hostId", "bootId", "uid")}})
    intent = r.write("observer-native-intent.json", {"schemaVersion": "RecoveryControlNativeIntent/v1",
        **{k: request[k] for k in ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain")},
        "profilePin": profile, "startedMonotonicNs": time.monotonic_ns()-1000000})
    atomic_json(root/"native-original-exit.json", {"schemaVersion": "RecoveryControlNativeExit/v1",
        **{k: request[k] for k in ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain", "pid", "processStartedAt")},
        "intentPin": intent, "cliExitCode": 0, "processTerminal": True, "timedOut": False,
        "observedMonotonicNs": time.monotonic_ns(), "observedWallNs": time.time_ns()})
    request["originalExitPin"] = pin_file(root/"native-original-exit.json")
    atomic_json(root/"native-process-binding.json", {"schemaVersion": "RecoveryControlObservationBinding/v1",
        **{k: request[k] for k in ("operationId", "requestId", "requestPin", "attemptId", "observerEpoch", "clockDomain", "pid", "processStartedAt")},
        "intentPin": intent, "profilePin": profile})
    journal = r.write("observer-journal.json", {"schemaVersion": "RecoveryEnvironmentJournal/v1", "operationId": "unit-op", "state": "SUCCEEDED"})
    registration = {"schemaVersion": "RecoveryTaskResourceRegistration/v1",
        **{k: request[k] for k in ("operationId", "requestId", "requestPin", "sourceOrTargetRef", "selectedPointPin", "operationResultPath")},
        "containers": [], "networks": [], "volumes": [], "files": [], "journalPaths": [journal["path"]], "nativeProcesses": []}
    reg_pin = r.write("observer-registration.json", registration)
    manifest = r.write("observer-resource-manifest.json", {"schemaVersion": "RecoveryTaskResourceManifest/v1",
        "ownerThreadId": "01a124c0-a5fa-7e22-bd17-f37908b4827e", "containers": [], "networks": [], "volumes": [], "journalPaths": [journal["path"]]})
    source = r.write("observer-source-profile.json", {"schemaVersion": "RecoveryLocalEnvironmentRegistration/v1",
        "usableForExecution": True, "host": {"selectedExecutionHost": "unit-not-runtime"}, "resourceManifestPin": manifest,
        "privateNativePath": str(r.material)})
    config = {"schemaVersion": "RecoveryResourceObserverConfig/v1", "sourceProfilePin": source, "hostIdentity": actual,
        "pythonPin": pin_file(sys.executable), "observerPin": pin_file(MODULE/"recovery_environment_observer.py"),
        "moduleSourcePins": [pin_file(MODULE/name) for name in ("recovery_environment_observer.py", "recovery_environment_contract.py", "recovery_environment_runtime.py", "recovery_environment_supervisor.py")],
        "dockerPin": r.sample, "dockerEngineId": "unit-engine", "registrations": {request_pin["sha256"]: reg_pin}}
    return r, request, config, actual


def test_host_mismatch_is_unknown_with_actual_fact(tmp_path):
    r, request, config, actual = observer_inputs(tmp_path)
    config_ref = r.write("observer-config.json", config)
    result, code = observe(request, config_ref, config, r.root/"evidence", identity_reader=lambda: {**actual, "hostId": "other"})
    assert code == 2 and result["resourceTerminal"] is None
    assert result["failureCode"] == "RESOURCE_OBSERVER_HOST_MISMATCH" and result["originalPins"]
    assert read_pin(result["originalPins"][0])["fact"]["hostId"] == "other"


def bind_engineering_native_profile(r, request, config):
    intent = read_pin(read_pin(request["originalExitPin"])["intentPin"])
    profile = read_pin(intent["profilePin"]); profile["sourceProfilePin"] = config["sourceProfilePin"]
    config_ref = r.write("observer-config.json", config)
    profile.update(pythonPin=config["pythonPin"], evidenceRoot=str((r.root/"evidence").parent.parent),
                   environment={"RECOVERY_RESOURCE_OBSERVER_CONFIG_PIN": json.dumps(config_ref)})
    profile_ref = r.write("observer-profile-current.json", profile)
    intent["profilePin"] = profile_ref
    intent_ref = r.write("observer-intent-current.json", intent)
    exit_record = read_pin(request["originalExitPin"]); exit_record["intentPin"] = intent_ref
    atomic_json(r.root/"evidence"/"native-original-exit.json", exit_record)
    request["originalExitPin"] = pin_file(r.root/"evidence"/"native-original-exit.json")
    binding = read_pin(pin_file(r.root/"evidence"/"native-process-binding.json"))
    binding.update(intentPin=intent_ref, profilePin=profile_ref)
    atomic_json(r.root/"evidence"/"native-process-binding.json", binding)
    atomic_json(request["operationResultPath"], {"schemaVersion": "backup-restore-operation-result/v1", "operationId": "unit-op",
               "requestId": "unit-request", "action": "PREPARE_TARGET", "state": "SUCCEEDED"})
    return r.write("observer-config.json", config)


def test_zero_exit_without_approved_profile_or_resource_fact_is_unknown(tmp_path):
    r, request, config, actual = observer_inputs(tmp_path)
    config_ref = bind_engineering_native_profile(r, request, config)
    result, code = observe(request, config_ref, config, r.root/"evidence", identity_reader=lambda: actual,
                           process_reader=lambda *args: {"unitProtocolOnly": True})
    assert code == 2 and result["resourceTerminal"] is None
    assert result["failureCode"] == "RESOURCE_OBSERVER_REGISTERED_CONTAINER_REQUIRED"


@pytest.mark.parametrize("unsettled", [None, "journal", "exec", "changed", "omitted"])
def test_registered_resource_readback_and_unknown_boundaries(tmp_path, monkeypatch, unsettled):
    # Controlled in-memory command responses exercise parsing and gates only.
    # They are not an executable environment or independent runtime evidence.
    r, request, config, actual = observer_inputs(tmp_path)
    item = {"Id": "unit-container", "Name": "/br20261010-w01w07-unit", "Image": "unit-image",
        "Config": {"Labels": {"intruoyi.recovery.operation": "unit-op"}, "Env": []}, "Path": "unit", "Args": [],
        "HostConfig": {}, "Mounts": [], "NetworkSettings": {"Networks": {}, "Ports": {}}, "RestartCount": 0,
        "ExecIDs": [], "State": {"Status": "exited", "Running": False, "Paused": False, "Restarting": False,
        "OOMKilled": False, "Dead": False, "Pid": 0, "ExitCode": 0, "StartedAt": "unit-start", "FinishedAt": "unit-end"}}
    observed = container_fact(item)
    expected = {"bindingKind": "PINNED_EXISTING", "id": item["Id"], "name": item["Name"][1:], "imageId": item["Image"], "labels": item["Config"]["Labels"],
        "envSha256": observed["envSha256"], "hostConfigSha256": observed["hostConfigSha256"], "mountsSha256": digest([]),
        "expectedRunning": False, "startedAt": "unit-start", "restartCount": 0, "expectedHealth": None,
        "nativeProcessStartedAt": None, "namespaceIds": None}
    source = read_pin(config["sourceProfilePin"]); inventory = read_pin(source["resourceManifestPin"])
    inventory["containers"] = [expected]
    source["resourceManifestPin"] = r.write("observer-resource-manifest.json", inventory)
    config["sourceProfilePin"] = r.write("observer-source-profile.json", source)
    registration = read_pin(config["registrations"][request["requestPin"]["sha256"]]); registration["containers"] = [expected]
    config["registrations"][request["requestPin"]["sha256"]] = r.write("observer-registration.json", registration)
    config_ref = bind_engineering_native_profile(r, request, config)
    result_ref = pin_file(request["operationResultPath"])
    r.write("observer-journal.json", {"schemaVersion": "RecoveryRequestJournal/v1", "operationId": "unit-op",
        "requestId": "unit-request", "requestSha256": digest(r.request), "state": "RUNNING" if unsettled == "journal" else "SUCCEEDED",
        "resultPin": result_ref})
    class ReadOnlyResponses:
        def __init__(self, *args):
            self.pins = []; self.reads = 0
        def run(self, argv):
            if argv[-3:-1] == ["info", "--format"]:
                return json.dumps({"ID": "unit-engine", "OSType": "linux", "DockerRootDir": str(r.material)}).encode()
            if argv[-2] == "--filter":
                assert argv[-1] == "label=intruoyi.recovery.operation=unit-op"
                if "ps" in argv:
                    return b"unit-container\nunregistered-container\n" if unsettled == "omitted" else b"unit-container\n"
                return b""
            assert argv[-2:] == ["inspect", "unit-container"]
            self.reads += 1
            row = json.loads(json.dumps(item))
            if unsettled == "exec":
                row["ExecIDs"] = ["active-exec"]
            if unsettled == "changed" and self.reads == 2:
                row["RestartCount"] = 1
            return json.dumps([row]).encode()
    monkeypatch.setattr(observer_module, "CommandRunner", ReadOnlyResponses)
    result, code = observe(request, config_ref, config, r.root/"evidence", identity_reader=lambda: actual,
        process_reader=lambda *args: {"engineeringOnly": True})
    if unsettled is None:
        assert code == 0 and result["resourceTerminal"] is True and result["originalPins"]
        assert all(read_pin(ref)["originalExitPin"] == request["originalExitPin"] for ref in result["originalPins"])
    else:
        assert code == 2 and result["resourceTerminal"] is None
        assert result["failureCode"] == {"journal": "RESOURCE_OBSERVER_JOURNAL_UNKNOWN",
            "exec": "RESOURCE_OBSERVER_CONTAINER_ACTIVE_OR_CHANGED",
            "changed": "RESOURCE_OBSERVER_CONTAINER_CHANGED_DURING_READBACK",
            "omitted": "RESOURCE_OBSERVER_REGISTRATION_INCOMPLETE"}[unsettled]


@pytest.mark.skipif(sys.platform != "linux", reason="Native proc observation requires Linux; Windows does not establish it")
def test_actual_live_pid_is_not_terminal():
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(1)"], start_new_session=True)
    try:
        started = process_stat(child.pid, boot)["processStartedAt"]
        with pytest.raises(EnvironmentFailure, match="ORIGINAL_PID_ACTIVE_OR_REUSED"):
            process_scope(child.pid, started, boot)
    finally:
        child.wait(timeout=5)
    assert process_scope(child.pid, started, boot)["currentPidAbsent"] is True


def test_rehearsal_never_reads_controlled_context(tmp_path, monkeypatch):
    r = LocalRecords(tmp_path)
    monkeypatch.setenv("RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN", "invalid-json")
    assert check_controlled_preconditions(r.request, r.config, r.trust, object())["mode"] == "REHEARSAL"


def test_missing_controlled_handoff_is_explicit(tmp_path, monkeypatch):
    r = LocalRecords(tmp_path); r.request["mode"] = "CONTROLLED_RESTORE"
    monkeypatch.delenv("RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN", raising=False)
    with pytest.raises(EnvironmentFailure, match="CONTROLLED_FENCE_HANDOFF_REQUIRED"):
        controlled_handoff(r.request, r.config, r.policy, lambda: None, r.trust.schemas)


@pytest.mark.parametrize("field", ["operationId", "targetIdentityPin", "sourceScopePin", "selectedPointPin", "leaseRef"])
def test_controlled_other_scope_is_rejected_before_native_consumers(tmp_path, monkeypatch, field):
    r = LocalRecords(tmp_path); r.request["mode"] = "CONTROLLED_RESTORE"
    value = {"schemaVersion": "RecoveryControlledFenceHandoff/v1", "operationId": r.request["operationId"], "originalRequestPin": r.sample,
        "planPin": r.plan_pin, "targetIdentityPin": r.config["targetIdentityPin"], "sourceScopePin": r.config["sourceScopePin"],
        "selectedPointPin": r.point_pin, "leaseRef": r.request["leaseRef"], "sourceFencePin": r.sample, "sourceFencePointEvidencePin": r.sample}
    value[field] = "other-operation" if field == "operationId" else {**r.sample, "sha256": "0"*64}
    ref = r.write("other-operation-handoff.json", value)
    monkeypatch.setenv("RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN", json.dumps(ref))
    with pytest.raises(EnvironmentFailure, match="CONTROLLED_FENCE_HANDOFF_BINDING_INVALID"):
        controlled_handoff(r.request, r.config, r.policy, lambda: None, r.trust.schemas)


def test_health_observation_preserves_status_without_secret_output():
    item = {"Id": "unit-id", "Name": "/unit-name", "Image": "unit-image", "Config": {"Labels": {}, "Env": ["SECRET=unit"]},
        "Path": "unit", "Args": [], "HostConfig": {}, "Mounts": [], "NetworkSettings": {"Networks": {}, "Ports": {}},
        "RestartCount": 0, "State": {"Status": "running", "Running": True, "Paused": False, "Restarting": False,
        "OOMKilled": False, "Dead": False, "Pid": 1, "ExitCode": 0, "StartedAt": "unit-start", "FinishedAt": "unit-end",
        "Error": "secret-in-error", "Health": {"Status": "healthy", "Log": [{"Output": "secret-in-health"}]}}}
    observed = container_fact(item)
    assert observed["state"]["healthStatus"] == "healthy"
    assert "secret" not in json.dumps(observed).lower() and observed["envSha256"]


@pytest.mark.parametrize("action", ["PREPARE_TARGET", "START_APPLICATION"])
def test_new_container_identity_comes_from_same_request_w05_artifact(tmp_path, action):
    r = LocalRecords(tmp_path); original = dict(r.request, action=action)
    service = r.config["services"][0]
    row = {"id": "created-native-id", "name": "/" + service["name"]}
    proof = {"operationId": "unit-op", "targetIdentityPin": r.config["targetIdentityPin"],
        "configurationPin": r.config["configurationPin"], "configurationRef": original["sourceOrTargetRef"],
        "planPin": r.plan_pin, "leaseRef": original["leaseRef"], "services": [row]}
    data = {"targetIdentityPin": r.config["targetIdentityPin"], "configurationPin": r.config["configurationPin"]}
    if action == "PREPARE_TARGET":
        proof["schemaVersion"] = "RecoveryEnvironmentProof/v1"
        data.update(schemaVersion="RecoveryTarget/v1", resourcesProofPin=r.write("observer-produced-target.json", proof))
    else:
        restore_pin = r.sample; original["inputPins"] = {"restoreExecutionResult": restore_pin}
        proof.update(schemaVersion="RecoveryApplicationLaunch/v1", restoreResultPin=restore_pin, started=[row])
        data.update(schemaVersion="ApplicationStartResult/v1", state="SUCCEEDED",
            originalStartResultPins=[r.write("application-launch.json", proof)])
    input_pins, facts = [], []
    actual_row, runtime, actual_service = result_container({"bindingKind": "W05_RESULT", "role": service["role"], "name": service["name"]},
        {"data": data}, original, None, input_pins, lambda name, value: facts.append(value), lambda: None)
    assert actual_row == row and actual_service == service and runtime.operation_id == "unit-op" and input_pins and facts
    if action == "PREPARE_TARGET":
        original["inputPins"] = {"restorePlan": r.sample}
    else:
        original["inputPins"] = {"restoreExecutionResult": r.plan_pin}
    with pytest.raises(EnvironmentFailure, match="RESOURCE_OBSERVER_RESULT_PROOF_MISMATCH"):
        result_container({"bindingKind": "W05_RESULT", "role": service["role"], "name": service["name"]},
            {"data": data}, original, None, [], lambda *args: None, lambda: None)


def test_missing_configuration_cli_preserves_explicit_unknown(tmp_path):
    r, request, config, actual = observer_inputs(tmp_path)
    request_path = r.root/"evidence"/"resource-observer-request.json"
    output = r.root/"evidence"/"resource-observation.json"
    atomic_json(request_path, request)
    env = dict(os.environ); env.pop("RECOVERY_RESOURCE_OBSERVER_CONFIG_PIN", None)
    child = subprocess.run([sys.executable, str(MODULE/"recovery_environment_observer.py"), "--request", str(request_path),
        "--output", str(output)], env=env, capture_output=True, timeout=5)
    result = read_pin(pin_file(output))
    assert child.returncode == 2 and result["resourceTerminal"] is None and result["originalPins"]
    assert result["failureCode"] == "RESOURCE_OBSERVER_CONFIG_REQUIRED" and result["originalExitPin"] == request["originalExitPin"]
