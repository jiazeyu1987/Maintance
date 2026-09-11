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

## Phase P1 - 基线与契约收敛

USER_AUTHORIZATION: 用户要求“根据文档进行开发”；本轮授权覆盖本机 P1 实现、测试和任务分支提交，不覆盖真实 E2E、NAS、测试服、正式服、审查服、数据库或 MinIO 写入。

BDD: 验证发布线无损融合 -> Given 当前维护仓与 IntRuoyi 主工作区均含并发脏改动 / When 从各自已提交 `int_main` 创建任务 worktree 并融合 R44 验证线 / Then 原主工作区不变，任务分支可追溯 `8080c0d`、`713c641` 或等价能力，两个 Git root 与三个 source role 均明确。

BDD: 标准程序包固定无数据 -> Given 操作者通过标准 workflow 生成程序安装包 / When 构建合同解析请求 / Then scope 固定为 `app-release`，客户端不能选择 `with-data`，权威制品只接受 `manifest.json`，并拒绝数据库/MinIO/DCC/runtime data/秘密制品。

BDD: 构建前测试与来源门禁 -> Given 任一来源 dirty、摘要向量不一致或后端/前端/脚本测试失败 / When workflow 准备进入 Maven/frontend/Docker 构建 / Then 在昂贵构建前返回明确失败，不产生 NAS 或服务器副作用。

GREEN: experience-preflight-p1 -> PASS，已读取本仓经验索引、按钮化 app-release 门禁、发布/备份恢复规则、PowerShell 规则、IntRuoyi AGENTS、worktree-memory、worktree-restrictions、branch-runtime-ports、task-closeout、后端/前端开发规则与统一前端样式。两个目标 worktree 路径均在允许根内且当前不存在；P1 禁止服务启动、远程访问和 E2E。

ACTION: p1-isolated-worktrees -> 计划从维护仓 `int_main@08823268e9efe7571a06c261a7b919c890c45dad` 创建 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m`，从应用仓 `int_main@860496e330a8b47bcb421b8b65ece03c06df33d8` 创建 `D:\IntRuoyiWorktree\r260911-release-button\a`；两仓任务分支统一为 `codex/one-button-app-release-20260911`。原主工作区只读保留。

DEFERRED: P4/P5 规定 Playwright 1.60.0 运行时缺失；真实测试服/正式服授权缺失。这些不阻塞不启动服务、不运行 E2E、不访问远程环境的 P1。
