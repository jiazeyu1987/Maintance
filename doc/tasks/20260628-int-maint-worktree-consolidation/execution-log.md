# IntRuoyiMaintance worktree 融合与清理执行日志

- BDD: 待融合 worktree 只有在主工作区可安全接收时才允许合并 -> Given 主工作区存在未提交改动 / When 待融合分支与这些改动重叠 / Then 任务必须先阻塞并说明重叠文件，不能强行 merge。
- BDD: 发布快照 worktree 只有在确认无残留改动后才允许删除 -> Given detached release worktree 仅用于历史发布快照 / When 其工作区仍存在运行时目录、未跟踪文件或本地修改 / Then 任务必须先记录残留，再决定是否清理。
- BDD: 维护仓最终只保留一个主 worktree 需要明确主分支名称 -> Given 用户要求只保留主 worktree / When 当前仓库主分支不是 master 而是 int_main / Then 任务必须先明确“保留 int_main”还是“改名为 master”。

- GREEN: experience-preflight -> PASS，已读取 `experience-index`、`worktree-memory`、`project-error-prevention`；在未消除阻塞前不执行 merge、remove 或强制清理。
- GREEN: worktree-inventory -> PASS，当前维护仓共有 6 个 worktree 路径，其中主 worktree 为 `D:\ProjectPackage\Int\IntRuoyiMaintance`，附加 worktree 包含 1 个任务分支 worktree 和 4 个 detached release worktree。
- GREEN: previous-task-check -> PASS，上一任务 `20260628-release-change-items-garbled-fix` 文档状态已为 `COMPLETED`，本轮阻塞不来自任务文档状态。
- GREEN: main-branch-check -> PASS，确认维护仓主 worktree 当前分支为 `int_main`，并不存在 `master` 分支。
- GREEN: branch-diff-analysis -> PASS，待融合任务 worktree 相对 `int_main` 领先 3 个提交：`94d0837`、`9c2c25c`、`2a56869`；差异文件包括 `ops/deploy/publish-int-ruoyi.ps1`、`ops/deploy/int-ruoyi-test/docker-compose.yml`、`scripts/tests/test_publish_dcc_codex_runtime_contract.py`、`docs/request-command-log.md` 及对应任务文档。
- BLOCKER: merge-target-name-ambiguous -> 用户要求“最后只保留一个主worktree master”，但当前维护仓无 `master` 分支。影响：在未明确“保留 int_main”还是“改名为 master”前，不能完成最终目标定义。
- BLOCKER: main-worktree-overlap -> 主工作区存在未提交改动，且与待融合分支 `codex/20260623-test-server-dcc-content-recognition-enable` 触达同一文件：`ops/deploy/publish-int-ruoyi.ps1`、`ops/deploy/int-ruoyi-test/docker-compose.yml`、`docs/request-command-log.md`。影响：按 `worktree-memory` 门禁，不能直接 merge 或通过临时 merge worktree 绕过。
- BLOCKER: release-worktree-residue -> detached release worktree 中仍发现本地残留：`IntRuoyiMaintance-20260624-0736fb7` 含未跟踪 `runtime/`，`IntRuoyiMaintance-20260624-head` 含未跟踪 `doc/tasks/20260620-prod-release-current-latest/prod-target-config.json` 与 `runtime/`，`IntRuoyiMaintance-20260625-3eb9047` 含未跟踪 `runtime/`，`IntRuoyiMaintance-20260627-3eb9047` 含修改中的 `ops/deploy/publish-int-ruoyi.ps1` 与未跟踪 `runtime/`。影响：删除前必须先确认这些残留是否可丢弃。
- GREEN: merge-target-corrected -> PASS，用户已明确更正目标为“只保留 `int_main` 主 worktree”，不再要求改名为 `master`。
- GREEN: branch-content-absorbed-in-main-worktree -> PASS，复核主工作区当前文件后确认，待删除任务 worktree 的代码与测试核心内容已在主工作区现有文件中体现；仅缺 `doc/tasks/20260623-test-server-dcc-content-recognition-enable/` 任务记录，已补回主工作区。
- GREEN: release-worktree-residue-classified -> PASS，4 个 detached release worktree 的残留均为 `runtime/`、发布过程日志、临时状态或已在主工作区存在的任务证据；未发现需要单独保留的唯一生产代码。
- GREEN: `git worktree remove --force D:/ProjectPackage/Int/IntRuoyiMaintanceWorktrees/int-maint-dcc-content-recognition-enable` -> PASS
- GREEN: `git worktree remove --force D:/ProjectPackage/Int/release-worktrees/IntRuoyiMaintance-20260624-0736fb7` -> PASS
- GREEN: `git worktree remove --force D:/ProjectPackage/Int/release-worktrees/IntRuoyiMaintance-20260624-head` -> PASS
- GREEN: `git worktree remove --force D:/ProjectPackage/Int/release-worktrees/IntRuoyiMaintance-20260625-3eb9047` -> PASS
- GREEN: `git worktree remove --force D:/ProjectPackage/Int/release-worktrees/IntRuoyiMaintance-20260627-3eb9047` -> PASS
- GREEN: post-cleanup-worktree-list -> PASS，`git worktree list` 复核仅剩 `D:\ProjectPackage\Int\IntRuoyiMaintance [int_main]`。
