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
