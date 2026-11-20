# 测试服发布与菜单修复

## Current Status
completed

## 目标和授权
用户要求发布到测试服务器；承接已授权下一次发布修复菜单。仅172.30.30.58，本轮禁止mark-tested/promote-prod/promote-backup。以前序已完成代码更新46c87dd2c为起点，核当前HEAD后确定本次已提交输入。原工作区未提交改动不入包。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，新增不可变前向菜单迁移、隔离验证、发布最终状态验收。
- 是否存在临时补丁或绕过：否，不改旧SQL/账本或全表覆盖。

## 经验门禁
- 先按server-access/login-access/release-backup-restore和next-release-menu-repair执行；仅新专用worktree构建测试发布，固定提交，操作锁及恢复依据必须明确。
- 菜单SQL先读真实DESCRIBE及身份、父链、角色套餐；新增迁移与target-preflight和release-sources登记一起交付，保留900120根级。
- BDD/TDD及真实隔离MySQL验证包括旧态修复、幂等、冲突拒绝和回滚；不以静态检查冒充实际迁移。
- 服务器写入/菜单修改/worktree合并清理前记录experience-preflight PASS；密码只取现有私密来源，不入日志。
- 验收核operation、manifest、IMAGE_TAG、双镜像tag、UP/200、页面版本与变更说明、菜单及权限；只读admin页面验证，任何测试写入仅测试租户。
- 收口先ready_for_closeout，新提交合回int_main并验证后删除本任务worktree、恢复本任务控制台，其他任务资源不动。

## 里程碑
- [x] 核已提交输入、测试目标与发布入口，创建本次worktree。
- [x] 完成菜单修复迁移和必要验证并提交（152a084c3，已合回int_main，合后4项真实MySQL及2项Node验证通过）。
- [x] 同releaseTag build-release及publish-test成功。
- [x] 测试服运行态、菜单、页面与版本验收（页面PASS_WITH_OBSERVATIONS，详见verification.md）。
- [x] 合回/清理/记录收口。

## 当前执行
build-release JOB-8e4a355562及publish-test JOB-363a294001均succeeded，版本2026-11-20-14-42-40；新增菜单修复和注册证通知迁移均APPLIED。运行态UP/200、镜像和IMAGE_TAG一致、正常模式；真实菜单页面通过。原综合预检审查服旧配置失败保留，不影响本次目标测试服专用预检通过。两处自有worktree已验证清理；应用修复新提交已合回int_main，slot9已释放，其他分配不变。未启动或改变本机控制台，原执行器PID43352/稳定source路径保持；主区原30项未提交内容保留。正式服未在本轮发布，菜单修复待正式发布时执行。
