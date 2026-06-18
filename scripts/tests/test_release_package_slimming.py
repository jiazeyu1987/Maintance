import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def _script_text() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def test_build_release_removes_docker_build_context_before_manifest_and_upload() -> None:
    script = _script_text()

    assert "function Remove-ReleaseDockerBuildContextFromPackage" in script
    assert "$dockerBuildContextRoot = Join-Path $releaseDir 'docker-build-context'" in script

    cleanup_call = re.search(r"(?m)^\s*Remove-ReleaseDockerBuildContextFromPackage\s*$", script)
    assert cleanup_call is not None
    manifest_call = script.index("Write-ReleaseManifest -PackageTag $ReleaseTag")
    upload_call = script.index("Copy-ReleasePackageToNas -PackageTag $ReleaseTag")

    assert cleanup_call.start() < manifest_call
    assert cleanup_call.start() < upload_call


def test_release_manifest_artifact_scan_fails_if_docker_build_context_remains() -> None:
    script = _script_text()

    assert "'docker-build-context'" in script
    assert "Release package still contains docker-build-context" in script
