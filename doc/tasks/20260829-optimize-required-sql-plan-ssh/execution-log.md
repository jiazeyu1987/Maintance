# 20260829 优化 required SQL 规划阶段 SSH 往返执行日志

## Log

- BDD: required SQL 规划阶段批量化 -> Given required SQL 列表较多，When publish-test 规划/执行 required SQL，Then 已可预先批量判断的信息不得逐条建立 SSH 会话，且执行顺序、ledger 状态和失败 fail-fast 不变。
- GREEN: experience-preflight -> PASS，命中 `docs/release-build-preflight-lessons.md#2026-08-29-publish-test-required-sql-批量化与脱敏门禁`；本轮只做本地脚本/合同测试，不执行真实发布、服务器写入或数据库写入。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_combines_route_snapshot_run_and_report_check_in_single_ssh_session -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\red` -> FAIL，`1 failed`；旧实现中 `Invoke-RouteSnapshotIdentityMigrationCommand` 含 2 次 `Invoke-SshCommand`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_combines_route_snapshot_run_and_report_check_in_single_ssh_session -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\green` -> PASS，`1 passed in 0.02s`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\sql-gate` -> PASS，`49 passed in 0.25s`；首次全量运行因 basetemp 父目录不存在出现 setup error，创建本任务临时父目录后复跑通过。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS，`PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\regression` -> PASS，`60 passed in 0.17s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-plan-ssh/task.md doc/tasks/20260829-optimize-required-sql-plan-ssh/execution-log.md doc/tasks/20260829-optimize-required-sql-plan-ssh/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: implementation-commit -> PASS，`f035655`（`任务: 优化route snapshot发布hook校验`），仅提交 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- GREEN: task-closeout-cleanup preview/apply -> PASS，仅清理本任务 `pytest-parent` 临时产物。
- GREEN: project-experience-consolidation -> PASS，更新 required SQL 批量化门禁、经验索引与 request-command-log 条目。
