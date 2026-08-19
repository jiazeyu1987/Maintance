import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
BACKEND_DOCKERFILE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "Dockerfile.backend"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def read_backend_dockerfile() -> str:
    return BACKEND_DOCKERFILE.read_text(encoding="utf-8")


def test_release_sql_contract_gate_blocks_duplicate_system_menu_ids(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    first_sql = sql_root / "20260622_feature_a.sql"
    first_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'A', 0);\n",
        encoding="utf-8",
    )
    second_sql = sql_root / "20260622_feature_b.sql"
    second_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260622_feature_a; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'B', 0);\n",
        encoding="utf-8",
    )

    try:
        gate.assert_release_sql_contracts([first_sql, second_sql])
    except gate.ReleaseSqlContractError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected duplicate system_menu.id conflict")

    assert "duplicate system_menu.id detected across release SQL history" in message
    assert "900285" in message
    assert "20260622_feature_a.sql" in message
    assert "20260622_feature_b.sql" in message


def test_migration_policy_gate_passes_unique_system_menu_ids(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    first_sql = sql_root / "20260622_feature_a.sql"
    first_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900285, 'A', 0);\n",
        encoding="utf-8",
    )
    second_sql = sql_root / "20260622_feature_b.sql"
    second_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260622_feature_a; type=menu; riskLevel=medium\n"
        "INSERT INTO system_menu (id, name, parent_id) VALUES (900286, 'B', 0);\n",
        encoding="utf-8",
    )

    report = policy_gate.run_migration_policy_gate(sql_root)

    assert report["status"] == "passed"
    assert report["migrationCount"] == 2


def test_migration_policy_gate_accepts_evidence_only_migration_types(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    migrations = [
        ("20260811_base_schema", "", "schema"),
        ("20260812_c00_preflight", "20260811_base_schema", "preflight"),
        ("20260812_c00_schema", "20260811_base_schema", "schema"),
        ("20260812_c00_backfill", "20260812_c00_schema", "backfill"),
        ("20260812_c00_postflight", "20260812_c00_schema", "postflight"),
        ("20260812_c00_rollback", "20260812_c00_schema", "rollback-dry-run"),
    ]
    for migration_id, dependency, migration_type in migrations:
        (sql_root / f"{migration_id}.sql").write_text(
            "-- release-migration: allowedEnvironments=test,backup,prod; "
            f"dependsOn={dependency}; type={migration_type}; riskLevel=high\n"
            "SELECT 1;\n",
            encoding="utf-8",
        )

    report = policy_gate.run_migration_policy_gate(sql_root)

    assert report["status"] == "passed"
    assert {entry["type"] for entry in report["migrations"]} == {
        "preflight",
        "schema",
        "backfill",
        "postflight",
        "rollback-dry-run",
    }


def test_migration_policy_gate_rejects_executable_dependency_on_evidence_only_migration(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    preflight_sql = sql_root / "20260812_c00_preflight.sql"
    preflight_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; "
        "dependsOn=; type=preflight; riskLevel=high\n"
        "SELECT 1;\n",
        encoding="utf-8",
    )
    schema_sql = sql_root / "20260812_c00_schema.sql"
    schema_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; "
        "dependsOn=20260812_c00_preflight; type=schema; riskLevel=high\n"
        "SELECT 1;\n",
        encoding="utf-8",
    )

    try:
        policy_gate.run_migration_policy_gate(sql_root)
    except policy_gate.MigrationPolicyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected executable-to-evidence-only dependency rejection")

    assert "executable migration cannot depend on evidence-only migration" in message
    assert "20260812_c00_schema" in message
    assert "20260812_c00_preflight" in message


def test_publish_script_excludes_evidence_only_sql_from_required_migrations() -> None:
    script = read_publish_script()

    assert "$releaseMigrationExecutableTypes = @('schema', 'data', 'menu', 'config', 'permission', 'seed')" in script
    assert "$releaseMigrationEvidenceOnlyTypes = @('preflight', 'backfill', 'postflight', 'rollback-dry-run')" in script
    assert "$releaseMigrationAllowedTypes = @($releaseMigrationExecutableTypes + $releaseMigrationEvidenceOnlyTypes)" in script
    assert "if ([string]$metadata.type -in $releaseMigrationEvidenceOnlyTypes)" in script
    assert 'Info "Excluding evidence-only release SQL from required migrations: $($file.Name) [$($metadata.type)]"' in script
    assert "continue" in script


def test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    sql_path = sql_root / "20260520_system_nas_management_menu.sql"
    sql_path.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=low\n"
        "INSERT INTO `system_menu` (`id`, `name`, `parent_id`) VALUES\n"
        "  (5900, 'NAS 管理', 1)\n"
        "ON DUPLICATE KEY UPDATE\n"
        "  `name` = VALUES(`name`),\n"
        "  `parent_id` = VALUES(`parent_id`);\n",
        encoding="utf-8",
    )

    gate.assert_release_sql_contracts([sql_path])


def test_release_sql_contract_gate_ignores_insert_select_on_duplicate_update_values(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    base_sql = sql_root / "20260624_unified_signature.sql"
    base_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=menu; riskLevel=medium\n"
        "INSERT INTO `system_menu` (`id`, `name`, `parent_id`) VALUES (900411, '文件签名记录', 900218);\n",
        encoding="utf-8",
    )
    select_sql = sql_root / "20260714_signature_my_signature_admin_menu.sql"
    select_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260624_unified_signature; type=menu; riskLevel=medium\n"
        "INSERT INTO `system_menu`\n"
        "(`id`, `name`, `permission`, `type`, `sort`, `parent_id`)\n"
        "SELECT @unified_signature_my_signature_menu_id, '我的签名', 'signature-governance:policy:query', 2, 3, @unified_signature_menu_id\n"
        "FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `id` = @unified_signature_my_signature_menu_id)\n"
        "ON DUPLICATE KEY UPDATE\n"
        "  `name` = VALUES(`name`),\n"
        "  `parent_id` = VALUES(`parent_id`);\n"
        "INSERT INTO `tmp_signature_regular_menu_ids` (`menu_id`)\n"
        "VALUES\n"
        "  (900218),\n"
        "  (900411),\n"
        "  (900418);\n",
        encoding="utf-8",
    )

    gate.assert_release_sql_contracts([base_sql, select_sql])


def test_publish_script_runs_sql_preflight_before_backend_build() -> None:
    script = read_publish_script()

    for expected in (
        "Invoke-ReleaseMigrationPolicyGate",
        "$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts",
        "Info 'Building backend jar'",
    ):
        assert expected in script

    required_sql_index = script.index("$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts")
    gate_index = script.index("Invoke-ReleaseMigrationPolicyGate", required_sql_index)
    backend_build_index = script.index("Info 'Building backend jar'")
    assert required_sql_index < gate_index < backend_build_index


def test_publish_script_executes_dcc_view_matrix_prereq_before_seed_on_test() -> None:
    script = read_publish_script()

    helper_start = script.index("function Get-RequiredDatabaseSqlSessionPreamble")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    helper_block = script[helper_start:invoke_start]
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    assert "function Sort-RequiredDatabaseSqlApplyItems" in script
    assert "'20260624_dcc_view_matrix_test_tenant_prereq' = 10" in script
    assert "'20260624_dcc_view_matrix_independent_seed' = 20" in script
    assert "$preflightApplyItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })" in invoke_block
    assert "$applyItems = Sort-RequiredDatabaseSqlApplyItems -Items $preflightApplyItems -TargetEnvironment $Environment" in invoke_block
    assert "'20260624_dcc_view_matrix_independent_seed'" in helper_block
    assert "'test' { '122' }" in helper_block
    assert "SET @dcc_view_matrix_seed_tenant_id := $seedTenantId;" in helper_block


def test_publish_script_uses_environment_specific_dcc_view_matrix_seed_tenant() -> None:
    script = read_publish_script()

    helper_start = script.index("function Get-RequiredDatabaseSqlSessionPreamble")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    helper_block = script[helper_start:invoke_start]
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    assert "[string]$TargetEnvironment" in helper_block
    assert "'test' { '122' }" in helper_block
    assert "'prod' { '1' }" in helper_block
    assert "'backup' { '1' }" in helper_block
    assert "SET @dcc_view_matrix_seed_tenant_id := $seedTenantId;" in helper_block
    assert "Get-RequiredDatabaseSqlSessionPreamble -Item $item -TargetEnvironment $Environment" in invoke_block
    assert "SET @dcc_view_matrix_seed_tenant_id := 122;" not in helper_block


def test_publish_script_authorizes_dcc_view_matrix_seed_for_production_grade_environments() -> None:
    script = read_publish_script()

    helper_start = script.index("function Get-RequiredDatabaseSqlSessionPreamble")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    helper_block = script[helper_start:invoke_start]

    assert "SET @dcc_view_matrix_seed_tenant_id := $seedTenantId;" in helper_block
    assert "$TargetEnvironment -in @('prod', 'backup')" in helper_block
    assert "SET @dcc_view_matrix_seed_allow_yudao_tenant := 1;" in helper_block
    assert "SET @dcc_view_matrix_seed_allow_yudao_tenant := NULL;" in helper_block


def test_publish_script_preserves_preflight_dependency_order_for_non_priority_required_sql() -> None:
    script = read_publish_script()

    sort_start = script.index("function Sort-RequiredDatabaseSqlApplyItems")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    sort_block = script[sort_start:invoke_start]

    assert "'20260624_dcc_view_matrix_test_tenant_prereq' = 10" in sort_block
    assert "'20260624_dcc_view_matrix_independent_seed' = 20" in sort_block
    assert "OriginalOrder" in sort_block
    assert "return 1000 + [int]$_.OriginalOrder" in sort_block
    assert "Sort-Object" in sort_block
    assert "@{ Expression = { [int]$_.OriginalOrder } }" in sort_block
    assert "ForEach-Object { $_.Item }" in sort_block


def test_publish_script_runs_route_snapshot_identity_backfill_before_enforcement_sql() -> None:
    script = read_publish_script()

    assert "function Invoke-RouteSnapshotIdentityMigrationCommand" in script
    assert "function Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement" in script
    assert "20260812_mes_route_version_snapshot_identity_enforce" in script
    assert "route-snapshot-identity-backfill.json" in script
    assert "route-snapshot-identity-readiness.json" in script
    assert "yudao.mes.route-snapshot-migration.mode=$MigrationMode" in script
    assert "Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'BACKFILL'" in script
    assert "Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'READINESS'" in script
    assert "-e INTRUOYI_EXTRA_ARGS=" in script
    assert "-e ARGS=" not in script

    hook_index = script.index("Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement -Item $item")
    sql_apply_index = script.index("Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'RUNNING'", hook_index)
    assert hook_index < sql_apply_index


def test_backend_image_appends_one_shot_extra_args_without_overriding_compose_args() -> None:
    dockerfile = read_backend_dockerfile()

    assert 'ENV INTRUOYI_EXTRA_ARGS=""' in dockerfile
    assert '${ARGS} ${INTRUOYI_EXTRA_ARGS}' in dockerfile


def test_release_runtime_env_package_contains_target_bound_edhr_endpoint() -> None:
    script = read_publish_script()

    assert 'EDHR_S3_ENDPOINT=$resolvedEdhrS3Endpoint' in script


def test_release_error_state_updates_are_bounded_and_secret_redacted() -> None:
    script = read_publish_script()

    assert 'function ConvertTo-ReleaseErrorMessage' in script
    assert '$script:ReleaseErrorMessageMaxLength' in script
    assert 'ConvertTo-ReleaseErrorBase64 -Value $ErrorMessage' in script
    assert 'FROM_BASE64' in script
    assert 'function Protect-ReleaseSensitiveText' in script
    assert 'Protect-ReleaseSensitiveText $text' in script


def test_publish_script_allows_empty_required_sql_apply_items() -> None:
    script = read_publish_script()

    sort_start = script.index("function Sort-RequiredDatabaseSqlApplyItems")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    sort_block = script[sort_start:invoke_start]

    assert "[AllowEmptyCollection()]" in sort_block
    assert "[AllowNull()]" in sort_block
    assert "if ($null -eq $Items -or $Items.Count -eq 0)" in sort_block
    assert "return @()" in sort_block


def test_publish_script_uses_exec_backend_jar_for_release_image() -> None:
    script = read_publish_script()
    dockerfile = read_backend_dockerfile()

    assert "yudao-server\\target\\yudao-server-exec.jar" in script
    assert "Copy-Item -LiteralPath $BackendJarPath -Destination (Join-Path $backendJarTargetDir 'yudao-server-exec.jar') -Force" in script
    assert "yudao-server\\target\\yudao-server.jar" not in script
    assert "COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar" in dockerfile
    assert "COPY ruoyi-vue-pro/yudao-server/target/yudao-server.jar app.jar" not in dockerfile
