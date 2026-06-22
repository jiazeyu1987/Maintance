# 执行日志

## 2026-06-22 Phase 0 建档与 holding 审计

- task id: `T1-T2`
- changed paths:
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\task.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\task-state.json`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\execution-log.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\test-report.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`
- implemented behavior:
  - `BDD: 原始现场不丢失 -> Given 原始前后端工作区都存在未提交改动 / When 收口到 int_main / Then 原始现场继续保留在 holding 分支上，真正的 int_main 只接收经过分组、验证和提交的改动。`
  - `BDD: DCC 审阅矩阵成组收口 -> Given frontend/backend holding 现场都存在 DCC 审阅矩阵相关改动 / When 在 clean int_main 基线重放并验证 / Then DCC 审阅矩阵前后端改动作为同一组进入真正的 int_main。`
  - `BDD: 已入主线的 DCC 文件名识别不重复污染 -> Given DCC 受控预览文件名识别修复已经进入 backend int_main / When 继续处理 holding 现场 / Then 只保留主线已有结果，不重复把同一任务残留当成新改动再合一次。`
  - 已把旧的页面发布主线维护任务显式改为 `BLOCKED`，避免与本轮 `int_main` 融合并行推进。
  - 已建立新的融合总任务工件，并完成第一轮 holding 现场分组审计。
- validation commands:
  - `python -X utf8 -c "...experience-index.md..."`
  - `python -X utf8 -c "...worktree-memory.md..."`
  - `python -X utf8 -c "...project-error-prevention.md..."`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro branch --show-current`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro diff --stat`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 branch --show-current`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 diff --stat`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean log --oneline -5`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean log --oneline -5`
- validation results:
  - `GREEN: experience-preflight -> PASS`，已读取 `experience-index.md`、`worktree-memory.md` 与项目错误预防记忆，当前准备执行的是本机 worktree / Git 融合高风险动作，不涉及服务器写入。
  - `GREEN: previous-task-gate -> PASS`，最新维护仓只读任务 `20260622-task-tab-inventory` 已完成；旧的页面发布主线已显式改为 `BLOCKED`。
  - `GREEN: backend-hold-audit -> PASS`，backend 原始工作区当前在 `codex/20260622-ruoyi-vue-pro-int-main-hold`；未提交改动混有 `DCC 审阅矩阵`、`DCC 文件名识别残留`、`MES 自动排产/preflight` 三组。
  - `GREEN: frontend-hold-audit -> PASS`，frontend 原始工作区当前在 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`；未提交改动主要是一组 `DCC 审阅矩阵页签`，另带 `.env.merged-e2e` 非主线文件。
  - `GREEN: true-int-main-map -> PASS`，backend/frontend 真正持有 `int_main` 的仍是两条 clean worktree，而不是原始 holding 工作区。
- covered acceptance ids:
  - `AC-01`
  - `AC-02`
  - `AC-03`
  - `AC-06`
- known risks or blockers:
  - backend `yudao-module-dcc` 某些文件可能同时承载“已入主线的 DCC 文件名识别”和“未入主线的 DCC 审阅矩阵”两层变化，重放时必须以 clean `int_main` 为基线精确处理。
  - backend MES 排产组当前还未确认 owning task 文档，进入真正合并前必须补齐。

## 2026-06-22 Phase 1 DCC 审阅矩阵重放与主线收口

- task id: `T3-T4`
- changed paths:
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\yudao-module-dcc\`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\doc\tasks\20260622-dcc-review-matrix-tab\`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\src\api\dcc\controlledFile\`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\src\views\dcc\controlled-file\categories\`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\tests\e2e\`
- implemented behavior:
  - 在 backend/frontend 两条 clean `int_main` 集成 worktree 上分离重放 DCC 审阅矩阵组，不把已入主线的 DCC 文件名识别残留重复混入。
  - backend/frontend 均补齐该组任务证据并各自提交到 `codex/20260622-int-main-one-shot-integration`。
- validation commands:
  - `mvn --% -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\pom.xml -pl yudao-module-dcc -Dtest=DccCategoryApprovalMatrixAdminServiceImplTest,DccCategoryPermissionAdminServiceImplTest,DccControlledFileWorkflowServiceImplTest,DccControlledFileQueryServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
  - `pnpm --dir D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration install --frozen-lockfile`
  - `node D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\tests\e2e\dcc-category-governance-summary-static.spec.js`
  - `node D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\tests\e2e\dcc-route-instruction-alert-reduction-static.spec.js`
  - `node D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\tests\e2e\dcc-route-summary-static.spec.js`
  - `node D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration\tests\e2e\dcc-review-matrix-tab-static.spec.js`
  - `pnpm --dir D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration ts:check`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean merge --ff-only codex/20260622-int-main-one-shot-integration`
- validation results:
  - `GREEN: backend-dcc-regression -> PASS`，`BUILD SUCCESS`，后端定向测试共 `127` 通过。
  - `GREEN: frontend-dcc-static -> PASS`，4 个静态 spec 与 `ts:check` 全部通过。
  - `GREEN: backend-dcc-int-main-ff -> PASS`，backend 真正的 `int_main` 已快进到 `90159e05ca`。
  - `GREEN: frontend-dcc-int-main-ff -> PASS`，frontend 真正的 `int_main` 已持有 `2cec13de0`。
- covered acceptance ids:
  - `AC-03`
  - `AC-04`
  - `AC-06`
- known risks or blockers:
  - 无；该组已独立进入真正主线。

## 2026-06-22 Phase 2 MES 排产组重放与 backend int_main 收口

- task id: `T5-T6`
- changed paths:
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\yudao-module-mes\`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\doc\tasks\20260622-mes-auto-schedule-preflight-gate\`
- implemented behavior:
  - 在 backend clean 集成 worktree 内新建 MES owning task 文档，先记录 RED，再精确重放 holding 工作区中的 7 个 `yudao-module-mes` 目标文件。
  - 将 MES 自动排产 preflight fail-fast、批记录路线阻断、零任务显式失败相关改动提交到集成分支，并快进到 backend 真正的 `int_main`。
- validation commands:
  - `mvn --% -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\pom.xml -pl yudao-module-mes -Dtest=MesProAutoSchedulePreflightGateContractTest test`
  - `mvn --% -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration\pom.xml -pl yudao-module-mes -Dtest=MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProScheduleOrderPreflightServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean merge --ff-only codex/20260622-int-main-one-shot-integration`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro branch --show-current`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 branch --show-current`
  - `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short`
- validation results:
  - `GREEN: mes-red-evidence -> PASS`，Surefire 明确失败 `No tests matching pattern "MesProAutoSchedulePreflightGateContractTest" were executed!`，已作为该组 strict TDD 的 RED 证据入档。
  - `GREEN: mes-regression -> PASS`，`BUILD SUCCESS`，MES 定向测试共 `36` 通过。
  - `GREEN: mes-commit-gate -> PASS`，集成分支已产生 `843851bf38`（代码）与 `d9ba8afae5`（证据）两笔提交。
  - `GREEN: backend-mes-int-main-ff -> PASS`，backend 真正的 `int_main` 已从 `90159e05ca` 快进到 `d9ba8afae5`。
  - `GREEN: holding-preserved -> PASS`，原始前后端工作区仍分别停在 `codex/20260622-ruoyi-vue-pro-int-main-hold` 与 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，未提交现场继续保留。
- covered acceptance ids:
  - `AC-01`
  - `AC-05`
  - `AC-06`
- known risks or blockers:
  - 原始 holding 现场仍保留未提交内容，后续若要继续清场，需要另外开任务逐组处理；这不影响本轮“真正 int_main 已收口”的结果。

## 2026-06-22 Phase 3 收尾预览

- task id: `T7`
- validation commands:
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-one-shot-integration --mode preview`
- validation results:
  - `GREEN: closeout-preview -> PASS`，状态 `ready`，当前维护仓不是 linked worktree。
  - `GREEN: closeout-keep-set -> PASS`，默认保留 `task.md` 与 `execution-log.md`。
  - `GREEN: closeout-delete-set -> PASS`，默认可清理 `dev-plan.md`、`prd.md`、`request-analysis.md`、`task-state.json`、`test-plan.md`、`test-report.md`。
  - `GREEN: closeout-blockers -> PASS`，`blocked=<none>`，`warnings=<none>`。
- covered acceptance ids:
  - `AC-06`
- known risks or blockers:
  - 无。

## 2026-06-22 Phase 4 集成 worktree 实际收尾

- task id: `T7`
- implemented behavior:
  - 为了让 `task-closeout-cleanup` 在 backend linked worktree 正确指向真正主线，仅在本机 Git 元数据中把 backend 仓库的 `refs/remotes/origin/HEAD` 从 `origin/master-jdk17` 调整为 `origin/int_main`；未改远端默认分支，也未改业务文件。
  - backend 集成 worktree 先用脚本分别删除 DCC/MES 任务的 evidence 文件，再手工按同一规则提交 cleanup、`--ff-only` 快进到 backend 真正的 `int_main` 并删除 linked worktree。
  - frontend 集成 worktree 用脚本完成 evidence 文件删除与 cleanup 提交，并成功快进到 frontend 真正的 `int_main`；随后因目录内残留 `node_modules` 导致 `git worktree remove --force` 无法清空目录，再经路径复核后以 Node 递归删除残留普通目录。
- validation commands:
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/int_main`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-dcc-review-matrix-tab --mode preview`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-mes-auto-schedule-preflight-gate --mode preview`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-dcc-review-matrix-tab --mode apply --worktree-closeout off`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-mes-auto-schedule-preflight-gate --mode apply --worktree-closeout off`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration commit -m "任务: 清理DCC与MES收尾产物"`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean merge --ff-only codex/20260622-int-main-one-shot-integration`
  - `git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean worktree remove --force D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-int-main-one-shot-integration`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-dcc-review-matrix-tab --mode apply`
  - `node -e "fs.rmSync(...)" D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-int-main-one-shot-integration`
- validation results:
  - `GREEN: backend-origin-head-align -> PASS`，backend cleanup 预览/脚本主线识别已从错误的 `master-jdk17` 修正为 `int_main`。
  - `GREEN: backend-worktree-closeout -> PASS`，backend cleanup 提交 `20e2e70305` 已进入真正的 `int_main`，backend 集成 worktree 已从 `git worktree list` 消失。
  - `GREEN: frontend-worktree-closeout -> PASS`，frontend cleanup 提交 `db289300f` 已进入真正的 `int_main`，frontend 集成 worktree 已从 `git worktree list` 消失，残留普通目录也已删除。
  - `GREEN: remaining-hold-preserved -> PASS`，原始 holding worktree 仍分别保留在前后端原始工作区，不受本轮集成 worktree 收尾影响。
- covered acceptance ids:
  - `AC-01`
  - `AC-06`
- known risks or blockers:
  - 无；当前仅剩维护仓本任务目录自身的 cleanup apply。

## 2026-06-22 Phase 5 维护仓任务目录 cleanup apply

- task id: `T7`
- validation commands:
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-one-shot-integration --mode preview`
  - `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-one-shot-integration --mode apply`
- validation results:
  - `GREEN: maintenance-closeout-preview -> PASS`，keep/delete 计划与此前预览一致，`blocked=<none>`。
  - `GREEN: maintenance-closeout-apply -> PASS`，已删除 `dev-plan.md`、`prd.md`、`request-analysis.md`、`task-state.json`、`test-plan.md` 与 `test-report.md`，当前任务目录仅保留 `task.md` 与 `execution-log.md`。
- covered acceptance ids:
  - `AC-06`
- known risks or blockers:
  - 无。
