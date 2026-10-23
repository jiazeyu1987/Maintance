"""Explicit image-specific enforcement and actual refusal observations.

No image-independent switch is presumed to provide application write protection.
An independently approved policy must select the real version's mechanism and
its enforce/observe programs. Missing mechanisms fail before application start.
"""
import hashlib
import os
import re
import shlex
from pathlib import Path

from recovery_environment_contract import (EnvironmentFailure, atomic_json, canonical, decode, exact, pin_file, read_pin,
    require, utc, utc_now, verify_large_pin)
from recovery_environment_runtime import ensure_material_path


def validate_recovery_launch(config, mechanism):
    """Require protection before ordinary Spring startup, never after a write."""
    backend = [service for service in config["services"] if service["role"] == "backend"]
    require(len(backend) == 1, "APPLICATION_PROTECTION_BACKEND_REQUIRED")
    backend = backend[0]
    # JVM control belongs to reviewed public configuration, never secret values.
    for secret_pin in config["secretRefs"]:
        secret = read_pin(secret_pin)
        require(not (secret["service"] == "backend" and secret["environment"] in
                    {"JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "JAVA_OPTS"}),
                "APPLICATION_PROTECTION_SECRET_JVM_OPTIONS_REJECTED")
    mounts = mechanism["mounts"]
    application_mount = [mount for mount in mounts if mount["pin"] == mechanism["applicationConfigPin"]]
    require(len(application_mount) == 1 and all(mount in backend["configurationMounts"] for mount in mounts),
            "APPLICATION_PROTECTION_LAUNCH_MOUNTS_UNBOUND")
    application = read_pin(mechanism["applicationConfigPin"])
    expected = {
        "intruoyi.recovery.protection.path": application_mount[0]["target"],
        "intruoyi.recovery.protection.sha256": mechanism["applicationConfigPin"]["sha256"],
        "intruoyi.maintenance.boot.artifactSha256": application["artifactSha256"]}
    options = shlex.split(backend["env"].get("JAVA_TOOL_OPTIONS", ""))
    for key, value in expected.items():
        matching = [option for option in options if option.startswith("-D" + key + "=")]
        require(matching == ["-D" + key + "=" + value], "APPLICATION_PROTECTION_LAUNCH_PROPERTIES_UNBOUND")
    overrides = list(backend["command"])
    for name in ("JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "JAVA_OPTS"):
        overrides.extend(shlex.split(backend["env"].get(name, "")))
    require(not any(option.startswith("-D" + key + "=") for option in overrides for key in expected),
            "APPLICATION_PROTECTION_LAUNCH_PROPERTY_OVERRIDE")


def observe_mechanism_failure(raw, receipt, payload, executor_pin, runner):
    """Validate a selected producer's effect certainty separately from its exit."""
    try:
        failure = decode(raw)
        verify_large_pin(executor_pin, runner.guard)
        keys = ("schemaVersion", "state", "code", "bindings", "originalInvocationPins", "failureEvidencePins")
        exact(failure, keys, "APPLICATION_PROTECTION_FAILURE_INVALID")
        require(receipt["actualExitCode"] == 2 and failure["schemaVersion"] == "RecoveryApplicationProtectionFailure/v1"
                and failure["state"] in ("FAILED_RETAINED", "TERMINAL_UNKNOWN")
                and type(failure["code"]) is str and re.fullmatch("PROTECTION_[A-Z0-9_]+|APPLICATION_[A-Z0-9_]+", failure["code"])
                and failure["bindings"] == {key: payload[key] for key in
                    ("phase", "operationId", "restoreId", "targetIdentityPin", "recoveryPoint", "policyPin", "configurationPin", "imagePins", "containers")},
                "APPLICATION_PROTECTION_FAILURE_UNBOUND")
        for key in ("originalInvocationPins", "failureEvidencePins"):
            require(type(failure[key]) is list, "APPLICATION_PROTECTION_FAILURE_INVALID")
            for ref in failure[key]:
                verify_large_pin(ref, runner.guard)
        for ref in failure["originalInvocationPins"]:
            original = read_pin(ref)
            require(original["schemaVersion"] == "RecoveryEnvironmentInvocation/v1"
                    and original["state"] in ("SUCCEEDED", "FAILED_RETAINED", "TERMINAL_UNKNOWN")
                    and utc(receipt["startedAt"]) <= utc(original["startedAt"]) <= utc(original["finishedAt"]) <= utc(utc_now()),
                    "APPLICATION_PROTECTION_FAILURE_ORIGINAL_UNBOUND")
        if failure["state"] == "FAILED_RETAINED":
            for ref in failure["originalInvocationPins"]:
                original = read_pin(ref)
                require(original["state"] != "TERMINAL_UNKNOWN" and (
                    (original["pid"] is None and original["actualExitCode"] is None)
                    or (type(original["pid"]) is int and original["pid"] > 0
                        and type(original["actualExitCode"]) is int and original["localProcessTerminated"] is True)),
                    "APPLICATION_PROTECTION_FAILURE_UNKNOWN_ORIGINAL")
    except (EnvironmentFailure, ValueError, KeyError, TypeError, OSError):
        # Unreadable effect evidence never proves that a mutating producer stopped.
        raise EnvironmentFailure("APPLICATION_PROTECTION_FAILURE_EVIDENCE_UNPROVEN", unknown=True) from None
    try:
        path = runner.root / ("application-protection-failure-" + payload["phase"].lower() + ".json")
        require(not path.exists(), "APPLICATION_PROTECTION_FAILURE_ALREADY_RECORDED")
        atomic_json(path, {**failure, "executorPin": executor_pin, "originalStdoutSha256": hashlib.sha256(raw).hexdigest(),
                           "localProcessPid": receipt["pid"], "localProcessExitCode": receipt["actualExitCode"]})
        proof = pin_file(path)
    except (OSError, EnvironmentFailure):
        raise EnvironmentFailure("APPLICATION_PROTECTION_FAILURE_EVIDENCE_NOT_PERSISTED", unknown=True) from None
    runner.pins.append(proof)
    return {"code": failure["code"], "unknown": failure["state"] == "TERMINAL_UNKNOWN", "evidencePin": proof}


def validate_write_protection(config, policy, guard):
    require(type(policy.get("applicationWriteProtectionPin")) is dict,
            "APPLICATION_WRITE_PROTECTION_POLICY_REQUIRED")
    record = read_pin(policy["applicationWriteProtectionPin"])
    exact(record, ("schemaVersion", "targetIdentityPin", "configurationPin", "imagePins", "mechanismId",
                  "sourceEvidencePins", "enforceScriptPin", "observeScriptPin", "requiredScopes"),
          "APPLICATION_WRITE_PROTECTION_POLICY_INVALID")
    require(record["schemaVersion"] == "RecoveryApplicationWriteProtectionPolicy/v1" and
            record["targetIdentityPin"] == config["targetIdentityPin"] and
            record["configurationPin"] == config["configurationPin"] and record["imagePins"] == config["imagePins"],
            "APPLICATION_WRITE_PROTECTION_VERSION_MISMATCH")
    require(type(record["mechanismId"]) is str and record["mechanismId"] and record["sourceEvidencePins"] and
            set(record["requiredScopes"]) == {"BUSINESS_DATABASE", "BUSINESS_OBJECTS", "BUSINESS_DERIVED", "APPLICATION_MUTATIONS", "SCHEDULERS", "EXTERNAL_DISPATCH"},
            "APPLICATION_WRITE_PROTECTION_COVERAGE_INCOMPLETE")
    for pin in record["sourceEvidencePins"]:
        verify_large_pin(pin, guard)
    for key in ("enforceScriptPin", "observeScriptPin"):
        ensure_material_path(record[key]["path"], config)
        verify_large_pin(record[key], guard)
        require(Path(record[key]["path"]).suffix == ".py", "APPLICATION_PROTECTION_EXECUTOR_INVALID")
    return record


def protect_application(request, config, policy, runtime, restore, phase):
    spec = validate_write_protection(config, policy, runtime.runner.guard)
    containers = dict(runtime.identities)
    payload = {"schemaVersion": "RecoveryApplicationWriteProtectionRequest/v1", "phase": phase,
               "operationId": request["operationId"], "restoreId": restore["restoreId"],
               "targetIdentityPin": config["targetIdentityPin"], "recoveryPoint": restore["recoveryPoint"],
               "policyPin": policy["applicationWriteProtectionPin"], "configurationPin": config["configurationPin"],
               "imagePins": config["imagePins"], "containers": containers,
               "deadlineMilliseconds": max(1, int(runtime.runner.remaining() * 1000))}
    selected = "enforceScriptPin" if phase == "BEFORE_START" else "observeScriptPin"
    effect = runtime.runner.sequence + 1
    argv = [config["pythonPin"]["path"], "-I", spec[selected]["path"]]
    runtime.runner.guard()
    # Observation includes attempted writes; an uncertain probe cannot be
    # treated as a read-only effect even when its intended outcome is refusal.
    if spec["mechanismId"] == "INT_RUOYI_RECOVERY_PROTECTION_V3":
        provisioned = os.environ.get("RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN")
        require(provisioned, "APPLICATION_MECHANISM_CONFIG_NOT_PROVISIONED")
        mechanism_pin = decode(provisioned.encode("utf-8"))
        ensure_material_path(mechanism_pin["path"], config)
        mechanism = read_pin(mechanism_pin)
        require(mechanism["schemaVersion"] == "RecoveryApplicationMechanismConfig/v1" and
                all(mechanism[key] == payload[key] for key in ("operationId", "restoreId", "targetIdentityPin", "recoveryPoint",
                    "policyPin", "configurationPin", "imagePins")), "APPLICATION_MECHANISM_CONFIG_UNBOUND")
        validate_recovery_launch(config, mechanism)
        raw = runtime.runner.run(argv, stdin=canonical(payload), mutation=True,
                                 environment_bindings={"RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN": provisioned},
                                 failure_observer=lambda output, receipt: observe_mechanism_failure(
                                     output, receipt, payload, spec[selected], runtime.runner))
    else:
        raw = runtime.runner.run(argv, stdin=canonical(payload), mutation=True)
    receipt = read_pin(runtime.runner.pins[-1])
    observation = decode(raw)
    exact(observation, ("schemaVersion", "phase", "operationId", "restoreId", "targetIdentityPin", "recoveryPoint",
                        "policyPin", "containers", "state", "observedAt", "scopeObservations"),
          "APPLICATION_WRITE_PROTECTION_OBSERVATION_INVALID")
    require(observation["schemaVersion"] == "RecoveryApplicationWriteProtectionObservation/v1" and
            all(observation[key] == payload[key] for key in ("phase", "operationId", "restoreId", "targetIdentityPin",
                "recoveryPoint", "policyPin", "containers")) and observation["state"] == "ENFORCED",
            "APPLICATION_WRITE_PROTECTION_NOT_ENFORCED")
    now = utc(utc_now())
    require(utc(receipt["startedAt"]) <= utc(observation["observedAt"]) <=
            utc(receipt["finishedAt"]) <= now, "APPLICATION_PROTECTION_OBSERVATION_STALE")
    scopes = observation["scopeObservations"]
    require(type(scopes) is list and len(scopes) == len(spec["requiredScopes"]) and
            {item["scope"] for item in scopes} == set(spec["requiredScopes"]), "APPLICATION_PROTECTION_OBSERVATIONS_INCOMPLETE")
    for item in scopes:
        exact(item, ("scope", "enforcementPin", "beforeFingerprint", "afterFingerprint", "rejectionObservationPins"),
              "APPLICATION_PROTECTION_SCOPE_INVALID")
        require(item["beforeFingerprint"] == item["afterFingerprint"] and
                type(item["beforeFingerprint"]) is str and re.fullmatch("[0-9a-f]{64}", item["beforeFingerprint"]),
                "APPLICATION_PROTECTION_PROBE_CHANGED_DATA")
        verify_large_pin(item["enforcementPin"], runtime.runner.guard)
        require(item["rejectionObservationPins"], "APPLICATION_WRITE_REFUSAL_NOT_OBSERVED")
        for pin in item["rejectionObservationPins"]:
            proof = read_pin(pin)
            require(proof["schemaVersion"] == "RecoveryApplicationWriteRefusal/v1" and
                    proof["scope"] == item["scope"] and proof["phase"] == phase and proof["denied"] is True and
                    proof["operationId"] == request["operationId"] and proof["targetIdentityPin"] == config["targetIdentityPin"] and
                    proof["recoveryPoint"] == restore["recoveryPoint"] and proof["containers"] == containers and
                    proof["beforeFingerprint"] == item["beforeFingerprint"] == proof["afterFingerprint"] and
                    proof["originalInvocationPins"], "APPLICATION_WRITE_REFUSAL_UNBOUND")
            for original_pin in proof["originalInvocationPins"]:
                verify_large_pin(original_pin, runtime.runner.guard)
                invocation = read_pin(original_pin)
                require(invocation["schemaVersion"] == "RecoveryEnvironmentInvocation/v1" and
                        invocation["mutation"] is True and type(invocation["actualExitCode"]) is int and
                        invocation["state"] in ("SUCCEEDED", "FAILED_RETAINED") and
                        utc(receipt["startedAt"]) <= utc(invocation["startedAt"]) <=
                        utc(invocation["finishedAt"]) <= utc(receipt["finishedAt"]),
                        "APPLICATION_WRITE_REFUSAL_TERMINATION_UNPROVEN")
    require(receipt["actualExitCode"] == 0 and receipt["state"] == "SUCCEEDED" and
            receipt["stdoutSha256"] == hashlib.sha256(raw).hexdigest(), "APPLICATION_PROTECTION_ORIGINAL_EXIT_MISSING")
    # Recheck the exact script and target container membership after observing.
    verify_large_pin(spec[selected], runtime.runner.guard)
    require(containers == runtime.identities, "APPLICATION_PROTECTION_CONTAINER_CHANGED")
    path = runtime.runner.root / ("application-write-protection-" + phase.lower() + ".json")
    runtime.runner.guard()
    atomic_json(path, {**observation, "originalInvocationPin": runtime.runner.pins[-1], "executorPin": spec[selected]})
    proof = pin_file(path)
    runtime.runner.guard()
    runtime.runner.confirm_effects([effect])
    return proof
