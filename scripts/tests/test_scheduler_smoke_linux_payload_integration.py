"""TC-14: real, offline Linux smoke payload from the production preparer.

Requires the exact official image locally and an explicit task-owned artifact root.
No mocks, registry/image substitution, shared business resources, or skipped gates.
Other application components in the governance envelope are format fixtures; only
the smoke image and smoke payload are real, and this is not an application release.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import uuid

import pytest

from test_release_full_package_contract import (
    ROOT, SCRIPT, GOVERNANCE, SMOKE_IMAGE, complete_package_payload,
)
from release_test_runtime import application_backend_root

TASK = "20260925-full-package-release-refactor"


def run(args, *, timeout=120, input=None):
    result = subprocess.run(args, input=input, capture_output=True, text=True,
                            encoding="utf-8", errors="strict", timeout=timeout)
    assert result.returncode == 0, (
        f"Command failed ({result.returncode}): {args[0:3]}\n"
        f"{result.stdout}\n{result.stderr}"
    )
    return result


def ps(script, *, timeout=600):
    prefix = """
$ErrorActionPreference='Stop'
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
"""
    encoded = base64.b64encode((prefix + script).encode("utf-16le")).decode()
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=timeout,
    )


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def facts(path):
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def production_functions(names):
    requested = ",".join("'" + name + "'" for name in names)
    return f"""
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{SCRIPT}',[ref]$tokens,[ref]$errors)
if ($errors.Count) {{ throw 'production script syntax error' }}
foreach($name in @({requested})) {{
 $fn=$ast.Find({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name}},$true)
 if ($null -eq $fn) {{ throw "Missing production function: $name" }}
 Invoke-Expression $fn.Extent.Text
}}
"""


@pytest.fixture(scope="module")
def prepared():
    value = os.environ.get("RELEASE_TEST_SMOKE_PAYLOAD_ROOT")
    assert value, "RELEASE_TEST_SMOKE_PAYLOAD_ROOT is required; no shared cache default"
    cache = Path(value)
    assert cache.is_absolute(), "smoke payload root must be absolute"
    assert cache.name == "smoke-payload" and cache.parent.name == "full-package-release-refactor", (
        "smoke payload root must be the explicitly assigned task cache"
    )
    root = cache / ("integration-" + uuid.uuid4().hex)
    root.mkdir(parents=True)
    image = json.loads(run(["docker", "image", "inspect", SMOKE_IMAGE]).stdout)[0]
    assert image["Os"] == "linux" and image["Architecture"] == "amd64"
    assert image["Id"].startswith("sha256:")
    receipt_path = cache.parent / "image/final-local-image-identity.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["officialTag"] == SMOKE_IMAGE
    assert receipt["dockerImageId"] == image["Id"]
    assert receipt["configAndAllLayerBytesMatchOfficial"] is True
    frontend = application_backend_root().parent / "IntRuoyiFronted"
    for filename in ("smart-scheduling-smoke-real-flow.e2e.js",
                     "smart-scheduling-smoke-real-flow-static.spec.js"):
        assert (frontend / "tests/e2e" / filename).is_file(), filename
    payload = root / "smoke"
    names = ["Fail", "Info", "Remove-SshNoise", "Write-Utf8LfNoBomFile",
             "Invoke-ProcessCapture", "Invoke-CheckedCommand",
             "New-SchedulerSmokeNpmWrapperContent", "New-SchedulerSmokeRunnerPackage"]
    script = production_functions(names) + f"""
$publishBackend=$true
$frontendDir='{frontend.as_posix()}'
$schedulerSmokeRunnerLocalDir='{payload.as_posix()}'
$maintenanceReleaseScriptRoot='{(ROOT / "ops/release").as_posix()}'
$schedulerSmokeFrontendDirectory='/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3'
New-SchedulerSmokeRunnerPackage -RuntimeImageId '{image["Id"]}'
"""
    (root / "prepare.ps1").write_text(script, encoding="utf-8")
    result = ps(script)
    (root / "prepare.stdout.log").write_text(result.stdout, encoding="utf-8")
    (root / "prepare.stderr.log").write_text(result.stderr, encoding="utf-8")
    json_write(root / "preparation-evidence.json", {
        "task": TASK, "officialImage": SMOKE_IMAGE, "imageId": image["Id"],
        "repoDigests": image.get("RepoDigests", []), "officialSource": receipt,
        "productionScript": {"path": str(SCRIPT), **facts(SCRIPT)},
        "exitCode": result.returncode,
    })
    assert result.returncode == 0, result.stdout + result.stderr + f"\nEvidence: {root}"
    work = payload / "yudao-ui-admin-vue3"
    assert (work / "dependencies.tar").stat().st_size > 0
    for filename in ("package.json", "package-lock.json"):
        assert (work / filename).read_bytes() == (ROOT / "ops/release/smoke" / filename).read_bytes()
    return {"root": root, "payload": payload, "work": work, "image": image}


OFFLINE_JS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const lock = require('./package-lock.json');
const pkg = require('./package.json');
const checked = [];
for (const [name, entry] of Object.entries(lock.packages)) {
  if (!name) continue;
  if (entry.os && !entry.os.includes(process.platform)) {
    assert.equal(entry.optional, true, name + ' unsupported required dependency');
    continue;
  }
  const installed = require('./' + name + '/package.json');
  assert.equal(installed.version, entry.version, name);
  checked.push({name, version: installed.version});
}
assert.equal(pkg.devDependencies.playwright, '1.60.0');
assert.equal(pkg.devDependencies.xlsx, '0.18.5');
const xlsx = require('xlsx');
const {chromium} = require('playwright');
const rows = [['task','quantity'], ['TC-14', 17], ['\u79bb\u7ebf\u9a8c\u8bc1', 3]];
const workbook = xlsx.utils.book_new();
xlsx.utils.book_append_sheet(workbook, xlsx.utils.aoa_to_sheet(rows), 'proof');
const bytes = xlsx.write(workbook, {bookType:'xlsx', type:'buffer'});
const restored = xlsx.read(bytes, {type:'buffer'});
assert.deepEqual(xlsx.utils.sheet_to_json(restored.Sheets.proof, {header:1}), rows);
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();
    await page.setContent('<title>TC-14 offline</title><button>ready</button>');
    assert.equal(await page.title(), 'TC-14 offline');
    await page.getByRole('button', {name:'ready'}).click();
    console.log(JSON.stringify({
      status:'PASS', platform:process.platform, architecture:process.arch,
      playwright:require('playwright/package.json').version, xlsx:xlsx.version,
      checkedDependencies:checked, chromiumVersion:browser.version(),
      executablePath:chromium.executablePath(), xlsxRoundTripBytes:bytes.length,
      nonLoopbackInterfaces:Object.keys(os.networkInterfaces()).filter(n=>n!=='lo')
    }));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error); process.exitCode=1});
"""


def test_production_smoke_payload_runs_real_libraries_and_chromium_without_network(prepared):
    root, work, image = prepared["root"], prepared["work"], prepared["image"]
    (root / "offline-check.js").write_text(OFFLINE_JS, encoding="utf-8")
    name = "release-fullpkg-8bea35-smoke-" + uuid.uuid4().hex[:12]
    created = False
    try:
        run(["docker", "create", "--name", name, "--label", f"codex.task={TASK}",
             "--pull=never", "--network=none",
             "--mount", f"type=bind,source={work},target=/inputs,readonly",
             "--mount", f"type=bind,source={root / 'offline-check.js'},target=/check.js,readonly",
             image["Id"], "sh", "-lc",
             "set -eu; mkdir /work; cp /inputs/package.json /inputs/package-lock.json /check.js /work/; "
             "tar -xf /inputs/dependencies.tar -C /work; cd /work; node check.js"])
        created = True
        identity = json.loads(run(["docker", "inspect", name]).stdout)[0]
        assert identity["Image"] == image["Id"]
        assert identity["HostConfig"]["NetworkMode"] == "none"
        assert not identity["HostConfig"].get("PortBindings")
        result = run(["docker", "start", "--attach", name], timeout=120)
        state = json.loads(run(["docker", "inspect", name]).stdout)[0]["State"]
        assert state["ExitCode"] == 0, result.stdout + result.stderr
        output = json.loads(result.stdout.strip())
        assert output["status"] == "PASS"
        assert output["nonLoopbackInterfaces"] == []
        assert len(output["checkedDependencies"]) == 11
        json_write(root / "offline-evidence.json", {
            **output, "container": name, "actualImageId": identity["Image"],
            "networkMode": identity["HostConfig"]["NetworkMode"],
            "containerExitCode": state["ExitCode"],
            "dependencies": facts(work / "dependencies.tar"),
            "packageLock": facts(work / "package-lock.json"),
        })
    finally:
        if created:
            run(["docker", "rm", name])


def bind_manifest(root, manifest):
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            entries.append({"path": path.relative_to(root).as_posix(), **facts(path)})
    manifest["artifacts"] = entries
    manifest["packageDigest"] = hashlib.sha256("".join(
        f"{a['path']}\t{a['bytes']}\t{a['sha256']}\n" for a in entries
    ).encode()).hexdigest()
    json_write(root / "manifest.json", manifest)


def govern(root):
    return ps(f"Import-Module '{GOVERNANCE}' -Force; "
              f"Test-ReleasePackageIntegrity -PackagePath '{root.as_posix()}' | "
              "ConvertTo-Json -Depth 12 -Compress", timeout=300)


def test_real_smoke_archive_bytes_are_bound_by_package_governance(prepared):
    root, image = prepared["root"], prepared["image"]
    saved = root / "official-smoke-image.tar"
    # Saving the verified local tag retains its official reference in manifest.json.
    current = json.loads(run(["docker", "image", "inspect", SMOKE_IMAGE]).stdout)[0]
    assert current["Id"] == image["Id"], "official tag changed after payload preparation"
    run(["docker", "save", "--output", str(saved), SMOKE_IMAGE], timeout=300)
    package = root / "release-tc14-smoke"
    package.mkdir()
    files, metadata = complete_package_payload(package.name)
    archive_name = f"intruoyi-images_{package.name}.tar"
    fixture_archive = files.pop(archive_name)
    for path, data in files.items():
        if path.startswith("smoke/"):
            continue
        target = package / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    shutil.copytree(prepared["payload"], package / "smoke")
    with tarfile.open(saved) as actual, tarfile.open(fileobj=io.BytesIO(fixture_archive)) as fixture:
        actual_manifest = json.load(actual.extractfile("manifest.json"))
        assert len(actual_manifest) == 1
        assert SMOKE_IMAGE in actual_manifest[0]["RepoTags"]
        fixture_manifest = json.load(fixture.extractfile("manifest.json"))
        other = [e for e in fixture_manifest if SMOKE_IMAGE not in e["RepoTags"]]
        referenced = {e["Config"] for e in other}
        with tarfile.open(package / archive_name, "w") as combined:
            for entry in actual:
                if entry.name == "manifest.json":
                    continue
                combined.addfile(entry, actual.extractfile(entry) if entry.isfile() else None)
            for entry in fixture:
                if entry.name in referenced:
                    combined.addfile(entry, fixture.extractfile(entry))
            data = json.dumps(other + actual_manifest).encode()
            header = tarfile.TarInfo("manifest.json")
            header.size = len(data)
            combined.addfile(header, io.BytesIO(data))
    for item in metadata["runtimeImages"]:
        if item["name"] == "scheduler-smoke":
            item.update(id=image["Id"], sizeBytes=image["Size"])
    manifest = {
        "releaseTag": package.name, "packageId": package.name, "publishScope": "app-release",
        **metadata,
        "sourceRoots": [
            {"rootRole": role, "normalizedRoot": f"d:/fixture/{role}",
             "approvedCommit": commit * 40, "commit": commit * 40, "dirty": False}
            for role, commit in [("maintenance", "a"), ("application", "b")]
        ],
        "sourceRoles": [
            {"sourceRole": role, "rootRole": owner, "relativePath": path, "commit": commit * 40}
            for role, owner, path, commit in [
                ("maintenance", "maintenance", ".", "a"),
                ("backend", "application", "IntRuoyiBackend", "b"),
                ("frontend", "application", "IntRuoyiFronted", "b")]
        ],
    }
    bind_manifest(package, manifest)
    result = govern(package)
    (root / "governance.stdout.log").write_text(result.stdout, encoding="utf-8")
    (root / "governance.stderr.log").write_text(result.stderr, encoding="utf-8")
    evidence = {
        "officialReference": SMOKE_IMAGE, "actualImageId": image["Id"],
        "sourceArchive": facts(saved), "packagedArchive": facts(package / archive_name),
        "dependencies": facts(package / "smoke/yudao-ui-admin-vue3/dependencies.tar"),
        "packageDigest": manifest["packageDigest"], "manifestDigest": digest(package / "manifest.json"),
        "governanceExitCode": result.returncode,
        "scope": "real smoke only; other application components are format fixtures",
    }
    json_write(root / "package-evidence.json", evidence)
    assert result.returncode == 0, result.stdout + result.stderr + f"\nEvidence: {root}"
    integrity = json.loads(result.stdout)
    assert integrity["packageDigest"] == manifest["packageDigest"]
    assert integrity["manifestDigest"] == digest(package / "manifest.json")
    # In-place mutations keep the signed byte list unchanged and must fail.
    for path in (package / archive_name, package / "smoke/yudao-ui-admin-vue3/dependencies.tar"):
        original_size = path.stat().st_size
        try:
            with path.open("ab") as stream:
                stream.write(b"TC14-TAMPER")
            assert govern(package).returncode != 0, f"accepted changed bytes: {path.name}"
        finally:
            with path.open("r+b") as stream:
                stream.truncate(original_size)
        hidden = path.with_suffix(path.suffix + ".tc14-hidden")
        path.rename(hidden)
        try:
            assert govern(package).returncode != 0, f"accepted missing archive: {path.name}"
        finally:
            hidden.rename(path)
    assert govern(package).returncode == 0
