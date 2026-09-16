# Bug Regression Evidence

## Bug
发布按钮 R5 复查指出构建阶段和失败定位仍未接入真实执行阶段，应用侧只能在 operation succeeded 后补写 TESTING/BUILDING/READY，维护脚本缺少供主程序消费的阶段事件证据。

## Expected
维护仓 `ops/deploy/publish-int-ruoyi.ps1` 在 build-release 进入标准合同测试前输出 `RELEASE_WORKFLOW_STAGE=TESTING`，在进入后端/前端/Docker 构建前输出 `RELEASE_WORKFLOW_STAGE=BUILDING`，主程序据此推进 UI-visible stage 和 failedStage。

## Reproduction
- 静态复查报告确认 R5 仍存在。
- RED: 首轮复查证据显示维护脚本没有可供应用仓读取的 `RELEASE_WORKFLOW_STAGE` 阶段事件，构建阶段只能成功后回填。

## Root Cause
脚本执行器没有对外输出稳定、可解析的 workflow stage marker；应用编排器也没有从 operation log 读取阶段事件。

## Regression Tests
- `scripts/tests/test_release_workflow_preflight.py::test_build_release_emits_workflow_stage_markers_before_test_and_build_blocks`
- app 仓 `ReleaseWorkflowOrchestratorTest#buildLogStageMarkersAdvanceRunningWorkflowBeforeOperationCompletes`
- app 仓 `ReleaseWorkflowOrchestratorTest#failedBuildUsesLastObservedBuildStage`
- app 仓 `ReleaseWorkflowOrchestratorTest#recoveryRequiredBuildWithObservedStageLogStaysReadable`
- app 仓 `ReleaseWorkflowOrchestratorTest#cancelDuringTestDeploymentKeepsTestLeaseIsolatedForRecovery`
- app 仓 `ReleaseWorkflowOrchestratorTest#failedTestAcceptanceFailsWorkflowWithoutWritingTestedAttestation`
- app 仓 `RuntimeControlServiceImplTest#executeMarkReleaseTestedShouldRequireExplicitPassResult`
- frontend static contract `runtime-control-one-button-static.spec.cjs`
- `scripts/tests/test_release_package_governance.py::test_mark_tested_requires_explicit_pass_result_before_creating_attestation`

## GREEN
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py -k "workflow_stage_markers or app_release"` -> PASS, 3 selected tests.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py` -> PASS, 12 tests.
- GREEN: `mvn.cmd -f D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\pom.xml -pl yudao-module-infra '-Dtest=ReleaseWorkflowOrchestratorTest,ReleaseWorkflowSourceBindingTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowStoreTest,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test` -> PASS, 102 tests.
- GREEN: `node D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs` -> PASS.
- GREEN: `corepack pnpm run ts:check` -> PASS.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_package_governance.py --basetemp .pytest-tmp-release-button-current-all` -> PASS, 86 tests.

## Verification
- Static pytest confirms marker function exists and marker ordering is before the relevant test/build blocks.
- `git diff --check` passed for maintenance script/test files.

## Blockers
- No real build-release, publish-test, mark-tested, promote-prod, promote-backup, server/database write, E2E, commit or push executed in this turn.
- Final `completed` status and repository commits require user current-turn explicit authorization under the nearest project rules.
