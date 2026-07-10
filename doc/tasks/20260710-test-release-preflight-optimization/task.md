# 20260710 测试服发布前置经验优化

## 任务目标

将当前分散在发布复盘、PowerShell 经验和 worktree 经验中的测试服发布要点，整理成发布前可直接执行的门禁入口，帮助后续构建发布任务更快、更稳定地完成检查。

## 里程碑

1. M1：建立任务文档，确认上一发布任务已完成，读取经验索引与命中文档。COMPLETED
2. M2：新增测试服发布专用前置门禁文档。COMPLETED
3. M3：更新经验索引和发布执行清单，使后续任务优先命中新门禁。COMPLETED
4. M4：验证 UTF-8、关键词可发现性、链接和任务记录。COMPLETED
5. M5：运行 task-closeout preview，提交本任务文档与经验优化。COMPLETED

## 预期验证

- `docs/test-release-preflight.md` 存在，包含阶段门禁、fail fast 条件、推荐检查命令、可自动化项和禁止跳过项。
- `docs/experience-index.md` 能通过“测试服发布 / current HEAD / publish-test / frozen release baseline”等关键词命中新文档。
- `docs/release-agent-checklist.md` 和 `docs/release-build-preflight-lessons.md` 指向新门禁入口，减少后续阅读长文时漏项。
- 所有新增/修改中文文档均为 UTF-8 可读。
- 仅提交本任务直接产生的文档改动。

## 经验门禁

- 任务开始必须读取 `docs/experience-index.md`，并只打开命中发布、构建、PowerShell、worktree 的经验文档。
- 优化经验时必须把复盘内容转成 before-action gate，包含 Trigger、Preflight check、Blocker、Verification、Forbidden action。
- 测试服发布门禁必须覆盖：干净临时 release worktree、冻结提交、Manifest v1、legacy 清单分 schema 校验、required SQL、publish-test 预览、真实运行态、运行控制台版本与变更说明、worktree 清理。
- PowerShell 命令示例不得使用 `&&`；中文读写必须显式 UTF-8。
- 不得把 fallback、手工绕过、静默跳过或 mock success 写成可接受路径。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；通过新增可执行前置门禁入口降低后续发布漏项和重复踩坑概率。
- 是否存在临时补丁或绕过：否。

## 当前状态

- 状态：已完成。
- 已完成：上一任务 `20260709-current-head-test-only-release` 已确认 `Current Status=completed`；已读取经验索引、发布构建经验、PowerShell 经验、worktree 记忆和 preflight 技能参考；已新增 `docs/test-release-preflight.md` 并更新索引与发布执行清单。
- 验证结果：UTF-8 校验通过；关键词可通过 `rg` 命中；`git diff --check` 通过；task-closeout preview 无删除项、无阻塞、无警告。

## Current Status

completed
