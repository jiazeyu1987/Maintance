# 自动备份后的独立来源恢复验证

## Current Status
ready_for_closeout — TASK helper/测试/说明已完成；16项本机合同测试PASS，真实10044原件清单唯一性及远端载体语法检查PASS，现场执行交根任务，未调用服务器。

## 目标与里程碑
- [x] 基于真实 audit 与 UI terminal 精确绑定操作及已安装0d44578来源。
- [x] RED 后实现独立只读检查，保留原367脚本/证明。
- [x] GREEN 回归，交付每点不可覆盖报告与closeout字段。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。证据、身份、健康、锁或SQL状态不符明确失败。
- 是否从根因和长期维护角度解决：是。新自动代次使用实际source owner和capture pin；复用已核旧只读检查，不复用其旧安装选择与操作证明。
- 是否存在临时补丁或绕过：否。FULL和I2完整10044原件SHA，I1明确仅实时状态，非全SHA声明。

## 经验门禁
- Trigger：每个自动FULL/I1/I2成功后需要独立证明来源恢复。
- Preflight check：audit PASS、terminal SUCCEEDED、submission request操作号/source/安装提交一致；实际安装owner→capture pin和engine精确绑定。
- Blocker：数据库UUID/version不符、event_scheduler非ON、read_only/super_read_only非0、服务/语义健康失败、epoch非READY、source worker存在、锁忙、原失败pin变化。
- Verification：真实临时文件与终态合同单测；现场执行只能由根任务在该操作完成后另行运行。
- Forbidden action：不得执行SQL写入、重载服务、重放备份/恢复、改原件/旧367回执，或将I1实时检查标为10044全SHA。
- Evidence：每种kind固定 automatic-<kind>-source-restoration.json，独占创建并绑定各输入pin。

## BDD
- Given submission、audit、terminal均指向相同成功操作及安装提交，When 只读检查实际来源，Then 验证原五服务/SQL全局状态/周期/源空闲，并报告精确pins。
- Given 任一输入非成功、操作或源码代次不匹配，When 准备检查，Then 在远程调用前失败。
- Given FULL/I2，When 检查失败原件，Then 精确10044个唯一固定pins全SHA保持；Given I1，Then 明确fullShaVerified=false/verifiedFiles=0而不假造完整校验。
- Given 输出已存在，When 再调用，Then 拒绝覆盖或重复执行远程检查。

## 验证和交付
- RED：新增测试先因 verify_automatic_source_restoration 模块不存在而 collection FAIL。
- GREEN：16项任务内输入合同/拒绝条件/独占写入测试PASS（0.22秒，零skip）。使用实际FULL submission及安装记录配结构单测对象，不向服务器发送、不将样例保存为现场证明。
- REGRESSION：本机读取原失败基线，验证10044个唯一合法pins；新远端载体与原只读SQL/exporter/原件代码编译PASS，remoteReadDispatched=false。
- 调用与固定报告/收尾字段见 automatic-chain-audit-usage.md。每点来源报告 schema AutomaticSourceRestoration/v1；FULL/I2完整SHA，I1明确仅状态。输入终态缺失时预检失败，不能先生成成功结果。
