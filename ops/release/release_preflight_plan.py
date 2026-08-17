from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from collections import defaultdict
from pathlib import Path


BLOCKED_ACTIONS = {
    "BLOCKED_CHECKSUM_MISMATCH",
    "BLOCKED_DEPENDENCY_MISSING",
    "BLOCKED_PREREQUISITE_MISSING",
    "BLOCKED_SCOPE_DEPENDENCY",
}
SKIP_ENV_NOT_ALLOWED = "SKIP_ENV_NOT_ALLOWED"
SKIP_SCOPE_EXCLUDED = "SKIP_SCOPE_EXCLUDED"
SUPPORTED_PUBLISH_SCOPES = {"code-only", "with-data"}
SUPPORTED_MIGRATION_TYPES = {"schema", "data", "menu", "config", "permission", "seed"}


def _state_for(target_state: dict[str, dict[str, object]], migration_id: str) -> dict[str, object] | None:
    value = target_state.get(migration_id)
    return value if isinstance(value, dict) else None


def _item(migration: dict[str, object], action: str, reason: str) -> dict[str, object]:
    return {
        "migrationId": migration["migrationId"],
        "file": migration.get("file"),
        "sha256": migration.get("sha256"),
        "action": action,
        "reason": reason,
    }


def _order_migrations_by_dependencies(migrations: list[dict[str, object]]) -> list[dict[str, object]]:
    migration_by_id = {str(migration["migrationId"]): migration for migration in migrations}
    original_index = {str(migration["migrationId"]): index for index, migration in enumerate(migrations)}
    indegree = {migration_id: 0 for migration_id in migration_by_id}
    edges: dict[str, list[str]] = defaultdict(list)

    for migration in migrations:
        migration_id = str(migration["migrationId"])
        for dependency in migration.get("dependsOn", []):
            dependency_id = str(dependency)
            if dependency_id not in migration_by_id:
                continue
            edges[dependency_id].append(migration_id)
            indegree[migration_id] += 1

    ready = [
        (original_index[migration_id], migration_id)
        for migration_id, degree in sorted(indegree.items(), key=lambda item: original_index[item[0]])
        if degree == 0
    ]
    heapq.heapify(ready)
    ordered_ids: list[str] = []
    while ready:
        _, migration_id = heapq.heappop(ready)
        ordered_ids.append(migration_id)
        for child_id in sorted(edges.get(migration_id, []), key=lambda item: original_index[item]):
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                heapq.heappush(ready, (original_index[child_id], child_id))

    if len(ordered_ids) != len(migrations):
        return migrations
    return [migration_by_id[migration_id] for migration_id in ordered_ids]


def build_preflight_plan(
    migrations: list[dict[str, object]],
    target_state: dict[str, dict[str, object]],
    *,
    target_environment: str,
    publish_scope: str,
) -> dict[str, object]:
    if publish_scope not in SUPPORTED_PUBLISH_SCOPES:
        raise ValueError(f"unsupported publish scope: {publish_scope}")

    items: list[dict[str, object]] = []
    ordered_migrations = _order_migrations_by_dependencies(migrations)
    known_migrations = {str(migration["migrationId"]) for migration in ordered_migrations}
    planned_actions: dict[str, str] = {}
    scope_dependency_paths: dict[str, list[str]] = {}
    satisfied_migrations = {
        migration_id
        for migration_id, state in target_state.items()
        if state.get("status") == "APPLIED" and migration_id not in known_migrations
    }
    for migration in ordered_migrations:
        migration_id = str(migration["migrationId"])
        migration_type = str(migration.get("type", "")).strip()
        if migration_type not in SUPPORTED_MIGRATION_TYPES:
            raise ValueError(f"unsupported migration type for {migration_id}: {migration_type or '<blank>'}")
        allowed = [str(item) for item in migration.get("allowedEnvironments", [])]
        if target_environment not in allowed:
            items.append(_item(migration, SKIP_ENV_NOT_ALLOWED, f"{target_environment} is not allowed"))
            planned_actions[migration_id] = SKIP_ENV_NOT_ALLOWED
            continue

        state = _state_for(target_state, migration_id)
        if state and state.get("status") == "APPLIED":
            accepted_checksums = {str(migration.get("sha256"))}
            accepted_checksums.update(str(item) for item in migration.get("equivalentSha256", []))
            if str(state.get("sha256")) in accepted_checksums:
                items.append(_item(migration, "SKIP_ALREADY_APPLIED", "migration already applied with matching checksum"))
                satisfied_migrations.add(migration_id)
                planned_actions[migration_id] = "SKIP_ALREADY_APPLIED"
                continue

        if publish_scope == "code-only" and migration_type == "data":
            items.append(_item(migration, SKIP_SCOPE_EXCLUDED, "code-only excludes pending data migration"))
            planned_actions[migration_id] = SKIP_SCOPE_EXCLUDED
            scope_dependency_paths[migration_id] = [migration_id]
            continue

        if state and state.get("status") == "APPLIED":
            items.append(_item(migration, "APPLY", "target checksum differs from manifest; reapply current required SQL"))
            satisfied_migrations.add(migration_id)
            planned_actions[migration_id] = "APPLY"
            continue

        missing_dependencies = []
        scope_dependency_path: list[str] | None = None
        for dependency in migration.get("dependsOn", []):
            dependency_id = str(dependency)
            if dependency_id in satisfied_migrations:
                continue
            if dependency_id in scope_dependency_paths:
                candidate_path = [migration_id, *scope_dependency_paths[dependency_id]]
                if scope_dependency_path is None or len(candidate_path) < len(scope_dependency_path):
                    scope_dependency_path = candidate_path
                continue
            dependency_action = planned_actions.get(dependency_id)
            if dependency_action == SKIP_ENV_NOT_ALLOWED:
                missing_dependencies.append(f"{dependency_id} (skipped for environment)")
                continue
            if dependency_action is not None:
                missing_dependencies.append(f"{dependency_id} ({dependency_action})")
                continue
            if dependency_id in known_migrations:
                missing_dependencies.append(dependency_id)
                continue
            missing_dependencies.append(dependency_id)
        if scope_dependency_path is not None:
            items.append(
                _item(
                    migration,
                    "BLOCKED_SCOPE_DEPENDENCY",
                    f"publish scope {publish_scope} excludes required dependency path: "
                    + " -> ".join(scope_dependency_path),
                )
            )
            planned_actions[migration_id] = "BLOCKED_SCOPE_DEPENDENCY"
            scope_dependency_paths[migration_id] = scope_dependency_path
            continue
        if missing_dependencies:
            items.append(
                _item(
                    migration,
                    "BLOCKED_DEPENDENCY_MISSING",
                    "missing applied dependencies: " + ", ".join(missing_dependencies),
                )
            )
            planned_actions[migration_id] = "BLOCKED_DEPENDENCY_MISSING"
            continue

        items.append(_item(migration, "APPLY", "migration is pending and prerequisites are satisfied"))
        satisfied_migrations.add(migration_id)
        planned_actions[migration_id] = "APPLY"

    return {
        "status": "blocked" if any(item["action"] in BLOCKED_ACTIONS for item in items) else "passed",
        "targetEnvironment": target_environment,
        "publishScope": publish_scope,
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
    parser.add_argument("--publish-scope", required=True, choices=sorted(SUPPORTED_PUBLISH_SCOPES))
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

    plan = build_preflight_plan(
        migrations,
        target_state,
        target_environment=args.target_environment,
        publish_scope=args.publish_scope,
    )
    Path(args.output).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
