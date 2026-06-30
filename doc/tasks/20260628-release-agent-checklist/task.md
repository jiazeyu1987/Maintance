# 20260628 Codex 发布执行检查清单

## Task Goal

把本次发布复盘进一步压缩为一份面向 Codex 执行的检查清单，供后续所有 IntRuoyi 构建发布任务直接引用。文档必须尽量使用“触发条件 / 必做动作 / 放行条件 / 阻塞条件”的机器友好格式。

## Scope

- 基于以下已有证据整理：
  - `doc/tasks/20260625-head-full-release/`
  - `doc/tasks/20260628-release-flow-fupan/`
  - `docs/release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`
- 输出一份面向 Codex 使用的执行清单。
- 把新清单接入经验索引或经验文档路由。

## Non-Scope

- 不重新发布。
- 不修改服务器环境。
- 不改动业务代码或发布脚本。

## 经验门禁

- 任务开始先读经验索引，只打开命中文档。
- 长期细则优先沉淀到经验文档；`AGENTS.md` 只保留高度压缩硬规则。
- 本任务仅做文档整理，不执行高风险动作。

## Current Status

COMPLETED：已输出面向 Codex 的发布执行检查清单，并接入维护仓发布经验文档与 IntRuoyi 经验索引。后续 Codex 执行构建发布任务时，可直接命中并按本文顺序执行。
