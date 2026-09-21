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
PUBLISH_SCRIPT = ROOT / "ops/deploy/publish-int-ruoyi.ps1"
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


def run_publish_migration_state_update(
    database: str,
    release_tag: str,
    lease_token: str,
    migration_id: str,
    *,
    enter_lock: bool = False,
    required_sql_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    computer = os.environ["COMPUTERNAME"]
    identity = f"{os.environ['USERNAME']}@{computer}"
    harness = r'''
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('__PUBLISH_SCRIPT__', [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw 'publish script parse failed' }
$functionNames = @(
  'ConvertTo-SqlStringLiteral',
  'Protect-ReleaseSensitiveText',
  'ConvertTo-ReleaseErrorMessage',
  'ConvertTo-ReleaseErrorBase64',
  'Get-RequiredDatabaseSqlFileName',
  'New-ReleaseMigrationStateUpsertSql',
  'Get-ReleaseOperationLockSchemaState',
  'Assert-ReleaseOperationLockSchemaReady',
  'Invoke-ReleaseOperationLegacyLockAcquire',
  'Invoke-ReleaseOperationLockLeaseUpgrade',
  'Enter-ReleaseOperationLock',
  'Invoke-ReleaseOperationLockAcquire',
  'Assert-ReleaseOperationLockOwnership',
  'Assert-ReleaseOperationWriteFence',
  'Invoke-ReleaseMigrationStateBatchUpdate'
)
foreach ($name in $functionNames) {
  $definition = $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true) | Select-Object -First 1
  if ($null -eq $definition) { throw "function missing: $name" }
  Invoke-Expression $definition.Extent.Text
}

function Info { param([string]$Message) }

function Invoke-IntegrationSsh {
  param(
    [Parameter(Mandatory = $true)][string]$Command,
    [AllowNull()][string]$StandardInput = $null
  )
  $rewritten = $Command.Replace('ruoyi-vue-pro', $DatabaseName)
  $rewritten = $rewritten.Replace('MYSQL_PWD=integration-placeholder', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD"')
  $rewritten = $rewritten.Replace('-pintegration-placeholder', '-p"$MYSQL_ROOT_PASSWORD"')
  $prefix = @'
set -eu
MYSQL_ROOT_PASSWORD=$(grep -E '^MYSQL_ROOT_PASSWORD=' '/opt/intruoyi/runtime/.env' | head -n 1 | cut -d= -f2-)
test -n "$MYSQL_ROOT_PASSWORD"
export MYSQL_ROOT_PASSWORD
'@
  if ($null -ne $StandardInput) {
    $encodedInput = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($StandardInput))
    $remoteBody = $prefix + "`nprintf '%s' '$encodedInput' | base64 -d | " + $rewritten
  } else {
    $remoteBody = $prefix + "`n" + $rewritten
  }
  $remoteBody = $remoteBody -replace "`r`n", "`n" -replace "`r", "`n"
  $payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($remoteBody))
  $runner = "PAYLOAD='$payload'; printf '%s' `"`$PAYLOAD`" | base64 -d | bash"
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $output = & ssh.exe -n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@172.30.30.58 $runner 2>&1
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  return @{
    Ok = ($exitCode -eq 0)
    Output = (($output | ForEach-Object { [string]$_ }) -join "`n").Trim()
    ExitCode = $exitCode
  }
}

function Invoke-SshCapture {
  param([Parameter(Mandatory = $true)][string]$Command, [switch]$IgnoreExitCode)
  $result = Invoke-IntegrationSsh -Command $Command
  if (-not $result.Ok -and -not $IgnoreExitCode) { throw "SSH command failed: $($result.Output)" }
  return $result
}

function Invoke-SshCommandWithInput {
  param([Parameter(Mandatory = $true)][string]$Command, [AllowNull()][string]$StandardInput = '')
  $result = Invoke-IntegrationSsh -Command $Command -StandardInput $StandardInput
  if (-not $result.Ok) { throw "SSH command failed: $($result.Output)" }
}

$DatabaseName = '__DATABASE__'
$Mode = 'deploy-release'
$Environment = 'test'
$ReleaseTag = '__RELEASE_TAG__'
$mySqlRootPassword = 'integration-placeholder'
$requiredSqlLocalDir = '__REQUIRED_SQL_DIR__'
$script:ReleaseOperationLockHeld = $true
$script:ReleaseOperationLegacyLockHeld = $false
$script:ReleaseOperationLeaseToken = '__LEASE_TOKEN__'
$script:ReleaseOperationExecutorHost = '__EXECUTOR_HOST__'
$script:ReleaseOperationExecutorPid = '2147483000'
$script:ReleaseOperationExecutorIdentity = '__EXECUTOR_IDENTITY__'
$script:ReleaseErrorMessageMaxLength = 2048
if ('__ENTER_LOCK__' -eq 'true') {
  $script:ReleaseOperationLockHeld = $false
  $script:ReleaseOperationLeaseToken = ''
  Enter-ReleaseOperationLock
  Write-Output "LOCK_ENTRY_COMPLETED:$($script:ReleaseOperationLeaseToken)"
  exit 0
}
$item = [pscustomobject]@{
  migrationId = '__MIGRATION_ID__'
  file = 'required-sql/__MIGRATION_ID__.sql'
  sha256 = 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
}
Invoke-ReleaseMigrationStateBatchUpdate -Items @($item) -Status 'RUNNING'
Write-Output 'PUBLISH_WRITE_COMPLETED:__MIGRATION_ID__'
'''
    replacements = {
        "__PUBLISH_SCRIPT__": str(PUBLISH_SCRIPT).replace("'", "''"),
        "__DATABASE__": database,
        "__RELEASE_TAG__": release_tag,
        "__LEASE_TOKEN__": lease_token,
        "__REQUIRED_SQL_DIR__": str(required_sql_dir or ROOT).replace("'", "''"),
        "__ENTER_LOCK__": "true" if enter_lock else "false",
        "__EXECUTOR_HOST__": computer,
        "__EXECUTOR_IDENTITY__": identity,
        "__MIGRATION_ID__": migration_id,
    }
    for marker, value in replacements.items():
        harness = harness.replace(marker, value)
    encoded = base64.b64encode(harness.encode("utf-16le")).decode("ascii")
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
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
    lease_token = ""
    app_backend_root = Path(os.environ.get("INTRUOYI_APP_BACKEND_ROOT", "E:/IntRuoyi/IntRuoyiBackend"))
    required_sql_dir = app_backend_root / "sql/mysql"
    lease_migration = required_sql_dir / "20260921_infra_release_operation_lock_lease_fencing.sql"
    if not lease_migration.is_file():
        raise AssertionError(f"lease migration missing: {lease_migration}")
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
  release_tag varchar(128) NOT NULL,
  migration_id varchar(191) NOT NULL,
  file_name varchar(512) NOT NULL,
  sha256 varchar(80) NOT NULL,
  target_environment varchar(32) NOT NULL,
  status varchar(32) NOT NULL
  ,started_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
  ,finished_at datetime NULL
  ,error_message text NULL
  ,operation_id varchar(128) NOT NULL
  ,creator varchar(64) DEFAULT ''
  ,create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
  ,updater varchar(64) DEFAULT ''
  ,update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
  ,deleted bit(1) NOT NULL DEFAULT b'0'
  ,tenant_id bigint NOT NULL DEFAULT 0
  ,UNIQUE KEY uk_infra_release_migration_env_id (target_environment, migration_id)
) ENGINE=InnoDB;
"""
    try:
        require_success(remote_mysql(None, setup_sql), "setup")

        entered = run_publish_migration_state_update(
            database,
            release_tag,
            "",
            "unused",
            enter_lock=True,
            required_sql_dir=required_sql_dir,
        )
        require_success(entered, "actual legacy lock entry and lease upgrade")
        evidence_lines = [
            line.strip() for line in entered.stdout.splitlines()
            if line.strip().startswith("LOCK_ENTRY_COMPLETED:")
        ]
        if len(evidence_lines) != 1:
            raise AssertionError(f"legacy lock entry evidence missing: {entered.stdout!r}")
        lease_token = evidence_lines[0].split(":", 1)[1]
        if not lease_token:
            raise AssertionError("legacy lock entry returned a blank lease token")
        upgraded = remote_mysql(
            database,
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='infra_release_operation_lock' "
            "AND COLUMN_NAME IN ('executor_host','executor_pid','executor_identity','lease_token','heartbeat_at','write_fence'); "
            "SELECT operation_id,status,executor_pid,lease_token FROM infra_release_operation_lock WHERE target_environment='test';",
        )
        require_success(upgraded, "verify legacy lock lease upgrade")
        upgraded_lines = [line.strip() for line in upgraded.stdout.splitlines() if line.strip()]
        expected_owner = f"test-{release_tag}\tRUNNING\t2147483000\t{lease_token}"
        if upgraded_lines != ["6", expected_owner]:
            raise AssertionError(f"unexpected upgraded lock state: {upgraded_lines!r}")

        allowed = run_publish_migration_state_update(database, release_tag, lease_token, "allowed-write")
        require_success(allowed, "actual publish writer with owned lease")
        if "PUBLISH_WRITE_COMPLETED:allowed-write" not in allowed.stdout:
            raise AssertionError(f"owned publish write lacks completion evidence: {allowed.stdout!r}")

        require_success(
            remote_mysql(
                database,
                "UPDATE infra_release_operation_lock SET lease_token='replacement-lease', write_fence=write_fence+1;",
            ),
            "replace publish lease",
        )
        blocked = run_publish_migration_state_update(
            database, release_tag, lease_token, "blocked-after-lease-loss"
        )
        if blocked.returncode == 0 or "RELEASE_OPERATION_LOCK_LOST" not in (blocked.stdout + blocked.stderr):
            raise AssertionError(
                "lost lease did not block the actual publish writer: "
                f"exit={blocked.returncode}, stdout={blocked.stdout!r}, stderr={blocked.stderr!r}"
            )
        migration_state = remote_mysql(
            database,
            "SELECT migration_id, status FROM infra_release_migration ORDER BY migration_id;",
        )
        require_success(migration_state, "verify actual publish writer fence")
        if migration_state.stdout.strip() != "allowed-write\tRUNNING":
            raise AssertionError(f"unexpected migration writes after lease loss: {migration_state.stdout.strip()}")
        require_success(
            remote_mysql(
                database,
                f"DELETE FROM infra_release_migration; "
                f"UPDATE infra_release_operation_lock SET lease_token='{lease_token}', heartbeat_at=NOW();",
            ),
            "restore recovery fixture",
        )

        active = run_recovery(database, release_tag, lease_token)
        if active.returncode == 0 or "RECOVER_BLOCKED_ACTIVE_HEARTBEAT" not in (active.stdout + active.stderr):
            raise AssertionError(
                "active heartbeat did not block the actual recovery script: "
                f"exit={active.returncode}, stdout={active.stdout!r}, stderr={active.stderr!r}"
            )

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
