# 本轮目标激活的两个明确续办合同

## Current Status

ready_for_parent_review；两个明确续办profile及正常路径共118项纯units通过，相邻有限回归247项通过。已用父实际57 context r1、58 context r2验证纯入口与runtime spec；helper重新冻结供父真实载体使用，旧历史v1模块保持。无远端操作、无提交，不把本地纯PASS当实际服务或恢复验收。

## 目标、里程碑与验证

- 58：已知错误dropin仅换了config path而保留旧bytes/SHA，服务exit2。保留FAILED审计和错误dropin，追加更后正确dropin，仅恢复该target控制服务；原业务/NAS保持。
- 57：正确新控制已启动，载体仅缺pure._new_package_pin导致after比较未完成。只读续验，不再重启、不增dropin。
- BDD→RED→最小helper扩展→原87与新有限测试回归→父审实际原文；UI接线仍等待，不运行浏览器。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；只接受58 CONTROL_PROCESS_CHANGED与57精确AttributeError，FAILED原文不改。
- 是否从根因和长期维护角度解决：是；将物理动作已完成与历史观察显式区分，原PID退出后不伪造current before观测。
- 是否存在临时补丁或绕过：否；错误dropin正式保留为历史并加入新spec，追加正确配置有独立pin和argv证明。

## 经验门禁

- Trigger：目标控制服务激活失败续办、保留原审计/dropin、旧PID已退出。
- Preflight check：真实FAILED wrapper/receipt原pin、原before原pin、原dropin raw、两profile精确错误；58先停本任务失败target到0/inactive/dead并真实读保护观察及170/158/4原pin；57从原PREPARE固定nativeBefore/HTTP且只读after。
- Blocker：未知失败、原件失配、业务/挂载/源/custody漂移、target仍有worker、错误dropin内容不是已定位单pin错误、正确dropin不等全新pin。
- Verification：全部原始pin闭合，before仅历史、after真实gate+原147历史绑定；58只准两个dropin追加、57只准原单个追加，未知变化拒绝。
- Forbidden action：不删除/改写FAILED、before或错误dropin，不称旧PID仍活动，不重派57服务切换，不允许其它host/profile，不扩大业务恢复授权。
- Evidence：父保留target-control-successor-58-b9caa00-r2-activate-result.private.json、57-r3同类原件及reader-target58-failed-activation-observation-r1.private.json。

## 正式数据合同

selection仍TaskMainProgramTargetControlSuccessorSelection/v1五字段。正常wrapper不变；仅57/58续办wrapper增加continuationLocalEvidencePin（本机私密原文pin）。result增加精确六字段：continuationProfile、continuationFailurePin、continuationBeforePin、continuationDropinPin、controlServiceRestartedInPriorAttempt=true、controlServiceRestartedDuringContinuation（57false/58true）。

58 profile TARGET58_BAD_DROPIN_REPLACEMENT/v1；context schema MainTarget58ReaderContinuationEvidence/v1，字段schemaVersion/failureWrapperPin/failureWrapper/beforePin/before/failedDropinPin/failedDropinRawBase64/correctDropinRawBase64/preContinuationObservation/prepareWrapperPin/prepareWrapper。

preContinuationObservation按父约定MainTarget58ReaderContinuationPreflight/v1，PASS/serverWritesfalse/physicalLockVerifiedtrue/protectedObservation原before去controllers全部实际读且相等/peerControllers[]/targetProperties实际MainPID0 inactive dead/retainedPins170/successorPins158/failurePins原4/failedDropinPin；与实际纯stage计划逐pin相等。新spec明确保留错误dropin，current row绑定正确新dropin。

57 profile TARGET57_AFTER_READBACK_ONLY/v1；context schema MainTarget57ReaderReadbackEvidence/v1，字段schemaVersion/failureWrapperPin/failureWrapper/beforePin/before/dropinPin/dropinRawBase64/prepareWrapperPin/prepareWrapper。只接受stage=new-runtime,errorType=AttributeError,errorCode精确“'_PureTransition' object has no attribute '_new_package_pin'”；原PREPARE.nativeBefore/originalApi是before证据，不能新建替代。

两profile均严格读取真实FAILED wrapper（status=FAILED）与真实PREPARE wrapper（status=SUCCESSOR_ACTIVATION_PREPARED）；PREPARE.result.before==after==原历史before，nativeBefore/originalApi来源闭合。58 proposedDropinPin等原错误dropin，57等原正确dropin。不能将PREPARE或FAILED改写成PASS。

原receipt仍按已验证两个出版阶段闭合。新58raw必须是原错误raw中仅完整config JSON pin替换为正确完整新pin；两者ExecStart经shlex解析6args，python/engine/serve固定，其它文本逐字保持。两个dropin均独立路径且lex严格递增。

## BDD（实现前）

1. Given 58精确失败原文、历史before、错误raw和真实零PID停稳preflight；When 构造续办spec/核成功result；Then 新spec含原+错误dropin，正确dropin最后，所有其它业务/源/挂载/历史保持。
2. Given 57精确after比较失败原文和原PREPARE；When 只读续验；Then 不新增/重启，nativeBefore/HTTP来自原件，after完整，正常单dropin比较通过。
3. Given 错host/profile/error、缺原件、SHA不符、58额外文本变化/旧pin、preflight有worker或PID非0、未知mount/custody变化；When 核续办；Then 拒绝。
4. Given 正常59/正常57、原87tests；When 正常路径核验；Then 原语义不变；loader仅遇显式continuation pin才读对应context和原wrapper/script/prepare原件，所有inputs结尾再核。

## RED / GREEN / REGRESSION

命令固定为本机缓存Python、pytest8.3.5与禁止第三方pytest插件；`pytest scripts/tests/test_main_program_target_control_successor.py -q`，有限集合按continuation选择；不启动容器或外部服务。

- 新续办首轮RED：26 FAIL、0 error/skip，5.427s，reader-continuation-red-r1.xml；正常入口原87项未替换。
- 最小续办GREEN：26 PASS，6.424s，reader-continuation-green-r1.xml。
- loader显式context原文接线RED：2 FAIL、0 error/skip，1.832s，reader-continuation-loader-red-r1.xml；随后新续办31 PASS，7.916s，reader-continuation-green-r2.xml。
- 全新helper GREEN：118 PASS，18.682s，reader-continuation-green-r3.xml。
- 有限REGRESSION：successor118 + 原candidate54 + 原activated61 + dependency14 = 247 PASS，0 error/skip，XML时间22.156s，reader-continuation-regression-r1.xml。原正常路径及重复依赖/DropInPaths精确语义保持。
- 上述XML均保留在本任务PRIVATE目录；没有用模拟原文冒充现场验收。实现冻结前直接读取真实57 context r1与58 context r2，两个纯入口及新runtime spec均PASS；57不增加失败dropin，58明确返回原failedDropinPin，retainedDocuments均35。

## 冻结、现场证据与剩余范围

- main_program_target_control_successor.py：40508 bytes，SHA256 ae1be3679bce0c348a971ecb0ad9f7978c83325c107eefc7e1aacdf26fc15547。
- test_main_program_target_control_successor.py：50699 bytes，SHA256 c5e136ef6a247129251ac9e73c6f23aae403e86acb15486bc2c50613c240c4f1。
- 父已报告58 r4真实续办PASS40.578s、57 r4只读续办PASS28.531s、59 r3正常ACTIVATE PASS41.656s，并报告三份实际wrapper纯投影PASS8.266s；子任务未执行这些远端操作。
- 父报告新正式selection完整loader PASS103.313s/1689 input pins，selection SHA256 a132da270e0b59e78d956ff07da05d087c82ca48fc951b82e8f271a7842f84d1。失败receipt、错误dropin、原before、旧receipt/custody均作为历史保留；此处不声称业务数据恢复成功。
- 当前等待父审/提交与真实UI后续验收；helper保持冻结，不随文档更新改变运行字节。
