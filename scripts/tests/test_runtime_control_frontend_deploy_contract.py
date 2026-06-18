from pathlib import Path


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
