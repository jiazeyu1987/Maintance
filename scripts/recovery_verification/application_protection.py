"""Check W05's real version-specific write refusal chain before and after start."""
from core import canonical, digest, fields, need, pin_key, pins, same, sha, timestamp


SCOPES = {"BUSINESS_DATABASE", "BUSINESS_OBJECTS", "BUSINESS_DERIVED",
          "APPLICATION_MUTATIONS", "SCHEDULERS", "EXTERNAL_DISPATCH"}


def verify_application_protection(context, application, side, resources):
    environment_policy = context.record(context.plan["sideEffectPolicyPin"])
    spec_pin = side["applicationWriteProtectionPolicyPin"]
    same(spec_pin, environment_policy["applicationWriteProtectionPin"], "APPLICATION_PROTECTION_POLICY_MISMATCH")
    spec = context.record(spec_pin)
    fields(spec, "schemaVersion targetIdentityPin configurationPin imagePins mechanismId sourceEvidencePins "
           "enforceScriptPin observeScriptPin requiredScopes", "RecoveryApplicationWriteProtectionPolicy/v1")
    same(spec["targetIdentityPin"], context.target_pin, "APPLICATION_PROTECTION_TARGET_MISMATCH")
    same(spec["configurationPin"], application["configurationPin"], "APPLICATION_PROTECTION_VERSION_MISMATCH")
    need(spec["imagePins"] == application["imagePins"] and bool(spec["mechanismId"]) and
         len(spec["requiredScopes"]) == len(SCOPES) and set(spec["requiredScopes"]) == SCOPES and
         bool(spec["sourceEvidencePins"]), "APPLICATION_PROTECTION_POLICY_INCOMPLETE")
    for ref in spec["sourceEvidencePins"]:
        context.read(ref)
    config = context.record(context.request["sourceOrTargetRef"])
    original_keys = set(pins(application["originalStartResultPins"]))
    launch = context.application_launch
    prepared_ids = {item["id"] for item in resources["services"]}
    started_ids = {item["id"] for item in launch["started"]}
    prior = None
    for phase, field, executor_field in (("BEFORE_START", "writeProtectionBeforePin", "enforceScriptPin"),
                                        ("AFTER_START", "writeProtectionAfterPin", "observeScriptPin")):
        proof = context.record(side[field])
        fields(proof, "schemaVersion phase operationId restoreId targetIdentityPin recoveryPoint policyPin containers "
               "state observedAt scopeObservations originalInvocationPin executorPin", "RecoveryApplicationWriteProtectionObservation/v1")
        context.bind(proof)
        same(proof["policyPin"], spec_pin, "APPLICATION_PROTECTION_POLICY_MISMATCH")
        same(proof["executorPin"], spec[executor_field], "APPLICATION_PROTECTION_EXECUTOR_MISMATCH")
        need(pin_key(proof["executorPin"]) in context.source_keys, "APPLICATION_PROTECTION_EXECUTOR_UNPINNED")
        context.read(proof["executorPin"])
        need(proof["phase"] == phase and proof["state"] == "ENFORCED" and
             proof["recoveryPoint"] == context.plan["recoveryPoint"], "APPLICATION_PROTECTION_OBSERVATION_UNBOUND")
        need(type(proof["containers"]) is dict and set(proof["containers"].values()) ==
             (prepared_ids if phase == "BEFORE_START" else prepared_ids | started_ids), "APPLICATION_PROTECTION_CONTAINERS_UNBOUND")
        if prior is not None:
            need(all(proof["containers"].get(role) == identity for role, identity in prior["containers"].items()) and
                 timestamp(prior["observedAt"]) <= timestamp(proof["observedAt"]), "APPLICATION_PROTECTION_DEPENDENCY_CHANGED")
        prior = proof
        need(pin_key(proof["originalInvocationPin"]) in original_keys, "APPLICATION_PROTECTION_ORIGINAL_EXIT_REQUIRED")
        original = context.record(proof["originalInvocationPin"])
        need(original["schemaVersion"] == "RecoveryEnvironmentInvocation/v1" and original["state"] == "SUCCEEDED" and
             type(original["actualExitCode"]) is int and original["actualExitCode"] == 0 and
             type(original["pid"]) is int and original["pid"] > 0 and original["mutation"] is True and
             original["argvSha256"] == digest(canonical([config["pythonPin"]["path"], "-I", spec[executor_field]["path"]])) and
             type(original["stdoutBytes"]) is int and original["stdoutBytes"] > 0 and
             timestamp(original["startedAt"]) <= timestamp(proof["observedAt"]) <= timestamp(original["finishedAt"]),
             "APPLICATION_PROTECTION_ORIGINAL_EXIT_REQUIRED")
        sha(original["stdoutSha256"])
        # Both phases can attempt writes; W05 marks both as mutations.
        scopes = proof["scopeObservations"]
        need(type(scopes) is list and len(scopes) == len(SCOPES) and {item["scope"] for item in scopes} == SCOPES,
             "APPLICATION_PROTECTION_COVERAGE_INCOMPLETE")
        for item in scopes:
            fields(item, "scope enforcementPin beforeFingerprint afterFingerprint rejectionObservationPins")
            sha(item["beforeFingerprint"])
            need(item["beforeFingerprint"] == item["afterFingerprint"] and bool(item["rejectionObservationPins"]),
                 "APPLICATION_PROTECTION_REFUSAL_REQUIRED")
            context.read(item["enforcementPin"])
            for ref in item["rejectionObservationPins"]:
                refusal = context.record(ref)
                need(refusal["schemaVersion"] == "RecoveryApplicationWriteRefusal/v1" and
                     refusal["scope"] == item["scope"] and refusal["phase"] == phase and refusal["denied"] is True and
                     refusal["operationId"] == context.request["operationId"] and refusal["recoveryPoint"] == context.plan["recoveryPoint"] and
                     refusal["containers"] == proof["containers"] and
                     refusal["beforeFingerprint"] == item["beforeFingerprint"] == refusal["afterFingerprint"] and
                     bool(refusal["originalInvocationPins"]), "APPLICATION_PROTECTION_REFUSAL_UNBOUND")
                same(refusal["targetIdentityPin"], context.target_pin, "APPLICATION_PROTECTION_TARGET_MISMATCH")
                for invocation_pin in refusal["originalInvocationPins"]:
                    invocation = context.record(invocation_pin)
                    need(invocation["schemaVersion"] == "RecoveryEnvironmentInvocation/v1" and invocation["mutation"] is True and
                         invocation["state"] in ("SUCCEEDED", "FAILED_RETAINED") and type(invocation["actualExitCode"]) is int and
                         type(invocation["pid"]) is int and invocation["pid"] > 0 and
                         timestamp(original["startedAt"]) <= timestamp(invocation["startedAt"]) <=
                         timestamp(invocation["finishedAt"]) <= timestamp(original["finishedAt"]),
                         "APPLICATION_PROTECTION_REFUSAL_TERMINATION_UNPROVEN", "UNKNOWN")
