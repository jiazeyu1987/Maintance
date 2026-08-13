# Release Review Report

## Task Summary

The current package is substantially narrowed to one roadmap node, OPS-NODE-001, covering scheduled-backup registration, protected production authorization, explicit repository selection, scheduler health, and the existing backup-plan page. The successor initiatives are now explicitly out of scope. The node is not yet releasable because its executable paths do not consistently target the code that the backend and deployment chain actually own, and the status and E2E contracts still contain release-gating inconsistencies.

## Logic Review

- Status: fail
- logic_status: fail
- Blocking Issues:
  1. **The script implementation and test plan target a non-owning copy instead of the backend/deployment source.** The planning package repeatedly names `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops` and runs Pester there (`prd.md:15-17`, `development-plan.md:13-15,68,76-83,96-107`, `test-plan.md:15-17,36-38,91-105`). Current product code resolves the scheduler scripts from the backend repository at `repoRoot/script/backup-ops`, and the deployment script also packages `IntRuoyiBackend/script/backup-ops`. The backend copy has already diverged from the maintenance copy, including a cleartext production-confirmation argument and no explicit `RepositoryEnvironment`. Implementing and passing the documented commands against the maintenance copy would not fix or verify the scripts invoked by `/system/backup-plan` or shipped by the release chain.
  2. **The protected authorization design does not define the scheduled-task identity required for its own ACL contract.** The package freezes `auth.productionBackupConfirmText` and requires “the scheduled-task account” to read it while ordinary users cannot write it, but the current registrar calls `Register-ScheduledTask` without a principal/account. The plan neither chooses a task identity nor includes principal creation/update, logon mode, credential handling, or principal verification in the candidate files, BDD, acceptance criteria, and exact commands. Consequently ACL validity cannot be determined, `Register-ScheduledTask` may run under a different identity than the one tested, and AC-002/AC-003 cannot be proven.
  3. **Status-health requirements are incomplete relative to the existing failure paths.** AC-004 and the health states require every critical omission to avoid “正常”, including missing `NextRunTime`, missing recent backup point, invalid task/config/script paths, and query failure. However BDD-003 and the backend RED/GREEN description do not consistently include missing config/secrets files or a missing latest backup point, and no staleness/newness rule is specified for the “recent” point. Without a defined threshold/reference and full scenario matrix, a task can still be marked normal using old or incomplete evidence.
  4. **Cross-document machine status remains inconsistent.** `task-state.json` says `currentPhase=ready-for-implementation` and `currentMilestone=M1`, while `task.md` says the planning task is `in_progress` at its M4 review milestone. These use overlapping milestone identifiers for different lifecycles and contradict the stated verification requirement that selected node, phase, milestone, and status agree across artifacts. A machine consumer cannot distinguish planning M4 from implementation M1.
- Notes:
  - The original program-sized scope and notification-state issue are correctly removed from this node.
  - The package now uses named planned tests and exact command strings, which is an improvement, but exact commands against the wrong owning source are not valid release evidence.

## Usability Review

- Status: fail
- usability_status: fail
- Blocking Issues:
  1. **The implementer cannot safely choose the repository to modify or commit.** Candidate files span the maintenance repository, backend repository, and frontend repository, but the package does not state the authoritative script source, whether the maintenance copy is generated or mirrored, how duplicate copies must be synchronized, or which owning repositories receive implementation commits. Following the plan literally can produce a green local contract while leaving the shipped product broken.
  2. **The operator cannot configure the required repository selection through the existing workflow.** The plan says the operator must explicitly supply `test` or `backup` for every registration/plan-only run, but the current backend `saveSchedule/enable` path invokes the registrar with only `-ConfigPath`, and the existing page/API schedule contract has no repository field. The package does not decide whether repository selection is an approved protected configuration value, a backend property, or a UI control, nor specify how it reaches `Register-BackupOpsScheduledTasks.ps1`. This leaves the central AC-001/AC-002 path unusable through the retained product entry.
- Notes:
  - The blocker-clearance tables and successor backlog make the revised package easier to navigate.

## UI Review

- Status: fail
- ui_status: fail
- Blocking Issues:
  1. **The E2E entry contract is internally inconsistent with the project frontend baseline and does not cover the promised states.** The existing E2E script defaults to `http://127.0.0.1:8083`, while project policy and the planning context use `http://localhost:8081`; the plan does not require overriding the base URL or fail fast on the mismatch. More importantly, the single read-only E2E only accepts whatever state happens to exist and asserts general headings. It cannot deterministically exercise disabled, last-failed, configuration-abnormal, API-error, permission-denied, or empty-history states listed in `test-plan.md:181` without approved real frontend setup paths. Static source matching is not behavioral proof for those states.
  2. **The documented page contract omits an existing command and misstates permission behavior.** The page exposes “立即备份一次” and the API includes `POST /infra/backup-plan/backup-now`, but `development-plan.md:116-125` omits that endpoint while still listing its execute permission. The node calls the page path read-only yet retains write controls and write permissions without explicitly limiting E2E to query-only behavior or asserting that unauthorized users cannot see/activate those controls. This creates ambiguity about what UI behavior is actually in scope and what Playwright may safely operate.
- Notes:
  - UI runtime rendering is not required for this documentation review. The decision is based only on route, contract, permission, and testability evidence.

## Non-Blocking Suggestions

- Use distinct identifiers such as `PLAN-M1` and `IMPL-M1` if both planning and implementation milestones must coexist in the same task directory.
- Record the exact source-of-truth and mirror/generated-copy policy in the successor documentation as well, because backup scripts currently exist in more than one repository location.
- Keep the page's operator-facing `blockedReason` concise and expose detailed technical evidence only through secured logs/status fields.

## Required Changes

1. Rebase all script candidate files, planned tests, Pester/parser commands, and RED/GREEN expectations onto the actual owning source used by `BackupPlanServiceImpl` and the release packager: `E:\IntRuoyi\IntRuoyiBackend\script\backup-ops`, or explicitly define and test a deterministic synchronization mechanism if the maintenance copy is intentionally authoritative. State the owning repositories and required task-scoped commits. Add a regression that proves the backend runtime/deployment input contains the corrected contract and no divergent cleartext path remains.
2. Define the Windows scheduled-task principal contract end to end: selected account/principal source, logon mode, least-privilege requirements, secret-file ACL ownership/read/write rules, registration arguments, verification command/output, and fail-fast behavior. Add named Pester scenarios and acceptance coverage proving the registered task principal is the same identity whose read/write access is validated. Do not place credentials or confirmation text on the command line.
3. Define how `RepositoryEnvironment` is selected and propagated through the retained `/system/backup-plan` save/enable workflow. Choose one formal source, update the backend/UI/config contracts and permissions accordingly, and add BDD/TDD/E2E coverage for explicit `test`/`backup`, missing, and invalid selections. Do not leave the operator instruction disconnected from the product entry.
4. Complete the scheduler-health contract with exact rules and tests for query exit code, enabled state, `NextRunTime`, last result, task command/script path, config path, secrets/protected-input validation, latest backup point presence, and the definition of “recent”/fresh enough. Every missing/invalid field must have a deterministic health status and blocked reason and must not result in “正常”.
5. Separate planning-task progress from implementation-node readiness in the machine state, using unambiguous phase/milestone fields or distinct IDs, and make `task-state.json`, `task.md`, and `execution-log.md` agree after review.
6. Make the UI/E2E plan executable: pin the documented frontend entry to `http://localhost:8081` or require an explicit verified override; identify real approved frontend setup paths for every required state or reduce the acceptance claim to states that can be reached without API/SQL/stub setup; add Playwright assertions for blocked reason, empty/error feedback, permission behavior, and absence of secrets. Missing setup paths must be recorded as blockers rather than treated as covered by static source tests.
7. Correct the UI contract to include the existing `POST /admin-api/infra/backup-plan/backup-now` endpoint and explicitly state that OPS-NODE-001 E2E is query-only: it must not operate save/enable/disable/backup-now controls. Specify expected visibility/disabled behavior for accounts with query permission but without update/execute permissions.

## Final Decision

- final_decision: fail

The revised package is now one roadmap node, but logic, usability, and UI/testability still contain release-blocking gaps. Most critically, its script tests target a different copy from the backend and deployment source, so the documented GREEN path would not prove the shipped system is fixed.
