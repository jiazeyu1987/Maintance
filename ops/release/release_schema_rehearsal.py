from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Callable


class RehearsalError(RuntimeError):
    pass


Runner = Callable[[list[str], bytes | None], str]


def _default_runner(args: list[str], stdin: bytes | None = None) -> str:
    completed = subprocess.run(args, input=stdin, capture_output=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RehearsalError(f"command failed ({completed.returncode}): {args[0]} {args[1]}: {stderr}")
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _require_file(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise RehearsalError(f"{label} is missing: {path}")
    content = path.read_bytes()
    if not content.strip():
        raise RehearsalError(f"{label} is blank: {path}")
    return content


def run_schema_rehearsal(
    *,
    mysql_image: str,
    schema_path: Path,
    migration_paths: list[Path],
    runner: Runner = _default_runner,
    container_name: str | None = None,
) -> dict[str, object]:
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", mysql_image):
        raise RehearsalError("mysql image must be pinned by sha256 digest")
    if not migration_paths:
        raise RehearsalError("at least one migration is required")
    schema = _require_file(Path(schema_path), "schema-only snapshot")
    migrations = [(Path(path), _require_file(Path(path), "migration")) for path in migration_paths]
    name = container_name or "release-schema-rehearsal-" + uuid.uuid4().hex[:16]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{7,62}", name):
        raise RehearsalError("container name is invalid")

    started = False
    try:
        runner([
            "docker", "run", "--detach", "--name", name,
            "--env", "MYSQL_ALLOW_EMPTY_PASSWORD=yes", mysql_image,
            "--skip-log-bin",
        ], None)
        started = True
        for attempt in range(30):
            try:
                runner(["docker", "exec", name, "mysqladmin", "--protocol=TCP", "-h127.0.0.1",
                        "-uroot", "ping", "--silent"], None)
                break
            except RehearsalError:
                if attempt == 29:
                    raise RehearsalError("temporary MySQL did not become ready")
                time.sleep(1)
        mysql = ["docker", "exec", "--interactive", name, "mysql", "--protocol=TCP",
                 "-h127.0.0.1", "-uroot", "--default-character-set=utf8mb4", "ruoyi-vue-pro"]
        runner(["docker", "exec", name, "mysql", "--protocol=TCP", "-h127.0.0.1", "-uroot",
                "-e", "CREATE DATABASE `ruoyi-vue-pro` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"], None)
        runner(mysql, schema)
        for _ in range(2):
            for _, content in migrations:
                runner(mysql, content)
        return {
            "status": "passed",
            "mysqlImage": mysql_image,
            "schemaSha256": hashlib.sha256(schema).hexdigest(),
            "migrationCount": len(migrations),
            "passes": 2,
        }
    finally:
        if started:
            runner(["docker", "rm", "--force", name], None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mysql-image", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--migration", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run_schema_rehearsal(
        mysql_image=args.mysql_image,
        schema_path=Path(args.schema),
        migration_paths=[Path(value) for value in args.migration],
    )
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
