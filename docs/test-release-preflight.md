# 测试服发布前置门禁

## 目的

本文是 Codex 执行 IntRuoyi 仅测试服构建发布前的主入口。目标是把长篇经验拆成可执行门禁：先按本文逐项检查，失败时再跳转到对应经验文档诊断。

正式规则仍以以下文档为准：

- `E:\IntRuoyi\docs\release-backup-restore.md`
- `E:\IntRuoyi\docs\server-access.md`
- `E:\IntRuoyi\docs\login-access.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
- `E:\IntRuoyi\docs\worktree-memory.md`

## 使用顺序

1. 创建或识别 `doc/tasks/<task-id>/`，先在 `task.md` 写入目标、里程碑、预期验证和当前状态。
2. 再读 `docs/experience-index.md`，确认本任务命中测试服发布、构建、manifest、PowerShell、worktree 和运行态门禁，并把适用门禁补入 `task.md`。
3. 在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS` 后，再执行发布、服务器写入、数据库写入或真实 E2E。
4. 按本文阶段顺序执行；任一 fail fast 条件出现时停止发布，记录问题，不进入下一阶段。

## 可索引门禁摘要

- Trigger: 任何“仅测试服发布”“当前提交发布到测试服”“publish-test”“测试服运行态验收”“运行控制台版本和变更说明验证”任务。
- Preflight check: 创建任务目录，读取经验索引，冻结三仓提交到本轮专用 release worktree，构建前后校验 Manifest v1、legacy manifest、required SQL、publish-test 预览和测试服真实运行态。
- Blocker: 构建来源无法证明为冻结提交、manifest 缺失或 dirty、版本/变更说明无法确认、预览不是 test、operation 非 SUCCESS、实际镜像/health/HTTP/迁移/控制台版本任一失败。
- Verification: `execution-log.md` 中记录冻结提交、worktree 路径、build/publish operation、manifest 校验、远端 `.env IMAGE_TAG`、实际镜像、容器、health、HTTP、Playwright 页面和 worktree 清理结果。
- Forbidden action: 不得从脏主工作区构建，不得拼接不同 releaseTag，不得手工改库绕过 required SQL，不得跳过真实页面验证，不得在 worktree 未清理或控制台仍指向临时路径时宣称完成。

## 阶段 0：发布范围锁定

### 必查项

- 本次是否只允许测试服。
- 本次 releaseTag。
- 目标测试服务器是否为 `172.30.30.58`。
- 是否明确禁止正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。

### Fail Fast

- 用户未明确授权正式服或备份服，却出现正式服/备份服动作。
- 发布目标、服务器或 releaseTag 无法确认。
- 想复用旧 releaseTag 拼接新构建、新测试服结果或旧成功记录。

### 必须记录

- 用户发布范围。
- releaseTag。
- 禁止动作清单。

## 阶段 1：Git 与临时发布 Worktree

### 必查项

- 维护仓、后端仓、前端仓当前分支、HEAD、dirty 状态。
- 主工作区若存在未提交或未跟踪内容，必须创建本轮专用临时 release worktree。
- release worktree 使用短路径，推荐 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><短标识>\m|b|f`。
- release worktree 必须检出本次冻结提交。
- 构建开始后以冻结 release worktree 提交为来源基线；持续开发导致源分支后续新增提交，不要求本轮重复追逐重建。

### 推荐命令

```powershell
git -C D:\ProjectPackage\Int\IntRuoyiMaintance status --short --branch
git -C E:\IntRuoyi\IntRuoyiBackend status --short --branch
git -C E:\IntRuoyi\IntRuoyiFronted status --short --branch
git -C <release-worktree> rev-parse HEAD
git -C <release-worktree> status --porcelain
```

### Fail Fast

- release worktree dirty。
- worktree 提交与冻结基线不一致。
- 构建输入来自主工作区脏内容、长期旧 worktree 或未确认路径。
- `runtime-control.local.yaml` 仍指向旧 worktree 或主工作区。

### 必须记录

- 三仓冻结提交。
- worktree 路径。
- 构建目录。
- worktree 是否 clean。
- 是否产生新提交，是否需要合回 `int_main`。

## 阶段 2：构建前契约门禁

### 必查项

- 维护控制台当前 48181 进程是否加载本轮发布逻辑。
- 前端依赖是否在 release worktree 内按锁文件恢复。
- 后端 release migration metadata gate 是否通过。
- code-only 发布是否明确 `-Component intruoyi`、`SkipDatabaseSync`、`SkipMinioSync`。
- 测试服已知 required SQL 前置数据冲突是否已只读检查。

### 推荐命令

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:48181/actuator/health
python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --json
corepack pnpm@10.25.0 --version
```

### Fail Fast

- 维护控制台不是本轮 Jar 或健康检查不是 `UP`。
- SQL metadata 缺失、`dependsOn` 错误或 type 不在允许枚举。
- 前端 lockfile/依赖恢复失败。
- code-only 包仍会执行 `type=data` required SQL。

## 阶段 3：Build Release

### 必查项

- build preview 只包含构建动作，不包含正式服、备份服、恢复、回滚或推广动作。
- build operation 最终为 `SUCCESS`。
- 发布包目录存在。
- `manifest.json` 存在且为来源权威。
- legacy `release-manifest.json` 只按 legacy schema 校验，不强制其包含 frontend commit。

### Manifest 必查字段

- `releaseTag` 等于本轮 releaseTag。
- `component=intruoyi`。
- `publishScope=code-only` 或本轮明确范围。
- `sourceRepos` 中后端、前端 commit 等于冻结提交。
- `sourceRepos[*].dirty=false`。
- `changeSet.summary` 或变更说明可确认。
- artifact 清单大小和 SHA256 全部匹配。

### Fail Fast

- manifest 缺失。
- 版本号或变更说明无法确认。
- 任一 source repo `dirty=true`。
- artifact 缺失或哈希不一致。
- package 包含 Website/showroom 非本次范围目录。

## 阶段 4：Publish-Test 前门禁

### 必查项

- publish-test preview 中 `Environment=test`。
- 测试服主机为 `172.30.30.58`。
- 远端运行目录为 `/opt/intruoyi/runtime`。
- preview/log 中无 `172.30.30.57`、`172.30.30.59`、`promote-prod`、`promote-backup`、`mark-tested`。
- required SQL 真实数据前置冲突已清零或已明确阻塞。

### Fail Fast

- 预览动作不是测试服。
- 参数来自正式服或备份服模板。
- required SQL 依赖未验证 live data。
- 测试服数据修复缺少授权、备份、ROLLBACK 演练或引用保持验证。

### 并发发布与目标版本漂移门禁

- Trigger: 测试服发布、完成性审计或长时间 publish-test 期间，可能存在其他任务操作同一测试环境、发布锁或运行目录。
- Preflight check: 在真实写入前和最终验收前分别检查本地/远端发布进程、`infra_release_operation_lock`、远端 `.env IMAGE_TAG`、compose 解析镜像、实际容器镜像和 `release-info.json`，记录当前 releaseTag 与 operation。
- Blocker: 存在活动发布进程或 `RUNNING` 锁；任一检查点的 releaseTag 与本任务目标不一致；发布过程中被其他任务覆盖。
- Verification: 无活动发布进程，锁状态为本任务对应的 `APPLIED`，`.env`、compose、实际镜像和 `release-info.json` 全部等于同一目标 releaseTag。
- Forbidden action: 不得使用发布前旧快照代替最终状态，不得让两个任务重叠发布同一环境，不得在目标版本已被覆盖后仍宣称完成。
- Evidence: `doc/tasks/20260710-current-head-test-only-release-completion-audit/execution-log.md`；并发 v3 于 2026-07-10 14:43 完成后，本任务按冻结 v9 基线于 14:49-15:05 恢复并重新验证。

## 阶段 5：测试服发布后真实运行态

### 必查项

- publish operation 为 `SUCCESS`。
- `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG=<releaseTag>`。
- `intruoyi-backend` 与 `intruoyi-frontend` 实际镜像 tag 等于 releaseTag。
- 两个容器均为 running。
- 后端 health HTTP 200 且 `status=UP`。
- 前端 HTTP 200 且 HTML 非空。
- required migration 与 release lock 为 APPLIED。
- 本次涉及的数据库唯一索引、冲突数或核心契约按只读 SQL 验证通过。

### 推荐远端检查

```powershell
ssh root@172.30.30.58 bash -s
```

远端脚本通过 UTF-8 bytes + LF 发送，避免 Windows text mode 把 LF 转 CRLF。

### Fail Fast

- `.env IMAGE_TAG` 已变但容器仍运行旧镜像。
- health 或 frontend HTTP 失败。
- operation 未成功或 release lock 未 APPLIED。
- migration 失败、唯一索引缺失或冲突数不为 0。

## 阶段 6：运行控制台与前端页面

### 必查项

- 用 Playwright 真实登录测试租户。
- 从真实菜单进入 `基础设施 -> 监控中心 -> 运行控制台`。
- 打开全局版本/变更说明入口。
- 页面可见本轮 releaseTag、变更说明、变更项和后端/前端冻结提交。
- 页面 console error 为 0。

### Fail Fast

- 页面无法真实登录或菜单不存在。
- 版本号或变更说明不可见。
- 只用接口结果代替页面验收。
- 用户明确要求运维矩阵健康时，矩阵显示 `ERROR/unknown`。

### 可记录但不可隐藏

- 若 Linux 后端运行控制台矩阵仍调用 `powershell.exe`，必须记录为独立缺陷。
- 若 `/release-status` current tag 为 null，但 release-info 对话框、维护控制台和真实运行态一致，必须分开记录，不得说矩阵健康。

## 阶段 7：问题记录与经验沉淀

每个问题必须记录：

- 现象。
- 阶段。
- 影响。
- 原因判断。
- 处理动作。
- 结果。
- 是否可前置检查。
- 是否可自动化。
- 下次如何避免。

测试服发布成功后，把可复用问题沉淀到：

- `docs/test-release-preflight.md`：发布前必查和 fail fast 门禁。
- `docs/release-build-preflight-lessons.md`：构建、manifest、required SQL、运行态发布经验。
- `docs/powershell-preflight-lessons.md`：PowerShell、SSH、编码、退出码经验。
- `docs/experience-index.md`：关键词路由。

## 阶段 8：收尾与 Worktree 清理

### 必查项

- 发布和真实运行态验证完成后，将任务状态标记为 `ready_for_closeout`，不得提前写 `completed`。
- 运行 `task-closeout-cleanup` preview。
- `task.md`、`execution-log.md` 和 `verification-report.md` 必须位于默认 keep 集。
- 临时 release worktree 若无新提交，发布完成后删除。
- 若有新提交，必须先合回对应 `int_main` 并验证，再清理。
- 删除前恢复本地维护控制台配置，不得让 48181 继续引用即将删除的 worktree。
- Windows `git worktree remove` 后还要确认物理目录不存在。
- cleanup、合并、Git 注册、物理目录和运行控制台恢复全部验证通过后，才把任务状态更新为 `completed`。

### Fail Fast

- worktree 有未确认改动。
- worktree 有未合回提交。
- cleanup 尚未通过却已把任务标记为 `completed`。
- `verification-report.md` 被归入 delete。
- 运行控制台仍引用 release worktree。
- Git 注册已删但物理目录残留，且未完成固定路径、无进程引用和无 Git 注册检查。

## 必须自动化的候选项

- 三仓 HEAD/dirty/worktree 冻结 JSON。
- Manifest v1 与 legacy manifest 分 schema 校验。
- artifact 大小和 SHA256 校验。
- publish-test preview 环境边界检查。
- 测试服 `.env`、镜像、容器、health、HTTP、migration、release lock 检查。
- 运行控制台 release-info 页面 Playwright 检查。
- worktree 注册和物理目录清理检查。

## 永远不得跳过

- 不得从脏主工作区直接构建发布包。
- 不得用健康检查单点代替真实运行态。
- 不得用运行控制台错误矩阵覆盖已独立验证的真实状态。
- 不得手工改测试库绕过 required SQL。
- 不得把失败 releaseTag 的 build/test/prod/backup 结果与新 releaseTag 拼接。
- 不得因为 PowerShell 编码、SSH 换行或本地校验脚本误报而降级验证。

## 2026-07-11 仅测试服发布运行态验收新增门禁

### Trigger

仅测试服发布、`publish-test`、测试服真实运行态验收、运行控制台版本号和变更说明核对。

### Preflight check

- `publish-test` 前先直接确认目标 releaseTag 的本地包和 NAS manifest 可读，不依赖全量候选包扫描作为唯一可用性证明。
- 执行 `publish-test` 预览前确认运行控制台 health=`UP`，且没有与本 releaseTag 无关的活动发布锁。
- 发布后必须同时验证：operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=`UP`、frontend HTTP=200、`/release-info.json`、运行控制台 release-status 和真实页面版本对话框。
- 使用 Playwright 验证运行控制台时，先确认 `require.resolve('playwright')` 和浏览器 executable path；浏览器缓存缺失时使用稳定安装的 Chrome/Edge 路径，不在发布验收中临时下载浏览器。

### Blocker

- 目标 releaseTag 的 manifest 不可读、sourceRepos 不匹配或 `dirty=true`。
- `publish-test` preview/submit 无法返回明确 operation，或 operation 非 SUCCESS。
- 远端 `.env`、实际镜像 tag、backend health、frontend HTTP、release-info 或运行控制台版本/变更说明任一缺失。

### Verification

- 记录 build-release operation、publish-test operation、manifest path、远端 `.env`、`docker compose ps`/`docker inspect`、backend health、frontend HTTP、`/release-info.json` 和 Playwright 结果。
- 运行控制台版本验收必须打开 `版本变更说明` 对话框，核对 releaseTag、summary/changeSet 和 backend/frontend commits。

### Forbidden action

- 禁止用 HTTP 200 单项替代运行态完整验收。
- 禁止在仅测试服发布任务中执行 `mark-release-tested`、`promote-prod`、`promote-backup`。
- 禁止把 PowerShell 默认 JSON/控制台输出中的中文文本作为唯一变更说明证据。

### Evidence

- 本次任务：`doc/tasks/20260711-current-head-test-only-release/execution-log.md`、`verification-report.md`。
- ReleaseTag：`release-20260711-current-head-test-r4`；build operation `op-2026-07-11T020116790952700Z-a56e7120-5a78-45a4-a2a3-a1016359d0f1`；publish operation `op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d`。

## 2026-07-12 publish-test 目标字段与版本说明验收门禁

### Trigger

仅测试服发布、`publish-test` preview、发布后运行控制台版本号与变更说明核对。

### Preflight check

- `publish-test` preview 的目标判断必须基于结构化字段：`action=publish-test`、`mode=deploy-release`、`environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime` 和目标 `releaseTag`。
- preview 输出中的 `BackupServerHost` 只能作为参数元数据记录，不得单独作为实际发布目标判定；必须同时确认没有 `mark-tested`、`promote-prod`、`promote-backup` 动作。
- 运行控制台版本与变更说明验收必须核对 releaseTag、changeSet.summary、changes、backend/frontend sourceRepos commit 和 dirty=false。
- PowerShell 输出出现中文 mojibake 时，必须改用 UTF-8-aware parser、HTTP JSON 原文或真实页面作为权威证据，不得用默认渲染结果判定通过或失败。

### Blocker

- preview 无法明确证明 `ServerHost=172.30.30.58` 或 `environment=test`。
- preview 中出现正式服/备份服的实际 `ServerHost`、`RemoteAppDir` 或 promote/mark-tested 动作。
- release-info、运行控制台或页面无法证明版本号与变更说明来自本次 releaseTag。

### Verification

- 记录 preview 字段化检查结果、publish-test operation、远端 `.env IMAGE_TAG`、镜像 tag、health、HTTP、`/release-info.json` 和运行控制台版本说明结果。

### Forbidden action

- 禁止用字符串包含 `BackupServerHost` 直接判定 publish-test 目标错误。
- 禁止在仅测试服发布任务中执行 prod/backup/promote/mark-tested。
- 禁止因 PowerShell 中文渲染乱码降级或跳过版本说明验收。

### Evidence

- 本次任务：`doc/tasks/20260712-current-head-test-only-release/execution-log.md`、`verification-report.md`。
- ReleaseTag：`release-20260712-intmain-test-r260712p-r3`；build operation `op-2026-07-12T031646245278700Z-f1006e17-c7b6-445b-9eaa-5d67e4b66ed1`；publish operation `op-2026-07-12T043308044248700Z-d8e299c3-a64e-43cc-bd5a-949db86dc67f`。
