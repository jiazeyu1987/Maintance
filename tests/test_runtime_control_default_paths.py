from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BACKEND = "repo-root: E:/IntRuoyi/IntRuoyiBackend"
EXPECTED_FRONTEND = "frontend-root: E:/IntRuoyi/IntRuoyiFronted"


def test_runtime_control_tracked_defaults_use_fixed_main_repository_paths() -> None:
    for relative_path in (
        "config/runtime-control.example.yaml",
        "backend/src/main/resources/application.yaml",
    ):
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert EXPECTED_BACKEND in text, relative_path
        assert EXPECTED_FRONTEND in text, relative_path
        assert "D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro" not in text, relative_path
        assert "D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3" not in text, relative_path

    verifier = (REPO_ROOT / "scripts/verify_contracts.py").read_text(encoding="utf-8")
    assert "E:/IntRuoyi/IntRuoyiBackend" in verifier
    assert "E:/IntRuoyi/IntRuoyiFronted" in verifier
    assert "D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro" not in verifier
    assert "D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3" not in verifier
