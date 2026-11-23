# PQC巡检约束与发布链只读调查

## Current Status
completed

## 目标
定位测试Z/zhangfeihong将881MO083056加入活跃订单发生系统异常的迁移根因。用户提供的PATROL约束结论作为待核证据，区分当前事实与历史推断；不修改服务器数据或发布。

## 里程碑与验证
1. 核已发布固定源码、PQC枚举/SQL及manifest登记。
2. 只读核测试服真实表结构、约束、迁移账本与相关日志。
3. 给出根因、发布检查缺口及正式修复建议并记录结论。

三项均完成。结论及证据边界见findings.md；无产品修改、服务器写入或临时worktree。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，追踪业务合同和增量迁移。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：迁移及线上异常调查。Preflight check：按server-access读取测试58，核配置确定源码路径和已部署提交，先查迁移/manifest再查环境；SQL字段以真实DESCRIBE为准。
- Blocker：身份不符、凭据缺失、证据无法定位时停止对应结论，不猜测历史。
- Verification：源码、原包和真实约束/账本相互印证。
- Forbidden action：不重放SQL、不修改账本/约束、不执行订单写入、不把用户转述当独立核实。
- Evidence：execution-log及脱敏调查报告，私密原始日志不提交。前序正式发布任务completed。
