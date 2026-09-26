from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from ops.release import release_preflight_plan as planner
from ops.release.release_preflight_plan import build_preflight_plan
from ops.release.release_deploy_executor import execute_preflight_apply_migrations, ReleaseDeployExecutionError
from ops.release.release_digest import ArtifactBytes, calculate_package_digest
from ops.release.release_target_state_collector import (
    TargetStateCollectionError, collect_target_state, normalize_target_snapshot,
    fingerprint_target_snapshot, evidence_digest,
)

ROOT = Path(__file__).resolve().parents[2]
PLANNER = ROOT / "ops/release/release_preflight_plan.py"


def package(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    (root / "required-sql").mkdir()
    migrations = []
    artifacts = []
    for n in range(1, 5):
        content = f"-- release-migration: type=schema\nCREATE TABLE task_m{n} (id INT);\n".encode()
        path = f"required-sql/m{n}.sql"
        (root / path).write_bytes(content)
        migrations.append(migration(f"m{n}", sha256=hashlib.sha256(content).hexdigest(), dependsOn=[] if n == 1 else [f"m{n-1}"]))
        artifacts.append(ArtifactBytes(path, content))
    digest = calculate_package_digest(artifacts)
    manifest = {"releaseTag": "release-t3", "publishScope": "app-release",
                "packageDigest": digest.package_digest,
                "artifacts": [vars(item) for item in digest.artifacts],
                "targetRequirements": {"platformPrerequisites": [{"toolId": "dcc-codex", "pathEnv": "DCC_PROJECT_CODE_CODEX_CLI_COMMAND", "sha256Env": "DCC_PROJECT_CODE_CODEX_CLI_SHA256"}]},
                "database": {"schemaMigrations": migrations}}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest


def snapshot(manifest, applied=0, environment="test"):
    return {
        "schemaVersion": "release-deploy-target-state/v1",
        "capturedAt": "2026-09-25T08:00:00Z", "targetEnvironment": environment,
        "hostIdentity": {"host": f"local-{environment}", "machineId": f"machine-{environment}"},
        "databaseIdentity": {"name": "task_t3", "serverUuid": "00000000-0000-4000-8000-000000000003"},
        "schemaEvidence": {"tables": [{"table": f"task_m{n}"} for n in range(1, applied + 1)],
                           "controlSchemaVersion": "v1"},
        "migrationLedgerComplete": True,
        "migrationLedger": [{"migrationId": item["migrationId"], "status": "APPLIED", "sha256": item["sha256"]}
                            for item in manifest["database"]["schemaMigrations"][:applied]],
        "nonSecretConfig": {"MYSQL_DATABASE": "task_t3", "IMAGE_TAG": "release-old", "MINIO_ENDPOINT": "http://storage:9000"},
        "persistentMounts": [{"role": "mysql", "type": "bind", "source": "/data/mysql", "destination": "/var/lib/mysql", "identity": "fs-task-t3"}],
        "platformPrerequisites": [{"toolId": "dcc-codex", "path": "/usr/bin/codex", "approvedSha256": "d" * 64, "actualSha256": "d" * 64, "executable": True}],
    }


def test_default_cli_refuses_unbound_legacy_plan(tmp_path):
    path, _ = package(tmp_path)
    state = tmp_path / "ledger.json"
    state.write_text("{}", encoding="utf-8")
    completed = subprocess.run([sys.executable, "-X", "utf8", str(PLANNER), "--manifest", str(path),
        "--target-state", str(state), "--target-environment", "test", "--publish-scope", "app-release",
        "--output", str(tmp_path / "plan.json")], capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode != 0, "deploy CLI must reject legacy unbound input"


def test_executor_refuses_unbound_legacy_plan_before_any_callback():
    calls = []
    with pytest.raises(ReleaseDeployExecutionError, match="TARGET_BOUND_PLAN_REQUIRED"):
        execute_preflight_apply_migrations(build([migration()], {}),
            execute_sql=lambda item: calls.append("sql"), record_state=lambda *args: calls.append("ledger"))
    assert calls == []


def migration(migration_id="m1", **changes):
    result = {
        "migrationId": migration_id, "file": f"required-sql/{migration_id}.sql",
        "sha256": "a" * 64, "type": "schema",
        "allowedEnvironments": ["test", "prod", "backup"], "dependsOn": [],
    }
    result.update(changes)
    return result


def build(migrations, ledger):
    return build_preflight_plan(migrations, ledger, target_environment="test", publish_scope="app-release")


def test_applied_checksum_drift_is_blocked_without_replay():
    result = build([migration()], {"m1": {"status": "APPLIED", "sha256": "b" * 64}})
    assert result["status"] == "blocked"
    assert result["items"][0]["action"] == "BLOCKED_CHECKSUM_MISMATCH"


@pytest.mark.parametrize("status", ["FAILED", "RUNNING", "UNKNOWN", "RECOVERY_REQUIRED", ""])
@pytest.mark.parametrize("migration_id", ["m1", "historical-outside-package"])
def test_complete_ledger_rejects_unresolved_status_even_outside_package(status, migration_id):
    result = build([migration()], {migration_id: {"status": status, "sha256": "a" * 64}})
    assert result["status"] == "blocked"
    assert any(item["action"] == "BLOCKED_LEDGER_STATE" for item in result["items"])


def test_duplicate_migration_id_is_rejected_before_planning():
    with pytest.raises(ValueError, match="MIGRATION_ID_DUPLICATE"):
        build([migration(), migration()], {})


def test_manifest_equivalent_checksum_whitelist_cannot_hide_drift():
    result = build([migration(equivalentSha256=["b" * 64])],
                   {"m1": {"status": "APPLIED", "sha256": "b" * 64}})
    assert result["status"] == "blocked"
    assert result["items"][0]["action"] == "BLOCKED_CHECKSUM_MISMATCH"


def bound(path, target, executor=PLANNER):
    return planner.build_target_bound_plan(path, target, executor_path=executor,
        target_environment=target["targetEnvironment"], publish_scope="app-release")


def verify(plan, path, target, executor=PLANNER):
    return planner.verify_target_bound_plan(plan, path, target, executor_path=executor,
        target_environment=target["targetEnvironment"], publish_scope="app-release")


def invoke_cli(path, target, output, *, verify_plan=False, extra=()):
    state = output.with_name(output.stem + "-state.json")
    state.write_text(json.dumps(target), encoding="utf-8")
    args = [sys.executable, "-X", "utf8", str(PLANNER), "--manifest", str(path),
        "--target-state", str(state), "--target-environment", target["targetEnvironment"],
        "--publish-scope", "app-release", "--executor", str(PLANNER), "--output", str(output), *extra]
    if verify_plan:
        args.append("--verify")
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def test_same_package_three_baselines_api_and_cli_are_deterministic(tmp_path):
    path, manifest = package(tmp_path)
    package_before = {item.relative_to(path.parent).as_posix(): item.read_bytes() for item in path.parent.rglob("*") if item.is_file()}
    digests = set()
    for environment, count, expected in [("test", 3, ["m4"]), ("prod", 1, ["m2", "m3", "m4"]), ("backup", 2, ["m3", "m4"])]:
        target = snapshot(manifest, count, environment)
        first = bound(path, target)
        assert bound(path, target) == first
        assert first["status"] == "passed"
        assert [item["migrationId"] for item in first["items"] if item["action"] == "APPLY"] == expected
        assert first["binding"]["capturedAt"] == target["capturedAt"]
        assert verify(first, path, target)["planDigest"] == first["planDigest"]
        digests.add((first["binding"]["packageDigest"], first["binding"]["manifestDigest"]))
        output = tmp_path / f"plan-{environment}.json"
        for _ in range(2):
            result = invoke_cli(path, target, output)
            assert result.returncode == 0, result.stderr
            assert json.loads(output.read_text(encoding="utf-8")) == first
        assert invoke_cli(path, target, output, verify_plan=True).returncode == 0
    assert len(digests) == 1
    assert package_before == {item.relative_to(path.parent).as_posix(): item.read_bytes() for item in path.parent.rglob("*") if item.is_file()}


@pytest.mark.parametrize("field", ["host", "machine", "database", "serverUuid", "environment", "schema", "ledger", "ledgerMetadata", "config", "mount", "platform"])
def test_fresh_target_drift_refuses_previous_plan(tmp_path, field):
    path, manifest = package(tmp_path)
    original = snapshot(manifest, 1)
    plan = bound(path, original)
    changed = deepcopy(original)
    if field == "host":
        changed["hostIdentity"]["host"] = "other-host"
    elif field == "machine":
        changed["hostIdentity"]["machineId"] = "other-machine"
    elif field == "database":
        changed["databaseIdentity"]["name"] = changed["nonSecretConfig"]["MYSQL_DATABASE"] = "other_database"
    elif field == "serverUuid":
        changed["databaseIdentity"]["serverUuid"] = "00000000-0000-4000-8000-000000000004"
    elif field == "environment":
        changed["targetEnvironment"] = "prod"
    elif field == "schema":
        changed["schemaEvidence"]["extraTable"] = "unexpected"
    elif field == "ledger":
        changed["migrationLedger"][0]["status"] = "FAILED"
    elif field == "ledgerMetadata":
        changed["migrationLedger"][0]["operationId"] = "different-operation"
    elif field == "config":
        changed["nonSecretConfig"]["IMAGE_TAG"] = "another-running-version"
    elif field == "mount":
        changed["persistentMounts"][0]["identity"] = "other-filesystem"
    else:
        changed["platformPrerequisites"][0]["actualSha256"] = changed["platformPrerequisites"][0]["approvedSha256"] = "e" * 64
    with pytest.raises(ValueError, match="PLAN_INPUT_DRIFT"):
        verify(plan, path, changed)
    output = tmp_path / "original-plan.json"
    output.write_text(json.dumps(plan), encoding="utf-8")
    before = output.read_bytes()
    result = invoke_cli(path, changed, output, verify_plan=True)
    assert result.returncode != 0 and "PLAN_INPUT_DRIFT" in result.stderr
    assert output.read_bytes() == before


@pytest.mark.parametrize("field", ["packageDigest", "releaseTag", "manifest", "sql", "executor", "planner"])
def test_package_or_engine_identity_change_refuses_previous_plan(tmp_path, field, monkeypatch):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    executor = tmp_path / "executor.ps1"
    executor.write_text("# actual executor one", encoding="utf-8")
    plan = bound(path, target, executor)
    if field == "packageDigest":
        manifest["packageDigest"] = "f" * 64
    elif field == "releaseTag":
        manifest["releaseTag"] = "another-release"
    elif field == "manifest":
        manifest["annotation"] = "changed"
    elif field == "sql":
        (path.parent / "required-sql/m4.sql").write_text("DROP TABLE task_m1;", encoding="utf-8")
    elif field == "executor":
        executor.write_text("# actual executor two", encoding="utf-8")
    else:
        monkeypatch.setattr(planner, "planner_identity", lambda: "f" * 64)
    if field in {"packageDigest", "releaseTag", "manifest"}:
        path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="PLAN_INPUT_DRIFT|PACKAGE_.*MISMATCH"):
        verify(plan, path, target, executor)


@pytest.mark.parametrize("field", ["action", "order", "status", "binding", "capturedAt", "unknownAction", "extra"])
@pytest.mark.parametrize("recompute_digest", [False, True])
def test_tampered_plan_never_executes(tmp_path, field, recompute_digest):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    plan = bound(path, target)
    if field == "action":
        plan["items"][0]["action"] = "APPLY"
    elif field == "order":
        plan["items"].reverse()
    elif field == "status":
        plan["status"] = "blocked"
    elif field == "binding":
        plan.pop("binding")
    elif field == "capturedAt":
        plan["binding"]["capturedAt"] = "invalid-time"
    elif field == "unknownAction":
        plan["items"][1]["action"] = "TRUST_ME"
    else:
        plan["unexpected"] = True
    if recompute_digest:
        plan["planDigest"] = evidence_digest({key: val for key, val in plan.items() if key != "planDigest"})
    calls = []
    with pytest.raises(ReleaseDeployExecutionError):
        execute_preflight_apply_migrations(plan, manifest_path=path, target_snapshot=target,
            executor_path=PLANNER, target_environment="test", execute_sql=lambda item: calls.append("SQL"),
            record_state=lambda *args: calls.append("ledger"))
    assert calls == []


def test_time_only_recollection_preserves_actions_and_allows_locked_verification(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 2)
    first = bound(path, target)
    target["capturedAt"] = "2026-09-25T08:01:00Z"
    newer = verify(first, path, target)
    assert newer["items"] == first["items"]
    assert newer["binding"]["capturedAt"] == target["capturedAt"]
    assert newer["binding"]["fingerprints"] == first["binding"]["fingerprints"]


def test_executor_runs_only_apply_without_replacing_successful_history(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 2)
    plan = bound(path, target)
    calls = []
    summary = execute_preflight_apply_migrations(plan, manifest_path=path, target_snapshot=target,
        executor_path=PLANNER, target_environment="test",
        execute_sql=lambda item: calls.append((item["migrationId"], "SQL")),
        record_state=lambda item, status, error: calls.append((item["migrationId"], status)))
    assert summary == {"applied": ["m3", "m4"], "skipped": ["m1", "m2"]}
    assert calls == [(migration_id, action) for migration_id in ["m3", "m4"] for action in ["RUNNING", "SQL", "APPLIED"]]


@pytest.mark.parametrize("field", ["schemaVersion", "capturedAt", "hostIdentity", "databaseIdentity", "schemaEvidence", "migrationLedgerComplete", "migrationLedger", "nonSecretConfig", "persistentMounts", "platformPrerequisites"])
def test_missing_target_evidence_is_not_inferred(tmp_path, field):
    path, manifest = package(tmp_path)
    target = snapshot(manifest)
    target.pop(field)
    with pytest.raises(ValueError, match="TARGET_"):
        bound(path, target)


def test_duplicate_ledger_rows_and_incomplete_capture_fail_closed(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    target["migrationLedger"].append(deepcopy(target["migrationLedger"][0]))
    with pytest.raises(ValueError, match="LEDGER_ID_DUPLICATE"):
        bound(path, target)
    target = snapshot(manifest)
    target["migrationLedgerComplete"] = False
    with pytest.raises(ValueError, match="TARGET_COMPLETE_LEDGER_REQUIRED"):
        bound(path, target)


@pytest.mark.parametrize("secret_config", [{"MYSQL_PASSWORD": "example-secret"}, {"MINIO_ENDPOINT": "http://admin:example-secret@storage:9000"}, {"MINIO_ENDPOINT": "http://storage:9000?token=example-secret"}])
def test_secret_config_is_rejected_without_leaking_value(tmp_path, secret_config):
    path, manifest = package(tmp_path)
    target = snapshot(manifest)
    target["nonSecretConfig"].update(secret_config)
    output = tmp_path / "plan.json"
    result = invoke_cli(path, target, output)
    assert result.returncode != 0
    assert "example-secret" not in result.stdout + result.stderr
    assert not output.exists()


@pytest.mark.parametrize("bad_platform", [[], [{"toolId": "dcc-codex", "path": "/usr/bin/codex", "approvedSha256": "e" * 64, "actualSha256": "d" * 64, "executable": True}], [{"toolId": "dcc-codex", "path": "/usr/bin/codex", "approvedSha256": "d" * 64, "actualSha256": "d" * 64, "executable": False}]])
def test_missing_or_unapproved_platform_identity_blocks(tmp_path, bad_platform):
    path, manifest = package(tmp_path)
    target = snapshot(manifest)
    target["platformPrerequisites"] = bad_platform
    with pytest.raises(ValueError, match="TARGET_PLATFORM_"):
        bound(path, target)


@pytest.mark.parametrize("mutation,expected", [("cycle", "MIGRATION_DEPENDENCY_CYCLE"), ("duplicate", "MIGRATION_ID_DUPLICATE"), ("missing", "BLOCKED_DEPENDENCY_MISSING"), ("excluded", "BLOCKED_DEPENDENCY_MISSING")])
def test_dependency_faults_cannot_form_an_executable_plan(mutation, expected):
    migrations = [migration("m1"), migration("m2", dependsOn=["m1"])]
    if mutation == "cycle":
        migrations[0]["dependsOn"] = ["m2"]
    elif mutation == "duplicate":
        migrations.append(migration("m1"))
    elif mutation == "missing":
        migrations[1]["dependsOn"] = ["not-in-package"]
    else:
        migrations[0]["allowedEnvironments"] = ["prod"]
    if mutation in {"cycle", "duplicate"}:
        with pytest.raises(ValueError, match=expected):
            build(migrations, {})
    else:
        result = build(migrations, {})
        assert result["status"] == "blocked"
        assert result["items"][-1]["action"] == expected


def test_explicit_prospective_cli_requires_no_final_package_digest(tmp_path):
    path, manifest = package(tmp_path)
    manifest.pop("artifacts")
    manifest.pop("packageDigest")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    state = tmp_path / "ledger.json"
    state.write_text("{}", encoding="utf-8")
    output = tmp_path / "prospective.json"
    result = subprocess.run([sys.executable, "-X", "utf8", str(PLANNER), "--mode", "prospective",
        "--manifest", str(path), "--target-state", str(state), "--target-environment", "test",
        "--publish-scope", "app-release", "--output", str(output)],
        capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["planKind"] == "prospective" and "binding" not in plan
    with pytest.raises(ValueError, match="TARGET_BOUND_PLAN_REQUIRED"):
        verify(plan, path, snapshot(manifest))


def test_cli_cannot_write_plan_into_immutable_package(tmp_path):
    path, manifest = package(tmp_path)
    output = path.parent / "plan.json"
    # Input capture itself is outside the immutable package.
    state = tmp_path / "state.json"
    state.write_text(json.dumps(snapshot(manifest)), encoding="utf-8")
    result = subprocess.run([sys.executable, "-X", "utf8", str(PLANNER), "--manifest", str(path),
        "--target-state", str(state), "--target-environment", "test", "--publish-scope", "app-release",
        "--executor", str(PLANNER), "--output", str(output)], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0 and "PLAN_OUTPUT_INSIDE_PACKAGE" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("status", ["SKIPPED_ALREADY_APPLIED", "SKIPPED_ENV_NOT_ALLOWED", "SKIPPED_SCOPE_EXCLUDED", "SKIPPED_IMMUTABLE"])
def test_recognized_skip_history_does_not_disguise_applied_proof(status):
    result = build([migration()], {"m1": {"status": status, "sha256": "a" * 64}})
    assert result["status"] == "passed"
    assert result["items"][0]["action"] == ("SKIP_ALREADY_APPLIED" if status == "SKIPPED_ALREADY_APPLIED" else "APPLY")


@pytest.mark.parametrize("status", ["FAILED", "RUNNING", "UNRECOGNIZED"])
def test_supersession_cannot_erase_unresolved_history(status):
    result = build([migration("legacy"), migration("successor", requiresTargetPreflight=True, supersedes=["legacy"])],
                   {"legacy": {"status": status, "sha256": "a" * 64}})
    assert result["status"] == "blocked"
    assert result["items"][0]["action"] == "BLOCKED_LEDGER_STATE"


def test_metadata_equivalence_requires_actual_unchanged_executable_sql(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    sql = (path.parent / "required-sql/m1.sql").read_bytes()
    target["migrationLedger"][0]["sha256"] = hashlib.sha256(planner._sql_without_release_metadata(sql)).hexdigest()
    result = bound(path, target)
    assert result["status"] == "passed"
    assert result["items"][0]["action"] == "SKIP_ALREADY_APPLIED"
    target["migrationLedger"][0]["sha256"] = hashlib.sha256(b"CREATE TABLE task_m1 (id BIGINT);\n").hexdigest()
    result = bound(path, target)
    assert result["status"] == "blocked"
    assert result["items"][0]["action"] == "BLOCKED_CHECKSUM_MISMATCH"


def test_failed_plan_is_written_as_evidence_but_never_authorizes_execution(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    target["migrationLedger"][0]["status"] = "FAILED"
    output = tmp_path / "blocked.json"
    result = invoke_cli(path, target, output)
    assert result.returncode == 2
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["status"] == "blocked"
    assert plan["items"][0]["action"] == "BLOCKED_LEDGER_STATE"
    calls = []
    with pytest.raises(ReleaseDeployExecutionError, match="PLAN_BLOCKED"):
        execute_preflight_apply_migrations(plan, manifest_path=path, target_snapshot=target,
            executor_path=PLANNER, target_environment="test", execute_sql=lambda item: calls.append("sql"),
            record_state=lambda *args: calls.append("ledger"))
    assert calls == []


def test_ledger_and_mount_observation_order_does_not_change_fingerprint(tmp_path):
    _, manifest = package(tmp_path)
    target = snapshot(manifest, 3)
    target["persistentMounts"].append({"role": "minio", "type": "volume", "source": "task-minio", "destination": "/data", "identity": "volume-task"})
    first = normalize_target_snapshot(target, target_environment="test")
    target["migrationLedger"].reverse()
    target["persistentMounts"].reverse()
    second = normalize_target_snapshot(target, target_environment="test")
    assert fingerprint_target_snapshot(first) == fingerprint_target_snapshot(second)


def test_duplicate_json_keys_cannot_mask_ledger_or_target_identity(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"migrationLedger": [{"migrationId": "m1", "status": "FAILED", "status": "APPLIED"}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON_DUPLICATE_KEY"):
        planner._load_json(path)


def snapshot_json_with_duplicate_field(target, field):
    field_values = {
        "status": ("status", "APPLIED", "FAILED"),
        "same_status": ("status", "APPLIED", "APPLIED"),
        "migrationLedger": ("migrationLedger", target["migrationLedger"],
                            [{**target["migrationLedger"][0], "status": "FAILED"}]),
        "host": ("host", target["hostIdentity"]["host"], "unapproved-host"),
        "serverUuid": ("serverUuid", target["databaseIdentity"]["serverUuid"],
                       "00000000-0000-4000-8000-000000000099"),
    }
    name, current, previous = field_values[field]
    original = f'{json.dumps(name)}: {json.dumps(current)}'
    text = json.dumps(target)
    assert text.count(original) == 1
    return text.replace(original, f'{json.dumps(name)}: {json.dumps(previous)}, {original}', 1)


@pytest.mark.parametrize("field", ["status", "same_status", "migrationLedger", "host", "serverUuid"])
def test_public_collector_rejects_duplicate_json_before_planning_or_execution(tmp_path, field):
    path, manifest = package(tmp_path)
    target_path = tmp_path / "target-state.json"
    target_path.write_text(snapshot_json_with_duplicate_field(snapshot(manifest, 1), field), encoding="utf-8")
    calls = []

    with pytest.raises(TargetStateCollectionError, match="JSON_DUPLICATE_KEY"):
        target = collect_target_state(tmp_path, target_environment="test")
        calls.append("plan")
        plan = bound(path, target)
        execute_preflight_apply_migrations(plan, manifest_path=path, target_snapshot=target,
            executor_path=PLANNER, target_environment="test",
            execute_sql=lambda item: calls.append("sql"), record_state=lambda *args: calls.append("ledger"))

    assert calls == []


@pytest.mark.parametrize("field", ["status", "same_status", "migrationLedger", "host", "serverUuid"])
def test_deploy_cli_rejects_duplicate_target_json_before_writing_plan(tmp_path, field):
    path, manifest = package(tmp_path)
    target_path = tmp_path / "target-state.json"
    target_path.write_text(snapshot_json_with_duplicate_field(snapshot(manifest, 1), field), encoding="utf-8")
    output = tmp_path / "plan.json"
    result = subprocess.run([sys.executable, "-X", "utf8", str(PLANNER), "--manifest", str(path),
        "--target-state", str(target_path), "--target-environment", "test", "--publish-scope", "app-release",
        "--executor", str(PLANNER), "--output", str(output)], capture_output=True, text=True, encoding="utf-8")

    assert result.returncode != 0
    assert "JSON_DUPLICATE_KEY" in result.stderr
    assert not output.exists()


def test_public_collector_valid_snapshot_preserves_bound_plan_contract(tmp_path):
    path, manifest = package(tmp_path)
    target = snapshot(manifest, 1)
    target_path = tmp_path / "target-state.json"
    target_path.write_text(json.dumps(target), encoding="utf-8")

    collected = collect_target_state(tmp_path, target_environment="test")
    assert collected == normalize_target_snapshot(target, target_environment="test")
    plan = bound(path, collected)
    assert plan == bound(path, target)
    assert plan["status"] == "passed"
    assert plan["items"][0]["action"] == "SKIP_ALREADY_APPLIED"
    assert [item["migrationId"] for item in plan["items"] if item["action"] == "APPLY"] == ["m2", "m3", "m4"]
    assert verify(plan, path, collected) == plan
