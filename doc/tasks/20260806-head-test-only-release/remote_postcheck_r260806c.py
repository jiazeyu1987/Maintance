from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

RELEASE_TAG = "release-20260806-intmain-head-test-r260806c-r1"
TASK_DIR = pathlib.Path(__file__).resolve().parent
RAW = TASK_DIR / "remote-release-postcheck-r260806c-r1.txt"
JSON_OUT = TASK_DIR / "remote-release-postcheck-r260806c-r1.json"

REMOTE_SCRIPT = r"""set -euo pipefail
cd /opt/intruoyi/runtime
printf 'IMAGE_TAG=%s\n' "$(sed -n 's/^IMAGE_TAG=//p' .env | head -n 1)"
printf 'BACKEND_IMAGE=%s\n' "$(docker inspect intruoyi-backend --format '{{.Config.Image}}' 2>/dev/null || true)"
printf 'FRONTEND_IMAGE=%s\n' "$(docker inspect intruoyi-frontend --format '{{.Config.Image}}' 2>/dev/null || true)"
printf 'BACKEND_RUNNING=%s\n' "$(docker inspect intruoyi-backend --format '{{.State.Status}}' 2>/dev/null || true)"
printf 'FRONTEND_RUNNING=%s\n' "$(docker inspect intruoyi-frontend --format '{{.State.Status}}' 2>/dev/null || true)"
printf 'COMPOSE_PS_START\n'
docker compose ps backend frontend --format json || true
printf '\nCOMPOSE_PS_END\n'
printf 'BACKEND_HEALTH_BODY='
set +e
health_body=$(curl -fsS --max-time 15 http://127.0.0.1:48081/actuator/health 2>&1)
health_exit=$?
set -e
printf '%s\n' "$health_body" | tr '\n' ' '
printf '\nBACKEND_HEALTH_EXIT=%s\n' "$health_exit"
printf 'FRONTEND_HTTP_CODE='
curl -sS -o /tmp/codex-postcheck-r260806c.html -w '%{http_code}' --max-time 15 http://127.0.0.1:8081/ || true
printf '\nFRONTEND_TITLE=%s\n' "$(grep -o '<title>[^<]*</title>' /tmp/codex-postcheck-r260806c.html 2>/dev/null | head -n 1 | sed 's/<\/?title>//g')"
printf 'RELEASE_INFO_START\n'
(curl -fsS --max-time 15 http://127.0.0.1:8081/release-info.json || true)
printf '\nRELEASE_INFO_END\n'
printf 'LOCK_AND_MIGRATIONS_START\n'
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 -N ruoyi-vue-pro <<"SQL"
SELECT CONCAT("lock=", target_environment, ":", release_tag, ":", status, ":", IFNULL(REPLACE(error_message, "\n", " "), "")) FROM infra_release_operation_lock WHERE target_environment="test";
SELECT CONCAT("migration_status=", status, ":", COUNT(*)) FROM infra_release_migration WHERE release_tag="__RELEASE_TAG__" GROUP BY status ORDER BY status;
SELECT CONCAT("migration_failed_running=", COUNT(*)) FROM infra_release_migration WHERE release_tag="__RELEASE_TAG__" AND status IN ("FAILED","RUNNING");
SQL' || true
printf 'LOCK_AND_MIGRATIONS_END\n'
""".replace("__RELEASE_TAG__", RELEASE_TAG)


def main() -> int:
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "ConnectionAttempts=1",
        "-o", "StrictHostKeyChecking=no",
        "root@172.30.30.58",
        "bash", "-s",
    ]
    payload = REMOTE_SCRIPT.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    if b"\r" in payload:
        raise RuntimeError("CR byte found in SSH payload")
    proc = subprocess.run(cmd, input=payload, capture_output=True)
    output = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    RAW.write_text(output, encoding="utf-8")
    fields = {}
    for line in output.splitlines():
        if "=" in line and not line.startswith("mysql:") and not line.startswith("close -"):
            key, value = line.split("=", 1)
            if re.fullmatch(r"[A-Z_]+|lock|migration_status|migration_failed_running", key):
                fields.setdefault(key, []).append(value)
    release_info_text = ""
    if "RELEASE_INFO_START" in output and "RELEASE_INFO_END" in output:
        release_info_text = output.split("RELEASE_INFO_START", 1)[1].split("RELEASE_INFO_END", 1)[0].strip()
    try:
        release_info = json.loads(release_info_text) if release_info_text else {}
    except Exception as exc:
        release_info = {"parseError": repr(exc), "raw": release_info_text[:500]}
    checks = {
        "sshExitZero": proc.returncode == 0,
        "imageTagMatches": fields.get("IMAGE_TAG", [""])[0] == RELEASE_TAG,
        "backendImageMatches": fields.get("BACKEND_IMAGE", [""])[0].endswith(":" + RELEASE_TAG),
        "frontendImageMatches": fields.get("FRONTEND_IMAGE", [""])[0].endswith(":" + RELEASE_TAG),
        "backendRunning": fields.get("BACKEND_RUNNING", [""])[0] == "running",
        "frontendRunning": fields.get("FRONTEND_RUNNING", [""])[0] == "running",
        "backendHealthExitZero": fields.get("BACKEND_HEALTH_EXIT", ["1"])[0] == "0",
        "backendHealthUp": '"status":"UP"' in fields.get("BACKEND_HEALTH_BODY", [""])[0] or "UP" in fields.get("BACKEND_HEALTH_BODY", [""])[0],
        "frontendHttp200": fields.get("FRONTEND_HTTP_CODE", [""])[0] == "200",
        "frontendTitlePresent": bool(fields.get("FRONTEND_TITLE", [""])[0]),
        "releaseInfoTagMatches": release_info.get("releaseTag") == RELEASE_TAG,
        "releaseInfoSourceDirtyFalse": bool(release_info.get("sourceRepos")) and all(repo.get("dirty") is False for repo in release_info.get("sourceRepos", [])),
        "releaseLockApplied": any(v.startswith("test:" + RELEASE_TAG + ":APPLIED") for v in fields.get("lock", [])),
        "migrationFailedRunningZero": fields.get("migration_failed_running", [""])[0] == "0",
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "releaseTag": RELEASE_TAG,
        "checks": checks,
        "fields": fields,
        "releaseInfo": release_info,
        "rawEvidencePath": str(RAW),
        "sshReturnCode": proc.returncode,
    }
    JSON_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())