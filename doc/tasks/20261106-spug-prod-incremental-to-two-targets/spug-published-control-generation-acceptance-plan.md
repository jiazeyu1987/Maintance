# 已发布 Spug 配置的控制代次验收

## Current Status

ready_for_closeout（仅第一阶段）。父已批准的单一载体及四个reader显式接线实现已冻结；最终31个新场景PASS/0skip，包含完整真实历史读取。旧无参数回归仍有2 FAIL/70 setup ERROR，全部精确拒绝原源码漂移，原失败保留，不称全回归PASS。父独立保存的原源码只读消费，本分工未提取Git旧源码或访问服务器；待父独立复核及提交。第二阶段和产品全目标尚未完成。

## 目标、里程碑与验证

1. 闭合当前 `main-program-current-installations-45dd7dc-r6-v4.json` 的完整历史读取：原publication失败、c1成功写入前缀、依赖补齐、565资源transition及原verification-v3完成验收全部仍验证。
2. 先真实临时原件RED，再有限typed custody与显式参数接线GREEN、旧合同REGRESSION。原失败、原输入、原attempt/inputPins、原核心和现有custody均不修改。
3. 第一阶段父审、独立验证并冻结后，第二阶段另做明确的只读代次验收入口：严格证明r7计划四个新名连接的payload与已发布四旧连接逐对象相等，再核新四控制、12 selector、565全部14资源和七配置。不得声称发布了r7新连接文件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。无显式custody继续原路径，缺字节或错关联即失败；不自动发现sidecar。
- 是否从根因和长期维护角度解决：是。将历史逻辑输入的不可变身份与当前读取程序的身份分别核验，避免要求开发源码永远停留在历史字节。
- 是否存在临时补丁或绕过：否。不覆盖源码，不执行保留的旧源码，不把当前观察替代过去的完成证明。

## 经验门禁

- Trigger：已完成Spug配置写入后的历史验收，因读取程序合法更新而出现 `MAIN_SPUG_ORIGINAL_BYTES_CHANGED`。
- Preflight check：核当前v4 selector、原完整v3验收、565 transition reader wrapper及其五份明确attempt的真实pins；确认全部旧inputPins和已有custody保持。只新增已证实activation旧字节的精确保留关系；本轮修改reader造成的自身保留需求单列并需父审。
- Blocker：未知输入漂移、缺保留原字节、原attempt不包含该pin、跨attempt混用、覆盖已有映射、额外源码范围、原生阶段或退出/输出不闭合。
- Verification：本机真实私有临时文件、当前真实历史只读消费、逐节点负例、旧合同回归及原件前后SHA/身份保持；测试不派发远程调用。
- Forbidden action：不重复七配置写入，不重放失败，不改旧报告或用Git模板覆盖私密资料；不允许全局monkeypatch、动态任意源码加载、隐式映射或吞异常。
- Evidence：`docs/release-agent-checklist.md` 的“Spug运行资源依赖闭包门禁”和“多机器发布接管与缺失记录分析门禁”；前序宽回归原件 `source-policy-activation-regression-r1.log/json`；本计划及后续专属TDD记录。

## 已证实根因与原件范围

原activation逻辑输入为107657字节、SHA256 `963bbe907d1d2f7334ee9fa5d8598a5659361ca512d23514d92d9721b91146bb`，路径为本TASK的 `main_program_control_activation.py`。Git `3e5113225d6c09a8ade5a0b6321d55fbee8d6122` 的该原始blob逐字节相同；父已独立保存到PRIVATE/spug-historical-read-originals-20261110-r1，原manifest及五份源码字节本轮只读。

同一个pin出现在以下五份attempt，不能只修第一个读取点：

| 阶段 | 原attempt文件（PRIVATE） | 精确读取入口 |
| --- | --- | --- |
| 原publication | main-program-spug-installation-45dd7dc-r6.attempt.private.json | continuation.load_failed_originals / validate_source_custody |
| c1 | main-program-spug-installation-45dd7dc-r6-continuation-c1.attempt.private.json | dependency.validate_failed_continuation |
| 依赖补齐 | main-program-spug-runtime-dependency-activation-c7728ad-r1.attempt.private.json | verify_only.load_completed_dependency_activation |
| 565 transition | main-program-spug-resource-transition-5651efc-r1.attempt.private.json | resource_transition.load_completed_transition |
| 完整v3验收 | main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v3.attempt.private.json | verify_only.validate_publication_v4 |

当前已有source-custody与reader-custody继续独立验证。新增上下文不替换它们，也不能因已有映射失败而采用第二条路径。当前完成selector仍绑定原45代次；本阶段不能把它改成r7。

## 单一有限typed载体（父已批准）

新增 `MainProgramSpugHistoricalReadCustody/v1`，只作为第一阶段显式读参数，不新建selector/旧验收输入版本。固定字段：

- `schemaVersion`。
- `selectionPin`：当前v4 selector；其原 `controlGenerationPin`、`verificationInputsPin`、`spugInstallationPin` 必须完整闭合。
- `verificationInputsPin`、`verificationCorePin`：与该selector原字段完全相同。
- `resourceTransitionReferencePin`：原v3验收输入绑定的565 reader-custody wrapper，继续核其原transition core/attempt/旧reader保留关系。
- `attemptPins`：对象，精确五个键 `publication`、`continuation`、`dependency`、`resourceTransition`、`verification`。每个pin必须由上方不可变原件关系独立导出并全等，不接受调用者新增attempt或挑选五个无关记录。
- `activationSource`：精确 `{originalPin,preservedPin}`。originalPin仅接受上述原路径/107657/963bbe；preservedPin为PRIVATE内独立普通文件、非别名/硬链，完整字节/SHA相同，且每份已绑定attempt恰含这个原pin一次。
- `readerCustodies`：仅处理本次参数接线实际改变的四个reader，条目为 `{attempt,originalPin,preservedPin,currentPin}`。路径范围固定为下表四模块；originalPin必须确实出现在该明确attempt，preservedPin逐字节证明旧输入，currentPin固定现在实际读取模块。映射键为具体attempt和完整originalPin，不按路径覆盖。已有旧reader保留原件可引用，不复写；冲突或多余条目拒绝。父已明确批准该范围。
- `currentReaderPins`：新helper及实际四个reader的完整当前pin；与实际导入的 `__file__`/字节相同，完整核验结束再复核。不得把这个当前pin当作旧attempt的原输入。

历史逻辑inputPins和本次实际读取physicalPins必须分开：前者仍按原attempt逐对象比较；后者包含custody载体、保留原件及当前reader。不得给旧attempt重算一组“新inputPins”。新物理保留pins不混入旧expected-input集合导致伪差异。

### 当前reader自身变更的必要审查点

增加显式参数会改变continuation、verify_only、dependency、resource_transition自身字节；原五attempt也钉住了这些reader中的部分历史版本。仅在别处登记currentReaderPin无法证明旧inputPin。已有custody覆盖其中一部分，未覆盖本次新变化。

因此额外的业务源码映射仍严格只有activation；四个固定reader的真实旧输入需要独立reader-custody，形式复用现有 `originalReaderPin / preservedReaderPin / currentReaderPin` 语义，合并在上述一个有限载体中，不再逐个叠加新schema。只允许保留确实在原attempt中的原reader字节；不执行它们。若父限定连这些reader原字节都不能保留，则现有参数接线无法同时保持旧inputPins完整核验，本里程碑必须阻塞，不能忽略reader漂移。

## 最少文件与函数接线

新增 `main_program_spug_historical_custody.py`：唯一typed校验和局部上下文；入口 `load_historical_publication(task, private, custody_pin)` 读取载体后，调用原 `validate_publication_v4`，返回其原 `{generation,inputPins}` 形状。helper不提供远程/写入/旧源码执行接口。

内部上下文仅在本次调用栈持有：按明确attempt名核原输入、与该attempt已有映射互斥合并、核原expected集合及返回本次physicalPins。无需全局注册、修改模块变量或替换Records返回文档。

| 现有模块 | 最小改动（显式keyword-only `historical=None`） |
| --- | --- |
| main_program_spug_publication_continuation.py | prepare_value → load_failed_originals → validate_source_custody 传同一上下文；只有 `publication` attempt核原输入时消费附加保留事实。无参数保持原允许范围和失败路径。 |
| spug_runtime_dependency_completion.py | validate_failed_continuation 在现有一项selection source custody验证完成后，核 `continuation` attempt的附加保留事实；已有映射仍按旧合同。 |
| main_program_spug_publication_verify_only.py | validate_publication_v4 → prepare_value（包括v2递归）→ continuation/dependency/transition显式传递；load_completed_dependency_activation 核 `dependency`，最终完整验收核 `verification`。不得改变原stage_program、真实dispatch/输出/退出比较。 |
| main_program_spug_resource_transition.py | _prepare / load_completed_transition 传同一上下文；仍由现有transition_reference核旧reader wrapper。在 `resourceTransition` 原expected-input集合核验处应用精确历史身份，保留现有逐项事件/native/前后状态检查。 |

第一阶段不改publication.py、installation_selection.py、现有v4 selector或任何旧输入/原件；调用新helper为显式有限入口。第二阶段验收可消费这个入口返回的完整闭合结果，但本轮不写其实现。

## BDD与严格TDD范围

1. Given 当前五attempt均引用同一真实activation原pin，When 仅提供当前helper源码，Then 保持原 `ORIGINAL_BYTES_CHANGED`；提供明确载体与真实独立原字节后，原完整v3验收可闭合，原全部逻辑输入不改。
2. Given wrong selector/core/transition/任一attempt关联、少一个/多一个attempt、重复映射、wrong SHA/bytes/路径/越界/别名/硬链或不在原attempt的源码，When load，Then 在原阶段消费前失败。
3. Given 其它未知源码或任一业务原件漂移，When 读取，Then 不得被activation特例覆盖。已有source/reader custody缺失或冲突也必须失败。
4. Given 本次reader更新，When old原字节未保留或currentReaderPin不匹配实际导入，Then 失败；正确保留时仍逐字核原program、request、native stdout/stderr、exit及真实终态，不以mock成功替代。
5. Given 未传historical，When 旧输入调用原reader，Then 原schema/允许范围/结果与失败不变；新helper不得被普通apply/observe入口隐式使用。
6. Given 显式历史调用开始与结束，Then 全部原文件stat/bytes/SHA保持，没有transport、Git源码提取、目录扫描发现、新备份恢复或配置写入。

测试新增 `test_main_program_spug_historical_custody.py`，本机临时私有文件覆盖路径/身份负例；原完整真实证明只读集成用实际报告，不伪造远程成功。设计批准后先记录真实RED，再实现，最后回归 continuation / verify_only / dependency / resource_transition / installation_selection 相关用例。原有2 FAIL/26前置错误不删除，须由明确新入口证明闭合；旧无参数路径继续报告缺custody。

## 第一阶段停止点

实现及必要回归完成后冻结源SHA交父审，不提交、不远端、不生成正式新验收原件。本地真实历史读取的完成不代表r7运行态或Spug产品验收完成；父当前inactive staging与本地历史读取互不冒充成功。

## 第二阶段最小设计（仅提案，未实施）

新增有限入口 `main_program_spug_control_generation_acceptance.py` 与专属测试。prepare显式接受本阶段custody pin、r7正式generation pin、新鲜Spug/三host观察pin及输出名；先调用本阶段完整历史reader，再调用唯一generation loader。只有四份新控制实际完成的generation可用，FILES_STAGED或STAGED_NOT_ACTIVATED不能替代。

准备阶段纯函数逐对象证明：原v3/565证明中的七配置和四旧连接文件仍是当前实际值；r7 privatePlan.newConnections的四个新名payload分别按同一source/target连接角色对应原已发布四旧文件，完整JSON对象相等，不能只比URL或忽略header/认证字段；同一个原文件不得映射多个不同payload。simple/bridge里的真实connection引用继续指向旧名。27项历史登记逐项保持。新计划的连接文件不存在也不产生写入；如果任一payload不同则本路线BLOCKED，必须另走明确发布需求。

执行与聚合仅复用已验证的只读操作：Spug guard-before → 三host verify → Spug verify → guard-after。新host spec精确绑定r7四控制的已安装owner/control/program/receipt及12个selector；Spug spec保留565全部14资源、七配置、旧四连接名和原历史指纹。固定原生request/program/argv/stdout/exit逐项留存；不复用旧aggregate里的publicationCompleted语义，新结论只能是“已发布配置对新控制代次的验收通过”，configurationWrites/backupDispatched/restoreDispatched均为false，并明确control查询可能追加自身审计。

载体只增加该有限验收的inputs/result一对，不改旧verification-v1/v2/v3或五attempt。若需让当前v4 selector指向新验收，应在现有selector reader按明确新receipt discriminator作一个有限分派：分别验证原Spug已发布证明与新generation验收，不把旧45的spugInstallationPin重新解释为r7成功；旧分支逐值不动。该分派与正式schema字段需父审后先BDD/RED，不在第一阶段顺带实现。

BDD范围：完整payload同值而名字不同可验收且无文件写入；任一认证/URL/引用/旧文件pin或565资源变动拒绝；r7未激活/少一个控制/selector关联错拒绝；真实原生非零退出/未知/缺阶段/错程序拒绝；前后配置和业务容器/NAS/旧历史漂移拒绝；原历史仍须本阶段完整读取，不用新鲜观察补造过去成功。只读验收PASS不替代用户前端真实增量备份/恢复验证和最终工作区收尾。
