from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


BLOCKED_ACTIONS = {
    "BLOCKED_CHECKSUM_MISMATCH",
    "BLOCKED_ENV_NOT_ALLOWED",
    "BLOCKED_DEPENDENCY_MISSING",
    "BLOCKED_PREREQUISITE_MISSING",
}


def _state_for(target_state: dict[str, dict[str, object]], migration_id: str) -> dict[str, object] | None:
    value = target_state.get(migration_id)
    return value if isinstance(value, dict) else None


def _dependency_satisfied(target_state: dict[str, dict[str, object]], dependency: str) -> bool:
    state = _state_for(target_state, dependency)
    return bool(state and state.get("status") == "APPLIED")


def _item(migration: dict[str, object], action: str, reason: str) -> dict[str, object]:
    return {
        "migrationId": migration["migrationId"],
        "file": migration.get("file"),
        "sha256": migration.get("sha256"),
        "action": action,
        "reason": reason,
    }


def build_preflight_plan(
    migrations: list[dict[str, object]],
    target_state: dict[str, dict[str, object]],
    *,
    target_environment: str,
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for migration in migrations:
        migration_id = str(migration["migrationId"])
        allowed = [str(item) for item in migration.get("allowedEnvironments", [])]
        if target_environment not in allowed:
            items.append(_item(migration, "BLOCKED_ENV_NOT_ALLOWED", f"{target_environment} is not allowed"))
            continue

        state = _state_for(target_state, migration_id)
        if state and state.get("status") == "APPLIED":
            accepted_checksums = {str(migration.get("sha256"))}
            accepted_checksums.update(str(item) for item in migration.get("equivalentSha256", []))
            if str(state.get("sha256")) in accepted_checksums:
                items.append(_item(migration, "SKIP_ALREADY_APPLIED", "migration already applied with matching checksum"))
            else:
                items.append(_item(migration, "APPLY", "target checksum differs from manifest; reapply current required SQL"))
            continue

        missing_dependencies = [
            str(dependency)
            for dependency in migration.get("dependsOn", [])
            if not _dependency_satisfied(target_state, str(dependency))
        ]
        if missing_dependencies:
            items.append(
                _item(
                    migration,
                    "BLOCKED_DEPENDENCY_MISSING",
                    "missing applied dependencies: " + ", ".join(missing_dependencies),
                )
            )
            continue

        items.append(_item(migration, "APPLY", "migration is pending and prerequisites are satisfied"))

    return {
        "status": "blocked" if any(item["action"] in BLOCKED_ACTIONS for item in items) else "passed",
        "targetEnvironment": target_environment,
        "items": items,
    }


def _normalize_sha256(value: object) -> str:
    text = str(value or "")
    return text.removeprefix("sha256:")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sql_without_release_metadata(value: bytes) -> bytes:
    return b"".join(
        line
        for line in value.splitlines(keepends=True)
        if not line.lstrip().startswith(b"-- release-migration:")
    )


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_migrations(manifest: object) -> list[dict[str, object]]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    database = manifest.get("database")
    if isinstance(database, dict) and "schemaMigrations" in database:
        migrations = database.get("schemaMigrations", [])
    else:
        migrations = manifest.get("schemaMigrations", manifest.get("requiredSql", []))
    if not isinstance(migrations, list):
        raise ValueError("manifest schema migrations must be an array")
    return [migration for migration in migrations if isinstance(migration, dict)]


def _normalize_target_state(raw_state: object) -> dict[str, dict[str, object]]:
    if raw_state is None:
        return {}
    if not isinstance(raw_state, dict):
        raise ValueError("target state must be a JSON object")
    normalized: dict[str, dict[str, object]] = {}
    for migration_id, state in raw_state.items():
        if isinstance(state, dict):
            normalized[str(migration_id)] = {
                "status": str(state.get("status", "")),
                "sha256": _normalize_sha256(state.get("sha256")),
            }
    return normalized


def _attach_equivalent_sql_checksums(migrations: list[dict[str, object]], manifest_path: Path) -> None:
    package_root = manifest_path.parent
    for migration in migrations:
        relative_file = migration.get("file")
        if not relative_file:
            continue
        sql_path = package_root / str(relative_file)
        if not sql_path.is_file():
            continue
        sql_bytes = sql_path.read_bytes()
        executable_bytes = _sql_without_release_metadata(sql_bytes)
        if executable_bytes == sql_bytes:
            continue
        executable_sha256 = _sha256_bytes(executable_bytes)
        if executable_sha256 != str(migration.get("sha256")):
            migration["equivalentSha256"] = [executable_sha256]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target-state", required=True)
    parser.add_argument("--target-environment", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = _load_json(manifest_path)
    target_state = _normalize_target_state(_load_json(Path(args.target_state)))
    migrations = _extract_migrations(manifest)
    for migration in migrations:
        if "sha256" in migration:
            migration["sha256"] = _normalize_sha256(migration["sha256"])
    _attach_equivalent_sql_checksums(migrations, manifest_path)

    plan = build_preflight_plan(migrations, target_state, target_environment=args.target_environment)
    Path(args.output).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
