from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
COMPOSE_TEMPLATE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "docker-compose.yml"


def _dcc_release_object_reference_query() -> str:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    start = script.index("function Get-DccReleaseObjectReferenceRows")
    end = script.index("$output = Invoke-LocalMySqlRaw", start)
    return script[start:end]


def _dcc_release_object_reference_function() -> str:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    start = script.index("function Get-DccReleaseObjectReferenceRows")
    end = script.index("function Resolve-DccSnapshotObjectPath", start)
    return script[start:end]


def _dcc_inventory_writer() -> str:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    start = script.index("function Write-DccObjectInventoryForReleasePackage")
    end = script.index("function Write-NasReleaseDeploymentHistory", start)
    return script[start:end]


def _nas_release_config_reader() -> str:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    start = script.index("function Read-NasReleaseConfig")
    end = script.index("function Join-NasRelativePath", start)
    return script[start:end]


def test_publish_runtime_preserves_dcc_codex_linux_contract() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    compose = COMPOSE_TEMPLATE.read_text(encoding="utf-8")

    assert "[string]$DccProjectCodeCodexCliCommand = $env:DCC_PROJECT_CODE_CODEX_CLI_COMMAND" in script
    assert "[string]$DccProjectCodeCodexHome = $env:DCC_PROJECT_CODE_CODEX_HOME" in script
    assert "[string]$DccProjectCodeCodexTimeoutSeconds = $env:DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS" in script
    assert "[string]$DccProjectCodeRecognitionWorkerCount = $env:DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT" in script
    assert "DCC_PROJECT_CODE_CODEX_CLI_COMMAND=$DccProjectCodeCodexCliCommand" in script
    assert "DCC_PROJECT_CODE_CODEX_HOME=$DccProjectCodeCodexHome" in script
    assert "DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS=$DccProjectCodeCodexTimeoutSeconds" in script
    assert "DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT=$DccProjectCodeRecognitionWorkerCount" in script
    assert "/opt/intruoyi/runtime/tools/codex" in script
    assert "/opt/intruoyi/runtime/backend-codex-home" in script
    assert "$effectiveDccProjectCodeCodexTimeoutSeconds" in script
    assert "else { '300' }" in script
    assert "$effectiveDccProjectCodeRecognitionWorkerCount" in script
    assert "else { '5' }" in script

    assert "DCC_PROJECT_CODE_CODEX_HOME: ${DCC_PROJECT_CODE_CODEX_HOME}" in compose
    assert "CODEX_HOME: ${DCC_PROJECT_CODE_CODEX_HOME}" in compose
    assert "--yudao.dcc.project-code-recognition.codex-cli-command=${DCC_PROJECT_CODE_CODEX_CLI_COMMAND}" in compose
    assert "--yudao.dcc.project-code-recognition.timeout-seconds=${DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS}" in compose
    assert "--yudao.dcc.project-code-recognition.worker-count=${DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT}" in compose
    assert "- /opt/intruoyi/runtime/tools/codex:/opt/intruoyi/runtime/tools/codex:ro" in compose
    assert "- /opt/intruoyi/runtime/backend-codex-home:/opt/intruoyi/runtime/backend-codex-home" in compose


def test_dcc_release_inventory_excludes_bound_temporary_uploads() -> None:
    query = _dcc_release_object_reference_query()

    assert (
        "FROM dcc_controlled_file_temporary_file WHERE storage_file_id IS NOT NULL AND deleted = b'0'"
        not in query
    )
    assert "dcc_controlled_file_temporary_file" not in query


def test_nas_release_config_file_is_authoritative_for_share_name() -> None:
    reader = _nas_release_config_reader()

    assert "$config.server = $NasServer" in reader
    assert "$config.share = $NasShare" not in reader
    assert "NAS release config share must come from the UTF-8 config file" in reader


def test_dcc_inventory_generation_uses_linear_collections_and_progress_logging() -> None:
    reference_function = _dcc_release_object_reference_function()
    writer = _dcc_inventory_writer()

    assert "$rows += " not in reference_function
    assert "$inventoryFiles += " not in writer
    assert "System.Collections.Generic.List[object]" in reference_function
    assert "System.Collections.Generic.List[object]" in writer
    assert "DCC object inventory progress:" in writer
