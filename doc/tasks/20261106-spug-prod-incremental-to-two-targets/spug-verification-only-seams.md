# c1 只验收：阶段 B 的最小接缝

## Current Status

design_for_review。父授权本轮仅只读调查及本文件；没有修改阶段A三文件、产品、旧350项输入、reader、测试或现场记录，没有Docker、服务器、浏览器、构建或提交操作。本文承接 `spug-runtime-dependency-completion-design.md` 的阶段B；阶段A已经实际成功，B实现仍须父明确批准边界。

目标仍为控制提交45dd7dc/r6、原c1及资源提交c7728ad；不创建c2/r7，不重发原七配置或三服selectors。最终独立验收成功也不把原r6/c1失败改为成功。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。历史原输入必须有逐字节证据；只有明确映射的旧源码允许从正式托管读取。
- 是否从根因和长期维护角度解决：是。将历史执行证据与当前验收执行输入分开，保持同一套深校验；避免复制旧验证器、动态执行历史代码或全局猴补。
- 是否存在临时补丁或绕过：否。复用原HOST/SPUG验证正文，独立完成只验收；没有配置重新发布入口。

## 经验门禁

- Trigger：c1已完成全部写入，最终配置解析失败；补齐依赖后应只验收。
- Preflight check：两次原FAILED、c1七APPLIED/三HOST PASS/原native失败、阶段A实际单文件安装及新entry、严格源码托管与全部当前不变输入。
- Blocker：缺任一原生阶段、旧输入漂移无明确托管、未知原调用仍可能进行、需要重写配置或改变原控制代次、没有真实A成功。
- Verification：实际原件纯准备、源码变更前RED、托管后的历史读取GREEN、原生成验证程序及新原生回执逐项深绑定、旧分支回归；现场由父执行。
- Forbidden action：不删除/覆盖原claim、gate、FAILED、attempt；不把副本改成PASS；不新增宽泛ignore、latest扫描、任意pin替代或跳过349项；不以本机fixture宣称现场成功。
- Evidence：阶段A实际core/rich、原c1原件、A16源码托管、本文定位的函数与后续独立TDD记录。沿用已批准父计划及实际执行前experience-preflight门禁。

## 已发生的事实

父唯一A安装原session32386已exit0/48.922秒。本文只读了其实际core和rich，没有重跑：

- `main-program-spug-runtime-dependency-activation-c7728ad-r1.json`：8391B，SHA `e71d33ce1e1e7c0610a6f033208175542fbe4cbfbfda6fcdd8de8e5f2ed3de8f`。
- PRIVATE同stem `.private.json`：13951B，SHA `7ee0eafea0e1cafbb8a14c800181757451dbf61dc07f6c2d9b1b0dc5fa237a0c`。
- entry真实转移151768/119726793 → 151963/120521202；完整argv/cwd/executable/parent/supervisor及环境摘要保持。唯一simple APPLIED；14文件、七配置、历史路由及两个实例保持。
- A报告仍为`liveUiVerified=false`，返回`publicationCompleted=false`；资源安装不能代替发布最终验证。
- A原attempt有719个`inputPins`；七个阶段为before、before-write、replacement-dispatched、installed、replacement-applied、reload、after；15个原生回执对应五次guard/reload调用及其前后inspect。
- 原c1 attempt仍350项，c1末项原生stdout仍FAILED/SIMPLE_CONFIGURATION_INVALID；七配置及三HOST成功历史保持。
- 实际A依赖completion为4053B/SHA `b057c6c4d3c145a1d5de25bb5bd544b25a13c8eab6173a5e3ffb8a4b6719e55f`；其`sourceCustodyPin`指向PRIVATE `spug-runtime-dependency-source-custody-c7728ad-r1.private.json`，8354B/SHA `a1e12c49c755372dbecdcadfe581f5085ce50590e68c789c712d19022ad63475`。

## 精确接缝与建议允许修改集合

|文件/函数|当前行为|B最小修改|
|---|---|---|
|新增 `main_program_spug_publication_verify_only.py`|尚不存在|严格输入、只验收执行、历史A证据reader和v4成功reader；没有发布/安装方法|
|`main_program_installation_selection.py:select_main_program_installation`|仅v1/v2/v3|增加显式v4分派；返回已有控制选择形状，使用已深核同一generation；旧分支不变|
|`observe_closeout_hosts.py:controller_selection`|仅v1/v2/v3|增加v4调用同一selector；不放宽未知schema，不改变采集命令|
|`spug_runtime_dependency_completion.py:validate_failed_continuation`|第173行对c1全部350原pin直接`publication.verify_bytes`|仅增加严格可选`historical_source_custody`参数及这一输入循环的源码托管验证；默认None完全保持A准入行为，其余真实阶段/native深验证不变|

最后一项是本轮只读核出的必要额外接缝，须父批准后才解除该单函数冻结。若不允许，B不能直接调用A前缀reader后声称支持selection变化；复制约90行深验证或临时替换publication.verify_bytes均不是建议方案。无需改旧publication.py、v2 publisher、c1 continuation、HOST/SPUG正文、资源安装器、generation、产品或原报告。

只新增专属测试/TDD日志；保留原A测试。A现有源码050c及测试835f已经进入正式16项托管；若单函数被批准修改，新执行pin与旧A实际执行pin必须分别固定。

## 两代原执行输入的严格读取

### 原c1的350项

已核现路径`main_program_installation_selection.py`为14854B/SHA `d1191685c5792f3caf438d0b093285ded09800140677db4b71b7e089332cbe0b`，它在c1原350和A原719内；collector d626不在两者中。

在修改selection前，由父排他保全且读回唯一d119原件。新`historicalSourceCustodyPin`指向TASK公开脱敏记录：

```text
MainProgramSpugVerificationSourceCustody/v1
schemaVersion
continuationAttemptPin   # 原c1私密attempt，精确350项
dependencyAttemptPin     # 原A私密attempt，精确719项
entries                  # 严格一行 {originalPin,preservedPin}
```

`originalPin`必须是两个原attempt中完全相同的d119 selection原pin；basename/任务目录角色、bytes/SHA及原attempt包含关系全部核对。`preservedPin`必须是PRIVATE内排他保存的不同路径原字节。重复行、额外源码、不同提交的selection、把整个目录都列入映射，一律拒绝。记录不能只自称“原源码”，必须绑定真实两个attempt。

A函数新增参数只接受已读取的上述严格记录及其pin，内部仍核原c1 attempt绑定和唯一selection角色；只把这一原pin改为核对应preservedPin，其余349项仍逐原pin读取。输出的实际证据pins收录托管原件，不把已被合法修改的d119现路径继续列为必须不变的当前输入。没有`skipVerify`或任意callback。

`continuation.prepare_value`可以继续复用：它从原不可变输入重建原SPEC，并按当前执行源码建立本轮工具pins；旧v2来源源码仍由原两份托管逐字节证明。它本身没有强制当前selection等于d119；实际阻塞在A的350循环。原c1成功前缀保持调用同一深验证器，不构造假PASS供v3全成功reader使用。

### A实际安装的719项

B新增纯reader `load_completed_dependency_activation(records,private,reference,historical_source_custody)`，不调用A的`prepare_value`：后者是安装前准入，当前simple已安装时`deployment_difference`应拒绝，不能把它当历史读取器。

先核A core/rich/attempt/七阶段/15原生原件与两次entry身份，随后验证719项：

1. 唯一d119 selection原pin走上面已绑定两个attempt的托管。
2. A的14候选、模块050c、测试835f只从已实际存在的16项`sourceCustodyPin`读取；每个映射必须与719中原pin逐字段相等，覆盖证据16项和依赖图再重建。这样候选checkout清理或A reader合法演进不会使旧A证据失读。
3. 原v2两份源码托管路径（含f663旧selection）是原件，保持原路径/rawSHA；不能用d119托管替代f663，也不能把两代source custody互相冒用。
4. 其余原输入逐原pin核验；新B执行源码另列当前inputPins，不能把新hash补入旧attempt。既有650构建托管继续由已有reader按其明确合同消费，不为本次创建大范围“找不到就用归档”的fallback。

映射集合以完整原pin为键而非basename；同path不同历史版本不能互相覆盖。无当前路径/托管路径的模糊优先级，无缺失时自动搜索。更广的旧任务工作区路径迁移如果仍有既有原件依赖，必须给出具体剩余路径并由原收尾合同处理，B不宣称替所有历史证据解决迁移。

## A成功reader必须验证的实际内容

- core只能是`MainProgramSpugRuntimeDependencyActivation/v1/PASS`，唯一simple APPLIED；resource commit c772、原c1failure、补充completion、base11安装、activationInputsPin完全闭合。
- rich完整字段和core投影精确相等，七阶段顺序/唯一原件路径严格；attempt/gate绑定相同，未覆盖旧c1claim。
- 15原生回执严格逐项绑定原argv固定容器、原program实际bytes、native exit0、stdout、stderr；不得用inspect回执替代before/installed/reload/after。
- 使用不修改的A runtime/reload生成函数重算五个原program并与stdinPin逐字节比较；单函数托管接缝不能改变这些正文。历史A执行源码另由16托管证明，不能因当前生成函数看似相同就省略旧050c证据。
- before/before-write对应旧simple和旧entry；installed为候选14但仍旧entry；reload严格新pid/start且其它身份/env保持；after为新entry和14文件。real stage stdout必须通过原`validate_runtime_result`/`validate_reload_identity`；替换前原件完整读回，原子移动结果、host目标路径和container读回pin一致。
- 资源PASS不自动得到publication PASS。B仍执行新的只读验证阶段。

## B输入、输出和API

输入仍采用原设计的严格12字段，不增加产品代次：

```text
MainProgramSpugPublicationVerificationInputs/v1
schemaVersion, sourceCommit, revisionId, controlGenerationPin,
continuationInputsPin, continuationAttemptPin, continuationFailurePin,
continuationCompletionPin, dependencyActivationPin, historicalSourceCustodyPin,
verificationId, outputFile
```

sourceCommit/revisionId从原c1取45完整SHA/r6；verificationId为明确`v1`（仅独立观察编号，不是重发布编号）。dependencyActivationPin指实际A core，其内部派生completion/16托管及安装输入；c1 runner原生缺席证明由原A输入指向的runnerExitObservationPin读取，并严格绑定本输入continuationCompletionPin。A全部同步native退出、rich/core落盘及冻结实际代码证明A变更阶段已闭合；父外层实际exit0另保留，不伪造新的机器查询。

建议outputFile严格为`main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v1.json`。新core继续复用原`project_core`的`MainProgramSpugInstallation/v1`字段，不能扩写旧核心合同。

API：

- `prepare_verification(task,private,input_basename)`：纯本机读取，返回历史上下文、新当前执行pins及验证SPEC；不创建claim，不调用网络。
- `run_request(..., verify=False)`：默认`PREPARED_NOT_VERIFIED`；只有显式CLI `--verify`才执行，只验收传输不提供`--apply/--activate`或publish方法。
- `validate_publication_v4(records,private,selected)`：纯深验证，返回现有`generation,inputPins`形状供selector/collector复用。

新selection严格5字段：

```text
TaskMainProgramInstallations/v4
schemaVersion, sourceCommit, controlGenerationPin,
spugInstallationPin, verificationInputsPin
```

只有真实完整验证原件和新core通过reader后，父才能排他生成该selection；本机fixture或A PASS不能先创建实际选择。

## 只验收执行顺序及原件

固定六阶段：`spug-guard-before → host-verify-57 → host-verify-58 → host-verify-59 → spug-verify → spug-guard-after`。

两guard固定A新entry完整身份/env、14文件、七配置、原audit/旧源custody/历史指纹、task快照及两实例。host三阶段直接使用原HOST_BODY/原SPEC的verify；不host-publish。Spug直接使用原SPUG_BODY verify；旧11检查保留，外围guard另完整核14。唯一可变SPEC字段是`spugSpec.observation.entryPid`，必须等于A实际151963且由A old→new证明；其余配置值/expected/auditPath/历史路由/任务/原11/代次逐字段完全不变。不能把before环境改成任意当前值。

新rich为`MainProgramSpugPublicationVerification/v1`，固定绑定inputs、verificationId、controlGeneration、原c1failure、dependencyActivation、attempt、六个stage原件、原六成功阶段pins及原失败阶段pin。每阶段保存排他的request/program/native stdout/stderr/actualExitCode；rich与core只有六阶段及原历史全部证明后才写PASS。失败/未知写独立FAILED原件并保留实际已完成列表，没有自动重试。

每阶段的request固定lane/host/phase=verify或guard；native argv固定原三服解释器或固定本机容器，program bytes重算相同。不能把不同host、inspect或无stdin receipt当该验证成功。

新只验收固定gate绑定完整c1FailurePin和固定容器，不用随机verificationId绕过未闭合原调用；原c1/A gate不删除。若新验证未知，仍只跟原PID/原native receipt，不自动重发验证或写入。源码不继承旧带install方法的传输；仅复用底层原生记录/读取函数，通过严格命令枚举构造三服verify与固定容器guard/verify。

控制GET可能新增原控制查询审计；报告为`configurationWrites=false,businessMutationDispatched=false,controlApiQueriesPerformed=true,queryAuditWritesMayOccur=true`，不写“服务器零写入”。所有阶段backup/restore=false。新成功只表示部署验证闭合，实际登录UI矩阵仍需父独立真实浏览器证据。

## BDD / RED → GREEN / REGRESSION

1. Given 实际c1 FAILED及A PASS，When 只验收prepare，Then 可严格读取七写入/三HOST及A真实单文件证据，仍不生成发布成功或现场调用。
2. Given 真实d119 selection托管，When 在临时文件闭包中变更当前selection路径字节，Then 原350旧调用先RED，唯一托管接缝GREEN；缺托管/改任一其它349项/额外映射继续拒绝。旧A默认分支行为保持。
3. Given A719与正式16原件，When 当前A helper合法变更或候选临时副本删除，Then 历史reader仍核旧执行字节；伪造旧module pin/换新工具字节/漏任何原件拒绝。
4. Given 实际15原生回执，When 删除一项、改容器/程序/argv/native退出或把installed与after互换，Then A成功reader拒绝；不只信rich布尔值。
5. Given 原验证SPEC，When 只替换经A证明的entryPid，Then 生成原HOST/SPUG verify；改audit/config/指纹/代次任一字段拒绝。
6. Given 六只验收阶段，When 参数含publish/install/custody或异常重试，Then 在派发前拒绝；真实本机原生文件/子进程测试证明命令与回执绑定，不宣称现场成功。
7. Given 全部六阶段真实回执，When v4reader投影core及三服选择，Then 形状与原控制选择一致，两原FAILED及claim仍逐pin保持；部分成功不能生成selection。
8. 回归只跑实际受影响A前缀/历史托管、continuation成功/失败reader、selector/collector及新B测试；原v1/v2/v3断言不能删改。当前A39及父135 PASS原件保留，新增测试不冒称已执行。

## 交付前置与边界

阶段A已完成；本轮尚未生成新selection旧源码托管、B输入、程序或任何验收成功。待父审准上述单函数额外接缝后，先由父排他保全d119，记录BDD/RED，再实现。若父不同意该最小接缝，明确阻塞B的历史c1前缀读取，不改冻结A绕过。

本设计不扩成通用历史源码装载器、不动态exec托管模块、不改全局验证函数、不复制整套安装体系、不触及新的产品构建/控制代次。更广收尾和最终真实UI验收仍由父按原全目标流程完成。
