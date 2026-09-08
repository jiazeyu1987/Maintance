# Independent Test Report

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes
- Workspace: D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-cache-optimization-20260908\m
- Operating system / shell: Windows 11 / Windows PowerShell 5.1.26100.3624
- Python / pytest: Python 3.12.10 / pytest 8.4.2
- Java / Maven: Microsoft OpenJDK 17.0.20 at C:\Users\BJB110\.jdks\jdk-17.0.20+8 / Apache Maven 3.9.16
- Node.js: v24.12.0
- Temporary root: $env:TEMP\release-preflight-cache-optimization-20260908
- External systems: not accessed; no SSH, NAS, Docker daemon, database, server, or remote service access
- Withheld artifacts read: no

## Initial Verdict

- Outcome: failed
- Withheld artifacts read: no
- Reason: Recorded before test execution; no acceptance criterion was considered satisfied without direct evidence.

## Results

### T1: Preflight precedes every expensive build

- Result: passed
- Covers: P1-AC1
- Command run: `python -X utf8 -m pytest "scripts/tests/test_release_build_preflight_cache.py" "scripts/tests/test_release_sql_preflight_gate.py" -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\focused"`; PowerShell AST parse command from the test plan.
- Environment proof: Python 3.12.10 with pytest 8.4.2; Windows PowerShell 5.1.26100.3624 parser.
- Evidence refs: Focused suite 96 passed; AST exited 0; `scripts/tests/test_release_build_preflight_cache.py::test_publish_script_orders_fresh_test_preflight_before_expensive_builds`; `ops/deploy/publish-int-ruoyi.ps1:5885-5981`.
- Notes: Source order is required SQL staging, target-bound preflight, backend/frontend build, then Docker build.

### T2: Every build recollects target state and fails closed

- Result: passed
- Covers: P1-AC2
- Command run: Focused pytest command from T1; independent source inspection of the preflight collector and runner failure paths.
- Environment proof: Python 3.12.10 and the checked PowerShell 5.1 source in the task worktree.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_invalid_target_state_fails_closed`; `scripts/tests/test_release_build_preflight_cache.py::test_blocked_plan_is_written_but_cannot_qualify_build`; `ops/deploy/publish-int-ruoyi.ps1:3913-4009`.
- Notes: Each invocation deletes prior local evidence, creates a fresh UUID/UTC timestamp, and fails immediately on SSH nonzero, blank output, invalid JSON, invalid ledger, or planner failure.

### T3: Evidence schema is complete and contains no sensitive material

- Result: passed
- Covers: P1-AC3
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2 using local credential-free fixtures.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_runner_writes_complete_deterministic_binding_evidence`; `scripts/tests/test_release_build_preflight_cache.py::test_evidence_excludes_sensitive_manifest_material`.
- Notes: Evidence binds source, staged SQL, prospective manifest, target state, environment/scope, collection identity/time, and planner status/items without serializing sensitive manifest values.

### T4: Blocked or invalid evidence cannot qualify a build

- Result: passed
- Covers: P1-AC4
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2; PowerShell ordering inspected after successful AST parsing.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_blocked_plan_is_written_but_cannot_qualify_build`; `scripts/tests/test_release_build_preflight_cache.py::test_verify_rejects_invalid_or_tampered_evidence`; `ops/release/release_build_preflight.py:280-325`.
- Notes: Blocked dependencies persist blocked evidence and return nonzero; tampered status, action, binding, or digest cannot qualify before application builds.

### T5: Preflight fingerprints are deterministic and drift-sensitive

- Result: passed
- Covers: P1-AC5
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2 using deterministic local fixtures.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_runner_is_deterministic_except_fresh_collection_identity`; `scripts/tests/test_release_build_preflight_cache.py::test_material_input_drift_changes_binding_or_fails`; `scripts/tests/test_release_build_preflight_cache.py::test_planner_migrations_must_exactly_match_required_sql`; `scripts/tests/test_release_build_preflight_cache.py::test_source_repo_must_explicitly_be_clean`.
- Notes: Source, SQL, target state, environment, and scope drift changes the binding or fails; requiredSql/schemaMigrations are equivalent and dirty must explicitly equal false.

### T6: Application image builds use native cache

- Result: passed
- Covers: P2-AC1
- Command run: Focused pytest command from T1; direct inspection of backend and frontend Docker argument arrays.
- Environment proof: Python 3.12.10 contract tests and PowerShell 5.1-parsed release script.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_publish_script_uses_native_cache_and_keeps_governance_order`; `ops/deploy/publish-int-ruoyi.ps1:5981-5998`.
- Notes: Both application image commands omit `--no-cache` and contain no cache-bypass or weak-validation option.

### T7: Docker input fingerprints cover all material inputs

- Result: passed
- Covers: P2-AC2
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2 using local Dockerfile/context fixtures without contacting Docker.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_docker_evidence_covers_only_dockerfile_copy_inputs_args_and_base`; `scripts/tests/test_release_build_preflight_cache.py::test_docker_input_fingerprint_changes_for_every_material_input`; `ops/release/release_docker_build_evidence.py:107-236`.
- Notes: Fixed vector and independent Dockerfile, context, build-arg, and base-digest mutations passed; normalized COPY inputs are sorted deterministically.

### T8: Unsafe, missing or drifting Docker inputs fail fast

- Result: passed
- Covers: P2-AC3
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2 using task-owned temporary fixtures.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_docker_input_contract_fails_closed`; `scripts/tests/test_release_build_preflight_cache.py::test_docker_input_drift_after_build_is_rejected`; `ops/deploy/publish-int-ruoyi.ps1:6001-6021`.
- Notes: Missing input, traversal, duplicate input, invalid base digest, missing build arg, and after-capture mutation return nonzero before actual-image evidence, save, manifest, integrity, or NAS copy.

### T9: Final manifest records reproducible build evidence

- Result: passed
- Covers: P2-AC4
- Command run: Focused pytest command from T1.
- Environment proof: Python 3.12.10 with pytest 8.4.2 using local image-identity fixtures.
- Evidence refs: `scripts/tests/test_release_build_preflight_cache.py::test_final_docker_evidence_records_actual_images_and_recomputes`; `ops/release/release_docker_build_evidence.py:253-321`; package artifact `manifest/docker-build-evidence.json`.
- Notes: Final immutable evidence records input, Dockerfile, context, base/build-args, actual image identity, and evidence digests after recomputing captured inputs.

### T10: Cache does not bypass package governance

- Result: passed
- Covers: P2-AC5
- Command run: `python -X utf8 -m pytest "scripts/tests" "tests" -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\full"`; `$env:JAVA_HOME = "C:\Users\BJB110\.jdks\jdk-17.0.20+8"; mvn.cmd -f "backend\pom.xml" test`; `node --test "scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs" "scripts/tests/publish_image_tar_transfer_contract.test.mjs" "scripts/tests/publish_release_info_contract.test.mjs"`.
- Environment proof: Python 3.12.10 / pytest 8.4.2; Microsoft OpenJDK 17.0.20 / Maven 3.9.16; Node.js v24.12.0.
- Evidence refs: Full Python regression 188 passed; Maven 26 passed with 0 failures/errors/skips; Node 6 passed; `scripts/tests/test_release_build_preflight_cache.py::test_publish_script_uses_native_cache_and_keeps_governance_order`; `scripts/tests/test_release_package_governance.py`; `ops/deploy/publish-int-ruoyi.ps1:6001-6079`.
- Notes: Lifecycle remains input verification, actual image inspection/evidence, Docker save, release manifest hashes, package integrity, then NAS copy verification.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3, P2-AC4, P2-AC5
- Blocking prerequisites:
- Summary: T1-T10 passed in the required real local runtimes. The implementation fails closed on incompatible or stale preflight inputs before expensive builds, binds Docker cache qualification to material inputs and actual images, and preserves unconditional P0 package governance ordering.

## Open Issues

- `scripts/verify_contracts.py` was not run, exactly as excluded by the approved test plan, because it reads the concurrent user-owned missing `frontend/src/App.vue`; no file was restored or altered.
- The first AST shell invocation was rejected by outer PowerShell command-string expansion of `$tokens` and `$errors`. The same parser check was immediately rerun with literal quoting and exited 0; this was a test harness quoting issue, not a product parse failure.
- No live build-release invocation was made because it would contact SSH and the Docker daemon, both explicitly prohibited. External-call behavior and ordering were verified through local fixtures, focused contracts, AST parsing, and direct source inspection.
