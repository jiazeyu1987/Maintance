import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
ROOT = "http://127.0.0.1:48181/admin-api/infra/runtime-control"
RELEASE_TAG = "release-20260806-intmain-head-test-r260806b-r2"
SUFFIX = "r260806b-r2"
APP_HEAD = "04d71d4328bff04833b3e97fe77439c1d00e5f72"
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


def fetch_log(operation_id: str, prefix: str) -> None:
    try:
        path = "/operations/" + urllib.parse.quote(operation_id, safe="") + "/log?maxBytes=131072"
        body = api(path, timeout=30)
        data = body.get("data")
        content = data.get("content", "") if isinstance(data, dict) else str(data)
        (TASK_DIR / f"{prefix}-log-tail-{SUFFIX}.redacted.txt").write_text(
            redact_log(content), encoding="utf-8"
        )
    except Exception as exc:
        (TASK_DIR / f"{prefix}-log-tail-{SUFFIX}.redacted.txt").write_text(
            "LOG_FETCH_FAILED: " + repr(exc), encoding="utf-8"
        )


def has_pair(args: list[str], flag: str, value: str) -> bool:
    return any(item == flag and args[index + 1] == value for index, item in enumerate(args[:-1]))


def gate_build_preview(preview_body: dict) -> dict:
    data = preview_body["data"]
    args = [str(value) for value in data.get("arguments", [])]
    joined = " ".join(args).lower()
    checks = {
        "actionBuildRelease": data.get("action") == "build-release",
        "modeBuildRelease": has_pair(args, "-Mode", "build-release"),
        "releaseTagMatches": has_pair(args, "-ReleaseTag", RELEASE_TAG),
        "componentIntruoyi": has_pair(args, "-Component", "intruoyi"),
        "skipDatabaseSync": "-SkipDatabaseSync" in args,
        "skipMinioSync": "-SkipMinioSync" in args,
        "backendRepoRootR260806b": "D:/IntRuoyiWorktree/r260806b-release-app/IntRuoyiBackend" in args,
        "frontendRepoRootR260806b": "D:/IntRuoyiWorktree/r260806b-release-app/IntRuoyiFronted" in args,
        "noDeployMode": "deploy-release" not in joined,
        "noMarkOrPromoteAction": all(
            token not in joined for token in ["mark-tested", "promote-prod", "promote-backup"]
        ),
    }
    return {"releaseTag": RELEASE_TAG, "scriptPath": data.get("scriptPath"), "checks": checks, "passed": all(checks.values())}


def gate_publish_preview(preview_body: dict) -> dict:
    data = preview_body["data"]
    args = [str(value) for value in data.get("arguments", [])]
    joined = " ".join(args).lower()
    checks = {
        "actionPublishTest": data.get("action") == "publish-test",
        "modeDeployRelease": has_pair(args, "-Mode", "deploy-release"),
        "environmentTest": has_pair(args, "-Environment", "test"),
        "releaseTagMatches": has_pair(args, "-ReleaseTag", RELEASE_TAG),
        "serverHostTest": has_pair(args, "-ServerHost", "172.30.30.58"),
        "remoteAppDirRuntime": has_pair(args, "-RemoteAppDir", "/opt/intruoyi/runtime"),
        "noProdServerHostAsTarget": not has_pair(args, "-ServerHost", "172.30.30.57"),
        "noBackupServerHostAsTarget": not has_pair(args, "-ServerHost", "172.30.30.59"),
        "noMarkOrPromoteAction": all(
            token not in joined for token in ["mark-tested", "promote-prod", "promote-backup"]
        ),
    }
    return {"releaseTag": RELEASE_TAG, "scriptPath": data.get("scriptPath"), "checks": checks, "passed": all(checks.values())}


def poll_operation(operation_id: str, prefix: str, max_polls: int, sleep_seconds: int) -> int:
    last_status = None
    for poll in range(1, max_polls + 1):
        operations = api("/operations", timeout=30)["data"]
        current = next((op for op in operations if op.get("operationId") == operation_id), None)
        if current is None:
            raise RuntimeError("operation not found: " + operation_id)
        write_json(f"{prefix}-operation-latest-{SUFFIX}.json", current)
        fetch_log(operation_id, prefix)
        status = current.get("status")
        if status != last_status or poll % 15 == 0:
            print(json.dumps({"poll": poll, "status": status, "summary": current.get("summary")}, ensure_ascii=False), flush=True)
            last_status = status
        if status in TERMINAL_STATUSES:
            write_json(f"{prefix}-operation-final-{SUFFIX}.json", current)
            return 0 if status == "SUCCESS" else 3
        time.sleep(sleep_seconds)
    print(f"{prefix} operation polling timed out", file=sys.stderr)
    return 4


def build_release() -> int:
    payload = {
        "action": "build-release",
        "reason": "20260806 test-only release build from frozen r260806b clean worktrees",
        "releaseTag": RELEASE_TAG,
        "publishScope": "code-only",
        "includeOnlyOffice": False,
        "includeShowroomBuildPackage": False,
        "enableSmartReleaseReport": False,
    }
    preview = api("/actions/preview", "POST", payload, timeout=60)
    write_json(f"build-release-preview-{SUFFIX}.json", preview)
    gate = gate_build_preview(preview)
    write_json(f"build-release-preview-gate-{SUFFIX}.json", gate)
    print(json.dumps({"previewGate": gate}, ensure_ascii=False), flush=True)
    if not gate["passed"]:
        return 2
    submit = api("/actions", "POST", payload, timeout=60)
    write_json(f"build-release-submit-{SUFFIX}.json", submit)
    operation_id = submit["data"]["operationId"]
    print(json.dumps({"submittedOperationId": operation_id}, ensure_ascii=False), flush=True)
    return poll_operation(operation_id, "build-release", max_polls=240, sleep_seconds=20)


def publish_test() -> int:
    payload = {
        "action": "publish-test",
        "reason": "20260806 test-only publish from frozen r260806b release package",
        "releaseTag": RELEASE_TAG,
    }
    preview = api("/actions/preview", "POST", payload, timeout=60)
    write_json(f"publish-test-preview-{SUFFIX}.json", preview)
    gate = gate_publish_preview(preview)
    write_json(f"publish-test-preview-gate-{SUFFIX}.json", gate)
    print(json.dumps({"previewGate": gate}, ensure_ascii=False), flush=True)
    if not gate["passed"]:
        return 2
    submit = api("/actions", "POST", payload, timeout=60)
    write_json(f"publish-test-submit-{SUFFIX}.json", submit)
    operation_id = submit["data"]["operationId"]
    print(json.dumps({"submittedOperationId": operation_id}, ensure_ascii=False), flush=True)
    return poll_operation(operation_id, "publish-test", max_polls=300, sleep_seconds=20)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "publish"}:
        print("usage: runtime_control_release_r260806b.py [build|publish]", file=sys.stderr)
        return 2
    if sys.argv[1] == "build":
        return build_release()
    return publish_test()


if __name__ == "__main__":
    sys.exit(main())
