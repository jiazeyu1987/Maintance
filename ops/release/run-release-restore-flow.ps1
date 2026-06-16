param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('publish-only', 'restore-only', 'restore-then-publish', 'publish-then-restore')]
    [string]$Flow,

    [string]$ReleaseManifestPath,

    [string]$BackupManifestPath,

    [string]$PlanFixturePath,

    [Parameter(Mandatory = $true)]
    [ValidateSet('test', 'backup', 'prod')]
    [string]$TargetEnvironment,

    [Parameter(Mandatory = $true)]
    [ValidateSet('dry-run')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\ReleaseRestoreFlowPlanner.psm1'
Import-Module $modulePath -Force

$result = Invoke-ReleaseRestoreFlowPlan `
    -Flow $Flow `
    -ReleaseManifestPath $ReleaseManifestPath `
    -BackupManifestPath $BackupManifestPath `
    -PlanFixturePath $PlanFixturePath `
    -TargetEnvironment $TargetEnvironment `
    -Mode $Mode `
    -OutputPath $OutputPath

Write-Host ("flow={0} status={1}" -f $Flow, $result.Payload.status)
exit $result.ExitCode
