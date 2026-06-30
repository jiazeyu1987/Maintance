# 20260630 维护仓 worktree 合并与清理执行日志

BDD: 已合入主线的发布 worktree 可以直接清理 -> Given 某待清理 worktree 的提交已经包含在 int_main 中且不存在需要保留的未提交改动 When 执行 worktree 清理 Then 该 worktree 应从维护仓 worktree 列表中移除且目录被删除。

BDD: 存在归属不明脏改的 worktree 不得强删 -> Given 某待清理 worktree 含有未提交文件且这些改动未确认已安全落到主 worktree When 尝试执行清理 Then 必须先阻塞并向用户报告风险，不得直接 --force 删除。

GREEN: experience-preflight -> PASS, 已读取 D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md 与 D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md，满足 worktree 合并/清理前置门禁。
GREEN: repository-state-audit -> PASS, 已确认主 worktree `int_main` 当前存在大量未提交改动；3 个待清理 worktree 中，`20260629-4fa706d` 与 `20260630-fd139bc` 均存在未提交差异，`20260629-fd139bc` 仅残留临时产物。
GREEN: remove-worktree-20260629-fd139bc -> PASS, 已删除 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-fd139bc` 目录，并通过 `git worktree prune` 将其从维护仓 worktree 清单移除。
GREEN: diff-audit-20260629-4fa706d -> PASS, 已核对 `ops/deploy/publish-int-ruoyi.ps1` 与 `ops/deploy/int-ruoyi-test/Dockerfile.backend` 差异；确认该 worktree 保留的是较旧/较弱的本地版本，不是主 worktree 缺失的独有修复。
GREEN: doc-recovery-20260630-fd139bc -> PASS, 已将 `docs/request-command-log.md` 与任务文档中的补发版发布证据回收到主 worktree。
GREEN: remove-worktree-20260629-4fa706d -> PASS, 已清理 `frontend/pnpm-workspace.yaml`、`runtime/`、`frontend/node_modules` 等残留产物，还原未提交代码差异，并删除 worktree。
GREEN: remove-worktree-20260630-fd139bc -> PASS, 已停止残留进程 `powershell -File scripts/start.ps1` 与 `java -jar backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，删除目录并完成 `git worktree prune`。
GREEN: final-worktree-list -> PASS, `git -C D:\ProjectPackage\Int\IntRuoyiMaintance worktree list` 当前仅剩 `D:/ProjectPackage/Int/IntRuoyiMaintance fd139bc [int_main]`。
