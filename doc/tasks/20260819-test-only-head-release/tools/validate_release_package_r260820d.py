"""Validate the frozen r260820d release package without emitting secrets."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


TAG = "release-20260820-frozen-head-test-r260820d-r1"
COMMIT = "adeb3aabc89e03d1f231552015d37bc78e0f2adb"
SUBJECT = "任务: 修复C00发布后空哈希"
PACKAGE = Path(r"E:\Int\CacheData\IntRuoyi\publish-int-ruoyi") / TAG
EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "package-provenance-r260820d-r1.json"
FRONTEND_RELEASE_INFO = Path(__file__).resolve().parents[1] / "evidence" / "frontend-release-info-r260820d-r1.json"
MANIFEST_VALIDATION = Path(__file__).resolve().parents[1] / "evidence" / "manifest-validator-r260820d-r1.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def env_value(path: Path, key: str) -> str:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            values[name] = value
    return values.get(key, "")


def main() -> int:
    failures: list[str] = []
    manifest = read_json(PACKAGE / "manifest.json")
    legacy = read_json(PACKAGE / "release-manifest.json")
    frontend = read_json(FRONTEND_RELEASE_INFO)
    manifest_validation = read_json(MANIFEST_VALIDATION)

    source_repos = manifest.get("sourceRepos", [])
    source_repo_ok = (
        len(source_repos) == 2
        and all(repo.get("commit") == COMMIT and repo.get("dirty") is False for repo in source_repos)
    )
    change_set = manifest.get("changeSet", {})
    change_items = change_set.get("items", [])
    change_set_ok = (
        change_set.get("summary") == SUBJECT
        and any(COMMIT[:12] in item and SUBJECT in item for item in change_items)
    )
    frontend_ok = (
        frontend.get("releaseTag") == TAG
        and frontend.get("packageId") == TAG
        and frontend.get("publishScope") == "code-only"
        and frontend.get("sourceRepos") == source_repos
        and frontend.get("changeSet") == change_set
    )
    tar = PACKAGE / f"intruoyi-images_{TAG}.tar"
    tar_sha256 = hashlib.sha256(tar.read_bytes()).hexdigest() if tar.exists() else ""
    declared_tar = next(
        (
            item
            for item in manifest.get("artifacts", [])
            if item.get("path") == tar.name
        ),
        None,
    )
    tar_ok = declared_tar is not None and declared_tar.get("sha256") == f"sha256:{tar_sha256}"

    test_endpoint = env_value(PACKAGE / "runtime-env" / "test.env", "EDHR_S3_ENDPOINT")
    prod_endpoint = env_value(PACKAGE / "runtime-env" / "prod.env", "EDHR_S3_ENDPOINT")
    backup_endpoint = env_value(PACKAGE / "runtime-env" / "backup.env", "EDHR_S3_ENDPOINT")
    runtime_env_ok = (
        test_endpoint == "http://172.30.30.58:9000"
        and prod_endpoint == ""
        and backup_endpoint == ""
    )

    checks = {
        "manifestValidatorPassed": manifest_validation.get("status") == "passed"
        and manifest_validation.get("code") == "MANIFEST_VALIDATION_PASSED",
        "manifestTagMatches": manifest.get("packageId") == TAG and manifest.get("releaseTag") == TAG,
        "legacyManifestMatches": legacy.get("releaseTag") == TAG
        and legacy.get("gitCommit") == COMMIT
        and legacy.get("publishScope") == "code-only"
        and legacy.get("component") == "intruoyi",
        "sourceReposFrozenAndClean": source_repo_ok,
        "changeSetBoundToCommit": change_set_ok,
        "frontendReleaseInfoMatches": frontend_ok,
        "imageArchiveDeclaredAndHashed": tar_ok,
        "runtimeEnvironmentBoundary": runtime_env_ok,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(name)

    evidence = {
        "status": "passed" if not failures else "failed",
        "releaseTag": TAG,
        "packagePath": str(PACKAGE),
        "frozenCommit": COMMIT,
        "changeSummary": SUBJECT,
        "checks": checks,
        "artifacts": {
            "imageArchive": {"path": str(tar), "sha256": tar_sha256, "bytes": tar.stat().st_size},
            "requiredSqlCount": len(list((PACKAGE / "required-sql").glob("*.sql"))),
        },
        "runtimeEnvironment": {
            "testEdhrEndpoint": test_endpoint,
            "prodEdhrEndpointConfigured": bool(prod_endpoint),
            "backupEdhrEndpointConfigured": bool(backup_endpoint),
        },
        "failures": failures,
    }
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
