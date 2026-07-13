# 20260713 项目经验归档执行日志

## Initial Request

- REQUEST: 用户指定 `project-experience-consolidation` 技能。
- SCOPE: 归档本轮发布中已暴露且可复用的工程经验；优先合并到已有经验文档，不创建新长期经验文档。

## Milestone 1 - Task Bootstrap

- GREEN: task-directory -> PASS，创建 `doc/tasks/20260713-project-experience-consolidation/`。
- GREEN: task-doc-bootstrap -> PASS，写入任务目标、里程碑、预期验证和设计约束。

## Milestone 2 - Experience Routing

- COMMAND: 读取 `project-experience-consolidation` 技能、维护仓 `docs/experience-index.md`、主项目 `docs/experience-index.md`、`docs/worktree-memory.md`、`docs/release-backup-restore.md`、`docs/powershell-memory.md`。
- GREEN: experience-routing -> PASS，本轮没有需要新建的长期经验文档；发布专项细节已在维护仓 preflight，跨项目通用经验归入主项目 worktree / PowerShell / release 文档。
- GREEN: experience-preflight -> PASS，后续仅更新已有经验文档和本任务记录，不执行服务器写入、构建、发布或环境修改。

## Milestone 3 - Long-term Experience Updates

- GREEN: update-worktree-memory -> PASS，更新 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`，补充发布 worktree 清理必须同时证明 Git 注册和物理根目录的门禁。
- GREEN: update-powershell-memory -> PASS，更新 `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`，补充 release-info CRLF、Playwright console 结构化判定、长运行日志目录锁定门禁。
- GREEN: update-release-memory -> PASS，更新 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，补充发布运行态验收解析门禁。
- GREEN: update-experience-index -> PASS，更新 `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md` 关键词路由。

## Milestone 4 - Verification

- GREEN: keyword-route -> PASS，`rg` 可定位 `releaseInfoTagOk false`、`task-closeout runtime log lock`、`物理根目录残留`、`发布运行态验收解析`。
- GREEN: int-ruoyi-diff-check -> PASS，主项目 `docs/experience-index.md`、`docs/worktree-memory.md`、`docs/powershell-memory.md`、`docs/release-backup-restore.md` 无 diff check 错误。
- GREEN: maint-diff-check -> PASS，维护仓本任务记录和 `docs/request-command-log.md` 无 diff check 错误。
- GREEN: utf8-control-scan -> PASS，两个仓库本次修改文件均无非法控制字符。
- GREEN: secret-scan -> PASS，两个仓库本次修改文件未发现明文密码、token、private key 或 `mysql -p<redacted>` 以外的明文形态。
- ISSUE: request-command-log-historical-passwords -> 现象：更新 `docs/request-command-log.md` 时，文件中已有历史命令包含测试账号明文密码；阶段：提交前脱敏扫描；影响：若只追加本次记录会把 secret-bearing 日志继续带入提交；原因判断：早期请求日志记录了真实登录命令参数；处理动作：将命令中的密码参数改为 `<redacted>`，同时保留命令意图、租户、账号、URL、路径和验证结果；结果：secret scan 通过；是否可前置检查：是；是否可自动化：是；下次如何避免：请求命令日志写入前先对待提交 blob 做 secret scan，命令参数只记录脱敏值。
- STATUS: ready_for_closeout。

## Milestone 5 - Closeout

- GREEN: task-closeout-preview -> PASS，keep=`task.md`/`execution-log.md`/`verification-report.md`，delete=<none>，blocked=<none>，warnings=<none>。
- GREEN: task-closeout-apply -> PASS，delete=<none>，blocked=<none>，warnings=<none>。
- STATUS: completed。
