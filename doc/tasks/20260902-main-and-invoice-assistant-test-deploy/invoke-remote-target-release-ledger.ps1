param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')]
    [string]$ReleaseTag,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$remoteScript = @'
set -eu
mysql_password="$(docker exec intruoyi-mysql printenv MYSQL_ROOT_PASSWORD)"
cat <<'SQL' | docker exec -i -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
SELECT CONCAT('target_failed_running=', COUNT(*))
FROM infra_release_migration
WHERE target_environment = 'test'
  AND release_tag = '__RELEASE_TAG__'
  AND status IN ('FAILED', 'RUNNING');
SELECT CONCAT('target_lock_running=', COUNT(*))
FROM infra_release_operation_lock
WHERE target_environment = 'test'
  AND release_tag = '__RELEASE_TAG__'
  AND status = 'RUNNING';
SQL
'@

$remoteScript = $remoteScript.Replace('__RELEASE_TAG__', $ReleaseTag)
$payload = [System.Text.Encoding]::UTF8.GetBytes(($remoteScript -replace "`r`n", "`n"))
if ($payload.Length -eq 0) {
    throw 'Remote target release ledger payload is empty.'
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
    throw 'Unable to start SSH target release ledger probe.'
}

$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.StandardInput.BaseStream.Write($payload, 0, $payload.Length)
$process.StandardInput.Close()
$process.WaitForExit()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()

if ($process.ExitCode -ne 0) {
    throw ("SSH target release ledger probe failed with exit code {0}: {1}" -f $process.ExitCode, $stderr.Trim())
}

if ([string]::IsNullOrWhiteSpace($stdout)) {
    throw 'Remote target release ledger probe returned blank output.'
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllText($OutputPath, $stdout, [System.Text.UTF8Encoding]::new($false))

$hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output ("payload_bytes={0}" -f $payload.Length)
Write-Output ("target_ledger_sha256={0}" -f $hash)
Write-Output 'REMOTE_TARGET_RELEASE_LEDGER_PROBE_PASS'
