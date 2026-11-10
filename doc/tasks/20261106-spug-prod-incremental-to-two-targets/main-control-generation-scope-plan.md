# 控制代次原件闭包准入

## Current Status

ready_for_closeout。本机最小实现、15项GREEN（含真实r7默认prepare）与214项相关回归已通过，source/test冻结交父；叶symlink用例在Windows创建前置报1314，保留给父真实Linux执行，不能把本轮说成单次16全绿。属于现有完整 MAIN 任务的同一控制安装链；本子任务未派发远端、未创建真实attempt。父已批准最小方案及分开真实Linux证据收口。

## 目标、范围与里程碑

仅修复 activation.prepare 将已经严格验证的 generation 原件闭包继续套用旧 TASK/PRIVATE 平层目录约束的矛盾。拥有该处局部范围接缝、新独立测试与日志；不改 generation、source policy、旧 plan/原件/输入，不访问服务器，不 build/commit。

1. 阅读真实调用及经验，冻结最小方案/BDD，交父审阅。
2. 真实 r7 输入和局部范围合同先 RED；固定原输入与原 source-policy 214 证据。
3. 使用本次已验证 bundle.inputPins 的完整 pin 精确成员关系，逐文件保持 verify_local_pin，最小 GREEN。
4. 必要旧范围与相关回归、默认 prepare 本机验证，冻结 helper/test SHA 交父。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。仅正式 generation 已验证闭包分支，任何缺失成员、路径/bytes/SHA变化或别名拒绝；旧分支规则保持。
- 是否从根因和长期维护角度解决：是。目录归属用于旧报告合同，完整已验证物理 pin 闭包用于正式代次合同，两者按明确 generation 模式区分，不把新闭包误当任意路径。
- 是否存在临时补丁或绕过：否。不开放递归 PRIVATE/TASK/主源目录，不修改原记录，不补造成功证据。

## 经验门禁

- Trigger：跨目录安装代次输入闭包与原件范围判断；纯本机 prepare 失败。
- Preflight check：按 docs/experience-index.md 路由阅读 release-agent-checklist 的活动回执历史保全/运行依赖闭包，核真实 r7 loader 已验证 bundle.inputPins、localInstallationPins 来源及 verify_local_pin 路径/别名验证；所有文本显式 UTF-8。
- Blocker：pin 不属于本次正式已验证闭包，原 bytes/SHA/路径漂移、别名；未进入真实行为前的环境/setup 问题不能算 RED。
- Verification：真实 r7 默认 prepare 在旧代码出现目标范围失败；临时真实文件局部测试包含合法外部闭包、错path/bytes/SHA/缺成员/别名与旧目录限制，随后必要回归。测试不宣称实际部署。
- Forbidden action：不修改 generation/source-policy/package、真实 r7 输入/原件、历史214证据；不远端、不生成真实 attempt、不构建/提交、不用任意目录白名单替代闭包。
- Evidence：父指定原 helper 121722B SHA ba46ae81fa20861c6a4c9221f80bcd86cbbd0e7e9eec18548d117e7c0ba1ac3b；后续独立 RED/GREEN 原日志与最终 SHA。

## BDD（实现前）

1. Given 正式 generation loader 已完成物理闭包核验且某 localInstallationPin 精确属于本次 bundle.inputPins，When activation 准备原件，Then 即使其位于主源/PRIVATE子目录/实际包路径也逐文件核验并接纳。
2. Given 路径看似在合法目录但完整 pin 不在该闭包，或 path/bytes/SHA任一改变，When generation 准备，Then 拒绝；不以同内容、同文件名或目录前缀替代成员关系。
3. Given 已绑定路径变成符号链接/别名或原文件内容漂移，When 逐文件验证，Then verify_local_pin 原严格规则拒绝。
4. Given 非 generation 旧模式，When 原件在 TASK 直接子文件层，Then 原合同接受；PRIVATE、TASK子目录/任意外部路径仍拒绝，即使人为提供额外 pins。
5. Given 真实固定59 r7输入，When 仅默认 prepare，Then旧代码在范围门禁RED，新实现不得在该门禁误拒；所有其它准入保持且不得派发远端或创建实际attempt。

## 待审最小方案

保持 loader 先成功返回的 bundle 为唯一 generation 授权依据。在选中代次分支逐项要求完整原 pin 为 bundle.inputPins 的精确成员，再使用原 verify_local_pin 检查物理文件；非 generation 继续原 parent 限制。只提取一个小型局部 helper（若测试需要）共用该判定，不能允许 caller 以任意 unvalidated list 选择 generation 分支。实际函数签名以读取当前代码为准，父审阅前不改实现。

已读实现：verify_local_pin 调用 file_pin，后者拒绝叶文件符号链接并核读前后 inode/size/mtime/ctime 以及 bytes/SHA；并不检查硬链接 nlink 或父目录 symlink。本次不扩展既有验证能力；只验证原支持的叶符号链接拒绝与完整闭包成员的路径别名拒绝，不声称覆盖所有物理别名。真实 generation loader 在当前本机路径拼写下生成并 _finish 逐 pin 重验闭包。

## 已实现与验证结果

- 仅原循环内替换范围判断：generation要求完整 `item in bundle['inputPins']`；非generation仍要求 `path.resolve().parent == Path(task).resolve()`；后续 `verify_local_pin(path,item)` 原样保留。不新增目录前缀/递归授权，不改generation loader及其它逻辑。
- 原始RED：11 FAIL/5 PASS，其中10项为预期行为RED（含真实r7 ORIGINAL_EVIDENCE_SCOPE），另1项叶symlink在创建时WinError1314，不计业务RED。完整原日志保留。
- GREEN：`test_main_program_control_generation_scope.py -k 'not leaf_symlink'` → 15 PASS/1明确deselected，33.23秒，exit0、无skip；实际r7默认prepare完整通过，输入pin保持、remoteDispatched=false且无真实attempt/rich/core产生。
- REGRESSION：原source-policy/activation/generation-activation/generation/environment/evidence-pins六文件 → 214 PASS，81.80秒，exit0、无skip；原父sourcepolicy214证明未修改，不冒充同一轮输出。
- 逆应用唯一scope hunk可重建原helper精确121722B/SHA ba46ae81fa20861c6a4c9221f80bcd86cbbd0e7e9eec18548d117e7c0ba1ac3b，证明sourcepolicy及其余逻辑字节保持。
- 最终helper121760B/SHA `ef070f77fd7c8f5753a5eead343d2e49e20e52e45cc4aabc5601f7e1d0726f69`；新测试6090B/SHA `2cb1267f8f2f947838948bc9e100112edcf2d3073cbba353f0a625603660d321`。
- 待父：仅叶symlink原节点实际Linux和独立defaultprepare/实际授权安装；本子任务无服务器、Docker、构建、提交动作。完整本机证据见 main-control-generation-scope-tdd-log.md。
