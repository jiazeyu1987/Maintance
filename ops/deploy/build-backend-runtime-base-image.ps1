param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Version,
    [string]$ImageRepository = 'intruoyi-backend-runtime-base',
    [string]$OutputDirectory = 'D:\ProjectPackage\Int\BaseImages'
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $null
    )

    Info ("Run: {0} {1}" -f $FilePath, ($ArgumentList -join ' '))
    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $(if ($WorkingDirectory) { $WorkingDirectory } else { (Get-Location).Path }) `
        -NoNewWindow `
        -Wait `
        -PassThru
    if ($process.ExitCode -ne 0) {
        Fail "Command failed with exit code $($process.ExitCode): $FilePath"
    }
}

if ([string]::IsNullOrWhiteSpace($ImageRepository)) {
    Fail 'ImageRepository is required.'
}
if ($ImageRepository -notmatch '^[A-Za-z0-9][A-Za-z0-9._/-]*$') {
    Fail "ImageRepository contains unsupported characters: $ImageRepository"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRepo = (Resolve-Path (Join-Path $scriptDir '..')).Path
$dockerfile = Join-Path $scriptDir 'int-ruoyi-test\Dockerfile.backend-base'
if (-not (Test-Path -LiteralPath $dockerfile -PathType Leaf)) {
    Fail "Backend runtime base Dockerfile missing: $dockerfile"
}

$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $resolvedOutputDirectory | Out-Null

$image = "${ImageRepository}:$Version"
$tarPath = Join-Path $resolvedOutputDirectory ("${ImageRepository}-${Version}.tar")
$manifestPath = Join-Path $resolvedOutputDirectory ("${ImageRepository}-${Version}.json")

Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('build', '--no-cache', '-t', $image, '-f', $dockerfile, $backendRepo)
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('run', '--rm', $image, 'java', '-version')
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('run', '--rm', $image, 'python3', '--version')
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('run', '--rm', $image, 'docker', '--version')
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('run', '--rm', $image, 'docker', 'compose', 'version')

$imageId = (& docker image inspect $image --format '{{.Id}}' 2>&1)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($imageId)) {
    Fail "Cannot inspect backend runtime base image id: $image"
}
$imageId = ([string]$imageId).Trim()
if ($imageId -notmatch '^sha256:[0-9a-f]{64}$') {
    Fail "Unexpected backend runtime base image id: $imageId"
}

Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('save', '-o', $tarPath, $image)
$tarSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $tarPath).Hash.ToLowerInvariant()

$manifest = [ordered]@{
    image = $image
    version = $Version
    digest = $imageId
    tarPath = $tarPath
    tarSha256 = $tarSha256
    builtAt = (Get-Date).ToUniversalTime().ToString('o')
    sourceDockerfile = $dockerfile
}
$manifestJson = $manifest | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($manifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))

Info "Backend runtime base image exported: $tarPath"
Info "Backend runtime base manifest: $manifestPath"
