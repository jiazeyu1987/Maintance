# Release Build Preflight and Cache Optimization Test Plan

- Task ID: `release-preflight-cache-optimization-20260908`
- Created: `2026-09-08T11:13:31+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-cache-optimization-20260908\m`
- User Request: `实现构建前发布资格预检与可验证 Docker 构建缓存，减少测试服晚失败和重复全量打包，不执行真实发布。`

## Test Scope

验证 `build-release` 构建前 target-bound preflight 的调用顺序、每次重新采集、证据绑定和 fail-fast 行为；验证 backend/frontend Docker 原生缓存命令、输入指纹失效规则、构建前后漂移门禁及最终 P0 包完整性回归。测试运行真实 PowerShell 5.1、Python 3.12、JDK 17、Maven 和 Node runtime，但以本地 fixture 和命令构造合同隔离 SSH、Docker build、NAS 与服务器写入。

不测试 UI，不读取 `frontend/src/App.vue`，不运行真实 Docker build、远端连接、安装包生成、发布、数据库写入、服务重启或 NAS 写入。

## Environment

- Windows 11 and Windows PowerShell 5.1.
- Python 3.12 with pytest.
- JDK 17 at `C:\Users\BJB110\.jdks\jdk-17.0.20+8` and Maven 3.9.
- Node.js for repository JavaScript contract tests.
- Repository root is the task worktree; all commands run from that root.
- Temporary test root is `$env:TEMP\release-preflight-cache-optimization-20260908`; tests must clean task-owned fixture output.
- Docker CLI may be installed, but tests must not contact the daemon or run an image build.

## Accounts and Fixtures

- No account or credential is required or permitted.
- Minimal prospective `manifest.json` fixtures with real migration fields and staged SQL files.
- Target-state JSON fixtures covering passed, checksum drift, dependency missing, malformed, blank, and changed-ledger cases.
- Deterministic backend/frontend Dockerfile and minimal context trees under the task temporary root.
- Base-image digest and build-arg fixtures use syntactically valid non-sensitive values.
- If a test attempts SSH, NAS, database, Docker daemon, or remote service access, stop the test run and report the scope violation.

## Commands

Run focused tests first, followed by parser and broader regressions. Expected success is process exit code 0 and the stated test summary.

```powershell
python -X utf8 -m pytest "scripts/tests/test_release_build_preflight_cache.py" "scripts/tests/test_release_sql_preflight_gate.py" -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\focused"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$tokens = $null; $errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'ops\deploy\publish-int-ruoyi.ps1'), [ref]$tokens, [ref]$errors); if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"

python -X utf8 -m pytest "scripts/tests" "tests" -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\full"

$env:JAVA_HOME = "C:\Users\BJB110\.jdks\jdk-17.0.20+8"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
mvn.cmd -f "backend\pom.xml" test

node --test "scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs" "scripts/tests/publish_image_tar_transfer_contract.test.mjs" "scripts/tests/publish_release_info_contract.test.mjs"
```

Do not use `scripts/verify_contracts.py` as a completion gate while the concurrent user-owned deletion of `frontend/src/App.vue` remains present, because that command reads the missing file. The independent tester must instead run all release-focused Python, PowerShell, Java, and Node commands above and record this pre-existing exclusion explicitly.

## Test Cases

### T1: Preflight precedes every expensive build

- Covers: P1-AC1
- Level: integration/contract
- Command: focused pytest call-order case plus PowerShell AST command.
- Expected: prospective manifest creation, fresh target-state collection and planner invocation occur after required SQL staging and before the first Maven, frontend build and Docker build call.

### T2: Every build recollects target state and fails closed

- Covers: P1-AC2
- Level: integration
- Command: focused pytest parameterized fixture cases.
- Expected: two invocations have distinct collection identity; existing evidence is ignored; SSH/query failure, blank output, malformed JSON, missing ledger and planner error each produce nonzero status before expensive command probes.

### T3: Evidence schema is complete and contains no sensitive material

- Covers: P1-AC3
- Level: unit/integration
- Command: focused pytest evidence-schema and forbidden-key/value cases.
- Expected: all mandatory binding fields and UTC/ID formats are present; serialized evidence contains no password, token, secret, connection string or raw `.env` field.

### T4: Blocked or invalid evidence cannot qualify a build

- Covers: P1-AC4
- Level: integration
- Command: focused pytest status/action/digest parameterized cases.
- Expected: blocked plan, `BLOCKED_*`, unsupported action, missing binding and digest mismatch all fail before Maven/frontend/Docker probe files can be created.

### T5: Preflight fingerprints are deterministic and drift-sensitive

- Covers: P1-AC5
- Level: unit
- Command: focused pytest fixed-vector and one-field mutation cases.
- Expected: identical normalized inputs yield the fixed expected digest; changing source commit, SQL byte, target-state value, environment or scope changes the digest or fails validation.

### T6: Application image builds use native cache

- Covers: P2-AC1
- Level: contract
- Command: focused pytest Docker argument construction/source contract cases.
- Expected: backend and frontend commands use Docker build without `--no-cache`; no cache bypass or weak-validation switch is added.

### T7: Docker input fingerprints cover all material inputs

- Covers: P2-AC2
- Level: unit
- Command: focused pytest fixed-vector and independent mutation cases.
- Expected: Dockerfile, each normalized context file, backend base digest and every build arg contribute to the correct backend/frontend fingerprint.

### T8: Unsafe, missing or drifting Docker inputs fail fast

- Covers: P2-AC3
- Level: integration
- Command: focused pytest invalid-input and before/after mutation cases.
- Expected: missing file, traversal, duplicate/case collision, invalid digest and between-check mutation each return nonzero before Docker save or package-copy probes.

### T9: Final manifest records reproducible build evidence

- Covers: P2-AC4
- Level: integration
- Command: focused pytest manifest fixture reconstruction cases.
- Expected: each included image exposes input, Dockerfile, context, base/build-args and actual image digest fields; tester recomputation equals recorded values and a changed field fails.

### T10: Cache does not bypass package governance

- Covers: P2-AC5
- Level: regression
- Command: focused pytest lifecycle-order case and `scripts/tests/test_release_package_governance.py` within the full suite.
- Expected: image inspect/save and final manifest/package/NAS-copy verification remain unconditional and ordered after build; P0 tamper, missing and extra-file tests still pass.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | build-release | preflight ordering | integration/contract | P1-AC1 | `test-report.md#T1` |
| T2 | target-state | fresh collection and failure branches | integration | P1-AC2 | `test-report.md#T2` |
| T3 | evidence | complete and non-sensitive schema | unit/integration | P1-AC3 | `test-report.md#T3` |
| T4 | qualification gate | blocked/invalid rejection | integration | P1-AC4 | `test-report.md#T4` |
| T5 | preflight digest | determinism and drift | unit | P1-AC5 | `test-report.md#T5` |
| T6 | Docker command | native cache enabled | contract | P2-AC1 | `test-report.md#T6` |
| T7 | Docker fingerprint | material input coverage | unit | P2-AC2 | `test-report.md#T7` |
| T8 | Docker gate | invalid and drifting inputs | integration | P2-AC3 | `test-report.md#T8` |
| T9 | package metadata | reproducible image evidence | integration | P2-AC4 | `test-report.md#T9` |
| T10 | P0 governance | immutable package regression | regression | P2-AC5 | `test-report.md#T10` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: Windows PowerShell 5.1, Python 3.12, pytest, JDK 17, Maven 3.9, Node.js, Git
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run the listed commands against the actual task worktree with the real local runtimes. Local fixtures replace dangerous external side effects only; they cannot manufacture a passing command result.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main Agent explicitly requests discrepancy analysis.

## Pass / Fail Criteria

- Pass when: T1-T10 all pass; every acceptance ID is evidenced; AST parsing, focused and full pytest, JDK 17 Maven and Node tests exit 0; no test performs external writes; P0 package governance regressions remain green.
- Fail when: any acceptance ID lacks a passing case; any command fails or is skipped without an approved scope reason; evidence can be stale, incomplete or sensitive; a blocked preflight reaches an expensive command; cache inputs can drift without invalidation; `--no-cache` remains on application image builds; or package integrity can be bypassed.
- A missing required runtime, fixture contract or readable source file is a blocker, not a pass.

## Regression Scope

- Existing `release_preflight_plan.py` migration ordering, checksum equivalence, allowed-environment, code-only scope and dependency behavior.
- P0 exact payload, manifest/package digest, tested attestation and NAS post-copy integrity tests.
- Existing release SQL policy/staging and Spring constructor/frontend dependency preflight ordering contracts.
- Runtime-control backend action construction and Node release-info contracts that do not require the missing frontend page.
- PowerShell 5.1 parsing and UTF-8 evidence serialization.

## Reporting Notes

Write independent first-pass results to `test-report.md` with environment versions, exact commands, per-case PASS/FAIL, evidence references and final verdict. Record the known `frontend/src/App.vue` exclusion separately; do not restore, generate or alter that user-owned file. Redact any unexpectedly observed credential and fail the task if evidence serialization exposes it.
