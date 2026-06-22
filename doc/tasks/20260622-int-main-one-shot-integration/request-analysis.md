# Request Analysis

## User Goal

把 `D:\ProjectPackage\Int\IntRuoyi` 当前 holding 现场里的有效改动按阶段真正融合进 `int_main`，同时保住原始未提交工作现场，不让主线和 holding 状态混在一起。

## Current System

- backend 真正的 `int_main` 当前由 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean` 持有，最近已包含 DCC 文件名识别修复。
- frontend 真正的 `int_main` 当前由 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean` 持有。
- 原始 backend 工作区 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 已切到 `codex/20260622-ruoyi-vue-pro-int-main-hold`，仍保留大量未提交改动。
- 原始 frontend 工作区 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 已切到 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，仍保留未提交改动。
- 当前 holding 改动经过初步盘点，至少分为：
  - backend `DCC 审阅矩阵`
  - backend `DCC 受控预览文件名识别残留`
  - backend `MES 自动排产 / preflight`
  - frontend `DCC 审阅矩阵页签`

## Constraints

- 必须遵守 `AGENTS.md`：不引入 fallback、不静默降级、先建档、严格记录请求与命令。
- 根目录 Git 不是融合依据；以前后端两个仓库各自的 `int_main` 为准。
- 原始脏工作区不能直接当成最终提交源，同文件混合 hunk 必须在干净 `int_main` worktree 重放。
- 未经再次授权，不操作正式服；本轮默认只做本机 Git/worktree/测试收口。
- 用户不懂代码，需要保持任务边界清晰、结论简单。

## Unknowns

- backend MES 排产这组改动当前是否已有独立任务文档和完整验证证据。
- DCC 审阅矩阵后端改动与已入主线的 DCC 文件名识别是否存在同文件级别的额外冲突。
- frontend `package.json` 改动是否仅为 DCC 审阅矩阵静态合同测试引入，还是混入了其他目标。

## Risks

- 直接从 holding 工作区整文件复制可能把不属于当前逻辑组的残留一起带进主线。
- backend 某些文件同时包含“已入主线的 DCC 文件名识别”和“尚未入主线的 DCC 审阅矩阵”，如果分组不清会重复污染历史。
- MES 排产改动如果没有任务归属或验证前置，不应被伪装成“今天也一起并了”。
- 如果不先挂起旧的页面发布主线任务，维护仓状态会同时存在两个正在推进的高风险主线。

## Validation Surface

- maintenance 仓任务文档、执行日志、请求命令日志
- holding 工作区 `git status --short`、`git diff --stat`、关键 diff 片段
- clean `int_main` worktree 上的 scoped 测试命令
- 最终两个真实 `int_main` worktree 的 `git log --oneline` 与原始 holding 工作区分支状态

## Blocking Prerequisites

- 当前文档与盘点阶段无硬阻塞。
- 进入真正合并前，必须先明确每一组改动的 owning task 和 scoped validation。
