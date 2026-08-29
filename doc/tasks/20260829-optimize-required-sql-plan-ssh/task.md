# 20260829 优化 required SQL 规划阶段 SSH 往返

## Task Goal

继续优化测试服发布链路耗时：检查 `publish-test` required SQL 规划与执行路径中仍可批量化的远端 SSH / MySQL 往返，优先减少可证明的逐条状态查询或文件校验开销；保持 releaseTag、manifest、migration ledger、fail-fast 和失败证据不变。

## Milestones

1. 启动门禁与任务文档：记录本轮范围、BDD、预期验证和经验门禁。
2. 代码合同盘点：定位 required SQL 规划/执行路径中仍存在的逐条远端往返点。
3. RED 合同测试：先新增失败测试证明目标往返仍是逐条执行。
4. GREEN 实现：用最小脚本改动批量化该往返点，保留失败阻断和证据。
5. 回归验证与收尾：运行目标合同、发布合同回归、PowerShell AST、差异检查、经验沉淀和任务收尾。

## Expected Verification

- BDD: Given required SQL 列表较多，When publish-test 规划/执行 required SQL，Then 已可预先批量判断的信息不得逐条建立 SSH 会话。
- RED: 新增合同测试在旧实现下失败，失败原因指向本轮目标逐条 SSH / MySQL 往返。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过。
- REGRESSION: 发布合同相关测试集合通过。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- `git diff --check` 通过；只提交本任务脚本/测试和任务记录。

## 经验门禁

- required SQL 批量化只能减少远端往返，不得跳过 required SQL、手工改 migration ledger、复用失败 releaseTag/旧包、降低 manifest/运行态验收标准。
- required SQL staging 必须先有单 tar 上传、远端解包数量一致、`SKIP_ALREADY_APPLIED` 批量 upsert、APPLY 成功路径单 SSH 的既有合同保护；本轮优化不得破坏这些合同。
- 若发现新的批量化目标，必须先用 RED 合同证明旧实现逐条远端调用，再实现最小批量化并回归既有合同。
- 日志、异常和任务证据不得输出 `mysql -p...`、`MYSQL_PWD=` 原值、password/token/secret 等敏感信息。
- 当前仓库存在与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务不得恢复、覆盖或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed，已读取 required SQL 批量化与脱敏门禁。
2. 代码合同盘点：completed，确认 route snapshot 身份迁移 hook 每个模式仍分两次 SSH：运行 backend 后再检查报告。
3. RED 合同测试：completed，新增合同在旧实现下失败，命中 2 次 `Invoke-SshCommand`。
4. GREEN 实现：completed，`Invoke-RouteSnapshotIdentityMigrationCommand` 改为单个远端脚本块内完成 run + report check。
5. 回归验证与收尾：completed，目标合同、发布合同回归、PowerShell AST、差异检查、task-closeout-cleanup 和经验沉淀完成。

## Implementation Evidence

- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- `Invoke-RouteSnapshotIdentityMigrationCommand` 由每个模式 2 次 `Invoke-SshCommand` 调整为 1 次：
  - `mkdir`/清理旧 report
  - `docker compose run --rm --no-deps ... backend`
  - `test -f` report
  - `grep` 校验 `"status" : "READY"` 和 `"blockerCount" : 0`
- 使用 `set -e` 保持任一步失败即阻断；不改变 required SQL 排序、APPLY 状态入账、route snapshot hook 触发条件或 release ledger。

## Verification Evidence

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_combines_route_snapshot_run_and_report_check_in_single_ssh_session -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\red` -> FAIL，`1 failed`，旧实现中 helper 含 2 次 `Invoke-SshCommand`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_combines_route_snapshot_run_and_report_check_in_single_ssh_session -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\green` -> PASS，`1 passed in 0.02s`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\sql-gate` -> PASS，`49 passed in 0.25s`；首次全量运行因 `--basetemp` 父目录不存在产生 setup error，创建本任务临时父目录后复跑通过。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-required-sql-plan-ssh\pytest-parent\regression` -> PASS，`60 passed in 0.17s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-required-sql-plan-ssh/task.md doc/tasks/20260829-optimize-required-sql-plan-ssh/execution-log.md doc/tasks/20260829-optimize-required-sql-plan-ssh/verification-report.md` -> PASS，仅 LF/CRLF warning。

## Verification Boundary

- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 仓库中已有与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务未恢复、覆盖或提交。

## Closeout Evidence

- Implementation commit: `f035655`（`任务: 优化route snapshot发布hook校验`）。
- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- project-experience-consolidation: 已合并到 `docs/release-build-preflight-lessons.md` 的 2026-08-29 required SQL 批量化门禁，并更新 `docs/experience-index.md` 关键词路由。
- request-command-log: 已追加本轮优化条目并记录实现提交。
- 最终状态：completed。
