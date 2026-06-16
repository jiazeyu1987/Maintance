param(
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'worktree-port-map.ps1')

$plan = Sync-IntRuoyiWorktreePorts

if ($Json) {
    $plan | ConvertTo-Json -Depth 10
    exit 0
}

Write-Host "Registry: $($plan.RegistryPath)"
Write-Host "Base: frontend=$($plan.BaseFrontendPort) backend=$($plan.BaseBackendPort)"
$plan.Assignments |
    Where-Object { $_.Active } |
    Sort-Object @{ Expression = { if ($_.Name -eq 'int_main') { 0 } else { 1 } } }, Name |
    Format-Table Name, FrontendPort, BackendPort, FrontendPath, BackendPath -AutoSize
