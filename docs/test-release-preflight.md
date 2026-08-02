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
- Evidence: `task.md`、`execution-log.md`、`verification-report.md`、releaseTag、build/publish operation、manifest 路径、远端运行态证据、Playwright 页面证据和 worktree 清理证据。

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
python -X utf8 script\release\run-release-migration-policy-gate.py --help
python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --output <task-dir>\migration-policy-gate.json
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

### publish-test 失败后 `.env` 与实际镜像漂移门禁

- Trigger: `publish-test` operation 非 `SUCCESS`，尤其 required SQL 失败后仍发现 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG` 已被写成目标 releaseTag。
- Preflight check: 失败冻结时必须同时记录 operation 状态、release lock、migration failed 行、`.env IMAGE_TAG`、`docker inspect` 后端/前端实际镜像、容器状态、backend health、frontend HTTP；若 `.env` 与实际镜像不一致，任务状态必须标记 blocked，后续重启/发布前先处理 drift。
- Blocker: `.env IMAGE_TAG=<目标 releaseTag>` 但 backend/frontend 实际镜像 tag 仍为旧 releaseTag；release lock 为 `FAILED`；migration failed count 大于 0；operation 非 `SUCCESS`。
- Verification: 远端证据必须显示 `.env`、实际镜像、容器状态、health、HTTP、lock/migration 状态；恢复或重发前再次确认 drift 已消除。
- Forbidden action: 不得因 `.env IMAGE_TAG` 等于目标 releaseTag 就宣称发布成功；不得在未授权时手工改 `.env`、手工更新 release lock/migration、或复用失败 releaseTag 继续 mark/promote。
- Evidence: `doc/tasks/20260729-head-test-only-release/execution-log.md`；`publish-test` operation `op-2026-07-29T024258673743700Z-1774cd02-0579-420e-86eb-bcd0ed97475a` failed 后 `.env IMAGE_TAG=release-20260729-intmain-head-test-r260729a-r1`，但 backend/frontend 容器仍运行 `release-20260728-codeonly-noonlyoffice-test-r2`。2026-08-01 追加证据：`doc/tasks/20260801-head-test-only-release/execution-log.md`；`publish-test` operation `op-2026-07-31T184648151088Z-d51572f6-9207-44dd-bbab-6f54c347cea4` failed 后 `.env IMAGE_TAG=release-20260801-intmain-head-test-r260801a-r2`，backend/frontend 实际容器仍运行 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`，release lock=`FAILED`，migration `FAILED=1`。

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
- 2026-07-29 追加证据：`release-20260729-sqlfix-test-r260729d-r1` 仅执行 `build-release` 与 `publish-test`，未执行 `mark-tested`、`promote-prod`、`promote-backup`；测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health `UP`、frontend HTTP `200`、release-info、运行控制台 release-status 和 Playwright 版本变更说明对话框均一致。

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

## 2026-07-13 仅测试服发布远端验收脚本承载门禁

### Trigger

仅测试服发布后通过 SSH 脚本验证 `.env IMAGE_TAG`、Docker 镜像、容器状态、health、HTTP、`release-info.json`、release lock 或 migration 状态。

### Preflight check

- 远端多行脚本必须以 UTF-8 bytes + LF 发送；Windows Python/PowerShell 文本模式不得直接作为 `bash -s` stdin。
- 需要向 `bash -s` 传脚本时不得使用 `ssh -n`。
- 远端 MySQL 只读核验使用 stdin heredoc 和单引号 SQL 字面量，避免多层双引号过滤返回空结果。
- 配置和 operation 日志证据必须先脱敏；不得打印完整 `runtime-control.local.yaml`、`.env` 或 raw operation log。

### Blocker

- SSH 输出为空、stderr 出现 CRLF 解析错误、release lock/migration 查询为空且未做 schema-aware 复查。
- 任一待保留证据含明文密码、token、私钥、连接串或 `mysql -p<secret>`。

### Verification

- 记录 `.env IMAGE_TAG`、backend/frontend image tag、container running、health=UP、frontend HTTP 200、PDF worker HTTP 200、release-info tag/commit、release lock APPLIED、migration failed count=0。
- 页面验收必须打开运行控制台“版本变更说明”，确认 releaseTag 与变更说明可见，console error=0。

### Forbidden action

- 禁止把 SSH/CRLF/SQL 承载错误当作服务器发布失败；修正采集路径后必须重跑。
- 禁止因 release-status/release-packages 超时跳过目标 Manifest 直接校验。

### Evidence

- 本次任务：`doc/tasks/20260713-current-head-test-only-release/execution-log.md`、`verification-report.md`。
- ReleaseTag：`release-20260713-current-head-test-r260713t-r3`；build operation `op-2026-07-13T114933441747800Z-ea18fdef-4abd-44e8-a712-8615a67b95bf`；publish operation `op-2026-07-13T121325438123300Z-549989ce-c0b2-4cab-bc66-e7dfc0630394`。
- 2026-07-31 追加证据：`release-20260731-smartseed-tempfix-head-test-r260731d-r1` 首次远端验收因 Windows text mode stdin CRLF 导致 `.env IMAGE_TAG` 和 frontend inspect 证据不完整；改用 `input=remote_script.encode('utf-8')`、LF 二进制 stdin 后，`.env IMAGE_TAG`、backend/frontend image tag、container running、backend health `UP`、frontend HTTP `200`、release-info、release lock `APPLIED`、migration failed/running count `0` 全部通过。

## 2026-07-13 运行控制台版本说明与 source commit 分层验收门禁

### Trigger

仅测试服发布后，使用 Playwright 验证运行控制台版本号、变更说明，并同时需要证明后端/前端 source commit 来自冻结 HEAD。

### Preflight check

- 页面验收聚焦用户可见字段：releaseTag、版本号、发布包、组件范围、变更说明或 change summary。
- source commit、dirty=false、publishScope 等机器字段以远端 `release-info.json` 和发布包 `manifest.json` 为权威。
- 若当前 UI 版本对话框不展示 commit，不得把“页面无 commit”直接当作发布失败；必须确认页面可见版本说明已通过且 release-info/manifest 的 commit 校验独立通过。

### Blocker

- 页面无法显示当前 releaseTag 或版本变更说明。
- `release-info.json` 或 `manifest.json` 无法证明 backend/frontend commit 与冻结 HEAD 一致，或 sourceRepos `dirty=true`。

### Verification

- Playwright 记录运行控制台 HTTP 200、版本变更说明对话框可见、releaseTag/发布包/组件范围可见、console errors=0。
- release-info/manifest 记录 backend commit、frontend commit、publishScope、dirty=false，并与冻结 worktree HEAD 比对。

### Forbidden action

- 禁止用页面 HTTP 200 替代版本说明可见性。
- 禁止仅因 UI 不显示 commit 而跳过 release-info/manifest commit 校验，或反过来只用 API 校验替代用户可见页面验收。

### Evidence

- 本次任务：`doc/tasks/20260713-current-head-test-only-release-rerun/task.md` P006，`runtime-console-page-probe-r260713u.json`。
- ReleaseTag：`release-20260713-current-head-test-r260713u`；build operation `op-2026-07-13T130433994984600Z-0ddaec3f-7a3b-465a-a40b-182c572b3508`；publish operation `op-2026-07-13T132238031788800Z-7427e313-5a0e-4bae-8bc3-be5decaa3c0a`。
- 2026-07-31 追加证据：运行控制台页面显示测试服版本 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`，点击“查看变更”后对话框显示“发布包：release-20260731-smartseed-tempfix-head-test-r260731d-r1”和“组件范围：intruoyi”；source commit 与 dirty=false 由远端 `/release-info.json` 和发布包 `manifest.json` 独立证明。

## 2026-08-01 仅测试服 r260801e 成功闭环门禁

### Trigger

用户明确要求“仅测试服发布”，且发布链路中出现过失败 releaseTag、冻结修复分支或测试服 `.env` / 容器状态漂移。

### Preflight check

- 每个失败 releaseTag 判废；修复后必须重新 `build-release` 新 releaseTag，再执行 `publish-test`。
- 成功判定只接受同一 releaseTag 的 `build-release SUCCESS`、manifest/sourceRepos clean、`publish-test SUCCESS`、测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、health、HTTP、release-info、release lock 和 migration 状态全部一致。
- 运行控制台 release-status 必须显示同一 `testCurrentReleaseTag`、summary、changes 和 sourceRepos；prod/backup current tag 或 `latestTestedReleaseTag` 不参与仅测试服成功判定。
- 任务收尾前必须恢复 48181 到主维护路径，并确认 prod/backup access disabled 后再删除 release worktree。

### Blocker

- 任一成功证据来自不同 releaseTag。
- `mark-tested`、`promote-prod`、`promote-backup` 出现在本轮仅测试服操作链。
- release lock 非 `APPLIED`，migration 存在 `FAILED` / `RUNNING`，或 `.env IMAGE_TAG` 与实际镜像不一致。
- 运行控制台仍指向待删 release worktree。

### Verification

- 保存 `manifest-validation-<tag>.json`、`manifest-summary-<tag>.json`、`publish-test-operation-final-<tag>.json`、`runtime-control-release-status-<tag>.json`、`remote-runtime-verification-<tag>.json` 和 `worktree-cleanup-<tag>.json`。
- 远端运行态断言至少包括 `.env IMAGE_TAG`、backend/frontend image tag、容器 Up、backend health `UP`、frontend HTTP 200、页面标题、`release-info.json`、release lock `APPLIED`、migration failed/running count `0`。

### Forbidden action

- 禁止把失败 releaseTag 的 build 结果与新 releaseTag 的 publish 结果拼接。
- 禁止用 HTTP 200 或 `.env` 单项替代真实镜像、release-info、lock/migration 检查。
- 禁止在仅测试服任务中顺手执行 `mark-tested` 或任何正式/备份服动作。

### Evidence

- `doc/tasks/20260801-head-test-only-release/`；最终 releaseTag `release-20260801-frozen-dcc-column-collation-r260801e-r1`，build operation `op-2026-08-01T075619071613500Z-8ce3eda8-87d7-412c-8daf-b944d4d737df`，publish operation `op-2026-08-01T082221679621900Z-bdfeb32d-6378-404e-af3c-3bb8b8407300`，远端运行态和 cleanup 证据均通过。

## 2026-08-02 仅测试服 r260802a 发布 payload 与历史失败记录门禁

### Trigger

仅测试服发布使用运行控制台 API 发起 `publish-test`，或发布前远端只读检查发现 `infra_release_migration` 中存在旧 releaseTag 的 `FAILED` 记录。

### Preflight check

- `publish-test` 请求体必须使用最小有效 payload：`action`、`reason`、`releaseTag`；不要携带 `includeOnlyOffice`、`includeShowroomBuildPackage`、`publishScope` 等 build-only 字段。
- 发布前只读检查必须区分两类 migration：当前目标 releaseTag 的 `FAILED/RUNNING` 行必须为 `0`；历史旧 releaseTag 的 `FAILED` 行需记录但不直接阻塞当前 code-only 发布。
- 版本变更说明校验不得只查发布包根目录；必须按顺序核 `manifest.json` changeSet、前端镜像或远端 `/release-info.json`、运行控制台 `release-status`。

### Blocker

- `publish-test` preview 返回 `msg=includeOnlyOffice`、`publishScope` 或其他 action schema 错误且未重新预览通过。
- 当前目标 releaseTag 的 migration `FAILED/RUNNING` count 不为 `0`。
- `release-info.json`、manifest changeSet、运行控制台 release-status 不能证明同一 releaseTag 的版本号和变更说明。

### Verification

- preview 结构化参数显示 `Mode=deploy-release`、`Environment=test`、`ReleaseTag=<target>`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，且无正式/备份动作。
- 远端验收保存 `.env IMAGE_TAG`、backend/frontend image tag、health、HTTP、release-info、release lock、当前 releaseTag migration status；历史 failed migration 单独记录 releaseTag 和原因。
- 运行控制台 release-status 显示 `testCurrentReleaseTag=<target>`、summary、changes、sourceRepos dirty=false。

### Forbidden action

- 禁止把 build-only 字段塞进 publish-test payload 后忽略 preview 失败继续发布。
- 禁止因历史旧 releaseTag 的 FAILED migration 行存在就手工改库、清空迁移表或误判本次发布失败；也禁止忽略当前 releaseTag 的 FAILED/RUNNING。
- 禁止只用 HTTP 200 或 package root 文件存在性替代版本变更说明验收。

### Evidence

- `doc/tasks/20260802-head-test-only-release/`；releaseTag `release-20260802-intmain-head-test-r260802a-r1`；build operation `op-2026-08-01T164440373170300Z-e1e28b57-392e-4329-9a0f-7c6e1541cbe9`；publish operation `op-2026-08-01T170326581868700Z-f11be1e5-4e3b-4335-9730-2c989e8800f5`；远端运行态、release-status 和 Playwright 页面证据均通过。

## 2026-08-02 09:58 后 r260802b 仅测试服重新上传门禁

### Trigger

用户要求“重新上传一遍”且明确不接受某个时间点之前的发布实现、operation、截图或 closeout 结论作为完成证据。

### Preflight check

- 新建独立任务目录并写明时间边界；旧 releaseTag 只能作为发布前状态或历史背景，不得作为完成证据。
- 重新冻结当前维护仓和主程序仓 HEAD；主工作区 dirty 时必须创建本轮专用 clean release worktree。
- 使用新 releaseTag 重新完成同一条 `build-release -> publish-test` 链路；发布后只接受同一 releaseTag 的 operation、manifest、远端运行态、release-status 和页面证据。
- 发布前后均记录测试服当前 tag、目标 releaseTag 的 migration `FAILED/RUNNING` 数量、历史旧失败 migration 数量和 release lock 状态。

### Blocker

- 任一完成证据来自用户指定时间边界之前。
- build-release、publish-test、manifest、远端 `.env`、实际镜像、release-info、release-status 或页面可见版本号不属于同一 releaseTag。
- 出现 `mark-tested`、`promote-prod`、`promote-backup` 或正式/备份服部署动作。

### Verification

- 任务日志记录新冻结 HEAD、worktree 路径、build operation、publish operation、manifest sourceRepos dirty=false、远端 `.env IMAGE_TAG`、backend/frontend image tag、container running、backend health `UP`、frontend HTTP `200`、release lock `APPLIED`、目标 migration failed/running `0`。
- 运行控制台页面必须显示当前 releaseTag、发布包、组件范围和变更说明，且 Playwright console errors/failed requests 为空。

### Forbidden action

- 禁止把旧成功 releaseTag 的截图、operation 或 closeout 结论复用为本次重新上传成功。
- 禁止因主分支后续继续更新而追逐新提交；构建发布只认发布开始时记录的冻结 worktree HEAD。
- 禁止只用 HTTP 200、`.env` 单项或 operation summary 替代完整运行态验收。

### Evidence

- `doc/tasks/20260802-0958-head-test-only-release/`；releaseTag `release-20260802-intmain-head-test-r260802b-r1`；maintenance HEAD `b25214b3de563aa83e3bac9eacf401da49c5f476`；app HEAD `b99246f58ff7d556caee24307ec89b662d0427e3`；build operation `op-2026-08-02T021129767983200Z-e204dce2-6be8-4a13-9428-063c4070ae40`；publish operation `op-2026-08-02T022945019393Z-852720a9-61ba-4c79-8cc5-245ced64c078`；远端运行态、release-status、前端页面和运行控制台页面证据均通过。

## 2026-08-02 反馈修复测试服发布与业务数据分层门禁

### Trigger

仅测试服发布用于验证“本机修复已进入测试服”，并且后续还要用真实 Excel、真实租户或真实业务流程验证功能结果，例如第三方报工 `李萍.xlsx`、`WORK_ORDER_NOT_FOUND`、`ACTIVE_TASK_NOT_FOUND`、运行控制台版本变更说明。

### Preflight check

- 发布验收必须先证明同一 releaseTag 的 clean worktree HEAD、manifest sourceRepos、远端 `.env`、实际镜像、health、HTTP、release-info、release lock、migration 和真实页面版本说明一致。
- 前端 `/release-info.json` 必须包含 `changeSet.gitChanges` 或等价用户可见变更项；只有 manifest 有 changeSet 不够，因为版本说明对话框读取的是前端 release-info。
- 业务 Excel 验证前必须按租户只读检查样例行的工单、排产工单、活动任务、工序、工位和报工用户覆盖情况；缺少任一业务前置数据时，先记录业务数据阻塞，不把它混同为发布失败。
- 测试租户和芋道源码租户的验证结论必须分开；测试租户缺工单、芋道源码缺活动任务或用户都应分别记录。

### Blocker

- release-info 缺少当前 releaseTag、sourceRepos commit、dirty=false 或 `changeSet.gitChanges`。
- `.env`、实际镜像、release-info、release lock 或 migration 任一项不属于同一 releaseTag。
- 业务验证出现 `WORK_ORDER_NOT_FOUND`、`ACTIVE_TASK_NOT_FOUND`、`PROCESS_NOT_FOUND`、`WORKSTATION_NOT_FOUND`、`FEEDBACK_USER_NOT_FOUND` 等前置数据缺口且未先归类记录。

### Verification

- 发布成功证据记录 releaseTag、worktree 路径、目标提交、manifest path、远端 `.env IMAGE_TAG`、backend/frontend image tag、backend health、frontend HTTP、remote `/release-info.json`、release lock、migration status 和 Playwright 版本对话框。
- 业务 Excel 验证证据记录租户、账号、上传文件、submitted/imported/skipped 计数、失败原因分布，以及只读数据覆盖查询结果。

### Forbidden action

- 禁止把业务数据缺口解释为“发布没生效”，也禁止把发布成功解释为“业务导入一定通过”。
- 禁止为了让 Excel 验证通过而手工改测试库、跨租户借数据、用接口或 SQL 代替真实前端上传，除非用户明确授权数据修复范围。
- 禁止 release-info 没有变更说明时降级为只看 HTTP 200 或 manifest。

### Evidence

- `doc/tasks/20260802-commit-feedback-fix-test-release/`；最终 releaseTag `release-20260802-feedback-fix-test-r260802h-r1`；源提交 `f0c34dfed910f52f9c03b401e976cbd2d0424e00`；运行态和版本说明通过，`李萍.xlsx` 业务导入阻塞于测试服数据前置条件。
