# 测试报告

## 2026-06-22 Audit Gate

- task id or phase id: `T1-T2`
- tested cases:
  - `TC-01`
  - `TC-02`
- actual result:
  - 旧的页面发布主线任务已从 `IN_PROGRESS` 明确改为 `BLOCKED`。
  - 新的 `20260622-int-main-one-shot-integration` 工件已创建。
  - holding 审计已确认 backend 至少混有三组改动，frontend 主要是一组 DCC 审阅矩阵页签改动。
  - backend 真正的 `int_main` 仍持有 DCC 文件名识别修复，frontend 真正的 `int_main` 仍位于 clean worktree。
- expected result:
  - 在进入真正重放和主线提交前，必须先明确旧主线已挂起、holding 组边界已清楚、真正 `int_main` 所在路径已核定。
- pass or fail: `PASS`
- evidence:
  - `execution-log.md` 中 `2026-06-22 Phase 0 建档与 holding 审计`
  - 原始 holding 工作区的 `git status --short` / `git diff --stat`
  - clean `int_main` worktree 的 `git log --oneline -5`
- blockers:
  - backend MES 排产组的 owning task 尚待补齐或确认。
- unresolved issues:
  - 下一阶段需要在 clean `int_main` 基线上逐组重放，并对 DCC 与 MES 分组分别执行 scoped 验证。

## 2026-06-22 Integration And Closeout Audit

- task id or phase id: `T3-T7`
- tested cases:
  - `TC-03`
  - `TC-04`
  - `TC-05`
  - `TC-06`
- actual result:
  - DCC 审阅矩阵后端在 clean 集成基线执行定向 Maven 回归，`127` 个测试通过，并已进入 backend 真正的 `int_main`。
  - DCC 审阅矩阵前端在 clean 集成基线执行 4 个静态 spec 与 `ts:check`，全部通过，并已进入 frontend 真正的 `int_main`。
  - MES 自动排产/preflight 组先记录 RED，再执行定向 Maven 回归，`36` 个测试通过，并已把 backend 真正的 `int_main` 快进到 `d9ba8afae5`。
  - `task-closeout-cleanup` 预览返回 `ready`，仅建议保留 `task.md` 与 `execution-log.md`，无阻塞项。
  - 原始前后端 working tree 仍保留在各自 holding 分支，未提交现场没有被这轮主线收口覆盖或丢失。
- expected result:
  - 真正的前后端 `int_main` 分别持有本轮应收口的 DCC / MES 改动。
  - 原始 holding 现场继续保留。
  - 收尾预览可正常生成 keep/delete 计划且无 blocked。
- pass or fail: `PASS`
- evidence:
  - `execution-log.md` 中 `Phase 1 DCC 审阅矩阵重放与主线收口`
  - `execution-log.md` 中 `Phase 2 MES 排产组重放与 backend int_main 收口`
  - `execution-log.md` 中 `Phase 3 收尾预览`
  - backend 真正 `int_main` 的 `git log --oneline -5`
  - frontend 真正 `int_main` 的 `git log --oneline -5`
- blockers:
  - 无阻塞当前目标完成的 blocker。
- unresolved issues:
  - 原始 holding 工作区仍有残余未提交内容；如需继续清场，应以新任务逐组处理。
