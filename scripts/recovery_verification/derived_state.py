"""Independent business-required derived-state collection and exact comparison."""
import os
import subprocess

from core import (canonical, digest, fields, integer, json_pin, need, parse, pin_key, pins,
                  read_pin, same, sha)
from service_identity import probe_service, verify_service_observation


def required_classes(inventory):
    need(inventory["schemaVersion"] == "RecoveryDerivedInventory/v1" and inventory["complete"] is True and
         set(inventory["classes"]) == {"redis", "queue"}, "DERIVED_CLASSIFICATION_REQUIRED")
    required = set()
    for name, item in inventory["classes"].items():
        need(type(item["requiredForBusiness"]) is bool and
             item["classification"] in ("RESTORE", "REBUILD", "NOT_PRESENT"), "DERIVED_CLASSIFICATION_INVALID")
        if item["requiredForBusiness"]:
            need(item["classification"] != "NOT_PRESENT", "REQUIRED_DERIVED_DATA_CANNOT_BE_ABSENT")
            required.add(name)
    return required


def collect_derived(inventory_pin, observers, identity, deadline):
    inventory = json_pin(inventory_pin, deadline)
    required = required_classes(inventory)
    need(type(observers) is list and len(observers) == len(required) and
         {item["className"] for item in observers} == required, "DERIVED_OBSERVER_COVERAGE_REQUIRED")
    result = []
    for observer in observers:
        fields(observer, "className bindingPin pythonPin scriptPin sourcePins settingsPin secretEnvRefs")
        source_keys = set(pins(observer["sourcePins"]))
        need({pin_key(observer["pythonPin"]), pin_key(observer["scriptPin"])} <= source_keys,
             "DERIVED_OBSERVER_SOURCE_SCOPE_REQUIRED")
        for pin in observer["sourcePins"]:
            read_pin(pin, deadline, content=False)
        settings = json_pin(observer["settingsPin"], deadline)
        binding = json_pin(observer["bindingPin"], deadline)
        same(binding["targetIdentityPin"], identity["targetIdentityPin"], "DERIVED_TARGET_MISMATCH")
        need(binding["role"] == observer["className"], "DERIVED_SERVICE_ROLE_MISMATCH")
        from native_observe import collect_service
        from collect_data import secret_environment
        need(type(observer["secretEnvRefs"]) is list and
             len(set(observer["secretEnvRefs"])) == len(observer["secretEnvRefs"]), "DERIVED_SECRET_REFERENCES_INVALID")
        environment = {name: secret_environment(name) for name in observer["secretEnvRefs"]}
        def execute(before):
            request = {"schemaVersion": "RecoveryDerivedObservationRequest/v1", "className": observer["className"],
                       "targetIdentityPin": identity["targetIdentityPin"], "operationId": before["operationId"],
                       "recoveryPoint": inventory["recoveryPoint"], "serviceObservation": before,
                       "settings": settings, "writesAllowed": False, "deadlineMilliseconds": max(1, int(deadline.remaining()*1000))}
            try:
                return subprocess.run([observer["pythonPin"]["path"], observer["scriptPin"]["path"]],
                                      input=canonical(request), capture_output=True,
                                      timeout=deadline.remaining(), env=environment, check=False)
            except subprocess.TimeoutExpired:
                need(False, "DERIVED_OBSERVATION_EXIT_UNKNOWN", "UNKNOWN")
        process, after = collect_service(observer["bindingPin"], deadline, execute)
        need(process.returncode == 0 and not process.stderr, "DERIVED_OBSERVER_FAILED")
        need(len(process.stdout) <= 16 * 1024 * 1024, "DERIVED_OBSERVER_OUTPUT_LIMIT")
        observed = parse(process.stdout)
        fields(observed, "schemaVersion className operationId targetIdentityPin recoveryPoint complete "
               "recordCount stateSha256 writesPerformed", "RecoveryDerivedState/v1")
        same(observed["targetIdentityPin"], identity["targetIdentityPin"], "DERIVED_TARGET_MISMATCH")
        actual_service = after['after']['observation'] if binding['schemaVersion']=='RecoveryServiceBinding/v2' else after
        need(observed["className"] == observer["className"] and observed["operationId"] == actual_service["operationId"] and
             observed["recoveryPoint"] == inventory["recoveryPoint"] and observed["complete"] is True and
             observed["writesPerformed"] is False, "DERIVED_OBSERVER_RESULT_INVALID")
        integer(observed["recordCount"])
        sha(observed["stateSha256"])
        for pin in observer["sourcePins"]:
            read_pin(pin, deadline, content=False)
        result.append({"className": observer["className"], "recordCount": observed["recordCount"],
                       "stateSha256": observed["stateSha256"], "service": after,
                       "observerSourcePins": observer["sourcePins"], "observerSettingsPin": observer["settingsPin"],
                       "actualExitCode": process.returncode, "outputSha256": digest(process.stdout)})
    return result


def verify_derived(context, baseline_pin, data):
    inventory = context.derived_inventory
    required = required_classes(inventory)
    need(inventory["recoveryPoint"] == context.plan["recoveryPoint"], "DERIVED_RECOVERY_POINT_MISMATCH")
    same(data["derivedInventoryPin"], context.derived_inventory_pin, "DERIVED_INVENTORY_MISMATCH")
    observations = data["derived"]
    need(type(observations) is list and len(observations) == len(required) and
         {item["className"] for item in observations} == required, "DERIVED_OBSERVATION_COVERAGE_REQUIRED")
    if not required:
        need(baseline_pin is None, "UNEXPECTED_DERIVED_BASELINE")
        return
    need(baseline_pin is not None, "DERIVED_INDEPENDENT_BASELINE_REQUIRED")
    baseline = context.record(baseline_pin)
    fields(baseline, "schemaVersion recoveryPoint inventoryPin states", "RecoveryDerivedBaseline/v1")
    same(baseline["inventoryPin"], context.derived_inventory_pin, "DERIVED_BASELINE_INVENTORY_MISMATCH")
    need(baseline["recoveryPoint"] == context.plan["recoveryPoint"] and type(baseline["states"]) is list and
         len(baseline["states"]) == len(required) and {item["className"] for item in baseline["states"]} == required,
         "DERIVED_BASELINE_COVERAGE_REQUIRED")
    expected = {}
    for item in baseline["states"]:
        fields(item, "className recordCount stateSha256")
        integer(item["recordCount"])
        sha(item["stateSha256"])
        expected[item["className"]] = (item["recordCount"], item["stateSha256"])
    for item in observations:
        fields(item, "className recordCount stateSha256 service observerSourcePins observerSettingsPin actualExitCode outputSha256")
        name = item["className"]
        need(type(item["actualExitCode"]) is int and item["actualExitCode"] == 0, "DERIVED_OBSERVER_EXIT_INVALID", "UNKNOWN")
        integer(item["recordCount"])
        sha(item["stateSha256"])
        sha(item["outputSha256"])
        need(set(pins(item["observerSourcePins"])) <= context.source_keys, "DERIVED_OBSERVER_NOT_INDEPENDENTLY_PINNED")
        for pin in item["observerSourcePins"]:
            context.read(pin)
        context.read(item["observerSettingsPin"])
        verify_service_observation(context, item["service"], item["service"]["bindingPin"], name)
        need((item["recordCount"], item["stateSha256"]) == expected[name], "DERIVED_BUSINESS_STATE_MISMATCH", "FAILED")
