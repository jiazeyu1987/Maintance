# 两入口发布下一步实施分析

## Current Status
completed

## 用户确认与目标
用户同意保留现有构建、部署、验收、晋级阶段作为后台步骤，收敛为“发布到测试服”和“晋级正式服”两个顶层入口；先修复锁和状态问题，再做真实页面测试服发布及正式晋级验收。本任务分析现有代码、明确实施范围和顺序，形成可执行计划，不立即修改产品或执行发布。

## 里程碑
1. 读取现有前后端、工作流和发布器合同，核对当前基线（完成）。
2. 明确两个入口的请求/状态/验收行为、复用边界及 BDD/TDD 顺序（完成）。
3. 保存下一步计划及分析证据，完成本任务收尾（完成）。

## 预期验证
每项计划对应实际类/组件和当前缺口；区分编码、隔离验证、独立复检和真实发布；不以计划形成替代实施或发布成功。

## 经验门禁
- Trigger：按钮化发布、状态编排、发布锁、既有流程收敛。
- Preflight check：前序自有审查已 completed；复核最新源码和批准提交，既有 R22 GO 只对应精确旧提交，新产品变更不能直接继承该 GO。
- Blocker：源身份不明、关键阶段契约或测试缺失时记录，不用默认成功或手工补状态绕过。
- Verification：按本任务 execution-log.md、实施计划和代码路径交叉核对。
- Forbidden action：不改写不可变旧迁移、不修改冻结发布包、不操作并行发布锁/进程，不在本规划任务执行远程写入。
- Evidence：适用 AGENTS、docs/experience-index.md、前序审查报告及当前源码。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；失败阶段、写入边界与人工处置必须显式。
- 是否从根因和长期维护角度解决：是；复用既有阶段、状态机和执行器，增加两个业务入口的固定编排。
- 是否存在临时补丁或绕过：否。

## Cleanup Keep
- doc/tasks/20260924-two-button-release-next-steps/task-state.json
- doc/tasks/20260924-two-button-release-next-steps/implementation-plan.md
- doc/tasks/20260924-two-button-release-next-steps/docs/acceptance/bdd-scenarios.md
- doc/tasks/20260924-two-button-release-next-steps/docs/acceptance/tdd-plan.md
- doc/tasks/20260924-two-button-release-next-steps/docs/acceptance/e2e-plan.md
- doc/tasks/20260924-two-button-release-next-steps/docs/acceptance/test-data.md

## 当前阻塞
无。仅分析，不实施和发布。

## 分析验证
变更评估与BDD/TDD计划校验器通过，实际源码/测试位置已交叉核对。该通过仅指规划文档有效，不代表产品实现、测试或发布已完成。
