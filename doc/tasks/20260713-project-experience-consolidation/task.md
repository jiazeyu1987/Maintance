# 20260713 项目经验归档

## Task Goal

按 `project-experience-consolidation` 技能，将本轮发布暴露的可复用经验合并到已有长期经验文档，避免只留在任务日志中。

## Milestones

- [x] 创建任务目录与初始任务记录。
- [x] 读取经验索引和已有长期经验文档，确定归档位置。
- [x] 仅更新已有合适经验文档；不新建长期经验文档。
- [x] 验证关键词路由、UTF-8、diff check 与提交隔离。

## Expected Verification

- 可复用经验已归档到现有经验文档。
- 未创建未经授权的新经验文档。
- 任务记录、执行日志和请求命令日志完整。
- 只提交本任务直接产生的文件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，经验归档为行动前可检查门禁。
- 是否存在临时补丁或绕过：否。

## 经验门禁

### 长期经验归档门禁

- Trigger: 用户指定 `project-experience-consolidation` 或要求沉淀项目经验。
- Preflight check: 先读取 `docs/experience-index.md`，按关键词只打开匹配经验文档；优先更新已有文档。
- Blocker: 没有合适归宿且用户未授权新建长期经验文档；候选经验只是一次性任务状态或可能过期的业务事实。
- Verification: `rg` 能从经验索引定位新关键词；更新内容不包含任务流水、secret 或一次性状态。
- Forbidden action: 不得把任务日志原样复制进长期经验；不得未经授权创建新经验文档。
- Evidence: `project-experience-consolidation` 技能；本任务执行日志。

### 本轮命中归档

- Worktree / 清理：`D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`
- PowerShell / 解析 / 长运行日志：`D:/ProjectPackage/Int/IntRuoyi/docs/powershell-memory.md`
- 发布运行态验收：`D:/ProjectPackage/Int/IntRuoyi/docs/release-backup-restore.md`
- 关键词路由：`D:/ProjectPackage/Int/IntRuoyi/docs/experience-index.md`

## Current Status

completed - 主项目已有经验文档已更新，关键词路由、UTF-8、diff check、secret scan 和 task-closeout preview/apply 均通过；未创建新的长期经验文档。
