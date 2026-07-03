set +e
echo "CHECKED_AT=$(date -Is)"
echo "HOSTNAME=$(hostname)"
echo "PWD_BEFORE=$(pwd)"
cd /opt/intruoyi/runtime 2>&1
echo "PWD=$(pwd)"
echo "ENV_IMAGE_TAG=$(grep '^IMAGE_TAG=' .env 2>/dev/null | tail -n 1 | cut -d= -f2-)"
echo "COMPOSE_PS_BEGIN"
docker compose ps 2>&1
echo "COMPOSE_PS_END"
echo "INSPECT_BACKEND_BEGIN"
docker inspect intruoyi-backend --format 'name={{.Name}} image={{.Config.Image}} state={{.State.Status}} running={{.State.Running}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} exit={{.State.ExitCode}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>&1
echo "INSPECT_BACKEND_END"
echo "INSPECT_FRONTEND_BEGIN"
docker inspect intruoyi-frontend --format 'name={{.Name}} image={{.Config.Image}} state={{.State.Status}} running={{.State.Running}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} exit={{.State.ExitCode}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>&1
echo "INSPECT_FRONTEND_END"
echo "PORTS_BEGIN"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E '(:80|:48080|:48181)' || true
echo "PORTS_END"
echo "BACKEND_HEALTH_BEGIN"
curl -sS --max-time 20 -w '\nHTTP_CODE=%{http_code}\n' http://127.0.0.1:48080/actuator/health 2>&1
echo "BACKEND_HEALTH_END"
echo "FRONTEND_HTTP_BEGIN"
curl -sS -o /dev/null -w 'HTTP_CODE=%{http_code}\n' --max-time 20 http://127.0.0.1/ 2>&1
echo "FRONTEND_HTTP_END"
echo "PDF_WORKER_HTTP_BEGIN"
curl -sS -o /dev/null -w 'HTTP_CODE=%{http_code}\n' --max-time 20 http://127.0.0.1/pdf-worker/ 2>&1
echo "PDF_WORKER_HTTP_END"
echo "BACKEND_LOG_TAIL_BEGIN"
docker logs --tail 220 intruoyi-backend 2>&1
echo "BACKEND_LOG_TAIL_END"
echo "FRONTEND_LOG_TAIL_BEGIN"
docker logs --tail 100 intruoyi-frontend 2>&1
echo "FRONTEND_LOG_TAIL_END"
exit 0
