# Verification Report - 20260715 current HEAD code-only three-env release

## Result

PASS - `release-20260715-intmain-codeonly-three-env-r260715w-r1` completed the full code-only chain on one releaseTag.

## Operations

- `build-release`: `op-2026-07-14T165644637047400Z-6a9ac983-7cf6-4874-99ca-1f120e2b2047` = `SUCCESS`
- `publish-test`: `op-2026-07-14T171101441161400Z-3ce7c6d8-1dcc-49c9-aaa8-ca98bd35e318` = `SUCCESS`
- `mark-tested`: `op-2026-07-14T173039483650500Z-c55bbe7e-4fd4-48cd-bca6-864397c535cb` = `SUCCESS`
- `promote-prod`: `op-2026-07-14T173414012244200Z-be4dccfd-ba21-4511-9833-6ab3f07a136c` = `SUCCESS`
- `promote-backup`: `op-2026-07-15T004326358968100Z-0f5e222a-a4b0-43d6-ba36-2cc3d08dc540` = `SUCCESS`

## Manifest

- `publishScope`: `code-only`
- Backend commit: `a33743cd059b0de18f647466941603adabec8c3e`, `dirty=false`
- Frontend commit: `9a59dd50ff67e66573ecca7ffcd957b4fe15686a`, `dirty=false`
- Blocked data directories: none found in the release package.

## Environment Verification

- Test `172.30.30.58`: `.env IMAGE_TAG`, backend image, frontend image all equal releaseTag; backend health `UP`; frontend HTTP `200`; PDF worker HTTP `200`.
- Production `172.30.30.57`: `.env IMAGE_TAG`, backend image, frontend image all equal releaseTag; backend health `UP`; frontend HTTP `200`; PDF worker HTTP `200`.
- Backup `172.30.30.59`: `.env IMAGE_TAG`, backend image, frontend image all equal releaseTag; backend health `UP`; frontend HTTP `200`; PDF worker HTTP `200`; `/mnt/intruoyi-data` mounted from `/dev/mapper/cl-home`; release dir and data root exist.

## Closeout

- Runtime-control restored to main workspace jar and health `UP`.
- Release experience candidates were read; no new unique long-term lesson was required beyond existing gates.
- Task-owned temporary release worktrees `r260715v` and `r260715w` are absent from maintenance/backend/frontend Git registrations and physical worktree roots.
- Task-closeout preview/apply passed with delete, blocked, and warnings all `<none>`.
