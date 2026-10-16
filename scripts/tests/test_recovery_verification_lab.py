"""Engineering signature/binding tests; never source data or rehearsal evidence."""
import base64
import datetime as dt
import os
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "recovery_verification"))
from core import Deadline, VerificationError, canonical, file_pin, json_pin, read_pin
from lab_boundary import LabBoundary, REHEARSAL, HOST, ROOT, PREFIX, LAB_ACTIONS


def fixture(tmp_path, change=None, omit=None, repository_authority=False, key_roles=None):
    selected = []
    def save(name, value, raw=False):
        path = tmp_path / name
        path.write_bytes(value if raw else canonical(value))
        pin = file_pin(str(path))
        selected.append(pin)
        return pin
    key = Ed25519PrivateKey.generate()
    key_pin = save("engineering-key.pem", key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo), True)
    evidence_key = Ed25519PrivateKey.generate()
    evidence_key_pin = save("engineering-evidence-key.pem", evidence_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo), True)
    copy_key = Ed25519PrivateKey.generate()
    copy_key_pin = save("engineering-copy-key.pem", copy_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo), True)
    if key_roles is not None:
        key_roles.update(authority=(key, key_pin), evidence=(evidence_key, evidence_key_pin),
                         copy=(copy_key, copy_key_pin))
    def sign(name, payload, copy=False):
        selected_key, selected_pin = (copy_key, copy_key_pin) if copy else (key, key_pin)
        return save(name, {"schemaVersion": "RepositorySignedRecord/v1", "keySha256": selected_pin["sha256"],
                          "payload": payload, "signature": base64.b64encode(selected_key.sign(canonical(payload))).decode()})
    end = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    # These opaque engineering originals test pin binding only. They do not
    # establish real installation or business acceptance. Nested copy records
    # below use the W03 carrier shapes with separate ephemeral engineering keys.
    originals = {name: save(name + ".json", {"engineeringOnly": name})
                 for name in ("source", "closure", "target")}
    policy_pin = save("policy.json", {"engineeringOnly":"policy"})
    lease = {"schemaVersion":"RecoveryEnvironmentLease/v1","operationId":"engineering-op",
             "targetId":"engineering-target","executorId":"engineering-executor","leaseId":"engineering-lease",
             "fenceToken":1,"notBefore":start,"expiresAt":end,"state":"HELD"}
    grant = {"schemaVersion":"RecoveryEnvironmentAuthorization/v1","operationId":"engineering-op",
             "targetId":"engineering-target","executorId":"engineering-executor","mode":"REHEARSAL",
             "actions":["VERIFY_RECOVERY"],"notBefore":start,"expiresAt":end,"approved":True}
    host = {"schemaVersion":"RepositoryNativeExecutionHost/v1","hostOs":"Linux","hostId":"engineering-host",
            "bootId":"engineering-boot","uid":0,"gid":0,"pidNamespace":"engineering-pidns","mountNamespace":"engineering-mntns",
            "pythonPin":originals['source'],"sourceProfilePin":originals['source'],"dispatcherPin":originals['source'],
            "resourceObserverPin":originals['source'],"workingDirectory":ROOT+"/engineering", "evidenceRoot":ROOT+"/engineering",
            "environment":{"ENGINEERING_ONLY":"1"},"installationManifestPin":originals['closure']}
    if change and change[0]=='host': host[change[1]]=change[2]
    originals['host']=save('host.json',host)
    target_config = save("target-config.json", {"schemaVersion":"RepositoryNativeBackupSource/v1",
        "sourceIdentityPin":originals['source'],"executionHostPin":originals['host']} if repository_authority else
        {"targetId":"engineering-target"})
    if repository_authority:
        lease={"schemaVersion":"RepositoryLease/v1","repositoryId":"engineering-repository",
               "operationId":"engineering-op","ownerIdentityPin":originals['source'],"expiresAt":end}
        if change and change[0]=='lease': lease[change[1]]=change[2]
        originals['lease']=sign('lease.json',lease)
        grant={"schemaVersion":"RepositoryAuthorization/v1","repositoryId":"engineering-repository",
               "operationId":"engineering-op","actions":["VERIFY_RECOVERY"],"sourceOrTargetRef":target_config,
               "policyPin":policy_pin,"resourcePin":target_config,"notBefore":start,"expiresAt":end,
               "leaseRef":originals['lease']}
        if change and change[0]=='grant': grant[change[1]]=change[2]
        originals['grant']=sign('grant.json',grant)
    else:
        if change and change[0] in ("grant","lease"):
            (grant if change[0]=="grant" else lease)[change[1]]=change[2]
        originals['lease']=save('lease.json',lease)
        originals['grant']=save('grant.json',grant)
    approval = {"schemaVersion":"RecoveryVerificationAuthorization/v1","operationId":"engineering-op",
                "action":"VERIFY_RECOVERY","targetIdentityPin":originals["target"],
                "validFrom":start,"validUntil":end,"tenantId":122,"writesAllowed":False}
    if change and change[0] == "approval": approval[change[1]] = change[2]
    originals["approval"] = save("approval.json", approval)
    request = save("request.json", {"operationId": "engineering-op", "mode": "REHEARSAL",
                                  "action": "VERIFY_RECOVERY", "leaseRef": originals["lease"],
                                  "sourceOrTargetRef":target_config,"policyPin":policy_pin,
                                  "authorizationRefs": [originals["grant"], originals["approval"]]})
    scope = {"schemaVersion": "RepositoryLabScope/v1", "rehearsalId": REHEARSAL,
             "repositoryId": "engineering-repository", "sourceIdentityPin": originals["source"],
             "host": HOST, "root": ROOT, "resourcePrefix": PREFIX,
             "allowedActions": ["BACKUP_FULL", "BACKUP_INCREMENTAL", "READBACK_VERIFY", "VERIFY_RECOVERY"], "expiresAt": end}
    if change and change[0] == "scope":
        scope[change[1]] = change[2]
    scope_pin = sign("scope.json", scope)
    accounts = {name: save(name + "-account.txt", name.encode(), True) for name in ("source", "writer", "reader")}
    if change and change[0] == "accounts": accounts[change[1]] = accounts[change[2]]
    if change and change[0] == "account-bytes":
        accounts[change[1]] = save(change[1]+"-duplicate-content-account.txt", change[2].encode(), True)
    probes = {name: save(name + "-probe.txt", name.encode(), True) for name in ("deletion", "key-access", "readback")}
    archive_root = ROOT + "/brlab-20261012-repository/archives"
    deletion = {"schemaVersion":"RepositoryLabDeletionProbe/v1", "labScopePin":scope_pin,
                "accountPin":accounts["source"], "archiveRoot":archive_root,
                "deleteDenied":True,"probeOriginalPin":probes["deletion"]}
    access = {"schemaVersion":"RepositoryLabKeyAccess/v1","labScopePin":scope_pin,
              "recoveryKeysAvailable":True,"probeOriginalPin":probes["key-access"]}
    if change and change[0] in ("deletion", "key-access"):
        (deletion if change[0] == "deletion" else access)[change[1]] = change[2]
    originals["deletion"] = sign("deletion.json", deletion, True)
    originals["key-access"] = sign("key-access.json", access, True)
    acl = {"schemaVersion":"RepositoryLabAclEvidence/v1","labScopePin":scope_pin,
           "sourceIdentityPin":originals["source"],"archiveRoot":archive_root,
           "sourceAccountPin":accounts["source"],"writerAccountPin":accounts["writer"],
           "readerAccountPin":accounts["reader"],"deletionAttemptPin":originals["deletion"],
           "keyAccessEvidencePin":originals["key-access"]}
    endpoint = {"schemaVersion":"RepositoryLabReadbackEndpoint/v1","labScopePin":scope_pin,
                "archiveRoot":archive_root,"uncRoot":"\\\\"+HOST+"\\"+PREFIX+"-readback",
                "encrypted":True,"signingRequired":True,"independentConnectionId":"engineering-connection",
                "readerAccountPin":accounts["reader"],"readbackOriginalPin":probes["readback"],"observedAt":start}
    if change and change[0] in ("acl", "readback"):
        (acl if change[0] == "acl" else endpoint)[change[1]] = change[2]
    originals["acl"] = sign("acl.json", acl, True)
    originals["readback"] = sign("readback.json", endpoint, True)
    context = {"schemaVersion": "BackupRehearsalAuthorityContext/v1", "rehearsalId": REHEARSAL,
               "environment": "backup-lab", "sourceIdentityPin": originals["source"],
               "executionHostPin": originals["host"], "labScopePin": scope_pin,
               "operationRequestPin": request, "installedClosurePin": originals["closure"],
               "authorizationPin": originals["grant"], "leasePin": originals["lease"],
               "authorityKeyPin": key_pin, "issuedAt": start, "expiresAt": end}
    if change and change[0] == "context":
        context[change[1]] = change[2]
    context_pin = sign("context.json", context)
    selected.remove(context_pin)
    os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_PATH"] = context_pin["path"]
    os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_SHA256"] = context_pin["sha256"]
    admission = {"schemaVersion": "RecoveryLabAdmission/v2",
                 "authorityKeyPin": key_pin, "repositoryEvidenceKeyPin": evidence_key_pin,
                 "copyProtectionEvidenceKeyPins": [copy_key_pin],
                 "targetIdentityPin": originals["target"], "mode": "REHEARSAL", "validUntil": end,
                 **{k: context[k] for k in ("labScopePin", "sourceIdentityPin", "executionHostPin", "installedClosurePin")}}
    if change and change[0] == "admission":
        admission[change[1]] = change[2]
    admission_pin = save("admission.json", admission)
    proof = {"schemaVersion": "RepositoryLabCopyProtection/v1", "repositoryId": "engineering-repository",
             "sourceIdentityPin": originals["source"], "labScopePin": scope_pin,
             "sourceDeletionDenied": True, "independentFailureDomain": False, "recoveryKeysAvailable": True,
             "aclEvidencePin": originals["acl"], "readbackEndpointEvidencePin": originals["readback"], "validUntil": end}
    if change and change[0] == "proof":
        proof[change[1]] = change[2]
    proof_pin = sign("proof.json", proof, True)
    if omit:
        selected.remove(originals[omit])
    return admission_pin, selected, request, proof_pin


def admit(values, mode="REHEARSAL"):
    admission, selected, request, proof = values
    return LabBoundary(admission, selected, read_pin, json_pin, Deadline(30000),
                       "engineering-op", mode, request_pin=request)


def test_signed_private_lab_scope_is_explicit(tmp_path):
    values = fixture(tmp_path)
    boundary = admit(values)
    assert boundary.copy_protection(values[3], 300000)["independentFailureDomain"] is False
    assert boundary.scope["host"] == HOST


@pytest.mark.parametrize("mode", ["CONTROLLED_RESTORE", "PROD", "NAS"])
def test_lab_cannot_gain_production_credit(tmp_path, mode):
    with pytest.raises(VerificationError, match="LAB_REHEARSAL_ONLY"):
        admit(fixture(tmp_path), mode)


@pytest.mark.parametrize("change,error", [
    (("scope", "host", "172.30.30.57"), "LAB_RESOURCE_SCOPE_MISMATCH"),
    (("scope", "root", "/mnt/intruoyi-data"), "LAB_RESOURCE_SCOPE_MISMATCH"),
    (("scope", "allowedActions", ["CONTROLLED_CUTOVER"]), "LAB_ACTION_SCOPE_INVALID"),
    (("scope", "allowedActions", ["RETENTION_EXECUTE"]), "LAB_ACTION_SCOPE_INVALID"),
    (("context", "environment", "PROD"), "LAB_CONTEXT_SCOPE_MISMATCH"),
    (("context", "expiresAt", "2020-01-01T00:00:00Z"), "LAB_CONTEXT_WINDOW_INVALID"),
    (("admission", "validUntil", "2020-01-01T00:00:00Z"), "LAB_AUTHORITY_EXPIRED"),
])
def test_invalid_selected_scope_is_rejected(tmp_path, change, error):
    with pytest.raises(VerificationError, match=error):
        admit(fixture(tmp_path, change))


@pytest.mark.parametrize("field,value,error", [
    ("independentFailureDomain", True, "LAB_FALSE_FAILURE_DOMAIN_REQUIRED"),
    ("sourceDeletionDenied", False, "LAB_COPY_PROTECTION_REQUIRED"),
    ("recoveryKeysAvailable", False, "LAB_COPY_PROTECTION_REQUIRED"),
])
def test_signed_false_copy_protection_is_rejected(tmp_path, field, value, error):
    values = fixture(tmp_path, ("proof", field, value))
    with pytest.raises(VerificationError, match=error):
        admit(values).copy_protection(values[3], 300000)


def test_producer_cannot_choose_unselected_acl_original(tmp_path):
    values = fixture(tmp_path, omit="acl")
    with pytest.raises(VerificationError, match="LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED"):
        admit(values).copy_protection(values[3], 300000)


def test_changed_authority_original_invalidates_before_effect(tmp_path):
    values = fixture(tmp_path)
    boundary = admit(values)
    Path(boundary.context["leasePin"]["path"]).write_bytes(b"changed")
    with pytest.raises(VerificationError, match="PIN_MISMATCH"):
        boundary.recheck()


def test_bad_signature_rejected_even_when_new_pin_is_selected(tmp_path):
    values = fixture(tmp_path)
    admission_pin, selected, request, proof = values
    admission = json_pin(admission_pin)
    path = Path(os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_PATH"])
    old_context = file_pin(str(path))
    record = json_pin(old_context)
    record["signature"] = base64.b64encode(b"x" * 64).decode()
    path.write_bytes(canonical(record))
    new_pin = file_pin(str(path))
    os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_SHA256"] = new_pin["sha256"]
    with pytest.raises(VerificationError, match="LAB_SIGNATURE_INVALID"):
        admit((admission_pin, selected, request, proof))


def test_context_cannot_be_embedded_in_current_trust_list(tmp_path):
    values = fixture(tmp_path)
    values[1].append(file_pin(os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_PATH"]))
    with pytest.raises(VerificationError, match="LAB_CONTEXT_MUST_BE_OUT_OF_BAND"):
        admit(values)


def test_missing_out_of_band_selection_fails(tmp_path, monkeypatch):
    values = fixture(tmp_path)
    monkeypatch.delenv("INTRUOYI_BACKUP_LAB_CONTEXT_PATH")
    with pytest.raises(VerificationError, match="LAB_CONTEXT_LAUNCH_SELECTION_REQUIRED"):
        admit(values)


def test_stable_admission_must_not_embed_current_context(tmp_path):
    values = fixture(tmp_path)
    admission = json_pin(values[0])
    admission["contextPin"] = file_pin(os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_PATH"])
    Path(values[0]["path"]).write_bytes(canonical(admission))
    changed = file_pin(values[0]["path"])
    values[1].remove(values[0])
    values[1].append(changed)
    with pytest.raises(VerificationError, match="RECORD_FIELDS"):
        admit((changed, values[1], values[2], values[3]))


def test_current_context_is_rejected_in_transitive_graph(tmp_path):
    boundary = admit(fixture(tmp_path))
    with pytest.raises(VerificationError, match="LAB_CONTEXT_REQUEST_PIN_CYCLE"):
        boundary.reject_context_cycle(boundary.context_pin)
