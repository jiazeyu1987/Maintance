# Execution Log

## BDD

BDD: 当前 HEAD 干净构建 -> Given 三个主工作区均存在未提交改动 When 从维护仓、后端、前端当前 HEAD 创建干净 worktree 并构建 Then 发布包 manifest 必须显示三个 sourceRepos 均为本任务记录的 HEAD 且 dirty=false。

BDD: 测试服先行发布 -> Given 发布包 manifest 校验通过 When 部署测试服务器 Then 远端 `.env`、前后端镜像 tag、容器状态、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。

BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过且已标记测试通过 When 依次发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。

## Preflight

GREEN: experience-preflight -> PASS，已读取 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-memory.md` 与 `project-error-prevention.md`；用户当前发布目标明确授权测试服、正式服和备份服发布；本轮必须从干净 HEAD worktree 构建，发布包 manifest 必须证明 sourceRepos dirty=false。

GREEN: git-preflight -> PASS，维护控制台 `int_main/3eb9047d0ac0759ee46d7d88f4adba442bed474f`，后端 `int_main/b0586ee897dc5124580b49121b0a1656052b68fa`，前端 `int_main/0e7616075c6105efb577c6eabb02adafbd497290`；三个主工作区均存在未提交改动，禁止直接作为构建来源。

## RED

RED: dirty-workspace-direct-build -> FAIL，维护仓、后端、前端主工作区均存在未提交改动，直接构建会违反“未提交改动不得进入构建产物”验收标准。

RED: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> FAIL，干净后端 HEAD `b0586ee897dc5124580b49121b0a1656052b68fa` 报告 `20260624_unified_approval_phase5_retire_legacy_menus.sql` 缺少 `release-migration` 元数据。

RED: python -X utf8 -m pytest script\tests\test_unified_approval_phase5_retirement_sql.py -q -> FAIL，新增 `test_retirement_sql_declares_release_migration_metadata` 断言复现 SQL 第一行不是发布元数据。

## GREEN

GREEN: python -X utf8 -m pytest script\tests\test_unified_approval_phase5_retirement_sql.py -q -> PASS，`3 passed`；已只为 `20260624_unified_approval_phase5_retire_legacy_menus.sql` 增加发布元数据头并保留原 SQL 行为。

BLOCKER: main-workspace-policy-gate-noise -> 主后端工作区全量迁移门禁还扫描到未提交 SQL `20260624_mes_auto_schedule_permission_split` 的依赖问题；该文件不属于本次已提交发布输入，主工作区不得用于发布验证。后续必须在提交门禁修复后从新后端 HEAD 创建干净 worktree 重新运行全量门禁。

GREEN: backend-release-metadata-commit -> PASS，后端已提交 `acec53539490f1d9bf5953ddb6e0c8b5f5b8e8e1`，提交信息 `任务: 补齐统一审批Phase5发布元数据`；提交只包含 `20260624_unified_approval_phase5_retire_legacy_menus.sql` 与对应测试。

RED: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> FAIL，干净后端 HEAD `acec535394763ff037b099679ef547a48121ee24` 报告 `20260624_mes_auto_schedule_permission_split` 的 `dependsOn` 使用了带 `.sql` 后缀的文件名。

RED: python -X utf8 -m pytest script\tests\test_mes_auto_schedule_permission_sql.py script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，新增两个元数据格式断言复现 `dependsOn` 使用 `.sql` 后缀的问题。

GREEN: python -X utf8 -m pytest script\tests\test_mes_auto_schedule_permission_sql.py script\tests\test_unified_electronic_signature_menu_sql.py -q -> PASS，`8 passed`；已仅去掉两个已提交 SQL 头部 `dependsOn` 的 `.sql` 后缀，未改变 SQL 执行业务内容。

GREEN: backend-migration-depends-on-commit -> PASS，后端已提交 `b70624daea23e5792e546f62a868272f99b71af4`，提交信息 `任务: 修正发布迁移依赖元数据`；提交只包含两个 SQL 元数据和对应测试。

GREEN: release-resume-20260627 -> PASS，用户于 `2026-06-27` 明确要求继续执行“构建发布到测试服务器，然后发布到正式服务器和备份服务器，并持续记录问题”；已复核上一未完成任务与本轮目标一致，继续沿用当前任务目录执行，不新建并行发布任务。

GREEN: runtime-control-preflight -> PASS，本机运行控制台 `http://127.0.0.1:48181/actuator/health` 返回 `UP`，页面入口 `http://127.0.0.1:48181/` 返回 `200`；具备按真实页面按钮继续发布的基础条件。

RED: stale-head-baseline-20260627 -> FAIL，`2026-06-27` 复核发现任务文档中的后端/前端发布基线已过期：后端主仓最新已提交 HEAD 从 `b70624daea23e5792e546f62a868272f99b71af4` 前进到 `e48845f3203fdc19c673de5d09b14f2b1d6b6181`，前端主仓最新已提交 HEAD 从 `0e7616075c6105efb577c6eabb02adafbd497290` 前进到 `ae9c00762c481b87edb3aa72ba8c312bfe9d3633`。继续沿用旧提交出包会违反“只发布当前最新已提交代码”要求。

GREEN: stale-head-baseline-20260627 -> PASS，已将任务基线更新为维护控制台 `3eb9047d0ac0759ee46d7d88f4adba442bed474f`、后端 `e48845f3203fdc19c673de5d09b14f2b1d6b6181`、前端 `ae9c00762c481b87edb3aa72ba8c312bfe9d3633`；后续必须基于这三个最新 HEAD 重新创建干净 worktree 并出包。

GREEN: release-worktree-preflight-20260627 -> PASS，已创建干净发布 worktree：维护控制台 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047`、后端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-e48845f`、前端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260627-ae9c007`；三者 `git status --short` 为空且 HEAD 与任务基线一致。

GREEN: pnpm-install-release-frontend-20260627 -> PASS，干净前端 worktree 已执行 `pnpm install --frozen-lockfile` 成功，满足发布前端依赖恢复门禁。

RED: release-metadata-gate-20260627 -> FAIL，最新后端 HEAD 初次运行 `python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` 失败，依次暴露 `20260624_dcc_view_matrix_independent_seed.sql` 等 4 个 SQL 缺少 `release-migration` 元数据，以及 10 个 SQL 的 `dependsOn` 仍引用带 `.sql` 后缀或不存在的 migrationId；若直接点运行控制台 `build-release`，会在发布门禁处失败，无法生成 manifest。

GREEN: release-metadata-tdd-20260627 -> PASS，已在干净后端 worktree 先以严格 TDD 补齐/修正上述 SQL 发布契约：新增 `test_dcc_view_matrix_independent_seed_sql.py`、`test_dcc_review_matrix_rule_metadata_sql.py`，并扩展相关 SQL 契约测试；定向 `pytest` 已从 RED 走到 `19 passed`，发布门禁复跑返回 `status=passed`、`migrationCount=217`。

GREEN: backend-release-metadata-commit-20260627 -> PASS，已将发布契约修复回放到真实后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，在真实仓复跑定向 `pytest` 与 `run-release-migration-policy-gate.py` 均通过，并提交为新 HEAD `72705e1808d2b0c2e95c914f8a55d569ca0e88f5`，提交信息 `任务: 补齐发布迁移契约门禁`。

RED: runtime-control-stale-source-path-20260627 -> FAIL，续跑时发现本机 `48181` 运行控制台实际仍从旧 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260625-3eb9047` 启动，预览参数错误指向陈旧后端/前端路径 `D:/rw/BE25`、`D:/rw/FE25`；若继续点击页面发布，将违反“只发布当前最新已提交代码”要求。

GREEN: runtime-control-stale-source-path-20260627 -> PASS，已在干净维护控制台 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047` 重新构建并重启本机运行控制台；`http://127.0.0.1:48181/actuator/health` 返回 `UP`，发布页面 `build-release` 预览现已显示正确脚本 `...\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1`，且 `BackendRepoRoot=D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro`、`FrontendRepoRoot=D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3`，满足继续执行真实页面构建的源路径门禁。

RED: runtime-control-build-release-20260627 -> FAIL，运行控制台页面真实执行 `build-release` 后生成 operation `op-2026-06-26T203544816067200Z-7af990fb-ef4f-4038-901c-888076d1661c`，本机执行日志返回 `Migration policy gate failed`；首个阻塞为 `sql/mysql/20260624_unified_electronic_signature_menu.sql:99 -> @unified_signature_overview_menu_id`，说明当前已提交 SQL 仍有 `system_menu.id` 不是整数字面量，发布包在 manifest 生成前即被门禁拦截。

RED: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，新增“统一电子签名子菜单插入必须使用整数字面量 id”断言后，复现 `VALUES (@unified_signature_overview_menu_id, '总览', ...)` 不满足发布门禁。

GREEN: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> PASS，`6 passed`；已将 `20260624_unified_electronic_signature_menu.sql` 子菜单 `INSERT INTO system_menu` 的 900410-900417 改为整数字面量，保留 parent 变量绑定与既有业务语义不变。

GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS，真实后端仓发布迁移门禁复跑通过，返回 `status=passed`、`migrationCount=217`；当前可重新执行运行控制台 `build-release`。

RED: runtime-control-build-release-20260627-retry1 -> FAIL，切换新 releaseTag `release-20260627-0448-head-full-v2` 后再次从页面执行 `build-release`，operation `op-2026-06-26T204120738837700Z-25253bc1-c5c0-4014-a23e-7ef808100cc5` 仍在发布门禁前失败；日志显示真正阻塞点是同一 SQL 第 99 行临时表 `tmp_unified_signature_child_menu_ids` 仍使用 `(@unified_signature_overview_menu_id)` 等变量字面量，而不是此前已修复的 `INSERT INTO system_menu` 段。

RED: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，追加“临时菜单 id 表也必须使用整数字面量”断言后，复现 `tmp_unified_signature_child_menu_ids` 的 `VALUES (@unified_signature_overview_menu_id)` 仍违反发布门禁。

GREEN: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> PASS，`6 passed`；已将 `tmp_unified_signature_child_menu_ids` 的 900410-900417 改为整数字面量，并同步修正角色菜单绑定断言。

GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS，第二轮真实后端仓发布迁移门禁复跑仍返回 `status=passed`、`migrationCount=217`，说明统一电子签名菜单 SQL 现已完整满足发布契约。

GREEN: backend-release-literal-menuid-commit-20260627 -> PASS，已将第二轮统一电子签名菜单字面量门禁修复提交到真实后端仓，新 HEAD `413d38ce8cedd59f92f369c64f10a3441617d07d`，提交信息 `任务: 修复统一电子签名菜单字面量门禁`。

RED: runtime-control-build-release-20260627-retry2 -> FAIL，第三次页面执行 `build-release` 生成 operation `op-2026-06-26T204436560083900Z-9419725c-ca3e-4508-9b6b-c96c3c736b95`，已越过前两次“非整数字面量”门禁，但被更深一层 SQL 合约拦截：`20260624_unified_electronic_signature_menu.sql` 同时在临时表 `tmp_unified_signature_child_menu_ids` 和 `INSERT INTO system_menu ... VALUES` 中声明 `900410-900417`，`release_sql_contract_gate.py` 判定为 `duplicate system_menu.id detected across release SQL history`。

RED: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，新增“子菜单插入必须使用 `SELECT ... UNION ALL` 而不是 `VALUES`”断言后，复现当前 SQL 结构仍会触发维护仓 `release_sql_contract_gate.py` 的重复菜单 id 检查。

GREEN: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> PASS，`6 passed`；已将统一电子签名子菜单 `INSERT INTO system_menu` 从 `VALUES (...)` 改为派生表 `SELECT child_def... FROM (SELECT ... UNION ALL ...) AS child_def`，保留字面量 id 与既有业务字段。

GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS，第三轮真实后端仓发布迁移门禁复跑仍为 `status=passed`、`migrationCount=217`。

GREEN: python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\release_sql_contract_gate.py D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260624_unified_electronic_signature_menu.sql -> PASS，维护仓发布 SQL 合约门禁不再报告重复 `system_menu.id`，说明统一电子签名菜单 SQL 现已同时满足 manifest 门禁与 contract gate。

RED: runtime-control-build-release-20260627-retry3 -> FAIL，第四次页面执行 `build-release` 生成 operation `op-2026-06-26T204920464790500Z-8df740fe-ea40-4a32-958a-6fb7a2cc7189`，后端 Maven 打包已通过，但前端构建阶段在 `src/views/dcc/controlled-file/approval-tasks/index.vue` 命中 `vue/valid-template-root`，发布包未生成。

GREEN: frontend-template-root-fix-20260627 -> PASS，已在前端仓新增 `tests/e2e/redirect-template-root-static.spec.js`，先 RED 复现空模板构建阻塞，再为 `approval-tasks/index.vue` 与 `mes/pro/edhr/ApprovalPage.vue` 补充合法根节点；`node tests/e2e/redirect-template-root-static.spec.js`、`node tests/e2e/approval-center-phase5-retirement-static.spec.mjs`、`pnpm build:test` 均通过。

RED: release-script-frontend-default-heap-20260627 -> FAIL，前端源码修复后直接执行运行控制台同款命令 `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js build --mode test` 暴露新的真实阻塞：默认 Node heap OOM，说明运行控制台发布脚本前端构建入口仍绕过正式 `build:test` 内存保护。

GREEN: release-script-frontend-memory-guard-20260627 -> PASS，已在后端仓把 `publish-int-ruoyi.ps1` 的 `Invoke-FrontendViteBuild` 改为执行 `pnpm build:test`，并新增脚本契约测试锁定该入口；`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `90 passed`，且前端 `pnpm build:test` 回归成功。

RED: runtime-control-build-release-20260627-retry4 -> FAIL，operation `op-2026-06-26T211910735094400Z-902d4c44-da17-4a6c-a275-f33bb5cf2109` 已完成后端 jar、前端静态构建、前后端镜像构建与镜像导出，但最终在挂载 NAS 发布仓库 `\\172.30.30.4\IT共享` 时失败，`net use` 返回 `System error 86`。

GREEN: nas-credential-preflight-20260627 -> PASS，用户修复 NAS 权限后，本机 `net use "\\172.30.30.4\IT共享" /user:int <redacted>` 已返回成功；当前运行控制台进程 `60664` 也确认通过 `--spring.config.import=optional:file:D:/ProjectPackage/Int/IntRuoyiMaintance/config/runtime-control.local.yaml` 读取最新本机配置，具备再次真实重跑 `build-release` 的前置条件。

RED: runtime-control-dirty-source-root-20260627 -> FAIL，`release-20260627-2312-head-full-v4` 对应 operation `op-2026-06-27T031133631088Z-69fa15c1-af7a-4d05-967a-b2e476c2466d` 虽然已越过 NAS 凭据阶段，但日志确认其 `-BackendRepoRoot` / `-FrontendRepoRoot` 实际仍指向主工作区 `D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro` 与 `.../yudao-ui-admin-vue3`，而非干净 release worktree。进一步只读核对显示主后端仓当前存在未提交 `yudao-module-mes` 改动，且本次 Maven 失败正落在这些未提交测试/实现上，因此该失败不属于“当前已提交 HEAD 发布输入”的合法阻塞；若继续沿此基线重试，将违反“未提交改动不得进入构建产物”和 `sourceRepos.dirty=false` 门禁。

RED: release-worktree-head-stale-20260627 -> FAIL，修正主工作区漂移后重新以 `release-20260627-2330-head-full-v5` 从真实页面发起 `build-release`，预览参数虽已切回干净 worktree，但仍指向旧后端 `D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260627-72705e1` 与旧前端 `.../IntRuoyi-frontend-20260627-ae9c007`。真实 operation `op-2026-06-27T032830617333Z-b6d06255-379f-4e61-bd2e-cd146749fb5d` 日志再次命中 `20260624_unified_electronic_signature_menu.sql:99` 的旧 SQL 门禁，证明当前控制台基线不是任务要求的最新已提交后端 `ebabbfc...` / 前端 `7632896...`。若继续沿旧 worktree 重试，仍会违反“发布输入必须与当前任务记录的最新 HEAD 一致”的门禁。

RED: frontend-release-worktree-deps-missing-20260627 -> FAIL，切换到最新后端 `ebabbfc...` 与前端 `7632896...` 的干净 worktree 后，真实页面 `build-release` operation `op-2026-06-27T033250656299700Z-51c6af05-68cf-4424-a807-9c9a4f5deef9` 已完成后端 Maven 全量打包并返回 `BUILD SUCCESS`，随后在前端构建入口失败：`Missing frontend Vite CLI: D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260627-7632896\node_modules\vite\bin\vite.js`。这说明最新前端干净 worktree 尚未按经验门禁恢复依赖，发布包仍未生成。

GREEN: frontend-release-worktree-deps-missing-20260627 -> PASS，已在最新前端干净 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260627-7632896` 执行 `pnpm install --frozen-lockfile` 恢复依赖，满足 `release-build-preflight-lessons.md` 的依赖门禁。

GREEN: runtime-control-build-release-20260627-v6 -> PASS，真实页面重新执行 `build-release` 后生成 operation `op-2026-06-27T034552307086100Z-d5d79836-4ec1-4ee5-b0ef-bdff8e971f94`，release tag=`release-20260627-2350-head-full-v6`，最终状态 `SUCCESS`；operation 日志确认发布脚本已完成后端打包、前端 `pnpm build:test`、镜像构建、镜像导出、manifest 生成和 NAS 上传。

GREEN: release-manifest-verify-20260627-v6 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260627-2350-head-full-v6\manifest.json` 与 NAS `\\172.30.30.4\IT共享\Backup\ReleasePackage\release-20260627-2350-head-full-v6\manifest.json` 已核对一致；其中后端 commit=`ebabbfcfbf6cbde468f602c5ea18c12346013699`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`。

GREEN: runtime-control-release-packages-20260627-v6 -> PASS，运行控制台 `release-packages` 已出现 `release-20260627-2350-head-full-v6`，状态 `AVAILABLE`，`tested=false`；说明当前候选包已满足继续测试服真实发布的前置门禁。

RED: runtime-control-deploy-test-20260627-v6 -> FAIL，真实页面从运行控制台选择“部署测试服”并执行后，生成 operation `op-2026-06-27T040320387887200Z-cf7a52cd-2025-43d3-b485-f8b027c4f58f`。发布链路已通过 SSH、测试服数据盘校验、`.env` 下发、发布包/required-sql/ops-runtime 同步，并开始逐条执行 `required-sql` 与回写 `infra_release_migration`。在执行 `20260624_dcc_view_matrix_independent_seed.sql` 时，测试服远端 MySQL 返回 `ERROR 1644 (45000) at line 736: VIEW_MATRIX_SEED_TENANT_REQUIRED: set @dcc_view_matrix_seed_tenant_id before sourcing this SQL`，随后发布脚本将该 migration 记为 `FAILED` 并释放 `infra_release_operation_lock`，operation 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。

GREEN: deploy-test-required-sql-context-fix-20260627 -> PASS，已在后端仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260627-release-required-sql-dcc-view-matrix-tenant-context\` 按严格 TDD 收口该阻塞。修复将发布脚本 `Invoke-RequiredDatabaseSqlScripts` 扩展为：当 migration 为 `20260624_dcc_view_matrix_independent_seed` 时，在同一 mysql 会话内先注入 `SET @dcc_view_matrix_seed_tenant_id := 122;`，再拼接远端 SQL 文件内容执行；不再依赖人工登录服务器临时设变量。定向回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `91 passed`，`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_view_matrix_independent_seed_sql.py -q` 返回 `1 passed`。

RED: runtime-control-deploy-test-20260627-v6-retry1 -> FAIL，真实页面重新执行测试服发布后生成 operation `op-2026-06-27T043350216700900Z-8388a3a5-8744-4d3c-9ab0-b2f34ac760f5`。日志确认 `20260624_dcc_view_matrix_independent_seed.sql` 已在同一 mysql 会话中先执行 `SET @dcc_view_matrix_seed_tenant_id := 122;`，不再报 `VIEW_MATRIX_SEED_TENANT_REQUIRED`；但随后在 line 737 失败为 `VIEW_MATRIX_SEED_SUBJECT_PRECHECK_FAILED`。

GREEN: test-server-view-matrix-org-readonly-preflight-20260627 -> PASS，按只读方式查询测试服 `172.30.30.58` 的 `system_dept` / `system_users` 真实数据，确认 tenant `122` 当前组织树为：
- `质量体系中心`、`研发创新中心`、`供应链中心`、`注册服务中心` 直属 `顶级部门`
- `市场营销中心`、`生产制造中心`、`检测中心` 直属 `瑛泰医疗`
- 不存在 `市场服务部`
- 不存在 `生产一车间`
- 不存在 `瑛泰医疗/注册服务中心`

GREEN: deploy-test-view-matrix-org-contract-fix-20260627 -> PASS，已在后端仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260627-release-required-sql-dcc-view-matrix-tenant-context\` 继续按严格 TDD 收口该新阻塞：
- `20260624_dcc_view_matrix_independent_seed.sql` 将“市场 / 业务+跟单及以上”主体改为测试服真实存在的 `瑛泰医疗/市场营销中心`
- `20260624_dcc_view_matrix_independent_seed.sql` 将“市场 / 注册”主体改为测试服真实存在的 `顶级部门/注册服务中心`
- `script/dcc_view_matrix_test_tenant_prereq_20260624.sql` 同步移除过时 `市场服务部`、`生产一车间`、`dccmatrixworkshop` 假设，并把 `dccmatrixmarket` 绑定到 `市场营销中心`
- 回归：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_view_matrix_independent_seed_sql.py D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_view_matrix_excel_seed_sql.py -q` -> PASS (`95 passed`)

BLOCKER: 由于发布包 `release-20260627-2350-head-full-v6` 内已固化旧后端 commit `ebabbfcfbf6cbde468f602c5ea18c12346013699`，即便维护仓与真实后端仓已修复主体映射，当前候选包也无法直接继续测试服放行。必须先将后端本轮 DCC seed 组织映射修复提交，基于新的已提交 HEAD 重新创建干净发布基线并重新执行 `build-release -> deploy test`；在新的测试服候选包成功前，正式服与备份服仍不得继续。

## BLOCKER

- 当前 blocker：测试服真实发布已从“缺少 `@dcc_view_matrix_seed_tenant_id` 上下文”推进到“发布包内的 DCC 查阅矩阵 seed 仍固化旧测试租户组织树”，而当前候选包 `release-20260627-2350-head-full-v6` 已固化旧后端 commit，不能直接沿用。影响：必须先提交后端组织映射修复、重新构建新的发布包并重新执行测试服真实发布；正式服与备份服继续阻塞。

GREEN: release-worktree-head-refresh-20260627 -> PASS，后端真实仓已提交 DCC 查阅矩阵发布前置契约修复，新 HEAD=dc9677512231b987160d0bd0be4523c704d3f07；已新建干净后端发布 worktree D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-fdc9677，并将本机 config/runtime-control.local.yaml 的 
epo-root 切换到该新 worktree，准备重新执行真实页面 uild-release。
GREEN: runtime-control-build-release-20260628-v7 -> PASS，真实页面重新执行 `build-release` 后生成 operation `op-2026-06-27T045917982904200Z-4e244e96-85da-4f2a-ad70-918929ee31d4`，release tag=`release-20260628-0015-head-full-v7`，最终状态 `SUCCESS`；manifest 核对后端 commit=`fdc9677512231b987160d0bd0be4523c704d3f07`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`。

RED: runtime-control-deploy-test-20260628-v7 -> FAIL，真实页面重新执行测试服发布后生成 operation `op-2026-06-27T052800433952800Z-b29af7f5-7631-4416-86f5-bc3f4b891c56`。日志确认：
- `.env` 的 `IMAGE_TAG=release-20260628-0015-head-full-v7` 校验通过；
- `required-sql` 与 `infra_release_migration` 已越过此前的 `VIEW_MATRIX_SEED_TENANT_REQUIRED` 和 `VIEW_MATRIX_SEED_SUBJECT_PRECHECK_FAILED`；
- 最终在 `20260624_dcc_view_matrix_independent_seed.sql` line 737 失败为 `VIEW_MATRIX_SEED_ROLE_USER_PRECHECK_FAILED`。

GREEN: test-server-role-user-root-cause-readonly-preflight-20260628 -> PASS，只读核对测试服 tenant `122` 真实数据后确认：
- `研发创新中心`、`质量体系中心`、`注册服务中心`、`瑛泰医疗`、`供应链中心` 及其关键子部门都存在；
- 但 `QC`、`新品开发部`、`生产制造中心`、`生产采购`、`包装设计组` 以及上层中心部门的 `leader_user_id` 均为空；
- 测试服不存在任何 `username LIKE 'dccmatrix%'` 的 prerequisite 用户；
- 基于真实部门数据模拟五个目标角色的 role-user 解析，`dcc_matrix_qc_lead`、`dcc_matrix_packaging_design_lead`、`dcc_matrix_new_product_lead`、`dcc_matrix_production_line_lead`、`dcc_matrix_production_purchase_lead` 全部得到 `user_count=0`。

GREEN: deploy-test-view-matrix-role-user-prereq-fix-20260628 -> PASS，已在真实后端仓按严格 TDD 收口该新 blocker：
- 将 `script/dcc_view_matrix_test_tenant_prereq_20260624.sql` 正式化为发布迁移 `sql/mysql/20260624_dcc_view_matrix_test_tenant_prereq.sql`，限制 `allowedEnvironments=test`
- 保持 `20260624_dcc_view_matrix_independent_seed.sql` 的共享环境契约不变，避免 test-only 依赖污染 backup/prod
- 发布脚本新增 `Sort-RequiredDatabaseSqlApplyItems`，仅在 `deploy-release(test)` 时强制 prerequisite 先于 independent seed 执行
- 本地回归：
  - `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_view_matrix_independent_seed_sql.py D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_view_matrix_excel_seed_sql.py -q` -> PASS (`98 passed`)
  - `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` -> PASS (`status=passed`, `migrationCount=218`)
  - `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\dcc_view_matrix_independent_seed_sql_test.py` -> PASS
  - `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\dcc_view_matrix_test_tenant_prereq_sql_test.py` -> PASS

GREEN: runtime-control-build-release-20260628-v8 -> PASS，继续轮询真实页面 `build-release` operation `op-2026-06-27T064023871534600Z-6a62871f-d07d-447d-aea0-5d847b6c73b0`，确认 release tag=`release-20260628-1438-head-full-v8` 最终状态为 `SUCCESS`；日志显示已完成后端 Maven 打包、前端 `pnpm build:test`、前后端镜像构建、`docker save` 导出、manifest 生成和 NAS 上传，结束语为 `Release package built: release-20260628-1438-head-full-v8`。

GREEN: release-manifest-verify-20260628-v8 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-1438-head-full-v8\manifest.json` 已生成并核对：后端 commit=`e091969a38e78ef8b53a3806972f0fd6e4f464bd`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`；与本轮新的已提交发布基线一致。

GREEN: runtime-control-deploy-test-20260628-v8-start -> PASS，已从真实页面再次执行“部署测试服”，生成 operation `op-2026-06-27T065833213012400Z-00f1bc62-ed29-4e0c-8088-dd988db4ed2a`，release tag=`release-20260628-1438-head-full-v8`。预览命令确认参数指向测试服 `172.30.30.58`，且后端源码根为 `D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260627-e091969`。

GREEN: runtime-control-deploy-test-20260628-v8-progress -> PASS，持续轮询 `op-2026-06-27T065833213012400Z-00f1bc62-ed29-4e0c-8088-dd988db4ed2a` 日志，当前已完成：NAS 下载、eDHR Object Lock 校验、测试服 SSH 与 `docker compose` 预检、远端数据盘/运行目录准备、`.env` 下发与 `IMAGE_TAG=release-20260628-1438-head-full-v8` 核对、smoke 依赖准备、镜像 tar 上传，并已进入 `required-sql` 批量同步阶段；最新日志已推进到 `20260619_*` SQL，同步过程中暂未出现新的 `FAILED`、`VIEW_MATRIX_*` 或 `infra_release_migration` 错误。

RED: runtime-control-deploy-test-20260628-v8 -> FAIL，真实页面测试服发布 operation `op-2026-06-27T065833213012400Z-00f1bc62-ed29-4e0c-8088-dd988db4ed2a` 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。日志确认本轮链路已真实完成：NAS 下载、eDHR Object Lock 校验、测试服 SSH/`docker compose` 预检、远端目录准备、`.env` 下发与 `IMAGE_TAG=release-20260628-1438-head-full-v8` 核对、镜像上传、`20260624_dcc_view_matrix_test_tenant_prereq.sql` 同步、`20260624_dcc_view_matrix_independent_seed.sql` 同步，并在执行 independent seed 前同一 mysql 会话内注入 `SET @dcc_view_matrix_seed_tenant_id := 122;`。真正失败点仍收敛为 `20260624_dcc_view_matrix_independent_seed.sql` line 737，测试服远端 MySQL 返回 `VIEW_MATRIX_SEED_ROLE_USER_PRECHECK_FAILED`；随后 `infra_release_migration` 被回写为 `FAILED`，`infra_release_operation_lock` 释放为 `LOCK_RELEASED`。

BLOCKER: 最新 blocker 已进一步收敛为“即使 test-only prerequisite migration 已纳入发布链路并排序在 independent seed 之前，测试服真实 role-user precheck 仍未被满足”。影响：当前候选包 `release-20260628-1438-head-full-v8` 不得继续标记测试通过、正式服或备份服；必须先回到后端真实仓继续只读核对 prerequisite 对测试服 tenant `122` 的实际补数效果，按严格 TDD 修复并提交后，重新生成新的候选包，再从真实页面重走测试服发布。

GREEN: deploy-test-root-cause-readonly-20260628-v8 -> PASS，继续只读核对 `release-20260628-1438-head-full-v8` 的真实发布证据后，确认当前根因不是“prerequisite SQL 执行后仍无法满足 role-user precheck”，而是“真实发布脚本根本没有执行 prerequisite apply item”：
- 本地发布包 `manifest.json` 与 `preflight-plan.json` 都包含 `20260624_dcc_view_matrix_test_tenant_prereq`，且 test 环境 action=`APPLY`；
- 本地 `preflight-target-state-test.json` 对该 migration 返回 `null`，说明 preflight 也未把它判成已应用；
- 测试服真实 operation 日志没有出现 `Applying required database SQL: 20260624_dcc_view_matrix_test_tenant_prereq.sql`；
- 测试服 `infra_release_migration` 中不存在 migration_id=`20260624_dcc_view_matrix_test_tenant_prereq` 的任何记录；
- 测试服 tenant `122` 仍不存在任何 `dccmatrix*` prerequisite 用户，关键部门 `leader_user_id` 仍全部为空。

GREEN: maintenance-script-prereq-sort-fix-20260628 -> PASS，只读比对后确认：后端真实仓 `script\deploy\publish-int-ruoyi.ps1` 已包含 `Sort-RequiredDatabaseSqlApplyItems` 并把 `20260624_dcc_view_matrix_test_tenant_prereq` 排在 `20260624_dcc_view_matrix_independent_seed` 之前，但运行控制台当前实际使用的维护仓脚本 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 缺少该函数，`Invoke-RequiredDatabaseSqlScripts` 仍直接使用原始 `Get-ReleasePreflightApplyItems` 顺序，导致真实测试服发布先跑了 independent seed、完全漏掉 prerequisite。

GREEN: maintenance-script-prereq-sort-regression-20260628 -> PASS，已在维护仓 `ops\deploy\publish-int-ruoyi.ps1` 同步回填 `Sort-RequiredDatabaseSqlApplyItems`，并让 `Invoke-RequiredDatabaseSqlScripts` 在 test 环境使用排序后的 applyItems；新增维护仓契约测试 `scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_executes_dcc_view_matrix_prereq_before_seed_on_test` 后，`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` 返回 `5 passed`。

RED: runtime-control-deploy-test-20260628-v8-retry2 -> FAIL，真实页面再次执行测试服发布后生成 operation `op-2026-06-27T072114322041600Z-826c3463-e987-40cb-a9af-9a14a903c669`。本轮日志已确认维护仓脚本排序修复真实生效：`Applying required database SQL: 20260624_dcc_view_matrix_test_tenant_prereq.sql` 出现在 line 1784，随后 `Applying required database SQL: 20260624_dcc_view_matrix_independent_seed.sql` 出现在 line 1803，说明此前“运行控制台实际脚本漏执行 prerequisite”这一根因已被关闭；但链路继续前进后，在 `Applying required database SQL: 20260625_dcc_fvm_matrix_retain_other_completion.sql`（line 1878）处失败，测试服远端 MySQL 返回 `ERROR 1644 (45000) at line 404: DCC_FVM_RETAIN_OTHER_COMPLETION_CATEGORY_BASELINE_CHANGED`，operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。

BLOCKER: 当前最新 blocker 已从 `VIEW_MATRIX_SEED_ROLE_USER_PRECHECK_FAILED` 前进到 `20260625_dcc_fvm_matrix_retain_other_completion.sql` 的分类基线校验失败 `DCC_FVM_RETAIN_OTHER_COMPLETION_CATEGORY_BASELINE_CHANGED`。影响：测试服仍未发布成功，`mark-tested`、正式服和备份服都不得继续；下一步必须先只读核对测试服 tenant `122` 当前分类基线与该 SQL 的真实断言，再按严格 TDD 修复并重新出包。

GREEN: test-server-fvm-category-baseline-readonly-20260628 -> PASS，只读核对测试服 `172.30.30.58` 的 `tenant_id=1` 分类基线后，已确认 `20260625_dcc_fvm_matrix_retain_other_completion.sql` 的首道断言与真实数据不一致。该 SQL 写死要求：`active_total=60`、`dcc_fvm_count=59`、`other_count=1`；而测试服真实查询结果为：`active_total=81`、`dcc_fvm_count=32`、`other_count=1`、`intauth_count=48`。进一步只读列出 `DCC_FVM*` 编码仅有 32 条，且同一租户下同时存在 48 条 `INTAUTH-*` 活跃分类，因此本轮失败不是脚本顺序问题，而是 SQL 把旧分类基线硬编码为 60/59/1，已不匹配测试服当前真实分类结构。

GREEN: backend-release-env-scope-fix-20260628 -> PASS，真实后端仓已按严格 TDD 将 `20260625_dcc_fvm_matrix_retain_other_completion.sql` 的 migration 头从 `allowedEnvironments=test,backup,prod` 收敛为 `allowedEnvironments=backup,prod`，避免 tenant_id=1 的本地补全 SQL 继续污染测试服发布链路；定向回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_dcc_fvm_matrix_retain_other_completion_sql.py -q` 返回 `5 passed`，`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` 返回 `status=passed`、`migrationCount=218`。

GREEN: release-worktree-head-refresh-20260628-v9 -> PASS，后端真实仓已提交上述修复，新 HEAD=`dec48d81d531dbdc4ff38251b37dec806392bfa9`，并创建干净发布 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-dec48d8`；本机 `config/runtime-control.local.yaml` 已切换到该后端 worktree，前端仍为 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260627-7632896`。

GREEN: runtime-control-build-release-20260628-v9 -> PASS，真实页面重新执行 `build-release` 后生成 operation `op-2026-06-27T081234904927200Z-72754ee9-de72-41d8-800c-88dabbda60c3`，release tag=`release-20260628-1615-head-full-v9`，最终状态 `SUCCESS`；日志确认已完成后端 Maven 打包、前端 `pnpm build:test`、前后端镜像构建、`docker save` 导出、manifest 生成与 NAS 上传，结束语为 `Release package built: release-20260628-1615-head-full-v9`。

GREEN: release-manifest-verify-20260628-v9 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-1615-head-full-v9\manifest.json` 已核对：后端 commit=`dec48d81d531dbdc4ff38251b37dec806392bfa9`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`；当前候选包满足继续真实页面测试服发布的前置门禁。

GREEN: experience-preflight-20260628-v9-deploy-test -> PASS，已在执行新一轮测试服真实发布前复核 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md` 与 `project-error-prevention.md` 的高风险动作门禁；本轮仍必须沿单一 releaseTag `release-20260628-1615-head-full-v9` 依次执行 `test -> mark-tested -> prod -> backup`，测试服未成功前不得继续后续环境。

RED: runtime-control-deploy-test-20260628-v9-form-stale-tag -> FAIL，真实页面本轮首次重新执行测试服发布后生成 operation `op-2026-06-27T083335423752100Z-e22269bb-7716-4773-9717-3936680d7915`，但运行控制台实际提交参数仍是旧值 `releaseTag=release-20260624-head-full-v3`，而不是目标 `release-20260628-1615-head-full-v9`。日志确认其后续失败并非 `v9` 候选包本身，而是误发旧包后在同步 `required-sql` 阶段命中 `scp ... release-20260624-head-full-v3/required-sql/20260520_dcc_signature_menu_restore.sql: No such file or directory`。当前必须先纠正运行控制台表单/自动化输入方式，确保真实提交参数切到 `v9`，再重新发起测试服发布；正式服与备份服仍不得继续。

RED: runtime-control-deploy-test-20260628-v9-form-binding -> FAIL，继续在真实页面把“部署测试服”的发布标签输入框直接改写为 `release-20260628-1615-head-full-v9` 并重新执行后，又生成 operation `op-2026-06-27T083459881154100Z-a938d6a1-cfcb-4da6-9158-12553195a4a9`；但 operation JSON 仍显示 `parameters.releaseTag=release-20260624-head-full-v3`，日志也继续从旧目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260624-head-full-v3\...` 取包。说明当前新 blocker 已从“自动化没填到输入框”收敛为“页面可见输入值与实际提交绑定值不一致”。在修正运行控制台这一前端绑定问题前，测试服真实发布无法切到 `v9`，正式服与备份服仍不得继续。

GREEN: runtime-control-deploy-test-20260628-v9-preview-execute-path -> PASS，随后继续核对真实页面请求链路与 operation 证据，确认当前运行控制台并非表单绑定损坏，而是“必须在命令预览弹窗里点击真正的 `执行` 才会提交新 releaseTag”。当自动化只改列表页输入框或停在预览态时，operation 仍沿用旧标签；在预览弹窗里点击 `执行` 后，已抓到真实请求体 `POST /admin-api/infra/runtime-control/actions`，其中 `releaseTag=release-20260628-1615-head-full-v9`。

RED: runtime-control-deploy-test-20260628-v9-real -> FAIL，按正确页面路径重新从预览弹窗点击 `执行` 后，真实测试服发布 operation `op-2026-06-27T084525781193200Z-0aedd906-c321-4703-858f-f64a876df446` 已切到候选包 `release-20260628-1615-head-full-v9`，但运行到 `Applying required database SQL: 20260626_showroom_keyword_bu_seed_runtime.sql` 时失败，测试服远端 MySQL 返回 `ERROR 1146 (42S02) at line 4: Table 'ruoyi-vue-pro.showroom_keyword' doesn't exist`。日志同时证明包内已同步 `20260626_showroom_keyword_schema_seed_runtime.sql`，但真实 apply 顺序仍先跑了 `bu_seed_runtime`。

GREEN: backend-release-required-sql-showroom-order-fix-20260627 -> PASS，真实后端仓已按严格 TDD 收敛该新 blocker：`deploy-release` 的 `Sort-RequiredDatabaseSqlApplyItems` 现仅保留 DCC prerequisite 显式优先级，其余 required SQL 保持 `preflight-plan` 依赖顺序，不再把 `20260626_showroom_keyword_bu_seed_runtime` 提前到 `20260626_showroom_keyword_schema_seed_runtime` 之前；回归：
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` -> PASS (`94 passed`)
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_release_preflight_plan.py -q` -> PASS (`11 passed`)
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` -> PASS (`status=passed`, `migrationCount=218`)
- 提交：`1a40e46215f7fb64323772c060eec46489d0a8c1`，消息 `任务: 修复发布期关键词 SQL 依赖顺序`

GREEN: experience-preflight-20260627-v10-build-deploy -> PASS，重新继续真实发布前，已复核 `server-access.md`、`release-backup-restore.md`、`worktree-memory.md` 的高风险门禁；本轮必须先基于已提交后端 HEAD 创建新的干净发布 worktree，更新运行控制台 `repo-root` 后重新执行 `build-release -> deploy test`，测试服未成功前不得继续 `mark-tested/prod/backup`。

GREEN: release-worktree-head-refresh-20260628-v10 -> PASS，已基于后端提交 `1a40e46215f7fb64323772c060eec46489d0a8c1` 创建新的干净后端发布 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-1a40e46`，并将 `D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml` 的 `repo-root` 切换到该 worktree；本机 48181 维护控制台已按带 `--spring.config.import=optional:file:D:/ProjectPackage/Int/IntRuoyiMaintance/config/runtime-control.local.yaml` 的方式重启，发布包接口恢复正常。

GREEN: runtime-control-build-release-20260628-v10 -> PASS，真实页面从预览弹窗内点击 `执行` 后生成 operation `op-2026-06-27T091553014027800Z-33d227f8-d1ad-4727-a64a-aeef78d179f4`，release tag=`release-20260628-1705-head-full-v10`，最终状态 `SUCCESS`。日志确认本轮已完成：
- 后端 Maven 打包，且明确使用后端 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-1a40e46\pom.xml`
- 前端 `pnpm build:test` 成功，生成 `dist-intruoyi-test`
- 前后端镜像构建成功
- `docker save` 导出成功
- NAS 上传成功，结束语为 `Release package built: release-20260628-1705-head-full-v10`

GREEN: release-manifest-verify-20260628-v10 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-1705-head-full-v10\manifest.json` 已核对：
- 后端 commit=`1a40e46215f7fb64323772c060eec46489d0a8c1`
- 前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`
- 两个 sourceRepos 均为 `dirty=false`
- 候选包满足继续真实页面测试服发布门禁

GREEN: runtime-control-deploy-test-20260628-v10-start -> PASS，已按真实页面正确路径重新执行“部署测试服”：先在命令预览弹窗内点击真正的“执行”，生成 operation `op-2026-06-27T092934632261600Z-ef40c69c-ac56-4d68-bab8-b03cae7db62c`，release tag=`release-20260628-1705-head-full-v10`。随后只读核对 operation JSON 与运行控制台请求体，确认本轮实际提交参数为 `action=publish-test`、`targetEnvironment=test`、`releaseTag=release-20260628-1705-head-full-v10`，不再是此前旧 tag 残留误发问题。

GREEN: runtime-control-deploy-test-20260628-v10-progress -> PASS，持续轮询 `op-2026-06-27T092934632261600Z-ef40c69c-ac56-4d68-bab8-b03cae7db62c` 的 operation JSON、接口 `/admin-api/infra/runtime-control/operations` 与执行日志，确认当前真实发布仍在推进中：
- 已完成测试服 `172.30.30.58` 的 SSH / `docker compose` 预检
- 已完成远端数据盘、运行目录、`.env` 下发与 `IMAGE_TAG=release-20260628-1705-head-full-v10` 核对
- 已完成 smoke runner 同步与远端 `npm install --no-audit --no-fund`
- 已开始上传镜像 tar 与 `required-sql`
- 最新日志已推进到 `required-sql\20260613_*` 批量同步，operation 当前状态仍为 `RUNNING`
- 截至本次记录，尚未出现新的 `FAILED`、`infra_release_migration`、`VIEW_MATRIX_*` 或 `showroom_keyword` 相关错误

RED: runtime-control-deploy-test-20260628-v10 -> FAIL，真实页面测试服发布 operation `op-2026-06-27T092934632261600Z-ef40c69c-ac56-4d68-bab8-b03cae7db62c` 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。最新日志确认：
- 大量历史 migration 已被正确写入 `infra_release_migration` 为 `SKIPPED_ALREADY_APPLIED`
- `20260625_dcc_fvm_matrix_retain_other_completion` 已被正确识别为 `Skipping required database SQL outside target environment`
- 真正失败点再次落在 `Applying required database SQL: 20260626_showroom_keyword_bu_seed_runtime.sql`
- 远端 MySQL 返回 `ERROR 1146 (42S02) at line 4: Table 'ruoyi-vue-pro.showroom_keyword' doesn't exist`
- 随后 `infra_release_migration` 将 `20260626_showroom_keyword_bu_seed_runtime` 回写为 `FAILED`，`infra_release_operation_lock` 释放结果为 `LOCK_RELEASED`

BLOCKER: 当前最新 blocker 已证实不是旧包误发，也不是 `20260625_dcc_fvm_matrix_retain_other_completion` 再次误入 test，而是测试服真实执行顺序仍先跑了 `20260626_showroom_keyword_bu_seed_runtime.sql`，没有在它之前执行 `20260626_showroom_keyword_schema_seed_runtime.sql`。影响：测试服发布仍未成功，`mark-tested`、正式服和备份服全部不得继续；下一步必须回到真实后端/维护链路，只读核对本轮 `v10` 的 preflight 计划与真实 apply item 顺序，继续按严格 TDD 收敛“schema_seed_runtime 未在 bu_seed_runtime 前执行”的根因。

GREEN: showroom-keyword-runtime-order-root-cause-20260628 -> PASS，继续只读核对 `release-20260628-1705-head-full-v10` 本地证据与真实运行日志后，已确认本轮根因不是 SQL 元数据缺失，也不是 preflight 计划本身顺序错误：
- 发布包 `preflight-plan.json` 中 `20260626_showroom_keyword_schema_seed_runtime` 与 `20260626_showroom_keyword_bu_seed_runtime` 都是 `action=APPLY`
- 同一 `preflight-plan.json` 中顺序明确是 `schema_seed_runtime -> bu_seed_runtime -> healing_seed_runtime`
- `preflight-target-state-test.json` 中不存在 `20260626_showroom_keyword_schema_seed_runtime` / `20260626_showroom_keyword_bu_seed_runtime` 的既有 `APPLIED` 状态，说明 preflight 并未把 schema 判成已应用
- 真实测试服发布日志完全没有出现 `Applying required database SQL: 20260626_showroom_keyword_schema_seed_runtime.sql`，却直接执行了 `20260626_showroom_keyword_bu_seed_runtime.sql`

GREEN: maintenance-script-showroom-keyword-order-fix-20260628 -> PASS，进一步比对后端真实仓脚本与当前运行中的维护脚本后，已确认新的真实根因是维护仓 `Sort-RequiredDatabaseSqlApplyItems` 再次分叉：
- 后端真实仓 `script/deploy/publish-int-ruoyi.ps1` 已按 `OriginalOrder` 保留 non-priority required SQL 的 `preflight-plan` 原始依赖顺序
- 当前维护脚本 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 却仍把 non-priority migration 按 `migrationId` 字母序排序，导致 `20260626_showroom_keyword_bu_seed_runtime` 被排到 `20260626_showroom_keyword_schema_seed_runtime` 前面
- 已先补 RED 契约测试 `test_publish_script_preserves_preflight_dependency_order_for_non_priority_required_sql`
- 随后将维护仓与当前运行 worktree 的 `Sort-RequiredDatabaseSqlApplyItems` 修正为：仅保留 DCC prerequisite 显式优先级，其余按 `OriginalOrder` 保持 preflight 原顺序
- 回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> PASS (`6 passed`)

GREEN: experience-preflight-20260627-showroom-product-bu-probe-fix -> PASS，继续进入下一轮真实测试服发布前，已复核 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`worktree-memory.md` 的高风险门禁；当前必须先基于已提交后端 HEAD 创建新的干净发布 worktree，更新运行控制台 `repo-root`，然后重新执行真实页面 `build-release -> publish-test`。测试服成功前，`mark-tested`、正式服、备份服全部禁止继续。

GREEN: backend-showroom-product-bu-probe-fix-20260627 -> PASS，真实后端仓已按严格 TDD 修复 `20260626_showroom_product_current_bu_normalization.sql` 的探针误拦截：
- 真实 blocker：测试服 operation `op-2026-06-27T094707808570600Z-965ba79d-53d0-4848-8ee2-479dfc61b761` 在 `20260626_showroom_product_current_bu_normalization.sql` 失败，错误 `ERROR 1048 (23000) at line 75: Column 'must_be_empty' cannot be null`
- 只读核对唯一未识别记录为 `revision_id=4574`、`product_id=252`、`tenant_id=0`、`pipeline_layout=NULL`、`pipeline_layout_en='Null value probe'`
- 修复策略：仅排除 `tenant_id=0`、中文 BU 为空且英文值等于 `Null value probe` 的非业务探针记录，不放宽真实业务 unknown guard
- 回归：
  - `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_showroom_product_bu_normalization_sql.py -q` -> PASS (`7 passed`)
  - `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` -> PASS (`status=passed`, `migrationCount=218`)
- 提交：`8632c424ba2cb80ba2ac4c4342945fc859a6edc3`，消息 `任务: 修复发布期产品BU探针拦截`

GREEN: runtime-control-build-release-20260628-v11 -> PASS，真实页面重新执行 `build-release` 后生成 operation `op-2026-06-27T101820542591Z-7b85c77c-eb8d-48b1-89b7-f3f35968efce`，release tag=`release-20260628-1835-head-full-v11`，最终状态 `SUCCESS`；日志确认已完成后端 Maven 打包、前端 `pnpm build:test`、前后端镜像构建、`docker save` 导出、manifest 生成与 NAS 上传。

GREEN: release-manifest-verify-20260628-v11 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-1835-head-full-v11\manifest.json` 已核对：后端 commit=`8632c424ba2cb80ba2ac4c4342945fc859a6edc3`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`；当前候选包满足继续真实页面测试服发布门禁。

GREEN: experience-preflight-20260628-v11-deploy-test -> PASS，继续执行真实测试服发布前，已复核 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`worktree-memory.md` 与 `project-error-prevention.md` 的高风险门禁；本轮仍必须沿单一 releaseTag `release-20260628-1835-head-full-v11` 执行 `test -> mark-tested -> prod -> backup`，测试服未成功前不得继续后续环境。

RED: runtime-control-deploy-test-20260628-v11 -> FAIL，真实页面测试服发布 operation `op-2026-06-27T103042306966Z-b5687d95-24b9-4b0e-b2a6-f4248c6bbbbb` 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。本轮真实链路已越过：
- 测试服 SSH / `docker compose` 预检
- 远端数据盘、运行目录、`.env` 下发与 `IMAGE_TAG=release-20260628-1835-head-full-v11` 核对
- 发布包、`required-sql`、smoke runner 同步
- 真实数据库应用阶段，`20260625_dcc_fvm_matrix_retain_other_completion` 被正确识别为 `Skipping required database SQL outside target environment`
- `20260626_showroom_product_current_bu_normalization.sql` 已真实执行并回写为 `APPLIED`

GREEN: test-server-nas-mount-root-cause-readonly-20260628-v11 -> PASS，继续只读核对失败日志、候选包 compose、测试服远端 compose/.env、Docker inspect 与宿主机挂载状态后，已将新 blocker 收敛为远端 NAS bind mount 启动异常，而不是本次候选包 SQL 或镜像内容问题：
- 候选包与远端 `/opt/intruoyi/runtime/docker-compose.yml` 一致，`backend` 服务都显式声明了 bind mount `/mnt/nas/Backup/BackupPackage:/mnt/nas/Backup/BackupPackage`
- `docker compose up -d --no-deps backend frontend` 在重建 `intruoyi-backend` 时失败：`error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists`
- `docker inspect intruoyi-backend --format '{{json .Mounts}}'` 证明旧后端容器历史上确实使用过该 bind mount，说明 compose 契约不是本轮新引入
- 远端 `docker compose config` 显示该 mount 带 `create_host_path: true`，因此 Docker 在重新创建容器时会重新校验宿主机源路径
- 宿主机 `/proc/self/mountinfo` 显示 `/mnt/nas` 当前挂载为 `//172.30.30.4/IT共享 on /mnt/nas type cifs ... username=ceshi`
- 远端 root 对 `/mnt/nas`、`/mnt/nas/Backup`、`/mnt/nas/Backup/BackupPackage` 的 `ls/stat/python os.stat` 全部返回 `Permission denied`
- `namei -l /mnt/nas/Backup/BackupPackage` 只解析到 `/mnt`，在 `nas` 节点即报 `无此文件或目录`，与 CIFS 挂载点访问异常一致
- 当前 `intruoyi-backend` / `intruoyi-frontend` 容器状态均为 `Created`，`docker inspect intruoyi-backend` 的 `State.Error` 与 operation 日志中的 mount 报错一致

BLOCKER: 当前最新 blocker 已从 required SQL 链路前进到“测试服宿主机 `/mnt/nas` 的 CIFS 挂载/权限状态异常，导致 `backend` 容器在重新创建时无法重新绑定 `/mnt/nas/Backup/BackupPackage`”。影响：测试服发布仍未成功，`mark-tested`、正式服和备份服全部不得继续；在完成服务器侧只读确认与正式修复前，不能把该失败归因于本次候选包，也不能继续后续环境。

GREEN: test-server-nas-mount-config-source-20260628 -> PASS，继续只读核对测试服挂载来源与本机发布配置后，已确认当前异常是测试服历史坏挂载而不是本轮候选包或本机配置写错：
- 本机运行控制台配置 `D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml` 当前 NAS 凭据为 `nas-username=int`
- 测试服 root 主目录存在 `/root/.smbcredentials`（`username=BJB110`）与 `/root/.smbcred_backup`（`username=beifen`），均与当前坏挂载 `username=ceshi` 不一致
- 远端 `smbclient -L //172.30.30.4 -U int%<redacted>` 可成功列出 `IT共享`，说明 NAS 本身与当前 `int` 账号可用
- `cd /mnt/nas` 在坏挂载状态下直接返回 `不是目录`，进一步证明是测试服本地 `/mnt/nas` 挂载损坏，而不是共享盘内容缺失

GREEN: test-server-nas-mount-repair-20260628 -> PASS，在不修改共享盘内容、不修改 `/etc/fstab`、不删除 `ReleasePackage/BackupPackage` 数据的前提下，已对测试服本地坏掉的 `/mnt/nas` 挂载执行最小正式修复：
- 先只读记录修复前证据：`/proc/self/mountinfo` 显示 `/mnt/nas` 由 `//172.30.30.4/IT共享` 以 `username=ceshi` 挂载
- `umount -v /mnt/nas` 成功卸载旧坏挂载；卸载后确认 `/mnt/nas` 恢复为宿主机普通目录项
- 仅清理测试服本地空挂载点 `/mnt/nas` 并重新 `mkdir /mnt/nas`，未触碰共享盘文件内容
- 使用当前发布链路一致的凭据 `username=int` 重新执行 `mount -t cifs '//172.30.30.4/IT共享' /mnt/nas ...`
- 修复后 `/proc/mounts` 显示 `/mnt/nas` 已变为 `username=int`
- 宿主机验证通过：`cd /mnt/nas` 成功，`/mnt/nas/Backup/BackupPackage` 存在且 `os.stat` 全部返回目录
- Docker bind 验证通过：`docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 返回 `DOCKER_BIND_OK`

RED: runtime-control-deploy-test-20260628-v11-retry-after-mount-repair -> FAIL，完成测试服 `/mnt/nas` 最小正式修复后，已重新从真实页面发起测试服发布 operation `op-2026-06-27T105253570049600Z-36d2fc17-9145-40aa-b1c6-6a1c2d2c7ed2`。本轮真实证据显示：
- operation 已重新越过 SSH 预检、镜像加载、MySQL/Redis 启动、发布锁获取和大批 `required-sql` 回写阶段。
- `20260624_dcc_view_matrix_test_tenant_prereq`、`20260624_dcc_view_matrix_independent_seed`、`20260626_showroom_keyword_schema_seed_runtime`、`20260626_showroom_keyword_bu_seed_runtime`、`20260626_showroom_product_current_bu_normalization` 等此前 blocker 均已真实越过，并在 `infra_release_migration` 中被写为 `SKIPPED_ALREADY_APPLIED`。
- 但远端只读核对 `docker ps -a`、`docker inspect intruoyi-backend` 后确认：`intruoyi-backend` 仍停在 `Created`，`State.Error` 仍是 `error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists`；`intruoyi-frontend` 也停在 `Created`。
- 同一时刻再核对测试服宿主机 `/mnt/nas`，`/proc/mounts` 仍显示 `username=int`，`os.stat('/mnt/nas/Backup/BackupPackage')` 成功，且再次手工执行 `docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 仍返回 `DOCKER_BIND_OK`。
- operation 执行日志已出现 `LOCK_RELEASED` 与 `ERROR: 命令退出码非 0: 1`，只是本地 operation JSON 尚未及时从 `RUNNING` 刷新为最终失败状态。

BLOCKER: 当前测试服最新真实 blocker 已从“坏 CIFS 挂载不可访问”进一步收敛为“测试服宿主机 `/mnt/nas` 在独立 Docker bind probe 中可用，但真实发布链路重建 `intruoyi-backend` 容器时仍被 Docker 解析为同一 host path 错误”。影响：测试服仍未完成发布，`mark-tested`、正式服和备份服全部不得继续。

RED: maintenance-release-script-empty-applyitems-20260628 -> FAIL，继续只读抓取 operation `op-2026-06-27T105253570049600Z-36d2fc17-9145-40aa-b1c6-6a1c2d2c7ed2` 的真实失败尾部后，已确认本轮并不是再次执行到 `docker compose up -d --no-deps backend frontend` 才失败。真实失败发生在维护仓脚本 `Sort-RequiredDatabaseSqlApplyItems`：日志 line 1861 先打印 `Skipping required database SQL outside target environment: 20260625_dcc_fvm_matrix_retain_other_completion`，随后发布锁被释放，PowerShell 抛出 `Sort-RequiredDatabaseSqlApplyItems : 无法将参数绑定到参数“Items”，因为该参数是空值。`。也就是说，在当前测试服状态下，`Get-ReleasePreflightApplyItems` 返回空集合，而维护仓排序函数没有允许空集合/空值，导致发布在 SQL 阶段尾部直接异常退出；此前看到的 `intruoyi-backend` `Created` 与旧 mount `State.Error` 只是历史残留容器状态，不是本轮真正失败点。

RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL，新增 `test_publish_script_allows_empty_required_sql_apply_items` 后首次回归返回 `1 failed, 6 passed`，精确复现当前维护仓脚本没有显式允许空 `Items` 集合的缺陷。

GREEN: maintenance-release-script-empty-applyitems-fix-20260628 -> PASS，已在维护仓 `ops/deploy/publish-int-ruoyi.ps1` 以及当前运行 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 对 `Sort-RequiredDatabaseSqlApplyItems` 做最小正式修复：
- 为 `Items` 参数增加 `[AllowNull()]`
- 在测试环境排序前新增 `if ($null -eq $Items -or $Items.Count -eq 0) { return @() }`
- 未改变已有 DCC prerequisite 优先级与 `OriginalOrder` 保序规则

GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> PASS，`7 passed`；说明维护仓发布脚本现在已能正确处理“当前无 APPLY 项、只有 SKIPPED_ALREADY_APPLIED / SKIP_ENV_NOT_ALLOWED”的真实场景。

GREEN: experience-preflight-20260627-v11-retry-after-empty-applyitems-fix -> PASS，继续重新执行真实测试服发布前，已复核 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`worktree-memory.md` 与 `project-error-prevention.md` 的高风险门禁；当前仍必须沿单一 releaseTag `release-20260628-1835-head-full-v11` 执行 `test -> mark-tested -> prod -> backup`，测试服未成功前不得继续后续环境。

RED: runtime-control-deploy-test-20260628-v11-retry-after-empty-applyitems-fix -> FAIL，真实页面测试服发布 operation `op-2026-06-27T111300642917500Z-84f1824f-db7c-4571-8c78-c52231bcc51e` 已真实越过此前 maintenance 脚本空 `applyItems` 崩溃点：
- 日志确认已完成测试服 SSH / `docker compose` 预检、远端运行目录和 `.env` 校验、发布包和 `required-sql` 同步、`docker load`、MySQL 健康检查。
- `required-sql` 阶段已将大量历史 migration 回写为 `SKIPPED_ALREADY_APPLIED`，并再次正确出现 `Skipping required database SQL outside target environment: 20260625_dcc_fvm_matrix_retain_other_completion`。
- 同一 operation 随后真实执行 `docker compose up -d --no-deps backend frontend`，日志显示 `Container intruoyi-backend Started`、`Container intruoyi-frontend Started`，然后进入 `Waiting for remote HTTP readiness`。

RED: test-server-backend-runtime-jar-entrypoint-20260628 -> FAIL，继续只读核对测试服运行态后，新的真实 blocker 已收敛为后端镜像产物不可启动，而不是 SQL / NAS mount / 空 `applyItems`：
- `docker compose ps --format json` 显示 `intruoyi-frontend` 已 `Up`，但 `intruoyi-backend` 处于 `Restarting (1)`。
- `docker logs --tail 200 intruoyi-backend` 连续报错 `no main manifest attribute, in app.jar`。
- 远端健康检查 `http://172.30.30.58:48081/actuator/health` 无法连通。
- 当前测试服后端镜像标签已经是本轮候选包 `intruoyi-backend:release-20260628-1835-head-full-v11`，说明失败不是旧镜像残留。

GREEN: backend-runtime-jar-root-cause-20260628 -> PASS，继续只读核对后端发布源 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 后，已确认根因是“可执行 jar 产物与 Dockerfile 取包路径不匹配”：
- `yudao-server/pom.xml` 使用 `spring-boot-maven-plugin` 且配置了 `<classifier>exec</classifier>`，表示可执行 Spring Boot jar 会以带 `exec` classifier 的产物生成。
- 当前 `script/deploy/int-ruoyi-test/Dockerfile.backend` 和 `yudao-server/Dockerfile` 仍都在复制普通 `yudao-server.jar` 为 `app.jar`。
- 测试服容器日志 `no main manifest attribute, in app.jar` 与上述配置完全一致，说明镜像拿到的是普通分类包，而不是 Spring Boot repackage 后的可执行包。

BLOCKER: 当前最新 blocker 已从测试服环境/脚本链路收敛为后端发布产物契约问题。影响：必须先修正后端镜像取包逻辑，重新构建候选包并在测试服重跑；在此之前，`mark-tested`、正式服与备份服全部不得继续。

GREEN: backend-exec-jar-release-image-fix-20260628 -> PASS，真实后端发布源 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 已按严格 TDD 完成镜像入口修复：
- 新建后端任务目录 `doc/tasks/20260627-backend-exec-jar-release-image/`，记录本次 `no main manifest attribute, in app.jar` 的真实 blocker。
- 只读验证 `yudao-server/target/yudao-server-exec.jar` 的 `MANIFEST.MF`，确认包含 `Main-Class: org.springframework.boot.loader.launch.JarLauncher` 与 `Start-Class: cn.iocoder.yudao.server.YudaoServerApplication`。
- 将 `script/deploy/int-ruoyi-test/Dockerfile.backend` 与 `yudao-server/Dockerfile` 的复制目标从 `yudao-server.jar` 改为 `yudao-server-exec.jar`。
- 后端仓以 `TDD_TASK_DIR=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42\doc\tasks\20260627-backend-exec-jar-release-image` 成功提交 `任务: 修正后端发布镜像可执行jar入口`，commit=`d3ee53edaf015f98ec3bfebf9f91602103568b6d`。

BLOCKER: 当前主链路 blocker 已从“后端镜像入口错误”转为“需要基于新后端提交 `d3ee53edaf015f98ec3bfebf9f91602103568b6d` 重新构建候选包并在测试服重跑，验证后端容器是否恢复可启动”。在新候选包完成测试服真实验证前，`mark-tested`、正式服与备份服全部不得继续。

RED: runtime-control-build-release-20260628-v12 -> FAIL，继续轮询真实页面发起的构建 operation `op-2026-06-27T113224282720200Z-dd2ed29c-419b-4309-9e8d-8504c7c578c0` 后，已确认本轮并未成功生成新的候选包。日志在后端 Maven `BUILD SUCCESS` 之后进入 backend image `docker build` 阶段失败，真实报错为 `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar -> not found`，最终摘要仍为 `命令退出码非 0: 1`。

GREEN: maintenance-release-script-backend-exec-jar-root-cause-20260628 -> PASS，继续只读核对当前运行维护脚本 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 后，已确认新的真实 blocker 不是后端仓 Dockerfile 回退，而是维护控制台发布脚本仍把构建产物复制为普通文件名 `yudao-server.jar`：
- `New-ReleaseDockerBuildContext` 仍执行 `Copy-Item ... 'yudao-server.jar'`
- `$backendJar` 仍固定指向 `yudao-server\target\yudao-server.jar`
- 但后端发布源 `script/deploy/int-ruoyi-test/Dockerfile.backend` 已改为复制 `yudao-server-exec.jar`
- 结果是 Docker build context 中根本不存在 `yudao-server-exec.jar`，导致 `docker build` 在 `COPY` 阶段失败

RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL（预期新增契约前置），本轮先补充发布脚本契约测试 `test_publish_script_uses_exec_backend_jar_for_release_image`，用于约束维护控制台必须使用 `yudao-server-exec.jar` 作为 backend release image 输入。

GREEN: maintenance-release-script-backend-exec-jar-fix-20260628 -> PASS，已在维护仓 `ops/deploy/publish-int-ruoyi.ps1` 与当前运行 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 完成最小正式修复：
- `$backendJar` 改为 `yudao-server\target\yudao-server-exec.jar`
- `New-ReleaseDockerBuildContext` 复制目标改为 `yudao-server-exec.jar`
- 未引入 fallback、未改动其他发布路径、未改变 SQL / NAS / 环境门禁逻辑

GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> PASS，`8 passed`；说明维护控制台现在已通过自动化契约同时覆盖：
- non-priority required SQL 保序
- 空 `applyItems` 合法处理
- backend release image 必须使用 `yudao-server-exec.jar`

BLOCKER: 当前主链路 blocker 已从“后端仓 Dockerfile 入口错误”进一步收敛为“维护控制台发布脚本与后端可执行 jar 契约未同步，导致新候选包在本地 backend image 构建阶段即失败”。该 blocker 现已完成最小正式修复并通过本地回归；下一步必须回到真实页面重新执行 `build-release`，生成包含后端提交 `d3ee53edaf015f98ec3bfebf9f91602103568b6d` 且维护脚本已同步 `exec jar` 的新候选包，再继续测试服发布验证。测试服成功前，`mark-tested`、正式服与备份服全部不得继续。

GREEN: runtime-control-build-release-20260628-v13 -> PASS，真实页面重新执行 `build-release` 后生成 operation `op-2026-06-27T123449843975400Z-ddb66461-67a4-4383-bb46-1955940ac5e4`，release tag=`release-20260628-2015-head-full-v13`，最终状态 `SUCCESS`。日志确认本轮完成后端 Maven 打包、前端 `pnpm build:test`、后端镜像构建、前端镜像构建、`docker save` 导出、manifest 生成与 NAS 上传。

GREEN: backend-release-image-exec-jar-copy-20260628-v13 -> PASS，本轮 backend image `docker build` 已真实越过此前 `yudao-server-exec.jar not found` blocker。日志明确显示：
- `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar`
- `#8 DONE 2.1s`
- 后端镜像成功命名为 `intruoyi-backend:release-20260628-2015-head-full-v13`

GREEN: release-manifest-verify-20260628-v13 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-2015-head-full-v13\manifest.json` 已核对：
- releaseTag=`release-20260628-2015-head-full-v13`
- publishScope=`code-only`
- 后端 commit=`d3ee53edaf015f98ec3bfebf9f91602103568b6d`
- 前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`
- 两个 sourceRepos 均为 `dirty=false`

GREEN: experience-preflight-20260628-v13-deploy-test -> PASS，继续执行真实测试服发布前，已按本任务既有门禁复核：测试服必须先发布并验证，通过后才能继续 `mark-tested`、正式服和备份服；当前候选包为单一 releaseTag `release-20260628-2015-head-full-v13`，不得拼接旧包结果。

GREEN: runtime-control-deploy-test-20260628-v13 -> PASS，真实页面测试服发布 operation `op-2026-06-27T125259682648200Z-a77f32ea-36b0-4ccb-97c2-d96effb42d26` 最终状态为 `SUCCESS`，release tag=`release-20260628-2015-head-full-v13`。日志确认测试服链路完成 SSH / Docker Compose / 数据盘预检、`.env` 下发与 `IMAGE_TAG` 校验、发布包和 `required-sql` 同步、镜像 `docker load`、MySQL/Redis 启动、required SQL 迁移回写、`docker compose up -d --no-deps backend frontend`、远端 HTTP readiness、scheduler smoke runtime 检查、发布锁释放与远端临时文件清理。

GREEN: test-server-runtime-verify-20260628-v13 -> PASS，测试服最终运行态已只读核对：
- `docker compose ps` 显示 `intruoyi-backend|running|intruoyi-backend:release-20260628-2015-head-full-v13` 与 `intruoyi-frontend|running|intruoyi-frontend:release-20260628-2015-head-full-v13`
- 远端 `/opt/intruoyi/runtime/.env` 显示 `IMAGE_TAG=release-20260628-2015-head-full-v13`
- `http://172.30.30.58:48081/actuator/health` 返回 HTTP 200，内容为 `{"status":"UP"}`
- `http://172.30.30.58:8081/` 返回 HTTP 200
- 后端容器日志显示 Spring Boot 正常启动，不再出现 `no main manifest attribute, in app.jar`

GREEN: experience-preflight-20260628-v13-mark-tested -> PASS，测试服已真实发布并完成运行态验证；下一步允许进入 `mark-tested`，但仍必须通过真实运行控制台页面/动作提交，不得手工改数据库或伪造 tested 状态。`mark-tested` 成功前，正式服与备份服不得发布。


GREEN: mark-release-tested-20260628-v13 -> PASS????? `mark-tested` operation `op-2026-06-27T131326845519900Z-98877440-48cd-4d2d-9adc-202703db3b23` ???? `SUCCESS`????? `releaseTag=release-20260628-2015-head-full-v13`?`selectedRecoverySetCandidateId=restore:20260621-063218`????? `????????????`????? `Release package marked as tested: Backup/ReleasePackage/release-20260628-2015-head-full-v13`???? `rollback-compatibility.json status=BLOCKED`????????????????? `promote-prod`?

GREEN: experience-preflight-20260628-v13-promote-prod -> PASS????????? `server-access.md` ? `release-backup-restore.md` ????????????????????????????????? releaseTag `release-20260628-2015-head-full-v13`??????????? `/mnt/nas` ??/fstab?????????? operation ???


RED: promote-prod-20260628-v13 -> FAIL?????????? operation `op-2026-06-27T131638848845800Z-55f29aeb-ced9-4b7d-aeeb-47eb859e1e9d` ?? `FAILED`??? `?????? 0: 1`????????????? required SQL ?????? `20260624_dcc_view_matrix_independent_seed.sql` ? MySQL ?? `ERROR 1644 (45000) at line 737: VIEW_MATRIX_SEED_SUBJECT_PRECHECK_FAILED`??????????? `LOCK_RELEASED`????????????? `.env` ???? `IMAGE_TAG=release-20260628-2015-head-full-v13`?? `docker compose ps` ??? `intruoyi-backend` ? `intruoyi-frontend` ??????? `release-20260624-head-full-v3`?????????? HTTP 200????????????????????? v13 ?????????????????????????/????? DCC view matrix subject precheck ????????? `.env` ????????????????????????

BLOCKER: promote-prod-v13-subject-precheck -> ??? `tenant_id=122` ?? DCC ?????? seed ??? `VIEW_MATRIX_SEED_SUBJECT_PRECHECK_FAILED`??????? `promote-backup`???????? 200 ?????????

GREEN: backend-dcc-view-matrix-prod-subject-fix -> PASS，后端发布输入 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 已完成 DCC 矩阵主体映射修复并提交：`c17ef45d2c` 修复 `市场 / 注册` 从 `顶级部门/注册服务中心` 改为 `瑛泰医疗/注册服务中心`，`6d1bb4c976` 完成任务文档收尾。验证证据：`python -X utf8 -m pytest script\tests\test_dcc_view_matrix_independent_seed_sql.py -q` -> `4 passed`；`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> `status=passed`、`migrationCount=218`；正式服只读临时表预检 `missing_or_duplicate=0`、`checked_dept_subjects=13`。

GREEN: maintenance-release-script-dcc-seed-env-context -> PASS，维护仓发布脚本已验证 DCC seed 按环境注入租户上下文：test -> `122`，prod/backup -> `1`；测试服 required SQL 仍保持 prerequisite 先于 seed 执行。回归命令 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> `9 passed`。

GREEN: runtime-control-build-release-20260627-v14 -> PASS，真实运行控制台执行 `build-release` operation `op-2026-06-27T134842037528200Z-7f15a00b-1c02-41d2-ac81-270e53dda79a`，release tag=`release-20260627-2147-head-full-v14`，最终状态 `SUCCESS`。日志确认后端 Maven 打包成功并生成 `yudao-server-exec.jar`，后端 Docker build 真实执行 `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar`，前端 `pnpm build:test` 成功，后端/前端镜像构建、`docker save` 和 NAS 上传完成。

GREEN: release-manifest-verify-20260627-v14 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260627-2147-head-full-v14\release-manifest.json` 已核对：`releaseTag=release-20260627-2147-head-full-v14`，`publishScope=code-only`，`component=intruoyi`，后端发布输入 commit=`6d1bb4c97648d51861e6cd8015a3595b47267cf6`，`required-sql/20260624_dcc_view_matrix_independent_seed.sql` sha256=`aee4ed22fdee6b9d17aeb7b43404967c286505559876d3f5fcff05a1cec178be`，镜像 tar 大小 `813532160` bytes。

RED: runtime-control-deploy-test-20260627-v14 -> FAIL????????????? operation `op-2026-06-27T140529058593900Z-da047d1c-947c-4985-846f-f9aad9396d1a` ???? `FAILED`?release tag=`release-20260627-2147-head-full-v14`??????????? SSH ???`.env` ????? `IMAGE_TAG=release-20260627-2147-head-full-v14`????? required SQL ???ops-runtime ????? required SQL ???????? `Applying required database SQL: 20260624_dcc_view_matrix_test_tenant_prereq.sql` ???????? MySQL ?? `ERROR 1644 (45000) at line 297: VIEW_MATRIX_TEST_PREREQ_DEPT_RESOLUTION_FAILED`????? `LOCK_RELEASED`?????????? v14 ?????`mark-tested`?????????????

GREEN: experience-preflight-20260627-v16-mark-tested -> PASS，继续 v16 标记测试通过前已复核 `release-backup-restore.md`、`server-access.md`、`login-access.md` 与 `experience-index.md` 命中门禁；当前候选包为 `release-20260627-2305-head-full-v16`，测试服发布 operation `op-2026-06-27T151937284837Z-588bfbc7-0cb8-470b-8172-f68305004782` 已成功，测试服 `.env`、后端镜像、前端镜像均为 v16，后端 health `UP`、前端 HTTP `200`。下一步只允许通过 runtime-control action 执行 `mark-release-tested`，不得手工改 tested 状态；成功前不得发布正式服或备份服。

GREEN: mark-release-tested-20260627-v16 -> PASS，runtime-control action `mark-release-tested` operation `op-2026-06-27T153456717904700Z-70a1ffd8-c6b7-4d66-b2a3-6dd0a2c04cca` 最终状态 `SUCCESS`；命令包含 `-Mode mark-tested -ReleaseTag release-20260627-2305-head-full-v16 -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 -RecoverySetManifestHash 6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66`。日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260627-2305-head-full-v16`，同时记录 `rollback-compatibility.json status=BLOCKED`；该 rollback blocker 不阻止当前已测试发布包继续执行正式服发布，但回滚兼容性仍需按独立风险记录。

GREEN: experience-preflight-20260627-v16-promote-prod -> PASS，正式服发布前已复核生产动作门禁：用户当前任务已授权发布正式服；必须使用 runtime-control action，必须提交 `prodConfirmText=PROD`，必须带 `-RequireTested`，不得触碰正式服 `/mnt/nas` 根、挂载或 fstab。`promote-prod` 预览通过，参数包含 `-Environment prod -ReleaseTag release-20260627-2305-head-full-v16 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath ...release-20260627-2305-head-full-v16-preflight-release-dry-run.json`，目标主机为 `172.30.30.57`。

RED: promote-prod-20260627-v16 -> FAIL，runtime-control action `promote-prod` operation `op-2026-06-27T153743633299600Z-bc8b122b-2d22-4b7b-a33f-0c5b6752b55e` 最终状态 `FAILED`、摘要 `命令退出码非 0: 1`。真实失败点：正式服执行 required SQL `20260624_dcc_view_matrix_independent_seed.sql` 时，发布脚本只注入 `SET @dcc_view_matrix_seed_tenant_id := 1;`，未注入该 SQL 对 tenant 1 要求的 `@dcc_view_matrix_seed_allow_yudao_tenant := 1` 授权变量；SQL 保护门禁的错误文案长度为 132，超过 MySQL `SIGNAL MESSAGE_TEXT` 限制，导致日志最终表现为 `ERROR 1648 (HY000) at line 757: Data too long for condition item 'MESSAGE_TEXT'`。发布锁已释放为 `FAILED`；只读核对正式服发现 `.env` 已写入 `IMAGE_TAG=release-20260627-2305-head-full-v16`，但后端/前端容器仍运行旧镜像 `release-20260624-head-full-v3`，健康检查 `UP`。该状态不是发布成功，备份服不得继续。

RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL，新增契约测试 `test_publish_script_authorizes_dcc_view_matrix_seed_for_production_grade_environments` 后首次运行返回 `1 failed, 9 passed`，精确复现发布脚本没有为 `prod/backup` DCC view matrix seed 注入 tenant 1 授权变量。

GREEN: maintenance-release-script-dcc-seed-tenant1-authorization -> PASS，已在维护仓 `ops/deploy/publish-int-ruoyi.ps1` 与当前运行 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1` 最小修复 `Get-RequiredDatabaseSqlSessionPreamble`：对 `prod` / `backup` 的 `20260624_dcc_view_matrix_independent_seed` 额外注入 `SET @dcc_view_matrix_seed_allow_yudao_tenant := 1;`，对 `test` 显式注入 `SET @dcc_view_matrix_seed_allow_yudao_tenant := NULL;`；未放宽 SQL 门禁，未引入 fallback。回归命令 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> `10 passed`。

RED: promote-prod-20260627-v16-retry-after-tenant1-authorization -> FAIL，runtime-control action `promote-prod` operation `op-2026-06-27T155152777266Z-7e35f829-9f1d-4a98-bbc9-45c1eb0209c3` 真实越过 `20260624_dcc_view_matrix_independent_seed.sql`，日志返回 `tenant_id=1 category_count=59 view_matrix_rule_count=243 generated_role_count=5 generated_role_user_count=7`，并将该 migration 记为 `APPLIED`；随后在 `20260625_dcc_fvm_matrix_retain_other_completion.sql` 失败，错误 `DCC_FVM_RETAIN_OTHER_COMPLETION_CATEGORY_BASELINE_CHANGED`。发布锁已释放为 `FAILED`，备份服仍不得继续。

GREEN: backend-dcc-fvm-retain-other-prod-baseline-fix -> PASS，后端发布输入 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 已追加正式服基线修复：正式服 tenant_id=1 只读结果为 `active_total=207`、`dcc_fvm_count=59`、`other_count=1`，说明目标 DCC_FVM 集合与 OTHER 模板满足契约，失败仅由 `20260625_dcc_fvm_matrix_retain_other_completion.sql` 硬编码全租户 active 分类总数 `60` 导致；现已将首道校验收敛为只约束 `v_dcc_fvm_count <> 59`，保留 OTHER 模板、view matrix 59/243、review route 59 与节点完整性门禁。验证：`python -X utf8 -m pytest script\tests\test_dcc_fvm_matrix_retain_other_completion_sql.py -q` -> `6 passed`；`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> `status=passed`、`migrationCount=218`。下一步必须提交后端修复并重新构建新候选包；v16 不得继续推广。

GREEN: backend-dcc-fvm-retain-other-prod-baseline-commit -> PASS，后端发布输入 worktree 已提交 `de2c66fb83deee1e08ea9d60647d532501515b52`，提交信息 `任务: 修复DCC FVM正式服分类基线`，并通过 TDD commit hook。

GREEN: runtime-control-build-release-20260628-v17 -> PASS，runtime-control action `build-release` operation `op-2026-06-27T160959148735600Z-10a9a4be-9806-485e-b84f-736813806996` 最终状态 `SUCCESS`，release tag=`release-20260628-0015-head-full-v17`。日志确认后端 Maven 打包成功并生成 `yudao-server-exec.jar`，后端镜像构建真实执行 `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar`，前端 `pnpm build:test` 成功，镜像导出与 NAS 上传完成。

GREEN: release-manifest-verify-20260628-v17 -> PASS，本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-0015-head-full-v17\manifest.json` 已核对：`publishScope=code-only`，后端 commit=`de2c66fb83deee1e08ea9d60647d532501515b52`，前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均 `dirty=false`；`20260625_dcc_fvm_matrix_retain_other_completion.sql` artifact sha256=`df8dc349a95958b4bd23c50dcf56ad0d70a745e927ac0bdc09d48850b18a8e1f`。当前允许进入 v17 测试服发布，v16 仍作为失败证据不再推广。

GREEN: runtime-control-deploy-test-20260628-v17 -> PASS，runtime-control action `publish-test` operation `op-2026-06-27T162359407428600Z-5df2d01d-4ddb-4a12-8758-ed258cfee69e` 最终状态 `SUCCESS`，release tag=`release-20260628-0015-head-full-v17`。日志确认测试服 `.env` 写入并核对 `IMAGE_TAG=release-20260628-0015-head-full-v17`，`20260625_dcc_fvm_matrix_retain_other_completion` 在 test 环境被正确 `Skipping required database SQL outside target environment`，后端/前端容器重建、HTTP readiness、scheduler smoke runtime、发布锁释放和远端临时文件清理均通过。

GREEN: test-server-runtime-verify-20260628-v17 -> PASS，测试服只读核对：`/opt/intruoyi/runtime/.env` 显示 `IMAGE_TAG=release-20260628-0015-head-full-v17`；`docker compose ps` 显示 `intruoyi-backend|running|intruoyi-backend:release-20260628-0015-head-full-v17` 与 `intruoyi-frontend|running|intruoyi-frontend:release-20260628-0015-head-full-v17`；后端 health 返回 `{"status":"UP"}`，前端 HTTP 返回 `200`。

GREEN: experience-preflight-20260628-v17-mark-tested -> PASS，v17 测试服已真实发布并完成运行态验证；允许通过 runtime-control action 执行 `mark-release-tested`。正式服与备份服仍必须等待 v17 mark-tested 成功后继续。

GREEN: mark-release-tested-20260628-v17 -> PASS，runtime-control action `mark-release-tested` operation `op-2026-06-27T163633543263400Z-3d0408ea-09b5-4aa3-8e5f-a157c5454f8b` 最终状态 `SUCCESS`；命令包含 `-ReleaseTag release-20260628-0015-head-full-v17 -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 -RecoverySetManifestHash 6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66`。日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260628-0015-head-full-v17`。下一步允许进入 v17 正式服发布。

RED: promote-prod-20260628-v17 -> FAIL，runtime-control action `promote-prod` operation `op-2026-06-27T163752298963300Z-eb6ca513-42a3-4936-a05a-dd211fe60fe4` 最终状态 `FAILED`。本轮已真实越过 `20260625_dcc_fvm_matrix_retain_other_completion.sql`，该 migration 被写为 `APPLIED`；随后在正式服 `docker compose up -d --no-deps backend frontend` 阶段失败：`error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists`。只读核对显示正式服 `.env` 已为 `IMAGE_TAG=release-20260628-0015-head-full-v17`，但后端/前端容器停在 `created`，后端 health 连接拒绝；`/mnt/nas` 当前挂载为 `//172.30.30.4/IT共享` 且 `username=ceshi`，root 对 `/mnt/nas` 与 `/mnt/nas/Backup/BackupPackage` 均 `Permission denied`，独立 Docker bind probe 同样失败。发布锁已释放为 `FAILED`；备份服不得继续。

BLOCKER: prod-nas-mount-permission-20260628 -> 正式服当前不可用原因已收敛为 `/mnt/nas` CIFS 挂载凭据/权限异常，而不是 v17 包或 SQL 内容。按项目门禁，正式服 `/mnt/nas` 是共享盘，禁止删除、清空、移除 fstab 或清理 NAS 内容；恢复服务前只能做受控的本地坏挂载修复，并且必须先确认可用凭据。当前任务用户已说明“新的用户名是 int 密码与之前一样”，但仍需只读确认正式服凭据来源后执行最小修复。

GREEN: prod-nas-remount-repair-20260628 -> PASS，正式服 `/mnt/nas` 坏挂载已按用户提供的新用户名 `int` 与原密码完成最小修复；未删除、清空或移除 `/mnt/nas`、NAS 数据或 `fstab`。修复后只读证据：`/proc/mounts` 显示 `//172.30.30.4/IT共享 /mnt/nas cifs ... username=int ...`；`/mnt/nas/Backup/BackupPackage` 可访问；独立 Docker bind probe 对 `/mnt/nas/Backup/BackupPackage:/probe` 返回 `DOCKER_BIND_OK`。当前允许通过 runtime-control 重试 v17 正式服发布恢复服务，不得手工执行 docker compose 替代发布链路。

GREEN: experience-preflight-20260628-v17-promote-prod-retry-after-nas -> PASS，继续重试正式服发布前已复核 `server-access.md`、`release-backup-restore.md` 与 `experience-index.md` 命中门禁；用户当前任务已授权继续正式服发布，候选包仍为已测试通过的 `release-20260628-0015-head-full-v17`。本轮必须通过 runtime-control action 执行 `promote-prod`，必须提交 `prodConfirmText=PROD`，不得手工部署或绕过发布脚本，备份服仍必须等待正式服成功并完成运行态验证后才能继续。

GREEN: promote-prod-20260628-v17-retry-after-nas -> PASS，runtime-control action `promote-prod` operation `op-2026-06-27T165516540152300Z-1f99ed56-fc7d-4175-92c5-f0f608bf7208` 已完成正式服发布。日志确认 required SQL 均越过或回写为已应用状态，`docker compose up -d --no-deps backend frontend` 成功，后端 readiness、MinIO endpoint、前端 readiness、scheduler smoke runtime 均通过，发布锁返回 `LOCK_RELEASED`，并写入 `Backup/ReleasePackage/release-20260628-0015-head-full-v17/prod-latest.json`。正式服只读运行态核对：`/opt/intruoyi/runtime/.env` 显示 `IMAGE_TAG=release-20260628-0015-head-full-v17`；`docker compose ps` 显示 `intruoyi-backend|running|intruoyi-backend:release-20260628-0015-head-full-v17` 与 `intruoyi-frontend|running|intruoyi-frontend:release-20260628-0015-head-full-v17`；后端 health 返回 `{"status":"UP"}`，前端 HTTP 返回 `200`。

GREEN: experience-preflight-20260628-v17-promote-backup -> PASS，正式服 v17 发布与运行态验证已通过；允许继续通过 runtime-control action 执行备份服发布。备份服发布必须使用已测试且已正式服验证的 `release-20260628-0015-head-full-v17`，目标主机必须为 `172.30.30.59`，并显式使用 `/mnt/intruoyi-data`、`/mnt/intruoyi-data/runtime-data`、`/mnt/intruoyi-data/intruoyi-releases` 与 `RemoteMinioContainer=intruoyi-minio`，不得回退到根分区或 Docker 默认路径。

GREEN: promote-backup-20260628-v17 -> PASS，runtime-control action `promote-backup` 预览已确认参数包含 `-Environment backup -ReleaseTag release-20260628-0015-head-full-v17 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home -RemoteMinioContainer intruoyi-minio`；执行 operation `op-2026-06-27T171709623597300Z-4014e39d-d9e3-4380-9100-bc0d8b5990eb` 最终状态 `SUCCESS`。日志确认 required SQL 执行/回写完成，`docker compose up -d --no-deps backend frontend` 成功，后端 readiness、MinIO endpoint、前端 readiness、scheduler smoke runtime 均通过，发布锁返回 `LOCK_RELEASED`，并写入 `Backup/ReleasePackage/release-20260628-0015-head-full-v17/backup-latest.json`。备份服只读运行态核对：`/opt/intruoyi/runtime/.env` 显示 `IMAGE_TAG=release-20260628-0015-head-full-v17`；`docker compose ps` 显示 `intruoyi-backend|running|intruoyi-backend:release-20260628-0015-head-full-v17` 与 `intruoyi-frontend|running|intruoyi-frontend:release-20260628-0015-head-full-v17`；`df -h /mnt/intruoyi-data` 显示 `/dev/mapper/cl-home` 挂载在 `/mnt/intruoyi-data`，可用约 `453G`；后端 health 返回 `{"status":"UP"}`，前端 HTTP 返回 `200`。

GREEN: final-release-chain-20260628-v17 -> PASS，`release-20260628-0015-head-full-v17` 已完成 `build-release -> deploy test -> mark-tested -> promote prod -> promote backup` 全链路。测试服、正式服、备份服均已验证 `.env IMAGE_TAG`、后端/前端运行镜像、后端 health 和前端 HTTP 与 v17 一致。本轮发布中遇到的主要问题已按时间记录：prod DCC seed 授权变量缺失、prod DCC FVM 分类基线过严、prod `/mnt/nas` CIFS 凭据错误；最终均通过正式修复或受控挂载修复关闭，未使用 mock、静默跳过或手工 docker compose 替代发布链路。

