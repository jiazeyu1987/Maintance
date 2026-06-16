[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,

    [ValidateSet('report-only')]
    [string]$Mode = 'report-only',

    [string]$OutputPath
)

Set-StrictMode -Version Latest

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'lib\ReleaseManifestValidator.psm1'
Import-Module -Name $modulePath -Force

$result = Invoke-ReleaseManifestValidation -PackagePath $PackagePath -Mode $Mode
$json = $result | ConvertTo-Json -Depth 20
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
    $outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
    if (-not [string]::IsNullOrWhiteSpace($outputDirectory) -and -not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
        [System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
    }
    [System.IO.File]::WriteAllText($outputFullPath, $json + [System.Environment]::NewLine, $utf8NoBom)
    [Console]::Out.WriteLine("status=$($result.status) code=$($result.code) mode=$($result.mode) output=$outputFullPath")
} else {
    [Console]::Out.WriteLine($json)
}

if ($result.status -eq 'failed') {
    exit 1
}

exit 0
