# 运行控制台前端视觉优化执行记录

## BDD

BDD: 更精致的本机运维控制台 -> Given 操作者打开独立运行控制台，When 页面加载实例状态、运维动作和操作记录，Then 页面应以紧凑、清晰、灰蓝工作面展示关键信息，主操作突出但不营销化，表格和表单可扫描。

BDD: 不改变运维动作边界 -> Given 本任务只做前端视觉优化，When 操作者浏览页面或预览命令，Then 不应新增登录/权限依赖，不应隐藏真实错误，不应触发发布、备份、恢复、回滚、重启或远端清理动作。

## TDD / Verification Evidence

- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL，缺少前端设计 marker `console-shell`，当前页面尚未具备新的运维控制台视觉结构。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS，新增前端设计契约 marker 与视觉 token 均满足。
- GREEN: `pnpm --dir frontend typecheck` -> PASS，Vue/TypeScript 类型检查通过。
- GREEN: `pnpm --dir frontend build` -> PASS，生产构建通过；Vite 仅提示现有大 chunk 体积。
- GREEN: `.\scripts\build.ps1` -> PASS，独立应用后端可托管打包后的 Vue 页面。
- GREEN: `curl.exe -s http://127.0.0.1:48181/actuator/health` -> PASS，返回 `{"status":"UP"}`。
- GREEN: Playwright desktop `http://127.0.0.1:48181/` -> PASS，页面显示新版运行控制台，浏览器 console error 为 0，截图 `.playwright-cli\page-2026-06-16T08-08-36-568Z.png`。
- GREEN: Playwright mobile 390x844 -> PASS，运行摘要、实例状态与运维动作区域无重叠，浏览器 console error 为 0，截图 `.playwright-cli\page-2026-06-16T08-11-12-717Z.png` 和 `.playwright-cli\page-2026-06-16T08-12-06-775Z.png`。
- GREEN: `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260616-runtime-control-ui-polish --mode preview` -> PASS，无删除项、无阻塞、无警告。
- GREEN: `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260616-runtime-control-ui-polish --mode apply` -> PASS，无删除项、无阻塞、无警告。

## Blockers

- 暂无。
