@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%run-dcc-manual-release-isolated-e2e.ps1"

if not exist "%PS1%" (
  echo [FAIL] Missing run script: %PS1%
  exit /b 1
)

if /i "%~1"=="cancel" goto cancel
if /i "%~1"=="keep-running" goto keep_running
if not "%~1"=="" goto passthrough

echo.
echo ==========================================
echo DCC Isolated Manual-Release E2E
echo ==========================================
echo 1. Run and auto-stop
echo 2. Run and keep environment running
echo 3. Cancel
echo.
set /p CHOICE=Choose option number:

if "%CHOICE%"=="1" goto run_default
if "%CHOICE%"=="2" goto keep_running
if "%CHOICE%"=="3" goto cancel

echo [FAIL] Invalid option: %CHOICE%
exit /b 1

:run_default
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
goto done

:keep_running
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -KeepRunning
goto done

:passthrough
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
goto done

:cancel
echo [INFO] DCC isolated E2E cancelled.
set "EXIT_CODE=0"
goto end

:done
set "EXIT_CODE=%ERRORLEVEL%"

:end
exit /b %EXIT_CODE%
