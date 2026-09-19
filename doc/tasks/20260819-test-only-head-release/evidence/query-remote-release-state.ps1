param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$ReleaseTag
)

$ErrorActionPreference = 'Stop'

$template = @'
set -eu
TAG='__RELEASE_TAG__'
run_sql() {
  docker exec -i intruoyi-mysql sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro'
}
printf 'LOCK_BEGIN\n'
cat <<SQL | run_sql
SELECT CONCAT_WS('\t', target_environment, operation_id, release_tag, status)
FROM infra_release_operation_lock
WHERE target_environment='test' AND release_tag='$TAG' AND deleted=b'0';
SQL
printf 'LOCK_END\n'
printf 'COUNTS_BEGIN\n'
cat <<SQL | run_sql
SELECT CONCAT_WS('\t', status, COUNT(*))
FROM infra_release_migration
WHERE target_environment='test' AND release_tag='$TAG' AND deleted=b'0'
GROUP BY status ORDER BY status;
SQL
printf 'COUNTS_END\n'
printf 'BAD_BEGIN\n'
cat <<SQL | run_sql
SELECT COUNT(*)
FROM infra_release_migration
WHERE target_environment='test' AND release_tag='$TAG' AND deleted=b'0'
  AND status IN ('FAILED','RUNNING');
SQL
printf 'BAD_END\n'
printf 'FAILED_BEGIN\n'
cat <<SQL | run_sql
SELECT CONCAT_WS('\t', migration_id, file_name, HEX(LEFT(COALESCE(error_message, ''), 512)))
FROM infra_release_migration
WHERE target_environment='test' AND release_tag='$TAG' AND deleted=b'0'
  AND status='FAILED'
ORDER BY update_time DESC;
SQL
printf 'FAILED_END\n'
'@

$remoteScript = $template.Replace('__RELEASE_TAG__', $ReleaseTag)
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = 'ssh'
$startInfo.Arguments = '-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@172.30.30.58 bash -s'
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
$process.Start() | Out-Null
$bytes = [System.Text.Encoding]::UTF8.GetBytes($remoteScript)
$process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
$process.StandardInput.Close()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()

if ($process.ExitCode -ne 0) {
    throw "Remote release-state query failed with exit code $($process.ExitCode): $($stderr.Trim())"
}

$lines = @($stdout -split "`r?`n")
function Get-MarkerLines([string]$Start, [string]$End) {
    $startIndex = [Array]::IndexOf($lines, $Start)
    $endIndex = [Array]::IndexOf($lines, $End)
    if ($startIndex -lt 0 -or $endIndex -le $startIndex) {
        throw "Missing output markers: $Start / $End"
    }
    if ($endIndex -eq $startIndex + 1) {
        return @()
    }
    return @($lines[($startIndex + 1)..($endIndex - 1)] | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_) -and
        $_ -notmatch '^mysql: \[Warning\] Using a password on the command line interface can be insecure\.$'
    })
}

$lockRows = @()
foreach ($line in (Get-MarkerLines 'LOCK_BEGIN' 'LOCK_END')) {
    $parts = $line -split "`t", 4
    if ($parts.Count -ne 4) {
        throw "Invalid lock row: $line"
    }
    $lockRows += [pscustomobject]@{
        environment = $parts[0]
        operationId = $parts[1]
        releaseTag = $parts[2]
        status = $parts[3]
    }
}

$migrationCounts = [ordered]@{}
foreach ($line in (Get-MarkerLines 'COUNTS_BEGIN' 'COUNTS_END')) {
    $parts = $line -split "`t", 2
    if ($parts.Count -ne 2) {
        throw "Invalid migration count row: $line"
    }
    $migrationCounts[$parts[0]] = [int]$parts[1]
}

$badLines = @(Get-MarkerLines 'BAD_BEGIN' 'BAD_END')
if ($badLines.Count -ne 1) {
    throw 'Expected exactly one bad migration count.'
}

$failedRows = @()
foreach ($line in (Get-MarkerLines 'FAILED_BEGIN' 'FAILED_END')) {
    $parts = $line -split "`t", 3
    if ($parts.Count -ne 3) {
        throw "Invalid failed migration row: $line"
    }
    $failedRows += [pscustomobject]@{
        migrationId = $parts[0]
        fileName = $parts[1]
        errorMessage = if ([string]::IsNullOrWhiteSpace($parts[2])) {
            ''
        } else {
            [System.Text.Encoding]::UTF8.GetString([Convert]::FromHexString($parts[2]))
        }
    }
}

[pscustomobject]@{
    releaseTag = $ReleaseTag
    checkedAt = (Get-Date).ToString('o')
    lockRows = $lockRows
    migrationCounts = $migrationCounts
    badMigrationCount = [int]$badLines[0]
    failedRows = $failedRows
} | ConvertTo-Json -Depth 6
