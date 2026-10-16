from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import pytest

from test_recovery_environment_fixtures import LocalRecords
from test_recovery_environment_contract import rejects
from recovery_application import match_restore
from recovery_environment_contract import digest, read_pin, pin_file
from recovery_environment_runtime import CommandRunner
from recovery_application_restore import verify_dependency
from recovery_application_protection import validate_write_protection, protect_application


@pytest.fixture
def records(tmp_path):
    records = LocalRecords(tmp_path)
    records.start_inputs()
    return records


def test_start_gate_preserves_complete_plan_versions_and_consumes_original_exits(records):
    restore, _, target, _, plan = match_restore(records.request, records.config, records.policy, records.trust)
    assert restore["restoreId"] == "unit-restore"
    # W04 may carry tools/versions beyond W05's image set. They must survive.
    assert target["versionPins"] == plan["supportedVersionPins"]
    assert len(target["versionPins"]) > len(records.config["imagePins"])


@pytest.mark.parametrize("field,value,code", [("state", "TERMINAL_UNKNOWN", "RESTORE_NOT_SUCCEEDED_OR_NOT_PROTECTED"),
    ("writeProtectionState", "RELEASED", "RESTORE_NOT_SUCCEEDED_OR_NOT_PROTECTED"),
    ("operationId", "another-operation", "RESTORE_TARGET_CONFIG_MISMATCH"),
    ("restoreId", "another-restore", "RESTORE_POINT_OR_ID_MISMATCH"),
    ("recoveryPoint", "another-point", "RESTORE_POINT_OR_ID_MISMATCH"),
    ("dbStepEvidencePins", [], "RESTORE_EXECUTION_ORIGINALS_MISSING"),
    ("objectStepEvidencePins", [], "RESTORE_EXECUTION_ORIGINALS_MISSING")])
def test_start_gate_rejects_failed_unprotected_mismatched_or_unproved_restore(records, field, value, code):
    records.restore[field] = value
    records.repin_start()
    rejects(code, match_restore, records.request, records.config, records.policy, records.trust)


def test_start_gate_rejects_missing_original_exit(records):
    records.restore["originalInvocationPins"] = records.restore["originalInvocationPins"][:-1]
    records.repin_start()
    rejects("ORIGINAL_EXECUTOR_TERMINATION_MISSING", match_restore, records.request, records.config, records.policy, records.trust)


def test_start_gate_rejects_wrong_versions(records):
    records.target["versionPins"] = records.config["imagePins"]
    records.repin_start()
    rejects("RESTORE_VERSION_PINS_MISMATCH", match_restore, records.request, records.config, records.policy, records.trust)


@pytest.mark.parametrize("field,value,code", [("observedAt", "2000-01-01T00:00:00Z", "PREPARED_ENVIRONMENT_STALE"),
    ("configurationRef", None, "PREPARED_ENVIRONMENT_RESTORE_MISMATCH"),
    ("recoveryPoint", "other-point", "PREPARED_ENVIRONMENT_RESTORE_MISMATCH")])
def test_start_gate_rejects_stale_or_different_prepared_target(records, field, value, code):
    proof = read_pin(records.target["resourcesProofPin"])
    proof[field] = value
    records.target["resourcesProofPin"] = records.write("changed-proof.json", proof)
    records.repin_start()
    rejects(code, match_restore, records.request, records.config, records.policy, records.trust)


def test_start_gate_rejects_policy_not_used_by_prepare(records):
    proof = read_pin(records.target["sideEffectIsolationPin"])
    proof["startupInventoryPins"] = []
    records.target["sideEffectIsolationPin"] = records.write("changed-side-effects.json", proof)
    records.repin_start()
    rejects("PREPARED_SIDE_EFFECT_POLICY_MISMATCH", match_restore, records.request, records.config, records.policy, records.trust)


def test_arbitrary_zero_exit_is_not_a_restore_step(records):
    records.restore["originalInvocationPins"] = records.original_child()
    records.repin_start()
    rejects("RESTORE_STEP_NOT_BOUND_TO_ACTUAL_WORKER", match_restore, records.request, records.config, records.policy, records.trust)


def test_worker_request_other_target_is_rejected(records):
    original = next(pin for pin in records.restore["originalInvocationPins"]
                    if pin["path"].endswith("step-database_full\\request.json") or pin["path"].endswith("step-database_full/request.json"))
    child = read_pin(original)
    child["recoveryTargetPin"] = records.sample
    changed = records.write("other-target-worker.json", child)
    intent_pin = next(pin for pin in records.restore["originalInvocationPins"]
                      if pin["path"].endswith("step-database_full\\intent.json") or pin["path"].endswith("step-database_full/intent.json"))
    intent = read_pin(intent_pin)
    intent["requestPin"] = changed
    records.write_at(__import__("pathlib").Path(intent_pin["path"]), intent)
    updated_intent = __import__("recovery_environment_contract").pin_file(intent_pin["path"])
    terminal_pin = next(pin for pin in records.restore["originalInvocationPins"]
                        if pin["path"].endswith("step-database_full\\exit.json") or pin["path"].endswith("step-database_full/exit.json"))
    terminal = read_pin(terminal_pin)
    terminal["intentPin"] = updated_intent
    updated_terminal = records.write_at(__import__("pathlib").Path(terminal_pin["path"]), terminal)
    records.restore["originalInvocationPins"] = [changed if pin == original else updated_intent if pin == intent_pin
                                                  else updated_terminal if pin == terminal_pin else pin
                                                  for pin in records.restore["originalInvocationPins"]]
    records.repin_start()
    rejects("RESTORE_WORKER_SCOPE_MISMATCH", match_restore, records.request, records.config, records.policy, records.trust)


def test_unrelated_database_and_consistency_bytes_do_not_admit_start(records):
    records.restore["dbStepEvidencePins"] = [records.sample]
    records.repin_start()
    rejects("RESTORE_STEP_NOT_BOUND_TO_ACTUAL_WORKER", match_restore, records.request, records.config, records.policy, records.trust)


def test_dependency_restart_without_w04_physical_originals_is_rejected(records):
    prepared = {key: key for key in ("id", "name", "imageId", "labels", "envSha256", "hostConfigSha256", "mounts", "commandSha256", "restartCount")}
    prepared["state"] = {"StartedAt": "2026-10-10T10:00:00Z"}
    current = deepcopy(prepared)
    assert verify_dependency(prepared, current, "minio", None, records.config, records.policy, lambda: None) is None
    current["state"]["StartedAt"] = "2026-10-10T11:00:00Z"
    rejects("PREPARED_DEPENDENCY_RESTART_UNPROVEN", verify_dependency, prepared, current, "minio", None,
            records.config, records.policy, lambda: None)
    current["imageId"] = "another-image"
    rejects("PREPARED_DEPENDENCY_CHANGED", verify_dependency, prepared, current, "minio", None,
            records.config, records.policy, lambda: None)


def test_missing_real_write_protection_coverage_fails_fast(records):
    spec = read_pin(records.policy["applicationWriteProtectionPin"])
    spec["requiredScopes"] = ["EXTERNAL_DISPATCH"]
    records.policy["applicationWriteProtectionPin"] = records.write("incomplete-write-policy.json", spec)
    rejects("APPLICATION_WRITE_PROTECTION_COVERAGE_INCOMPLETE", validate_write_protection,
            records.config, records.policy, lambda: None)


def test_physical_restart_requires_exact_container_volume_and_real_command_times(records):
    # Protocol unit records only; this test does not start or restore MinIO.
    prepared = {key: key for key in ("id", "name", "imageId", "envSha256", "hostConfigSha256", "commandSha256", "restartCount")}
    prepared.update(labels={"unit": "only"}, mounts=[{"Destination": "/data", "Type": "volume",
                    "Name": "unit-only-volume", "Source": "/unit-only-mount"}],
                    state={"StartedAt": "2026-10-10T10:00:00Z"})
    current = deepcopy(prepared)
    current["state"]["StartedAt"] = "2026-10-10T11:00:00Z"
    approval = {"schemaVersion": "RecoveryPhysicalStartupApproval/v1", "approved": True,
                "targetIdentityPin": records.config["targetIdentityPin"], "recoveryPoint": records.plan["recoveryPoint"],
                "imageId": prepared["imageId"], "validFrom": "2026-10-10T09:00:00Z", "validUntil": "2026-10-10T12:00:00Z",
                **{key: True for key in ("notificationAbsent", "lifecycleAbsent", "replicationAbsent",
                    "externalTierAbsent", "pendingJobsAbsent", "credentialsCompatible")}}
    approval_pin = records.write("unit-physical-approval.json", approval)
    records.policy["physicalRestartPolicyPin"] = records.write("unit-restart-policy.json", {
        "schemaVersion": "RecoveryPhysicalRestartPolicy/v1", "targetIdentityPin": records.config["targetIdentityPin"],
        "approvalPin": approval_pin, "storageStopSeconds": 10, "minioDataMount": "/data"})
    physical_pin = records.write("unit-physical-result.json", {"purpose": "protocol test only"})
    stop = {"containerId": prepared["id"], "preserveExisting": True, "approvalPin": approval_pin,
            "volumeIdentity": {"Name": "unit-only-volume", "Mountpoint": "/unit-only-mount",
                               "Labels": prepared["labels"], "Driver": "local", "Options": None}}
    records.write("physical-stop-intent.json", stop)
    docker = [records.config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock"]
    native = [{"mutation": True, "argvSha256": digest(docker+["stop", "--time", "10", prepared["id"]]),
               "startedAt": "2026-10-10T10:59:00Z", "finishedAt": "2026-10-10T10:59:01Z"},
              {"mutation": True, "argvSha256": digest(docker+["start", prepared["id"]]),
               "startedAt": "2026-10-10T10:59:59Z", "finishedAt": "2026-10-10T11:00:01Z"}]
    step = {"pin": physical_pin, "original": {"policyPin": records.request["policyPin"]}, "native": native,
            "result": {"data": {"recoveryPoint": records.plan["recoveryPoint"]}}}
    observed = verify_dependency(prepared, current, "minio", step, records.config, records.policy, lambda: None)
    assert observed["currentStartedAt"] == current["state"]["StartedAt"]
    current["state"]["StartedAt"] = "2026-10-10T11:01:00Z"
    rejects("PHYSICAL_RESTART_ORIGINAL_EXIT_UNPROVEN", verify_dependency,
            prepared, current, "minio", step, records.config, records.policy, lambda: None)
    current["state"]["StartedAt"] = "2026-10-10T11:00:00Z"
    stop["volumeIdentity"]["Name"] = "different-volume"
    records.write("physical-stop-intent.json", stop)
    rejects("PHYSICAL_RESTART_VOLUME_MISMATCH", verify_dependency,
            prepared, current, "minio", step, records.config, records.policy, lambda: None)


def test_no_declared_write_protection_policy_is_rejected(records):
    records.policy["applicationWriteProtectionPin"] = None
    rejects("APPLICATION_WRITE_PROTECTION_POLICY_REQUIRED", validate_write_protection,
            records.config, records.policy, lambda: None)


@pytest.mark.parametrize("phase", ["BEFORE_START", "AFTER_START"])
def test_application_protection_rejects_missing_scope_observations(records, phase):
    # Real local subprocess, engineered protocol observations; never runtime acceptance.
    spec = read_pin(records.policy["applicationWriteProtectionPin"])
    script = records.material/"unit-protection-protocol.py"
    script.write_text('''import json,sys,datetime
p=json.load(sys.stdin)
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
o={k:p[k] for k in ('phase','operationId','restoreId','targetIdentityPin','recoveryPoint','policyPin','containers')}
o.update(schemaVersion='RecoveryApplicationWriteProtectionObservation/v1',state='ENFORCED',observedAt=now(),scopeObservations=[])
json.dump(o,sys.stdout)
''', encoding="utf-8")
    spec["enforceScriptPin"] = spec["observeScriptPin"] = pin_file(script)
    records.policy["applicationWriteProtectionPin"] = records.write("unit-observation-policy.json", spec)
    runner = CommandRunner(records.root/"evidence", time.monotonic()+10, lambda: None)
    runtime = SimpleNamespace(runner=runner, identities={"minio": "unit-container"})
    rejects("APPLICATION_PROTECTION_OBSERVATIONS_INCOMPLETE", protect_application,
            records.request, records.config, records.policy, runtime, records.restore, phase)
    assert read_pin(runner.pins[-1])["actualExitCode"] == 0
    assert not (runner.root/("application-write-protection-"+phase.lower()+".json")).exists()


@pytest.mark.parametrize("defect,code", [("NONE", None),
    ("CHANGED_DATA", "APPLICATION_PROTECTION_PROBE_CHANGED_DATA"),
    ("OTHER_CONTAINER", "APPLICATION_WRITE_REFUSAL_UNBOUND"),
    ("UNKNOWN_EXIT", "APPLICATION_WRITE_REFUSAL_TERMINATION_UNPROVEN")])
def test_protection_protocol_consumes_observed_terminal_pins(records, defect, code):
    # Gate engineering only. The child refuses a unit test operation; no business system is accessed.
    spec = read_pin(records.policy["applicationWriteProtectionPin"])
    template = records.write("unit-protection-template.json", {
        "scopes": spec["requiredScopes"], "enforcementPin": records.sample, "defect": defect})
    script = records.material/"unit-refusal-protocol.py"
    program = '''import json,sys,datetime,subprocess,hashlib,pathlib
p=json.load(sys.stdin)
t=json.load(open(TEMPLATE,encoding='utf-8'))
root=pathlib.Path(TEMPLATE).parent
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
def pin(path,value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    path.write_bytes(raw)
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
argv=[sys.executable,'-I','-c','raise SystemExit(7)']
started=now()
child=subprocess.run(argv,capture_output=True)
invocation=dict(schemaVersion='RecoveryEnvironmentInvocation/v1',mutation=True,actualExitCode=child.returncode,
                state='FAILED_RETAINED',startedAt=started,finishedAt=now())
if t['defect']=='UNKNOWN_EXIT':invocation.update(actualExitCode=None,state='TERMINAL_UNKNOWN')
original=pin(root/'unit-refusal-original.json',invocation)
o={k:p[k] for k in ('phase','operationId','restoreId','targetIdentityPin','recoveryPoint','policyPin','containers')}
o.update(schemaVersion='RecoveryApplicationWriteProtectionObservation/v1',state='ENFORCED',observedAt=now(),scopeObservations=[])
for scope in t['scopes']:
    proof={k:p[k] for k in ('phase','operationId','targetIdentityPin','recoveryPoint','containers')}
    proof.update(schemaVersion='RecoveryApplicationWriteRefusal/v1',scope=scope,denied=True,
                 beforeFingerprint='a'*64,afterFingerprint='a'*64,originalInvocationPins=[original])
    if t['defect']=='OTHER_CONTAINER':proof['containers']={'minio':'other-unit-container'}
    rejection=pin(root/('unit-refusal-'+scope+'.json'),proof)
    o['scopeObservations'].append(dict(scope=scope,enforcementPin=t['enforcementPin'],beforeFingerprint='a'*64,
        afterFingerprint=('b' if t['defect']=='CHANGED_DATA' else 'a')*64,rejectionObservationPins=[rejection]))
json.dump(o,sys.stdout)
'''
    script.write_text("TEMPLATE = "+repr(template["path"])+"\n"+program, encoding="utf-8")
    spec["enforceScriptPin"] = spec["observeScriptPin"] = pin_file(script)
    records.policy["applicationWriteProtectionPin"] = records.write("unit-refusal-policy.json", spec)
    runner = CommandRunner(records.root/"evidence", time.monotonic()+10, lambda: None)
    runtime = SimpleNamespace(runner=runner, identities={"minio": "unit-container"})
    if code:
        rejects(code, protect_application, records.request, records.config, records.policy, runtime, records.restore, "AFTER_START")
        assert not (runner.root/"application-write-protection-after_start.json").exists()
    else:
        pin = protect_application(records.request, records.config, records.policy, runtime, records.restore, "AFTER_START")
        assert read_pin(pin)["originalInvocationPin"] == runner.pins[-1]
    assert read_pin(runner.pins[-1])["mutation"] is True
