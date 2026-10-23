"""Start only the application matching a successful pinned W04 data restore."""
from __future__ import annotations

from datetime import datetime, timezone

from recovery_environment_contract import (atomic_json, digest, exact, original_w04_exits, pin_file, read_pin, require, utc, utc_now, verify_large_pin)
from recovery_environment import check_controlled_preconditions, validate_plan, wait_health
from recovery_environment_runtime import sanitize_inspect
from recovery_application_restore import restore_steps, verify_dependency
from recovery_application_protection import protect_application


def match_restore(request, config, policy, trust, guard=lambda: None):
    restore_pin = request["inputPins"]["restoreExecutionResult"]
    target_pin = request["inputPins"]["recoveryTarget"]
    restore = read_pin(restore_pin)
    target = read_pin(target_pin)
    trust.schemas.validate(restore, "RestoreExecutionResult")
    trust.schemas.validate(target, "RecoveryTarget")
    require(restore["state"] == "SUCCEEDED" and restore["writeProtectionState"] == "ENFORCED", "RESTORE_NOT_SUCCEEDED_OR_NOT_PROTECTED")
    require(restore["operationId"] == request["operationId"] and target["targetId"] == config["targetId"] and
            restore["targetIdentityPin"] == target["targetIdentityPin"] == config["targetIdentityPin"] and
            target["leaseRef"] == request["leaseRef"] and target["configurationPin"] == config["configurationPin"] and
            target["secretRefs"] == config["secretRefs"], "RESTORE_TARGET_CONFIG_MISMATCH")
    plan_pin = restore["planPin"]
    plan = validate_plan(read_pin(plan_pin), plan_pin, request, config, trust, guard)
    require(target["versionPins"] == plan["supportedVersionPins"], "RESTORE_VERSION_PINS_MISMATCH")
    require(restore["restoreId"] == plan["restoreId"] and restore["recoveryPoint"] == plan["recoveryPoint"], "RESTORE_POINT_OR_ID_MISMATCH")
    require(restore["dbStepEvidencePins"] and restore["objectStepEvidencePins"] and restore["originalInvocationPins"],
            "RESTORE_EXECUTION_ORIGINALS_MISSING")
    proof = read_pin(target["resourcesProofPin"])
    require(proof["schemaVersion"] == "RecoveryEnvironmentProof/v1" and proof["planPin"] == plan_pin and
            proof["operationId"] == request["operationId"] and proof["configurationRef"] == request["sourceOrTargetRef"] and
            proof["targetIdentityPin"] == config["targetIdentityPin"] and proof["leaseRef"] == request["leaseRef"] and
            proof["recoveryPoint"] == restore["recoveryPoint"], "PREPARED_ENVIRONMENT_RESTORE_MISMATCH")
    now = datetime.now(timezone.utc)
    require(0 <= (now - utc(proof["observedAt"])).total_seconds() <= policy["maximumProofAgeSeconds"], "PREPARED_ENVIRONMENT_STALE")
    for key in ("isolationProofPin", "sideEffectIsolationPin", "modePreconditionsPin"):
        record = read_pin(target[key])
        require(record["operationId"] == request["operationId"], "PREPARED_PROOF_OPERATION_MISMATCH")
    side_effect = read_pin(target["sideEffectIsolationPin"])
    require(side_effect["state"] == "ENFORCED" and side_effect["targetIdentityPin"] == config["targetIdentityPin"] and
            side_effect["policyPin"] == request["policyPin"] and side_effect["startupInventoryPins"] == policy["startupInventoryPins"],
            "PREPARED_SIDE_EFFECT_POLICY_MISMATCH")
    restore_steps(request, config, policy, restore, target_pin, plan, guard)
    return restore, restore_pin, target, proof, plan


def start_application(request, config, policy, trust, runtime, private_dir):
    restore, restore_pin, target, proof, plan = match_restore(request, config, policy, trust, runtime.runner.guard)
    runtime.native_preflight()
    check_controlled_preconditions(request, config, trust, runtime)
    runtime.check_firewall()
    physical_step = restore_steps(request, config, policy, restore, request["inputPins"]["recoveryTarget"], plan, runtime.runner.guard)
    service_by_role = {service["role"]: service for service in config["services"]}
    prepared = proof["services"]
    require({item["labels"]["intruoyi.recovery.target"] for item in prepared} == {config["targetId"]}, "PREPARED_CONTAINER_TARGET_MISMATCH")
    restart_observations = []
    for record in prepared:
        role = next((role for role, service in service_by_role.items() if record["name"] == "/" + service["name"]), None)
        require(role in ("mysql", "minio", "redis") and role not in runtime.identities, "PREPARED_DEPENDENCY_IDENTITY_INVALID")
        item = runtime.inspect(record["id"])
        runtime.check_service(service_by_role[role], item, running=True)
        current = sanitize_inspect(item)
        restart = verify_dependency(record, current, role, physical_step, config, policy, runtime.runner.guard)
        if restart is not None:
            restart_observations.append(restart)
        runtime.identities[role] = record["id"]
    require(set(runtime.identities) == {"mysql", "minio", "redis"}, "PREPARED_DEPENDENCIES_INCOMPLETE")
    network_id = proof["network"]["networkId"]
    runtime.check_network(network_id, list(runtime.identities.values()))
    tables = runtime.mysql_tables()
    require(tables["tableCount"] > 0, "RESTORED_DATABASE_HAS_NO_TABLES")
    objects = runtime.minio_buckets()
    require(set(objects["result"]["buckets"]) == set(config["buckets"]), "RESTORED_OBJECT_BUCKETS_MISMATCH")
    blocked = runtime.isolation_probes()
    protection_before = protect_application(request, config, policy, runtime, restore, "BEFORE_START")
    created, started, healthy = [], [], {}
    application_roles = set(service_by_role) - {"mysql", "minio", "redis"}
    # Dependency order is explicit: document/showroom dependencies, backend,
    # then frontend. Unknown service roles were rejected by configuration.
    ordered_roles = [role for role in ("onlyoffice", "showroom", "backend", "frontend") if role in application_roles]
    require(set(ordered_roles) == application_roles, "APPLICATION_START_ORDER_UNDEFINED")
    for role in ordered_roles:
        service = service_by_role[role]
        runtime.runner.guard()
        check_controlled_preconditions(request, config, trust, runtime)
        record = runtime.create_service(service, private_dir)
        created.append(record)
        started.append(runtime.start_service(service, record["id"]))
        healthy[role] = wait_health(runtime, service)
    network = runtime.check_network(network_id, list(runtime.identities.values()))
    firewall = runtime.check_firewall()
    blocked_after = runtime.isolation_probes()
    for role in application_roles:
        runtime.check_service(service_by_role[role], runtime.inspect(runtime.identities[role]), running=True)
    protection_after = protect_application(request, config, policy, runtime, restore, "AFTER_START")
    root = runtime.runner.root
    runtime.runner.guard()
    atomic_json(root / "application-launch.json", {"schemaVersion": "RecoveryApplicationLaunch/v1", "operationId": request["operationId"],
        "restoreId": restore["restoreId"], "restoreResultPin": restore_pin, "targetIdentityPin": config["targetIdentityPin"],
        "created": created, "started": started, "imagePins": config["imagePins"], "configurationPin": config["configurationPin"],
        "network": network, "dependencyRestartObservations": restart_observations, "observedAt": utc_now()})
    runtime.runner.guard()
    atomic_json(root / "application-side-effects.json", {"schemaVersion": "RecoverySideEffectIsolation/v1",
        "operationId": request["operationId"], "targetIdentityPin": config["targetIdentityPin"], "state": "ENFORCED",
        "policyPin": request["policyPin"], "startupInventoryPins": policy["startupInventoryPins"],
        "firewall": firewall, "blockedBefore": blocked, "blockedAfter": blocked_after, "observedAt": utc_now(),
        "sourceWritesPerformed": False, "writeProtectionState": "ENFORCED",
        "applicationWriteProtectionPolicyPin": policy["applicationWriteProtectionPin"],
        "writeProtectionBeforePin": protection_before, "writeProtectionAfterPin": protection_after})
    runtime.runner.guard()
    atomic_json(root / "application-health.json", {"schemaVersion": "RecoveryApplicationHealth/v1", "operationId": request["operationId"],
        "restoreId": restore["restoreId"], "targetIdentityPin": config["targetIdentityPin"], "state": "SUCCEEDED", "services": healthy,
        "database": tables, "objectStore": objects, "observedAt": utc_now(), "businessAcceptance": "NOT_PERFORMED"})
    runtime.runner.guard()
    result = {"schemaVersion": "ApplicationStartResult/v1", "operationId": request["operationId"], "restoreId": restore["restoreId"],
              "targetIdentityPin": config["targetIdentityPin"], "restoreResultPin": restore_pin, "imagePins": config["imagePins"],
              "configurationPin": config["configurationPin"], "sideEffectIsolationPin": pin_file(root / "application-side-effects.json"),
              "originalStartResultPins": [*runtime.runner.pins, pin_file(root / "application-launch.json")],
              "healthEvidencePin": pin_file(root / "application-health.json"), "state": "SUCCEEDED"}
    trust.schemas.validate(result, "ApplicationStartResult")
    runtime.runner.guard()
    atomic_json(root / "application-start-result.json", result)
    artifact = pin_file(root / "application-start-result.json")
    runtime.runner.guard()
    return result, artifact
