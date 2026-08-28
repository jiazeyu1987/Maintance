[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FrontendDir,
    [string[]]$RequiredBinary = @('cross-env.cmd', 'vite.cmd', 'vue-tsc.cmd'),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Require-File {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required frontend dependency input is missing: $Path"
    }
}

function Invoke-NativeText {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    $previous = Get-Location
    try {
        Set-Location -LiteralPath $WorkingDirectory
        $output = (& $FilePath @ArgumentList 2>&1 | Out-String).Trim()
        $exitCode = [int]$LASTEXITCODE
    } finally {
        Set-Location -LiteralPath $previous
    }
    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $FilePath $($ArgumentList -join ' ')`n$output"
    }
    return $output
}

function Get-IgnoredBuilds {
    param([Parameter(Mandatory = $true)][string]$WorkingDirectory)

    $output = Invoke-NativeText -FilePath 'pnpm' -ArgumentList @('ignored-builds') -WorkingDirectory $WorkingDirectory
    $lines = @($output -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $compactOutput = ($lines -join ' ')
    $isNoneOutput = ($lines.Count -eq 1 -and $lines[0] -eq 'None') -or
        ($compactOutput -eq 'Automatically ignored builds during installation: None')
    if (-not $isNoneOutput) {
        throw "pnpm ignored-builds must report exactly None before build; got: $output"
    }
    return @()
}

function Test-DependencyStamp {
    param(
        $Stamp,
        [Parameter(Mandatory = $true)][string]$PackageHash,
        [Parameter(Mandatory = $true)][string]$LockHash,
        [Parameter(Mandatory = $true)][string]$NodeVersion,
        [Parameter(Mandatory = $true)][string]$PnpmVersion,
        [Parameter(Mandatory = $true)][string[]]$BinaryNames
    )

    if ($null -eq $Stamp -or [int]$Stamp.schema -ne 1) {
        return $false
    }
    if ([string]$Stamp.packageHash -ne $PackageHash -or [string]$Stamp.lockHash -ne $LockHash) {
        return $false
    }
    if ([string]$Stamp.nodeVersion -ne $NodeVersion -or [string]$Stamp.pnpmVersion -ne $PnpmVersion) {
        return $false
    }
    if (@($Stamp.ignoredBuilds).Count -ne 0) {
        return $false
    }
    $stampedBinaries = @($Stamp.requiredBinaries | ForEach-Object { [string]$_ } | Sort-Object)
    $expectedBinaries = @($BinaryNames | ForEach-Object { [string]$_ } | Sort-Object)
    return (($stampedBinaries -join "`n") -eq ($expectedBinaries -join "`n"))
}

function Assert-RequiredBinaries {
    param(
        [Parameter(Mandatory = $true)][string]$FrontendDirectory,
        [Parameter(Mandatory = $true)][string[]]$BinaryNames
    )

    $binDirectory = Join-Path $FrontendDirectory 'node_modules\.bin'
    foreach ($binaryName in $BinaryNames) {
        $binaryPath = Join-Path $binDirectory $binaryName
        Require-File -Path $binaryPath
    }
}

$resolvedFrontendDir = (Resolve-Path -LiteralPath $FrontendDir).Path
$packageJsonPath = Join-Path $resolvedFrontendDir 'package.json'
$lockfilePath = Join-Path $resolvedFrontendDir 'pnpm-lock.yaml'
$nodeModulesDir = Join-Path $resolvedFrontendDir 'node_modules'
$stampPath = Join-Path $nodeModulesDir '.release-dependencies.json'
Require-File -Path $packageJsonPath
Require-File -Path $lockfilePath
Require-Command -Name 'node'
Require-Command -Name 'pnpm'

$packageHash = (Get-FileHash -LiteralPath $packageJsonPath -Algorithm SHA256).Hash.ToLowerInvariant()
$lockHash = (Get-FileHash -LiteralPath $lockfilePath -Algorithm SHA256).Hash.ToLowerInvariant()
$nodeVersion = Invoke-NativeText -FilePath 'node' -ArgumentList @('--version') -WorkingDirectory $resolvedFrontendDir
$pnpmVersion = Invoke-NativeText -FilePath 'pnpm' -ArgumentList @('--version') -WorkingDirectory $resolvedFrontendDir
$binaryNames = @($RequiredBinary | ForEach-Object { [string]$_ } | Sort-Object -Unique)

$stamp = $null
if (Test-Path -LiteralPath $stampPath -PathType Leaf) {
    $stamp = Get-Content -LiteralPath $stampPath -Raw -Encoding utf8 | ConvertFrom-Json
}

$stampMatches = Test-DependencyStamp `
    -Stamp $stamp `
    -PackageHash $packageHash `
    -LockHash $lockHash `
    -NodeVersion $nodeVersion `
    -PnpmVersion $pnpmVersion `
    -BinaryNames $binaryNames
if (-not $Force -and $stampMatches) {
    Assert-RequiredBinaries -FrontendDirectory $resolvedFrontendDir -BinaryNames $binaryNames
    [Console]::WriteLine('FRONTEND_DEPENDENCIES_REUSED')
    exit 0
}

Invoke-NativeText `
    -FilePath 'pnpm' `
    -ArgumentList @('--dir', $resolvedFrontendDir, 'install', '--frozen-lockfile') `
    -WorkingDirectory $resolvedFrontendDir | Out-Null
Invoke-NativeText `
    -FilePath 'pnpm' `
    -ArgumentList @('--dir', $resolvedFrontendDir, 'rebuild', '--pending') `
    -WorkingDirectory $resolvedFrontendDir | Out-Null
$null = Get-IgnoredBuilds -WorkingDirectory $resolvedFrontendDir
Assert-RequiredBinaries -FrontendDirectory $resolvedFrontendDir -BinaryNames $binaryNames

if (-not (Test-Path -LiteralPath $nodeModulesDir -PathType Container)) {
    throw "Frontend dependency install did not create node_modules: $nodeModulesDir"
}
$stampObject = [ordered]@{
    schema = 1
    packageHash = $packageHash
    lockHash = $lockHash
    nodeVersion = $nodeVersion
    pnpmVersion = $pnpmVersion
    requiredBinaries = @($binaryNames)
    ignoredBuilds = @()
}
$stampJson = $stampObject | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($stampPath, $stampJson + "`n", [System.Text.UTF8Encoding]::new($false))
[Console]::WriteLine('FRONTEND_DEPENDENCIES_PREPARED')
