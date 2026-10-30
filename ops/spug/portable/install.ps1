param(
    [Parameter(Mandatory=$true)][string]$Package,
    [Parameter(Mandatory=$true)][string]$Destination,
    [switch]$SourceStopped,
    [string]$GitProxy
)
$ErrorActionPreference = 'Stop'
if (-not $SourceStopped) { throw 'Finish all jobs and stop the old executor before handoff. Then pass -SourceStopped.' }
$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Python prerequisite failed.' }
$cli = Join-Path $Package 'tools/playwright/node_modules/@playwright/cli/playwright-cli.js'
$extra = @()
if ($GitProxy) { $extra = @('--git-proxy', $GitProxy) }
& $python (Join-Path $PSScriptRoot 'import_local.py') --package $Package --destination $Destination --source-stopped --playwright-cli $cli @extra
if ($LASTEXITCODE -ne 0) { throw 'Import failed. Do not start the executor; preserve output for diagnosis.' }
