# Execution Log

## 2026-07-22

- 用户问题：测试服 `DCC文件分类 -> 类别列表` 的“阶段”列仍显示旧阶段，要求统一且与本机一致。
- BDD: 测试服前端使用新阶段逻辑 -> Given 测试服已绑定 `file_type_taxonomy_id`; When 发布当前前端到测试服; Then 类别列表阶段列显示 DCC 文件分类阶段名。
- BDD: 仅测试服发布边界 -> Given 用户只要求测试服与本机一致; When 发布完成; Then 不执行正式服、备份服或 mark-tested 动作。
- GREEN: experience-preflight -> PASS，已读取 `docs/test-release-preflight.md`、`docs/release-agent-checklist.md`、`docs/release-build-preflight-lessons.md`、IntRuoyi `docs/server-access.md`、`docs/login-access.md`、`docs/release-backup-restore.md`、`docs/powershell-memory.md`；本轮仅允许测试服 `build-release -> publish-test -> 运行态和页面验证`。
- RED: dcc-category-stage-page-e2e -> FAIL(expected)，数据绑定已同步但测试服前端仍显示 `01 plan 策划`、`02 input 输入` 等旧阶段；证据在 IntRuoyi 任务 `doc/tasks/20260722-dcc-category-stage-test-sync/e2e-category-stage-page-20260722.json`。
- GREEN: frontend-release-deps -> PASS，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260722s\frontend_release` 执行 `pnpm install --frozen-lockfile` 成功，未修改业务源码。
- GREEN: build-release -> PASS，frontend-only 发布包 `release-20260722-dcc-category-stage-test-r260722b-r1` 已生成并上传 NAS；manifest 显示 `component=frontend`、`publishScope=code-only`、前端提交 `a0dd9098fb3b9177fd3c6b516bd94ee400952bd0`、dirty=false。
- RED: frontend-only-deploy-sql-gate-contract -> FAIL(expected)，`deploy-release` 在解析 `Component` 前调用 `Get-ReleasePackageDatabaseSqlScripts`，导致 frontend-only code-only 包因无 required SQL 被阻塞。
- GREEN: frontend-only-deploy-sql-gate-contract -> PASS，已将 deploy 包 required SQL 解析移动到 `$publishBackend` 分支内；`node --test scripts\tests\publish_frontend_deploy_sql_gate_contract.test.mjs scripts\tests\publish_release_info_contract.test.mjs scripts\tests\publish_image_tar_transfer_contract.test.mjs` 在维护主仓和发布 worktree 均通过。
- GREEN: publish-test -> PASS，测试服 frontend-only `deploy-release` 成功，`IMAGE_TAG=release-20260722-dcc-category-stage-test-r260722b-r1`，前端容器使用 `intruoyi-frontend:release-20260722-dcc-category-stage-test-r260722b-r1`。
- GREEN: runtime-test-verify -> PASS，`http://172.30.30.58:8081/` 返回 200，`/release-info.json` 返回 releaseTag `release-20260722-dcc-category-stage-test-r260722b-r1`，后端 `/actuator/health` 返回 200/UP。
- GREEN: dcc-category-stage-page-e2e -> PASS，真实登录测试服 `芋道源码/admin` 打开 `/dcc/controlled-file/categories`，`oldStageValues=[]`，可见新阶段包含 `设计和开发策划阶段`、`设计和开发输入阶段`、`设计和开发输出阶段`、`设计和开发验证`、`设计和开发转换阶段`。
- GREEN: runtime-control-local-restore -> PASS，`config/runtime-control.local.yaml` 已恢复为主工作区稳定路径。