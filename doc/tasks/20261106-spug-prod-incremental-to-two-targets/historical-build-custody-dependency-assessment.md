# 历史构建依赖与持久托管评估

## Current Status

completed（仅本次只读评估），等待父代理确认实施设计。继续同一完整目标的收尾前置职责分离，父任务计划为 `historical-build-custody-closeout-plan.md`。本结论不表示完整 Spug 任务、发布、恢复验收或清理已完成。前一 observation 组件已交父独立核验/提交，当前未修改其代码。调查基线 HEAD `16193812c9d8aa52053c363c8d3c4ef6809913c6`，共享目录存在父任务和其他归属原件，本评估仅拥有本文件。

## 目标、里程碑和预期验证

1. 只读追踪 generation/coverage、已发布 Spug 资源、旧 automatic 部署和 closeout 对临时 worktree 的直接与递归依赖。
2. 核对实际原包、提交、测试与 cleanup 记录，区分仍可读取、已删除但原件留存、证据缺口。
3. 提出最小正式历史托管合同、准确改动/API 边界及真实 Git/文件 BDD/TDD 设计，交父确认；不实施或执行测试。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；历史来源显式选择，证据不完整拒绝，不按目录缺失切换。
- 是否从根因和长期维护角度解决：是；安装前专属干净 checkout 与已完成安装后的不可变证据分离生命周期。
- 是否存在临时补丁或绕过：否；不重写原 pin、不建立空壳 worktree、不复制目录伪造 Git/历史事实。

## 经验门禁

- Trigger：历史读取闭包依赖本任务必须删除的临时发布 worktree。
- Preflight check：读取父计划、实际 generation、owned-builds、cleanup 与对应构建/测试原件；先枚举明确文件再读，禁止递归 PRIVATE 内 19 个构建 checkout。
- Blocker：消费者漏枚举、原提交/包/失败原件缺失、历史和新安装模式未显式分离、建议弱化专属干净 checkout。
- Verification：本阶段只读静态与原件摘要，不运行服务器/构建/测试/清理；后续真实临时 Git 仓库和实际文件验证由父确认后执行。
- Forbidden action：不改生产/测试/共享日志，不删除、移动、修复或重建任何 worktree，不访问服务器，不提交。
- Evidence：父计划、`main-program-control-generation-45dd7dc-r6.json`、`task-owned-builds.json`、既有 cleanup 原件、下述精确调用链与材料表。

## 结论与必须保留的边界

需要修正的是历史证据读取与安装前 checkout 校验的职责混合。不能只处理 45 的 22 个路径，也不能仅把 `Path.exists()` 改成可选：45/r6 的历史读取还隐式读取 899 的 461 个文件、维护仓的 12 个文件以及若干持久包/日志；当前 122 个返回 pins 不是完整物理依赖清单。

采用一个显式、不可变的历史构建托管入口，保存原始字节、原报告和提交/包/测试的关系；旧引用仍指向原路径和原 SHA，读取时由明确传入的托管凭据解析原字节。新的安装 prepare 保持专属干净 checkout、精确提交和实际输入检查。不能因 checkout 消失自动采用归档，也不能把归档加载成功解释成 Spug 发布成功。

现有机制已有两部分可复用：`published_resource_evidence` 已明确区分资源的历史读取与安装前校验；旧 `automatic_stage_deployment` 已能只凭原报告和私密安装原件读取历史。不存在可直接复用的、覆盖当前控制 coverage 原输入与提交关系的完整历史托管机制。

## 只读调查范围与证据限制

- 本次读取明确列出的源码、TASK 小型 JSON/日志、PRIVATE 顶层指定路径和构建/清理记录；未执行远程命令、测试、构建、清理或提交，未修改生产/测试/共享日志。
- 父代理说明系统盘为 SATA HDD 后，不再重验大包、不再递归扫描 worktree、不再运行宽泛 Git status；后续只读取已知文件与小型报告。19 项构建及对应标准包的存在/摘要关系已在本轮前段核对；未以此冒充所有双包成员、461/154 个输入或全部 Git 对象的新一轮验证。
- `catalogue-linux-input-r2.tar` 和 `source-archive-protection-regression-r10-input.tar` 已确认存在且大小与报告相符。此次没有取得它们与全部来源成员逐一比较的完成结果，因此“可直接复用为完整归档来源”仍须正式封存时验证，不记为 PASS。
- Git 提交身份、已运行测试次数及清理命令结果以下述原报告为证；本次不重新执行这些历史行为。旧 cleanup 的 `gitRegistrationAbsent` 是当时记录，物理路径当前仍不存在；本次未重新逐条执行 Git 注册表核验。
- 当前四控制已激活的事实来自实际 generation/core/rich，Spug 资源与 selectors 尚未完整发布。新托管记录只能证明证据保存完整，不可补造安装/恢复/测试历史。

## 消费者与精确依赖

下列行号以调查基线为准，文件均位于 TASK，另行注明者除外。

| 入口 | 实际依赖和结论 | 改动边界 |
| --- | --- | --- |
| `main_program_control_generation.py:346 load_control_generation` → `_validate:228` → `_validate_upgrade_materials:145` | 递归核显式前代、四 core/rich、计划、source baseline 和分层 receipt custody；后继调用共享 coverage。`_finish:338` 对返回 `inputPins` 直接重新读取原路径。 | 引入显式历史证据上下文，递归传递；不能改变前代/core/rich/计划/receipt 的证明要求。 |
| `main_program_control_activation.py:322 validate_generation_coverage` | 第 385 行读取维护仓的 12 个文件；第 390–397 行读取 45 工作区 22 个文件及维护仓 1 个测试；第 400 行读取 PRIVATE 原输入 tar；第 401 行核 899 coverage；第 403 行核 45 HEAD/clean；第 406–454 行实读两代、两变体包并核每成员、差异、编译、测试关系。 | 将“读取既有证明/原字节”与“当前安装 checkout 准入”分开，保留同一语义验证器。历史模式不能跳过包/差异/失败报告。 |
| `main_program_control_activation.py:460 validate_coverage` | 明确读取原 461 输入及 7 阶段报告，保留 r5/r7 失败；第 489–499 行强制 899 工作区存在、HEAD/clean 和 461 原 SHA。该 461 路径集没有进入其返回值，也没有合入 generation 的物理 pins。 | 历史模式须由原 coverage 派生完整 461 集合，不得只从现有 `inputPins` 归档。新增完整输入闭包结果，末尾复核不得遗漏。 |
| `main_program_control_staging.py:167 prepare_materials_from_records`；activation `prepare` 的 v4 分支约第 731 行 | 先读取前代 generation，再核本次候选 coverage；候选的实际包和干净 checkout 是安装门禁。 | 前代可显式使用托管历史；本次候选仍必须当前专属 checkout。不能把一个 `historical=True` 贯穿两者。 |
| `main_program_control_observation.py:252 prepare_observation`、`:247 _finish` | 调用 generation/load 和 select，核原计划中的前代选择全等，再对聚合输入直接 `pin_file`。 | 传递同一显式历史上下文；观察仍是现场只读观察，不能声称拥有写锁。原 selection 保留，另复核真正的物理托管输入。 |
| `main_program_spug_publication.py:313 validate_resource_build` | 安装前核 c772 专属工作区、HEAD/clean、全部 154 测试输入及 11 个资源文件；`git hash-object --path` 与原提交 blob 相等，并核真实日志。 | 保持新资源安装准入，不允许以历史归档替代。 |
| 同文件 `:682 published_resource_evidence` | 已有正式历史入口：核原 build、测试报告（154 个 SHA）、资源的 11 个 SHA 和实际测试日志；不读取 c772 checkout。 | 可复用历史/安装显式分离思路。它本身不重新读取 154 个原字节，不能宣称已经提供了完整字节托管。 |
| 同文件 `:715 v2_context`、`:755 validate_publication_v2` | 历史 full publication 默认用上项，但仍先加载 generation，继承 45/899 依赖；核 12 个真实阶段、core/rich、原观察与资源 productPins。`prepare_v2:745` 显式 `verify_checkout=True`。 | 保持已发布与未发布的严格区别；历史托管只能接 generation 与证据读取，不能跳过 12 阶段或反推 Spug 成功。 |
| `main_program_installation_selection.py:186 / :231 _select_v2` | v1 主要读取原记录；v2 经 `validate_publication_v2`。返回 `localInstallationPins`，后续读取器还会重新读取这些路径。 | 新显式历史上下文只向 v2 必需分支传递，旧 schema/合同不改。 |
| `observe_closeout_hosts.py:212` | MAIN selection 间接依赖 generation；远端只读结果返回后直接重新读所有 `localInstallationPins`。 | 改用同一正式输入校验器，不保留第二套路径替换逻辑；远端业务/进程/挂载检查仍原样。 |
| `main_program_spug_resource_activation.py:79 prepare / :125 dispatch_prepared` | 安装前严格资源验证，并实际读取工作区新资源用于发送。 | 安装阶段必须仍有实际干净 checkout；该模块不应接“已删除即归档”的分支。 |
| `automatic_stage_deployment.py:40 check_build / :47 load_stage_deployment` | 只读 FULL/I1/I2 的显式 stage、原 build、public/private 安装原件，保持混合代次和 retained targets；不读取临时工作区或 Git status。 | 无需生产改动；用已删除工作区的真实文件测试回归，防止新托管机制反而制造依赖。 |
| `closeout_contracts.py:64 build_entry / :172 current_installations / :251 validate_source_spug / :305 automatic_chain` | worktree 字符串用于归属/身份比较，不要求目录存在；自动链读取原报告。不是临时 checkout 依赖。 | 保留旧历史合同；仅新 closeout 入口需要明确支持 MAIN 当前选择和 typed ownership。 |
| `verify_automatic_backup_chain.py:39 package_manifest` | 读 `PRIVATE/package-<commit>/backup-restore-standard.tgz` 与原构建/manifest；不读取 checkout。 | 必须保留原包，不能以只留 build JSON 代替；旧 130 文件合同不拓宽成新 147。 |
| `prepare_automatic_ui_preflight.py:14 / :74` | 是新一次 UI 行为前对实际执行源码、提交关系及运行输入的准入，不是已完成自动链历史 reader。 | 不为清理而放宽；本轮不重跑旧现场动作。 |
| `cleanup_owned_build.py:23–75` | 旧 ready_for_closeout、真实自动备份/恢复和稳定控制准入后，核本任务 checkout/ignored/提交/进程/包，再删除；只认 legacy automatic-current-installations、engine 命名；现无历史消费者可持续读取门禁。 | 需显式新 MAIN closeout inputs 和托管先验。不能直接执行当前分支清理当前任务后半段。 |
| `verify_closeout.py:192`、`commit_records.py:178–198` | 对当前 owned-builds 与原 cleanup aggregate 全等，要求物理/Git 注册均不存在；不会读 checkout 内容。 | 新不可变清理汇总须绑定完整最新所有权范围及之前 11 项原件，不能覆盖旧成功报告或降低当前闭合要求。 |

### 必须分开的逻辑原引用与物理读取凭据

`main_program_control_generation.py:96 _partition` 强制 `privatePlan.currentSelections == previous.selections`。`selections.localInstallationPins` 是该等式的一部分；已写入原私密计划，不能追加归档路径或改写旧 pin。`main_program_control_observation.py:274` 也核这项全等。

因此新增归档元数据不能混入原 selection 字典。返回的逻辑选择继续含原 pins；另以只读上下文/验证结果保存 `verificationPins`（新 manifest、归档、仍原位的报告/包等）。所有直接复核原路径的有限调用点应改用该上下文的 `verify_original_inputs`，并同时复核新物理凭据。归档映射必须匹配原 path、原 SHA、原 bytes（旧输入只有 SHA 时先按原报告限定成员，并明确补充实测 bytes），不是一个全局任意路径重定向器。

补齐原先隐式的 461 输入也只能进入独立的完整验证依赖/托管集合，不能追加入历史 selection 的 `localInstallationPins`，否则仍会破坏旧计划全等。历史逻辑闭包的原形和本次完整物理验证的集合需要同时保留。

## 实际材料与清理范围

| 原件 | 本次核实事实 | 后续封存需要 |
| --- | --- | --- |
| `main-program-control-generation-45dd7dc-r6.json` | 2561 B，SHA `2e29dd21044f2d7c44ba3a6800140ed225dec822b3e80944e4a84103b13b2b29`；实际 PASS；保留未发布布尔字段。 | 作为历史入口原件，原内容不改。 |
| `main-program-control-coverage-45dd7dc-r1.json` | 23187 B，SHA `c385a5fac8a0a76f5e0c5164a49d8c2eed9b2c78bfdce9467cfa01a686495357`。 | 保留 baseline、delta、实际包、失败报告的完整关系。 |
| `release-build-899730d.json` | 32255 B，SHA `a6576dcf3ec5c7024abbc9d7827495d34030109bfbf0362ddfba11a3e91019da`；提交 `899730de38c0e883245c11f2ad7986424ecbaf80`。原记录 461 输入、109 LF/352 CRLF，`GIT_CHECKOUT_INDEX_FROM_TARGET_COMMIT`，无源内容复制、无新提交/待合并。 | 精确保存原 raw bytes，禁止统一换行后改 SHA。461 由原 coverage 清单派生。 |
| `release-build-45dd7dc.json` | 933 B，SHA `112b7631c8f94540220ba9991eeb4c898108578f0e5fcca1b79f51a512d111f1`；提交 `45dd7dc65409c87fe856584b85873ea96c0b830e`；147 文件标准包。 | 保存 23 Linux 输入和 12 本地证据输入的并集及实际两变体包关系，不把 source59+standard50+lightweight50 写成全套重跑。 |
| `source-archive-protection-regression-r10-input.tar` | 实际存在、8980480 B；原报告 SHA `10a79b1f8f919d31610534da083c3655343285cd34543a2da613ed77879610d4`。 | 可作为明确候选来源；须逐成员核原 461 SHA 后才登记复用，不猜目录布局。保留原 7 阶段及失败原件，不仅 r10 PASS。 |
| `catalogue-linux-input-r2.tar` | 实际存在、2293760 B；原报告 SHA `964a04dad8d4438adefcaa98f89c440ac10a7999c38b4c4036fa2b7db2b0090f`。 | 可作为候选来源；仍须核 23 个源成员、两代双包和 manifest 的实际对应。 |
| `spug-resource-build-c7728ad.json` | 2351 B，SHA `659ae1f24bbb7f110a58c67b11618dfcda18e7104b65517b692f536388a47368`；提交 `c7728adcecf94c199c0954330b29184f56b9c053`；11 资源。 | 不能只归档 11 个资源：测试报告实际绑定 154 输入。 |
| `spug-resource-validation-c7728ad.json` | 19002 B，SHA `21ea75038aee1bc22390ebdbf79c65df6f49c3ff6cfb8b4dd2a06197b767b298`；96 PASS/0 skip，实际日志原 pin 本次重核一致。 | 原测试报告/日志、154 原输入和提交归属一起封存；新验证不能改写原 96 结论。 |
| `spug-resource-worktree-c7728ad.json` | 1678 B，SHA `ecd478de8013cdea3973b560f601eaa3749a67ef4816071f6bd376260999b7ef`；`VALIDATED_NOT_INSTALLED`，无新提交/待合并，目录实际存在。 | 用独立 SPUG_RESOURCE 所有权类型纳入最终清理，不伪装成 engine 包条目，不提前声称资源已安装。 |

`task-owned-builds.json` 有 19 项 engine 构建。当前 11 项目录已不存在，并各有原 PASS/deleted/physicalPathAbsent/gitRegistrationAbsent 清理记录：

`6319024、d487abf、9a65b5a、701b442、7c5f057、9c93449、0c5828a、3019c2e、0d44578、b5c8817、0dc7429`。

另 8 项目录实际存在：`73c0e72、362c7f3、5cf430d、d8e44bb、978c40c、5a5d6eb、899730d、45dd7dc`。额外的 `release-spug-c7728ad` 不属于该 19 项 engine 清单，故本任务最终拥有的剩余构建工作区是 8 个 engine 加 1 个资源工作区；不能根据旧计数只清理 8 个。

旧 `owned-build-cleanup.json` 为 18368 B，SHA `ddefa0ae54285bb85eeba6e81f2b2c6f04be470508cabe7548e6eda6dee9663d`，它证明当时的 11 项，不是当前 19 项的完整清理证明。其旧 manifest pin 与当前扩大的清单不同，是范围随任务增长的历史事实；必须保留该旧原件。新 closeout 应追加有独立名字和 schema 的汇总，引用旧 aggregate/逐项记录及本次新增结果。

已删除 11 项不需要重建 checkout。旧自动阶段 reader 原本不依赖目录；只有确实需要而没有任何原字节来源的证明项才单独阻塞，不能伪造 461 类覆盖或给每个旧包补造全套测试。

## 建议的最小正式合同

### 1. 显式封存原件，历史读取不发现“当前最新”

新增 `historical_build_custody.py`，只管本任务明确登记的构建证据，不管服务器安装/active receipts。建议一个版本化的 `HistoricalBuildCustody/v1` 公共 manifest，包含：

- 固定 schema、taskId、唯一 custodyId、`state=SEALED`、建立时间、实际 verifier pin；明确 `installationPerformed=false / testsExecuted=false / serverWrites=false`，它是本次封存验证，绝不重标原测试或安装结果。
- 每项 `kind=ENGINE_PACKAGE | SPUG_RESOURCE`、精确完整 commit、原 buildReportPin、originalWorktree（身份信息，不作为历史模式的存在条件）、coverage/test evidence 原 pins、实际包/manifest 原 pins、对应提交树身份。
- 原输入集合完全由已核原报告派生。每个输入保留原 reference、用途及所属报告 pin；新增归档成员描述仅说明原字节的位置。允许明确选定的原 `PINNED_TEST_ARCHIVE` 或新 `CAPTURED_INPUT_ARCHIVE`，不因源目录缺失自动切换。
- 每个 archive/member 的原始 bytes/SHA、固定安全成员名、有限总大小/成员数；拒绝重复、绝对路径、`..`、软硬链接、额外成员、覆盖写入。内容保留 PRIVATE，公开 manifest 不包含私密配置内容、凭据或环境文本。归档范围只限已证明需要的代码/测试/报告/日志/包，不能把整个 PRIVATE 打包。
- 每个提交源码输入绑定原 Git tree 中的 blob 身份与原 raw 字节。封存时在真实 target commit checkout 中核当前 HEAD/clean、原 SHA 及原 `git hash-object --path` 关系，固定结果；历史读取核原报告、归档 raw SHA 和提交/blob 对应，不再执行临时 checkout 的 status。使用稳定主仓的 Git 对象读取（显式 repository 参数、精确 commit/tree），不制造工作区。收口合并门禁必须确认提交可达；对象缺失必须报错，不能只信新 JSON 的 `verified=true`。
- 明确区分 `COMMITTED_SOURCE` 和 `TASK_TEST_INPUT/ORIGINAL_LOG`：任务日志、独立测试及报告按原证据 pin 绑定，不能猜测它们属于某个构建提交，也不能为通过 Git 门禁给历史原件补造提交归属。
- LF/CRLF 原表示是合同。历史原 raw SHA 与 Git blob 可分别保留，严禁用 LF 内容替换原 352 个 CRLF 输入。原记录已绑定 raw SHA；封存新记录只能证明保存了这批原字节，不能重新解释旧测试实际输入。

writer 和 reader 分离。writer 仅在另行批准后按明确清单核验、使用唯一新目录和 O_EXCL 原件写入并完成末尾复核；reader 不创建/修复文件。原 build/coverage/generation/selection/计划/失败/cleanup 文件全部不改。将来的撤回只能更换新的显式调用输入，不能覆盖已被 pin 引用的 manifest。

### 2. API 与原合同兼容

建议新增正式 API（名称可在父审阅后定稿，行为不可模糊）：

```python
seal_build_custody(task, private, *, inputs, destination, repository) -> custody_pin
load_build_custody(task, private, custody_pin, *, repository) -> HistoricalBuildCustody

# 严格限定到由原报告派生的条目，不能给任意 path 兜底。
custody.read_original(reference, *, evidence_pin, purpose) -> bytes
custody.verify_original_inputs(references) -> None
custody.finish() -> verification_pins
```

读取上下文最多在一次调用中按原 pin 缓存已核字节；末尾核物理 archive/报告/包没有漂移。按明确索引一次顺序读取归档，避免 HDD 上每个逻辑成员再扫描整个归档或 checkout。不要在这一重构中改变现有包/失败证据校验算法。

现有 `load_control_generation` / `select_control_generation` 增加 keyword-only `historical_custody=None`，无参数时保留原严格行为；明确传入正式类型时才使用历史原件解析。递归同一上下文，但保留每个前代独立 Records 和原 closure，防止子代 pins 污染前代选择。原 `inputPins`/selection 仍表示原逻辑证据，新增与之分离的 `verificationPins`/reader receipt 承载实际物理来源；不得向原 `currentSelections` 字典塞新字段。

coverage 两层 API 建议分成“证据语义验证”与“候选 checkout 准入”：

```python
validate_coverage(records, build, *, historical_custody=None)
validate_generation_coverage(records, inputs, predecessor,
                             *, candidate_custody=None, predecessor_custody=None)
```

历史 generation 读取可显式对两代使用同一已核 custody。新 activation/staging prepare 必须 `candidate_custody=None` 并执行本次专属 checkout 准入，仅前代可使用 `predecessor_custody`。不能用一个布尔开关使本次安装也进入历史模式。资源的 `validate_resource_build` 无历史参数、维持当前安装检查；`published_resource_evidence` 可消费同一 custody 取得完整旧 raw 输入，保留原无参数历史合同。

### 3. 新收尾输入必须独立且完整

建议新增 `TaskBuildCloseoutInputs/v1`，显式引用：当前 engine manifest 原 pin、额外资源 worktree ownership pins、历史 custody pin、之前 11 项 cleanup aggregate pin、本次实际完整安装 selection pin 与稳定控制证明 pin。它不推断当前安装，不把控制代次索引当 full Spug selection。

执行阶段必须先完成本任务真实完整目标，再标 `ready_for_closeout`，核实际新 MAIN 当前控制/Spug、恢复/备份验收和控制台稳定路径；逐项保留旧 clean/ignored/new commit/进程/运行 helper/包/归属门禁。删除前先用显式 custody 完整读取历史（禁止碰原 checkout 的测试证明必须先有）；删除后复核同一历史结果及物理/Git 注册缺失。新增 `owned-build-cleanup-final-rN.json` 引用原 11 结果和新增 9 结果，不覆盖 `owned-build-cleanup.json`。

## 准确待改文件与分工建议

| 文件 | 必要修改或明确不改 |
| --- | --- |
| 新 `historical_build_custody.py`、对应独立测试 | 唯一封存/读取/原 pin 到归档成员的严格合同；真实 Git/原文件测试。 |
| `main_program_control_activation.py` | 复用原 coverage 语义，分离历史原件输入与本次候选 checkout；补完整 461 输入收集；不改远端激活行为。 |
| `main_program_control_generation.py` | 显式 custody 递归与末尾输入校验，保持原 logical selections/privatePlan 全等。 |
| `main_program_control_staging.py` | 前代历史上下文与本次候选严格准入分开；不改远端 staging 写法。 |
| `main_program_control_observation.py` | 仅输入解析/末尾复核接统一 helper；现场 RuntimeGates 不改。 |
| `main_program_spug_publication.py` | v2 历史/prepare 分支传递明确上下文，保留 12 实际阶段与安装前资源检查；历史资源原字节托管可复用新 helper。 |
| `main_program_installation_selection.py`、`observe_closeout_hosts.py` | v2 历史上下文透传，直接 read_bytes 的本地原引用复核接唯一 helper；不改服务器观察合同。 |
| `cleanup_owned_build.py`、`closeout_contracts.py`、`verify_closeout.py`、`commit_records.py` | 新显式 MAIN closeout schema 分支、资源所有权、持久证据先验及独立最终汇总；旧 schema/旧 11 项成功原件保留。建议在 custody/历史 reader GREEN 后作为单独 BDD 阶段。 |
| `automatic_stage_deployment.py`、`verify_automatic_backup_chain.py`、`prepare_automatic_ui_preflight.py` | 无需为历史托管修改生产；保留相关回归。实际包仍必需，新的 UI 行为准入仍严格。 |
| `main_program_spug_resource_activation.py`、`installation_history_custody.py`、纯 upgrade planner | 不修改。前者新安装仍要实际源码；后两者分别负责远端 active receipt 与纯计划，不应混入本机归档生命周期。 |

现有 `ops/spug/release-center/intruoyi_build.py:428 cleanup_sealed_build` 和 `nas_package_retry.py:30 verify_sealed_package` 可复用“原包封存后清理、失败保留、不重编译”的流程原则和安全成员校验，但其 releaseTag/application/manifest schema 不适用于本任务 generation/coverage，不能直接拿它们当当前托管证明。

## BDD 与后续真实 RED→GREEN→REGRESSION 设计

仅设计，本阶段未运行以下测试。测试应使用真实临时 Git 仓库、已提交文件、`git worktree add/remove`、实际归档和原报告文件；不连接服务器，不 mock 安装/测试成功。外部既有历史原件在测试中是固定协议载体，不能称真实业务恢复。

1. **删除后历史保持**：Given 真实提交、独立干净 worktree、原覆盖/包/报告；When 正式封存并删除该测试拥有的 worktree；Then 明确 custody 模式仍核同一历史结果/原 pins，默认 checkout 模式真实失败。
2. **新安装仍阻断**：Given 历史归档有效；When 新安装候选 checkout 缺失、HEAD 不同、已跟踪/未跟踪文件变化；Then prepare 失败，归档不能使本次候选通过。前代已归档与本次干净候选可正常同时验证。
3. **原字节与 Git 关系**：Given 提交 `.gitattributes` 的 LF/CRLF 和二进制原件；When 封存/删除/重读；Then 原 raw SHA、原 commit/blob、报告引用保持。改 raw 换行、commit/tree/blob 或只改新 manifest 的“通过”字段必须拒绝。
4. **完整隐式依赖**：Given 返回 pins 只含 22 个 45 路径，但原 baseline 有 461 输入；When 漏一个 899 文件或漏一个维护仓本地证据；Then 封存及历史读取均失败。资源 154 输入漏一个也失败，不能只核 11 文件。
5. **归档结构和漂移**：缺成员、额外/重复成员、路径穿越、链接、错 bytes/SHA、同名替换、超过上限、末尾漂移均拒绝。显式原测试 tar 只有完整对应原清单时才可复用。
6. **历史失败保持**：原 7 阶段 r5/r7 失败、catalogue r1 失败和 source59/实际两包50 原证据逐项保留；只留 GREEN 总数或手工汇总成功必须失败。
7. **前代选择稳定**：真实文件生成两代/三代记录；旧 `privatePlan.currentSelections` 原 bytes 不变，显式归档前后 selection 深度相等；物理 `verificationPins` 可不同且独立严格核。前代闭包不受子代读序污染。
8. **已发布/未发布隔离**：仅四 core/rich 和 custody 有效时，完整 publication 仍拒绝；原 12 阶段完整时才通过，资源或阶段 pin 漂移均失败。
9. **旧 automatic 兼容**：实际临时文件构造 FULL/I1/I2 混合代次及 private 原件，删除各测试工作区后原 loader 继续相同结果；删原标准包时 package audit 仍失败。
10. **资源安装职责**：published_resource_evidence 可在工作区删除后核原发布证据；新 resource activation prepare 仍失败。c772 资源 ownership 不可伪装为 engine 147 文件包。
11. **最终所有权范围**：旧 11 cleanup 原件保留，最新 engine19 加 resource1 必须精确覆盖；未归属工作区不动，缺某项 custody/当前 full selection/稳定运行态/恢复验收不得进入删除。
12. **真实清理后闭合**：只删除测试自己创建的临时 worktree；旧原件 hash 不变、新汇总引用全齐、物理与 Git 注册缺失；删除中断不产生 completed。

建议分三次可审阅的 TDD 单元：A 新 custody 与真实 Git/文件测试；B coverage/generation/publication/observer 消费者；C typed closeout 和旧 automatic/commit-records 回归。各阶段先实际 RED 再最小实现、GREEN 和关联回归，不把缺环境/跳过当通过。父代理统一决定实际命令与执行时机；本阶段没有任何 RED/GREEN 新结果。

建议 A 阶段新测试名 `test_historical_build_custody.py`；本机候选命令使用既定 Python 的 `-X utf8 -B -m pytest -q -p no:cacheprovider <TASK>/test_historical_build_custody.py`，`PYTHONPATH` 沿用本任务显式 test-dependencies。B/C 再按上述有限消费者增加原套件。真实 Git 测试应在临时目录中创建自身 repo/worktree，不能把测试参数指向 19 个实际构建工作区；是否需要独立 Linux 封装由父按可用环境决定，本阶段不启动任何 runner。

## 尚未证明和实施前必须确认的事项

- 现有两个输入 tar 与 461/23 清单逐成员全等、154 资源输入的完整可读来源、稳定主仓各原提交/blob 的可达性，须在正式封存中实际核验。本次没有完成这些读取，不能提前登记 SEALED。
- 现有 12 本地证据包含 1 个产品源文件、1 个测试、10 个原 RED/GREEN/REGRESSION 日志；它们也应原位保留或被明确托管，不能只保存 release-* 文件。
- 旧已删除 11 个 checkout 的 package/report 历史能力无需增强成未曾有过的全覆盖；只有被当前实际 reader 消费的证据按原合同保存。不能回写旧 `deleted=false` 构建报告，其含义是构建时状态。
- 当前尚未完整发布 Spug，也未达到当前完整任务的收尾准入。即使上述设计获批、代码 GREEN、原件已封存，也仍不能提前清理构建工作区。
- 设计阶段完成并停止；下一步由父代理确认具体 schema/API 和实现归属，再进入新增失败测试。
