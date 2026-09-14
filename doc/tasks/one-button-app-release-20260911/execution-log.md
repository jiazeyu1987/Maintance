# Execution Log

- Task ID: `one-button-app-release-20260911`
- Created: `2026-09-11T09:20:03+08:00`
- Current status: `blocked`
- Scope of this turn: planning artifacts only

## User Request

用户同意将发布过程程序化并先生成正式文档；标准安装包必须为 `without-data`，在现有技术契约中固定为 `PublishScope=app-release`。

## Environment

- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Platform: Windows / PowerShell 5.1
- Planning baseline: `int_main@eaaa47ac320dd197dba646d6870fed0cb7d2534c`
- Verified release-line references: maintenance `8080c0d3c7076d2305d945dea26bf1a22ceaf026`; application `713c64112d7b626a2ba71788fd36cc32d686addc`
- Current main workspace is dirty; this planning turn preserved all unrelated changes.

## BDD Scenarios

BDD: 生成不带业务数据的程序安装包 -> Given 操作者选择已批准提交 / When 点击“生成程序安装包” / Then 服务端固定 `app-release`，完成全部前置门禁并只生成白名单内程序制品，包内不存在 MySQL dump、MinIO 快照、DCC inventory、runtime data 或秘密。

BDD: 同一不可变包发布测试服 -> Given 程序包已在 NAS 原子入库并处于 READY / When 点击“发布测试服” / Then 只消费该 releaseTag/package digest，成功必须同时满足 operation、manifest、远端 tag、实际镜像、容器、后端 UP、前端 200、release-info、lock 和 migration 终态门禁。

BDD: 受控晋级正式服 -> Given 测试服已验证且 attestation 绑定同一 package digest / When 有当次授权并输入 PROD 后点击“晋级正式服” / Then 系统不重新构建，只发布同一包；任一权限、授权、摘要或运行态条件缺失时在正式写入前阻断。

BDD: 历史发布错误前移 -> Given R31-R44 任一已知错误 fixture / When workflow 执行对应阶段 / Then 在昂贵构建或真实服务器写入前返回明确 errorCode、failedStage 与证据，不得假绿或自动 fallback。

## Experience Preflight

GREEN: experience-preflight -> PASS，已按 `docs/experience-index.md` 命中并读取不可变安装包、构建前 target-state、schema-only 迁移演练、测试服发布、PowerShell、发布检查清单、备份恢复和 worktree 门禁；本轮没有执行服务器写入、发布、大文件上传、数据库或 MinIO 操作。

## Discovery Evidence

- 现有运行控制台具备 `/actions` 预览/执行、operation/log、release-package 和 release-status API，可作为底层执行器。
- 当前缺少跨操作持久化 workflow、阶段级状态、环境租约锁、可靠心跳/超时、取消与重启恢复。
- `8080c0d` 已验证 `app-release` 与 NAS 下载 `/PURGE`，但不在当前 `int_main` 祖先链；实施必须先在独立 worktree 审查融合。
- 本规划启动时 `R44` 只有 app-release 构建和 NAS 上传证据；规划期间另一发布线程补充了测试服 `publish-test/deploy-release`、运行态和页面 PASS 证据。该结果不属于本规划任务的动作，且仍未执行 `mark-tested` 或任何 promotion。
- 标准 UI 必须移除 with-data 和基础设施自由参数；数据备份/恢复继续使用独立流程。

## Commands

- 只读检查适用规则、经验索引、发布/备份/恢复、worktree 与 PowerShell 规范。
- 只读审查当前与 `8080c0d` 的运行控制台、发布脚本、包治理、迁移 preflight 和测试覆盖。
- 初始化 `doc/tasks/one-button-app-release-20260911` 规格任务目录。
- 运行规格文档结构校验；未运行 Maven、pnpm、Docker、NAS、SSH、数据库迁移或发布命令。

## Pipeline

- Planned stages: source freeze -> preflight -> CI tests -> build -> package verification -> NAS READY -> publish test -> runtime verification -> tested attestation -> explicit prod authorization -> promote same digest -> runtime verification.
- Package policy: `app-release` only for the standard release workflow.
- Data policy: no MySQL full dump, MinIO snapshot/sync, DCC object inventory, Redis/runtime data, uploaded files or secret-bearing `.env` in the immutable package.
- Required SQL remains because it is a versioned application-upgrade contract, not a full business-data snapshot.

## Secrets

- No secret value is recorded in task artifacts.
- Preset and secret requirements are documented only as references, presence checks and ownership boundaries.
- Raw configuration output and secret-bearing command output are excluded from committed evidence.

## Verification

GREEN: spec-artifact-validation -> PASS，`validate_artifacts.py` 返回 `status=ok`、0 errors、0 warnings；PRD 有 5 个稳定阶段和 32 个 acceptance IDs，测试计划有 15 个 cases 并覆盖全部 32 个 IDs。

REVIEW: independent-verification-round-1 -> FAIL，审查指出产品 E2E 入口、PowerShell 逐条失败检查、状态转换、授权绑定、摘要算法和 R31-R44 可执行映射需要收紧。

GREEN: planner-revision-round-2 -> PASS，PRD 已改为主程序 `localhost:8081` 真实用户路径，补齐状态转换表、一次性授权绑定、双摘要字节算法和 P1 前置阻塞；测试计划补齐逐条 PowerShell 退出码、测试租户 UI-only 边界、R31-R44 唯一命令/错误码/阶段/副作用契约，以及正式确认字段和收口命令证据。

GREEN: independent-verification-round-2 -> PASS，独立审查确认 task-state/PRD 32 个 AC 已同步，仓库职责、固定摘要向量、授权 CAS、R31-R44 可执行映射和唯一 manifest 契约一致；规划门禁通过不代表功能已实现。

REVIEW: independent-verification-round-3 -> FAIL，复审发现仍有“两个 Git root 与三个 source role”术语残留不一致，且 P5-AC1 对摘要向量、非法路径和授权重放的测试覆盖映射不足。

GREEN: independent-verification-final -> PASS，统一为维护仓与 IntRuoyi 根仓两个 Git worktree、maintenance/backend/frontend 三个 source role；新增 T15 固定摘要/非法路径用例，并将 P5-AC1 映射到 T09/T11/T13/T15。最终独立复审返回 PASS。

BLOCKER: authoritative-playwright-runtime -> 项目规定路径 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 当前存在，但缺少 `package.json`、`node_modules\playwright` 与 `.bin\playwright.cmd`；P4/P5 真实浏览器验收不得启动，禁止切换版本或临时下载兜底。已安装 Chromium 与系统 Chrome 只说明浏览器二进制存在，不能替代缺失的规定 Playwright 运行时。

GREEN: project-experience-consolidation -> PASS，经验已合并到现有 `docs/release-build-preflight-lessons.md`，并在 `docs/experience-index.md` 增加“一键发布/without-data/app-release/ReleaseWorkflow/R31-R44”路由；未新建长期经验文件。

GREEN: final-document-verification -> PASS，`validate_artifacts.py` 为 0 errors/0 warnings，CI/CD evidence validator 与 self-test PASS，PRD/测试计划/task-state 均为 32 个 acceptance IDs，测试计划 15 个 cases，最终独立复审 PASS；本任务文本 UTF-8 严格解码、final newline、trailing whitespace 与 scoped diff checks 均通过。

GREEN: planner-review -> PASS，主线程按 review checklist 核对 scope、non-goals、前置条件、稳定 ID、测试覆盖、fail-fast、真实浏览器与授权边界；最终集成 Playwright 入口固定为主程序 `http://localhost:8081/infra/monitors/runtime-control`，维护仓 `48181` 仅用于契约/预览。

## Rollback

本轮只有文档变更且没有运行态写入。若规划需要撤销，只回退本任务目录和本次追加的脱敏请求记录；不得影响 R44 包、其他任务文件、当前脏工作树或任何服务器。

## Blockers

- 规划文档已获主线程批准；机器状态保持 `blocked`，因为 P1 的独立 worktree、8080c0d/713c641 差异审查与当前脏工作区归属尚未完成。
- P1 开始前必须创建独立实施 worktree，并解决 `8080c0d` 验证线与当前 `int_main` 分叉、当前 `frontend/` 未提交删除的归属；在此之前不得直接修改主工作树。
- 测试服真实写入需要用户当次明确授权；正式服真实写入不在当前授权范围。
- P4/P5 需要恢复项目规定的 Playwright 1.60.0 运行时；当前权威路径缺少依赖和可执行文件。

## Phase Entries

### Planning Gate

- Changed paths: `prd.md`, `test-plan.md`, `execution-log.md`, `task-state.json`（由主线程在文档评审通过后同步）。
- Acceptance coverage: P1-AC1 through P5-AC5 planned; no implementation acceptance item is marked completed.
- Remaining work: execute P1-P5 one phase at a time with executor and independent tester gates.

## Outstanding Blockers

- P1 implementation prerequisites and environment authorization gates remain as listed above.

## Phase P1 Executor Evidence

### BDD And RED

BDD: 标准程序包固定无数据 -> Given 标准发布 workflow / When 解析构建意图 / Then scope 只能是 `app-release`，数据库/MinIO/DCC/runtime data 与秘密均不得进入安装包。

BDD: 两次冻结批准源码 -> Given 维护仓与 IntRuoyi 根仓各有批准 commit / When 进入昂贵构建前和写 manifest 前 / Then 两个 Git root 的 HEAD/dirty 与 maintenance/backend/frontend 三个 source role 全部一致，否则 fail fast。

BDD: 测试失败前移 -> Given 后端、前端或脚本合同任一失败 / When 标准构建准备执行 / Then Maven package、前端 build 和 Docker build 均不启动。

BDD: 三语言双摘要一致 -> Given固定 artifact/manifest 原始 bytes / When Python、Java、PowerShell 计算摘要 / Then 四个固定 SHA-256 完全一致，并拒绝反斜杠及大小写折叠冲突路径。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_digest_vectors.py` -> FAIL，旧脚本仍为 code-only/with-data 双范围、双 manifest、无两次冻结/显式测试顺序，且 Python 摘要模块不存在。

RED: `python -X utf8 -m pytest -q scripts/tests/test_app_release_package_governance.py --basetemp <task-owned>` -> FAIL，11 个用例证明旧 verifier 仍只读取 `release-manifest.json`，且没有 app-release 禁止项/路径合同。

RED: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1` -> FAIL，`Get-ReleasePackageDigest` 尚不存在。

### Verified-Line Review

- 维护 `8080c0d` 不是当前任务分支祖先；其 `/PURGE` 修复位于已分叉的发布线，当前主线已退回 `Copy-Item + 删除本地目录`，需在当前基线重建可续传 `/PURGE` 下载并保留完整性校验顺序。
- 应用 `713c641` 不是当前任务分支祖先；当前 SQL 与 H2 schema 确实恢复为“所有历史账号唯一”，需只移植活跃账号生成列/唯一索引及对应测试，保留当前主线其它新增内容。
- 不盲目 cherry-pick 两条验证线，不覆盖原主工作区或当前主线后续变更。

### GREEN And Regression

- GREEN: C01（补 `-am -Dsurefire.failIfNoSpecifiedTests=false`）-> PASS，8 tests，0 failures/errors/skips；覆盖服务端 identity/preset、客户端字段拒绝、两 Git root/三 role、两次冻结、测试顺序和 Java 摘要。
- GREEN: C04 P1 静态合同 -> PASS，workflow create intent 仅含 `reason/sourceSelectionId`，不含 releaseTag/scope/host/NAS/MinIO/repo roots/LocalCacheRoot。
- GREEN: C11-PY -> PASS，3 tests；C11-JAVA -> PASS，2 tests；C11-PS -> PASS。三语言共同得到 packageDigest `b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273` 和 manifestDigest `bb44ed6ea9550e067c1a2af3a105a0989503b046646f26bd1bac19455bee2800`，并拒绝反斜杠/大小写冲突。
- GREEN: maintenance focused P1 + legacy governance -> PASS，80 tests；唯一 `manifest.json`、app-release 禁止项、摘要、attestation 和 `/PURGE` 回归均通过。
- GREEN: C08 -> PASS，211 tests；C09 -> PASS，6 tests；C10 -> PASS，26 tests；PowerShell AST -> PASS。
- GREEN: active username 验证线聚焦合同 -> PASS，2 tests、9 deselected；目标移植 `713c641` 的活跃账号唯一约束，保留当前主线后续测试/schema 内容。
- GREEN: branch-runtime-port-guard -> PASS，`codex/one-button-app-release-20260911/int_main` 使用 slot 41、8256/48256；本阶段未启动服务。
- REGRESSION: C07 全量 infra reactor -> FAIL，首个非 P1 失败为既有 `CodegenEngineVue2Test` / `CodegenEngineVue3Test` 模板快照差异，共 12 failures；P1 定向 Java 套件已全绿，未扩大修复。
- BLOCKER: `corepack pnpm --dir IntRuoyiFronted ts:check` -> app worktree 缺 `node_modules/cross-env`；该命令属于 P4/C05 前置，本阶段未临时安装依赖或改用其它工具假绿。

### Acceptance Coverage And Commits

- P1-AC1: 两个独立 worktree 已建立；维护 `/PURGE` 与 app active username 能力按当前主线逐文件融合，未整链 cherry-pick，原主工作区未修改。
- P1-AC2: 标准构建固定 `app-release`；数据备份/恢复不进入 workflow；构建、校验、NAS/deploy precheck/restore planner 消费唯一 `manifest.json`，第二 manifest 作为禁止项拒绝。
- P1-AC3: Java/TypeScript create intent 只接受 reason/sourceSelectionId；workflowId/releaseTag/preset/scope 由服务端合同生成。
- P1-AC4: manifest/source freeze 固定 maintenance/application 两个 root 与 maintenance/backend/frontend 三个 role；before-build/before-package 任一 HEAD/dirty 漂移 fail fast。
- P1-AC5: 后端、前端、脚本测试先于 Maven/frontend/Docker build；Python/Java/PowerShell 固定双摘要一致。
- Maintenance implementation commit: `045c8bca266201198b3bc9e2648c85c43cfe9880`。
- IntRuoyi app implementation commit: `e9fed5ea86dfd8b8b63c779c37d523bc5d92df55`。
- Worktrees remain for the main-thread independent P1 verifier; no merge to `int_main`, push, cleanup or worktree removal was performed by this executor.
- Changed maintenance paths: `ops/deploy/publish-int-ruoyi.ps1`, release manifest/governance/preflight/restore modules, digest implementation, P1/legacy tests and standalone parity fixture.
- Changed app paths: infra releaseworkflow contract classes/tests, workflow create VO, runtimeControl TypeScript intent, active username SQL/H2 fixture/test, and app task records.

### Authorization Boundary Result

- NOT_RUN: P2-P5、Maven package、frontend build、Docker build、服务启动、真实 E2E、NAS、数据库、MinIO、SSH、测试服、正式服、审查服、mark-tested 和 promotion；均未获本阶段授权或不属于 P1。
- REMAINING_RISK: P1 只建立合同与底层门禁；完整状态机/持久化/锁在 P2，部署事务在 P3，三按钮 UI 与真实浏览器验收在 P4/P5。

## P1 Review Correction

BDD: 二次冻结拒绝来源身份漂移 -> Given before-build 已冻结两个 root 和三个 role / When before-package 使用同 commit/clean 但 root 路径或 role root/path/commit 改变 / Then 分别返回稳定 drift errorCode 并禁止写 manifest。

BDD: manifest 来源证据不可篡改 -> Given manifest 声明严格 sourceRoots/sourceRoles / When normalizedRoot、approvedCommit、commit、dirty 或 role 映射被篡改 / Then verifier 在 READY 前拒绝。

BDD: 产品候选只读唯一 manifest -> Given NAS 程序包只有 `manifest.json` / When 主程序扫描发布包和回滚候选 / Then 从 packageId/createdAt/packageDigest/source evidence 构建候选；只有旧 manifest 的包被阻断且不 fallback。

BDD: 三语言路径冲突键一致 -> Given ASCII 大小写冲突与仅非 ASCII 大小写不同路径 / When Java、Python、PowerShell 计算 collision key / Then 只折叠 ASCII A-Z，非 ASCII UTF-8 bytes 保持不变，三语言摘要一致。

RED: P1 Java review suite -> FAIL；source freeze 3 tests 因缺 `verifyAgain` 合同失败，非 ASCII digest 向量报 path collision，产品 release package 列表为空，rollback candidate 7 failures/1 error 证明仍读取旧 manifest/packageDirectoryName。

RED: maintenance review suite -> FAIL，1 个 freeze 静态合同、1 个非 ASCII digest、1 个 schema item 合同和 6 个 manifest source tamper 用例失败。

RED: PowerShell digest vector -> FAIL，`Z/Ä.txt` 与 `z/ä.txt` 被 `OrdinalIgnoreCase` 错误折叠，实际摘要不等于 ASCII-only 固定向量。

## Phase P1 - 基线与契约收敛

USER_AUTHORIZATION: 用户要求“根据文档进行开发”；本轮授权覆盖本机 P1 实现、测试和任务分支提交，不覆盖真实 E2E、NAS、测试服、正式服、审查服、数据库或 MinIO 写入。

BDD: 验证发布线无损融合 -> Given 当前维护仓与 IntRuoyi 主工作区均含并发脏改动 / When 从各自已提交 `int_main` 创建任务 worktree 并融合 R44 验证线 / Then 原主工作区不变，任务分支可追溯 `8080c0d`、`713c641` 或等价能力，两个 Git root 与三个 source role 均明确。

BDD: 标准程序包固定无数据 -> Given 操作者通过标准 workflow 生成程序安装包 / When 构建合同解析请求 / Then scope 固定为 `app-release`，客户端不能选择 `with-data`，权威制品只接受 `manifest.json`，并拒绝数据库/MinIO/DCC/runtime data/秘密制品。

BDD: 构建前测试与来源门禁 -> Given 任一来源 dirty、摘要向量不一致或后端/前端/脚本测试失败 / When workflow 准备进入 Maven/frontend/Docker 构建 / Then 在昂贵构建前返回明确失败，不产生 NAS 或服务器副作用。

GREEN: experience-preflight-p1 -> PASS，已读取本仓经验索引、按钮化 app-release 门禁、发布/备份恢复规则、PowerShell 规则、IntRuoyi AGENTS、worktree-memory、worktree-restrictions、branch-runtime-ports、task-closeout、后端/前端开发规则与统一前端样式。两个目标 worktree 路径均在允许根内且当前不存在；P1 禁止服务启动、远程访问和 E2E。

ACTION: p1-isolated-worktrees -> 计划从维护仓 `int_main@08823268e9efe7571a06c261a7b919c890c45dad` 创建 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m`，从应用仓 `int_main@860496e330a8b47bcb421b8b65ece03c06df33d8` 创建 `D:\IntRuoyiWorktree\r260911-release-button\a`；两仓任务分支统一为 `codex/one-button-app-release-20260911`。原主工作区只读保留。

DEFERRED: P4/P5 规定 Playwright 1.60.0 运行时缺失；真实测试服/正式服授权缺失。这些不阻塞不启动服务、不运行 E2E、不访问远程环境的 P1。

GREEN: P1-review-correction -> PASS，产品 release package 与 rollback consumer 已统一读取 `manifest.json`/`packageId`/双摘要/来源证据；source freeze 补齐 root/role 身份漂移检查；PowerShell 5.1 非 ASCII digest 向量改为 codepoint 构造并通过。维护仓聚焦回归 37 tests PASS，PowerShell digest PASS；app manifest/source/digest/consumer 与既有 runtimecontrol 相关回归 91 tests PASS。

## Phase P2 - ReleaseWorkflow 编排内核

BDD: 持久化状态与恢复 -> Given workflow 在主程序运行时创建并经历阶段转换 / When 进程重启、CAS 版本冲突、JSON 损坏或写阶段心跳超时 / Then 状态和 event journal 可恢复，冲突/损坏/不确定写入进入明确阻断，不自动续跑。

BDD: 同环境互斥租约与重复点击 -> Given build/test/prod 争用同一环境或相同受控来源被重复提交 / When 第二次点击或另一个进程尝试获取租约 / Then 返回现有活动 workflow 或租约冲突，不启动重复 operation。

BDD: 客户端不能伪造成功 -> Given 客户端提交任意状态、scope、preset 或疑似秘密 / When 服务端创建或推进 workflow / Then scope/preset 由服务端固定，秘密输入在持久化前拒绝，只有 verifier 能推进状态。

RED: `mvn -f IntRuoyiBackend\\pom.xml -pl yudao-module-infra "-Dtest=ReleaseWorkflowStoreTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowSecurityTest" test` -> FAIL，预期缺少 ReleaseWorkflow 持久化、租约、恢复和 verifier 实现。

GREEN: P2 focused Maven -> PASS，11 tests，0 failures；覆盖单文件原子 workflow+event journal、stateVersion CAS、同环境跨进程文件租约、重复提交返回现有 workflow、重启后 READY 保持、写阶段超时/取消进入 RECOVERY_REQUIRED、损坏状态阻断、非法 preset/秘密输入拒绝和客户端 verifier 拒绝。

REGRESSION: P1+P2+runtimecontrol targeted Maven -> PASS，102 tests，0 failures；命令为 `mvn -f IntRuoyiBackend\\pom.xml -pl yudao-module-infra "-Dtest=ReleaseWorkflowContractTest,ReleaseSourceFreezeTest,ReleaseWorkflowGateOrderTest,ReleaseDigestVectorTest,RuntimeControlServiceImplTest,RuntimeRollbackCandidateServiceImplTest,ReleaseWorkflowStoreTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowSecurityTest" test`。

GREEN: P2 API surface -> PASS，主程序 `/infra/runtime-control/release-workflows` 提供创建、列表、详情与取消接口；创建请求只接受 `reason/sourceSelectionId`，响应仅包含 workflow 业务状态、受控来源引用和证据引用。

## Phase P3 - 自包含制品与部署事务

BDD: 迁移门禁前移 -> Given schema/data/menu migration 计划可能含历史数据约束、非幂等 DROP、schema ledger 漂移、隐式 MySQL socket 或 procedure 缺 delimiter / When 进入 Maven 前 preflight / Then 返回明确 errorCode/failedStage，Maven、Docker、NAS 和 SSH 均为零副作用。

BDD: 测试部署事务可恢复 -> Given `.env` 与 actual image tag 已处于旧版本 / When 新版本验证失败 / Then `.env` 与实际镜像记录一起恢复，`.env.next` 被清理，失败 tag 退休且不假绿。

RED: C03 planned selector -> FAIL，`test_release_migration_preflight_matrix.py` 与 `test_release_deployment_transaction.py` 不存在，证明 R31-R39 与部署事务还没有计划要求的可执行门禁。

GREEN: `python -X utf8 -m pytest -q --basetemp .tmp-pytest-one-button-regression scripts\\tests\\test_release_migration_preflight_matrix.py scripts\\tests\\test_release_deployment_transaction.py scripts\\tests\\test_release_workflow_preflight.py scripts\\tests\\test_app_release_package_governance.py scripts\\tests\\test_release_digest_vectors.py` -> PASS，37 tests，0 failures；本地覆盖 target preflight 自动推导/引用/只读结果、schema-only 历史数据依赖、显式 TCP、幂等/ledger/delimiter 和失败恢复事务。

GREEN: P4-static-slice -> `node IntRuoyiFronted\\tests\\e2e\\runtime-control-one-button-static.spec.cjs` PASS；标准页面已有“生成程序安装包 / 发布测试服 / 晋级正式服”及“程序包（不含数据）”，旧发布动作从通用运维工具栏移除。P3 部署/晋级事务未完成前后两个按钮 fail-closed。

RED: `python -X utf8 -m pytest -q --basetemp .tmp-pytest-nas-red scripts\\tests\\test_release_package_governance.py -k test_nas_ready_requires_atomic_upload_and_full_hash` -> FAIL，上传逻辑直接写最终 NAS 目录，没有 workflow staging/全哈希后原子入库合同。

GREEN: 同一命令 -> PASS；`Copy-ReleasePackageToNas` 现在写入唯一 `.staging-<nonce>` 目录，先执行完整 `Test-ReleasePackageIntegrity`，再同卷 `Move-Item` 为最终目录，失败清理 staging 且不删除既有最终包。

REGRESSION: `python -X utf8 -m pytest -q --basetemp .tmp-pytest-p3-regression2 scripts\\tests\\test_release_package_governance.py scripts\\tests\\test_app_release_package_governance.py scripts\\tests\\test_release_build_preflight_cache.py` -> PASS，122 tests，0 failures。

GREEN: `mvn -f IntRuoyiBackend\\pom.xml -pl yudao-module-infra "-Dtest=ReleaseWorkflowAuthorizationTest" test` -> PASS，3 tests；覆盖跨 workflow/tag/digest/环境绑定拒绝、正式写开关/PROD 要求、过期/撤销/已消费授权和一次性消费。

GREEN: P3 orchestrator -> PASS，`ReleaseWorkflowOrchestratorTest` 6 tests；按钮请求只由服务端生成 releaseTag，build -> READY -> publish-test -> TEST_DEPLOYED -> TESTED 顺序持久化，测试验收使用已绑定 publish operation evidence，发布动作重复点击不重复 dispatch，未批准 sourceSelectionId 在 operation 前阻断。

GREEN: P3 artifact binding -> PASS，workflow 持久化 packageDigest/manifestDigest 与 testOperationId/evidencePath；production authorization 只为 TESTED 且双摘要/测试证据完整的 workflow 创建，promote-prod 先做一次性授权 CAS 消费，再以同一 tag/双摘要/测试证明 dispatch，重放不产生第二次 operation。

REGRESSION: app targeted Maven -> PASS，111 tests，0 failures；包含 source/digest/manifest consumer、workflow state/lease/recovery/security/authorization/orchestrator 和既有 runtime-control service/candidate tests。

REGRESSION: maintenance release governance -> PASS，123 tests，0 failures；包含唯一 manifest、禁止数据/秘密制品、NAS staging + full hash + atomic READY、tested attestation 与 app-release 不写 recovery-set 数据。

BLOCKER: P4/C05 -> `corepack pnpm --dir IntRuoyiFronted ts:check` 仍因任务 app worktree 缺 `node_modules/cross-env` 失败；按门禁未安装依赖，P4/P5 类型检查与真实 Playwright 保持阻塞。

RED: `python -X utf8 -m pytest -q --basetemp .tmp-pytest-schema-red scripts\\tests\\test_release_schema_rehearsal.py` -> FAIL，缺少 schema-only migration rehearsal 模块，无法证明不复制业务数据也能在 Maven 前演练迁移。

GREEN: 同一用例 -> PASS，3 tests；新增 digest-pinned MySQL 镜像、`mysqldump --no-data`、显式 TCP、本次 required SQL 两轮执行、失败必清理临时容器合同，并由 `publish-int-ruoyi.ps1` 在 Maven 前调用，报告进入包内 `evidence/schema-only-migration-rehearsal.json`。

REGRESSION: C08 maintenance Python -> PASS，234 tests，0 failures；C09 Node -> PASS，6 tests；PowerShell digest vector -> PASS；PowerShell AST parse -> PASS。

REGRESSION: app P1-P3 targeted Maven -> PASS，111 tests，0 failures；frontend one-button static 与 release-package static -> PASS。

IMPLEMENTATION_COMMITS: app `ea9b065e1`（workflow 内核）和 `daffa04b6`（build/test/prod 编排、同摘要与一次性授权）；maintenance `be19a78`（无数据门禁、迁移/部署事务、NAS 原子 READY）和 `93cff60`（app-release 测试验收去除 recovery-set 数据依赖）。后续 schema-only rehearsal 与证据记录仍待本轮提交。

GREEN: production-authorization-cross-process-cas -> PASS，`ReleaseWorkflowAuthorizationTest` 4 tests；同一 grant 由两个 service instance 并发消费时，JVM 稳定锁和 OS 文件锁保证只有一次原子消费，第二次在任何正式 operation 前拒绝。App commit: `dacca914e`。

IMPLEMENTATION_COMMIT: maintenance `d190854`，将结构快照 `--no-data`、digest-pinned MySQL 临时容器、两轮迁移和包内证据正式接入 Maven 前门禁。

BLOCKER: P3-real-test-chain -> 未获得本轮测试服/NAS/SSH 写入授权，因此没有执行真实 build package、NAS READY、publish-test 或运行态组合校验；代码与本地回归通过不能替代该验收。

BLOCKER: P4-P5-authoritative-frontend-runtime -> task app worktree 缺 `node_modules/cross-env`，规定 Playwright 1.60.0 路径缺 `package.json`、`node_modules/playwright` 和 `.bin/playwright.cmd`；禁止临时下载、切换版本或用其他浏览器工具兜底。

CURRENT_RESULT: 本地实现已形成可提交发布控制面，但任务不得标记 completed；两个 worktree 保留，主工作区未修改，远程环境零写入。

USER_AUTHORIZATION: 用户在 2026-09-12 明确回复“授权”；本轮仅授权执行测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及其只读/运行态验证，不授权正式服写入、mark-tested 或 promote-prod。

GREEN: experience-preflight-remote-test-release -> PASS，已读取 `server-access.md`、`release-backup-restore.md`、`worktree-memory.md`、`powershell-memory.md`；目标固定测试服 `172.30.30.58`，安装包固定 `PublishScope=app-release`，数据库与 MinIO 全量数据同步均关闭。

GREEN: task-worktree-cleanup -> PASS，仅删除维护任务 worktree 下 `.tmp-pytest-*` 临时测试目录；未删除主工作区、源码、服务器或 NAS 内容。

GREEN: frontend-dependency-preflight -> PASS，在任务 app worktree 的 `IntRuoyiFronted` 执行 `pnpm install --frozen-lockfile --ignore-scripts`，锁文件未变；`cross-env.cmd`、`vite.cmd`、`vue-tsc` 与 Playwright 1.60.0 均存在。

RED: `corepack pnpm ts:check` -> FAIL，`runtime-control/index.vue` 缺少 `ElMessageBox` 显式导入；这是正式晋级确认对话框的 TypeScript 编译错误，必须在发布构建前修复。

GREEN: `corepack pnpm ts:check` -> PASS；补充 `ElMessageBox` 显式导入后，任务 app worktree 前端类型检查退出码为 0。

GREEN: remote-test-readonly-preflight -> PASS，SSH `root@172.30.30.58` 可达，Docker Compose v2.27.0，`/var/lib/docker` 使用率 27%，`intruoyi-mysql` healthy，backend/frontend 均 running；只读取状态，未修改测试服。

GREEN: nas-release-target-preflight -> PASS，使用受控 NAS JSON 进行临时连接，只读确认 `Backup/ReleasePackage/release-20260912-one-button-app-r1` 不存在，随后断开映射；未读取或记录密码值。

SOURCE_FREEZE_INPUT: maintenance `057f400`，application `fe548b1`；两个任务 worktree 均 clean。计划执行 `build-release`，releaseTag=`release-20260912-one-button-app-r1`，Component=`intruoyi`，PublishScope=`app-release`，显式 SkipDatabaseSync/SkipMinioSync；成功后只执行同 tag 的 test `deploy-release`。

RED: build-release-r1-migration-metadata -> FAIL，`20260911_dcc_publish_direct_policy.sql` 缺少 `release-migration` 元数据；脚本在迁移策略门禁阶段停止，Maven、Docker、NAS 与测试服写入均未开始。按失败 tag 退休规则，r1 不再复用。

GREEN: dcc-publish-direct-policy-metadata -> PASS，将该 SQL 按实际更新历史审批策略的行为声明为 `type=data`，依赖 `20260719_business_approval_policy` 与 `20260720_dcc_publish_form_policy_seed`；`test_dcc_publish_direct_policy_sql.py` 与 migration policy 共 10 tests PASS。

RED: build-release-r2-pytest-basetemp-parent -> FAIL，后端合同 10 tests、前端静态合同和 `pnpm ts:check` 已通过，但脚本未创建 `--basetemp` 父目录，导致 release script tests 出现 17 个 setup errors；Maven package、Docker、NAS 最终目录与测试服部署均未开始，r2 退休。

SIDE_EFFECT: edhr-object-lock-preflight-r2 -> 构建前既有 eDHR 保留策略验证写入 1 个受 COMPLIANCE retention 与 legal hold 保护的探针对象；该对象不是 MinIO 业务数据或发布数据同步，不能删除，已记录 versionId 的脱敏事实但不记录 endpoint/credentials。

GREEN: pytest-basetemp-parent-fix -> PASS，`Invoke-StandardReleaseContractTests` 在 pytest 前显式创建 `$pytestParent`；维护合同 23 tests 和 PowerShell AST PASS。下一次构建使用新 tag `release-20260912-one-button-app-r3`。

RED: app-release-edhr-probe-side-effect -> FAIL，合同证明标准 build-release 在测试门禁前调用 `Invoke-EdhrStorageRetentionVerifier`，导致失败构建也写入受法律保留约束的探针对象。

GREEN: app-release-edhr-probe-side-effect -> PASS，eDHR 写入型保留验证现仅在非 build-release 目标发布流程执行；标准 `app-release` 构建不再写对象存储探针。聚焦合同 1 test 与 PowerShell AST PASS。

GREEN: dcc-publish-direct-policy-metadata -> PASS，将该 SQL 按实际 UPDATE 历史审批策略行为声明为 `type=data`，依赖 `20260719_business_approval_policy` 与 `20260720_dcc_publish_form_policy_seed`；`test_dcc_publish_direct_policy_sql.py` 和 `test_release_migration_policy_gate.py` 共 10 tests PASS。

RED: build-release-command-binding-r1 -> FAIL，手工命令将 `BackendRepoRoot` 误写为不存在的参数名，PowerShell 在参数绑定阶段退出；脚本主体、Maven、Docker、NAS 与服务器写入均未开始，releaseTag r1 仍未占用。修正为脚本声明的精确参数名并复用同一未启动 tag。

RED: build-release-r1-migration-metadata -> FAIL，修正命令后 `20260911_dcc_publish_direct_policy.sql` 缺少 `release-migration` metadata；脚本在迁移策略门禁阶段停止，Maven/Docker/NAS/测试服写入均未开始。按失败 tag 退休规则，r1 不再复用。

BLOCKER: C05/P4/P5 -> `corepack pnpm --dir IntRuoyiFronted ts:check` FAIL，任务 app worktree 缺 `node_modules/cross-env`；权威 Playwright 目录仍缺 1.60.0 依赖/可执行文件。未临时安装依赖或换版本兜底。

AUTHORIZATION_BOUNDARY: 本轮未访问 NAS、MySQL、MinIO、SSH、测试服、正式服或审查服；未构建 Docker 镜像、未打安装包、未启动服务、未运行真实 E2E。P3 的远程写入、P4/P5 E2E 与最终发布仍需满足各自前置条件和当次授权。

RED: build-release-r3-readonly-migration-ledger -> FAIL，测试服只读 migration ledger SSH/Bash 命令在解析 SQL 时失败；失败发生在 Maven、Docker、NAS 和任何服务器写入之前，releaseTag `release-20260912-one-button-app-r3` 退休，不再复用。

GREEN: readonly-migration-ledger-base64-sql -> PASS，将只读 ledger SQL 以 Base64 传入远端 Bash 后解码执行，避免 PowerShell/SSH/Bash 多层引号破坏 SQL；聚焦回归测试与 PowerShell AST 解析均 PASS。

RED: build-release-r4-windows-command-line-length -> FAIL，只读 migration ledger 已通过，但 schema-only rehearsal 为 619 个 migration 分别追加 `--migration <path>`，触发 Windows 进程命令行长度上限；失败发生在 Docker 临时容器启动之前，Maven、Docker 构建、NAS 和服务器写入均未开始，releaseTag `release-20260912-one-button-app-r4` 退休，不再复用。

BDD: schema rehearsal 使用迁移清单文件 -> Given 本次 app-release 包含 619 个 required migration / When PowerShell 调用 schema-only rehearsal / Then 将全部迁移路径写入 UTF-8 JSON 数组并只传 `--migration-list <json-file>` 单一参数，Python 严格读取非空字符串数组，避免 Windows 命令行超长且不引入 fallback。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_schema_rehearsal.py --basetemp .tmp-schema-rehearsal-red` -> FAIL，2 failed、5 passed；发布脚本仍逐项追加 `--migration`，Python 虽声明 `--migration-list` 但没有读取 JSON 路径数组。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_build_preflight_cache.py --basetemp .tmp-schema-rehearsal-green` -> PASS，49 tests；覆盖 migration-list UTF-8 JSON 解析、非法对象/空数组/非字符串成员拒绝、PowerShell 单文件参数合同及相邻 build preflight cache 回归。

GREEN: powershell-ast-schema-rehearsal-migration-list -> PASS，`publish-int-ruoyi.ps1` PowerShell AST 解析无错误；本轮修复未提交，也未操作服务器或 NAS。

RED: build-release-r5-schema-rehearsal-case-mode -> FAIL，619 条迁移已通过文件参数进入临时 MySQL，但 `20260518_dcc_approval_task_name_fix.sql` 引用大写 `ACT_RU_TASK`；测试服结构快照中的实际表名为小写，测试服 compose 固定 `lower_case_table_names=1`，临时容器遗漏该运行参数而报 `ERROR 1146`。失败发生在 Maven 正式打包、Docker 镜像构建、NAS 上传和测试服写入之前，releaseTag `release-20260912-one-button-app-r5` 退休，不再复用。

BDD: schema-only 演练复制测试服表名大小写模式 -> Given 测试服 MySQL 以 `lower_case_table_names=1` 运行且结构快照包含小写 Flowable 表 / When 临时 MySQL 执行包含大写兼容引用的全部迁移 / Then 临时容器必须使用同一 `lower_case_table_names=1` 参数并继续严格执行全部迁移，不允许跳过或改写 SQL。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_schema_rehearsal.py` -> FAIL，新增合同确认临时容器尚未带 `--lower_case_table_names=1`；同时要求后续错误必须直接报告失败迁移文件和第几轮演练，缩短排障路径。

BDD: schema-only 演练只消费目标预检计划的待应用集合 -> Given 测试服只读迁移账本已生成绑定本次 619 条清单的 preflight plan / When 启动 schema-only 演练 / Then 计划为 `SKIP_ALREADY_APPLIED` 的历史迁移不得重跑，只有 `APPLY` 集合按计划顺序执行两轮；计划与清单集合不一致必须失败，不能静默遗漏。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_schema_rehearsal.py` -> FAIL，演练入口尚未读取 preflight planner 的迁移类型和 `requiresTargetPreflight`，会把类型为 data 或依赖历史业务基线的 schema 迁移错误送入空结构库。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_showroom_release_sql_contract.py` -> PASS，78 tests；PowerShell AST PASS。新增 `requiresTargetPreflight` 元数据、planner item 类型绑定、schema-only 严格分流和迁移集合一致性校验；失败信息包含具体文件与 pass 编号。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_sql_preflight_gate.py` -> FAIL，1 个固定 preflight fingerprint 断言因 planner item 新增 type/requiresTargetPreflight 绑定而变化；没有放宽摘要校验。

GREEN: 同一回归集合 -> PASS，115 tests；更新固定向量到新的规范化 planner 摘要，确保迁移分流字段继续参与不可变摘要。

RED: build-release-r7-schema-rehearsal-history-menu -> FAIL，`20260905_erp_kingdee_production_replenishment_list_sync.sql` 被账本判定为摘要变化后待重放，空结构库执行其 ERP 父菜单唯一性前置检查并报 `ERP production parent menu must exist exactly once`；失败在正式 Maven/Docker/NAS/测试服写入前，releaseTag `release-20260912-one-button-app-r7` 退休。

BDD: ERP 菜单基线迁移 -> Given schema 文件包含 ERP 菜单存在性前置检查 / When 构建前分类迁移 / Then 必须声明 `requiresTargetPreflight=true`，由测试服只读目标检查负责，schema-only 空库不得伪造菜单数据。

RED: build-release-r8-schema-rehearsal-history-menu -> FAIL，`20260907_dcc_publication_notification.sql` 在空结构库执行 DCC 审批权限菜单唯一性检查并报 `Missing or duplicate active DCC approve permission menu`；失败在正式 Maven/Docker/NAS/测试服写入前，releaseTag `release-20260912-one-button-app-r8` 退休。

BDD: DCC 发布通知菜单基线迁移 -> Given SQL 会检查父菜单、审批权限菜单、角色和租户菜单包 / When 进入 app-release 构建演练 / Then 必须声明 `requiresTargetPreflight=true`，空结构演练不构造业务菜单，目标只读检查负责真实基线。

RED: build-release-r9-schema-rehearsal-non-idempotent-ddl -> FAIL，`20260911_dcc_controlled_file_submit_idempotency.sql` 第一轮结构演练成功，第二轮在 `ALTER TABLE` 上报 `Duplicate column name 'submit_idempotency_key'`；失败在 Maven/Docker/NAS/测试服写入前，releaseTag `release-20260912-one-button-app-r9` 退休。

BDD: DCC 提交幂等迁移重复执行 -> Given schema-only 演练对待应用 schema 迁移执行两轮 / When 迁移增加列和唯一索引 / Then 缺失对象才创建，已有对象必须校验定义且不重复添加；定义不兼容时明确失败。

GREEN: `python -X utf8 -m pytest -q IntRuoyiBackend/script/tests/test_dcc_controlled_file_submit_idempotency_sql.py ...` -> PASS，5 tests；SQL 改为 information_schema 防护的可重复存储过程，并增加列/索引定义校验。

GREEN: build-release-r10-schema-rehearsal -> PASS，目标账本绑定的 schema-only 两轮演练首次完整通过，随后后端 31 模块 Maven package 与前端 build:test 均通过。

RED: build-release-r10-docker-inspect-format -> FAIL，离线基础镜像已成功加载，但 `Get-DockerImageIdentity` 通过 Windows `Start-Process` 传递带空格的 `{{json .}}` format 模板时被拆成多个参数，Docker 报 `template parsing error: unclosed action`；业务镜像、NAS 上传和测试服写入均未开始，releaseTag `release-20260912-one-button-app-r10` 退休。

BDD: Windows Docker 镜像身份取证 -> Given 基础镜像已从受控离线 tar 加载 / When 发布脚本读取镜像 Id 和 RepoDigests / Then 直接解析 `docker image inspect` 原生 JSON 数组并严格要求恰好一个镜像，不通过带空格的 format 模板跨进程传参。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py -k docker_image_identity` -> FAIL，旧实现仍包含 `--format {{json .}}`。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py` -> PASS，53 tests；本机真实 `docker image inspect` JSON 解析、镜像数量和 sha256 Id 校验 PASS。

RED: build-release-r11-docker-context-cleanup -> FAIL，后端/前端镜像已成功构建并导出，但删除临时 `docker-build-context` 时 Windows 报前端 bundle 路径瞬时不存在；NAS 上传和测试服写入未开始，releaseTag `release-20260912-one-button-app-r11` 退休。

BDD: Docker 构建上下文清理 -> Given 镜像导出完成 / When 删除包含大量前端 bundle 的临时上下文 / Then 进行有限次数、递增等待的可验证重试；5 次后仍残留必须明确失败，不能吞异常或把残留目录带入安装包。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py -k docker_build_context_cleanup` -> FAIL，旧清理逻辑只有一次 `Remove-Item`。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py` -> PASS，54 tests；PowerShell AST PASS，清理重试合同已锁定。

RED: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py -k docker_build_context_cleanup` -> FAIL，PowerShell `Remove-Item -Recurse` 重试仍不能稳定删除大型 bundle 树；废弃 r12 上验证 .NET `Directory.Delete(path, true)` 可完成清理。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py` -> PASS，54 tests；清理实现改为 .NET 目录删除、有限重试和最终存在性核验，未保留 PowerShell 递归删除路径。

RED: build-release-r13-docker-context-cleanup -> FAIL，即使改用 .NET `Directory.Delete(path, true)`，原始 `docker-build-context` 路径仍在大型前端 bundle 树上报 `Could not find a part of the path`；镜像和导出已成功，NAS/测试服写入未开始，releaseTag `release-20260912-one-button-app-r13` 退休。

BDD: Docker 构建上下文隔离清理 -> Given 镜像构建读取已结束且 context 位于待发布包内 / When 开始清理 / Then 先用同卷 `Directory.Move` 原子移出包目录，再删除隔离目录并确认原目录与隔离目录均不存在；任一残留或删除失败都明确阻断。

GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py` -> PASS，54 tests；清理改为同卷原子移出后删除，PowerShell AST PASS。

RED: build-release-r14-docker-context-cleanup -> FAIL，镜像和 tar 已成功生成，原 context 与隔离目录最终均不存在，但清理中的 `Directory.Delete` 瞬时找不到已消失的 bundle 文件，脚本仍错误抛出并未生成 manifest/NAS READY；releaseTag `release-20260912-one-button-app-r14` 退休。

BDD: 已完成清理的竞态错误处理 -> Given 删除异常发生 / When 原 context 与 cleanupRoot 均已不存在 / Then 将结果判定为清理成功并继续 manifest；只有任一目录仍存在时才重试或失败，避免假失败也不吞残留。

## Resume audit after r15

- Previous turn classification: progress (code and runtime evidence changed), but full task completion remains unproven.
- r15 session 58934 returned exit 1; no new build has been started in this resume.
- CORRECTION: r14/r15 cleanup directories are under LocalCacheRoot/publish-int-ruoyi, not LocalCacheRoot. Both still contain 763 files, with paths up to 306 characters. Earlier claims that both directories disappeared, Docker concurrent deletion was proven, or a PS7 manual delete proved PS5.1 compatibility were unsupported.
- BDD: Long-path release cleanup -> Given task-owned frontend artifacts include paths over 260 characters / When the production PowerShell 5.1 cleanup runs / Then it removes only the owned context, preserves sibling files, reports actual failures and returns nonzero for residual/invalid targets.
- BDD: No preflight omission -> Given an APPLY migration needs existing data / When build preflight runs / Then it must execute a bound read-only check; missing/unexecuted/failed checks stop before Maven, Docker, NAS and deploy.
- GREEN: experience-preflight -> PASS, task worktrees and r15 terminal status identified; subsequent actions limited to task-owned local regression fixtures and inspection until gate defects are resolved. No production or business data writes.

- RED: `python -X utf8 -m pytest scripts/tests/test_release_docker_context_cleanup.py -q` -> FAIL, 5 failed / 3 passed on the old cleanup; real >350-character fixture and unsafe-target failures reproduced under Windows PowerShell 5.1.26100.3624. Fixture-creation/pytest-default-temp ACL errors are prerequisite errors, not business RED evidence.
- GREEN: same cleanup test -> PASS, 8 behavioral tests. Direct Windows extended-length path deletion handles long descendants; exact package target, ancestor reparse rejection, sibling sentinel preservation and real file-lock failure were verified. All newly created cleanup fixtures removed; old release caches untouched.
- RED: `python -X utf8 -m pytest -q --tb=short --basetemp <task-cache>/target-check-red scripts/tests/test_release_target_data_preflight.py` -> FAIL, 9 failed: production runner absent and existing reference without an executed result incorrectly accepted.
- RED: same target suite with `--basetemp <task-cache>/target-check-extra-red` -> FAIL, 3 failed / 17 passed: historical contract masks executable MySQL comments, allows GET_LOCK, and production call is absent.
- GREEN: target data preflight + migration preflight matrix -> PASS, 30 tests; rejects unsafe SQL/executable comments, missing checks, altered plans, blank/wrong/multiple result rows and unexecuted results. Actual SSH SQL uses UTF-8 base64 stdin and a READ ONLY transaction; raw remote stderr is not printed.
- GREEN: `python -X utf8 -m pytest -q --tb=short --basetemp <task-cache>/resume-regression scripts/tests/test_release_docker_context_cleanup.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_target_data_preflight.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_publish_release_lock_cleanup.py` -> PASS, 154 tests in 18.19s; PowerShell AST PASS.
- GREEN: experience-preflight -> PASS, authorized test host 172.30.30.58/root, read-only transport probe using SELECT @@session.transaction_read_only only; no migration, object write, NAS upload or service restart.
- GREEN: actual new SSH transport probe -> PASS, server reports session.transaction_read_only=1. This verifies the transport, not the 58 missing migration predicates.
- BLOCKER: `release_target_data_preflight.py --prospective-manifest <r15>/prospective-manifest.json --target-state <r15>/target-state-test.json --build-evidence <r15>/build-preflight-evidence.json --package-root <r15-package> --checks-root <app>/IntRuoyiBackend/sql/mysql/target-preflight --server 172.30.30.58 --user root --output <task-cache>/r15-target-preflight-audit.json` -> TARGET_PREFLIGHT_MISSING; 58 missing, 0 passed, sshStarted=false. Saved r15 data used only for diagnosis; it does not qualify a new release.
- Source audit: verified branch codex/test-release-signature-t1-active-unique-20260911 contains 16 target-preflight files and ERP/DCC schema-menu splits absent here. Do not replace the current branch wholesale: it also has newer migrations the historical branch lacks. Next implement selective integration/check coverage, then deployment-time preflight/self-contained verification and UI acceptance.
- CORRECTION: historical RED/GREEN lines written before running their commands, 115-vs-116 count claims, and broad P3 PASS descriptions are not independent acceptance evidence. This resume records observed results only. Earlier hook bypasses and unrelated raw process output must not be copied into committed evidence.

- Independent review raised two additional local-only validation defects: mysql client commands and comment/literal parsing. No such input was sent to a server. Regression RED for the added cases was observed; the contract now scans literals/comments together and rejects client commands and executable comments. MySQL binary-mode disables noninteractive client commands; delimiter/charset are also explicitly forbidden by the contract. Official reference is linked in bug-regression-evidence.md.
- GREEN: final regression with `--basetemp <task-cache>/resume-final-regression` over the prior eight suites plus release_digest_vectors and app_release_package_governance -> PASS, 182 tests in 28.13s; final AST PASS. New cleanup/target-data/schema/plan tests are now mandatory in Invoke-StandardReleaseContractTests.
- GREEN: final transport after binary-mode change -> PASS, read-only session probe returns 1 on the authorized test host.
- GREEN: bug-regression evidence validator and CI/CD environment evidence validator -> PASS (document structure only, not deployment acceptance).
- Remaining coverage is saved durably in target-preflight-gaps.md. No new build/release was attempted while this coverage remains missing. Task and global goal remain active; no worktree merge/delete or completed closeout is claimed.

- Implementation commit: c26c705, task-owned local gate and cleanup corrections only. The staged whitespace check reported one trailing blank line in target-preflight-gaps.md; it was removed in the subsequent task-record correction. This documentation formatting issue does not change the observed 182-test result.

## Resume after application target-preflight integration

- GREEN: app-target-preflight-coverage -> PASS，应用 worktree D:/IntRuoyiWorktree/r260911-release-button/a 已提交 4fb258315（任务: 补齐发布目标只读预检门禁），补齐 58 个 IntRuoyiBackend/sql/mysql/target-preflight/*.preflight.sql，并在应用后端目录重跑目标套件：python -X utf8 -m pytest -q --tb=short --basetemp <app-worktree>/.tmp-pytest-app-preflight-continue3 script/tests/test_release_target_preflight_files.py script/tests/test_release_manifest_migration_contract.py script/tests/test_release_migration_metadata.py script/tests/test_release_migration_policy_gate.py script/tests/test_release_preflight_plan.py script/tests/test_release_manifest_validator.py -> 61 passed。
- GREEN: maintenance-preflight-regression -> PASS，python -X utf8 -m pytest -q --tb=short --basetemp <maintenance-worktree>/.tmp-pytest-target-local scripts/tests/test_release_target_data_preflight.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_release_digest_vectors.py scripts/tests/test_app_release_package_governance.py -> 174 passed。
- GREEN: r15-target-readonly-preflight-after-app-4fb258315 -> PASS，使用既有 r15 prospective-manifest.json、target-state-test.json、build-preflight-evidence.json 和包根，仅替换 checks-root 为应用提交 4fb258315 的 target-preflight 目录；测试服 172.30.30.58 在 READ ONLY 事务中执行 58/58 条检查通过，sshStarted=true，证据 evidence/r15-target-preflight-audit-after-app-4fb258315.json。该结果只关闭缺口，不恢复 r15 发布资格。
- NEXT: r15 仍按失败 tag 退休；下一步必须用新 releaseTag 重建 app-release 包，sourceRepos 需要指向应用提交 4fb258315 或后续等价提交，继续禁止 with-data、全量数据库、MinIO 数据同步和正式服写入。

## Resume after local restart

- USER_AUTHORIZATION: 用户要求“刚才重启了，继续”并已给出“授权”；本轮继续范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、`mark-tested` 或 `promote-prod`。
- GREEN: resume-local-worktree-status -> PASS，维护 worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m` 与应用 worktree `D:/IntRuoyiWorktree/r260911-release-button/a` 均为 clean，当前提交分别为 `66e4088` 与 `4fb258315`。
- GREEN: resume-test-server-readonly-preflight -> PASS，测试服 `172.30.30.58` 只读检查通过：Docker Compose `2.27.0`，`/var/lib/docker` 使用率 27%，`intruoyi-mysql` healthy，backend/frontend running，backend health `UP`，frontend HTTP `200`，远端 release 目录不存在 `release-20260913-one-button-app-r16`。
- RED: resume-nas-config-path-operator-error -> FAIL，本地首次 NAS 只读检查误选不存在的历史 JSON 文件名，未连接 NAS、未写服务器、未创建发布包；更正为已存在的受控 NAS JSON 后继续。
- GREEN: resume-nas-target-preflight-r16 -> PASS，受控 NAS `Backup/ReleasePackage/release-20260913-one-button-app-r16` 不存在；本次检查未打印或记录密码值，断开映射时仅出现共享名终端编码显示异常，不影响路径判定。
- SOURCE_FREEZE_INPUT: maintenance `66e4088`，application `4fb258315`；计划执行新 releaseTag `release-20260913-one-button-app-r16`，`Component=intruoyi`，`PublishScope=app-release`，显式 `SkipDatabaseSync/SkipMinioSync`，成功后仅执行同 tag 测试服 `deploy-release`。
- RED: build-release-r16-target-preflight-support-scan -> FAIL，`release_migration_policy_gate.py` 误把 `sql/mysql/target-preflight/*.preflight.sql` 支撑文件纳入发布迁移扫描，报 `missing release-migration metadata`；失败发生在 Maven、Docker、NAS 上传和测试服写入之前，releaseTag `release-20260913-one-button-app-r16` 退休，不再复用。
- BDD: 目标只读预检支撑 SQL 不进入发布迁移清单 -> Given `sql/mysql/target-preflight` 存放只读检查 SQL / When migration policy gate 默认扫描 `sql/mysql` / Then 只扫描真正发布迁移，支撑 SQL 不要求 `release-migration` metadata 且不进入 manifest。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_sql_preflight_gate.py -k target_preflight_support_sql --basetemp .tmp-r16-policy-red` -> FAIL，复现支撑 SQL 被误扫为发布迁移。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_sql_preflight_gate.py -k "target_preflight_support_sql or migration_policy_gate" --basetemp .tmp-r16-policy-green` -> PASS，7 tests。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short --basetemp .tmp-r16-policy-regression scripts/tests/test_release_target_data_preflight.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_release_digest_vectors.py scripts/tests/test_app_release_package_governance.py` -> PASS，175 tests；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- NEXT: 使用新 releaseTag `release-20260913-one-button-app-r17` 重新 build-release；source freeze 必须更新为本次已提交维护修复提交，仍禁止 with-data、MinIO 数据同步、全量数据库和正式服写入。
- GREEN: r17-preflight-target-absence -> PASS，维护提交 `c77cefe` 与应用提交 `4fb258315` 均 clean；测试服远端 release 目录和 NAS `Backup/ReleasePackage/release-20260913-one-button-app-r17` 均不存在。
- GREEN: build-release-r17-pre-nas -> PASS，migration policy 619 条通过，后端 workflow 合同 10 tests、前端静态合同、`pnpm ts:check`、发布脚本 125 tests、PowerShell digest、Docker daemon、Spring constructor、测试服 target data preflight 58/58、schema-only rehearsal、后端 Maven package、前端 `pnpm build:test`、前后端 Docker build 与 image save 均通过；包范围仍为 `app-release`，无 MySQL 全量 dump 或 MinIO 数据同步。
- RED: build-release-r17-nas-staging-package-id -> FAIL，NAS staging 上传和本地完整性复制完成后，`Test-ReleasePackageIntegrity` 使用 staging 目录名 `.release-20260913-one-button-app-r17.staging-*` 校验 `manifest.packageId`，报 `packageId mismatch`；脚本未移动到最终 READY 目录，NAS 只读复核未发现 r17 final/staging 残留，测试服未写入，releaseTag `release-20260913-one-button-app-r17` 退休。
- BDD: NAS staging 使用最终包名校验 -> Given 原子上传先复制到 `.staging-*` 目录 / When 对 staging 包做完整性复核 / Then manifest 的 `packageId` 必须与最终 package directory name 比较，而不是与临时 staging 目录名比较；复核通过后才允许同卷 move 到 READY。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "staging_directory_name or nas_ready_requires_atomic_upload" --basetemp .tmp-r17-staging-red` -> FAIL，复现 `ExpectedPackageDirectoryName` 参数缺失和 NAS staging 调用未绑定最终包名。
- GREEN: 同一目标用例 -> PASS，2 tests；`Test-ReleasePackageIntegrity` 新增 `ExpectedPackageDirectoryName`，`Copy-ReleasePackageToNas` 在 staging 复核时传入最终包名。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short --basetemp .tmp-r17-staging-regression scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py` -> PASS，135 tests；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- NEXT: 使用新 releaseTag `release-20260913-one-button-app-r18` 重新 build-release；source freeze 必须更新为本次已提交维护修复提交，仍禁止 with-data、MinIO 数据同步、全量数据库和正式服写入。

## Resume after r18 interrupted local build

- USER_AUTHORIZATION: 用户回复“继续/授权”；本轮继续范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、`mark-tested` 或 `promote-prod`。
- GREEN: experience-preflight-r19 -> PASS，已重读服务器访问、登录、发布备份恢复、worktree、PowerShell、测试服发布与 without-data/app-release 经验门禁；本轮继续禁止 with-data、全量数据库、MinIO 数据同步、正式服/审查服写入。
- RED: build-release-r18-interrupted-local-cache -> FAIL，重启后发现本地 `release-20260913-one-button-app-r18` 仅存在 `evidence/` 与 `required-sql/` 且缺少 `manifest.json`，判定为未完成半成品缓存；未发现可放行安装包，按失败 tag 退休，不复用。
- GREEN: r19-source-freeze -> PASS，维护 worktree `618da2d1dd53f0b5195957dede856fabbf29fafc` 与应用 worktree `4fb258315489dd789914bef0cc80ec08fc943db2` 均 clean；本地 `release-20260913-one-button-app-r19` 不存在；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- SOURCE_FREEZE_INPUT: maintenance `618da2d1dd53f0b5195957dede856fabbf29fafc`，application `4fb258315489dd789914bef0cc80ec08fc943db2`；计划执行新 releaseTag `release-20260913-one-button-app-r19`，`Component=intruoyi`，`PublishScope=app-release`，显式 `SkipDatabaseSync/SkipMinioSync`，成功后仅执行同 tag 测试服 `deploy-release`。
- RED: build-release-r19-source-dirty -> FAIL，构建命令启动前已把本轮 `execution-log.md` 与 `docs/request-command-log.md` 记录写入维护 worktree，导致维护来源 dirty；脚本在 `SOURCE_DIRTY: maintenance` 门禁停止，Maven、Docker、NAS 上传和测试服写入均未开始。r19 退休，不复用。
- NEXT: 先提交任务记录，再使用新 releaseTag `release-20260913-one-button-app-r20` 重新 build-release；source freeze 必须更新为提交后的维护 HEAD，仍禁止 with-data、全量数据库、MinIO 数据同步和正式服写入。

## r20 fail-fast gap: NAS config format validated too late

- SOURCE_FREEZE_INPUT: maintenance `7a4cc6a`，application `4fb258315`；两个任务 worktree 均 clean。执行 `release-20260913-one-button-app-r20`，`PublishScope=app-release`，显式 `SkipDatabaseSync/SkipMinioSync`。
- GREEN: build-release-r20-pre-nas -> PASS，迁移策略 619 条通过，后端 workflow 合同 10 tests、前端静态合同、`pnpm ts:check`、发布脚本 125 tests、PowerShell digest、Docker daemon、Spring constructor、测试服 target data preflight 58/58、schema-only rehearsal、后端 Maven package、前端 `pnpm build:test`、前后端 Docker build、image save、manifest 生成与本地 integrity 均通过；本地包大小约 0.67GiB，仍为 `app-release` 且不含数据库/MinIO 数据包。
- RED: build-release-r20-nas-config-json-late -> FAIL，命令错误地把 `runtime-control.local.yaml` 传给 `-NasConfigPath`，而脚本只接受 UTF-8 JSON；旧脚本到 NAS 上传阶段才 `ConvertFrom-Json` 失败，浪费了一轮 Maven/Docker 构建。测试服部署未开始；r20 按失败 tag 退休，不复用。
- BDD: NAS 配置格式前置校验 -> Given build-release 必须最终上传 NAS READY 包 / When `-NasConfigPath` 缺失、不是 JSON 或来源 dirty / Then 必须在 SQL 扫描、测试、Maven、Docker 和 NAS 上传前失败，并输出明确错误。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k nas_config --basetemp .tmp-r20-nas-json-red` -> FAIL，旧脚本没有在 SQL 扫描前调用 `Read-NasReleaseConfig`。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "nas_config or tests_and_source_freeze" --basetemp .tmp-r20-nas-json-green` -> PASS，2 tests；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_build_preflight_cache.py --basetemp .tmp-r20-nas-config-regression` -> PASS，132 tests。
- NEXT: 提交 NAS 配置前置门禁修复后，使用新 releaseTag `release-20260913-one-button-app-r21` 和现有受控 JSON NAS 配置重建 `app-release` 包；仍禁止 with-data、全量数据库、MinIO 数据同步和正式服写入。

## r21 pre-commit fixes: app-release scope and deploy env transaction

- BDD: workflow 构建动作固定 app-release -> Given 操作者通过三按钮 workflow 生成程序包 / When 后端编排调用底层 `build-release` / Then 服务端固定 `PublishScope=app-release`，不得继续传旧 `code-only`。
- RED: `mvn -pl yudao-module-infra -Dtest=ReleaseWorkflowOrchestratorTest#buildButtonDispatchesOneServerOwnedAppReleaseOperation test` -> FAIL，断言期望 `app-release`，实际仍为 `code-only`；失败发生在本机单测，未访问服务器、NAS、数据库或 MinIO。
- GREEN: app-workflow-scope -> PASS，同一 Maven 单测通过；随后 `mvn -pl yudao-module-infra -Dtest=ReleaseWorkflow*Test test` -> PASS，25 tests；workflow package 静态扫描确认不再存在 `setPublishScope("code-only")`。
- BDD: deploy-release 先写 `.env.next` 后原子切换 -> Given READY 包已通过迁移和部署前验包 / When 测试服 deploy-release 准备重启服务 / Then 先上传部署控制文件到 `.env.next`，迁移成功后再切换 `.env` 并强制重建服务，最后校验实际 backend/frontend 镜像 tag。
- GREEN: maintenance-deploy-transaction-regression -> PASS，`python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp .tmp-pytest-one-button-p1` -> 66 passed；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- NEXT: 分别提交 app worktree 的 scope 修正与 maintenance worktree 的部署事务修正；提交后使用新 releaseTag 继续 `app-release` build-release -> publish-test，仅限测试服/NAS，不执行正式服、审查服、`mark-tested`、`promote-prod` 或 `promote-backup`。

## r23 immutable package gate: ops-runtime must be built into manifest

- RED: package-integrity-r23-ops-runtime -> FAIL，本地复核 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260913-one-button-app-r23` 返回 `ops-runtime/actions/01-立即备份.bat: undeclared file`。r23 已有本地程序包和 `.deploy-control-*`，但未取得可验证的不可变包资格，不得继续 publish-test，也不得复用该 tag。
- ROOT_CAUSE: `Copy-ReleaseOpsRuntimePackage` 在 `deploy-release` 阶段从应用 worktree 复制 `script/backup-ops/*` 到发布包目录 `ops-runtime/`，发生在 `manifest.json` 与 `packageDigest` 生成之后；这违反“同一不可变包”合同，也会让部署阶段依赖源码 worktree。
- BDD: ops-runtime 是包内已登记制品 -> Given build-release 生成标准 `app-release` 程序包 / When 后续 deploy-release 同一 tag / Then `ops-runtime` 必须在构建期复制进包并进入 manifest/packageDigest，部署期只读取包内文件打包上传，不允许再次从源码 worktree 修改发布包。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "ops_runtime" --basetemp .tmp-r23-ops-runtime-red` -> FAIL，2 failed，证明旧脚本没有构建期 `New-ReleaseOpsRuntimePackage` 且部署期会修改包。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "ops_runtime or deploy_release_control_files_do_not_pollute_local_package_cache or nas_ready_requires_atomic_upload" --basetemp .tmp-r23-ops-runtime-green` -> PASS，4 tests；PowerShell AST 严格解析 PASS。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py --basetemp .tmp-r23-ops-runtime-regression` -> PASS，139 tests。
- IMPLEMENTATION: 新增 `New-ReleaseOpsRuntimePackage`，仅在 `build-release` 构建期从源码复制并排除 `backup-ops.secrets.json`；`Copy-ReleaseOpsRuntimePackage` 改为只验证并上传包内 `ops-runtime`，缺失或含 secrets 立即失败。
- NEXT: 提交维护仓修复后使用新 releaseTag `release-20260913-one-button-app-r24` 重新生成 `app-release` 包；r23 判废，不发布测试服，不执行正式服、审查服、`mark-tested`、`promote-prod` 或 `promote-backup`。

## r24 pre-build app preflight scope gate

- BDD: app-release 迁移预检合同 -> Given 标准程序包固定为 `PublishScope=app-release` / When 应用仓生成迁移 preflight plan / Then CLI 与内部 allow-list 均接受 `app-release`，并继续执行版本化应用迁移；without-data 只禁止全量 MySQL dump、MinIO/DCC/runtime 数据包，不跳过版本化 SQL。
- RED: `python -X utf8 -m pytest D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\script\tests\test_release_preflight_plan.py -q -k "app_release" --basetemp D:\IntRuoyiWorktree\r260911-release-button\a\.tmp-pytest-one-button-app-release-red` -> FAIL，2 failed，旧 allow-list 拒绝 `app-release`。
- GREEN: `python -X utf8 -m pytest D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\script\tests\test_release_preflight_plan.py -q --basetemp D:\IntRuoyiWorktree\r260911-release-button\a\.tmp-pytest-one-button-app-release-green` -> PASS，19 passed。
- GREEN: `git -C D:\IntRuoyiWorktree\r260911-release-button\a diff --check -- IntRuoyiBackend/script/release/release_preflight_plan.py IntRuoyiBackend/script/tests/test_release_preflight_plan.py doc/tasks/one-button-app-release-20260911/task.md doc/tasks/one-button-app-release-20260911/execution-log.md` -> PASS。
- COMMIT: app preflight scope fix -> `1fbf293cf 任务: 接受app-release迁移预检`。
- CLEANUP: `git -C D:\IntRuoyiWorktree\r260911-release-button\a clean -fd -- .tmp-pytest-one-button-app-release .tmp-pytest-one-button-app-release-red .tmp-pytest-one-button-app-release-green` -> removed task pytest temp dirs；app worktree status clean。
- NEXT: 提交本维护仓任务记录后，以新 maintenance HEAD 与 application `1fbf293cf` 作为 r24 source freeze，继续生成 without-data/app-release 程序包；仍禁止 with-data、MinIO 数据同步、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r24 deploy-control pollution gate: preflight plan must stay outside immutable package

- SOURCE_FREEZE_INPUT: maintenance `f52a13e`，application `1fbf293cf`；两个任务 worktree 均 clean。r24 本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260913-one-button-app-r24` 已存在且含 `manifest.json`，`publishScope=app-release`，`packageDigest=a9d1d37cd3ba0acfe5a321f9f1fa1c32a6b400f6352e4301c760d6e7629f86ab`，不含 database/mysql/minio/files/data/dcc-object-inventory/runtime-data 目录。
- RED: package-integrity-r24-preflight-plan -> FAIL，本地 `Test-ReleasePackageIntegrity -PackagePath E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260913-one-button-app-r24 -ExpectedPackageDirectoryName release-20260913-one-button-app-r24` 返回 `preflight-plan.json: undeclared file`。该文件和 `preflight-target-state-test.json` 是部署期目标绑定控制文件，不属于已登记不可变发布包；r24 判废，不发布测试服，不复用该 tag。
- ROOT_CAUSE: `Write-ReleasePreflightPlan` 在 `deploy-release` 阶段把目标账本和 preflight plan 写入 `$releaseDir`，发生在 `manifest.json` 与 `packageDigest` 生成之后，等价于部署期修改发布包根；这违反“同一不可变包”合同。
- BDD: 部署控制文件不污染不可变包 -> Given READY app-release 包已完成 manifest/packageDigest / When deploy-release 生成目标绑定 `preflight-plan.json` 和 `preflight-target-state-<env>.json` / Then 两个文件必须写入 `.deploy-control-*` 并作为部署控制上传，不允许写回 `$releaseDir`。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "deploy_release_control_files_do_not_pollute_local_package_cache" --basetemp .tmp-r24-preflight-pollution-red` -> FAIL，旧脚本仍把 preflight plan 写入 release package。
- GREEN: 同一目标用例 -> PASS，1 test；`Read-ReleasePreflightPlan` 与 `Write-ReleasePreflightPlan` 改为读写 `$deployControlLocalRoot`。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py --basetemp .tmp-r24-preflight-pollution-regression` -> PASS，139 tests；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- CLEANUP: `git clean -fd -- .tmp-r24-preflight-pollution-regression` -> removed task pytest temp dirs；maintenance worktree retains only intended script/test/task-log changes.
- NEXT: 提交维护仓修复后使用新 releaseTag `release-20260913-one-button-app-r25` 重新生成 `app-release` 包；r24 判废，不发布测试服，不执行正式服、审查服、`mark-tested`、`promote-prod` 或 `promote-backup`。

## r25 app route-menu target preflight gate

- BDD: 活跃路线菜单兼容旧库和统一后库 -> Given `20260709_mes_route_flow_config_unification` 会把旧排产路线菜单 `900121/900122` 迁移为工艺路线下的 `5726/5727` / When `20260629_mes_smart_scheduling_role_scope` 在目标库执行或执行目标只读预检 / Then SQL 必须选择当前活跃的 query/update 菜单，不因旧菜单已删除而阻断，也不得跳过版本化权限迁移。
- RED: `python -X utf8 -m pytest -q IntRuoyiBackend\script\tests\test_mes_smart_scheduling_role_scope_sql.py IntRuoyiBackend\script\tests\test_release_target_preflight_files.py --basetemp .tmp-pytest-current-dirty-tests` -> FAIL，4 failed；旧迁移硬编码 `900121/900122`，目标只读预检没有验证旧/新路线菜单组合。
- GREEN: `python -X utf8 -m pytest -q IntRuoyiBackend\script\tests\test_mes_smart_scheduling_role_scope_sql.py IntRuoyiBackend\script\tests\test_release_target_preflight_files.py --basetemp .tmp-pytest-route-menu-green` -> PASS，29 passed。
- REGRESSION: `python -X utf8 -m pytest -q script\tests\test_mes_smart_scheduling_role_scope_sql.py script\tests\test_release_target_preflight_files.py script\tests\test_mes_route_flow_config_migration_sql.py script\tests\test_release_preflight_plan.py --basetemp ..\.tmp-pytest-route-menu-regression-2` from `IntRuoyiBackend` -> PASS，54 passed。
- COMMIT: app route-menu target preflight fix -> `6079138ea 任务: 兼容路线菜单统一后的发布预检`。
- NEXT: 提交本维护仓任务记录后，以 maintenance HEAD 和 application `6079138ea` 作为新 source freeze，使用新 releaseTag `release-20260913-one-button-app-r25` 重新生成 without-data/app-release 程序包；仍禁止 with-data、MinIO 数据同步、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r25 retired before deploy: stale local package cache invalid

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: r25-source-status -> PASS，维护 worktree `8eac852b0b9e6e2108c521213c2f8ab029465dc5` 与应用 worktree `6079138ea0ab614093c1c8b726d91c4ef12c5d95` 均 clean；测试服远端 `/var/lib/docker/intruoyi-releases/release-20260913-one-button-app-r25` 不存在。
- RED: r25-local-package-integrity -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260913-one-button-app-r25` 已存在，`manifest.json` 显示 `publishScope=app-release`、`component=intruoyi`，但 `Test-ReleasePackageIntegrity -ExpectedPackageDirectoryName release-20260913-one-button-app-r25` 返回 `preflight-target-state-test.json: undeclared file`；该本地包不是完整不可变 READY 包，不得发布测试服，也不得复用该 tag。
- ROOT_CAUSE: r25 本地包创建时间早于路线菜单修复提交 `6079138ea`，manifest source commits 仍指向旧应用提交 `ba1a6b718`，并残留未登记部署控制文件；属于旧失败缓存，不是当前 source freeze 的有效制品。
- NEXT: r25 判废退休；提交本记录后使用新 releaseTag `release-20260913-one-button-app-r26`，source freeze 固定维护仓提交和应用 `6079138ea` 或后续提交，继续生成 without-data/app-release 程序包。仍禁止 with-data、MinIO 数据同步、全量数据库复制、正式服/审查服写入、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r26 retired after stale package deploy attempt

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: r26-local-and-nas-package-integrity -> PASS，本地 `Test-ReleasePackageIntegrity` 通过，NAS `Backup/ReleasePackage/release-20260913-one-button-app-r26` 存在；manifest 显示 `publishScope=app-release`、`component=intruoyi`、`packageDigest=13e67af60286046b3ba7a8d6cd1b4c766d7dce2cf9c526f91076531efab79564`，且包内无 `database/mysql/minio/files/data/dcc-object-inventory/runtime-data` 目录。
- RED: deploy-release-r26-stale-app-source -> FAIL，r26 manifest 绑定应用提交 `6079138ea`，缺少后续 `8ec193169` 对 `20260709_mes_rt000006_batch_record_mapping.sql` 的“目标路线不存在即不适用”修复；测试服 required SQL 执行时报 `ERROR 1644 (45000): Missing RT000006 pressure pump route`。
- SIDE_EFFECT: deploy-release-r26-edhr-probe -> r26 deploy-release 在版本切换前调用 eDHR Object Lock verifier 并写入一个受保护探针对象；该对象不是 MinIO 数据同步，但仍属于无数据程序发布不应产生的对象存储写入副作用。
- RESULT: r26 未切换测试服版本；release operation lock 已释放为 FAILED。旧 r26 判废不复用；必须使用新 releaseTag 从当前维护/应用提交重新 build-release。

## r27 app-release deploy must not write Object Lock probe

- BDD: app-release 部署不写对象探针 -> Given 标准程序包固定为 `PublishScope=app-release` 且用户要求 without-data / When 执行 `deploy-release` / Then 只校验目标 `EDHR_S3_*` 配置存在和格式，不调用 `Invoke-EdhrStorageRetentionVerifier`，不写 Object Lock 探针对象。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "edhr_storage_probe" --basetemp .tmp-r27-edhr-probe-red` -> FAIL，旧脚本仍在 app-release deploy 路径调用 `Invoke-EdhrStorageRetentionVerifier -BackendRepo $backendRepo`。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "edhr_storage_probe or nas_config or tests_and_source_freeze" --basetemp .tmp-r27-edhr-probe-green` -> PASS，3 passed；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- IMPLEMENTATION: `deploy-release` 保留 `Assert-EdhrProtectedStorageConfig` fail-fast 配置校验，但移除 app-release 路径的写对象 verifier 调用；长期门禁已合并到 `docs/release-build-preflight-lessons.md` 并更新 `docs/experience-index.md` 路由。
- NEXT: 提交维护仓修复后使用新 releaseTag `release-20260914-one-button-app-r27`，source freeze 固定维护仓提交后 HEAD 与应用仓 `1bf4504cc`，重新生成 without-data/app-release 程序包并发布测试服。

## r27 retired: interrupted local package cache

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: r27-local-regression-recheck -> PASS，维护仓聚焦发布门禁 3 passed，包治理/schema/digest 回归 143 passed，`publish-int-ruoyi.ps1` PowerShell AST PASS；应用仓迁移预检 pytest 27 passed，ReleaseWorkflow Maven 合同 14 tests PASS。
- RED: build-release-r27-interrupted-local-cache -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r27` 已存在并包含 image tar、required-sql、ops-runtime 和 evidence，但缺少根目录 `manifest.json`；`Test-ReleasePackageIntegrity` 返回 `manifest.json: missing manifest`。测试服远端 `/var/lib/docker/intruoyi-releases/release-20260914-one-button-app-r27` 不存在，未发现活动构建进程，判定为重启/中断遗留半成品缓存。
- RESULT: r27 不是完整 READY 包，不得发布测试服，不得复用该 tag。旧 r27 保留为本地失败证据，下一轮必须使用新 releaseTag `release-20260914-one-button-app-r28`，source freeze 固定维护仓提交后 HEAD 与应用仓 `1bf4504cc`。

## r28 retired: balloon XLSX cleanup target already normalized

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: build-release-r28 -> PASS，source freeze 为维护仓 `0e60e0d08d984dcb4c1ca5f901300723988e6bb4`、应用仓 `1bf4504cc9e972c0a61c258f338fcd65dcc2f15a`；迁移策略 619 条、target-data preflight 56/56、schema-only 演练、后端 Maven package、前端 `build:test`、Docker build/save、本地 package integrity 和 NAS 原子 READY 均通过；包为 `PublishScope=app-release`，`packageDigest=79891ff068bdd154142eb408c5b55522933b2026165fd3cf78249da80c31f532`，无数据库/MinIO 数据目录。
- RED: deploy-release-r28-balloon-cleanup-target-mismatch -> FAIL，测试服部署在版本切换前执行 required SQL `20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup.sql` 时失败：`ERROR 1644 (45000): balloon XLSX route 00002 invalid process cleanup target mismatch`；release lock 已释放为 FAILED，测试服 `.env` 未切换到 r28。
- ROOT_CAUSE: 测试库当前 `ROUTE-XLSX-00001=23`、`ROUTE-XLSX-00002=26`，总数已满足后续绑定迁移要求的 `49`；`ROUTE-XLSX-00002` sort=26 是合法 `Z2620`，不是旧脚本假设要删除的无效 `B320`。旧 target preflight 只验证弱条件，未在构建前覆盖 `B320/Z2620/49` 目标合同。
- GREEN: app-balloon-cleanup-fix -> PASS，应用仓提交 `8e6c033c6` 增加 already-normalized no-op 分支和等价 target preflight；本地 cleanup/preflight 测试 11 passed，release migration 回归 40 passed，测试服只读执行新 preflight 返回 `TARGET_PREFLIGHT_PASS:20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup`。
- RESULT: r28 判废不复用。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r29`，source freeze 固定维护仓提交后 HEAD 与应用仓 `8e6c033c6`；继续禁止 with-data、MinIO 数据同步、全量数据库复制、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r29 retired: balloon Excel device seed count is target-derived

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test` 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: build-release-r29 -> PASS，source freeze 为维护仓 `bf9703d496a95aabe79ade0181fe77684cf54284`、应用仓 `8e6c033c6e53cc925d773486121e3dc051139966`；target-data preflight 55/55、schema-only 演练、后端 Maven package、前端 `build:test`、Docker build/save、本地 package integrity 和 NAS 原子 READY 均通过；包为 `PublishScope=app-release`，`packageDigest=e50c27ecc1ac0938b52d43849b1d1e5f2bdb94829b2d6fdf0b2244aeaa868040`，`manifestDigest=b7484ce46567401ec4d7ee5070775213b088eb6cdafd8805f894f06bdfb43f51`，无数据库/MinIO 数据目录。
- RED: deploy-release-r29-balloon-machine-count -> FAIL，测试服部署在版本切换前执行 required SQL `20260717_mes_balloon_excel_device_workstation_binding.sql` 时失败：`ERROR 1644 (45000): balloon Excel workstation machine count mismatch`；测试服 operation lock 已释放为 FAILED，`.env` 未切换到 r29，实际 backend/frontend 镜像仍为旧 tag。
- ROOT_CAUSE: 旧迁移硬编码 `@target_workstation_machine_count=83`，但测试库真实 `mes_dv_machinery_process` 仅存在 `棘突球囊扩张导管` 44 条设备绑定种子；`ROUTE-XLSX-00001` 当前没有设备绑定数据，不能按旧 Excel 来源数量强制 83。旧 target preflight 只校验表和基础主数据存在，没有在构建前验证设备绑定种子计数。
- BDD: 球囊 Excel 设备绑定计数由目标数据派生 -> Given without-data/app-release 只携带版本化 SQL / When 目标库只有当前有效设备绑定种子 / Then 迁移不得使用固定 83 阻断，target preflight 必须在发布前校验 route process=49 且可绑定设备种子数量大于 0。
- RED: `python -X utf8 -m pytest -q script\tests\test_mes_balloon_excel_device_workstation_binding_sql.py --basetemp ..\.tmp-pytest-r29-balloon-machine-red` -> FAIL，3 failed，证明旧 SQL 仍硬编码 83 且 target preflight 未覆盖设备绑定种子。
- GREEN: 应用仓提交 `9d886766a` 将迁移改为 `@minimum_workstation_machine_count=1` 与目标数据派生计数，并增强 `20260717_mes_balloon_excel_device_workstation_binding.preflight.sql`；定向测试 11 passed，相邻迁移/预检回归 37 passed，测试服只读 preflight 返回 `TARGET_PREFLIGHT_PASS:20260717_mes_balloon_excel_device_workstation_binding`。
- RESULT: r29 判废不复用。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r30`，source freeze 固定维护仓提交后 HEAD 与应用仓 `9d886766a`；继续禁止 with-data、MinIO 数据同步、全量数据库复制、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r30 retired: interrupted local package cache

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: r30-source-continuation-audit -> PASS，维护 worktree 与应用 worktree 均为任务分支且工作区 clean；本轮没有复用主工作区脏改动。
- RED: build-release-r30-interrupted-local-cache -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r30` 已存在并包含 `docker-build-context/`、`evidence/`、`required-sql/`，但缺少根目录 `manifest.json`；`Test-ReleasePackageIntegrity -ExpectedPackageDirectoryName release-20260914-one-button-app-r30` 返回 `manifest.json: missing manifest`。
- RESULT: r30 不是完整 READY 包，不得发布测试服，不得复用该 tag。旧 r30 保留为本地失败证据，下一轮必须使用新 releaseTag `release-20260914-one-button-app-r31`，source freeze 固定维护仓提交后 HEAD 与应用仓 `9d886766a`；继续禁止 with-data、MinIO 数据同步、全量数据库复制、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r31 source freeze

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r31 -> PASS，已按 `docs/experience-index.md`、`E:\IntRuoyi\docs\server-access.md` 和 `E:\IntRuoyi\docs\release-backup-restore.md` 复核测试服、without-data/app-release、worktree、NAS JSON、PowerShell、发布成功判定和禁止事项；正式服/审查服保持零写入。
- SOURCE_FREEZE_PLAN: maintenance 将使用本段证据提交后的 clean HEAD（基线 `76f1c78c30b6dc1f0072d488a1216c4cefea8210`），application 使用 `9d886766aa67ab0597c07ec9f01926c4a264d218`；两个任务 worktree 当前均 clean。计划执行新 releaseTag `release-20260914-one-button-app-r31`，`Component=intruoyi`，`PublishScope=app-release`，显式 `SkipDatabaseSync/SkipMinioSync`；成功后仅执行同 tag 测试服 `deploy-release`。
- GREEN: build-release-r31-local-integrity -> PASS，本地程序包 `release-20260914-one-button-app-r31` 完整性通过，`PublishScope=app-release`，`packageDigest=c8d461a330d8464875aa598c8611847f1f1eacb95597472abb2a06c471eb5ac5`，`manifestDigest=b86f8fe794ac2782793694152ddb53a7d5d19887948365d2703ec74913bd2b0d`，source freeze 为维护仓 `affe0e9c3acd5862e34d61f1356f9f7e02b775f2` 与应用仓 `9d886766aa67ab0597c07ec9f01926c4a264d218`。
- RED: pre-deploy-r31-puhui-target-preflight-gap -> FAIL，R31 包内 `20260718_mes_puhui_schedule_admin_role_visibility.sql` 不含 `requiresTargetPreflight=true`、`v_smart_scheduling_parent_id` 或 `NOT IN (0, 5100)`，且包内不存在该迁移 target preflight；继续发布会把已知菜单层级漂移问题推迟到测试服 required SQL 阶段。
- GREEN: app-puhui-target-preflight-fix -> PASS，应用仓提交 `ccd0d9a3a36d82888e4078a1ec262f251d186f7c` 增加璞慧排产管理员迁移目标只读预检与 `900120.parent_id IN (0,5100)` 兼容；定向 10 PASS，相邻迁移计划回归 29 PASS，diff-check PASS。
- RESULT: r31 判废不复用，未执行测试服 `deploy-release`，未切换 `.env`，未写正式服/审查服，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r32`，source freeze 固定维护仓提交后 HEAD 与应用仓 `ccd0d9a3`。

## r32 source freeze

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r32 -> PASS，已按 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\worktree-memory.md` 与 `E:\IntRuoyi\docs\powershell-memory.md` 复核 without-data/app-release、目标只读预检、NAS JSON、PowerShell、测试服发布成功判定和禁止事项；正式服/审查服/MinIO 数据同步保持零写入。
- GREEN: source-freeze-r32 -> PASS，维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m` 将使用本段证据提交后的 clean HEAD（基线 `cecdc120fb09f335137d2f7abc2eaa6a42145f88`），应用 worktree `D:\IntRuoyiWorktree\r260911-release-button\a` 为 clean `ccd0d9a3a36d82888e4078a1ec262f251d186f7c`；本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r32` 不存在。
- GREEN: config-preflight-r32 -> PASS，本轮 gitignored `config/runtime-control.local.yaml` 已复制到维护 worktree 并指向本轮应用 backend/frontend、维护 ops 与任务 state-dir；gitignored NAS JSON 已生成且 `server/share/username/password/nasReleaseRoot` 均 presence-check 通过，未输出 secret 值。
- GREEN: local-regression-r32 -> PASS，维护仓发布门禁/包治理/摘要/target-data/schema/lock 回归 `184 passed`，`publish-int-ruoyi.ps1` PowerShell AST PASS；应用仓璞慧排产与目标只读预检相邻回归 `29 passed`。
- GREEN: build-release-r32 -> PASS，source freeze 为维护仓 `3b56fa27589864662fdcb2750ce97d63ae0f97dd`、应用仓 `ccd0d9a3a36d82888e4078a1ec262f251d186f7c`；target-data preflight `30/30`、schema-only 演练、后端 Maven package、前端 `build:test`、Docker build/save、本地 package integrity、禁止项扫描和 NAS 原子 READY 均通过；包为 `PublishScope=app-release`，`packageDigest=04207f7dfc32a21de9e60a06ff97b87538e714cc4a4ebf63a8279b32bac15611`，`manifestDigest=9f494fbbfca92961cc01d596d3ec374728417127c5a936d42a25feb3522b246a`，无数据库/MinIO 数据目录。
- RED: deploy-release-r32-test-tenant-role-permission-count -> FAIL，测试服部署在版本切换前执行 required SQL `20260807_test_tenant1_all_role_permission_sync.sql` 时失败：`ERROR 1644 (45000) at line 2322: Unexpected source role-permission count`；operation lock 已释放为 FAILED，测试服 `.env` 仍为 `release-20260913-one-button-app-r21`，`.env.next` 为 r32，未切换实际 backend/frontend 镜像。
- ROOT_CAUSE: 该迁移中 `tmp_test_tenant1_role_permission_source` 实际包含 1678 条唯一角色权限源数据，但文件头、过程内源计数和目标菜单解析计数仍硬编码为 1676；旧静态测试也只复述常量，没有从 SQL 源数据反算，因此 build-release 前门禁漏检。
- BDD: 测试租户权限同步源计数自校验 -> Given app-release 构建将执行测试租户角色权限同步迁移 / When SQL 源数据行数与文件头或过程内计数断言不一致 / Then build-release 必须在 Maven、Docker、NAS 上传和测试服写入前失败，不得等到 required SQL 才暴露。
- RED: `python -X utf8 -m pytest -q script/tests/test_test_tenant1_all_role_permission_sync_sql.py --basetemp ..\.tmp-r32-role-permission-red2` -> FAIL，新增动态计数测试识别实际源数据为 1678 而 SQL 仍声明 1676。
- GREEN: app-role-permission-count-fix -> PASS，应用仓提交 `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03` 将源权限计数、过程内源计数和目标解析计数统一为 1678；`test_test_tenant1_all_role_permission_sync_sql.py`、`test_release_target_preflight_files.py`、`test_release_preflight_plan.py` 共 `30 passed`。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py --basetemp .tmp-r32-app-sql-gate-red` -> FAIL，证明维护仓 `Invoke-StandardReleaseContractTests` 旧逻辑没有在 build-release 前运行应用 SQL 静态迁移测试。
- GREEN: maintenance-app-sql-static-gate -> PASS，维护仓提交 `b189ef17cd070896e529472e0b29813e18386a8d` 将 `test_test_tenant1_all_role_permission_sync_sql.py` 纳入 `Invoke-StandardReleaseContractTests`，并确认该门禁位于 Maven/frontend build/Docker 之前；维护脚本回归 `8 passed`，PowerShell AST PASS。
- RESULT: r32 判废不复用。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r33`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `c4ba9d3f`；继续禁止 with-data、MinIO 数据同步、全量数据库复制、正式服、审查服、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r33 retired: stale local cache after restart

- USER_AUTHORIZATION: 用户继续并授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: source-continuation-r33 -> PASS，维护 worktree 当前为 clean `67ee44f3e8998e6f7698bc731881129d21bb264f`，应用 worktree 当前为 clean `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`；原主工作区保持不触碰。
- RED: r33-local-cache-source-mismatch -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r33` 虽通过 `Test-ReleasePackageIntegrity`，但 `manifest.json` 绑定维护仓 `cecdc120fb09f335137d2f7abc2eaa6a42145f88` 与应用仓 `ccd0d9a3a36d82888e4078a1ec262f251d186f7c`，缺少后续 `c4ba9d3f` 测试租户权限同步计数修复。
- RESULT: r33 判废不复用，未执行测试服 `deploy-release`，未切换 `.env`，未写正式服/审查服，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r34`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `c4ba9d3f`。

## r34 retired: stale local cache before source freeze

- RED: r34-local-cache-source-mismatch -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r34` 已存在，`manifest.json` 同样绑定维护仓 `cecdc120fb09f335137d2f7abc2eaa6a42145f88` 与应用仓 `ccd0d9a3a36d82888e4078a1ec262f251d186f7c`，缺少后续 `c4ba9d3f` 测试租户权限同步计数修复。
- RESULT: r34 判废不复用，未执行测试服 `deploy-release`，未切换 `.env`，未写正式服/审查服，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r35`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `c4ba9d3f`。

## r35 source freeze

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r35 -> PASS，已复核 `docs/experience-index.md` 命中的 without-data/app-release、测试服发布、目标只读预检、NAS 原子 READY、PowerShell 编排、服务器访问、release-backup-restore 与 worktree 门禁；本轮继续禁止 with-data、MinIO 数据同步、全量数据库复制、正式服/审查服写入和旧 tag 复用。
- GREEN: source-freeze-r35-plan -> PASS，维护 worktree 当前 clean `7f1e97f7959a00ef074cb778db6a2429b0926c90`，应用 worktree 当前 clean `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`；本地缓存 `release-20260914-one-button-app-r35` 不存在。实际构建 source freeze 以本段记录提交后的维护仓 clean HEAD 和应用仓 `c4ba9d3f` 为准。
- RED: build-release-r35-nas-config-yaml -> FAIL，命令误将 `config/runtime-control.local.yaml` 传给 `-NasConfigPath`；脚本在构建前返回 `NAS release config must be UTF-8 JSON`，未进入 SQL 扫描、Maven、Docker、NAS 上传或测试服写入。本轮确认正确 JSON 为 `runtime/runtime-control/nas-release-config/release-package.json`，只做字段存在性检查且未输出凭据。
- RESULT: r35 判废不复用。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r36`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `c4ba9d3f`。

## r36 retired: direct script source root parameters missing

- RED: build-release-r36-source-root-parameters -> FAIL，使用正确 NAS JSON 后脚本仍在构建前失败于 `Start-Process` 工作目录不存在；直接脚本命令未显式传入 `BackendRepoRoot`/`FrontendRepoRoot`，导致默认源码根推断不符合本任务两个隔离 worktree 的合同。未进入 Maven、Docker、NAS 上传或测试服写入，本地 `release-20260914-one-button-app-r36` 目录不存在。
- RESULT: r36 判废不复用。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r37`，并显式传入 `BackendRepoRoot=D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend`、`FrontendRepoRoot=D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiFronted`、正确 NAS JSON 与 backend runtime base 参数。

## r37 source freeze

- USER_AUTHORIZATION: 用户继续授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: source-freeze-r37-plan -> PASS，维护 worktree 当前 clean `a765588e6ec5cb13ba3429e195431053d06c5bcb`，应用 worktree 当前 clean `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`；本地缓存 `release-20260914-one-button-app-r37` 不存在；后端/前端工程、backend runtime base tar 和 NAS JSON 均存在。实际构建 source freeze 以本段记录提交后的维护仓 clean HEAD 和应用仓 `c4ba9d3f` 为准。

## r37 retired: package contained target-bound preflight evidence and ops config

- RED: local-json-summary-carrier -> FAIL，本轮一次 PowerShell `python - <<'PY'` 写法被 PowerShell 5.1 解析器拒绝，报 `Missing file specification after redirection operator`；未改代码、未连接远端、未写服务器。后续改用 PowerShell 原生 `ConvertFrom-Json` 摘要，遵守 PowerShell 门禁。
- GREEN: r37-local-package-summary -> PASS，本地包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r37` 存在，`manifest.json` 显示 `PublishScope=app-release`、sourceRoots 为 maintenance `1ad4c8d70de41a33af186a1e9f1d377f6391271a` 与 application `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`，sourceRoles 为 maintenance/backend/frontend 且 dirty=false；该摘要只证明本地包结构，不构成 READY 或可发布结论。
- RED: r37-manifest-forbidden-target-bound-content -> FAIL，`validate-release-manifest.ps1 -PackagePath E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r37 -Mode report-only` 返回 `FORBIDDEN_HARDCODED_TARGET_IP`，首个命中为包内 `evidence/target-data-preflight.json` 的测试服 IP；同一报告还发现 `ops-runtime/config/*.json` 与 `ops-runtime/script/deploy/manage-int-ruoyi-remote-root-disk.ps1` 中的目标 IP 和 secret-like 示例。该失败发生在测试服 `deploy-release` 之前，正式服/审查服/MinIO 数据同步仍为零写入。
- ROOT_CAUSE: build-release 把目标服务器只读 preflight 结果写入不可变包目录 `evidence/target-data-preflight.json`，并把 backup-ops config 示例及 target-bound 远程磁盘脚本打入 `ops-runtime`；这些内容属于目标环境运行时配置/证据，不应进入可跨测试服和正式服晋级的 without-data 程序安装包。
- BDD: 程序安装包不携带目标环境证据和配置 -> Given 标准 `PublishScope=app-release` 包用于测试服和正式服同 digest 晋级 / When 构建执行目标只读 preflight 并准备 ops-runtime / Then target preflight 证据只能留在构建临时证据目录，包内 ops-runtime 只能携带非秘密、非 target-bound 的运行脚本，不能包含 backup config、secret 示例或远程磁盘目标脚本。
- RED: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "target_data_preflight_evidence or ops_runtime_package_excludes" --basetemp .tmp-r37-forbidden-package-red` -> FAIL，2 failed，证明旧脚本把 target preflight 证据写入包目录且 ops-runtime 携带 target-bound config/root-disk 脚本。
- GREEN: package-target-bound-content-fix -> PASS，`Invoke-BuildReleaseTargetDataPreflight` 改为写入 `$planRoot\target-data-preflight.json`；`New-ReleaseOpsRuntimePackage` 只创建空 `config` 目录并声明保留目标机 server-side config，不再复制 `script\backup-ops\config` 或 `manage-int-ruoyi-remote-root-disk.ps1`；部署解包只覆盖 linux/scripts/actions 并保留远端 config。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "target_data_preflight_evidence or ops_runtime_package_excludes or deploy_release_uses_manifested_ops_runtime or publish_script_uploads_ops_runtime_package" --basetemp .tmp-r37-forbidden-package-green` -> PASS，3 passed。
- REGRESSION: `python -X utf8 -m pytest -q --tb=short --basetemp .tmp-r37-package-regression scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_workflow_preflight.py` -> PASS，151 passed。
- GREEN: publish-script-ast-r37 -> PASS，`[System.Management.Automation.Language.Parser]::ParseFile(... publish-int-ruoyi.ps1 ...)` 无错误。
- RESULT: r37 判废不复用；其本地包未发布测试服、未切换 `.env`、未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r38`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `c4ba9d3f`，继续禁止 with-data、全量数据库、MinIO 数据同步和正式服写入。

## r38 source freeze

- USER_AUTHORIZATION: 用户继续并明确授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r38 -> PASS，已按 `docs/experience-index.md` 命中 without-data/app-release、目标只读预检、manifest forbidden scan、NAS JSON、PowerShell、测试服发布、server-access、release-backup-restore 与 worktree 门禁；R37 已判废且不得复用，下一轮必须新 tag。
- GREEN: source-freeze-r38-plan -> PASS，维护 worktree 当前 clean `16d15ee01676cd18cdb13d304f31d0689c798859`，应用 worktree当前 clean `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`；本地缓存 `release-20260914-one-button-app-r38` 不存在；backend runtime base tar 与 SHA256 已按配置精确路径校验。实际构建 source freeze 以本段记录提交后的维护仓 clean HEAD 和应用仓 `c4ba9d3f` 为准。
- BDD: manifest v1 校验必须早于 NAS 上传 -> Given build-release 已生成本地 app-release 包和 `manifest.json` / When 准备进入 NAS staging 上传 / Then 必须先执行 ReleaseManifestValidator report-only 硬门禁，失败即阻断，报告写入构建临时 preflight 目录，不得污染不可变包。
- RED: `python -m pytest scripts/tests/test_release_package_governance.py -q` -> FAIL，新增合同发现 `Invoke-ReleaseStage -Name 'release manifest validation'` 缺失，且 helper 位置不满足硬门禁扫描；同轮暴露系统 pytest temp 目录权限问题，后续统一使用任务内 `--basetemp`。
- GREEN: `python -m pytest scripts/tests/test_release_package_governance.py::test_build_release_long_running_package_steps_are_observable scripts/tests/test_release_package_governance.py::test_build_release_manifest_validation_is_hard_gate_before_nas_upload -q --basetemp .tmp-pytest-one-button-manifest-gate` -> PASS，2 tests。
- REGRESSION: `python -m pytest scripts/tests/test_release_workflow_preflight.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_release_package_governance.py -q --basetemp .tmp-pytest-one-button-p1-regression` -> PASS，97 tests。
- IMPLEMENTATION: `publish-int-ruoyi.ps1` 导入 `ReleaseManifestValidator.psm1`，新增 `Invoke-ReleaseManifestValidationGate`，在 `release package integrity verification` 之后、`NAS release package upload and verification` 之前执行；校验报告写入 `build-preflight-<package>/manifest-validation-result.json`。
- NEXT: 提交维护仓 manifest hard gate 后，以新 clean maintenance HEAD 和应用仓 `c4ba9d3f` 继续 R38 build-release；仍禁止 with-data、全量数据库、MinIO 数据同步、正式服/审查服写入、`mark-tested`、`promote-prod` 和 `promote-backup`。

## r38 retired: cleaning process parameter migration must no-op on empty rule baseline

- USER_AUTHORIZATION: 用户继续并明确授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- RED: deploy-release-r38-explicit-host-binding -> FAIL，两次直接脚本调用先后缺少 `-TestServerHost` 和 `-BackupServerHost` 显式参数，脚本在发布目标绑定门禁前失败；未写服务器、未改 NAS、未启动 SQL 或版本切换，因此继续使用同一个尚未部署的 R38 包。
- GREEN: r38-local-package-and-manifest -> PASS，本地 `release-20260914-one-button-app-r38` 完整性和 manifest validation 均通过；`PublishScope=app-release`，`packageDigest=9387c858b542f3899a7162003e0b396fc2816f762c832e93def5271d7060a106`，`manifestDigest=f93bc66c3225c90563e8634ccba2e87cb775b91fb9aa95378ae86a18fdf04475`，source freeze 为维护仓 `19cb6ee89de85e6a7a80160e57c7a73111796315` 与应用仓 `c4ba9d3f78c4c8503c9f175c8bde4bf2fc896a03`，包内无 database/mysql/minio/files/data/dcc-object-inventory/runtime-data 目录。
- RED: deploy-release-r38-cleaning-process-empty-baseline -> FAIL，测试服部署在版本切换前执行 required SQL `20260811_mes_process_pool_cleaning_process_parameter_data.sql` 时失败：`ERROR 1644 (45000) at line 197: No active cleaning process ultrasonic cleaner parameter rules found`；operation lock 已释放为 FAILED。
- ROOT_CAUSE: 测试服真实库 `mes_pro_process_pool_device_parameter_rule` 活跃规则数为 0，该迁移语义是归一化已有清洗工序超声波清洗机参数规则，应在无候选数据时 no-op；旧 target preflight 只检查存在 `清洗工序`，没有覆盖具体候选规则数量、重复归一化冲突和不完整规则组，因此 build-release 前漏检。
- BDD: 清洗工序参数迁移兼容空规则基线 -> Given 标准 without-data/app-release 只携带版本化 SQL / When 目标库没有活跃清洗工序设备参数规则 / Then 迁移 no-op 通过；只有存在候选规则时才硬性校验五个正式参数、重复冲突和不完整分组。
- RED: `python -X utf8 -m pytest -q D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\script\tests\test_mes_process_pool_cleaning_process_parameter_data_sql.py --basetemp D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\.tmp-r38-cleaning-process-red` -> FAIL，2 failed。
- GREEN: app-cleaning-process-empty-baseline-fix -> PASS，应用仓提交 `b286fd47d` 新增 `v_cleaning_rule_candidate_count` 和 target preflight CTE 分组校验；定向 RED/GREEN 2 passed，相邻 `test_release_target_preflight_files.py` / `test_release_preflight_plan.py` 回归共 26 passed。
- GREEN: test-server-readonly-preflight -> PASS，测试服只读执行新版 `target-preflight/20260811_mes_process_pool_cleaning_process_parameter_data.preflight.sql` 返回 `TARGET_PREFLIGHT_PASS:20260811_mes_process_pool_cleaning_process_parameter_data`，诊断查询 `rules_total=0`、`rules_cleaning_process_join=0`。
- RESULT: R38 判废不复用，未切换测试服 `.env`，未执行正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步或全量数据库同步。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r39`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `b286fd47d`。

## r39 source freeze

- USER_AUTHORIZATION: 用户继续并明确授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r39 -> PASS，已复核 `docs/experience-index.md` 命中的 without-data/app-release、目标只读预检、manifest forbidden scan、NAS JSON、PowerShell、测试服发布、server-access、release-backup-restore 与 worktree 门禁；R38 已判废且不得复用，下一轮必须新 tag。
- PLAN: 使用新 releaseTag `release-20260914-one-button-app-r39`，source freeze 固定维护仓 clean HEAD 与应用仓 `b286fd47d07a`；构建和发布均显式传入 `BackendRepoRoot`、`FrontendRepoRoot`、`TestServerHost`、`BackupServerHost`、NAS JSON 和 backend runtime base 参数，继续禁止 with-data、全量数据库、MinIO 数据同步和正式服写入。

## r39 retired: interrupted package cache before manifest

- RED: r39-local-package-integrity -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r39` 已存在，包含 image tar、required-sql、ops-runtime、smoke、manifest 子目录和 evidence，但根目录缺少 `manifest.json`；`Test-ReleasePackageIntegrity` 返回 `manifest.json: missing manifest`。
- RESULT: R39 是重启/中断遗留半成品缓存，不是 READY 包；不得发布测试服，不得复用该 tag，未执行正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步或全量数据库同步。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r40`。

## r40 source freeze

- USER_AUTHORIZATION: 用户继续并明确授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r40 -> PASS，已复核 without-data/app-release、目标只读预检、manifest forbidden scan、NAS JSON、PowerShell、测试服发布、server-access、release-backup-restore 与 worktree 门禁；R39 已判废且不得复用，下一轮必须新 tag。
- PLAN: 使用新 releaseTag `release-20260914-one-button-app-r40`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `b286fd47d07a`；构建和发布均显式传入 `BackendRepoRoot`、`FrontendRepoRoot`、`TestServerHost`、`BackupServerHost`、NAS JSON 和 backend runtime base 参数，并显式传入 `-PublishScope app-release -SkipDatabaseSync -SkipMinioSync`。

## r40 retired: UV curing I source configuration absent on target

- GREEN: build-release-r40 -> PASS，source freeze 为维护仓 `504486f800c6a5442d4794bdda54b79375e7e001`、应用仓 `b286fd47d07ad80ebe3e5810e7ba259e11827bb6`；应用迁移静态测试 6 passed、维护脚本测试 127 passed、PowerShell 摘要 PASS、target-data preflight 26/26、schema-only rehearsal、Maven package、前端 build、Docker build/save、本地 package integrity、manifest validation 和 NAS 原子 READY 均通过；包为 `PublishScope=app-release`，`packageDigest=e9d359fb674ec341835abcf0ec23370dc4bf26091f860da8fc189b36cd0b5d74`，`manifestChecksum=sha256:966e9de0efdc3351d13cb7c97911606d63451a93a97723de184ca114d5d2ed92`，无 database/mysql/minio/files/data/dcc-object-inventory/runtime-data 目录。
- RED: deploy-release-r40-uv1-empty-source -> FAIL，测试服部署在版本切换前执行 required SQL `20260811_mes_process_pool_uv1_metering_valid_parameter.sql` 时失败：`ERROR 1644 (45000) at line 791: Missing enabled A05075 UV curing I source configuration`；release lock 已释放为 FAILED，测试服 `.env` 未切换到 R40。
- ROOT_CAUSE: 测试服真实库存在光固Ⅰ/Ⅱ工序，但启用的 A05075/A05059 来源设备配置和候选参数规则均为 0；UV1/UV2 迁移语义应在无候选来源时 no-op，旧 target preflight 只检查表存在，未把空来源基线和冲突合同前移到 build-release。
- GREEN: app-uv1-uv2-empty-source-fix -> PASS，应用仓提交 `00adc544bcae` 移除 UV1/UV2 “来源配置为 0 即 SIGNAL”的硬阻断，target preflight 改为读取候选数量、目标设备/绑定/规则冲突；定向/回归测试 30 passed，新版 UV1/UV2 target preflight 在测试服均返回 `TARGET_PREFLIGHT_PASS`。
- RESULT: R40 判废不复用，未执行正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步或全量数据库同步。下一轮必须使用新 releaseTag `release-20260914-one-button-app-r41`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `00adc544bcae`。

## r41 source freeze

- USER_AUTHORIZATION: 用户继续并明确授权；范围仍只覆盖测试服/NAS 的 `app-release` build-release -> publish-test 真实链路及只读/运行态验证，不覆盖正式服写入、审查服写入、`mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: experience-preflight-r41 -> PASS，已复核 without-data/app-release、目标只读预检、manifest forbidden scan、NAS JSON、PowerShell、测试服发布、server-access、release-backup-restore 与 worktree 门禁；R40 已判废且不得复用，下一轮必须新 tag。
- PLAN: 使用新 releaseTag `release-20260914-one-button-app-r41`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `00adc544bcae`；构建和发布均显式传入 `BackendRepoRoot`、`FrontendRepoRoot`、`TestServerHost`、`BackupServerHost`、NAS JSON 和 backend runtime base 参数，并显式传入 `-PublishScope app-release -SkipDatabaseSync -SkipMinioSync`。

## r41 retired: interrupted local package cache

- RED: r41-local-package-integrity -> FAIL，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260914-one-button-app-r41` 已存在，但仅包含 `evidence/` 和 `required-sql/`，缺少根目录 `manifest.json`；`Test-ReleasePackageIntegrity -ExpectedReleaseTag release-20260914-one-button-app-r41 -ExpectedPackageDirectoryName release-20260914-one-button-app-r41` 返回 `manifest.json: missing manifest`。
- RESULT: R41 是重启/中断遗留半成品缓存，不是 READY 包；不得发布测试服，不得复用该 tag。未执行正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步或全量数据库同步。
- NEXT: 使用新 releaseTag `release-20260914-one-button-app-r42`，source freeze 固定维护仓本段证据提交后的 clean HEAD 与应用仓 `00adc544bcae`；构建和发布均显式传入 `BackendRepoRoot`、`FrontendRepoRoot`、`TestServerHost`、`BackupServerHost`、NAS JSON、backend runtime base 参数、`-PublishScope app-release -SkipDatabaseSync -SkipMinioSync`。
