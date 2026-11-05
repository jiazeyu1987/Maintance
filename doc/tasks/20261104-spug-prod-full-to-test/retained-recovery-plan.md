# 保留失败记录的显式续恢复方案

## 当前真实故障与范围
History352 的原 worker 已 exit1，原结果 FAILED_RETAINED/RESTORE_TYPEERROR；测试服 .58 同一数据库 UUID 的应用库表数为0。MinIO、后端、前端停止；Redis、MySQL仍运行。不得启动空库主程序，也不得直接删锁重试。正式服新 FULL 已成功且归档完好。

本方案继续用户已授权的“本轮正式新全量包，经 Spug 恢复到测试服”及组件安装范围。只处理同一 .58 MAIN 与同一新 FULL，不触及正式业务数据、不更换实例、不使用旧点。授权文本及本计划摘要记入新的操作审计回执。

## 正式机制
1. 先修复 SAFE包注入接口和破坏性SQL mutation审计；真实包组件RED/GREEN及受影响回归通过，从已提交目标在本次专属临时发布worktree构建，保留旧引擎和配置代次。
2. 增加显式本机运维 CLI：只允许已明确失败并退出、非UNKNOWN、已有replacement-intent且同一原目标的保留操作。核原结果/退出/请求/预约pin、无原进程、严格容器/网络/存储/DB UUID及目标停写、预期表数0。操作受原物理目标锁及宿主预约锁保护。
3. CLI只追加 `RetainedReplacementRecovery/v1` 准许回执、真实目标观察及宿主预约释放回执；保留原FAILED_RETAINED结果、claim和所有历史字节。释放当前指针须与原预约逐字段一致，不能影响其它操作。任一步失败不继续。
4. 新准许只允许同一来源、同一备份点、同一目标配置。下一次真实Spug恢复由UI生成新operationId，恢复器在写入前消费准许并追加新编号关联。未消费过期、不同点、不同目标、原pin变化、并行任务均拒绝。新操作不成功仍保留，新失败不自动解锁。
5. 通过正常Spug页面再次确认同一新FULL→.58 MAIN并提交一次。验证真实恢复终态、数据库/对象版本/Redis一致性、原容器镜像与UUID、后端health、前端HTTP及实际登录后用户管理页面。

## BDD 与设计约束
- Given失败结果仍FAILED_RETAINED且原进程退出；When显式运维准许追加并经Spug确认同一恢复；Then原结果不改，新编号可追踪，原锁仅按原预约释放，异点/漂移/未知/活动操作不能重试。
- Given新操作又失败；When刷新或重复查询；Then不自动再试、不释放新保留。
- 是否引入fallback/降级/吞异常：否。显式失败恢复是独立审计路径，不改变正常失败保留规则。
- 是否从根因和长期维护角度解决：是。构建产物接口合同与受控失败恢复均有实际组件验证。
- 是否存在临时补丁或绕过：否。不删失败claim、不重写结果、不复制新stateRoot绕开保留，不直接API/SQL执行数据恢复。

## 经验门禁
- Trigger：真实覆盖恢复已清库后失败。
- Preflight check：原操作明确退出，原pins完好，实际同一目标严格身份与停写、DB表数0；本机修复与回归，提交快照、临时发布隔离，执行前日志GREEN。
- Blocker：UNKNOWN、活动进程、目标/配置/pin漂移、其它预约、无明确既有实际恢复授权。
- Verification：追加准许/释放/消费回执、原失败字节不变、真实Spug新操作及完整最终验收。
- Forbidden action：删锁/claim、改FAILED为成功、起空库主程序、替代目标/旧点、API绕过页面、停止无关服务。
- Evidence：restore-terminal-record.json、failed-restore-data-state.json、本机回归日志、新受控恢复回执及最终实际恢复证据。
