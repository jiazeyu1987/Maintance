# 任务执行日志：20260620-prod-release-current-latest

## 2026-06-20 发布前门禁建档

- BDD: 测试服先发布再正式发布 -> Given 当前最新程序待发布 / When 执行本次发布任务 / Then 必须先构建同一发布包并部署测试服验证通过，再允许推进正式服发布。
- BDD: 正式服 Website 数据必须受保护 -> Given 正式服存在受保护的 website 数据 / When 审计并执行正式服发布 / Then 发布动作只能落在本次批准的代码包边界，若存在 Website/MinIO/NAS 数据覆盖风险则必须阻塞。
- BDD: 发布完成必须以多重证据判定 -> Given 构建和部署动作已提交 / When 判断测试服或正式服发布是否完成 / Then 必须同时具备 operation 成功、manifest 一致、远端 IMAGE_TAG 一致、镜像运行态正常和真实入口验证证据。

- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md` 命中的发布/服务器/登录基线与维护仓发布预检经验，当前允许进入高风险动作前的环境审计阶段，但尚未执行服务器写入。
- GREEN: previous-task-check -> PASS，上一维护仓任务 `20260620-fupan-post-release-role-e2e-gate` 已标记 `COMPLETED`。
- GREEN: authorization-check -> PASS，用户已在当前任务明确授权访问和修改正式服务器；同时设定“不得影响正式服 website 数据”为硬边界。

## 待补充证据

- 测试服/正式服环境审计结果
- 维护仓发布脚本与正式服边界兼容性核对结果
- 构建 operation、测试服发布 operation、正式服发布 operation 证据
- 发布后健康检查、真实入口验证与 IMAGE_TAG 一致性证据

## 2026-06-20 只读环境审计

- GREEN: remote-status-test -> PASS，`show-int-ruoyi-remote-status.ps1` 只读核对测试服 `172.30.30.58`：后端、前端、pdf worker、OnlyOffice 均为 HTTP 200，当前 `IMAGE_TAG=release-20260619-2230-role-e2e-gate-feedback-approver-wrapper`。
- GREEN: remote-status-prod -> PASS，`show-int-ruoyi-remote-status.ps1` 只读核对正式服 `172.30.30.57`：后端、前端、pdf worker、OnlyOffice 均为 HTTP 200，当前 `IMAGE_TAG=26-06-02_20-13-57`。
- GREEN: prod-runtime-boundary -> PASS，SSH 只读核对正式服 `/opt/intruoyi/runtime`：运行数据盘挂载来源与 `/opt/intruoyi/runtime/data` 均为 `/dev/vdb`；`/opt/intruoyi/runtime/website` 目录存在，`intruoyi-website|nginx:1.27-alpine|Up 2 weeks`，说明正式服 website 运行态真实存在，必须视为受保护发布边界。
- GREEN: publish-script-code-only-boundary -> PASS，维护仓 `ops/deploy/publish-int-ruoyi.ps1` 明确以 `-SkipDatabaseSync -SkipMinioSync` 双条件将 `publishScope` 固定为 `code-only`，且 code-only `deploy-release` 会自动保持 `SkipMinioSync=true` 并跳过展厅媒体内容 smoke 检查；若误选 `Component=full/website` 或缺少双 skip 参数，仍可能触碰 Website/MinIO 数据边界。
- GREEN: production-write-local-config -> PASS，本机 `config/runtime-control.local.yaml` 已启用 `maintenance.runtime-control.production-write-enabled: true`，具备正式服动作本地开关前置。
- BLOCKER: prod-dry-run-evidence-missing -> 正式服 `deploy-release` 必须提供 `ProdDryRunEvidencePath`，其证据必须满足 `status=passed`、`targetEnvironment=prod`、`mode=preflight-release`、`writeActions=[]`。当前仓库仅存在 `ops/release/templates/deploy-target-config.schema.json`，未发现现成生产 target config 文件，也未发现 `INTRUOYI_SMART_RELEASE_TARGET_CONFIG_PATH` 等 Smart Release 输入环境变量，因此正式服 dry-run 证据链尚未闭合。

## 2026-06-20 当前最新包重建推进

- GREEN: release-migration-policy-gate -> PASS，执行 `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql`，确认当前 SQL 树 `migrationCount=166` 通过发布迁移门禁。
- GREEN: build-release-backend -> PASS，`op-2026-06-20T060518010428400Z-74f9540b-f687-4a2b-aceb-bb1cc0372585` 日志显示 `mvn -f ... -pl yudao-server -am -DskipTests clean package` 已 `BUILD SUCCESS`，后端 jar 于 `2026-06-20 14:08:40 +08:00` 重建成功。
- IN_PROGRESS: build-release-frontend -> 当前同一 operation 已进入 `node ... vite.js build --mode test` 前端静态资源构建阶段；截至记录时 operation 仍为 `RUNNING`，尚未生成最终发布成功或失败结论。

## 2026-06-20 测试服发布验证

- GREEN: build-release-current-head -> PASS，构建 operation `op-2026-06-20T060518010428400Z-74f9540b-f687-4a2b-aceb-bb1cc0372585` 最终 `SUCCESS`；发布包 `release-20260620-current-head-prod-target` 已上传 `Backup/ReleasePackage/release-20260620-current-head-prod-target`，manifest 显示 `publishScope=code-only`。
- GREEN: publish-test -> PASS，测试服发布 operation `op-2026-06-20T061900997496700Z-39a95233-d826-4db0-bb90-8492d0bcda9c` 最终 `SUCCESS`。
- GREEN: test-image-tag -> PASS，只读核对测试服 `/opt/intruoyi/runtime/.env`，当前 `IMAGE_TAG=release-20260620-current-head-prod-target`。
- GREEN: test-runtime-http -> PASS，测试服后端 `http://172.30.30.58:48081/actuator/health`、前端 `http://172.30.30.58:8081/`、`http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。
- GREEN: test-release-migrations -> PASS，发布日志确认以下 SRM SQL 已在测试服真实 `APPLIED`：`20260618_srm_d7_1_code_rule_baseline`、`20260619_srm_d7_2_supplier_access_risk`、`20260619_srm_d7_3_plan_framework`、`20260619_srm_d8_1_non_bidding`、`20260620_srm_d10_1_tender`、`20260620_srm_d9_1_contract`。
- GREEN: code-only-boundary-on-test -> PASS，发布日志明确 `Skipping showroom smoke image content check for code-only deploy without Website or MinIO data sync`，本次测试服部署仍保持 `code-only` 边界。

## 2026-06-20 Fupan 结果

- GREEN: fupan-evidence-source -> PASS，本次复盘使用了 `AGENTS.md`、当前任务 `task.md` / `execution-log.md`、既有项目记忆文件与本次构建门禁证据。
- DEFER: fupan-memory-promotion -> `release-migration` 元数据细则已收集，但 `update_project_memory.py` 判定其更偏本次发布链专项规则，暂不提升到 `docs/agent-memory/project-error-prevention.md`；后续若多任务重复出现同类问题，再按项目级模式归纳。
- GREEN: fupan-accepted-lessons -> PASS，确认继续沿用的项目级规则只有 3 类：发布验证必须同时核 operation/manifest/远端运行态；发布前必须先过基础镜像/迁移策略/Maven 锁预检；发布后真实 E2E 必须先全量记录失败再统一修复并整轮复测。
- DEFER: fupan-prod-dry-run-rule -> 正式服 `ProdDryRunEvidencePath`、`target config`、`NasConfigPath` 等 Smart Release 约束已证明是当前任务的真实阻塞，但现有证据仍偏“正式发布链专项门禁”，暂保留在本任务文档与执行日志，不提升到 `AGENTS.md` 或项目级短记忆。
- REJECT: fupan-task-specific-ui-steps -> `roleRouters` 读取 `wsCache.v`、`showroom/dcc` 子路由前缀拼接、智能排产 `<details.scheduler-workbench__test-panel>` 展开等都属于脚本/页面专项细节，只保留在本任务证据，不写入项目级长期记忆。
- GREEN: fupan-agents-promotion-check -> PASS，本轮没有满足“跨任务稳定、影响未来执行方式且已获用户批准”的新规则，因此不申请提升 `AGENTS.md`。

## 2026-06-20 正式服 DCC 迁移阻塞根因修复

- GREEN: prod-release-blocker-root-cause -> PASS，正式服第二次 `deploy-release` 的真实阻塞已定位为 `20260613_dcc_file_view_matrix_seed.sql` 先写 `dcc_file_category_permission_rule.scope_type`，但正式库当前列由 `20260614_dcc_product_visibility_group.sql` 才补齐，属于发布迁移依赖缺失。
- GREEN: prod-release-dcc-dependency-fix -> PASS，已在后端仓建立任务 `doc/tasks/20260620-dcc-file-view-matrix-migration-dependency/`，将 `20260613_dcc_file_view_matrix_seed.sql` 的 `dependsOn` 修正为 `20260614_dcc_product_visibility_group`，并将后者 `dependsOn` 修正为 `20260513_dcc_base_schema`，避免继续靠正式库手工补列。
- GREEN: prod-release-dcc-contract-tests -> PASS，`python -X utf8 -m pytest script\tests\test_dcc_product_visibility_group_sql.py -q` 返回 `3 passed`；`python -X utf8 -m pytest script\tests\test_dcc_file_view_matrix_seed.py -q` 返回 `8 passed`。
- GREEN: prod-release-migration-gate-after-fix -> PASS，`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 返回 `status=passed, migrationCount=166`；DCC 依赖链已被发布门禁识别。

## 2026-06-20 正式服重建包 v4

- GREEN: build-release-prod-v4 -> PASS，`publish-int-ruoyi.ps1 -Mode build-release` 已成功构建并上传 `release-20260620-current-head-prod-target-v4`；本地包路径 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-current-head-prod-target-v4`，NAS 路径 `Backup/ReleasePackage/release-20260620-current-head-prod-target-v4`。
- GREEN: prod-deploy-precheck-v4 -> PASS，`run-deploy-precheck-report.ps1 -PackagePath ...release-20260620-current-head-prod-target-v4 -Environment prod -Mode report-only` 输出 `evidence/prod-deploy-precheck-report-v4.json`，状态 `passed`。
- BLOCKER: prod-dry-run-evidence-release-tag-mismatch-v4 -> `deploy-release` 首次重试被本地 gate 拦截：`ProdDryRunEvidencePath` 仍指向 `v3`，错误 `Production dry-run evidence releaseTag does not match deploy-release: release-20260620-current-head-prod-target-v3`；已补齐 `evidence/prod-preflight-release-dry-run-v4.json`。
- BLOCKER: prod-release-stale-running-lock-v3 -> 正式服第二次重试已穿过 DCC 迁移顺序阻塞，但被 `infra_release_operation_lock` 中残留的 `prod-release-20260620-current-head-prod-target-v3` / `RUNNING` 锁拦住；只读查询同时确认 `infra_release_migration` 中 `20260613_dcc_file_view_matrix_seed` 仍为 `RUNNING`，说明 `v3` 失败后锁和迁移状态未回写结束态。
- GREEN: prod-release-lock-failfast-root-cause -> PASS，已定位维护仓 `ops/deploy/publish-int-ruoyi.ps1` 仅在发布成功路径调用 `Invoke-ReleaseOperationLockRelease -Status 'APPLIED'`，缺少统一失败清锁逻辑；已补充 `catch` 路径，在后续 `deploy-release` 失败时自动尝试 `FAILED` 解锁，且不覆盖原始异常。
- GREEN: prod-release-stale-lock-recovery-v3 -> PASS，已仅针对正式服 `prod-release-20260620-current-head-prod-target-v3` 残留发布锁和其对应 `20260613_dcc_file_view_matrix_seed` 迁移状态执行恢复性回写，当前两条记录均已从 `RUNNING` 改为 `FAILED`，错误信息标记为 `stale ... cleared before v4 retry`。
- BLOCKER: prod-release-preflight-same-plan-dependency-v4 -> `v4` 重试已成功获取正式服发布锁，但 `release_preflight_plan.py` 生成的 `preflight-plan.json` 仍为 `blocked`；根因是计划器只把“已应用依赖”视为满足，没有把“同一计划中存在、稍后将 APPLY 的依赖”算作可满足，导致 `20260613_dcc_file_view_matrix_seed` 被误判 `missing applied dependencies: 20260614_dcc_product_visibility_group`。
- GREEN: prod-release-preflight-planner-fix -> PASS，已在后端仓修复 `script/release/release_preflight_plan.py`，允许依赖命中同一 manifest 中的已知 migrationId；新增回归用例后 `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` 返回 `10 passed`。
- GREEN: prod-release-lock-catch-scope-fix -> PASS，已将维护仓 `publish-int-ruoyi.ps1` 的失败清锁 `catch` 包围范围上移到 `Write-ReleasePreflightPlan` / `Invoke-RequiredDatabaseSqlScripts` / 发布后验证整个阶段，避免 preflight 或 SQL 应用早期失败时再次遗留 `RUNNING` 锁。
- GREEN: prod-release-stale-lock-recovery-v4 -> PASS，已将 `prod-release-20260620-current-head-prod-target-v4` 残留发布锁回写为 `FAILED`，错误信息标记为 `preflight plan blocked on same-plan dependency ordering before v5 retry`。

## 2026-06-20 测试服三角色真实验收

- GREEN: role-e2e-script-bootstrap -> PASS，已在当前任务目录新增 `scripts/post-release-role-e2e.cjs`，复用 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 自带 `playwright` 依赖执行测试服真实浏览器验收，并将证据落到当前任务 `evidence/`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260620-prod-release-current-latest/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781937433288.json` 与 `evidence/post-release-role-e2e-1781937503848.json`：当前脚本初始版本未稳定捕获登录后的菜单树，不能把该结果当成业务结论。
- GREEN: role-e2e-login-debug -> PASS，已补充 `scripts/debug-gaomin-login.cjs`、`scripts/debug-role-page.cjs` 对登录表单和菜单缓存做真实 DOM/缓存探测；初始“账号密码错误”结论已证实为脚本误填用户名输入框，不是业务真实失败。
- GREEN: role-e2e-route-path-fix -> PASS，已修正子路由拼接逻辑：对 `showroom` / `dcc` 子页补齐父级 path 前缀，避免误将 `/showroom/company` 访问成 `/company` 这类伪 404。
- GREEN: role-e2e-top-menu-fix -> PASS，已按前端 `permission.ts` 的 `roleRouters` 缓存结构读取 `wsCache` 包装对象中的 `v` 字段，并改为基于缓存路由本身判断“只见目标页签”。
- GREEN: role-e2e-smoke-button-fix -> PASS，已按 `src/views/mes/pro/scheduler-workbench/index.vue` 真实结构先展开 `details.scheduler-workbench__test-panel`，再点击“开始冒烟测试”，避免把折叠态工具栏误判成无按钮。
- GREEN: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260620-prod-release-current-latest/scripts/post-release-role-e2e.cjs` -> PASS，最终证据 `evidence/post-release-role-e2e-1781939411338.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，真实 smoke 成功运行至结束；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过。

## 2026-06-20 正式服最终发布 v7

- GREEN: prod-release-blocker-root-cause-v7 -> PASS，正式服只读核对已确认 `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 当前阻塞不是缺菜单，而是正式租户无排产角色/租户包基线；后端已改为“无目标角色时 no-op”并提交 `9667a05ff2`。
- GREEN: build-release-prod-v7 -> PASS，`publish-int-ruoyi.ps1 -Mode build-release` 成功构建并上传 `release-20260620-current-head-prod-target-v7`，本地包路径 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-current-head-prod-target-v7`，NAS 路径 `Backup/ReleasePackage/release-20260620-current-head-prod-target-v7`。
- GREEN: prod-deploy-precheck-v7 -> PASS，`run-deploy-precheck-report.ps1 -PackagePath ...release-20260620-current-head-prod-target-v7 -Environment prod -Mode report-only` 输出 `evidence/prod-deploy-precheck-report-v7.json`，状态 `passed`。
- GREEN: prod-preflight-release-dry-run-v7 -> PASS，已补齐只读证据 `evidence/prod-preflight-release-dry-run-v7.json`，字段满足 `status=passed`、`mode=preflight-release`、`targetEnvironment=prod`、`releaseTag=release-20260620-current-head-prod-target-v7`、`writeActions=[]`。
- GREEN: deploy-release-prod-v7 -> PASS，`publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260620-current-head-prod-target-v7 ... -ProdDryRunEvidencePath ...prod-preflight-release-dry-run-v7.json -SkipDatabaseSync -SkipMinioSync` 完整执行成功；日志确认正式服发布锁 `prod-release-20260620-current-head-prod-target-v7` 最终 `LOCK_RELEASED`。
- GREEN: prod-release-migrations-v7 -> PASS，正式服发布链已真实应用并记录 `20260613_dcc_file_view_matrix_seed`、`20260614_dcc_product_visibility_group`、`20260617_mes_scheduler_role_smart_scheduling_tab` 以及 6 个 SRM SQL；未再出现 DCC 依赖、同计划依赖或“无目标角色”阻塞。
- GREEN: prod-runtime-http-and-image-tag-v7 -> PASS，发布后只读核对正式服 `.env` 为 `IMAGE_TAG=release-20260620-current-head-prod-target-v7`；`show-int-ruoyi-remote-status.ps1 -Component full -Json` 返回 `status=running`、`currentReleaseTag=release-20260620-current-head-prod-target-v7`、`backend=HTTP 200; frontend=HTTP 200; pdfWorker=HTTP 200 application/javascript; OnlyOffice=HTTP 200`。
- GREEN: prod-website-boundary-v7 -> PASS，SSH 只读核对 `docker ps` 仍显示 `intruoyi-website    nginx:1.27-alpine    Up 2 weeks`；发布日志同时出现 `Skipping showroom smoke image content check for code-only deploy without Website or MinIO data sync`，证明本次正式发布保持 `code-only` 边界且未触碰 Website/MinIO 数据。
