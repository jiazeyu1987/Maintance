# 排产员增加排产工单删除权限

## Task Goal

通过正式、可重复执行的数据库权限迁移，为 `mes_scheduler/排产员` 角色增加 `mes:pro-schedule-order:delete`，应用到测试服务器并通过 `zhaojie` fresh 登录确认删除按钮可见；不扩大其它角色权限，不执行实际删除，不操作正式服或审查服。

## Milestones

1. [completed] 完成权限、迁移、数据库、worktree 和测试服写入前置检查，冻结变更范围与回滚方案。
2. [completed] 先补 RED 合同测试，证明正式迁移尚未给排产员授权删除权限。
3. [completed] 新增幂等前向迁移与只读 target preflight，完成 GREEN 和迁移策略回归。
4. [completed] 在测试服执行精确授权，核对只有目标角色绑定新增，并精确检查权限缓存。
5. [completed] Playwright 使用 `芋道源码/zhaojie` fresh 登录，确认删除按钮可见但不点击。
6. [blocked] 提交任务变更并记录证据已完成；主工作区脏状态阻塞安全融合和 worktree 收尾。

## Expected Verification

- 新迁移只解析活动 `mes_scheduler/排产员` 与唯一活动 `mes:pro-schedule-order:delete` 菜单，前置不满足即失败。
- 迁移重复执行不产生重复有效绑定；非目标角色和用户角色绑定保持不变。
- 回滚 SQL 能精确删除本迁移新增的角色菜单绑定，不影响迁移前已有绑定。
- 测试服 `zhaojie` 权限响应包含 `mes:pro-schedule-order:delete`，排产工单页面至少显示一个删除按钮。
- 不点击删除，不修改工单数据，不操作正式服、审查服或备份服。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；角色、菜单或唯一性前置不满足立即失败。
- `是否从根因和长期维护角度解决`：是；使用新的前向迁移固化角色权限，而不是只在测试库手工插入一次。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- 权限变更必须按 `tenant_id + role.code` 和菜单 `permission` 解析，不复制环境相关自增 ID。
- 先记录目标账号全部有效角色、目标菜单与现有绑定作为 RED；不得绑定管理员角色或扩大非目标角色权限。
- 必须以当前真实库 `DESCRIBE` 和活动数据为准设计 SQL；迁移需幂等、可审计、可回滚。
- 测试服高风险写入前必须记录 `GREEN: experience-preflight -> PASS`，且只允许目标主机 `172.30.30.58`。
- 权限缓存只能精确刷新目标用户/角色相关缓存，不得清空全库 Redis。
- 最终必须由 Playwright 使用目标账号 fresh 登录验证按钮可见；不得执行删除动作。

## Current Status

blocked

## Final Verification

- 测试服两个活动排产员角色各获得一条有效删除权限绑定，非目标角色与用户角色哈希不变。
- `zhaojie` fresh 登录权限响应包含目标 permission，排产工单页 20 行显示 20 个删除按钮。
- 未执行删除、未扩大其它角色、未操作非测试环境。

## Blocker

- 应用分支已推送，但 `E:\IntRuoyi` 主工作区有其它任务 staged/dirty/untracked 改动，`task-closeout-cleanup` preview 拒绝 `ff-only` 融合。
- 测试服权限已经生效并完成真实页面验证；剩余影响只限主线融合、临时证据清理和 worktree/slot 42 删除。
