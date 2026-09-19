import json
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
RELEASE_TAG = "release-20260803-intmain-head-test-r260803a-r1"
HOST = "172.30.30.58"


REMOTE_SCRIPT = f"""#!/usr/bin/env bash
set -euo pipefail
release_tag={json.dumps(RELEASE_TAG)}
remote_app_dir=/opt/intruoyi/runtime
cd "$remote_app_dir"

image_tag=""
if [ -f .env ]; then
  image_tag="$(sed -n 's/^IMAGE_TAG=//p' .env | head -n 1)"
fi
printf 'IMAGE_TAG=%s\\n' "$image_tag"

printf 'CONTAINERS_BEGIN\\n'
docker ps -a --format '{{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}' | grep 'intruoyi' || true
printf 'CONTAINERS_END\\n'

mysql_state=missing
mysql_pass=""
if [ -f .env ]; then
  mysql_pass="$(sed -n 's/^MYSQL_ROOT_PASSWORD=//p' .env | head -n 1)"
  if [ -z "$mysql_pass" ]; then
    mysql_pass="$(sed -n 's/^MYSQL_PASSWORD=//p' .env | head -n 1)"
  fi
fi
if [ -n "$mysql_pass" ] && docker ps --format '{{{{.Names}}}}' | grep -qx 'intruoyi-mysql'; then
  mysql_state=available
fi
printf 'MYSQL_STATE=%s\\n' "$mysql_state"

mysql_scalar() {{
  local db="$1"
  local sql="$2"
  printf '%s\\n' "$sql" | docker exec -i -e MYSQL_PWD="$mysql_pass" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names "$db"
}}

if [ "$mysql_state" = available ]; then
  table_count="$(mysql_scalar information_schema "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ruoyi-vue-pro' AND table_name IN ('infra_release_migration', 'infra_release_operation_lock');" | tail -n 1)"
  printf 'RELEASE_STATE_TABLE_COUNT=%s\\n' "$table_count"
  if [ "$table_count" = "2" ]; then
    running_locks="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment = 'test' AND deleted = b'0' AND status = 'RUNNING';" | tail -n 1)"
    target_failed_running="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0' AND status IN ('FAILED','RUNNING');" | tail -n 1)"
    target_rows="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0';" | tail -n 1)"
    latest_lock="$(mysql_scalar 'ruoyi-vue-pro' "SELECT CONCAT_WS('|', target_environment, operation_id, release_tag, status, COALESCE(DATE_FORMAT(started_at,'%Y-%m-%d %H:%i:%s'),''), COALESCE(DATE_FORMAT(finished_at,'%Y-%m-%d %H:%i:%s'),'')) FROM infra_release_operation_lock WHERE target_environment = 'test' AND deleted = b'0' ORDER BY update_time DESC LIMIT 1;" | tail -n 1)"
    printf 'RUNNING_LOCK_COUNT=%s\\n' "$running_locks"
    printf 'TARGET_RELEASE_FAILED_RUNNING_COUNT=%s\\n' "$target_failed_running"
    printf 'TARGET_RELEASE_MIGRATION_ROWS=%s\\n' "$target_rows"
    printf 'LATEST_TEST_LOCK=%s\\n' "$latest_lock"
  fi
fi
"""


def parse_lines(stdout: str) -> dict:
    result = {"containers": []}
    in_containers = False
    for raw in stdout.splitlines():
        if raw == "CONTAINERS_BEGIN":
            in_containers = True
            continue
        if raw == "CONTAINERS_END":
            in_containers = False
            continue
        if in_containers:
            parts = raw.split("\t")
            if len(parts) >= 3:
                result["containers"].append({"name": parts[0], "image": parts[1], "status": parts[2]})
            elif raw.strip():
                result["containers"].append({"raw": raw})
            continue
        if "=" in raw:
            key, value = raw.split("=", 1)
            result[key] = value
    return result


def main() -> int:
    res = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{HOST}",
            "bash",
            "-s",
        ],
        input=REMOTE_SCRIPT.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
    )
    stdout = res.stdout.decode("utf-8", "replace")
    stderr = res.stderr.decode("utf-8", "replace")
    parsed = parse_lines(stdout)
    evidence = {
        "host": HOST,
        "releaseTag": RELEASE_TAG,
        "returncode": res.returncode,
        "parsed": parsed,
        "stderrRedacted": stderr,
        "gate": {
            "mysqlStateAvailable": parsed.get("MYSQL_STATE") == "available",
            "releaseStateTablesPresent": parsed.get("RELEASE_STATE_TABLE_COUNT") == "2",
            "noRunningTestLock": parsed.get("RUNNING_LOCK_COUNT") == "0",
            "targetReleaseFailedOrRunningZero": parsed.get("TARGET_RELEASE_FAILED_RUNNING_COUNT") == "0",
        },
    }
    out_path = TASK_DIR / "remote-release-precheck-r260803a-r1.json"
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if res.returncode != 0:
        return res.returncode
    if not all(evidence["gate"].values()):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
