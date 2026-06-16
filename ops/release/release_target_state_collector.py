from __future__ import annotations

import hashlib
import json
from pathlib import Path


class TargetStateCollectionError(RuntimeError):
    pass


def _read_required_text(path: Path, name: str) -> str:
    if not path.exists():
        raise TargetStateCollectionError(f"missing {name}: {path}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise TargetStateCollectionError(f"empty {name}: {path}")
    return value


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, name: str) -> dict[str, object]:
    if not path.exists():
        raise TargetStateCollectionError(f"missing {name}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def collect_target_state(target_root: Path | str) -> dict[str, object]:
    root = Path(target_root).resolve()
    release_tag = _read_required_text(root / "release-tag.txt", "releaseTag")
    migration_payload = _read_json(root / "migration-state.json", "migration-state.json")
    images = _read_json(root / "images.json", "images.json")
    compose_hash = _sha256(root / "docker-compose.yml")
    env_hash = _sha256(root / ".env")

    migrations: dict[str, dict[str, object]] = {}
    for item in migration_payload.get("migrations", []):
        migration_id = str(item.get("migrationId", "")).strip()
        if not migration_id:
            raise TargetStateCollectionError("migration-state.json contains migration without migrationId")
        migrations[migration_id] = dict(item)

    ops_dir = root / "ops"
    if not ops_dir.exists():
        raise TargetStateCollectionError(f"missing ops script directory: {ops_dir}")
    ops_scripts = {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(ops_dir.rglob("*"))
        if path.is_file()
    }
    if not ops_scripts:
        raise TargetStateCollectionError(f"missing ops scripts under: {ops_dir}")

    return {
        "status": "collected",
        "releaseTag": release_tag,
        "migrations": migrations,
        "images": images,
        "opsScripts": ops_scripts,
        "composeHash": compose_hash,
        "envHash": env_hash,
    }
