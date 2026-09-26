param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]*$')]
    [string]$ServerHost,
    [string]$ServerUser = 'root',
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^/[A-Za-z0-9_./-]+$')]
    [string]$RemoteAppDir,
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_-]{0,63}$')]
    [string]$DatabaseName = 'ruoyi-vue-pro',
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^test-[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')]
    [string]$ExpectedOperationId,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')]
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
$encoding=[Text.UTF8Encoding]::new($false)
[Console]::InputEncoding=$encoding;[Console]::OutputEncoding=$encoding;$OutputEncoding=$encoding
Import-Module -Force (Join-Path $PSScriptRoot '..\release\lib\ReleaseDeploymentEvidence.psm1')
if($RemoteAppDir -match '(^|/)\.\.?(?:/|$)' -or $RemoteAppDir.EndsWith('/')){throw 'RECOVER_RELEASE_LOCK_PATH_INVALID'}
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

function Invoke-RecoveryEvidenceCapture {
    param([string]$Command)
    $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Command -replace "`r`n","`n")))
    $native="printf '%s' '$payload' | base64 -d | bash"
    $prior=$ErrorActionPreference
    try {$ErrorActionPreference='Continue';$text=@(& ssh @sshArgs $native 2>&1);$code=$LASTEXITCODE}
    finally{$ErrorActionPreference=$prior}
    return @{Ok=($code -eq 0);Output=($text -join "`n")}
}

$mysqlCommand="docker exec -i intruoyi-mysql sh -lc 'MYSQL_PWD=`"`$MYSQL_ROOT_PASSWORD`" exec mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names `"`$1`"' sh '$DatabaseName'"
$machine=Invoke-RecoveryEvidenceCapture -Command 'cat /etc/machine-id'
$database=Invoke-RecoveryEvidenceCapture -Command "$mysqlCommand <<'RECOVERY_IDENTITY_SQL'`nSELECT @@server_uuid;`nRECOVERY_IDENTITY_SQL"
if(-not $machine.Ok -or -not $database.Ok){throw 'RECOVER_RELEASE_LOCK_TARGET_IDENTITY_UNAVAILABLE'}
$scope=[pscustomobject]@{environment='test';host=$ServerHost;machineId=([string]$machine.Output).Trim();database=$DatabaseName;serverUuid=([string]$database.Output).Trim()}
$evidenceRoot="$RemoteAppDir/.release-state/test"
$evidence=Read-ReleaseDeploymentState -Root $evidenceRoot -Scope $scope -Capture {param($c) Invoke-RecoveryEvidenceCapture -Command $c}
Assert-ReleaseDeploymentGate -State $evidence -Recovery -ExpectedOperationId $ExpectedOperationId -ExpectedReleaseTag $ExpectedReleaseTag -ExpectedLeaseToken $ExpectedLeaseToken

$sqlLiteral = $ExpectedReleaseTag.Replace("'", "''")
$operationLiteral = $ExpectedOperationId.Replace("'", "''")
$executorHostLiteral = $ExpectedExecutorHost.Replace("'", "''")
$executorPidLiteral = $ExpectedExecutorPid.Replace("'", "''")
$executorIdentityLiteral = $ExpectedExecutorIdentity.Replace("'", "''")
$leaseTokenLiteral = $ExpectedLeaseToken.Replace("'", "''")
$operationReadback=if($evidence.gate.state -ceq 'READY') {
    "test -z `"`$(find '$evidenceRoot/operations' -mindepth 1 -maxdepth 1 -print -quit)`""
}else{
    "operation_hash=`$(sha256sum <'$evidenceRoot/operations/$($evidence.gate.attemptId).json')`ntest `"`${operation_hash%% *}`" = '$($evidence.gate.operationDigest)'"
}
$remote = @"
set -eu
test -f '$evidenceRoot/gate.lock'
test ! -L '$evidenceRoot/gate.lock'
exec 9<'$evidenceRoot/gate.lock'
flock -x 9
current=`$(sha256sum <'$evidenceRoot/gate.json')
test "`${current%% *}" = '$($evidence.gateDigest)'
$operationReadback
$mysqlCommand <<'SQL'
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
    if($null -ne $evidence.operation) {
        $operation=$evidence.operation
        $operation.state='ZERO_WRITE_FAILED';$operation.phase='explicit-zero-write-recovery'
        $operation.originalError='Explicit recovery confirmed zero runtime writes and FAILED lease'
        $leaseDigest=$operation.binding.leaseTokenDigest
        $fence=@"
$mysqlCommand <<'RECOVERY_FENCE_SQL'
SELECT CASE WHEN COUNT(*)=1 AND @@server_uuid='$($scope.serverUuid)' THEN 'EVIDENCE_FENCE_OK' ELSE 'EVIDENCE_FENCE_LOST' END FROM infra_release_operation_lock WHERE target_environment='test' AND operation_id='$operationLiteral' AND release_tag='$sqlLiteral' AND SHA2(lease_token,256)='$leaseDigest' AND status='FAILED';
RECOVERY_FENCE_SQL
"@
        $null=Save-ReleaseDeploymentState -Root $evidenceRoot -State $evidence -Operation $operation -Capture {param($c) Invoke-RecoveryEvidenceCapture -Command $c} -FenceCommand $fence
    }
    Write-Host "Release operation lock recovered: $ExpectedOperationId"
} finally {
}
