# IMPL-M3 Independent Verification Report

## Current Status

passed

## Scope

- Verification object: IMPL-M3 - RepositoryEnvironment 传播与确定性健康判定。
- Backend cwd: `D:\IntRuoyiWorktree\production-backup-scheduled-task-contract\IntRuoyiBackend`
- Maintenance task package: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260813-production-operations-hardening-plan`
- This tester gate did not modify production code, test code, `execution-log.md`, `task-state.json`, servers, services, backups, restores, releases, or databases.

## Verdict

- PASS: IMPL-M3 satisfies the independent tester gate. 上一轮 fail 项已补强，主线程可以将 IMPL-M3 标记为 completed。

## Command Evidence

| Check | Command | Result |
|---|---|---|
| Maven target | `mvn -pl yudao-module-infra -am "-Dtest=BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest,RuntimeBackupDrillServiceImplTest" "-Dsurefire.failIfNoSpecifiedTests=false" test` | PASS; `BackupPlanServiceImplTest` 17 passed, `WindowsBackupPlanSchedulerGatewayTest` 6 passed, `RuntimeBackupDrillServiceImplTest` 7 passed; total 30 passed; BUILD SUCCESS |
| Pester regression | `Invoke-Pester -Path .\script\backup-ops\tests -EnableExit` | PASS; Passed=9 Failed=0 Skipped=0 |
| pytest contracts | `python -X utf8 -m pytest script/tests/test_backup_ops_scheduled_task_contract.py script/tests/test_runtime_control_ops_scripts.py -q` | PASS; 13 passed |
| diff hygiene | `git diff --check` | PASS; only CRLF working-copy warnings, no whitespace errors |
| static / coverage gate | IMPL-M3 field, branch, and test coverage scan | PASS |

## Static / Coverage Evidence

- implFieldsAndBranches=True
- gatewayDynamicInfrastructure=True
- drillCompletedAtParser=True
- serviceDynamicQueryExit=True
- serviceDynamicDisabled=True
- serviceDynamicMissingNextRun=True
- serviceDynamicLastFailure=True
- serviceDynamicPathDrift=True
- serviceFreshnessBranches=True
- gatewayFakeSchtasks=True
- drillCompletedAtTests=True
- noMaintenanceOpsInput=True

## Coverage Judgment

- RepositoryEnvironment propagation is constrained from config/service schedule through gateway registrar arguments.
- Health decision branches are now dynamically covered for scheduler query failure, disabled task, missing next run time, non-zero last result, task path drift, missing backup point, missing/invalid/stale `completedAt`, and missing `maxFreshnessHours`.
- `WindowsBackupPlanSchedulerGatewayTest` now uses fake command output via `gatewayReturning`, rather than only source-string assertions.
- `RuntimeBackupDrillServiceImplTest` now covers valid manifest `completedAt` parsing and invalid `completedAt` -> null behavior.
- No GREEN evidence uses maintenance `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops` as input.

## Blockers / Gaps

- None for IMPL-M3.

# IMPL-M4 Independent Gate

## Current Status

FAIL

## Scope

- Verification object: IMPL-M4 - 现有 `/system/backup-plan` 页面当前状态与 query-only 权限验收。
- Implementation worktree: `D:\IntRuoyiWorktree\production-backup-scheduled-task-contract`.
- This gate did not modify production code, test code, task state, accounts, permissions, databases, remote services, scheduled tasks, backups, restores, or releases.

## Verdict

- FAIL: 页面实现、状态空值回归和非阻塞自动化检查通过，但 planned query-only E2E 对写接口断言 `HTTP 403`，与当前项目方法级权限拒绝合同 `HTTP 200 + business code 403` 冲突。即使补齐 query-only 凭据，脚本也会在四个写接口比对处失败，不能把 IMPL-M4 仅判定为凭据 BLOCKED。
- BLOCKED evidence remains valid for the real query-only user path: no pre-approved query-only tenant, username, or password is present, so the real permission E2E cannot be executed. `测试租户/aoteman` has a full-permission baseline and cannot replace this account.

## Requirement Traceability

| Requirement / Gate | Artifact / Evidence | Judgment |
|---|---|---|
| OPS-REQ-001D / AC-005 current-state display | `src/views/system/backup-plan/index.vue`, readonly screenshot, status/history business payload evidence | PASS |
| Query-only write controls hidden | `v-if="canUpdateBackupPlan"`, `v-hasPermi`, static contract, planned query-only Playwright | STATIC PASS; real path BLOCKED by missing approved credentials |
| Four write endpoints reject query-only identity | Controller `@PreAuthorize` annotations and planned final API comparison | FAIL: E2E asserts transport HTTP 403, project contract returns HTTP 200 with business code 403 |
| Missing `repositoryEnvironment` diagnostic behavior | `BackupPlanServiceImplTest#getStatusShouldExposeConfigAbnormalWhenRepositoryEnvironmentIsMissing` | PASS |

## Command Evidence

| Check | Command | Result |
|---|---|---|
| Frontend static contract | `node tests/e2e/system-backup-plan-standard-list-static.spec.js` | PASS |
| Readonly E2E syntax | `node --check tests/e2e/system-backup-plan-real-readonly.e2e.js` | PASS |
| Query-only E2E syntax | `node --check tests/e2e/system-backup-plan-query-only-permission.e2e.js` | PASS |
| Frontend type check | `pnpm ts:check` | PASS; exit 0 |
| Backend status regression | `mvn.cmd -pl yudao-module-infra -Dtest=BackupPlanServiceImplTest test` | PASS; 18 tests, 0 failures/errors, BUILD SUCCESS |
| Permission response contract | `mvn.cmd -pl yudao-framework/yudao-spring-boot-starter-web "-Dtest=GlobalExceptionHandlerTest#accessDeniedException_prefersProjectAdviceOverLowerPriorityThirdPartyAdvice" test` | PASS; existing test proves HTTP 200 and response `code=403` |
| Query-only prerequisite | Environment-presence check plus `node tests/e2e/system-backup-plan-query-only-permission.e2e.js` | BLOCKED as designed; all three `SYSTEM_BACKUP_PLAN_QUERY_ONLY_*` inputs absent, script exits 1 before browser launch |
| Local paired runtime | GET `http://127.0.0.1:48086/actuator/health`; GET `http://127.0.0.1:8086/system/backup-plan` | PASS; backend `UP`, frontend HTTP 200 |
| Diff hygiene | `git diff --check` | PASS; only CRLF working-copy warnings, no whitespace errors |

## Defect Evidence

- `IntRuoyiFronted/tests/e2e/system-backup-plan-query-only-permission.e2e.js:117` asserts `response.status() === 403`.
- `IntRuoyiFronted/tests/e2e/system-backup-plan-standard-list-static.spec.js:85` locks the literal `expected HTTP 403` into the static contract.
- `IntRuoyiBackend/yudao-framework/yudao-spring-boot-starter-web/src/test/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandlerTest.java:37` asserts HTTP status OK, while line 38 asserts JSON business code 403 for method-level access denial.
- `BackupPlanController` protects schedule/enable/disable/backup-now with method-level `@PreAuthorize`, so the framework contract above applies to the planned final API comparison.

## Required Correction Before Rerun

- Align the query-only E2E and its static contract with the existing API convention: assert HTTP 200, parse JSON, and assert business `code === 403` for each forbidden write endpoint. Changing global HTTP semantics would have a much larger blast radius and is not justified by IMPL-M4.
- After that correction passes static/type checks, provide a pre-approved test-tenant account containing `system:backup-plan:query` and excluding `system:backup-plan:update`, `system:backup-plan:execute`, and `*:*:*`; inject credentials only through `SYSTEM_BACKUP_PLAN_QUERY_ONLY_TENANT`, `SYSTEM_BACKUP_PLAN_QUERY_ONLY_USERNAME`, and `SYSTEM_BACKUP_PLAN_QUERY_ONLY_PASSWORD`.
- Do not create or alter roles through API/SQL during acceptance, and do not use `aoteman` as query-only evidence.

# IMPL-M4 Independent Gate Round 2

## Current Status

BLOCKED

## Verdict

- The round-1 deterministic defect is resolved. The query-only script now reads complete request headers with `await statusResponse.request().allHeaders()` and validates each forbidden write endpoint using the project's established permission envelope: HTTP 200 plus JSON business `code=403`.
- Frontend static coverage now locks both the full-header requirement and the HTTP/business-code contract. The existing `GlobalExceptionHandlerTest` independently confirms that method-level access denial uses HTTP 200 plus JSON code 403, and `BackupPlanController` protects the four write endpoints with `@PreAuthorize`.
- No remaining deterministic implementation or test defect was found in the round-1 correction.
- Overall gate remains BLOCKED, not PASS: the pre-approved query-only tenant, username, and password are all absent, so the required real Playwright login, DOM permission behavior, and final same-identity write-endpoint comparison cannot be executed. The full-permission `测试租户/aoteman` account is not acceptable evidence.

## Command Evidence

| Check | Command | Result |
|---|---|---|
| Frontend static contract | `node tests/e2e/system-backup-plan-standard-list-static.spec.js` | PASS |
| Query-only E2E syntax | `node --check tests/e2e/system-backup-plan-query-only-permission.e2e.js` | PASS |
| Permission envelope regression | `mvn.cmd -pl yudao-framework/yudao-spring-boot-starter-web "-Dtest=GlobalExceptionHandlerTest#accessDeniedException_prefersProjectAdviceOverLowerPriorityThirdPartyAdvice" test` | PASS; 1 test, 0 failures/errors; verifies HTTP 200 plus JSON code 403 |
| Controller permission mapping | Static inspection of `BackupPlanController` | PASS; schedule/enable/disable require update, backup-now requires execute, status/history require query |
| Query-only prerequisites | Presence check for `SYSTEM_BACKUP_PLAN_QUERY_ONLY_TENANT`, `SYSTEM_BACKUP_PLAN_QUERY_ONLY_USERNAME`, `SYSTEM_BACKUP_PLAN_QUERY_ONLY_PASSWORD` | BLOCKED; all three inputs are absent |
| Diff hygiene | `git diff --check` | PASS; only CRLF working-copy warnings, no whitespace errors |

## Remaining Clearance

- Provide or approve a test-tenant account whose live permission response contains `system:backup-plan:query` and excludes `system:backup-plan:update`, `system:backup-plan:execute`, and `*:*:*`.
- Inject the approved credentials through the three `SYSTEM_BACKUP_PLAN_QUERY_ONLY_*` environment variables and run the real query-only Playwright path against the explicitly selected local frontend URL.
- Do not create or alter the account/role through API or SQL during acceptance, and do not substitute `aoteman`.

# IMPL-M4 Independent Gate Round 3

## Current Status

PASS

## Verdict

- PASS: IMPL-M4 的前端静态/语法/类型门禁、后端定向回归、真实 query-only 用户路径、四个写接口权限封装和测试租户清理均已独立复验通过。
- 最终真实路径使用现有字母数字测试用户，原角色数量为 0；验收后恢复为原角色集合并删除任务专用角色，最终输出为 `PASS lifecycle_ui=true query_e2e=true original_role_count=0 cleanup=true`。
- 本轮未修改产品代码、测试代码、`execution-log.md`、`task-state.json`、`task.md`、数据库、远程环境、正式服、计划任务、备份或恢复；唯一任务文档写入是本报告。

## Requirement Traceability

| Requirement / Gate | Independent Evidence | Judgment |
|---|---|---|
| `/system/backup-plan` 当前状态与历史可读 | query-only 用户真实登录后，status/history 业务响应成功，页面显示当前健康状态、异常原因和备份历史 | PASS |
| query-only 写控件隐藏 | 页面显示“当前账号只有查询权限”，编辑表单和“现在备份一次”按钮均不在 DOM 中 | PASS |
| 权限实时响应最小化 | 含 `system:backup-plan:query`，不含 wildcard、update、execute | PASS |
| 四个写接口拒绝同一身份 | schedule、enable、disable、backup-now 均为 HTTP 200 且 JSON `code=403` | PASS |
| 权限准备与回收 | 管理员仅通过真实前端创建最小角色、分配现有用户、恢复原角色并删除角色 | PASS |
| 秘密与会话清理 | 无 `.playwright-cli`、无任务所属浏览器进程、无残留角色；含可识别账号信息的截图已删除 | PASS |

## Command Evidence

| Check | Command / Path | Result |
|---|---|---|
| Playwright prerequisite | `Get-Command npx` | PASS; `npx` available |
| Role menu static contract | `node tests/e2e/role-management-split-static.spec.js` | PASS |
| Backup plan static contract | `node tests/e2e/system-backup-plan-standard-list-static.spec.js` | PASS |
| E2E syntax | `node --check` for readonly, query-only, and lifecycle scripts | PASS |
| Frontend type check | `pnpm ts:check` | PASS; exit 0 |
| Backend target regression | Maven target for `BackupPlanServiceImplTest,WindowsBackupPlanSchedulerGatewayTest,RuntimeBackupDrillServiceImplTest` | PASS; 31 tests, 0 failures/errors/skips |
| Permission envelope regression | `GlobalExceptionHandlerTest#accessDeniedException_prefersProjectAdviceOverLowerPriorityThirdPartyAdvice` | PASS; 1 test, HTTP 200 + JSON code 403 contract retained |
| Paired runtime | backend `48086 /actuator/health`; frontend `8086 /system/backup-plan` | PASS; backend `UP`, frontend HTTP 200 |
| Real query-only lifecycle | UI-only role creation/menu assignment/user assignment -> query-only Playwright -> UI restore/delete | PASS; lifecycle, E2E, original-role restore, and cleanup all true |
| Diff hygiene | `git diff --check` | PASS; only existing CRLF warnings |
| Session artifact check | exact path/process checks after E2E | PASS; no `.playwright-cli`, no retained query-only screenshot, no task-owned Playwright browser process |

## Permission Matrix

| Endpoint | Required Permission | Query-only Result |
|---|---|---|
| `PUT /admin-api/infra/backup-plan/schedule` | `system:backup-plan:update` | HTTP 200, JSON `code=403` |
| `POST /admin-api/infra/backup-plan/enable` | `system:backup-plan:update` | HTTP 200, JSON `code=403` |
| `POST /admin-api/infra/backup-plan/disable` | `system:backup-plan:update` | HTTP 200, JSON `code=403` |
| `POST /admin-api/infra/backup-plan/backup-now` | `system:backup-plan:execute` | HTTP 200, JSON `code=403` |

## Real UI And Cleanup Evidence

- 管理员通过本机测试租户真实登录页进入角色管理，创建任务专用角色，关闭父子联动，只选择“备份计划”父节点；两个写权限子节点保持未选中。
- 通过用户管理真实页面选择可登录的字母数字现有用户，记录其原角色集合后仅绑定任务专用角色；未使用 API 或 SQL 准备权限。
- query-only 用户通过真实登录页进入 `/system/backup-plan`；读取状态和历史、验证写控件不存在后，才使用相同登录态执行四个写接口最终权限比对。
- 最终运行将用户恢复为原始空角色集合，重新打开分配角色弹窗验证一致，并通过角色管理真实页面删除任务专用角色、搜索确认不存在。
- 一次临时 helper 直跑因消息框“确定”按钮空格定位不一致而留下 1 个未分配临时角色；UI 审计确认 16 个候选用户中 0 个仍绑定该角色后，通过真实页面删除。最终复跑使用仅驻留进程内存的定位修正，未修改 helper、产品或测试文件，并完整通过恢复/删除断言。

## Runtime And Security Notes

- 初始 `8086` 虽返回 HTTP 200，但启动模式导致浏览器 API 前缀为 `/undefined`，租户识别失败；仅检查静态页面 HTTP 200 不能证明前后端成对可用。停止经路径核对的任务所属前端进程后，以 `vite --mode dev`、slot 5 端口和 `48086` 代理恢复本机运行态，真实登录随后通过。该调整未修改配置或源码。
- 临时 lifecycle helper 还假设角色选择器可输入且角色表单项正文精确等于“角色”；当前 UI 中选择器为只读且已选角色会扩展正文。最终验收只在进程内修正这些 tester locator；该未跟踪 helper 不作为产品交付物，应在 closeout 清理。
- 凭据通过关闭终端回显的短时进程内存通道注入；没有进入命令行、文件、命令输出、报告或保留截图。query-only 截图因顶部存在可识别账号展示而删除，DOM、网络响应和清理断言作为本轮证据。

## Remaining Risk

- 正式服计划任务 principal、RPO 数值、注册、启用和连续运行证明仍需后续明确授权，属于既有 rollout blocker，不阻塞 IMPL-M4 本地/测试环境完成。
- 本机计划任务与 backup repository 配置当前仍可自然显示“配置异常”；本轮验证的是异常可诊断和最小权限只读行为，没有修改或伪造该状态。
