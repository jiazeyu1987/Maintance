# 任务：IntRuoyiMaintance worktree 融合与清理

## 任务目标

- 盘点 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前全部 worktree。
- 判断哪些 worktree 需要先融合到主维护分支，哪些仅为可清理的发布快照。
- 在满足门禁的前提下，将维护仓收口为只保留一个主 worktree。

## 当前状态

COMPLETED

## 上一任务检查

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260628-release-change-items-garbled-fix\task.md`
- 状态：`COMPLETED`
- 处理：上一任务文档已标记完成；本次阻塞来自当前主工作区的未提交改动与 worktree 残留，不是上一任务文档未收尾。

## 经验门禁

- 已读取：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务适用强制门禁：
  - worktree 融合、清理属于高风险动作；执行前必须先完成 `experience-preflight` 记录。
  - `IntRuoyiMaintance` 当前主 worktree 绑定分支为 `int_main`，不能把不存在的 `master` 当作默认融合目标。
  - 主工作区存在与待融合分支重叠的未提交改动时，必须先拆分归属或记录阻塞；不得通过临时 merge worktree 绕过。
  - 删除 worktree 前必须确认其无未提交改动、无待保留运行时或任务证据。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。先识别主工作区脏改、旧任务状态与 worktree 差异，再决定融合或清理路径。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 待融合 worktree 只有在主工作区可安全接收时才允许合并 -> Given 主工作区存在未提交改动 / When 待融合分支与这些改动重叠 / Then 任务必须先阻塞并说明重叠文件，不能强行 merge。`
- `BDD: 发布快照 worktree 只有在确认无残留改动后才允许删除 -> Given detached release worktree 仅用于历史发布快照 / When 其工作区仍存在运行时目录、未跟踪文件或本地修改 / Then 任务必须先记录残留，再决定是否清理。`
- `BDD: 维护仓最终只保留一个主 worktree 需要明确主分支名称 -> Given 用户要求只保留主 worktree / When 当前仓库主分支不是 master 而是 int_main / Then 任务必须先明确“保留 int_main”还是“改名为 master”。`

## 里程碑

1. 建立任务台账并完成经验门禁检查。`COMPLETED`
2. 核对上一任务状态与主工作区脏改归属。`COMPLETED`
3. 盘点所有 worktree 的提交差异和本地残留。`COMPLETED`
4. 在无阻塞前提下执行融合和清理。`COMPLETED`
5. 验证最终只保留一个主 worktree，并完成收尾。`COMPLETED`

## 预期验证

- `git worktree list`
- `git status --short`
- `git diff --name-status int_main...codex/20260623-test-server-dcc-content-recognition-enable`
- 如获授权继续变更主分支名，再验证目标分支列表与 worktree 绑定状态

## Final Verification

- 已根据用户更正，把目标统一为“仅保留 `int_main` 主 worktree”。
- 已核对待删除 worktree 的唯一代码变更已存在于主工作区当前文件中；缺失的任务记录已补回：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable\task.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable\execution-log.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable\ci-cd-evidence.md`
- 已删除以下附加 worktree：
  - `D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-0736fb7`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-36f4fb1`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-head`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260625-3eb9047`
  - `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047`
- `git worktree list` 复核后仅剩 `D:\ProjectPackage\Int\IntRuoyiMaintance [int_main]`
- `D:\ProjectPackage\Int\release-worktrees` 与 `D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees` 下已无 `IntRuoyiMaintance` 残留目录
- 已执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260628-int-maint-worktree-consolidation --mode preview`

## 当前阻塞

- 无。
