from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def test_backend_runtime_base_is_validated_early_and_loaded_at_point_of_use() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    integrity_call_index = text.index(
        "Assert-BackendRuntimeBaseTarIntegrity -Config $backendRuntimeBaseConfig"
    )
    maven_index = text.index("Invoke-CheckedCommand -FilePath 'mvn'")
    context_index = text.index("New-ReleaseDockerBuildContext `")
    image_call_index = text.index(
        "Assert-BackendRuntimeBaseImageAvailable -Config $backendRuntimeBaseConfig"
    )
    backend_build_index = text.index("Info 'Building backend image'")

    assert "function Assert-BackendRuntimeBaseTarIntegrity" in text
    assert "function Assert-BackendRuntimeBaseImageAvailable" in text
    assert text.count("Assert-BackendRuntimeBaseTarIntegrity -Config $backendRuntimeBaseConfig") == 1
    assert text.count("Assert-BackendRuntimeBaseImageAvailable -Config $backendRuntimeBaseConfig") == 1
    assert integrity_call_index < maven_index
    assert context_index < image_call_index < backend_build_index
