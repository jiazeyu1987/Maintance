# 20260709 当前 HEAD 测试服发布

Status: in_progress

## 任务目标

仅基于当前分支最新已提交代码构建维护控制台和 IntRuoyi code-only 测试发布包，并只发布到测试服务器。未提交改动、未跟踪文件和脏工作区内容不得进入构建产物。发布后必须验证真实运行态、运行控制台版本号与变更说明，并将问题沉淀为前置经验。

## 发布输入

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`，分支 `int_main`，目标提交 `91700a6b65190e1d6a651cf9a16a1f96207ed2a5`。
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，分支 `int_main`，原始目标提交 `549fa9199a7b8e8663d62aaee3d1c47d76e7a83a`；build-release 发现 SQL release metadata 阻塞后，已最小修复并提交为 `87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5`，后续构建目标更新为该已提交 HEAD。
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`，分支 `int_main`，目标提交 `d2022624d7c362400f0f8a976da59b828a06881f`。
- 主工作区状态：三仓均存在未提交改动；本次必须从上述 HEAD 创建短路径干净临时 worktree 构建，不允许主工作区脏内容进入发布包。
- 发布范围：仅测试服；不执行 `mark-tested`、正式服、备份服、备份、恢复或回滚。

## 经验门禁

- 发布前读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
- 主工作区 dirty 时必须使用本轮专用短路径临时 worktree，例如 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m|b|f`。
- 构建前必须记录三仓目标提交、分支、dirty 状态、worktree 路径和构建目录。
- build-release 成功后必须以发布包根目录 `manifest.json` 为完整契约入口，校验 `releaseTag`、`publishScope`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`，不得用 `release-manifest.json` 替代。
- 如 manifest、版本号、变更说明或构建来源无法确认，必须 fail fast，不得继续发布。
- `publish-test` 预览必须确认目标环境为 `test`、ServerHost 为 `172.30.30.58`、RemoteAppDir 为 `/opt/intruoyi/runtime`，不得出现正式服或备份服动作。
- 发布后必须验证 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP 200、前端页面、运行控制台版本号和变更说明。
- PowerShell/中文/SSH 相关命令必须显式 UTF-8；PowerShell 5.1 不使用 `&&`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；通过干净 HEAD worktree、manifest 和远端运行态验证证明发布输入与输出。
- 是否存在临时补丁或绕过：否。

## BDD 场景

- BDD: 当前 HEAD 测试服发布 -> Given 三仓主工作区存在未提交改动且目标 HEAD 已固定 / When 从目标 HEAD 创建干净临时 worktree 构建并发布到测试服 / Then 发布包 manifest 必须证明 sourceRepos 为目标提交且 dirty=false，测试服真实运行态必须运行同一 releaseTag。
- BDD: 发布信息可追溯 -> Given build-release 生成发布包 / When 检查 manifest、版本号和变更说明 / Then 版本号和变更说明必须能对应本次构建提交，否则阻塞发布。

## 里程碑

1. M1：建立任务文档、读取经验门禁并记录三仓 Git 基线。COMPLETED
2. M2：创建短路径干净临时 worktree，并验证三仓均为目标 HEAD 且 clean。COMPLETED
3. M3：构建维护控制台，切换运行控制台配置到临时 worktree 并验证本地健康。COMPLETED
4. M4：构建测试发布包，校验发布包、manifest、版本号与变更说明。COMPLETED
5. M5：仅发布测试服，并验证真实运行态与运行控制台发布信息。IN_PROGRESS
6. M6：记录所有问题、沉淀前置经验、清理临时 worktree 并提交本任务产物。PENDING

## 预期验证

- GREEN: experience-preflight -> PASS。
- GREEN: release-worktree-create -> PASS，三仓临时 worktree 均为计划 HEAD 且 dirty=false。
- GREEN: build-release -> PASS，`manifest.json` 可证明 sourceRepos 为目标提交且 dirty=false。
- GREEN: publish-test -> PASS，测试服 operation 成功且运行态 tag/health/frontend 均通过。
- GREEN: runtime-console-release-info -> PASS，运行控制台显示当前版本号和变更说明。
- GREEN: experience-consolidation -> PASS，新增前置经验可被 `docs/experience-index.md` 命中。

## 问题记录

- 维护控制台构建被 pnpm `ERR_PNPM_IGNORED_BUILDS` 阻断：`approve-builds --all` 空结果不代表 install 可通过；根因是实际 pnpm 11.7.0 与项目声明 pnpm 10.25.0 漂移，已改用声明版本完成构建。
- pnpm 10 install 曾因 pnpm 11 已生成 node_modules 报 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`；最终以完整 `scripts\build.ps1` 通过作为构建证据。
- PowerShell Bash heredoc 形态导致一次切换命令解析失败，已改用 UTF-8 原生文件 API 重试成功。
- build-release 预览本地门禁曾误把 `BackupServerHost` 构建参数判为备份服部署动作，已调整为按 action 分层校验。
- build-release v1 失败在后端 `20260709_mes_route_process_master_alignment.sql` release metadata 非 key-value 形态；已在后端主仓按严格 TDD 修复并提交，后续必须使用新的 releaseTag。
- build-release v2 生成本地包后失败于 Smart Release report-only 缺少显式 baseline manifest，operation 非 SUCCESS；v2 不得发布，后续使用新 releaseTag 且不启用 Smart Release report-only。

## 长时间过程复盘

待记录。

## 当前状态

- 状态：进行中。
- 已完成：创建任务目录、读取发布/经验/worktree/PowerShell 门禁、记录三仓目标 HEAD 与 dirty 基线；已创建短路径干净临时 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h`；维护控制台已从干净 worktree 构建并启动，48181 health=UP。
- 当前阻塞：无；`release-20260709-head-test-v3` 构建成功并已通过 manifest/sourceRepos/dirty=false/变更说明校验，下一步仅发布测试服。
## 发布完成记录（2026-07-09）

- 当前状态：Completed
- 发布范围：仅测试服务器；未执行正式服或备份服发布。
- 发布标签：`release-20260709-head-test-v3`。
- 构建来源：后端 `87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5`、前端 `d2022624d7c362400f0f8a976da59b828a06881f`，manifest 记录 `dirty=false`；维护控制台发布脚本最终提交 `65fb961439679fc329642ee4a0650c545ec3de9d`。
- 构建操作：`op-2026-07-09T013606785826300Z-45bc8231-d958-4e92-b0a9-00bf09c6010c`，本地发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-head-test-v3`，NAS 归档 `Backup/ReleasePackage/release-20260709-head-test-v3`。
- 测试服发布操作：`op-2026-07-09T023914856131600Z-09fcea10-25d3-496b-98bf-31a5f71225c1`，结果 `SUCCESS`。
- 真实运行态验证：测试服 `.env IMAGE_TAG`、后端/前端镜像 tag、容器运行状态、后端 health=UP、前端 HTTP 200、前端页面标题、`release-info.json`、运行控制台版本号和变更说明均已核对通过。
- 收尾要求：本节后续执行临时 worktree 清理预览、清理、验证和提交。
## 临时发布 worktree 清理记录（2026-07-09）

GREEN: task-closeout-cleanup-preview -> PASS, 已预览 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h` 下维护仓、后端仓、前端仓临时 worktree；确认三仓目标提交均已包含在各自主工作区 HEAD，`r260709h` 无剩余 Git worktree 注册。
GREEN: release-worktree-cleanup -> PASS, 停止精确匹配本次维护控制台 jar 的本地 Java 进程 PID 34472，删除残留的未注册目录 `m`、`f` 及空发布根目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h`；最终验证路径均已删除。
