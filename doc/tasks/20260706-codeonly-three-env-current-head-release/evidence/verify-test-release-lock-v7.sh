#!/bin/sh
set -eu
TAG='release-20260706-2245-codeonly-three-env-v6'
SQL_LOCK="/tmp/verify_release_lock_v7.sql"
SQL_HISTORY="/tmp/verify_release_history_v7.sql"
SQL_FAILED="/tmp/verify_release_failed_migrations_v7.sql"
cat > "$SQL_LOCK" <<SQL
SELECT operation_id, release_tag, target_environment, status
FROM infra_release_operation_lock
WHERE release_tag = '$TAG' OR operation_id LIKE CONCAT('%', '$TAG')
ORDER BY started_at DESC
LIMIT 20;
SQL
cat > "$SQL_HISTORY" <<SQL
SELECT operation_id, release_tag, target_environment, status
FROM infra_release_operation_history
WHERE release_tag = '$TAG' OR operation_id LIKE CONCAT('%', '$TAG')
ORDER BY started_at DESC
LIMIT 20;
SQL
cat > "$SQL_FAILED" <<SQL
SELECT script_name, apply_status
FROM infra_release_migration_log
WHERE release_tag = '$TAG' AND apply_status NOT IN ('APPLIED','SKIPPED')
ORDER BY id DESC;
SQL
echo "section=release_lock_rows"
docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro' < "$SQL_LOCK"
echo "section=operation_history_rows"
docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro' < "$SQL_HISTORY" || true
echo "section=release_migrations_failed_or_running"
docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro' < "$SQL_FAILED"