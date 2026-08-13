# Reviewer Packet

- Run ID: 20260813T000000Z-opsdocs
- Round: 3
- Workspace: D:/ProjectPackage/Int/IntRuoyiMaintance
- Goal: 复核正式服运维规划包的范围、依赖、验收、测试和跨文档一致性，修订后形成可执行且可验证的单节点计划
- Requires UI Runtime: no

## Instructions

- 只做独立评审，不要修改代码。
- 只从逻辑层、易用性层、UI 层判断是否放行。
- 不要参考主任务的诊断结论，只根据当前代码现状与材料评估。
- 将完整放行单写入 `D:/ProjectPackage/Int/IntRuoyiMaintance/.review-fix-loop/runs/20260813T000000Z-opsdocs/review/report-round-3.md`。

## Task

# Task

- Goal: 复核正式服运维规划包的范围、依赖、验收、测试和跨文档一致性，修订后形成可执行且可验证的单节点计划
- Workspace: D:/ProjectPackage/Int/IntRuoyiMaintance
- Max Rounds: 4
- Requires UI Runtime: no
- Reviewer must judge only from logic, usability, and UI.
- Worker must only implement required changes from reviewer output.

## Review Scope

- `doc/tasks/20260813-production-operations-hardening-plan/prd.md`
- `doc/tasks/20260813-production-operations-hardening-plan/development-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/test-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/task-state.json`
- `doc/tasks/20260813-production-operations-hardening-plan/task.md`
- `doc/tasks/20260813-production-operations-hardening-plan/execution-log.md`

## Evidence Sources

- `doc/tasks/20260813-production-operations-review/verification-report.md`
- `E:/IntRuoyi/docs/release-backup-restore.md`
- Current maintenance repository scripts, tests, configuration, and runtime-control source referenced by the planning package.

## Review Constraints

- Judge whether this is exactly one executable roadmap node rather than a bundle of unrelated initiatives.
- Verify requirement, acceptance, milestone, BDD/TDD, blocker, and machine-state consistency.
- Treat missing business decisions, unavailable dependencies, placeholder commands, secret exposure, unauthorized production actions, mocks, fallback, and silent downgrade as release-gating concerns.
- This is a documentation-only review; UI runtime review is not required. Review UI-related plans only for testability and consistency with current product entry points.

## Current Package Rule

- Review the current files on disk, including the worker edits. Do not rely on the original round-one line numbers or scope.
- The selected node is allowed to plan new tests that will be created during strict TDD; planned files must be named and commands must be exact.
- `ready-for-implementation` means local/test RED work may start. It does not authorize production rollout, server access, or backup execution.


## Previous Worker Result

# Worker Result Round 2

## 修改摘要

- 将所有 backup-ops 候选文件、Pester/pytest 命令和 source-of-truth 回归统一到实际后端仓 \`E:\IntRuoyi\IntRuoyiBackend\script\backup-ops\`，明确维护仓副本不是实现、测试、打包或验收输入，并记录后端/前端各自提交归属。
- 定义计划任务 principal 全链路合同：backend secrets 的 \`taskPrincipal.principalId\`、S4U/Limited、batch-logon、最小权限、ACL identity 一致、普通用户不可写 secrets，以及 named Pester fail-fast 场景；命令不携带账号密码或生产确认。
- 将 RepositoryEnvironment 正式来源固定为 backend \`backup.repositoryEnvironment\`，经 service -> BackupPlanSchedule -> gateway -> registrar 传播并在页面只读展示；缺失/非法不设默认且阻塞。
- 完整化健康判定：覆盖 query exit、enabled、NextRunTime、last result、command/script/config/secrets/principal/ACL、最新成功备份点，以及 manifest \`completedAt\` 与 \`backup.maxFreshnessHours\` 的确定性新鲜度规则。
- 分离规划进度 PLAN-M5 和实施就绪 IMPL-M1，更新 task-state/task/execution-log 一致性。
- 固定前端入口 \`http://localhost:8081\`，补齐 backup-now endpoint；E2E 明确 query-only，不操作任何写控件。新增 planned query-only Playwright 文件、预先批准仅 query 账号前置、写控件隐藏断言和最终 403 权限比对。

## 已验证项

- \`task-state.json\` 使用 UTF-8 解析成功。
- 静态一致性检查覆盖 source of truth、PLAN/IMPL 生命周期、principal/ACL、RepositoryEnvironment 传播、completedAt 新鲜度、UI endpoints/query-only E2E 和精确 backend 命令。
- \`git diff --check\` 用于规划包和 worker 结果，无 whitespace error。

## 未解决项

- 本轮未执行任何生产代码修改、Pester、pytest、Maven、pnpm 或 Playwright；这些是后续实施节点的 RED/GREEN/REGRESSION 命令。
- 正式 principal identity、batch-logon/ACL 安装、RPO 对应 maxFreshnessHours 和正式连续运行证明仍须后续明确授权。
- 测试租户 query-only 账号若尚未预先批准，对应权限 E2E 将按计划记录 BLOCKED。

## 剩余风险

- Windows S4U 是否可满足目标账号与备份资源访问必须在实施 Pester 和后续授权环境验证；失败时必须 blocked，不得改用 current user/SYSTEM/highest 或命令行凭据。
- completedAt 需要由后端备份 manifest/status 链路规范化暴露；在该字段实现并验证前，健康状态不得返回正常。
- 维护仓历史副本继续存在漂移风险，但本节点通过后端运行/打包 source contract 排除其作为放行输入；删除或建立单向生成机制属于独立后续治理范围。

