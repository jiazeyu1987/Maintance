from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from release_test_runtime import application_backend_root


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/deploy/publish-int-ruoyi.ps1"
GOVERNANCE = ROOT / "ops/release/lib/ReleasePackageGovernance.psm1"
SMOKE_IMAGE = "mcr.microsoft.com/playwright:v1.60.0-noble"


def _tar_bytes(files: dict[str, bytes]) -> bytes:
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as archive:
        for name, content in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    return result.getvalue()


def complete_package_payload(package_id: str, profile: str = "intruoyi", only_office: bool = False):
    references = {
        "backend": f"intruoyi-backend:{package_id}",
        "frontend": f"intruoyi-frontend:{package_id}",
        "scheduler-smoke": SMOKE_IMAGE,
    }
    if profile == "full":
        references["website"] = "nginx:1.27-alpine"
    if only_office:
        references["onlyoffice"] = "onlyoffice/documentserver:latest"
    image_files = {}
    docker_manifest = []
    images = []
    for name, reference in references.items():
        config = json.dumps({
            "architecture": "amd64", "os": "linux", "config": {"Labels": {"fixture": name}},
            "rootfs": {"type": "layers", "diff_ids": []},
        }, sort_keys=True).encode()
        image_id = hashlib.sha256(config).hexdigest()
        image_files[f"{image_id}.json"] = config
        docker_manifest.append({"Config": f"{image_id}.json", "RepoTags": [reference], "Layers": []})
        images.append({"name": name, "reference": reference, "id": f"sha256:{image_id}", "sizeBytes": len(config)})
    image_files["manifest.json"] = json.dumps(docker_manifest).encode()
    smoke_dependencies = _tar_bytes({
        "node_modules/playwright/package.json": b'{"name":"playwright","version":"1.60.0"}',
        "node_modules/xlsx/package.json": b'{"name":"xlsx","version":"0.18.5"}',
    })
    files = {
        "bin/app.bin": b"immutable-app-payload\x00\x01",
        "docker-compose.yml": (ROOT / "ops/deploy/int-ruoyi-test/docker-compose.yml").read_bytes(),
        f"intruoyi-images_{package_id}.tar": _tar_bytes(image_files),
        "manifest/docker-build-evidence.json": json.dumps({
            "schemaVersion": "release-docker-build-evidence/v1",
            "components": [{"name": item["name"], "imageReference": item["reference"],
                            "actualImage": {"reference": item["reference"], "id": item["id"], "repoDigests": []}}
                           for item in images if item["name"] in {"backend", "frontend"}],
        }).encode(),
        "required-sql/001.sql": b"SELECT 1;\n",
        "ops-runtime/linux/backup-ops-linux.sh": b"#!/bin/sh\nexit 0\n",
        "ops-runtime/scripts/backup-ops.ps1": b"param()\n",
        "ops-runtime/actions/action.ps1": b"param()\n",
        "smoke/bin/npm": b"#!/bin/sh\nexec npm \"$@\"\n",
        "smoke/yudao-ui-admin-vue3/package.json": b'{"devDependencies":{"playwright":"1.60.0","xlsx":"0.18.5"}}',
        "smoke/yudao-ui-admin-vue3/package-lock.json": b'{"lockfileVersion":3,"packages":{}}',
        "smoke/yudao-ui-admin-vue3/dependencies.tar": smoke_dependencies,
        "smoke/yudao-ui-admin-vue3/tests/e2e/smart-scheduling-smoke-real-flow.e2e.js": b"'use strict';\n",
        "smoke/yudao-ui-admin-vue3/tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js": b"'use strict';\n",
    }
    components = ["backend", "admin-frontend", "database-contract", "required-sql", "runtime-env", "packaging-manifest"]
    prerequisites = [{"toolId": "dcc-codex", "pathEnv": "DCC_PROJECT_CODE_CODEX_CLI_COMMAND", "sha256Env": "DCC_PROJECT_CODE_CODEX_CLI_SHA256"}]
    if profile == "full":
        files["website/dist/index.html"] = b"<html><body>Package fixture</body></html>"
        files["website/nginx.template.conf"] = b"location /api { proxy_pass http://__BACKEND_ORIGIN__; }\n"
        components.append("website")
        prerequisites.append({"toolId": "showroom-codex", "pathEnv": "SHOWROOM_CODEX_CLI_COMMAND", "sha256Env": "SHOWROOM_CODEX_CLI_SHA256"})
    if only_office:
        components.append("onlyoffice")
    metadata = {"installationContractVersion": "full-app-release/v1", "component": profile,
                "components": components, "onlyOfficeIncluded": only_office, "runtimeImages": images,
                "targetRequirements": {"platformPrerequisites": prerequisites}}
    return files, metadata


def write_complete_package(root: Path, *, profile="intruoyi", only_office=False):
    root.mkdir(parents=True)
    files, metadata = complete_package_payload(root.name, profile, only_office)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {
        "releaseTag": root.name, "packageId": root.name, "publishScope": "app-release", **metadata,
        "sourceRoots": [{"rootRole": role, "normalizedRoot": f"d:/fixture/{role}", "approvedCommit": commit * 40,
                         "commit": commit * 40, "dirty": False}
                        for role, commit in [("maintenance", "a"), ("application", "b")]],
        "sourceRoles": [{"sourceRole": role, "rootRole": owner, "relativePath": path, "commit": commit * 40}
                        for role, owner, path, commit in [("maintenance", "maintenance", ".", "a"),
                            ("backend", "application", "IntRuoyiBackend", "b"),
                            ("frontend", "application", "IntRuoyiFronted", "b")]],
    }
    rebind_package(root, manifest)
    return manifest


def rebind_package(root: Path, manifest):
    artifacts = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            content = path.read_bytes()
            artifacts.append({"path": path.relative_to(root).as_posix(), "bytes": len(content),
                              "sha256": hashlib.sha256(content).hexdigest()})
    manifest["artifacts"] = artifacts
    canonical = "".join(f"{a['path']}\t{a['bytes']}\t{a['sha256']}\n" for a in artifacts)
    manifest["packageDigest"] = hashlib.sha256(canonical.encode()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _ps(script: str):
    encoded = base64.b64encode(script.encode("utf-16le")).decode()
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                          encoding="utf-8", text=True, capture_output=True, check=False, timeout=45)


def _functions(*names):
    requested = ",".join(f"'{name}'" for name in names)
    return f"""
$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{SCRIPT}',[ref]$tokens,[ref]$errors)
if ($errors.Count) {{ throw 'production script syntax error' }}
foreach($name in @({requested})) {{
 $fn=$ast.Find({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name}},$true)
 if ($null -ne $fn) {{ Invoke-Expression $fn.Extent.Text }}
}}
function Fail([string]$Message) {{ throw $Message }}
function Info([string]$Message) {{}}
"""


def verify(root: Path):
    return _ps(f"$ErrorActionPreference='Stop'; Import-Module '{GOVERNANCE}' -Force; Test-ReleasePackageIntegrity -PackagePath '{root}' | ConvertTo-Json -Depth 12 -Compress")


@pytest.mark.parametrize("profile", ["intruoyi", "full"])
@pytest.mark.parametrize("only_office", [False, True])
def test_complete_profiles_accept_all_fixed_components(tmp_path, profile, only_office):
    root = tmp_path / "release-complete"
    write_complete_package(root, profile=profile, only_office=only_office)
    result = verify(root)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("component", ["backend", "frontend", "website"])
def test_single_component_package_is_rejected(tmp_path, component):
    root = tmp_path / "release-single"
    manifest = write_complete_package(root)
    manifest["component"] = component
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_COMPONENT_INVALID" in result.stdout + result.stderr


@pytest.mark.parametrize("component", ["backend", "frontend", "website"])
def test_actual_cli_parameter_contract_rejects_single_component(component):
    result = _ps(_functions() + f"\n$bind=[scriptblock]::Create($ast.ParamBlock.Extent.Text + \"`n'ACCEPTED'\"); & $bind -Mode build-release -Component '{component}'")
    assert result.returncode != 0
    assert "ValidateSet" in result.stderr or "ParameterArgumentValidationError" in result.stderr


@pytest.mark.parametrize("component", ["intruoyi", "full", "frontend"])
def test_deploy_cannot_override_manifest_component(tmp_path, component):
    root = tmp_path / "release-selection"
    write_complete_package(root)
    result = _ps(_functions("Read-ReleaseManifest", "Resolve-DeployReleasePackageComponent") + f"\n$releaseDir='{root}'; $Component='{component}'; Resolve-DeployReleasePackageComponent -ComponentExplicit $true")
    assert result.returncode != 0
    assert "DEPLOY_COMPONENT_OVERRIDE_FORBIDDEN" in result.stdout + result.stderr


def test_deploy_cannot_override_onlyoffice(tmp_path):
    root = tmp_path / "release-office"
    write_complete_package(root)
    result = _ps(_functions("Read-ReleaseManifest", "Resolve-DeployReleasePackageOnlyOfficeIncluded") + f"\n$releaseDir='{root}'; Resolve-DeployReleasePackageOnlyOfficeIncluded -IncludeOnlyOfficeExplicit $true")
    assert result.returncode != 0
    assert "DEPLOY_ONLYOFFICE_OVERRIDE_FORBIDDEN" in result.stdout + result.stderr


@pytest.mark.parametrize("missing", [
    "docker-compose.yml", "website/nginx.template.conf", "website/dist/index.html",
    "intruoyi-images_release-missing.tar", "manifest/docker-build-evidence.json",
    "ops-runtime/linux/backup-ops-linux.sh", "smoke/bin/npm",
    "smoke/yudao-ui-admin-vue3/package-lock.json", "smoke/yudao-ui-admin-vue3/dependencies.tar",
])
def test_self_consistent_package_missing_required_input_is_rejected(tmp_path, missing):
    root = tmp_path / "release-missing"
    manifest = write_complete_package(root, profile="full")
    (root / missing).unlink()
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_REQUIRED_ARTIFACT_MISSING" in result.stdout + result.stderr
    assert missing in result.stdout + result.stderr


@pytest.mark.parametrize("missing", ["backend", "frontend", "scheduler-smoke", "website", "onlyoffice"])
def test_image_archive_must_contain_each_selected_image(tmp_path, missing):
    root = tmp_path / "release-image"
    manifest = write_complete_package(root, profile="full", only_office=True)
    archive_path = root / f"intruoyi-images_{root.name}.tar"
    with tarfile.open(archive_path) as archive:
        files = {entry.name: archive.extractfile(entry).read() for entry in archive}
    missing_ref = next(item["reference"] for item in manifest["runtimeImages"] if item["name"] == missing)
    images = [item for item in json.loads(files["manifest.json"]) if missing_ref not in item["RepoTags"]]
    files["manifest.json"] = json.dumps(images).encode()
    archive_path.write_bytes(_tar_bytes(files))
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_IMAGE_MISSING" in result.stdout + result.stderr


@pytest.mark.parametrize("field", ["installationContractVersion", "platformPrerequisites"])
def test_old_or_undeclared_platform_contract_requires_rebuild(tmp_path, field):
    root = tmp_path / "release-old"
    manifest = write_complete_package(root)
    if field == "platformPrerequisites":
        del manifest["targetRequirements"][field]
    else:
        del manifest[field]
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_INSTALLATION_CONTRACT_INVALID" in result.stdout + result.stderr


def test_website_target_render_does_not_write_into_frozen_package(tmp_path):
    root = tmp_path / "release-render"
    write_complete_package(root, profile="full")
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    for index, host in enumerate(["192.0.2.10", "192.0.2.20"]):
        control = tmp_path / f"control-{index}"
        control.mkdir()
        command = _functions("Write-Utf8LfNoBomFile", "Write-ReleaseWebsiteDeployControl") + f"""
$Mode='deploy-release'; $publishWebsite=$true
$releaseDir='{root}'; $websiteRuntimeLocal=Join-Path $releaseDir 'website'
$deployControlLocalRoot='{control}'; $ServerHost='{host}'; $BackendPort=48081
$websiteNginxTemplate='{ROOT / 'ops/deploy/int-ruoyi-test/website.nginx.conf'}'
$assignment=$ast.Find({{param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$websiteNginxLocal'}},$true)
Invoke-Expression $assignment.Extent.Text
$block=$ast.EndBlock.Statements | Where-Object {{ $_.Extent.Text.StartsWith('if ($Mode -eq ''deploy-release'' -and $publishWebsite)') }}
if ($null -eq $block) {{ throw 'production Website render block missing' }}
Invoke-Expression $block.Extent.Text
"""
        result = _ps(command)
        assert result.returncode == 0, result.stdout + result.stderr
        assert before == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        rendered = (control / "website/nginx.conf").read_text(encoding="utf-8")
        assert f"{host}:48081" in rendered
        assert "__BACKEND_ORIGIN__" not in rendered


def test_target_environment_render_preserves_package_and_approved_tool_pins(tmp_path):
    root = tmp_path / "release-environment"
    write_complete_package(root, profile="full")
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    before_identity = json.loads(verify(root).stdout)
    for index in (1, 2):
        control = tmp_path / f"control-{index}"
        result = _ps(_functions("Write-Utf8LfNoBomFile", "Get-ReleasePlatformIdentityEnvironmentLines") + f"""
Import-Module '{GOVERNANCE}' -Force
$Component='full'; $deployControlLocalRoot='{control}'
$existingRemoteEnv=@{{DCC_PROJECT_CODE_CODEX_CLI_SHA256='{str(index) * 64}'; SHOWROOM_CODEX_CLI_SHA256='{'a' * 64}'}}
$remoteEnvContent='TARGET_HOST=192.0.2.{index}'
$statements=@($ast.EndBlock.Statements)
$start=-1; $finish=-1
for($i=0;$i -lt $statements.Count;$i++) {{
 if($statements[$i].Extent.Text.StartsWith('$remoteEnvLocal =')) {{ $start=$i }}
 if($statements[$i].Extent.Text.StartsWith('Write-Utf8LfNoBomFile -Path $remoteEnvLocal')) {{ $finish=$i; break }}
}}
if($start -lt 0 -or $finish -lt $start) {{ throw 'production environment write block missing' }}
for($i=$start;$i -le $finish;$i++) {{ Invoke-Expression $statements[$i].Extent.Text }}
""")
        assert result.returncode == 0, result.stdout + result.stderr
        rendered = (control / ".env").read_text(encoding="utf-8")
        assert f"DCC_PROJECT_CODE_CODEX_CLI_SHA256={str(index) * 64}" in rendered
        assert f"SHOWROOM_CODEX_CLI_SHA256={'a' * 64}" in rendered
        assert before == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        after_identity = json.loads(verify(root).stdout)
        assert (after_identity["packageDigest"], after_identity["manifestDigest"]) == (before_identity["packageDigest"], before_identity["manifestDigest"])


def test_website_template_cannot_be_replaced_from_execution_workspace(tmp_path):
    root = tmp_path / "release-template"
    write_complete_package(root, profile="full")
    (root / "website/nginx.template.conf").unlink()
    outside = tmp_path / "workspace-template.conf"
    outside.write_text("server __BACKEND_ORIGIN__;", encoding="utf-8")
    result = _ps(_functions("Write-Utf8LfNoBomFile", "Write-ReleaseWebsiteDeployControl") + f"""
$websiteRuntimeLocal='{root / 'website'}'; $websiteNginxTemplate='{outside}'
$deployControlLocalRoot='{tmp_path / 'control'}'; $websiteNginxLocal=Join-Path $deployControlLocalRoot 'website/nginx.conf'
$ServerHost='192.0.2.1'; $BackendPort=48081
Write-ReleaseWebsiteDeployControl
""")
    assert result.returncode != 0
    assert "PACKAGE_REQUIRED_ARTIFACT_MISSING" in result.stdout + result.stderr
    assert not (tmp_path / "control").exists()


def test_missing_scheduler_payload_does_not_rebuild_or_touch_transport(tmp_path):
    result = _ps(_functions("Copy-SchedulerSmokeRunnerToServer") + f"""
$publishBackend=$true; $schedulerSmokeRunnerLocalDir='{tmp_path / 'missing'}'
function Invoke-SshCommand {{ throw 'UNEXPECTED_TRANSPORT' }}
function Copy-ToServer {{ throw 'UNEXPECTED_TRANSPORT' }}
function New-SchedulerSmokeRunnerPackage {{ throw 'UNEXPECTED_REBUILD' }}
Copy-SchedulerSmokeRunnerToServer
""")
    assert result.returncode != 0
    assert "PACKAGE_REQUIRED_ARTIFACT_MISSING" in result.stdout + result.stderr
    assert "UNEXPECTED_TRANSPORT" not in result.stdout + result.stderr
    assert "UNEXPECTED_REBUILD" not in result.stdout + result.stderr


def test_smoke_build_uses_committed_lock_in_linux_image_before_packaging(tmp_path):
    frontend = application_backend_root().parent / "IntRuoyiFronted"
    result = _ps(_functions("New-SchedulerSmokeRunnerPackage", "New-SchedulerSmokeNpmWrapperContent", "Write-Utf8LfNoBomFile") + f"""
$publishBackend=$true; $frontendDir='{frontend}'; $schedulerSmokeRunnerLocalDir='{tmp_path / 'smoke'}'
$maintenanceReleaseScriptRoot='{ROOT / 'ops/release'}'; $schedulerSmokeFrontendDirectory='/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3'
function Invoke-CheckedCommand {{
 param([string]$FilePath,[string[]]$ArgumentList)
 Write-Output ('CAPTURED_COMMAND=' + (@{{file=$FilePath; arguments=$ArgumentList; shell=[IO.File]::ReadAllText((Join-Path $schedulerSmokeRunnerLocalDir 'yudao-ui-admin-vue3/.prepare-dependencies.sh'),[Text.UTF8Encoding]::new($false))}} | ConvertTo-Json -Depth 6 -Compress))
 throw 'TASK_TEST_CAPTURED_CREATE'
}}
New-SchedulerSmokeRunnerPackage -RuntimeImageId 'sha256:{'a' * 64}'
""")
    assert result.returncode != 0
    assert "TASK_TEST_CAPTURED_CREATE" in result.stderr
    captured = json.loads(next(line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("CAPTURED_COMMAND=")))
    assert captured["file"] == "docker"
    assert captured["arguments"][0] == "create"
    assert f"sha256:{'a' * 64}" in captured["arguments"]
    assert captured["arguments"][-2:] == ["sh", "/inputs/.prepare-dependencies.sh"]
    shell = captured["shell"]
    assert "npm ci --ignore-scripts --no-audit --no-fund" in shell
    assert "chromium.launch" in shell
    assert "tar --sort=name --mtime=@0" in shell
    assert (tmp_path / "smoke/yudao-ui-admin-vue3/package-lock.json").read_bytes() == (ROOT / "ops/release/smoke/package-lock.json").read_bytes()
    assert not (tmp_path / "smoke/yudao-ui-admin-vue3/dependencies.tar").exists()
    assert not (tmp_path / "smoke/yudao-ui-admin-vue3/.prepare-dependencies.sh").exists()


def test_smoke_deploy_generated_commands_use_payload_without_registry_install(tmp_path):
    root = tmp_path / "release-smoke"
    write_complete_package(root)
    result = _ps(_functions("Copy-SchedulerSmokeRunnerToServer") + f"""
$publishBackend=$true; $schedulerSmokeRunnerLocalDir='{root / 'smoke'}'
$PublishTargetName='task'; $RemoteAppDir='/task/runtime'; $remoteSchedulerSmokeRoot='/task/runtime/smoke'
$remoteSchedulerSmokeFrontendDir='/task/runtime/smoke/yudao-ui-admin-vue3'; $remoteSchedulerSmokeBinDir='/task/runtime/smoke/bin'
$remoteSchedulerSmokeNpmWrapper='/task/runtime/smoke/bin/npm'
$script:commands=@()
function Invoke-SshCommand {{ param([string]$Command) $script:commands += $Command }}
function Copy-ToServer {{ param([string]$LocalPath,[string]$RemotePath,[switch]$Recursive) }}
Copy-SchedulerSmokeRunnerToServer
$script:commands | ConvertTo-Json -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    commands = "\n".join(json.loads(result.stdout))
    assert "dependencies.tar" in commands and "tar -xf" in commands
    assert " install " not in commands
    assert " pull " not in commands


@pytest.mark.parametrize(("mode", "profile"), [("deploy-release", "full"), ("build-release", "intruoyi")])
def test_package_only_or_core_workflow_does_not_require_website_source(tmp_path, mode, profile):
    result = _ps(_functions() + f"""
$Mode='{mode}'; $Component='{profile}'; $WebsiteRepo='{tmp_path / 'missing-website-source'}'
$source=[IO.File]::ReadAllText('{SCRIPT}')
$start=$source.IndexOf('$defaultWebsiteRepo =')
$finish=$source.IndexOf('$publishBackend =', $start)
Invoke-Expression $source.Substring($start, $finish-$start)
'WEBSITE_SOURCE_NOT_REQUIRED'
""")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WEBSITE_SOURCE_NOT_REQUIRED" in result.stdout


def test_deploy_initialization_does_not_resolve_application_source_roots(tmp_path):
    result = _ps(_functions() + f"""
$Mode='deploy-release'; $scriptDir='{ROOT / 'ops/deploy'}'
$BackendRepoRoot='{tmp_path / 'missing-backend'}'; $FrontendRepoRoot='{tmp_path / 'missing-frontend'}'
$source=[IO.File]::ReadAllText('{SCRIPT}')
$start=$source.IndexOf('$defaultBackendRepo =')
$finish=$source.IndexOf('$defaultWebsiteRepo =', $start)
Invoke-Expression $source.Substring($start, $finish-$start)
'APPLICATION_SOURCE_NOT_REQUIRED'
""")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "APPLICATION_SOURCE_NOT_REQUIRED" in result.stdout


def test_deploy_report_directory_is_outside_immutable_package(tmp_path):
    root = tmp_path / "release-report"
    write_complete_package(root)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    control = tmp_path / "control"
    result = _ps(_functions("New-SmartReleaseReportDirectory") + f"""
$Mode='deploy-release'; $deployControlLocalRoot='{control}'
New-SmartReleaseReportDirectory -PackagePath '{root}'
""")
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(control).replace("\\", "/") in result.stdout.replace("\\", "/")
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) == before


@pytest.mark.parametrize("path", ["docker-compose.yml", "website/nginx.template.conf"])
def test_empty_required_control_payload_is_rejected(tmp_path, path):
    root = tmp_path / "release-empty"
    manifest = write_complete_package(root, profile="full")
    (root / path).write_bytes(b"")
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_REQUIRED_ARTIFACT_EMPTY" in result.stdout + result.stderr


def test_image_identity_is_derived_from_config_bytes_not_just_its_filename(tmp_path):
    root = tmp_path / "release-config"
    manifest = write_complete_package(root)
    archive_path = root / f"intruoyi-images_{root.name}.tar"
    with tarfile.open(archive_path) as archive:
        files = {entry.name: archive.extractfile(entry).read() for entry in archive}
    config_path = json.loads(files["manifest.json"])[0]["Config"]
    config = json.loads(files[config_path])
    config["config"]["Labels"]["fixture"] = "different-content-same-config-filename"
    files[config_path] = json.dumps(config).encode()
    archive_path.write_bytes(_tar_bytes(files))
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_IMAGE_IDENTITY_MISMATCH" in result.stdout + result.stderr


def test_ops_payload_uses_target_config_without_requiring_empty_package_config_directory(tmp_path):
    root = tmp_path / "release-ops"
    write_complete_package(root)
    result = _ps(_functions("Copy-ReleaseOpsRuntimePackage") + f"""
$opsRuntimeLocalDir='{root / 'ops-runtime'}'; $packageDirectoryName='release-ops'
$remoteReleaseDir='/task/release'
function Invoke-CheckedCommand {{ throw 'INPUT_CONTRACT_PASSED_BEFORE_TRANSPORT' }}
Copy-ReleaseOpsRuntimePackage
""")
    assert result.returncode != 0
    assert "INPUT_CONTRACT_PASSED_BEFORE_TRANSPORT" in result.stdout + result.stderr


def test_scheduler_wrapper_refuses_registry_pull_when_packaged_image_is_missing():
    result = _ps(_functions("New-SchedulerSmokeNpmWrapperContent") + "\n$schedulerSmokeFrontendDirectory='/task/smoke'; New-SchedulerSmokeNpmWrapperContent")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "docker run --rm --pull=never" in result.stdout


@pytest.mark.parametrize("mutation", ["missing", "checksum", "not_readonly", "projection"])
def test_declared_target_preflight_is_part_of_complete_package_contract(tmp_path, mutation):
    root = tmp_path / "release-target-check"
    manifest = write_complete_package(root)
    check = root / "target-preflight/001.preflight.sql"
    check.parent.mkdir()
    check.write_text("-- release-target-preflight: migrationId=001; allowedEnvironments=test,prod,backup\n"
                     "SELECT CASE WHEN COUNT(*)=1 THEN 'TARGET_PREFLIGHT_PASS:001' ELSE 'BLOCKED' END FROM task_probe;\n", encoding="utf-8")
    entry = {"migrationId": "001", "file": "required-sql/001.sql", "type": "data", "requiresTargetPreflight": True,
             "targetPreflight": {"reference": "target-preflight/001.preflight.sql",
                                 "sha256": hashlib.sha256(check.read_bytes()).hexdigest(), "readOnly": True}}
    manifest["requiredSql"] = [entry]
    manifest["database"] = {"schemaMigrations": [copy.deepcopy(entry)]}
    manifest["migrationPlan"] = [copy.deepcopy(entry)]
    if mutation == "missing":
        check.unlink()
    elif mutation == "checksum":
        for item in [entry, manifest["database"]["schemaMigrations"][0], manifest["migrationPlan"][0]]:
            item["targetPreflight"]["sha256"] = "0" * 64
    elif mutation == "not_readonly":
        for item in [entry, manifest["database"]["schemaMigrations"][0], manifest["migrationPlan"][0]]:
            item["targetPreflight"]["readOnly"] = False
    else:
        manifest["migrationPlan"][0]["targetPreflight"]["sha256"] = "0" * 64
    rebind_package(root, manifest)
    result = verify(root)
    assert result.returncode != 0
    assert "PACKAGE_TARGET_PREFLIGHT_INVALID" in result.stdout + result.stderr


@pytest.mark.parametrize("environment", ["test","prod","backup"])
def test_complete_package_rejects_legacy_target_secret_environment_payload(tmp_path, environment):
    root=tmp_path/"release-legacy-env"
    manifest=write_complete_package(root)
    env=root/f"runtime-env/{environment}.env"
    env.parent.mkdir();env.write_text("TASK_TEST_NON_SECRET=fixture\n",encoding="utf-8")
    rebind_package(root,manifest)
    result=verify(root)
    assert result.returncode!=0
    assert "PACKAGE_CONTENT_FORBIDDEN" in result.stdout+result.stderr


def oci_smoke_package(root, mutation=None):
    manifest = write_complete_package(root)
    archive_path = root / f"intruoyi-images_{root.name}.tar"
    with tarfile.open(archive_path) as archive:
        files = {entry.name: archive.extractfile(entry).read() for entry in archive}
    docker_entries = json.loads(files["manifest.json"])
    smoke = next(e for e in docker_entries if SMOKE_IMAGE in e["RepoTags"])
    old_config = smoke["Config"]
    config = files.pop(old_config)
    config_digest = hashlib.sha256(config).hexdigest()
    config_path = "blobs/sha256/" + config_digest
    layer = b"TC14-real-bytes-contract-layer"
    layer_digest = hashlib.sha256(layer).hexdigest()
    layer_path = "blobs/sha256/" + layer_digest
    descriptor_body = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                       "config": {"digest": "sha256:" + config_digest, "size": len(config)},
                       "layers": [{"digest": "sha256:" + layer_digest, "size": len(layer)}]}
    if mutation == "wrong-config-link":
        descriptor_body["config"]["digest"] = "sha256:" + "f" * 64
    if mutation == "wrong-layer-link":
        descriptor_body["layers"][0]["digest"] = "sha256:" + "e" * 64
    blob = json.dumps(descriptor_body).encode()
    descriptor_digest = hashlib.sha256(blob).hexdigest()
    descriptor_path = "blobs/sha256/" + descriptor_digest
    descriptor = {"digest": "sha256:" + descriptor_digest, "size": len(blob),
                  "mediaType": descriptor_body["mediaType"],
                  "annotations": {"io.containerd.image.name": SMOKE_IMAGE}}
    files[config_path] = config
    files[layer_path] = layer
    files[descriptor_path] = blob
    files["oci-layout"] = b'{"imageLayoutVersion":"1.0.0"}'
    if mutation == "forged-descriptor":
        files[descriptor_path] = blob + b" "
    if mutation == "config-bytes":
        files[config_path] = config + b" "
    if mutation == "layer-bytes":
        files[layer_path] = b"X" * len(layer)
    if mutation == "missing-blob":
        files.pop(layer_path)
    if mutation == "descriptor-size":
        descriptor["size"] += 1
    if mutation == "tag-binding":
        descriptor["annotations"]["io.containerd.image.name"] = "other:tag"
    files["index.json"] = json.dumps({"schemaVersion":2, "manifests":[descriptor]}).encode()
    smoke.update(Config=config_path, Layers=[layer_path])
    files["manifest.json"] = json.dumps(docker_entries).encode()
    archive_path.write_bytes(_tar_bytes(files))
    next(i for i in manifest["runtimeImages"] if i["name"] == "scheduler-smoke")["id"] = "sha256:" + descriptor_digest
    rebind_package(root, manifest)
    return manifest


def test_containerd_archive_identity_requires_verified_descriptor_chain(tmp_path):
    root = tmp_path / "release-oci"
    oci_smoke_package(root)
    result = verify(root)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("oci", [False, True])
def test_verified_image_content_preserves_build_identity_and_returns_target_config(tmp_path, oci):
    root = tmp_path / "release-content"
    manifest = oci_smoke_package(root) if oci else write_complete_package(root, profile="full", only_office=True)
    result = verify(root)
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(result.stdout)
    contents = value["verifiedImageContent"]
    assert len(contents) == len(manifest["runtimeImages"])
    with tarfile.open(root / f"intruoyi-images_{root.name}.tar") as archive:
        images = json.load(archive.extractfile("manifest.json"))
        for item in contents:
            build = next(i for i in manifest["runtimeImages"] if i["name"] == item["name"])
            entry = next(i for i in images if build["reference"] in i["RepoTags"])
            config_bytes = archive.extractfile(entry["Config"]).read()
            config = json.loads(config_bytes)
            assert item["reference"] == build["reference"]
            assert item["buildImageId"] == build["id"]
            assert item["configDigest"] == "sha256:" + hashlib.sha256(config_bytes).hexdigest()
            assert item["platform"] == {"os": "linux", "architecture": "amd64"}
            assert item["rootfsDiffIds"] == config["rootfs"]["diff_ids"]
            assert item["descriptorDigest"] == (build["id"] if oci and item["name"] == "scheduler-smoke" else None)


@pytest.mark.parametrize("mutation", [
    "forged-descriptor", "wrong-config-link", "wrong-layer-link", "config-bytes",
    "layer-bytes", "missing-blob", "descriptor-size", "tag-binding",
])
def test_containerd_archive_rejects_unverified_identity_chain(tmp_path, mutation):
    root = tmp_path / "release-oci"
    oci_smoke_package(root, mutation)
    result = verify(root)
    assert result.returncode != 0, mutation
    assert "PACKAGE_IMAGE_" in result.stdout + result.stderr
