# 正式自动备份计划任务契约开发计划

## Purpose and Scope

本开发计划只覆盖 OPS-NODE-001 正式自动备份计划任务契约。目标是让自动备份计划任务的注册、生产授权、仓库选择和状态判定可通过测试复现，并避免把不可运行的正式计划任务展示为正常。

## Evidence Reviewed

- prd.md
- test-plan.md
- doc/tasks/20260813-production-operations-review/verification-report.md
- E:\IntRuoyi\docs\release-backup-restore.md
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\actions\Register-BackupOpsScheduledTasks.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\backup-ops.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_backup_ops_scheduled_task_contract.py
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_runtime_control_ops_scripts.py
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan
- E:\IntRuoyi\IntRuoyiFronted\src\views\system\backup-plan\index.vue

## Selected Node

| Node | Scope | Implementation Ready | Rollout Ready |
|---|---|---|---|
| OPS-NODE-001 | 正式自动备份计划任务注册与健康合同 | yes | blocked until production authorization |

Implementation readiness means local/test code work can begin with BDD + strict TDD. It does not authorize production scheduler registration, production backup execution, or remote server changes.

## Ownership and Source of Truth

- Owning implementation repository: E:\IntRuoyi\IntRuoyiBackend.
- Authoritative scripts: E:\IntRuoyi\IntRuoyiBackend\script\backup-ops.
- Backend service and release packager must both resolve the authoritative backend directory.
- D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops is a divergent historical copy. It is not modified, tested, packaged, or accepted in OPS-NODE-001. A separate cleanup/governance task may later delete it or establish a one-way generated mirror after explicit approval.
- Implementation commits for script/backend/menu tests belong to IntRuoyiBackend. RepositoryEnvironment 的只读状态字段和页面展示发生变化时，IntRuoyiFronted 必须产生独立提交；本节点不新增 RepositoryEnvironment 写入控件。

Completion of this plan means only the selected node is ready for implementation handoff. Successor nodes remain out of scope and must not be started from this task package.

## Out-of-Scope Successor Nodes

- 外部通知通道：等待渠道、凭据、责任人和测试目标确认。
- 备份可恢复性看板：等待候选状态机和仓库读取策略确认。
- 独立外部监控：等待部署位置和网络策略确认。
- 告警/事件闭环：等待通知节点完成，并保持告警生命周期与投递状态分离。
- Prometheus/Grafana/日志与镜像治理：等待监控采集端、管理网络和镜像批准策略。
- PITR：等待业务 RPO/RTO 决策。
- 只读分析与月报：等待只读数据源、指标负责人和口径确认。

## Blocker-Clearance Contracts

| Dependency | Entry Condition | Validation | If Missing |
|---|---|---|---|
| 后端脚本 source of truth | Backend service, tests and release packager all use E:\IntRuoyi\IntRuoyiBackend\script\backup-ops | backend pytest source-path/packaging contract + backend Pester | Block implementation if any runtime/package path uses maintenance copy |
| 计划任务 principal 与受保护生产确认输入 | Backend secrets supplies \`taskPrincipal.principalId\`; registrar fixes S4U/Limited; account has batch-logon right, no interactive login, least-privilege read/execute on scripts/config/secrets and write on task log/temp; ordinary users cannot write secrets | Named Pester principal-identity, S4U/Limited, batch-logon, ACL, masked-proof and fail-fast scenarios | Stop implementation if principal/batch-logon/S4U/Limited/ACL cannot be met; do not use current user/SYSTEM/highest or pass credentials/confirmation cleartext |
| RepositoryEnvironment propagation | backend backup-ops.config.json requires backup.repositoryEnvironment=test or backup; service -> BackupPlanSchedule -> gateway -> registrar propagates it; UI displays it read-only | frontend static display contract + JUnit propagation + backend Pester | Block IMPL-M2/IMPL-M3 if any layer drops/defaults it |
| 后端 scheduler 状态字段 | Status DTO and gateway can represent query exit code, task enabled state, command path check, config path, last result, next run, latest backup point, blocked reason | Maven target tests listed below | Block M3; do not map unknown/error to normal |
| 备份新鲜度 | 运维负责人 sets positive backup.maxFreshnessHours from approved RPO; missing/invalid config is abnormal | Pester config validation + JUnit health table | Implementation can deliver fail-fast state; production health remains configuration abnormal until value is supplied |
| 现有页面入口 | \`/system/backup-plan\` route, component, API wrapper, permission and menu SQL are present | Static test and authorized Playwright read-only E2E | Block M4 if adding a new entry is outside the implementation task scope |
| 正式服 rollout proof | Separate user authorization, protected input installed on server, and release/backup docs reread | Later authorized task evidence | Does not block this node's local/test implementation; blocks production rollout proof |

## Planning Principles

- 先写失败测试，再改脚本/后端/前端合同，最后跑回归。
- 不把生产确认明文写入计划任务命令、日志、报告或文档。
- 不用默认仓库、默认成功、mock 成功或静默降级填补缺失条件。
- 页面只验收现有 /system/backup-plan 入口；新增页面、菜单、权限不在本节点范围内。
- 正式服注册、启用、备份运行和连续成功证明必须另开授权任务。

## Milestones

| Milestone | Requirements | Outcome | Gate |
|---|---|---|---|
| IMPL-M1 | OPS-REQ-001A, OPS-REQ-001B, OPS-REQ-001E | 后端 source-of-truth、计划任务 principal 与受保护确认合同测试先失败 | backend pytest/Pester RED evidence |
| IMPL-M2 | OPS-REQ-001A, OPS-REQ-001B | 注册脚本支持显式 principal、仓库环境和非交互受保护确认 | Pester GREEN + parser |
| IMPL-M3 | OPS-REQ-001C, OPS-REQ-001D | RepositoryEnvironment 完整传播，后端按 health table 判定 | Maven target tests + frontend contract |
| IMPL-M4 | OPS-REQ-001D | 现有页面 query-only 路径显示当前状态和异常，且 query-only 权限隐藏全部写控件 | Node static + current-state Playwright + query-only permission Playwright |

## Implementation Steps

1. 在后端仓新增 script/backup-ops/tests/BackupScheduledTaskContract.Tests.ps1 和 script/tests/test_backup_ops_scheduled_task_contract.py，先证明 actual runtime/packaged source 中仍有明文确认、缺 RepositoryEnvironment、缺 principal，并证明 service/release packager 必须只指向 backend source。
2. 扩展 backend Register-BackupOpsScheduledTasks.ps1：要求显式 RepositoryEnvironment 和受保护 principalId；使用 New-ScheduledTaskPrincipal 固定 S4U/Limited，拒绝当前用户、SYSTEM 和缺失 principal；计划任务命令显式传 TargetEnvironment=prod、RepositoryEnvironment 和 NonInteractive，但不传确认明文或账号密码；plan-only 只展示 masked proof/principalId/logonType/runLevel。
3. 扩展 backend backup-ops.ps1 / Config/Validation：backup-scheduled 从 backend secrets auth.productionBackupConfirmText 读取确认，验证缺失/不匹配和 ACL；配置增加正整数 backup.maxFreshnessHours，缺失/非法为配置异常。
4. 扩展 backend config/BackupPlanSchedule/API page status：backup.repositoryEnvironment 为必填 test/backup，经 service、schedule、gateway 传播到 registrar，不设默认值；/system/backup-plan 页面只读显示，不新增写控件，本节点 E2E 保持 query-only。
5. 新增或扩展 BackupPlanServiceImplTest 和 WindowsBackupPlanSchedulerGatewayTest，覆盖 source path、principal/ACL status、RepositoryEnvironment 传播、schtasks 查询失败、禁用、NextRunTime=N/A、路径漂移、上次失败、备份点缺失、completedAt 缺失/非法和超过 freshness threshold。
6. 扩展状态 DTO，保留查询退出码、任务 principal、命令/配置/secrets 路径校验、blocked reason 和 masked proof；页面显示 concise blockedReason，不展示秘密或受保护路径。
7. 运行 backend Pester/pytest/Maven、frontend static/typecheck 和授权 query-only Playwright，并记录证据。

## Candidate Files

- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\actions\Register-BackupOpsScheduledTasks.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\backup-ops.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\modules\Core\Config.psm1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\modules\Core\Validation.psm1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\tests\BackupScheduledTaskContract.Tests.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_backup_ops_scheduled_task_contract.py
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_runtime_control_ops_scripts.py
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan\WindowsBackupPlanSchedulerGateway.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanServiceImpl.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanSchedulerStatus.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\controller\admin\backupplan\vo\BackupPlanStatusRespVO.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\controller\admin\runtimecontrol\vo\RuntimeControlBackupPointRespVO.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\test\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanServiceImplTest.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\test\java\cn\iocoder\yudao\module\infra\service\backupplan\WindowsBackupPlanSchedulerGatewayTest.java
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanSchedule.java
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\config\backup-ops.config.example.json
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\config\backup-ops.secrets.example.json
- E:\IntRuoyi\IntRuoyiFronted\src\views\system\backup-plan\index.vue
- E:\IntRuoyi\IntRuoyiFronted\src\api\system\backupPlan\index.ts
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-standard-list-static.spec.js
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-real-readonly.e2e.js
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-query-only-permission.e2e.js（planned）

## TDD Sequence

1. RED: Invoke-Pester -Script .\script\backup-ops\tests\BackupScheduledTaskContract.Tests.ps1
   - Working directory: E:\IntRuoyi\IntRuoyiBackend
   - Planned test file: script/backup-ops/tests/BackupScheduledTaskContract.Tests.ps1
   - Expected failure: actual backend plan-only 含明文生产确认、缺 RepositoryEnvironment/principal contract 或 masked proof。
2. GREEN: 同一 Pester 命令通过，且断言 plan-only 不包含确认明文或其它秘密。
3. RED: python -X utf8 -m pytest script/tests/test_backup_ops_scheduled_task_contract.py script/tests/test_runtime_control_ops_scripts.py -q
   - Working directory: E:\IntRuoyi\IntRuoyiBackend
   - Expected failure: current actual runtime/packaged source still exposes cleartext or lacks source-of-truth/repository/principal contract.
4. GREEN: 同一 pytest 命令通过。
5. RED: mvn -pl yudao-module-infra -am "-Dtest=BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
   - Working directory: E:\IntRuoyi\IntRuoyiBackend
   - Existing/planned tests: BackupPlanServiceImplTest and WindowsBackupPlanSchedulerGatewayTest
   - Expected failure: 状态模型无法表达脚本路径漂移、查询失败或缺少 protected confirmation blocked reason。
6. GREEN: 同一 Maven 命令通过。
7. REGRESSION: 在 E:\IntRuoyi\IntRuoyiBackend 运行 Invoke-Pester -Path .\script\backup-ops\tests -EnableExit。
8. REGRESSION: 在 E:\IntRuoyi\IntRuoyiBackend 运行 python -X utf8 -m pytest script/tests/test_system_backup_plan_menu_sql.py script/tests/test_publish_int_ruoyi_to_test_tooling.py -q。
9. REGRESSION: 在 E:\IntRuoyi\IntRuoyiFronted 运行 pnpm ts:check 和 node tests/e2e/system-backup-plan-standard-list-static.spec.js。
10. AUTHORIZED READ-ONLY E2E: 在 PowerShell 中执行 `$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-real-readonly.e2e.js`；缺少运行态或授权时记录 BLOCKED，不用 API 或 stub 替代。
11. QUERY-ONLY PERMISSION E2E: 使用预先批准的测试租户 query-only 账号运行 `$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-query-only-permission.e2e.js`；账号缺失时记录 BLOCKED，不临时改权限。

## UI Entry Contract

- Route: /system/backup-plan
- Component: E:\IntRuoyi\IntRuoyiFronted\src\views\system\backup-plan\index.vue
- API:
  - GET /admin-api/infra/backup-plan/status
  - PUT /admin-api/infra/backup-plan/schedule
  - POST /admin-api/infra/backup-plan/enable
  - POST /admin-api/infra/backup-plan/disable
  - POST /admin-api/infra/backup-plan/backup-now
  - GET /admin-api/infra/backup-plan/history/page
- Permissions:
  - system:backup-plan:query
  - system:backup-plan:update
  - system:backup-plan:execute
- Menu SQL: E:\IntRuoyi\IntRuoyiBackend\sql\mysql\20260725_system_backup_plan_menu.sql
- Test tenant access: query-only E2E 使用明确只有 \`system:backup-plan:query\` 的授权测试账号；项目默认 aoteman 全权限基线不能证明 query-only 控件行为。该账号未准备时权限场景记录 BLOCKED。Production UI verification requires separate authorization.
- Schedule contract: backend backup.repositoryEnvironment is required test/backup, propagated to registrar and displayed read-only; missing/invalid config fails. This is covered by config/Pester/JUnit/static display contract, not by query-only E2E.
- Query-only E2E: never click save, enable, disable, or backup-now. 只有 query permission 的账号应看到 status/history，update/execute controls 必须隐藏；后端用该身份调用四个写接口必须为 403（仅最终 API 权限比对，不替代页面步骤）。
- Read-only states to assert: current returned health state, blocked reason when present, empty history when naturally present, request error feedback when naturally reproducible through the real runtime. States without an approved frontend-only setup path are recorded BLOCKED, not claimed by source matching.
- Frontend entry: http://localhost:8081. Any override must be explicit, logged, and verified before navigation; implicit 8083 default is forbidden for acceptance.

## Deployment Strategy

1. 本地和测试环境先完成脚本、后端和前端只读验证。
2. 实现提交不得包含生产确认明文、真实 webhook、密码、token、私钥或连接串。
3. 测试服发布按既有 releaseTag 链路执行并验证 /system/backup-plan 页面。
4. 正式服计划任务注册、启用和连续运行证明另开授权任务，执行前读取 E:\IntRuoyi\docs\release-backup-restore.md 与 E:\IntRuoyi\docs\server-access.md。

## Verification Gates

- Pester、Maven、Node static、前端类型检查均有当前命令证据。
- Playwright 真实页面路径只在本地/测试运行态或授权环境执行；API 仅用于最终比对。
- 任何含生产确认明文、密码、token、私钥或连接串的输出必须阻塞提交。
- 状态接口和页面不得把查询失败、任务禁用、脚本路径漂移、受保护输入缺失或上次失败展示为正常。

## Rollback or Stop Conditions

- backend service/release packager/target tests do not all use E:\IntRuoyi\IntRuoyiBackend\script\backup-ops 时停止，不以维护仓副本测试代替。
- 无法满足显式 principalId/logonType、最小权限和 auth.productionBackupConfirmText ACL 边界时，停止实现，不改成命令行明文或其它未批准来源。
- 无法确认计划任务目标仓库，停止实现，不使用隐式默认。
- 状态字段无法表达关键 blocked reason，停止页面放行。
- Playwright 无真实入口、无测试租户权限或运行态不可用时，记录 E2E BLOCKED，不用 stub/API 替代。
- 发现生产环境写入、共享 NAS 风险或秘密泄露时立即停止。

## Blockers

- 无本节点本地实现入口阻塞。
- 生产注册与连续运行证明阻塞于用户明确授权和受保护确认输入在正式环境的安装验证。
- 后续通知、监控、PITR、分析和月报节点阻塞于各自业务/环境决策，不阻塞本节点。

## Completion Meaning

- \`ready-for-implementation\` 表示 OPS-NODE-001 可启动 RED 阶段，不表示正式服 rollout 已获授权。
- \`completed\` 只能在实施任务完成 Pester、Maven、Node static、类型检查和可授权的 Playwright 只读验证后使用。
- 正式服连续运行证明只能由后续授权任务完成，不得并入本节点放行口径。
