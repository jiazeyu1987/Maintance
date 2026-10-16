"""Bind only the two defined collector CLIs to their independently selected originals."""
import os
from pathlib import Path

from core import absolute, fields, need, pin_key, same


def collection_invocation(context, invocation_pin, stage, result_pin, verification_target_pin):
    original = context.invocation(invocation_pin, stage, [result_pin])
    argv = original["argv"]
    index = 1
    flags = set()
    while index < len(argv) and argv[index] in ("-I", "-B"):
        need(argv[index] not in flags, "COLLECTOR_ARGV_INVALID")
        flags.add(argv[index])
        index += 1
    need(index < len(argv), "COLLECTOR_ENTRY_NOT_PINNED_OR_INVOKED")
    entry = os.path.normcase(str(absolute(argv[index])))
    module = Path(__file__).resolve().parent
    legacy = os.path.normcase(str(module / "collect_recovery.py"))
    scenario = os.path.normcase(str(module / "run_ui_recovery.py"))
    if context.lab is not None and stage == "COLLECT_PLAYWRIGHT":
        need(entry == scenario, "LAB_PLAYWRIGHT_SCENARIO_REQUIRED")
    supported = {legacy} if stage == "COLLECT_DATA" else {legacy, scenario}
    need(entry in supported and entry in {pin_key(pin)[0] for pin in original["sourcePins"]},
         "COLLECTOR_ENTRY_NOT_PINNED_OR_INVOKED")
    arguments = argv[index + 1:]
    need(len(arguments) == 4 and arguments[::2] in
         (["--config", "--output"], ["--output", "--config"]), "COLLECTOR_ARGV_INVALID")
    options = dict(zip(arguments[::2], arguments[1::2]))
    need(os.path.normcase(str(absolute(options["--output"]))) == pin_key(result_pin)[0],
         "COLLECTOR_OUTPUT_UNBOUND")
    config_path = os.path.normcase(str(absolute(options["--config"])))
    selected = [pin for pin in context.trust["independentOriginalPins"] if pin_key(pin)[0] == config_path]
    need(len(selected) == 1, "COLLECTOR_CONFIG_NOT_CALLER_PINNED")
    config = context.record(selected[0])
    if entry == legacy:
        fields(config, "schemaVersion kind operationId restoreId recoveryPoint targetIdentityPin verificationTargetPin "
               "authorizationPin deadlineMilliseconds settings", "RecoveryCollectionConfig/v1")
        need(config["kind"] == ("data" if stage == "COLLECT_DATA" else "playwright"), "COLLECTOR_KIND_MISMATCH")
    else:
        fields(config, "schemaVersion runId phase operationId restoreId recoveryPoint sourceOrigin targetOrigin "
               "baseUrl apiOrigin allowedOrigins objectOrigins writeApiPaths browserExecutable passwordEnv "
               "targetIdentityPin verificationTargetPin authorizationPin deadlineMilliseconds login flows "
               "schemaPin prerequisites", "RecoveryUiScenarioConfig/v1")
        need(stage == "COLLECT_PLAYWRIGHT" and config["phase"] == "target", "COLLECTOR_TARGET_PHASE_REQUIRED")
        from run_ui_recovery import validate_endpoints
        validate_endpoints(config)
        prerequisites = config["prerequisites"]
        fields(prerequisites, "deltaObservationPin fullPointPin fullBackupResultPin incrementalPointPin "
               "incrementalBackupResultPin restorePlanPin restoreResultPin applicationStartPin")
        for key, input_key in (("restorePlanPin", "restorePlan"), ("restoreResultPin", "restoreExecutionResult"),
                               ("applicationStartPin", "applicationStartResult")):
            same(prerequisites[key], context.request["inputPins"][input_key], "COLLECTOR_RECOVERY_INPUT_MISMATCH")
        identity = context.record(verification_target_pin)
        need(config["targetOrigin"] == identity["frontendOrigin"], "COLLECTOR_FRONTEND_TARGET_MISMATCH")
    context.bind(config)
    same(config["verificationTargetPin"], verification_target_pin, "COLLECTOR_VERIFICATION_TARGET_MISMATCH")
    # Retain configuration, grants, source-stage and payload originals independently.
    from controlled_eligibility import read_original_graph
    read_original_graph(context, selected[0])
    return original
