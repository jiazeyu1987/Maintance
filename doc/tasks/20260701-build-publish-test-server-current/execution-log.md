GREEN: experience-preflight -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`，确认本轮只允许执行 `build-release -> publish-test -> 测试服运行态验证`，不推进 `mark-tested`、正式服或备份服。

BDD: 默认发布只允许明确的主分支输入 -> Given 用户要求构建并发布到测试服务器 When 三仓主工作区存在未提交改动 Then 先阻塞并请用户选择“先提交主工作区”或“仅发布已提交 git 版本”的正式方案，未经确认不得继续真实发布。

BDD: 用户选择先提交主工作区后才能继续真实发布 -> Given 用户已明确选择“先提交再发布” When 三仓当前改动完成任务归属、验证与独立提交 Then 才允许把这些新提交作为本轮 `build-release -> publish-test` 的发布输入。

BDD: 测试服运行态必须落到同一 releaseTag -> Given 发布输入已满足仓库门禁且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health 与 frontend HTTP 必须全部与同一 `releaseTag` 一致。

GREEN: previous-task-check -> PASS，已核对上一维护仓发布任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-main-branch-test-server-release-closure\task.md` 状态为 `COMPLETED`，允许开启本轮新任务。

GREEN: repo-status-check -> PASS，已分别核对三仓当前状态，确认三仓主工作区存在待提交改动，必须先由用户选择发布输入方案。

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

GREEN: frontend-commit -> PASS，前端仓提交 `9662a85e7e54c41cbbc594a843a47dff8d1dfa7f`（`任务: 收口待归属与排产前端修复`），提交范围包含待归属权限、UserSelectV2 simple-list 回显、排产工单换行显示、展厅导入提示与 SRM NAS 定位浏览器验证脚本。

GREEN: maint-commit -> PASS，维护仓提交 `29bd0aa`（`任务: 更新测试服发布任务记录`），提交范围为当前发布任务台账与请求命令记录。

BLOCKER: backend-commit-without-tdd-task-dir -> 首次后端提交因 `.git/hooks/pre-commit` 要求 `TDD_TASK_DIR` 被阻塞，提示 `TDD compliance failed: set TDD_TASK_DIR to the task directory path before committing.`；该阻塞证明后端提交必须绑定明确任务目录。

GREEN: backend-release-input-closeout -> PASS，已补后端聚合任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260701-release-input-closeout\`，并重新验证：
- `python -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_d7_d10_sql_contract.py -k nas_locator -q` -> `PASS`
- `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-srm -am "-Dtest=SrmNasLocatorWildcardTenantSqlRegressionTest,SrmNasLocatorServiceTest" "-Dsurefire.failIfNoSpecifiedTests=false" test` -> `PASS`
- `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-showroom "-Dtest=ShowroomProductExcelImportExportIntegrationTest" test` -> `PASS`

GREEN: backend-commit -> PASS，后端仓带 `TDD_TASK_DIR=doc/tasks/20260701-release-input-closeout` 提交 `1985ac31a4ff57e52ff78721302ac0bd77ba505c`（`任务: 收口展厅与SRM发布修复`），TDD compliance hook 返回 `TDD compliance passed.`。

GREEN: clean-input-check -> PASS，三仓主工作区在发布前均已恢复 clean：
- 维护仓：`## int_main`
- 后端仓：`## int_main...origin/int_main [ahead 1230, behind 1128]`
- 前端仓：`## int_main...origin/int_main [ahead 52]`

GREEN: runtime-control-health -> PASS，`http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`；本轮通过运维台页面真实点击提交动作，不以命令行直跑发布脚本替代。

GREEN: build-release-preview -> PASS，通过本机运维台页面预览 `build-release`，参数包含 `-Mode build-release -ReleaseTag release-20260701-1720-current -Component intruoyi -SkipDatabaseSync -SkipMinioSync -BackendRepoRoot D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro -FrontendRepoRoot D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3`，符合 code-only 测试服发布包门禁。

GREEN: build-release -> PASS，运维台真实提交 `build-release` operation `op-2026-07-01T092718393431Z-e0ee2912-b24f-46d6-9a2e-5608c0426cde`，最终 `SUCCESS`；发布包 `release-20260701-1720-current` 已上传 NAS `Backup/ReleasePackage/release-20260701-1720-current`。

GREEN: manifest-check -> PASS，`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260701-1720-current\manifest.json` 已复核：
- 后端：`commit=1985ac31a4ff57e52ff78721302ac0bd77ba505c branch=int_main dirty=false`
- 前端：`commit=9662a85e7e54c41cbbc594a843a47dff8d1dfa7f branch=int_main dirty=false`

GREEN: publish-test-preview -> PASS，通过本机运维台页面预览 `publish-test`，参数为 `-Mode deploy-release -Environment test -ReleaseTag release-20260701-1720-current -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1`，与当前测试服真实基线一致。

GREEN: publish-test -> PASS，运维台真实提交 `publish-test` operation `op-2026-07-01T094350943851500Z-35882b3a-115c-44c0-b76e-57a2c4906633`，最终 `SUCCESS`；日志确认 remote `.env IMAGE_TAG`、required SQL、容器重建、readiness、PDF worker 与 smoke runtime 均通过。

GREEN: test-runtime-verification -> PASS，测试服运行态复核结果：
- `ENV_IMAGE_TAG=release-20260701-1720-current`
- `backend|intruoyi-backend:release-20260701-1720-current|running`
- `frontend|intruoyi-frontend:release-20260701-1720-current|running`
- `BACKEND_HEALTH={"status":"UP"}`
- `FRONTEND_HTTP=200`
- `PDF_WORKER_HTTP=200 application/javascript`
