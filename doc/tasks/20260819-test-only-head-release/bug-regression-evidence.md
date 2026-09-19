# Release Regression Evidence

## Bug Summary

The test publish hook for MES route snapshot identity replaced the backend Compose `ARGS` environment instead of extending it. The one-shot backend then used its image default datasource (`127.0.0.1:23306`) and failed before the migration command could run. The same failure path embedded an unbounded, multiline exception in the lock-release SQL heredoc, so the test release lock remained `RUNNING`. The generated target runtime environment also omitted `EDHR_S3_ENDPOINT`, allowing a previous endpoint to persist on the server.

## Expected Behavior

The one-shot migration must retain the normal Compose datasource, Redis, runtime-control, and secret arguments while appending only its mode/report arguments. Failure state updates must be bounded, secret-redacted, and transported safely so the release lock is marked `FAILED`. The target-bound runtime environment package must include the selected test eDHR endpoint.

## Reproduction

- Publish operation: `op-2026-08-19T123706070455900Z-1dfb7779-a297-4a37-9f7c-c378926f64f6`.
- Release log: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819e-state\runtime-control\logs\op-2026-08-19T123706070455900Z-1dfb7779-a297-4a37-9f7c-c378926f64f6.log`.
- Observed one-shot datasource: `jdbc:mysql://127.0.0.1:23306/ruoyi-vue-pro`.
- Remote post-failure evidence: `evidence\remote-postfailure-precheck-r260819e-r2.json`.

## Root Cause

`docker compose run ... -e ARGS=<migration args> backend` overrides the service-level `ARGS` block from `docker-compose.yml`. `Invoke-ReleaseOperationLockRelease` and `Invoke-ReleaseMigrationStateUpdate` interpolate the full exception into a shell heredoc without length or transport protection. `New-ReleaseRuntimeEnvContent` did not emit `EDHR_S3_ENDPOINT`.

## Regression Tests

- `test_publish_script_runs_route_snapshot_identity_backfill_before_enforcement_sql`
- `test_backend_image_appends_one_shot_extra_args_without_overriding_compose_args`
- `test_release_runtime_env_package_contains_target_bound_edhr_endpoint`
- `test_release_error_state_updates_are_bounded_and_secret_redacted`

## TDD Evidence

- RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py::test_publish_script_runs_route_snapshot_identity_backfill_before_enforcement_sql scripts/tests/test_release_sql_preflight_gate.py::test_backend_image_appends_one_shot_extra_args_without_overriding_compose_args scripts/tests/test_release_sql_preflight_gate.py::test_release_runtime_env_package_contains_target_bound_edhr_endpoint scripts/tests/test_release_sql_preflight_gate.py::test_release_error_state_updates_are_bounded_and_secret_redacted -q` -> FAIL, all four assertions absent before the fix.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_deploy_precheck_report_contract.py -q` -> PASS, 23 tests.
- GREEN: PowerShell parser check for `ops/deploy/publish-int-ruoyi.ps1` -> PASS.

## Risk and Scope

The fix changes only the maintenance release image startup contract, release-state error serialization, and generated runtime environment metadata. It does not alter application business logic or manually mutate test data. A new committed maintenance HEAD and new releaseTag are required before retrying publish.

## Blockers / Follow-up

The failed `r260819e-r2` tag remains invalid. Before a new publish, the exact test lock must be formally marked `FAILED`, the stale `.env IMAGE_TAG` must be reconciled using the recorded prepublish evidence, and a fresh remote precheck must pass. No failed tag may be reused.

## Verification

The regression fix is committed separately from the release attempt. A new frozen release worktree and releaseTag are required to prove the fix in a real test-server publish; this document does not claim deployment success.

---

## Commit-bound Change Notes Bug Summary

`build-release` generated a valid package whose `sourceRepos` correctly identified the frozen application commit, but both manifest v1 and the frontend `release-info.json` emitted only generic releaseTag/component text. The package therefore could not prove that its displayed change notes described the code it contained.

## Commit-bound Change Notes Expected Behavior

For every included source repository, release metadata must read the subject of the exact commit already recorded in `sourceRepos`. Manifest v1 and frontend `release-info.json` must use the same changeSet containing the commit subject and short commit id. Missing or unreadable commit metadata must fail the build; generated packages must not be patched after build.

## Commit-bound Change Notes Reproduction

- Build operation: `op-2026-08-19T155932383630800Z-bf57b59b-0327-46d9-86c1-53e233b37888`.
- ReleaseTag: `release-20260819-intmain-head-test-r260819f-r2`.
- Frozen application commit: `adeb3aabc89e03d1f231552015d37bc78e0f2adb`, subject `任务: 修复C00发布后空哈希`.
- Observed manifest/release-info summary: generic `Release package <releaseTag>` with only release package and component scope items.

## Commit-bound Change Notes Root Cause

`New-ReleaseChangeSetManifest` accepted only `PackageTag`; it did not receive `sourceRepos` or resolve commit metadata. Both manifest v1 and `Write-FrontendReleaseInfo` reused this generic function, so the defect affected the package and runtime console together.

## Commit-bound Change Notes Regression Test

- Update `scripts/tests/publish_release_info_contract.test.mjs` to require `SourceRepos`, exact-commit `git show -s --format=%s`, commit-bound items, and the same generated changeSet in manifest and release-info.

## Commit-bound Change Notes TDD Evidence

- RED: `node --test scripts/tests/publish_release_info_contract.test.mjs` -> FAIL，4 tests 中 3 个按预期失败；缺少 sourceRepos 参数、exact-commit subject 读取、short commit item 和 manifest/release-info 一致调用。
- GREEN: `node --test scripts/tests/publish_release_info_contract.test.mjs` -> PASS, 4 tests.
- GREEN: PowerShell parser check for `ops/deploy/publish-int-ruoyi.ps1` -> PASS.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_deploy_precheck_report_contract.py scripts/tests/test_release_package_slimming.py -q` -> PASS, 27 tests.
- GREEN: isolated PowerShell function probe against frozen commit `adeb3aabc89e...` -> summary and item contain `任务: 修复C00发布后空哈希` and short commit id.

## Unrelated Regression Note

`publish_frontend_deploy_sql_gate_contract.test.mjs` remains a pre-existing stale textual assertion in the broader Node command; it is outside this fix scope and is recorded as P044 in `execution-log.md`. The commit-bound targeted contract and release pytest suite are the applicable verification gates for this change.

## Commit-bound Change Notes Risk and Scope

The fix changes release metadata generation only. It does not change application code, database migrations, image contents other than generated `release-info.json`, or any server state. Because metadata enters the image and checksummed manifest, the existing releaseTag is invalid and a new committed maintenance HEAD plus new releaseTag are mandatory.

## Commit-bound Change Notes Blockers / Follow-up

Do not publish `r260819f-r2`. After the fix passes tests and is committed, create a new task-specific clean maintenance worktree, keep the same recorded application commit unless explicitly changed, rebuild, and verify manifest plus image release-info before `publish-test`.
