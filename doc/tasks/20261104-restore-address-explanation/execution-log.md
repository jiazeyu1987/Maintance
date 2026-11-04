# 执行记录

- 用户需求：为什么恢复备份包界面有两个服务器地址。
- 已执行 UTF-8 只读 bootstrap，读取 AGENTS.md、经验索引和 PowerShell 经验入口；输出过长，后续仅定向读取命中部分。
- 范围：本地只读核对，未执行服务器操作或恢复。
- BDD：字段说明 -> Given 恢复备份包截图，When 核对来源和恢复目标，Then 解释两字段职责及空目标提示。无行为变更，不适用 RED/GREEN 代码测试。
- Verification：simple.js 的 currentBinding 使用上方 simple-server 选择来源；simpleRequest 将来源 sourceConfigRef 与下方目标 targetConfigRef 分别提交。
- Verification：simpleRender 按当前来源筛选恢复目标；无可用空目标时输出截图原文，并令 simple-submit.disabled=true。
- 文档可用性：E:\IntRuoyi 文档路径在本机不可读；不执行任何实际备份恢复操作，不推断远端状态。已确认的字段语义不依赖远端操作。
- Closeout：仅新增本任务记录及请求记录；未修改产品，无构建、E2E、远端访问、worktree 或控制台操作。
