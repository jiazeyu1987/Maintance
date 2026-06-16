param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('validate-chain', 'validate-point', 'plan-restore')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$BackupManifestPath,

    [string]$RestorePoint,

    [string]$ExpectFile,

    [string]$ExpectState,

    [string]$ExpectContentHash,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'modules\Core\DccBackupChainValidator.psm1'
Import-Module $modulePath -Force

$result = Invoke-DccBackupChainValidation `
    -Mode $Mode `
    -BackupManifestPath $BackupManifestPath `
    -RestorePoint $RestorePoint `
    -ExpectFile $ExpectFile `
    -ExpectState $ExpectState `
    -ExpectContentHash $ExpectContentHash `
    -OutputPath $OutputPath

Write-Host ("dcc-backup mode={0} status={1}" -f $Mode, $result.Payload.status)
exit $result.ExitCode
