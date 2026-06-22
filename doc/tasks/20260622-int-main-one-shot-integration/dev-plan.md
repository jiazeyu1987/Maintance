# Development Plan

## Task Graph

### T1

- task_id: `T1`
- title: `挂起旧主线并建立融合总台账`
- objective: 把旧的页面发布主线显式改为阻塞状态，并创建本轮 `int_main` 融合总任务文档。
- dependency_ids: `[]`
- affected_paths:
  - `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/`
  - `doc/tasks/20260622-int-main-one-shot-integration/`
  - `docs/request-command-log.md`
- write_scope:
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`
- acceptance_ids:
  - `AC-01`
  - `AC-06`
- validation_steps:
  - 复核旧任务 `task.md` 与 `task-state.json` 已改为 `BLOCKED`
  - 复核新任务所需文档全部存在
- done_definition: 旧主线不再处于进行中，新主线文档与状态文件已落地。

### T2

- task_id: `T2`
- title: `审计 holding 现场并分组`
- objective: 用真实 `git status --short`、`git diff --stat` 与关键 diff 片段，确认 holding 现场的逻辑组边界。
- dependency_ids:
  - `T1`
- affected_paths:
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
  - `doc/tasks/20260622-int-main-one-shot-integration/`
- write_scope:
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`
- acceptance_ids:
  - `AC-01`
  - `AC-02`
  - `AC-03`
- validation_steps:
  - 复核前后端 holding 分支名、状态和 diff 统计
  - 抽样关键 diff，确认 DCC 与 MES 组边界
- done_definition: 已形成“哪些文件属于哪一组、哪些已经在 int_main”的明确结论。

### T3

- task_id: `T3`
- title: `重放并验证 DCC 审阅矩阵后端`
- objective: 在 clean backend `int_main` 基线上只重放 DCC 审阅矩阵后端改动，并完成 scoped Maven 回归。
- dependency_ids:
  - `T2`
- affected_paths:
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean`
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-dcc-review-matrix-tab\`
- write_scope:
  - `yudao-module-dcc/**`
  - `doc/tasks/20260622-dcc-review-matrix-tab/**`
- acceptance_ids:
  - `AC-03`
  - `AC-04`
- validation_steps:
  - 仅重放 DCC 审阅矩阵相关后端文件
  - 运行 DCC 审阅矩阵 scoped Maven 测试
- done_definition: clean backend 基线获得可提交的 DCC 审阅矩阵后端改动并验证通过。

### T4

- task_id: `T4`
- title: `重放并验证 DCC 审阅矩阵前端`
- objective: 在 clean frontend `int_main` 基线上只重放 DCC 审阅矩阵前端改动，并完成静态合同和 `ts:check`。
- dependency_ids:
  - `T2`
- affected_paths:
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\doc\tasks\20260622-dcc-review-matrix-tab\`
- write_scope:
  - `src/api/dcc/controlledFile/**`
  - `src/views/dcc/controlled-file/categories/**`
  - `tests/e2e/dcc-review-matrix-tab*`
  - related DCC static contract tests
- acceptance_ids:
  - `AC-04`
  - `AC-06`
- validation_steps:
  - 运行 DCC 审阅矩阵静态合同测试
  - 运行 `pnpm ts:check`
- done_definition: clean frontend 基线获得可提交的 DCC 审阅矩阵前端改动并验证通过。

### T5

- task_id: `T5`
- title: `处理 backend MES 排产组`
- objective: 为 backend MES 自动排产 / preflight 改动确认 owning task、重放路径和 scoped 验证，并在可验证时并入 clean backend 基线。
- dependency_ids:
  - `T2`
- affected_paths:
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-mes\`
  - `doc/tasks/20260622-int-main-one-shot-integration/`
- write_scope:
  - `yudao-module-mes/**`
  - owning task doc if missing
- acceptance_ids:
  - `AC-05`
  - `AC-06`
- validation_steps:
  - 明确 MES 组对应任务边界
  - 运行 scoped MES Maven 测试
  - 若边界或前置不足，显式记录 blocker
- done_definition: MES 组要么验证后进入 clean backend 主线，要么明确阻塞并给出精确原因。

### T6

- task_id: `T6`
- title: `推进真正 int_main 并回写映射`
- objective: 将本轮已验证通过的分组真正并入两个仓库的 `int_main`，并更新维护仓记录。
- dependency_ids:
  - `T3`
  - `T4`
  - `T5`
- affected_paths:
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean`
  - `doc/tasks/20260622-int-main-one-shot-integration/`
  - `docs/request-command-log.md`
- write_scope:
  - clean `int_main` worktrees
  - maintenance task docs
  - request command log
- acceptance_ids:
  - `AC-01`
  - `AC-03`
  - `AC-04`
  - `AC-05`
  - `AC-06`
- validation_steps:
  - 检查两个真正 `int_main` worktree 的 `git log --oneline`
  - 检查原始 holding 工作区仍停在 holding 分支
- done_definition: 真正的 `int_main` 已包含本轮允许进入主线的分组，维护仓台账也同步更新。

### T7

- task_id: `T7`
- title: `收尾预览`
- objective: 运行本任务的 closeout preview，并记录仍需保留的 holding 现场。
- dependency_ids:
  - `T6`
- affected_paths:
  - `doc/tasks/20260622-int-main-one-shot-integration/`
- write_scope:
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\`
- acceptance_ids:
  - `AC-06`
- validation_steps:
  - 运行 `task-closeout-cleanup --mode preview`
  - 复核只保留正式任务证据和仍需保留的 holding 现场说明
- done_definition: 已形成可收尾预览结果，并清楚说明哪些 holding 现场仍然保留。
