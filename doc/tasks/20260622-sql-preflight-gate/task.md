# 任务：发布 SQL 预检前移门禁

## 任务目标

把 SQL 风险从远端 `deploy-release` 慢路径前移到本机 `build-release` 预检阶段，先在维护仓落地两个长期门禁：

1. `required SQL` 迁移策略门禁在 Maven/Vite/Docker 构建前执行。
2. 发布 SQL 中 `system_menu` 主键冲突在本机预检阶段直接失败，不再等测试服部署半天后才暴露。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-backup-server-backup-restore-rerun\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已闭环完成，本轮为新的维护仓长期治理任务，单独建档执行。

## 用户要求与执行边界

- 用户要求：落实“只要 SQL 有变动，发布就很久”的长期解决方案。
- 当前任务授权：
  - 允许仅在维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 内修改发布脚本、预检脚本、测试与任务文档。
  - 允许执行本地只读分析和本地测试。
- 禁止范围：
  - 不操作测试服、正式服、备份服，不触发真实发布。
  - 不修改业务仓 `D:\ProjectPackage\Int\IntRuoyi` 源码或远端环境。
  - 不用 fallback、静默跳过、默认成功掩盖 SQL 预检失败。

## 技能与交付契约

- 使用技能：`ci-cd-environment-delivery`、`database-schema-delivery`
- 契约摘录：
  - 必须把 build/test/package/deploy gate 做成显式可复现的流程能力。
  - 必须先写失败校验，再做最小实现。
  - 必须记录 BDD、RED、GREEN、风险和阻塞。
  - SQL/迁移改动必须以数据安全门禁方式交付，不能靠远端慢发布再暴露问题。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 凡是本机正常、服务器失败、构建后才暴露的问题，都要补成 preflight、测试或脚本门禁，不能只修一次。
  - 构建前先跑迁移策略门禁，`code-only` 不等于跳过 required SQL、迁移元数据或发布 manifest 门禁。
  - 发布相关配置和校验必须代码化，不能依赖人工记忆或服务器现场。
  - 部署输入变更后必须用新 `releaseTag` 整链复测；旧候选包只能作证据，不能继续发布。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。本次直接把 SQL 失败前移到本机构建预检。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: build-release 前移 SQL 门禁 -> Given 发布候选包含 required SQL / When 本机构建开始前执行 SQL 预检 / Then 迁移策略或菜单主键冲突必须在 Maven/Vite/Docker 前直接失败。`
- `BDD: system_menu 主键冲突提前暴露 -> Given 两个发布 SQL 向 system_menu 写入同一个 id / When 运行维护仓 SQL 预检 / Then 返回明确冲突明细并阻断发布。`
- `BDD: 合法 required SQL 正常通过 -> Given 发布 SQL metadata 完整且 system_menu id 不冲突 / When 运行 build-release 预检 / Then 预检通过，后续打包流程才允许继续。`

## 里程碑

1. 建立本任务文档、执行日志与请求记录。`DONE`
2. 完成经验门禁与发布链路上下文核对。`DONE`
3. 写出 SQL 预检 RED 测试。`DONE`
4. 实现 `system_menu` 冲突预检并接入现有迁移策略门禁。`DONE`
5. 把 SQL 门禁调用前移到 build-release 耗时步骤之前。`DONE`
6. 完成本地回归、更新任务文档和执行日志。`DONE`

## 预期验证

- `python -m pytest scripts\tests\test_release_sql_preflight_gate.py` 能覆盖：
  - duplicate `system_menu.id` 失败。
  - 合法 SQL 通过。
  - 发布脚本中 SQL 门禁调用早于 backend/frontend build。
- `python -m pytest scripts\tests\test_showroom_release_sql_contract.py` 继续通过，证明旧发布合同未回退。
- 发布脚本静态契约明确：
  - `Invoke-ReleaseMigrationPolicyGate` 只保留一次实际调用。
  - 调用位置位于 `$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts` 之后、`Info 'Building backend jar'` 之前。

## 当前状态

COMPLETED：维护仓 SQL 预检前移门禁已完成，并在真实页面 `build-release(v11)` 暴露出的新回归上完成二次收口。当前 `release_sql_contract_gate.py` 已支持跳过合法 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 更新子句，不再对 `20260520_system_nas_management_menu.sql` 误报。

## 最终验证

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> `PASS`（4 passed）
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro\sql\mysql` -> `PASS`（`migrationCount=186`）
- 真实页面失败证据 `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 已回灌本任务与主发布链路任务，后续可回页面改用 `release-20260621-page-full-flow-mainmerge-v12` 继续重跑。
