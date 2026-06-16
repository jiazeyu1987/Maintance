param(
    [Parameter(Mandatory = $true)]
    [string]$OperationEvidencePath,

    [Parameter(Mandatory = $true)]
    [ValidateSet('build', 'publish', 'backup', 'restore', 'rollback')]
    [string]$Gate,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\OperationEvidenceValidator.psm1'
Import-Module $modulePath -Force

$result = Invoke-OperationEvidenceValidation `
    -OperationEvidencePath $OperationEvidencePath `
    -Gate $Gate `
    -OutputPath $OutputPath

Write-Host ("operation-evidence gate={0} status={1}" -f $Gate, $result.Payload.status)
exit $result.ExitCode
