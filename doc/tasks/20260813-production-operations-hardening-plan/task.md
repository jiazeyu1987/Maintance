# 正式自动备份计划任务契约实施

## Task Goal

基于 20260813-production-operations-review 的正式服运维现状评估，将原来过大的“正式服运维能力补齐规划”优化并实施为一个可执行、可测试、可复审的单节点：正式自动备份计划任务注册与健康合同。

规划阶段已完成并通过独立复审；用户于 2026-08-14 要求继续后，按既有 implementationNode 执行 IMPL-M1 至 IMPL-M4。本节点允许修改隔离 worktree 内的后端 source-of-truth、相关后端服务、前端页面和测试，但不操作正式服务器、数据库或远端运行环境。

## Scope

- 生成并优化单节点 PRD、开发计划、测试计划和机器可读任务状态，并按计划实施 OPS-NODE-001。
- Selected node: OPS-NODE-001 正式自动备份计划任务契约。
- 实施唯一 source of truth：E:\IntRuoyi\IntRuoyiBackend\script\backup-ops；维护仓 ops/backup-ops 不作为本节点修改、测试、打包或验收输入。
- 覆盖计划任务注册参数、受保护生产确认输入、显式备份仓库、后端状态查询、现有 /system/backup-plan 页面只读验收。
- 建立需求、验收标准、BDD/TDD、E2E 和证据路径的追踪关系。

## Non-Scope

- 不操作正式服务器、正式配置、数据库或远端运行环境；本地实现仅在任务隔离 worktree 中进行。
- 不注册计划任务，不执行备份、恢复、发布、重启、故障注入或远端探测。
- 不实现外部通知、备份可恢复性看板扩展、独立外部监控、事件闭环、可观测性、镜像治理、PITR、只读分析或月报。
- 不替业务决定 RTO、RPO、SLO、通知渠道、负责人、监控部署位置或分析数据源。
- 不在任何文档、命令、日志或报告中写入生产确认明文、密码、token、私钥或连接串。
- 不把 successor backlog 的未决策项作为 OPS-NODE-001 的完成条件。

## Milestones

- [completed] PLAN-M1：读取适用技能、既有评估和当前系统证据，识别原规划包的问题。
- [completed] PLAN-M2：完成第一轮独立审查，确认原规划包范围过大、状态不一致、测试占位和 UI/E2E 合同缺口。
- [completed] PLAN-M3：将 PRD、开发计划、测试计划和 task-state 收敛为 OPS-NODE-001 单节点。
- [completed] PLAN-M4：完成第二轮独立复审，识别实际脚本 source-of-truth、principal/ACL、RepositoryEnvironment 传播、健康判定和 E2E 合同缺口。
- [completed] PLAN-M5：按第二轮审查单修订并通过第三轮独立复审。
- [completed] PLAN-M6：更新收尾记录并标记完成。
- [completed] IMPL-M1：在隔离 worktree 中为后端 source-of-truth、计划任务 principal 和受保护生产确认建立失败合同测试；独立复核确认 RED 有效。
- [completed] IMPL-M2：实现注册脚本、principal、仓库环境和受保护确认合同 GREEN。
- [completed] IMPL-M3：实现 RepositoryEnvironment 传播与确定性健康判定。
- [completed] IMPL-M4：现有页面当前状态、缺配置异常回归、最小菜单授权和 query-only 真实 E2E 已完成；独立 tester 已确认四个写接口权限封装、原角色恢复、任务专用角色删除和敏感临时产物清理均通过。

## Expected Verification

- PRD 只保留 OPS-NODE-001，其它运维能力进入 successor backlog。
- 开发计划可从需求 ID 追踪到里程碑、代码/配置影响范围、TDD 顺序和完成门禁。
- 测试计划可从需求 ID 追踪到 BDD 场景、精确 RED/GREEN 命令、真实页面路径和证据要求。
- task-state.json 与 task.md、PRD、开发计划和测试计划对同一 selected node、phase、milestone、blocker 和 successor backlog 表述一致。
- 不虚构已确定的 RTO、RPO、SLO、通知渠道、负责人、监控部署位置或生产流量。
- 不引入 fallback、静默降级、mock 成功或自动修改生产数据的设计。
- review-fix-loop 最终复审为 pass。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；将过大的项目级规划拆成一个可实施节点，并把未决业务/环境依赖转入 successor backlog。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 发布、备份、恢复和服务器容量设计以 E:\IntRuoyi\docs\release-backup-restore.md 为准，正式环境访问以 E:\IntRuoyi\docs\server-access.md 为准。
- 正式服备份计划任务状态不能只看计划存在、历史备份包或 LastTaskResult=0；必须同时核对查询退出码、Enabled/Status、NextRunTime、LastTaskResult、Task To Run、脚本存在、配置路径和成功备份证据。
- 最新成功备份点以 manifest completedAt 为唯一新鲜度时间，按 now-completedAt 与已批准 backup.maxFreshnessHours 比较；不得用 lastVerifiedAt 或 backupId 推算。
- 计划任务 principal 来源固定为 backend secrets taskPrincipal.principalId，注册使用 S4U/Limited 并要求 batch-logon 与 ACL identity 一致；不得退回当前用户、SYSTEM 或最高权限。
- 备份就绪必须以真实恢复证据判定；存在计划、备份文件或成功日志不能单独证明可恢复。
- 未由业务确认的 RTO、RPO、SLO、告警通道、责任人、监控部署位置和数据口径不得写成已批准默认值。
- 高风险验证必须先记录 GREEN: experience-preflight -> PASS，并在独立测试环境或备用服隔离 rehearsal 中执行；未经授权不得操作正式服。
- 中文文档使用 UTF-8 无 BOM；请求与命令记录必须脱敏。

## Current Status

completed

规划任务和 OPS-NODE-001 的 IMPL-M1 至 IMPL-M4 均已完成独立复核、实现提交、`int_main` 融合验证与任务清理。实现提交已进入 `int_main`，当前融合基线完成 30 模块后端构建、定向回归、脚本合同和前端类型门禁；任务 helper、Git worktree 注册、物理目录及 8086/48086 运行态均已清理。正式服 rollout 仍需后续明确授权。

## Planning Artifacts

- PRD：doc/tasks/20260813-production-operations-hardening-plan/prd.md
- 开发计划：doc/tasks/20260813-production-operations-hardening-plan/development-plan.md
- 测试计划：doc/tasks/20260813-production-operations-hardening-plan/test-plan.md
- 任务状态：doc/tasks/20260813-production-operations-hardening-plan/task-state.json

## Blockers

- 本地/测试环境实现、验收、融合和收尾无剩余 blocker。
- 正式服计划任务注册、启用和连续运行证明需要另行明确授权。
- 正式环境 principalId/logonType、受保护凭据安装方式和 backup.maxFreshnessHours 对应 RPO 数值未确认，阻塞 rollout，不阻塞本地合同实现。
- 后续若重新执行 query-only 权限 E2E，仍必须通过真实前端准备并恢复最小权限身份；不得用 API/SQL 临时改权限或用全权限账号冒充。
- 外部通知、独立监控、PITR、只读分析和月报的业务/环境决策阻塞对应后续节点，不阻塞本节点规划包。

## Completion Meaning

- 本任务完成表示 OPS-NODE-001 的脚本、后端状态和现有页面只读合同已在本地/测试环境实现、融合并通过独立验证。
- 本任务完成不表示正式服计划任务已经注册、启用或取得连续运行证明。
- 正式服 rollout 必须在后续明确授权任务中完成，不能用本规划任务状态替代。

## Cleanup Keep

- doc/tasks/20260813-production-operations-hardening-plan/prd.md
- doc/tasks/20260813-production-operations-hardening-plan/development-plan.md
- doc/tasks/20260813-production-operations-hardening-plan/test-plan.md
- doc/tasks/20260813-production-operations-hardening-plan/task-state.json
- doc/tasks/20260813-production-operations-hardening-plan/test-report.md
- doc/tasks/20260813-production-operations-hardening-plan/verification-report.md
