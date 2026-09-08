# 发布流水线 P0 优化

## Task Goal

通过不可变安装包和发布前置门禁，减少服务器阶段晚失败与重复完整打包；本轮实施 direct 收口、生产级环境数据包阻断、包完整性强校验、tested 证明强绑定，并评估可安全落地的 preflight 与构建缓存优化。

## Milestones

- [completed] M1：PRD/test plan 与独立规划审查。
- [completed] M2：逐阶段严格 TDD 实现。
- [completed] M3：独立测试与回归验证。
- [completed] M4：实现提交、融合验证和任务收尾。

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

completed

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

## Closeout Evidence

- Implementation commits `ad9bf60`、`82c4d44`、`4303126` 与任务证据提交 `ee93103` 已 fast-forward 融入 `int_main`。
- 任务 worktree 已确认 clean、与 `int_main` 同为 `ee93103` 后移除；物理路径和 Git 注册均不存在。
- `task-closeout-cleanup` 在 worktree preview 因主工作区并发脏改动保护而阻断；完成显式 fast-forward 和 worktree 清理后，在主工作区重新执行 preview=`ready`、apply=`applied`，无 blocked，唯一 warning 为已清理的 pytest 路径不存在。
- `project-experience-consolidation` 已把 tested v2、完整性校验、恢复兼容与 operation 确定性排序合并到现有 `docs/release-build-preflight-lessons.md`，未新建长期经验文档。

## Final Verification

- 独立最终验证：T1-T15、P1-AC1..P3-AC6 全部 PASS；test-report schema validation PASS。
- 隔离 worktree：governance 57、focused 65、full pytest 146、JDK17 Maven 26、Node 6、AST/verify_contracts/diff check 全部 PASS。
- 融合主工作区：JDK17 Maven 27 PASS、Node 6 PASS、PowerShell AST 2 files PASS；并发 OperationStore 改动与其新增测试共同通过。
- 主工作区相邻 pytest 123 PASS / 1 FAIL；唯一失败是本任务前已有 `frontend/src/App.vue` 删除导致 `FileNotFoundError`，隔离 worktree同一完整套件为 146 PASS。本任务未恢复或覆盖该并发删除。
