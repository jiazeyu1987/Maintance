# Query-only 测试账号页面授权变更评估

## Request Summary And Source

- 来源：用户在当前任务中明确授权，可从用户管理选择现有用户；普通用户测试密码由用户提供，所需权限可由管理员赋予。
- 目标：解除 IMPL-M4 因缺少预批准 query-only 账号导致的真实 Playwright 权限验收阻塞。
- 凭据处理：密码只用于当前本机浏览器进程，不写入文档、命令日志、截图、源码或提交。

## Current Baseline Reviewed

- `doc/tasks/20260813-production-operations-hardening-plan/prd.md`
- `doc/tasks/20260813-production-operations-hardening-plan/development-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/test-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/task-state.json`
- `doc/tasks/20260813-production-operations-hardening-plan/test-report.md`
- 当前基线要求 query-only 身份拥有 `system:backup-plan:query`，且不拥有 `system:backup-plan:update`、`system:backup-plan:execute` 或 `*:*:*`；原计划因未获账号配置授权而禁止在验收时改权限。

## Classification

- 类型：测试前置与运维授权范围变更。
- 不属于产品功能、生产发布、正式服务器操作或数据库直接修改。

## Impact Analysis

- Product：不改变产品功能或页面需求。
- Design：不改变备份计划 API、权限码或 UI 设计；若角色菜单树无法通过真实 UI 表达父菜单单独授权，允许复用数据权限页既有模式，为角色菜单权限弹窗补充“父子联动”开关，以支持最小权限配置。
- Data：允许仅通过真实前端在测试租户调整一个现有测试用户的角色，并可创建任务专用最小权限角色；必须记录原角色并在验收后恢复，任务专用角色在不再需要时删除。
- API：不得使用 API 准备账号、角色或权限；API 仍只用于页面验收完成后的最终权限拒绝比对。
- Test：query-only Playwright 从 BLOCKED 转为可执行；必须先验证实时 permission response 精确满足 query-only 合同，再验证页面 DOM 和四个写接口的 `HTTP 200 + JSON code=403`。
- Release：不发布、不操作测试服或正式服，不改变 rollout 阻塞项。
- Operations：只操作本机测试租户；禁止修改芋道源码租户业务数据、正式配置、服务器、计划任务、备份或恢复状态。
- Security：权限授予遵循最小权限；管理员凭据和用户密码不进入持久文件、日志、截图或 Git。

## Decision

- Decision: accept。
- 接受范围：管理员或测试租户全权限管理员通过真实前端完成最小权限角色配置、现有测试用户绑定、query-only E2E、原角色恢复和任务专用角色清理；允许对角色菜单权限弹窗实施有测试覆盖的最小父子联动控制修复。
- 禁止范围：SQL/API 直接改权限、使用全权限账号冒充 query-only、保留未记录的额外权限、操作远端或正式环境。

## Required Approvals

- 用户授权：已在当前任务明确获得。
- 生产环境授权：未获得且本变更不需要；任何正式服操作继续保持禁止。

## Downstream Skill Reruns

- `playwright`：通过真实页面完成测试租户角色/用户配置、query-only 验收与清理。
- `milestone-tdd-delivery`：继续 IMPL-M4 门禁，不扩大到 successor node。
- `independent-verification-gate`：真实 E2E 完成后重新判定 IMPL-M4 PASS/FAIL。

## Blockers And Next Action

- 当前无授权阻塞。
- 下一步：检查本机 8086/48086 运行态；选择低风险现有测试用户；记录其原角色；通过前端赋予任务专用 query-only 角色；运行真实 Playwright；恢复原角色并清理任务专用角色；提交独立复核。
