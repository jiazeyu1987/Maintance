# 当前 HEAD 仅测试服发布

## Task Goal

基于当前分支最新已提交代码构建维护控制台与测试发布包，并仅发布到测试服务器。构建产物必须只包含发布开始时记录的当前分支 HEAD 已提交内容，未提交改动不得进入构建产物；发布后完成测试服真实运行态、前端页面、运行控制台版本号和变更说明验证。

## Milestones

- [x] 记录发布起点：当前分支、目标提交号、工作区脏状态、构建目录和临时 worktree 路径。
- [x] 读取发布、服务器、worktree、PowerShell 和测试服发布前置经验，并摘取本任务适用门禁。
- [x] 从当前分支 HEAD 创建本次专用干净临时发布 worktree，并证明构建只基于该 HEAD。
- [x] 在临时 worktree 中构建维护控制台和测试发布包。
- [x] 检查发布包、manifest、版本号和变更说明，确认与目标提交一致。
- [x] 仅执行测试服发布，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- [x] 验证测试服真实运行态：镜像 tag、容器状态、健康检查、前端 HTTP 状态、前端页面、运行控制台版本号和变更说明。
- [x] 记录全过程问题、阶段复盘、耗时点和处理结果。
- [x] 测试服发布成功后沉淀前置经验。
- [x] 将任务状态置为 `ready_for_closeout`，执行 task-closeout-cleanup preview/apply，清理本任务临时发布 worktree 后标记完成。

## Expected Verification

- `git status --short --branch`、`git branch --show-current`、`git rev-parse HEAD` 记录发布起点。
- 临时 worktree `git status --short --branch` 为干净，`git rev-parse HEAD` 等于目标提交。
- 构建命令成功，发布包和 manifest 存在。
- manifest / release-info / 版本号 / 变更说明能证明构建来源为目标提交。
- `publish-test` 成功且同一 releaseTag 未进入正式服或备份服发布动作。
- 远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP 200、前端页面、运行控制台版本号和变更说明全部通过。
- 问题记录完整，经验沉淀完成，task-closeout-cleanup preview/apply 通过。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，本次按现有发布文档和已沉淀前置经验执行，发布输入固定为发布起点 HEAD，不追逐后续提交。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

### 仅测试服发布范围锁定

- Trigger: 仅测试服发布、`publish-test`、测试服运行态验收、运行控制台版本号与变更说明验证。
- Preflight check: 本轮只允许 `build-release -> publish-test -> 测试服真实运行态验证`，目标测试服固定 `172.30.30.58`、远端运行目录 `/opt/intruoyi/runtime`；构建开始后固定使用发布起点 worktree 内记录的目标提交，不追逐后续提交。
- Blocker: preview/日志/操作参数出现正式服或备份服实际发布动作、`mark-tested`、`promote-prod`、`promote-backup`，或无法证明 releaseTag 与目标测试服一致。
- Verification: 记录 releaseTag、build operation、publish-test operation、preview 字段、远端 `.env IMAGE_TAG`、实际镜像、容器、health、HTTP、release-info 和运行控制台页面证据。
- Forbidden action: 不得拼接不同 releaseTag 的构建和发布结果，不得因“仅测试服”而跳过测试服运行态或版本说明验收。
- Evidence: `docs/test-release-preflight.md`、`docs/release-agent-checklist.md`、`E:\IntRuoyi\docs\release-backup-restore.md`。

### 冻结 HEAD 与干净 release worktree

- Trigger: 当前分支 HEAD 发布、主工作区存在未提交改动、构建发布包或运行控制台 build-release。
- Preflight check: 分别记录维护仓、主程序后端/前端仓当前分支、HEAD、dirty 状态；创建短路径本轮专用 release worktree；构建前后确认 worktree `git status --porcelain --ignored=no` 为空。
- Blocker: release worktree dirty、worktree HEAD 与冻结提交不一致、运行控制台仍指向主工作区或旧 worktree、state-dir/log/cache 污染 release worktree、构建产物 manifest `sourceRepos[*].dirty=true`。
- Verification: `git status --short --branch`、`git rev-parse HEAD`、`git worktree list --porcelain`、manifest `sourceRepos` commit/dirty 校验。
- Forbidden action: 不得从脏主工作区构建，不得复用长期旧 worktree，不得把主工作区未提交修复混入发布包。
- Evidence: `docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\worktree-restrictions.md`。

### 构建、manifest 与版本变更说明

- Trigger: `build-release`、发布包候选验收、release-info 版本变更说明校验。
- Preflight check: `build-release` 使用 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；构建后以发布包根目录 `manifest.json` 为权威，校验 `releaseTag`、`component`、`publishScope`、`sourceRepos`、`dirty=false`、artifact hash、`changeSet.summary`/变更说明。
- Blocker: manifest 缺失、版本号或变更说明无法确认、sourceRepos commit 与冻结 HEAD 不一致、dirty 非 false、artifact 缺失/哈希不一致、包内出现非本次范围 Website/showroom 数据目录。
- Verification: 记录 manifest path、releaseTag、sourceRepos backend/frontend commit、dirty=false、artifact 校验和 release-info/changeSet 摘要。
- Forbidden action: 不得用 legacy `release-manifest.json` 替代 Manifest v1 的 sourceRepos 证明，不得用 PowerShell 中文乱码输出作为唯一变更说明证据。
- Evidence: `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`。

### PowerShell / SSH / 远端验证承载

- Trigger: PowerShell 编排 Git、构建、发布、SSH、MySQL、HTTP、Playwright 或中文日志/JSON。
- Preflight check: 全程不用 `&&`；中文读写显式 UTF-8；SSH 多行脚本用 UTF-8 bytes + LF；远端 MySQL 查询用 stdin heredoc/单引号 SQL；native 命令以退出码和结构化结果共同判定。
- Blocker: 命令输出含明文密码/token/私钥/连接串、SSH stdin/CRLF 损坏、SQL 查询为空但未做承载复查、Playwright 模块或浏览器路径不可用且无稳定安装浏览器可用。
- Verification: 记录退出码、结构化响应、脱敏日志、secret scan 摘要、远端检查字段和 Playwright 页面结果。
- Forbidden action: 不得记录完整 `.env`、runtime-control local config、数据库密码或 raw secret-bearing logs；不得因承载错误跳过 release lock、migration、release-info 或页面验收。
- Evidence: `E:\IntRuoyi\docs\powershell-memory.md`、`docs/powershell-preflight-lessons.md`。

### 收尾清理与经验沉淀

- Trigger: 发布验证完成后进入 closeout、清理 release worktree、沉淀发布问题。
- Preflight check: 先把任务状态置为 `ready_for_closeout`；运行 task-closeout-cleanup preview/apply；确认 `task.md`、`execution-log.md`、`verification-report.md` 保留；删除 release worktree 前确认无未确认改动、无未合回提交、运行控制台已恢复稳定主路径。
- Blocker: worktree dirty、有未合回提交、运行控制台仍引用待删 worktree、Git 注册或物理目录残留无法解释、经验沉淀无合适既有归宿且未取得新建授权。
- Verification: cleanup preview/apply、`git worktree list --porcelain` 不含本轮路径、`Test-Path` 物理目录为 false、运行控制台 health=UP、经验索引关键词可定位。
- Forbidden action: 不得删除其他任务 worktree 或进程，不得把任务状态提前标记 `completed`，不得把一次性流水混入长期经验。
- Evidence: `docs/test-release-preflight.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`project-experience-consolidation` 技能。

## Current Status

completed

## Previous Blocker Resolution

- `publish-test` 已执行但失败，operationId=`op-2026-07-31T020623302348Z-69bf4670-0461-434a-beb1-d4efd1d6f369`。
- 原阻塞原因：测试服执行 required-sql `20260726_dcc_codex_test_items_seed.sql` 时，`CALL ensure_dcc_codex_test_items_seed()` 在第 291 行失败，MySQL 报 `ERROR 1267 Illegal mix of collations`。
- 正式修复已提交到主程序提交 `b6370020247aac7fd27e25a9842601a992a816c7`，提交说明为 `任务: 修复测试项种子排序规则`；目标 pytest 5 passed，全量 migration policy 400 passed。
- 本轮重新冻结维护提交 `9b530038433c964ab39de19f5d30d63ad4702333` 与主程序提交 `b6370020247aac7fd27e25a9842601a992a816c7`，分别使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731b\m` 和 `D:\IntRuoyiWorktree\r260731b-release-app`。
- 新候选 `release-20260731-sqlfix-head-test-r260731b-r2` 已完成 `build-release`；发布包位于 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260731-sqlfix-head-test-r260731b-r2`，尚未执行本轮 `publish-test`。

## Current Release Candidate

- releaseTag：`release-20260731-sqlfix-head-test-r260731b-r2`
- 维护仓提交：`9b530038433c964ab39de19f5d30d63ad4702333`
- 主程序提交：`b6370020247aac7fd27e25a9842601a992a816c7`
- 构建时间：`2026-07-31 16:34:43 +08:00` 至 `2026-07-31 18:08:11 +08:00`
- 构建结果：退出码 `0`，Manifest v1、legacy manifest、镜像 tar 和 NAS 上传均已生成。
- 当前动作边界：仅允许继续 `publish-test` 和测试服真实运行态验证；继续禁止 `mark-tested`、`promote-prod`、`promote-backup`。

## r260731c Continuation

- `r260731b-r2` 已因智能排产 seed collation 冲突判废，不得复用该 releaseTag 或发布包。
- 新发布输入固定为维护提交 `9b530038433c964ab39de19f5d30d63ad4702333` 与主程序正式修复提交 `7b9d8c36f3aa19779277be1a2cddaa50789a3821`，不追逐 `int_main` 后续提交。
- 新维护 release worktree 规划为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731c\m`，新主程序 release worktree 规划为 `D:\IntRuoyiWorktree\r260731c-release-app`。
- `release-20260731-smartseed-sqlfix-head-test-r260731c-r1` 在 build-release 期间因本机重启中断，缺少 manifest 和镜像 tar，已判废。
- 重启后新候选 releaseTag 固定为 `release-20260731-smartseed-sqlfix-head-test-r260731c-r2`。
- 当前动作边界重新从新候选的 `build-release` 开始，后续仅允许 `publish-test` 与测试服真实运行态验收；禁止 `mark-tested`、`promote-prod`、`promote-backup`。

## r260731c-r2 Build Evidence

- `build-release` operation=`op-2026-07-31T121620378859300Z-2ce13a4f-9be4-4468-bc59-340c4505a8bf`，通过真实运行控制台页面提交，最终 `SUCCESS`。
- 构建输入固定为维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731c\m`、主程序 release worktree `D:\IntRuoyiWorktree\r260731c-release-app`；维护提交=`9b530038433c964ab39de19f5d30d63ad4702333`，主程序提交=`7b9d8c36f3aa19779277be1a2cddaa50789a3821`，构建前后两个 worktree 均 clean。
- 发布包=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260731-smartseed-sqlfix-head-test-r260731c-r2`；包含 Manifest v1、legacy manifest、镜像 tar，`validate-release-manifest.ps1 -Mode report-only` 返回 `MANIFEST_VALIDATION_PASSED`。
- Manifest v1 `manifestVersion=1.0`、`publishScope=code-only`、两个 `sourceRepos.commit=7b9d8c36f3aa19779277be1a2cddaa50789a3821`、`dirty=false`；所有 artifact SHA-256、两个修复 seed SQL SHA-256、前端 `release-info.json` 的版本号和变更说明均已复核一致；包内无 Website/showroom 目录。
- 当前仍只允许同一 releaseTag 执行 `publish-test` 和测试服真实运行态验证；不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## r260731d Continuation

- `r260731c-r2` 已因智能排产 seed MySQL 临时表重复打开错误判废，不得复用该 releaseTag 或发布包。
- 新发布输入固定为维护提交 `9b530038433c964ab39de19f5d30d63ad4702333` 与主程序正式修复提交 `fa6137aa24f65bca75714d9b8c497d71ffee5d14`，不追逐 `int_main` 后续提交。
- 当前 releaseTag：`release-20260731-smartseed-tempfix-head-test-r260731d-r1`。
- 当前维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d\m`，detached HEAD=`9b530038433c964ab39de19f5d30d63ad4702333`，`git status --porcelain --ignored=no` 为空。
- 当前主程序 release worktree：`D:\IntRuoyiWorktree\r260731d-release-app`，detached HEAD=`fa6137aa24f65bca75714d9b8c497d71ffee5d14`，`git status --porcelain --ignored=no` 为空。
- `build-release` operation=`op-2026-07-31T132619952790400Z-5fdeca9b-97ac-42bc-aac0-d8803cf25169`，结果 `SUCCESS`。
- 发布包=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260731-smartseed-tempfix-head-test-r260731d-r1`；Manifest v1 校验 `MANIFEST_VALIDATION_PASSED`，`publishScope=code-only`，两个 `sourceRepos.commit=fa6137aa24f65bca75714d9b8c497d71ffee5d14`，`dirty=false`，变更说明为 `Release package release-20260731-smartseed-tempfix-head-test-r260731d-r1`。
- 真实运行控制台已预览并提交仅测试服 `publish-test`，operation=`op-2026-07-31T134347021461200Z-e8246902-6278-427a-a4c3-0ea2df178311`；参数为 `-Mode deploy-release -Environment test -ReleaseTag release-20260731-smartseed-tempfix-head-test-r260731d-r1 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime`，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 2026-07-31 22:01 +08:00 恢复后核验：运行控制台 PID=`41284`、health=`UP`，publish-test 子进程仍在运行且日志持续增长，当前处于 required-sql 迁移状态记录阶段，尚未到最终 `SUCCESS/FAILED`。

## Closeout Completion

- 2026-07-31 22:31 +08:00 最终收口完成：本轮最终 releaseTag `release-20260731-smartseed-tempfix-head-test-r260731d-r1` 已完成仅测试服发布和真实运行态验证，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- `task-closeout-cleanup` preview/apply 已通过并保留 `task.md`、`execution-log.md`、`verification-report.md`；本次任务附属 Playwright snapshot 和临时 evidence 文件已按规则清理。
- 本任务运行控制台已从 `r260731d` 临时路径恢复到稳定主路径；维护控制台 PID=`50580`，`http://127.0.0.1:48181/actuator/health` 返回 `UP`，生产服和备份服访问仍禁用。
- 维护仓 `git worktree list --porcelain` 与主程序仓 `git worktree list --porcelain` 均不含 `r260731d`；物理路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260731d-state`、`D:\IntRuoyiWorktree\r260731d-release-app` 均为 `Test-Path=False`。
- 本任务残留 Playwright CLI daemon `r260731c-r2` 已按任务归属校验后停止；`output\playwright\20260730-head-test-only-release` 与 `output\playwright\20260731-r260731c` 已删除，任务相关 `.playwright-cli\page-*.yml` 快照复核不存在。
- 收口问题已记录并沉淀：Git 注册删除后仍可能遗留 ignored `node_modules` 物理目录；必须同时复核 Git 注册和物理路径，不得只凭 `git worktree list` 判定清理完成。
