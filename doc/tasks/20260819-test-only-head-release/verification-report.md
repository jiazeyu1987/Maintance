# Verification Report

## Current Result

IN_PROGRESS。`r260819d-r2` build-release 已成功，当前正在进行 publish-test 前的预检与测试服发布；更早的 `r260819a` / `r260819b` 阻塞结论仍保留供追溯。

## Frozen Build Input

- Maintenance repo: branch `int_main`, HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741`, release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819a\m`, worktree status clean。
- App repo: branch `int_main`, HEAD `037e55c280c346df8aa8d89453240ce5c7e0c83a`, release worktree `D:\IntRuoyiWorktree\r260819a\a`, worktree status clean。
- ReleaseTag attempted: `release-20260819-intmain-head-test-r260819a-r1`。

## Build Evidence

- Build preview passed after removing invalid `targetEnvironment`; preview script path was `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819a\m\ops\deploy\publish-int-ruoyi.ps1` with `-Mode build-release`, `-Component intruoyi`, `-SkipDatabaseSync`, `-SkipMinioSync`, and all three environment hosts present。
- Build operation: `op-2026-08-18T174311645827300Z-818527d7-fab1-4411-9cec-bb27e29acdec`。
- Build result: `FAILED`, exit code `1`。
- Failure reason: `executable migration cannot depend on evidence-only migration: migrationId '20260814_mes_c015_route_dcc_qa_reconciliation_schema' (schema) depends on '20260814_mes_c015_route_dcc_qa_reconciliation_backfill' (backfill)`。
- Evidence files: `evidence/build-release-operation-failed-r260819a.json`, `evidence/build-release-operation-failed-r260819a.log`, `evidence/ops-migration-policy-gate-failed-r260819a.json`。

## Package / Manifest Result

- Local release package path `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260819-intmain-head-test-r260819a-r1`: missing。
- `manifest.json` / `release-manifest.json`: not generated。
- Version number / change notes: not generated; cannot be verified for this failed releaseTag。

## Publish / Runtime Result

- `publish-test`: not executed by design, because build-release did not produce a valid package/manifest。
- Test server runtime checks: not executed, because no test deployment occurred。
- Forbidden actions avoided: no `mark-tested`, no `promote-prod`, no `promote-backup`。
- Temporary runtime-control: task-owned release worktree console was stopped after failure; 48181 is currently unreachable, while worktree/state/log evidence remains on disk。

## Blocker

Current frozen HEAD cannot be published under the actual maintenance ops release policy. A formal source fix is required for the migration dependency chain, followed by a new committed HEAD, a new clean release worktree, and a new releaseTag. This task must not continue by editing the release worktree, bypassing the policy gate, hand-modifying the database, or reusing the failed releaseTag。

## Required Evidence

- If resumed after a formal source fix: new task or resumed log must record the new target commit, new releaseTag, actual ops migration policy gate PASS, build-release SUCCESS, manifest/sourceRepos/release-info validation, publish-test SUCCESS, and full test server runtime verification。

## Latest Attempt r260819b

### Current Result

BLOCKED。`r260819b` 已完成当前 HEAD 冻结、两个干净 release worktree 创建、runtime-control 本轮隔离配置生成，以及维护仓实际 ops migration policy gate。构建前置门禁失败，因此没有执行 `build-release`，没有生成发布包/manifest/版本号/变更说明，也没有执行 `publish-test` 或任何正式/备份服动作。

### Frozen Build Input

- Maintenance repo: branch `int_main`, HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741`, release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819b\m`, worktree status clean detached HEAD。
- App repo: branch `int_main`, HEAD `037e55c280c346df8aa8d89453240ce5c7e0c83a`, release worktree `D:\IntRuoyiWorktree\r260819b\a`, worktree status clean detached HEAD。
- ReleaseTag candidate: `release-20260819-intmain-head-test-r260819b-r1`，已判废且未产生构建产物。

### Build Preflight Evidence

- Actual ops gate command: maintenance worktree `ops\release\run-release-migration-policy-gate.py --sql-root D:\IntRuoyiWorktree\r260819b\a\IntRuoyiBackend\sql\mysql`。
- Result: FAIL, `status=failed`。
- Evidence file: `evidence/ops-migration-policy-gate-r260819b.json`。
- Failure reason: `executable migration cannot depend on evidence-only migration: migrationId '20260814_mes_c015_route_dcc_qa_reconciliation_schema' (schema) depends on '20260814_mes_c015_route_dcc_qa_reconciliation_backfill' (backfill)`。

### Publish / Runtime Result

- `build-release`: not executed after preflight failure。
- Package / manifest / version / changeSet: not generated。
- `publish-test`: not executed。
- Test server runtime checks: not applicable because no deployment occurred。
- Forbidden actions avoided: no `mark-tested`, no `promote-prod`, no `promote-backup`。

### Required Fix Before Resume

修复必须进入主程序正式源码并提交：调整 `20260814_mes_c015_route_dcc_qa_reconciliation_schema` 与 `20260814_mes_c015_route_dcc_qa_reconciliation_backfill` 的迁移元数据/依赖关系，使维护仓实际 ops migration policy gate 通过。修复后需要重新冻结新的 HEAD、使用新的 releaseTag，并完整重走 build-release -> publish-test -> 真实运行态验收。

## Follow-up Audit

- App current HEAD remains `037e55c280c346df8aa8d89453240ce5c7e0c83a`; the C015 schema SQL committed at HEAD still declares `dependsOn=20260814_mes_c015_route_dcc_qa_reconciliation_backfill; type=schema`.
- The exact C015 SQL files are not dirty in the app main workspace, so there is no already-existing uncommitted fix to freeze.
- Completing the release requires a formal app source fix and a new committed HEAD; otherwise any build would either fail the actual ops gate or include uncommitted changes, both of which violate the release objective.

## Latest Attempt r260819c

### Current Result

IN PROGRESS。用户授权后已完成主程序正式源码修复与提交，`r260819c` 已从新的 app HEAD 创建干净发布 worktree，并通过 app gate 与维护仓实际 ops migration policy gate。尚未完成 build-release、publish-test 或运行态验证。

### Frozen Build Input

- Maintenance repo: branch `int_main`, HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741`, release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819c\m`, worktree status clean detached HEAD。
- App repo: branch `int_main`, HEAD `22fce6c341c770cb6ac78eb5b2f9f82d5bbcd843`, release worktree `D:\IntRuoyiWorktree\r260819c\a`, worktree status clean detached HEAD。
- ReleaseTag candidate: `release-20260819-intmain-head-test-r260819c-r1`。

### Build Preflight Evidence

- App gate: `evidence/app-migration-policy-gate-r260819c.json`, status=passed, migrationCount=505。
- Maintenance actual ops gate: `evidence/ops-migration-policy-gate-r260819c.json`, status=passed, migrationCount=505。

## Latest Attempt r260819c Publish Failure

### Current Result

FAILED。`r260819c` 的 `build-release`、manifest/sourceRepos/release-info 校验和 `publish-test` 预览均已通过，但唯一 `publish-test` operation `op-2026-08-19T023827875413100Z-13472fce-31e6-4fa5-89d5-8a16f28dccd8` 在 required SQL 阶段失败。

### Failure Evidence

- ReleaseTag: `release-20260819-intmain-head-test-r260819c-r1`。
- Failure SQL: `20260812_mes_pqc_dcc_qa_c00_postflight.sql`。
- Error: `ERROR 1048 (23000) at line 80: Column 'input_manifest_sha256' cannot be null`。
- Remote release lock: `FAILED`。
- Migration counts: `APPLIED=2`, `FAILED=1`, `SKIPPED_ALREADY_APPLIED=433`。
- Evidence file: `evidence/publish-test-failure-state-r260819c.json`。

### Decision

`r260819c` 判废；不得复用该 releaseTag，不得手工修补测试服数据库或 release worktree。需要正式源码修复、提交新的 app HEAD，并以新 releaseTag 重走 build-release -> publish-test -> 真实运行态验收。

## Latest Attempt r260819d

### Current Result

IN PROGRESS。用户再次授权后，主程序已提交 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`（`任务: 修复C00发布后空哈希`），`r260819d` 已从新的 app HEAD 创建干净发布 worktree，并通过 app gate 与维护仓实际 ops migration policy gate。尚未完成 build-release、publish-test 或运行态验证。

### Frozen Build Input

- Maintenance repo: branch `int_main`, HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741`, release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819d\m`, worktree status clean detached HEAD。
- App repo: branch `int_main`, HEAD `adeb3aabc89e03d1f231552015d37bc78e0f2adb`, release worktree `D:\IntRuoyiWorktree\r260819d\a`, worktree status clean detached HEAD。
- ReleaseTag candidate: `release-20260819-intmain-head-test-r260819d-r1`。

### Build Preflight Evidence

- App gate: `evidence/app-migration-policy-gate-r260819d.json`, status=passed, migrationCount=505。
- Maintenance actual ops gate: `evidence/ops-migration-policy-gate-r260819d.json`, status=passed, migrationCount=505。
- Runtime-control config summary: `evidence/runtime-control-config-summary-r260819d.json`。

## r260819d Build Success

- GREEN: build-release-r260819d-r2 -> PASS，operation=`op-2026-08-19T042941283451700Z-b0f3d097-fb52-42a6-9d49-ad7c44a67312`，status=`SUCCESS`，releaseTag=`release-20260819-intmain-head-test-r260819d-r2`。
- GREEN: package-manifest -> PASS，`manifestVersion=1.0`、`packageType=full-release`、`packageId=release-20260819-intmain-head-test-r260819d-r2`、`publishScope=code-only`；backend/admin-frontend `sourceRepos` 均为 `adeb3aabc89e03d1f231552015d37bc78e0f2adb` 且 `dirty=false`。
- GREEN: release-info -> PASS，`release-manifest.json` 的 `gitCommit=adeb3aabc89e03d1f231552015d37bc78e0f2adb`；前端 `dist-intruoyi-test/release-info.json` 的 `releaseTag/packageId/changeSet` 与同一冻结 HEAD 一致。
