"""Engineering regression checks; no browser, network or rehearsal acceptance."""
import base64
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_recovery_verification_lab import fixture, admit
from core import Deadline, VerificationError, canonical, file_pin, json_pin, pin_key
from verify_recovery import authorize
from collection_originals import collection_invocation
from ruoyi_ui import api_business_body

MODULE = Path(__file__).resolve().parents[1] / "recovery_verification"


def approval_context(values):
    lab = admit(values)
    return SimpleNamespace(lab=lab, request=json_pin(values[2]),
                           target_pin=lab.admission["targetIdentityPin"],
                           record=lab.original, deadline=lab.deadline)


@pytest.mark.parametrize("repository", [False, True])
def test_current_grant_and_separate_approval_are_both_required_and_accepted(tmp_path, repository):
    context = approval_context(fixture(tmp_path, repository_authority=repository))
    refs = context.request["authorizationRefs"]
    authorize(context, refs)
    with pytest.raises(VerificationError, match="VERIFICATION_AUTHORIZATION_REQUIRED"):
        authorize(context, refs[:1])
    with pytest.raises(VerificationError, match="LAB_CURRENT_GRANT_REQUIRED"):
        authorize(context, refs[1:])
    with pytest.raises(VerificationError, match="DUPLICATE_PIN"):
        authorize(context, refs + refs[:1])


@pytest.mark.parametrize("field,value,code", [
    ("schemaVersion", "UnknownApproval/v1", "RECORD_VERSION"),
    ("operationId", "other", "AUTHORIZATION_ACTION_MISMATCH"),
    ("action", "READBACK_VERIFY", "AUTHORIZATION_ACTION_MISMATCH"),
    ("tenantId", 1, "AUTHORIZATION_PROTECTED_TENANT"),
    ("tenantId", True, "AUTHORIZATION_PROTECTED_TENANT"),
    ("writesAllowed", 1, "AUTHORIZATION_PROTECTED_TENANT"),
    ("validFrom", "2099-01-01T00:00:00Z", "AUTHORIZATION_WINDOW_EXPIRED"),
    ("validUntil", "2020-01-01T00:00:00Z", "AUTHORIZATION_WINDOW_EXPIRED"),
])
def test_every_other_ref_is_an_exact_current_verification_approval(tmp_path, field, value, code):
    context = approval_context(fixture(tmp_path, ("approval", field, value)))
    with pytest.raises(VerificationError, match=code):
        authorize(context, context.request["authorizationRefs"])


def test_target_mismatch_and_unselected_approval_fail(tmp_path):
    values = fixture(tmp_path)
    context = approval_context(values)
    context.target_pin = context.lab.admission["sourceIdentityPin"]
    with pytest.raises(VerificationError, match="LAB_AUTHORIZATION_TARGET_MISMATCH"):
        authorize(context, context.request["authorizationRefs"])
    context.target_pin = context.lab.admission["targetIdentityPin"]
    context.lab.selected.remove(pin_key(context.request["authorizationRefs"][1]))
    with pytest.raises(VerificationError, match="LAB_APPROVAL_NOT_INDEPENDENTLY_SELECTED"):
        authorize(context, context.request["authorizationRefs"])


def test_changed_current_grant_cannot_be_rescued_by_valid_approval(tmp_path):
    context = approval_context(fixture(tmp_path))
    Path(context.lab.context["authorizationPin"]["path"]).write_bytes(b"changed grant")
    with pytest.raises(VerificationError, match="PIN_MISMATCH"):
        authorize(context, context.request["authorizationRefs"])


@pytest.mark.parametrize("change,code", [
    (("acl", "archiveRoot", "/other/archives"), "LAB_COPY_ARCHIVE_ROOT_MISMATCH"),
    (("acl", "archiveRoot", "/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07/x/../archives"), "LAB_COPY_ARCHIVE_ROOT_MISMATCH"),
    (("readback", "uncRoot", "\\\\172.30.30.57\\brlab-20261012-readback"), "LAB_COPY_ENDPOINT_OUT_OF_SCOPE"),
    (("readback", "uncRoot", "\\\\172.30.30.59\\shared"), "LAB_COPY_ENDPOINT_OUT_OF_SCOPE"),
    (("readback", "encrypted", False), "LAB_COPY_SECURE_READBACK_REQUIRED"),
    (("readback", "signingRequired", False), "LAB_COPY_SECURE_READBACK_REQUIRED"),
    (("readback", "independentConnectionId", ""), "TEXT_REQUIRED"),
    (("readback", "observedAt", "2020-01-01T00:00:00Z"), "LAB_COPY_EVIDENCE_STALE"),
    (("readback", "observedAt", "2099-01-01T00:00:00Z"), "LAB_COPY_EVIDENCE_STALE"),
    (("deletion", "deleteDenied", False), "LAB_COPY_PROBES_REQUIRED"),
    (("key-access", "recoveryKeysAvailable", False), "LAB_COPY_PROBES_REQUIRED"),
    (("deletion", "probeOriginalPin", None), "RECORD_FIELDS"),
    (("accounts", "writer", "source"), "DUPLICATE_PIN"),
    (("accounts", "reader", "writer"), "DUPLICATE_PIN"),
    (("account-bytes", "writer", "source"), "LAB_COPY_INDEPENDENT_ACCOUNTS_REQUIRED"),
    (("acl", "labScopePin", None), "RECORD_FIELDS"),
    (("readback", "readerAccountPin", None), "RECORD_FIELDS"),
    (("deletion", "accountPin", None), "RECORD_FIELDS"),
])
def test_current_w03_nested_copy_shapes_enforce_semantics(tmp_path, change, code):
    values = fixture(tmp_path, change)
    with pytest.raises(VerificationError, match=code):
        admit(values).copy_protection(values[3], 300000)


def test_opaque_nested_original_and_wrong_selected_key_fail(tmp_path):
    values = fixture(tmp_path)
    boundary = admit(values)
    outer = json_pin(values[3])["payload"]
    opaque_path = tmp_path / "opaque-acl.json"
    opaque_path.write_bytes(canonical({"engineeringOnly": "acl"}))
    opaque_pin = file_pin(str(opaque_path))
    boundary.selected.add(pin_key(opaque_pin))
    with pytest.raises(VerificationError, match="RECORD_FIELDS"):
        boundary.copy_signed(opaque_pin)
    boundary.admission["copyProtectionEvidenceKeyPins"] = [boundary.admission["authorityKeyPin"]]
    with pytest.raises(VerificationError, match="LAB_COPY_SIGNING_KEY_NOT_SELECTED"):
        boundary.copy_signed(outer["aclEvidencePin"])


def test_signature_account_and_probe_bytes_are_independently_checked(tmp_path):
    values = fixture(tmp_path)
    boundary = admit(values)
    proof = boundary.copy_signed(values[3])
    acl = boundary.copy_signed(proof["aclEvidencePin"])
    readback = boundary.copy_signed(proof["readbackEndpointEvidencePin"])
    # Current W03 signed shape is admitted with a distinct selected copy key.
    assert boundary.copy_protection(values[3], 300000)["independentFailureDomain"] is False
    Path(readback["readbackOriginalPin"]["path"]).write_bytes(b"changed probe")
    with pytest.raises(VerificationError, match="PIN_MISMATCH"):
        boundary.copy_protection(values[3], 300000)
    # A newly selected envelope with an invalid signature still fails.
    envelope = json_pin(proof["aclEvidencePin"])
    envelope["signature"] = base64.b64encode(b"x" * 64).decode()
    bad_path = tmp_path / "bad-signature.json"
    bad_path.write_bytes(canonical(envelope))
    bad_pin = file_pin(str(bad_path))
    boundary.selected.add(pin_key(bad_pin))
    with pytest.raises(VerificationError, match="LAB_SIGNATURE_INVALID"):
        boundary.copy_signed(bad_pin)
    assert len({acl[key]["sha256"] for key in ("sourceAccountPin", "writerAccountPin", "readerAccountPin")}) == 3


def test_lab_legacy_playwright_cli_exits_before_admission_browser_or_output(tmp_path):
    dummy_path = tmp_path / "engineering-only.txt"
    dummy_path.write_bytes(b"engineering-only")
    dummy = file_pin(str(dummy_path))
    config = {"schemaVersion":"RecoveryCollectionConfig/v1","kind":"playwright","operationId":"engineering-op",
              "restoreId":"engineering-restore","recoveryPoint":"engineering-point","targetIdentityPin":dummy,
              "verificationTargetPin":dummy,"authorizationPin":dummy,"deadlineMilliseconds":1000,"settings":{}}
    config_path = tmp_path / "config.json"
    config_path.write_bytes(canonical(config))
    binding = {"schemaVersion":"RecoveryLabCollectionCallerBinding/v1","callerThreadId":"engineering-caller",
               "producerThreadIds":["engineering-producer"],"configPin":file_pin(str(config_path)),
               "authorizationPin":dummy,"targetIdentityPin":dummy,"toolPins":[],"independentOriginalPins":[],
               "labAdmissionPin":dummy,"validUntil":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5)).isoformat().replace("+00:00","Z")}
    binding_path = tmp_path / "binding.json"
    binding_path.write_bytes(canonical(binding))
    output = tmp_path / "not-created.json"
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       RECOVERY_VERIFICATION_COLLECTION_TRUST_PIN=json.dumps(file_pin(str(binding_path))))
    result = subprocess.run([sys.executable,"-B",str(MODULE / "collect_recovery.py"),"--config",str(config_path),
                             "--output",str(output)],capture_output=True,text=True,env=environment,timeout=10)
    assert result.returncode == 1 and "LAB_PLAYWRIGHT_SCENARIO_REQUIRED" in result.stderr
    assert not output.exists() and not Path(str(output)+".artifacts").exists()


def test_independent_lab_reader_rejects_legacy_browser_original_before_config():
    entry = str(MODULE / "collect_recovery.py")
    # This fixture supplies only an invocation's routing fields; it makes no
    # claim about a real successful process, browser, login or business result.
    original = {"argv":[sys.executable,"-B",entry],"sourcePins":[]}
    context = SimpleNamespace(lab=object(),invocation=lambda *args: original)
    with pytest.raises(VerificationError, match="LAB_PLAYWRIGHT_SCENARIO_REQUIRED"):
        collection_invocation(context, {}, "COLLECT_PLAYWRIGHT", {}, {})


@pytest.mark.parametrize("body", [{"code":500}, {"code":True}, {"code":"0"}, {}, [], None])
def test_http200_business_error_is_not_success(body):
    response = SimpleNamespace(status=200,headers={"content-type":"application/json"},json=lambda:body)
    with pytest.raises(VerificationError, match="UI_API_BUSINESS_FAILED"):
        api_business_body(response)


def test_http200_malformed_json_is_not_success():
    def malformed():
        return json.loads("not json")
    response = SimpleNamespace(status=200,headers={"content-type":"application/json"},json=malformed)
    with pytest.raises(json.JSONDecodeError):
        api_business_body(response)
    response.headers = {"content-type":"text/html"}
    with pytest.raises(VerificationError, match="UI_API_JSON_REQUIRED"):
        api_business_body(response)


def test_http200_exact_business_code_zero_is_required():
    response = SimpleNamespace(status=200,headers={"content-type":"application/json"},json=lambda:{"code":0})
    assert api_business_body(response) == {"code":0}


def test_production_authorization_reader_still_rejects_operation_grant(tmp_path):
    context = approval_context(fixture(tmp_path))
    grant, approval = context.request["authorizationRefs"]
    context.lab = None
    context.record = json_pin
    authorize(context, [approval])
    with pytest.raises(VerificationError, match="RECORD_FIELDS"):
        authorize(context, [grant, approval])
