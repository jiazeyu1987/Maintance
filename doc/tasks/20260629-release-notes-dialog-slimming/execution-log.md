# 执行日志：20260629-release-notes-dialog-slimming

## 2026-06-29

- BDD: 版本变更说明弹窗只展示必要信息 -> Given 用户从版本栏打开“版本变更说明”弹窗 / When 弹窗渲染当前版本发布说明 / Then 页面只展示版本号与变更说明，不再展示构建时间、发布范围、发布组件、源码提交等额外字段。
- BDD: 已生成发布包的乱码变更项可读 -> Given manifest.json 中 changeSet.items 含历史乱码或占位符串值 / When 运行控制台读取并展示发布说明 / Then 用户看到的是可读的中文变更说明，而不是乱码或未替换变量名。
- BDD: 新生成发布包不再写入乱码标点 -> Given 维护仓发布脚本在 PowerShell 5.1 下生成 changeSet.items / When 写入 manifest.json 与 release-info.json / Then 变更说明中的中文标签和分隔符保持 UTF-8 正常文本，不再出现 mojibake。

- 命令记录：读取 `bug-regression-fix-loop`、`frontend-feature-delivery` 技能，以及 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，确认本次任务需要同时覆盖前端展示、后端 release-status 契约和发布脚本编码安全。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260629-build-publish-test-server-committed-head/task.md` 已 `COMPLETED`，允许新建本次任务目录 `doc/tasks/20260629-release-notes-dialog-slimming/`。
- 命令记录：只读检查当前实现 `frontend/src/App.vue`、`backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java`、`ops/deploy/publish-int-ruoyi.ps1` 与现有契约测试，确认弹窗当前仍展示构建时间/发布范围/发布组件/源码提交，且 `manifest.json changeSet.items` 读取无历史乱码规范化逻辑。
- 命令记录：只读读取本地候选包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260629-2118-committed-head-v10\manifest.json`，确认当前真实坏数据为 `发布包锛?PackageTag`、`组件范围锛?Component`。
- RED: `python -X utf8 -m pytest scripts\tests\test_frontend_version_badge_contract.py scripts\tests\test_release_package_slimming.py -q` -> FAIL，新增断言命中当前弹窗仍未展示 `版本号`，且发布脚本尚未使用 Unicode 安全的全角冒号拼接。
- RED: `mvn -f backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#releaseStatusSanitizesGarbledChangeItemsAndKeepsOnlyReleaseNotesFields" test` -> FAIL，`$.data.testCurrentReleaseNotes.changes[0]` 实际返回 `发布包锛?PackageTag`，证明后端仍原样透传坏说明。
- 命令记录：实现前端弹窗精简，仅保留 `版本号` 与 `变更说明` 区块；移除弹窗中的构建时间、发布范围、发布组件、源码提交与缺失信息展示。
- 命令记录：实现后端发布说明规范化，针对历史 `锛?`/占位符 `PackageTag`、`Component` 变更项返回可读中文说明。
- 命令记录：实现发布脚本 `New-ReleaseChangeSetManifest` 的 Unicode 安全全角冒号拼接，避免 PowerShell 5.1 下再次写入 mojibake。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_frontend_version_badge_contract.py scripts\tests\test_release_package_slimming.py -q` -> PASS，`6 passed in 0.04s`。
- GREEN: `node scripts\tests\publish_release_info_contract.test.mjs` -> PASS，3 个契约测试全部通过。
- GREEN: `mvn -f backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#releaseStatusSanitizesGarbledChangeItemsAndKeepsOnlyReleaseNotesFields" test` -> PASS，后端 release-status 返回已规范化中文变更项。
