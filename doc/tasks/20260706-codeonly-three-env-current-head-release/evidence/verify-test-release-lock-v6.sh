#!/bin/sh
set -eu
TAG="release-20260706-2245-codeonly-three-env-v6"
echo "section=release_lock_rows"
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro -e "SELECT operation_id, release_tag, target_environment, status FROM infra_release_operation_lock WHERE release_tag='"'"'$TAG'"'"' OR operation_id LIKE CONCAT('%', '"'"'$TAG'"'"') ORDER BY started_at DESC LIMIT 20;"'
echo "section=operation_history_rows"
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro -e "SELECT operation_id, release_tag, target_environment, status FROM infra_release_operation_history WHERE release_tag='"'"'$TAG'"'"' OR operation_id LIKE CONCAT('%', '"'"'$TAG'"'"') ORDER BY started_at DESC LIMIT 20;"' || true
echo "section=release_migrations_failed_or_running"
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro -e "SELECT script_name, apply_status FROM infra_release_migration_log WHERE release_tag='"'"'$TAG'"'"' AND apply_status NOT IN ('APPLIED','SKIPPED') ORDER BY id DESC;"'