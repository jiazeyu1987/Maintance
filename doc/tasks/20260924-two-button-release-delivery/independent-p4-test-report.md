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
- RED: required-playwright-entry -> FAIL, the named P4 script is absent from the implementation history/worktree; no replacement was accepted because T5 requires the approved two-entry real-user path.

## Follow-up evidence review (2026-09-25)

- GREEN: admin-override-browser-evidence-review -> PASS with scope limitation
  - Reviewed implementation commit `d353b633f1ea9dfbd149333e0c61f82d3f86e237` and the later local admin-override artifacts under `IntRuoyiFronted/tests/e2e/output/runtime-control-two-entry-release/admin-override/`.
  - `node --check tests/e2e/runtime-control-two-entry-release.e2e.cjs` passed.
  - The real Playwright evidence contains screenshots for the two-entry page, intent creation, refresh, cancellation, and no-candidate promotion blocking; the report records frontend/backend HTTP 200, zero page errors, and zero request failures.
  - The HAR shows one `POST /release-workflows` with `reason`, `sourceSelectionId`, and `idempotencyKey`, one cancel POST, refresh GETs, and no legacy `/actions` or browser-driven `/publish-test` POST.
  - The user explicitly authorized this local isolated admin identity override; this is valid evidence of the local UI contract only.
- BLOCKER: tenant-boundary-evidence -> the actual HAR login is tenant `芋道源码` / user `admin`, while the required test tenant `测试租户` / `aoteman` was unavailable. The admin override is explicitly authorized for local verification, but it does not prove the required test-tenant write boundary.
- BLOCKER: trace-secret-leak -> the admin-override Playwright trace contains the configured admin password literal in `trace.trace` and one trace resource JSON. The HAR is redacted, but the trace cannot be accepted as clean evidence until regenerated without credential capture or removed from the evidence set.
- BLOCKER: fault-matrix-coverage -> the executed script covers login, two buttons, one publish-intent POST, refresh, cancel, and no-candidate promotion blocking. It does not provide executed evidence for double-click, concurrent推进者, close/refresh continuation after an in-flight operation, restart recovery, dispatch-boundary interruption, lease loss, migration failure, digest drift, evidence expiry, or authorization expiry. The script contains branches for some guards, but the recorded run did not exercise them.

## Final P4 acceptance review

- **P4-AC1: PASS with qualification.** A real Playwright path and required entry now exist and were exercised in the isolated local runtime; the admin identity was used only under the user's explicit authorization. This does not satisfy the normal test-tenant identity requirement.
- **P4-AC2: BLOCKER.** The required independent fault matrix is not fully executed or evidenced.
- **P4-AC3: BLOCKER.** Browser artifacts exist, but the trace contains a credential and the run used `芋道源码/admin` instead of `测试租户/aoteman`; the safety and tenant-boundary requirements are therefore not proven.
- **P4-AC4: PASS for honest independent reporting only.** The missing matrix, tenant mismatch, and trace leak are explicitly recorded as blockers; no mock, API-only substitute, remote publish, or production action was used. Overall P4 remains **BLOCKED**.

## Initial P4 acceptance result (before `d353b633f`)

- **P4-AC1: BLOCKER.** Static/backend gates passed, but the required real-browser entry `tests/e2e/runtime-control-two-entry-release.e2e.cjs` is absent from the app worktree. The task requires a blind-first real-browser pass; no substitute or mock was used.
- **P4-AC2: BLOCKER / unverified.** No authenticated independent runtime was available for injecting the required fault matrix. The backend targeted tests cover only part of the matrix and cannot substitute for independent runtime verification.
- **P4-AC3: BLOCKER / unverified.** No browser case ran, so there are no screenshot/trace/HAR artifacts.
- **P4-AC4: PASS for reporting discipline; overall P4 remains BLOCKED.** This report records the missing entry/runtime as a blocker and does not claim P4 completion.

## Untested / required follow-up

- Add or restore the approved Playwright real-user case at `IntRuoyiFronted/tests/e2e/runtime-control-two-entry-release.e2e.cjs` in the implementation worktree, without adding product controls solely for testing.
- Start the independent app worktree runtime with its registered ports and valid test-tenant login prerequisites; verify authenticated route, tenant and permissions before fault cases.
- Re-run the fault matrix: double click, concurrent推进者, close/refresh, restart, dispatch boundary, lease loss, migration failure, digest drift, evidence expiry, authorization expiry.
- Save redacted screenshots/traces/HAR and rerun this report; do not mark P4 complete from static or API-only results.
