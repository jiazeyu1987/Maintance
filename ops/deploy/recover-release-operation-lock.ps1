param(
    [Parameter(Mandatory = $true)]
    [string]$ServerHost,
    [string]$ServerUser = 'root',
    [Parameter(Mandatory = $true)]
    [string]$RemoteAppDir,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedOperationId,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedReleaseTag,
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

$sshArgs = @(
    '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=10',
    '-o', 'ServerAliveCountMax=3', '-o', 'StrictHostKeyChecking=no',
    "$ServerUser@$ServerHost"
)

$sqlLiteral = $ExpectedReleaseTag.Replace("'", "''")
$operationLiteral = $ExpectedOperationId.Replace("'", "''")
$remote = @"
set -eu
active_publishers=`$(ps -eo args= | grep -E 'publish-int-ruoyi\.ps1|recover-release-operation-lock\.ps1' | grep -v grep || true)
if [ -n "`$active_publishers" ]; then
  echo "RECOVER_BLOCKED_ACTIVE_EXECUTOR:`$active_publishers" >&2
  exit 41
fi
MYSQL_ROOT_PASSWORD=`$(grep -E '^MYSQL_ROOT_PASSWORD=' '$RemoteAppDir/.env' | head -n 1 | cut -d= -f2-)
if [ -z "`$MYSQL_ROOT_PASSWORD" ]; then
  echo 'RECOVER_BLOCKED_MISSING_DB_CREDENTIAL' >&2
  exit 42
fi
export MYSQL_ROOT_PASSWORD
docker exec -i -e MYSQL_PWD="`$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL'
SET @expected_operation_id := '$operationLiteral';
SET @expected_release_tag := '$sqlLiteral';
SELECT CASE
  WHEN NOT EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = @expected_operation_id
      AND release_tag = @expected_release_tag
      AND status = 'RUNNING'
  ) THEN 'RECOVER_BLOCKED_LOCK_NOT_FOUND'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_migration
    WHERE target_environment = 'test'
      AND release_tag = @expected_release_tag
      AND status IN ('RUNNING', 'APPLIED', 'FAILED')
  ) THEN 'RECOVER_BLOCKED_MIGRATION_EVIDENCE'
  ELSE 'RECOVER_ELIGIBLE'
END;
SQL
eligibility=`$(docker exec -i -e MYSQL_PWD="`$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL'
SELECT CASE
  WHEN NOT EXISTS (
    SELECT 1 FROM infra_release_operation_lock
    WHERE target_environment = 'test'
      AND operation_id = '$operationLiteral'
      AND release_tag = '$sqlLiteral'
      AND status = 'RUNNING'
  ) THEN 'RECOVER_BLOCKED_LOCK_NOT_FOUND'
  WHEN EXISTS (
    SELECT 1 FROM infra_release_migration
    WHERE target_environment = 'test'
      AND release_tag = '$sqlLiteral'
      AND status IN ('RUNNING', 'APPLIED', 'FAILED')
  ) THEN 'RECOVER_BLOCKED_MIGRATION_EVIDENCE'
  ELSE 'RECOVER_ELIGIBLE'
END;
SQL
)
if [ "`$eligibility" != 'RECOVER_ELIGIBLE' ]; then
  echo "`$eligibility" >&2
  exit 43
fi
docker exec -i -e MYSQL_PWD="`$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL'
UPDATE infra_release_operation_lock
SET status = 'FAILED',
    finished_at = NOW(),
    error_message = 'RECOVERED_BY_EXPLICIT_BUTTON_AFTER_EXECUTOR_AND_MIGRATION_CHECK',
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = 'test'
  AND operation_id = '$operationLiteral'
  AND release_tag = '$sqlLiteral'
  AND status = 'RUNNING';
SELECT CASE WHEN ROW_COUNT() = 1 THEN 'LOCK_RECOVERED' ELSE 'LOCK_RECOVERY_FAILED' END;
SQL
"@

$temp = Join-Path $env:TEMP ("recover-release-lock-" + [guid]::NewGuid().ToString('N') + ".sh")
try {
    [System.IO.File]::WriteAllText($temp, $remote, [System.Text.UTF8Encoding]::new($false))
    $result = Get-Content -LiteralPath $temp -Raw | & ssh @sshArgs "bash -s" 2>&1
    $exitCode = $LASTEXITCODE
    $result | ForEach-Object { Write-Host $_ }
    if ($exitCode -ne 0) {
        throw "RECOVER_RELEASE_LOCK_FAILED: exit code $exitCode"
    }
    if (-not (($result | Out-String) -match 'LOCK_RECOVERED')) {
        throw 'RECOVER_RELEASE_LOCK_FAILED: missing LOCK_RECOVERED evidence'
    }
    Write-Host "Release operation lock recovered: $ExpectedOperationId"
} finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}
