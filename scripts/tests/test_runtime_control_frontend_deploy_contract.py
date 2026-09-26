from pathlib import Path
import subprocess

from release_test_runtime import application_backend_root
from test_release_full_package_contract import _functions, _ps


ROOT = Path(__file__).resolve().parents[2]
APP_VUE = ROOT / "frontend" / "src" / "App.vue"


def _app_vue_text() -> str:
    return APP_VUE.read_text(encoding="utf-8")


def test_frontend_deploy_actions_send_target_environment() -> None:
    app_vue = _app_vue_text()

    function_start = app_vue.index("function operationRequiresTargetEnvironment(action: string)")
    function_end = app_vue.index("function operationUsesReleaseTag(action: string)")
    function_body = app_vue[function_start:function_end]

    for action in ("publish-test", "promote-prod", "promote-backup"):
        assert action in function_body


def test_existing_legacy_and_application_callers_match_complete_package_parameters() -> None:
    legacy = ROOT / "backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java"
    application = application_backend_root() / "yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlOperationAction.java"
    for path in (legacy, application):
        assert path.is_file(), f"real caller source missing: {path}"
        tracked = subprocess.run(["git", "-C", str(path.parent), "ls-files", "--error-unmatch", path.name],
                                 capture_output=True, text=True, encoding="utf-8", check=False)
        assert tracked.returncode == 0, f"caller source is not tracked by its owning Git repository: {path}"
        text = path.read_text(encoding="utf-8")
        build = text.split("private static List<String> buildReleaseArguments", 1)[1].split("private static List<String>", 1)[0]
        deploy = text.split("private static List<String> deployReleaseArguments", 1)[1].split("private static ", 1)[0]
        assert '? "full" : "intruoyi"' in build
        assert 'args.add("-IncludeOnlyOffice")' in build
        assert '"-Component"' not in deploy
        assert '"-IncludeOnlyOffice"' not in deploy
    cases = [f"& $bind -Mode build-release -Component {profile} -PublishScope app-release {option}"
             for profile in ("intruoyi", "full") for option in ("", "-IncludeOnlyOffice")]
    cases += [f"& $bind -Mode deploy-release -Environment {environment} -ReleaseTag release-fixture -ConfirmText PROD"
              for environment in ("test", "prod", "backup")]
    cases.append("& $bind -Mode mark-tested -ReleaseTag release-fixture -TestResult PASS -TestOperationId test-fixture")
    result = _ps(_functions() + '\n$bind=[scriptblock]::Create($ast.ParamBlock.Extent.Text + "`n\'PARAMETERS_ACCEPTED\'")\n' + "\n".join(cases))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("PARAMETERS_ACCEPTED") == 8
