# 20260715 project experience consolidation r260715w

## Task Goal

Consolidate reusable lessons from the `r260715w` code-only three-environment release into existing long-term project experience documents, without creating new memory files unless explicitly authorized.

## Milestones

- [x] Create task records and identify source release evidence.
- [x] Search existing experience/memory documents and choose existing destinations.
- [x] Merge only durable, reusable preflight lessons; avoid one-time release status.
- [x] Update request/command log with intent and verification.
- [x] Verify keyword discoverability, diff scope, closeout cleanup, and secret safety.
- [x] Mark completed and commit only task-owned records plus necessary experience updates.

## Expected Verification

- Existing long-term experience documents are updated only where the new lesson fits their purpose.
- No new experience document is created.
- `docs/experience-index.md` routes future tasks to the new/updated gate.
- `docs/request-command-log.md` records the user request, command intent, and result.
- `git diff --check`, strict secret scan, and task-closeout preview/apply pass.
- Commit includes only this task's task records, request log, and necessary experience updates.

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；只沉淀可复用前置门禁，不记录一次性状态。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed - source release evidence and existing experience destinations have been checked. The reusable r260715w lesson is already consolidated into existing maintenance release preflight docs and routed by `docs/experience-index.md`; the main project `docs/release-backup-restore.md` already contains the same durable migration metadata gate. No new experience document is needed. Task-closeout preview/apply passed with no delete, blocked, or warning items.

## Experience Consolidation Result

- Lesson type: release/build preflight, specifically SQL `release-migration` metadata missing during `build-release`.
- Existing destination: `docs/release-build-preflight-lessons.md`, section `2026-07-09 build-release 迁移元数据必须先过全量策略门禁`.
- Existing route: `docs/experience-index.md` routes `20260714_dcc_personal_file_decommission.sql` / `Release migration metadata missing` to the migration policy gate.
- Cross-project baseline: `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` already records the general migration metadata gate and `SkipDatabaseSync` boundary.
- New document decision: no new experience document created because existing release/build documents are the correct conceptual fit.
- Closeout: `task-closeout-cleanup` preview/apply kept the three core task records; delete=`<none>`, blocked=`<none>`, warnings=`<none>`.
