# 历史 Spug 源码角色的显式补充 custody

## 目标与当前状态

继续同一自动备份任务的本机历史证据读取修复。父已批准限定读取合同；不改现行 Spug、任何远端、旧 selector/attempt/checksum/native 原件。当前状态：BDD / RED 待执行。

里程碑：1. 精确原件保全及 RED；2. 两类角色及当前 reader 分离的最小实现；3. 有限合同、受影响回归及一次实际完整入口；4. 冻结交父审阅。未经父确认不提交。

## 经验门禁

- Trigger：I1 preflight 的历史 publication 在 `MAIN_SPUG_ORIGINAL_BYTES_CHANGED` 阻断。
- Preflight check：只按显式 selector/原 custody/六份 attempt 读取；核完整 bytes/SHA，Git 原 blob 须精确提交和路径、实际 exit0。当前目录不是历史源码权威来源。
- Blocker：原件缺失/漂移、旧集合不符、映射冲突、未知角色、Git 非零或超时、reader 实际加载路径不符均停止。
- Verification：真实临时文件负例、真实 Git blob 原生结果、旧无参数失败保持、完整当前历史入口一次。源输入与原件前后摘要保持。
- Forbidden action：不得归一换行、重写旧 checksum、动态执行旧源码、全局 mapping、宽泛忽略 TASK、无依据补成功或重派业务。
- Evidence：原 r2 preflight native/stderr；45dd7dc catalogue blob；78de6dc activation blob；原 r7 acceptance 401366B/f1302551…。
- 路由依据：`docs/experience-index.md` 的多机器发布接管、运行资源依赖闭包、输入原件及 UTF-8 门禁。仅本机文件/Git/测试，不进入高风险远端执行阶段。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。无参数保持旧严格失败；有参数只接受显式固定角色。
- 是否从根因和长期维护角度解决：是。历史逻辑输入与当前执行 reader/物理保全原件分别验证。
- 是否存在临时补丁或绕过：否。旧 schema/记录保持；附加 record 仅为已确证来源提供独立 custody。

## 正式边界

新 `MainProgramSpugHistoricalSourceRoles/v1` 精确字段：`schemaVersion`、`selectionPin`、`baseHistoricalCustodyPin`、`acceptanceInputsPin`、`acceptanceAttemptPin`、`attemptPins`、`sourceRoles`、`readerCustodies`、`currentReaderPins`。

`sourceRoles` 只有 `catalogue` 与 `acceptanceActivation`。前者固定旧产品相对路径及 20770B/d6dfd470…，出现于五旧 attempt 和外层 acceptance；保全来源为 acceptance 原 inputPins 已绑定的 b5 checkout 相同原字节，并绑定 45 build/commit/path。后者仅外层 acceptance 的 121760B/ef070f77…，使用 78de6dc6308c88020b149b1a656540e94b7e097f 的精确 Git blob 独立保全与实际 native/stdout/stderr。五旧 attempt 原 activation107657/963bbe 的现有 custody 不变。

`readerCustodies` 只允许本次需改动的 historical-custody 与 acceptance 两个原 reader；原件须在 acceptance 原 inputPins，独立保存完整字节。当前执行的 history/acceptance/current-loader 三个源码另 pin，并核实际导入路径。新增执行证据与保全文件不掺进原 logical inputPins；旧集合逐项比较只有明示角色可投影，未映射项完整相等，额外项仅限已验证补充 record 的物理闭包。

原 selector 不改。新 preflight CLI 参数显式传入 private custody pin，current loader→acceptance→history 用 keyword 传递。旧四 reader 的接口与原 native/program/argv/exit 逐值比较保持。结束复核全部实际物理原件。

## BDD / 首批 RED

1. Given 真实原 selector/六 attempt 及合法开发漂移，When 不传补充 custody，Then 仍精确拒绝。
2. Given 两种已证原字节及独立 reader 原件，When 加载有限补充合同，Then 验证全部关联并只产生物理闭包，不改任何旧 logical pin。
3. Given 错 role/attempt/原 SHA/提交/路径/重复或已有 custody 冲突，When 读取，Then 明确拒绝。
4. Given 原件缺失/内容变化/硬链接或当前 reader 错原点，When 读取或 finish，Then 拒绝，无 live fallback。
5. Given 六 attempt 原集合，When 重建输入少了未授权项或多了未绑定项，Then 拒绝；只两类角色及两个 reader 的逐项证明可解释差异。
6. Given 完整原 r7 receipt 与上述显式补充，When 实际 current loader 只读重验，Then 原六 stage/native 全部仍严格通过；无配置/备份/恢复派发。

## 原始定位

2026-11-11：只读正式入口首先在 publication attempt 的 catalogue 原 pin（20770B/d6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9）失败。五旧 attempt 均有同 pin。外层 acceptance 的14个工作区源码只有此项及 activation（121760B/ef070f77fd7c8f5753a5eead343d2e49e20e52e45cc4aabc5601f7e1d0726f69）变化；其余12个完整保持。45 checkout HEAD 精确且 clean，Git blob 实际20770/d6，checkout21152/3de保持。78de Git blob 实际121760/ef070、exit0。未修改旧记录。

## RED 与原件保全

父批准后，以 x 模式创建 PRIVATE/spug-historical-source-roles-originals-20261111-r1。实际 Git argv/cwd/30秒期限/exit0/timeout=false/stdout/stderr/executablePin 均写入独占原件；stdout 精确121760/ef070。两个将变动的 reader 原字节也独立保全，preservation.json 为6205B/e2294680bc1c678075eee9051e4312637f4d8ea050f330bdebbb04f83c0aeb91。catalogue 使用原 acceptance inputPins 已绑定的 b5 checkout d6 原文件，不改文件。

RED：PRIVATE/spug-source-roles-red-r1，真实 pytest nativeexit1，31 tests /30 failures /0 errors /0 skipped，5.24秒，输入前后保持。30项均到达缺失正式 `load_source_roles` 入口；旧无参数测试实际以原 ORIGINAL_BYTES_CHANGED 拒绝并 PASS。原 stdout/stderr/JUnit/native 全部保留。现在进入已审最小实现；不改31条期望。

首次 GREEN r1：30 PASS/1 FAIL，0 errors/skip。唯一失败为新冲突测试把三字段 source-role 行直接当成原两字段 existing-custody 行，因此先正确拒绝 `EXISTING_MAPPING_NOT_BOUND`，未到预期冲突门禁。只修夹具为原合同的 originalPin/preservedPin 两字段；原 CONFLICT 期望与产品严格门禁不改，原失败保留。

GREEN r2：31 PASS，2.57秒；有限旧协议回归65 PASS，16.84秒；均0 failure/error/skip、nativeexit0、输入保持。

## 同项 generation 逻辑/物理库存接缝

唯一实际完整 current 入口 r1（49.219秒/nativeexit1/输入保持）越过五份旧 attempt 后，在原 `MAIN_GENERATION_PRIVATE_PREDECESSOR_CHANGED` 拒绝。原 public/private 五元字段全部相同；父批准只读核前代及本项精确修复。正式上一45 reader 实际完整读取后，三份 selection 的其他字段完全相等；旧 localInstallationPins122项→当前physical121项，唯一缺项是workspace catalogue20770/d6，无extra/changed，checkout21152/3de仍在。诊断原件33423B/a8ada837d4cc007e0aa4e73e074a73bdffdb48fff09dd6039023b0c7a95f8aef保留。

有限设计：不改 `_partition` 全等或旧secret。仅45 catalogue具名转换复用已正式校验的local proof及真实Git/checkout验证，将material原序列中首次checkout替身恢复成原d6 logical pin，后续Linux checkout项保留。递归selection继承旧logical库存；bundle.inputPins和_finish仍只包含当前已核physical。其他来源/提交不转换，不归一换行，不扩角色。

新增BDD：Given三份真实冻结selection/真实Git原件/真实诊断physical集合，When精确logical投影，Then逐对象、顺序完全等于旧selection且physical不变；错commit、缺/错checkout或缺独立Linux项应拒绝。仅这组RED/GREEN后才重新运行实际完整入口。

有限 logical RED r1：5 FAIL/0 error/skip，0.52秒，全部到达缺失 `_catalogue_logical_materials`，原件/代码输入保持。父批准后仅增加 generation 内具名逻辑投影：45原证据产品集合必须恰一catalogue/d6，复用实际Gitblob+checkout读取；原material列表须有恰两份相同checkout身份，首个转回原local proof的logical pin、独立Linux项保持。递归logical selection与physical inputPins分别组装，`_partition`/原plan严格全等/_finish物理复核均不改；未改activation/包/原记录。

logical GREEN r1：本项36新用例＋原generation36项，共72 PASS /0 failure/error/skip，11.99秒、nativeexit0、输入保持。三份真实冻结selection的122项、顺序、所有字段完整相等；diagnostic实际physical121项保持。未更改任何旧测试期望。

## 冻结与交付边界

当前本机有限合同已通过；完整实际 current 入口 r1 的 generation 耦合失败原件保留。按父要求，修正后的完整 actual 重验 HOLD，交父审后由父新r3执行，不能将本机72 PASS写成真实I1/UI验收或完整历史成功。

实施仅五模块：historical custody、acceptance、current installation、preflight CLI、generation 的上述窄接缝；另新本测试与本日志。旧四reader、selector、attempt、native/program/argv/exit、任何原checksum均未改。新记录`main-program-spug-historical-source-roles-20261111-r1.private.json`6191B/428e12b072d94ab8b3cdb40ca0b0a934029767ffce17beb7c533f474b5d72570，与原件保全目录均x模式创建。父preflight追加`--historical-source-custody <该绝对路径>`，仍使用原b5/r7 selector。

测试解释器为固定Codex Python；PYTHONPATH只含本TASK及PRIVATE/test-dependencies，禁第三方pytest自动插件，无业务/远端调用。各阶段native.json保留实际argv、退出码、期限状态、原stdout/stderr/JUnit与完整输入前后摘要：`spug-source-roles-red-r1`、`green-r1`、`green-r2`、`regression-r1`、`logical-red-r1`、`logical-green-r1`。全部原失败及本次完整actual-r1保留，无删除或覆盖。
