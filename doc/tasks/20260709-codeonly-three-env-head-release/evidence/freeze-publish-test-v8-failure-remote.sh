set -eu
RELEASE_TAG='release-20260709-codeonly-three-env-head-v8'
echo "== date =="
date -Is
echo "== env image tag =="
grep -E '^IMAGE_TAG=' /opt/intruoyi/runtime/.env || true
echo "== docker images =="
docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep -E 'intruoyi-(backend|frontend|mysql|redis)' || true
echo "== release dir =="
ls -la "/var/lib/docker/intruoyi-releases/${RELEASE_TAG}" || true
echo "== preflight-plan rt000006 item =="
python3 - <<'PY' || true
import json
from pathlib import Path
p=Path('/var/lib/docker/intruoyi-releases/release-20260709-codeonly-three-env-head-v8/preflight-plan.json')
if p.exists():
    data=json.loads(p.read_text(encoding='utf-8'))
    for item in data.get('items', []):
        if item.get('migrationId') == '20260709_mes_rt000006_batch_record_mapping' or 'rt000006' in str(item).lower():
            print(json.dumps(item, ensure_ascii=False, indent=2))
PY
echo "== manifest rt000006 item =="
python3 - <<'PY' || true
import json
from pathlib import Path
p=Path('/var/lib/docker/intruoyi-releases/release-20260709-codeonly-three-env-head-v8/manifest.json')
if p.exists():
    data=json.loads(p.read_text(encoding='utf-8'))
    for item in data.get('requiredSql', []):
        if item.get('migrationId') == '20260709_mes_rt000006_batch_record_mapping' or 'rt000006' in str(item).lower():
            print(json.dumps(item, ensure_ascii=False, indent=2))
PY
echo "== migration state =="
docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL' || true
SELECT release_tag, migration_id, file_name, target_environment, status, LEFT(COALESCE(error_message,''),240)
FROM infra_release_migration
WHERE release_tag='release-20260709-codeonly-three-env-head-v8'
ORDER BY update_time DESC, id DESC
LIMIT 20;
SQL
echo "== route probe =="
docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL' || true
SELECT id, code, name, deleted FROM mes_pro_route WHERE code LIKE '%RT000006%' OR name LIKE '%压力泵%' LIMIT 20;
SELECT id, code, name, deleted FROM mes_pro_process WHERE code LIKE '%RT000006%' OR name LIKE '%压力泵%' LIMIT 20;
SQL
echo "== operation lock =="
docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL' || true
SELECT target_environment, operation_id, status, LEFT(COALESCE(error_message,''),240) FROM infra_release_operation_lock WHERE target_environment='test';
SQL