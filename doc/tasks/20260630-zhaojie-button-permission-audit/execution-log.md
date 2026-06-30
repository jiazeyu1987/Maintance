# Execution Log：zhaojie 按钮与页签权限排查

- `2026-06-30 任务创建`：建立维护仓只读权限审计任务文档，目标是定位 `zhaojie` 看不到的 MES 按钮/页签对应权限码。
- `BDD: 生产报工按钮映射到精确权限码 -> Given 用户在生产报工页看不到按钮 / When 审计前端按钮显隐条件 / Then 可以得到每个按钮对应的 permission code 与额外显示条件。`
- `BDD: 生产工单按钮映射到精确权限码 -> Given 用户在生产工单页看不到按钮 / When 审计前端按钮显隐条件 / Then 可以得到导出、同步金蝶、创建 ERP 测试单对应的 permission code。`
- `BDD: 排产员正式角色范围不误判为前端问题 -> Given zhaojie 可能使用排产员类角色 / When 对照正式角色范围 SQL / Then 可以区分哪些权限是角色白名单故意排除，哪些是应该具备但运行态缺失。`
- `GREEN: source-audit -> PASS`，已只读核对 `src/views/mes/pro/feedback/index.vue`、`src/views/mes/pro/workorder/index.vue`、`sql/mysql/ruoyi-vue-pro.sql`、`sql/mysql/20260611_mes_work_order_create_erp_order.sql`、`sql/mysql/20260629_mes_smart_scheduling_role_scope.sql`。
- `GREEN: local-runtime-role-check -> PASS`，已只读查询本机 `int-ruoyi-mysql`，确认 `zhaojie` 在 `tenant_id=1` 绑定 `mes_scheduler + approval_center_entry`，在 `tenant_id=122` 绑定 `mes_scheduler`。
- `GREEN: local-runtime-menu-check -> PASS`，已只读查询本机 `system_role_menu` / `system_menu`，确认：
- `INFO: tenant_id=1` 当前仅有 `900120`、`5530`、`5531`、`5550`，缺 `5532`、`5535`、`5552`、`5553`、`5555`、`5969`、`900200`。
- `INFO: tenant_id=122` 当前已有 `900120`、`5530`、`5531`、`5532`、`5550`、`5552`、`900200`，仍缺 `5535`、`5553`、`5555`、`5969`。
- `GREEN: conclusion-output -> PASS`，已得到按钮权限映射。
- `INFO: 生产报工按钮 -> 新增/第三方导入/模拟报工 = mes:pro-feedback:create；导出 = mes:pro-feedback:export；审批 = mes:pro-feedback:approve，且需当前人为审批人、状态为 APPROVING。`
- `INFO: 生产工单按钮 -> 同步金蝶 = mes:pro-work-order:create；导出 = mes:pro-work-order:export；创建 ERP 测试单 = mes:pro-work-order:create-erp。`
- `INFO: 页签说明 -> 正式报工/待归属 没有单独权限码；整页入口缺失时应先查 5550/5551 与上级菜单 900120。`
- `INFO: 角色范围说明 -> 排产员正式白名单默认不含 5532、5535、5555、5969；若 zhaojie 当前用的是排产员角色，看不到这些按钮属于当前角色收敛结果。`
