param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$remoteScript = @'
set -eu
mysql_password="$(docker exec intruoyi-mysql printenv MYSQL_ROOT_PASSWORD)"
cat <<'SQL' | docker exec -i -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
SELECT COALESCE(
    JSON_OBJECTAGG(
        migration_id,
        JSON_OBJECT(
            'sha256', REPLACE(sha256, 'sha256:', ''),
            'status', CASE WHEN status IN ('APPLIED', 'SKIPPED_ALREADY_APPLIED') THEN 'APPLIED' ELSE status END
        )
    ),
    JSON_OBJECT()
)
FROM infra_release_migration
WHERE target_environment = 'test';
SQL
'@

$payload = [System.Text.Encoding]::UTF8.GetBytes(($remoteScript -replace "`r`n", "`n"))
if ($payload.Length -eq 0) {
    throw 'Remote target-state payload is empty.'
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
    throw 'Unable to start SSH target-state probe.'
}

$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.StandardInput.BaseStream.Write($payload, 0, $payload.Length)
$process.StandardInput.Close()
$process.WaitForExit()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()

if ($process.ExitCode -ne 0) {
    throw ("SSH target-state probe failed with exit code {0}: {1}" -f $process.ExitCode, $stderr.Trim())
}

$targetState = $stdout.Trim()
if ([string]::IsNullOrWhiteSpace($targetState)) {
    throw 'Remote target-state probe returned blank output.'
}

try {
    $parsed = $targetState | ConvertFrom-Json
} catch {
    throw ("Remote target-state output is not JSON: {0}" -f $_.Exception.Message)
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllText($OutputPath, ($targetState + "`n"), [System.Text.UTF8Encoding]::new($false))
$hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$entryCount = @($parsed.PSObject.Properties).Count
Write-Output ("payload_bytes={0}" -f $payload.Length)
Write-Output ("target_state_entries={0}" -f $entryCount)
Write-Output ("target_state_sha256={0}" -f $hash)
Write-Output 'REMOTE_TARGET_STATE_PROBE_PASS'
