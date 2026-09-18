# Database Schema Evidence — IDI target route repair

## Data

## Goal

在测试服租户 `1` 中补齐已存在 IDI 项目对应的 `RT000028-IDI` 目标路线及 active binding，使既有发布迁移能够按正式业务数据模型执行。只允许新增本次缺失的业务主数据，不修改芋道源码租户、生产服、备份或 MinIO。

## Migration

The existing `20260830_mes_process_pool_idi_device_parameter_rules` migration is now validation-only. It verifies the formal target route/device/rule baseline and performs no business-data INSERT/UPDATE/DELETE; it no longer infers target rules from source `process_id`.

## Entities and invariants

- `dcc_project_code`: exactly one active `IDI` project for tenant `1`.
- `mes_pro_route`: exactly one active source route `RT000028` and exactly one active target route `RT000028-IDI`.
- `mes_pro_route_dcc_project_binding`: exactly one active binding from IDI project to target route, with `active_route_id = route_id`.
- target route process/device bindings must satisfy the migration's existing `admin` leader and enabled-device predicates.
- target rule baseline contains at least 37 active tenant-aware rules and the five `IDIJSON_01_B09393_*` anchor parameters.
- duplicate active `(route_process_id, device_id, parameter_code)` rows are rejected.

## Safety and rollback

- Pre-write: `SHOW CREATE TABLE`/`DESCRIBE`, full source/target row snapshots, duplicate/soft-deleted checks, and transaction capability check.
- Write: one explicit transaction on `intruoyi-mysql`, additive rows only, creator marker `20260918_idi_target_route_repair`, post-write invariant assertions; any failed assertion rolls back.
- Rollback: execute the recorded primary-key deletes only if post-write verification shows no dependent production report consumed the created rows; otherwise enter recovery review and do not delete.
- Credentials are never written to task logs.

## BDD

BDD: formal IDI target rule baseline -> Given tenant `1` has one active IDI project, source route and a business-provided `RT000028-IDI` target configuration, When the migration runs, Then it only validates target identity, rule completeness and uniqueness and passes idempotently; when the target baseline is missing, Then it blocks before any write and never guesses a source-to-target process mapping.

## TDD evidence

RED: `python -X utf8 -m pytest -q script/tests/test_mes_process_pool_idi_device_parameter_rules_sql.py --tb=short --basetemp .pytest-tmp-20260918-idi-red` -> FAIL, old migration still declared source-process inference and INSERT behavior.

GREEN: `python -X utf8 -m pytest -q script/tests/test_mes_process_pool_idi_device_parameter_rules_sql.py script/tests/test_release_target_preflight_files.py --tb=short --basetemp .pytest-tmp-20260918-idi-contract2` -> PASS, 13 tests.
GREEN: local MySQL executed the repaired migration and target-preflight -> PASS; target-preflight returned `TARGET_PREFLIGHT_PASS:20260830_mes_process_pool_idi_device_parameter_rules`.

## Verification

- Schema evidence captured from the live test database.
- Pre/post invariant query results captured without secrets during the attempted alignment: route=1, route-process=15, binding=1, devices=19, process-device=23, source/target tenant-aware rules=109; the alignment was then rolled back after R85 migration rejected the process-ID/source-rule mismatch.
- `validate_database_schema.py` must pass for this file.
- New release must use one new releaseTag and stop at `publish-test`; no mark-tested/promote/backup.

## Blockers

Current blocker: the test server still lacks the formal IDI target route/device/rule baseline; its authorized alignment must be repeated as a complete, transactionally verifiable data operation before a new releaseTag can be deployed.
