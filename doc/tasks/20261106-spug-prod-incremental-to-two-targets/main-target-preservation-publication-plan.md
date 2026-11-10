# MAIN目标保留第二阶段：正式发布、全量读回与清库前门禁

## Current Status

ready_for_closeout（2a本机实现已冻结，待父限定提交）。严格出版/全读回/原仓库锁与durable hold新22项、普通FULL三生命周期、真实SAFE root identity八项已有分轮PASS；原失败原件保留。2b同session handoff/首clear/历史闭包/retention消费尚未开始，等待父提交冻结实现后执行；当前无真实包、目标登记或现场覆盖许可。设计正文是已批准长期方案，实际完成边界与原件以本轮TDD和target-preservation-2a-freeze-r1.json为准。

## 目标、里程碑与预期验证

1. 定位现有同进程FULL归档发布、完整SMB读回、仓库proof及原锁/epoch/预算合同。
2. 固定最小持续接口和typed handoff/首次clear硬门禁，不新增源控制服务或复制SQL/对象/Redis算法。
3. 定位SAFE五项认证patch/新成员实际构造合同，列出58/59 capture登记的真实前置条件。
4. 写有限BDD/RED、分工与后续集成顺序，交父审；未经批准不开始实现。

预期交付是基于实际源码/已存在证据的设计和精确阻断项，不是现场状态、仓库成功proof或恢复授权。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。原件缺失/变化、payload未全读回、锁/epoch/保护漂移或unknown均阻断；不得从Git重造原字节、重派未知操作或用普通FULL的sourceRestored适配目标HOLD。
- 是否从根因和长期维护角度解决：是。复用现有正式publisher/readback，显式typed生命周期和保留角色，不建第二套数据算法。
- 是否存在临时补丁或绕过：否。不得skip_stop/skip_restore、fake sourceRestored/READY、以旧历史点代替本次目标数据保留。

## 经验门禁

- Trigger：覆盖前目标保留FULL、同锁采集/归档/独立完整读回、MAIN存储在线复查及clear准入。
- Preflight check：定位实际worker/SAFE构造pins；核本次目标UUID、原代次/epoch、全部writer、真实同PID EX flock、原预约/绝对deadline、原archive/fence/scheduler与三类全部载荷。
- Blocker：仅metadata-readback、缺完整payload原始读回记录、未登记目标capture配置、未封装严格SAFE算法、proof/当前阶段不绑定、unknown/锁丢失。
- Verification：后续真实Linux同锁/文件/ctx/custody/SMB协议与实际双包入口、成功和失败生命周期；真实58/59状态只由父另行只读观察，不从fixture推断。
- Forbidden action：不修改现有产品/测试或活动配置，不安装/服务器/清理/提交；不把第一阶段HOLD当READY，不重派376，不停止或重启原业务以凑前置状态。
- Evidence：父本次设计分派、第一阶段plan/TDD、经验索引“覆盖前保留备份完整读回”“自动增量链与恢复周期”“原main语义健康”“事件调度器与失败保护交接”。

## 已核事实与最小复用边界

本次只读调查的对象是当前源码、认证SAFE基线的相应函数、既有v4配置评估和父正式组件报告；没有取得58/59新鲜现场状态，没有生成任何保留成功原件。以下行号仅用于定位，后续实现必须以精确输入SHA/AST边界为准。

| 已有入口 | 可复用的正式能力 | 本次不能直接采用的部分 |
| --- | --- | --- |
| `repository_minimal.py::publish`（324起） | capture tree、归档manifest/point、binder、SMB配置和回执组装 | 先调用capture子进程；普通来源强制`sourceRestorationPin`。当前源码显式`verify_content=False`、`payload_content=False`、`payloadContentVerified=False`，不能拿来证明MAIN完整保留 |
| `CapturedPublisher`与`repository_native_publisher.Publisher.stream`（317起） | 同进程逐块传输、guard、O_EXCL/NOFOLLOW、有限字节、fsync、精确文件集合；`verify_content=True`核实际内容 | 不能把MAIN伪造成普通FULL UI请求/原来源恢复成功，也不能走`repository.execute/worker`另起锁/预算 |
| 认证SAFE中的`repository_minimal.publish` | 全字节发布、独立SMB完整读回、原始记录、binder、sidecar再次读回、严格清理后已发布链验证 | 仍含普通capture子进程和来源恢复生命周期；应提取其材料发布段，不能整段套在MAIN或用当前LIGHT文件覆盖认证文件 |
| `repository_native_readback.SmbReadback`（21起） | 新连接、认证/加密签名检查、有限记录缓存、目录树、载荷读取、connection identity | 当前源码`read`（82起）未比较传入expected，亦无读后身份核；认证SAFE对应方法有这些严格检查。MAIN必须消费严格方法，不能仅把`payload_content`设True就声称全部SAFE合同成立 |
| `repository_binding.assemble_readback_bindings`（58起） | manifest与读回原始记录、完整载荷集合、真实binder输出、内容/元数据绑定 | MAIN固定`verify_content=True`；不允许合成成功binder/expected副本或借metadata-only记录填proof |
| `recovery_program_restore.execute`（197–286） | 单次begin_restore、同原锁/预约/Budget、PREPARATION与RESTORE、原custody、完整来源材料准入 | quiesce后当前立即image load/switch；尚无目标保留，必须插在任何load/switch/stage之前 |
| `MainNativeExecutionContext.stage`（222起） | 活动/失败session与capture lease阻止跨阶段；旧PREPARATION view失效 | 当前无session仍可继续是旧合同。启用新保留策略后必须强制proof，不能利用`session is None`绕过 |
| `recovery_replace.clear`（218起） | 同RESTORE view、bound、服务核验；随后DROP/CREATE、MinIO清树、Redis FLUSHDB | 第一条数据破坏前必须再核本次保留proof，不能只在早期prepare核一次 |
| `repository_retention.RepositoryLock/plan_retention` | 仓库共用服务器字节锁、unknown阻断、静态legalHold、显式授权删除 | 尚无动态目标保留点角色/hold。现`recovery-read-guard.json`出现即拒所有writer，不能给本操作伪造owner例外 |

`snapshot_restore`保存的是程序配置/代次和epoch上下文，不是数据。第一阶段`MainTargetCapture.capture()`只返回`CapturedMaterials`并落`MATERIAL_COMPLETE`，MinIO已停、SQL为1/1、scheduler仍paused、外部fence与原应用停写保持；`handoff()`当前始终拒绝。该状态是阶段2的唯一输入边界，不是READY或仓库成功。

## 建议接口与文件归属

仅新增一个产品协调模块`ops/recovery/recovery_target_preservation.py`；采集算法继续在第一阶段共用材料核心，归档/读回算法继续在现有repository模块。不得新增第二个worker/源控制器/CLI或第二套SQL、对象、Redis实现。

建议固定以下API后再写失败测试：

```python
TargetPreservation.prepare(native, *, policy_pin, reservation_pin) -> TargetPreservation
TargetPreservation.preserve() -> preservation_pin
validate_preservation(native, preservation_pin, *, before_clear=False) -> verified_binding

# 位于现有repository_minimal，材料段的新正式入口；不创建capture子进程。
publish_materials(configuration, materials, *, publication, deadline) -> archive_proof_pin
```

`prepare`从真实`native.native_context`取得唯一ctx/owner/request/lock/Budget/custody，拒绝额外传入另一套同名对象。`policy_pin`必须是冻结owner登记的原pin，`reservation_pin`等于原正式预约；不接受临时拼装policy。它创建唯一publication journal并调用原`MainTargetCapture.prepare`，在写保护/停服前完成配置、工具、认证、可写归档位置与容量准入。`preserve`只能在原quiesce成功后调用一次，内部完成capture→publish/full readback→handoff→小型终态，不能由调用者填成功字典。

`publish_materials`的`materials`必须是本session产生的真实`CapturedMaterials`且仍持有其originals/预算/文件身份；`publication`为本协调器产生的封闭typed能力，固定operation、目标、路径、仓库锁及角色。普通FULL通过单独的原来源适配器调用材料段，仍强制真实source restoration原件；MAIN适配器要求连续HOLD，不生成该原件。不要添加`skip_restore`、`sourceRestored`参数或通用成功callback来混合两种生命周期。

严格SMB共享的最小位置是现有`repository_native_readback.py`：提取认证SAFE的实际严格`read`算法为一个共享实现，保留expected/前后stat/字节/缓存上限/fsync语义；MAIN用明确的typed `PreservationReadback`入口，认证SAFE原`SmbReadback.read`接同一算法。现LIGHT普通行为保持。这样只有一个严格算法，不能复制SAFE整文件或将当前LIGHT方法当正式全量读回。具体函数抽取边界须由父/包装owner在RED前核认证方法SHA；本设计不实施该变换。

| 文件 | 后续最小职责；本轮均未修改 |
| --- | --- |
| 新`recovery_target_preservation.py` | policy验证、同锁生命周期、typed publication/archive-proof/最终proof、独立验证入口 |
| `repository_minimal.py` | 抽出材料发布段；原SOURCE try/restore和LIGHT行为保留；MAIN不走capture子进程 |
| `repository_native_readback.py`、必要`repository_binding.py` | 共享认证严格读回方法及typed入口；完整载荷/原始记录/sidecar绑定 |
| `recovery_target_capture.py`、`recovery_program_protection.py` | 只实现已验证archive-proof后的同session handoff；保持原保护原件和普通FULL |
| `recovery_program_restore.py`、`recovery_program_native.py` | 插入prepare/preserve；必需proof的stage门禁；原failed/unknown不自动收口 |
| `recovery_minimal_runtime.py`、`recovery_replace.py` | 同一proof传给RESTORE native，并在首次clear前再次严格验证 |
| `recovery_program_evidence.py`及控制验收入口 | 验完整proof闭包、失败与unknown、generation/receipt一致性；不增加64KiB epoch receipt上限 |
| `repository_records.py`、catalog/retention与基线选择入口 | 明确保留角色与动态hold，排除普通自动增量基线；仅父协调对应owner后实施 |
| `files.json`、`standard_fixes.py`及构造测试 | 单独后续代次接新成员/精确方法；不得混进本轮现有147/146候选 |

## 策略、原件和typed proof

沿用事前评估的owner `targetPreservationPolicies[targetRef]`，不新建控制堆叠。建议每项是`MainTargetPreservationPolicy/v1`原件pin，精确字段为`schemaVersion,targetConfigRef,captureRef,captureConfigurationPin,repositoryConfigurationPin,backupEpochPolicy,maxArchiveBytes,maxReadbackRecordBytes,maxPreservationSeconds,minimumFreeBytes`。数值为显式正整数，capture基线pin须等于原target program policy登记；实际活动capture由既有generation解析后与本ctx evidence交叉核，不能把基线pin硬当当前活动文档。repository配置复用原正式配置/SMB凭据/tool pins并提取不依赖UI请求的校验，不伪造UI request。策略有效后即必需保留；不支持运行时关闭或缺字段回旧路径。

本操作固定`operationRoot/target-preservation/`，第一阶段`session/`和`capture/`保持，新增`publication/`；原三保护journal绝不改写。建议固定小型原件如下，字段在实施RED前由父最终冻结：

| 原件 | 必须绑定及消费含义 |
| --- | --- |
| `publication/intent.json`，`MainTargetPreservationIntent/v1` | 原operation/target/policy、owner/原target/活动capture/repository pins、ctx/binding/预约、旧READY与本次REPLACING事件、唯一archive路径、真实截止；先于仓库写 |
| `publication/archive-proof.json`，`MainTargetPreservationArchive/v1` | 上述intent、真实materials pin、FULL point/manifest/tree、全部payload发布账本、独立SMB原始记录/binder/sidecar复核pins、仓库hold intent；`payloadContentVerified:true`、`serverDurabilityVerified:false`、`independentFailureDomain:false`。仅已知完整通过才写 |
| 既有session的`handoff-intent.json`与`handoff.json`，`MainTargetCaptureHandoff/v1` | archive-proof、原lease与三保护pins、原SQL flags、实际handoff命令终态与0/0+paused+MinIO stopped复核；`sourceRestored:false`、`originalQuiescenceRetained:true` |
| `publication/result.json`，`MainTargetPreservation/v1` | state=SUCCEEDED、上述intent/archive-proof/handoff、hold pin、原目标UUID/程序代次和实际capture pins；只证明本次目标已保留且可在同操作继续，不证明恢复/业务验收/READY |
| `publication/failure.json`，`MainTargetPreservationFailure/v1` | 真实最后phase、failureCode、mutationDispatched、terminalUnknown、已有全部聚合pins；不重写已有成功原件，不清理半成品，不启动原服务、不重派 |

避免循环引用：archive-proof先独立完成；严格验证函数返回只由本模块构造、绑定同一session/ctx/原pin的内部typed对象，交`session.handoff()`；handoff只引用archive-proof，最后result再引用两者。不得传caller bool、普通dict或把最终result提前伪造出来。stage/clear消费的是最终result；历史验收可重新由原件验证，不要求原Python对象仍存活。

详细payload/native/process/SMB记录留在固定有界文件中，经小型聚合pin闭包；result与replacement receipt仅增`targetPreservationPin`及必要有限阶段pin。继续遵守epoch receipt原64KiB上限、大native账本专门上限和原unknown汇总。成功receipt后READY发布失败不重写已pin引用的任何snapshot/proof；失败外层可保守提升unknown，但不改先前成功原件。

## 同锁、预算与阶段顺序

1. 原`recovery_replace.execute`取得目标/source物理EX flock并保留原预约；原MAIN仍单次`begin_restore`早于首DB，进入同一PREPARATION ctx，取得原custody。
2. 原来源链/全部程序tar/元数据与data/program资源准入保持在任何保护/停服写之前。新增preservation prepare也在此完成：当前目标capture配置与原服务身份、工具/凭据、完整原件、独立SMB认证探针及真正可写目的、容量准入。探针在独占新小文件中写入/严格读回/删除，有独立intent/终态；失败则不quiesce。
3. 原quiesce先安装原archive/fence/scheduler并停止全部writer。`preserve()`复用stage1真实capture-fence 1/1及MinIO在线复核，最后保持MinIO停止、scheduler paused、原writer全部停止；不释放原保护。
4. 同PID同步发布FULL、完整独立SMB读回和binder/sidecar复核；每chunk/文件边界都核同ctx/锁/预算/文件身份，按原0.5秒节流加必要阶段force物理保护核。不得恢复每条只读调用重复force造成的过度保护开销，也不得让文件传输逃离绝对deadline。发布后为全部payload与sidecar固定完整目录/文件身份lease，持续到clear及本次终态；before-clear再核原全集与身份。完整内容读回已有一次正式原件后，不无条件再次读取全部大文件；任一身份/集合漂移则失败，不能用一次历史proof代替当前仍可恢复性。
5. archive-proof通过后执行下面唯一typed handoff，最终preservation result与仓库hold闭合；随后才允许原image load/switch/derive/stage。RESTORE native在首bound前接同一proof/custody；首次clear之前再次验证原目标→新generation的正式转换和proof。DROP库、清对象树、Redis FLUSHDB三者任何一次前置失败均零派发。
6. 原RESTORE数据链、业务语义验收、`replacement_finish`、原保护release、compact成功receipt、READY的既有顺序保持。保留点不因本次成功或失败自动删除。

全部耗时仍受原ctx Budget同一对象及同一绝对截止，capture预算只进一步收紧。新增`maxPreservationSeconds`从prepare计时且不能延长外层；readback/SMB/文件读取使用同一deadline适配器，不能另new Budget续时。容量按实际设备合并原数据恢复展开/投影、程序导入、目标FULL暂存、NAS归档、SMB小记录缓存及保留余量；同设备并存项相加，不拿原数据预算顶替新增材料。最大字节/空间不足必须在停写前拒绝，实际累计仍受原sink/出版字节限制。长链路默认预算是否足够必须以正式配置明确解决，不能用测试预算冒充生产容量。

原目标/source物理flock全过程不释放，不起新capture子进程抢同一锁。仓库发布复用其服务器字节锁；锁顺序固定目标flock→目的仓库锁，无自动等锁/超时夺权。当前MAIN入口使用`ArchivePathGuard`维持来源材料；`RepositoryReadGuard`位于另一recovery CLI路径，不能声称两者已自动兼容。若实际目的仓库有任一`recovery-read-guard.json`或write-unknown，保留准备/发布必须拒绝，不对本操作开例外。先登记一个明确不重叠、无该冲突的可写输出根；不能因同一NAS而假定不同路径/别名是不同仓库，必须按真实挂载/设备/服务端路径核对。

## 唯一handoff与首clear硬门禁

handoff只交回原quiesced状态，绝不是恢复来源。前提为本session仍MATERIAL_COMPLETE、无pending/unknown、archive-proof实际全核且全部原保护/数据服务身份当前一致、MinIO实际停止、SQL精确1/1、scheduler原paused、事务严格0、所有writer屏障仍成立。

先O_EXCL写handoff intent，再由同PREPARATION native正式账本传输设置精确原0/0；仍保持scheduler paused/原应用停止/外部fence/archive。回查精确0/0+UUID/事务0、原scheduler普通verify、MinIO停止和全部writer，才写handoff回执并允许session/lease进入handed_off。不能预设handed_off、不能让原guard接受任意0/0或1/1混合。转换中的唯一内部状态只允许本次已记intent的命令及其后严格复核；命令未派发/已知失败/未知都保留真实状态，禁止自动再发、恢复flags、释放保护或把异常吞成handoff成功。

启用`targetPreservationPolicies[targetRef]`后，ctx.stage在检查generation前必须验证同操作已完成proof及typed handoff；无session、缺proof或旧点均拒绝。首clear再次核proof pin、原owner/policy/目标UUID/capture和旧READY/本次REPLACING、原operation/binding/预约、同lock fd/原custody、目标从原程序到本代RESTORE的合法转换与真实handoff。proof是原目标的捕获，不将其改写成新target pin；转换由原execution/generation证据证明。已发布归档lease/小型proof交同ctx持有，stage后通过RESTORE view的原custody与本地proof检查消费，绝不再用失效PREPARATION native派命令。close本地资源不会授权clear，失败/unknown不会取得缺省proof。

## 仓库角色、持有和后续可恢复性

载荷仍使用正式`RepositoryPoint/v1`、pointType=FULL、parents=[]及既有manifest/RecoveryMaterial/ObjectContentIndex，不发明第二种SQL/对象/Redis布局。新增的是`TARGET_PRE_RESTORE`角色/保留绑定：原目标自身source identity、旧READY与本次RESTORE_STARTED/REPLACING、operation/target/current generation、完整readback。它不能冒用`SmallAppPointEpochBinding/v1`，不能把REPLACING松绑成普通READY，也不能进入普通自动增量baseline候选。

最小持有机制建议放在已存在`.repository-control`下的专属有界`preservation-holds/`：在同仓库锁内、point开始写之前O_EXCL写`MainTargetPreservationHoldIntent/v1`（唯一operation、repository、archive根/预定point路径、保留role、原proof意图）；完整后写另一个不可覆盖的`MainTargetPreservationHold/v1`指向真实point/result。intent存在而无终态亦保护对应路径，malformed/links/超界/unknown直接阻断retention，不能当“没有hold”。不向普通point/v1增加未定义字段，也不每次改静态policy.legalHoldPointPins。

catalog/自动baseline只明确排除登记的该角色（含未完成intent路径），其它普通点原合同保持；UI可把它列为“覆盖前目标保留”，不得把未完成材料列为可恢复。retention在原锁内将所有有效hold的完整依赖加入保护集合，并在每个删除前重新核；未完成/无效hold不允许删除。后续删除hold/点仍须正式显式授权，不因READY自动清理。将来恢复该点也必须走正式选择/来源绑定，不等于允许任意原目录导入。

这是后续repository owner必须实现的有限接缝，当前只有静态legalHold能力，没有可复用的动态hold终态。未闭合该角色/保留与选择合同，不得发布“完整可持续目标保留”功能。

## 58/59登记的具体前置

既有v4只读评估已核：57有一个capture映射；58/59 `targetProgramPolicies[*].captureConfigurationPins`为空。登记历史来源59或57的备份不是登记当前58/59的捕获。实施时必须先由父按原授权/门禁作新鲜只读观测，再独占生成新配置/代次原件，不能原地改旧owner/pin。

每台分别要有：当前MAIN程序/五服务完整身份与配置材料；自身数据库UUID/范围及查询/导出权限；MinIO真实data root、所有bucket/version/delete-marker/multipart/headers与凭据/所有writer归属；Redis实际db/auth pin；全部工具/library pins及Linux可执行性；原网络/端口/共享RW者/保护根；同一物理source锁/epoch；新capture限额；明确可写归档根/严格独立SMB凭据/容量。`.58/.59`这些新鲜事实本设计没有证明。

活动代次capture从原targetProgramPolicies的正式generation派生机制处理，baseline→current关系必须保留；`MainTargetCapture._configuration`现有目标服务/网络/凭据/挂载校验仍是首门禁。源input归档只读视图与目标保留输出写视图分离，均不得改/移除正式服公司共享`/mnt/nas`或fstab。目标启用后也只在Spug原恢复按钮的正式编排中自动执行，无需Codex临时SSH dump或人工选择skip步骤。

## SAFE实际构造与五项采集保持点

STANDARD来源为认证基线+`standard_fixes.apply`，LIGHT为`files.json`显式成员；两者不能用源码import顺序互相代表。当前构造器已有五个具名窄变换：`incremental_sql_stream`、`native_invocation_transports`、`incremental_chain_admission`、`program_restore_handoff`、`program_worker_handoff`，另有apply中的已审精确上下文replace。新捕获/发布接线不能丢弃这些变换，或用当前worker/runtime/repository整文件覆盖认证基线来逃过方法SHA/AST检查。

第一阶段真实SAFE worker契约测试明确要求下列五项保持点，后续构造须逐一仍有实际包入口证据：

| 保持点 | 当前正式证据边界 |
| --- | --- |
| `semantic.close()` | 原ordinary FULL finally关闭；不能借MAIN不恢复来源而删除该来源生命周期 |
| `semantic.verify_parent()` | 原parent/private输入持续验证；不能只保留一次配置pin |
| `SemanticCapture.finalize`的`complete=True` | 完整references/derived材料，不能替成源码LIGHT的complete=False |
| `observe_replica_bucket_dependencies` | 原完整bucket依赖观测；不能把单次对象列表称完整语义 |
| `_require_empty_multipart_observation` | 原multipart无未决证明，采集与离线后复查约束保持 |

同一测试还必须保留`runtime.restore()`和真实`sourceRestorationPin`；不是五项通过后即可省略原恢复。除此以外，以下认证合同同样不可减：对象双次versions/内容SHA/headers/delete markers与Redis DUMP/expiry；SAFE FULL原dump后的完整数据端点/位置/UUID和INCREMENTAL affectedData严格分支；全部payload出版、严格SMB expected/前后身份、binder/sidecar复读；持续ArchivePathGuard、精确清理及本地载荷清理后的published chain验证。第一阶段共享源码的before/after数据比较虽严格，也不能直接替换认证SAFE整段`capture_database`；只能抽实际共享子段/传输seam并保留各自已审语义。MAIN本地清理只能在正式proof/hold闭合后执行，失败保留，不能删除proof原始记录或把server durability/独立失败域提升为true。

第一阶段新增`common/recovery_capture_materials.py`、`common/recovery_target_capture.py`目前不在实际SAFE payload中；共享worker调用亦未入SAFE。`test_capture_materials_lifecycle.py`的这三项实际合同仍HARD HOLD。阶段2若新增协调器则还须新增`common/recovery_target_preservation.py`，实际成员数由完整manifest推导，不能继续硬认147/146或把旧三模块delta证据用来证明新包。formal streaming/query/schema/reference/endpoint/Redis observer接缝及strict Data副本都要按实际包内可达调用验证，不只检查两个新增文件存在。

父r8 fresh-process相关回归211项中195PASS、16项`test_capture_archive_guard.py`失败：载体直接加载源码LIGHT `CapturedReader(path_guard=None)`却预期SAFE guard。父r9已保持原断言，用实际认证SAFE payload独立预加载并核3个依赖模块的`__file__/SHA`，17项全部PASS/1.78秒，输入保持、容器删除，报告`capture-archive-scope-linux-20261110-r9.json`。因此r8的非archive194PASS加r9的archive17PASS覆盖计划211个唯一节点；不是宣称211同轮通过。此前r7/r8失败原件均保留。本设计不改产品或测试断言，不把错误入口载体当SAFE产品结论。

## BDD、严格TDD与后续集成顺序

以下都是待父审后执行的正式RED计划，本轮未执行测试或生成成功结果。新增测试尽量限定三个文件：材料发布/读回合同、typed preservation/handoff、MAIN真实执行入口；已有普通FULL和SAFE合同回归复用，不复制大套测试框架。

| Given / When / Then | 真实最小验证边界 |
| --- | --- |
| 原普通FULL来源；抽出发布段成功/采集失败/恢复失败；仍有原恢复次序、sourceRestorationPin与失败码，不会进入MAIN handoff | 复用第一阶段真实本地子进程/文件与ordinary FULL成功、dump失败、恢复失败三生命周期；source算法AST边界保持 |
| 真ctx/custody/EX flock与MATERIAL_COMPLETE；直接调用正式publish_materials；产真实FULL/manifest/binder/SMB原记录而非合成成功 | 真实本地payload/独立协议connection；外部SMB/Docker/SQL仅明确有限协议，不声称真实NAS/业务恢复 |
| 完整payload；少文件/额外文件/链接/内容错/同内容inode或读中身份漂移/expected错/认证拒绝；不产archive-proof/handoff/clear | 调真实strict reader、tree和binder；逐个精确失败，不把fixture成功字典当readback |
| publish已完成但SMB超时/末guard失锁/原件漂移；失败保留与unknown；不自动restore、重传、释放、启动旧应用 | 首次intent与所有终态真实落地；后续再次调用唯一入口明确拒绝 |
| archive-proof有效；正式SQL 1/1→0/0，scheduler仍paused且MinIO停；同session handoff成功 | 真flock/ctx/custody/native账本；实际本地进程传输/外部协议响应；无第二source worker |
| 缺proof/错operation、target、UUID、旧READY/REPLACING或旧capture/外ctx/外PID/预约变化/active或FAILED租约；stage/首clear在破坏操作前拒绝 | 调真实context.stage及recovery_replace.clear，DROP/树变更/FLUSHDB probe均0 |
| handoff命令未创建/exit失败/exit0后guard失败/未获实际终态；不伪handed_off，不replay、不恢复保护 | 与原process未知聚合合同一致，原intent/result不可重写 |
| 同源物理锁+仓库锁；另一retention/恢复read guard/unknown在场；无错误重入或保留点被删 | 实际Linux file/lock及第二本地进程；活动/异常hold均阻断删除，无目录fallback |
| 同一operation真实producer→RESTORE runtime→worker→历史validator；成功及stage失败、首clear拒绝、READY失败；proof闭包一致且原receipt保留 | 保留真实source/archive/ctx/custody/epoch/executor；协议seam范围明确，不手工publish_envelopes |
| 真实两variant交付入口；新成员/严格方法正确、普通FULL既有语义保持；LIGHT不完整合同不能冒称SAFE | 精确提交的专用worktree、actual tar/manifest、fresh Linux进程、有限真实数据；父统一派发，零skip，输入前后SHA保持 |

顺序建议：先完成父正在运行的阶段1既有回归和三项实际SAFE成员RED事实；再由父协调repository/包装owner固定上述policy/schema/方法边界，写最小RED；先归档/严格读回GREEN，再typed handoff/clear GREEN，再完整producer+历史验收闭合，随后独立新代次实际两包。最后才能只读准入58/59、生成新登记/安装、真实Spug用户路径唯一操作及验收。不得为了先解除按钮阻断而跳过任一步。

当前待审的实质前置：严格SMB共享的认证方法边界、目的仓库动态hold/角色选择合同、合并资源预算与正式足够截止、58/59新鲜capture登记、SAFE实际构造。这些都是功能启用前HARD HOLD；无一由阶段1 12PASS或已有历史点替代。

## 本轮验证与交付事实

- 父正式`capture-session-linux-guard-verify-20261110-r6.json`：12PASS/0FAIL/ERROR/SKIP，pytest169.05秒、outer198.234秒，原/副本输入保持、容器removed=true。是完整材料HOLD和生命周期/竞争组件证明，不是仓库/目标覆盖证明。
- 计划相关回归已有正确入口的211个唯一节点PASS分轮证据（r8非archive194+r9认证SAFE archive17）；另r6会话12PASS。没有重跑其余已通过项，也没有把三项尚缺新SAFE成员合同纳入通过数。
- 本设计只做定向源码/既有报告读取，未递归扫描PRIVATE、未重跑父测试、未访问服务器/Docker/浏览器、未构建安装提交或改活动配置。没有产生任何现场保留/READY/成功原件。
- 独立文档经显式UTF-8静态回读、引用存在性与无BOM/替换字符/行尾空格检查后交父审；产品/测试保持冻结。后续实现、RED和实际封包由父明确分派。
