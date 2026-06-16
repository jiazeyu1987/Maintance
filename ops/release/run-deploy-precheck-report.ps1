[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,

    [Parameter(Mandatory = $true)]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [string]$TargetConfigPath,

    [ValidateSet('report-only')]
    [string]$Mode = 'report-only',

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

function Write-DeployPrecheckJson {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $outputFullPath = [System.IO.Path]::GetFullPath($Path)
    $outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
    if (-not [string]::IsNullOrWhiteSpace($outputDirectory) -and -not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
        [System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
    }

    $json = $Payload | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($outputFullPath, $json + [System.Environment]::NewLine, $utf8NoBom)
    return $outputFullPath
}

function New-DeployPrecheckExceptionReport {
    param(
        [Parameter(Mandatory = $true)][string]$Message
    )

    $diagnostic = [pscustomobject]([ordered]@{
        code = 'DEPLOY_PRECHECK_EXCEPTION'
        status = 'failed'
        scope = 'deployPrecheck'
        message = $Message
        impact = 'The deploy precheck report-only command could not complete its local contract checks.'
        nextStep = 'Fix the reported local precondition and rerun deploy precheck report-only.'
    })

    return [pscustomobject]([ordered]@{
        status = 'failed'
        mode = $Mode
        deployBehavior = 'deploy-release'
        packageId = $null
        manifestVersion = $null
        environment = $Environment
        targetConfigId = $null
        checkedAt = (Get-Date).ToUniversalTime().ToString('o')
        changesDeployExitCode = $false
        errors = @($diagnostic)
        warnings = @()
        checks = @()
    })
}

try {
    $modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'lib\DeployPrecheckReport.psm1'
    Import-Module -Name $modulePath -Force

    $result = Invoke-DeployPrecheckReport `
        -PackagePath $PackagePath `
        -Environment $Environment `
        -TargetConfigPath $TargetConfigPath `
        -Mode $Mode

    $writtenPath = Write-DeployPrecheckJson -Payload $result -Path $OutputPath
    [Console]::Out.WriteLine("status=$($result.status) mode=$($result.mode) output=$writtenPath")

    if ($result.status -eq 'failed') {
        exit 2
    }

    exit 0
} catch {
    $exceptionReport = New-DeployPrecheckExceptionReport -Message $_.Exception.Message
    $writtenPath = Write-DeployPrecheckJson -Payload $exceptionReport -Path $OutputPath
    [Console]::Out.WriteLine("status=failed mode=$Mode output=$writtenPath")
    exit 2
}
