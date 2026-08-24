# Execution Log

## User Intent

用户明确授权先修复当前 app HEAD 的 0 字节 `TrainingRulesReadonlyTab.vue`，再基于修复后的已提交代码继续仅测试服发布；未提交改动不得进入构建产物，禁止正式服、备份服和推广动作。

## BDD

BDD: training rules page remains buildable -> Given a user opens the DCC training rules mapping view, When the frontend source is loaded and built, Then `TrainingRulesReadonlyTab.vue` must be a non-empty Vue SFC with a template and script, preserve the toolbar/mapping behavior and expose the existing training permission precheck; an empty or malformed file must fail before build and release.

## Fix Worktree

- Source HEAD frozen before fix: app `int_main@a0025c94278790badeefdc624af4372399e1207a`。
- Fix worktree: `D:\IntRuoyiWorktree\20260823-fix-training-rules-sfc`，branch=`codex/20260823-fix-training-rules-sfc`。
- Maintenance source remains `int_main@66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；no maintenance code change is in scope。

## TDD

- RED: `node tests/e2e/dcc-training-rules-sfc-integrity-static.spec.js` -> FAIL, `training rules component must not be empty`。
- RED: `node tests/e2e/dcc-training-rules-context-static.spec.js` -> FAIL, `培训规则页必须保留工具栏与映射区两个工作面`。
- Expected fix: restore the last known formal component implementation from the immediate pre-deletion commit, then rerun both contracts and frontend build.

## GREEN Fix Verification

- GREEN: `node tests/e2e/dcc-training-rules-sfc-integrity-static.spec.js` -> PASS。
- GREEN: `node tests/e2e/dcc-training-rules-context-static.spec.js` -> PASS。
- GREEN: `node tests/e2e/dcc-training-ux-prechecks-static.spec.cjs` -> PASS。
- GREEN: `pnpm ts:check` -> PASS。
- GREEN: `pnpm build:test` -> PASS，生成 `dist-test`。
- 修复提交：app `4535936e0b3c9afe75c5c48dfd63007ef04e577d`，仅包含恢复的 SFC 和新增静态完整性测试。

## Release Preparation Issue Log

## Frozen Release Input

- Git executable: `D:\Programs\Git-2.55.0.5\cmd\git.exe`，version `2.55.0.windows.5`。
- Maintenance target: branch source `int_main`，commit `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`。
- App target: task fix branch `codex/20260823-fix-training-rules-sfc`，commit `4535936e0b3c9afe75c5c48dfd63007ef04e577d`。
- 并发开发说明：app 主工作区在冻结后继续前进；依据用户“构建发布一开始 worktree 里记录的即可”的要求，不追赶后续提交，不把其未提交或后续提交纳入本次发布。
- Planned releaseTag: `r260823f`。
- Planned maintenance release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f\m`。
- Planned app release worktree: `D:\IntRuoyiWorktree\r260823f\a`。
- GREEN: experience-preflight -> PASS；已读取并应用 test-release、release-build、PowerShell、worktree、server-access、login-access、release-backup-restore 门禁；后续仅允许 `build-release -> publish-test`，禁止正式服/备份服/推广动作。

### ISSUE-001: 临时 fix worktree 未登记运行时槽位

- 现象：首次提交触发 `.githooks/pre-commit`，失败于 `No worktree port registry entry is registered for 'D:\IntRuoyiWorktree\20260823-fix-training-rules-sfc'`。
- 阶段：修复提交前置检查。
- 影响：提交暂时阻塞，未产生错误提交或发布产物。
- 原因判断：项目提交钩子强制校验附加 worktree 的运行时槽位登记；新建 worktree 尚未登记。
- 处理动作：运行 `scripts/runtime/reserve-worktree-slot.ps1`，为该 worktree 登记 `int_main` profile 的 slot 41（frontend `8256`、backend `48256`），随后重试提交。
- 结果：钩子通过，修复提交 `4535936e0` 成功生成。
- 是否可前置检查：是；创建 worktree 后立即运行槽位登记并执行 guard。
- 是否可自动化：是；创建发布/修复 worktree 的脚本应把 reserve 和 guard 作为原子前置步骤。
- 下次如何避免：不在未登记的附加 worktree 执行提交、构建或运行态操作；记录 slot 与端口证据。

## Issues

每个问题记录：现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免。

### ISSUE-002: 新增迁移缺少 release-migration 元数据

- 现象：首轮 `build-release` operation `op-2026-08-23T110119013778700Z-60ebf447-4ff4-4f9c-b2c3-829236ee29bc` 失败，提示 `20260822_mes_active_order_pick_list_binding.sql` 缺少首行 release metadata。
- 阶段：发布包构建前 migration policy gate。
- 影响：首轮 tag `release-20260823-intmain-training-r260823f-r1` 判废；未生成 package/manifest，未执行测试服写入。
- 原因判断：冻结 app 提交新增 SQL 时未同步声明 allowedEnvironments、dependsOn、type 和 riskLevel。
- 处理动作：先补静态回归测试并得到 RED，再补元数据；目标 pytest 与全量 migration policy gate PASS，提交 `c04c2e57b31f409e703aa1a4f550bd2d07a96453`。
- 结果：修复完成，后续从该提交创建全新 release worktree 和 releaseTag。
- 是否可前置检查：是。是否可自动化：是。
- 下次如何避免：build-release 前必须运行实际发布脚本使用的全量 migration policy gate；新增 SQL 未通过不得创建 operation。

### ISSUE-003: 本机预览门禁字段路径误读

- 现象：build preview 的 `publishScope`、publish-test preview 的 `releaseTag` 实际位于 `data.parameters`，本地证据脚本先按 arguments/顶层字段判断为 false。
- 阶段：build-release / publish-test preview。
- 影响：各发生一次只读 preview 门禁失败；没有创建 operation 或服务器写入。
- 原因判断：证据脚本未严格按 RuntimeControlActionPreviewVO 的结构化响应契约解析。
- 处理动作：改为读取 `parameters.publishScope` 与 `parameters.releaseTag`，重跑 preview 后全部检查为 true。
- 结果：仅修正本任务证据脚本，发布动作未重复提交。
- 是否可前置检查：是。是否可自动化：是。
- 下次如何避免：维护共享 preview schema validator，禁止任务脚本凭印象重复实现字段路径。

### ISSUE-004: eDHR 测试目标凭据未原子绑定

- 现象：`release-20260823-intmain-training-r260823f-r2` build operation `op-2026-08-23T111559418984100Z-a9888811-87f6-4853-87ea-93de95c1246f` 在 Object Lock verifier 返回 `InvalidAccessKeyId (403)`。
- 阶段：build-release 前置对象存储校验。
- 影响：r2 未生成 package/manifest，不得 publish-test。
- 原因判断：测试服当前 `.env` 保留正式端点 `172.30.30.57`、旧 bucket/凭据；隔离控制台未注入 `EDHR_S3_TEST_*`，导致环境字段混用。
- 处理动作：只读确认受控 `.env.copytest` 的 endpoint=`172.30.30.58:9000`、bucket=`edhr-retention-verifier-20260530` 和字段完整性；将其仅注入本任务控制台进程，不写回服务器、不落盘 secret。
- 结果：新 tag r3 build-release 通过 verifier 并 SUCCESS。
- 是否可前置检查：是。是否可自动化：是。
- 下次如何避免：隔离控制台启动前对 endpoint/bucket/access/secret 做同环境原子 presence + Object Lock read 验证，缺一项即 fail fast。

## r260823f2 Build Evidence

- Release worktrees：maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f2\m@66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；app `D:\IntRuoyiWorktree\r260823f2\a@c04c2e57b31f409e703aa1a4f550bd2d07a96453`；build 前均 clean。
- GREEN: maintenance `scripts/build.ps1` -> PASS，Maven tests 26/26；app `pnpm install --frozen-lockfile` + `pnpm rebuild --pending`，ignored builds=None。
- GREEN: build-release r3 -> SUCCESS；operation=`op-2026-08-23T112030256372800Z-3283cca5-1f91-4a61-bbe6-9f486c99f116`；package=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260823-intmain-training-r260823f-r3`。
- GREEN: manifest validator -> `MANIFEST_VALIDATION_PASSED`；manifest sourceRepos backend/frontend commit 均为 `c04c2e57b31f409e703aa1a4f550bd2d07a96453`、dirty=false；component=intruoyi；publishScope=code-only；changeSet.summary=`任务: 补充领料绑定迁移元数据`。
- GREEN: remote prepublish -> PASS；无 RUNNING lock、目标 tag migration 行为 0、旧 backend health=UP、frontend HTTP=200。

### ISSUE-005: publish-test 新镜像启动构造器注入失败

- 现象：r3 publish operation `op-2026-08-23T113924059150Z-a7647560-ff31-4df8-a8fa-8bd16a95ab98` 最终 FAILED；Spring 报 `MesProRouteVersionSnapshotMigrationRunner: No default constructor found`。
- 阶段：publish-test，目标迁移执行后启动一次性后端命令容器。
- 影响：r3 判废；测试服未切换新 backend/frontend 镜像；`.env IMAGE_TAG` 已漂移为 r3，release lock=FAILED。
- 原因判断：runner 有生产构造器和测试专用构造器，未显式标记 Spring 注入构造器；单元测试只直接 new 实例，未覆盖 Spring 构造器选择。
- 处理动作：冻结失败态；新增反射合同测试，RED 证明没有 `@Autowired`；在生产构造器添加显式 `@Autowired`；目标合同 + 原有 runner tests 共 5/5 PASS；提交 `c0d367dc778d294179c74898ed13b76583deb04f`。
- 结果：源代码根因已修复；r3 不复用，准备新 tag 和新 release worktree。
- 是否可前置检查：是。是否可自动化：是。
- 下次如何避免：所有带多个构造器的 Spring bean 必须有显式注入合同；发布前对会在 migration hook 启用的条件 bean 执行 Spring 实例化 smoke。

### ISSUE-006: publish-test 失败后的 env/镜像漂移

- 现象：失败后 `.env IMAGE_TAG=r3`，但实际 backend=`hotfix-20260814-route-submit-order-r1`、frontend=`release-20260813-intmain-head-test-r260812b-r2`；两容器仍 running，backend health=UP、frontend HTTP=200；target lock=FAILED；migration `APPLIED=1, SKIPPED_ALREADY_APPLIED=436, FAILED/RUNNING=0`。
- 阶段：publish-test 失败收束。
- 影响：只看 `.env` 会误判已发布；测试服务仍由旧镜像提供，r3 不满足验收。
- 原因判断：发布脚本先写 `.env` 并执行迁移，再启动目标镜像；启动失败后保留旧容器但未恢复 env tag。
- 处理动作：仅做只读证据冻结，不手工改锁/迁移/镜像；下一轮新 tag 发布必须重新验证 `.env`、实际镜像和 operation 一致。
- 结果：服务当前可用，但任务未完成。
- 是否可前置检查：部分。是否可自动化：是。
- 下次如何避免：部署失败收束应自动恢复 `.env IMAGE_TAG` 至实际运行 tag，且输出结构化 drift 证据；最终验收必须联合校验 env/compose/container/release-info。

## Route Runner Fix TDD

- BDD: route snapshot migration hook starts -> Given deploy-release enables `yudao.mes.route-snapshot-migration.mode`, When Spring creates `MesProRouteVersionSnapshotMigrationRunner`, Then the explicit production constructor is autowired and startup reaches the migration command instead of requesting a default constructor.
- RED: `mvn --% -pl yudao-module-mes -Dtest=MesProRouteVersionSnapshotMigrationRunnerSpringContractTest -Dsurefire.failIfNoSpecifiedTests=false test` -> FAIL，explicit Spring constructor annotation absent。
- GREEN: `mvn --% -pl yudao-module-mes -Dtest=MesProRouteVersionSnapshotMigrationRunnerSpringContractTest,MesProRouteVersionSnapshotMigrationCommandTest -Dsurefire.failIfNoSpecifiedTests=false test` -> PASS，5/5。
- Commit: `c0d367dc778d294179c74898ed13b76583deb04f`，message=`任务: 修复路线快照迁移启动注入`。
- Next release inputs：maintenance `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；app `c0d367dc778d294179c74898ed13b76583deb04f`；new worktrees `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f3\m` and `D:\IntRuoyiWorktree\r260823f3\a`。

### ISSUE-007: 路线快照报告校验的 PowerShell 引号构造错误

- 现象：r4 publish operation `op-2026-08-23T125137336286200Z-e52fa56c-9937-4eee-a49c-c7dc08331347` 在后端一次性启动已成功、迁移 hook 收束阶段失败；脱敏日志显示 `Invoke-RouteSnapshotIdentityMigrationCommand` 将 `status\ : \READY` 及后续 grep 参数当成未命名参数，返回 `PositionalParameterNotFound`。
- 阶段：publish-test，路线快照 identity backfill/readiness 报告验证。
- 影响：r4 判废；测试服未切换到 r4 实际镜像；r4 lock 已记录 FAILED；不得仅依据短暂启动成功判定发布成功。
- 原因判断：PowerShell 双引号字符串中错误使用反斜杠转义 (`\\\"`)，反斜杠不是 PowerShell 的引号转义符，导致 `Invoke-SshCommand` 调用被拆参。
- 处理动作：先新增静态回归测试；RED：`python -X utf8 -m pytest -q scripts/tests/test_route_snapshot_identity_report_command_contract.py` 失败；修复为单字符串拼接，使用 `grep -Eq` 的结构化 JSON 字段模式；GREEN：定向维护脚本测试 `23 passed`、PowerShell AST parse PASS；提交维护仓 `bc6def3` (`任务: 修复路线报告校验命令构造`)。
- 结果：脚本根因已修复；r4 不复用，准备维护 `bc6def3` + app `c0d367dc` 的新 release worktree 和 r5 tag。
- 是否可前置检查：是；可在发布前对所有 PowerShell 远程命令执行 AST/参数构造合同测试。
- 是否可自动化：是；将 PowerShell 字符串构造静态合同加入 release preflight，并禁止 `\\\"` 伪转义。
- 下次如何避免：发布脚本涉及 grep/JSON 引号时统一使用单引号拼接或 `-f` 格式化，先跑脚本合同测试再提交 publish operation；失败 tag 永不复用。

## r260823f3 Build/Publish Evidence

- r4 build worktrees：maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f3\m@66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；app `D:\IntRuoyiWorktree\r260823f3\a@c0d367dc778d294179c74898ed13b76583deb04f`；build 前均 clean。
- GREEN: runtime-control `scripts/verify_contracts.py` -> PASS；r4 build preview gate -> PASS；build operation `op-2026-08-23T122749017675600Z-22608d84-e33f-42a2-b764-b51466f6f573` -> SUCCESS。
- GREEN: package `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260823-intmain-training-r260823f-r4`；manifest validator -> `MANIFEST_VALIDATION_PASSED`；sourceRepos backend/frontend=`c0d367dc778d294179c74898ed13b76583deb04f`, dirty=false；changeSet.summary=`任务: 修复路线快照迁移启动注入`；publishScope=code-only。
- GREEN: r4 publish preview gate -> PASS；only target environment=test and server `172.30.30.58`.
- ISSUE-007 operation log and remote failure evidence are recorded in `publish-test-log-tail-r260823f3-r4.redacted.txt`; no prod/backup action was submitted.

### ISSUE-008: r5 远端 JSON 双引号在 SSH 命令层丢失

- 现象：r5 后端一次性启动成功，远端报告真实为 `status=READY`、`blockerCount=0`，但携带 JSON 双引号的 grep 合同经 PowerShell/SSH 传递后退出码为 1。
- 阶段：publish-test，路线快照报告就绪校验。
- 影响：r5 operation `op-2026-08-23T134640336614600Z-2a4edccf-485b-4d17-a9e0-abe23fd86ce4` 判定 FAILED；未切换目标镜像，不得判定测试发布成功。
- 原因判断：本地 PowerShell、SSH 参数传递与远端 shell 共同处理引号，JSON 字段名双引号没有按预期保留。
- 处理动作：先以只读 SSH 确认报告真实 READY/0，再将命令收敛为不依赖 JSON 双引号的 token 模式，定向及迁移策略测试 23 passed，维护提交 `fbd88f74424215682fe30aa96ba95f03a443116d`。
- 结果：r5 不复用；从 `fbd88f7` 创建 r6 clean worktree 重建。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：命令合同测试必须覆盖经过 SSH 后的实际 shell 参数，而非只检查 PowerShell 源字符串。

### ISSUE-009: r6 首次 preview 命中旧控制台配置

- 现象：r6 首次 build preview 返回的 backend/frontend root 仍指向 r260823f4。
- 阶段：build-release preview。
- 影响：preview 门禁失败；未创建 operation、未写服务器。
- 原因判断：端口 `48181` 仍由上一轮任务控制台进程提供服务。
- 处理动作：停止本任务上一轮 PID 42712，按 r260823f5 config 重启控制台；重新 preview 后全部字段 PASS。
- 结果：后续仅提交一次 r6 build operation。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：提交 operation 前把控制台 config path、source roots、state dir 和服务 PID 纳入同一 preview identity gate。

## r260823f5 Build/Publish Evidence

- Release worktrees：maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f5\m@fbd88f74424215682fe30aa96ba95f03a443116d`；app `D:\IntRuoyiWorktree\r260823f5\a@c0d367dc778d294179c74898ed13b76583deb04f`；build 前及包校验后均 clean。
- GREEN: maintenance build、Maven tests 26/26、app frozen install/rebuild、runtime-control contracts -> PASS。
- GREEN: r6 build operation `op-2026-08-23T160900644893400Z-1b1f8405-c037-4472-995e-a2d9c452675d` -> SUCCESS；manifest validator=`MANIFEST_VALIDATION_PASSED`；backend/frontend source commit 均为 `c0d367dc778d294179c74898ed13b76583deb04f`、dirty=false；changeSet.summary=`任务: 修复路线快照迁移启动注入`。
- FAILED: r6 publish operation `op-2026-08-23T164819432616300Z-e2432055-a2fe-4eb2-9ea5-85f485f66aad` -> FAILED；未执行 prod/backup/mark-tested/promotion。

### ISSUE-010: blockerCount 正则未容纳 JSON 字段名闭合引号

- 现象：r6 日志显示后端启动成功且首个 `grep -Eq 'READY'` 通过；随后 `grep -Eq 'blockerCount[[:space:]]*:[[:space:]]*0'` 对真实行 `\"blockerCount\" : 0` 返回 1。
- 阶段：publish-test，路线快照报告就绪校验。
- 影响：r6 operation 判定 FAILED；发布未完成，禁止进入运行态成功判定。
- 原因判断：正则在 `blockerCount` 后只允许空白和冒号，实际 JSON 字段名还有闭合双引号；上一轮静态测试只验证脚本文本，没有使用真实报告样本验证匹配语义。
- 处理动作：冻结 r6 失败证据；创建 maintenance 分支 `codex/20260824-fix-route-report-blocker-regex`，先补真实 JSON 报告匹配回归测试，再最小修正命令合同。
- 结果：修复进行中；r6 永不复用，后续必须创建全新 r7 tag/worktree。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：报告命令合同必须把真实 JSON fixture 经同一 grep 模式执行，不能只做源字符串 contains 断言。

## Route Report Blocker Regex Fix TDD

- BDD: route snapshot readiness report accepts valid JSON -> Given the generated report contains `\"status\" : \"READY\"` and `\"blockerCount\" : 0`, When publish-test evaluates the remote readiness command, Then both checks exit 0 and deployment continues.
- RED: `python -X utf8 -m pytest -q scripts/tests/test_route_snapshot_identity_report_command_contract.py` -> FAIL，真实 JSON fixture 的 `"blockerCount" : 0` 未被旧模式匹配（1 failed, 1 passed）。
- GREEN: `python -X utf8 -m pytest -q --basetemp D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f5\pytest-tmp-route3 scripts/tests/test_route_snapshot_identity_report_command_contract.py scripts/tests/test_release_sql_preflight_gate.py` -> PASS（24 passed）；PowerShell AST parse -> PASS。
- GREEN: 对 r6 远端真实报告执行新合同 `grep -Eq 'blockerCount[^:]*:[[:space:]]*0'` -> `ROUTE_REPORT_READY`；SSH carrier 仍输出非致命 closed-socket warning，退出码为 0。
- Commit: maintenance `2307b93c2ce541b7458c4e7c524810d0b1f6687f`，message=`任务: 修复路线报告阻塞数匹配`；工作树提交后 clean。

### ISSUE-011: 测试服生产角色迁移临时表排序规则冲突

- 现象：r7 publish operation `op-2026-08-24T013810334620500Z-096473bc-e705-41f7-9b26-c01e2bbdb55a` 在执行 `20260814_mes_production_release_roles.sql` 时，MySQL 返回 `ERROR 1267 (HY000) at line 477: Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and (utf8mb4_unicode_ci,IMPLICIT) for operation '='`。
- 阶段：publish-test，required database SQL 执行；此前 route report 校验已通过。
- 影响：r7 判定 FAILED；目标 operation lock=FAILED，测试服未切换目标镜像；不得继续运行态成功验收。
- 原因判断：迁移创建的 Memory 临时表字符串列继承服务器默认 `utf8mb4_general_ci`，与 `system_menu/system_role/system_users` 等现有列的 `utf8mb4_unicode_ci` 在 join/where 比较时冲突。
- 处理动作：冻结 r7 失败日志；从 app `c0d367dc778d294179c74898ed13b76583deb04f` 创建修复 worktree `D:\IntRuoyiWorktree\20260824-fix-production-release-roles-collation`；新增临时表排序规则合同测试，先 RED，再为五个字符串临时表固定 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`。
- 结果：定向迁移合同 + release migration policy gate `15 passed`；修复提交待生成，后续必须使用全新 app commit/releaseTag/worktree。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：发布前在目标数据库 collation 配置下执行所有 required SQL 的真实 dry-run/隔离库 smoke；静态合同要求临时表字符串列明确字符集与排序规则。

## Production Release Roles Collation Fix TDD

- BDD: production role migration joins remain collation-safe -> Given target MySQL uses `utf8mb4_general_ci` by default while system tables use `utf8mb4_unicode_ci`, When the migration joins string columns from its temporary tables to system tables, Then it executes without `ERROR 1267` collation mismatch.
- RED: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> FAIL，新增临时表 collation 合同失败（6 passed, 1 failed）。
- GREEN: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> PASS（7 passed）。
- GREEN: `python -X utf8 -m pytest -q --basetemp D:\IntRuoyiWorktree\20260824-fix-production-release-roles-collation\pytest-tmp-sql script/tests/test_mes_production_release_roles_sql.py script/tests/test_release_migration_policy_gate.py` -> PASS（15 passed）。

### ISSUE-012: 生产角色迁移递归遍历重复打开临时表

- 现象：r8 publish operation `op-2026-08-24T025804907117100Z-017adf02-a2a4-4b00-b72e-a6407c236dbd` 通过排序规则修复后，在同一迁移第 477 行报 `ERROR 1137 (HY000): Can't reopen table: 'tmp_mes_production_release_required_role_menu'`。
- 阶段：publish-test，required database SQL 执行。
- 影响：r8 判定 FAILED；目标 lock=FAILED，未进入镜像切换和运行态验收。
- 原因判断：MySQL 不允许在同一个语句中把临时表同时作为 `INSERT` 目标和 `SELECT` 来源；原递归 parent walk 正是该模式。
- 处理动作：冻结 r8 失败证据；从 app `ac62dd455d592877a2f0be2a7a4fcac0e741b304` 创建修复 worktree `D:\IntRuoyiWorktree\20260824-fix-production-release-role-menu-reopen`；新增 self-read 合同测试先 RED，再引入 `_next` 临时表执行两步写入并删除缓冲表。
- 结果：迁移合同 8 passed，迁移策略 gate 合计 16 passed；修复提交 `ae05e0d8c387fd4fdc39864baded8968337e4867`，工作树 clean；后续必须创建全新 releaseTag/worktree。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：required SQL preflight 必须静态拒绝临时表 self-read/self-write，并在真实 MySQL 版本隔离库执行迁移 smoke；不要只依赖脚本源代码检查。

## Required SQL Temp-Table Reopen Fix TDD

- BDD: recursive role-menu expansion avoids MySQL temp-table reopen -> Given the required role-menu set must repeatedly add parent menus, When the migration expands one level, Then it reads the current table into a separate `_next` temporary table before inserting into the accumulator.
- RED: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> FAIL，缺少 `_next` 缓冲且检测到 self-read（7 passed, 1 failed）。
- GREEN: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> PASS（8 passed）。
- GREEN: `python -X utf8 -m pytest -q --basetemp D:\IntRuoyiWorktree\20260824-fix-production-release-role-menu-reopen\pytest-tmp-sql script/tests/test_mes_production_release_roles_sql.py script/tests/test_release_migration_policy_gate.py` -> PASS（16 passed）。
- Commit: app `ae05e0d8c387fd4fdc39864baded8968337e4867`，message=`任务: 修复生产角色菜单临时表遍历`。

## r260823f6/r7/r8 Evidence

- r7 build `op-2026-08-24T011840854040700Z-e3c70ff4-496c-453b-ba89-9d9b1f4532c0` -> SUCCESS；manifest source commit `c0d367dc7`、dirty=false；publish `op-2026-08-24T013810334620500Z-096473bc-e705-41f7-9b26-c01e2bbdb55a` -> FAILED at collation `ERROR 1267`。
- r8 build `op-2026-08-24T022754939741800Z-942b4100-1f3a-46ff-9a65-f5857e54a90a` -> SUCCESS；package `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260823-intmain-training-r260823f-r8`；manifest validator PASS；source commit `ac62dd455`、dirty=false；publish `op-2026-08-24T025804907117100Z-017adf02-a2a4-4b00-b72e-a6407c236dbd` -> FAILED at temp-table reopen `ERROR 1137`。
- r8 worktrees：maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f7\m@2307b93c`、app `D:\IntRuoyiWorktree\r260823f7\a@ac62dd455`，build/publish 前 clean；r9 app fix worktree `D:\IntRuoyiWorktree\20260824-fix-production-release-role-menu-reopen@ae05e0d8` clean。

## r260823f6 Frozen Release Input

- ReleaseTag: `release-20260823-intmain-training-r260823f-r7`；失败的 r6 tag 不复用。
- Maintenance worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823f6\m`，detached HEAD `2307b93c2ce541b7458c4e7c524810d0b1f6687f`，创建后 Git changes=0。
- App worktree: `D:\IntRuoyiWorktree\r260823f6\a`，detached HEAD `c0d367dc778d294179c74898ed13b76583deb04f`，创建后 Git changes=0。
- 构建目录：maintenance 根目录与 app 的 `IntRuoyiBackend`/`IntRuoyiFronted`；仅使用上述 frozen worktree，不追赶并发分支新提交。
- GREEN: experience-preflight -> PASS；创建 worktree 前已确认目标路径不存在，检出进程完成后重新校验 clean；检出中间态的大量暂态删除未用于构建或结论。

### ISSUE-013: 权限一致性守卫重复读取角色临时表

- 现象：r9 build-release 与 manifest 校验均通过，但 publish operation `op-2026-08-24T040413177429900Z-1b67a355-3573-46c7-b771-2f9b0711e562` 在 `20260814_mes_production_release_roles.sql` 第 489 行 `CALL` 阶段报 `ERROR 1137 (HY000): Can't reopen table: 'role'`。
- 阶段：publish-test，required database SQL 执行；排序规则和递归 `_next` 修复均已通过。
- 影响：r9 判定 FAILED，目标锁释放为 FAILED，未进入目标镜像切换和运行态验收；不得手工重置锁或复用 r9。
- 原因判断：同一个 `IF EXISTS (...) OR EXISTS (...)` 权限一致性表达式分别从同一临时表 `tmp_mes_production_release_role` 读取两次。MySQL 对临时表在同一语句中的重复打开直接返回 1137，错误消息显示第二个别名 `role`。
- 处理动作：冻结 r9 失败日志；在 `D:\IntRuoyiWorktree\20260824-fix-production-release-role-menu-check` 先新增重复读取回归测试，RED 为 8 项通过/1 项失败；新增 `tmp_mes_production_release_role_check` 独立检查表，第二个 `OR EXISTS` 使用该表并在清理阶段显式 DROP；GREEN 为迁移合同 9 passed、迁移策略门禁合计 17 passed；提交 app `c9b510463` (`任务: 修复角色权限检查临时表重复打开`)。
- 结果：r9 永不复用；下一轮必须使用 app `c9b510463` 创建新的 r10 release worktree/tag。
- 是否可前置检查：是；发布前可静态检测同一 SQL 语句/IF 表达式中临时表名的重复引用，并在目标 MySQL 版本隔离库执行 required SQL smoke。
- 是否可自动化：是；将临时表重复打开合同加入 migration policy gate，遇到同一语句重复 `FROM tmp_*` 直接 fail fast。
- 下次如何避免：不得仅验证递归循环；权限一致性、汇总、校验类 SQL 也必须覆盖 MySQL 临时表单语句引用限制，失败 tag 必须废弃并从新提交重建。

## Required SQL Permission Guard Temp-Table Reopen Fix TDD

- BDD: permission consistency validation avoids temp-table reopen -> Given two role permission checks are combined by `OR`, When the required migration validates both directions, Then each branch reads a distinct temporary table and MySQL does not reopen the same temporary table in one statement。
- RED: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> FAIL，新增守卫测试发现旧 `IF` 对 `tmp_mes_production_release_role` 有 2 次引用（8 passed, 1 failed）。
- GREEN: `python -X utf8 -m pytest -q script/tests/test_mes_production_release_roles_sql.py` -> PASS（9 passed）。
- GREEN: `python -X utf8 -m pytest -q --basetemp D:\IntRuoyiWorktree\20260824-fix-production-release-role-menu-check\pytest-tmp-sql script/tests/test_mes_production_release_roles_sql.py script/tests/test_release_migration_policy_gate.py` -> PASS（17 passed）。
- Commit: app `c9b510463`，worktree branch `codex/20260824-fix-production-release-role-menu-check`；提交前已登记 runtime slot 32（frontend 8207/backend 48207），工作树 clean。

### ISSUE-014: r10 构建 operation 在对话中断后遗留本地 RUNNING

- 现象：r10 build operation 在前端/Docker 打包阶段因本轮对话中断，控制台进程已退出但本地 operation JSON 仍为 RUNNING，日志未推进。
- 阶段：build-release。
- 影响：无法把该 operation 当作成功或失败依据，若直接继续会造成重复提交或误判构建状态。
- 原因判断：长耗时构建与交互会话生命周期耦合，operation 状态持久化没有在本地进程异常退出时自动收敛。
- 处理动作：保留原 operation 和日志证据，未重用其 releaseTag；重新启动当前 r11 控制台并提交全新 build operation。
- 结果：r10 记录封存为中断失败，r11 build operation op-2026-08-24T115227267149700Z-05373329-a53c-4c18-902b-428b115ecb68 SUCCESS。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：长操作必须以持久化 operation final 与最后日志时间为准，进程退出后自动标记 FAILED/INTERRUPTED，并禁止同一 releaseTag 再次提交。

### ISSUE-015: r11 首次 preview 使用旧维护控制台身份

- 现象：r11 首次 preview 仍解析到 f9 维护仓/前端路径，未提交 build operation。
- 阶段：build-release preview。
- 影响：构建来源无法证明为 r11 worktree，触发 fail fast；未构建、未发布。
- 原因判断：48181 旧控制台进程仍持有 f9 runtime-control 配置。
- 处理动作：停止本任务旧控制台 PID，启动 r260823f10 专用配置，重新执行 preview identity gate。
- 结果：重试 preview 的 source roots、state dir、releaseTag、test-only scope 全部 PASS；只有第二次 build operation 被提交。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：每次 release worktree 必须生成唯一控制台 config/state-dir/端口绑定，preview 读取并校验进程命令行与配置摘要。

## r260823f10/r11 Build and Manifest Evidence

- Release worktrees：maintenance D:/ProjectPackage/Int/IntRuoyiWorktrees/r260823f10/m@2307b93c2ce541b7458c4e7c524810d0b1f6687f；app D:/IntRuoyiWorktree/r260823f10/a@4f1f847b63bd82bb53ffc0081d7eeecfb1f5c47f；构建前后均 clean，构建期间未读取主工作区脏改动。
- 构建目录：E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260823-intmain-training-r260823f-r11。
- GREEN: build-release operation op-2026-08-24T115227267149700Z-05373329-a53c-4c18-902b-428b115ecb68 -> SUCCESS；Maven backend BUILD SUCCESS；frontend pnpm build:test 成功；Docker package 成功。
- GREEN: manifest validator -> PASS（MANIFEST_VALIDATION_PASSED）；manifest.json 与 release-manifest.json releaseTag=r11，双 sourceRepos commit=4f1f847b63bd82bb53ffc0081d7eeecfb1f5c47f、dirty=false，changeSet.summary=任务: 修复生产角色权限临时表重复打开，publishScope=code-only。

## r260823f10/r11 Publish Evidence

- GREEN: publish preview gate -> PASS；environment=test、noPromotion=true、noRequireTested=true；未提交 mark-tested/promote-prod/promote-backup。
- GREEN: publish-test operation op-2026-08-24T130555285358Z-d4c042ba-6f92-4f8e-a4d1-a380601bca5f -> SUCCESS；范围仅测试服。
- GREEN: remote runtime probe remote-runtime-r260823f10-r11.json -> PASS；.env IMAGE_TAG、backend/frontend 实际镜像 tag、容器 running|true|0、backend health HTTP=200/body.status=UP、frontend HTTP=200、frontend release-info.json HTTP=200、releaseTag/packageId/publishScope/sourceRepos/changeSet 均一致、目标最新 release lock=APPLIED、RUNNING lock=0、目标迁移 FAILED/RUNNING=0。
- 备注：数据库 release lock 的内部 operation_id 使用 releaseTag 作为锁键，不等于控制台 operation id；验证改为“该 releaseTag 最新锁 APPLIED”，未错误要求两套 ID 相等。

## Real Page and Runtime Console Evidence

- BDD: test frontend page is reachable -> Given r11 is deployed to test host, When Playwright opens http://172.30.30.58:8081/, Then the real login page loads with title 瑛泰管理系统 - 登录, HTTP/API requests return 200 and browser console has zero errors.
- GREEN: Playwright test frontend page -> PASS；登录页真实打开，tenant lookup/captcha/login endpoints HTTP=200，console errors=0；截图 output/playwright/r11-test-frontend-login.png。认证后业务页未冒用凭据继续：当前 admin 密码已过期，tenant selector 返回无数据，记录为 ISSUE-016。
- BDD: runtime console shows the deployed release -> Given publish-test operation is SUCCESS, When operator opens http://127.0.0.1:48181/ and opens 版本变更说明, Then test releaseTag and change items match r11 and prod/backup remain unreported.
- GREEN: Playwright runtime console -> PASS；operation row SUCCESS，测试服 releaseTag=r11，版本变更说明显示“发布包：r11 / 组件范围：intruoyi / 提交：4f1f847b63bd 任务: 修复生产角色权限临时表重复打开”，正式服/备份服均“未上报”，console errors=0；截图 output/playwright/r11-runtime-console.png。

### ISSUE-016: 测试服认证后页面无法继续

- 现象：真实打开测试前端登录页后，预填的 芋道源码/admin 提交返回“密码已过期，请修改密码后再登录”；租户选择接口随后返回无数据，无法从页面登录测试租户 aoteman。
- 阶段：发布后真实页面验证。
- 影响：无法在本轮用认证后的业务路由做只读页面检查；公共登录页、静态 release-info.json、远端 HTTP 和运行控制台版本说明均已独立通过。
- 原因判断：测试服登录基线账号已过期，当前任务上下文未提供新的远端凭据；不能猜测密码、修改账号或切换环境。
- 处理动作：保留登录页、网络 200、console errors=0 和失败提示截图；未执行任何账号/租户写入或 API 绕过。
- 结果：按发布验收范围，前端入口可达且运行控制台版本/变更说明通过；认证后业务页作为已知残余缺口记录。
- 是否可前置检查：是；是否可自动化：是。
- 下次如何避免：发布前增加只读登录基线检查，确认测试租户账号有效/密码未过期；缺失时在页面门禁阶段明确 BLOCKED，不要在发布后临时猜凭据。

## Closeout Evidence

- GREEN: task-closeout preview -> PASS；保留 `task.md`、`execution-log.md`、`verification-report.md`，其余本任务临时证据、脚本、截图和操作输出列入删除清单。
- GREEN: task-closeout apply -> PASS；本任务附属产物已清理，未删除其他任务文档或并发 worktree。
- GREEN: release worktree cleanup -> PASS；本次 r11 maintenance/app 物理目录已删除且不再出现在 Git `worktree list --porcelain`，既有修复 worktree 与并发 worktree 保留；本次 release 未产生需合回 `int_main` 的新提交。
- GREEN: runtime console restore -> PASS；本任务 r11 控制台进程已停止，维护仓稳定 JAR `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 已恢复监听 `127.0.0.1:48181`，`/actuator/health` HTTP=200、status=UP。
- Final status: completed；仅测试服 r11 发布成功，正式服/备份服及 `mark-tested`/promotion 均未执行。
