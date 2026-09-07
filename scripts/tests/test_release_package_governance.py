from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
GOVERNANCE_MODULE = ROOT / "ops" / "release" / "lib" / "ReleasePackageGovernance.psm1"
ACTION_SOURCE = (
    ROOT
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "intruoyi"
    / "maintenance"
    / "runtime"
    / "RuntimeControlOperationAction.java"
)


def _powershell() -> str:
    executable = shutil.which("powershell")
    if executable is None:
        pytest.fail("Windows PowerShell 5.1 is required for release governance tests")
    return executable


def _run_powershell(arguments: list[str], *, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_powershell(), "-NoLogo", "-NoProfile", "-NonInteractive", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_package(
    package_dir: Path,
    *,
    release_tag: str = "release-p2-fixture",
    publish_scope: str = "code-only",
) -> dict[str, object]:
    package_dir.mkdir(parents=True)
    payload = {
        "manifest.json": b'{"manifestVersion":"1.0"}\n',
        "bin/app.bin": b"immutable-app-payload\x00\x01",
    }
    artifacts: list[dict[str, object]] = []
    for relative_path, content in payload.items():
        target = package_dir / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        artifacts.append(
            {
                "path": relative_path,
                "sha256": _sha256(content),
                "bytes": len(content),
            }
        )
    manifest: dict[str, object] = {
        "releaseTag": release_tag,
        "packageDirectoryName": package_dir.name,
        "publishScope": publish_scope,
        "artifacts": artifacts,
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (package_dir / "release-manifest.json").write_bytes(manifest_bytes)
    return manifest


def _rewrite_manifest(package_dir: Path, manifest: dict[str, object]) -> None:
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (package_dir / "release-manifest.json").write_bytes(manifest_bytes)


def _verify_package(package_dir: Path | str) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE_MODULE}'",
            f"Test-ReleasePackageIntegrity -PackagePath '{package_dir}' | ConvertTo-Json -Depth 8 -Compress",
        ]
    )
    return _run_powershell(["-Command", command])


def _verification_result(package_dir: Path | str) -> dict[str, object]:
    result = _verify_package(package_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip())


def test_mode_is_mandatory_and_direct_is_rejected_before_script_body(tmp_path: Path) -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    mode_declaration = re.search(
        r"\[Parameter\(Mandatory\s*=\s*\$true\)\]\s*"
        r"\[ValidateSet\((?P<values>[^)]*)\)\]\s*"
        r"\[string\]\$Mode(?P<default>\s*=\s*[^,]+)?\s*,",
        script,
        flags=re.IGNORECASE,
    )
    assert mode_declaration is not None
    assert "direct" not in mode_declaration.group("values")
    assert mode_declaration.group("default") is None

    for supplied_mode in (None, "direct"):
        sentinel = tmp_path / ("missing-mode" if supplied_mode is None else supplied_mode)
        arguments = ["-File", str(PUBLISH_SCRIPT), "-LocalCacheRoot", str(sentinel)]
        if supplied_mode is not None:
            arguments.extend(["-Mode", supplied_mode])
        result = _run_powershell(arguments)
        assert result.returncode != 0
        assert not sentinel.exists(), result.stdout + result.stderr


@pytest.mark.parametrize(
    ("environment", "publish_scope", "allowed"),
    [
        ("test", "with-data", True),
        ("test", "code-only", True),
        ("prod", "code-only", True),
        ("backup", "code-only", True),
        ("prod", "with-data", False),
        ("backup", "with-data", False),
    ],
)
def test_release_package_scope_matrix_blocks_production_data_packages_before_probe(
    tmp_path: Path, environment: str, publish_scope: str, allowed: bool
) -> None:
    probe = tmp_path / f"{environment}-{publish_scope}.probe"
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE_MODULE}'",
            f"Assert-ReleasePackageDeploymentScope -TargetEnvironment '{environment}' -PublishScope '{publish_scope}'",
            f"[System.IO.File]::WriteAllText('{probe}', 'external-action-probe')",
        ]
    )
    result = _run_powershell(["-Command", command])

    if allowed:
        assert result.returncode == 0, result.stdout + result.stderr
        assert probe.read_text(encoding="utf-8") == "external-action-probe"
    else:
        assert result.returncode != 0
        assert "requires a code-only release package" in result.stdout + result.stderr
        assert not probe.exists()


def test_scope_gate_is_wired_before_remote_or_deployment_actions() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    deploy_start = script.index("if ($Mode -eq 'deploy-release') {")
    deploy_end = script.index("if ($Mode -eq 'build-release' -and $publishBackend)", deploy_start)
    deploy_block = script[deploy_start:deploy_end]

    integrity_index = deploy_block.index("$releasePackageIntegrity = Copy-ReleasePackageFromNas")
    scope_index = deploy_block.index("$releasePublishScope = $releasePackageIntegrity.PublishScope")
    gate_index = deploy_block.index("Assert-ReleasePackageDeploymentScope")
    assert integrity_index < scope_index < gate_index
    for later_action in (
        "Assert-DeployReleasePackageArtifactsForScope",
        "Apply-ReleaseRuntimeEnvPackage",
        "Require-Command 'ssh'",
        "Import-ExistingRemoteRuntimeEnvSettings",
        "Invoke-SmartReleaseDeployPrecheckReportOnly",
    ):
        assert gate_index < deploy_block.index(later_action)


def test_runtime_console_only_emits_explicit_package_modes_for_code_only_flow() -> None:
    source = ACTION_SOURCE.read_text(encoding="utf-8")
    explicit_modes = re.findall(r'args\.add\("(build-release|deploy-release|mark-tested|direct)"\);', source)

    assert set(explicit_modes) == {"build-release", "deploy-release", "mark-tested"}
    assert 'args.add("direct")' not in source
    assert 'args.add("-SkipDatabaseSync")' in source
    assert 'args.add("-SkipMinioSync")' in source
    assert 'deployReleaseArguments("test", req)' in source
    assert 'deployReleaseArguments("prod", req)' in source
    assert 'deployReleaseArguments("backup", req)' in source


def test_publish_script_has_valid_powershell_ast() -> None:
    command = "\n".join(
        [
            "$errors = $null",
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{PUBLISH_SCRIPT}', [ref]$null, [ref]$errors)",
            "if ($errors.Count -gt 0) { $errors | ConvertTo-Json -Compress; exit 1 }",
        ]
    )
    result = _run_powershell(["-Command", command])
    assert result.returncode == 0, result.stdout + result.stderr


def test_integrity_verifier_exactly_covers_payload_and_includes_manifest_json(tmp_path: Path) -> None:
    package_dir = tmp_path / "package-exact"
    _write_package(package_dir)

    verification = _verification_result(package_dir)

    assert verification["releaseTag"] == "release-p2-fixture"
    assert verification["packageDirectoryName"] == "package-exact"
    assert verification["publishScope"] == "code-only"
    assert [item["path"] for item in verification["artifacts"]] == ["bin/app.bin", "manifest.json"]
    assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in verification["artifacts"])


def test_package_digest_uses_fixed_vector_and_is_root_separator_independent(tmp_path: Path) -> None:
    package_a = tmp_path / "root-a" / "same-package"
    package_b = tmp_path / "root-b" / "same-package"
    _write_package(package_a)
    shutil.copytree(package_a, package_b)

    result_a = _verification_result(package_a)
    result_b = _verification_result(package_b)
    result_b_forward_slash = _verification_result(package_b.as_posix())

    manifest_digest = f"sha256:{_sha256((package_a / 'release-manifest.json').read_bytes())}"
    canonical_records = [f"manifestDigest={manifest_digest}\n"]
    for artifact in sorted(result_a["artifacts"], key=lambda item: item["path"]):
        canonical_records.append(
            f"artifact={artifact['path']}\tsha256:{artifact['sha256']}\t{artifact['bytes']}\n"
        )
    expected_package_digest = f"sha256:{_sha256(''.join(canonical_records).encode('utf-8'))}"

    assert result_a["manifestDigest"] == manifest_digest
    assert result_a["packageDigest"] == expected_package_digest
    assert manifest_digest == "sha256:2d03b3a34a07105aec291600962fcfbf1494534055466a0d559ca7736db75c62"
    assert expected_package_digest == "sha256:bca84ee56d15a8cf4b662442ba30d7f96000835ccaa63d6c6d402251cdde3276"
    assert result_b["packageDigest"] == expected_package_digest
    assert result_b_forward_slash["packageDigest"] == expected_package_digest


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("tamper", "bin/app.bin: hash mismatch"),
        ("missing", "bin/app.bin: missing artifact"),
        ("extra", "extra.txt: undeclared file"),
        ("bytes", "bin/app.bin: bytes mismatch"),
        ("hash", "bin/app.bin: hash mismatch"),
        ("absolute", "C:/outside.bin: invalid artifact path"),
        ("parent", "../outside.bin: invalid artifact path"),
        ("backslash", "bin\\app.bin: invalid artifact path"),
        ("duplicate", "bin/app.bin: duplicate artifact path"),
        ("case-conflict", "BIN/APP.BIN: duplicate artifact path"),
        ("uppercase-hash", "bin/app.bin: invalid sha256"),
        ("negative-bytes", "bin/app.bin: invalid bytes"),
        ("null-bytes", "bin/app.bin: invalid bytes"),
        ("missing-manifest-declaration", "manifest.json: missing artifact declaration"),
        ("declared-missing", "ghost.bin: missing artifact"),
    ],
)
def test_integrity_verifier_rejects_all_payload_drift(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    package_dir = tmp_path / f"package-{mutation}"
    manifest = _write_package(package_dir)
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)

    if mutation == "tamper":
        (package_dir / "bin" / "app.bin").write_bytes(b"X" * int(artifacts[1]["bytes"]))
    elif mutation == "missing":
        (package_dir / "bin" / "app.bin").unlink()
    elif mutation == "extra":
        (package_dir / "extra.txt").write_text("not declared", encoding="utf-8")
    elif mutation == "bytes":
        artifacts[1]["bytes"] = int(artifacts[1]["bytes"]) + 1
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "hash":
        artifacts[1]["sha256"] = "0" * 64
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "absolute":
        artifacts[1]["path"] = "C:/outside.bin"
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "parent":
        artifacts[1]["path"] = "../outside.bin"
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "backslash":
        artifacts[1]["path"] = "bin\\app.bin"
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "duplicate":
        artifacts.append(dict(artifacts[1]))
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "case-conflict":
        duplicate = dict(artifacts[1])
        duplicate["path"] = "BIN/APP.BIN"
        artifacts.append(duplicate)
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "uppercase-hash":
        artifacts[1]["sha256"] = str(artifacts[1]["sha256"]).upper()
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "negative-bytes":
        artifacts[1]["bytes"] = -1
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "null-bytes":
        artifacts[1]["bytes"] = None
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "missing-manifest-declaration":
        artifacts.pop(0)
        _rewrite_manifest(package_dir, manifest)
    elif mutation == "declared-missing":
        artifacts.append({"path": "ghost.bin", "sha256": "0" * 64, "bytes": 0})
        _rewrite_manifest(package_dir, manifest)

    result = _verify_package(package_dir)
    assert result.returncode != 0
    assert expected_error in result.stdout + result.stderr


def test_payload_or_manifest_change_changes_digest_or_fails(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline" / "same-package"
    manifest_changed_dir = tmp_path / "manifest-changed" / "same-package"
    payload_changed_dir = tmp_path / "payload-changed" / "same-package"
    manifest = _write_package(baseline_dir)
    shutil.copytree(baseline_dir, manifest_changed_dir)
    shutil.copytree(baseline_dir, payload_changed_dir)

    baseline = _verification_result(baseline_dir)
    manifest["publishScope"] = "with-data"
    _rewrite_manifest(manifest_changed_dir, manifest)
    manifest_changed = _verification_result(manifest_changed_dir)
    (payload_changed_dir / "bin" / "app.bin").write_bytes(b"changed-without-manifest-update")
    payload_changed = _verify_package(payload_changed_dir)

    assert manifest_changed["manifestDigest"] != baseline["manifestDigest"]
    assert manifest_changed["packageDigest"] != baseline["packageDigest"]
    assert payload_changed.returncode != 0
    assert "bin/app.bin: bytes mismatch" in payload_changed.stdout + payload_changed.stderr


def test_only_controlled_mutable_metadata_is_excluded_from_payload(tmp_path: Path) -> None:
    package_dir = tmp_path / "package-metadata"
    _write_package(package_dir)
    mutable_files = {
        "tested.json": b"not-yet-validated-by-p3",
        "rollback-compatibility.json": b"not-payload",
        "prod-latest.json": b"mutable-prod-pointer",
        "backup-latest.json": b"mutable-backup-pointer",
        "prod-deployments/20260907/deploy.json": b"prod-history",
        "backup-deployments/20260907/deploy.json": b"backup-history",
    }
    for relative_path, content in mutable_files.items():
        target = package_dir / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    verification = _verification_result(package_dir)
    assert [item["path"] for item in verification["artifacts"]] == ["bin/app.bin", "manifest.json"]

    for invalid_extra in (
        "attestation.json",
        "prod-deployments.json",
        "deployments/deploy.json",
    ):
        isolated_dir = (
            tmp_path / invalid_extra.replace("/", "-").replace(".", "-") / "package-metadata"
        )
        isolated_dir.parent.mkdir(parents=True)
        shutil.copytree(package_dir, isolated_dir)
        target = isolated_dir / Path(invalid_extra)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"not-whitelisted")
        result = _verify_package(isolated_dir)
        assert result.returncode != 0
        assert f"{invalid_extra}: undeclared file" in result.stdout + result.stderr

    case_check = _run_powershell(
        [
            "-Command",
            "\n".join(
                [
                    f"Import-Module -Force '{GOVERNANCE_MODULE}'",
                    "Test-IsReleasePackageMutableMetadataPath -RelativePath 'Prod-deployments/deploy.json'",
                ]
            ),
        ]
    )
    assert case_check.returncode == 0
    assert case_check.stdout.strip() == "False"


def test_manifest_generation_avoids_self_reference_and_declares_manifest_json() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    function_start = script.index("function Write-ReleaseManifest {")
    function_end = script.index("if ($ReleaseTag.Contains('..')", function_start)
    function_body = script[function_start:function_end]

    v1_write = function_body.index("Write-ReleaseManifestV1")
    final_collection = function_body.index("Get-ReleasePackageImmutableArtifactEntries", v1_write)
    legacy_write = function_body.index("'release-manifest.json'", final_collection)
    assert v1_write < final_collection < legacy_write


def test_same_verifier_guards_all_four_package_lifecycle_points() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    verifier_call = "Test-ReleasePackageIntegrity"

    copy_to_start = script.index("function Copy-ReleasePackageToNas")
    copy_to_end = script.index("function Copy-ReleasePackageFromNas", copy_to_start)
    copy_to = script[copy_to_start:copy_to_end]
    assert copy_to.index("Copy-Item") < copy_to.index(verifier_call)
    assert copy_to.index(verifier_call) < copy_to.index("Release package uploaded to NAS")

    copy_from_start = script.index("function Copy-ReleasePackageFromNas")
    copy_from_end = script.index("function Get-RequiredJsonPropertyValue", copy_from_start)
    copy_from = script[copy_from_start:copy_from_end]
    assert copy_from.index("Copy-Item") < copy_from.index(verifier_call)
    assert copy_from.index(verifier_call) < copy_from.index("Release package downloaded from NAS")

    mark_start = script.index("function Mark-NasReleaseTested")
    mark_end = script.index("function Read-ReleaseManifest", mark_start)
    mark = script[mark_start:mark_end]
    assert mark.index(verifier_call) < mark.index("Write-ReleaseTestedAttestation")

    build_start = script.index("Write-ReleaseManifest -PackageTag $ReleaseTag")
    build_end = script.index("if ($Mode -eq 'build-release')", build_start)
    build = script[build_start:build_end]
    assert build.index(verifier_call) > build.index("Write-ReleaseManifest")

    deploy_start = script.index("if ($Mode -eq 'deploy-release') {")
    deploy_end = script.index("if ($Mode -eq 'build-release' -and $publishBackend)", deploy_start)
    deploy = script[deploy_start:deploy_end]
    assert "$releasePackageIntegrity = Copy-ReleasePackageFromNas" in deploy
    assert "$releasePublishScope = $releasePackageIntegrity.PublishScope" in deploy


def _write_operation(
    path: Path,
    *,
    operation_id: str = "op-publish-test-success",
    environment: str = "test",
    action: str = "publish-test",
    status: str = "SUCCESS",
    release_tag: str = "release-p3-fixture",
    requested_at: str = "2026-09-07T12:34:56Z",
) -> None:
    payload = {
        "operationId": operation_id,
        "requestedBy": "local-operator",
        "requestedAt": requested_at,
        "environment": environment,
        "component": "publish-test",
        "action": action,
        "actionLabel": "publish-test",
        "parameters": {"releaseTag": release_tag},
        "reason": "local fixture",
        "status": status,
        "summary": "success",
        "resultLogPath": "fixture.log",
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _write_tested_attestation(package_dir: Path, operation_path: Path) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE_MODULE}'",
            f"Write-ReleaseTestedAttestation -PackagePath '{package_dir}' -ExpectedReleaseTag 'release-p3-fixture' "
            f"-TestOperationId 'op-publish-test-success' -TestOperationEvidencePath '{operation_path}' "
            "-TestedBy 'local-operator' -TestConclusion 'all acceptance checks passed' | ConvertTo-Json -Depth 8 -Compress",
        ]
    )
    return _run_powershell(["-Command", command])


def _verify_promotion(
    package_dir: Path,
    operation_path: Path,
    environment: str,
) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE_MODULE}'",
            f"Test-ReleasePromotionAttestation -PackagePath '{package_dir}' -ExpectedReleaseTag 'release-p3-fixture' "
            f"-TargetEnvironment '{environment}' -TestOperationId 'op-publish-test-success' "
            f"-TestOperationEvidencePath '{operation_path}' | ConvertTo-Json -Depth 8 -Compress",
        ]
    )
    return _run_powershell(["-Command", command])


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ({"environment": "prod"}, "environment mismatch"),
        ({"action": "promote-prod"}, "action mismatch"),
        ({"status": "FAILED"}, "status mismatch"),
        ({"release_tag": "other-release"}, "releaseTag mismatch"),
        ({"operation_id": "other-operation"}, "operationId mismatch"),
        ({"requested_at": "not-a-time"}, "requestedAt invalid"),
    ],
)
def test_mark_tested_rejects_invalid_operation_without_overwriting_existing_attestation(
    tmp_path: Path, mutation: dict[str, str], expected_error: str
) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    tested_path = package_dir / "tested.json"
    original = b"existing-attestation-must-survive"
    tested_path.write_bytes(original)
    operation_path = tmp_path / "operation.json"
    _write_operation(operation_path, **mutation)

    result = _write_tested_attestation(package_dir, operation_path)

    assert result.returncode != 0
    assert expected_error in result.stdout + result.stderr
    assert tested_path.read_bytes() == original
    assert list(package_dir.glob("tested.json.*.tmp")) == []


def test_mark_tested_rejects_missing_or_malformed_operation_without_creating_attestation(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    operation_path = tmp_path / "operation.json"

    for content, expected_error in ((None, "operation evidence missing"), ("{", "operation evidence invalid JSON")):
        if content is None:
            operation_path.unlink(missing_ok=True)
        else:
            operation_path.write_text(content, encoding="utf-8")
        result = _write_tested_attestation(package_dir, operation_path)
        assert result.returncode != 0
        assert expected_error in result.stdout + result.stderr
        assert not (package_dir / "tested.json").exists()


def test_mark_tested_writes_atomic_v2_attestation_bound_to_package_and_operation(tmp_path: Path) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    operation_path = tmp_path / "operation.json"
    _write_operation(operation_path)

    result = _write_tested_attestation(package_dir, operation_path)
    assert result.returncode == 0, result.stdout + result.stderr
    written = json.loads((package_dir / "tested.json").read_text(encoding="utf-8"))
    integrity = _verification_result(package_dir)

    assert written["schemaVersion"] == "v2"
    assert written["releaseTag"] == "release-p3-fixture"
    assert written["packageDirectoryName"] == "release-p3-fixture"
    assert written["packageDigest"] == integrity["packageDigest"]
    assert written["manifestDigest"] == integrity["manifestDigest"]
    assert written["testEnvironment"] == "test"
    assert written["publishTestOperationId"] == "op-publish-test-success"
    assert written["publishTestOperationStatus"] == "SUCCESS"
    assert written["publishTestRequestedAt"] == "2026-09-07T12:34:56Z"
    assert written["testedBy"] == "local-operator"
    assert written["testConclusion"] == "all acceptance checks passed"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", written["testedAt"])
    assert list(package_dir.glob("tested.json.*.tmp")) == []


@pytest.mark.parametrize("environment", ["prod", "backup"])
def test_valid_attestation_allows_both_production_grade_environments(
    tmp_path: Path, environment: str
) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    operation_path = tmp_path / "operation.json"
    _write_operation(operation_path)
    assert _write_tested_attestation(package_dir, operation_path).returncode == 0

    result = _verify_promotion(package_dir, operation_path, environment)

    assert result.returncode == 0, result.stdout + result.stderr
    verification = json.loads(result.stdout.strip())
    assert verification["releaseTag"] == "release-p3-fixture"
    assert verification["testOperationId"] == "op-publish-test-success"


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("schemaVersion", "v1", "schemaVersion mismatch"),
        ("releaseTag", "other", "releaseTag mismatch"),
        ("packageDirectoryName", "other", "packageDirectoryName mismatch"),
        ("packageDigest", "sha256:" + "0" * 64, "packageDigest mismatch"),
        ("manifestDigest", "sha256:" + "0" * 64, "manifestDigest mismatch"),
        ("testEnvironment", "prod", "testEnvironment mismatch"),
        ("publishTestOperationId", "other", "publishTestOperationId mismatch"),
        ("publishTestOperationStatus", "FAILED", "publishTestOperationStatus mismatch"),
        ("publishTestRequestedAt", "2026-09-07T12:35:00Z", "publishTestRequestedAt mismatch"),
        ("testedAt", "not-a-time", "testedAt invalid"),
        ("testedBy", "", "testedBy invalid"),
        ("testConclusion", "", "testConclusion invalid"),
    ],
)
def test_prod_and_backup_reject_every_stale_or_forged_attestation_field_before_probe(
    tmp_path: Path, field: str, value: str, expected_error: str
) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    operation_path = tmp_path / "operation.json"
    _write_operation(operation_path)
    assert _write_tested_attestation(package_dir, operation_path).returncode == 0
    tested_path = package_dir / "tested.json"
    tested = json.loads(tested_path.read_text(encoding="utf-8"))
    tested[field] = value
    tested_path.write_text(json.dumps(tested, separators=(",", ":")), encoding="utf-8")

    for environment in ("prod", "backup"):
        probe = tmp_path / f"{field}-{environment}.probe"
        command = "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                f"Import-Module -Force '{GOVERNANCE_MODULE}'",
                f"Test-ReleasePromotionAttestation -PackagePath '{package_dir}' -ExpectedReleaseTag 'release-p3-fixture' "
                f"-TargetEnvironment '{environment}' -TestOperationId 'op-publish-test-success' "
                f"-TestOperationEvidencePath '{operation_path}'",
                f"[System.IO.File]::WriteAllText('{probe}', 'external-action')",
            ]
        )
        result = _run_powershell(["-Command", command])
        assert result.returncode != 0
        assert expected_error in result.stdout + result.stderr
        assert not probe.exists()


def test_promotion_recomputes_payload_and_rejects_drift_before_probe(tmp_path: Path) -> None:
    package_dir = tmp_path / "release-p3-fixture"
    _write_package(package_dir, release_tag="release-p3-fixture")
    operation_path = tmp_path / "operation.json"
    _write_operation(operation_path)
    assert _write_tested_attestation(package_dir, operation_path).returncode == 0
    (package_dir / "bin" / "app.bin").write_bytes(b"X" * 23)

    result = _verify_promotion(package_dir, operation_path, "prod")
    assert result.returncode != 0
    assert "bin/app.bin: hash mismatch" in result.stdout + result.stderr


def test_production_attestation_gate_is_unconditional_and_precedes_remote_actions() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    action_source = ACTION_SOURCE.read_text(encoding="utf-8")
    assert "RequireTested" not in script
    assert "TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED" not in script
    assert 'args.add("-RequireTested")' not in action_source

    copy_start = script.index("function Copy-ReleasePackageFromNas")
    copy_end = script.index("function Get-RequiredJsonPropertyValue", copy_start)
    copy_block = script[copy_start:copy_end]
    integrity_index = copy_block.index("Test-ReleasePackageIntegrity")
    attestation_index = copy_block.index("Test-ReleasePromotionAttestation")
    assert integrity_index < attestation_index < copy_block.index("return $packageIntegrity")

    evidence_gate = script.index("Assert-PublishTestOperationEvidence")
    mark_call = script.index("Mark-NasReleaseTested -PackageTag")
    deploy_copy = script.index("$releasePackageIntegrity = Copy-ReleasePackageFromNas")
    assert evidence_gate < mark_call
    assert evidence_gate < deploy_copy


def test_blocked_rollback_compatibility_preserves_existing_tested_attestation(tmp_path: Path) -> None:
    tested_path = tmp_path / "tested.json"
    original = b"existing-tested-attestation"
    tested_path.write_bytes(original)
    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Force '{GOVERNANCE_MODULE}'",
            "$compatibility = @{ status = 'BLOCKED'; summary = 'recovery set does not match package' }",
            "Assert-ReleaseRollbackCompatibility -Compatibility $compatibility",
            f"[System.IO.File]::WriteAllText('{tested_path}', 'must-not-write')",
        ]
    )

    result = _run_powershell(["-Command", command])

    assert result.returncode != 0
    assert "rollback compatibility BLOCKED" in result.stdout + result.stderr
    assert tested_path.read_bytes() == original


def test_mark_checks_rollback_compatibility_before_atomic_tested_write() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    mark_start = script.index("function Mark-NasReleaseTested")
    mark_end = script.index("function Read-ReleaseManifest", mark_start)
    mark = script[mark_start:mark_end]

    compatibility_index = mark.index("$compatibility = New-RollbackCompatibilityEvidence")
    gate_index = mark.index("Assert-ReleaseRollbackCompatibility")
    tested_write_index = mark.index("Write-ReleaseTestedAttestation")
    assert compatibility_index < gate_index < tested_write_index
