# 备份恢复六个里程碑文档审查报告

## 审查结论

文档审查与修订通过。原文的六个里程碑顺序仍然成立，但首轮审查发现若干会导致实现误判、恢复循环或数据风险的问题，均已在正式文档和关联灾备设计中修复或明确标为实施 blocker。

本报告的“通过”仅表示文档合同和审查质量通过，不表示测试服务器已经完成实时备份、恢复或灾备放行。

## 首轮问题与修复

| 编号 | 严重度 | 首轮问题 | 修复结果 |
| --- | --- | --- | --- |
| R1 | P1 | `COMPLETE`、`PASSED` 和可发起首次演练混为一个候选状态，形成循环依赖 | 拆成“演练候选”和“受控恢复候选”；`COMPLETE + NOT_RUN` 只能演练，目标绑定 `PASSED` 才能受控恢复 |
| R2 | P1 | 不可变 manifest 混入演练状态、兼容结果和保留状态，导致每次演练都要重签载荷清单 | 拆分不可变 manifest/detached signature 与独立候选目录、演练证明、兼容证明和保留状态 |
| R3 | P1 | 隔离恢复只描述独立数据库/目录，没有禁止 MQ、定时任务、Webhook、通知和外部写入 | 增加独立 Redis namespace、网络 allowlist、禁用/隔离外部副作用、队列策略和副作用验收 |
| R4 | P1 | 覆盖恢复可能被实现成原地覆盖，失败后留下半恢复环境；源账号权限边界不足 | 默认使用版本化目标/快照后切换；定义 `REPLACE_EXISTING`/`REBUILD_EMPTY`；源系统只追加，受保护副本由独立权限维护 |
| R5 | P1 | RPO/RTO 未说明数据库和对象共同口径，也没有区分封存点年龄与已证明恢复点年龄 | 增加共同恢复点 RPO、目标/当前/已证明 RPO 指标，并分离演练 RTO 与覆盖 RTO |
| R6 | P1 | 没有充分约束 binlog 提前 purge、对象扫描期间修改和增量失败后的补链规则 | 增加日志保留、对象版本/受保护副本、缺口阻断、新 FULL 和连续性验收 |
| R7 | P1 | 当前运行控制台静态逻辑要求 `PASSED`，无法支持首次 `NOT_RUN` 隔离演练 | 明确记录为 M4 实施前置 blocker，要求 `candidateType=REHEARSAL/CONTROLLED_RESTORE` 或等价服务端分层 |
| R8 | P2 | 权限、四眼确认、发布/迁移/清理并发和异常终态不完整 | 增加 RBAC、重新认证、独立批准、共享环境租约、`UNKNOWN` 和取消语义 |
| R9 | P2 | 镜像、恢复工具、历史 key、DCC、配置、Redis/MQ 和法规归档边界不完整 | M1 数据分类、独立 escrow、不可变 artifact、DCC 校验、Redis/MQ 策略和灾备/法规保留分离均已补齐 |
| R10 | P2 | 候选目录或 operation 元数据损坏时缺少重建路径 | 增加从独立仓库签名 manifest、payload inventory 和仓库保留元数据重建候选目录的要求 |

## 要求覆盖检查

- 六个且仅六个主里程碑：通过。
- M2 实际规模 FULL + 隔离全量恢复：通过，且明确不能以文件生成代替恢复。
- M3 三个真实增量点、数据库/对象增删改、整链恢复和损坏链阻断：通过。
- M4 两个页面入口、三种后端语义动作、候选分层、异步 operation、互斥租约和危险操作确认：通过。
- M5 升级、降级、同架构换机、跨架构、路径/域名/证书/外部端点变化和不兼容阻断：通过。
- M6 调度、依赖图保留、最大链限制、独立副本、目录重建、RPO/RTO 监控和故障注入：通过。
- 数据库与对象共同恢复点、对象 tombstone、binlog 连续性和对象版本一致性：通过。
- secret 不入备份集明文、历史 key 可恢复、独立镜像/工具 artifact 和脱敏审计：通过。
- 隔离演练外部副作用阻断和真实数据访问保护：通过。
- 当前静态方案与实时服务器状态区分：通过。

## 验证证据

- PASS：灾备验证器 self-test。
- PASS：`docs/recovery/backup-disaster-recovery.md` 通过灾备证据验证器。
- PASS：两份正式文档 UTF-8 回读。
- PASS：两份正式文档代码围栏成对，未发现行尾空白。
- PASS：六个主里程碑标题数量为 6。
- PASS：关键合同关键词检查：候选分层、`NOT_RUN`、目标模式、`UNKNOWN`、共同 RPO、已证明恢复点年龄、隔离副作用、独立副本和无 blocker 放行条件均存在。
- PASS：关联设计文档已同步候选分层、状态枚举和 BDD 场景。
- PASS：关联设计文档已进一步同步 freshness 与业务 RPO 的区分、`REPLACE_EXISTING/REBUILD_EMPTY` 和 `FAILED/UNKNOWN` 终态。
- PASS：长期经验合并到既有 `E:\IntRuoyi\docs\release-backup-restore.md`，并更新维护仓经验索引路由。
- PASS：`git diff --check` 对已跟踪请求日志无 whitespace error；未跟踪正式文档通过独立行尾空白检查。

## 仍然存在的实施前置条件

以下不是文档遗漏，而是必须在真实实现/演练前完成的 blocker：

1. 对当前运行控制台实现候选分层，确保 `NOT_RUN` 备份可以进入隔离演练而不能直接覆盖。
2. 由业务 owner 批准共同恢复点 RPO、演练 RTO、覆盖 RTO、保留周期和法规归档是否适用。
3. 在实际几百 GB 规模完成数据库方案、容量、停写、最长链和恢复耗时实测。
4. 建立完整 writer registry、隔离槽位和外部副作用 allowlist。
5. 验证独立故障域备份仓库、源/仓库权限分离、历史密钥 escrow、镜像/工具 artifact 和候选目录重建。
6. 用真实服务器和真实数据完成 M2-M6 证据；本次未执行远端操作，不能把本文档审查结果当作恢复成功。

## 复审补充

复审发现并修复关联设计文档中的三处旧口径：配置 freshness 阈值不等于业务 RPO；空白/已毁目标不应强制伪造 pre-restore snapshot；恢复终态应使用 `FAILED/UNKNOWN`，不能使用含义不清的 `FAIL`。修复后重新通过 UTF-8、结构、关键合同和灾备验证器检查。

## 相关文件

- [优化后的六个里程碑文档](../../docs/recovery/backup-restore-milestones.md)
- [测试服务器备份恢复总体设计](../../docs/recovery/backup-disaster-recovery.md)
- [任务记录](task.md)

## 收尾验证

- PASS：task-closeout cleanup preview/apply。
- 保留：`task.md`、`execution-log.md`、`verification-report.md`。
- 删除：0 个文件。
- Worktree：主工作区，无合并或删除动作。
- 最终状态：`completed`。

关联设计文档复审后的最终状态：`completed`；closeout preview/apply 第二轮通过，删除 0 个文件。
