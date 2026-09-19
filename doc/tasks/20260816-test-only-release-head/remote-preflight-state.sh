#!/usr/bin/env bash
set -euo pipefail

cd /opt/intruoyi/runtime

echo 'LOCK_LATEST_BEGIN'
docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$MYSQL_DATABASE" -e "SELECT release_tag,operation_id,status,target_environment,started_at,finished_at,COALESCE(error_message,CHAR(45)) FROM infra_release_operation_lock WHERE target_environment=CHAR(116,101,115,116) AND deleted=0 ORDER BY id DESC LIMIT 10;"'
echo 'LOCK_LATEST_END'

echo 'LOCK_RUNNING_BEGIN'
docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment=CHAR(116,101,115,116) AND status=CHAR(82,85,78,78,73,78,71) AND deleted=0;"'
echo 'LOCK_RUNNING_END'

echo 'MIGRATION_UNRESOLVED_BEGIN'
docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$MYSQL_DATABASE" -e "SELECT release_tag,status,COUNT(*) FROM infra_release_migration WHERE target_environment=CHAR(116,101,115,116) AND status IN (CHAR(70,65,73,76,69,68),CHAR(82,85,78,78,73,78,71)) AND deleted=0 GROUP BY release_tag,status ORDER BY MAX(id) DESC LIMIT 20;"'
echo 'MIGRATION_UNRESOLVED_END'

printf 'ENV_TAG='
sed -n 's/^IMAGE_TAG=//p' .env | tail -n 1
docker compose config --images | sed 's/^/COMPOSE_IMAGE=/'
docker inspect -f 'BACKEND_ACTUAL={{.Config.Image}} state={{.State.Status}}' intruoyi-backend
docker inspect -f 'FRONTEND_ACTUAL={{.Config.Image}} state={{.State.Status}}' intruoyi-frontend
printf 'RELEASE_INFO='
curl -fsS --max-time 10 http://127.0.0.1:8081/release-info.json
printf '\n'
