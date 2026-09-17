# 发布失败直接原因分析

## Current Status
completed

## 任务目标
只分析当前按钮发布路径中已实际导致 build-release 或 publish-test 失败的原因，使用指定应用/维护 worktree 的真实提交、operation 日志和代码调用链；不把展示、审计或罕见恢复风险混入阻断结论。

## 里程碑与预期验证
1. [completed] 已定位今天4次真实build operation，当前第四次中断，未创建publish-test。
2. [completed] 已验证编码、NAS错目标、manifest读取合同三项历史阻断及修复状态；当前根因为重启中断和恢复无法收束。
3. [completed] 报告已保存，preview/apply通过且零删除；分析完成，发布目标未完成。

## 经验门禁
- 只读分析；不触发构建、发布、服务器、数据库、MinIO、E2E 或进程操作。
- 先查 migration/manifest/operation/脚本契约，再查环境；命令退出码和日志终态必须可追溯。
- 只使用显式 UTF-8；日志中的凭据、连接串和 token 不进入记录。
- 当前 worktree 可能有并发任务脏改动，不修改或清理其文件。
- 不把静态检查失败、登录阻塞或旧 releaseTag 结果误写成当前应用逻辑失败；按时间和 releaseTag 分层。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；将实际失败映射到唯一责任边界。
- 是否存在临时补丁或绕过：否。

## 任务链与归属
- 本任务承接用户对20260917-release-button-static-review的范围纠偏，旧静态问题不作为本轮发布失败根因；不接管被审发布任务。
- 经验门禁沿用已有发布合同/终态/真实证据规则，具体operation状态留在本任务报告，不新增长期经验文档。

## Cleanup Keep
- doc/tasks/20260917-release-failure-cause-analysis/task-state.json
