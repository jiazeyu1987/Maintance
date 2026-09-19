from __future__ import annotations

import pathlib
import subprocess
import sys


OUTPUT = pathlib.Path(__file__).with_name("post-failure-runtime-probe-r260806b-r2.txt")

REMOTE_SCRIPT = r"""set -euo pipefail
cd /opt/intruoyi/runtime
printf 'IMAGE_TAG=%s\n' "$(sed -n 's/^IMAGE_TAG=//p' .env | head -n 1)"
printf 'COMPOSE_PS_START\n'
docker compose ps backend frontend --format json || true
printf '\nCOMPOSE_PS_END\n'
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
curl -sS -o /tmp/codex-frontend-r260806b.html -w '%{http_code}' --max-time 10 http://127.0.0.1:8081/ || true
printf '\nFRONTEND_TITLE=%s\n' "$(grep -o '<title>[^<]*</title>' /tmp/codex-frontend-r260806b.html 2>/dev/null | head -n 1 | sed 's/<\/\?title>//g')"
printf 'RELEASE_INFO_START\n'
(curl -fsS --max-time 10 http://127.0.0.1:8081/release-info.json || true)
printf '\nRELEASE_INFO_END\n'
printf 'LOCK_AND_MIGRATIONS_START\n'
docker exec intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 -N ruoyi-vue-pro <<"SQL"
SELECT CONCAT("lock=", target_environment, ":", release_tag, ":", status, ":", IFNULL(REPLACE(error_message, "\n", " "), "")) FROM infra_release_operation_lock WHERE target_environment="test";
SELECT CONCAT("migration_status=", status, ":", COUNT(*)) FROM infra_release_migration WHERE release_tag="release-20260806-intmain-head-test-r260806b-r2" GROUP BY status ORDER BY status;
SELECT CONCAT("migration_failed_running=", COUNT(*)) FROM infra_release_migration WHERE release_tag="release-20260806-intmain-head-test-r260806b-r2" AND status IN ("FAILED","RUNNING");
SQL' || true
printf 'LOCK_AND_MIGRATIONS_END\n'
"""


def main() -> int:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "StrictHostKeyChecking=no",
        "root@172.30.30.58",
        "bash",
        "-s",
    ]
    proc = subprocess.run(
        cmd,
        input=REMOTE_SCRIPT.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"),
        capture_output=True,
    )
    output = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    OUTPUT.write_text(output, encoding="utf-8")
    sys.stdout.write(output)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
