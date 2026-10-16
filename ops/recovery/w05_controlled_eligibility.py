"""W05 bounded read-only adapter to the independently pinned W06 verifier.

This private selection is not a VERIFY_RECOVERY request or run trace. W06
rebuilds the selected report using its actual original request and caller binding.
No producer can enlarge the independently selected original graph.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from recovery_environment_contract import (EnvironmentFailure, atomic_json, canonical, decode, exact,
    pin_file, read_pin, require, verify_large_pin)


def validate_admission_policy(policy, guard):
    require(policy["schemaVersion"] == "RecoveryEnvironmentPolicy/v2", "ENVIRONMENT_POLICY_V2_REQUIRED")
    originals = policy["controlledIndependentOriginalPins"]
    require(type(originals) is list and len(originals) <= 10000, "CONTROLLED_ORIGINAL_LIST_REQUIRED")
    pair = policy["controlledEligibilityPin"], policy["controlledVerificationPolicyPin"]
    if pair == (None, None):
        require(originals == [], "REHEARSAL_CONTROLLED_ORIGINALS_PROHIBITED")
        return
    require(all(pin is not None for pin in pair) and originals, "CONTROLLED_ADMISSION_PINS_REQUIRED")
    keys = [(pin["path"], pin["bytes"], pin["sha256"]) for pin in originals]
    require(len(set(keys)) == len(keys), "CONTROLLED_ORIGINAL_DUPLICATE")
    require(all(pin in originals for pin in pair), "CONTROLLED_AUTHORITY_NOT_INDEPENDENTLY_SELECTED")
    for pin in originals:
        verify_large_pin(pin, guard)


def admit_controlled(request, config, policy, trust, runner):
    validate_admission_policy(policy, runner.guard)
    require(policy["controlledEligibilityPin"] is not None, "CONTROLLED_ADMISSION_PINS_REQUIRED")
    plan_pin = request["inputPins"].get("restorePlan")
    if request["action"] == "START_APPLICATION":
        restore = read_pin(request["inputPins"]["restoreExecutionResult"])
        trust.schemas.validate(restore, "RestoreExecutionResult")
        plan_pin = restore["planPin"]
    plan = read_pin(plan_pin)
    trust.schemas.validate(plan, "RestorePlan")
    from recovery_environment import validate_plan
    validate_plan(plan, plan_pin, request, config, trust, runner.guard)
    payload = {"schemaVersion": "W05ControlledAdmissionSelection/v1", "environmentRequest": request,
        "configuration": config, "policy": policy, "plan": plan, "schemaPin": trust.value["recordSchemasPin"],
        "deadlineMilliseconds": max(1, int(runner.remaining() * 1000))}

    def failed(raw, receipt):
        failure = decode(raw)
        exact(failure, ("schemaVersion", "code", "verdict", "consumedPins"), "CONTROLLED_READER_FAILURE_INVALID")
        require(failure["schemaVersion"] == "W05ControlledAdmissionFailure/v1" and
                failure["verdict"] in ("BLOCKED", "FAILED", "STALE", "UNKNOWN"), "CONTROLLED_READER_FAILURE_INVALID")
        for pin in failure["consumedPins"]:
            require(pin in policy["controlledIndependentOriginalPins"], "CONTROLLED_READER_ADMISSION_ENLARGED")
            verify_large_pin(pin, runner.guard)
        path = runner.root / ("controlled-admission-failure-" + str(runner.sequence) + ".json")
        atomic_json(path, {**failure, "localInvocation": receipt})
        return {"evidencePin": pin_file(path), "code": failure["code"], "unknown": failure["verdict"] == "UNKNOWN"}

    raw = runner.run([config["pythonPin"]["path"], "-I", str(Path(__file__).resolve())],
                     stdin=canonical(payload), failure_observer=failed)
    value = decode(raw)
    exact(value, ("schemaVersion", "eligibility", "consumedPins", "protectionReportPin", "validUntil"), "CONTROLLED_READER_RESULT_INVALID")
    require(value["schemaVersion"] == "W05ControlledAdmission/v1", "CONTROLLED_READER_RESULT_INVALID")
    require(value["eligibility"] == read_pin(policy["controlledEligibilityPin"]), "CONTROLLED_READER_ELIGIBILITY_MISMATCH")
    conditions = config["controlledPreconditions"]
    expected_protection = conditions["verificationReportPin"] if conditions["restoreKind"] == "REPLACE_EXISTING" else None
    require(value["protectionReportPin"] == expected_protection, "CONTROLLED_PROTECTION_READER_BINDING_MISMATCH")
    from datetime import datetime, timezone
    from recovery_environment_contract import utc
    remaining_validity = (utc(value["validUntil"]) - datetime.now(timezone.utc)).total_seconds()
    require(remaining_validity > 0, "CONTROLLED_ADMISSION_EXPIRED_BEFORE_USE")
    runner.deadline = min(runner.deadline, time.monotonic() + remaining_validity)
    if runner.admission_valid_until is None or utc(value["validUntil"]) < utc(runner.admission_valid_until):
        runner.admission_valid_until = value["validUntil"]
    runner.guard()
    for pin in value["consumedPins"]:
        require(pin in policy["controlledIndependentOriginalPins"], "CONTROLLED_READER_ADMISSION_ENLARGED")
        verify_large_pin(pin, runner.guard)
    path = runner.root / ("controlled-admission-" + str(runner.sequence) + ".json")
    atomic_json(path, {**value, "environmentPolicyPin": request["policyPin"],
                      "verificationPolicyPin": policy["controlledVerificationPolicyPin"],
                      "originalInvocationPin": runner.pins[-1]})
    runner.pins.append(pin_file(path))
    runner.guard()
    return value["eligibility"]


def verify_protection_report(context, policy, eligibility, conditions):
    """Admit a distinct protection backup without deriving authority from its report."""
    from core import canonical as utf8_json, need, now, parse, pin_key, pins, same
    from controlled_eligibility import independently_selected, read_original_graph, signed_approval
    from evidence import EvidenceContext, report_invalidations
    from verify_recovery import verify, policy_record
    from integrity import verify_data, verify_protection, verify_user_paths

    point_pin, report_pin = conditions["protectionPointPin"], conditions["verificationReportPin"]
    independently_selected(context, point_pin)
    independently_selected(context, report_pin)
    point = context.record(point_pin, "RepositoryPoint")
    need(point["integrityState"] == "COMPLETE" and point["blockedReason"] in
         (None, "REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED") and point["rehearsalEligible"] is True,
         "PROTECTION_POINT_INCOMPLETE")
    report = context.record(report_pin, "RecoveryVerificationReport")
    need(report["verdict"] == "PASSED" and report["invalidatedBy"] == [], "PROTECTION_REPORT_NOT_CURRENT_PASSED")
    same(report["sourceScopePin"], context.source_pin, "PROTECTION_REPORT_SOURCE_MISMATCH")
    same(report["targetIdentityPin"], context.target_pin, "PROTECTION_REPORT_TARGET_MISMATCH")
    # Only caller-selected approvals and the current explicitly selected authority
    # keys are eligible. No report-provided key can authorize the protection point.
    approvals = []
    for pin in context.trust["independentOriginalPins"]:
        context.deadline.remaining()
        if pin["bytes"] > 64 * 1024 * 1024:
            continue
        raw = context.read(pin, content=True)
        if not raw.lstrip().startswith(b"{"):
            continue
        value = parse(raw)
        if type(value) is dict and value.get("schemaVersion") == "RepositorySignedRecord/v1" and \
                type(value.get("payload")) is dict and value["payload"].get("reportPin") == report_pin:
            approvals.append(pin)
    need(len(approvals) == 1, "PROTECTION_SIGNED_APPROVAL_NOT_INDEPENDENTLY_SELECTED")
    signed_approval(context, {**eligibility, "reportPin": report_pin, "approvalPin": approvals[0]})
    read_original_graph(context, report_pin)
    bindings = []
    for pin in report["dataEvidencePins"]:
        raw = context.read(pin, content=True)
        if raw.lstrip().startswith(b"{"):
            value = parse(raw)
            if type(value) is dict and value.get("schemaVersion") == "RecoveryCallerBinding/v1":
                bindings.append((pin, value))
    need(len(bindings) == 1, "PROTECTION_REPORT_CALLER_BINDING_REQUIRED")
    binding_pin, binding = bindings[0]
    request_pin = binding["requestPin"]
    need(pin_key(request_pin) in set(pins(report["dataEvidencePins"])), "PROTECTION_REPORT_REQUEST_UNBOUND")
    original = context.record(request_pin, "OperationRequest")
    for key, field in (("restorePlan", "planPin"), ("restoreExecutionResult", "restoreResultPin"),
                       ("applicationStartResult", "applicationStartPin")):
        same(original["inputPins"][key], report[field], "PROTECTION_REPORT_REQUEST_UNBOUND")
    plan = context.record(report["planPin"], "RestorePlan")
    same(plan["candidatePin"], point_pin, "PROTECTION_REPORT_CANDIDATE_MISMATCH")
    need(plan["recoveryPoint"] == point["commonRecoveryPoint"] and
         pins(plan["orderedChainPins"]) == pins(report["backupAndChainPins"]) and
         pins(plan["toolPins"] + plan["supportedVersionPins"]) == pins(report["toolAndVersionPins"]),
         "PROTECTION_REPORT_PLAN_MISMATCH")
    prior = EvidenceContext(original, request_pin, binding_pin, context.deadline)
    prior.eligibility_ancestry = (pin_key(report_pin),)
    need(utf8_json(verify(prior)) == utf8_json(report), "PROTECTION_REPORT_ORIGINAL_VERIFICATION_MISMATCH")
    report_bindings = {key: report[key] for key in ("backupAndChainPins", "planPin", "targetIdentityPin", "sourceScopePin",
        "toolAndVersionPins", "restoreResultPin", "applicationStartPin", "targetApprovalRefs", "operationId", "restoreId", "mode")}
    report_bindings["reportGeneratedAt"] = prior.trace["finishedAt"]
    need(not report_invalidations(report, report_bindings, policy["maxAgeMilliseconds"], now(), context.deadline),
         "PROTECTION_REPORT_EXPIRED")
    context.limit_report_age(prior.trace["finishedAt"], policy["maxAgeMilliseconds"])
    old = policy_record(prior)
    verify_data(prior.record(old["dataBaselinePin"])["data"], prior.observation(old["dataObservationPin"], "data")["data"],
                policy["requireDeletedReferenceObjects"])
    verify_protection(prior.observation(old["protectionBeforePin"], "protection")["data"],
        prior.observation(old["protectionAfterPin"], "protection")["data"], policy["protectedScopes"],
        prior.record(old["recoveryTargetPin"])["sideEffectIsolationPin"], prior.record(report["applicationStartPin"])["sideEffectIsolationPin"])
    verify_user_paths(prior.observation(old["playwrightObservationPin"], "playwright")["data"],
                      policy["requiredUserPaths"], context.record(policy["verificationTargetPin"]))
    for key in ("rto", "rpo"):
        observation, objective = report[key + "Observation"], policy[key + "ObjectiveMilliseconds"]
        need(observation["state"] == "MEASURED" and objective is not None and observation["observedMilliseconds"] <= objective,
             "PROTECTION_REPORT_TIMING_NOT_PASSED")
    prior.recheck()
    context.recheck()
    return report_pin


def verify_selection(selection):
    """Pure evidence reads; no browser, service, SQL or repository mutation."""
    exact(selection, ("schemaVersion", "environmentRequest", "configuration", "policy", "plan", "schemaPin",
                      "deadlineMilliseconds"), "CONTROLLED_SELECTION_INVALID")
    require(selection["schemaVersion"] == "W05ControlledAdmissionSelection/v1", "CONTROLLED_SELECTION_INVALID")
    budget = selection["deadlineMilliseconds"]
    require(type(budget) is int and 0 < budget <= 86400000, "CONTROLLED_READER_DEADLINE_INVALID")
    end = time.monotonic() + budget / 1000
    def guard():
        require(time.monotonic() < end, "DEADLINE_EXCEEDED")
    policy, config = selection["policy"], selection["configuration"]
    validate_admission_policy(policy, guard)
    originals = policy["controlledIndependentOriginalPins"]
    verifier_root = Path(__file__).resolve().parents[2] / "scripts" / "recovery_verification"
    expected = {os.path.normcase(str(path.resolve())) for path in verifier_root.glob("*.py")}
    require(bool(expected), "CONTROLLED_VERIFIER_SOURCE_MISSING")
    expected.add(os.path.normcase(str(Path(sys.executable).resolve())))
    admitted_paths = {os.path.normcase(str(Path(pin["path"]).resolve())) for pin in originals}
    require(expected <= admitted_paths and pin_file(sys.executable) == config["pythonPin"],
            "CONTROLLED_VERIFIER_SOURCE_CLOSURE_NOT_SELECTED")
    # A fresh isolated process avoids module-name collision with other executors.
    sys.path.insert(0, str(verifier_root))
    from core import Deadline, VerificationError, frozen_schema, need, parse, pin_key, read_pin as original_read, validate
    from controlled_eligibility import verify_controlled_eligibility, read_original_graph
    from verify_recovery import policy_record

    class ReadOnlyContext:
        def __init__(self):
            self.deadline = Deadline(budget)
            self.deadline.end = end
            # Private policy selectors only; no fabricated operation/request Pin.
            self.request = {"policyPin": policy["controlledVerificationPolicyPin"], "mode": "CONTROLLED_RESTORE"}
            self.trust = {"independentOriginalPins": originals}
            self.admitted = {pin_key(pin) for pin in originals}
            self.consumed = []
            self.valid_until = None
            self.read(selection["schemaPin"])
            self.schema = frozen_schema(selection["schemaPin"])
            self.source_pin, self.target_pin = config["sourceScopePin"], config["targetIdentityPin"]
            self.business_scope = self.record(self.source_pin)
            self.record(self.business_scope["sourceIdentityPin"])
            target = self.record(self.target_pin)
            need(target["sourceIdentityPin"] == self.business_scope["sourceIdentityPin"], "CONTROLLED_TARGET_SOURCE_MISMATCH")
            self.plan = selection["plan"]

        def read(self, pin, content=False):
            self.deadline.remaining()
            need(pin_key(pin) in self.admitted, "ORIGINAL_NOT_CALLER_PINNED")
            raw = original_read(pin, self.deadline, content=content)
            if pin not in self.consumed:
                self.consumed.append(pin)
            return raw

        def record(self, pin, definition=None):
            value = parse(self.read(pin, content=True))
            if definition:
                validate(self.schema, definition, value)
            return value

        def recheck(self):
            for pin in originals:
                self.deadline.remaining()
                original_read(pin, self.deadline, content=False)

        def limit_report_age(self, generated, milliseconds):
            import datetime as dt
            from core import timestamp
            expires = timestamp(generated) + dt.timedelta(milliseconds=milliseconds)
            remaining = (expires - dt.datetime.now(dt.timezone.utc)).total_seconds()
            need(remaining > 0, "CONTROLLED_REPORT_EXPIRED")
            self.valid_until = expires if self.valid_until is None else min(self.valid_until, expires)
            self.deadline.end = min(self.deadline.end, time.monotonic() + remaining)

    context = ReadOnlyContext()
    try:
        current = policy_record(context)
        need(current["controlledEligibilityPin"] == policy["controlledEligibilityPin"], "CONTROLLED_ELIGIBILITY_SELECTION_MISMATCH")
        read_original_graph(context, policy["controlledVerificationPolicyPin"])
        target = context.record(current["recoveryTargetPin"], "RecoveryTarget")
        need(target["targetIdentityPin"] == context.target_pin, "CONTROLLED_POLICY_RECOVERY_TARGET_MISMATCH")
        need(target["versionPins"] == context.plan["supportedVersionPins"], "CONTROLLED_POLICY_TARGET_VERSION_MISMATCH")
        verification_target = context.record(current["verificationTargetPin"])
        need(verification_target["schemaVersion"] == "RecoveryVerificationTarget/v1" and
             verification_target["targetIdentityPin"] == context.target_pin,
             "CONTROLLED_POLICY_VERIFICATION_TARGET_MISMATCH")
        context.recheck()
        eligibility = verify_controlled_eligibility(context, current)
        from core import timestamp
        report = context.record(eligibility["reportPin"])
        for pin in report["dataEvidencePins"]:
            raw = context.read(pin, content=True)
            if raw.lstrip().startswith(b"{"):
                record = parse(raw)
                if type(record) is dict and record.get("schemaVersion") == "RecoveryCallerBinding/v1":
                    trace = context.record(record["runTracePin"])
                    context.limit_report_age(trace["finishedAt"], current["maxAgeMilliseconds"])
                    prior_request = context.record(record["requestPin"], "OperationRequest")
                    prior_policy = context.record(prior_request["policyPin"])
                    from integrity import verify_user_paths
                    verify_user_paths(context.record(prior_policy["playwrightObservationPin"])["data"],
                                      current["requiredUserPaths"], verification_target)
        expiry = min(timestamp(eligibility["validUntil"]),
                     timestamp(context.record(eligibility["approvalPin"])["payload"]["validUntil"]))
        context.valid_until = expiry if context.valid_until is None else min(context.valid_until, expiry)
        protection_pin = None
        conditions = config.get("controlledPreconditions")
        if conditions is not None and conditions["restoreKind"] == "REPLACE_EXISTING":
            protection_pin = verify_protection_report(context, current, eligibility, conditions)
        # signed_approval/unexpired also bound the shared reader clock. Convert
        # its remaining validity to a UTC upper bound for the outer executor.
        import datetime as dt
        clock_expiry = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=context.deadline.remaining())
        context.valid_until = min(context.valid_until, clock_expiry)
    except VerificationError as failure:
        failure.consumed_pins = context.consumed
        raise
    return {"schemaVersion": "W05ControlledAdmission/v1", "eligibility": eligibility,
            "consumedPins": context.consumed, "protectionReportPin": protection_pin,
            "validUntil": context.valid_until.isoformat().replace("+00:00", "Z")}


def main():
    try:
        raw = sys.stdin.buffer.read(16 * 1024 * 1024 + 1)
        require(len(raw) <= 16 * 1024 * 1024, "CONTROLLED_SELECTION_INPUT_LIMIT")
        selection = decode(raw)
        value = verify_selection(selection)
    except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError, ImportError) as failure:
        value = {"schemaVersion": "W05ControlledAdmissionFailure/v1",
            "code": getattr(failure, "code", "CONTROLLED_READER_" + type(failure).__name__.upper()),
            "verdict": getattr(failure, "verdict", "UNKNOWN" if getattr(failure, "unknown", False) else "BLOCKED"),
            "consumedPins": getattr(failure, "consumed_pins", [])}
        sys.stdout.buffer.write(canonical(value) + b"\n")
        return 1
    sys.stdout.buffer.write(canonical(value) + b"\n")
    return 0


if __name__ == "__main__":
    # -I excludes the adjacent source directory; only this pinned directory is loaded.
    raise SystemExit(main())
