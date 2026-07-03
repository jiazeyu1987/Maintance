# 20260703 build-publish-test-again execution log

## 请求

- 用户请求：再次构建发布到测试服务器。

## 口径

- 默认沿用上次发布口径：测试服 code-only / 不带数据。
- 本轮不执行 mark-tested、正式服、备份服、备份、恢复或回滚。

## BDD

- BDD: 测试服 code-only 发布 -> Given 本次目标提交已在后端/前端仓库提交，When 创建临时发布 worktree 并执行 build-release 和 publish-test，Then 测试服运行的 backend/frontend 镜像 tag 与本轮 releaseTag 一致，backend health=UP 且 frontend HTTP 200。
- BDD: 不带数据门禁 -> Given 本轮为 code-only / 不带数据发布，When build-release 生成 manifest，Then manifest 必须声明 publishScope=code-only 且发布包不得包含数据目录。

## 执行记录

- GREEN: task-doc-created -> PASS，已创建任务文档。

## 2026-07-03 09:14:53 +08:00 发布 worktree 与运行控制台切换

- releaseTag: release-20260703-0912-test-again
- backend worktree: D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260703-0912-test-again
- backend commit: bbbdbf3228d6d43fab613a4fcb1a3cadec0d54d7
- frontend worktree: D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260703-0912-test-again
- frontend commit: 013c26372f444e9550eaa48ac3f012b8538727e0
- runtime-control config backup: config/runtime-control.local.before-test-again-20260703-0912.yaml
- GREEN: experience-preflight -> PASS，已读取发布、构建、PowerShell、worktree、服务器访问、备份恢复门禁。
- GREEN: release-worktree-create -> PASS，两个发布 worktree 均为目标提交且 git status --porcelain 为空。
- GREEN: runtime-control-config-update -> PASS，repo-root/frontend-root 已指向本次临时发布 worktree。
- GREEN: runtime-control-health -> PASS，health=UP。

- GREEN: build-release-preview -> PASS，releaseTag=release-20260703-0912-test-again，参数包含 build-release、intruoyi、SkipDatabaseSync、SkipMinioSync、TestServerHost=172.30.30.58，并指向本次发布 worktree。

- GREEN: build-release-start -> PASS，operation=op-2026-07-03T011522088783Z-a5911d73-7521-4ff2-a583-32d202173206，releaseTag=release-20260703-0912-test-again。

- GREEN: build-release -> PASS，operation=op-2026-07-03T011522088783Z-a5911d73-7521-4ff2-a583-32d202173206，releaseTag=release-20260703-0912-test-again。
- GREEN: manifest-source-repos -> PASS，backend=bbbdbf3228d6d43fab613a4fcb1a3cadec0d54d7 dirty=false；frontend=013c26372f444e9550eaa48ac3f012b8538727e0 dirty=false；publishScope=code-only；dataDirs absent。

## 2026-07-03 16:01:20 +08:00 publish-test 首次执行失败

- BLOCKER-RESOLVED: publish-test-smart-release-report -> 首次 publish-test operation=op-2026-07-03T080000300286800Z-15fd0acf-70e5-483a-8585-82bc282ce473 FAILED，原因为启用 EnableSmartReleaseReport 但缺少 -SmartReleaseTargetConfigPath。
- 处理结论：本次用户目标为测试服 code-only 发布，不执行 Smart Release report-only；不使用现有 prod target config 误套测试服，按发布主路径关闭可选报告后重试同一 releaseTag。
## 2026-07-03 16:16:10 +08:00 publish-test 重试与测试服验证

- GREEN: publish-test-preview-retry -> PASS，预览参数不包含 -EnableSmartReleaseReport，包含 -Environment test、-ServerHost 172.30.30.58、-RemoteAppDir /opt/intruoyi/runtime。
- GREEN: publish-test -> PASS，operation=op-2026-07-03T080239101028700Z-e0b55e76-a62e-4445-be42-248ed979a170，releaseTag=release-20260703-0912-test-again。
- GREEN: manifest-final-check -> PASS，manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260703-0912-test-again\manifest.json，publishScope=code-only，backend=bbbdbf3228d6d43fab613a4fcb1a3cadec0d54d7 dirty=false，frontend=013c26372f444e9550eaa48ac3f012b8538727e0 dirty=false，dataDirs absent。
- GREEN: remote-runtime-verification -> PASS，测试服 .env IMAGE_TAG=release-20260703-0912-test-again，backend image=intruoyi-backend:release-20260703-0912-test-again，frontend image=intruoyi-frontend:release-20260703-0912-test-again，backend health={"status":"UP"}，frontend HTTP 200，pdf worker HTTP 200 application/javascript，release dir exists=yes。
- GREEN: external-http-verification -> PASS，http://172.30.30.58:48081/actuator/health HTTP 200，http://172.30.30.58:8081/ HTTP 200，pdf worker HTTP 200 application/javascript。
- 边界确认：本轮仅执行 build-release 与 publish-test；未执行 mark-tested、正式服、备份服、备份、恢复或回滚。
## 2026-07-03 16:25:20 +08:00 收尾清理

- GREEN: runtime-control-config-restore -> PASS，config/runtime-control.local.yaml 已恢复 repo-root=D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro、frontend-root=D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3，/actuator/health=UP。
- GREEN: release-worktree-cleanup -> PASS，已删除后端临时发布 worktree D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260703-0912-test-again，已删除前端临时发布 worktree D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260703-0912-test-again；后端/前端主仓 worktree list 均不再登记本次临时发布 worktree。
- GREEN: task-closeout-preview -> PASS，task-closeout-cleanup preview 仅保留 task.md 与 execution-log.md，无 delete、blocked、warnings。