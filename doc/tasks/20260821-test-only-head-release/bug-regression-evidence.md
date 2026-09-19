# Bug Regression Evidence

## Incident

- 现象：测试服 `publish-test` 的 route snapshot BACKFILL 在 Spring context 初始化阶段失败，日志为 `MesProRouteVersionSnapshotMigrationRunner: No default constructor found`。
- 发现阶段：2026-08-21 发布包 `release-20260821-intmain-head-test-r260821h-r4` 的测试服发布运行报告。
- 影响：backend 新镜像未完成运行报告，r4 不得判定发布成功；未执行 mark-tested、正式服或备份服动作。
- 原因判断：runner 同时存在生产构造函数和测试构造函数，但生产构造函数没有显式 `@Autowired`，Spring 无法确定注入构造函数。

## Reproduction And Fix

- Given route snapshot runner has multiple constructors, When Spring creates the runner bean, Then the production constructor must be selected and the context must start.
- RED：移除 `@Autowired` 后，Spring context regression test FAIL，错误为 `BeanCreationException ... No default constructor found`。
- 最小修复：在生产构造函数上增加 `@Autowired`，不引入 fallback、吞异常或测试绕过。
- GREEN：恢复 `@Autowired` 后同一 Spring context regression test PASS；目标 Maven reactor PASS；实现提交 `c4d2c637bf1f2cea723876ee363f311b1128aaf4`。

## Follow-Up

- 发布前检查：对发布报告涉及的 Spring Bean 执行 context smoke；多构造函数 Bean 必须存在唯一显式注入构造函数。
- 自动化：将该 Spring context 回归测试保留在 `MesProRouteVersionSnapshotMigrationCommandTest`，并纳入 build-release 前置验证。
- 下次避免：必须从包含该提交的全新干净 release worktree 构建，并用新的 releaseTag 完成 manifest、镜像和测试服真实运行态闭环。
