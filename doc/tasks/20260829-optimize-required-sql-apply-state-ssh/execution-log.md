# 20260829 优化 required SQL APPLY 状态入账 SSH 往返执行日志

- BDD: APPLY 成功路径单 SSH 状态入账 -> Given required SQL APPLY 项需要记录 RUNNING 和 APPLIED, When 发布脚本执行单条 SQL, Then RUNNING、SQL 执行、APPLIED 应在同一次 SSH 会话中完成，减少额外 SSH 往返。
- BDD: APPLY 失败仍 fail fast -> Given 单条 required SQL 执行失败, When 单 SSH 成功路径抛出异常, Then 发布脚本必须继续写 FAILED 状态并终止，不得吞异常或把失败 SQL 标记 APPLIED。
- GREEN: experience-preflight -> PASS，本任务只修改本地维护仓脚本/测试/文档，不执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\red` -> FAIL，`2 failed, 46 passed`；新增测试命中缺少 `Invoke-RequiredDatabaseSqlScriptWithState`，且 APPLY 循环仍直接写 `RUNNING`/`APPLIED`。
- 修复动作：新增 `Invoke-RequiredDatabaseSqlScriptWithState`，单次 SSH 中先检查远端 SQL 文件、写 `RUNNING`、执行 SQL、写 `APPLIED`；原 catch 保留 `FAILED` 入账并继续抛出。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\green` -> PASS，`48 passed in 0.24s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\regression` -> PASS，`59 passed in 0.18s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-apply-state-ssh/task.md doc/tasks/20260829-optimize-required-sql-apply-state-ssh/execution-log.md doc/tasks/20260829-optimize-required-sql-apply-state-ssh/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: tool-preflight -> PASS，本机 `tar.exe`、`ssh.exe`、`scp.exe` 存在。
- COMMIT: implementation -> `e4bc1e5`（`任务: 优化required SQL状态入账`），提交范围仅 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- GREEN: task-closeout-cleanup preview -> PASS，状态 `ready`，仅计划清理本任务 `pytest-parent` 临时产物。
- GREEN: task-closeout-cleanup apply -> PASS，状态 `applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`。
- GREEN: project-experience-consolidation -> PASS，经验合并到 `docs/release-build-preflight-lessons.md`，索引更新到 `docs/experience-index.md`。
- FINAL: task status -> completed；本任务未执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
