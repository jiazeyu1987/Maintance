# 任务：功能模块 Excel 补充 QMS 文控与瑛泰系统 Sheet

## Goal

继续补充现有功能模块 Excel，完成两项内容：

1. 在 QMS 文控相关范围中补充 `NAS 管理`、`从 NAS 平移数据到文控中心` 的工作内容。
2. 新增 `瑛泰系统` sheet，整理运行控制台相关工作内容。
3. 将 QMS 文控中除“浏览功能”“浏览权限功能”以外的内容标灰，并把“浏览功能”“浏览权限功能”进一步细化。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-functional-module-excel-purun-sheet\task.md`
- 状态：`BLOCKED`
- 处理：上一任务已完成 `璞润` sheet 内容整理，并生成可用替代文件 `functional-module-appendix-20260623-purun.xlsx`；当前阻塞是原始 Excel 文件仍被其他进程占用，无法直接覆盖回原文件名。

## Scope

- 继续整理以下两块内容：
  - QMS 文控中与 `NAS 管理`、`NAS 数据平移到文控中心` 相关的工作
  - `瑛泰系统` 运行控制台相关工作
- 资料来源限定为：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 表达要求：
  - 仅使用业务语言
  - 不出现函数名、接口名、控制器名等程序员表述
  - 保持和现有 sheet 一致的列结构与口径

## Non-Scope

- 不修改业务代码
- 不执行运行控制台真实发布、备份、恢复、回滚或服务器写入
- 不把代码中没有证据的规划内容写成现有工作内容

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 强制门禁摘录：
  - 先把任务文档、执行记录和请求命令记录落盘，再继续最终交付，避免后续追溯来源不清。
  - Windows 环境下处理中文 Excel 与任务文档时必须显式使用 UTF-8，避免标题、路径和说明文字乱码。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。若原文件仍被锁定，需明确报告并由用户决定是否继续写替代文件。
- `是否从根因和长期维护角度解决`：是。新增内容继续写入同一套附录结构，后续可持续增补。
- `是否存在临时补丁或绕过`：是。若用户同意继续写替代文件，则属于“原文件被占用时的替代交付路径”，需在任务记录中明确标注。

## BDD 场景

- `BDD: 领导查看 QMS 文控工作时能看到 NAS 相关内容 -> Given 现有 DCC/QMS 文控整理已覆盖文控主流程 / When 更新 QMS 文控相关条目 / Then 能看到 NAS 管理和 NAS 数据平移到文控中心的工作内容。`
- `BDD: 领导查看瑛泰系统时能单独看到运行控制台范围 -> Given 运行控制台内容不适合混在其他业务 sheet 中 / When 新增瑛泰系统 sheet / Then 能独立看到构建发布、部署、备份恢复、运行治理等工作内容。`

## Milestones

1. 建立补充任务文档并确认本轮新增范围。`COMPLETED`
2. 只读提取 QMS 文控新增内容与运行控制台证据。`COMPLETED`
3. 将内容写入 Excel 并完成结构校验。`COMPLETED`
4. 更新请求命令记录并完成收尾。`COMPLETED`

## Expected Verification

- 目标文件若可写：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx`
- 若目标文件继续被占用，则替代交付文件应包含：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-purun.xlsx`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-qms-yingtai.xlsx`
- Excel 中应具备：
  - `璞润` sheet
  - `瑛泰系统` sheet
  - QMS 文控相关内容已补充 NAS 管理与 NAS 平移
  - QMS 文控中除“浏览功能”“浏览权限功能”外的条目已标灰

## Blockers

- 当前存在锁文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\~$functional-module-appendix-20260623.xlsx`，说明原始 Excel 仍被其他进程占用；影响：本轮已通过替代交付文件完成更新，但若要覆盖回原文件名，仍需先释放原始文件锁定。

## Final Verification Result

- 已生成最新可用交付文件：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-qms-yingtai.xlsx`
- 结构核对通过：
  - workbook sheetnames 为 `展厅 / eDHR / DCC / 智能排产 / 璞润 / 瑛泰系统`
  - `DCC` 为 `17` 行、`6` 列
  - `瑛泰系统` 为 `17` 行、`6` 列
- QMS 文控调整通过：
  - `浏览功能` 与 `浏览权限功能` 已细化
  - `DCC` sheet 中第 `12-17` 行为灰色，表示当前不是重点
- 运行控制台整理通过：
  - `瑛泰系统` sheet 已覆盖构建发布、测试部署、正式上线、备份恢复、状态查看与风险监控等内容
- 原始文件状态说明：
  - 原始文件仍被占用，当前未覆盖回 `functional-module-appendix-20260623.xlsx`

## Current Status

COMPLETED：已通过替代交付文件完成本轮更新；如需覆盖回原文件名，需先关闭占用原文件的程序。
