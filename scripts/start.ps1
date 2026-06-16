$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
$Jar = Join-Path $Root 'backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar'
if (-not (Test-Path -LiteralPath $Jar)) {
  throw "Jar does not exist. Run scripts\build.ps1 first: $Jar"
}

Set-Location -LiteralPath $Root
java -jar $Jar
