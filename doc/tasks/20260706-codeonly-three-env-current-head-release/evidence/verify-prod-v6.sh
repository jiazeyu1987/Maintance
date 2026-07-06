#!/bin/sh
set -eu
TAG='release-20260706-2245-codeonly-three-env-v6'
APP_DIR='/opt/intruoyi/runtime'
echo 'section=env_tag'
if [ -f "$APP_DIR/.env" ]; then grep '^IMAGE_TAG=' "$APP_DIR/.env" || true; else echo 'MISSING_ENV'; fi
echo 'section=compose_images'
docker compose -f "$APP_DIR/docker-compose.yml" --env-file "$APP_DIR/.env" config | grep -E 'image:.*intruoyi-(backend|frontend)' || true
echo 'section=running_images'
docker inspect -f '{{.Name}} {{.Config.Image}}' intruoyi-backend intruoyi-frontend 2>/dev/null || true
echo 'section=backend_health'
code=$(curl -sS -o /tmp/prod_backend_health.json -w '%{http_code}' http://127.0.0.1:48081/actuator/health || true)
echo "http_code=$code"
cat /tmp/prod_backend_health.json 2>/dev/null || true
echo
echo 'section=frontend_http'
curl -sS -o /dev/null -w 'http_code=%{http_code}\n' http://127.0.0.1:8081/ || true
echo 'section=pdf_worker_http'
curl -sS -o /dev/null -w 'http_code=%{http_code} content_type=%{content_type}\n' http://127.0.0.1:8081/pdfjs/pdf.worker.mjs || true
echo 'section=release_lock'
cat > /tmp/prod_release_lock_v6.sql <<SQL
SELECT operation_id, release_tag, target_environment, status
FROM infra_release_operation_lock
WHERE target_environment = 'prod'
ORDER BY started_at DESC
LIMIT 5;
SQL
docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro' < /tmp/prod_release_lock_v6.sql || true