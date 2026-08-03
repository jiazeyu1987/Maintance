import json
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
RELEASE_TAG = "release-20260803-dcc-menu-replay-fix-test-r260803b-r1"
HOST = "172.30.30.58"


REMOTE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail
release_tag="__RELEASE_TAG__"
remote_app_dir=/opt/intruoyi/runtime
cd "$remote_app_dir"

image_tag=""
if [ -f .env ]; then
  image_tag="$(sed -n 's/^IMAGE_TAG=//p' .env | head -n 1)"
fi
printf 'IMAGE_TAG=%s\n' "$image_tag"

printf 'CONTAINERS_BEGIN\n'
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' | grep 'intruoyi' || true
printf 'CONTAINERS_END\n'

health_body=""
health_code="$(curl -sS -m 10 -o /tmp/intruoyi_health.json -w '%{http_code}' http://127.0.0.1:48081/actuator/health || true)"
if [ -f /tmp/intruoyi_health.json ]; then
  health_body="$(tr -d '\r\n' < /tmp/intruoyi_health.json)"
fi
printf 'BACKEND_HEALTH_CODE=%s\n' "$health_code"
printf 'BACKEND_HEALTH_BODY=%s\n' "$health_body"

frontend_code="$(curl -sS -m 10 -o /tmp/intruoyi_frontend.html -w '%{http_code}' http://127.0.0.1:8081/ || true)"
frontend_bytes=0
if [ -f /tmp/intruoyi_frontend.html ]; then
  frontend_bytes="$(wc -c < /tmp/intruoyi_frontend.html | tr -d ' ')"
fi
printf 'FRONTEND_HTTP_CODE=%s\n' "$frontend_code"
printf 'FRONTEND_HTML_BYTES=%s\n' "$frontend_bytes"

release_info_code="$(curl -sS -m 10 -o /tmp/intruoyi_release_info.json -w '%{http_code}' http://127.0.0.1:8081/release-info.json || true)"
release_info_json=""
if [ -f /tmp/intruoyi_release_info.json ]; then
  release_info_json="$(tr -d '\r\n' < /tmp/intruoyi_release_info.json)"
fi
printf 'RELEASE_INFO_HTTP_CODE=%s\n' "$release_info_code"
printf 'RELEASE_INFO_JSON=%s\n' "$release_info_json"

mysql_state=missing
mysql_pass=""
if [ -f .env ]; then
  mysql_pass="$(sed -n 's/^MYSQL_ROOT_PASSWORD=//p' .env | head -n 1)"
  if [ -z "$mysql_pass" ]; then
    mysql_pass="$(sed -n 's/^MYSQL_PASSWORD=//p' .env | head -n 1)"
  fi
fi
if [ -n "$mysql_pass" ] && docker ps --format '{{.Names}}' | grep -qx 'intruoyi-mysql'; then
  mysql_state=available
fi
printf 'MYSQL_STATE=%s\n' "$mysql_state"

mysql_scalar() {
  local db="$1"
  local sql="$2"
  printf '%s\n' "$sql" | docker exec -i -e MYSQL_PWD="$mysql_pass" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names "$db"
}

if [ "$mysql_state" = available ]; then
  table_count="$(mysql_scalar information_schema "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ruoyi-vue-pro' AND table_name IN ('infra_release_migration', 'infra_release_operation_lock');" | tail -n 1)"
  printf 'RELEASE_STATE_TABLE_COUNT=%s\n' "$table_count"
  if [ "$table_count" = "2" ]; then
    running_locks="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment = 'test' AND deleted = b'0' AND status = 'RUNNING';" | tail -n 1)"
    target_failed_running="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0' AND status IN ('FAILED','RUNNING');" | tail -n 1)"
    target_rows="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0';" | tail -n 1)"
    target_applied="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0' AND status = 'APPLIED';" | tail -n 1)"
    latest_lock="$(mysql_scalar 'ruoyi-vue-pro' "SELECT CONCAT_WS('|', target_environment, operation_id, release_tag, status, COALESCE(DATE_FORMAT(started_at,'%Y-%m-%d %H:%i:%s'),''), COALESCE(DATE_FORMAT(finished_at,'%Y-%m-%d %H:%i:%s'),'')) FROM infra_release_operation_lock WHERE target_environment = 'test' AND deleted = b'0' ORDER BY update_time DESC LIMIT 1;" | tail -n 1)"
    current_lock_status="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COALESCE(MAX(status),'') FROM infra_release_operation_lock WHERE release_tag = '$release_tag' AND target_environment = 'test' AND deleted = b'0';" | tail -n 1)"
    historical_failed="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM infra_release_migration WHERE target_environment = 'test' AND deleted = b'0' AND status = 'FAILED' AND release_tag <> '$release_tag';" | tail -n 1)"
    printf 'RUNNING_LOCK_COUNT=%s\n' "$running_locks"
    printf 'TARGET_RELEASE_FAILED_RUNNING_COUNT=%s\n' "$target_failed_running"
    printf 'TARGET_RELEASE_MIGRATION_ROWS=%s\n' "$target_rows"
    printf 'TARGET_RELEASE_APPLIED_ROWS=%s\n' "$target_applied"
    printf 'CURRENT_RELEASE_LOCK_STATUS=%s\n' "$current_lock_status"
    printf 'HISTORICAL_FAILED_MIGRATION_COUNT=%s\n' "$historical_failed"
    printf 'LATEST_TEST_LOCK=%s\n' "$latest_lock"
  fi
  print_permission_count="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM system_menu WHERE permission = 'dcc:controlled-file:print' AND deleted = b'0';" | tail -n 1)"
  fixed_id_count="$(mysql_scalar 'ruoyi-vue-pro' "SELECT COUNT(*) FROM system_menu WHERE id = 6813 AND deleted = b'0';" | tail -n 1)"
  printf 'CONTROLLED_PRINT_PERMISSION_COUNT=%s\n' "$print_permission_count"
  printf 'SYSTEM_MENU_6813_COUNT=%s\n' "$fixed_id_count"
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
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if mode not in {"pre", "post"}:
        print("usage: remote_release_probe_r260803b.py [pre|post]", file=sys.stderr)
        return 2
    script = REMOTE_SCRIPT.replace("__RELEASE_TAG__", RELEASE_TAG)
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
        input=script.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    stdout = res.stdout.decode("utf-8", "replace")
    stderr = res.stderr.decode("utf-8", "replace")
    parsed = parse_lines(stdout)
    release_info = None
    if parsed.get("RELEASE_INFO_JSON"):
        try:
            release_info = json.loads(parsed["RELEASE_INFO_JSON"])
        except json.JSONDecodeError:
            release_info = None

    backend = next((c for c in parsed["containers"] if c.get("name") == "intruoyi-backend"), {})
    frontend = next((c for c in parsed["containers"] if c.get("name") == "intruoyi-frontend"), {})
    common_checks = {
        "sshExitZero": res.returncode == 0,
        "mysqlStateAvailable": parsed.get("MYSQL_STATE") == "available",
        "releaseStateTablesPresent": parsed.get("RELEASE_STATE_TABLE_COUNT") == "2",
        "noRunningTestLock": parsed.get("RUNNING_LOCK_COUNT") == "0",
        "targetReleaseFailedOrRunningZero": parsed.get("TARGET_RELEASE_FAILED_RUNNING_COUNT") == "0",
        "backendHealthUp": parsed.get("BACKEND_HEALTH_CODE") == "200" and '"UP"' in parsed.get("BACKEND_HEALTH_BODY", ""),
        "frontendHttp200": parsed.get("FRONTEND_HTTP_CODE") == "200" and int(parsed.get("FRONTEND_HTML_BYTES") or 0) > 0,
    }
    post_checks = {
        "envImageTagMatches": parsed.get("IMAGE_TAG") == RELEASE_TAG,
        "backendImageMatches": RELEASE_TAG in backend.get("image", ""),
        "frontendImageMatches": RELEASE_TAG in frontend.get("image", ""),
        "backendRunning": "Up" in backend.get("status", ""),
        "frontendRunning": "Up" in frontend.get("status", ""),
        "releaseInfoHttp200": parsed.get("RELEASE_INFO_HTTP_CODE") == "200",
        "releaseInfoTagMatches": bool(release_info) and release_info.get("releaseTag") == RELEASE_TAG,
        "releaseInfoSourceCommitMatches": bool(release_info) and all(
            repo.get("commit") == "ae4c85511f050785f91b51f29c22c511df8e7cdc"
            for repo in release_info.get("sourceRepos", [])
        ),
        "releaseLockApplied": parsed.get("CURRENT_RELEASE_LOCK_STATUS") == "APPLIED",
        "targetReleaseHasAppliedRows": int(parsed.get("TARGET_RELEASE_APPLIED_ROWS") or 0) > 0,
    }
    checks = common_checks if mode == "pre" else {**common_checks, **post_checks}
    evidence = {
        "mode": mode,
        "host": HOST,
        "releaseTag": RELEASE_TAG,
        "returncode": res.returncode,
        "parsed": parsed,
        "releaseInfo": release_info,
        "stderrRedacted": stderr,
        "checks": checks,
        "passed": all(checks.values()),
    }
    output = TASK_DIR / f"remote-release-{mode}check-r260803b-r1.json"
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": mode, "passed": evidence["passed"], "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if evidence["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
