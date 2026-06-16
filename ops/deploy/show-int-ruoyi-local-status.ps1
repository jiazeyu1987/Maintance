param(
    [ValidateSet('frontend', 'backend', 'full', 'website')]
    [string]$Component = 'full',
    [string]$WorktreeName,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'worktree-port-map.ps1')

$EffectiveWorktreeName = if ([string]::IsNullOrWhiteSpace($WorktreeName)) { 'int_main' } else { $WorktreeName }

function Probe-HttpStatus {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
        return "HTTP $($response.StatusCode)"
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

function Test-PortListening {
    param([int]$Port)
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return ($connections | Measure-Object).Count -gt 0
    } catch {
        $netstat = netstat -ano | Select-String -Pattern (":$Port\s+")
        return $null -ne $netstat
    }
}

function New-Status {
    param(
        [string]$Name,
        [int]$Port,
        [string]$Url
    )
    $httpStatus = Probe-HttpStatus -Url $Url
    $listening = Test-PortListening -Port $Port
    $status = if ($httpStatus -like 'HTTP 2*' -or $httpStatus -like 'HTTP 3*') {
        'running'
    } elseif ($listening) {
        'degraded'
    } else {
        'stopped'
    }
    return [ordered]@{
        status = $status
        httpStatus = $httpStatus
        runtimeState = if ($listening) { 'listening' } else { 'not-listening' }
        blockedReason = $null
    }
}

function New-OnlyOfficeStatus {
    $httpStatus = Probe-HttpStatus -Url 'http://127.0.0.1:8080/healthcheck'
    $listening = Test-PortListening -Port 8080
    $status = if ($httpStatus -like 'HTTP 2*' -or $httpStatus -like 'HTTP 3*') {
        'running'
    } elseif ($listening) {
        'degraded'
    } else {
        'stopped'
    }
    return [ordered]@{
        status = $status
        httpStatus = $httpStatus
        runtimeState = if ($listening) { 'listening' } else { 'not-listening' }
        blockedReason = $null
    }
}

if ($Component -eq 'full') {
    $portContext = Get-IntRuoyiWorktreePortContext -WorktreeName $EffectiveWorktreeName
    $frontend = New-Status -Name 'intruoyi-frontend' -Port $portContext.FrontendPort -Url "http://127.0.0.1:$($portContext.FrontendPort)/"
    $backend = New-Status -Name 'intruoyi-backend' -Port $portContext.BackendPort -Url "http://127.0.0.1:$($portContext.BackendPort)/actuator/health"
    $onlyOffice = New-OnlyOfficeStatus
    $combinedStatus = if ($frontend.status -eq 'running' -and $backend.status -eq 'running') { 'running' } else { 'degraded' }
    $result = [ordered]@{
        worktree = $portContext.Name
        frontendPort = $portContext.FrontendPort
        backendPort = $portContext.BackendPort
        status = $combinedStatus
        httpStatus = "frontend=$($frontend.httpStatus); backend=$($backend.httpStatus)"
        runtimeState = "frontend=$($frontend.runtimeState); backend=$($backend.runtimeState)"
        blockedReason = $null
        onlyOffice = $onlyOffice
    }
} else {
    if ($Component -ne 'website') {
        $portContext = Get-IntRuoyiWorktreePortContext -WorktreeName $EffectiveWorktreeName
    }
    $result = switch ($Component) {
        'frontend' { New-Status -Name 'intruoyi-frontend' -Port $portContext.FrontendPort -Url "http://127.0.0.1:$($portContext.FrontendPort)/" }
        'backend' { New-Status -Name 'intruoyi-backend' -Port $portContext.BackendPort -Url "http://127.0.0.1:$($portContext.BackendPort)/actuator/health" }
        'website' { New-Status -Name 'website-frontend' -Port 4173 -Url 'http://127.0.0.1:4173/' }
    }
    if ($Component -ne 'website') {
        $result['worktree'] = $portContext.Name
        $result['frontendPort'] = $portContext.FrontendPort
        $result['backendPort'] = $portContext.BackendPort
    }
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
    exit 0
}

Write-Host "Component: $Component"
if ($result.worktree) {
    Write-Host "Worktree: $($result.worktree)"
    Write-Host "Ports: frontend=$($result.frontendPort) backend=$($result.backendPort)"
}
Write-Host "Status: $($result.status)"
Write-Host "HTTP: $($result.httpStatus)"
Write-Host "Runtime: $($result.runtimeState)"
if ($result.onlyOffice) {
    Write-Host "OnlyOffice: status=$($result.onlyOffice.status) http=$($result.onlyOffice.httpStatus) runtime=$($result.onlyOffice.runtimeState)"
}
