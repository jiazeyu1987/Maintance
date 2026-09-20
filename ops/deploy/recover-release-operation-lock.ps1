param(
    [Parameter(Mandatory = $true)]
    [string]$ServerHost,
    [string]$ServerUser = 'root',
    [Parameter(Mandatory = $true)]
    [string]$RemoteAppDir,
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$DatabaseName = 'ruoyi-vue-pro',
    [Parameter(Mandatory = $true)]
    [string]$ExpectedOperationId,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedReleaseTag,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedExecutorHost,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedExecutorPid,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedExecutorIdentity,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedLeaseToken,
    [Parameter(Mandatory = $true)]
    [ValidateSet('TERMINATED')]
    [string]$ExecutorTerminalState,
    [Parameter(Mandatory = $true)]
    [ValidateSet('RECOVER-TEST-LOCK')]
    [string]$ConfirmText
)

$ErrorActionPreference = 'Stop'
if ($ConfirmText -ne 'RECOVER-TEST-LOCK') {
    throw 'RECOVER_RELEASE_LOCK_CONFIRMATION_REQUIRED'
}
if ($ExpectedOperationId -ne "test-$ExpectedReleaseTag") {
    throw "RECOVER_RELEASE_LOCK_OPERATION_MISMATCH: expected operationId must be test-$ExpectedReleaseTag"
}
if ($ExecutorTerminalState -ne 'TERMINATED') {
    throw 'RECOVER_RELEASE_LOCK_TERMINAL_STATE_REQUIRED'
}
if ($ExpectedExecutorHost -ne [string]$env:COMPUTERNAME) {
    throw "RECOVER_RELEASE_LOCK_EXECUTOR_HOST_MISMATCH: expected $ExpectedExecutorHost, current $env:COMPUTERNAME"
}
if ($ExpectedExecutorIdentity -ne "$([string]$env:USERNAME)@$([string]$env:COMPUTERNAME)") {
    throw 'RECOVER_RELEASE_LOCK_EXECUTOR_IDENTITY_MISMATCH'
}
if ($ExpectedExecutorPid -notmatch '^\d+$') {
    throw 'RECOVER_RELEASE_LOCK_EXECUTOR_PID_INVALID'
}
if (Get-Process -Id ([int]$ExpectedExecutorPid) -ErrorAction SilentlyContinue) {
    throw "RECOVER_BLOCKED_ACTIVE_LOCAL_EXECUTOR:$ExpectedExecutorPid"
}

$sshArgs = @(
    '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=10',
    '-o', 'ServerAliveCountMax=3', '-o', 'StrictHostKeyChecking=no',
    "$ServerUser@$ServerHost"
)

$sqlLiteral = $ExpectedReleaseTag.Replace("'", "''")
$operationLiteral = $ExpectedOperationId.Replace("'", "''")
$executorHostLiteral = $ExpectedExecutorHost.Replace("'", "''")
$executorPidLiteral = $ExpectedExecutorPid.Replace("'", "''")
$executorIdentityLiteral = $ExpectedExecutorIdentity.Replace("'", "''")
$leaseTokenLiteral = $ExpectedLeaseToken.Replace("'", "''")
$remote = @"
set -eu
MYSQL_ROOT_PASSWORD=`$(grep -E '^MYSQL_ROOT_PASSWORD=' '$RemoteAppDir/.env' | head -n 1 | cut -d= -f2-)
if [ -z "`$MYSQL_ROOT_PASSWORD" ]; then
  echo 'RECOVER_BLOCKED_MISSING_DB_CREDENTIAL' >&2
  exit 42
fi
export MYSQL_ROOT_PASSWORD
docker exec -i -e MYSQL_PWD="`$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names '$DatabaseName' <<'SQL'
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
START TRANSACTION;
SELECT CASE
  WHEN NOT EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = '$operationLiteral'
      AND release_tag = '$sqlLiteral'
      AND status = 'RUNNING'
      AND executor_host = '$executorHostLiteral'
      AND executor_pid = '$executorPidLiteral'
      AND executor_identity = '$executorIdentityLiteral'
      AND lease_token = '$leaseTokenLiteral'
  ) THEN 'RECOVER_BLOCKED_OWNERSHIP_MISMATCH'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_migration
    WHERE target_environment = 'test'
      AND release_tag = '$sqlLiteral'
      AND status IN ('RUNNING', 'APPLIED', 'FAILED')
  ) THEN 'RECOVER_BLOCKED_MIGRATION_EVIDENCE'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = '$operationLiteral'
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
  AND operation_id = '$operationLiteral'
  AND release_tag = '$sqlLiteral'
  AND status = 'RUNNING'
  AND executor_host = '$executorHostLiteral'
  AND executor_pid = '$executorPidLiteral'
  AND executor_identity = '$executorIdentityLiteral'
  AND lease_token = '$leaseTokenLiteral'
  AND (heartbeat_at IS NULL OR heartbeat_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE))
  AND @recovery_eligibility = 'RECOVER_ELIGIBLE';
SELECT CASE WHEN ROW_COUNT() = 1 THEN 'LOCK_RECOVERED' ELSE 'LOCK_RECOVERY_FAILED' END;
COMMIT;
SQL
"@

$remote = $remote -replace "`r`n", "`n"
$remotePayload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($remote))
$remoteCommand = "PAYLOAD='$remotePayload'; printf '%s' ""`$PAYLOAD"" | base64 -d | bash"
try {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $result = & ssh @sshArgs $remoteCommand 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $result | ForEach-Object { Write-Host $_ }
    $resultText = $result | Out-String
    if ($exitCode -ne 0) {
        throw "RECOVER_RELEASE_LOCK_FAILED: exit code $exitCode"
    }
    if ($resultText -match 'RECOVER_BLOCKED_|LOCK_RECOVERY_FAILED|ERROR [0-9]+|Permission denied|Connection timed out|Could not resolve') {
        throw 'RECOVER_RELEASE_LOCK_FAILED: explicit recovery evidence contains a blocker'
    }
    if ($resultText -notmatch 'RECOVER_ELIGIBLE' -or $resultText -notmatch 'LOCK_RECOVERED') {
        throw 'RECOVER_RELEASE_LOCK_FAILED: missing explicit eligibility or recovery evidence'
    }
    Write-Host "Release operation lock recovered: $ExpectedOperationId"
} finally {
}
