from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def test_release_bootstrap_emits_utf8_even_with_legacy_console_encoding() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    bootstrap = source[source.index("$ErrorActionPreference = 'Stop'"):source.index("Import-Module -Force")]
    command = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(936); "
        + bootstrap
        + "\n$text = [string][char]0x4e2d + [char]0x6587; "
        + "[Console]::WriteLine($text); [Console]::Error.WriteLine($text)"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, check=True, timeout=30,
    )
    assert result.stdout.decode("utf-8").strip() == "\u4e2d\u6587"
    assert result.stderr.decode("utf-8").strip() == "\u4e2d\u6587"


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
    assert tests.index("frontend contract tests") < tests.index("Discovering application migration tests")
    assert tests.index("Discovering application migration tests") < tests.index("release script tests")
    assert "-Dsurefire.failIfNoSpecifiedTests=false" in tests
    application_parent_create = tests.index("New-Item -ItemType Directory -Force -Path $applicationPytestParent")
    application_pytest = tests.index("'-X', 'utf8', '-m', 'pytest'", tests.index("Discovering application migration tests"))
    assert application_parent_create < application_pytest
    script_test_start = tests.index("release script tests")
    parent_create = tests.index("New-Item -ItemType Directory -Force -Path $pytestParent", script_test_start)
    pytest_invoke = tests.index("'-X', 'utf8', '-m', 'pytest'", script_test_start)
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


def test_build_release_emits_workflow_stage_markers_before_test_and_build_blocks() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")

    assert "function Write-ReleaseWorkflowStage" in source
    assert "RELEASE_WORKFLOW_STAGE=$State" in source
    testing_marker = source.index("Write-ReleaseWorkflowStage -State 'TESTING'")
    backend_contract = source.index("Info 'Running backend contract tests'")
    building_marker = source.index("Write-ReleaseWorkflowStage -State 'BUILDING'")
    backend_build = source.index("Info 'Building backend jar'")
    frontend_build = source.index('Info "Building frontend static assets')
    docker_build = source.index("Info 'Building backend image'")

    assert testing_marker < backend_contract
    assert backend_contract < building_marker
    assert building_marker < min(backend_build, frontend_build, docker_build)


def test_build_release_validates_nas_config_and_clean_sources_before_sql_scan() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")

    main_nas_preflight = source.index("$null = Read-NasReleaseConfig")
    first_freeze = source.index("Assert-ReleaseSourceFreeze -VerificationPoint 'before-build'")
    migration_scan = source.index("$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts")
    migration_policy_gate = source.index("Invoke-ReleaseMigrationPolicyGate", migration_scan)
    contract_tests = source.index("Invoke-StandardReleaseContractTests", migration_policy_gate)
    maven_build = source.index("Info 'Building backend jar'", contract_tests)

    assert main_nas_preflight < migration_scan
    assert first_freeze < migration_scan
    assert migration_scan < migration_policy_gate < contract_tests < maven_build


def test_nas_config_path_resolves_against_maintenance_repo_not_caller_cwd() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    reader = _function(source, "Read-NasReleaseConfig", "Join-NasRelativePath")

    assert "Resolve-MaintenanceRepoRelativeFilePath" in source
    assert "Resolve-MaintenanceRepoRelativeFilePath -PathValue $NasConfigPath -ArgumentName 'NasConfigPath'" in reader
    assert "[System.IO.Path]::IsPathRooted($trimmedPath)" in source
    assert "Join-Path $maintenanceRoot $trimmedPath" in source
    assert "[System.IO.File]::ReadAllText($resolvedNasConfigPath" in reader


def test_release_script_pytest_runs_from_maintenance_repo_root() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    tests = _function(source, "Invoke-StandardReleaseContractTests", "Get-ReleaseSchemaDigest")
    release_script_tests = tests[tests.index("Info 'Running release script tests'"):]

    assert "$maintenanceRoot = (Resolve-Path (Join-Path $scriptDir '..\\..')).Path" in tests
    assert "-WorkingDirectory $maintenanceRoot" in release_script_tests


def test_backend_contract_maven_uses_windows_surefire_classpath_guard() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    tests = _function(source, "Invoke-StandardReleaseContractTests", "Get-ReleaseSchemaDigest")
    helper = _function(source, "Invoke-CheckedMavenCommand", "Invoke-CheckedShell")

    assert "Invoke-CheckedMavenCommand -ArgumentList @(" in tests
    assert "$env:JDK_JAVA_OPTIONS" in helper
    assert "-Djdk.net.URLClassPath.disableClassPathURLCheck=true" in helper
    assert "finally" in helper and "$env:JDK_JAVA_OPTIONS = $previousJdkJavaOptions" in helper


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


def test_app_release_workflow_never_writes_edhr_storage_probe() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    call = "Invoke-EdhrStorageRetentionVerifier -BackendRepo $backendRepo"

    runtime_validation = source.split("$mySqlRootPassword = ''", 1)[0]
    assert call not in runtime_validation
    assert "Assert-EdhrProtectedStorageConfig -Context 'target publish environment'" in runtime_validation


def test_application_sql_static_regressions_are_mandatory_build_gates() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    tests = _function(source, "Invoke-StandardReleaseContractTests", "Get-ReleaseSchemaDigest")

    assert "Assert-ApplicationMigrationTestsDiscovered" in tests
    assert "MIGRATION_TEST_MISSING" in source
    assert "Get-ReleaseGitValue -RepoPath $applicationRoot" in tests


def test_application_migration_tests_use_runner_for_each_file_type() -> None:
    source = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    tests = _function(source, "Invoke-StandardReleaseContractTests", "Get-ReleaseSchemaDigest")

    assert "applicationPytestFiles" in tests
    assert "applicationNodeTestFiles" in tests
    assert "Invoke-CheckedCommand -FilePath 'node'" in tests
    assert "-notmatch '(^|/)target-preflight/'" in tests
