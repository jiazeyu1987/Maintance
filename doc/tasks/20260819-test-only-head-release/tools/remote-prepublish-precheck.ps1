param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseTag,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$remote = @'
set -euo pipefail
cd /opt/intruoyi/runtime
image_tag=$(awk -F= '$1=="IMAGE_TAG"{v=$2} END{print v}' .env 2>/dev/null || true)
edhr_endpoint=$(awk -F= '$1=="EDHR_S3_ENDPOINT"{v=$2} END{print v}' .env 2>/dev/null || true)
printf 'IMAGE_TAG=%s\n' "$image_tag"
printf 'EDHR_ENDPOINT=%s\n' "$edhr_endpoint"
printf 'COMPOSE_BEGIN\n'
(docker compose ps --format '{{.Name}}|{{.Image}}|{{.State}}|{{.Status}}' 2>/dev/null || docker-compose ps) | sed 's/[[:cntrl:]]//g'
printf 'COMPOSE_END\n'
backend_health=$(curl -fsS --max-time 10 http://127.0.0.1:48081/actuator/health 2>/dev/null | tr -d '\n' || true)
frontend_http=$(curl -o /dev/null -s -w '%{http_code}' --max-time 10 http://127.0.0.1:8081/ || true)
printf 'BACKEND_HEALTH=%s\n' "$backend_health"
printf 'FRONTEND_HTTP=%s\n' "$frontend_http"
mysql_pw=$(docker inspect intruoyi-mysql --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '$1=="MYSQL_ROOT_PASSWORD"{print $2; exit}')
printf 'LOCK_BEGIN\n'
docker exec -e MYSQL_PWD="$mysql_pw" intruoyi-mysql mysql -uroot -N -B ruoyi-vue-pro -e "SELECT CONCAT_WS('|', target_environment, operation_id, release_tag, status, COALESCE(error_message,'')) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING';" 2>/dev/null || true
printf 'LOCK_END\n'
printf 'MIGRATION_BEGIN\n'
docker exec -e MYSQL_PWD="$mysql_pw" intruoyi-mysql mysql -uroot -N -B ruoyi-vue-pro -e "SELECT CONCAT_WS('|', status, COUNT(*)) FROM infra_release_migration WHERE release_tag='__RELEASE_TAG__' GROUP BY status ORDER BY status;" 2>/dev/null || true
printf 'MIGRATION_END\n'
printf 'RECENT_LOCK_BEGIN\n'
docker exec -e MYSQL_PWD="$mysql_pw" intruoyi-mysql mysql -uroot -N -B ruoyi-vue-pro -e "SELECT CONCAT_WS('|', target_environment, release_tag, status, DATE_FORMAT(update_time, '%Y-%m-%d %H:%i:%s')) FROM infra_release_operation_lock WHERE target_environment='test' ORDER BY update_time DESC LIMIT 5;" 2>/dev/null || true
printf 'RECENT_LOCK_END\n'
'@

$remote = $remote.Replace('__RELEASE_TAG__', $ReleaseTag).Replace("`r`n", "`n")

$psi = [System.Diagnostics.ProcessStartInfo]::new('ssh')
foreach ($arg in @('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'root@172.30.30.58', 'bash -s')) {
    [void]$psi.ArgumentList.Add($arg)
}
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false

$process = [System.Diagnostics.Process]::Start($psi)
$bytes = [System.Text.Encoding]::UTF8.GetBytes($remote)
$process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
$process.StandardInput.Close()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
[void]$process.WaitForExit(30000)

$lines = $stdout -split "`r?`n"
function Get-Section([string]$Name) {
    $start = [array]::IndexOf($lines, "${Name}_BEGIN")
    $end = [array]::IndexOf($lines, "${Name}_END")
    if ($start -ge 0 -and $end -gt ($start + 1)) {
        return @($lines[($start + 1)..($end - 1)] | Where-Object { $_ -ne '' })
    }
    return @()
}

$imageTag = (($lines | Where-Object { $_ -like 'IMAGE_TAG=*' } | Select-Object -First 1) -replace '^IMAGE_TAG=', '')
$edhrEndpoint = (($lines | Where-Object { $_ -like 'EDHR_ENDPOINT=*' } | Select-Object -First 1) -replace '^EDHR_ENDPOINT=', '')
$backendHealth = (($lines | Where-Object { $_ -like 'BACKEND_HEALTH=*' } | Select-Object -First 1) -replace '^BACKEND_HEALTH=', '')
$frontendHttp = (($lines | Where-Object { $_ -like 'FRONTEND_HTTP=*' } | Select-Object -First 1) -replace '^FRONTEND_HTTP=', '')
$lockRows = Get-Section 'LOCK'
$migrationRows = Get-Section 'MIGRATION'

$summary = [ordered]@{
    status = 'passed'
    releaseTag = $ReleaseTag
    checkedAt = (Get-Date).ToString('o')
    sshExitCode = $process.ExitCode
    sshStderrSanitized = ($stderr -replace 'MYSQL_PWD=[^\s]+', 'MYSQL_PWD=<redacted>' -replace '-p\S+', '-p<redacted>')
    imageTagBeforePublish = $imageTag
    edhrEndpointBeforePublish = $edhrEndpoint
    composeRows = Get-Section 'COMPOSE'
    backendHealthBeforePublish = $backendHealth
    frontendHttpBeforePublish = $frontendHttp
    runningLockRows = $lockRows
    targetTagMigrationRows = $migrationRows
    recentTestLocks = Get-Section 'RECENT_LOCK'
    checks = [ordered]@{
        sshOk = ($process.ExitCode -eq 0 -or ($stdout -match 'IMAGE_TAG='))
        noRunningTestLock = ($lockRows.Count -eq 0)
        noTargetTagMigrations = ($migrationRows.Count -eq 0)
        backendHealthReadable = ($backendHealth -match 'UP')
        frontendHttp200 = ($frontendHttp -eq '200')
    }
}

$failed = @()
foreach ($prop in $summary.checks.GetEnumerator()) {
    if ($prop.Value -ne $true) {
        $failed += $prop.Key
    }
}
$summary.status = if ($failed.Count -eq 0) { 'passed' } else { 'failed' }
$summary.failedChecks = $failed

$json = $summary | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
$json

if ($failed.Count -gt 0) {
    exit 2
}
