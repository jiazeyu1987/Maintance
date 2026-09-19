# DCC 失效文件引用数据修复证据

## Data Change Goal

用户授权“删除失效的引用，再继续”。本次仅处理本地 MySQL `ruoyi-vue-pro` 中阻断测试服发布包 DCC 对象清单的失效文件引用；目标是在不创建占位文件、不绕过发布门禁、不修改测试服务器的前提下，让 with-data 发布包只包含可证明存在的对象引用。

## Database Engine

- Engine: MySQL 8.0 in local Docker container `int-ruoyi-mysql`
- Affected database: `ruoyi-vue-pro`
- Remote/test/prod databases: not modified

## BDD Scenarios

BDD: remove invalid DCC file references -> Given DCC rows reference `infra_file` paths that have no object in local MinIO, no historical source snapshot, and no `infra_file_content` content, When the user explicitly authorizes deleting invalid references, Then nullable file-id columns are cleared and required-reference records are soft-deleted with backup evidence.

BDD: package gate remains strict -> Given invalid DCC references were repaired locally, When release packaging runs again, Then DCC object inventory must pass from real data and must not be bypassed by placeholder objects or skipped validation.

BDD: test server stays untouched until package is valid -> Given the repair is local data cleanup, When the DCC gate is still failing, Then `publish-test` must not run and no test server state may be changed.

## Data Safety Analysis

- Remaining unresolved DCC refs before repair: `128` total; `126` nonblank object paths and `2` blank paths.
- `infra_file_content` read-only coverage for the `126` nonblank paths: `0` rows / `0` bytes.
- These refs cannot be restored from currently available local historical snapshots or database content.
- Repair rule: do not hard-delete rows. Soft-delete rows whose required file reference is invalid; clear nullable invalid file-id columns where the parent row can remain meaningful.
- Rollback: export all affected rows before update and generate rollback SQL containing original values.

## RED Evidence

RED: dcc-full-bucket-object-preflight-after-restores -> FAIL/BLOCKED, `128` DCC references remained unresolved and would fail release package DCC object inventory.

## GREEN Evidence

- GREEN: dcc-invalid-reference-cleanup -> PASS, applied `dcc-invalid-reference-cleanup-20260909.sql` after exporting `dcc-invalid-reference-cleanup-backup-20260909.json` and rollback SQL `dcc-invalid-reference-cleanup-rollback-20260909.sql`.
- GREEN: dcc-invalid-reference-counts-after-cleanup -> PASS, current unresolved missing fileIds no longer appear in active DCC release reference columns; `infra_file.active_missing_ids=126` are now unreferenced metadata rows and are not release package inputs.
- GREEN: dcc-current-object-inventory-after-cleanup -> PASS, re-exported current DCC release references (`17760` rows, `14016` unique object paths, `0` blank paths) and compared them with current local MinIO `yudao` inventory (`19964` objects); result `missing_paths=0`.

## Blockers

None for local data repair after user authorization. The DCC object consistency blocker is cleared for the current local source data; continue with a fresh releaseTag and keep the strict package gate enabled.

## 2026-09-10 Build-Time Migration Rehearsal

### Data Change Goal

Validate the final release migration plan against a current test-server snapshot without writing the real test database and before expensive application builds.

### Database Engine And Fixture Strategy

- Source: test server MySQL 8.0.39 container `intruoyi-mysql`, read by `mysqldump --single-transaction --quick --routines --triggers --events --hex-blob` only.
- Fixture: disposable same-image MySQL using a releaseTag-scoped Docker volume, `--network none`, and no published ports.
- Package scope: snapshot bytes are streamed container-to-container and never included in the lightweight application package or sent to NAS.

### BDD Scenarios

BDD: final migrations pass before build -> Given a fresh target-state-bound plan and current test snapshot, When build-release starts, Then all APPLY SQL executes successfully in the disposable database before Maven.

BDD: incompatible migration blocks without target writes -> Given an APPLY migration rejects the snapshot, When rehearsal reaches it, Then the releaseTag fails before Maven/NAS/publish and the real migration ledger remains untouched.

BDD: disposable resources are always removed -> Given rehearsal succeeds or fails, When the remote session exits, Then the exact container, volume, SQL archive, and staging directory are absent.

### RED/GREEN Evidence

- RED: missing rehearsal contract -> `2 failed`; no Maven-before ordering, snapshot, isolation, evidence, or cleanup implementation.
- GREEN: contract regression -> PowerShell AST PASS and `scripts/tests/test_release_build_preflight_cache.py` `50 passed`.
- GREEN: snapshot integration -> r29 copied the current 15.4 GB source into same-image MySQL and emitted `REHEARSAL_SNAPSHOT:PASSED`.
- GREEN: fail-fast integration -> three SQL migrations passed; `20260717_mes_balloon_excel_device_workstation_binding` failed with MySQL 1644; Maven never started.
- GREEN: cleanup integration -> `REHEARSAL_CLEANUP:PASSED` and independent `REHEARSAL_RESOURCES_ABSENT`.

### Verification

- The build preflight plan, target state, verified baseline plan, and rehearsal result are copied into package `manifest/` and hashed by normal package integrity generation.
- The same verified target baseline exclusion plan is passed to build-time planning and deploy-time planning; its digest participates in `preflightFingerprint`.
- A successful gate requires authenticated snapshot import, exact APPLY success count, structured evidence, and independently verified resource cleanup before Maven.

### Data Risk And Rollback

- Real test/prod/backup databases are never migration targets for rehearsal.
- Source transaction impact is limited to a consistent logical read and metadata locks inherent to mysqldump; no source UPDATE/DDL is issued.
- Rollback is exact cleanup of the releaseTag-scoped container, Docker volume, archive, and staging directory; cleanup failure blocks the build.

### Blockers

`20260717_mes_balloon_excel_device_workstation_binding` is incompatible with the current test snapshot and must be fixed before a package can be built. No fallback or skip is permitted.

## 2026-09-11 system_signature_password_t1 Active Username Constraint

### Data Change Goal

Fix `20260908_system_signature_password_t1.sql` so the permanent username uniqueness constraint applies to active accounts only while preserving deleted-account audit history.

### BDD Scenario

BDD: active username uniqueness only -> Given deleted `system_users` rows may share a normalized username with active rows, When electronic signature T1 migration runs, Then deleted rows remain auditable and only active duplicate tenant usernames block the release.

### RED/GREEN Evidence

- RED: r43 deploy failed on real test data with `ERROR 1644` because all historical duplicates were counted.
- GREEN: target read-only duplicate probe returned `ALL_DUP_GROUPS=2` and `ACTIVE_DUP_GROUPS=0`, proving the correct constraint boundary.
- GREEN: application commit `713c64112d7b626a2ba71788fd36cc32d686addc` adds `active_canonical_username` generated column and unique key `(tenant_id, active_canonical_username)`.
- GREEN: focused contract tests `10 passed`, migration metadata test `3 passed`, migration policy gate `status=passed migrationCount=607`, and scoped `git diff --check` PASS.

### Data Risk And Rollback

The fix does not alter user identity data beyond the original `canonical_username` backfill already required by T1. Deleted rows are preserved; active duplicate rows still fail fast. Rollback for a failed deploy remains release operation lock failure plus restoring `.env IMAGE_TAG` to the actual running container tag.
