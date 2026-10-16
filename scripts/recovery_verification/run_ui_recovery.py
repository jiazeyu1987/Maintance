"""Run one released real UI stage. Backups/restores remain original module calls.

RECOVERY_UI_TRUST_PIN must be independently selected by the calling service.
--check validates pinned prerequisites only; it never opens a browser.
"""
import argparse
import datetime as dt
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

from collect_playwright import origin
from core import (Deadline, VerificationError, absolute, fields, need, text, integer,
                  file_pin, parse, json_pin, read_pin, same, pins, pin_key, timestamp,
                  now, write_atomic, frozen_schema, validate)
from ruoyi_ui import validate_flows, validate_login, run_browser


def validate_endpoints(config):
    for key in ("sourceOrigin", "targetOrigin", "apiOrigin"):
        need(origin(config[key]) == config[key], "UI_LITERAL_ORIGIN_REQUIRED")
    need(config["sourceOrigin"] != config["targetOrigin"], "UI_SOURCE_TARGET_MUST_DIFFER")
    need(type(config["allowedOrigins"]) is list and bool(config["allowedOrigins"])
         and len(config["allowedOrigins"]) == len(set(config["allowedOrigins"])), "UI_ALLOWED_ORIGINS_REQUIRED")
    for value in config["allowedOrigins"]:
        need(origin(value) == value, "UI_LITERAL_ORIGIN_REQUIRED")
        url = urlsplit(value)
        need(not (url.hostname in ("localhost", "127.0.0.1", "::1") and url.port in (8081, 9000)),
             "UI_SHARED_LEGACY_ENDPOINT_PROHIBITED")
    selected = config["targetOrigin"] if config["phase"] == "target" else config["sourceOrigin"]
    excluded = config["sourceOrigin"] if config["phase"] == "target" else config["targetOrigin"]
    need(origin(config["baseUrl"]) == selected and selected in config["allowedOrigins"]
         and config["apiOrigin"] in config["allowedOrigins"] and excluded not in config["allowedOrigins"],
         "UI_STAGE_ENDPOINT_SCOPE")
    need(type(config["objectOrigins"]) is list and len(config["objectOrigins"]) == len(set(config["objectOrigins"]))
         and set(config["objectOrigins"]) <= set(config["allowedOrigins"])
         and not set(config["objectOrigins"]) & {selected, config["apiOrigin"]}, "UI_OBJECT_ORIGINS_REQUIRED")
    need(type(config["writeApiPaths"]) is list and len(config["writeApiPaths"]) == len(set(config["writeApiPaths"])),
         "UI_WRITE_PATHS_REQUIRED")
    allowed = {"/mes/md/product-sop/create", "/mes/md/product-sop/update", "/mes/md/product-sop/delete",
               "/infra/file/upload", "/infra/file/create", "/infra/file/delete", "/crm/follow-up-record/create"}
    for path in config["writeApiPaths"]:
        text(path)
        need(path in allowed or path.startswith("/admin-api/") and path[len("/admin-api"):] in allowed,
             "UI_BUSINESS_WRITE_PATH_PROHIBITED")
    need((not config["writeApiPaths"]) if config["phase"] == "target" else bool(config["writeApiPaths"]),
         "UI_PHASE_WRITE_SCOPE")


def prepare(config_path, trust_pin):
    need(trust_pin is not None, "UI_CALLER_TRUST_REQUIRED")
    trust = json_pin(trust_pin)
    lab_selected = trust.get("schemaVersion") == "RecoveryLabUiCallerBinding/v1"
    fields(trust, "schemaVersion callerThreadId producerThreadIds configPin authorizationPin "
           "targetIdentityPin toolPins independentOriginalPins validUntil" + (" labAdmissionPin" if lab_selected else ""),
           "RecoveryLabUiCallerBinding/v1" if lab_selected else "RecoveryUiCallerBinding/v1")
    text(trust["callerThreadId"])
    need(type(trust["producerThreadIds"]) is list and bool(trust["producerThreadIds"])
         and all(type(value) is str and bool(value) for value in trust["producerThreadIds"])
         and trust["callerThreadId"] not in trust["producerThreadIds"], "UI_CALLER_NOT_INDEPENDENT")
    config_pin = file_pin(str(absolute(config_path)))
    same(config_pin, trust["configPin"], "UI_CONFIG_NOT_CALLER_PINNED")
    config = json_pin(config_pin)
    fields(config, "schemaVersion runId phase operationId restoreId recoveryPoint sourceOrigin targetOrigin "
           "baseUrl apiOrigin allowedOrigins objectOrigins writeApiPaths browserExecutable passwordEnv "
           "targetIdentityPin verificationTargetPin authorizationPin deadlineMilliseconds login flows "
           "schemaPin prerequisites", "RecoveryUiScenarioConfig/v1")
    need(config["phase"] in ("baseline", "delta", "target"), "UI_PHASE_REQUIRED")
    for key in ("runId", "operationId", "restoreId", "recoveryPoint", "passwordEnv"):
        text(config[key])
    validate_endpoints(config)
    validate_flows(config["flows"], config["phase"])
    validate_login(config["login"])
    deadline = Deadline(config["deadlineMilliseconds"])
    same(config["authorizationPin"], trust["authorizationPin"], "UI_AUTHORIZATION_NOT_BOUND")
    same(config["targetIdentityPin"], trust["targetIdentityPin"], "UI_IDENTITY_NOT_BOUND")
    admitted = set(pins(trust["independentOriginalPins"]))
    consumed = [trust_pin, config_pin, *trust["toolPins"]]

    def record(pin):
        need(pin_key(pin) in admitted, "UI_ORIGINAL_NOT_CALLER_PINNED")
        consumed.append(pin)
        return json_pin(pin, deadline)

    if lab_selected:
        from lab_boundary import LabBoundary
        def read_original(pin, content=False):
            need(pin_key(pin) in admitted, "UI_ORIGINAL_NOT_CALLER_PINNED")
            consumed.append(pin)
            return read_pin(pin, deadline, content=content)
        boundary = LabBoundary(trust["labAdmissionPin"], trust["independentOriginalPins"], read_original,
                               record, deadline, config["operationId"], "REHEARSAL",
                               target_pin=config["targetIdentityPin"])
        boundary.reject_context_cycle(config_pin)
        consumed.append(boundary.context_pin)
        deadline.lab_guard = boundary.recheck

    authorization = record(config["authorizationPin"])
    fields(authorization, "schemaVersion runId phase operationId targetIdentityPin sourceOrigin targetOrigin "
           "tenantId username writesAllowed validFrom validUntil", "RecoveryUiAuthorization/v1")
    for key in ("runId", "phase", "operationId", "sourceOrigin", "targetOrigin"):
        need(authorization[key] == config[key], "UI_AUTHORIZATION_STAGE_MISMATCH")
    same(authorization["targetIdentityPin"], config["targetIdentityPin"], "UI_AUTHORIZATION_IDENTITY")
    need(type(authorization["tenantId"]) is int and authorization["tenantId"] == 122
         and authorization["username"] == "aoteman" and authorization["writesAllowed"] is True,
         "UI_REAL_ACTIONS_NOT_RELEASED")
    current = dt.datetime.now(dt.timezone.utc)
    end = min(timestamp(authorization["validUntil"]), timestamp(trust["validUntil"]))
    need(timestamp(authorization["validFrom"]) <= current < end, "UI_AUTHORIZATION_EXPIRED", "STALE")
    deadline.end = min(deadline.end, time.monotonic() + (end - current).total_seconds())
    record(config["targetIdentityPin"])
    identity = record(config["verificationTargetPin"])
    fields(identity, "schemaVersion targetIdentityPin targetId environment databaseId frontendOrigin objectBindingPin",
           "RecoveryVerificationTarget/v1")
    same(identity["targetIdentityPin"], config["targetIdentityPin"], "UI_ENVIRONMENT_IDENTITY_MISMATCH")
    selected = config["targetOrigin"] if config["phase"] == "target" else config["sourceOrigin"]
    need(identity["environment"] == "ISOLATED" and identity["frontendOrigin"] == selected,
         "UI_QUALIFIED_ENVIRONMENT_REQUIRED")
    tool_keys = set(pins(trust["toolPins"]))
    required = {os.path.normcase(str(path.resolve())) for path in Path(__file__).resolve().parent.glob("*.py")}
    required.update((os.path.normcase(str(Path(sys.executable).resolve())),
                     os.path.normcase(str(absolute(config["browserExecutable"])))))
    need(required <= {key[0] for key in tool_keys}, "UI_TOOL_SCOPE_INCOMPLETE")
    for flow in config["flows"]:
        for step in [*flow["entrySteps"], *flow["steps"]]:
            if step["kind"] in ("upload", "captureReference"):
                pin = step["contentPin"]
                need(pin_key(pin) in admitted, "UI_UPLOAD_NOT_CALLER_PINNED")
                need(Path(pin["path"]).name.startswith(config["runId"] + "-"), "UI_TASK_OWNED_FILENAME_REQUIRED")
                suffixes = (".doc", ".xls", ".ppt", ".txt", ".pdf") if flow["pathId"] == "baseline-download" else (".png", ".jpg", ".jpeg", ".gif")
                need(Path(pin["path"]).suffix.lower() in suffixes
                     and integer(pin["bytes"], 1) < 5 * 1024 * 1024, "UI_REAL_ATTACHMENT_INPUT_REQUIRED")
                consumed.append(pin)
    schema = frozen_schema(config["schemaPin"])
    need(pin_key(config["schemaPin"]) in admitted, "UI_SCHEMA_NOT_CALLER_PINNED")
    consumed.append(config["schemaPin"])
    prerequisites = config["prerequisites"]
    expected = {"baseline": "", "delta": "baselineObservationPin fullPointPin fullBackupResultPin",
                "target": "deltaObservationPin fullPointPin fullBackupResultPin incrementalPointPin "
                          "incrementalBackupResultPin restorePlanPin restoreResultPin applicationStartPin"}
    fields(prerequisites, expected[config["phase"]])
    source_references = []
    if config["phase"] != "baseline":
        previous_pin = prerequisites["baselineObservationPin" if config["phase"] == "delta" else "deltaObservationPin"]
        previous = record(previous_pin)
        need(previous.get("schemaVersion") == "RecoveryUiStageObservation/v1"
             and previous.get("runId") == config["runId"] and previous.get("phase") ==
             ("baseline" if config["phase"] == "delta" else "delta") and previous.get("complete") is True,
             "UI_PREVIOUS_REAL_STAGE_REQUIRED")
        need(previous.get("sourceOrigin") == config["sourceOrigin"] and previous.get("targetOrigin") == config["targetOrigin"],
             "UI_PREVIOUS_ENVIRONMENT_MISMATCH")
        previous_config = record(previous["configPin"])
        need(previous_config.get("schemaVersion") == "RecoveryUiScenarioConfig/v1"
             and previous_config.get("runId") == config["runId"], "UI_PREVIOUS_CONFIG_REQUIRED")
        source_references = previous["referenceObservations"]
        for ref in source_references:
            fields(ref, "pathId selector objectPath contentPin")
            need(pin_key(ref["contentPin"]) in admitted, "UI_SOURCE_CONTENT_NOT_CALLER_PINNED")
            consumed.append(ref["contentPin"])
        if config["phase"] == "delta":
            same(previous["targetIdentityPin"], config["targetIdentityPin"], "UI_SOURCE_IDENTITY_CHANGED")
        if config["phase"] == "target":
            baseline = record(previous_config["prerequisites"]["baselineObservationPin"])
            need(baseline.get("complete") is True and baseline.get("runId") == config["runId"]
                 and baseline.get("phase") == "baseline", "UI_BASELINE_REQUIRED")
            source_references = [*previous["referenceObservations"], *baseline["referenceObservations"]]
            for ref in source_references:
                fields(ref, "pathId selector objectPath contentPin")
                text(ref["pathId"])
                text(ref["selector"])
                text(ref["objectPath"])
                need(pin_key(ref["contentPin"]) in admitted, "UI_SOURCE_CONTENT_NOT_CALLER_PINNED")
                consumed.append(ref["contentPin"])
            for flow in config["flows"]:
                for step in [*flow["entrySteps"], *flow["steps"]]:
                    if step["kind"] == "objectReference":
                        need(sum(ref["pathId"] == step["sourcePathId"] and ref["selector"] == step["sourceSelector"]
                                 for ref in source_references) == 1, "UI_SOURCE_REFERENCE_AMBIGUOUS")
            for flow in config["flows"]:
                for step in [*flow["entrySteps"], *flow["steps"]]:
                    if step["kind"] == "download":
                        need(any(ref["pathId"] == "baseline-download" and ref["contentPin"]["bytes"] == step["expectedBytes"]
                                 and ref["contentPin"]["sha256"] == step["expectedSha256"] for ref in source_references),
                             "UI_DOWNLOAD_NOT_SOURCE_BOUND")
        point = record(prerequisites["fullPointPin"])
        validate(schema, "RepositoryPoint", point)
        need(point["pointType"] == "FULL" and point["integrityState"] == "COMPLETE"
             and point["parentPointPins"] == [], "UI_FULL_POINT_REQUIRED")

        def backup(pin, action, selected_point_pin):
            result = record(pin)
            validate(schema, "OperationResult", result)
            need(result["action"] == action and result["state"] == "SUCCEEDED"
                 and type(result["actualExitCode"]) is int and result["actualExitCode"] == 0
                 and result["failureCode"] is None, "UI_ORIGINAL_BACKUP_FAILED")
            need(timestamp(result["startedAt"]) >= timestamp(previous["finishedAt"])
                 or action == "BACKUP_FULL" and config["phase"] == "target", "UI_BACKUP_STAGE_ORDER")
            need(pin_key(selected_point_pin) in set(pins(result["originalResultPins"])), "UI_BACKUP_POINT_UNBOUND")
            for original in result["originalResultPins"]:
                need(pin_key(original) in admitted, "UI_ORIGINAL_NOT_CALLER_PINNED")
                consumed.append(original)
            return result

        backup(prerequisites["fullBackupResultPin"], "BACKUP_FULL", prerequisites["fullPointPin"])
        for key in ("manifestPin", "readbackEvidencePin", "ownerCloseEvidencePin", "originalExitEvidencePin"):
            record(point[key])
        for payload in point["payloadRefs"]:
            need(pin_key(payload) in admitted, "UI_PAYLOAD_NOT_CALLER_PINNED")
            consumed.append(payload)
        if config["phase"] == "target":
            tip = record(prerequisites["incrementalPointPin"])
            validate(schema, "RepositoryPoint", tip)
            need(tip["pointType"] == "INCREMENTAL" and tip["integrityState"] == "COMPLETE"
                 and tip["generationId"] == point["generationId"]
                 and pins(tip["parentPointPins"]) == pins([prerequisites["fullPointPin"]]), "UI_INCREMENTAL_PARENT_MISMATCH")
            need(tip["commonRecoveryPoint"] == config["recoveryPoint"], "UI_RECOVERY_POINT_MISMATCH")
            backup(prerequisites["incrementalBackupResultPin"], "BACKUP_INCREMENTAL", prerequisites["incrementalPointPin"])
            for key in ("manifestPin", "readbackEvidencePin", "ownerCloseEvidencePin", "originalExitEvidencePin"):
                record(tip[key])
            for payload in tip["payloadRefs"]:
                need(pin_key(payload) in admitted, "UI_PAYLOAD_NOT_CALLER_PINNED")
                consumed.append(payload)
            plan = record(prerequisites["restorePlanPin"])
            restored = record(prerequisites["restoreResultPin"])
            app = record(prerequisites["applicationStartPin"])
            validate(schema, "RestorePlan", plan)
            validate(schema, "RestoreExecutionResult", restored)
            validate(schema, "ApplicationStartResult", app)
            need(pins(plan["orderedChainPins"]) == pins([prerequisites["fullPointPin"], prerequisites["incrementalPointPin"]]),
                 "UI_RESTORE_CHAIN_MISMATCH")
            same(restored["planPin"], prerequisites["restorePlanPin"], "UI_RESTORE_PLAN_MISMATCH")
            same(app["restoreResultPin"], prerequisites["restoreResultPin"], "UI_APP_RESTORE_MISMATCH")
            for item in (plan, restored, app):
                need(item["operationId"] == config["operationId"] and item["restoreId"] == config["restoreId"],
                     "UI_RESTORE_OPERATION_MISMATCH")
            for item in (restored, app):
                same(item["targetIdentityPin"], config["targetIdentityPin"], "UI_RESTORE_TARGET_MISMATCH")
                need(item["state"] == "SUCCEEDED", "UI_RESTORE_OR_START_FAILED")
            need(restored["writeProtectionState"] == "ENFORCED"
                 and restored["recoveryPoint"] == config["recoveryPoint"] == plan["recoveryPoint"],
                 "UI_PROTECTED_RESTORE_REQUIRED")
            check_started_protection(app, restored, record)
    for pin in consumed:
        read_pin(pin, deadline, content=False)
    # Dependency imports and secret availability are checked before opening a browser.
    import playwright.sync_api  # noqa: F401
    from collect_data import secret_environment
    secret_environment(config["passwordEnv"])
    return config, config_pin, consumed, deadline, source_references


def check_started_protection(app, restored, record):
    from application_protection import SCOPES
    side = record(app["sideEffectIsolationPin"])
    same(side["targetIdentityPin"], app["targetIdentityPin"], "UI_POST_START_TARGET_MISMATCH")
    policy_pin = side["applicationWriteProtectionPolicyPin"]
    policy = record(policy_pin)
    need(policy.get("schemaVersion") == "RecoveryApplicationWriteProtectionPolicy/v1", "UI_START_PROTECTION_POLICY_REQUIRED")
    same(policy["targetIdentityPin"], app["targetIdentityPin"], "UI_START_PROTECTION_TARGET_MISMATCH")
    same(policy["configurationPin"], app["configurationPin"], "UI_START_PROTECTION_VERSION_MISMATCH")
    need(policy["imagePins"] == app["imagePins"], "UI_START_PROTECTION_IMAGE_MISMATCH")
    original_keys = set(pins(app["originalStartResultPins"]))
    for phase, key in (("BEFORE_START", "writeProtectionBeforePin"), ("AFTER_START", "writeProtectionAfterPin")):
        proof = record(side[key])
        need(proof.get("schemaVersion") == "RecoveryApplicationWriteProtectionObservation/v1"
             and proof["phase"] == phase and proof["state"] == "ENFORCED"
             and proof["operationId"] == app["operationId"] and proof["restoreId"] == app["restoreId"]
             and proof["recoveryPoint"] == restored["recoveryPoint"], "UI_START_PROTECTION_NOT_PROVED")
        same(proof["targetIdentityPin"], app["targetIdentityPin"], "UI_START_PROTECTION_TARGET_MISMATCH")
        same(proof["policyPin"], policy_pin, "UI_START_PROTECTION_POLICY_MISMATCH")
        need(pin_key(proof["originalInvocationPin"]) in original_keys, "UI_START_PROTECTION_ORIGINAL_REQUIRED")
        invocation = record(proof["originalInvocationPin"])
        need(invocation.get("schemaVersion") == "RecoveryEnvironmentInvocation/v1"
             and invocation["state"] == "SUCCEEDED" and type(invocation["actualExitCode"]) is int
             and invocation["actualExitCode"] == 0 and type(invocation["pid"]) is int and invocation["pid"] > 0,
             "UI_START_PROTECTION_PROCESS_UNCONFIRMED", "UNKNOWN")
        need(timestamp(invocation["startedAt"]) <= timestamp(proof["observedAt"]) <= timestamp(invocation["finishedAt"]),
             "UI_START_PROTECTION_TIME_MISMATCH")
        need({item["scope"] for item in proof["scopeObservations"]} == SCOPES
             and len(proof["scopeObservations"]) == len(SCOPES), "UI_START_PROTECTION_SCOPES_MISSING")
        for item in proof["scopeObservations"]:
            need(item["beforeFingerprint"] == item["afterFingerprint"] and bool(item["rejectionObservationPins"]),
                 "UI_START_PROTECTION_REFUSAL_REQUIRED")
            for pin in item["rejectionObservationPins"]:
                refusal = record(pin)
                need(refusal.get("schemaVersion") == "RecoveryApplicationWriteRefusal/v1"
                     and refusal["phase"] == phase and refusal["scope"] == item["scope"]
                     and refusal["operationId"] == app["operationId"]
                     and refusal["recoveryPoint"] == restored["recoveryPoint"]
                     and refusal["containers"] == proof["containers"]
                     and refusal["denied"] is True and bool(refusal["originalInvocationPins"])
                     and refusal["beforeFingerprint"] == refusal["afterFingerprint"] == item["beforeFingerprint"],
                     "UI_START_ACTUAL_REFUSAL_REQUIRED")
                same(refusal["targetIdentityPin"], app["targetIdentityPin"], "UI_REFUSAL_TARGET_MISMATCH")
                for original in refusal["originalInvocationPins"]:
                    call = record(original)
                    need(call.get("schemaVersion") == "RecoveryEnvironmentInvocation/v1"
                         and call["state"] in ("SUCCEEDED", "FAILED_RETAINED")
                         and type(call["actualExitCode"]) is int and type(call["pid"]) is int and call["pid"] > 0,
                         "UI_REFUSAL_PROCESS_UNCONFIRMED", "UNKNOWN")
                    need(timestamp(invocation["startedAt"]) <= timestamp(call["startedAt"])
                         <= timestamp(call["finishedAt"]) <= timestamp(invocation["finishedAt"]),
                         "UI_REFUSAL_TIME_MISMATCH")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        need(args.check or args.output is not None, "UI_NEW_OUTPUT_REQUIRED")
        raw = os.environ.get("RECOVERY_UI_TRUST_PIN")
        trust_pin = parse(raw.encode("utf-8")) if raw is not None else None
        config, config_pin, consumed, deadline, source_references = prepare(args.config, trust_pin)
        if args.check:
            print("UI_CONFIG_CHECKED_ONLY_BROWSER_NOT_RUN")
            return 0
        output = absolute(args.output)
        root = Path(str(output) + ".artifacts")
        need(output.parent.is_dir() and not output.exists() and not root.exists(), "UI_OUTPUT_MUST_BE_NEW")
        root.mkdir()
        started = now()
        try:
            data, references = run_browser(config, root, deadline, source_references)
            if hasattr(deadline, "lab_guard"):
                deadline.lab_guard()
            for pin in consumed:
                read_pin(pin, deadline, content=False)
            if config["phase"] == "target":
                result = {"schemaVersion": "RecoveryObservation/v1", "kind": "playwright",
                          "operationId": config["operationId"], "restoreId": config["restoreId"],
                          "targetIdentityPin": config["targetIdentityPin"], "recoveryPoint": config["recoveryPoint"],
                          "startedAt": started, "finishedAt": now(), "complete": True, "data": data}
            else:
                result = {"schemaVersion": "RecoveryUiStageObservation/v1", "runId": config["runId"],
                          "phase": config["phase"], "sourceOrigin": config["sourceOrigin"],
                          "targetOrigin": config["targetOrigin"], "configPin": config_pin,
                          "targetIdentityPin": config["targetIdentityPin"], "startedAt": started,
                          "finishedAt": now(), "complete": True, "data": data,
                          "referenceObservations": references}
            write_atomic(output, result)
            return 0
        except Exception as error:
            code = error.code if isinstance(error, VerificationError) else "UI_" + type(error).__name__.upper()
            write_atomic(output, {"schemaVersion": "RecoveryUiStageFailure/v1", "runId": config["runId"],
                                  "phase": config["phase"], "startedAt": started, "finishedAt": now(),
                                  "complete": False, "failureCode": code})
            raise
    except VerificationError as error:
        print(error.code, file=sys.stderr)
        return 2 if error.verdict == "UNKNOWN" else 1
    except Exception as error:
        print("UI_" + type(error).__name__.upper(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
