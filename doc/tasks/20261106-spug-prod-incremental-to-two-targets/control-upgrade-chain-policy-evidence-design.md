# 链策略控制升级证据合同设计

## Current Status

design_review。父任务批准只读分析后要求独立设计；尚未修改产品、旧验证器、计划或原件，未运行测试/构建/Docker/远端/浏览器。本设计属于 `control-upgrade-policy-evidence-plan.md` 的 Subagent-Driven Development 子阶段，等待父审查后才准备 RED。

## 目标、里程碑与预期验证

保持目录优化历史的 `ArchiveCataloguePackageDelta/v2`、`MainProgramControlCoverage/v1` 逐项原规则；为本轮链年龄/点数准入新增独立版本和固定审核范围。新证据必须证明实际两代双包全部成员、唯一批准的程序差异、同一提交的真实测试输入与成功终态；不能通过任意报告自报 PASS 放行。

里程碑：精确设计审查 → 新合同真实临时原件 RED → 最小两处分派和独立验证器 → 新旧回归 → 父独立验证与实现提交。真实构建/安装/页面操作均是其后单独阶段。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。schema/profile 精确选择；任何未知版本、范围、原件、结果或输入漂移拒绝。
- 是否从根因和长期维护角度解决：是。审核范围按显式版本隔离；新旧原件各按其创建时合同验证，不修改旧 allowlist 或重解释历史。
- 是否存在临时补丁或绕过：否。无固定本轮提交、测试数量或失败轮次白名单，不制造失败来满足模板。

## 经验门禁

- Trigger：目录优化的单模块与23/27/9、59/50/50测试证据不能覆盖链策略三模块修改。
- Preflight check：实际调用链与原版本条件已逐项读取；明确 STANDARD147/LIGHTWEIGHT146，SAFE 包来自冻结基线加 transforms，不能要求它等同普通源码或仅测 lightweight。
- Blocker：额外语义文件、缺一种包、旧/新提交或前代绑定错误、未批准测试集合、命令非零/超时/缺终态、任意 fail/error/skip、实际加载模块不属于被测包、原始日志或结果 pin 不符。
- Verification：真实临时 tar、源快照、JUnit/逐测试事件及命令退出原件；新旧路由回归和父独立实际包测试；全部输入进入最终 physicalPins 并再次核验。
- Forbidden action：改旧常量或失败要求；以模块 AST 相似代替实际 SAFE 文件；给当前失败添 PASS；把父点历史或上一轮测试当本轮结果；访问未授权远端。
- Evidence：父事前计划、现有两验证器和 generation/staging 调用链；后续本设计对应专属 RED/GREEN 原始日志。

## 已核调用链与最小接缝

1. `main_program_control_upgrade_plan.plan_control_upgrade` → `validate_delta`；同函数也用于私密/公开计划的完整重建。
2. `main_program_control_activation.validate_generation_coverage` 由 activation.prepare、staging.prepare_materials_from_records、generation._validate_upgrade_materials 共同调用。
3. generation 另核 `coverage.actualPackageEvidencePins[0] == plan.packageDeltaPin`；stager 核同 pin 属于该数组。现有返回值为 coverage/build/delta/packageFiles/previousPackageFiles/physicalPins。
4. 旧 coverage 要求前代 build.exactTestCoveragePin 和899的461证明。45的 generic build 没有该字段，不能用旧路径冒充45自身的新验证。新覆盖证据必须经45的实际 generation 和四份 rich 激活原件绑定其原 coveragePin。

拟新增唯一正式辅助模块 `main_program_chain_policy_evidence.py`，分为纯差异验证与严格本地原件读取两个职责明确的入口：

- `validate_chain_policy_delta(delta, build, build_pin, old_build, old_build_pin, files, previous_files, commit, previous_commit)`：签名与旧纯 delta 一致，只完整处理传入的 STANDARD raw maps；校验另一 variant 的严格声明结构，不假称已读取其内容。
- `validate_chain_policy_coverage(records, inputs, predecessor, *, file_pin, validate_initial_coverage)`：读取原件、两代两包和测试终态，返回原六字段 shape；纯内部函数对每种 variant 独立重算差异。默认不运行任何构建或测试，不访问网络。

最小接线只有两处：planner.validate_delta 在明确新 schema 时调用新纯入口，其他情况继续现有旧函数体；activation.validate_generation_coverage 读 report 后在明确新 schema 时调用新入口，旧 v1 函数体和既有所有检查不变。新模块不反向 import activation，避免循环；必要旧初代完整覆盖通过显式函数参数调用。

generation/stager/plan v2/activation inputs v4/rich receipt 字段不改。`actualPackageEvidencePins` 第一项仍固定为本次 delta pin，唯一覆盖读取返回值保持原合同。新旧原件文件名采用显式 pin 和受控普通文件名，不自动找 latest，不固定r2/r3。

## 通用 pin 与原件规则

`LocalPin` 精确为 `{file, bytes, sha256}`，file 为 TASK 内无分隔符的固定普通文件名；`PhysicalPin` 精确为 `{path, bytes, sha256}`，绝对路径须在已绑定 TASK、PRIVATE 或候选构建根范围。所有整数排除 bool。原件先核真实普通文件/别名及读取前后身份，再核完整 bytes/SHA，JSON 仍拒重复 key。非 JSON 原始日志、tar、源码只做字节验证，不按 JSON 解析。

所有已读文件加入 physicalPins；返回前再核完整原件集合，任何输入在验证过程中变化即失败。tar 必须无重复成员、链接、路径穿越/非规范路径；维持已有单成员16MiB、总展开128MiB、原始证据64MiB上限，若真实材料超过则明确阻塞，不自动无限扩大。

## 新 delta：MainProgramChainPolicyPackageDelta/v1

顶层精确字段：

`schemaVersion, status, profile, sourceCommit, predecessorCommit, buildPin, predecessorBuildPin, predecessorGenerationPin, sourceSnapshotPin, packages`。

- schemaVersion 固定新值；status=`PASS`；profile=`incremental-chain-policy-admission/v1`。
- sourceCommit、predecessorCommit 为两个不同的完整 Git SHA；buildPin 与 predecessorBuildPin 必须是调用方当前/前代 build；predecessorGenerationPin 必须是已验证前代 generation。
- sourceSnapshotPin 指向下述本次提交输入快照声明，覆盖构建和测试使用的已提交材料。
- packages 恰有 standard、lightweight 两项，顺序固定；文件数分别147、146，不互用 variant 的成员或摘要。

每项精确字段：`variant, packagePin, fileCount, fileManifestSha256, predecessor, changedFileEvidence, unchangedFileSha256`。

`predecessor` 精确字段：`variant, packagePin, fileCount, fileManifestSha256`。packagePin 是完整 tgz 的 PhysicalPin。STANDARD 当前/前代三个摘要字段必须与各自 build 完全一致；LIGHTWEIGHT 独立核真实 tar 和 manifest，不从 STANDARD 推算。

changedFileEvidence 为 path→`{oldBytes,newBytes,oldSha256,newSha256,lineEndingOnly}`；unchangedFileSha256 为 path→SHA。验证器自己从两代 raw maps 重算，两组互斥并精确覆盖该 variant 的原成员集合。原/新 member names 必须完全相同；每个 Python 成员实际 compile。

本 profile 唯一批准的语义变化集合为：

- `common/repository_records.py`
- `common/repository_minimal.py`
- `control/recovery_control_incremental_plan.py`

两 variant 均须精确为这三个语义文件；其余 raw 变化仅允许 CRLF/LF 归一后字节一致且 Python AST一致。若真实最终包不是这个集合，停止报告差异，由父审明确新设计，不能自动放宽为任意子集/超集。不要求三个文件在 STANDARD 和 LIGHTWEIGHT 之间同 SHA，更不能把 SAFE repository_minimal.py 与普通源码 AST 全等作为替代。

## 新覆盖：MainProgramControlCoverage/v2

顶层精确字段：

`schemaVersion, status, profile, sourceCommit, baselineGenerationPin, baselineBuildPin, baselineCoverageKind, baselineCoveragePin, candidateBuildPin, packagePartitions, deltaTestEvidencePins, actualPackageEvidencePins, failedEvidencePins`。

- profile 与 delta 同值；candidateBuildPin/commit 和 baselineGenerationPin/build 与调用方、delta 完全相同。
- packagePartitions 恰有 standard/lightweight，各为 `{changedFileEvidence,unchangedFileSha256}`，与真实两包及 delta逐项相同。
- deltaTestEvidencePins 恰有一个本轮 `MainProgramChainPolicyVerification/v1` 成功报告 pin。
- actualPackageEvidencePins 恰为 `[deltaPin, 同一成功验证报告pin]`。不得把旧目录报告放入新 profile。
- failedEvidencePins 可以是空数组。不要求先制造安装/验证失败；已明确登记的失败按原件保留，只作为失败历史，不计入任何通过证明。每项必须是下述同版本验证报告的真实 FAIL 终态，不接受不明 schema 或改写成 PASS。

### baseline45原件绑定

`baselineCoverageKind` 是显式联合类型，只有以下两值：

1. `CONTROL_GENERATION_COVERAGE`：本次前代45应使用此值。baselineGenerationPin==predecessor.generationPin；baselineBuildPin==该generation.buildPin；从该 generation.activationEvidenceByHost 明确引用的四份实际 rich 原件取 coveragePin，四份必须完全相同且等于 baselineCoveragePin。每份 rich 都须已在 predecessor.inputPins 内，重新按其原 pin 读，并核 sourceCommit/buildPin/previousControlGenerationPin/revisionId 与已验证 predecessor 的关联；其 activationInputsPin 也必须绑定同 coveragePin。原 coverage由既有 generation loader 已按自身 v1 合同完整验证，不能仅信 rich 的 PASS 字符串。
2. `INITIAL_FULL_COVERAGE`：仅当显式前代为初代 AUTOMATIC_INSTALLATION、build.exactTestCoveragePin==baselineCoveragePin 时可用，继续原 validate_coverage 的完整461/原失败/原源码规则。不得遇前项缺失后自动降到此项。

未知 kind、缺四份相同rich、把899证明直接填为45coverage、同名不同pin、缺前代build均拒绝。新合同不修改历史 generation/v1 字段或旧rich。

## 同提交输入快照：MainProgramChainPolicySourceSnapshot/v1

顶层精确字段：`schemaVersion, sourceCommit, buildPin, archivePin, filePins, gitHeadPin, gitStatusPin, captureReceiptPin`。

- archivePin 为保留的真实输入 tar；filePins 为规范相对路径→`{bytes,sha256}`，精确覆盖 tar 中全部普通文件。三份产品源、standard_fixes及固定构建映射/基线输入、全部所选测试与运行器都必须包含；不得漏任意实际运行输入。
- gitHeadPin 原始输出必须精确为 sourceCommit；gitStatusPin 原始输出必须为空；captureReceiptPin 为实际快照命令终态，exit0、timedOut=false，读前后文件集合/SHA相同。不能仅自报 worktreeClean=true。
- 当前准备按既有门禁实际核候选 worktree HEAD/clean，并将快照文件逐项与同提交 checkout 原件核对；原始 tar、git输出和命令回执永久纳入原件闭包。已有临时worktree历史读取收尾问题仍由父独立阶段处理，本设计不暗中取消旧验证。
- buildPin 绑定同一候选 build；不要求被转换的 SAFE 文件与源文件逐字节相同：SAFE/LIGHTWEIGHT各自真正运行的模块必须绑定对应实际包成员，测试运行器及 transforms 则绑定这个同提交快照。

## 实际测试：MainProgramChainPolicyVerification/v1

顶层精确字段：`schemaVersion, status, profile, sourceCommit, buildPin, packageDeltaPin, sourceSnapshotPin, runnerPin, runs, failedAttemptPins`。

每个 run 精确字段：`suiteId, mode, commandPin, inputPin, collectionPin, resultPin, stdoutPin, stderrPin, exitReceiptPin, loadedModulePins`。

- mode 为 source/standard/lightweight；inputPin分别绑定同提交source archive或该variant实际tgz。runnerPin必须在source snapshot精确输入集合中。
- commandPin为原始JSON命令原件，含固定argv、cwd、mode、sourceCommit、inputPin、testFiles、startedAt。禁止`-k`、排除选择、`--ignore`、替换测试文件或混用其它包；执行方式由固定profile核对，不接受任意自报suiteId。
- collectionPin为同次真实收集原件 `{suiteId,mode,testFiles,nodeIds}`；nodeIds非空、唯一，来自指定完整测试集合。
- resultPin为同次pytest事件/JUnit正规化原件 `{suiteId,mode,tests,failures,errors,skipped,nodeResults,junitPin}`，每个nodeResult含原nodeId及实际setup/call/teardown终态；集合与collection精确相等。所有阶段成功，tests>0且等于实际节点数，failures/errors/skipped均严格0。JUnit原件必须与这些数和每个测试终态一致；不能只解析最后一句“passed”。
- exitReceiptPin为原始父执行器终态 `{commandPin,inputPin,startedAt,finishedAt,exitCode,timedOut,inputPinsBefore,inputPinsAfter}`；exitCode严格0，timedOut=false，结束晚于开始，两个真实输入集合相等并与该输入快照/包和runner一致。原stdout/stderr固定pin且按真实输出保留，原命令/JUnit/节点终态之间相互绑定。
- loadedModulePins包含实际进程加载的上述三模块路径/bytes/SHA；source按快照映射，standard/lightweight按该包成员映射，实际路径必须在被选输入根内。缺任一模块、从工作区偷加载或跨variant均拒绝。
- FAIL报告不得满足成功准入；允许非零、失败或未知终态，但须如实保留其原始命令/日志/已有结果，缺项明确null。失败输入可与最终候选不同，不能改写为最终提交；它只进入失败原件列表，不产生覆盖继承。

### 批准的必要测试集合（父审项目）

不冻结本轮49/其它数量；冻结的是下面三种职责和明确完整文件/入口集合，并核同提交真实collection/终态：

1. `source-policy`：完整 `scripts/tests/test_incremental_chain_policy_admission.py`，覆盖年龄/点数/非法字段/未来时间/计划摘要/确认后过期及实际首采集边界。
2. `source-regression`：完整 `test_automatic_incremental_plan.py`、`test_automatic_incremental_resilience.py`、`test_automatic_incremental_async_closure.py`、`test_repository_root_identity.py`、`test_repository_operator_cancel.py`、`test_backup_variants.py`；目录均为scripts/tests。父可在设计审查时确定最终必要集合，冻结后由profile代码精确核验，不能由报告自行删减。
3. `actual-package-policy` 各运行 standard/lightweight：从已冻结实际tgz加载三个模块，复用已审链策略全部边界及正式构造/publish到首采集前测试。不得由现有actual_packages fixture重新构建另一个未绑定包；须新增明确选择实际冻结tgz的执行载体并记录真实loaded module SHA。该载体只替换包来源/本机传输协议，不能伪造ctx/source成功或改业务断言。

当前现有 `test_incremental_chain_policy_admission.py` 的 actual_packages 会重建包，子进程只输出 result/events；单独这份通过不能证明父最终tgz已经实测。因此需一个新增TASK辅助测试载体 `test_main_program_chain_policy_actual_packages.py` 和实际运行器 `run_main_program_chain_policy_verification.py`，由父审其有限输入/输出后实现。验证器只消费它们的原始证据，不自行派发运行或从报告布尔值推定成功。

实际包测试既要证明repository_records/minimal入口，也要证明incremental_plan实际加载并执行共享策略；不能仅import第三模块填SHA而没有其行为用例。所有产品/测试/运行器均必须来自同一已提交候选输入；如果运行器位于TASK，也必须是该提交中已登记输入。

## BDD / RED 范围

- 旧v2 delta/v1 coverage原件正例及原负例逐项保持，无新增字段要求；改旧模块常量或旧测试计数不能作为新实现。
- 新真实临时两代standard147/lightweight146 tar，通过逐成员SHA/compile、精确三模块语义变化与完整分区；增加模块/遗漏成员/重复member/链接/非法路径/编译失败/改manifest均拒绝。
- 错profile/schema、错commit/build/generation、错误baseline45 rich coverage链、四rich不一致、把初代461当45当前证明均拒绝。
- source snapshot缺真实输入、包与源码模式混淆、loadedModule路径外逃、错variant SHA、测试运行中输入改变均拒绝。
- 非零/超时/缺终态、0 tests、任意skip/fail/error、未批准测试集合、collection与逐节点/JUnit不一致、原日志/命令/exit pin漂移均拒绝。
- failedEvidencePins为空可合法；实际失败存在时仅保留为失败，不需制造安装失败，不得计入通过。
- planner完整重建、activation prepare、stager材料绑定、generation历史读取均通过既有相同返回shape；纯准备无远端/输出副作用。

首轮仅新增合同测试和真实小型临时材料，不用手写PASS替代运行证据；最少一个正例由真实本机pytest子进程产生collection/JUnit/终态/日志，并保留一个真实非零反例。实际完整产品双包验证由父在提交后的专用发布worktree运行，不能把缩小协议fixture称生产验证。

## 待父确认后方可实现

确认新schema/profile/两处分派、上述必要测试集合及新增actual-package载体/运行器范围。设计通过后才写新增RED测试；本轮仅设计，没有修改产品、执行器或已有原件。
