$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$releaseTag = 'release-20260722-dcc-category-stage-test-r260722b-r1'
$maintenanceRoot = 'D:\ProjectPackage\Int\IntRuoyiMaintance'
$worktreeRoot = 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260722s'
$configPath = Join-Path $maintenanceRoot 'config\runtime-control.local.yaml'
$configText = [System.IO.File]::ReadAllText($configPath, [System.Text.UTF8Encoding]::new($false))

function Get-ConfigValue {
  param([Parameter(Mandatory = $true)][string]$Name)
  $pattern = '(?m)^\s+' + [regex]::Escape($Name) + ':\s+''?([^''\r\n]+)''?\s*$'
  $match = [regex]::Match($configText, $pattern)
  if (-not $match.Success) {
    throw "missing config value: $Name"
  }
  return $match.Groups[1].Value.Trim()
}

$nasPayload = [ordered]@{
  server = Get-ConfigValue 'nas-server'
  share = Get-ConfigValue 'nas-share'
  username = Get-ConfigValue 'nas-username'
  password = Get-ConfigValue 'nas-password'
}
$nasDir = Join-Path $maintenanceRoot 'runtime\runtime-control\nas-release-config'
New-Item -ItemType Directory -Force -Path $nasDir | Out-Null
$nasConfigPath = Join-Path $nasDir 'dcc-category-stage-test-release-20260722.json'
[System.IO.File]::WriteAllText(
  $nasConfigPath,
  ($nasPayload | ConvertTo-Json -Compress),
  [System.Text.UTF8Encoding]::new($false)
)

$publishParams = @{
  Mode = 'build-release'
  ReleaseTag = $releaseTag
  Component = 'frontend'
  SkipDatabaseSync = $true
  SkipMinioSync = $true
  NasConfigPath = $nasConfigPath
  NasReleaseRoot = 'Backup/ReleasePackage'
  BackendRepoRoot = (Join-Path $worktreeRoot 'backend_release')
  FrontendRepoRoot = (Join-Path $worktreeRoot 'frontend_release')
  WebsiteRepo = 'D:\ProjectPackage\Website'
  TestServerHost = '172.30.30.58'
  ProdServerHost = '172.30.30.57'
  BackupServerHost = '172.30.30.59'
  BackendRuntimeBaseMode = 'offline-tar'
  BackendRuntimeBaseTarPath = (Get-ConfigValue 'backend-runtime-base-tar-path')
  BackendRuntimeBaseTarSha256 = (Get-ConfigValue 'backend-runtime-base-tar-sha256')
  BackendRuntimeBaseImage = (Get-ConfigValue 'backend-runtime-base-image')
  BackendRuntimeBaseDigest = (Get-ConfigValue 'backend-runtime-base-digest')
  BackendRuntimeBaseVersion = (Get-ConfigValue 'backend-runtime-base-version')
}

$scriptPath = Join-Path $worktreeRoot 'm\ops\deploy\publish-int-ruoyi.ps1'
& $scriptPath @publishParams
if ($LASTEXITCODE -ne 0) {
  throw "build-release failed with exit code $LASTEXITCODE"
}
Write-Host "releaseTag=$releaseTag"
