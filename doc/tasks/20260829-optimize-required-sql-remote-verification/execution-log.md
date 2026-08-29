# 20260829 优化 required SQL 远端完整性校验执行日志

- BDD: required SQL 集中完整性校验 -> Given publish-test 已将 required SQL 打包为单个 tar 上传, When 远端解包完成, Then 远端 SQL 文件数必须等于本地发布计划数量，数量不一致立即失败。
- BDD: APPLY 循环减少额外 SSH 往返 -> Given 远端 required SQL 完整性已集中校验通过, When APPLY 循环逐条执行 SQL, Then 不再为每条 SQL 单独执行 `ssh test -f`，但 SQL 执行失败仍必须中止并记录 FAILED 状态。
- GREEN: experience-preflight -> PASS，本任务只修改本地维护仓脚本/测试/文档，不执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\red` -> FAIL，`2 failed, 44 passed`；新增测试命中远端只校验非空和 APPLY 循环仍逐条 `test -f '$remoteSqlPath'`。
- 修复动作：required SQL tar 解包后用 `remote_sql_count` 与本地 `$archiveSqlCount` 精确比对；删除 APPLY 循环中每条 SQL 前的额外 `Invoke-SshCommand "test -f '$remoteSqlPath' && echo REQUIRED_SQL_EXISTS"`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\green` -> PASS，`46 passed in 0.14s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\regression` -> PASS，`57 passed in 0.16s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-remote-verification/task.md doc/tasks/20260829-optimize-required-sql-remote-verification/execution-log.md doc/tasks/20260829-optimize-required-sql-remote-verification/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: tool-preflight -> PASS，本机 `tar.exe`、`ssh.exe`、`scp.exe` 存在。
- COMMIT: implementation -> `079c6a6`（`任务: 优化required SQL远端校验`），提交范围仅 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- GREEN: task-closeout-cleanup preview -> PASS，状态 `ready`，仅计划清理本任务 `pytest-parent` 临时产物。
- GREEN: task-closeout-cleanup apply -> PASS，状态 `applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`。
- GREEN: project-experience-consolidation -> PASS，经验合并到 `docs/release-build-preflight-lessons.md`，索引更新到 `docs/experience-index.md`。
- FINAL: task status -> completed；本任务未执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
