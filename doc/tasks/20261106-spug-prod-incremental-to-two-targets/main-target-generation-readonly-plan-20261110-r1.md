# 三服 MAIN 保全登记前的只读代次核对

## Current Status

completed（仅本次只读核对）。三服均保持原 initial READY sequence 0，无成功程序代次；.57 原 capture 一项，.58/.59 为空。结果与原生诊断见 `main-target-generation-readonly-reconciliation-20261110-r4.json`。r1/r2 载体失败及 r3 Windows SSH 关闭诊断保持原样；不等同于后续配置安装通过。沿用用户对三服只读检查的明确授权，没有写配置、获取业务写锁、启动 capture、备份或恢复。

## 目标与里程碑

1. 按已成功 activation 的精确 path/bytes/SHA 验证三服 owner/control 原件，读取实际结构及声明的引擎位置。
2. 使用该已登记引擎的只读 generation/epoch reader，区分仍为初始 READY 与已经发生成功程序代次；记录实际 capture 映射与证据 pins。
3. 为后续静态保全配置计划提供事实前提；有代次时阻断直接追加 capture，不实现假设性 adoption。

## 预期验证

独立保留每服的输入程序、原始 stdout/stderr、真实退出码、耗时及解析结果；远端输入原件读取前后身份和 SHA 不变。失败按对应目标记录，不把另一个目标结果补到失败目标。

## 经验门禁

- Trigger：三服目标保全登记设计。Preflight check：已读迁移后的 server-access、release-backup-restore、PowerShell UTF-8 门禁；主机严格为 .57/.58/.59，owner/control pins 来自已成功 activation。Blocker：原件不符、缺失或无法验证实际引擎/epoch 时，只阻断对应登记。Verification：原生终态及精确输入输出 pins；原件前后不变。Forbidden action：重启、写数据库/配置/epoch、改 NAS/fstab、以旧状态冒充实时结果。Evidence：本计划、后续只读观察记录及 execution-log。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，先确认真实代次条件，再确定必要配置方案。
- 是否存在临时补丁或绕过：否。
