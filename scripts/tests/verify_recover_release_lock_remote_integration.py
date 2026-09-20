from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECOVERY_SCRIPT = ROOT / "ops/deploy/recover-release-operation-lock.ps1"
SERVER_HOST = "172.30.30.58"
REMOTE_APP_DIR = "/opt/intruoyi/runtime"


def remote_mysql(database: str | None, sql: str) -> subprocess.CompletedProcess[str]:
    database_arg = f" '{database}'" if database else ""
    remote = f"""
set -eu
MYSQL_ROOT_PASSWORD=$(grep -E '^MYSQL_ROOT_PASSWORD=' '{REMOTE_APP_DIR}/.env' | head -n 1 | cut -d= -f2-)
test -n "$MYSQL_ROOT_PASSWORD"
export MYSQL_ROOT_PASSWORD
printf '%s' '{base64.b64encode(sql.encode('utf-8')).decode('ascii')}' | base64 -d | \
  docker exec -i -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot \
    --default-character-set=utf8mb4 --batch --skip-column-names{database_arg}
"""
    payload = base64.b64encode(remote.encode("utf-8")).decode("ascii")
    return subprocess.run(
        [
            "ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no", f"root@{SERVER_HOST}",
            f"PAYLOAD='{payload}'; printf '%s' \"$PAYLOAD\" | base64 -d | bash",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def run_recovery(database: str, release_tag: str, lease_token: str) -> subprocess.CompletedProcess[str]:
    computer = os.environ["COMPUTERNAME"]
    identity = f"{os.environ['USERNAME']}@{computer}"
    return subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RECOVERY_SCRIPT),
            "-ServerHost", SERVER_HOST,
            "-RemoteAppDir", REMOTE_APP_DIR,
            "-DatabaseName", database,
            "-ExpectedOperationId", f"test-{release_tag}",
            "-ExpectedReleaseTag", release_tag,
            "-ExpectedExecutorHost", computer,
            "-ExpectedExecutorPid", "2147483000",
            "-ExpectedExecutorIdentity", identity,
            "-ExpectedLeaseToken", lease_token,
            "-ExecutorTerminalState", "TERMINATED",
            "-ConfirmText", "RECOVER-TEST-LOCK",
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], step: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{step} failed: exit={result.returncode}, stderr={result.stderr.strip()}")


def main() -> int:
    suffix = uuid.uuid4().hex[:12]
    database = f"release_lock_it_{suffix}"
    release_tag = f"integration-{suffix}"
    lease_token = f"lease-{suffix}"
    computer = os.environ["COMPUTERNAME"]
    identity = f"{os.environ['USERNAME']}@{computer}"
    setup_sql = f"""
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
INSERT INTO infra_release_operation_lock (
  target_environment, operation_id, release_tag, status, started_at,
  executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
  creator, create_time, updater, update_time
) VALUES (
  'test', 'test-{release_tag}', '{release_tag}', 'RUNNING', NOW(),
  '{computer}', '2147483000', '{identity}', '{lease_token}', NOW(),
  'integration-test', NOW(), 'integration-test', NOW()
);
"""
    try:
        require_success(remote_mysql(None, setup_sql), "setup")

        active = run_recovery(database, release_tag, lease_token)
        if active.returncode == 0 or "RECOVER_BLOCKED_ACTIVE_HEARTBEAT" not in (active.stdout + active.stderr):
            raise AssertionError("active heartbeat did not block the actual recovery script")

        require_success(
            remote_mysql(database, "UPDATE infra_release_operation_lock SET heartbeat_at=DATE_SUB(NOW(), INTERVAL 31 MINUTE);"),
            "expire heartbeat",
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            attempts = list(executor.map(lambda _: run_recovery(database, release_tag, lease_token), range(2)))
        successes = [result for result in attempts if result.returncode == 0]
        failures = [result for result in attempts if result.returncode != 0]
        if len(successes) != 1 or len(failures) != 1:
            raise AssertionError(f"concurrent recovery expected one winner: {[item.returncode for item in attempts]}")

        status = remote_mysql(
            database,
            "SELECT operation_id, status, lease_token FROM infra_release_operation_lock WHERE target_environment='test';",
        )
        require_success(status, "verify")
        expected = f"test-{release_tag}\tFAILED\t{lease_token}"
        if status.stdout.strip() != expected:
            raise AssertionError(f"unexpected final lock state: {status.stdout.strip()}")
        print(json.dumps({"status": "passed", "database": database, "winnerCount": 1}, ensure_ascii=False))
        return 0
    finally:
        cleanup = remote_mysql(None, f"DROP DATABASE IF EXISTS `{database}`;")
        if cleanup.returncode != 0:
            print("temporary database cleanup failed", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
