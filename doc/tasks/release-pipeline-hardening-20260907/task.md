# 发布流水线 P0 优化

## Task Goal

通过不可变安装包和发布前置门禁，减少服务器阶段晚失败与重复完整打包；本轮实施 direct 收口、生产级环境数据包阻断、包完整性强校验、tested 证明强绑定，并评估可安全落地的 preflight 与构建缓存优化。

## Milestones

- [completed] M1：PRD/test plan 与独立规划审查。
- [completed] M2：逐阶段严格 TDD 实现。
- [completed] M3：独立测试与回归验证。
- [in_progress] M4：实现提交、融合验证和任务收尾。

## Expected Verification

- 所有拒绝路径均在远端写入前发生。
- 合法 code-only 测试服与生产级晋级路径保持兼容。
- 包哈希、测试 operation 和 tested 证明形成可验证绑定。
- PowerShell、Java、Python 合同测试和相关回归通过。

## 经验门禁

- Trigger：发布脚本、安装包、反复打包、测试服/正式服晋级。
- Preflight check：只在本任务 worktree 修改；先写 BDD/RED；不连接远端；所有新门禁必须 fail fast。
- Blocker：需要 fallback、无法验证写入顺序、与并发任务改动重叠或测试依赖缺失时停止。
- Verification：精确测试命令、PowerShell AST、差异检查和独立测试报告。
- Forbidden action：禁止真实发布、修改失败包、手工改服务器/NAS/数据库或弱化现有门禁。
- Evidence：`prd.md`、`test-plan.md`、`execution-log.md`、`test-report.md`、`task-state.json`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。
- 是否存在临时补丁或绕过：否。

## Worktree

- Path: `D:/ProjectPackage/Int/IntRuoyiWorktrees/release-pipeline-hardening-20260907/m`
- Branch: `codex/release-pipeline-hardening-20260907`
- Baseline: `b085f32e4953138467223a17a1afbe03e6b1ad7d`
- Ports: 未启动服务，不登记端口。

## Current Status

ready_for_closeout

## Completed Work

- P1：删除 direct/default Mode，生产级环境拒绝 with-data 包。
- P2：新增逐文件完整性、稳定 package/manifest digest 与四生命周期校验。
- P3：tested v2 绑定真实成功 publish-test operation；prod/backup 统一强制复核，移除 RequireTested 与备份服临时绕过。

## Verification Evidence

- Independent blind-first-pass final verdict: PASS。
- Governance pytest: 57 passed；focused pytest: 65 passed；full pytest: 146 passed。
- JDK 17 Maven: 27 passed；Node: 6 passed。
- PowerShell AST、`scripts/verify_contracts.py`、`git diff --check`：PASS。
- 未连接 NAS、SSH、Docker、数据库、MinIO 或任何服务器。

## Remaining Blockers

- 无实现或测试阻塞；实现提交已快进融合 `int_main`，待任务记录提交和 worktree 清理。

## Implementation Commits

- `ad9bf60`：加固不可变发布包门禁。
- `82c4d44`：将测试证据选择职责移出并发修改文件。
- `4303126`：按 requestedAt/operationId 固定发布操作选择顺序。

## Integration Verification

- `int_main` 已 fast-forward 到 `4303126`；原有未提交 `RuntimeControlOperationStore` 改动和其它并发改动保持存在，未被覆盖。
- 主工作区 JDK 17 Maven：27 passed，包含并发任务新增 OperationStore 测试；BUILD SUCCESS。
- 主工作区 Node：6 passed；PowerShell AST：2 files PASS。
- 主工作区治理/相邻 pytest：123 passed，唯一失败为本任务前已有 `frontend/src/App.vue` 删除导致前端合同测试 FileNotFound；隔离 worktree 全量 pytest 146 passed，独立最终验证 PASS。

## Cleanup Candidates

- `output/pytest-release-governance-p3-ordering-full/`

## Cleanup Keep

- `doc/tasks/release-pipeline-hardening-20260907/task.md`
- `doc/tasks/release-pipeline-hardening-20260907/prd.md`
- `doc/tasks/release-pipeline-hardening-20260907/test-plan.md`
- `doc/tasks/release-pipeline-hardening-20260907/task-state.json`
- `doc/tasks/release-pipeline-hardening-20260907/execution-log.md`
- `doc/tasks/release-pipeline-hardening-20260907/test-report.md`
