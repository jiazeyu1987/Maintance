# 20260716 r260716d 三环境发布经验归档

## Task Goal

将 `20260716-current-head-codeonly-three-env` 完整三环境 code-only 发布闭环中可复用的发布、构建、前置门禁和工作区经验，归档或核验到已有长期经验文档；不新建经验文档，不执行构建、发布、服务器写入、备份、恢复或回滚。

## Milestones

- [x] 创建任务记录并读取项目经验归档技能。
- [x] 读取本轮发布任务证据和现有长期经验入口。
- [x] 判断可复用经验是否已有合适归宿，避免重复或一次性流水进入长期文档。
- [x] 必要时更新已有经验文档和经验索引。
- [x] 更新请求命令日志、执行日志并完成提交隔离验证。

## Expected Verification

- 不新增长期经验文档，除非用户明确授权。
- 可复用经验只进入已有合适文档，不写入一次性 releaseTag 状态或流水。
- `docs/experience-index.md` 能按关键词路由到对应经验入口。
- `git diff --check` 通过，UTF-8/凭据扫描通过。
- 只提交本任务直接产生的任务记录、请求日志和必要经验文档 hunk。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；仅将可复用门禁合并进已有长期经验入口，避免任务流水污染长期记忆。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- 经验归档优先更新已有经验文档；没有合适归宿时必须先问用户，不得擅自新建。
- 长期经验只记录可复用触发条件、前置检查、阻塞条件、验证方式和禁止做法；一次性 releaseTag、operation 流水和当前完成状态留在任务文档。
- 发布/构建类经验优先归入 `docs/release-build-preflight-lessons.md` 和 `docs/experience-index.md`；worktree 清理类经验优先归入 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
- 写中文 Markdown 使用显式 UTF-8；提交前必须执行 `git diff --check` 与凭据扫描。

## Consolidation Result

- 本次发布新增的两条可复用经验已有合适归宿：`docs/release-build-preflight-lessons.md` 与 `docs/experience-index.md`。
- `release preflight 菜单 SQL 解析边界门禁` 已覆盖 `system_menu.id must be an integer literal`、`INSERT INTO system_menu ... SELECT ... ON DUPLICATE KEY UPDATE VALUES(...)` 误解析和重复菜单 ID 误报。
- `release build 前端 ESLint slot 未使用变量门禁` 已覆盖 `pnpm build:test` / `vite-plugin-eslint` 捕获 Vue slot scope 未使用变量的问题。
- 无需新建长期经验文档；一次性 releaseTag、operationId 和完成状态保留在原发布任务记录中。

## Current Status

completed
