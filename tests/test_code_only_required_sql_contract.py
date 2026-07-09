from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def read_script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_required_sql_manifest_entries_preserve_type_for_scope_filtering():
    text = read_script()
    assert "type = [string]$metadata.type" in text
    assert "Type = [string]$_.type" in text


def test_code_only_deploy_skips_data_required_sql_before_remote_mysql_apply():
    text = read_script()
    assert "Get-ReleasePreflightApplyItems -PreflightPlan $preflightPlan -PublishScope $releasePublishScope" in text
    assert "Skipping data required database SQL for code-only release" in text
    apply_index = text.index('Info "Applying required database SQL: $fileName"')
    skip_index = text.index("Skipping data required database SQL for code-only release")
    assert skip_index < apply_index
