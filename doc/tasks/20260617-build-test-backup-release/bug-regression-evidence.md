# Bug 回归证据: code-only 备份服发布门禁

## Bug

`release-202606172114-codeonly-e2e` 已通过真实前端构建、测试服发布、远端版本、迁移状态、健康检查和真实浏览器入口验收，但运行控制台“上线备份服”预览仍返回 `releaseTag 尚未测试通过`。

## Expected

用户已明确本轮不要备份、恢复、回滚或恢复集标记，只要把 code-only 发布包发布到测试服和备份服。对于 `publishScope=code-only` 的备份服代码发布，运行控制台应接受同一 `releaseTag` 的成功 `publish-test` operation 作为测试服通过证据；仍必须保留发布包 manifest/checksum、责任人、`PROD`、备份服目标参数和正式服隔离门禁。

## Reproduction

- `RED: playwright-promote-backup-preview -> FAIL`：Playwright 打开 `http://127.0.0.1:48182/`，选择“上线备份服”，填写 `releaseTag=release-202606172114-codeonly-e2e` 与 `PROD` 后点击“预览命令”，后端返回 `code=400,msg=releaseTag 尚未测试通过: release-202606172114-codeonly-e2e`。
- `RED: mvn -Dtest=RuntimeControlOriginalParityTest#promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment test -> FAIL`：新增回归测试期望 `promote-backup` 预览 `code=0`，修复前实际 `code=400`。

## Root Cause

`RuntimeControlService.validateReleasePackageAvailability(...)` 对 `PROMOTE_BACKUP` 与 `PROMOTE_PROD` 统一要求 NAS 发布包存在 `tested.json`。`mark-release-tested` 当前又强制恢复集候选；当本次只授权 code-only 发布且 NAS 没有最终恢复集候选时，测试服真实成功部署证据无法被备份服代码发布门禁识别。

## Verification

- 新增后端 MockMvc 回归测试：未测试且没有成功 `publish-test` operation 的 `promote-backup` 仍失败。
- 新增后端 MockMvc 回归测试：`publishScope=code-only` 且存在同一 `releaseTag` 成功 `publish-test` operation 时，`promote-backup` 预览成功，并仍生成 `-Environment backup`、`-ReleaseTag`、`-ConfirmText PROD`、`-RequireTested` 和远端备份服参数。
- `GREEN: mvn -Dtest=RuntimeControlOriginalParityTest#promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment test -> PASS`。
- `GREEN: mvn -Dtest=RuntimeControlOriginalParityTest test -> PASS`。
- `GREEN: mvn test -> PASS`，后端 16 个测试通过。
- `GREEN: Playwright 真实前端 promote-backup 预览 -> PASS`，命令指向 `172.30.30.59` 和 `/mnt/intruoyi-data`，不包含正式服、备份、恢复或回滚动作。

## Blockers

无当前阻塞。修复前阻塞为 `promote-backup` 只认 `tested.json`，修复后仅在 `PROMOTE_BACKUP + code-only + 同 releaseTag 成功 publish-test operation` 下放行。

## 风险与范围

范围仅限 `PROMOTE_BACKUP` 的 `code-only` 发布门禁；`PROMOTE_PROD` 不放宽，`with-data` 不放宽，备份、恢复、回滚动作不变。
