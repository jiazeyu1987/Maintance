# 已闭合旧版 MAIN 续办记录兼容

## Current Status
in_progress

## 目标与根因
701b442实装后，真实.58 selections返回500/SMALLAPP_KEYERROR。实际堆栈为validate_clearance无条件读取mainProtectionRecoveryPin；两条2026-11-05旧RetainedReplacementRecovery/v1在该字段引入前已消费，原MAIN/v1目标配置与当前相同、无归档/发布端口保护配置或保护日志。原消费链af9 -> 91cc -> 6cb实际最终SUCCEEDED，旧失败和消费链均不可修改。当前368新clearance已正式签发且全部校验通过，尚未消费，业务保持停写。

## 正式方案与设计约束检查
- 是否引入 fallback/降级/吞异常：否。显式识别已闭合的旧MAIN/v1历史合同，不接受未消费、未闭合、v2、有任何新保护配置/记录或配置漂移的缺凭证记录；不将缺字段笼统当可用。
- 是否从根因和长期维护角度解决：是。版本兼容校验保留旧原件，核当前和原始配置、全部既有pins、同点同目标消费链及最终真实成功/exit0，并有循环和深度拒绝。当前新流程仍产生并验证完整保护证明。
- 是否存在临时补丁或绕过：否。不改历史JSON、不删除失败、消费或锁，不忽略错误、不放宽实际恢复验收。

## BDD与里程碑
- Given 两条原MAIN/v1旧clearance均已消费且同点同目标链最终原生SUCCEEDED；When 新控制加载目标；Then 逐项核其合同并允许历史读取，旧字节不变。
- Given 未消费/循环/过深/跨点目标/配置变化/保护日志或配置存在/后续未知或失败未闭合/原始pin变化；When 加载；Then 明确拒绝，不发布目标。
- Given 本次含mainProtectionRecoveryPin的新clearance；When 加载；Then 原完整保护验证保持。
1. [x] 实际只读错误、旧配置/消费链固定。
2. [x] Linux独立RED后27项GREEN、七进程244项回归全部PASS；两服真实历史只读候选检查PASS。
3. [x] 限定4份文件提交7c5f0573e7e1ed7a54e42dbb614cb6e1f0a0534b，专属release-7c5f057干净构建127文件SHA/编译PASS；保留四个旧构建，最终按五个精确清理。
4. [x] 04:44:42Z .58 r3实装PASS，真实新进程及04:46 HTTP selections均通过；clearance/停写/459原容器/共享挂载及2842失败原件完整SHA保持。
5. [ ] 新鲜准入及真实UI单次提交后，继续两服完整恢复验收。

## 经验门禁
Trigger：升级控制读取旧已消费MAIN/v1续办记录。Preflight check：固定真实旧版本/当前配置相等、旧clearance/消费关系和终态；先RED。Blocker：任一原件、配置、消费关系、保护或最终成功证据无法核对。Verification：封包真实入口、严格负向用例、真实目标selections及原件保持；本次实际恢复另验收。Forbidden action：改写旧记录、删除锁或兜底放行、用测试成功替代实际恢复。Evidence：allocator-selection-native-error-summary.json、allocator-historical-claims-58.json、allocator-legacy-clearance-contract-58.json和execution-log.md。
