# 恢复备份包两个服务器地址说明

## Task Goal
解释截图中“服务器地址”和“恢复服务器地址”的区别，仅核对本地文档和代码。

## Milestones
- [x] 核对恢复表单及字段用途。
- [x] 记录证据，确认用户说明结论。

## Expected Verification
以恢复表单、请求参数和恢复目标筛选逻辑交叉核对。不执行恢复、不访问服务器、不修改产品代码。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，依据真实字段逻辑说明。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：恢复备份界面字段咨询。
- Preflight check：读取经验索引命中项及恢复说明；PowerShell 显式使用 UTF-8。
- Blocker：字段语义无法由本地代码确认时，不推断远端状态。
- Verification：核对来源字段、目标字段和空目标提示。
- Forbidden action：不得执行备份、恢复或远端写入，不扩大为产品修改。
- Evidence：见 execution-log.md。

## Current Status
completed

## Verification Result
- `ops/spug/smallapp-ui/simple.js:11`：上方服务器参与来源绑定选择；41–44 行分别提交 sourceConfigRef 和 targetConfigRef。
- `simple.js:88–114`：下方服务器为恢复目标；无可用空目标时显示截图提示并禁用提交。
- 结论：上方表示“从哪台服务器的备份恢复”，下方表示“恢复到哪台服务器”。界面命名不清晰，适合分别命名为“备份来源服务器”和“恢复目标服务器”。本次未改产品。
- 本机不存在规则指向的 `E:\IntRuoyi\docs\release-backup-restore.md` 和 PowerShell 经验路径；未据此执行备份恢复或服务器操作。字段解释由本地代码交叉确认，远端目标实际状态未检查。
- 无 worktree、进程或运行控制台变更，无待清理资源。

## Task Chain
本聊天无已知前序拥有任务；不接管其他并发任务。
