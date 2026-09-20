# Bug Regression Evidence

## Bug
发布按钮静态复查仍 FAIL：R1-R5 涉及旧包复用、租约泄漏、派发/授权后未知态提前释放、正式发布前置拒绝误判废包、构建阶段/失败定位不真实。

## Expected
同一按钮工作流必须绑定当前批准来源 tuple；安全终态释放 lease，未知执行态保留隔离；正式发布前置拒绝不改变 TESTED；构建阶段由维护脚本 `RELEASE_WORKFLOW_STAGE` 事件驱动。

## Reproduction
- 静态复查报告确认 R1-R5。
- RED: 应用仓 `mvn.cmd -pl yudao-module-infra '-Dtest=ReleaseWorkflowOrchestratorTest#consumedProductionAuthorizationDispatchFailureKeepsWorkflowIsolated' '-Dsurefire.failIfNoSpecifiedTests=false' test` -> FAIL, expected `RECOVERY_REQUIRED` but was `FAILED`.

## Root Cause
工作流去重身份缺少批准来源 tuple；租约生命周期缺少恢复终态释放和未知态隔离；正式执行前置校验晚于部分状态推进；构建阶段缺少执行器输出事件。

## Regression Tests
- 应用仓 ReleaseWorkflow 相关 JUnit：31/31 PASS。
- 应用仓 RuntimeControlServiceImpl 发布合同 JUnit：2/2 PASS。
- 维护仓发布脚本静态 pytest：12/12 PASS。

## GREEN
- GREEN: 应用仓 R3 单测 -> PASS, 1 test。
- GREEN: 应用仓 ReleaseWorkflow clean 定向回归 -> PASS, 31 tests。
- GREEN: 应用仓 RuntimeControlServiceImpl 低层合同 -> PASS, 2 tests。
- GREEN: 维护仓 `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py` -> PASS, 12 tests。

## Verification
- `git diff --check` passed for task-owned application workflow files and maintenance script/test files.
- No real release/server/database/E2E path was executed.

## Blockers
- 提交、推送、task-closeout apply、worktree 清理和最终 completed 标记需要用户当轮明确授权。
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
