# 20260706-codeonly-three-env-current-head-release IntRuoyi 不带数据三环境发布闭环

Status: completed

## 任务目标

执行 IntRuoyi code-only / 不带数据完整三环境发布闭环，使用当前后端、前端、维护仓 `int_main` 已提交 HEAD，在本轮专用干净临时发布 worktree 中构建并发布到测试服、正式服和备份服，最终完成同一 releaseTag 的完整验证。

## 上一任务检查

- 最新任务：`20260706-dcc-policy-test-server-release`
- 状态：`completed`
- 结论：上一任务已完成，本轮可新建独立发布任务。

## 发布输入

| 仓库 | 路径 | 分支 | 目标提交 | 主工作区 dirty |
| --- | --- | --- | --- | --- |
| backend | `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` | `int_main` | `042037a42a91ac3e285bccbbccebd05f7507628d` | true |
| frontend | `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` | `int_main` | `ab36017e80982b9f308b2324b4d18c6f83792424` | true |
| maintenance | `D:\ProjectPackage\Int\IntRuoyiMaintance` | `int_main` | `19b121a72e0fe65c38137a154bf45e4f5391c438` | true |

> 主工作区 dirty 状态只作为隔离约束记录；发布包输入必须来自干净临时发布 worktree 的目标提交，未提交改动、未跟踪文件和脏工作区内容不得进入发布包。

## 经验门禁

- 只认已提交 `int_main` HEAD：主工作区未提交改动、未跟踪文件、脏工作区内容不得进入发布包；必须使用本轮专用干净临时发布 worktree。
- code-only / 不带数据发布：构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`；manifest 必须为 `publishScope=code-only`，发布包不得包含数据目录。
- 发布前必须读取并执行发布经验门禁：`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`release-backup-restore.md`、`server-access.md`、`worktree-memory.md`。
- 高风险动作前必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`；没有该记录不得执行发布、服务器写入或 worktree 清理。
- 构建后必须立即复核 manifest 的 `sourceRepos`：后端、前端、维护仓 branch/commit 与计划一致且 `dirty=false`，否则 releaseTag 判废。
- 完整闭环只认同一 releaseTag 的 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，不得拼接多轮结果。
- 任一步失败必须先冻结 operation JSON、operation log、预览参数、manifest 状态、远端关键输出与失败时间点；先沉淀可复用经验，再修根因或重试。
- 正式服/备份服发布本轮已获 `PROD` 授权；不执行备份、恢复或回滚。
- 备份服发布必须显式使用 `/mnt/intruoyi-data` 参数，并验证数据盘挂载与发布路径正确。
- runtime-control 切换临时 worktree 前后都必须验证 `http://127.0.0.1:48181/actuator/health=UP`，收尾必须恢复主路径。
- 发布脚本真实命令口径：构建使用 `-Mode build-release`；测试服/正式服/备份服发布使用 `-Mode deploy-release -Environment test|prod|backup`；测试通过标记使用 `-Mode mark-tested`。
- promote-prod / promote-backup 必须带 `-ConfirmText PROD -RequireTested`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，按既有发布脚本、manifest 与服务器真实运行态门禁执行。
- 是否存在临时补丁或绕过：否。

## BDD 场景

BDD: code-only 三环境发布闭环 -> Given 后端、前端、维护仓当前 `int_main` 已提交 HEAD 被检出到本轮专用干净发布 worktree When 使用 `SkipDatabaseSync` 与 `SkipMinioSync` 构建同一 releaseTag 并依次发布测试服、正式服、备份服 Then 五个 operation 必须均为 SUCCESS，三环境运行态必须全部匹配同一 releaseTag，备份服必须确认 `/mnt/intruoyi-data` 挂载与发布路径正确。

## 里程碑

1. M1：创建任务文档并记录发布前置经验门禁。
2. M2：创建后端、前端、维护仓临时发布 worktree，并确认 commit、branch、dirty=false。
3. M3：将运行控制台配置指向本次临时发布 worktree，验证本机 health=UP。
4. M4：执行 `build-release`，生成新 releaseTag，并校验 build operation 与 manifest。
5. M5：执行测试服发布，验证测试服运行态后 `mark-tested`。
6. M6：执行正式服发布，验证正式服运行态。
7. M7：执行备份服发布，验证备份服运行态和 `/mnt/intruoyi-data` 挂载。
8. M8：恢复 runtime-control 主路径，清理临时 worktree，更新日志并提交本任务文档。

## 预期验证

- 同一 releaseTag 完成五个 SUCCESS operation：build-release、publish-test、mark-tested、promote-prod、promote-backup。
- 测试服、正式服、备份服均验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200。
- 备份服额外验证 `/mnt/intruoyi-data` 挂载和发布路径正确。
- 发布包 manifest 为 `publishScope=code-only`，`sourceRepos` dirty=false，且发布包不包含数据目录。
- 临时发布 worktree 已删除，运行控制台配置已恢复主路径。
- 本次任务直接产生的任务文档、执行日志、请求日志和必要经验沉淀文件已按提交隔离规则单独提交。

## 当前状态

- 状态：已完成。
- 已完成：同一 releaseTag 的 code-only 三环境发布闭环、三环境验证、运行控制台恢复、临时 worktree 清理。
- 阻塞：无。

## 执行记录

- 2026-07-06 19:02:41 +08:00 初始化任务目录：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release`。
## 项目经验沉淀

- 2026-07-06：已将 M2 长路径 release worktree 失败经验沉淀到已有长期文档：D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md、docs/release-build-preflight-lessons.md、docs/release-agent-checklist.md。
- 结论：不新建经验文档；该经验属于 worktree 创建/发布前置门禁。

## 最终结果

Status: completed

- 最终 releaseTag：release-20260706-2245-codeonly-three-env-v6。
- 完整闭环：build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup 已用同一 releaseTag 完成。
- 五个关键 operation / 命令结论：build-release v6 PASS、publish-test v6 PASS、mark-tested v6 PASS、promote-prod operation op-2026-07-06T145929632013700Z-6235332a-37e7-46fb-9802-10b30080ac88 SUCCESS、promote-backup operation op-2026-07-06T152642480550500Z-f8bfc329-aab8-4400-b723-7beada4fa2e3 SUCCESS。
- 测试服 172.30.30.58：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、release lock=APPLIED 均通过。
- 正式服 172.30.30.57：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、release lock=APPLIED 均通过。
- 备份服 172.30.30.59：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、release lock=APPLIED 均通过；/mnt/intruoyi-data 挂载、发布路径和数据路径均验证通过。
- code-only 校验：manifest publishScope=code-only，sourceRepos dirty=false，发布包无数据目录；构建/发布均使用 SkipDatabaseSync 与 SkipMinioSync。
- 收尾：运行控制台已恢复主工作区 jar 且 health=UP；本次临时发布 worktree 根 D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce 已删除。

## 最终证据索引

- 构建与包校验：evidence/build-release-v6-command-summary.txt、evidence/build-release-v6-package-validation-summary.txt、evidence/build-release-v6-package-validation.json。
- 测试服发布与验证：evidence/publish-test-v6-command-summary.txt、evidence/test-server-v6-verification-v5-summary.txt、evidence/test-server-v6-release-lock-verification-v7-summary.txt。
- mark-tested：evidence/mark-tested-v6-retry-command-summary.txt。
- 正式服：evidence/promote-prod-v6-command-summary-corrected.txt、evidence/prod-server-v6-verification-summary.txt、evidence/promote-prod-v6-operation-state.json。
- 备份服：evidence/promote-backup-v6-command-summary.txt、evidence/backup-server-v6-verification-summary.txt、evidence/promote-backup-v6-operation-state-verified.json。
- 收尾：evidence/runtime-restore-failure-inspection.txt、evidence/worktree-removal-final-force-residual.txt、evidence/task-closeout-cleanup-preview.txt。