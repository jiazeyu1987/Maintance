[CmdletBinding()]
param(
  [switch]$ForceFrontendDependencies
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $Name"
  }
}

Require-Command java
Require-Command mvn
Require-Command node
Require-Command pnpm

& (Join-Path $PSScriptRoot 'prepare-frontend-dependencies.ps1') `
  -FrontendDir (Join-Path $Root 'frontend') `
  -RequiredBinary @('vite.cmd', 'vue-tsc.cmd') `
  -Force:$ForceFrontendDependencies
if ($LASTEXITCODE -ne 0) {
  throw "Frontend dependency preparation failed with exit code $LASTEXITCODE"
}
pnpm --dir "$Root\frontend" typecheck
pnpm --dir "$Root\frontend" build

$DistDir = Join-Path $Root 'frontend\dist'
if (-not (Test-Path -LiteralPath (Join-Path $DistDir 'index.html'))) {
  throw "Frontend dist is missing index.html: $DistDir"
}

$StaticDir = Join-Path $Root 'backend\src\main\resources\static'
$ResolvedRoot = (Resolve-Path -LiteralPath $Root).Path
if (Test-Path -LiteralPath $StaticDir) {
  $ResolvedStatic = (Resolve-Path -LiteralPath $StaticDir).Path
  if (-not $ResolvedStatic.StartsWith($ResolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove static directory outside repository: $ResolvedStatic"
  }
  Remove-Item -LiteralPath $ResolvedStatic -Recurse -Force
}
New-Item -ItemType Directory -Path $StaticDir | Out-Null
Copy-Item -Path (Join-Path $DistDir '*') -Destination $StaticDir -Recurse -Force

mvn -f "$Root\backend\pom.xml" test package
