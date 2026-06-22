import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def test_release_sql_contract_gate_blocks_duplicate_system_menu_ids(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    first_sql = sql_root / "20260622_feature_a.sql"
    first_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'A', 0);\n",
        encoding="utf-8",
    )
    second_sql = sql_root / "20260622_feature_b.sql"
    second_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260622_feature_a; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'B', 0);\n",
        encoding="utf-8",
    )

    try:
        gate.assert_release_sql_contracts([first_sql, second_sql])
    except gate.ReleaseSqlContractError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected duplicate system_menu.id conflict")

    assert "duplicate system_menu.id detected across release SQL history" in message
    assert "900285" in message
    assert "20260622_feature_a.sql" in message
    assert "20260622_feature_b.sql" in message


def test_migration_policy_gate_passes_unique_system_menu_ids(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    first_sql = sql_root / "20260622_feature_a.sql"
    first_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'A', 0);\n",
        encoding="utf-8",
    )
    second_sql = sql_root / "20260622_feature_b.sql"
    second_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260622_feature_a; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900286, 'B', 0);\n",
        encoding="utf-8",
    )

    report = policy_gate.run_migration_policy_gate(sql_root)

    assert report["status"] == "passed"
    assert report["migrationCount"] == 2


def test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    sql_path = sql_root / "20260520_system_nas_management_menu.sql"
    sql_path.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=low\n"
        "INSERT INTO `system_menu` (`id`, `name`, `parent_id`) VALUES\n"
        "  (5900, 'NAS 管理', 1)\n"
        "ON DUPLICATE KEY UPDATE\n"
        "  `name` = VALUES(`name`),\n"
        "  `parent_id` = VALUES(`parent_id`);\n",
        encoding="utf-8",
    )

    gate.assert_release_sql_contracts([sql_path])


def test_publish_script_runs_sql_preflight_before_backend_build() -> None:
    script = read_publish_script()

    for expected in (
        "Invoke-ReleaseMigrationPolicyGate",
        "$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts",
        "Info 'Building backend jar'",
    ):
        assert expected in script

    required_sql_index = script.index("$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts")
    gate_index = script.index("Invoke-ReleaseMigrationPolicyGate", required_sql_index)
    backend_build_index = script.index("Info 'Building backend jar'")
    assert required_sql_index < gate_index < backend_build_index
