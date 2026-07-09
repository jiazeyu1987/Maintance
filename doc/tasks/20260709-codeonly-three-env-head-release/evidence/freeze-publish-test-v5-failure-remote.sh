set -e
RELEASE_TAG='release-20260709-codeonly-three-env-head-v5'
echo '--- date ---'
date -Is
echo '--- release dir ---'
ls -la /var/lib/docker/intruoyi-releases/${RELEASE_TAG} || true
echo '--- required sql checksum ---'
sha256sum /var/lib/docker/intruoyi-releases/${RELEASE_TAG}/required-sql/20260708_mes_balloon_process_device_capacity.sql || true
echo '--- release operation lock ---'
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT target_environment, operation_id, release_tag, status, started_at, finished_at, error_message FROM infra_release_operation_lock WHERE target_environment='test'\G" || true
echo '--- failed migration row ---'
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT release_tag,migration_id,file_name,status,started_at,finished_at,error_message FROM infra_release_migration WHERE release_tag='${RELEASE_TAG}' AND migration_id='20260708_mes_balloon_process_device_capacity'\G" || true
echo '--- env image tag ---'
grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env || true
echo '--- docker images ---'
docker compose -f /opt/intruoyi/runtime/docker-compose.yml ps || true
docker inspect -f '{{.Name}} {{.Config.Image}} {{.State.Status}}' intruoyi-backend intruoyi-frontend 2>/dev/null || true