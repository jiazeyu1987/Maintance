from __future__ import annotations

import re
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT.parent
    / "a"
    / "IntRuoyiBackend"
    / "sql"
    / "mysql"
    / "20260830_dcc_registration_certificate_notification_role_scope_backfill.sql"
)


def _mysql(script: str, database: str | None = None) -> subprocess.CompletedProcess[str]:
    args = [
        "docker",
        "exec",
        "-i",
        "-e",
        "MYSQL_PWD=123456",
        "int-ruoyi-mysql",
        "mysql",
        "-uroot",
        "--default-character-set=utf8mb4",
        "--batch",
        "--skip-column-names",
    ]
    if database:
        args.append(database)
    return subprocess.run(args, input=script, text=True, capture_output=True, check=False)


def _database() -> str:
    return "dcc_role_scope_test_" + uuid.uuid4().hex[:12]


def _schema(database: str, *, missing_role: bool = False, tenant_two_certificate: bool = False) -> str:
    role = "" if missing_role else "INSERT INTO system_role (id, tenant_id, status, deleted) VALUES (1001, 1, 0, b'0');"
    cert_tenant = 2 if tenant_two_certificate else 1
    return f"""
CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `{database}`;
CREATE TABLE infra_job (
  id bigint PRIMARY KEY AUTO_INCREMENT,
  handler_name varchar(128) NOT NULL,
  handler_param json NULL,
  deleted bit(1) NOT NULL DEFAULT b'0',
  updater varchar(64) NOT NULL DEFAULT '',
  update_time datetime NULL
) ENGINE=InnoDB;
CREATE TABLE dcc_registration_certificate (
  id bigint PRIMARY KEY,
  tenant_id bigint NOT NULL,
  owner_company_id bigint NOT NULL,
  status varchar(32) NOT NULL,
  deleted bit(1) NOT NULL DEFAULT b'0'
) ENGINE=InnoDB;
CREATE TABLE mdm_enterprise (
  id bigint PRIMARY KEY,
  tenant_id bigint NOT NULL,
  type varchar(32) NOT NULL,
  status varchar(32) NOT NULL,
  deleted bit(1) NOT NULL DEFAULT b'0'
) ENGINE=InnoDB;
CREATE TABLE system_role (
  id bigint PRIMARY KEY,
  tenant_id bigint NOT NULL,
  status tinyint NOT NULL,
  deleted bit(1) NOT NULL DEFAULT b'0'
) ENGINE=InnoDB;
CREATE TABLE mdm_role_company_scope (
  id bigint PRIMARY KEY AUTO_INCREMENT,
  role_id bigint NOT NULL,
  company_id bigint NOT NULL,
  status varchar(32) NOT NULL,
  revision int NOT NULL,
  creator varchar(64) NOT NULL,
  create_time datetime NOT NULL,
  updater varchar(64) NOT NULL,
  update_time datetime NOT NULL,
  deleted bit(1) NOT NULL DEFAULT b'0',
  tenant_id bigint NOT NULL
) ENGINE=InnoDB;
INSERT INTO infra_job (handler_name, handler_param, deleted, updater, update_time)
VALUES ('registrationCertificateReminderDailyJob',
        '{{"actorId":1,"roleIds":[1001]}}',
        b'0', 'seed', NOW());
INSERT INTO mdm_enterprise (id, tenant_id, type, status, deleted)
VALUES (200, {cert_tenant}, 'OWNED_COMPANY', 'ENABLE', b'0');
INSERT INTO dcc_registration_certificate (id, tenant_id, owner_company_id, status, deleted)
VALUES (300, {cert_tenant}, 200, 'ACTIVE', b'0');
{role}
"""


def _run_migration(database: str) -> subprocess.CompletedProcess[str]:
    migration = MIGRATION.read_text(encoding="utf-8")
    return _mysql(migration, database=database)


def _query(database: str, sql: str) -> str:
    result = _mysql(sql, database=database)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _drop(database: str) -> None:
    result = _mysql(f"DROP DATABASE IF EXISTS `{database}`;")
    assert result.returncode == 0, result.stderr


def test_notification_role_scope_migration_executes_idempotently_in_real_mysql() -> None:
    database = _database()
    try:
        setup = _mysql(_schema(database))
        assert setup.returncode == 0, setup.stderr
        first = _run_migration(database)
        assert first.returncode == 0, first.stderr
        assert _query(database, "SELECT COUNT(*) FROM mdm_role_company_scope;") == "1"
        assert _query(database, "SELECT handler_param FROM infra_job;") == '{"actorId": 1, "roleIds": [1001]}'
        second = _run_migration(database)
        assert second.returncode == 0, second.stderr
        assert _query(database, "SELECT COUNT(*) FROM mdm_role_company_scope;") == "1"
    finally:
        _drop(database)


def test_notification_role_scope_migration_fails_closed_and_rolls_back_missing_role() -> None:
    database = _database()
    try:
        setup = _mysql(_schema(database, missing_role=True))
        assert setup.returncode == 0, setup.stderr
        result = _run_migration(database)
        assert result.returncode != 0
        assert "notification role mapping" in (result.stderr + result.stdout).lower()
        assert _query(database, "SELECT COUNT(*) FROM mdm_role_company_scope;") == "0"
        assert _query(database, "SELECT handler_param FROM infra_job;") == '{"actorId": 1, "roleIds": [1001]}'
    finally:
        _drop(database)


def test_notification_role_scope_migration_keeps_tenant_scope_isolated() -> None:
    database = _database()
    try:
        setup = _mysql(_schema(database, tenant_two_certificate=True))
        assert setup.returncode == 0, setup.stderr
        result = _run_migration(database)
        assert result.returncode == 0, result.stderr
        assert _query(database, "SELECT COUNT(*) FROM mdm_role_company_scope;") == "0"
    finally:
        _drop(database)


def test_notification_role_scope_migration_has_no_permission_based_role_inference() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "json_arrayagg" not in sql
    assert "system_role_menu" not in sql
    assert "query-current permission cannot define notification recipients" in sql
    assert re.search(r"start\s+transaction", sql)
