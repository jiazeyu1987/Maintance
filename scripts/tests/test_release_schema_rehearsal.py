import json
from pathlib import Path

import pytest

from ops.release import release_schema_rehearsal
from ops.release.release_schema_rehearsal import RehearsalError, run_schema_rehearsal


class FakeRunner:
    def __init__(self, fail_contains: str | None = None):
        self.calls: list[tuple[list[str], bytes | None]] = []
        self.fail_contains = fail_contains

    def __call__(self, args: list[str], stdin: bytes | None = None) -> str:
        self.calls.append((args, stdin))
        joined = " ".join(args)
        if self.fail_contains and self.fail_contains in joined:
            raise RehearsalError("fixture failure")
        if "mysqladmin" in joined:
            return "mysqld is alive"
        return ""


def _write_preflight(path: Path, migrations: list[Path], apply_names: set[str] | None = None) -> None:
    selected = apply_names if apply_names is not None else {migration.name for migration in migrations}
    path.write_text(
        json.dumps({
            "schemaVersion": "release-build-preflight/v1",
            "status": "passed",
            "targetEnvironment": "test",
            "publishScope": "app-release",
            "planner": {
                "status": "passed",
                "items": [
                    {
                        "migrationId": migration.stem,
                        "file": f"required-sql/{migration.name}",
                        "type": "schema",
                        "requiresTargetPreflight": False,
                        "action": "APPLY" if migration.name in selected else "SKIP_ALREADY_APPLIED",
                    }
                    for migration in migrations
                ],
            },
        }),
        encoding="utf-8",
    )


def test_schema_only_rehearsal_uses_explicit_tcp_applies_twice_and_cleans(tmp_path: Path):
    schema = tmp_path / "schema.sql"
    migration = tmp_path / "001.sql"
    schema.write_text("CREATE TABLE t(id BIGINT PRIMARY KEY);\n", encoding="utf-8")
    migration.write_text("ALTER TABLE t ADD COLUMN name VARCHAR(20);\n", encoding="utf-8")
    runner = FakeRunner()

    report = run_schema_rehearsal(
        mysql_image="mysql@sha256:" + "a" * 64,
        schema_path=schema,
        migration_paths=[migration],
        runner=runner,
        container_name="release-rehearsal-fixture",
    )

    commands = [" ".join(args) for args, _ in runner.calls]
    assert report["status"] == "passed"
    assert commands[0].startswith("docker run --detach --name release-rehearsal-fixture")
    assert commands[0].endswith("--skip-log-bin --lower_case_table_names=1")
    assert sum(
        "mysql --protocol=TCP -h127.0.0.1" in command and stdin is not None
        for command, (_, stdin) in zip(commands, runner.calls)
    ) == 3
    assert commands[-1] == "docker rm --force release-rehearsal-fixture"


def test_schema_only_rehearsal_cleans_container_on_migration_failure(tmp_path: Path):
    schema = tmp_path / "schema.sql"
    migration = tmp_path / "001.sql"
    schema.write_text("CREATE TABLE t(id BIGINT PRIMARY KEY);\n", encoding="utf-8")
    migration.write_text("BROKEN;\n", encoding="utf-8")
    runner = FakeRunner(fail_contains="mysql --protocol=TCP")

    with pytest.raises(RehearsalError):
        run_schema_rehearsal(
            mysql_image="mysql@sha256:" + "a" * 64,
            schema_path=schema,
            migration_paths=[migration],
            runner=runner,
            container_name="release-rehearsal-failure",
        )

    assert " ".join(runner.calls[-1][0]) == "docker rm --force release-rehearsal-failure"


def test_schema_only_rehearsal_reports_failing_migration_and_pass(tmp_path: Path):
    schema = tmp_path / "schema.sql"
    migration = tmp_path / "001.sql"
    schema.write_text("CREATE TABLE t(id BIGINT PRIMARY KEY);\n", encoding="utf-8")
    migration.write_text("BROKEN;\n", encoding="utf-8")

    def fail_migration(args: list[str], stdin: bytes | None = None) -> str:
        if stdin and b"BROKEN;" in stdin:
            raise RehearsalError("fixture migration failure")
        return ""

    with pytest.raises(RehearsalError, match=r"001\.sql.*pass 1"):
        run_schema_rehearsal(
            mysql_image="mysql@sha256:" + "a" * 64,
            schema_path=schema,
            migration_paths=[migration],
            runner=fail_migration,
            container_name="release-rehearsal-reporting",
        )


def test_publish_script_runs_schema_only_rehearsal_before_maven():
    script = (Path(__file__).resolve().parents[2] / "ops/deploy/publish-int-ruoyi.ps1").read_text(encoding="utf-8")
    rehearsal = script.index("Invoke-BuildReleaseSchemaOnlyMigrationRehearsal")
    maven = script.index("Info 'Building backend jar'")
    assert rehearsal < maven
    assert "--no-data" in script
    assert "release_schema_rehearsal.py" in script
    assert "--migration-list" in script
    assert "--preflight-evidence" in script
    assert "$argumentList += @('--migration', $migrationPath)" not in script


def test_main_reads_migrations_from_json_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    schema = tmp_path / "schema.sql"
    output = tmp_path / "report.json"
    migration_list = tmp_path / "migration-paths.json"
    migration_paths = [tmp_path / "001.sql", tmp_path / "002.sql"]
    migration_list.write_text(
        json.dumps([str(path) for path in migration_paths]),
        encoding="utf-8",
    )
    preflight = tmp_path / "build-preflight-evidence.json"
    _write_preflight(preflight, migration_paths, {"002.sql"})
    captured: dict[str, object] = {}

    def fake_rehearsal(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "passed"}

    monkeypatch.setattr(release_schema_rehearsal, "run_schema_rehearsal", fake_rehearsal)

    result = release_schema_rehearsal.main([
        "--mysql-image", "mysql@sha256:" + "a" * 64,
        "--schema", str(schema),
        "--migration-list", str(migration_list),
        "--preflight-evidence", str(preflight),
        "--output", str(output),
    ])

    assert result == 0
    assert captured["migration_paths"] == [migration_paths[1]]


def test_main_rejects_preflight_migration_set_mismatch(tmp_path: Path):
    migration = tmp_path / "001.sql"
    migration_list = tmp_path / "migration-paths.json"
    migration_list.write_text(json.dumps([str(migration)]), encoding="utf-8")
    preflight = tmp_path / "build-preflight-evidence.json"
    _write_preflight(preflight, [tmp_path / "002.sql"])

    with pytest.raises(RehearsalError, match="migration set"):
        release_schema_rehearsal.main([
            "--mysql-image", "mysql@sha256:" + "a" * 64,
            "--schema", str(tmp_path / "schema.sql"),
            "--migration-list", str(migration_list),
            "--preflight-evidence", str(preflight),
            "--output", str(tmp_path / "report.json"),
        ])


def test_main_includes_executable_data_and_target_preflight_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE t(id BIGINT PRIMARY KEY);\n", encoding="utf-8")
    migrations = [tmp_path / "001.sql", tmp_path / "002.sql", tmp_path / "003.sql"]
    migration_list = tmp_path / "migration-paths.json"
    migration_list.write_text(json.dumps([str(path) for path in migrations]), encoding="utf-8")
    preflight = tmp_path / "build-preflight-evidence.json"
    preflight.write_text(json.dumps({
        "schemaVersion": "release-build-preflight/v1",
        "status": "passed",
        "targetEnvironment": "test",
        "publishScope": "app-release",
        "planner": {
            "status": "passed",
            "items": [
                {"migrationId": "001", "file": "required-sql/001.sql", "type": "schema", "requiresTargetPreflight": False, "action": "APPLY"},
                {"migrationId": "002", "file": "required-sql/002.sql", "type": "data", "requiresTargetPreflight": True, "action": "APPLY"},
                {"migrationId": "003", "file": "required-sql/003.sql", "type": "schema", "requiresTargetPreflight": True, "action": "APPLY"},
            ],
        },
    }), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_rehearsal(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "passed"}

    monkeypatch.setattr(release_schema_rehearsal, "run_schema_rehearsal", fake_rehearsal)
    assert release_schema_rehearsal.main([
        "--mysql-image", "mysql@sha256:" + "a" * 64,
        "--schema", str(schema),
        "--migration-list", str(migration_list),
        "--preflight-evidence", str(preflight),
        "--output", str(tmp_path / "report.json"),
    ]) == 0
    assert captured["migration_paths"] == migrations


@pytest.mark.parametrize("payload", ["{}", "[]", '["001.sql", 2]'])
def test_main_rejects_invalid_json_migration_list(
    tmp_path: Path,
    payload: str,
):
    migration_list = tmp_path / "migration-paths.json"
    migration_list.write_text(payload, encoding="utf-8")
    preflight = tmp_path / "build-preflight-evidence.json"
    _write_preflight(preflight, [tmp_path / "001.sql"])

    with pytest.raises(RehearsalError):
        release_schema_rehearsal.main([
            "--mysql-image", "mysql@sha256:" + "a" * 64,
            "--schema", str(tmp_path / "schema.sql"),
            "--migration-list", str(migration_list),
            "--preflight-evidence", str(preflight),
            "--output", str(tmp_path / "report.json"),
        ])
