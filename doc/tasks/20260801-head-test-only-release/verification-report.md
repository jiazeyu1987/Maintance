# Verification Report

## Current Result

PASS：最终 releaseTag `release-20260801-frozen-dcc-column-collation-r260801e-r1` 已完成仅测试服 `build-release -> publish-test`，测试服真实运行态、版本号、变更说明和清理收尾均通过；未执行正式服、备份服、`mark-tested` 或 promote 动作。

## Evidence

- 发布输入：本轮发布从冻结 worktree 开始，维护仓冻结 HEAD=`cb85bb0dbf2f36931ff2bc0aff75a4e96b5bd331`；主程序修复链最终 HEAD=`f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce`，source worktree 在构建前 `git status --short --branch` clean。
- 构建结果：`build-release` operation=`op-2026-08-01T075619071613500Z-8ce3eda8-87d7-412c-8daf-b944d4d737df` 为 `SUCCESS`；发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-frozen-dcc-column-collation-r260801e-r1`。
- Manifest：`manifest-validation-r260801e-r1.json` 为 `passed`；`manifest-summary-r260801e-r1.json` 显示 `publishScope=code-only`，backend/frontend `sourceRepos[*].commit=f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce` 且 `dirty=false`。
- 变更说明：发布包 `release-info` / 运行控制台 release-status 显示 summary=`Release package release-20260801-frozen-dcc-column-collation-r260801e-r1`，changes 包含 `发布包：release-20260801-frozen-dcc-column-collation-r260801e-r1` 和 `组件范围：intruoyi`。
- 发布结果：`publish-test` operation=`op-2026-08-01T082221679621900Z-bdfeb32d-6378-404e-af3c-3bb8b8407300` 为 `SUCCESS`；最近 operation 中未出现 `mark-tested`、`promote-prod`、`promote-backup`。
- 测试服运行态：`remote-runtime-verification-r260801e-r1.json` 所有断言通过；`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=`UP`、frontend HTTP=`200`、页面标题、`release-info.json` 均匹配 r260801e。
- 发布锁与迁移：最新测试环境 release lock 为 `APPLIED`；r260801e migration counts 为 `APPLIED=2`、`SKIPPED_ALREADY_APPLIED=369`、`FAILED/RUNNING=0`。
- 运行控制台：`runtime-control-release-status-r260801e-r1.json` 显示 `testCurrentReleaseTag=release-20260801-frozen-dcc-column-collation-r260801e-r1` 且 notes 可用；48181 已恢复主维护路径 PID=`45648`，health=`{"status":"UP"}`。
- 主线合并：修复提交已合回 `E:\IntRuoyi` 的 `int_main`，merge commit=`ac8457724d16d287f5d65013ba304f77f3786e7b`；`python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_dcc_file_category_match_rule_seed_sql.py IntRuoyiBackend\script\tests\test_codex_smart_scheduling_test_items_seed.py -q` -> `8 passed`；`git diff --check HEAD~1..HEAD` 通过。
- 清理收尾：`worktree-cleanup-r260801e-r1.json` 为 `passed=true`；r260801a/r260801b release/fix worktree 与 state dir 的 Git 注册和物理目录均不存在；其他并发 worktree 未清理。

## Conclusion

本次仅测试服发布成功，构建产物可追溯到已提交源代码，测试服真实运行态与运行控制台版本说明均通过。失败 releaseTag `release-20260801-intmain-head-test-r260801a-r2`、`release-20260801-frozen-smartseed-fix-r260801b-r1`、`release-20260801-frozen-smartseed-tempfix-r260801c-r1`、`release-20260801-frozen-dcc-category-collation-r260801d-r1` 均不得复用。
