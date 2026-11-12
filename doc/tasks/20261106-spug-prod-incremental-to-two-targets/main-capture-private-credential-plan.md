# MAIN 保全凭据权限合同修复

## Current Status

2026-11-12 续办确认：用户要求不因178 GiB预估阻止操作，沿用三服已生效的OBSERVE_ONLY。采集重构专属19项通过，完整材料与退出处理均在原期限内通过；相邻回归92/94通过，两项旧fixture缺少当前构造器必要配置，须准确修正fixture后验证。原失败不重发，正式续办与新代次安装仍按既有授权执行。

01:29 UTC：权限10项、准备失败续办及完整历史回归163项均PASS/0skip，输入不变/容器移除。消费端无intent反向RED6项准确失败后已补严格历史判定；真实保留原件r2的23次调用和未安装三保护也满足新判定（仅本地验证，尚未签发clearance或改服务器）。采集性能与可重复后继代次由独立子代理按正式方案推进，整体仍in_progress。

2026-11-12 续办：按用户“现在直接操作，真的满了再说”继续执行已授权范围；三服 OBSERVE_ONLY 已生效，178 GiB 预估不再阻断。新增准备失败续办 RED 为 12 项中 1 项预期失败、11 项通过；真实 Spug 只读查询准确暴露原恢复失败（0业务POST），不重复提交原请求。凭据权限修复的扩大回归尚未通过，正在用修复前相同输入定位既有超时。

in_progress：原恢复失败保留；已确认实际对象凭据0400、内容pin一致，MySQL/Redis均0600。测试58原五服务仍running，backend health UP、frontend HTTP200，启动时间早于本次恢复；custody archive/scheduler为NOT_INSTALLED、fence为ABSENT。

## 目标与里程碑

1. 已完成：只读定位原失败与实际五服务、原保护阶段，原operation不重复提交。
2. 待完成：严格BDD/TDD统一采集器与不可变生成凭据的合法权限合同。
3. 待完成：正式失败续办仅消费可验证的准备阶段失败，保留旧结果，不删除锁绕过；产品包、真实页面和新授权范围内恢复另按原任务链验收。
4. 待完成：将现有单次153成员目标后继安装合同正式扩展为可持续的重复代次升级；保留原v1历史解释。新代次仅允许已审查的实际包差异，明确承接当前b9目标，不能伪造a312前代、覆盖旧engine或修改历史pin。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。对象凭据明确支持owner只读0400或owner读写0600；不接受组/其他用户可读、执行位或owner不可读。MySQL和Redis原0600合同不变。
- 是否从根因和长期维护角度解决：是。安装器生成所有冻结配置为0400是有意的不可变配置合同；采集器必须接受这种更小权限的对象凭据，不能为了兼容修改历史秘密或将配置改成可写。测试实际进入MAIN准备过程，不能只测权限辅助函数。
- 是否存在临时补丁或绕过：否。旧配置、凭据内容和pin不改，不关闭权限检查。当前保留失败仍须通过正式、独立证据闭合的续办路径。

## BDD 与预期验证

- Given 真实文件系统上生成对象凭据0400且原pin匹配，When MAIN准备目标保全材料，Then 完成PREPARED，未停writer/安装保护；与既有0600对象凭据兼容。
- Given 对象凭据具有组/其他权限、执行位或owner不可读，When 同一实际MAIN入口准备材料，Then MINIMAL_SECRET_MODE_REQUIRED并且没有stop/start动作。
- Given MySQL或Redis秘密0400，When 同一入口准备，Then 原0600合同仍拒绝，不扩宽无关凭据合同。
- RED -> GREEN -> REGRESSION须来自隔离Linux真实文件权限、MAIN上下文与实际子进程；有限SQL/S3协议单元不能当服务器验收。实际STANDARD内容精确匹配共享入口。

## 经验门禁

- Trigger：MINIMAL_SECRET_MODE_REQUIRED发生于CONFIGURATION_ADMISSION。
- Preflight check：先核原operation终态/进程退出/完整pin、真实服务与custody步骤。Windows UTF-8，Linux原生权限；变更后先已提交clean专用构建，再考虑控制组件安装。
- Blocker：未知mutation、未证明原进程结束、保护步骤或当前目标身份漂移仍阻断续恢复；当前顶层TERMINAL_UNKNOWN不得改成成功。
- Verification：实际0400正向、非法权限反向、原0600兼容和打包源码一致性；终态、实际原服务、真实Spug分别记录。
- Forbidden action：不chmod历史秘密、不改旧失败、不删active/claim、不重发旧请求、不将仅容器running称恢复成功。
- Evidence：PRIVATE下reader58-secret-admission-r1.private.json（27702B，SHA1fa8e05a96c5454e81fb390b10f4def9fef532de5a7d5067b5a0c8a53036158a）和reader58-current-target-r1.private.json（4581B，SHAf8233b8cffedcbafccf2875a79caf76f2b613ef30540c6779ecb7775371949fc）。

## 已完成的有限验证与续办设计

- 续办RED：preparation-no-mutation-red-r1为12项/11PASS/1预期FAIL；正向停在replacement-intent无条件拒绝。最小实现仅完整历史验证后的PREPARATION、无generation/mutation/unknown、ACTIVE custody且全部未安装保护、原native均exit0时放行。GREEN与原合同回归进行中。
- 采集成本复核：修复前不可变RED快照73ae320c的同一真实dump用例也失败；cProfile显示138次guard中1690次session.check，31216次actual_pin累计24.811秒。原60秒工作预算不能完成完整材料流程。本次不延长生产或测试期限，先按AGENTS重构流程独立评估并降低重复检查成本；内容完整性、实际路径/FD、未知调用拒绝和保护检查保持。
- BDD（采集成本）：Given 真实Linux固定输入和仍为60秒的完整MAIN保全材料预算 / When 子进程退出发生于guard中且原件保持 / Then 在同一预算内完成MATERIAL_COMPLETE且原调用终态可验证；Given 日志原件/目录/权限或活动意图被改动 / When 后续guard / Then 仍拒绝，不使用计时缓存或吞错。若正式可持续保护方案尚不完整则阻断安装，不用延时掩盖。
- GREEN：secret-mode-green-r1实际Linux10项PASS/0skip/native0，输入不变/隔离容器移除。扩大回归仍在运行，已有原生dump时序用例失败，必须读取最终错误并独立复现；不能在未分析前提交或安装。
- 真实历史验证r2使用原目标控制进程25916已绑定PYTHONPATH及b9caa00封包代码，只读0.110秒通过55份原件、23次准备调用：FAILED_RETAINED/PREPARATION，mutation=false、terminalUnknown=false、generation=null，三个保护均NOT_INSTALLED或ABSENT，宿主active精确匹配。r1裸解释器缺jsonschema是诊断载体错误，保留原stderr，未修改服务器依赖。
- 正式续办需覆盖“程序已开始准备、但未安装任何保护且没有业务mutation”的已知失败。现有NOT_STARTED准许不满足该情况，不能手工删除active或把mutation字段改为true。
- BDD：Given 全部原件经过现有MainProgramEvidenceValidation/v1且phase=PREPARATION、无generation、无mutation/unknown，所有保护未安装且原进程已退出 / When 正式no-mutation资源释放和同点同目标clearance / Then 仅释放本operation精确预约、原FAILED与所有原件保持，下一次仍须新真实UI请求。
- 反向：存在安装/释放/未知保护、RESTORE阶段、generation、任何mutation/unknown、缺调用终态、原件变动或别的宿主预约时均拒绝；不能把仅几个布尔字段当完整证明。旧NOT_STARTED及已停写续办合同保持。

## 重复目标组件升级设计与BDD

- 当前v1后继安装只认可a312前代和单reader差异，不能直接安装本轮三处恢复合同及采集成本修复。正式方案是版本化重复后继合同，复用既有独占stage、运行态before/after、原业务/挂载/失败原件保持规则；旧v1字段和判定完整保留。
- Given 当前b9后继已由完整原链原件loader验证 / When 为已提交候选包建立下一代计划 / Then 明确绑定实际前代selection/build/package/controller，精确审查变化成员，四配置文档最小更新，三服及Spug加载同一正式后继链。
- Given 前代pin/实际包差异/物理target/旧runtime/保全图漂移或后继引用成环 / When 构造或加载 / Then fail fast；禁止改旧选择、伪造前代或允许任意文件差异。
- 按AGENTS重构要求独立子代理设计和BDD/TDD，父审查后安装；服务器写入仍须记录experience-preflight。
