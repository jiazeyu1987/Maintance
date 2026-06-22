# 任务：按阶段一次性融合 holding 改动进 int_main

## 任务目标

在不丢失 `D:\ProjectPackage\Int\IntRuoyi` 原始未提交现场的前提下，把当前需要收口到主线的 holding 改动按阶段融合进真正的 `int_main`。融合判断以前后端 `ruoyi-vue-pro` 与 `yudao-ui-admin-vue3` 两个 Git 仓库为准，根目录只作为协调目录。

## 上一任务检查

- 最近已完成维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-task-tab-inventory\task.md`
- 状态：`COMPLETED`
- 仍未收口但已显式挂起的维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\task.md`
- 状态：`BLOCKED`
- 处理：
  - 最近完成任务不阻塞本轮新的 `int_main` 融合任务。
  - 原“页面发布全链路”任务已因用户当前优先级切换明确挂起，避免与本任务并行推进。

## 用户要求与执行边界

- 用户要求：
  - `D:\ProjectPackage\Int\IntRuoyi` 下的改动后续真正要收口到 `int_main`
  - 本轮按阶段执行，但目标是一次性把当前 holding 现场融合进 `int_main`
  - 需要简单、确定地推进，不新建无意义的长期分叉
- 当前任务授权：
  - 允许在本机对 `ruoyi-vue-pro`、`yudao-ui-admin-vue3` 与维护仓执行 Git 审计、worktree 建立、补丁重放、测试验证与文档更新
  - 允许在干净 `int_main` 基线上创建本次融合专用 worktree/分支并提交
  - 允许更新本任务文档、执行日志、测试报告与 `docs/request-command-log.md`
- 禁止范围：
  - 未经用户再次明确授权，不触碰正式服
  - 不直接在原始脏工作区整仓提交，不把混合 hunk 硬塞进 `int_main`
  - 不为了“快并进去”引入 fallback、临时绕过、静默跳过测试或丢弃原始未提交改动

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 根目录 Git 不作为融合完成依据；以前后端两个仓库各自的 `int_main` 为准。
  - 同文件若混入多任务 hunk，不得在原始脏工作区整文件暂存，必须在干净 `int_main` worktree 里重放当前任务补丁。
  - worktree 合并前后都要记录真实归属，避免把 holding 现场误认成真正的 `int_main`。
  - 涉及 worktree 合并、切换、清理等高风险动作前，`execution-log.md` 必须先有 `GREEN: experience-preflight -> PASS`。
  - 不能把“dirty 工作区看起来像最终状态”当作已融合完成；必须以 clean 基线验证和主线提交结果闭环。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。通过干净 `int_main` 基线重放逻辑分组改动，避免把历史脏现场直接塞进主线。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 原始现场不丢失 -> Given 原始前后端工作区都存在未提交改动 / When 收口到 int_main / Then 原始现场继续保留在 holding 分支上，真正的 int_main 只接收经过分组、验证和提交的改动。`
- `BDD: DCC 审阅矩阵成组收口 -> Given frontend/backend holding 现场都存在 DCC 审阅矩阵相关改动 / When 在 clean int_main 基线重放并验证 / Then DCC 审阅矩阵前后端改动作为同一组进入真正的 int_main。`
- `BDD: 已入主线的 DCC 文件名识别不重复污染 -> Given DCC 受控预览文件名识别修复已经进入 backend int_main / When 继续处理 holding 现场 / Then 只保留主线已有结果，不重复把同一任务残留当成新改动再合一次。`
- `BDD: MES 排产改动必须有独立验证 -> Given backend holding 现场还包含 MES 自动排产与 preflight 改动 / When 评估是否并入 int_main / Then 必须先确认独立任务边界和测试命令，验证不过或边界不清时明确阻塞，不得伪装成“一次性已融合”。`

## 里程碑

1. 挂起旧维护主线并建立新的融合总任务文档。`DONE`
2. 审计前后端 holding 现场，按逻辑分组列出文件范围和主线状态。`DONE`
3. 在 clean backend `int_main` 基线重放并验证 DCC 审阅矩阵后端改动。`DONE`
4. 在 clean frontend `int_main` 基线重放并验证 DCC 审阅矩阵前端改动。`DONE`
5. 处理 backend MES 排产改动：补齐任务归属、验证并决定是否并入本轮主线。`DONE`
6. 把本轮确认可收口的分组真正并入两个仓库的 `int_main`，并回写分支/worktree 映射。`DONE`
7. 执行收尾预览并记录剩余 holding 现场。`DONE`

## 预期验证

- holding 审计：
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro diff --stat`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 diff --stat`
- DCC 审阅矩阵后端：
  - `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccCategoryApprovalMatrixAdminServiceImplTest,DccCategoryPermissionAdminServiceImplTest,DccControlledFileWorkflowServiceImplTest,DccControlledFileQueryServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
- DCC 审阅矩阵前端：
  - `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\dcc-category-governance-summary-static.spec.js`
  - `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\tests\e2e\dcc-review-matrix-tab-static.spec.js`
  - `pnpm --dir D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 ts:check`
- MES 排产：
  - `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-mes -Dtest=MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProScheduleOrderPreflightServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
- 主线收口：
  - 两个真正持有 `int_main` 的 clean worktree 上 `git log --oneline -5`
  - 原始 holding 工作区 `git branch --show-current` 与 `git status --short`

## 当前状态

COMPLETED：本轮一次性分组收口已经完成。frontend `int_main` 已保留 DCC 审阅矩阵收口结果 `2cec13de0`，backend `int_main` 已在其基础上继续快进到 MES 收口结果 `d9ba8afae5`。原始前后端工作区继续分别保留在 `codex/20260622-ruoyi-vue-pro-int-main-hold` 与 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，其中残余未提交内容仅作为 holding 现场保留，不再作为“真正 int_main 是否完成”的判断依据。`task-closeout-cleanup` 预览也已执行，通过结果显示本任务仅需保留 `task.md` 与 `execution-log.md`，无阻塞项。
