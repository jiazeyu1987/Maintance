# PRD

## Goal

把 `D:\ProjectPackage\Int\IntRuoyi` 当前需要收口的 holding 改动按逻辑组、安全地并入真正的 `int_main`，同时保留原始未提交现场，避免继续把 clean `int_main` 与原始 holding 工作区混用。

## Scope

- maintenance 仓内的融合总台账、状态管理和执行证据
- backend holding 改动分组、重放、验证和并入 `int_main`
- frontend holding 改动分组、重放、验证和并入 `int_main`
- 对“已在 `int_main` 的改动”和“尚未在 `int_main` 的改动”做明确区分

## Non-Goals

- 不继续推进旧的页面发布 `prod -> backup` 主线
- 不在本轮默认操作正式服
- 不清理原始 holding 工作区中的剩余未提交现场，除非收尾阶段确认只是本任务附属产物

## User or System Scenarios

1. 作为用户，我希望 `D:\ProjectPackage\Int\IntRuoyi` 下真正代表主线的就是 `int_main`，而不是某个临时 worktree 或脏工作目录。
2. 作为维护者，我需要知道 holding 现场里到底有几组改动，哪些已经进入主线，哪些还没进入。
3. 作为集成人员，我需要在干净 `int_main` 基线上重放和验证改动，避免把用户原始未提交工作一起提交。

## Functional Requirements

- 系统必须先把当前 holding 改动按逻辑组列清楚，并标注对应仓库、文件范围和任务归属。
- 系统必须区分“已经在 `int_main` 的 DCC 文件名识别修复”和“仍停留在 holding 的其他改动”。
- DCC 审阅矩阵前后端改动必须分别在 clean `int_main` 基线重放并通过 scoped 验证后，才能并入真正的 `int_main`。
- backend MES 排产改动必须先确认 owning task 与 scoped validation，验证通过后才能并入真正的 `int_main`。
- 系统必须保留原始 holding 工作区与 holding 分支，不得通过融合过程丢失未提交现场。
- 维护仓必须更新任务文档、执行日志、测试报告和请求命令日志，说明最终 `int_main` 与 holding 现场各自位于哪里。

## Non-Functional Requirements

- 不引入 fallback、mock 成功或静默跳过验证
- 所有文档与日志使用 UTF-8 明确编码
- Git 操作必须非交互、可追溯，并优先使用 clean worktree
- 结论必须能让非技术用户理解当前哪些改动已经进入主线、哪些还没有

## Dependencies and Constraints

- 依赖现有 clean `int_main` worktree：
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean`
- 依赖原始 holding 工作区保留现场：
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 依赖已有 DCC 审阅矩阵任务文档：
  - backend `20260622-dcc-review-matrix-tab`
  - frontend `20260622-dcc-review-matrix-tab`
- 若 MES 排产组缺少 owning task 或 scoped validation，则必须阻塞并报告

## Acceptance Criteria

- `AC-01` 原始 frontend/backend 工作区继续停留在 holding 分支并保留未提交现场，没有因本轮融合丢失文件或内容。
- `AC-02` 已产出 holding 改动分组清单，明确区分 backend `DCC 审阅矩阵`、backend `DCC 文件名识别残留`、backend `MES 排产`、frontend `DCC 审阅矩阵页签`。
- `AC-03` backend 真正的 `int_main` 明确保留已进入主线的 DCC 文件名识别修复，且本轮不重复把该残留当成新任务再次并入。
- `AC-04` DCC 审阅矩阵前后端改动在 clean `int_main` 基线完成重放、scoped 验证和并入，且没有混入无关文件。
- `AC-05` backend MES 排产改动在并入前已经明确 owning task、边界和 scoped validation；若任何一项缺失，任务必须显式阻塞并说明原因，而不是伪装成已完成融合。
- `AC-06` 维护仓文档与 `docs/request-command-log.md` 已更新，用户可以直接看到真正 `int_main` 和 holding 现场分别位于哪里，以及本轮哪些组已经进入主线。
