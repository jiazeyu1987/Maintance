[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseManifestPath,

    [Parameter(Mandatory = $true)]
    [string]$TargetSchemaPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet('local', 'test', 'backup')]
    [string]$TargetEnvironment,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

try {
    $modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'lib\SchemaPreflight.psm1'
    Import-Module -Name $modulePath -Force

    $result = Invoke-SchemaPreflight `
        -ReleaseManifestPath $ReleaseManifestPath `
        -TargetSchemaPath $TargetSchemaPath `
        -TargetEnvironment $TargetEnvironment `
        -OutputPath $OutputPath

    [Console]::Out.WriteLine("status=$($result.Payload.status) targetEnvironment=$TargetEnvironment output=$OutputPath")
    exit $result.ExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
