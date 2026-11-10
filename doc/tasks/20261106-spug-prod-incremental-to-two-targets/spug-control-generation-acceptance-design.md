# 已发布配置对 r7 控制代次的只读验收

## Current Status

READY_FOR_ACTUAL_GENERATION。本机限定实现与合同测试已冻结：38新+31历史69项通过，父审录证修正另4个受影响真实子进程场景通过；详见专属TDD日志。第一阶段已由父提交b88bfb4且本阶段未修改。未派发远程验收；当前r7必须由唯一generation loader证明已完成安装，暂存不能代替，实际prepare正向集成待父原件。

## 目标、里程碑与预期验证

1. 新有限 helper `main_program_spug_control_generation_acceptance.py` 和专属测试；不改产品、不改五个历史 reader。
2. 默认 prepare 只读本机原件。严格闭合旧完整历史、r7 正式代次、新鲜观察，以及已发布配置与新计划之间的精确等值关系。
3. 复用既有六阶段只读程序、真实 argv 和 native 记录协议。execute 只有父明确调用才派发；本分工仅本机测试。
4. 新结果只能声明已发布配置对新控制代次通过验收，不声明新连接文件已发布。selector 分派另报父审，不在本阶段改旧入口。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。缺已完成 r7 generation、缺观察或原件不一致即拒绝。
- 是否从根因和长期维护角度解决：是。分离已发布配置的历史身份、当前控制代次和本次只读验收，不重复发布。
- 是否存在临时补丁或绕过：否。无旧代码覆盖、隐式 latest、全局 mapping 或改旧报告。

## 经验门禁

- Trigger：七配置已完成发布，控制执行器升级，但配置 payload 与连接地址不变。
- Preflight check：第一阶段正式 custody 与五 attempt 完整验证；唯一 generation loader 的四控制完成证据；565 全部14资源、七配置、四旧连接及27历史登记；新鲜观察的实际实例/进程/配置归属。
- Blocker：暂存代次、任一 payload/认证字段/引用/原件漂移、缺三服实际观察、缺 native 原退出或程序/输出关系、少一个阶段。
- Verification：真实私有文件负例；纯等值投影测试；默认 prepare 不构造 transport；有限本机子进程证明失败/未知保留；父后续实际六阶段验收。
- Forbidden action：不调用 publication writer、不重写四旧连接或三个 settings、不伪称四新名文件存在、不复制原旧成功为新成功、不访问远端或提交。
- Evidence：`docs/release-agent-checklist.md` 的“Spug 运行资源依赖闭包门禁”“多机器发布接管与缺失记录分析门禁”；父第一阶段 `spug-historical-custody-parent-20261110-r1.json` 与 `spug-historical-read-parent-20261110-r1.json`。

## 最小输入与函数合同

仅新增一对 inputs/result 合同，不增加 selector 版本或覆盖旧 verification：

`MainProgramSpugControlGenerationAcceptanceInputs/v1` 精确字段：
`schemaVersion, historicalReadCustodyPin, controlGenerationPin, observationPin, verificationId, outputFile`。

- historicalReadCustodyPin 为本机 PRIVATE 完整 path/bytes/SHA；必须绑定第一阶段所核原 v4 selector、完整 v3/565 与五 attempt。
- controlGenerationPin 为 TASK file/bytes/SHA；新代次须明确以前述旧 generation 为 predecessor，plan revision 为 r7，所有四控制已完成，不能用当前时钟或“最新”推断。
- observationPin 沿用已存在 `MainProgramSpugPublicationObservation/v2` 的私密载体，绑定本次 sourceCommit/revision/controlGeneration 和原565实际资源构建；不造新观察 schema。三 host 原件及 Spug 实际身份必须完整。
- verificationId 仅用于独占新 attempt/output 名；outputFile 精确按新提交/revision/id导出，拒复用旧验收文件。

正式 API：

- `prepare(task, private, inputs_file)`：只读文件，不创建 transport、不写配置；返回已核完整 prepared。
- `project_published_configuration(base, candidate, observation)`：纯函数，显式输入已经读取的协议对象；返回六阶段所需 detached specs，不生成成功 receipt。只有 prepare 完成所有实际 loader 后才能执行。
- `stage_program(prepared, stage)` / `command_arguments(prepared, stage)`：固定六阶段白名单；仅 verify，不接受 preflight/publish/reload。
- `execute_acceptance(task, private, prepared, *, transport)`：显式只读 transport；O_EXCL固定新 attempt、stage、native与result原件，失败保留实际阶段/未知结果，不重试。
- `load_completed_acceptance(task, private, result_pin)`：只读全部输入和每个stage/native原件，复算等值投影，返回 `{generation,inputPins}`；不会查询当前服务器。

默认CLI只prepare；远程execute须显式参数和父已有授权，模块导入无IO。不会复用旧 `aggregate` 的 `publicationCompleted=True`。

## loader 接线和精确投影

1. `historical.load_context` + 原 `verify_only.validate_publication_v4(..., historical=context)` 完整读取，最后 `context.finish()`；原结果保持。
2. 在同一明确上下文调用原 `verify_only.prepare_value` 得已核 c1/565 spec。不得用 current 控制替换它再声称原历史通过。
3. `generation.load_control_generation` 读取新代次；绑定 predecessor、计划与实际四个安装 core/rich、package、owner/control、PID/dropin/receipt。全部 current input pins 在 prepare 结束复核。
4. 新 plan 的四 `newConnections` 按 source/target 角色和桥接引用，分别与原 c1 四已写连接完整 JSON 对象全等；不按同名猜，不忽略认证字段。三个 settings 的有效语义与旧已发布值相同，桥接新名只作受控角色映射比较，实际引用保持旧名；原27登记及12 selector value/registrationPin必须逐对象相同。
5. host spec 从原已核 spec 拷贝，仅替换新控制完整身份、sourceCommit及本次新鲜业务/NAS基线。保留原 selector `expected` 与原 auditPath/backup 关系；新鲜 selector 当前pin单独核为既有已发布value，不能把当前pin误当最初发布前pin。
6. Spug spec 保留原七 writes、settings、四旧连接及原auditPath；仅核并投影本次实际进程/容器观察。runtime guard继续核565全部14资源。新四连接名不进入 writes，不要求存在，不称已发布。原27历史路由指纹不变。

本机真实只读比较已证：r7四连接与四旧连接一一完整同值；entry/simple全对象相同，bridge仅四连接名角色映射后全对象相同；retainedDocumentsByHost每服9项共27项与r6全对象相同，registrations/sourceRegistrationSelectors/originalMetadata/originalSpug均相同。r7完成generation文件尚不存在，因此尚不能作实际prepare成功声明。

实现只向旧 `verify_only.stage_program/command_arguments/validate_stage_result/validate_stage_native` 传一个detached programView；不改这些函数。view内部保留原continuationFailurePin等真实命令关联材料，外部新输入/结果单独绑定本次generation。view中的 `verificationContext.generation` 为已核新bundle，565 resource仍原14项，不能把旧core原件改写成新context。

原六stage代码未调用incremental_plan或/incremental-plan。它们验证Native.selections及bridge.selections，故不要求旧I2 READY；来源允许状态转换由已完成r7 generation中的正式activation sourcePolicy proof校验，不在此入口另设宽泛baseline准入。

阶段严格为：spug-guard-before、host-verify-57、host-verify-58、host-verify-59、spug-verify、spug-guard-after。host/spug verify复用 `continuation.original.program(...,'verify',...)` 的原函数；两guard复用 `dependency.runtime_program`。实际 native 关联继续用固定argv/stdin程序/完整stdout/exit/timeout原件判断。只读控制查询可能追加查询审计，要如实记录 `controlApiQueriesPerformed=True/queryAuditWritesMayOccur=True`。

## selector 入口影响（仅评估，暂不改）

当前 `main_program_installation_selection.select_main_program_installation` 的 v4 分支无条件调用旧 `verify_only.validate_publication_v4`；后者绑定原45 sourceCommit/原generation，不能直接消费新验收。

若父后续允许统一选择：仍用 v4 selector 的原五字段形状，先按 `verificationInputsPin` 的确切 schema 做一个有限分派，新的 acceptance reader 返回原 `{generation,inputPins}` 形状。旧验证分支及原 selector 不改；新 selector 为独立文件，spugInstallationPin指向新只读验收结果并在结果内明确引用原已发布核心。不得把原旧core重解释为r7。

该改动会改变 installation_selection.py 当前物理pin；旧五attempt中它的历史版本已有严格原source custody，但当前第一阶段正式载体/reader并未授权新的隐式映射。实施前须逐个列出受影响历史读取所核的当前pin/原pin，父审通过后再做限定RED，不能在本阶段顺带修改以导致第一阶段新正式原件漂移。

## BDD / TDD

- Given 原完整历史与已完成r7，且所有连接payload/历史登记相同，When prepare，Then 零transport、精确六阶段、四旧文件保持、newConnectionFilesPublished=False。
- Given 新代次仅STAGED、predecessor错误、少一个控制或新观察错代，Then prepare拒绝，不构造transport。
- Given 名称不同但payload相同，Then 只认可精确角色映射；多对一、任意认证/URL字段、settings引用或27登记变更均拒绝。
- Given 相同已发布selector，Then 保留原expected/audit备份关系；不得用新观察的当前pin替代原发布前pin。
- Given 真实本机子进程非零退出、无JSON、timeout、阶段丢失或request/program/stdout错关联，Then 不生成PASS，保留原失败与未知，禁止自动重试。
- Given 原生六stage完成，Then reader重读全部原件并验证565十四资源/七配置/12selector；结果仅控制代次验收，配置写入/备份/恢复均false。

先纯合同与缺失实现RED；本机协议测试不得制造已完成r7安装。若真实r7尚未完成，实际prepare正向集成明确等待父原件，不能用构造的成功安装替代。原参数历史测试保持第一阶段已报告的严格漂移拒绝，不重写期望。
