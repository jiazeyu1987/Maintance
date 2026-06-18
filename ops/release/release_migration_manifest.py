from __future__ import annotations

import hashlib
import re
from pathlib import Path


class MigrationManifestError(RuntimeError):
    pass


ALLOWED_ENVIRONMENTS = {"test", "backup", "prod"}
ALLOWED_TYPES = {"schema", "data", "menu", "config", "permission", "seed"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
DEFAULT_ALLOWED_ENVIRONMENTS = ["test", "backup", "prod"]
DEFAULT_TYPE = "schema"
DEFAULT_RISK_LEVEL = "medium"
METADATA_PATTERN = re.compile(r"^\s*--\s*release-migration\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migration_id(path: Path) -> str:
    return path.stem


def _relative_file(sql_root: Path, path: Path, file_prefix: str = "sql/mysql") -> str:
    relative = path.relative_to(sql_root).as_posix()
    return f"{file_prefix.rstrip('/')}/{relative}"


def _parse_metadata(path: Path) -> dict[str, list[str] | str]:
    text = path.read_text(encoding="utf-8")
    match = METADATA_PATTERN.search(text)
    if not match:
        return {
            "allowedEnvironments": DEFAULT_ALLOWED_ENVIRONMENTS,
            "dependsOn": [],
            "type": DEFAULT_TYPE,
            "riskLevel": DEFAULT_RISK_LEVEL,
        }

    metadata: dict[str, list[str] | str] = {
        "allowedEnvironments": DEFAULT_ALLOWED_ENVIRONMENTS,
        "dependsOn": [],
        "type": DEFAULT_TYPE,
        "riskLevel": DEFAULT_RISK_LEVEL,
    }
    for segment in match.group(1).split(";"):
        if not segment.strip():
            continue
        if "=" not in segment:
            raise MigrationManifestError(f"invalid release-migration metadata in {path}: {segment.strip()}")
        key, value = [part.strip() for part in segment.split("=", 1)]
        values = [item.strip() for item in value.split(",") if item.strip()]
        if key == "allowedEnvironments":
            if not values:
                raise MigrationManifestError(f"allowedEnvironments is empty in {path}")
            invalid = [item for item in values if item not in ALLOWED_ENVIRONMENTS]
            if invalid:
                raise MigrationManifestError(f"invalid allowedEnvironments in {path}: {', '.join(invalid)}")
            metadata[key] = values
        elif key == "dependsOn":
            metadata[key] = values
        elif key == "type":
            if len(values) != 1 or values[0] not in ALLOWED_TYPES:
                raise MigrationManifestError(f"invalid type in {path}: {value}")
            metadata[key] = values[0]
        elif key == "riskLevel":
            if len(values) != 1 or values[0] not in ALLOWED_RISK_LEVELS:
                raise MigrationManifestError(f"invalid riskLevel in {path}: {value}")
            metadata[key] = values[0]
        else:
            raise MigrationManifestError(f"unknown release-migration metadata key in {path}: {key}")
    return metadata


def build_migration_manifest(
    sql_root: Path | str,
    *,
    sql_paths: list[Path | str] | None = None,
    file_prefix: str = "sql/mysql",
) -> list[dict[str, object]]:
    root = Path(sql_root).resolve()
    if not root.exists():
        raise MigrationManifestError(f"SQL root does not exist: {root}")
    if not root.is_dir():
        raise MigrationManifestError(f"SQL root is not a directory: {root}")

    entries: list[dict[str, object]] = []
    seen: dict[str, Path] = {}
    if sql_paths is None:
        paths = sorted(root.rglob("20*.sql"), key=lambda item: item.relative_to(root).as_posix())
    else:
        paths = []
        for sql_path in sql_paths:
            path = Path(sql_path).resolve()
            if not path.is_file():
                raise MigrationManifestError(f"SQL file does not exist: {path}")
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise MigrationManifestError(f"SQL file is outside SQL root: {path}") from exc
            paths.append(path)
        paths = sorted(paths, key=lambda item: item.relative_to(root).as_posix())

    for path in paths:
        migration_id = _migration_id(path)
        if migration_id in seen:
            raise MigrationManifestError(f"duplicate migrationId '{migration_id}': {seen[migration_id]} and {path}")
        seen[migration_id] = path
        metadata = _parse_metadata(path)
        entries.append(
            {
                "migrationId": migration_id,
                "file": _relative_file(root, path, file_prefix),
                "sha256": _sha256(path),
                "type": metadata["type"],
                "allowedEnvironments": metadata["allowedEnvironments"],
                "dependsOn": metadata["dependsOn"],
                "riskLevel": metadata["riskLevel"],
            }
        )

    known_ids = {entry["migrationId"] for entry in entries}
    for entry in entries:
        for dependency in entry["dependsOn"]:
            if dependency not in known_ids:
                raise MigrationManifestError(
                    f"dependsOn missing migration '{dependency}' for migrationId '{entry['migrationId']}'"
                )
    return entries
