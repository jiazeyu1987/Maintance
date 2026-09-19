# Verification Report

## Status

BLOCKED

## Historical Attempt: r260821h-r4

## Frozen Input

- Maintenance HEAD: `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`, release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821h\m`.
- App HEAD: `12a773ef285ff34bf2bd25036fd3dff2930912bc`, release worktree `D:\IntRuoyiWorktree\r260821h\a`.
- Both release worktrees were detached and clean before publish. No later app commits were fetched or used.
- Package: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821h-r4`.

## Build Evidence

- Maintenance console build PASS: `scripts\build.ps1`; Maven 26 tests passed, frontend typecheck/build passed.
- JAR: `runtime-control-maintenance-2026.06-SNAPSHOT.jar`; SHA-256 `DDEEAE6B07D8C56287A77A5BE1A997B106541FB3E4D81AC6199CD6D21719614E`.
- `build-release` operation `op-2026-08-21T204711713137200Z-9de34c7d-990f-4236-8d47-70be7309ce14`: `SUCCESS`.
- Manifest validator: `MANIFEST_VALIDATION_PASSED`; `manifest.json`, legacy manifest, artifact hash, sourceRepos, dirty=false, release-info and changeSet all match the frozen app HEAD.
- Version contract: `manifest.packageId/releaseTag`, frontend `release-info.releaseTag` and runtime-console release identifier all use `release-20260821-intmain-head-test-r260821h-r4`; app package version `2026.04-snapshot`; maintenance JAR version `2026.06-SNAPSHOT`.
- Image tar SHA-256: `b9735d8aaf43e4665aec5ea262a7fa92e8c66e16bbbadad7e31ca5203cb5c040`.

## Publish Evidence

- Preview PASS: action `publish-test`, environment `test`, host `172.30.30.58`, remote `/opt/intruoyi/runtime`; no mark-tested/promote actions.
- Publish operation `op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b`: `FAILED`, exit code 1.
- Failure: route snapshot BACKFILL runtime report could not start `MesProRouteVersionSnapshotMigrationRunner`; Spring reported `No default constructor found` and `Application run failed`.

## Failure-State Remote Verification

- Remote status script reported old backend/frontend containers running and HTTP 200, but this only proves the old runtime remains available.
- Remote `.env`: `IMAGE_TAG=release-20260821-intmain-head-test-r260821h-r4`.
- Actual backend image: `intruoyi-backend:hotfix-20260814-route-submit-order-r1`.
- Actual frontend image: `intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`.
- Backend Actuator: `{"status":"UP"}`; frontend `/` HTTP 200; frontend `/release-info.json` remains `release-20260813-intmain-head-test-r260812b-r2`.
- Runtime console `/release-status`: `testCurrentReleaseTag=null`, `testCurrentReleaseNotes=null`; page version acceptance was not run because publish failed.
- Failure impact: `.env`/compose target r4 while actual images and frontend release-info are old. The pre-publish `.env` baseline is not safely proven, so no guessed rollback, release-lock edit, migration-ledger edit, or retry was performed.

## Scope Boundary

- No formal server or backup server access/write.
- No `mark-tested`, `promote-prod`, or `promote-backup`.
- r4 is a failed release candidate and must not be reused for later promotion or retry.

## Issues

- P026: Docker `InvalidDefaultArgInFrom` warning during backend image build; non-blocking in this run, but requires a build preflight/static warning gate.
- P027: raw operation log contained a MySQL password-bearing command; raw log is not evidence and must not be committed. The publisher logger requires a secret-redaction fix.
- P028: publish failure left remote `.env` and actual images/release-info inconsistent; future publish must preserve and restore the pre-write `.env` baseline or fail before remote write.
- P029: Spring multi-constructor Bean lacked explicit `@Autowired`; build tests did not cover real context startup. A later code fix must be committed and rebuilt under a new frozen HEAD/releaseTag.

## Conclusion

The build artifact provenance and manifest gates passed, but the test-server publish and real runtime acceptance did not. The requested test-only release is **not successful** and the task remains `blocked`.

## Current Attempt: r260822a-r2

- Frozen maintenance commit: `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`; frozen app release commit: `c4d2c637bf1f2cea723876ee363f311b1128aaf4`.
- Dedicated worktrees: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m` and `D:\IntRuoyiWorktree\r260822a\a`; build package: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260822-intmain-head-test-r260822a-r2`.
- Build operation `op-2026-08-22T033833931534300Z-c3389b33-a5b1-44e0-9b17-e63dc07cce7e`: `SUCCESS`; manifest validator: `MANIFEST_VALIDATION_PASSED`; sourceRepos commit=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`, dirty=false; frontend version=`2026.04-snapshot`; maintenance JAR version=`2026.06-SNAPSHOT`; releaseTag/packageId and changeSet summary match the frozen app commit.
- Artifact tar SHA-256: `aa2c8e5d2b8748798f2c6f2966806e7c91fb5bedc115a103bddd6c22826ddb68`.
- Publish operation `op-2026-08-22T035621436028400Z-55335b7f-e740-4d0f-a9d1-a85f875648fa`: never reached `SUCCESS`; API/state remained `RUNNING` after the task-owned temporary runner was removed. This is a failed/blocked operation, not a successful publish.
- Route snapshot BACKFILL report: `status=BLOCKED`, `blockerCount=882`; no live backend/frontend switch occurred.
- Remote live containers after cleanup: backend `intruoyi-backend:hotfix-20260814-route-submit-order-r1`, frontend `intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`, both still running. The old runtime health/HTTP state is not acceptance evidence for r260822a-r2.
- Failure-state drift: remote `.env IMAGE_TAG` and Compose target were r2 while the live backend/frontend image tags remained old; the previous `.env` baseline was not safely provable, so no guessed rollback or state-table edit was performed.
- No `mark-tested`, `promote-prod`, `promote-backup`, production write, backup write, migration-ledger edit, or tenant-data repair was performed.
- Raw publish log was rewritten in place as UTF-8 redacted text; raw secret-bearing content was not copied into task evidence. Issues P038-P043 are recorded in `task.md` and `execution-log.md`.

## Decision

`NO-GO`: the test-only release acceptance criteria are not met. Keep the r260822a release worktrees and task state for blocker audit; do not mark `completed` or delete the blocked release worktrees until the route snapshot blocker and operation-state handling are formally resolved.

## Continued Diagnosis: route snapshot BLOCKED/882

- Remote report evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-identity-backfill-r260822a-r2.json`; `status=BLOCKED`, `scannedCount=47`, `updatedCount=0`, `blockerCount=882`.
- Read-only blocker classification: `FLOW_NODES_MISSING=8`, `ROUTE_ID_MISSING=2`, `PROCESS_ID_INVALID=436`, `PRODUCT_BOM_IDENTITY_INVALID=436`.
- Read-only database evidence: `mes_pro_route_version` has 47 rows; tenant 1 (芋道源码) has 46 rows and tenant 122 (测试租户) has 1 row. All 47 rows have both snapshot identity columns empty. No INSERT/UPDATE/DELETE/DDL was executed.
- Sample evidence: route version `id=110` stores 26 `productBoms`; the stored snapshot has `processId=0`, while current `mes_pro_route_product_bom` rows for the corresponding route have positive `process_id`. The release migration explicitly forbids inferring immutable historical snapshot identity from the current projection, so a silent rewrite would be an invalid fallback.
- Root-cause decision: the `@Autowired` runner fix resolved the prior Spring construction failure, but the test server contains historical route snapshots that do not satisfy the strict identity/structure contract. The publisher correctly fails before enforcement; no code or release-script bypass is justified by the current authorization.
- Governance blocker: 46 blockers-bearing rows belong to the protected 芋道源码 tenant, which this task is forbidden to modify. A formal historical snapshot data-governance/remediation plan and applicable authorization are required before another release attempt; until then the task remains `BLOCKED`.

## Continued-Diagnosis Issues

- P044: remote image lacked `jq`; the report summarization probe failed, then Python standard-library parsing of the same report passed. Preflight/automation: yes, check diagnostic tool availability or ship a documented standard-library probe. Avoidance: record tool versions before remote evidence collection.
- P045: first inline MySQL aggregate probe failed from PowerShell/SSH quoting; no database write occurred. A UTF-8 SQL file through stdin passed. Preflight/automation: yes. Avoidance: use file-backed SQL for multi-layer quoting and assert each exit code.
- P046: first JSON path probe used a binary `CHAR(36)` expression and MySQL returned `ERROR 3144`; no database write occurred. Literal `$.` paths in the UTF-8 SQL file passed. Preflight/automation: yes. Avoidance: validate JSON path parameter types with a minimal sample before aggregate probing.
- P047: real route snapshot BACKFILL remained `BLOCKED/882`; release could not reach container/runtime/page/console acceptance. Read-only classification confirmed historical data blockers; no data repair, bypass, or same-tag retry was performed. Preflight/automation: yes, mandatory before remote write. Avoidance: make tenant distribution and blocker reason counts a hard fail-fast gate.
- P048: direct terminal output of Chinese tenant names was garbled; raw output was not used as evidence. Querying `HEX(name)` and decoding as UTF-8 confirmed tenant 1=芋道源码 and 122=测试租户. Preflight/automation: yes. Avoidance: write Chinese database evidence to UTF-8 files or use HEX.

## Continued Decision

`NO-GO / BLOCKED`: build provenance remains valid, but publish-test and real runtime acceptance remain incomplete. The only safe next step is a formally authorized historical snapshot remediation outside this release-only scope, followed by a new frozen worktree and new releaseTag. Do not reuse r260822a-r2, edit migration state, exclude tenant 1, or skip BACKFILL/READINESS.

## Current-State Recheck 2026-08-22

- Frozen maintenance worktree remains detached clean at `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`; frozen app worktree remains detached clean at `c4d2c637bf1f2cea723876ee363f311b1128aaf4`.
- Saved route snapshot report remains `BLOCKED`, with `blockerCount=882`, `scannedCount=47`, and `updatedCount=0`.
- Test server read-only state remains inconsistent: `.env IMAGE_TAG=release-20260822-intmain-head-test-r260822a-r2`, while live backend is `intruoyi-backend:hotfix-20260814-route-submit-order-r1` and live frontend is `intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`; both are running. No task-owned route runner remains.
- A first nested PowerShell/SSH/Python status probe failed locally with a parser error before remote execution; a simpler SSH read-only probe succeeded. This is recorded as P049 and did not modify the server.
- Decision unchanged: `NO-GO / BLOCKED`. The r2 operation is not SUCCESS, target images are not live, and page/console version verification remains invalid.

## Tenant Attribution Recheck

- The report schema does not include `tenantId`, so the blocker tenant split was independently derived by a read-only query of `mes_pro_route_version(id, tenant_id)` and local correlation by `routeVersionId`.
- All 882 blockers mapped successfully: tenant 1 (芋道源码) has 881 blockers (`FLOW_NODES_MISSING=7`, `ROUTE_ID_MISSING=2`, `PROCESS_ID_INVALID=436`, `PRODUCT_BOM_IDENTITY_INVALID=436`); tenant 122 (测试租户) has 1 `FLOW_NODES_MISSING` blocker.
- The frozen migration service calls `selectAllPhysicalRows()` under `TenantUtils.executeIgnore`, and the enforcement SQL rejects any non-zero full-table blocker count. Therefore, repairing only tenant 122 or excluding tenant 1 would not satisfy the release contract and is forbidden.
- This evidence is recorded as P050. No database write, migration-ledger edit, release-lock edit, or container operation occurred.

## Historical Orphan Identity Evidence

- Three test-database historical backup tables were read-only cross-checked: `m3syncbk_20260731025047_schedproc`, `m3syncbk_20260731025254_schedproc`, and `m3syncbk_20260731025525_schedproc`. Their results agree on the historical identities for old `routeProcessId=900124/900125/900126/900127`, historical process IDs `900331/900333/900370/900371`, historical codes `B010/B030/PROC-XLSX-00001/PROC-XLSX-00002`, and historical schedule config IDs `203/204/205/206`.
- Current route `900025` has 23 processes; its first four physical route-process IDs are `926785/926786/926787/926788`, with process IDs `922894/922895/922896/922897` and changed codes `Z2630/Z3710/Z2775/Z2772`. Historical and current IDs/codes differ; overlapping names or ordering are not an auditable mapping.
- Evidence file: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-orphan-route-process-history-r260822a.json`; `readOnly=true`, `writesPerformed=false`, `mappingSourceFound=false`, conclusion `BLOCKED`.
- P062-P064 are recorded in `execution-log.md`: no formal old-to-new mapping source, unsafe identity-by-name/order inference, and one failed MySQL read-only probe without controlled password injection. The probe was rerun through the test runtime environment without recording credentials and without additional writes.
- Formal contract evidence: frozen app `docs/backend-development.md` requires unique proof for stale snapshot identity repair and explicitly forbids using `processId`, process name, `sort`, or runtime fallback as a substitute for formal `routeProcessId` mapping.
- P065-P066 are recorded in `execution-log.md`: one broad source search produced truncated output, and one assumed task path did not exist. Neither created code, database, or server side effects; the follow-up narrowed search confirmed the formal contract but found no mapping source.
- P067 is recorded in `execution-log.md`: the final worktree JSON probe repeated the PowerShell empty-pipe syntax error, then passed after collecting results before piping. Both frozen worktrees remain detached and clean at their recorded commits.

## Current Decision

`NO-GO / BLOCKED`: the remaining 8 `ROUTE_PROCESS_UNRESOLVED` blockers have no formal, auditable mapping source. Do not rebuild, publish, retry r2, run a success-only READINESS path, modify migration state, or delete the frozen release worktrees until an approved remediation design produces a new verified release input.

## Stale-State Recovery

- The test-only recovery SQL has now been applied and verified: both `infra_release_operation_lock` and `infra_release_migration` for `release-20260822-intmain-head-test-r260822a-r2` are `FAILED`, and test `RUNNING` counts are `0`.
- This clears the stale publish residue only. It does not change the release verdict: the correct frozen publish still failed before container switch, live backend/frontend remain on old images, and the task remains `BLOCKED`.
