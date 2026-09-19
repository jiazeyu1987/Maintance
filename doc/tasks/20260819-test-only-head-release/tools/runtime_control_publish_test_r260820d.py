"""Preview or submit the one permitted publish-test operation for r260820d."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:48182/admin-api/infra/runtime-control"
TAG = "release-20260820-frozen-head-test-r260820d-r1"
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence"
REQUEST_PAYLOAD = {
    "action": "publish-test",
    "reason": "r260820d test-only publish after manifest, provenance, and runtime-env validation",
    "targetEnvironment": "test",
    "releaseTag": TAG,
}


def request_json(path: str, payload: dict) -> dict:
    request = Request(
        BASE_URL + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        envelope = json.loads(response.read().decode("utf-8"))
    if not isinstance(envelope, dict) or envelope.get("code") != 0:
        raise RuntimeError(f"runtime-control request failed: {envelope!r}")
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"runtime-control response data is missing: {envelope!r}")
    return {"envelope": envelope, "data": data}


def ensure_preview_is_test_only(preview: dict) -> list[str]:
    failures: list[str] = []
    arguments = preview.get("arguments", [])
    argument_pairs = dict(zip(arguments[::2], arguments[1::2]))
    expected = {
        "action": "publish-test",
        "environment": "test",
        "scriptPathContains": True,
        "mode": "deploy-release",
        "targetEnvironment": "test",
        "serverHost": "172.30.30.58",
        "remoteAppDir": "/opt/intruoyi/runtime",
        "releaseTag": TAG,
    }
    actual = {
        "action": preview.get("action"),
        "environment": preview.get("environment"),
        "scriptPathContains": "r260820d" in preview.get("scriptPath", ""),
        "mode": argument_pairs.get("-Mode"),
        "targetEnvironment": REQUEST_PAYLOAD["targetEnvironment"],
        "serverHost": argument_pairs.get("-ServerHost"),
        "remoteAppDir": argument_pairs.get("-RemoteAppDir"),
        "releaseTag": argument_pairs.get("-ReleaseTag"),
    }
    for name, expected_value in expected.items():
        if actual[name] != expected_value:
            failures.append(f"{name}: expected={expected_value!r}, actual={actual[name]!r}")
    forbidden = ["mark-release-tested", "mark-tested", "promote-prod", "promote-backup"]
    serialized = json.dumps(preview, ensure_ascii=False)
    for action in forbidden:
        if action in serialized:
            failures.append(f"forbidden action leaked into preview: {action}")
    if "publishScope" in preview.get("parameters", {}):
        failures.append("publishScope must not be supplied for publish-test")
    return failures


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"preview", "submit"}:
        print("usage: runtime_control_publish_test_r260820d.py preview|submit", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    endpoint = "/actions/preview" if mode == "preview" else "/actions"
    response = request_json(endpoint, REQUEST_PAYLOAD)
    failures = ensure_preview_is_test_only(response["data"]) if mode == "preview" else []
    evidence = {
        "status": "passed" if not failures else "failed",
        "requestPayload": REQUEST_PAYLOAD,
        "response": response["data"],
        "responseCode": response["envelope"]["code"],
        "failedChecks": failures,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    name = f"publish-test-{mode}-r260820d-r1.json"
    (EVIDENCE_DIR / name).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
