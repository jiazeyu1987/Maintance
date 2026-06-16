param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$BaselineManifestPath,

    [string]$LocalDatabaseConfigPath = '',

    [Parameter(Mandatory = $true)]
    [string]$DataOwnershipRegistryPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [ValidateSet('report-only')]
    [string]$Mode = 'report-only',

    [string]$LocalSchemaFingerprintPath = '',
    [string]$LocalDataChangeRowsPath = '',
    [string]$ResourceRowsPath = '',
    [string]$DockerCliPath = 'docker'
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$modulePath = Join-Path $PSScriptRoot 'lib\ReleaseIntake.psm1'
Import-Module $modulePath -Force

$result = Invoke-ReleaseIntake `
    -RepoRoot $RepoRoot `
    -BaselineManifestPath $BaselineManifestPath `
    -LocalDatabaseConfigPath $LocalDatabaseConfigPath `
    -DataOwnershipRegistryPath $DataOwnershipRegistryPath `
    -OutputDir $OutputDir `
    -Mode $Mode `
    -LocalSchemaFingerprintPath $LocalSchemaFingerprintPath `
    -LocalDataChangeRowsPath $LocalDataChangeRowsPath `
    -ResourceRowsPath $ResourceRowsPath `
    -DockerCliPath $DockerCliPath

exit $result.ExitCode
