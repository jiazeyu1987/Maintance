"""Consume W04's native restore records without inventing invocation wrappers."""
from pathlib import Path

from recovery_environment_contract import (digest, exact, original_w04_exits, pin_file, read_pin, require,
    utc, verify_large_pin)


def restore_steps(request, config, policy, restore, target_pin, plan, guard):
    originals = restore["originalInvocationPins"]
    terminals = original_w04_exits(originals, guard)
    invocations = []
    for terminal in terminals:
        intent = read_pin(terminal["intentPin"])
        if intent["scriptPin"] != policy["restoreWorkerPin"]:
            continue  # PREPARE_TARGET has its own OperationResult in this list.
        require(intent["style"] == "operation", "RESTORE_WORKER_STYLE_INVALID")
        child = read_pin(intent["requestPin"])
        extras = {"DATABASE_FULL": set(), "DATABASE_INCREMENTAL": {"previousDatabaseResultPin"},
                  "OBJECT_FULL": {"previousObjectResultPin", "parentRecoveryPoint"},
                  "OBJECT_INCREMENTAL": {"previousObjectResultPin", "parentRecoveryPoint"},
                  "OBJECT_CHAIN_PHYSICAL": {"allMaterialPins"},
                  "DERIVED_DATA": {"databaseResultPin", "objectResultPin"},
                  "CONSISTENCY": {"databaseResultPin", "objectResultPin"}}
        base = {"schemaVersion", "operationId", "requestId", "action", "originalRequestPin", "planPin",
                "recoveryTargetPin", "materialPin", "deadlineMilliseconds"}
        require(child.get("action") in extras and set(child) == base | extras[child["action"]],
                "RESTORE_WORKER_REQUEST_INVALID")
        require(child["schemaVersion"] == "RecoveryDataRequest/v1" and
                child["operationId"] == request["operationId"] and child["planPin"] == restore["planPin"] and
                child["recoveryTargetPin"] == target_pin, "RESTORE_WORKER_SCOPE_MISMATCH")
        original = read_pin(child["originalRequestPin"])
        require(original["schemaVersion"] == "backup-restore-operation/v1" and
                original["operationId"] == request["operationId"] and original["mode"] == request["mode"] and
                original["action"] in ("REHEARSAL", "RESTORE_EXECUTE", "CONTROLLED_CUTOVER") and
                original["selectedPointPin"] == request["selectedPointPin"] and
                original["sourceOrTargetRef"] == request["sourceOrTargetRef"] and
                original["policyPin"] == request["policyPin"] and
                original["leaseRef"] == request["leaseRef"] and
                original["authorizationRefs"] == request["authorizationRefs"], "RESTORE_ORIGINAL_REQUEST_MISMATCH")
        require(intent["pythonPin"] == config["pythonPin"] and intent["pythonPin"] in plan["toolPins"],
                "RESTORE_WORKER_INTERPRETER_MISMATCH")
        verify_large_pin(intent["pythonPin"], guard)
        result_pin = pin_file(Path(terminal["intentPin"]["path"]).with_name("result.json"))
        require(result_pin in originals, "RESTORE_WORKER_RESULT_ORIGINAL_MISSING")
        result = read_pin(result_pin)
        require(result["schemaVersion"] == "RecoveryDataStepResult/v1" and
                result["operationId"] == child["operationId"] and result["requestId"] == child["requestId"] and
                result["action"] == child["action"] and result["state"] == "SUCCEEDED" and
                result["failureCode"] is None,
                "RESTORE_WORKER_RESULT_MISMATCH")
        material = read_pin(child["materialPin"])
        require(material["sourceScopePin"] == config["sourceScopePin"] and
                result["data"]["recoveryPoint"] == material["recoveryPoint"] and
                material["recoveryPoint"] in {read_pin(pin)["commonRecoveryPoint"] for pin in plan["orderedChainPins"]},
                "RESTORE_MATERIAL_SOURCE_OR_POINT_MISMATCH")
        native = []
        for proof_pin in result["originalResultPins"]:
            verify_large_pin(proof_pin, guard)
            proof = read_pin(proof_pin)
            if proof.get("schemaVersion") == "RecoverySqlImporter/v1":
                require(proof["state"] == "SUCCEEDED" and type(proof["actualExitCode"]) is int and
                        proof["actualExitCode"] == 0, "RESTORE_NATIVE_EXECUTION_NOT_SUCCEEDED")
            if proof.get("schemaVersion") == "RecoveryDataInvocation/v1":
                require(proof["operationId"] == request["operationId"] and proof["action"] == child["action"] and
                        proof["state"] == "SUCCEEDED" and type(proof["actualExitCode"]) is int and
                        proof["actualExitCode"] == 0, "RESTORE_NATIVE_EXECUTION_NOT_SUCCEEDED")
                native.append(proof)
        require(native, "RESTORE_NATIVE_EXECUTION_MISSING")
        invocations.append({"pin": result_pin, "request": child, "result": result, "native": native,
                            "intent": intent, "terminal": terminal, "material": material,
                            "original": original})
    by_pin = {item["pin"]["sha256"]: item for item in invocations}
    require(len(by_pin) == len(invocations), "RESTORE_STEP_DUPLICATE")

    def admit(pin, action):
        item = by_pin.get(pin["sha256"])
        require(item is not None and item["pin"] == pin and item["request"]["action"] == action,
                "RESTORE_STEP_NOT_BOUND_TO_ACTUAL_WORKER")
        return item

    require(len(restore["dbStepEvidencePins"]) == len(plan["orderedChainPins"]), "RESTORE_DATABASE_CHAIN_INCOMPLETE")
    databases = []
    for index, pin in enumerate(restore["dbStepEvidencePins"]):
        step = admit(pin, "DATABASE_FULL" if index == 0 else "DATABASE_INCREMENTAL")
        point = read_pin(plan["orderedChainPins"][index])
        require(step["material"]["recoveryPoint"] == point["commonRecoveryPoint"], "RESTORE_DATABASE_CHAIN_POINT_MISMATCH")
        if index:
            require(read_pin(step["request"]["previousDatabaseResultPin"]) == databases[-1]["result"]["data"],
                    "RESTORE_DATABASE_PREVIOUS_STEP_MISMATCH")
        databases.append(step)
    object_pins = restore["objectStepEvidencePins"]
    physical = len(object_pins) == 1 and by_pin.get(object_pins[0]["sha256"], {}).get("request", {}).get("action") == "OBJECT_CHAIN_PHYSICAL"
    objects = []
    if physical:
        step = admit(object_pins[0], "OBJECT_CHAIN_PHYSICAL")
        require(len(step["request"]["allMaterialPins"]) == len(plan["orderedChainPins"]), "RESTORE_PHYSICAL_CHAIN_INCOMPLETE")
        for pin, point_pin in zip(step["request"]["allMaterialPins"], plan["orderedChainPins"]):
            material, point = read_pin(pin), read_pin(point_pin)
            require(material["sourceScopePin"] == config["sourceScopePin"] and
                    material["recoveryPoint"] == point["commonRecoveryPoint"] and
                    material["objects"]["method"] == "PHYSICAL_FILES", "RESTORE_PHYSICAL_CHAIN_MISMATCH")
        require(step["result"]["data"]["originalVersionIdsPreserved"] is True and
                len(step["result"]["data"]["physicalStepEvidencePins"]) == len(plan["orderedChainPins"]),
                "RESTORE_PHYSICAL_READBACK_INCOMPLETE")
        for pin in step["result"]["data"]["physicalStepEvidencePins"] + [step["result"]["data"]["comparisonPin"]]:
            verify_large_pin(pin, guard)
        objects.append(step)
    else:
        require(len(object_pins) == len(plan["orderedChainPins"]), "RESTORE_OBJECT_CHAIN_INCOMPLETE")
        for index, pin in enumerate(object_pins):
            step = admit(pin, "OBJECT_FULL" if index == 0 else "OBJECT_INCREMENTAL")
            require(step["material"]["recoveryPoint"] == read_pin(plan["orderedChainPins"][index])["commonRecoveryPoint"],
                    "RESTORE_OBJECT_CHAIN_POINT_MISMATCH")
            if index:
                require(read_pin(step["request"]["previousObjectResultPin"]) == objects[-1]["result"]["data"],
                        "RESTORE_OBJECT_PREVIOUS_STEP_MISMATCH")
            objects.append(step)
    consistent = read_pin(restore["consistencyEvidencePin"])
    consistency = admit(consistent["originalConsistencyResultPin"], "CONSISTENCY")
    derived = admit(consistent["derivedEvidencePin"], "DERIVED_DATA")
    for item in (consistency, derived):
        require(read_pin(item["request"]["databaseResultPin"]) == databases[-1]["result"]["data"] and
                read_pin(item["request"]["objectResultPin"]) == objects[-1]["result"]["data"],
                "RESTORE_FINAL_STEP_INPUTS_MISMATCH")
    data = consistency["result"]["data"]
    require(data["schemaVersion"] == "RecoveryConsistencyEvidence/v1" and
            data["targetIdentityPin"] == config["targetIdentityPin"] and data["allReferencesVerified"] is True and
            data["invariantsVerified"] is True and data["applicationVerified"] is False and
            consistent == {**data, "derivedEvidencePin": derived["pin"], "originalConsistencyResultPin": consistency["pin"]},
            "RESTORE_CONSISTENCY_NOT_VERIFIED")
    require(derived["result"]["data"]["schemaVersion"] == "RecoveryDerivedEvidence/v1" and
            derived["result"]["data"]["targetIdentityPin"] == config["targetIdentityPin"], "RESTORE_DERIVED_TARGET_MISMATCH")
    require(len(invocations) == len(databases) + len(objects) + 2, "RESTORE_UNEXPECTED_DATA_STEP")
    return objects[0] if physical else None


def restart_policy(config, policy, guard):
    require(type(policy.get("physicalRestartPolicyPin")) is dict, "PHYSICAL_RESTART_POLICY_REQUIRED")
    record = read_pin(policy["physicalRestartPolicyPin"])
    exact(record, ("schemaVersion", "targetIdentityPin", "approvalPin", "minioDataMount", "storageStopSeconds"),
          "PHYSICAL_RESTART_POLICY_INVALID")
    require(record["schemaVersion"] == "RecoveryPhysicalRestartPolicy/v1" and
            record["targetIdentityPin"] == config["targetIdentityPin"] and
            type(record["storageStopSeconds"]) is int and 1 <= record["storageStopSeconds"] <= 300 and
            type(record["minioDataMount"]) is str and record["minioDataMount"].startswith("/") and
            ".." not in Path(record["minioDataMount"]).parts, "PHYSICAL_RESTART_POLICY_SCOPE_MISMATCH")
    verify_large_pin(record["approvalPin"], guard)
    return record


def verify_dependency(prepared, current, role, physical_step, config, policy, guard):
    stable = ("id", "name", "imageId", "labels", "envSha256", "hostConfigSha256", "mounts", "commandSha256", "restartCount")
    require(all(current[key] == prepared[key] for key in stable), "PREPARED_DEPENDENCY_CHANGED")
    if current["state"]["StartedAt"] == prepared["state"]["StartedAt"]:
        return None
    require(role == "minio" and physical_step is not None, "PREPARED_DEPENDENCY_RESTART_UNPROVEN")
    root = Path(physical_step["pin"]["path"]).parent
    stop_pin = pin_file(root / "physical-stop-intent.json")
    stop = read_pin(stop_pin)
    require(stop["containerId"] == prepared["id"] and stop["preserveExisting"] is True,
            "PHYSICAL_RESTART_CONTAINER_MISMATCH")
    # W04's operation policyPin selects W05's environment policy. Its internal
    # data policy is separate, so never interpret that wire Pin as a data policy.
    data_policy = restart_policy(config, policy, guard)
    require(stop["approvalPin"] == data_policy["approvalPin"], "PHYSICAL_RESTART_APPROVAL_MISMATCH")
    approval = read_pin(stop["approvalPin"])
    require(approval["schemaVersion"] == "RecoveryPhysicalStartupApproval/v1" and approval["approved"] is True and
            approval["targetIdentityPin"] == config["targetIdentityPin"] and
            approval["recoveryPoint"] == physical_step["result"]["data"]["recoveryPoint"] and
            approval["imageId"] == prepared["imageId"], "PHYSICAL_RESTART_APPROVAL_SCOPE_MISMATCH")
    require(all(approval[key] is True for key in ("notificationAbsent", "lifecycleAbsent", "replicationAbsent",
                "externalTierAbsent", "pendingJobsAbsent", "credentialsCompatible")), "PHYSICAL_RESTART_PROTECTION_UNPROVEN")
    mounts = [entry for entry in prepared["mounts"] if entry["Destination"] == data_policy["minioDataMount"]]
    volume = stop["volumeIdentity"]
    require(len(mounts) == 1 and mounts[0]["Type"] == "volume" and
            volume["Name"] == mounts[0]["Name"] and volume["Mountpoint"] == mounts[0]["Source"] and
            volume["Labels"] == prepared["labels"] and volume["Driver"] == "local" and not volume["Options"],
            "PHYSICAL_RESTART_VOLUME_MISMATCH")
    stop_argv = [config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock", "stop", "--time",
                 str(data_policy["storageStopSeconds"]), prepared["id"]]
    start_argv = [config["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock", "start", prepared["id"]]
    stops = [item for item in physical_step["native"] if item["mutation"] is True and item["argvSha256"] == digest(stop_argv)]
    starts = [item for item in physical_step["native"] if item["mutation"] is True and item["argvSha256"] == digest(start_argv)]
    require(len(stops) == len(starts) == 1 and utc(stops[0]["finishedAt"]) <= utc(starts[0]["startedAt"]) and
            utc(starts[0]["startedAt"]) <= utc(current["state"]["StartedAt"]) <= utc(starts[0]["finishedAt"]),
            "PHYSICAL_RESTART_ORIGINAL_EXIT_UNPROVEN")
    require(utc(approval["validFrom"]) <= utc(stops[0]["startedAt"]) and
            utc(starts[0]["finishedAt"]) < utc(approval["validUntil"]), "PHYSICAL_RESTART_APPROVAL_EXPIRED")
    verify_large_pin(stop["approvalPin"], guard)
    return {"containerId": prepared["id"], "previousStartedAt": prepared["state"]["StartedAt"],
            "currentStartedAt": current["state"]["StartedAt"], "physicalResultPin": physical_step["pin"], "stopIntentPin": stop_pin}
