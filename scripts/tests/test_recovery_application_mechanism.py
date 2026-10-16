"""Affected mechanism checks; these do not represent recovery/runtime acceptance."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops/recovery"))
from recovery_application_mechanism import (SCOPES, Executor, ProtectionFailure, canonical, decode,
    pin_file, read_pin, select_configuration, validate_observation, write_json)
from recovery_environment_runtime import CommandRunner
from recovery_environment_contract import read_pin as read_environment_pin
from recovery_environment_contract import EnvironmentFailure
from recovery_application_protection import validate_recovery_launch


def test_pinned_executor_inputs_reject_tampering_and_symlink(tmp_path):
    path = tmp_path / "configuration.json"
    path.write_bytes(canonical({"purpose": "unit-input-only"}))
    pin = pin_file(path)
    assert read_pin(pin) == {"purpose": "unit-input-only"}
    path.write_bytes(canonical({"purpose": "tampered"}))
    with pytest.raises(ProtectionFailure, match="PROTECTION_PIN_CHANGED"):
        read_pin(pin)


def test_duplicate_json_keys_and_nonfinite_values_are_not_accepted():
    with pytest.raises(ProtectionFailure, match="PROTECTION_DUPLICATE_JSON_KEY"):
        decode(b'{"scope":"BUSINESS_DATABASE","scope":"SCHEDULERS"}')
    with pytest.raises(ProtectionFailure, match="PROTECTION_NONFINITE_JSON"):
        decode(b'{"x":NaN}')


def test_native_probe_requires_every_scope_original_binding_and_unchanged_fingerprints():
    pin = {"sha256": "a" * 64}
    before = {scope: "b" * 64 for scope in SCOPES}
    observation = {"schemaVersion": "RecoveryProtectionNativeProbe/v1", "configurationSha256": pin["sha256"],
                   "state": "REFUSED", "scopes": sorted(SCOPES), "beforeFingerprints": before, "afterFingerprints": dict(before)}
    validate_observation(observation, pin)
    for field, value, code in (
        ("configurationSha256", "c" * 64, "PROTECTION_NATIVE_COVERAGE_INVALID"),
        ("scopes", sorted(SCOPES)[:-1], "PROTECTION_NATIVE_COVERAGE_INVALID"),
        ("afterFingerprints", {**before, "BUSINESS_OBJECTS": "d" * 64}, "PROTECTION_NATIVE_BUSINESS_STATE_CHANGED"),
        ("state", "NOT_OBSERVED", "PROTECTION_NATIVE_COVERAGE_INVALID"),
    ):
        changed = deepcopy(observation); changed[field] = value
        with pytest.raises(ProtectionFailure, match=code):
            validate_observation(changed, pin)


def test_missing_operator_provisioning_is_not_replaced_by_request_input(monkeypatch):
    monkeypatch.delenv("RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN", raising=False)
    request = {"schemaVersion": "RecoveryApplicationWriteProtectionRequest/v1", "phase": "BEFORE_START",
               "operationId": "unit-only", "restoreId": "unit-only", "targetIdentityPin": {}, "recoveryPoint": "unit-only",
               "policyPin": {}, "configurationPin": {}, "imagePins": [], "containers": {}, "deadlineMilliseconds": 1000}
    with pytest.raises(ProtectionFailure, match="APPLICATION_MECHANISM_CONFIG_NOT_PROVISIONED"):
        select_configuration(request)


def test_actual_child_exit_is_preserved_and_not_inferred_from_probe_state(tmp_path):
    executor = Executor({"deadlineMilliseconds": 5000}, {}, tmp_path)
    raw = executor.run([sys.executable, "-I", "-c", "print('unit-child')"], mutation=True)
    receipt = read_pin(executor.invocations[-1])
    assert raw.strip() == b"unit-child"
    assert receipt["actualExitCode"] == 0 and receipt["state"] == "SUCCEEDED" and receipt["mutation"] is True
    assert type(receipt["pid"]) is int and receipt["pid"] > 0
    assert receipt["stdoutSha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ProtectionFailure, match="PROTECTION_NATIVE_EXECUTION_FAILED"):
        executor.run([sys.executable, "-I", "-c", "raise SystemExit(7)"], mutation=True)
    failure = read_pin(executor.invocations[-1])
    assert failure["actualExitCode"] == 7 and failure["state"] == "FAILED_RETAINED"


def test_worker_secrets_never_enter_original_command_or_saved_output(tmp_path):
    executor = Executor({"deadlineMilliseconds": 5000}, {}, tmp_path)
    secret = b"unit-test-credential-not-runtime"
    raw = executor.run([sys.executable, "-I", "-c", "import sys; sys.stdin.buffer.read(); print('redacted')"],
                       mutation=True, stdin=secret)
    assert raw.strip() == b"redacted"
    assert all(secret not in Path(pin["path"]).read_bytes() for pin in executor.invocations)


def test_evidence_cannot_overwrite_an_existing_original(tmp_path):
    path = tmp_path / "observation.json"
    write_json(path, {"state": "unit-only"})
    with pytest.raises(ProtectionFailure, match="PROTECTION_EVIDENCE_ALREADY_EXISTS"):
        write_json(path, {"state": "replacement"})


def test_protection_configuration_binding_survives_explicit_child_environment(tmp_path):
    runner = CommandRunner(tmp_path, time.monotonic() + 5, lambda: None)
    raw = runner.run([sys.executable, "-I", "-c", "import os; print(os.environ['RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN'])"],
                     environment_bindings={"RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN": "unit-only-pinned-config"})
    assert raw.strip() == b"unit-only-pinned-config"
    receipt = read_environment_pin(runner.pins[-1])
    assert receipt["actualExitCode"] == 0 and receipt["pid"] > 0


def test_application_cannot_start_without_exact_pinned_protection_mount_and_jvm_options(tmp_path):
    path = tmp_path / "application.json"
    path.write_bytes(canonical({"artifactSha256": "a" * 64}))
    pin = pin_file(path)
    mount = {"pin": pin, "target": "/run/recovery/protection.json"}
    mechanism = {"applicationConfigPin": pin, "mounts": [mount]}
    backend = {"role": "backend", "configurationMounts": [mount], "command": [], "env": {"JAVA_TOOL_OPTIONS":
               "-Dintruoyi.recovery.protection.path=" + mount["target"] +
               " -Dintruoyi.recovery.protection.sha256=" + pin["sha256"] +
               " -Dintruoyi.maintenance.boot.artifactSha256=" + "a" * 64}}
    config = {"services": [backend], "secretRefs": []}
    validate_recovery_launch(config, mechanism)
    changed = deepcopy(config)
    changed["services"][0]["configurationMounts"] = []
    with pytest.raises(EnvironmentFailure, match="APPLICATION_PROTECTION_LAUNCH_MOUNTS_UNBOUND"):
        validate_recovery_launch(changed, mechanism)
    changed = deepcopy(config)
    changed["services"][0]["env"]["JAVA_TOOL_OPTIONS"] = ""
    with pytest.raises(EnvironmentFailure, match="APPLICATION_PROTECTION_LAUNCH_PROPERTIES_UNBOUND"):
        validate_recovery_launch(changed, mechanism)


def test_later_jvm_property_override_cannot_disable_pinned_protection(tmp_path):
    path = tmp_path / "application.json"
    path.write_bytes(canonical({"artifactSha256": "a" * 64}))
    pin = pin_file(path)
    mount = {"pin": pin, "target": "/run/recovery/protection.json"}
    mechanism = {"applicationConfigPin": pin, "mounts": [mount]}
    backend = {"role": "backend", "configurationMounts": [mount], "command": [], "env": {"JAVA_TOOL_OPTIONS":
               "-Dintruoyi.recovery.protection.path=" + mount["target"] +
               " -Dintruoyi.recovery.protection.sha256=" + pin["sha256"] +
               " -Dintruoyi.maintenance.boot.artifactSha256=" + "a" * 64,
               "_JAVA_OPTIONS": "-Dintruoyi.recovery.protection.path="}}
    with pytest.raises(EnvironmentFailure, match="APPLICATION_PROTECTION_LAUNCH_PROPERTY_OVERRIDE"):
        validate_recovery_launch({"services": [backend], "secretRefs": []}, mechanism)
