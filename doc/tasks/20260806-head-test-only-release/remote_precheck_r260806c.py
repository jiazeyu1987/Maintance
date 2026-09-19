from __future__ import annotations

import pathlib
import subprocess
import sys

RELEASE_TAG = "release-20260806-intmain-head-test-r260806c-r1"
OUTPUT = pathlib.Path(__file__).with_name("remote-release-precheck-r260806c-r1.txt")

REMOTE_SCRIPT = r"""set -euo pipefail
cd /opt/intruoyi/runtime
printf 'IMAGE_TAG=%s\n' "$(sed -n 's/^IMAGE_TAG=//p' .env | head -n 1)"
printf 'BACKEND_IMAGE=%s\n' "$(docker inspect intruoyi-backend --format '{{.Config.Image}}' 2>/dev/null || true)"
printf 'FRONTEND_IMAGE=%s\n' "$(docker inspect intruoyi-frontend --format '{{.Config.Image}}' 2>/dev/null || true)"
printf 'BACKEND_RUNNING=%s\n' "$(docker inspect intruoyi-backend --format '{{.State.Status}}' 2>/dev/null || true)"
printf 'FRONTEND_RUNNING=%s\n' "$(docker inspect intruoyi-frontend --format '{{.State.Status}}' 2>/dev/null || true)"
printf 'BACKEND_HEALTH_BODY='
set +e
health_body=$(curl -fsS --max-time 10 http://127.0.0.1:48081/actuator/health 2>&1)
health_exit=$?
set -e
printf '%s\n' "$health_body" | tr '\n' ' '
printf '\nBACKEND_HEALTH_EXIT=%s\n' "$health_exit"
printf 'FRONTEND_HTTP_CODE='
curl -sS -o /tmp/codex-precheck-r260806c.html -w '%{http_code}' --max-time 10 http://127.0.0.1:8081/ || true
printf '\nFRONTEND_TITLE=%s\n' "$(grep -o '<title>[^<]*</title>' /tmp/codex-precheck-r260806c.html 2>/dev/null | head -n 1 | sed 's/<\/?title>//g')"
printf 'LOCK_AND_MIGRATIONS_START\n'
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 -N ruoyi-vue-pro <<"SQL"
SELECT CONCAT("lock=", target_environment, ":", release_tag, ":", status, ":", IFNULL(REPLACE(error_message, "\n", " "), "")) FROM infra_release_operation_lock WHERE target_environment="test";
SELECT CONCAT("target_migration_failed_running=", COUNT(*)) FROM infra_release_migration WHERE release_tag="__RELEASE_TAG__" AND status IN ("FAILED","RUNNING");
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
    OUTPUT.write_text(output, encoding="utf-8")
    sys.stdout.write(output)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())