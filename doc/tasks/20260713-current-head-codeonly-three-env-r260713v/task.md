# 20260713 当前 HEAD code-only 三环境发布 r260713v

## Task Goal

执行 IntRuoyi 不带数据的完整三环境发布闭环：使用维护仓、后端仓、前端仓在本轮开始时冻结的 `int_main` 已提交 HEAD，在本次专用干净临时发布 worktree 中构建并依次发布到测试服、正式服和备份服。最终同一 `releaseTag` 必须完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，并完成三环境真实运行态验证。

## User Constraints

- 发布输入只允许来自本轮开始时冻结的 `int_main` 已提交 HEAD；未提交改动、未跟踪文件和脏工作区内容不得进入发布包。
- 本轮为 `code-only` / 不带数据发布；构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`。
- 必须新建本次专用临时发布 worktree，在干净 worktree 中构建和发布。
- 不执行备份、恢复或回滚。
- 正式服和备份服发布已获本轮授权，确认口径为 `PROD`。
- 最终结果不得拼接不同 `releaseTag`；五个 operation 必须属于同一 `releaseTag` 且全部 `SUCCESS`。

## Milestones

- [x] 创建任务目录并写入初始 `task.md` 与 `execution-log.md`。
- [x] 读取并摘录发布前置经验门禁，记录 `GREEN: experience-preflight -> PASS`。
- [x] 冻结三仓当前 `int_main` HEAD，创建干净临时发布 worktree 并验证 commit/branch/dirty=false。
- [x] 将运行控制台配置指向本次临时发布 worktree，并验证本地 health=`UP`。
- [x] 执行 `build-release`，生成新的 `releaseTag`。
- [x] 校验 build operation、Manifest、`publishScope=code-only`、sourceRepos、数据目录缺失。
- [x] 执行 `publish-test` 并验证测试服运行态。
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
- 是否从根因和长期维护角度解决：是。构建、发布、验证任一门禁失败均冻结真实证据、沉淀可复用经验并修复根因后继续；未使用 mock、默认成功或手工标绿。
- 是否存在临时补丁或绕过：否。

## BDD Scenarios

- BDD: clean committed release input -> Given 三个主工作区可能存在未提交或未跟踪内容, When 本轮发布开始, Then 发布包只能来自本轮冻结的 `int_main` HEAD 干净 worktree。
- BDD: code-only publish scope -> Given 用户要求 code-only 且不带数据, When 执行 build-release, Then 必须使用 `SkipDatabaseSync` 与 `SkipMinioSync` 且 Manifest `publishScope=code-only`。
- BDD: three-environment release chain -> Given 测试服验证通过, When 执行发布闭环, Then 同一 releaseTag 必须完成 test、mark-tested、prod、backup 且三环境运行态一致。
- BDD: backup data disk verification -> Given 发布到备份服, When 验证完成标准, Then 必须证明 `/mnt/intruoyi-data` 挂载和发布路径正确。

## 经验门禁

### 发布输入与临时 worktree 门禁

- Trigger: 当前主工作区存在未提交或未跟踪内容，且发布要求只包含当前 `int_main` 已提交 HEAD。
- Preflight check: 在短路径 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v/m|b|f` 新建本次专用 release worktree；三仓检出本轮冻结 `int_main` HEAD；记录 branch、commit、dirty=false。
- Blocker: 任一 release worktree dirty、HEAD 与冻结提交不一致、路径不在标准 worktree 根、构建输入来自主工作区或旧 release worktree。
- Verification: `git worktree list --porcelain`、`git rev-parse HEAD`、`git status --porcelain --ignored=no`、最终 Git 注册与物理目录删除结果。
- Forbidden action: 不得从脏主工作区构建；不得复用旧 release worktree；不得删除无关并发任务 worktree。
- Evidence: `docs/release-build-preflight-lessons.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`。

### code-only build-release 与 Manifest 门禁

- Trigger: `build-release`、`code-only`、`SkipDatabaseSync`、`SkipMinioSync`。
- Preflight check: 构建前运行 migration policy gate；preview 必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、`TestServerHost=172.30.30.58`、`ProdServerHost=172.30.30.57`、`BackupServerHost=172.30.30.59`、本轮 BackendRepoRoot 与 FrontendRepoRoot。
- Blocker: build operation 非 `SUCCESS`、Manifest v1 缺失、`publishScope` 非 `code-only`、sourceRepos commit 不等于冻结 HEAD、dirty=true、包含 Website/展厅或数据目录、required SQL/data SQL 门禁失败。
- Verification: 记录 operationId、manifest 路径、`publishScope`、sourceRepos、artifact hash、数据目录扫描、版本号和变更说明。
- Forbidden action: 不得用 legacy `release-manifest.json`、Docker 缓存、HTTP 200 或旧成功包替代 Manifest v1；不得把 `SkipDatabaseSync` 当作跳过 schema/required SQL/迁移门禁。
- Evidence: `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/release-backup-restore.md`。

### 测试服发布与 mark-tested 门禁

- Trigger: `publish-test`、测试服运行态验证、`mark-tested`。
- Preflight check: publish-test preview 必须证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`；真实写入前后检查发布锁和版本漂移；测试服验证通过后才允许 `mark-tested`；mark-tested 不得带 `targetEnvironment`，必须提供真实 `selectedRecoverySetCandidateId`。
- Blocker: preview 目标不是测试服、存在活动发布或 RUNNING 锁、operation 非 SUCCESS、`.env`/compose/实际镜像/release-info/lock 指向不同 releaseTag、测试服未验收即 mark-tested、缺 recovery set 候选。
- Verification: 测试服 `.env IMAGE_TAG`、backend/frontend image tag、backend health=UP、frontend HTTP=200、PDF worker HTTP=200、release-info tag/commit、operation lock、migration target failure count；mark-tested operation=SUCCESS。
- Forbidden action: 不得用 publish-test 成功直接代替 mark-tested；不得手工标绿 tested 状态；不得拼接不同 releaseTag。
- Evidence: `docs/release-agent-checklist.md`、`docs/test-release-preflight.md`。

### 正式服与备份服 promotion 门禁

- Trigger: `promote-prod`、`promote-backup`、正式服和备份服运行态验证。
- Preflight check: `promote-prod` 必须带 `ConfirmText=PROD` 与 `RequireTested`；`promote-backup` 必须显式使用 `ServerHost=172.30.30.59`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`、`RemoteDataRoot=/mnt/intruoyi-data/runtime-data`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteDataDiskDevice=/dev/mapper/cl-home`、`RemoteMinioContainer=intruoyi-minio`。
- Blocker: 任一 promote operation 非 SUCCESS、正式服缺 `PROD` 或 `RequireTested`、备份服未显式使用 `/mnt/intruoyi-data`、目标 host/目录错误、运行态验证失败。
- Verification: 正式服和备份服分别验证 `.env IMAGE_TAG`、backend/frontend image tag、backend health=UP、frontend HTTP=200、PDF worker HTTP=200、release-info；备份服额外验证 `/mnt/intruoyi-data` 挂载和发布路径。
- Forbidden action: 不得把测试服结果替代正式/备份结果；不得回退到根分区、Docker 默认路径或正式服参数；不得跳过备份服挂载证明。
- Evidence: `docs/release-agent-checklist.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/server-access.md`。

### PowerShell / SSH / 日志脱敏门禁

- Trigger: Windows PowerShell、SSH、Docker、MySQL、HTTP、release-info、中文发布说明、日志留存。
- Preflight check: 设置 UTF-8；不使用 `&&`；多行远端脚本用 UTF-8 bytes + LF；release-info 用 JSON parser 或 CRLF-safe 解析；preview 参数解析兼容 switch flag；保存/提交日志前扫描并脱敏密码、token、私钥、连接串和 `mysql -p***`。
- Blocker: 中文/JSON 证据不可读、命令依赖 PowerShell 默认编码或 `&&`、远端脚本 CRLF 污染、待保留日志含明文凭据、脱敏规则误伤 releaseTag/host/repo 名导致证据失真。
- Verification: 记录退出码、HTTP status、health JSON、结构化 preview gate、远端关键输出、secret scan 命中数。
- Forbidden action: 不得提交 secret-bearing 原始日志；不得用 PowerShell 默认乱码输出作为唯一证据；不得把本地承载脚本错误误判为服务器失败。
- Evidence: `D:/ProjectPackage/Int/IntRuoyi/docs/powershell-memory.md`、`docs/powershell-preflight-lessons.md`、`docs/release-build-preflight-lessons.md`。

### closeout 与提交隔离门禁

- Trigger: 三环境发布和验证完成后恢复运行控制台、清理临时 worktree、task-closeout、提交任务记录。
- Preflight check: 先将任务状态写为 `ready_for_closeout`；恢复 `runtime-control.local.yaml` 主路径并验证 48181 health=UP；task-closeout preview/apply 通过；检查本轮 release worktree Git 注册与物理目录均不存在。
- Blocker: 运行控制台仍指向待删 worktree、worktree dirty 或存在未合并提交、物理根目录/state dir 残留且未完成固定路径和进程占用检查、task-closeout blocked、提交范围混入无关改动。
- Verification: `git worktree list`、物理目录检查、runtime-control health、task-closeout 输出、git status/diff/cached 范围检查、最终提交。
- Forbidden action: 不得提前写 `completed`；不得删除无关 worktree；不得把 Git 注册删除等同于物理目录清理完成；不得整文件提交混入其他任务 hunk。
- Evidence: `docs/release-build-preflight-lessons.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`、`C:/Users/BJB110/.codex/skills/task-closeout-cleanup/references/closeout-rules.md`。

## Current Status

completed - `release-20260713-intmain-codeonly-three-env-r260713v-r1` 已完成同一 releaseTag 的 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；五个 operation 均为 SUCCESS，测试服、正式服和备份服运行态验证通过。运行控制台已恢复主路径，本轮临时 release worktree Git 注册、物理目录和 state 目录均已删除，task-closeout preview/apply 已通过且核心任务记录保留。

## Frozen Release Input

- Release worktree root: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v`
- External state dir: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v-state`
- Maintenance worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v/m`
- Backend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v/b`
- Frontend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v/f`
- Maintenance target HEAD: `872a17bc5d2f01cf3b6d4bc4b53f3605ffc9309a`
- Backend target HEAD: `a69271e228c7738cd0ade0e12f9b7f8a85aec205`
- Frontend target HEAD: `69df78f24279d4f144fa252230f6571202409bf7`

## Release Evidence

- Release tag: `release-20260713-intmain-codeonly-three-env-r260713v-r1`
- Build operation: `op-2026-07-13T143350577788200Z-3d861300-83a9-4b8a-a453-96b7ae54e225` = `SUCCESS`
- Publish-test operation: `op-2026-07-13T145223142838Z-f31e7309-5106-4c25-ac53-5ddbf4efefa3` = `SUCCESS`
- Mark-tested operation: `op-2026-07-13T150911502243700Z-029f98c3-29d6-4104-9f34-d36bfe281ea1` = `SUCCESS`
- Promote-prod operation: `op-2026-07-13T151108922995700Z-109cd33a-e66b-4297-b73d-9ea4d6f2f488` = `SUCCESS`
- Promote-backup operation: `op-2026-07-13T152649835481600Z-c8a04317-1b9d-4ed7-8b43-61002803e87c` = `SUCCESS`
- Manifest: `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-intmain-codeonly-three-env-r260713v-r1/manifest.json`; `publishScope=code-only`; backend/frontend sourceRepos dirty=false and match frozen HEAD; 295 artifact hashes verified; forbidden data dirs absent.

## Runtime Verification Summary

- Test `172.30.30.58`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info source commits、release lock 和 target migration failure count 均通过。
- Prod `172.30.30.57`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info source commits、release lock 和 target migration failure count 均通过。
- Backup `172.30.30.59`: `.env IMAGE_TAG`、backend/frontend image、backend health、frontend HTTP、PDF worker HTTP、release-info source commits、release lock、target migration failure count、`/mnt/intruoyi-data` 挂载、release dir 和 data root 均通过。

## Issues Recorded

- backup-verification-python3-absent: 首次备份服验收脚本调用远端 `python3` 失败，未改变服务器状态；已改用纯 shell/grep 解析 `release-info.json` 并复验通过。
- release-worktree-physical-residual: `git worktree remove` 清掉注册后，维护/前端物理目录存在残留；确认无 Git 注册、无进程引用且路径位于 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v` 后，使用固定路径删除并复核通过。

## Closeout Evidence

- Runtime-control restore: `http://127.0.0.1:48181/actuator/health=UP`，进程命令行指向主工作区 `D:/ProjectPackage/Int/IntRuoyiMaintance/backend/target/runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- Release worktree cleanup: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v` exists=false；`D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v-state` exists=false；维护/后端/前端 Git worktree registrations absent。
- task-closeout: preview/apply `blocked=<none>`、`warnings=<none>`；保留 `task.md`、`execution-log.md`、`verification-report.md`，删除临时 JSON evidence 文件。
