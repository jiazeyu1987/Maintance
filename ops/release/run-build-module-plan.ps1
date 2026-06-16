[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ModuleManifestPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [ValidateSet('plan-only')]
    [string]$Mode = 'plan-only'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

try {
    $modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'lib\BuildModulePlanner.psm1'
    Import-Module -Name $modulePath -Force

    $result = Invoke-BuildModulePlanner `
        -ModuleManifestPath $ModuleManifestPath `
        -OutputPath $OutputPath `
        -Mode $Mode

    [Console]::Out.WriteLine("status=$($result.Plan.status) buildAction=$($result.Plan.buildAction) mode=$Mode output=$OutputPath")
    exit $result.ExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
