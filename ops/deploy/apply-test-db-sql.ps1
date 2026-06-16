param(
    [Parameter(Mandatory = $true)]
    [string]$SqlPath,
    [string]$ServerHost = '172.30.30.58',
    [string]$ExpectedServerHost = '172.30.30.58',
    [string]$ServerUser = 'root',
    [string]$RemoteAppDir = '/opt/intruoyi/runtime',
    [string]$RemoteWorkDir = '/opt/intruoyi/runtime/tmp/db-quick-apply',
    [string]$MySqlContainer = 'intruoyi-mysql',
    [string]$DatabaseName = 'ruoyi-vue-pro',
    [int]$BackendPort = 48081,
    [string]$Reason = ''
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Missing command: $Name"
    }
}

function Write-Utf8LfNoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalized = ($Content -replace "`r`n", "`n") -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function ConvertTo-ShellSingleQuotedLiteral([string]$Value) {
    return "'" + ($Value -replace "'", "'\''") + "'"
}

function Get-SshCommonOptions {
    return @(
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=10',
        '-o', 'ConnectionAttempts=1',
        '-o', 'ServerAliveInterval=10',
        '-o', 'ServerAliveCountMax=3',
        '-o', 'StrictHostKeyChecking=no'
    )
}

function Invoke-ProcessCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @()
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("apply-test-db-sql-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $stdoutPath = Join-Path $tempDir 'stdout.log'
    $stderrPath = Join-Path $tempDir 'stderr.log'
    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $stdout = if (Test-Path -LiteralPath $stdoutPath) {
            [System.IO.File]::ReadAllText($stdoutPath, [System.Text.Encoding]::UTF8)
        } else {
            ''
        }
        $stderr = if (Test-Path -LiteralPath $stderrPath) {
            [System.IO.File]::ReadAllText($stderrPath, [System.Text.Encoding]::UTF8)
        } else {
            ''
        }
        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output = (($stdout, $stderr) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
        }
    } finally {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}

function Invoke-SshCommand([string]$Command) {
    $arguments = @('-n') + (Get-SshCommonOptions) + @("${ServerUser}@${ServerHost}", $Command)
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList $arguments
    if ($result.ExitCode -ne 0) {
        Fail "SSH command failed on ${ServerHost}: $($result.Output)"
    }
    if (-not [string]::IsNullOrWhiteSpace($result.Output)) {
        Write-Host $result.Output
    }
}

function Copy-ToRemote {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LocalPath,
        [Parameter(Mandatory = $true)]
        [string]$RemotePath
    )

    $arguments = (Get-SshCommonOptions) + @($LocalPath, "${ServerUser}@${ServerHost}:${RemotePath}")
    $result = Invoke-ProcessCapture -FilePath 'scp' -ArgumentList $arguments
    if ($result.ExitCode -ne 0) {
        Fail "SCP failed to ${ServerHost}: $($result.Output)"
    }
}

function Assert-SafeIdentifier([string]$Name, [string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^[A-Za-z0-9_.-]+$') {
        Fail "$Name contains unsupported characters: $Value"
    }
}

if ([string]::IsNullOrWhiteSpace($ServerHost)) {
    Fail 'Missing ServerHost'
}
if ([string]::IsNullOrWhiteSpace($ExpectedServerHost)) {
    Fail 'Missing ExpectedServerHost'
}
if ($ServerHost -ne $ExpectedServerHost) {
    Fail "target proof failed: expected test server $ExpectedServerHost, got ServerHost=$ServerHost"
}
if ($ExpectedServerHost -ne '172.30.30.58') {
    Fail "ExpectedServerHost must be 172.30.30.58"
}
if ([string]::IsNullOrWhiteSpace($RemoteAppDir)) {
    Fail 'Missing RemoteAppDir'
}

Require-Command 'ssh'
Require-Command 'scp'
Assert-SafeIdentifier -Name 'MySqlContainer' -Value $MySqlContainer
Assert-SafeIdentifier -Name 'DatabaseName' -Value $DatabaseName

try {
    $resolvedSqlPath = [System.IO.Path]::GetFullPath($SqlPath)
} catch {
    Fail "Invalid SqlPath: $SqlPath. $($_.Exception.Message)"
}
if (-not [System.IO.File]::Exists($resolvedSqlPath)) {
    Fail "SQL file does not exist: $resolvedSqlPath"
}
if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals([System.IO.Path]::GetExtension($resolvedSqlPath), '.sql')) {
    Fail 'SqlPath must point to a .sql file'
}
$sqlFileInfo = Get-Item -LiteralPath $resolvedSqlPath
if ($sqlFileInfo.Length -le 0) {
    Fail 'SQL file is empty'
}
$sqlText = [System.IO.File]::ReadAllText($resolvedSqlPath, [System.Text.Encoding]::UTF8)
if ($sqlText -match '(?is)\bdrop\s+database\b') {
    Fail 'SQL contains forbidden drop database statement'
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$remoteSql = "$RemoteWorkDir/apply-test-db-sql-$stamp.sql"
$remoteScript = "$RemoteWorkDir/apply-test-db-sql-$stamp.sh"
$localScript = Join-Path ([System.IO.Path]::GetTempPath()) ("apply-test-db-sql-" + [System.Guid]::NewGuid().ToString("N") + ".sh")

$remoteApplyScript = @'
#!/usr/bin/env sh
set -eu

REMOTE_SQL="$1"
REMOTE_APP_DIR="$2"
MYSQL_CONTAINER="$3"
DATABASE_NAME="$4"
BACKEND_PORT="$5"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

[ "$REMOTE_APP_DIR" = "/opt/intruoyi/runtime" ] || fail "RemoteAppDir proof failed: $REMOTE_APP_DIR"
[ -d "$REMOTE_APP_DIR" ] || fail "Missing remote runtime dir: $REMOTE_APP_DIR"
[ -s "$REMOTE_SQL" ] || fail "SQL file is empty"
command -v docker >/dev/null 2>&1 || fail "Missing docker on remote server"
command -v curl >/dev/null 2>&1 || fail "Missing curl on remote server"

docker ps --format "{{.Names}}" | grep -Fx "$MYSQL_CONTAINER" >/dev/null || fail "Missing MySQL container: $MYSQL_CONTAINER"
docker exec "$MYSQL_CONTAINER" sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqladmin -uroot ping --silent' >/dev/null

tenant_count="$(docker exec -e MYSQL_DATABASE="$DATABASE_NAME" "$MYSQL_CONTAINER" sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = '\''system_tenant'\'';"')"
[ "$tenant_count" = "1" ] || fail "system_tenant preflight failed for database: $DATABASE_NAME"

cat "$REMOTE_SQL" | docker exec -i -e MYSQL_DATABASE="$DATABASE_NAME" "$MYSQL_CONTAINER" sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 "$MYSQL_DATABASE"'
curl -fsS "http://127.0.0.1:$BACKEND_PORT/actuator/health" >/tmp/apply-test-db-sql-health.json
echo "APPLY_TEST_DB_SQL_OK"
'@

Write-Utf8LfNoBomFile -Path $localScript -Content $remoteApplyScript

try {
    Info "Applying SQL to test server database: $resolvedSqlPath"
    if (-not [string]::IsNullOrWhiteSpace($Reason)) {
        Info "Reason: $Reason"
    }
    Invoke-SshCommand "mkdir -p $(ConvertTo-ShellSingleQuotedLiteral $RemoteWorkDir)"
    Invoke-SshCommand "test -d $(ConvertTo-ShellSingleQuotedLiteral $RemoteAppDir)"
    Copy-ToRemote -LocalPath $resolvedSqlPath -RemotePath $remoteSql
    Copy-ToRemote -LocalPath $localScript -RemotePath $remoteScript
    Invoke-SshCommand "chmod 700 $(ConvertTo-ShellSingleQuotedLiteral $remoteScript)"

    $command = "sh $(ConvertTo-ShellSingleQuotedLiteral $remoteScript) " +
        "$(ConvertTo-ShellSingleQuotedLiteral $remoteSql) " +
        "$(ConvertTo-ShellSingleQuotedLiteral $RemoteAppDir) " +
        "$(ConvertTo-ShellSingleQuotedLiteral $MySqlContainer) " +
        "$(ConvertTo-ShellSingleQuotedLiteral $DatabaseName) " +
        "$(ConvertTo-ShellSingleQuotedLiteral ([string]$BackendPort))"
    Invoke-SshCommand $command
    Invoke-SshCommand "rm -f $(ConvertTo-ShellSingleQuotedLiteral $remoteSql) $(ConvertTo-ShellSingleQuotedLiteral $remoteScript)"
    Info "Test server database SQL quick apply completed"
} finally {
    if (Test-Path -LiteralPath $localScript) {
        Remove-Item -LiteralPath $localScript -Force
    }
}
