# 修复 MES Stage6 编译阻塞

## 任务目标

修复 `MesStage6IdiSimulationServiceImpl` 调用 `ErpKingdeeProductionPickListItemMapper.selectPickListIdsByProductionOrderNo(String)` 导致的后端编译失败，补齐正式 mapper 合同和回归测试，不改变无关业务行为。

## 里程碑

1. [completed] 建立 BDD/TDD 记录并复现缺失方法编译错误。
2. [completed] 确认生产订单号到领料单 ID 的现有 mapper 语义；确认源码已存在该方法，无需新增代码。
3. [completed] 使用 reactor 构建验证当前 mapper 合同和 MES 编译/测试。
4. [completed] 运行相关静态合同、差异审计和任务收尾。

## 预期验证

- BDD 场景覆盖查询存在结果、无结果和参数契约。
- RED 先证明方法不存在或编译失败，GREEN 再证明 mapper/API 合同通过。
- 使用 `mvn -pl yudao-module-mes -am "-Dtest=..." "-Dsurefire.failIfNoSpecifiedTests=false" test`，避免陈旧上游 reactor 依赖。
- 仅提交本任务任务记录；mapper、SQL 映射和生产测试均未修改，保留并发任务的其他脏改动。

## 经验门禁

### Maven 单模块陈旧依赖

- Trigger: 多模块 Maven 目标测试在 compile/testCompile 阶段提示 mapper、DTO 或 service 方法缺失。
- Preflight check: 先确认生产源码和 XML 映射，再使用 `mvn -pl yudao-module-mes -am` 运行目标测试。
- Blocker: 未进入 Surefire、上游模块使用陈旧 `.m2` 产物、或并发 Maven 写同一 target。
- Verification: reactor 编译通过并进入目标 Surefire；记录命令、退出码和测试数量。
- Forbidden action: 不删除无关 target、不缩小测试范围冒充通过、不修改并发任务源码绕过编译。
- Evidence: 本任务 execution-log.md 与 `docs/release-build-preflight-lessons.md` 中 Maven 依赖门禁。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。查询返回真实数据库结果，不返回默认成功值。
- 是否从根因和长期维护角度解决：是。确认 mapper 接口已在当前源码中存在，修正 Maven reactor 依赖验证门禁并用现有测试固定查询行为。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Final Verification

- `task-closeout-cleanup` preview/apply: PASS; task records retained, no task-specific temporary artifacts found.
- Reactor MES target test: PASS, 5 tests passed.
- Reactor ERP target test: PASS, 3 tests passed.
- `git diff --check` on task records and request log: PASS.
- No production source change or backend implementation commit required; concurrent Stage6 source remains untouched.
