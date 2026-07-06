#!/bin/sh
set -eu
TAG='release-20260706-2245-codeonly-three-env-v6'
APP_DIR='/opt/intruoyi/runtime'
RELEASE_ROOT='/mnt/intruoyi-data/intruoyi-releases'
DATA_ROOT='/mnt/intruoyi-data/runtime-data'
echo 'section=mount'
findmnt -T /mnt/intruoyi-data -o TARGET,SOURCE,FSTYPE,OPTIONS -n || true
df -P /mnt/intruoyi-data || true
echo 'section=paths'
test -d "$RELEASE_ROOT" && echo "release_root_exists=$RELEASE_ROOT"
test -d "$DATA_ROOT" && echo "data_root_exists=$DATA_ROOT"
test -d "$RELEASE_ROOT/$TAG" && echo "release_tag_path_exists=$RELEASE_ROOT/$TAG"
echo 'section=env_tag'
if [ -f "$APP_DIR/.env" ]; then grep '^IMAGE_TAG=' "$APP_DIR/.env" || true; else echo 'MISSING_ENV'; fi
echo 'section=compose_images'
docker compose -f "$APP_DIR/docker-compose.yml" --env-file "$APP_DIR/.env" config | grep -E 'image:.*intruoyi-(backend|frontend)' || true
echo 'section=running_images'
docker inspect -f '{{.Name}} {{.Config.Image}}' intruoyi-backend intruoyi-frontend 2>/dev/null || true
echo 'section=backend_health'
code=$(curl -sS -o /tmp/backup_backend_health.json -w '%{http_code}' http://127.0.0.1:48081/actuator/health || true)
echo "http_code=$code"
cat /tmp/backup_backend_health.json 2>/dev/null || true
echo
echo 'section=frontend_http'
curl -sS -o /dev/null -w 'http_code=%{http_code}\n' http://127.0.0.1:8081/ || true
echo 'section=pdf_worker_http'
curl -sS -o /dev/null -w 'http_code=%{http_code} content_type=%{content_type}\n' http://127.0.0.1:8081/pdfjs/pdf.worker.mjs || true
echo 'section=release_lock'
cat > /tmp/backup_release_lock_v6.sql <<SQL
SELECT operation_id, release_tag, target_environment, status
FROM infra_release_operation_lock
WHERE target_environment = 'backup'
ORDER BY started_at DESC
LIMIT 5;
SQL
docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro' < /tmp/backup_release_lock_v6.sql || true