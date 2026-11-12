# 操作配置目录物化验证续办设计

## Current Status

ready_for_closeout。父已完成三服b10 STAGE/PREPARE/ACTIVATE；本项正式optional配置关系及typed小context已实现，新增19项及相邻97项均通过。finalizer已从实际stdout与27原件本机核验并生成2135B context；原collector FAIL和未知exit保持。原successor字节先保存，唯一该源增加参数/关系/loader接线，current/UI和其它冻结源不改；原plan/inputPins、packet、旧配置不改。父接续唯一正式verify→原UI；本子任务不执行SSH/业务写入/提交。

## 目标与里程碑

1. 读取现有失败请求核验及产品archiveCatalogue→operation materialization正式入口。
2. 核对真实packet配置与前代owner差异是否完整符合正式物化结果，不删sources或忽略未知字段。
3. 提出可独立审查、逐pin绑定、无旧原件修改的验证续办模块和消费者边界，给父审批。
4. 仅设计阶段；实现和RED/GREEN须父批准后继续。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。未知差异、缺少物化输入原件或pin无法验证均拒绝。
- 是否从根因和长期维护角度解决：是。按正式操作配置物化合同证明安装owner与operation配置的可验证派生关系。
- 是否存在临时补丁或绕过：否。不得删除sources比较、归一化伪造原packet或把真实native PASS替代正式配置验证。

## 经验门禁

- Trigger：安装控制配置与真实历史操作配置存在catalogue物化差异。Preflight check：先定位正式产品转换函数及其全部输入pins，保留源/物化配置原字节、request与真实已激活回执。Blocker：任何未知delta、缺原始目录/manifest/repository pin或消费者无法绑定。Verification：完整转换结果逐值等于原packet、所有非物化字段严格相同、反例RED。Forbidden action：修改旧pins、回执、原packet、冻结loader或安装源；删sources/无条件忽略字段。Evidence：本设计、父保存verify失败及实际原件。

## 前项状态与边界

前项PRIVATE载体已冻结交付并由父真实安装三服全PASS；最终selection被本次具体配置投影差异阻断。旧载体freeze与plan保持，本项是直接必要的只读续办设计，不重复安装或重跑历史链。

## 根因与正式产品合同

- 冻结successor._verify_repeat_api在647行将packet.operation configuration直接等同predecessor.targetOwners[58]。产品for_request先按旧base owner、原request与唯一point binding物化恢复配置，该相等关系不适用于目录来源；原失败、控制安装、产品epoch与native并未因此变成无效。
- `backend/src/main/resources/recovery_control_restore_catalogue.py:314-345`先验证真实来源候选及全部父链可选，再调用正式`derive_archive_restore_owner`，独占留下`restore-inputs.json`、`archive-point.json`与`recovery.json`。
- `ops/recovery/recovery_restore_inputs.py:118-240`严格验证source scope/identity、点/manifest/binding、父链前缀、同scope、原退出/读回/归档关闭证据以及完整pointBinding。仅所选source删除archiveCatalogue，精确更新sourceScopePin、recoveryPoints、repositoryPointPins、repositoryBindingPinsByManifestSha256和parentChains；owner其它字段全部保持。
- 正式`verify_archive_restore_inputs`还核原request路径、三个request-configurations原件固定路径、restore-inputs的原base owner pin和request，最终canonical derivedOwner与原recovery.json相同。它仅验证历史输入，不授权payload/source/target/clear。

## 已批准的只读采集

父批准只新增PRIVATE/collect-retry-archive-owner-r1.py并由父执行58只读采集。本子任务本机已绑定真实planning、58ACTIVATE、原packet，完整73934B脚本compile通过，没有远端执行。

- 实际b10官方154模块逐SHA前后验证，当前控制PID/完整argv及正式模块origin验证；base owner为真实previousOwnerPin，request/config为原packet pin。
- 固定旧taskRoot/request-configurations/原operation下三个原件，调用原产品verify，不discover、不读载荷。
- pure产品结果、所有originalResultPins对应原字节、控制/包/模块/脚本/输入pin留作独立证据；canonical derivedOwner必须与原operation configuration相同。
- collector r1 SHA bcb5d9ba6b7f5093047ed37943d4b3f06838205786354e6111b26569d94a82e0。父实际r1因未继承CONTROL.environment而import jsonschema失败，原stderr/脚本留存，不能算业务RED或采集成功。
- r2仅接线正式CONTROL.environment，以env -i启动同python并切换正式workingDirectory；PRIVATE/collect-retry-archive-owner-r2.py 8807B SHA9b3743aa7634bd6aa695a308983aec3fd0e661a800c98bbcd3c9c6d127c3f5ce。本机真实prepare/compile通过；实际采集由父执行后另记，不把compile当实际PASS。

## 待审批的最小独立消费边界

父明确不批准复制80+68行验证器及UI主体。后续优先正式optional typed配置关系参数：原successor仅配置equality点支持完整ArchiveRestoreOwner/v1验证context，并逐host透传；mixed loader读取明确仅58的可选evidence pin字段，旧六字段selection/v3和全部旧行为保持。current loader/UI不变。原successor字节预先snapshot；新reader由追加custody绑定，独立verify输入明确验证旧planning reader pin→保存snapshot→新reader关系，不改原planning。以下复制式初案仅保留讨论历史，不实施。

1. 新增`main_program_target_archive_owner_continuation.py`，明确版本化selection/profile，接受精确pinned采集证据；不修改冻结helper或旧plan。原partial完整loader只调用一次；57/59复用原perhost verifier；58独立续办verifier逐句保留原perhost/API证据门禁，配置关系只接受完整产品物化证明，原old_owner/packet均保持。
2. PRIVATE新增独立最终verify入口，3真实ACTIVATE PASS及58续办全部通过后才独占生成新selection，完整pin收录验证器、采集脚本/报告/metadata和旧原件。禁止全局函数猴补或临时修改sys.modules来改变原loader。
3. 旧current loader不能消费新schema，新增PRIVATE UI续办载体只修改冻结UI的schema/profile及Python loader入口两处接线，其余真实UI业务路径同字节。verify/submit每phase重新正式load；源custody以追加wrapper明确收录新reader pins，旧结果和旧reader pins不改。

## 待实现BDD/TDD

- Given完整真实catalogue物化原件，When独立验证，ThenderivedOwner精确等于原packet且所有其它owner/source字段逐值相同。
- Given任一base pin、request source/point/target、3配置路径、scope/identity、父链、manifest/binding/原成功证据或metadata字节漂移，When验证，Then在生成selection前拒绝。
- Given仅删除sources比较或只提供PASS布尔报告而无完整metadata原件，When验证，Then拒绝；真实native PASS不能替代该合同。
- Given冻结6源、原plan/inputPins/receipt未变，When新loader和真实UI phase消费，Then走明确新schema/新模块pin，旧v1/v2/v3原行为保持；缺续办或旧UI入口拒绝，不产生假summary。

## 父批准的最终最小实施方案

- 正式小模块只绑定已实际完成的remote product结果与27原件SHA、实际58ACTIVATE/current PID/package/module pin；独立重建产品最后projection并canonical比较全owner。产品已完成的全部文件系统观察不在Windows伪造或再演；不用AST替换is_dir，不复制host/API验证器或UI。
- successor._verify_repeat_api仅增加optional typed verification参数，默认None原全等门禁保持；当前58/原381/source57/I2完整context可证明合法派生。host函数仅透传，mixed loader显式读archiveOwnerVerificationPinsByHost={'58':…}，原six-field v3维持。current reader与UI源完全不变。
- 旧successor 83043B SHA803bfbd0db121c1668368a6e2c12beffbbde9676ba87ec26dac77ade6d41f2a8已精确保存PRIVATE/main_program_target_control_successor-before-archive-owner-r1.private.py并逐字节核相同。旧planning及安装脚本原值保持；独立verify续办入口明确从snapshot验证旧reader历史，不冒称旧路径SHA未变。
- 父实际collector r2 stdout是PASS、27metadata、PID17559、0写/0载荷，25522600B SHA61035c65218422394a5ba6ac4cba35aa38f88d418030a13ef697c9bef07d90cb。原carrier因唯一OpenSSH关闭通知而FAIL；不重SSH。独立finalizer保留FAIL及stderr，exitCode=null且来源明确未落盘，只从完整原件与实际product结果建立配置关系证明，不伪造进程exit0。

## 最终结果与交付

- 本机RED `archive-owner-continuation-red-r1.xml`：13 FAIL，缺typed参数/模块；旧默认合法行为1 PASS。GREEN `archive-owner-continuation-green-r2.xml`：19 PASS/0 skip，3.83秒；相邻 `archive-owner-continuation-adjacent-r1.xml`：97 PASS/0 skip，31.47秒。
- `archive-owner-continuation-regression-r1.xml`为命令组合PRIVATE与repo路径导致pytest共同root落到C盘、采集Documents and Settings PermissionError的环境收集失败，未执行用例；分别原范围运行获得上述19+97实际PASS，未修改业务/测试来掩盖。
- PRIVATE/finalize-retry-archive-owner-r1.py已实际本机完成：`retry-archive-owner-verification-r1.private.json`2135B SHA72fd2edf6b23d287b314b3962701e82b3417d30e569d18bb950c7560c5bb0078。父无需重跑finalizer或SSH。
- 正式入口PRIVATE/verify-retry-archive-owner-continuation-r1.py，仅增加唯一旧reader snapshot历史映射；真实inputs()已通过，原planning/已验partial全部其它输入逐pin核对。未运行入口main、未生成selection、不与父独占操作并行。
- 原SourceRoles/v1的currentReaderPins精确限定historical_custody、acceptance及current_installation三模块，三者本轮未改，所以实际`main-program-spug-historical-source-roles-20261112-r2.private.json`仍是正确custody（6191B SHA0fac47c6c3d429a93ad9a38a77b23eacb9b90c4c591d707a946ede68f8d44ae6）。不将非该合同role的新target helper塞入此列表；新target reader及snapshot在verify独立readerOriginalPreservation及最终loader inputPins中明确绑定。
- 可执行命令：固定PY `-B -X utf8 PRIVATE/verify-retry-archive-owner-continuation-r1.py --custody PRIVATE/main-program-spug-historical-source-roles-20261112-r2.private.json`。父完成实际全链后，仍使用原current loader/原UI入口，不复制UI或额外版本平台。
