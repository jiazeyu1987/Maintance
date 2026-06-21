from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ReleaseDeployExecutionError(RuntimeError):
    """Raised when a release migration plan cannot be executed safely."""


APPLY_ACTION = "APPLY"
SKIP_ACTIONS = {
    "SKIP_ALREADY_APPLIED",
    "SKIP_ENV_NOT_ALLOWED",
}
BLOCKED_ACTIONS = {
    "BLOCKED_CHECKSUM_MISMATCH",
    "BLOCKED_ENV_NOT_ALLOWED",
    "BLOCKED_DEPENDENCY_MISSING",
}


def execute_preflight_apply_migrations(
    preflight_plan: dict[str, Any],
    *,
    execute_sql: Callable[[dict[str, Any]], None],
    record_state: Callable[[dict[str, Any], str, str | None], None],
) -> dict[str, list[str]]:
    """Execute only APPLY items from a passed preflight plan."""

    items = list(preflight_plan.get("items") or [])
    for entry in items:
        action = str(entry.get("action") or "")
        if action in BLOCKED_ACTIONS:
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
            if action == "SKIP_ALREADY_APPLIED":
                record_state(entry, "SKIPPED_ALREADY_APPLIED", None)
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
