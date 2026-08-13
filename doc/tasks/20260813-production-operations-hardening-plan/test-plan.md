# 正式自动备份计划任务契约测试计划

## Purpose and Scope

本测试计划覆盖 OPS-NODE-001 正式自动备份计划任务契约。测试目标是证明计划任务注册命令、生产授权输入、仓库环境、状态接口和现有页面只读路径可被重复验证。

测试默认在本地和测试环境执行。任何正式服注册、启用、备份、恢复、远端状态写入或生产页面验证都必须另开授权任务。

## Evidence Reviewed

- prd.md
- development-plan.md
- doc/tasks/20260813-production-operations-review/verification-report.md
- E:\IntRuoyi\docs\release-backup-restore.md
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\actions\Register-BackupOpsScheduledTasks.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\backup-ops.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_runtime_control_ops_scripts.py
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_publish_int_ruoyi_to_test_tooling.py
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\test\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanServiceImplTest.java
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-standard-list-static.spec.js
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-real-readonly.e2e.js

## Test Strategy

- BDD 描述运维人员可观察行为。
- 严格 TDD：先写 RED，再最小实现 GREEN，最后回归。
- 脚本合同用 Pester 和 PowerShell Parser。
- 后端状态合同用 Maven 目标 JUnit。
- 前端只验证已有 /system/backup-plan 页面，不新增入口。
- E2E 只能由 Playwright 操作真实页面；API 仅用于最终比对。
- 禁止 mock 成功、静默跳过、stub 替代 E2E、自动修改生产数据或输出秘密。

## Exact Command Matrix

| Layer | Command | Working Directory | Test File/Class | Evidence |
|---|---|---|---|---|
| Pester RED/GREEN | Invoke-Pester -Script .\script\backup-ops\tests\BackupScheduledTaskContract.Tests.ps1 | E:\IntRuoyi\IntRuoyiBackend | planned script/backup-ops/tests/BackupScheduledTaskContract.Tests.ps1 | implementation execution-log.md |
| Pester regression | Invoke-Pester -Path .\script\backup-ops\tests -EnableExit | E:\IntRuoyi\IntRuoyiBackend | script/backup-ops/tests | implementation execution-log.md |
| Source/package RED/GREEN | python -X utf8 -m pytest script/tests/test_backup_ops_scheduled_task_contract.py script/tests/test_runtime_control_ops_scripts.py -q | E:\IntRuoyi\IntRuoyiBackend | planned test_backup_ops_scheduled_task_contract.py + existing runtime source test | pytest output |
| Backend RED/GREEN | mvn -pl yudao-module-infra -am "-Dtest=BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest" "-Dsurefire.failIfNoSpecifiedTests=false" test | E:\IntRuoyi\IntRuoyiBackend | existing BackupPlanServiceImplTest + planned WindowsBackupPlanSchedulerGatewayTest | Surefire reports |
| Backend release/menu regression | python -X utf8 -m pytest script/tests/test_system_backup_plan_menu_sql.py script/tests/test_publish_int_ruoyi_to_test_tooling.py -q | E:\IntRuoyi\IntRuoyiBackend | existing menu and packaging tests | pytest output |
| Frontend static | node tests/e2e/system-backup-plan-standard-list-static.spec.js | E:\IntRuoyi\IntRuoyiFronted | tests/e2e/system-backup-plan-standard-list-static.spec.js | node output |
| Frontend typecheck | pnpm ts:check | E:\IntRuoyi\IntRuoyiFronted | TypeScript project | pnpm output |
| Authorized read-only E2E | `$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-real-readonly.e2e.js` | E:\IntRuoyi\IntRuoyiFronted | tests/e2e/system-backup-plan-real-readonly.e2e.js | Playwright log/screenshot |
| Query-only permission E2E | `$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-query-only-permission.e2e.js` | E:\IntRuoyi\IntRuoyiFronted | planned tests/e2e/system-backup-plan-query-only-permission.e2e.js | Playwright log/screenshot + final 403 comparison |

## BDD Scenarios

### BDD: 计划任务注册命令包含正式备份必需合同

Given 运维负责人已在 backend backup-ops.config.json 显式配置 test 或 backup 仓库，受保护配置已声明专用 principalId\
When 以 plan-only 方式生成计划任务命令摘要\
Then 摘要包含 backup-scheduled、TargetEnvironment=prod、RepositoryEnvironment=<test|backup> 和 NonInteractive\
And 摘要只显示 masked production authorization proof\
And 摘要不包含生产确认明文、密码、token、私钥或连接串

### BDD: 实际运行与打包只使用后端脚本源

Given backend service 与发布打包器准备引用自动备份脚本\
When 执行 source-of-truth 合同测试\
Then 两者只引用 E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\
And 实际注册脚本不含明文生产确认\
And 维护仓副本不作为 GREEN 或打包输入

### BDD: 生产确认受保护输入缺失时失败

Given 非交互正式备份计划任务缺少受保护生产确认输入/principalId、principal 不是 S4U/Limited 专用账号或 ACL 不合规\
When 注册或执行 backup-scheduled\
Then 系统 fail fast\
And 返回明确 blocked reason\
And 不把该任务显示为正常

### BDD: 注册 principal 与 ACL identity 一致

Given backend secrets 显式配置 taskPrincipal.principalId，账号具备 batch-logon 且 ACL 只授予必需读写权限\
When registrar 生成或注册任务\
Then task principal 使用相同 identity、LogonType=S4U、RunLevel=Limited\
And principal 缺失、batch-logon 不满足、普通用户可写 secrets 或 identity 不一致时 fail fast\
And 命令/日志不包含账号密码或生产确认文本

### BDD: 计划任务状态异常不被误判正常

Given Windows 计划任务查询失败、任务禁用、NextRunTime=N/A、路径/受保护输入/principal 校验失败、LastTaskResult 非 0、备份点缺失、completedAt 缺失/非法或 now-completedAt 超过 backup.maxFreshnessHours\
When 后端读取自动备份状态\
Then 状态为 配置异常、已关闭或上次失败\
And blocked reason 保留可审计原因\
And 不返回正常

### BDD: 管理员通过现有页面查看自动备份状态

Given 测试租户或授权运维账号具备 system:backup-plan:query 权限\
When 管理员登录并打开 /system/backup-plan\
Then 页面展示当前自动备份计划、下次备份时间、上次备份结果和异常提示\
And 页面不直接展示生产确认、密码、token、私钥或连接串\
And API 响应仅用于最终比对

### BDD: 仓库环境从后端配置传播到注册命令

Given backend backup-ops.config.json 显式配置 backup.repositoryEnvironment=test 或 backup\
When 后端读取或注册备份计划\
Then RepositoryEnvironment 经 service、schedule 和 gateway 传播到注册脚本，并在页面只读显示\
And 缺失或非法值时状态为配置异常且注册失败\
And query-only E2E 不执行任何写操作，传播行为由 config contract、JUnit 和 Pester 验证

## TDD Sequence

### OPS-REQ-001A/001B 计划任务注册与受保护生产确认

Prerequisites:

- Pester 可用。
- 测试使用 TestDrive: 创建 dummy config/secrets，其中受保护字段固定为 auth.productionBackupConfirmText 并提供 dummy principalId；注册合同固定 LogonType=S4U/RunLevel=Limited。值仅为测试标识，不使用真实生产确认值或账号密码。
- ACL 场景验证注册 plan 中的 principal identity 与被验证 ACL identity 相同、principal 可读、普通用户不可写；无法构造该 Windows ACL 前置时本组测试 blocked，不改为跳过。
- Named Pester scenarios: \`registers-the-validated-principal-with-s4u-limited\`, \`blocks-missing-batch-logon-right\`, \`blocks-principal-acl-identity-mismatch\`, \`blocks-ordinary-user-write-access\`, \`never-emits-password-or-confirmation\`。

RED:

- Command: Invoke-Pester -Script .\script\backup-ops\tests\BackupScheduledTaskContract.Tests.ps1
- Working directory: E:\IntRuoyi\IntRuoyiBackend
- Expected failure: 当前实际 Register-BackupOpsScheduledTasks.ps1 -PlanOnly 含明文生产确认，且缺 RepositoryEnvironment、专用 principalId、S4U/Limited、auth.productionBackupConfirmText 受保护读取合同或 masked proof。
- Evidence path: doc/tasks/<implementation-task>/execution-log.md

GREEN:

- Command: Invoke-Pester -Script .\script\backup-ops\tests\BackupScheduledTaskContract.Tests.ps1
- Expected pass: plan-only 输出包含必需合同，且断言不包含生产确认明文、密码、token、私钥或连接串。

Regression:

- Command: Invoke-Pester -Path .\script\backup-ops\tests -EnableExit
- Expected pass: backend source 的计划任务和既有 backup-ops Pester 全部通过。

### OPS-REQ-001E 后端 source of truth 与发布打包

RED:

- Command: python -X utf8 -m pytest script/tests/test_backup_ops_scheduled_task_contract.py script/tests/test_runtime_control_ops_scripts.py -q
- Working directory: E:\IntRuoyi\IntRuoyiBackend
- Expected failure: 实际后端注册脚本仍含明文确认或缺仓库/principal 合同，或 service/runtime path 不指向 backend script/backup-ops。

GREEN:

- Command: python -X utf8 -m pytest script/tests/test_backup_ops_scheduled_task_contract.py script/tests/test_runtime_control_ops_scripts.py -q
- Expected pass: service 和目标脚本 source of truth 一致且无明文确认。

Regression:

- Command: python -X utf8 -m pytest script/tests/test_publish_int_ruoyi_to_test_tooling.py -q
- Expected pass: 发布打包继续从 backend script/backup-ops 取包，且不打包 backup-ops.secrets.json。

### OPS-REQ-001C 后端状态查询与健康判定

Prerequisites:

- JDK/Maven 与 yudao-module-infra 依赖可用。
- \`WindowsBackupPlanSchedulerGatewayTest\` 在 RED 阶段由实施任务先创建；fixture 直接作为 scheduler gateway 单元输入，不作为 E2E 或生产成功证据。

RED:

- Command: mvn -pl yudao-module-infra -am "-Dtest=BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
- Working directory: E:\IntRuoyi\IntRuoyiBackend
- Expected failure: 当前状态模型无法完整表达 health decision table，或 RepositoryEnvironment 无法从 backend config 传播到 registrar/page status。

GREEN:

- Command: mvn -pl yudao-module-infra -am "-Dtest=BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
- Expected pass: 查询失败、禁用、NextRunTime 缺失、上次失败、脚本/config/secrets/principal/ACL 无效、备份点缺失、completedAt 缺失/非法、now-completedAt 超过 maxFreshnessHours 和 RepositoryEnvironment 丢失均产生确定状态与 blocked reason。

Regression:

- Command: python -X utf8 -m pytest script/tests/test_system_backup_plan_menu_sql.py script/tests/test_publish_int_ruoyi_to_test_tooling.py -q
- Working directory: E:\IntRuoyi\IntRuoyiBackend
- Expected pass: 页面菜单、组件、权限和租户包绑定 SQL 合同仍完整。

### OPS-REQ-001D 现有页面只读路径

Prerequisites:

- 静态测试文件已存在；前端依赖安装完成。
- Playwright 当前状态只读 E2E 可按 login-access.md 使用测试租户 tenant_id=122 / aoteman；query-only permission E2E 必须使用测试租户内预先批准、仅绑定 \`system:backup-plan:query\` 且不含 update/execute 的账号。不得在 E2E 中用 API/SQL 创建或改权限；账号缺失时该场景 BLOCKED。
- E2E base URL 固定为 http://localhost:8081。若脚本环境变量允许覆盖，必须显式设置为该值并在日志核对；不得使用脚本隐式 8083 默认。

RED:

- Command: node tests/e2e/system-backup-plan-standard-list-static.spec.js
- Working directory: E:\IntRuoyi\IntRuoyiFronted
- Expected failure: 页面缺少现有入口、API 包装、标准列表、RepositoryEnvironment 只读字段、写控件权限指令或当前状态/blockedReason 展示合同时，静态测试失败；静态测试不作为任何运行态行为证据。

GREEN:

- Command: node tests/e2e/system-backup-plan-standard-list-static.spec.js
- Expected pass: /system/backup-plan 页面、API 包装、状态文案和历史列表合同完整。

Regression:

- Command: pnpm ts:check
- Working directory: E:\IntRuoyi\IntRuoyiFronted
- Expected pass: 前端类型检查通过。

Authorized E2E:

- Command: `$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-real-readonly.e2e.js`
- Working directory: E:\IntRuoyi\IntRuoyiFronted
- Prerequisite: http://localhost:8081 前端/后端运行态可用，测试租户或授权运维账号可登录，且本任务已获准进行只读页面验证。
- Expected pass: Playwright 登录后打开 /system/backup-plan，看到自动备份状态、备份包历史和无秘密泄露；截图写入 E:\IntRuoyi\output\playwright\system-backup-plan-readonly.png。
- Blocked handling: 运行态、账号或授权缺失时记录 BLOCKER: system-backup-plan-real-readonly -> <impact>，不得用 API、stub、文件夹样本或接口脚本替代。

Query-only permission E2E:

- Command: \`$env:SYSTEM_BACKUP_PLAN_E2E_BASE_URL='http://localhost:8081'; node tests/e2e/system-backup-plan-query-only-permission.e2e.js\`
- Working directory: E:\IntRuoyi\IntRuoyiFronted
- Planned test file: tests/e2e/system-backup-plan-query-only-permission.e2e.js
- User path: 仅 query 账号登录 -> 打开页面 -> 验证 status/history 可见 -> 验证保存、启用、停用、立即备份控件在 DOM 中不可见 -> 不点击任何写控件。
- Final API comparison: 只在页面步骤完成后，用同一登录态确认 PUT schedule、POST enable、POST disable、POST backup-now 均返回 403；不得用于设置页面状态。
- Blocked handling: 缺少预先批准的 query-only 账号时记录 BLOCKER，不用 aoteman 全权限账号、API/SQL 改权限或静态匹配冒充。

## E2E User Paths

### E2E-001 备份计划任务状态查看

- 登录测试租户或授权运维账号。
- 从 http://localhost:8081 登录并打开 /system/backup-plan。
- 等待 GET /admin-api/infra/backup-plan/status 和 GET /admin-api/infra/backup-plan/history/page 返回 200。
- 验证页面显示“当前自动备份计划”“自动备份”“下次备份时间”“上次备份结果”“备份包历史”。
- 若 blockedReason 存在，验证页面显示“配置异常”和原因。
- 复核页面正文不包含生产确认明文、密码、token、私钥或连接串。
- 不点击保存计划、开关、立即备份或其它写操作。
- query-only 账号缺 update/execute 权限时，保存/开关/立即备份控件必须隐藏；不可仅以“不点击”或 disabled 代替权限指令验收。
- 不通过 API、SQL、文件样本或 stub 准备页面状态；若无法通过真实前端路径到达该页面或读取真实状态，记录 BLOCKED。

## UI Contract for Retained Behavior

- Existing route/component: \`/system/backup-plan\` / \`E:\IntRuoyi\IntRuoyiFronted\src\views\system\backup-plan\index.vue\`
- Backend endpoint contract: GET /admin-api/infra/backup-plan/status returns scheduler status, schedule, next run, last run/result, latest backup point, principal/command/path validation summary and blocked reason without secrets.
- Existing endpoints also include POST /admin-api/infra/backup-plan/backup-now, PUT schedule, POST enable and POST disable; OPS-NODE-001 E2E is query-only and must not invoke them.
- Permission and dynamic menu: \`system:backup-plan:query\` from \`E:\IntRuoyi\IntRuoyiBackend\sql\mysql\20260725_system_backup_plan_menu.sql\`; target tenant binding must be verified before E2E.
- States to assert dynamically: 当前真实状态、blockedReason（若存在）、秘密缺失；query-only permission behavior 由独立预批准账号场景验证。
- Disabled, last failed, configuration abnormal, empty history and API error require an approved frontend-only real setup path. If the current environment does not naturally expose one, record that state as BLOCKED rather than claiming it via source matching. Permission behavior follows the dedicated query-only account path above.
- Cleanup: read-only E2E creates no business data; any screenshot/log containing credentials or secrets blocks closeout and must be deleted or redacted in the implementation task.

## Test Data

- Pester 在 backend repo 使用 TestDrive: 或临时目录生成 dummy config/secrets/principal；该数据只验证合同，不冒充生产成功。
- 后端 JUnit 使用 fake scheduler output 覆盖 schtasks 本地化输出、空输出、非 0 exit code、禁用、NextRunTime=N/A、脚本路径漂移和上次失败；备份点 fixture 必须显式提供 completedAt，覆盖缺失、非法、阈值内和超阈值。
- 前端静态测试读取现有源文件和 API 包装。
- Playwright 真实页面只用测试租户或授权运维账号；写入型操作必须在测试租户执行，生产只读验证需另行授权。
- 不使用芋道源码租户做写入测试，不修改生产数据。

## Failure Paths

- RepositoryEnvironment 缺失或非法。
- 受保护生产确认输入缺失、不可读、权限不合规或值不匹配。
- plan-only 输出泄露生产确认明文或其它秘密。
- Register-BackupOpsScheduledTasks.ps1 指向错误 backup-ops.ps1。
- schtasks 查询非 0、空输出、任务禁用或 NextRunTime=N/A。
- LastTaskResult 非 0。
- 最近备份点缺失、不可恢复或超过 backup.maxFreshnessHours。
- backup.maxFreshnessHours 缺失、非正数或无 RPO 决策证据。
- 成功备份点 completedAt 缺失、不可解析或 now-completedAt 超阈值。
- 页面无权限、路由 404、API 500、页面不显示 blocked reason。
- Playwright 运行态或登录前置缺失。

## Requirement Traceability

| Requirement | Acceptance | BDD | RED/GREEN | Evidence |
|---|---|---|---|---|
| OPS-REQ-001A | AC-001, AC-002 | BDD-001 | BackupScheduledTaskContract.Tests.ps1 | implementation execution-log |
| OPS-REQ-001B | AC-001, AC-003 | BDD-002 | BackupScheduledTaskContract.Tests.ps1 | implementation execution-log |
| OPS-REQ-001C | AC-002, AC-004 | BDD-003 | BackupPlanServiceImplTest, WindowsBackupPlanSchedulerGatewayTest | Surefire reports |
| OPS-REQ-001D | AC-005 | BDD-004 | system-backup-plan-standard-list-static.spec.js + authorized real readonly E2E | Playwright screenshot/log |
| OPS-REQ-001E | AC-006 | BDD-006 | test_backup_ops_scheduled_task_contract.py + packaging regression | pytest output |
| OPS-REQ-001B | AC-007 | BDD-007 | named principal/ACL Pester scenarios | Pester output |

## Successor Notification Test Contract

- Notification failure tests are out of scope for OPS-NODE-001 implementation commands.
- OPS-NODE-002 must add BDD and automated tests proving a notification delivery failure records delivery status, retry metadata and secondary alert linkage without mutating the primary alert workflow state.

## Verification Evidence Template

- BDD: <scenario name> -> Given/When/Then
- RED: <command> -> FAIL, <expected reason>
- GREEN: <command> -> PASS
- REGRESSION: <command> -> PASS
- E2E: /system/backup-plan -> PASS/BLOCKED with evidence path
- SECURITY: secret redaction check -> PASS
- SCOPE: no production write without explicit authorization -> PASS

## Test Blockers

- TB-001：真实生产计划任务注册、启用和连续运行证明需另行授权。
- TB-002：Playwright 真实页面验证缺少本地/测试运行态或登录账号时 blocked。
- TB-003：受保护生产确认输入方案无法落地时 blocked；不得改为命令行明文。
- TB-004：无法确定 RepositoryEnvironment 时 blocked；不得用隐式默认值。
- TB-005：计划任务专用 principalId、S4U/Limited 或 ACL 安装合同无法满足时 blocked；不得退回当前用户、SYSTEM、最高权限，也不得把账号密码或确认值放入命令行。
- TB-006：backup.maxFreshnessHours 对应 RPO 尚未确认时，生产健康必须为配置异常；不得使用默认阈值。
- TB-007：维护仓与后端脚本副本继续漂移不阻塞本节点，只要所有实际运行、测试和打包均严格使用 backend source；不得混用维护仓 GREEN 证据。
- TB-008：测试租户缺少预先批准的 query-only 账号时，权限 E2E blocked；不得临时用 API/SQL 改权限或用 aoteman 全权限账号冒充。
