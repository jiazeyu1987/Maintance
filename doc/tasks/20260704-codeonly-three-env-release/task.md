# 20260704-codeonly-three-env-release IntRuoyi 不带数据三环境发布闭环

## 任务目标

执行 IntRuoyi code-only / 不带数据完整三环境发布闭环，使用当前后端、前端、维护仓 `int_main` 已提交 HEAD，在本轮专用干净临时发布 worktree 中构建并发布到测试服、正式服和备份服，最终完成同一 releaseTag 的完整验证。

## 上一任务检查

- `20260703-codeonly-three-env-release`：当前状态 `Completed`，完成时间 `2026-07-04 01:16:34 +08:00`。

## 发布输入

| 仓库 | 路径 | 分支 | 目标提交 | 主工作区 dirty |
| --- | --- | --- | --- | --- |
| backend | `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` | `int_main` | `ddd93f9089b510c323417d0aee91708099448ebf` | false |
| frontend | `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` | `int_main` | `cc2cef81e11220a6ba50b8931dfca5811a368401` | false |
| maintenance | `D:\ProjectPackage\Int\IntRuoyiMaintance` | `int_main` | `3df8d5a96920f8fd9bb7ec7362499bb52940e55d` | true |

> 维护仓主工作区存在既有未提交文档/运行产物；本次发布包输入必须来自专用干净临时发布 worktree 的目标提交，未提交改动和未跟踪文件不得进入发布包。

## 发布范围

- code-only / 不带数据发布。
- 构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`。
- 不执行备份、恢复或回滚。
- 正式服和备份服发布授权口径：`PROD` 确认。

## 经验门禁

- 已读取 `docs/experience-index.md`：本任务命中发布、code-only、临时 release worktree、服务器访问和 worktree 清理门禁；高风险动作前必须先在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。
- 已读取 `docs/release-build-preflight-lessons.md`：发布统一走本轮专用干净临时 worktree；`code-only` / `SkipDatabaseSync` / `SkipMinioSync` 不跳过 schema、required SQL、migration 或 manifest 门禁；构建后必须复核 manifest `publishScope=code-only`、sourceRepos branch/commit/dirty=false，且包内无数据目录。
- 已读取 `docs/release-build-preflight-lessons.md`：完整闭环只认单一 releaseTag 的 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；任一 blocker 修复后必须重新 `build-release` 生成新 releaseTag，不得拼接旧结果。
- 已读取 `docs/release-build-preflight-lessons.md`：运行控制台配置切到临时 worktree 后必须回读 YAML 和 `http://127.0.0.1:48181/actuator/health`；收尾前恢复主路径并再次验证。
- 已读取 `docs/release-build-preflight-lessons.md`：mark-tested 必须携带真实 `selectedRecoverySetCandidateId`；正式服/备份服验收不得硬编码宿主端口，必须先以 `docker compose ps` 或发布配置确认后端、前端和 PDF worker 端口。
- 已读取 `docs/release-agent-checklist.md`：测试服发布预览必须核对 `-Environment test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`；正式服发布必须带 `ConfirmText=PROD` 与 `RequireTested`；备份服发布必须核对 `172.30.30.59`、`/mnt/intruoyi-data`、`/mnt/intruoyi-data/runtime-data`、`/mnt/intruoyi-data/intruoyi-releases`、`/dev/mapper/cl-home`、`intruoyi-minio`。
- 已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台按钮或等价前端 action 提交 operation，命令行只用于只读核验、排障和脚本单测；缺少 manifest、schema 版本、环境凭据或授权必须 fail fast。
- 已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服 IP 为 `172.30.30.58`，备份服 IP 为 `172.30.30.59`，三台服务器远端运行目录为 `/opt/intruoyi/runtime`；正式/备份服本轮已有 `PROD` 授权；远端凭据不得写入仓库或任务文档。
- 已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`：发布工作必须记录临时 worktree 路径、目标 commit、branch、dirty=false、构建命令和验证命令；清理前必须预览并确认只处理本任务 worktree、运行时和临时产物。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，按既有发布脚本、manifest 与三服务器真实运行态门禁执行。
- 是否存在临时补丁或绕过：否。

## BDD 场景

- Given 本轮发布输入为三个仓库当前 `int_main` 已提交 HEAD；When 在专用干净临时发布 worktree 中执行 code-only build-release；Then manifest 必须记录 `publishScope=code-only`、sourceRepos dirty=false，且发布包不包含数据目录。
- Given 测试服 `172.30.30.58` 已按同一 releaseTag 发布；When 验证 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP；Then 全部必须通过后才能 mark-tested。
- Given releaseTag 已 mark-tested；When 使用 `ConfirmText=PROD` 和 `RequireTested` promote-prod；Then 正式服 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP 全部必须通过。
- Given 正式服验证通过；When 使用 `/mnt/intruoyi-data` 参数 promote-backup 到 `172.30.30.59`；Then 备份服 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP、数据盘挂载和发布路径全部必须通过。

## 里程碑

1. 创建任务文档并摘录发布前置经验门禁。
2. 创建后端、前端、维护仓临时发布 worktree，并确认 commit、branch、dirty=false。
3. 将运行控制台配置指向本次临时发布 worktree，验证 `http://127.0.0.1:48181/actuator/health=UP`。
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
- 已完成：任务文档初始化、上一任务完成状态检查、目标提交和主工作区 dirty 基线记录、发布前置经验门禁摘录、三仓临时 release worktree 创建与路径配置、临时维护仓运行控制台构建、48181 切换到临时 release worktree 控制台并验证 health=UP。
- 当前阻塞：后端 migration policy gate 失败，`20260704_showroom_product_target_market_text` 依赖不存在的 `20260519_showroom_v1_schema`；需先修复 SQL release-migration 元数据并重新验证后再 build-release。

## 执行记录

- 2026-07-04 23:44:12 +08:00 初始化任务文档。
- 2026-07-04 23:44:12 +08:00 完成 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`release-backup-restore.md`、`server-access.md`、`worktree-memory.md` 阅读与门禁摘录。
- 2026-07-04 23:54:10 +08:00 创建本轮临时 release worktree：维护仓、后端、前端均为计划提交 detached HEAD 且 dirty=false。
- 2026-07-04 23:56:00 +08:00 临时维护仓运行控制台构建失败，已冻结 stdout/stderr 证据，先补经验再修复。
- 2026-07-04 23:59:25 +08:00 修复临时维护仓 pnpm allowBuilds 前置状态后重建成功；Maven 测试 26 项通过并生成 runtime-control jar。
- 2026-07-05 00:04:30 +08:00 48181 已切换到本轮临时 release worktree 控制台，health=UP。
- 2026-07-05 00:07:34 +08:00 构建前 migration policy gate 失败，已冻结证据，尚未生成 releaseTag。

## Cleanup Candidates

- `doc/tasks/20260704-codeonly-three-env-release/evidence/`


## 发布输入更新
- 后端发布输入提交已更新为迁移依赖修复后的提交：933de66d093e4c78dadddf6c56400160cbceb1fb。
- 前端发布输入提交保持：cc2cef81e11220a6ba50b8931dfca5811a368401。

## 最终完成状态
- 状态：Completed
- 完成时间：2026-07-05 02:55:15 +0800
- releaseTag：`release-20260705-001827-codeonly-three-env`
- 发布范围：code-only / 不带数据；构建使用 SkipDatabaseSync 与 SkipMinioSync；未执行备份、恢复或回滚。
- 完整闭环：`build-release -> publish-test -> mark-release-tested -> promote-prod -> promote-backup`，五个 operation 均为 SUCCESS。
- 测试服：172.30.30.58，`.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200 全部通过。
- 正式服：172.30.30.57，`.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200 全部通过。
- 备份服：172.30.30.59，`.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200 全部通过；`/mnt/intruoyi-data` 挂载自 `/dev/mapper/cl-home`，发布目录与 runtime-data 均在该数据盘。
- 本机运行控制台：已恢复到主维护仓路径，`http://127.0.0.1:48181/actuator/health=UP`。
- 临时 release worktree：本轮专用根目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release` 已删除，三仓 worktree 元数据已 prune。
- 后端根因修复提交：`933de66d093e4c78dadddf6c56400160cbceb1fb`（迁移 dependsOn 门禁修复）。
- 主要证据：`evidence/final-release-loop-summary.json`、`evidence/test-server-verification-final.txt`、`evidence/prod-server-verification-final.txt`、`evidence/backup-server-verification-final.txt`、`evidence/runtime-control-main-restore-verification.json`、`evidence/worktree-removal-verification.json`。
