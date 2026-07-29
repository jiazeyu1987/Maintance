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
- [x] 测试服发布成功后沉淀前置经验；本轮 SQL collation、临时表重开、日志脱敏、Playwright 浏览器缓存和运行态验收门禁均已合并到已有经验文档。
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
- `是否从根因和长期维护角度解决`：是，本次按现有发布文档和已沉淀前置经验执行，发布输入固定为目标 HEAD，不追逐后续提交。
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
- Preflight check: 分别记录维护仓、后端仓、前端仓当前分支、HEAD、dirty 状态；创建短路径本轮专用 release worktree，维护仓/后端/前端分别使用 `m`、`b`、`f` 子目录；构建前后确认 worktree `git status --porcelain --ignored=no` 为空。
- Blocker: release worktree dirty、worktree HEAD 与冻结提交不一致、运行控制台仍指向主工作区或旧 worktree、state-dir/log/cache 污染 release worktree、构建产物 manifest `sourceRepos[*].dirty=true`。
- Verification: `git status --short --branch`、`git rev-parse HEAD`、`git worktree list --porcelain`、manifest `sourceRepos` commit/dirty 校验。
- Forbidden action: 不得从脏主工作区构建，不得复用长期旧 worktree，不得把主工作区未提交修复混入发布包。
- Evidence: `docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\worktree-memory.md`。

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

- 最终成功 releaseTag：`release-20260729-sqlfix-test-r260729d-r1`。
- 最终发布输入：
  - 维护仓 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729d\m`，detached HEAD `4a77055f4a90209bae9bbba4fc2b75c03eb9aa88`，构建/发布前后 `git status --porcelain --ignored=no` 为空。
  - 主程序 release worktree `D:\IntRuoyiWorktree\r260729d-release-app`，detached HEAD `919122b6f72e2f0cf7e4cdb7f2ee913294af0473`，构建/发布前后 `git status --porcelain --ignored=no` 为空。
  - 后端构建目录 `D:\IntRuoyiWorktree\r260729d-release-app\IntRuoyiBackend`，前端构建目录 `D:\IntRuoyiWorktree\r260729d-release-app\IntRuoyiFronted`。
- 构建结果：`build-release` operation `op-2026-07-29T101921985772400Z-05210b94-fafa-43d9-990e-dca0ea15c7e1` 为 `SUCCESS`；本地发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260729-sqlfix-test-r260729d-r1` 存在，Manifest v1 validator `MANIFEST_VALIDATION_PASSED`。
- Manifest/版本/变更说明：`manifest.json` 与 `release-manifest.json` 均为 `release-20260729-sqlfix-test-r260729d-r1`、`publishScope=code-only`、`component=intruoyi`；backend/admin-frontend sourceRepos commit 均为 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 且 `dirty=false`；changeSet 包含“发布包：release-20260729-sqlfix-test-r260729d-r1”和“组件范围：intruoyi”。
- 测试服发布结果：`publish-test` operation `op-2026-07-29T103744548087400Z-d86c6a40-3508-43f9-933c-7c63af704bb3` 为 `SUCCESS`；本 releaseTag 只有 `build-release` 与 `publish-test` 两个 operation，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 测试服真实运行态：远端 `/opt/intruoyi/runtime/.env IMAGE_TAG`、`intruoyi-backend` / `intruoyi-frontend` 实际镜像 tag 均为 `release-20260729-sqlfix-test-r260729d-r1`，两个容器 running，backend health `{"status":"UP"}`，backend HTTP `200`，frontend HTTP `200`，PDF worker HTTP `200 application/javascript`。
- 数据库发布状态：`infra_release_operation_lock` 目标 releaseTag 为 `APPLIED`；`infra_release_migration` 统计 `APPLIED=7`、`SKIPPED_ALREADY_APPLIED=353`、`FAILED=0`。
- 页面与运行控制台：Playwright 使用本机 Chrome 打开测试服前端并显示登录页；运行控制台页面显示测试服版本 `release-20260729-sqlfix-test-r260729d-r1`，版本变更说明对话框显示目标 releaseTag、发布包和组件范围；`/release-status` 的 `testCurrentReleaseNotes` 与 Manifest sourceRepos 一致。
- 经验沉淀：已更新 `docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md` 与 `docs/experience-index.md`，覆盖 SQL collation、MySQL 1137 临时表重开、release worktree 前端依赖、日志脱敏、Playwright 浏览器缓存和测试服运行态完整验收。
- 本地运行控制台已从 `r260729d` 临时维护 worktree 恢复到主维护路径，PID `48676`，health=`UP`。
- 非发布阻塞项：主程序修复 worktree `D:\IntRuoyiWorktree\r260729-sql-collation` 的本地提交 `919122b6` 已用于本次发布，但 `git push origin codex/20260729-test-release-sql-collation` 仍因 GitHub `Recv failure: Connection was reset` 失败；该 worktree 保留，不作为本次 release worktree 清理对象。
- 收尾清理：task-closeout-cleanup preview/apply 通过且无删除项；本任务维护仓 release worktree `r260729a/b/c/d`、主程序 release worktree `r260729a/app` 与 `r260729b/c/d-release-app`、状态目录 `r260729a/b/c/d-state` 均已清理；维护仓与主程序 `git worktree list --porcelain` 不再包含 `r260729a/b/c/d`，物理路径 `Test-Path` 均为 `False`。
- 收尾验证：本地运行控制台 48181 health=`UP` 且 PID `48676` 命令行指向主维护路径；没有进程命令行引用本任务 release worktree 路径；`docs/experience-index.md` 可通过本次新增关键词定位已沉淀经验。

## Verification Result

PASS: 仅测试服发布已完成，最终 releaseTag `release-20260729-sqlfix-test-r260729d-r1` 的构建来源、manifest、版本号、变更说明、测试服真实运行态、前端页面、运行控制台版本对话框、forbidden operation 检查、经验沉淀和 closeout 清理均通过。未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Problem Log

详见 `execution-log.md` 的 `## Problem Records`。本轮已记录并沉淀 Git/worktree、构建、manifest、required SQL、发布脚本、镜像/容器、健康检查、前端页面、运行控制台、日志脱敏、Playwright 浏览器缓存、重复操作和耗时点等问题。

## Cleanup Candidates

- `output/playwright/test-frontend-r260729d-r1.png`
- `output/playwright/runtime-control-r260729d-r1.png`
- `.playwright-cli/`
