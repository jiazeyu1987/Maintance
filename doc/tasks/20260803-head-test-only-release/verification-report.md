# Verification Report

## Status

blocked

## Required Gates

- Git / worktree source gate: passed; source HEAD frozen as maintenance `ed7ef820d57fc0185e5c16a8be2e820a13384b15`, main program `1606947b7598eca15e904362759a7236a255dbbf`; both main workspaces dirty, so clean release worktrees were used.
- Build artifact / manifest gate: passed; `build-release` operation `op-2026-08-02T164907897014700Z-a76bd666-e3b7-449a-b77f-e4541826cd8f` SUCCESS, manifest validator `MANIFEST_VALIDATION_PASSED`, sourceRepos dirty=false.
- Test publish gate: failed; `publish-test` operation `op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241` FAILED on required SQL `20260513_dcc_base_schema.sql`, MySQL `ERROR 1062 Duplicate entry '6813' for key 'system_menu.PRIMARY'`.
- Runtime verification gate: failed for target releaseTag; release lock=`FAILED`, target release migration `FAILED/RUNNING=1`, backend/frontend containers did not move to the target releaseTag. Test server was stabilized back to previous `.env IMAGE_TAG` and remains health=UP / frontend HTTP 200.
- Console version / change notes gate: not run for target releaseTag because publish-test failed; prior release remains visible remotely.
- Issue log and experience consolidation gate: passed for blocked state; issues and preflight lessons recorded.
- Cleanup gate: blocked intentionally; release worktrees/state retained as failure evidence and failed releaseTag must not be reused.

## Final Result

Blocked. The requested test-server release did not succeed. Continue only after fixing the required SQL checksum/idempotency root cause and rebuilding a new releaseTag from a committed fix; do not reuse `release-20260803-intmain-head-test-r260803a-r1`.
