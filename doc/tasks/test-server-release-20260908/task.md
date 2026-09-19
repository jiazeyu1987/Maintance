# test-server-release-20260908

## Task Goal

在临时发布 worktree 中对当前 `int_main` 目标提交执行真实测试服发布链路：`build-release -> publish-test`，验证测试服实际运行态、页面、版本号、发布包与远端镜像一致性。不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

1. 发布前置门禁：读取发布、服务器、worktree、PowerShell、登录与经验文档，确认目标提交、发布范围、临时 worktree 和真实测试服验证方法。
2. 临时发布 worktree：创建本次专用 worktree，检出当前发布目标提交，确认发布输入为 clean committed content。
3. 构建安装包：执行 `build-release`，记录 releaseTag、manifest、包哈希、构建预检和 Docker 构建证据。
4. 发布测试服：执行 `publish-test`，等待 operation 终态，验证迁移台账、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200。
5. 页面验收：通过 Playwright 真实登录测试租户并检查运行控制台版本/变更说明。
6. 收尾：记录证据，清理本次临时发布 worktree；不触碰正式服、备份服和无关并发改动。

## Expected Verification

- `build-release` operation SUCCESS，manifest 与 package digest 校验通过。
- `publish-test` operation SUCCESS。
- 测试服远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 与本次 releaseTag 一致。
- backend actuator health 为 `UP`，frontend HTTP 200。
- Playwright 通过真实登录路径确认页面可访问，并核对运行控制台 releaseTag/版本变更说明。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；本次是对已完成发布链路优化做真实测试服验证，失败即记录阻断与根因，不以手工修补或跳过替代。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- 测试服范围：本次只允许 `build-release -> publish-test`；目标主机 `172.30.30.58`；禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服和审查服动作。
- 冻结来源：维护仓、主程序仓必须从已提交 HEAD 创建本轮专用短路径 release worktree；主工作区脏改动、未跟踪文件和冲突不得进入发布包。
- 构建前门禁：构建前需确认 release worktree clean、迁移策略/SQL 合同/target-state preflight 由实际维护脚本执行，失败即停止，不手工改库或复用失败 releaseTag。
- 安装包门禁：构建后必须用 `manifest.json` 权威核对 releaseTag、component、publishScope、sourceRepos commit、dirty=false、artifact size/SHA 和 package digest。
- 发布前门禁：`publish-test` 只能指向 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，预览或日志出现正式/审查/推广动作即停止。
- 发布后门禁：成功必须同时核 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、release-info、release lock 和 migration 无 FAILED/RUNNING。
- 页面门禁：Playwright 必须真实打开测试服页面并登录测试租户验证运行控制台版本/变更说明；不能用 API-only 代替页面验收，不能保存含密码/token 的证据。
- PowerShell/SSH 门禁：中文与多行脚本使用 UTF-8/LF，外部命令以退出码和结构化结果为准，SSH carrier warning 与业务断言分层记录，不打印完整 `.env` 或 secret-bearing 日志。
- Worktree 收尾：发布和验收完成后先标记 `ready_for_closeout`，再 preview/apply cleanup；临时 worktree 必须无 Git 注册、物理路径不存在、无进程引用后才能 `completed`。

## Current Status

blocked

## Cleanup Keep

- `doc/tasks/test-server-release-20260908/database-schema-evidence.md`
- `doc/tasks/test-server-release-20260908/bug-regression-evidence.md`
- `doc/tasks/test-server-release-20260908/dcc-invalid-reference-cleanup-20260909.sql`
- `doc/tasks/test-server-release-20260908/dcc-invalid-reference-cleanup-backup-20260909.json`
- `doc/tasks/test-server-release-20260908/dcc-invalid-reference-cleanup-rollback-20260909.sql`
- `doc/tasks/test-server-release-20260908/dcc-invalid-reference-cleanup-summary-20260909.txt`
- `doc/tasks/test-server-release-20260908/r44-signature-t1-active-migration-policy.json`

### 2026-09-11 r44 测试服发布完成

- 当前结论：`release-20260911-verified-branch-app-r260908c-r44` 已完成测试服发布验证，范围仍止于 `build-release -> publish-test/deploy-release`，未执行 `mark-tested`、`promote-prod`、`promote-backup`，未触碰正式服、备份服或审查服。
- 远端运行态：测试服 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health、frontend HTTP 200、frontend `/release-info.json` 均指向 r44。
- 数据库迁移：`infra_release_operation_lock` 最新测试服记录为 r44 `APPLIED`，`infra_release_migration` 中 r44 为 `APPLIED=6`、`SKIPPED_ALREADY_APPLIED=555`，`FAILED/RUNNING=0`；`system_users` 已存在 `active_canonical_username` 及唯一键 `uk_system_users_tenant_active_canonical_username`。
- 页面验收：Playwright 真实打开测试服 `http://172.30.30.58:8081`，使用 `测试租户/aoteman` 登录成功，权限响应成功，登录后稳定期 console error 和 failed request 均为 0；证据位于 `output/playwright/r44-test-release/playwright-test-server-r44-post-login-stable-summary.json`。
- 收尾状态：测试服发布和 release worktree 清理已完成；主线融合仍阻塞，原因是应用发布分支 `713c64112d7b626a2ba71788fd36cc32d686addc` 与 `E:\IntRuoyi` 当前 `int_main` 分叉，维护脚本提交 `8080c0d3c7076d2305d945dea26bf1a22ceaf026` 与维护仓 `int_main` 分叉，且维护仓主工作区存在 38 个 tracked dirty、应用主工作区存在 7 个 unrelated tracked dirty。已保护发布修复分支，未执行风险合并或覆盖并发改动。

### 2026-09-11 closeout 结果

- `task-closeout-cleanup` preview/apply 通过；任务目录只保留 `task.md`、`execution-log.md`、`verification-report.md`、数据库/回归证据、DCC 清理备份/回滚 SQL 和 r44 迁移策略证据。
- 已创建维护提交保护分支 `codex/release-r44-maintenance-script-20260911` 指向 `8080c0d3c7076d2305d945dea26bf1a22ceaf026`；应用发布提交由 `codex/test-release-signature-t1-active-unique-20260911` 保护。
- 已删除本任务 r260908c 系列 release worktree 的 Git 注册与物理残留：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c*`、`D:\IntRuoyiWorktree\r260908c-app`、`D:\IntRuoyiWorktree\r260908c-gate-verify`、`D:\IntRuoyiWorktree\r260908c-r33` 到 `r260908c-r44`。
- 长期经验已合并进 `docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md` 和 `docs/experience-index.md`，新增 r44 的“有效用户唯一约束”和“Playwright 登录后稳定窗口”门禁。
- 当前阻塞：尚未把维护脚本提交和应用发布修复链合入各自 `int_main` 并在主线上复验；维护仓和应用仓主工作区均存在不属于本次收尾的 tracked dirty。在合并前不得删除保护分支或宣称主线已具备 r44 发布修复。

## 2026-09-10 构建前迁移演练门禁

### 目标

在 Maven、前端构建、Docker 构建、安装包上传和测试服真实数据库迁移之前，基于测试服数据库的一致性只读快照创建一次性隔离 MySQL，按最终 `preflight-plan.json` 的 APPLY 顺序完整执行待发布迁移。任一迁移失败必须立即阻断昂贵构建和服务器写入，并清理本任务创建的临时容器与数据目录。

### 里程碑

- [completed] M1：补充 BDD 场景与 RED 契约测试，锁定演练顺序、失败阻断、证据和清理要求。
- [completed] M2：实现一次性 MySQL 快照、迁移执行与结构化证据生成，并接入 `build-release` 的 Maven 前门禁。
- [completed] M3：完成单元/契约测试及测试服只读快照真实演练，证明迁移错误可在构建前暴露。
- [completed] M4：更新发布经验门禁、数据库证据和任务记录；维护脚本提交完成。

### 预期验证

- 契约测试证明迁移演练调用严格位于 `Building backend jar` 之前。
- 演练只读取测试服源数据库；SQL 仅写入无端口暴露、带唯一 releaseTag 的一次性 MySQL。
- 失败证据包含 releaseTag、源提交、计划摘要、失败 migrationId 和退出状态；失败后 Maven 标记不得出现。
- 无论成功或失败，只清理本任务精确命名的演练容器、临时快照和数据目录。
- 使用当前测试服快照与最终迁移计划进行真实演练；若迁移仍不兼容，必须在构建前明确失败。

### BDD 场景

- `BDD: 最终迁移计划在昂贵构建前演练 -> Given 测试服只读快照和最终 preflight 计划已生成 / When build-release 开始 / Then 一次性 MySQL 按 APPLY 顺序执行全部迁移且通过后才允许 Maven`。
- `BDD: 演练失败阻断真实发布 -> Given 任一待执行迁移与目标快照不兼容 / When 一次性 MySQL 执行该迁移失败 / Then 生成失败证据、清理临时资源并在 Maven、NAS 上传和测试服写入前终止`。
- `BDD: 演练环境隔离且不可复用 -> Given 任意成功或失败的 releaseTag / When 演练结束 / Then 临时容器和数据目录均被精确清理，真实测试库无写入且失败 releaseTag 不得继续发布`。

### 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；快照、临时 MySQL、迁移计划、证据或清理任一前置不满足均失败。
- `是否从根因和长期维护角度解决`：是；把目标数据库兼容性验证前移为每次安装包构建的强制、可审计门禁。
- `是否存在临时补丁或绕过`：否；不通过跳过迁移、伪造台账或改写测试服真实数据换取通过。

### 2026-09-10 方案调整：标准 CI/CD 快速门禁

- 用户明确取消“每次复制完整 15.4 GB 业务数据”的常态方案。
- 日常强制路径调整为：测试服 schema-only dump -> 一次性空结构 MySQL -> 结构迁移演练；对 data/menu/permission/config/seed 等迁移执行显式、只读、目标服务器依赖检查。
- 非结构迁移缺少只读 preflight 契约时直接阻断，不允许用空库执行成功冒充真实兼容。
- 完整数据快照演练仅保留为高风险迁移或定期夜间任务，本次不实现自动调度、不参与日常安装包构建。
- MinIO 不参与数据库结构迁移门禁。

### 最终结果与剩余阻塞

- 门禁实现提交：`53338f2`、`6b3c02e`、`2261062`、`3fb9a8c`、`d2cfd84`、`120df30`。
- 契约回归：PowerShell AST PASS，`scripts/tests/test_release_build_preflight_cache.py` 为 `50 passed`。
- 真实验收：`r29` 从测试服 MySQL 8.0.39 一致性只读快照创建无网络、无端口的一次性同镜像数据库；快照成功，前三条迁移成功，第 4 条 `20260717_mes_balloon_excel_device_workstation_binding` 因 `balloon Excel workstation machine count mismatch` 失败。
- Fail-fast 结论：Maven、前端构建、Docker image、NAS 上传和真实测试库迁移均未开始；临时 container、volume、staging 均已精确清理。
- 当前阻塞：主程序迁移 `20260717_mes_balloon_excel_device_workstation_binding` 与测试服快照中的工作站机器基线不兼容。必须先按 BDD/TDD 修复迁移契约，再使用全新 releaseTag；禁止跳过演练或复用 r25-r29。

## Blocker

当前从已验证主程序提交 `b88c242f0aa3030f387695b500b3fb6e85fa54d8` 继续发布到测试服，但 with-data 安装包在 DCC 对象清单阶段被正确阻塞：本地数据库引用 `infra_file.id=9198354891791`、`config_id=28`、`path=dcc/original/20260611/empty.docx`、`deleted=0`，而本地 MinIO `yudao` bucket 快照不存在该对象。若跳过该门禁发布，测试服会带着坏的 DCC 文件引用运行；按 no-fallback/no-mock 规则不得绕过。

## Current Release Attempt

- Attempt: `r260908c-r1`
- Release scope: test server only, `build-release -> publish-test`
- Maintenance release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\m`
- Maintenance frozen commit: `bd4a05fa82263814cbf2828e86183f9413aa28b1`; release-script fix commits in this worktree: `67ab5cf`, `467f750`, `8bd1481`
- App release worktree: `D:\IntRuoyiWorktree\r260908c-app` (moved from legacy noncompliant path before the migration-fix commit)
- App frozen commit: `b88c242f0aa3030f387695b500b3fb6e85fa54d8`
- Target server: `172.30.30.58`
- Last attempted releaseTag: `release-20260908-verified-branch-r260908c-r8`

## Final Verification

- `GREEN: experience-preflight -> PASS`，已读取测试服发布、构建、PowerShell、服务器、登录、备份恢复和 worktree 门禁。
- `GREEN: release-worktree-freeze-r260908c -> PASS`，维护仓 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\m` 从 `bd4a05fa82263814cbf2828e86183f9413aa28b1` 创建；主程序 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\a` 检出 `b88c242f0aa3030f387695b500b3fb6e85fa54d8`。
- `GREEN: migration-policy-gate-r260908c-r1 -> PASS`，维护仓与主程序仓迁移门禁均通过，`migrationCount=605`。
- `GREEN: maintenance-release-script-fix -> PASS`，发布 worktree 内提交 `67ab5cf`、`467f750`、`8bd1481`，并完成 `scripts\tests\test_release_build_preflight_cache.py` 回归 `45 passed`。
- `BLOCKER: build-release-r260908c-r8 -> FAIL`，with-data 安装包 DCC object inventory 检测到 `infra_file.id=9198354891791` 指向的 MinIO 对象缺失；未执行 `publish-test`，未写测试服务器。

## Impact

本次验证继续证明安装包门禁有效：SQL 元数据问题、code-only 数据依赖问题、Docker inspect 参数问题、MinIO 客户端镜像缺失问题都已在测试服写入前暴露或修复；当前剩余阻塞是本地源数据与对象存储不一致。下一步需要先明确修复策略：补回 `dcc/original/20260611/empty.docx` 对象，或确认并清理/修复数据库中的失效 DCC 文件引用。该决策会修改本地测试数据/对象，需单独授权后执行。

## Resume After User Authorization

- 用户已明确授权继续处理本地 DCC 对象缺失阻塞。
- 采用策略：从历史真实发布快照恢复缺失对象，不删除、不改写数据库业务引用。
- Source: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-121500-e2e\minio\yudao\dcc\original\20260611\empty.docx`
- Target: local MinIO `yudao/dcc/original/20260611/empty.docx`
- Verification: size `3306`, SHA256 `fd9160a87bcbe94570d998499f1b1ed9b39f381fde1688c2ed2b0b0a6d562bf2`

## Current Blocker Update

- `release-20260908-verified-branch-r260908c-r12` reached late package creation successfully through migration policy, eDHR storage, target-state build preflight, backend Maven build, frontend `pnpm build:test`, Docker image build/export, MySQL dump, and MinIO mirror.
- r12 was blocked before final manifest and before any test server write by DCC inventory: missing local MinIO object `dcc/original/20260614/QMS文件清单.xlsx`.
- The missing QMS object was restored through MinIO API from historical release snapshot `release-20260616-121500-e2e`; no database rows were changed.
- A batch preflight then found systemic local data/object drift: `17870` missing referenced DCC objects out of `17897`; `17528` are covered by `release-20260616-121500-e2e`, but `342` require later source snapshots or a deliberate data repair decision.
- The task is blocked before `publish-test`; do not reuse failed releaseTags r1-r12 and do not publish to test until the DCC object consistency gate is clean.

## 2026-09-09 Resume Update

- 用户再次授权继续后，按既定“补回真实历史对象，不删除、不改写数据库业务引用”策略处理 DCC 对象漂移。
- 已从 `release-20260616-121500-e2e` 历史快照补齐/确认 `17529` 个对象；补齐过程只写本地 MinIO `yudao` bucket，不修改 MySQL 业务表，不访问测试服务器。
- 额外扫描所有带 `minio\yudao` 的历史发布快照后，又从 `release-20260701-1720-mes-scheduler-dcc-inventory-fast` 补回 `215` 个对象。
- 全 bucket 复核后仍有 `128` 条 DCC 引用缺失对象，其中 `126` 条为非空 objectPath、`2` 条为空 objectPath；这些对象不在本地 MinIO、不在已扫描历史发布快照中，且 `infra_file_content` 表无对应真实内容。
- 当前继续阻断在 build/package 阶段；未执行 `publish-test`，未写测试服务器，未复用失败 releaseTag。下一步只能在拿到真实文件来源后补回对象，或由用户单独明确授权并确认规则后进行 DCC 数据修复/清理。

## 2026-09-09 Invalid Reference Cleanup Update

- 用户明确要求“删除失效的引用，再继续”后，本地 DCC 数据修复已执行；只修改本地 MySQL `ruoyi-vue-pro`，未修改测试服/正式服/备份服。
- 清理前已导出备份与回滚 SQL：`dcc-invalid-reference-cleanup-backup-20260909.json`、`dcc-invalid-reference-cleanup-rollback-20260909.sql`。
- 清理后实时 DCC 发布引用复核通过：`17760` 行引用、`14016` 个唯一对象路径、`0` 个空路径、MinIO inventory 对比 `missing_paths=0`。
- 当前 DCC 对象一致性阻塞已解除，继续使用新的 releaseTag 重新执行 `build-release`；失败 releaseTags r1-r12 不复用。

## 2026-09-10 Lightweight Release Correction

- 用户明确要求立即终止当前 `with-data` 发布，修改脚本后重新生成轻量程序安装包并仅发布测试服。
- 已终止本任务 `with-data` 进程 PID `61812`；终止前无 SSH/SCP/Docker 子进程。测试服仍为 `release-20260903-main-invoice-assistant-test-r260903b-r1`，本轮 r14 未写入测试服。
- 根因：当前发布 worktree 创建早于已验证优化提交 `6639128`，脚本仍通过两个默认 false 的 skip switch 推导 `with-data`，直接调用 `-Component full` 时会隐式打包 MySQL dump 与 MinIO 快照。
- 正式方案：`build-release` 使用明确的 `PublishScope`，默认 `code-only`；`with-data` 必须显式选择并二次确认。`Component=intruoyi` 只表示完整前后端程序，不再隐式携带全量运行数据。
- 新安装包必须使用新 releaseTag，不复用 r14；只包含前后端镜像、运行配置、required SQL/增量迁移及治理证据，不得包含 MySQL 全量 dump、MinIO 快照或 DCC 对象清单。
- 发布范围仍止于测试服 `172.30.30.58`，禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服和备份服动作。

### 设计约束复核

- `是否引入 fallback/降级/吞异常`：否；范围由显式契约决定，冲突参数直接失败。
- `是否从根因和长期维护角度解决`：是；消除 `Component=full` 与全量数据同步的隐式绑定，并把日常程序发布设为安全默认值。
- `是否存在临时补丁或绕过`：否；不复用或改写 r14 大包，不跳过 manifest、迁移预检、完整性和测试服运行态门禁。

### r15 Preflight Result And Scope Refinement

- r15 `code-only` 构建在昂贵构建前约一分钟内阻断：`APPLY=36`、`SKIP_ALREADY_APPLIED=497`、`SKIP_SCOPE_EXCLUDED=60`、`BLOCKED_SCOPE_DEPENDENCY=12`；未进入 Maven、Docker、NAS 或测试服写入。
- 证据表明 `code-only` 同时承担“无全量快照”和“禁用 type=data 增量迁移”两个不同语义，无法表达日常程序升级。
- 正式范围调整为：`code-only` 保持绝不执行 type=data；新增 `app-release` 作为日常默认，包含版本化 required SQL/增量迁移但不包含 MySQL dump、MinIO 快照或 DCC object inventory；`with-data` 仍表示全量数据快照并要求显式确认。
- 同一个 `app-release` 不可变安装包必须可以用于测试服、正式服和备份服晋级；本任务仍只执行测试服发布。

### Current Blocker After r17 Test Deploy

- r17 轻量安装包构建成功并上传 NAS：`publishScope=app-release`、`component=intruoyi`、`684.73 MiB`、616 个文件；backend/frontend source commit 均为 `b88c242f0aa3030f387695b500b3fb6e85fa54d8`，dirty=0；包内无 MySQL dump、MinIO 快照或 DCC inventory。
- 测试服发布在增量迁移 `20260629_mes_smart_scheduling_role_scope` 失败：它要求菜单 900121/900122 仍启用，但测试服已应用更晚的 `20260709_mes_route_flow_config_unification` 和 `20260728_mes_scheduler_route_flow_list_permission`，后者正式下线旧菜单；目标迁移台账存在“后继已应用、前置缺失”的历史不闭合状态。
- r17 operation/lock 已正确标记 `FAILED` 并释放；前两条增量迁移已成功应用。应用容器仍运行旧 tag，失败后已把远端 `.env IMAGE_TAG` 恢复为实际运行版本 `release-20260903-main-invoice-assistant-test-r260903b-r1`。
- 禁止手工启用旧菜单、删除/伪造 migration ledger、直接标记旧迁移成功或修改失败 r17 包。
- 下一步需要从 `b88c242f0` 派生新的主程序迁移修复提交：让 `20260629` 在检测到正式的 20260709 替代拓扑时执行等价角色权限收敛而不要求已下线菜单重新启用；完成 BDD/TDD 与迁移门禁后用新 releaseTag 重建。

### Authorized Migration Fix Result

- 主程序修复分支：`codex/test-release-migration-chain-fix-20260910`。
- 新发布源提交：`0684dbd06`，基于 `b88c242f0`，只修改 `20260629_mes_smart_scheduling_role_scope.sql` 及对应回归测试。
- App worktree 已移动至合规路径 `D:\IntRuoyiWorktree\r260908c-app` 并登记 `int_main slot 38`；未启动本地分支运行态。
- 下一发布标签为全新 r18；禁止复用 r17。

## 2026-09-10 Baseline Dependency Promotion Update

- r23 失败根因已修复：基线排除项不再被无条件视为依赖已满足。
- 若本次待执行迁移直接或间接依赖某个基线排除的数据迁移，规划器会将整条未应用依赖链提升为 `APPLY`；无关且同 ID/file/SHA 的历史数据仍保持 `SKIP_BASELINE_SCOPE_EXCLUDED`。
- 聚焦测试与全量发布脚本回归通过：`1 passed`、`170 passed in 51.30s`。
- 使用 r23 真实 manifest、测试服捕获状态和当前运行基线计划重算通过：`APPLY=54`、`SKIP_ALREADY_APPLIED=507`、`SKIP_BASELINE_SCOPE_EXCLUDED=44`、`SKIP_ENV_NOT_ALLOWED=1`；所需菜单层级迁移与其权限迁移均为 `APPLY`。
- r23 已失败，禁止复用；下一步从主程序提交 `dfc481c40b8d3dfc637322518bbd40359b6082f3` 和新的维护脚本提交生成 r24，仅发布测试服。

## 2026-09-11 Resume After r30 Thread Close

- 用户说明 `r30` 线程已关闭，要求继续当前测试服发布任务。
- 本轮继续使用全新 r33，不复用 r15-r32 任一失败 releaseTag。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r33\m`，冻结提交 `0719d094b5dd6bc4a6e21e27ec938a49733b388a`。
- 应用 release worktree：`D:\IntRuoyiWorktree\r260908c-r33\a`，冻结提交 `512e179858db92c5aaf637726cf748f98967aff6`。
- 发布范围仍限测试服 `172.30.30.58` 的 `build-release -> publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服和审查服动作。
- `GREEN: experience-preflight-r33 -> PASS`：沿用测试服发布、构建、数据库、PowerShell、服务器访问、worktree、不可变安装包和无 fallback 门禁；高风险动作前必须验证 r33 worktree clean、发布包无 MySQL dump/MinIO/DCC 数据制品、测试服运行态五项一致。

## 2026-09-11 Resume r34 After Target Preflight Completion

- r33 已在 Maven 前被 `TARGET_PREFLIGHT_MISSING` 阻断并判废，不复用。
- 应用仓已补齐缺失的 3 个只读 target preflight 文件并提交 `d0942cf920980f79a7a6319f17ef8f88bd4be500`。
- 本轮继续使用全新 r34 release worktree：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r34\m`，提交 `0719d094b5dd6bc4a6e21e27ec938a49733b388a`；应用仓 `D:\IntRuoyiWorktree\r260908c-r34\a`，提交 `d0942cf920980f79a7a6319f17ef8f88bd4be500`。
- r34 仅允许测试服 `build-release -> publish-test`，禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服、备份服和审查服动作。
- `GREEN: experience-preflight-r34 -> PASS`：release worktree 均 clean；业务前端 `pnpm ignored-builds=None` 且 `frontend_dependency_preflight.cjs` 对 `cross-env/vite/vue-tsc` 返回 PASS；NAS 配置字段完整；离线后端基础镜像参数完整。

### r34 Result And r35 Source

- r34 已判废：schema-only 迁移演练在 Maven 前约 67 秒阻断，失败迁移为 `20260904_dcc_registration_certificate_download_project_optional`。
- 根因：`20260904_dcc_registration_certificate_download_optional_project_code` 已删除 `chk_dcc_reg_cert_access_request_project` 后，后续两个同意图迁移仍裸 `DROP CHECK`，在目标结构中约束不存在时报 `ERROR 3821`。
- 修复：三个注册证下载项目可选迁移改为先校验目标表存在，再通过 `information_schema.TABLE_CONSTRAINTS` 条件执行 `DROP CHECK`；表缺失仍 fail fast，不做静默成功。
- 验证：新增回归 `test_dcc_registration_certificate_optional_project_sql.py`，RED 为 `2 failed`，GREEN 为目标测试 `4 passed`；维护仓发布回归 `108 passed`，迁移策略 `605` PASS，`git diff --check` PASS。
- 新发布源提交：应用仓 `18bcfb225da38782e6622091eac5a521e546d46f`；下一 releaseTag 必须使用全新 r35，禁止复用 r34。

## 2026-09-11 r35 Build Attempt

- releaseTag：`release-20260911-verified-branch-app-r260908c-r35`，本地 cache/preflight 目录未被占用。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r35\m`，clean detached at `0719d094b5dd6bc4a6e21e27ec938a49733b388a`。
- 应用 release worktree：`D:\IntRuoyiWorktree\r260908c-r35\a`，clean detached at `18bcfb225da38782e6622091eac5a521e546d46f`。
- r35 前端依赖已按锁文件恢复；`pnpm ignored-builds=None`，`frontend_dependency_preflight.cjs` PASS；应用聚焦测试 `2 passed`。
- 构建命令范围：`PublishScope=app-release`、`Component=intruoyi`、测试服主机 `172.30.30.58`；显式传入正式/备份主机仅用于 build manifest/runtime env 参数完整性，不执行正式/备份动作。

### r35 Result And r36 Source

- r35 已判废：schema-only 迁移演练在 Maven 前约 63 秒阻断，失败迁移为 `20260904_mes_pqc_task_process_item_identity`。
- 根因：目标测试服迁移台账显示 `20260817_mes_pqc_item_level_task_identity` 已应用且 checksum 匹配，但 schema-only 快照中 `mes_pqc_inspection_task.qa_item_code` 实际缺失；后续唯一键迁移直接引用该列，导致 `ERROR 1054 Unknown column 'qa_item_code'`。
- 修复：`20260904_mes_pqc_task_process_item_identity` 在重复检测和建唯一键前先校验 `mes_pqc_inspection_task` 存在，并对 `qa_item_code` 执行显式 schema 闭包；表缺失仍 fail fast。
- 验证：新增 `test_mes_pqc_task_process_item_identity_sql.py`，RED 为 `2 failed`，GREEN 聚焦测试 `8 passed`；维护仓发布回归 `108 passed`，迁移策略 `605` PASS，`git diff --check` PASS。
- 新发布源提交：应用仓 `46b128f506b793674e593c70650733c00f574512`；下一 releaseTag 必须使用全新 r36，禁止复用 r35。

## 2026-09-11 r36 Build Attempt

- releaseTag：`release-20260911-verified-branch-app-r260908c-r36`，本地 cache/preflight 目录未被占用。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r36\m`，clean detached at `0719d094b5dd6bc4a6e21e27ec938a49733b388a`。
- 应用 release worktree：`D:\IntRuoyiWorktree\r260908c-r36\a`，clean detached at `46b128f506b793674e593c70650733c00f574512`。
- r36 前端依赖已按锁文件恢复；`pnpm ignored-builds=None`，`frontend_dependency_preflight.cjs` PASS；应用聚焦测试 `4 passed`。
- 构建仍为 `PublishScope=app-release`、`Component=intruoyi`，只允许后续测试服 `publish-test`。

### r36 Result And r37 Source

- r36 已判废：schema-only 迁移演练在 Maven 前约 15 秒阻断；没有 final manifest，没有 Maven、Docker、NAS 上传、真实测试库迁移或应用重启。
- 失败根因：演练脚本在源 MySQL 和一次性 MySQL 容器内使用默认 socket 连接，r36 远端输出 `ERROR 2002 ... Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock'`；这是脚本连接契约问题，不是业务 SQL 失败。
- 修复：迁移演练的 readiness、CREATE DATABASE、schema-only mysqldump、迁移执行和目标只读 preflight 均强制 `-h127.0.0.1 --protocol=TCP`，不再依赖容器 socket 路径。
- 验证：新增/调整发布预检回归，RED 为聚焦测试 `1 failed`，GREEN 为聚焦测试 `1 passed`、相关发布回归 `108 passed`、PowerShell AST `AST_OK`、`git diff --check` PASS。
- 新维护发布源提交：`8f38c94`；下一 releaseTag 必须使用全新 r37，禁止复用 r36。

## 2026-09-11 r37 Build Attempt

- releaseTag：`release-20260911-verified-branch-app-r260908c-r37`，本地 cache/preflight 目录需在构建前确认未占用。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r37\m`，clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`。
- 应用 release worktree：`D:\IntRuoyiWorktree\r260908c-r37\a`，clean detached at `46b128f506b793674e593c70650733c00f574512`。
- r37 前端依赖已按锁文件恢复；发布脚本同款 `frontend_dependency_preflight.cjs` 从前端目录返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。
- 构建范围仍为 `PublishScope=app-release`、`Component=intruoyi`；只允许后续测试服 `publish-test`。

### r37 Retired And r38 Source

- r37 在构建前复核时发现应用 release worktree 出现未提交迁移拆分改动；按 clean frozen source 规则判废，未执行 Maven、Docker、NAS、测试服数据库写入或应用重启。
- 该改动属于当前迁移门禁修复：把 `20260905_erp_kingdee_production_replenishment_list_sync` 中的菜单、角色和 job 配置拆出为独立 `type=config` 迁移，并补齐对应只读 target preflight；schema 迁移只保留建表。
- 验证：应用聚焦测试 `3 passed`，迁移策略 `status=passed migrationCount=606`，新 target preflight 合同 `TARGET_PREFLIGHT_CONTRACT_PASS`，`git diff --check` PASS。
- 应用修复提交：`95883471a1adae29c6045531074c3c05629fff30`，提交信息 `任务: 拆分生产补料单迁移配置`。
- 全新 r38 release worktree 已创建：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r38\m` at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用仓 `D:\IntRuoyiWorktree\r260908c-r38\a` at `95883471a1adae29c6045531074c3c05629fff30`。
- r38 前端依赖已按锁文件恢复，`pnpm ignored-builds=None`，发布脚本同款 `ops/release/frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。
- 下一步只允许使用 `release-20260911-verified-branch-app-r260908c-r38` 执行 `build-release -> publish-test`；继续禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服、备份服和审查服动作。

## 2026-09-11 r38 Result And r39 Source

- r38 已判废：schema-only 迁移演练在 Maven 前阻断；未执行 Maven、Docker、NAS 上传、测试服数据库迁移或应用重启。
- 失败迁移：`20260907_dcc_publication_notification`；错误 `Missing or duplicate DCC parent menu 6800`。
- 根因：`type=schema` 迁移混入菜单、通知模板、角色授权和租户套餐配置，导致空结构演练依赖目标业务数据。
- 修复：应用仓提交 `a62d4f95cd941ef2b569488b9479884225a3a016` 将 DCC 发布通知建表与业务配置拆分，并补齐同名 target readonly preflight；同时同步业务仓迁移策略排除 `target-preflight` 目录。
- 验证：聚焦测试 `15 passed`，业务仓迁移策略 `status=passed migrationCount=607`，新增 target preflight 合同 PASS。
- 下一 releaseTag 必须使用全新 `release-20260911-verified-branch-app-r260908c-r39`；维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r39\m` at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`，应用 worktree `D:\IntRuoyiWorktree\r260908c-r39\a` at `a62d4f95cd941ef2b569488b9479884225a3a016`。

## 2026-09-11 r39 Result And r40 Source

- r39 已判废：schema-only 迁移演练在 Maven 前阻断；未执行 Maven、Docker、NAS 上传、测试服数据库迁移或应用重启。
- 失败迁移：`20260908_system_signature_password_t1`；错误 `ERROR 1064 ... near '' at line 13`。
- 根因：MySQL 迁移包含 `CREATE PROCEDURE` 多语句过程体，但缺少 `DELIMITER`，客户端按默认分号截断。
- 修复：应用仓提交 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 为两个临时过程补齐 delimiter，并新增回归约束。
- 验证：T1 与发布相关聚焦测试 `16 passed`，业务仓迁移策略 `status=passed migrationCount=607`，`git diff --check` PASS。
- 下一 releaseTag 必须使用全新 `release-20260911-verified-branch-app-r260908c-r40`；维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r40\m` at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`，应用 worktree `D:\IntRuoyiWorktree\r260908c-r40\a` at `66a10cd33af5970f04277d5bea103ff0e3a7693e`。
