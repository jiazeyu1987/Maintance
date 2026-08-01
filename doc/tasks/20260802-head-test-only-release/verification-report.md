# Verification Report

## Scope

仅测试服发布，构建产物必须只包含发布启动时记录的当前分支 HEAD 已提交代码。

## Status

PASS：`release-20260802-intmain-head-test-r260802a-r1` 已完成仅测试服 `build-release -> publish-test`，构建来源、manifest、版本变更说明、测试服真实运行态和页面验收均通过；未执行正式服、备份服、`mark-tested` 或 promote 动作。

## Verification Evidence

- PASS: Git preflight identified dirty primary workspaces and froze target HEADs: maintenance `dbc80bc678ae299f419b61c6264601477ea95410`, main program `baf59590f11907efae992cd65d48c067c2f3e572`.
- PASS: Worktrees: maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802a\m`, main program `D:\IntRuoyiWorktree\r260802a-release-app`; both detached at frozen HEAD and clean except ignored/generated runtime files.
- PASS: Maintenance console build: frontend typecheck/build passed; Maven tests `26` passed; Jar generated in release worktree.
- PASS: Build package: build operation `op-2026-08-01T164440373170300Z-e1e28b57-392e-4329-9a0f-7c6e1541cbe9` status `SUCCESS`; package `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260802-intmain-head-test-r260802a-r1`.
- PASS: Manifest: `manifest-validation-r260802a-r1.json` status `passed`; `manifest-summary-r260802a-r1.json` shows `publishScope=code-only`, `component=intruoyi`, requiredSqlCount `410`, artifactCount `420`, sourceRepos commit `baf59590f11907efae992cd65d48c067c2f3e572`, dirty `false`.
- PASS: Version/change notes: manifest changeSet, frontend image `/usr/share/nginx/html/release-info.json`, remote `/release-info.json`, and runtime-control release-status all show summary `Release package release-20260802-intmain-head-test-r260802a-r1` and changes `发布包：...` / `组件范围：intruoyi`.
- PASS: Publish-test: publish operation `op-2026-08-01T170326581868700Z-f11be1e5-4e3b-4335-9730-2c989e8800f5` status `SUCCESS`; recent operations for this releaseTag contain no forbidden actions.
- PASS: Runtime: `remote-runtime-verification-r260802a-r1.json` asserts `.env IMAGE_TAG`, backend/frontend image tags, containers, health, HTTP, release-info, release lock and current release migration status all match the releaseTag.
- PASS: Page: Playwright Chrome screenshot `frontend-page-r260802a-r1.png` captured the test server login page at `http://172.30.30.58:8081/`.
- PASS: Experience consolidation and closeout cleanup completed; task-closeout preview/apply reported no deletes, no blockers, no warnings; temporary release worktrees/state dir were removed and local runtime-control port returned to the task-start no-listener state.

## Final Runtime Values

- `.env IMAGE_TAG=release-20260802-intmain-head-test-r260802a-r1`
- backend image/status=`intruoyi-backend:release-20260802-intmain-head-test-r260802a-r1|running`
- frontend image/status=`intruoyi-frontend:release-20260802-intmain-head-test-r260802a-r1|running`
- backend health=`{"status":"UP"}`
- frontend HTTP=`200`
- release lock=`test-release-20260802-intmain-head-test-r260802a-r1|release-20260802-intmain-head-test-r260802a-r1|APPLIED`
- current release migration failed/running=`0`
