#!/usr/bin/env bash
set -euo pipefail

cd /opt/intruoyi/runtime

release_tag='release-20260816-intmain-head-test-r260816a-r1'
run_sql() {
  local sql="$1"
  docker exec -e RELEASE_AUDIT_SQL="$sql" intruoyi-mysql sh -lc \
    'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 -D "$MYSQL_DATABASE" -e "$RELEASE_AUDIT_SQL"'
}

printf 'ENV_TAG='
sed -n 's/^IMAGE_TAG=//p' .env | tail -n 1
docker compose config --images | sed 's/^/COMPOSE_IMAGE=/'
docker inspect -f 'BACKEND_ACTUAL={{.Config.Image}} state={{.State.Status}}' intruoyi-backend
docker inspect -f 'FRONTEND_ACTUAL={{.Config.Image}} state={{.State.Status}}' intruoyi-frontend
printf 'BACKEND_HEALTH='
curl -fsS --max-time 20 http://127.0.0.1:48081/actuator/health
printf '\nFRONTEND_HTTP='
curl -sS -o /tmp/r260816a-failure-index.html -w '%{http_code}' --max-time 20 http://127.0.0.1:8081/
printf '\nFRONTEND_BYTES='
wc -c < /tmp/r260816a-failure-index.html
printf 'RELEASE_INFO='
curl -fsS --max-time 20 http://127.0.0.1:8081/release-info.json
printf '\n'

echo 'LOCK_TARGET_BEGIN'
run_sql "SELECT release_tag,operation_id,status,target_environment,COALESCE(error_message,CHAR(45)),deleted FROM infra_release_operation_lock WHERE release_tag='${release_tag}' ORDER BY id DESC LIMIT 5;"
echo 'LOCK_TARGET_END'

echo 'LOCK_RUNNING_COUNT_BEGIN'
run_sql "SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING' AND deleted=0;"
echo 'LOCK_RUNNING_COUNT_END'

echo 'TARGET_MIGRATION_STATUS_BEGIN'
run_sql "SELECT status,COUNT(*) FROM infra_release_migration WHERE release_tag='${release_tag}' AND target_environment='test' AND deleted=0 GROUP BY status ORDER BY status;"
echo 'TARGET_MIGRATION_STATUS_END'

echo 'TARGET_FAILED_MIGRATION_BEGIN'
run_sql "SELECT migration_id,status,LEFT(COALESCE(error_message,''),240) FROM infra_release_migration WHERE release_tag='${release_tag}' AND target_environment='test' AND status IN ('FAILED','RUNNING') AND deleted=0 ORDER BY id;"
echo 'TARGET_FAILED_MIGRATION_END'

echo 'TARGET_APPLIED_MIGRATION_BEGIN'
run_sql "SELECT migration_id,status FROM infra_release_migration WHERE release_tag='${release_tag}' AND target_environment='test' AND status='APPLIED' AND deleted=0 ORDER BY id;"
echo 'TARGET_APPLIED_MIGRATION_END'

echo 'FORM_CENTER_MIGRATION_HISTORY_BEGIN'
run_sql "SELECT release_tag,migration_id,status,sha256 FROM infra_release_migration WHERE migration_id IN ('20260717_bpm_form_center','20260721_form_center_menu_under_basic_data','20260722_form_center_policy_menu_hide','20260722_form_center_business_action_page_retire','20260813_form_template_menu_before_form_center') AND target_environment='test' AND deleted=0 ORDER BY id;"
echo 'FORM_CENTER_MIGRATION_HISTORY_END'

echo 'FORM_CENTER_MENU_BEGIN'
run_sql "SELECT id,name,parent_id,path,type,deleted FROM system_menu WHERE id=605071200 OR path='form-center' ORDER BY id;"
echo 'FORM_CENTER_MENU_END'

echo 'BASIC_DATA_MENU_BEGIN'
run_sql "SELECT id,name,parent_id,path,type,deleted FROM system_menu WHERE id IN (1186,990200) OR path='/mdm' ORDER BY id;"
echo 'BASIC_DATA_MENU_END'
