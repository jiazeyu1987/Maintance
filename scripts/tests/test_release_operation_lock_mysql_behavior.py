from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

from release_test_runtime import mysql_runtime, run_mysql


_PUBLISH_SCRIPT = Path(__file__).resolve().parents[2] / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def test_mysql_runtime_requires_explicit_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RELEASE_TEST_MYSQL_RUNTIME_CONFIG", raising=False)
    with pytest.raises(RuntimeError, match="RELEASE_TEST_MYSQL_RUNTIME_CONFIG is required"):
        mysql_runtime()


def test_mysql_runtime_rejects_wrong_task_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = mysql_runtime()
    config_path = tmp_path / "wrong-owner.json"
    config_path.write_text(json.dumps({
        "task": "unrelated-task", "container": runtime.container_name,
        "volume": runtime.volume, "password": "unused-test-value",
    }), encoding="utf-8")
    monkeypatch.setenv("RELEASE_TEST_MYSQL_RUNTIME_CONFIG", str(config_path))
    with pytest.raises(RuntimeError, match="container ownership mismatch"):
        mysql_runtime()


def _mysql(script: str, database: str | None = None) -> subprocess.CompletedProcess[str]:
    return run_mysql(script, database)


def _checked_mysql(script: str, database: str | None = None) -> subprocess.CompletedProcess[str]:
    result = _mysql(script, database=database)
    assert result.returncode == 0, result.stderr
    return result


def _database() -> str:
    return "release_lock_test_" + uuid.uuid4().hex[:12]


def _setup(database: str) -> None:
    result = _checked_mysql(
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
    result = _checked_mysql(f"DROP DATABASE IF EXISTS `{database}`;")
    assert result.returncode == 0, result.stderr


def _query(database: str, sql: str) -> str:
    result = _checked_mysql(sql, database=database)
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


def _function_text(name: str) -> str:
    parser = f"$source = [IO.File]::ReadAllText($env:PUBLISH_SCRIPT); $tokens=$null; $errors=$null; $ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors); $fn=$ast.Find({{ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq '{name}' }}, $true) | Select-Object -First 1; if ($null -eq $fn) {{ throw 'function not found' }}; [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($fn.Extent.Text))"
    parsed = subprocess.run(["pwsh", "-NoProfile", "-Command", parser], capture_output=True, text=True,
                            encoding="utf-8", errors="strict", check=False, timeout=30,
                            env={**os.environ, "PUBLISH_SCRIPT": str(_PUBLISH_SCRIPT)})
    assert parsed.returncode == 0, parsed.stderr
    text = base64.b64decode(parsed.stdout.strip(), validate=True).decode("utf-8")
    if "Get-ReleaseTargetMySqlCommand" in text and name != "Get-ReleaseTargetMySqlCommand":
        text = _function_text("Get-ReleaseTargetMySqlCommand") + "\n" + text
    if "Protect-ReleaseSensitiveText" in text and name != "Protect-ReleaseSensitiveText":
        text = _function_text("Protect-ReleaseSensitiveText") + "\n" + text
    return text


def _acquire_function_text() -> str:
    return _function_text("Invoke-ReleaseOperationLockAcquire")


def _actual_acquire_sql(
    *,
    release_tag: str,
    executor_host: str,
    executor_pid: str,
    executor_identity: str,
) -> tuple[str, str]:
    function_text = _acquire_function_text()
    wrapper = f"""
$Environment = 'test'
$ReleaseTag = '{release_tag}'
$mySqlRootPassword = 'task-test-redacted'
$script:TargetMySqlDatabase = 'release_lock_carrier'
$script:ReleaseOperationExecutorHost = '{executor_host}'
$script:ReleaseOperationExecutorPid = '{executor_pid}'
$script:ReleaseOperationExecutorIdentity = '{executor_identity}'
function Invoke-SshCapture {{
  param([switch]$IgnoreExitCode, [string]$Command)
  $script:CapturedCommand = $Command
  [pscustomobject]@{{ Ok = $true; Output = "LOCK_ACQUIRED:$($script:ReleaseOperationLeaseToken)" }}
}}
{function_text}
Invoke-ReleaseOperationLockAcquire
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script:CapturedCommand))
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
        handle.write(wrapper)
        wrapper_path = handle.name
    try:
        captured = subprocess.run(["pwsh", "-NoProfile", "-File", wrapper_path], capture_output=True, text=True,
                                  encoding="utf-8", errors="strict", check=False, timeout=30,
                                  env=os.environ.copy())
    finally:
        Path(wrapper_path).unlink(missing_ok=True)
    assert captured.returncode == 0, captured.stderr
    output_lines = captured.stdout.strip().splitlines()
    assert output_lines, "PowerShell acquire wrapper produced no capture output"
    command = base64.b64decode(output_lines[-1], validate=True).decode("utf-8")
    marker = command.find("cat <<'SQL'")
    assert marker >= 0, "actual PowerShell acquire command did not contain SQL heredoc"
    payload = command[marker:].splitlines()
    assert len(payload) >= 3 and payload[-1].strip().startswith("SQL"), "actual SQL heredoc terminator missing"
    sql = "\n".join(payload[1:-1])
    lease_match = re.search(r"(?:SELECT |VALUES \()'test', '[^']+', '[^']+', 'RUNNING'.*?'([^']+)', NOW\(\), 1", sql, re.DOTALL)
    assert lease_match, "actual PowerShell SQL did not expose generated lease token"
    return sql, lease_match.group(1)


def _actual_acquire_command(release_tag: str) -> str:
    wrapper = f"""
$Environment = 'test'
$ReleaseTag = '{release_tag}'
$mySqlRootPassword = 'task-test-redacted'
$script:TargetMySqlDatabase = 'release_lock_carrier'
$script:ReleaseOperationExecutorHost = 'CARRIER-HOST'
$script:ReleaseOperationExecutorPid = '999'
$script:ReleaseOperationExecutorIdentity = 'carrier@HOST'
function Invoke-SshCapture {{ param([switch]$IgnoreExitCode, [string]$Command) $script:CapturedCommand = $Command; [pscustomobject]@{{ Ok = $true; Output = "LOCK_ACQUIRED:$($script:ReleaseOperationLeaseToken)" }} }}
{_acquire_function_text()}
Invoke-ReleaseOperationLockAcquire
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script:CapturedCommand))
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
        handle.write(wrapper)
        wrapper_path = handle.name
    try:
        result = subprocess.run(["pwsh", "-NoProfile", "-File", wrapper_path], capture_output=True, text=True,
                                encoding="utf-8", errors="strict", check=False, timeout=30, env=os.environ.copy())
    finally:
        Path(wrapper_path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
    return base64.b64decode(result.stdout.strip().splitlines()[-1], validate=True).decode("utf-8").replace("\r\n", "\n")


def _run_actual_lock_function(database: str, function_name: str, release_tag: str, lease_token: str, held: bool) -> subprocess.CompletedProcess[str]:
    runtime = mysql_runtime()
    wrapper = f"""
$Environment = 'test'
$ReleaseTag = '{release_tag}'
$Database = '{database}'
$script:TargetMySqlDatabase = $Database
$mySqlRootPassword = 'task-test-redacted'
$script:ReleaseOperationExecutorHost = 'SAME-HOST'
$script:ReleaseOperationExecutorPid = '888'
$script:ReleaseOperationExecutorIdentity = 'same@HOST'
$script:ReleaseOperationLeaseToken = '{lease_token}'
$script:ReleaseOperationLockHeld = ${str(held).lower()}
function Invoke-SshCapture {{
  param([switch]$IgnoreExitCode, [string]$Command)
  $lines = @($Command -split "`r?`n")
  $start = [Array]::FindIndex($lines, [Predicate[string]]{{ param($line) $line -like "cat <<'SQL'*" }})
  $end = [Array]::FindLastIndex($lines, [Predicate[string]]{{ param($line) $line -like 'SQL*' }})
  if ($start -lt 0 -or $end -le $start) {{ throw 'SQL heredoc missing' }}
  $sql = ($lines[($start + 1)..($end - 1)] -join "`n")
  $bridge = 'docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}' + "`n"
  $transport = Invoke-ProcessCaptureWithInput -FilePath 'docker' -ArgumentList @('exec','-i',$env:RELEASE_TEST_MYSQL_CONTAINER_ID,'sh','-s') -StandardInput (($bridge+$Command) -replace "`r`n","`n")
  [pscustomobject]@{{ Ok = ($transport.ExitCode -eq 0); Output = ($transport.StdOut+$transport.StdErr); ExitCode = $transport.ExitCode }}
}}
{_function_text('ConvertTo-ProcessArgumentString')}
{_function_text('Invoke-ProcessCaptureWithInput')}
{_function_text(function_name)}
try {{
  {function_name}
  'FUNCTION_OK'
}} catch {{
  "FUNCTION_ERROR:$($_.Exception.Message)|HELD=$($script:ReleaseOperationLockHeld)"
}}
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
        handle.write(wrapper)
        wrapper_path = handle.name
    try:
        return subprocess.run(["pwsh", "-NoProfile", "-File", wrapper_path], capture_output=True, text=True,
                              encoding="utf-8", errors="strict", check=False, timeout=30, env={**os.environ, "RELEASE_TEST_MYSQL_CONTAINER_ID": runtime.container_id})
    finally:
        Path(wrapper_path).unlink(missing_ok=True)


def _run_actual_lock_release(
    database: str, release_tag: str, lease_token: str, status: str,
    *, error_message: str = "", transport_exit_after_sql: int = 0,
) -> subprocess.CompletedProcess[str]:
    runtime = mysql_runtime()
    definitions = "\n".join(_function_text(name) for name in (
        "Protect-ReleaseSensitiveText", "ConvertTo-ReleaseErrorMessage",
        "ConvertTo-ReleaseErrorBase64", "Remove-SshNoise", "Get-SshCommonOptions",
        "New-SshArgumentList", "Invoke-SshCommand", "Invoke-ReleaseOperationLockRelease",
        "ConvertTo-ProcessArgumentString", "Invoke-ProcessCaptureWithInput",
    ))
    encoded_error = base64.b64encode(error_message.encode("utf-8")).decode("ascii")
    wrapper = f"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$Environment = 'test'
$ReleaseTag = '{release_tag}'
$Database = '{database}'
$script:TargetMySqlDatabase = $Database
$ServerUser = 'task-transport'
$ServerHost = 'task-transport'
$mySqlRootPassword = 'task-test-redacted'
$script:ReleaseErrorMessageMaxLength = 1024
$script:ReleaseOperationExecutorHost = 'SAME-HOST'
$script:ReleaseOperationExecutorPid = '888'
$script:ReleaseOperationExecutorIdentity = 'same@HOST'
$script:ReleaseOperationLeaseToken = '{lease_token}'
$script:ReleaseOperationLockHeld = $true
$script:ReleaseOperationLegacyLockHeld = $false
$script:ReleaseOperationLockReleasing = $true
function Info {{ param([string]$Message) }}
function Invoke-ProcessCapture {{
  param([string]$FilePath, [string[]]$ArgumentList)
  if ($FilePath -ne 'ssh') {{ throw 'unexpected production transport' }}
  $command = $ArgumentList[-1]
  $sourceConnection = Get-ReleaseTargetMySqlCommand
  if (-not $command.Contains($sourceConnection)) {{ throw 'production release MySQL connection not found' }}
  $bridge = 'docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}' + "`n"
  $localCommand = $bridge + $command
  if ({transport_exit_after_sql} -ne 0) {{ $localCommand += "`nexit {transport_exit_after_sql}`n" }}
  # Preserve the production UTF-8/LF transport; a PowerShell pipeline appends
  # CRLF and corrupts the final shell comparison when the command has no LF.
  Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList @('exec','-i',$env:RELEASE_TEST_MYSQL_CONTAINER_ID,'sh','-s') -StandardInput ($localCommand -replace "`r`n","`n")
}}
{definitions}
try {{
  $errorMessage = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_error}'))
  Invoke-ReleaseOperationLockRelease -Status '{status}' -ErrorMessage $errorMessage
  "FUNCTION_OK|HELD=$($script:ReleaseOperationLockHeld)|RELEASING=$($script:ReleaseOperationLockReleasing)|LEASE_PRESENT=$(-not [string]::IsNullOrEmpty($script:ReleaseOperationLeaseToken))"
}} catch {{
  "FUNCTION_ERROR:$($_.Exception.Message)|HELD=$($script:ReleaseOperationLockHeld)|RELEASING=$($script:ReleaseOperationLockReleasing)|LEASE_PRESENT=$(-not [string]::IsNullOrEmpty($script:ReleaseOperationLeaseToken))"
  exit 19
}}
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
        handle.write(wrapper)
        wrapper_path = handle.name
    try:
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", wrapper_path], capture_output=True, text=True,
            encoding="utf-8", errors="strict", check=False, timeout=30,
            env={**os.environ, "RELEASE_TEST_MYSQL_CONTAINER_ID": runtime.container_id},
        )
    finally:
        Path(wrapper_path).unlink(missing_ok=True)


def _acquire_same_host(database: str, release_tag: str) -> str:
    sql, lease = _actual_acquire_sql(
        release_tag=release_tag, executor_host="SAME-HOST", executor_pid="888",
        executor_identity="same@HOST",
    )
    result = _checked_mysql(sql, database)
    assert result.stdout.strip() == f"LOCK_ACQUIRED:{lease}"
    return lease


@pytest.mark.parametrize("status", ["APPLIED", "FAILED"])
def test_actual_release_writes_terminal_state_and_clears_executor_flags(status: str) -> None:
    database = _database()
    try:
        _setup(database)
        lease = _acquire_same_host(database, "release-terminal")
        message = "task release failed\r\npassword=synthetic-secret" if status == "FAILED" else ""
        result = _run_actual_lock_release(
            database, "release-terminal", lease, status, error_message=message,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "FUNCTION_OK|HELD=False|RELEASING=False|LEASE_PRESENT=False" in result.stdout
        assert "FUNCTION_ERROR" not in result.stdout
        assert _query(database, "SELECT status, finished_at IS NOT NULL, lease_token FROM infra_release_operation_lock;") == f"{status}\t1\t{lease}"
        if status == "FAILED":
            expected = "task release failed\npassword=<redacted>".encode("utf-8").hex().upper()
            assert _query(database, "SELECT HEX(error_message) FROM infra_release_operation_lock;") == expected
        else:
            assert _query(database, "SELECT error_message IS NULL FROM infra_release_operation_lock;") == "1"
    finally:
        _drop(database)


def test_actual_release_rejects_replaced_lease_without_mutating_current_owner() -> None:
    database = _database()
    try:
        _setup(database)
        old_lease = _acquire_same_host(database, "release-replaced")
        released = _run_actual_lock_release(database, "release-replaced", old_lease, "FAILED")
        assert released.returncode == 0, released.stdout + released.stderr
        current_lease = _acquire_same_host(database, "release-replaced")
        assert current_lease != old_lease
        before = _query(database, "SELECT * FROM infra_release_operation_lock;")
        rejected = _run_actual_lock_release(database, "release-replaced", old_lease, "APPLIED")
        assert rejected.returncode == 19, rejected.stdout + rejected.stderr
        assert "FUNCTION_ERROR:Command failed with exit code 1" in rejected.stdout
        assert "HELD=True|RELEASING=True" in rejected.stdout
        assert "FUNCTION_OK" not in rejected.stdout
        assert _query(database, "SELECT * FROM infra_release_operation_lock;") == before
    finally:
        _drop(database)


def test_actual_release_preserves_real_mysql_error_and_unconfirmed_held_state() -> None:
    database = _database()
    try:
        _setup(database)
        lease = _acquire_same_host(database, "release-sql-error")
        _checked_mysql("ALTER TABLE infra_release_operation_lock DROP COLUMN error_message;", database)
        before = _query(database, "SELECT * FROM infra_release_operation_lock;")
        result = _run_actual_lock_release(database, "release-sql-error", lease, "FAILED")
        assert result.returncode == 19, result.stdout + result.stderr
        assert "FUNCTION_ERROR:" in result.stdout
        assert "ERROR 1054" in result.stdout
        assert "HELD=True|RELEASING=True" in result.stdout
        assert "FUNCTION_OK" not in result.stdout
        assert _query(database, "SELECT * FROM infra_release_operation_lock;") == before
    finally:
        _drop(database)


def test_actual_release_preserves_transport_failure_after_sql_applied() -> None:
    database = _database()
    try:
        _setup(database)
        lease = _acquire_same_host(database, "release-transport-error")
        result = _run_actual_lock_release(
            database, "release-transport-error", lease, "APPLIED", transport_exit_after_sql=17,
        )
        assert result.returncode == 19, result.stdout + result.stderr
        assert "FUNCTION_ERROR:Command failed with exit code 17" in result.stdout
        # The actual shell now consumes its success marker internally. The
        # persisted APPLIED row below proves SQL ran before transport exit 17.
        assert "LEASE_PRESENT=True" in result.stdout
        assert "HELD=True|RELEASING=True" in result.stdout
        assert "FUNCTION_OK" not in result.stdout
        assert _query(database, "SELECT status, lease_token FROM infra_release_operation_lock;") == f"APPLIED\t{lease}"
    finally:
        _drop(database)


def test_publish_script_updates_lock_status_after_owner_fields() -> None:
    source = _PUBLISH_SCRIPT.read_text(encoding="utf-8")
    start = source.index("ON DUPLICATE KEY UPDATE", source.index("function Invoke-ReleaseOperationLockAcquire"))
    end = source.index("SELECT CASE", start)
    update_clause = source[start:end]
    assert update_clause.index("lease_token = IF(status = 'RUNNING'") < update_clause.index(
        "status = IF(status = 'RUNNING'"
    )
    assert update_clause.index("heartbeat_at = IF(status = 'RUNNING'") < update_clause.index(
        "status = IF(status = 'RUNNING'"
    )


def test_mysql_nonzero_is_preserved_when_success_text_precedes_sql_error() -> None:
    database = _database()
    try:
        _setup(database)
        result = _mysql(
            "SELECT 'LOCK_ACQUIRED:carrier'; SELECT * FROM missing_release_lock_table;",
            database=database,
        )
        assert result.returncode != 0
        assert "LOCK_ACQUIRED:carrier" in result.stdout
    finally:
        _drop(database)


def test_acquire_transport_does_not_mask_mysql_exit_with_grep() -> None:
    source = _PUBLISH_SCRIPT.read_text(encoding="utf-8")
    acquire = source[source.index("function Invoke-ReleaseOperationLockAcquire"):source.index(
        "function Assert-ReleaseOperationLockOwnership"
    )]
    assert "| grep -E '^(LOCK_ACQUIRED|LOCK_HELD:)'" not in acquire


def test_local_shell_carrier_preserves_docker_failure_after_success_marker() -> None:
    command = _actual_acquire_command("carrier-release")
    lines = command.splitlines()
    command_line = next(index for index, line in enumerate(lines) if line.startswith("cat <<'SQL'"))
    fault_command = "docker() { cat >/dev/null; printf 'LOCK_ACQUIRED:carrier\\n'; return 17; }; " + command
    old_lines = list(lines)
    old_lines[command_line] += " | grep -E '^(LOCK_ACQUIRED|LOCK_HELD:)'"
    masked = subprocess.run(
        ["bash", "-lc", fault_command.replace(command, "\n".join(old_lines))],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict", check=False, timeout=30,
    )
    preserved = subprocess.run(
        ["bash", "-lc", fault_command],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="strict", check=False, timeout=30,
    )
    assert masked.returncode == 0
    assert "LOCK_ACQUIRED:carrier" in masked.stdout
    assert preserved.returncode == 17
    assert "LOCK_ACQUIRED:carrier" in preserved.stdout


def test_actual_acquire_rejects_success_text_when_transport_is_nonzero() -> None:
    wrapper = f"""
$Environment = 'test'
$ReleaseTag = 'release-transport-failure'
$mySqlRootPassword = 'task-test-redacted'
$script:TargetMySqlDatabase = 'release_lock_carrier'
$script:ReleaseOperationExecutorHost = 'FAILURE-HOST'
$script:ReleaseOperationExecutorPid = '777'
$script:ReleaseOperationExecutorIdentity = 'failure@HOST'
$captureOutput = 'LOCK_ACQUIRED:carrier-text'
function Invoke-SshCapture {{
  param([switch]$IgnoreExitCode, [string]$Command)
  [pscustomobject]@{{ Ok = $false; Output = "LOCK_ACQUIRED:$($script:ReleaseOperationLeaseToken)"; ExitCode = 17 }}
}}
{_acquire_function_text()}
try {{
  Invoke-ReleaseOperationLockAcquire
  'SUCCESS'
}} catch {{
  "THREW:$($_.Exception.Message)|HELD=$($script:ReleaseOperationLockHeld)"
}}
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
        handle.write(wrapper)
        wrapper_path = handle.name
    try:
        result = subprocess.run(["pwsh", "-NoProfile", "-File", wrapper_path], capture_output=True, text=True,
                                encoding="utf-8", errors="strict", check=False, timeout=30,
                                env=os.environ.copy())
    finally:
        Path(wrapper_path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
    assert "THREW:RELEASE_OPERATION_LOCK_ACQUIRE_FAILED: LOCK_ACQUIRED:<redacted>" in result.stdout
    assert "HELD=True" not in result.stdout


def test_mysql_reacquire_terminal_row_refreshes_lease_and_reports_new_owner() -> None:
    database = _database()
    try:
        _setup(database)
        _checked_mysql(
            """
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at, finished_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   creator, create_time, updater, update_time)
VALUES
  ('test', 'test-release-old', 'release-old', 'FAILED', DATE_SUB(NOW(), INTERVAL 2 DAY),
   DATE_SUB(NOW(), INTERVAL 2 DAY), 'OLD-HOST', '111', 'old@OLD-HOST', 'old-lease',
   DATE_SUB(NOW(), INTERVAL 2 DAY), 'release-system', NOW(), 'release-system', NOW());
""",
            database=database,
        )
        actual_sql, actual_lease = _actual_acquire_sql(
                release_tag="release-new",
                executor_host="NEW-HOST",
                executor_pid="222",
                executor_identity="new@NEW-HOST",
            )
        result = _mysql(
            actual_sql,
            database=database,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().startswith("LOCK_ACQUIRED:")
        owner_row = _query(
            database,
            "SELECT operation_id, status, executor_host, executor_pid, executor_identity, lease_token "
            "FROM infra_release_operation_lock;",
        )
        owner_fields = owner_row.split("\t")
        assert owner_fields[:5] == ["test-release-new", "RUNNING", "NEW-HOST", "222", "new@NEW-HOST"]
        assert owner_fields[5] == actual_lease
        assert _query(
            database,
            "SELECT heartbeat_at >= DATE_SUB(NOW(), INTERVAL 30 SECOND) "
            "FROM infra_release_operation_lock;",
        ) == "1"
    finally:
        _drop(database)


@pytest.mark.parametrize("terminal_status", ["APPLIED", "FAILED"])
def test_mysql_reacquire_any_terminal_row_gets_a_fresh_lease(terminal_status: str) -> None:
    database = _database()
    try:
        _setup(database)
        seed = _mysql(
            f"""
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at, finished_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   write_fence, creator, create_time, updater, update_time)
VALUES ('test', 'test-release-old', 'release-old', '{terminal_status}', NOW(), NOW(),
        'OLD-HOST', '111', 'old@OLD-HOST', 'old-lease', NOW(), 7,
        'release-system', NOW(), 'release-system', NOW());
""",
            database=database,
        )
        assert seed.returncode == 0, seed.stderr
        actual_sql, actual_lease = _actual_acquire_sql(
            release_tag="release-new",
            executor_host="NEW-HOST",
            executor_pid="222",
            executor_identity="new@NEW-HOST",
        )
        result = _mysql(actual_sql, database=database)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().startswith("LOCK_ACQUIRED:")
        assert _query(database, "SELECT operation_id, status, lease_token, write_fence FROM infra_release_operation_lock;") == (
            f"test-release-new\tRUNNING\t{actual_lease}\t8"
        )
    finally:
        _drop(database)


def test_mysql_active_other_owner_is_rejected_without_mutation() -> None:
    database = _database()
    try:
        _setup(database)
        _checked_mysql(
            """
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   write_fence, creator, create_time, updater, update_time)
VALUES ('test', 'test-release-active', 'release-active', 'RUNNING', NOW(),
        'ACTIVE-HOST', '333', 'active@ACTIVE-HOST', 'active-lease', NOW(), 9,
        'release-system', NOW(), 'active-owner', '2026-01-01 00:00:00');
""",
            database=database,
        )
        before = _query(database, "SELECT * FROM infra_release_operation_lock;")
        actual_sql, _ = _actual_acquire_sql(
            release_tag="release-contender",
            executor_host="NEW-HOST",
            executor_pid="444",
            executor_identity="new@NEW-HOST",
        )
        result = _mysql(actual_sql, database=database)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "LOCK_HELD:test-release-active:release-active"
        assert _query(database, "SELECT operation_id, status, lease_token, write_fence FROM infra_release_operation_lock;") == (
            "test-release-active\tRUNNING\tactive-lease\t9"
        )
        assert _query(database, "SELECT * FROM infra_release_operation_lock;") == before
    finally:
        _drop(database)


@pytest.mark.parametrize("race_case", range(10))
def test_mysql_concurrent_actual_acquire_has_one_winner(race_case: int) -> None:
    from concurrent.futures import ThreadPoolExecutor

    database = _database()
    try:
        _setup(database)
        statements = [
            _actual_acquire_sql(
                release_tag=f"release-race-{race_case}-{index}",
                executor_host=f"RACE-HOST-{index}",
                executor_pid=str(500 + index),
                executor_identity=f"race-{index}@HOST",
            )[0]
            for index in (1, 2)
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda sql: _mysql(sql, database=database), statements))
        assert all(result.returncode == 0 for result in results), [
            (result.returncode, result.stdout, result.stderr) for result in results
        ]
        evidence = [result.stdout.strip() for result in results]
        assert sum(item.startswith("LOCK_ACQUIRED:") for item in evidence) == 1
        assert sum(item.startswith("LOCK_HELD:") for item in evidence) == 1
        assert _query(database, "SELECT COUNT(*) FROM infra_release_operation_lock WHERE status='RUNNING';") == "1"
    finally:
        _drop(database)


def test_mysql_lock_release_requires_exact_executor_and_lease_owner() -> None:
    database = _database()
    try:
        _setup(database)
        _checked_mysql(
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
        seed = _mysql(
            """
INSERT INTO infra_release_operation_lock
  (target_environment, operation_id, release_tag, status, started_at, finished_at,
   executor_host, executor_pid, executor_identity, lease_token, heartbeat_at,
   write_fence, creator, create_time, updater, update_time)
VALUES ('test', 'test-release-old', 'release-old', 'FAILED', NOW(), NOW(),
        'HOST-A', '111', 'operator@HOST-A', 'lease-old', NOW(), 4,
        'release-system', NOW(), 'release-system', NOW());
""",
            database=database,
        )
        assert seed.returncode == 0, seed.stderr
        actual_sql, actual_lease = _actual_acquire_sql(
            release_tag="release-new",
            executor_host="HOST-A",
            executor_pid="222",
            executor_identity="operator@HOST-A",
        )
        result = _mysql(actual_sql, database=database)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().startswith("LOCK_ACQUIRED:")
        result = _mysql(
            f"""
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
            f"test-release-new\tRUNNING\t{actual_lease}"
        )
    finally:
        _drop(database)


def test_same_tag_lifecycle_uses_real_ownership_sql_and_rejects_old_lease() -> None:
    database = _database()
    try:
        _setup(database)
        first_sql, lease1 = _actual_acquire_sql(
            release_tag="same-tag", executor_host="SAME-HOST", executor_pid="888", executor_identity="same@HOST"
        )
        first = _checked_mysql(first_sql, database=database)
        assert first.stdout.strip().startswith("LOCK_ACQUIRED:")
        assert _query(database, "SELECT operation_id, status, lease_token, write_fence FROM infra_release_operation_lock;") == (
            f"test-same-tag\tRUNNING\t{lease1}\t1"
        )
        _checked_mysql("UPDATE infra_release_operation_lock SET status='FAILED', finished_at=NOW() WHERE target_environment='test';", database=database)
        second_sql, lease2 = _actual_acquire_sql(
            release_tag="same-tag", executor_host="SAME-HOST", executor_pid="888", executor_identity="same@HOST"
        )
        second = _checked_mysql(second_sql, database=database)
        assert second.stdout.strip().startswith("LOCK_ACQUIRED:")
        assert lease2 != lease1
        assert _query(database, "SELECT operation_id, status, lease_token, write_fence FROM infra_release_operation_lock;") == (
            f"test-same-tag\tRUNNING\t{lease2}\t2"
        )
        old_owner = _run_actual_lock_function(database, "Assert-ReleaseOperationLockOwnership", "same-tag", lease1, True)
        assert old_owner.returncode == 0, old_owner.stderr
        assert "FUNCTION_ERROR:RELEASE_OPERATION_LOCK_LOST" in old_owner.stdout
        assert "HELD=False" in old_owner.stdout
        assert "FUNCTION_OK" not in old_owner.stdout
        assert _query(database, "SELECT operation_id, lease_token, write_fence FROM infra_release_operation_lock;") == (
            f"test-same-tag\t{lease2}\t2"
        )
        current_owner = _run_actual_lock_function(database, "Assert-ReleaseOperationLockOwnership", "same-tag", lease2, True)
        assert current_owner.returncode == 0, current_owner.stderr
        assert "FUNCTION_OK" in current_owner.stdout
        assert _query(database, "SELECT write_fence FROM infra_release_operation_lock;") == "3"
        assert _query(database, "SELECT heartbeat_at >= DATE_SUB(NOW(), INTERVAL 30 SECOND) FROM infra_release_operation_lock;") == "1"
    finally:
        _drop(database)
