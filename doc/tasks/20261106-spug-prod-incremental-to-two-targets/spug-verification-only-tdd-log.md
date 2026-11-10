# c1 只验收：阶段 B 的 BDD / TDD

## Current Status

本机实现与必要验证完成，源码冻结；等待父独立核验，现场B验收因产品读取预算问题暂缓，整体发布尚未完成。父已批准设计 `spug-verification-only-seams.md` a4409ec4691c76f0145c1aa70e58a85180c535dee8126f97ac9c4241395db16b 的最小四接缝；仅新verify-only模块/专属测试/本日志、selection/collector v4及A单函数历史托管参数及明确批准两处旧A测试fixture。旧pub/v2/c1/HOST/SPUG正文和产品保持。不调用Docker、服务器、浏览器，不提交。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；每一历史输入/原生回执必须有明确完整证据。
- 是否从根因和长期维护角度解决：是；历史执行原件与当前验证源码分别绑定，同一深校验不复制。
- 是否存在临时补丁或绕过：否；只验收不重新发布，不修改失败历史。

## 经验门禁

- Trigger：七配置写入已完成，最终配置解析失败；A现已实际补齐并重载。
- Preflight check：原c1七APPLIED/三HOST及原FAILED、A七阶段/15native/719输入、唯一d119及A16正式托管。
- Blocker：缺原件、超托管集合、当前输入漂移、未知调用、需重写配置或变更代次。
- Verification：实际旧记录纯读取、RED/GREEN、原生文件/进程负向合同及旧reader回归；现场由父独立执行。
- Forbidden action：不重发七配置/host-publish，不删claim/gate，不改350/719，不mock现场成功。
- Evidence：已批准设计、父源码托管3c1cafd4、实际A e71d33ce、各独占测试日志/原生退出。

## BDD（先于实现）

1. Given 原c1和A真实记录，When 唯一d119已托管后当前selection改变，Then 历史前缀可完整读取，默认A无托管仍严格拒绝；其余349项和映射范围不能放宽。
2. Given A实际七阶段/15native及719输入，When 逐项读取，Then 只接受原单simple替换与精确entry重载；丢失/替换原件或任意摘要PASS不足通过。
3. Given 原c1/A真实完整闭包，When B默认prepare，Then 无现场命令、不生成成功原件；只修改经A证明的entryPid，控制45/r6/c1不变。
4. Given 只验收传输，When 选择publish/install/custody/其它容器/错误host/未知阶段，Then 派发前拒绝；六阶段只guard与原HOST/SPUG verify。
5. Given 原生结果非零、损坏stdout、读回缺项或阶段未知，When runner收口，Then 保留原失败及门禁，不生成core/selection或自动重试。
6. Given 六阶段原生原件完整，When v4reader，Then 原project_core与三服选择闭合；旧v1/v2/v3行为保持。fixture只证明合同，不形成实际安装结论。

测试固定缓存Python与既有test-dependencies；实际原配置/回执仅私密读取，不输出凭据。实际服务器、容器及最终UI由父任务处理。

## 里程碑与真实TDD证据

各日志均在本任务PRIVATE排他创建，同stem `.private.json`保存原生argv、实际退出码、耗时、logPin；不覆盖RED。固定Python为缓存runtime，`-X utf8 -B -m pytest -q --tb=short -p no:cacheprovider --rootdir <repo> --confcutdir <repo>`；PYTHONPATH仅已有test-dependencies。

|日志|原生结果|SHA256|
|---|---|---|
|verification-only-red-r1.log|9 FAIL/exit1/4.78s；缺历史托管参数及新模块|4879fc1062c70d601690dd2a7598c04f642877a1758b527d942b1e1cb05f5310|
|verification-only-green-history-r1.log|1 FAIL/8 PASS/exit1；新增stderr必须空条件不属于旧A原合同，实际五原件为warning诊断|b0c1a1b289eee9dbb2f280fcd21d79ecb7cde491488732e43a448e84f2fd5840|
|verification-only-red-runner-r1.log|2 FAIL/8 PASS/8 ERROR/exit1；runner未实现，且reload原repr字典顺序重建有误|6355f8dd38c117b699493c17ebe7921b85c01ac453328956202bfc7c43d2699c|
|verification-only-green-runner-r1.log|18 PASS/exit0/9.59s|15f1cefbebe348005087f9f4cef7167ccec2844115e5b8a7cb60f64f87411c6c|
|verification-only-red-v4-r1.log|2 FAIL/22 deselected/exit1；selector和collector尚无v4分派|ece07ee18a775a9b310996d69641a23a6c2bc300fdb086ca20ed2ee1020c1430|
|verification-only-green-v4-r1.log|24 PASS/exit0/16.00s；包括真实本机原生exit3/损坏JSON/timeout、原gate第二次拒绝|ebcdec1628198f858b1d17685cf9f674f70ce04b11ef88a651f4f9e1e098ce67|
|verification-only-green-boundary-r1.log|30 PASS/exit0/15.60s；原native篡改拒绝及源码范围验证|5dcf597c3876679d188348561d530edf01ea7b284571781c69f9f925468c5672|
|verification-only-regression-r1.log|400 PASS/2 FAIL/exit1/195.54s；7模块所有输入保持；旧A参数化write/stage无custody先被真实d119漂移门禁拒绝，错误来源与旧regex不同，待父批准同类fixture显式托管|203a58bea1d50e273d3dc161554e7f478ec322bfe285566eeef77260c4ef533a|
|verification-only-green-fixtures-r1.log|5 PASS/64 deselected/exit0/19.20s；父批准负向fixture同类调整后，四篡改和精确diff边界全部通过|268d4f745243f0d803697ecbffe8b80d08f6e2a3b76ebd3aba303f79e387ebb7|
|verification-only-regression-r2.log|69 PASS/0skip/exit0/61.22s；变动两测试模块完整回归，原session28810收终态，全部14输入前后保持，其余333项r1 PASS输入未变|97c494ed3a94e5ec99e03f4e07ab9edd19b4b237703f2e839a30ac9bfa732ffa|

历史A五份实际602B stderr/SHA39b33f3d1d0d7f1df5c6e17bcf25a8a889f298615fab81a30ee32834eb1396d7为Paramiko导入warning。旧A/c1合同保存stderr，以native exit及完整stdout判结果；B不追设stderr-empty要求。完整stderr原件仍逐pin读取，返回nativeDiagnosticPins并在新rich显式保存；没有忽略过滤、删除或修改旧警告。inspect仍按旧纯JSON命令要求空stderr。

reload原程序含repr(identity)，原canonical core/stage排序不能恢复当时native对象顺序；现在从真实before原生stdout取得完全相等的identity原插入顺序，逐字节重建reload program。没有AST/换行归一化替代载体SHA。

## 父明确批准的旧测试接缝

旧A测试 `test_actual_seven_applied_and_three_host_verifications_remain_proven` 原来直接读取350现路径。selection加入v4后，默认A合同正确拒绝已经变化的d119；不能让历史测试继续假设工作文件永远旧版。父明确批准唯一两行调整：先UTF8读取正式 `spug-verification-source-custody-r1.json`，再向原函数显式传`historical_source_custody=custody`。原结果、appliedCount/hostVerifications、错误码和pins断言全部保持。

新测试另证明无custody默认调用仍拒绝；并从A正式16托管读原835f测试字节，断言当前差异仅这一处两行。A模块也从050c原字节验证除批准的 `validate_failed_continuation` 外所有AST节点完全一致；runtime/reload生成函数没有修改。原A执行源码/测试托管原件和350/719报告不变。

随后7模块回归暴露同一参数化负向fixture的write/stage两例仍无custody，先被原pin漂移正确拒绝而非原期望摘要错误。父明确追加批准 `test_changed_c1_summary_cannot_authorize_simple_installation` 同样读取正式custody并向原函数传参；保留全部四种tamper和`pytest.raises(ValueError, match='DEPENDENCY_')`断言。新边界测试与原835f全文比较，严格只允许上述正向与负向两处差异，没有放宽regex或改产品错误掩盖。

失败项修后仅重跑变动的A/B两模块；原其它五模块333项已经PASS，源码/测试与r1输入逐SHA保持。最终不把分次覆盖宣称为一条402 PASS原生记录；保留r1的400 PASS/2 FAIL原件及后续修复回归原件。

## 默认准备及父实际执行接口

输入严格12字段（控制提交45/r6、资源c772从A证明派生，不混为同一SHA）：

```python
records = contract.Records(TASK)
c1_inputs = records.read('main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')
c1_failure = continuation.private_json(PRIVATE, c1_failure_pin, [])
runner = records.read('spug-c1-runner-terminal-r1.json')
records.read('main-program-spug-runtime-dependency-activation-c7728ad-r1.json')
records.read('spug-verification-source-custody-r1.json')
inputs = dict(
    schemaVersion='MainProgramSpugPublicationVerificationInputs/v1',
    sourceCommit=c1_inputs['sourceCommit'], revisionId=c1_inputs['revisionId'],
    controlGenerationPin=c1_inputs['controlGenerationPin'],
    continuationInputsPin=records.references['main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json'],
    continuationAttemptPin=c1_failure['attemptPin'], continuationFailurePin=c1_failure_pin,
    continuationCompletionPin=runner['completionPin'],
    dependencyActivationPin=records.references['main-program-spug-runtime-dependency-activation-c7728ad-r1.json'],
    historicalSourceCustodyPin=records.references['spug-verification-source-custody-r1.json'],
    verificationId='v1',
    outputFile='main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v1.json')
```

父应先逐pin确认，排他保存输入再调用；本子任务未生成实际输入/selection。默认CLI：`python -X utf8 -B <TASK>/main_program_spug_publication_verify_only.py --inputs <输入文件名>`，返回PREPARED_NOT_VERIFIED且无现场调用。显式追加`--verify`才运行。`--apply/--activate/--publish`均拒绝。

纯API：`prepare_verification(task, private, input_basename)`；`stage_program(prepared, stage)`生成固定六阶段程序；`command_arguments(prepared,stage)`给精确argv/timeout，父可独立只读审查载体。只有`VerificationTransport.execute(stage)`受限派发，没有install/publish/custody/reload方法。

顺序是两个A完整after guard夹住三服原HOST verify与原SPUG verify；只有Spug SPEC的entryPid由A精确原→新证明替换。固定容器gate与按原c1failure摘要的claim都排他保留；未知不重试。每阶段原生request/program/stdout/stderr/实际退出码独立保存。

新core仍原MainProgramSpugInstallation/v1，PRIVATE同stem MainProgramSpugPublicationVerification/v1 rich深验证成功才写。新TaskMainProgramInstallations/v4仅schemaVersion/sourceCommit/controlGenerationPin/spugInstallationPin/verificationInputsPin；不能拿A PASS或控制-only创建选择。

## 本机验证的限度与现场风险

- 已读取实际A七阶段/15native/719输入、c1七写/350输入，并真实核唯一d119与A16托管；本机没有产生六阶段现场成功原件。
- 本机进程/临时文件用例只验证失败留存、原生绑定及不重试，不冒称真实Spug或服务器成功。最终六阶段、v4成功core和UI仍由父实际执行验证。
- 控制GET可能产生原控制审计；报告configurationWrites=false/businessMutationDispatched=false/controlApiQueriesPerformed=true/queryAuditWritesMayOccur=true。不得将只验收表述为服务器绝对零写入。
- 若现场或本地finalization失败，完整原件和gate保留，不自动再跑六阶段；须按明确原结果诊断后另审正式续办，不能删除gate或追改失败。
- 父已发现实际UI读取链路累计耗时超过现有deadline，独立产品修复正在进行；B现场`--verify`目前由父暂缓。本工具的本机准备/交付不宣称该现场阻塞已解除。

## 最终冻结（6源码及本日志）

|文件|bytes|SHA256|
|---|---:|---|
|main_program_spug_publication_verify_only.py|29240|5ac6b75bab7ff5b0afa9418b281f705947bbd4630dfe9a9c70ca34b31fec987f|
|test_main_program_spug_publication_verify_only.py|12836|88468211e6605d0508103e6ae0b9cd84dc18268c7252acc4fb3dda9939c99b20|
|spug_runtime_dependency_completion.py|49719|4c4477b301a0058681944c815ce63533852230ce768a9b640b26f1dd9ac938d4|
|test_spug_runtime_dependency_completion.py|19073|64204dd327fc04da89ee7d3756ec5d760b5780ec4a9a8bd7a5e81f59caa94c0b|
|main_program_installation_selection.py|15700|557b384234b5b38ec7c738ba3c1086d74f8c2768412399dc1680a6a5427dd786|
|observe_closeout_hosts.py|16656|436edc7e36f68c965eb21f392c80d2618a6e5cf0305698da8d86fe30fc2f736d|

6文件均内存compile PASS，无pycache。完整7模块命令/输入pins在 `verification-only-regression-r1.request.private.json`，两模块修后命令和前轮其余输入不变证明在 `verification-only-regression-r2.request.private.json`；原生退出与原始日志pin在同stem `.private.json`。7模块分别为B、A、原continuation、原publication、publication_v2、installation_selection、closeout_host_snapshot。未写任何实际B输入或成功选择，不将分次验证伪报为原生402 PASS。
