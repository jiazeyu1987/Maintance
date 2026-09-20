from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock


class ReleaseOperationLockError(RuntimeError):
    """Raised when a release operation lock cannot be acquired or released."""


class ReleaseOperationLockStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, str]] = {}
        self._lock = Lock()

    def current(self, environment: str) -> dict[str, str] | None:
        with self._lock:
            record = self._records.get(environment)
            return dict(record) if record else None

    def save(self, environment: str, record: dict[str, str]) -> None:
        with self._lock:
            self._records[environment] = dict(record)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def acquire_release_operation_lock(
    store: ReleaseOperationLockStore,
    *,
    environment: str,
    operation_id: str,
    release_tag: str,
    executor_host: str = "",
    executor_pid: str = "",
    executor_identity: str = "",
    lease_token: str = "",
) -> dict[str, str]:
    with store._lock:
        current = store._records.get(environment)
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
            "executorHost": executor_host,
            "executorPid": executor_pid,
            "executorIdentity": executor_identity,
            "leaseToken": lease_token,
        }
        store._records[environment] = dict(record)
        return dict(record)


def release_release_operation_lock(
    store: ReleaseOperationLockStore,
    *,
    environment: str,
    operation_id: str,
    status: str,
    executor_identity: str = "",
    lease_token: str = "",
) -> dict[str, str]:
    with store._lock:
        current = store._records.get(environment)
        if (
            not current
            or current.get("status") != "RUNNING"
            or current.get("operationId") != operation_id
            or current.get("executorIdentity") != executor_identity
            or current.get("leaseToken") != lease_token
        ):
            raise ReleaseOperationLockError(
                f"operation {operation_id} does not match running operation for {environment}"
            )
        record = dict(current)
        record["status"] = status
        record["finishedAt"] = _now_iso()
        store._records[environment] = dict(record)
        return record


def recover_release_operation_lock(
    store: ReleaseOperationLockStore,
    *,
    environment: str,
    operation_id: str,
    executor_identity: str,
    lease_token: str,
    executor_terminal: bool,
) -> dict[str, str]:
    with store._lock:
        current = store._records.get(environment)
        if (
            not current
            or current.get("status") != "RUNNING"
            or current.get("operationId") != operation_id
            or current.get("executorIdentity") != executor_identity
            or current.get("leaseToken") != lease_token
            or not executor_terminal
        ):
            raise ReleaseOperationLockError(
                f"operation {operation_id} is not recoverable for {environment}"
            )
        record = dict(current)
        record["status"] = "FAILED"
        record["finishedAt"] = _now_iso()
        store._records[environment] = dict(record)
        return record
