@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%show-int-ruoyi-remote-status.ps1"
set "SERVER_HOST=172.30.30.58"
set "REMOTE_APP_DIR=/opt/intruoyi/runtime"
set "FRONTEND_PORT=8081"
set "BACKEND_PORT=48081"

if not exist "%PS1%" (
  echo [FAIL] Missing status script: %PS1%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -ServerHost "%SERVER_HOST%" -RemoteAppDir "%REMOTE_APP_DIR%" -FrontendPort %FRONTEND_PORT% -BackendPort %BACKEND_PORT%
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%
