# 20260719 project experience consolidation r260719k

## Task Goal

Consolidate reusable lessons from the completed IntRuoyi code-only three-environment release `release-20260719-intmain-codeonly-three-env-r260719k-r1` into existing long-term project experience documents.

## Scope

- Source task: `doc/tasks/20260719-current-head-codeonly-three-env`.
- Prefer existing experience documents; do not create a new long-term document without explicit user approval.
- Keep task-specific release status and one-off evidence in task records only.
- Do not execute build, publish, backup, restore, rollback, or server write actions.

## Milestones

- [x] Create task records before changing long-term documents.
- [x] Read experience index and matching long-term experience destinations.
- [x] Identify reusable lessons and decide existing destinations.
- [x] Update only suitable existing experience documents.
- [x] Update request command log and execution evidence.
- [x] Run UTF-8, diff, keyword, and secret-scan verification.
- [x] Mark ready_for_closeout, run task-closeout preview/apply, then mark completed.
- [x] Commit only this task's records and experience updates.

## Expected Verification

- `docs/experience-index.md` routes every new or refreshed gate.
- Updated experience entries use the required summary fields: Trigger, Preflight check, Blocker, Verification, Forbidden action, Evidence.
- `rg` can locate new keywords from the index.
- `git diff --check` passes for task-owned staged files.
- UTF-8 readback succeeds and no mojibake or replacement-character text is introduced in this task's files.
- Secret scan finds no raw password, token, private key, connection secret, or secret-bearing command output in this task's staged changes.

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；只把可复用前置门禁归入既有长期经验，不写一次性流水。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed - Reusable r260719k release lessons were matched to existing release/build/worktree/PowerShell destinations. `docs/release-agent-checklist.md` now contains an execution-facing r260719k failure-prevention checklist, and `docs/experience-index.md` routes matching keywords to it. Keyword lookup, task-closeout preview/apply, diff check, staged UTF-8 scan, and staged secret scan passed. Final commit is isolated to this task's records, request log entries, and necessary experience gate updates.
