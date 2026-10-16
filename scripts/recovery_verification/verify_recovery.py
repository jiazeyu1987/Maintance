"""VERIFY_RECOVERY file CLI. No restore, SQL write, browser action or external notification.

The service caller supplies RECOVERY_VERIFICATION_TRUST_PIN as a JSON Pin to its
independently selected RecoveryCallerBinding/v1. A producer request cannot supply
or replace this trust root. Evidence collection is a separate authorized operation.
"""
import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from core import (Deadline, VerificationError, absolute, fields, need, now, parse, raw_file,
                  digest, pin_key, pins, json_pin, read_pin, same, integer, timestamp, validate, write_atomic)
from evidence import EvidenceContext, admit_restore
from integrity import (PROTECTED, verify_data, verify_protection, verify_user_paths, measure_timing)


def policy_record(context):
    policy = context.record(context.request["policyPin"])
    fields(policy, "schemaVersion maxAgeMilliseconds rtoObjectiveMilliseconds rpoObjectiveMilliseconds "
           "recoveryTargetPin verificationTargetPin dataBaselinePin dataObservationPin protectionBeforePin protectionAfterPin "
           "playwrightObservationPin timingObservationPin requiredUserPaths protectedScopes "
           "requireDeletedReferenceObjects derivedBaselinePin controlledEligibilityPin", "RecoveryVerificationPolicy/v2")
    integer(policy["maxAgeMilliseconds"], 1)
    for key in ("rtoObjectiveMilliseconds", "rpoObjectiveMilliseconds"):
        if policy[key] is not None:
            integer(policy[key])
    if context.request["mode"] == "REHEARSAL":
        need(policy["controlledEligibilityPin"] is None, "REHEARSAL_CONTROLLED_ELIGIBILITY_PROHIBITED")
    else:
        need(policy["controlledEligibilityPin"] is not None, "CONTROLLED_ELIGIBILITY_REQUIRED")
        context.record(policy["controlledEligibilityPin"])
    return policy


def authorize(context, approvals):
    need(bool(approvals), "VERIFICATION_AUTHORIZATION_REQUIRED")
    if context.lab is not None:
        # The operation grant and verifier approvals have different contracts.
        # Revalidate the exact current grant; never interpret it as an approval.
        context.lab.recheck()
        same(context.target_pin, context.lab.admission["targetIdentityPin"], "LAB_AUTHORIZATION_TARGET_MISMATCH")
        approval_keys = pins(approvals)
        grant_key = pin_key(context.lab.context["authorizationPin"])
        need(grant_key in approval_keys, "LAB_CURRENT_GRANT_REQUIRED")
        approvals = [pin for pin in approvals if pin_key(pin) != grant_key]
        need(bool(approvals), "VERIFICATION_AUTHORIZATION_REQUIRED")
        for pin in approvals:
            need(pin_key(pin) in context.lab.selected, "LAB_APPROVAL_NOT_INDEPENDENTLY_SELECTED")
    now_at = dt.datetime.now(dt.timezone.utc)
    for pin in approvals:
        approval = context.record(pin)
        fields(approval, "schemaVersion operationId action targetIdentityPin validFrom validUntil "
               "tenantId writesAllowed", "RecoveryVerificationAuthorization/v1")
        need(approval["operationId"] == context.request["operationId"] and
             approval["action"] == "VERIFY_RECOVERY", "AUTHORIZATION_ACTION_MISMATCH")
        same(approval["targetIdentityPin"], context.target_pin, "AUTHORIZATION_TARGET_MISMATCH")
        need(timestamp(approval["validFrom"]) <= now_at < timestamp(approval["validUntil"]),
             "AUTHORIZATION_WINDOW_EXPIRED", "STALE")
        need(type(approval["tenantId"]) is int and approval["tenantId"] == 122 and
             type(approval["writesAllowed"]) is bool, "AUTHORIZATION_PROTECTED_TENANT")
        import time
        context.deadline.end = min(context.deadline.end, time.monotonic() +
                                   (timestamp(approval["validUntil"]) - now_at).total_seconds())


def verify(context):
    policy = policy_record(context)
    plan, restore, application, target = admit_restore(context, policy["recoveryTargetPin"], policy)
    authorize(context, context.request["authorizationRefs"])
    identity = context.record(policy["verificationTargetPin"])
    fields(identity, "schemaVersion targetIdentityPin targetId environment databaseId frontendOrigin objectBindingPin", "RecoveryVerificationTarget/v1")
    same(identity["targetIdentityPin"], context.target_pin, "VERIFICATION_TARGET_MISMATCH")
    need(identity["targetId"] == target["targetId"] and identity["environment"] == "ISOLATED",
         "REAL_ISOLATED_TARGET_REQUIRED")
    baseline = context.record(policy["dataBaselinePin"])
    fields(baseline, "schemaVersion recoveryPoint data", "RecoveryDataBaseline/v1")
    need(baseline["recoveryPoint"] == plan["recoveryPoint"], "BASELINE_RECOVERY_POINT_MISMATCH", "STALE")
    data = context.observation(policy["dataObservationPin"], "data")
    need(data["data"]["databaseId"] == identity["databaseId"], "ACTUAL_DATABASE_TARGET_MISMATCH", "STALE")
    from service_identity import verify_service_observation
    from derived_state import verify_derived
    verify_service_observation(context, data["data"]["objectTarget"], identity["objectBindingPin"], "minio")
    need(timestamp(data["startedAt"]) <= timestamp(data["data"]["objectTarget"]["observedAt"]) <=
         timestamp(data["finishedAt"]), "OBJECT_IDENTITY_OBSERVATION_OUTSIDE_COLLECTION")
    verify_derived(context, policy["derivedBaselinePin"], data["data"])
    for item in data["data"]["derived"]:
        need(timestamp(data["startedAt"]) <= timestamp(item["service"]["observedAt"]) <= timestamp(data["finishedAt"]),
             "DERIVED_IDENTITY_OBSERVATION_OUTSIDE_COLLECTION")
    if context.lab is not None:
        from native_observe import verify_collection_sequence
        service_records=[data["data"]["objectTarget"],*[item["service"] for item in data["data"]["derived"]]]
        verify_collection_sequence(context,service_records)
        for record in service_records:
            if record.get('schemaVersion')=='RepositoryLabNativeCollection/v1':
                need(timestamp(data['startedAt'])<=timestamp(record['startedAt'])<=timestamp(record['finishedAt'])<=timestamp(data['finishedAt']),
                     'NATIVE_COLLECTION_OUTSIDE_DATA_OBSERVATION')
                for phase in ('before','after'):
                    probe=context.record(record[phase]['responsePin'])['payload']
                    need(timestamp(data['startedAt'])<=timestamp(probe['probeStartedAt'])<=timestamp(probe['probeFinishedAt'])<=timestamp(data['finishedAt']),
                         'NATIVE_PROBE_OUTSIDE_DATA_OBSERVATION')
    verify_data(baseline["data"], data["data"], policy["requireDeletedReferenceObjects"])
    before = context.observation(policy["protectionBeforePin"], "protection")
    after = context.observation(policy["protectionAfterPin"], "protection")
    need(timestamp(before["finishedAt"]) <= timestamp(data["startedAt"]) and
         timestamp(data["finishedAt"]) <= timestamp(after["startedAt"]), "PROTECTION_OBSERVATION_ORDER")
    need(timestamp(before["finishedAt"]) <= min(timestamp(item["startedAt"]) for item in context.restore_invocations)
         and timestamp(after["startedAt"]) >= max(timestamp(item["finishedAt"]) for item in context.application_invocations),
         "PROTECTION_DOES_NOT_COVER_RESTORE")
    verify_protection(before["data"], after["data"], policy["protectedScopes"],
                      target["sideEffectIsolationPin"], application["sideEffectIsolationPin"])
    browser = context.observation(policy["playwrightObservationPin"], "playwright")
    collection_pins = context.trace["collectionInvocationPins"]
    from core import pins
    pins(collection_pins)
    collection_records = [context.record(pin) for pin in collection_pins]
    need({item["stage"] for item in collection_records} == {"COLLECT_DATA", "COLLECT_PLAYWRIGHT"},
         "COLLECTION_ORIGINAL_CALLS_REQUIRED")
    for pin, item in zip(collection_pins, collection_records):
        expected = policy["dataObservationPin"] if item["stage"] == "COLLECT_DATA" else policy["playwrightObservationPin"]
        from collection_originals import collection_invocation
        collection_invocation(context, pin, item["stage"], expected, policy["verificationTargetPin"])
    need(timestamp(before["finishedAt"]) <= timestamp(browser["startedAt"]) and
         timestamp(browser["finishedAt"]) <= timestamp(after["startedAt"]), "BROWSER_PROTECTION_ORDER")
    verify_user_paths(browser["data"], policy["requiredUserPaths"], identity)
    browser_pins = [policy["playwrightObservationPin"]]
    for path in browser["data"]["paths"]:
        context.read(path["screenshotPin"])
        browser_pins.append(path["screenshotPin"])
        if path["download"] is not None:
            download = path["download"]
            context.read(download["contentPin"])
            need(download["contentPin"]["bytes"] == download["expectedBytes"] and
                 download["contentPin"]["sha256"] == download["expectedSha256"],
                 "DOWNLOAD_ORIGINAL_CONTENT_MISMATCH", "FAILED")
            browser_pins.append(download["contentPin"])
    timing = context.observation(policy["timingObservationPin"], "timing")
    timing_data = timing["data"]
    # The caller captures original marks; names and a duration in an author report do not
    # establish either the first restore invocation or the point/user-ready boundaries.
    first_restore = min(context.restore_invocations, key=lambda value: timestamp(value["startedAt"]))
    first_pins = [item["pin"] for item in context.restore_invocations if item["startedAt"] == first_restore["startedAt"]]
    need(any(pin_key(pin) == pin_key(timing_data["restoreStartInvocationPin"]) for pin in first_pins),
         "RTO_START_NOT_FIRST_RESTORE_INVOCATION")
    same(timing_data["userReadyObservationPin"], policy["playwrightObservationPin"], "RTO_USER_READY_UNBOUND")
    marks = context.record(timing_data["clockEvidencePin"])
    fields(marks, "schemaVersion clockDomainId restoreStartInvocationPin userReadyObservationPin "
           "restoreStartMonotonicNs userReadyMonotonicNs restoreStartUtc userReadyUtc "
           "clockUncertaintyMilliseconds", "RecoveryTimingMarks/v1")
    for key in ("restoreStartInvocationPin", "userReadyObservationPin"):
        same(marks[key], timing_data[key], "TIMING_MARK_BINDING_MISMATCH")
    for key in ("clockDomainId", "restoreStartMonotonicNs", "userReadyMonotonicNs", "clockUncertaintyMilliseconds"):
        need(type(marks[key]) is type(timing_data[key]) and marks[key] == timing_data[key], "TIMING_MARK_VALUE_MISMATCH")
    need(marks["restoreStartUtc"] == first_restore["startedAt"] and marks["userReadyUtc"] == browser["finishedAt"],
         "RTO_OBSERVATION_BOUNDARY_MISMATCH")
    point_time = context.record(timing_data["recoveryPointEvidencePin"])
    fields(point_time, "schemaVersion backupPointPin recoveryPoint utc", "RecoveryPointTimestamp/v1")
    same(point_time["backupPointPin"], plan["candidatePin"], "RPO_BACKUP_POINT_UNBOUND")
    need(point_time["recoveryPoint"] == plan["recoveryPoint"] and
         point_time["utc"] == timing_data["recoveryPointUtc"], "RPO_COMMON_POINT_TIME_MISMATCH")
    disruption = context.record(timing_data["disruptionEvidencePin"])
    fields(disruption, "schemaVersion operationId utc", "RecoveryDisruption/v1")
    need(disruption["operationId"] == context.request["operationId"] and
         disruption["utc"] == timing_data["disruptionUtc"], "RPO_DISRUPTION_UNBOUND")
    rto, rpo, verdict = measure_timing(timing["data"], policy["rtoObjectiveMilliseconds"],
                                    policy["rpoObjectiveMilliseconds"], policy["timingObservationPin"])
    elapsed_wall_ms = (timestamp(marks["userReadyUtc"]) - timestamp(marks["restoreStartUtc"])).total_seconds() * 1000
    need(abs(elapsed_wall_ms - rto["observedMilliseconds"]) <= 2 * timing_data["clockUncertaintyMilliseconds"] + 1,
         "TIMING_CLOCK_DISCONTINUITY", "UNKNOWN")
    evidence = [data, before, after, browser, timing]
    oldest = min(timestamp(record["finishedAt"]) for record in evidence)
    age = (dt.datetime.now(dt.timezone.utc) - oldest).total_seconds() * 1000
    need(0 <= age <= policy["maxAgeMilliseconds"], "RECOVERY_EVIDENCE_EXPIRED", "STALE")
    report = make_report(context, verdict)
    report["dataEvidencePins"] = [policy[key] for key in (
        "recoveryTargetPin", "verificationTargetPin", "dataBaselinePin", "dataObservationPin", "protectionBeforePin", "protectionAfterPin")]
    report["dataEvidencePins"] += [context.request_pin, context.request["policyPin"],
                                   context.consumed[1], context.trust["runTracePin"], context.trust["executableScopePin"],
                                   application["sideEffectIsolationPin"], context.derived_inventory_pin]
    if policy["derivedBaselinePin"] is not None:
        report["dataEvidencePins"].append(policy["derivedBaselinePin"])
    report["playwrightEvidencePins"] = browser_pins
    report["rtoObservation"], report["rpoObservation"] = rto, rpo
    if verdict == "BLOCKED":
        report["invalidatedBy"] = ["RTO_OR_RPO_OBJECTIVE_UNKNOWN"]
    elif verdict == "FAILED":
        report["invalidatedBy"] = ["RTO_OR_RPO_OBJECTIVE_EXCEEDED"]
    context.recheck()
    validate(context.schema, "RecoveryVerificationReport", report)
    return report


def make_report(context, verdict, reason=None):
    request, plan = context.request, context.plan
    unknown = {"state": "UNKNOWN", "observedMilliseconds": None,
               "objectiveMilliseconds": None, "evidencePins": []}
    return {"schemaVersion": "RecoveryVerificationReport/v1", "reportId": request["requestId"] + ":verification",
            "operationId": request["operationId"], "restoreId": plan["restoreId"], "mode": request["mode"],
            "backupAndChainPins": plan["orderedChainPins"], "planPin": request["inputPins"]["restorePlan"],
            "targetIdentityPin": context.target_pin, "sourceScopePin": context.source_pin,
            "toolAndVersionPins": plan["toolPins"] + plan["supportedVersionPins"],
            "restoreResultPin": request["inputPins"]["restoreExecutionResult"],
            "applicationStartPin": request["inputPins"]["applicationStartResult"],
            "dataEvidencePins": [], "playwrightEvidencePins": [], "rtoObservation": dict(unknown),
            "rpoObservation": dict(unknown), "targetApprovalRefs": request["authorizationRefs"],
            "verdict": verdict, "invalidatedBy": [reason] if reason else []}


def run(request_path, output_path, trust_pin):
    started = now()
    # Raw request parse errors never echo its potentially secret-bearing contents.
    request_raw = raw_file(str(absolute(request_path)))
    request = parse(request_raw)
    need(type(request) is dict and all(type(request.get(key)) is str and request[key]
         for key in ("operationId", "requestId", "action")), "REQUEST_IDENTITY_REQUIRED")
    request_pin = {"path": str(absolute(request_path)), "bytes": len(request_raw), "sha256": digest(request_raw)}
    output = absolute(output_path)
    need(not output.exists() and not Path(str(output) + ".report.json").exists(), "OUTPUT_ALREADY_EXISTS")
    need(str(output) != request_pin["path"], "OUTPUT_INPUT_COLLISION")
    context, report, failure, code = None, None, None, 1
    try:
        deadline = Deadline(request["deadlineMilliseconds"])
        need(trust_pin is not None, "CALLER_TRUST_PIN_REQUIRED")
        context = EvidenceContext(request, request_pin, trust_pin, deadline)
        report = verify(context)
        code = 0 if report["verdict"] == "PASSED" else 1
        failure = None if code == 0 else report["invalidatedBy"][0]
    except VerificationError as error:
        failure = error.code
        code = 2 if error.verdict == "UNKNOWN" else 1
        if context is not None and hasattr(context, "plan") and hasattr(context, "target_pin"):
            report = make_report(context, error.verdict, failure)
    except (OSError, KeyError, TypeError, ValueError, ImportError, MemoryError) as error:
        failure = "VERIFIER_" + type(error).__name__.upper()
        code = 1
    original_pins = list(context.consumed) if context else [request_pin]
    if report is not None:
        validate(context.schema, "RecoveryVerificationReport", report)
        original_pins.append(write_atomic(str(output) + ".report.json", report))
    result = {"schemaVersion": "backup-restore-operation-result/v1", "operationId": request["operationId"],
              "requestId": request["requestId"], "action": request["action"],
              "state": "SUCCEEDED" if code == 0 else "TERMINAL_UNKNOWN" if code == 2 else "FAILED_RETAINED",
              "failureCode": failure, "message": ("Same-host lab REHEARSAL verified; no production, NAS or cutover acceptance"
                  if context is not None and context.lab is not None else "Recovery evidence verified") if code == 0 else failure,
              "data": report, "originalResultPins": original_pins, "startedAt": started, "finishedAt": now(),
              "actualExitCode": None}
    if context is not None:
        validate(context.schema, "OperationResult", result)
    write_atomic(output, result)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        configured = os.environ.get("RECOVERY_VERIFICATION_TRUST_PIN")
        trust = parse(configured.encode("utf-8")) if configured is not None else None
        return run(args.request, args.output, trust)
    except VerificationError as error:
        print(error.code, file=sys.stderr)
        return 2 if error.verdict == "UNKNOWN" else 1
    except (OSError, ValueError, TypeError, ImportError) as error:
        print("VERIFIER_" + type(error).__name__.upper(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
