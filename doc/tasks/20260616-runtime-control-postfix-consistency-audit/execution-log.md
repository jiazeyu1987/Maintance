# 执行日志

## BDD

- `BDD: 原版一致性审计 -> Given 当前独立维护应用已完成上一轮原版对齐修复, When 对比原版 IntRuoyi 运行控制台的后端、前端、脚本与测试证据, Then 输出明确的一致、偏差、意图性差异和剩余风险清单`

## TDD / 验证证据

- `GREEN: experience-preflight -> PASS, 本任务只执行代码审计、本地测试与构建，不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入`
- `GREEN: static endpoint/action compare -> PASS, 独立版与原版归一后均为 33 个 HTTP 接口；10 个运行控制台 action id 顺序一致`
- `GREEN: python -X utf8 scripts\verify_contracts.py -> PASS`
- `GREEN: mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest test -> PASS, 7 tests / 0 failures`
- `GREEN: pnpm --dir frontend typecheck -> PASS`
- `GREEN: mvn -f backend\pom.xml test -> PASS, 14 tests / 0 failures`
- `GREEN: pnpm --dir frontend build -> PASS, Vite 仅提示现有单 chunk 体积超过 500 kB`
- `GREEN: script hash compare -> PASS, 4 个脚本字节级一致；publish-int-ruoyi.ps1 保留独立应用路径与编码修正差异`

## 命令记录

- `Get-Content -LiteralPath C:\Users\BJB110\.codex\skills\independent-verification-gate\SKILL.md -Encoding utf8`，确认采用独立验证门禁流程。
- `Get-ChildItem D:\ProjectPackage\Int`、`Get-ChildItem D:\ProjectPackage\Int\IntRuoyiMaintance`，确认原项目与独立仓库位置。
- `Get-Content docs\experience-index.md`，读取任务门禁；命中发布/备份/恢复和前端风格门禁。
- `rg --files ... runtimecontrol`，定位原版后端 `yudao-module-infra`、原版前端 `runtime-control`、独立版 `backend/src/main/java/com/intruoyi/maintenance/runtime` 与 `frontend/src`。
- `rg -n @(GetMapping|PostMapping|PutMapping|DeleteMapping)|@RequestMapping|PreAuthorize...`，比对控制器接口、权限注解与动作枚举。
- `Get-Content RuntimeControlOperationAction.java`、`Get-Content RuntimeControlService.java`，比对动作参数、候选解析、发布/恢复门禁与运行态治理逻辑。
- `python -X utf8 scripts\verify_contracts.py`，静态契约 PASS。
- `mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest test`，原版一致性测试 PASS。
- `pnpm --dir frontend typecheck`，前端类型检查 PASS。
- `mvn -f backend\pom.xml test`，后端完整测试 PASS。
- `pnpm --dir frontend build`，前端生产构建 PASS，存在 Vite chunk size warning。
- 内联 Python 静态比对控制器接口和动作枚举：33 个接口一致，10 个 action id 一致。
- `Get-FileHash` 比对复制脚本：4 个脚本一致，`publish-int-ruoyi.ps1` 不一致且为独立化必要修正。

## 审计输出

- `verification-report.md` 已生成，结论为“独立化边界内一致”。
- 未修改生产代码，未执行任何真实高风险动作。
- GREEN: task-closeout-cleanup --mode preview -> PASS, keep task.md/execution-log.md/verification-report.md; delete candidate directory outside task scope was removed manually after preview.
