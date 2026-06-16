param(
    [ValidateSet('status', 'cleanup')]
    [string]$Mode = 'status',
    [ValidateSet('test', 'prod', 'backup')]
    [string]$TargetEnvironment = 'test',
    [string]$ServerHost,
    [string]$ServerUser = 'root',
    [string]$Reason = '',
    [string]$RequestedBy = '',
    [string]$ProdConfirmText = ''
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ExpectedHosts = @{
    test = '172.30.30.58'
    prod = '172.30.30.57'
    backup = '172.30.30.59'
}
$BackupTmpPath = '/opt/intruoyi/ops/backup/tmp'
$SystemTmpPath = '/tmp'

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Missing required command: $Name"
    }
}

function Assert-TargetBoundary {
    if (-not $ExpectedHosts.ContainsKey($TargetEnvironment)) {
        Fail 'remote root disk operation requires targetEnvironment=test/prod/backup'
    }
    if ([string]::IsNullOrWhiteSpace($ServerHost)) {
        Fail 'Missing ServerHost'
    }
    $expectedHost = [string]$ExpectedHosts[$TargetEnvironment]
    if ($ServerHost -ne $expectedHost) {
        Fail "target proof failed: expected $TargetEnvironment server $expectedHost, got ServerHost=$ServerHost"
    }
    if ($Mode -eq 'cleanup' -and ($TargetEnvironment -eq 'prod' -or $TargetEnvironment -eq 'backup') -and $ProdConfirmText -ne 'PROD') {
        Fail 'protected remote root cleanup requires ProdConfirmText=PROD'
    }
}

function Remove-SshNoise([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ''
    }
    return (($Text -split "`r?`n") | Where-Object {
        $_ -and $_ -notlike 'close - IO is still pending on closed socket.*'
    }) -join "`n"
}

function Invoke-ProcessCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @()
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("intruoyi-remote-root-disk-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $stdoutPath = Join-Path $tempDir 'stdout.log'
    $stderrPath = Join-Path $tempDir 'stderr.log'
    try {
        $process = Start-Process -FilePath $FilePath `
            -ArgumentList $ArgumentList `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -NoNewWindow `
            -Wait `
            -PassThru
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
        return @{
            ExitCode = $process.ExitCode
            StdOut = $stdout
            StdErr = $stderr
        }
    } finally {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-SshCapture {
    param([string]$Command)
    Assert-TargetBoundary
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList @(
        '-n',
        '-T',
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=8',
        '-o', 'StrictHostKeyChecking=no',
        "$ServerUser@$ServerHost",
        $Command
    )
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $cleanOutput = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    if ($result.ExitCode -ne 0) {
        Fail "SSH command failed on remote server ${ServerHost}: $cleanOutput"
    }
    return $cleanOutput
}

function Convert-MetricLines {
    param([string]$Text)
    $map = @{}
    foreach ($line in ($Text -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $index = $line.IndexOf('=')
        if ($index -le 0) {
            Fail "Invalid metric line from remote server: $line"
        }
        $map[$line.Substring(0, $index)] = $line.Substring($index + 1)
    }
    $expectedHost = [string]$ExpectedHosts[$TargetEnvironment]
    if ($map['serverHost'] -ne $expectedHost -or $map['targetEnvironment'] -ne $TargetEnvironment) {
        Fail "status output does not prove $TargetEnvironment server $expectedHost"
    }
    if ($map['mountPoint'] -ne '/') {
        Fail 'status output mountPoint must be /'
    }
    return [ordered]@{
        targetEnvironment = $map['targetEnvironment']
        serverHost = $map['serverHost']
        mountPoint = $map['mountPoint']
        filesystem = $map['filesystem']
        totalBytes = [int64]$map['totalBytes']
        usedBytes = [int64]$map['usedBytes']
        availableBytes = [int64]$map['availableBytes']
        usagePercent = [double]$map['usagePercent']
        inodeTotal = [int64]$map['inodeTotal']
        inodeUsed = [int64]$map['inodeUsed']
        inodeAvailable = [int64]$map['inodeAvailable']
        inodeUsagePercent = [double]$map['inodeUsagePercent']
        backupTempBytes = [int64]$map['backupTempBytes']
        tmpBytes = [int64]$map['tmpBytes']
        sampledAt = $map['sampledAt']
    }
}

function Get-RemoteStatus {
    $expectedHost = [string]$ExpectedHosts[$TargetEnvironment]
    $command = @'
set -eu
EXPECTED_IP='__EXPECTED_IP__'
TARGET_ENVIRONMENT='__TARGET_ENVIRONMENT__'
BACKUP_TMP='/opt/intruoyi/ops/backup/tmp'
SYSTEM_TMP='/tmp'
ips="$(hostname -I 2>/dev/null || true)"
printf '%s\n' "$ips" | grep -qw "$EXPECTED_IP" || { echo "target proof failed: hostname -I=$ips expected=$EXPECTED_IP" >&2; exit 12; }
df_line="$(df -P -B1 / | sed -n '2p')"
set -- $df_line
filesystem="$1"
total="$2"
used="$3"
available="$4"
usage="$5"
mount_point="$6"
inode_line="$(df -Pi / | sed -n '2p')"
set -- $inode_line
inode_total="$2"
inode_used="$3"
inode_available="$4"
inode_usage="$5"
backup_bytes="$(du -sxB1 "$BACKUP_TMP" 2>/dev/null | cut -f1 | head -n 1)"
tmp_bytes="$(du -sxB1 "$SYSTEM_TMP" 2>/dev/null | cut -f1 | head -n 1)"
backup_bytes="${backup_bytes:-0}"
tmp_bytes="${tmp_bytes:-0}"
usage="${usage%\%}"
inode_usage="${inode_usage%\%}"
echo "targetEnvironment=$TARGET_ENVIRONMENT"
echo "serverHost=$EXPECTED_IP"
echo "mountPoint=$mount_point"
echo "filesystem=$filesystem"
echo "totalBytes=$total"
echo "usedBytes=$used"
echo "availableBytes=$available"
echo "usagePercent=$usage"
echo "inodeTotal=$inode_total"
echo "inodeUsed=$inode_used"
echo "inodeAvailable=$inode_available"
echo "inodeUsagePercent=$inode_usage"
echo "backupTempBytes=$backup_bytes"
echo "tmpBytes=$tmp_bytes"
echo "sampledAt=$(date '+%Y-%m-%dT%H:%M:%S')"
'@
    $command = $command.Replace('__EXPECTED_IP__', $expectedHost).Replace('__TARGET_ENVIRONMENT__', $TargetEnvironment)
    return Convert-MetricLines (Invoke-SshCapture $command)
}

function Invoke-RemoteCleanup {
    $expectedHost = [string]$ExpectedHosts[$TargetEnvironment]
    $command = @'
set -eu
EXPECTED_IP='__EXPECTED_IP__'
BACKUP_TMP='/opt/intruoyi/ops/backup/tmp'
SYSTEM_TMP='/tmp'
ips="$(hostname -I 2>/dev/null || true)"
printf '%s\n' "$ips" | grep -qw "$EXPECTED_IP" || { echo "target proof failed: hostname -I=$ips expected=$EXPECTED_IP" >&2; exit 12; }
if [ "$BACKUP_TMP" != '/opt/intruoyi/ops/backup/tmp' ] || [ "$SYSTEM_TMP" != '/tmp' ]; then
  echo 'cleanup path guard failed' >&2
  exit 13
fi
backup_count=0
tmp_count=0
if [ -d "$BACKUP_TMP" ]; then
  backup_count="$(find "$BACKUP_TMP" -xdev -mindepth 1 -maxdepth 1 | wc -l)"
  find "$BACKUP_TMP" -xdev -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
fi
if [ -d "$SYSTEM_TMP" ]; then
  tmp_count="$(find "$SYSTEM_TMP" -xdev -mindepth 1 -maxdepth 1 \
    ! -name 'systemd-private-*' \
    ! -name '.X11-unix' \
    ! -name '.ICE-unix' \
    ! -name '.font-unix' \
    ! -name '.Test-unix' | wc -l)"
  find "$SYSTEM_TMP" -xdev -mindepth 1 -maxdepth 1 \
    ! -name 'systemd-private-*' \
    ! -name '.X11-unix' \
    ! -name '.ICE-unix' \
    ! -name '.font-unix' \
    ! -name '.Test-unix' \
    -exec rm -rf -- {} +
fi
echo "deletedEntryCount=$((backup_count + tmp_count))"
'@
    $command = $command.Replace('__EXPECTED_IP__', $expectedHost)
    $output = Invoke-SshCapture $command
    foreach ($line in ($output -split "`r?`n")) {
        if ($line -like 'deletedEntryCount=*') {
            return [int]($line.Substring('deletedEntryCount='.Length))
        }
    }
    Fail "Cleanup result missing deletedEntryCount: $output"
}

Require-Command 'ssh'
Assert-TargetBoundary

if ($Mode -eq 'status') {
    Get-RemoteStatus | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Reason)) {
    Fail 'Missing cleanup reason'
}

$before = Get-RemoteStatus
$deletedEntryCount = Invoke-RemoteCleanup
$after = Get-RemoteStatus
[ordered]@{
    targetEnvironment = $TargetEnvironment
    serverHost = [string]$ExpectedHosts[$TargetEnvironment]
    cleanupPaths = @($BackupTmpPath, $SystemTmpPath)
    before = $before
    after = $after
    deletedEntryCount = $deletedEntryCount
    requestedBy = $RequestedBy
    reason = $Reason
    cleanedAt = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
} | ConvertTo-Json -Depth 8 -Compress
