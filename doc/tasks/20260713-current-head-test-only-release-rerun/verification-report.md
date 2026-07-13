# Verification Report

## Current Status

Completed. Test release succeeded, experience consolidation is complete, task-closeout apply passed, runtime-control is restored to the main workspace, temporary release worktree/state paths are removed, and final HTTP/release-info recheck passed.

## Frozen Inputs

- Maintenance: `efa0cfd79c75a48de807a40e1e80deefff63e6ee`
- Backend: `a69271e228c7738cd0ade0e12f9b7f8a85aec205`
- Frontend: `627f644d542902481809441efe5c1371f6a7d28c`
- Worktree root: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u`

## Build Evidence

- Release tag: `release-20260713-current-head-test-r260713u`
- Build operation: `op-2026-07-13T130433994984600Z-0ddaec3f-7a3b-465a-a40b-182c572b3508` = `SUCCESS`
- Manifest: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-current-head-test-r260713u\manifest.json`
- Manifest checks: releaseTag/component/publishScope/sourceRepos/artifacts all passed; forbidden data dirs absent.

## Publish Evidence

- Publish-test operation: `op-2026-07-13T132238031788800Z-7427e313-5a0e-4bae-8bc3-be5decaa3c0a` = `SUCCESS`
- Scope boundary: only test server publish executed; no `mark-tested`, `promote-prod`, or `promote-backup`.

## Runtime Evidence

- Test server `.env IMAGE_TAG`: `release-20260713-current-head-test-r260713u`
- Backend image: `intruoyi-backend:release-20260713-current-head-test-r260713u`
- Frontend image: `intruoyi-frontend:release-20260713-current-head-test-r260713u`
- Containers: backend/frontend running.
- Backend health: `UP`
- Frontend HTTP: `200`
- Release info: releaseTag/publishScope/backend commit/frontend commit/dirty flags all matched.
- Release lock: `test APPLIED test-release-20260713-current-head-test-r260713u`
- Target release failed migrations: `0`
- Playwright: test frontend login page HTTP 200 with console errors=0; runtime-control version dialog visible with current releaseTag and change notes.

## Issues

Issues P001-P008 are recorded in `task.md`; reusable items have been promoted to preflight experience docs.

## Experience Consolidation

- Release/build gates: local config absence, generated runtime dirty output, package lookup vs UNC false negative, historical migration separation, and long operation polling.
- PowerShell/SSH gates: Python f-string literal braces in remote verification carriers.
- Test runtime gates: split user-visible version/change notes from release-info/manifest source commit verification.
- Index routing: new keywords route to the updated preflight documents.

## Closeout Evidence

- task-closeout apply: status=applied, delete=<none>, blocked=<none>, warnings=<none>.
- Runtime-control restored: PID 38540, main workspace jar/config, health=UP.
- Worktree cleanup: r260713u maintenance/backend/frontend Git registrations absent; physical root and state dir absent.
- Final lightweight runtime recheck: frontend HTTP 200; release-info tag/publishScope/sourceRepos commits matched frozen HEAD and dirty=false.
- Closeout issue: P008 records Windows `Directory not empty` residual cleanup and prevention gate.
