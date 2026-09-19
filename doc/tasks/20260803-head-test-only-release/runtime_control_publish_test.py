import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
ROOT = "http://127.0.0.1:48181/admin-api/infra/runtime-control"
RELEASE_TAG = "release-20260803-intmain-head-test-r260803a-r1"
TERMINAL_STATUSES = {"SUCCESS", "FAILED", "CANCELED", "CANCELLED"}


def api(path: str, method: str = "GET", payload: dict | None = None, timeout: int = 30):
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        ROOT + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(json.dumps(body, ensure_ascii=False))
    return body.get("data")


def redact_log(content: str) -> str:
    content = re.sub(r"(?i)(MYSQL_PWD=)[^\s'\"]+", r"\1<redacted>", content)
    content = re.sub(r"(?i)(mysql\s+[^\n\r]*?\s-p)([^\s'\"]+)", r"\1<redacted>", content)
    content = re.sub(r"(?i)(password\s*[=:]\s*)[^\s'\"]+", r"\1<redacted>", content)
    return content


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_log(operation_id: str) -> None:
    try:
        path = "/operations/" + urllib.parse.quote(operation_id, safe="") + "/log?maxBytes=65536"
        log = api(path, timeout=30)
        content = log.get("content", "") if isinstance(log, dict) else str(log)
        (TASK_DIR / "publish-test-log-tail-r260803a-r1.redacted.txt").write_text(
            redact_log(content), encoding="utf-8"
        )
    except Exception as exc:
        (TASK_DIR / "publish-test-log-tail-r260803a-r1.redacted.txt").write_text(
            "LOG_FETCH_FAILED: " + repr(exc), encoding="utf-8"
        )


def main() -> int:
    payload = {
        "action": "publish-test",
        "reason": "20260803 HEAD-only test server release deploy from frozen worktree r260803a",
        "releaseTag": RELEASE_TAG,
    }
    submit = api("/actions", "POST", payload, timeout=60)
    write_json(TASK_DIR / "publish-test-submit-r260803a-r1.json", submit)
    operation_id = submit["operationId"]
    print(
        json.dumps(
            {
                "submittedOperationId": operation_id,
                "status": submit.get("status"),
                "summary": submit.get("summary"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    last_status = None
    for poll in range(1, 121):
        operations = api("/operations", timeout=30)
        current = next((op for op in operations if op.get("operationId") == operation_id), None)
        if current is None:
            raise RuntimeError("operation not found: " + operation_id)
        status = current.get("status")
        write_json(TASK_DIR / "publish-test-operation-latest-r260803a-r1.json", current)
        fetch_log(operation_id)
        if status != last_status:
            print(
                json.dumps(
                    {"poll": poll, "status": status, "summary": current.get("summary")},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            last_status = status
        if status in TERMINAL_STATUSES:
            write_json(TASK_DIR / "publish-test-operation-final-r260803a-r1.json", current)
            print(
                json.dumps(
                    {
                        "finalStatus": status,
                        "operationId": operation_id,
                        "summary": current.get("summary"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            return 0 if status == "SUCCESS" else 2
        time.sleep(10)
    print("operation polling timed out", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
