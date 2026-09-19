import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any


PACKAGE = pathlib.Path(r"E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260820-frozen-head-test-r260820a-r2")
TASK_DIR = pathlib.Path(r"D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260819-test-only-head-release")
OUT = TASK_DIR / "manifest-validation-r260820a-r2.json"
EXPECTED_TAG = "release-20260820-frozen-head-test-r260820a-r2"
EXPECTED_APP_COMMIT = "adeb3aabc89e03d1f231552015d37bc78e0f2adb"
EXPECTED_SUBJECT = "任务: 修复C00发布后空哈希"
TEST_HOST = "172.30.30.58"
FORBIDDEN_HOSTS = ["172.30.30.57", "172.30.30.59"]


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_env(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def docker_stdout(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, stdout, stderr


def sanitize_env(env: dict[str, str]) -> dict[str, Any]:
    keys = [
        "IMAGE_TAG",
        "EDHR_S3_ENDPOINT",
        "EDHR_S3_BUCKET",
        "EDHR_S3_TEST_ENDPOINT",
        "EDHR_S3_TEST_BUCKET",
        "EDHR_S3_ACCESS_KEY",
        "EDHR_S3_SECRET_KEY",
        "EDHR_S3_TEST_ACCESS_KEY",
        "EDHR_S3_TEST_SECRET_KEY",
    ]
    summary: dict[str, Any] = {}
    for key in keys:
        value = env.get(key)
        if value is None:
            summary[key] = None
        elif re.search(r"(SECRET|PASSWORD|ACCESS_KEY|TOKEN)", key):
            summary[key] = {"present": bool(value), "length": len(value)}
        else:
            summary[key] = value
    return summary


def main() -> int:
    manifest_path = PACKAGE / "manifest.json"
    legacy_path = PACKAGE / "release-manifest.json"
    root_env_path = PACKAGE / ".env"
    env_path = PACKAGE / "runtime-env" / "test.env"
    result: dict[str, Any] = {
        "package": str(PACKAGE),
        "releaseTag": EXPECTED_TAG,
        "expectedAppCommit": EXPECTED_APP_COMMIT,
        "expectedSubject": EXPECTED_SUBJECT,
        "checks": {},
        "issues": [],
    }

    manifest = read_json(manifest_path)
    legacy = read_json(legacy_path)
    root_env = parse_env(root_env_path)
    env = parse_env(env_path)

    source_repos = manifest.get("sourceRepos") or []
    repo_checks = []
    for repo in source_repos:
        repo_checks.append(
            {
                "name": repo.get("name"),
                "pathRole": repo.get("pathRole"),
                "commit": repo.get("commit"),
                "dirty": repo.get("dirty"),
                "commitMatches": repo.get("commit") == EXPECTED_APP_COMMIT,
                "dirtyOk": repo.get("dirty") is False,
            }
        )

    artifact_checks = []
    for artifact in manifest.get("artifacts") or []:
        rel = artifact.get("path") or artifact.get("relativePath") or artifact.get("file")
        path = PACKAGE / rel if rel else None
        exists = bool(path and path.exists())
        actual_size = path.stat().st_size if exists and path else None
        actual_hash = sha256(path) if exists and path else None
        expected_hash = str(artifact.get("sha256") or artifact.get("hash") or "").removeprefix("sha256:").lower()
        artifact_checks.append(
            {
                "path": rel,
                "exists": exists,
                "sizeBytes": actual_size,
                "expectedSizeBytes": artifact.get("sizeBytes"),
                "sizeMatches": actual_size == artifact.get("sizeBytes") if artifact.get("sizeBytes") is not None else None,
                "sha256Prefix": actual_hash[:16] if actual_hash else None,
                "sha256Matches": actual_hash == expected_hash if expected_hash else None,
            }
        )

    backend_image = f"intruoyi-backend:{EXPECTED_TAG}"
    frontend_image = f"intruoyi-frontend:{EXPECTED_TAG}"
    docker_checks: dict[str, Any] = {}
    for image in [backend_image, frontend_image]:
        code, stdout, stderr = docker_stdout(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
        docker_checks[image] = {
            "inspectExitCode": code,
            "imageIdPrefix": stdout.strip()[:32],
            "stderr": stderr.strip()[:300],
        }

    release_info: dict[str, Any] | None = None
    code, stdout, stderr = docker_stdout(
        ["docker", "run", "--rm", "--entrypoint", "cat", frontend_image, "/usr/share/nginx/html/release-info.json"]
    )
    docker_checks["frontendReleaseInfo"] = {
        "catExitCode": code,
        "stderr": stderr.strip()[:300],
    }
    if code == 0:
        release_info = json.loads(stdout)

    combined_env_values = "\n".join(list(root_env.values()) + list(env.values()))
    edhr_env_values = "\n".join(
        value for key, value in {**root_env, **env}.items() if key.startswith("EDHR_")
    )
    result["checks"] = {
        "manifestExists": manifest_path.exists(),
        "legacyExists": legacy_path.exists(),
        "rootEnvExists": root_env_path.exists(),
        "runtimeEnvExists": env_path.exists(),
        "manifestReleaseTagMatches": manifest.get("releaseTag") == EXPECTED_TAG,
        "manifestPublishScope": manifest.get("publishScope"),
        "manifestPackageId": manifest.get("packageId"),
        "sourceRepos": repo_checks,
        "changeSet": manifest.get("changeSet"),
        "changeSetContainsSubject": EXPECTED_SUBJECT in json.dumps(manifest.get("changeSet"), ensure_ascii=False),
        "changeSetContainsCommit": EXPECTED_APP_COMMIT[:12] in json.dumps(manifest.get("changeSet"), ensure_ascii=False),
        "legacy": {
            "releaseTag": legacy.get("releaseTag"),
            "gitCommit": legacy.get("gitCommit"),
            "component": legacy.get("component"),
            "publishScope": legacy.get("publishScope"),
            "releaseTagMatches": legacy.get("releaseTag") == EXPECTED_TAG,
            "gitCommitMatches": legacy.get("gitCommit") == EXPECTED_APP_COMMIT,
        },
        "artifacts": artifact_checks,
        "runtimeEnv": {
            "rootSummary": sanitize_env(root_env),
            "summary": sanitize_env(env),
            "rootImageTagMatches": root_env.get("IMAGE_TAG") == EXPECTED_TAG,
            "containsTestHost": TEST_HOST in combined_env_values,
            "edhrContainsTestHost": TEST_HOST in edhr_env_values,
            "edhrContainsForbiddenHosts": {host: host in edhr_env_values for host in FORBIDDEN_HOSTS},
            "nonEdhrForbiddenHostKeys": [
                key for key, value in {**root_env, **env}.items()
                if any(host in value for host in FORBIDDEN_HOSTS) and not key.startswith("EDHR_")
            ],
        },
        "docker": docker_checks,
        "frontendReleaseInfo": {
            "releaseTag": release_info.get("releaseTag") if release_info else None,
            "packageId": release_info.get("packageId") if release_info else None,
            "sourceRepos": release_info.get("sourceRepos") if release_info else None,
            "changeSet": release_info.get("changeSet") if release_info else None,
            "releaseTagMatches": release_info.get("releaseTag") == EXPECTED_TAG if release_info else False,
            "changeSetContainsSubject": EXPECTED_SUBJECT in json.dumps(release_info.get("changeSet"), ensure_ascii=False) if release_info else False,
            "sourceReposMatch": all((repo.get("commit") == EXPECTED_APP_COMMIT and repo.get("dirty") is False) for repo in release_info.get("sourceRepos", [])) if release_info else False,
        },
    }

    if not result["checks"]["manifestReleaseTagMatches"]:
        result["issues"].append("manifest releaseTag mismatch")
    if manifest.get("publishScope") != "code-only":
        result["issues"].append("manifest publishScope is not code-only")
    if not all(item["commitMatches"] and item["dirtyOk"] for item in repo_checks):
        result["issues"].append("sourceRepos commit/dirty check failed")
    if not result["checks"]["changeSetContainsSubject"]:
        result["issues"].append("manifest changeSet missing expected UTF-8 subject")
    if not result["checks"]["changeSetContainsCommit"]:
        result["issues"].append("manifest changeSet missing expected short commit")
    if not result["checks"]["legacy"]["releaseTagMatches"] or not result["checks"]["legacy"]["gitCommitMatches"]:
        result["issues"].append("legacy manifest mismatch")
    if not all(item["exists"] and item["sha256Matches"] is not False and item["sizeMatches"] is not False for item in artifact_checks):
        result["issues"].append("artifact existence/hash/size check failed")
    env_check = result["checks"]["runtimeEnv"]
    if (
        not env_check["rootImageTagMatches"]
        or not env_check["edhrContainsTestHost"]
        or any(env_check["edhrContainsForbiddenHosts"].values())
    ):
        result["issues"].append("test runtime env boundary failed")
    if any(item["inspectExitCode"] != 0 for key, item in docker_checks.items() if key != "frontendReleaseInfo"):
        result["issues"].append("local docker image inspect failed")
    if not result["checks"]["frontendReleaseInfo"]["releaseTagMatches"]:
        result["issues"].append("frontend image release-info releaseTag mismatch")
    if not result["checks"]["frontendReleaseInfo"]["changeSetContainsSubject"]:
        result["issues"].append("frontend image release-info missing expected UTF-8 subject")
    if not result["checks"]["frontendReleaseInfo"]["sourceReposMatch"]:
        result["issues"].append("frontend image release-info sourceRepos mismatch")

    result["passed"] = not result["issues"]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "issues": result["issues"], "evidence": str(OUT)}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
