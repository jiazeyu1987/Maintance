# 历史目录重复读取重构

## Current Status

in_progress。原目标不变；四控制服务已切换，资源与 selectors 尚未安装。先修复真实目录查询超出原请求期限的问题，再进入原安装验证链。

## 目标与证据

正式服原控制 `/selections` 原生 HTTP 实际 11.043 秒返回 200/1323 字节，超过 Spug 固定 10 秒期限。真实 cProfile 为 14.193 秒，其中 archive_references 13.001 秒、两次 bind_archive_chain 11.495 秒，52 次 read_document、227 次 pinned_read；见 source-control-native-latency-diagnostic-r1.json 与 source-control-native-selections-profile-r3.json。r1/r2 profile 调用的导入路径错误原件保持，不属于业务测试失败。

长期方案为请求内消除重复的目录扫描、完整读取和 JSON 解析，维持所有来源、身份、链前缀、不可变索引、元数据 SHA、隔离标记、路径和最终稳定性检查。不使用跨请求陈旧缓存，不修改原备份，不延长产品 HTTP 期限，不用静默跳过换取成功。具体实现在 RED 场景后决定。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；针对真实调用图重复工作，按请求验证和结束复核，保持外部结果及安全拒绝。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger：历史恢复目录真实扫描使 Spug 十秒请求期限超时。
- Preflight check：固定原始失败、实际 HTTP 时长与 profile；只修改本任务拥有的目录解析模块和相应测试；按 AGENTS.md 重构使用 Subagent-Driven Development。
- Blocker：来源、隔离标记、目录集合、原件 SHA 或路径变化不可检测；缺失真实回归；仅凭夹具耗时宣称生产通过。
- Verification：BDD -> RED -> GREEN -> REGRESSION；变更/替换/新增重复点/隔离标记必须拒绝；真实部署后仍以固定十秒 HTTP 和完整资源观察为准。
- Forbidden action：不得扩大超时、删除历史、改原件、跨请求缓存未复核数据、吞异常、弱化元数据或完整恢复校验。
- Evidence：上述两个 JSON、本计划、execution-log.md 和新测试日志。

## BDD 与里程碑

1. Given 同一请求选择两个共享目录或父点的历史备份，When 枚举完整目录，Then 每份相同元数据只解析一次，目录发现不随点数重复；全部原 SHA 和链约束保持。
2. Given 目录枚举期间有原件内容/文件身份/目录集合变化或新增重复 backupId，When 请求完成，Then 显式拒绝，不能返回旧缓存成功。
3. Given 保留的 quarantine 标记或错误父前缀/来源身份，When 请求枚举或绑定恢复点，Then 保持原错误拒绝。
4. Given 下一次独立请求发生，When 原件已有变化，Then 重新读取并验证，不复用上次请求缓存。

预期验证：先新增失败测试并保存 RED，最小实现后同集 GREEN，既有归档来源、目录、安装包和控制测试回归。实现通过后单独提交；从新干净专属发布 worktree 构建，补齐新配置/包绑定与真实安装验证后才能宣称运行态修复。

## 已发现的其它完整目标缺口

13 组真实历史元数据诊断已保存 archive-program-contract-evidence-r3.json。演练库 rehearsal 的 lab_* 数据与主程序 ruoyi-vue-pro 范围不同，不能仅按 application 标签认定兼容。审查服 lightweight 增量 smallapp-84563aceae404c18a96a47ae336c4e5a 的三个载荷元数据与 manifest SHA 不同；诊断原件和实际摘要保持，不修改清单，不假称该备份已可恢复。完整目标仍需核查和处理这些历史点。
