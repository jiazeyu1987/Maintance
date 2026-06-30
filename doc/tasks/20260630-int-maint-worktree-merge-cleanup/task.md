# 20260630 维护仓 worktree 合并与清理

## Task Goal

按用户要求，逐个检查并处理 `D:\ProjectPackage\Int\IntRuoyiMaintance` 主 worktree 之外的 3 个 worktree，先确认是否已安全合并到主 worktree `int_main`，再删除可安全清理的 worktree；若存在未提交改动、归属不明或与主 worktree 脏改冲突，则按门禁阻塞并明确报告。

## Scope

- 仓库：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 主 worktree：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 待处理 worktree：
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-4fa706d`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-fd139bc`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`

## Non-Scope

- 不处理 `IntRuoyi` 前后端仓库的 worktree
- 不修改服务器、发布状态或运行环境
- 不清理归属不明的未提交改动

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-release-main-branch-baseline\task.md`
- 状态：`COMPLETED`
- 处理说明：上一维护仓任务已完成，本次可继续执行 worktree 合并与清理。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 涉及 `worktree` 合并或清理属于高风险动作，执行前必须在 `execution-log.md` 记录 `experience-preflight`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 合并后必须在主结果上确认状态；若主 worktree 存在重叠脏改且无法安全判断归属，必须阻塞，不能强行合并或删除。
  - 清理前必须确认只处理本任务 worktree，且不能误删未提交改动或其他任务产物。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；按 worktree 门禁先核对提交关系与脏改归属，只删除已确认可清理的工作区。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 已合入主线的发布 worktree 可以直接清理 -> Given 某待清理 worktree 的提交已经包含在 `int_main` 中且不存在需要保留的未提交改动 When 执行 worktree 清理 Then 该 worktree 应从维护仓 worktree 列表中移除且目录被删除。

BDD: 存在归属不明脏改的 worktree 不得强删 -> Given 某待清理 worktree 含有未提交文件且这些改动未确认已安全落到主 worktree When 尝试执行清理 Then 必须先阻塞并向用户报告风险，不得直接 `--force` 删除。

## Milestones

1. 建立任务台账并记录经验门禁。`COMPLETED`
2. 核对 3 个待处理 worktree 的提交归属与工作区状态。`COMPLETED`
3. 清理可安全删除的 worktree，并记录阻塞项。`COMPLETED`
4. 回填验证结论并完成任务状态。`COMPLETED`

## Expected Verification

- `git -C D:\ProjectPackage\Int\IntRuoyiMaintance worktree list`
- 对每个待处理 worktree 记录：
  - 是否已被 `int_main` 包含
  - 是否存在未提交改动
  - 是否已删除或为何阻塞

## Current Status

COMPLETED：已完成主 worktree 之外 3 个 worktree 的逐项整理、必要内容回收与删除，当前维护仓 `git worktree list` 只剩主 worktree `D:\ProjectPackage\Int\IntRuoyiMaintance`。

- `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-fd139bc`
  - 仅残留 `runtime/`、`frontend/pnpm-workspace.yaml`、`frontend/node_modules` 等临时产物。
  - 已删除目录，并通过 `git worktree prune` 清理挂账记录。
- `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-4fa706d`
  - 提交 `4fa706d` 已被 `int_main` 包含。
  - 未提交代码差异经核对属于该 worktree 上的旧版本本地改动，不是主 worktree 缺失的独有修复；已还原并删除 worktree。
- `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`
  - 任务文档与 `docs/request-command-log.md` 中的增量证据已回收到主 worktree。
  - 其后清理了 `runtime/`、任务目录和残留运行进程（`start.ps1` 与 `java -jar runtime-control-maintenance-2026.06-SNAPSHOT.jar`），并删除 worktree。
