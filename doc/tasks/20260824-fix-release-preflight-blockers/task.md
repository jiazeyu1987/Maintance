# 发布前置阻塞修复

## 任务目标

修复最近发布前置门禁发现的两个真实阻塞，使后端 Spring 启动契约和 `20260814_mes_production_release_roles.sql` 通过同一套发布检查，并保留可回归验证的测试证据。

## 里程碑

1. [completed] 建立 BDD/TDD 任务记录，复现两个阻塞。
2. [completed] 修复 `MesProRouteVersionSnapshotMigrationRunner` 的 Spring 构造器注入契约并通过静态回归门禁。
3. [completed] 修复生产放行角色 SQL 的临时表读写冲突并通过 SQL 合同门禁。
4. [completed] 运行相关静态门禁、测试和差异审计，记录未解决阻塞。
5. [in_progress] 完成本任务实现提交、收尾记录和状态更新。

## 预期验证

- Spring 构造器合同测试先 RED 后 GREEN。
- SQL 合同测试先 RED 后 GREEN，且实际 `20260814_mes_production_release_roles.sql` 通过 `release_sql_contract_gate`。
- 相关 Python 测试、后端目标测试或编译检查、PowerShell 解析检查通过。
- 只提交本任务产生的后端源代码、SQL、测试和任务证据，不触碰并发工作区改动。

## 经验门禁

### 发布前置门禁

- Trigger: 发布构建、迁移 SQL 修改、Spring 启动 runner 修改。
- Preflight check: 先运行 `spring_constructor_contract_gate.py` 和 `release_sql_contract_gate.py`，再进入构建或服务器动作。
- Blocker: 多构造器无明确注入入口、临时表在同一语句中重复引用、或实际迁移 SQL 仍被门禁拒绝。
- Verification: 门禁退出码为 0，目标测试通过，且记录实际路径和输出摘要。
- Forbidden action: 禁止删除门禁、跳过检查、改成静默降级或用复制旧发布证据绕过。
- Evidence: `20260824-release-preflight-build-optimization` 的门禁实现与本任务执行日志。

### 数据库迁移安全

- Trigger: 修改 `sql/mysql/20260814_mes_production_release_roles.sql`。
- Preflight check: 以当前 SQL 为准检查临时表生命周期、读写语句和回滚清理路径；不执行正式服写入。
- Blocker: 无法证明临时表读写安全、清理不完整、或缺少数据库引擎/迁移工具验证。
- Verification: 静态合同门禁通过，SQL 结构测试通过，记录变更前后语义和清理路径。
- Forbidden action: 不删除既有数据、不改测试/正式租户数据、不用 mock 成功掩盖 SQL 失败。
- Evidence: `release_sql_contract_gate.py` 输出与数据库合同证据。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。两个修复都保持失败即报错。
- 是否从根因和长期维护角度解决：是。Spring 使用明确注入构造器；SQL 使用独立迭代快照表消除 MySQL 1137 根因。
- 是否存在临时补丁或绕过：否。

## Current Status

ready_for_closeout
