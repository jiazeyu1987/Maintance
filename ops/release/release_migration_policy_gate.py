from __future__ import annotations

import json
from pathlib import Path

from script.release.release_migration_manifest import (
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


def _require_explicit_metadata(sql_root: Path) -> None:
    for path in sorted(sql_root.rglob("20*.sql"), key=lambda item: item.relative_to(sql_root).as_posix()):
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


def run_migration_policy_gate(
    sql_root: Path | str,
    *,
    frozen_registry_path: Path | str | None = None,
) -> dict[str, object]:
    root = Path(sql_root).resolve()
    _require_explicit_metadata(root)
    try:
        entries = build_migration_manifest(root)
    except MigrationManifestError as exc:
        raise MigrationPolicyError(str(exc)) from exc
    _check_frozen_checksums(entries, _load_frozen_registry(frozen_registry_path))
    return {
        "status": "passed",
        "migrationCount": len(entries),
        "migrations": entries,
    }
