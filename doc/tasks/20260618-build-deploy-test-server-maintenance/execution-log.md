# 维护仓构建并发布到测试服务器执行日志

BDD: 维护仓发布包含展厅奖项 SQL 门禁 -> Given 后端代码查询 showroom_award When 从维护仓 build-release Then required SQL / manifest / migration gate 包含 sql/showroom/20260613_showroom_award_and_hall_item_schema.sql。
BDD: 测试服部署前 schema preflight -> Given deploy-release 到测试服 When required SQL 执行完成 Then 后端启动前只读校验 showroom_award、showroom_award_revision、showroom_hall_item 和关键索引，缺失即失败。
BDD: 构建发布到测试服 -> Given 维护仓发布入口和目标测试服授权 When 使用真实前端操作构建并部署 code-only 发布包 Then build/deploy operation 均 SUCCESS，远端 backend/frontend 运行新 releaseTag 且健康。

- 用户需求：构建发布到测试服务器。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；本次授权仅限测试服 `172.30.30.58` 构建发布与只读验证，禁止备份服/正式服/备份/恢复/回滚/数据同步。
- BLOCKER-PREFLIGHT: maintenance-showroom-award-release-gate -> 维护仓 `ops/deploy/publish-int-ruoyi.ps1` 尚未包含 `sql/showroom` 奖项 schema required SQL / schema preflight；直接构建发布会复发测试服缺 `showroom_award` 表风险，先补 RED/GREEN 门禁。
- RED: `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> FAIL，发布脚本缺少 `Get-ReleaseDatabaseSqlRoots` / `Assert-RemoteShowroomAwardSchemaReady`，维护仓 `ops.release.release_migration_policy_gate` 导入不存在的 `script.release` 并且不支持 `sql_paths` / `file_prefix`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS，3 passed。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS。
- GREEN: `python -X utf8 -m pytest scripts\tests -q` -> PASS，8 passed。
- GREEN: `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\showroom --file-prefix sql/showroom --sql-file sql\showroom\20260613_showroom_award_and_hall_item_schema.sql` -> PASS，`migrationCount=1`。
- GREEN: `python -X utf8 ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\showroom --file-prefix sql/showroom --sql-file D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\showroom\20260613_showroom_award_and_hall_item_schema.sql` -> PASS，维护仓 CLI 入口支持指定 `sql/showroom` 文件。
- RED: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> FAIL，测试服 backend 冒烟前端目录和 npm 包装器配置未固化到发布模板，后续 deploy-release 会覆盖运行时手工修复。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，发布脚本从远端 `.env` 导出 `MES_SMOKE_NODE_IMAGE` 并在 backend 容器挂载 `/opt/intruoyi/runtime/smoke/bin/npm`。
- RED: `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> FAIL，发布包未同时纳入 `20260606_showroom_hall_product_canvas_layout` 与 `20260613_showroom_award_and_hall_item_schema` 的 dependsOn 契约。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS，发布 SQL 清单、manifest 和 policy gate 均包含 20260606/20260613 顺序依赖。
- RED: `node tests\e2e\vite-release-build-plugin-contract-static.spec.js` -> FAIL，前端 release build 仍启用 `vite-plugin-top-level-await`，真实 Vite 构建在 Rollup/SWC 阶段报 `TypeError: Cannot set property code of  which has only a getter`。
- GREEN: `node tests\e2e\vite-release-build-plugin-contract-static.spec.js` -> PASS，release build 已移除 `vite-plugin-top-level-await`。
- GREEN: 前端真实构建 `VITE_OUT_DIR=dist-intruoyi-test node ...\vite\bin\vite.js build --mode test` -> PASS，输出 `dist-intruoyi-test`。
- RED: Playwright 真实预览维护控制台“部署测试服” -> FAIL，请求未携带或后端拒绝 `targetEnvironment=test`，响应 `code=400`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_runtime_control_frontend_deploy_contract.py -q` -> PASS，前端部署类动作必须携带目标环境。
- GREEN: `mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#publishTestPreviewAcceptsMatchingTargetEnvironmentFromFrontend test` -> PASS，后端允许 deploy action 携带匹配的 `targetEnvironment` 并拒绝不匹配环境。
- GREEN: `scripts\build.ps1` -> PASS，维护控制台前端构建、后端测试 17 个、后端打包完成并重启健康。
- GREEN: 真实前端 build-release -> PASS，operation `op-2026-06-18T094150771556100Z-0c41d8dd-8879-42b1-b068-4e0457975aa7` SUCCESS，releaseTag `release-20260618-1742-showroom-sql-vite`，包大小 `813535256 bytes` / `775.85 MiB`，无 `docker-build-context`。
- BLOCKER: deploy-release stale-lock -> FAIL，测试服 `infra_release_operation_lock` 存在旧 `release-20260618-1437-showroom-sql-smoke-env` `RUNNING` 锁；该旧操作已失败但未释放锁。
- GREEN: stale-lock-close -> PASS，只将旧 `test-release-20260618-1437-showroom-sql-smoke-env` 锁更新为 `FAILED`，`updated_rows=1`。
- BLOCKER: deploy-release preflight-plan -> FAIL，operation `op-2026-06-18T101259230451800Z-07fd2c3e-63f6-4918-b3ad-75652da916bd` 在 `preflight-plan.json status=blocked` 停止；阻塞项为 `20260613_showroom_award_and_hall_item_schema -> BLOCKED_DEPENDENCY_MISSING`，缺 `20260606_showroom_hall_product_canvas_layout`。
- RED: `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` -> FAIL，新增用例 `test_preflight_accepts_dependency_applied_earlier_in_same_plan` 复现同一发布包内 parent `APPLY` 后 child 依赖仍被判 blocked。
- GREEN: `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` -> PASS，9 passed；预检计划按 manifest 顺序累积已满足迁移，当前计划中 20260606 和 20260613 均为 `APPLY` 且整体 `passed`。
- GREEN: maintenance-preflight-sync -> PASS，维护仓 `ops\release\release_preflight_plan.py` 与业务仓 `script\release\release_preflight_plan.py` SHA256 一致。
- GREEN: current-lock-close -> PASS，只将本次失败的 `test-release-20260618-1742-showroom-sql-vite` `RUNNING` 锁更新为 `FAILED`，`updated_rows=1`。
- GREEN: real-ui-deploy-test -> PASS，通过 Playwright 操作维护控制台“部署测试服”，operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` SUCCESS，日志显示 `Publish completed for test`。
- GREEN: remote-release-state -> PASS，测试服 operation lock `APPLIED`；`20260606_showroom_hall_product_canvas_layout`、`20260613_showroom_award_and_hall_item_schema`、`20260618_showroom_publicity_role_menu_scope` 均 `APPLIED`。
- GREEN: remote-schema -> PASS，`showroom_hall_product.layout_x/layout_y/layout_width/layout_height` 存在；`showroom_award`、`showroom_award_revision`、`showroom_hall_item` 和 6 个关键索引存在。
- GREEN: remote-runtime -> PASS，测试服 `.env` `IMAGE_TAG=release-20260618-1742-showroom-sql-vite`；backend/frontend 容器镜像 tag 均匹配且 `running`；`/actuator/health` 返回 `{"status":"UP"}`；前端 HTTP 200。
- GREEN: real-browser-test-server-frontend -> PASS，Playwright 打开 `http://172.30.30.58:8081/`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0，截图 `test-server-frontend-after-deploy.png`。
- GREEN: evidence-validators -> PASS，CI/CD、bug regression、database schema evidence validators 均通过。
- GREEN: task-closeout-cleanup-preview -> PASS，keep task/evidence/screenshot，delete none，blocked none，warnings none。
- GREEN: task-closeout-cleanup-apply -> PASS，deleted none，blocked none，warnings none。
