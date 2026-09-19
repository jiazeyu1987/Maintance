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
- 后端 release migration metadata gate 是否通过；以运行控制台 preview 返回的维护仓实际 `ops/release/run-release-migration-policy-gate.py` 为主，app 仓 `script/release/run-release-migration-policy-gate.py` 只作辅助。
- 主程序冻结 HEAD 的 migration type 去重集合，是否全部包含在维护仓 Python policy gate 与 `publish-int-ruoyi.ps1` 的相同允许集合中；新增类型是否已同步提交两个 parser 和契约测试。
- 可执行迁移（`schema/data/menu/config/permission/seed`）是否依赖 evidence-only 迁移（`preflight/backfill/postflight/rollback-dry-run`）；实际 ops gate 报 `executable migration cannot depend on evidence-only migration` 时必须在 build-release 前停止。
- code-only 过滤后的可执行迁移依赖闭包是否完整；任一将执行的 schema/menu/config/permission/seed 迁移都不得直接或传递依赖 preflight=`APPLY` 但会被 scope 过滤的 `type=data` 迁移。data 祖先已真实 APPLIED 时仍应对关键 live-state 断言做只读探针，不能只信台账。
- code-only 发布是否明确 `-Component intruoyi`、`SkipDatabaseSync`、`SkipMinioSync`。
- 测试服已知 required SQL 前置数据冲突是否已只读检查。

### 推荐命令

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:48181/actuator/health
python -X utf8 <maintenance-release-worktree>\ops\release\run-release-migration-policy-gate.py --help
python -X utf8 <maintenance-release-worktree>\ops\release\run-release-migration-policy-gate.py --sql-root <app-release-worktree>\IntRuoyiBackend\sql\mysql --file-prefix sql/mysql --output <task-dir>\ops-migration-policy-gate.json
corepack pnpm@10.25.0 --version
```

### Fail Fast

- 维护控制台不是本轮 Jar 或健康检查不是 `UP`。
- SQL metadata 缺失、`dependsOn` 错误、type 不在允许枚举，或 `rollback-migration` 脚本混入发布 SQL 扫描根但未被正式 parser/manifest/测试支持。
- 主程序 SQL、维护仓 Python gate、维护仓 PowerShell parser 的 migration type 集合不一致；尤其出现 `invalid type ... backfill` 时必须在依赖恢复和 build-release 前停止。
- app 仓 gate PASS 但实际维护仓 ops gate FAIL；以实际 ops gate 为准阻塞，不得继续构建或发布。
- code-only 过滤后存在 `APPLY executable -> pending filtered data` 的直接或传递依赖，或迁移台账显示已应用但 SQL 要求的关键 live state 不成立。
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
- Evidence: `doc/tasks/20260729-head-test-only-release/execution-log.md`；`publish-test` operation `op-2026-07-29T024258673743700Z-1774cd02-0579-420e-86eb-bcd0ed97475a` failed 后 `.env IMAGE_TAG=release-20260729-intmain-head-test-r260729a-r1`，但 backend/frontend 容器仍运行 `release-20260728-codeonly-noonlyoffice-test-r2`。2026-08-01 追加证据：`doc/tasks/20260801-head-test-only-release/execution-log.md`；`publish-test` operation `op-2026-07-31T184648151088Z-d51572f6-9207-44dd-bbab-6f54c347cea4` failed 后 `.env IMAGE_TAG=release-20260801-intmain-head-test-r260801a-r2`，backend/frontend 实际容器仍运行 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`，release lock=`FAILED`，migration `FAILED=1`。2026-08-03 追加证据：`doc/tasks/20260803-head-test-only-release/execution-log.md`；`publish-test` operation `op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241` failed 后 `.env IMAGE_TAG` 短暂变为 `release-20260803-intmain-head-test-r260803a-r1`，backend/frontend 实际容器仍为 `release-20260802-feedback-fix-test-r260802h-r1`，release lock=`FAILED`，migration `FAILED/RUNNING=1`；失败收束时仅恢复 `.env IMAGE_TAG` 到实际运行 tag，不改 release lock/migration，不宣称发布成功。

### publish-test 失败后镜像已切换但后端启动失败门禁

- Trigger: `publish-test` operation 非 `SUCCESS`，且失败后 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 已等于目标 releaseTag，但 backend health 失败或容器持续重启。
- Preflight check: 失败冻结时必须同时记录 operation final、release lock、migration status、`.env IMAGE_TAG`、backend/frontend image tag、`docker compose ps`、backend health、frontend HTTP、frontend `/release-info.json` 和 backend `docker logs --tail`；如果镜像已切换但 backend health 失败，必须把该 releaseTag 判废。
- Blocker: operation 非 `SUCCESS`；release lock=`FAILED`；backend health 非 `UP`；backend 日志存在 `Application run failed`、`UnsatisfiedDependencyException`、`No default constructor found`、`BeanCreationException` 或同类 Spring context 启动失败。
- Verification: 证据必须显示前端 HTTP 与 release-info 不能覆盖 backend health 失败；只有 operation=`SUCCESS`、lock=`APPLIED`、backend health=`UP`、migration `FAILED/RUNNING=0` 全部满足，才可进入运行控制台页面版本验收。
- Forbidden action: 不得因 `.env` 和实际镜像 tag 已等于目标 releaseTag 就宣称测试服发布成功；不得手工改 release lock/migration 或复用失败 releaseTag；不得在未授权时回滚或重试。
- Evidence: `doc/tasks/20260806-head-test-only-release/`；`release-20260806-intmain-head-test-r260806b-r2` publish operation `op-2026-08-06T114908393935900Z-ded107d0-7996-4d3f-b7b4-ceadb49e489a` failed 后 `.env` 与实际镜像均为 r2，frontend HTTP 200，但 backend health curl exit=56，release lock=`FAILED`，后端日志显示 `MesTeamLeaderProcessConfigServiceImpl` 多构造函数缺显式 `@Autowired` 导致 `No default constructor found`。

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

## 2026-08-03 required SQL 修复后仅测试服 r260803b 成功闭环门禁

### Trigger

仅测试服发布在上一轮失败于 required SQL checksum 漂移、菜单固定 ID、`.env` 与实际镜像短暂漂移后，修复 SQL 并使用新 releaseTag 重新发布。

### Preflight check

- 失败 releaseTag 必须判废；修复后用新 releaseTag 重新 `build-release -> publish-test`，不得复用失败包或旧运行态证据。
- 发布前必须运行远端只读 precheck：无 RUNNING test lock、目标 releaseTag migration FAILED/RUNNING=0、backend health 和 frontend HTTP 仍正常。
- 发布后必须同时核 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health、frontend HTTP、`/release-info.json` sourceRepos、release lock、target migration 和运行控制台“版本变更说明”。
- 长时间 `RUNNING` 时先看脱敏 operation log 是否持续推进；镜像分片上传和逐文件 required SQL scp 属于正常长耗时阶段，不得仅凭轮询次数判定失败。

### Blocker

- 任一完成证据来自失败 releaseTag 或不同 releaseTag。
- `publish-test` preview 不指向 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`。
- 当前 releaseTag 的 release lock 不是 `APPLIED`，或 migration `FAILED/RUNNING` 不为 `0`。
- 运行控制台页面不显示本轮 releaseTag 或变更说明。

### Verification

- 记录 build operation、publish operation、manifest summary、前端镜像 release-info、remote pre/postcheck、运行控制台 Playwright 弹窗和测试服前端页面截图。
- 运行控制台页面验收至少确认测试服 releaseTag、版本号、发布包、组件范围；source commit 以 manifest 和 `/release-info.json` 作为机器证据。

### Forbidden action

- 禁止因测试服 frontend HTTP 200 就跳过镜像 tag、release-info、lock/migration 和页面版本说明验证。
- 禁止用 `.env IMAGE_TAG` 单项替代实际容器镜像。
- 禁止在仅测试服任务中执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

### Evidence

- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/`；releaseTag `release-20260803-dcc-menu-replay-fix-test-r260803b-r1`；build operation `op-2026-08-03T014004195140200Z-27256ee2-7aa4-4539-a982-044bd4f86239`；publish operation `op-2026-08-03T020027072659300Z-324edfd7-4658-4822-89ed-0e35e37f7feb`；remote postcheck 与运行控制台版本变更说明均通过。

## 2026-08-06 r260806c 仅测试服成功闭环门禁

### Trigger

仅测试服发布在上一轮失败 tag 已切换镜像但后端启动失败后，用户确认修复已提交，需要用新 clean release worktree 和新 releaseTag 恢复测试服。

### Preflight check

- 失败 releaseTag 必须判废；修复后重新冻结当前 HEAD 到本轮专用 clean release worktree，并使用新 releaseTag 完整执行 `build-release -> publish-test`。
- build-release 前增加 Spring constructor/static smoke 门禁；多构造函数 Spring bean 必须有唯一显式 `@Autowired` 生产构造函数或明确无参构造函数。
- publish-test 前做远端只读 precheck；旧失败 `.env` / image tag 可作为背景记录，但必须确认无 RUNNING lock 后才允许发布新 tag。
- 发布后必须同时核 operation、manifest/sourceRepos dirty=false、`.env IMAGE_TAG`、实际镜像、容器 running、backend health、frontend HTTP、release-info、release lock、target migration 和运行控制台版本变更说明。

### Blocker

- 任一完成证据来自失败 releaseTag 或不同 releaseTag。
- Spring constructor gate 未通过，或 backend health 非 `UP`。
- publish-test preview 不是 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`。
- 运行控制台页面不显示当前 releaseTag、发布包、组件范围或变更说明。

### Verification

- 记录 build operation、publish operation、manifest validation、remote pre/postcheck、Playwright JSON 和截图。
- 成功证据必须显示 release lock=`APPLIED`、target migration failed/running=`0`、frontend console errors/failed requests=`0`、runtime console errors/failed requests=`0`。

### Forbidden action

- 禁止复用已失败的 r260806b-r2 releaseTag。
- 禁止手工改 release lock/migration 或用前端 HTTP 200 覆盖 backend health 失败。
- 禁止在仅测试服任务中执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

### Evidence

- `doc/tasks/20260806-head-test-only-release/`；releaseTag `release-20260806-intmain-head-test-r260806c-r1`；build operation `op-2026-08-06T131808382264900Z-1a134a91-d2eb-434d-b0a6-b0da5018a2f7`；publish operation `op-2026-08-06T134301524868800Z-58d50c52-dab5-43b8-8ce9-81849d0c96ef`；`remote-release-postcheck-r260806c-r1.json` 与 `playwright-runtime-console-r260806c-r1.json` 均通过，未执行正式服、备份服或 mark/promote。

## 2026-08-08 运行控制台 release-status 等待与端口隔离验收门禁

- Trigger: 仅测试服发布完成后，需要用运行控制台页面验证当前 releaseTag、发布包、组件范围和变更说明；页面底部显示“加载中”；或因 48181 已被主维护控制台占用/进程管理策略限制，临时在其它端口启动本轮 release worktree 控制台。
- Preflight check: 页面验收前先用实际控制台端口只读调用 `/admin-api/infra/runtime-control/release-status`，确认 `testCurrentReleaseTag`、`testCurrentReleaseNotes.changes`、`sourceRepos.commit` 和 `dirty=false` 已返回；Playwright 页面脚本必须等待目标 releaseTag 出现在 `document.body.innerText` 后再点击“查看变更”，不能只截取初始“加载中”状态。
- Blocker: release-status API 不含目标 releaseTag/变更说明；页面等待 60 秒仍不显示目标 releaseTag；“查看变更”对话框不显示版本号、发布包或组件范围；页面 console error / failed request 非 0；控制台 preview 的 `repo-root` / `frontend-root` 未指向本轮 clean worktree。
- Verification: 记录实际控制台端口、release-status JSON、Playwright JSON、截图路径、前端 HTTP 200、运行控制台 HTTP 200、releaseTagVisible/packageVisible/componentVisible/changeNotesVisible、consoleErrors 和 failedRequests。
- Forbidden action: 禁止把 API 已返回 releaseTag 但页面仍“加载中”的初始截图当作页面验收通过；禁止因端口隔离而省略运行控制台页面验证；禁止用接口验证替代“查看变更”真实页面对话框。
- Evidence: `doc/tasks/20260808-head-test-only-release/playwright-runtime-console-r260808a-r1.json`；首次脚本等待不足失败，重试等待 releaseTag 后通过，截图位于 `output/playwright/r260808a-release/`，releaseTag=`release-20260808-intmain-head-test-r260808a-r1`。

## 2026-08-08 publish-test 长 migration 状态写入进度门禁

- Trigger: `publish-test` 长时间 `RUNNING`，operation summary 长期停留在“命令已提交到本机执行队列”，但脱敏日志持续输出 required SQL 上传或 `infra_release_migration` 逐条状态写入。
- Preflight check: 长阶段每隔固定时间读取 operation JSON 和脱敏 log tail；判断进度以日志阶段为准，区分“仍在推进”和“无新增日志卡死”；记录当前阶段、耗时原因和下一步等待/诊断动作。
- Blocker: operation 非 SUCCESS；log tail 长时间无新增且远端存在 RUNNING lock；日志出现 MySQL/SSH/scp/docker health 失败；无法确认是否仍在同一 releaseTag 上推进。
- Verification: publish-test 结束后必须独立 postcheck：operation=SUCCESS、release lock=APPLIED、migration failed/running=0、`.env`/实际镜像/容器/health/HTTP/release-info 均匹配目标 releaseTag。
- Forbidden action: 禁止因 summary 未更新而重复提交 publish-test；禁止中断仍在推进的 required SQL/migration 状态写入；禁止只看 `Publish completed for test` 文本而跳过独立 postcheck。
- Evidence: `doc/tasks/20260808-head-test-only-release/publish-test-log-tail-r260808a-r1.redacted.txt`；poll 15/30/45 仍为 RUNNING，但日志从 required SQL 上传推进到 migration 状态写入，最终 poll 59 SUCCESS。
## 2026-08-10 r260809a 仅测试服成功闭环与长 operation 门禁

- Trigger: 从冻结 clean worktree 对单一 releaseTag 执行 `build-release -> publish-test`，且 required SQL/migration 数量较多导致 operation 长时间保持 RUNNING、摘要变化少。
- Preflight check: 发布前固定 releaseTag、build/publish operation scope、测试服 host 和远端目录；manifest 必须核 source commit/dirty、artifact hash、release-info 和 changeSet。publish-test 提交后保持唯一 operation id，按 operation 状态、日志最后推进时间、当前 migration 文件和状态表计数判断进展。
- Blocker: manifest 任一来源/版本/变更说明无法确认；operation 日志和 migration 状态均超过既定超时无推进；出现 FAILED；或 `.env IMAGE_TAG`、实际镜像、容器、health、HTTP、release-info、lock/migration、运行控制台任一验收不一致。
- Verification: build operation 和 publish operation 均 SUCCESS；测试服 `.env` 与 backend/frontend 实际镜像匹配，容器 running、backend health=UP、frontend HTTP 200、release lock=APPLIED、migration failed/running=0；Playwright 打开测试服页面和运行控制台，点击 `查看变更` 后确认 releaseTag、发布包和组件说明，无 console error/failed request。
- Forbidden action: 不得因摘要长时间不变而重复点击或重提 publish-test；不得把本机实例矩阵代替测试服远端验收；不得执行 `mark-tested`、`promote-prod`、`promote-backup`，不得写正式服或备份服。
- Evidence: `doc/tasks/20260809-head-test-only-release/`；releaseTag `release-20260809-intmain-head-test-r260809a-r1`，build operation `op-2026-08-09T154417143232100Z-1cbd9f9c-35e8-4b3f-9cda-1646af3f808f`、publish operation `op-2026-08-09T155709667969700Z-6d3f54cc-4892-4b0e-8c49-624bacd79bfe` 均 SUCCESS；publish 约 24 分钟且没有重复提交。

## 2026-08-11 r260811a 仅测试服成功闭环与脱敏页面验收门禁

- Trigger: 仅测试服发布完成后，需要同时证明远端真实运行态、运行控制台版本变更说明和页面验收，且 Playwright snapshot 可能暴露登录页默认凭据。
- Preflight check: publish-test 只允许 action=`publish-test`、Environment=`test`、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`；页面验收优先用 Playwright CLI `open/eval/screenshot` 采集脱敏结构化结果，登录页 snapshot 原文不得留存。
- Blocker: `.env IMAGE_TAG`、实际镜像 tag、release-info、release lock、migration counts 或运行控制台页面版本说明任一项不匹配 releaseTag；snapshot/日志中出现默认密码或 raw secret。
- Verification: 记录 publish operation SUCCESS、backend/frontend running、health UP、frontend HTTP 200、PDF worker 200、release-info sourceRepos dirty=false、lock APPLIED、migration FAILED/RUNNING=0、运行控制台可见软件版本、测试服 releaseTag、发布包和组件范围。
- Forbidden action: 禁止用前端 HTTP 200 替代 release-info/lock/migration/运行控制台页面验收；禁止保存含默认密码的 Playwright snapshot；禁止执行 mark-tested/promote-prod/promote-backup。
- Evidence: `doc/tasks/20260811-head-test-only-release/execution-log.md`；releaseTag `release-20260811-intmain-head-test-r260811a-r2`；publish operation `op-2026-08-10T184419479334Z-b3dd4c79-c0f1-4a8c-bc32-5a930700a511`。

## 2026-08-13 DCC 活跃上传槽与运行控制台配置门禁

- Trigger: `publish-test` 包含 `20260811_dcc_upload_slot_idempotency.sql`，或 release worktree 控制台用于验收测试服版本号和“查看变更”。
- Preflight check: 远端写入前按迁移真实口径查询 `dcc_controlled_file_temporary_file`：`deleted=0 AND status='AVAILABLE' AND cleanup_status IN ('ACTIVE','CLEANING') AND bound_controlled_file_id IS NULL`，按 tenant/uploader/session/purpose 分组必须无重复；启动隔离控制台前同时校验 `maintenance.runtime-control.backup-ops` 与 `release-package` 的 NAS server/share/username/password/root 必填项，凭据只做 presence check；Playwright 等待目标 releaseTag 出现后再点“查看变更”。
- Blocker: 活跃上传槽存在重复；无法确认应该保留哪一条；未生成逐行备份和回滚 SQL；隔离控制台缺任一 NAS 配置块；页面虽有 SUCCESS operation 但测试服版本为“未上报”或版本对话框缺变更项。
- Verification: 重复组查询结果为 0；如经用户授权修复，必须证明事务 affectedRows 精确为 1、保留行与清理行、回滚材料和迁移重试结果；页面六个 API 均 200，版本栏、版本号、发布包与组件范围可见；远端 `.env`、实际镜像、Actuator、HTTP、release-info、lock 和 migration 独立全绿。最终控制台复核固定使用 `/admin-api/infra/runtime-control/release-status`，同时校验 `testCurrentReleaseTag`、`testCurrentReleaseNotes.releaseTag`、`changes`、48181 PID 和启动参数；误用简写路由或 404 只能记为校验假阴性并按真实路由重查。
- Forbidden action: 禁止发布脚本自动选择并删除/清理重复业务行；禁止无用户授权修改测试数据；禁止用 release-status API 已成功替代真实页面；禁止因 rollback/restore 候选接口失败而把测试服版本“未上报”降级为可接受。
- Evidence: `doc/tasks/2026-08-11-test-only-release-head/execution-log.md`；releaseTag=`release-20260813-intmain-head-test-r260812b-r2`，publish operation=`op-2026-08-13T001732036464300Z-1541e376-2561-40b8-82c8-77c33bcfda17`。

## 2026-08-13 发布后探针契约、稳定控制台与收尾门禁

- Trigger: `publish-test` 已返回 SUCCESS，准备运行独立远端探针、恢复 48181 稳定控制台、执行 Playwright 最终复验或删除 release worktree/state。
- Preflight check: 远端 SQL 探针先从冻结 migration 和真实库 `DESCRIBE` 确认表名/字段；先读 compose 判断容器是否定义 Docker healthcheck，未定义时容器门禁只核 `state=running`，应用健康独立核 Actuator HTTP 200/UP。删除 release worktree 前，主 `runtime-control.local.yaml` 的 repo/frontend/ops/state 必须符合当前固定根，48181 的 PID/命令行/JAR 必须指向主维护路径，完整 `/admin-api/infra/runtime-control/release-status` 必须返回目标 tag 和变更说明；同一 Playwright CLI 会话的 open/resize/snapshot/click/find/console/close 必须串行执行。每次实际构建单独记录 JAR hash，不把同 HEAD 的历史重建 hash 当作当前产物固定值。
- Blocker: 探针凭推断使用表名/字段；把未定义 healthcheck 的 `health=none` 当成应用失败或健康成功；主控制台配置仍指向废弃 repo/frontend 路径；48181 仍引用 release worktree、主路径 JAR/state 只显示旧版本、release-status 缺目标变更说明；Playwright 出现 `ECOMPROMISED Lock compromised` 且尚未串行重验；task-closeout preview 把 workspace 外 worktree/state 列为 blocked；或当前 JAR 来源/当次 hash 无法证明。
- Verification: 远端 `.env`、实际镜像、容器 running、Actuator UP、frontend HTTP 200、release-info、lock/migration 和业务探针均按真实契约通过；48181 health=UP、PID/命令行指向主维护路径、release-status 的 `testCurrentReleaseTag`/notes/changes 匹配目标；Playwright 页面版本与 console errors=0 串行复验通过；外部 worktree/state 按 `E:\IntRuoyi\docs\worktree-memory.md` 清理后，task-closeout preview/apply 的 blocked/warnings 均为空。
- Forbidden action: 禁止臆造数据库表、Docker healthcheck 或简写 API 路由；禁止用旧稳定控制台 health=UP 替代当前版本/变更说明；禁止跨重建强求历史 JAR hash 相同；禁止并行启动同一 npm cache 下的多个 Playwright CLI 命令；禁止绕过 task-closeout workspace 边界或扩大删除到其它任务路径。
- Evidence: `doc/tasks/2026-08-11-test-only-release-head/execution-log.md` 的 `postcheck-probe-contract`、`main-runtime-stale-jar-state`、`maintenance-jar-hash-nondeterminism`、`playwright-npm-lock-contention`、`task-closeout-outside-workspace`、`worktree-remove-directory-not-empty` 和 `final-runtime-status-wrong-route`。

1. 阶段 1：独立远端探针
   必查项：冻结 SQL/`DESCRIBE`、compose healthcheck、容器 state、Actuator、HTTP、release-info、lock/migration。
   推荐命令：`rg <table-or-field> <frozen-migration>`、远端 `DESCRIBE <table>`、`docker compose ps --format json`、`curl -fsS <backend>/actuator/health`。
   Fail Fast：schema/compose 契约不明、任一真实运行态字段不匹配目标 releaseTag。
   必须记录：探针依据、容器状态、Actuator/HTTP、迁移计数和业务冲突计数。

2. 阶段 2：稳定控制台与页面复验
   必查项：主 local config 的 repo/frontend/ops/state 固定路径、48181 PID/命令行/JAR 路径、当次 JAR hash、主 state 中本次 operation、完整 release-status 路由、目标 tag/notes/changes。
   推荐命令：`Get-NetTCPConnection -LocalPort 48181 -State Listen`、`Get-CimInstance Win32_Process`、`Get-FileHash <jar> -Algorithm SHA256`、`Invoke-RestMethod http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status`。
   Fail Fast：主路径控制台仍显示旧版本、来源 JAR/operation state 无法证明、页面版本对话框或 console 验收失败。
   必须记录：PID、命令行、JAR hash、release-status 关键字段和串行 Playwright 结果。

3. 阶段 3：外部 worktree 与任务 closeout
   必查项：Git 注册、固定物理路径、state dir、进程引用、task-closeout workspace 边界。
   推荐命令：两仓 `git worktree list --porcelain`、固定路径 `Test-Path`、进程命令行扫描、`task_closeout.py --mode preview`。
   Fail Fast：存在未合并提交/dirty、`.git`、归属不明进程、路径越界、preview blocked/warnings 非空。
   必须记录：每个路径的 registered/existsAfter、稳定控制台最终状态和 task-closeout preview/apply 结果。

## 2026-08-16 code-only 迁移依赖闭包与真实状态门禁

- Trigger: `publishScope=code-only` 会跳过 `type=data` required SQL，同时存在依赖这些迁移的 schema/menu/config/permission/seed 迁移，或迁移脚本使用 `SIGNAL SQLSTATE '45000'` 校验菜单、配置、权限等 live state。
- Preflight check: 从 Manifest v1 `migrationPlan`/`requiredSql` 和 target preflight action 计算 code-only 过滤后的传递依赖闭包；对每个待执行迁移，若任一祖先是 preflight=`APPLY` 且会因 `type=data` 被过滤，必须在远端写入前阻塞。对 SQL 中固定 ID、parent/path、唯一键或状态断言生成只读查询，同时比较 migration ledger 与真实表状态，不能只看 `SKIPPED_ALREADY_APPLIED`。
- Blocker: 出现 `APPLY executable -> pending filtered data` 依赖；ledger 标记 APPLIED/已应用但 live state 不满足后续迁移；无法从当前冻结提交证明正式修复方案；或失败 releaseTag 已产生 APPLIED/FAILED 部分记录。
- Verification: 保存最小依赖链、相关 Manifest 条目、远端只读 state probe、目标 release lock 与 migration counts。修复后必须新增 policy/contract tests，提交正式源码，从新冻结 HEAD 构建新 releaseTag，再完整执行测试服发布。
- Forbidden action: 禁止手工把测试库调整成预期形态后继续失败 tag；禁止改 migration ledger、把 data 类型随意改成 schema、复用失败发布包、重复提交同一 operation，或用旧容器 health/HTTP 200 掩盖目标镜像未上线。
- Evidence: `doc/tasks/20260816-test-only-release-head/`；`20260721_form_center_menu_under_basic_data` 为 `type=data`，后续 menu 迁移依赖该状态；失败时菜单仍位于旧父级，release lock=`FAILED`，`.env` 与实际镜像不一致。

1. 阶段 1：Manifest 依赖闭包
   必查项：`publishScope`、migrationId/type/dependsOn、code-only 执行集合、被过滤祖先。
   推荐命令：使用 `ConvertFrom-Json`/JSON parser 读取 `manifest.json` 的 `migrationPlan` 与 `requiredSql`，输出最小依赖链；禁止用日志全文搜索代替结构化解析。
   Fail Fast：任一待执行迁移传递依赖 pending 且会被 scope 过滤的迁移。
   必须记录：待执行节点、被过滤祖先、最小依赖路径和 Manifest checksum。

2. 阶段 2：迁移台账与 live state 对照
   必查项：目标环境 `infra_release_migration` 状态、SQL 的固定 ID/parent/path/唯一键断言、真实表当前值。
   推荐命令：先按真实库 `DESCRIBE`，再运行只读 `SELECT`；菜单迁移至少核 `system_menu.id/name/parent_id/path/type/deleted`。
   Fail Fast：ledger 与 live state 不一致，或 live state 前置缺失。
   必须记录：脱敏 SQL 意图、ledger 状态、真实值、期望值和差异。

3. 阶段 3：失败后的版本漂移冻结
   必查项：operation、release lock、migration failed 行、`.env IMAGE_TAG`、Compose images、实际镜像、health/HTTP、release-info。
   推荐命令：运行任务内只读 post-failure probe；operation 日志仅取脱敏摘要。
   Fail Fast：任一目标版本证据未通过；失败 tag 已产生部分迁移记录。
   必须记录：失败迁移、状态计数、实际运行版本与禁止重试结论。

## 2026-08-21 r260821h-r4 失败态漂移与 Spring context 门禁

### 门禁摘要

- Trigger: `publish-test` 失败发生在 required SQL、route snapshot BACKFILL/READINESS 或其它容器前置运行报告阶段；日志出现 `No default constructor found`、`Application run failed`、`InvalidDefaultArgInFrom` 或 MySQL 密码命令。
- Preflight check: publish-test 写入前保存远端 `.env` 的脱敏 hash/来源、当前 compose 解析镜像和实际容器镜像；build-release 前扫描 Docker warning，并执行 Spring context smoke 或多构造函数 Spring Bean 静态检查；operation log 只能记录脱敏命令摘要。
- Blocker: operation 非 `SUCCESS`；`.env`/compose/实际镜像/release-info 任一漂移；Spring context 启动失败；raw log 含密码/token；或失败 tag 已产生迁移部分状态且无法证明恢复基线。
- Verification: 失败冻结同时记录 operation final、`.env IMAGE_TAG`、`docker compose config --images`、`docker compose images`、`docker inspect`、容器状态、Actuator、前端 HTTP、`release-info.json`、release lock/migration 和脱敏日志扫描结果。
- Forbidden action: 不得因旧容器 health/HTTP 200 或 `.env` 已等于目标 tag 判成功；不得猜测旧 tag 回滚、手工改 release lock/migration、重试失败 tag、执行 mark-tested/promote；不得提交 raw operation log。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P026-P029；publish operation `op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b`；releaseTag `release-20260821-intmain-head-test-r260821h-r4`。

### 阶段 1：构建前运行契约

- 必查项：Dockerfile `FROM`/ARG warning、Spring Bean 多构造函数注入、发布 logger secret scan、旧 `.env` 可恢复性。
- 推荐命令：`rg -n "^FROM |ARG " <backend> <frontend> -g "Dockerfile*"`；对 Spring Bean 做构造函数静态扫描；对 log 样本扫描 `mysql -p`、`password=`, `token=`。
- Fail Fast：`InvalidDefaultArgInFrom` 未解释；多构造函数无唯一显式 `@Autowired`；日志出现 secret 形态；无法保存旧 `.env` hash/恢复路径。
- 必须记录：warning 摘要、目标 Bean、logger 脱敏测试、旧 env 证明和自动恢复路径。

### 阶段 2：失败收束

- 必查项：同一 operation 状态、失败日志阶段、远端 env/compose/actual images、容器/health/HTTP/release-info、lock/migration。
- 推荐命令：`docker compose config --images`、`docker compose images`、`docker inspect`、`curl -fsS /actuator/health`、`curl -fsS /release-info.json`。
- Fail Fast：env/compose/actual images 不一致、失败 tag 有部分迁移状态、或旧 env 基线不可证明。
- 必须记录：现象、阶段、影响、原因判断、处理动作、结果、前置检查、自动化方式、下次避免；失败 tag 判废且禁止重试。

## 2026-08-22 r260822a-r2 route snapshot blocker 与 operation 终态门禁

### 门禁摘要

- Trigger: `publish-test` 已通过构建/manifest 门禁，但 route snapshot BACKFILL/READINESS 报告返回 `BLOCKED`，或临时 backend runner 未退出、operation API 长时间保持 `RUNNING`。
- Preflight check: 发布前验证修复提交的真实 Spring context smoke；发布中记录报告 `status`/`blockerCount`、临时 runner 生命周期、operation 状态文件更新时间和命令执行器超时；logger 先完成 secret redaction 样例测试。
- Blocker: report `status != READY`、`blockerCount != 0`；临时 runner 未退出；operation 未进入明确 `SUCCESS`/`FAILED`；或 raw log 命中 `mysql -p`、`password=`、`token=`。
- Verification: 保存脱敏报告摘要、runner 创建/清理结果、operation JSON/API、日志 scan、live backend/frontend 实际 tag；发布成功仍必须满足 operation=`SUCCESS` 与全部运行态门禁。
- Forbidden action: 禁止因构造注入修复测试通过就跳过真实 BACKFILL/READINESS；禁止手工将 `RUNNING` 改为 `SUCCESS`；禁止修改业务数据/迁移台账消除 blocker；禁止重复提交同一 operation 或复用失败 releaseTag。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P038-P043；releaseTag=`release-20260822-intmain-head-test-r260822a-r2`；publish operation=`op-2026-08-22T035621436028400Z-55335b7f-e740-4d0f-a9d1-a85f875648fa`。

### 阶段 1：发布前运行报告

1. 必查项：修复提交的 Spring context smoke、route snapshot runner 参数、远端报告目录、logger 脱敏样例。
2. 推荐命令：项目内 `ApplicationContextRunner` 测试；远端只读读取 report `status`/`blockerCount`；本地 secret-pattern scan。
3. Fail Fast：Spring context 启动失败、报告非 READY、blockerCount 非 0、logger 输出 raw secret。
4. 必须记录：目标提交、测试命令、报告摘要、releaseTag、operation id、日志 scan 结果。

### 阶段 2：长 operation 与失败收束

1. 必查项：脱敏日志进度、operation JSON/API、command-timeout、临时 runner 状态、live 容器 tag。
2. 推荐命令：读取 operation state 与 log tail；远端 `docker inspect`/`docker ps` 只查询任务创建的 runner 与 live backend/frontend。
3. Fail Fast：无日志进展超过真实超时、runner 不退出、operation 不是明确终态、env/compose/actual image/release-info 漂移。
4. 必须记录：耗时阶段、进度计数、阻塞根因、清理边界、live 容器未受影响证据和下一步自动化动作。

## 2026-08-22 route snapshot 历史数据治理与租户范围门禁

### 门禁摘要

- Trigger: route snapshot BACKFILL/READINESS 已能启动，但报告返回 `BLOCKED`，尤其 blocker 来自历史快照结构、正式身份或多个租户。
- Preflight check: 远端写入前读取结构化报告并按 `reasonCode`、`routeVersionId`、租户分布聚合；按真实库 `DESCRIBE` 核对 `mes_pro_route_version` 与相关源表；区分芋道源码租户与测试租户；确认历史快照是不可变证据，不能从当前投影推断修复值。
- Blocker: `status != READY`、`blockerCount != 0`、存在受保护租户 blocker、无法提供正式历史快照治理/回滚方案，或有人提出排除租户、只写 hash、跳过 BACKFILL/READINESS 的降级路径。
- Verification: 保存原始报告的非敏感副本、status/scanned/updated/blockerCount、reasonCode counts、tenant counts、关键样本字段和零写入证明；修复后必须用新提交、新 worktree、新 releaseTag 重新执行完整 `build-release -> publish-test`。
- Forbidden action: 禁止修改芋道源码租户数据；禁止用当前路线/BOM 表重建不可变历史快照；禁止排除 tenant 1、修改 migration ledger/release lock、只写身份列、跳过门禁或复用失败 releaseTag。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P047；`evidence/route-snapshot-identity-backfill-r260822a-r2.json`；`evidence/route-snapshot-readonly-probe.sql`。

## 2026-08-22 route snapshot blocker 租户精确归属门禁

### 门禁摘要

- Trigger: route snapshot 报告包含 blocker，但报告 schema 只提供 `routeVersionId`、未提供 `tenantId`，或发布判断需要确认 blocker 是否落在受保护租户。
- Preflight check: 使用真实库只读查询 `mes_pro_route_version(id, tenant_id)`，按报告 `routeVersionId` 做完整关联；必须证明映射覆盖率为 100%，并按 `tenant_id/reasonCode` 输出计数。
- Blocker: 任一 blocker 无法映射、报告缺少关键 ID、关联退出码非 0、存在受保护租户 blocker，或有人提出只修测试租户/排除受保护租户来满足全租户门禁。
- Verification: 记录 SQL 意图、SSH exit code、报告 blocker 总数、映射总数、未映射数、租户与 reasonCode 聚合；不记录密码和 raw operation log。
- Forbidden action: 禁止只凭报告总数推断租户归属；禁止用 tenant filter、只写 hash、跳过 BACKFILL/READINESS 或修改受保护租户来伪造可发布状态。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P050；本轮 882 条 blocker 全部映射，tenant 1=881、tenant 122=1。

### 阶段必查项

1. 发布前运行报告：报告必须是结构化 JSON，聚合 `status`、`scannedCount`、`updatedCount`、`blockerCount`、reasonCode 和租户分布。
2. 数据契约核对：以真实库 `DESCRIBE` 和只读 SQL 为准；历史 snapshot 的结构/身份必须由自身证明，不能引用当前 projection 作为 fallback。
3. 失败收束：保持 operation 非成功、保留 worktree/报告，禁止同 tag 重试；若失败脚本已写 `.env`，另行验证 env/compose/actual image 漂移。

## 2026-08-24 r11 仅测试服发布终态与页面门禁

### 门禁摘要

- Trigger: 完成修复后重新执行同一 releaseTag 的 build-release -> publish-test，并准备判断测试发布成功。
- Preflight check: build operation SUCCESS；manifest/release-manifest、sourceRepos commit/dirty、前端 release-info、changeSet.summary 和 worktree HEAD 一致；publish preview 明确 environment=test、noPromotion=true。
- Blocker: build/publish operation 非 SUCCESS、远端 .env 与实际 image tag 不一致、容器非 running、Actuator 非 UP、frontend HTTP 非 200、release-info 缺 commit/dirty/changeSet、目标 release lock 非 APPLIED、目标 migration 存在 FAILED/RUNNING，或运行控制台版本说明无法展示时必须判定 NO-GO。
- Verification: 远端只读探针同时核对 .env、docker inspect、compose ps、health、frontend、release-info、latest releaseTag lock 和 migration；Playwright 真实打开测试前端入口并记录 title、HTTP/API、console errors；运行控制台打开版本变更说明核对 releaseTag、summary、commit，正式/备份保持未上报。
- Forbidden action: 禁止因 publish operation SUCCESS 跳过运行态；禁止把数据库锁内部 operation_id 与控制台 operation id 强行要求相等；禁止为页面验收猜测过期凭据、修改租户/账号或 API-only 冒充真实页面；禁止访问正式服和备份服。
- Evidence: 本任务 remote-runtime-r260823f10-r11.json、output/playwright/r11-test-frontend-login.png、output/playwright/r11-runtime-console.png、execution-log.md ISSUE-014/015/016。

## 2026-08-29 r260829j 仅测试服成功闭环、真实运行态与控制台版本门禁

### 门禁摘要

- Trigger: 用户明确要求“仅测试服发布”，需要从 clean release worktree 的同一 releaseTag 验证 `build-release -> publish-test`，并证明测试服真实运行态、前端页面、运行控制台版本号和变更说明。
- Preflight check: `publish-test` preview 必须是 action=`publish-test`、environment=`test`，禁止 `mark-tested`、`promote-prod`、`promote-backup`；发布后必须独立核 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、container running、backend Actuator UP、frontend HTTP 200、frontend `/release-info.json`、运行控制台 `/release-status` 和 Playwright 页面。
- Blocker: build/publish operation 非 SUCCESS；`.env`、实际镜像、release-info、manifest 或运行控制台任一 releaseTag 不一致；backend health 非 UP；frontend HTTP 非 200；运行控制台无法显示当前 releaseTag/发布包/组件范围/提交摘要；页面证据含默认密码或 raw secret；正式服或备份服被触发。
- Verification: 保存 `remote-runtime-check*.json`、`runtime-console-release-status*.json`、`playwright-verification*.json`、截图和最终 `test-release-final-gate*.json`；final gate 必须把 worktree clean、manifest、官方 validator、远端运行态、页面、控制台和禁止推广动作全部列为 true。
- Forbidden action: 禁止用 `publish-test` SUCCESS 代替真实运行态；禁止只看前端 HTTP 200；禁止把运行控制台 API 验收降级为页面未展开的初始状态；禁止保存含敏感输入值的 Playwright snapshot；禁止访问或发布正式服/备份服。
- Evidence: `doc/tasks/20260828-test-only-release-head/execution-log.md`；releaseTag `release-20260829-frozen-head-test-r260829j-r1`；build operation `op-2026-08-29T074248158573400Z-4ec035f6-02a6-49ee-a41c-c598d4cd2cee`；publish operation `op-2026-08-29T080003811407100Z-9e826bd7-61ca-44e3-bc28-f8a3794035bb`；final gate `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\test-release-final-gate-r260829j-r1.json`。

### 阶段 1：publish-test 前范围确认

1. 必查项：releaseTag、build package、preview action/environment、目标 test host、远端 runtime 目录、禁止动作 token。
2. 推荐命令：通过运行控制台 preview API 保存 `publish-test-preview*.json`，再用结构化 guard 检查 `action=publish-test`、`environment=test`、无 `mark-tested/promote-prod/promote-backup`。
3. Fail Fast：preview 指向非 test 环境、releaseTag 不等于构建包、或 payload 出现 promotion/mark 动作。
4. 必须记录：preview JSON、guard JSON、releaseTag、目标 host 和未执行正式/备份动作声明。

### 阶段 2：远端真实运行态

1. 必查项：`.env IMAGE_TAG`、backend/frontend `docker inspect` image、compose ps、container state、Actuator health、frontend HTTP、frontend release-info。
2. 推荐命令：远端只读 SSH 脚本使用 POSIX shell、docker、curl 和 JSON parser；`.env` 只读取白名单键，不整体 source。
3. Fail Fast：任一字段缺失或不匹配 releaseTag；container 非 running；backend health 非 UP；frontend HTTP 非 200；release-info sourceRepos dirty 非 false。
4. 必须记录：脱敏 stdout 摘要、SSH exit code、runtime JSON、image tag、health body、HTTP status 和 release-info summary。

### 阶段 3：页面和运行控制台版本说明

1. 必查项：测试服前端可真实打开；运行控制台 API 返回当前 test releaseTag 和 changes；页面点击 `查看变更` 后显示 releaseTag、发布包、组件范围和提交摘要。
2. 推荐命令：Playwright CLI 串行执行 `open`、页面断言和 `screenshot`；登录页只记录非敏感 visible text，运行控制台用实际隔离端口。
3. Fail Fast：页面打不开、运行控制台 release-status 缺当前 tag、对话框缺变更说明、Playwright 证据含密码/token。
4. 必须记录：页面 URL/title、截图路径、release-status 关键字段、console/请求异常摘要和 secret scan 结果。

## 2026-08-30 发布后登录页租户选择器门禁

### 门禁摘要

- Trigger: 测试服发布后用 Playwright 登录 `测试租户/aoteman`、外部助手入口、权限菜单验收，或登录页显示默认 `芋道源码` 但脚本声称已填 `测试租户`。
- Preflight check: 打开登录页后先确认租户控件真实 DOM；Element Plus `el-select filterable allow-create` 必须优先操作 `.el-select input[role="combobox"], input.el-select__input`，填入目标租户后等待对应 `.el-select-dropdown__item:visible` 并点击，找不到选项时才按允许创建规则 `Enter`。旧版普通输入框只作为明确存在且可见时的兼容路径。
- Blocker: 租户控件不可见、目标租户选项无法确认、页面仍显示默认租户、登录接口返回账号密码错误/密码过期、或权限响应的用户/权限/菜单与目标租户不一致时必须停止。
- Verification: Playwright 脱敏输出租户/账号标签、租户字段是否成功填入、登录业务码、权限响应是否包含目标 permission、菜单 path/component/componentName、console error count；必要时用只读 DB 查目标账号所在租户和角色，不输出密码或 token。
- Forbidden action: 禁止只找 `input[placeholder="请输入租户名称"]` 后在未填中时继续登录；禁止把默认 `芋道源码` 登录结果当作 `测试租户` 验收；禁止猜密码、改账号密码、切租户或用 API-only 冒充页面登录。
- Evidence: `doc/tasks/20260829-invoice-print-assistant-test-deploy/execution-log.md`，`release-20260830-invoice-assistant-test-r260830k-r1`。

### 阶段必查项

1. 登录页 DOM 识别：确认 `.login-form` 内租户控件类型、可见 input、页面默认租户文本。
2. 租户选择：优先使用 Element Plus combobox，选中后记录页面显示的目标租户。
3. 权限响应：登录后核对用户标签、permissions、menu path/component/componentName。
4. Fail Fast：控件不存在、目标租户未选中、登录业务码非 0、权限响应不属于目标租户。
5. 必须记录：租户字段是否成功填入、登录 URL、账号标签、权限响应摘要。

## 2026-08-30 publish-test 远端 staging 清理与 manifest 权威门禁

### 门禁摘要

- Trigger: `publish-test` 成功后核验 manifest，远端 `/var/lib/docker/intruoyi-releases/<releaseTag>` 目录存在但为空，或脚本已将发布包解包后清理 staging 内容。
- Preflight check: manifest 权威优先使用本地发布包根目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\<releaseTag>\manifest.json`，再用远端 `/release-info.json`、`.env IMAGE_TAG`、实际镜像 tag、release lock 和 migration ledger 交叉验证；远端 staging 目录只能作为 publish 临时工作目录，不得作为唯一 manifest 来源。
- Blocker: 本地发布包 manifest 缺失、sourceRepos commit/dirty 与冻结 HEAD 不一致、远端 release-info 与 manifest 不一致、`.env IMAGE_TAG` 或实际镜像 tag 漂移、release lock 非 `APPLIED`、或 migration 存在 `FAILED/RUNNING`。
- Verification: 结构化读取本地 `manifest.json`，记录 `publishScope`、sourceRepos commit/dirty、镜像 tar；远端记录 `.env IMAGE_TAG`、`docker inspect` image/status、Actuator health、frontend HTTP、`/release-info.json`、release lock 和 migration count。
- Forbidden action: 禁止因为远端 staging 目录为空就手工补传 manifest 或修改远端状态；禁止用旧 releaseTag 的 manifest、旧运行态或口头说明代替当前 releaseTag 的结构化验证。
- Evidence: `doc/tasks/20260829-invoice-print-assistant-test-deploy/execution-log.md`，`release-20260830-invoice-assistant-test-r260830k-r1`。

### 阶段必查项

1. 本地发布包 manifest：核 `releaseTag`、`publishScope`、sourceRepos commit/dirty、artifact path/hash。
2. 远端运行态交叉验证：核 `.env IMAGE_TAG`、实际镜像、容器、health、HTTP、release-info。
3. release ledger：核 release lock 与 migration status，FAILED/RUNNING 必须为 0。
4. Fail Fast：manifest 缺失、JSON 解析失败、commit/dirty 漂移、远端运行态漂移。
5. 必须记录：manifest path、sourceRepos 摘要、artifact 摘要、远端运行态摘要。

## 2026-09-03 发票打印助手 systemd 与容器 tag 漂移门禁

### 门禁摘要

- Trigger: 联合发布或独立发布发票打印助手到测试服 `18733`，或发现 `erp-invoice-voucher-print-assistant.service` 非 active/running。
- Preflight check: 发布前只读核对 `systemctl cat/status erp-invoice-voucher-print-assistant.service`、`docker ps -a --filter name=erp-invoice-voucher-print-assistant`、`ss -ltnp | grep :18733` 和直连 HTTP；必须同时记录 systemd 单元中的 image tag、实际同名容器 image tag、service active 状态和容器 name 冲突日志。
- Blocker: systemd 单元 tag 与实际容器 tag 不一致、service 处于 `activating`/auto-restart、同名容器由旧 tag 占用导致 `docker run --name` 冲突、`18733` 未监听、直连根路径不是 403、或容器存在 `KINGDEE_ENV_PATH` 全局配置。
- Verification: 新版 source artifact SHA256 本地/远端一致；远端 Docker image tag 与冻结助手 commit/tag 对齐；部署只停止 `erp-invoice-voucher-print-assistant.service` 并移除同名旧容器；重启后 service active、container running、`0.0.0.0:18733` listening、direct HTTP 403、`KINGDEE_RUNTIME_DIR` 存在且 `KINGDEE_ENV_PATH` 不存在；主系统 backend/frontend health 保持通过。
- Forbidden action: 禁止补全局 `.env.kingdee` 或 `KINGDEE_ENV_PATH` 掩盖旧包；禁止因旧容器 HTTP 可访问就忽略 systemd auto-restart；禁止删除无关容器、重启主系统或修改数据库来修助手部署问题；禁止记录完整 service secret/env、密码或 raw secret-bearing 日志。
- Evidence: `doc/tasks/20260903-main-invoice-assistant-test-release/execution-log.md`；助手镜像 `erp-invoice-voucher-print-assistant:f077f49-r260903b`。

### 阶段必查项

1. 发布前：核 systemd unit tag、service active 状态、同名容器 image/status、`18733` listen、direct HTTP。
2. 构建前：用冻结助手 worktree 生成 source artifact，记录 bytes 和 SHA256，远端 extraction 前复核 SHA256。
3. 部署时：仅停止助手 service 和同名旧容器，安装新 tag unit，`daemon-reload` 后 restart。
4. Fail Fast：service/container tag 漂移、同名容器冲突、artifact SHA 不一致、`18733` 不监听或直连非 403。
5. 必须记录：旧 tag/new tag、artifact hash、远端 image、systemd active、container running、listen/HTTP 和主系统健康保持结果。

## 2026-08-31 r260831c 仅测试服成功闭环与发布失败恢复门禁

### 门禁摘要

- Trigger: 当前 HEAD 仅测试服发布，前轮因 scope dependency、required SQL duplicate column 或 `.env`/actual image 漂移失败，修复后使用新 releaseTag 重建。
- Preflight check: 每轮新建 maintenance/app clean release worktree；失败 tag 绝不复用；最终 manifest 后先跑 target-bound code-only plan，status=passed/blocked=0；历史 ADD COLUMN 对 live schema 必须可重放；publish preview 精确解析 `-Environment/-ServerHost`，不能把 inert `-BackupServerHost` 配置误判为备份动作。
- Blocker: target plan blocked、required SQL 非幂等、`.env` 与 actual image 漂移未恢复、operation 非 SUCCESS、lock 非 APPLIED、migration FAILED/RUNNING>0、页面版本说明缺 tag/summary/commit 或出现浏览器错误。
- Verification: 同一成功 tag 的 build/publish operation SUCCESS；manifest validator、sourceRepos dirty=false；远端 `.env`/compose/actual image/container/health/HTTP/release-info；lock/migration；runtime-control release-status；Playwright 测试服页面与查看变更；结构化 final gate 全 true。
- Forbidden action: 禁止拼接 r1/r2/r3 证据、手工改 ledger/schema 过关、with-data 扩大范围、跳过页面、执行 mark/prod/backup，或在失败 worktree 临时修 SQL后继续。
- Evidence: `doc/tasks/20260831-test-only-release-head/verification-report.md`；成功 releaseTag `release-20260831-cell-link-idempotency-test-r260831c-r1`；final gate 28/28。

### 阶段 1：失败轮次收束

1. 每个失败 operation 记录 operationId、duration、脱敏日志、根因 migration、lock/migration、`.env`/actual image/health。
2. `.env` 漂移恢复需用户授权、精确旧新 tag、原子单行替换和恢复后交叉验证；不重启容器、不修改 FAILED 记录。
3. 修复必须在独立开发 worktree 严格 RED/GREEN、提交并合入主线；随后从新主线提交创建全新 release worktree/tag。

### 阶段 2：成功运行态与 ledger

1. 必查项：`.env`、compose backend/frontend image、docker inspect actual image、container running、Actuator UP、frontend 200、release-info commit/dirty/summary。
2. Ledger 必须显示当前 tag lock=APPLIED、FAILED/RUNNING=0、global RUNNING=0；本任务修复的 target migrations 必须 APPLIED 且 checksum 与最终 manifest 一致。
3. 任何单项缺失不得用 operation SUCCESS 替代。

### 阶段 3：浏览器与 final gate

1. Playwright 版本和浏览器路径必须预检；标准依赖目录缺模块时，不得 `npx` 临时下载版本，使用项目内已确认同版本依赖并记录来源。
2. 镜像内 release-info 读取优先 `docker create + docker cp + docker rm`，避免短命 `docker run --rm cat` 客户端/状态悬挂。
3. 测试服公开登录页与认证后业务页结论分层；缺远端测试账号凭据时不得猜密码。本次公开页只证明前端可见，运行控制台页面负责版本说明验收。
4. Final gate 至少汇总 worktree/head/clean、两 operation、manifest、runtime、ledger、release-status、Playwright、禁止动作；输出 false 清单，全部 true 才进入 closeout。

## 2026-09-11 发布后 Playwright 登录稳定窗口门禁

- Trigger: 测试服发布后 Playwright 登录 `测试租户/aoteman`，首次登录跳转、二次导航或外部资源请求产生 `net::ERR_ABORTED`，需要判断页面是否真实可用。
- Preflight check: Playwright 必须先完成真实登录、确认最终进入认证后业务路由，并等待权限接口返回目标用户、菜单和 permissions；登录完成前的导航中止单独记录为登录过程事件。进入认证后页面并清零计数器后，再采集固定稳定窗口内的 console error 和 failed request。
- Blocker: 登录业务码非成功、未进入认证后路由、权限响应为空或不属于目标账号、稳定窗口内出现 console error、业务接口 failed request、页面 title/URL 异常，或证据中包含密码、token、cookie 等敏感值。
- Verification: 记录 Playwright 版本/浏览器路径、base URL、最终 URL、页面 title、租户/账号标签、menuCount、permissionCount、稳定窗口秒数、postLoginConsoleErrorCount、postLoginFailedRequestCount、截图和脱敏 summary JSON。
- Forbidden action: 禁止把所有 `net::ERR_ABORTED` 一律忽略；禁止只看前端 HTTP 200 或登录页可见就判定发布成功；禁止用 API-only 代替真实页面登录；禁止保存含密码/token 的 snapshot。
- Evidence: `doc/tasks/test-server-release-20260908/execution-log.md`；r44 首次登录成功但登录过程 abort 被单独隔离，最终认证后稳定窗口 `consoleErrors=0`、`failedRequests=0`。
