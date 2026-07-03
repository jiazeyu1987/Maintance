# 20260703-codeonly-three-env-release IntRuoyi 不带数据三环境发布闭环

## 任务目标

执行 IntRuoyi code-only / 不带数据完整三环境发布闭环，使用当前后端、前端、维护仓 `int_main` 已提交 HEAD，在本轮专用干净临时发布 worktree 中构建并发布到测试服、正式服和备份服，最终完成同一 releaseTag 的完整验证。

## 上一任务检查

- `20260703-build-publish-test-again`：- 状态：已完成。

## 发布输入

| 仓库 | 路径 | 分支 | 目标提交 | 主工作区 dirty |
| --- | --- | --- | --- | --- |
| backend | `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` | `int_main` | `4ef9206881465189f06d4dd8db30c4bacf03b5d8` | true |
| frontend | `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` | `int_main` | `0587b626a86a570016a53dae350a4a4bbea2e81f` | true |
| maintenance | `D:\ProjectPackage\Int\IntRuoyiMaintance` | `int_main` | `14fcac2349d79a33351dca1ed65d99bfe9b40982` | true |

> 主工作区 dirty 状态只作为隔离约束记录；发布包输入必须来自干净临时发布 worktree 的目标提交，未提交改动和未跟踪文件不得进入发布包。

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
- 收尾前必须恢复 `runtime-control.local.yaml` 主路径，验证本机运行控制台 health=UP，删除本轮临时发布 worktree。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，按既有发布脚本、manifest 与服务器真实运行态门禁执行。
- 是否存在临时补丁或绕过：否。

## 里程碑

1. 创建任务文档并记录发布前置经验门禁。
2. 创建后端、前端临时发布 worktree，并确认 commit、branch、dirty=false。
3. 将运行控制台配置指向本次临时发布 worktree，验证本机 health=UP。
4. 执行 `build-release`，生成新 releaseTag，并校验 build operation 与 manifest。
5. 执行 `publish-test`，验证测试服运行态后 `mark-tested`。
6. 执行 `promote-prod`，验证正式服运行态。
7. 执行 `promote-backup`，验证备份服运行态和 `/mnt/intruoyi-data` 挂载。
8. 恢复 runtime-control 主路径，清理临时 worktree，更新日志并提交本任务文档。

## 预期验证

- 同一 releaseTag 完成五个 SUCCESS operation：build-release、publish-test、mark-tested、promote-prod、promote-backup。
- 测试服、正式服、备份服均验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200。
- 备份服额外验证 `/mnt/intruoyi-data` 挂载和发布路径正确。
- 发布包 manifest 为 `publishScope=code-only`，`sourceRepos` dirty=false，且发布包不包含数据目录。
- 临时发布 worktree 已删除，运行控制台配置已恢复主路径。

## 当前状态

- 状态：进行中。
- 已完成：任务文档初始化、目标提交和主工作区 dirty 基线记录、经验门禁摘录。
- 阻塞：无；主工作区 dirty 不进入发布包，后续通过专用干净 release worktree 隔离。

## 执行记录

- 2026-07-03 23:21:20 初始化任务文档。

- 2026-07-03 23:24:52 +08:00 创建本轮临时发布 worktree：维护仓 $wtMaint、后端 $wtBackend、前端 $wtFrontend；后端/前端 dirty=false，维护仓只含 gitignored 的本地 runtime 配置副本。
## 完成状态

- 当前状态：Completed
- 完成时间：2026-07-04 01:16:34 +08:00
- releaseTag：release-20260703-2335-codeonly-three-env
- 发布范围：code-only / 不带数据，构建使用 SkipDatabaseSync 与 SkipMinioSync。
- 完整闭环：build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup。
- 五个 operation：build-release、publish-test、mark-tested、promote-prod、promote-backup 均为 SUCCESS。
- 测试服验证：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200 均通过。
- 正式服验证：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200 均通过。
- 备份服验证：.env IMAGE_TAG、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、/mnt/intruoyi-data 挂载和发布路径均通过。
- 运行控制台：已恢复主维护仓 jar 与主配置，health=UP。
- 临时发布 worktree：已删除，git worktree prune 后不再列出本次路径。
- task-closeout-cleanup：已执行 preview，见 `evidence/task-closeout-cleanup-preview.txt`。

## 最终验证证据

- build-release operation：`evidence/build-release-op-2026-07-03T153405744077400Z-02fbe71d-f709-4364-b21c-90821b63c934-operation.json`
- publish-test operation：`evidence/publish-test-op-2026-07-03T155449725216100Z-adc5802d-1d2e-4199-8635-81110bf97774-operation.json`
- mark-tested operation：`evidence/mark-tested-op-2026-07-03T161333772184700Z-06061413-1db6-43a9-97e5-863ca79e0f97-operation.json`
- promote-prod operation：`evidence/promote-prod-op-2026-07-03T163511316141200Z-89e50181-d9b3-4874-8c72-893e90ac8c48-operation.json`
- promote-backup operation：`evidence/promote-backup-op-2026-07-03T165324146656100Z-83717ddc-3a40-41f3-bb28-ae4b1e9d3dba-operation.json`
- 测试服验证：`evidence/test-server-verification-final.txt`
- 正式服验证：`evidence/prod-server-verification-final.txt`
- 备份服验证：`evidence/backup-server-verification-final.txt`
- 运行控制台恢复：`evidence/runtime-control-main-restore-final-check-corrected.json`
- 临时 worktree 清理：`evidence/temporary-release-worktree-cleanup-longpath-final.json`
