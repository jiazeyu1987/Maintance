# MAIN 目标保留 2b：同会话交接与破坏前证明

## Current Status

ready_for_closeout。本机2b限定实现与必要验证已完成，待父代理精确审查和限定提交；没有本子项测试容器运行。前置实现提交685e8e0e87196a18bcba84285935740d69b507c0；阶段1/2a原证据保持。双包构造、配置登记、安装、远端及真实业务恢复均未执行，不宣称目标已可覆盖。

## 目标与里程碑

1. BDD/RED：archive-only 证明不能授权清库；真会话完整归档后允许唯一交接；缺失、漂移、外会话、未知均拒绝。
2. GREEN：显式 typed final proof、1/1→0/0 交接、持续载荷租约；同 ctx stage/首 clear 独立核验；原 producer 和资源关闭接线。
3. GREEN：有限 receipt/result/历史严格闭包、实际 retention 入口消费 holds。
4. REGRESSION：仅受影响的原 MAIN/native/custody/retention 与普通 FULL 生命周期；不重复无关已通过节点。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。已登记 policy 时缺 session/final proof 立即拒绝；旧无 policy 分支保持。
- 是否从根因和长期维护角度解决：是。同一次操作的真实锁、原保护 custody、仓库锁和持续路径身份共同持有；不使用时间缓存或 caller skip 参数。
- 是否存在临时补丁或绕过：否。旧 archive proof 保持不授 clear；新增最终证明显式绑定原 proof 与真实 handoff，不改原件。

## 经验门禁

- Trigger：MAIN 覆盖前保留与清库。Preflight check：目标 flock→独立目的 RepositoryLock；配置/容量/可写意图在停写前完成，源 readGuard 无 owner 特赦。Blocker：未知、并行占锁、源目的根冲突、缺完整归档/严格读回。Verification：真实临时文件、flock、ctx/custody、协议进程、独占 JSON 和零破坏 probe。Forbidden action：临时 SSH dump、恢复 flags 重试、缺证明回旧路径、REPLACING 当 READY。Evidence：publication-plan、阶段1 r6/r8/r9、2a closure/SAFE 回归与 freeze-r2。
- Trigger：大载荷证明。Preflight check：初次完整 readback 后持有 ArchivePathGuard 文件/inode/目录全集；后续 same-object/local pins 校验。Blocker：任何身份/集合漂移。Verification：计数证明 stage/clear 不再全 SHA 读 payload；离线历史验证独立完整读。Forbidden action：按时间缓存、skip_verify、丢弃持续 lease。
- Trigger：Linux 测试。Preflight check：固定镜像/离线 wheel、network none/read-only root/cap-drop、无 socket/NAS；原/副本输入 SHA、JUnit/raw log、真实容器清理。Blocker：collect/载体错误不当产品 RED。Verification：逐轮退出/零 skip/输入不变。Forbidden action：覆盖旧失败报告、合成成功或重跑业务。

## typed API 与精确证明边界（实现前冻结）

保留 `VerifiedPreservationArchive` 与 `validate_archive` 的 archive-only 语义。新增不可由 pin/字典替代的 `VerifiedTargetPreservation`，仅由 `TargetPreservation.handoff()` 在真实 session/lease 交接成功后构造；同 publication/context 的对象身份与固定 pin 才可消费。

- `MainTargetCapture.handoff(typed archive)`：只接受由本 publication 内部完成严格核验并持续租约的绑定；原公开 archive-only 值仍拒绝。先独占 `handoff-intent.json`，通过原 native 账本唯一 SET 0/0，随后严格 UUID/flags/事务零、原暂停 scheduler、MinIO 停止和 writer/fence/archive 核验，才写 `handoff.json`。失败/未知进入 FAILED_RETAINED，不重放。
- `MainTargetPreservationHandoffIntent/v1`：`schemaVersion,operationId,targetConfigRef,bindingPin,archiveProofPin,captureSessionPin,originalFlags,restoreFlags,createdAt`。
- `MainTargetPreservationHandoff/v1`：`schemaVersion,state,operationId,targetConfigRef,intentPin,archiveProofPin,originalResultPins,finishedAt`。
- `MainTargetPreservation/v1` 最终证明：`schemaVersion,state,operationId,targetConfigRef,policyPin,intentPin,archiveProofPin,handoffPin,holdPin,originalResultPins,finishedAt`。`SUCCEEDED` 仅证明保留和交接，不是业务恢复/READY。
- `TargetPreservation.handoff()` 返回 typed final；`require_preservation(context,native=None)` 在 policy 存在时必须核同 ctx/final/pins/lease/锁/原绑定和原 custody；stage 只本地核、clear 使用当前 RESTORE view 再核，绝不让旧 PREPARATION view 派发。
- 2a publication 已完整读回；final 绑定沿已持有 lease 校验，不重新全 SHA 读取 payload；历史 reader 显式独立完整核载荷。
- producer 的有限 `targetPreservationPin` 同时进入 result/receipt，详细原件仍入原件闭包；历史验收绑定该字段与原 owner policy。原 ctx/native snapshot schema 不混入未定义字段。
- ctx.close 成功/失败都关闭 preservation repo lock/leases、capture lease/session；本地关闭不释放业务保护、不删除 hold。

## 文件接线表

`recovery_target_preservation.py`（最终 typed proof/历史材料验证）、`recovery_target_capture.py`（handoff/local guard）、`recovery_program_protection.py`/`recovery_main_mysql_scheduler.py`（唯一 flags 交接）、`recovery_program_native.py`（stage/本地持续验证/关闭）、`recovery_program_restore.py`（prepare/preserve/handoff/result）、`recovery_minimal_runtime.py`/`recovery_replace.py`（RESTORE proof/首 clear）、`recovery_program_evidence.py`（历史严格闭包）、`repository_retention.py`（实际 hold 消费）。专属测试新增，不修改其它代理消费者/Spug/activation/SAFE 构造。

## BDD

- Given 真 ctx/custody/flock 且完整材料 readback；When 同 publication 交接；Then 真实 1/1→0/0，scheduler 仍暂停、MinIO 停、原保护未释放，唯一 intent/result/final 原件落地。
- Given archive-only/缺失/外 ctx/漂移/未知；When handoff/stage/clear；Then 明确拒绝，DROP/对象删除/FLUSHDB 为零，不重试或释放保护。
- Given final proof 和持续 lease；When stage 后 RESTORE clear；Then 独立复核同 proof 与合法 generation，旧 PREPARATION 不派发，载荷不重复全读。
- Given 成功或异常；When ctx.close；Then repo lock 和全部本地 fd/lease 关闭，hold 和失败材料保留。
- Given malformed/pending hold；When 实际 retention.plan/delete；Then malformed fail closed、有效 pending 持有路径不删除，普通 Catalog 不冒列保留点为 baseline。
- Given 正式 producer→runtime→worker→历史验收；When 成功、handoff未知、stage失败、READY失败；Then final/receipt/result 闭包一致、原成功 receipt 不改写、unknown 不重发。

## 验证记录

RED：唯一 session35713，`run-target-preservation-2b-local.py --label handoff-red-r1 --safe-semantics --tests scripts/tests/test_recovery_target_preservation_handoff.py`，真实 Linux 5FAIL/0ERROR/SKIP，exit1，pytest133.91秒/outer329.312秒。首项已完整执行 capture/publication/readback 后精确缺 `TargetPreservation.handoff`；另四项分别为缺 stage 策略门禁、ctx 未关闭 publication、retention 两种异常 hold 未查就读普通 inventory。输入原/副本保持、容器 removed=true，报告 `target-preservation-2b-handoff-red-r1.json`；原 log/XML/tar 在 PRIVATE 同 stem，保留不覆盖。

候选 r1：handoff-green-r1 实际4PASS/1FAIL，155.05秒pytest、outer221.828秒。完整 capture→publication→handoff 已通过，新测试误用了不存在的 `running_apps` 属性，正式属性为 `running_applications`；仅精确改测试属性名，其它断言保持，不标整组 GREEN。runtime-red-r1 为两FAIL，其中 policy 用例沿用了旧完整 owner 预约，卡 `RESTORE_RESOURCE_RESERVATION_CHANGED`，不是该接线的 RED；精确改新 fixture 为独立 owner/root/host 预约后重取 RED。clear 的错误类型测试是仅消费入口的类型拒绝 unit，不冒称真实 ctx 正向。

runtime-red-r2：2FAIL/0ERROR/SKIP，exit1，独立预约已通过，首项实际 producer 在保护/导入/切换后才由 stage 报 PROGRAM_TARGET_PRESERVATION_REQUIRED，明确尚缺首停写前准入。clear 类型负例依旧越过 bound 读机器身份，缺独立 proof 门禁。两项均是实际接线 RED。handoff-green-r2 的唯一正向没有到交接，在 SOURCE_DATA_BEFORE/catalog 的原 querySeconds=10 窗口触 FORMAL_CAPTURE_PIPE_DEADLINE；保留真实失败，不当交接产品回归或调大产品默认期限。该轮和另一独立 RED 载体同时运行；后续完整捕获轮顺序执行，保持当前 fixture/策略预算，以实际终态判定。

producer-red-r1 为载体 collect ERROR：快照缺新 handoff fixture 依赖文件，不是业务 RED。只修载体明确清单纳入三个新测试文件，原报告保留。父已授权新 fixture 使用明确足够预算；仅新的 2b capture_protocol 包装 fixture 在全 owner/pin/预约形成前设置 querySeconds=30/dataSeconds=60，work=180/context=240 不变，普通 FULL/原2a测试/产品默认均保持。顺序跑完整捕获，避免并行载体竞争。

producer-red-r2 仍为 fixture collect ERROR：独立 pytest 未导出 wrapper 所依赖的 original_capture_protocol 别名；仅精确导入补齐，原报告不作业务 RED。两轮任务容器均 removed=true。父诊断 Spug/Docker 时暂停新容器，本地按已有 runtime-red-r2 / handoff-red-r1 实施停写前 prepare、真实 capture/publication/handoff、显式 RESTORE typed proof 与首 clear 双重复核；ctx 本地 guard 直接调用非递归资源检查，保留原仓库锁算法/readGuard、原 payload/inode/closed-directory 租约，不重新读大载荷。

producer-red-r3 实际1FAIL/0ERROR/SKIP，pytest10.76秒/outer140.266秒，输入保持、container removed。真实worker进入PREPARATION，但复用的旧ActualProcessProtocol ctor所有formal模块同目录断言不适用于capture已加载的strict Data，尚未到捕获。仅新2b fixture替换该构造载体段为相同真实CaptureNative ctor、NativeData.command/formal SQL transport，逐模块断言正式strict/源码formal具体路径与SHA；不改旧用例、不换错Data导入或合成终态。

producer-red-r4：1FAIL/0ERROR/SKIP，pytest66.22秒/outer161.032秒，capture42.622秒后原current_owner_guard五秒窗口拒绝。定位为新综合协议观察器每个Popen都复制整份增长ctx.snapshot账本；仅新2b fixture直接核真实最后intent、pending和argvSha，仍实际Popen/终态全留，旧fixture和产品五秒不改。此轮不是history缺实现RED。

producer-red-r5：1FAIL/0ERROR/SKIP，pytest184.68秒/outer436.953秒；capture107.097秒和copy55.833秒真实完成后，原180秒preservation绝对期限正确拒绝，尚未readback/handoff。原件保留。父明确批准新综合fixture独立owner/root/host/预约及新capture/policy pins，work/maxPreservation480秒，原owner600秒、query30/data60和产品五秒不改；依据163秒已测capture+copy以及尚余完整readback/原件核/交接。只用于本机每命令真实Popen有限协议，不是现场数GB策略。新的carrier外层900秒仅包住Docker启动和原owner600秒，超时仍精确回收本任务隔离容器。

producer-red-r6：实际1FAIL/0ERROR/SKIP，pytest117.60秒/outer194.578秒，capture105.897秒处原 dataSeconds=60 的 FORMAL_DATA_DEADLINE 拒绝，尚未到历史正向。保留原件，不标作 history RED。父已明确批准仅本轮综合 fixture 的 dataSeconds=180，query30/work480/maxPreservation480/owner600保持；原产品及旧fixture默认期限均不改。当前本机 Docker 竞争会显著增加真实协议进程启动成本，后续实际捕获轮顺序执行，不以加总超时掩盖算法或原生终态。

stream-intent-red-r1：唯一实际 session56121 已 exit1，1FAIL/5deselected/0ERROR/SKIP，pytest7.01秒/outer84.157秒。实际 PREPARATION image exporter 已经通过真实 Popen/reap，并产生真实 native invocation；新 stream writer 写入297字节（含LF），原 Native v1 intentObservation 正式 canonical 为296字节，精确断言失败。报告 `target-preservation-2b-stream-intent-red-r1.json`，原 log 9613B/SHA9087dd45ba67614588598e26088f29de3846afc2e77cc6e48c63baa189858205；输入原/副本保持、容器 removed=true。最小候选仅将新 stream writer 复用现有 `recovery_program_activation._exclusive`（正式 engine canonical、O_EXCL、fsync、原guard），不改原 Native v1解析/digest/字段，也不放宽LF容错；activation→generation 的现有导入不引入 capture/native 循环。

离线入口先行 malformed-input unit：Windows原 session14270 实际1FAIL/1deselected，15.22秒，精确缺 `validate_preservation_evidence`；实现候选后原 session88831 实际1PASS/1deselected，0.18秒/exit0。此项只证明未绑定scope在读载荷前拒绝，不冒称Linux或完整producer正向。完整离线入口复用既有严格 `assemble_readback_bindings(...,verify_content=True)`，独立读实际归档载荷/原SMB读回原件、固定sidecar全集、native canonical与终态、真实handoff/hold闭包；返回历史事实且 `clearAuthorized=false`，不能构造live typed grant。

## 当前有限闭环与HOLD

最终有限组为：handoff文件现7项（含实际stream canonical及逐删前late hold）、runtime入口2项、producer文件5项（malformed unit、真实成功、handoff外部SQL协议未知、stage失败、成功receipt后READY未知）。后3项新负例使用同一个既有完整producer fixture；真实worker/runtime/ctx/custody/epoch/捕获/归档路径保持，外部DB/Docker/对象语义仍明确为有限协议，不声称真实业务恢复。不得手工发布成功envelope代替producer，也不把尚未执行的用例记成通过。

历史 Native 扫描仅新增固定 `operationRoot/target-preservation/session/stream-[0-9]{5}.json`，仍对扫描集合与实际完整ctx账本全等校验；不以glob收任意新路径。最终preservation pin进入有限receipt/result/worker错误交接，详细原件通过原snapshot闭包保留。stage/首clear沿同ctx持续lease与元数据核验，离线历史是独立完整内容验证，两者权限不互换。

当前尚未完成完整producer正向及对应history，不能声明2b或目标可覆盖。父为分离Spug实际预检与本机Docker竞争，已要求在session56121终态后暂停新Docker载体；已确认没有本子项容器运行，仅继续本机源码/静态核对，等父明确放行再跑有限实际组。

另一个明确部署HOLD：现 `MainTargetPreservationPolicy/v1.repositoryConfigurationPin` 下的固定 `PreservationReadback/v1.recordRoot` 必须等于本operation的 `target-preservation/publication`，尚无正式按operation派生路径；本机fixture每次独占新owner/root/pins不能冒充长期三服配置。phase3须另有显式只读模板→同ctx独占派生配置/pin合同；本阶段不静默替换固定policy或放宽root。三新common成员与SAFE具名transform、实际双包、新控制代次协议及58/59捕获登记/任何远端恢复继续HOLD。

## 精确完整性闭合（父已批准）

- 同一个真实 typed final 的公开 reference 被指向另一份内容相同但路径不同的JSON时，必须因不等于原固定 `publication/preservation.json` pin 拒绝，而不是以等价schema授权clear。在既有完整handoff场景插入该精确断言，保留其它barrier/无重复全读/漂移断言；先拿真实RED，尚未修产品。
- 实际 `execute_retention` 已计划并取得原 RepositoryLock、完成当前inventory与DELETE_INTENT后，出现新的 malformed hold 时必须在真实 `shutil.rmtree` 前拒绝。新轻量文件inventory seam仍实读point/manifest/plan pins和原服务器字节锁，明确不代表完整业务archive/readback。Windows首次本机试跑失败在新fixture混用engine/repository pin路径分隔符，精确改用原repository.pin_file；第二次到真实删除前hold检查后因Windows无geteuid失败。均为载体边界，不当产品RED/GREEN，也不改Linux权限算法。
- 父只放行下一唯一有限轮；实际命令 `run-target-preservation-2b-local.py --label handoff-runtime-r3 --safe-semantics --tests scripts/tests/test_recovery_target_preservation_handoff.py scripts/tests/test_recovery_target_preservation_runtime.py scripts/tests/test_recovery_target_preservation_producer.py --expression "not test_main_"`，固定10项（仅一次完整capture）。启动后源码/测试冻结，原handle session45679；结束必须记录真实终态及清理，不能自动重复或启动下一组。

该轮 session45679 实际 exit1、10项9PASS/1FAIL/0ERROR/SKIP，pytest169.66秒/outer203.171秒，输入原/副本保持、容器 removed=true。真实capture64.361/copy20.118/full-readback17.759秒后，唯一FAIL为 copied final reference 精确 `DID NOT RAISE`，因此是最终原件身份缺口的真实RED；其它9项均实过。最小实现仅在原live检查中加入 `final.reference == publication._pins[固定preservation.json路径]` 全等要求，再读原metadata，未改schema/原件/lease/历史pin。

父明确批准唯一有限GREEN范围为原10项及现成完整producer成功→history、handoff未知、stage失败、READY未知4项；每次需要独立完整capture，故后续各carrier顺序运行、逐例独占标签/快照/日志/JUnit与预算，不并行Spug/UI、不新增harness或场景，不动产品及旧fixture期限。首个原10项GREEN标签为 handoff-runtime-green-r4；之后先收完整producer成功实际终态，不能将组件PASS当完整恢复闭环已完成。

handoff-runtime-green-r4 原 session68871 实际 exit0、10PASS/0FAIL/ERROR/SKIP，outer191.687秒；原/副本输入保持、container removed=true。fixed final pin拒绝、handoff后原payload同内容inode漂移拒绝且无重复全SHA、canonical exporter、注册准入/首clear、ctx关闭与实际retention planner/逐删前hold均通过。该组仍不代表完整producer成功。随后按既定唯一顺序启动 producer-green-r7/session71481，只选真实worker完整成功→historical validator一项，输入继续冻结，不同时跑其它capture。

producer-green-r7/session71481 实际 exit1、1FAIL/0ERROR/SKIP，pytest297.75秒/outer309.125秒；capture113.504/copy38.967/full-readback30.527秒均完成，后续已构造实际RESTORE native（两轮formal组件路径/SHA输出），但worker返回 RESTORE_KEYERROR/actualNativeExitCode=0，未到该测试离线验收。原/副本输入保持、容器 removed=true，失败原件保留；不能据此称成功或在无trace时猜测产品缺陷。原worker按正式合同仅保留errorType，因此新fixture只增加实际producer异常trace并原样raise，原worker/产品及所有业务断言不改。静态线索是原CaptureNative外部协议状态表仅有旧app ID，RESTORE新app ID尚未登记；必须由真实trace确认后才能精确修fixture，不能先猜测替换状态或跳过原生命周期。父已要求后续容器暂停，本子项无容器运行。

格式核验：原生r7终态后，仅将HEAD原为LF、工作文件全CRLF的 minimal_runtime/replace/retention/minimal_worker 四文件恢复LF。旧工作raw独占保存PRIVATE/target-preservation-2b-format-r1，逐一核与r7实际sourceInventory原SHA相同；前后完整 AST（include_attributes=True，含line/column位置）全等、仅CRLF→LF，行为测试未为此重跑。正式格式报告 `target-preservation-2b-format-verification-r1.json` 3170B/SHA7be51074adc1837fc0ba9f57a5ab1fbdbda003bfbeb6b5d089647573b903fb0d；原运行的snapshot/log/JUnit/输入pin绝不改写。

## r7 后有限协议定位与失败原件保全

r7 driver仅将raw stdout/JUnit带出tmpfs，未导出生成的worker完整结果、最后invocation/state；该轮pytest assert有截断，因此现有原件不能证明最后成功start/stop的精确ID。保留这一证据缺口，不从已删除tmpfs补造原件。源码静态可证ProtocolEngine新建8/9开头ID，而CaptureNative状态表只有原五服务；该线索尚须实际RED。

BDD：Given现成fixture的真实有限ProtocolEngine创建新backend ID；When原CaptureNative.docker对同一ID执行start；Then引擎状态与capture状态表同步、原callback/action保持，且不启动producer/capture/SQL恢复。新增一个微型协议用例，仅证明fixture一致性，不代替完整MAIN。当前producer文件共6项；新增项不扩展产品能力。

父已批准只在当前新2b fixture/driver增加失败原件导出：fixture teardown在tmpfs删除前，将实际worker完整raw结果、真实producer traceback、有限末次invocation及其原intent/terminal文件、协议state原文件和实际进程returncode，通过一个显式base64 stdout记录带出。driver严格解码、校验文件bytes/SHA并以独占新路径写PRIVATE，报告列出diagnostic pins。只取固定/末项原件，不递归扫描、不另建通用harness、不改业务stderr限制或实际终态；日志无材料/私密凭据公开输出。原r7及其driver原件保持。父UI期间不启动Docker，待明确放行后先微型RED，再最小fixture修复与原完整producer验真。

父放行后，微型fixture-created-id-red-r1/session84131实际1ERROR，原因是综合publication fixture要求SAFE而本轮纯协议未引导；不是预期RED。精确改该微型测试只依赖同一capture_protocol，不改变旧SAFE断言。r2/session98960实际1FAIL/0ERROR/SKIP、pytest0.67秒/outer28.656秒，原CaptureNative.docker:192实际KeyError=8×64；创建和引擎start callback已真实发生。输入保持、容器删除。候选只在新2b composite adapter把真实engine中当前RESTORE app的新ID观察登记进capture协议状态表，原super callback/action完整保留；RESTORE本地运行态也从同engine观察投影，而不是CaptureNative原ctor的固定true。原fixture/产品未改。

fixture-created-id-green-r3/session17614实际exit0、1PASS/5deselected/0ERROR/SKIP，outer65.016秒；原/副本输入保持、容器删除。仅证明有限外部协议的同一create/start状态一致，不声称完整MAIN。后续完整fixture让CompositeCaptureProtocol进入ActualProcessProtocol真实MRO，保持正式NativeData.command和所有ctx/SQL/capture调用。完整producer下一轮仍只原成功→history用例；capsys.disabled保证真实worker/trace/末次原件即使成功也在删除tmpfs前带出并校验保全。未重跑已GREEN10项或历史1630。

## r8 实际成功恢复与独立历史权限缺口

producer-green-r8/session25824实际exit1，1FAIL/5deselected/0ERROR/SKIP，pytest269.41秒/outer299.875秒。capture87.019/copy39.296/full-readback31.076秒。实际worker为SUCCEEDED/exit0/RESTORE；两native已关闭，同ctx记录1719次invocation，1636个实际协议进程均exit0。随后独立validate_preservation_evidence读取私密readback-originals.json时被原_Reader的PROGRAM_EVIDENCE_FILE_INVALID拒绝。两种结论分别保留，不能将worker成功写成历史验收成功。输入保持、容器removed=true，原report/log/XML不改。

原stdout已在tmpfs删除前带出完整诊断，但pytest的FAILED紧贴marker，使driver原行首regex没有提取。仅从原raw日志精确解码唯一marker，校验每个raw的bytes/SHA，另存5份实际原件；追加报告target-preservation-2b-producer-green-r8-diagnostic-export-r1.json（2435B/SHA5fa99932df1b950f5216bce51288d46f06e6c83c20d4722a40b95aa0c4b76286）。后续只在新fixture marker前加换行，保持原driver/报告原件。

根因：MAIN直接构造PreservationReadback，未经过repository_minimal.main的umask077。read_verified保留raw及继承verify的write_new原件索引在umask022下创建0644，而operation私密根历史reader正确要求无group/other位。父已批准仅专用MAIN读回入口显式0600/O_EXCL/NOFOLLOW，不改全局umask、repository_records、历史权限规则或普通SmbReadback默认合同。

BDD：Given普通umask022及现成真实文件SMB协议；When MAIN read/verify生成保留raw与原件索引；Then真实历史_Reader可读取且所有新原件0600/单链接。Given普通SmbReadback；When同协议verify；Then原创建字节与0644合同保持。新增精确测试文件test_recovery_target_preservation_readback.py，两项MAIN精确RED加一项普通reader回归，使用独占标签载体，不重跑完整FULL来定位。

最小设计：SmbReadback.verify原write_new调用提取为_write_original_records默认hook，默认仍原write_new；PreservationReadback覆盖，以repository canonical及严格私密排他写原语输出。仅read_verified的保留raw同步该私密writer。新writer局限已持有私密record目录、原deadline及原pin，O_EXCL/NOFOLLOW/0600并fsync文件和目录；不改旧payload/readback schema或任意历史pin。

readback-private-red-r1/session17622实际exit1，3项2FAIL/1PASS/0ERROR/SKIP，pytest1.64秒/outer28.969秒。两MAIN分别实际read与完整verify后，原真实_Reader均精确PROGRAM_EVIDENCE_FILE_INVALID；普通SmbReadback同协议verify与0644合同PASS。输入原/副本保持、容器removed=true。仅据该精确RED实现上述专用私密writer/default hook，不改普通read方法或repository_records。

readback-private-green-r2/session65404实际exit0、9PASS/0FAIL/ERROR/SKIP，outer11.515秒；新3项及原6个真实SMB协议正负例均通过，原/副本输入保持、容器removed=true。仅MAIN retained raw/原件索引使用显式0600排他writer；普通SmbReadback原read方法和默认write_new仍保持。之后顺序仅原完整producer成功→独立history一项，不重跑已通过10项。

producer-green-r9/session90945实际exit0，1PASS/5deselected/0FAIL/ERROR/SKIP，pytest304.23秒/outer492.89秒；capture94.393/copy41.099/full-readback36.217秒，原绝对期限保持。真实worker完成保全→typed handoff→stage→clear→原数据恢复→成功receipt→ctx全部资源关闭；随后独立preservation完整内容验真、完整program历史validator和载荷漂移拒绝全部通过。外部SQL/Docker/对象/SMB仍是明确有限协议，actualBusinessRestore=false，未触真实服务器或SMB。

原/副本输入保持、容器removed=true。marker换行后实际driver已提取1份1236756B诊断和5份原raw（worker840239B、receipt5174B、final11887B及state/最后invocation），不再依赖截断assert；rawlog1654381B/SHAaa0bbf27e807fc7350e3b1111c2342cd210a975311f6392b4a65cb843c50b802，JUnit412B/SHA1e5e6c575cfc5d6c8cad4a39c411d9a77544ae2e958e1e2abe1735118fb18c8d，均随report精确pin。r8原FAIL保持；后续仅既定handoff未知、stage失败、成功receipt后READY未知三闭环，各独占载体顺序运行。

handoff-unknown-green-r1/session83248实际exit0，1PASS/5deselected/0FAIL/ERROR/SKIP，outer539.765秒。真实完整捕获/归档后原SQL交接协议unknown，worker保守TERMINAL_UNKNOWN，archive/hold原件保留，未派program import/clear/原execute_empty，原保护未释放；ctx本地repo lock/leases关闭，历史validator保留unknown。原/副本输入保持、容器removed=true，完整诊断随report保全；未重跑成功或原10项。

stage-failure-green-r1/session33269实际exit0，1PASS/5deselected/0FAIL/ERROR/SKIP，outer355.313秒。真实完整保全/交接后generation已发布、ctx stage租约建立被明确拒绝；worker失败仍保留final和generation pin，未clear/execute_empty/释放业务保护；repo lock/leases关闭，原PREPARATION snapshot与已发布generation的合法失败差别由历史validator严格验真。原/副本输入保持、容器removed=true，完整诊断随report保留。

ready-unknown-green-r1/session7616实际exit0，1PASS/5deselected/0FAIL/ERROR/SKIP，outer553.093秒。真实恢复已成功、原成功receipt/native/custody/final落地后，READY发布协议unknown；worker保守TERMINAL_UNKNOWN，原成功receipt及全部被固定的snapshot/final raw不改，原epoch保持REPLACING，未释放原reservation；ctx本地全部资源关闭，独立历史validator严格承认外层unknown提升。原/副本输入保持、容器removed=true，诊断和完整worker/原件保全。

最后回归范围经父明确批准，仅test_recovery_program_native.py、test_recovery_program_protection.py、test_recovery_program_restore.py、test_recovery_program_evidence.py和test_smallapp_replacement.py五个旧消费者文件；不扩回1630，不重复r9或原10。实际retention.plan/逐delete前hold由新10已有真实分支证据，仓内没有普通retention独立旧文件，不为镜像实现另造测试。普通FULL三生命周期及阶段1/2a211唯一节点证据保留，本阶段未修改其恢复算法或源入口，不将这些旧PASS说成当前同轮重跑。

legacy-consumers-regression-r1/session20135实际exit0，五文件173PASS/0FAIL/ERROR/SKIP，outer271.562秒。新preservation字段缺省的旧producer/历史路径、原native stage/close/invocation、旧custody与旧清库准入均通过。原/副本输入保持、容器removed=true；原173项不是1630全套。最后容器已结束并通知父代理空档；不再启动任何Docker测试。

## 本机完成范围与精确剩余边界

- 已完成：prepare首停写前仓库准入与锁/唯一hold意图；真实capture/publication完整readback；同ctx/custody typed handoff；stage与首clear独立proof核验；无重复GB内容读取的持续lease；完整producer→worker→preservation/program历史验收；真实retention.plan/逐delete前hold阻断；成功/失败全部本地fd/leases/repo lock关闭。18个本阶段新增节点及既有读回/五消费者回归按分轮原件证明，不能说成同轮全部通过。
- 产品精确11文件：本表原10个接线文件及repository_native_readback.py的专用私密原件writer。新增测试4文件：handoff/runtime/producer/readback。普通SmbReadback.read原完整方法与HEAD逐字相同；无全局umask变化，原write_new默认路径保持。
- 仍HOLD：认证SAFE五具名transform/五采集保持点和新增成员尚未正式构造/双包验证；无新控制代次协议或远端安装；静态readback配置按operation独占派生未实现；来源与保全目的仓库布局尚未登记，58/59仍缺合法capture；专用角色归档尚不能从Spug普通Catalog选择为恢复点。这些是后续3A1/登记/交付边界，不能从本机有限协议PASS推成目标可覆盖。
- 历史证据不改写：r7的RESTORE_KEYERROR、r8的实际worker成功但独立history权限拒绝、微型载体setup错误和所有原RED均保留。r8原stdout补充导出有独立报告，未修改原report。四文件EOL纯格式证明保持原r1，未据此重跑行为。
- 旧正例不重复依据：本阶段未改普通FULL采集/源恢复算法、原源策略或默认SemanticCapture。其阶段1/2a的12完整会话、211唯一节点和普通FULL三生命周期证据仍有效；2b只补影响到的5旧消费者173项及SMB六项。本地有限SQL/Docker/SMB协议不代表真实业务恢复。

最终冻结由独立freeze-target-preservation-2b-r1.py逐文件compile、逐report/JUnit/诊断raw pin核对、从实际passing snapshot核当前11源码+4测试完整覆盖，并生成独占新target-preservation-2b-freeze-r1.json。完整原始driver/快照/JUnit/raw日志均保持；不提交、不清理任何其它任务或业务资源。
