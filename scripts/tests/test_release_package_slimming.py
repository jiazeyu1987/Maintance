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


def test_build_context_prepares_backend_exec_jar_and_fail_fast_checks() -> None:
    script = _script_text()

    assert "function New-ReleaseDockerBuildContext" in script
    assert "$backendJarTargetPath = Join-Path $backendJarTargetDir 'yudao-server-exec.jar'" in script
    assert "[System.IO.File]::Copy($BackendJarPath, $backendJarTargetPath, $true)" in script
    assert "Backend exec jar missing from Docker build context:" in script
    assert "Backend exec jar missing from Docker build context after preparation:" in script


def test_release_change_set_manifest_uses_unicode_safe_labels() -> None:
    script = _script_text()

    assert "function ConvertTo-ReleaseUnicodeText" in script
    assert "$releasePackageLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(21457, 24067, 21253)" in script
    assert "$componentScopeLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(32452, 20214, 33539, 22260)" in script
    assert '${releasePackageLabel}：$PackageTag' in script
    assert '${componentScopeLabel}：$Component' in script
    assert '"发布包：$PackageTag"' not in script
    assert '"组件范围：$Component"' not in script
