# 一键式不可变程序发布工作流测试计划

- Task ID: `one-button-app-release-20260911`
- Created: `2026-09-11T09:20:03+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Basis: `prd.md` 的 P1-P5、P1-AC1 至 P5-AC5、R31-R44 与 Done Definition

## Test Scope

- 验证标准流程只能生成和消费不含业务数据的 `PublishScope=app-release` 程序包，并覆盖源码冻结、CI 前置门禁、迁移策略、目标只读 preflight、NAS READY 与不可变摘要。
- 验证持久化 ReleaseWorkflow 状态机、CAS、阶段证据、租约锁、心跳、超时、取消、重试和重启恢复。
- 验证构建完成后与每次部署前两次独立白名单、禁止项、敏感值和全包哈希扫描。
- 验证测试发布、测试证明和正式晋级始终绑定同一 releaseTag 与 package digest，期间不得重建或修改包。
- 验证三按钮运行控制台的 API 合同、错误可见性、刷新恢复、可访问性和响应式布局；R31-R44 每项至少有自动负例或恢复用例并证明下游副作用为零。
- 数据备份、数据恢复、灾难恢复和 IntRuoyi 业务功能变更不在本测试范围。
- 本计划阶段及未获授权的执行阶段均不进行测试服真实写入。
- 正式服只验证只读 preview、前置守卫、授权要求与零写入事实，绝不执行真实写入。

## Environment

- 所有命令从本任务独立且 clean 的实施 worktree 根目录在 Windows PowerShell 5.1 中逐行执行。
- PowerShell 会话显式使用 UTF-8；任一命令非零退出立即停止，不使用双与号串联符；必备工具为 Java 17、Maven、Node.js、Corepack/pnpm、Python UTF-8、Git、Docker 和 Playwright 1.60.0。
- 最终产品集成与 Playwright 验收固定从 `http://localhost:8081/infra/monitors/runtime-control` 开始；先登录测试租户 `aoteman`，所有创建/操作通过真实页面完成，API 只用于页面路径完成后的最终只读校验。维护仓 standalone 控制台（例如 `127.0.0.1:48181`）仅用于后端契约/预览，不得作为产品 E2E 通过依据。
- Playwright 固定使用 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 的 1.60.0 依赖及项目浏览器缓存。当前核验该目录缺少 `package.json`、`node_modules\playwright` 和 `.bin\playwright.cmd`，因此 P4/P5 保持 blocker；不得用 `npx` 临时下载、其它 Playwright 版本或维护仓页面兜底。
- 浏览器截图、trace 和录像写入 `output/playwright/one-button-app-release-20260911/`，不得写入任务目录。
- workflow state、测试制品、隔离 NAS 目录和进程日志均使用任务专属临时目录；preset 必须完整，敏感配置只验证引用存在和脱敏结果。
- 真实测试服步骤仅在用户另行明确授权且 experience-preflight 通过后执行。
- 正式服始终保持写开关关闭；测试仅允许 preview 和必然阻断的负路径。

## Accounts and Fixtures

- `source-approved`：包含 `713c64112d7b626a2ba71788fd36cc32d686addc` 修复或等价提交的批准源。
- `source-dirty`：仅供冻结负例使用的任务临时仓，含一个可识别未提交文件。
- `workflow-created`、`workflow-ready`、`workflow-tested`：由真实持久化模型生成的本地测试记录，不伪造服务器成功。
- `lease-active`、`lease-expired`、`state-corrupt`：用于并发、恢复和损坏状态阻断；`app-release-valid` 只含白名单文件、自包含 verifier、required SQL、manifest 和逐文件 SHA-256。
- `app-release-tampered`：分别注入禁止文件、未登记文件、目录穿越、外链、哈希漂移和敏感值命中。
- `migration-r31-r39`：逐项复现缺 preflight、误分类、缺引用、非幂等、schema 漂移、隐式 socket、脏源、类型不纯和缺 delimiter。
- `nas-r40-r42` 与 `deploy-r43-r44`：隔离模拟缺 READY、异常 cache、旧环境文件、原子改名冲突、preset 漂移、历史数据约束、切换失败和中断恢复。
- 测试操作者覆盖构建、测试发布、正式晋级三种独立权限；正式授权使用本地失效/缺失引用负例。
- 真实浏览器使用测试租户 `aoteman` 登录；任何 E2E 写入只允许发生在测试租户，禁止修改芋道源码租户。登录凭据只从 `E:\IntRuoyi\docs\login-access.md` 的受控入口使用，不写入测试代码、日志或证据。
- 任一工具、fixture、preset 或 evidence 目录缺失均记为 blocker，不得 mock 成功或跳过。

## Commands

以下命令均为 PowerShell 5.1 命令；外部命令必须逐条运行并立即检查 `$LASTEXITCODE`，不得用分号把多个外部命令串在同一条语句中。

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'
$releaseButtonMaintenanceRoot = 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m'
$releaseButtonAppRoot = 'D:\IntRuoyiWorktree\r260911-release-button\a'
$PSVersionTable.PSVersion
java -version
if ($LASTEXITCODE -ne 0) { throw 'java -version failed' }
mvn -version
if ($LASTEXITCODE -ne 0) { throw 'mvn -version failed' }
node --version
if ($LASTEXITCODE -ne 0) { throw 'node --version failed' }
corepack pnpm --version
if ($LASTEXITCODE -ne 0) { throw 'pnpm --version failed' }
python -X utf8 --version
if ($LASTEXITCODE -ne 0) { throw 'python --version failed' }
git --version
if ($LASTEXITCODE -ne 0) { throw 'git --version failed' }
docker version
if ($LASTEXITCODE -ne 0) { throw 'docker version failed' }
& 'D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\.bin\playwright.cmd' --version
if ($LASTEXITCODE -ne 0) { throw 'playwright --version failed' }
```

- `C01`：`mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseWorkflowContractTest,ReleaseSourceFreezeTest,ReleaseWorkflowGateOrderTest' test`
- `C02`：`mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseWorkflowStoreTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowSecurityTest' test`
- `C03`：`python -X utf8 -m pytest -q "$releaseButtonMaintenanceRoot\scripts\tests\test_release_workflow_preflight.py" "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" "$releaseButtonMaintenanceRoot\scripts\tests\test_app_release_package_governance.py" "$releaseButtonMaintenanceRoot\scripts\tests\test_release_deployment_transaction.py"`
- `C04`：`node "$releaseButtonAppRoot\IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs"`
- `C05`：`corepack pnpm --dir "$releaseButtonAppRoot\IntRuoyiFronted" ts:check`；通过后单独执行 `corepack pnpm --dir "$releaseButtonAppRoot\IntRuoyiFronted" build:test`。
- `C06`：从 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 运行 `node .\node_modules\playwright\cli.js test --config "$releaseButtonAppRoot\IntRuoyiFronted\tests\e2e\playwright.config.ts" "$releaseButtonAppRoot\IntRuoyiFronted\tests\e2e\one-button-app-release.spec.ts"`。
- `C07`：`mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra test`
- `C08`：`python -X utf8 -m pytest -q "$releaseButtonMaintenanceRoot\scripts\tests" "$releaseButtonMaintenanceRoot\tests"`
- `C09`：`node --test "$releaseButtonMaintenanceRoot\scripts\tests\publish_release_info_contract.test.mjs" "$releaseButtonMaintenanceRoot\scripts\tests\publish_image_tar_transfer_contract.test.mjs" "$releaseButtonMaintenanceRoot\scripts\tests\publish_frontend_deploy_sql_gate_contract.test.mjs"`
- `C10`：`mvn -f "$releaseButtonMaintenanceRoot\backend\pom.xml" test`，只验证保留的 standalone 诊断/合同同步，不替代主程序后端 `C07`。
- `C11-PY`：`python -X utf8 -m pytest -q "$releaseButtonMaintenanceRoot\scripts\tests\test_release_digest_vectors.py"`。
- `C11-JAVA`：`mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseDigestVectorTest' test`。
- `C11-PS`：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$releaseButtonMaintenanceRoot\scripts\tests\verify-release-digest-vector.ps1"`。

固定摘要向量必须逐字节使用：`docker-compose.yml` 内容为 `services:<LF>`（10 bytes，SHA-256 `fa73fccdc99ea835967c7dee7efbed1f3ca87260d92931850fdd66da8cb12f1d`）；`required-sql/001.sql` 内容为 `SELECT 1;<LF>`（10 bytes，SHA-256 `b4e0497804e46e0a0b0b8c31975b062152d551bac49c3c2e80932567b4085dcd`）。按 path UTF-8 无符号字节序生成的 packageDigest 必须为 `b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273`。精确 manifest bytes 为 `{"schemaVersion":2,"packageDigest":"b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273"}<LF>`，manifestDigest 必须为 `bb44ed6ea9550e067c1a2af3a105a0989503b046646f26bd1bac19455bee2800`。`C11-PY/JAVA/PS` 三者必须完全一致。

严格 TDD 顺序：

- `P1`：RED 先增加 T01-T03 与固定摘要向量并运行 `C01`、`C03`、`C11-PY/JAVA/PS`，预期旧合同失败；GREEN 最小实现后逐项重跑；REGRESSION 运行 `C07`、`C08`、`C09`、`C10`。
- `P2`：RED 先增加 T04-T06 并运行 `C02`，预期状态/安全合同失败；GREEN 最小实现后重跑 `C02`；REGRESSION 运行 `C01`、`C07`。
- `P3`：RED 先增加 T07-T11 与 R31-R44 的独立命名 fixture，按“R31-R44 唯一命令映射”逐项运行，预期门禁/事务断言失败；GREEN 最小实现后逐项重跑；REGRESSION 运行 `C01`、`C02`、`C07`、`C08`、`C09`。
- `P4`：RED 先增加 T12 并运行 `C04`、`C06`，预期 UI 行为失败；GREEN 最小实现后重跑 `C04`、`C05`、`C06`；REGRESSION 运行 `C07`、`C08`、`C09`。
- `REGRESSION-P5`：按顺序运行 `C07`、`C08`、`C09`、`C10`、`C11-PY/JAVA/PS`、`C04`、`C05`、`C06`，任何失败或跳过均停止验收。

## Test Cases

### T01: 冻结批准源码且保护现有工作区

- Covers: P1-AC1, P1-AC4, P3-AC1
- Level: backend integration + Git fixture
- BDD: Given 主工作区脏且批准源有效；When 创建 workflow；Then 只创建 clean detached worktree，manifest 记录提交与 `dirty=false`，原工作区不变。
- Command: C01
- Expected: 脏 release worktree 在 `SOURCE_FREEZING` 阻断，构建与 NAS 写入计数均为零；另用 Git 命令证明 8080c0d 差异已逐文件审查、批准应用源包含 713c641 或等价修复、维护仓与 IntRuoyi 根仓两个 Git root 及 maintenance/backend/frontend 三个 source role 的 HEAD/dirty 审计齐全，并分别记录构建前和打包前两次冻结校验。

### T02: 固定 app-release 与服务端参数所有权

- Covers: P1-AC2, P1-AC3, P4-AC1, P4-AC2
- Level: API contract + frontend unit
- BDD: Given 操作者进入标准发布；When 创建 workflow 或提交额外基础设施字段；Then 服务端固定 `app-release` 并拒绝额外字段，UI 只显示三个按钮和“程序包（不含数据）”。
- Command: C01, C04
- Expected: with-data 和备份/恢复入口均不进入 workflow，releaseTag 与 preset 由服务端产生；所有消费者只认 `manifest.json`，`release-manifest.json` 必须被拒绝。

### T03: 昂贵构建前 CI 顺序门禁

- Covers: P1-AC5
- Level: backend integration + command-order contract
- BDD: Given 任一后端、前端或脚本测试失败；When workflow 执行 preflight；Then Maven、前端和 Docker 构建都不启动。
- Command: C01
- Expected: 失败阶段和错误码明确，命令事件序列中无构建动作。

### T04: 原子持久化与 verifier 唯一推进

- Covers: P2-AC1, P2-AC4
- Level: backend unit + persistence integration
- BDD: Given 并发 stateVersion、写入中断或损坏 JSON；When 转换状态或重启加载；Then CAS 拒绝冲突，损坏状态阻断，只有 verifier 能推进成功态。
- Command: C02
- Expected: record、attempt、operationId、错误、retryable 和 evidence 引用原子一致；append-only event journal 在进程重启后恢复相同序列，损坏或缺口直接阻断，客户端无法伪造 SUCCESS。

### T05: 并发锁、心跳、取消、恢复与重试

- Covers: P2-AC2, P2-AC3, P2-AC6
- Level: backend concurrency + recovery integration
- BDD: Given 重复点击、租约冲突、guard 提前 return、各阶段取消、心跳超时、内容/迁移已变或写阶段中断；When 同一资源再次执行；Then 返回现有 workflow/冲突、确定终态或 `RECOVERY_REQUIRED`，只有零写入审计满足时回 READY，内容/迁移变化必须新 workflow/new tag。
- Command: C02
- Expected: 无重复执行；guard return 不得写 SUCCESS；读阶段取消可达 CANCELED，写阶段取消进入 RECOVERY_REQUIRED；FAILED/CANCELED/COMPLETED 不可变；正式失败不自动重试，后续仍要求新授权和 PROD。

### T06: preset、权限、错误可见与全表面脱敏

- Covers: P2-AC5, P4-AC5
- Level: backend security + frontend unit
- BDD: Given preset、secret 引用或权限缺失；When 启动或请求动作；Then fail fast 且 UI 显示错误，API、预览、日志、异常、复制内容和审计只含脱敏摘要。
- Command: C02, C04
- Expected: 不产生写动作，无空 catch、默认成功值或敏感值泄漏。

### T07: Maven 前环境与 LocalCacheRoot 预检

- Covers: P3-AC2
- Level: script integration
- BDD: Given NAS、Docker、空间、容器、端口、secret、锁、目标状态任一异常或 cache 根不规范；When 执行 preflight；Then 在 Maven 前阻断。
- Command: C03
- Expected: 尾部为 `publish-int-ruoyi` 的 LocalCacheRoot 被拒绝，昂贵构建和正式目录写入为零。

### T08: 迁移合同与目标只读检查

- Covers: P3-AC3, P3-AC4
- Level: script unit + isolated database integration
- BDD: Given R31-R39 fixture；When 解析迁移计划并做两次同镜像演练；Then allowlist、metadata、delimiter、标识符、幂等、显式 TCP 和自动推导 preflight 逐项阻断错误。
- Command: C03
- Expected: 非 schema 或依赖历史数据约束的迁移必须执行目标只读检查，失败时 Maven 未启动。

### T09: 双扫描、不可变摘要与 NAS 原子 READY

- Covers: P3-AC5, P3-AC6, P5-AC1
- Level: package governance + filesystem integration
- BDD: Given 有效包及 R40-R42 篡改 fixture；When 构建后扫描、上传、全哈希并在部署前复扫；Then 仅有效自包含包经同卷原子改名成为 READY。
- Command: C03
- Expected: 两次扫描独立留证，逐项覆盖 MySQL dump、MinIO 快照/目录、DCC inventory、runtime data、`.env`、秘密、`release-manifest.json`、绝对路径、目录穿越、外链和未登记文件；自包含 verifier 与构建/迁移证据可脱离源码 worktree 运行；哈希漂移或占用目录均阻断部署；`C11-PY/JAVA/PS` 输出固定双摘要。

### T10: 测试部署事务与完整成功证明

- Covers: P3-AC7, P3-AC8
- Level: isolated deployment integration
- BDD: Given READY app-release；When 使用 `.env.next` 切换并执行测试发布；Then 成功证据同时绑定 operation、manifest/digest、环境 tag、实际镜像、容器、后端健康、前端响应、release-info、锁和迁移状态。
- Command: C03
- Expected: 任一条件缺失不判绿；切换失败恢复旧环境与实际镜像，状态不明进入 `RECOVERY_REQUIRED`。

### T11: 同摘要正式晋级守卫与零写入

- Covers: P3-AC9, P3-AC10, P5-AC1, P5-AC5
- Level: backend integration + real-browser negative E2E
- BDD: Given TESTED workflow；When preview 或 execute 的授权在 workflowId、releaseTag、packageDigest、manifestDigest、prod 环境、presetId/version、approvedScope、issuedAt/validUntil、nonce、revokedAt、consumedAt 任一字段不匹配，或缺权限、开关、PROD、无锁条件；Then preview 只读且 execute 在任何正式写入前拒绝，并发 CAS 只允许一个请求消费授权。
- Command: C02, C03, C06
- Expected: app-release attestation 可识别但不触发重建；授权逐字段绑定 workflowId、releaseTag、packageDigest、manifestDigest、targetEnvironment、presetId/version、approvedScope、approver、issuedAt/validUntil、nonce、revokedAt/consumedAt；两个并发请求只能有一个 CAS 消费成功，逐一拒绝错环境、跨 workflow/tag/digest/preset/scope、扩大 scope、非法 issuedAt、撤销、过期和 nonce 重放。失败 tag 退休；正式服写入证据恒为零。

### T12: 工作台详情、eligibility、刷新与可访问性

- Covers: P4-AC3, P4-AC4, P4-AC6
- Level: e2e
- BDD: Given 本机真实控制台载入持久化 workflow；When 桌面/窄屏刷新、键盘操作和重复点击；Then 状态、阶段、心跳、tag、digest、失败、证据、实际版本和 retry policy 一致且无重叠。
- Command: C04, C05, C06
- Expected: 服务端 eligibility 与禁用原因可见；状态不只靠颜色；按钮有可访问名称；重复点击不重复启动；正式确认显示目标、双摘要、测试证明、授权绑定和 `PROD`。

### T13: R31-R44 自动防复发矩阵

- Covers: P5-AC1
- Level: backend + script regression
- BDD: Given 每个历史失败的最小 fixture；When 运行对应负例或恢复测试；Then 在指定阶段失败或恢复，并证明 Maven、Docker、NAS 正式目录和服务器写入未开始。
- Command: C01, C02, C03
- Expected: R31-R44 全部一一留证，每项记录独立 fixture、命名命令、预期 `errorCode`、`failedStage`、状态序列和 Maven/Docker/NAS/SSH/服务器写入副作用计数；无 skip、fallback、guard return 假成功或复用失败 tag。

### T14: 同制品全链、独立验收与运行手册

- Covers: P5-AC2, P5-AC3, P5-AC4
- Level: isolated full-chain integration + independent real-browser acceptance
- BDD: Given 有效 app-release fixture 和主程序真实控制台；When 完成 build-release、NAS READY、publish-test、工作流详情 test-attestation、TESTED、promote-prod 隔离链并执行全回归；Then 全程 workflow/tag/packageDigest/manifestDigest 不变、授权只消费一次且无重建，报告和运行手册可独立复核且不含敏感值。
- Command: C07, C08, C09, C04, C05, C06
- Expected: blind-first-pass tester 先给初判；浏览器证据位于任务目录外；运行手册字段、提交范围、融合后主线程复验、worktree 注册/物理目录/进程清理均有命令证据；测试服授权缺失记 blocker，正式服始终零写入。

### T15: 三语言摘要向量与非法路径拒绝

- Covers: P1-AC5, P3-AC5, P5-AC1
- Level: unit
- BDD: Given 完全相同的两个 artifact 固定向量，以及反斜杠路径和仅大小写不同的冲突路径 / When Java、Python、PowerShell 分别计算双摘要并验证路径 / Then 三者输出四个固定 SHA-256 值完全一致，非法路径在 READY 前被拒绝。
- Command: C11-PY, C11-JAVA, C11-PS；另运行 `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_app_release_package_governance.py" -k "test_backslash_path_is_rejected or test_case_fold_collision_is_rejected" -q`。
- Expected: packageDigest=`b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273`，manifestDigest=`bb44ed6ea9550e067c1a2af3a105a0989503b046646f26bd1bac19455bee2800`；非法路径返回 `PACKAGE_PATH_INVALID`，NAS READY/部署计数为零。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T01 | 来源冻结 | clean/frozen worktree | integration | P1-AC1, P1-AC4, P3-AC1 | `test-report.md#T01` |
| T02 | 范围/API/UI | app-release 唯一合同 | contract/unit | P1-AC2, P1-AC3, P4-AC1, P4-AC2 | `test-report.md#T02` |
| T03 | 顺序门禁 | CI 失败前移 | integration | P1-AC5 | `test-report.md#T03` |
| T04 | 持久化 | CAS、恢复、verifier | unit/integration | P2-AC1, P2-AC4 | `test-report.md#T04` |
| T05 | 可靠执行 | 锁、心跳、取消、重试 | concurrency | P2-AC2, P2-AC3, P2-AC6 | `test-report.md#T05` |
| T06 | 安全边界 | preset、权限、脱敏 | security/unit | P2-AC5, P4-AC5 | `test-report.md#T06` |
| T07 | 环境 preflight | Maven 前阻断 | integration | P3-AC2 | `test-report.md#T07` |
| T08 | 迁移治理 | R31-R39 | unit/integration | P3-AC3, P3-AC4 | `test-report.md#T08` |
| T09 | 制品/NAS | 双扫描和原子 READY | integration | P3-AC5, P3-AC6, P5-AC1 | `test-report.md#T09` |
| T10 | 测试部署 | 环境事务和成功证明 | integration | P3-AC7, P3-AC8 | `test-report.md#T10` |
| T11 | 正式守卫 | 同 digest、授权、零写入 | integration/e2e | P3-AC9, P3-AC10, P5-AC1, P5-AC5 | `test-report.md#T11` |
| T12 | 工作台 | 状态、刷新、可访问性 | unit/e2e | P4-AC3, P4-AC4, P4-AC6 | `output/playwright/one-button-app-release-20260911/` |
| T13 | 防复发 | R31-R44 自动矩阵 | regression | P5-AC1 | `test-report.md#T13` |
| T14 | 最终验收 | 同制品链和运行手册 | integration/e2e/manual | P5-AC2, P5-AC3, P5-AC4 | `test-report.md#T14` |
| T15 | 摘要/路径 | 三语言固定向量与非法路径 | unit | P1-AC5, P3-AC5, P5-AC1 | `test-report.md#T15` |

### R31-R44 唯一命令与失败契约

R31-R44 不得只由聚合 T13 代替；每项都必须有独立命名测试、预期错误码/阶段，以及下游副作用为零的断言（适用时包括 Maven、Docker、NAS 正式目录、SSH 和服务器写入）：

| Regression | Executable command / selector | Expected result | Required side-effect assertion |
| --- | --- | --- | --- |
| R31 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_target_preflight_auto_derivation_missing_blocks_before_maven -q` | `TARGET_PREFLIGHT_MISSING` / `PREFLIGHTING` | Maven=0, Docker=0, NAS-final=0, SSH=0 |
| R32 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_target_preflight_directory_excluded_from_migration_scan -q` | PASS; remains `PREFLIGHTING`, no classification error | target-preflight files absent from migration IDs |
| R33 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_target_preflight_reference_or_digest_missing_blocks -q` | `TARGET_PREFLIGHT_INVALID` / `PREFLIGHTING` | Maven=0, Docker=0, NAS-final=0, SSH=0 |
| R34 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_migration_idempotency_duplicate_drop_check_blocks -q` | `MIGRATION_NOT_IDEMPOTENT` / `PREFLIGHTING` | second rehearsal fails before Maven |
| R35 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_schema_ledger_drift_missing_column_blocks -q` | `SCHEMA_LEDGER_DRIFT` / `PREFLIGHTING` | target remains read-only; Maven=0 |
| R36 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_rehearsal_requires_explicit_tcp -q` | `MYSQL_CONNECTION_CONTRACT_INVALID` / `PREFLIGHTING` | no implicit socket call; temporary resources cleaned |
| R37 | `mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseSourceFreezeTest#dirtyReleaseWorktreeBlocksSourceFreezing' test` | `SOURCE_DIRTY` / `SOURCE_FREEZING` | original workspace unchanged; build/NAS=0 |
| R38 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_schema_data_dependency_requires_target_preflight -q` | `TARGET_PREFLIGHT_REQUIRED` / `PREFLIGHTING` | target read-only; Maven=0 |
| R39 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_procedure_without_delimiter_blocks_parser -q` | `SQL_DELIMITER_INVALID` / `PREFLIGHTING` | Maven=0, Docker=0, NAS-final=0, SSH=0 |
| R40 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_app_release_package_governance.py" -k test_nas_ready_requires_atomic_upload_and_full_hash -q` | `NAS_READY_INVALID` / `PUBLISHING_ARTIFACT` | final READY path absent; deploy/SSH=0 |
| R41 | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_workflow_preflight.py" -k test_local_cache_root_parent_contract -q` | `LOCAL_CACHE_ROOT_INVALID` / `PREFLIGHTING` | Maven=0, Docker=0, NAS-final=0, SSH=0 |
| R42a | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_app_release_package_governance.py" -k test_stale_local_cache_is_purged_before_integrity -q` | PASS; local staging equals immutable source | stale `.env` absent after purge; target write=0 |
| R42b | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_app_release_package_governance.py" -k test_package_source_env_is_forbidden -q` | `PACKAGE_FORBIDDEN_ARTIFACT` / `VERIFYING_PACKAGE` | READY/deploy/SSH=0 |
| R43a | `mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseWorkflowSecurityTest#invalidPresetBlocksBeforeDispatch' test` | `PRESET_INVALID` / `PREFLIGHTING` | operationId absent; SSH=0 |
| R43b | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_migration_preflight_matrix.py" -k test_data_constraint_conflict_requires_target_preflight -q` | `TARGET_PREFLIGHT_FAILED` / `PREFLIGHTING` | target read-only; Maven/build=0 |
| R43c | `python -X utf8 -m pytest "$releaseButtonMaintenanceRoot\scripts\tests\test_release_deployment_transaction.py" -k test_env_transaction_restores_actual_image_after_failure -q` | `DEPLOYMENT_FAILED` / `VERIFYING_TEST`; final state `FAILED` | old `.env`/actual tags restored; health UP; tag retired |
| R44 | `mvn -f "$releaseButtonAppRoot\IntRuoyiBackend\pom.xml" -pl yudao-module-infra '-Dtest=ReleaseWorkflowRecoveryTest#persistedReadyWorkflowRemainsReadyAfterRestart' test` | PASS; persisted READY remains `READY` awaiting test publish | publish/deploy invocation count=0; never auto-TESTED |

### 状态转换与恢复断言

- 每个状态转换测试必须比较完整序列（当前状态、事件、守卫、下一状态、锁、可观察副作用），不能只断言最终字符串。
- `FAILED`、`CANCELED`、`COMPLETED` 为不可变终态；主动作重试必须新 workflow/new tag。`READY` 或 `TESTED` 的拒绝只可在未创建 operation、未取得环境锁、未消费授权且目标零写入时保留原状态。
- `RECOVERY_REQUIRED` 只有在只读审计证明零写入、无有效 operation 效果、无遗留锁且双摘要未变时才能回 `READY`；其他情况必须 `FAILED`。取消在写阶段不能直接伪造 `CANCELED`。

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 使用本机真实运行控制台和真实持久化 API，不拦截网络、不伪造成功响应。
- Evidence rule: 首轮结论必须引用命令退出状态、断言结果及任务目录外截图/trace。
- Escalation rule: tester 写出初始 verdict 前不得读取 withheld artifacts；之后仅用于差异分析。

## Pass / Fail Criteria

- Pass when: 32 个 acceptance ID 均有通过证据，R31-R44 全覆盖，所有必需命令退出码为 0 且无 skip。
- Pass when: app-release 双扫描、NAS READY、状态机/锁/恢复、同 digest 链和最终运行态组合断言全部通过。
- Pass when: 本机真实浏览器桌面、窄屏、错误态、刷新恢复和正式确认均有任务目录外证据。
- Pass when: 未获授权时没有测试服写入，正式服在所有情况下均无真实写入。
- Fail when: 任一门禁后仍发生下游副作用，或仅凭退出码、HTTP 200、旧容器存活判定成功。
- Fail when: 任一失败被吞掉、降级、mock 成功、静默跳过、guard return 假成功或缺少错误码/失败阶段。
- Fail when: package digest 漂移、晋级发生重建、READY 包被修改、敏感值泄漏或证据不完整。
- Blocked when: worktree、工具、fixture、preset、Playwright 或明确授权缺失；blocker 不得计为通过。

## Regression Scope

| Regression | Required assertion |
| --- | --- |
| R31 | 自动推导的 target preflight 缺失时在 Maven 前阻断 |
| R32 | target-preflight 不被误识别为 release migration |
| R33 | preflight 引用或摘要缺失时阻断 |
| R34 | 重复 DROP CHECK、非法标识符或二次演练非幂等时阻断 |
| R35 | ledger 与真实 schema 不一致时阻断 |
| R36 | 演练必须显式 TCP host/port，隐式 socket 被拒绝 |
| R37 | release worktree 脏时在 `SOURCE_FREEZING` 阻断 |
| R38 | schema 类型夹带历史数据依赖时强制目标只读检查 |
| R39 | 多语句 procedure 缺 delimiter 时解析失败 |
| R40 | 本地有包但 NAS 无原子 READY 时禁止部署 |
| R41 | 异常 LocalCacheRoot 被拒绝 |
| R42 | 旧环境文件由唯一 staging/严格 purge 和两次扫描检出 |
| R43 | preset 固化、历史数据 preflight、环境漂移恢复分别通过 |
| R44 | 中断后从持久化 READY 恢复等待授权，历史包不自动变为 READY/TESTED |

相邻回归还包括旧 `/actions` UI 入口隔离、备份/恢复流程不被 workflow 接管、现有 release-info/镜像传输/前端 SQL gate 合同、事件审计顺序与敏感值扫描。

## Reporting Notes

- 独立 tester 将最终结果写入 `test-report.md`，按 T01-T15 记录 PASS、FAIL 或 BLOCKED。
- `execution-log.md` 必须逐项记录 `BDD:`、`RED:`、`GREEN:`、`REGRESSION:` 的精确命令、退出状态、预期原因和证据引用。
- 浏览器证据只写入 `output/playwright/one-button-app-release-20260911/`，报告引用相对路径与文件摘要。
- 报告分别记录构建后扫描和部署前扫描，不得合并成一次扫描证明。
- 报告记录 tag/digest 流转、状态转换、锁、重试、恢复及最终运行态组合断言。
- 测试服授权缺失记录为真实发布 blocker；正式服报告只记录 preview/守卫与零写入证明。
- 所有请求、响应、命令摘要、异常、日志和截图在入证前完成脱敏。
- 最终 recommendation 仅可为 PASS、FAIL 或 BLOCKED，不得以部分通过替代验收结论。
