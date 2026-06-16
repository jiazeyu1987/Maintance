param(
    [Parameter(Mandatory = $true)]
    [string]$TargetEnvironment,

    [Parameter(Mandatory = $true)]
    [string]$TargetHost,

    [Parameter(Mandatory = $true)]
    [long]$TenantId,

    [Parameter(ParameterSetName = 'QueryJson', Mandatory = $true)]
    [string]$QueryResultJsonPath,

    [Parameter(ParameterSetName = 'QueryCsv', Mandatory = $true)]
    [string]$QueryResultCsvPath,

    [Parameter(ParameterSetName = 'MySqlCliOutput', Mandatory = $true)]
    [string]$MySqlCliOutputPath,

    [Parameter(ParameterSetName = 'Database', Mandatory = $true)]
    [string]$DatabaseHost,

    [Parameter(ParameterSetName = 'Database', Mandatory = $true)]
    [int]$DatabasePort,

    [Parameter(ParameterSetName = 'Database', Mandatory = $true)]
    [string]$DatabaseName,

    [Parameter(ParameterSetName = 'Database', Mandatory = $true)]
    [string]$MySqlPath,

    [Parameter(ParameterSetName = 'Database')]
    [string]$DatabaseUser,

    [Parameter(ParameterSetName = 'Database')]
    [string]$DatabasePassword,

    [Parameter(ParameterSetName = 'Database')]
    [string]$DefaultsExtraFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'modules\Core\DccDatabaseSnapshotExporter.psm1'
Import-Module $modulePath -Force

$parameters = @{
    TargetEnvironment = $TargetEnvironment
    TargetHost = $TargetHost
    TenantId = $TenantId
    OutputPath = $OutputPath
}

if ($PSCmdlet.ParameterSetName -eq 'QueryJson') {
    $parameters.QueryResultJsonPath = $QueryResultJsonPath
} elseif ($PSCmdlet.ParameterSetName -eq 'QueryCsv') {
    $parameters.QueryResultCsvPath = $QueryResultCsvPath
} elseif ($PSCmdlet.ParameterSetName -eq 'MySqlCliOutput') {
    $parameters.MySqlCliOutputPath = $MySqlCliOutputPath
} elseif ($PSCmdlet.ParameterSetName -eq 'Database') {
    $parameters.DatabaseHost = $DatabaseHost
    $parameters.DatabasePort = $DatabasePort
    $parameters.DatabaseName = $DatabaseName
    $parameters.MySqlPath = $MySqlPath
    $parameters.DatabaseUser = $DatabaseUser
    $parameters.DatabasePassword = $DatabasePassword
    $parameters.DefaultsExtraFile = $DefaultsExtraFile
}

$result = Invoke-DccDatabaseSnapshotExport @parameters
Write-Host ("dcc-snapshot targetEnvironment={0} targetHost={1} tenantId={2} status={3}" -f $TargetEnvironment, $TargetHost, $TenantId, $result.Payload.status)
exit $result.ExitCode
