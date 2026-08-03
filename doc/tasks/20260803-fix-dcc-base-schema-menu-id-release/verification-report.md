# Verification Report

## Status

completed：仅测试服发布成功，主程序 `int_main` 合回、48181 恢复、本任务 worktree/state 清理和 task-closeout-cleanup 均已完成。

## Gates

- RED regression: PASS，修复前新增合同测试失败，原因指向 `id` / `6813` 固定写入。
- SQL fix: PASS，修复提交 `ae4c85511f050785f91b51f29c22c511df8e7cdc` 已移除 controlled print 菜单固定 ID。
- Migration policy gate: PASS，`migrationCount=415`。
- Maintenance console build: PASS，`scripts\build.ps1` 成功，Maven tests `26` run / `0` failures / `0` errors。
- Build and manifest: PASS，build operation `op-2026-08-03T014004195140200Z-27256ee2-7aa4-4539-a982-044bd4f86239` 为 `SUCCESS`，manifest validation passed，sourceRepos 均为 `ae4c85511f050785f91b51f29c22c511df8e7cdc` 且 `dirty=false`。
- Publish-test preview: PASS，目标为 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，未出现 `mark-tested`、`promote-prod`、`promote-backup`。
- Test publish runtime verification: PASS，publish operation `op-2026-08-03T020027072659300Z-324edfd7-4658-4822-89ed-0e35e37f7feb` 为 `SUCCESS`。
- Remote postcheck: PASS，`.env IMAGE_TAG`、backend/frontend image tag、容器 Up、backend health、frontend HTTP、release-info、release lock 与 migration 状态均通过。
- Runtime console page: PASS，Playwright 页面显示本轮 releaseTag 和变更说明。
- Mainline closeout: PASS，主程序 `E:\IntRuoyi` 的 `int_main` 已提交 `6b1fd19eb`，cached diff 只含本任务两文件，聚焦 pytest `15 passed`。
- Runtime-control restore: PASS，48181 已从 r260803b release worktree PID `33196` 恢复到主维护目录 PID `57912`，health=`UP`。
- Worktree cleanup: PASS，本任务 r260803b release/fix worktree 与 state 目录 Git 注册和物理路径均已清理。
- Task closeout cleanup: PASS，preview/apply 均 `delete=<none>`、`blocked=<none>`、`warnings=<none>`。

## Current Evidence

- 修复 worktree：`D:\IntRuoyiWorktree\20260803-fix-dcc-base-schema-menu-id-release`（已删除）
- 修复提交：`ae4c85511f050785f91b51f29c22c511df8e7cdc`
- 修复后 worktree 状态：clean
- 禁止复用失败 releaseTag：`release-20260803-intmain-head-test-r260803a-r1`
- 本轮 releaseTag：`release-20260803-dcc-menu-replay-fix-test-r260803b-r1`
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b\m`（已删除）
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260803b-release-app`（已删除）
- 发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260803-dcc-menu-replay-fix-test-r260803b-r1`
- manifest evidence：`manifest-validation-r260803b-r1.json`、`manifest-summary-r260803b-r1.json`、`frontend-release-info-image-r260803b-r1.json`
- remote evidence：`remote-release-precheck-r260803b-r1.json`、`remote-release-postcheck-r260803b-r1.json`
- page evidence：`output\playwright\r260803b-runtime-control\.playwright-cli\page-2026-08-03T02-29-55-705Z.png`、`output\playwright\r260803b-runtime-control\.playwright-cli\page-2026-08-03T02-30-19-847Z.png`

## Final Result

测试服发布成功；主线合回、48181 恢复、本任务 worktree/state 清理、task-closeout-cleanup 和最终 `completed` 标记均已完成。

最终并发复核：`E:\IntRuoyi` 后续已有其它任务提交到 HEAD `134434c78`；本任务提交 `6b1fd19eb` 仍为当前 HEAD 祖先，且提交范围仍仅为本任务两文件。
