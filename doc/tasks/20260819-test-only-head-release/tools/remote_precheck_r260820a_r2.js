const cp = require('child_process');

const script = String.raw`
set -euo pipefail
cd /opt/intruoyi/runtime

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

image_tag=''
if [ -f .env ]; then
  image_tag=$(grep -E '^IMAGE_TAG=' .env | tail -n 1 | cut -d= -f2- || true)
fi

backend_image=$(docker inspect intruoyi-backend --format '{{.Config.Image}}' 2>/dev/null || true)
backend_status=$(docker inspect intruoyi-backend --format '{{.State.Status}}' 2>/dev/null || true)
frontend_image=$(docker inspect intruoyi-frontend --format '{{.Config.Image}}' 2>/dev/null || true)
frontend_status=$(docker inspect intruoyi-frontend --format '{{.State.Status}}' 2>/dev/null || true)
health=$(curl -fsS --max-time 8 http://127.0.0.1:48081/actuator/health 2>/dev/null || true)
frontend_http=$(curl -sS -o /tmp/intruoyi-front-pre.html -w '%{http_code}' --max-time 8 http://127.0.0.1:8081/ 2>/dev/null || true)
release_info=$(curl -fsS --max-time 8 http://127.0.0.1:8081/release-info.json 2>/dev/null || true)
if [ -z "$health" ]; then health='null'; fi
if [ -z "$release_info" ]; then release_info='null'; fi

lock_summary=$(docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro -e "SELECT IFNULL(operation,\\x27\\x27), IFNULL(status,\\x27\\x27), IFNULL(release_tag,\\x27\\x27), IFNULL(environment,\\x27\\x27) FROM infra_release_operation_lock ORDER BY updated_at DESC LIMIT 5;"' 2>/dev/null || true)
migration_summary=$(docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro -e "SELECT status, COUNT(*) FROM infra_release_migration GROUP BY status;"' 2>/dev/null || true)

printf '{\n'
printf '  "imageTag": %s,\n' "$(printf '%s' "$image_tag" | json_escape)"
printf '  "backendImage": %s,\n' "$(printf '%s' "$backend_image" | json_escape)"
printf '  "backendStatus": %s,\n' "$(printf '%s' "$backend_status" | json_escape)"
printf '  "frontendImage": %s,\n' "$(printf '%s' "$frontend_image" | json_escape)"
printf '  "frontendStatus": %s,\n' "$(printf '%s' "$frontend_status" | json_escape)"
printf '  "health": %s,\n' "$health"
printf '  "frontendHttp": %s,\n' "$(printf '%s' "$frontend_http" | json_escape)"
printf '  "releaseInfo": %s,\n' "$release_info"
printf '  "lockSummaryBase64": %s,\n' "$(printf '%s' "$lock_summary" | base64 -w0 | json_escape)"
printf '  "migrationSummaryBase64": %s\n' "$(printf '%s' "$migration_summary" | base64 -w0 | json_escape)"
printf '}\n'
`;

const result = cp.spawnSync('ssh', ['root@172.30.30.58', 'bash', '-s'], {
  input: script,
  encoding: 'utf8',
  maxBuffer: 20 * 1024 * 1024,
});

if (result.stderr) {
  process.stderr.write(result.stderr);
}
if (result.stdout) {
  process.stdout.write(result.stdout);
}
process.exit(result.status ?? 1);
