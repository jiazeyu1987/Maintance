$ErrorActionPreference = 'Stop'

param(
    [switch]$KeepRunning
)

function Fail($message) {
    Write-Host "[FAIL] $message" -ForegroundColor Red
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$workspaceRoot = Split-Path -Parent $repoRoot
$delegate = Join-Path $repoRoot 'doc\tasks\20260518-dcc-isolated-e2e-ops-hardening\scripts\run_isolated_dcc_manual_release_e2e.ps1'

if (-not (Test-Path -LiteralPath $delegate)) {
    Fail "Missing delegated isolated E2E runner: $delegate"
}

$argsList = @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $delegate
)
if ($KeepRunning) {
    $argsList += '-KeepRunning'
}

& powershell @argsList
exit $LASTEXITCODE
