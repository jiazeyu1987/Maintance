# Verification Report - 20260712 IntRuoyi code-only three-env release

## Result

PASS - `release-20260713-intmain-codeonly-three-env-r260713g-r1` completed the full code-only release chain on 2026-07-13.

## Frozen Inputs

- Maintenance: `367786f125c3075aa2507854ee5d91b4479d3c69`
- Backend: `738cfaeb04cc1b123de42283a01560b63fdac2b2`
- Frontend: `c1326e7b427ff1036bc49fcb401d6a365655099e`
- Release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g` (deleted after verification)
- External state dir: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state` (deleted after verification)

## Operations

- build-release: `op-2026-07-13T042641075294500Z-a45c6318-f096-4085-9715-38795a98fa74` -> SUCCESS
- publish-test: `op-2026-07-13T043904247039400Z-58e11f61-27d7-4475-897f-726cf69c0367` -> SUCCESS
- mark-tested: `op-2026-07-13T045527979959Z-8ae49468-8a07-46ca-a512-aab65f41f62d` -> SUCCESS
- promote-prod: `op-2026-07-13T045743664719Z-4c45114b-fa52-488d-b32a-3e39e4e00244` -> SUCCESS
- promote-backup: `op-2026-07-13T051411658807100Z-2bb859ba-86d9-492b-8b32-3e9980ebe07c` -> SUCCESS

## Manifest

- Package: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-intmain-codeonly-three-env-r260713g-r1`
- Manifest v1 and legacy manifest exist.
- `publishScope=code-only`, component=`intruoyi`.
- Source repos match frozen backend/frontend commits and `dirty=false`.
- No data directories were found in the release package.
- Change summary exists: `Release package release-20260713-intmain-codeonly-three-env-r260713g-r1`.
- Artifact size/SHA256 validation passed.

## Runtime Verification

- Test server `172.30.30.58`: `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, and `release-info.json` all matched the releaseTag.
- Production server `172.30.30.57`: `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, and `release-info.json` all matched the releaseTag.
- Backup server `172.30.30.59`: `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, and `release-info.json` all matched the releaseTag.
- Backup server data disk: `findmnt` returned `/dev/mapper/cl-home /mnt/intruoyi-data ext4`; release and data directories existed under `/mnt/intruoyi-data`.
- Runtime console UI: Playwright verified test/prod/backup version cards and three `版本变更说明` dialogs for the releaseTag with zero console errors.

## Closeout

- Runtime control restored to main path `D:\ProjectPackage\Int\IntRuoyiMaintance`.
- `http://127.0.0.1:48181/actuator/health` returned `UP`.
- `r260713g` Git registrations, physical directory, and external state directory were removed.
- Task closeout preview/apply completed with no delete, blocked, or warning items.
- Final task status is `completed`; commit scope is limited to this task's records, request log, and reusable preflight lessons.
