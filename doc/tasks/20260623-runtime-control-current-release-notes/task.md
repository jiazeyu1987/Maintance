# 任务：运行控制台展示当前版本变动说明

## Goal

在运行控制台左下角版本栏中，为当前测试服、正式服、备份服正在运行的版本增加可查看的变动说明；只展示当前运行版本，不做历史版本库。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-restart-to-commit\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成本机控制台更新，本任务在其版本栏基础上继续增强。

## Scope

- 后端 `release-status` 增加当前测试服、正式服、备份服版本对应的发布说明数据。
- 说明来源优先使用发布包 `manifest.json` 的 `changeSet.summary` 与 `changeSet.items`，同时带出构建时间、发布范围、组件和源码仓提交信息。
- 前端左下角版本栏提供“查看变更”入口，弹窗展示对应环境的当前版本说明。

## Non-Scope

- 不做历史版本列表。
- 不改发布服务器、测试服、正式服、备份服运行态。
- 不修改发布包生成规则。
- 不新增 mock 成功或默认成功说明。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`
- 强制门禁摘录：
  - 运行控制台修改后必须重新构建并重启 48181 才算当前进程已加载新逻辑。
  - 发布包信息必须来自实际 manifest，不能把页面硬编码说明当发布包说明。
  - 前端保持运维控制台的紧凑、蓝灰、可扫描风格。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺少发布包或缺少变动说明时明确返回不可用状态和原因。
- `是否从根因和长期维护角度解决`：是；从发布包 manifest 读取说明，与构建包绑定。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 查看测试服当前版本变动说明 -> Given 测试服当前运行 releaseTag 对应发布包 manifest 含 changeSet When 打开版本栏变更弹窗 Then 弹窗显示该 releaseTag 的摘要和变动条目。`
- `BDD: 只展示当前运行版本说明 -> Given 发布包仓库存在多个历史包 When release-status 返回当前环境说明 Then test/prod/backup 仅绑定各自 currentReleaseTag 的说明。`
- `BDD: 变动说明缺失时显式暴露 -> Given 当前 releaseTag 对应发布包缺少 manifest 或 changeSet When 查看变更 Then 页面显示缺失原因而不是伪造说明。`

## Milestones

1. 记录任务文档、证据文件和 RED 测试。`COMPLETED`
2. 后端扩展 release-status 当前版本说明契约。`COMPLETED`
3. 前端增加版本栏变更弹窗。`COMPLETED`
4. 完成回归验证、收尾清理和提交。`COMPLETED`

## Expected Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q`
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly test`
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test`
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck`
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build`

## Current Status

COMPLETED：已完成当前测试服、正式服、备份服版本变动说明展示，并已更新本机 48181 运行控制台。

## Final Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q` -> PASS。
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly test` -> PASS。
- `mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test` -> PASS。
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck` -> PASS。
- `pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build` -> PASS，产物为 `index-BriPWzK2.js` / `index-DSQLovY0.css`。
- `python C:\Users\BJB110\.codex\skills\backend-api-delivery\scripts\validate_backend_api.py --evidence ...\backend-api-evidence.md` -> PASS。
- `python C:\Users\BJB110\.codex\skills\frontend-feature-delivery\scripts\validate_frontend_feature.py --evidence ...\frontend-feature-evidence.md` -> PASS。
- `powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1` -> PASS，Maven 全量测试 `23` 个通过，jar 已重新打包。
- 本机运行态复核 -> PASS，当前 `48181` 监听 PID `46892`，首页加载 `assets/index-BriPWzK2.js`，JS 含“查看变更”和“版本变更说明”，release-status 已返回 `test/prod/backupCurrentReleaseNotes`。
- `task-closeout-cleanup` preview/apply -> PASS，保留 `task.md` 与 `execution-log.md`，清理本任务 evidence 临时交付文件。
