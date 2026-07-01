# 20260701 删除旧发布任务与旧发布基线任务执行日志

BDD: 删除旧发布任务目录 -> Given `20260701-build-publish-test-server-current` 已被新发布规则替代且用户明确要求删除 When 执行本次清理 Then 该任务目录必须从维护仓删除。

BDD: 删除旧发布基线任务目录 -> Given `20260630-release-main-branch-baseline` 仅用于记录已被替换的旧发布基线且用户明确要求删除 When 执行本次清理 Then 该任务目录必须从维护仓删除。

BDD: 新发布规则保持不变 -> Given 新发布规则已经写入 `AGENTS.md` 与发布前置文档 When 删除旧任务目录 Then 当前有效规则正文不得回退。

INFO: task-created -> 已创建删除旧发布任务与旧发布基线任务台账。
GREEN: experience-preflight -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
GREEN: obsolete-release-task-deleted -> PASS，`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-build-publish-test-server-current\` 已按用户要求删除。
GREEN: obsolete-release-baseline-deleted -> PASS，`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-release-main-branch-baseline\` 已按用户要求删除。
GREEN: command-log-updated -> PASS，`docs/request-command-log.md` 已记录本次删除动作。
GREEN: task-closeout-preview -> PASS，`python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260701-delete-obsolete-release-tasks --mode preview` 返回 `status: ready`，无额外清理阻塞项。
