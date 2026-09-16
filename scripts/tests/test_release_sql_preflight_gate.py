import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"
BACKEND_DOCKERFILE = ROOT / "ops" / "deploy" / "int-ruoyi-test" / "Dockerfile.backend"


def read_publish_script() -> str:
    return PUBLISH_SCRIPT.read_text(encoding="utf-8")


def read_backend_dockerfile() -> str:
    return BACKEND_DOCKERFILE.read_text(encoding="utf-8")


def test_release_docker_context_copy_uses_parallel_robocopy() -> None:
    script = read_publish_script()

    assert "'/MT:32'" in script
    assert "robocopy {0} {1} /E /MT:32" in script
    assert "$sourceFiles = @(Get-ChildItem -LiteralPath $SourceDirectory -Recurse -File -Force)" in script
    assert "$destinationFiles = @(Get-ChildItem -LiteralPath $DestinationDirectory -Recurse -File -Force)" in script
    assert "Release directory copy incomplete" in script


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


def test_migration_policy_gate_excludes_target_preflight_support_sql(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    migration_sql = sql_root / "20260913_release_schema.sql"
    migration_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=; type=schema; riskLevel=medium\n"
        "CREATE TABLE IF NOT EXISTS release_table (id bigint);\n",
        encoding="utf-8",
    )
    support_dir = sql_root / "target-preflight"
    support_dir.mkdir()
    support_sql = support_dir / "20260913_release_schema.preflight.sql"
    support_sql.write_text(
        "SELECT 'release_table_exists' AS check_name, COUNT(*) AS actual_count FROM information_schema.tables;\n",
        encoding="utf-8",
    )

    report = policy_gate.run_migration_policy_gate(sql_root)

    assert report["status"] == "passed"
    assert [entry["migrationId"] for entry in report["migrations"]] == [
        "20260913_release_schema"
    ]


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


def test_migration_policy_gate_excludes_rollback_only_sql_from_default_release_manifest(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    release_sql = sql_root / "20260822_release_schema.sql"
    release_sql.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; "
        "dependsOn=; type=schema; riskLevel=medium\n"
        "CREATE TABLE IF NOT EXISTS release_table (id bigint);\n",
        encoding="utf-8",
    )
    rollback_sql = sql_root / "20260822_release_schema_rollback.sql"
    rollback_sql.write_text(
        "-- rollback-migration: allowedEnvironments=test,backup,prod; "
        "requiresBackup=true; type=schema; riskLevel=high\n"
        "DROP TABLE IF EXISTS release_table;\n",
        encoding="utf-8",
    )

    report = policy_gate.run_migration_policy_gate(sql_root)

    assert report["status"] == "passed"
    assert [entry["migrationId"] for entry in report["migrations"]] == [
        "20260822_release_schema"
    ]


def test_migration_policy_gate_rejects_explicit_rollback_only_sql_manifest_input(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    rollback_sql = sql_root / "20260822_release_schema_rollback.sql"
    rollback_sql.write_text(
        "-- rollback-migration: allowedEnvironments=test,backup,prod; "
        "requiresBackup=true; type=schema; riskLevel=high\n"
        "DROP TABLE IF EXISTS release_table;\n",
        encoding="utf-8",
    )

    try:
        policy_gate.run_migration_policy_gate(sql_root, sql_paths=[rollback_sql])
    except policy_gate.MigrationPolicyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected rollback-only manifest input rejection")

    assert "rollback-only migration cannot be included in a release manifest" in message
    assert "20260822_release_schema_rollback.sql" in message


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


def test_migration_policy_gate_propagates_temp_table_reopen_contract(tmp_path: Path) -> None:
    policy_gate = importlib.import_module("ops.release.release_migration_policy_gate")
    sql_root = tmp_path / "sql" / "mysql"
    sql_root.mkdir(parents=True)
    sql_path = sql_root / "20260824_temp_reopen.sql"
    sql_path.write_text(
        "-- release-migration: allowedEnvironments=test,backup,prod; "
        "dependsOn=; type=data; riskLevel=high\n"
        "INSERT INTO tmp_demo (id) SELECT id FROM tmp_demo;\n",
        encoding="utf-8",
    )

    try:
        policy_gate.run_migration_policy_gate(sql_root)
    except policy_gate.MigrationPolicyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected migration policy gate to propagate temp-table reopen risk")

    assert "MySQL temp table reopen risk" in message
    assert "20260824_temp_reopen" in message


def test_publish_script_excludes_evidence_only_sql_from_required_migrations() -> None:
    script = read_publish_script()

    assert "$releaseMigrationExecutableTypes = @('schema', 'data', 'menu', 'config', 'permission', 'seed')" in script
    assert "$releaseMigrationEvidenceOnlyTypes = @('preflight', 'backfill', 'postflight', 'rollback-dry-run')" in script
    assert "$releaseMigrationAllowedTypes = @($releaseMigrationExecutableTypes + $releaseMigrationEvidenceOnlyTypes)" in script
    assert "if ([string]$metadata.type -in $releaseMigrationEvidenceOnlyTypes)" in script
    assert 'Info "Excluding evidence-only release SQL from required migrations: $($file.Name) [$($metadata.type)]"' in script
    assert "continue" in script


def test_publish_script_excludes_rollback_only_sql_before_required_metadata_read() -> None:
    script = read_publish_script()

    assert "function Test-ReleaseRollbackMigrationMetadata" in script
    assert 'Info "Excluding rollback-only release SQL from required migrations: $($file.Name)"' in script
    rollback_skip_index = script.index("Test-ReleaseRollbackMigrationMetadata -SqlPath $file.FullName")
    metadata_read_index = script.index("Read-ReleaseMigrationMetadata -SqlPath $file.FullName", rollback_skip_index)
    assert rollback_skip_index < metadata_read_index


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


def test_publish_script_does_not_scan_live_sql_for_package_only_modes() -> None:
    script = read_publish_script()

    assignment = "$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts"
    assignment_index = script.index(assignment)
    next_mark_tested = script.index("if ($Mode -eq 'mark-tested')", assignment_index)
    guard_block = script[assignment_index - 180:assignment_index + len(assignment) + 80]

    assert "if ($Mode -notin @('deploy-release', 'mark-tested'))" in guard_block
    assert "$Mode -eq 'mark-tested'" not in guard_block.split(assignment, 1)[0]
    assert next_mark_tested > assignment_index


def test_publish_script_executes_dcc_view_matrix_prereq_before_seed_on_test() -> None:
    script = read_publish_script()

    helper_start = script.index("function Get-RequiredDatabaseSqlSessionPreamble")
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    helper_block = script[helper_start:invoke_start]
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    assert "function Sort-RequiredDatabaseSqlApplyItems" in script
    assert "applyOrder = $_.Item.applyOrder" in script
    assert "sessionProfile" in script
    assert "$preflightApplyItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })" in invoke_block
    assert "$applyItems = Sort-RequiredDatabaseSqlApplyItems -Items $preflightApplyItems -TargetEnvironment $Environment" in invoke_block
    assert "'dcc-view-matrix-seed'" in helper_block
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

    assert "applyOrder = $_.Item.applyOrder" in sort_block
    assert "OriginalOrder" in sort_block
    assert "return 1000 + [int]$_.OriginalOrder" in sort_block
    assert "Sort-Object" in sort_block
    assert "@{ Expression = { [int]$_.OriginalOrder } }" in sort_block
    assert "ForEach-Object { $_.Item }" in sort_block


def test_publish_script_runs_route_snapshot_identity_backfill_before_enforcement_sql() -> None:
    script = read_publish_script()

    assert "function Invoke-RouteSnapshotIdentityMigrationCommand" in script
    assert "function Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement" in script
    assert "approvedHook" in script
    assert "route-snapshot-identity" in script
    assert "route-snapshot-identity-backfill.json" in script
    assert "route-snapshot-identity-readiness.json" in script
    assert "yudao.mes.route-snapshot-migration.mode=$MigrationMode" in script
    assert "Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'BACKFILL'" in script
    assert "Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'READINESS'" in script
    assert "-e INTRUOYI_EXTRA_ARGS=" in script
    assert "-e ARGS=" not in script
    assert "docker compose --env-file $remoteEnvNextLiteral run --rm --no-deps" in script
    assert "test -f $remoteEnvNextLiteral" in script

    hook_index = script.index("Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement -Item $item")
    sql_apply_index = script.index("Invoke-RequiredDatabaseSqlScriptWithState -Item $item", hook_index)
    assert hook_index < sql_apply_index


def test_publish_script_combines_route_snapshot_run_and_report_check_in_single_ssh_session() -> None:
    script = read_publish_script()

    helper_start = script.index("function Invoke-RouteSnapshotIdentityMigrationCommand")
    helper_end = script.index("function Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement", helper_start)
    helper_block = script[helper_start:helper_end]

    assert helper_block.count("Invoke-SshCommand") == 1
    assert "docker compose --env-file $remoteEnvNextLiteral run --rm --no-deps" in helper_block
    assert "route_snapshot_exit=`$?" in helper_block
    assert "`$route_snapshot_exit=`$?" not in helper_block
    assert "cat $remoteReportFileLiteral" in helper_block
    assert "ROUTE_SNAPSHOT_IDENTITY_REPORT_MISSING" in helper_block
    assert "test -f $remoteReportFileLiteral" in helper_block
    assert "grep -q '\"status\" : \"READY\"' $remoteReportFileLiteral" in helper_block
    assert "grep -q '\"blockerCount\" : 0' $remoteReportFileLiteral" in helper_block


def test_backend_image_appends_one_shot_extra_args_without_overriding_compose_args() -> None:
    dockerfile = read_backend_dockerfile()

    assert 'ENV INTRUOYI_EXTRA_ARGS=""' in dockerfile
    assert '${ARGS} ${INTRUOYI_EXTRA_ARGS}' in dockerfile


def test_release_runtime_env_package_omits_secret_env_files() -> None:
    script = read_publish_script()

    writer_start = script.index("function Write-ReleaseRuntimeEnvPackage")
    apply_start = script.index("function Apply-ReleaseRuntimeEnvPackage")
    writer_block = script[writer_start:apply_start]

    assert "Skipping runtime-env secret package files" in writer_block
    assert "Write-Utf8LfNoBomFile" not in writer_block
    assert "EDHR_S3_ENDPOINT=" not in writer_block
    assert "EDHR_S3_ACCESS_KEY=" not in writer_block
    assert "EDHR_S3_SECRET_KEY=" not in writer_block


def test_release_runtime_env_fails_when_test_endpoint_points_outside_test_host() -> None:
    script = read_publish_script()

    assert "function Assert-ReleaseRuntimeEnvTargetBoundary" in script
    assert "EDHR_S3_ENDPOINT for test runtime env must point to 172.30.30.58" in script
    assert "172\\.30\\.30\\.57|172\\.30\\.30\\.59" in script
    assert "Assert-ReleaseRuntimeEnvTargetBoundary `\n        -TargetEnvironment $TargetEnvironment" in script


def test_release_runtime_env_rebinds_generic_edhr_endpoint_to_target_host() -> None:
    script = read_publish_script()

    resolver_start = script.index("function Resolve-TargetPublishRuntimeValue")
    boundary_start = script.index("function Assert-ReleaseRuntimeEnvTargetBoundary")
    resolver_block = script[resolver_start:boundary_start]
    defaults_start = script.index("function Set-PublishRuntimeDefaultsForTarget")
    read_env_start = script.index("function Read-ReleaseRuntimeEnvFile")
    defaults_block = script[defaults_start:read_env_start]
    content_start = script.index("function New-ReleaseRuntimeEnvContent")
    writer_start = script.index("function Write-ReleaseRuntimeEnvPackage")
    content_block = script[content_start:writer_start]

    assert "function Resolve-TargetEdhrS3Endpoint" in script
    assert "[string]$TargetServerHost" in resolver_block
    assert "$builder.Host = $TargetServerHost" in script
    assert "Resolve-TargetEdhrS3Endpoint" in resolver_block
    assert "-TargetServerHost $TargetServerHost" in defaults_block
    assert "-TargetServerHost $TargetServerHost" in content_block


def test_deploy_release_imports_remote_runtime_env_before_secret_gates() -> None:
    script = read_publish_script()

    import_start = script.index("function Import-ExistingRemoteRuntimeEnvSettings")
    deploy_start = script.index("if ($Mode -eq 'deploy-release')")
    defaults_index = script.index("Set-PublishRuntimeDefaultsForTarget", deploy_start)
    secret_gate_index = script.index("$edhrProtectedStorageSettings = Get-EdhrProtectedStorageSettings", deploy_start)
    import_call_index = script.index("Import-ExistingRemoteRuntimeEnvSettings", deploy_start)

    import_block = script[import_start:deploy_start]
    assert "Get-RemoteRuntimeEnvMap" in import_block
    assert "Set-PublishRuntimeValuesFromSettings -Settings $existingRemoteEnv" in import_block
    assert deploy_start < import_call_index < defaults_index < secret_gate_index


def test_build_release_imports_remote_runtime_env_before_secret_gates() -> None:
    script = read_publish_script()

    import_start = script.index("function Import-ExistingRemoteRuntimeEnvSettings")
    resolve_existing_start = script.index("function Resolve-ExistingRuntimeEnvValue")
    import_block = script[import_start:resolve_existing_start]
    deploy_start = script.index("if ($Mode -eq 'deploy-release')")
    defaults_index = script.index("Set-PublishRuntimeDefaultsForTarget", deploy_start)
    secret_gate_index = script.index("$edhrProtectedStorageSettings = Get-EdhrProtectedStorageSettings", deploy_start)
    build_import_index = script.index("if ($Mode -eq 'build-release' -and $publishBackend)", deploy_start)

    build_import_block = script[build_import_index:defaults_index]

    assert "if ($Mode -eq 'build-release')" in import_block
    assert "Get-RemoteRuntimeEnvMap" in import_block
    assert "eDHR protected storage verifier must use target environment secrets" in import_block
    assert "Set-PublishRuntimeValuesFromSettings -Settings $existingRemoteEnv" in import_block
    assert "Require-Command 'ssh'" in build_import_block
    assert "Import-ExistingRemoteRuntimeEnvSettings" in build_import_block
    assert deploy_start < build_import_index < defaults_index < secret_gate_index

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


def test_release_sql_contract_gate_blocks_repeated_temp_table_reference(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_path = tmp_path / "20260824_temp_reopen.sql"
    sql_path.write_text(
        "INSERT INTO tmp_demo (id) SELECT id FROM tmp_demo;\n",
        encoding="utf-8",
    )

    try:
        gate.assert_release_sql_contracts([sql_path])
    except gate.ReleaseSqlContractError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected MySQL temp table reopen conflict")

    assert "MySQL temp table reopen risk" in message
    assert "tmp_demo" in message
    assert "20260824_temp_reopen.sql" in message


def test_release_sql_contract_gate_blocks_repeated_nested_temp_table_reference(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_path = tmp_path / "20260824_temp_nested_reopen.sql"
    sql_path.write_text(
        "SELECT 1 WHERE EXISTS (SELECT 1 FROM tmp_role) "
        "AND EXISTS (SELECT 1 FROM tmp_role);\n",
        encoding="utf-8",
    )

    try:
        gate.assert_release_sql_contracts([sql_path])
    except gate.ReleaseSqlContractError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected nested MySQL temp table reopen conflict")

    assert "MySQL temp table reopen risk" in message
    assert "tmp_role" in message


def test_production_release_role_sql_passes_temp_table_reopen_contract() -> None:
    backend_sql = Path(r"E:\IntRuoyi\IntRuoyiBackend\sql\mysql\20260814_mes_production_release_roles.sql")
    assert backend_sql.is_file(), f"required backend migration is missing: {backend_sql}"

    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    gate.assert_release_sql_contracts([backend_sql])


def test_release_sql_contract_gate_requires_explicit_collation_for_text_temp_tables(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_path = tmp_path / "20260824_temp_collation.sql"
    sql_path.write_text(
        "CREATE TEMPORARY TABLE tmp_labels (label VARCHAR(64));\n"
        "SELECT 1 FROM tmp_labels JOIN system_labels "
        "ON tmp_labels.label = system_labels.label;\n",
        encoding="utf-8",
    )

    try:
        gate.assert_release_sql_contracts([sql_path])
    except gate.ReleaseSqlContractError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected explicit temporary table collation requirement")

    assert "temporary table collation must be explicit" in message
    assert "tmp_labels" in message


def test_release_sql_contract_gate_accepts_explicit_collation_for_text_temp_tables(tmp_path: Path) -> None:
    gate = importlib.import_module("ops.release.release_sql_contract_gate")
    sql_path = tmp_path / "20260824_temp_collation_ok.sql"
    sql_path.write_text(
        "CREATE TEMPORARY TABLE tmp_labels (label VARCHAR(64)) "
        "DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n"
        "SELECT 1 FROM tmp_labels JOIN system_labels "
        "ON tmp_labels.label = system_labels.label;\n",
        encoding="utf-8",
    )

    gate.assert_release_sql_contracts([sql_path])


def test_build_script_delegates_frontend_dependency_preparation() -> None:
    build_script = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")

    assert "prepare-frontend-dependencies.ps1" in build_script
    assert "ForceFrontendDependencies" in build_script
    assert "-RequiredBinary @('vite.cmd', 'vue-tsc.cmd')" in build_script
    assert "install --frozen-lockfile" not in build_script


def test_frontend_dependency_preparation_contract_is_explicit() -> None:
    helper_path = ROOT / "scripts" / "prepare-frontend-dependencies.ps1"
    assert helper_path.is_file()
    helper = helper_path.read_text(encoding="utf-8")

    for expected in (
        "pnpm-lock.yaml",
        "Get-FileHash",
        ".release-dependencies.json",
        "ignored-builds",
        "cross-env.cmd",
        "vite.cmd",
        "vue-tsc.cmd",
        "'install', '--frozen-lockfile'",
        "FRONTEND_DEPENDENCIES_REUSED",
    ):
        assert expected in helper


def test_frontend_dependency_preparation_allows_missing_stamp() -> None:
    helper_path = ROOT / "scripts" / "prepare-frontend-dependencies.ps1"
    helper = helper_path.read_text(encoding="utf-8")
    function_body = helper.split("function Test-DependencyStamp", 1)[1].split("function Assert-RequiredBinaries", 1)[0]

    assert "[Parameter(Mandatory = $true)]$Stamp" not in function_body
    assert "if ($null -eq $Stamp" in function_body


def test_frontend_dependency_preparation_accepts_verbose_none_ignored_builds() -> None:
    helper_path = ROOT / "scripts" / "prepare-frontend-dependencies.ps1"
    helper = helper_path.read_text(encoding="utf-8")
    function_body = helper.split("function Get-IgnoredBuilds", 1)[1].split("function Test-DependencyStamp", 1)[0]

    assert "Automatically ignored builds during installation:" in function_body
    assert "None" in function_body


def test_frontend_dependency_preparation_accepts_multiline_none_ignored_builds() -> None:
    helper_path = ROOT / "scripts" / "prepare-frontend-dependencies.ps1"
    helper = helper_path.read_text(encoding="utf-8")
    function_body = helper.split("function Get-IgnoredBuilds", 1)[1].split("function Test-DependencyStamp", 1)[0]

    assert "$lines.Count -eq 2" in function_body
    assert "$lines[0] -eq 'Automatically ignored builds during installation:'" in function_body
    assert "$lines[1] -eq 'None'" in function_body


def test_publish_script_runs_frontend_dependency_preflight_before_backend_build() -> None:
    script = read_publish_script()

    assert "function Assert-FrontendBuildPreflight" in script
    assert "cross-env.cmd" in script
    assert "vite.cmd" in script
    assert "vue-tsc.cmd" in script
    assert "-ArgumentList @('ignored-builds')" in script
    preflight_index = script.index("Assert-FrontendBuildPreflight -FrontendDir $frontendDir")
    backend_build_index = script.index("Info 'Building backend jar'")
    assert preflight_index < backend_build_index


def test_publish_script_accepts_multiline_none_ignored_builds() -> None:
    script = read_publish_script()
    function_body = script.split("function Assert-FrontendBuildPreflight", 1)[1].split("function Assert-FrontendBuildStaticAssetContract", 1)[0]

    assert "$ignoredBuildLines.Count -eq 2" in function_body
    assert "$ignoredBuildLines[0] -eq 'Automatically ignored builds during installation:'" in function_body
    assert "$ignoredBuildLines[1] -eq 'None'" in function_body


def test_publish_script_bounds_edhr_storage_verifier_wait() -> None:
    script = read_publish_script()
    process_capture = script.split("function Invoke-ProcessCapture", 1)[1].split("function Resolve-SmartReleaseReportOnlyEnabled", 1)[0]
    verifier_block = script.split("function Invoke-EdhrStorageRetentionVerifier", 1)[1].split("function ConvertTo-SqlStringLiteral", 1)[0]

    assert "[int]$TimeoutSeconds = 0" in process_capture
    assert "$process.WaitForExit($TimeoutSeconds * 1000)" in process_capture
    assert "Stop-Process -Id $process.Id -Force" in process_capture
    assert "Process timed out after $TimeoutSeconds seconds." in process_capture
    assert "$timeoutSeconds = 120" in verifier_block
    assert "-TimeoutSeconds $timeoutSeconds" in verifier_block
    assert "timed out after $timeoutSeconds seconds" in verifier_block


def test_publish_script_waits_for_unbounded_process_capture_before_reading_exit_code() -> None:
    script = read_publish_script()
    process_capture = script.split("function Invoke-ProcessCapture", 1)[1].split("function Resolve-SmartReleaseReportOnlyEnabled", 1)[0]

    assert "$startProcessParameters = @{" in process_capture
    assert "if ($TimeoutSeconds -le 0)" in process_capture
    assert "$startProcessParameters['Wait'] = $true" in process_capture
    assert "Start-Process @startProcessParameters" in process_capture
    assert "$process.Refresh()" in process_capture
    assert "$process.ExitCode" in process_capture


def test_publish_script_primes_process_handle_before_timeout_wait() -> None:
    script = read_publish_script()
    process_capture = script.split("function Invoke-ProcessCapture", 1)[1].split("function Resolve-SmartReleaseReportOnlyEnabled", 1)[0]

    assert "$null = $process.Handle" in process_capture
    assert process_capture.index("$process = Start-Process @startProcessParameters") < process_capture.index("$null = $process.Handle")
    assert process_capture.index("$null = $process.Handle") < process_capture.index("if ($TimeoutSeconds -gt 0)")


def test_publish_script_uploads_required_sql_as_single_archive() -> None:
    script = read_publish_script()
    copy_start = script.index("function Copy-RequiredDatabaseSqlScriptsToServer")
    next_function = script.index("function Copy-ReleaseOpsRuntimePackage", copy_start)
    copy_block = script[copy_start:next_function]

    assert "required-sql.tar" in copy_block
    assert "Invoke-CheckedCommand -FilePath 'tar'" in copy_block
    assert "Copy-ToServer -LocalPath $requiredSqlArchivePath -RemotePath $remoteRequiredSqlArchive" in copy_block
    assert "tar -xf" in copy_block
    assert "required SQL archive contains no files" in copy_block
    assert "Copy-ToServer -LocalPath $packageSqlPath" not in copy_block


def test_publish_script_requires_exact_remote_required_sql_archive_count() -> None:
    script = read_publish_script()
    copy_start = script.index("function Copy-RequiredDatabaseSqlScriptsToServer")
    next_function = script.index("function Copy-ReleaseOpsRuntimePackage", copy_start)
    copy_block = script[copy_start:next_function]

    assert "remote_sql_count" in copy_block
    assert "-ne $archiveSqlCount" in copy_block
    assert "required SQL archive remote file count mismatch" in copy_block


def test_publish_script_does_not_check_each_required_sql_file_over_ssh_after_archive_gate() -> None:
    script = read_publish_script()
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    assert "test -f '$remoteSqlPath'" not in invoke_block
    assert "REQUIRED_SQL_EXISTS" not in invoke_block


def test_publish_script_combines_required_sql_success_state_updates_in_single_ssh_session() -> None:
    script = read_publish_script()

    assert "function Invoke-RequiredDatabaseSqlScriptWithState" in script
    helper_start = script.index("function Invoke-RequiredDatabaseSqlScriptWithState")
    helper_end = script.index("function Invoke-RequiredDatabaseSqlScripts", helper_start)
    helper_block = script[helper_start:helper_end]
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    assert "New-ReleaseMigrationStateUpsertSql -Item $Item -Status 'RUNNING'" in helper_block
    assert "New-ReleaseMigrationStateUpsertSql -Item $Item -Status 'APPLIED'" in helper_block
    assert "Invoke-SshCommand $command" in helper_block
    assert "Invoke-RequiredDatabaseSqlScriptWithState -Item $item -RemoteSqlPath $remoteSqlPath -SessionPreamble $sessionPreamble" in invoke_block
    assert "Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'RUNNING'" not in invoke_block
    assert "Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'APPLIED'" not in invoke_block


def test_publish_script_records_failed_required_sql_after_combined_apply_failure() -> None:
    script = read_publish_script()
    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]

    helper_call = "Invoke-RequiredDatabaseSqlScriptWithState -Item $item -RemoteSqlPath $remoteSqlPath -SessionPreamble $sessionPreamble"
    failed_update = "Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'FAILED' -ErrorMessage $_.Exception.Message"
    assert helper_call in invoke_block
    assert failed_update in invoke_block
    assert invoke_block.index(helper_call) < invoke_block.index(failed_update)
    assert "throw" in invoke_block[invoke_block.index(failed_update):]


def test_publish_script_uploads_ops_runtime_package_as_single_archive() -> None:
    script = read_publish_script()
    copy_start = script.index("function Copy-ReleaseOpsRuntimePackage")
    next_function = script.index("function Write-TargetBoundPostImportSql", copy_start)
    copy_block = script[copy_start:next_function]

    assert "ops-runtime.tar" in copy_block
    assert "Invoke-CheckedCommand -FilePath 'tar'" in copy_block
    assert "Copy-ToServer -LocalPath $opsRuntimeArchivePath -RemotePath $remoteOpsRuntimeArchive" in copy_block
    assert "tar -xf '$remoteOpsRuntimeArchive' -C '$remoteOpsRuntimeDir'" in copy_block
    assert "Runtime-control ops package must not include backup-ops.secrets.json" in copy_block
    assert "Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'linux')" not in copy_block
    assert "Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'scripts')" not in copy_block
    assert "Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'actions')" not in copy_block
    assert "Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'config')" not in copy_block


def test_publish_script_uploads_deploy_control_files_as_single_archive() -> None:
    script = read_publish_script()

    assert "function Copy-DeployControlFilesToServer" in script
    helper_start = script.index("function Copy-DeployControlFilesToServer")
    helper_end = script.index("function Copy-ReleaseOpsRuntimePackage", helper_start)
    helper_block = script[helper_start:helper_end]
    deploy_start = script.index('Info "Copying deploy control files to the $PublishTargetName server"')
    deploy_end = script.index('Info "Reading remote compose services on the $PublishTargetName server"', deploy_start)
    deploy_block = script[deploy_start:deploy_end]

    assert "deploy-control.tar" in helper_block
    assert "trap cleanup_deploy_control EXIT" in helper_block
    assert "Invoke-CheckedCommand -FilePath 'tar'" in helper_block
    assert "Copy-ToServer -LocalPath $deployControlArchivePath -RemotePath $remoteDeployControlArchive" in helper_block
    assert "tar -xf $remoteDeployControlArchiveLiteral -C $remoteDeployControlExtractDirLiteral" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/app/docker-compose.yml" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/app/.env" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/website/dist/index.html" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/website/nginx.conf" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/sql/reset-db.sql" in helper_block
    assert "test -f $remoteDeployControlExtractDirLiteral/sql/post-import.sql" in helper_block
    assert "Copy-DeployControlFilesToServer -ComposeLocal $composeLocal" in deploy_block
    assert "Copy-ToServer -LocalPath $composeLocal -RemotePath $remoteCompose" not in deploy_block
    assert "Copy-ToServer -LocalPath $remoteEnvLocal -RemotePath $remoteEnv" not in deploy_block
    assert "Copy-ToServer -LocalPath $websiteRuntimeLocal -RemotePath $remoteReleaseDir -Recursive" not in deploy_block
    assert "Copy-ToServer -LocalPath $resetDbSqlLocal -RemotePath $remoteResetDbSql" not in deploy_block
    assert "Copy-ToServer -LocalPath $postImportSqlLocal -RemotePath $remotePostImportSql" not in deploy_block
    assert "Copy-LargeFileToServerInChunks -LocalPath $imageTar -RemotePath $remoteImageTar" in deploy_block


def test_publish_script_batches_skip_already_applied_migration_state_updates() -> None:
    script = read_publish_script()

    assert "function Invoke-ReleaseMigrationStateBatchUpdate" in script
    assert "Batch updating release migration state" in script
    assert "$skipAlreadyAppliedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ALREADY_APPLIED' })" in script
    assert "Invoke-ReleaseMigrationStateBatchUpdate -Items $skipAlreadyAppliedItems -Status 'SKIPPED_ALREADY_APPLIED'" in script

    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]
    assert "foreach ($item in @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ALREADY_APPLIED' }))" not in invoke_block


def test_publish_script_batches_environment_and_scope_skips_to_clear_stale_failed_rows() -> None:
    script = read_publish_script()

    assert "$skipEnvNotAllowedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ENV_NOT_ALLOWED' })" in script
    assert "Invoke-ReleaseMigrationStateBatchUpdate -Items $skipEnvNotAllowedItems -Status 'SKIPPED_ENV_NOT_ALLOWED'" in script
    assert "$skipScopeExcludedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_SCOPE_EXCLUDED' })" in script
    assert "Invoke-ReleaseMigrationStateBatchUpdate -Items $skipScopeExcludedItems -Status 'SKIPPED_SCOPE_EXCLUDED'" in script
    assert "'SKIPPED_ENV_NOT_ALLOWED', 'SKIPPED_SCOPE_EXCLUDED'" in script

    invoke_start = script.index("function Invoke-RequiredDatabaseSqlScripts")
    invoke_end = script.index("if ($Mode -eq 'mark-tested')", invoke_start)
    invoke_block = script[invoke_start:invoke_end]
    assert "foreach ($item in @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ENV_NOT_ALLOWED' }))" not in invoke_block
    assert "foreach ($item in @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_SCOPE_EXCLUDED' }))" not in invoke_block


def test_release_migration_state_batch_update_streams_sql_over_ssh_stdin() -> None:
    script = read_publish_script()

    assert "function New-SshArgumentListWithInput" in script
    assert "function Invoke-SshCommandWithInput" in script

    batch_start = script.index("function Invoke-ReleaseMigrationStateBatchUpdate")
    batch_end = script.index("function Ensure-ReleaseMigrationStateSchema", batch_start)
    batch_block = script[batch_start:batch_end]

    assert "Invoke-SshCommandWithInput" in batch_block
    assert "-StandardInput $stateSql" in batch_block
    assert "cat <<'SQL'" not in batch_block
    assert 'Info "Batch updating release migration state: $Status ($($Items.Count))"' in batch_block


def test_ssh_command_logs_and_errors_are_secret_redacted() -> None:
    script = read_publish_script()
    command_start = script.index("function Invoke-SshCommand")
    capture_start = script.index("function Invoke-SshCapture", command_start)
    command_block = script[command_start:capture_start]
    capture_end = script.index("function Test-RemoteFileExists", capture_start)
    capture_block = script[capture_start:capture_end]

    assert "$displayCommand = Protect-ReleaseSensitiveText $normalizedCommand" in command_block
    assert "Info (\"Run: ssh {0}\" -f ((New-SshArgumentList -Command $displayCommand) -join ' '))" in command_block
    assert "$safeText = Protect-ReleaseSensitiveText $text" in command_block
    assert "throw \"Command failed with exit code $($result.ExitCode): ssh`n$safeText\"" in command_block
    assert "$safeCommand = Protect-ReleaseSensitiveText $normalizedCommand" in capture_block
    assert "$safeText = Protect-ReleaseSensitiveText $text" in capture_block
    assert "throw \"SSH command failed ($exitCode): $safeCommand`n$safeText\"" in capture_block
