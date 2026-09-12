"""Execute the production cleanup function in Windows PowerShell 5.1."""

import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/deploy/publish-int-ruoyi.ps1"
POWERSHELL = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"


def ps_string(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


@pytest.fixture
def package():
    fixture_parent = ROOT / "doc/tasks/one-button-app-release-20260911/tmp"
    fixture_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ps51-cleanup-", dir="\\\\?\\" + str(fixture_parent)) as fixture:
        cache = Path(fixture.removeprefix("\\\\?\\"))
        temporary = cache / "publish-int-ruoyi"
        release = temporary / "release-fixture"
        context = release / "docker-build-context"
        context.mkdir(parents=True)
        (release / "manifest.json").write_text("sentinel", encoding="utf-8")
        sibling = temporary / "unrelated-release"
        sibling.mkdir()
        (sibling / "sentinel.txt").write_text("preserve", encoding="utf-8")
        yield cache, temporary, release, context


def invoke(package, *, target=None, lock=None):
    cache, temporary, release, context = package
    script = f"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) {{ throw 'PowerShell 5.1 required' }}
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput([System.IO.File]::ReadAllText({ps_string(SCRIPT)}, [System.Text.Encoding]::UTF8), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) {{ throw $parseErrors[0] }}
$definition = $ast.Find({{ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Remove-ReleaseDockerBuildContextFromPackage' }}, $true)
. ([scriptblock]::Create($definition.Extent.Text))
function Info([string]$Message) {{ }}
function Fail([string]$Message) {{ throw $Message }}
$resolvedLocalCacheRoot = {ps_string(cache)}
$localTempRoot = {ps_string(temporary)}
$releaseDir = {ps_string(release)}
$packageDirectoryName = 'release-fixture'
$dockerBuildContextRoot = {ps_string(context if target is None else target)}
$stream = $null
try {{
    {'' if lock is None else '$stream = [System.IO.File]::Open(' + ps_string(lock) + ', [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)'}
    Remove-ReleaseDockerBuildContextFromPackage
    @{{ success = $true; version = $PSVersionTable.PSVersion.ToString() }} | ConvertTo-Json -Compress
}} catch {{
    @{{ success = $false; version = $PSVersionTable.PSVersion.ToString(); error = $_.Exception.ToString() }} | ConvertTo-Json -Compress
}} finally {{
    if ($null -ne $stream) {{ $stream.Dispose() }}
}}
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"].startswith("5.1.")
    return payload


def assert_sentinels(package):
    _, temporary, release, _ = package
    assert (release / "manifest.json").read_text(encoding="utf-8") == "sentinel"
    assert (temporary / "unrelated-release/sentinel.txt").read_text(encoding="utf-8") == "preserve"


def test_ps51_removes_real_long_paths_and_preserves_siblings(package):
    _, temporary, _, context = package
    nested = context / "frontend" / ("component-" + "a" * 90) / ("module-" + "b" * 65)
    extended_nested = Path("\\\\?\\" + str(nested))
    extended_nested.mkdir(parents=True)
    payload = extended_nested / "Chinese-name-\u6d4b\u8bd5.vue"
    payload.write_text("real filesystem fixture", encoding="utf-8")
    assert len(str(payload)) > 350
    result = invoke(package)
    assert result["success"], result
    assert not context.exists()
    assert not list(temporary.glob("docker-build-context-cleanup-*"))
    assert_sentinels(package)


@pytest.mark.parametrize("target_kind", ["empty", "package", "sibling", "traversal", "file"])
def test_ps51_rejects_invalid_or_outside_targets_without_deleting_them(package, target_kind):
    _, temporary, release, context = package
    targets = {
        "empty": "",
        "package": release,
        "sibling": temporary / "unrelated-release",
        "traversal": context / ".." / ".." / "unrelated-release",
        "file": release / "manifest.json",
    }
    result = invoke(package, target=targets[target_kind])
    assert not result["success"], result
    assert context.is_dir()
    assert_sentinels(package)


def test_ps51_reports_real_delete_failure(package):
    *_, context = package
    locked = context / "locked.txt"
    locked.write_text("locked", encoding="utf-8")
    result = invoke(package, lock=locked)
    assert not result["success"], result
    assert "cleanup failed" in result["error"]
    assert_sentinels(package)


def test_ps51_already_absent_context_is_success(package):
    *_, context = package
    context.rmdir()
    assert invoke(package)["success"]
    assert_sentinels(package)
