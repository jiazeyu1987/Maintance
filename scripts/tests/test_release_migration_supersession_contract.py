from __future__ import annotations

from pathlib import Path

import pytest

from ops.release.release_migration_manifest import MigrationManifestError, build_migration_manifest
from ops.release.release_migration_policy_gate import MigrationPolicyError, run_migration_policy_gate
from ops.release.release_preflight_plan import build_preflight_plan


ROOT = Path(__file__).resolve().parents[2]


def _migration(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "migrationId": "m1",
        "file": "required-sql/m1.sql",
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


def test_planner_skips_legacy_ids_as_immutable_and_applies_successor() -> None:
    legacy_a = _migration(
        migrationId="legacy-a",
        sha256="b" * 64,
        requiresTargetPreflight=False,
    )
    legacy_b = _migration(
        migrationId="legacy-b",
        sha256="c" * 64,
        requiresTargetPreflight=False,
    )
    successor = _migration(
        migrationId="successor",
        sha256="d" * 64,
        supersedes=["legacy-a", "legacy-b"],
    )
    plan = build_preflight_plan(
        [legacy_a, legacy_b, successor],
        {
            "legacy-a": {"status": "APPLIED", "sha256": "0" * 64},
            "legacy-b": {"status": "APPLIED", "sha256": "1" * 64},
        },
        target_environment="test",
        publish_scope="app-release",
    )

    assert plan["status"] == "passed"
    assert [item["action"] for item in plan["items"]] == [
        "SKIP_IMMUTABLE",
        "SKIP_IMMUTABLE",
        "APPLY",
    ]
    assert plan["items"][0]["reason"].startswith("superseded by successor")


def test_planner_runs_successor_before_migrations_that_depend_on_legacy_id() -> None:
    plan = build_preflight_plan(
        [
            _migration(migrationId="legacy", requiresTargetPreflight=False),
            _migration(migrationId="consumer", dependsOn=["legacy"], requiresTargetPreflight=False),
            _migration(
                migrationId="successor",
                requiresTargetPreflight=True,
                supersedes=["legacy"],
            ),
        ],
        {},
        target_environment="test",
        publish_scope="app-release",
    )

    assert plan["status"] == "passed"
    assert [item["migrationId"] for item in plan["items"]] == [
        "legacy",
        "successor",
        "consumer",
    ]
    assert [item["action"] for item in plan["items"]] == [
        "SKIP_IMMUTABLE",
        "APPLY",
        "APPLY",
    ]


def test_planner_rejects_unknown_superseded_id() -> None:
    with pytest.raises(ValueError, match="supersedes missing migration"):
        build_preflight_plan(
            [_migration(migrationId="successor", supersedes=["missing"])],
            {},
            target_environment="test",
            publish_scope="app-release",
        )


def test_policy_rejects_duplicate_supersession_owner(tmp_path: Path) -> None:
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    header = (
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; "
        "type=schema; riskLevel=medium; requiresTargetPreflight=true; "
        "supersedes=20260901_legacy\n"
    )
    (sql_root / "20260901_legacy.sql").write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=schema; riskLevel=medium\n"
        "SELECT 1;\n",
        encoding="utf-8",
    )
    (sql_root / "20260902_successor_a.sql").write_text(header + "SELECT 1;\n", encoding="utf-8")
    (sql_root / "20260903_successor_b.sql").write_text(header + "SELECT 1;\n", encoding="utf-8")

    with pytest.raises(MigrationPolicyError, match="multiple supersession owners"):
        run_migration_policy_gate(sql_root)


def test_policy_rejects_empty_supersession_declaration(tmp_path: Path) -> None:
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    (sql_root / "20260902_successor.sql").write_text(
        "-- release-migration: allowedEnvironments=test; dependsOn=; type=schema; "
        "riskLevel=medium; supersedes=\nSELECT 1;\n",
        encoding="utf-8",
    )

    with pytest.raises(MigrationManifestError, match="supersedes"):
        build_migration_manifest(sql_root)


def test_planner_rejects_successor_not_allowed_for_target_environment() -> None:
    with pytest.raises(ValueError, match="supersession target .* not allowed"):
        build_preflight_plan(
            [
                _migration(
                    migrationId="legacy",
                    allowedEnvironments=["prod"],
                    requiresTargetPreflight=False,
                ),
                _migration(
                    migrationId="successor",
                    allowedEnvironments=["test"],
                    supersedes=["legacy"],
                ),
            ],
            {},
            target_environment="prod",
            publish_scope="app-release",
        )


def test_planner_rejects_supersession_cycle() -> None:
    with pytest.raises(ValueError, match="supersession cycle"):
        build_preflight_plan(
            [
                _migration(migrationId="a", supersedes=["b"]),
                _migration(migrationId="b", supersedes=["a"]),
            ],
            {},
            target_environment="prod",
            publish_scope="app-release",
        )


def test_planner_rejects_successor_excluded_from_publish_scope() -> None:
    with pytest.raises(ValueError, match="supersession target .* publish scope"):
        build_preflight_plan(
            [
                _migration(migrationId="legacy", requiresTargetPreflight=False),
                _migration(
                    migrationId="successor",
                    supersedes=["legacy"],
                    allowedPublishScopes=["with-data"],
                ),
            ],
            {},
            target_environment="prod",
            publish_scope="app-release",
        )


def test_planner_preserves_blocked_plan_for_unresolved_successor_dependency() -> None:
    plan = build_preflight_plan(
        [
            _migration(migrationId="legacy", requiresTargetPreflight=False),
            _migration(
                migrationId="successor",
                supersedes=["legacy"],
                dependsOn=["missing-dependency"],
            ),
        ],
        {},
        target_environment="prod",
        publish_scope="app-release",
    )
    assert plan["status"] == "blocked"
    assert plan["items"][-1]["action"] == "BLOCKED_DEPENDENCY_MISSING"


def test_planner_accepts_dependency_applied_in_external_target_ledger() -> None:
    plan = build_preflight_plan(
        [
            _migration(migrationId="legacy", requiresTargetPreflight=False),
            _migration(
                migrationId="successor",
                supersedes=["legacy"],
                dependsOn=["external-parent"],
            ),
        ],
        {"external-parent": {"status": "APPLIED", "sha256": "e" * 64}},
        target_environment="prod",
        publish_scope="app-release",
    )
    assert plan["status"] == "passed"
    assert [item["action"] for item in plan["items"]] == ["SKIP_IMMUTABLE", "APPLY"]


def test_maintenance_publish_script_propagates_supersedes_contract() -> None:
    script = (ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1").read_text(encoding="utf-8")
    assert "supersedes = @()" in script
    assert "'supersedes'" in script
    assert "supersedes = @($metadata.supersedes)" in script
    assert "supersedes = @($requiredSql.supersedes)" in script
