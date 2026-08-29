# 20260829 带分段耗时统计的仅测试服真实发布验证报告

## Verification Summary

- 状态：completed。
- 范围：仅测试服真实发布；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 成功 releaseTag：`release-20260829-timed-head-test-r260829k-r2`。
- 作废 releaseTag：`release-20260829-timed-head-test-r260829k-r1`，原因是 build-release 前置检查发现 clean app worktree 缺少前端依赖二进制。
- build operation：`op-2026-08-29T094711769603400Z-ded24bdd-b6fc-40f1-a43a-79f8a9232111`，SUCCESS。
- publish operation：`op-2026-08-29T100507230543400Z-9db39d71-d6b4-42f9-a030-61da96fc4c5f`，SUCCESS。
- 远端验收：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、release-info、release-status、页面版本说明全部匹配 r2。

## Timing Summary

- setupBeforeRelease：408.656s。
- r1FailureAndDependencyRecovery：491.808s。
- successfulBuildRelease：840.638s。
- successfulPublishTest：290.605s。
- successfulBuildReleasePlusPublishTest：1131.243s。
- successfulCorePlusValidation：1155.638s。
- wallClockFromWorktreeCreateToPagePass：3219.000s。
- closeoutCleanupAndVerification：30.555s。

## Evidence

- `doc/tasks/20260829-timed-test-release/timing-summary.md`
- `doc/tasks/20260829-timed-test-release/timing-summary.json`
- `doc/tasks/20260829-timed-test-release/execution-log.md`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k-state\evidence\remote-runtime-verification-summary-r2.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k-state\evidence\runtime-control-release-status-summary-r2.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k-state\evidence\runtime-console-page-verification-r2.json`

## Closeout Verification

- runtime-control：端口 `48196` 无监听，PID `47276` 不存在。
- release worktree：maintenance/app 的 `r260829k` Git 登记数均为 0，两个物理 worktree 路径均不存在。
- task cleanup：helper 脚本与 runtime-control 启动临时文件已删除；timing 与验证报告保留。
