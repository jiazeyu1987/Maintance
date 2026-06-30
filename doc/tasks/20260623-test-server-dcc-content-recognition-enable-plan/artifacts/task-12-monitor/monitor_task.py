from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


TASK_SQL = """cat <<'SQL' | docker exec -i intruoyi-mysql env MYSQL_PWD=123456 mysql --default-character-set=utf8mb4 -N -B -uroot ruoyi-vue-pro
SELECT id, status, total_count, processed_count, success_count, failed_count, skipped_existing_count, remaining_count, COALESCE(last_failure_message, '')
FROM dcc_controlled_file_batch_recognition_task
WHERE id = {task_id};
SQL
"""


def now_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(content.replace("\r\n", "\n").replace("\r", "\n"))


def query_task(server_host: str, task_id: int) -> dict[str, object]:
    remote = TASK_SQL.format(task_id=task_id)
    result = subprocess.run(
        ["ssh", f"root@{server_host}", remote],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
    stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]
    data_line = next((line for line in stdout_lines if line.startswith(f"{task_id}\t")), None)
    if data_line is None:
        raise RuntimeError(
            "No task row returned: "
            + json.dumps(
                {
                    "returncode": result.returncode,
                    "stdout": stdout_lines,
                    "stderr": stderr_lines,
                },
                ensure_ascii=False,
            )
        )
    parts = data_line.split("\t", 8)
    if len(parts) != 9:
        raise RuntimeError(f"Unexpected task row format: {data_line}")
    return {
        "checkedAt": now_text(),
        "taskId": int(parts[0]),
        "status": parts[1],
        "totalCount": int(parts[2]),
        "processedCount": int(parts[3]),
        "successCount": int(parts[4]),
        "failedCount": int(parts[5]),
        "skippedExistingCount": int(parts[6]),
        "remainingCount": int(parts[7]),
        "lastFailureMessage": parts[8],
        "diagnostics": {
            "returncode": result.returncode,
            "stdout": [line for line in stdout_lines if line != data_line],
            "stderr": stderr_lines,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-host", default="172.30.30.58")
    parser.add_argument("--task-id", type=int, default=12)
    parser.add_argument("--interval-seconds", type=int, default=120)
    parser.add_argument(
        "--output-dir",
        default=r"D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\artifacts\task-12-monitor",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_path = output_dir / "latest.json"
    history_path = output_dir / "history.ndjson"
    log_path = output_dir / "poll.log"
    meta_path = output_dir / "monitor-meta.json"

    write_text(
        meta_path,
        json.dumps(
            {
                "startedAt": now_text(),
                "serverHost": args.server_host,
                "taskId": args.task_id,
                "intervalSeconds": args.interval_seconds,
                "outputDir": str(output_dir),
                "monitor": "python",
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    last_processed: int | None = None
    last_success: int | None = None
    last_failed: int | None = None

    while True:
        try:
            snapshot = query_task(args.server_host, args.task_id)
            delta_processed = None if last_processed is None else snapshot["processedCount"] - last_processed
            delta_success = None if last_success is None else snapshot["successCount"] - last_success
            delta_failed = None if last_failed is None else snapshot["failedCount"] - last_failed
            record = {
                **snapshot,
                "deltaProcessed": delta_processed,
                "deltaSuccess": delta_success,
                "deltaFailed": delta_failed,
            }
            json_text = json.dumps(record, ensure_ascii=False, indent=2)
            write_text(latest_path, json_text)
            append_text(history_path, json.dumps(record, ensure_ascii=False) + "\n")
            append_text(
                log_path,
                "[{checkedAt}] status={status} processed={processedCount}/{totalCount} "
                "success={successCount} failed={failedCount} skipped={skippedExistingCount} "
                "remaining={remainingCount} deltaProcessed={deltaProcessed} deltaSuccess={deltaSuccess} "
                "deltaFailed={deltaFailed} lastFailure={lastFailureMessage}\n".format(
                    checkedAt=snapshot["checkedAt"],
                    status=snapshot["status"],
                    processedCount=snapshot["processedCount"],
                    totalCount=snapshot["totalCount"],
                    successCount=snapshot["successCount"],
                    failedCount=snapshot["failedCount"],
                    skippedExistingCount=snapshot["skippedExistingCount"],
                    remainingCount=snapshot["remainingCount"],
                    deltaProcessed="null" if delta_processed is None else delta_processed,
                    deltaSuccess="null" if delta_success is None else delta_success,
                    deltaFailed="null" if delta_failed is None else delta_failed,
                    lastFailureMessage=snapshot["lastFailureMessage"] or "-",
                ),
            )
            last_processed = int(snapshot["processedCount"])
            last_success = int(snapshot["successCount"])
            last_failed = int(snapshot["failedCount"])
            if snapshot["status"] not in {"WAITING", "RUNNING"}:
                break
        except Exception as exc:  # noqa: BLE001
            error_record = {
                "checkedAt": now_text(),
                "taskId": args.task_id,
                "status": "MONITOR_ERROR",
                "message": str(exc),
            }
            json_text = json.dumps(error_record, ensure_ascii=False, indent=2)
            write_text(latest_path, json_text)
            append_text(history_path, json.dumps(error_record, ensure_ascii=False) + "\n")
            append_text(
                log_path,
                f"[{error_record['checkedAt']}] status=MONITOR_ERROR message={error_record['message']}\n",
            )
        time.sleep(args.interval_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
