# 链策略升级证据 TDD

## Current Status

frozen_for_parent_review。本机新合同79项全部通过；旧回归169项通过、1项旧测试环境前提失效，父已接管唯一旧测试。实际同提交产品双包与Linux原生测试仍未执行，不构成产品部署完成。产品准入修复八文件、旧 v1 reader/常量/失败原件均不改。不远端/Docker/浏览器、不构建产品、不安装、不提交。

## 目标、里程碑、验证

先以真实临时147/146成员tar、已提交临时Git输入和实际pytest子进程产生证据，复现缺新合同；实现新版本后新旧回归。最终真实产品包/测试必须来自同一已提交 sourceCommit 和专用干净 release worktree，当前未提交工作区不能产生最终升级成功证明。源快照只包含已提交文件和显式冻结包，不带tmp/ignored内容。

里程碑：纯delta/tar RED→GREEN；命令/collection/JUnit/loaded输入 RED→GREEN；完整coverage/两处分派 RED→GREEN；runner实际本机协议→受影响回归→精确冻结。最终交付包验证缺提交时明确阻塞对应阶段，不称恢复保留功能完成。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；未知schema/profile/范围/缺终态/漂移直接失败。
- 是否从根因和长期维护角度解决：是；显式新合同，不重解释旧覆盖证明。
- 是否存在临时补丁或绕过：否；实际测试节点和输入绑定，不固定本轮测试数量或制造失败。

## 经验门禁

- Trigger：三模块链策略修复不能复用单模块目录优化证明。
- Preflight check：父已审独立设计；真实包成员与提交输入、SAFE转换、原始测试终态、baseline45四rich/coverage关联必须全核。
- Blocker：任何额外语义差异、未提交/ignored输入、错variant、未绑定原始结果、skip/fail/error/timeout、旧合同改变。
- Verification：真实临时文件/tar/提交与实际pytest子进程；新旧原件回归；最后父独立完整产品包验证。
- Forbidden action：运行服务器/业务、改八个产品文件、伪造安装失败或PASS、将协议fixture称真实产品验证。
- Evidence：批准设计、后续每阶段原始输出和冻结SHA。

## BDD

- Given 两种真实147/146成员包，When 新delta验证，Then只允许批准三模块语义变化和完整成员分区，未知/额外/缺失/编译失败拒绝。
- Given实际pytest命令、collection、JUnit、逐节点结果、退出回执和输入前后SHA，When验收，Then零fail/error/skip、tests>0且全部绑定；缺任何原件或错加载模块拒绝。
- Given已提交干净输入，When快照/测试，Then仅接收同commit的tracked字节；tmp/ignored/脏输入不得进入证据成功路径。
- Given前代45四rich，When新coverage，Then其原activationInputs和coveragePin一致；初代461不得自动顶替。
- Given旧v2/v1原件，When同一公开入口，Then逐项按旧逻辑验证，无新字段要求。

## TDD

RED: 本机 UTF-8 Python pytest test_main_program_chain_policy_evidence.py -q --tb=short -> 21 failed / 0 skipped / exit 1 / 1.14s。20项缺新增模块，公开planner分派1项明确拒绝新schema；真实临时147/146成员tar夹具均完成，无setup失败。

GREEN: 同一21项 -> 21 passed / 0 skipped / exit 0 / 0.92s。实际包全成员读取、SHA、compile及两版本planner分派已实现。

RED: 加入真实pytest执行器合同后的36项 -> 21 passed / 1 failed / 14 errors / 0 skipped / exit 1 / 1.45s。15项新场景统一缺 run_main_program_chain_policy_verification；14项是在建立实际执行夹具时失败，尚未宣称子进程已运行。

GREEN: 36 passed / 0 skipped / exit 0 / 7.17s。真实pytest成功和exit1失败原件均已产生；过程中暴露pytest将导入名pytest_command误认hook，改为显式非hook别名后全过，未改断言。

RED: source snapshot/baseline新增15项 -> 36 passed / 9 failed / 6 errors / exit 1。缺正式snapshot及baseline接口；6项fixture缺REQUIRED_SOURCE_FILES，未运行Git冒称成功。

GREEN: 51 passed / 0 skipped / exit 0 / 27.76s。真实临时Git提交、完整raw输入与四rich文件绑定通过。

BDD: 父批准显式 MainProgramExecutionInputRoot/v1 五字段 {schemaVersion,sourceRoot,moduleRoot,sourceInputPin,moduleInputPin}；Linux路径用PurePosixPath严格核，不用Windows resolve。实际runner从__file__取原字节并全树读前后，terminal固定runtimeInputPinsBefore/After；validator从持久source tar及variant tgz独立重读。容器卸载后不要求runtime路径存在，未知schema/外逃/跨variant/错成员/输入漂移拒绝。旧v1不变。

RED: 执行根映射新增12项 -> 12 failed / 51 passed / 0 skipped / exit1 / 66.97s；7项缺executionInputRoot、5项缺runtime_path。最小实现后62 passed / 1 failed：原非零进程fixture使用文本冒充source.tgz，被新增真实解包准入正确拒绝。仅将此fixture输入换成包含原失败用例的真实tar，保留真实pytest exit1断言。

RED: 全覆盖公开分派7项 -> 1 failed / 6 passed / 63 deselected / exit1 / 130.24s；正例明确在旧v1-only入口拒绝。最小新v2分派后该完整原件正例1 passed / 69 deselected / exit0 / 25.65s；返回原6字段不变。

RED: 真实仓库source输入名和冻结包载体2项 -> 2 failed / 70 deselected / exit1。发现standard_fixes是单.py文件、不是目录；按实际路径纠正required列表，新增只消费已指定tgz的载体后2 passed / exit0。

BDD: 父另批准verification.evidenceRootMapping精确{runtimeRoot,persistentRoot}；只允许已允许证据根内的一一映射，不改原command/exit/pin，最终physicalPins返回真正host文件pin。RED 6 failed（缺bind_mapping）→ GREEN 映射及运行路径11 passed / 0 skipped / exit0。

GREEN: 完整 test_main_program_chain_policy_evidence.py -> 79 passed / 0 skipped / exit0 / 144.10s。包括真实四suite执行器CLI协议测试、原失败保留及完整v2coverage。协议夹具没有构建/安装产品，也没有业务恢复。

REGRESSION: 原5文件 -> 169 passed / 1 failed / 0 skipped / exit1 / 67.02s。唯一失败：test_main_program_control_upgrade_plan.py::test_actual_routes_settings_and_four_connection_values_stay_compatible，原断言要求PRIVATE/main-program-configuration-plan-45dd7dc-r5.private.json不存在，但该原件已在先前正式阶段落盘。未修改/删除原件或旧测试；父负责将过时“不存在”改成原字节及完整pin前后保持。其余新旧schema、目录覆盖、旧常量和v1-v4激活回归通过。原工具会话24637 / 输出chunk257546；本轮没有重定向生成原始本机stdout文件，不将手写摘要冒充原始log。

## 实际命令与冻结边界

使用独立依赖目录PYTHONPATH与PYTEST_DISABLE_PLUGIN_AUTOLOAD=1；Python固定 C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe。

新合同完整命令：python -B -X utf8 -m pytest doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_chain_policy_evidence.py -q --tb=short。

旧回归命令：python -B -X utf8 -m pytest TASK/test_main_program_control_upgrade_plan.py TASK/test_main_program_control_generation_activation.py TASK/test_main_program_activation_coverage.py TASK/test_main_program_activation_evidence_pins.py TASK/test_main_program_control_activation.py -q --tb=short；TASK为本目录。

新增正式helper、runner、冻结实包测试载体和合同测试；原文件只增加planner/activation两处分派。源码/测试在79项通过后冻结；仅此日志补记结果。父将审阅后提交，随后必须以包含本阶段代码的同一已提交commit新建LF干净release worktree，生成实际147/146包、同提交source snapshot、四suite完整Linux原件以及新delta/v2coverage；当前尚无这些真实产品成功报告。生产范围仍未完成，不能用此协议GREEN代替。

## Windows原件路径规范接缝（父限定授权）

当前状态：新窄阶段frozen_for_parent_review，103项全通过。父授权只修新profile的Windows路径规范表示与旧delta绑定；不改变旧v1 reader、任何原件、Linux运行入口或产品范围。

BDD: Given真实archive-catalogue-package-delta-r3.json中的C:/原路径与同一归档的native C:\\ pin，When新profile核前代包，Then以PureWindowsPath规范物理等价且完整bytes/SHA相同闭合，原件不改；两种写法仅允许各自全程一致的规范分隔符。

BDD: Given混用分隔符、..、重复/点路径、UNC/设备/流别名或POSIX反斜杠，When新reader或前代绑定读取，Then明确拒绝；不能利用路径归一丢弃非法段或放宽POSIX。

RED: 窄阶段24项（pytest同一文件 -k 'real_prior_delta or canonical_separator_forms or physical_aliases or equivalent_path_never'）-> 6 failed / 18 passed / 79 deselected / 0 skipped / exit1 / 0.48s。真实旧delta及两种真实归档已读，5项缺独立前代包绑定接口、1项C:/被旧路径解析器拒绝。

GREEN: 同24项 -> 24 passed / 79 deselected / 0 skipped / exit0 / 0.69s。新profile的Windows路径接受纯前斜杠或纯反斜杠规范写法；二者通过PureWindowsPath做物理规范比较，同时严格核完整长度/SHA。旧delta没有长度字段时，以新pin长度+旧原SHA读取原真实文件证明；不补写旧原件。POSIX仍原严格规则。混用、UNC、设备、流、点/尾空格别名及路径穿越拒绝。

REGRESSION: 完整同一新合同文件 -> 103 passed / 0 skipped / exit0 / 123.57s，工具会话23594 / 终态chunk b36216。此前79项和新增24项均通过；runner/实包载体及planner/activation两分派本窄阶段未改。测试和helper冻结，仅日志补记终态。父继续负责已接管的旧测试回归及最终同commit发布产物验证。
