# Release Build Preflight and Cache Optimization PRD

- Task ID: `release-preflight-cache-optimization-20260908`
- Created: `2026-09-08T11:13:31+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-cache-optimization-20260908\m`
- User Request: `实现构建前发布资格预检与可验证 Docker 构建缓存，减少测试服晚失败和重复全量打包，不执行真实发布。`

## Goal

把测试服迁移兼容性判断前移到昂贵构建之前，并让重复构建安全使用 Docker 原生内容寻址缓存。每次 `build-release` 都必须重新读取测试服只读迁移状态，使用本次源码与已暂存 required SQL 生成目标绑定的预检证据；任何阻断、证据漂移或输入无法验证都必须在 Maven、前端构建和 Docker build 之前失败。Docker 缓存命中不能改变最终发布包、镜像和 P0 完整性校验语义。

## BDD Scenarios

### BDD-1: Block incompatible build before expensive work

- Given: 本次源码与 required SQL 已完成静态门禁和暂存，测试服迁移台账与其中一项依赖或校验和不兼容。
- When: 操作者执行 `build-release`。
- Then: 流程重新采集测试服只读 target-state，运行既有 `release_preflight_plan.py`，写出状态为 blocked 的本次外部证据并立即失败；Maven、前端构建和 Docker build 均不执行。

### BDD-2: Bind a passing preflight to the exact build inputs

- Given: 测试服迁移台账允许本次迁移计划。
- When: 构建前预检通过。
- Then: 外部证据固定绑定源码提交集合、required SQL 内容、prospective manifest、target-state、`environment=test` 与 publish scope；缺字段、旧证据、路径不安全或任一输入漂移都不能获得构建资格。

### BDD-3: Recollect target state on every build

- Given: 相同 release tag 或相同源码再次执行 `build-release`，本地存在旧预检证据。
- When: 新一轮构建开始。
- Then: 流程覆盖式生成新的采集标识与 target-state 摘要，不读取旧证据作为成功依据；SSH/query/parse 失败均停止，不切换数据源。

### BDD-4: Reuse native Docker cache only for identical inputs

- Given: Dockerfile、最小构建上下文、基础镜像 digest 和全部 build args 与前次一致。
- When: 再次构建应用镜像。
- Then: 命令不再使用 `--no-cache`，由 Docker/BuildKit 原生内容寻址缓存决定命中，并记录可复算的输入指纹。

### BDD-5: Invalidate cache qualification on any material drift

- Given: Dockerfile、上下文文件、基础镜像 digest 或 build arg 任一发生变化。
- When: 计算构建输入并准备 Docker build。
- Then: 输入指纹必然变化；缺失、无法规范化或前后不一致时构建失败，不沿用旧资格。

### BDD-6: Preserve immutable package guarantees

- Given: 构建前预检与 Docker 缓存均通过。
- When: 生成最终安装包。
- Then: 最终 manifest 仍准确声明本次镜像和构建输入证据，P0 逐文件 SHA-256、package digest 与 NAS 入库校验继续执行；外部预检原始 target-state 不携带凭据且不成为可跨构建复用的放行文件。

## Scope

- `ops/deploy/publish-int-ruoyi.ps1` 中 `build-release` 的预检调用顺序、prospective manifest、只读测试服 target-state 采集、外部 evidence 生成与 Docker build 参数。
- `ops/release/release_preflight_plan.py` 的输入校验和确定性摘要/证据字段；必要时新增 `ops/release/lib/` 下可独立测试的 PowerShell 模块。
- `scripts/tests/` 中针对预检证据、失败顺序、缓存输入指纹、Docker 命令和最终包完整性回归的本地合同测试。
- `docs/` 中面向维护者的构建前置条件和证据说明，仅在实现改变操作契约时更新。

## Non-Goals

- 不执行真实远程连接、Docker build、安装包生成、NAS 写入、测试服/正式服发布、数据库修改、服务重启或浏览器 E2E。
- 不修改 `frontend/`，不恢复或覆盖该目录中的并发删除状态。
- 不改变 P0 的不可变包、逐文件哈希、`packageDigest`、`tested.json v2`、测试服到正式服/备份服同包晋级规则。
- 不建立自定义缓存服务器、手写缓存索引、缓存归档或缓存回退分支；本阶段只使用 Docker/BuildKit 原生内容寻址缓存。
- 不把正式服作为 build 预检目标，不读取或写入正式服。
- 不用固定成功文件、旧 evidence、空 target-state、替代数据源或跳过命令掩盖前置失败。

## Preconditions

- 本任务只在指定 worktree 和分支中修改；发现不明来源重叠改动立即停止并交由主 Agent 记录。
- Windows PowerShell 5.1、Python 3.12、pytest、Git、Node.js、JDK 17 和 Maven 3.9 可用；JDK 17 固定为 `C:\Users\BJB110\.jdks\jdk-17.0.20+8`。
- 现有 `ops/release/release_preflight_plan.py`、required SQL manifest 构造、迁移策略门禁和 P0 `ReleasePackageGovernance.psm1` 均可读取。
- 生产代码变更前，`execution-log.md` 必须记录 BDD 和预期失败的 RED 命令；实现遵循 `RED -> GREEN -> REGRESSION`。
- 测试仅使用 `$env:TEMP\release-preflight-cache-optimization-20260908` 下无凭据 fixture；需要真实服务器、Docker daemon 或远程凭据才可通过的设计视为阻断。

## Impacted Areas

- 构建顺序：required SQL staging 之后、Maven/前端/Docker 之前新增强制 target-bound preflight。
- 迁移规划：复用现有 Python planner，不复制第二套迁移决策逻辑。
- Evidence contract：外部证据包含 schema version、采集 ID/UTC 时间、source fingerprint、SQL/manifest digest、target-state digest、target environment、publish scope、planner status 和 items digest。
- Docker build：移除应用镜像的 `--no-cache`，将 Dockerfile、规范化上下文、基础镜像 digest 和 build args 纳入确定性输入指纹。
- Package manifest：记录构建输入指纹及实际镜像身份，同时继续由 P0 完整性治理生成和校验最终包摘要。
- 调用方合同：维护控制台参数不增加弱校验开关，不改变 deploy/mark/promote 用户流程。

## Phase Plan

### P1: Early Target-Bound Build Preflight

- Objective: 在任何昂贵构建前，以本次源码和 staged SQL 对测试服真实只读迁移台账执行一次不可复用的发布资格判断。
- Owned paths: `ops/deploy/publish-int-ruoyi.ps1`, `ops/release/release_preflight_plan.py`, optional focused module under `ops/release/lib/`, focused tests under `scripts/tests/`, relevant operator documentation.
- Dependencies: P0 package governance; required SQL discovery/policy/staging; configured test server host; SSH; readable test migration ledger; Python 3.12.
- Deliverables: prospective manifest contract, fresh target-state collector, deterministic external build-preflight evidence, blocked-status fail-fast gate, call-order tests.

### P2: Verifiable Native Docker Cache

- Objective: 允许 Docker/BuildKit 根据内容复用应用镜像层，同时使缓存资格输入可复算、可失效并与最终安装包证据绑定。
- Owned paths: `ops/deploy/publish-int-ruoyi.ps1`, optional focused module under `ops/release/lib/`, focused tests under `scripts/tests/`, final manifest build metadata and relevant operator documentation.
- Dependencies: P1 completed; existing minimal Docker build context; verified backend base tar/image digest contract; P0 final package integrity checks.
- Deliverables: deterministic backend/frontend build-input fingerprint, validated Docker command arguments without `--no-cache`, before/after input consistency gate, manifest evidence, package-governance regressions.

## Phase Acceptance Criteria

### P1

- P1-AC1: `build-release` 在 required SQL staging 完成后、首次 Maven、frontend build 或 Docker build 之前构造仅含本次迁移决策所需字段的 prospective manifest，并使用测试服只读迁移台账调用现有 planner。
- P1-AC2: 每次 `build-release` 都发起新的 target-state 采集；本地旧 evidence 不参与本次通过判定，采集命令失败、空输出、非法 JSON、缺少台账或 planner 异常均立即失败。
- P1-AC3: 外部 evidence 使用稳定 schema，至少绑定 source commits/fingerprint、staged required SQL digest、prospective manifest digest、target-state digest、`targetEnvironment=test`、publish scope、采集 ID/UTC 时间和 planner items/status digest，且不记录密码、token、连接串或原始 `.env`。
- P1-AC4: evidence 中 `status=blocked`、任一 `BLOCKED_*` action、缺少必需绑定字段或重新计算摘要不一致时，脚本在昂贵构建前失败；只接受 planner 明确定义的 passed actions。
- P1-AC5: 相同规范输入产生相同绑定摘要；源码、SQL、target-state、environment 或 publish scope 任一变化会改变对应摘要或导致验证失败。
- Evidence expectation: `execution-log.md` 记录 BDD、RED/GREEN 命令、修改路径及本地 fixture 结果；独立 tester 在 `test-report.md` 记录 T1-T5 结果。

### P2

- P2-AC1: backend 和 frontend 应用镜像 build 命令不含 `--no-cache`，不增加弱校验开关，由 Docker/BuildKit 原生内容寻址机制处理缓存命中。
- P2-AC2: backend 输入指纹覆盖 Dockerfile 字节、规范相对路径排序后的最小 context 文件内容、固定基础镜像 digest 和全部 build args；frontend 输入指纹覆盖其 Dockerfile、最小 context 和全部 build args。
- P2-AC3: 任一必需输入缺失、路径逃逸、重复/大小写冲突、基础镜像 digest 非法，或 Docker build 前后重新计算的指纹不一致时立即失败；不得执行后续 docker save 或包入库。
- P2-AC4: 最终 `manifest.json` 或等价不可变构建元数据记录各镜像的 input fingerprint、Dockerfile digest、context digest、base digest/build args digest 与实际镜像 ID/digest，使测试者可从本次文件复算。
- P2-AC5: 使用缓存后仍执行实际镜像检查、docker save、最终 release manifest 逐文件 SHA-256、package digest 和 NAS copy 后复验；缓存不得成为跳过 P0 门禁的条件。
- Evidence expectation: `execution-log.md` 记录 TDD 和真实 PowerShell/Python 合同测试结果；独立 tester 在 `test-report.md` 记录 T6-T10 及全量回归结果。

## Done Definition

- P1、P2 及 P1-AC1 至 P2-AC5 全部完成，并在 `execution-log.md` 或 `test-report.md` 中有对应证据。
- PowerShell AST、focused pytest、全量 pytest、JDK 17 Maven tests、Node tests 和不依赖缺失 frontend 文件的发布合同验证全部通过。
- 独立 tester 采用 blind-first-pass，在真实 PowerShell/Python/JDK 17/Node runtime 上验证，最终 verdict 为 PASS。
- 没有执行远端连接、Docker build、发布、数据库写入、NAS 写入或正式服操作。
- 实现提交只包含本任务文件；最终任务状态和 closeout 由主 Agent 按项目规则处理。

## Blocking Conditions

- 无法在 required SQL staging 后且首次 Maven/frontend/Docker 构建前插入预检，或预检需要先生成昂贵产物。
- 测试服 host/SSH/迁移台账缺失或只读查询失败；不得以空状态、旧文件或其他环境替代。
- prospective manifest 与最终 manifest 的迁移语义无法由同一构造逻辑保证一致。
- 缓存输入无法覆盖 Dockerfile、完整最小 context、基础镜像 digest 和 build args，或构建期间输入可漂移而无法检测。
- 修改需要触碰 `frontend/` 并与并发删除冲突。
- 任一必需测试工具缺失、测试失败、发现凭据写入 evidence 或需要回退/降级路径。
