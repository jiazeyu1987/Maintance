# 两入口发布开发交付 PRD

- Task ID: `20260924-two-button-release-delivery`
- Created: `2026-09-24T10:49:16+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- User Request: 保留 build-release、publish-test、mark-tested、promote-prod 内部阶段和执行器，页面仅提供“发布到测试服”“晋级正式服”；测试发布一次提交后后台持续推进，晋级收集真实验收/恢复候选并复用既有安全合同。

## Goal

一次点击测试发布意图后，后端持久化源、目标和操作身份，冻结三角色源，准备隔离 worktree/依赖，完成构建、校验、测试部署及运行态验证；READY 是内部检查点，关页/重启不影响推进。正式晋级必须在弹窗提交真实验收和有效恢复候选，复用 preview、grant、stateVersion、幂等和同一不可变包。锁、未知写入、目标/摘要漂移和证据失效必须阻断。

## Scope

- `E:\IntRuoyi\IntRuoyiBackend` ReleaseWorkflow/RuntimeControl 编排、Record/Store/Service、RecoveryScheduler、API 和测试。
- `E:\IntRuoyi\IntRuoyiFronted` runtime-control 两入口、进度/失败反馈、晋级验收对话框、API 类型和 UI 测试。
- 维护仓 `ops/deploy/publish-int-ruoyi.ps1`、`ops/release` 锁/lease/fence 及真实生成 SQL 测试。
- 三角色源冻结、专用发布 worktree、提交/执行器 SHA/双摘要/manifest 绑定、同包晋级和失败证据。

## Non-Goals

- 不删除内部四阶段、不另建部署平台、不把阶段串联交给浏览器。
- 不修改冻结 R22 worktree，不直接复用旧 R22 GO，不丢失 int_main 的其他提交。
- 不默认 PASS、不吞异常、不手工清锁/补状态、不正式重构建已测试包、不复制业务数据、不扩大到备份服。

## Preconditions

- 主代理完成只读基线调查；R22 参照 app=`b15b52e0c4c14ed46ebe0772ba4aea2caa8df090`、maintenance=`2a867b91c9add6ec681831e927b347d2e7b088bf`；已确认维护锁修复提交 `0e5d785added60ed742455c37efe3612fcf60ba3` 应选择性合入当前 main，并用真实 SQL 验证。
- 当前 main 与 R22 的 app 10 个、maintenance 8 个发布/迁移相关提交需逐项归属后选择性合入，保留 main 其他提交；冻结 worktree 只读。
- 隔离 MySQL 能执行生产代码生成的锁 SQL，覆盖首次、旧 APPLIED/FAILED、同 tag 旧 lease、活动他人锁、失权 fence 和并发；缺失只阻断锁/真实发布阶段。
- 后端 Maven、维护仓 Python/pytest、前端 pnpm 和 Playwright 1.60.0 可用；真实写入仅测试租户 `aoteman`，不改芋道源码租户。
- 新独立 GO 前不做远程发布；真实正式发布还需批准源、恢复候选、NAS、镜像工具、目标 preflight 和环境访问。凭据不入文档。

## Impacted Areas

ReleaseWorkflow Orchestrator/Service/Store/Record/Scheduler/controller/API；`runtime-control/index.vue` 及验收/授权组件；`publish-int-ruoyi.ps1`、lock/fence/lease；现有 ReleaseWorkflow 与 lock/preflight 测试；Playwright 真实路径和任务证据。

## Phase Plan

### P1: 基线隔离与锁/状态证据

- Objective: 选择性合入已审核发布提交；用生产生成 SQL 复现/验证锁顺序；验证 Orchestrator dispatched、Service verifyAdvance retryable、reconcile 终态和 RuntimeControl 先 save/guard 边界，区分明确 zero-write blocked 与执行后未知。
- Owned paths: 应用/维护独立 worktree、锁代码与后端状态测试。
- Dependencies: 主代理只读调查、隔离 MySQL、`0e5d785...`。
- Deliverables: 差异归属、真实 RED/GREEN、未知态合同和持久目标缺口清单。

### P2: 持久目标与后台自动推进

- Objective: 持久化测试发布目标、源冻结和阶段意图；READY 自动 publish-test；关页/重启/并发不重复派发，历史 READY/FAILED 不接管。
- Owned paths: ReleaseWorkflow Record/Store/Service/Orchestrator/Scheduler/API 与测试；维护仓固定 publish-int-ruoyi.ps1 的受控源准备/清理模式、ops/release 准备模块与对应测试。
- Dependencies: P1 状态合同。
- Deliverables: stateVersion/CAS/lease/operation 证据、防重和未知写入阻断。

### P3: 两入口前端与晋级门禁

- Objective: 顶层只显示两个入口；测试验收/恢复候选进入晋级弹窗，复用 preview/grant/stateVersion/同包晋级。
- Owned paths: 前端 runtime-control、API 类型、组件测试。
- Dependencies: P2 API 合同、IntPP 样式。
- Deliverables: 一次测试发布提交、阶段反馈、真实错误、取消/过期/漂移阻断。

### P4: 集成故障回归与独立验证

- Objective: 覆盖锁占用/失权、双击/双推进者、关页、重启、派发临界、摘要/证据/授权过期、迁移失败；blind-first-pass tester 独立验证。
- Owned paths: 集成/Playwright 测试和 test-report。
- Dependencies: P1–P3、真实运行时。
- Deliverables: 每个 AC 的可复核证据，tester 不改代码。

### P5: 新 GO 后真实双按钮闭环与收尾

- Objective: 新批准提交、新 worktree/new tag；页面一次发布测试服，再用同包晋级正式服并完成运行态核验。
- Owned paths: 本任务发布 worktree、脱敏运行证据和 closeout。
- Dependencies: P4 通过、独立 GO、服务器/恢复/镜像前提。
- Deliverables: operation SUCCESS、manifest、远端 IMAGE_TAG、实际镜像 tag、health UP、HTTP 200、业务页面和清理记录。

## P2 内部交接合同（主审确定）

- 新顶层 API 为创建测试发布意图，字段仅 reason/sourceSelectionId/idempotencyKey；服务器生成 workflow/tag 并固定目标。既有内部四阶段能力保留。请求键绑定操作者和规范化载荷/批准源；同键同载荷回读，异载荷拒绝；新键可在旧任务终结后有意再次发布，不能永久按原因去重。并发活动冲突显式返回已有任务身份，不重复派发。
- 固定已安装且 SHA 校验通过的维护执行器作为控制平面。新增内部 action/mode `prepare-release-inputs` 与 `cleanup-release-inputs`，客户端不能传路径或命令。实际只有 maintenance/application 两个 Git 根，backend/frontend 是 application 下的两个角色，不得改成三仓或三次 checkout。
- 准备模式参数由后端生成：ReleaseWorkflowId、ReleaseWorktreeRoot、SourceMaintenanceRepoRoot、SourceApplicationRepoRoot、PreparationStateDir，以及既有 ExpectedMaintenanceCommit/ExpectedApplicationCommit/ExpectedFrontendCommit/SourceSelectionId。application/frontend 提交必须一致。目录固定为 ReleaseWorktreeRoot/workflowId/maintenance 与 application；PreparationStateDir 固定在服务端 state-dir/release-workflows/source-inputs/workflowId。
- 准备程序按已批准 Git 对象创建全新专用输入，固定 core.autocrlf=false/core.eol=lf，绝不执行脏主工作区脚本。Git源仓允许有未提交开发内容或HEAD已前进，但批准commit对象必须存在；这些开发内容不得进入新输入。安装执行器与新冻结输入的完整性必须单独验证，不能把源仓当前HEAD误当批准版本。复用 scripts/prepare-frontend-dependencies.ps1；缺少正式依赖或安装失败明确阻断。纯构建输入不启动服务、不占用主工作区端口；若既有 guard 需要注册，必须调用正式登记工具，不能猜端口或绕过。
- PreparationStateDir 保留 ownership.json、prepared.json、cleanup.json。prepared.json 最小合同：schemaVersion=1、workflowId、sourceSelectionId、maintenanceCommit/applicationCommit/frontendCommit、maintenanceRoot/applicationRoot、publishScriptSha256、frontendLockSha256、dependencyStampSha256、status=PREPARED；后端严格校验身份、批准源、受控路径和摘要。依赖 stamp 为 node_modules/.release-dependencies.json。避免重复保存已有 actor/提交字段，Record 可使用小型 prepared-input 引用/摘要对象。
- 本轮 build 只能在准备后的 maintenance/application 输入上运行；源冻结与打包再次校验。包封存并验证双摘要后，由受控后台清理本轮构建输入，再推进测试部署；publish-test/promote-prod 使用已安装且绑定批准指纹的执行器和同一不可变包，不依赖已删除的构建目录。cleanup入口额外接收服务端已保存的ExpectedPreparationDigest（64位SHA-256），持锁后先验证prepared.json未漂移再删除；cleanup.json绑定该摘要及每个资源删除事实。未知归属、HEAD/dirty漂移、未确认进程终止或路径越界不得强删。
- 复用 scheduler，只有持久目标为测试发布的新任务可从准备到构建、内部 READY/清理检查点、测试部署自动推进。准备、构建、清理和部署各有持久 operation 身份；先保存意图再派发。OS 文件锁/CAS 保证跨实例竞争安全，不能仅依赖 synchronized 或内存 Map。
- 关闭页面、重复请求、重启只根据真实持久证据续接；确认未派发可继续，已派发未知保留 P1 隔离，不盲重放。准备重入仅复核同一 workflow 自有资源，不能接管既有目录；历史目标缺失的 READY/FAILED 不自动推进。准备/清理仅写本机任务拥有的路径，开发验证不触发服务器发布。

## Phase Acceptance Criteria

### P1

- P1-AC1: app 10、maintenance 8 个差异逐项归属；当前 main 选择性保留必要已审核提交，`0e5d785...` 父提交关系可追踪，冻结 worktree 未修改。
- P1-AC2: 生产生成锁 SQL 在隔离 MySQL 证明新 operation 不继承旧 lease；活动锁拒绝、失权零业务写入、终态一致。
- P1-AC3: 行为测试证明 dispatched 仅凭返回值不能判零写入；`verifyAdvance` retryable 不绕过 zeroWriteEvidence；reconcile 区分 preflight 明确 blocked 与执行后未知；save/guard/submit 边界可观察。
- P1-AC4: P1 形成持久 target 缺口、四阶段不变量和新 GO/远程门禁；无 fallback/mock/静默降级。

### P2

- P2-AC1: 一次请求持久化唯一 workflow/operation、批准源、目标、幂等身份，并由受控代码自动创建本轮专用隔离 worktree、依赖准备和清理事实，客户端不提供路径或命令。
- P2-AC2: 后台 `build-release → READY → publish-test` 自动至 TEST_DEPLOYED，关页/重启可续接。
- P2-AC3: 并发/重试只产生一个有效阶段 operation；不重复构建、迁移或部署。
- P2-AC4: 历史 READY/FAILED 不自动部署；部分/未知写入隔离并保留实际证据。

### P3

- P3-AC1: 顶层只有“发布到测试服”“晋级正式服”，按钮提交意图并展示阶段/错误。
- P3-AC2: 缺真实结论、恢复候选或证据过期时不形成 TESTED/grant/正式 operation。
- P3-AC3: 已 TESTED 复用 preview/grant/stateVersion 和同一包，禁止正式重构建。
- P3-AC4: 取消、过期、stateVersion/目标/提交/执行器 SHA/摘要漂移均阻断并可见。
- P3-AC5: 请求失败真实暴露，不空 catch、静默 toast 或默认 PASS。

### P4

- P4-AC1: 新代码通过独立预发布门禁；tester 首轮只读 PRD/test-plan，使用 real-browser/playwright，隐藏 execution-log/task-state。
- P4-AC2: 故障矩阵覆盖双击、并发、关页、重启、临界中断、锁失权、迁移失败、摘要/证据/授权失效。
- P4-AC3: 浏览器通过用例均有截图/trace/HAR 等现存证据；只写测试租户。
- P4-AC4: 独立报告逐项覆盖 AC；缺前提记录 BLOCKER，不以 mock/旧 GO/单 HTTP 200 通过。

### P5

- P5-AC1: 新 GO 后干净 worktree/new tag 构建；测试/正式使用同一 package/manifest/digest。
- P5-AC2: 真实登录点击测试发布一次，关闭/刷新仍完成，测试服版本说明、健康和业务页通过。
- P5-AC3: 晋级弹窗真实验收/恢复候选后正式运行态同时满足 operation SUCCESS、manifest、远端 `.env IMAGE_TAG`、实际镜像 tag、backend UP、frontend HTTP 200 和页面结果。
- P5-AC4: 发布只由按钮触发，接口仅最终只读核验；无 GO/前提不足不远程发布；closeout 后才 completed。

## Done Definition

P1–P5、全部 AC、后端/维护/前端/Playwright/独立验证通过；新 GO 和同包真实闭环证据齐全；任务先 `ready_for_closeout`，清理/合并验证后 `completed`。

## Blocking Conditions

差异或锁归属不清、真实 SQL/隔离库缺失、持久 target/zero-write/未知态无法证明、证据/摘要/授权/恢复候选失效、无新 GO、正式环境未授权、凭据泄露、mock/手写 SQL/手工补绿/重复构建/旧 tag 拼接。
