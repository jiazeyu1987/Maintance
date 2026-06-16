@echo off
setlocal EnableExtensions
chcp 65001 >nul
title IntRuoyi Backup Console - PRODUCTION

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%scripts\backup-ops.ps1"
set "DEFAULT_CONFIG=%SCRIPT_DIR%config\backup-ops.config.json"
set "RESOLVE_LOG_ROOT_PS1=%SCRIPT_DIR%actions\Resolve-BackupOpsLogRoot.ps1"
set "PROD_HOST=172.30.30.57"
set "TEST_HOST=172.30.30.58"

if not exist "%PS1%" (
  echo 缺少主脚本:
  echo %PS1%
  exit /b 2
)

:MENU
cls
echo ========================================
echo  IntRuoyi 备份恢复控制台
echo  正式服务器: %PROD_HOST%
echo  测试服务器: %TEST_HOST%
echo  操作机: %COMPUTERNAME%
echo  当前时间: %date% %time%
echo ========================================
echo.
echo 请选择操作:
echo   1. 立即备份
echo   2. 回滚应用版本
echo   3. 恢复数据到备份服
echo   9. 查看最近日志目录
echo   0. 退出
echo.

set "CHOICE="
set /p "CHOICE=请输入编号: "

if "%CHOICE%"=="1" goto BACKUP_NOW
if "%CHOICE%"=="2" goto ROLLBACK_APP
if "%CHOICE%"=="3" goto RESTORE_DATA
if "%CHOICE%"=="9" goto OPEN_LOGS
if "%CHOICE%"=="0" goto END

echo 输入无效，请输入 0 / 1 / 2 / 3 / 9。
echo 按回车返回主菜单...
pause >nul
goto MENU

:BACKUP_NOW
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode "backup-now" -TargetEnvironment "test"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo 操作退出码: %EXIT_CODE%
echo 按回车返回主菜单...
pause >nul
goto MENU

:ROLLBACK_APP
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode "rollback-app"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo 操作退出码: %EXIT_CODE%
echo 按回车返回主菜单...
pause >nul
goto MENU

:RESTORE_DATA
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Mode "restore-data" -TargetEnvironment "test"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo 操作退出码: %EXIT_CODE%
echo 按回车返回主菜单...
pause >nul
goto MENU

:OPEN_LOGS
if not exist "%RESOLVE_LOG_ROOT_PS1%" (
  echo 缺少日志目录解析脚本:
  echo %RESOLVE_LOG_ROOT_PS1%
  echo.
  echo 按回车返回主菜单...
  pause >nul
  goto MENU
)

set "LOG_DIR="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%RESOLVE_LOG_ROOT_PS1%" -ConfigPath "%DEFAULT_CONFIG%"`) do (
  if not defined LOG_DIR set "LOG_DIR=%%I"
)
set "RESOLVE_EXIT=%ERRORLEVEL%"

if not "%RESOLVE_EXIT%"=="0" (
  echo.
  echo 无法定位运行时日志目录，请先修复上方提示的问题。
  echo 按回车返回主菜单...
  pause >nul
  goto MENU
)

if not defined LOG_DIR (
  echo.
  echo 未解析到日志目录，请检查:
  echo %DEFAULT_CONFIG%
  echo 按回车返回主菜单...
  pause >nul
  goto MENU
)

if not exist "%LOG_DIR%" (
  mkdir "%LOG_DIR%"
)

start "" explorer "%LOG_DIR%"
echo 已打开日志目录:
echo %LOG_DIR%
echo.
echo 按回车返回主菜单...
pause >nul
goto MENU

:END
endlocal
exit /b 0
