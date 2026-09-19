param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$remoteScript = @'
set -eu
printf 'image_tag='; grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env | cut -d= -f2
printf 'backend_image='; docker inspect -f '{{.Config.Image}}' intruoyi-backend
printf 'backend_state='; docker inspect -f '{{.State.Status}}' intruoyi-backend
printf 'frontend_image='; docker inspect -f '{{.Config.Image}}' intruoyi-frontend
printf 'frontend_state='; docker inspect -f '{{.State.Status}}' intruoyi-frontend
printf 'assistant_image='; docker inspect -f '{{.Config.Image}}' erp-invoice-voucher-print-assistant
printf 'assistant_state='; docker inspect -f '{{.State.Status}}' erp-invoice-voucher-print-assistant
printf 'assistant_unit='; systemctl is-active erp-invoice-voucher-print-assistant.service
printf 'backend_health='; curl -fsS http://127.0.0.1:48081/actuator/health
printf '\nfrontend_http='; curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/
printf '\nassistant_http='; curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18733/
printf '\n'
mysql_password="$(docker exec intruoyi-mysql printenv MYSQL_ROOT_PASSWORD)"
cat <<'SQL' | docker exec -i -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
SHOW COLUMNS FROM infra_release_operation_lock LIKE 'status';
SELECT CONCAT('running_locks=', COUNT(*)) FROM infra_release_operation_lock WHERE status = 'RUNNING';
SELECT CONCAT('test_failed_running_migrations=', COUNT(*)) FROM infra_release_migration WHERE target_environment = 'test' AND status IN ('FAILED', 'RUNNING');
SQL
'@

$payload = [System.Text.Encoding]::UTF8.GetBytes(($remoteScript -replace "`r`n", "`n"))
if ($payload.Length -eq 0) {
    throw 'Remote prepublish payload is empty.'
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
    throw 'Unable to start SSH prepublish probe.'
}

$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.StandardInput.BaseStream.Write($payload, 0, $payload.Length)
$process.StandardInput.Close()
$process.WaitForExit()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()

if ($process.ExitCode -ne 0) {
    throw ("SSH prepublish probe failed with exit code {0}: {1}" -f $process.ExitCode, $stderr.Trim())
}

if ([string]::IsNullOrWhiteSpace($stdout)) {
    throw 'Remote prepublish probe returned blank output.'
}

$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllText($OutputPath, $stdout, [System.Text.UTF8Encoding]::new($false))

$requiredPrefixes = @(
    'image_tag=', 'backend_image=', 'backend_state=', 'frontend_image=', 'frontend_state=',
    'assistant_image=', 'assistant_state=', 'assistant_unit=', 'backend_health=', 'frontend_http=',
    'assistant_http=', 'running_locks=', 'test_failed_running_migrations='
)
foreach ($prefix in $requiredPrefixes) {
    if ($stdout -notmatch [regex]::Escape($prefix)) {
        throw "Remote prepublish output is missing required field: $prefix"
    }
}

$hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output ("payload_bytes={0}" -f $payload.Length)
Write-Output ("probe_sha256={0}" -f $hash)
Write-Output 'REMOTE_PREPUBLISH_PROBE_PASS'
