"""Read-only application registration checks and existing UI request projection.

This tool does not dispatch, install, resolve secrets, sign records, or implement
backup/restore. Native configuration and registry originals stay with their owners.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

# Read-only consumer imports must not create bytecode in another owner's tree.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
FIELDS = "schemaVersion schemaRevision requiredComponents applicationId displayName batchId engineSelectionRef sourceConfigRef source runtime redisRecovery secretReferences archive allowedRestoreTargets schedule retention evidencePins".split()
PIN_FIELDS = {"path", "bytes", "sha256"}
REFERENCE = r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}"
ACTIONS = ("FULL", "INCREMENTAL", "RESTORE", "START_APPLICATION", "SCHEDULE", "RETENTION")
REVISION = "three-component-20261014-r1"
REDIS_FIELDS = "state role configRef instanceId containerId endpoint databaseIndex keyPrefix serverVersion runtimeConfigurationPin secretRole secretReference resourceProofPin applicationUseProofPin".split()


class Invalid(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise Invalid(code)


def exact(value, fields):
    need(type(value) is dict and set(value) == set(fields), "REGISTRATION_FIELDS_INVALID")


def reference(value, nullable=False):
    need((nullable and value is None) or
         (type(value) is str and re.fullmatch(REFERENCE, value) is not None),
         "REFERENCE_INVALID")


def pin(value, nullable=True):
    if value is None and nullable:
        return
    exact(value, PIN_FIELDS)
    need(type(value["path"]) is str and
         (PureWindowsPath(value["path"]).is_absolute() or PurePosixPath(value["path"]).is_absolute()),
         "PIN_PATH_INVALID")
    need(type(value["bytes"]) is int and value["bytes"] >= 0 and
         type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
         "PIN_INVALID")


def no_secret_values(value):
    forbidden = {"password", "passwordhash", "password_hash", "token", "accesstoken",
                 "accesskey", "secretkey", "privatekey", "connectionstring", "authkeybase64",
                 "controltoken", "signature"}
    if type(value) is dict:
        for key, item in value.items():
            need(key.lower() not in forbidden, "PLAINTEXT_OR_SECRET_MATERIAL_REFUSED")
            no_secret_values(item)
    elif type(value) is list:
        for item in value:
            no_secret_values(item)
    elif type(value) is str:
        need(re.search(r"://[^/\s]*@", value) is None, "CREDENTIAL_URL_REFUSED")


def load(path):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "DUPLICATE_JSON_FIELD")
            value[key] = item
        return value
    def constant(_):
        raise Invalid("NONFINITE_JSON_NUMBER")
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise Invalid("INPUT_MISSING_OR_INVALID") from None
    no_secret_values(value)
    return value


def nullable_text(value):
    need(value is None or (type(value) is str and bool(value) and "\0" not in value), "TEXT_INVALID")


def verified_raw(reference_value):
    pin(reference_value, nullable=False)
    path = Path(reference_value["path"])
    need(path.is_file(), "LOCAL_EVIDENCE_NOT_READABLE")
    raw = path.read_bytes()
    need(len(raw) == reference_value["bytes"] and hashlib.sha256(raw).hexdigest() == reference_value["sha256"],
         "LOCAL_EVIDENCE_CHANGED")
    return raw


def local_document(reference_value):
    verified_raw(reference_value)
    return load(reference_value["path"])


def runtime_fields(value):
    """Use W02's actual published field descriptor for the partial source config."""
    fields = value["runtime"]["sourceConfigurationFields"]
    if fields is None:
        return
    descriptor_pin = value["evidencePins"].get("runtimeConfigurationDescriptor")
    need(descriptor_pin is not None, "RUNTIME_DESCRIPTOR_REQUIRED")
    descriptor = local_document(descriptor_pin)
    need(descriptor["schemaVersion"] == "SmallAppConfigurationDescriptor/v2", "RUNTIME_DESCRIPTOR_INVALID")
    exact(fields, descriptor["backendRequiredFields"])
    for key, descriptor_key in (("database", "databaseRequiredFields"), ("s3", "s3RequiredFields"),
                                 ("http", "backendHttpRequiredFields"), ("redis", "redisRequiredFields")):
        exact(fields[key], descriptor[descriptor_key])
    redis = value["source"]["redis"]
    need(fields["schemaVersion"] == descriptor["backendRuntimeSchema"] == "SmallAppRuntimeConfig/v2" and
         fields["version"] == value["runtime"]["version"] == descriptor["version"] and
         fields["logicalConfigRef"] == value["sourceConfigRef"] and fields["runtimeRole"] == "SOURCE" and
         fields["tenantId"] == descriptor["fixedIdentity"]["tenantId"] and
         fields["username"] == descriptor["fixedIdentity"]["username"] and
         fields["database"]["name"] == value["source"]["database"]["name"] and
         fields["database"]["host"] == value["source"]["database"]["endpoint"] and
         fields["s3"]["bucket"] == value["source"]["objects"]["bucket"] and
         fields["s3"]["keyPrefix"] == value["source"]["objects"]["keyPrefix"] == descriptor["keyPrefix"] and
         fields["secretRefs"] == descriptor["secretReferences"] and
         fields["redis"]["host"] == redis["endpoint"] and fields["redis"]["instanceId"] == redis["instanceId"] and
         fields["redis"]["database"] == redis["databaseIndex"] and fields["redis"]["keyPrefix"] == redis["keyPrefix"] and
         fields["redis"]["serverVersion"] == redis["serverVersion"], "RUNTIME_REGISTRATION_MISMATCH")


def delivered_semantics(value):
    """Bind the actual sealed producer family, not a working file or a live proof."""
    recovery = value["redisRecovery"]
    need(recovery["state"] == "OWNER_DELIVERED", "REDIS_SEMANTICS_UNCONFIGURED")
    observed = local_document(value["evidencePins"]["sourceDeliveryObservation"])
    need(recovery["sourceDeliveryPin"] == observed["currentThreeComponentSourceDeliveryPin"],
         "REDIS_OWNER_DELIVERY_MISMATCH")
    delivery = local_document(recovery["sourceDeliveryPin"])
    need(delivery["schemaVersion"] == "SmallAppThreeComponentSourceDelivery/v1" and
         delivery["version"] == recovery["applicationVersion"] == value["runtime"]["version"],
         "REDIS_PRODUCER_FAMILY_OR_VERSION_INVALID")
    need(value["evidencePins"].get("applicationArtifact") ==
         observed["currentThreeComponentArtifactPin"] == delivery["sourceArtifactPin"],
         "REDIS_SOURCE_ARTIFACT_MISMATCH")
    verified_raw(delivery["sourceArtifactPin"])
    def member(name, claimed):
        entry = observed["snapshots"][name]
        original = entry["producerMemberPin"]
        need(claimed == entry["snapshotPin"] and original in delivery["sourcePins"] and
             claimed["bytes"] == original["bytes"] and claimed["sha256"] == original["sha256"],
             "REDIS_SEALED_MEMBER_MISMATCH")
        return local_document(claimed)
    descriptor = member("config-contract.json", value["evidencePins"]["runtimeConfigurationDescriptor"])
    policy = member("redis-policy.json", recovery["freshTarget"]["policyPin"])
    semantics = member("recovery-semantics.json", recovery["semanticsPin"])
    cache = observed["snapshots"]["redis_cache.py"]
    need(recovery["consumerPin"] == cache["snapshotPin"] and cache["producerMemberPin"] in delivery["sourcePins"] and
         cache["snapshotPin"]["bytes"] == cache["producerMemberPin"]["bytes"] and
         cache["snapshotPin"]["sha256"] == cache["producerMemberPin"]["sha256"], "REDIS_CONSUMER_PIN_MISMATCH")
    verified_raw(recovery["consumerPin"])
    redis = policy["redis"]
    need(descriptor["version"] == policy["version"] == semantics["version"] == delivery["version"] and
         descriptor["schemaVersion"] == "SmallAppConfigurationDescriptor/v2" and
         policy["schemaVersion"] == "SmallAppRedisRecoveryPolicy/v1" and
         semantics["schemaVersion"] == "SmallAppRecoverySemantics/v1" and
         redis["classification"] == "REBUILD" and redis["rebuildFrom"] == "DATABASE" and
         redis["requiredForBusiness"] is True and redis["captureRedisPayload"] is False,
         "REDIS_ACTUAL_POLICY_MISMATCH")
    recipe_pin = delivery["existingDerivedAdapterContractPin"]
    adapter = local_document(recipe_pin)
    need(adapter["schemaVersion"] == "SmallAppExistingDerivedAdapterContract/v1" and
         adapter["version"] == delivery["version"] and adapter["classification"] == redis["classification"] and
         adapter["rebuildFrom"] == redis["rebuildFrom"] and adapter["executorKey"] == redis["executorKey"] and
         adapter["policyPin"] == delivery["redisPolicyPin"] and adapter["cacheSourcePin"] == cache["producerMemberPin"],
         "REDIS_EXISTING_ADAPTER_MISMATCH")
    source = value["source"]["redis"]
    need(value["sourceConfigRef"] == descriptor["logicalReferences"][0] and
         all(target["configRef"] == descriptor["logicalReferences"][1]
             for target in value["allowedRestoreTargets"]), "REDIS_LOGICAL_ALIAS_POLICY_MISMATCH")
    expected_classes = [dict(dataClass=adapter["className"], keyPatterns=[source["keyPrefix"] + "*"],
                             treatment=redis["classification"], authoritativeSources=["MYSQL"], recipePin=recipe_pin)]
    need(recovery["classifications"] == expected_classes, "REDIS_CLASSIFICATION_OWNER_MISMATCH")
    for instance in [source, *[t["redis"] for t in value["allowedRestoreTargets"]]]:
        prefix = descriptor["redisScope"]["keyPrefix"].replace("<source|target>", instance["role"].lower())
        need(instance["databaseIndex"] == descriptor["redisScope"]["database"] and
             instance["keyPrefix"] == prefix and instance["secretRole"] == descriptor["secretReferences"]["redis"],
             "REDIS_ROLE_NAMESPACE_POLICY_MISMATCH")
        if instance["instanceId"] is not None:
            need(re.fullmatch("brlab-20261012-smallapp-" + instance["role"].lower() + r"-[a-z0-9-]+",
                              instance["instanceId"]), "REDIS_INSTANCE_SCOPE_INVALID")
        if instance["serverVersion"] is not None:
            need(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", instance["serverVersion"]) and
                 tuple(map(int, instance["serverVersion"].split("."))) >= (6, 2, 0),
                 "REDIS_SERVER_VERSION_POLICY_INVALID")
    need(recovery["freshTarget"]["initialState"] == "EMPTY" and
         recovery["freshTarget"]["startupState"] == "PROTECTED" and
         recovery["freshTarget"]["reloginRequired"] is True and
         semantics["restoreExpectations"]["freshTargetLogin"], "REDIS_FRESH_TARGET_POLICY_CONFLICT")
    return descriptor, policy, semantics, adapter


def redis_classifications(items, key_prefix):
    """Finite, non-overlapping key scopes and explicit authoritative sources."""
    need(type(items) is list and items and type(key_prefix) is str and key_prefix,
         "REDIS_CLASSIFICATIONS_INVALID")
    names, patterns = set(), []
    for item in items:
        exact(item, "dataClass keyPatterns treatment authoritativeSources recipePin".split())
        reference(item["dataClass"])
        need(item["dataClass"] not in names, "REDIS_CLASSIFICATION_DUPLICATE")
        names.add(item["dataClass"])
        need(item["treatment"] in ("RECOVER", "REBUILD", "RELOGIN"), "REDIS_CLASSIFICATION_UNKNOWN")
        authorities = item["authoritativeSources"]
        need(type(authorities) is list and authorities and
             all(type(a) is str and a in ("MYSQL", "MINIO", "REDIS") for a in authorities) and
             len(authorities) == len(set(authorities)), "REDIS_AUTHORITY_INVALID")
        need((item["treatment"] != "RECOVER" or "REDIS" in authorities) and
             (item["treatment"] != "REBUILD" or "REDIS" not in authorities),
             "REDIS_TREATMENT_AUTHORITY_CONFLICT")
        keys = item["keyPatterns"]
        need(type(keys) is list and keys and all(
             type(k) is str and k.startswith(key_prefix) and "\0" not in k and
             not any(c in k for c in "?[]") and ("*" not in k or (k.endswith("*") and k.count("*") == 1))
             for k in keys), "REDIS_KEY_SCOPE_INVALID")
        for key in keys:
            for previous in patterns:
                overlap = key == previous or (key.endswith("*") and previous.startswith(key[:-1])) or (
                    previous.endswith("*") and key.startswith(previous[:-1]))
                need(not overlap, "REDIS_KEY_CLASS_OVERLAP")
            patterns.append(key)
        pin(item["recipePin"], nullable=False)
    return {item["treatment"] for item in items}


def redis_fields(value):
    """Validate declarations, never treat these metadata as native authority."""
    roles = {item["role"]: item for item in value["secretReferences"]}
    source = value["source"]["redis"]
    instances = [(source, "SOURCE", value["sourceConfigRef"])] + [
        (target["redis"], "TARGET", target["configRef"])
        for target in value["allowedRestoreTargets"]]
    for instance, role, config_ref in instances:
        exact(instance, REDIS_FIELDS)
        need(instance["role"] == role and instance["configRef"] == config_ref,
             "REDIS_ROLE_OR_CONFIG_REFERENCE_MISMATCH")
        need(instance["state"] in ("UNCONFIGURED", "OBSERVED_ALLOCATED"), "REDIS_STATE_INVALID")
        reference(instance["configRef"], nullable=True)
        reference(instance["secretRole"], nullable=True)
        reference(instance["secretReference"], nullable=True)
        for name in ("instanceId", "containerId", "endpoint", "keyPrefix", "serverVersion"):
            nullable_text(instance[name])
        if instance["keyPrefix"] is not None:
            need(not any(c in instance["keyPrefix"] for c in "*?[]") and
                 not any(ord(c) < 32 for c in instance["keyPrefix"]), "REDIS_KEY_PREFIX_INVALID")
        need(instance["databaseIndex"] is None or
             (type(instance["databaseIndex"]) is int and instance["databaseIndex"] >= 0),
             "REDIS_DATABASE_INDEX_INVALID")
        for name in ("runtimeConfigurationPin", "resourceProofPin", "applicationUseProofPin"):
            pin(instance[name])
        if instance["secretRole"] is not None:
            need(instance["secretRole"] in roles, "REDIS_SECRET_ROLE_NOT_REGISTERED")
        if instance["state"] == "UNCONFIGURED":
            need(instance["resourceProofPin"] is None and instance["applicationUseProofPin"] is None,
                 "UNKNOWN_REDIS_CANNOT_HAVE_PROOF")
        else:
            need(instance["containerId"] is not None or instance["endpoint"] is not None,
                 "REDIS_RESOURCE_IDENTITY_REQUIRED")
            need(all(instance[k] is not None for k in (
                "configRef", "instanceId", "databaseIndex", "keyPrefix", "serverVersion",
                "runtimeConfigurationPin", "secretRole", "secretReference", "resourceProofPin")),
                "ALLOCATED_REDIS_FIELDS_REQUIRED")
        if role == "TARGET":
            for name in ("containerId", "endpoint"):
                need(instance[name] is None or source[name] is None or instance[name] != source[name],
                     "REDIS_TARGET_REUSES_SOURCE_RESOURCE")
            need(instance["databaseIndex"] is None or source["databaseIndex"] is None or
                 instance["databaseIndex"] == source["databaseIndex"], "REDIS_TARGET_KEYSPACE_MISMATCH")
            need(instance["keyPrefix"] is None or source["keyPrefix"] is None or
                 instance["keyPrefix"] != source["keyPrefix"], "REDIS_TARGET_REUSES_SOURCE_NAMESPACE")
            need(instance["secretReference"] is None or source["secretReference"] is None or
                 instance["secretReference"] != source["secretReference"], "REDIS_TARGET_REUSES_SOURCE_SECRET")
        elif instance["secretReference"] is not None:
            need(instance["secretRole"] in roles and
                 instance["secretReference"] == roles[instance["secretRole"]]["reference"],
                 "REDIS_SOURCE_SECRET_REFERENCE_MISMATCH")
    runtime_pin = value["runtime"]["configurationPin"]
    if runtime_pin is not None and source["runtimeConfigurationPin"] is not None:
        need(runtime_pin == source["runtimeConfigurationPin"], "REDIS_RUNTIME_CONFIGURATION_MISMATCH")
    recovery = value["redisRecovery"]
    exact(recovery, "state applicationVersion sourceConfigRef sourceDeliveryPin semanticsPin consumerPin classifications freshTarget".split())
    need(recovery["state"] in ("UNCONFIGURED", "OWNER_DELIVERED"), "REDIS_SEMANTICS_STATE_INVALID")
    nullable_text(recovery["applicationVersion"])
    reference(recovery["sourceConfigRef"], nullable=True)
    for name in ("sourceDeliveryPin", "semanticsPin", "consumerPin"):
        pin(recovery[name])
    need(type(recovery["classifications"]) is list, "REDIS_CLASSIFICATIONS_INVALID")
    fresh = recovery["freshTarget"]
    exact(fresh, "initialState startupState reloginRequired policyPin".split())
    pin(fresh["policyPin"])
    if recovery["state"] == "UNCONFIGURED":
        need(all(recovery[k] is None for k in (
            "applicationVersion", "sourceConfigRef", "sourceDeliveryPin", "semanticsPin", "consumerPin")) and
             recovery["classifications"] == [] and all(v is None for v in fresh.values()),
             "UNCONFIGURED_REDIS_SEMANTICS_HAS_VALUES")
        return
    need(all(recovery[k] is not None for k in (
        "applicationVersion", "sourceConfigRef", "sourceDeliveryPin", "semanticsPin", "consumerPin")) and
         recovery["classifications"] and source["keyPrefix"] is not None,
         "DELIVERED_REDIS_SEMANTICS_FIELDS_REQUIRED")
    need(recovery["applicationVersion"] == value["runtime"]["version"] and
         recovery["sourceConfigRef"] == value["sourceConfigRef"] and
         recovery["sourceDeliveryPin"] == value["source"]["assetInventory"]["applicationDeliveryPin"],
         "REDIS_SEMANTICS_SOURCE_MISMATCH")
    need(recovery["sourceDeliveryPin"] != value["evidencePins"].get("historicalTwoComponentSourceDelivery"),
         "REDIS_SOURCE_SCOPE_SUPERSEDED")
    treatments = redis_classifications(recovery["classifications"], source["keyPrefix"])
    need(fresh["initialState"] == ("RESTORE_REQUIRED" if "RECOVER" in treatments else "EMPTY") and
         fresh["startupState"] == "PROTECTED" and type(fresh["reloginRequired"]) is bool and
         ("RELOGIN" not in treatments or fresh["reloginRequired"] is True) and fresh["policyPin"] is not None,
         "REDIS_FRESH_TARGET_POLICY_CONFLICT")
    delivered_semantics(value)


def validate(value):
    exact(value, FIELDS)
    no_secret_values(value)
    need(value["schemaVersion"] == "ApplicationRegistration/v1", "REGISTRATION_VERSION_INVALID")
    need(value["schemaRevision"] == REVISION and
         value["requiredComponents"] == ["MySQL", "MinIO", "Redis"], "COMPONENT_CONTRACT_INVALID")
    reference(value["applicationId"])
    need(type(value["displayName"]) is str and bool(value["displayName"]), "APPLICATION_NAME_REQUIRED")
    for name in ("batchId", "engineSelectionRef", "sourceConfigRef"):
        reference(value[name], nullable=True)
    source = value["source"]
    exact(source, "hostAddress root database objects redis assetInventory resourceBindingPin nativeConfigPin".split())
    for name in ("hostAddress", "root"):
        nullable_text(source[name])
    for name in ("resourceBindingPin", "nativeConfigPin"):
        pin(source[name])
    database = source["database"]
    exact(database, "name state serverUuid containerId endpoint tableNames coveragePin".split())
    objects = source["objects"]
    exact(objects, "bucket state keyPrefix containerId endpoint coveragePin".split())
    for data in (database, objects):
        need(data["state"] in ("UNCONFIGURED", "PROPOSED_NOT_ALLOCATED", "OBSERVED_ALLOCATED"),
             "RESOURCE_STATE_INVALID")
        pin(data["coveragePin"])
        for name, item in data.items():
            if name not in ("coveragePin", "tableNames"):
                nullable_text(item)
        if data["state"] == "UNCONFIGURED":
            need(data["coveragePin"] is None, "UNKNOWN_RESOURCE_CANNOT_HAVE_COVERAGE")
    need(type(database["tableNames"]) is list and
         all(type(name) is str and re.fullmatch(r"[A-Za-z0-9_]+", name) for name in database["tableNames"]) and
         len(database["tableNames"]) == len(set(database["tableNames"])),
         "TABLE_INVENTORY_INVALID")
    inventory = source["assetInventory"]
    exact(inventory, "state applicationFilePins applicationDeliveryPin runtimeClosurePin writerInventoryPin capturedInventoryPin".split())
    need(inventory["state"] in ("UNCONFIGURED", "OBSERVED_WORKING_SOURCE_INSTALL_PENDING", "OWNER_DELIVERED"),
         "INVENTORY_STATE_INVALID")
    need(type(inventory["applicationFilePins"]) is list, "APPLICATION_FILES_INVALID")
    for item in inventory["applicationFilePins"]:
        pin(item, nullable=False)
    for name in ("applicationDeliveryPin", "runtimeClosurePin", "writerInventoryPin", "capturedInventoryPin"):
        pin(inventory[name])
    runtime = value["runtime"]
    exact(runtime, "version pythonPin dependencyNames dependencyClosurePin configurationPin startupDescriptorPin quiescenceDescriptorPin sourceConfigurationFields".split())
    nullable_text(runtime["version"])
    need(type(runtime["dependencyNames"]) is list and all(type(name) is str and bool(name)
         for name in runtime["dependencyNames"]), "DEPENDENCY_NAMES_INVALID")
    for name in ("pythonPin", "dependencyClosurePin", "configurationPin", "startupDescriptorPin", "quiescenceDescriptorPin"):
        pin(runtime[name])
    need(runtime["sourceConfigurationFields"] is None or type(runtime["sourceConfigurationFields"]) is dict,
         "RUNTIME_FIELDS_INVALID")
    need(type(value["secretReferences"]) is list, "SECRET_REFERENCES_INVALID")
    roles = set()
    for item in value["secretReferences"]:
        exact(item, ("role", "reference", "state", "resolverOwner"))
        reference(item["role"]); reference(item["reference"], nullable=True)
        need(item["role"] not in roles and item["resolverOwner"] == "W05" and
             item["state"] in ("UNCONFIGURED", "GENERATED_UNRESOLVED", "OWNER_BOUND"), "SECRET_REFERENCE_STATE_INVALID")
        need((item["reference"] is None) == (item["state"] == "UNCONFIGURED"), "SECRET_REFERENCE_STATE_CONFLICT")
        roles.add(item["role"])
    archive = value["archive"]
    exact(archive, "root repositoryId servicePin policyPin fullParentChainRef recoveryPointRef independentReadbackRequired".split())
    nullable_text(archive["root"])
    for name in ("repositoryId", "fullParentChainRef", "recoveryPointRef"):
        reference(archive[name], nullable=True)
    for name in ("servicePin", "policyPin"):
        pin(archive[name])
    need(archive["independentReadbackRequired"] is True, "INDEPENDENT_READBACK_REQUIRED")
    need(type(value["allowedRestoreTargets"]) is list, "RESTORE_TARGETS_INVALID")
    targets = set()
    for target in value["allowedRestoreTargets"]:
        exact(target, "configRef hostAddress root resourceBindingPin nativeConfigPin freshnessProofPin allowedModes redis".split())
        reference(target["configRef"])
        need(target["configRef"] not in targets and target["configRef"] != value["sourceConfigRef"], "TARGET_REFERENCE_CONFLICT")
        targets.add(target["configRef"])
        nullable_text(target["hostAddress"]); nullable_text(target["root"])
        for name in ("resourceBindingPin", "nativeConfigPin", "freshnessProofPin"):
            pin(target[name])
        need(target["allowedModes"] == ["REHEARSAL"], "CURRENT_TARGET_MODE_NOT_AUTHORIZED")
    schedule = value["schedule"]
    exact(schedule, ("state", "timezone", "fullFrequency", "incrementalFrequency"))
    retention = value["retention"]
    exact(retention, ("state", "policyPin", "configuration"))
    for data in (schedule, retention):
        need(data["state"] in ("UNCONFIGURED", "CONFIGURED"), "POLICY_STATE_INVALID")
        if data["state"] == "UNCONFIGURED":
            need(all(item is None for name, item in data.items() if name != "state"), "UNCONFIGURED_POLICY_HAS_VALUES")
        else:
            need(all(item is not None for name, item in data.items() if name != "state"), "CONFIGURED_POLICY_MISSING_VALUES")
    for name in ("timezone", "fullFrequency", "incrementalFrequency"):
        nullable_text(schedule[name])
    pin(retention["policyPin"])
    need(retention["configuration"] is None or type(retention["configuration"]) is dict, "RETENTION_FIELDS_INVALID")
    need(type(value["evidencePins"]) is dict and bool(value["evidencePins"]), "EVIDENCE_REQUIRED")
    for item in value["evidencePins"].values():
        pin(item, nullable=False)
    runtime_fields(value)
    redis_fields(value)
    return value


def selected_target(value, target_ref):
    matches = [target for target in value["allowedRestoreTargets"] if target["configRef"] == target_ref]
    need(len(matches) == 1, "REGISTERED_TARGET_REQUIRED")
    return matches[0]


def redis_missing(value, action, target_ref=None):
    """Component prerequisites only. Startup/use proofs are not interchangeable."""
    needs = []
    def check(path, item, owner):
        if item is None or item == []:
            needs.append({"field": path, "owner": owner})
    recovery = value["redisRecovery"]
    if recovery["state"] != "OWNER_DELIVERED":
        needs.append({"field": "redisRecovery.state", "owner": "W02"})
    for key in ("applicationVersion", "sourceConfigRef", "sourceDeliveryPin", "semanticsPin", "consumerPin", "classifications"):
        check("redisRecovery." + key, recovery[key], "W02")
    for key, item in recovery["freshTarget"].items():
        check("redisRecovery.freshTarget." + key, item, "W02")
    source = value["source"]["redis"]
    for key in ("databaseIndex", "keyPrefix"):
        check("source.redis." + key, source[key], "W02")
    target_action = action == "RESTORE" or (action == "START_APPLICATION" and target_ref is not None)
    if target_action:
        if target_ref is None:
            needs.append({"field": "selectedTargetConfigRef", "owner": "W01/caller"})
            return needs
        target = selected_target(value, target_ref)
        check("allowedRestoreTargets." + target_ref + ".freshnessProofPin", target["freshnessProofPin"], "W05")
        instance, path = target["redis"], "allowedRestoreTargets." + target_ref + ".redis."
    else:
        instance, path = source, "source.redis."
    if instance["state"] != "OBSERVED_ALLOCATED":
        needs.append({"field": path + "state", "owner": "W05"})
    if instance["containerId"] is None and instance["endpoint"] is None:
        needs.append({"field": path + "containerIdOrEndpoint", "owner": "W05"})
    for key in ("configRef", "instanceId", "databaseIndex", "keyPrefix", "serverVersion", "runtimeConfigurationPin", "resourceProofPin", "secretRole", "secretReference"):
        check(path + key, instance[key], "W01/W05" if key == "configRef" else "W05")
    role = instance["secretRole"]
    secret = next((item for item in value["secretReferences"] if item["role"] == role), None)
    if instance["secretReference"] is None or (not target_action and
            (secret is None or secret["state"] != "OWNER_BOUND")):
        needs.append({"field": path + "secretReference.ownerResolution", "owner": "W05"})
    # Actual use is required for capture; initial protected startup produces it.
    if action in ("FULL", "INCREMENTAL", "SCHEDULE"):
        check(path + "applicationUseProofPin", instance["applicationUseProofPin"], "W05/W06")
    return needs


def missing(value, action, target_ref=None):
    """Report configuration prerequisites only; no live readiness or authority claim."""
    needs = []
    def check(path, item, owner):
        if item is None or item == []:
            needs.append({"field": path, "owner": owner})
    need(action in ACTIONS, "ACTION_INVALID")
    capture = action in ("FULL", "INCREMENTAL", "SCHEDULE")
    source_start = action == "START_APPLICATION" and target_ref is None
    if capture or action in ("RESTORE", "START_APPLICATION"):
        check("engineSelectionRef", value["engineSelectionRef"], "W01")
        check("sourceConfigRef", value["sourceConfigRef"], "W01")
        needs.extend(redis_missing(value, action, target_ref))
    if capture or source_start:
        for key in ("hostAddress", "root"):
            check("source." + key, value["source"][key], "W05")
        for key in ("resourceBindingPin", "nativeConfigPin"):
            check("source." + key, value["source"][key], "W01/W05" if key == "resourceBindingPin" else "W03/W02/W05")
        for lane in ("database", "objects"):
            if value["source"][lane]["state"] != "OBSERVED_ALLOCATED":
                needs.append({"field": "source." + lane + ".state", "owner": "W05"})
            check("source." + lane + ".coveragePin", value["source"][lane]["coveragePin"], "W02")
        for key in ("name", "serverUuid", "containerId", "endpoint", "tableNames"):
            check("source.database." + key, value["source"]["database"][key], "W02/W05")
        for key in ("bucket", "keyPrefix", "containerId", "endpoint"):
            check("source.objects." + key, value["source"]["objects"][key], "W02/W05")
        # The captured inventory is an output of FULL. It cannot be an input
        # prerequisite for starting the first FULL.
        for key in (("applicationDeliveryPin", "applicationFilePins", "runtimeClosurePin", "writerInventoryPin") if capture
                    else ("applicationDeliveryPin", "applicationFilePins", "runtimeClosurePin")):
            check("source.assetInventory." + key, value["source"]["assetInventory"][key],
                  "W05" if key == "runtimeClosurePin" else "W02")
        for key in (("configurationPin", "dependencyClosurePin", "startupDescriptorPin", "quiescenceDescriptorPin") if capture
                    else ("configurationPin", "dependencyClosurePin", "startupDescriptorPin")):
            check("runtime." + key, value["runtime"][key], "W05" if key == "configurationPin" else "W02/W05")
        for key in ("version", "pythonPin", "dependencyNames"):
            check("runtime." + key, value["runtime"][key], "W02/W05")
        fields = value["runtime"]["sourceConfigurationFields"]
        check("runtime.sourceConfigurationFields", fields, "W02/W05")
        # Generated target/bootstrap references are not source runtime inputs.
        if fields is not None:
            roles = {item["role"]: item for item in value["secretReferences"]}
            required_roles = fields["secretRefs"].values()
            if any(role not in roles or roles[role]["state"] != "OWNER_BOUND" for role in required_roles):
                needs.append({"field": "secretReferences.sourceRuntimeResolution", "owner": "W05"})
    if capture or action == "RESTORE":
        for key in ("root", "repositoryId", "servicePin", "policyPin"):
            check("archive." + key, value["archive"][key], "W03")
    if action == "INCREMENTAL":
        check("archive.fullParentChainRef", value["archive"]["fullParentChainRef"], "W01/W03")
    if action == "RESTORE":
        check("archive.recoveryPointRef", value["archive"]["recoveryPointRef"], "W01/W03")
        if not value["allowedRestoreTargets"]:
            needs.append({"field": "allowedRestoreTargets", "owner": "W05"})
    if action == "RESTORE" or (action == "START_APPLICATION" and target_ref is not None):
        if target_ref is not None:
            target = selected_target(value, target_ref)
            for key in ("resourceBindingPin", "nativeConfigPin"):
                check("allowedRestoreTargets." + target_ref + "." + key, target[key],
                      "W01/W04/W05" if key == "nativeConfigPin" else "W01/W05")
    if action == "SCHEDULE" and value["schedule"]["state"] == "UNCONFIGURED":
        needs.append({"field": "schedule", "owner": "user/root/Spug"})
    if action == "RETENTION":
        if value["retention"]["state"] == "UNCONFIGURED":
            needs.append({"field": "retention", "owner": "user/root/W03"})
        for key in ("servicePin", "policyPin"):
            check("archive." + key, value["archive"][key], "W03")
    return needs


def ui_request(value, action, operation_id, parent=None, point=None, target=None):
    """Project the issued shared request, then let both actual consumers parse it."""
    validate(value)
    need(action in ("FULL", "INCREMENTAL", "RESTORE"), "UI_ACTION_INVALID")
    need(value["sourceConfigRef"] is not None, "SOURCE_REFERENCE_UNCONFIGURED")
    if action == "INCREMENTAL":
        need(parent is not None and parent == value["archive"]["fullParentChainRef"], "REGISTERED_PARENT_REQUIRED")
    if action == "RESTORE":
        need(point is not None and point == value["archive"]["recoveryPointRef"], "REGISTERED_RECOVERY_POINT_REQUIRED")
        need(target in {item["configRef"] for item in value["allowedRestoreTargets"]}, "REGISTERED_TARGET_REQUIRED")
    request = dict(schemaVersion="SmallAppBackupUiRequest/v1", operationId=operation_id, action=action,
                   sourceConfigRef=value["sourceConfigRef"], parentChainRef=parent,
                   recoveryPointRef=point, targetConfigRef=target)
    # Import only pure request validators. No Native/HTTP bridge object is constructed.
    workspace = ROOT.parents[2]
    sys.path.insert(0, str(workspace / "backend/src/main/resources"))
    sys.path.insert(0, str(workspace / "ops/spug"))
    from recovery_control_smallapp import Failure, request as w01_request
    from smallapp_adapter import Refused, validate_request as spug_request
    try:
        w01_request(request); spug_request(request)
    except (Failure, Refused) as error:
        need(re.fullmatch(r"[A-Z][A-Z0-9_]+", str(error)), "CONSUMER_VALIDATOR_ERROR")
        raise Invalid(str(error)) from None
    return request


def redis_inputs(value, action, target_ref=None, scope="RUNTIME"):
    """Pure owner handoff, not native wire, an execution receipt, or a signature."""
    validate(value)
    need(action in ("FULL", "INCREMENTAL", "RESTORE", "START_APPLICATION"), "REDIS_ACTION_INVALID")
    need(scope in ("SEMANTIC", "RUNTIME"), "REDIS_PROJECTION_SCOPE_INVALID")
    need(action in ("START_APPLICATION", "RESTORE") or target_ref is None,
         "REDIS_TARGET_NOT_APPLICABLE")
    need(value["sourceConfigRef"] is not None, "SOURCE_REFERENCE_UNCONFIGURED")
    descriptor, policy, semantics, adapter = delivered_semantics(value)
    if scope == "RUNTIME":
        need(not redis_missing(value, action, target_ref), "REDIS_INPUTS_UNCONFIGURED")
    if action == "RESTORE":
        need(target_ref is not None, "REGISTERED_TARGET_REQUIRED")
    target = selected_target(value, target_ref) if target_ref is not None else None
    instance = target["redis"] if target is not None else value["source"]["redis"]
    return dict(schemaVersion="ApplicationRedisInputs/v1", schemaRevision=REVISION,
                applicationId=value["applicationId"], action=action, projectionScope=scope,
                sourceConfigRef=value["sourceConfigRef"],
                targetConfigRef=target_ref, sourceKeyspace={key: value["source"]["redis"][key]
                    for key in ("databaseIndex", "keyPrefix", "serverVersion")},
                instance=dict(instance), secretReference=dict(role=instance["secretRole"],
                    reference=instance["secretReference"], resolverOwner="W05"),
                recovery=value["redisRecovery"],
                derivedClass=dict(classification=policy["redis"]["classification"],
                    requiredForBusiness=policy["redis"]["requiredForBusiness"], executorKey=adapter["executorKey"],
                    rebuildFrom=policy["redis"]["rebuildFrom"],
                    configurationReferences=[value["redisRecovery"]["freshTarget"]["policyPin"]]),
                expiryRule=policy["redis"]["expiryRule"], restoreExpectations=semantics["restoreExpectations"],
                runtimeMissing=redis_missing(value, action, target_ref), executionReadiness="NOT_EVALUATED")


def verify_local_pins(value):
    """Verify local evidence only; native Linux members remain owner checks."""
    verified = 0
    unique = {}
    local_members = [item for item in value["source"]["assetInventory"]["applicationFilePins"]
                     if PureWindowsPath(item["path"]).is_absolute() or
                     (sys.platform != "win32" and PurePosixPath(item["path"]).is_absolute())]
    for item in [*value["evidencePins"].values(), *local_members]:
        if item["path"] in unique:
            need(item == unique[item["path"]], "LOCAL_PIN_CONFLICT")
        unique[item["path"]] = item
    for item in unique.values():
        path = Path(item["path"])
        need(path.is_file(), "LOCAL_EVIDENCE_NOT_READABLE")
        raw = path.read_bytes()
        need(len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], "LOCAL_EVIDENCE_CHANGED")
        verified += 1
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "ui-request", "redis-inputs"))
    parser.add_argument("registration")
    parser.add_argument("--require-action", choices=ACTIONS)
    parser.add_argument("--verify-local-evidence", action="store_true")
    parser.add_argument("--action", choices=("FULL", "INCREMENTAL", "RESTORE", "START_APPLICATION"))
    parser.add_argument("--operation-id")
    parser.add_argument("--projection-scope", choices=("SEMANTIC", "RUNTIME"))
    parser.add_argument("--parent-chain-ref")
    parser.add_argument("--recovery-point-ref")
    parser.add_argument("--target-config-ref")
    args = parser.parse_args()
    try:
        value = validate(load(args.registration))
        if args.mode == "ui-request":
            need(args.action is not None and args.operation_id is not None, "UI_ARGUMENTS_REQUIRED")
            print(json.dumps(ui_request(value, args.action, args.operation_id, args.parent_chain_ref,
                                         args.recovery_point_ref, args.target_config_ref), ensure_ascii=False))
            return 0
        if args.mode == "redis-inputs":
            need(args.action is not None, "REDIS_ACTION_REQUIRED")
            need(args.projection_scope is not None, "REDIS_PROJECTION_SCOPE_REQUIRED")
            print(json.dumps(redis_inputs(value, args.action, args.target_config_ref, args.projection_scope), ensure_ascii=False, indent=2))
            return 0
        result = dict(schemaVersion="ApplicationRegistrationCheck/v1", applicationId=value["applicationId"],
                      structureValid=True, executionReadiness="NOT_EVALUATED",
                      actionConfiguration={action: dict(complete=not missing(value, action, args.target_config_ref),
                          missing=missing(value, action, args.target_config_ref)) for action in ACTIONS})
        if args.verify_local_evidence:
            result["verifiedLocalEvidenceCount"] = verify_local_pins(value)
            result["nativeApplicationFilePinsNotVerified"] = sum(
                sys.platform == "win32" and PurePosixPath(item["path"]).is_absolute() and
                not PureWindowsPath(item["path"]).is_absolute()
                for item in value["source"]["assetInventory"]["applicationFilePins"])
            result["localVerificationScope"] = "Local evidence bytes only; Linux installed files and signed/native authority require original owner verification."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.require_action and missing(value, args.require_action, args.target_config_ref) else 0
    except (Invalid, ImportError) as error:
        code = str(error) if isinstance(error, Invalid) else "EXISTING_CONSUMER_UNAVAILABLE"
        print(json.dumps({"state": "REFUSED", "errorCode": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
