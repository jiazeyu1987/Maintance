# 任务：zhaojie 排产员按钮权限正式修复

- Task ID: `20260630-zhaojie-scheduler-button-permission-fix`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Created: `2026-06-30`
- Current Status: `completed`

## Task Goal

基于前一轮只读审计结果，确认 `zhaojie` 看不到的 MES 按钮是否已有现成角色承载，并把用户明确要求的按钮权限正式下放到 `排产员`，采用后端正式 SQL 与回归测试交付，不做一次性手工改库结论交付。

## Scope

- 维护仓任务台账与请求/命令记录
- 后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 的正式角色范围 SQL 与回归测试
- 本机只读核验相关角色/菜单绑定

## Non-Scope

- 不直接改测试服或正式服
- 不修改前端页面显隐逻辑
- 不扩大到用户未明确要求的其他权限

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-zhaojie-button-permission-audit\task.md`
- 状态：`COMPLETED`
- 处理说明：上一任务已完成只读审计并定位权限码；本次进入正式修复。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 本次命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
  - PowerShell 5.1 不使用 `&&`。
  - 中文任务文档与命令输出统一显式 UTF-8。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。通过正式 SQL 白名单与回归测试修复，而不是临时加菜单绑定。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 排产员保留工单按钮权限 -> Given 排产员已拥有生产工单页面入口 / When 应用正式角色范围 SQL / Then 排产员具备 5532=create、5535=export、900200=create-erp。`
- `BDD: 排产员保留报工按钮权限 -> Given 排产员已拥有生产报工页面入口 / When 应用正式角色范围 SQL / Then 排产员具备 5552=create、5555=export、5969=approve。`
- `BDD: 非目标角色不被顺带放大 -> Given 本次仅修复排产员角色按钮权限 / When 应用正式角色范围 SQL / Then 车间主任与班组长不额外获得 5532、5535、5555、5969、900200。`

## Milestones

1. M1：确认已有角色归属与正式 SQL 当前缺口。`completed`
2. M2：建立维护仓/后端仓任务台账。`completed`
3. M3：完成后端 SQL 与回归测试修复。`completed`
4. M4：回填验证证据与请求/命令记录。`completed`

## Expected Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_scope_sql.py -q`
- 后端任务文档、证据文档与维护仓 `docs/request-command-log.md` 已同步更新

## Current Blockers

- 无。

## Final Verification Result

- 已确认这些权限已有现成角色承载，不是“系统中完全没有对应角色”：
  - `super_admin`：`5532/5535/5552/5555/5969/900200`
  - `tenant_id=122` 的 `mes_scheduler`：`5532/5552/900200`
  - `mes_team_leader`：`5552`
- 已在后端正式 SQL 中把用户要求的按钮权限补到 `排产员` 白名单：
  - `5532`、`5535`、`5552`、`5555`、`5969`、`900200`
- 已通过 SQL 合同测试：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_scope_sql.py -q`
- 已应用本机运行库并回查通过：`tenant_id=1` 的 `mes_scheduler/排产员` 当前已有效拥有 `5532/5535/5552/5555/5969/900200`
- 已同步更新维护仓命令日志与后端任务证据文档。

## Current Status

completed
