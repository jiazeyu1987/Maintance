# 20260701 发布统一走临时 worktree 规则固化执行日志

BDD: 每次发布统一走临时 worktree -> Given 用户后续再次下达“构建并发布到测试服务器”或其他发布命令 When Codex 读取事前经验与 `AGENTS.md` Then 必须先新建本次专用临时发布 `worktree`，并在该 `worktree` 中完成构建、验证和发布。

BDD: 发布输入固定为 Git 已提交内容 -> Given 主工作区存在脏改或无脏改 When Codex 准备发布输入 Then 必须只使用目标提交对应的 Git 已提交内容，未提交改动、未跟踪文件和脏工作区内容一律不得进入发布包。

BDD: 发布结束后只保留主工作区 -> Given 本次发布所需临时发布 `worktree` 已完成构建、验证与发布 When 本次发布收尾 Then 未产生新提交的临时发布 `worktree` 必须直接删除；产生新提交的临时发布 `worktree` 必须先合回对应仓库 `int_main` 并验证通过后删除；最终现场只剩各仓库 `int_main` 主工作区。

INFO: task-created -> 已创建统一发布临时 worktree 规则固化任务文档与执行日志。
GREEN: experience-preflight -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`。
GREEN: previous-task-blocked -> PASS，已将 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-build-publish-test-server-current\task.md` 显式标记为 `BLOCKED`，避免旧发布基线与新规则冲突。
GREEN: baseline-written-to-agents -> PASS，`AGENTS.md` 已统一改为“每次构建发布一律在临时发布 worktree 中执行；发布完成后只保留各仓库 int_main 主工作区”的线程基线。
GREEN: preflight-docs-updated -> PASS，`docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md` 已统一改为“每次发布一律先创建本次专用临时发布 worktree，并以目标提交对应的 Git 已提交内容作为唯一发布输入”。
GREEN: command-log-updated -> PASS，`docs/request-command-log.md` 已记录本次统一发布临时 worktree 规则固化。
GREEN: task-closeout-preview -> PASS，`python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260701-release-temp-worktree-baseline --mode preview` 返回 `status: ready`，无额外清理阻塞项。
