"""Read-only controlled admission from caller-selected signed recovery originals."""
import base64
import binascii
import datetime as dt
import time

from core import (MAX_JSON_BYTES, canonical, fields, need, now, parse, pin_key,
                  pins, same, text, timestamp, VerificationError)


def read_original_graph(context, root_pin):
    """Rehash each referenced original under the current caller's admission gate."""
    pending, visited = [root_pin], set()
    while pending:
        context.deadline.remaining()
        pin = pending.pop()
        key = pin_key(pin)
        if key in visited:
            continue
        lab_selected = hasattr(context, "lab") and context.lab is not None
        need(len(visited) < (4096 if lab_selected else 10000), "EVIDENCE_GRAPH_LIMIT")
        visited.add(key)
        context.read(pin)
        if pin["bytes"] > MAX_JSON_BYTES:
            continue
        raw = context.read(pin, content=True)
        if not raw.lstrip().startswith((b"{", b"[")):
            continue
        values = [parse(raw)]
        while values:
            context.deadline.remaining()
            value = values.pop()
            if type(value) is dict:
                # JSON Schema's Pin.properties has these same names, but its
                # values describe types rather than selecting an original file.
                if set(value) == {"path", "bytes", "sha256"} and type(value["path"]) is str and \
                        type(value["bytes"]) is int and type(value["sha256"]) is str:
                    pin_key(value)
                    pending.append(value)
                else:
                    values.extend(value.values())
            elif type(value) is list:
                values.extend(value)


def independently_selected(context, pin):
    need(pin_key(pin) in set(pins(context.trust["independentOriginalPins"])),
         "CONTROLLED_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
    context.read(pin)


def unexpired(context, value, code):
    current = dt.datetime.now(dt.timezone.utc)
    end = timestamp(value)
    need(current < end, code, "STALE")
    context.deadline.end = min(context.deadline.end, time.monotonic() + (end - current).total_seconds())


def signed_approval(context, eligibility):
    """Use the exact W03/W04 RepositorySignedRecord/v1 Ed25519 protocol."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    approval_pin = eligibility["approvalPin"]
    independently_selected(context, approval_pin)
    signed = context.record(approval_pin)
    fields(signed, "schemaVersion keySha256 payload signature", "RepositorySignedRecord/v1")
    keys = eligibility["repositoryEvidenceKeyPins"]
    pins(keys)
    for pin in keys:
        independently_selected(context, pin)
    selected = [pin for pin in keys if pin["sha256"] == signed["keySha256"]]
    need(len(selected) == 1, "CONTROLLED_APPROVAL_KEY_NOT_SELECTED")
    try:
        key = serialization.load_pem_public_key(context.read(selected[0], content=True))
        need(isinstance(key, Ed25519PublicKey), "CONTROLLED_APPROVAL_ED25519_REQUIRED")
        key.verify(base64.b64decode(signed["signature"], validate=True), canonical(signed["payload"]))
    except (InvalidSignature, ValueError, TypeError, binascii.Error) as error:
        raise VerificationError("CONTROLLED_APPROVAL_SIGNATURE_INVALID") from error
    approval = signed["payload"]
    fields(approval, "schemaVersion repositoryId reportPin targetIdentityPin sourceIdentityPin validUntil",
           "RepositoryRecoveryApproval/v1")
    need(text(approval["repositoryId"]) == eligibility["repositoryId"], "CONTROLLED_APPROVAL_REPOSITORY_MISMATCH")
    same(approval["reportPin"], eligibility["reportPin"], "CONTROLLED_APPROVAL_REPORT_MISMATCH")
    same(approval["targetIdentityPin"], context.target_pin, "CONTROLLED_APPROVAL_TARGET_MISMATCH")
    same(approval["sourceIdentityPin"], context.business_scope["sourceIdentityPin"],
         "CONTROLLED_APPROVAL_SOURCE_MISMATCH")
    unexpired(context, approval["validUntil"], "CONTROLLED_APPROVAL_EXPIRED")
    return approval


def verify_controlled_eligibility(context, policy):
    """Retain immutable COMPLETE points; derive eligibility from current evidence."""
    eligibility_pin = policy["controlledEligibilityPin"]
    need(eligibility_pin is not None, "CONTROLLED_ELIGIBILITY_REQUIRED")
    independently_selected(context, context.request["policyPin"])
    independently_selected(context, eligibility_pin)
    eligibility = context.record(eligibility_pin)
    fields(eligibility, "schemaVersion repositoryId sourceScopePin targetIdentityPin candidatePin orderedChainPins "
           "recoveryPoint reportPin approvalPin repositoryEvidenceKeyPins validUntil", "RecoveryControlledEligibility/v1")
    text(eligibility["repositoryId"])
    same(eligibility["sourceScopePin"], context.source_pin, "CONTROLLED_SOURCE_SCOPE_MISMATCH")
    same(eligibility["targetIdentityPin"], context.target_pin, "CONTROLLED_TARGET_MISMATCH")
    same(eligibility["candidatePin"], context.plan["candidatePin"], "CONTROLLED_CANDIDATE_MISMATCH")
    need(pins(eligibility["orderedChainPins"]) == pins(context.plan["orderedChainPins"]),
         "CONTROLLED_CHAIN_MISMATCH", "STALE")
    need(eligibility["recoveryPoint"] == context.plan["recoveryPoint"], "CONTROLLED_POINT_MISMATCH", "STALE")
    unexpired(context, eligibility["validUntil"], "CONTROLLED_ELIGIBILITY_EXPIRED")
    signed_approval(context, eligibility)
    report_pin = eligibility["reportPin"]
    independently_selected(context, report_pin)
    ancestry = getattr(context, "eligibility_ancestry", ())
    need(pin_key(report_pin) not in ancestry and len(ancestry) < 32, "CONTROLLED_REPORT_ANCESTRY_INVALID")
    report = context.record(report_pin, "RecoveryVerificationReport")
    need(report["verdict"] == "PASSED" and report["invalidatedBy"] == [], "CONTROLLED_REPORT_NOT_CURRENT_PASSED")
    same(report["sourceScopePin"], context.source_pin, "CONTROLLED_REPORT_SOURCE_MISMATCH")
    same(report["targetIdentityPin"], context.target_pin, "CONTROLLED_REPORT_TARGET_MISMATCH")
    need(pins(report["backupAndChainPins"]) == pins(context.plan["orderedChainPins"]),
         "CONTROLLED_REPORT_CHAIN_MISMATCH", "STALE")
    need(pins(report["toolAndVersionPins"]) == pins(context.plan["toolPins"] + context.plan["supportedVersionPins"]),
         "CONTROLLED_REPORT_VERSION_MISMATCH", "STALE")
    prior_plan = context.record(report["planPin"], "RestorePlan")
    same(prior_plan["candidatePin"], context.plan["candidatePin"], "CONTROLLED_REPORT_CANDIDATE_MISMATCH")
    need(prior_plan["recoveryPoint"] == context.plan["recoveryPoint"], "CONTROLLED_REPORT_POINT_MISMATCH", "STALE")
    need(pins(prior_plan["orderedChainPins"]) == pins(context.plan["orderedChainPins"]),
         "CONTROLLED_REPORT_PLAN_CHAIN_MISMATCH", "STALE")
    need(pins(prior_plan["toolPins"]) == pins(context.plan["toolPins"]) and
         pins(prior_plan["supportedVersionPins"]) == pins(context.plan["supportedVersionPins"]),
         "CONTROLLED_REPORT_PLAN_VERSION_MISMATCH", "STALE")

    # A producer's PASSED label cannot establish actual data, browser or native exits.
    # Before rebuilding the report, admit its entire original graph in CURRENT trust.
    read_original_graph(context, report_pin)
    bindings = []
    for pin in report["dataEvidencePins"]:
        raw = context.read(pin, content=True)
        if raw.lstrip().startswith(b"{"):
            value = parse(raw)
            if value.get("schemaVersion") == "RecoveryCallerBinding/v1":
                bindings.append((pin, value))
    need(len(bindings) == 1, "CONTROLLED_REPORT_CALLER_BINDING_REQUIRED")
    prior_binding_pin, prior_binding = bindings[0]
    prior_request_pin = prior_binding["requestPin"]
    need(pin_key(prior_request_pin) in set(pins(report["dataEvidencePins"])), "CONTROLLED_REPORT_REQUEST_UNBOUND")
    prior_request = context.record(prior_request_pin, "OperationRequest")
    same(prior_request["inputPins"]["restorePlan"], report["planPin"], "CONTROLLED_REPORT_PLAN_UNBOUND")
    same(prior_request["inputPins"]["restoreExecutionResult"], report["restoreResultPin"], "CONTROLLED_REPORT_RESTORE_UNBOUND")
    same(prior_request["inputPins"]["applicationStartResult"], report["applicationStartPin"], "CONTROLLED_REPORT_APPLICATION_UNBOUND")
    from evidence import EvidenceContext, report_invalidations
    from verify_recovery import verify, policy_record
    prior_context = EvidenceContext(prior_request, prior_request_pin, prior_binding_pin, context.deadline)
    prior_context.eligibility_ancestry = ancestry + (pin_key(report_pin),)
    rebuilt = verify(prior_context)
    need(canonical(rebuilt) == canonical(report), "CONTROLLED_REPORT_ORIGINAL_VERIFICATION_MISMATCH")

    bindings = {key: report[key] for key in ("backupAndChainPins", "planPin", "targetIdentityPin", "sourceScopePin",
                "toolAndVersionPins", "restoreResultPin", "applicationStartPin", "targetApprovalRefs",
                "operationId", "restoreId", "mode")}
    bindings["reportGeneratedAt"] = prior_context.trace["finishedAt"]
    need(not report_invalidations(report, bindings, policy["maxAgeMilliseconds"], now(), context.deadline),
         "CONTROLLED_REPORT_EXPIRED", "STALE")
    old_policy = policy_record(prior_context)
    from integrity import verify_data, verify_protection, verify_user_paths
    verify_data(prior_context.record(old_policy["dataBaselinePin"])["data"],
                prior_context.observation(old_policy["dataObservationPin"], "data")["data"],
                policy["requireDeletedReferenceObjects"])
    verify_protection(prior_context.observation(old_policy["protectionBeforePin"], "protection")["data"],
                      prior_context.observation(old_policy["protectionAfterPin"], "protection")["data"],
                      policy["protectedScopes"], prior_context.record(old_policy["recoveryTargetPin"])["sideEffectIsolationPin"],
                      prior_context.record(report["applicationStartPin"])["sideEffectIsolationPin"])
    verify_user_paths(prior_context.observation(old_policy["playwrightObservationPin"], "playwright")["data"],
                      policy["requiredUserPaths"], prior_context.record(old_policy["verificationTargetPin"]))
    for key in ("rto", "rpo"):
        observation = report[key + "Observation"]
        objective = policy[key + "ObjectiveMilliseconds"]
        need(observation["state"] == "MEASURED" and objective is not None and
             observation["observedMilliseconds"] <= objective, "CONTROLLED_REPORT_TIMING_NOT_PASSED")
    prior_context.recheck()
    context.recheck()
    return eligibility
