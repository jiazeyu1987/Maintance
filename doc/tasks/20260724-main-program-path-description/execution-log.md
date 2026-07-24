# Execution Log

- 用户需求：将主程序描述由原来的 D 盘 IntRuoyi 目录改为 `E:\IntRuoyi\`；已确认范围为文档描述，不改运行配置。
- BDD: main program path description -> Given 后续任务读取维护仓长期规则, When 查看主程序 / IntRuoyi 根目录描述, Then 应看到 `E:\IntRuoyi` 以及后端 `E:\IntRuoyi\IntRuoyiBackend`、前端 `E:\IntRuoyi\IntRuoyiFronted`。
- RED: pre-change-targeted-search -> FAIL, expected reason: `AGENTS.md`、`docs/experience-index.md`、发布/PowerShell 预检入口仍包含旧路径 `D:\ProjectPackage\Int\IntRuoyi` 或 `D:/ProjectPackage/Int/IntRuoyi`。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md` 与命中的 `docs/powershell-preflight-lessons.md`，确认本任务适用 UTF-8 读写、禁止 PowerShell 默认编码、禁止 `&&` 串联、只修改文档描述且不执行高风险动作。
- GREEN: path-description-update -> PASS，已更新 `AGENTS.md`、`docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-agent-checklist.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 中面向后续任务的主程序文档路径和源码目录示例；未修改运行控制台配置、发布脚本、测试契约或历史任务日志。
- GREEN: targeted-old-path-search -> PASS，排除 `doc/tasks/**` 与 `docs/request-command-log.md` 后，`AGENTS.md` 和 `docs` 中旧主程序子路径 `D:\ProjectPackage\Int\IntRuoyi\` / `D:/ProjectPackage/Int/IntRuoyi/` 无命中。
- GREEN: new-path-structure-search -> PASS，目标文档已包含 `E:\IntRuoyi`、`E:\IntRuoyi\IntRuoyiBackend`、`E:\IntRuoyi\IntRuoyiFronted`。
- GREEN: diff-check -> PASS，`git diff --check -- AGENTS.md docs/experience-index.md docs/test-release-preflight.md docs/release-agent-checklist.md docs/release-build-preflight-lessons.md docs/powershell-preflight-lessons.md doc/tasks/20260724-main-program-path-description/task.md doc/tasks/20260724-main-program-path-description/execution-log.md` 退出码为 0；仅输出 Git 换行规范 warning。
