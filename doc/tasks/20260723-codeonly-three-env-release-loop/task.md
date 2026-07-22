# 20260723 不带数据三环境发布闭环

## Task Goal

使用维护仓、后端仓、前端仓当前 `int_main` 已提交 HEAD，在本次专用干净临时发布 worktree 中执行 IntRuoyi code-only / 不带数据完整三环境发布闭环，并完成同一 `releaseTag` 的测试服、正式服、备份服验证。

## Scope

- 发布输入：`D:\ProjectPackage\Int\IntRuoyiMaintance`、`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`、`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 当前 `int_main` HEAD。
- 包含：维护仓/后端仓/前端仓临时发布 worktree、运行控制台切换、`build-release`、`publish-test`、`mark-tested`、`promote-prod`、`promote-backup`、三环境运行态验证、运行控制台恢复、worktree 清理和任务记录提交。
- 排除：数据库同步、MinIO 同步、备份、恢复、回滚、未提交改动或未跟踪文件进入发布包。
- 正式服与备份服发布授权：用户已给出 `PROD` 确认口径。

## Milestones

1. 写入维护仓任务文档和执行日志。
2. 摘录发布前置经验门禁，记录 `GREEN: experience-preflight -> PASS`。
3. 创建维护仓、后端仓、前端仓临时发布 worktree，并确认 commit、branch、dirty=false。
4. 将运行控制台配置指向临时发布 worktree，验证 `http://127.0.0.1:48181/actuator/health=UP`。
5. 执行 code-only `build-release`，生成新的 `releaseTag`。
6. 校验 build operation、manifest、`publishScope=code-only`、sourceRepos dirty=false、发布包不含数据目录。
7. 执行 `publish-test` 到测试服 `172.30.30.58` 并验证运行态。
8. 测试服验证通过后执行 `mark-tested`。
9. 执行带 `ConfirmText=PROD` 与 `RequireTested` 的 `promote-prod` 并验证正式服运行态。
10. 执行带 `/mnt/intruoyi-data` 参数的 `promote-backup` 并验证备份服运行态、挂载和路径。
11. 恢复 `runtime-control.local.yaml` 主路径，验证运行控制台 health=UP，删除本轮临时发布 worktree，更新任务文档和请求命令日志。
12. 提交本任务直接产生的任务文档、执行日志、请求日志和必要经验沉淀文件。

## Expected Verification

- 同一 `releaseTag` 完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`。
- 五个 operation 均为 `SUCCESS`。
- 测试服、正式服、备份服均验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200。
- 备份服额外验证 `/mnt/intruoyi-data` 挂载、release root 和 data root 正确。
- 临时发布 worktree 已删除，运行控制台配置已恢复主路径且 health=UP。
- 任务文档标记完成，执行日志记录全部证据，相关改动按提交隔离规则单独提交。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`：本轮命中维护仓发布清单、发布执行 checklist、发布/备份/恢复基线、服务器访问和 worktree 清理门禁；高风险发布动作前必须记录 `GREEN: experience-preflight -> PASS`。
- `docs/release-build-preflight-lessons.md`：完整三环境发布必须沿单一 `releaseTag` 完成闭环；`code-only` 必须显式 `-Component intruoyi -SkipDatabaseSync -SkipMinioSync`，且不得跳过 schema、required SQL、migration 或 manifest 门禁；构建后必须核 manifest `publishScope=code-only`、sourceRepos commit 与 `dirty=false`，发布包不得含数据目录。
- `docs/release-agent-checklist.md`：执行模型为 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；失败先冻结 operation JSON、脱敏日志、preview 参数、manifest 状态、远端关键输出和失败时间；修复后必须用新 `releaseTag`，不得拼接不同 `releaseTag`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布代码入口统一在维护仓；构建发布包必须通过运行控制台或等价前端操作提交 operation；发布成功以 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像、health、frontend HTTP、PDF worker 和 release-info 共同判定。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服为 `172.30.30.58`，备份服为 `172.30.30.59`，远端运行目录统一 `/opt/intruoyi/runtime`；备份服与正式服同等级门禁，必须显式使用 `/mnt/intruoyi-data`、`/mnt/intruoyi-data/runtime-data`、`/mnt/intruoyi-data/intruoyi-releases`、`/dev/mapper/cl-home` 和 `intruoyi-minio`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`：发布专用 worktree 使用短路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><短标识>\m|b|f`；runtime-control 的本地 config/state 置于 release worktree 外部；构建和运行控制台启动后必须复核三仓 worktree `dirty=false`；收尾必须同时证明 Git 注册和物理目录均清理完成。
- `docs/release-build-preflight-lessons.md#2026-07-19-build-release-mes-companion-contract-编译门禁`：clean release worktree 的 MES 编译门禁必须覆盖已提交实现引用的 companion VO/Service/Mapper/ParsedCell 方法；缺失 `isReviewedCellRule`、`getCellRuleSource` 或出现 `@Override` 签名漂移时，不得继续 build-release，必须先冻结证据、沉淀经验、补 RED/GREEN 合同测试并修复已提交 HEAD。
- `docs/release-build-preflight-lessons.md#2026-07-23-frontend-buildtest-vite-progress-cache-门禁`：若 `pnpm build:test` 被中断或超时，重跑前必须确认无残留 node/vite 进程，并清理 `node_modules\.progress` / `node_modules\.progress.json` / `dist` / `dist-test`，否则 `vite-plugin-progress` 会因 `EEXIST` 再次失败；构建通过后也要清理本地输出再进入 release build。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本轮按既有运行控制台、manifest、operation、远端运行态和 worktree 清理证据闭环执行。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Completed Work

- 已创建维护仓任务目录、写入任务文档和执行日志，并摘录发布前置经验门禁。
- 已记录 `GREEN: experience-preflight -> PASS`，并按用户授权 `PROD` 执行正式服和备份服发布。
- 已创建并使用本轮干净 release worktree；失败轮次 `r260723r` 不生成 releaseTag，最终闭环使用 `r260723s`。
- 已完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，同一 releaseTag 为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- 已完成测试服 `172.30.30.58`、正式服 `172.30.30.57`、备份服 `172.30.30.59` 运行态验证。
- 已恢复运行控制台主路径并验证 `http://127.0.0.1:48181/actuator/health=UP`。
- 已删除本次临时 release worktree/state 物理目录并确认三仓 worktree 注册不含 `r260723r` 或 `r260723s`。

## Verification Evidence

- `GREEN: experience-preflight -> PASS` 已记录在执行日志。
- Worktree 冻结：maintenance `ccca443d3c5d20da3b07e21e48cb79737bd836f9` / branch `codex/r260723r` / dirty=false；backend `63edb0502ce13b695f883f33fab40857fac56873` / branch `codex/r260723r` / dirty=false；frontend `2989ec4d711d96be77bb2c6244f7189b7815a745` / branch `codex/r260723r` / dirty=false。
- 运行控制台切换验证：`http://127.0.0.1:48181/actuator/health=UP`。
- RED: build-release 前 MES companion compile gate 失败，证据 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260723-codeonly-three-env-release-loop\evidence\mes-release-companion-test-r260723r.log`。
- RED: 前端 build-test 中断残留 `.progress` 后重跑失败，证据 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260723-codeonly-three-env-release-loop\evidence\frontend-build-test-r260723s.log`。
- GREEN: build-release operation `op-2026-07-22T175810310071200Z-7cb76546-9daa-43eb-b41c-dd4e73b9cc33` 为 `SUCCESS`；manifest 验证 `publishScope=code-only`、sourceRepos dirty=false、发布包不含数据目录，证据 `evidence\manifest-validation-r260723s.json`。
- GREEN: publish-test operation `op-2026-07-22T181416808987800Z-e34ba850-6090-45b1-9f1c-91fd1520aff8` 为 `SUCCESS`；测试服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP 均通过，证据 `evidence\verify-test-server-r260723s.txt`。
- GREEN: mark-tested operation `op-2026-07-22T183551381955800Z-b585c04f-7b40-4186-8f24-939a1aaf57d6` 为 `SUCCESS`，证据 `evidence\mark-tested-operation-r260723s-final.json`。
- GREEN: promote-prod operation `op-2026-07-22T183923974967500Z-1c2b9700-98d1-4030-9281-6db971d70660` 为 `SUCCESS`；正式服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP 均通过，证据 `evidence\verify-prod-server-r260723s.json`。
- GREEN: promote-backup operation `op-2026-07-22T190310805388600Z-632cc7e5-cf73-45b1-b8ba-f43ecffe54ca` 为 `SUCCESS`；备份服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP、`/mnt/intruoyi-data` 挂载、release path、runtime-data 均通过，证据 `evidence\verify-backup-server-r260723s.json`。
- GREEN: runtime-control main restore -> PASS，PID `59516`，主 Jar 存在，配置 allowlist 指向主维护仓路径，无 `r260723s` 路径泄漏，证据 `evidence\runtime-control-main-restore-r260723s.json`。
- GREEN: release worktree cleanup -> PASS，三仓 `git worktree list` 不含 `r260723r`/`r260723s`，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723s`、`r260723s-state`、`r260723r`、`r260723r-state` 均不存在，证据 `evidence\worktree-cleanup-r260723s.json`。

## Remaining Blockers

- 无。
