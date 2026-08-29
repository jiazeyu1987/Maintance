# 20260829 优化 required SQL APPLY 状态入账 SSH 往返

## Task Goal

继续优化测试服发布链路耗时：将每个 required SQL APPLY 项的 `RUNNING -> SQL -> APPLIED` 成功路径收敛到单次 SSH 会话中执行，减少每条 SQL 额外两次 SSH 往返；保留 SQL 执行失败后的本地 `FAILED` 入账和 fail-fast 语义。

## Milestones

1. 启动门禁与任务文档：记录本轮范围、BDD、预期验证和经验门禁。
2. RED 合同测试：新增测试证明当前 APPLY 循环仍逐条调用 `Invoke-ReleaseMigrationStateUpdate` 写 `RUNNING` 和 `APPLIED`。
3. GREEN 实现：新增单项 APPLY helper，在同一 SSH 命令中写 `RUNNING`、执行远端 SQL、写 `APPLIED`；失败 catch 仍写 `FAILED`。
4. 回归验证：运行目标合同测试、发布合同回归、PowerShell AST 和差异检查。
5. 收尾记录：清理本任务临时产物，记录经验与提交。

## Expected Verification

- RED: 新测试在旧实现下失败，命中 `Invoke-RequiredDatabaseSqlScripts` 内仍有 `Invoke-ReleaseMigrationStateUpdate -Status 'RUNNING'` 和 `-Status 'APPLIED'`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过。
- REGRESSION: 发布合同测试集合通过；无法运行的相邻测试必须记录前置阻塞。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- `git diff --check` 通过；只提交本任务脚本/测试和任务记录。

## 经验门禁

- APPLY 状态合并只能减少 SSH 会话，不得跳过 `RUNNING`、`APPLIED` 或失败后的 `FAILED` 入账。
- SQL 执行失败必须继续抛出异常并由 catch 写入 `FAILED`，不得吞异常或返回默认成功。
- 不改变 required SQL 执行顺序、session preamble、route snapshot hook、migration ledger、release lock、manifest 或运行态验收。
- 当前仓库存在与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务不得恢复、覆盖或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. RED 合同测试：completed，新增 2 个测试命中 APPLY 循环仍直接写 `RUNNING`/`APPLIED`。
3. GREEN 实现：completed，新增 `Invoke-RequiredDatabaseSqlScriptWithState`，成功路径单 SSH 完成远端文件检查、RUNNING、SQL、APPLIED。
4. 回归验证：completed，目标合同测试、发布合同回归、PowerShell AST 和差异检查通过。
5. 收尾记录：completed，task-closeout-cleanup 通过，长期经验与索引已更新，任务记录完成。

## Implementation Evidence

- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- 新增 `Invoke-RequiredDatabaseSqlScriptWithState`，在单次 `Invoke-SshCommand` 中执行：
  - `test -f <remote sql>`
  - `RUNNING` 状态 upsert
  - required SQL 执行，含原有 session preamble 支持
  - `APPLIED` 状态 upsert
- `Invoke-RequiredDatabaseSqlScripts` 的 catch 仍调用 `Invoke-ReleaseMigrationStateUpdate -Status 'FAILED'` 并 `throw`，保留 fail-fast 与失败证据。

## Verification Evidence

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\red` -> FAIL，`2 failed, 46 passed`；失败测试为成功路径单 SSH 状态入账和失败后 FAILED 入账契约。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\green` -> PASS，`48 passed in 0.24s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-apply-state-ssh\pytest-parent\regression` -> PASS，`59 passed in 0.18s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-apply-state-ssh/task.md doc/tasks/20260829-optimize-required-sql-apply-state-ssh/execution-log.md doc/tasks/20260829-optimize-required-sql-apply-state-ssh/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: 本机 `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Verification Boundary

- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 仓库中已有与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务未恢复、覆盖或提交。

## Closeout Evidence

- Implementation commit: `e4bc1e5`（`任务: 优化required SQL状态入账`）。
- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- project-experience-consolidation: 已合并到 `docs/release-build-preflight-lessons.md` 的 2026-08-29 required SQL 批量化门禁，并更新 `docs/experience-index.md` 关键词路由。
- 最终状态：completed。
