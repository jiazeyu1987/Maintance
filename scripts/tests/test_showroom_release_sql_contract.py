import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def test_publish_script_includes_showroom_award_required_sql_contract() -> None:
    script = read_publish_script()

    for expected in (
        "function Get-ReleaseDatabaseSqlRoots",
        "RelativePath = 'sql/showroom'",
        "Root = Join-Path $backendRepo 'sql\\showroom'",
        "'20260606_showroom_hall_product_canvas_layout.sql'",
        "'20260613_showroom_award_and_hall_item_schema.sql'",
        "function Read-ReleaseMigrationMetadata",
        "--file-prefix",
        "--sql-file",
        "sourcePath = $relativePath",
        "type = [string]$metadata.type",
        "allowedEnvironments = @($metadata.allowedEnvironments)",
        "dependsOn = @($metadata.dependsOn)",
        "riskLevel = [string]$metadata.riskLevel",
    ):
        assert expected in script


def test_publish_script_checks_showroom_award_schema_before_backend_start() -> None:
    script = read_publish_script()

    for expected in (
        "function Assert-RemoteShowroomAwardSchemaReady",
        "SHOWROOM_AWARD_SCHEMA_MISSING",
        "showroom_award",
        "showroom_award_revision",
        "showroom_hall_item",
        "uk_showroom_award_code",
        "uk_showroom_award_revision_no",
        "idx_showroom_award_revision_award",
        "uk_showroom_hall_item",
        "idx_showroom_hall_item_order",
        "idx_showroom_hall_item_item",
    ):
        assert expected in script

    required_sql_index = script.index("Invoke-RequiredDatabaseSqlScripts")
    showroom_schema_index = script.index("Assert-RemoteShowroomAwardSchemaReady", required_sql_index)
    service_start_index = script.index("Starting application services on the $PublishTargetName server")
    assert required_sql_index < showroom_schema_index < service_start_index


def test_migration_policy_gate_supports_explicit_showroom_sql_file(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "showroom"
    sql_root.mkdir(parents=True)
    layout_sql = sql_root / "20260606_showroom_hall_product_canvas_layout.sql"
    layout_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=schema; riskLevel=medium\n"
        "ALTER TABLE showroom_hall_product ADD COLUMN layout_x decimal(8,6) DEFAULT NULL;\n",
        encoding="utf-8",
    )
    award_sql = sql_root / "20260613_showroom_award_and_hall_item_schema.sql"
    award_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260606_showroom_hall_product_canvas_layout; type=schema; riskLevel=medium\n"
        "CREATE TABLE IF NOT EXISTS showroom_award (id bigint NOT NULL);\n",
        encoding="utf-8",
    )
    (sql_root / "20260699_unrelated_showroom_experiment.sql").write_text(
        "-- release-migration: allowedEnvironments=test; dependsOn=; type=schema; riskLevel=low\n"
        "CREATE TABLE IF NOT EXISTS unrelated_showroom_experiment (id bigint NOT NULL);\n",
        encoding="utf-8",
    )

    report = policy_gate.run_migration_policy_gate(
        sql_root,
        sql_paths=[layout_sql, award_sql],
        file_prefix="sql/showroom",
    )

    assert report["status"] == "passed"
    assert report["migrationCount"] == 2
    assert [migration["file"] for migration in report["migrations"]] == [
        "sql/showroom/20260606_showroom_hall_product_canvas_layout.sql",
        "sql/showroom/20260613_showroom_award_and_hall_item_schema.sql",
    ]
    assert report["migrations"][1]["dependsOn"] == ["20260606_showroom_hall_product_canvas_layout"]
