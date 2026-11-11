# 目标覆盖前保全配置图

## Current Status

local_verified；纯配置生成和 Redis 合同回归通过，尚未安装或业务恢复。审查服容量不足单独阻塞该服运行准入，不降低限额。

## 目标与里程碑

- 从当前已验证目标、程序策略、原凭据字节和显式预算生成完整不可变配置图，结果仅 BOUND_NOT_INSTALLED。
- 已完成：BDD、RED、Windows GREEN、隔离 Linux GREEN 和原 Redis 入口回归。
- 待完成：正式新包、目标角色升级、真实 prepare/安装与 Spug 页面验收。

## BDD

- Given 已验证目标五服务、epoch、原配置及凭据 pins；When 构造保全配置；Then 目标物理身份保持，数据库日志模式和 SMB 凭据格式必须显式提供，输出源身份、对象/派生数据、采集、私有凭据、独立读回、仓库及策略的完整 pins。
- Given 物理 targetId 与注册 targetConfigRef 不同但各自真实有效；When 构造；Then 保持两者原语义，不以字符串相同冒充物理绑定。
- Given 来源范围、epoch、服务、凭据、认证、预算、日志模式、SMB 格式或对象引用有误；When 构造；Then 明确拒绝，不写文件、访问网络或隐式填默认值。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。格式、日志模式和原件都显式绑定，产品异常转换为明确错误且停止。
- 是否从根因和长期维护角度解决：是。复用正式采集值合同，按已验证物理目标生成每服独立配置，不复制来源或验证目录充当生产配置。
- 是否存在临时补丁或绕过：否。返回配置不赋予文件系统、SMB、运行态或恢复准入。

## 经验门禁

- Trigger：三服目标尚无覆盖前保全策略、不同版本 Redis 登记、旧电脑路径迁移。
- Preflight check：真实全部原件/pin、五服务、数据库 UUID/GTID、对象范围、显式预算及精确包来源；运行安装前另核新鲜健康、锁、容量和挂载。
- Blocker：未知或漂移输入、认证/格式不明、缺少正式包或实际空间不足，只阻断对应阶段。
- Verification：先 RED，再 Windows/Linux GREEN；正式包与真实业务验收分别记录，不相互替代。
- Forbidden action：不改目标业务数据、NAS/fstab、旧历史/pin，不将 BOUND 标为安装，不以单元测试宣称恢复通过。
- Evidence：execution-log.md、main-target-provisioning-readonly-r1.json、PRIVATE 原始测试和只读报告。

## TDD 证据

- RED：初始 17 项因模块缺失失败；最小实现后 17 PASS。
- RED：显式 database_log_mode 新参数缺失；实现后 18 PASS。
- RED：真实物理身份不同的正向场景暴露错误相等要求，2 FAIL/16 PASS；修正为分别绑定后 18 PASS。
- RED：显式 smb_credential_format 新参数缺失；实现严格两种格式解析、重复字段拒绝及原凭据复制后 19 PASS。
- GREEN：Windows 19 PASS/native0/0.26秒；隔离 Linux 19 PASS/native0/0.25秒，源352件保持、固定镜像与12轮子校验通过、容器移除、stderr0。快照6563840B/98aade8aa530407db42b06fc695b50acd3678c63509da2647a5ff5fd4d1e4564。
- REGRESSION：父 Windows 组合实际53 PASS/native0/0.44秒（生成19+Redis合同31+原capture_redis_auth3），不把它称为全部旧Redis5项。此前误用不存在的 test_minimal_redis_snapshot.py，pytest无节点/文件不存在，未作为通过；后续命令明确保存原生退出码。
- Redis 产品入口的完整 Linux54项证据见 target-capture-redis-contract-tdd.md；不重复累计通过数。

## 只读核验与限制

- 三服原11份文档、五容器身份和排序挂载、真实SQL字段、UUID/GTID及Redis认证通过；GTID均OFF，因此新配置显式FILE_POSITION。凭据正文仅PRIVATE。
- 审查服可用131378769920B；原恢复预留120259084288B、新保全预算68719476736B和余量2147483648B，合计191126044672B，缺59747274752B。不得用降低预算冒充空间通过。
- 维护仓 docs/worktree-restrictions.md 为已核实主程序规则的维护仓适配入口。原文9104B/SHA6764203a48b74e98f780cc9d2549c84d7a708592ca021bf5e69a1b68ace4a3ac，仅摘要适用规则，不把主程序端口登记强加给纯资源构建。
