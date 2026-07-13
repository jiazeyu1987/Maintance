# Verification Report - r260713v Code-only Three-environment Release

## Summary

- Release tag: `release-20260713-intmain-codeonly-three-env-r260713v-r1`
- Scope: `code-only`, `Component=intruoyi`, `SkipDatabaseSync`, `SkipMinioSync`
- Result: PASS for build, test, mark-tested, prod, and backup operations.

## Operation Chain

- Build-release: `op-2026-07-13T143350577788200Z-3d861300-83a9-4b8a-a453-96b7ae54e225` = `SUCCESS`
- Publish-test: `op-2026-07-13T145223142838Z-f31e7309-5106-4c25-ac53-5ddbf4efefa3` = `SUCCESS`
- Mark-tested: `op-2026-07-13T150911502243700Z-029f98c3-29d6-4104-9f34-d36bfe281ea1` = `SUCCESS`
- Promote-prod: `op-2026-07-13T151108922995700Z-109cd33a-e66b-4297-b73d-9ea4d6f2f488` = `SUCCESS`
- Promote-backup: `op-2026-07-13T152649835481600Z-c8a04317-1b9d-4ed7-8b43-61002803e87c` = `SUCCESS`

## Manifest

- Path: `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-intmain-codeonly-three-env-r260713v-r1/manifest.json`
- `publishScope=code-only`
- Backend source commit: `a69271e228c7738cd0ade0e12f9b7f8a85aec205`, dirty=false
- Frontend source commit: `69df78f24279d4f144fa252230f6571202409bf7`, dirty=false
- Artifact hashes: 295 checked, 0 failures
- Forbidden data directories: absent

## Runtime Verification

- Test `172.30.30.58`: `.env IMAGE_TAG`, backend/frontend images, health, frontend HTTP, PDF worker HTTP, release-info source commits, release lock and target migration failures all passed.
- Prod `172.30.30.57`: `.env IMAGE_TAG`, backend/frontend images, health, frontend HTTP, PDF worker HTTP, release-info source commits, release lock and target migration failures all passed.
- Backup `172.30.30.59`: `.env IMAGE_TAG`, backend/frontend images, health, frontend HTTP, PDF worker HTTP, release-info source commits, release lock, target migration failures, `/mnt/intruoyi-data` mount, release dir and data root all passed.

## Notes

- First backup verification script failed because the backup host lacks `python3`; the verification carrier was rewritten to pure shell and passed without changing release state.
- Runtime-control was restored to the main workspace path after release verification.
- Temporary release worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v` and state dir `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v-state` were removed after Git registrations cleared.
- task-closeout preview/apply passed with blocked=<none> and warnings=<none>.
