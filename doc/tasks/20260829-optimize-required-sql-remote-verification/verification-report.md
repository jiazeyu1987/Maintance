# 20260829 优化 required SQL 远端完整性校验验证报告

## Result

PASS with boundary.

## Scope

- Target script: `ops\deploy\publish-int-ruoyi.ps1`
- Target tests: `scripts\tests\test_release_sql_preflight_gate.py`
- Boundary: 不执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。

## Implemented Optimization

- required SQL tar 解包后从非空校验升级为远端文件数必须等于本地发布计划文件数。
- APPLY 循环取消每条 SQL 前的独立 `ssh test -f` 往返，依赖集中完整性校验和 SQL 执行本身 fail fast。

## Verification

- RED: `test_publish_script_requires_exact_remote_required_sql_archive_count` 与 `test_publish_script_does_not_check_each_required_sql_file_over_ssh_after_archive_gate` -> FAIL，旧实现只校验非空且逐条 `test -f`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\green` -> PASS，`46 passed in 0.14s`。
- REGRESSION: 发布合同测试集合 -> PASS，`57 passed in 0.16s`。
- PowerShell AST parse: `PSSCRIPT_PARSE_OK`。
- `git diff --check`: PASS，仅 LF/CRLF warning。
- Tool preflight: `tar.exe`、`ssh.exe`、`scp.exe` present。

## Boundary

- 未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 未恢复、覆盖或提交仓库中既有的并行脏改动和 `frontend/` 删除状态。

## Commits

- Implementation: `079c6a6`（`任务: 优化required SQL远端校验`）。

## Closeout

- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，经验已合并到发布前置经验文档并更新索引。
