# P4 Independent Verification Report

- Task: 20260924-two-button-release-delivery
- Role: blind-first-pass independent tester
- Date: 2026-09-25 (Asia/Shanghai)
- App worktree: `D:\\IntRuoyiWorktree\\two-button-release-delivery-app`
- Maintenance worktree: `D:\\IntRuoyiWorktree\\two-button-release-delivery-maintenance`
- App commit: `b984f85f401eb0033f71b485d4e5f7de601b780a`
- Maintenance commit: `d316da978e5bcf169d08ec33b110132a124a103e`
- Scope: read-only PRD/test-plan first; no product-code changes; no `execution-log.md`/`task-state.json` read; no remote publish; no production access; no business-database writes.

## Preflight

- GREEN: experience-preflight -> PASS
  - Read only `prd.md`, `test-plan.md`, and indexed preflight/worktree/login guidance before verification.
  - Both task worktrees are clean on the expected task branch.
  - Python/pytest, Maven/Java, pnpm/Node and Playwright 1.60.0 are available in the app worktree.
  - Frontend dependencies and maintenance test files are present.
  - No remote publish, production access, API-only substitution, mock data, or business-database write was attempted.
- BLOCKER: p4-runtime-preflight -> expected `tests/e2e/runtime-control-two-entry-release.e2e.cjs` is absent from the app worktree, and the independent app worktree ports `48208`/`8208` are not reachable. Existing legacy runtime-control E2E files are not equivalent to the approved two-entry fault case, so they were not substituted. Real-browser P4 fault regression cannot be claimed without the required entry and authenticated service.

## Verification log

- GREEN: maintenance-input-tests -> PASS
  - Command: `python -X utf8 -m pytest scripts/tests/test_release_input_preparation.py -q`
  - Environment: `INTRUOYI_TEST_APP_BACKEND=D:/IntRuoyiWorktree/two-button-release-delivery-app/IntRuoyiBackend`
  - Result: `3 passed in 6.98s`
- GREEN: maintenance-preflight-tests -> PASS
  - Command: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py -q`
  - Environment: `INTRUOYI_TEST_APP_BACKEND=D:/IntRuoyiWorktree/two-button-release-delivery-app/IntRuoyiBackend`
  - Result: `14 passed in 0.72s`
- GREEN: backend-targeted-tests -> PASS
  - Command: `mvn.cmd -pl yudao-module-infra -am '-Dtest=ReleaseWorkflowOrchestratorTest,ReleaseWorkflowSourceBindingTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowStoreTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowRecoverySchedulerTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowTestEvidenceStoreTest,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test`
  - Result: reactor `BUILD SUCCESS`; Surefire `Tests run: 142, Failures: 0, Errors: 0, Skipped: 0`.
- GREEN: frontend-static-contracts -> PASS
  - Commands: `node src\\views\\infra\\runtime-control\\twoEntryRelease.static.spec.cjs`; `node src\\views\\infra\\runtime-control\\productionPromotionButton.static.spec.cjs`.
  - Result: both contracts printed `PASS`; the page exposes the two top-level entries and the promotion contract rejects client-owned target fields.
- GREEN: frontend-typecheck -> PASS
  - Command: `pnpm.cmd ts:check`
  - Result: exit code `0`.

## P4 acceptance result

- **P4-AC1: BLOCKER.** Static/backend gates passed, but the required real-browser entry `tests/e2e/runtime-control-two-entry-release.e2e.cjs` is absent from the app worktree. The task requires a blind-first real-browser pass; no substitute or mock was used.
- **P4-AC2: BLOCKER / unverified.** No authenticated independent runtime was available for injecting the required fault matrix. The backend targeted tests cover only part of the matrix and cannot substitute for independent runtime verification.
- **P4-AC3: BLOCKER / unverified.** No browser case ran, so there are no screenshot/trace/HAR artifacts.
- **P4-AC4: PASS for reporting discipline; overall P4 remains BLOCKED.** This report records the missing entry/runtime as a blocker and does not claim P4 completion.

## Untested / required follow-up

- Add or restore the approved Playwright real-user case at `IntRuoyiFronted/tests/e2e/runtime-control-two-entry-release.e2e.cjs` in the implementation worktree, without adding product controls solely for testing.
- Start the independent app worktree runtime with its registered ports and valid test-tenant login prerequisites; verify authenticated route, tenant and permissions before fault cases.
- Re-run the fault matrix: double click, concurrent推进者, close/refresh, restart, dispatch boundary, lease loss, migration failure, digest drift, evidence expiry, authorization expiry.
- Save redacted screenshots/traces/HAR and rerun this report; do not mark P4 complete from static or API-only results.
