# 发布流水线 P0 加固最终独立测试报告

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: Windows 11; PowerShell 5.1.26100.3624; Python 3.12.10; pytest 8.4.2; JDK `C:\Users\BJB110\.jdks\jdk-17.0.20+8` (OpenJDK 17.0.20); Maven 3.9.16; Node 24.12.0; pnpm 10.22.0; Git 2.55.0.windows.5
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Tested workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-pipeline-hardening-20260907\m`. Tested HEAD: `82c4d44de6a845f38e3fbf2083786e542e4f596b`. Verification completed at `2026-09-08T02:01:36.994Z`. The system `$env:TEMP` parent existed. No NAS, SSH, Docker, database, MinIO, or server access was performed.

## Results

### T1: Mode 强制并删除 direct

- Result: passed
- Covers: P1-AC1
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real Windows PowerShell parameter binding and AST parsing; governance suite reported 57 passed in 38.58s.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_mode_is_mandatory_and_direct_is_rejected_before_script_body`; `ops/deploy/publish-int-ruoyi.ps1`
- Notes: Mode is mandatory, has no default, excludes direct, and rejects direct or missing Mode before side effects.

### T2: with-data 生产级拒绝

- Result: passed
- Covers: P1-AC2
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Scope matrix executed through the real PowerShell governance module; external-action probe remained absent.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_release_package_scope_matrix_blocks_production_data_packages_before_probe`; `ops/release/lib/ReleasePackageGovernance.psm1`
- Notes: with-data passes for test and fails for prod and backup; code-only passes for all three environments.

### T3: scope 门禁早于外部动作

- Result: passed
- Covers: P1-AC3
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real script source ordering and fail-on-call local probes were evaluated; probe count was 0 after rejection.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_scope_gate_is_wired_before_remote_or_deployment_actions`; `ops/deploy/publish-int-ruoyi.ps1`
- Notes: Scope validation precedes SSH, remote environment, directory, Docker, database, and MinIO actions.

### T4: 显式命令兼容

- Result: passed
- Covers: P1-AC4
- Command run: `$env:JAVA_HOME='C:\Users\BJB110\.jdks\jdk-17.0.20+8'; $env:Path="$env:JAVA_HOME\bin;$env:Path"; mvn.cmd -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test`
- Environment proof: Maven ran under Java 17.0.20 and reported BUILD SUCCESS; 26 tests, 0 failures, 0 errors, 0 skipped.
- Evidence refs: `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlContractTest.java`; `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`; `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java`
- Notes: Runtime control emits only explicit build-release, deploy-release, and mark-tested package modes while retaining legal code-only test/prod/backup arguments.

### T5: artifact 精确覆盖 payload

- Result: passed
- Covers: P2-AC1
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real local files were hashed and sized by the PowerShell module in an isolated pytest fixture.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_integrity_verifier_exactly_covers_payload_and_includes_manifest_json`; `ops/release/lib/ReleasePackageGovernance.psm1`
- Notes: The artifact set exactly matches the immutable payload, includes manifest.json, and validates path, bytes, and SHA-256 from actual files.

### T6: 摘要稳定且变化敏感

- Result: passed
- Covers: P2-AC2
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Fixed-vector fixtures were verified across distinct absolute roots with real SHA-256 computation.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_package_digest_uses_fixed_vector_and_is_root_separator_independent`; `scripts/tests/test_release_package_governance.py::test_payload_or_manifest_change_changes_digest_or_fails`
- Notes: Identical content yields the same packageDigest across roots and separators; payload or manifest changes alter the digest or fail validation.

### T7: 完整性负例矩阵

- Result: passed
- Covers: P2-AC3
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Parameterized real-file fixtures exercised tamper, missing, extra, bytes/hash, invalid path, duplicate, and case-conflict cases.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_integrity_verifier_rejects_all_payload_drift`
- Notes: Every negative case returned nonzero and named the affected path and mismatch, missing, undeclared, invalid, or duplicate reason.

### T8: 四个生命周期位置强制校验

- Result: passed
- Covers: P2-AC4
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Structural source contract inspected the actual publish script and verifier call ordering.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_same_verifier_guards_all_four_package_lifecycle_points`; `ops/deploy/publish-int-ruoyi.ps1`
- Notes: The same verifier gates local build, post-NAS copy, post-download deploy, and pre-write mark-tested lifecycle points.

### T9: attestation 精确排除

- Result: passed
- Covers: P2-AC5
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Isolated package fixtures tested each controlled mutable metadata path and an undeclared non-whitelist file.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_only_controlled_mutable_metadata_is_excluded_from_payload`; `ops/release/lib/ReleasePackageGovernance.psm1`
- Notes: Only tested.json, rollback-compatibility.json, prod-latest.json, backup-latest.json, prod-deployments/**, and backup-deployments/** are excluded from immutable payload coverage.

### T10: operation 严格选择

- Result: passed
- Covers: P3-AC1
- Command run: `$env:JAVA_HOME='C:\Users\BJB110\.jdks\jdk-17.0.20+8'; $env:Path="$env:JAVA_HOME\bin;$env:Path"; mvn.cmd -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test`
- Environment proof: Java tests used real JSON operation-store files, forced their mtimes equal, and ran through Spring MockMvc under JDK 17.
- Evidence refs: `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`; `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java`
- Notes: Only exact test/publish-test/SUCCESS/releaseTag matches are accepted. Equal-mtime fixtures selected by requestedAt descending and then operationId descending: mark selected `op-current-test-release`, prod selected `op-prod-dry-run-test`, backup selected `op-publish-test-pass`.

### T11: 服务端证据所有权和脚本交叉验证

- Result: passed
- Covers: P3-AC2
- Command run: `$env:JAVA_HOME='C:\Users\BJB110\.jdks\jdk-17.0.20+8'; $env:Path="$env:JAVA_HOME\bin;$env:Path"; mvn.cmd -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test`; `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real backend command preparation and PowerShell JSON validation ran locally; client-forged operation ID and path were absent from the command.
- Evidence refs: `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`; `scripts/tests/test_release_package_governance.py::test_mark_tested_rejects_invalid_operation_without_overwriting_existing_attestation`
- Notes: The server owns operation selection; PowerShell independently checks operationId, environment, action, status, releaseTag, and requestedAt.

### T12: tested 字段和原子写入

- Result: passed
- Covers: P3-AC3
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real filesystem writes verified UTF-8 JSON output, atomic replacement, prior-byte preservation, and no temporary-file residue.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_mark_tested_writes_atomic_v2_attestation_bound_to_package_and_operation`; `scripts/tests/test_release_package_governance.py::test_mark_tested_rejects_missing_or_malformed_operation_without_creating_attestation`
- Notes: tested v2 contains every required field and bound digest/operation value; failed prerequisites do not create, truncate, or overwrite attestation bytes.

### T13: prod 与 backup 强绑定矩阵

- Result: passed
- Covers: P3-AC4
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`
- Environment proof: Real PowerShell module calls accepted valid prod and backup attestations and rejected every mutated field before a fail-on-call external probe.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_valid_attestation_allows_both_production_grade_environments`; `scripts/tests/test_release_package_governance.py::test_prod_and_backup_reject_every_stale_or_forged_attestation_field_before_probe`; `scripts/tests/test_release_package_governance.py::test_promotion_recomputes_payload_and_rejects_drift_before_probe`
- Notes: Both environments recompute payload, packageDigest, and manifestDigest and require exact tag, directory, digest, environment, operation ID/status, requestedAt, testedAt, tester, and conclusion values.

### T14: 删除 backup 和 RequireTested 绕过

- Result: passed
- Covers: P3-AC5
- Command run: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance-final"`; PowerShell Parser AST checks for `ops/deploy/publish-int-ruoyi.ps1` and `ops/release/lib/ReleasePackageGovernance.psm1`
- Environment proof: Both PowerShell files parsed with 0 errors; source contract ran against current production files.
- Evidence refs: `scripts/tests/test_release_package_governance.py::test_production_attestation_gate_is_unconditional_and_precedes_remote_actions`; `ops/deploy/publish-int-ruoyi.ps1`; `ops/release/lib/ReleasePackageGovernance.psm1`
- Notes: RequireTested and TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED bypass semantics are absent; prod and backup require attestation unconditionally before remote actions.

### T15: 合法本地闭环与回归

- Result: passed
- Covers: P3-AC6
- Command run: governance pytest (57 passed); focused pytest (65 passed); full pytest (146 passed); Maven directed tests (26 passed); `node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs scripts/tests/publish_image_tar_transfer_contract.test.mjs scripts/tests/publish_release_info_contract.test.mjs` (6 passed); `python -X utf8 scripts/verify_contracts.py`; `git diff --check`; two PowerShell AST checks
- Environment proof: Commands ran in the designated worktree with JDK 17 and independent temp roots; all exit codes were 0, Maven reported BUILD SUCCESS, and no test was skipped.
- Evidence refs: `scripts/tests/test_release_package_governance.py`; `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`; `scripts/verify_contracts.py`; `scripts/tests/*.test.mjs`
- Notes: The legal code-only fixture completed exact mark, prod gate, and backup gate success against the same tag, package, manifest, and SUCCESS publish-test operation; external probe count remained 0. `git diff --check` emitted only non-failing LF/CRLF worktree warnings and no whitespace errors.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P2-AC1, P2-AC2, P2-AC3, P2-AC4, P2-AC5, P3-AC1, P3-AC2, P3-AC3, P3-AC4, P3-AC5, P3-AC6
- Blocking prerequisites:
- Summary: T1-T15 and every P1-P3 acceptance criterion passed using real local PowerShell, Python, JVM, Node, filesystem, hash, JSON, and contract execution. Required commands all exited 0 with no relevant skip or xfail. Equal operation-file mtimes did not affect deterministic requestedAt/operationId selection, and mark/prod/backup exact-success paths passed without external access or fallback behavior.

## Open Issues

- None.
