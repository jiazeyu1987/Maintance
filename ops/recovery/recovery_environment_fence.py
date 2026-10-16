"""Read-only W05 consumer of W04's controlled source fence handoff."""
import os
from pathlib import Path

from recovery_environment_contract import (EnvironmentFailure, decode, exact, original_w04_exits,
    read_pin, require, utc, utc_now, verify_large_pin)

CONTEXT_KEY = "RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN"


def controlled_handoff(request, config, policy, guard, schemas):
    require(request["mode"] == "CONTROLLED_RESTORE", "CONTROLLED_FENCE_MODE_REQUIRED")
    raw = os.environ.get(CONTEXT_KEY)
    require(raw is not None, "CONTROLLED_FENCE_HANDOFF_REQUIRED")
    ref = decode(raw.encode("utf-8")); value = read_pin(ref)
    exact(value, ("schemaVersion", "operationId", "originalRequestPin", "planPin", "targetIdentityPin", "sourceScopePin",
                  "selectedPointPin", "leaseRef", "sourceFencePin", "sourceFencePointEvidencePin"), "CONTROLLED_FENCE_HANDOFF_INVALID")
    require(value["schemaVersion"] == "RecoveryControlledFenceHandoff/v1" and
            value["operationId"] == request["operationId"] and value["targetIdentityPin"] == config["targetIdentityPin"] and
            value["sourceScopePin"] == config["sourceScopePin"] and value["selectedPointPin"] == request["selectedPointPin"] and
            value["leaseRef"] == request["leaseRef"], "CONTROLLED_FENCE_HANDOFF_BINDING_INVALID")
    original = read_pin(value["originalRequestPin"]); plan = read_pin(value["planPin"])
    schemas.validate(original, "OperationRequest"); schemas.validate(plan, "RestorePlan")
    require(original["action"] == "CONTROLLED_CUTOVER" and original["mode"] == plan["mode"] == request["mode"] and
            all(original[key] == request[key] for key in ("operationId", "selectedPointPin", "sourceOrTargetRef", "policyPin",
                                                         "authorizationRefs", "leaseRef")) and
            plan["operationId"] == request["operationId"] and plan["candidatePin"] == request["selectedPointPin"] and
            plan["targetRef"] == request["sourceOrTargetRef"] and plan["leaseRef"] == request["leaseRef"] and
            plan["sideEffectPolicyPin"] == request["policyPin"] and plan["authorizationRefs"] == request["authorizationRefs"] and
            plan["plannedWrites"] and all(write["targetIdentityPin"] == config["targetIdentityPin"] for write in plan["plannedWrites"]),
            "CONTROLLED_FENCE_ORIGINAL_REQUEST_INVALID")
    actual_plan_pin = request["inputPins"]["restorePlan"] if request["action"] == "PREPARE_TARGET" else \
                      read_pin(request["inputPins"]["restoreExecutionResult"])["planPin"]
    require(actual_plan_pin == value["planPin"], "CONTROLLED_FENCE_CURRENT_PLAN_MISMATCH")
    verifier_ref = policy.get("controlledFenceVerificationPin")
    require(type(verifier_ref) is dict, "CONTROLLED_FENCE_VERIFIER_REQUIRED")
    verifier = read_pin(verifier_ref)
    exact(verifier, ("schemaVersion", "targetIdentityPin", "sourceScopePin", "trustEnvironmentKeys", "moduleSourcePins"),
          "CONTROLLED_FENCE_VERIFIER_INVALID")
    require(verifier["schemaVersion"] == "RecoveryEnvironmentControlledFenceVerification/v1" and
            verifier["targetIdentityPin"] == config["targetIdentityPin"] and verifier["sourceScopePin"] == config["sourceScopePin"] and
            verifier["trustEnvironmentKeys"] == ["RECOVERY_DATA_TRUST_FILE", "RECOVERY_DATA_TRUST_SHA256"],
            "CONTROLLED_FENCE_VERIFIER_SCOPE_INVALID")
    root = Path(__file__).parent
    closure = {root / "recovery_cli.py", *root.glob("recovery_engine*.py"),
               *root.glob("recovery_plan*.py"), *root.glob("recovery_cutover*.py"), *root.glob("recovery_data*.py")}
    require({Path(pin["path"]) for pin in verifier["moduleSourcePins"]} == closure,
            "CONTROLLED_FENCE_VERIFIER_CLOSURE_REQUIRED")
    for pin in verifier["moduleSourcePins"]:
        verify_large_pin(pin, guard)
    from recovery_plan import trusted_configuration
    from recovery_engine import RecoveryError
    require(Path(trusted_configuration.__code__.co_filename).resolve() == root / "recovery_plan.py",
            "CONTROLLED_FENCE_LOADED_CONSUMER_MISMATCH")
    try:
        data_trust, data_policy, data_config = trusted_configuration(original)
    except RecoveryError as error:
        raise EnvironmentFailure(error.code, unknown=getattr(error, "unknown", False)) from error
    require(data_policy["schemaVersion"] == "RecoveryDataPolicy/v1" and data_policy["environmentPolicyPin"] == request["policyPin"] and
            data_policy["sourceScopePin"] == config["sourceScopePin"] and data_policy["recordSchemasPin"] == policy["recordSchemasPin"] and
            read_pin(data_policy["dataTargetPin"])["targetIdentityPin"] == config["targetIdentityPin"] and data_config == config,
            "CONTROLLED_FENCE_DATA_POLICY_MISMATCH")
    # Approved W04 consumers own their actual recipe, remote signature, native
    # PID/wait and selected repository material parsing. Reuse their verified
    # read-only consumer after verifying its complete source closure.
    from recovery_cutover_fence import fence_handoff
    require(Path(fence_handoff.__code__.co_filename).resolve() == root / "recovery_cutover_fence.py",
            "CONTROLLED_FENCE_LOADED_CONSUMER_MISMATCH")
    try:
        require(fence_handoff(request, data_policy) == value, "CONTROLLED_FENCE_CONSUMER_CHANGED")
    except RecoveryError as error:
        raise EnvironmentFailure(error.code, unknown=getattr(error, "unknown", False)) from error
    source = read_pin(config["sourceScopePin"]); fence = read_pin(value["sourceFencePin"])
    exact(fence, ("schemaVersion", "operationId", "sourceIdentityPin", "state", "writerCoverage", "leaseRef", "observedAt",
                  "expiresAt", "originalInvocationPins", "retainedSourceResources"), "SOURCE_FENCE_INVALID")
    require(fence["schemaVersion"] == "RecoverySourceFence/v1" and fence["operationId"] == request["operationId"] and
            fence["sourceIdentityPin"] == source["sourceIdentityPin"] and fence["state"] == "ENFORCED" and
            fence["leaseRef"] == request["leaseRef"] and fence["retainedSourceResources"] is True and
            set(fence["writerCoverage"]) == {"HTTP", "QUARTZ", "MQ", "EXTERNAL", "DIRECT_ACCOUNTS"} and
            all(state == "ENFORCED" for state in fence["writerCoverage"].values()), "SOURCE_WRITERS_NOT_FENCED")
    now = utc(utc_now())
    require(0 <= (now - utc(fence["observedAt"])).total_seconds() <= policy["maximumProofAgeSeconds"] and
            now < utc(fence["expiresAt"]), "SOURCE_FENCE_STALE")
    terminals = original_w04_exits(fence["originalInvocationPins"], guard)
    actions = set()
    for terminal in terminals:
        intent = read_pin(terminal["intentPin"]); child = read_pin(intent["requestPin"])
        require(child["schemaVersion"] == "RecoveryCutoverRequest/v1" and child["phase"] == "SOURCE_FENCE" and
                child["originalRequestPin"] == value["originalRequestPin"] and child["planPin"] == value["planPin"] and
                child["operationId"] == request["operationId"] and child["targetIdentityPin"] == config["targetIdentityPin"] and
                child["sourceScopePin"] == config["sourceScopePin"] and child["leaseRef"] == request["leaseRef"] and
                child["authorizationRefs"] == request["authorizationRefs"] and
                child["action"] in ("STOP_SOURCE_WRITES", "OBSERVE_SOURCE_FENCE") and
                intent["scriptPin"] == data_policy["cutoverAdapters"][child["action"]]["scriptPin"] and
                intent["scriptPin"]["sha256"] in data_trust["cutoverExecutorSha256s"] and
                intent["pythonPin"] == config["pythonPin"],
                "SOURCE_FENCE_PARENT_ORIGINAL_UNBOUND")
        actions.add(child["action"])
    require(actions == {"STOP_SOURCE_WRITES", "OBSERVE_SOURCE_FENCE"}, "SOURCE_FENCE_ORIGINAL_ACTIONS_MISSING")
    for pin in [ref, verifier_ref, *verifier["moduleSourcePins"]]:
        verify_large_pin(pin, guard)
    return ref, value, fence, terminals
