from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__:
    from .release_preflight_plan import verify_target_bound_plan
else:
    from release_preflight_plan import verify_target_bound_plan


class ReleaseDeployExecutionError(RuntimeError):
    """Raised when a release migration plan cannot be executed safely."""


APPLY_ACTION = "APPLY"
SKIP_ACTIONS = {
    "SKIP_ALREADY_APPLIED",
    "SKIP_ENV_NOT_ALLOWED",
    "SKIP_SCOPE_EXCLUDED",
    "SKIP_IMMUTABLE",
}


def execute_preflight_apply_migrations(
    preflight_plan: dict[str, Any],
    *,
    execute_sql: Callable[[dict[str, Any]], None],
    record_state: Callable[[dict[str, Any], str, str | None], None],
    manifest_path: Path | str | None = None,
    target_snapshot: dict | None = None,
    executor_path: Path | str | None = None,
    target_environment: str | None = None,
    publish_scope: str = "app-release",
) -> dict[str, list[str]]:
    """Execute only APPLY items from a passed preflight plan."""

    if manifest_path is None or target_snapshot is None or executor_path is None or target_environment is None:
        raise ReleaseDeployExecutionError("TARGET_BOUND_PLAN_REQUIRED: execution requires current package, target and executor evidence")
    try:
        verify_target_bound_plan(preflight_plan, manifest_path, target_snapshot, executor_path=executor_path,
                                 target_environment=target_environment, publish_scope=publish_scope)
    except ValueError as exc:
        raise ReleaseDeployExecutionError(str(exc)) from exc
    items = list(preflight_plan.get("items") or [])
    for entry in items:
        action = str(entry.get("action") or "")
        if action.startswith("BLOCKED_"):
            migration_id = str(entry.get("migrationId") or "")
            raise ReleaseDeployExecutionError(f"blocked preflight item prevents deploy-release: {migration_id}")
        if action not in ({APPLY_ACTION} | SKIP_ACTIONS):
            migration_id = str(entry.get("migrationId") or "")
            raise ReleaseDeployExecutionError(
                f"unsupported preflight action for deploy-release: {migration_id} -> {action}"
            )

    status = str(preflight_plan.get("status") or "")
    if status != "passed":
        raise ReleaseDeployExecutionError(f"preflight plan status must be passed before deploy-release: {status}")

    summary: dict[str, list[str]] = {"applied": [], "skipped": []}
    for entry in items:
        migration_id = str(entry.get("migrationId") or "")
        action = str(entry.get("action") or "")
        if action in SKIP_ACTIONS:
            # A read-only skip must not replace historical APPLIED/FAILED evidence.
            summary["skipped"].append(migration_id)
            continue

        record_state(entry, "RUNNING", None)
        try:
            execute_sql(entry)
        except Exception as exc:  # noqa: BLE001 - surface the original failure after recording FAILED.
            message = str(exc)
            record_state(entry, "FAILED", message)
            raise ReleaseDeployExecutionError(message) from exc
        record_state(entry, "APPLIED", None)
        summary["applied"].append(migration_id)

    return summary
