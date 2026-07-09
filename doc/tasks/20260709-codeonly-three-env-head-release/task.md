# IntRuoyi code-only 三环境发布闭环

- 任务ID：20260709-codeonly-three-env-head-release
- 创建时间：2026-07-09 13:12:23 +0800
- 状态：进行中
- 发布输入：后端、前端、维护仓当前 int_main 已提交 HEAD；未提交/未跟踪/脏工作区内容不得进入发布包。
- 发布范围：code-only，不带数据；构建必须使用 SkipDatabaseSync 与 SkipMinioSync；不执行备份、恢复或回滚。
- 正式/备份授权：PROD 确认。

## 任务目标
使用本次专用临时发布 worktree，从同一 releaseTag 完成 build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup，并验证测试服、正式服、备份服均发布成功。

## 输入仓库基线
- 后端：D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro
- 前端：D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3
- 维护仓：D:\ProjectPackage\Int\IntRuoyiMaintance
- 初始仓库状态证据：evidence/initial-repo-heads-and-dirty-status.json
- 注意：主工作区存在未提交/未跟踪内容，发布输入仅允许已提交 HEAD；发布将在新建干净 worktree 中执行。

## 最近任务检查
最近任务检查已执行；本任务开始时主工作区存在历史未提交/未跟踪内容，发布输入限定为三个仓库 int_main 已提交 HEAD。

## 里程碑
- [x] 创建任务目录、task.md、execution-log.md
- [x] 读取并摘录发布前置经验门禁
- [x] 创建后端/前端临时发布 worktree 并确认 commit、branch、dirty=false
- [x] 切换运行控制台到临时 worktree 并验证 health=UP
- [ ] 执行 build-release 并校验 code-only manifest
- [ ] publish-test 并验证测试服
- [ ] mark-tested
- [ ] promote-prod 并验证正式服
- [ ] promote-backup 并验证备份服及 /mnt/intruoyi-data
- [ ] 恢复 runtime-control.local.yaml 主路径、清理 worktree
- [ ] 更新任务文档、请求命令日志，并提交本任务直接改动

## 期望验证
- 五个 operation 均为 SUCCESS。
- 同一 releaseTag 完整闭环，不拼接不同 releaseTag。
- 三环境均验证 .env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200。
- 备份服额外验证 /mnt/intruoyi-data 挂载和发布路径正确。
- 临时发布 worktree 已删除，运行控制台配置已恢复主路径。

## 经验门禁
### experience-index
- - 维护控制台临时 worktree 构建 / pnpm approve-builds / ERR_PNPM_IGNORED_BUILDS：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - pnpm approve-builds 空结果但 install 仍因 ERR_PNPM_IGNORED_BUILDS 失败：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - 构建发布耗时 / 真实 E2E 发布预检：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - 已提交 git 版本发布 / clean worktree 发布输入 / 发布前置门禁：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - Windows 发布 worktree 长路径 / Filename too long / 维护仓历史 evidence 检出失败：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - build-release 目标主机参数 / TestServerHost / BackupServerHost / ProdServerHost / runtime env 生成：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - publish-int-ruoyi NasConfigPath / NAS JSON / runtime-control.local.yaml 误传 / ConvertFrom-Json maintenance：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - 不带数据发布 / code-only / SkipDatabaseSync / SkipMinioSync / manifest 无数据目录验证：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - release-migration dependsOn 缺失 / SQL 元数据依赖不存在 / migration policy gate：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - DCC 分类 lifecycle_stage / NOT NULL 迁移 / required SQL 空值 / deleted=1 历史归档行：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - 测试服远端 MySQL 查询 / ruoyi-vue-pro 业务库 / 容器内 MYSQL_ROOT_PASSWORD / SSH 多层引号：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - runtime-control.local.yaml / repo-root / frontend-root / 临时发布 worktree / 控制台健康检查：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- - 发布 / 备份 / 恢复 / 服务器容量：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
- ## 任务门禁
- - 在 `task.md` 只摘命中文档的门禁，写入 `## 经验门禁`。
- - 涉及服务器写入、发布、恢复、大文件上传、真实 E2E、worktree 合并或清理等高风险动作前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS` 或 `BLOCKER: experience-preflight -> <原因>`。
- - 发布 mark-tested / mark-release-tested / selectedRecoverySetCandidateId / recovery set 候选：见 `docs/release-build-preflight-lessons.md` 的
- - 发布验证 / 正式服端口 / docker compose ps / 48081 / 8081：见 `docs/release-build-preflight-lessons.md` 的
### release-build-preflight-lessons
- # 构建发布耗时问题预防清单
- 当任务涉及 IntRuoyi 运行控制台真实 E2E 构建发布包、发布到测试服、发布包候选验收或构建发布失败重试时，先读本文。
- 本文只沉淀可复用经验；正式发布规则仍以 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md` 和 `login-access.md` 为准。
- 如任务目标是让 Codex 直接照清单执行，请同时读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`。
- ## 通用发布验证基线
- 适用场景：任何功能修改、配置修改、脚本修改、菜单/权限调整、构建发布包和部署服务器。
- 1. 唯一发布源头：所有发布链路只认一个维护仓发布入口和产物来源，本机源码通过不等于发布已通过。
- 2. 配置必须代码化：发布相关的环境变量、路径、参数、菜单权限、脚本和构建开关优先写入仓库和发布脚本，不把服务器手工改动当最终方案。
- 3. 验证发布产物：每次构建都要检查发布包、manifest、打包内容和关键文件是否与本次变更一致，不能只看编译成功。
- 4. 环境差异显式检查：本机、构建机、测试服、备份服、正式服的镜像 tag、目录、挂载、数据库和账号基线都要明确核对，不能默认一致。
- 5. 目标环境真实运行态：到服务器必须看真实运行中的镜像、进程、健康、页面和权限响应，不能只验健康检查或接口单点。
- 6. 故障补成门禁：凡是本机正常、服务器失败、发布后暴露、或构建后才发现的问题，都要补成 preflight、测试或脚本门禁，不能只修一次就结束。
- - 功能修改阶段：先确认修改会进入正确的发布源头和打包范围。
- - 构建发布包阶段：确认产物、manifest、依赖和配置在包内完整且一致。
- - 部署服务器阶段：确认真实运行态、真实权限、真实页面和真实数据路径。
- - 线上或测试服暴露的问题：必须回写到门禁或经验，不要停留在口头提醒。
- ## 发布前必做预检
-    - 如果刚改过维护控制台后端或发布脚本，必须重新构建并重启控制台，再用实际接口或页面确认候选列表、预览命令和门禁行为已生效。
### release-agent-checklist
- # IntRuoyi Codex 发布执行检查清单
- 当任务涉及以下任一事项时，Codex 必须先读本文，再决定是否进入真实发布动作：
- - 运行控制台 `build-release`
- - 发布到测试服
- - `mark-tested`
- - 发布到正式服
- - 发布到备份服
- - 发布失败后的重试
- 本文面向 Codex 执行，不替代正式规则。正式边界仍以以下文档为准：
- - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
- Codex 必须把完整发布任务视为以下严格顺序：
- 1. `build-release`
- 2. `publish-test`
- 3. 测试服运行态验证
- 4. `mark-tested`
- 5. `promote-prod`
- 6. 正式服运行态验证
- 7. `promote-backup`
### release-backup-restore
- # 构建发布备份恢复基线
- - 构建发布包、发布到测试服/备份服/正式服。
- - 标记测试通过、上线备份服、上线正式服。
- - 备份、增量备份、恢复、恢复演练、回滚。
- ## 强制门禁
- - 涉及 worktree 发布隔离、合并或清理时先读取 `docs/worktree-memory.md`。
- - 开始前必须确认目标环境、目标主机、目标库、对象存储 endpoint、发布包或备份点。
- - 发布、备份、恢复、回滚不得用 mock、默认成功、静默跳过或自动降级掩盖失败。
- - 缺少 manifest、schema 版本、备份链、恢复证据、环境凭据或授权时必须 fail fast。
- - 发布代码入口必须先确认：发布、构建、部署脚本和运行控制台发布链路的修改统一在 `D:\ProjectPackage\Int\IntRuoyiMaintance`；`D:\ProjectPackage\Int\IntRuoyi` 只作为业务源码、SQL 和前后端发布输入。
- - 真实写入、备份、恢复必须同一环境闭环，记录前端 URL、后端 action origin、目标主机和目标库证明。
- - 备份或恢复前必须检查根分区、NAS、数据盘、临时目录、日志目录和挂载写入权限。
- - 发布和恢复前必须证明前端、后端、数据库 schema、迁移脚本、required SQL 与 `releaseTag` 或兼容矩阵一致。
- - 备份可用性必须以最终目录、manifest、checksum、对象清单和恢复演练证据共同判定。
- - 新旧发布包、数据库 schema、对象 inventory 和 manifest 容易跨环境混跑。
- - 候选发布包不能只按目录名或时间排序，必须读取 manifest 校验 releaseTag 和 sha256。
- - 构建：manifest 存在且 artifact sha256 可校验。
- - 发布：远端 `.env`、运行镜像和 manifest `IMAGE_TAG` 一致，健康检查通过。
### server-access
- - 测试服、备份服、正式服状态检查、联调、排障。
- - 远端重启、发布、备份、恢复、回滚、大文件上传和批量导入。
- ## 强制门禁
- - 涉及发布、备份、恢复或回滚时，同时读取 `docs/release-backup-restore.md`。
- - 正式服默认禁止操作；测试服、备份服、正式服写入或重启必须有用户当前任务授权。
- - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- - 服务器动作前必须确认目标主机、目标目录、目标数据盘、目标容器和授权范围。
- - 备份服与正式服同等级门禁：只允许已测试通过发布包，必须提供发布责任人与 `PROD` 确认。
- - 备用服务器必须显式使用 `/mnt/intruoyi-data` 数据盘相关参数，不得回退到根分区或 Docker 默认路径。
- - 大文件上传、批量导入、备份或恢复前必须检查根分区、数据盘、NAS 挂载和目标临时目录可用空间。
- - 远端命令应优先使用仓库封装脚本；直接 SSH 时必须记录执行目标和关键输出。
- - 本机后端重启或健康检查失败时，先核当前进程命令行和运行参数；默认后端 jar/profile 可能连接 `3306/root`，不得把该启动前置错误误判成业务功能失败。
- - 本机启动脚本退出码为 0 只代表脚本流程完成，收尾必须分别验证端口监听、进程命令行、后端 `/actuator/health` 和前端 HTML 响应。
- - 备用服务器没有 `/dev/vdb`，真实 1T 数据盘是 `/dev/sdb` 下的 LVM `/dev/mapper/cl-home`。
- - MinIO 容器名和对象存储 endpoint 必须以当前目标环境为准，不得从正式服配置兜底。
- - 健康检查通过不等于发布、备份、恢复或导入任务完成。
- - 远端 `/actuator/health` 返回健康。
- - 远端 `.env`、Docker 镜像、挂载目录、对象存储配置与任务目标一致。
### worktree-memory
- - worktree 创建、切换、排障、合并、清理、删除。
- - 多仓并行开发、前后端成对分支、发布隔离 worktree。
- ## 强制门禁
- - 并行开发默认一任务一独立 worktree，前后端成对创建同名分支。
- - 涉及登录、E2E 或发布时，还要读取对应登录、服务器和发布经验文档。
- - 新建 worktree 前必须明确前后端分支、路径、端口和依赖目标。
- - worktree 路径必须符合仓库标准脚本可识别模式；本项目本机标准路径优先使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\<worktree-name>\...`，不要放在脚本未收录的自定义目录名下。
- - 启动或 E2E 前必须做运行态归属校验，确认前端、后端、数据库、Redis 和文件服务指向本任务目标。
- - 在把某个端口当作真实验收入口前，必须先证明它属于当前 worktree；`8081/48081` 默认视为主工作区 `int_main`，除非已有证据证明当前任务显式接管了它们。
- - 真实 E2E 或登录前置开始前，前后端都必须启动成功；前端可访问但后端 `/actuator/health` 不通时，直接判定运行态未就绪，不得继续把前端页面当作有效验收环境。
- - 合并后必须在合并结果上验证相关功能；验证未通过不得清理 worktree。
- - 清理前必须预览并确认只处理本任务 worktree、运行时和临时产物。
- - 同文件混入其他任务 hunk 时，不得整文件暂存；必须人工拆分或在干净 worktree 重放补丁。
- - 端口、日志、数据库连接和 E2E 目标比代码冲突更容易串线。
- - 新前端 worktree 可能缺少 `node_modules`，类型检查前需先确认依赖。
- - 新前端 worktree 若缺少 `node_modules`，官方 `login-preflight.mjs` 会在启动浏览器前直接报 `Cannot find module 'playwright'`；这属于依赖前置未满足，不是业务登录失败。
- - `8081/48081` 是主工作区默认端口，并行 worktree 不应默认复用。
- - worktree 若放在 `D:\ProjectPackage\Int\IntRuoyi-worktrees\...` 这类非标准目录下，端口台账/标准脚本可能无法识别，导致 FE/BE 端口解析失败或误判。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本任务按既有发布闭环与前置门禁执行；失败时先冻结证据和沉淀经验，再修复根因。
- 是否存在临时补丁或绕过：否。

## 当前状态
- 进行中：运行控制台已切到临时 worktree 且 health=UP，准备执行 build-release。
- 临时 worktree：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709ce


### 维护脚本修复：code-only 跳过 data required SQL（2026-07-09 14:46:36）
- 状态：完成。
- 根因：`publishScope=code-only` 已设置 `SkipDatabaseSync/SkipMinioSync`，但 `Invoke-RequiredDatabaseSqlScripts` 仍按 `preflight-plan.json` 执行所有 `APPLY` 项，导致 `type=data` 的 `20260709_mes_rt000006_batch_record_mapping.sql` 在测试服真实执行并因缺少 RT000006 数据失败。
- 修复：`Get-ReleasePackageDatabaseSqlScripts` 保留 requiredSql 的 `type/migrationId/file/sha256`，`Get-ReleasePreflightApplyItems` 接收 `PublishScope`，当 `code-only` 时在远端 MySQL 执行前明确跳过 `type=data` required SQL。
- 验证：`GREEN: python -X utf8 -m pytest tests/test_code_only_required_sql_contract.py -q -> PASS`，证据见 `evidence/maintenance-codeonly-required-sql-contract-pytest.out.log`。
- 后续：必须重新构建新的 releaseTag，不能复用 v6 失败包。


### v7 范围校验失败（2026-07-09 15:06:02）
- 状态：失败并判废。
- 失败点：manifest sourceRepos 包含 dirty Website 仓，违反本次仅 IntRuoyi 后端/前端/维护仓发布输入。
- 处置：冻结失败证据并沉淀门禁；下一轮用 `-Component intruoyi` 重新构建 v8。


### v8 manifest 校验修正（2026-07-09 15:22:45）
- 状态：完成。
- 结论：v8 包范围正确，sourceRepos 仅后端/前端且 dirty=false，无 Website 或数据目录。
- 下一步：发布测试服并验证同一 releaseTag。


### v8 publish-test 失败与过滤修复 v2（2026-07-09 15:38:14）
- 状态：失败并判废。
- 失败点：preflight item 缺少 `type`，旧过滤未跳过 `type=data` 的 RT000006 数据迁移。
- 处置：冻结失败证据；修复发布脚本按 manifest requiredSql 回查类型；本地测试与 PowerShell 解析通过。
- 后续：维护仓提交修复后同步发布 worktree，重新构建 v9。
