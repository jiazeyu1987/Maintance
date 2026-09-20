from concurrent.futures import ThreadPoolExecutor

import pytest

from ops.release.release_operation_lock import (
    ReleaseOperationLockError,
    ReleaseOperationLockStore,
    acquire_release_operation_lock,
    recover_release_operation_lock,
    release_release_operation_lock,
)


def _acquire(store: ReleaseOperationLockStore, operation_id: str) -> dict[str, str]:
    return acquire_release_operation_lock(
        store,
        environment="test",
        operation_id=operation_id,
        release_tag=operation_id,
        executor_host="HOST-A",
        executor_pid="100",
        executor_identity="runner@HOST-A",
        lease_token="lease-" + operation_id,
    )


def test_active_slow_task_blocks_recovery_and_new_acquisition() -> None:
    store = ReleaseOperationLockStore()
    _acquire(store, "op-active")

    with pytest.raises(ReleaseOperationLockError):
        recover_release_operation_lock(
            store,
            environment="test",
            operation_id="op-active",
            executor_identity="runner@HOST-A",
            lease_token="lease-op-active",
            executor_terminal=False,
        )
    with pytest.raises(ReleaseOperationLockError):
        _acquire(store, "op-next")


def test_terminated_task_can_only_be_recovered_by_exact_owner() -> None:
    store = ReleaseOperationLockStore()
    _acquire(store, "op-dead")

    with pytest.raises(ReleaseOperationLockError):
        recover_release_operation_lock(
            store,
            environment="test",
            operation_id="op-dead",
            executor_identity="other@HOST-A",
            lease_token="lease-op-dead",
            executor_terminal=True,
        )
    recovered = recover_release_operation_lock(
        store,
        environment="test",
        operation_id="op-dead",
        executor_identity="runner@HOST-A",
        lease_token="lease-op-dead",
        executor_terminal=True,
    )
    assert recovered["status"] == "FAILED"


def test_concurrent_recovery_has_single_winner() -> None:
    store = ReleaseOperationLockStore()
    _acquire(store, "op-race")

    def recover() -> str:
        try:
            recover_release_operation_lock(
                store,
                environment="test",
                operation_id="op-race",
                executor_identity="runner@HOST-A",
                lease_token="lease-op-race",
                executor_terminal=True,
            )
            return "won"
        except ReleaseOperationLockError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: recover(), range(2)))
    assert sorted(results) == ["lost", "won"]
    assert store.current("test")["status"] == "FAILED"


def test_old_executor_cannot_release_after_ownership_is_replaced() -> None:
    store = ReleaseOperationLockStore()
    _acquire(store, "op-old")
    recover_release_operation_lock(
        store,
        environment="test",
        operation_id="op-old",
        executor_identity="runner@HOST-A",
        lease_token="lease-op-old",
        executor_terminal=True,
    )
    _acquire(store, "op-new")

    with pytest.raises(ReleaseOperationLockError):
        release_release_operation_lock(
            store,
            environment="test",
            operation_id="op-old",
            status="FAILED",
            executor_identity="runner@HOST-A",
            lease_token="lease-op-old",
        )
