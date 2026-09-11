# Execution Log

BDD: zhaojie 删除按钮可见性诊断 -> Given 测试服存在 `zhaojie` 账号和排产工单页面 / When 通过真实登录路径进入页面并核对权限与工单状态 / Then 能以页面、权限响应和只读授权事实解释删除按钮不可见原因，且不产生任何写入。

GREEN: task-scope-preflight -> PASS, 已限定为测试服只读诊断；禁止点击删除、修改权限、业务数据或服务器配置。

GREEN: experience-preflight -> PASS, 已读取登录权限投影与跨环境角色权限差异门禁；真实页面必须核对 `get-permission-info`，动态菜单需同时核对前端权限码、`system_menu`、`system_role_menu` 和目标账号全部有效角色；不使用其它账号、旧 token 或数据库写入替代目标账号验证。

GREEN: source-permission-contract -> PASS, 排产工单删除按钮绑定 `mes:pro-schedule-order:delete`，额外条件仅为 `!row.removedFromSchedule`；按钮缺失优先判断当前登录权限投影不含该权限。

GREEN: test-server-readonly-role-menu-check -> PASS, 测试服 `芋道源码/zhaojie` 为启用账号，活动角色包括 `mes_scheduler`、`approval_center_entry`、`wenkong` 和 `dcc_action_training_independent`；菜单 `5586 / mes:pro-schedule-order:delete` 存在且启用，但该账号所有角色均无此菜单绑定。

GREEN: playwright-zhaojie-delete-visibility -> PASS, 使用项目 Playwright 1.60.0 真实登录测试服 `芋道源码/zhaojie`；`get-permission-info` HTTP 200、业务码 0，`hasDeletePermission=false`；排产工单页加载 20 行、无权限错误、删除按钮数量 0。未执行任何删除或写入。

GREEN: root-cause -> PASS, 正式 `mes_scheduler/排产员` 白名单包含排产查询、新增、调整、入池差异、预检和人工完成，但不包含菜单 `5586`；因此按钮不可见是角色未被授予危险删除权限，不是前端故障、页面状态或缓存漂移。

GREEN: project-experience-consolidation -> PASS, 已将“页面可进入但危险按钮缺失”的精确权限诊断门禁合并到 `E:\IntRuoyi\docs\login-access.md`，并更新 `E:\IntRuoyi\docs\experience-index.md` 路由。

GREEN: task-closeout-cleanup -> PASS, preview/apply 无 blocker 或 warning；已删除任务自有临时 Playwright 脚本与截图目录，保留 `task.md`、`execution-log.md`、`verification-report.md`，任务状态更新为 `completed`。
