"""Explicit private same-host rehearsal admission; never production eligibility.

The independent caller selects every original, including both public keys. This
consumer does not create a context, grant, lease, installed identity or ACL proof.
"""
import base64
import binascii
import datetime as dt
import os
import time
from pathlib import PurePosixPath

from core import (MAX_JSON_BYTES, canonical, fields, file_pin, json_pin, need, parse,
                  pin_key, pins, read_pin, same, sha, text, timestamp, VerificationError)

REHEARSAL = "backup-server-rehearsal-20261012-r1"
HOST = "172.30.30.59"
ROOT = "/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07"
PREFIX = "brlab-20261012"
LAB_ACTIONS = frozenset({"BACKUP_FULL", "BACKUP_INCREMENTAL", "LIST_POINTS", "POINT_DETAIL", "READBACK_VERIFY",
                        "RESTORE_PREFLIGHT", "PREPARE_TARGET", "RESTORE_EXECUTE", "START_APPLICATION",
                        "VERIFY_RECOVERY", "REHEARSAL", "PLAN_REHEARSAL"})
ADMISSION_FIELDS = ("schemaVersion authorityKeyPin repositoryEvidenceKeyPin copyProtectionEvidenceKeyPins labScopePin "
                    "sourceIdentityPin executionHostPin installedClosurePin "
                    "targetIdentityPin mode validUntil")


def selected_context(deadline):
    path = os.environ.get("INTRUOYI_BACKUP_LAB_CONTEXT_PATH")
    checksum = os.environ.get("INTRUOYI_BACKUP_LAB_CONTEXT_SHA256")
    need(path is not None and checksum is not None, "LAB_CONTEXT_LAUNCH_SELECTION_REQUIRED")
    sha(checksum)
    pin = file_pin(path, deadline)
    need(pin["sha256"] == checksum, "LAB_CONTEXT_LAUNCH_HASH_MISMATCH", "STALE")
    return pin


class LabBoundary:
    def __init__(self, admission_pin, originals, read, record, deadline,
                 operation_id, mode, request_pin=None, target_pin=None):
        self.selected = set(pins(originals))
        self.read, self.record, self.deadline = read, record, deadline
        self.admission_pin = admission_pin
        self.operation_id, self.mode = operation_id, mode
        self.request_pin, self.target_pin = request_pin, target_pin
        self.context_pin = selected_context(deadline)
        need(pin_key(self.context_pin) not in self.selected, "LAB_CONTEXT_MUST_BE_OUT_OF_BAND")
        self.graph_checked = False
        self.launch_selection = (os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_PATH"],
                                 os.environ["INTRUOYI_BACKUP_LAB_CONTEXT_SHA256"])
        self.recheck()

    def original(self, pin, as_json=True):
        if pin_key(pin) == pin_key(self.context_pin):
            return json_pin(pin, self.deadline) if as_json else read_pin(pin, self.deadline)
        need(pin_key(pin) in self.selected, "LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
        return self.record(pin) if as_json else self.read(pin, content=True)

    def window(self, value):
        current = dt.datetime.now(dt.timezone.utc)
        end = timestamp(value)
        need(current < end, "LAB_AUTHORITY_EXPIRED", "STALE")
        self.deadline.end = min(self.deadline.end,
                                time.monotonic() + (end - current).total_seconds())

    def signed(self, pin, key_pin):
        from cryptography.exceptions import InvalidSignature
        signed = self.original(pin)
        fields(signed, "schemaVersion keySha256 payload signature", "RepositorySignedRecord/v1")
        need(signed["keySha256"] == key_pin["sha256"], "LAB_SIGNING_KEY_NOT_SELECTED")
        try:
            key = self.public_key(key_pin)
            key.verify(base64.b64decode(signed["signature"], validate=True), canonical(signed["payload"]))
        except (InvalidSignature, ValueError, TypeError, binascii.Error) as error:
            raise VerificationError("LAB_SIGNATURE_INVALID") from error
        return signed["payload"]

    def public_key(self, pin):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        need(pin_key(pin) in self.selected, "LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
        need(0 < pin["bytes"] <= 65536, "LAB_PUBLIC_KEY_SIZE")
        raw = read_pin(pin, self.deadline, max_bytes=65536)
        # Retain the caller's consumed-original accounting without an unbounded content read.
        self.read(pin, content=False)
        try:
            key = serialization.load_pem_public_key(raw)
        except (ValueError, TypeError) as error:
            raise VerificationError("LAB_PUBLIC_KEY_INVALID") from error
        need(isinstance(key, Ed25519PublicKey), "LAB_ED25519_REQUIRED")
        return key

    def recheck(self):
        self.deadline.remaining()
        need(self.launch_selection == (os.environ.get("INTRUOYI_BACKUP_LAB_CONTEXT_PATH"),
             os.environ.get("INTRUOYI_BACKUP_LAB_CONTEXT_SHA256")), "LAB_CONTEXT_LAUNCH_SELECTION_CHANGED", "STALE")
        admission = self.original(self.admission_pin)
        fields(admission, ADMISSION_FIELDS, "RecoveryLabAdmission/v2")
        need(self.mode == admission["mode"] == "REHEARSAL", "LAB_REHEARSAL_ONLY")
        self.window(admission["validUntil"])
        context = self.signed(self.context_pin, admission["authorityKeyPin"])
        fields(context, "schemaVersion rehearsalId environment sourceIdentityPin executionHostPin labScopePin "
               "operationRequestPin installedClosurePin authorizationPin leasePin authorityKeyPin issuedAt expiresAt",
               "BackupRehearsalAuthorityContext/v1")
        need(context["rehearsalId"] == REHEARSAL and context["environment"] == "backup-lab",
             "LAB_CONTEXT_SCOPE_MISMATCH")
        current = dt.datetime.now(dt.timezone.utc)
        need(timestamp(context["issuedAt"]) <= current < timestamp(context["expiresAt"]),
             "LAB_CONTEXT_WINDOW_INVALID", "STALE")
        self.window(context["expiresAt"])
        for key in ("sourceIdentityPin", "executionHostPin", "labScopePin", "installedClosurePin", "authorityKeyPin"):
            same(context[key], admission[key], "LAB_CONTEXT_" + key.upper() + "_MISMATCH")
            self.original(admission[key], key != "authorityKeyPin")
        self.original(admission["repositoryEvidenceKeyPin"], False)
        copy_keys = pins(admission["copyProtectionEvidenceKeyPins"])
        need(len(copy_keys) == len(set(copy_keys)) and
             len({pin["sha256"] for pin in admission["copyProtectionEvidenceKeyPins"]}) == len(copy_keys),
             "LAB_COPY_SIGNING_KEYS_DUPLICATE")
        for pin in admission["copyProtectionEvidenceKeyPins"]:
            self.public_key(pin)
        self.original(admission["targetIdentityPin"])
        if self.target_pin is not None:
            same(admission["targetIdentityPin"], self.target_pin, "LAB_TARGET_MISMATCH")
        if self.request_pin is not None:
            same(context["operationRequestPin"], self.request_pin, "LAB_REQUEST_MISMATCH")
        request = self.original(context["operationRequestPin"])
        need(request.get("operationId") == self.operation_id and request.get("mode") == "REHEARSAL",
             "LAB_OPERATION_MISMATCH")
        need(request.get("action") in LAB_ACTIONS,
             "LAB_OPERATION_ACTION_PROHIBITED")
        same(request["leaseRef"], context["leasePin"], "LAB_REQUEST_LEASE_MISMATCH")
        self.original(context["leasePin"])
        self.original(context["authorizationPin"])
        need(pin_key(context["authorizationPin"]) in set(pins(request["authorizationRefs"])),
             "LAB_REQUEST_AUTHORIZATION_MISMATCH")
        scope = self.signed(admission["labScopePin"], admission["authorityKeyPin"])
        fields(scope, "schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix "
               "allowedActions expiresAt", "RepositoryLabScope/v1")
        need(scope["rehearsalId"] == REHEARSAL and scope["host"] == HOST and scope["root"] == ROOT
             and scope["resourcePrefix"] == PREFIX, "LAB_RESOURCE_SCOPE_MISMATCH")
        text(scope["repositoryId"])
        same(scope["sourceIdentityPin"], admission["sourceIdentityPin"], "LAB_SOURCE_MISMATCH")
        # Exact frozen OperationRequest tokens; no compatibility aliases.
        actions = scope["allowedActions"]
        need(type(actions) is list and bool(actions) and all(type(a) is str for a in actions)
             and len(actions) == len(set(actions)) and set(actions) <= LAB_ACTIONS,
             "LAB_ACTION_SCOPE_INVALID")
        need(request["action"] in actions, "LAB_REQUEST_ACTION_NOT_SCOPED")
        self.window(scope["expiresAt"])
        self.authority(context, scope, request)
        host = self.original(admission["executionHostPin"])
        fields(host, "schemaVersion hostOs hostId bootId uid gid pidNamespace mountNamespace pythonPin sourceProfilePin "
               "dispatcherPin resourceObserverPin workingDirectory evidenceRoot environment installationManifestPin",
               "RepositoryNativeExecutionHost/v1")
        need(host["hostOs"] == "Linux" and type(host["uid"]) is int and type(host["gid"]) is int
             and host["uid"] == host["gid"] == 0, "LAB_NATIVE_HOST_INVALID")
        for key in ("hostId", "bootId", "pidNamespace", "mountNamespace", "workingDirectory", "evidenceRoot"):
            text(host[key])
        same(host["installationManifestPin"], context["installedClosurePin"], "LAB_HOST_INSTALLATION_MISMATCH")
        self.admission, self.scope, self.context = admission, scope, context
        if not self.graph_checked:
            self.reject_context_cycle(context["operationRequestPin"])
            self.graph_checked = True

    def authority(self, context, scope, request):
        def value(pin):
            raw = self.original(pin)
            if raw.get("schemaVersion") == "RepositorySignedRecord/v1":
                return self.signed(pin, context["authorityKeyPin"])
            need(raw.get("schemaVersion") in {"RecoveryEnvironmentAuthorization/v1", "RecoveryEnvironmentLease/v1"},
                 "LAB_AUTHORITY_RECORD_UNKNOWN")
            return raw
        grant, lease = value(context["authorizationPin"]), value(context["leasePin"])
        if grant.get("schemaVersion") == "RepositoryAuthorization/v1":
            fields(grant, "schemaVersion repositoryId operationId actions sourceOrTargetRef policyPin resourcePin "
                   "notBefore expiresAt leaseRef", "RepositoryAuthorization/v1")
            fields(lease, "schemaVersion repositoryId operationId ownerIdentityPin expiresAt", "RepositoryLease/v1")
            need(grant["repositoryId"] == lease["repositoryId"] == scope["repositoryId"], "LAB_GRANT_REPOSITORY_MISMATCH")
            for key in ("sourceOrTargetRef", "policyPin"):
                same(grant[key], request[key], "LAB_GRANT_REQUEST_MISMATCH")
            same(grant["resourcePin"], request["sourceOrTargetRef"], "LAB_GRANT_RESOURCE_MISMATCH")
            same(grant["leaseRef"], context["leasePin"], "LAB_GRANT_LEASE_MISMATCH")
            self.original(lease["ownerIdentityPin"])
            source = self.original(request["sourceOrTargetRef"])
            need(source.get("schemaVersion") == "RepositoryNativeBackupSource/v1", "LAB_GRANT_SOURCE_VERSION")
            same(source["sourceIdentityPin"], context["sourceIdentityPin"], "LAB_GRANT_SOURCE_MISMATCH")
            same(source["executionHostPin"], context["executionHostPin"], "LAB_GRANT_HOST_MISMATCH")
        else:
            fields(grant, "schemaVersion operationId targetId executorId mode actions notBefore expiresAt approved",
                   "RecoveryEnvironmentAuthorization/v1")
            fields(lease, "schemaVersion operationId targetId executorId leaseId fenceToken notBefore expiresAt state",
                   "RecoveryEnvironmentLease/v1")
            target = self.original(request["sourceOrTargetRef"])
            need(grant["approved"] is True and grant["mode"] == request["mode"]
                 and grant["targetId"] == lease["targetId"] == target["targetId"]
                 and grant["executorId"] == lease["executorId"] and lease["state"] == "HELD"
                 and type(lease["fenceToken"]) is int and lease["fenceToken"] > 0,
                 "LAB_TARGET_GRANT_LEASE_INVALID")
            need(timestamp(lease["notBefore"]) <= dt.datetime.now(dt.timezone.utc), "LAB_LEASE_NOT_CURRENT", "STALE")
            text(lease["leaseId"])
        actions = grant["actions"]
        need(type(actions) is list and bool(actions) and all(type(a) is str for a in actions)
             and len(actions) == len(set(actions)) and set(actions) <= LAB_ACTIONS, "LAB_GRANT_ACTIONS_INVALID")
        need(request["action"] in actions and grant["operationId"] == lease["operationId"] == request["operationId"],
             "LAB_GRANT_ACTION_OR_OPERATION_MISMATCH")
        current = dt.datetime.now(dt.timezone.utc)
        need(timestamp(grant["notBefore"]) <= current, "LAB_GRANT_NOT_CURRENT", "STALE")
        self.window(grant["expiresAt"])
        self.window(lease["expiresAt"])
        need(timestamp(context["expiresAt"]) <= min(timestamp(grant["expiresAt"]), timestamp(lease["expiresAt"]),
             timestamp(scope["expiresAt"])), "LAB_CONTEXT_EXCEEDS_AUTHORITY", "STALE")
        self.grant, self.lease = grant, lease

    def reject_context_cycle(self, *root_pins):
        pending, visited = [*root_pins, self.admission_pin], set()
        while pending:
            pin = pending.pop()
            key = pin_key(pin)
            need(key != pin_key(self.context_pin), "LAB_CONTEXT_REQUEST_PIN_CYCLE")
            if key in visited:
                continue
            need(len(visited) < 4096, "LAB_PIN_GRAPH_LIMIT")
            visited.add(key)
            if pin["bytes"] > MAX_JSON_BYTES:
                need(key in self.selected, "LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
                self.read(pin, content=False)
                continue
            raw = self.original(pin, False)
            if not raw.lstrip().startswith((b"{", b"[")):
                continue
            values = [parse(raw)]
            while values:
                value = values.pop()
                if type(value) is dict:
                    if set(value) == {"path", "bytes", "sha256"} and type(value["path"]) is str and type(value["bytes"]) is int:
                        pending.append(value)
                    else:
                        values.extend(value.values())
                elif type(value) is list:
                    values.extend(value)

    def copy_signed(self, pin):
        record = self.original(pin)
        fields(record, "schemaVersion keySha256 payload signature", "RepositorySignedRecord/v1")
        keys = [key for key in self.admission["copyProtectionEvidenceKeyPins"]
                if key["sha256"] == record["keySha256"]]
        need(len(keys) == 1, "LAB_COPY_SIGNING_KEY_NOT_SELECTED")
        return self.signed(pin, keys[0])

    def copy_protection(self, pin, maximum_age_ms):
        self.recheck()
        need("READBACK_VERIFY" in self.scope["allowedActions"], "LAB_READBACK_NOT_RELEASED")
        need(type(maximum_age_ms) is int and maximum_age_ms > 0, "LAB_COPY_FRESHNESS_REQUIRED")
        proof = self.copy_signed(pin)
        fields(proof, "schemaVersion repositoryId sourceIdentityPin labScopePin sourceDeletionDenied "
               "independentFailureDomain recoveryKeysAvailable aclEvidencePin readbackEndpointEvidencePin validUntil",
               "RepositoryLabCopyProtection/v1")
        need(proof["repositoryId"] == self.scope["repositoryId"], "LAB_REPOSITORY_MISMATCH")
        same(proof["sourceIdentityPin"], self.admission["sourceIdentityPin"], "LAB_COPY_SOURCE_MISMATCH")
        same(proof["labScopePin"], self.admission["labScopePin"], "LAB_COPY_SCOPE_MISMATCH")
        need(proof["independentFailureDomain"] is False, "LAB_FALSE_FAILURE_DOMAIN_REQUIRED")
        need(proof["sourceDeletionDenied"] is True and proof["recoveryKeysAvailable"] is True,
             "LAB_COPY_PROTECTION_REQUIRED")
        self.window(proof["validUntil"])
        acl = self.copy_signed(proof["aclEvidencePin"])
        fields(acl, "schemaVersion labScopePin sourceIdentityPin archiveRoot sourceAccountPin writerAccountPin "
               "readerAccountPin deletionAttemptPin keyAccessEvidencePin", "RepositoryLabAclEvidence/v1")
        endpoint = self.copy_signed(proof["readbackEndpointEvidencePin"])
        fields(endpoint, "schemaVersion labScopePin archiveRoot uncRoot encrypted signingRequired "
               "independentConnectionId readerAccountPin readbackOriginalPin observedAt",
               "RepositoryLabReadbackEndpoint/v1")
        for value in (acl, endpoint):
            same(value["labScopePin"], proof["labScopePin"], "LAB_COPY_SCOPE_MISMATCH")
        same(acl["sourceIdentityPin"], proof["sourceIdentityPin"], "LAB_COPY_SOURCE_MISMATCH")
        root = PurePosixPath(text(acl["archiveRoot"]))
        need(root.is_absolute() and str(root) == acl["archiveRoot"] and ".." not in root.parts
             and root.name == "archives" and PurePosixPath(self.scope["root"]) in root.parents
             and endpoint["archiveRoot"] == acl["archiveRoot"], "LAB_COPY_ARCHIVE_ROOT_MISMATCH")
        unc = text(endpoint["uncRoot"])
        need(unc.startswith("\\\\" + self.scope["host"] + "\\") and len(unc.split("\\")) == 4
             and unc.split("\\")[3].startswith(self.scope["resourcePrefix"]), "LAB_COPY_ENDPOINT_OUT_OF_SCOPE")
        need(endpoint["encrypted"] is True and endpoint["signingRequired"] is True,
             "LAB_COPY_SECURE_READBACK_REQUIRED")
        text(endpoint["independentConnectionId"])
        same(endpoint["readerAccountPin"], acl["readerAccountPin"], "LAB_COPY_READER_MISMATCH")
        accounts = [acl[key] for key in ("sourceAccountPin", "writerAccountPin", "readerAccountPin")]
        pins(accounts)
        need(len({account["sha256"] for account in accounts}) == 3, "LAB_COPY_INDEPENDENT_ACCOUNTS_REQUIRED")
        deletion = self.copy_signed(acl["deletionAttemptPin"])
        fields(deletion, "schemaVersion labScopePin accountPin archiveRoot deleteDenied probeOriginalPin",
               "RepositoryLabDeletionProbe/v1")
        keys = self.copy_signed(acl["keyAccessEvidencePin"])
        fields(keys, "schemaVersion labScopePin recoveryKeysAvailable probeOriginalPin", "RepositoryLabKeyAccess/v1")
        for value in (deletion, keys):
            same(value["labScopePin"], proof["labScopePin"], "LAB_COPY_SCOPE_MISMATCH")
        same(deletion["accountPin"], acl["sourceAccountPin"], "LAB_COPY_DELETE_ACCOUNT_MISMATCH")
        need(deletion["archiveRoot"] == acl["archiveRoot"] and deletion["deleteDenied"] is True
             and keys["recoveryKeysAvailable"] is True, "LAB_COPY_PROBES_REQUIRED")
        for original in (*accounts, deletion["probeOriginalPin"], keys["probeOriginalPin"], endpoint["readbackOriginalPin"]):
            self.original(original, False)
        observed = timestamp(endpoint["observedAt"])
        age_ms = (dt.datetime.now(dt.timezone.utc) - observed).total_seconds() * 1000
        need(0 <= age_ms <= maximum_age_ms and observed < timestamp(proof["validUntil"]),
             "LAB_COPY_EVIDENCE_STALE", "STALE")
        self.window((observed + dt.timedelta(milliseconds=maximum_age_ms)).isoformat().replace("+00:00", "Z"))
        return proof
