@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%stop-dcc-manual-release-isolated-e2e.ps1"

if not exist "%PS1%" (
  echo [FAIL] Missing stop script: %PS1%
  exit /b 1
)

if /i "%~1"=="cancel" goto cancel

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%

:cancel
echo [INFO] DCC isolated stop cancelled.
exit /b 0
