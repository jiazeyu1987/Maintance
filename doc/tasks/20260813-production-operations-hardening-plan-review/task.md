# 正式服运维规划文档复核优化

## Task Goal

复核并优化 `doc/tasks/20260813-production-operations-hardening-plan/` 下的 PRD、开发计划、测试计划和任务状态，使范围、优先级、依赖、验收口径、技术边界和跨文档映射与当前维护仓及生产约束一致。

## Scope

- 只修改规划文档及本次任务记录。
- 不修改生产代码、配置、数据库或服务器状态。
- 不执行备份、恢复、发布、远程联调或真实 E2E。

## Milestones

| Milestone | Status | Exit Criteria |
| --- | --- | --- |
| M1 独立审查 | completed | 形成结构化审查报告并列出必须修复项 |
| M2 文档修订 | completed | PRD、开发计划、测试计划和任务状态完成一致性修订 |
| M3 独立复审 | completed | 审查结论为 `pass`，无阻断项 |
| M4 验证与收尾 | completed | 文档校验、编码校验和任务收尾证据完整 |

## Expected Verification

- `validate_task_package.py` 校验通过。
- 需求、验收标准、里程碑、BDD 场景和任务状态之间不存在缺失映射或冲突。
- 独立复审结论为 `pass`。
- 所有新增及修改中文文档均为 UTF-8 无 BOM，且可按 UTF-8 正常读取。
- `git diff --check` 对本任务文件通过。

## 经验门禁

- Trigger：复核正式服备份、恢复、计划任务和生产运维规划。
- Preflight check：以 `E:\IntRuoyi\docs\release-backup-restore.md` 为权威入口，规划中的备份健康判定必须同时覆盖任务查询退出码、`Enabled/Status`、`NextRunTime`、`LastTaskResult`、`Task To Run` 脚本存在性、配置频率和成功备份包证据。
- Blocker：若规划把错误输出、空输出、旧路径、禁用任务、单次历史备份或未验证恢复能力描述为“正常”，必须阻塞修订放行。
- Verification：独立审查报告与最终文档校验必须证明上述字段和恢复证据均已进入验收标准；本任务不执行真实服务器检查。
- Forbidden action：禁止未授权操作服务器；禁止在文档、命令或日志中固化/输出生产确认值、密码、token、私钥或连接串；禁止用 mock、默认成功或静默降级填补未决条件。
- Evidence：`E:\IntRuoyi\docs\release-backup-restore.md#正式服备份计划任务状态门禁`、`E:\IntRuoyi\docs\powershell-memory.md`、本任务独立审查报告。
- PowerShell / UTF-8：PowerShell 5.1 不使用 `&&`；中文文档仅用 `apply_patch` 或明确 UTF-8 的读写方式，写后复读并检查 BOM。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；通过拆分独立交付节点、明确决策门禁和可测试契约消除规划层面的耦合与歧义。
- `是否存在临时补丁或绕过`：否。

## Cleanup Candidates

本任务无清理候选。

## Cleanup Keep

- `.review-fix-loop/runs/20260813T000000Z-opsdocs/`

## Current Status

completed

第三轮独立复审、文档校验和 task-closeout preview/apply 均已通过。阻塞项：无。
