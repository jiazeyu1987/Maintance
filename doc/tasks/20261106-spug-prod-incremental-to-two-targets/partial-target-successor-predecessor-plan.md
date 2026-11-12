# 单服已激活后继的精确承接设计

## Current Status

ready_for_closeout：父批准的本机实现与必要回归完成，6个必要task源及5个独立测试已冻结；未访问服务器、未提交。336项Python受影响合同及74项Node合同全部PASS、0skip。真实partial和新官方包的逐host验收由父接续，不把本机有限测试当服务器安装证明。57原0119156及58/59原b9身份保留，旧pin/PID/回执不改；完整v3只有三host实际ACTIVATE全验后才发布。

## 目标、里程碑与验证

1. 核对57真实PASS回执以及现有三服验证循环可复用边界。
2. 审查最小partial predecessor与混合前代最终selection合同。
3. 若父批准再BDD RED→最小实现→GREEN；仅必要纯合同和真实57原件定点验证。
4. 57以前代0119156、58/59以前代b9各自精确承接同一新官方包；最终必须三服真实PASS才对外完整ACTIVATED。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。部分完成是显式状态，不能以缺结果自动采用旧行。
- 是否从根因和长期维护角度解决：是。按每host真实激活原件承接混合前代，复用原完整host判定；不建立每轮一次性迁移脚本。
- 是否存在临时补丁或绕过：否。不伪造三服PASS、不改历史选择，不将STAGE/PREPARE当ACTIVATE，不为epoch失败放宽runtime/native。

## 经验门禁

- Trigger：三服控制组件升级只有部分ACTIVATE成功。Preflight check：完整原base链、真实单hostPASS wrapper/receipt与精确新包及review，实际当前行与runtime spec；Blocker：原件漂移、包/配置/runtime/依赖/业务/原生/API或未知阶段缺证据；Verification：同原host验证与定点BDD；Forbidden action：合成其它host PASS、改旧PID/pin、回退已成功host、容忍任意包差异、把原FAILED写成功；Evidence：本设计和父私有实际报告。

## 已确认事实

- 57真实私有wrapper `target-control-successor-57-0119156-r1-activate-result.private.json` 为MainProgramTargetControlSuccessorActivation/v2、PASS/complete，sourceCommit=0119156d9c6be9e73d35509da6b19f642b81dadf、pid=14267，明确前代为b9共同selection及57原b9 activation receipt；currentRuntimeSpec/successorRuntimeSpec和四新配置均随原件保存。它可逐项验证，不需要伪造其它两服wrapper。
- 现有 `verify_target_successor_activations` 已在每host循环内执行完整wrapper/result/receipt、候选重建、runtime/peer/依赖/argv、native/API、失败原件和createdPaths验证；三服共同参数只在循环外围固定。因此可抽出同一host判定供partial与完整final复用，旧v1入口与外层三服要求保持。
- 现有v2 selection/build/review与loader默认三host同一前代包。不能只替换57 effective行、仍让它引用b9的build/package/current spec；也不能让58/59引用0119156冒充已激活。
- 58的0119156 STAGE158件与PREPARE失败应留在不完整尝试证据中，不产生当前控制组件权限。旧58 b9仍是唯一已证实运行前代。

## 建议最小正式方案

### 1. 一个显式前代overlay原件，保持三服完整状态真实

新增local `TaskMainProgramTargetControlPartialPredecessor/v1`，精确字段建议：schemaVersion、baseSelectionPin、buildPin、standardPackagePin、packageDeltaReviewPin、targetActivationEvidencePins。本次evidence keys必须且仅为57；build/package/review是57实际0119156那一轮，不含新修复包，不修改b9 selection。

loader先完整读取并验证base b9链，再读取0119156官方包和原review以及57真实ACTIVATE wrapper/script pin；调用共享host判定逐项完整核验。输出status=PARTIALLY_ACTIVATED、activationVerifiedHosts=[57]、retainedBaseHosts=[58,59]、installationVerified=false、runtimeVerified=false。输出的effective rows/owner/control/runtime specs/activationReceiptPins与per-host build/package绑定明确：57来自真实PASS，58/59来自原base。

该输出只用于构造后继，不作为Spug可执行完整安装，也不能让UI写入。parent/输入pins全部保存，原source/Spug/base与58/59原件保持。未知host、缺57真实PASS、STAGE/PREPARE或失败wrapper一律拒绝；本轮不扩展任意partial调度。

### 2. 最终三服selection显式v3，只增加混合前代所需信息

建议 `TaskMainProgramTargetControlSuccessorSelection/v3`：schemaVersion、predecessorSelectionPin（指上述overlay）、buildPin、standardPackagePin、packageDeltaReviewPinsByHost（精确57/58/59）、targetActivationEvidencePins（精确57/58/59）。不改变旧v1/v2字段或解释。

每host仍使用同一固定 `MainProgramTargetControlPackageDeltaReview/v1`：predecessorSelectionPin=overlay pin；57的predecessorBuildPin/previousPackagePin/commit精确为0119156，58/59精确为b9；三host新build/package必须同一个新正式提交。58/59 review可共用同一原件pin。每条实际包差异仍严格匹配源码固定reviewed profile，不接受caller任意成员集合。

具体新profile成员数须等epoch/failed-journal产品修复冻结、正式包生成后，从0119156→新包与b9→新包两套真实差异确定并单独代码审查；本设计不猜成员、不重写旧四成员profile。

candidate/activation可复用现v2逐host字段，因为它们已明确previousController、predecessorSelectionPin、predecessorBuildPin、packageDeltaReviewPin和当前runtime，足够表示该host的实际前代；v3只改变外层三host混合输入选择。若实现审查发现不能无歧义，应升级该层schema，不能隐藏新增含义。

### 3. 抽出共享host判定，禁止合成全服输入

将当前for-host循环主体提取成纯 `_verify_target_successor_host`，输入为同一base/host的精确controller/owner/control/current+original runtime/receipt、各自旧包与build、review和实际wrapper；输出仅该host的已验行、配置、spec与receipt。原v1/v2完整verifier仍要求3个host，调用同一helper聚合，原返回语义保持。

partial loader只调用57一次，不补造58/59 wrapper，不暂时改HOSTS、不复制57 proof到其它host、不把缺host当成功。最终v3 loader逐host调用同一helper，全部通过才status=ACTIVATED、installationVerified=true；最新target三服同一新commit。57真实0119156 PID/owner/control/spec/receipt成为精确前代，不回写它的b9历史。

现有builder `_repeat_predecessor`只增加显式partial输入分支：必须是上述正式loader输出、当前host具有精确predecessorBuild/package绑定及完整已证实行，不能通过把status改ACTIVATED绕原判定。其它caller不能自造混合行。

### 4. runtime与未完成尝试保持

- 57：current=真实0119156 successor spec，original=原147 history；四配置与engine/dropin/receipt精确保留，source peer维持现已批准的CONFIG_EXACT单向投影。
- 58/59：current仍来自b9，原147 history不变；58已暂存0119156与PREPARE失败原件保留但不被当当前组件。新commit路径不能覆盖它们。
- no_workers/native/epoch准入保持，failed-journal产品修复须经另agent正式设计/TDD与新已提交包解决；此承接合同不能吞掉58的当前epoch错误。
- UI仅新增完整v3 schema分派，仍经统一正式loader；partial不能走assertInstallationGeneration或submit。v3祖先保留overlay与其b9/57原件，但完整target祖先链中的提交身份必须显式解释，不把overlay当三服旧提交成功。

## 最小文件范围

1. `main_program_target_control_successor.py`：提取共享host判定、显式partial loader/绑定、v3混合前代完整loader与按host review选择，旧v1/v2保持。
2. `main_program_current_installation.py`：仅分派完整v3与供builder显式读partial（不能当完整安装）。
3. `main_three_target_ui.cjs`：仅完整v3分派/已验commit与正式祖先形状；partial拒绝，不增UI控件或扩大恢复目标。
4. 新独立 `test_main_program_target_control_partial_predecessor.py` 与必要UI schema测试；设计/TDD记录。

candidate preservation_graph、产品ops/recovery、旧结果/pins、旧wrapper和服务器均无需为partial承接修改。

## 必要BDD / RED范围

- Given真实b9全链与57真实0119156 PASS原件 / When partial load / Then仅57升级、58/59精确保留，status明确PARTIALLY_ACTIVATED，source/Spug/原147历史不变。
- Given57缺wrapper、仅STAGE/PREPARE、任一实际receipt/script/candidate/argv/peer/native/API漂移 / When同loader / Then拒绝，不能靠顶层PASS或改PID通过。
- Given新包及两种精确旧包 / When按host构造 / Then57旧build/package=0119156、58/59=b9；任一互换或review差异不符拒绝。
- Given实际57已升级 / When下一次完整v3 / Then57使用真实current spec和PID，不回退；三host全部新ACTIVATE完整验证后才对外ACTIVATED。
- Given partial只有57 / When Spug完整安装/真实UI submit / Then拒绝；旧v1/v2协议不因增加partial而改变。

## 批准后的必要补充与完成情况

- 共享host validator已提取；原v1/v2仍要求完整三host，partial明确仅57且`installationVerified=false`。真实本机文件partial载体28PASS，缺回执、非ACTIVATE、包/脚本/配置/peer/native/运行态漂移均拒绝。完整祖先仅加载一次，不逐host重载或复制整47MB祖先。
- 产品新增正式`common/recovery_program_retry.py`后，父批准安全tar仅增加显式153/154边界；旧默认153不变。正式growth review/v2增加`addedMembers`，固定两个源码profile：`MAIN_TARGET_RETAINED_RETRY_FROM_PREPARATION/v1`精确8changed；`MAIN_TARGET_RETAINED_RETRY_FROM_READER/v1`精确12changed。两者唯一新增retry模块，禁止删除或caller自定白名单，逐项old/new SHA必须等于实际包差异。实际官方包最终核对由父执行。
- 154包对应candidate/staging/activation/v3：155个包文件+4新配置=159独占写，旧153包+manifest、14图、owner/control共170原pins保持。transition新行与新包观测154，before真实旧行仍153；原147history、no_workers/protected_compare不改。shared RuntimeGates.verify_package原按row.fileCount判定，无需修改。
- 父批准activated native必要分支：READY仍原5字段；只有candidate/v3显式允许FAILED_RETAINED_RETRY_ADMITTED，native增加原产品14字段admission及精确rejectedSources。真实FAILED tail、原READY前缀与17字段授权/未消费pins闭合，并绑定原失败packet和正式clearance纯结果。只有被授权source可选，其它源仅精确PROGRAM_RETRY_SOURCE_NOT_AUTHORIZED；旧v1/v2三源全可选合同不改。
- 完整selection/v3逐host选择review/build/旧包，统一新154包；57前代011、58/59前代b9全部精确绑定。完整本机文件链21PASS，partial不能通过统一完整loader或UI。UI只增加schema dispatch/partial ancestry表达，仍同一I2→58一次真实提交，回执以已验selection SHA命名，旧两次失败operation禁止重用。
- RED/GREEN/REGRESSION与完整命令、限制见`partial-target-successor-predecessor-tdd.md`。最后源码冻结后的Python336PASS/0skip，Node74PASS/0skip；本机未启动浏览器、未调用服务器或执行恢复。提交/正式原件loader/运行安装/UI恢复由父任务收尾。
