# CIFS reader修复的目标组件后继升级设计

## Current Status

ready_for_parent_review；父已确认独立后继方案并执行36节点RED后放行实现。新纯helper及独立loader共87项单元通过，与原candidate/activated/dependency相邻回归共216项通过；实际三服官方双包/原配置纯candidate与current/history spec构造均通过。未SSH/Docker/提交；尚无本轮三服真实新激活原文，本轮不宣称安装或恢复成功。原v1模块保持原字节。

## 目标、里程碑与预期验证

- 目标：以当前正式ACTIVATED三服153文件代次为唯一前代，设计153→153且仅common/recovery_backup_epoch.py变化的新目标代次；保留来源6968b58、Spug5651efc、全部旧receipt/custody、失败ledger和历史输入。
- 本轮里程碑：核已有candidate/staging/runtime/loader合同；确定最小后继合同与必要重构边界；写BDD和正式验证计划交父审。
- 本轮验证：静态代码审阅、UTF-8回读与仅本文diff检查；不构建、不运行测试、不重载loader、不访问服务器。
- 后续验证（获父确认再实现）：BDD→RED→GREEN→有限相邻回归，实际官方包单成员精确delta、三服真实暂存/切换证据和只读UI九对矩阵；恢复只限授权测试服58。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；不能把当前153目标重新声明成旧147，不能改变前代receipt证明或跳过原reader门禁。
- 是否从根因和长期维护角度解决：是；共享reader修复由父独立处理，本设计显式连接已激活前代和精确后继，不扩展通用升级平台。
- 是否存在临时补丁或绕过：否；不手修服务器包、不回写旧选择、不删失败记录，不升级无关source。

## 经验门禁

- Trigger：CIFS nlink打开前后观测差异、MAIN目标控制代次升级、同包153成员、既有ACTIVATED选择和失败后续办。
- Preflight check：先核当前有效target/source/Spug独立绑定，前后包官方清单与逐字pins，真实失败发生阶段与worker/业务副作用；旧receipt/custody按原spec独立实读，后继按新spec实读。
- Blocker：前代未完整ACTIVATED、任意未知成员delta、丢失前代或失败原件、目标物理配置/源信任/epoch/凭据漂移、发现真实worker或状态不明、缺真实UI入口。
- Verification：精确delta单成员+全部153 SHA/compile，独占新目录与原件保持，真实前后运行gate、三来源native/HTTP、UI九对；只记录实际阶段，不把单元PASS当服务器或恢复验收。
- Forbidden action：不重写旧receipt/custody/失败ledger，不把保留历史改绑新owner，不伪造旧147起点，不改变公司NAS挂载/fstab，不加fallback或静默降低reader安全约束，不借后继升级重复执行已成功步骤。
- Evidence：前代main-program-targets-activated-a3121c6-r2-v1.json；正式加载activated-target-formal-load-r3.private.json；本任务main-target-control-selection-tdd.md；失败操作smallapp-b4f21de7a0c64d31beda7efa0204ced8的实际服务器证据由父持有。

## 已确认的根因边界

父已保留失败operation `smallapp-b4f21de7a0c64d31beda7efa0204ced8`：Native.resolve准入阶段的epoch reader在CIFS打开前观测nlink=2，而打开后的FD/path均为1，原SHA及其它身份字段未变；尚无worker。这个事实仅定位reader缺陷，不能让新安装器替代原运行/写入前门禁。reader正式修复、BDD/TDD、固定提交的包构建和失败原件由父负责。

本轮没有重新读服务器或执行reader，不把父给出的失败定位扩写成业务恢复已通过。

## 现有合同能否直接复用

| 组件 | 可复用部分 | 当前明确不兼容点 |
| --- | --- | --- |
| main_program_target_control_candidate | path/pin、program_pin、python_path、canonical及14文档图的核验规则 | packages调用planner.manifest要求旧147；固定6新增及23/25变更；build字段形状旧版；旧target capture/preservation map只允许不存在或同pin，不能重绑定已装图。 |
| main_program_target_control_staging | `_target_package`已严格支持官方153成员+原package.json；独占目录、无alias、0400、读回、失败保留辅助 | preflight用legacy.verify_package要求旧147；重建旧candidate；固定新16文档/170路径、旧150保留路径。不能仅把147改153。 |
| TargetControlRuntimeTransition | 完整真实before/after观测、peer/业务/挂载保持、进程实读、只允许目标服务切换、旧worker拒绝、dropin顺序/依赖并集 | `_validate`要求旧147→新153及16文档；构造时original为普通RuntimeGates，会把当前新owner/control和更早legacy custody强绑，不适用于当前153目标。 |
| main_program_target_control_activated | 本机pin/私密原文读取、原始回执发布阶段与59续验合同、原生native/API证明形状、正式source v2加载闭包 | verifier回到baseInstallation.generation的旧147起点，而不是effective target153；旧candidate及16文档硬约束；不能把后继证据套入原v1选择。 |

结论：保持四个既有v1合同。新增明确的153→153后继入口；原147→153证据仍由原loader验证，不追认、不改写。底层RuntimeGates无需降低任何校验。

## 最小配置变化：每服四份新文档

不能只写owner/control两份后直接沿用整张旧保全图。产品recovery_target_preservation在实际保全和证据验证时均要求repository.captureBinderPin.path等于本轮实际import的formal_capture_recovery_inputs.__file__；后继formal来自新engine，因此repository也必须正式新代次。

也不必重新复制14份保全文档、复制凭据或重绑captureRef。单reader修复只需如下精确变化：

1. 新`preservation/repository.json`：从当前repository原值深拷贝，只将captureBinderPin改为新engine/formal/formal_capture_recovery_inputs.py的实际字节pin。该成员在新旧包字节必须相同；repositoryId、root、writeView、sourceIdentityPin、readbackTemplatePin和未知字段全部保持。
2. 新`preservation/policy.json`：只将repositoryConfigurationPin从精确旧repo pin替换新repo pin；captureConfigurationPin、captureRef、backupEpochPolicy、限额及未知字段保持。
3. 新`main-recovery.json`：只改formalModuleDirectory和targetPreservationPolicies[本target]的精确旧policy pin→新policy pin；物理targets、baselineTargetPin、source信任/归档策略、targetProgramPolicies含captureConfigurationPins、targetResourceAdmissionPolicies含OBSERVE_ONLY、epoch、凭据及其它字段保持。
4. 新`control-target.json`：两programPins重绑定新engine的同字节入口；PYTHONPATH中旧engine/control/common/formal精确换新；restoreConfigurations中精确旧owner pin换新owner pin，其它字段和值保持。

新配置根为旧target parent/configuration/main-target-<newcommit7>-rN；新engine为同parent/engine-main-program-<newcommit7>，两者都必须预先不存在、祖先无alias。旧14份图原件全部保留；新policy经新repo并引用原capture/原readback图，完整可达图仍闭合为14份（12原件+2后继），不是允许任意跨图引用。

旧的captureConfigurationPins无需修改：新policy仍使用原captureRef及精确原capture pin。只核验并保留原映射，禁止以“已存在”为由覆盖或改变其余map。

## 最小正式数据合同与API建议

### 前代

唯一前代是正式`TaskMainProgramTargetControlSelection/v1`的r2选择原pin。正式加载返回status=ACTIVATED、installationVerified=true/runtimeVerified=false，三服effective target153及对应controllerBuildBindings的buildPin精确属于同一a3121c6官方包。

当前controller原始raw有保留的历史buildPin/packageSha256字段，不能拿它们冒充当前包；当前artifact身份取前代selection.buildPin、standardPackagePin及controllerBuildBindings.target，实际engine manifest再独立读取。raw前代controller必须完整原值保留。

### 纯candidate

建议新增`MainProgramTargetControlSuccessorCandidate/v1`，状态BOUND_NOT_INSTALLED；明确predecessorSelectionPin、predecessorBuildPin、buildPin、host/targetConfigRef、previousController原值、controller新绑定、package/previousPackage、newDocuments精确4、retainedPreservationDocuments精确14和失败原件pins。

建议函数：

```python
build_target_control_successor_candidate(
    *, predecessor, predecessor_selection_pin, predecessor_build, build,
    predecessor_selection_raw, predecessor_build_raw,
    predecessor_package_raw, package_raw, host,
    preservation_documents, configuration_root, new_engine, retained_failure_pins)
```

这里predecessor必须是正式已加载结果；selection/build的原始raw必传，直接核原bytes/SHA并拒绝重复JSON key，再和已加载值比对。真实pretty JSON不得重新canonical编码冒充原文。preservation_documents由前代已验证激活candidate原始14份图取得，逐pin与前代owner/control绑定，不能凭调用者新建“等价配置”。两实际tgz都用已严格153合同验证；包成员集合完全相同，只有`common/recovery_backup_epoch.py`允许且必须字节变化，全部其余152成员字节逐一相等，两个package.json各自原字节与官方manifest/SHA/compile一致。不能接受调用者传入任意expected_changed集合。新build需固定已提交输入、正式构建PASS；旧build为前代原build，而不是base历史147格式。

### 文件暂存

建议独立`preflight_target_successor_filesystem`/`stage_target_successor_filesystem`，复用已验证目录/写入辅助和_target_package；首写前重新构造candidate并等值、固定所有实际old pins。

本轮每服：153 payload+原package.json=154包文件，4新文档，总158个新文件；完整保持前代154包文件+前代16配置图原件=170个文件（其它旧历史仍由完整runtime门禁读取）。所有新文件独占0400/无softlink/hardlink/alias，部分失败保留路径且不自动回退或重派。返回FILES_STAGED_RUNTIME_UNVERIFIED，不授予安装或恢复资格。

### 实际运行过渡

建议明确`TargetControlSuccessorRuntimeTransition`：当前before spec来自前代targetRuntimeSpecs[host].successor的确定性完整值；legacy历史spec独立来自前代targetRuntimeSpecs[host].original。两者的不同是显式角色关系，不能通过临时替换custody、owner或current字段骗过原RuntimeGates。

- before：以`RetainedHistoryRuntimeGates(current153_spec, retained_gates=RuntimeGates(original_history_spec))`真正实读当前153进程/包/配置，旧receipt/custody/inventory仍委托原147绑定实读。
- after：新153运行spec仍以同一原历史gate处理legacy custody；本轮前代153激活回执、原新dropin、16配置图、旧153 package完整加入本轮retained/history pins并真实再读，不能仅依赖旧选择快照。
- 原历史receipt所在路径、current153独立激活receipt和本轮新receipt三层分开，均不旋转。
- 真实before→after只允许本host target行、相应package pin、唯一新dropin和指定owner/control/engine/PID变化；source/其它controller/业务容器/原mount/fstab/epoch/保全view/失败ledger全部保持。
- 保全view依赖已存在，明确addedDependencies={Requires:[],After:[]}，原Requires/After全部原样集合保持；不新增、删除或重复依赖。DropInPaths原顺序+唯一新pin。
- 候选精确4文档、旧153→新153两官方artifact身份独立验证；不能将旧验证条件简单改为`old.fileCount in (147,153)`。
- before与after完整原件、PID实际argv/env/exe和无旧worker分别核；新增本轮activation receipt独立目录、canonical闭合。

现有transition的方法可复用，但构造器的original gate及_validate有真实版本分歧；后续可小范围提取共同unit/dropin/观测比较到私有helper，保持原v1测试/合同；新的明确class提供153/4文档及原历史委托。禁止将旧spec暂时改成147、用旧candidate schema假装兼容、或复制整个RuntimeGates实现。

### 后继selection/loader

建议`TaskMainProgramTargetControlSuccessorSelection/v1`精确五字段：

```text
schemaVersion
predecessorSelectionPin
buildPin
standardPackagePin
targetActivationEvidencePins  # 精确57/58/59
```

建议API：`load_activated_target_successor_installation(task, private, *, selection_file, historical_source_custody_pin=None)`。

这个入口只承认本次既有v1选择为前代（不引入任意代次递归平台）。先正式调用原loader全闭包，再读本轮三份真实激活wrapper；每份新activation须显式绑定predecessorSelectionPin和前代activationReceiptPin、current153 raw、current spec/原历史spec以及本轮candidate/transition/native/API。不能再引用base147作为当前目标。

输出仍只覆盖effectiveControllersByHost中的三target和target owner/control；sourceInstallation/baseInstallation及原predecessorInstallation完整保留，source6968b58、Spug5651efc独立版本保持；controllerBuildBindings.target换新build，status ACTIVATED/installationVerified=true/runtimeVerified=false。返回inputPins包含完整前代和当前全部本机原件及代码依赖，结尾重新核pin。

原失败ledger和本次失败operation原始终态应由实际安装载体在同一物理锁下完整固定，加入新activation的retainedFailurePins/observations前后相等；只读loader实际读本机原始结果pins并核它们绑定远端原件SHA。新选择不把FAILED改成功、不创建clearance或重派恢复。

## BDD场景（实现前必须先RED）

1. Given 三服a3121c6正式ACTIVATED，前代所有pins闭合；When 单reader的153→153官方包构造后继；Then 只允许该唯一成员变化及四份明确配置变化，其余全部保持。
2. Given 任一旧包不是前代build、当前target被假装147、成员增加/删除或第二成员变化；When 构造/暂存/加载；Then 首写前拒绝。
3. Given 原14图已登记captureRef；When 仅新repo binder/newpolicy/newowner/newcontrol；Then capture配置map、凭据、baseline/物理目标/epoch/资源策略都保持，binder指向真实新formal同字节成员；直接旧binder或额外map修改拒绝。
4. Given 旧legacy custody仍绑定原147，当前实际进程是153；When before/after真实检查；Then 分别按current153和retained original147 spec实读，旧receipt保持，未知变化拒绝；普通RuntimeGates误绑应在RED暴露。
5. Given 新engine/配置根已存在或原件/alias/模式漂移；When 文件暂存；Then 首写前拒绝；部分失败则明确保留已创建文件，不自动删除/重试。
6. Given 真实58失败记录仍FAILED且无worker；When 三target控制升级；Then 失败原件、ledger和全部业务/源/NAS状态保持，不执行恢复、不授权新恢复。
7. Given 少一服激活证据、仅BOUND或本地PASS、前代receipt不符或native/API缺失；When 后继loader加载；Then fail closed，原v1选择仍可核原历史且不伪称最新安装。
8. Given 完整三服后继真实证据；When 新选择加载与真实Spug页面核九对；Then 只投影三target新版本，source/Spug/点/历史原件保持；随后仅测试服58通过真实前端发起新恢复操作并按原合同验收。

## 建议后续实现文件范围与阶段

父最新限定范围：保持全部既有candidate/staging/activated/runtime字节，不修改旧148/170合同。只规划新`main_program_target_control_successor.py`的明确纯helper入口与对应`test_main_program_target_control_successor.py`，加独立TDD文档。helper负责本次纯candidate、只创建暂存计划及激活证据投影；实际文件独占暂存与运行前后检查由父安装载体执行，复用现有底层RuntimeGates/RetainedHistoryRuntimeGates，传递已验证current153 spec与原历史147 spec。

上文建议class是运行语义说明，不批准本轮改旧runtime或复制其实现。若父载体无法用已有底层gate完成明确153前后检查，应先报告具体缺口，不能为了复用旧147 transition而改spec/count。

1. 父已确认独立successor选择与4文档方向；先只写BDD及有限纯测试，父执行RED后再放行实现。实际新build commit和单成员delta由父准备，本文不预批未知差异。
2. candidate纯重建+4文档闭包，TDD先行；实际两包一次纯核验，不冒充安装。
3. staging真实本机POSIX文件协议；runtime真实本机进程/文件/旧custody分层协议；loader纯pin/原始证据，有限邻接回归。
4. 父按已授权范围执行三服逐服真实read-only preflight→独占暂存→切换控制服务→after双核，旧业务和挂载保持；全部原始结果固定后生成新选择。
5. 完整新选择只读加载、真实Spug九对页面选择验收；真实恢复仍只58，新操作必须保留旧失败关联，缺前置直接报告。

## 本轮设计验证与剩余前置

- 已静态检查四现有入口的固定147/153/16/150约束、RuntimeGates.retained_custody旧绑定规则，以及产品两处binder实际路径强绑定。
- 本轮仅新增本文；没有执行测试/loader/构建、没有远端连接、没有产品或测试文件改动。
- 未知且需父提供：reader最终提交/新官方build+双包pins；新激活原始shape和本轮失败ledger固定证据。缺它们阻断安装/实际恢复，不阻断本设计审查。

### 实现阶段补充（父审后）

正式新build为b9caa00b7eeed2b915c8855a8313521e57d06f72，标准包153成员；父已独立验证官方producer。子任务读取父已完成的1668-pin前代加载快照和官方两包，仅生成本机纯candidate/计划，不访问服务器。每服四新文档、158写计划、170保留pin；原件PRIVATE/nas-reader-actual-successor-candidates-r1.private.json。

正式新helper只新增一个模块；实际文件系统独占创建/前后运行观察由父载体执行。`build_target_successor_runtime_spec`仅构造明示current153→new153规格；`verify_target_successor_activations`先重建candidate及规格，再复用旧纯比较/native/API检查，不调用旧147构造器。58失败原件由carrier实际pin_file得到failurePinsBefore/failurePinsAfter，并严格等于retainedFailurePins；57/59明确为空。

独立loader公开API同前述；它调用原v1完整loader验证前代，再实读新五字段选择和三份本轮wrapper/脚本/官方包，所有本机输入和代码pins结尾复核。纯unit中formal-loader边界注入只验证调用协议与真实临时文件pin行为，不冒称完整历史链已在本轮重新加载。父随后提供真实三服激活原文后，才可生成新正式selection并运行完整loader及真实UI验证。
