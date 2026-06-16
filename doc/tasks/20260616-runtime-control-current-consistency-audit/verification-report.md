# Verification Report

## Objective

验证当前独立维护应用运行控制台与原 IntRuoyi 运行控制台逻辑是否一致，并记录剩余差异。

## Status

CORE PASS / OVERALL PARTIAL.

当前独立应用的“核心运行控制台动作契约”已与原版对齐；如果把原版的告警、事故、巡检、责任人、远端根盘、完整前端治理界面也纳入一致性范围，则当前仍是部分一致。

## Compared Sources

- Current standalone: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Original backend: `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra`
- Original frontend: `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src\views\infra\runtime-control`
- Original scripts: `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script`

## Requirement Matrix

| Area | Result | Evidence |
| --- | --- | --- |
| HTTP path surface | PASS | Normalized controller paths match exactly: 33 standalone paths vs 33 original paths; no missing or extra HTTP paths. |
| Login / role / menu security | INTENTIONAL DIFFERENCE | Original controller uses `@PreAuthorize` and `getLoginUserId`; standalone removes Spring Security and uses configured local operator, matching independent-local-app requirement. |
| Core action enum | PASS | Action names and labels match for build, publish-test, apply-test-db-sql, mark-tested, promote-prod, promote-backup, backup, rollback, rehearsal, restore. Standalone script roots are changed from `script/...` to `ops/...` by design. |
| Action request validation | PASS | Target environment, publish scope, include flags, releaseTag, sqlPath, unsupported fields, selectedImageTag/selectedBackupId server-only binding, mark-tested current test releaseTag are aligned. |
| Release status | PASS WITH LOCALIZED IMPLEMENTATION | Standalone returns `testCurrentReleaseTag` and `latestTestedReleaseTag`; original resolves from status scripts/properties, standalone additionally derives current test tag from successful local operation history when status probe has no tag. |
| Release package gate | PASS | Manifest, component, packageDirectoryName, include flags, checksum, tested.json, tested recovery set binding and promote-backup recheck are covered by parity tests. |
| Rollback/restore candidates | PASS | Rollback compatibility, prod-latest, recovery set fields, checksum, DCC `chainStatus=COMPLETE`, candidate server binding and blocked reasons match the original behavior. |
| Frontend action payload | PASS | Standalone `App.vue` now builds payload only with fields supported by selected action, matching original `buildOperationActionRequest`. |
| Frontend API type for action request | PASS | Both expose only client-submittable fields; server-derived `selectedImageTag` / `selectedBackupId` are not part of frontend request type. |
| Core scripts | MOSTLY PASS | `apply-test-db-sql.ps1`, `backup-ops.ps1`, local status and local restart scripts are byte-identical. `publish-int-ruoyi.ps1` differs by 64 lines because standalone carries later fixes for explicit repo roots, UTF-8 process capture, and base64 JSON DCC inventory. |
| Linux-local backup mode | GAP | Original switches both script path and argument style to `--mode/--config/...` when `backupOps.executionMode=linux-local`; standalone switches script path but still builds PowerShell-style `-Mode/-NonInteractive` arguments. Default config is `powershell`, so this is conditional. |
| Owner matrix / responsibility gate | INTENTIONAL/PARTIAL | Original persists owner matrix and enforces `validateRequiredOwners` on high-risk actions. Standalone exposes owner-matrix shape but uses local simplified responses and does not reintroduce role/owner gates. |
| Alerts / incidents / inspection / probes / capacity / remote root | PARTIAL | Backend endpoints exist, but standalone implementations are local/minimal or fail-fast for high-risk remote actions. Original has dedicated stores, alert delivery, incident actions, probe snapshots, storage guard, and richer inspection composition. |
| Frontend full governance UI | PARTIAL | Standalone page focuses on core operations and exports a reduced API subset; original frontend exposes operation logs, alerts, inspections, probes, remote root disk, backup points, incidents, and richer wizard/governance panels. |

## Main Findings

1. Core action flow is now aligned with original IntRuoyi for default standalone use:
   - request field validation is strict;
   - mark-tested releaseTag is server-resolved;
   - release package and recovery evidence are manifest/checksum/tested/DCC based;
   - frontend no longer submits unrelated action fields.

2. The current standalone implementation is not a full clone of original operational governance:
   - owner responsibility gate, alert delivery, incident persistence, inspection/probe history, capacity guard, remote-root cleanup/status, and the full original frontend management surface are simplified or intentionally blocked.

3. One non-intentional-looking conditional mismatch remains:
   - `backupOps.executionMode=linux-local` would call the Linux script with PowerShell-style parameters in standalone, while original uses Linux-style `--mode --config --target-environment ...`.

4. The standalone publish script is ahead of the current original script in this workspace:
   - explicit `BackendRepoRoot` / `FrontendRepoRoot`;
   - UTF-8 output capture;
   - base64 JSON DCC object inventory parsing.
   These differences came from prior real-data build validation and are safer than reverting to original.

## Verification Commands

- `python -X utf8 scripts\verify_contracts.py` -> PASS.
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS, 7 tests / 0 failures.
- `pnpm --dir frontend typecheck` -> PASS.

## Conclusion

If the target is “独立本机运行控制台的核心构建、发布包校验、标记测试通过、回滚/恢复候选和前端提交契约与原版一致”，当前结果可以判定为 PASS。

If the target is “原 IntRuoyi 运行控制台完整治理能力 1:1 复制”，当前结果应判定为 PARTIAL，主要缺口是 linux-local 参数、责任人/告警/事故/巡检/探针/容量/远端根盘的完整逻辑，以及对应的完整前端治理界面。
