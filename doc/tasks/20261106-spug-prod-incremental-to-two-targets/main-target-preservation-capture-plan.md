# MAIN 目标保留第一阶段：FULL 采集与连续停写接口

## 本阶段 FULL 子进程可达审计（2026-11-10）

实际 FULL 采集路径仅含以下新增生命周期接缝：PrivateDockerMySql.query/dump、SchemaMySql.schema_query、DataMySql.data_query_to_file、bounded_reference_query、共享 image save、SemanticCapture.verify_endpoint 的 Docker/IP 只读观测、minimal_redis_snapshot.source_client 的 Docker inspect。已有 native.command/docker/mysql_query 的控制动作继续由原 ctx 记录，不重复建立 transport。binlog_container 及 binlog Popen 仅 INCREMENTAL 可达，不纳本次 FULL；独立旧 producer barrier/stopper、PrivateDockerMySql.ready/probe 也不是共享 FULL 调用路径，不为非必要只读账本扩范围。

两份 DataMySql 均是正式输入：严格源码 worker 按同目录优先加载 `ops/recovery/formal_data_evidence.py`；显式轻量映射和 SAFE 构造覆盖用 `ops/backup_engine/formal/formal_data_evidence.py`。本次只同步同一个方法的 observer 接缝，不更改 mapping/standard_fixes、不通过测试换导入遮掩。默认 None 均保持原算法。

新增 query3 与 observation6 的 Given/When/Then：真实本地 Python 客户端、有限外部 Docker/IP/Redis 协议；默认路径解析与版本/身份门禁保持；显式 observer 必须在 Popen 前 before，启动和已知收割才对应 started/finished；准入拒绝零子进程。它们是组件协议测试，不是实际数据库或业务恢复。

## Current Status

ready_for_closeout（第一阶段本机实现与必要回归冻结，待父限定提交）。真实MAIN/原FULL/退出竞争12项PASS；相关211计划节点由r8非archive194与r9实际SAFE archive17分轮闭合，原失败保留。当前不接覆盖执行、目标登记或handoff；三个SAFE候选成员及实际封包仍HARD HOLD。完整raw SHA见target-preservation-2a-freeze-r1.json。

## 目标、里程碑与预期验证

复用现有 FULL 数据算法，在同进程真实 flock、原 MAIN ctx/ProtectionCustody 下完成目标当前数据采集，明确 MinIO 为一致性复查启动存储时如何保持全部 writer 屏障；普通 FULL 原来源恢复语义保持。本组件仅本机限定实现，不访问远端/Docker/浏览器，不安装、构建、清理或提交。真实Linux隔离测试统一由父执行。

1. 只读核 FULL 的阶段、MinIO 复查和恢复路径，及现有 fence/scheduler/ctx 合同。
2. 固定最小模块/API、状态与证据、原普通路径不变条件及后续集成顺序。
3. 写可执行的真实 Linux 文件/flock/ctx/custody BDD/RED 计划，区分有限协议 seam 与现场验收；交父审。
4. 父批准后按实际RED实施限定共享材料/typed session/observer接缝；当前候选冻结，独立Linux49材料接缝及普通FULL成功/失败恢复已通过。
5. 完成MAIN全材料正向、失败保留、实际dump退出竞争以及相关旧回归；当前仍在验证，不能提前判完成。
6. 记录SAFE成员/完整语义与后续保留归档proof的HARD HOLD；不激活覆盖、不做现场接线。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。不能用 skip_stop/skip_restore、伪造 sourceRestored 或放宽 READY。
- 是否从根因和长期维护角度解决：是。只提取既有 FULL 核心和明确 typed 生命周期，不复制第二套 SQL/MinIO/Redis 算法，不建新源控制服务。
- 是否存在临时补丁或绕过：否。原操作、配置、代次、保护和既有原件均不改。

## 经验门禁

- Trigger：MAIN 目标 FULL 保留采集、MinIO 停启和原保护托管。
- Preflight check：按经验索引命中的原 MAIN 语义健康、已启动存储续办、事件 scheduler、发布端口/存储、归档 RO 和覆盖前完整读回门禁，核同一 UUID/挂载/配置、全部 writer 与真实物理锁。
- Blocker：任何 writer 未覆盖、存储启动前 fence 未核、同锁/ctx/保护摘要不符、终态未知或完整材料未核。
- Verification：后续真实 Linux 同 PID/flock/原件场景及实际双包合同，不将协议 seam 称现场成功；普通 FULL 恢复服务证据不变。
- Forbidden action：不改另一子代理拥有的 repository_records.py、repository_minimal.py、standard_fixes.py、planner/app.js；不重派376，不执行远端或业务操作。
- Evidence：父批准分派、前一评估、下列只读源码定位和阶段接口。

## 只读事实与必须处理的接缝

1. 严格来源采集器 `ops/recovery/minimal_capture_worker.py:311` 的 `capture_locked` 混合材料准备、停 writer、设置 MySQL `1/1`、数据算法和来源恢复。其 `386–446` 已有真正的语义导出、FULL 前后数据库内容比较、SQL gzip、MinIO 离线物理树、重启后的全版本对象复查、位置复查、Redis 复核和归档输入。应提取这些原调用，不能复制数据算法。`452–460` 的普通来源恢复和 `sourceRestorationPin` 必须继续属于原 FULL/INCREMENTAL 来源生命周期。
2. MinIO 不能一直保持停止：严格路径先在在线状态做语义 S3 导出，离线采集物理树，再启动原 MinIO、`wait_ready`、`verify_objects_after_offline`。后者不只读列表：核 endpoint、双次完整 versions/delete markers 列表、空 multipart、逐对象内容摘要/大小/可恢复 headers。严格 `MinimalSemantic.finalize` 还调用 Redis `verify_current`，不可提前结束保护。本轮只读核实际 45 标准包确认，标准 `SemanticCapture.capture` 另含 replica dependency、multipart、endpoint 和引用完整性证明；`finalize` 写 `complete=True`。
3. 源码 `ops/backup_engine/formal/` 是 lightweight 构造输入。其 `Runtime.protected`、对象复查、`SemanticCapture.finalize(complete=False)` 与实际标准包不同。不能简单将该目录当前版本称为 SAFE 采集核心。第一阶段以现有严格来源路径的真实调用为提取基准；父负责与标准构造 owner 协调精确双包输入。普通 lightweight FULL 的既有合同也不得被顺手改写。
4. MAIN 原调用在 `recovery_program_restore.py:214` 已 `begin_restore`，其后用同一实际 lock fd、`MainNativeExecutionContext` 和 `ProtectionCustody`。`recovery_replace.quiesce:202` 安装原 archive/fence，停应用及 MinIO，随后安装原 scheduler。新增保留采集应在这次 quiesce 之后、镜像 load/switch 以及任何 DROP/对象清理/Redis reset 之前运行；不能另起 `minimal_capture_worker.py` 子进程占用第二把锁。
5. `recovery_mysql_scheduler.py:24` 的 `_state()` 明确要求 UUID 和 `read_only/super_read_only=0/0`，而严格 FULL 的 `Runtime.protected:208` 要求 `1/1`。直接用原 scheduler.verify 包围 FULL 会失败；把 `_state` 放宽为两种任意状态则破坏原合同。必须增加只由同一 typed custody 持有的采集 fence 租约，而不是跳过 scheduler 校验。另 `mysqldump --single-transaction` 自身有读事务，不能让采集 guard 始终要求 innodb_trx=0；已有 `formal_snapshot_linux.observe_database_barrier:214` 明确区别真实导出期与严格前后0，应复用其规则。
6. 原 `ProtectionCustody` 严格绑定原 target/source/request/ctx/budget、三个保护摘要、私密输入和原 journal。它只向执行 transport 授权具体保护方法，不是通用旧 native 命令入口。采集不能重建三 factory 或给旧 PREPARATION native 特赦 `bound()`；PREPARATION 应复用 `application_runtime_inputs` 核当前旧程序，RESTORE 的 archive/runtime 全等校验保持。
7. `PublishedHostWriteFence/v1` 核原整套 iptables 状态并拦登记发布端口，但允许登记 writer IP，且不等同 Docker 网络或 host-root 沙箱。因此必须同时持续核全部登记 writer 停止、原网络成员/固定 IP/挂载/镜像、独占存储及数据库范围、Redis 客户端和未登记 RW 共享者。只读 S3 client 不等于吊销其他写凭据。
8. 当前 `Budget` 有两个类型：MAIN 的 `recovery_engine.Budget` 是 ctx 同一对象；capture 输出 Budget 有累计写入/空间限制和自己的新 deadline。新接缝必须继承 MAIN 原绝对截止，并保留 capture 累计输出限制，不能重新开始 `workSeconds`、替换 native.budget 或把剩余恢复预算挪给保留。

以上是代码和原包的只读事实，不是对当前三服环境的重新认证。目标 .58 的冻结 policy 中 `captureConfigurationPins={}` 仍是正式接线前置缺口；此设计不补造登记、不把旧 .57 包当当前 .58 保留点。

## 最小第一阶段边界

第一阶段只交付可复用的材料核心和 typed 连续停写生命周期，使用真实本机文件/flock/ctx/custody 测试闭合。不得仅因该组件完成就在 MAIN 开启覆盖入口。后续父完成“完整归档落盘、全量独立读回、保留角色与本次覆盖绑定、容量和 UI 确认”后，才把它接到正式执行链。

普通来源采集和目标保留分成两个明确生命周期，两者调用同一个严格材料核心。没有 `skip_stop`、`skip_restore`、`already_stopped`、`restore=False` 等布尔通行证，也不把普通 FULL 的恢复回执改成可选。

### 1. 材料核心：仅抽取原算法调用

建议新增 `ops/recovery/recovery_capture_materials.py`，不提供 CLI 或产品入口：

```python
prepare_materials(config, identity, root, *, output_budget, originals, transport)
    -> PreparedCaptureMaterials

capture_protected_materials(prepared, lifecycle)
    -> CapturedMaterials
```

- `PreparedCaptureMaterials` 为模块内创建的 typed 对象，持有已核原 config/raw/pins、FULL/INCREMENTAL 原 identity、现有 `MinimalSeries` / `MinimalSemantic` / MySQL adapters；不可用任意 dict/duck type 冒充。配置、工具、凭据、材料、实际导出 image digest 等校验全部先于停服/保护写入；内部先读元数据的步骤与大载荷准备可以分段，但不能迟至停写后才发现配置缺失。
- `CapturedMaterials` 只含原材料结果：capture root、captureInputs/entries/contentPoint/objectContentIndex pins、recoveryPoint、sourceIdentity；不含 `sourceRestorationPin`、不发布 READY、不宣称可覆盖。
- `lifecycle` 是模块内有限的两种正式适配器：普通来源生命周期和 `MainTargetCapture`。它提供保护检查、原 MinIO 停/启、实际阶段事件与原件归集。不能接收调用者自定义的成功 guard 或不受限命令执行器作为运行入口。
- 提取边界是现有 `semantic.capture → observe_data(before) → series.database → compare_data(after) → series.files → wait_ready → verify_objects_after_offline → position/Redis/finalize → capture_recovery_inputs`；函数名、格式、完整性检查和实际 SQL/对象/Redis 实现继续引用既有模块，不重写。
- 原 `minimal_capture_worker.capture_locked` 保留真实来源 preflight、实际锁、停 writer/SQL fence、try/primary 错误处理及无条件 `Runtime.restore`。仅把内部材料段改成上述调用；成功仍必须有原 `source-restoration.json` 且 `restored=True`。普通失败仍按原清理/恢复合同处理。INCREMENTAL 的既有父链/位置/affected-data 逻辑不借此改变。
- 分离材料 identity 的最小输入（原 `MinimalSeries` 实际使用 operationId/action）与“Spug UI 请求”schema：MAIN 使用内部 `MainTargetCaptureIdentity/v1`、`pointType=FULL`、`parent=None`，与原 RESTORE operation 绑定；不能伪造第二个 `SmallAppBackupUiRequest`/UI POST。普通 request 原样进入原验证。

### 2. MAIN 专用生命周期：同进程、同 ctx、同 custody

建议新增 `ops/recovery/recovery_target_capture.py`：

```python
MainTargetCapture.prepare(native, *, capture_ref, reservation_pin)
    -> MainTargetCapture

session.capture() -> CapturedMaterials
session.guard(force=False)
session.handoff(verified_preservation) -> target_capture_handoff_pin
session.snapshot() -> dict
session.close()  # 仅关闭本地 leases/fd，不启动/恢复/解除任何保护
```

`prepare` 在任何新增保护/停服写之前调用，完成所有可只读验证的配置/凭据/工具/作用域和资源准入；`capture` 只在现有 quiesce 完成后调用。具体约束：

- `type(native.native_context) is _NativeView`、phase=PREPARATION，原 ctx 同一对象；`native.protection_custody` 必须是同一 `ProtectionCustody`。prepare 只绑定原尚未安装的保护对象及预检；capture 必须再确认原 quiesce 已完成、archive/fence/scheduler 已安装且与原 journal 一一绑定。
- `capture_ref` 显式选原 frozen owner 的该 target `captureConfigurationPins` 成员，不能取第一个、不能接受未登记任意 path、不能用当前恢复来源 config 代替目标 config。空 map、未知 ref、显式 null 均拒绝。58/59 登记由父后续正规配置步骤完成，本阶段不修改当前原件。
- 逐项核 capture UUID、数据库、三项数据服务 ID/image、实际旧程序两角色 ID/image、writer 完整集合、MinIO 根/物理 scopes、S3 buckets/endpoint/凭据归属、Redis DB/身份、config/material pins 与原 active target 完全相同。当前 old program 与 incoming program 可以不同；只读比对对象始终是原 active target。
- 使用 ctx 已持有的物理 EX flock fd，核同 PID、fd/dev/inode/path/原 REPLACING operation；不另 open+flock、不 fork 一名 worker 持 inherited fd 冒充同 PID owner。
- 固定新输出路径为 ctx operation root 下 `target-preservation/capture`，目录逐级私有且唯一、原件 O_EXCL、不链接/不重用。必须与全部目标数据、preserved 路径、来源 archive RO 根、claim/runtime、控制状态根明确不重叠。不能修改 capture config 的原 archiveRoot 或原 pin 来迎合路径；新 typed admission 明确允许的仅是这个已绑定材料输出根。
- `reservation_pin` 必须是绑定本 ctx/original request/lock 的正式资源准入结果。输出预算组合原 ctx.budget，`deadline=min(原绝对deadline, 固定capture上限)`，所有查询/流式写/健康等待都受同一绝对 deadline。复用 capture 的累计 maxWritten/free-space 方法，不新建第二套字节算法；不以磁盘 free observation 代替独占预约。原生 budget 对象不变。
- 所有新控制写通过原 native 的正式 command/MySQL transport 记录；大 SQL/镜像流仍使用原 `dump_until`、`drain_owned_process` 和有界 sink，不塞进 NativeData.command 的内存 stdout 上限。
- 流式采集也要在固定 capture session journal 中写 intent→实际进程退出/终态→后置 guard；原 streaming helper 如缺终态 hook，只增加薄 observer hook，不换 SQL/压缩/对象/Redis 实现。进程未获终态或 exit0 后 guard 失败，均保守记录 session unknown。ctx 只接受真实终态，不合成 `RecoveryDataInvocation` 成功。SQL 导出期仅在这个精确 Popen 已登记且尚未 reap 的内部状态下采用原 `observe_database_barrier(...dump_in_progress=True)` 规则并保留实际计数，前后严格0；不能用普通调用者提供的 bool 或仅 phase 字符串跳过事务检查。

`handoff(verified_preservation)` 的权限严格限于恢复“原 quiesced PREPARATION 状态”：MinIO 已停止、所有应用仍停止、SQL flags 回原 `0/0`、原 scheduler 仍保持 paused、archive/fence 未释放。入参必须是父/仓库 owner 下一阶段正式读回验证器生成的 typed 结果，绑定本 session、原 context/binding/op/target/捕获点和完整仓库 proof pin，不能是任意 dict 或成功 callback。该 verifier/schema 未落地时不提供正式 handoff 成功路径；第一阶段可先用真实材料完成的 HOLD 状态和错误类型测试冻结接口，不用合成成功 proof 补齐。

handoff pin 不是 DROP/覆盖许可、不是 sourceRestored。第一阶段不得只凭这个 pin 调用 ctx.stage/clear；后续正式编排必须在它之前验证完整保留 proof，在 ctx.stage/clear 再独立核该 proof。这是后续集成不可省略的门禁。

### 3. 原 custody 的显式 SQL capture-fence 租约

只在 `ProtectionCustody` 增加专用入口（建议 `capture_view_for(native)`），返回内部 typed `TargetCaptureProtectionLease`；不扩大现有 `view_for`、不接受任意方法名/SQL/旧 native。租约绑定 ctx/native 对象身份、原保护摘要、原 scheduler intent/active pins 和 capture session identity。

原 `MainMysqlScheduler._state()`、preflight/install/verify/release 的 `0/0` 默认合同保留。将其状态解析/UUID/唯一数据库范围检查提取为内部共用函数；采集租约的独立方法只在该 typed 能力下核精确 `1/1 + 原 pausedState`，仍核 worker=0、原 journal；事务沿用正式 barrier 的导出期/非导出期规则，后者严格0。不是让普通 verify 接受一个 flags 参数。

租约依次写：`capture-fence-intent.json`（原 UUID、0/0、原 scheduler pins、ctx/binding/op）、实际设置 `read_only=ON; super_read_only=ON`、完整查回 `1/1/paused/worker0/trx0`、`capture-fence-active.json`。新文件只写在新 `target-preservation` journal，绝不向原三个保护 journal 添加文件或改变它们的固定文件集合。失败不恢复 flags、不启动应用、不恢复 scheduler、不删除原件；原 custody/新 session 标记 FAILED_RETAINED。

handoff 只在已知成功且所有 writer 屏障仍核通过时写独占 handoff intent，以正式 transport 设置回精确原 `0/0`，核原普通 scheduler.verify 重新成立并记录 handoff 回执。全过程绝不把 event_scheduler 从 paused 改回 ON；只有原 RESTORE 成功后的 `custody.release` 能按原序恢复。

活动/失败的 capture 租约必须阻止原 custody.release、第二次 capture、ctx.stage，以及普通 `.bound()` 被拿来绕过检查；不能把 FAILED_RETAINED 租约视作“没有采集”。在 ctx 中挂同一 typed session 的最小登记/check，类似已有 SQL staging manager，仅做本地身份/终态观察，不在 native guard 中递归调用 Docker/SQL。物理保护复核由 session 的显式 force guard 执行。

## MinIO 在线复查期间的连续保护顺序

下表为新 MAIN 生命周期；所有行使用同 PID、同 EX flock、原 PREPARATION ctx，业务应用始终停止，原 archive/fence/scheduler 的 intent/active 原件始终不变。

| 阶段 | MinIO | SQL flags / scheduler | 必须成立的检查 |
| --- | --- | --- | --- |
| 原 quiesce 结束 | STOPPED | 0/0，原 pausedState | 原全部 writer 停止；无外部 DB/Redis writer；端口 fence、网络成员、RW 卷和身份全核 |
| capture-fence active | STOPPED | 1/1，原 pausedState | 原保护和 drain 复核；新 lease 与 ctx 绑定 |
| 首次受保护启动 | RUNNING/ready | 1/1，原 pausedState | 启动前后 force guard；只启动原 MinIO；实际退出、StartedAt/完整配置/挂载/网络身份确认；健康等待有界 |
| 语义/SQL/Redis 采集 | RUNNING | 1/1，原 pausedState | 原算法完整检查；阻止所有登记/未知 writer；共同位置未变 |
| 物理树采集 | STOPPED | 1/1，原 pausedState | 实际 stop 终态确认后才读物理树；所有 writer 屏障持续 |
| 完整对象在线复查 | RUNNING/ready | 1/1，原 pausedState | 原完整 GET/版本/delete-marker/multipart/headers 比较，禁止只作一次列表或跳过内容 |
| 原 finalize/末尾检查 | RUNNING | 1/1，原 pausedState | 位置、Redis 和完整输入末核全部通过；保留 schema 的 sourceRestored=False |
| 材料完成后归档/读回 | STOPPED | 1/1，原 pausedState | 再次实际 stop 原 MinIO；保护保持，材料/输入 leases 不丢；归档和完整 readback 尚须父接线 |
| proof 通过后的 handoff | STOPPED | 原 0/0，原 pausedState | 只交回原 quiesced 状态；原 archive/fence 不 release，未授权 DROP |

补充约束：

- `native.storage_running` 只能在真实启动/停止终态且实际 inspect 全核后更新，不先改期望状态“让 guard 通过”。不用原 `bound()` 去核此临时 1/1；专用 session guard 显式组合 `verify_services`、`verify_runtime`、`application_runtime_inputs`、原 archive/fence 与租约 scheduler 检查。
- 首次启动前必须证明 capture S3 endpoint 是原登记的本机受 fence 端点。已登记允许 IP 的应用必须确实停止且不能由新容器占用；未知 RW 容器、网络成员/固定 IP 漂移、额外共享凭据写入者或无法排除的外部入口立即阻断。host-root 和 Docker daemon 属既有可信边界，不把 iptables 证明夸大成对恶意 root 的隔离；没有独占/归属证据不能继续。
- 失败/超时的存储动作不自动重发。start exit 未知时不在 finally 再 stop；已启动且复查失败时保留实际状态和全部 barrier，后续只凭原操作、原 StartedAt 和真实终态作正式保留处理。不能靠“清理”启动旧程序或解除 fence。`close` 只回收本地资源。
- 数据库 flags 回 0/0 并不开放业务 writer：原应用停止、外部 fence、scheduler paused、DB/Redis 独占检查仍在。任何 guard 漂移即不可 handoff；失败保持当前已证明/未知状态，不尝试恢复现场来伪造成功。

## 证据与失败闭合

固定新目录 `operationRoot/target-preservation/` 保存材料与生命周期证据，原保护 journal 不改名/重写。建议三个小型版本回执：

- `MainTargetCaptureIntent/v1`：operationId、targetConfigRef、captureRef/configurationPin、originalTargetPin、executionBindingPin、原 epoch context pin、原三保护 intent/active pins、resourceAdmissionPin、captureRoot、原绝对 deadline。只含 pins/身份摘要，不含明文认证。
- `MainTargetCaptureMaterials/v1`：state=MATERIAL_COMPLETE、intentPin、原 `CapturedMaterials` pins、原位置/原 target 身份、流式实际终态证明 pins、`writersRemainQuiesced:true`、`sourceRestored:false`。它只证明材料，不能当 `RepositoryPoint` 或覆盖准入。
- `MainTargetCaptureHandoff/v1`：材料 pin、随后正式 preservation proof pin（由父后续合同确定）、SQL capture-fence/handoff pins、原保护 pins、实际 storage stopped proof、`originalQuiescenceRetained:true`、`sourceRestored:false`。如果后续 proof 合同未实现，本阶段只测隔离 handoff 状态转换，不发布可供正式覆盖消费的 PASS。

失败记录为 `MainTargetCaptureFailure/v1`，聚合原 phase、failureCode、mutationDispatched、terminalUnknown、原 intent/实际终态/材料/保护 pins。首次失败冻结前纳入外层 unknown；已有终态原件不二写。不输出 `sourceRestorationPin`，不发布 READY，不清理半成品，不将本 FULL 放进普通自动增量基线。完整大账本与小型聚合 pins 分离，继续遵守原 epoch receipt 64KiB 和 native 专用有界读取合同。

关于 ctx 的末尾门禁：单一正式 capture session 的 ACTIVE、FAILED_RETAINED、terminalUnknown 或未完成 handoff 都必须阻止 stage；后续启用 MAIN 时，即使 HANDOFF 也须完整 preservation proof 精确绑定才能 stage/clear。不能用“session 不存在”作为已要求保留目标的旧行为退路。

## BDD / RED 范围（尚未运行）

新增测试建议仅两文件：`scripts/tests/test_capture_materials_lifecycle.py` 与 `scripts/tests/test_recovery_target_capture.py`。先写以下有限核心场景和测试，父用真实 Linux 独立快照跑 RED；得到实际终态后才改产品。

1. **普通 FULL 恢复合同**：Given 原普通 FULL 来源；When 共享材料段成功或材料失败；Then 仍走原 `Runtime.restore`，原服务恢复次序和 sourceRestorationPin 不变，恢复失败不得返回成功。用原真实材料格式/本地进程与文件，有限 Docker/SQL 协议 seam 明示，不将其称实际业务恢复。
2. **同锁与所有权**：Given 真实 Linux 文件、REPLACING epoch、ctx/保护对象；When 同 PID 原 EX flock 进入；Then 可创建唯一 session；换 ctx/native/budget/fd、子进程继承 fd、释放/换 inode 均在首新增写之前拒绝，外部 probe=0。
3. **正式目标配置**：Given 原 owner capture ref；When 无 ref/null/58 当前空 map、scope/UUID/服务/凭据 pin 或程序角色错配；Then 明确拒绝，不用当前恢复来源配置补足、不写 capture fence。逐项参数化保持有限。
4. **1/1 精确租约**：Given 原 scheduler ON/OFF/DISABLED 已正式 install；When 同 custody 捕获；Then 原 scheduler 默认 verify 仍只认0/0，新租约只认1/1+原 paused；任何 UUID、数据库范围、worker、非导出期 trx、journal 变化拒绝；真实有界 dump 子进程存活期自身读事务不误报，前后有事务则拒绝；无凭证/伪 phase/bool 不能启用新校验。
5. **MinIO 在线窗口**：Given 原 quiesce 后 MinIO STOPPED；When 完整材料采集；Then 严格顺序为 guarded start→语义/SQL→stop→物理→start→原完整对象复查/finalize→stop，应用 start、scheduler ON、fence release 次数均为0。
6. **writer 屏障未变**：Given 即将启动或正在复查；When fence 表、allowlisted writer 状态、网络成员/IP、挂载、RW 共用者、Redis 客户端或 archive 视图漂移；Then 不开始下一读写，不 handoff、不 stage、不 DROP；保留失败原件和实际服务状态。
7. **真实材料完整性**：Given 本地 gzip SQL/目录树/S3 HTTP+版本协议/Redis 固定序列的有限数据；When 调用真实既有 MinimalSeries/MinimalSemantic/逐对象复查方法（非合成成功结果）；Then 原材料 schema/内容/摘要一致；修改对象内容或 delete marker、Redis 或数据库 end 使正式原算法拒绝。真实数据库/Docker 不在此 fixture 证明范围。
8. **预算连续**：Given 原 MAIN 剩余时间和 output 累计写限制；When SQL/镜像/对象分段采集/健康等待；Then 原 deadline 不延长、原 native.budget 身份不变、超时/超字节/预约变化在下一实际派发前拒绝；不能重建 Budget 续时。
9. **实际流式终态**：Given 真实本地 Python 子进程输出到原有有界 sink；When 正常退出、被预算中断、仅 intent、或 exit0 后 guard 丢失；Then 终态与 unknown 如实记录，失败不 replay、不合成 ctx 成功。
10. **handoff 与后续阶段阻断**：Given 材料完成且原保护未动；When 手动尝试 release/stage/第二次 capture 或 proof 未完成；Then 均拒绝。第一阶段在真实 HOLD 状态验证未授权 handoff 拒绝，不合成成功仓库 proof；下一阶段正式 proof 后才补恢复原 quiesced 0/0+paused+MinIO stopped 的闭合用例，不能仅以材料替代 proof。
11. **失败不自动复原**：Given 任一捕获/启动/停机阶段失败或终态未知；When unwind/close；Then 不启动原业务、不恢复 scheduler、不解除 fence、不写 sourceRestored=true、不进入 READY；文件/ctx/lease 证据保留。

测试必须复用现有 `test_recovery_program_protection.py` 的真实 ctx/flock/epoch/私有原件 builders；SQL/iptables/容器有限协议 seam 只模拟外部响应，不可把正式 `ProtectionCustody`、ctx、完整材料核心替换成“成功 mock”。每文件 fresh pytest 可独立运行，不依赖 import 顺序。原 source tests/known schema 不删、不降低断言。

拟由父执行的有限 Linux 命令（新文件编写后才可运行；本轮未执行）：

```sh
PYTHONPATH=ops/backup_engine/formal:ops/recovery:scripts/tests python -m pytest -q -ra \
  scripts/tests/test_capture_materials_lifecycle.py \
  scripts/tests/test_recovery_target_capture.py
```

RED 必须是新行为缺失/精确保护冲突，不接受环境缺 flock、导入路径错误或组件缺依赖作为业务 RED。GREEN 后一次受影响回归至少包括现有 `test_recovery_program_protection.py`、`test_recovery_program_native.py`、`test_main_mysql_scheduler.py`、`test_main_published_endpoint.py`、`test_capture_parent_guard.py`、`test_capture_redis_auth.py`、`test_capture_request_binding.py`、`test_capture_archive_guard.py`、`test_backup_performance.py`；确认文件实际存在后运行。父协调 `test_backup_variants.py` 和实际双包 fresh Linux 核真实 strict 语义/原 FULL 恢复，不能只用源码 import 代替包内行为，也不冒称重跑旧全覆盖。

## 精确改动归属与后续集成顺序

| 顺序 | 归属/文件 | 内容和退出条件 |
| --- | --- | --- |
| 1，当前 | 本子代理：仅本计划 | 事实、接口、BDD/RED 和已知阻断交父审；不改产品 |
| 2，父明确分派后 | 新 `recovery_capture_materials.py`、新 `recovery_target_capture.py`、上述两测试 | 先实际 RED；抽取原严格算法，建立 typed session；真实 Linux GREEN/旧 FULL 回归 |
| 3，与2同一小迭代 | `minimal_capture_worker.py` / `minimal_capture_support.py`，`recovery_program_protection.py`、`recovery_mysql_scheduler.py`、`recovery_program_native.py` 的最小接缝 | 原 source 生命周期不变；精确 capture-fence/预算/终态 hook/ctx gate；禁止用任意参数改旧 guard |
| 4，父/当前各 owner | repository/保留角色、plan/app.js、容量、source/target 登记 | 接完整仓库归档和**全部载荷**独立读回，绑定 original epoch/本次 REPLACING/target/current data proof；登记合法目标 capture inputs；不借旧373/375或11月7包省略当前目标保留 |
| 5，父正式编排 owner | `recovery_program_restore.py`、必要 clear 准入/证据 validator | prepare 在保护前，capture 在 quiesce 后、任何镜像 load/switch/清库前；读回证明后 handoff，stage/clear 再核该 proof；完整失败/unknown 保留 |
| 6，父与包装 owner | files mapping / standard 构造 / 实际双包 | 精确构造新提交字节，MAIN 捕获必须获得严格语义实现；普通两 variant 既有行为保持。任何包只提供 lightweight 不完整证据时不能启用本功能 |
| 7，父另行协调 | 新鲜运行态准入、真实 Spug E2E 与收尾 | 按既有授权/门禁另做完整唯一操作，不重派原376，不用组件fixture声称现场保留成功 |

本子代理此刻不拥有第2–6步产品修改权限。尤其不改并行 owner 的 `repository_records.py`、`repository_minimal.py`、`standard_fixes.py`、planner/app.js；包装/仓库 proof schema 与正式登记完成之前，本设计有意不激活现场路径。

### 父批准第一阶段后的精确文件接线表

本表替代上句对第2/3步的待授权状态；第4–7步仍未授权给本组件，标准构造文件尚未接管。

本轮后续精确授权还包含：`formal_snapshot_linux.py` 的query/dump、strict/SAFE两份`formal_data_evidence.py`、schema/reference、endpoint与Redis inspect的显式observer接缝，默认None维持原路径；`recovery_main_target.py`仅提取原writer静默检查为`verify_writer_quiescence(native)`并在原位置调用。每一新增实际Popen接缝均先取得独立真实Linux RED，记录见本组件TDD日志。没有改变成员映射或标准构造文件。

### 实际 exporter 的有限账本嵌套与 drain 尾部

observer的`before`必须先完成同一session force_guard，再独占写intent、向同一ctx登记token，最后才能Popen。仅固定原mysql容器的正式mysqldump argv、同PID实际Popen且仍存活、同lease、唯一未结外token，才允许force_guard内部已观测成功的有限原保护命令摘要嵌套。该集合在没有活动exporter的完整原保护检查中冻结；不能在导出中扩展。不接受任意`mutation=False`、任意调用者查询或第二stream。

实际Popen已被poll观察退出但原drain尚在关闭/收完管道时，guard仅做同一ctx/物理锁/预算/私有文件身份检查，不准入新的嵌套外部读取。`finished`仍只由原完整drain正式回调执行；它固定真实终态后立即恢复严格0事务及完整force_guard，任何失败都阻断材料完成。未知/未创建/未获reap均保持未结，不提前写成功、不做双终态幂等框架。该有限尾部仍在原1/1、scheduler暂停、外部fence及绝对截止保护下。

Linux r5真实退出竞争RED后补充：lease以实际`waitid(WEXITED|WNOHANG|WNOWAIT)`区分RUNNING、EXITED_UNREAPED与实际Popen已知REAPED，不在保护检查中主动poll/reap。只有入口确认RUNNING的那一次有限guard登记实际process身份；若途中真实退出且未reap，仅该次guard原已冻结的只读命令仍可结束，scheduler此时严格0事务。下一guard入口已退出则只有本地检查；REAPED、外PID、任意命令与guard外调用不获此权限。原完整drain唯一finished/实际收割及其后严格0全核保持。此边界仅用于当前typed MAIN session，不改变普通FULL生命周期。

| 文件 | 本轮权限/接缝 | 首个对应 RED |
| --- | --- | --- |
| 新 `ops/recovery/recovery_capture_materials.py` | 原严格材料段唯一提取，ordinary/MAIN 两生命周期共用；无 CLI | 严格源码入口缺共享核心；原算法语义/调用序保留 |
| 新 `ops/recovery/recovery_target_capture.py` | typed PREPARATION session、实际锁、原保护连续 HOLD；未接 restore executor | 缺 session；对象/lock/ctx/配置负例及 MinIO 完整顺序 |
| `ops/recovery/minimal_capture_worker.py` | 仅严格 worker 原材料段转共享调用；原 try/restore/result 语义保留 | 原 FULL 真实生命周期/原恢复失败合同 |
| `ops/recovery/minimal_capture_support.py` | 输出预算绑定原绝对 deadline 的独立 typed 接缝；原构造不变 | 原预算身份、超时/累计字节负例 |
| `ops/recovery/recovery_program_protection.py` | 新 capture_view_for 与原对象身份租约；原 view_for 能力不扩大 | 1/1 专用租约、三原 journal 不变、无通用 transport |
| `ops/recovery/recovery_mysql_scheduler.py` | 严格状态解析复用，原默认0/0保持；专用租约核1/1 | 原默认1/1拒绝、新typed租约与paused/事务规则 |
| `ops/recovery/recovery_program_native.py` | 同一 typed session 登记/本地check/close，活动/失败session拒绝跨阶段 | ctx/lock/phase漂移在派发前拒绝；不接 executor 的 stage/switch/clear |
| 新 `scripts/tests/test_capture_materials_lifecycle.py` | 共享严格核心、普通来源恢复、实际候选payload消费边界 | 明确 source 与 SAFE payload 的缺失，不用LIGHT替代 |
| 新 `scripts/tests/test_recovery_target_capture.py` | 真文件/flock/epoch/ctx/custody；外部服务有限协议 | 有限核心正负例；不冒称业务恢复 |
| 新 `main-target-preservation-capture-tdd-log.md` | 独立阶段原件/命令/RED/GREEN/回归记录 | 所有轮次原终态保留 |

2026-11-10 父进一步确认：当前 SAFE 来源是认证冻包+`standard_fixes.apply`，不会读当前严格 worker 源；新模块不会自动进入SAFE。先冻结实际候选payload RED，再由父协调受限接管标准构造接缝。当前链准入候选代次保持原147/146与三模块delta，不得混入目标保留新成员；本轮不改 `standard_fixes.py`、files mapping，不构建包。若 formal streaming 终态需要改 `formal_snapshot_linux.py`，先报告具体 observer hook 与 RED，再经父协调归属。

## 事前只读验证与审查记录（历史阶段，非当前结论）

- 已读严格源 worker/support、原 MAIN quiesce/restore/native/custody/scheduler/fence 与预算；只读取实际45标准 tar 中 `formal_capture_semantics.py` 的相应函数，未解包安装、未执行产品代码。
- 未运行测试、构建、远端、Docker、浏览器或业务动作；没有生成任何捕获/保留/READY/成功原件。上面 RED/GREEN 为待实施计划。
- 父需确认：两新模块命名和 typed lease 接缝归属；严格包内材料核心的复用落点；父/仓库 owner 的正式 preservation proof schema。以上不影响先写真实有限组件 RED，但对应接口未明确前不得拼临时 dict、运行缺省 proof 或开启正式覆盖。
- 第一阶段可交付的是“共用严格 FULL 材料算法 + 原保护连续托管”能力，不是“目标当前数据已保留”。目标登记、完整仓库保留/读回和正式 UI/clear 门禁仍按后续步骤逐项完成。

里程碑1、2、3的只读设计均完成。2026-11-10 本机 `python -X utf8` 文档静态校验实际 exit0：UTF-8 无 BOM、无替换字符/行尾空格、末尾换行及20个既有源码/测试文件引用均通过；不是产品测试。当前停在父审查，不执行后续产品步骤。

上述为批准前历史记录。当前批准范围、实现状态及真实轮次以本文Current Status、精确接线表和`main-target-preservation-capture-tdd-log.md`为准；不据历史“未改产品”文字覆盖后续已获授权的本机实现事实。
