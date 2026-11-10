# Spug 资源转换 TDD

## Current Status

历史 reader 接缝修复 ready_for_closeout。新增9项通过，联合回归104项通过+2项旧协议载体失败，精确修正载体后两项均通过，全部零skip；父正式v3 prepare亦已通过。源helper冻结b483f0d、B仍b4619e，等待父独立验证/限定提交。实际安装成功不重派，本组件没有业务写入或重跑安装。

## 嵌套 B / 显式历史 reader 托管（本轮先行 BDD）

只读诊断：实际 attempt 1141 项，nested B prepare expected 1142 项；唯一 expectedOnly 为失败 v2 输入 550B/9d37b3df8136924571c4d24afcaf77d9eaf86d4e8615c03f7684ffbdfed2b5bb，无 actualOnly/changed。共享 Records 的 B v1 baseline.inputPins 夹带外层 v2，原安装原件无缺失。

正式入口：原 B 五字段不改，resourceTransitionPin 明确支持 direct Transition/v1 或 ReaderCustody/v1。custody 仅六字段 schemaVersion/transitionCorePin/attemptPin/originalReaderPin/preservedReaderPin/currentReaderPin，只包原 direct core；core/attempt/原 helper 唯一路径 pin/显式 PRIVATE 原 raw/当前实际 reader 全核。旧 direct core 在 reader 变更后拒绝；无 wrapper 自动发现。父后续生成新 verificationId v3 输入，失败 v2 保持。本轮不生成实际安装或新 B 元数据。

BDD-1：Given 已完成正式转换原件与实际 nested B prepare_value 入口，When 外层输入已读入 Records，Then 不污染原安装 exact expected 集合，外层及 custody 留在新验收闭包。

BDD-2：Given 安装源 pin 已过时，When 读取 direct core，Then 显式 READER_CUSTODY_REQUIRED；Given 精确 typed custody，Then 完整原件逐项读回成功。

BDD-3：Given 错 core/attempt/原路径/原 pin/保全字节/current pin、额外字段或递归 wrapper，When 读取，Then 拒绝，禁止通用源 pin 替换。

先保全原 helper 29106B/dc3d9f01bc3e52204d6801683d3d05033c57afec7a3f89427091c8b0a7357a0b，再写失败测试；RED/GREEN/回归原日志将在实际终态后附记。测试使用真实 Records/私有原件/子进程，协议 seam 不称真实业务安装。

本轮保全实际 exit0：PRIVATE/spug-resource-transition-reader-dc3d9f01bc3e52204d6801683d3d05033c57afec7a3f89427091c8b0a7357a0b.py，排他 xb 写入/fsync 后完整原字节读回相等。没有修改真实 attempt/core/gate/native/observer、失败 v2 输入、build/proof 或 B 源码。

RED：`python -X utf8 -B -m pytest TASK/test_main_program_spug_resource_transition.py -q --tb=short -k "actual_nested_b_scope or reader_custody"`，原 session65136 实际 exit1、9 FAIL / 26 deselected / 0 skip、15.97秒；真实 nested B 的 scope 场景精确 ATTEMPT_INPUT_SET_CHANGED，新的 wrapper 不被旧模块接受，7种负例缺相应正式 custody 拒绝。原日志 spug-resource-transition-reader-red-r1.log。

第一最小实现后 GREEN-r1 原 session20753 实际 exit1、8 PASS / 1 FAIL / 26 deselected / 0 skip、19.87秒。新增严格 base authority 比较暴露第二个同源污染：只读逐字段差异仅 spec.inputPins[0].path/bytes/sha256。它是 Records 派生 provenance，而非 runtime spec/配置变化。保留原失败日志 spug-resource-transition-reader-green-r1.log。

正式处理：独立 Records 从原 transition inputs 读取完整 B v1，作为安装 expected 输入集合唯一 authority；传入 B baseline 的物理 pins 仍全部验证，其 spec 除派生 inputPins provenance 以外字段和 A core 与 canonical 全等。原 native 程序、argv、timeout、退出/输出、完整原件仍逐项严格重建比较。wrapper 仅将 expected 中当前 helper 这一条替为原 attempt 已固定 pin，再用显式 PRIVATE raw 验原字节；新 wrapper/consumer 输入/current reader 只进入新验收闭包，不混入原 attempt。

GREEN-r2：原 session33700 实际 exit0、9 PASS / 26 deselected / 0 skip、26.60秒；原日志 spug-resource-transition-reader-green-r2.log。成功场景使用真实已完成转换与真实 B.prepare_verification 嵌套入口，全量原件读取；只新增独占临时 consumer JSON 并 finally 删除，未人工构造安装成功。源码变化后 direct 原 core 明确 READER_CUSTODY_REQUIRED。所有新 wrapper 六字段及 core/attempt/原 pin/保全 raw/current pin、单层限制均验证。

生产/测试当前冻结：helper 32123B/b483f0db726992ee10764046d4a594418b77feb05c63fc96aaf9624a7a43dd11；test 27170B/cca0b9f6f6255caaca0de2d3910ea2949bce0344a39838a7530d6108dcfdd7cb；B 33479B/b4619ef30c12dc7754256b87b753fc0932f1007e8925ca2a1df0cfe047229ebe 保持。联合受影响回归原 session11541 运行中；不把旧96项与当前新SHA混记。父后续创建正式 wrapper/v3并独立实际完整prepare，本组件未创建真实新验收输入或派发 gate。

ready_for_closeout（父96项已验收，实际Windows日志接缝已精准RED/GREEN，等待父161输入reader复核及限定提交）。本阶段仅本机实现/测试，不生成实际候选 build，不安装、不访问 Docker/服务器、不提交。整个自动增量/三服恢复任务仍由父继续。

## 接口与边界

新增 `main_program_spug_resource_transition.py`。入口 `prepare_transition(task, private, inputs_file)` 默认只读；`observe_transition` 显式只读运行观测；`execute_transition` 显式唯一安装；`load_completed_transition` 严格历史读取。输入 MainProgramSpugResourceTransitionInputs/v1：baseVerificationInputsPin、resourceBuildPin、deploymentDeltaPin、observationPin、operationId、outputFile。基线必须是正式 B v1，仅使用其已验证 A/c1 历史。候选 MainProgramSpugResourceBuild/v2 包含完整14文件/依赖图、实际已提交 commit/干净 checkout、测试证明和精确源码 custody；安装读取当前 checkout，历史只从明确 custody 读取原字节。

精确差异按完整前后集合计算，不固定变化文件数。所有变化原件在首次替换前完整保全，逐项混合状态、原配置/环境/历史守卫，最后唯一 entry 重载。失败保留原件与 gate，禁止自动重试。B v2 额外引用 resourceTransitionPin；原 c1/A 对象不可改写，两个产品投影和14文件运行视图均取已证明新状态。

## BDD

- Given 完整14依赖候选及正式前代，When 核差异，Then 接受任意合法非空精确差异，空/遗漏/额外/伪变化拒绝。
- Given 真实临时 Git 提交、checkout 字节与源 custody，When build 准入或历史读取，Then commit/clean/blob/图/测试原件全部吻合；漂移拒绝。
- Given 多文件变化，When 本地真实文件替换，Then 首次替换前全部原件已有；每步只接受证明的混合状态；中途失败保留实际状态并禁止重试。
- Given 缺进程/环境/配置/原件或伪运行结果，When 完整守卫或历史验收，Then 拒绝，不能凭一个 PASS 字段通过。
- Given 新转换证明，When B v2 派生视图，Then 新14 pins、新entry及两个11产品投影一致，旧历史不变，原六阶段及 HOST 验证不变。

## 经验门禁与设计约束

Trigger：selection 查询产品修复后的资源安装；Preflight check：正式前代、完整依赖、干净已提交候选、原件/配置/进程；Blocker：缺原件、漂移、未结束调用或不完整集合；Verification：真实 RED/GREEN/旧 B 回归及父独立验收；Forbidden action：修改旧 helper/custody、访问真实服务器、重发配置、冒称协议单元为实际安装；Evidence：本日志及真实命令输出。

是否引入 fallback/降级/吞异常：否。是否从根因和长期维护角度解决：是。是否存在临时补丁或绕过：否。

## 验证记录

RED：`python -X utf8 -B -m pytest TASK/test_main_program_spug_resource_transition.py -q --tb=short`，原 session60730，实际 exit1，22 FAIL / 0 skip，79.54秒；均为缺正式模块 ModuleNotFoundError，临时 Git/文件与真实A/c1前置 fixture 已运行。测试中的临时 Git/文件/子进程为实际本地操作；容器协议载体只验证调度/证据合同，不代表真实业务安装。

追加 BDD：Given 九组来源/目标查询、单组共享50秒，When v2 spug-verify，Then 截止=组合数×50+120秒，本次570秒；旧v1和两guard仍120秒，HOST/SPUG正文和组合全集不改。

RED：B 新两项实际 exit1，2 FAIL / 30 deselected，9.49秒，分别缺 `apply_transition_view` 与120!=570。首轮联合实际53 PASS / 1 FAIL（78.29秒），唯一失败为子进程缺候选模块 PYTHONPATH，已仅纠正载体路径。

本地整链回归明确复用已完整核过的真实 A/c1 fixture，Docker 调用仅通过 Popen 边界重定向至本地 Python peer：native 请求/程序/退出码/输出、真实保全/替换仍由正式实现产生；peer 只映射测试临时挂载并给出有限 Docker/进程协议，不声称真实服务器或业务安装。初始回归先暴露载体 PRIVATE 根及 mount snapshot 映射未齐；最小明确修正载体后，实际命中 observation/apply native 原件重名，生产已为只读 observation 分配独立 recorder stem，保留两套原件。

追加 BDD：Given 主 checkout，When 新候选准入，Then 不得作为专属发布 worktree；真实 RED 为 DID NOT RAISE，session73377 exit1，1 FAIL / 24 deselected，13.55秒。实现要求候选 `.git` 为正式 linked worktree 文件，测试改为真实临时 Git repository + detached worktree；历史读取不重新要求该 checkout 存在。

本地整链 session89502 实际1 FAIL / 2 PASS，130.11秒；成功协议路径已完成所有替换和新entry验证，最后正式历史自验发现重复 inputPins（ORIGINAL_INPUT_SET_INVALID）。修正为入口局部 Records 防止调用方后续读集合污染，观察原件全部读取后去重；历史按“精确已核集合+原候选源pins”全等核 attempt 输入集合，不减少任何原件验证。另失败协议路径已实际 PASS，退出3原件及唯一 gate 均保留。

GREEN：session92250 实际本地整链2 PASS / 0 skip，103.35秒。session31917 完整联合25转换+32 B（原30+新增2）实际 exit0，57 PASS / 0 skip，229.31秒，原日志 `spug-resource-transition-green-r1.log` 保持。

父审阅追加 BDD：Given 真实候选将已提交测试放于 `ops/spug/test_contract.py`，When 验证 build，Then 测试应与全部原输入同样核 Git/blob/原字节/custody，但不混入14项运行图。先将载体由根目录 contract_test.py 精确移至该路径取得 RED，再只让完整 files 集合中的成员进入 runtime sources；其它输入仍完整逐项验证。

RED：session95052 原终态 exit1，1 FAIL / 24 deselected，32.70秒，精确 `SOURCE_FILE_CHANGED`。生产最小改动仅分类条件 `if name in report['files']`；源原件、已提交 blob、完整 custody/测试证据校验保持。

GREEN：session64213 原终态 exit0，6 PASS / 19 deselected / 0 skip，116.93秒，实际临时 Git linked worktree、构建正反与历史字节读取。原日志 `spug-resource-transition-build-input-green-r1.log`。本次未重跑已通过的57项，不把原57记录冒称最终新SHA下重跑；父将独立新25+B32+旧A39验收，并读实际565/r3候选161输入。

## 正式调用

- `prepare_transition(task, private, inputs_file, allow_unobserved=False)`：只读候选/基线/实际观察准入。
- `observe_transition(private, prepared, transport=None)`：显式只读观测，返回固定私密 observation pin；未绑定观察输入可先用 CLI `--observe`。
- `execute_transition(task, private, prepared, transport=None)`：显式安装，保全全差异、每步混合状态守卫、唯一 entry 重载、成功前历史自验；失败 gate 保持，不重试。
- `load_completed_transition(records, private, reference, base)`：读取完整真实回执，返回 afterFiles、entryAfter、entryEnvironmentSha256、selectionReadBudgetSeconds、inputPins。base 是调用方已经完整验证的正式 B v1 baseline，不是未验证输入字典。
- B v2 输入字段精确为 schemaVersion/baseVerificationInputsPin/resourceTransitionPin/verificationId/outputFile；旧 v1 路径不变。`prepare_transition_verification` 消费已完整读出的 baseline 与实际转换闭包；HOST/原SPUG正文及六阶段顺序保持。

候选 build v2字段：schemaVersion/status/sourceCommit/worktree/fileCount/files/dependencyGraph/testEvidencePin/sourceCustodyPin/selectionReadBudgetSeconds。proof v2仍独立记录原 actualPassed/exit/skipped/inputPins/log；不把 Node 与 pytest 输出伪装成一个原 pytest 计数。source custody 精确 entries(relativePath/originalPin/preservedPin)，覆盖 proof 全部已提交输入。预算直接从候选 adapter 的 module-level `SELECTION_TOTAL_SECONDS` 字面 int 核验；当前产品50，B仅v2 spug-verify为3×3×50+120=570秒。

最终四源码/测试编译及raw SHA另由本轮工具输出交父；仅本专属文档和两个实际GREEN日志为附加交付。未写源码custody扩权、旧helpers、配置、实际build、安装或selection；未访问真实Docker/服务器，未提交。

## 实际 Windows 日志接缝

父独立原 session72870：96 PASS / 0 skip，exit0，263.156秒，源码冻结保持，原报告 spug-resource-transition-parent-regression-r1.json 保留。实际161输入 reader-r1 在最后日志校验拒绝：原 pytest 输出为CRLF，现正则行尾不能越过CR。不得修改原日志或proof来通过。

BDD：Given 原字节LF或CRLF的实际pytest成功摘要，When 读取正式build日志，Then 两者均按同一计数接受；Given 同样原字节含 failed/skipped/error，Then 即使附加成功摘要也拒绝，不放宽原结果。先仅把测试 protocol.log 改真实CRLF取得RED；生产只添加行尾可选CR，不重写输入字节，不重跑已通过的96项。

RED：原 session73931 exit1，1 FAIL / 24 deselected，35.55秒；真实临时 linked worktree 及原件全部核验后精确 `TEST_LOG_NOT_PASSED`，原件 `spug-resource-transition-crlf-red-r1.log`。

最小实现：仅将成功摘要正则尾部 `[^\r\n]*$` 改为 `[^\r\n]*\r?$`，原失败/跳过/错误拒绝表达式不变。新增一项正式历史reader测试遍历 LF/CRLF × 成功/failed/skipped/error，重pin真实日志/proof原件以命中解析而不是字节漂移，并逐次确认原日志字节未改；此前准入正例保留实际Git/干净checkout门禁。

GREEN：原 session72968 exit0，2 PASS / 24 deselected / 0 skip，74.33秒，原件 `spug-resource-transition-crlf-green-r1.log`。未重跑旧96项，也不把旧96的冻结SHA改记为本次SHA。只读核实际565/r3原日志摘要字节确为 `114 passed in 46.62s\r\n`，新表达式匹配114；未改实际日志/proof/report，完整161输入reader仍由父复核。新helper/test/TDD冻结，B及旧helpers保持。

父实际最终接入：原session97601实际exit0，正式validate_build读取已提交565/r3全部161输入、Git blob、完整14依赖、实际原日志和保全字节；324 pins，26.172秒，最终helper29106B/dc3d9f01bc3e52204d6801683d3d05033c57afec7a3f89427091c8b0a7357a0b与B33479B/b4619ef30c12dc7754256b87b753fc0932f1007e8925ca2a1df0cfe047229ebe前后保持。报告spug-resource-build-5651efc-parent-reader-r2.json；原reader-r1失败保持。实现必要验证已通过，准备精确提交与实际只读观察；尚未安装或执行B现场验收。

联合回归原 session11541 实际 exit1，104 PASS / 2 FAIL / 0 skip，257.66秒，原日志 spug-resource-transition-reader-regression-r1.log 保留。仅两个旧本地 native 协议用例的正式 PRIVATE 路径不满足：原 A/c1 私密原件仍在真实 PRIVATE，新 transition 用 temp/private；canonical 新增真实历史实读正确报 MAIN_SPUG_PRIVATE_PATH_CHANGED。产品不放宽 private 范围，不改变该严格门禁。已向父提出仅测试 seam 显式调用原真实 B reader、将旧历史读取绑定其真实 PRIVATE，新安装/协议文件仍用临时目录，等待确认；未改业务断言。

父批准仅这两旧协议用例的真实scope适配。精确复跑r2实际 exit1、2 FAIL / 33 deselected、17.41秒：将private绑定原根后，更深的旧activation原attempt仍固定实际TASK路径，载体复制到temp/task不能冒充该物理路径。r3实际 exit1、2 FAIL / 33 deselected、31.90秒：TASK/PRIVATE成对绑定后，fixture全局RUNTIME投影仍与旧实际bind定义不同。两轮原日志 spug-resource-transition-reader-protocol-regression-r2.log/r3.log 保持。

最终只修这两个协议测试的明确scope seam：新建原TASK的真实Records并逐pin读取同一B v1原输入，原真实B.prepare_value在原PRIVATE和临时恢复原RUNTIME的context中完整实读；返回原真实reader结果，不返回预存/合成成功、不跳过任一历史门禁。新transition的安装原件/native/替换仍处于temp/task+private，原全部成功/失败业务断言不改；生产helper和B始终未再变化。

REGRESSION-r4：原 session6234 实际 exit0、2 PASS / 33 deselected / 0 skip、92.50秒，原日志 spug-resource-transition-reader-protocol-regression-r4.log。与联合原104 PASS组合覆盖35转换+32B+39A共106项；这是分轮证据，绝不声称最终一次106全通过。没有再重跑原104项。

父实际接入：独占正式 wrapper main-program-spug-resource-transition-reader-custody-5651efc-r1.json、原五字段新verificationId v3输入；原 session95173 实际完整prepare exit0、14.281秒、1079物理pins，两11产品投影/14runtime/entry152321/570秒预算全等。原attempt、失败v2和B源保持。该正式metadata由父生成，本组件只负责本机helper/测试，不派发B gate、不重装、不观察或操作服务器。

最终正式读取入口仍为load_completed_transition(records,private,reference,base)：reference只能是direct Transition/v1或明确的ReaderCustody/v1；wrapper精确六字段、单层directcore、attempt/原helper逻辑pin/保全raw/当前实际reader全绑。原安装expected严格全等；新consumer/custody/current reader是新的B验收闭包。原逻辑源pin保留于wrapper和原attempt，当前同路径physical pin只表示当前reader，旧raw由PRIVATE保全pin承接，无同路径双pin冲突或无约束fallback。
