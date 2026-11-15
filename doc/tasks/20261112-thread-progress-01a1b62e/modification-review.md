# 开发修改独立检查

## Current Status

in_progress：已派发并获开发线程确认，等待修改完成后核验。

## 授权与范围

用户于2026-11-14要求通知“查找未登记目标的含义 (3)”进行前轮四项修改，并由本对话在修改后检查。目标threadId：01a1b62e-c0a4-7da2-bed2-9b4a58188636。当前仅新数据、已有新FULL/I1/I2到测试58，旧兼容与镜像/对象索引/构建架构扩展后置。

## 验收项目

| 项目 | 独立检查要求 | 当前结论 |
| --- | --- | --- |
| 保全失败根因 | 原异常/阶段/系统错误与实际修复对应；最小失败复现及修复验证；诊断增强不能替代修复 | 未完成，原OSError根因未知 |
| 重复校验 | 同轮复用边界明确；跨轮变化失效；保留内容、目标身份、停写与保护检查；测试和实际调用/读取指标支持 | 已审同轮边界与Linux回执；实际查询局部改善，整体吞吐尚待真实恢复 |
| 失败处理 | 覆盖前无业务写入有实际证据，正确恢复原状态；覆盖后或未知不得启动半恢复业务；历史失败保持 | 容量提前拒绝和局部严格消费者通过；旧缺件现场接管与真实规模仍在开发 |
| 源码与实际包 | 最终提交、变更文件、包成员/摘要和安装身份匹配；不夹带旧兼容或无关改动 | 98cbfec源码及52d0b1e实际包已核；七成员差异和容量入口一致，未安装验收 |
| 新I2到58 | 同一原生operation真实成功，数据库/附件/引用/服务/页面一致；记录阶段耗时和停写时长 | 尚无当前成功证据 |
| 收尾 | 规定融合结果验证、任务自有构建worktree及控制台归位，区分ready_for_closeout与completed | 待前述验收 |

## 跟踪记录

- 发送工具确认目标threadId；wait快照revision16中开发方明确确认按四项收敛并集中审阅摘要，未宣称完成。
- 本轮观察integration-20261112-r5 HEAD=9614f9f，新增未提交生产改动为recovery_main_target.py、recovery_target_capture.py、recovery_minimal_worker.py；前两者为同轮查询去重，后者为异常因果诊断。仅初步读取，最终审查以交付提交和实际包为准。
- 本对话不修改目标产品、不发起新的恢复，不创建定时自动化；在当前对话跟踪并核证据。
- 首份开发摘要和实际Linux回执核对：r3共82项、零失败/错误/跳过，原容器集合不变；最新修改随后提交a440513。去重代码保留原过滤条件，Redis CONFIG/ACL/CLIENT仍实时读取，观察退出/身份与配置改变/失败或pending调用拒绝。该结论仅限已读逻辑与回执，不代表实际包或业务恢复验收。
- 审阅反馈1已传达并获回应：mutation应区分停服务、只读开关和启动MinIO与真正数据库/附件覆盖。现有记录尚未发现覆盖，但终结回执缺失，不能宣称历史调用完整或授权释放保护。要求明确实际未知范围和最小解除条件。

## 待修复或证明的发现

- P1：长流程证据容量可能阻断失败终结。recovery_program_restore.py:16固定NATIVE_LIMIT=64MiB；:127的snapshots先将context.snapshot整体写盘，失败即到不了后续保护证据/终结回执。:43的_write_once明确拒绝超限；成功和异常路径均依赖snapshots。开发已有执行日志记d26已见命令汇总至少78,151,751B。不能由此断言原始OSError原因，但需要证明该容量边界不会再次使收尾失效。已反馈要求精确复现并在现有正式机制内解决或保留阻塞；不得靠无边界增大上限、删原始记录或伪造终结凭据解决，不要求通用ledger重构。
- 截至a440513，上述容量/终结路径未改变，新增worker异常诊断只改善错误可见性。当前总体检查不通过，等待必要后续修复、实际包和新恢复证据。

## 用户再次询问时的阶段判断（2026-11-14）

- 最新快照revision98仍inProgress。已提交a440513的去重/诊断及c888737的实际标准包诊断helper遗漏修复；修正后c66f28c发布分支包108项通过，未安装；容量准入修改还未提交，严格失败回执消费者验证尚未通过。
- 容量准入在下一条命令意图落盘和命令派发前保留终态空间，方向合理；提前安全停止只解决不可记录的新调用，不能保证当前实际规模可以完整恢复。当前失败载体18 PASS/1 FAIL发生在消费者要求的正式操作路径文件缺失，不能将局部测试判作完整修复。
- 原d26五个已见mutation是停前端、停后端、停MinIO、设置数据库只读及启动MinIO，尚未发现数据库导入、代次切换或附件覆盖；终结材料缺失仍阻止证明历史调用完整。最新摘要更正session/publication均为OSError，顶层FileNotFoundError；具体原errno/路径仍未知。
- 结论：全量加连续增量及同源父链模型有实现依据；当前去重、实际包验证和容量前置保护是合理修正。恢复系统尚未形成可交付的失败闭环：严格拒绝不确定现场合理，但一次异常导致终结材料缺失且没有正式接管路径，是必须解决的设计缺口。日志容量修复不能补回原历史证据，也不能以强制释放保护替代处理。
- 仍无新I2到58完整成功和整体耗时证据，独立验收继续in_progress。当前问询得到阶段判断，不标总体完成，不把已修打包缺陷继续写成现存缺陷。
- 独立只读包验证：实际c66f28c标准tgz大小/SHA与报告一致，逐一核156个成员摘要全部通过，AST确认worker含_retain_failure_chain函数。未执行包代码或服务器动作；该包不含尚未提交的容量修复。

## 再次派发后的检查（2026-11-14）

- revision101：开发方确认完成新流程真实规模恢复，并补齐旧d26缺失终结材料的正式处置路径。保留旧失败与原件、未知历史不能变造为未覆盖；未新建恢复操作。
- 98cbfec已提交原生证据容量准入；Linux r4为150项通过，包含保护前、已停服并安装保护后的完整失败回执消费者验证。该回归是本地协议集成，不能替代真实服务器恢复。
- 已独立读提交：真实command/import/stream入口在intent写入前核容量；每个pending预留现有4MiB文档上限，finish用实际大小回收额度，同轮不反复编码全历史；总量64MiB、原件引用2MiB。正常容量拒绝的终态路径已获得局部证据，pending stream全生命周期、所有非native聚合以及当前规模是否能完成仍未证明。
- 等待新容量修复实际包及旧失败处置实现。c66f28c旧候选的既有验证继续有效，但不用于冒称新代码已打包或安装；总体检查保持in_progress。
- 新候选52d0b1e的独立只读检查通过：899033字节，SHA256 f6767cf1f1d5df9335acc826df1b72d5f1e7977331700c552882cdb0e0047315；156个文件摘要与manifest一致，相对已安装旧版仅七个预期成员改变。AST核native/target_capture及data的command/import_sql与发布源码一致，容量派发入口确实进入STANDARD。证据见package-review-52d0b1e.json；未执行包代码，尚不代表安装或恢复成功。

## 四万多条命令的原因核对

- 独立读取原2ac4b37实际STANDARD包代码：formal_capture_semantics._read_content在对象读取前及每个1MiB块读取前后调用guard；MainTargetCapture.guard非force时只在距上轮完成不足0.5秒时省略远端检查。stream开始和完成使用force=True。
- 一次完整guard串行调用verify_services、verify_runtime、application_runtime_inputs、verify_writer_quiescence及保护lease.verify；多个函数再次inspect同一服务，旧writer校验分别执行两条SQL，Redis继续查询身份、CONFIG、ACL、CLIENT，另有网络、调度器及已发布端口规则核对。小粒度数据回调与整套远端检查耦合，同轮重复采集进一步放大命令数量。
- 既有d26-command-distribution-r1统计独立重算：43922条native、26种argv指纹，其中18种重复指纹包含43914条命令；全部已见终态SUCCEEDED。记录里的命令累计耗时11822.213371秒（约3小时17分），是命令计时累计，不能直接冒充完整壁钟耗时分解；也不说明这些相同命令全部可取消。
- 更正表述：capture-000754.bin是捕获临时文件序号，不能作为754个附件成功恢复的证明。该阶段仍是覆盖前保全；现有704内容文件还涉及内容去重。此次解释不改变历史覆盖完整性未知及原OSError原因未知结论。
- 结论：主要放大来自检查调用粒度与重复采集设计，不能简单归因附件数；新候选已解决部分同轮重复，但完整5916对象与失败终态预算仍待证明。用户追问已答复，原修改后独立验收继续。
- 用户再问是否已修复：即时核integration HEAD仍98cbfec，产品目录无未提交变化；guard:391仍0.5秒，块级回调未改。判断为部分修复，尚未解决或验证大量轮次开销。revision116确认仅在评估分段证据和旧现场正式接管；分段容量处理不能替代性能修复。已再次要求两项分别交付：降低冗余调用并以同工作量计数/耗时验证、有界证据保证正常和失败收尾；新包未安装/完整恢复未验收。

## 测试服无法恢复的替代路径咨询

- 用户仅举例询问方案，未要求执行切服、清空或重建。推荐先考虑保留旧现场、在独立空目标恢复、验收后切换测试入口；宿主机正常可用隔离新实例与新数据卷，宿主机异常则另用主机/虚拟机。必须验证独立存储与空目标，不能重用旧实例数据卷或把新容器误称空环境；当前程序是否具备这条正式入口尚未验证，不能承诺现成可执行。
- 真正独立的空目标可免于对旧实例执行原地覆盖及其覆盖前保全流程，但不能省略源链完整性、数据/对象共同恢复点、恢复后内容和页面验证，也不能消除共享恢复代码中的缺陷。旧失败现场继续隔离保留，不因新目标成功就虚构旧任务成功。
- 若增量链不可用，可选仍完整可验证的更早共同恢复点（例如全量或FULL+I1），明确放弃该点之后的变化；不得跳过缺失I1直用I2，不得拼接不同恢复点的数据库与附件。
- 若原数据源仍健康且用户只需重建当前测试环境，可另作新的完整备份并恢复到空目标；这是新恢复基线，不证明原I2链已修好，也不恢复已丢失历史。此为备选设计，不授权本轮访问源服务器或重复已有成功备份。
- 若只有自动编排故障，可制定受控的独立恢复流程消费已经验证的数据、对象、配置和镜像；仍要遵守实际格式和增量顺序，先完成隔离验证。不是删除锁、修改成功状态或忽略错误的旁路。若没有任何有效备份且原数据源也丢失，不能保证找回缺失数据。
- 本轮只核本地恢复约束与已有审阅事实；原厂网页查询两次502，未引用未取得的网页作为证据。咨询结论与原修改验收分开，原验收保持in_progress。

## 现有全量包与空目标重建能力核对

- 当前新链全量为smallapp-3c2395ff88bd474e9fc007649565b848。公开证据automatic-main-r7-20261110-full-ui-terminal.json记录History377、FULL、operationState=SUCCEEDED；local-terminal-r7同时记录原result.json的SUCCEEDED及归档整链读回结束。后续已核I2成功摘要明确以此为baseFullOperationId。旧373全量不冒充本次新链。
- 已安装2ac4b37实际STANDARD确有空目标分支：recovery_minimal_runtime.py:422–427在目标未启用replacement时调用execute_empty；:487核fresh_target，之后全量数据库、对象链、跨存储一致性、Redis重建及应用启动。一般计划器recovery_plan.py:296支持REBUILD_EMPTY，:362拒绝把空目标路径套用覆盖保护材料。由此补充上轮未知：底层空目标恢复能力已存在，不能再说完全没有实现。
- 材料合同包含数据库SQL、对象内容/物理载荷、原程序镜像及恢复元数据；实际STANDARD recovery_capture_materials.py:180生成original-application-images.tar、:206生成database.sql.gz。凭据有独立引用且:167拒绝作为普通material归档，不能把备份当作包括凭据/操作系统/宿主机配置的整机镜像。具体新目标必须准备和登记运行环境、隔离数据卷、目标身份、网络与安全配置和可用凭据。
- 当前真实UI预览证据main-three-target-preview-startup-r3.json确认的是既有MAIN三服目标；当前MAIN程序装载/派生/保全入口属于replacement流程。代码有execute_empty不证明当前MAIN全量包到任意新实例的程序部署、配置映射和真实登录均已打通，未找到该新空目标验收证据，故不宣称现在即可一键换机恢复。
- 判断：现有全量是空目标重建可复用的备份基础；若仅恢复全量对应时点，不需要后续I1/I2；若要到I2时点仍需完整连续链。无需因旧目标保全失败就认定全量包不可用或重复备份。下一验证应是登记独立空目标并用该全量实际恢复，核数据、附件、程序和页面；本轮仅核能力，没有执行或改派该验证。旧失败现场保持，原I2→58修改验收仍未完成。

## 增量备份点到全新机器的能力结论

- 独立读取实际2ac4b37 STANDARD：recovery_minimal_plan.selected_chain:53–122从选中点递归parent，强制完整父前缀、同源/同代次、日志结束位置与下一开始位置连续，并校验对象链。选I2会得到FULL/I1/I2，不是只导入I2文件。
- 当前新I2成功摘要已核：e7b668的parent为20a1bb、baseFull为3c2395、chainDepth=2、SUCCEEDED_VERIFIED；其restoreDispatched=false明确仅为备份成功证据。
- 空目标入口execute_empty接收同一个selected_chain，按顺序先full_database再incremental_database，随后恢复对象链和跨存储一致性、Redis与应用启动。因此数据引擎已具备在空目标重建到增量点的组合能力，不要求目标预存旧业务数据。
- target_configuration:125–150仍要求已登记目标身份、Docker/network/services、隔离数据路径、程序配置和secrets；新机器并非任意裸机。完整全量及所有中间增量、对象内容和所需元数据必须可读，不能跳过缺段或只搬增量包。
- 当前MAIN包到一台全新机器的部署/路径与凭据迁移、真实恢复和页面验收尚无完整成功证据，不能将底层组合能力说成已交付的一键换机功能。本轮仅回答能力边界，不扩大原I2到58任务，不执行恢复。

## 开发线程当前方向核对

- 即时wait revision120、最新实际对话和review-summary交叉核实：主线仍是已有新FULL/I1/I2恢复到测试服58原MAIN实例。最新消息为旧d26三个已知进程退出、epoch仍REPLACING，先保留历史未知、完整保全当前目标，再交接一次新恢复。
- 当前并行工作：A有对象/字节/时间边界的保护读取批次、块级本地检查与批次前后远端检查、同轮SQL合并和调用/耗时验证；B原生证据有界分段和严格消费/失败收尾；C旧d26正式隔离接管与受限升级。尚未安装新候选、尚未完成真实新恢复。
- 与用户新机方向共用的是完整父链、数据/对象一致性和可扩展恢复执行；区别在于目标生命周期。现主线保全和覆盖既有58实例，新机方案需独立空目标环境准备、配置/凭据/路径迁移、恢复与入口切换验证。当前摘要及最新消息未将后者列为交付验收；不能把一次新operation理解为一台新机器。
- 判断：数据链方向一致，但开发重心尚未转到全新机器恢复。此前新机讨论是替代方案与能力咨询，本轮只核实，无新改派；不新增新目标或扩大原范围。


## 已有测试服原地恢复方向与剩余重复检查（2026-11-14）

- 范围与版本：本轮只读即时revision122、已提交release lineage 52d0b1e相关调用链和既有私密统计。已安装仍为此前核实的2ac4b37；未取得新包安装和新I2到58成功证据。主线为已有58原地恢复，未改派全新机器。
- 方向判断：核完整新备份链、停止写入并持续保护、一次可恢复的当前状态保全、覆盖导入FULL及连续增量、恢复附件并校验引用、启动后核业务，适合保留现有测试环境身份且需要回滚的目标。当前保全是回滚策略，不能说是增量算法固有要求；用户取消旧格式兼容不等于授权丢弃现有测试数据。旧d26未知现场需最小正式接管，不能伪造历史、删保护或无限追加通用平台。
- 明确优化点1：recovery_replacement_storage.py:496–507全宿主容器清单后完整inspect；普通消费者后续只使用Id/Mounts，特殊inactive另需State/ExecIDs/Path/Args/HostConfig/Config等字段。独立按argvSha256连接既有统计，459个容器的完整inspect执行1761次、累计输出10,018,699,360B、累计命令耗时968.261169秒；加清单及三个volume检查累计2469.101048秒，约41分9秒。此为检查命令累计耗时与输出量，不是备份体积，不可当作全部墙钟时间或可节省时长。建议按角色返回必要字段、同轮复用，不能删掉非目标/已停止容器的共享卷覆盖检查。
- 明确优化点2：recovery_target_capture.py:375–421完整guard仍按0.5秒节流并受对象/块级调用触发；只压缩单轮命令数仍不足。当前计划的对象数/字节/时间有界批次、块级本地检查、批次前后及状态变化/破坏性步骤前完整检查是合理方向；必须证明批次内写入防护持续有效，不能只延长时间间隔或跨变化复用旧结果。
- 明确优化点3：同轮guard的verify_services→verify_storage:535在storage v3下，与application_runtime_inputs→_application_runtime_inputs:502在MAIN v2下重复verify_preserved_mounts；每次均调用observe_preserved_mount。此为条件化代码路径重复，可绑定同轮观察复用，配置/身份/阶段变化须失效。全宿主inspect也覆盖了同轮已经检查的目标容器；复用需确保所需字段和当前有效性。
- 可合并传输而不删语义：verify_services:177独立数据库UUID；MainMysqlScheduler._state_flags:29、34分别查询状态与数据库列表，verify:97另查scheduler worker。按同轮统一观察可减少连接/命令，保留数据库身份、范围、只读状态、事件和事务校验。Docker info当前仅使用ID，也可投影字段，收益优先级低于整机inspect和guard频率。
- 已修项不重复计错：候选_CaptureServiceObservation已将目标角色inspect合并并在同轮复用，writer process/event count已合并为一条SQL；这些尚不能证明整条恢复已提速。Redis CONFIG/ACL/CLIENT等不同语义检查不能只因使用同一服务就当重复删除。
- 必须保留：目标及实际可写目录/挂载身份、受保护目录不重叠、其他容器共享存储检查、源链及内容完整性、真实停写与持续保护、覆盖边界重验、最终数据库/附件/引用及页面验证。已有完整读回的有效证据应复用，不追加相同输入的独立全读。
- 已按原授权将以上具体位置与条件反馈指定开发线程，工具确认投递；不等于开发已经修改或验收通过。当前审阅结论：技术方向合理、执行粒度和采集量过重；正在实施的优化方向合理，最终仍待实际安装和真实I2到58恢复、阶段耗时/命令数/读取量证据。原独立验收保持in_progress。


## 再次明确修改授权后的跟踪（2026-11-14）

- 已向原threadId发送四项明确实施要求：全宿主必要字段与同轮inspect合并、受保护批次、同轮挂载观察去重、数据库查询传输合并；保留原新I2到58最小范围和真实验收。工具确认投递；revision124–126仍inProgress，不将发送当修改完成。
- 读取新i2-test58-final-acceptance-plan：明确完整FULL/I1/I2三步、真实Spug单次请求、严格新终态与数据库/对象引用/服务/实际登录页面；旧固定两步验证脚本不直接用作此次成功证明。计划无实际新恢复结果。
- 独立查看相关任务工作树后，e958476已在unresolved-takeover-dev-r1提交基础合同与预约交接；native-scale-dev-r1尚有分段生产/消费未提交修改，受限installer尚未集成。主源码98cbfec、发布线52d0b1e不变。此为阶段快照，非最终交付集合。
- e958476只读初审：授权/preview保持oldOutcome=UNKNOWN、historicalCompletenessProven=false、restorePermitted=false；只由真实请求绑定新operation，消费目录排他、原物理锁与host mutex下原子替换active，无清空窗口；不补写旧成功。当前静态材料不能产生_LiveAdmission，实时观察、epoch接管、受限capture及完整保全/恢复接线明确仍未完成。未发现所读基础部分直接绕过覆盖权限，但不得将此解读为整个接管安全验收已通过。
- 独立读取private/unresolved-takeover-core-regression-core-r1/result.xml：130 tests、0 failures/errors/skipped，4.658秒；result.json exitCode=0、containerRemoved=true。只证明已有局部Linux回归回执，不是本对话重跑，不证明真实新包安装或业务恢复。原独立验收保持in_progress。

- 热路径草稿继续审查：按角色投影、同轮挂载复用、集中数据库观察已有实现但尚待主流程/实际STANDARD接线；已反馈单对象16MiB scope可能无法摊薄大量小对象的完整检查，要求以实际分布证明或按授权采用跨对象有界批次。当前58 inactive/preserved均0，该条件分支去重仅合同收益。分段首次联合回归74PASS/1FAIL，原失败保留，未作整体通过结论。
- 最新revision130：开发线程正完成剩余接管验证和安装准备；最新实际命令提取58当前恢复控制配置、引擎路径与版本pins。局部性能通过为对方最新进度报告，当前未据此宣称完整性能、安装或真实恢复成功。此前130项接管基础回归已独立核证，完整功能仍待交付，原审阅in_progress。

## 原地恢复与重复检查再次复审（2026-11-15）

- 版本与证据边界：即时revision131至133仍inProgress。本轮主要审阅私密根目录prod-incremental-to-two-targets-20261106下capture-release-integration-r1，HEAD a327d21加正在暂存的集成修改；integration-20261112-r5仍98cbfec，已核实际封包52d0b1e、既有安装2ac4b37。不能把当前暂存源码视为最终封包或服务器运行版本。审阅端不执行服务器操作和恢复。
- 方向：现有58实例核新FULL/I1/I2完整链、持续停写保护、一次完整当前状态保全、导入全量和顺序增量、恢复对象并核引用、启动和页面验收，符合用户最小目标。保全服务于现有目标的可恢复性；取消旧格式兼容不等于允许丢弃现有测试数据。旧d26须保留未知事实并做最小安全接管，不能无限扩大成通用历史兼容或新机部署项目。
- 已有实质改进：全宿主容器按角色投影并同轮复用；五条SQL同连接保持语句边界（直接合并成单条SELECT曾引入自身事务计数问题，已纠正）；对象读取已是跨对象有界批次，通常每批至多64对象、16MiB，时间段30秒，单个大对象另受分段边界约束。不能继续把昨日单对象scope问题说成当前尚未修改。命令证据已采用有界分组，不把旧无限扩展问题重复计入。
- 独立核真实58只读组件对照capture-guard-real58-r3.private.json：三轮baseline平均3.870867秒、26条远端命令，candidate平均2.316647秒、10条，约降40.15%；同轮观察摘要相等、远端写入为0。baseline是当前函数禁用观察复用的对照，不是历史安装版本重放。fullMainTargetCaptureGuard=false，未包含完整本地custody/context/claim/budget等成本，不能外推完整恢复提速。当前58为MAIN/v1、storage/v2，部分挂载复用分支不能计为此次实际收益。
- 明确重复一，优先处理证据收尾：recovery_target_preservation.py的_publish在838调用context.snapshot()，该函数于recovery_program_native.py:611–628遍历全部segments并读取terminal/pending文档；紧接着_publish:843–849再次iter_rows并读取terminal文档，而且每条记录调用session.guard()。后者达到节流条件会发远端检查，审计旧命令时又增加新命令。并非断言无限循环，但重复全读及逐记录保护成本随记录数量增长。建议一次严格流式校验同时产出摘要和成功状态，遍历中用轻量本地检查，前后边界完成必要保护验证；不能仅信摘要、吞掉UNKNOWN或删掉唯一一次原始完整校验。
- 明确重复二，失败路径：同文件capture_and_publish:761取得context.snapshot()，769又调用session.snapshot()，后者recovery_target_capture.py:588再次context.snapshot()；在这两次调用之间无必要远端状态迁移，造成相同证据全量重读。应同一失败收尾内复用已验证快照和捕获状态，发生变更则失效。handoff前后有真实租约状态迁移，两侧快照不能一概删除。
- 本地检查仍有重叠，实际耗时尚未量化：recovery_target_capture.guard:433先执行check、view.guard_native、custody._validate才进入轻量scope分支。recovery_program_protection._validate:335–356又对固定输入逐个_input校验，_input:312–333会完整读文件算SHA，_verify_journals:358–377还读取证据记录；recovery_capture_read._binding:51和formal_capture_semantics._read_content:550–552在块前后继续嵌套上述检查。不能因无SSH就当作廉价内存检查，也不能把未知大小的输入夸大为大包全读。应先量化同工作量完整guard中的本地文件读取和校验次数，再在持续租约及变化失效约束下消除同回调/同批次重复；保留初始完整性和必要持续变化监测。
- 明确重复三，数据库身份：recovery_replace.verify_services:178独立native.database_uuid()，同轮MainTargetCapture.guard:474集中数据库观察仍查@@server_uuid。可在捕获轮次复用同一次有效观察并调整顺序，保留其他调用路径的默认校验，不能删除身份判断。
- 条件化优化，避免扩范围：recovery_capture_sql._boundary:77–85及表scope进入/退出分别完整guard，formal_data_evidence._observe_data:367–386逐表使用。小表很多时远端保护轮数仍可能偏高，可在现有受保护边界内做有界批次，但应先量化；表行数、逻辑摘要、schema前后校验是不同语义，不因多条检查就删除，也不把这项后续优化变成无限追加验收前置。
- 回归和环境分别报告：开发证据native-segment-linux-r14为75通过、1失败、0跳过，失败涉及pending证据在保护范围外的处理；尚未取得修复后的完整通过回执。开发线程另报告本机Docker客户端崩溃和只读info超时，已暂停重型测试；这只能解释当前测试受阻，不能解释全部历史耗时。新包安装及真实新I2到58恢复仍无完成证据。
- 已沿用户既有明确授权发送上述具体位置、去重语义、成本计量和不扩范围要求。工具确认投递，revision133开发方明确接受，优先核实审计时再产生检查命令、失败重复扫描，并分别计量本地检查和UUID读取；发送与接受均不算修复完成。此轮评审完成，原修改后独立验收继续in_progress。

## 明确修改授权后再次核验（2026-11-15，revision136）

- 上轮用户明确要求修改后检查，四项正式指令已成功投递；实际线程记录已分别安排证据扫描/本地成本和UUID去重。中途再次问方向，沿原任务审查，不重派相同指令、不新建任务、不执行服务器动作。上一等待cell因中断已不存在，改取即时revision136与最近实际消息。
- 最新实现仍为capture-release-integration-r1 HEAD a327d21加集成修改，已与上一轮出现明确差异。保全成功收尾recovery_target_preservation.py:837–844改为前边界完整guard、snapshot(require_success=True, guard=scan_guard, after_scan=...)一次严格扫描；扫描中只作本地检查，后边界新增的有限命令尾部另行校验。recovery_program_native.py:611–663对原件成功状态、实际exitCode、完整性失败、扫描期间追加、尾部上限和后边界失败均做拒绝处理，尾部live_row重新读terminal原件，不能再将昨日双重全遍历和逐记录远端guard当作尚未修复。
- 失败路径recovery_target_preservation.py:761–769只取一次context.snapshot并结合session._unknown，不再调用session.snapshot造成第二遍扫描。跨真实handoff变化的快照仍保留，未误删变化后的验证。
- UUID去重已经接入：recovery_replace.py:158–191仅在正式capture且绑定同轮观察时使用CaptureDatabaseObservation.for_round；recovery_target_capture.py:469–477同轮取得同一对象。helper:38–65拒绝失败轮重建、校验原native及观察生命周期，parse仍核databaseUuid；非capture保留独立database_uuid。未简单删除数据库身份验证。
- 本地去重已部分落实：MainTargetCapture.guard:433不再直接重复session.check，因view.guard_native内已执行；custody._validate移至scope分支后，内容/SQLscope内由lease._guard执行一次。新增test_capture_local_guard_dedup覆盖单回调一次session/custody、下一回调重新验证、异常传播、scope身份/序号/期限和force分支。这不是跨批次长期缓存。
- 仍可优化但需成本证据：ProtectedContentRead.before_read/after_read各做scope.check，内容读取函数块前后另调用guard；每次scope._binding仍经过lease._guard→custody._validate，对固定输入SHA和日志读取。单次guard内去重不等于每1MiB块只校验一次；不能把这些全部说成已消除，也不能未经持续变化保护证明直接删除。逐表scope前后完整guard仍在，属于可量化的频率疑点，优先完成现有本地成本测量及最小恢复，不无限扩范围。
- 独立读取capture-guard-real58-r5.private.json：三轮远端组件调用均26→9，平均3.965837→2.173243秒，约下降45.20%，观察摘要完全相同，remoteWrites=0，fullMainTargetCaptureGuard=false。对照为当前函数关闭复用，不是历史安装版重放，不代表整条恢复提速45%。新test_native_local_guard_cost测真实Linux本地文件/锁/监视，但远端准备是声明的协议fixture，不是完整测试服保护证明；本轮未取得其测量完成回执，r16结果目录尚未生成。
- 实际最近命令显示单次扫描及segment context两文件pytest退出0，线程报告修正object.__new__夹具缺失_takeover后19项通过；未以此证明Linux全链通过。r15记录77PASS/1setupERROR，原pending失败场景已通过，剩余SQL夹具导入修复待重跑，不再沿用r14旧失败当当前缺陷。Docker只读查询已自然恢复，未重启Docker或服务器；原崩溃/超时保留，不能继续把基础设施故障说成当前唯一阻塞。
- 结论：原地保全后按新FULL/I1/I2恢复的方向仍合理，已开始在代码层面收敛；四项问题有实际修复，其中本地检查粒度和完整成本仍待验证。现有已验证封包52d0b1e、安装2ac4b37，尚未发起新的真实恢复；最终提交/封包/安装和同一I2到58成功仍待独立验收。用户当前咨询已复核，原修改后审阅继续in_progress。

## 再次核对方向、必要保护与过重预检（2026-11-15，revision138）

- 最新来源：只读即时快照、最近实际命令、R集成742ce1e与独立冻结process-fact-final-own-r1候选（main SHA06bb67c15bcf76a133ee0e1a9d9e7325b5f0a361322b8d0b9a71db215057a537）。R已提交原四项修复、监视和挂载规范化；最终进程转换修复仍以冻结输入/原回执核实，不能混称已全部融合、安装。review-summary部分旧段落落后，已优先以最新execution-log及原件判断。
- 方向未变：保全已有目标后恢复新FULL/I1/I2仍合理；当前新增工作主要属于旧UNKNOWN现场安全接管和消除预检误判。应只核目标身份、写入隔离、存储占用/进程关联、备份完整性和实际覆盖条件；无关进程正常生灭或列表顺序变化不应成为持续返工原因。必要的原进程退出证明不能删除，也不能把当前观察当作旧操作成功证据。
- 扫描持续保护缺口已有代码修复：recovery_program_native.py:611–693在成功扫描前取得context唯一NativeSnapshotWatch，先登记每个原件/段再读；中途、后边界和返回前检查，有限尾部也纳入监视。recovery_native_segments.py:286起使用本地inode事件、目录句柄及挂载变化检测，故障粘滞阻断；只在挂载表变化时逐路径复核，非每条原件都全量重扫。test_native_single_scan新增已读前缀/段在后边界变化、后续回调变化、连续snapshot复用监视的测试。该持续保护弥补单次扫描盲区，不应视为可删除的额外校验；不能沿用revision137说缺口仍完全未修。
- 已确认并修复的过重检查：742ce1e将Docker Mounts按既有Destination规则规范化，仅消除列表顺序差异，完整挂载内容仍比较。最终进程候选recovery_main_target.py:1846–1878不因无关进程产生而重读全部稳定PID的cmdline/cgroup/exe，保留同句柄stat身份/关系闭合，仅变化时重采完整事实；原两轮FD/事实采样保留。实际只读probe-r2原JSON为357进程、22瞬态、6轮、26571次本地保护回调、11.967920秒、remoteWrites=0、fullAdmission=false。26571不是远端命令数，也不能仅因数量大判多余；前一失败探针原样保留。最终退出边界变更仍待父线程最终现场复核。
- 本地成本已取得原件native-local-guard-cost-r18.json：真实Linux文件/flock/inotify、外部有限协议fixture。3次本地回调49.756782ms→26.90625ms；custody6→3、输入读36→18、日志读60→36。一次完整force回调仍有custody12、输入读72、日志读254、context265、lease3623，实测190.875389ms。计时项含嵌套不能相加，fixture并非真实测试服性能。说明重复层级确实仍在，但该证据不能证明它仍是小时级阻塞；不应凭调用数再无限追加优化前置。
- 剩余可评估优化：块前后scope与guard仍多次进入固定输入/日志校验，逐表入口出口仍完整保护检查，可在持续保护和失效条件下减少同一状态重复读取、按实测决定小表批次。当前未发现足以支持直接删除停写保护、完整性/挂载身份或覆盖边界校验的新依据。应先修确切正确性/准入失败，再冻结候选执行真实恢复；非阻断优化后置。
- 独立核JUnit及result.json：unresolved-process-full-fact-final-regression-r1为226 tests/0 failures/0 errors/0 skipped，pytest14.456秒、载体exit0；同sourceSha256的preservation-final为1 test/0 failures/0 errors/0 skipped，pytest121.459秒、载体130.203秒exit0，自有容器移除、原容器不变。后者是本地完整当前保全、发布、读回和handoff测试，不能误称测试服完整I2恢复成功。此前19PASS、r16失败均为历史阶段，不能当最新终态。
- 发布运行边界更新：04b34ac已有正式161成员包并上传本任务私密控制材料，但INITIAL在STAGE前失败，未激活新控制；安装仍旧2ac4b37，尚无新真实Spug恢复。最新父线程明确226及完整保全交接通过，准备最终只读采样与精确交付。PF_EXITING组件诊断整体FAIL（后续发现EACCES），两条退出子事实不等于整体成功；保留具体缺口，不用新增泛化校验替代收敛。原修改后独立验收仍in_progress。
