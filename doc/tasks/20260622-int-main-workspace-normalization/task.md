# 任务：恢复原始工作区并清理 int_main 临时承载 worktree

## 任务目标

在不丢失 `D:\ProjectPackage\Int\IntRuoyi` 原始前后端现场的前提下，把原始前后端目录恢复成更直观的主线状态：能恢复的目录切回真正的 `int_main`，不再需要的临时承载 worktree 与 holding 分支按验证结果清理。

## 当前状态

COMPLETED：前端原始目录已恢复为真正的 `int_main`；后端原始目录也已在补齐 DCC / BPM / eDHR readiness 主线结果后切回 `int_main`。当前 backend 只保留主仓目录这一份 worktree，额外 linked worktree 已全部清理完成；backend holding 分支仅作为历史分支指针保留，不再承载工作区。

## Current Status

COMPLETED

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\task.md`
- 状态：`COMPLETED`
- 处理：
  - 上一任务已经完成“按阶段一次性融合进 int_main”与集成 worktree 收尾。
  - 本任务只处理“原始目录是否切回 int_main、holding 分支是否可删、临时承载 worktree 是否可删”的后续整理，不重做上一任务的代码收口。

## 用户要求与执行边界

- 用户要求：
  - 说明 `ruoyi-vue-pro-dcc-preview-int-main-clean`、`codex/20260622-ruoyi-vue-pro-int-main-hold`、`codex/20260622-yudao-ui-admin-vue3-int-main-hold` 的作用
  - 如已融合进 `int_main`，帮助处理能删除的 worktree/holding 分支
  - 保留 DCC 改动，同时把后端内容都融合进 `int_main`，并只保留一个 backend worktree
- 当前任务授权：
  - 允许在本机审计、切换、删除本轮相关 Git worktree 与 holding 分支
  - 允许把原始前后端目录切回真正的 `int_main`，前提是切换前已确认不会覆盖未提交现场
  - 允许更新维护仓任务文档、执行日志与 `docs/request-command-log.md`
- 禁止范围：
  - 不因“想简化目录”而丢弃原始未提交内容
  - 不触碰服务器、正式环境或远程默认分支
  - 不使用 fallback、临时补丁、静默跳过验证或强行 `reset --hard`

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
- 本任务强制门禁摘录：
  - worktree 合并、切换、清理、删除前必须确认真实归属，避免误删真正主线承载目录。
  - 清理前必须预览并确认只处理本任务 worktree、运行时和临时产物。
  - 涉及高风险 worktree 切换/清理前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS`。
  - 根目录 Git 不作为判断项，以前后端各自仓库与 `git worktree list` 为准。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是。目标是把“真正承载主线的目录”和“仅用于保留现场的目录”重新恢复成直观状态，而不是继续长期保留临时承载 worktree。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 前端原始目录可直接回主线 -> Given 前端原始目录只剩不影响切分支的未跟踪文件 / When 切回 int_main 并删除 holding 分支 / Then 前端原始目录恢复为真正主线目录，holding 分支可安全移除。`
- `BDD: 后端原始目录只有在内容安全时才回主线 -> Given 后端原始目录仍有本地改动 / When 比对这些改动与真正 int_main 的文件内容 / Then 仅在确认不会覆盖现场时才切回 int_main 并删除多余承载 worktree，否则明确保留阻塞。`
- `BDD: 临时承载 worktree 只在原始目录恢复后删除 -> Given 原始目录已经接管真正 int_main / When 再清理临时承载 worktree / Then 主线结果继续保留，但临时目录不再占用认知成本。`

## 里程碑

1. 建立恢复原始工作区任务台账并复核前后端 worktree/holding 现状。`DONE`
2. 核对前端原始目录，若安全则切回 `int_main` 并删除前端 holding 分支。`DONE`
3. 核对后端原始目录的本地改动与真正 `int_main` 的文件内容差异，判断能否切回。`DONE`
4. 若后端安全切回，则删除后端临时承载 worktree 与 holding 分支；若不安全，则明确阻塞原因。`DONE`

## 完成/阻塞结论

- 前端：
  - 原始目录 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 已切回 `int_main`
  - `codex/20260622-yudao-ui-admin-vue3-int-main-hold` 已删除
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean` 已删除
  - 原始目录内仍保留现存本地改动与 `.env.merged-e2e`，未丢失
- 后端：
  - DCC 相关主线结果继续保留在 `int_main`，并已通过 DCC 定向回归验证
  - `39b2d15f6b` `任务: 修正eDHR BPM通知迁移依赖`、`9a96ca4f68` `任务: 新增eDHR演练预检`、`2b538ad5dd` `任务: 补齐eDHR预检模板与BPM门禁`、`fffbba0c89` `任务: 补充eDHR预检回归证据` 已进入 backend `int_main`
  - 原始目录 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 当前直接承载 `int_main`
  - `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-release`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 已删除
  - `codex/20260622-ruoyi-vue-pro-int-main-hold` 仍保留为 branch 指针，但不再绑定任何 worktree

## 预期验证

- `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short --branch`
- `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro worktree list`
- `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro branch --list codex/20260622-ruoyi-vue-pro-int-main-hold`
- `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short --branch`
- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileQueryServiceTest,DccControlledFileReviewMatrixAccessServiceTest,DccControlledFilePreviewProtectionTest,DccOnlyOfficeControlledPreviewTest -Dsurefire.failIfNoSpecifiedTests=false test`
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_edhr_bpm_notify_to_inbox_sql.py -q`
- `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql`
- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-bpm -Dtest=BpmMessageServiceImplTest -Dsurefire.failIfNoSpecifiedTests=false test`
- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-mes -Dtest=MesProScheduleOrderPreflightServiceTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProEdhrRehearsalReadinessServiceTest,MesProEdhrBatchExecutionControllerTest -Dsurefire.failIfNoSpecifiedTests=false test`
