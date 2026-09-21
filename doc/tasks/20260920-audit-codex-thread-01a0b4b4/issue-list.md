# 备份恢复完整问题清单

## 最新复核：2026-09-21 16:57

最新提交为 `f742c4b37`，已构建并启动隔离后端。P01 独立报告消费、P03 Java/PowerShell 增量计划、P04 现场哈希指纹及 P02 先停写再快照均有实质修正，已确认 100 个相关 Java 测试通过。15:03 页面发起的新演练仍 running，16:53 的对象目录已有 94G/30467 个文件，没有受控恢复成功证据。

**P06/P02 仍有明确阻塞：首次保护快照失败后，同点重试只看到 marker/snapshotId 就跳过快照生成，未证明保护点完整，随后会继续覆盖数据库。** 必须区分 snapshot-ready 与只创建 marker 的阶段，并验证保护点后才复用；不得在部分恢复后重建并覆盖原保护点。此项须先关闭再放行“恢复数据”。

当前方法已有明显改善，但新演练终态、故障注入、真实增量链及最终集成收尾仍待验收。更早的清单和快照见下文，不能按旧状态否定本轮已完成的修正。

## 最新复核：2026-09-21 08:50

当前 worktree 已到 `3a245aabb`，新运行 Jar 已部署；下面 9 月 20 日的清单是历史基线，不应继续把全部项目视为未修改。

- P01：顺序错误部分修正；不可变 manifest 与演练状态分离未完成。
- P02：已有数据库和对象快照，但先快照后停写，跨存储一致性未闭合。
- P03：已有 base+增量重放，候选仍要求增量目录含完整 dump；实际 mysqlbinlog 也缺失。
- P04：新报告为 SHA-256 指纹，Java 候选仍是旧文本格式，当前严格比较必然不匹配。
- P05：停服/覆盖前完整性检查已实现，故障场景待验。
- P06：持久隔离与同点重试已实现，真实故障注入待验。
- P07：rollback mutex 遗漏已修正。
- P08：已改全目录 UNKNOWN 扫描。
- P09：最新真实 FULL 日志 UTF-8 与中文正常。
- P10：已改 File.Replace 原子替换，完整并发/中断验证待补。

原任务已归档中断，后续由“备份恢复 (2)”继续。昨晚演练已有 success 报告；今日 03:30 FULL 因保留失败，06:59 INCREMENTAL 因 mysqlbinlog 缺失失败，07:10 新 FULL 仍 running。受控恢复按钮仍未验收。

详见 verification-report.md 的“2026-09-21 08:50 复审”。以下为 2026-09-20 原始完整清单。

范围：本线程历次审查发现的去重汇总。核对时间：2026-09-20 22:38 +08:00；实现基线：整改 worktree `e20b77d50`，当前工作区干净。

结论：10 项待修复问题，8 项待验收事项。历史修复另列，不将其重复记为当前未修复。代码级缺陷不等于已发生数据事故；本审查未执行破坏性复现。

当前运行状态：页面 FULL 备份 `87da58cc-96e0-4b00-b631-f6b191071024` 已 succeeded，备份点 `20260920-171349`；页面恢复演练 `cb1cfa1f-48bc-49bc-8cdd-087b7bef9847` 仍 running，尚未完成“恢复数据”按钮闭环。e20b77d50 已部署到隔离运行态，尚未合入 int_main。

## A. 待修复问题

| 编号 | 级别 | 问题 | 影响/触发条件 | 修复与验证要求 |
| --- | --- | --- | --- | --- |
| P01 | P1 | 演练报告计算 manifestDigest 后又修改同一 manifest | 报告与候选的新哈希不一致，演练成功后仍无法作为有效受控恢复候选 | manifest 不可变，状态独立存放；验证完整“演练完成→重列候选→预览恢复”链路，不得取消哈希检查 |
| P02 | P1 | pre-restore 保护快照仅保存配置，无数据库/对象数据 | 覆盖失败后，该快照无法恢复覆盖前的数据 | 创建并验证数据库与对象共同一致的数据保护点，或证明为空目标；验证能恢复到覆盖前状态 |
| P03 | P1 | 受控恢复没有复用 FULL+增量链重放 | 演练支持增量，恢复候选却要求所选点自身含 FULL dump，恢复入口也只导入单个 dump | 统一恢复计划、base/parent/target 解析与重放；通过按钮验证中间及最新增量恢复点 |
| P04 | P1 | targetFingerprint 来自备份元数据，未真正绑定实时目标 | 同 IP 换机、schema/存储变化等不能由当前指纹识别；已有 IMAGE_TAG 检查不足以覆盖 | 预览和执行前获取现场身份及兼容指纹；变更即 STALE/阻断并重新验证 |
| P05 | P1 | 对象载荷完整性检查晚于数据库 DROP/导入 | 可能数据库已覆盖，才发现附件备份缺失/损坏 | 破坏性步骤前校验整个恢复集，固定执行计划与数据引用 |
| P06 | P1 | 部分恢复失败后只记 failed 并释放 mutex，未持续隔离目标 | 未完成恢复的环境可能再次接受回滚、启动或其他写入；unknown 门禁覆盖不到该 failed 状态 | 持久化恢复阶段和环境保护状态；明确远端写入者、处置及解除保护条件，不得失败后一律强启 |
| P07 | P1 | rollback-app 未加入恢复使用的互斥集合 | 数据恢复期间应用回滚可修改镜像并重启服务 | 备份、恢复、回滚等同目标操作共用环境级执行权；验证并发请求只允许一个获准 |
| P08 | P1 | UNKNOWN 保护只查询全局最近 200 条操作 | 后续记录含 blocked 尝试会把未处理 unknown 挤出窗口，保护未经确认便消失 | 用独立环境状态或全量未解决查询；覆盖超过 200 条、跨环境和重复 blocked 场景 |
| P09 | P1 | Windows runner 默认重定向产生非 UTF-8 日志 | 两份实际日志严格 UTF-8 解码失败；后端 running 列表按 UTF-8 读取，存在页面状态查询失败路径 | 执行器统一 UTF-8 输出；验证中文/错误输出、列表与页面日志；保留原异常证据，禁止静默替代编码掩盖 |
| P10 | P2 | runner 状态 JSON 没有原子发布 | 写了临时文件，却直接覆写正式 JSON；并发读取/进程中断可能得到不完整状态 | 同目录原子替换，并与其他写入者协调；验证轮询和中断不会暴露半份 JSON |

### 精确代码证据

以下路径均相对 `D:/IntRuoyiWorktree/backup-restore-remediation/backend/IntRuoyiBackend`，行号对应 e20b77d50。

- P01：`script/backup-ops/scripts/modules/UseCases/Rehearsal.psm1:173`、`:357`；`script/backup-ops/scripts/modules/Infra/DockerOps.psm1:1941`；`yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeOpsCandidateServiceImpl.java:366`、`:483`。
- P02：`script/backup-ops/scripts/modules/Infra/DockerOps.psm1:1155`；`script/backup-ops/scripts/modules/UseCases/RestoreData.psm1:270`。
- P03：`script/backup-ops/scripts/modules/Infra/DockerOps.psm1:993`、`:2006`；`script/backup-ops/scripts/modules/UseCases/RestoreData.psm1:278`；`script/backup-ops/scripts/modules/Infra/MySqlOps.psm1:1217`。
- P04：`script/backup-ops/scripts/modules/UseCases/Rehearsal.psm1:183`；`yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeOpsCandidateServiceImpl.java:454`；`script/backup-ops/scripts/modules/UseCases/RestoreData.psm1:77`。
- P05：`script/backup-ops/scripts/modules/UseCases/RestoreData.psm1:278`；`script/backup-ops/scripts/modules/Infra/MySqlOps.psm1:440`、`:565`；`script/backup-ops/scripts/modules/Infra/ObjectOps.psm1:1212`、`:1243`。
- P06：`script/backup-ops/scripts/modules/UseCases/RestoreData.psm1:111`、`:314`；`script/backup-ops/scripts/backup-ops.ps1:374`；`yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlCommandExecutorImpl.java:236`；`RuntimeControlServiceImpl.java:1079`（同一 service/runtimecontrol 目录）。
- P07：`script/backup-ops/scripts/backup-ops.ps1:338`、`:361`；`script/backup-ops/scripts/modules/UseCases/RollbackApp.psm1:143`；`yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlServiceImpl.java:73`。
- P08：同目录 `RuntimeControlServiceImpl.java:1095`、`:224`；`RuntimeControlOperationStore.java:65`。
- P09：同目录 `RuntimeControlCommandExecutorImpl.java:230`、`:254`；`RuntimeControlServiceImpl.java:414`。实证为隔离运行态 state/logs 下两份操作日志，分别在 UTF-8 byte offset 643/543 解码失败。
- P10：同目录 `RuntimeControlCommandExecutorImpl.java:223`。

## B. 待验收事项

这些是证据尚未闭合的验收项，不全部等同于已确认代码缺陷。

| 编号 | 验收项 | 当前缺口 | 通过标准 |
| --- | --- | --- | --- |
| V01 | 当前真实恢复演练 | operation 仍 running，无本轮最终 PASSED | 同一备份点的有效报告、operation、链摘要和目标证据一致 |
| V02 | “恢复数据”前端完整路径 | 尚未执行到恢复成功 | Playwright 登录→选包→点击→确认→进度/日志→结果；实际业务数据和对象一致 |
| V03 | 真实增量链及中间点恢复 | 无完整真实证据，且 P03 未修复 | 真实 FULL 与连续增量；恢复中间/最新点，覆盖对象新增、修改、删除及断链拒绝 |
| V04 | 中断/崩溃后的恢复责任 | detached 正常退出测试不能证明所有故障场景 | 控制台/runner 中断、SSH 超时、主机重启、远端子进程与目标隔离均有可验证处置 |
| V05 | 升级、降级、换机兼容矩阵 | 未完成原始需求中的运行态矩阵 | 支持路径实测通过；不兼容 schema/版本/硬件/存储变化明确阻断 |
| V06 | 大数据运行指标及持续调度 | 未形成完整 RTO/RPO、容量、停写窗口和调度周期证据 | 以实际数据规模记录指标和阈值，完成至少一个调度周期及最长链恢复 |
| V07 | 长期保留和独立恢复条件 | 本次无完整链保留、独立副本、恢复所需秘密/依赖的完整验收证据 | 清理不破坏可恢复链；独立故障域副本及恢复所需密钥/配置可用且受保护 |
| V08 | 主线集成与任务收尾 | 改动在独立分支及隔离运行态，未完成主线集成/收尾 | 合并结果验证、稳定入口加载正确版本、仅清理任务资源、恢复稳定控制台路径并完成记录 |

## C. 历史问题的修正/改善状态

“实现已修正”仅代表该缺陷代码已修改，不替代 A/B 两节的最终验收。

| 编号 | 历史问题 | 最新状态 |
| --- | --- | --- |
| H01 | INCREMENTAL 无条件删除 FULL 父链和 object-store | e00d22cc7 已分流，代码级修正；完整增量恢复仍见 P03/V03 |
| H02 | FULL 清理全部日期备份目录和共享对象仓库 | e20b77d50 已缩至当前 `.creating` 并校验归属，广泛删除缺陷已修正 |
| H03 | 长任务被 Java 2 小时等待强杀 | 已改 detached runner；并不代表中断全闭环通过，仍见 P06/V04 |
| H04 | 大 dump 完整性校验仅 60 秒 | 已改为 7200 秒，相关定向测试通过 |
| H05 | 镜像 READY 输出带字面量换行被误判 | 已规范化，代码修正且后续演练越过该阶段 |
| H06 | 转义函数不可见、远端文件读取函数未导出 | 已补模块函数/导出及相关测试；整体证据协议仍见 P01/P04 |
| H07 | 陈旧重启样例、MinIO 容器参数缺失、OnlyOffice 校验顺序 | 已修正并有此前测试服官方重启成功证据 |
| H08 | mysqlbinlog 缺失在停服之后才发现 | 已在增量停服前检查工具，实际增量链能力仍待 V03 |
| H09 | 只检查源代码字符串、靠整轮恢复发现模块问题 | 已增加实际调用及失败路径测试；还需跨模块最终候选与事故路径回归 |
| H10 | 共享主工作区反复构建重启 | 已使用独立 worktree、隔离运行态；主线集成与收尾见 V08 |
| H11 | PowerShell-only 修改却重新构建 Java | 已明确加载边界；e20b77d50 确有 Java 变化，本轮构建有依据 |
| H12 | 失败报告与 operation 长期 running | 增加日志收束及 runner 写终态，部分改善；旧记录现场收束受 P09/V04 等影响，不能标记完全关闭 |
| H13 | 错误直达路由造成 404 | 已确认并使用 `/infra/monitors/runtime-control`，真实按钮工具记录存在 |

## D. 不应继续作为违规/缺陷的事项

- 用户已授权真实测试服备份恢复，并于 21:05 明确允许本次使用“芋道源码”租户；不得沿用旧登录/租户 blocker。
- 已核对真实前端按钮触发，不能继续声称未通过页面发起备份或演练；只是受控恢复尚未完成。
- 存在本机备份/恢复 mutex，不应说“完全没有锁”；已确认的是 rollback-app 漏入锁范围，跨主机/发布统一租约仍需核验。
- 数据库恢复存在 DROP/CREATE，主对象恢复使用 --remove，没有证据据此认定必然残留旧表/对象。
- 本轮审查没有证据说明已经发生数据丢失；明确的是放行前应关闭的代码与验证缺口。

## 推荐执行顺序

先让当前演练安全收束并保留证据；随后集中修复 A 节，不通过重复昂贵恢复来逐个发现局部错误。先验证证据与候选合同、完整载荷和保护点、并发与失败隔离、UTF-8/原子状态，再完成 B 节真实按钮及故障场景验收。未满足受控恢复门禁前，不应点击“恢复数据”。

详细逐轮证据：[verification-report.md](D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260920-audit-codex-thread-01a0b4b4/verification-report.md)。


## 最新复核：2026-09-21 21:38

- `eb31c41a...` 演练已 succeeded；`77e560145` 保护快照重试门禁已提交，`b5762701d` 修正 rehearsal 显式 `TargetEnvironment=test`，隔离后端已启动新 Jar。
- 尚无新版本 `CONTROLLED_RESTORE AVAILABLE` 证据，尚未成功执行“恢复数据”。
- P06 仍只有合同测试，真实故障注入待验；operation JSON 中文 summary 仍有乱码，日志 UTF-8 已正常。
