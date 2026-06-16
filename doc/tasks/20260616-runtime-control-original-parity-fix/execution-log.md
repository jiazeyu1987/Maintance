# Execution Log

- Task ID: `20260616-runtime-control-original-parity-fix`
- Created: `2026-06-16`

## BDD

- BDD: release-status 版本字段对齐 -> Given 发布包列表包含 tested 包且 overview 有测试服当前版本, When 请求 `/release-status`, Then 返回 `testCurrentReleaseTag` 与 `latestTestedReleaseTag`。
- BDD: mark-tested 服务端解析当前测试服版本 -> Given 当前测试服 releaseTag 已由 overview 提供, When 前端提交 `mark-release-tested`, Then 后端使用当前测试服 releaseTag 而不是客户端任意 releaseTag。
- BDD: 非动作字段严格拒绝 -> Given 请求携带当前动作不支持的字段, When 预览命令, Then 后端按原版 fail fast。
- BDD: 恢复候选 DCC 链必须完整 -> Given `dcc-backup-manifest.json` 的 `chainStatus` 不是 `COMPLETE`, When 构造恢复候选, Then 候选状态为 `BLOCKED`。
- BDD: 前端按动作提交字段 -> Given 用户选择非构建动作, When 生成请求 payload, Then 不提交 `includeOnlyOffice` / `includeShowroomBuildPackage` 等构建专属字段。

## TDD Evidence

- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> FAIL, `release-status` 的 `testCurrentReleaseTag/latestTestedReleaseTag` 为空，非动作字段未被拒绝，DCC `chainStatus=BROKEN` 候选仍为 `AVAILABLE`。
- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL, 前端缺少按动作裁剪 payload 的 `operationSupportsPublishScope(selectedAction.value.action)` 等原版契约标记。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS, 7 tests / 0 failures。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS。
- GREEN: `pnpm --dir frontend typecheck` -> PASS。
- GREEN: `pnpm --dir frontend build` -> PASS，Vite 产物构建成功，存在 chunk size warning。
- GREEN: `mvn -f backend/pom.xml test` -> PASS，12 tests / 0 failures。
- GREEN: `experience-preflight -> PASS`，本任务只执行本地契约测试、静态检查、前端构建和命令预览契约验证；未执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- GREEN: `task-closeout-cleanup --mode preview` -> PASS，无删除项、无阻塞、无警告。
- GREEN: `task-closeout-cleanup --mode apply` -> PASS，无删除项、无阻塞、无警告。

## Outstanding Blockers

- None.
