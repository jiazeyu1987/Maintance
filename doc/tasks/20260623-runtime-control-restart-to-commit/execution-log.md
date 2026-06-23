# Execution Log

## BDD

- `BDD: 重新构建并重启本机运行控制台 -> Given 当前提交已包含版本栏 When 执行 build 并启动 48181 Then 页面和 release-status 应返回新版本字段。`
- `BDD: 旧进程被替换 -> Given 48181 仍运行旧 jar When 停止旧进程并启动新 jar Then 进程命令行应切换到最新构建产物。`

## RED

- `RED: Invoke-WebRequest http://127.0.0.1:48181/assets/index-CaycDeTl.js -> FAIL, 当前运行前端资源 HasVersionDock=false 且 HasBuildVersion=false，说明 48181 未加载左下角版本栏。`
- `RED: Invoke-WebRequest http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status -> FAIL, 当前运行后端 HasTestField=true 但 HasProdField=false、HasBackupField=false。`
- `RED: Get-NetTCPConnection -LocalPort 48181 + Win32_Process -> FAIL, 当前旧进程 PID 29548 仍以 backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar 运行，需停止后重建。`

## GREEN

- `GREEN: Stop-Process old 48181 PID 29548 -> PASS，旧运行控制台进程已停止，端口释放。`
- `GREEN: powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1 -> PASS，前端 typecheck/build 通过，Maven 测试 22 个通过，jar 重新打包成功。`
- `BLOCKER: start-runtime-control -> config/runtime-control.local.yaml repo-root/frontend-root 指向已删除 clean release worktree，Spring 启动失败并提示 maintenance.runtime-control.repo-root directory does not exist。`
- `GREEN: local-config-root-repair -> PASS，按项目基线把 repo-root/frontend-root 改回 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro 与 D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3。`
- `GREEN: restart-runtime-control -> PASS，48181 重新启动成功，当前保留运行 PID 35752，命令行指向 backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar。`
- `GREEN: verify-runtime-control-page -> PASS，http://127.0.0.1:48181/ 返回新资源 index-BVR1hDry.js，JS 包含 console-version-dock 和 2026.06.0。`
- `GREEN: verify-runtime-control-api -> PASS，release-status 返回 test/prod/backupCurrentReleaseTag，页面快照左下角显示软件版本 2026.06.0、测试服 release-20260623-random-erp-test-v1、正式服 release-20260621-page-full-flow-mainmerge-v15、备份服 release-20260621-page-full-flow-mainmerge-v15。`
- `GREEN: final-runtime-recheck -> PASS，最终保留进程 PID 35752 仍监听 48181，首页 HTTP 200，release-status HTTP 200，新 JS 资源仍包含 console-version-dock 和 2026.06.0。`
- `GREEN: task-closeout-cleanup preview/apply -> PASS，保留 task.md 与 execution-log.md，删除本次旧启动临时日志 runtime-control-start.log/runtime-control-start.err.log。`
