from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY_PRECHECK_REPORT = ROOT / "ops" / "release" / "lib" / "DeployPrecheckReport.psm1"
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
BUILD_MODULE_PLANNER = ROOT / "ops" / "release" / "lib" / "BuildModulePlanner.psm1"
RELEASE_MANIFEST_VALIDATOR = ROOT / "ops" / "release" / "lib" / "ReleaseManifestValidator.psm1"


def read_deploy_precheck_report() -> str:
    return DEPLOY_PRECHECK_REPORT.read_text(encoding="utf-8")


def test_deploy_precheck_hashing_uses_dotnet_sha256_without_get_file_hash() -> None:
    script = read_deploy_precheck_report()
    function_body = script.split("function Get-Sha256Prefixed", 1)[1].split("function Resolve-PackageFilePath", 1)[0]

    assert "Get-FileHash" not in function_body
    assert "[System.IO.File]::Open" in function_body
    assert "[System.Security.Cryptography.SHA256]::Create()" in function_body
    assert ".ComputeHash($stream)" in function_body
    assert "sha256:" in function_body


def test_core_release_scripts_do_not_depend_on_get_file_hash() -> None:
    for script_path in (
        DEPLOY_PRECHECK_REPORT,
        PUBLISH_SCRIPT,
        BUILD_MODULE_PLANNER,
        RELEASE_MANIFEST_VALIDATOR,
    ):
        script = script_path.read_text(encoding="utf-8")

        assert "Get-FileHash" not in script, script_path
