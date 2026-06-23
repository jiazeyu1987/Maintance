from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = ROOT / "frontend"
PACKAGE_JSON = FRONTEND_ROOT / "package.json"
APP_VUE = FRONTEND_ROOT / "src" / "App.vue"
STYLES = FRONTEND_ROOT / "src" / "styles.css"
VITE_CONFIG = FRONTEND_ROOT / "vite.config.ts"


def test_version_badge_contract_is_wired_from_build_package_and_release_status() -> None:
    package_json = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    app_vue = APP_VUE.read_text(encoding="utf-8")
    styles = STYLES.read_text(encoding="utf-8")
    vite_config = VITE_CONFIG.read_text(encoding="utf-8")

    assert package_json["version"]
    assert "__APP_VERSION__" in vite_config
    assert "packageJson.version" in vite_config
    assert "console-version-dock" in app_vue
    assert "buildVersion" in app_vue
    assert "testCurrentReleaseTag" in app_vue
    assert "prodCurrentReleaseTag" in app_vue
    assert "backupCurrentReleaseTag" in app_vue
    assert "console-version-dock" in styles
