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
    assert "testCurrentReleaseNotes" in app_vue
    assert "prodCurrentReleaseNotes" in app_vue
    assert "backupCurrentReleaseNotes" in app_vue
    assert "releaseNotesDialogVisible" in app_vue
    assert "查看变更" in app_vue
    assert "版本变更说明" in app_vue
    assert "console-version-dock" in styles
    assert "console-version-change-button" in styles
    assert "release-notes-dialog" in styles


def test_release_notes_dialog_only_lists_version_and_change_description() -> None:
    app_vue = APP_VUE.read_text(encoding="utf-8")
    dialog_section = app_vue.split('title="版本变更说明"', 1)[1]

    assert "版本号" in dialog_section
    assert "变更说明" in dialog_section
    assert "release-notes-list" in dialog_section
    assert "release-notes-summary" not in dialog_section
    assert "release-notes-meta" not in dialog_section
    assert "release-notes-repos" not in dialog_section
    assert "release-notes-blocked" not in dialog_section
    assert "构建时间" not in dialog_section
    assert "发布范围" not in dialog_section
    assert "发布组件" not in dialog_section
