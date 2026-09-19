"""Read-only status for the release route snapshot hook container."""

from __future__ import annotations

import subprocess


SCRIPT = r"""set -euo pipefail
cid=$(docker ps --filter name=intruoyi-runtime-backend-run --format '{{.ID}}' | sed -n '1p')
printf 'CID=%s\n' "$cid"
if [ -n "$cid" ]; then
  docker inspect "$cid" --format 'status={{.State.Status}} running={{.State.Running}} exit={{.State.ExitCode}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} image={{.Config.Image}}'
  docker logs --tail 80 "$cid" 2>&1 | sed -E 's/-p[^[:space:]]+/-p<redacted>/g'
fi
"""


def main() -> int:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1", "root@172.30.30.58", "bash", "-s"],
        input=SCRIPT.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.stdout:
        print(result.stdout.decode("utf-8", errors="replace"), end="")
    if result.stderr:
        print(result.stderr.decode("utf-8", errors="replace"), end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
