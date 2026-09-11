"""Local deployment transaction primitive used by isolated release tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeploymentError(RuntimeError):
    code: str
    stage: str
    tag_retired: bool

    def __str__(self) -> str:
        return f"{self.code} / {self.stage}"


def execute_env_transaction(
    root: Path,
    *,
    new_env: str,
    new_images: dict[str, str],
    apply: callable,
    verify: callable,
) -> dict[str, object]:
    """Switch .env and actual images atomically; restore both on any verify error."""

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    env_path = root / ".env"
    images_path = root / "actual-images.json"
    old_env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    old_images = json.loads(images_path.read_text(encoding="utf-8")) if images_path.exists() else {}
    next_path = root / ".env.next"
    next_path.write_text(new_env, encoding="utf-8")
    try:
        next_path.replace(env_path)
        images_path.write_text(json.dumps(new_images, sort_keys=True), encoding="utf-8")
        apply()
        verify()
        return {"status": "SUCCESS", "stage": "VERIFYING_TEST"}
    except Exception as exc:
        env_path.write_text(old_env, encoding="utf-8")
        images_path.write_text(json.dumps(old_images, sort_keys=True), encoding="utf-8")
        raise DeploymentError("DEPLOYMENT_FAILED", "VERIFYING_TEST", True) from exc
    finally:
        if next_path.exists():
            next_path.unlink()
