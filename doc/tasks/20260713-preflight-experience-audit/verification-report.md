# 20260713 前置经验一致性审查报告

## Status

completed

## Reviewed Scope

- Maintenance experience index: `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- Maintenance release/test preflight docs: `docs\test-release-preflight.md`, `docs\release-build-preflight-lessons.md`, `docs\release-agent-checklist.md`
- Maintenance PowerShell preflight docs: `docs\powershell-preflight-lessons.md`
- Main project shared rules: `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md`, `docs\experience-index.md`, `docs\worktree-memory.md`, `docs\powershell-memory.md`, `docs\release-backup-restore.md`
- Verified script contract: `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --help`

## Summary

- Found 2 actionable conflicts that can affect execution order or command correctness.
- Found 2 documentation quality issues that affect discovery/format consistency.
- Did not find a rule that would permit fallback, mock success, dirty-worktree release input, skipping real runtime validation, or publishing prod/backup during a test-only task.
- The test-only vs full-release boundary is mostly safe because `release-agent-checklist.md` explicitly says test-only stops after test runtime validation; however, older full-chain wording in `release-build-preflight-lessons.md` can still confuse readers if opened out of order.

## Findings

### PF-AUDIT-001 - migration policy gate command conflicts with frozen script contract

- Severity: High.
- Evidence:
  - `docs\test-release-preflight.md:101` recommends `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --json`.
  - `docs\release-build-preflight-lessons.md:335` also requires `--json` and complete JSON evidence.
  - `docs\release-build-preflight-lessons.md:528-534` later says frozen worktree scripts must be checked by `--help`, and specifically forbids relying on historical `--json`.
  - Actual script help only supports `--output`, not `--json`.
- Impact: An agent following the current primary test-release preflight command will fail the gate with an argument error before build, or misclassify a parameter-contract failure as migration-content failure.
- Recommendation: Replace primary examples with `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --output <task-dir>\migration-policy-gate.json`, and keep the "read --help from frozen worktree first" gate as the controlling rule.

### PF-AUDIT-002 - task-doc-first conflicts with PowerShell readonly bootstrap

- Severity: High.
- Evidence:
  - `AGENTS.md:41` and `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md:41` require creating/writing the task document before starting any task.
  - `docs\experience-index.md:3` and `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md:3` repeat that the task doc is written before reading the index.
  - `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md:45`, `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md:40`, `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md:13`, and `docs\powershell-preflight-lessons.md:18` say PowerShell tasks may only run a readonly bootstrap first and must not write files before reading PowerShell memory.
- Impact: Any Windows task that needs PowerShell cannot satisfy both orders literally: writing the task doc first violates the readonly bootstrap, while doing the bootstrap first violates task-doc-first.
- Recommendation: Add an explicit precedence rule, e.g. "For PowerShell/Windows-shell tasks, one readonly UTF-8 bootstrap may run before task document creation; immediately after bootstrap, create/update the task doc and extract experience gates." This removes the impossible ordering without weakening the encoding gate.

### PF-AUDIT-003 - primary test-release summary misses required Evidence field

- Severity: Medium.
- Evidence:
  - Maintenance index requires every executable lesson to include `Trigger`, `Preflight check`, `Blocker`, `Verification`, `Forbidden action`, and `Evidence`.
  - `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md:7-16` mirrors the six-field standard.
  - `docs\test-release-preflight.md:23-30` has Trigger through Forbidden action, but no Evidence line in the primary "可索引门禁摘要".
- Impact: The most important test-only release entry is slightly less machine-extractable and less consistent with the current standard.
- Recommendation: Add `Evidence: execution-log.md, verification-report.md, releaseTag, build/publish operation, manifest path, remote runtime evidence, Playwright page evidence, worktree cleanup evidence`.

### PF-AUDIT-004 - several experience-index anchors are stale or fragile

- Severity: Medium.
- Evidence:
  - `docs\experience-index.md:55` points to `#2026-07-11-powershellsshplaywright-发布验收门禁`, while the target heading is `## 2026-07-11 PowerShell/SSH/Playwright 发布验收门禁`.
  - `docs\experience-index.md:94` includes a plain-text anchor ending with `mysql-1137。`; the target heading omits the punctuation.
  - `docs\experience-index.md:124` points to `#2026-07-13-powershell-发布脚本承载参数解析与证据脱敏门禁`, while the target heading includes punctuation between 承载 and 参数.
  - `docs\experience-index.md:126` points to `#2026-07-12-publish-test-preview-目标字段门禁`, while the target heading is `## 2026-07-12 publish-test 目标字段与版本说明验收门禁`.
- Impact: Keyword search still works, but clickable or copyable section routes can land at the wrong place or fail to jump.
- Recommendation: Normalize referenced anchors to exact generated heading slugs, or remove fragile fragments and route to the file plus a nearby unique keyword.

### PF-AUDIT-005 - full-release wording can still confuse test-only tasks if read out of order

- Severity: Low.
- Evidence:
  - `docs\release-build-preflight-lessons.md:126` says real release must run the full chain `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`.
  - `docs\release-build-preflight-lessons.md:267` says some code-only releases must still run `mark-release-tested` and `promote-prod`.
  - `docs\release-agent-checklist.md:34` correctly constrains test-only tasks to `docs\test-release-preflight.md` and forbids `mark-tested`, `promote-prod`, and `promote-backup`.
- Impact: Not a direct conflict when the index is followed, but the older full-release paragraphs can mislead if someone opens `release-build-preflight-lessons.md` directly.
- Recommendation: Add "完整三环境发布适用；仅测试服发布以 `docs/test-release-preflight.md` 为范围权威" near the full-chain paragraphs.

### PF-AUDIT-006 - minor formatting/typo artifacts in release-build lessons

- Severity: Low.
- Evidence:
  - `docs\release-build-preflight-lessons.md:324` contains a standalone `'`.
  - `docs\release-build-preflight-lessons.md:327` uses `\build-release`.
- Impact: Low execution risk, but these artifacts make the document look corrupted and can reduce confidence during emergency release work.
- Recommendation: Remove the stray quote and normalize `\build-release` to `build-release`.

## Verified Non-Issues

- Test-only scope is protected by `docs\test-release-preflight.md` and `docs\release-agent-checklist.md:34`; I did not find a rule that requires prod/backup promotion for a user-authorized test-only release when the index is followed.
- The no-fallback posture is consistent across the checked docs: release, worktree, PowerShell, and runtime validation all forbid mock success, silent downgrade, dirty-worktree build input, or HTTP-only completion.

## Recommended Fix Order

1. Fix PF-AUDIT-001 before the next release: stale `--json` commands can break the preflight immediately.
2. Resolve PF-AUDIT-002 in AGENTS/index/powershell docs: it is a rule-order conflict every Windows task will hit.
3. Patch PF-AUDIT-003 and PF-AUDIT-004 for discoverability.
4. Clean PF-AUDIT-005 and PF-AUDIT-006 as low-risk documentation polish.
