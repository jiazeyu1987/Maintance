# Execution Log：zhaojie 排产员按钮权限正式修复

- `2026-06-30 任务创建`：建立维护仓正式修复任务文档，承接上一轮只读权限审计。
- `BDD: 排产员保留工单按钮权限 -> Given 排产员已拥有生产工单页面入口 / When 应用正式角色范围 SQL / Then 排产员具备 5532=create、5535=export、900200=create-erp。`
- `BDD: 排产员保留报工按钮权限 -> Given 排产员已拥有生产报工页面入口 / When 应用正式角色范围 SQL / Then 排产员具备 5552=create、5555=export、5969=approve。`
- `BDD: 非目标角色不被顺带放大 -> Given 本次仅修复排产员角色按钮权限 / When 应用正式角色范围 SQL / Then 车间主任与班组长不额外获得 5532、5535、5555、5969、900200。`
- `GREEN: local-role-scan -> PASS`，本机只读回查确认这些权限已有现成角色承载：`super_admin` 全量拥有；`tenant_id=122` 的 `mes_scheduler` 已拥有 `5532/5552/900200`；`mes_team_leader` 已拥有 `5552`；`tenant_id=1` 的 `mes_scheduler` 仍缺 `5532/5535/5555/5969/900200`，且运行态也缺失 `5552` 绑定。
- `GREEN: formal-sql-gap-check -> PASS`，已确认当前正式 SQL 白名单已包含 `5552`，但尚未包含 `5532/5535/5555/5969/900200`；因此本次正式修复应补齐真正缺项，并通过重跑正式 SQL 自动恢复 `5552` 等允许项绑定。`
- `GREEN: backend-red-green-fix -> PASS`，后端仓已完成 SQL 合同测试 RED -> SQL 白名单修复 -> GREEN，当前 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_scope_sql.py -q` 为 `19 passed`。
- `GREEN: local-runtime-apply -> PASS`，已将更新后的正式 SQL 应用到本机运行库；只读回查确认 `tenant_id=1` 的 `mes_scheduler/排产员` 当前已拥有 `5532/5535/5552/5555/5969/900200`。
