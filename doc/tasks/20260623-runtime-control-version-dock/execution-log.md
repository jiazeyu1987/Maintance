# Execution Log

## BDD

- `BDD: 构建包版本进入左下角版本栏 -> Given frontend/package.json 存在版本号 When 前端执行构建 Then 页面左下角版本栏应显示同一构建版本。`
- `BDD: 测试服与备份服版本可见 -> Given 后端 release-status 返回测试服与备份服最新发布包标签 When 页面加载完成 Then 左下角应同时显示测试服版本与备份服版本。`
- `BDD: 缺少版本时显式可见 -> Given 某环境没有上报当前发布包标签 When 页面渲染版本栏 Then 该环境应显示未上报而不是静默空白。`

## RED

- `RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q -> FAIL, frontend/vite.config.ts 尚未注入 __APP_VERSION__，页面也没有左下角版本栏。`
- `RED: mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test -> FAIL, release-status 响应缺少 $.data.prodCurrentReleaseTag 和 $.data.backupCurrentReleaseTag。`

## GREEN

- `GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q -> PASS, 前端构建版本注入与左下角版本栏契约通过。`
- `GREEN: mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test -> PASS, release-status 已返回 test/prod/backup 当前发布包标签字段。`
- `GREEN: pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck -> PASS。`
- `GREEN: pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build -> PASS, Vite 构建成功，提示 chunk size warning，不影响本次版本栏功能。`
- `GREEN: playwright-version-dock-visual -> PASS, 打开 http://127.0.0.1:48182/ 后快照显示左下角“版本信息”：软件版本 2026.06.0、测试服 release-20260623-random-erp-test-v1、正式服/备份服未上报；临时截图已目视检查并在收尾时清理。`
- `GREEN: python C:\Users\BJB110\.codex\skills\frontend-feature-delivery\scripts\validate_frontend_feature.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-version-dock\frontend-feature-evidence.md -> PASS。`
- `GREEN: python C:\Users\BJB110\.codex\skills\backend-api-delivery\scripts\validate_backend_api.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-version-dock\backend-api-evidence.md -> PASS。`
- `GREEN: python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\verify_contracts.py -> PASS。`
- `GREEN: task-closeout-cleanup preview/apply -> PASS，保留 task.md 与 execution-log.md，清理 Vite 临时日志和本次 Playwright 临时截图。`
