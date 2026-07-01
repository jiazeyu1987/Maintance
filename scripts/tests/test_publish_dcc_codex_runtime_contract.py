from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
COMPOSE_TEMPLATE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "docker-compose.yml"


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
