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


def test_publish_script_runs_schema_only_rehearsal_before_maven():
    script = (Path(__file__).resolve().parents[2] / "ops/deploy/publish-int-ruoyi.ps1").read_text(encoding="utf-8")
    rehearsal = script.index("Invoke-BuildReleaseSchemaOnlyMigrationRehearsal")
    maven = script.index("Info 'Building backend jar'")
    assert rehearsal < maven
    assert "--no-data" in script
    assert "release_schema_rehearsal.py" in script
    assert "--migration-list" in script
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
    captured: dict[str, object] = {}

    def fake_rehearsal(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "passed"}

    monkeypatch.setattr(release_schema_rehearsal, "run_schema_rehearsal", fake_rehearsal)

    result = release_schema_rehearsal.main([
        "--mysql-image", "mysql@sha256:" + "a" * 64,
        "--schema", str(schema),
        "--migration-list", str(migration_list),
        "--output", str(output),
    ])

    assert result == 0
    assert captured["migration_paths"] == migration_paths


@pytest.mark.parametrize("payload", ["{}", "[]", '["001.sql", 2]'])
def test_main_rejects_invalid_json_migration_list(
    tmp_path: Path,
    payload: str,
):
    migration_list = tmp_path / "migration-paths.json"
    migration_list.write_text(payload, encoding="utf-8")

    with pytest.raises(RehearsalError):
        release_schema_rehearsal.main([
            "--mysql-image", "mysql@sha256:" + "a" * 64,
            "--schema", str(tmp_path / "schema.sql"),
            "--migration-list", str(migration_list),
            "--output", str(tmp_path / "report.json"),
        ])
