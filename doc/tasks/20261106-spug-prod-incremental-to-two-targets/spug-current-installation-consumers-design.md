# Spug 当前控制验收消费者接入设计

## Current Status

design_review。本阶段仅只读设计，不修改生产/测试、不执行验证器/远端/构建/提交。沿用同一完整 MAIN 任务，新 r7 控制须保留 Spug 原七配置与四旧连接；新独立 acceptance 模块由 backend owner 冻结。此前 scope 子阶段本机 15+214 和父真实 Linux 叶symlink已通过，源/测试冻结；父已在其收口日志记录补充结果。

## 目标、里程碑与预期验证

避免修改被旧五 attempt 精确 pin 的 installation_selection、旧五 reader 和历史 custody。以新独立显式 dispatcher 消费旧发布验收或新控制代次独立验收，并只改未被历史 attempt 绑定的当前 UI preflight、备份链审计和最终只读观察消费者。

1. 只读核当前 acceptance/selector/消费者及五 attempt 的完整文件 pin，固定影响范围。
2. 给出精确 API、有限 schema 分派、历史565资源build/guard-after/七配置来源。
3. 给出实现前 BDD/TDD 和必须保留的旧分支行为，交父审阅；本子阶段不实施。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。verificationInputsPin 精确 schema 决定分支；未知/缺失schema拒绝，不隐式选择最新文件，不注入callback替代正式校验。
- 是否从根因和长期维护角度解决：是。控制代次验收与历史 Spug 安装是不同事实，使用显式 proof 分派及统一消费者视图，不伪造安装回执或改写旧原件。
- 是否存在临时补丁或绕过：否。旧 verifier 及历史pin保持；新消费者须携带新 acceptance result真实pin及完整验证闭包。

## 经验门禁

- Trigger：Spug保留旧资源/连接，仅新控制代次已验收，需要真实UI/链审计消费。
- Preflight check：按 experience-index 命中的运行依赖闭包与活动回执历史保全，先核五attempt所有inputPins/helper绑定、明确新acceptance完整inputPins来源；读取565资源build与guard-after时必须在已验历史context闭包内。
- Blocker：拟改文件被历史pin绑定；新acceptance伪装旧安装schema；缺历史资源build/guard/实际七配置证明；未核完整验收而仅信自述PASS；隐式latest或其它schema回退。
- Verification：后续先RED旧/新有限分派及真实本地历史fixture，再GREEN与原消费者回归；验收必须绑定实际Spug/控制代次原件，纯合同测试不替代实际页面/备份链验证。
- Forbidden action：本阶段不实现/跑测试/服务器；不修改installation_selection、旧五reader/历史custody，不改五attempt原件，不伪造MainProgramSpugInstallation。
- Evidence：下文列只读文件与精确pin闭包核查结果；所有输出仅结构、path/bytes/SHA，无凭据。

## 待只读核对的正式合同

以下合同已按当前实际源码与五attempt原件只读核对；不是已完成实现或真实新r7验收结论。

## 建议的唯一新入口

新增 TASK `main_program_current_installation.py`，不修改 `main_program_installation_selection.py`。正式函数：

`load_current_installation(task, private, *, selection_file) -> dict`

只读本地、无callback/transport参数，固定返回：`selectionPin, selection, generation, inputPins, spugRuntime`。其中 `spugRuntime` 私有内存视图含 `kind, resourceBuildPin, resourceBuild, guardStagePin, guard, publishedConfigurationPins`；kind只允许 `PUBLICATION_VERIFICATION` 或 `CONTROL_GENERATION_ACCEPTANCE`。不需要为当前消费者增加新的selector schema或再造安装回执。

1. 固定 `Records(task)` 读取显式 selection_file，精确校验 v4 原五字段：schemaVersion/sourceCommit/controlGenerationPin/spugInstallationPin/verificationInputsPin；不猜当前文件、不找latest。
2. 读取并验证 verificationInputsPin 的原字节；按精确schema有限分派：旧 `MainProgramSpugPublicationVerificationInputs/v1`、`.../v2` 调原 `validate_publication_v4(records,private,selection)`，原成功/失败合同原样保持；新 `MainProgramSpugControlGenerationAcceptanceInputs/v1` 调正式 `load_completed_acceptance(task,private,selection['spugInstallationPin'])`。未知schema直接拒绝，绝不try旧失败后fallback新。
3. 新分支额外核 acceptance core 的 acceptanceInputsPin 精确等于selector.verificationInputsPin，controlGenerationPin/sourceCommit等于selector，inputs.outputFile精确等于spugInstallationPin.file；返回generation的generationPin/commit也必须相等。新 spugInstallationPin 如实指 schema `MainProgramSpugControlGenerationAcceptance/v1` 的实际result，不允许伪称旧 `MainProgramSpugInstallation/v1`。
4. 完整 `inputPins` 合并正式loader返回闭包、selector自身及dispatcher/helper身份，按物理路径冲突拒绝，返回前逐原pin重验。后续消费者新增读取必须先证明完整pin属于该闭包，再读字节验证；不能凭路径已在PRIVATE/TASK就读取未绑定文件。
5. 新入口只支持这些消费者原要求的v4，不接管历史v1/v2/v3 selection路由；旧installation_selection保持原所有入口与失败行为。无需往历史custody添加新映射。

## 565 资源、guard-after 与七配置的精确来源

### 新验收分支

- 新core.acceptanceInputsPin → 新inputs.historicalReadCustodyPin → 已验 `MainProgramSpugHistoricalReadCustody/v1` 的 `resourceTransitionReferencePin` → `MainProgramSpugResourceTransitionReaderCustody/v1.transitionCorePin` → transition core的 `transitionInputsPin` → inputs的 **resourceBuildPin**。这是565实际资源build，不能拿candidateResourceBuildPin、r7控制build或旧c772 build替代。
- 实际历史链目前为 `main-program-spug-resource-transition-reader-custody-5651efc-r1.json` → `main-program-spug-resource-transition-5651efc-r1.json` → `main-program-spug-resource-transition-inputs-5651efc-r1.json` → `spug-resource-build-5651efc-r3.json`，后者7153B/SHA `a30b1d8f3472be5e740994ad71b4eb95f2be0743defe450d82427a7bb58008a5`。实施仍按上述pin链读取，不硬编码名称作为授权。
- 新core.privateEvidencePin → rich.stages 中唯一最后一项 `spug-guard-after` → stage.resultPin → stage.result。不得猜“与core同stem的private.json”；新schema已明确给privateEvidencePin。正式loader已经核stage schema/recordType、native原exit/完整stdout、程序/请求关联和validationError=None。消费者使用**本次新验收**guard，不能借旧v3 guard自述新运行态。
- guard的14个filePins、7个configurationPins和entryIdentity/entryEnvironmentSha256才是当前Spug实际观察证明。UI预检继续用原SPUG_SCRIPT逐实际文件SHA及PID/startTicks/argv/exe/cwd/env核验；新helper不能把这种实时核验替换为离线PASS。
- 七配置真实内容仍是历史已发布的三个settings和四旧连接：historical custody.verificationInputsPin → v2.baseVerificationInputsPin → v1.continuationInputsPin → c1.controlGenerationPin → 旧generation.planPin → 旧plan.privatePlanPin。该旧私有plan的entrySettings/simpleSettings/bridgeSettings及newConnections四项（在该历史语境中即已发布四旧名）是已核原值；路径使用原publication.SETTINGS与四旧连接文件名。只在内存按canonical字节求pin，与guard的7个configurationPins逐对象相等；真实值不写stdout或公共结果。
- 新acceptance已通过 `configuration_equivalence` 和完整历史prepare证明r7四个拟新名payload与四旧文件逐对象同值，三个settings/27历史登记严格一致；消费者不再复制该整套投影或改用r7新文件名。现在的三个消费者实际上只需build/guard/pins，不需输出配置内容。

### 原验收分支

沿用原 `validate_publication_v4` 完整校验，再按原rich的resourceTransitionPin和原stage取值；无resource transition的旧v1按其正式原resourceBuild输入关系解析，不能猜565。现有这三个消费者的主目标原为v2/565，新增helper至少不得把旧v2逻辑改成新schema或吞掉旧失败。原底层validator的既有历史scope限制保留。

## 最小消费者影响

| 文件 | 必要变化 | 保持 |
| --- | --- | --- |
| prepare_main_program_ui_preflight.py | 以新load_current_installation替换直接validate_publication_v4；spug_observation使用spugRuntime.guard/resourceBuild，不再按新result猜旧rich结构 | 真实Docker只读runtime核验、source原服务/健康/epoch/锁/容量与计划、UI阶段/operation绑定、原输出字段 |
| verify_automatic_backup_chain.py | `_prepare_main`通过新入口取generation/fullinputPins/resourceBuild；删其对新result假设旧rich.resourceTransitionPin的解析 | 真实原生点/父链/manifest/readback/epoch/source restoration核验与147包、sourceCommit/spugCommit分别绑定；新result pin原样传入deployment |
| verify_goal_readonly.cjs | point-audit指定selection时调用新dispatcher的固定本机CLI安全摘要，替换只能认MainProgramSpugInstallation/v1与verification/v2的硬编码块 | 同point/完整chain/baseline/147包/资源commit绑定、真实Playwright只读用户路径、禁止最终执行按钮 |

建议dispatcher自带固定 `--selection <TASK文件名> --public-summary`（只读）模式供CJS以固定Python绝对路径、参数数组、无shell调用。摘要仅返回schema/status、selectorPin/sourceCommit/controlGenerationPin/spugInstallationPin、主build147身份、565resourceBuildPin/spugCommit及完整本地inputPins，不包含generation私有owner/settings或凭据。CJS必须把摘要inputPins纳入现有输入重验（单独严格path pin读取，限制为该固定helper返回集合），读前后身份和bytes/SHA保持；不能只信subprocess stdout中的PASS或省略既有point审计绑定。旧不带point-audit模式保持无需新入口。若实现阶段选择独占公共projection文件而非stdout，文件必须由同一loader产生并绑定selector/完整闭包，不能仅传自述摘要；本设计推荐固定CLI避免新增持久证据类型。

## 五attempt的只读修改范围证明

读取 PRIVATE `main-program-spug-historical-read-custody-20261110-r1.private.json`，12119B/SHA `779c3eae7d706abd5f91bdb4f679a1edde268cbc5f9f9d969e6fe7db259702da`，逐核其五个attempt实际字节与pin后，扫描全部inputPins，并递归扫描完整attempt所有path/bytes/SHA对象。只做原件读取，没有调用历史验证器或测试。

| attempt label / 文件 | bytes | SHA256 | inputPins数 | 拟改三个消费者/新dispatcher命中 |
| --- | ---: | --- | ---: | --- |
| publication / main-program-spug-installation-45dd7dc-r6.attempt.private.json | 73005 | `50a42921f08ef427c6983391fd90e55bb714267dcc5c12b5a222415b2cfb9360` | 286 | 0 |
| continuation / main-program-spug-installation-45dd7dc-r6-continuation-c1.attempt.private.json | 89473 | `8593e4510f0c4206e3260894f6c1523b59c6226bf0ed1da4195f096e461dd296` | 350 | 0 |
| dependency / main-program-spug-runtime-dependency-activation-c7728ad-r1.attempt.private.json | 184844 | `5670c6c4eb6b37b71805a7787f2c76336f66cdc54b6e821e95f784b720066afc` | 719 | 0 |
| resourceTransition / main-program-spug-resource-transition-5651efc-r1.attempt.private.json | 288419 | `ab8a478b09de9eed3269823d88aa395ca0c7a3c4d875f95236a8e43a06499673` | 1141 | 0 |
| verification / main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v3.attempt.private.json | 275829 | `41b3cd85685a4d6c6a4981dd069d30a34162e8bef26a437a4be51baa3d93d2b1` | 1079 | 0 |

`main_program_installation_selection.py` 同名pin分别命中1/2/2/2/2（包含历史release副本），所以不得修改。历史custody.currentReaderPins精确为 continuation、runtime_dependency_completion、verify_only、resource_transition、historical_custody 五文件，拟改三消费者/新dispatcher均不在其中。只读查过的既有 `test_main_program_ui_preflight.py` 也不在五attempt；其余建议新增专属测试，不改旧五reader测试。

当前消费者冻结身份供后续实现前复核：

| 文件 | bytes | SHA256 |
| --- | ---: | --- |
| prepare_main_program_ui_preflight.py | 16295 | `dbaf24f88aaea7a4d50cedb789740146d8df1cbbc85047fb874dffd8fcdb3c87` |
| verify_automatic_backup_chain.py | 18872 | `d1273dad3f1e93b7512c933c7ca0491a98e9063efb9f9055f90c971a7281e5fd` |
| verify_goal_readonly.cjs | 25162 | `dee4cdfe0b45c277aba72ceaedf4036d7b525856d0d68e037c57c322304562fc` |

## BDD 与后续 TDD（尚未执行）

1. Given旧v4+verification/v2真实原件，When dispatcher，Then调用原validator保持相同失败/成功与generation/闭包，不修改旧输入或映射；未知schema不得回退。
2. Given新v4指真实completed acceptance，When dispatcher，Then新正式loader完整通过且acceptanceInputs/generation/sourceCommit/output全部交叉绑定；仅STAGED/缺stage/native/错result pin拒绝。
3. Given旧565build+七配置四旧文件保持而r7四拟新名未发布，When新UI预检，Then使用565实际14资源、新guard-after实际进程/7配置及r7source控制；不能要求新连接文件存在，也不能把Spug commit写成r7commit。
4. Given伪造acceptance core为旧schema、verificationInputs/result不配对、历史transition/build错pin、guard借旧轮或不在inputPins，Then在任何远端/UI调用前拒绝。
5. Given同点提交与FULL/I1/I2链，Whenchain audit，Then原有全部147/读回/epoch/源恢复门禁保持，deployment.spugInstallationPin精确为新acceptance结果；仅替换安装证明来源不减少数据证明。
6. GivenCJS指定point-audit，When固定CLI返回失败/非JSON/未知schema/错selector/漂移inputPins，Then浏览器创建前拒绝；成功只返回安全摘要，禁止私有配置值进入输出。
7. Given实施后的拟改文件，When完整五attempt pin审计+原历史reader本机回归，Then旧文件SHA及原成功/失败原件保持；新测试不能伪造新r7实际完成来宣称现场验收。

后续建议新 `test_main_program_current_installation.py` 和专属消费者接缝测试先RED；旧source/目标UI运行门禁、原chain审计fixture、CJS point-scope合同回归保持。真实r7 acceptance尚由父实际执行，正向现场材料未齐不得用mock安装成功替代。此设计只提供读取方案；无生产/测试代码变更、无测试/服务器/浏览器/提交执行。
