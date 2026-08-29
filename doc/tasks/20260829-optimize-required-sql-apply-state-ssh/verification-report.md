# 20260829 优化 required SQL APPLY 状态入账 SSH 往返验证报告

## Result

PASS with boundary.

## Scope

- Target script: `ops\deploy\publish-int-ruoyi.ps1`
- Target tests: `scripts\tests\test_release_sql_preflight_gate.py`
- Boundary: 不执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。

## Implemented Optimization

- required SQL APPLY 成功路径由每条 SQL 三次 SSH 调用收敛为一次 SSH 会话：
  - 远端文件检查
  - `RUNNING` 状态入账
  - required SQL 执行
  - `APPLIED` 状态入账
- SQL 执行失败仍由外层 catch 写 `FAILED` 并抛出，不吞异常。

## Verification

- RED: 新增 2 个合同测试 -> FAIL，`2 failed, 46 passed`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\green` -> PASS，`48 passed in 0.24s`。
- REGRESSION: 发布合同测试集合 -> PASS，`59 passed in 0.18s`。
- PowerShell AST parse: `PSSCRIPT_PARSE_OK`。
- `git diff --check`: PASS，仅 LF/CRLF warning。
- Tool preflight: `tar.exe`、`ssh.exe`、`scp.exe` present。

## Boundary

- 未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 未恢复、覆盖或提交仓库中既有的并行脏改动和 `frontend/` 删除状态。

## Commits

- Implementation: `e4bc1e5`（`任务: 优化required SQL状态入账`）。

## Closeout

- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，经验已合并到发布前置经验文档并更新索引。
