# 任务：运行控制台左下角版本号

## Goal

在运行控制台左下角增加版本信息，显示本次前端构建包版本，并同步展示测试服/备份服当前运行的发布包标签，让用户直接看出当前软件与服务器版本。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\task.md`
- 状态：`BLOCKED`
- 处理：已确认上一任务阻塞点是测试服写入授权与真实联调前置条件，不影响本任务的本机前端/后端版本展示修复。

## Scope

- 前端：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\App.vue`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\styles.css`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\vite.config.ts`
- 后端：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeDtos.java`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java`
- 回归测试：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\test\java\com\intruoyi\maintenance\runtime\RuntimeControlOriginalParityTest.java`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py`

## Non-Scope

- 不修改数据库 schema。
- 不改服务器部署脚本。
- 不新增兜底版本值或静默降级。
- 不调整发布、备份、恢复流程本身。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`
- 强制门禁摘录：
  - 前端页面必须遵循 IntPP 生产单风格，页面底部版本信息要清晰但不抢占主工作区。
  - 版本展示必须来源于构建包与运行态数据，缺字段时显式暴露，不得静默伪装成功。
  - 本任务不涉及服务器写入、发布、恢复或真实 E2E；若后续要做服务器联调，再补 `experience-preflight` 记录。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少构建版本或运行版本字段时只显示显式的未上报状态，不做静默兜底。
- `是否从根因和长期维护角度解决`：是。通过构建注入和后端状态字段把版本信息放进正式数据链路。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 构建包版本进入左下角版本栏 -> Given frontend/package.json 存在版本号 When 前端执行构建 Then 页面左下角版本栏应显示同一构建版本。`
- `BDD: 测试服与备份服版本可见 -> Given 后端 release-status 返回测试服与备份服最新发布包标签 When 页面加载完成 Then 左下角应同时显示测试服版本与备份服版本。`
- `BDD: 缺少版本时显式可见 -> Given 某环境没有上报当前发布包标签 When 页面渲染版本栏 Then 该环境应显示未上报而不是静默空白。`

## Milestones

1. 写出 RED 契约测试，证明当前页面没有版本栏且 release-status 版本字段不足。`COMPLETED`
2. 补齐后端 release-status 的测试服/正式服/备份服版本字段。`COMPLETED`
3. 注入前端构建版本并渲染左下角版本栏。`COMPLETED`
4. 跑通类型检查、后端回归与前端构建验证。`COMPLETED`

## Expected Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q`
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test`
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck`
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build`

## Current Status

COMPLETED：已完成左下角版本栏、后端版本字段扩展、前后端契约测试、前端 typecheck/build 与 Playwright 视觉验证。

## Final Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q` -> PASS。
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test` -> PASS。
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck` -> PASS。
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build` -> PASS。
- Playwright 视觉验证 -> PASS，快照确认左下角版本栏显示构建版本和环境版本；临时截图已在收尾时清理。
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\verify_contracts.py` -> PASS。
