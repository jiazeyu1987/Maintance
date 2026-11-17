# 增量日志临时迁移过程支持

## Goal
修复六步重复发布后增量备份对临时迁移过程DDL的拒绝，完整保留原始日志与ROW范围验证。

## Milestones
- [x] BDD及失败复现
- [x] 最小生命周期范围实现及负向测试
- [ ] 真实MySQL回放、实际封包、实际全段严格审计
- [ ] 提交、安装、本轮增量与恢复验证、融合清理

## Expected Verification
同库零参数临时过程创建、ROW效果和删除通过；跨库、CALL、动态执行、未知语法及未闭合生命周期拒绝。源服务已恢复UP/HTTP200；禁止重提备份直到严格审计通过。

## 经验门禁
Trigger: FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN。Preflight check: 原失败终态、来源恢复、原父链与安装模块SHA、只读全段诊断。Blocker: 未知语法或验证失败。Verification: RED/GREEN/REGRESSION、真实MySQL与实际全段审计。Forbidden action: 不删事件、不改历史、不静默全量、不把诊断跳过当PASS。Evidence: 上级20261117-sixstep-repeat及私密binlog-scope-scan。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，定义临时过程生命周期与实际行事件范围合同。
- 是否存在临时补丁或绕过：否。

## Current Status
in_progress；Linux120项通过、真实MySQL导出回放通过，候选全段审计通过；待提交后专用构建与安装、实际安装全段审计及本轮备份恢复。开发worktree基线86f37989，保留未清理。
