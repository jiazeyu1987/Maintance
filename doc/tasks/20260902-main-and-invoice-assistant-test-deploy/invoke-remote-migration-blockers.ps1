param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$remoteScript = @'
set -eu
mysql_password="$(docker exec intruoyi-mysql printenv MYSQL_ROOT_PASSWORD)"
cat <<'SQL' | docker exec -i -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
SELECT
    migration_id,
    status,
    release_tag,
    file_name,
    REPLACE(sha256, 'sha256:', ''),
    operation_id,
    DATE_FORMAT(finished_at, '%Y-%m-%dT%H:%i:%sZ'),
    CHAR_LENGTH(COALESCE(error_message, '')),
    SHA2(COALESCE(error_message, ''), 256)
FROM infra_release_migration
WHERE target_environment = 'test'
  AND status IN ('FAILED', 'RUNNING')
ORDER BY update_time ASC, id ASC;
SQL
'@

$payload = [System.Text.Encoding]::UTF8.GetBytes(($remoteScript -replace "`r`n", "`n"))
if ($payload.Length -eq 0) {
    throw 'Remote migration blocker payload is empty.'
}

$processInfo = [System.Diagnostics.ProcessStartInfo]::new()
$processInfo.FileName = 'ssh.exe'
$processInfo.UseShellExecute = $false
$processInfo.RedirectStandardInput = $true
$processInfo.RedirectStandardOutput = $true
$processInfo.RedirectStandardError = $true
[void]$processInfo.ArgumentList.Add('root@172.30.30.58')
[void]$processInfo.ArgumentList.Add('bash')
[void]$processInfo.ArgumentList.Add('-s')

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $processInfo
if (-not $process.Start()) {
    throw 'Unable to start SSH migration blocker probe.'
}

$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.StandardInput.BaseStream.Write($payload, 0, $payload.Length)
$process.StandardInput.Close()
$process.WaitForExit()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()

if ($process.ExitCode -ne 0) {
    throw ("SSH migration blocker probe failed with exit code {0}: {1}" -f $process.ExitCode, $stderr.Trim())
}

if ([string]::IsNullOrWhiteSpace($stdout)) {
    throw 'Remote migration blocker probe returned blank output.'
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllText($OutputPath, $stdout, [System.Text.UTF8Encoding]::new($false))

$hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$rowCount = @(Get-Content -LiteralPath $OutputPath -Encoding utf8 | Where-Object { $_.Trim() }).Count
Write-Output ("payload_bytes={0}" -f $payload.Length)
Write-Output ("blocker_rows={0}" -f $rowCount)
Write-Output ("blocker_probe_sha256={0}" -f $hash)
Write-Output 'REMOTE_MIGRATION_BLOCKER_PROBE_PASS'
