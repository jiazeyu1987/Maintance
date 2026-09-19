$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c\m'
$Jar = Join-Path $Root 'backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar'
$TaskDir = 'D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260806-head-test-only-release'
$OutLog = Join-Path $TaskDir 'runtime-control-r260806c.out.log'
$ErrLog = Join-Path $TaskDir 'runtime-control-r260806c.err.log'

if (-not (Test-Path -LiteralPath $Jar -PathType Leaf)) {
  throw "Jar does not exist: $Jar"
}

$Process = Start-Process `
  -FilePath 'java' `
  -ArgumentList @('-jar', $Jar) `
  -WorkingDirectory $Root `
  -RedirectStandardOutput $OutLog `
  -RedirectStandardError $ErrLog `
  -PassThru `
  -WindowStyle Hidden

"PID=$($Process.Id)"

for ($Index = 1; $Index -le 60; $Index++) {
  Start-Sleep -Seconds 2
  try {
    $Response = Invoke-RestMethod -Uri 'http://127.0.0.1:48181/actuator/health' -TimeoutSec 3
    "HEALTH=$($Response | ConvertTo-Json -Compress)"
    exit 0
  } catch {
    if ($Index -eq 60) {
      throw "runtime-control health timeout: $($_.Exception.Message)"
    }
  }
}
