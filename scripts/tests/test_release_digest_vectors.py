from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "ops" / "release" / "release_digest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_digest", MODULE_PATH)
    assert spec is not None and spec.loader is not None, "release_digest.py is missing"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_double_digest_matches_fixed_vector() -> None:
    digest = _load_module()
    result = digest.calculate_package_digest(
        [
            digest.ArtifactBytes("required-sql/001.sql", b"SELECT 1;\n"),
            digest.ArtifactBytes("docker-compose.yml", b"services:\n"),
        ]
    )

    assert [item.path for item in result.artifacts] == ["docker-compose.yml", "required-sql/001.sql"]
    assert result.artifacts[0].sha256 == "fa73fccdc99ea835967c7dee7efbed1f3ca87260d92931850fdd66da8cb12f1d"
    assert result.artifacts[1].sha256 == "b4e0497804e46e0a0b0b8c31975b062152d551bac49c3c2e80932567b4085dcd"
    assert result.package_digest == "b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273"
    manifest = b'{"schemaVersion":2,"packageDigest":"b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273"}\n'
    assert digest.calculate_manifest_digest(manifest) == "bb44ed6ea9550e067c1a2af3a105a0989503b046646f26bd1bac19455bee2800"


@pytest.mark.parametrize("paths", [["required-sql\\001.sql"], ["A/file.txt", "a/file.txt"]])
def test_python_rejects_backslashes_and_case_folded_collisions(paths: list[str]) -> None:
    digest = _load_module()
    with pytest.raises(digest.PackagePathError, match="PACKAGE_PATH_INVALID"):
        digest.calculate_package_digest([digest.ArtifactBytes(path, b"x") for path in paths])
