"""Collect a read-only, secret-free post-failure state snapshot for r260820d."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RELEASE_TAG = "release-20260820-frozen-head-test-r260820d-r1"
OPERATION_ID = "op-2026-08-20T035749033642700Z-9fd70534-dc8f-4f9a-a974-e2d6103bae22"
TASK_DIR = Path(r"D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260819-test-only-head-release")
EVIDENCE = TASK_DIR / "evidence" / "publish-test-failure-state-r260820d-r1.json"


REMOTE_SCRIPT = r"""set -u
TAG="__RELEASE_TAG__"
OP="__OPERATION_ID__"
APP_DIR=/opt/intruoyi/runtime
RELEASE_DIR="/var/lib/docker/intruoyi-releases/$TAG"

emit() {
  key="$1"
  value="$2"
  value=$(printf '%s' "$value" | tr '\r\n' '  ' | sed 's/[[:space:]][[:space:]]*/ /g')
  printf '%s=%s\n' "$key" "$value"
}

mysql_query() {
  docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B ruoyi-vue-pro' 2>/dev/null
}

image_of() {
  docker inspect "$1" --format '{{.Config.Image}}' 2>/dev/null || true
}

state_of() {
  docker inspect "$1" --format '{{.State.Status}}|{{.State.Running}}|{{.State.ExitCode}}|{{.State.StartedAt}}|{{.State.FinishedAt}}' 2>/dev/null || true
}

cd "$APP_DIR"
emit ENV_IMAGE_TAG "$(grep '^IMAGE_TAG=' .env 2>/dev/null | tail -1 | cut -d= -f2- || true)"
emit BACKEND_IMAGE "$(image_of intruoyi-backend)"
emit FRONTEND_IMAGE "$(image_of intruoyi-frontend)"
emit BACKEND_STATE "$(state_of intruoyi-backend)"
emit FRONTEND_STATE "$(state_of intruoyi-frontend)"
emit BACKEND_HEALTH_HTTP "$(curl -sS -o /tmp/r260820d-health.json -w '%{http_code}' --max-time 8 http://127.0.0.1:48081/actuator/health 2>/dev/null || true)"
emit BACKEND_HEALTH_BODY "$(cat /tmp/r260820d-health.json 2>/dev/null || true)"
emit FRONTEND_HTTP "$(curl -sS -o /tmp/r260820d-index.html -w '%{http_code}' --max-time 8 http://127.0.0.1:8081/ 2>/dev/null || true)"
emit FRONTEND_HTML_BYTES "$(wc -c </tmp/r260820d-index.html 2>/dev/null || printf '0')"
emit FRONTEND_RELEASE_INFO_HTTP "$(curl -sS -o /tmp/r260820d-release-info.json -w '%{http_code}' --max-time 8 http://127.0.0.1:8081/release-info.json 2>/dev/null || true)"
emit FRONTEND_RELEASE_INFO_TAG "$(grep -o 'release-20260820-frozen-head-test-r260820d-r1' /tmp/r260820d-release-info.json 2>/dev/null | head -1 || true)"

emit TARGET_LOCK_ROWS "$(mysql_query <<SQL
SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND release_tag='$TAG';
SQL
)"
emit TARGET_LOCK_STATUS_COUNTS "$(mysql_query <<SQL
SELECT status, COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND release_tag='$TAG' GROUP BY status ORDER BY status;
SQL
)"
emit OPERATION_LOCK_ROWS "$(mysql_query <<SQL
SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND operation_id='$OP';
SQL
)"
emit RUNNING_LOCKS "$(mysql_query <<SQL
SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING';
SQL
)"
emit TARGET_MIGRATION_STATUS_COUNTS "$(mysql_query <<SQL
SELECT status, COUNT(*) FROM infra_release_migration WHERE target_environment='test' AND release_tag='$TAG' GROUP BY status ORDER BY status;
SQL
)"
emit TARGET_MIGRATION_BAD_ROWS "$(mysql_query <<SQL
SELECT COUNT(*) FROM infra_release_migration WHERE target_environment='test' AND release_tag='$TAG' AND status IN ('FAILED','RUNNING');
SQL
)"
emit TARGET_MIGRATION_ROUTE_STATUS "$(mysql_query <<SQL
SELECT status, COUNT(*) FROM infra_release_migration WHERE target_environment='test' AND release_tag='$TAG' AND migration_id='20260812_mes_route_version_snapshot_identity_enforce' GROUP BY status ORDER BY status;
SQL
)"
emit TARGET_MIGRATION_LAST "$(mysql_query <<SQL
SELECT migration_id, status FROM infra_release_migration WHERE target_environment='test' AND release_tag='$TAG' ORDER BY id DESC LIMIT 1;
SQL
)"

emit RELEASE_DIR_EXISTS "$(test -d "$RELEASE_DIR" && printf true || printf false)"
emit REPORT_DIR_EXISTS "$(test -d "$RELEASE_DIR/runtime-reports" && printf true || printf false)"
emit BACKFILL_REPORT_EXISTS "$(test -f "$RELEASE_DIR/runtime-reports/route-snapshot-identity-backfill.json" && printf true || printf false)"
emit TARGET_HOOK_CONTAINERS "$(docker ps -a --filter ancestor="intruoyi-backend:$TAG" --format '{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}' 2>/dev/null | head -20 || true)"
emit COMPOSE_STATUS "$(docker compose ps --format '{{.Name}}|{{.State}}|{{.Image}}' 2>/dev/null || true)"
"""


def redact(text: str) -> str:
    patterns = [
        (re.compile(r"(?i)(mysql\s+-p)([^\s]+)"), r"\1<redacted>"),
        (re.compile(r"(?i)(password\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
        (re.compile(r"(?i)(secret[_-]?key\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
        (re.compile(r"(?i)(access[_-]?key\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
        (re.compile(r"(?i)(token\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    ]
    for pattern, replacement in patterns:
        text = pattern.sub(replacement, text)
    return text


def parse_lines(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value.strip()
    return result


def main() -> int:
    script = REMOTE_SCRIPT.replace("__RELEASE_TAG__", RELEASE_TAG).replace("__OPERATION_ID__", OPERATION_ID)
    if "\r" in script:
        raise SystemExit("remote script contains CRLF")
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ConnectionAttempts=1",
            "root@172.30.30.58",
            "bash",
            "-s",
        ],
        input=script.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = redact(proc.stderr.decode("utf-8", errors="replace"))
    parsed = parse_lines(stdout)
    evidence = {
        "releaseTag": RELEASE_TAG,
        "operationId": OPERATION_ID,
        "targetEnvironment": "test",
        "serverHost": "172.30.30.58",
        "remoteAppDir": "/opt/intruoyi/runtime",
        "exitCode": proc.returncode,
        "checks": parsed,
        "stderr": stderr,
        "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stdinTransport": "utf8-bytes-lf",
    }
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if proc.returncode != 0:
        return proc.returncode
    required = ("ENV_IMAGE_TAG", "BACKEND_IMAGE", "FRONTEND_IMAGE", "TARGET_MIGRATION_BAD_ROWS")
    missing = [key for key in required if not parsed.get(key)]
    if missing:
        raise SystemExit(f"missing post-failure fields: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
