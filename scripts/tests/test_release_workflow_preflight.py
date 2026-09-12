from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def _function(source: str, name: str, next_name: str) -> str:
    start = source.index(f"function {name}")
    end = source.index(f"function {next_name}", start)
    return source[start:end]


def test_standard_workflow_is_fixed_to_app_release_without_data() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    scope = _function(source, "Resolve-EffectiveBuildReleasePublishScope", "Set-ReleasePackageArtifactCache")

    assert "[ValidateSet('app-release')]" in source
    assert "[string]$PublishScope = 'app-release'" in source
    assert "return 'app-release'" in scope
    assert "with-data" not in scope
    assert "$script:SkipDatabaseSync = $true" in scope
    assert "$script:SkipMinioSync = $true" in scope


def test_tests_and_source_freeze_run_before_expensive_builds() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    tests = _function(source, "Invoke-StandardReleaseContractTests", "Get-ReleaseSchemaDigest")

    assert tests.index("backend contract tests") < tests.index("frontend contract tests")
    assert tests.index("frontend contract tests") < tests.index("release script tests")
    assert "-Dsurefire.failIfNoSpecifiedTests=false" in tests
    parent_create = tests.index("New-Item -ItemType Directory -Force -Path $pytestParent")
    pytest_invoke = tests.index("'-X', 'utf8', '-m', 'pytest'")
    assert parent_create < pytest_invoke

    first_freeze = source.index("Assert-ReleaseSourceFreeze -VerificationPoint 'before-build'")
    required_tests = source.index("Invoke-StandardReleaseContractTests", first_freeze)
    maven_build = source.index("Info 'Building backend jar'")
    frontend_build = source.index('Info "Building frontend static assets')
    docker_build = source.index("Info 'Building backend image'")
    second_freeze = source.index("Assert-ReleaseSourceFreeze -VerificationPoint 'before-package'")
    manifest = source.index("Write-ReleaseManifest -PackageTag $ReleaseTag", second_freeze)

    assert first_freeze < required_tests < min(maven_build, frontend_build, docker_build)
    assert second_freeze < manifest


def test_freeze_evidence_has_two_git_roots_and_three_source_roles() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    freeze = _function(source, "Assert-ReleaseSourceFreeze", "Invoke-StandardReleaseContractTests")

    for root_role in ("maintenance", "application"):
        assert f"rootRole = '{root_role}'" in freeze
    for source_role in ("maintenance", "backend", "frontend"):
        assert f"sourceRole = '{source_role}'" in freeze
    assert "SOURCE_HEAD_DRIFT" in freeze
    assert "SOURCE_DIRTY" in freeze
    assert "SOURCE_ROOT_PATH_DRIFT" in freeze
    assert "SOURCE_ROLE_ROOT_DRIFT" in freeze
    assert "SOURCE_ROLE_PATH_DRIFT" in freeze
    assert "SOURCE_ROLE_COMMIT_DRIFT" in freeze
    assert "expectedRoot.normalizedRoot" in freeze
    assert "ExpectedEvidence.sourceRoles" in freeze


def test_standard_workflow_uses_only_authoritative_manifest_json() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")

    assert "Write-ReleaseManifestV1" not in source
    assert "Read-NasReleaseManifestForCompatibility" not in source
    assert "release-manifest.json" not in source
    assert "packageDigest" in source
    assert "sourceRoots" in source
    assert "sourceRoles" in source


def test_nas_download_purges_stale_cache_before_integrity_check() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    copy_helper = _function(source, "Copy-ReleasePackageDirectory", "Resolve-LocalCacheRoot")
    download = _function(source, "Copy-ReleasePackageFromNas", "Get-RequiredJsonPropertyValue")

    assert "'/PURGE'" in copy_helper
    assert " /PURGE" in copy_helper
    copy = download.index("Copy-ReleasePackageDirectory -SourceDirectory $sourcePath -DestinationDirectory $releaseDir")
    integrity = download.index("Test-ReleasePackageIntegrity -PackagePath $releaseDir")
    assert copy < integrity


def test_app_release_build_does_not_write_edhr_storage_probe() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    call = "Invoke-EdhrStorageRetentionVerifier -BackendRepo $backendRepo"

    call_index = source.index(call)
    guard_index = source.rfind("if ($publishBackend -and $Mode -ne 'build-release')", 0, call_index)
    assert guard_index >= 0
    assert call_index - guard_index < 400
