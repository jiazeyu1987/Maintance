@echo off
setlocal EnableExtensions
chcp 65001 >nul
title IntRuoyi Backup Console - 立即备份

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%..\scripts\backup-ops.ps1"

if not exist "%PS1%" (
  echo 缺少主脚本:
  echo %PS1%
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode "backup-now" -TargetEnvironment "test" %*
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
