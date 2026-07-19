# 项目经验索引

任务启动顺序固定为：先创建或识别 `doc/tasks/<task-id>/` 并写入最小 `task.md`（目标、里程碑、预期验证、当前状态），再读本文件并只打开命中的经验文档，随后把适用门禁补入任务文档；不要全量阅读所有经验。

## 经验文档写入规范（强制）

### 归档原则

- 先搜索并更新已有经验文档；不得把同类经验拆成多个重复入口。
- 可在行动前检查的问题，必须优先写入 preflight、checklist、memory 或正式流程文档；只有不能转成前置门禁的事后分析才写入 error-prevention。
- 一次性任务状态、临时数据、当前完成情况和长篇执行流水保留在 `doc/tasks/<task-id>/`，不得混入长期经验。
- 没有合适归宿且确需新建长期经验文档时，必须先取得用户明确授权。

### 门禁摘要模板

每条可执行经验必须先提供以下固定摘要，字段不得缺失：

```markdown
### <经验标题>

- Trigger: <哪些任务、关键词或现象会命中本经验>
- Preflight check: <执行风险动作前必须运行的精确检查>
- Blocker: <出现哪些结果必须立即停止>
- Verification: <证明通过的命令、字段、状态、日志或证据路径>
- Forbidden action: <禁止采用的绕过、降级、手工修补或跳过动作>
- Evidence: <来源任务、提交、releaseTag、operation id、文件或问题记录>
```

### 操作流程扩展模板

涉及构建、发布、服务器、数据库、真实 E2E、worktree、备份恢复或其他长链路操作时，在门禁摘要后按执行顺序补充：

1. `阶段 N：<阶段名称>`
2. `必查项`
3. `推荐命令`
4. `Fail Fast`
5. `必须记录`

每个问题必须记录：现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免。

### 写入完成条件

- 在本索引增加可命中的任务关键词、错误文本、命令名、配置键或环境名路由。
- 若经验会阻塞实际流程，同步更新对应 checklist 或主流程入口。
- 在当前任务 `task.md` 摘取本次适用门禁，在 `execution-log.md` 记录验证证据。
- 使用 `rg` 验证新关键词能从索引定位到目标文档。
- 验证 UTF-8 编码和 `git diff --check`，只提交本任务产生的文件。
- 不得用模糊描述替代精确命令、字段、路径和 fail-fast 条件。

## 路由

- 经验沉淀 / 新增经验 / 更新经验 / 经验文件格式 / 前置经验 / 经验门禁模板：先执行本文件“经验文档写入规范（强制）”，再按下方关键词选择目标文档。
- 测试服发布 / 仅测试服 / current HEAD test release / publish-test / 运行态验收 / release-info 版本变更说明：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md`
- publish-test preview 崩溃 / release package candidate scan / dead RUNNING operation / runtime-control JVM 退出：`docs/release-build-preflight-lessons.md#2026-07-11-runtime-control-发布候选扫描与-dead-operation-门禁`。
- PowerShell host:port 插值 / SSH IO pending / bash `$()` / Playwright 浏览器缓存 / release-info mojibake：`docs/powershell-preflight-lessons.md#2026-07-11-powershellsshplaywright-发布验收门禁`。
- 仅测试服运行态验收 / release-info / 运行控制台版本变更说明 / Playwright 版本对话框：`docs/test-release-preflight.md#2026-07-11-仅测试服发布运行态验收新增门禁`。
- 维护控制台临时 worktree 构建 / pnpm approve-builds / ERR_PNPM_IGNORED_BUILDS：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- pnpm approve-builds 空结果但 install 仍因 ERR_PNPM_IGNORED_BUILDS 失败：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`

- PowerShell 命令编排 / 中文编码 / 终端输出预检：先读权威共同规则 `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`，维护仓专项增量再读 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
- 构建发布耗时 / 真实 E2E 发布预检：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 已提交 git 版本发布 / clean worktree 发布输入 / 发布前置门禁：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- Windows 发布 worktree 长路径 / Filename too long / 维护仓历史 evidence 检出失败：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- build-release 目标主机参数 / TestServerHost / BackupServerHost / ProdServerHost / runtime env 生成：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- publish-int-ruoyi NasConfigPath / NAS JSON / runtime-control.local.yaml 误传 / ConvertFrom-Json maintenance：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 不带数据发布 / code-only / SkipDatabaseSync / SkipMinioSync / manifest 无数据目录验证：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- release-migration dependsOn 缺失 / SQL 元数据依赖不存在 / migration policy gate：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- DCC 分类 lifecycle_stage / NOT NULL 迁移 / required SQL 空值 / deleted=1 历史归档行：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 测试服远端 MySQL 查询 / ruoyi-vue-pro 业务库 / 容器内 MYSQL_ROOT_PASSWORD / SSH 多层引号：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- runtime-control.local.yaml / repo-root / frontend-root / 临时发布 worktree / 控制台健康检查：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 发布 / 备份 / 恢复 / 服务器容量：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
- 服务器访问 / 重启 / 远端联调：`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
- 前端页面 / 表格 / 样式：`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`
- 项目错误预防短记忆：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`

## 任务门禁

- 在 `task.md` 只摘命中文档的门禁，写入 `## 经验门禁`。
- 涉及服务器写入、发布、恢复、大文件上传、真实 E2E、worktree 合并或清理等高风险动作前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS` 或 `BLOCKER: experience-preflight -> <原因>`。
- 没有 `experience-preflight` 记录时，不执行长链路或高风险动作。

- 发布 mark-tested / mark-release-tested / selectedRecoverySetCandidateId / recovery set 候选：见 `docs/release-agent-checklist.md#4-mark-tested-放行规则`；自由文本参数引号问题见 `docs/release-build-preflight-lessons.md#2026-07-06-mark-tested-本地启动参数引号门禁`。
- 发布验证 / 正式服端口 / docker compose ps / 48081 / 8081：见 `docs/release-build-preflight-lessons.md#2026-07-04-正式服验证必须读取-docker-compose-端口映射`。
- 发布构建后 sourceRepos 校验：完整契约入口是发布包根目录 `manifest.json`，不是兼容概要 `release-manifest.json`；详见 `docs/release-build-preflight-lessons.md#2026-07-05-发布-manifest-sourcerepos-校验入口`。
- 发布部署动作参数契约：`publish-test/promote-prod/promote-backup` 不传 `publishScope`，必须传 `targetEnvironment` 与 `releaseTag`；详见 `docs/release-build-preflight-lessons.md#2026-07-05-deploy-action-preview-参数契约`。
- required SQL 菜单硬编码 ID / system_menu 占用 / 900301 / 900302 / 权限漂移：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 发布脚本自由文本参数 / Start-Process ArgumentList / mark-tested TestConclusion 引号门禁：见 `docs/release-build-preflight-lessons.md` 的 “2026-07-06 mark-tested 本地启动参数引号门禁”。
- `docs/release-build-preflight-lessons.md`：测试服 HEAD 发布前置经验，覆盖 clean worktree、pnpm 版本、SQL metadata、Smart Release 输入、大镜像分块上传、runtime-control API、UTF-8/SSH 输出校验和发布后 fail-fast 条件。（2026-07-09 任务 `20260709-head-test-server-release` 更新）

- build-release API 预览 targetEnvironment 参数契约：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md#2026-07-09-build-release-预览请求不得携带-targetenvironment`

- build-release 三环境预览 ProdServerHost 门禁：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md#2026-07-09-build-release-三环境预览必须含-prodserverhost`
- 2026-07-09：build-release 前必须执行全量迁移元数据策略门禁，`type` 只允许 schema/data/menu/config/permission/seed，修复 SQL 元数据需同步补 `script/tests` 覆盖；`20260714_dcc_personal_file_decommission.sql` / `Release migration metadata missing` 也命中该门禁；详见 `docs/release-build-preflight-lessons.md#2026-07-09-build-release-迁移元数据必须先过全量策略门禁`。
- 2026-07-09：publish-test required SQL 若出现 MySQL 1137 Can't reopen table，先冻结远端 operation/migration/env 证据，再拆分或落表修复 SQL 并补 script/tests，最后重新构建新的 releaseTag；详见 docs/release-build-preflight-lessons.md#2026-07-09-publish-test-sql-不得复用同一派生临时表别名触发-mysql-1137。
- 2026-07-09：publish-test required SQL 不得依赖测试服手工业务数据；出现 Missing <业务对象> 时先冻结 operation/migration/业务表快照，再通过迁移自给或 dependsOn 修复并重新构建新 releaseTag；详见 docs/release-build-preflight-lessons.md#2026-07-09-publish-test-required-sql-前置业务数据必须由迁移自给或显式依赖。


- Keywords: code-only required SQL, type=data, publishScope=code-only, SkipDatabaseSync, SkipMinioSync, preflight-plan APPLY data migration
  - Read: `docs/release-build-preflight-lessons.md`
  - Gate: code-only 发布前确认 data required SQL 不进入远端 MySQL 执行队列；如会执行，阻塞并修复发布脚本后重建 releaseTag。


- Keywords: IntRuoyi code-only component, Component intruoyi, Website dirty sourceRepos, website package directory, manifest sourceRepos dirty
  - Read: `docs/release-build-preflight-lessons.md`
  - Gate: IntRuoyi 后端/前端发布 build-release 必须显式 `-Component intruoyi`；manifest 不得包含 Website 仓或 website 包目录。


- Keywords: preflight-plan missing type, manifest requiredSql type map, code-only data SQL skip, requiredSqlTypeByMigrationId, RT000006 data migration
  - Read: `docs/release-build-preflight-lessons.md`
  - Gate: code-only required SQL 过滤必须从 manifest requiredSql 回查 migration type；preflight item 缺 type 不得导致 data SQL 执行。


- Keywords: Java native memory allocation failed, Maven build memory, hs_err_pid, build-release memory, insufficient memory JVM
  - Read: `docs/release-build-preflight-lessons.md`
  - Gate: build-release 前检查内存余量；JVM native memory 失败必须冻结 hs_err 与内存快照，降低构建内存压力后重建新 releaseTag。
- Keywords: prod-preflight-release, ProdDryRunEvidencePath, sanitized package workspace, Copy-Item, robocopy, shutil.copytree -> `docs/release-build-preflight-lessons.md`
- Keywords: worktree remove failed, residual worktree directory, Invalid argument, Directory not empty, r260709ce cleanup -> `D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`
- Keywords: frozen release baseline, build start worktree commit, source HEAD drift after build, 不追逐后续提交 -> `docs/release-build-preflight-lessons.md`
- Keywords: mes_pro_route_schedule_config conflict, route schedule config duplicate, 工序维度收敛, conflict guard -> `docs/release-build-preflight-lessons.md`
- Keywords: Manifest v1 legacy release-manifest frontend commit, schema-specific manifest validation -> `docs/release-build-preflight-lessons.md`
- Keywords: Manifest artifact sha256 prefix, sha256:<64hex>, 281 hash mismatch, hash prefix normalization -> `docs/release-build-preflight-lessons.md#2026-07-10-manifest-artifact-sha256-前缀门禁`
- Keywords: runtime-control Linux powershell.exe, 运维矩阵 ERROR unknown, release-status current tag null, release-info 版本变更说明 -> `docs/release-build-preflight-lessons.md`
- Keywords: PowerShell pipe Python Node 中文问号, subprocess text CRLF ssh bash, $LASTEXITCODE stderr, $Args automatic variable -> `docs/powershell-preflight-lessons.md`
- Keywords: PowerShell heredoc, python -c newline, U+FEFF BOM stdin, Playwright 中文正则, rg -- lookahead, preview 参数 flag 错位, -RequireTested, 脱敏误伤 ruoyi-vue-pro, -ProdServerHost -> `docs/powershell-preflight-lessons.md#2026-07-13-powershell-发布脚本承载参数解析与证据脱敏门禁`
- Keywords: concurrent publish, releaseTag drift, operation lock RUNNING, 并发发布, 目标版本漂移, .env compose image release-info 不一致 -> `docs/test-release-preflight.md#并发发布与目标版本漂移门禁`
- Keywords: publish-test preview BackupServerHost metadata, forbidden host token, ServerHost target gate, 172.30.30.59 误判 -> `docs/test-release-preflight.md#2026-07-12-publish-test-preview-目标字段门禁`
- Keywords: SmartReleaseBaselineManifestPath missing, enableSmartReleaseReport failed, smart release report-only baseline -> `docs/release-build-preflight-lessons.md#2026-07-12-smart-release-报告基线门禁`
- Keywords: Manifest v1 changeSet.component, legacy release-manifest component, schema-specific manifest validation -> `docs/release-build-preflight-lessons.md#2026-07-12-manifest-v1-与-legacy-schema-分离校验`
- Keywords: PowerShell $PID automatic variable, cleanup process self-match, r260712p worktree removal, command line guard -> `docs/powershell-preflight-lessons.md#2026-07-12-powershell-自动变量与进程守卫门禁`
- Keywords: migration policy gate --json unsupported, run-release-migration-policy-gate --output, frozen script parameter contract -> `docs/release-build-preflight-lessons.md#2026-07-12-冻结-worktree-脚本参数契约门禁`
- Keywords: build-release missing ProdServerHost, three environment host preview, TestServerHost ProdServerHost BackupServerHost -> `docs/release-build-preflight-lessons.md#2026-07-13-build-release-三环境-host-完整性门禁`
- Keywords: release worktree frontend node_modules missing, cross-env not recognized, yudao-ui-admin-vue3 frozen install -> `docs/release-build-preflight-lessons.md#2026-07-13-release-worktree-双前端依赖恢复门禁`
- Keywords: release log secret, mysql -p plaintext, 发布日志明文密码, request-command-log 脱敏, raw secret log -> `docs/release-build-preflight-lessons.md#2026-07-10-发布日志凭据脱敏门禁`
- Keywords: mes_pro_route_use_process_batch_record missing, mes_pro_route_use_process_batch_record_legacy_20260709, ERROR 1146, 20260708_mes_batch_record_version_phase_one, route flow legacy rename order -> `docs/release-build-preflight-lessons.md#2026-07-13-required-sql-兼容路线流迁移重命名顺序`
- Keywords: docker inspect crash, Exception 0xc0000005, local container env, raw docker env secrets, LocalMySqlContainer, LocalMinioContainer -> `docs/release-build-preflight-lessons.md#2026-07-13-build-release-本地-docker-inspect-与-env-脱敏门禁`
- Keywords: infra_release_operation_lock updated_time, update_time, Unknown column updated_time, release lock schema -> `docs/release-build-preflight-lessons.md#2026-07-13-远端发布锁表查询必须先按真实-schema-校验`
- Keywords: mark-release-tested targetEnvironment, mark-tested targetEnvironment, selectedRecoverySetCandidateId restore candidate -> `docs/release-build-preflight-lessons.md#2026-07-13-mark-tested-payload-不得携带-targetenvironment`
- Keywords: runtime-control state-dir release worktree dirty, ?? runtime, operation state logs cache dirty sourceRepos -> `docs/release-build-preflight-lessons.md#2026-07-13-运行控制台-state-dir-不得污染-release-worktree`
- Keywords: preview arguments RequireTested switch flag parser, SkipDatabaseSync SkipMinioSync flag, ServerHost preview gate false negative -> `docs/release-build-preflight-lessons.md#2026-07-13-preview-参数解析必须兼容-switch-flag`
- Keywords: AGENTS rule conflict, 规则优先级, previous task ownership, concurrent worktree ownership, 仅测试服完成定义 -> 先读全局 `C:\Users\BJB110\.codex\AGENTS.md` 的 `Rule Precedence and Task Ownership`，再读当前目录最近的项目 `AGENTS.md`
- Keywords: Invoke-WebRequest Content byte array, Invoke-RestMethod health status, process scan exclude current PID -> `docs/powershell-preflight-lessons.md`
- Keywords: task-closeout status unknown, Current Status completed, cleanup preview apply, worktree Directory not empty -> `docs/release-build-preflight-lessons.md` and `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
- Keywords: task-closeout runtime log lock, PermissionError WinError 32, runtime-control-main err log, long-running process log under task dir -> `docs/release-build-preflight-lessons.md#2026-07-13-task-closeout-长运行进程日志目录门禁`
- Keywords: release-info CRLF, releaseInfoTagOk false, console-error-string-parser, Errors: 0, Warnings: 0, residual-release-worktree-root, r260713j physical root -> `docs/release-build-preflight-lessons.md#2026-07-13-release-info-与运行控制台验收解析门禁` and `docs/release-build-preflight-lessons.md#2026-07-13-release-worktree-物理根目录复核门禁`
- Keywords: ready_for_closeout, verification-report keep, cleanup apply, closeout state machine, completed after cleanup -> `docs/release-build-preflight-lessons.md#2026-07-10-发布任务-closeout-状态与清理契约` and `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
- Keywords: publish-test preview msg=publishScope, deploy action publishScope, includeOnlyOffice includeShowroomBuildPackage, r260719i preview 400 -> `docs/release-build-preflight-lessons.md#2026-07-05-deploy-action-preview-参数契约`
- Keywords: docker build no new log, Docker Desktop Linux engine 500, buildx _ping timeout, build-release BuildKit hang, Docker preflight passed then build hung, docker-buildx CPU, manifest absent after docker kill -> `docs/release-build-preflight-lessons.md#2026-07-19-build-release-docker-buildkit-卡顿诊断门禁`
- Keywords: 20260718_system_entitlement_management, system_entitlement_policy, system entitlement migration metadata, missing release-migration metadata, system entitlement policy SQL -> `docs/release-build-preflight-lessons.md#2026-07-19-system-entitlement-迁移元数据门禁`
- Keywords: unknown release-migration metadata key, dependsOn missing migration, invalid type, schema,menu, .sql dependsOn suffix, 20260715_mes_schedule_capacity_mode_unification, 20260717_mes_route_process_workstation_binding, 20260717_mes_edhr_filler_minimal_permissions, 20260717_bpm_form_center, 20260718_mes_feedback_import_record_direct_progress -> `docs/release-build-preflight-lessons.md#2026-07-19-release-migration-结构化字段与-dependson-后缀门禁`
- Keywords: setReleaseActionLocked, getWorkTaskId, setBatchRecordVersionNo, withdrawVoidBatchExecution, updateApprovalFieldsToDraft, MES companion contract, yudao-module-mes compilation failure -> `docs/release-build-preflight-lessons.md#2026-07-19-build-release-mes-companion-contract-编译门禁`
- Keywords: withdrawVoidBatchExecution frontend export, edhr change API missing export, RollupError not exported, BatchExecutionListPage import change.ts -> `docs/release-build-preflight-lessons.md#2026-07-19-frontend-edhr-companion-api-export-门禁`
- Keywords: ERROR 1267, Illegal mix of collations, utf8mb4_unicode_ci, utf8mb4_general_ci, 20260717_mes_edhr_filler_minimal_permissions, tmp_edhr_filler_required_permission, system_entitlement_policy no-op -> `docs/release-build-preflight-lessons.md#2026-07-19-publish-test-required-sql-collation-门禁`
- Keywords: ERROR 1644, Role id 910311 is already occupied, system_role.id, bpm_admin, 20260718_bpm_admin_role_assignment, electronic_signature_admin, LAST_INSERT_ID -> `docs/release-build-preflight-lessons.md#2026-07-19-publish-test-角色-id-硬编码占用门禁`
- Keywords: dcc master points to obsolete revision, OBSOLETE_CHAIN, 20260718_controlled_content_lifecycle, dcc_controlled_file_master, current_active_controlled_file_id, file_number, controlled content lifecycle -> `docs/release-build-preflight-lessons.md#2026-07-19-controlled-content-生命周期迁移-obsolete_chain-门禁`
- Keywords: controlled_content_version_ref.content_key, CAST master id AS CHAR collation, utf8mb4_0900_ai_ci, utf8mb4_unicode_ci, controlled content content_key ERROR 1267 -> `docs/release-build-preflight-lessons.md#2026-07-19-controlled-content-content_key-cast-collation-门禁`
- Keywords: ERROR 1406, Data too long for column menu_ids, system_tenant_package.menu_ids, 20260717_bpm_form_center, backup promote menu_ids length -> `docs/release-build-preflight-lessons.md#2026-07-19-backup-promote-tenant-package-menu_ids-长度门禁`
- Keywords: r260719k release failure prevention checklist, 三环境 code-only 发布复发防止, MES companion, frontend export, BuildKit, required SQL collation, menu_ids -> `docs/release-agent-checklist.md`，标题“2026-07-19 r260719k 发布失败复发防止清单”
- Keywords: test-only release, publish-test, test server runtime verification, release-info dialog, frozen release worktree, only test server -> `docs/test-release-preflight.md`
- Gate: 仅测试服发布任务优先读取 `docs/test-release-preflight.md`，再按失败点跳转 `release-build-preflight-lessons.md`、`powershell-preflight-lessons.md` 和 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
- Keywords: remote python3 absent, python3 command not found, jq command not found, backup runtime verification carrier, 远端验收工具缺失 -> `docs/powershell-preflight-lessons.md#2026-07-14-远端验收工具可用性门禁`
- Keywords: worktree remove Directory not empty, r260713v release worktree residual, git worktree registration absent physical directory exists -> `docs/release-build-preflight-lessons.md#2026-07-13-release-worktree-物理根目录复核门禁`
- Keywords: system_menu.id must be an integer literal, duplicate system_menu.id detected across release SQL history, INSERT INTO system_menu SELECT ON DUPLICATE KEY UPDATE VALUES, release SQL parser false positive, 20260714_signature_my_signature_admin_menu -> `docs/release-build-preflight-lessons.md#2026-07-16-release-preflight-菜单-sql-解析边界门禁`
- Keywords: vue/no-unused-vars, vite-plugin-eslint, pnpm build:test, ProcessWipTable, sortColumnAttrs, handleTemplateSortChange, slot unused vars -> `docs/release-build-preflight-lessons.md#2026-07-16-release-build-前端-eslint-slot-未使用变量门禁`
