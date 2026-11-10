# MAIN 目标保留采集第一阶段 TDD

### seams Linux GREEN r1：37 PASS / 3 FAIL，未通过

父实际 `capture-materials-seams-linux-green-20261110-r1.json` 为40项=37PASS/3FAIL/0skip。两项数据流失败使用正式 strict 路径 `ops/recovery/formal_data_evidence.py`，其接缝漏同步；不换测试导入，按正式 strict/SAFE 双消费者同步相同方法。另一项真实 unreaped client 的 `clientCleanupUncertain` 被 gzip.close 的 elapsed remaining 异常覆盖。修复仅在显式 observer 且原 drain 已证明 uncertain 时保留原异常与标记；默认 None 的异常转换及错误码保持。实际FAIL原件保留，不记成GREEN。

父批准后最小修复：strict DataMySql 同步三回调；dump 外层保留实际 observed primary，未确认 reap 不调用 finished、不发布压缩材料。没有修改 SAFE 构造/成员、标准算法或原测试期望。

### query3 / observation6 冻结待 RED

完整 FULL 可达调用图已记入阶段计划。query3为原 query 的 default/observed/before-refused，observation6为 endpoint/Redis inspect 各三模式，全部使用实际 Python Popen，外部语义明确有限协议。新增 API 只允许 keyword-only process_observer；默认 None 的原 run/check_output 保留。仅完成 compile 和 SHA，尚无真实 RED/GREEN；父统一 Linux 派发，禁止用静态结论冒充通过。

父真实 Linux seams r2：40PASS/0error/skip，源/宿主前后保持、容器已删，报告 `capture-materials-seams-linux-green-20261110-r2.json`。另真实 `capture-query-r1-linux-red-20261110.json` 为2FAIL/1PASS（回调缺失/拒绝不生效），`capture-observation-r1-linux-red-20261110.json` 为4FAIL/2PASS（接口缺失），均0error/skip、输入保持、容器删除。按批准范围只在显式observer分支复用现有有界_process；query保留UTF-8解码，endpoint保留原JSON/IP校验，Redis保留版本/身份/密码pin与close。默认None继续原 run/check_output，不改变普通FULL算法。新9项最小GREEN候选尚待父实际运行。

## Current Status

ready_for_closeout（本机第一阶段实现冻结，待父限定提交）。真实完整会话12项及相关211计划节点已有分轮PASS证据；完整封包/现场能力不在此结论内。范围及经验门禁继承 `main-target-preservation-capture-plan.md`，不重派失败376，不接 executor stage/switch/clear、不补登记或仓库proof、不构建/安装/远端/提交。

## 文件与入口

文件接线表已先于产品修改写入计划。新增核心 `recovery_capture_materials.py`、会话 `recovery_target_capture.py` 只供正式调用，不能用 CLI/布尔跳过来源恢复。严格来源 worker 使用共享材料方法；原 FULL try/restore/成功回执保持。SAFE 构造来自认证冻包，必须独立验证实际候选 payload，不把源码 LIGHT 导入当 SAFE。

## BDD

- BDD: candidate-delivery -> Given 当前严格来源与真实 SAFE 候选 payload；When 请求已批准的共享核心和 MAIN session；Then 两入口必须真正存在并与严格来源材料段绑定，原 ordinary restore 继续无条件执行。
- BDD: actual-custody -> Given 真 Linux 原 epoch/ctx/flock/私有原件及正式 ProtectionCustody；When 同操作开始采集；Then 原三保护持续，1/1只由专用typed租约认可，默认0/0不放宽，MinIO只按已知终态启动/停止。
- BDD: retained-failure -> Given 保护/对象/位置/预算/锁漂移或未知；When 后续阶段或close；Then 不重发、不启动旧业务、不解除保护、不伪造sourceRestored/READY。

## RED

待父按冻结测试实际执行；目前没有测试通过或失败结论。第一轮先给出候选消费接缝缺失，完整会话/材料生命周期新增场景随后在同一计划内逐批RED，不用环境缺依赖冒充业务失败。

### Linux r1：环境收集失败，非业务 RED

父报告 `capture-materials-linux-red-20261110-r1.json` 实际 exit2：Windows test-dependencies 的 rpds 缺 Linux `.so`，导入 jsonschema 报 `ModuleNotFoundError: rpds.rpds`。16项尚未运行，不能算产品RED或跳过通过。原报告/日志保留；测试和生产继续冻结，父修正独立Linux依赖载体后从相同源码快照重跑。

### Linux r2：tmpfs noexec，仍非业务 RED

父报告 Linux wheel 正确，但 tmpfs 默认 noexec 导致 rpds `.so failed to map segment`，仍为 collect 错误。相同源码tar保持、原件保存、容器已删除；r3仅调整隔离 `/work` tmpfs 为显式exec，继续 cap-drop ALL、无网络、只读rootfs，不改测试。没有将此轮记成16项实际执行。

### 原普通来源恢复函数基线

产品修改前本机只读 AST 摘要（不含行号属性）：`Runtime.restore` 为 `ee989fd4ac4c3c7bd69c7de60c7b9766f77dc37e59fe38ca28ab2b73b71041fa`；`Runtime.restore_container` 为 `e52411c5ff144018f476eeb63467a161ac029c57851954b6d748d4db2ae70af5`。共享提取不得改变两函数的正常或失败恢复语义；后续以实际生命周期回归补证，不能只凭AST称真实业务恢复。

### Linux r3：真实功能 RED

父实际 exit1，16 FAIL/0error/0skip，5.32秒。相同源码tar保持，运行内/主机文件及12 Linux wheel前后SHA一致，任务容器删除。报告 `capture-materials-linux-red-20261110-r3.json`；PRIVATE 原log24115B SHA7fd1613bde9cc7eed6d940bacab85391d5aef30eecbb9f78db1a00af89ab4603。失败均对应共享core/worker/SAFE成员/custody lease/session缺失。父批准进入GREEN，但SAFE构造/成员继续冻结，不能绕过这3项候选入口RED。

### 新流式接缝 BDD / 待真实 RED

BDD: actual-stream-observer -> Given 原严格dump/数据流算法和真实本地Python exporter；When 默认无observer或正式typed session观察实际Popen/reap；Then 默认压缩原件保持，started/child失败/超时/finished回调失败均收割同一实际client，不得伪造终态；无法观察reap时保持unknown、不发布材料、不发finished。外部SQL/Docker语义仍是明确协议单元，不是实际数据库恢复。

新增 `scripts/tests/test_capture_stream_observer.py` 8项：默认dump回归1、5种observer生命周期、data流1、无法reap1。仅编译静态PASS，尚未运行，formal生产未改。需要父统一真实LinuxRED后再审最小formal补丁。计划接缝：PrivateDockerMySql构造可选process_observer；其真实Popen/drain开始/已终态记录；DataMySql实际Popen/drain同入口；image stream由MAIN专用transport复用同observer。普通默认None不增加调用/改变算法。


### 独立流式 / 配置真实 RED 与最小实现

- `capture-stream-observer-linux-red-20261110-r1.json`：8项实际执行，7FAIL/1PASS/0error/0skip；缺 process_observer 接口为预期RED，默认实际Python dump压缩回归PASS。PRIVATE原log10123B SHA9f9286d9ad0c53c70c7e0ad8f057cfaacf70d0eadebcc35ae64c31722c50714d。
- 配置r1为18FAIL/2PASS，实际导入formal目录下LIGHT support，属于载体错误，不作strict产品RED。测试只纠正sys.path顺序并加严格__file__断言，原17负例不变。父从同一原tar替换该唯一测试，`capture-config-r2-linux-red-20261110.json` 实际20项=1FAIL缺validate_config/19PASS，0error/skip。
- `capture-image-r1-linux-red-20261110.json`：4项=4FAIL，缺save_application_images实际复现，0error/skip。
- BDD: before-dispatch -> Given原typed owner准入；When before拒绝；Then实际Popen调用数0、不写成功终态。`capture-before-r1-linux-red-20261110.json`：2项=2FAIL，实际EXPORTER_DISPATCHED_BEFORE_ADMISSION，0error/skip；冻结输入为两方法formal候选，不把后续修复字节冒充原RED。
- BDD: metadata-admission -> Given原schema/reference解析和真实本地Python客户端；When默认None/显式observer/启动前拒绝；Then默认解析不变，显式三回调与真实reap绑定，拒绝零Popen。`capture-metadata-r1-linux-red-20261110.json`：6项=4FAIL/2PASS，缺三回调和未阻止派发对应预期，0error/skip。原两默认真实解析PASS。

以上报告由父统一实际Linux隔离执行，输入前后SHA保持且容器已删除；本组件未自行Docker/远端/构建/安装。

最小GREEN候选：strict support拆为header/values/paths私有方法，公开validate_config不制造UI request；validate_job仍先原request形状、config/source关联，再原值、parent、路径，错误码/优先级不变。dump/data/image在Popen前直接调用强制before；started失败由原drain负责同一子进程kill/reap，只有已观察reap且非uncertain才finished。schema显式observer分支复用该既有有界drain，max_bytes/seconds/active budget及原UUID/warning解析保留；默认None原线程分支不动。reference原drain改为同observer包装，严格exact PrivateDockerMySql仍保留。

原stream8/image4测试的Observer仅增加before方法以符合父已批准的三方法接口；原子进程/输出/异常/收割断言保持。before2和metadata6测试原件不改。此修改是接口载体精确适配，不删除RED断言。

本机仅compile静态检查，尚未宣称GREEN。MAIN session真实合法正向/完整普通FULL生命周期和SAFE三个成员入口仍待后续独立验证；目前明确不接覆盖执行/不发布仓库保留证明。
# 2026-11-10 完整会话与来源生命周期候选

父实际 Linux `capture-materials-seams-linux-green-20261110-r3.json`：49 PASS、0 failure/error/skip，源/宿主输入保持、容器已删。严格 Redis passwordPin 单独实际 RED 为 1 FAIL/1 PASS（有效配置被严格副本拒绝），已只同步已有四字段合同并增加原 pin 格式核验；不移除无密码旧路径、不进行无认证重试。

BDD：Given 正式临时 owner/目标 capture 配置、原预约、真实 epoch/ctx/flock/三个保护及真实 Python 客户端进程；When typed MAIN 准备后原 quiesce、共享原 FULL 材料采集；Then 原 SQL gzip/schema/data/物理树/对象复查/Redis 和 images 实际执行，最终 MinIO 停止、SQL 1/1、scheduler paused、原保护文件不变，材料 HOLD 而无 sourceRestored/READY/覆盖许可。

BDD：Given 同一输入；When dump 非零、原 fence 漂移或原绝对预算耗尽；Then 保留 FAILED_RETAINED，close 零外部恢复/释放/重发。Given 普通 FULL；When 真实材料成功、dump 失败或原服务恢复失败；Then 必须执行原来源恢复路径，失败不得伪造 sourceRestorationPin 成功。

新增 `test_recovery_target_capture_session.py` 七场景，仅外部 Docker/SQL/S3/Redis/health 为有限协议单元；实际 Popen、文件、压缩、正式采集算法、ctx、预约、物理锁和 custody 均真实。它不是现场数据库或业务恢复证据；三项 SAFE 封包合同仍明确 HARD HOLD，未改标准构造/成员。当前只完成静态 compile，等待父从冻结源码实际 Linux RED。

已识别必须的真实账本接缝：mysqldump 的 before intent 先于 Popen，期间 guard 发出的原保护只读调用会被旧 ctx 的未结规则拒绝。父批准仅同 session、实际活 exporter、唯一外 token、固定 guard 内有限原角色/命令摘要白名单的嵌套读取；任意查询/写、第二 stream、外 ctx/PID、未创建或已 reap 进程均保持旧拒绝。不得假结束 exporter 或跳过 SQL 屏障。

### 完整会话实际 Linux RED r1 与精确载体修正

父原session59933已实际终态：`capture-session-linux-red-20261110-r1.json`，9 tests = 7 FAIL / 2 PASS / 0 error / 0 skip，29.719秒整体。4个MAIN用例都准确失败于`PROGRAM_CAPTURE_CONFIGURATION_ADMISSION_NOT_IMPLEMENTED`，属于实现RED；Redis2通过。普通FULL3例在原Runtime.preflight的`MINIMAL_TOOL_UNAVAILABLE`前置阻断，其后两项无source-restoration文件不算恢复算法RED。

只读追踪父冻结命令发现：`/tmp:rw,nosuid,nodev`未显式exec，pytest原tmp_path在/tmp；真实docker/ip脚本虽chmod700，仍被原os.access(X_OK)拒绝。下一父runner仅加`--basetemp=/work/pytest`使用既有exec/work，不放宽产品门禁、不mock os.access、不改变输出作用域。

冻结测试的正式输入纠正：为原target补充两个实际私密MinIO根凭据pins（仅有限协议fixture字符串，不含现场凭据），与S3 credential原件逐项绑定；补原writer检查所需EVENTS和Redis CLIENT LIST的有限响应，仍由真实native调用账本记录。7条原业务断言不削弱、不跳过共享材料算法、ctx/custody或来源恢复。原RED测试SHA0ac5bdb81363f9ab4b140f3c34b03d57b91b0446d10f81a0492e0ab48e6f3052保留；纠正后20280B SHA dfffc8c5f330aebd77a2e9ae554d2e8128b3968ec0eae59efb1be9b7ad3e7609。

### 最小GREEN候选冻结，尚未宣称通过

MAIN实现采用原FULL材料核心、原配置完整验证、原ctx/物理锁/预约和typed custody。prepare先核旧target/数据库/镜像/全部writer/挂载/凭据/归档作用域，建立独占私有session；capture只在原quiesce后获得1/1租约，实际MinIO启动→语义/SQL→停止/物理树→启动/对象及Redis复查→停止→MATERIAL_COMPLETE HOLD。无sourceRestorationPin、无handoff成功、无READY/覆盖许可。失败记录保留，close只关闭本地能力，不恢复业务或释放原保护。

原token只由正式完整drain/reap后的finished结束；已poll退出的有限drain尾部仅核本地ctx/锁/预算/文件，finished随即强制严格0事务和完整保护复核。真实存活mysqldump期间仅允许force_guard原命令摘要集合，不以mutation=False或phase通行。没有提前成功终态。

本机仅`compile`静态exit0，当前冻结源：target_capture 24794B/2cb7f56e68df6a5f321510b0cbf8596035e40ee6128d61652dd2ebbb7df10d2e；capture_materials 13349B/765dc9879bf6e83708e8fc043b8b64e0c2209c48c2eaa782a20e54b79c49e8ac；program_native 18714B/a4e76f8c492cf6838b85a3f005fe10de1e14b54a69c575549af27817f1be4a27；main_target 43363B/ffb60985e147de685926f84e04b476a4a76738182038955e398a7b7e7a3609a9；support 26335B/5b081fd2a7a475f7c2047e11dedf36f4719eee08ee8ad6bcc6af0c72a8b03348；worker 26171B/51b4db40cc54714c8c52e204b07570b2b7df98058109505cb943c4d13317a756。

父统一下一真实Linux GREEN及旧回归；本组件不自行派发测试。实际SAFE三成员/完整语义合同保持HARD HOLD，未改包成员/standard_fixes，不称目标可覆盖。

父尚未创建下一snapshot时，静态按原`SemanticCapture.queries`补齐三种明确外部SQL协议：SHOW TABLES、DESCRIBE唯一key列、SELECT HEX空表响应；原正式查询/解析照常运行，未mock材料成功。该新fixture最终20541B SHA7c44dd51751f93e14ba6340c1ac1c05271e65bd418810f470d9bd14979d3f708，compile exit0。上一20280B仅是中间静态候选，没有测试通过记录；全部生产SHA保持。

### 完整会话 Linux r2：普通FULL生命周期已通过，MAIN仍失败

父实际`capture-session-linux-green-20261110-r2.json`终态为9项=4FAIL/5PASS/0error/skip，输入未变、容器删除。普通FULL成功/dump失败/来源恢复失败3项以及Redis2均通过。MAIN4项在prepare调用原verify_services/verify_storage时因`REPLACEMENT_PROTECTED_ROOT_REQUIRED`失败，尚未进入dump，不能称MAIN GREEN。

根因是新fixture迁移owner.operationsRoot后未同步冻结storage.protectedRoots；只追加真实新capture-operations根，保留所有原根/挂载/目录身份，不放宽verify_storage。该修正属于正式输入纠正，不把旧fixture失败称产品算法RED。

新增BDD：Given同一真实ctx/flock/custody和等待本地release文件的实际Python dump；When有限force_guard首SQL前放行dump，并以waitid(WNOWAIT)确认真实退出但未reap；Then正常材料仍应完成，原token只能由原完整drain的finished固定，后置事务严格0。当前每嵌套begin/lease的主动poll会提前reap并拒绝未结调用，测试先交父实际RED，生产保持冻结。

另两项回归BDD：活dump在force_guard外的任意SQL/写命令/第二stream均在实际外部协议派发前拒绝；真实已reap但drain尚未finished的尾部仅做本地ctx/锁/预算/身份校验，token仍pending，正式finished之后才重启严格外部复核。不是任意phase特赦或以未poll等同仍存活。

新session10项测试24806B SHA10760e3f85dad7fae161689916c2130a50ad81cfb4e60ba60147c46229d491fb，compile exit0。父统一实际Linux10+Redis2；生产仍保持上一候选SHA，竞争尚未修复。

### Linux r3：新增observer过度force检查导致数据deadline，未到竞争

父真实`capture-session-linux-race-red-20261110-r3.json`12项=4FAIL/8PASS/0error/skip，96.79秒pytest/约110秒整体，输入保持、容器删除。4项在SOURCE_DATA_BEFORE原observe_data/schema后置报`FORMAL_DATA_DEADLINE`，未到dump，不能作为退出竞争RED。

只读追踪确认我新增observer对每个只读schema/data/query的before/finished都force_guard，使每条查询重复执行完整服务/网络/存储/三保护/SQL/Redis检查，而原runtime.protected已有0.5秒节流。父批准仅修此根因：每次仍执行包含ctx/锁/预算/文件的guard；固定正式dump前/后及原阶段边界仍force完整核，非dump使用原默认节流。不改fixture的dataSeconds10/workSeconds60，不实现waitid竞争修复，独立归因下一轮。

该唯一生产候选`recovery_target_capture.py`24828B SHA2561dd50a619945efa1d1bc47003e7e45696270353e6c1e783d9b446619ffd28，compile exit0；新session测试及其它源SHA保持。尚无本轮GREEN结论。

只读原r3 XML进一步限定证据：`dump`失败保持负例列PASS（13.983秒），但当前通用异常断言不能证明已到真实dump；其余4个材料正向均约14秒止于SOURCE_DATA_BEFORE。因此不把这条PASS称导出失败覆盖。最终应精确补phase与真实非零dump终态断言；父当前单变量轮次测试保持不动。

原普通来源`Runtime.restore`/`restore_container`的本机AST复核仍与事前摘要完全相同；r2/r3普通FULL3条实际生命周期均通过，这同时保留代码结构与真实有限协议执行两类证据，不等于真实服务器业务验收。

### Linux r4：测试注入点死锁，非产品结论

父外层180秒超时、无JUnit；只读检查确认新reaped-tail用例在observer.started中等待子进程退出，但原drain尚未发送stdin，子进程在stdin.read等待EOF，pytest则在waitid等待子进程，属于新fixture死锁。父保留公开timeout/空原log/状态并精确终止任务隔离容器，无远端动作；removed最初观察false待父最终复核，本文不先称删除成功。

父批准仅纠正注入点：竞争与tail均必须实际`process.stdin.closed`，该状态只能由原正式drain写完并关闭stdin产生；不手工发送/关闭stdin、不替换drain。waitid改WNOHANG|WNOWAIT循环，绝对截止为min(原budget,当前+5秒)。tail在原protected/guard实际调用处注入，started不阻塞等待。原token未结/零外部调用断言保持。

同步加强dump失败用例必须到DATABASE_CAPTURE，且真实ctx存在actualExitCode9/FAILED_RETAINED终态；不再允许任意早期FormalSnapshotError冒充dump失败覆盖。新测试26271B SHAd89842a477688d14962353a1ab5e5fd3748f6bd40f1253c85559031e364cb8e4，compile exit0。产品仍24828B/2561dd50...保持，未实现waitid竞争修复，父下一轮实际RED待定。

### Linux r5：完整MAIN通过，真实退出竞争RED

父实际12项=3FAIL/9PASS，121.19秒，输入保持、任务容器删除。MAIN完整材料成功、dump实际exit9/fence/budget三失败保留、普通FULL三生命周期及Redis两项全部PASS。完整MAIN结果仍是MATERIAL_COMPLETE HOLD，不是仓库保留证明/目标覆盖准入。

竞争用例首次真正进入dump，并在完整guard的verify_services→database_uuid→begin_invocation报`PROGRAM_NATIVE_INVOCATION_UNSETTLED`：dump实际退出且尚未被原drain收割，内部主动poll提前reap导致同一次有限保护读取被旧未结规则拒绝。这是waitid最小修复的实际产品RED。outside-guard/reaped-tail已越过dump边界，之后在SOURCE_DATA_AFTER的schema catalog触发10秒`FORMAL_DATA_DEADLINE`；这两条不是边界行为RED。父仅批准新fixture的dataSeconds10→30，workSeconds60和ctx120原样，不改产品默认或现场策略。

BDD：Given同session实际Popen、唯一未结dump token和已冻结的原保护只读命令集合；When guard入口证实child仍RUNNING而在同一次有限guard中退出；Then以实际waitid(WNOHANG|WNOWAIT)观察EXITED_UNREAPED，不reap、不发布终态，仍只准该次guard的原有限命令，scheduler立即使用严格0事务。入口已退出仅本地检查；外部PID、REAPED、第二stream、guard外查询/写和任意命令保持拒绝。原drain完成后唯一finished才结束token并强制原严格0/全保护复核。

父已批准窄实现：仅lease新增真实child状态观察、session记录一次guard的实际exporter身份并使用该状态；原observer终态与普通FULL路径不变。当前开始最小GREEN候选，未自行运行测试、构建、远端或提交。

候选已冻结并由本机`compile(raw,path,'exec')`静态实际exit0：`recovery_program_protection.py`24241B/bba9c672d402d9af81934a36f6ca98b69e145ca331d16fdcccf595ae899381fb；`recovery_target_capture.py`25285B/1ecfcafcf8388aa9604b5ddc326b00a8ca2f3711844299fe2288a6ae1386fc9b；session测试26271B/cda4ff5aa30d83aa6de5c2aa952bcee47ca8a86153bb78f52ca5ff94e67fc2c0。静态编译不是GREEN测试。父独立待运行：`PYTHONPATH=ops/backup_engine/formal:ops/recovery:scripts/tests python -m pytest -q -ra --basetemp=/work/pytest scripts/tests/test_recovery_target_capture_session.py scripts/tests/test_capture_strict_redis_config.py`，沿既有冻结tar、实际Linux依赖、网络none和输入前后核验流程。其余产品/测试保持；三SAFE候选成员合同仍HARD HOLD。

### Linux r6：完整会话12项GREEN

父独立正式报告`capture-session-linux-guard-verify-20261110-r6.json`实际12PASS/0FAIL/ERROR/SKIP，pytest169.05秒、outer198.234秒，输入前后不变、任务容器removed=true。真实dump退出竞争、guard外任意查询/写/第二stream拒绝、已reap尾部本地检查与原finished唯一终态全部PASS；MAIN完整材料HOLD、dump实际exit9/fence/budget失败保留、普通FULL三生命周期、Redis两项均保持。

冻结快照与rawlog完整pins以父正式报告为准（消息摘要分别93435483…4cdd、36930e02…e5af，不将截断摘要冒称完整SHA）。当前产品/测试继续冻结；父下一跑计划内11文件相关回归。当前仅写第二阶段设计，不开始归档/handoff/clear实现；三SAFE成员合同及真实封包/目标登记/完整仓库proof仍HARD HOLD。


### 最终分轮回归与冻结（2026-11-10）

父r8真实211项=195PASS/16FAIL；其中archive17因误用LIGHT有1PASS/16FAIL。逐项解析r8/r9已pin原log内JUnit，取得r8的211个唯一nodeid目标集合，archive17一律只选r9认证SAFE的同nodeid PASS（不用LIGHT偶然PASS），其余194逐个只选r8 PASS；核交并集准确覆盖原211且无缺项。r9另有独立generation symlink1项PASS，明确排除目标全集外，不混入覆盖。逐节点证据见target-preservation-stage1-node-coverage-r1.json。不是211同轮GREEN。原r7/r8失败均保留。引用原件：capture-components-linux-regression-20261110-r8.json、capture-archive-scope-linux-20261110-r9.json。完整MAIN/普通FULL/竞争12项继续引用r6，不重跑。

本阶段14产品与11新增测试精确raw SHA见target-preservation-2a-freeze-r1.json的phase1Prerequisites组。阶段1不是新增2a的三产品/一测试；两阶段分开提交范围由父决定。保持普通FULL恢复、真实ctx/flock/custody与原绝对预算；当前无正式SAFE成员/完整封包、目标登记、handoff或首clear授权。
