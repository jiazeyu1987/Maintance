import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
ROOT = "http://127.0.0.1:48181/admin-api/infra/runtime-control"
RELEASE_TAG = "release-20260803-dcc-menu-replay-fix-test-r260803b-r1"
SUFFIX = "r260803b-r1"
TERMINAL_STATUSES = {"SUCCESS", "FAILED", "CANCELED", "CANCELLED"}


def api(path: str, method: str = "GET", payload: dict | None = None, timeout: int = 60):
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
    return body


def write_json(name: str, data) -> None:
    (TASK_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def redact_log(content: str) -> str:
    content = re.sub(r"(?i)(MYSQL_PWD=)[^\s'\"]+", r"\1<redacted>", content)
    content = re.sub(r"(?i)(mysql\s+[^\n\r]*?\s-p)([^\s'\"]+)", r"\1<redacted>", content)
    content = re.sub(r"(?i)(password\s*[=:]\s*)[^\s'\"]+", r"\1<redacted>", content)
    content = re.sub(r"(?i)(nas-password\s+)[^\s'\"]+", r"\1<redacted>", content)
    return content


def fetch_log(operation_id: str) -> None:
    try:
        path = "/operations/" + urllib.parse.quote(operation_id, safe="") + "/log?maxBytes=65536"
        body = api(path, timeout=30)
        data = body.get("data")
        content = data.get("content", "") if isinstance(data, dict) else str(data)
        (TASK_DIR / f"build-release-log-tail-{SUFFIX}.redacted.txt").write_text(
            redact_log(content), encoding="utf-8"
        )
    except Exception as exc:
        (TASK_DIR / f"build-release-log-tail-{SUFFIX}.redacted.txt").write_text(
            "LOG_FETCH_FAILED: " + repr(exc), encoding="utf-8"
        )


def preview_gate(preview_body: dict) -> dict:
    data = preview_body["data"]
    args = [str(v) for v in data.get("arguments", [])]

    def has_pair(flag: str, value: str) -> bool:
        for i, item in enumerate(args[:-1]):
            if item == flag and args[i + 1] == value:
                return True
        return False

    joined = " ".join(args).lower()
    checks = {
        "actionBuildRelease": data.get("action") == "build-release",
        "modeBuildRelease": has_pair("-Mode", "build-release"),
        "releaseTagMatches": has_pair("-ReleaseTag", RELEASE_TAG),
        "componentIntruoyi": has_pair("-Component", "intruoyi"),
        "skipDatabaseSync": "-SkipDatabaseSync" in args,
        "skipMinioSync": "-SkipMinioSync" in args,
        "backendRepoRootR260803b": "D:/IntRuoyiWorktree/r260803b-release-app/IntRuoyiBackend" in args,
        "frontendRepoRootR260803b": "D:/IntRuoyiWorktree/r260803b-release-app/IntRuoyiFronted" in args,
        "noDeployMode": "-Mode deploy-release".lower() not in joined,
        "noMarkOrPromoteAction": all(token not in joined for token in ["mark-tested", "promote-prod", "promote-backup"]),
    }
    return {
        "releaseTag": RELEASE_TAG,
        "scriptPath": data.get("scriptPath"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    payload = {
        "action": "build-release",
        "reason": "20260803 DCC menu replay fix test-only release build from frozen r260803b worktrees",
        "releaseTag": RELEASE_TAG,
        "publishScope": "code-only",
        "includeOnlyOffice": False,
        "includeShowroomBuildPackage": False,
        "enableSmartReleaseReport": False,
    }

    preview = api("/actions/preview", "POST", payload, timeout=60)
    write_json(f"build-release-preview-{SUFFIX}.json", preview)
    gate = preview_gate(preview)
    write_json(f"build-release-preview-gate-{SUFFIX}.json", gate)
    print(json.dumps({"previewGate": gate}, ensure_ascii=False), flush=True)
    if not gate["passed"]:
        return 2

    submit = api("/actions", "POST", payload, timeout=60)
    write_json(f"build-release-submit-{SUFFIX}.json", submit)
    operation_id = submit["data"]["operationId"]
    print(json.dumps({"submittedOperationId": operation_id}, ensure_ascii=False), flush=True)

    last_status = None
    for poll in range(1, 181):
        operations = api("/operations", timeout=30)["data"]
        current = next((op for op in operations if op.get("operationId") == operation_id), None)
        if current is None:
            raise RuntimeError("operation not found: " + operation_id)
        write_json(f"build-release-operation-latest-{SUFFIX}.json", current)
        fetch_log(operation_id)
        status = current.get("status")
        if status != last_status or poll % 15 == 0:
            print(
                json.dumps(
                    {"poll": poll, "status": status, "summary": current.get("summary")},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            last_status = status
        if status in TERMINAL_STATUSES:
            write_json(f"build-release-operation-final-{SUFFIX}.json", current)
            return 0 if status == "SUCCESS" else 3
        time.sleep(20)
    print("build operation polling timed out", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())
