# 备份与恢复模块开发契约 v1

状态：接口及写入边界冻结，开始本机代码开发。冻结日期：2026-10-10。

本文件是执行契约；此前全局拆分文档的“仅设计/尚未授予开发”状态是历史状态。用户最新指令已授权以下模块代码开发。本文不授予正式环境、真实 NAS、系统时钟、共享 Docker/WSL/服务、真实数据写入、自动删除、正式切换或外部通知权限。

## 范围与负责人

完整范围引用 `../20261010-backup-restore-global-decomposition/functional-decomposition.json` 中 F01–F12 的 63 个子功能。按用户最新要求，新建七个独立 Codex 工作线程，每个承担一个逻辑模块，不复用原四个线程。主线程只负责契约、派发、集成和整体判断，不实现产品代码、不执行备份恢复。

| 执行组 | 现有线程 | 逻辑模块 | 子功能及开发结果 |
| --- | --- | --- | --- |
| W01 | 新建：备份恢复控制台与调度开发 | W01 | 控制台/API/服务侧调度、操作记录/去重/锁/重启状态、模式分级、候选与结果页面 |
| W02 | 新建：全量增量备份采集开发 | W02 | 全资产/写入者盘点、一致性保护、全量与真实增量、共同恢复点、数据库/对象/配置/镜像材料采集、失败源复原、正常采集入口 |
| W03 | 新建：NAS归档与备份链开发 | W03 | 采集前容量准入、归档发布、完整独立读回、点目录与链、候选分级、保留与清理能力 |
| W04 | 新建：备份整链与数据恢复开发 | W04 | 选点预检、全量/增量整链恢复、数据库/对象执行、受控切换编排及失败保护 |
| W05 | 新建：恢复环境与应用启动开发 | W05 | 目标身份/资源/隔离、版本/配置/秘密引用、应用启动和外部副作用保护 |
| W06 | 新建：恢复独立验证能力开发 | W06 | 数据/对象/引用/真实用户路径验证能力，独立原证据核对与验收报告 |
| W07 | 新建：备份恢复诊断与持续验收开发 | W07 | 操作观察、超时/时钟诊断能力、重启记录、告警证据及周期验收请求 |

W04 是数据恢复开发负责人，W05 是恢复环境开发负责人；W02 是备份采集开发负责人，W03 是持久归档负责人；W01 对用户入口负责。W06 的验证能力先开发，实际独立验收和静态审查在全部产品代码完成后进行。任何线程不得审查自己开发的代码来宣称独立审查通过。

主线程为第一层，七个新独立线程为第二层。第三层目前仅作模块内子功能拆分，完成前不继续创建或通知线程，不使用子 Agent。原四个线程不接收本轮派发，原产物作为明确版本输入复用。

## 写入边界

- W01：主维护仓 `backend/src/`、`backend/pom.xml`、`frontend/src/`、`frontend/package.json`、`frontend/tsconfig.json` 和必要构建配置；禁止修改运行时秘密配置或其他模块源码。
- W02：`D:/IntRuoyiWorktree/three-env-20260927-app/IntRuoyiBackend/script/backup-ops/linux/` 及对应备份测试。作为本轮该目录唯一写入负责人，继承既有未完采集代码，不修改原线程任务状态、其他应用 Java/前端模块或维护仓/NAS 代码。
- W03：`C:/Users/BJB110/.codex/worktrees/instance-snapshot-integration/IntRuoyiMaintance/` 中原 maintenance publisher、backup installer、NAS/backup 测试和 helper；新增 `ops/recovery/repository_cli.py`、`repository_*.py` 和对应测试。禁止写该工作树 backend/frontend 或主维护仓产品文件。
- W04：主维护仓 `ops/recovery/recovery_cli.py`、`recovery_engine*.py`、`recovery_plan*.py`、`recovery_data*.py`、`recovery_cutover*.py`，对应 `scripts/tests/test_recovery_engine*.py`、`test_recovery_plan*.py`、`test_recovery_data*.py`、`test_recovery_cutover*.py`。
- W05：主维护仓 `ops/recovery/environment_cli.py`、`recovery_environment*.py`、`recovery_application*.py`，对应 `scripts/tests/test_recovery_environment*.py`、`test_recovery_application*.py`。
- W06：主维护仓 `scripts/recovery_verification/`、对应 `scripts/tests/test_recovery_verification_*.py`；原 strict checker 和旧线程记录只读。
- W07：主维护仓 `ops/recovery/diagnostics_cli.py`、`recovery_diagnostics*.py`、对应 `scripts/tests/test_recovery_diagnostics*.py`；旧时钟/超时诊断产物只读。
- 各模块只能写自己新建的任务目录。新增共享文件必须由以上文件命名边界唯一归属，不擅自创建多模块同时改的 common.py。
- 主线程：仅本执行任务契约、调度记录和全局状态。最终产品集成由明确获得集成任务的开发线程执行，不能趁开发中复制覆盖。

各线程先核自身既有改动/基线，保留未完成且仍属于自己的工作。其他任务改动不作为通用阻塞或清理对象。禁止提交全脏基线、擅自 commit/push、删除无归属文件。开发阶段不修改 frozen v1 的 12 个原件及已发 v2 原件。

## 已固定的采集与 NAS 接口

继承 `../20261010-backup-cross-thread-interfaces/interface-contract.json`、`schemas.json`、`delivery-manifest-v1.json` 中现有签名和严格字段，及 `owner-task-routing-v2.json`、`control-response-addendum-v2.json` 两个增补。不得回填旧 taskId 或将新交付误标为旧任务。

原 `backup-worker-delivery/v1` 只用于先前四个接口任务。本次完整模块交付采用独立的 `backup-restore-module-delivery/v1`，任务身份见 `execution-contract.json`。两类交付不能混用。

W02 必须真正接通 normal owner、writer admission、NAS consumer 控制状态，处理 owner close 与原进程退出；W03 的采集前准入必须在停写/采集之前，成功不依赖退出后向已死 owner 发消息。计时用单调预算，各主机不比较单调绝对值。源恢复正常运行只表示 sourceRestored，不表示灾难恢复通过。旧 v1 的生产代码接口保持；旧作者 thread/task 身份是历史固定输入，本次新作者身份由 execution-contract 和实际 creation-results 绑定，禁止伪称自己是旧作者。

## 新边界接口：文件请求 + JSON 结果

传输版本 `backup-restore-operation/v1`。文件路径是当前执行主机上的绝对路径；秘密只存引用，不能写进请求日志和公开证据。请求和输出均使用 UTF-8 JSON。时间为 UTC RFC3339。所有枚举大小写严格匹配。业务原件额外必填 schemaVersion，固定为 `<记录名称>/v1`；RepositoryPoint 额外必填 blockedReason:string|null、rehearsalEligible:boolean、controlledRestoreEligible:boolean。八类业务记录类型以 record-schemas.json 的 `$defs` 为机器约束。

Pin 的精确定义为 `{path: string, bytes: integer >= 0, sha256: string matching ^[0-9a-f]{64}$}`；path 必须绝对、原件可读，并独立核 bytes/sha256。不能从作者声明自行取得信任根。列表保持顺序，不静默补默认值。必填 nullable 字段必须出现；只读动作允许相应字段为 null，写动作须核实非 null。

OperationRequest 必填字段：

| 字段 | 类型与含义 |
| --- | --- |
| schemaVersion | 固定 `backup-restore-operation/v1` |
| operationId、requestId | 非空字符串；requestId 为幂等键，同键不同请求内容拒绝 |
| action | `BACKUP_FULL`、`BACKUP_INCREMENTAL`、`LIST_POINTS`、`POINT_DETAIL`、`READBACK_VERIFY`、`RETENTION_PLAN`、`RETENTION_EXECUTE`、`RESTORE_PREFLIGHT`、`PREPARE_TARGET`、`RESTORE_EXECUTE`、`START_APPLICATION`、`VERIFY_RECOVERY`、`REHEARSAL`、`CONTROLLED_CUTOVER`、`OBSERVE_OPERATION`、`DIAGNOSE_EXECUTION`、`PLAN_REHEARSAL` |
| mode | `REHEARSAL` 或 `CONTROLLED_RESTORE` |
| selectedPointPin | Pin 或 null；选点恢复必填有效 Pin |
| sourceOrTargetRef | Pin；绑定源或目标配置原件，配置只含秘密引用 |
| policyPin | Pin；绑定版本/策略/隔离/保留/RTO/RPO 来源；未知必需项明确报错 |
| authorizationRefs | Pin[]；真实写入必须有当前有效、限定动作/目标/窗口的授权，并核其语义，文件存在不等于授权成立 |
| leaseRef | Pin 或 null；写入前必须核有效 lease/唯一执行者 |
| inputPins | object<string, Pin>；约定键见下表，未知键拒绝；缺少所需键立即失败 |
| deadlineMilliseconds | integer > 0；当前进程启动后按单调时钟计时，保留子进程真实退出结果 |

五个固定入口：

1. W03：`<配置的 python executable> <配置的 repository_cli.py> --request <OperationRequest.json> --output <OperationResult.json>`，支持 BACKUP_FULL/BACKUP_INCREMENTAL/LIST_POINTS/POINT_DETAIL/READBACK_VERIFY/RETENTION_PLAN/RETENTION_EXECUTE。W03 调用原 publisher，publisher 调用 W02 固定 owner 接口；W01 不另造一条绕过 NAS 准入的 backup-now 路径。
2. W04：`<配置的 python executable> <配置的 recovery_cli.py> --request <OperationRequest.json> --output <OperationResult.json>`，支持 RESTORE_PREFLIGHT/RESTORE_EXECUTE/REHEARSAL/CONTROLLED_CUTOVER。REHEARSAL 内部按 W05 的 environment_cli 编排准备/启动，共用同一真实 operationId、选点、目标和授权。
3. W05：`<配置的 python executable> <配置的 environment_cli.py> --request <OperationRequest.json> --output <OperationResult.json>`，支持 PREPARE_TARGET/START_APPLICATION。W04 内部和 W01 单动作调度均使用同一入口。
4. W06：`<配置的 python executable> <配置的 scripts/recovery_verification/verify_recovery.py> --request <OperationRequest.json> --output <OperationResult.json>`，支持 VERIFY_RECOVERY，独立读取原件、实际数据库/对象/用户路径证据。
5. W07：`<配置的 python executable> <配置的 diagnostics_cli.py> --request <OperationRequest.json> --output <OperationResult.json>`，支持 OBSERVE_OPERATION/DIAGNOSE_EXECUTION/PLAN_REHEARSAL；只观察和生成当前验收请求，不替 W04/W05 执行恢复、不发送通知、不修改时钟。

输入键：RESTORE_PREFLIGHT 使用 `repositoryPoint`；PREPARE_TARGET 使用 `restorePlan`；RESTORE_EXECUTE 使用 `restorePlan` 和 `recoveryTarget`；START_APPLICATION 使用 `restoreExecutionResult` 和 `recoveryTarget`；VERIFY_RECOVERY 使用 `restorePlan`、`restoreExecutionResult` 和 `applicationStartResult`；REHEARSAL 使用 `repositoryPoint`，W04 顺序生成预检/目标/执行/启动产物；CONTROLLED_CUTOVER 额外必须有当前 `recoveryVerificationReport`，匹配同源同点同目标；POINT_DETAIL/READBACK_VERIFY 使用 selectedPointPin；保留动作使用 policyPin，执行额外有 `retentionPlan`。OBSERVE_OPERATION/DIAGNOSE_EXECUTION 使用 `operationStatus`/`executionEvidence`，PLAN_REHEARSAL 使用 `repositoryPoint` 和当前可选 `recoveryVerificationReport`。备份的 sourceOrTargetRef/policyPin 和旧 v1 意图/准入记录按原真实配置适配，不能接受配置缺失而假成功。

OperationResult 必填字段：schemaVersion=`backup-restore-operation-result/v1`、operationId:string、requestId:string、action:同请求、state:`SUCCEEDED|FAILED_RETAINED|TERMINAL_UNKNOWN`、failureCode:string|null、message:string、data:object|null、originalResultPins:Pin[]、startedAt:string、finishedAt:string、actualExitCode:integer|null。成功 failureCode=null 且有真实结果；失败不能返回默认成功；未知不能假定子进程终止。正常成功 CLI exit=0，确定失败 exit=1，未知 exit=2；actualExitCode 是被调用执行器真实退出结果，与 CLI 分类码分开。输出原子写入；即使失败仍尽可能保留真实证据，不能吞异常。

业务 data 的八种记录由先前 `hierarchical-delivery-plan.json#interfaces` 对应 requiredFields 固定。精确类型如下：所有 `*Pin`、`planPin`、`candidatePin` 是 Pin；所有 `*Pins` 是 Pin[]；`secretRefs`、`authorizationRefs` 是 Pin[]；`payloadRefs` 是 Pin[]；`versionPins`、`imagePins` 是 Pin[]；`plannedWrites` 为 `{resource:string, action:string, targetIdentityPin:Pin}[]`；`targetRef` 为 Pin；`recoveryPoint` 和 `commonRecoveryPoint` 为非空字符串（生产者真实一致性标识，禁止用本机当前时间填充）；`leaseRef` 为 Pin；`supportedVersionPins`、`toolPins` 为 Pin[]；`immutableInputsSha256` 为 64 小写 hex；其余 Id/phase/nextAction 为非空字符串，waitReason:string|null，updatedAt:string。RepositoryPoint.pointType=`FULL|INCREMENTAL`，integrityState=`COMPLETE|INCOMPLETE|CORRUPT`；RestorePlan.mode 与请求枚举相同；执行和启动记录 state 使用结果枚举；验收报告 verdict=`PASSED|FAILED|BLOCKED|UNKNOWN|STALE`；writeProtectionState=`ENFORCED|RELEASED|UNKNOWN`。其他 requiredFields 的具体类型以 accompanying execution-contract.json 为准。

候选分级：完整独立读回/关闭/原 exit 和整链有效可进入 REHEARSAL；CONTROLLED_RESTORE 必须有当前匹配的恢复验收 PASSED 原件。备份 COMPLETE 不等于恢复 PASSED。失效/错源/缺链/损坏/未知原退出均拒绝写入。

## 控制台接口

W01 在现有独立维护服务中增加 `/admin-api/infra/recovery-control`，不得另建产品或只写 dry-run planner。

- `POST /operations`：OperationRequest → ApiResult<OperationStatus>，验证后异步真实调度上述入口，绝不启动真实任务来做本轮开发验收。
- `GET /operations/{operationId}`、`GET /operations`：OperationStatus / OperationStatus[]；GET 列表按最近提交排序。
- `GET /points?mode=REHEARSAL|CONTROLLED_RESTORE`：RepositoryPoint[]，同时提供明确 blockedReason，禁止把不合格点显示可执行。
- `POST /plans`：RESTORE_PREFLIGHT 的 OperationRequest → ApiResult<OperationStatus>。
- `PUT /schedules/{scheduleId}`、`GET /schedules`：配置实际服务侧调度，使用 `{scheduleId:string, enabled:boolean, intervalSeconds:integer>0, requestTemplate:OperationRequest}`；定时请求派生新的 operationId/requestId，重新检查当前权限和锁，服务重启后不重复执行已投递轮次，不使用前端轮询充当自动备份。

OperationStatus 使用已规划字段：operationId、phase、state、originalResultPins、nextAction、waitReason、updatedAt；额外固定 requestId:string、action:请求枚举、failureCode:string|null。state=`QUEUED|RUNNING|SUCCEEDED|FAILED_RETAINED|TERMINAL_UNKNOWN|BLOCKED`；原 executor 异常/重启失联必须明确 UNKNOWN，不能推断为成功。保留已有 `/runtime-control` 用户入口并将备份/恢复动作接到同一实现，避免第二套互相矛盾的状态。

CLI 的脚本、Python、repository 工作树/恢复根、证据根均采用显式服务配置。开发期未装配目标执行文件时报告不可执行，不回退其他 checkout/远程配置；静态接口可以按契约实现消费者，不等待别的线程写代码。最终集成只使用实际交付路径/版本。

## 执行顺序与沟通

用户最新要求高于技能中的 usable 立即消息、普通事件汇总/关键节点协作及旧消息中的 ACK/审查/TDD规则。

1. 本次初始派发一次给全契约。
2. 各线程自主完成所分配的代码开发，适用的编译/语法/关键行为检查在实现后执行；不强制先 RED/先写测试。
3. 代码开发任务完成前，不向主线程、同级或其他线程发送任何消息，不请求 ACK、不发接口可用/进度通知，不处理其他线程的普通辅助请求。普通问题和阻塞记在本线程文件中；必要前提缺失停止依赖动作，继续其他授权工作，最后一次汇总真实已完成/阻塞范围。不得永久等待其他开发线程完成。
4. 完成实现后只交付一次稳定结果与原证据。完成仅表示本模块当前开发任务出口，不能宣称真实 NAS/恢复/发布通过。
5. 主线程核实七个模块代码任务完成后，才派发独立静态审查；审查任务完成后才允许消息回传，随后必要返工同样按任务完成汇报。

开发期间只允许主线程读实际状态，主线程不插入协调消息。平台自身显示进度不是获准发送线程间消息。

## 完成与验证

AC-01：63 子功能均落实唯一负责人，各组逐项标明实际代码位置/已复用能力/缺口。
AC-02：真实采集、准入、归档、独立读回接口接通，增量不是重做全量。
AC-03：隔离恢复可执行完整 SQL/真实增量整链和对象内容，目标身份/空间/版本/外部副作用有严格门禁。
AC-04：恢复应用与用户入口可用，不把源服务复原、schema通过或 dry-run 当恢复通过。
AC-05：控制台/调度执行同一固定接口，权限、去重、锁、重启、失败/未知状态准确。
AC-06：开发后适用本机检查通过，证据绑定实际交付版本；全部代码完成后独立静态审查及必要修复完成。
AC-07：实际 NAS、Linux、隔离目标、真实数据/Playwright验收、RTO/RPO 实测必须另有现实前提及有效窗口；本机代码/静态通过不能宣称这些通过。

模块交付 `backup-restore-module-delivery/v1` 至自己模块任务目录：taskId、moduleGroup、ownerThreadId、contractPin、state=`CODE_COMPLETE|PARTIAL_BLOCKED`、sourcePins:Pin[]、changes:[{path, purpose}]、functionCoverage:[{functionId, state, implementationPaths, reason}]、checks:[{name, evidencePin, actualExitCode, result}]、blockers:[{code, impact, prerequisite, owner}]、runtimeAcceptance:{actualNas:false,linuxNative:false,restore:false,realUserPaths:false}。不靠本文件新增无限文档或测试门禁。

本轮集成目标是维护仓与原应用工作树中的可审查本机代码；无默认提交/推送/部署/清理。整体状态保持开发中，直到各组实现、后置审查及适用验收有真实证据；不能把派发完成记为功能完成。
