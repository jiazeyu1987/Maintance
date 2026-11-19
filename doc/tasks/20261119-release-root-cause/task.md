# 分析本次正式发布失败的根因

## Task Goal
继续分析“发布”聊天中的正式发布失败，基于实际导入代码、冻结校验路径与发布/迁移执行逻辑，解释错误如何产生、为何进入正式数据、为何停服后才发现，并清楚标出已证实与仍未知事项。本任务只读，不修代码、不访问服务器、不向目标聊天发消息。

## Current Status
completed

## Milestones
- [x] 追踪跨租户路线导入的映射、校验与快照冻结实际代码。
- [x] 追踪发布迁移执行和终端 READINESS 的先后关系，验证漏检机制。
- [x] 形成带基线文件行号的因果链，区分确定根因、促成条件和未知责任。

## Expected Verification
用当前 r2 隔离 worktree 源码与已有任务证据交叉验证；引用精确代码行及测试证据。运行只读源码/状态检查，不执行业务代码、构建、测试、服务器探测或数据写入。

## Final Verification
旧实现以冻结提交读取、候选基线和真实任务回执交叉核对，完整因果链及未知边界已记录。分析文档严格UTF-8、git diff --cached --check通过；提交4bc72fd只含本分析及共享请求日志本任务段。当前目标聊天专项修复仍inProgress；本任务completed仅表示根因分析交付完成。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；按代码因果分析，不做短期补丁或推测性归责。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger: 追查 Spug 正式发布的数据 blocker、route snapshot / READINESS 和迁移已 APPLIED 的行为。
- Preflight check: 读取目标聊天的 task.md / execution-log.md / production-blocker.md，确认本任务只读；代码路径固定为已验证的 r2 应用与维护 worktree。
- Blocker: 若代码与发布候选提交不匹配、无法定位冻结调用路径，或证据只来自摘要而无源代码/测试支撑，则将该点标为未证实。
- Verification: 核对导入 ID/key 映射、冻结前语义校验、快照序列化与摘要、发布 PRECHECK/BACKFILL 条件及调用顺序；行号对应目标提交。
- Forbidden action: 禁止读写服务器、数据库、测试租户或目标聊天；禁止把代码缺陷推定为具体用户责任；禁止把候选代码测试通过说成已上线。
- Evidence: docs/experience-index.md 中 route snapshot BACKFILL 前置门禁、已执行迁移不可变门禁及 Spug 构建前预检门禁；doc/tasks/20261119-update-and-release-prod/ 证据。
