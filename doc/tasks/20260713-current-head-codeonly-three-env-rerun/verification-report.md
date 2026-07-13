# Verification Report - 20260713 current HEAD code-only three-env rerun

## Result

PASS - `release-20260713-intmain-codeonly-three-env-r260713j-r1` completed the full IntRuoyi code-only three-environment release loop from the frozen `r260713j` clean worktree input.

## Requirement Checklist

- PASS: Single releaseTag chain completed: `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`.
- PASS: Five operations are `SUCCESS`: `op-2026-07-13T074159226342200Z-a71c4f54-dbde-40dc-b946-b53d9d6bab39`, `op-2026-07-13T080624260438700Z-7ca59077-0f96-473a-bd00-643de19d9fa7`, `op-2026-07-13T082842115595300Z-4a697216-cf00-4a78-a510-24ee79f105b9`, `op-2026-07-13T083054217937200Z-3408b81b-491c-44c7-9557-75c859340e60`, `op-2026-07-13T092109387694Z-f88175d9-76a4-4689-9279-8528c32400a3`.
- PASS: Manifest v1 exists at `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-intmain-codeonly-three-env-r260713j-r1/manifest.json`; `publishScope=code-only`; backend commit `dd986dc1a03c36d279f20ee93822a666aaf628ff` and frontend commit `a86c8da404fcd0fdd712375347494a1f711b925b` are dirty=false; forbidden data directories absent.
- PASS: Test server `172.30.30.58` verified `.env IMAGE_TAG`, backend/frontend image tags, backend health=`UP`, frontend HTTP 200, PDF worker HTTP 200, release-info tag/commits, and release lock.
- PASS: Prod server `172.30.30.57` verified `.env IMAGE_TAG`, backend/frontend image tags, backend health=`UP`, frontend HTTP 200, PDF worker HTTP 200, release-info tag/commits, and release lock.
- PASS: Backup server `172.30.30.59` verified `.env IMAGE_TAG`, backend/frontend image tags, backend health=`UP`, frontend HTTP 200, PDF worker HTTP 200, release-info tag/commits, release lock, `/mnt/intruoyi-data` mount, release dir and data root.
- PASS: Runtime console restored to main workspace jar and health=`UP`; page shows `release-20260713-intmain-codeonly-three-env-r260713j-r1` and change items.
- PASS: Temporary release worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j` and state dir were removed; Git registrations are absent in maintenance/backend/frontend repos.
- PASS: Encountered issues are recorded in `execution-log.md`; reusable lessons are added to release/PowerShell preflight docs and indexed.

## Evidence Files Used Before Closeout Cleanup

- `manifest-validation-r260713j-r1.json`
- `test-runtime-verification-r260713j-r1.json`
- `prod-runtime-verification-r260713j-r1.json`
- `backup-runtime-verification-r260713j-r1.json`
- `runtime-console-page-probe-r260713j.json`
- `runtime-control-main-health-final-r260713j.json`
- `worktree-cleanup-r260713j-final.json`

## Residual Risk

- Main development workspaces advanced after the `r260713j` freeze; by user rule this release intentionally does not chase later commits and remains bound to the frozen worktree input.
- Raw operation logs were not committed; the task record preserves operation IDs, statuses, manifest and runtime verification results, and secret scan passed before closeout.
