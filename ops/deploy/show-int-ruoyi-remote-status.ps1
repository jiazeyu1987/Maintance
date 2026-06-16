param(
    [string]$ServerHost,
    [string]$ServerUser = 'root',
    [string]$RemoteAppDir,
    [string]$RemoteDataRoot = '/var/lib/docker/intruoyi-data/runtime-data',
    [string]$RemoteDataDiskMount = '/var/lib/docker',
    [string]$RemoteDataDiskDevice = '/dev/vdb',
    [string]$RemoteMinioContainer = '',
    [ValidateSet('backend', 'frontend', 'full', 'website', 'onlyoffice')]
    [string]$Component = 'full',
    [int]$FrontendPort = 8081,
    [int]$BackendPort = 48081,
    [int]$WebsiteHostPort = 8083,
    [int]$OnlyOfficeHostPort = 8080,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Missing $Name command"
    }
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message"
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
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $null
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("show-int-ruoyi-status-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $stdoutPath = Join-Path $tempDir 'stdout.log'
    $stderrPath = Join-Path $tempDir 'stderr.log'
    try {
        $effectiveWorkingDirectory = if ($WorkingDirectory) { $WorkingDirectory } else { (Get-Location).Path }
        $process = Start-Process -FilePath $FilePath `
            -ArgumentList $ArgumentList `
            -WorkingDirectory $effectiveWorkingDirectory `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -NoNewWindow `
            -Wait `
            -PassThru
        $stdout = if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { '' }
        $stderr = if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { '' }
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
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList @(
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=5',
        '-o', 'StrictHostKeyChecking=no',
        "$ServerUser@$ServerHost",
        $Command
    )
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $cleanOutput = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    if ($result.ExitCode -ne 0) {
        Fail "SSH command failed: $Command`n$cleanOutput"
    }
    return $cleanOutput
}

function Probe-HttpStatus {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 10
        return "HTTP $($response.StatusCode)"
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

function Read-RemoteImageTag {
    $imageTag = Invoke-SshCapture "if [ -f '$RemoteAppDir/.env' ]; then sed -n 's/^IMAGE_TAG=//p' '$RemoteAppDir/.env' | head -n 1; fi"
    return $imageTag.Trim()
}

function Probe-HttpContentType {
    param(
        [string]$Url,
        [string]$ExpectedContentType
    )
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Head -TimeoutSec 10
        $rawContentType = $response.Headers['Content-Type']
        $contentType = if ($rawContentType -is [array]) { [string]$rawContentType[0] } else { [string]$rawContentType }
        if ([string]::IsNullOrWhiteSpace($contentType)) {
            return "ERROR: missing Content-Type"
        }
        if ($contentType -notlike "$ExpectedContentType*") {
            return "ERROR: expected $ExpectedContentType but got $contentType"
        }
        return "HTTP $($response.StatusCode) $contentType"
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

function Probe-FrontendPdfWorker {
    return Probe-HttpContentType -Url "http://${ServerHost}:$FrontendPort/pdfjs/pdf.worker.mjs" -ExpectedContentType 'application/javascript'
}

if ([string]::IsNullOrWhiteSpace($ServerHost)) {
    Fail 'Missing ServerHost'
}

if ([string]::IsNullOrWhiteSpace($RemoteAppDir)) {
    Fail 'Missing RemoteAppDir'
}

Require-Command 'ssh'
$runtimeDirState = Invoke-SshCapture "if [ -d '$RemoteAppDir' ]; then echo PRESENT; else echo MISSING; fi"
$dataDiskState = Invoke-SshCapture "data_disk_source=`$(findmnt -n -o SOURCE --target '$RemoteDataDiskMount' 2>/dev/null || true); data_dir_source=`$(df -P '$RemoteAppDir/data' 2>/dev/null | awk 'NR==2 {print `$1}'); if [ `"`$data_disk_source`" = '$RemoteDataDiskDevice' ] && [ `"`$data_dir_source`" = '$RemoteDataDiskDevice' ]; then echo READY; else echo `"INVALID data-disk=`$data_disk_source runtime-data=`$data_dir_source expected=$RemoteDataDiskDevice root=$RemoteDataRoot`"; fi"
$dockerState = Invoke-SshCapture "if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo PRESENT; else echo MISSING; fi"
$containerState = Invoke-SshCapture "docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | grep intruoyi || true"
$currentReleaseTag = Read-RemoteImageTag

$WEBSITE_HOST_PORT = $WebsiteHostPort

function Get-ContainerRuntimeState {
    param([string]$Name)
    if ($containerState -match $Name -and $containerState -match 'Up ') {
        return 'running'
    }
    if ($containerState -match $Name) {
        return 'stopped'
    }
    return 'missing'
}

function New-JsonStatus {
    param(
        [string]$Status,
        [string]$HttpStatus,
        [string]$RuntimeState,
        [string]$BlockedReason
    )
    return [ordered]@{
        status = $Status
        httpStatus = $HttpStatus
        runtimeState = $RuntimeState
        blockedReason = $BlockedReason
        currentReleaseTag = $currentReleaseTag
    }
}

if ($Json) {
    if ($runtimeDirState -ne 'PRESENT') {
        New-JsonStatus -Status 'error' -HttpStatus 'ERROR' -RuntimeState 'missing-runtime-dir' -BlockedReason "Missing remote runtime dir: $RemoteAppDir" | ConvertTo-Json -Depth 5
        exit 0
    }
    if ($dockerState -ne 'PRESENT') {
        New-JsonStatus -Status 'error' -HttpStatus 'ERROR' -RuntimeState 'missing-docker' -BlockedReason "Missing docker compose on ${ServerHost}" | ConvertTo-Json -Depth 5
        exit 0
    }
    if ($dataDiskState -ne 'READY') {
        New-JsonStatus -Status 'error' -HttpStatus 'ERROR' -RuntimeState 'invalid-runtime-data-disk' -BlockedReason "Runtime data directory is not on ${RemoteDataDiskDevice}: $dataDiskState" | ConvertTo-Json -Depth 5
        exit 0
    }

    switch ($Component) {
        'backend' {
            $backendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$BackendPort/actuator/health"
            $runtime = Get-ContainerRuntimeState -Name 'backend'
            $status = if ($backendProbe -like 'HTTP 2*' -or $backendProbe -like 'HTTP 3*') { 'running' } else { 'degraded' }
            New-JsonStatus -Status $status -HttpStatus $backendProbe -RuntimeState $runtime -BlockedReason $null | ConvertTo-Json -Depth 5
        }
        'frontend' {
            $frontendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$FrontendPort/"
            $pdfWorkerProbe = Probe-FrontendPdfWorker
            $runtime = Get-ContainerRuntimeState -Name 'frontend'
            $status = if (($frontendProbe -like 'HTTP 2*' -or $frontendProbe -like 'HTTP 3*') -and ($pdfWorkerProbe -like 'HTTP 2* application/javascript*')) { 'running' } else { 'degraded' }
            $blockedReason = if ($status -eq 'running') { $null } else { "frontend=$frontendProbe; pdfWorker=$pdfWorkerProbe" }
            New-JsonStatus -Status $status -HttpStatus "frontend=$frontendProbe; pdfWorker=$pdfWorkerProbe" -RuntimeState $runtime -BlockedReason $blockedReason | ConvertTo-Json -Depth 5
        }
        'website' {
            $websiteProbe = Probe-HttpStatus -Url "http://${ServerHost}:$WebsiteHostPort/"
            $runtime = Get-ContainerRuntimeState -Name 'website'
            $status = if ($websiteProbe -like 'HTTP 2*' -or $websiteProbe -like 'HTTP 3*') { 'running' } else { 'degraded' }
            New-JsonStatus -Status $status -HttpStatus $websiteProbe -RuntimeState $runtime -BlockedReason $null | ConvertTo-Json -Depth 5
        }
        'onlyoffice' {
            $onlyOfficeProbe = Probe-HttpStatus -Url "http://${ServerHost}:$OnlyOfficeHostPort/healthcheck"
            $runtime = Get-ContainerRuntimeState -Name 'onlyoffice'
            $status = if ($onlyOfficeProbe -like 'HTTP 2*' -or $onlyOfficeProbe -like 'HTTP 3*') { 'running' } else { 'degraded' }
            New-JsonStatus -Status $status -HttpStatus $onlyOfficeProbe -RuntimeState $runtime -BlockedReason $null | ConvertTo-Json -Depth 5
        }
        'full' {
            $backendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$BackendPort/actuator/health"
            $frontendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$FrontendPort/"
            $pdfWorkerProbe = Probe-FrontendPdfWorker
            $onlyOfficeProbe = Probe-HttpStatus -Url "http://${ServerHost}:$OnlyOfficeHostPort/healthcheck"
            $runtime = "backend=$(Get-ContainerRuntimeState -Name 'backend'); frontend=$(Get-ContainerRuntimeState -Name 'frontend'); onlyoffice=$(Get-ContainerRuntimeState -Name 'onlyoffice')"
            $status = if (($backendProbe -like 'HTTP 2*' -or $backendProbe -like 'HTTP 3*') -and ($frontendProbe -like 'HTTP 2*' -or $frontendProbe -like 'HTTP 3*') -and ($pdfWorkerProbe -like 'HTTP 2* application/javascript*') -and ($onlyOfficeProbe -like 'HTTP 2*' -or $onlyOfficeProbe -like 'HTTP 3*')) { 'running' } else { 'degraded' }
            $blockedReason = if ($status -eq 'running') { $null } else { "backend=$backendProbe; frontend=$frontendProbe; pdfWorker=$pdfWorkerProbe; OnlyOffice=$onlyOfficeProbe" }
            New-JsonStatus -Status $status -HttpStatus "backend=$backendProbe; frontend=$frontendProbe; pdfWorker=$pdfWorkerProbe; OnlyOffice=$onlyOfficeProbe" -RuntimeState $runtime -BlockedReason $blockedReason | ConvertTo-Json -Depth 5
        }
    }
    exit 0
}

Write-Host "Runtime directory: $RemoteAppDir -> $runtimeDirState"
Write-Host "Runtime data directory: $RemoteAppDir/data -> $dataDiskState"
Write-Host "Current release package: $(if ($currentReleaseTag) { $currentReleaseTag } else { '<none>' })"
Write-Host "Container status:"
if ($containerState) {
    Write-Host $containerState
} else {
    Write-Host "<none>"
}
if ($Component -eq 'backend' -or $Component -eq 'full') {
    $backendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$BackendPort/actuator/health"
    Write-Host "Backend health: $backendProbe"
}
if ($Component -eq 'frontend' -or $Component -eq 'full') {
    $frontendProbe = Probe-HttpStatus -Url "http://${ServerHost}:$FrontendPort/"
    Write-Host "Frontend status: $frontendProbe"
    $pdfWorkerProbe = Probe-FrontendPdfWorker
    Write-Host "Frontend PDF.js worker: $pdfWorkerProbe"
}
if ($Component -eq 'onlyoffice' -or $Component -eq 'full') {
    $onlyOfficeProbe = Probe-HttpStatus -Url "http://${ServerHost}:$OnlyOfficeHostPort/healthcheck"
    Write-Host "OnlyOffice status: $onlyOfficeProbe"
}
if ($Component -eq 'website') {
    $websiteProbe = Probe-HttpStatus -Url "http://${ServerHost}:$WebsiteHostPort/"
    Write-Host "Website status: $websiteProbe"
}
