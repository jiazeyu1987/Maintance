"""Private admission/version checks only; no real signed authority or business UI."""
import datetime as dt
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from test_recovery_verification_lab import fixture, admit
from core import VerificationError, canonical, file_pin, json_pin
from lab_boundary import ADMISSION_FIELDS
from evidence import EvidenceContext, report_invalidations
from bind_caller import bind
from collect_recovery import collect
from run_ui_recovery import prepare
from verify_recovery import policy_record


def reselect_admission(values, mutate):
    admission, selected, request, proof = values
    record = json_pin(admission)
    mutate(record)
    Path(admission["path"]).write_bytes(canonical(record))
    changed = file_pin(admission["path"])
    selected.remove(admission)
    selected.append(changed)
    return changed, selected, request, proof


def put(tmp_path, name, value):
    path = tmp_path / name
    path.write_bytes(canonical(value))
    return file_pin(str(path))


@pytest.mark.parametrize("version", ["RecoveryLabAdmission/v1", "RecoveryLabAdmission/v3"])
def test_only_explicit_v2_is_admitted(tmp_path, version):
    values = fixture(tmp_path, ("admission", "schemaVersion", version))
    with pytest.raises(VerificationError, match="RECORD_VERSION"):
        admit(values)


def test_v2_exact_fields_and_two_distinct_selected_copy_keys(tmp_path):
    values = fixture(tmp_path)
    values = reselect_admission(values, lambda record: record["copyProtectionEvidenceKeyPins"].append(record["authorityKeyPin"]))
    boundary = admit(values)
    assert set(boundary.admission) == set(ADMISSION_FIELDS.split())
    assert boundary.admission["schemaVersion"] == "RecoveryLabAdmission/v2"
    assert boundary.copy_protection(values[3], 300000)["sourceDeletionDenied"] is True


@pytest.mark.parametrize("mutation,code", [
    (lambda record: record.pop("copyProtectionEvidenceKeyPins"), "RECORD_FIELDS"),
    (lambda record: record.update(copyProtectionEvidenceKeyPins=None), "PIN_LIST_REQUIRED"),
    (lambda record: record.update(copyProtectionEvidenceKeyPins=[]), "PIN_LIST_REQUIRED"),
    (lambda record: record["copyProtectionEvidenceKeyPins"].append(record["copyProtectionEvidenceKeyPins"][0]), "DUPLICATE_PIN"),
    (lambda record: record.update(unknownField=True), "RECORD_FIELDS"),
])
def test_missing_empty_duplicate_or_unknown_key_selection_fails(tmp_path, mutation, code):
    values = reselect_admission(fixture(tmp_path), mutation)
    with pytest.raises(VerificationError, match=code):
        admit(values)


def test_distinct_pin_paths_cannot_duplicate_public_key_hash(tmp_path):
    values = fixture(tmp_path)
    key_pin = json_pin(values[0])["copyProtectionEvidenceKeyPins"][0]
    path = tmp_path / "same-public-key-different-path.pem"
    path.write_bytes(Path(key_pin["path"]).read_bytes())
    second = file_pin(str(path))
    values[1].append(second)
    values = reselect_admission(values, lambda record: record["copyProtectionEvidenceKeyPins"].append(second))
    with pytest.raises(VerificationError, match="LAB_COPY_SIGNING_KEYS_DUPLICATE"):
        admit(values)


def test_key_must_be_selected_independently_as_a_raw_original(tmp_path):
    values = fixture(tmp_path)
    values[1].remove(json_pin(values[0])["copyProtectionEvidenceKeyPins"][0])
    with pytest.raises(VerificationError, match="LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED"):
        admit(values)


def test_actual_copy_envelope_cannot_match_a_different_selected_key(tmp_path):
    values = fixture(tmp_path)
    values = reselect_admission(values, lambda record: record.update(copyProtectionEvidenceKeyPins=[record["authorityKeyPin"]]))
    with pytest.raises(VerificationError, match="LAB_COPY_SIGNING_KEY_NOT_SELECTED"):
        admit(values).copy_protection(values[3], 300000)


@pytest.mark.parametrize("entry", ["context", "binder"])
def test_verifier_context_and_binding_entry_reject_v1_before_execution(tmp_path, entry):
    values = fixture(tmp_path, ("admission", "schemaVersion", "RecoveryLabAdmission/v1"))
    admission = json_pin(values[0])
    request = dict(json_pin(values[2]), schemaVersion="backup-restore-operation/v1", requestId="engineering-request",
                   selectedPointPin=admission["sourceIdentityPin"], deadlineMilliseconds=10000,
                   inputPins={"restorePlan":admission["sourceIdentityPin"],
                              "restoreExecutionResult":admission["sourceIdentityPin"],
                              "applicationStartResult":admission["sourceIdentityPin"]})
    request_pin = put(tmp_path, "full-request.json", request)
    source = put(tmp_path, "business-source-scope.json", {
        "schemaVersion":"RecoverySourceScope/v1","machineId":"engineering-host",
        "sourceIdentityPin":admission["sourceIdentityPin"],"containerIds":[],"containerNames":[],
        "writerContainerIds":[],"volumeNames":[],"networkNames":[],"materialPaths":[],"endpointHosts":[]})
    schema = file_pin(str(Path(__file__).resolve().parents[2] / "doc/tasks/20261010-backup-restore-modular-development/record-schemas.json"))
    selection = {"schemaVersion":"RecoveryLabCallerSelection/v1","callerThreadId":"engineering-caller",
                 "producerThreadIds":["engineering-producer"],"requestPin":request_pin,"schemaPin":schema,
                 "sourceScopePin":source,"executableScopePin":source,"runTracePin":source,
                 "independentOriginalPins":[*values[1],source,request_pin,schema],
                 "labAdmissionPin":values[0],"validUntil":admission["validUntil"]}
    selected = put(tmp_path, "selection.json", selection)
    output = tmp_path / "never-bound.json"
    with pytest.raises(VerificationError, match="RECORD_VERSION"):
        if entry == "binder":
            bind(request_pin["path"], str(output), selected)
        else:
            from core import Deadline
            EvidenceContext(request, request_pin, selected, Deadline(10000), selected_binding=
                            dict(selection, schemaVersion="RecoveryLabCallerBinding/v1"))
    assert not output.exists()


def test_data_collector_rejects_v1_before_data_or_output(tmp_path):
    values = fixture(tmp_path, ("admission", "schemaVersion", "RecoveryLabAdmission/v1"))
    admission = json_pin(values[0])
    dummy = admission["targetIdentityPin"]
    config = {"schemaVersion":"RecoveryCollectionConfig/v1","kind":"data","operationId":"engineering-op",
              "restoreId":"engineering-restore","recoveryPoint":"engineering-point","targetIdentityPin":dummy,
              "verificationTargetPin":dummy,"authorizationPin":dummy,"deadlineMilliseconds":10000,"settings":{}}
    config_pin = put(tmp_path, "data-config.json", config)
    trust = put(tmp_path, "data-trust.json", {
        "schemaVersion":"RecoveryLabCollectionCallerBinding/v1","callerThreadId":"engineering-caller",
        "producerThreadIds":["engineering-producer"],"configPin":config_pin,"authorizationPin":dummy,
        "targetIdentityPin":dummy,"toolPins":[],"independentOriginalPins":values[1],
        "labAdmissionPin":values[0],"validUntil":admission["validUntil"]})
    output = tmp_path / "never-collected.json"
    with pytest.raises(VerificationError, match="RECORD_VERSION"):
        collect(config_pin["path"], str(output), trust)
    assert not output.exists()


def test_ui_prepare_rejects_v1_before_browser_or_service_access(tmp_path):
    values = fixture(tmp_path, ("admission", "schemaVersion", "RecoveryLabAdmission/v1"))
    admission = json_pin(values[0])
    dummy = admission["targetIdentityPin"]
    flows = []
    for name in ("query", "view", "download", "deleted"):
        steps = [{"kind":"text","selector":"#engineering","expected":"engineering-only"}]
        if name in ("view", "download"):
            steps.append({"kind":"objectReference","selector":"#engineering-reference",
                          "sourcePathId":"engineering","sourceSelector":"#engineering-source"})
        if name == "download":
            steps.append({"kind":"download","selector":"#engineering-download","expectedBytes":1,"expectedSha256":"0"*64})
        if name == "deleted": steps.append({"kind":"count","selector":"#engineering-deleted","expected":0})
        flows.append({"pathId":name,"entrySteps":[{"kind":"click","selector":"#engineering-entry"}],"steps":steps})
    login = {name:"#engineering" for name in ("tenantSelector","usernameSelector","passwordSelector",
                                               "submitSelector","profileUsernameSelector")}
    login["profileEntrySteps"] = [{"kind":"click","selector":"#engineering-profile"}]
    config = {"schemaVersion":"RecoveryUiScenarioConfig/v1","runId":"engineering-run","phase":"target",
              "operationId":"engineering-op","restoreId":"engineering-restore","recoveryPoint":"engineering-point",
              "sourceOrigin":"http://127.0.0.1:18081","targetOrigin":"http://127.0.0.1:18082",
              "baseUrl":"http://127.0.0.1:18082/login","apiOrigin":"http://127.0.0.1:18082",
              "allowedOrigins":["http://127.0.0.1:18082"],"objectOrigins":[],"writeApiPaths":[],
              "browserExecutable":sys.executable,"passwordEnv":"UNPROVIDED_ENGINEERING_SECRET",
              "targetIdentityPin":dummy,"verificationTargetPin":dummy,"authorizationPin":dummy,
              "deadlineMilliseconds":10000,"login":login,"flows":flows,"schemaPin":dummy,"prerequisites":{}}
    config_pin = put(tmp_path, "ui-config.json", config)
    trust = put(tmp_path, "ui-trust.json", {
        "schemaVersion":"RecoveryLabUiCallerBinding/v1","callerThreadId":"engineering-caller",
        "producerThreadIds":["engineering-producer"],"configPin":config_pin,"authorizationPin":dummy,
        "targetIdentityPin":dummy,"toolPins":[],"independentOriginalPins":values[1],
        "labAdmissionPin":values[0],"validUntil":admission["validUntil"]})
    with pytest.raises(VerificationError, match="RECORD_VERSION"):
        prepare(config_pin["path"], trust)


def policy_v2(pin):
    policy = {name:pin for name in ("recoveryTargetPin","verificationTargetPin","dataBaselinePin",
        "dataObservationPin","protectionBeforePin","protectionAfterPin","playwrightObservationPin",
        "timingObservationPin","derivedBaselinePin")}
    return dict(policy, schemaVersion="RecoveryVerificationPolicy/v2", maxAgeMilliseconds=300000,
                rtoObjectiveMilliseconds=None,rpoObjectiveMilliseconds=None,requiredUserPaths=[],protectedScopes=[],
                requireDeletedReferenceObjects=False,controlledEligibilityPin=None)


@pytest.mark.parametrize("version", ["RecoveryVerificationPolicy/v2", "RecoveryVerificationPolicy/v1"])
def test_actual_exact_policy_v2_preserves_unknown_objectives(tmp_path, version):
    pin = put(tmp_path, "engineering-original.json", {"engineeringOnly":True})
    policy = dict(policy_v2(pin), schemaVersion=version)
    context = SimpleNamespace(request={"policyPin":pin,"mode":"REHEARSAL"},record=lambda _:policy)
    if version.endswith("/v1"):
        with pytest.raises(VerificationError, match="RECORD_VERSION"): policy_record(context)
    else:
        assert policy_record(context) == policy
        assert policy["rtoObjectiveMilliseconds"] is policy["rpoObjectiveMilliseconds"] is None


@pytest.mark.parametrize("version,reason", [
    ("RecoveryLabAdmission/v2","dataEvidencePins_LAB_AUTHORITY_EXPIRED"),
    ("RecoveryLabAdmission/v1","dataEvidencePins_LAB_ADMISSION_VERSION_UNSUPPORTED")])
def test_report_currency_checks_v2_expiry_and_invalidates_old_version(tmp_path, version, reason):
    values = fixture(tmp_path, ("admission", "validUntil", "2020-01-01T00:00:00Z"))
    values = reselect_admission(values, lambda record: record.update(schemaVersion=version))
    pin = values[0]
    binding_pin = put(tmp_path, "engineering-report-binding.json", {"engineeringOnly":"report traversal"})
    stamp = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    current = {name:binding_pin for name in ("planPin","targetIdentityPin","sourceScopePin","restoreResultPin","applicationStartPin")}
    current.update(backupAndChainPins=[],toolAndVersionPins=[],targetApprovalRefs=[],operationId="engineering-op",
                   restoreId="engineering-restore",mode="REHEARSAL",reportGeneratedAt=stamp)
    report = {key:value for key,value in current.items() if key != "reportGeneratedAt"}
    report.update(dataEvidencePins=[pin],playwrightEvidencePins=[],rtoObservation={},rpoObservation={})
    assert reason in report_invalidations(report, current, 300000, stamp)
