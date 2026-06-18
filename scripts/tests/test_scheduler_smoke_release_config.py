from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
COMPOSE_TEMPLATE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "docker-compose.yml"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def read_compose_template() -> str:
    return COMPOSE_TEMPLATE.read_text(encoding="utf-8")


def test_maintenance_publish_uses_maintenance_compose_template() -> None:
    script = read_publish_script()

    assert "$composeTemplate = Join-Path $scriptDir 'int-ruoyi-test\\docker-compose.yml'" in script
    assert "$composeTemplate = Join-Path $backendRepo 'script\\deploy\\int-ruoyi-test\\docker-compose.yml'" not in script


def test_compose_template_exposes_scheduler_smoke_runtime() -> None:
    compose = read_compose_template()

    for expected in (
        "YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY: ${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY}",
        "YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME: ${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME}",
        "MES_SMOKE_BASE_URL: ${MES_SMOKE_BASE_URL}",
        "MES_SMOKE_EXCEL_FILE: ${MES_SMOKE_EXCEL_FILE}",
        "MES_SMOKE_ARTIFACT_DIR: ${MES_SMOKE_ARTIFACT_DIR}",
        "MES_SMOKE_NODE_IMAGE: ${MES_SMOKE_NODE_IMAGE}",
        "--yudao.mes.scheduler-workbench.smoke-test.frontend-directory=${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY}",
        "--yudao.mes.scheduler-workbench.smoke-test.script-name=${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME}",
        "/opt/intruoyi/runtime/smoke/bin/npm:/usr/local/bin/npm:ro",
    ):
        assert expected in compose


def test_publish_script_packages_scheduler_smoke_runner_and_env() -> None:
    script = read_publish_script()

    for expected in (
        "$schedulerSmokeFrontendDirectory = '/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3'",
        "$schedulerSmokeScriptName = 'e2e:mes:smart-scheduling-smoke'",
        "$schedulerSmokeNodeImage = 'mcr.microsoft.com/playwright:v1.60.0-noble'",
        "function New-SchedulerSmokeRunnerPackage",
        "function Copy-SchedulerSmokeRunnerToServer",
        "function Assert-RemoteSchedulerSmokeRuntime",
        "Smart scheduling smoke E2E script missing",
        "Smart scheduling smoke static script missing",
        "YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY=$effectiveSchedulerSmokeFrontendDirectory",
        "YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME=$effectiveSchedulerSmokeScriptName",
        "MES_SMOKE_BASE_URL=$effectiveMesSmokeBaseUrl",
        "MES_SMOKE_EXCEL_FILE=$effectiveMesSmokeExcelFile",
        "MES_SMOKE_ARTIFACT_DIR=$effectiveMesSmokeArtifactDir",
        "MES_SMOKE_NODE_IMAGE=$effectiveMesSmokeNodeImage",
        "if ($publishBackend) { New-SchedulerSmokeRunnerPackage }",
        "if ($publishBackend) { Copy-SchedulerSmokeRunnerToServer }",
        "if ($publishBackend) { Assert-RemoteSchedulerSmokeRuntime }",
    ):
        assert expected in script
