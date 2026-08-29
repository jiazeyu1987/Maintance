# 20260829 优化 required SQL 远端完整性校验

## Task Goal

继续优化测试服发布链路耗时：把 required SQL 远端文件完整性校验集中到 tar 解包阶段，要求远端 SQL 文件数与本地发布计划一致，并取消每条 APPLY 前的额外 `ssh test -f` 往返；不改变 required SQL 执行顺序、状态入账、失败中止或 releaseTag 验收语义。

## Milestones

1. 启动门禁与任务文档：确认上一轮优化任务已完成，记录本轮 BDD、范围和预期验证。
2. RED 合同测试：新增测试证明当前远端归档只校验非空且 APPLY 循环仍逐条执行 `test -f`。
3. GREEN 实现：远端解包后校验 SQL 数量等于本地计划数量，移除 APPLY 循环中的逐条存在性 SSH 检查。
4. 回归验证：运行目标合同测试、发布合同回归、PowerShell AST、差异检查。
5. 收尾记录：清理本任务临时产物，记录经验与提交。

## Expected Verification

- RED: 新测试在旧实现下失败，命中 `remote_sql_count <= 0` 非精确校验，以及 `Invoke-RequiredDatabaseSqlScripts` 内仍存在 `test -f '$remoteSqlPath'`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过。
- REGRESSION: 发布合同测试集合通过；无法运行的相邻测试必须记录前置阻塞。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- `git diff --check` 通过；只提交本任务脚本/测试和任务记录。

## 经验门禁

- required SQL 单包上传后，远端解包校验必须证明数量等于本地计划，不得只校验非空。
- 只有在集中完整性校验通过后，才允许取消逐条 `test -f` 往返；SQL 执行本身仍必须 fail fast。
- 不跳过 required SQL、migration ledger、release lock、manifest、health、HTTP 或版本说明验收。
- 当前仓库存在与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务不得恢复、覆盖或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. RED 合同测试：completed，新增 2 个测试分别命中远端数量非精确校验和逐条 `test -f`。
3. GREEN 实现：completed，远端解包数量必须等于本地计划数量，APPLY 循环不再逐条执行存在性 SSH 检查。
4. 回归验证：completed，目标合同测试、发布合同回归、PowerShell AST 和差异检查通过。
5. 收尾记录：completed，task-closeout-cleanup 通过，长期经验与索引已更新，任务记录完成。

## Implementation Evidence

- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- `Copy-RequiredDatabaseSqlScriptsToServer` 解包后计算远端 `*.sql` 文件数，并要求 `remote_sql_count == $archiveSqlCount`。
- `Invoke-RequiredDatabaseSqlScripts` 取消每个 APPLY 项前的 `Invoke-SshCommand "test -f '$remoteSqlPath' && echo REQUIRED_SQL_EXISTS"`，依赖集中完整性校验和 SQL 执行本身 fail fast。

## Verification Evidence

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\red` -> FAIL，`2 failed, 44 passed`；失败测试为精确远端数量校验和取消逐条 SSH 文件检查。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\green` -> PASS，`46 passed in 0.14s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-remote-verification\pytest-parent\regression` -> PASS，`57 passed in 0.16s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-remote-verification/task.md doc/tasks/20260829-optimize-required-sql-remote-verification/execution-log.md doc/tasks/20260829-optimize-required-sql-remote-verification/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: 本机 `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Verification Boundary

- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 仓库中已有与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务未恢复、覆盖或提交。

## Closeout Evidence

- Implementation commit: `079c6a6`（`任务: 优化required SQL远端校验`）。
- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- project-experience-consolidation: 已合并到 `docs/release-build-preflight-lessons.md` 的 2026-08-29 required SQL 批量化门禁，并更新 `docs/experience-index.md` 关键词路由。
- 最终状态：completed。
