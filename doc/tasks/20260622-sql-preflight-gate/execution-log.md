# 执行日志：发布 SQL 预检前移门禁

- BDD: build-release 前移 SQL 门禁 -> Given 发布候选包含 required SQL / When 本机构建开始前执行 SQL 预检 / Then 迁移策略或菜单主键冲突必须在 Maven/Vite/Docker 前直接失败。
- BDD: system_menu 主键冲突提前暴露 -> Given 两个发布 SQL 向 system_menu 写入同一个 id / When 运行维护仓 SQL 预检 / Then 返回明确冲突明细并阻断发布。
- BDD: 合法 required SQL 正常通过 -> Given 发布 SQL metadata 完整且 system_menu id 不冲突 / When 运行 build-release 预检 / Then 预检通过，后续打包流程才允许继续。
- GREEN: ci-cd-skill-read -> PASS，已读取 `C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\SKILL.md` 与 `references\cicd-contract.md`。
- GREEN: database-skill-read -> PASS，已读取 `C:\Users\BJB110\.codex\skills\database-schema-delivery\SKILL.md` 与 `references\database-contract.md`。
- GREEN: previous-task-check -> PASS，上一维护仓任务 `doc/tasks/20260622-backup-server-backup-restore-rerun/task.md` 已标记 `COMPLETED`。
- GREEN: baseline-docs-read -> PASS，已读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/agent-memory/project-error-prevention.md`、`ops/release/release_migration_policy_gate.py`、`ops/release/release_preflight_plan.py`、`ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_showroom_release_sql_contract.py`。
- RED: python -m pytest scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL???????? `system_menu` ????????????????????? SQL ???
- GREEN: python -m pytest scripts\tests\test_release_sql_preflight_gate.py -q -> PASS?3 passed?duplicate system_menu.id ??? build-release ?????????
- GREEN: python -m pytest scripts\tests\test_showroom_release_sql_contract.py -q -> PASS?3 passed??? showroom ?? SQL ??????
- BDD: 合法 ON DUPLICATE KEY UPDATE 不应误报 -> Given `system_menu` 菜单 SQL 使用 `INSERT ... VALUES (...) ON DUPLICATE KEY UPDATE ... VALUES(...)` / When 运行维护仓 release SQL 预检 / Then 只能解析真正插入元组，不能把更新子句里的 `VALUES(...)` 误识别成新的菜单记录。
- GREEN: real-page-failure-import -> PASS，已把真实页面 `build-release(v11)` operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 的失败证据回灌到本任务：本机 SQL 预检对 `20260520_system_nas_management_menu.sql` 报出 `system_menu.id must be an integer literal ... -> \`name\``，根因定位到 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 误解析。
- RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL，新增 `test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause` 后，预检仍把更新子句里的 `` `name` `` 误判为 `system_menu.id`。
- GREEN: parser-fix-minimal-change -> PASS，`ops/release/release_sql_contract_gate.py` 已将 `_extract_value_tuples()` 改为“只连续消费顶层 `VALUES (...)` 插入元组，遇到非逗号分隔的后续内容立即停止”，从而跳过 `ON DUPLICATE KEY UPDATE` 子句中的 `VALUES(...)`。
- GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> PASS，4 passed。
- GREEN: python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro\sql\mysql -> PASS，真实 clean release backend SQL 根目录当前 `migrationCount=186`，`20260520_system_nas_management_menu.sql` 不再误报。
