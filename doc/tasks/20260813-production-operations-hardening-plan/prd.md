# 正式自动备份计划任务契约 PRD

## Purpose and Scope

本 PRD 将原“正式服运维能力补齐规划”收敛为一个可独立实施、可测试、可复审的路线节点：修复并证明正式服自动备份计划任务的注册命令、非交互生产授权、备份仓库选择和状态检查契约。

本节点只覆盖 Windows 计划任务 IntRuoyi Backup Scheduled 的注册与健康判定链路。外部通知、备份可恢复性看板扩展、独立外部监控、事件闭环、可观测性、镜像版本治理、PITR、只读分析和月报均转入后续节点，不作为本节点完成条件。

本规划任务不执行正式服操作、备份、恢复、发布、重启、数据库写入或远端探测；真实生产注册与运行证明必须在后续明确授权的实施/发布任务中执行。

## Evidence Reviewed

- doc/tasks/20260813-production-operations-review/verification-report.md
- E:\IntRuoyi\docs\release-backup-restore.md
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\actions\Register-BackupOpsScheduledTasks.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\scripts\backup-ops.ps1
- E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\tests
- E:\IntRuoyi\IntRuoyiBackend\script\tests\test_runtime_control_ops_scripts.py
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\backupplan
- E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\test\java\cn\iocoder\yudao\module\infra\service\backupplan\BackupPlanServiceImplTest.java
- E:\IntRuoyi\IntRuoyiFronted\src\views\system\backup-plan\index.vue
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-standard-list-static.spec.js
- E:\IntRuoyi\IntRuoyiFronted\tests\e2e\system-backup-plan-real-readonly.e2e.js
- E:\IntRuoyi\IntRuoyiBackend\sql\mysql\20260725_system_backup_plan_menu.sql

## Product Summary

当前证据显示，正式备份主入口对 backup-now / backup-scheduled + TargetEnvironment=prod 已强制要求生产确认和显式 RepositoryEnvironment；实际后端注册脚本虽然传入 TargetEnvironment=prod，却把生产确认明文写入计划任务命令，并且没有传递 RepositoryEnvironment，也没有固定专用 principal/ACL 合同。这意味着当前计划任务既存在秘密暴露风险，又无法满足主入口参数合同，不能把“每日 01:30 配置存在”视为自动备份真实可运行。

本节点交付后，运维人员应能通过计划任务 plan-only、后端状态接口和现有 /system/backup-plan 页面确认：任务命令目标明确、备份仓库明确、生产授权来自受保护输入且不泄露、脚本路径正确、计划任务可查询、下次运行/上次运行/上次结果可读、异常原因不会被包装成“正常”。

## Target Users

- 运维负责人：确认正式自动备份计划任务是否真实可运行。
- 发布负责人：在正式发布或维护窗口前确认自动备份状态不是伪正常。
- 开发负责人：按明确合同修复脚本、后端状态和页面只读展示。
- 审计/复核人员：查看命令摘要、状态字段和测试证据，确认未泄露生产秘密。

## First Version Scope

### OPS-NODE-001 正式自动备份计划任务契约

Priority: P0

正式备份计划任务注册与状态检查必须形成一个可验证合同，确保计划任务不会因缺少生产确认、缺少仓库环境、脚本路径漂移或查询失败而被误判为正常。

In Scope:

- Register-BackupOpsScheduledTasks.ps1 的 plan-only 输出必须展示脱敏后的完整命令摘要。
- 本节点唯一脚本 source of truth 为 E:\IntRuoyi\IntRuoyiBackend\script\backup-ops；后端运行入口和发布打包必须引用该目录。维护仓 ops/backup-ops 只视为历史副本，不在本节点修改或作为 GREEN 证据；若继续保留，必须由独立后续治理任务决定删除或建立单向生成机制。
- 计划任务注册必须显式传递 TargetEnvironment=prod 和 RepositoryEnvironment=<test|backup>。
- RepositoryEnvironment 必须是 backend backup-ops.config.json 中显式必填的 backup.repositoryEnvironment（test 或 backup），由 BackupPlanServiceImpl 读取并经 BackupPlanSchedule、WindowsBackupPlanSchedulerGateway 和注册脚本传播；/system/backup-plan 当前节点只读展示选择结果，不新增页面写入控件，也不设默认值。
- 非交互生产确认必须来自 backend script/backup-ops/config/backup-ops.secrets.json 的 auth.productionBackupConfirmText；计划任务命令、plan-only 输出、日志、报告和任务文档不得包含生产确认明文。
- 计划任务 principal 必须使用 backend \`backup-ops.secrets.json\` 显式提供的专用服务账号 \`taskPrincipal.principalId\`，固定 LogonType=S4U、RunLevel=Limited；不得使用当前交互用户、SYSTEM 或最高权限作为隐式默认。该账号必须具备 Log on as a batch job、禁止交互登录，仅授予运行脚本、读取 config/secrets 和写任务日志/备份临时目录所需权限。S4U 注册不接收账号密码；账号密码和确认文本均不得进入命令、JSON、plan-only 输出或日志。注册前必须验证该 principal 可读脚本/config/secrets、可写任务目录，且普通交互用户不可写 secrets。
- backup-ops.ps1 必须保留正式备份 fail-fast 校验；受保护输入缺失、读取失败、值不匹配或权限不合规时必须失败。
- 后端状态检查必须读取并返回计划任务查询退出码、启用状态、NextRunTime、LastRunTime、LastTaskResult/Last Result、Task To Run 脚本路径校验、配置路径和 blocked reason。
- “最新成功备份点”以 manifest 中新增/规范化的 \`completedAt\` 为准，不能用 \`lastVerifiedAt\` 或 backupId 推算。新鲜度条件固定为 \`now - completedAt <= backup.maxFreshnessHours\`；completedAt 缺失/不可解析、没有成功点、阈值缺失/非法或超过阈值均为配置异常。
- 现有 /system/backup-plan 页面只做只读状态验收，不新增路线、菜单或权限。

Acceptance:

- AC-001：plan-only 命令摘要包含 -Mode backup-scheduled、-TargetEnvironment prod、-RepositoryEnvironment <test|backup>、-NonInteractive 和生产授权的 masked proof，且不包含确认明文、密码、token、私钥或连接串。
- AC-002：缺少仓库环境、受保护确认输入、计划任务 principal/logonType、脚本文件、配置文件或凭据文件时，注册/启用失败并返回明确 blocked reason，不注册或保留一个必然失败但显示正常的任务。
- AC-003：生产确认输入读取失败、值不匹配或权限不符合要求时，backup-scheduled fail fast，且错误被状态接口和页面配置异常提示暴露。
- AC-004：后端状态接口按 Health Decision Table 区分查询失败、任务禁用、脚本路径漂移、配置/凭据/受保护输入无效、principal/ACL 不一致、上次失败、下次运行时间缺失、最近备份点缺失或超过配置的新鲜度阈值；任一关键字段缺失时不得返回“正常”。
- AC-005：现有 /system/backup-plan 页面通过真实登录路径显示当前实际状态和 blocked reason；query-only E2E 只验收当前可达只读状态，不能稳定构造的其它状态必须记录为后续 E2E blocker，API 只用于最终比对。
- AC-006：后端脚本 source-of-truth 合同测试证明 BackupPlanServiceImpl 和发布打包均引用 E:\IntRuoyi\IntRuoyiBackend\script\backup-ops，目标注册脚本不含明文生产确认且不存在用维护仓测试结果替代后端脚本的路径。
- AC-007：注册计划中的 principalId、S4U/Limited 与 ACL 验证 identity 完全一致；principal 缺失、没有 batch-logon 前置、读/写权限不满足或普通交互用户可写 secrets 时，注册 fail fast。

## Selected Node Definition of Done

- 本节点完成仅表示 OPS-NODE-001 的脚本合同、后端状态合同、现有页面只读合同和本地/测试环境验证证据完成。
- 本节点不以外部通知、监控、PITR、分析、月报或真实正式服连续运行证明作为完成条件。
- 进入实施时必须先记录 RED 证据；所有 GREEN/REGRESSION 命令必须使用 test-plan.md 中的精确命令和工作目录。
- 若受保护确认输入、RepositoryEnvironment、现有页面入口或测试租户权限任一项无法按下表清除，实施任务必须标记 blocked，不得以默认值、stub、API 绕过或 mock 成功替代。

## Dependency Clearance Contracts

| Dependency | Owner | Required Artifact/Input | Validation Method | State Transition | Evidence Location |
|---|---|---|---|---|---|
| 后端脚本 source of truth | 后端实施 owner | E:\IntRuoyi\IntRuoyiBackend\script\backup-ops 为唯一修改、测试和发布输入；维护仓副本不作为运行源 | Pester 在 backend script/backup-ops/tests 运行；pytest 静态合同验证 service/release packager 路径且扫描明文确认 | 任一运行/打包路径指向维护仓或目标脚本仍含明文时节点 blocked | implementation task execution-log.md + pytest/Pester output |
| 计划任务 principal 与受保护确认 | 实施任务 owner / 运维负责人复核 | backend secrets 显式提供 \`taskPrincipal.principalId\` 与 \`auth.productionBackupConfirmText\`；registrar 固定 S4U/Limited；专用账号具备 batch logon、最小权限且普通用户不可写 secrets | Pester 断言 plan principal identity 等于 ACL identity，覆盖 batch-logon/ACL/masked proof/缺失/不匹配 fail fast；授权 rollout 用 Get-ScheduledTask/Get-Acl 核对 | principal、S4U/Limited、batch-logon 或 ACL 前置无法满足时当前实施任务 blocked | implementation task execution-log.md + Pester output |
| RepositoryEnvironment 传播 | 运维负责人 | backend backup-ops.config.json 必填 backup.repositoryEnvironment=test 或 backup，经 service -> BackupPlanSchedule -> gateway -> registrar 传播；页面只读展示 | JUnit/Pester/前端静态合同验证缺失/非法 fail fast、完整传播和只读显示；query-only E2E 不写配置 | IMPL-M1-M3 可执行；任一层丢值或使用默认时 blocked | implementation task execution-log.md |
| 现有页面入口与权限 | 前端/后端实施 owner | \`/system/backup-plan\` route、component、API、permission 与菜单 SQL | 静态测试 + 授权 Playwright 只读 E2E；API 仅最终比对 | M4 ready；入口或权限缺失且新增入口不在 scope 时 M4 blocked | frontend test output + Playwright screenshot/log |
| 正式服注册与连续运行证明 | 用户明确授权 / 运维负责人 | 单独授权任务、受保护确认输入已安装、release/backup docs 已复读 | 后续任务按 \`release-backup-restore.md\` 和 \`server-access.md\` 执行真实验证 | 不阻塞本节点本地实现；阻塞 rollout proof | successor authorized task evidence |

## Non-Goals

- 不在本节点选择或实现外部通知渠道。
- 不扩展备份可恢复性看板，不改变恢复候选状态机。
- 不新增独立外部监控节点、Prometheus/Grafana、集中日志或 Alertmanager。
- 不修改告警/事件闭环；后续通知节点必须把告警生命周期与通知投递状态分离。
- 不固定第三方镜像版本，不实现发布预检镜像治理。
- 不实现 MySQL PITR。
- 不建设只读分析数据集、指标目录或月度运维报告。
- 不执行正式服计划任务注册、备份、恢复或演练。

## Functional Requirements

| ID | Requirement | Priority | Depends On | Acceptance |
|---|---|---|---|---|
| OPS-REQ-001A | 计划任务注册参数合同 | P0 | 后端 script/backup-ops source of truth | AC-001, AC-002, AC-006 |
| OPS-REQ-001B | 受保护生产确认输入与 principal | P0 | 已冻结的 \`auth.productionBackupConfirmText\` / \`taskPrincipal.principalId\` 合同 | AC-001, AC-003, AC-007 |
| OPS-REQ-001C | 状态查询与健康判定 | P0 | Windows schtasks 输出解析 | AC-002, AC-004 |
| OPS-REQ-001D | 现有页面与 RepositoryEnvironment 传播合同 | P0 | /system/backup-plan 已有页面与权限 | AC-005 |
| OPS-REQ-001E | 后端运行/打包 source-of-truth 合同 | P0 | backend service 与 release packager | AC-006 |

## BDD Scenarios

- BDD-001：注册正式自动备份计划任务时，plan-only 输出包含目标环境、仓库环境和 masked production authorization proof。
- BDD-002：生产确认受保护输入缺失或不匹配时，注册或执行失败并暴露 blocked reason。
- BDD-003：计划任务查询失败、禁用、脚本路径漂移或上次失败时，状态接口不得返回“正常”。
- BDD-004：管理员通过 /system/backup-plan 页面查看计划任务状态时，页面显示状态和配置异常原因。
- BDD-005：显式配置的 RepositoryEnvironment 从 backend config 传播到实际注册命令并在页面只读显示，缺失或非法值时失败。
- BDD-006：后端运行和发布打包只使用后端 script/backup-ops，且实际注册脚本没有明文生产确认。
- BDD-007：注册计划中的 principalId 与 ACL 检查身份相同且固定 S4U/Limited；缺少 batch-logon 或最小权限时不创建/更新任务。

完整 Given/When/Then 与 RED/GREEN 映射见 test-plan.md。

## Business Rules

- 正式自动备份必须显式声明 TargetEnvironment=prod 和 RepositoryEnvironment，不得依赖隐式默认仓库。
- 生产确认值不得出现在计划任务命令行、plan-only 输出、日志、报告、任务文档或测试证据中。
- 受保护生产确认输入不是 fallback；它是非交互计划任务的正式授权来源。缺失、读取失败或不匹配时必须 fail fast。
- LastTaskResult=0 不能单独证明自动备份正常；还必须核对任务启用、下次运行时间、脚本路径、配置路径和最近备份点证据。
- 页面可使用白话状态，但后端必须保留足够 blocked reason 供审计和排障。
- 未经授权不得在本节点执行真实正式服计划任务注册、备份、恢复或远端状态写入。

## States and Transitions

Scheduled Backup Task Health:

- NOT_REGISTERED -> REGISTERED_DISABLED -> ENABLED_WAITING -> RUNNING -> LAST_SUCCESS
- ENABLED_WAITING -> BLOCKED when NextRunTime is missing, script path drifts, protected confirmation is missing, or repository environment is missing
- RUNNING -> LAST_FAILED when last result is non-zero
- Any -> QUERY_FAILED when schtasks exits non-zero or returns empty output

## Health Decision Table

| Condition | Health Status | Required blockedReason |
|---|---|---|
| schtasks exit non-zero or empty/unparseable output | 配置异常 | 查询退出码或解析失败摘要 |
| task disabled | 已关闭 | 任务禁用 |
| NextRunTime missing/N/A | 配置异常 | 缺少下次运行时间 |
| LastTaskResult non-zero | 上次失败 | 上次结果码 |
| Task To Run is not backend script/backup-ops/scripts/backup-ops.ps1 | 配置异常 | 实际与期望脚本路径 |
| config/secrets/protected input missing, unreadable, invalid, or principal/ACL mismatch | 配置异常 | 失败字段，不包含秘密值 |
| latest backup point missing | 配置异常 | 最近备份点缺失 |
| latest successful backup \`completedAt\` missing/unparseable | 配置异常 | 成功备份完成时间缺失或非法 |
| \`now - completedAt > backup.maxFreshnessHours\` | 配置异常 | completedAt、实际年龄与阈值 |
| all checks pass | 正常 | empty |

backup.maxFreshnessHours 是本节点新增的显式正整数配置，必须由运维负责人按已确认 RPO 设置；未配置、非正数或 RPO 未确认时健康状态为配置异常，不使用默认阈值。

Protected Production Authorization:

- MISSING -> PRESENT_MASKED -> VALIDATED
- Any -> BLOCKED when source is unreadable, value mismatches the required confirmation, permissions are invalid, or output would disclose the value

Alert/Notification:

- Out of scope for this node. Successor notification node must keep alert workflow state separate from notification delivery attempts, retry status, and secondary alert linkage.

## Edge Cases

- schtasks query exits non-zero but writes a localized error message.
- Next Run Time is N/A even though the task is enabled.
- Task To Run points to an old backup-ops.ps1 path.
- Plan-only output includes a real confirmation value by mistake.
- Secrets/config path exists but cannot be read under the scheduled-task account.
- RepositoryEnvironment is missing, invalid, or implicit.
- Last result code is zero but there is no recent backup point.
- Latest successful backup exists but exceeds backup.maxFreshnessHours.
- Existing page hides technical paths, so API/log evidence must carry detailed blocked reason.

## Acceptance Criteria

- AC-001：计划任务 plan-only 合同完整且脱敏。
- AC-002：缺必需参数、文件或受保护输入时 fail fast，不注册伪正常任务。
- AC-003：正式备份生产确认校验保留，非交互受保护输入校验失败时可追踪。
- AC-004：状态接口不把查询失败、禁用、脚本漂移、上次失败或证据缺失判为正常。
- AC-005：现有 /system/backup-plan 页面通过真实用户路径展示状态和异常。
- AC-006：实际后端运行/打包脚本与测试 source of truth 一致，且无明文生产确认路径。
- AC-007：注册 principal、S4U/Limited、batch-logon 与 ACL identity 合同一致，权限不满足时 fail fast。

## Successor Backlog

| Successor Node | Dependency | Entry Decision |
|---|---|---|
| OPS-NODE-002 外部通知通道 | OPS-NODE-001 | 通知渠道、测试 webhook/mailbox、责任人和凭据管理方案；告警生命周期必须独立于 notificationDelivery.status、attempts、retryAfter 和 secondaryAlertId |
| OPS-NODE-003 备份可恢复性看板 | OPS-NODE-001 | 备份仓库读取权限与恢复候选状态机确认 |
| OPS-NODE-004 独立外部监控节点 | OPS-NODE-002 | 部署位置、网络策略、探针目标和告警升级链 |
| OPS-NODE-005 可观测性与镜像治理 | 发布预检范围确认 | 镜像批准策略、监控采集端和管理网络边界 |
| OPS-NODE-006 PITR | RPO 决策 | RPO、binlog 保留、加密/权限和恢复负责人 |
| OPS-NODE-007 只读分析与月报 | 只读数据源确认 | 指标负责人、租户边界、刷新机制和报告收件人 |

## Open Questions

- OQ-001：真实生产注册验证由哪个后续授权任务执行，证据保存到哪个任务目录？
- OQ-002：运维负责人确认的 backup.maxFreshnessHours 数值和对应 RPO 决策证据是什么？未确认前实现可完成，但健康状态必须显示配置异常。
- OQ-003：正式环境专用计划任务 principalId/logonType 和受保护凭据安装方式是什么？未确认前本地合同可实现，生产 rollout blocked。

## Successor Notification Contract

- 后续通知节点不得把 \`NOTIFICATION_FAILED\` 建模为告警生命周期状态。
- 告警生命周期仅包含 OPEN、ACKNOWLEDGED、IN_PROGRESS、RESOLVED、CLOSED 等处理状态。
- 通知投递必须使用独立模型记录 delivery status、attempt count、retry schedule、last error 和 secondary alert linkage。
- 后续节点必须新增 BDD：通知投递失败时主告警仍保持原 workflow state，并记录可重试投递失败证据。

## Product Blockers

- PB-001：无阻塞本节点本地实现和测试的业务决策。
- PB-002：真实正式服注册、启用和连续运行证明需要另行授权；未授权前只能完成本地/测试环境合同验证。
