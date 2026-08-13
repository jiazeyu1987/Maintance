# Worker Task

- Run ID: 20260813T000000Z-opsdocs
- Round: 1
- Workspace: D:/ProjectPackage/Int/IntRuoyiMaintance
- Goal: 复核正式服运维规划包的范围、依赖、验收、测试和跨文档一致性，修订后形成可执行且可验证的单节点计划

## Instructions

- 只根据 reviewer 给出的 required changes 修复阻塞问题。
- 可以顺手处理明显相关的非阻塞问题，但不要偏航重构。
- 修改完成后，将结果写入 `D:/ProjectPackage/Int/IntRuoyiMaintance/.review-fix-loop/runs/20260813T000000Z-opsdocs/worker/result-round-1.md`。
- 结果必须包含：修改摘要、已验证项、未解决项、剩余风险。

## Task

# Task

- Goal: 复核正式服运维规划包的范围、依赖、验收、测试和跨文档一致性，修订后形成可执行且可验证的单节点计划
- Workspace: D:/ProjectPackage/Int/IntRuoyiMaintance
- Max Rounds: 4
- Requires UI Runtime: no
- Reviewer must judge only from logic, usability, and UI.
- Worker must only implement required changes from reviewer output.

## Review Scope

- `doc/tasks/20260813-production-operations-hardening-plan/prd.md`
- `doc/tasks/20260813-production-operations-hardening-plan/development-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/test-plan.md`
- `doc/tasks/20260813-production-operations-hardening-plan/task-state.json`
- `doc/tasks/20260813-production-operations-hardening-plan/task.md`
- `doc/tasks/20260813-production-operations-hardening-plan/execution-log.md`

## Evidence Sources

- `doc/tasks/20260813-production-operations-review/verification-report.md`
- `E:/IntRuoyi/docs/release-backup-restore.md`
- Current maintenance repository scripts, tests, configuration, and runtime-control source referenced by the planning package.

## Review Constraints

- Judge whether this is exactly one executable roadmap node rather than a bundle of unrelated initiatives.
- Verify requirement, acceptance, milestone, BDD/TDD, blocker, and machine-state consistency.
- Treat missing business decisions, unavailable dependencies, placeholder commands, secret exposure, unauthorized production actions, mocks, fallback, and silent downgrade as release-gating concerns.
- This is a documentation-only review; UI runtime review is not required. Review UI-related plans only for testability and consistency with current product entry points.


## Reviewer Report

# Release Review Report

## Task Summary

The reviewed package is intended to be an executable, verifiable single roadmap node for production-operations hardening. It currently defines ten requirements and seven implementation milestones spanning scheduled backups, external notification, backup UI, external monitoring, incident workflow, observability, image governance, PITR, analytics governance, and monthly reporting. Several required product and environment decisions remain unresolved.

## Logic Review

- Status: fail
- logic_status: fail
- Blocking Issues:
  1. **The package is not one executable roadmap node.** `prd.md:7` places ten materially distinct initiatives in one delivery scope, and `development-plan.md:26-46` divides them into seven milestones with separate repositories, deployment targets, decision owners, and verification modes. This is a multi-phase program, not a bounded node that one implementation task can take through RED, GREEN, regression, integration, and acceptance. The package therefore cannot satisfy its stated release-gating goal.
  2. **The declared current node is not executable because its P0 prerequisite is unresolved.** `task-state.json:4-6` declares `planned`, `ready-for-implementation`, and current milestone `M1`, while M1 combines the scheduled-task contract fix with an external notification adapter. The notification channel and credentials are explicitly unresolved in `prd.md:57`, `prd.md:280`, `development-plan.md:63`, and `task-state.json:80-82`. The no-fallback policy prevents choosing an adapter or inventing credentials, so M1 cannot currently reach its own outcome or acceptance gate.
  3. **Machine state does not represent the documented blockers.** Only M6 is marked `blocked` in `task-state.json:65-69`; M1 is `planned` despite B-001, M3 is `planned` despite B-003, and M7 is `planned` despite B-004. `currentPhase` still says `ready-for-implementation`. Downstream M2 also depends on OPS-REQ-002, and OPS-REQ-010 depends on blocked analytics/monitoring work, but those dependency effects are not reflected. A supervisor could start an impossible milestone or report readiness incorrectly.
  4. **The alert state model is internally invalid.** `prd.md:227-233` models `NOTIFICATION_FAILED` as a state reachable from `Any`, although notification delivery is a secondary outcome that can occur while an alert remains OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, or CLOSED. This makes the alert lifecycle lossy and conflicts with the requirement to retain alert handling while recording a secondary alert and retry status.
  5. **The test plan contains placeholder rather than executable commands.** Examples include `targeted backend/JUnit or Pester backup candidate tests`, `same target tests`, `external monitor config/unit tests`, `backend target JUnit`, `config contract tests`, `Pester MySQL PITR config tests`, `metrics catalog validation tests`, and `monthly report generation tests` (`test-plan.md:144-270`). These cannot produce reproducible RED/GREEN evidence and violate the packet's explicit release concern for placeholder commands.
- Notes:
  - The scheduled-task defect is correctly grounded in current source: the registrar currently omits `TargetEnvironment`, `RepositoryEnvironment`, and `ProductionBackupConfirmText`, while `backup-ops.ps1` requires explicit production confirmation and repository selection.
  - The package correctly forbids production writes, mock success, silent downgrade, and unapproved defaults, but those safeguards do not make the current combined node executable.

## Usability Review

- Status: fail
- usability_status: fail
- Blocking Issues:
  1. **An implementer cannot determine a bounded starting and stopping point.** `development-plan.md:48-53` says to execute M1 through M7 in sequence, while the task state selects M1 and the task goal describes the whole program. There is no single-node scope freeze, excluded follow-on backlog, named owning repository set, or completion rule that distinguishes completion of the selected node from completion of the overall program.
  2. **Required decisions lack an acquisition gate.** The package lists missing notification channel, deployment location, RTO/RPO/SLO, owners, and analytics source, but does not name a decision owner, required decision artifact, due/entry condition, or exact state transition that makes an affected milestone ready. Implementers can see that work is blocked but cannot operationally clear the blocker.
  3. **Several acceptance gates are qualitative and cannot be executed as written.** Phrases such as “页面/接口验证,” “配置/发布预检测试,” “看板导入/配置检查,” and “真实页面或真实命令证据” do not identify the command, environment, fixture acquisition, expected output, or evidence path. This prevents repeatable handoff and independent verification.
- Notes:
  - The requirement IDs and high-level traceability are helpful, but traceability alone does not make the plan runnable.

## UI Review

- Status: fail
- ui_status: fail
- Blocking Issues:
  1. **The planned UI paths are not tied to deliverable entry-point contracts.** E2E-001 through E2E-005 assume scheduled-task status, recoverability, imported external alerts, and data-quality views, but the development plan does not identify the exact existing route/component to extend, API contract, permission, dynamic-menu record, target-tenant role binding, loading/error/empty states, or whether a new page is in scope. Current source confirms a runtime-control page and related APIs exist, but not every assumed view/control. The planned paths therefore cannot be accepted through the required real user route without scope ambiguity.
  2. **The E2E data/setup plan conflicts with real-path test policy.** `test-plan.md:320-323` permits locally constructed repository samples, a local stub endpoint, and a read-only snapshot, while the E2E paths do not specify how Playwright creates or selects traceable test-tenant data through the frontend. `E2E-004` also says to point the probe at an invalid health URL without identifying an authorized UI entry or cleanup path. These are not executable real-user-path E2E prerequisites and could cause a tester either to bypass the frontend or silently substitute mock/stub evidence.
- Notes:
  - Runtime rendering is not required for this documentation review. The failure is based on testability and consistency with the existing runtime-control entry point, not visual styling.

## Non-Blocking Suggestions

- Add a compact requirement-to-milestone-to-BDD-to-command-to-evidence matrix after the package is reduced to one node.
- Normalize state names and casing (`BLOCKED`, `PRODUCT_BLOCKED`, `blocked`, `ready`) through a documented enum so machine and human artifacts use the same vocabulary.
- Separate evidence paths for local contract tests, test-tenant UI tests, authorized remote read-only checks, and later production rollout.

## Required Changes

1. Replace this program-sized package with exactly one independently deliverable roadmap node. A valid first node may be the scheduled-task registration contract fix alone; move notification, backup UI, monitoring, observability, image governance, PITR, analytics, and monthly reporting into explicitly out-of-scope successor nodes with dependency references. If external notification remains in the selected node, obtain and record the channel decision and test credentials before marking it ready.
2. Make `task-state.json`, `task.md`, `development-plan.md`, and `execution-log.md` agree on the selected node, current phase, milestone status, blockers, and completion meaning. Any milestone with a missing mandatory decision/dependency must be `blocked`, and the overall phase must not be `ready-for-implementation` unless the selected node has no unresolved entry blocker.
3. Define blocker-clearance contracts for every dependency retained in scope: decision owner, required input/artifact, validation method, state transition, and evidence location. Do not select defaults for notification, deployment, RTO/RPO/SLO, image versions, or analytics sources.
4. Correct the alert model by keeping alert lifecycle state separate from notification delivery attempts/status, secondary-alert linkage, and retry history. Add BDD and tests for notification failure without losing the primary alert's workflow state.
5. Replace every placeholder RED/GREEN/regression entry with an exact command runnable from an identified repository/worktree, an existing or explicitly planned test file/class, required environment/data prerequisites, expected failure reason, expected pass condition, and evidence output path.
6. For every UI behavior retained in the selected node, specify the existing or new route/component, backend endpoint contract, permission and dynamic-menu binding, test-tenant access prerequisite, loading/empty/error/success states, and the Playwright-only user steps. Remove stub/sample shortcuts from E2E; use traceable test-tenant data created or selected through an approved real frontend path, and specify cleanup. If no frontend entry exists and adding it is outside the selected node, mark that E2E blocked rather than using API, script, filesystem, or stub setup as a substitute.
7. Re-run cross-document validation only after the reduced node has a complete requirement-to-acceptance-to-BDD-to-exact-command chain and machine state accurately reports all remaining blockers.

## Final Decision

- final_decision: fail

The planning result is not releasable as a single executable roadmap node. Logic, usability, and UI/testability each contain blocking issues.
