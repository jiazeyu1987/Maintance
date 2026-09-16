# 20260916 发布按钮复查遗留问题修复

## Current Status
in_progress

## 任务目标
在维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m` 继续补齐发布脚本与测试验收合同，支持应用仓 S3/S4 的显式结果、可信操作人和失败时不产生 tested 凭据；完成严格验证后，为测试服按钮发布提供可审计执行器。

## 里程碑与预期验证
1. [completed] 建立维护仓任务记录与经验门禁。
2. [completed] 定向验证 `ops/deploy/publish-int-ruoyi.ps1` 在测试块和构建块前输出 `RELEASE_WORKFLOW_STAGE`。
3. [completed] 更新任务记录和验证报告；不执行真实发布、服务器写入、数据库写入或 worktree 清理。
4. [completed] 先补脚本合同回归测试取得 RED，再实现显式 PASS 结果、操作人透传和失败分支约束。
5. [pending] 在应用、维护提交结果上创建新的临时发布 worktree，完成脚本发布前置验证。
6. [pending] 支持并验证一次测试服发布按钮调用，记录 releaseTag、运行态和发布后问题处理结果。
7. [pending] 完成维护仓 task-owned 清理与最终记录。

## 经验门禁
- app-release 工作流门禁：维护仓脚本只作为受控执行器，必须服务主程序 workflow；不得回退到 `code-only/with-data` 或生成数据制品。
- 发布执行门禁：用户已明确授权本轮通过发布按钮执行一次测试服发布；脚本只能服务单一 releaseTag 的 `build-release -> publish-test`，不得自行执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- PowerShell/UTF-8 门禁：PowerShell 禁用 `&&`；中文文档读写必须 UTF-8；脚本命令必须有后置断言。
- Git/脏工作区门禁：维护 worktree 有大量既有未提交/未跟踪改动；只提交本任务脚本、测试和任务记录，不清理非本任务产物；发布必须从新的干净临时 worktree 执行。
- E2E/数据门禁：发布后运行态由真实页面和服务器状态共同核对，失败必须暴露并停止，不用 mock、默认值或静默跳过掩盖。

## BDD 场景
- BDD: build stages reflect real execution events -> Given build-release enters contract tests and application build, When the maintenance script logs progress, Then it emits TESTING before tests and BUILDING before build so the app workflow can show real stages.
- BDD: script accepts only structured test result -> Given mark-tested is invoked, When the script receives PASS, Then it may write tested evidence; when the result is FAIL or missing, Then it refuses to write tested evidence.
- BDD: script records authenticated operator -> Given the app passes requestedBy as OperatorName, When tested evidence is written, Then TestedBy equals that value rather than the machine account.
- BDD: direct mark-tested operation keeps structured PASS contract -> Given the generic mark-tested operation is still available to authorized operators, When the frontend submits it, Then the request carries `testResult=PASS` and the backend forwards the authenticated operator to the script.

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，阶段状态来自执行器事件而不是成功后补写。
- 是否存在临时补丁或绕过：否。

## 当前阻塞
- 暂无已确认阻塞；发布前置、测试服访问或脚本合同不满足时必须 fail fast 并记录精确影响。
