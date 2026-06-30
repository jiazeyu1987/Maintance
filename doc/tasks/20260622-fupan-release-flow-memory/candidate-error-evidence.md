# Candidate Error Prevention Evidence

- Generated At: 2026-06-22T22:10:42
- Project Root: D:\ProjectPackage\Int\IntRuoyiMaintance
- Source Files Scanned: 3
- Files With Matches: 3
- Context Lines: 1
- Keywords: 错误, 失败, 阻塞, 问题, 风险, 修复, 原因, 影响, 不得, 必须, 告警, 回归, fail, failed, error, blocked, root cause, regression, risk, must, should not, do not

Review these snippets before writing any durable project rule.

## doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/execution-log.md

### Match 1 (lines 2-5)

```text

- BDD: 合并后页面真实发布全链路仍可通过 -> Given 主程序前后端已合并新代码且运行控制台可访问 / When 在页面上依次执行构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服 / Then 每一步都必须由真实页面动作触发并最终成功。
- BDD: 合并后若链路失败必须先记录再修复重走 -> Given 任一步页面动作或后台执行因当前主程序基线失败 / When 记录失败证据并修复 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整链路直到一次性通过。

```

### Match 2 (lines 9-11)

```text
- GREEN: migration-policy-gate -> PASS，执行 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 返回 `status=passed`，当前主程序基线共有 `migrationCount=186`。
- GREEN: maven-clean-preflight -> PASS，执行 `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` 与 `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` 均 `BUILD SUCCESS`，本轮未复现 target/jar 锁阻塞。
- GREEN: docker-base-image-preflight -> PASS，执行 `docker image inspect nginx:1.27-alpine` 与 `docker image inspect eclipse-temurin:21-jre-noble` 均成功，基础镜像已在本机可用。
```

### Match 3 (lines 13-21)

```text
- GREEN: page-session-ready -> PASS，已通过 Playwright 打开 `http://127.0.0.1:48181/` 并完成页面快照；当前页面表单可见，构建发布包动作已选中，旧标签仍显示 `release-20260621-page-full-flow-v6`，可直接改成本轮新 `releaseTag` 后提交预览。
- GREEN: build-release-preview-v1 -> PASS，本轮页面已改用新标签 `release-20260621-page-full-flow-mainmerge-v1` 和原因“主程序合并后重新验证页面发布全链路”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v1 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到 `promote-prod`、`backup-now`、`rollback` 或 `restore-data`。
- GREEN: build-release-submit-v1 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T141253294294600Z-8e7296ad-f348-43e6-adca-f4bb9646fedb`；运行态状态文件当前记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v1`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- BLOCKER: build-release-operation-v1 -> operation `op-2026-06-21T141253294294600Z-8e7296ad-f348-43e6-adca-f4bb9646fedb` 于 `2026-06-21 22:16:17 +08:00` 收口为 `FAILED`；本机日志显示前端 `vite build` 在加载 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\vite.config.ts` 时抛出 `Cannot find module '@babel/helper-validator-identifier'`，require stack 指向 `@babel/types@7.26.0` 与 `@vitejs/plugin-vue-jsx`。影响：本轮页面链路在“构建发布包”阶段被当前主程序前端依赖现场阻断，未生成可继续部署测试服的发布包；必须先修复前端依赖根因，再从页面重新发起新的 build-release。
- RED: `node -e "require.resolve('@babel/helper-validator-identifier',{paths:['D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3/node_modules/.pnpm/@babel+types@7.26.0/node_modules/@babel/types/lib/validators']})"` -> FAIL，直接复现 `MODULE_NOT_FOUND`，确认问题存在于当前前端依赖现场而非仅存在于页面封装层。
- BLOCKER: frontend-deps-repair-v1 -> `pnpm install --frozen-lockfile` 虽提示 `Packages: +5`，但 `node_modules\\.pnpm\\@babel+helper-validator-identifier@7.25.9\\node_modules\\@babel\\helper-validator-identifier` 目录仍为空，缺失模块未恢复；继续执行 `pnpm install --frozen-lockfile --force` 时又在 `@rollup/rollup-win32-x64-msvc` 目录重建阶段收到 `ERR_PNPM_EPERM`。影响：当前前端 `node_modules` 不仅内容缺失，而且存在文件系统占用/权限阻塞；必须先排除占用并让依赖完整重建，之后才能重新验证构建。
- GREEN: frontend-deps-repair-v2 -> PASS，只读核对进程后确认同仓前端存在 `env.local`(`8081`) 与 `merged-e2e`(`8118`) 两组 Vite 进程持续占用 `yudao-ui-admin-vue3` 的 `node_modules`；停止 `PID 34612/19028/12688` 后重新执行 `pnpm install --frozen-lockfile --force`，依赖已按锁文件完整重建。
- GREEN: frontend-deps-regression-v1 -> PASS，`node_modules\\.pnpm\\@babel+helper-validator-identifier@7.25.9\\node_modules\\@babel\\helper-validator-identifier` 已恢复 `lib/package.json/README.md`；执行 `node -e "require.resolve('@babel/helper-validator-identifier', {paths:[...]})"` 返回 `resolved`，随后 `pnpm build:test` 通过并输出 `Build successful. Please see dist-test directory`。允许回到真实页面以新 `releaseTag` 重跑 `build-release`。
- GREEN: build-release-preview-v2 -> PASS，真实页面已把 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v2` 并重新打开“命令预览”；弹窗再次确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v2 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到部署测试服、标记测试通过、上线正式服、上线备份服、回滚或恢复动作。
```

### Match 4 (lines 25-66)

```text
- GREEN: deploy-test-submit-v1 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T145341175255100Z-0de12b04-2650-49e2-a088-47dfa4f2b7ed`；页面操作记录已刷新为 `RUNNING / 命令已提交到本机执行队列`，当前链路推进到测试服部署阶段。
- BLOCKER: deploy-test-operation-v1 -> operation `op-2026-06-21T145341175255100Z-0de12b04-2650-49e2-a088-47dfa4f2b7ed` 于 `2026-06-21 23:02:08 +08:00` 收口为 `FAILED`；远端日志显示测试服在应用 `20260619_mes_edhr_deployment_license_interface.sql` 时，MySQL 抛出 `ERROR 1644 (45000) at line 299: Invalid eDHR deployment page menu definition; cannot merge tenant package menu_ids`。影响：当前主程序基线下的真实页面发布链路在“部署测试服”阶段被 `required-sql` 根因阻断，测试服未能完成本轮候选包部署，也不能继续“标记测试通过 -> 上线正式服 -> 上线备份服”；必须先修复该 SQL/菜单定义根因，重新构建新的 `releaseTag`，再从页面重新执行完整链路。
- GREEN: deploy-test-root-cause-fix-v1 -> PASS，已在业务仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 建立任务 `20260621-edhr-deployment-menu-id-collision-fix`，按严格 TDD 修复 `20260619_mes_edhr_deployment_license_interface.sql`：deployment 菜单号段改为独立未冲突的 `900315-900319`，并加入对旧 `mes:pro-edhr-deployment:*` / `/mes/pro/feedback/edhr-deployment` 残留菜单的正式清理逻辑。验证已通过 `python -X utf8 -m pytest script\tests\test_edhr_deployment_schema_sql.py -q` 与 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`。由于发布包输入已变化，旧标签 `release-20260621-page-full-flow-mainmerge-v2` 不可继续使用；下一步必须从真实页面重新执行新的 `build-release`，建议标签升级为 `release-20260621-page-full-flow-mainmerge-v3`。
- GREEN: build-release-preview-v3 -> PASS，真实页面已重新选择“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v3`，原因填写“主程序合并后重新验证页面发布全链路”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v3 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到部署测试服、标记测试通过、正式服、备份服、回滚或恢复动作。
- GREEN: build-release-submit-v3 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209`；运行态状态文件记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v3`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- GREEN: build-release-operation-v3 -> PASS，operation `op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209` 最终 `SUCCESS`；日志明确记录 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v3` 与 `Release package built: release-20260621-page-full-flow-mainmerge-v3`。本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v3` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v3.tar`，其中 `manifest.json` 的 `releaseTag` 已核对为 `release-20260621-page-full-flow-mainmerge-v3`。至此修复后的新候选包已准备就绪，可继续在真实页面执行“部署测试服”。
- GREEN: deploy-test-preview-v2 -> PASS，真实页面已重新切换到“部署测试服”，目标环境显示 `测试服`，发布标签为 `release-20260621-page-full-flow-mainmerge-v3`，操作原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v3）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v3 -ServerHost 172.30.30.58 ...`，未带入 `PROD` 确认，也未漂移到正式服、备份服、回滚或恢复动作。
- GREEN: deploy-test-submit-v2 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，当前链路再次推进到测试服部署阶段。
- BLOCKER: deploy-test-operation-v2 -> operation `op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0` 最终 `FAILED`；远端日志显示 `20260619_mes_edhr_deployment_license_interface.sql` 在真实测试库执行到 line 327 时，MySQL 抛出 `ERROR 1644 (45000): Missing eDHR deployment system_menu rows; cannot merge tenant package menu_ids`。影响：当前主程序基线下的真实页面发布链路仍然卡在“部署测试服”，但根因已从先前的 deployment 菜单 ID 冲突推进为 deployment 页面 `system_menu` 主记录缺失/残缺；测试服本轮候选包未能完成部署，也不能继续“标记测试通过 -> 上线正式服 -> 上线备份服”。按任务门禁，下一步必须先只读定位 `system_menu` 缺失根因，修复后以新的 `releaseTag` 从真实页面重新执行完整链路。
- GREEN: deploy-test-root-cause-fix-v2 -> PASS，已在业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260621-edhr-deployment-menu-id-collision-fix\` 继续按严格 TDD 收口新的 eDHR deployment 阻塞。只读查询测试服真实库确认当前只存在 `900315-900318` 四条 deployment 菜单、旧 `900300 / mes:pro-edhr-deployment:precheck` 已被删除，说明旧残留先挡住了 `900319` 插入，随后又被后置 cleanup 删除；正式修复已把 legacy cleanup 前移到 `900315-900319` 新菜单插入之前，并通过 `python -X utf8 -m pytest script\tests\test_edhr_deployment_schema_sql.py -q`（6 passed）与 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v3` 不可继续使用；下一步必须从真实页面重新执行新的 `build-release`，建议标签升级为 `release-20260621-page-full-flow-mainmerge-v4`。
- BLOCKER: user-switched-goal -> 用户在 `2026-06-21` 将当前线程目标切换到“在测试服务器、正式服务器、备份服务器配置好 Codex CLI 运行环境，并保证连接参数与本机相同且全部跑通”。本任务暂停在 eDHR deployment `system_menu` 根因已修复、但尚未以新 `releaseTag` 重新执行页面 `build-release` 之前；后续若恢复，必须以新的 `releaseTag` 从真实页面重走 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: task-resume-after-cli-setup -> PASS，用户已恢复“主程序合并后重新走页面发布全链路”任务；当前继续沿用既有真实页面会话 `frontend-release-full-flow-mainmerge`，并以业务后端修复提交 `74f505d86b` 作为新的发布输入基线。
- GREEN: build-release-preview-v4 -> PASS，真实页面已重新切回“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v4`，原因填写为“主程序合并后重新验证页面发布全链路：cleanup-order修复后重建发布包（v4）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v4 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到部署测试服、标记测试通过、正式服、备份服、回滚或恢复动作。
- GREEN: build-release-submit-v4 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T160352403091200Z-0fa6c660-0ec3-4f8d-aaee-c211f9ce39ed`；运行态状态文件记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v4`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- GREEN: build-release-operation-v4 -> PASS，operation `op-2026-06-21T160352403091200Z-0fa6c660-0ec3-4f8d-aaee-c211f9ce39ed` 最终 `SUCCESS`；日志明确记录 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v4` 与 `Release package built: release-20260621-page-full-flow-mainmerge-v4`。本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v4` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v4.tar`，其中 `manifest.json` 已核对 `releaseTag=release-20260621-page-full-flow-mainmerge-v4`，并确认后端源提交为 `74f505d86b7cf7be9fe2d481d36ca5a7fe45f68a`、前端源提交为 `37359a074cedcc0a341f17cb0abdd1a71f838731`。至此 cleanup-order 修复后的新候选包已准备就绪，可继续在真实页面执行“部署测试服（v4）”。
- GREEN: deploy-test-preview-v3 -> PASS，真实页面已切换到“部署测试服”，目标环境显示 `测试服`，发布标签为 `release-20260621-page-full-flow-mainmerge-v4`，操作原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v4）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v4 -ServerHost 172.30.30.58 ...`，未带入 `PROD` 确认，也未漂移到正式服、备份服、回滚或恢复动作。
- GREEN: deploy-test-submit-v3 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，链路再次推进到测试服部署阶段。
- BLOCKER: deploy-test-operation-v3 -> operation `op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e` 最终 `FAILED`；日志确认上一轮阻塞的 `20260619_mes_edhr_deployment_license_interface.sql` 已在测试服真实库成功 `APPLIED`，说明 cleanup-order 修复已生效，但新的失败切换为 `20260618_mes_edhr_label_print_queue.sql`：MySQL 在 line 126 抛出 `ERROR 1062 (23000): Duplicate entry '900273' for key 'system_menu.PRIMARY'`。影响：当前主程序基线下的真实页面发布链路仍卡在“部署测试服”，测试服本轮候选包未能完成部署，也不能继续“标记测试通过 -> 上线正式服 -> 上线备份服”；按任务门禁，下一步必须先把新的 `system_menu` 主键冲突记录并定位根因，修复后以新的 `releaseTag` 从真实页面重新 `build-release -> deploy-test`。
- GREEN: deploy-test-root-cause-fix-v3 -> PASS，已在业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\` 继续按严格 TDD 收口新的 label print 阻塞。只读搜索源码与测试服真实 `system_menu` 确认：`20260618_mes_edhr_label_print_queue.sql` 复用了 `900272-900283`，其中 `900272-900279` 已被 `20260618_mes_edhr_form_instance.sql`/真实库“eDHR独立表单*”菜单占用，`900280-900283` 又被“eDHR报表目录 / 报表查询 / 报表导出审计 / 交付驾驶舱”占用；正式修复已把 label print 菜单整体切换到未占用的 `900320-900331`，并通过 `python -X utf8 -m pytest script\tests\test_edhr_label_print_queue_schema_sql.py script\tests\test_edhr_form_schema_sql.py -q`（9 passed）、`python C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\bug-regression-evidence.md` 与 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v4` 不可继续使用；下一步必须从真实页面重新执行新的 `build-release`，建议标签升级为 `release-20260621-page-full-flow-mainmerge-v5`。
- GREEN: backend-fix-commit-v1 -> PASS，业务仓 label-print 菜单号冲突修复已正式提交为 `6d96efef31`，确保本轮 `v5` 候选包输入可追溯。
- GREEN: build-release-preview-v5 -> PASS，真实页面已把 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v5`，原因填写为“主程序合并后重新验证页面发布全链路：label-print-menu修复后重建发布包（v5）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v5 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到部署测试服、标记测试通过、正式服、备份服、回滚或恢复动作。
- GREEN: build-release-submit-v5 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T222743046277600Z-b8ac2dad-4d52-4166-96a6-affe98450291`；页面操作记录已刷新为 `RUNNING / 命令已提交到本机执行队列`，当前 `releaseTag=release-20260621-page-full-flow-mainmerge-v5`。
- GREEN: build-release-operation-v5 -> PASS，operation `op-2026-06-21T222743046277600Z-b8ac2dad-4d52-4166-96a6-affe98450291` 最终 `SUCCESS`；日志明确记录 backend `BUILD SUCCESS`、`Build successful. Please see dist-intruoyi-test directory`、`Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v5` 与 `Release package built: release-20260621-page-full-flow-mainmerge-v5`。本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v5` 已生成 `manifest.json`、`release-manifest.json`、`intruoyi-images_release-20260621-page-full-flow-mainmerge-v5.tar`；`manifest.json` 中 backend 源提交为 `6d96efef31b8a3a81df10c307487803ca6fa2845`、admin frontend 源提交为 `37359a074cedcc0a341f17cb0abdd1a71f838731`，publishScope 为 `code-only`。至此新候选包已准备就绪，可继续在真实页面执行“部署测试服（v5）”。
- GREEN: deploy-test-preview-v5 -> PASS，真实页面已切换到“部署测试服”并填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v5）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v5 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 ...`。初看这组 `Remote*` 参数可疑，但随后只读核对 `backend/src/main/resources/application.yaml`、`ops/deploy/publish-int-ruoyi.ps1` 目标映射、历史通过链路证据与 `show-int-ruoyi-remote-status.ps1` 对测试服 `172.30.30.58` 的实机状态检查，确认当前测试服基线确为 `/var/lib/docker + /dev/vdb + ragflow_compose-minio-1`，运行态返回 `status=running`、`currentReleaseTag=release-20260621-page-full-flow-mainmerge-v4`。因此这不是新的参数漂移阻塞；按门禁完成事实校对后，可继续在同一真实页面预览弹窗提交 `deploy-test(v5)`。
- GREEN: deploy-test-submit-v5 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，当前链路再次推进到测试服部署阶段。
- BLOCKER: deploy-test-operation-v5 -> operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50` 最终 `FAILED`；远端日志显示先前阻塞的 `20260618_mes_edhr_label_print_queue.sql` 已在真实测试库成功 `APPLIED`，随后新的失败切换为 `20260618_mes_edhr_oq_pq_execution_deviation.sql`：MySQL 在 line 357 抛出 `ERROR 1644 (45000): Invalid eDHR OQ/PQ button menu definition; cannot merge tenant package menu_ids`。影响：当前主程序基线下的真实页面发布链路仍卡在“部署测试服”，测试服本轮候选包未能完成部署，也不能继续“标记测试通过 -> 上线正式服 -> 上线备份服”。按任务门禁，下一步必须先把新的 OQ/PQ 菜单定义冲突记录并定位根因，修复后以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test`。
- GREEN: deploy-test-root-cause-fix-v4 -> PASS，已在业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\` 按严格 TDD 收口新的 OQ/PQ 阻塞。只读源码与测试服真实 `system_menu` 共同确认：旧号段 `900290-900295` 中，`900290-900292` 与其他 eDHR SQL 存在直接复用，`900293-900295` 已被 `eDHR统一变更` 占用；正式修复已将 OQ/PQ 菜单整体迁移到独立的 `900332-900337`，新增 `tmp_mes_edhr_oq_pq_legacy_menu_map` 吸收测试库已落下的旧 OQ/PQ 页面/按钮残留，并在测试租户 `menu_ids`/`system_role_menu` 合并时做 legacy 归一。验证已通过 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_edhr_oq_pq_schema_sql.py -q`（5 passed）、`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` 与 `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\bug-regression-evidence.md`。
- GREEN: backend-fix-commit-v2 -> PASS，业务仓 OQ/PQ 菜单定义冲突修复已正式提交为 `0d82319b98 任务: 修复OQ/PQ菜单定义冲突`，并补充回归证据提交 `3ace5094ec 任务: 补充OQ/PQ回归证据`；当前后端发布输入已更新到 `3ace5094ec7768237e7249b876a4eca67dad5e2a`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 不可继续使用；下一步必须通过真实页面重新执行新的 `build-release`，建议标签升级为 `release-20260621-page-full-flow-mainmerge-v6`。
- GREEN: build-release-preview-v6 -> PASS，真实页面已切回“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v6`，原因填写为“主程序合并后重新验证页面发布全链路：oq-pq-menu修复后重建发布包（v6）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v6 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到部署测试服、标记测试通过、正式服、备份服、回滚或恢复动作。
- GREEN: build-release-submit-v6 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb`；运行态状态文件记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v6`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- GREEN: build-release-operation-v6 -> PASS，operation `op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb` 最终 `SUCCESS`；日志明确记录 backend `BUILD SUCCESS`、前端 `Build successful. Please see dist-intruoyi-test directory`、backend image 构建与 NAS 上传完成。当前本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v6` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v6.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v6`；`manifest.json` 已核对 `releaseTag=release-20260621-page-full-flow-mainmerge-v6`、`publishScope=code-only`，并记录 backend 源提交 `3ace5094ec7768237e7249b876a4eca67dad5e2a`、admin frontend 源提交 `37359a074cedcc0a341f17cb0abdd1a71f838731`。
- BLOCKER: build-release-input-baseline-v6 -> `manifest.json sourceRepos` 显示 backend 与 admin frontend 都是 `dirty=true`；随后只读执行 `git status --short` 确认业务后端存在 DCC 文件名识别相关未提交改动（`yudao-module-dcc/...DccControlledFileProjectCodeRecognitionService*` 等），业务前端存在 DCC 受控预览相关未提交改动（`src/views/dcc/controlled-file/detail/index.vue`、`scripts/dcc-controlled-preview-project-code-recognition.test.mjs` 等）。影响：`release-20260621-page-full-flow-mainmerge-v6` 不是“纯已提交 merged main 基线”候选包，而是混入未提交 DCC 工作树改动的 dirty baseline；在用户未明确这些 dirty 改动是否应纳入本轮真实发布链路前，不能安全继续 `deploy-test -> mark-tested -> prod -> backup`。
- GREEN: release-clean-worktree-prep -> PASS，已新建成对 clean release worktree：后端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `3ace5094ec`，`git status --short` 为空）、前端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `37359a074`，`git status --short` 为空）。本机运维台局部配置 `config/runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 已切换到这两个 clean worktree，下一步只需重启运维控制台并继续使用页面按钮提交 `deploy-test(v6)`。
- GREEN: release-clean-worktree-verify -> PASS，已只读核对 `config/runtime-control.local.yaml`、后端 clean worktree `git rev-parse HEAD=3ace5094ec7768237e7249b876a4eca67dad5e2a`、前端 clean worktree `git rev-parse HEAD=37359a074cedcc0a341f17cb0abdd1a71f838731`，且两仓 `git status --short` 为空；本机运维台健康检查 `http://127.0.0.1:48181/actuator/health` 返回 `{\"status\":\"UP\"}`。
- GREEN: build-release-preview-clean-baseline -> PASS，已回到真实页面会话 `frontend-release-full-flow-mainmerge` 并重新打开 `build-release` 预览弹窗；页面参数明确显示 `-BackendRepoRoot D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro -FrontendRepoRoot D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/yudao-ui-admin-vue3`，说明后续页面动作将使用 clean worktree 基线。由于输入基线已切换，旧标签 `release-20260621-page-full-flow-mainmerge-v6` 不可继续作为本轮候选结果；下一步必须在真实页面以新的 `releaseTag` 重建发布包，再重新推进 `deploy-test -> mark-tested -> prod -> backup`。
- GREEN: build-release-preview-v7 -> PASS，真实页面已将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v7`，原因填写为“主程序合并后重新验证页面发布全链路：clean-release-worktree重建发布包（v7）”；预览弹窗再次确认参数仍指向 clean backend/frontend worktree，且 `publish-int-ruoyi.ps1 -Mode build-release` 未漂移到其他动作。
- GREEN: build-release-submit-v7 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T234844686010400Z-12704e02-b10c-472d-af05-cb4b5ff828c3`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，当前 `releaseTag=release-20260621-page-full-flow-mainmerge-v7`。
- BLOCKER: build-release-operation-v7 -> operation `op-2026-06-21T234844686010400Z-12704e02-b10c-472d-af05-cb4b5ff828c3` 最终 `FAILED`；日志确认 backend clean worktree `mvn ... -DskipTests clean package` 已 `BUILD SUCCESS`，但前端阶段直接报错 `Missing frontend Vite CLI: D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js`。影响：当前 clean baseline 的真实页面链路在“构建发布包”阶段被前端依赖前置条件阻断，v7 发布包未生成，不能继续 `deploy-test -> mark-tested -> prod -> backup`；必须先补齐 clean frontend worktree 的依赖现场，再以新的 `releaseTag` 从真实页面重跑 `build-release`。
- GREEN: clean-frontend-deps-bootstrap-v7 -> PASS，只读确认 clean frontend worktree 原先 `node_modules` 不存在且 `node_modules/vite/bin/vite.js` 缺失后，已在 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3` 执行 `pnpm install --frozen-lockfile`，安装完成且未修改锁文件。
- GREEN: clean-frontend-deps-regression-v7 -> PASS，`Test-Path ...\\node_modules\\vite\\bin\\vite.js` 返回 `True`，随后执行 `pnpm build:test` 成功输出 `Build successful. Please see dist-test directory`。当前 clean frontend worktree 的依赖前置条件已恢复；为避免与失败的 `v7` operation 混淆，下一步将回真实页面改用新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v8` 重新提交 `build-release`。
- GREEN: build-release-preview-v8 -> PASS，真实页面已将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v8`，原因填写为“主程序合并后重新验证页面发布全链路：clean-worktree依赖修复后重建发布包（v8）”；预览弹窗确认仍执行 `publish-int-ruoyi.ps1 -Mode build-release`，且 `BackendRepoRoot/FrontendRepoRoot` 继续指向 clean release worktree。
- GREEN: build-release-submit-v8 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T000330671317300Z-c009a2ba-8bcf-4210-b73a-2a09a4a1e424`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`。
```

### Match 5 (lines 69-83)

```text
- GREEN: deploy-test-submit-v8 -> PASS，已在真实页面提交 `release-20260621-page-full-flow-mainmerge-v8` 的测试服部署，生成 operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e`；operation 记录的后台命令为 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v8 ...`，目标主机仍为 `172.30.30.58`。
- BLOCKER: deploy-test-operation-v8 -> operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e` 最终 `FAILED`；远端日志确认 `20260613_dcc_file_view_matrix_seed`、`20260615_showroom_hall_canvas_background`、`20260618_mes_edhr_label_print_queue` 与 `20260618_post_release_role_e2e_gate` 已成功跨过，随后在 `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 399 抛出 `ERROR 1644 (45000): Missing eDHR OQ/PQ system_menu rows; cannot merge tenant package menu_ids`。影响：当前 clean baseline 的真实页面发布链路仍卡在“部署测试服”，不能继续 `mark-tested -> prod -> backup`；必须先记录并修复新的 OQ/PQ 菜单缺行根因，再从真实页面重新构建新包并重走。
- GREEN: deploy-test-root-cause-readonly-v8 -> PASS，只读核对测试服 `172.30.30.58` 当前 `system_menu` 现场确认：新号段 `900332-900337` 仅剩 `900335-900337` 三条，`900332-900334` 缺失，且旧 OQ/PQ `900290-900292` 已不存在。这与当前 SQL 的执行顺序一致：`900332-900334` 会先因旧 `path/permission` 残留而跳过插入，随后 legacy cleanup 又删除 `900290-900292`，最终导致页面/查询/创建三条被删空，只剩执行/复测/关闭三条。下一步必须在业务后端按严格 TDD 修 cleanup 顺序，再通过真实页面用新的 `releaseTag` 重新执行 `build-release -> deploy-test`。
- GREEN: backend-oq-pq-legacy-cleanup-fix-v1 -> PASS，业务仓任务 `20260622-edhr-oq-pq-legacy-cleanup-order-fix` 已完成 cleanup 顺序修复并通过 `pytest`、迁移策略门禁与 bug regression validator；维护仓下一步必须改用 `release-20260621-page-full-flow-mainmerge-v9` 重新构建发布包，再从真实页面继续 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：收到用户再次确认“主程序合并修改了部分代码，怕已经不对了”，本任务保持在当前 T4 阶段，不改计划，下一步直接用 `release-20260621-page-full-flow-mainmerge-v9` 从真实页面重跑 `build-release -> deploy-test`。
- GREEN: build-release-preview-v9 -> PASS，真实页面已切回“构建发布包”，发布标签改为 `release-20260621-page-full-flow-mainmerge-v9`，原因填写为“主程序合并后重新验证页面发布全链路：oq-pq-cleanup-order修复后重建发布包（v9）”；预览弹窗确认仍执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v9 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，未漂移到其他动作。
- GREEN: build-release-submit-v9 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T010042891831400Z-d59751ca-ab81-4136-b128-0f98537c2cd5`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`。
- GREEN: build-release-operation-v9 -> PASS，operation `op-2026-06-22T010042891831400Z-d59751ca-ab81-4136-b128-0f98537c2cd5` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v9\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v9.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v9`。`manifest.json` 已核对 backend commit=`3ace5094ec7768237e7249b876a4eca67dad5e2a`、frontend commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`、`publishScope=code-only`，且 backend/admin frontend 的 `dirty` 均为 `false`。
- GREEN: deploy-test-preview-v9 -> PASS，真实页面已切换到“部署测试服”，操作原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v9）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v9 -ServerHost 172.30.30.58 ...`，真实部署目标仍是测试服 `172.30.30.58`，未漂移到正式服/备份服动作。
- GREEN: deploy-test-submit-v9 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，当前链路再次推进到测试服部署阶段。
- BLOCKER: deploy-test-operation-v9 -> operation `op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a` 最终 `FAILED`；远端日志确认此前阻塞的 `20260618_mes_edhr_oq_pq_execution_deviation.sql` 已在真实测试库成功 `APPLIED`，随后新的失败切换为 `20260618_mes_edhr_print_policy_reissue_void.sql`：MySQL 在 line 103 抛出 `ERROR 1062 (23000): Duplicate entry '900285' for key 'system_menu.PRIMARY'`。影响：当前 clean baseline 的真实页面发布链路仍卡在“部署测试服”，`release-20260621-page-full-flow-mainmerge-v9` 无法继续用于 `mark-tested -> prod -> backup`；按任务门禁，下一步必须先在业务后端记录并修复新的 `system_menu` 主键冲突根因，随后改用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v10`）从真实页面重新执行 `build-release -> deploy-test`。
- GREEN: backend-print-policy-fix-v1 -> PASS，业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-print-policy-menu-id-collision-fix\` 已完成 print policy 菜单主键冲突修复，并通过 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_edhr_print_policy_reissue_schema_sql.py -q`、`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` 与 `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-print-policy-menu-id-collision-fix\bug-regression-evidence.md`。
- GREEN: clean-release-backend-cherrypick-v10 -> PASS，已将 print policy 修复提交 `fd63921684d44f5f942befeeded64f2eb55348e7` 与回归证据提交 `db411a242d9f97ffe94c8682c0fcf087961ccf97` cherry-pick 到 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`，当前 clean backend HEAD 为 `a72602e2f0b26a7c34f58f0c66a0384944df361`，前端 clean worktree 仍为 `37359a074cedcc0a341f17cb0abdd1a71f838731`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v9` 不可继续使用；下一步必须回真实页面以 `release-20260621-page-full-flow-mainmerge-v10` 重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。
- GREEN: build-release-preview-v10 -> PASS，真实页面已切回“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v10`，原因填写为“主程序合并后重新验证页面发布全链路：print-policy修复后重建发布包（v10）”；预览弹窗确认仍执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v10 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktree，未漂移到部署测试服、标记测试通过、正式服或备份服动作。
- GREEN: build-release-submit-v10 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`，当前链路已重新进入 clean baseline 的 `build-release(v10)`。
```

### Match 6 (lines 85-96)

```text
- GREEN: build-release-manifest-v10 -> PASS，本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v10` 已生成 `manifest.json`、`release-manifest.json`、`docker-compose.yml`、`runtime-env/`、`smoke/` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v10.tar`；`manifest.json` 已核对 `releaseTag=release-20260621-page-full-flow-mainmerge-v10`、`publishScope=code-only`，backend source commit=`a72602e2f025bd2ad4f9d250198f743a607d7482`、frontend source commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`，且两仓 `dirty=false`。允许继续从真实页面执行 `deploy-test(v10)`。
- GREEN: deploy-test-preview-v10 -> PASS，真实页面已切换到“部署测试服”，填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v10）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v10 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 ...`，目标仍为测试服 `172.30.30.58`，且 backend/frontend repo root 继续指向 clean release worktree。
- GREEN: deploy-test-submit-v10 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3`；运行态状态文件记录 `action=publish-test`、`releaseTag=release-20260621-page-full-flow-mainmerge-v10`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- BLOCKER: deploy-test-operation-v10 -> operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3` 最终 `FAILED`；远端日志确认此前阻塞的 `20260618_mes_edhr_print_policy_reissue_void.sql` 已在真实测试库成功 `APPLIED`，随后新的失败切换为 `20260618_mes_edhr_dhr_template_lifecycle.sql`：MySQL 在 line `120` 抛出 `ERROR 1062 (23000): Duplicate entry '900293' for key 'system_menu.PRIMARY'`。影响：当前 clean baseline 的真实页面发布链路仍卡在“部署测试服”，`release-20260621-page-full-flow-mainmerge-v10` 不能继续进入 `mark-tested -> prod -> backup`；按任务门禁，必须先在业务后端记录并修复新的 DHR 模板菜单主键冲突，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test`。
- GREEN: deploy-test-root-cause-readonly-v10 -> PASS，只读核对测试服 `172.30.30.58` 当前真实 `system_menu` 现场确认：`900290-900292` 已是 DHR 模板菜单本身，但 `900293-900299` 已被 `eDHR统一变更 / 创建 / 提交 / 审批 / 生效申请 / 影响范围 / 事件` 占用；源码同步确认 `20260618_mes_edhr_dhr_template_lifecycle.sql` 当前仍把 DHR 模板按钮写死在 `900293-900298`，与统一变更整段冲突。下一步必须在业务后端按严格 TDD 将 DHR 模板按钮段切换到新的独立未冲突号段，再回真实页面用新的 `releaseTag` 重新 `build-release -> deploy-test`。
- GREEN: backend-dhr-template-fix-v1 -> PASS，业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix\` 已完成 DHR 模板菜单主键冲突修复，并通过 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_edhr_dhr_template_schema_sql.py -q`、`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` 与 `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix\bug-regression-evidence.md`。
- GREEN: clean-release-backend-cherrypick-v11 -> PASS，已将 DHR 模板修复提交 `e7a11af216206d78dc698b0a52b6c3bac7f03281` cherry-pick 到 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`，当前 clean backend HEAD 为 `d9606a65df0a2b3dcaec53f7a1b2c3d1e7313790`，前端 clean worktree 仍为 `37359a074cedcc0a341f17cb0abdd1a71f838731`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v10` 不可继续使用；下一步必须回真实页面以 `release-20260621-page-full-flow-mainmerge-v11` 重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。
- GREEN: build-release-preview-v11 -> PASS，真实页面已切回“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v11`，原因填写为“主程序合并后重新验证页面发布全链路：DHR模板菜单修复后重建发布包（v11）”；预览弹窗确认仍执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v11 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktree。
- GREEN: build-release-submit-v11 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f`；运行态状态文件记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v11`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- BLOCKER: build-release-operation-v11 -> operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 最终 `FAILED`；本机日志显示维护仓新增 SQL 预检门禁在 Maven/Vite 打包前直接失败，报错为 `system_menu.id must be an integer literal for release preflight: D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro/sql/mysql/20260520_system_nas_management_menu.sql:11 -> \`name\``。只读核对源 SQL 可见该文件的 `INSERT ... VALUES (...) ON DUPLICATE KEY UPDATE \`name\` = VALUES(\`name\`)` 语句本身合法，因此当前阻塞不在业务 SQL，而在维护仓 `ops/release/release_sql_contract_gate.py` 把更新子句中的 `VALUES(...)` 误识别成插入元组。影响：当前 clean baseline 的真实页面链路已退回“构建发布包”阶段，`release-20260621-page-full-flow-mainmerge-v11` 未生成可继续用于测试服/正式服/备份服的候选包；按任务门禁，必须先在维护仓按严格 TDD 修复该解析根因，再以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: maintenance-sql-preflight-fix-v11 -> PASS，维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-sql-preflight-gate\` 已对 `ops/release/release_sql_contract_gate.py` 完成最小修复：`_extract_value_tuples()` 现在只连续消费真正 `VALUES (...)` 顶层插入元组，遇到 `ON DUPLICATE KEY UPDATE` 这类非逗号分隔后续内容立即停止，因此不再把更新子句中的 `VALUES(\`name\`)` 误识别成新元组。回归已通过 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q`（4 passed）、`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_showroom_release_sql_contract.py -q`（3 passed）以及 `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro\sql\mysql`（passed, `migrationCount=186`）。下一步可以回真实页面改用新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: build-release-submit-v12 -> PASS，承接真实页面会话 `frontend-release-full-flow-mainmerge` 中已完成的页面预览与点击执行，`build-release(v12)` 生成 operation `op-2026-06-22T040752788980600Z-65f35dd8-4afa-4a4e-a9ee-5f04a5dd500a`；运行态 JSON 记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v12`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
```

### Match 7 (lines 98-130)

```text
- GREEN: build-release-manifest-v12 -> PASS，本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v12\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v12.tar`；`manifest.json` 已核对 `releaseTag=release-20260621-page-full-flow-mainmerge-v12`、`publishScope=code-only`，backend source commit=`d9606a65dfb4bfd4151970e3393e77be5f13a0c5`、frontend source commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`，且 backend/admin frontend 的 `dirty` 均为 `false`。允许继续从真实页面执行 `deploy-test(v12)`。
- GREEN: deploy-test-preview-v12 -> PASS，真实页面已切换到“部署测试服”，操作原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v12）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v12 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 ...`，目标仍为测试服 `172.30.30.58`，且 backend/frontend repo root 继续指向 clean release worktree。
- GREEN: deploy-test-submit-v12 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388`；运行态状态文件记录 `action=publish-test`、`releaseTag=release-20260621-page-full-flow-mainmerge-v12`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- BLOCKER: deploy-test-operation-v12 -> operation `op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388` 最终 `FAILED`；日志确认本轮已经成功跨过镜像加载、测试服 `mysql/redis` 启动、`post-import.sql` 执行与 `20260613_infra_release_migration_state.sql` bootstrap，但在 `infra_release_operation_lock` 的测试环境锁获取阶段，本机脚本通过 `grep '^LOCK_ACQUIRED$'` 断言锁获取结果时收到退出码 `1`，随后把当前 operation 标记为 `FAILED` 并释放当前尝试的锁记录。影响：当前 clean baseline 的真实页面发布链路再次卡在“部署测试服”，但失败点已切换为测试环境发布锁契约，而不是业务 required SQL；`release-20260621-page-full-flow-mainmerge-v12` 未进入 required SQL 正式执行与容器切换，不能继续 `mark-tested -> prod -> backup`。按任务门禁，下一步必须先只读核对测试服 `infra_release_operation_lock` 当前真实状态与锁获取契约，再决定是否需要在维护仓按严格 TDD 修复锁处理根因，修复后再用新的 `releaseTag` 从真实页面重新 `build-release -> deploy-test`。
- GREEN: publish-release-lock-regression-v12 -> PASS，执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` 返回 `2 passed in 0.02s`；确认维护仓此前修复过的“持锁后 fail-fast 必须先释放 `infra_release_operation_lock` 再退出”契约仍然有效，本轮主阻塞不是旧的锁释放代码回归。
- GREEN: test-stale-lock-audit-v12 -> PASS，只读 SSH 审计测试服 `172.30.30.58` 后确认：`infra_release_operation_lock` 当前唯一测试环境记录为外部链路 `operation_id=test-20260622_121338` / `release_tag=20260622_121338`，其状态已从早先阻断 `deploy-test(v12)` 的 `RUNNING` 被其他流程收口为 `FAILED`，`finished_at=2026-06-22 12:45:12`，`error_message='Recovered stale RUNNING lock after 20260622 DCC preview release failures; later fixes require retry.'`；同时 `infra_release_migration` 已无新的 `RUNNING` 记录。这说明当前锁阻塞来源已收敛为共享测试环境中的外部 stale lock，而不是本次页面链路自己再次遗留了锁。
- BLOCKER: shared-test-environment-drift-v12 -> 同一只读审计同时确认测试服已被外部链路改写到新的半切换现场：`/opt/intruoyi/runtime/.env` 当前 `IMAGE_TAG=20260622_123255`，但运行容器仍混杂为 backend `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v10`、frontend `intruoyi-frontend:release-20260621-page-full-flow-v6`，且 `/var/lib/docker/intruoyi-releases/` 下同时保留本任务的 `release-20260621-page-full-flow-mainmerge-v12` 候选目录。这意味着当前主阻塞已从“维护仓脚本锁契约待修”切换为“共享测试环境被外部失败发布链路改写成半切换状态”。由于本轮发布包输入没有变化、锁释放回归已通过，当前不应重新 `build-release`；下一步应继续按真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重试 `deploy-test`，以把测试服重新拉回本任务候选包，再根据结果继续 `mark-tested -> prod -> backup` 或记录新的页面链路阻塞。
- GREEN: deploy-test-submit-v12-retry1 -> PASS，真实页面已重新切换到“部署测试服”，原因填写为“主程序合并后重新验证页面发布全链路：共享测试环境漂移后重试部署测试服（v12）”，发布标签仍为 `release-20260621-page-full-flow-mainmerge-v12`；预览弹窗再次确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v12 ...`，随后在页面点击“执行”，生成 operation `op-2026-06-22T045846454437200Z-f0e05484-deef-41e1-b3b6-a0d6b64829b4`。
- GREEN: shared-test-environment-rebound-v12-retry1 -> PASS，只读轮询第二次页面重试日志时确认：本轮在再次失败前，至少已经把测试服 `/opt/intruoyi/runtime/.env` 重新拉回 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`，并将 backend 容器切到 `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v12`；这证明共享测试环境漂移问题并非本任务候选包本身损坏，而是可以被真实页面 `deploy-test(v12)` 拉回本任务 releaseTag。
- BLOCKER: deploy-test-operation-v12-retry1 -> operation `op-2026-06-22T045846454437200Z-f0e05484-deef-41e1-b3b6-a0d6b64829b4` 最终 `FAILED`；日志确认这次已重新同步 compose/.env、scheduler smoke runner、镜像 tar、全量 `required-sql` 和运行时脚本，并再次完成测试服 `mysql/redis` 启动、`post-import.sql` 与 `20260613_infra_release_migration_state.sql` bootstrap，但在 `Invoke-ReleaseOperationLockAcquire` 阶段再次因为 `grep '^LOCK_ACQUIRED$'` 收到退出码 `1` 而失败。影响：当前第二次真实页面重试仍未进入 `required SQL` 正式执行，不能继续 `mark-tested -> prod -> backup`。
- BLOCKER: test-stale-release-lock-root-cause-v12-retry1 -> 对同一失败现场继续只读核对测试服真实库与远端文件后确认：当前阻断本轮重试的测试环境锁已从前一条外部记录 `test-20260622_121338` 切换为另一条外部 `RUNNING` 锁 `operation_id=test-20260622_124533` / `release_tag=20260622_124533`，`started_at=2026-06-22 12:56:16`，且对应目录 `/var/lib/docker/intruoyi-releases/20260622_124533/` 完整存在；与此同时，`/opt/intruoyi/runtime/data/runtime-control/` 下没有任何与 `20260622_124533` 对应的 operation JSON / log，`pgrep -af 'publish-int-ruoyi|backup-ops|runtime-control|deploy-release|20260622_124533'` 也未发现可归属该 releaseTag 的活跃 shell / publish 进程。这说明当前测试服再次被缺少本地运行控制证据的外部 stale `RUNNING` 锁阻断，而不是本任务第二次页面重试自己遗留了锁。按 `20260618-build-test-backup-release` 与 `20260620-frontend-release-full-flow` 的既有先例，下一步必须先记录数据库状态修复设计与证据，再在确认无活跃发布进程前提下将 `test-20260622_124533` 从 `RUNNING` 收口为 `FAILED`，随后继续通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重试 `deploy-test`。
- GREEN: test-stale-release-lock-precheck-v12-retry2 -> PASS，`2026-06-22` 再次只读复核测试服当前现场后确认：`infra_release_operation_lock` 中 `target_environment='test'` 仍只剩一条 `RUNNING` 锁 `test-20260622_124533 / 20260622_124533 / started_at=2026-06-22 12:56:16`；`infra_release_migration` 当前 `RUNNING` 数量为 `0`；`/opt/intruoyi/runtime/data/runtime-control/` 下仍无任何包含 `20260622_124533` 的 operation 证据；远端进程列表仍只有长期驻留的运行控制 Java 进程，没有新的 `publish-int-ruoyi|backup-ops|deploy-release|20260622_124533` 活跃 shell。与此同时，测试服当前 `.env` 仍为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`，backend 容器也已切到 `release-20260621-page-full-flow-mainmerge-v12`，但 frontend 容器仍停留在 `release-20260621-page-full-flow-v6`，说明共享测试环境仍卡在锁阻断导致的半切换态。
- GREEN: database-schema-evidence-prepared-v12-retry2 -> PASS，已在主任务目录新增 `database-schema-evidence.md`，明确本次仅对测试服 `infra_release_operation_lock` 的单条 stale `RUNNING` 锁做恢复性收口，且不改发布输入、不改业务数据；下一步需先执行 `validate_database_schema.py` 校验证据，再按先例完成恢复性回写，随后回到真实页面继续点击 `deploy-test(v12)`。
- GREEN: test-stale-release-lock-recovery-apply-v12-retry2 -> PASS，已先执行 `python -X utf8 C:\Users\BJB110\.codex\skills\database-schema-delivery\scripts\validate_database_schema.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\database-schema-evidence.md`，结果 `Database schema evidence is valid.`；随后仅对测试服 `infra_release_operation_lock` 单条记录 `operation_id=test-20260622_124533 / release_tag=20260622_124533 / target_environment=test / status=RUNNING` 执行恢复性回写，SQL `ROW_COUNT()` 返回 `1`。回写后只读复核确认：该锁已变为 `FAILED`，`finished_at=2026-06-22 13:22:21`，`error_message='Recovered stale RUNNING lock during 2026-06-22 main-merge rerun after confirming no active publish process or runtime-control operation evidence.'`；测试环境 `RUNNING` 锁数量已清零为 `0`，`infra_release_migration` 的 `RUNNING` 数量仍为 `0`。下一步可以回到真实页面继续第三次 `deploy-test(release-20260621-page-full-flow-mainmerge-v12)`，验证测试服能否最终完成前后端双端切换。
- GREEN: deploy-test-submit-v12-retry2 -> PASS，恢复外部 stale 锁后，已继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 第三次执行“部署测试服”，原因填写为“主程序合并后重新验证页面发布全链路：恢复 stale 锁后第三次部署测试服（v12）”，发布标签仍为 `release-20260621-page-full-flow-mainmerge-v12`；页面真实点击“执行”后生成 operation `op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a`。
- GREEN: deploy-test-operation-v12-retry2 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a.log` 后确认：该真实页面 `deploy-test` 已最终 `SUCCESS`，结果为 `命令执行完成`；日志确认剩余 required SQL 已完成，随后跨过 Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、测试服发布锁释放与远端临时文件清理，最终输出 `Publish completed for test.`。
- GREEN: deploy-test-runtime-verify-v12-retry2 -> PASS，只读复核测试服 `172.30.30.58` 当前运行态后确认：`/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-mainmerge-v12`；`http://172.30.30.58:48081/actuator/health` 与 `http://172.30.30.58:8081/` 均返回 HTTP `200`；`infra_release_migration` 当前 `RUNNING` 数量为 `0`。至此真实页面测试服发布链路已恢复并通过，下一步继续在真实页面执行 `mark-tested(v12)`。
- BLOCKER: mark-tested-operation-v12 -> operation `op-2026-06-22T063134275225600Z-e0e3d514-ea55-432e-a8bd-c14693a7a321` 已由真实页面 `mark-tested(v12)` 触发并最终 `FAILED`；本机日志确认失败并非发布包或恢复集参数错误，而是 `publish-int-ruoyi.ps1` 在 `Resolve-Path -LiteralPath $BackendRepoRoot` 阶段找不到 `D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro`，因此脚本在执行业务校验前即退出。影响：当前链路暂停在“标记测试通过”阶段，不能继续 `prod -> backup`；按门禁必须先记录该环境级阻塞，再修复路径现场后回真实页面重试同一 `release-20260621-page-full-flow-mainmerge-v12`。
- GREEN: clean-release-backend-worktree-restore-v12 -> PASS，随后按 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md` 只读排障并确认：`config/runtime-control.local.yaml` 仍指向 clean release worktree，目录 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\` 下仅剩前端子仓、后端 `ruoyi-vue-pro` 子目录缺失；后端主仓分支 `codex/20260622-page-full-flow-mainmerge-release-clean` 仍存在且指向提交 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5`。已将该后端 worktree 最小补回原路径，并验证 `git -C ...\ruoyi-vue-pro rev-parse HEAD` 仍为 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5`、`git status --short` 为空。发布输入未变化，下一步应回真实页面继续重试 `mark-tested(v12)`，无需重新 `build-release` 或 `deploy-test`。- BLOCKER: mark-tested-operation-v12-retry1 -> operation `op-2026-06-22T064955263916Z-b55872da-49c6-4fae-a56a-1c3d6af01689` 在补回旧路径后再次由真实页面 `mark-tested(v12)` 触发并最终 `FAILED`；本机日志与直接 `Resolve-Path -LiteralPath 'D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro'` 共同证明：问题并非单次目录缺失，而是 `config/runtime-control.local.yaml` 当前仍指向宿主机上并不存在的 `D:/ProjectPackage/Int/IntRuoyi/worktrees/...` 旧 worktree 根。`git worktree list` 同时确认真实宿主机 worktree 根在 `D:/ProjectPackage/Int/IntRuoyiWorktrees/`，因此若不修正本地运行控制台配置，`mark-tested -> prod -> backup` 会持续在同一路径解析阶段失败。
- GREEN: clean-release-worktree-repoint-v12 -> PASS，随后已在真实宿主机 worktree 根 `D:/ProjectPackage/Int/IntRuoyiWorktrees/` 成对创建 clean release worktree：后端 `ruoyi-vue-pro-mainmerge-release-clean`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `d9606a65dfb4bfd4151970e3393e77be5f13a0c5`）与前端 `yudao-ui-admin-vue3-mainmerge-release-clean`（同名 branch，HEAD `37359a074cedcc0a341f17cb0abdd1a71f838731`）。已将本机 `config/runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 切换到这两条真实宿主机路径，并仅重启命中 `runtime-control-maintenance-2026.06-SNAPSHOT.jar` 的本地 Java 进程；`http://127.0.0.1:48181/actuator/health` 已恢复 `UP`。发布输入仍未变化，下一步回真实页面继续第三次重试 `mark-tested(v12)`。
- GREEN: mark-tested-preview-v12-retry2 -> PASS，真实页面第三次重试 `mark-tested(v12)` 前已重新 `snapshot` 并点击“预览命令”；弹窗确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v12 -TestConclusion 回归通过，允许上线正式服（v12） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 已切换到真实宿主机路径 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- GREEN: mark-tested-submit-v12-retry2 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3`。
- GREEN: mark-tested-operation-v12-retry2 -> PASS，只读核对运行态 JSON `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3.log` 后确认：本轮 `mark-tested(v12)` 已最终 `SUCCESS`，结果为 `命令执行完成`；日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v12`，并已记录 `rollback-compatibility.json status=BLOCKED` 元数据。至此里程碑 T5 已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 执行 `prod -> backup`。
- GREEN: promote-prod-submit-v12 -> PASS，承接真实页面会话 `frontend-release-full-flow-mainmerge` 中已完成的正式服预览与点击执行，`上线正式服(v12)` 生成 operation `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83`；运行态 JSON 记录 `environment=prod`、`component=promote-prod`、`action=promote-prod`、`releaseTag=release-20260621-page-full-flow-mainmerge-v12`、`prodDryRunEvidencePath=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-mainmerge-v12-preflight-release-dry-run.json`。
- BLOCKER: promote-prod-operation-v12 -> operation `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83` 最终 `FAILED`，运行态 JSON 收口为 `status=FAILED / summary=命令退出码非 0: 1`；本机日志确认正式服已成功跨过多条 required SQL，包括 `20260619_srm_d7_3_plan_framework.sql`、`20260620_srm_phase1_supplier_access_profile.sql`、`20260618_mes_edhr_print_policy_reissue_void.sql` 与 `20260618_mes_edhr_dhr_template_lifecycle.sql`，随后在 `20260618_mes_edhr_release_transaction_lifecycle.sql` line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已被脚本恢复性释放为 `LOCK_RELEASED`。影响：当前真实页面全链路首次推进到正式服时暴露了新的业务 SQL 根因，`release-20260621-page-full-flow-mainmerge-v12` 不能继续进入 `backup`；按“先记录再修复”门禁，下一步必须先在业务后端按严格 TDD 修复 `20260618_mes_edhr_release_transaction_lifecycle.sql` 的 release transaction permission 行缺失问题，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: release-transaction-root-cause-fix-v12 -> PASS，业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix\` 已按严格 TDD 修复 `20260618_mes_edhr_release_precheck_engine.sql` 对 legacy `900263/900264` submit/approve permission 漂移只插入不纠偏的缺口；验证已通过 `python -X utf8 -m pytest ...test_edhr_release_precheck_schema_sql.py -q`、`python -X utf8 -m pytest ...test_edhr_release_transaction_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 `validate_bug_regression.py --evidence ...bug-regression-evidence.md`。业务后端主仓提交为 `314ebb2204`，clean release backend worktree 已补齐 cherry-pick 为 `5c52f2ec42`。
- GREEN: release-input-rotate-v13 -> PASS，当前 clean 发布输入已从 backend `d9606a65dfb4bfd4151970e3393e77be5f13a0c5` 更新到 `5c52f2ec42`，前端 clean worktree 仍为 `37359a074cedcc0a341f17cb0abdd1a71f838731`；因此旧 `release-20260621-page-full-flow-mainmerge-v12` 的 build/test/mark-tested/prod 证据不得复用为新输入放行结果。下一步必须复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v13`）重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: build-release-preview-v13 -> PASS，真实页面已切回“构建发布包”，将 `releaseTag` 改为 `release-20260621-page-full-flow-mainmerge-v13`，原因填写为“主程序合并后重新验证页面发布全链路：release-transaction修复后重建发布包（v13）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v13 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- GREEN: build-release-submit-v13 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06`；运行态 JSON 记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v13`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
- BLOCKER: build-release-operation-v13 -> operation `op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06` 最终 `FAILED`；日志确认 clean backend `mvn -f ...ruoyi-vue-pro-mainmerge-release-clean\\pom.xml -pl yudao-server -am -DskipTests clean package` 已 `BUILD SUCCESS`，但随后在 clean frontend 打包前直接失败：`Missing frontend Vite CLI: D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean\node_modules\vite\bin\vite.js`。影响：本轮 v13 候选包未生成，不能继续 `deploy-test -> mark-tested -> prod -> backup`；按“先记录再修复”门禁，必须先恢复 clean frontend worktree 依赖现场并做本地回归，然后以新的 `releaseTag` 从真实页面重新执行 `build-release`。
- GREEN: clean-frontend-deps-repair-v13 -> PASS，只读核对确认 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean\node_modules` 整体缺失后，已在该 clean frontend worktree 最小执行 `pnpm install --frozen-lockfile` 恢复依赖现场；随后执行 `pnpm build:test` 返回 `Build successful. Please see dist-test directory`，证明 `vite` CLI 与 test 模式打包能力已恢复。由于发布包输入未变化、仅本机构建前置恢复，下一步无需重新修业务代码，只需以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v14`）回真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- GREEN: build-release-preview-v14 -> PASS，承接真实页面会话 `frontend-release-full-flow-mainmerge` 中已完成的表单填写与预览确认，本轮原因填写为“主程序合并后重新验证页面发布全链路：frontend依赖恢复后重建发布包（v14）”，发布标签为 `release-20260621-page-full-flow-mainmerge-v14`；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- GREEN: build-release-submit-v14 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9`；运行态 JSON 记录 `action=build-release`、`releaseTag=release-20260621-page-full-flow-mainmerge-v14`、`status=SUCCESS`、`summary=命令执行完成`。
```

### Match 8 (lines 132-134)

```text
- GREEN: build-release-manifest-v14 -> PASS，本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v14\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v14.tar`；`manifest.json` 已核对 `releaseTag=release-20260621-page-full-flow-mainmerge-v14`、`publishScope=code-only`，backend source commit=`5c52f2ec4268212e71070d57a14f006202f337c8`、frontend source commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`，且 backend/admin frontend 的 `dirty` 均为 `false`。至此新输入基线的 T3 已重新完成，下一步允许继续从真实页面执行 `deploy-test(v14)`。
- GREEN: deploy-test-preview-v14 -> PASS，真实页面已切换到“部署测试服”，操作原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v14）”；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 -ServerHost 172.30.30.58 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- GREEN: deploy-test-submit-v14 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7`；运行态 JSON 记录 `action=publish-test`、`releaseTag=release-20260621-page-full-flow-mainmerge-v14`、`status=RUNNING`、`summary=命令已提交到本机执行队列`。
```

### Match 9 (lines 136-142)

```text
- GREEN: deploy-test-runtime-verify-v14 -> PASS，只读复核测试服 `172.30.30.58` 当前运行态后确认：`/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v14`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-mainmerge-v14`；`http://172.30.30.58:48081/actuator/health` 与 `http://172.30.30.58:8081/` 均返回 HTTP `200`。至此新输入基线的 T4 已重新完成，下一步允许继续从真实页面执行 `mark-tested(v14)`。
- GREEN: mark-tested-preview-v14 -> PASS，真实页面已切换到“标记测试通过”，操作原因填写为“主程序合并后重新验证页面发布全链路：标记测试通过（v14）”，验证结论填写为“回归通过，允许上线正式服（v14）”，恢复集候选选择 `20260621-063218 · AVAILABLE`；预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 -TestConclusion 回归通过，允许上线正式服（v14） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- GREEN: mark-tested-submit-v14 -> PASS，已在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280`；页面操作记录刷新为 `RUNNING / 命令已提交到本机执行队列`。
- GREEN: mark-tested-operation-v14 -> PASS，只读核对运行态 JSON `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280.log` 后确认：本轮 `mark-tested(v14)` 已最终 `SUCCESS`，结果为 `命令执行完成`；日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14`，并已记录 `rollback-compatibility.json status=BLOCKED` 元数据。至此里程碑 T5 已按新输入基线重新完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 执行 `prod -> backup`。
- GREEN: promote-prod-submit-v14 -> PASS，承接真实页面会话 `frontend-release-full-flow-mainmerge` 中已完成的正式服预览与点击执行，`上线正式服(v14)` 生成 operation `op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1`；运行态 JSON 记录 `environment=prod`、`component=promote-prod`、`action=promote-prod`、`releaseTag=release-20260621-page-full-flow-mainmerge-v14`、`prodDryRunEvidencePath=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-mainmerge-v14-preflight-release-dry-run.json`。
- BLOCKER: promote-prod-operation-v14 -> operation `op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1` 最终 `FAILED`，运行态 JSON 收口为 `status=FAILED / summary=命令退出码非 0: 1`；本机日志确认正式服已成功跨过对象存储保护校验、远端磁盘前置、compose/.env 同步、镜像包与多条 required SQL 的前置应用，并在 `20260618_mes_edhr_release_precheck_engine.sql` 成功后继续执行 `20260618_mes_edhr_release_transaction_lifecycle.sql` 时于 line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已被脚本恢复性收口为 `LOCK_RELEASED`。影响：当前真实页面整链在同一新输入基线下仍卡在正式服上线，`release-20260621-page-full-flow-mainmerge-v14` 不能继续进入 `backup`；按“先记录再修复”门禁，下一步必须先在业务后端按严格 TDD 修复该正式 SQL 根因，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

```

### Match 10 (lines 151-153)

```text
  - 用户当前线程目标已切换为“按阶段一次性把 `D:\ProjectPackage\Int\IntRuoyi` holding 改动融合进真正的 `int_main`”。
  - 因此本任务在保留 `release-20260621-page-full-flow-mainmerge-v14` 的 `build-release -> deploy-test -> mark-tested` 通过证据和 `prod(v14)` 失败证据后，显式挂起，不再继续 `prod -> backup`。
- validation commands:
```

### Match 11 (lines 155-164)

```text
- validation results:
  - 旧任务状态已从 `in_progress` 改为 `blocked`
  - T6/T7/T8 已明确标记为 `blocked`
- covered acceptance ids:
  - `AC-01`
- known risks or blockers:
  - 若后续恢复本任务，必须重新判断 `release-20260621-page-full-flow-mainmerge-v14` 是否仍是允许继续 prod/backup 的有效输入；若业务输入或环境已变化，则需新 `releaseTag`

## 2026-06-22 Workflow Resume And Root Cause Fix v14

```

### Match 12 (lines 172-174)

```text
  - 已恢复本任务执行状态，不再沿用此前因 `int_main` 融合而设置的挂起结论。
  - 只读对比正式服/测试服 `system_menu` 后确认：正式库 `900266/900267/900268` 仍被 traveler 菜单占用，而旧 `20260618_mes_edhr_release_transaction_lifecycle.sql` 仍错误复用这组三号段。
  - clean release backend worktree 已按严格 TDD 将放行事务 `reject / withdraw / event-query` 切到独立的 `900353/900354/900355`，并同步更新 package menu merge 与 `system_role_menu` 合并逻辑；修复提交为 `49248d9f20`。
```
## doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/task.md

### Match 1 (lines 4-6)

```text

在主程序合并新代码后，重新通过运行控制台前端页面，严格执行一次“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”的完整链路，确认当前主程序基线仍然满足真实页面发布流程。全过程禁止用接口直调替代页面提交；遇到任一步失败，必须先记录到任务文档，再修复并从页面重走，直到单次链路一次性通过。

```

### Match 2 (lines 10-12)

```text
- 状态：`COMPLETED`
- 处理：上一任务完成的是“基于现有 v6 证据和远端运行态的完成审计”，证明旧链路曾完整走通；本任务是因主程序合并后担心当前基线已发生变化而重新发起的真实页面全链路重跑，属于新的高风险验证任务，需单独建档。

```

### Match 3 (lines 16-25)

```text
  - 主程序合并修改了部分代码后，重新再走一遍真实页面发布流程
  - 仍然必须按页面前端点击操作走完整链路
  - 禁止直接调接口替代页面动作
  - 每遇到问题先记录到任务文档，修复后继续从页面走
- 当前任务边界：
  - 当前验证目标基线已更新为 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 提交 `49248d9f20`（由业务后端主仓提交 `314ebb2204` cherry-pick 而来，已纳入 release transaction permission 漂移修复）
  - 当前验证目标基线是 clean release frontend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 提交 `37359a074`
  - 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前分支为 `int_main`，存在 `backup-ops` 相关未提交改动，但 `ops/deploy` 与运行控制台页面发布链路本次未发现未提交更改
  - 高风险动作前必须在 `execution-log.md` 中记录 `GREEN: experience-preflight -> PASS`

```

### Match 4 (lines 33-41)

```text
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须通过运行控制台页面按钮真实提交，命令行只允许做只读核验、失败排查和脚本/测试辅助。
  - 发布前必须确认当前运行控制台实例可用、当前业务前后端基线明确、目标环境明确、目标 `releaseTag` 唯一。
  - 每次主程序发布输入发生变化后，必须使用新的 `releaseTag` 重建并从测试服开始整链重走。
  - 发布验证不能只看健康检查，必须同时核 operation、发布包 manifest、远端 `.env`、运行镜像、页面入口和受保护边界。
  - 正式服和备份服都属于高门禁环境，必须使用已测试通过发布包，并保持 `PROD` 确认语义。

```

### Match 5 (lines 44-46)

```text
- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。若当前主程序合并引入任何发布链路问题，必须修正式代码/脚本/契约后再从页面重跑。
- `是否存在临时补丁或绕过`：否。
```

### Match 6 (lines 49-52)

```text

- `BDD: 合并后页面真实发布全链路仍可通过 -> Given 主程序前后端已合并新代码且运行控制台可访问 / When 在页面上依次执行构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 合并后若链路失败必须先记录再修复重走 -> Given 任一步页面动作或后台执行因当前主程序基线失败 / When 记录失败证据并修复 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整链路直到一次性通过。`

```

### Match 7 (lines 61-63)

```text
7. 通过页面真实上线备份服并完成运行态与受保护边界验证。`DONE`（`backup(v15)` 已完成，operation=`op-2026-06-22T134349739402400Z-5f5507e8-cd79-4630-b9fb-2e2e6fc6d3b8`）
8. 汇总本轮问题、修复、最终通过证据并执行收尾预览。`DONE`

```

### Match 8 (lines 70-72)

```text
- 正式服与备份服 `config_id=28 AND path LIKE 'showroom/%'` 的受保护 URL 边界未漂移
- 若发现问题，存在对应 BDD、失败记录、修复记录和整链重跑证据

```

### Match 9 (lines 76-84)

```text

BLOCKED：`2026-06-22` 真实页面 `deploy-test(v4)` 暴露的 `20260618_mes_edhr_label_print_queue.sql` 菜单主键冲突，已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\` 按严格 TDD 修复并通过回归，且修复提交已落盘为 `6d96efef31`。只读证据确认 `900272-900279` 被独立表单占用、`900280-900283` 被其他 eDHR 菜单占用，因此 label print 菜单已切换到独立的 `900320-900331` 号段；`pytest`、迁移策略门禁与真实页面 `build-release(v5)` 均已通过，NAS 产物目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v5`。

`2026-06-22` 继续在真实页面预览 `deploy-test(v5)` 时，测试服预览显示 `-RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1`。这组参数一度被怀疑为漂移，但随后已通过只读核对 `backend/src/main/resources/application.yaml`、`ops/deploy/publish-int-ruoyi.ps1` 环境映射、历史真实通过证据以及测试服 `show-int-ruoyi-remote-status.ps1` 运行态验证为当前测试服真实基线，实机状态返回 `running` 且当前运行标记为 `release-20260621-page-full-flow-mainmerge-v4`。因此本轮未出现新的配置阻塞，真实页面已继续提交 `deploy-test(v5)`。

`2026-06-22` 新的真实阻塞点出现在 `deploy-test(v5)` 远端执行中：operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50` 在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 357 因 `Invalid eDHR OQ/PQ button menu definition; cannot merge tenant package menu_ids` 失败。日志同时确认此前的 `20260618_mes_edhr_label_print_queue.sql` 已成功跨过，说明当前主阻塞已切换到新的 OQ/PQ 菜单定义冲突。按任务门禁，下一步必须先在业务后端按严格 TDD 修复该根因；由于发布包输入将再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 不可继续使用，修复后必须以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test`，再继续后续链路。

`2026-06-22` 上述 OQ/PQ 根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\` 按严格 TDD 修复完成并正式提交。当前只读源码与测试服真实 `system_menu` 共同证明：旧号段 `900290-900295` 中，`900290-900292` 与其他 eDHR SQL 存在直接复用，`900293-900295` 已被 `eDHR统一变更` 占用，因此 OQ/PQ 菜单整体切换到独立未占用的 `900332-900337`，并加入 `tmp_mes_edhr_oq_pq_legacy_menu_map` 吸收测试库已经落下的旧 OQ/PQ 页面/按钮残留。当前业务修复已通过 `python -X utf8 -m pytest ...test_edhr_oq_pq_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator，提交已落盘为 `0d82319b98`（功能修复）和 `3ace5094ec`（补充回归证据）。由于发布包输入已再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v6`）重新执行 `build-release -> deploy-test`，再继续后续链路。

```

### Match 10 (lines 86-90)

```text

`2026-06-22` 继续准备 `deploy-test(v6)` 前，只读核对 `manifest.json sourceRepos` 与当前源码仓状态时发现新的高风险前置差异：backend 与 admin frontend 在候选包中都被标记为 `dirty=true`。当前 `git status --short` 证明业务后端存在 DCC 文件名识别相关未提交改动（`DccControlledFileProjectCodeRecognitionService*` 等），业务前端存在 DCC 受控预览相关未提交改动（`src/views/dcc/controlled-file/detail/index.vue` 等）。影响：`release-20260621-page-full-flow-mainmerge-v6` 并非“纯已提交 merged main 基线”候选包，而是混入未提交 DCC 工作树改动的 dirty baseline；按 fail-fast 门禁，在未明确这些 dirty 改动是否应纳入本轮真实发布链路前，不应继续 `deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 为消除 dirty baseline 影响，已新建成对 clean release worktree：后端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `3ace5094ec`，`git status --short` 为空）、前端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `37359a074`，`git status --short` 为空）。同时已将本机运维台局部配置 `config/runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 切换到这两个 clean worktree，准备重启运维控制台后继续保持“页面按钮触发”的真实链路。

```

### Match 11 (lines 92-96)

```text

`2026-06-22` 真实页面 `build-release(v7)` 已成功提交到 clean worktree 基线，但 operation `op-2026-06-21T234844686010400Z-12704e02-b10c-472d-af05-cb4b5ff828c3` 在前端打包阶段失败：`D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js` 缺失，说明 clean frontend worktree 的依赖现场尚未完成 bootstrap。当前发布包未生成，不能继续测试服/正式服/备份服；必须先补齐 clean worktree 依赖，再用新的 `releaseTag` 从真实页面重新执行 build-release。

`2026-06-22` 上述 clean frontend worktree 依赖阻塞已完成现场修复：确认 `node_modules` 原先不存在后，已在 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3` 执行 `pnpm install --frozen-lockfile`，随后 `pnpm build:test` 成功输出 `Build successful. Please see dist-test directory`。当前 clean worktree 前端依赖前置条件已恢复，下一步可回真实页面用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v8`）重新提交 `build-release`。

```

### Match 12 (lines 98-100)

```text

`2026-06-22` 真实页面 `deploy-test(v8)` 已提交，operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e` 最终在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 399 失败，错误为 `Missing eDHR OQ/PQ system_menu rows; cannot merge tenant package menu_ids`。日志确认此前的 `20260613_dcc_file_view_matrix_seed`、`20260615_showroom_hall_canvas_background`、`20260618_mes_edhr_label_print_queue` 与 `20260618_post_release_role_e2e_gate` 都已成功跨过，说明当前主阻塞已切换为 OQ/PQ 菜单行缺失，而不是旧的按钮定义冲突。

```
## docs/agent-memory/project-error-prevention.md

### Match 1 (lines 1-6)

```text
# Project Error Prevention Memory

- 部署验证不能只看健康；要核 operation、manifest、镜像、迁移状态和真实入口；证据: 20260617-release
- 真实 E2E 先记失败再统一修复并整轮复测；不要边测边改；证据: 20260618-role-e2e
- 环境部署前先核本机控制台授权、secrets、确认文本、旧 jar/陈旧 RUNNING 锁；任一前置条件缺失直接阻塞；证据: 20260620-release-flow
- 构建完成就做候选包 preflight；manifest、required SQL、dry-run/隔离工作区、多环境迁移契约先过；证据: 20260621-release-flow
```

### Match 2 (lines 8-10)

```text
- 测试通过前先确认 AVAILABLE 恢复点；正式备份前单独校验 secrets、确认文本、DCC manifest 和 object inventory；证据: 20260620-release-flow
- 部署输入变更后必须新 releaseTag 重建并整链复测；旧候选包只作证据；证据: 20260621-flow
- 备份服路径固定 /mnt/intruoyi-data；发布前后核远端 .env、镜像与受保护对象边界；证据: 20260621-flow
```

### Match 3 (lines 12-18)

```text
- 不要只凭测试服通过放行正式服；涉及 system_menu/permission/租户权限合并的发布 SQL，正式服前先做正式库只读差异预审；证据: 20260621-main-merge-rerun
- 先判断发布失败是环境锁/半切换态还是业务 SQL/真实数据缺口；两类问题分开处置，别一失败就重建发布包；证据: 20260621-main-merge-rerun
- 多环境发布 workflow 中，同一 releaseTag 已过 test 但卡在 prod 时，先固化 operationId、失败 SQL、line number、锁释放结果和运行态证据，再决定是否重建发布包；证据: 20260621-main-merge-rerun
- 真实发布链路每次失败先回写 execution-log、task、test-report、request-command-log，再修复；避免多轮重试丢 releaseTag 与根因演进；证据: 20260621-main-merge-rerun
- 执行 mark-tested/prod/backup 前先核 repo-root/frontend-root 指向真实宿主机 worktree；路径漂移会在脚本解析阶段直接失败；证据: 20260621-main-merge-rerun
- Windows ACL 可能拦截普通读写和 apply_patch；高风险任务要预留 UTF-8 明确编码的受控文档写入方案，先保证失败证据能落盘；证据: 20260621-main-merge-rerun
- 环境发布 workflow 中，处理 RUNNING 锁前先核活跃进程、运行态 operation 和 RUNNING 迁移；未完成现场核验就阻塞，禁止直接改锁；证据: 20260621-main-merge-rerun
```
