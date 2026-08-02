# Verification Report

## Scope

仅测试服重新发布，构建产物必须只包含本次发布启动时记录的当前分支 HEAD 已提交代码；2026-08-02 09:58 之前发布实现不作为完成证据。

## Status

PASS - completed

## Verification Evidence

- Source freeze: maintenance `int_main` HEAD `b25214b3de563aa83e3bac9eacf401da49c5f476`; app `int_main` HEAD `b99246f58ff7d556caee24307ec89b662d0427e3`; both dirty main workspaces isolated into clean release worktrees.
- Build: maintenance console build passed with Maven tests `26/26`; build-release operation `op-2026-08-02T021129767983200Z-e204dce2-6be8-4a13-9428-063c4070ae40` ended `SUCCESS`.
- Package: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260802-intmain-head-test-r260802b-r1`; manifest validation passed with `artifactHashChecked=420`, `missing=0`, `sizeMismatch=0`, `hashMismatch=0`, sourceRepos dirty=false and commit `b99246f58ff7d556caee24307ec89b662d0427e3`.
- Publish: publish-test operation `op-2026-08-02T022945019393Z-852720a9-61ba-4c79-8cc5-245ced64c078` ended `SUCCESS`; no `mark-tested`, `promote-prod`, `promote-backup`, production or backup deployment action executed.
- Runtime: test server `.env IMAGE_TAG`, backend/frontend actual image tag, container status, backend health `UP`, frontend HTTP `200`, release-info, release lock `APPLIED`, current release migration failed/running `0`, frontend page and runtime console version/change notes all match `release-20260802-intmain-head-test-r260802b-r1`.
- Issue/experience: all observed release problems are recorded in `execution-log.md`; preflight lessons and keyword routes were updated in `docs/test-release-preflight.md`, `docs/release-build-preflight-lessons.md`, `docs/powershell-preflight-lessons.md`, and `docs/experience-index.md`.

## Final Closeout

- task-closeout cleanup preview/apply passed with no blocked paths or warnings.
- Task-owned runtime-control was stopped and `127.0.0.1:48181` returned to `NO_LISTENER`.
- r260802b maintenance/app release worktree registrations were removed; physical worktree roots and state dir no longer exist.
- Final remote recheck after local cleanup passed for `.env IMAGE_TAG`, backend/frontend image tags, health, HTTP, release-info, release lock and migration failed/running count.
