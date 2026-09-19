# Execution Log

BDD: 已测试包正式晋级 -> Given workflow 为 TESTED 且摘要与测试凭证存在，When 用户点击正式按钮，Then 先返回只读 preview 和结构化 blockers，不产生远端写入。
BDD: 未授权或字段越界 -> Given 用户无专用生产权限或请求含 host/path/releaseTag，When 调用 preview/confirm，Then 服务端拒绝且不创建 operation。
BDD: 写入结果未知 -> Given 授权已消费或 promote 已派发，When 下游失败/中断，Then workflow 进入 RECOVERY_REQUIRED 并保留隔离。

RED: 待实现后端/前端合同命令 -> FAIL, 当前缺少 production-preview API、preview 绑定和专用权限。

GREEN: experience-preflight -> PASS, 任务已在专用 worktree `D:\IntRuoyiWorktree\r260919-prod-button-impl` 执行；本轮禁止 E2E、服务器写入、数据库写入、发布、重启或正式服探测。

GREEN: app-backend-production-button-implementation -> PASS, 新增 production-preview、专用权限 `infra:runtime-control:promote-prod`、preview/stateVersion/artifact digest/test evidence 绑定、授权绑定和幂等 promote 路径。

GREEN: app-backend-no-legacy-prod-promotion -> PASS, 移除旧 `authorizeProduction(workflowId, approver)` 与旧 `startProductionPromotion(..., prodConfirmText)` 兼容入口；`rg` 检查 `prod-preview-legacy` 与 legacy promote overload 无命中。

GREEN: app-backend-generic-promote-prod-blocked -> PASS, 通用 `/actions` 与 `/actions/preview` 收到 `action=promote-prod` 时 fail fast，正式服发布只能走已测试工作流按钮。

GREEN: app-frontend-production-button-implementation -> PASS, 前端新增正式服发布 preview 对话框、专用权限显示、`PROD` 二次确认、`previewId`、`expectedStateVersion` 与 `idempotencyKey` 提交；删除可见旧通用 `promote-prod` 动作入口。

GREEN: maintenance-runtime-contract -> PASS, 维护仓运行控制台后端拒绝旧通用 `promote-prod`，前端删除旧通用正式服动作按钮，防止绕过应用侧已测试工作流按钮。

RED: app-backend-targeted-regression -> FAIL, 去除旧兼容入口后首次回归发现重复点击时 operation store 尚未落盘导致 `RELEASE_WORKFLOW_IDEMPOTENCY_CONFLICT`，以及生产写入开关关闭时测试仍期待授权后阻断。

GREEN: app-backend-targeted-regression -> PASS, `mvn -pl yudao-module-infra -am "-Dtest=ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowOrchestratorTest,RuntimeControlCanonicalContractTest" "-Dsurefire.failIfNoSpecifiedTests=false" test` -> Tests run: 36, Failures: 0, Errors: 0, Skipped: 0; BUILD SUCCESS。

GREEN: app-frontend-static-contract -> PASS, `node src/views/infra/runtime-control/productionPromotionButton.static.spec.cjs` -> `production promotion button static contract: PASS`。

GREEN: app-frontend-typecheck -> PASS, `corepack pnpm ts:check` -> exit 0。

GREEN: app-frontend-production-build -> PASS, `corepack pnpm build:prod` -> `Build successful. Please see dist-prod directory`。

GREEN: maintenance-backend-tests -> PASS, `mvn test` -> Tests run: 26, Failures: 0, Errors: 0, Skipped: 0; BUILD SUCCESS。

GREEN: maintenance-frontend-typecheck -> PASS, `corepack pnpm typecheck` -> exit 0。

GREEN: maintenance-frontend-build -> PASS, `corepack pnpm build` -> built successfully。

GREEN: migration-policy-gate -> PASS, `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --output ...\migration-policy-gate.json` -> status `passed`, migrationCount `620`，包含 `20260919_runtime_control_production_promotion_permission.sql`。

GREEN: diff-check -> PASS, 应用仓与维护仓 `git diff --check` 均 exit 0，仅存在 Git 提示的 LF/CRLF 工作区换行警告。

## Verification Scope
- 本轮不执行 Playwright E2E、远端登录、正式服探测、发布、重启或数据库写入。
