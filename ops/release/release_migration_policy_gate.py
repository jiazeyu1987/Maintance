from __future__ import annotations

import json
from pathlib import Path

from ops.release.release_migration_manifest import (
    METADATA_PATTERN,
    MigrationManifestError,
    build_migration_manifest,
)


class MigrationPolicyError(RuntimeError):
    pass


def _load_frozen_registry(path: Path | str | None) -> dict[str, str]:
    if path is None:
        return {}
    registry_path = Path(path)
    if not registry_path.exists():
        raise MigrationPolicyError(f"frozen registry does not exist: {registry_path}")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    migrations = payload.get("migrations")
    if not isinstance(migrations, dict):
        raise MigrationPolicyError(f"frozen registry missing migrations object: {registry_path}")
    return {str(key): str(value).lower() for key, value in migrations.items()}


def _resolve_sql_paths(sql_root: Path, sql_paths: list[Path | str] | None) -> list[Path]:
    if sql_paths is None:
        return sorted(sql_root.rglob("20*.sql"), key=lambda item: item.relative_to(sql_root).as_posix())
    resolved: list[Path] = []
    for sql_path in sql_paths:
        path = Path(sql_path).resolve()
        if not path.is_file():
            raise MigrationPolicyError(f"SQL file does not exist: {path}")
        try:
            path.relative_to(sql_root)
        except ValueError as exc:
            raise MigrationPolicyError(f"SQL file is outside SQL root: {path}") from exc
        resolved.append(path)
    return sorted(resolved, key=lambda item: item.relative_to(sql_root).as_posix())


def _require_explicit_metadata(sql_root: Path, sql_paths: list[Path] | None = None) -> None:
    for path in _resolve_sql_paths(sql_root, sql_paths):
        text = path.read_text(encoding="utf-8")
        if not METADATA_PATTERN.search(text):
            raise MigrationPolicyError(f"missing release-migration metadata: {path}")


def _check_frozen_checksums(entries: list[dict[str, object]], registry: dict[str, str]) -> None:
    for entry in entries:
        migration_id = str(entry["migrationId"])
        frozen_checksum = registry.get(migration_id)
        if frozen_checksum is None:
            continue
        current_checksum = str(entry["sha256"]).lower()
        if frozen_checksum != current_checksum:
            raise MigrationPolicyError(
                f"checksum frozen violation for migrationId '{migration_id}': "
                f"registry={frozen_checksum}, current={current_checksum}"
            )


def _check_dependency_environment_contract(entries: list[dict[str, object]]) -> None:
    environments_by_id = {
        str(entry["migrationId"]): {str(environment) for environment in entry["allowedEnvironments"]}
        for entry in entries
    }
    for entry in entries:
        migration_id = str(entry["migrationId"])
        child_environments = environments_by_id[migration_id]
        for dependency in entry["dependsOn"]:
            dependency_id = str(dependency)
            dependency_environments = environments_by_id[dependency_id]
            if child_environments.issubset(dependency_environments):
                continue
            raise MigrationPolicyError(
                "allowedEnvironments must be a subset of each dependency for "
                f"migrationId '{migration_id}': dependency '{dependency_id}' allows "
                f"{sorted(dependency_environments)}, child allows {sorted(child_environments)}"
            )


def run_migration_policy_gate(
    sql_root: Path | str,
    *,
    sql_paths: list[Path | str] | None = None,
    file_prefix: str = "sql/mysql",
    frozen_registry_path: Path | str | None = None,
) -> dict[str, object]:
    root = Path(sql_root).resolve()
    paths = _resolve_sql_paths(root, sql_paths)
    _require_explicit_metadata(root, paths)
    try:
        entries = build_migration_manifest(root, sql_paths=paths, file_prefix=file_prefix)
    except MigrationManifestError as exc:
        raise MigrationPolicyError(str(exc)) from exc
    _check_dependency_environment_contract(entries)
    _check_frozen_checksums(entries, _load_frozen_registry(frozen_registry_path))
    return {
        "status": "passed",
        "migrationCount": len(entries),
        "migrations": entries,
    }
