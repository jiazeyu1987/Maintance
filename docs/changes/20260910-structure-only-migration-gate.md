# 变更请求：日常发布改为结构迁移演练与目标只读依赖检查

## Request Summary And Source

- 来源：用户在 2026-09-10 明确提出“不管数据只管数据库结构”，并确认希望采用标准 CI/CD 方案。
- 请求：取消每次发布前复制约 15.4 GB 测试数据库的常态门禁，改为快速结构库演练；仍需防止菜单、权限、路线等目标数据状态导致发布中途失败。

## Current Baseline Reviewed

- 当前维护提交 `120df30`：每次 backend `build-release` 都从测试服执行完整 `mysqldump --single-transaction`，导入一次性同镜像 MySQL 后执行最终计划全部 APPLY SQL。
- r29 真实证据：完整快照约耗时 900 秒，成功暴露 `20260717_mes_balloon_excel_device_workstation_binding` 数据状态不兼容；Maven 未开始、真实库未写入、临时资源已清理。
- 现有构建预检已取得测试服新鲜 migration ledger，但尚无统一的“每条数据迁移只读依赖断言”契约。

## Classification

- 类型：发布策略变更、CI/CD 性能优化、数据库迁移安全策略调整。

## Impact Analysis

- Product/API：不改变产品或 API 行为。
- Data：日常门禁不复制业务数据、不写真实测试库；结构演练仅写一次性空库。
- Design：迁移验证拆为结构兼容性与目标数据依赖两条独立证据链。
- Tests：新增 schema-only dump/restore/迁移契约测试；非纯结构迁移必须有目标只读 preflight 证据，否则 fail fast。
- Release：日常门禁由约 15 分钟全库复制缩短为结构导出与小型临时库；同一不可变安装包仍用于测试和正式晋级。
- Operations：完整数据快照演练保留为显式高风险或定期任务，不再由日常 build-release 自动执行；MinIO 不参与数据库迁移门禁。
- Risk：若只执行空库 SQL 而没有目标只读断言，会漏掉 r17/r20/r21/r23/r29 类数据状态错误；因此只接受“结构演练 + 强制只读依赖检查”的组合，不接受纯空库假绿。

## Decision

- 决策：ACCEPT AND SPLIT。
- 日常强制：schema-only 临时 MySQL 演练 + 测试服只读依赖检查。
- 定期/高风险：完整数据快照演练作为独立流程，不阻塞普通安装包构建。
- 不允许 fallback：缺少只读依赖契约的非纯结构迁移必须在 Maven 前阻断。

## Required Approvals

- 用户已明确选择不复制业务数据并采用标准 CI/CD 方向。
- 正式服自动发布不在本次范围，仍需原有显式生产授权。

## Downstream Skill Reruns

- `ci-cd-environment-delivery`：调整 build-release 门禁、证据与顺序。
- `database-schema-delivery`：定义 schema-only 演练和非结构迁移只读 preflight 契约。
- `preflight-experience-consolidation`：更新发布经验门禁与索引。

## Blockers And Next Action

- 阻塞条件：无法为当前待执行的非纯结构迁移证明只读依赖契约时，不得构建。
- 下一步：先以测试锁定“不再完整复制业务数据”和“非结构迁移缺少只读 preflight 必须失败”，再实现脚本与证据。
