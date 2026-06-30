# 20260630 发布默认走主分支规则固化执行日志

BDD: 发布命令默认只走主分支 -> Given 用户后续再次下达“构建并发布到测试服务器” When Codex 读取事前经验与 `AGENTS.md` Then 必须先按各仓库主分支作为默认发布输入理解，不再默认切到发布 `worktree`。

BDD: 主分支脏改时先让用户选方案 -> Given 任一参与发布的主分支工作区存在未提交改动 When Codex 进入发布前检查 Then 必须先明确提示风险并让用户选择处理方案，而不是默认隔离到 `worktree` 或继续发布。

INFO: task-created -> 已创建长期发布规则固化任务文档与执行日志。
GREEN: experience-preflight -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`。
GREEN: baseline-written-to-agents -> PASS，`AGENTS.md` 已新增长期线程基线：后续默认发布只发布各仓库主分支当前版本，不默认创建发布 `worktree`；若主分支工作区有脏改，必须先提示用户选择处理方案。
GREEN: preflight-docs-updated -> PASS，`docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md` 已统一为“默认主分支发布；仅在用户明确要求发布已提交 git 版本或隔离输入时才使用 clean worktree”。
GREEN: command-log-updated -> PASS，`docs/request-command-log.md` 已记录本次长期规则固化。
