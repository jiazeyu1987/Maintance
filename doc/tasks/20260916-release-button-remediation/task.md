# 20260916 发布按钮复查遗留问题修复

## Current Status
blocked

## 任务目标
继续修复指定提交发布按钮静态复查报告中的 S1-S4：恢复态列表读取、写阶段取消隔离、测试验收显式 PASS/FAIL、可信 TestedBy；随后在新的临时发布 worktree 中通过真实发布按钮执行一次测试服发布，并闭环处理发布后的运行态问题。

## 里程碑与预期验证
1. [completed] 建立任务记录、经验门禁和 BDD/TDD 场景。
2. [completed] 为 R1-R5 增加或更新回归测试，先取得 RED 证据。
3. [completed] 修改后端编排、状态、租约和阶段证据逻辑，并同步维护仓脚本/合同测试。
4. [completed] 运行目标 JUnit/静态合同及相关回归验证，记录 GREEN/REGRESSION。
5. [completed] 更新任务文档、请求命令日志和最终验证报告；提交/推送因缺少用户当轮明确授权未执行。
6. [completed] 按 BDD + 严格 TDD 修复应用仓和维护仓 S1-S4，并完成回归验证。
7. [completed] 分别提交任务实现，创建只读目标提交对应的临时发布 worktree。
8. [completed] 完成 R89 测试服发布，核对发布闭环和发布后运行态。
9. [blocked] 清理本任务临时产物，合并/删除符合条件的 worktree，标记任务 completed。
10. [completed] 按 P0/P1 优化方向补齐真实迁移前置条件、部分写入恢复态、统一写锁边界和 R82 本地 schema/package 验证门禁。
11. [completed] R85/R88 暴露的 IDI 前置数据和迁移合同问题已修复；R89 包已通过本地门禁并部署到测试服，未执行 mark-tested、promote-prod 或 promote-backup。

## 经验门禁
- app-release 工作流门禁：固定 `app-release` 程序升级包，不得回退为 `code-only/with-data`；必须覆盖持久化 workflow、环境租约、阶段证据、失败恢复、一次性正式授权和测试/正式零写入守卫。
- 发布执行门禁：用户已明确授权通过发布按钮进行一次发布；本轮只执行测试服 `build-release -> publish-test`，先读取发布/服务器/登录/备份恢复/worktree 文档并记录 `GREEN: experience-preflight -> PASS`，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- PowerShell/Maven 门禁：PowerShell 禁用 `&&`；运行 Maven 的 `-D...` 参数必须作为完整参数引用；中文读写使用 UTF-8。
- Git/脏工作区门禁：应用和维护长期 worktree 及主工作区均有既有改动；实现提交只包含本任务文件，发布输入只来自目标提交对应的干净临时发布 worktree。
- E2E/运行态门禁：真实 Playwright 路径，写入只用测试租户；发布成功必须同时核对 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、实际镜像 tag、backend health=UP、frontend HTTP 200。 
- 真实安装包门禁：测试服前不得只依赖 15/15 静态预检；必须执行最终包、同一部署脚本、待执行迁移、应用启动和页面路径的隔离演练，业务数据只使用受控测试数据且不进入发布包。
- 迁移身份门禁：每个 `requiresTargetPreflight` 迁移必须同时覆盖 SQL 内部身份校验、重复执行、历史数据和部分执行后的后置条件；预检失败必须发生在任何远端业务写入之前。
- 部分写入门禁：远端写入已开始但结果不明时，状态只能进入 `RECOVERY_REQUIRED`，保持环境隔离；只有确认零写入或完成现场恢复验收后才能释放锁。
- 统一锁边界门禁：首次远端数据库/运行目录写入前取得远端发布锁，锁需覆盖 post-import、required SQL、容器切换与验收；重启恢复必须先检查未完成任务和锁版本。

## BDD 场景
- BDD: approved source tuple changes -> Given READY/TESTED workflow exists for source tuple A, When approved commits or preset change under the same reason/sourceSelectionId, Then build-release creates or selects a workflow only for tuple B and does not return package A.
- BDD: timed-out build recovery closes safe lease -> Given a PREFLIGHTING build operation times out and recovery marks it terminal, When active workflows reconcile, Then the build lease is released and the next build can acquire it.
- BDD: dispatch unknown after operation submitted -> Given publish-test/promote-prod/build dispatch has returned an operation id, When later binding or persistence reads fail, Then the workflow remains isolated for recovery and the lease is not released as if execution never started.
- BDD: prod preflight refusal preserves TESTED -> Given a TESTED workflow and production writes disabled or confirm text invalid, When promote-prod is requested, Then no operation intent is created and the workflow remains TESTED for retry.
- BDD: build stages reflect real execution events -> Given build-release progresses through preflight, test, build and ready evidence events, When workflow status is reconciled, Then UI-visible stage and failedStage reflect the actual event rather than success backfill.
- BDD: recovery workflow is read-only -> Given a workflow is RECOVERY_REQUIRED with stale build markers, When list/detail reconciliation runs, Then it returns the record without changing stage or throwing.
- BDD: canceled write stage retains isolation -> Given a write-stage workflow owns an environment lease, When canceled, Then it enters RECOVERY_REQUIRED and the lease remains held.
- BDD: test acceptance branches explicitly -> Given TEST_DEPLOYED, When PASS is submitted, Then mark-tested records the release; when FAIL is submitted, Then the workflow fails and no tested credential is written.
- BDD: TestedBy is authenticated -> Given PASS acceptance, When mark-tested is dispatched, Then TestedBy equals server-authenticated requestedBy, not the machine account or client input.

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，目标是收敛幂等身份、租约生命周期、派发一致性和阶段事件合同。
- 是否存在临时补丁或绕过：否。

## 本轮 P0/P1 BDD
- BDD: target identity conflict is blocked before write -> Given the target has an incompatible historical `system_menu` row, When target preflight runs for the migration, Then it returns a deterministic blocker with the conflicting identity and no remote write is attempted.
- BDD: failed migration keeps recovery isolation -> Given a publish operation has acquired the remote lock and applied any write, When a later migration fails or the process is interrupted, Then workflow state is `RECOVERY_REQUIRED`, the remote lock remains held, and no automatic release is reported.
- BDD: local install rehearsal gates publish -> Given a final immutable package exists, When the same deployment script is executed in an isolated local environment, Then all pending migrations, application startup, health checks, and the real login page path pass before `publish-test` is enabled.
- BDD: heartbeat separates progress from log mtime -> Given a long-running command emits structured stage/progress evidence but log mtime is unchanged, When the monitor reconciles, Then the workflow remains active with the last structured progress timestamp and is not marked stale.

## 当前阻塞
- 发布阻塞：无。R89 已完成测试服发布与真实登录验证。
- 收尾阻塞：主维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 与主程序仓 `E:\IntRuoyi` 存在大量既有未归属改动，其中维护主工作区还包含发布脚本/测试同类文件改动；按“不得覆盖无关用户/其他任务改动”和临时 worktree 规则，当前不能安全合并 R89 提交或删除 `D:\IntRuoyiWorktree\r260917-button-publish9`。需要先由用户/相关任务归档或明确这些主工作区改动归属，再执行最终合并和 worktree 清理。
- 收尾预览：`task-closeout-cleanup` preview 仅建议删除 `bug-regression-evidence.md` 与 `database-schema-evidence.md`，但未覆盖外部发布 worktree 的合并/删除前置条件；本轮未执行 apply、未删除文件、未合并或移除任何 worktree。
in_progress

## 任务目标
在维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m` 继续补齐发布脚本与测试验收合同，支持应用仓 S3/S4 的显式结果、可信操作人和失败时不产生 tested 凭据；完成严格验证后，为测试服按钮发布提供可审计执行器。

## 里程碑与预期验证
1. [completed] 建立维护仓任务记录与经验门禁。
2. [completed] 定向验证 `ops/deploy/publish-int-ruoyi.ps1` 在测试块和构建块前输出 `RELEASE_WORKFLOW_STAGE`。
3. [completed] 更新任务记录和验证报告；不执行真实发布、服务器写入、数据库写入或 worktree 清理。
4. [completed] 先补脚本合同回归测试取得 RED，再实现显式 PASS 结果、操作人透传和失败分支约束。
5. [in_progress] 在应用、维护提交结果上创建新的临时发布 worktree，完成脚本发布前置验证。
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

## 2026-09-17 续跑状态
- 失败根因：旧应用提交 `d7f4901aa65bec54c2b56b44fbc2e387a2be07e1` 的注册证菜单迁移对退休菜单 ID 605071320/605071321 采用盲目身份假设，测试服真实数据在 `605071320` 上存在企业公司范围身份漂移，导致 `ERROR 1644`。
- 已修复提交：应用仓 `6435dfc54c37291f2b54a4c734aea43475155fd5`，退休菜单仅在完整旧身份匹配时加入待退休集合；不覆盖未知身份，不吞 SQL 失败。
- 新发布冻结：releaseTag=`release-20260917-one-button-app-r82`；维护源 `7381c6e4d27b183cca79fafda623bccb52f8a2f6`；应用/前端源 `6435dfc54c37291f2b54a4c734aea43475155fd5`；目标仅测试服 `172.30.30.58`，范围 `app-release/without-data`。
