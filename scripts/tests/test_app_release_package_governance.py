from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "ops" / "release" / "lib" / "ReleasePackageGovernance.psm1"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_package(package_dir: Path) -> None:
    package_dir.mkdir()
    (package_dir / "required-sql").mkdir()
    files = {
        "docker-compose.yml": b"services:\n",
        "required-sql/001.sql": b"SELECT 1;\n",
    }
    for relative, content in files.items():
        (package_dir / relative).write_bytes(content)
    artifacts = [
        {"path": path, "bytes": len(content), "sha256": _sha256(content)}
        for path, content in sorted(files.items())
    ]
    package_digest_input = "".join(
        f"{item['path']}\t{item['bytes']}\t{item['sha256']}\n" for item in artifacts
    ).encode("utf-8")
    manifest = {
        "schemaVersion": 2,
        "packageId": package_dir.name,
        "releaseTag": "release-p1",
        "publishScope": "app-release",
        "packageDigest": _sha256(package_digest_input),
        "sourceRoots": [
            {"rootRole": "maintenance", "normalizedRoot": "d:/release/m", "approvedCommit": "a" * 40,
             "commit": "a" * 40, "dirty": False},
            {"rootRole": "application", "normalizedRoot": "d:/release/a", "approvedCommit": "b" * 40,
             "commit": "b" * 40, "dirty": False},
        ],
        "sourceRoles": [
            {"sourceRole": "maintenance", "rootRole": "maintenance", "relativePath": ".", "commit": "a" * 40},
            {"sourceRole": "backend", "rootRole": "application", "relativePath": "IntRuoyiBackend", "commit": "b" * 40},
            {"sourceRole": "frontend", "rootRole": "application", "relativePath": "IntRuoyiFronted", "commit": "b" * 40},
        ],
        "artifacts": artifacts,
    }
    (package_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n"
    )


def _verify(package_dir: Path) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE}'",
            f"Test-ReleasePackageIntegrity -PackagePath '{package_dir}' -ExpectedReleaseTag 'release-p1' | ConvertTo-Json -Depth 8 -Compress",
        ]
    )
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_manifest_json_is_the_only_authoritative_app_release_manifest(tmp_path: Path) -> None:
    package_dir = tmp_path / "release-p1"
    _write_package(package_dir)

    result = _verify(package_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    verification = json.loads(result.stdout.strip().splitlines()[-1])
    assert verification["publishScope"] == "app-release"
    assert verification["packageDigest"] == "b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273"
    assert verification["manifestDigest"] == _sha256((package_dir / "manifest.json").read_bytes())
    assert len(verification["sourceRoots"]) == 2
    assert len(verification["sourceRoles"]) == 3


def test_manifest_schema_strictly_defines_source_roots_and_roles() -> None:
    schema = json.loads((ROOT / "ops/release/manifest-v1.schema.json").read_text(encoding="utf-8"))
    root_items = schema["properties"]["sourceRoots"]["items"]
    role_items = schema["properties"]["sourceRoles"]["items"]
    assert root_items["additionalProperties"] is False
    assert set(root_items["required"]) == {
        "rootRole", "normalizedRoot", "approvedCommit", "commit", "dirty"
    }
    assert root_items["properties"]["rootRole"]["enum"] == ["maintenance", "application"]
    assert role_items["additionalProperties"] is False
    assert set(role_items["required"]) == {"sourceRole", "rootRole", "relativePath", "commit"}
    assert role_items["properties"]["sourceRole"]["enum"] == ["maintenance", "backend", "frontend"]


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda manifest: manifest["sourceRoots"][0].__setitem__("normalizedRoot", "D:\\release\\m"),
         "MANIFEST_SOURCE_ROOT_INVALID"),
        (lambda manifest: manifest["sourceRoots"][0].__setitem__("approvedCommit", "c" * 40),
         "MANIFEST_SOURCE_ROOT_INVALID"),
        (lambda manifest: manifest["sourceRoots"][0].__setitem__("dirty", True),
         "MANIFEST_SOURCE_ROOT_INVALID"),
        (lambda manifest: manifest["sourceRoles"][0].__setitem__("rootRole", "application"),
         "MANIFEST_SOURCE_ROLE_INVALID"),
        (lambda manifest: manifest["sourceRoles"][1].__setitem__("relativePath", "backend"),
         "MANIFEST_SOURCE_ROLE_INVALID"),
        (lambda manifest: manifest["sourceRoles"][2].__setitem__("commit", "c" * 40),
         "MANIFEST_SOURCE_ROLE_INVALID"),
    ],
)
def test_manifest_source_evidence_tampering_is_rejected(
    tmp_path: Path, mutation, error_code: str
) -> None:
    package_dir = tmp_path / "release-p1"
    _write_package(package_dir)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    mutation(manifest)
    (package_dir / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    result = _verify(package_dir)

    assert result.returncode != 0
    assert error_code in result.stdout + result.stderr


@pytest.mark.parametrize("forbidden_path", [
    "release-manifest.json",
    "ruoyi-vue-pro-current.sql",
    "reset-db.sql",
    "post-import.sql",
    "manifest/dcc-object-inventory.json",
    "minio/yudao/object.bin",
    ".env",
    "runtime/data.bin",
])
def test_app_release_rejects_data_secret_and_second_manifest_files(
    tmp_path: Path, forbidden_path: str
) -> None:
    package_dir = tmp_path / "release-p1"
    _write_package(package_dir)
    target = package_dir / forbidden_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"forbidden")

    result = _verify(package_dir)

    assert result.returncode != 0
    assert "PACKAGE_CONTENT_FORBIDDEN" in result.stdout + result.stderr


def test_backslash_path_is_rejected(tmp_path: Path) -> None:
    package_dir = tmp_path / "release-p1"
    _write_package(package_dir)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = "required-sql\\001.sql"
    (package_dir / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    result = _verify(package_dir)

    assert result.returncode != 0
    assert "PACKAGE_PATH_INVALID" in result.stdout + result.stderr


def test_case_fold_collision_is_rejected(tmp_path: Path) -> None:
    package_dir = tmp_path / "release-p1"
    _write_package(package_dir)
    (package_dir / "A").mkdir()
    (package_dir / "A" / "file.txt").write_bytes(b"one")
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"].extend([
        {"path": "A/file.txt", "bytes": 3, "sha256": _sha256(b"one")},
        {"path": "a/file.txt", "bytes": 3, "sha256": _sha256(b"one")},
    ])
    (package_dir / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    result = _verify(package_dir)

    assert result.returncode != 0
    assert "PACKAGE_PATH_INVALID" in result.stdout + result.stderr
