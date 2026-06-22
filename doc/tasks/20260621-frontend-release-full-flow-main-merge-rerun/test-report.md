# Test Report

## 2026-06-21 Initial Gate

- task id or phase id: `T1`
- tested cases: `TC-01`
- actual result: 已建立本轮任务目录，锁定当前主程序前后端与维护仓基线，并确认运行控制台与 `npx` 可用。
- expected result: 可以进入 `experience-preflight` 与真实页面预检。
- pass or fail: `PASS`
- evidence: `task.md`、`request-analysis.md`、`execution-log.md`
- blockers: 无
- unresolved issues: 待继续执行 `experience-preflight` 与真实页面链路。

## 2026-06-21 Build Gate

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 首次页面构建先因前端缺失 `@babel/helper-validator-identifier` 失败，已按执行日志记录后修复依赖现场并停止锁目录的同仓 Vite 进程；随后使用新标签 `release-20260621-page-full-flow-mainmerge-v2` 重新通过真实页面执行 `build-release`，operation `op-2026-06-21T143638404569500Z-2de68197-2e9d-41fb-8c28-8115bdca2325` 最终 `SUCCESS`，候选目录产物与 NAS 发布目录均存在。
- expected result: 页面构建发布包成功，且 `manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录齐备。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-operation-v2`，本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v2\`，运行态日志 `runtime\runtime-control\logs\op-2026-06-21T143638404569500Z-2de68197-2e9d-41fb-8c28-8115bdca2325.log`
- blockers: 已清除前端依赖损坏与本地 Vite 目录占用。
- unresolved issues: 待继续执行测试服、正式服、备份服真实页面链路。

## 2026-06-21 Deploy-Test Gate Attempt 1

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 真实页面触发测试服部署后，operation `op-2026-06-21T145341175255100Z-0de12b04-2650-49e2-a088-47dfa4f2b7ed` 最终 `FAILED`；日志显示远端在应用 `20260619_mes_edhr_deployment_license_interface.sql` 时抛出 `ERROR 1644 (45000) at line 299: Invalid eDHR deployment page menu definition; cannot merge tenant package menu_ids`。
- expected result: 页面部署测试服成功，测试服完成本轮候选包与 required-sql 应用，可继续进入“标记测试通过”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `deploy-test-operation-v1`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-21T145341175255100Z-0de12b04-2650-49e2-a088-47dfa4f2b7ed.log`
- blockers: 当前主程序基线下 `20260619_mes_edhr_deployment_license_interface.sql` 的菜单定义/合并逻辑与测试服真实库不兼容。
- unresolved issues: 必须先修复 SQL 根因，重新构建新 `releaseTag`，再从页面重跑 build/test/prod/backup 全链路。

## 2026-06-21 Build Gate Retry v3

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 `20260619_mes_edhr_deployment_license_interface.sql` 菜单 ID 冲突根因按严格 TDD 修复后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v3` 执行 `build-release`，operation `op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209` 最终 `SUCCESS`；本地候选目录与 NAS 发布目录均已重新生成，`manifest.json` 的 `releaseTag` 已核对一致。
- expected result: SQL 修复后的新发布输入能够通过真实页面重建新的候选发布包，为后续测试服/正式服/备份服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-operation-v3`，本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v3\`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209.log`
- blockers: 无。
- unresolved issues: 待继续通过真实页面执行测试服、标记测试通过、正式服和备份服链路。

## 2026-06-21 Deploy-Test Gate Attempt 2

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在 deployment 菜单 ID 冲突根因修复并重新构建 `release-20260621-page-full-flow-mainmerge-v3` 后，真实页面再次触发测试服部署，operation `op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0` 仍然 `FAILED`；日志显示 `20260619_mes_edhr_deployment_license_interface.sql` 执行到 line 327 时抛出 `ERROR 1644 (45000): Missing eDHR deployment system_menu rows; cannot merge tenant package menu_ids`。
- expected result: SQL 根因修复后的新候选包能够通过真实页面完成测试服部署，并继续进入“标记测试通过”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `deploy-test-operation-v2`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0.log`
- blockers: 当前主程序基线下 eDHR deployment 页面的 `system_menu` 主记录在真实测试库中仍不满足 SQL 合并前置条件。
- unresolved issues: 新的 eDHR deployment `system_menu` 缺失根因已在业务仓按严格 TDD 修复，但发布包输入已变化；必须重新构建新的 `releaseTag`，再从页面重跑 build/test/prod/backup 全链路。

## 2026-06-21 Task Pause Gate

- task id or phase id: `T4`
- tested cases: `TC-04`
- actual result: 用户将当前线程优先级切换到“三台服务器配置 Codex CLI 运行环境并跑通”的新任务；当前页面发布重跑任务在第二次测试服失败后的根因修复完成后暂停，未继续进入新的 `releaseTag` 页面重跑。
- expected result: 旧任务状态被显式标注为阻塞，避免与新任务并行推进造成文档链断裂。
- pass or fail: `PASS`
- evidence: `task.md` 当前状态、`task-state.json` 的 `status=blocked`、`execution-log.md` 中 `BLOCKER: user-switched-goal`
- blockers: 无。
- unresolved issues: 后续若恢复本任务，仍需用新的 `releaseTag` 从真实页面重走 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 Build Gate Retry v4

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 eDHR deployment legacy cleanup-order 根因按严格 TDD 修复后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v4` 执行 `build-release`，operation `op-2026-06-21T160352403091200Z-0fa6c660-0ec3-4f8d-aaee-c211f9ce39ed` 最终 `SUCCESS`；本地候选目录、`manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录均已重新生成，并核对 `manifest.json` 中后端源提交已切到 `74f505d86b7cf7be9fe2d481d36ca5a7fe45f68a`。
- expected result: cleanup-order 修复后的新发布输入能够通过真实页面重建新的候选发布包，为后续测试服、正式服和备份服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-operation-v4`，本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v4\`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-21T160352403091200Z-0fa6c660-0ec3-4f8d-aaee-c211f9ce39ed.log`
- blockers: 无。
- unresolved issues: 待继续通过真实页面执行测试服、标记测试通过、正式服和备份服链路。

## 2026-06-22 Deploy-Test Gate Attempt 3

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在 eDHR deployment cleanup-order 根因修复并重新构建 `release-20260621-page-full-flow-mainmerge-v4` 后，真实页面第三次触发测试服部署，operation `op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e` 仍然 `FAILED`；日志确认此前阻塞的 `20260619_mes_edhr_deployment_license_interface.sql` 已成功 `APPLIED`，但随后 `20260618_mes_edhr_label_print_queue.sql` 在 line 126 抛出 `ERROR 1062 (23000): Duplicate entry '900273' for key 'system_menu.PRIMARY'`。
- expected result: cleanup-order 修复后的新候选包能够通过真实页面完成测试服部署，并继续进入“标记测试通过”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `deploy-test-operation-v3`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e.log`
- blockers: 当前主程序基线下 `20260618_mes_edhr_label_print_queue.sql` 与测试服真实库在 `system_menu` 主键 `900273` 上发生冲突。
- unresolved issues: 必须先修复新的 `label_print_queue` 菜单冲突根因，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Deploy-Test Root Cause Fix v3

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 业务仓已按严格 TDD 修复 `20260618_mes_edhr_label_print_queue.sql` 的菜单号段冲突。只读证据确认 `900272-900279` 被 eDHR 独立表单菜单占用、`900280-900283` 被其他 eDHR 菜单占用，因此 label print 菜单已整体切换到独立的 `900320-900331`；`python -X utf8 -m pytest script\\tests\\test_edhr_label_print_queue_schema_sql.py script\\tests\\test_edhr_form_schema_sql.py -q` 返回 `9 passed`，`validate_bug_regression.py` 与 `run-release-migration-policy-gate.py --sql-root sql\\mysql` 也已通过。
- expected result: 新的 label print 菜单冲突根因在正式发布输入中被消除，维护仓可以据此重新构建新的发布包并从真实页面重走测试服链路。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `deploy-test-root-cause-fix-v3`，业务仓任务 `D:\\ProjectPackage\\Int\\IntRuoyi\\ruoyi-vue-pro\\doc\\tasks\\20260622-edhr-label-print-menu-id-collision-fix\\{task.md,execution-log.md,bug-regression-evidence.md}`
- blockers: 无。
- unresolved issues: 发布包输入已变化，必须重新构建新的 `releaseTag`，再从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Build Gate Retry v10

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 print policy 菜单主键冲突根因按严格 TDD 修复并 cherry-pick 进 clean release backend worktree 后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v10` 执行 `build-release`，operation `op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7` 最终 `SUCCESS`；本地候选目录、`manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录均已重新生成，并核对 backend/front commit 为 `a72602e2f025bd2ad4f9d250198f743a607d7482` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，且 `dirty=false`。
- expected result: print policy 修复后的 clean 发布输入能够通过真实页面重建新的候选发布包，为继续测试服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-operation-v10`、`build-release-manifest-v10`，本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v10\`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7.log`
- blockers: 无。
- unresolved issues: 待继续通过真实页面执行测试服、标记测试通过、正式服和备份服链路。

## 2026-06-22 Deploy-Test Gate Attempt 10

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在 print policy 根因修复并重新构建 `release-20260621-page-full-flow-mainmerge-v10` 后，真实页面再次触发测试服部署，operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3` 仍然 `FAILED`；日志确认此前阻塞的 `20260618_mes_edhr_print_policy_reissue_void.sql` 已成功 `APPLIED`，但随后 `20260618_mes_edhr_dhr_template_lifecycle.sql` 在 line `120` 抛出 `ERROR 1062 (23000): Duplicate entry '900293' for key 'system_menu.PRIMARY'`。
- expected result: print policy 修复后的新候选包能够通过真实页面完成测试服部署，并继续进入“标记测试通过”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `deploy-test-operation-v10`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3.log`
- blockers: 当前主程序基线下 `20260618_mes_edhr_dhr_template_lifecycle.sql` 与测试服真实库在 `system_menu` 主键 `900293` 上发生冲突。
- unresolved issues: 必须先修复新的 DHR 模板菜单冲突根因，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Build Gate Attempt 11

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 DHR 模板菜单冲突根因按严格 TDD 修复并并入 clean release backend worktree 后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v11` 执行 `build-release`，operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 最终 `FAILED`；失败发生在 Maven/Vite 打包前的维护仓 SQL 预检阶段，错误为 `system_menu.id must be an integer literal for release preflight: .../20260520_system_nas_management_menu.sql:11 -> \`name\``。
- expected result: DHR 模板修复后的 clean 发布输入能够通过真实页面重建新的候选发布包，为继续测试服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `build-release-operation-v11`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f.log`，运行态 JSON `runtime\\runtime-control\\op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f.json`
- blockers: 当前维护仓 `ops/release/release_sql_contract_gate.py` 误把合法 SQL 的 `ON DUPLICATE KEY UPDATE ... VALUES(\`name\`)` 更新子句解析成新的 `system_menu` 插入元组，导致本机 SQL 预检误报失败。
- unresolved issues: 必须先在维护仓按严格 TDD 修复 SQL 预检解析根因，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Build Gate Attempt 11 Root Cause Fix

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 维护仓已按严格 TDD 修复 `ops/release/release_sql_contract_gate.py` 对合法 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 的误解析；新增用例 `test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause` 先 RED 后 GREEN，随后真实 clean release backend SQL 根目录门禁再次通过，`20260520_system_nas_management_menu.sql` 不再误报。
- expected result: 页面 `build-release` 能重新通过本机 SQL 预检，继续为测试服链路生成新的 clean 候选包。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `maintenance-sql-preflight-fix-v11`，维护仓任务 `D:\\ProjectPackage\\Int\\IntRuoyiMaintance\\doc\\tasks\\20260622-sql-preflight-gate\\{task.md,execution-log.md,bug-regression-evidence.md}`，命令 `python -X utf8 -m pytest D:\\ProjectPackage\\Int\\IntRuoyiMaintance\\scripts\\tests\\test_release_sql_preflight_gate.py -q`、`python -X utf8 D:\\ProjectPackage\\Int\\IntRuoyiMaintance\\ops\\release\\run-release-migration-policy-gate.py --sql-root D:\\ProjectPackage\\Int\\IntRuoyi\\worktrees\\20260622-page-full-flow-mainmerge-release-clean\\ruoyi-vue-pro\\sql\\mysql`
- blockers: 无。
- unresolved issues: 需回真实页面改用 `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 Build Gate Retry v12

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在维护仓 SQL 预检误判根因按严格 TDD 修复后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v12` 执行 `build-release`，operation `op-2026-06-22T040752788980600Z-65f35dd8-4afa-4a4e-a9ee-5f04a5dd500a` 最终 `SUCCESS`；本地候选目录、`manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录均已重新生成，并核对 backend/front source commit 为 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，两仓 `dirty=false`。
- expected result: SQL 预检修复后的 clean 发布输入能够通过真实页面重建新的候选发布包，为继续测试服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-submit-v12`、`build-release-operation-v12`、`build-release-manifest-v12`，本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v12\`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T040752788980600Z-65f35dd8-4afa-4a4e-a9ee-5f04a5dd500a.log`
- blockers: 无。
- unresolved issues: 待继续通过真实页面执行测试服、标记测试通过、正式服和备份服链路。

## 2026-06-22 Deploy-Test Gate Attempt 12

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在 `release-20260621-page-full-flow-mainmerge-v12` 候选包构建通过后，真实页面再次触发测试服部署，operation `op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388` 最终 `FAILED`；日志确认本轮已成功完成镜像加载、测试服 `mysql/redis` 启动、`post-import.sql` 执行与 `20260613_infra_release_migration_state.sql` bootstrap，但随后在 `infra_release_operation_lock` 的测试环境锁获取阶段，本机脚本通过 `grep '^LOCK_ACQUIRED$'` 校验锁结果时收到退出码 `1`，导致整次部署被中断。
- expected result: v12 clean 候选包能够通过真实页面完成测试服部署，并继续进入“标记测试通过”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `deploy-test-preview-v12`、`deploy-test-submit-v12`、`deploy-test-operation-v12`，运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388.log`，运行态 JSON `runtime\\runtime-control\\op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388.json`
- blockers: 当前测试环境发布锁获取契约未满足，真实页面链路在环境锁阶段即被阻断。
- unresolved issues: 必须先只读核对测试服 `infra_release_operation_lock` 当前真实状态与锁获取脚本契约；若确认为维护仓锁处理根因，则需按严格 TDD 修复后重新构建新的 `releaseTag`，再从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 Deploy-Test Lock Audit v12

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` 返回 `2 passed`，确认维护仓历史锁释放修复未回退；随后只读 SSH 审计测试服确认，阻断 `deploy-test(v12)` 的 `infra_release_operation_lock` 实际来自外部链路 `test-20260622_121338 / 20260622_121338`，并且到审计时已被其他流程手动收口为 `FAILED`。同一现场还显示测试服共享环境已被外部链路改写成半切换态：`.env` 当前 `IMAGE_TAG=20260622_123255`，但容器仍混杂为 backend `release-20260621-page-full-flow-mainmerge-v10`、frontend `release-20260621-page-full-flow-v6`。
- expected result: 明确区分“维护仓锁释放代码回归”与“共享测试环境被外部 stale lock/并发发布改写”的根因，避免误判而重复重建发布包。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `publish-release-lock-regression-v12`、`test-stale-lock-audit-v12`、`shared-test-environment-drift-v12`；只读 SQL 现场、测试服 `.env` 与 `docker ps` 审计输出。
- blockers: 共享测试环境当前并不处于本任务 `release-20260621-page-full-flow-mainmerge-v12` 的稳定运行态。
- unresolved issues: 由于本轮发布包输入未变化，下一步不应重新 `build-release`；应继续通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重试 `deploy-test`，让测试服重新回到本任务候选包后再继续 `mark-tested -> prod -> backup`。

## 2026-06-22 Deploy-Test Lock Recovery Prep v12 Retry 2

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 对第二次页面重试失败现场做最新只读复核后，确认测试服 `infra_release_operation_lock` 中 `target_environment='test'` 仍只剩一条 `RUNNING` 锁 `test-20260622_124533 / 20260622_124533 / started_at=2026-06-22 12:56:16`；`infra_release_migration` 当前 `RUNNING` 数量为 `0`；`/opt/intruoyi/runtime/data/runtime-control/` 中没有任何包含 `20260622_124533` 的 operation 证据；远端进程列表中也没有可归属该 releaseTag 的活跃发布 shell。与此同时，测试服当前已被重新拉回 `.env IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`、backend `release-20260621-page-full-flow-mainmerge-v12`，但 frontend 仍停留在 `release-20260621-page-full-flow-v6`，说明 stale 锁仍在阻断本任务完成测试服切换。
- expected result: 在确认不存在活跃发布进程和运行控制 operation 的前提下，把该单条 stale `RUNNING` 锁先记录到数据库修复证据，再恢复性收口为 `FAILED`，随后回到真实页面继续点击 `deploy-test(v12)`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `test-stale-release-lock-precheck-v12-retry2`、`database-schema-evidence-prepared-v12-retry2`；任务证据文件 `database-schema-evidence.md`；只读 SQL / 进程 / 运行控制目录 / `.env` / `docker ps` 审计输出。
- blockers: 在完成该 stale 锁恢复性回写之前，真实页面 `deploy-test(v12)` 仍会被环境锁阻断。
- unresolved issues: 需先执行 `validate_database_schema.py --evidence doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/database-schema-evidence.md`，然后把 `test-20260622_124533` 从 `RUNNING` 收口为 `FAILED`，再回到真实页面继续 `deploy-test(v12)`。

## 2026-06-22 Deploy-Test Lock Recovery Apply v12 Retry 2

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 已先执行 `python -X utf8 C:\Users\BJB110\.codex\skills\database-schema-delivery\scripts\validate_database_schema.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\database-schema-evidence.md`，结果 `Database schema evidence is valid.`；随后仅对测试服 `infra_release_operation_lock` 中 `test-20260622_124533 / 20260622_124533 / target_environment=test / status=RUNNING` 做恢复性回写，SQL `ROW_COUNT()=1`。回写后只读复核确认：该锁已改为 `FAILED`，`finished_at=2026-06-22 13:22:21`，`error_message` 已写明“Recovered stale RUNNING lock during 2026-06-22 main-merge rerun after confirming no active publish process or runtime-control operation evidence.”；测试环境 `RUNNING` 锁数量已清零为 `0`，`infra_release_migration` 的 `RUNNING` 数量仍为 `0`。
- expected result: 在不改发布输入、不绕过页面的前提下，先恢复性收口外部 stale 锁，再回到真实页面继续第三次 `deploy-test(v12)`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `test-stale-release-lock-recovery-apply-v12-retry2`；`database-schema-evidence.md`；测试服 `infra_release_operation_lock` 回读结果；`validate_database_schema.py` 输出。
- blockers: 测试服当前前端容器仍停留在 `release-20260621-page-full-flow-v6`，尚未完成本任务 v12 双端切换。
- unresolved issues: 需立即回到真实页面继续第三次 `deploy-test(release-20260621-page-full-flow-mainmerge-v12)`，验证锁清零后测试服能否完成剩余切换并进入后续 `mark-tested -> prod -> backup`。

## 2026-06-22 Deploy-Test Gate Attempt 12 Retry 2

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在外部 stale 锁 `test-20260622_124533` 经证据校验和恢复性回写收口为 `FAILED` 后，真实页面第三次重新触发测试服部署，operation `op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a` 最终 `SUCCESS`；本机 operation JSON 已收口为 `status=SUCCESS / summary=命令执行完成`，日志确认剩余 required SQL、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、测试服发布锁释放和远端临时文件清理全部通过。
- expected result: v12 clean 候选包在清除外部 stale 锁后，能够通过真实页面完成测试服部署并把测试服完整切回本任务候选版本。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `deploy-test-submit-v12-retry2`、`deploy-test-operation-v12-retry2`、`deploy-test-runtime-verify-v12-retry2`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a.log`；测试服 `.env` / `docker ps` / HTTP 健康检查只读输出。
- blockers: 无。
- unresolved issues: 下一步需继续在真实页面执行 `mark-tested(release-20260621-page-full-flow-mainmerge-v12)`，并选择可用恢复集候选后再继续 `prod -> backup`。

## 2026-06-22 Mark-Tested Gate Attempt 12 Retry 2

- task id or phase id: `T5`
- tested cases: `TC-04`
- actual result: 在将运行控制台 `repo-root/frontend-root` 切换到真实宿主机 `IntRuoyiWorktrees` 后，真实页面第三次重新触发 `mark-tested(v12)`，operation `op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3` 最终 `SUCCESS`；本机 JSON 收口为 `status=SUCCESS / summary=命令执行完成`，日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v12`，并同步写入 `rollback-compatibility.json status=BLOCKED` 元数据。
- expected result: v12 clean 候选包能够通过真实页面完成测试通过标记，并保留正式服上线所需的恢复集候选与测试结论。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `mark-tested-preview-v12-retry2`、`mark-tested-submit-v12-retry2`、`mark-tested-operation-v12-retry2`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3.log`
- blockers: 无。
- unresolved issues: 下一步需继续在真实页面执行 `上线正式服(release-20260621-page-full-flow-mainmerge-v12)`，再继续 `上线备份服`。

## 2026-06-22 Promote-Prod Gate Attempt 12

- task id or phase id: `T6`
- tested cases: `TC-05`
- actual result: 在 `mark-tested(v12)` 完成后，真实页面触发 `上线正式服(release-20260621-page-full-flow-mainmerge-v12)`，operation `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83` 最终 `FAILED`；日志确认正式服已成功跨过多条 required SQL，但随后在 `20260618_mes_edhr_release_transaction_lifecycle.sql` line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已恢复性释放为 `LOCK_RELEASED`。
- expected result: v12 clean 候选包能够通过真实页面完成正式服上线，并继续进入“上线备份服”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `promote-prod-submit-v12`、`promote-prod-operation-v12`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83.log`
- blockers: 当前主程序基线下 `20260618_mes_edhr_release_transaction_lifecycle.sql` 与正式服真实库在 release transaction permission 菜单合并前置条件上不兼容。
- unresolved issues: 必须先按严格 TDD 修复该正式 SQL 根因，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Promote-Prod Root Cause Fix Handoff

- task id or phase id: `T6`
- tested cases: `TC-05`
- actual result: 业务后端已按严格 TDD 修复正式服 `release transaction permission` 漂移根因：`20260618_mes_edhr_release_precheck_engine.sql` 现会显式纠正 legacy `900263/900264` 的 submit/approve permission，不再仅做缺失插入。验证已通过 `test_edhr_release_precheck_schema_sql.py`、`test_edhr_release_transaction_schema_sql.py`、迁移策略门禁与 bug regression validator；业务后端主仓提交为 `314ebb2204`，clean release backend worktree 已更新为 `5c52f2ec42`。
- expected result: 发布输入更新后，维护仓必须用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`，并以同一输入基线一次性走通。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `release-transaction-root-cause-fix-v12`、`release-input-rotate-v13`；业务仓任务 `D:\\ProjectPackage\\Int\\IntRuoyi\\ruoyi-vue-pro\\doc\\tasks\\20260622-edhr-release-transaction-permission-rows-fix\\{task.md,execution-log.md,bug-regression-evidence.md}`；主仓提交 `314ebb2204`；clean worktree 提交 `5c52f2ec42`
- blockers: 无新的代码阻塞。
- unresolved issues: 旧 `release-20260621-page-full-flow-mainmerge-v12` 结果已失效，下一步必须回真实页面以新标签（建议 `release-20260621-page-full-flow-mainmerge-v13`）从 `build-release` 重跑全链路。

## 2026-06-22 Build Gate Attempt 13

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 release transaction permission 根因修复并切换到 clean backend `5c52f2ec42` 后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v13` 执行 `build-release`，operation `op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06` 最终 `FAILED`；日志确认 clean backend Maven 打包已 `BUILD SUCCESS`，但随后在 clean frontend 打包前直接失败：`Missing frontend Vite CLI: D:\Int\ProjectPackage\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean\node_modules\vite\bin\vite.js`。
- expected result: 新 clean 发布输入能够通过真实页面完成候选包构建，为后续测试服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `build-release-preview-v13`、`build-release-submit-v13`、`build-release-operation-v13`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06.log`
- blockers: clean frontend worktree 依赖现场缺失，`node_modules\\vite\\bin\\vite.js` 不存在。
- unresolved issues: 必须先恢复 clean frontend worktree 依赖并做本地 `pnpm build:test` 回归，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 Build Gate Attempt 13 Frontend Dependency Repair

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 已在 clean frontend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 最小恢复依赖现场：`pnpm install --frozen-lockfile` 成功重建 `node_modules`，随后 `pnpm build:test` 返回 `Build successful. Please see dist-test directory`。这说明 v13 阻塞属于本机构建前置丢失，而不是主程序代码回归。
- expected result: clean frontend 的 Vite CLI 与 test 模式打包能力恢复后，维护仓可以回真实页面以新的 `releaseTag` 继续 `build-release`，而无需新增业务代码修复。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `clean-frontend-deps-repair-v13`；命令 `pnpm install --frozen-lockfile`、`pnpm build:test` 于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`
- blockers: 无新的代码阻塞。
- unresolved issues: 需回真实页面以新标签（建议 `release-20260621-page-full-flow-mainmerge-v14`）重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 Build Gate Retry v14

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 在 clean frontend 依赖现场恢复并通过 `pnpm build:test` 回归后，真实页面重新以 `release-20260621-page-full-flow-mainmerge-v14` 执行 `build-release`，operation `op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9` 最终 `SUCCESS`；本地候选目录、`manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录均已重新生成，并核对 backend/front source commit 为 `5c52f2ec4268212e71070d57a14f006202f337c8` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，两仓 `dirty=false`。
- expected result: release transaction permission 根因修复后的新 clean 发布输入能够通过真实页面完成候选包重建，为后续测试服、正式服和备份服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-preview-v14`、`build-release-submit-v14`、`build-release-operation-v14`、`build-release-manifest-v14`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9.log`；本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v14\manifest.json`
- blockers: 无。
- unresolved issues: 需继续复用真实页面会话执行 `deploy-test(release-20260621-page-full-flow-mainmerge-v14)`，之后再继续 `mark-tested -> prod -> backup`。

## 2026-06-22 Deploy-Test Gate Attempt 14

- task id or phase id: `T4`
- tested cases: `TC-03`
- actual result: 在 `release-20260621-page-full-flow-mainmerge-v14` 候选包构建通过后，真实页面继续触发测试服部署，operation `op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7` 最终 `SUCCESS`；日志确认本轮完整跨过远端磁盘前置、compose/.env 同步、镜像包与 `required-sql` 传输、`20260618_mes_edhr_release_precheck_engine.sql` 与 `20260618_mes_edhr_release_transaction_lifecycle.sql` 应用、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 校验、测试服发布锁释放和远端临时文件清理。只读复核同时确认测试服 `.env` 与前后端运行镜像都已切到 `release-20260621-page-full-flow-mainmerge-v14`，`48081/8081` 均返回 HTTP `200`。
- expected result: 新 clean 发布输入能够通过真实页面完成测试服部署，并把测试服完整切换到 `release-20260621-page-full-flow-mainmerge-v14`，为继续 `mark-tested -> prod -> backup` 提供有效运行态。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `deploy-test-preview-v14`、`deploy-test-submit-v14`、`deploy-test-operation-v14`、`deploy-test-runtime-verify-v14`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7.log`；测试服 `.env` / `docker ps` / HTTP 健康检查只读输出。
- blockers: 无。
- unresolved issues: 需继续复用真实页面会话执行 `mark-tested(release-20260621-page-full-flow-mainmerge-v14)`，之后再继续 `prod -> backup`。

## 2026-06-22 Mark-Tested Gate Attempt 14

- task id or phase id: `T5`
- tested cases: `TC-04`
- actual result: 在 `deploy-test(v14)` 完成后，真实页面继续触发 `mark-tested(release-20260621-page-full-flow-mainmerge-v14)`，operation `op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280` 最终 `SUCCESS`；页面预览已确认恢复集候选为 `20260621-063218 · AVAILABLE`，验证结论为“回归通过，允许上线正式服（v14）”，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktrees。运行态 JSON 收口为 `status=SUCCESS / summary=命令执行完成`，日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14`，并同步写入 `rollback-compatibility.json status=BLOCKED`。
- expected result: v14 clean 候选包能够通过真实页面完成测试通过标记，并保留正式服上线所需的恢复集候选与测试结论。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `mark-tested-preview-v14`、`mark-tested-submit-v14`、`mark-tested-operation-v14`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280.log`
- blockers: 无。
- unresolved issues: 下一步需继续在真实页面执行 `上线正式服(release-20260621-page-full-flow-mainmerge-v14)`，再继续 `上线备份服`。

## 2026-06-22 Promote-Prod Gate Attempt 14

- task id or phase id: `T6`
- tested cases: `TC-05`
- actual result: 在 `mark-tested(v14)` 完成后，真实页面继续触发 `上线正式服(release-20260621-page-full-flow-mainmerge-v14)`，operation `op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1` 最终 `FAILED`；运行态 JSON 收口为 `status=FAILED / summary=命令退出码非 0: 1`，日志确认正式服在成功应用 `20260618_mes_edhr_release_precheck_engine.sql` 后，于 `20260618_mes_edhr_release_transaction_lifecycle.sql` line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已恢复性释放为 `LOCK_RELEASED`。
- expected result: v14 clean 候选包能够通过真实页面完成正式服上线，并继续进入“上线备份服”。
- pass or fail: `FAIL`
- evidence: `execution-log.md` 中 `promote-prod-submit-v14`、`promote-prod-operation-v14`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1.log`
- blockers: 当前主程序基线下 `20260618_mes_edhr_release_transaction_lifecycle.sql` 与正式服真实库在 release transaction permission 菜单合并前置条件上仍不兼容。
- unresolved issues: 必须先按严格 TDD 修复该正式 SQL 根因，再以新的 `releaseTag` 从真实页面重跑 `build-release -> deploy-test -> mark-tested -> prod -> backup` 全链路。

## 2026-06-22 Workflow Suspension

- task id or phase id: `T6-T8`
- tested cases: `暂停态核对`
- actual result: 用户已把当前线程目标切换为 `int_main` 融合，本任务在保留 `v14` 的测试通过与正式服失败证据后暂停，不再继续 `prod -> backup`。
- expected result: 旧主线必须显式变为 `BLOCKED`，避免与新的 `int_main` 融合主线并行推进。
- pass or fail: `BLOCKED`
- evidence: `task.md`、`task-state.json`、`execution-log.md` 中 `Workflow Pause For int_main Integration`
- blockers: 用户优先级已切换到“把 holding 改动融合进真正的 int_main”。
- unresolved issues: 若后续恢复页面发布主线，需重新确认 `release-20260621-page-full-flow-mainmerge-v14` 与环境状态是否仍允许直接续跑。

## 2026-06-22 Promote-Prod Root Cause Fix Handoff 14

- task id or phase id: `T6`
- tested cases: `TC-05`
- actual result: 当前线程恢复继续推进页面发布主线后，已在 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 按严格 TDD 收口正式服第二阶段根因。只读对比正式服/测试服 `system_menu` 后确认：正式库 `900266/900267/900268` 仍被 traveler 菜单占用，而旧 `20260618_mes_edhr_release_transaction_lifecycle.sql` 仍把放行事务 `reject / withdraw / event-query` 绑在这组三号段。正式修复已将三条放行事务菜单切换到独立的 `900353/900354/900355`，并同步更新 package menu merge 与 `system_role_menu` 合并逻辑；相关 RED/GREEN 回归、迁移策略门禁与 bug regression evidence 校验均已通过，clean worktree 提交为 `49248d9f20`。
- expected result: 新 clean 发布输入重新进入页面链路后，正式服上线不应再因 release transaction permission 行缺失或 traveler 号段冲突失败。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `Workflow Resume And Root Cause Fix v14`；业务任务 `D:\\ProjectPackage\\Int\\IntRuoyiWorktrees\\ruoyi-vue-pro-mainmerge-release-clean\\doc\\tasks\\20260622-edhr-release-transaction-permission-rows-fix\\{task.md,execution-log.md,bug-regression-evidence.md}`；clean worktree 提交 `49248d9f20`
- blockers: 无新的代码阻塞。
- unresolved issues: backend clean 发布输入已变化，旧 `release-20260621-page-full-flow-mainmerge-v14` 证据已失效；下一步必须回真实页面以新标签（建议 `release-20260621-page-full-flow-mainmerge-v15`）从 `build-release` 重跑全链路。

## 2026-06-22 Build Gate Attempt 15

- task id or phase id: `T3`
- tested cases: `TC-02`
- actual result: 真实页面已重新执行 `build-release(v15)` 并最终 `SUCCESS`；候选包、`manifest.json`、`release-manifest.json`、镜像 tar 与 NAS 发布目录均已重新生成，`manifest` 已核对 backend commit=`49248d9f20db9e3100bc5f492c7027d4de065f32`、frontend commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`，两仓 `dirty=false`。
- expected result: 新 clean 发布输入能够通过真实页面完成候选包构建，为后续测试服、正式服和备份服整链重跑提供唯一有效的 `releaseTag`。
- pass or fail: `PASS`
- evidence: `execution-log.md` 中 `build-release-preview-v15`、`build-release-submit-v15`、`build-release-operation-v15`、`build-release-manifest-v15`；运行态 JSON `runtime\\runtime-control\\op-2026-06-22T121006967109700Z-6dc95b22-9d29-4a00-b432-9cdd4e34bc51.json`；运行态日志 `runtime\\runtime-control\\logs\\op-2026-06-22T121006967109700Z-6dc95b22-9d29-4a00-b432-9cdd4e34bc51.log`；本地目录 `E:\\Int\\CacheData\\IntRuoyi\\publish-int-ruoyi\\release-20260621-page-full-flow-mainmerge-v15\\manifest.json`
- blockers: 无。
- unresolved issues: 需继续复用真实页面会话执行 `deploy-test(release-20260621-page-full-flow-mainmerge-v15)`，之后再继续 `mark-tested -> prod -> backup`。
