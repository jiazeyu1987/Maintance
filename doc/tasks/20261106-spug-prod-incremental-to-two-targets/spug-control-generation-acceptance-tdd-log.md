# r7 已发布配置只读验收 TDD

## Current Status

READY_FOR_ACTUAL_GENERATION。本机合同实现已冻结；父可执行实际r7四控制切换。实际r7正向prepare/六stage验收仍待真实generation及新鲜观察，本阶段不能记产品完成。第一阶段已提交b88bfb4且保持冻结；不改产品/旧reader/selector、不远端、不提交。

## BDD 与设计约束

按 `spug-control-generation-acceptance-design.md` 的精确等值投影、六stage白名单、原selector expected/audit关系、默认零transport和原生证据不可跨程序复用场景执行。无fallback/降级/吞异常；长期正式方案为独立已发布配置的控制代次验收；无临时绕过。已摘取Spug运行依赖闭包及多机器历史接管门禁。

## RED r1

命令：固定Python `-B -X utf8 -m pytest <TASK>/test_main_program_spug_control_generation_acceptance.py -q --tb=short`，PYTHONPATH=PRIVATE/test-dependencies、PYTEST_DISABLE_PLUGIN_AUTOLOAD=1。

实际27 FAIL / 0 ERROR / 0 skipped，exit1，26.87s；每项均为正式新模块缺失 ModuleNotFoundError。真实历史/custody/r7计划及原native前置读取无setup错误。日志PRIVATE/spug-control-acceptance-red-r1.log。尚无真实r7完成generation，不能用测试协议代替安装或最终prepare成功。

## RED r2

追加纯投影原expected/audit关系、观察漂移六项及真实staged记录拒绝，共8项实际FAIL，27 deselected、0 skipped，exit1，25.22s；均仍为正式模块缺失。日志spug-control-acceptance-red-r2.log。随后只读核实真实stage的status为STAGED_NOT_ACTIVATED，修正该测试前置断言；未将stage当PASS或制造完成generation。

## 最小候选、真实子进程与 GREEN

- 首次候选35项：34 PASS/1测试载体FAIL，51.66s；sourceRegistrationSelectors的真实合同是list，原负例误按dict索引。精确改成删除一项，拒绝期望不变；原green-r1.log保留。并按真实565转换输入核正式字段resourceBuildPin，未猜candidateResourceBuildPin。
- RED r3：新增本机真实子进程非零退出7/exit0非法JSON/timeout三个场景，3 FAIL、35 deselected、0 skipped，26.40s。缺正式独立阶段录证函数导致未留stage；随后最小抽取 `_record_stage` 并用于实际execute循环，没有另造成功或重写原stream/native协议。
- GREEN r2：`pytest <TASK>/test_main_program_spug_control_generation_acceptance.py <TASK>/test_main_program_spug_historical_custody.py -q --tb=short`，实际69 PASS（38新+31历史）、0 fail/error/skip，exit0，88.17s。完整命令、8项实现/测试/旧reader/selector的前后SHA在PRIVATE/spug-control-acceptance-green-r2.json；inputFilesUnchanged=true，原stdout在同stem.log。

## 父审录证修正 RED→GREEN

BDD：Given native实际exit0返回结构化FAILED，When 本地阶段validator拒绝，Then stage必须保留原完整result并单列validationError，不能用UNKNOWN替换已知业务失败；只有transport未返回时result为UNKNOWN。

RED r4：真实Python子进程输出FAILED对象，原件exit0/完整stdout保留；实际1 FAIL、38 deselected、0 skipped、25.81s，失败精确为原FAILED对象被UNKNOWN覆盖。日志spug-control-acceptance-red-r4.log。

最小修复：AcceptanceTransport的execute仅返回原实际命令对象，post-inspect由finish_stage在记录器保存返回值后执行；之后才调用原stage/native校验。program/argv/inspect顺序不变。stage固定增加validationError（成功必须None），reader严格要求成功证据该值为None。post-inspect或validator异常也保留已返回result；未返回才UNKNOWN。

GREEN r3：仅重跑受影响的3个原真实native失败场景+1个新FAILED返回场景，`-k 'real_local_native_failure or real_returned_failure'`：实际4 PASS、35 deselected、0 fail/error/skip，exit0，43.41s；未重复无影响已通过套件。PRIVATE/spug-control-acceptance-green-r3.log/json，所有记录输入SHA前后保持。此前69项终态保留，不将最终4项谎称39项整组重跑。

## 冻结与剩余验证

- helper：20948 bytes，SHA256 d0e6af24f5cc57eb185126c750fb43a85a93ac5754e9381e2c33e037130d4b0d。
- 专属test：14076 bytes，SHA256 77b89137a1012ca9c5cba59a50f8a8425bde5473fd67b05dc68597d2a8f14e1a。
- 两文件UTF-8读取及compile通过；旧五reader/installation_selection/phase1正式custody未改。无远程、备份、恢复、配置写入或提交。
- 剩余：父真实r7四activation+正式generation、新鲜三host/Spug观察后，本机实际prepare必须通过；之后父独占派发六stage验收，完整原生证据由新reader重读。新selector分派尚未实施，不应把当前旧v4 selector当已切新代次。
