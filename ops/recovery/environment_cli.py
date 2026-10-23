"""Frozen W05 UTF-8 file request / atomic JSON result entry point."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# The configured interpreter may run with -I. Load only this pinned executor
# directory, never a caller working directory or PYTHONPATH dependency.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from recovery_environment_contract import (EnvironmentFailure, Trust, atomic_json, decode, read_bytes, require, safe_path, utc_now)
from recovery_environment import run_operation


def main(argv=None):
    started_clock = time.monotonic()
    started_at = utc_now()
    parser = argparse.ArgumentParser(description="Prepare an authorized isolated recovery target or start its restored application.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    request = None
    output_path = None
    output_ready = False
    try:
        request_path = safe_path(args.request)
        output_path = safe_path(args.output, exists=False)
        require(output_path != request_path, "REQUEST_OUTPUT_PATH_COLLISION")
        require(not output_path.exists(), "OUTPUT_ALREADY_EXISTS")
        output_ready = True
        request = decode(read_bytes(str(request_path)))
        require(type(request) is dict and all(type(request.get(key)) is str and request[key]
                for key in ("operationId", "requestId", "action")), "REQUEST_IDENTITY_INVALID")
        require(type(request.get("deadlineMilliseconds")) is int and request["deadlineMilliseconds"] > 0, "DEADLINE_INVALID")
        deadline = started_clock + request["deadlineMilliseconds"] / 1000
        result = run_operation(request, Trust(), deadline)
    except EnvironmentFailure as failure:
        if not output_ready or type(request) is not dict or not all(type(request.get(key)) is str and request[key] for key in ("operationId", "requestId", "action")):
            print(failure.code, file=sys.stderr)
            return 2 if failure.unknown else 1
        result = failure.result if failure.result is not None else {"schemaVersion": "backup-restore-operation-result/v1", "operationId": request["operationId"],
                  "requestId": request["requestId"], "action": request["action"],
                  "state": "TERMINAL_UNKNOWN" if failure.unknown else "FAILED_RETAINED", "failureCode": failure.code,
                  "message": failure.code, "data": None, "originalResultPins": [], "startedAt": started_at,
                  "finishedAt": utc_now(), "actualExitCode": None}
    except (OSError, ValueError, TypeError, KeyError) as failure:
        code = "ENVIRONMENT_CLI_" + type(failure).__name__.upper()
        if not output_ready or type(request) is not dict or not all(type(request.get(key)) is str and request[key] for key in ("operationId", "requestId", "action")):
            print(code, file=sys.stderr)
            return 1
        result = {"schemaVersion": "backup-restore-operation-result/v1", "operationId": request["operationId"],
                  "requestId": request["requestId"], "action": request["action"], "state": "TERMINAL_UNKNOWN",
                  "failureCode": code, "message": code, "data": None, "originalResultPins": [],
                  "startedAt": started_at, "finishedAt": utc_now(), "actualExitCode": None}
    try:
        require(not output_path.exists(), "OUTPUT_ALREADY_EXISTS")
        atomic_json(output_path, result)
    except (OSError, EnvironmentFailure) as failure:
        print("RESULT_OUTPUT_NOT_PERSISTED", file=sys.stderr)
        return 2
    return {"SUCCEEDED": 0, "FAILED_RETAINED": 1, "TERMINAL_UNKNOWN": 2}[result["state"]]


if __name__ == "__main__":
    raise SystemExit(main())
