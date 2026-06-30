# 20260629 发布前经验前移整理

## Task Goal

将 `docs/agent-memory/project-error-prevention.md` 中属于“构建发布前就该看到”的规则迁移到发布前置文档与索引中，使 Codex 在进入 `build-release` / `publish-test` 前即可命中，而不是等出错后再查看事后 memory。

## Scope

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`

## Non-Scope

- 不改动正式发布规则边界
- 不新增服务器操作
- 不修改业务代码或发布脚本

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 先确认当前发布经验入口，避免新增文档后仍无法在任务开始阶段命中。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布前经验应优先进入预检文档，而不是只保留在事后记忆文件。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 面向 Codex 的前置执行规则，应保持在任务开始即可读取的位置。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是；把规则前移到发布前文档入口
- `是否存在临时补丁或绕过`：否

## Milestones

1. 识别需要前移的发布规则。`COMPLETED`
2. 更新发布前置文档与索引。`COMPLETED`
3. 清理事后 memory 中不应保留的前置规则。`COMPLETED`
4. 回写结果。`COMPLETED`

## Expected Verification

- `experience-index.md` 能在任务开始阶段命中发布前置文档
- `release-build-preflight-lessons.md` 或 `release-agent-checklist.md` 包含从 memory 前移的规则
- `project-error-prevention.md` 不再承载这些“发布前必看”的规则

## Current Status

COMPLETED：已将“发布前必看”的规则前移到 `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md` 与 `docs/experience-index.md`，并将 `docs/agent-memory/project-error-prevention.md` 收缩为事后短记忆占位说明。后续 Codex 在任务开始阶段即可直接命中这些发布前规则。
