import base64
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
RECOVERY_SCRIPT = ROOT / "ops" / "deploy" / "recover-release-operation-lock.ps1"
REMOTE_INTEGRATION = ROOT / "scripts" / "tests" / "verify_recover_release_lock_remote_integration.py"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def read_recovery_script() -> str:
    return RECOVERY_SCRIPT.read_text(encoding="utf-8")


def test_fail_releases_held_release_lock_before_exit() -> None:
    script = read_publish_script()

    fail_start = script.index("function Fail([string]$Message)")
    fail_end = script.index("function Info([string]$Message)")
    fail_function = script[fail_start:fail_end]

    assert "$script:ReleaseOperationLockHeld = $false" in script
    assert "$script:ReleaseOperationLockReleasing = $false" in script
    assert "if ($script:ReleaseOperationLockHeld -and -not $script:ReleaseOperationLockReleasing)" in fail_function
    assert "Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $Message" in fail_function
    assert fail_function.index("Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $Message") < fail_function.index("exit 1")


def test_release_lock_state_tracks_acquire_and_release_paths() -> None:
    script = read_publish_script()

    acquire_start = script.index("function Invoke-ReleaseOperationLockAcquire")
    release_start = script.index("function Invoke-ReleaseOperationLockRelease")
    copy_required_sql_start = script.index("function Copy-RequiredDatabaseSqlScripts")
    acquire_function = script[acquire_start:release_start]
    release_function = script[release_start:copy_required_sql_start]

    assert "$script:ReleaseOperationLockHeld = $true" in acquire_function
    assert "$script:ReleaseOperationLockHeld = $false" in release_function


def test_lock_acquire_failure_does_not_cleanup_unheld_lock() -> None:
    script = read_publish_script()

    catch_start = script.index("} catch {", script.index("Invoke-ReleaseOperationLockRelease -Status 'APPLIED'"))
    catch_end = script.index("    throw", catch_start)
    catch_block = script[catch_start:catch_end]

    assert "if ($requiresReleaseOperationLock)" in catch_block
    assert "if ($script:ReleaseOperationLockHeld)" in catch_block
    assert "Invoke-ReleaseOperationLockRelease -Status 'FAILED'" in catch_block


def test_lock_acquire_reports_current_holder_without_setting_held() -> None:
    script = read_publish_script()

    acquire_start = script.index("function Invoke-ReleaseOperationLockAcquire")
    release_start = script.index("function Invoke-ReleaseOperationLockRelease")
    acquire_function = script[acquire_start:release_start]

    assert "Invoke-SshCapture" in acquire_function
    assert "RELEASE_OPERATION_LOCK_HELD" in acquire_function
    assert "$script:ReleaseOperationLockHeld = $true" in acquire_function
    assert acquire_function.index("RELEASE_OPERATION_LOCK_HELD") < acquire_function.index("$script:ReleaseOperationLockHeld = $true")


def test_lock_ownership_is_fenced_by_lease_and_executor_identity() -> None:
    script = read_publish_script()

    assert "$script:ReleaseOperationLeaseToken" in script
    assert "executor_host" in script
    assert "executor_pid" in script
    assert "executor_identity" in script
    assert "heartbeat_at" in script
    assert "write_fence" in script
    assert "function Assert-ReleaseOperationLockOwnership" in script
    assert "LOCK_LOST" in script
    assert "HEARTBEAT_RENEWED" in script
    assert "lease_token = '$($script:ReleaseOperationLeaseToken.Replace(\"'\", \"''\"))'" in script
    assert "function Get-ReleaseOperationLockSchemaState" in script
    assert "function Enter-ReleaseOperationLock" in script
    assert "20260921_infra_release_operation_lock_lease_fencing.sql" in script


def test_deploy_acquires_lock_before_first_remote_mutation() -> None:
    script = read_publish_script()
    deploy_runtime = script[script.index("Info 'Writing remote compose environment file locally'"):]
    protected_try = deploy_runtime.index("try {")
    acquire = deploy_runtime.index("Enter-ReleaseOperationLock", protected_try)
    data_disk = deploy_runtime.index("Assert-RemoteRuntimeDataOnDataDisk", acquire)
    release_tree = deploy_runtime.index("Prepare-RemoteReleaseTree", data_disk)

    assert protected_try < acquire < data_disk < release_tree
    assert "Ensure-ReleaseMigrationStateSchema" not in deploy_runtime[protected_try:acquire]


def test_pre_acquire_lock_schema_gate_is_read_only_and_complete() -> None:
    script = read_publish_script()
    start = script.index("function Get-ReleaseOperationLockSchemaState")
    end = script.index("function Assert-ReleaseOperationLockSchemaReady", start)
    block = script[start:end]

    assert "information_schema.TABLES" in block
    assert "information_schema.COLUMNS" in block
    for column in ("executor_host", "executor_pid", "executor_identity", "lease_token", "heartbeat_at", "write_fence"):
        assert column in block
    assert "LOCK_SCHEMA_READY" in block
    assert "LOCK_SCHEMA_LEGACY" in block
    assert "LOCK_SCHEMA_INVALID" in block
    assert "ALTER TABLE" not in block
    assert "INSERT INTO" not in block
    assert "UPDATE " not in block


def test_legacy_lock_schema_is_upgraded_only_after_exact_legacy_lock_acquire() -> None:
    script = read_publish_script()
    assert "function Get-ReleaseOperationLockSchemaState" in script
    assert "LOCK_SCHEMA_LEGACY" in script
    assert "LOCK_SCHEMA_INVALID" in script
    assert "function Invoke-ReleaseOperationLegacyLockAcquire" in script
    assert "function Invoke-ReleaseOperationLockLeaseUpgrade" in script
    assert "function Enter-ReleaseOperationLock" in script

    enter_start = script.index("function Enter-ReleaseOperationLock")
    enter_end = script.index("function Invoke-ReleaseOperationLockAcquire", enter_start)
    enter = script[enter_start:enter_end]
    legacy_branch = enter[enter.index("if ($state -eq 'LOCK_SCHEMA_LEGACY')"):]
    state = enter.index("Get-ReleaseOperationLockSchemaState")
    legacy = legacy_branch.index("Invoke-ReleaseOperationLegacyLockAcquire")
    upgrade = legacy_branch.index("Invoke-ReleaseOperationLockLeaseUpgrade")
    ownership = legacy_branch.index("Assert-ReleaseOperationLockOwnership")
    assert state >= 0 and legacy < upgrade < ownership
    assert "20260921_infra_release_operation_lock_lease_fencing.sql" in script
    assert "ALTER TABLE" not in enter


def test_all_remote_deploy_components_share_the_environment_lock() -> None:
    script = read_publish_script()
    runtime = script[script.index("Info 'Writing remote compose environment file locally'"):]

    assert "$requiresReleaseOperationLock = ($Mode -eq 'deploy-release') -and ($publishBackend -or $publishFrontend -or $publishWebsite)" in runtime
    assert "if ($requiresReleaseOperationLock) {" in runtime
    assert runtime.count("if ($requiresReleaseOperationLock)") >= 3
    assert "if ($publishBackend) {\n        Assert-ReleaseOperationLockSchemaReady" not in runtime
    assert "if ($publishBackend) {\n        Assert-ReleaseOperationLockOwnership\n        Invoke-ReleaseOperationLockRelease" not in runtime


def test_actual_migration_writers_block_before_ssh_when_lock_is_not_held() -> None:
    harness = f"""
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('{str(PUBLISH_SCRIPT).replace("'", "''")}', [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) {{ throw 'publish script parse failed' }}
foreach ($name in @('Assert-ReleaseOperationWriteFence', 'Invoke-ReleaseMigrationStateBatchUpdate', 'Invoke-RequiredDatabaseSqlScriptWithState')) {{
  $definition = $ast.FindAll({{ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }}, $true) | Select-Object -First 1
  if ($null -eq $definition) {{ throw "function missing: $name" }}
  Invoke-Expression $definition.Extent.Text
}}
function Info {{ param([string]$Message) }}
function New-ReleaseMigrationStateUpsertSql {{ param($Item, [string]$Status, [string]$ErrorMessage = '') return 'SELECT 1;' }}
function Invoke-SshCommandWithInput {{ param([string]$Command, [string]$StandardInput) $script:sshCalled = $true }}
function Invoke-SshCommand {{ param([string]$Command) $script:sshCalled = $true }}
$Mode = 'deploy-release'
$script:ReleaseOperationLockHeld = $false
$script:sshCalled = $false
$batchBlocked = $false
$applyBlocked = $false
try {{ Invoke-ReleaseMigrationStateBatchUpdate -Items @([pscustomobject]@{{ migrationId = 'm1' }}) -Status 'RUNNING' }} catch {{ $batchBlocked = $_.Exception.Message -like 'RELEASE_OPERATION_LOCK_NOT_HELD*' }}
try {{ Invoke-RequiredDatabaseSqlScriptWithState -Item ([pscustomobject]@{{ migrationId = 'm1' }}) -RemoteSqlPath '/tmp/m1.sql' }} catch {{ $applyBlocked = $_.Exception.Message -like 'RELEASE_OPERATION_LOCK_NOT_HELD*' }}
Write-Output ([ordered]@{{ batchBlocked = $batchBlocked; applyBlocked = $applyBlocked; sshCalled = $script:sshCalled }} | ConvertTo-Json -Compress)
"""
    encoded_command = base64.b64encode(harness.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_command],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout.strip())
    assert evidence == {"batchBlocked": True, "applyBlocked": True, "sshCalled": False}


def test_explicit_lock_recovery_requires_executor_and_migration_evidence_checks() -> None:
    script = read_recovery_script()

    assert "RECOVER-TEST-LOCK" in script
    assert "RECOVER_BLOCKED_ACTIVE_LOCAL_EXECUTOR" in script
    assert "ExpectedExecutorHost" in script
    assert "ExpectedExecutorPid" in script
    assert "ExpectedExecutorIdentity" in script
    assert "ExpectedLeaseToken" in script
    assert "ExecutorTerminalState" in script
    assert "RECOVER_BLOCKED_OWNERSHIP_MISMATCH" in script
    assert "RECOVER_BLOCKED_ACTIVE_HEARTBEAT" in script
    assert "RECOVER_BLOCKED_MIGRATION_EVIDENCE" in script
    assert "START TRANSACTION;" in script
    assert "lease_token = '$leaseTokenLiteral'" in script
    assert "executor_host = '$executorHostLiteral'" in script
    assert "status = 'RUNNING'" in script
    assert "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;" in script
    assert "LOCK_RECOVERED" in script
    assert "AND @recovery_eligibility = 'RECOVER_ELIGIBLE';" in script
    assert '$remote = $remote -replace "`r`n", "`n"' in script


def test_lock_recovery_never_accepts_nonzero_ssh_exit_even_with_success_text() -> None:
    script = read_recovery_script()

    assert "if ($exitCode -ne 0)" in script
    assert "close - IO is still pending on closed socket" not in script
    assert "RECOVER_BLOCKED_|LOCK_RECOVERY_FAILED|ERROR [0-9]+|Permission denied|Connection timed out|Could not resolve" in script


def test_remote_integration_executes_actual_publish_writer_before_and_after_lease_loss() -> None:
    integration = REMOTE_INTEGRATION.read_text(encoding="utf-8")

    assert "def run_publish_migration_state_update" in integration
    assert "Invoke-ReleaseMigrationStateBatchUpdate" in integration
    assert "allowed-write" in integration
    assert "blocked-after-lease-loss" in integration
    assert "RELEASE_OPERATION_LOCK_LOST" in integration
    assert "SELECT migration_id, status FROM infra_release_migration" in integration


def test_build_release_holds_local_runtime_restart_guard_only_for_its_own_window() -> None:
    script = read_publish_script()

    assert "$script:BuildReleaseRuntimeRestartGuardCreated = $false" in script
    assert "function Enter-BuildReleaseRuntimeRestartGuard" in script
    assert "function Exit-BuildReleaseRuntimeRestartGuard" in script
    assert "$buildReleaseRuntimeRestartGuardFile = Join-Path $resolvedLocalCacheRoot 'runtime\\local-runtime-restart.guard'" in script
    assert "Enter-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile" in script
    assert "Exit-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile" in script
    assert "if ($Mode -eq 'build-release' -and $script:BuildReleaseRuntimeRestartGuardCreated -and (Test-Path -LiteralPath $GuardFile))" in script
    assert "build-release runtime guard active:" in script
    assert "build-release runtime guard released:" in script
