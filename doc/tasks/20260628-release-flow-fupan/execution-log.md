# 20260628 发布链路复盘执行日志

GREEN: evidence-source-check-20260628 -> PASS，已确认本轮复盘具备稳定证据来源：`20260625-head-full-release/task.md`、`20260625-head-full-release/execution-log.md`、`docs/request-command-log.md`、`docs/experience-index.md`、`docs/agent-memory/project-error-prevention.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`。

GREEN: task-bootstrap-20260628-release-flow-fupan -> PASS，已创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260628-release-flow-fupan\`，并写入 `task.md` 与本执行日志。当前目标限定为文档复盘与规范沉淀，不执行新的发布、重启或服务器写入动作。

GREEN: release-flow-fupan-doc-20260628 -> PASS，已基于 `20260625-head-full-release` 的任务与日志证据，完成 `release-flow-fupan.md`，覆盖版本演进、构建发布固定顺序、三环境验证要点、SQL/migration 规范、发布脚本规范、后端前端发布契约规范与环境运维规范。

GREEN: project-memory-candidate-20260628 -> PASS，已提炼出适合长期复用的项目级经验候选：发布失败优先查契约层而不是先猜环境、SQL/脚本必须按“可发布性”编写、正式服问题必须区分脚本/SQL/环境三类证据。下一步仅将其中稳定且可压缩的规则写入项目短记忆，不把任务专属细节提升为长期规则。
