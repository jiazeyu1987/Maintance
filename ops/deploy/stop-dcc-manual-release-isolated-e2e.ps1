$ErrorActionPreference = 'Stop'

function Fail($message) {
    Write-Host "[FAIL] $message" -ForegroundColor Red
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$delegate = Join-Path $repoRoot 'doc\tasks\20260518-dcc-isolated-e2e-ops-hardening\scripts\stop_isolated_dcc_manual_release_env.ps1'

if (-not (Test-Path -LiteralPath $delegate)) {
    Fail "Missing delegated isolated E2E stop script: $delegate"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $delegate
exit $LASTEXITCODE
