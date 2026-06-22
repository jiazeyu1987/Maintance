# Test Plan

## TC-01 文档与旧主线挂起

- test_case_id: `TC-01`
- mapped_task_ids:
  - `T1`
- mapped_acceptance_ids:
  - `AC-01`
  - `AC-06`
- environment or setup:
  - 维护仓本地文件系统
- steps:
  - 复核旧页面发布任务 `task.md` 和 `task-state.json`
  - 复核新融合任务八个工件是否存在
- expected_result:
  - 旧任务为 `BLOCKED`
  - 新任务工件完整落地
- evidence:
  - `task.md`
  - `task-state.json`
  - 新任务目录文件列表

## TC-02 holding 分组审计

- test_case_id: `TC-02`
- mapped_task_ids:
  - `T2`
- mapped_acceptance_ids:
  - `AC-02`
  - `AC-03`
- environment or setup:
  - 原始 backend/frontend holding 工作区
- steps:
  - 运行前后端 `git branch --show-current`
  - 运行前后端 `git status --short` 与 `git diff --stat`
  - 抽样关键 diff 片段确认 DCC 与 MES 组边界
- expected_result:
  - 能明确列出 backend 与 frontend 各自的逻辑组
  - 能确认 DCC 文件名识别已经进入 backend `int_main`
- evidence:
  - `execution-log.md`
  - `docs/request-command-log.md`

## TC-03 DCC 审阅矩阵后端验证

- test_case_id: `TC-03`
- mapped_task_ids:
  - `T3`
- mapped_acceptance_ids:
  - `AC-03`
  - `AC-04`
- environment or setup:
  - clean backend `int_main` 基线
- steps:
  - 在 clean backend 基线重放 DCC 审阅矩阵后端文件
  - 运行 scoped Maven 测试
- expected_result:
  - 仅 DCC 审阅矩阵相关后端文件进入待提交状态
  - scoped Maven 测试通过
- evidence:
  - backend `git diff --stat`
  - Maven 测试输出
  - backend 任务 `execution-log.md`

## TC-04 DCC 审阅矩阵前端验证

- test_case_id: `TC-04`
- mapped_task_ids:
  - `T4`
- mapped_acceptance_ids:
  - `AC-04`
  - `AC-06`
- environment or setup:
  - clean frontend `int_main` 基线
- steps:
  - 在 clean frontend 基线重放 DCC 审阅矩阵前端文件
  - 运行静态合同测试
  - 运行 `pnpm ts:check`
- expected_result:
  - 仅 DCC 审阅矩阵前端相关文件进入待提交状态
  - 静态合同和 `ts:check` 通过
- evidence:
  - frontend `git diff --stat`
  - Node/PNPM 测试输出
  - frontend 任务 `execution-log.md`

## TC-05 MES 排产组验证

- test_case_id: `TC-05`
- mapped_task_ids:
  - `T5`
- mapped_acceptance_ids:
  - `AC-05`
- environment or setup:
  - backend holding 工作区与 clean backend `int_main` 基线
- steps:
  - 确认 MES 改动的 owning task 或新建任务文档
  - 在 clean backend 基线重放 MES 文件
  - 运行 scoped MES Maven 测试
- expected_result:
  - 如果 owning task 和验证充足，则 MES 组可以形成可提交结果
  - 否则显式阻塞并记录精确缺口
- evidence:
  - MES 任务文档
  - Maven 测试输出或 blocker 记录

## TC-06 最终主线映射核对

- test_case_id: `TC-06`
- mapped_task_ids:
  - `T6`
  - `T7`
- mapped_acceptance_ids:
  - `AC-01`
  - `AC-04`
  - `AC-05`
  - `AC-06`
- environment or setup:
  - 真正持有 `int_main` 的 clean worktrees 与原始 holding 工作区
- steps:
  - 检查两个 clean `int_main` worktree 的 `git log --oneline -5`
  - 检查原始 holding 工作区的分支和工作树仍在
  - 运行收尾预览
- expected_result:
  - 用户可以明确看到真正 `int_main` 与原始 holding 现场分别位于哪里
  - closeout preview 不误删需要保留的现场
- evidence:
  - `execution-log.md`
  - `task-closeout-cleanup` preview 输出
