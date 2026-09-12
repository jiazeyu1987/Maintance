from pathlib import Path

import pytest

from ops.release.release_migration_preflight import MigrationPreflightError, run_migration_preflight, sha256_text


def _migration(**overrides):
    value = {
        "migrationId": "20260912_fixture",
        "file": "sql/mysql/20260912_fixture.sql",
        "type": "schema",
        "idempotent": True,
    }
    value.update(overrides)
    return value


def _target():
    return {"reference": "target-preflight/20260912.json", "sha256": "a" * 64, "readOnly": True}


def test_target_preflight_auto_derivation_missing_blocks_before_maven():
    with pytest.raises(MigrationPreflightError, match="TARGET_PREFLIGHT_MISSING"):
        run_migration_preflight([_migration(type="data")])


def test_target_preflight_directory_excluded_from_migration_scan():
    report = run_migration_preflight([_migration(migrationId="target-check", file="target-preflight/check.json")])
    assert report["migrations"] == []


def test_target_preflight_reference_or_digest_missing_blocks():
    with pytest.raises(MigrationPreflightError, match="TARGET_PREFLIGHT_INVALID"):
        run_migration_preflight([_migration(type="data", targetPreflight={"reference": "x", "readOnly": True})])


def test_migration_idempotency_duplicate_drop_check_blocks():
    with pytest.raises(MigrationPreflightError, match="MIGRATION_NOT_IDEMPOTENT"):
        run_migration_preflight([_migration(dropCheckCount=2)])


def test_schema_ledger_drift_missing_column_blocks():
    with pytest.raises(MigrationPreflightError, match="SCHEMA_LEDGER_DRIFT"):
        run_migration_preflight([_migration(schemaLedger={"expected": {"users": ["id", "name"]}, "actual": {"users": ["id"]}})])


def test_rehearsal_requires_explicit_tcp():
    with pytest.raises(MigrationPreflightError, match="MYSQL_CONNECTION_CONTRACT_INVALID"):
        run_migration_preflight([_migration(rehearsalConnection={"socket": "/var/run/mysql.sock"})])


def test_schema_data_dependency_requires_target_preflight():
    with pytest.raises(MigrationPreflightError, match="TARGET_PREFLIGHT_MISSING"):
        run_migration_preflight([_migration(dataDependency=True)])


def test_data_constraint_conflict_requires_target_preflight():
    migration = _migration(type="data", targetPreflight=_target())
    with pytest.raises(MigrationPreflightError, match="TARGET_PREFLIGHT_FAILED"):
        run_migration_preflight([migration], target_preflight_results={migration["migrationId"]: False})


def test_procedure_without_delimiter_blocks_parser():
    migration = _migration(migrationId="20260912_proc")
    with pytest.raises(MigrationPreflightError, match="SQL_DELIMITER_INVALID"):
        run_migration_preflight([migration], sql_by_id={migration["migrationId"]: "CREATE PROCEDURE p() BEGIN SELECT 1; END"})


def test_schema_requires_target_preflight_when_explicitly_marked():
    with pytest.raises(MigrationPreflightError, match="TARGET_PREFLIGHT_MISSING"):
        run_migration_preflight([_migration(requiresTargetPreflight=True)])
