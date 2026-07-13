# 20260713 当前 HEAD code-only 三环境重新发布

## Task Goal

主程序已更新，按完整三环境发布口径重新执行 IntRuoyi 不带数据发布闭环：使用维护仓、后端仓、前端仓在本轮开始时冻结的 `int_main` 已提交 HEAD，在本次专用干净临时发布 worktree 中构建并依次发布到测试服、正式服和备份服。最终同一 `releaseTag` 必须完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，并完成三环境真实运行态验证。

## User Constraints

- 发布输入只允许来自本轮开始时冻结的 `int_main` 已提交 HEAD；未提交改动、未跟踪文件和脏工作区内容不得进入发布包。
- 本轮为 `code-only` / 不带数据发布；构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`。
- 必须新建本次专用临时发布 worktree，不复用上一轮 `r260713g` 或旧 `r260713i`。
- 不执行备份、恢复或回滚。
- 用户要求“重新发布一次”，按上一轮完整三环境发布口径执行；正式服和备份服 promotion 使用 `ConfirmText=PROD` 与 `RequireTested`，备份服显式使用 `/mnt/intruoyi-data` 参数。
- 程序持续更新时不追逐冻结后的新 HEAD；本轮只构建发布开始时 `r260713j` worktree 记录的提交。
- 最终结果不得拼接不同 `releaseTag`；五个 operation 必须属于同一 `releaseTag` 且全部 `SUCCESS`。

## Milestones

- [x] 创建任务目录并记录初始任务文档、执行日志。
- [x] 读取并摘录发布前置经验门禁，记录 `GREEN: experience-preflight -> PASS`。
- [x] 重新冻结三仓当前 `int_main` HEAD，创建干净临时发布 worktree 并验证 commit/branch/dirty=false。
- [x] 将运行控制台配置指向本次临时发布 worktree，并验证本地 health=`UP`。
- [x] 执行 `build-release`，生成新的 `releaseTag`。
- [x] 校验 build operation、Manifest、`publishScope=code-only`、sourceRepos、数据目录缺失。
- [x] 执行 `publish-test`。
- [x] 验证测试服 `.env IMAGE_TAG`、镜像 tag、health、frontend HTTP、PDF worker HTTP。
- [x] 执行 `mark-tested`。
- [x] 执行 `promote-prod`，使用 `ConfirmText=PROD` 与 `RequireTested`，并验证正式服运行态。
- [x] 执行 `promote-backup` 到 `172.30.30.59`，显式使用 `/mnt/intruoyi-data` 参数，并验证备份服运行态和数据盘挂载。
- [x] 恢复 `runtime-control.local.yaml` 主路径，验证运行控制台 health=`UP`。
- [x] 删除本次临时发布 worktree，更新任务文档、执行日志、请求命令日志和必要经验沉淀。
- [x] 执行 task-closeout preview/apply，并提交仅本任务直接产生的任务记录、请求日志和必要经验文件。

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
- 是否从根因和长期维护角度解决：是。构建/发布/验证任一门禁失败均冻结证据、沉淀经验并修复根因后继续；未使用 mock、默认成功或手工标绿。
- 是否存在临时补丁或绕过：否。

## 经验门禁

### 干净发布输入与 worktree 门禁

- Trigger: 当前主工作区存在未提交或未跟踪内容，且发布要求仅包含已提交 HEAD。
- Preflight check: 使用短路径 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j/m|b|f` 新建本次专用临时发布 worktree；三仓检出冻结 `int_main` HEAD；记录 branch、commit、dirty=false。
- Blocker: 任一 release worktree dirty、HEAD 与冻结提交不一致、路径不在标准根、checkout 部分失败、构建输入来自主工作区或旧 worktree。
- Verification: `git worktree list --porcelain`、`git rev-parse HEAD`、`git status --porcelain --ignored=no`、最终 worktree 删除结果。
- Forbidden action: 不得复用旧 release worktree；不得从脏主工作区构建；不得删除无关并发任务 worktree。
- Evidence: `D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`、`docs/release-build-preflight-lessons.md`。

### code-only 构建与 Manifest 门禁

- Trigger: `code-only`、`SkipDatabaseSync`、`SkipMinioSync` 发布。
- Preflight check: build preview 必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 Host、BackendRepoRoot、FrontendRepoRoot；构建前运行 migration policy gate；构建后读取发布包根目录 Manifest v1 `manifest.json`。
- Blocker: Manifest 缺失、`publishScope` 非 `code-only`、sourceRepos commit 与冻结 HEAD 不一致、dirty=true、包含 Website sourceRepo/website 目录、包含数据目录、required SQL metadata 门禁失败。
- Verification: 记录 build operation、manifest 路径、sourceRepos、publishScope、目录扫描、artifact 校验、版本号和变更说明。
- Forbidden action: 不得用 legacy `release-manifest.json` 替代 Manifest v1；不得把 `SkipDatabaseSync` 理解为跳过 schema/required SQL/迁移门禁；不得把本地缓存或 Docker image 当发布包。
- Evidence: `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`。

### 三环境发布门禁

- Trigger: `publish-test`、`mark-tested`、`promote-prod`、`promote-backup`。
- Preflight check: `publish-test` 必须指向 `172.30.30.58`；测试服运行态验证通过后才允许 `mark-tested`；`mark-tested` 不得携带 `targetEnvironment` 且必须提供真实 `selectedRecoverySetCandidateId`；`promote-prod` 必须带 `ConfirmText=PROD` 与 `RequireTested`；`promote-backup` 必须显式使用 `ServerHost=172.30.30.59`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`、`RemoteDataRoot=/mnt/intruoyi-data/runtime-data`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteDataDiskDevice=/dev/mapper/cl-home`、`RemoteMinioContainer=intruoyi-minio`。
- Blocker: 任一 operation 非 SUCCESS、目标 host/目录错误、未 tested 即 promote、正式/备份缺 `PROD` 或 `RequireTested`、备份服未显式使用 `/mnt/intruoyi-data`、运行态验证失败。
- Verification: 三环境分别验证 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP、`release-info.json`；备份服额外验证 `/mnt/intruoyi-data` 挂载和发布路径。
- Forbidden action: 不得把测试服结果代替正式/备份结果；不得回退到根分区或 Docker 默认路径；不得跳过备份服数据盘挂载证明。
- Evidence: `docs/release-agent-checklist.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/server-access.md`。

### PowerShell / SSH / 日志脱敏门禁

- Trigger: Windows PowerShell、SSH、Docker、MySQL、HTTP、release-info、中文发布说明和日志保留。
- Preflight check: 设置 UTF-8 输入输出；不用 `&&`；Bash heredoc 不直接贴到 PowerShell；多层 SSH/bash 优先标准输入、Base64 或 UTF-8 脚本；以 `$LASTEXITCODE`/ExitCode 与结构化结果为准；保存/提交日志前扫描并脱敏密码、token、私钥、连接串和 `mysql -p...`。
- Blocker: 中文编码不可读、命令输出无法证明真实状态、PowerShell 字符串污染、待保留日志含明文凭据。
- Verification: 记录退出码、HTTP status、health JSON、远端关键输出、脱敏扫描结果。
- Forbidden action: 不得用默认 PowerShell 中文渲染作为唯一版本说明证据；不得提交 secret-bearing 原始日志。
- Evidence: `D:/ProjectPackage/Int/IntRuoyi/docs/powershell-memory.md`、`docs/powershell-preflight-lessons.md`、`docs/release-build-preflight-lessons.md`。

### closeout 门禁

- Trigger: 三环境发布和验证完成后清理临时 worktree、恢复运行控制台配置并提交记录。
- Preflight check: 先将状态写为 `ready_for_closeout`，恢复 `runtime-control.local.yaml` 主路径并验证 48181 health=`UP`；运行 task-closeout preview/apply；确认临时 worktree Git 注册和物理目录均不存在。
- Blocker: 运行控制台仍指向待删 worktree、worktree dirty 或未合并提交、task-closeout blocked、目标目录仍存在且无法证明安全清理。
- Verification: `git worktree list`、物理目录检查、runtime-control health、task-closeout 输出、最终提交。
- Forbidden action: 不得提前写 `completed`；不得删除无关 worktree；不得把 Git 注册删除等同于物理目录清理完成。
- Evidence: `docs/release-build-preflight-lessons.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`。

## Current Status

completed - `release-20260713-intmain-codeonly-three-env-r260713j-r1` 已完成完整三环境发布闭环并通过运行态验证；运行控制台已恢复主路径，本次临时 release worktree Git 注册、物理根目录和 state 目录均已删除；task-closeout preview/apply 已通过且核心任务记录保留。

## Frozen Release Input

- Release worktree root: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j`
- External state dir: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j-state`
- Maintenance worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j/m`
- Backend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j/b`
- Frontend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j/f`
- Maintenance target HEAD: `1535b827e6089549c978b670b8c8349e5362c63a`
- Backend target HEAD: `dd986dc1a03c36d279f20ee93822a666aaf628ff`
- Frontend target HEAD: `a86c8da404fcd0fdd712375347494a1f711b925b`
- Later main-workspace HEAD drift observed at closeout is out of scope by user rule; this release remains bound to the frozen `r260713j` input.

## Release Chain Evidence

- Release tag: `release-20260713-intmain-codeonly-three-env-r260713j-r1`
- Build operation: `op-2026-07-13T074159226342200Z-a71c4f54-dbde-40dc-b946-b53d9d6bab39` = `SUCCESS`
- Publish-test operation: `op-2026-07-13T080624260438700Z-7ca59077-0f96-473a-bd00-643de19d9fa7` = `SUCCESS`
- Mark-tested operation: `op-2026-07-13T082842115595300Z-4a697216-cf00-4a78-a510-24ee79f105b9` = `SUCCESS`
- Promote-prod operation: `op-2026-07-13T083054217937200Z-3408b81b-491c-44c7-9557-75c859340e60` = `SUCCESS`
- Promote-backup operation: `op-2026-07-13T092109387694Z-f88175d9-76a4-4689-9279-8528c32400a3` = `SUCCESS`
- Manifest: `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-intmain-codeonly-three-env-r260713j-r1/manifest.json`; `publishScope=code-only`；sourceRepos dirty=false；发布包不含数据目录；artifact hash 校验通过。

## Runtime Verification Summary

- Test `172.30.30.58`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info 和 release lock 均匹配 `release-20260713-intmain-codeonly-three-env-r260713j-r1`。
- Prod `172.30.30.57`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info 和 release lock 均匹配 `release-20260713-intmain-codeonly-three-env-r260713j-r1`。
- Backup `172.30.30.59`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info、release lock、`/mnt/intruoyi-data` 挂载、release dir 和 data root 均验证通过。
- Runtime console: `http://127.0.0.1:48181/actuator/health` = `UP`，进程命令行指向主工作区 `D:/ProjectPackage/Int/IntRuoyiMaintance/backend/target/runtime-control-maintenance-2026.06-SNAPSHOT.jar`；页面显示本轮版本号和变更说明。

## Issues Recorded

- stale-release-worktree: 旧 release worktree 落后于本轮冻结 HEAD，未复用并新建 `r260713j`。
- duplicate-task-bootstrap: 恢复执行时短暂创建重复任务目录，已删除并沿用当前任务目录。
- publish-test-log-tail-secret: operation log 中出现 `mysql -p...` 明文形态，已脱敏并通过 secret scan。
- release-info-crlf-parser: 初始解析未删除 CR，改为 CRLF-safe compact/JSON parser 后复验通过。
- console-error-string-parser: Playwright console 统计文本含 `Errors: 0` 被误判，改为结构化/精确模式后通过。
- powershell-pid-variable-reuse: `$PID` 自动变量误用，改为 `$listenPid` 并记录到 PowerShell 前置经验。
- residual-release-worktree-root: Git worktree 注册已删除但 `r260713j/m` 与 `r260713j/f` 物理目录残留，完成 fixed-path、unregistered、not-a-git-repo 校验后删除，最终复核 PASS。
