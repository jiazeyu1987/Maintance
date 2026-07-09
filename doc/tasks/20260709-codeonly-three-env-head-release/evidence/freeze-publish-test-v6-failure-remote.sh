set -e
RELEASE_TAG='release-20260709-codeonly-three-env-head-v6'
MIGRATION_ID='20260709_mes_rt000006_batch_record_mapping'
echo '--- date ---'
date -Is
echo '--- release dir ---'
ls -la /var/lib/docker/intruoyi-releases/${RELEASE_TAG} || true
echo '--- required sql checksum ---'
sha256sum /var/lib/docker/intruoyi-releases/${RELEASE_TAG}/required-sql/20260709_mes_rt000006_batch_record_mapping.sql || true
echo '--- release operation lock ---'
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT target_environment, operation_id, release_tag, status, started_at, finished_at, error_message FROM infra_release_operation_lock WHERE target_environment='test'\G" || true
echo '--- failed migration row ---'
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT release_tag,migration_id,file_name,status,started_at,finished_at,error_message FROM infra_release_migration WHERE release_tag='${RELEASE_TAG}' AND migration_id='${MIGRATION_ID}'\G" || true
echo '--- RT000006 route/process snapshot ---'
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT id,code,name,tenant_id,deleted FROM mes_pro_route WHERE code LIKE '%RT000006%' OR name LIKE '%压力泵%' OR name LIKE '%pressure%' ORDER BY tenant_id,id LIMIT 50;" || true
docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -e "SELECT id,code,name,product_name,tenant_id,deleted FROM mes_pro_process WHERE code LIKE '%RT000006%' OR name LIKE '%压力泵%' OR name LIKE '%pressure%' ORDER BY tenant_id,id LIMIT 50;" || true
echo '--- env image tag ---'
grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env || true
echo '--- containers ---'
docker compose -f /opt/intruoyi/runtime/docker-compose.yml ps || true
docker inspect -f '{{.Name}} {{.Config.Image}} {{.State.Status}}' intruoyi-backend intruoyi-frontend 2>/dev/null || true