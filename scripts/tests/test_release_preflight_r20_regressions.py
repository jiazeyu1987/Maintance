from __future__ import annotations

import hashlib

import pytest

from ops.release.release_preflight_plan import build_preflight_plan, _attach_equivalent_sql_checksums

SCOPE = "app-release"


def migration(migration_id: str, **overrides: object) -> dict[str, object]:
    value = {
        "migrationId": migration_id,
        "file": f"required-sql/{migration_id}.sql",
        "sha256": "a" * 64,
        "type": "schema",
        "allowedEnvironments": ["test", "backup", "prod"],
        "dependsOn": [],
        "requiresTargetPreflight": True,
        "supersedes": [],
        "allowedPublishScopes": [],
    }
    value.update(overrides)
    return value


def plan(migrations, state=None):
    return build_preflight_plan(
        migrations, state or {}, target_environment="prod", publish_scope=SCOPE
    )


def actions(result):
    return {item["migrationId"]: item["action"] for item in result["items"]}


@pytest.mark.parametrize("superseding", [False, True])
@pytest.mark.parametrize("status", ["APPLIED", "FAILED", "RUNNING"])
def test_unresolved_history_blocks_before_missing_dependency(superseding, status):
    migrations = [migration("child", dependsOn=["missing"])]
    if superseding:
        migrations.insert(0, migration("old"))
        migrations[-1]["supersedes"] = ["old"]
    result = plan(migrations, {"child": {"status": status, "sha256": "b" * 64}})
    assert result["status"] == "blocked"
    assert actions(result)["child"] == ("BLOCKED_CHECKSUM_MISMATCH" if status == "APPLIED" else "BLOCKED_LEDGER_STATE")


@pytest.mark.parametrize("superseding", [False, True])
def test_external_applied_dependency_does_not_authorize_checksum_replay(superseding):
    migrations = [migration("child", dependsOn=["external"])]
    if superseding:
        migrations.insert(0, migration("old"))
        migrations[-1]["supersedes"] = ["old"]
    result = plan(migrations, {
        "child": {"status": "APPLIED", "sha256": "b" * 64},
        "external": {"status": "APPLIED", "sha256": "c" * 64},
    })
    assert result["status"] == "blocked"
    assert actions(result)["child"] == "BLOCKED_CHECKSUM_MISMATCH"


@pytest.mark.parametrize("metadata_only", [False, True])
def test_matching_applied_proof_does_not_reexecute_or_require_historical_parent(tmp_path, metadata_only):
    sql = b"-- release-migration: type=schema\nSELECT 1;\n"
    (tmp_path / "required-sql").mkdir()
    (tmp_path / "required-sql/parent.sql").write_bytes(sql)
    parent = migration("parent", dependsOn=["historical"], sha256=hashlib.sha256(sql).hexdigest())
    verified = [parent]
    _attach_equivalent_sql_checksums(verified, tmp_path / "manifest.json")
    checksum = hashlib.sha256(b"SELECT 1;\n" if metadata_only else sql).hexdigest()
    result = plan(
        [parent,
         migration("consumer", dependsOn=["parent"])],
        {"parent": {"status": "APPLIED", "sha256": checksum}},
    )
    assert result["status"] == "passed"
    assert actions(result) == {"parent": "SKIP_ALREADY_APPLIED", "consumer": "APPLY"}


@pytest.mark.parametrize("reverse", [False, True])
def test_multilevel_supersession_is_explicitly_rejected(reverse):
    migrations = [
        migration("old"),
        migration("middle", supersedes=["old"]),
        migration("consumer", dependsOn=["old"]),
        migration("final", supersedes=["middle"]),
    ]
    if reverse:
        migrations.reverse()
    with pytest.raises(ValueError, match="multi-level supersession"):
        plan(migrations)


@pytest.mark.parametrize("consumer_applied", [False, True])
def test_immutable_alias_never_satisfies_blocked_successor(consumer_applied):
    state = {"old": {"status": "APPLIED", "sha256": "a" * 64}}
    if consumer_applied:
        state["consumer"] = {"status": "APPLIED", "sha256": "b" * 64}
    result = plan([
        migration("old"),
        migration("consumer", dependsOn=["old"]),
        migration("successor", supersedes=["old"], dependsOn=["missing"]),
    ], state)
    assert result["status"] == "blocked"
    assert actions(result) == {
        "old": "SKIP_IMMUTABLE",
        "successor": "BLOCKED_DEPENDENCY_MISSING",
        "consumer": "BLOCKED_CHECKSUM_MISMATCH" if consumer_applied else "BLOCKED_DEPENDENCY_MISSING",
    }
    if not consumer_applied:
        assert "successor" in result["items"][-1]["reason"]


def test_consumer_uses_matching_successor_proof():
    result = plan([
        migration("old"),
        migration("consumer", dependsOn=["old"]),
        migration("successor", supersedes=["old"], dependsOn=["historical"]),
    ], {"successor": {"status": "APPLIED", "sha256": "a" * 64}})
    assert result["status"] == "passed"
    assert [item["migrationId"] for item in result["items"]] == ["old", "successor", "consumer"]
    assert actions(result)["successor"] == "SKIP_ALREADY_APPLIED"


@pytest.mark.parametrize("ledger_checksum", [None, "b" * 64])
def test_scope_exclusion_cannot_hide_applied_checksum_drift(ledger_checksum):
    state = {} if ledger_checksum is None else {
        "restricted": {"status": "APPLIED", "sha256": ledger_checksum}
    }
    result = plan([migration("restricted", allowedPublishScopes=["with-data"])], state)
    assert actions(result)["restricted"] == ("SKIP_SCOPE_EXCLUDED" if ledger_checksum is None else "BLOCKED_CHECKSUM_MISMATCH")


def test_declared_scope_exclusion_propagates_to_transitive_consumers():
    result = plan([
        migration("restricted", allowedPublishScopes=["with-data"]),
        migration("consumer", dependsOn=["restricted"]),
        migration("leaf", dependsOn=["consumer"]),
    ])
    assert result["status"] == "blocked"
    assert actions(result) == {
        "restricted": "SKIP_SCOPE_EXCLUDED",
        "consumer": "BLOCKED_SCOPE_DEPENDENCY",
        "leaf": "BLOCKED_SCOPE_DEPENDENCY",
    }
    assert "leaf -> consumer -> restricted" in result["items"][-1]["reason"]


def test_matching_applied_scope_excluded_migration_is_only_read_as_proof():
    result = plan([
        migration("restricted", allowedPublishScopes=["with-data"]),
        migration("consumer", dependsOn=["restricted"]),
    ], {"restricted": {"status": "APPLIED", "sha256": "a" * 64}})
    assert result["status"] == "passed"
    assert actions(result) == {"restricted": "SKIP_ALREADY_APPLIED", "consumer": "APPLY"}


def test_declared_scope_permits_matching_scope():
    assert actions(plan([migration("ordinary", allowedPublishScopes=[SCOPE])])) == {
        "ordinary": "APPLY"
    }
