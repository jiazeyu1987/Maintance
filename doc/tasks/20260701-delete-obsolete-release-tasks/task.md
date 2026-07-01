# 20260701 删除旧发布任务与旧发布基线任务

## Task Goal

按用户明确指令，直接删除已经被新发布工作流替代的旧发布任务目录与旧发布基线任务目录，避免维护仓继续保留无效的旧规则任务台账。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 删除目标：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-build-publish-test-server-current\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-release-main-branch-baseline\`
- 日志更新：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`

## Non-Scope

- 不改动当前已生效的新发布规则正文
- 不删除真实发布成功闭环任务
- 不修改业务仓源码、数据库或服务器配置

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-release-temp-worktree-baseline\task.md`
- 状态：`COMPLETED`
- 处理说明：上一任务已完成新发布工作流固化，本次按用户要求删除被替代的旧发布任务目录与旧发布基线目录。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 先读索引，只打开命中的经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 当前新发布口径已经统一为“每次发布一律走临时发布 worktree”；本次删除只清理旧任务台账，不回退新基线。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 清理任务台账前先确认删除对象只是历史任务文档，不涉及真实运行中的 worktree、分支或运行态目录。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；通过删除被替代的旧任务台账，减少后续误读旧发布基线的风险。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 删除旧发布任务目录 -> Given `20260701-build-publish-test-server-current` 已被新发布规则替代且用户明确要求删除 When 执行本次清理 Then 该任务目录必须从维护仓删除。

BDD: 删除旧发布基线任务目录 -> Given `20260630-release-main-branch-baseline` 仅用于记录已被替换的旧发布基线且用户明确要求删除 When 执行本次清理 Then 该任务目录必须从维护仓删除。

BDD: 新发布规则保持不变 -> Given 新发布规则已经写入 `AGENTS.md` 与发布前置文档 When 删除旧任务目录 Then 当前有效规则正文不得回退。

## Milestones

1. 建立删除任务台账并记录经验门禁。`COMPLETED`
2. 删除旧发布任务目录。`COMPLETED`
3. 删除旧发布基线任务目录。`COMPLETED`
4. 回填命令日志与任务结论。`COMPLETED`

## Expected Verification

- `doc/tasks/20260701-build-publish-test-server-current/` 不再存在
- `doc/tasks/20260630-release-main-branch-baseline/` 不再存在
- `docs/request-command-log.md` 已记录本次删除动作
- `AGENTS.md` 与当前发布前置文档仍保持新发布规则不变

## Current Status

COMPLETED：两个旧任务目录已经按用户授权删除，命令日志与执行日志已回填，收尾预览通过。当前维护仓只保留已生效的新发布规则正文与新规则固化任务台账。
