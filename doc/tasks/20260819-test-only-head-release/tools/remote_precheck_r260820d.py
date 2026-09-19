import json
import subprocess
from datetime import datetime
from pathlib import Path

RELEASE_TAG = "release-20260820-frozen-head-test-r260820d-r1"
TASK_DIR = Path(r"D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260819-test-only-head-release")
EVIDENCE = TASK_DIR / "evidence" / "remote-prepublish-precheck-r260820d-r1.json"

REMOTE_SCRIPT = r"""set -eu
TAG="__RELEASE_TAG__"
cd /opt/intruoyi/runtime
kv() { printf '%s=%s\n' "$1" "$2"; }
image_tag="$(grep '^IMAGE_TAG=' .env | tail -1 | cut -d= -f2- || true)"
kv ENV_IMAGE_TAG "$image_tag"
backend_health="$(curl -fsS --max-time 5 http://127.0.0.1:48081/actuator/health 2>/dev/null | tr -d '\r\n' || true)"
kv BACKEND_HEALTH "$backend_health"
frontend_http="$(curl -o /dev/null -s -w '%{http_code}' --max-time 5 http://127.0.0.1:8081/ || true)"
kv FRONTEND_HTTP "$frontend_http"
lock_rows="$(docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B ruoyi-vue-pro' 2>/dev/null <<SQL
SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND release_tag='__RELEASE_TAG__';
SQL
)"
kv LOCK_ROWS "$lock_rows"
migration_bad_rows="$(docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B ruoyi-vue-pro' 2>/dev/null <<SQL
SELECT COUNT(*) FROM infra_release_migration WHERE target_environment='test' AND release_tag='__RELEASE_TAG__' AND status IN ('FAILED','RUNNING');
SQL
)"
kv MIGRATION_BAD_ROWS "$migration_bad_rows"
running_locks="$(docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B ruoyi-vue-pro' 2>/dev/null <<SQL
SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING';
SQL
)"
kv RUNNING_LOCKS "$running_locks"
"""


def main() -> int:
    script = REMOTE_SCRIPT.replace("__RELEASE_TAG__", RELEASE_TAG)
    proc = subprocess.run(
        ["ssh", "root@172.30.30.58", "bash -s"],
        input=script.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    evidence = {
        "releaseTag": RELEASE_TAG,
        "exitCode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr.replace("mysql -p", "mysql -p***"),
        "checkedAt": datetime.now().isoformat(timespec="seconds"),
    }
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if proc.returncode != 0:
        return proc.returncode
    parsed = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key] = value.strip()
    for key in ("RUNNING_LOCKS", "MIGRATION_BAD_ROWS"):
        value = parsed.get(key, "")
        if value and value != "0":
            raise SystemExit(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
