# 执行日志：复盘页面发布全链路 v6 经验

- BDD: 证据驱动复盘 -> Given 发布全链路任务已有 task/execution-log/request-log 证据 / When 执行复盘 / Then 只把由证据支持的项目级经验写入短记忆。
- BDD: 拒绝一次性细节 -> Given 候选证据包含具体按钮、operation ID、release tag 或单次报错 / When 选择长期规则 / Then 这些细节只留在任务文档，不进入项目短记忆。
- GREEN: fupan-skill-read -> PASS，已读取 `C:\Users\BJB110\.codex\skills\fupan\SKILL.md` 与 `references\project-memory-template.md`。
- GREEN: previous-task-check -> PASS，`doc/tasks/20260620-frontend-release-full-flow/task.md` 已标记 `COMPLETED`，可作为本次复盘证据。
- GREEN: experience-preflight -> PASS，本任务不执行服务器写入、发布、恢复、真实 E2E 或大文件上传；仅进行本地文档与项目短记忆更新，并已读取 `docs/experience-index.md`、命中经验文档和既有短记忆。
- GREEN: collect-error-evidence -> PASS，运行 `$fupan` 候选证据采集脚本，生成 `doc/tasks/20260621-fupan-frontend-release-full-flow-v6/candidate-error-evidence.md`，来源包括上一任务 `task.md`、`execution-log.md`、`docs/request-command-log.md` 与 `AGENTS.md`。
- BLOCKER: memory-char-count-heredoc -> PowerShell 不支持 bash 风格 `python -X utf8 - <<'PY'` heredoc，命令解析失败且未写入文件；后续改用 `python -X utf8 -c`。
- GREEN: memory-char-count-python-c -> PASS，使用 `python -X utf8 -c` 读取既有短记忆，更新前长度为 `620` 字符。
- GREEN: accepted-memory-lessons -> PASS，接受两条项目级经验：部署输入变更后必须新 `releaseTag` 重建并整链复测；备份服路径固定 `/mnt/intruoyi-data` 且发布前后需核远端 `.env`、镜像与受保护对象边界。
- GREEN: rejected-memory-lessons -> PASS，拒绝写入具体页面控件/弹窗操作、具体 operation ID、具体 release tag、单次 SQL 文件名和临时 Playwright ref；这些细节只保留在任务证据文件中。
- GREEN: update-project-memory -> PASS，运行 `update_project_memory.py` 更新 `docs/agent-memory/project-error-prevention.md`，更新后短记忆长度为 `750` 字符，低于默认 `800` 字符上限。
- GREEN: git-diff-check -> PASS，`git diff --check` 无空白错误；仅提示 Git 可能在下次接触 `docs/agent-memory/project-error-prevention.md` 与 `docs/request-command-log.md` 时执行 LF/CRLF 转换。
- GREEN: task-closeout-cleanup-preview -> PASS，`task_closeout.py --task-id 20260621-fupan-frontend-release-full-flow-v6 --mode preview` 输出 `status: ready`，保留 `task.md`、`execution-log.md`、`candidate-error-evidence.md`，删除项、阻塞项、警告项均为空。
