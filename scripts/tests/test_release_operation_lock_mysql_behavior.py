from __future__ import annotations

import subprocess
import uuid


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
    return "release_lock_test_" + uuid.uuid4().hex[:12]


def _setup(database: str) -> None:
    result = _mysql(
        f"""
CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `{database}`;
CREATE TABLE infra_release_operation_lock (
  id bigint PRIMARY KEY AUTO_INCREMENT,
  target_environment varchar(32) NOT NULL,
  operation_id varchar(128) NOT NULL,
  release_tag varchar(128) NOT NULL,
  status varchar(32) NOT NULL,
  started_at datetime NOT NULL,
  finished_at datetime NULL,
  error_message varchar(1024) NULL,
  executor_host varchar(255) NULL,
  executor_pid varchar(64) NULL,
  executor_identity varchar(255) NULL,
  lease_token varchar(128) NULL,
  heartbeat_at datetime NULL,
  write_fence bigint NOT NULL DEFAULT 0,
  creator varchar(64) NOT NULL,
  create_time datetime NOT NULL,
  updater varchar(64) NOT NULL,
  update_time datetime NOT NULL,
  deleted bit(1) NOT NULL DEFAULT b'0',
  tenant_id bigint NOT NULL DEFAULT 1,
  UNIQUE KEY uk_release_lock_env (target_environment)
) ENGINE=InnoDB;
CREATE TABLE infra_release_migration (
  id bigint PRIMARY KEY AUTO_INCREMENT,
  target_environment varchar(32) NOT NULL,
  release_tag varchar(128) NOT NULL,
  status varchar(32) NOT NULL
) ENGINE=InnoDB;
"""
    )
    assert result.returncode == 0, result.stderr


def _drop(database: str) -> None:
    result = _mysql(f"DROP DATABASE IF EXISTS `{database}`;")
    assert result.returncode == 0, result.stderr


def _query(database: str, sql: str) -> str:
    result = _mysql(sql, database=database)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _recover_sql(
    *,
    operation_id: str,
    release_tag: str,
    executor_host: str,
    executor_pid: str,
    executor_identity: str,
    lease_token: str,
) -> str:
    return f"""
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
START TRANSACTION;
SELECT CASE
  WHEN NOT EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = '{operation_id}'
      AND release_tag = '{release_tag}'
      AND status = 'RUNNING'
      AND executor_host = '{executor_host}'
      AND executor_pid = '{executor_pid}'
      AND executor_identity = '{executor_identity}'
      AND lease_token = '{lease_token}'
  ) THEN 'RECOVER_BLOCKED_OWNERSHIP_MISMATCH'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_migration
    WHERE target_environment = 'test'
      AND release_tag = '{release_tag}'
      AND status IN ('RUNNING', 'APPLIED', 'FAILED')
  ) THEN 'RECOVER_BLOCKED_MIGRATION_EVIDENCE'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = '{operation_id}'
      AND status = 'RUNNING'
      AND heartbeat_at IS NOT NULL
      AND heartbeat_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
  ) THEN 'RECOVER_BLOCKED_ACTIVE_HEARTBEAT'
  ELSE 'RECOVER_ELIGIBLE'
END INTO @recovery_eligibility;
SELECT @recovery_eligibility;
UPDATE infra_release_operation_lock
SET status = 'FAILED',
    finished_at = NOW(),
    error_message = 'RECOVERED_BY_EXPLICIT_BUTTON_AFTER_LOCAL_TERMINAL_AND_ATOMIC_OWNERSHIP_CHECK',
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = 'test'
  AND operation_id = '{operation_id}'
  AND release_tag = '{release_tag}'
  AND status = 'RUNNING'
  AND executor_host = '{executor_host}'
  AND executor_pid = '{executor_pid}'
  AND executor_identity = '{executor_identity}'
  AND lease_token = '{lease_token}'
  AND (heartbeat_at IS NULL OR heartbeat_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE))
  AND @recovery_eligibility = 'RECOVER_ELIGIBLE';
SELECT CASE WHEN ROW_COUNT() = 1 THEN 'LOCK_RECOVERED' ELSE 'LOCK_RECOVERY_FAILED' END;
COMMIT;
"""


def test_mysql_lock_release_requires_exact_executor_and_lease_owner() -> None:
    database = _database()
    try:
        _setup(database)
        _mysql(
            """
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   creator, create_time, updater, update_time)
VALUES
  ('test', 'test-release-a', 'release-a', 'RUNNING', NOW(),
   'HOST-A', '111', 'operator@HOST-A', 'lease-a', DATE_SUB(NOW(), INTERVAL 31 MINUTE),
   'release-system', NOW(), 'release-system', NOW());
""",
            database=database,
        )
        result = _mysql(
            _recover_sql(
                operation_id="test-release-a",
                release_tag="release-a",
                executor_host="HOST-A",
                executor_pid="111",
                executor_identity="other@HOST-A",
                lease_token="lease-a",
            ),
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert "RECOVER_BLOCKED_OWNERSHIP_MISMATCH" in result.stdout
        assert "LOCK_RECOVERY_FAILED" in result.stdout
        assert _query(database, "SELECT status FROM infra_release_operation_lock;") == "RUNNING"
        result = _mysql(
            _recover_sql(
                operation_id="test-release-a",
                release_tag="release-a",
                executor_host="HOST-A",
                executor_pid="111",
                executor_identity="operator@HOST-A",
                lease_token="lease-a",
            ),
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert "RECOVER_ELIGIBLE" in result.stdout
        assert "LOCK_RECOVERED" in result.stdout
        assert _query(database, "SELECT status FROM infra_release_operation_lock;") == "FAILED"
    finally:
        _drop(database)


def test_mysql_write_fence_blocks_old_executor_after_reacquire() -> None:
    database = _database()
    try:
        _setup(database)
        result = _mysql(
            """
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   creator, create_time, updater, update_time)
VALUES
  ('test', 'test-release-old', 'release-old', 'RUNNING', NOW(),
   'HOST-A', '111', 'operator@HOST-A', 'lease-old', NOW(),
   'release-system', NOW(), 'release-system', NOW());
UPDATE infra_release_operation_lock
SET status='FAILED', finished_at=NOW(), updater='release-system', update_time=NOW()
WHERE target_environment='test'
  AND operation_id='test-release-old'
  AND status='RUNNING'
  AND executor_host='HOST-A'
  AND executor_pid='111'
  AND executor_identity='operator@HOST-A'
  AND lease_token='lease-old';
UPDATE infra_release_operation_lock
SET operation_id='test-release-new',
    release_tag='release-new',
    status='RUNNING',
    finished_at=NULL,
    executor_host='HOST-A',
    executor_pid='222',
    executor_identity='operator@HOST-A',
    lease_token='lease-new',
    heartbeat_at=NOW(),
    write_fence=write_fence + 1
WHERE target_environment='test'
  AND status <> 'RUNNING';
UPDATE infra_release_operation_lock
SET status='FAILED', finished_at=NOW(), updater='release-system', update_time=NOW()
WHERE target_environment='test'
  AND operation_id='test-release-old'
  AND status='RUNNING'
  AND executor_host='HOST-A'
  AND executor_pid='111'
  AND executor_identity='operator@HOST-A'
  AND lease_token='lease-old';
SELECT ROW_COUNT();
""",
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("0")
        assert _query(database, "SELECT operation_id, status, lease_token FROM infra_release_operation_lock;") == (
            "test-release-new\tRUNNING\tlease-new"
        )
    finally:
        _drop(database)
