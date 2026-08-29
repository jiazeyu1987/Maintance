# 20260829 带分段耗时统计的仅测试服真实发布执行日志

## Log

- BDD: timed test release -> Given 当前已提交 HEAD 和本轮专用 release worktree，When 执行仅测试服真实发布，Then 同一 releaseTag 必须完成 `build-release -> publish-test` 并通过真实运行态、页面、版本说明和分段耗时报告验证。
- GREEN: experience-preflight -> PASS。已读取并摘取本任务命中的发布、服务器、登录、worktree、PowerShell、测试服发布、构建发布经验门禁；本次范围限定为仅测试服真实发布，不执行 `mark-tested`、`promote-prod`、`promote-backup`。
- INFO: timing-scope -> 本次分段计时至少覆盖文档/门禁、目标 HEAD 复核、release worktree 创建、发布前置测试、runtime-control 构建启动、build-release、publish-test、远端运行态/页面验证、收尾清理。
- GREEN: release-worktree-create -> PASS，维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k\m` 固定 `eb1193f1e3dec75ed87cb01a10464a05e2e91d60`，应用 worktree `D:\IntRuoyiWorktree\r260829k\a` 固定 `3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`，耗时 92.541s。
- GREEN: maintenance-release-contract-tests -> PASS，`python -X utf8 -m pytest scripts\tests -q --basetemp <state>\pytest-maintenance` -> `79 passed`，耗时 1.041s。
- GREEN: runtime-control-build -> PASS，控制台 JAR SHA256=`DC24D9969A3C34CEA5C5643FF965AD7703572B60A2C51DB1CDD5807D217225B1`，耗时 274.128s；端口 `48196` health=UP，启动耗时 40.902s。
- RED: build-release-r1 -> FAIL，releaseTag `release-20260829-timed-head-test-r260829k-r1`，operation `op-2026-08-29T093553125136900Z-8c48c57b-e941-4bb4-ac35-56d685710dda`，30.172s 后失败，原因是 clean app worktree 缺少 `D:\IntRuoyiWorktree\r260829k\a\IntRuoyiFronted\node_modules\.bin\cross-env.cmd`；r1 已作废。
- GREEN: app-frontend-dependency-prepare -> PASS，`prepare-frontend-dependencies.ps1` 补齐 `cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd`，耗时 461.456s。
- GREEN: build-release-r2 -> PASS，releaseTag `release-20260829-timed-head-test-r260829k-r2`，operation `op-2026-08-29T094711769603400Z-ded24bdd-b6fc-40f1-a43a-79f8a9232111`，耗时 840.638s。
- GREEN: manifest-package-validation-r2 -> PASS，Manifest v1 与 legacy manifest 均匹配 r2；component=`intruoyi`，publishScope=`code-only`，sourceRepos dirty=false，requiredSqlCount=532，artifactCount=539。
- GREEN: publish-test-r2 -> PASS，operation `op-2026-08-29T100507230543400Z-9db39d71-d6b4-42f9-a030-61da96fc4c5f`，耗时 290.605s；日志确认使用 `deploy-control.tar`、`required-sql.tar`、`ops-runtime.tar`，镜像包 6 个分片上传。
- GREEN: remote-runtime-verification-r2 -> PASS，测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均匹配 r2，backend/frontend container running，backend health=UP，frontend HTTP=200，release-info 匹配 r2，lock=APPLIED，migration FAILED/RUNNING=0。
- GREEN: runtime-control-release-status-r2 -> PASS，`testCurrentReleaseTag` 与 `testCurrentReleaseNotes.releaseTag` 均匹配 r2，changesCount=3，sourceRepos dirty=false。
- GREEN: playwright-runtime-console-page-r2 -> PASS，本地控制台页面可见 r2，点击“查看变更”后弹窗包含发布包、组件范围与变更摘要；consoleErrors=0，failedRequests=0。
- INFO: timing-summary -> `timing-summary.json` / `timing-summary.md` 已生成；r2 成功核心链路 `build-release + publish-test` 为 1131.243s，r2 核心链路加发布前后验收为 1155.638s；从 worktree 创建到页面验收通过的自然墙钟为 3219.000s。
- GREEN: runtime-control-stop -> PASS，端口 `48196` 无监听，PID `47276` 已不存在。
- GREEN: task-closeout-cleanup-apply -> PASS，`task_closeout.py --mode apply` 删除本任务 helper 脚本和 runtime-control 启动临时文件，保留 `task.md`、`execution-log.md`、`verification-report.md` 与 timing 文件。
- GREEN: release-worktree-cleanup -> PASS，`r260829k` maintenance/app release worktree 均已从 Git worktree 登记移除，物理路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k\m` 与 `D:\IntRuoyiWorktree\r260829k\a` 均不存在。
- GREEN: project-experience-consolidation -> PASS，发布耗时与 clean app frontend 依赖预热经验已合并到 `docs/release-build-preflight-lessons.md`，并同步更新 `docs/experience-index.md` 关键词路由。
- GREEN: final-status -> PASS，任务状态更新为 `completed`。
