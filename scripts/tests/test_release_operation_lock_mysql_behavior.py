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


def test_mysql_lock_release_requires_exact_executor_and_lease_owner() -> None:
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
  ('test', 'test-release-a', 'release-a', 'RUNNING', NOW(),
   'HOST-A', '111', 'operator@HOST-A', 'lease-a', NOW(),
   'release-system', NOW(), 'release-system', NOW());
UPDATE infra_release_operation_lock
SET status='FAILED', finished_at=NOW(), updater='release-system', update_time=NOW()
WHERE target_environment='test'
  AND operation_id='test-release-a'
  AND status='RUNNING'
  AND executor_host='HOST-A'
  AND executor_pid='111'
  AND executor_identity='other@HOST-A'
  AND lease_token='lease-a';
SELECT ROW_COUNT();
""",
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("0")
        assert _query(database, "SELECT status FROM infra_release_operation_lock;") == "RUNNING"
        result = _mysql(
            """
UPDATE infra_release_operation_lock
SET status='FAILED', finished_at=NOW(), updater='release-system', update_time=NOW()
WHERE target_environment='test'
  AND operation_id='test-release-a'
  AND status='RUNNING'
  AND executor_host='HOST-A'
  AND executor_pid='111'
  AND executor_identity='operator@HOST-A'
  AND lease_token='lease-a';
SELECT ROW_COUNT();
""",
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("1")
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
