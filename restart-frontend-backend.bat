@echo off
setlocal

set "PS1=D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\deploy\restart-int-ruoyi-local.ps1"

if /i "%~1"=="cancel" goto cancel

if not exist "%PS1%" (
  echo [FAIL] Missing restart script: %PS1%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Component full
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%

:cancel
echo [INFO] Restart cancelled.
exit /b 0
