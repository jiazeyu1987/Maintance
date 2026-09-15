from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class RehearsalError(RuntimeError):
    pass


Runner = Callable[[list[str], bytes | None], str]


@dataclass(frozen=True)
class PlannedMigration:
    path: Path
    session_profile: str = ""


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


def _read_migration_list(path: Path) -> list[Path]:
    content = _require_file(path, "migration list")
    try:
        values = json.loads(content.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RehearsalError(f"migration list is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(values, list) or not values:
        raise RehearsalError("migration list must be a non-empty JSON array")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise RehearsalError("migration list entries must be non-blank strings")
    return [Path(value) for value in values]


def _select_planned_migrations(
    migration_paths: list[Path],
    preflight_evidence_path: Path,
) -> list[PlannedMigration]:
    content = _require_file(preflight_evidence_path, "build preflight evidence")
    try:
        evidence = json.loads(content.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RehearsalError(
            f"build preflight evidence is not valid UTF-8 JSON: {preflight_evidence_path}"
        ) from exc
    if not isinstance(evidence, dict):
        raise RehearsalError("build preflight evidence must be a JSON object")
    if evidence.get("schemaVersion") != "release-build-preflight/v1":
        raise RehearsalError("build preflight evidence schemaVersion is invalid")
    if evidence.get("status") != "passed":
        raise RehearsalError("build preflight evidence status must be passed")
    if evidence.get("targetEnvironment") != "test" or evidence.get("publishScope") != "app-release":
        raise RehearsalError("build preflight evidence target contract is invalid")
    planner = evidence.get("planner")
    if not isinstance(planner, dict) or planner.get("status") != "passed":
        raise RehearsalError("build preflight planner status must be passed")
    items = planner.get("items")
    if not isinstance(items, list):
        raise RehearsalError("build preflight planner items must be an array")

    paths_by_name: dict[str, Path] = {}
    for path in migration_paths:
        if path.name in paths_by_name:
            raise RehearsalError(f"duplicate migration filename: {path.name}")
        paths_by_name[path.name] = path

    planned_names: set[str] = set()
    selected: list[Path] = []
    allowed_actions = {
        "APPLY",
        "SKIP_ALREADY_APPLIED",
        "SKIP_ENV_NOT_ALLOWED",
        "SKIP_SCOPE_EXCLUDED",
    }
    for item in items:
        if not isinstance(item, dict):
            raise RehearsalError("build preflight planner item must be an object")
        migration_id = str(item.get("migrationId", "")).strip()
        relative_file = str(item.get("file", "")).strip().replace("\\", "/")
        action = str(item.get("action", "")).strip()
        expected_file = f"required-sql/{migration_id}.sql"
        migration_type = str(item.get("type", "")).strip()
        session_profile = str(item.get("sessionProfile", "")).strip()
        if not migration_id or relative_file != expected_file or action not in allowed_actions:
            raise RehearsalError(f"build preflight planner item is invalid: {migration_id or '<blank>'}")
        name = f"{migration_id}.sql"
        if name in planned_names:
            raise RehearsalError(f"duplicate build preflight migration: {migration_id}")
        planned_names.add(name)
        if action == "APPLY" and migration_type in {"schema", "data", "menu", "config", "permission", "seed"}:
            path = paths_by_name.get(name)
            if path is None:
                raise RehearsalError(f"build preflight migration set does not match migration list: {name}")
            _session_preamble_for_profile(session_profile, "test")
            selected.append(PlannedMigration(path=path, session_profile=session_profile))

    if planned_names != set(paths_by_name):
        raise RehearsalError("build preflight migration set does not match migration list")
    return selected


def _normalize_planned_migration(value: Path | PlannedMigration) -> PlannedMigration:
    if isinstance(value, PlannedMigration):
        return PlannedMigration(path=Path(value.path), session_profile=value.session_profile)
    return PlannedMigration(path=Path(value))


def _session_preamble_for_profile(session_profile: str, target_environment: str) -> bytes:
    if session_profile == "":
        return b""
    if session_profile == "dcc-view-matrix-seed":
        if target_environment == "test":
            seed_tenant_id = "122"
            allow_yudao_tenant = "NULL"
        elif target_environment in {"prod", "backup"}:
            seed_tenant_id = "1"
            allow_yudao_tenant = "1"
        else:
            raise RehearsalError(f"unsupported DCC view matrix seed environment: {target_environment}")
        return (
            f"SET @dcc_view_matrix_seed_tenant_id := {seed_tenant_id};\n"
            f"SET @dcc_view_matrix_seed_allow_yudao_tenant := {allow_yudao_tenant};\n"
        ).encode("utf-8")
    raise RehearsalError(f"unsupported migration session profile: {session_profile}")


def run_schema_rehearsal(
    *,
    mysql_image: str,
    schema_path: Path,
    migration_paths: list[Path | PlannedMigration],
    runner: Runner = _default_runner,
    container_name: str | None = None,
    target_environment: str = "test",
) -> dict[str, object]:
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", mysql_image):
        raise RehearsalError("mysql image must be pinned by sha256 digest")
    if not migration_paths:
        raise RehearsalError("at least one migration is required")
    schema = _require_file(Path(schema_path), "schema-only snapshot")
    planned_migrations = [_normalize_planned_migration(path) for path in migration_paths]
    migrations = [
        (planned, _require_file(planned.path, "migration"))
        for planned in planned_migrations
    ]
    name = container_name or "release-schema-rehearsal-" + uuid.uuid4().hex[:16]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{7,62}", name):
        raise RehearsalError("container name is invalid")

    started = False
    try:
        runner([
            "docker", "run", "--detach", "--name", name,
            "--env", "MYSQL_ALLOW_EMPTY_PASSWORD=yes", mysql_image,
            "--skip-log-bin", "--lower_case_table_names=1",
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
        for pass_number in range(1, 3):
            for planned, content in migrations:
                try:
                    session_preamble = _session_preamble_for_profile(
                        planned.session_profile,
                        target_environment,
                    )
                    runner(mysql, session_preamble + content)
                except RehearsalError as exc:
                    raise RehearsalError(
                        f"migration failed: {planned.path} (pass {pass_number}): {exc}"
                    ) from exc
        return {
            "status": "passed",
            "mysqlImage": mysql_image,
            "lowerCaseTableNames": 1,
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
    parser.add_argument("--migration-list", required=True)
    parser.add_argument("--preflight-evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    migration_paths = _select_planned_migrations(
        _read_migration_list(Path(args.migration_list)),
        Path(args.preflight_evidence),
    )
    if not migration_paths:
        _require_file(Path(args.schema), "schema-only snapshot")
        if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", args.mysql_image):
            raise RehearsalError("mysql image must be pinned by sha256 digest")
        report = {
            "status": "passed",
            "mysqlImage": args.mysql_image,
            "lowerCaseTableNames": 1,
            "migrationCount": 0,
            "passes": 0,
        }
    else:
        report = run_schema_rehearsal(
            mysql_image=args.mysql_image,
            schema_path=Path(args.schema),
            migration_paths=migration_paths,
        )
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
