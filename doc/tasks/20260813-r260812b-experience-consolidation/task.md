# r260812b 发布经验沉淀

## Task Goal

复核 `2026-08-11-test-only-release-head` 的问题记录，将可复用经验合并到已有项目经验文档和索引；不新建长期经验文档，不改生产代码、服务器、数据库或运行环境。

## Milestones

- [completed] M1：读取来源任务问题记录和命中的既有经验文档，建立去重映射。
- [completed] M2：按 Trigger / Preflight check / Blocker / Verification / Forbidden action / Evidence 结构补齐已有经验归宿。
- [in_progress] M3：更新经验索引与请求日志，验证关键词路由、UTF-8、diff 范围和格式。
- [pending] M4：完成 task-closeout preview/apply 并提交本任务记录与经验变更。

## Expected Verification

- 来源任务中的可前置问题均有已有归宿或明确保留为一次性任务记录。
- 不创建新的长期经验文档。
- `rg` 可从 `docs/experience-index.md` 的关键词定位目标经验章节。
- 新增门禁包含六个固定字段，涉及流程的门禁包含阶段必查项、推荐命令、Fail Fast 和必须记录。
- `git diff --check` 通过，暂存/提交只包含本任务文件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；把重复失败模式转为可执行前置门禁，并按主题合并到既有文档。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 先查 `docs/experience-index.md` 并更新已有归宿；无合适归宿时必须先取得用户授权才能新建长期经验文档。
- 一次性 releaseTag、operation、数据行 ID 和执行流水只作为 Evidence，不得写成长期业务事实。
- 发布/构建问题优先归入 `docs/release-build-preflight-lessons.md` 或 `docs/test-release-preflight.md`；worktree/清理问题归入 `E:\IntRuoyi\docs\worktree-memory.md`。
- 每条门禁必须包含 Trigger、Preflight check、Blocker、Verification、Forbidden action、Evidence；涉及长流程时补充阶段执行 checklist。
- 中文文档使用 UTF-8；只用 `apply_patch` 写入，完成后运行关键词路由与 `git diff --check`。
- 工作区现有无关改动不得暂存、提交、清理或覆盖。

## Current Status

in_progress
