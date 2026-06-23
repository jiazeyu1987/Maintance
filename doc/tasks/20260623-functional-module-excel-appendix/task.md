# 任务：功能模块 Excel 附录整理

## Goal

基于当前代码现场整理展厅、eDHR、DCC、智能排产四块业务的现有功能模块明细，并生成一个 Excel 附录文件；每个业务单独一个 sheet，尽量细化到工作台、页面、流程、关键能力与对应代码证据。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-leader-time-allocation-document\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成领导时间分配文档整理与交付，不影响本任务继续执行。

## Scope

- 盘点以下四块当前功能模块：
  - 展厅
  - eDHR
  - DCC
  - 智能排产
- 盘点依据限定为当前本地代码与现有文档证据：
  - `D:\ProjectPackage\Website`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 输出 Excel：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx`
- 交付表达要求：
  - 仅使用业务语言整理
  - 不使用函数名、接口名、控制器名、模块名等程序员表述
  - 保证非技术人员也能直接阅读理解

## Non-Scope

- 不修改业务代码、数据库、菜单或权限
- 不执行服务器写入、发布、真实 E2E 或联调
- 不补充代码里没有证据支撑的“规划中功能”或“未来功能”

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 强制门禁摘录：
  - 先把任务文档、执行记录和请求命令记录落盘，再继续最终交付，避免多轮整理后来源不清。
  - 在 Windows 环境下处理中文文档与 Excel 时必须显式使用 UTF-8 读写，避免路径、标题和模块说明乱码。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。代码里未找到明确证据的模块不凭印象补写。
- `是否从根因和长期维护角度解决`：是。明细直接绑定页面目录、API 模块与后端控制器，便于后续持续更新。
- `是否存在临时补丁或绕过`：否。输出基于当前仓库现场自动提取加人工归纳，不造临时说明。

## BDD 场景

- `BDD: 领导查看展厅功能时能按模块理解当前交付范围 -> Given 展厅同时包含 Website 前台与 showrom-admin 后台能力 / When 打开 Excel 的展厅 sheet / Then 能看到模块、页面、关键功能和证据路径。`
- `BDD: 领导查看 eDHR 功能时能看到从执行到归档的闭环 -> Given eDHR 在 MES 生产域下分布多个页面和接口 / When 打开 eDHR sheet / Then 能看到批记录执行、签名、放行、归档、验证、标签打印等模块。`
- `BDD: 领导查看 DCC 与智能排产时能看到治理与计划两类能力 -> Given DCC 和智能排产均覆盖主页面、配置页和流程动作 / When 打开对应 sheet / Then 能看到目录、路由、审批、训练、电子签名、工艺路线、工单池、重排等内容。`

## Milestones

1. 建立任务文档并确认本次盘点范围。`COMPLETED`
2. 提取四块业务的页面、API 与后端控制器证据。`COMPLETED`
3. 整理为 Excel 四个 sheet 并做结构校验。`COMPLETED`
4. 更新请求命令记录并完成任务收尾。`COMPLETED`

## Expected Verification

- 交付文件存在：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx`
- 工作表校验：
  - `展厅`
  - `eDHR`
  - `DCC`
  - `智能排产`
- 每个 sheet 至少包含以下字段：
  - `一级工作`
  - `二级工作`
  - `页面/能力`
  - `具体内容`
  - `主要使用场景`
  - `补充说明`

## Blockers

- 若某一业务只存在零散测试或历史任务痕迹、缺少当前页面/API/控制器证据，则该项只能标记为“证据不足”，不能硬写成现有功能。
- 用户已明确要求“所有人都能看懂”，因此交付稿不得出现函数名、接口名、控制器名等技术术语；这些证据仅保留在任务记录中。

## Cleanup Candidates

- `tmp/docs/20260623-functional-module-excel-appendix/`

## Final Verification Result

- 交付文件通过：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx`
- 工作表核对通过：
  - `展厅`
  - `eDHR`
  - `DCC`
  - `智能排产`
- 结构核对通过：
  - 四个 sheet 均为 `6` 列
  - `展厅` 为 `22` 行
  - `eDHR` 为 `27` 行
  - `DCC` 为 `24` 行
  - `智能排产` 为 `22` 行
- 表达方式通过：交付表格已统一为业务语言，未直接暴露函数名、接口名、控制器名等程序员表述。
- 收尾清理通过：`task-closeout-cleanup` 已删除 `tmp/docs/20260623-functional-module-excel-appendix/` 临时目录，正式交付物已保留。

## Current Status

COMPLETED：Excel 已完成、通过结构校验并进入收尾阶段。
