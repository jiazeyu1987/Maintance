"""Consume W04/W05 genuine heterogeneous originals without manufacturing wrappers."""
from pathlib import Path

from core import canonical, digest, fields, integer, need, pin_key, pins, same, timestamp


def terminal(record):
    state, actual = record.get("state"), record.get("actualExitCode")
    need(state != "TERMINAL_UNKNOWN", "ORIGINAL_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
    need(actual is None or type(actual) is int, "ORIGINAL_EXIT_INTEGER_REQUIRED")
    need(state == "SUCCEEDED" and record.get("failureCode") is None,
         "ORIGINAL_PROCESS_FAILED", "FAILED")
    if actual is not None:
        need(actual == 0, "ORIGINAL_PROCESS_FAILED", "FAILED")


def traced(context, start, finish):
    need(timestamp(context.trace["startedAt"]) <= timestamp(start) <= timestamp(finish) <=
         timestamp(context.trace["finishedAt"]), "INVOCATION_TIME")


def restore_originals(context, restore, target_record_pin, points):
    references = restore["originalInvocationPins"]
    keys = pins(references)
    records = {key: context.record(pin) for key, pin in zip(keys, references)}
    intents = [(pin, records[pin_key(pin)]) for pin in references
               if records[pin_key(pin)].get("schemaVersion") == "recovery-invocation/v1"]
    need(bool(intents), "RESTORE_NATIVE_INTENTS_REQUIRED")
    outputs, calls, materials = {}, [], {}
    for intent_pin, intent in intents:
        need(intent.get("style") == "operation", "RESTORE_NATIVE_STYLE_INVALID")
        for field in ("scriptPin", "pythonPin"):
            ref = intent[field]
            need(pin_key(ref) in context.source_keys, "INVOCATION_SOURCE_UNBOUND")
            context.read(ref)
        request_pin = intent["requestPin"]
        need(pin_key(request_pin) in records, "NATIVE_REQUEST_ORIGINAL_MISSING")
        request = records[pin_key(request_pin)]
        exit_record = native_exit(context, intent_pin, list(zip(references, records.values())))
        traced(context, intent["startedAt"], exit_record["finishedAt"])
        matches = [(key, value) for key, value in records.items()
                   if value.get("schemaVersion") in ("RecoveryDataStepResult/v1",
                                                     "backup-restore-operation-result/v1") and
                   value.get("operationId") == request.get("operationId") and
                   value.get("requestId") == request.get("requestId") and
                   value.get("action") == request.get("action")]
        need(len(matches) == 1, "NATIVE_RESULT_BINDING_INVALID")
        result_key, result = matches[0]
        need(result_key not in outputs, "NATIVE_RESULT_REUSED")
        terminal(result)
        need(request["operationId"] == context.request["operationId"], "OPERATION_RESTORE_MISMATCH", "STALE")
        result_pin = next(ref for ref in references if pin_key(ref) == result_key)
        need(Path(result_pin["path"]).parent == Path(request_pin["path"]).parent ==
             Path(intent_pin["path"]).parent, "NATIVE_ORIGINAL_DIRECTORY_MISMATCH")
        # Transport summaries are genuine private-stream hashes, not Codex command events.
        streams = [value for ref, value in zip(references, records.values())
                   if Path(ref["path"]).parent == Path(intent_pin["path"]).parent and
                   set(value) == {"stdout", "stderr"}]
        need(len(streams) == 1, "NATIVE_STREAM_SUMMARY_MISSING")
        for stream in streams[0].values():
            fields(stream, "bytes sha256")
            integer(stream["bytes"])
            need(type(stream["sha256"]) is str and len(stream["sha256"]) == 64, "NATIVE_STREAM_HASH_INVALID")
        if request["schemaVersion"] == "RecoveryDataRequest/v1":
            same(request["planPin"], restore["planPin"], "NATIVE_PLAN_MISMATCH")
            same(request["recoveryTargetPin"], target_record_pin, "NATIVE_TARGET_MISMATCH")
            original = context.record(request["originalRequestPin"])
            need(original["operationId"] == context.request["operationId"] and
                 original["mode"] == context.request["mode"] and
                 original["action"] in ("REHEARSAL", "RESTORE_EXECUTE", "CONTROLLED_CUTOVER"),
                 "NATIVE_ORIGINAL_REQUEST_MISMATCH")
            same(original["selectedPointPin"], context.plan["candidatePin"], "NATIVE_POINT_MISMATCH")
            same(original["sourceOrTargetRef"], context.plan["targetRef"], "NATIVE_TARGET_CONFIG_MISMATCH")
            material = context.record(request["materialPin"])
            need(material["schemaVersion"] == "RecoveryMaterial/v1", "NATIVE_MATERIAL_VERSION")
            same(material["sourceScopePin"], context.source_pin, "BUSINESS_SOURCE_SCOPE_MISMATCH")
            matching = [point for point in points if point["manifestPin"] == material["manifestPin"] and
                        point["pointType"] == material["pointType"] and
                        point["commonRecoveryPoint"] == material["recoveryPoint"]]
            need(len(matching) == 1, "NATIVE_MATERIAL_POINT_MISMATCH")
            data = result["data"]
            if request["action"] in ("DERIVED_DATA", "CONSISTENCY"):
                same(data["targetIdentityPin"], context.target_pin, "TARGET_MISMATCH")
            need(data["recoveryPoint"] == material["recoveryPoint"], "RECOVERY_POINT_MISMATCH", "STALE")
            materials[pin_key(request["materialPin"])] = material
            children = [(ref, context.record(ref)) for ref in result["originalResultPins"]]
            for child_pin, child in children:
                profile = child.get("schemaVersion")
                if profile == "RecoveryDataInvocation/v1":
                    need(child["operationId"] == request["operationId"] and child["action"] == request["action"],
                         "NATIVE_CHILD_ACTION_MISMATCH")
                elif profile == "RecoverySqlImporter/v1":
                    sql = child["sqlPin"]
                    context.read(sql)
                    database = material["database"]
                    if request["action"] == "DATABASE_FULL":
                        auxiliary = [ref for ref in context.trust["independentOriginalPins"]
                                     if Path(ref["path"]).name == "sql-import-intent.json" and
                                     Path(ref["path"]).parent == Path(sql["path"]).parent]
                        need(len(auxiliary) == 1, "NATIVE_SQL_EXPANSION_INTENT_REQUIRED")
                        expansion = context.record(auxiliary[0])
                        same(expansion["targetIdentityPin"], context.target_pin, "NATIVE_SQL_TARGET_MISMATCH")
                        same(expansion["sourceSqlPin"], database["sqlPin"], "NATIVE_SQL_SOURCE_MISMATCH")
                        need(expansion["operationId"] == context.request["operationId"] and
                             expansion["expandedSha256"] == sql["sha256"] and expansion["expandedBytes"] == sql["bytes"],
                             "NATIVE_SQL_EXPANSION_MISMATCH")
                    elif database["method"] == "BINLOG_SQL":
                        need(sql["bytes"] == database["rawSqlPin"]["bytes"] and
                             sql["sha256"] == database["rawSqlPin"]["sha256"], "NATIVE_SQL_PAYLOAD_MISMATCH")
                    else:
                        proofs = [context.record(ref) for ref in data["segmentEvidencePins"]]
                        need(any(proof["expandedPin"] == sql and proof["segment"] in database["segments"]
                                 for proof in proofs), "NATIVE_SQL_PAYLOAD_MISMATCH")
                elif profile in ("recovery-invocation/v1", "recovery-original-exit/v1",
                                 "RecoveryDerivedRequest/v1", "RecoveryDerivedExecutionResult/v1",
                                 "backup-restore-operation-result/v1") or set(child) == {"stdout", "stderr"}:
                    continue  # Validated together as one nested native invocation below.
                else:
                    need(False, "NATIVE_CHILD_PROFILE_UNSUPPORTED")
                terminal(child)
                need(child.get("actualExitCode") is not None, "ORIGINAL_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
                traced(context, child["startedAt"], child["finishedAt"])
            nested_derived_originals(context, children, material)
        elif request["schemaVersion"] == "backup-restore-operation/v1":
            need(request["action"] == "PREPARE_TARGET", "RESTORE_NATIVE_ACTION_INVALID")
            same(request["inputPins"]["restorePlan"], restore["planPin"], "NATIVE_PLAN_MISMATCH")
            need(result["data"] == context.record(target_record_pin), "PREPARED_TARGET_RESULT_MISMATCH")
        else:
            need(False, "NATIVE_REQUEST_PROFILE_UNSUPPORTED")
        outputs[result_key] = (request, result)
        calls.append({"pin": intent_pin, "startedAt": intent["startedAt"], "finishedAt": exit_record["finishedAt"],
                      "stage": request["action"], "resultPin": result_pin})
    expected_steps = restore["dbStepEvidencePins"] + restore["objectStepEvidencePins"]
    need(expected_steps and all(pin_key(ref) in outputs for ref in expected_steps), "RESTORE_STEP_EXIT_COVERAGE")
    database_actions = [outputs[pin_key(ref)][0]["action"] for ref in restore["dbStepEvidencePins"]]
    need(database_actions == ["DATABASE_FULL"] + ["DATABASE_INCREMENTAL"] * (len(points) - 1),
         "RESTORE_DATABASE_CHAIN_COVERAGE")
    for ref, point in zip(restore["dbStepEvidencePins"], points):
        request = outputs[pin_key(ref)][0]
        material = materials[pin_key(request["materialPin"])]
        need(material["recoveryPoint"] == point["commonRecoveryPoint"] and material["manifestPin"] == point["manifestPin"],
             "RESTORE_DATABASE_CHAIN_POINT_MISMATCH")
    object_actions = [outputs[pin_key(ref)][0]["action"] for ref in restore["objectStepEvidencePins"]]
    if object_actions == ["OBJECT_CHAIN_PHYSICAL"]:
        request, result = outputs[pin_key(restore["objectStepEvidencePins"][0])]
        need(len(request["allMaterialPins"]) == len(points), "RESTORE_PHYSICAL_CHAIN_INCOMPLETE")
        for ref, point in zip(request["allMaterialPins"], points):
            material = context.record(ref)
            same(material["sourceScopePin"], context.source_pin, "BUSINESS_SOURCE_SCOPE_MISMATCH")
            need(material["manifestPin"] == point["manifestPin"] and material["pointType"] == point["pointType"] and
                 material["recoveryPoint"] == point["commonRecoveryPoint"] and material["objects"]["method"] == "PHYSICAL_FILES",
                 "RESTORE_PHYSICAL_CHAIN_POINT_MISMATCH")
        physical = result["data"]
        need(physical["originalVersionIdsPreserved"] is True and len(physical["physicalStepEvidencePins"]) == len(points),
             "RESTORE_PHYSICAL_READBACK_INCOMPLETE")
        for ref in physical["physicalStepEvidencePins"] + [physical["comparisonPin"]]:
            context.read(ref)
    else:
        need(object_actions == ["OBJECT_FULL"] + ["OBJECT_INCREMENTAL"] * (len(points) - 1),
             "RESTORE_OBJECT_CHAIN_COVERAGE")
        for ref, point in zip(restore["objectStepEvidencePins"], points):
            request = outputs[pin_key(ref)][0]
            material = materials[pin_key(request["materialPin"])]
            need(material["recoveryPoint"] == point["commonRecoveryPoint"] and material["manifestPin"] == point["manifestPin"],
                 "RESTORE_OBJECT_CHAIN_POINT_MISMATCH")
    consistency = context.record(restore["consistencyEvidencePin"])
    need(consistency["schemaVersion"] == "RecoveryConsistencyEvidence/v1" and
         consistency["allReferencesVerified"] is True and consistency["invariantsVerified"] is True,
         "RESTORE_CONSISTENCY_INCOMPLETE")
    same(consistency["targetIdentityPin"], context.target_pin, "TARGET_MISMATCH")
    need(consistency["recoveryPoint"] == context.plan["recoveryPoint"], "RECOVERY_POINT_MISMATCH", "STALE")
    for field, action in (("originalConsistencyResultPin", "CONSISTENCY"), ("derivedEvidencePin", "DERIVED_DATA")):
        ref = consistency[field]
        need(pin_key(ref) in outputs and outputs[pin_key(ref)][0]["action"] == action,
             "RESTORE_CONSISTENCY_EXIT_COVERAGE")
        result = outputs[pin_key(ref)][1]
        if action == "CONSISTENCY":
            original_data = result["data"]
            need(original_data == {k: v for k, v in consistency.items()
                                  if k not in ("originalConsistencyResultPin", "derivedEvidencePin")},
                 "CONSISTENCY_AGGREGATE_MISMATCH")
        else:
            derived = result["data"]
            need(derived["schemaVersion"] == "RecoveryDerivedEvidence/v1" and
                 derived["recoveryPoint"] == context.plan["recoveryPoint"], "DERIVED_RESULT_MISMATCH")
            same(derived["targetIdentityPin"], context.target_pin, "DERIVED_TARGET_MISMATCH")
            context.derived_inventory_pin = derived["inventoryPin"]
            context.derived_inventory = context.record(derived["inventoryPin"])
    need(hasattr(context, "derived_inventory"), "DERIVED_INVENTORY_MISSING")
    need(any(material["derivedInventoryPin"] == context.derived_inventory_pin for material in materials.values()
             if material["recoveryPoint"] == context.plan["recoveryPoint"]), "DERIVED_MATERIAL_MISMATCH")
    return calls


def nested_derived_originals(context, records, material):
    by_key = {pin_key(ref): value for ref, value in records}
    for intent_pin, intent in records:
        if intent.get("schemaVersion") != "recovery-invocation/v1":
            continue
        need(intent["style"] == "operation", "DERIVED_NATIVE_STYLE_INVALID")
        for key in ("pythonPin", "scriptPin"):
            need(pin_key(intent[key]) in context.source_keys, "INVOCATION_SOURCE_UNBOUND")
            context.read(intent[key])
        need(pin_key(intent["requestPin"]) in by_key, "NATIVE_REQUEST_ORIGINAL_MISSING")
        request = by_key[pin_key(intent["requestPin"])]
        need(request["schemaVersion"] == "RecoveryDerivedRequest/v1" and
             request["operationId"] == context.request["operationId"] and
             request["recoveryPoint"] == material["recoveryPoint"], "DERIVED_NATIVE_REQUEST_MISMATCH")
        same(request["targetIdentityPin"], context.target_pin, "DERIVED_TARGET_MISMATCH")
        same(request["classificationPin"], material["derivedInventoryPin"], "DERIVED_INVENTORY_MISMATCH")
        original_exit = native_exit(context, intent_pin, records)
        traced(context, intent["startedAt"], original_exit["finishedAt"])
        results = [record for _, record in records if record.get("schemaVersion") == "backup-restore-operation-result/v1" and
                   record.get("operationId") == request["operationId"] and record.get("requestId") == request["requestId"] and
                   record.get("action") == request["action"]]
        need(len(results) == 1, "DERIVED_NATIVE_RESULT_MISSING")
        terminal(results[0])
        output = results[0]["data"]
        need(output["schemaVersion"] == "RecoveryDerivedExecution/v1" and output["state"] == "VERIFIED" and
             output["className"] == request["className"] and output["recoveryPoint"] == request["recoveryPoint"] and
             output["externalDispatchBlocked"] is True, "DERIVED_NATIVE_RESULT_MISMATCH")
        same(output["targetIdentityPin"], context.target_pin, "DERIVED_TARGET_MISMATCH")
        for proof in output["verificationPins"]:
            context.read(proof)


def application_originals(context, application):
    references = application["originalStartResultPins"]
    pins(references)
    records = [(ref, context.record(ref)) for ref in references]
    launches = [(ref, item) for ref, item in records if item.get("schemaVersion") == "RecoveryApplicationLaunch/v1"]
    need(len(launches) == 1, "APPLICATION_NATIVE_LAUNCH_REQUIRED")
    launch_pin, launch = launches[0]
    context.bind(launch)
    same(launch["restoreResultPin"], context.request["inputPins"]["restoreExecutionResult"], "APP_RESTORE_MISMATCH")
    same(launch["configurationPin"], application["configurationPin"], "APPLICATION_CONFIGURATIONPIN_MISMATCH")
    need(pins(launch["imagePins"]) == pins(application["imagePins"]), "APPLICATION_IMAGE_MISMATCH")
    need(launch["created"] and launch["started"], "APPLICATION_SERVICE_ORIGINALS_MISSING")
    for service in launch["started"]:
        need(service["labels"]["intruoyi.recovery.target"] == context.record(context.target_pin)["targetId"] and
             service["labels"]["intruoyi.recovery.operation"] == context.request["operationId"] and
             service["state"]["Running"] is True, "APPLICATION_SERVICE_IDENTITY_MISMATCH")
    calls = []
    sequences = set()
    for ref, item in records:
        if item.get("schemaVersion") == "RecoveryApplicationLaunch/v1":
            continue
        need(item.get("schemaVersion") == "RecoveryEnvironmentInvocation/v1", "APPLICATION_NATIVE_PROFILE_UNSUPPORTED")
        need(Path(ref["path"]).parent == Path(launch_pin["path"]).parent, "APPLICATION_NATIVE_DIRECTORY_MISMATCH")
        terminal(item)
        need(item["actualExitCode"] is not None and type(item["pid"]) is int and item["pid"] > 0,
             "ORIGINAL_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
        need(item["sequence"] not in sequences, "APPLICATION_NATIVE_SEQUENCE_REUSED")
        sequences.add(item["sequence"])
        traced(context, item["startedAt"], item["finishedAt"])
        need(timestamp(item["finishedAt"]) <= timestamp(launch["observedAt"]), "APPLICATION_NATIVE_TIME_MISMATCH")
        calls.append({"pin": ref, "startedAt": item["startedAt"], "finishedAt": item["finishedAt"],
                      "stage": "START_APPLICATION", "mutation": item["mutation"]})
    need(any(item["mutation"] is True for item in calls), "APPLICATION_ORIGINAL_EXIT_REQUIRED")
    health = context.record(application["healthEvidencePin"])
    context.bind(health)
    need(health["schemaVersion"] == "RecoveryApplicationHealth/v1" and health["state"] == "SUCCEEDED" and
         timestamp(health["observedAt"]) >= timestamp(launch["observedAt"]), "APPLICATION_HEALTH_BINDING_INVALID")
    context.application_launch = launch
    return calls


def isolation_lifecycle(context, target, application):
    observations = []
    for ref in (target["sideEffectIsolationPin"], application["sideEffectIsolationPin"]):
        item = context.record(ref)
        need(item["schemaVersion"] == "RecoverySideEffectIsolation/v1" and
             item["operationId"] == context.request["operationId"] and item["state"] == "ENFORCED",
             "SIDE_EFFECT_LIFECYCLE_INVALID")
        same(item["targetIdentityPin"], context.target_pin, "TARGET_MISMATCH")
        same(item["policyPin"], context.plan["sideEffectPolicyPin"], "SIDE_EFFECT_POLICY_MISMATCH")
        for pin in item["startupInventoryPins"]:
            context.read(pin)
        need(item["firewall"]["state"] == "ENFORCED" and bool(item["firewall"]["rules"]),
             "SIDE_EFFECT_FIREWALL_UNPROVEN")
        observations.append(item)
    before, after = observations
    need(before["startupInventoryPins"] == after["startupInventoryPins"] and
         timestamp(before["observedAt"]) <= timestamp(after["observedAt"]),
         "SIDE_EFFECT_LIFECYCLE_MISMATCH")
    need(after["sourceWritesPerformed"] is False and after["writeProtectionState"] == "ENFORCED",
         "WRITE_PROTECTION_NOT_ENFORCED")
    for phase in ("blockedBefore", "blockedAfter"):
        probes = after[phase]
        need(type(probes) is list and bool(probes), "SIDE_EFFECT_PROBES_MISSING")
        need(all(probe["result"].get("blocked") is True or probe["result"].get("externalDnsBlocked") is True
                 for probe in probes), "SIDE_EFFECT_PROBE_FAILED")
    proof = context.record(target["isolationProofPin"])
    resources = context.record(target["resourcesProofPin"])
    need(proof["schemaVersion"] == "RecoveryIsolationProof/v1" and proof["state"] == "ENFORCED" and
         proof["operationId"] == context.request["operationId"] and proof["targetId"] == target["targetId"] and
         proof["network"] == resources["network"] and bool(proof["blockedEndpointProbes"]) and
         timestamp(proof["observedAt"]) <= timestamp(after["observedAt"]), "PREPARATION_ISOLATION_UNBOUND")
    need(all(item["result"].get("blocked") is True or item["result"].get("externalDnsBlocked") is True
             for item in proof["blockedEndpointProbes"]), "PREPARATION_ISOLATION_PROBE_FAILED")
    from application_protection import verify_application_protection
    verify_application_protection(context, application, after, resources)


def native_exit(context, intent_pin, records):
    """Bind a native local exit and, when present, its separate remote terminal original."""
    exits = [(ref, value) for ref, value in records if value.get("schemaVersion") == "recovery-original-exit/v1" and
             pin_key(value["intentPin"]) == pin_key(intent_pin)]
    local = [(ref, value) for ref, value in exits if "localExitPin" not in value]
    combined = [(ref, value) for ref, value in exits if "localExitPin" in value]
    need(len(local) == 1 and len(combined) <= 1 and len(exits) == 1 + len(combined), "NATIVE_EXIT_ORIGINAL_MISSING")
    local_pin, local_record = local[0]
    final = combined[0][1] if combined else local_record
    if combined:
        same(final["localExitPin"], local_pin, "NATIVE_LOCAL_EXIT_BINDING_MISMATCH")
        need(final["actualExitCode"] == local_record["actualExitCode"] and
             timestamp(local_record["finishedAt"]) <= timestamp(final["finishedAt"]), "NATIVE_TERMINAL_BINDING_MISMATCH")
    for item in (local_record, final):
        need(item["timedOut"] is False and item["actualExitCode"] is not None and
             item.get("remoteTerminalConfirmed") is not False, "ORIGINAL_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
        need(type(item["actualExitCode"]) is int and item["actualExitCode"] == 0, "ORIGINAL_PROCESS_FAILED", "FAILED")
    if final.get("remoteTerminalConfirmed") is True:
        need(bool(combined) and bool(final["remoteTerminalProofPins"]), "REMOTE_TERMINAL_ORIGINALS_REQUIRED", "UNKNOWN")
        intent = context.record(intent_pin)
        request = context.record(intent["requestPin"])
        workflow = context.record(request["originalRequestPin"]) if request.get("schemaVersion") == "RecoveryDataRequest/v1" else request
        verify_remote_terminals(context, final["remoteTerminalProofPins"], context.record(workflow["policyPin"]))
    elif combined:
        need(final["remoteTerminalConfirmed"] is None and final["remoteTerminalProofPins"] == [],
             "REMOTE_TERMINAL_BINDING_INVALID")
    return final


def verify_remote_terminals(context, references, policy):
    """Verify W04's signed wait evidence against independently admitted authority keys."""
    import base64
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    records = [context.record(ref) for ref in references]
    signed = [item for item in records if item.get("schemaVersion") == "RecoveryRemoteSignedTerminal/v1"]
    need(bool(signed), "REMOTE_SIGNED_TERMINAL_REQUIRED", "UNKNOWN")
    need(type(policy.get("remoteTerminalKeyPins")) is list and bool(policy["remoteTerminalKeyPins"]),
         "REMOTE_TERMINAL_AUTHORITY_REQUIRED")
    authority_pins = policy["remoteTerminalKeyPins"]
    for certificate in signed:
        fields(certificate, "schemaVersion keySha256 payload signature", "RecoveryRemoteSignedTerminal/v1")
        keys = {pin_key(ref): ref for ref in authority_pins if ref["sha256"] == certificate["keySha256"]}
        need(len(keys) == 1, "REMOTE_TERMINAL_AUTHORITY_UNKNOWN")
        key = load_pem_public_key(context.read(next(iter(keys.values())), content=True))
        need(isinstance(key, Ed25519PublicKey), "REMOTE_TERMINAL_KEY_INVALID")
        try:
            key.verify(base64.b64decode(certificate["signature"], validate=True), canonical(certificate["payload"]))
        except Exception as error:
            from core import VerificationError
            raise VerificationError("REMOTE_TERMINAL_SIGNATURE_INVALID") from error
        value = certificate["payload"]
        fields(value, "schemaVersion operationId action targetIdentityPin sourceScopePin recoveryPoint commandIntentPin "
               "executionHostIdentityPin originalProcessPin exitEvidencePin validFrom validUntil", "RecoveryRemoteTerminal/v1")
        need(value["schemaVersion"] == "RecoveryRemoteTerminal/v1" and
             value["operationId"] == context.request["operationId"] and
             value["recoveryPoint"] == context.plan["recoveryPoint"], "REMOTE_TERMINAL_BINDING_INVALID")
        same(value["targetIdentityPin"], context.target_pin, "REMOTE_TERMINAL_TARGET_MISMATCH")
        same(value["sourceScopePin"], context.source_pin, "REMOTE_TERMINAL_SOURCE_MISMATCH")
        need({pin_key(value["originalProcessPin"]), pin_key(value["exitEvidencePin"])} <= set(pins(references)),
             "REMOTE_TERMINAL_ORIGINALS_REQUIRED")
        process, wait = context.record(value["originalProcessPin"]), context.record(value["exitEvidencePin"])
        context.read(value["executionHostIdentityPin"])
        need(process["schemaVersion"] == "RecoveryRemoteProcess/v1" and
             wait["schemaVersion"] == "RecoveryRemoteWait/v1" and type(process["nativePid"]) is int and
             process["nativePid"] > 0 and wait["waitedPid"] == process["nativePid"] and
             process["processStartIdentity"] == wait["processStartIdentity"] and bool(process["processStartIdentity"]) and
             wait["originalProcessPin"] == value["originalProcessPin"] and wait["processTerminated"] is True and
             wait["timedOut"] is False and type(wait["actualExitCode"]) is int and wait["actualExitCode"] == 0,
             "REMOTE_ORIGINAL_PROCESS_TERMINATION_NOT_PROVEN", "UNKNOWN")
        need(all(process[field] == value[field] for field in ("operationId", "action", "targetIdentityPin", "sourceScopePin",
                 "recoveryPoint", "commandIntentPin", "executionHostIdentityPin")), "REMOTE_PROCESS_BINDING_INVALID")
        intent = context.record(value["commandIntentPin"])
        need(timestamp(intent["startedAt"]) <= timestamp(process["startedAt"]) <= timestamp(wait["finishedAt"]) <=
             timestamp(value["validFrom"]) < timestamp(value["validUntil"]), "REMOTE_TERMINAL_TIME_BINDING_INVALID")
        from core import now
        need(timestamp(value["validFrom"]) <= timestamp(now()) < timestamp(value["validUntil"]),
             "REMOTE_TERMINAL_EXPIRED", "STALE")
        traced(context, process["startedAt"], wait["finishedAt"])
