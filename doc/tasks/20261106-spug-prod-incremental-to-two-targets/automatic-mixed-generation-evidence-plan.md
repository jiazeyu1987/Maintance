# 自动增量各阶段真实代次验收

## Current Status
ready_for_closeout — 本机106项PASS/零skip，完整prepare与嵌入载体语法通过，FULL七原件SHA保持。helper冻结交root，未访问服务器或生成I1/I2现场证明。

## 目标与里程碑
- [x] 固定既有FULL所有回执与证明SHA，明确I1/I2 v2选择合同。
- [x] BDD/RED：新来源与保留MAIN各自包/控制/运行环境绑定；错阶段、错安装或旧控制拒绝。
- [x] GREEN/回归/载体语法，冻结交root实际执行。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。新I1/I2缺显式stage selection即失败，不选择latest或旧控制。
- 是否从根因和长期维护角度解决：是。统一复用automatic_stage_deployment纯本机loader，将每个controller实际代次及完整manifest带入验收，历史父点仅按原pin读取。
- 是否存在临时补丁或绕过：否。不重写FULL成功证明，不更改旧归档和控制配置。

## 经验门禁
- Trigger：仅来源控制升级，MAIN57和Spug继续保留0d，I1/I2跨代链验收。
- Preflight check：每个kind不可变stage选择+精确公开/私密安装/build/Spug pins；request/submission/terminal与实际source一致；目标按自身manifest和runtime。
- Blocker：缺stage、错提交/包/原始控制pin、历史父报告变化、混用source manifest检查旧target或未知协议。
- Verification：纯本机真实文件合同BDD RED/GREEN，旧FULL证据逐SHA保持，所有嵌入载体编译；现场执行由root另行完成。
- Forbidden action：不访问服务器、不生成假现场PASS、不改历史FULL证明、不自动选最新代次、不覆盖旧配置。
- Evidence：定向测试日志与混代helper冻结报告。

## BDD
- Given I1/I2 v2明确选择新source+旧MAIN/Spug，When准备审计与来源证明，Then绑定该阶段source实际控制pin及其包，逐controller使用对应manifest。
- Given旧FULL audit是父点，When新source审计增量，Then保持其原point/result/epoch pins，不要求历史点由新代码生成，也不重新写FULL报告。
- Given缺selection或传入旧installation或错terminal代次，Whenprepare，Then在远端调用前拒绝。
- Given完整source/target runtime不同，When验证实际服务配置，Then使用target自身固定runtime计算服务摘要，并核独立语义健康；不以新source代码代替旧target代码。

## 实现与验证
复用UI冻结的load_stage_deployment，wrapper以实际stage选定source控制pin/包构造spec；I1/I2缺stage、传旧安装或submission绑定不符立即拒绝。每个controller分别从自己的build和STANDARD包读取130文件manifest。audit使用新source程序读取历史FULL point/result原pins，不重写FULL报告；报告带明确stage/source/Spug/install代次。审计本机输入在远端返回后再次逐SHA复核。

sourceproof的validate_evidence新增可选deployment，I1/I2强制传loader结果；FULL历史无参数仅接受原0d。远端载体逐controller自己的manifest核文件，MAIN服务摘要在MAIN自己的Python与完整环境子进程计算，分别记录sourceRuntime/targetRuntime；源MySQL/Redis/五服务/语义健康/锁/epoch及10044原件检查保持。

- RED mixed-generation-evidence-red.txt：11 FAIL/1原FULL保全PASS。
- 第一次GREEN命令本机Python路径拼写错误，pytest未启动；mixed-generation-evidence-green.txt为空，不能计成功。修正命令并确认解释器存在后green-r2：12 PASS。
- 扩展完整I1/I2 prepare、任一controller包漂移、选择后改本机输入的拒绝测试。第一次回归103 PASS/2旧错误码断言不符；显式SOURCE_DEPLOYMENT_REQUIRED正确拒绝，更新对应断言后regression-r2：106 PASS/零skip，41.92秒。
- 新测试用临时真实文件和明确合成包元数据验证合同，不将fixture保存为现场成功。完整源证明/目标runtime子脚本编译通过，真实FULL prepare仍旧0d，automatic-mixed-generation-full-originals.json七份真实证据逐SHA保持。
- 冻结报告automatic-mixed-generation-evidence-fix.json固定helper/共享合同/测试与原件pins。操作命令见automatic-chain-audit-usage.md；现场I1/I2尚未由本分工运行，不宣称升级或备份已通过。
