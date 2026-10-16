"""Engineering fixtures exercise admission; they are never runtime acceptance evidence."""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/recovery_verification"
sys.path.insert(0, str(MODULE))
from core import canonical, digest, VerificationError, parse, raw_file, pin_key
from integrity import PROTECTED, measure_timing, verify_data, verify_protection
from evidence import report_invalidations, assess_report
from collect_data import encode_cell, row_digest, multiset_digest, identifier
from collect_playwright import validate_browser_settings

SCHEMA = ROOT / "doc/tasks/20261010-backup-restore-modular-development/record-schemas.json"


class Packet:
    def __init__(self, root):
        self.root, self.all_pins = root, {}
        self.clock = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30)
        self.target = self.blob("identity", b"Opaque caller-pinned W05 target identity")
        self.verification_target = self.put("verification-target", {"schemaVersion": "RecoveryVerificationTarget/v1",
                                          "targetIdentityPin": self.target,
                                          "targetId": "engineering-fixture", "environment": "ISOLATED",
                                          "databaseId": "isolated-uuid/db", "frontendOrigin": "http://127.0.0.1:9999"})
        self.tool = self.blob("tool", b"Engineering fixture: not an executed restore tool")
        self.image = self.blob("version", b"Engineering fixture image identity")
        self.isolation = self.blob("isolation", b"Caller-selected engineering isolation evidence")
        self.configuration = self.blob("configuration", b"Engineering configuration, no secrets")
        self.lease = self.blob("lease", b"engineering lease")
        self.point = self.put("point", {"schemaVersion": "RepositoryPoint/v1", "backupId": "b1", "generationId": "g1",
                                       "pointType": "FULL", "parentPointPins": [], "commonRecoveryPoint": "point-1",
                                       "manifestPin": self.blob("manifest", b"manifest"),
                                       "payloadRefs": [self.blob("payload", b"complete local payload")],
                                       "readbackEvidencePin": self.blob("readback", b"readback"),
                                       "ownerCloseEvidencePin": self.blob("owner-close", b"closed"),
                                       "originalExitEvidencePin": self.blob("source-exit", b"exit0"),
                                       "integrityState": "COMPLETE", "blockedReason": None,
                                       "rehearsalEligible": True, "controlledRestoreEligible": False})
        self.approval = self.put("authorization", {"schemaVersion": "RecoveryVerificationAuthorization/v1",
                                                   "operationId": "op1", "action": "VERIFY_RECOVERY",
                                                   "targetIdentityPin": self.target, "validFrom": self.time(0),
                                                   "validUntil": self.time(3600), "tenantId": 122, "writesAllowed": False})
        self.target_ref = self.blob("target-configuration", b"Caller-pinned target configuration input")
        self.target_record = self.put("target", {"schemaVersion": "RecoveryTarget/v1", "targetId": "engineering-fixture",
                                             "targetIdentityPin": self.target,
                                             "resourcesProofPin": self.blob("resources", b"resources"),
                                             "isolationProofPin": self.isolation, "versionPins": [self.image],
                                             "configurationPin": self.configuration, "secretRefs": [],
                                             "sideEffectIsolationPin": self.isolation, "leaseRef": self.lease,
                                             "modePreconditionsPin": self.blob("mode", b"mode")})
        self.plan = self.put("plan", {"schemaVersion": "RestorePlan/v1", "operationId": "op1", "restoreId": "restore1",
                                     "mode": "REHEARSAL", "candidatePin": self.point, "orderedChainPins": [self.point],
                                     "recoveryPoint": "point-1", "targetRef": self.target_ref,
                                     "supportedVersionPins": [self.image], "toolPins": [self.tool], "plannedWrites": [],
                                     "sideEffectPolicyPin": self.isolation, "authorizationRefs": [self.approval],
                                     "leaseRef": self.lease, "immutableInputsSha256": "a" * 64})
        steps = [self.blob("db-step", b"db"), self.blob("object-step", b"object"), self.blob("consistency", b"point-1")]
        invocations = [self.invocation("restore-call-" + str(i), "RESTORE_EXECUTE", step, 3, 7)
                       for i, step in enumerate(steps)]
        self.restore = self.put("restore", {"schemaVersion": "RestoreExecutionResult/v1", "operationId": "op1",
                                           "restoreId": "restore1", "planPin": self.plan, "targetIdentityPin": self.target,
                                           "recoveryPoint": "point-1", "dbStepEvidencePins": [steps[0]],
                                           "objectStepEvidencePins": [steps[1]], "consistencyEvidencePin": steps[2],
                                           "originalInvocationPins": invocations, "state": "SUCCEEDED",
                                           "writeProtectionState": "ENFORCED"})
        health = self.blob("health", b"UP is only app health, not acceptance")
        start = self.invocation("application-call", "START_APPLICATION", health, 8, 10)
        self.app = self.put("app", {"schemaVersion": "ApplicationStartResult/v1", "operationId": "op1",
                                   "restoreId": "restore1", "targetIdentityPin": self.target, "restoreResultPin": self.restore,
                                   "imagePins": [self.image], "configurationPin": self.configuration,
                                   "sideEffectIsolationPin": self.isolation, "originalStartResultPins": [start],
                                   "healthEvidencePin": health, "state": "SUCCEEDED"})
        self.snapshot = {"databaseId": "isolated-uuid/db", "tables": [{"name": "file", "schemaSha256": "b" * 64,
                                                                   "rowCount": 1, "dataSha256": "c" * 64}],
                         "objectScopes": [{"bucket": "private-test", "prefix": "files/"}],
                         "objects": [{"bucket": "private-test", "key": "files/a.txt", "bytes": 5,
                                      "sha256": digest(b"hello")}],
                         "references": [{"table": "file", "rowSha256": "d" * 64, "bucket": "private-test",
                                         "key": "files/a.txt", "deleted": False, "domain": "isolated"}],
                         "referenceSpecs": [{"table": "file", "bucket": "private-test", "keyColumn": "path",
                                             "deletedColumn": "deleted", "domainColumn": "domain",
                                             "allowedDomains": ["isolated"]}]}
        self.baseline = self.put("baseline", {"schemaVersion": "RecoveryDataBaseline/v1", "recoveryPoint": "point-1",
                                             "data": self.snapshot})
        self.data = self.observation("data", "data", self.snapshot, 11, 13)
        protected = {"scopeSnapshots": {name: {"resourceIdentity": name, "sha256": "e" * 64}
                                         for name in sorted(PROTECTED)}, "sideEffectIsolationPin": self.isolation}
        self.before = self.observation("before", "protection", protected, 1, 2)
        self.after = self.observation("after", "protection", protected, 21, 22)
        download = self.blob("download", b"hello")
        shot = self.blob("screenshot", b"Engineering fixture screenshot bytes")
        paths = [{"pathId": name, "entrySelector": "#" + name,
                  "assertions": [{"selector": "#business-row", "kind": "text", "expected": "fixture-row",
                                  "observed": "fixture-row"}], "screenshotPin": shot,
                  "download": {"expectedBytes": 5, "expectedSha256": digest(b"hello"), "actualBytes": 5,
                               "actualSha256": digest(b"hello"), "contentPin": download} if name == "download" else None}
                 for name in ("login", "query", "view", "download")]
        self.browser = self.observation("browser", "playwright", {"engine": "playwright",
                                         "targetOrigin": "http://127.0.0.1:9999", "tenantId": 122,
                                         "tenantName": "测试租户", "username": "aoteman", "paths": paths,
                                         "blockedExternalRequests": 0, "pageErrorCount": 0, "businessFailureCount": 0}, 14, 20)
        marks = self.put("timing-marks", {"schemaVersion": "RecoveryTimingMarks/v1", "clockDomainId": "fixture-domain",
                    "restoreStartInvocationPin": invocations[0], "userReadyObservationPin": self.browser,
                    "restoreStartMonotonicNs": 1000000, "userReadyMonotonicNs": 17001000000,
                    "restoreStartUtc": self.time(3), "userReadyUtc": self.time(20), "clockUncertaintyMilliseconds": 0})
        point_timestamp = self.put("point-timestamp", {"schemaVersion": "RecoveryPointTimestamp/v1",
                    "backupPointPin": self.point, "recoveryPoint": "point-1", "utc": self.time(-100)})
        disruption = self.put("disruption", {"schemaVersion": "RecoveryDisruption/v1", "operationId": "op1", "utc": self.time(0)})
        self.timing = self.observation("timing", "timing", {"clockDomainId": "fixture-domain",
                                      "restoreStartMonotonicNs": 1000000, "userReadyMonotonicNs": 17001000000,
                                      "recoveryPointUtc": self.time(-100), "disruptionUtc": self.time(0),
                                      "clockUncertaintyMilliseconds": 0, "restoreStartInvocationPin": invocations[0],
                                      "userReadyObservationPin": self.browser, "recoveryPointEvidencePin": point_timestamp,
                                      "clockEvidencePin": marks, "disruptionEvidencePin": disruption}, 20, 21)
        self.policy = self.put("policy", {"schemaVersion": "RecoveryVerificationPolicy/v2", "maxAgeMilliseconds": 600000,
                                          "rtoObjectiveMilliseconds": 20000, "rpoObjectiveMilliseconds": 200000,
                                          "recoveryTargetPin": self.target_record, "verificationTargetPin": self.verification_target,
                                          "dataBaselinePin": self.baseline, "dataObservationPin": self.data,
                                          "protectionBeforePin": self.before, "protectionAfterPin": self.after,
                                          "playwrightObservationPin": self.browser, "timingObservationPin": self.timing,
                                          "requiredUserPaths": ["login", "query", "view", "download"],
                                          "protectedScopes": sorted(PROTECTED), "requireDeletedReferenceObjects": False,
                                          "controlledEligibilityPin": None})
        self.request = {"schemaVersion": "backup-restore-operation/v1", "operationId": "op1", "requestId": "req1",
                        "action": "VERIFY_RECOVERY", "mode": "REHEARSAL", "selectedPointPin": self.point,
                        "sourceOrTargetRef": self.target_ref, "policyPin": self.policy,
                        "authorizationRefs": [self.approval], "leaseRef": None,
                        "inputPins": {"restorePlan": self.plan, "restoreExecutionResult": self.restore,
                                      "applicationStartResult": self.app}, "deadlineMilliseconds": 20000}
        from test_recovery_verification_native_fixture import upgrade
        upgrade(self)

    def time(self, seconds):
        return (self.clock + dt.timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

    def blob(self, name, raw):
        path = self.root / (name + ".json")
        path.write_bytes(raw)
        pin = {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}
        self.all_pins[name] = pin
        return pin

    def put(self, name, record):
        return self.blob(name, canonical(record))

    def blob_at(self, name, path, record):
        raw = canonical(record)
        path.write_bytes(raw)
        pin = {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}
        self.all_pins[name] = pin
        return pin

    def observation(self, name, kind, data, start, end):
        return self.put(name, {"schemaVersion": "RecoveryObservation/v1", "kind": kind, "operationId": "op1",
                               "restoreId": "restore1", "targetIdentityPin": self.target, "recoveryPoint": "point-1",
                               "startedAt": self.time(start), "finishedAt": self.time(end), "complete": True, "data": data})

    def invocation(self, name, stage, result, start, finish):
        interpreter = Path(sys.executable).resolve()
        interpreter_raw = interpreter.read_bytes()
        source = {"path": str(interpreter), "bytes": len(interpreter_raw), "sha256": digest(interpreter_raw)}
        sources = [self.tool, source]
        argv = [str(interpreter), self.tool["path"]]
        if stage in ("COLLECT_DATA", "COLLECT_PLAYWRIGHT"):
            entry = MODULE / "collect_recovery.py"
            sources.append({"path": str(entry), "bytes": len(entry.read_bytes()), "sha256": digest(entry.read_bytes())})
            config = self.put(name + "-config", {"schemaVersion": "RecoveryCollectionConfig/v1",
                         "kind": "data" if stage == "COLLECT_DATA" else "playwright", "operationId": "op1",
                         "restoreId": "restore1", "recoveryPoint": "point-1", "targetIdentityPin": self.target,
                         "verificationTargetPin": parse(Path(self.request["policyPin"]["path"]).read_bytes())["verificationTargetPin"],
                         "authorizationPin": self.request["authorizationRefs"][0],
                         "deadlineMilliseconds": 20000, "settings": {}})
            argv = [str(interpreter), str(entry), "--config", config["path"],
                    "--output", result["path"]]
        command = "engineering fixture command " + name
        process_result = self.put(name + "-process", {"id": name, "command": command, "argv": argv,
                                    "cwd": str(self.root), "result": {"exit_code": 0, "session_id": None}})
        return self.put(name, {"schemaVersion": "RecoveryInvocation/v1", "operationId": "op1", "restoreId": "restore1",
                               "targetIdentityPin": self.target, "recoveryPoint": "point-1", "stage": stage,
                               "state": "SUCCEEDED", "actualExitCode": 0, "startedAt": self.time(start),
                               "finishedAt": self.time(finish), "sourcePins": sources, "resultPin": result,
                               "commandId": name, "command": command, "argv": argv, "cwd": str(self.root),
                               "processProfile": "exec-command-result", "processResultPin": process_result})

    def change(self, name, mutate):
        old_pin = self.all_pins[name]
        record = parse(Path(old_pin["path"]).read_bytes())
        mutate(record)
        new = self.blob_at(name, Path(old_pin["path"]), record)
        # Rebind the test caller's selected packet; this isn't a runtime trust selection.
        def replace(value):
            if type(value) is dict:
                if value == old_pin:
                    return new
                return {key: replace(child) for key, child in value.items()}
            if type(value) is list:
                return [replace(child) for child in value]
            return value
        for other_name, pin in list(self.all_pins.items()):
            if other_name == name:
                continue
            raw = Path(pin["path"]).read_bytes()
            if old_pin["sha256"].encode() in raw:
                self.change(other_name, lambda item: item.update(replace(item)))
        self.request = replace(self.request)

    def run(self, no_trust=False, omit_original=None, producer_as_caller=False):
        collections = [self.invocation("collect-data-call", "COLLECT_DATA", self.all_pins["data"], 11, 13),
                       self.invocation("collect-browser-call", "COLLECT_PLAYWRIGHT", self.all_pins["browser"], 14, 20)]
        request_pin = self.put("request", self.request)
        sources = [{"path": str(path), "bytes": len(path.read_bytes()), "sha256": digest(path.read_bytes())}
                   for path in sorted(MODULE.glob("*.py"))]
        sources.append(self.tool)
        interpreter = Path(sys.executable).resolve()
        interpreter_raw = interpreter.read_bytes()
        sources.append({"path": str(interpreter), "bytes": len(interpreter_raw), "sha256": digest(interpreter_raw)})
        scope = self.put("executable-scope", {"schemaVersion": "RecoveryExecutableScope/v1", "callerThreadId": "caller",
                                         "producerThreadIds": ["producer"], "complete": True, "sourcePins": sources})
        trace = self.put("trace", {"schemaVersion": "RecoverySourceTrace/v1", "callerThreadId": "caller",
                                  "operationId": "op1", "sourcePinsBefore": sources, "sourcePinsAfter": sources,
                                  "startedAt": self.time(0), "finishedAt": self.time(25), "collectionInvocationPins": collections})
        originals = [pin for name, pin in self.all_pins.items() if name != omit_original]
        schema_pin = {"path": str(SCHEMA), "bytes": len(SCHEMA.read_bytes()), "sha256": digest(SCHEMA.read_bytes())}
        trust = self.put("trust", {"schemaVersion": "RecoveryCallerBinding/v1",
                                   "callerThreadId": "producer" if producer_as_caller else "caller",
                                   "producerThreadIds": ["producer"], "requestPin": request_pin, "schemaPin": schema_pin,
                                   "sourceScopePin": self.source_scope, "executableScopePin": scope,
                                   "runTracePin": trace, "independentOriginalPins": originals,
                                   "validUntil": self.time(3600)})
        env = dict(os.environ)
        env.pop("RECOVERY_VERIFICATION_TRUST_PIN", None)
        if not no_trust:
            env["RECOVERY_VERIFICATION_TRUST_PIN"] = json.dumps(trust)
        output = self.root / "result.json"
        command = [sys.executable, str(MODULE / "verify_recovery.py"), "--request", request_pin["path"], "--output", str(output)]
        process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
        return process, parse(output.read_bytes())


def test_cli_independent_packet_schema_and_report_sidecar(tmp_path):
    process, result = Packet(tmp_path).run()
    assert process.returncode == 0, (process.stderr, result)
    assert result["data"]["verdict"] == "PASSED"
    assert result["actualExitCode"] is None  # No child is called by the verifier.
    assert result["data"]["rtoObservation"]["observedMilliseconds"] == 17000
    assert result["data"]["rpoObservation"]["observedMilliseconds"] == 100000
    assert parse((tmp_path / "result.json.report.json").read_bytes()) == result["data"]
    assert process.stdout == process.stderr == ""


@pytest.mark.parametrize("arguments,code", [({"no_trust": True}, "CALLER_TRUST_PIN_REQUIRED"),
    ({"producer_as_caller": True}, "CALLER_NOT_INDEPENDENT"),
    ({"omit_original": "data"}, "ORIGINAL_NOT_CALLER_PINNED")])
def test_cli_requires_independent_caller_selected_originals(tmp_path, arguments, code):
    process, result = Packet(tmp_path).run(**arguments)
    assert process.returncode == 1
    assert result["failureCode"] == code
    assert result["state"] == "FAILED_RETAINED"


@pytest.mark.parametrize("name,mutate,code", [
    ("data", lambda r: r.update(recoveryPoint="point-2"), "RECOVERY_POINT_MISMATCH"),
    ("data", lambda r: r["data"].update(databaseId="production/db"), "ACTUAL_DATABASE_TARGET_MISMATCH"),
    ("data", lambda r: r["data"]["objects"][0].update(sha256="f" * 64), "OBJECT_CONTENT_OR_INVENTORY_MISMATCH"),
    ("data", lambda r: r["data"]["tables"][0].update(rowCount=2), "REFERENCE_ROWS_NOT_COMPLETE"),
    ("after", lambda r: r["data"]["scopeSnapshots"]["dcc-matrix"].update(sha256="f" * 64), "PROTECTED_RESOURCE_CHANGED"),
    ("browser", lambda r: r["data"].update(tenantId=1), "PROTECTED_TENANT_OR_USER"),
    ("browser", lambda r: r["data"].update(paths=[]), "USER_PATH_MISSING_OR_UNEXPECTED"),
    ("restore", lambda r: r.update(writeProtectionState="UNKNOWN"), "WRITE_PROTECTION_NOT_ENFORCED"),
    ("restore-call-0", lambda r: r.update(actualExitCode=7), "ORIGINAL_PROCESS_FAILED"),
    ("plan", lambda r: r.update(mode="CONTROLLED_RESTORE"), "PLAN_REQUEST_MISMATCH"),
    ("before", lambda r: r.update(finishedAt=r["finishedAt"].replace("T", " ")), "UTC_REQUIRED"),
    ("policy", lambda r: r.update(maxAgeMilliseconds=1), "RECOVERY_EVIDENCE_EXPIRED"),
])
def test_cli_rejects_mismatch_incomplete_and_expired_evidence(tmp_path, name, mutate, code):
    packet = Packet(tmp_path)
    packet.change(name, mutate)
    process, result = packet.run()
    assert process.returncode == 1, result
    assert result["failureCode"] == code, result
    assert result["data"] is None or result["data"]["verdict"] != "PASSED"


def test_unknown_original_exit_stays_unknown(tmp_path):
    packet = Packet(tmp_path)
    packet.change("restore-call-0", lambda r: r.update(actualExitCode=None, state="TERMINAL_UNKNOWN"))
    process, result = packet.run()
    assert process.returncode == 2
    assert result["state"] == "TERMINAL_UNKNOWN"
    assert result["data"]["verdict"] == "UNKNOWN"


def test_unknown_objective_keeps_measurement_but_blocks_acceptance(tmp_path):
    packet = Packet(tmp_path)
    packet.change("policy", lambda r: r.update(rtoObjectiveMilliseconds=None))
    process, result = packet.run()
    assert process.returncode == 1, result
    assert result["data"]["verdict"] == "BLOCKED"
    assert result["data"]["rtoObservation"] == {"state": "MEASURED", "observedMilliseconds": 17000,
        "objectiveMilliseconds": None, "evidencePins": [packet.all_pins["timing"]]}


def test_object_reference_gap_is_not_hidden_by_inventory_match(tmp_path):
    packet = Packet(tmp_path)
    expected = copy.deepcopy(packet.snapshot)
    expected["references"][0]["key"] = "files/missing.txt"
    with pytest.raises(VerificationError, match="DATABASE_REFERENCES_MISSING_OBJECTS"):
        verify_data(expected, copy.deepcopy(expected), False)


def test_deleted_reference_policy_and_counts_are_separate(tmp_path):
    packet = Packet(tmp_path)
    expected = copy.deepcopy(packet.snapshot)
    expected["references"][0].update(key="files/deleted.txt", deleted=True)
    result = verify_data(expected, copy.deepcopy(expected), False)
    assert result["referenceRows"] == 1 and result["activeReferenceRows"] == result["uniqueReferencedObjects"] == 0
    with pytest.raises(VerificationError, match="DATABASE_REFERENCES_MISSING_OBJECTS"):
        verify_data(expected, copy.deepcopy(expected), True)


def test_complete_scope_requires_protection_and_references(tmp_path):
    packet = Packet(tmp_path)
    with pytest.raises(VerificationError, match="PROTECTION_SCOPE_INCOMPLETE"):
        verify_protection({}, {}, ["dcc-matrix"], packet.isolation, packet.application_isolation)
    value = copy.deepcopy(packet.snapshot)
    value["references"] = []
    with pytest.raises(VerificationError, match="REFERENCE_ROWS_NOT_COMPLETE"):
        verify_data(value, value, False)


def test_timing_rounds_up_and_clock_uncertainty_cannot_improve_rpo():
    value = {"clockDomainId": "one-domain", "restoreStartMonotonicNs": 1, "userReadyMonotonicNs": 1000002,
             "recoveryPointUtc": "2026-01-01T00:00:00.0001Z", "disruptionUtc": "2026-01-01T00:00:00.0002Z",
             "clockUncertaintyMilliseconds": 4, "restoreStartInvocationPin": {}, "userReadyObservationPin": {},
             "recoveryPointEvidencePin": {}, "clockEvidencePin": {}, "disruptionEvidencePin": {}}
    rto, rpo, verdict = measure_timing(value, 1, 4, {})
    assert (rto["observedMilliseconds"], rpo["observedMilliseconds"], verdict) == (2, 5, "FAILED")
    value["userReadyMonotonicNs"] = 0
    with pytest.raises(VerificationError, match="RTO_MONOTONIC_ORDER"):
        measure_timing(value, 10, 10, {})


def test_report_changes_or_expiry_invalidate_old_success(tmp_path):
    _, result = Packet(tmp_path).run()
    report = result["data"]
    current = {key: copy.deepcopy(report[key]) for key in (
        "backupAndChainPins", "planPin", "targetIdentityPin", "sourceScopePin", "toolAndVersionPins",
        "restoreResultPin", "applicationStartPin", "targetApprovalRefs", "operationId", "restoreId", "mode")}
    current["reportGeneratedAt"] = result["finishedAt"]
    assert report_invalidations(report, current, 60000, result["finishedAt"]) == []
    current["targetIdentityPin"] = current["planPin"]
    assert "targetIdentityPin_CHANGED" in report_invalidations(report, current, 60000, result["finishedAt"])
    current["reportGeneratedAt"] = "2020-01-01T00:00:00Z"
    assert "REPORT_EXPIRED" in report_invalidations(report, current, 60000, result["finishedAt"])
    Path(report["planPin"]["path"]).write_bytes(b"late drift")
    assert any("PIN_MISMATCH" in value for value in report_invalidations(report, current, 60000, result["finishedAt"]))


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'\xef\xbb\xbf{}'])
def test_strict_json_rejects_ambiguous_or_nonfinite_input(raw):
    with pytest.raises(VerificationError):
        parse(raw)


def test_bool_size_and_relative_pin_path_rejected():
    with pytest.raises(VerificationError):
        pin_key({"path": str(SCHEMA), "bytes": True, "sha256": "a" * 64})
    with pytest.raises(VerificationError):
        pin_key({"path": "relative.json", "bytes": 1, "sha256": "a" * 64})


def test_row_hash_preserves_types_duplicates_and_order_independence():
    from decimal import Decimal
    assert row_digest((b"1",)) != row_digest(("1",)) != row_digest((1,))
    assert encode_cell(Decimal("1.00")) == {"type": "decimal", "value": "1.00"}
    assert multiset_digest(["a", "b"]) == multiset_digest(["b", "a"])
    assert multiset_digest(["a", "a"]) != multiset_digest(["a"])
    with pytest.raises(VerificationError, match="SQL_IDENTIFIER_REQUIRED"):
        identifier("file; DROP TABLE file")


def test_collection_never_uses_missing_trust_or_default_target(tmp_path):
    config = tmp_path / "config.json"
    config.write_bytes(b'{"password":"secret-must-not-appear"}')
    env = dict(os.environ)
    env.pop("RECOVERY_VERIFICATION_COLLECTION_TRUST_PIN", None)
    process = subprocess.run([sys.executable, str(MODULE / "collect_recovery.py"), "--config", str(config),
                              "--output", str(tmp_path / "collection.json")], env=env, capture_output=True, text=True)
    assert process.returncode == 1 and "COLLECTION_CALLER_TRUST_REQUIRED" in process.stderr
    assert "secret-must-not-appear" not in process.stdout + process.stderr
    assert not (tmp_path / "collection.json").exists()
