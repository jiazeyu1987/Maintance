GREEN: experience-preflight -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`，确认本轮只允许执行 `build-release -> publish-test -> 测试服运行态验证`，不推进 `mark-tested`、正式服或备份服。

BDD: 默认发布只允许明确的主分支输入 -> Given 用户要求构建并发布到测试服务器 When 三仓主工作区存在未提交改动 Then 先阻塞并请用户选择“先提交主工作区”或“仅发布已提交 git 版本”的正式方案，未经确认不得继续真实发布。

BDD: 测试服运行态必须落到同一 releaseTag -> Given 发布输入已满足仓库门禁且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health 与 frontend HTTP 必须全部与同一 `releaseTag` 一致。

GREEN: previous-task-check -> PASS，已核对上一维护仓发布任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-main-branch-test-server-release-closure\task.md` 状态为 `COMPLETED`，允许开启本轮新任务。

GREEN: repo-status-check -> PASS，已分别核对三仓当前状态：
- 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance`：`master`，存在 `AGENTS.md`、`docs/request-command-log.md` 等已跟踪改动，且存在多个未跟踪任务目录与脚本目录。
- 后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`：`int_main`，存在 showroom、srm、SQL、测试等已跟踪改动，且存在多个未跟踪任务目录与新 Java/测试文件。
- 前端仓 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`：`int_main`，存在 `feedback`、`scheduleorder`、`UserSelectV2`、E2E 等已跟踪改动，且存在多个未跟踪任务目录与测试文件。

BLOCKER: publish-input-dirty-main-workspaces -> 当前三仓主工作区均不满足“默认只发布主分支当前版本”的 clean 门禁。根据 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`，必须先由用户明确选择“先提交主工作区后再发布”或“仅发布已提交 git 版本并切 clean worktree”，否则不得继续真实 `build-release`。

GREEN: user-choice-confirmed -> PASS，用户已明确选择方案 `1`，即“先提交再发布”；本轮后续动作改为先收口并提交三仓主工作区，再以这些新提交作为真实发布输入。

GREEN: dirty-change-triage -> PASS，已完成当前脏改归类：
- 维护仓：本轮仅保留 `docs/request-command-log.md` 与当前发布任务台账。
- 后端仓：当前变更可归属到 `showroom-product-excel-audio-keyword-roundtrip`、`srm-nas-locator-blacklist-srm-admin-binding`、`srm-nas-locator-wildcard-search-error`、`local-admin-api-48081-connection-refused`。
- 前端仓：当前变更可归属到 `showroom-product-excel-audio-keyword-roundtrip`、`zhaojie-feedback-attribution-permission-fix`、`zhaojie-feedback-attribution-success-permission-toast-fix`、`schedule-order-main-table-wrap-display`、`zhaojie-feedback-user-select-simple-list-fix`。

GREEN: pre-commit-verification -> PASS，已完成当前直接相关静态验证：
- `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\mes-schedule-order-main-table-wrap-static.spec.js` -> `PASS`
- `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\mes-schedule-order-admission-wrap-static.spec.js` -> `PASS`
- `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\mes-feedback-user-select-permission-static.spec.js` -> `PASS`
- `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\mes-feedback-permission-static.spec.js` -> `PASS`
- `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\mes-feedback-tracking-static.spec.js` -> `PASS`
