# 任务：精简版本变更说明弹窗并修复变更说明乱码

## 任务目标

- 将运行控制台“版本变更说明”弹窗精简为只展示版本号与变更说明。
- 修复当前发布说明中 `变更说明` 的乱码与占位符串值问题，确保现有已生成发布包在页面中可正常阅读。
- 修复维护仓发布脚本对全角冒号等非 ASCII 字面量的依赖，避免后续新生成发布包再次写入乱码变更项。

## 当前状态

COMPLETED

## 经验门禁

- 来源：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`
- 适用强制门禁：
  - 发布说明相关修复不能只改页面观感，必须同时核对 manifest / release-info 契约，避免继续生成坏数据。
  - 前端改动需保持现有紧凑运维控制台风格，不引入无关重设计。
  - 本次仅做本机源码与静态/单测验证，不执行真实发布、服务器写入或其他高风险动作。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。前端弹窗精简、后端读取规范化、发布脚本移除高风险非 ASCII 字面量，三处共同收敛。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 版本变更说明弹窗只展示必要信息 -> Given 用户从版本栏打开“版本变更说明”弹窗 / When 弹窗渲染当前版本发布说明 / Then 页面只展示版本号与变更说明，不再展示构建时间、发布范围、发布组件、源码提交等额外字段。`
- `BDD: 已生成发布包的乱码变更项可读 -> Given manifest.json 中 changeSet.items 含历史乱码或占位符串值 / When 运行控制台读取并展示发布说明 / Then 用户看到的是可读的中文变更说明，而不是乱码或未替换变量名。`
- `BDD: 新生成发布包不再写入乱码标点 -> Given 维护仓发布脚本在 PowerShell 5.1 下生成 changeSet.items / When 写入 manifest.json 与 release-info.json / Then 变更说明中的中文标签和分隔符保持 UTF-8 正常文本，不再出现 mojibake。`

## 里程碑

1. M1：创建任务文档、执行日志并记录请求。`COMPLETED`
2. M2：补 RED 用例，复现弹窗冗余信息与变更说明乱码问题。`COMPLETED`
3. M3：实现前端弹窗精简、后端说明规范化与脚本编码修复。`COMPLETED`
4. M4：完成针对性验证并回写证据。`COMPLETED`
5. M5：完成收尾与提交。`COMPLETED`

## 预期验证

- `frontend/src/App.vue` 只保留版本号与变更说明相关渲染。
- `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java` 对历史乱码/占位符变更项返回可读结果。
- `ops/deploy/publish-int-ruoyi.ps1` 的 `New-ReleaseChangeSetManifest` 不再依赖高风险非 ASCII 字面量拼接。
- `python -X utf8 -m pytest scripts/tests/test_frontend_version_badge_contract.py scripts/tests/test_release_package_slimming.py -q` 通过。
- `node scripts/tests/publish_release_info_contract.test.mjs` 通过。
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusSanitizesGarbledChangeItemsAndKeepsOnlyReleaseNotesFields test` 通过。

## 风险与关注点

- 当前最新发布包 `release-20260629-2118-committed-head-v10` 的 manifest 已存在坏数据：`发布包锛?PackageTag`、`组件范围锛?Component`，说明不能只改前端模板。
- 运行控制台前端读取的是后端 `release-status` 返回值；若只在前端清洗，其他消费者仍会拿到坏说明。
- PowerShell 5.1 对 UTF-8 无 BOM 脚本中的中文标点仍有解释风险，脚本修复必须继续遵守编码安全策略。

## Final Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py -q` -> `PASS (6 passed)`
- `node D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\publish_release_info_contract.test.mjs` -> `PASS`
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#releaseStatusSanitizesGarbledChangeItemsAndKeepsOnlyReleaseNotesFields" test` -> `PASS`

## 完成结果

- “版本变更说明”弹窗已精简为只展示 `版本号` 与 `变更说明`。
- 后端 `release-status` 会将历史坏说明 `发布包锛?PackageTag`、`组件范围锛?Component` 规范化为可读中文。
- 发布脚本未来生成 `changeSet.items` 时改为 Unicode 安全拼接，不再依赖高风险非 ASCII 插值字面量。
