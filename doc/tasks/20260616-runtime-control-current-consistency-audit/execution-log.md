# Execution Log

- Task ID: `20260616-runtime-control-current-consistency-audit`
- Created: `2026-06-16`

## BDD

- BDD: 后端动作契约一致性 -> Given 原版运行控制台动作门禁, When 对比独立版服务层, Then 标出一致、独立化差异和缺口。
- BDD: 前端 payload 契约一致性 -> Given 原版 Vue 运行控制台按动作组装请求, When 对比独立版 `App.vue`, Then 不相关字段不应被提交。
- BDD: 发布/恢复候选一致性 -> Given 原版读取 manifest/checksum/tested/DCC 证据, When 对比独立版候选解析, Then 缺失证据必须 BLOCKED。
- BDD: 独立化边界 -> Given 独立应用不接入芋道登录权限, When 对比原版 controller/frontend, Then 明确哪些差异是用户要求保留的独立化差异。

## TDD Evidence

- GREEN: endpoint static compare -> PASS, normalized standalone/original controller paths both contain the same 33 HTTP methods and paths.
- GREEN: script hash compare -> PASS for `apply-test-db-sql.ps1`, `backup-ops.ps1`, `show-int-ruoyi-local-status.ps1`, `restart-int-ruoyi-local.ps1`; `publish-int-ruoyi.ps1` differs by 64 lines for standalone fixes.
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS.
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS, 7 tests / 0 failures.
- GREEN: `pnpm --dir frontend typecheck` -> PASS.
- GREEN: `experience-preflight -> PASS`，本任务只做静态审计和本地契约验证；未执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- GREEN: `task-closeout-cleanup --mode preview` -> PASS，无删除项、无阻塞、无警告。
- GREEN: `task-closeout-cleanup --mode apply` -> PASS，无删除项、无阻塞、无警告。

## Outstanding Blockers

- None.
