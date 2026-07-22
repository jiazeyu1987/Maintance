# Execution Log - 20260723 不带数据三环境发布闭环

## Request

执行 IntRuoyi 不带数据的完整三环境发布闭环，直到测试服务器、正式服务器、备份服务器全部发布成功并完成验证。

## BDD Scenarios

- BDD: code-only three-env release loop -> Given 当前维护仓、后端仓、前端仓 `int_main` HEAD 作为发布输入且不包含未提交改动, When 使用本次专用临时发布 worktree 构建并依次发布测试服、正式服、备份服, Then 同一 `releaseTag` 的五个 operation 均为 `SUCCESS` 且三环境运行态验证全部通过。
- BDD: no-data publish contract -> Given 本轮发布范围为 code-only, When 执行 `build-release`, Then 构建参数包含 `SkipDatabaseSync` 与 `SkipMinioSync` 且 manifest `publishScope=code-only`、发布包不包含数据目录。
- BDD: backup server data mount guard -> Given 备份服发布目标为 `172.30.30.59`, When 执行 `promote-backup`, Then 显式使用 `/mnt/intruoyi-data` 参数并验证数据盘挂载、release root 和 data root 正确。

## Milestone Evidence

- 2026-07-23 00:26 Asia/Shanghai: 创建维护仓任务目录 `doc/tasks/20260723-codeonly-three-env-release-loop/`。
- 2026-07-23 00:27 Asia/Shanghai: 已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`，索引指向维护仓 `docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md`。
- 2026-07-23 00:27 Asia/Shanghai: 已读取维护仓 `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md` 和根仓 `docs/release-backup-restore.md`、`docs/server-access.md`、`docs/worktree-memory.md`，确认 code-only 三环境发布、正式/备份授权、worktree 清理和远端验证门禁。
- 2026-07-23 00:29 Asia/Shanghai: 创建三仓临时发布 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723r\m|b|f`，外部 state 根 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723r-state`。
- 2026-07-23 00:29 Asia/Shanghai: maintenance `ccca443d3c5d20da3b07e21e48cb79737bd836f9` branch=`codex/r260723r` dirty=false；backend `63edb0502ce13b695f883f33fab40857fac56873` branch=`codex/r260723r` dirty=false；frontend `2989ec4d711d96be77bb2c6244f7189b7815a745` branch=`codex/r260723r` dirty=false。
- 2026-07-23 00:29 Asia/Shanghai: 主工作区存在未归属脏改，已通过临时发布 worktree 冻结已提交 HEAD，未将未提交改动纳入发布输入。
- 2026-07-23 00:56 Asia/Shanghai: 已停止旧 release worktree 运行控制台进程，生成外部 state 配置 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723r-state\runtime-control.local.yaml`，维护仓 runtime-control 构建与后端 Maven 测试通过，启动本轮 runtime-control PID `52688`，`http://127.0.0.1:48181/actuator/health=UP`。
- 2026-07-23 00:56 Asia/Shanghai: build-release 前置门禁中，后端 migration policy gate、SQL/static pytest、前端 `pnpm install --frozen-lockfile`、前端 `pnpm build:test`、Docker CLI/BuildKit 预检均通过，证据位于本任务 evidence 目录。
- 2026-07-23 00:56 Asia/Shanghai: RED: MES companion compile gate 在 build-release 前失败，命令 `mvn.cmd -pl yudao-module-mes "-Dtest=MesReleaseCompanionContractTest" test` 返回 Maven compile failure，尚未创建 releaseTag，未执行 build-release/publish-test/mark-tested/promote-prod/promote-backup。
- 2026-07-23 01:33 Asia/Shanghai: RED: 前端 `pnpm build:test` 在 build-release 前置门禁阶段失败；首次执行被 360 秒工具超时截断，随后重跑命中 `vite-plugin-progress` 创建 `node_modules\.progress` 时 `EEXIST`。失败日志已冻结到 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260723-codeonly-three-env-release-loop\evidence\frontend-build-test-r260723s.log`，尚未创建 releaseTag，未执行 build-release/publish-test/mark-tested/promote-prod/promote-backup。
- 2026-07-23 01:42 Asia/Shanghai: 已将 `pnpm build:test` 超时残留 `node_modules\.progress` 导致 `vite-plugin-progress EEXIST` 的可复用门禁写入维护仓 `docs/release-build-preflight-lessons.md`，并同步维护仓 `docs/experience-index.md` 关键词路由。
- 2026-07-23 01:54 Asia/Shanghai: 按门禁确认前端 worktree 无残留构建进程，清理 `node_modules\.progress` / `dist-test` 后重跑 `pnpm.cmd build:test` 通过；构建成功后再次清理 `node_modules\.progress` / `dist-test`，三仓 release worktree `git status --short` 均为空。
- 2026-07-23 02:12 Asia/Shanghai: `build-release` operation `op-2026-07-22T175810310071200Z-7cb76546-9daa-43eb-b41c-dd4e73b9cc33` 完成 `SUCCESS`，releaseTag=`release-20260723-intmain-codeonly-three-env-r260723s-r1`；manifest `publishScope=code-only`，后端/前端 `sourceRepos dirty=false`，发布包无 forbidden data directories。
- 2026-07-23 02:33 Asia/Shanghai: `publish-test` operation `op-2026-07-22T181416808987800Z-e34ba850-6090-45b1-9f1c-91fd1520aff8` 完成 `SUCCESS`；测试服 `172.30.30.58` 独立 SSH 验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health `UP`、frontend HTTP `200`、PDF worker HTTP `200` 均匹配 releaseTag。
- 2026-07-23 02:36 Asia/Shanghai: `mark-release-tested` operation `op-2026-07-22T183551381955800Z-b585c04f-7b40-4186-8f24-939a1aaf57d6` 完成 `SUCCESS`，使用恢复候选 `restore:20260621-063218`。
- 2026-07-23 02:45 Asia/Shanghai: `promote-prod` operation `op-2026-07-22T183923974967500Z-1c2b9700-98d1-4030-9281-6db971d70660` 完成 `SUCCESS`；正式服 `172.30.30.57` 独立 SSH 验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health `UP`、frontend HTTP `200`、PDF worker HTTP `200` 均匹配 releaseTag。
- 2026-07-23 03:16 Asia/Shanghai: `promote-backup` operation `op-2026-07-22T190310805388600Z-632cc7e5-cf73-45b1-b8ba-f43ecffe54ca` 完成 `SUCCESS`；备份服 `172.30.30.59` 独立 SSH 验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health `UP`、frontend HTTP `200`、PDF worker HTTP `200`、`/mnt/intruoyi-data` 挂载源 `/dev/mapper/cl-home`、release path 与 runtime-data 均通过。
- 2026-07-23 03:26 Asia/Shanghai: 已恢复运行控制台主路径，PID `59516`，`http://127.0.0.1:48181/actuator/health=UP`，主 Jar 存在，配置 allowlist 指向主维护仓路径，无 `r260723s` 路径泄漏。
- 2026-07-23 03:30 Asia/Shanghai: 已清理本次临时 release worktree/state；maintenance/backend/frontend `git worktree list` 均不含 `r260723r` 或 `r260723s`，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723s`、`r260723s-state`、`r260723r`、`r260723r-state` 均不存在。
- 2026-07-23 03:31 Asia/Shanghai: 任务状态更新为 `completed`；最终闭环 releaseTag=`release-20260723-intmain-codeonly-three-env-r260723s-r1`。

## TDD / Verification Markers

- GREEN: experience-preflight -> PASS, matched=root experience-index, maintenance release-build-preflight-lessons, maintenance release-agent-checklist, root release-backup-restore, root server-access, root worktree-memory; scope=code-only build-release/publish-test/mark-tested/promote-prod/promote-backup; PROD authorization confirmed by user request.
- RED: mvn.cmd -pl yudao-module-mes "-Dtest=MesReleaseCompanionContractTest" test -> FAIL, build-release 前 MES companion compile gate 在 clean release worktree 失败，缺少 `MesProBatchRecordParsedCell.isReviewedCellRule()` / `getCellRuleSource()`，且 `MesProBatchRecordExecutionBusinessApprovalEffectExecutor` 的 `@Override` 命中父契约解析漂移。
- GREEN: mvn.cmd -pl yudao-module-mes -am "-Dtest=MesReleaseCompanionContractTest" "-Dsurefire.failIfNoSpecifiedTests=false" test -> PASS, 5 tests, companion contract 覆盖 ParsedCell reviewed rule 与 BPM process definition key。
- GREEN: mvn.cmd -pl yudao-module-mes -am "-DskipTests" compile -> PASS, yudao-module-mes 及上游模块编译通过。
- RED: pnpm build:test -> FAIL, interrupted frontend build left `node_modules\.progress` as a directory; retry failed with `Error: EEXIST: file already exists, mkdir '<frontend>\node_modules\.progress'`.
- GREEN: release-build-preflight-lessons frontend progress cache lesson -> PASS, documented cleanup gate for interrupted `pnpm build:test` before retrying release preflight.
- GREEN: pnpm.cmd build:test -> PASS, retry log `frontend-build-test-r260723s-retry.log` exitCode=0; post-build cleanup log `frontend-post-build-cache-cleanup-r260723s.log` confirms `.progress`, `.progress.json`, `dist`, and `dist-test` absent.
- GREEN: build-release-r260723s -> PASS, preview `build-release-preview-r260723s.utf8.json` validated `-Component intruoyi`, `-SkipDatabaseSync`, `-SkipMinioSync`, test/prod/backup hosts, backend/frontend worktree roots, and no target environment; operation final JSON and sanitized log frozen under evidence.
- GREEN: manifest-validation-r260723s -> PASS, releaseTag `release-20260723-intmain-codeonly-three-env-r260723s-r1`, `publishScope=code-only`, sourceRepos dirty=false, and no forbidden data directories.
- GREEN: publish-test-r260723s -> PASS, preview `publish-test-preview-r260723s.utf8.json` validated deployment-only payload for `172.30.30.58`; operation final JSON and sanitized log frozen under evidence.
- GREEN: verify-test-server-r260723s -> PASS, `verify-test-server-r260723s.txt/json` confirm env tag, backend image, frontend image, backend health, frontend HTTP, and PDF worker HTTP all match releaseTag.
- GREEN: mark-tested-r260723s -> PASS, preview `mark-tested-preview-r260723s.utf8.json` validated releaseTag, test conclusion, and recovery set candidate; operation final JSON and sanitized log frozen under evidence.
- GREEN: promote-prod-r260723s -> PASS, preview `promote-prod-preview-r260723s.utf8.json` validated releaseTag, `ConfirmText=PROD`, and `RequireTested`; operation final JSON and sanitized log frozen under evidence.
- GREEN: verify-prod-server-r260723s -> PASS, `verify-prod-server-r260723s.txt/json` confirm env tag, backend image, frontend image, backend health, frontend HTTP, and PDF worker HTTP all match releaseTag.
- GREEN: promote-backup-r260723s -> PASS, preview `promote-backup-preview-r260723s.utf8.json` validated releaseTag and explicit `/mnt/intruoyi-data` backup parameters; operation final JSON and sanitized log frozen under evidence.
- GREEN: verify-backup-server-r260723s -> PASS, `verify-backup-server-r260723s.txt/json` confirm env tag, backend image, frontend image, backend health, frontend HTTP, PDF worker HTTP, `/mnt/intruoyi-data` mount source `/dev/mapper/cl-home`, release path, runtime-data, and runtime app path.
- GREEN: runtime-control-main-restore-r260723s -> PASS, `runtime-control-main-restore-r260723s.json` confirms health `UP`, PID `59516`, main Jar present, config allowlist on main paths, and releasePathLeak=false.
- GREEN: worktree-cleanup-r260723s -> PASS, `worktree-cleanup-r260723s.json` confirms no `r260723r`/`r260723s` registrations in maintenance/backend/frontend worktree lists and physical release/state paths absent.

## Failure Evidence

- 2026-07-23 00:56 Asia/Shanghai: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260723-codeonly-three-env-release-loop\evidence\mes-release-companion-test-r260723r.log` 冻结失败证据；失败摘要：`MesProBatchRecordExecutionBusinessApprovalEffectExecutor.java:[65,5]` 的 `@Override` 方法未覆盖或实现父类型方法；`MesProBatchRecordReportJsonBuilder.java:[1119,17]` 缺少 `MesProBatchRecordParsedCell.isReviewedCellRule()`；`MesProBatchRecordReportJsonBuilder.java:[1120,33]` 缺少 `MesProBatchRecordParsedCell.getCellRuleSource()`。
- 2026-07-23 01:33 Asia/Shanghai: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260723-codeonly-three-env-release-loop\evidence\frontend-build-test-r260723s.log` 冻结失败证据；失败摘要：`vite-plugin-progress` 在 `closeBundle` 中执行 `mkdir node_modules\.progress`，但该路径已由上次被超时打断的 `pnpm build:test` 留存为目录，导致 `EEXIST`。
