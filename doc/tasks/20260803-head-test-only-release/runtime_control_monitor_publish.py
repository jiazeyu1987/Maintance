import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
ROOT = "http://127.0.0.1:48181/admin-api/infra/runtime-control"
OPERATION_ID = "op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241"
TERMINAL_STATUSES = {"SUCCESS", "FAILED", "CANCELED", "CANCELLED"}


def api(path: str):
    with urllib.request.urlopen(ROOT + path, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(json.dumps(body, ensure_ascii=False))
    return body["data"]


def redact_log(content: str) -> str:
    content = re.sub(r"(?i)(MYSQL_PWD=)[^\s'\"]+", r"\1<redacted>", content)
    content = re.sub(r"(?i)(mysql\s+[^\n\r]*?\s-p)([^\s'\"]+)", r"\1<redacted>", content)
    content = re.sub(r"(?i)(password\s*[=:]\s*)[^\s'\"]+", r"\1<redacted>", content)
    return content


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_log() -> None:
    log_path = "/operations/" + urllib.parse.quote(OPERATION_ID, safe="") + "/log?maxBytes=65536"
    try:
        log = api(log_path)
        content = log.get("content", "") if isinstance(log, dict) else str(log)
        (TASK_DIR / "publish-test-log-tail-r260803a-r1.redacted.txt").write_text(
            redact_log(content), encoding="utf-8"
        )
    except Exception as exc:
        (TASK_DIR / "publish-test-log-tail-r260803a-r1.redacted.txt").write_text(
            "LOG_FETCH_FAILED: " + repr(exc), encoding="utf-8"
        )


def main() -> int:
    last_status = None
    for poll in range(1, 361):
        operations = api("/operations")
        operation = next((op for op in operations if op.get("operationId") == OPERATION_ID), None)
        if operation is None:
            raise RuntimeError("operation not found: " + OPERATION_ID)
        write_json(TASK_DIR / "publish-test-operation-latest-r260803a-r1.json", operation)
        update_log()
        status = operation.get("status")
        if status != last_status or poll % 15 == 0:
            print(
                json.dumps(
                    {
                        "poll": poll,
                        "status": status,
                        "summary": operation.get("summary"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            last_status = status
        if status in TERMINAL_STATUSES:
            write_json(TASK_DIR / "publish-test-operation-final-r260803a-r1.json", operation)
            return 0 if status == "SUCCESS" else 2
        time.sleep(20)
    print("operation monitor timed out", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
