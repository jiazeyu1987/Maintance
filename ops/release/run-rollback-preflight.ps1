param(
    [string]$ReleaseManifestPath,

    [string]$BackupManifestPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet('test', 'backup', 'prod')]
    [string]$TargetEnvironment,

    [Parameter(Mandatory = $true)]
    [ValidateSet('code', 'data', 'combined')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\RollbackPreflight.psm1'
Import-Module $modulePath -Force

$result = Invoke-RollbackPreflight `
    -ReleaseManifestPath $ReleaseManifestPath `
    -BackupManifestPath $BackupManifestPath `
    -TargetEnvironment $TargetEnvironment `
    -Mode $Mode `
    -OutputPath $OutputPath

Write-Host ("rollback-preflight mode={0} status={1}" -f $Mode, $result.Payload.status)
exit $result.ExitCode
