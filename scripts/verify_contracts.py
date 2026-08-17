from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        raise AssertionError(f"missing required file: {path}")
    return target.read_text(encoding="utf-8")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def assert_not_contains(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise AssertionError(f"forbidden {label}: {needle}")


def verify_backend_contract() -> None:
    controller = read_text("backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlController.java")
    application = read_text("backend/src/main/java/com/intruoyi/maintenance/MaintenanceApplication.java")
    config = read_text("backend/src/main/resources/application.yaml")
    pom = read_text("backend/pom.xml")

    for endpoint in [
        "/admin-api/infra/runtime-control/overview",
        "/admin-api/infra/runtime-control/restart",
        "/admin-api/infra/runtime-control/actions",
        "/admin-api/infra/runtime-control/actions/preview",
        "/admin-api/infra/runtime-control/release-packages",
        "/admin-api/infra/runtime-control/release-status",
        "/admin-api/infra/runtime-control/backup-points",
        "/admin-api/infra/runtime-control/remote-root-disk/status",
        "/admin-api/infra/runtime-control/incidents/page",
    ]:
        assert_contains(controller, endpoint, f"backend endpoint {endpoint}")

    assert_not_contains(controller, "@PreAuthorize", "Spring Security pre-authorization")
    assert_not_contains(application + pom, "spring-boot-starter-security", "Spring Security dependency")
    assert_contains(config, "address: 127.0.0.1", "loopback binding")
    assert_contains(config, "port: 48181", "standalone server port")
    assert_contains(controller, "local-operator", "local operator identity")


def verify_backend_tests() -> None:
    test_source = read_text("backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlContractTest.java")
    assert_contains(test_source, "noSpringSecurityDependency", "backend security removal test")
    assert_contains(test_source, "missingConfigurationFailsFast", "backend fail-fast test")
    assert_contains(test_source, "runtimeControlEndpointsAreExposed", "backend endpoint contract test")


def verify_frontend_contract() -> None:
    page = read_text("frontend/src/App.vue")
    api = read_text("frontend/src/api/runtimeControl.ts")
    package_json = read_text("frontend/package.json")

    for forbidden in ["v-hasPermi", "checkPermi", "usePermissionStore", "/login", "infra:runtime-control"]:
        assert_not_contains(page + api, forbidden, f"frontend permission/login dependency {forbidden}")

    for action in [
        "build-release",
        "publish-test",
        "apply-test-db-sql",
        "mark-release-tested",
        "promote-prod",
        "promote-backup",
        "backup-now",
        "rollback-app",
        "restore-data",
        "rehearsal",
    ]:
        assert_contains(page, action, f"frontend action {action}")

    assert_contains(api, "/admin-api/infra/runtime-control/overview", "frontend overview API")
    for api_path in [
        "/infra/runtime-control/owner-matrix",
        "/infra/runtime-control/wizard/scenarios",
        "/infra/runtime-control/wizard/recommendation",
        "/infra/runtime-control/rollback-candidates",
        "/infra/runtime-control/restore-candidates",
        "/infra/runtime-control/release-packages",
        "resend-site-message",
    ]:
        assert_contains(api, api_path, f"frontend original runtime-control API {api_path}")
    for api_function in [
        "getRuntimeControlOperationLog",
        "runRuntimeControlInspection",
        "getRuntimeControlInspectionRun",
        "getRuntimeControlBusinessHealth",
        "runRuntimeControlProbes",
        "getRuntimeControlLatestProbes",
        "getRuntimeControlBackupPoints",
        "getRuntimeControlBackupPoint",
        "getRuntimeControlAlertsPage",
        "createRuntimeControlAlert",
        "acknowledgeRuntimeControlAlert",
        "getRuntimeControlIncidentsPage",
        "createRuntimeControlIncident",
        "recordRuntimeControlIncidentAction",
        "closeRuntimeControlIncident",
        "getRuntimeControlRemoteRootDiskStatus",
        "cleanupRuntimeControlRemoteRootTemporaryFiles",
    ]:
        assert_contains(api, api_function, f"frontend original runtime-control wrapper {api_function}")
    assert_contains(page, "showOperationLog", "frontend operation log action")
    assert_contains(page, "operation-log-dialog", "frontend operation log dialog")
    assert_not_contains(api, "selectedImageTag?:", "client-submittable selectedImageTag")
    assert_not_contains(api, "selectedBackupId?:", "client-submittable selectedBackupId")
    assert_not_contains(page, "v-model=\"actionForm.selectedImageTag\"", "free-text image tag input")
    assert_not_contains(page, "v-model=\"actionForm.selectedBackupId\"", "free-text backup id input")
    assert_contains(page, "operationSupportsPublishScope(selectedAction.value.action)", "action-scoped publish payload")
    assert_contains(page, "operationUsesReleaseTag(selectedAction.value.action)", "action-scoped releaseTag payload")
    assert_contains(page, "operationRequiresTargetEnvironment(selectedAction.value.action)", "action-scoped targetEnvironment payload")
    assert_contains(page, "operationUsesTestConclusion(selectedAction.value.action)", "action-scoped testConclusion payload")
    assert_not_contains(page, "includeOnlyOffice: actionForm.includeOnlyOffice", "unscoped includeOnlyOffice payload")
    assert_not_contains(page, "includeShowroomBuildPackage: actionForm.includeShowroomBuildPackage", "unscoped includeShowroom payload")
    assert_not_contains(page, "releaseTag: actionForm.releaseTag || undefined", "unscoped releaseTag payload")
    assert_not_contains(page, "testConclusion: '独立控制台验证记录'", "hard-coded testConclusion payload")
    assert_contains(package_json, "typecheck", "frontend typecheck script")


def verify_frontend_design_contract() -> None:
    page = read_text("frontend/src/App.vue")
    styles = read_text("frontend/src/styles.css")

    for marker in [
        "console-shell",
        "status-summary-grid",
        "workbench-grid",
        "control-surface",
        "action-choice-grid",
        "command-summary",
        "operation-table-shell",
        "status-pill",
        "skeleton-line",
    ]:
        assert_contains(page + styles, marker, f"frontend design marker {marker}")

    for token in [
        "--console-accent: #1677ff",
        "--console-line: #dbe3ef",
        "--console-text: #172033",
        "min-height: 100dvh",
    ]:
        assert_contains(styles, token, f"frontend design token {token}")

    assert_not_contains(styles, "Inter,", "generic Inter font stack")
    assert_not_contains(styles, "linear-gradient(", "marketing gradient background")


def verify_scripts_and_config() -> None:
    for path in [
        "config/runtime-control.example.yaml",
        "scripts/build.ps1",
        "scripts/start.ps1",
        "scripts/dev-backend.ps1",
        "scripts/dev-frontend.ps1",
        "ops/deploy/publish-int-ruoyi.ps1",
        "ops/backup-ops/scripts/backup-ops.ps1",
        "ops/release/release_preflight_plan.py",
    ]:
        read_text(path)

    config = read_text("config/runtime-control.example.yaml")
    assert_contains(config, "E:/IntRuoyi/IntRuoyiBackend", "managed backend root")
    assert_contains(config, "E:/IntRuoyi/IntRuoyiFronted", "managed frontend root")
    assert_contains(config, "D:/ProjectPackage/Website", "managed website root")

    gitignore = read_text(".gitignore")
    assert_contains(gitignore, "runtime/runtime-control/", "runtime state ignore")
    assert_contains(gitignore, "config/runtime-control.local.yaml", "local config ignore")


def verify_release_script_contract() -> None:
    script = read_text("ops/deploy/publish-int-ruoyi.ps1")
    assert_contains(script, "JSON_OBJECT(", "DCC object inventory JSON row query")
    assert_contains(script, "TO_BASE64(", "DCC object inventory base64 transport")
    assert_contains(script, "FromBase64String", "DCC object inventory base64 decoder")
    assert_contains(script, "StandardOutputEncoding", "UTF-8 process output capture")
    assert_contains(script, "ConvertFrom-Json", "DCC object inventory JSON parser")
    assert_not_contains(script, '$columns = $line -split "`t", 7', "tab-delimited DCC inventory parser")


def main() -> int:
    checks = [
        verify_backend_contract,
        verify_backend_tests,
        verify_frontend_contract,
        verify_frontend_design_contract,
        verify_scripts_and_config,
        verify_release_script_contract,
    ]
    for check in checks:
        check()
    print("PASS: standalone runtime-control contracts are present")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
