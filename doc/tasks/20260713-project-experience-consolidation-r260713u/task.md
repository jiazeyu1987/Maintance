# 20260713 r260713u 项目经验归档

## Task Goal

按 `project-experience-consolidation` 技能，将 `20260713-current-head-test-only-release-rerun` 复跑中暴露的可复用发布、worktree、PowerShell 和运行态验收经验合并到已有长期经验文档；不新建长期经验文档。

## Milestones

- [x] 创建任务记录并读取经验索引、已有归档任务和匹配长期经验文档。
- [ ] 更新已有长期经验文档，覆盖 P001-P008 中可复用门禁。
- [ ] 更新关键词路由，确保后续任务可命中新增经验。
- [ ] 验证 UTF-8、关键词、diff、secret scan 和提交隔离。

## Expected Verification

- 可复用经验归档到现有长期文档：`docs/worktree-memory.md`、`docs/release-backup-restore.md`、`docs/powershell-memory.md`、`docs/experience-index.md`。
- 未创建新的长期经验文档。
- 新关键词可通过 `rg` 从经验索引定位。
- 不提交 secret-bearing 日志或一次性任务流水。
- 只暂存和提交本任务直接产生的文件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，沉淀为行动前可检查门禁。
- 是否存在临时补丁或绕过：否。

## 经验门禁

### 长期经验归档门禁

- Trigger: 用户指定 `project-experience-consolidation` 或要求沉淀项目经验。
- Preflight check: 先搜索已有 memory / release / PowerShell / worktree 文档；优先更新已有文档，经验必须写成可执行门禁。
- Blocker: 没有合适归宿且用户未授权新建长期文档；候选内容只是一次性任务状态、临时数据或可能过期的业务事实。
- Verification: `rg` 能从经验索引定位新关键词；`git diff --check` 通过；secret scan 无真实凭据；任务记录完整。
- Forbidden action: 不得把任务流水原样复制进长期经验；不得未经授权创建新经验文档；不得记录明文凭据。
- Evidence: `project-experience-consolidation` 技能与本任务执行日志。

## Current Status

completed - main project long-term experience docs and keyword routes were updated; keyword check, diff check, secret scan and task-closeout apply all passed; no new long-term document was created.

## Updated Long-Term Documents

- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`: release worktree local config/state outside worktree, generated runtime output dirty gate, and physical residual cleanup evidence.
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`: test-only package lookup, historical migration separation, page-visible version notes vs release-info source commit verification, and operationId polling.
- `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`: Python f-string literal braces in remote verification carriers.
- `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`: keyword routes for the new gates.

## Commit Evidence

- Main project experience docs commit: `44922ec` (`??: ????????`).
