"""Affected offline checks using W02's actual sealed r2 and W05's r1 evidence.

Invalid in-memory mutations test refusals only. No ready runtime fixture,
service mock, Registry/Native instance, business operation or dispatch is used.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
import registration as r

ROOT = Path(__file__).resolve().parent
small = r.load(ROOT / "smallapp.registration.json")
large = r.load(ROOT / "intruoyi.registration.json")
target_ref = small["allowedRestoreTargets"][0]["configRef"]
observed = r.local_document(small["evidencePins"]["sourceDeliveryObservation"])
checks = []
consumer_observation = {}


def rejected(function, code):
    try:
        function()
    except r.Invalid as error:
        assert str(error) == code, (str(error), code)
    else:
        raise AssertionError("invalid input accepted")


def mutate(path, item, code):
    value = deepcopy(small)
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = item
    rejected(lambda: r.validate(value), code)


def sealed_provenance():
    r.validate(small); r.validate(large)
    assert set(small) == set(large) == set(r.FIELDS)
    assert set(small["source"]["redis"]) == set(large["source"]["redis"]) == set(r.REDIS_FIELDS)
    delivery = r.local_document(observed["currentThreeComponentSourceDeliveryPin"])
    assert small["source"]["assetInventory"]["applicationDeliveryPin"] == observed["currentThreeComponentSourceDeliveryPin"]
    assert delivery["version"] == small["runtime"]["version"] == "smallapp-20261014-r2-redis"
    r.verified_raw(observed["currentThreeComponentArtifactPin"])
    with tarfile.open(observed["currentThreeComponentArtifactPin"]["path"], "r:gz") as archive:
        assert len([m for m in archive.getmembers() if m.isfile()]) == observed["archiveMembers"] == 26
        for entry in observed["snapshots"].values():
            original, snapshot = entry["producerMemberPin"], entry["snapshotPin"]
            assert original in delivery["sourcePins"]
            assert (snapshot["bytes"], snapshot["sha256"]) == (original["bytes"], original["sha256"])
            assert r.verified_raw(snapshot) == archive.extractfile(entry["archiveMember"]).read()
    assert large["redisRecovery"]["state"] == "UNCONFIGURED" and large["runtime"]["version"] is None
    return "Actual r2 delivery/archive and ten scoped archive members match; both registrations use the same structure. IntRuoyi remains unconfigured."


def owner_binding_refusals():
    mutate(("evidencePins", "applicationArtifact"), small["evidencePins"]["historicalTwoComponentSourceArtifact"], "REDIS_SOURCE_ARTIFACT_MISMATCH")
    mutate(("redisRecovery", "consumerPin"), small["evidencePins"]["uiContract"], "REDIS_CONSUMER_PIN_MISMATCH")
    mutate(("redisRecovery", "freshTarget", "policyPin"), small["evidencePins"]["runtimeConfigurationDescriptor"], "REDIS_SEALED_MEMBER_MISMATCH")
    mutate(("redisRecovery", "classifications", 0, "recipePin"), small["redisRecovery"]["freshTarget"]["policyPin"], "REDIS_CLASSIFICATION_OWNER_MISMATCH")
    mutate(("redisRecovery", "freshTarget", "reloginRequired"), False, "REDIS_FRESH_TARGET_POLICY_CONFLICT")
    mutate(("runtime", "version"), None, "REDIS_SEMANTICS_SOURCE_MISMATCH")
    value = deepcopy(small)
    old = value["evidencePins"]["historicalTwoComponentSourceDelivery"]
    value["redisRecovery"]["sourceDeliveryPin"] = old
    value["source"]["assetInventory"]["applicationDeliveryPin"] = old
    rejected(lambda: r.validate(value), "REDIS_SOURCE_SCOPE_SUPERSEDED")
    value = deepcopy(small)
    value["allowedRestoreTargets"][0]["configRef"] += "-invalid"
    value["allowedRestoreTargets"][0]["redis"]["configRef"] = value["allowedRestoreTargets"][0]["configRef"]
    rejected(lambda: r.validate(value), "REDIS_LOGICAL_ALIAS_POLICY_MISMATCH")
    return "Mismatched source artifact, sealed consumer/policy/recipe/version, historical r1 authority, wrong alias and incompatible fresh-target login rule refused."


def instance_and_classification_refusals():
    mutate(("source", "redis", "databaseIndex"), True, "REDIS_DATABASE_INDEX_INVALID")
    mutate(("source", "redis", "databaseIndex"), 1, "REDIS_TARGET_KEYSPACE_MISMATCH")
    value = deepcopy(small)
    value["source"]["redis"]["databaseIndex"] = value["allowedRestoreTargets"][0]["redis"]["databaseIndex"] = 1
    rejected(lambda: r.validate(value), "REDIS_ROLE_NAMESPACE_POLICY_MISMATCH")
    mutate(("source", "redis", "serverVersion"), "6.0.0", "REDIS_SERVER_VERSION_POLICY_INVALID")
    mutate(("source", "redis", "instanceId"), "brlab-20261012-smallapp-target-invalid", "REDIS_INSTANCE_SCOPE_INVALID")
    mutate(("allowedRestoreTargets", 0, "redis", "keyPrefix"), small["source"]["redis"]["keyPrefix"], "REDIS_TARGET_REUSES_SOURCE_NAMESPACE")
    mutate(("source", "redis", "resourceProofPin"), small["evidencePins"]["uiContract"], "UNKNOWN_REDIS_CANNOT_HAVE_PROOF")
    value = deepcopy(small)
    value["source"]["redis"]["endpoint"] = small["source"]["database"]["endpoint"]
    value["allowedRestoreTargets"][0]["redis"]["endpoint"] = value["source"]["redis"]["endpoint"]
    rejected(lambda: r.validate(value), "REDIS_TARGET_REUSES_SOURCE_RESOURCE")
    value = deepcopy(small)
    existing_ref = next(s["reference"] for s in small["secretReferences"] if s["reference"] is not None)
    role = next(s for s in value["secretReferences"] if s["role"] == "smallapp.redis")
    role.update(reference=existing_ref, state="GENERATED_UNRESOLVED")
    value["source"]["redis"]["secretReference"] = existing_ref
    value["allowedRestoreTargets"][0]["redis"]["secretReference"] = existing_ref
    rejected(lambda: r.validate(value), "REDIS_TARGET_REUSES_SOURCE_SECRET")
    declared = small["redisRecovery"]["classifications"]
    prefix = small["source"]["redis"]["keyPrefix"]
    for change, code in ((dict(treatment="NOT_PRESENT"), "REDIS_CLASSIFICATION_UNKNOWN"),
                         (dict(authoritativeSources=["REDIS"]), "REDIS_TREATMENT_AUTHORITY_CONFLICT"),
                         (dict(keyPatterns=["*"]), "REDIS_KEY_SCOPE_INVALID"),
                         (dict(keyPatterns=[prefix + "*", prefix + "session:*"]), "REDIS_KEY_CLASS_OVERLAP")):
        items = deepcopy(declared); items[0].update(change)
        rejected(lambda: r.redis_classifications(items, prefix), code)
    return "Declared DB0/version/role scope is strict; invalid proofs, source resource/private-reference reuse and invalid key classifications refused."


def action_scopes():
    def fields(action, target=None):
        return {item["field"] for item in r.missing(small, action, target)}
    full, start, restore = fields("FULL"), fields("START_APPLICATION"), fields("RESTORE", target_ref)
    assert "redisRecovery.state" not in full | restore
    assert not any(k.startswith("allowedRestoreTargets") for k in full)
    assert not full.intersection({"archive.fullParentChainRef", "archive.recoveryPointRef", "schedule", "retention", "source.assetInventory.capturedInventoryPin"})
    assert "archive.fullParentChainRef" in fields("INCREMENTAL")
    assert "archive.recoveryPointRef" in restore
    assert "source.redis.applicationUseProofPin" in full and "source.redis.applicationUseProofPin" not in start
    assert not any(k.endswith("applicationUseProofPin") for k in restore | fields("START_APPLICATION", target_ref))
    assert not any(k.startswith("source.database.") or k.startswith("source.objects.") or k.startswith("runtime.") or
                   k == "source.resourceBindingPin" or k == "source.redis.serverVersion" for k in restore)
    assert not any(k.startswith("archive.") or k.endswith("quiescenceDescriptorPin") for k in start)
    assert fields("RETENTION") == {"retention", "archive.servicePin", "archive.policyPin"}
    assert "schedule" in fields("SCHEDULE")
    assert "selectedTargetConfigRef" in fields("RESTORE")
    rejected(lambda: r.redis_inputs(small, "FULL", target_ref, "SEMANTIC"), "REDIS_TARGET_NOT_APPLICABLE")
    return "First FULL has no future parent/point/target/output prerequisite; initial RESTORE and protected startup do not require application-use proof."


def configured_semantic_projection():
    descriptor, policy, semantics, adapter = r.delivered_semantics(small)
    source = r.redis_inputs(small, "FULL", scope="SEMANTIC")
    target = r.redis_inputs(small, "RESTORE", target_ref, "SEMANTIC")
    for projection in (source, target):
        assert projection["projectionScope"] == "SEMANTIC" and projection["executionReadiness"] == "NOT_EVALUATED"
        assert projection["derivedClass"] == dict(classification=policy["redis"]["classification"],
            requiredForBusiness=policy["redis"]["requiredForBusiness"], executorKey=adapter["executorKey"],
            rebuildFrom=policy["redis"]["rebuildFrom"], configurationReferences=[small["redisRecovery"]["freshTarget"]["policyPin"]])
        assert projection["expiryRule"] == policy["redis"]["expiryRule"]
        assert projection["restoreExpectations"] == semantics["restoreExpectations"]
        assert projection["instance"]["state"] == "UNCONFIGURED" and projection["instance"]["serverVersion"] is None
        assert projection["secretReference"] == dict(role=descriptor["secretReferences"]["redis"], reference=None, resolverOwner="W05")
        assert projection["runtimeMissing"]
    assert source["instance"]["keyPrefix"] != target["instance"]["keyPrefix"]
    assert source["recovery"]["classifications"][0]["keyPatterns"] == [source["instance"]["keyPrefix"] + "*"]
    assert target["recovery"]["freshTarget"]["reloginRequired"] is True
    for action, selected in (("FULL", None), ("INCREMENTAL", None), ("RESTORE", target_ref), ("START_APPLICATION", None)):
        rejected(lambda: r.redis_inputs(small, action, selected), "REDIS_INPUTS_UNCONFIGURED")
    rejected(lambda: r.redis_inputs(small, "RESTORE", scope="SEMANTIC"), "REGISTERED_TARGET_REQUIRED")
    rejected(lambda: r.redis_inputs(large, "FULL", scope="SEMANTIC"), "SOURCE_REFERENCE_UNCONFIGURED")
    return "Actual configured source FULL/target RESTORE semantic projections succeed with exact policy/adapter/expiry/login rules and explicit runtime gaps; runtime projection remains refused."


def affected_cli():
    def run(*args):
        return subprocess.run([sys.executable, "-B", str(ROOT / "registration.py"), *args],
                              capture_output=True, text=True, encoding="utf-8")
    path = str(ROOT / "smallapp.registration.json")
    result = run("redis-inputs", path, "--action", "FULL", "--projection-scope", "SEMANTIC")
    assert result.returncode == 0 and json.loads(result.stdout)["projectionScope"] == "SEMANTIC"
    for extra, code in (([], "REDIS_PROJECTION_SCOPE_REQUIRED"),
                        (["--projection-scope", "RUNTIME"], "REDIS_INPUTS_UNCONFIGURED")):
        result = run("redis-inputs", path, "--action", "FULL", *extra)
        assert result.returncode == 2 and not result.stdout and json.loads(result.stderr)["errorCode"] == code
    for action in ("FULL", "INCREMENTAL", "RESTORE", "START_APPLICATION"):
        selected = ["--target-config-ref", target_ref] if action == "RESTORE" else []
        result = run("validate", path, "--require-action", action, *selected)
        assert result.returncode == 2 and json.loads(result.stdout)["executionReadiness"] == "NOT_EVALUATED"
    return "Explicit semantic CLI succeeds; omitted scope, runtime projection and required-action runtime gaps return exit=2."


def existing_pure_consumers():
    # This offline identifier is used only by pure frozen request parsers.
    projected = r.ui_request(small, "FULL", "smallapp-20261014000000000000000000000001")
    assert set(projected) == set("schemaVersion operationId action sourceConfigRef parentChainRef recoveryPointRef targetConfigRef".split())
    from recovery_control_registration import metadata, REDIS_FIELDS
    from recovery_control_smallapp import Failure
    consumer_observation["observedAt"] = datetime.now(timezone.utc).isoformat()
    consumer_observation["redisInstanceFields"] = REDIS_FIELDS.split()
    try:
        metadata(small)
    except Failure as error:
        assert str(error) == "REGISTRATION_REDIS_FIELDS_INVALID", str(error)
        consumer_observation.update(structureAccepted=False, errorCode=str(error))
    else:
        consumer_observation.update(structureAccepted=True, errorCode=None)
    return "Existing W01/Spug pure UI parsers accept unchanged FULL wire; actual metadata parser compatibility is recorded without Registry/Native construction."


def preserved_runtime_observation():
    installation = r.local_document(small["evidencePins"]["w05R1InstallationObservation"])
    published = installation["published"]
    assert published["actualSourceVersion"] == "smallapp-20261014-r1"
    assert published["applicationProtectedStartupExecuted"] is True and published["businessDataWritten"] is False
    assert published["redisApplicationConsumerInstalled"] is False and installation["currentR2InstallAccepted"] is False
    assert small["source"]["database"]["name"] == published["actualSourceSchema"]
    assert small["source"]["objects"]["bucket"] == published["actualSourceBucket"]
    assert small["source"]["database"]["coveragePin"] == small["source"]["objects"]["coveragePin"] == published["artifacts"]["actualInstallation"]
    r.verified_raw(published["artifacts"]["actualInstallation"])
    requirements = (ROOT / "r2-contracts/requirements.txt").read_text(encoding="utf-8").splitlines()
    assert small["runtime"]["dependencyNames"] == [item for item in requirements if item]
    assert len(small["runtime"]["dependencyNames"]) == 11
    assert all(small["runtime"][key] is None for key in ("pythonPin", "dependencyClosurePin", "configurationPin", "sourceConfigurationFields"))
    assert small["source"]["assetInventory"]["runtimeClosurePin"] is None
    return "Pinned r1 schema/bucket/protected/zero-business facts preserved; eleven declared r2 dependencies do not become observed r2 runtime/config/closure."


if __name__ == "__main__":
    for name, function in (("exact_r2_sealed_provenance", sealed_provenance),
                           ("actual_owner_binding_refusals", owner_binding_refusals),
                           ("instance_and_classification_refusals", instance_and_classification_refusals),
                           ("first_action_dependency_scopes", action_scopes),
                           ("configured_semantic_projection", configured_semantic_projection),
                           ("affected_cli", affected_cli), ("existing_pure_consumers", existing_pure_consumers),
                           ("preserved_w05_r1_and_unknown_r2_runtime", preserved_runtime_observation)):
        try:
            detail = function()
        except Exception as error:
            checks.append(dict(name=name, passed=False, errorClass=type(error).__name__,
                               diagnostic=str(error) if isinstance(error, (AssertionError, r.Invalid)) else type(error).__name__))
        else:
            checks.append(dict(name=name, passed=True, detail=detail))
    report = dict(schemaVersion="W08RedisRegistrationChecks/v2", at=datetime.now(timezone.utc).isoformat(),
                  scope="Actual r2 semantics and affected registrations/action/projection/consumer paths only",
                  passed=all(c["passed"] for c in checks), checks=checks, currentW01MetadataObservation=consumer_observation,
                  successfulConfiguredSemanticProjectionVerified=any(c["name"] == "configured_semantic_projection" and c["passed"] for c in checks),
                  successfulConfiguredRuntimeProjectionVerified=False, nativeAcceptance=False,
                  previousEvidenceReused="history/r1/checks.json and history/pre-r2-consumption/checks-redis.json: historical scopes only",
                  remoteCalls=0, businessWrites=0, serviceMocks=0)
    (ROOT / "checks-redis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["passed"] else 1)
