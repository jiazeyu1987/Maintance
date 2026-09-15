from ops.release.release_preflight_plan import build_preflight_plan


def migration(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "migrationId": "m1",
        "file": "required-sql/m1.sql",
        "sha256": "a" * 64,
        "type": "schema",
        "allowedEnvironments": ["test", "backup", "prod"],
        "dependsOn": [],
    }
    base.update(overrides)
    return base


def test_build_preflight_orders_independent_items_by_declared_apply_order() -> None:
    plan = build_preflight_plan(
        [
            migration(migrationId="view-matrix-seed", type="seed", applyOrder=20),
            migration(migrationId="test-tenant-prereq", type="seed", applyOrder=10),
            migration(migrationId="ordinary-schema"),
        ],
        {},
        target_environment="test",
        publish_scope="app-release",
    )

    assert plan["status"] == "passed"
    assert [item["migrationId"] for item in plan["items"]] == [
        "test-tenant-prereq",
        "view-matrix-seed",
        "ordinary-schema",
    ]


def test_build_preflight_dependency_order_overrides_apply_order() -> None:
    plan = build_preflight_plan(
        [
            migration(migrationId="child", applyOrder=10, dependsOn=["parent"]),
            migration(migrationId="parent", applyOrder=20),
        ],
        {},
        target_environment="test",
        publish_scope="app-release",
    )

    assert plan["status"] == "passed"
    assert [item["migrationId"] for item in plan["items"]] == ["parent", "child"]
