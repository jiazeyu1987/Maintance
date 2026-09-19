# 20260713 前置经验问题修复验证报告

## Status

completed

## Fixed Items

- PF-AUDIT-001: Replaced stale migration policy gate `--json` recommendations with the current `--output` contract and added an explicit `--help` check before running frozen-worktree scripts.
- PF-AUDIT-002: Added an executable precedence rule: PowerShell / Windows shell tasks may run one readonly UTF-8 bootstrap before task doc creation, then must immediately create/update task docs and extract gates.
- PF-AUDIT-003: Added the missing `Evidence` field to the primary test-release preflight summary.
- PF-AUDIT-004: Replaced fragile or drifted experience-index anchors with file + heading-title routes; remaining anchors were checked.
- PF-AUDIT-005: Clarified that full three-environment release wording applies only when that scope is authorized; test-only release remains bounded by `docs/test-release-preflight.md`.
- PF-AUDIT-006: Removed a stray quote and normalized `build-release` formatting.

## Verification

- `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --help` showed supported parameters include `--output` and do not include `--json`.
- `rg` confirmed the only remaining `--json` occurrence in the target release preflight docs is the warning that historical `--json` must not be used directly.
- Anchor verification for `docs/experience-index.md`: `anchor_refs=29`, `missing=0`, `broken=0`.
- Bootstrap exception route check found the new `task-doc-first` exception in maintenance and main project rule entries.
- `git diff --check` passed for maintenance and main project modified files; Git only emitted line-ending warnings.
- UTF-8/control scan passed: all touched files decoded as UTF-8, `NUL=0`, invalid control characters=0.
- Secret scan found only redacted/placeheld examples such as `<redacted>` and `<secret>`; no new raw credentials were found.

## Remaining Notes

- Main project `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md` already had unrelated uncommitted changes before this fix; this task only added the PowerShell bootstrap precedence line there and did not revert or stage unrelated edits.
- This was a documentation/rule fix only; no build, release, server operation, or production code change was executed.
