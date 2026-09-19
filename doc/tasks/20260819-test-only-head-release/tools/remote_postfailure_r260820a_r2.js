const cp = require('child_process')
const fs = require('fs')

const releaseTag = 'release-20260820-frozen-head-test-r260820a-r2'
const outPath = 'D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260819-test-only-head-release/remote-postfailure-r260820a-r2.json'

const script = String.raw`
set -euo pipefail
tag="$1"
cd /opt/intruoyi/runtime

section() {
  printf '__BEGIN_%s__\n' "$1"
  cat
  printf '__END_%s__\n' "$1"
}

kv() {
  printf '%s=%s\n' "$1" "$2"
}

image_tag=$(awk -F= '$1=="IMAGE_TAG"{v=$2} END{print v}' .env 2>/dev/null || true)
edhr_endpoint=$(awk -F= '$1=="EDHR_S3_ENDPOINT"{v=$2} END{print v}' .env 2>/dev/null || true)
backend_image=$(docker inspect intruoyi-backend --format '{{.Config.Image}}' 2>/dev/null || true)
backend_status=$(docker inspect intruoyi-backend --format '{{.State.Status}}' 2>/dev/null || true)
frontend_image=$(docker inspect intruoyi-frontend --format '{{.Config.Image}}' 2>/dev/null || true)
frontend_status=$(docker inspect intruoyi-frontend --format '{{.State.Status}}' 2>/dev/null || true)
backend_health=$(curl -fsS --max-time 8 http://127.0.0.1:48081/actuator/health 2>/dev/null | tr -d '\r\n' || true)
frontend_http=$(curl -o /dev/null -s -w '%{http_code}' --max-time 8 http://127.0.0.1:8081/ || true)
release_info=$(curl -fsS --max-time 8 http://127.0.0.1:8081/release-info.json 2>/dev/null | tr -d '\r\n' || true)

mysql_query() {
  docker exec -i intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro' <<SQL
$1
SQL
}

kv IMAGE_TAG "$image_tag"
kv EDHR_ENDPOINT "$edhr_endpoint"
kv BACKEND_IMAGE "$backend_image"
kv BACKEND_STATUS "$backend_status"
kv FRONTEND_IMAGE "$frontend_image"
kv FRONTEND_STATUS "$frontend_status"
kv BACKEND_HEALTH "$backend_health"
kv FRONTEND_HTTP "$frontend_http"
printf '__BEGIN_RELEASE_INFO__\n%s\n__END_RELEASE_INFO__\n' "$release_info"

mysql_query "SELECT CONCAT_WS('\t', target_environment, operation_id, release_tag, status, LEFT(COALESCE(error_message,''), 1000), started_at, finished_at) FROM infra_release_operation_lock WHERE release_tag='$tag' OR status='RUNNING' ORDER BY id DESC LIMIT 20;" | section LOCKS
mysql_query "SELECT CONCAT_WS('\t', status, COUNT(*)) FROM infra_release_migration WHERE release_tag='$tag' GROUP BY status ORDER BY status;" | section TARGET_MIGRATIONS
mysql_query "SELECT CONCAT_WS('\t', release_tag, status, COUNT(*)) FROM infra_release_migration WHERE migration_id='20260814_mes_production_release_flow' GROUP BY release_tag, status ORDER BY release_tag, status;" | section FLOW_LEDGER
mysql_query "SHOW COLUMNS FROM mes_pro_edhr_work_task LIKE 'pqc_release_application_scope_id';" | section FLOW_COLUMN
mysql_query "SELECT COUNT(*) FROM mes_pro_edhr_work_task;" | section WORK_TASK_COUNT
mysql_query "SELECT COUNT(*) FROM infra_release_operation_lock WHERE status='RUNNING';" | section RUNNING_LOCK_COUNT
mysql_query "SELECT release_tag, status, COUNT(*) FROM infra_release_migration WHERE status IN ('FAILED','RUNNING') GROUP BY release_tag, status ORDER BY release_tag, status;" | section FAILED_RUNNING_MIGRATIONS
printf '__BEGIN_BACKEND_LOG_TAIL__\n'
docker logs --tail 220 intruoyi-backend 2>&1 | sed -E 's/-p[^[:space:]]+/-p<redacted>/g; s/(MYSQL_PWD=)[^[:space:]]+/\1<redacted>/g; s/(password[=:])[^\;[:space:]]+/\1<redacted>/Ig' || true
printf '\n__END_BACKEND_LOG_TAIL__\n'
`

function section(text, name) {
  const start = `__BEGIN_${name}__`
  const end = `__END_${name}__`
  const startIndex = text.indexOf(start)
  const endIndex = text.indexOf(end)
  if (startIndex < 0 || endIndex < 0 || endIndex <= startIndex) return ''
  return text.slice(startIndex + start.length, endIndex).replace(/^\r?\n/, '').replace(/\r?\n$/, '')
}

function kv(text, key) {
  const line = text.split(/\r?\n/).find((item) => item.startsWith(`${key}=`))
  return line ? line.slice(key.length + 1) : ''
}

function rows(sectionText) {
  return sectionText ? sectionText.split(/\r?\n/).filter(Boolean) : []
}

const result = cp.spawnSync('ssh', ['root@172.30.30.58', 'bash', '-s', '--', releaseTag], {
  input: Buffer.from(script, 'utf8'),
  maxBuffer: 30 * 1024 * 1024,
})

const stdout = result.stdout.toString('utf8')
const stderr = result.stderr.toString('utf8')
const releaseInfoText = section(stdout, 'RELEASE_INFO')
let releaseInfo = null
try {
  releaseInfo = releaseInfoText ? JSON.parse(releaseInfoText) : null
} catch {
  releaseInfo = { parseError: true, rawPrefix: releaseInfoText.slice(0, 200) }
}

const evidence = {
  releaseTag,
  checkedAt: new Date().toISOString(),
  sshExitCode: result.status,
  sshStderrSanitized: stderr
    .replace(/MYSQL_PWD=[^\s]+/g, 'MYSQL_PWD=<redacted>')
    .replace(/-p[^\s]+/g, '-p<redacted>')
    .slice(0, 2000),
  remote: {
    imageTag: kv(stdout, 'IMAGE_TAG'),
    edhrEndpoint: kv(stdout, 'EDHR_ENDPOINT'),
    backendImage: kv(stdout, 'BACKEND_IMAGE'),
    backendStatus: kv(stdout, 'BACKEND_STATUS'),
    frontendImage: kv(stdout, 'FRONTEND_IMAGE'),
    frontendStatus: kv(stdout, 'FRONTEND_STATUS'),
    backendHealth: kv(stdout, 'BACKEND_HEALTH'),
    frontendHttp: kv(stdout, 'FRONTEND_HTTP'),
    releaseInfo,
  },
  database: {
    locks: rows(section(stdout, 'LOCKS')),
    targetMigrations: rows(section(stdout, 'TARGET_MIGRATIONS')),
    productionReleaseFlowLedger: rows(section(stdout, 'FLOW_LEDGER')),
    pqcReleaseApplicationScopeColumn: rows(section(stdout, 'FLOW_COLUMN')),
    workTaskCount: rows(section(stdout, 'WORK_TASK_COUNT')),
    runningLockCount: rows(section(stdout, 'RUNNING_LOCK_COUNT')),
    failedRunningMigrations: rows(section(stdout, 'FAILED_RUNNING_MIGRATIONS')),
  },
  backendLogTail: section(stdout, 'BACKEND_LOG_TAIL').slice(-16000),
}

evidence.checks = {
  operationFailedForTarget: evidence.database.locks.some((row) => row.includes(releaseTag) && row.includes('FAILED')),
  noRunningLocks: evidence.database.runningLockCount[0] === '0',
  targetMigrationsNoFailedRunning: !evidence.database.targetMigrations.some((row) => /^FAILED|^RUNNING/.test(row)),
  targetMigrationsOnlySkipped: evidence.database.targetMigrations.length === 1 && evidence.database.targetMigrations[0].startsWith('SKIPPED_ALREADY_APPLIED\t'),
  flowColumnExists: evidence.database.pqcReleaseApplicationScopeColumn.length > 0,
  backendImageMatches: evidence.remote.backendImage.includes(releaseTag),
  frontendImageMatches: evidence.remote.frontendImage.includes(releaseTag),
  backendHealthUp: evidence.remote.backendHealth.includes('"UP"'),
  frontendHttp200: evidence.remote.frontendHttp === '200',
  releaseInfoMatches: evidence.remote.releaseInfo && evidence.remote.releaseInfo.releaseTag === releaseTag,
}

fs.writeFileSync(outPath, JSON.stringify(evidence, null, 2), 'utf8')
console.log(JSON.stringify({ outPath, checks: evidence.checks }, null, 2))
process.exit(result.status ?? 1)
