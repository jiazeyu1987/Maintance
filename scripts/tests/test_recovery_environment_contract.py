from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import jsonschema
import pytest

from test_recovery_environment_fixtures import LocalRecords, MODULE
from recovery_environment_contract import (EnvironmentFailure, atomic_json, authorize, decode,
    digest, original_w04_exits, pin_file, read_pin, safe_path, verify_large_pin)
from recovery_environment import (check_controlled_preconditions, run_operation, validate_configuration,
    validate_endpoint_bindings, validate_plan, validate_startup_inventory)
from recovery_environment_runtime import CommandRunner, exclusive_lock, capacity_observation


@pytest.fixture
def records(tmp_path):
    return LocalRecords(tmp_path)


def rejects(code, function, *args, **kwargs):
    with pytest.raises(EnvironmentFailure) as error:
        function(*args, **kwargs)
    assert error.value.code == code
    return error.value


def test_configuration_and_frozen_plan_allow_explicit_frontend_port_80(records):
    assert validate_configuration(records.config, records.policy, records.trust, lambda: None) is records.config
    assert validate_plan(records.plan, records.plan_pin, records.request, records.config, records.trust) is records.plan
    jsonschema.Draft202012Validator({"$ref": "#/$defs/RestorePlan", "$defs": records.trust.schemas.schema["$defs"]}).validate(records.plan)


@pytest.mark.parametrize("change", ["unknown", "missing", "bad-pin", "bool-deadline", "bad-mode", "bad-action"])
def test_frozen_request_agrees_with_independent_jsonschema(records, change):
    request = deepcopy(records.request)
    if change == "unknown":
        request["unexpected"] = True
    elif change == "missing":
        del request["mode"]
    elif change == "bad-pin":
        request["selectedPointPin"] = {"sha256": "a"*64}
    elif change == "bool-deadline":
        request["deadlineMilliseconds"] = True
    elif change == "bad-mode":
        request["mode"] = "DEFAULT"
    else:
        request["action"] = "START_ALL"
    with pytest.raises(EnvironmentFailure):
        records.trust.schemas.validate(request, "OperationRequest")
    validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/OperationRequest", "$defs": records.trust.schemas.schema["$defs"]})
    assert list(validator.iter_errors(request))


def test_nullable_pin_schema_does_not_bypass_nonnull_pin_validation(records):
    request = deepcopy(records.request)
    request["selectedPointPin"] = request["leaseRef"] = None
    records.trust.schemas.validate(request, "OperationRequest")
    records.trust.schemas.validate(records.request, "OperationRequest")


@pytest.mark.parametrize("raw,code", [(b'{"a":1,"a":2}', "DUPLICATE_JSON_KEY"),
    (b'{"a":NaN}', "NONFINITE_JSON_NUMBER"), (b'\xff', "JSON_INVALID")])
def test_strict_json(raw, code):
    rejects(code, decode, raw)


def test_changed_pin_bytes_and_digest_fail(records):
    Path(records.sample["path"]).write_bytes(b'{"changed":true}')
    rejects("PIN_MISMATCH", read_pin, records.sample)
    rejects("ARCHIVE_PIN_MISMATCH", verify_large_pin, records.sample, lambda: None)


def test_link_and_path_traversal_rejected(tmp_path):
    rejects("ABSOLUTE_PATH_REQUIRED", safe_path, "relative.json")
    rejects("PATH_TRAVERSAL", safe_path, str(tmp_path/".."/"value.json"), exists=False)
    source = tmp_path/"source.json"
    source.write_bytes(b"{}")
    linked = tmp_path/"linked.json"
    # Hard links are available on Windows without symbolic-link privileges.
    linked.hardlink_to(source)
    rejects("PIN_FILE_INVALID", pin_file, linked)


@pytest.mark.parametrize("field,value,code", [("approved", False, "AUTHORIZATION_NOT_APPROVED"),
    ("mode", "CONTROLLED_RESTORE", "AUTHORIZATION_SCOPE_MISMATCH"),
    ("targetId", "another-target", "AUTHORIZATION_SCOPE_MISMATCH"),
    ("executorId", "another-owner", "AUTHORIZATION_SCOPE_MISMATCH"),
    ("actions", [], "ACTION_NOT_AUTHORIZED"),
    ("expiresAt", "2000-01-01T00:00:00Z", "AUTHORIZATION_OR_LEASE_EXPIRED")])
def test_authorization_does_not_downgrade(records, field, value, code):
    records.authorization[field] = value
    records.approve()
    rejects(code, authorize, records.request, records.trust, records.config["targetId"])


@pytest.mark.parametrize("field,value", [("state", "RELEASED"), ("fenceToken", True), ("fenceToken", 0), ("operationId", "other")])
def test_lease_scope_is_live_and_owned(records, field, value):
    records.lease[field] = value
    records.approve()
    rejects("LEASE_SCOPE_MISMATCH", authorize, records.request, records.trust, "unit-target")


def test_request_cannot_authorize_its_own_new_configuration(records):
    changed = deepcopy(records.config)
    changed["targetId"] = "new-target"
    records.request["sourceOrTargetRef"] = records.write("unapproved-config.json", changed)
    rejects("INPUT_NOT_TRUSTED", run_operation, records.request, records.trust, time.monotonic()+2)


@pytest.mark.parametrize("issue,code", [("overlap", "PRIVATE_PUBLIC_STATE_ROOT_OVERLAP"),
    ("capability", "SERVICE_CAPABILITY_REJECTED"), ("secret-public", "PUBLIC_ENV_SECRET_OR_FORMAT_REJECTED"),
    ("source-address", "SOURCE_ENV_ADDRESS_REJECTED"), ("shared-volume", "CROSS_SERVICE_VOLUME_SHARING_REJECTED"),
    ("host-port", "PORT_MAPPING_UNSAFE"), ("metadata-address", "SOURCE_ENDPOINT_MAPPING_REJECTED"),
    ("non-independent", "MATERIAL_NOT_IN_INDEPENDENT_CUSTODY"), ("missing-host-probe", "SOURCE_HOST_EXTERNAL_PROBES_INCOMPLETE")])
def test_configuration_rejects_unsafe_runtime_before_any_executor(records, issue, code):
    config, policy = deepcopy(records.config), deepcopy(records.policy)
    if issue == "overlap":
        config["privateRoot"] = config["evidenceRoot"]
    elif issue == "capability":
        config["services"][3]["capabilities"] = ["NET_ADMIN"]
    elif issue in ("secret-public", "source-address"):
        key = "DB_PASSWORD" if issue == "secret-public" else "OUTBOUND_HOST"
        value = "unit-test-value" if issue == "secret-public" else "http://10.40.0.2:80"
        config["services"][3]["env"][key] = value
        application = deepcopy(records.configuration)
        application["serviceEnvironment"]["backend"][key] = value
        config["configurationPin"] = records.write("unsafe-env.json", application)
    elif issue == "shared-volume":
        config["services"][1]["mounts"][0]["volume"] = config["services"][0]["mounts"][0]["volume"]
    elif issue == "host-port":
        config["services"][4]["ports"][0]["hostPort"] = 80
    elif issue == "metadata-address":
        application = deepcopy(records.configuration)
        application["endpointMap"]["database"]["host"] = "10.40.0.2"
        config["configurationPin"] = records.write("unsafe-endpoint.json", application)
    elif issue == "non-independent":
        unowned = records.root/"unowned-tool"
        unowned.write_bytes(b"unit-tool")
        config["dockerPin"] = pin_file(unowned)
    else:
        policy["blockedEndpoints"] = [endpoint for endpoint in policy["blockedEndpoints"] if endpoint["class"] != "HOST"]
    rejects(code, validate_configuration, config, policy, records.trust, lambda: None)


@pytest.mark.parametrize("issue,code", [("wrong-consumer", "ENDPOINT_CONSUMER_CONFIGURATION_MISMATCH"),
    ("missing-consumer", "ENDPOINT_CONSUMER_COVERAGE_INCOMPLETE"), ("no-source", "ENDPOINT_CONSUMER_SOURCE_EVIDENCE_REQUIRED"),
    ("template-access", "ENDPOINT_TEMPLATE_UNSAFE")])
def test_actual_endpoint_consumers_are_required(records, issue, code):
    application = deepcopy(records.configuration)
    if issue == "wrong-consumer":
        application["endpointBindings"][0]["template"] = "http://{host}:{port}"
    elif issue == "missing-consumer":
        application["endpointBindings"].pop()
    elif issue == "no-source":
        application["endpointBindings"][0]["consumerEvidencePins"] = []
    else:
        application["endpointBindings"][0]["template"] = "{host.__class__}:{port}"
    rejects(code, validate_endpoint_bindings, application, records.config, lambda: None)


@pytest.mark.parametrize("issue,code", [("one-switch", "STARTUP_CALL_PATH_COVERAGE_INCOMPLETE"),
    ("wrong-image", "STARTUP_INVENTORY_IMAGE_MISMATCH"), ("no-source", "STARTUP_ENTRANCE_EVIDENCE_REQUIRED"),
    ("enabled-hook", "STARTUP_ENTRANCE_UNSAFE"), ("unbound-switch", "STARTUP_ENTRANCE_NOT_DISABLED")])
def test_quartz_switch_does_not_prove_all_call_paths(records, issue, code):
    policy = deepcopy(records.policy)
    inventory = read_pin(policy["startupInventoryPins"][0])
    if issue == "one-switch":
        inventory["entrances"] = [entry for entry in inventory["entrances"] if entry["type"] == "QUARTZ"]
    elif issue == "wrong-image":
        inventory["imageId"] = "sha256:" + "f"*64
    elif issue == "no-source":
        inventory["entrances"][0]["evidencePins"] = []
    elif issue == "enabled-hook":
        inventory["entrances"][0]["state"] = "ENABLED"
    else:
        inventory["entrances"][0].update(state="DISABLED_BY_CONFIGURATION", requiredEnvironment={"DISABLE_HOOKS": "true"})
    policy["startupInventoryPins"][0] = records.write("invalid-startup.json", inventory)
    rejects(code, validate_startup_inventory, records.config, policy, records.images)


def runner(tmp_path, seconds=3, guard=lambda: None):
    return CommandRunner(tmp_path, time.monotonic()+seconds, guard)


def test_real_child_exit_zero_preserves_digest_and_not_secret_bytes(tmp_path):
    execution = runner(tmp_path)
    marker = "LOCAL_SECRET_SENTINEL_FOR_REDACTION"
    assert execution.run([sys.executable, "-I", "-c", f"import sys; sys.stdout.buffer.write(b'{marker}\\n')"]) == (marker+"\n").encode()
    receipt = read_pin(execution.pins[0])
    assert receipt["actualExitCode"] == 0 and receipt["state"] == "SUCCEEDED"
    assert receipt["stdoutSha256"] == hashlib.sha256((marker+"\n").encode()).hexdigest()
    assert marker not in Path(execution.pins[0]["path"]).read_text()


@pytest.mark.parametrize("script,code,exit_code", [("raise SystemExit(7)", "EXECUTOR_NONZERO_EXIT", 7),
    ("import sys; sys.stderr.write('LOCAL_SECRET_ERROR_SENTINEL')", "EXECUTOR_STDERR_PRESENT", 0)])
def test_real_child_failure_is_not_exit_zero_success(tmp_path, script, code, exit_code):
    execution = runner(tmp_path)
    rejects(code, execution.run, [sys.executable, "-I", "-c", script])
    receipt = read_pin(execution.pins[0])
    assert receipt["actualExitCode"] == execution.last_exit == exit_code
    assert receipt["state"] == "FAILED_RETAINED"
    assert "LOCAL_SECRET_ERROR_SENTINEL" not in Path(execution.pins[0]["path"]).read_text()


def test_real_child_deadline_is_killed_and_effect_unknown(tmp_path):
    execution = runner(tmp_path, seconds=0.15)
    failure = rejects("DEADLINE_EXCEEDED", execution.run, [sys.executable, "-I", "-c", "import time; time.sleep(10)"], mutation=True)
    assert failure.unknown
    receipt = read_pin(execution.pins[0])
    assert receipt["actualExitCode"] is not None and receipt["actualExitCode"] != 0
    assert receipt["state"] == "TERMINAL_UNKNOWN"
    assert time.monotonic() < execution.deadline+3


def test_live_lease_revocation_terminates_owned_child_and_retains_reason(tmp_path, monkeypatch):
    processes = []
    import recovery_environment_runtime as native
    original_spawn = native.subprocess.Popen
    def spawn(*args, **options):
        process = original_spawn(*args, **options)
        processes.append(process)
        return process
    monkeypatch.setattr(native.subprocess, 'Popen', spawn)
    def guard():
        if processes:
            raise EnvironmentFailure("LEASE_REVOKED")
    execution = runner(tmp_path, guard=guard)
    failure = rejects("LEASE_REVOKED", execution.run, [sys.executable, "-I", "-c", "import time; time.sleep(10)"], mutation=True)
    assert failure.unknown
    assert read_pin(execution.pins[0])["actualExitCode"] is not None
    assert processes[0].poll() is not None


def test_lock_is_exclusive_and_reusable_after_release(tmp_path):
    path = tmp_path/"target.lock"
    with exclusive_lock(path):
        with pytest.raises(EnvironmentFailure, match="TARGET_ALREADY_EXECUTING"):
            with exclusive_lock(path):
                pytest.fail("second executor acquired target")
    with exclusive_lock(path):
        pass


def test_original_w04_requires_real_terminal_for_every_intent(records):
    pins = records.original_child()
    assert original_w04_exits(pins, lambda: None)[0]["actualExitCode"] == 0
    rejects("ORIGINAL_EXECUTOR_TERMINATION_MISSING", original_w04_exits, pins[:-1], lambda: None)
    pins = records.original_child(exit_code=9)
    rejects("ORIGINAL_EXECUTOR_NOT_SUCCEEDED", original_w04_exits, pins, lambda: None)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native-prerequisite failure path")
def test_real_cli_native_prerequisite_fails_retains_and_replays(records, monkeypatch):
    # Windows host cannot execute the required Linux namespace path. This is
    # a real CLI failure test, not a successful recovery or Docker simulation.
    assert sys.platform == "win32"
    monkeypatch.setenv("RECOVERY_ENVIRONMENT_TRUST_FILE", records.trust_pin["path"])
    monkeypatch.setenv("RECOVERY_ENVIRONMENT_TRUST_SHA256", records.trust_pin["sha256"])
    request_pin = records.write("request.json", records.request)
    env = dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1")
    results = []
    for index in range(2):
        output = records.root/f"cli-result-{index}.json"
        child = subprocess.run([sys.executable, "-I", str(MODULE/"environment_cli.py"), "--request", request_pin["path"],
                                "--output", str(output)], capture_output=True, timeout=10, env=env)
        assert child.returncode == 1, child.stderr
        result = json.loads(output.read_text())
        assert result["state"] == "FAILED_RETAINED" and result["failureCode"] == "NATIVE_LINUX_ROOT_WITH_SETNS_REQUIRED"
        assert result["actualExitCode"] is None and result["data"] is None
        records.trust.schemas.validate(result, "OperationResult")
        results.append(result)
    assert results[0] == results[1]
    assert len(list((records.root/"evidence").iterdir())) == 1


def test_unknown_previous_invocation_never_retries(records):
    journal = Path(records.config["journalRoot"])/("request-"+hashlib.sha256(records.request["requestId"].encode()).hexdigest()+".json")
    atomic_json(journal, {"requestSha256": digest(records.request), "state": "RUNNING"})
    failure = rejects("PREVIOUS_INVOCATION_TERMINAL_UNKNOWN", run_operation, records.request, records.trust, time.monotonic()+3)
    assert failure.unknown
    assert not list((records.root/"evidence").iterdir())
    records.request["deadlineMilliseconds"] += 1
    rejects("IDEMPOTENCY_CONTENT_MISMATCH", run_operation, records.request, records.trust, time.monotonic()+3)


def test_rehearsal_rejects_source_cutover_configuration(records):
    class NotAnExecutor:
        def __getattr__(self, key):
            pytest.fail("rehearsal attempted native source access: " + key)
    assert check_controlled_preconditions(records.request, records.config, records.trust, NotAnExecutor())["sourceWritesAuthorized"] is False
    records.config["controlledPreconditions"] = {}
    rejects("REHEARSAL_CONTROLLED_CONFIGURATION_REJECTED", check_controlled_preconditions,
            records.request, records.config, records.trust, NotAnExecutor())


def test_cli_never_overwrites_existing_output(tmp_path):
    output = tmp_path/"existing.json"
    output.write_bytes(b"keep-existing")
    request = tmp_path/"request.json"
    request.write_bytes(b"{}")
    child = subprocess.run([sys.executable, "-I", str(MODULE/"environment_cli.py"), "--request", str(request), "--output", str(output)],
                           capture_output=True, timeout=5)
    assert child.returncode == 1 and b"OUTPUT_ALREADY_EXISTS" in child.stderr
    assert output.read_bytes() == b"keep-existing"


def test_first_complete_rehearsal_point_does_not_require_its_own_report(records):
    records.point.update(blockedReason="REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED", controlledRestoreEligible=False)
    records.point_pin = records.write("point.json", records.point)
    records.approve()
    assert validate_plan(records.plan, records.plan_pin, records.request, records.config, records.trust) == records.plan
    records.request["mode"] = records.plan["mode"] = "CONTROLLED_RESTORE"
    assert validate_plan(records.plan, records.plan_pin, records.request, records.config, records.trust) == records.plan
    # A valid immutable point only passes the structural gate; run_operation
    # still requires independently selected current report and signed approval.


@pytest.mark.parametrize("reason", ["REPOSITORY_ORIGINAL_EXIT_UNKNOWN", "REPOSITORY_PAYLOAD_CORRUPT"])
def test_actual_point_failures_still_block_rehearsal(records, reason):
    records.point["blockedReason"] = reason
    records.point_pin = records.write("point.json", records.point)
    records.approve()
    rejects("RESTORE_POINT_NOT_ELIGIBLE", validate_plan, records.plan, records.plan_pin, records.request, records.config, records.trust)


def test_shared_filesystem_capacity_combines_simultaneous_peaks(tmp_path):
    data, temporary = tmp_path/"data", tmp_path/"temporary"
    data.mkdir(); temporary.mkdir()
    free = __import__("shutil").disk_usage(data).free
    rejects("TARGET_SPACE_INSUFFICIENT", capacity_observation, temporary, data, free//2+1, free//2+1)
    observed = capacity_observation(temporary, data, 1024, 2048)
    assert len(observed["filesystems"]) == 1
    assert observed["filesystems"][0]["requiredBytes"] == 3072


@pytest.mark.parametrize("state", ["RUNNING", "TERMINAL_UNKNOWN"])
def test_new_request_cannot_bypass_target_unknown_gate(records, state):
    identity = read_pin(records.config["targetIdentityPin"])
    target_key = digest({"targetId": records.config["targetId"], "machineId": identity["machineId"],
                         "dockerEngineId": identity["dockerEngineId"]})
    path = Path(records.config["journalRoot"])/("target-"+target_key+".json")
    atomic_json(path, {"targetKey": target_key, "state": state, "requestId": "earlier-uncertain-request"})
    records.request["requestId"] = "new-request"
    failure = rejects("TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN", run_operation,
                      records.request, records.trust, time.monotonic()+3)
    assert failure.unknown and not list((records.root/"evidence").iterdir())


def test_new_request_checks_prior_uncertain_journal_for_same_target(records):
    identity = read_pin(records.config["targetIdentityPin"])
    target_key = digest({"targetId": records.config["targetId"], "machineId": identity["machineId"],
                         "dockerEngineId": identity["dockerEngineId"]})
    atomic_json(Path(records.config["journalRoot"])/"request-earlier.json", {"targetKey": target_key, "state": "TERMINAL_UNKNOWN"})
    failure = rejects("TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN", run_operation,
                      records.request, records.trust, time.monotonic()+3)
    assert failure.unknown
