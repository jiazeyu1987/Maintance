"""Explicitly authorized evidence collection. Never runs as part of verification.

RECOVERY_VERIFICATION_COLLECTION_TRUST_PIN is selected by the trusted caller.
No default target, credentials, endpoint, database, browser, or page selectors exist.
"""
import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from core import (Deadline, VerificationError, absolute, fields, need, parse, json_pin, raw_file,
                  digest, same, timestamp, now, write_atomic, read_pin, pins)
from collect_data import collect_data
from collect_playwright import collect_playwright


def collect(config_path, output_path, trust_pin):
    need(trust_pin is not None, "COLLECTION_CALLER_TRUST_REQUIRED")
    trust = json_pin(trust_pin)
    lab_selected = trust.get("schemaVersion") == "RecoveryLabCollectionCallerBinding/v1"
    fields(trust, "schemaVersion callerThreadId producerThreadIds configPin authorizationPin "
           "targetIdentityPin toolPins validUntil" + (" independentOriginalPins labAdmissionPin" if lab_selected else ""),
           "RecoveryLabCollectionCallerBinding/v1" if lab_selected else "RecoveryCollectionCallerBinding/v1")
    need(type(trust["callerThreadId"]) is str and trust["callerThreadId"] and
         type(trust["producerThreadIds"]) is list and trust["producerThreadIds"] and
         trust["callerThreadId"] not in trust["producerThreadIds"], "COLLECTION_CALLER_NOT_INDEPENDENT")
    need(timestamp(trust["validUntil"]) > dt.datetime.now(dt.timezone.utc), "COLLECTION_BINDING_EXPIRED", "STALE")
    raw = raw_file(str(absolute(config_path)))
    current_pin = {"path": str(absolute(config_path)), "bytes": len(raw), "sha256": digest(raw)}
    same(current_pin, trust["configPin"], "COLLECTION_CONFIG_NOT_CALLER_PINNED")
    config = parse(raw)
    fields(config, "schemaVersion kind operationId restoreId recoveryPoint targetIdentityPin verificationTargetPin "
           "authorizationPin deadlineMilliseconds settings", "RecoveryCollectionConfig/v1")
    need(config["kind"] in ("data", "playwright"), "UNSUPPORTED_COLLECTION_KIND")
    need(not (lab_selected and config["kind"] == "playwright"), "LAB_PLAYWRIGHT_SCENARIO_REQUIRED")
    deadline = Deadline(config["deadlineMilliseconds"])
    boundary = None
    if lab_selected:
        from lab_boundary import LabBoundary
        boundary = LabBoundary(trust["labAdmissionPin"], trust["independentOriginalPins"],
                               lambda pin, content=False: read_pin(pin, deadline, content=content),
                               lambda pin: json_pin(pin, deadline), deadline, config["operationId"],
                               "REHEARSAL", target_pin=config["targetIdentityPin"])
        boundary.reject_context_cycle(current_pin)
    same(config["authorizationPin"], trust["authorizationPin"], "COLLECTION_AUTHORIZATION_UNBOUND")
    same(config["targetIdentityPin"], trust["targetIdentityPin"], "COLLECTION_TARGET_UNBOUND")
    read_pin(config["targetIdentityPin"])
    identity = json_pin(config["verificationTargetPin"])
    fields(identity, "schemaVersion targetIdentityPin targetId environment databaseId frontendOrigin objectBindingPin", "RecoveryVerificationTarget/v1")
    same(identity["targetIdentityPin"], config["targetIdentityPin"], "COLLECTION_VERIFICATION_TARGET_MISMATCH")
    need(identity["environment"] == "ISOLATED", "COLLECTION_ISOLATED_TARGET_REQUIRED")
    authorization = json_pin(config["authorizationPin"])
    fields(authorization, "schemaVersion operationId action targetIdentityPin validFrom validUntil "
           "tenantId writesAllowed", "RecoveryVerificationAuthorization/v1")
    same(authorization["targetIdentityPin"], config["targetIdentityPin"], "COLLECTION_AUTHORIZATION_TARGET")
    need(authorization["operationId"] == config["operationId"] and authorization["action"] == "VERIFY_RECOVERY",
         "COLLECTION_AUTHORIZATION_ACTION")
    need(type(authorization["tenantId"]) is int and authorization["tenantId"] == 122
         and type(authorization["writesAllowed"]) is bool, "COLLECTION_PROTECTED_TENANT")
    if config["kind"] == "playwright":
        need(authorization["writesAllowed"] is True, "REAL_BROWSER_ACTIONS_NOT_AUTHORIZED")
    observed = dt.datetime.now(dt.timezone.utc)
    need(timestamp(authorization["validFrom"]) <= observed < timestamp(authorization["validUntil"]),
         "COLLECTION_AUTHORIZATION_EXPIRED", "STALE")
    # Shorten the single monotonic budget to the approved window before contacting any service.
    deadline.end = min(deadline.end, __import__("time").monotonic() +
                       (min(timestamp(authorization["validUntil"]), timestamp(trust["validUntil"])) - observed).total_seconds())
    pins(trust["toolPins"])
    required_sources = {str(path.resolve()).lower() if os.name == "nt" else str(path.resolve())
                        for path in Path(__file__).resolve().parent.glob("*.py")}
    required_sources.add(os.path.normcase(str(Path(sys.executable).resolve())))
    if config["kind"] == "playwright":
        required_sources.add(os.path.normcase(str(absolute(config["settings"]["browserExecutable"]))))
    from core import pin_key
    need(required_sources <= {pin_key(pin)[0] for pin in trust["toolPins"]}, "COLLECTOR_TOOL_SCOPE_INCOMPLETE")
    if config["kind"] == "data":
        for observer in config["settings"]["derivedObservers"]:
            need(set(pins(observer["sourcePins"])) <= set(pins(trust["toolPins"])),
                 "DERIVED_OBSERVER_NOT_CALLER_PINNED")
    for pin in trust["toolPins"]:
        deadline.remaining()
        read_pin(pin, deadline, content=False)
    if boundary is not None and config["kind"] == "data":
        object_binding = boundary.original(identity["objectBindingPin"])
        if object_binding.get("schemaVersion") == "RecoveryServiceBinding/v2" or any(
                boundary.original(observer["bindingPin"]).get("schemaVersion") == "RecoveryServiceBinding/v2"
                for observer in config["settings"]["derivedObservers"]):
            # Selection comes only from the explicit lab binding and guarded current request.
            current_request = boundary.original(boundary.context["operationRequestPin"])
            plan = boundary.original(current_request["inputPins"]["restorePlan"])
            same(plan["targetRef"], current_request["sourceOrTargetRef"], "COLLECTION_NATIVE_PLAN_TARGET")
            need(plan["operationId"] == config["operationId"] and plan["restoreId"] == config["restoreId"] and
                 plan["recoveryPoint"] == config["recoveryPoint"], "COLLECTION_NATIVE_CURRENT_RESTORE")
            target_config = boundary.original(current_request["sourceOrTargetRef"])
            same(target_config["targetIdentityPin"], config["targetIdentityPin"], "COLLECTION_NATIVE_CURRENT_TARGET")
            policy = boundary.original(current_request["policyPin"])
            from core import integer
            deadline.native_service_context = dict(boundary=boundary, sourcePins=trust["toolPins"],
                maximumAgeMilliseconds=integer(policy["maxAgeMilliseconds"], 1),
                expected=dict(operationId=config["operationId"], restoreId=config["restoreId"],
                    recoveryPoint=config["recoveryPoint"], targetIdentityPin=config["targetIdentityPin"],
                    sourceScopePin=target_config["sourceScopePin"], environmentConfigPin=current_request["sourceOrTargetRef"],
                    applicationStartPin=current_request["inputPins"]["applicationStartResult"]))
            from native_observe import NativeObservationClient
            configured_launch = os.environ.get("RECOVERY_VERIFICATION_NATIVE_LAUNCH_PIN")
            need(configured_launch is not None, "COLLECTION_NATIVE_LAUNCH_SELECTION_REQUIRED")
            launch_pin = parse(configured_launch.encode("utf-8"))
            deadline.native_service_context["client"] = NativeObservationClient(boundary, launch_pin,
                deadline.native_service_context["expected"], trust["toolPins"], policy["maxAgeMilliseconds"])
    if boundary is not None:
        boundary.recheck()
    output = absolute(output_path)
    need(output.parent.is_dir() and not output.exists(), "COLLECTION_OUTPUT_MUST_BE_NEW")
    # Playwright artifact root is a new operation-owned directory, never a shared browser profile.
    evidence_root = Path(str(output) + ".artifacts")
    started = now()
    try:
        if config["kind"] == "data":
            data = collect_data(config["settings"], identity, deadline)
        else:
            need(not evidence_root.exists(), "COLLECTION_ARTIFACT_DIRECTORY_EXISTS")
            evidence_root.mkdir()
            data = collect_playwright(config["settings"], identity, str(evidence_root), deadline)
        deadline.remaining()
        if boundary is not None:
            boundary.recheck()
        for pin in [trust_pin, current_pin, config["authorizationPin"], config["targetIdentityPin"], config["verificationTargetPin"], *trust["toolPins"]]:
            deadline.remaining()
            read_pin(pin, deadline, content=False)
        record = {"schemaVersion": "RecoveryObservation/v1", "kind": config["kind"],
                  "operationId": config["operationId"], "restoreId": config["restoreId"],
                  "targetIdentityPin": config["targetIdentityPin"], "recoveryPoint": config["recoveryPoint"],
                  "startedAt": started, "finishedAt": now(), "complete": True, "data": data}
        write_atomic(output, record)
        return 0
    except Exception as error:
        # A failure is retained explicitly. No raw driver/browser message is persisted: these
        # can contain passwords, connection URLs, rendered secrets, or private business rows.
        failure = error.code if isinstance(error, VerificationError) else "COLLECTION_" + type(error).__name__.upper()
        write_atomic(output, {"schemaVersion": "RecoveryCollectionFailure/v1", "operationId": config["operationId"],
                              "kind": config["kind"], "startedAt": started, "finishedAt": now(), "complete": False,
                              "failureCode": failure, "actualExitCode": None})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        raw = os.environ.get("RECOVERY_VERIFICATION_COLLECTION_TRUST_PIN")
        trust = parse(raw.encode("utf-8")) if raw is not None else None
        return collect(args.config, args.output, trust)
    except VerificationError as error:
        print(error.code, file=sys.stderr)
        return 2 if error.verdict == "UNKNOWN" else 1
    except Exception as error:
        print("COLLECTION_" + type(error).__name__.upper(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
