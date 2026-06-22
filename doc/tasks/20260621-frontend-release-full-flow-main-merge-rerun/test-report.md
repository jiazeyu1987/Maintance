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
