# 20260714 r260713v 三环境发布经验归档

## Task Goal

将 `20260713-current-head-codeonly-three-env-r260713v` 完整三环境发布闭环中可复用的发布、验收、worktree 清理经验，归档到已有长期经验文档；不新建经验文档，不执行构建、发布、服务器写入、备份、恢复或回滚。

## Milestones

- [x] 创建任务目录并写入 `task.md` 与 `execution-log.md`。
- [x] 读取经验索引和命中长期经验文档，摘取本次适用门禁。
- [x] 将 r260713v 可复用经验合并到已有长期经验文档。
- [x] 更新请求命令日志并执行格式、关键词、脱敏和 diff 校验。
- [x] 标记任务完成并只提交本次任务直接产生的记录和经验变更。

## Expected Verification

- 已更新已有经验文档，无新增长期经验文件。
- `docs/experience-index.md` 可按关键词定位新增经验。
- `docs/request-command-log.md` 记录本次请求、命令意图和结果。
- `git diff --check`、关键词检索和凭据扫描通过。
- 最终提交不包含无关工作区改动。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。只把可复用前置门禁写入长期经验，任务状态和一次性流水留在任务目录。
- 是否存在临时补丁或绕过：否。

## BDD Scenarios

- BDD: existing experience destination -> Given r260713v 发布发现可复用发布经验, When 执行经验归档, Then 必须优先更新已有经验文档，不新建重复文档。
- BDD: task-specific facts stay local -> Given 发布任务有 releaseTag、operationId 和一次性状态, When 写长期经验, Then 只保留可复用门禁和证据引用，不记录一次性流水。
- BDD: commit isolation -> Given 主工作区存在其他任务未提交改动, When 本任务完成提交, Then 只暂存本任务直接产生的任务记录、请求日志条目和必要经验 hunk。

## 经验门禁

### 经验写入归宿门禁

- Trigger: `project-experience-consolidation`、发布失败/发布收尾经验沉淀、长期经验文档更新。
- Preflight check: 先按 `docs/experience-index.md` 路由搜索已有经验文档；worktree 清理经验优先使用已有 release/worktree 清理门禁，PowerShell/SSH 远端验收经验优先使用 `docs/powershell-preflight-lessons.md`；无合适归宿时必须先询问用户是否新建。
- Blocker: 经验只是一次性状态、需要新建长期文档但未获授权、或目标文档与经验类型不匹配。
- Verification: 新增条目包含 Trigger、Preflight check、Blocker、Verification、Forbidden action、Evidence；索引关键词能定位；diff 和 secret scan 通过。
- Forbidden action: 不得把 task 流水、releaseTag 运行结论或临时数据混入长期经验；不得提交含凭据的原始日志。
- Evidence: `project-experience-consolidation` skill；`docs/experience-index.md` 写入规范。

### 提交隔离门禁

- Trigger: 主工作区已有其他任务未提交改动，且本任务需要更新共享经验文档。
- Preflight check: 提交前必须核对 `git status --short`、`git diff -- <path>` 和 staged diff；同文件含其他任务 hunk 时不得整文件暂存。
- Blocker: 无法证明 staged diff 只包含本任务新增 hunk，或共享文件已有未归属改动会被误提交。
- Verification: `git diff --cached --name-only` 和 `git diff --cached --check` 通过；必要时使用路径级/patch 级暂存隔离。
- Forbidden action: 不得顺手提交 `AGENTS.md`、历史任务日志或其它 release 任务遗留改动。
- Evidence: 当前 `git status --short` 已显示多个无关未提交改动。

## Current Status

completed - r260713v 可复用经验已写入维护仓已有经验入口；task-closeout preview/apply blocked=<none> warnings=<none>；关键词、格式和凭据风险校验通过，准备提交本任务 hunk。
