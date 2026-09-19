import json
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
HOST = "172.30.30.58"
FAILED_TAG = "release-20260803-intmain-head-test-r260803a-r1"
RESTORE_TAG = "release-20260802-feedback-fix-test-r260802h-r1"


REMOTE_SCRIPT = f"""#!/usr/bin/env bash
set -euo pipefail
cd /opt/intruoyi/runtime
before="$(grep -m1 '^IMAGE_TAG=' .env | cut -d= -f2- || true)"
if [ "$before" != "{FAILED_TAG}" ]; then
  printf 'RESTORE_BLOCKED before=%s expected={FAILED_TAG}\\n' "$before"
  exit 3
fi
python3 -c 'from pathlib import Path
p = Path(".env")
lines = p.read_text().splitlines()
out = []
changed = False
for line in lines:
    if line.startswith("IMAGE_TAG="):
        out.append("IMAGE_TAG={RESTORE_TAG}")
        changed = True
    else:
        out.append(line)
if not changed:
    raise SystemExit("IMAGE_TAG missing")
p.write_text("\\n".join(out) + "\\n")'
after="$(grep -m1 '^IMAGE_TAG=' .env | cut -d= -f2- || true)"
frontend_image="$(docker ps --format '{{{{.Names}}}}\\t{{{{.Image}}}}' | while IFS="$(printf '\\t')" read -r name image; do if [ "$name" = intruoyi-frontend ]; then printf '%s' "$image"; break; fi; done)"
backend_image="$(docker ps --format '{{{{.Names}}}}\\t{{{{.Image}}}}' | while IFS="$(printf '\\t')" read -r name image; do if [ "$name" = intruoyi-backend ]; then printf '%s' "$image"; break; fi; done)"
printf 'RESTORE_OK before=%s after=%s frontend=%s backend=%s\\n' "$before" "$after" "$frontend_image" "$backend_image"
"""


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
        timeout=60,
    )
    evidence = {
        "host": HOST,
        "failedTag": FAILED_TAG,
        "restoreTag": RESTORE_TAG,
        "returncode": res.returncode,
        "stdout": res.stdout.decode("utf-8", "replace"),
        "stderr": res.stderr.decode("utf-8", "replace"),
    }
    (TASK_DIR / "remote-env-restore-after-failed-publish-r260803a-r1.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
