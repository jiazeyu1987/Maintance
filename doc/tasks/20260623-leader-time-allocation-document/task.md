# 任务：领导时间分配文档整理

## Goal

将当前“集团任务与子公司任务”的时间安排，以及集团内部各项目阶段性投入比例，整理成一份适合直接提交给领导的正式文档，并输出可转发的交付文件。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\task.md`
- 状态：`BLOCKED`
- 处理：因用户当前线程切换为领导文档整理，该任务已显式阻塞并记录影响；本任务可独立继续执行。

## Scope

- 按用户提供的固定排班整理工作时间：
  - 周一至周五：集团、璞润与休息时段
  - 周六至周日：集团、璞润与休息时段
- 整理集团内部项目在三个阶段的时间投入比例：
  - `5.15` 之前
  - `5.15` 至 `20` 周年期间
  - `20` 周年之后
- 输出正式文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.docx`

## Non-Scope

- 服务器、数据库、发布链路、E2E 或任何远端操作
- 与时间分配无关的业务方案设计
- 未经用户确认的额外制度说明或考勤规则扩写

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 强制门禁摘录：
  - 先把任务文档、执行记录和请求命令记录落盘，再继续最终交付，避免文档多轮修改后来源不清。
  - 在 Windows 环境下处理中文文档时必须明确使用 UTF-8，避免正文、表格和任务记录出现乱码。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。用户提供的信息不足以支撑的内容不自行扩写，不用默认值掩盖。
- `是否从根因和长期维护角度解决`：是。交付同时保留 Markdown 源文件和 DOCX 正式文档，便于后续继续维护。
- `是否存在临时补丁或绕过`：否。文档内容直接基于用户已确认的时间安排整理。

## BDD 场景

- `BDD: 领导可快速区分集团与璞润常规时段 -> Given 用户提供了工作日与周末的固定排班 / When 阅读正式文档 / Then 能清楚看到集团、璞润与休息时段的分配。`
- `BDD: 集团内部项目分配按阶段清晰呈现 -> Given 用户提供了三个阶段的项目投入比例 / When 阅读正式文档 / Then 能直接看到每个阶段各项目占比且单阶段合计为 100%。`
- `BDD: 特殊停工条件必须被明确说明 -> Given 连续三天及以上节假日和青云学院课程会中断工作 / When 阅读正式文档 / Then 能明确知道这些期间暂停工作。`

## Milestones

1. 补齐任务文档、阻塞上一未完成任务，并固化本次文档范围。`COMPLETED`
2. 生成正式中文文档内容，整理常规排班、阶段占比和特殊说明。`COMPLETED`
3. 输出 Markdown 与 DOCX 交付物，并完成可读性验证。`COMPLETED`
4. 更新请求命令记录并完成任务收尾。`COMPLETED`

## Expected Verification

- 结构核对：工作日、周末、集团内部项目分配、特殊说明四部分齐全。
- 数值核对：
  - 周一至周五集团 `7.5` 小时/天，璞润 `5` 小时/天。
  - 周六至周日集团 `9.5` 小时/天，璞润 `1` 小时/天。
  - 三个阶段的集团项目投入比例均合计 `100%`。
- 交付核对：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.docx`

## Blockers

- `5.15` 至 `20` 周年期间的原始口述里，`智能排产` 与 `批记录 EDHR` 未显式写出“各占 10%”，本任务按语义闭合整理为“各占 10%”；如用户后续修正，以用户最新口径为准。
- 若领导需要公司抬头、盖章页、签发人或正式编号，本任务当前未包含，需要用户补充。

## Cleanup Candidates

- `tmp/docs/20260623-leader-time-allocation-document/`

## Final Verification Result

- 文档结构核对通过：已包含常规时间安排、集团内部项目时间分配、特殊情况说明和文档说明。
- 数值核对通过：
  - 周一至周五集团 `7.5` 小时/天，璞润 `5` 小时/天。
  - 周六至周日集团 `9.5` 小时/天，璞润 `1` 小时/天。
  - 集团内部三个阶段的项目投入比例均闭合为 `100%`。
- 交付文件通过：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.docx`
- 版式检查通过：已将 DOCX 导出为 PDF 并渲染 `2` 页预览图人工核对，标题、表格、分页和中文显示正常。
- 收尾清理通过：`task-closeout-cleanup` 预览结果为 `status: ready`，随后已按 `Cleanup Candidates` 删除 `tmp/docs/20260623-leader-time-allocation-document/` 临时预览目录，正式交付物已保留。

## Current Status

COMPLETED：已完成领导文档整理、DOCX 交付与可读性验证。
