-- Test-only recovery for the interrupted r260822a-r2 publish.
-- Scope: exact operation and exact migration row only.
-- No business data, containers, production, or backup environment is touched.

UPDATE infra_release_migration
SET status = 'FAILED',
    finished_at = NOW(),
    error_message = 'Recovered stale RUNNING migration after interrupted test-only publish; route snapshot enforcement failed before container switch.',
    updater = 'codex',
    update_time = NOW()
WHERE target_environment = 'test'
  AND release_tag = 'release-20260822-intmain-head-test-r260822a-r2'
  AND operation_id = 'test-release-20260822-intmain-head-test-r260822a-r2'
  AND migration_id = '20260812_mes_route_version_snapshot_identity_enforce'
  AND status = 'RUNNING';

SELECT CASE WHEN ROW_COUNT() = 1 THEN 'MIGRATION_RECOVERY_UPDATED' ELSE 'MIGRATION_RECOVERY_NOT_UPDATED' END;

UPDATE infra_release_operation_lock
SET status = 'FAILED',
    finished_at = NOW(),
    error_message = 'Recovered stale RUNNING lock after interrupted test-only publish; route snapshot enforcement failed before container switch.',
    updater = 'codex',
    update_time = NOW()
WHERE target_environment = 'test'
  AND release_tag = 'release-20260822-intmain-head-test-r260822a-r2'
  AND operation_id = 'test-release-20260822-intmain-head-test-r260822a-r2'
  AND status = 'RUNNING';

SELECT CASE WHEN ROW_COUNT() = 1 THEN 'LOCK_RECOVERY_UPDATED' ELSE 'LOCK_RECOVERY_NOT_UPDATED' END;
