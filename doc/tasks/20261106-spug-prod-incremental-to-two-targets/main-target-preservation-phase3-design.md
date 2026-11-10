# MAIN 目标保全阶段 3：正式封包与配置登记设计

## Current Status

design_ready_for_review。只读评估已完成，等待阶段 2b 最终冻结及父任务审查。当前运行的 b5/r7 STANDARD 147、LIGHTWEIGHT 146、Spug 565 和已冻结 current dispatcher／1630 原件闭包保持；本阶段没有构建、测试、安装、服务器访问或产品修改。设计不等于功能可以部署。

## 目标与里程碑

1. 核对阶段 1／2a 已提交输入与阶段 2b 边界，确定新增模块、SAFE 共用方法及真实调用入口。
2. 定位旧 147／146 封包、增量证据、配置计划和代次读取合同的边界；提出显式新合同，旧历史读取保持原样。
3. 定义有限 BDD、真实双包验证和三服 MAIN capture／preservation policy 登记前提。
4. 交父任务审查；批准且阶段 2b 冻结后才开始 RED 与实现。

## 设计约束检查

- 是否引入 fallback／降级／吞异常：否。未知成员、缺失 SAFE 调用、未绑定配置、未通过真实封包验证均阻断。
- 是否从根因和长期维护角度解决：是。新功能使用显式版本及完整成员闭包，保留旧代次的原证据合同。
- 是否存在临时补丁或绕过：否。不改旧冻结 reader 的常量、不重算旧 pins、不拼接脏工作区发布输入。

## 经验门禁

- Trigger：新增 capture／preservation 进入 STANDARD 和 LIGHTWEIGHT。Preflight check：核真实成员清单、已提交输入和实际封包入口；SAFE 内容读取与 source restoration 生命周期逐项保持。Blocker：只存在源码、构造漏传 policy、封包缺成员或完整读回证明不足。Verification：两个实际封包分别执行构造、材料捕获、发布读回、handoff 和失败边界。Forbidden action：把本机轻量源码或自报 PASS 当作 SAFE 包证明。Evidence：`docs/release-agent-checklist.md` 的“实际封包构造配置传递门禁”“覆盖前保留备份完整读回门禁”。
- Trigger：控制组件与配置新代次登记。Preflight check：旧历史清单、原 receipt custody、实际目标身份／共同物理锁／恢复 epoch／宿主资源预约完整关联。Blocker：身份或原件未核、历史读取需要覆盖旧文件。Verification：旧成员合同与旧历史仍可原样读取，新代次逐成员及配置关系验证。Forbidden action：更新旧 receipt、伪造旧成功或用 SMALL 身份代替 MAIN。Evidence：同 checklist 的“授权控制升级的活动回执历史保全”“自动增量链与恢复周期门禁”。
- Trigger：后续构建／发布。Preflight check：阶段 2b 冻结、父任务批准、新建目标提交的干净发布 worktree。Blocker：未提交或脏输入、最终成员集合未定。Verification：实际两包逐成员 SHA／编译与同提交测试原件闭合。Forbidden action：本阶段构建或套用旧 147／146 测试证据。Evidence：任务主计划与 AGENTS 的发布 worktree、BDD／TDD 规则。

## 1. 已核事实与本阶段边界

检查起点为 `e59899af64f1a8dbee7ae8f1452bd32a592d3699`，阶段 1／2a 的父任务实现提交为 `685e8e0`。依据 `target-preservation-2a-freeze-r2.json`、`target-preservation-parent-freeze-verification-20261110-r3.json` 和两阶段计划，原源码验证不含双包构建、目标登记、业务恢复。阶段 2b owner 明确尚未最终 GREEN：它不新增产品模块，正在接 handoff、producer、runtime、stage／first-clear、历史验收和 retention。以下三个新增成员仍是正式封包 HOLD：

| 已存在源码 | 应进入两包的成员 |
| --- | --- |
| `ops/recovery/recovery_capture_materials.py` | `common/recovery_capture_materials.py` |
| `ops/recovery/recovery_target_capture.py` | `common/recovery_target_capture.py` |
| `ops/recovery/recovery_target_preservation.py` | `common/recovery_target_preservation.py` |

当前 `files.json` 为 143 个映射，加三个入口形成 LIGHTWEIGHT 146。映射里的 `formal/minimal_capture_worker.py`、`formal/minimal_capture_support.py` 仍来自 `ops/backup_engine/formal/`；阶段 1 提取后的严格来源 worker／support 在 `ops/recovery/`。因此只增加三行映射无法接通共享材料入口。若最终只增加这三个成员，算术上才是 STANDARD 150／LIGHTWEIGHT 149；这不是已验证的最终成员清单，不能先写进运行回执。

`build_variants.standard_sources()` 认证冻结 tar，`standard_fixes.apply()` 进行具名修订；LIGHT 从显式 mapping 读当前源码。`write_package()` 还会改两处归档前缀。新证据必须核最终 tgz 原字节及每个最终成员，不能把源文件原 SHA 直接当作变换后 SHA。`build_variants` 自身不实施干净工作区门禁，发布执行器必须在调用前后核目标提交和完整输入；不能因为当前工作区可调用 builder 就在这里构建。

阶段 3 分三个可独立冻结的里程碑：3A 正式材料入口／模板与双包合同；3B 已证实际身份的纯配置计划；3C 新代次 staging／activation／只读验收。批准 3A 不自动表示准许生成现场原件或安装。阶段 2b 的 typed proof 和历史／retention 接缝必须先冻结，3A 才能开始产品 RED。

## 2. SAFE 与 LIGHT 的正式接线

### 2.1 复用对象及保持项

`recovery_capture_materials` 是唯一材料算法编排入口；`SourceCaptureLifecycle` 与 `MainTargetCapture` 是两种具体生命周期，不增加 skip-restore／skip-stop 布尔。MAIN 继续同 ctx、同 PID 物理锁、同预约、同 deadline；普通来源仍由原 worker 无条件执行真实 `Runtime.restore()` 并保存 `sourceRestorationPin`。

STANDARD 不允许整文件替换成当前 LIGHT 版本。具名 transform 须先认证现有 SAFE 输入段，再迁移共享入口及必要 transport hook，保留未改段的原字节／AST证明。必须保留：`semantic.verify_parent()` 和 `semantic.close()`、完整 reference inventory、完整 bucket dependencies、multipart 拒绝、数据库前后内容／schema、对象全版本／删除标记／headers／内容 SHA、Redis DUMP 与绝对到期、完整载荷上传／读回、真实 binder、持续租约、原严格 cleanup 与清理后 published chain 验证。

当前 `MainTargetCapture._semantic()` 构造所加载的 `MinimalSemantic(..., process_observer=...)`。LIGHT 映射的类没有该参数，且它的 `SemanticCapture.finalize()` 明确产生 `complete=False`。因此 MAIN 在 LIGHT 中也必须选严格材料语义，不能仅补参数后接受轻量结果。建议在现有 `recovery_capture_materials.py` 中形成具名、唯一的严格 MAIN 语义适配器，从认证 SAFE 方法提取共享实现；SAFE 对应方法调用同一实现，LIGHT 的普通来源类仍走原合同。它只绑定已有正式 SQL／对象／Redis算法，不新造另一套算法。若完整方法提取不能在这三成员范围内无循环地完成，必须在 RED 前明确新增的唯一模块与调用边界并重新审查成员集合；不得构建后靠扩大 allowlist 放行。

### 2.2 精确接缝

| 接缝 | 最小改变与必须验证的行为 |
| --- | --- |
| `files.json`、`standard_fixes.apply()` | 三新 common 成员显式登记；具名材料 transform 处理真实 worker／support／semantics 的调用与 observer 参数。不是扫描目录自动收录。 |
| `formal/minimal_capture_worker.py::capture_locked` | SAFE 普通 FULL 调用共享材料段，原 try／primary error／来源恢复及 parent lease 收尾保持。LIGHT 普通 FULL 保持原公开语义，不顺手改成 SAFE。 |
| `MainTargetCapture._semantic/_mysql/_verify_objects` | 两实际包都选明确严格 MAIN 实现；调用真实 endpoint、query、dump、schema、data、image、Redis transport hook，`__file__` 必须属于该实际包。 |
| `repository_native_readback` | 复用阶段 2a `read_verified`／`PreservationReadback` 的实际完整读取；SAFE 原 `SmbReadback.read` 通过具名方法共享保持原严格校验，LIGHT 默认 reader 不被隐式改写。 |
| `repository_minimal` | 将 `publish_materials` 的 typed 边界加入 SAFE；保留原 SAFE `publish` 的完整校验和普通来源终态，不整体替换为含 `verify_content=False` 的源码文件。 |
| `recovery_minimal_runtime` 的 SAFE transform | 显式传递阶段 2b 的 `target_preservation` 能力；`ctx.stage` 和 `clear` 独立核同能力。不能只把字段写进 owner，而实际构造丢失。 |
| `recovery_program_restore/native/protection/evidence`、`recovery_replace`、`repository_retention` | 按 2b 最终冻结输入登记共享模块；真实 producer→history 消费同一 `targetPreservationPin`，保留仓库 hold 不进普通增量基线。 |

阶段 1 已有的 query／dump、SchemaMySql、DataMySql、bounded reference、image save、endpoint、Redis client observer 都要在实际包执行链中验证。存在两份 DataMySql 源不能通过测试换 import 遮掩；SAFE 对 `verify_endpoint` 的纯 candidate 实验不是正式 transform 已完成。

## 3. 可重复使用的保全读回模板

### 3.1 已证阻塞

阶段 2a `TargetPreservation.prepare()` 要求静态 repository 的 `readbackConfigPin.recordRoot` 等于本次 `context._root/target-preservation/publication`。操作根随 operation 改变；2b owner 确认没有正式派生路径。测试给每操作生成独立 policy 只证明协议，不证明长期登记可用。不得把单次 policy 安装到三服，或运行时改原字典／旧 pin 绕过相等检查。

### 3.2 限定新版合同

使用 `MainTargetPreservationPolicy/v2`，保留 v1 所有身份、capture、epoch、预算字段；`repositoryConfigurationPin` 显式只允许指向 `MainTargetPreservationRepository/v2`。v2 repository 字段为 `schemaVersion, repositoryId, repositoryRoot, sourceIdentityPin, captureBinderPin, readbackTemplatePin`；v1 repository／policy 和旧结果读取逻辑保持。

`MainTargetPreservationReadbackTemplate/v1` 的精确字段建议：

`schemaVersion, uncRoot, repositoryRelativePath, repositoryRoot, credentialPin, port, authProtocol, maximumRecordBytes, maximumTotalRecordBytes, libraryPins, recordRootPolicy`。

`recordRootPolicy` 只接受字面量 `CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION`。模板没有 command、host 任意 path、format／环境变量表达式、用户传入 suffix 或 recordRoot。repositoryRoot 必须与已核 repository 相同；凭据和 libraries 只保存原 pin 引用，不能复制、重新测量后冒充原 pin 或公开内容。固定 root 由原不可变 owner/request/binding 对应的 ctx._root 证明，不取可漂移的 native.root 或请求参数。

派生次序为同 ctx 物理锁／预约／预算已验证后、首次 quiesce／capture fence 前：

1. 核模板、policy、repository、owner/request、binding、原目标、epoch 和所有允许 root 的原件／身份；私密目录、无链接／别名、和数据／清理／epoch／历史读视图不重叠。
2. 在固定 `operationRoot/target-preservation/publication/` 下，以 0600、O_EXCL／NOFOLLOW、目录 FD 身份复核和 fsync 独占写 `readback-configuration.json`。它是原 `RepositorySmbReadbackConfig/v1`，连接字段逐值来自模板，唯一生成项是固定 `recordRoot`。
3. 独占写小型 `MainTargetPreservationReadbackDerivation/v1`：`schemaVersion, operationId, targetConfigRef, policyPin, repositoryConfigurationPin, templatePin, executionBindingPin, operationRoot, configurationPin`。固定文件为同目录 `readback-derivation.json`。
4. 必须调用正式 `PreservationReadback` 校验实际配置及原认证／library pins，成功才允许进入停写。它只能生成自己的新连接目录；派生文件自身不是连接成功或备份成功。
5. v2 publication intent 绑定 `readbackDerivationPin`；v2 archive／preservation结果通过原 intent 和自身列出的实际原件闭合它。若要新增字段，使用对应结果的 v2 严格分支，不能给旧 exact v1 增加可选字段。历史消费只依据这些固定原件重建模板→实际配置关系，不读当前 policy 或重算旧证据。

同一长期 policy 可被 operation A、B 分别使用，生成不同固定目录、相同模板 pin 和连接声明；同 operation 已有文件即失败，不覆盖、不自动续办或重用 A 的配置。派生失败发生在停写前则证明实际未派发；已派发连接的异常保留真实阶段和原件。单纯解析失败不能把已知结果重写为 UNKNOWN。

## 4. 新包证据合同，旧 147／146 不变

### 4.1 新的有限 profile

建议只新增 `profile=main-target-preservation/v1`，由一个独立 `main_target_preservation_package_evidence.py` 验证。旧 `MainProgramChainPolicyPackageDelta/v1`／`MainProgramControlCoverage/v2` 及 catalogue v2／coverage v1 的字段、常量、批准模块集合不改。

新 delta 使用 `MainTargetPreservationPackageDelta/v1`，精确绑定 `status, profile, sourceCommit, predecessorCommit, predecessorGenerationPin, buildPin, predecessorBuildPin, sourceSnapshotPin, packages`。packages 固定 STANDARD 和 LIGHTWEIGHT 两项；每项包含实际 `packagePin, packageJsonPin, fileCount, fileManifestSha256, predecessor` 及互斥完整分区：`addedMembers, removedMembers, changedMembers, unchangedMembers`。每个新增项核来源成员／变换记录及新 bytes/SHA，每个改变项核旧新 bytes/SHA 和明确 transform；未变项核双方相同原 SHA。初次 profile 的 removedMembers 必须为空；批准新成员集合在 2b 和严格 MAIN 入口冻结后写死为有限集合，不接受报告自报集合充当批准范围。每 variant 单独核，不能假定两包同名成员相同。

新 coverage 使用 `MainProgramControlCoverage/v3`，精确字段为 `schemaVersion,status,profile,sourceCommit,baselineGenerationPin,baselineBuildPin,candidateBuildPin,packageDeltaPin,sourceSnapshotPin,verificationPin`。它不要求制造一次安装失败。历史失败测试有真实证据则由 verification 引用保留，不能把先前失败删掉。

`MainTargetPreservationVerification/v1` 采用已有证明模式：同提交 source snapshot 与显式 ExecutionInputRoot、持久 tar／tgz、每条实际 command/input/collection/result/stdout/stderr/exitReceipt pins、实际 loaded module __file__／SHA、输入前后完整树不变。source、STANDARD、LIGHTWEIGHT 为明确模式；每条必要 suite 完整 collection、tests>0、exit0、fail/error/skip0。由独立 validator 从持久原 tar／tgz 重读成员，不能只信自报 PASS、SHA或临时容器路径。沿用已批准跨平台 root／evidence root 映射规则；新 helper 可以复用与 profile 无关的严格 path/tar/XML 原语，不能复用旧固定三模块／suite／数量准入。

构建与所有最终验证须来自同一已提交 sourceCommit 的本次新建干净 release worktree。包括 builder、mapping、冻结原 tar、具名 transforms、产品源、tests、runner／validator 在 committed input snapshot 内；PRIVATE 原件不混进代码包。临时工作区删除后凭持久原件可继续验旧代次。禁止把阶段 1／2a／2b 源码 PASS 拼成新包 PASS；它们是根因与设计依据，正式发布需重跑受影响实际包用例。

### 4.2 已定位的旧合同边界

| 文件／函数 | 当前严格约束 | 新阶段处理 |
| --- | --- | --- |
| `main_program_control_upgrade_plan.manifest/validate_delta/plan_control_upgrade` | 147；同成员集合；旧三个语义模块；8 新＋27保留文件 | 旧函数不改。新纯 planner 消费新 profile 的完整 manifest，额外登记文件显式分组，不能借旧 8＋27 函数放行。 |
| `main_program_chain_policy_evidence` | STANDARD147／LIGHT146、三模块及固定 suites | 保留原文件；新 evidence helper 独立约束本次有限 feature profile。 |
| `main_program_control_activation.validate_generation_coverage`、remote candidate | 旧 coverage v1/v2；候选有 fileCount=147 | 不 patch 冻结 reader／REMOTE_SCRIPT。新安装入口只消费新 coverage，候选数量由已核完整 manifest提供。 |
| `main_program_control_staging.verify_package/stage_filesystem` | build147；已写 engine 回执147；SOURCE before 固定 READY及原链 | 新入口复用安全文件原语和 RuntimeGates，不把新包喂旧函数。源已合法 AGE_EXPIRED 时只能依当前正式 source-policy proof，不能任意接受 baseline 状态。 |
| `main_program_control_generation._upgrade_build/_partition/_validate_upgrade_materials` | build147；public/private v2；每 host 新4/2/2、保留9；同旧 coverage | 新 loader 接新 plan/profile，旧 loader只验证明确的 b5/r7 predecessor，不把新记录伪装成它已支持的旧升级。 |
| `main_program_spug_publication.validate_packages/VERIFY_HOST`、r7 acceptance | 两包147/146、host147、r7有限输入 | 只作为旧发布证据读取。新只读验收必须关联已核的新代次成员清单；不能复用原固定程序并篡改其结果。 |
| `main_program_current_installation.public_summary`／当前 dispatcher | 当前147、已冻结1630闭包 | 本轮不动。新代次将有显式新验收入口和选择原件；旧 current 仍按原 reader 读取，不重算旧闭包。 |
| `main_program_control_runtime.RuntimeGates.verify_package` | 实际 package.files 与明确 row.fileCount／manifest 相等，并逐成员读 SHA | 可原样复用；它没有147常量。新的调用者必须先通过有限 profile，不能任意传一个较大数字。 |

## 5. 最小代次工具和配置计划边界

建议新增三个责任明确的 TASK 模块，而非给旧 helper 扩大常量：

1. `main_target_preservation_package_evidence.py`：上节 profile、两包成员和原始验证证据的唯一 validator；配一个固定 runner 与专属合同测试。
2. `main_target_preservation_control_generation.py`：纯新配置计划和对应后继 loader。新 plan 使用 `MainProgramConfigurationPlan/v3`／private v3；保存已核 predecessor generation、build、delta、coverage、每 host 明确的新控制文件／新增支持文件／原27保留文件。controller角色、service、端口、原 targets／sources、12 selectors、原 Spug565／七配置／四连接 payload 保持，新增 capture 仅供目标内部保全，不创建 .58/.59 来源服务。新 loader 的外层 generation 可沿现有字段形状，由显式 plan-v3/profile 唯一入口读取，不为了成员数另造通用代次平台。
3. `main_target_preservation_control_installation.py`：在上两者已验证的材料上组织新的有限 staging／activation／只读验收入口，复用未改的 RuntimeGates、physical lock、environment／custody 和 O_EXCL 文件原语。不能复制整份旧 REMOTE_SCRIPT 再替换数字；先用测试证明可共用的子程序边界，旧 observer／reader pins不改。其实现属于后续 3C，不由本文授权立即执行。

新 plan 明确区分原8个 controller/owner 替代文件与每 host 新增 capture、object/source identity、版本材料、repository、template、policy 等支持文档。支持文档数量依实际 pin闭包而定，不能先规定每服同样数量；相同已核旧文档可按原 pin复用。旧27文件逐 path、bytes、SHA、value保持，新文件只在新的代次配置目录独占生成。所有支持 pin 必须可达且只允许该 target/host；未引用文件、跨host credential或将 .57 source identity用于 .58 都失败。

保持现有四 controller 的角色关系，不新建历史停止的 source服务。是否同时升级现有 .57 source由实际调用差异和父部署范围决定；若只升级三 target，必须显式记录各 controller 的不同 build pin，不能让旧147 source冒用新 manifest。优先沿原统一四 controller 的已知安装关系评审，避免为本功能额外构造隐式混代假设；实际安装范围由父任务最终确认。

后继 generation 尚未实际完成前，current 选择仍指向 b5/r7。新 stage 不是激活，新控制 health/imports不是 Spug验收。完成后新只读验收重核实际控制和原12selectors、565资源／七配置／四连接原 payload；如果它们没有改变，就准确记录“控制代次验收”，不声称发布了新Spug文件。当前旧 reader／1630闭包以及旧失败／activation输入完全保留。真正需要接下游消费者的新选择接口，另行以其精确 schema 分派做有限审查，不能本文顺手 patch旧 dispatcher。

## 6. 三服真实登记前提

旧本机已核配置显示 .57 MAIN 有一个 capture 映射；.58/.59 MAIN 的 `captureConfigurationPins` 为空。这是旧发布原件的事实，不是今日远端运行态证明。当前 b5/r7 必须由父从正式 current loader 得到准确 owner/target pins后做新鲜只读观测。

| 目标 | 可以沿用的依据 | 仍须证明或正式新增 |
| --- | --- | --- |
| .57 MAIN | 已有自身 source identity／capture／共同锁与 epoch 的历史登记 | 当前 active capture 与真实五服务、程序代次、权限、资源预算、独立保全写根／SMB模板完整一致；不能把传入恢复来源当当前目标。 |
| .58 MAIN | 当前 MAIN target、epoch、物理锁、原程序保护 | 自身 sourceIdentity／UUID、完整 FULL capture／对象描述／版本材料／Redis身份、模板／repository／policy。禁止套 SMALL58 或 .57 身份。 |
| .59 MAIN | 当前 MAIN target、epoch、物理锁、原程序保护 | 同样新增自身当前 MAIN capture；旧59来源或旧路径漂移不能作为当前采集登记，更不能为凑登记启动旧服务。 |

每服必须固定五服务完整 ID／image／配置材料、唯一数据库及UUID、全部writer、MinIO真实RW目录／完整bucket和凭据引用、Redis db/auth、正式工具和library pins、网络/端口、外部及共享写者归属。capture parent=None，sourceLockPath 与目标 replacement／epoch同一物理锁。`MainTargetCapture._configuration` 要求 capture.archiveRoot 已在 incoming source 的 archiveRoots内；要逐现有可恢复来源核它是否成立。若真实布局不满足，明确缺哪个受保护读视图，不能把可写保全仓库塞进所有历史 source archiveRoots 或改原27配置来绕过。

保全 repositoryRoot 必须为已登记可写目的，与输入归档只读视图、目标dataPaths/dataRoot、replacement stateRoot、epoch、操作暂存／清理范围不重叠。SMB auth/sign/encrypt、实际完整读回、服务器视图绑定、仓库锁／dynamic holds、合并磁盘余量／临时展开／元数据记录／总deadline都要明确证明。禁止修改公司 `/mnt/nas`、fstab或解除旧保护来制造可写目的。未获得完整前提，只阻塞对应目标的启用，不编造配置或让 typed MAIN静默无保全覆盖。

### 条件门禁：追加 capture 与原程序代次

`recovery_program_generation._resolve_state` 对每个成功 MainProgramGeneration/v1 核整个 program policy 的 `policySha256`，并要求 captureBindings 键集合等于 policy.captureConfigurationPins。新增 .58/.59 capture 会改变这两个约束。

父须先只读核原 initial READY、当前 READY及两者之间的真实程序代次。若仍处原 initial READY且无成功程序代次，依旧合同核新capture与原baseline一致后才可规划登记；不得把这个前提当作已成立。若已存在代次，当前阶段明确阻断直接追加，另外审查必要的有限策略接纳方案；本设计不预建 adoption平台。任何情况下不改 initialEpochPin、不回写旧policy/generation，不把旧captureBindings重新签成新值。

## 7. BDD 与有限实际验证

以下是待批准后执行的 RED→GREEN→REGRESSION 场景，本轮未运行：

1. **两包真正可达。** Given 同提交实际STANDARD／LIGHT tar及严格MAIN原生fixture；When 正式entry→实际构造→prepare→capture→publish→handoff→producer；Then 三新模块和全部transport实际从该包加载，typed能力到stage/clear，完整读回和原件证明闭合。现有 `test_capture_materials_lifecycle.py` 三个包缺口先保留真实RED；不能仅源码字符串检查转绿。
2. **SAFE不降级／LIGHT MAIN仍严格。** Given对象reference／bucket依赖／multipart／SQL内容／Redis到期发生不一致；When各包MAIN捕获和归档；Then在clear前拒绝。普通SAFE FULL成功与失败仍实际恢复来源；普通LIGHT来源结果维持旧差异。原五项SAFE认证义务逐条实跑。
3. **静态模板多操作。** Given一个真实私有模板及policy、两个各自原ctx/锁/预约；When A和B分别派生／读回；Then两套独占固定原件，模板原字节不变；A重入、跨operation绑定、任意root、别名／symlink、凭据pin变化、外部命令字段均拒绝，首次停写尚未派发。
4. **读回链真实性。** Given真实SMB协议fixture和完整载荷；When内容后段改变、read-before/after身份漂移、少raw record、错binder、错sidecar、预算超限；Then无handoff／stage／clear。实际Linux/SMB fixture的用途只证明协议，不冒称生产NAS备份成功。
5. **新增成员闭包。** Given两个实际tar；When删一个新成员、加未知成员、重复tarname、链接／路径外逃、跨variant包、manifest或transform/source原件不符；Then新profile失败。新count由完整批准集合验证，不接受单一count相等。旧147/146验证输入及结果不变。
6. **同提交证据。** Given source snapshot、package、loaded module、collection和exit原件；When跨commit、少必要suite、skip、失败、伪collection、stderr/exit被替换、输入前后漂移或runtime映射外逃；Thencoverage失败。无任何“测试未跑但已有旧PASS”路径。
7. **配置传播。** Given真实三目标owner／policy协议fixture；When实际包构造到首次数据库访问边界；Then仅选中目标的capture／preservation/template pins被绑定，缺失／错误身份明确失败，构造预检不启动停写。两包均覆盖，不能手填native属性假装传递完成。
8. **原件及历史保持。** Given原b5/r7／旧27／四controller／12selectors／current闭包；When纯新计划及新代次读取；Then旧pins不变，新增支持闭包完整，旧reader继续读原代次；新包误送旧reader仍拒绝。旧retained/no-mutation/unknown/释放等回归消费2b正式证据，不删除旧失败。
9. **登记条件。** Given原initial READY与有成功程序代次两种真实协议文件；When尝试追加capture；Then前者严格核baseline关系，后者本阶段明确拒绝，需要单独方案；不得自动刷新initial READY或重写policy摘要。
10. **现场验收边界。** Given已实际激活的新代次；When父执行真实Spug原恢复按钮一次；Then自动保全→完整读回→保留保护交接→恢复／验证全链，无Codex补采。此项只在所有前置通过后由父执行，源码／封包PASS不计为现场完成。

实际封包测试按有限职责分为材料／生命周期、出版读回／handoff、完整producer→history→retention、构造传播／旧恢复回归四组；每组两个包分别在真实Linux独立进程运行。需要真实资源的组缺环境即阻断，不能skip或用虚假业务成功替代。保留失败原log，全部终态由外层runner核验，实际运行前后原包与源码SHA保持。数量不预先伪定，完整collection与已批准场景集合必须双向闭合。

## 8. 本轮交付和未完成项

本轮只新增本文。已只读核源码、mapping、冻结报告和旧验证器；没有执行 safe_fixes／builder、pytest、远端命令或业务操作，也没有读取凭据内容。

尚未完成：阶段2b最终GREEN／freeze；严格MAIN在两个包的具名方法共享；上述模板正式合同及测试；实际双包／新profile实现与同提交证明；三服新鲜身份和资源观察；必要配置／generation条件门禁；新的staging／activation与真实Spug保全恢复验收。父审查前不进入实现。
