from __future__ import annotations

from datetime import UTC, datetime


class ReleaseOperationLockError(RuntimeError):
    """Raised when a release operation lock cannot be acquired or released."""


class ReleaseOperationLockStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, str]] = {}

    def current(self, environment: str) -> dict[str, str] | None:
        record = self._records.get(environment)
        return dict(record) if record else None

    def save(self, environment: str, record: dict[str, str]) -> None:
        self._records[environment] = dict(record)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def acquire_release_operation_lock(
    store: ReleaseOperationLockStore,
    *,
    environment: str,
    operation_id: str,
    release_tag: str,
) -> dict[str, str]:
    current = store.current(environment)
    if current and current.get("status") == "RUNNING":
        raise ReleaseOperationLockError(
            "running release operation exists for "
            f"{environment}: {current.get('operationId')} ({current.get('releaseTag')})"
        )

    record = {
        "environment": environment,
        "operationId": operation_id,
        "releaseTag": release_tag,
        "status": "RUNNING",
        "startedAt": _now_iso(),
        "finishedAt": "",
    }
    store.save(environment, record)
    return record


def release_release_operation_lock(
    store: ReleaseOperationLockStore,
    *,
    environment: str,
    operation_id: str,
    status: str,
) -> dict[str, str]:
    current = store.current(environment)
    if not current or current.get("status") != "RUNNING" or current.get("operationId") != operation_id:
        raise ReleaseOperationLockError(
            f"operation {operation_id} does not match running operation for {environment}"
        )

    record = dict(current)
    record["status"] = status
    record["finishedAt"] = _now_iso()
    store.save(environment, record)
    return record
