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
