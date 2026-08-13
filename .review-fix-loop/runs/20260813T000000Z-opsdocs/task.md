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

## Current Package Rule

- Review the current files on disk, including the worker edits. Do not rely on the original round-one line numbers or scope.
- The selected node is allowed to plan new tests that will be created during strict TDD; planned files must be named and commands must be exact.
- `ready-for-implementation` means local/test RED work may start. It does not authorize production rollout, server access, or backup execution.
