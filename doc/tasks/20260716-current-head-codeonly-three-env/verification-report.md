# Verification Report - 20260716-current-head-codeonly-three-env

## Final Result

PASS - same releaseTag release-20260716-intmain-codeonly-three-env-r260716d-r1 completed the full code-only three-environment release chain.

## Operations

- build-release: SUCCESS, op-2026-07-15T173559012275200Z-74da6163-9f2e-44d7-9272-8a77c42763f6.
- publish-test: SUCCESS, op-2026-07-15T175214013013100Z-2d520056-36d1-480c-b108-8ad462751cbb.
- mark-tested: SUCCESS, op-2026-07-15T181231613483300Z-0ffaaffb-2a0f-4b35-8dd0-54706eacc0b9.
- promote-prod: SUCCESS, op-2026-07-15T181510607361700Z-b06c84b1-91cf-43ca-8468-84cfe5eeb1f8.
- promote-backup: SUCCESS, op-2026-07-15T183245550228300Z-9a8bc4e4-339b-4cbe-9ef1-aac15e8e8bb5.

## Build Package

- Manifest: E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260716-intmain-codeonly-three-env-r260716d-r1\manifest.json.
- publishScope: code-only.
- Source repos: backend 8241c4331124d7f97c597bdee0612013f53498ef, frontend 8853c30b58bce5c5d32473ce25425f71ee7784c9, both dirty=false.
- No-data package check: no database, minio, data, package-data, or Website data directory detected; top-level dirs are required-sql, resources, runtime-env, smoke.

## Environment Verification

- Test 172.30.30.58: .env IMAGE_TAG, backend image, frontend image, backend health UP, frontend HTTP 200, PDF worker HTTP 200, and release-info tag all matched release-20260716-intmain-codeonly-three-env-r260716d-r1.
- Prod 172.30.30.57: .env IMAGE_TAG, backend image, frontend image, backend health UP, frontend HTTP 200, PDF worker HTTP 200, and release-info tag all matched release-20260716-intmain-codeonly-three-env-r260716d-r1.
- Backup 172.30.30.59: .env IMAGE_TAG, backend image, frontend image, backend health UP, frontend HTTP 200, PDF worker HTTP 200, release-info tag all matched release-20260716-intmain-codeonly-three-env-r260716d-r1; /mnt/intruoyi-data mounted from /dev/mapper/cl-home as ext4, release dir and data root exist.

## Closeout State

- Runtime-control restored to main maintenance workspace and health is UP on http://127.0.0.1:48181/actuator/health.
- Temporary r260716a/b/c/d release worktrees and state directories removed.
- Remaining concurrent worktrees under D:\ProjectPackage\Int\IntRuoyiWorktrees are unrelated and preserved.
## Task Closeout

- task-closeout cleanup preview/apply: PASS.
- Kept core records: `task.md`, `execution-log.md`, `verification-report.md`.
- Removed task-local temporary evidence files after their summaries were written into the execution log and verification report.
- Task status: completed.