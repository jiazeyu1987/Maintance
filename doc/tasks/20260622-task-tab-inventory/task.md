# 任务：盘点现有任务总览页签

## 任务目标

确认当前系统是否已经存在类似“个人中心”或“任务中心”的页签/页面，可用于查看任务列表、待办/已办或全部任务，并给出真实代码与菜单依据。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-sql-preflight-gate\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成并标记完成，本次为新的只读盘点任务，单独建档执行。

## 用户要求与执行边界

- 用户要求：确认“现在有没有类似个人中心的页签，可以看到所有的任务”。
- 当前任务授权：
  - 允许在本机维护仓与业务仓内执行只读检索、代码阅读和文档记录。
  - 允许更新本任务文档、执行日志和请求命令日志。
- 禁止范围：
  - 不修改前后端业务代码。
  - 不操作服务器、数据库、测试环境或正式环境。
  - 不凭印象回答，必须以代码、菜单或文档证据为准。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 结论必须来自真实仓库证据，不得凭历史印象推断现状。
  - 只读盘点任务也要先核对上一任务状态、请求记录和任务文档，再开始检索。
  - 本任务不执行真实 E2E、服务器写入或高风险动作，如范围变化需先补门禁记录。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。本次直接基于真实代码、菜单和页面入口盘点现状。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 盘点任务入口现状 -> Given 用户需要确认是否存在任务总览页签 / When 检索前端路由、页面、菜单和后端任务相关模块 / Then 输出当前是否存在、入口在哪里、能看到哪些任务。`
- `BDD: 拒绝印象式回答 -> Given 可能存在历史页面、未接菜单页面或仅后端接口 / When 对照真实仓库证据 / Then 明确区分“已有可访问入口”“仅有代码无入口”“完全不存在”。`

## 里程碑

1. 建立任务文档、执行日志并登记请求。`DONE`
2. 检查上一任务状态与经验门禁。`DONE`
3. 检索前端页面、路由、菜单和后端任务模块。`DONE`
4. 汇总结论并更新任务文档与执行日志。`DONE`

## 预期验证

- 能提供至少一组真实证据：
  - 前端页面/路由文件；
  - 菜单 SQL、菜单配置或权限标识；
  - 后端任务/审批相关控制器或接口。
- 明确区分以下情况：
  - 已有可访问页签；
  - 有页面但缺入口；
  - 只有接口/能力，没有完整总览页。

## 盘点结论

- 当前系统里有多个“任务/待办”入口，但没有一个挂在标准“个人中心”里的统一总任务页签。
- 标准个人中心仅包含基础资料、修改密码、社交绑定，不包含任务聚合能力。
- 最接近“个人任务中心”的现成能力是 BPM 的“审批中心”，可查看：
  - 我的流程
  - 待办任务
  - 已办任务
  - 抄送我的
- 业务域还各自有独立任务页，不是统一聚合：
  - DCC：`DCC 工作台`、`DCC审批任务`、`DCC我的文件`
  - eDHR：`eDHR工作任务`，页内含“我的待办 / 候选审核 / 逾期任务 / 我已处理”
  - 展厅：有单独 `审批中心`

## 关键证据

- 个人中心路由与页面：
  - 前端隐藏路由 `/user/profile` 指向 `src/views/Profile/Index.vue`，仅包含基础信息/重置密码/社交绑定页签。
- BPM 审批中心菜单：
  - `sql/mysql/ruoyi-vue-pro.sql` 已登记 `审批中心`、`我的流程`、`待办任务`、`已办任务`、`抄送我的` 菜单。
  - 对应前端页面和接口已存在：
    - `src/views/bpm/processInstance/index.vue`
    - `src/views/bpm/task/todo/index.vue`
    - `src/views/bpm/task/done/index.vue`
    - `src/api/bpm/processInstance/index.ts`
    - `src/api/bpm/task/index.ts`
- DCC 独立任务入口：
  - `sql/mysql/20260513_dcc_base_schema.sql` 已登记 `DCC我的文件`、`DCC审批任务` 菜单。
  - `src/views/dcc/controlled-file/workbench/index.vue` 有“我的审批待办”面板，并跳转到 `/dcc/controlled-file/approval-tasks` 与 `/dcc/controlled-file/mine`。
- eDHR 独立任务入口：
  - `sql/mysql/20260611_mes_edhr_work_task_flow.sql` 已登记 `eDHR工作任务` 菜单，组件为 `mes/pro/edhr-work-task/WorkTaskBoardPage`。
  - 该页自带“我的待办 / 候选审核 / 逾期任务 / 我已处理”页签。

## 最终验证结果

- 前端路由验证：`src/router/modules/remaining.ts`、`src/router/modules/showroom.ts`
- 前端页面验证：`src/views/Profile/Index.vue`、`src/views/bpm/task/{todo,done}/index.vue`、`src/views/bpm/processInstance/index.vue`、`src/views/dcc/controlled-file/{workbench,approval-tasks}/index.vue`、`src/views/mes/pro/edhr-work-task/WorkTaskBoardPage.vue`
- 菜单 SQL 验证：`sql/mysql/ruoyi-vue-pro.sql`、`sql/mysql/20260513_dcc_base_schema.sql`、`sql/mysql/20260611_mes_edhr_work_task_flow.sql`
- 收尾预览：`python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-task-tab-inventory --mode preview` -> PASS

## 当前状态

COMPLETED：已完成现状盘点，结论已基于前端路由、页面、菜单 SQL 与接口证据写回。

## Current Status

completed
