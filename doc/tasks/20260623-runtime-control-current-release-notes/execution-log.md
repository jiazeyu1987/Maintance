# Execution Log

## BDD

BDD: 查看测试服当前版本变动说明 -> Given 测试服当前运行 releaseTag 对应发布包 manifest 含 changeSet When 打开版本栏变更弹窗 Then 弹窗显示该 releaseTag 的摘要和变动条目。

BDD: 只展示当前运行版本说明 -> Given 发布包仓库存在多个历史包 When release-status 返回当前环境说明 Then test/prod/backup 仅绑定各自 currentReleaseTag 的说明。

BDD: 变动说明缺失时显式暴露 -> Given 当前 releaseTag 对应发布包缺少 manifest 或 changeSet When 查看变更 Then 页面显示缺失原因而不是伪造说明。

## Preflight

GREEN: experience-preflight -> PASS，已读取 experience-index、release-build-preflight-lessons、project-error-prevention、FRONTEND_STYLE；本任务仅本机代码修改与测试，不执行远端发布或服务器写入。

## RED

RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q -> FAIL，前端 App.vue 尚未绑定 test/prod/backupCurrentReleaseNotes，也没有查看变更弹窗。

RED: mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly test -> FAIL，release-status 响应缺少 $.data.testCurrentReleaseNotes。

## GREEN

GREEN: mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly test -> PASS，release-status 返回 test/prod/backupCurrentReleaseNotes，且不混入历史版本说明。

GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q -> PASS，前端版本栏契约已包含当前版本说明字段、查看变更入口和弹窗样式。

GREEN: mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test -> PASS，原 test/prod/backupCurrentReleaseTag 字段保持兼容。

GREEN: pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck -> PASS。

GREEN: pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build -> PASS，生产构建通过，Vite 仅保留既有 chunk size warning。

GREEN: backend/frontend evidence validation -> PASS，backend-api-evidence.md 与 frontend-feature-evidence.md 均通过技能校验。

GREEN: powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1 -> PASS，前端 typecheck/build 通过，Maven 全量测试 23 个通过，jar 重新打包成功。

GREEN: restart-runtime-control -> PASS，当前 48181 运行 PID 46892，首页加载 assets/index-BriPWzK2.js，JS 包含“查看变更”“版本变更说明”和三类 notes 字段。

GREEN: verify-runtime-control-api -> PASS，release-status 返回 test/prod/backupCurrentReleaseNotes；测试服 notes status=AVAILABLE，summary=Release package release-20260623-random-erp-test-v1。

GREEN: task-closeout-cleanup preview/apply -> PASS，保留 task.md 与 execution-log.md，删除本任务 backend-api-evidence.md、frontend-feature-evidence.md。
