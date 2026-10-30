param([Parameter(Mandatory=$true)][string]$Root, [switch]$SourceStopped)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath (Join-Path $Root 'STAGING_ONLY')) { throw 'This is an import-verification staging directory, not an active publisher.' }
if (-not $SourceStopped) { throw 'Stop the previous executor and use its latest handoff snapshot first. Then pass -SourceStopped.' }
$config = Join-Path $Root 'executor.private.json'
$entry = Join-Path $Root 'source/ops/spug/release-center/intruoyi_executor.py'
if (!(Test-Path -LiteralPath $config) -or !(Test-Path -LiteralPath $entry)) { throw 'Import has not completed.' }
$settings = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
if ([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object Port -EQ $settings.port) { throw 'Executor port is already in use. Do not start a second executor.' }
& $settings.pythonExecutable $entry --config $config
if ($LASTEXITCODE -ne 0) { throw "Executor exited with code $LASTEXITCODE" }
