# 控制代次独占暂存 BDD/TDD

## Current Status

implementation / complete_runtime_path_ready_for_parent_validation。完整暂存入口已接共享 RuntimeGates、原物理锁、原/新候选、epoch 与来源10秒准入、完整历史/分层 custody、业务/NAS/fstab 保全及独占文件层；本地最终回归结果见末节。以下早期文件层记录保留其当时状态，不代表当前完整接线仍缺API。最终8项Linux字节快照与真实899/45/r5默认prepare交父任务独立验证；本子任务未调用Docker/服务器、构建、提交或生成实际r5 stage原件。

## 目标、里程碑与预期验证

1. 冻结输入、147 包闭包、每 host 的新文档与保留文档、宿主身份及阶段结果合同。
2. RED：真实本地 tar/配置文件与旧门禁 API，证明精确代次/新旧分区/路径/重复/别名/部分失败拒绝。
3. GREEN：纯 prepare 复用 generation/planner/coverage；独占文件原语按真实 Linux 目录可验证，不用字符串替换或 exec 旧模板。
4. 回归旧 staging 判定；冻结实际受测 SHA 与未覆盖现场条件。完整生产门禁未接齐时明确 fail-fast，不产生 STAGED_NOT_ACTIVATED 成功报告。

本阶段可交付的结论为“纯准备和文件暂存合同通过”，不是控制部署完成。现场部署需要当前进程、无 worker、物理锁、epoch、完整历史和分层 custody、业务容器、NAS/fstab、实际新包构造及逐来源 factory 保护；历史观察不能替代同次锁内实时检查。当前这些完整运行门禁仍在旧 private SCRIPT / activation REMOTE_SCRIPT，不能靠删掉门禁实现“可运行”。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。包、原件、目录、锁内门禁不齐直接拒绝；不忽略保留配置，不自动清理部分写入或重试。
- 是否从根因和长期维护角度解决：是。显式版本/commit/revision/host及不可变材料，重用正式纯验证 API；文件暂存与现场激活证据分开，不重放旧模板。
- 是否存在临时补丁或绕过：否。生产入口缺实时门禁必须停在只读准备；临时目录测试结果不能生成现场成功回执。

## 经验门禁

- Trigger：已安装控制代次升级，需要新 engine/config 暂存而保留全部 r4 与失败历史。
- Preflight check：精确干净提交构建和两代实际包/覆盖原件；generation 与 v2 plan 精确重建；当前 host 身份；8新/27保留及35闭包；新 engine 唯一路径，全部147成员 SHA/安全路径；原业务、NAS/fstab、epoch、worker及完整history/custody实际可验证。
- Blocker：缺任一材料、包闭包/路径冲突、重复写入、符号/硬链接、旧配置漂移、活动worker、无法取得原物理锁或无可审查现场验证 API。缺现场条件只阻止对应派发，不能伪造过去成功。
- Verification：先真实 RED，再本地真实 tar/文件/变动拒绝 GREEN；旧 validate_staging 与新 validate_generation_staging 回归。0400、O_NOFOLLOW、父目录 fsync、链接/真实 Linux 锁由独立 Linux 临时目录测试证明，Windows 不冒充 Linux 验收。
- Forbidden action：不改旧engine/r4/失败原件，不覆盖/删除/盲续办，不执行旧 replace+exec 脚本，不重载服务/重启Docker，不省略27份保留文件或全历史，不把本机输入pin当现场保全证明。
- Evidence：上位两计划、docs/experience-index.md 路由命中的 release-agent-checklist.md“自动增量链与恢复周期门禁”“历史来源归档与叠层挂载保护门禁”“多机器发布接管与缺失记录分析门禁”“授权控制升级的活动回执历史保全”；本日志真实测试原件。

阶段必查：纯prepare前只读核全部本机pin与输入闭包；文件写入前一次核所有新路径不存在和全部保留原件；写入采用O_EXCL、0400、fsync及精确读回；失败保存已创建路径，不自动删除或重跑。生产派发必须另有同次物理锁/现场门禁与实际构造证明，缺项零派发、零运行资源写入。必须记录精确commit/revision/host、包及新/保留集合、输入SHA、真实失败与残留状态，报告只声明实际完成阶段。

## BDD

1. Given 明确已核 generation、新 v2 public/private plan、实际147包与覆盖，When 纯prepare，Then重建同一计划并绑定host/commit/revision/旧控制身份；零写入、零transport，不生成真实r5原件。
2. Given 缺输入或任一pin/commit/host/revision/物理来源发生变化，When prepare，Then在任何写入前明确拒绝。
3. Given 新代仅8份新配置且27份原配置保留，When本机真实临时目录暂存，Then每host只创建4/2/2份新文档、9份保留只核不写，35闭包不减少。
4. Given 真实147成员标准tar，When校验和写入新engine，Then安全路径、唯一成员、每成员SHA、manifest与包SHA及Python编译一致，独占新目录并精确读回package.json+147成员。
5. Given 重复目的地、额外tar成员、重复名、路径穿越、链接/特殊文件或旧文件漂移，When准备写入，Then拒绝且不覆盖旧文件；预检发现的任何问题须零新写。
6. Given 写入中存储失败，When暂存中止，Then保留原失败与已写文件，不删除新目录、不覆盖重试、不产完整成功回执。
7. Given 旧业务/控制/epoch/history/custody或新包factory现场门禁尚未具备，When生产remote入口，Then明确fail-fast；文件合同成功不能冒充validate_generation_staging所需完整现场报告。
8. Given 完整现场报告由后续真实门禁产生，When交给既有validate_generation_staging，Then保持engine逐控制147/manifest/编译及config新保留分区、原物理锁与三来源factory门禁；缺任一不能放行。

## 固定 API 与边界

- generation.load_control_generation 负责真实前代与分层custody；planner.validate_control_upgrade_plan 精确重建新public/private；activation.validate_generation_coverage 负责实际两代包/旧完整覆盖/新delta。
- 输入显式固定sourceCommit/revisionId/suffix/previousControlGenerationPin/buildPin/planPin/coveragePin和当前unit/environment观察pins，不从“最新”文件猜测，不接受自定义host或远程路径覆盖。
- 文件层只提供显式已验证spec的真实目录操作，不提供服务器连接；生产remote入口在完整现场门禁未接齐时无条件拒绝，不能把调用方给出的布尔PASS当门禁证明。
- 预期完整阶段报告沿用 activation.validate_generation_staging 的名字与字段：main-program-engine-staged-<suffix>-<short>-<revision>.json / main-program-configuration-staged-<suffix>-<short>-<revision>.json。当前不实际生成这两种现场成功原件。

## RED / GREEN / REGRESSION

- RED（最初模块尚无）：PRIVATE/control-staging-red-r1.log，exit2，1184B，SHA256 `29d654495d3537eb5a4500c765a6ef1d93210b924a272519a5bb024eb887a261`；实际失败为待新增模块缺失。
- 首轮文件预检：PRIVATE/control-staging-green-r1.log，18 PASS / 1 FAIL / 5 deselected；1996B，SHA256 `a1159dd50f88c5c9f1a4a1b2504740eed5b10b4cac5625976b051eb7d6bff70b`。Windows路径stat与句柄fstat的ctime表达不同；改为相同API前后比较，同时保留FD和路径dev/inode绑定，未取消任一完整性检查。
- GREEN：PRIVATE/control-staging-green-r2.log，19 PASS / 5 deselected，115B，SHA256 `15eafaccc0d13d8fe8f545b321adef8f65754a2c864c4ff5f23eb71ebf4fcff7`。
- RED（纯prepare未实现）：PRIVATE/control-staging-prepare-red-r1.log，8 FAIL / 24 deselected，11422B，SHA256 `dd67a5001911f80aa641850a7ed3972da01625cfafa84fbd669c9cd7a86a93b0`。真实覆盖、两个实际tar和旧原件fixture先成功读取；8项均因待实现prepare_materials缺失失败。
- 环境/fixture失败保留：PRIVATE/control-staging-prepare-green-r1.log，8 setup ERROR，4189B，SHA256 `5fad745b4eb2c379b5a6af09dadea9eb0eb1c6b0b06b86530e3b99a79a8fed8e`。旧planner纯fixture只有最小controller集合；按真实activation core补齐generation.SELECTION_CONTROLLER_KEYS（包括role/sourceCommit等），不改正式合同、不放宽断言。
- GREEN：PRIVATE/control-staging-prepare-green-r2.log，8 PASS / 24 deselected，115B，SHA256 `175389cc71a9e09e1aaca06b48b221c9f07ecdbdc90578eb0efc273354a7b990`。
- 完整Records入口：PRIVATE/control-staging-record-green-r1.log，57/58/59三项PASS，116B，SHA256 `0674c797e613c2eecbf38366b9cb8775c2f6bdc14d04189e60a2c412126929b2`。复用真实两代tar、覆盖原件、planner；generation及当前宿主观察是明示临时文件协议边界，不能宣称真实部署或实时准入。全部临时原件逐字节不变，stage零transport。
- REGRESSION：`python -X utf8 -B -m pytest -q --tb=short test_main_program_control_staging.py test_main_program_control_generation_activation.py -k "not linux and (not v4 or staging)"`，42 PASS / 52 deselected，41.61s，无skip。PRIVATE/control-staging-regression-r1.log，117B，SHA256 `43c9f4985c87654fca87aed0f8860c62864439783180354a212d430211da4172`。这是新30项与旧v4 staging12项；其余未选择的场景没有被宣称重新验收。

所有日志均独占写入任务PRIVATE，未覆盖失败原件。编译采用compile(bytes, filename, 'exec')，不生成pyc。测试包安全负例保持148个tar成员，使路径穿越/符号链接命中对应安全拒绝，不能只因成员数错误假通过。

## 早期阶段冻结与 Linux 验证入口（历史快照）

- main_program_control_staging.py：24049B，SHA256 `235115462117f90772ab72e18d86b5b7f293205bd4ee64e31b39652e81d43476`。
- test_main_program_control_staging.py：16451B，SHA256 `a9aba4deb5c1ff74ea472d77b144fe0ee9f4688985304f36b18b4b9981192dc5`。
- 入口：`python -B -m pytest -q --tb=short <TASK>/test_main_program_control_staging.py -k linux`，预期5项：真实临时目录独占/0400/读回/保留文件inode与mtime/ctime，三种真实别名拒绝，真实文件写入边界ENOSPC失败残留和重复拒绝。
- 最小同目录源码9份：以上2份，加main_program_control_activation.py、main_program_control_generation.py、main_program_control_upgrade_plan.py、main_program_installation_selection.py、installation_history_custody.py、common.py、test_main_program_control_upgrade_plan.py。只需pytest依赖；选择Linux5项时不运行旧实际业务原件fixture，也不需要真实服务器材料。
- 父任务负责单一pin tar、原生tmpfs、network none、只读rootfs与精确原始日志；本子任务不启动Docker。Linux结果未到前不宣称完整文件暂存验证通过。

### Linux 实际结果

父任务已实际完成原生Linux5项：PASS / 0 skip / exit0，固定上述235115.../a9aba...源码快照。TASK/control-staging-linux-r2.json及log保留；log222B，SHA256 `601b66153c4f4cacceee897e32114646174c12523c2d2d1eb1a1e121b8c6f515`。network none、只读rootfs/bind、原生tmpfs；容器已删除，全部输入原件保持。r1载体缺pytest的py.py shim尚未收集测试，其FAIL原件和依赖预检失败原件均保留，不算业务RED。后续门禁接线改动不自动继承此字节级验收，需要最终源码重验。

## 早期下一阶段输入与当时尚缺门禁（保留历史记录）

父任务已另行生成真实899代次索引和45/r5纯计划。本入口固定MainProgramControlStagingInputs/v1十字段：schemaVersion、sourceCommit、revisionId、suffix、previousControlGenerationPin、buildPin、planPin、coveragePin、unitObservationPin、originalEnvironmentObservationPin。sourceCommit固定本次已核45dd7dc65409c87fe856584b85873ea96c0b830e，revisionId=r5，suffix逐台57/58/59；不猜“最新”文件。

已提供真实原件：main-program-control-generation-899730d-r1.json（2526B，SHA256 `9ca1cc30ddabc0594a8066f90a7d0f7ca0300d1a972eea196cbc6ac66a9d43f9`）和main-program-configuration-plan-45dd7dc-r5.json（14714B，SHA256 `201b897582afdfc9ee41f3b9f29e9178236cde81b4a78e670c92836c7cbde009`）。实际构建与覆盖直接用release-build-45dd7dc.json和main-program-control-coverage-45dd7dc-r1.json的真实pin；不伪造新的构建或覆盖证明。

每台仍需明确的新观察：main-program-control-units-<suffix>-45dd7dc-r5.json及PRIVATE同名.private.json；main-program-control-environment-baseline-<suffix>-45dd7dc-r5.json及PRIVATE同名.private.json。沿用既有MainControlUnitObservation/v1、MainControlEnvironmentBaseline/v1，补sourceCommit（unit）、revisionId、previousControlGenerationPin；private投影、进程身份、unit/dropin、环境SHA均走冻结activation API。三个host的controller完整集合取真实generation.SELECTION_CONTROLLER_KEYS；保留原role，不从当前端口或历史自动安装猜测。

纯prepare只读这些原件并末尾复核所有输入pin。native文件函数仅生成FILES_STAGED_RUNTIME_UNVERIFIED/activationReportEligible=false，不生成完整STAGED_NOT_ACTIVATED回执。生产入口现明确MAIN_STAGING_RUNTIME_GATES_REQUIRED，未调用transport。下一阶段继续从旧staging/activation提取可调用实时门禁，保留当前进程/环境、无worker、物理锁、epoch和FULL/I1/I2基线、原业务与NAS/fstab、全部历史和分层custody、实际新包构造与逐来源factory、写后全部保全核验；该缺口不能作为最终交付留存。

## 第二阶段 BDD 与固定设计

父任务批准固定两正式模块+固定bootstrap内存载入：stager和新RuntimeGates逐源码pin校验，不落远端helper、不污染147产品成员；不动态替换旧r4脚本、不执行历史private模板。纯prepare相关依赖改函数内导入，原生文件层只用stdlib。既有environment/custody、CANDIDATE_GATE和SOURCE_IDLE作为固定正式原件绑定，完整helper pin末尾再核。实际Unit/environment观察由独立owner提供新鲜绑定材料，不把本机协议fixture当现场观察。

- BDD: Given 原生执行环境只有stdlib和两个精确模块，When 导入文件原语并准备固定payload，Then无本机任务依赖、无导入时I/O、无远端临时文件；任一模块pin变化先拒绝。
- BDD: Given 原进程/配置/单位/环境、全历史、分层custody、物理锁或来源周期变化，When 暂存前检查，Then零新文件；锁必须是原目标replacement锁，57来源/目标epoch必须同物理范围。
- BDD: Given 全部门禁通过且新engine与新文档不存在，When 同一物理锁内执行暂存，Then真实独占写入与保留只读；随后逐控制实际新包构造、三来源archive factory和source capture/epoch前后相等，所有保护状态不变，才生成完整stage报告。
- BDD: Given 写入后任何门禁失败，When 收尾，Then保留全部已写engine/新配置与失败日志，不发布成功原件、不重启/切换控制、不自动回滚或重试。
- BDD: Given 来源计划查询超时或旧目录超出既有10秒准入，When 现场/升级后验收，Then明确失败，不扩大HTTP期限或把本次完整history审计预算当产品目录预算。


## 完整运行门禁接线与终态边界

- BDD: Given 最后一次候选构造仍可能改变受保护原件，When final candidate返回，Then必须在其后再执行完整RuntimeGates.preserve及锁身份检查，才可投影成功报告。真实临时文件变更测试先出现DID NOT RAISE，再最小调整顺序通过；不是只检查源码字符串。
- 共享正式模块main_program_control_runtime.py使用已冻结父独立85 PASS的实际API；before/preserve保持当前进程、原unit/dropin物理集合、环境、无worker、容器定义和状态、NAS/fstab、全历史、分层custody和完整旧包成员。所有阶段首尾验证同一原物理锁FD，禁止新建锁或替换路径。
- 持锁顺序：before全门禁 → 原候选实际构造/epoch/来源计划 → 写前完整preserve → 独占新engine/config → 新候选实际构造 → 最后候选再核 → 写后完整preserve → 锁身份 → 释放同一FD → 报告投影。每target核三来源factory保护，每source核实际capture、READY epoch和原FULL/I1/I2基线；完整来源HTTP总预算保持10秒，没有重试/redirect/更长产品期限。
- 两正式模块和四段已有正式程序均按精确源码SHA绑定，以固定bootstrap内存加载。没有远端helper落盘，不改147成员，不动态改写旧private模板。prepare依赖仅在函数内导入，原生import为stdlib且无I/O。
- 引擎与配置仍O_EXCL/0400/fsync/精确读回；147成员和元数据闭包、旧配置只读、容量、别名/路径、部分写入保留不减弱。文件层状态仍FILES_STAGED_RUNTIME_UNVERIFIED；只有实际完整门禁和释放锁后才可投影STAGED_NOT_ACTIVATED。
- 本地先独占ATTEMPT_RESERVED，再唯一transport；保存原stdout/stderr、超时/实际exit、远端失败与已创建路径，不自动回滚/删除/重派。成功还须通过原activation.validate_generation_staging及全部本地输入/执行源码pin末尾复核，再独占写两份公共报告。

## 第二阶段实际 TDD 原件

全部日志在任务PRIVATE，以下只列名称、字节数与摘要，不提交私密原文。环境/fixture缺失与真正行为RED分别记录；只有实际PASS才计GREEN。

| 日志 | 实际结果末行 | 字节 | SHA256 |
| --- | --- | ---: | --- |
| control-staging-native-import-red-r1.log | 1 failed, 35 deselected in 0.45s | 1663 | `3bf520dbc3510b17a9759612cf486aea74b8bcccbc169f698d2bd75ebc753ff8` |
| control-staging-native-import-green-r1.log | 19 passed, 17 deselected in 1.50s | 116 | `08aa69c8ca01a36c0cdc2f58009b33f2b1a6fab9cb14c2b4f8384c91447ff82a` |
| control-staging-runtime-binding-red-r1.log | 4 failed, 36 deselected in 6.51s | 2733 | `577e3453b785750623db8c3f7619c483dd2c260d01c0b292aae2e941e9df5ec1` |
| control-staging-runtime-binding-green-r1.log | 4 passed, 36 deselected in 5.32s | 115 | `24355de5a0ef786c3725ceda71926edf27690a9519415ced38821396bff86fb3` |
| control-staging-physical-scope-red-r1.log | 42 deselected, 2 errors in 0.40s | 1337 | `d9ddca65fe8778adb4eb99182dbbe28f726396a999aecc6db1f48939b1af21a6` |
| control-staging-physical-scope-red-r2.log | 2 failed, 42 deselected in 0.40s | 1493 | `d4ed8dd72a91e4439b4399343566e133944a9ee3ad3f6c28c89c2fbf4f31acee` |
| control-staging-physical-scope-green-r1.log | 2 passed, 42 deselected in 0.42s | 115 | `9d7900036993dfcee25dea76664ba0485e63eae3bdebaa37a574d43c57ab43a6` |
| control-staging-candidate-projection-red-r1.log | 3 failed, 43 deselected in 18.08s | 2852 | `f9a9716f16fa1e217c77ed9aeeaf1e29e5c3948f3f0dede0d69f9dc2733ebc50` |
| control-staging-candidate-projection-green-r1.log | 4 passed, 42 deselected in 13.96s | 116 | `9fd3153414d0f172dd4cb47b3dd2f081a7a4f8d9151de42ee90fee731d2bb49f` |
| control-staging-http-red-r1.log | 2 failed, 46 deselected in 0.41s | 1546 | `1c9c1ed3d72bdc778665e66b03a1e2e2e0275cf0281e3dd993bcc66d20dd76c8` |
| control-staging-http-green-r1.log | 2 passed, 46 deselected in 1.20s | 115 | `6ecda31e467957dc9b526413db850addb66b3f2fe5bd5afbbd5a272d515b4cad` |
| control-staging-prewrite-preservation-red-r1.log | 1 failed, 48 deselected in 0.41s | 1137 | `6e51a98d0c749184e747677bc61498b276e9b5f1e911e8a87d260073ac66880e` |
| control-staging-prewrite-preservation-green-r1.log | 4 passed, 45 deselected in 0.36s | 115 | `f2b35ee8748942fa04fc3044c7346b5c73f4a3865a707c8da7827c7cc697f79c` |
| control-staging-bootstrap-red-r1.log | 2 failed, 49 deselected in 8.90s | 1479 | `0b1f5c60aa2808008c29808d9487f81b8cbc26047ecc0c2ac31ba315b8053437` |
| control-staging-bootstrap-green-r1.log | 2 passed, 49 deselected in 7.09s | 115 | `6e2dca80d59facdea168486c719003e7dcf4f699520b10379930442b581f4a3b` |
| control-staging-dispatch-red-r1.log | 2 failed, 51 deselected in 6.20s | 1526 | `285d1a3995aac53555c2fa212efb5a1a37e99301043a30c7732bcd98bf43801b` |
| control-staging-dispatch-green-r1.log | 2 passed, 51 deselected in 9.04s | 115 | `da7411d0f24cb4883bacc213f08b600e11adb41b80d4fd1e9bf37a8e025267bd` |
| control-staging-final-preservation-red-r1.log | 1 failed, 54 deselected in 0.45s | 795 | `cbbc07d147434684cccf1eb28472f68b2bdb3f6a07b86d6ef35c26cf4637f62f` |
| control-staging-final-preservation-green-r1.log | 5 passed, 50 deselected in 10.06s | 116 | `639192317aa3fd3eea3d486c4c2265e5a6249eea637adb93ce6e710687cfaeaa` |


physical-scope-red-r1为测试材料缺SOURCE常量的setup错误，不是行为RED；修复测试材料后red-r2才证明待实现入口缺失。bootstrap在真实独立Python进程执行，使用stdin避免Windows命令行长度限制；候选构造和系统服务命令在合同测试中是明确外部协议边界，不是现场成功证明。

父任务原生锁RED为2 FAIL/0skip/exit1且原因均缺PhysicalLock：control-staging-native-lockred1.json，log1252B，SHA d28720639aa4cc521271f725435c22e49e71e1f9f5153e5909c04cbbdbd5080d。实现后原生锁GREEN为2 PASS/0skip/exit0：control-staging-native-lockgreen1.json，log222B，SHA fbb7c51608e57e2541aea5386db975ff9e24c9606d2d3f61796a54d2344a99ca。此轮工作源码仍继续变化，workingSourcesUnchanged=false，因此只认其锁快照，不冒充最终全套通过。

## 最终输入与输出合同

输入固定十字段MainProgramControlStagingInputs/v1：schemaVersion/sourceCommit/revisionId/suffix/previousControlGenerationPin/buildPin/planPin/coveragePin/unitObservationPin/originalEnvironmentObservationPin。六个引用为TASK本地{file,bytes,sha256}。严格用本轮45dd7dc完整commit、r5、57/58/59，精确既有899索引、实际build/coverage和r5 plan；没有latest或缺省代次。

每host观察精确名称：main-program-control-units-<suffix>-45dd7dc-r5.json、main-program-control-environment-baseline-<suffix>-45dd7dc-r5.json；PRIVATE对应*.private.json。prepare需要实际生成的新观察、原generation完整闭包、public/private plan、两代真实tar和coverage、原环境/进程/unit原件及输入私密配置；全部经现有Records/generation/planner/coverage/environment验证，不复制凭据进公共文档。

建议输入文件名main-program-control-staging-inputs-<suffix>-45dd7dc-r5.json（由父任务写实际pin，工具不生成猜测材料）。纯prepare：

```text
python -X utf8 -B <TASK>/main_program_control_staging.py --inputs main-program-control-staging-inputs-59-45dd7dc-r5.json
```

默认只读本机，零transport、零输出文件，stdout为PREPARED_NOT_STAGED/remoteExecutable=false及host/commit/revision/新保留计数。先经父审查与实际门禁后，唯一实际暂存调用才追加--stage。57/58仅替换显式suffix与其独立输入，不跨host复用观察。库接口run_request(task,private,inputs_file,*,stage=False,transport=None)，正式CLI无自定义transport入口。

成功公共文件两份，沿用原stage报告字段，不另增替代schema：main-program-engine-staged-<suffix>-45dd7dc-r5.json及main-program-configuration-staged-<suffix>-45dd7dc-r5.json。共同status=STAGED_NOT_ACTIVATED、sourceCommit/host/revisionId/previousControlGenerationPin/buildPin/planPin；业务和原配置保持true，reload/backup/restore=false；含原controls身份、容器数、fstab/mountinfo摘要及privateSnapshotPin。engine含逐控制147/packageSha/fileManifest/读回/编译；configuration含原锁取得释放、newDocuments/retainedDocuments完整分区和实际候选/三来源factory结果。共享activation.validate_generation_staging为最终正式判定，不接受文件层结果代替。

PRIVATE唯一同stem main-program-control-staging-<suffix>-45dd7dc-r5：

- -attempt.private.json：MainProgramControlStagingAttempt/v1，ATTEMPT_RESERVED，实际inputs/prepared、执行源码pins、payload bytes/SHA、host。
- -stdout.private.log / -stderr.private.log：实际transport原字节，包含远端私密证据时仅留PRIVATE。
- -transport.private.json：MainProgramControlStagingTransport/v1，实际exit/timeout/原日志pins；unknown/失败保留且automaticRetryAllowed=false。transport抛异常时写UNKNOWN与errorType，不宣称远端未写。
- -result.private.json：原生执行返回的canonical JSON，status/阶段/reports/actual/createdPaths/filesMayHaveBeenCreated；失败保留lastCommand原stdout/stderr的base64。公共privateSnapshotPin指该实际原件。

任意已有attempt或输出都拒绝重复；失败或未知状态没有自动续办路径。旧r4、失败历史与旧engine一律保留，不覆盖。

## 最终独立 Linux 入口与材料

```text
python -B -m pytest -q --tb=short <TASK>/test_main_program_control_staging.py -k linux
```

预期8项：原文件层5、真实物理flock与路径替换2、共享RuntimeGates+真实锁+真实新文件接线1。最后1项使用真实Python子进程和临时proc/systemd/docker协议材料，仅证明组件接线；actual factory仍需真实stage验证，不称其为业务部署测试。

同目录源码最小12份：main_program_control_staging.py、test_main_program_control_staging.py、main_program_control_activation.py、main_program_control_generation.py、main_program_control_upgrade_plan.py、main_program_installation_selection.py、installation_history_custody.py、common.py、test_main_program_control_upgrade_plan.py、main_program_control_runtime.py、test_main_program_control_runtime.py、test_installation_history_custody_layered.py。只需准确pytest依赖（含py.py shim）。8项不需真实服务器私密配置/包材料；父任务使用单一pin tar、原生tmpfs、network none、只读rootfs/bind，验证原始exit/计数/0skip/输入未漂移并清理任务容器。


## 最终本地回归与交接冻结

REGRESSION：`python -X utf8 -B -m pytest -q --tb=short test_main_program_control_staging.py test_main_program_control_generation_activation.py -k "not linux and (not v4 or staging)"`，实际59 PASS / 55 deselected / 0 skip / exit0，187.71s。包含own47与既有v4 staging12。PRIVATE/control-staging-complete-regression-r1.log，128B，SHA256 `d896dcd882d40fbc67b7cc9d71811ac63b044f35a34626b3ba85318a111f4e4b`。本轮未调用远端或Docker。程序及测试使用compile(bytes, filename, 'exec')均PASS、不生成pyc。

冻结源码main_program_control_staging.py 52383B，SHA256 `b2bfa508b5e962007def4f7fbadb8e873cdbd3767415174e5282ed6ce5f7a99f`；test_main_program_control_staging.py 36514B，SHA256 `b8f84c43e3049b67efc8a01c9bacdee59c44ae15d9c716a13b466befaddea606`。最终回归运行期间只更正了程序开头过时docstring，没有修改任何行为或测试；独立父任务仍应以这两个最终SHA做一次完整Windows/Linux验证。日志自身SHA单独发送父任务，不在文档内自引用。

当前结论：完整可审查实现与本机合同完成，等待父独立Linux8项、真实观察材料默认prepare及审查。没有宣称真实暂存、激活或整体用户任务完成；后续真实stage必须由父任务显式审查执行，失败原件/旧路径/所有历史继续保留。


## r5 真实失败后的 bootstrap 回调修复（事前）

Current Status: implementation / bootstrap_environment_dependency_fix。父任务已独立Linux8项PASS、三服真实只读观察与默认prepare PASS，随后唯一59/r5实际stage在runtime-before以NameError失败，filesMayHaveBeenCreated=false、createdPaths=[]。旧attempt/result/stdout/stderr及r5计划/观察均保持，不重试。问题来自ENVIRONMENT_PROGRAM只定义函数，依赖外层hashlib/re/shlex；新的隔离environment namespace仅注入need，真实回调执行到hashlib时报NameError。原局部与Linux接线测试用activation模块回调，未覆盖bootstrap实际返回回调，是本次验收缺口。

设计约束检查：不引入fallback/降级/吞异常；根因修复为固定bootstrap显式提供实际固定程序所需stdlib命名空间，并让真实测试执行load_execution返回的函数；不修改冻结activation或ENVIRONMENT_PROGRAM、不复制另一份环境校验，不临时绕过环境门禁。完整异常只保存在PRIVATE原生result/transport及原stdout，公共CLI只输出稳定错误码。其他固定程序只读核依赖闭包，避免扩大产品范围。

BDD: Given 实际两模块与四段固定程序经同一bootstrap加载，When CONFIG_EXACT及ORIGINAL_BASELINE回调被调用，Then执行真实hash/声明解析且结果与正式环境合同一致；环境漂移仍明确拒绝，不能用activation原模块替代回调证明。

BDD: Given 原生bootstrap内实际程序抛出异常，When远端阶段捕获失败，ThenPRIVATE result保存异常类型、消息和完整traceback（含chain，无locals），保留原errorCode/stage/写入状态；本地公共REFUSED不含异常内容。transport异常亦保留私密完整chain，不重试。

BDD: Given 真实临时Linux进程/原锁/受保护文件，When共享门禁接线测试，Then环境验证必须采用同一个load_execution返回的回调；不再通过activation模块globals隐式填补bootstrap依赖。

后续attempt策略：原r5已永久占用；不改旧attempt、plan、观察或输入、不改名复制冒充新观察。父任务通过正式planner生成新revision r6的public/private计划，重新采逐host绑定r6的新unit/environment观察，写新inputs并默认prepare；只有真实确认候选engine不存在/原状态保持、全部门禁通过后才可新唯一stage。包commit仍45dd7dc、前代仍真实899；revision仅区分新的配置计划/观察/attempt，不能声明r5成功。此策略本轮只记录，不生成或执行r6。


### r5 根因修复实际 RED / GREEN / REGRESSION

- 只读保全核验：PRIVATE/main-program-control-staging-59-45dd7dc-r5-result.private.json，1095B，SHA256 `29b0f2421272961f79fd92bc506ceae8fbc1180b21cf6ae634558206a0d92957`，status=FAILED/stage=runtime-before/errorCode=NameError/filesMayHaveBeenCreated=false/createdPaths=[]。本轮结束同pin保持；未编辑旧计划/观察/attempt/result。
- RED：`pytest -q --tb=short test_main_program_control_staging.py -k "actual_bootstrap_environment or actual_bootstrap_failure or transport_exception_keeps"`，4 FAIL / 55 deselected / exit1。前两实际调用load_execution返回环境回调，CONFIG_EXACT和ORIGINAL_BASELINE均真正NameError/hashlib；后两真实生成bootstrap及transport捕获缺完整exception字段。PRIVATE/control-staging-bootstrap-callback-red-r1.log，2522B，SHA256 `d91fcc87680d5f39a03f55005a7669d4aa738f2c63a812c24656c758cb5e30de`。
- 最小实现：固定BOOTSTRAP imports与environment namespace显式提供hashlib/re/shlex；ENVIRONMENT_PROGRAM原字节不改。exception_details仅在私密remote result/transport错误路径记录异常type/module/message/完整traceback和cause chain，不捕获locals、不投影公共CLI、不改变旧拒绝码/写入状态/重试策略。
- GREEN：同一4项实际PASS / 55 deselected / exit0，5.94s。PRIVATE/control-staging-bootstrap-callback-green-r1.log，115B，SHA256 `010f935fc259544e7122514933d1337a8cd7de17f89de6d7a878bd88ec5e268b`。两环境模式真实成功与环境漂移拒绝都通过；声明含空格的PYTHONPATH实际经过shlex及re，未只核源码字符串。
- REGRESSION：`pytest -q --tb=short test_main_program_control_staging.py test_main_program_control_generation_activation.py -k "not linux and (not v4 or staging)"`，63 PASS / 55 deselected / 0skip / exit0，50.57s；own51+既有v4 staging12。PRIVATE/control-staging-bootstrap-regression-r1.log，117B，SHA256 `6b06de6f1cdbd003d0354142627355022704ce356202ab7e5e8e9e5b9a748977`。
- 固定程序依赖只读审计：实际环境源码外部global仅need/hashlib/re/shlex；custody.SCRIPT内部显式imports，CANDIDATE_GATE及SOURCE_IDLE自己imports，静态符号闭包未发现其他未提供global。没有修改另三段程序或扩大产品范围。
- Linux门禁仍8项，相同12源码输入闭包；原共享门禁接线项已替换为实际bootstrap环境回调。父独立最终建议选择`linux or actual_bootstrap_environment or actual_bootstrap_failure`共11项，使同一Linux字节快照同时覆盖固定程序加载及私密诊断；此轮不自行调用Docker。

新冻结：main_program_control_staging.py 52832B SHA256 `ef5461391a132001586c4c559f1278aa9de8d624c556672b8b31ca7b7f95568c`；test_main_program_control_staging.py 41435B SHA256 `0ad15bf560936bb94c89cb217056821927bfb81adcfe012d5b61843624950e90`。两文件compile PASS；整个最终回归期间源码/测试未改。当前为本机修复完成、等待父独立Linux11与审查，之后由父按正式r6新计划/新观察/新inputs策略执行唯一新attempt；不是重试r5，不新增continuation或revision白名单。
