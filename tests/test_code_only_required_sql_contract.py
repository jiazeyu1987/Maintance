from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def read_script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_required_sql_manifest_entries_preserve_type_for_scope_filtering():
    text = read_script()
    assert "type = [string]$metadata.type" in text
    assert "Type = [string]$_.type" in text


def test_code_only_deploy_executes_only_scope_aware_preflight_apply_items():
    text = read_script()
    assert "'--publish-scope', $releasePublishScope" in text
    assert "SKIP_SCOPE_EXCLUDED" in text
    assert "function Get-ReleasePreflightApplyItems" not in text
    assert "$preflightApplyItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })" in text
    apply_index = text.index('Info "Applying required database SQL: $fileName"')
    skip_index = text.index("Skipping required database SQL excluded by publish scope")
    assert skip_index < apply_index


def test_code_only_scope_is_planned_before_deploy_without_post_plan_filtering():
    text = read_script()
    assert "'--publish-scope', $releasePublishScope" in text
    assert "SKIP_SCOPE_EXCLUDED" in text
    assert "function Get-ReleasePreflightApplyItems" not in text
    assert "$preflightApplyItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })" in text
