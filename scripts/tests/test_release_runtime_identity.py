"""T5: production PowerShell against the task's real, isolated classic engine."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from test_release_full_package_contract import SCRIPT, GOVERNANCE, _functions, _ps
from test_scheduler_smoke_linux_payload_integration import ps as long_ps
from release_test_runtime import classic_configuration, classic_runtime, runtime_settings, official_archive

_SETTINGS = runtime_settings()
ENGINE = classic_configuration().container_id
TASK = _SETTINGS.task
PREFIX = _SETTINGS.prefix + 't5-'
TAG = PREFIX + 'fixed'
BASE = "sha256:ab853f51b03036cd52e74771c2dd07ee1471c408645048e928af67db6beae6d7"
NAMES = ["backend", "frontend", "scheduler-smoke", "website", "onlyoffice"]


def docker(*args, input=None):
    result = subprocess.run(["docker", "exec", "-i", ENGINE, "docker", *args], input=input,
                            capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture(scope="module")
def engine():
    assert classic_runtime().container_id == ENGINE
    official_archive()
    assert docker("info", "--format", "{{.Driver}}") == "overlay2"
    existing = docker("ps", "-a", "--format", "{{.Names}}").splitlines()
    assert not any(n.startswith(PREFIX) or n.startswith("intruoyi-") for n in existing), existing
    seed = PREFIX + "seed"
    docker("create", "--name", seed, "--network", "none", "--label", f"codex.task={TASK}", BASE, "sleep", "600")
    good = docker("commit", "--change", "LABEL codex.t5.variant=good", seed, PREFIX + "good:fixed")
    wrong = docker("commit", "--change", "LABEL codex.t5.variant=wrong", seed, PREFIX + "wrong:fixed")
    docker("rm", seed)
    refs = {name: PREFIX + name + ":fixed" for name in NAMES}
    refs.update(backend="intruoyi-backend:" + TAG, frontend="intruoyi-frontend:" + TAG)
    current_refs = docker("images", "--format", "{{.Repository}}:{{.Tag}}").splitlines()
    assert not any(r in current_refs for r in refs.values()), current_refs
    for ref in refs.values():
        docker("tag", good, ref)
    yield {"refs": refs, "good": good, "wrong": wrong}
    leftovers = docker("ps", "-a", "--format", "{{.Names}}").splitlines()
    assert not any(n.startswith("intruoyi-") or n.startswith(PREFIX) for n in leftovers), leftovers
    for ref in refs.values():
        docker("image", "rm", ref)
    docker("image", "rm", PREFIX + "wrong:fixed")
    docker("image", "rm", PREFIX + "good:fixed")


def context(engine, website=True, office=True):
    names = NAMES[:3] + (["website"] if website else []) + (["onlyoffice"] if office else [])
    actual = json.loads(docker("image", "inspect", engine["good"]))[0]
    return [{"name": n, "reference": engine["refs"][n],
             "buildImageId": "sha256:" + "a" * 64, "descriptorDigest": "sha256:" + "a" * 64,
             "configDigest": engine["good"], "platform": {"os": actual["Os"], "architecture": actual["Architecture"]},
             "rootfsDiffIds": actual["RootFS"]["Layers"]} for n in names]


def production(engine, action, website=True, office=True, extra="", files_container=None):
    content = context(engine, website, office)
    encoded = base64.b64encode(json.dumps(content).encode()).decode()
    names = ["Assert-ReleaseSelectedImagesLoaded", "Assert-RemoteActualApplicationImages",
             "Get-ReleaseTargetImageIdentities", "Assert-RemoteWebsitePayloadIdentity",
             "Invoke-ReleaseRuntimeVerificationCheck", "ConvertTo-ShellSingleQuotedLiteral",
             "Invoke-ProcessCaptureWithInput", "ConvertTo-ProcessArgumentString", "ConvertTo-ReleaseFileSha256Hex",
             "Assert-RemoteBackendHealthStatus"]
    transport = f"@('exec','-i','{ENGINE}','sh','-s')"
    if files_container:
        transport = f"@('exec','-i','{ENGINE}','docker','exec','-i','{files_container}','sh','-s')"
    return _ps(_functions(*names) + f"""
$releaseConsoleEncoding=[Text.UTF8Encoding]::new($false)
[Console]::InputEncoding=$releaseConsoleEncoding;[Console]::OutputEncoding=$releaseConsoleEncoding;$OutputEncoding=$releaseConsoleEncoding
$parsed=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$script:ReleaseVerifiedImageContent=@($parsed)
$script:ReleaseRuntimeImages=@($parsed|ForEach-Object{{[pscustomobject]@{{name=$_.name;reference=$_.reference;id=$_.buildImageId;sizeBytes=1}}}})
$publishBackend=$true;$publishFrontend=$true;$publishWebsite=${str(website).lower()};$IncludeOnlyOffice=${str(office).lower()}
$packageDirectoryName='{TAG}'
$script:ReleaseRuntimeVerification=[ordered]@{{images=@();loadedImages=@();website=$null;checks=@()}}
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 $r=Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList {transport} -StandardInput ($Command -replace "`r`n","`n")
 @{{Ok=($r.ExitCode -eq 0);Output=($r.StdOut+$r.StdErr)}}
}}
function Invoke-SshCommand {{param($Command) $r=Invoke-SshCapture -Command $Command;if(-not $r.Ok){{throw $r.Output}}}}
{extra}
try{{{action};$outcome='passed'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;evidence=$script:ReleaseRuntimeVerification}}|ConvertTo-Json -Depth 15 -Compress
""")


def observed(result):
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("website,office", [(False, False), (False, True), (True, False), (True, True)])
def test_real_classic_loaded_images_accept_verified_config_not_build_descriptor(engine, website, office):
    value = observed(production(engine, "Assert-ReleaseSelectedImagesLoaded", website, office))
    assert value["outcome"] == "passed", value
    rows = value["evidence"]["loadedImages"]
    assert len(rows) == 3 + website + office
    assert all(r["expectedImageId"] == r["actualImageId"] == engine["good"] for r in rows)
    assert all(r["buildImageId"] != r["actualImageId"] for r in rows)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("fault", ["missing", "retagged"])
def test_real_loaded_images_reject_each_missing_or_same_tag_different_image(engine, name, fault):
    ref = engine["refs"][name]
    if fault == "missing":
        docker("image", "rm", ref)
    else:
        docker("tag", engine["wrong"], ref)
    try:
        value = observed(production(engine, "Assert-ReleaseSelectedImagesLoaded"))
        assert f"RELEASE_IMAGE_NOT_LOADED: {name}" in value["outcome"], value
    finally:
        docker("tag", engine["good"], ref)


@pytest.mark.parametrize("fault_name", [None, "backend", "frontend", "website", "onlyoffice"])
@pytest.mark.parametrize("fault", ["stale", "missing"])
def test_real_running_containers_require_every_selected_content_identity(engine, fault_name, fault):
    created = []
    try:
        for name in ["backend", "frontend", "website", "onlyoffice"]:
            if name == fault_name and fault == "missing":
                continue
            ref = engine["refs"][name]
            if name == fault_name:
                docker("tag", engine["wrong"], ref)
            container = "intruoyi-" + name
            docker("run", "-d", "--name", container, "--network", "none", "--label", f"codex.task={TASK}", ref, "sleep", "600")
            created.append(container)
            # The tag now points to the correct archive, but a stale container
            # keeps the different immutable Image ID despite Config.Image matching.
            docker("tag", engine["good"], ref)
        value = observed(production(engine, "Assert-RemoteActualApplicationImages"))
        if fault_name:
            assert f"RELEASE_RUNTIME_IMAGE_MISMATCH: {fault_name}" in value["outcome"], value
        else:
            assert value["outcome"] == "passed", value
            assert len(value["evidence"]["images"]) == 4
            assert all(r["expectedImageId"] == r["actualImageId"] == engine["good"] for r in value["evidence"]["images"])
    finally:
        for container in created:
            docker("rm", "-f", container)
        for ref in engine["refs"].values():
            docker("tag", engine["good"], ref)


def test_runtime_identity_validation_is_after_website_start():
    source = SCRIPT.read_text(encoding="utf-8")
    start = source.index("    $runtimeServices = @()")
    body = source[start:source.index("    Info 'Waiting for remote HTTP readiness'", start)]
    assert body.index("docker compose up -d --force-recreate --no-deps --pull never website") < body.index("Assert-RemoteActualApplicationImages")


@pytest.mark.parametrize("fault", [None, "missing", "changed", "extra", "file-link", "directory-link", "config"])
def test_real_website_payload_requires_exact_files_and_rendered_configuration(engine, tmp_path, fault):
    name = PREFIX + "files"
    docker("run", "-d", "--name", name, "--network", "none", "--label", f"codex.task={TASK}", engine["good"], "sleep", "600")
    payload = {"dist/index.html": b"<html>frozen release</html>", "dist/assets/app.js": b"console.log('release');", "nginx.conf": b"server { listen 80; }\n"}
    configuration = tmp_path / "nginx.conf"
    configuration.write_bytes(payload["nginx.conf"])
    artifacts = [{"path": "website/" + key, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                 for key, value in payload.items() if key.startswith("dist/")]
    encoded = base64.b64encode(json.dumps(artifacts).encode()).decode()
    setup = "from pathlib import Path\nimport base64\nr=Path('/task-website')\nr.mkdir()\n"
    for key, value in payload.items():
        setup += f"p=r/{key!r};p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode({base64.b64encode(value).decode()!r}))\n"
    setup += {
        None: "", "missing": "(r/'dist/assets/app.js').unlink()\n",
        "changed": "(r/'dist/assets/app.js').write_bytes(b'changed')\n",
        "extra": "(r/'dist/stale.js').write_bytes(b'old')\n",
        "file-link": "(r/'dist/index.html').unlink();(r/'dist/index.html').symlink_to('/etc/hostname')\n",
        "directory-link": "(r/'dist/outside').symlink_to('/etc',target_is_directory=True)\n",
        "config": "(r/'nginx.conf').write_bytes(b'wrong config')\n",
    }[fault]
    try:
        docker("exec", "-i", name, "python3", "-", input=setup)
        value = observed(production(engine, "Assert-RemoteWebsitePayloadIdentity", files_container=name, extra=f"""
$remoteWebsiteDir='/task-website';$websiteNginxLocal='{configuration.as_posix()}'
$items=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$releasePackageIntegrity=@{{artifacts=@($items)}}
"""))
        if fault:
            assert "RELEASE_WEBSITE_CONTENT_MISMATCH" in value["outcome"], value
            assert value["evidence"]["website"]["status"] == "failed"
        else:
            assert value["outcome"] == "passed", value
            evidence = value["evidence"]["website"]
            assert evidence["status"] == "passed" and len(evidence["actual"]) == 3
            assert evidence["actual"] == evidence["expected"]
    finally:
        docker("rm", "-f", name)


@pytest.mark.parametrize("failure", [False, True])
def test_health_contract_has_independent_structured_success_and_failure(engine, failure):
    action = "Invoke-ReleaseRuntimeVerificationCheck -Name 'backend-health' -Action { " + ("throw 'HTTP 503'" if failure else "$null=1") + " }"
    value = observed(production(engine, action))
    row = value["evidence"]["checks"][0]
    assert row["name"] == "backend-health"
    assert row["status"] == ("failed" if failure else "passed")
    if failure:
        assert "HTTP 503" in value["outcome"] and row["error"] == "HTTP 503"
    else:
        assert value["outcome"] == "passed"


def test_wrong_archive_platform_is_rejected_before_image_inspection(engine):
    value = observed(production(engine, "Assert-ReleaseSelectedImagesLoaded", extra="$script:ReleaseVerifiedImageContent[0].platform.architecture='arm64'"))
    assert "RELEASE_TARGET_IMAGE_PLATFORM_MISMATCH: backend" in value["outcome"], value


@pytest.mark.parametrize("reply", ['{"status":"UP"}', '{"status":"DOWN"}', '{}', 'not-json'])
def test_backend_health_requires_up_status_not_only_http_success(engine, reply):
    encoded = base64.b64encode(reply.encode()).decode()
    value = observed(production(engine,
        "Invoke-ReleaseRuntimeVerificationCheck -Name 'backend-health' -Action { Assert-RemoteBackendHealthStatus }",
        extra=f"""
$BackendPort=48080
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 @{{Ok=$true;Output=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))}}
}}
"""))
    if reply == '{"status":"UP"}':
        assert value["outcome"] == "passed", value
        assert value["evidence"]["checks"][0]["actual"]["status"] == "UP"
    else:
        assert "RELEASE_BACKEND_HEALTH_NOT_UP" in value["outcome"], value
        assert value["evidence"]["checks"][0]["status"] == "failed"


@pytest.mark.parametrize("tool", ["find", "stat", "sha256sum", "base64"])
def test_website_observation_propagates_each_tool_failure(engine, tmp_path, tool):
    name=PREFIX+"tool-failure"
    docker("run","-d","--name",name,"--network","none","--label",f"codex.task={TASK}",engine["good"],"sleep","600")
    config=tmp_path/"nginx.conf";config.write_text("server {}",encoding="utf-8")
    setup=f"""
from pathlib import Path
r=Path('/task-website');r.mkdir();(r/'dist').mkdir();(r/'dist/index.html').write_text('index');(r/'nginx.conf').write_text('server {{}}')
b=Path('/task-tools');b.mkdir();p=b/{tool!r};p.write_text('#!/bin/sh\\nexit 73\\n');p.chmod(0o755)
"""
    try:
        docker("exec","-i",name,"python3","-",input=setup)
        extra=f"""
$remoteWebsiteDir='/task-website';$websiteNginxLocal='{config.as_posix()}'
$releasePackageIntegrity=@{{artifacts=@(@{{path='website/dist/index.html';bytes=5;sha256='1'}})}}
$originalTransport=(Get-Item function:Invoke-SshCapture).ScriptBlock
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode) & $originalTransport -Command ('export PATH=/task-tools:$PATH' + "`n" + $Command) -IgnoreExitCode}}
"""
        value=observed(production(engine,"Assert-RemoteWebsitePayloadIdentity",files_container=name,extra=extra))
        assert "remote content observation failed" in value["outcome"],value
        assert value["evidence"]["website"]["status"]=="unknown"
    finally:
        docker("rm","-f",name)


@pytest.mark.parametrize("fault", ["empty", "duplicate", "foreign-build"])
def test_verified_image_content_is_mandatory_and_bound_without_build_id_fallback(engine, fault):
    mutation = {
        "empty": "$script:ReleaseVerifiedImageContent=@()",
        "duplicate": "$script:ReleaseVerifiedImageContent[1]=$script:ReleaseVerifiedImageContent[0]",
        "foreign-build": "$script:ReleaseVerifiedImageContent[0].buildImageId='sha256:'+('b'*64)",
    }[fault]
    value = observed(production(engine, "Assert-ReleaseSelectedImagesLoaded", extra=mutation))
    assert "RELEASE_IMAGE_IDENTITY_REQUIRED" in value["outcome"], value


def test_unselected_website_and_office_have_no_running_identity_claim(engine):
    created=[]
    try:
        for component in ("backend", "frontend"):
            name="intruoyi-"+component
            docker("run", "-d", "--name", name, "--network", "none", "--label", f"codex.task={TASK}", engine["refs"][component], "sleep", "600")
            created.append(name)
        value=observed(production(engine,"Assert-RemoteActualApplicationImages",website=False,office=False))
        assert value["outcome"]=="passed",value
        assert [r["name"] for r in value["evidence"]["images"]]==["backend","frontend"]
    finally:
        for name in created:
            docker("rm","-f",name)


def test_real_containerd_archive_identity_flows_into_classic_loaded_smoke_verification(engine):
    archive = official_archive()
    archive_path = base64.b64encode(archive.as_posix().encode('utf-8')).decode()
    with archive.open("rb") as stream:
        before = hashlib.file_digest(stream, "sha256").hexdigest()
    assert before == "b6a43d0d5f3ea034d90249bddae37e278e28bbb702168867317420434e8ec716"
    build_id = "sha256:aa88ecce96d1abff3797127aa1b22171134b4f217b99e81f0c01b2c1b1bd2992"
    reference = "mcr.microsoft.com/playwright:i-was-a-digest"
    result = long_ps(f"""
Import-Module '{GOVERNANCE}' -Force
$verified=& (Get-Module ReleasePackageGovernance) {{
 $archive=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{archive_path}'));$paths=@(& tar -tf $archive)
 if($LASTEXITCODE -ne 0){{throw 'archive list failed'}}
 $parsed=(& tar -xOf $archive manifest.json) -join "`n" | ConvertFrom-Json
 if($LASTEXITCODE -ne 0){{throw 'archive manifest failed'}}
 $image=@($parsed|Where-Object{{@($_.RepoTags) -ccontains '{reference}'}})
 if($image.Count -ne 1){{throw 'reference missing'}}
 Assert-ReleaseArchiveImageIdentity -ArchivePath $archive -ArchivePaths $paths -ArchiveImage $image[0] -Identity @{{name='scheduler-smoke';reference='{reference}';id='{build_id}'}}
}}
$verified|ConvertTo-Json -Depth 10 -Compress
""", timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    verified = json.loads(result.stdout)
    assert verified["buildImageId"] == verified["descriptorDigest"] == build_id
    assert verified["configDigest"] == BASE
    assert verified["rootfsDiffIds"] == json.loads(docker("image", "inspect", BASE))[0]["RootFS"]["Layers"]
    encoded = base64.b64encode(json.dumps(verified).encode()).decode()
    value = observed(production(engine, "Assert-ReleaseSelectedImagesLoaded", extra=f"""
$real=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$script:ReleaseVerifiedImageContent[2]=$real
$script:ReleaseRuntimeImages[2]=[pscustomobject]@{{name=$real.name;reference=$real.reference;id=$real.buildImageId;sizeBytes=1}}
"""))
    assert value["outcome"] == "passed", value
    smoke = next(row for row in value["evidence"]["loadedImages"] if row["name"] == "scheduler-smoke")
    assert smoke["actualImageId"] == smoke["expectedImageId"] == BASE
    assert smoke["buildImageId"] == build_id != BASE
    with archive.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == before
