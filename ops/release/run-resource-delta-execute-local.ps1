[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceDeltaPlanPath,

    [Parameter(Mandatory = $true)]
    [string]$SourceObjectRoot,

    [Parameter(Mandatory = $true)]
    [string]$TargetObjectRoot,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [ValidateSet('local-execute')]
    [string]$Mode = 'local-execute'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

try {
    $modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'lib\ResourceDeltaLocalExecutor.psm1'
    Import-Module -Name $modulePath -Force

    $result = Invoke-ResourceDeltaLocalExecutor `
        -ResourceDeltaPlanPath $ResourceDeltaPlanPath `
        -SourceObjectRoot $SourceObjectRoot `
        -TargetObjectRoot $TargetObjectRoot `
        -OutputPath $OutputPath `
        -Mode $Mode

    [Console]::Out.WriteLine("status=$($result.Proof.status) mode=$Mode output=$OutputPath")
    exit $result.ExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
