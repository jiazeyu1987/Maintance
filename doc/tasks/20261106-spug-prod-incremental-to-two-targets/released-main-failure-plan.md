# 已无变更释放的 MAIN 失败状态收口

## Goal / Current Status
in_progress。修复实际history381：外层TERMINAL_UNKNOWN/RESTORE_RESOURCE_NO_MUTATION_NOT_PROVEN保留了child exit1，worker已FAILED_RETAINED且正式no-mutation release已存在，但GET仍返回RUNNING，阻挡后续同源恢复。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。仅明确的RESTORE MAIN、该外层失败码且存在正式释放原件走独立收口；任何缺件/改动仍RUNNING并暴露原因。
- 是否从根因和长期维护角度解决：是。复用正式verify_no_mutation与完整worker程序证据，将原操作终态投影为FAILED；不修改历史外层、epoch、成功/失败原件或互斥。
- 是否存在临时补丁或绕过：否。保留原实际child退出码；不能把UNKNOWN里的1改成2来伪造历史。

## 经验门禁
Trigger：已退出原操作外层未知但已有正式无变更释放。Preflight check：原request/config/intent/native exit、worker完整程序证据及no-mutation release同一操作绑定。Blocker：任何未知调用、变更、缺件、错误释放、活进程或绑定不符。Verification：BDD RED/GREEN/REGRESSION、正式包构建与精确安装后原GET返回FAILED。Forbidden action：改写原失败、跳过RUNNING互斥、重复恢复POST、凭目录缺失宣布失败。Evidence：query-381-spug-r1、terminal-envelope-381-r1及原55pin/正式clearance。

## BDD / Verification / Milestones
1. Given MAIN准备失败已实际退出、所有调用成功结束、无变更且原正式release完整；When 查询原操作；Then 返回原worker失败码和FAILED，追加引用证据，原文件保持。
2. Given 缺失/篡改release、worker、exit或存在未决调用；When 查询；Then 保持RUNNING并暴露具体错误，不释放、不重跑。
3. Given 未释放或其它UNKNOWN/传统恢复；When 查询；Then 保持原合同。

先真实失败测试，最小实现，再相邻回归。只在已提交目标对应新临时构建worktree构建；安装范围仍为恢复控制组件，测试58恢复仍需真实Spug入口。新4e请求未受理的原失败回执保留。

## Actual TDD
- RED released-main-native-red-r2：9场景实际执行，原本应闭合场景FAIL，8项拒绝PASS；r1收集期模块来源错误保留，不算RED。
- GREEN/REGRESSION released-native-safe-r2：真实认证SAFE payload，12新场景+47相邻native，共59 PASS/0failure/error/skip，11.719秒、exit0，源码/包内输入保持、容器已移除。追加live PID、boot和布尔exit拒绝，原正常与拒绝路径均验证。测试载体对已认证payload名称强制原位置导入并在收集及结束逐SHA验证，不容许旧fixture插入source路径导致混源。
- 独立原resource-release回归14 PASS/36.954秒，原source模块，未冒充包认证。
- mixed formal及候选来源失败、Docker关闭期间未执行的两份失败报告完整保留。Docker进程/服务均已退出且API named pipe消失，启动原本机Desktop后原18080/18081容器恢复；未重启远端、未重派业务POST。
- 本次产品仅native控制文件修改；59项通过后可单独提交。整体真实新恢复/安装/融合/清理仍未完成。

## 真实入口缓存失败续办

c2bc8b8 已在57/58实际激活，原GET仍返回同错误。只读原件证明 completion.json 早已记录控制层 FAILED，terminal exit2；该缓存路径先调用 owner_result 严格校验外层，尚未进入新增 refresh_original，已有测试只覆盖直接 refresh。因此此前修复测试边界不完整，不能认定实际问题已解决。

BDD：Given 原缓存FAILED、同一已退出MAIN外层UNKNOWN且正式无变更释放完整；When 真实 reconcile 查询；Then 走同一严格 refresh_original，投影原worker失败，原completion及所有原件保持。缺释放、原件漂移、错误操作/退出/PID等仍RUNNING或明确拒绝。其它缓存失败保持原 owner_result 校验，不改原终态。

设计约束与经验门禁保持。先在既有真实Linux夹具增加 reconcile 场景并复现，再最小接入，原直接路径及相邻用例回归。仍只有同一native控制成员变化；产品须提交后新建独立构建worktree，正式包认证后才能安装。不在服务器直接改已安装代码或历史completion。

- RED released-cached-native-red-r1：实际24项，11 FAIL、0 error/skip，13.094秒；缓存有效案例在 owner_result 抛 PROGRAM_EVIDENCE_RESULT_TERMINAL_INVALID，直接12项通过。额外修正两项既有拒绝合同的测试断言：原 request 绑定错误直接拒绝；非 MAIN 缓存失败保持原结果，均不得投影为成功或解除 MAIN 互斥。
- 最小实现：仅已绑定的 MAIN 缓存 FAILED、指定控制层错误和严格整数 original exit2，转同一 refresh_original 全量验证；该入口继续验证 timeout、进程、原 result 和正式无变更释放，缓存原件不修改。
- GREEN released-cached-native-green-r1：24 PASS，9.204秒；REGRESSION released-cached-native-regression-r1：24个直接/缓存场景及47个既有 native 场景，共71 PASS，9.688秒，均0 failure/error/skip。实际认证 SAFE 模块输入、运行时输入未变，隔离容器已移除；没有远端动作或业务写入。实际安装与真实 Spug 验证仍待完成。
