# 当前 HEAD 仅测试服发布验证报告

## Status

completed

## Final Release Candidate

- releaseTag：`release-20260731-smartseed-tempfix-head-test-r260731d-r1`
- 维护仓提交：`9b530038433c964ab39de19f5d30d63ad4702333`
- 主程序提交：`fa6137aa24f65bca75714d9b8c497d71ffee5d14`
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d\m`
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260731d-release-app`
- 构建发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260731-smartseed-tempfix-head-test-r260731d-r1`

## Verification Summary

- 构建来源校验通过：维护 release worktree HEAD=`9b530038433c964ab39de19f5d30d63ad4702333`，主程序 release worktree HEAD=`fa6137aa24f65bca75714d9b8c497d71ffee5d14`，两者构建前后 `git status --porcelain --ignored=no` 均为空。
- 构建与发布包校验通过：build operation `op-2026-07-31T132619952790400Z-5fdeca9b-97ac-42bc-aac0-d8803cf25169` 为 `SUCCESS`；发布包含 Manifest v1、legacy manifest 和镜像 tar；Manifest 校验 `MANIFEST_VALIDATION_PASSED`。
- Manifest / release-info 校验通过：`publishScope=code-only`，backend/frontend `sourceRepos.commit=fa6137aa24f65bca75714d9b8c497d71ffee5d14` 且 `dirty=false`；变更说明为 `Release package release-20260731-smartseed-tempfix-head-test-r260731d-r1`。
- 测试服发布通过：publish-test operation `op-2026-07-31T134347021461200Z-e8246902-6278-427a-a4c3-0ea2df178311` 为 `SUCCESS`，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 测试服真实运行态通过：远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均等于目标 releaseTag；两个容器 running；backend health=`UP`；frontend HTTP=`200`。
- 迁移与锁通过：`infra_release_operation_lock` 为 `APPLIED`；本 releaseTag 迁移状态 `APPLIED=9`、`SKIPPED_ALREADY_APPLIED=359`、`FAILED=0`、`RUNNING=0`。
- 真实页面通过：Playwright 打开测试服前端登录页，标题 `瑛泰管理系统 - 登录`，console `Errors=0`、`Warnings=0`。
- 运行控制台版本说明通过：页面显示测试服版本 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`；“版本变更说明”对话框显示本 releaseTag、`发布包：release-20260731-smartseed-tempfix-head-test-r260731d-r1` 和 `组件范围：intruoyi`。

## Failed Candidates

- `release-20260731-intmain-head-test-r260730a-r1`：`publish-test` 失败于 `20260726_dcc_codex_test_items_seed.sql` collation mismatch；未进入成功运行态。
- `release-20260731-sqlfix-head-test-r260731b-r2`：`publish-test` 失败于 `20260726_system_codex_smart_scheduling_test_items.sql` collation mismatch；不得复用。
- `release-20260731-smartseed-sqlfix-head-test-r260731c-r1`：本机重启中断 build-release，缺少 manifest 和镜像 tar，判废。
- `release-20260731-smartseed-sqlfix-head-test-r260731c-r2`：`publish-test` 失败于 MySQL `ERROR 1137 Can't reopen table: 'seed'`；不得复用。

## Closeout Result

- 任务记录、问题记录和经验沉淀已完成。
- `task-closeout-cleanup` preview/apply 已通过，最终保留 `task.md`、`execution-log.md`、`verification-report.md`。
- 运行控制台已恢复稳定主路径，PID=`50580`，`http://127.0.0.1:48181/actuator/health` 返回 `UP`；测试服访问启用，正式服/备份服访问禁用。
- 本任务 release worktree Git 注册均已移除；`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d-state`、`D:\IntRuoyiWorktree\r260731d-release-app` 物理路径均不存在。
- 本任务 Playwright 残留已清理：`r260731c-r2` CLI daemon 进程树已停止，`output\playwright\20260730-head-test-only-release` 与 `output\playwright\20260731-r260731c` 均不存在，任务相关 `.playwright-cli\page-*.yml` 快照不存在。
- 结论：本次当前 HEAD 仅测试服发布已完成，测试服真实运行态和运行控制台版本变更说明验收均通过。
