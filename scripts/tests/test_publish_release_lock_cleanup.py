from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def test_fail_releases_held_release_lock_before_exit() -> None:
    script = read_publish_script()

    fail_start = script.index("function Fail([string]$Message)")
    fail_end = script.index("function Info([string]$Message)")
    fail_function = script[fail_start:fail_end]

    assert "$script:ReleaseOperationLockHeld = $false" in script
    assert "$script:ReleaseOperationLockReleasing = $false" in script
    assert "if ($script:ReleaseOperationLockHeld -and -not $script:ReleaseOperationLockReleasing)" in fail_function
    assert "Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $Message" in fail_function
    assert fail_function.index("Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $Message") < fail_function.index("exit 1")


def test_release_lock_state_tracks_acquire_and_release_paths() -> None:
    script = read_publish_script()

    acquire_start = script.index("function Invoke-ReleaseOperationLockAcquire")
    release_start = script.index("function Invoke-ReleaseOperationLockRelease")
    copy_required_sql_start = script.index("function Copy-RequiredDatabaseSqlScripts")
    acquire_function = script[acquire_start:release_start]
    release_function = script[release_start:copy_required_sql_start]

    assert "$script:ReleaseOperationLockHeld = $true" in acquire_function
    assert "$script:ReleaseOperationLockHeld = $false" in release_function
