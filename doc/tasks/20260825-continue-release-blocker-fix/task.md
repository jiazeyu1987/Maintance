# 继续修复发布阻塞

## 任务目标

修复并验证 `code-only` 发布迁移依赖闭包与正式库基线漂移的可执行前置门禁，先在本地源码和合同测试中消除可修复错误，再决定是否具备继续发布条件；禁止手工修改正式库、迁移台账或复用失败 releaseTag。

## 里程碑

1. [completed] 建立 BDD/TDD 记录并确认当前未完成任务的最高优先级根因。
2. [completed] 复现并验证现有迁移依赖闭包/基线对账门禁。
3. [completed] 确认当前实现已覆盖依赖闭包，暂无安全的本地代码补丁。
4. [completed] 运行静态门禁、目标测试和独立验证。
5. [completed] 完成任务收尾并记录剩余外部阻塞。

## 预期验证

- BDD 场景覆盖 `code-only` 过滤 data 祖先、已应用且 checksum 等价的祖先、checksum 不一致的正式库状态。
- RED 先证明现有计划/对账逻辑不能安全放行或无法准确区分状态。
- GREEN 使用目标 Python 回归测试和全量相关门禁。
- 不执行服务器写入、发布、数据库写入、迁移台账修改或 E2E。

## 经验门禁

### code-only 迁移依赖闭包与真实状态

- Trigger: `publishScope=code-only` 跳过 `type=data`，但可执行迁移直接或传递依赖该 data 迁移，或正式库 ledger checksum 与 manifest 不一致。
- Preflight check: 读取 manifest migrationPlan、target migration state 和 SQL live-state 契约；按过滤后的执行图计算最小阻塞链。
- Blocker: `APPLY` 节点依赖被过滤且未被真实状态满足的祖先，或 checksum 不一致且没有正式 reconciliation。
- Verification: 保存 RED/GREEN 测试、最小依赖链、checksum 差异和目标计划状态。
- Forbidden action: 禁止改 ledger、补正式库数据、修改 manifest、复用失败 releaseTag 或用旧容器健康状态代替目标版本验证。
- Evidence: 本任务 `execution-log.md`、相关迁移策略测试和既有 `docs/test-release-preflight.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；优先修复迁移计划/状态判定合同，不以发布时绕过为方案。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Final Verification

- Backend preflight plan tests: 17 passed using task-scoped basetemp.
- Maintenance release SQL contract tests: 32 passed using task-scoped basetemp.
- task-closeout-cleanup preview/apply: PASS; temporary pytest artifacts removed, core records retained.
- No production source change or server/database write was made; formal r11 reconciliation remains an external blocker.

## 结论

本地迁移计划实现已正确阻断 code-only 过滤后仍依赖 pending data 祖先的执行图；正式服 r11 的剩余阻塞来自历史迁移 checksum/真实状态漂移，当前没有正式 reconciliation 入口。未执行服务器写入、迁移台账修改、发布或失败 releaseTag 重试。
