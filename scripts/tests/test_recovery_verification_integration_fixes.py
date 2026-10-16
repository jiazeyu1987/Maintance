"""Focused integration-contract regressions; generated packets are engineering only."""
import copy
from pathlib import Path
import sys

import pytest

from test_recovery_verification_report import Packet, MODULE
from core import Deadline, VerificationError, canonical, digest, file_pin, json_pin, read_pin, write_atomic
from bind_caller import bind
from evidence import EvidenceContext, admit_restore
from verify_recovery import policy_record
from collection_originals import collection_invocation
from controlled_eligibility import verify_controlled_eligibility


def current_context(packet, request, name="current", omit_original=None):
    """Engineering-only caller selection; never a real invocation or approval."""
    request_pin = packet.put(name + "-request", request)
    prior = json_pin(packet.all_pins["trust"])
    trace = json_pin(prior["runTracePin"])
    trace["operationId"] = request["operationId"]
    trace_pin = packet.put(name + "-trace", trace)
    originals = [pin for key, pin in packet.all_pins.items() if key != omit_original]
    originals.append(prior["schemaPin"])
    binding = dict(prior, requestPin=request_pin, runTracePin=trace_pin, independentOriginalPins=originals)
    binding_pin = packet.put(name + "-binding", binding)
    context = EvidenceContext(request, request_pin, binding_pin, Deadline(20000))
    context.plan = json_pin(request["inputPins"]["restorePlan"])
    context.target_pin = packet.target
    return context


def controlled_case(tmp_path, eligibility_change=None, approval_change=None, report_change=None,
                    policy_change=None, omit_original=None, bad_signature=False):
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    packet = Packet(tmp_path)
    packet.change("point", lambda point: point.update(blockedReason="REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED"))
    process, result = packet.run()
    assert process.returncode == 0, result
    report = copy.deepcopy(result["data"])
    if report_change:
        report_change(report, packet)
    report_pin = packet.put("prior-report", report)
    private_key = Ed25519PrivateKey.generate()  # Ephemeral fixture key; never saved.
    public_key = packet.blob("repository-key", private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    approval = {"schemaVersion": "RepositoryRecoveryApproval/v1", "repositoryId": "engineering-repository",
                "reportPin": report_pin, "targetIdentityPin": packet.target,
                "sourceIdentityPin": json_pin(packet.source_scope)["sourceIdentityPin"], "validUntil": packet.time(3600)}
    if approval_change:
        approval_change(approval, packet)
    signature = base64.b64encode(private_key.sign(canonical(approval))).decode("ascii")
    if bad_signature:
        signature = base64.b64encode(b"invalid signature").decode("ascii")
    approval_pin = packet.put("repository-approval", {"schemaVersion": "RepositorySignedRecord/v1",
                    "keySha256": public_key["sha256"], "payload": approval, "signature": signature})
    plan = dict(json_pin(packet.request["inputPins"]["restorePlan"]), operationId="controlled-op",
                restoreId="controlled-restore", mode="CONTROLLED_RESTORE")
    plan_pin = packet.put("controlled-plan", plan)
    eligibility = {"schemaVersion": "RecoveryControlledEligibility/v1", "repositoryId": "engineering-repository",
                   "sourceScopePin": packet.source_scope, "targetIdentityPin": packet.target,
                   "candidatePin": plan["candidatePin"], "orderedChainPins": plan["orderedChainPins"],
                   "recoveryPoint": plan["recoveryPoint"], "reportPin": report_pin, "approvalPin": approval_pin,
                   "repositoryEvidenceKeyPins": [public_key], "validUntil": packet.time(3600)}
    if eligibility_change:
        eligibility_change(eligibility, packet)
    eligibility_pin = packet.put("controlled-eligibility", eligibility)
    policy = dict(json_pin(packet.request["policyPin"]), controlledEligibilityPin=eligibility_pin)
    if policy_change:
        policy_change(policy, packet)
    policy_pin = packet.put("controlled-policy", policy)
    request = dict(packet.request, operationId="controlled-op", requestId="controlled-request", mode="CONTROLLED_RESTORE",
                   policyPin=policy_pin, inputPins=dict(packet.request["inputPins"], restorePlan=plan_pin))
    context = current_context(packet, request, omit_original=omit_original)
    return packet, context, policy


def test_controlled_gate_rebuilds_signed_current_report_without_rewriting_point(tmp_path):
    packet, context, policy = controlled_case(tmp_path)
    original_point = Path(packet.all_pins["point"]["path"]).read_bytes()
    assert policy_record(context) == policy
    assert verify_controlled_eligibility(context, policy)["reportPin"] == packet.all_pins["prior-report"]
    assert Path(packet.all_pins["point"]["path"]).read_bytes() == original_point
    assert json_pin(packet.all_pins["point"])["controlledRestoreEligible"] is False
    # Reaches the later native-result binding gate. The prior REHEARSAL's restore
    # is intentionally not a new controlled restore; no controlled PASS is fabricated.
    with pytest.raises(VerificationError, match="OPERATION_RESTORE_MISMATCH"):
        admit_restore(context, policy["recoveryTargetPin"], policy)


@pytest.mark.parametrize("change,code", [
    (lambda value, p: value.update(repositoryId="other"), "CONTROLLED_APPROVAL_REPOSITORY_MISMATCH"),
    (lambda value, p: value.update(reportPin=p.target), "CONTROLLED_APPROVAL_REPORT_MISMATCH"),
    (lambda value, p: value.update(targetIdentityPin=p.image), "CONTROLLED_APPROVAL_TARGET_MISMATCH"),
    (lambda value, p: value.update(sourceIdentityPin=p.target), "CONTROLLED_APPROVAL_SOURCE_MISMATCH"),
    (lambda value, p: value.update(validUntil=p.time(0)), "CONTROLLED_APPROVAL_EXPIRED"),
])
def test_controlled_signed_payload_binding_rejections(tmp_path, change, code):
    _, context, policy = controlled_case(tmp_path, approval_change=change)
    with pytest.raises(VerificationError, match=code):
        verify_controlled_eligibility(context, policy)


@pytest.mark.parametrize("change,code", [
    (lambda value, p: value.update(sourceScopePin=p.target), "CONTROLLED_SOURCE_SCOPE_MISMATCH"),
    (lambda value, p: value.update(targetIdentityPin=p.image), "CONTROLLED_TARGET_MISMATCH"),
    (lambda value, p: value.update(candidatePin=p.target), "CONTROLLED_CANDIDATE_MISMATCH"),
    (lambda value, p: value.update(orderedChainPins=[p.target]), "CONTROLLED_CHAIN_MISMATCH"),
    (lambda value, p: value.update(recoveryPoint="other-point"), "CONTROLLED_POINT_MISMATCH"),
    (lambda value, p: value.update(validUntil=p.time(0)), "CONTROLLED_ELIGIBILITY_EXPIRED"),
    (lambda value, p: value.update(repositoryEvidenceKeyPins=[p.tool]), "CONTROLLED_APPROVAL_KEY_NOT_SELECTED"),
])
def test_controlled_eligibility_exact_bindings(tmp_path, change, code):
    _, context, policy = controlled_case(tmp_path, eligibility_change=change)
    with pytest.raises(VerificationError, match=code):
        verify_controlled_eligibility(context, policy)


@pytest.mark.parametrize("verdict,invalidations", [("FAILED", []), ("UNKNOWN", []), ("STALE", ["changed"]),
                                                   ("PASSED", ["changed"])])
def test_controlled_refuses_failed_unknown_or_invalidated_report(tmp_path, verdict, invalidations):
    _, context, policy = controlled_case(tmp_path, report_change=lambda r, _: r.update(verdict=verdict, invalidatedBy=invalidations))
    with pytest.raises(VerificationError, match="CONTROLLED_REPORT_NOT_CURRENT_PASSED"):
        verify_controlled_eligibility(context, policy)


@pytest.mark.parametrize("original,code", [
    ("controlled-policy", "ORIGINAL_NOT_CALLER_PINNED"),
    ("controlled-eligibility", "ORIGINAL_NOT_CALLER_PINNED"),
    ("prior-report", "CONTROLLED_ORIGINAL_NOT_INDEPENDENTLY_SELECTED"),
    ("repository-approval", "CONTROLLED_ORIGINAL_NOT_INDEPENDENTLY_SELECTED"),
    ("repository-key", "CONTROLLED_ORIGINAL_NOT_INDEPENDENTLY_SELECTED"),
    ("download", "ORIGINAL_NOT_CALLER_PINNED"),
])
def test_controlled_current_caller_must_admit_originals(tmp_path, original, code):
    _, context, policy = controlled_case(tmp_path, omit_original=original)
    with pytest.raises(VerificationError, match=code):
        selected_policy = policy_record(context)
        verify_controlled_eligibility(context, selected_policy)


def test_controlled_bad_signature_is_refused(tmp_path):
    _, context, policy = controlled_case(tmp_path, bad_signature=True)
    with pytest.raises(VerificationError, match="CONTROLLED_APPROVAL_SIGNATURE_INVALID"):
        verify_controlled_eligibility(context, policy)


@pytest.mark.parametrize("change,code", [
    (lambda value, _: value.update(controlledEligibilityPin=None), "CONTROLLED_ELIGIBILITY_REQUIRED"),
    (lambda value, _: value.update(maxAgeMilliseconds=1), "CONTROLLED_REPORT_EXPIRED"),
    (lambda value, _: value.update(rtoObjectiveMilliseconds=1), "CONTROLLED_REPORT_TIMING_NOT_PASSED"),
])
def test_controlled_current_policy_is_enforced(tmp_path, change, code):
    _, context, policy = controlled_case(tmp_path, policy_change=change)
    with pytest.raises(VerificationError, match=code):
        selected_policy = policy_record(context)
        verify_controlled_eligibility(context, selected_policy)


def test_controlled_passed_label_cannot_replace_substantive_original_report(tmp_path):
    _, context, policy = controlled_case(tmp_path, report_change=lambda r, _: r["rtoObservation"].update(observedMilliseconds=1))
    with pytest.raises(VerificationError, match="CONTROLLED_REPORT_ORIGINAL_VERIFICATION_MISMATCH"):
        verify_controlled_eligibility(context, policy)


@pytest.mark.parametrize("version,eligibility,code", [("RecoveryVerificationPolicy/v1", None, "RECORD_VERSION"),
                                                     ("RecoveryVerificationPolicy/v2", "target", "REHEARSAL_CONTROLLED_ELIGIBILITY_PROHIBITED")])
def test_policy_has_no_v1_fallback_or_rehearsal_eligibility(tmp_path, version, eligibility, code):
    packet = Packet(tmp_path)
    packet.change("policy", lambda value: value.update(schemaVersion=version,
                   controlledEligibilityPin=None if eligibility is None else packet.target))
    process, result = packet.run()
    assert process.returncode == 1 and result["failureCode"] == code, result


def ui_collection_case(tmp_path, entry="run_ui_recovery.py", argv_change=None, config_change=None, omit_original=None):
    packet = Packet(tmp_path)
    process, result = packet.run()
    assert process.returncode == 0, result
    policy = json_pin(packet.request["policyPin"])
    packet.browser = policy["playwrightObservationPin"]
    packet.verification_target = policy["verificationTargetPin"]
    packet.point = packet.request["selectedPointPin"]
    packet.plan = packet.request["inputPins"]["restorePlan"]
    packet.restore = packet.request["inputPins"]["restoreExecutionResult"]
    packet.app = packet.request["inputPins"]["applicationStartResult"]
    packet.approval = packet.request["authorizationRefs"][0]
    prior_stage = packet.put("source-stage-engineering", {"schemaVersion": "RecoveryUiStageObservation/v1",
                 "runId": "engineering-only", "phase": "delta", "complete": True,
                 "referenceObservations": [{"pathId": "add", "selector": "#engineering",
                    "objectPath": "files/a.txt", "contentPin": packet.all_pins["download"]}]})
    schema_pin = json_pin(packet.all_pins["trust"])["schemaPin"]
    config = {"schemaVersion": "RecoveryUiScenarioConfig/v1", "runId": "engineering-only", "phase": "target",
              "operationId": "op1", "restoreId": "restore1", "recoveryPoint": "point-1",
              "sourceOrigin": "http://127.0.0.1:9998", "targetOrigin": "http://127.0.0.1:9999",
              "baseUrl": "http://127.0.0.1:9999/login", "apiOrigin": "http://127.0.0.1:9999",
              "allowedOrigins": ["http://127.0.0.1:9999"], "objectOrigins": [], "writeApiPaths": [],
              "browserExecutable": sys.executable, "passwordEnv": "UNPROVIDED_ENGINEERING_SECRET",
              "targetIdentityPin": packet.target, "verificationTargetPin": packet.verification_target,
              "authorizationPin": packet.approval, "deadlineMilliseconds": 20000,
              "login": {}, "flows": [], "schemaPin": schema_pin,
              "prerequisites": {"deltaObservationPin": prior_stage, "fullPointPin": packet.point,
                 "fullBackupResultPin": packet.all_pins["payload"], "incrementalPointPin": packet.point,
                 "incrementalBackupResultPin": packet.all_pins["payload"], "restorePlanPin": packet.plan,
                 "restoreResultPin": packet.restore, "applicationStartPin": packet.app}}
    # This deliberately does not claim a real runnable full+incremental scenario.
    # It checks collector invocation binding only, with no UI/controlled PASS output.
    if config_change:
        config_change(config, packet)
    config_pin = packet.put("ui-config-engineering", config)
    invocation = copy.deepcopy(json_pin(packet.all_pins["collect-browser-call"]))
    entry_path = str(MODULE / entry)
    invocation["sourcePins"] = [file_pin(sys.executable), file_pin(entry_path)]
    invocation["argv"] = [sys.executable, entry_path, "--config", config_pin["path"], "--output", packet.browser["path"]]
    if argv_change:
        argv_change(invocation["argv"], packet)
    saved = json_pin(invocation["processResultPin"])
    saved["argv"] = invocation["argv"]
    invocation["processResultPin"] = packet.put("ui-call-process-engineering", saved)
    invocation_pin = packet.put("ui-call-engineering", invocation)
    context = current_context(packet, packet.request, omit_original=omit_original)
    return packet, context, invocation_pin


def test_ui_target_collector_entry_is_bound_to_current_independent_originals(tmp_path):
    packet, context, invocation = ui_collection_case(tmp_path)
    admitted = collection_invocation(context, invocation, "COLLECT_PLAYWRIGHT", packet.browser, packet.verification_target)
    assert admitted["argv"][1] == str(MODULE / "run_ui_recovery.py")


@pytest.mark.parametrize("change,code", [
    (lambda argv, _: argv.append("--check"), "COLLECTOR_ARGV_INVALID"),
    (lambda argv, _: argv.insert(1, "-c"), "HOST_ABSOLUTE_PATH_REQUIRED"),
    (lambda argv, _: argv.extend(["--tool", str(MODULE / "collect_recovery.py")]), "COLLECTOR_ARGV_INVALID"),
    (lambda argv, p: argv.__setitem__(3, p.target["path"]), "RECORD_FIELDS"),
    (lambda argv, p: argv.__setitem__(5, p.target["path"]), "COLLECTOR_OUTPUT_UNBOUND"),
])
def test_ui_collector_argv_cannot_impersonate_defined_entry(tmp_path, change, code):
    packet, context, invocation = ui_collection_case(tmp_path, argv_change=change)
    with pytest.raises(VerificationError, match=code):
        collection_invocation(context, invocation, "COLLECT_PLAYWRIGHT", packet.browser, packet.verification_target)


@pytest.mark.parametrize("change,code", [
    (lambda value, _: value.update(phase="delta"), "COLLECTOR_TARGET_PHASE_REQUIRED"),
    (lambda value, _: value.update(operationId="other"), "OPERATION_RESTORE_MISMATCH"),
    (lambda value, _: value.update(restoreId="other"), "OPERATION_RESTORE_MISMATCH"),
    (lambda value, _: value.update(recoveryPoint="other"), "RECOVERY_POINT_MISMATCH"),
    (lambda value, p: value.update(targetIdentityPin=p.image), "TARGET_MISMATCH"),
    (lambda value, p: value["prerequisites"].update(restorePlanPin=p.target), "COLLECTOR_RECOVERY_INPUT_MISMATCH"),
])
def test_ui_collector_config_must_bind_target_restore_and_operation(tmp_path, change, code):
    packet, context, invocation = ui_collection_case(tmp_path, config_change=change)
    with pytest.raises(VerificationError, match=code):
        collection_invocation(context, invocation, "COLLECT_PLAYWRIGHT", packet.browser, packet.verification_target)


@pytest.mark.parametrize("original,code", [("ui-config-engineering", "COLLECTOR_CONFIG_NOT_CALLER_PINNED"),
                                           ("source-stage-engineering", "ORIGINAL_NOT_CALLER_PINNED"),
                                           ("download", "ORIGINAL_NOT_CALLER_PINNED")])
def test_ui_collector_retains_independent_config_and_source_original_gates(tmp_path, original, code):
    packet, context, invocation = ui_collection_case(tmp_path, omit_original=original)
    with pytest.raises(VerificationError, match=code):
        collection_invocation(context, invocation, "COLLECT_PLAYWRIGHT", packet.browser, packet.verification_target)


def test_arbitrary_pinned_script_is_not_a_collector(tmp_path):
    packet, context, invocation = ui_collection_case(tmp_path, entry="verify_recovery.py")
    with pytest.raises(VerificationError, match="COLLECTOR_ENTRY_NOT_PINNED_OR_INVOKED"):
        collection_invocation(context, invocation, "COLLECT_PLAYWRIGHT", packet.browser, packet.verification_target)


@pytest.mark.parametrize("reason,expected", [
    ("REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED", None),
    ("REPOSITORY_PAYLOAD_CORRUPT", "REPOSITORY_POINT_INCOMPLETE"),
    ("EXECUTOR_TERMINAL_UNKNOWN", "REPOSITORY_POINT_INCOMPLETE"),
])
def test_first_rehearsal_uses_mode_specific_eligibility(tmp_path, reason, expected):
    packet = Packet(tmp_path)
    packet.change("point", lambda record: record.update(blockedReason=reason))
    process, result = packet.run()
    if expected is None:
        assert process.returncode == 0, result
        assert result["data"]["verdict"] == "PASSED"
    else:
        assert process.returncode == 1 and result["failureCode"] == expected


def test_report_keeps_business_scope_and_distinct_code_scope(tmp_path):
    packet = Packet(tmp_path)
    process, result = packet.run()
    assert process.returncode == 0, result
    assert result["data"]["sourceScopePin"] == packet.source_scope
    assert result["data"]["targetApprovalRefs"] == packet.request["authorizationRefs"]
    assert json_pin(result["data"]["targetApprovalRefs"][0])["schemaVersion"] == "RecoveryVerificationAuthorization/v1"
    assert json_pin(packet.all_pins["executable-scope"])["schemaVersion"] == "RecoveryExecutableScope/v1"
    assert packet.isolation != packet.application_isolation
    assert packet.application_isolation in result["data"]["dataEvidencePins"]


def test_native_originals_do_not_accept_engineering_wrappers(tmp_path):
    packet = Packet(tmp_path)
    wrapper = packet.invocation("unrelated-wrapper", "RESTORE_EXECUTE", packet.all_pins["payload"], 3, 7)
    packet.change("restore", lambda record: record.update(originalInvocationPins=[wrapper]))
    process, result = packet.run()
    assert process.returncode == 1 and result["failureCode"] == "RESTORE_NATIVE_INTENTS_REQUIRED"


@pytest.mark.parametrize("name,mutation,code", [
    ("native-request-0", lambda record: record.update(action="OBJECT_FULL"), "NATIVE_RESULT_BINDING_INVALID"),
    ("native-result-0", lambda record: record.update(requestId="other-request"), "NATIVE_RESULT_BINDING_INVALID"),
    ("material", lambda record: record.update(sourceScopePin=record["derivedInventoryPin"]), "BUSINESS_SOURCE_SCOPE_MISMATCH"),
    ("application-isolation", lambda record: record.update(policyPin=record["targetIdentityPin"]), "SIDE_EFFECT_POLICY_MISMATCH"),
    ("data", lambda record: record["data"]["objectTarget"].update(containerId="source-container"), "ACTUAL_SERVICE_TARGET_MISMATCH"),
    ("object-binding", lambda record: record.update(endpointUrl="http://10.255.0.1:9000"), "SERVICE_ENDPOINT_TARGET_MISMATCH"),
    ("application-native-call", lambda record: record.update(actualExitCode=None), "ORIGINAL_PROCESS_EXIT_UNKNOWN"),
    ("material", lambda record: record.update(manifestPin=record["derivedInventoryPin"]), "NATIVE_MATERIAL_POINT_MISMATCH"),
    ("restore", lambda record: record.update(objectStepEvidencePins=record["objectStepEvidencePins"]*2), "RESTORE_OBJECT_CHAIN_COVERAGE"),
])
def test_native_target_lifecycle_and_exit_rejections(tmp_path, name, mutation, code):
    packet = Packet(tmp_path)
    packet.change(name, mutation)
    process, result = packet.run()
    assert result["failureCode"] == code, result
    assert process.returncode == (2 if code == "ORIGINAL_PROCESS_EXIT_UNKNOWN" else 1)


def test_required_derived_state_is_not_certified_by_producer_verified(tmp_path):
    packet = Packet(tmp_path)
    packet.change("derived-inventory", lambda record: record["classes"]["redis"].update(
        classification="REBUILD", requiredForBusiness=True))
    process, result = packet.run()
    assert process.returncode == 1 and result["failureCode"] == "DERIVED_OBSERVATION_COVERAGE_REQUIRED"


def test_caller_binding_uses_exact_existing_request_and_does_not_mint_approval(tmp_path):
    packet = Packet(tmp_path)
    process, result = packet.run()
    assert process.returncode == 0, result
    selection = json_pin(packet.all_pins["trust"])
    selection["schemaVersion"] = "RecoveryCallerSelection/v1"
    selected_pin = write_atomic(str(tmp_path / "independent-selection.json"), selection)
    binding_pin = bind(packet.all_pins["request"]["path"], str(tmp_path / "caller-binding.json"), selected_pin)
    value = json_pin(binding_pin)
    assert value == dict(selection, schemaVersion="RecoveryCallerBinding/v1")
    assert packet.request["authorizationRefs"] == result["data"]["targetApprovalRefs"]
    altered = dict(packet.request, requestId="second-request")
    changed_path = tmp_path / "changed-request.json"
    changed_path.write_bytes(canonical(altered))
    with pytest.raises(VerificationError, match="CALLER_REQUEST_MISMATCH"):
        bind(str(changed_path), str(tmp_path / "wrong-binding.json"), selected_pin)
    assert not (tmp_path / "wrong-binding.json").exists()


def test_binary_pin_hash_is_streamed_and_deadline_checked_between_chunks(tmp_path):
    path = tmp_path / "archive.bin"
    block = b"archive" * 160000
    with path.open("wb") as stream:
        for _ in range(4):
            stream.write(block)
    expected = file_pin(str(path), Deadline(1000))
    assert read_pin(expected, Deadline(1000), content=False) == expected

    class ExpiringBudget:
        def __init__(self):
            self.calls = 0
        def remaining(self):
            self.calls += 1
            if self.calls == 3:
                raise VerificationError("DEADLINE_EXCEEDED", "UNKNOWN")
            return 1
    budget = ExpiringBudget()
    with pytest.raises(VerificationError, match="DEADLINE_EXCEEDED"):
        read_pin(expected, budget, content=False)
    assert budget.calls == 3


def test_json_original_has_explicit_size_limit(tmp_path, monkeypatch):
    import core
    path = tmp_path / "oversized.json"
    path.write_bytes(b'{"payload":"' + b"x"*128 + b'"}')
    pin = file_pin(str(path))
    monkeypatch.setattr(core, "MAX_JSON_BYTES", 64)
    assert read_pin(pin, content=False) == pin
    with pytest.raises(VerificationError, match="JSON_INPUT_LIMIT"):
        json_pin(pin)


@pytest.mark.parametrize("name,mutation,code", [
    ("protection-AFTER_START", lambda r: r["scopeObservations"][0].update(rejectionObservationPins=[]),
     "APPLICATION_PROTECTION_REFUSAL_REQUIRED"),
    ("protection-BEFORE_START", lambda r: r["containers"].update(minio="source-container"),
     "APPLICATION_PROTECTION_CONTAINERS_UNBOUND"),
    ("refusal-call-AFTER_START", lambda r: r.update(actualExitCode=None),
     "APPLICATION_PROTECTION_REFUSAL_TERMINATION_UNPROVEN"),
])
def test_application_enforced_label_cannot_replace_actual_refusal(tmp_path, name, mutation, code):
    packet = Packet(tmp_path)
    packet.change(name, mutation)
    process, result = packet.run()
    assert result["failureCode"] == code, result
    assert process.returncode == (2 if code.endswith("TERMINATION_UNPROVEN") else 1)


def test_native_local_and_combined_exits_bind_without_rewriting(tmp_path):
    from types import SimpleNamespace
    from native_originals import native_exit
    intent = write_atomic(str(tmp_path / "intent.json"), {"schemaVersion": "recovery-invocation/v1"})
    local = {"schemaVersion": "recovery-original-exit/v1", "intentPin": intent, "actualExitCode": 0,
             "timedOut": False, "remoteTerminalConfirmed": None, "finishedAt": "2026-10-10T12:00:00Z"}
    local_pin = write_atomic(str(tmp_path / "client-exit.json"), local)
    combined = dict(local, localExitPin=local_pin, remoteTerminalProofPins=[])
    combined_pin = write_atomic(str(tmp_path / "exit.json"), combined)
    records = [(local_pin, local), (combined_pin, combined)]
    assert native_exit(SimpleNamespace(), intent, records) == combined
    combined["localExitPin"] = intent
    with pytest.raises(VerificationError, match="NATIVE_LOCAL_EXIT_BINDING_MISMATCH"):
        native_exit(SimpleNamespace(), intent, records)
    combined["localExitPin"] = local_pin
    combined["remoteTerminalConfirmed"] = True
    with pytest.raises(VerificationError, match="REMOTE_TERMINAL_ORIGINALS_REQUIRED"):
        native_exit(SimpleNamespace(), intent, records)


@pytest.mark.parametrize("actual_hash,expected", [("a"*64, None), ("b"*64, "DERIVED_BUSINESS_STATE_MISMATCH")])
def test_required_derived_state_compares_actual_target_to_independent_baseline(tmp_path, actual_hash, expected):
    from types import SimpleNamespace
    from derived_state import verify_derived
    from core import pin_key
    packet = Packet(tmp_path)
    inventory = json_pin(packet.derived_inventory)
    inventory["classes"]["redis"].update(classification="REBUILD", requiredForBusiness=True)
    inventory_pin = packet.put("required-redis-inventory", inventory)
    config = json_pin(packet.target_ref)
    config["services"].append({"role": "redis", "name": "fixture-redis"})
    config_pin = packet.put("derived-target-configuration", config)
    binding = json_pin(packet.object_binding)
    resources = json_pin(binding["resourcesProofPin"])
    redis = copy.deepcopy(resources["services"][0])
    redis.update(id="redis-target", name="/fixture-redis", imageId="fixture-redis-image")
    redis["networks"]["fixture-network"].update(IPAddress="10.254.0.4", EndpointID="endpoint-redis")
    resources["services"].append(redis)
    resources["configurationRef"] = config_pin
    resources_pin = packet.put("derived-target-resources", resources)
    launch = json_pin(packet.all_pins["application-launch"])
    launch["network"]["containers"]["redis-target"] = {"Name": "fixture-redis", "EndpointID": "endpoint-redis",
                                                       "IPv4Address": "10.254.0.4/24"}
    launch_pin = packet.put("derived-application-launch", launch)
    application = json_pin(packet.app)
    application["originalStartResultPins"] = [launch_pin]
    application_pin = packet.put("derived-application-result", application)
    binding.update(role="redis", endpointUrl="redis://10.254.0.4:6379", environmentConfigPin=config_pin,
                   resourcesProofPin=resources_pin, applicationStartPin=application_pin)
    binding_pin = packet.put("derived-service-binding", binding)
    service = dict(packet.snapshot["objectTarget"], bindingPin=binding_pin, role="redis", endpointUrl=binding["endpointUrl"],
                   containerId="redis-target", imageId="fixture-redis-image", endpointId="endpoint-redis", ipAddress="10.254.0.4")
    settings_pin = packet.put("derived-observer-settings", {"database": 0})
    baseline = packet.put("independent-derived-baseline", {"schemaVersion": "RecoveryDerivedBaseline/v1",
        "recoveryPoint": "point-1", "inventoryPin": inventory_pin,
        "states": [{"className": "redis", "recordCount": 3, "stateSha256": "a"*64}]})
    context = SimpleNamespace(derived_inventory=inventory, derived_inventory_pin=inventory_pin,
        plan={"recoveryPoint": "point-1"}, source_keys={pin_key(packet.tool)}, target_pin=packet.target,
        source_pin=packet.source_scope, request={"operationId": "op1", "sourceOrTargetRef": config_pin,
                                               "inputPins": {"applicationStartResult": application_pin}},
        record=json_pin, read=lambda ref: read_pin(ref, content=False))
    data = {"derivedInventoryPin": inventory_pin, "derived": [{"className": "redis", "recordCount": 3,
        "stateSha256": actual_hash, "service": service, "observerSourcePins": [packet.tool],
        "observerSettingsPin": settings_pin, "actualExitCode": 0, "outputSha256": "c"*64}]}
    if expected:
        with pytest.raises(VerificationError, match=expected):
            verify_derived(context, baseline, data)
    else:
        verify_derived(context, baseline, data)
