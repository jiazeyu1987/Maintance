# 20260630 zhaojie 按钮与页签权限排查

## Task Goal

只读审计 `zhaojie` 账号在 MES 智能排产相关页面看不到按钮/页签的问题，定位这些前端元素对应的精确权限码、菜单记录与角色范围约束，并输出可直接用于授权的权限清单。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 前端源码：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 后端/SQL 源码：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 动作范围：只读代码与 SQL 审计、任务台账记录、结论输出

## Non-Scope

- 不修改测试服、本机运行库或正式库角色数据
- 不执行服务器写入、SQL 落库或真实 E2E
- 不修改前后端业务代码

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-main-branch-test-server-release-closure\task.md`
- 状态：`BLOCKED`
- 处理说明：用户已切换优先级到 `zhaojie` 权限排查；上一任务已显式阻塞，不与本次只读审计并行推进。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 本次只按索引命中与 PowerShell/编码相关的经验，不扩散阅读无关发布或服务器文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
  - PowerShell 5.1 不使用 `&&`。
  - 中文文件读写与终端输出统一显式 UTF-8。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。本轮为只读权限审计。
- `是否从根因和长期维护角度解决`：是。直接从前端 `v-hasPermi`、菜单 SQL 与角色范围 SQL 反查真实权限合同。
- `是否存在临时补丁或绕过`：否。不做手工改库或前端临时显隐绕过。

## BDD 场景

- `BDD: 生产报工按钮映射到精确权限码 -> Given 用户在生产报工页看不到按钮 / When 审计前端按钮显隐条件 / Then 可以得到每个按钮对应的 permission code 与额外显示条件。`
- `BDD: 生产工单按钮映射到精确权限码 -> Given 用户在生产工单页看不到按钮 / When 审计前端按钮显隐条件 / Then 可以得到导出、同步金蝶、创建 ERP 测试单对应的 permission code。`
- `BDD: 排产员正式角色范围不误判为前端问题 -> Given zhaojie 可能使用排产员类角色 / When 对照正式角色范围 SQL / Then 可以区分哪些权限是角色白名单故意排除，哪些是应该具备但运行态缺失。`

## Milestones

1. 建立任务台账并补齐经验门禁。`COMPLETED`
2. 审计前端页面按钮/页签显隐条件。`COMPLETED`
3. 审计菜单 SQL、角色范围 SQL 与历史权限任务。`COMPLETED`
4. 形成可授权的权限清单并回填日志。`COMPLETED`

## Expected Verification

- `rg -n` 命中目标页面中的 `v-hasPermi` / `checkPermi`
- `Get-Content -Encoding utf8` / `python -X utf8` 只读核对相关 Vue 与 SQL 文件
- 维护仓任务文档与命令日志已同步更新

## Final Verification Result

- 已确认 `生产报工` 页面按钮显隐由 `mes:pro-feedback:create/export/approve` 控制。
- 已确认 `生产工单` 页面按钮显隐由 `mes:pro-work-order:create/export/create-erp` 控制。
- 已确认 `审批` 按钮除权限外，还要求行状态为 `APPROVING` 且 `approveUserId === 当前登录用户`。
- 已确认 `正式报工 / 待归属` 页签本身没有独立权限判断；若整页入口缺失，应优先核对页面菜单与查询权限。
- 已确认 `排产员` 正式角色范围白名单包含 `5550/5551/5552/5553`、`5530/5531`，但不包含 `5532`、`5535`、`5555`、`5969`；因此 `同步金蝶`、工单导出、报工导出、审批在该角色下默认不会显示。
- 已确认本机运行库中 `zhaojie` 实际存在两套账号：
  - `tenant_id=1 / 芋道源码`：角色为 `910233=mes_scheduler/排产员` 与 `910295=approval_center_entry/审批中心入口`
  - `tenant_id=122 / 测试租户`：角色为 `910287=mes_scheduler/排产员`
- 已确认本机运行库中目标菜单实际绑定差异：
  - `tenant_id=1` 当前仅拥有 `900120`、`5530`、`5531`、`5550`；缺少 `5532`、`5535`、`5552`、`5553`、`5555`、`5969`、`900200`
  - `tenant_id=122` 当前拥有 `900120`、`5530`、`5531`、`5532`、`5550`、`5552`、`900200`；仍缺少 `5535`、`5553`、`5555`、`5969`

## Current Status

COMPLETED：本轮已完成只读权限审计，结论可直接用于给 `zhaojie` 角色补菜单/权限；未进行任何服务器或数据库写入。
