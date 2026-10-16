"""Producer-shaped engineering packets; no runtime or business acceptance claim."""
import copy
from pathlib import Path
import sys

from core import canonical, digest


def upgrade(packet):
    p = packet
    old = p.target
    p.target = p.put("identity-native", {"schemaVersion": "RecoveryTargetIdentity/v1", "targetId": "engineering-fixture",
                                     "machineId": "host-fixture", "dockerEngineId": "engine-fixture",
                                     "sourceIdentityPin": p.put("business-source-identity", {"databaseUuid": "source-uuid"})})
    p.source_scope = p.put("business-source-scope", {"schemaVersion": "RecoverySourceScope/v1",
        "machineId": "source-host", "sourceIdentityPin": p.all_pins["business-source-identity"],
        "containerIds": ["source-container"], "containerNames": ["source-minio"], "writerContainerIds": [],
        "volumeNames": ["source-volume"], "networkNames": ["source-network"], "materialPaths": [],
        "endpointHosts": ["10.255.0.1"]})
    # Replace the exact target Pin throughout the inherited fixture, without minting a grant at runtime.
    for name, pin in list(p.all_pins.items()):
        if old["sha256"].encode() in Path(pin["path"]).read_bytes():
            p.change(name, lambda record: _replace_in_place(record, old, p.target))
    p.request = _replace(p.request, old, p.target)
    firewall = {"state": "ENFORCED", "rules": [["FORWARD", "-j", "DROP"]], "observedAt": p.time(2)}
    environment_policy = p.put("environment-policy", {"schemaVersion": "RecoveryEnvironmentPolicy/v1"})
    prepared_isolation = {"schemaVersion": "RecoverySideEffectIsolation/v1", "operationId": "op1",
        "targetIdentityPin": p.target, "state": "ENFORCED", "policyPin": environment_policy,
        "startupInventoryPins": [], "firewall": firewall, "observedAt": p.time(2)}
    p.isolation = p.put("prepared-isolation", prepared_isolation)
    p.application_isolation = p.put("application-isolation", {**prepared_isolation, "observedAt": p.time(10),
        "sourceWritesPerformed": False, "writeProtectionState": "ENFORCED",
        "blockedBefore": [{"result": {"blocked": True}}], "blockedAfter": [{"result": {"externalDnsBlocked": True}}]})
    minio = {"id": "minio-target", "name": "/fixture-minio", "imageId": "fixture-minio-image",
        "labels": {"intruoyi.recovery.target": "engineering-fixture", "intruoyi.recovery.operation": "op1"},
        "networks": {"fixture-network": {"NetworkID": "network-target", "EndpointID": "endpoint-target",
                                          "IPAddress": "10.254.0.3"}}, "state": {"Running": True}}
    configuration = {"schemaVersion": "RecoveryEnvironmentConfig/v1", "sourceScopePin": p.source_scope,
        "targetIdentityPin": p.target, "dockerPin": p.tool, "pythonPin": p.native_python_pin if hasattr(p, "native_python_pin") else
        {"path": str(Path(sys.executable).resolve()), "bytes": Path(sys.executable).stat().st_size,
         "sha256": digest(Path(sys.executable).read_bytes())},
        "services": [{"role": "minio", "name": "fixture-minio", "health": {"port": 9000}}]}
    p.target_ref = p.put("target-configuration-native", configuration)
    p.change("plan", lambda r: r.update(targetRef=p.target_ref, sideEffectPolicyPin=environment_policy))
    p.plan = p.all_pins["plan"]
    proof = p.put("resources-native", {"schemaVersion": "RecoveryEnvironmentProof/v1", "operationId": "op1",
        "targetIdentityPin": p.target, "configurationRef": p.target_ref, "services": [minio],
        "resources": {"machineId": "host-fixture", "dockerEngineId": "engine-fixture"},
        "network": {"networkId": "network-target"}})
    isolation_proof = p.put("preparation-isolation-proof", {"schemaVersion": "RecoveryIsolationProof/v1", "state": "ENFORCED",
        "operationId": "op1", "targetId": "engineering-fixture", "network": {"networkId": "network-target"},
        "blockedEndpointProbes": [{"result": {"blocked": True}}], "observedAt": p.time(2)})
    p.change("target", lambda r: r.update(targetIdentityPin=p.target, resourcesProofPin=proof,
                                          isolationProofPin=isolation_proof, sideEffectIsolationPin=p.isolation))
    p.target_record = p.all_pins["target"]
    p.object_binding = p.put("object-binding", {"schemaVersion": "RecoveryServiceBinding/v1",
        "targetIdentityPin": p.target, "sourceScopePin": p.source_scope, "environmentConfigPin": p.target_ref,
        "resourcesProofPin": proof, "dockerPin": p.tool, "machineIdPath": str(p.root / "machine-id"),
        "role": "minio", "endpointUrl": "http://10.254.0.3:9000"})
    p.change("verification-target", lambda r: r.update(targetIdentityPin=p.target, objectBindingPin=p.object_binding))
    p.verification_target = p.all_pins["verification-target"]
    p.derived_inventory = p.put("derived-inventory", {"schemaVersion": "RecoveryDerivedInventory/v1",
        "complete": True, "recoveryPoint": "point-1",
        "classes": {name: {"classification": "NOT_PRESENT", "requiredForBusiness": False,
                            "payloadPins": [], "executorKey": None} for name in ("redis", "queue")}})
    material = p.put("material", {"schemaVersion": "RecoveryMaterial/v1", "sourceScopePin": p.source_scope,
        "manifestPin": p.all_pins["manifest"], "pointType": "FULL", "recoveryPoint": "point-1", "derivedInventoryPin": p.derived_inventory,
        "payloadPins": [p.all_pins["payload"]]})
    original = p.put("original-request", {**p.request, "sourceOrTargetRef": p.target_ref,
        "action": "REHEARSAL", "policyPin": environment_policy, "inputPins": {"repositoryPoint": p.point},
        "leaseRef": p.lease})
    invocations, results, calls = [], {}, []
    python_path = Path(sys.executable).resolve()
    python_pin = {"path": str(python_path), "bytes": python_path.stat().st_size,
                  "sha256": digest(python_path.read_bytes())}
    p.native_python_pin = python_pin
    for index, action in enumerate(("DATABASE_FULL", "OBJECT_FULL", "DERIVED_DATA", "CONSISTENCY")):
        folder = p.root / ("native-%s" % index)
        folder.mkdir()
        request = {"schemaVersion": "RecoveryDataRequest/v1", "operationId": "op1", "requestId": "native-%s" % index,
                   "action": action, "originalRequestPin": original, "planPin": p.plan,
                   "recoveryTargetPin": p.target_record, "materialPin": material, "deadlineMilliseconds": 20000}
        request_pin = p.blob_at("native-request-%s" % index, folder / "request.json", request)
        intent = p.blob_at("native-intent-%s" % index, folder / "intent.json",
            {"schemaVersion": "recovery-invocation/v1", "scriptPin": p.tool, "pythonPin": python_pin,
             "requestPin": request_pin, "startedAt": p.time(3 + index), "style": "operation"})
        streams = p.blob_at("native-streams-%s" % index, folder / "streams.json",
            {name: {"bytes": 0, "sha256": digest(b"")} for name in ("stdout", "stderr")})
        exit_pin = p.blob_at("restore-call-%s" % index, folder / "exit.json",
            {"schemaVersion": "recovery-original-exit/v1", "intentPin": intent,
             "actualExitCode": 0, "timedOut": False, "remoteTerminalConfirmed": None, "finishedAt": p.time(7)})
        data = {"recoveryPoint": "point-1"}
        if action == "DERIVED_DATA":
            data.update(schemaVersion="RecoveryDerivedEvidence/v1", targetIdentityPin=p.target,
                        inventoryPin=p.derived_inventory, classes=[])
        elif action == "CONSISTENCY":
            data.update(schemaVersion="RecoveryConsistencyEvidence/v1", targetIdentityPin=p.target,
                        allReferencesVerified=True, invariantsVerified=True)
        result = p.blob_at("native-result-%s" % index, folder / "result.json",
            {"schemaVersion": "RecoveryDataStepResult/v1", "operationId": "op1", "requestId": request["requestId"],
             "action": action, "state": "SUCCEEDED", "failureCode": None, "data": data,
             "originalResultPins": [], "actualExitCode": None, "startedAt": p.time(3 + index), "finishedAt": p.time(7)})
        invocations.extend([intent, request_pin, streams, exit_pin, result])
        results[action] = result
        calls.append(intent)
    consistency = p.put("consistency-native", {**data, "derivedEvidencePin": results["DERIVED_DATA"],
                                                "originalConsistencyResultPin": results["CONSISTENCY"]})
    p.change("restore", lambda r: r.update(targetIdentityPin=p.target, planPin=p.plan,
        dbStepEvidencePins=[results["DATABASE_FULL"]], objectStepEvidencePins=[results["OBJECT_FULL"]],
        consistencyEvidencePin=consistency, originalInvocationPins=invocations))
    p.restore = p.all_pins["restore"]
    started = {"id": "backend-target", "name": "/fixture-backend", "imageId": "fixture-backend-image",
               "labels": minio["labels"], "state": {"Running": True}}
    launch = p.put("application-launch", {"schemaVersion": "RecoveryApplicationLaunch/v1", "operationId": "op1",
        "restoreId": "restore1", "restoreResultPin": p.restore, "targetIdentityPin": p.target,
        "created": [started], "started": [started], "imagePins": [p.image], "configurationPin": p.configuration,
        "network": {"networkId": "network-target", "containers": {"minio-target": {"Name": "fixture-minio",
            "EndpointID": "endpoint-target", "IPv4Address": "10.254.0.3/24"}}}, "observedAt": p.time(10)})
    start = p.put("application-native-call", {"schemaVersion": "RecoveryEnvironmentInvocation/v1", "sequence": 1,
        "argvSha256": digest(b"fixture-argv"), "mutation": True, "pid": 999, "startedAt": p.time(8),
        "finishedAt": p.time(9), "actualExitCode": 0, "state": "SUCCEEDED", "stdoutBytes": 0,
        "stdoutSha256": digest(b""), "stderrBytes": 0, "stderrSha256": digest(b"")})
    health = p.put("application-health", {"schemaVersion": "RecoveryApplicationHealth/v1", "operationId": "op1",
        "restoreId": "restore1", "targetIdentityPin": p.target, "state": "SUCCEEDED", "observedAt": p.time(10),
        "businessAcceptance": "NOT_PERFORMED"})
    from application_protection import SCOPES
    protection_spec = p.put("application-protection-policy", {"schemaVersion": "RecoveryApplicationWriteProtectionPolicy/v1",
        "targetIdentityPin": p.target, "configurationPin": p.configuration, "imagePins": [p.image],
        "mechanismId": "engineering-refusal-fixture", "sourceEvidencePins": [p.configuration],
        "enforceScriptPin": p.tool, "observeScriptPin": p.tool, "requiredScopes": sorted(SCOPES)})
    p.change("environment-policy", lambda r: r.update(applicationWriteProtectionPin=protection_spec))
    # A policy revision propagates its precise Pin through every native dependent original.
    environment_policy = p.all_pins["environment-policy"]
    p.change("plan", lambda r: r.update(sideEffectPolicyPin=environment_policy))
    p.plan = p.all_pins["plan"]
    p.change("original-request", lambda r: r.update(policyPin=environment_policy))
    original = p.all_pins["original-request"]
    for index in range(4):
        p.change("native-request-%s" % index, lambda r: r.update(planPin=p.plan, originalRequestPin=original))
        request_pin = p.all_pins["native-request-%s" % index]
        p.change("native-intent-%s" % index, lambda r: r.update(requestPin=request_pin))
        intent_pin = p.all_pins["native-intent-%s" % index]
        p.change("restore-call-%s" % index, lambda r: r.update(intentPin=intent_pin))
        invocations[index*5:index*5+5] = [intent_pin, request_pin, p.all_pins["native-streams-%s" % index],
                                       p.all_pins["restore-call-%s" % index], p.all_pins["native-result-%s" % index]]
        calls[index] = intent_pin
    p.change("restore", lambda r: r.update(planPin=p.plan, originalInvocationPins=invocations))
    p.restore = p.all_pins["restore"]
    p.change("application-launch", lambda r: r.update(restoreResultPin=p.restore))
    launch = p.all_pins["application-launch"]
    phase_pins, protection_calls = {}, []
    for sequence, phase, observed_time in ((2, "BEFORE_START", 8), (3, "AFTER_START", 9)):
        containers = {"minio": "minio-target"}
        if phase == "AFTER_START":
            containers["backend"] = "backend-target"
        scopes = []
        attempt = p.put("refusal-call-" + phase, {"schemaVersion": "RecoveryEnvironmentInvocation/v1",
            "pid": 1000 + sequence, "mutation": True, "state": "FAILED_RETAINED", "actualExitCode": 1,
            "startedAt": p.time(observed_time), "finishedAt": p.time(observed_time)})
        for scope in sorted(SCOPES):
            refusal = p.put("refusal-" + phase + scope, {"schemaVersion": "RecoveryApplicationWriteRefusal/v1",
                "scope": scope, "phase": phase, "denied": True, "operationId": "op1", "targetIdentityPin": p.target,
                "recoveryPoint": "point-1", "containers": containers, "beforeFingerprint": "b"*64,
                "afterFingerprint": "b"*64, "originalInvocationPins": [attempt]})
            scopes.append({"scope": scope, "enforcementPin": p.configuration, "beforeFingerprint": "b"*64,
                           "afterFingerprint": "b"*64, "rejectionObservationPins": [refusal]})
        observation = {"schemaVersion": "RecoveryApplicationWriteProtectionObservation/v1", "phase": phase,
            "operationId": "op1", "restoreId": "restore1", "targetIdentityPin": p.target, "recoveryPoint": "point-1",
            "policyPin": protection_spec, "containers": containers, "state": "ENFORCED", "observedAt": p.time(observed_time),
            "scopeObservations": scopes}
        receipt = p.put("protection-call-" + phase, {"schemaVersion": "RecoveryEnvironmentInvocation/v1", "sequence": sequence,
            "argvSha256": digest(canonical([configuration["pythonPin"]["path"], "-I", p.tool["path"]])),
            "pid": 900 + sequence, "mutation": True, "state": "SUCCEEDED", "actualExitCode": 0,
            "startedAt": p.time(observed_time), "finishedAt": p.time(observed_time),
            "stdoutBytes": len(canonical(observation)), "stdoutSha256": digest(canonical(observation))})
        protection_calls.append(receipt)
        phase_pins[phase] = p.put("protection-" + phase, {**observation, "originalInvocationPin": receipt, "executorPin": p.tool})
    p.change("prepared-isolation", lambda r: r.update(policyPin=environment_policy))
    p.isolation = p.all_pins["prepared-isolation"]
    p.change("target", lambda r: r.update(sideEffectIsolationPin=p.isolation))
    p.target_record = p.all_pins["target"]
    # Target changed, so propagate its Pin to each actual data request and intent/exit.
    for index in range(4):
        p.change("native-request-%s" % index, lambda r: r.update(recoveryTargetPin=p.target_record))
        p.change("native-intent-%s" % index, lambda r: r.update(requestPin=p.all_pins["native-request-%s" % index]))
        p.change("restore-call-%s" % index, lambda r: r.update(intentPin=p.all_pins["native-intent-%s" % index]))
        invocations[index*5:index*5+5] = [p.all_pins["native-intent-%s" % index], p.all_pins["native-request-%s" % index],
            p.all_pins["native-streams-%s" % index], p.all_pins["restore-call-%s" % index], p.all_pins["native-result-%s" % index]]
        calls[index] = p.all_pins["native-intent-%s" % index]
    p.change("restore", lambda r: r.update(originalInvocationPins=invocations))
    p.restore = p.all_pins["restore"]
    p.change("application-launch", lambda r: r.update(restoreResultPin=p.restore))
    launch = p.all_pins["application-launch"]
    p.change("application-isolation", lambda r: r.update(policyPin=environment_policy,
        applicationWriteProtectionPolicyPin=protection_spec, writeProtectionBeforePin=phase_pins["BEFORE_START"],
        writeProtectionAfterPin=phase_pins["AFTER_START"]))
    p.application_isolation = p.all_pins["application-isolation"]
    p.change("app", lambda r: r.update(targetIdentityPin=p.target, restoreResultPin=p.restore,
        sideEffectIsolationPin=p.application_isolation, originalStartResultPins=[start, *protection_calls, launch], healthEvidencePin=health))
    p.app = p.all_pins["app"]
    p.change("object-binding", lambda r: r.update(applicationStartPin=p.app))
    p.object_binding = p.all_pins["object-binding"]
    p.change("verification-target", lambda r: r.update(objectBindingPin=p.object_binding))
    p.verification_target = p.all_pins["verification-target"]
    object_target = {"schemaVersion": "RecoveryServiceObservation/v1", "bindingPin": p.object_binding,
        "targetIdentityPin": p.target, "operationId": "op1", "role": "minio", "endpointUrl": "http://10.254.0.3:9000",
        "machineId": "host-fixture", "dockerEngineId": "engine-fixture", "containerId": "minio-target",
        "imageId": "fixture-minio-image", "networkId": "network-target", "endpointId": "endpoint-target",
        "ipAddress": "10.254.0.3", "observedAt": p.time(12)}
    p.snapshot.update(objectTarget=object_target, derivedInventoryPin=p.derived_inventory, derived=[])
    p.change("data", lambda r: r.update(data=copy.deepcopy(p.snapshot)))
    p.change("baseline", lambda r: r.update(data=copy.deepcopy(p.snapshot)))
    p.change("before", lambda r: r["data"].update(sideEffectIsolationPin=p.isolation))
    p.change("after", lambda r: r["data"].update(sideEffectIsolationPin=p.application_isolation))
    p.change("timing-marks", lambda r: r.update(restoreStartInvocationPin=calls[0]))
    p.change("timing", lambda r: r["data"].update(restoreStartInvocationPin=calls[0]))
    p.change("policy", lambda r: r.update(recoveryTargetPin=p.target_record, verificationTargetPin=p.verification_target,
                                         derivedBaselinePin=None))
    p.request.update(sourceOrTargetRef=p.target_ref, policyPin=p.all_pins["policy"],
        inputPins={"restorePlan": p.all_pins["plan"], "restoreExecutionResult": p.all_pins["restore"],
                   "applicationStartResult": p.all_pins["app"]})
    p.policy = p.all_pins["policy"]


def _replace(value, old, new):
    if type(value) is dict:
        if value == old:
            return new
        return {key: _replace(item, old, new) for key, item in value.items()}
    if type(value) is list:
        return [_replace(item, old, new) for item in value]
    return value


def _replace_in_place(record, old, new):
    updated = _replace(record, old, new)
    record.clear()
    record.update(updated)
