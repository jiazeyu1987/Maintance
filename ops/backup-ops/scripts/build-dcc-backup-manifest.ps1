param(
    [Parameter(Mandatory = $true)]
    [string]$BackupId,

    [Parameter(Mandatory = $true)]
    [string]$RestorePointId,

    [Parameter(Mandatory = $true)]
    [ValidateSet('test', 'backup', 'prod', 'production')]
    [string]$TargetEnvironment,

    [Parameter(Mandatory = $true)]
    [string]$TargetHost,

    [Parameter(Mandatory = $true)]
    [string]$DccSnapshotPath,

    [Parameter(Mandatory = $true)]
    [string]$ObjectInventoryPath,

    [string]$PreviousManifestPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'modules\Core\DccBackupManifestBuilder.psm1'
Import-Module $modulePath -Force

$result = Invoke-DccBackupManifestBuild `
    -BackupId $BackupId `
    -RestorePointId $RestorePointId `
    -TargetEnvironment $TargetEnvironment `
    -TargetHost $TargetHost `
    -DccSnapshotPath $DccSnapshotPath `
    -ObjectInventoryPath $ObjectInventoryPath `
    -PreviousManifestPath $PreviousManifestPath `
    -OutputPath $OutputPath

Write-Host ("dcc-manifest backupId={0} restorePoint={1} status={2}" -f $BackupId, $RestorePointId, $result.Payload.status)
exit $result.ExitCode
