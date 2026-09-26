"""Fail-fast migration checks that run before Maven or any remote write.

The module intentionally accepts a small JSON-like migration plan so the same
rules can be exercised in CI without copying a production database.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class MigrationPreflightError(RuntimeError):
    code: str
    stage: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code} / {self.stage}: {self.detail}"


def _fail(code: str, detail: str) -> None:
    raise MigrationPreflightError(code, "PREFLIGHTING", detail)


def _validate_relative_path(path: str) -> None:
    if not path or "\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        _fail("MIGRATION_PATH_INVALID", path or "<blank>")
    parts = PurePosixPath(path).parts
    if ".." in parts or any(not part or part == "." for part in parts):
        _fail("MIGRATION_PATH_INVALID", path)


def _requires_target_preflight(migration: dict[str, object]) -> bool:
    migration_type = str(migration.get("type", "schema")).strip().lower()
    return migration_type != "schema" or bool(migration.get("dataDependency")) or bool(
        migration.get("requiresTargetPreflight")
    )


def _check_target_preflight(migration: dict[str, object]) -> None:
    if not _requires_target_preflight(migration):
        return
    target = migration.get("targetPreflight")
    if not isinstance(target, dict):
        _fail("TARGET_PREFLIGHT_MISSING", str(migration.get("migrationId", "<unknown>")))
    reference = str(target.get("reference", "")).strip()
    digest = str(target.get("sha256", "")).strip().lower()
    if not reference or not digest or not bool(target.get("readOnly", False)):
        _fail("TARGET_PREFLIGHT_INVALID", str(migration.get("migrationId", "<unknown>")))
    _validate_relative_path(reference)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        _fail("TARGET_PREFLIGHT_INVALID", reference)


def _check_idempotency(migration: dict[str, object]) -> None:
    if migration.get("idempotent") is False:
        _fail("MIGRATION_NOT_IDEMPOTENT", str(migration.get("migrationId", "<unknown>")))
    if int(migration.get("dropCheckCount", 0) or 0) > 1:
        _fail("MIGRATION_NOT_IDEMPOTENT", str(migration.get("migrationId", "<unknown>")))


def _check_schema_ledger(migration: dict[str, object]) -> None:
    ledger = migration.get("schemaLedger")
    if not isinstance(ledger, dict):
        return
    expected = ledger.get("expected")
    actual = ledger.get("actual")
    if expected is not None and actual is not None and expected != actual:
        _fail("SCHEMA_LEDGER_DRIFT", str(migration.get("migrationId", "<unknown>")))


def _check_explicit_tcp(migration: dict[str, object]) -> None:
    connection = migration.get("rehearsalConnection")
    if not isinstance(connection, dict):
        return
    if connection.get("socket") or not connection.get("host") or not connection.get("port"):
        _fail("MYSQL_CONNECTION_CONTRACT_INVALID", str(migration.get("migrationId", "<unknown>")))


def _check_delimiter(migration: dict[str, object], sql: str) -> None:
    if re.search(r"\b(create|alter)\s+procedure\b", sql, re.IGNORECASE) and not re.search(
        r"^\s*delimiter\s+\S+", sql, re.IGNORECASE | re.MULTILINE
    ):
        _fail("SQL_DELIMITER_INVALID", str(migration.get("migrationId", "<unknown>")))


def _check_supersession_contract(migrations: list[dict[str, object]]) -> None:
    known_ids = {
        str(migration.get("migrationId", "")).strip()
        for migration in migrations
        if not str(migration.get("file", "")).strip().startswith("target-preflight/")
    }
    owners: dict[str, str] = {}
    for migration in migrations:
        migration_id = str(migration.get("migrationId", "")).strip()
        supersedes = migration.get("supersedes", []) or []
        if not isinstance(supersedes, list):
            _fail("MIGRATION_SUPERSESSION_INVALID", migration_id or "<unknown>")
        if supersedes and not bool(migration.get("requiresTargetPreflight", False)):
            _fail("MIGRATION_SUPERSESSION_PREFLIGHT_REQUIRED", migration_id or "<unknown>")
        for legacy_value in supersedes:
            legacy_id = str(legacy_value).strip()
            if not legacy_id or legacy_id not in known_ids or legacy_id == migration_id:
                _fail("MIGRATION_SUPERSESSION_INVALID", f"{migration_id}:{legacy_id}")
            previous_owner = owners.get(legacy_id)
            if previous_owner is not None and previous_owner != migration_id:
                _fail("MIGRATION_SUPERSESSION_DUPLICATE", legacy_id)
            owners[legacy_id] = migration_id


def run_migration_preflight(
    migrations: Iterable[dict[str, object]],
    *,
    sql_by_id: dict[str, str] | None = None,
    target_preflight_results: dict[str, bool] | None = None,
) -> dict[str, object]:
    """Validate all migration contracts without opening a database connection."""

    sql_by_id = sql_by_id or {}
    target_preflight_results = target_preflight_results or {}
    migration_list = list(migrations)
    _check_supersession_contract(migration_list)
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for migration in migration_list:
        migration_id = str(migration.get("migrationId", "")).strip()
        if not migration_id or migration_id in seen:
            _fail("MIGRATION_ID_INVALID", migration_id or "<blank>")
        seen.add(migration_id)
        path = str(migration.get("file", "")).strip()
        _validate_relative_path(path)
        if path.startswith("target-preflight/"):
            continue
        _check_target_preflight(migration)
        _check_idempotency(migration)
        _check_schema_ledger(migration)
        _check_explicit_tcp(migration)
        _check_delimiter(migration, sql_by_id.get(migration_id, ""))
        if _requires_target_preflight(migration):
            if migration_id not in target_preflight_results:
                _fail("TARGET_PREFLIGHT_RESULT_MISSING", migration_id)
            if target_preflight_results[migration_id] is not True:
                _fail("TARGET_PREFLIGHT_FAILED", migration_id)
        normalized.append(
            {
                "migrationId": migration_id,
                "file": path,
                "requiresTargetPreflight": _requires_target_preflight(migration),
            }
        )
    return {"status": "passed", "stage": "PREFLIGHTING", "migrations": normalized}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
