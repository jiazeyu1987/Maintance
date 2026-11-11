# NAS reader目标153后继的纯helper TDD

## Current Status

ready_for_parent_review；新helper87项纯units、有限相邻回归216项全部通过，三服实际官方包candidate及current/history spec纯构造通过。未SSH/Docker/提交，旧loader/runtime字节未改。真实后继三服激活与正式新selection尚待父执行，不能将本轮纯验证称为安装或恢复验收。

## 目标与里程碑

- 目标：本次a3121c6已ACTIVATED的153文件目标，升级为仅common/recovery_backup_epoch.py变化的新153包；新配置只4份。
- 里程碑：父审设计已通过→有限测试→父RED→最小纯实现→父GREEN/有限相邻回归→真实安装与恢复由父负责。
- 预期验证：候选和暂存计划逐字deterministic、所有非允许变化fail closed、原对象不变；纯测试不是服务器安装或恢复证明。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；固定153→153单成员，错误起点/图/原件一律拒绝。
- 是否从根因和长期维护角度解决：是；显式已激活前代与原历史分层，旧合同不改。
- 是否存在临时补丁或绕过：否；不假造147起点、不覆盖原文件、不删除失败历史。

## 经验门禁

- Trigger：NAS共享reader、目标控制后继、旧receipt/custody、单成员正式包。
- Preflight check：完整正式前代ACTIVATED及build绑定、新旧包153全清单/SHA/compile、4doc边闭合、保留失败pin、current153与legacy147 spec分别处理。
- Blocker：未知delta、旧schema伪起点、源/业务/epoch/凭据/资源/原图变化、已有目的路径或别名、未闭合实际激活。
- Verification：本文BDD/RED/GREEN及实际包纯重建；后续真实载体固定前后observations、独占创建和新activation原文。
- Forbidden action：不降级reader门禁、不改旧v1模块、不以mock PASS冒充实际安装，不自动恢复/重派失败，不覆盖原件。
- Evidence：nas-reader-target-successor-plan.md、前代r2选择及正式r3加载原件、旧smallapp失败原件（父持有）。

## BDD与有限单元范围

1. Given 前代完整ACTIVATED且target153/build身份匹配；When 构造本次仅epoch reader变化的新153候选；Then 只生成repo/policy/owner/control四文档，旧12图引用/源/物理目标/epoch/资源/凭据/失败pins保持。
2. Given 不是固定a3121c6前代、target仍147、build绑定或当前controller不匹配；When 构造；Then 拒绝，不读取历史字段冒充当前artifact。
3. Given 加删成员、第二成员变化、reader未变化、包或manifest/pin/compile错误；When 构造；Then 拒绝。
4. Given 原保全14图变化或少边、旧binder不在当前153 engine；When 构造；Then 拒绝，不重新生成秘密或captureRef。
5. Given 有效候选；When 生成只创建文件计划；Then 新154包文件+4doc=158，原154包+16doc=170原pin保持，输出非安装状态且输入不变；错candidate或冲突路径拒绝。
6. Given 旧legacy receipt绑定147而当前PID来自153；When 父运行载体核验；Then current spec用于实际进程，原history spec只用于旧custody/inventory；本helper绝不调用旧TargetControlRuntimeTransition构造伪147，相关字段的纯合同先拒绝错绑定。

## 实现等待门

父已完成：36 FAIL/0 ERROR/SKIP，1.60s，全部MISSING_TARGET_153_READER_SUCCESSOR_HELPER，PRIVATE/target-successor-red-r1.xml。父随后明确放行本机pytest与新helper/loader。

## 已完成TDD证据

- GREEN candidate/staging：本机固定pytest8.3.5，`pytest scripts/tests/test_main_program_target_control_successor.py -q` -> 36 PASS，1.30s；PRIVATE/target-successor-green-r1.xml。
- RED runtime spec：同命令加`-k runtime_spec` -> 8 FAIL，0.56s，MISSING_SUCCESSOR_RUNTIME_SPEC_BUILDER；PRIVATE/target-successor-runtime-red-r1.xml。
- GREEN runtime spec与前阶段：44 PASS，1.59s；PRIVATE/target-successor-green-r2.xml。
- 以上都是纯配置/文件计划协议，不是服务器安装/真实恢复证明。

## 激活投影与独立loader的BDD（下一RED前）

1. Given 已正式加载的a3121c6三服前代和三份本轮原始成功wrapper；When 后继投影；Then 每服candidate重新构造、current spec与原history spec分别等于前代，new spec严格推导；只替换target有效行和对应owner/control/build绑定，source/Spug/前代完整保留。
2. Given before/after真实完整观测；When 检查153→153切换；Then 只允许选定target的PID/argv/env/package与唯一追加dropin；未知依赖、业务、挂载、custody、历史或source peer变化拒绝。
3. Given 58原失败文件真实pin_file数组；When 核原始结果；Then failurePinsBefore==failurePinsAfter==retainedFailurePins==candidate原值；57/59允许明确空数组，不将失败改成功。
4. Given BOUND/缺一服/错spec/旧receipt错绑/不完整native或HTTP/原始receipt字节不闭合；When 投影；Then 拒绝，不授予安装资格。
5. Given 独立五字段selection及全部本地pin原件；When loader实际读文件；Then 先原v1完整前代loader，再三份本轮原文和官方双包，全inputPins与代码闭包重读；路径/SHA/未知selection字段/任一输入变化拒绝。结果installationVerified=true/runtimeVerified=false，不能当实时健康。

## 后续RED / GREEN / REGRESSION原始证据

统一本机命令使用固定Python缓存runtime、`PYTHONPATH=PRIVATE/pytest-runtime-8.3.5`和`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`；不下载依赖，不启动Docker或外部服务。

`python -X utf8 -m pytest scripts/tests/test_main_program_target_control_successor.py -q --junitxml=<PRIVATE/对应原件>`；有限集合用`-k`选择。

- 激活第一次fixture跨host pin失配：30 ERROR（RESTORE_OWNER_BINDING_CHANGED），PRIVATE/target-successor-activation-red-r1.xml；没有拿ERROR当RED。修正fixture原owner/control重新pin后取得真正RED：45 PASS/30 FAIL，全部MISSING_SUCCESSOR_ACTIVATION_PROJECTION，6.55s，target-successor-activation-red-r2.xml。
- 父审发现真实pretty JSON原pin不等canonical：先新增正例真实RED，1 FAIL，0.24s，PREDECESSOR_SELECTION_PIN；target-successor-pretty-red-r1.xml。最小修复显式必传原selection/build raw，按原bytes/SHA/重复key及值核验，不重编码原件。
- 实际纯candidate第一次发现私密本机Windows path不能用POSIX remote pin校验；新增native path RED，1 FAIL，0.26s，MAIN_TARGET_CANDIDATE_PATH_INVALID；target-successor-local-pin-red-r1.xml。新独立私密输入pin规则保留原生绝对路径，不改原记录；远端paths仍严格POSIX。
- 激活GREEN第一次75 PASS/1 FAIL：测试wrong-receipt fixture误共享前代receipt dict，修改会同时改变前代；修正fixture深拷贝，没有放宽验证。随后76 PASS，7.34s，target-successor-activation-green-r2.xml。
- 独立loader RED：9 FAIL，2.19s，全部MISSING_SUCCESSOR_LOCAL_LOADER；target-successor-loader-red-r1.xml。
- 独立loader GREEN：85 PASS，9.68s，target-successor-loader-green-r1.xml。
- 原始receipt唯一末尾自身路径出版阶段正例PASS；before重复依赖反例先真实RED（DID NOT RAISE），1 FAIL/1 PASS，0.67s，target-successor-dependency-red-r1.xml。最小修复调用原canonical_dependency_properties检查前后所有properties，只检测重复而不修改任何原始观测；DropInPaths顺序仍精确。
- 最终REGRESSION：`pytest scripts/tests/test_main_program_target_control_successor.py scripts/tests/test_main_program_target_control_candidate.py scripts/tests/test_main_program_target_control_activated.py scripts/tests/test_main_program_runtime_dependency_properties.py -q --tb=short` -> 216 PASS，13.42s，0 skip/error；target-successor-regression-r2.xml。其中新入口87、原candidate54、原activated61、依赖14。

## 三服实际纯输入验证

- 输入：父已完成的PRIVATE/nas-reader-predecessor-formal-load-r1.private.json（1668pin正式前代结果，不在子任务重跑loader），原r2选择/raw1552B build、实际旧a3121c6及新b9caa00标准tgz、原三激活candidate图和58原4失败文件pins。
- 结果：57/58/59均BOUND_NOT_INSTALLED、4新docs、158独占写计划、170前代原件pin；仅本机纯处理。PRIVATE/nas-reader-actual-successor-candidates-r1.private.json，315294B，SHA e67db35bf7b5cd057ee2fa80578f402007406b968a1fe4acc0aeccb62ce832ee。
- 正式current153/history147 spec各组纯构造均PASS，35 retainedDocuments、旧receipt字段保持；规划dropin名必须在所有原名字后。第一次6个z规划名被严格拒绝，16个z规划值后通过；未写实际dropin。
- 新后继完整loader尚无真实本轮3激活原文，未执行正式完整加载，未声称现场健康/恢复完成。

## 公开接口与当前限制

- `build_target_control_successor_candidate(*, predecessor, predecessor_selection_pin, predecessor_selection_raw, predecessor_build, predecessor_build_raw, build, predecessor_package_raw, package_raw, host, preservation_documents, configuration_root, new_engine, retained_failure_pins)`。
- `build_target_successor_staging_plan(*, candidate, **同candidate输入)`，返回原始bytes的158项write计划；不写文件。
- `build_target_successor_runtime_spec(*, current_spec, retained_history_spec, candidate, dropin_pin, successor_pid)`，只构造，不执行或验证进程。
- `verify_target_successor_activations(*, predecessor, activations, build, build_pin, package_raw, previous_package_raw, predecessor_selection_raw, predecessor_build_raw)`，三服完整原始wrapper的纯投影。
- `load_activated_target_successor_installation(task, private, *, selection_file, historical_source_custody_pin=None)`，本机完整pin文件链；安装历史通过后runtimeVerified仍false。

本子任务仅新增helper/test/计划/TDD；无commit，父审后统一集成。工作区全局git diff --check报告共享execution-log与request-command-log末尾空行；子任务未修改它们，也未清理其他任务内容。
