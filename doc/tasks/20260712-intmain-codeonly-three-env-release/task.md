# 20260712 IntRuoyi int_main code-only 三环境发布闭环

## Task Goal

使用维护仓、后端仓、前端仓当前 `int_main` 已提交 HEAD，在本次专用干净临时发布 worktree 中执行不带数据的完整发布闭环：`build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`。最终同一 `releaseTag` 必须在测试服、正式服、备份服全部发布成功并完成真实运行态验证。

## User Constraints

- 发布输入只允许来自当前 `int_main` 已提交 HEAD；未提交改动、未跟踪文件和脏工作区内容不得进入发布包。
- 本轮为 `code-only` / 不带数据发布；构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`。
- 必须新建本次专用临时发布 worktree，不复用旧发布 worktree。
- 不执行备份、恢复或回滚。
- 正式服和备份服发布已获授权，确认口径为 `PROD`。
- 最终结果不得拼接不同 `releaseTag`；五个 operation 必须属于同一 `releaseTag` 且全部 `SUCCESS`。

## Milestones

- [x] 创建任务目录并记录初始任务文档、执行日志。
- [x] 读取并摘录发布前置经验门禁，记录 `GREEN: experience-preflight -> PASS`。
- [x] 冻结三仓当前 `int_main` HEAD，创建干净临时发布 worktree 并验证 commit/branch/dirty=false。
- [x] 将运行控制台配置指向本次临时发布 worktree，并验证本地 health=`UP`。
- [x] 执行 `build-release`，生成新的 `releaseTag`。
- [x] 校验 build operation、Manifest、`publishScope=code-only`、sourceRepos、数据目录缺失。
- [x] 执行 `publish-test` 并验证测试服 `.env IMAGE_TAG`、镜像 tag、health、frontend HTTP、PDF worker HTTP。
- [x] 执行 `mark-tested`。
- [x] 执行 `promote-prod`，使用 `ConfirmText=PROD` 与 `RequireTested`，并验证正式服运行态。
- [x] 执行 `promote-backup` 到 `172.30.30.59`，显式使用 `/mnt/intruoyi-data` 参数，并验证备份服运行态和数据盘挂载。
- [x] 恢复 `runtime-control.local.yaml` 主路径，验证运行控制台 health=`UP`。
- [x] 删除本次临时发布 worktree，更新任务文档、执行日志、请求命令日志和必要经验沉淀。
- [x] 提交仅本任务直接产生的任务记录、请求日志和必要经验文件。

## Expected Verification

- 同一 `releaseTag` 完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`。
- 五个 operation 均为 `SUCCESS`。
- 测试服、正式服、备份服均验证 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=`UP`、frontend HTTP 200、PDF worker HTTP 200。
- 备份服额外验证 `/mnt/intruoyi-data` 挂载正确且发布路径正确。
- 发布包 Manifest 存在，`publishScope=code-only`，sourceRepos 均为冻结提交且 `dirty=false`，发布包不包含数据目录。
- 本次临时发布 worktree 已删除，运行控制台配置已恢复主路径且 health=`UP`。
- 任务文档标记完成，执行日志记录全部证据，提交范围隔离。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。构建/发布/验证任一门禁失败必须冻结证据、沉淀经验并修复根因后继续，不允许 mock 或手工标绿。
- 是否存在临时补丁或绕过：否。

## 经验门禁

### 任务与发布范围门禁

- Trigger: 完整三环境发布、`build-release`、`publish-test`、`mark-tested`、`promote-prod`、`promote-backup`。
- Preflight check: 任务目录必须存在；正式/备份授权必须明确，本次授权口径为 `PROD`；执行顺序固定为 `build-release -> publish-test -> 测试服验证 -> mark-tested -> promote-prod -> 正式服验证 -> promote-backup -> 备份服验证`。
- Blocker: 未写任务文档、缺 `experience-preflight`、正式/备份缺授权、任一步 operation 不明确或非 `SUCCESS`。
- Verification: `execution-log.md` 记录五个 operation、releaseTag、目标环境和运行态验证。
- Forbidden action: 不得 mock 成功、手工标绿、静默跳过、拼接不同 releaseTag。
- Evidence: `docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`。

### 干净发布输入与 worktree 门禁

- Trigger: 当前主工作区存在未提交或未跟踪内容，且发布要求仅包含已提交 HEAD。
- Preflight check: 使用短路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712c\m|b|f` 新建本次专用临时发布 worktree；三仓检出冻结 `int_main` HEAD；记录 branch、commit、dirty=false。
- Blocker: 任一 release worktree dirty、HEAD 与冻结提交不一致、路径不在标准根、checkout 部分失败、构建输入来自主工作区或旧 worktree。
- Verification: `git worktree list --porcelain`、`git rev-parse HEAD`、`git status --porcelain`、最终 worktree 删除结果。
- Forbidden action: 不得复用旧 release worktree；不得从脏主工作区构建；不得删除无关并发任务 worktree。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`docs/test-release-preflight.md`。

### code-only 构建与 Manifest 门禁

- Trigger: `code-only`、`SkipDatabaseSync`、`SkipMinioSync` 发布。
- Preflight check: build preview 必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；三环境闭环必须同时包含 Test/Prod/Backup host；构建前运行 migration policy gate；构建后读取发布包根目录 Manifest v1 `manifest.json`。
- Blocker: Manifest 缺失、`publishScope` 非 `code-only`、sourceRepos commit 与冻结 HEAD 不一致、dirty=true、包含 Website sourceRepo/website 目录、包含数据目录、required SQL metadata 门禁失败。
- Verification: 记录 build operation、manifest 路径、sourceRepos、publishScope、目录扫描、artifact 校验、版本号和变更说明。
- Forbidden action: 不得用 legacy `release-manifest.json` 替代 Manifest v1；不得把 `SkipDatabaseSync` 理解为跳过 schema/required SQL/迁移门禁；不得把本地缓存或 Docker image 当发布包。
- Evidence: `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`。

### 测试服发布门禁

- Trigger: `publish-test` 到 `172.30.30.58`。
- Preflight check: preview 必须结构化证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`；真实写入前检查运行控制台 health 和发布锁；发布后验证 `.env IMAGE_TAG`、compose/实际镜像、backend health、frontend HTTP、PDF worker HTTP、`release-info.json`。
- Blocker: operation 非 SUCCESS、目标不是测试服、活动发布锁冲突、`.env`/镜像/release-info 不一致、health/frontend/PDF worker 任一失败。
- Verification: 记录 publish-test operation、远端 `.env`、docker inspect、HTTP 状态和 release-info。
- Forbidden action: 不得因 preview 中出现 `BackupServerHost` 参数元数据就误判目标，也不得用 HTTP 200 单项替代完整运行态。
- Evidence: `docs/test-release-preflight.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`。

### mark-tested / promote-prod / promote-backup 门禁

- Trigger: 测试服验证通过后进入正式和备份推广。
- Preflight check: `mark-tested` 只能在测试服运行态验证通过后执行；`promote-prod` 必须带 `ConfirmText=PROD` 与 `RequireTested`；`promote-backup` 必须显式使用 `ServerHost=172.30.30.59`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`、`RemoteDataRoot=/mnt/intruoyi-data/runtime-data`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteDataDiskDevice=/dev/mapper/cl-home`、`RemoteMinioContainer=intruoyi-minio`。
- Blocker: 未 tested 即 promote、正式服未带 `PROD` 或 `RequireTested`、备份服未显式使用 `/mnt/intruoyi-data`、operation 非 SUCCESS、正式/备份运行态验证失败。
- Verification: 正式服和备份服分别验证 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP；备份服额外验证 `/mnt/intruoyi-data` 挂载和发布路径。
- Forbidden action: 不得把测试服结果代替正式/备份结果；不得回退到根分区或 Docker 默认路径；不得跳过备份服数据盘挂载证明。
- Evidence: `docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`。

### PowerShell / SSH / 日志脱敏门禁

- Trigger: Windows PowerShell、SSH、Docker、MySQL、HTTP、release-info、中文发布说明和日志保留。
- Preflight check: 设置 UTF-8 输入输出；不用 `&&`；Bash heredoc 不直接贴到 PowerShell；多层 SSH/bash 优先标准输入或 UTF-8 脚本；以 `$LASTEXITCODE`/ExitCode 与结构化结果为准；保存/提交日志前扫描并脱敏密码、token、私钥、连接串和 `mysql -p...`。
- Blocker: 中文编码不可读、命令输出无法证明真实状态、PowerShell 字符串污染、待保留日志含明文凭据。
- Verification: 记录退出码、HTTP status、health JSON、远端关键输出、脱敏扫描结果。
- Forbidden action: 不得用默认 PowerShell 中文渲染作为唯一版本说明证据；不得提交 secret-bearing 原始日志。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`docs/powershell-preflight-lessons.md`、`docs/release-build-preflight-lessons.md`。

### closeout 门禁

- Trigger: 三环境发布和验证完成后清理临时 worktree、恢复运行控制台配置并提交记录。
- Preflight check: 先将状态写为 `ready_for_closeout`，恢复 `runtime-control.local.yaml` 主路径并验证 48181 health=`UP`；运行 task-closeout preview/apply；确认临时 worktree Git 注册和物理目录均不存在。
- Blocker: 运行控制台仍指向待删 worktree、worktree dirty 或未合并提交、task-closeout blocked、目标目录仍存在且无法证明安全清理。
- Verification: `git worktree list`、物理目录检查、runtime-control health、task-closeout 输出、最终提交。
- Forbidden action: 不得提前写 `completed`；不得删除无关 worktree；不得把 Git 注册删除等同于物理目录清理完成。
- Evidence: `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。

## Current Status

completed - 同一 releaseTag `release-20260713-intmain-codeonly-three-env-r260713g-r1` 已完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，五个 operation 均为 `SUCCESS`；测试服、正式服、备份服真实运行态验证均通过，运行控制台页面已显示三环境版本号和变更说明；本次临时 worktree `r260713g` 与外部 state 目录已删除，48181 已恢复主路径并 health=`UP`；task-closeout preview/apply 均无 blocked、warnings 或 delete 项；本任务直接产生的任务记录、请求日志和必要经验文件已进入隔离提交流程。

## Frozen Release Input

- Release worktree root: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g` (deleted after verification)
- External state dir: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state` (deleted after verification)
- Maintenance worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g\m`
- Backend worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g\b`
- Frontend worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g\f`
- Maintenance HEAD: `367786f125c3075aa2507854ee5d91b4479d3c69`
- Backend HEAD: `738cfaeb04cc1b123de42283a01560b63fdac2b2`
- Frontend HEAD: `c1326e7b427ff1036bc49fcb401d6a365655099e`
- Main workspaces dirty: maintenance=true, backend=true, frontend=true; release worktrees were detached HEAD and clean before build, so build input was isolated from uncommitted and untracked main-workspace content.

## Current Release Package

- Current valid releaseTag: `release-20260713-intmain-codeonly-three-env-r260713g-r1`.
- Operations: build-release `op-2026-07-13T042641075294500Z-a45c6318-f096-4085-9715-38795a98fa74`; publish-test `op-2026-07-13T043904247039400Z-58e11f61-27d7-4475-897f-726cf69c0367`; mark-tested `op-2026-07-13T045527979959Z-8ae49468-8a07-46ca-a512-aab65f41f62d`; promote-prod `op-2026-07-13T045743664719Z-4c45114b-fa52-488d-b32a-3e39e4e00244`; promote-backup `op-2026-07-13T051411658807100Z-2bb859ba-86d9-492b-8b32-3e9980ebe07c`.
- Superseded releaseTag: `release-20260713-intmain-codeonly-three-env-r260713f-r1` completed three-environment release successfully but is no longer the final acceptance release for this continuation because backend/frontend `int_main` HEAD had moved before `r260713g` was frozen.
- Superseded releaseTag: pending/failed `r260713e` attempts are invalid for this task because the current backend/frontend `int_main` HEAD moved to backend `4d7baa09fa7642dfd5017239622fecfe83c2796e` and frontend `08c269172045526e2ed730b4c932d93dfab94e4a` before this continuation; `r260713e` has been cleaned.
- Superseded releaseTag: `release-20260713-intmain-codeonly-three-env-r260713d-r1` completed build-release and publish-test, but is invalid for this task because it used backend `fdd93ec98cfe8e020982ec59e1e03da633cfeef7` and frontend `1b359734068d845b690c8f0c45e72f9bc040ce0c`, not the newly frozen current `int_main` HEAD.
- Prior failed releaseTag: `release-20260713-intmain-codeonly-three-env-r260713c-r2` failed publish-test required SQL and remains failure evidence only.

## Current Continuation Freeze Plan

- New release worktree root: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g`.
- Maintenance target HEAD: `367786f125c3075aa2507854ee5d91b4479d3c69`.
- Backend target HEAD: `738cfaeb04cc1b123de42283a01560b63fdac2b2`.
- Frontend target HEAD: `c1326e7b427ff1036bc49fcb401d6a365655099e`.
- Main workspaces dirty: maintenance=true, backend=true, frontend=true; build input must therefore come only from the new detached clean release worktrees.

## Cleanup Keep

- `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md`
