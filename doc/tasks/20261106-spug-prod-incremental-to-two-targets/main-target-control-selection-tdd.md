# 已激活目标控制 overlay 加载

## Current Status

ready_for_closeout；父已批准独立v1合同与三文件范围，实现和必要验证已通过，等待父最终审查与提交。上一依赖集合语义修复98 PASS已交父审，本项不改其范围。不远端、不提交、不改旧选择/receipt/custody。

## 目标、里程碑与预期验证

1. 设计明确的三target已激活证据和本地pin选择合同，父确认后实现。
2. BDD→RED→GREEN：只有三份完整实际transition/native/HTTP证据齐全且绑定相同官方153包，才能覆盖effective target；来源6968b58、Spug5651efc和完整旧历史保持。
3. 有限回归与实际父留存证据纯加载验收；本机协议不冒称远端runtime健康。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；三份不齐、绑定/原件/实读内容漂移、BOUND或仅本机测试证据拒绝。
- 是否从根因和长期维护角度解决：是；角色独立激活overlay与旧receipt历史明确分离，完整复用正式来源加载链。
- 是否存在临时补丁或绕过：否；旧选择和旧activeReceipt留原位，不借用旧custody证明后继安装。

## 经验门禁

- Trigger：source/target分角色安装代次、三服真实激活、旧receipt/custody、只读UI preflight。
- Preflight check：正式source v2 loader核完整base，三target证据全pin与官方包逐字/manifest验证，target-only变化及真实native/HTTP绑定。
- Blocker：任意少服/错主机/错pin/错源/错build、仅BOUND或模拟通过、原source/Spug/历史/物理目标改变。
- Verification：父审数据合同→RED→GREEN→有限邻接回归→三份真实记录纯读取；返回installationVerified=true/runtimeVerified=false。
- Forbidden action：不改旧选择/回执/历史、不读写服务器、不发布选择/Spug配置、不把旧托管记录或本机测试当新安装证明。
- Evidence：已读main_program_installation_selection/source_control_selection/source_control_activated/current_installation、TargetControlRuntimeTransition及父最终升级计划；后续由父提供真实私密证据。

## BDD

- Given 正式已加载来源v2选择与三份目标实际激活证据；When 只读加载target overlay；Then 只替换各host target row及其owner/control与build binding，完整保留source、Spug与旧历史。
- Given 任何一服缺transition/native/HTTP证明或旧source/target绑定不符；When 加载；Then fail closed，不投影BOUND或部分激活状态为可用安装。
- Given 后继运行spec与旧custody绑定不同；When 核验证据；Then 两套绑定分别明确验证，旧receipt原位和旧配置/包/历史pins保持，不旋转、不伪造新托管。
- Given 原始激活回执已固定；When 校验发布原文；Then 直接canonical闭合，或者只允许createdPaths唯一最后一项为回执自身路径、去掉该项后闭合；中间项、错路径或任何其它差异拒绝。
- Given 已重启但后验失败的明确续验；When 读取成功证据；Then 必须同时实际读取原失败wrapper和原PREPARE wrapper，远端失败回执与原before pin闭合，原API和原运行spec保持；不得将失败或重复重启隐去。

## 已批准接口与输入

- `load_activated_target_installation(task, private, *, selection_file, historical_source_custody_pin=None)`：只读本机文件，复用完整正式source v2加载器。
- selection精确五字段：schemaVersion、baseSourceSelectionPin、buildPin、standardPackagePin、targetActivationEvidencePins；最后字段精确57/58/59三键，私密本机绝对pin。
- 原始wrapper保留status/host/mode/observedAt/elapsedSeconds/scriptPin/result；result使用同次真实MainProgramTargetControlActivation/v1原值，不拆人为报告。
- 续验可追加continuationLocalFailurePin/continuationLocalPreparePin；成功result仅追加continuationFailurePin/continuationBeforePin/controlServiceRestartedInPriorAttempt。
- 三target完整官方153包、16文档、旧147包、旧当前target绑定与实际before/after、native READY epoch和三来源HTTP准入全部核验。输出installationVerified=true、runtimeVerified=false，完整保留来源6968b58、Spug5651efc和旧代次历史。

## TDD证据

- 环境前置：直接python -m pytest因内置runtime未带pytest而失败；明确使用既有私密pytest-runtime-8.3.5，不安装依赖或跳过测试。
- RED：既有pytest runtime执行新测试文件 `-q -p no:cacheprovider --tb=short -x` → 1 failed，预期 `MISSING_ACTIVATED_TARGET_OVERLAY_LOADER`；已先修正fixture自身bytes序列化错误，RED来自待实现功能。
- GREEN首轮：43纯配置/原始回执/过渡观测units PASS；真实三服raw+实际新旧包的纯重建PASS（正式来源快照作为输入，不冒称已重新加载完整旧链）。
- RED补充：续验与精确原dropin/创建范围测试 → 原dropin伪变、遗漏before文件、遗漏dropin三项未拒绝；记录实际缺口后最小补充门禁。续验fixture已消除proposedDropinPin与成功result的对象别名，避免测试同时改两份输入。
- GREEN补充：60纯units PASS/3.41s；所有续验原失败/准备/before/API/native/dropin绑定、原dropin加载集合和普通/续验创建路径闭包均验证。
- REGRESSION：`PRIVATE/run-target-control-activated-linux.py regression-r1` → native exit0，158 PASS/28.23s。范围为新增60、依赖集合14、目标运行过渡47、原RuntimeGates37；固定python3.12-bookworm镜像、12既有pin wheels、network=none、只读root、cap-drop ALL、1CPU/512MiB、有限600s。33源码快照921600 bytes SHA256 `5baae4ad50691135c8421952b985efe901589e5dbc3f340b5fa3c073b590c4e7`，inputsUnchanged=true、containerRemoved=true、remoteWrites=0；仅协议测试。
- 正式链第一次实读：原`main-program-targets-activated-a3121c6-v1.json`在完整source历史段通过后，于standardPackagePin因本地正斜杠path与既有publication.file_pin原生path不等而exit1；选择原件保留。没有修改旧helper或增加路径兼容，父另独占产生符合既有合同的r2选择。
- 正式r2全链实读：`load_activated_target_installation(..., selection_file='main-program-targets-activated-a3121c6-r2-v1.json', historical_source_custody_pin=<正式原pin>)` → PASS/81.0s，1667枚inputPins全部复核；selection 1621 bytes SHA256 `07c970986f1a34691f41e7010d7ab8d185dba3848bc4338d6b66d99e6d923f0b`。输出原件PRIVATE/activated-target-formal-load-r2.private.json，16569671 bytes SHA256 `fa040c2c3a71ed9d07810353803b0909e028d4c13ca0d378b4071c98af297c6c`，不冒称fresh runtime健康。
- 实际投影：source57仍6968b58/147文件/PID25028；target57/58/59均a3121c6/153文件，原始观测PID分别5868/26210/17563；Spug及全部旧base由正式原链保留。本机只读证明，无服务器动作、无新包构建、无提交。
- BDD补充代码pin闭包：Given 原过渡类使用共享RuntimeGates实现；When 本机加载入口在读取选择前固定代码pins；Then 共享类的实际定义文件也必须包含在pin集合中，防止本轮加载期间依赖实现漂移。父已确认等真实preview退出后仅补该直接依赖，不改任何数据合同。
- RED补充：精确单元`test_shared_runtime_implementation_is_pinned_before_any_selection_read` → 1 failed，`SHARED_RUNTIME_IMPLEMENTATION_NOT_PINNED`。最小实现仅增加共享runtime导入和显式codepins成员；61纯units GREEN/3.57s，未重复未变化的158项Linux矩阵。
- 正式最终r3全链实读：同r2正式选择，91.547s/PASS，1668枚inputPins（新增共享runtime19647 bytes SHA256 `80c0fbfcddd45953adcbb0d834ad21c48d782ae5acc3df22bfe117a3561181c8`），全部再次复核。输出PRIVATE/activated-target-formal-load-r3.private.json，16569934 bytes SHA256 `90728e85024de4a15b2912731b2b80dc4e0a0715eb050facf4bd3f249939ff5c`。installationVerified=true/runtimeVerified=false，角色投影保持r2相同。

## 里程碑状态

1. 独立selection、原始wrapper、两种明确回执发布阶段和续验合同：父批准，完成。
2. BDD→RED→GREEN：61纯协议units，完成。
3. 有限Linux回归158 PASS、真实三raw纯重建、r2正式全链实读：完成。
4. 父审完成：核对最终代码字节、原件发布阶段/59续验绑定、完整新旧包重建、旧custody保持及共享runtime codepin；61纯unit、158有限Linux和最终1668 pin全链原件证据通过。仅本子项进入实现提交，总任务真实UI/恢复及融合清理仍未完成。

## 最终实现字节

- main_program_target_control_activated.py：24100 bytes，SHA256 `f858d66ab65ba885fc6307be848ab0419e2276cd76a30d9546d6ca45013dc77f`。
- scripts/tests/test_main_program_target_control_activated.py：22847 bytes，SHA256 `9b3dd8ff089881ffac4d89dd245090887dc71bb2ab87a1bbedeb230503303bfe`。
- 全部新增文本已以UTF-8显式回读；无服务器操作、无提交。

## 输出与使用边界

- 返回selection/selectionPin/inputPins/effectiveControllersByHost/controllerBuildBindings；sourceInstallation和baseInstallation完整保留，后者保留Spug独立版本。
- targetControls/targetOwners按host输出；targetRuntimeSpecs按host分别保留original与successor。旧receipt/custody保持原位置和原spec，实际运行核验仍须TargetControlRuntimeTransition或RetainedHistoryRuntimeGates明确委托旧历史，不能把旧receipt改绑新owner。
- currentController是实际activation的原值，包含保留下来的旧历史字段；当前target包身份由controllerBuildBindings.target和严格重建candidate.package明确给出。
- `historical_source_custody_pin=publication.file_pin(PRIVATE/'main-program-spug-historical-source-roles-20261111-r1.private.json')`，6191 bytes SHA256 `428e12b072d94ab8b3cdb40ca0b0a934029767ffce17beb7c533f474b5d72570`；本加载器转发正式source链，不替换历史角色凭据。
