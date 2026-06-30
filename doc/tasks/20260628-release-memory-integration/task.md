# 20260628 发布经验融合到 AGENTS 与经验文档

## Task Goal

基于 `20260628-release-flow-fupan` 的复盘结果，判断并落实哪些内容应进入：

- `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md`
- `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- `D:\ProjectPackage\Int\IntRuoyi\docs\agent-memory\project-error-prevention.md`
- 其他更合适的经验文档或索引

目标是把长期稳定、跨任务复用的规则沉淀到正确层级，避免把任务级细节直接写进 `AGENTS.md`。

## Scope

- 读取并比较两个仓库的 `AGENTS.md`、经验索引、发布经验文档、项目短记忆与本次复盘文档。
- 更新适合的经验文档与项目短记忆。
- 输出适合写入 `AGENTS.md` 的精简候选规则。

## Non-Scope

- 未经用户明确确认，不直接修改任何 `AGENTS.md`。
- 不修改发布脚本、业务代码或服务器环境。

## 经验门禁

- `docs/experience-index.md`
  - 长期规则优先沉淀到经验文档；只有稳定、跨任务、低歧义规则才考虑提升到 `AGENTS.md`。
- `docs/agent-memory/project-error-prevention.md`
  - 短记忆只保留项目级、可压缩、长期稳定规则，不写任务细节。
- `thread-baseline-agents` 技能
  - 写 `AGENTS.md` 前必须先给出候选基线并获得用户明确确认。

## Milestones

- [x] 对照发布复盘，拆分“AGENTS 候选规则”和“经验文档更新项”。
- [x] 更新维护仓发布经验文档、业务仓经验索引与项目短记忆。
- [x] 形成面向用户确认的 `AGENTS.md` 精简候选，并在获批后完成落地。
- [x] 校验任务收尾范围，确认仅保留核心任务记录文件。

## Expected Verification

- 维护仓与业务仓中，发布经验已按“AGENTS / 经验索引 / 经验文档 / 项目短记忆”分层落位。
- 面向 Codex 的长期硬规则只保留精简版本进入 `AGENTS.md`，详细方法保留在经验文档与清单。
- `task-closeout-cleanup` 预览结果无阻塞、无误删风险。

## Final Verification

- 已完成以下落地核对：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md`
  - `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\agent-memory\project-error-prevention.md`
- 已执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260628-release-memory-integration --mode preview`，结果为 `ready`，仅保留 `task.md` 与 `execution-log.md`，无待删项、无阻塞项、无警告项。

## Current Status

COMPLETED：本次发布复盘经验已按长期规则、经验索引、详细经验文档和项目短记忆完成分层沉淀；面向 Codex 的执行清单已补齐，任务收尾预览通过。
