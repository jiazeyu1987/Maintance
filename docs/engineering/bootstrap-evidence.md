# Bootstrap Evidence

## Goal and Scope

- Goal：创建可独立运行的 IntRuoyi 运行控制台本机应用。
- Scope：后端 Spring Boot、前端 Vue 单页、运行控制台脚本子集、配置示例、一键构建/启动脚本、Git 初始化。
- Non-goal：本次不执行真实发布、备份、恢复、回滚、重启、远端清理或服务器写入。

## Detected Stack

- 后端：Java 17、Spring Boot 3。
- 前端：Vue 3、Vite、TypeScript、Element Plus。
- 脚本：PowerShell、本机 Windows。

## Evidence

- RED/GREEN 证据记录在 `doc/tasks/20260616-runtime-control-standalone-extraction/execution-log.md`。
- GREEN: `.\scripts\build.ps1` -> PASS；前端静态资源被复制到 `backend/src/main/resources/static` 并进入 Spring Boot jar。
- GREEN: `.\scripts\start.ps1` -> PASS；默认监听 `127.0.0.1:48181`。
- GREEN: Playwright 页面验证 -> PASS；生产形态由 Spring Boot 托管打包后的 Vue 页面。
