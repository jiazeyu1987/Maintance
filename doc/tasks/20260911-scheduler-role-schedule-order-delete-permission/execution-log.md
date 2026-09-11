# Execution Log

BDD: 排产员获得排产工单删除权限 -> Given 活动排产员角色和唯一活动删除菜单存在 / When 正式权限迁移执行 / Then 每个目标排产员角色获得 `mes:pro-schedule-order:delete` 且其它角色权限不变。

BDD: 迁移前置异常立即阻断 -> Given 目标角色缺失、重复或删除菜单缺失、重复 / When 迁移或 target preflight 执行 / Then 明确失败且不写入任何角色菜单绑定。

BDD: zhaojie fresh 登录看到删除按钮 -> Given 测试服迁移成功并精确刷新权限缓存 / When `芋道源码/zhaojie` 重新登录排产工单页 / Then 权限响应包含删除 permission 且页面显示删除按钮，但测试不点击按钮。

RED: test-server-current-permission -> FAIL, `zhaojie` 当前权限响应不含 `mes:pro-schedule-order:delete`，排产工单页加载 20 行但删除按钮为 0；测试服菜单存在且启用，目标账号全部有效角色均无此绑定。

GREEN: experience-preflight -> PASS, 已读取数据库迁移合同、角色权限差异同步门禁、远端危险按钮诊断门禁、测试服访问规则、PowerShell 编码规则、worktree 限制与收尾规则。变更只允许 `mes_scheduler` + `mes:pro-schedule-order:delete`；使用新前向迁移、唯一性 fail-fast、幂等写入和精确回滚；禁止修改已发布旧迁移、绑定管理员角色、清空 Redis 或操作非测试环境。

GREEN: worktree-preflight -> PASS, 目标路径固定为 `D:\IntRuoyiWorktree\20260911-scheduler-delete-permission`，位于允许根目录下；分支 `codex/20260911-scheduler-delete-permission` 当前不存在，未发现同语义 worktree。基线使用创建时 `E:\IntRuoyi` 的已提交 `int_main` HEAD，不携带主工作区 staged/dirty 内容。

GREEN: implementation-and-test -> PASS, 新前向迁移、只读 target preflight、迁移候选过滤和回归测试已在独立 worktree 完成；静态与 MySQL 隔离 `6 passed`，迁移策略 `10 passed`，数据库 evidence validator PASS。提交 `41467d6c2` 已推送任务分支。

GREEN: test-server-write-preflight -> PASS, 测试服只读 preflight 通过；目标角色 2、目标菜单 1、现有有效绑定 0。非目标删除权限和全部用户角色计数/哈希已冻结，精确回滚与 pre-state 备份已就绪；只允许执行已提交 migrationId。

GREEN: test-server-permission-apply -> PASS, 测试服两个活动 `mes_scheduler` 角色各有且仅有一条删除权限绑定；非目标删除权限和全部用户角色计数/哈希保持不变。

GREEN: zhaojie-fresh-login-e2e -> PASS, `芋道源码/zhaojie` 权限响应已包含 `mes:pro-schedule-order:delete`，排产工单页 20 行显示 20 个删除按钮，无权限/系统错误；未点击删除。

BLOCKER: app-main-integration-closeout -> 应用主工作区存在其它任务 staged/dirty/untracked 改动，cleanup preview 拒绝 ff-only 融合；保留已推送分支、worktree 和 slot 42，不覆盖并行工作。测试服授权与页面验收不受影响。
