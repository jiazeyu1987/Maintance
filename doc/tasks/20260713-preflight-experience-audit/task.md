# 20260713 前置经验一致性审查

## Task Goal

验证当前前置经验、经验索引、发布/worktree/PowerShell 门禁与项目 AGENTS 基线之间是否存在错误、冲突、缺失路由或不可执行表述；本任务只做审查记录，不修改现有经验正文。

## Milestones

- [x] 创建任务目录和审查任务记录。
- [x] 读取前置经验技能参考、项目经验索引和命中的经验文档。
- [x] 对照 AGENTS 基线检查发布、worktree、manifest、PowerShell、运行态验收和经验写入规则。
- [x] 记录发现的问题、冲突、风险和建议处理优先级。
- [x] 完成验证报告并标记任务完成。

## Expected Verification

- 能证明本次审查覆盖 `docs/experience-index.md` 及当前命中的前置经验文档。
- 能列出明确冲突、疑似错误、缺失路由和表述风险；若未发现则说明检查范围和剩余风险。
- 不改动发布脚本、环境、服务器或现有经验正文。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本任务只审查经验门禁是否能在事前阻断风险。
- 是否存在临时补丁或绕过：否。

## 经验门禁

### 前置经验审查门禁

- Trigger: 用户要求验证当前前置经验是否错误、冲突或不可执行。
- Preflight check: 先读取 `docs/experience-index.md`，按关键词打开命中的前置经验文档；对照 AGENTS 发布、worktree、PowerShell、UTF-8、任务记录和 fail-fast 基线检查。
- Blocker: 经验正文允许 fallback、mock 成功、跳过真实运行态、复用旧 releaseTag、从脏主工作区构建，或与 AGENTS 明确禁令冲突。
- Verification: 形成 `verification-report.md`，记录覆盖文件、发现项、证据位置和建议动作。
- Forbidden action: 不得只写“已阅读”；不得在未确认归属时直接重写长期经验正文。
- Evidence: 本任务 `execution-log.md` 与 `verification-report.md`。

## Current Status

completed - 已完成前置经验一致性审查；发现 2 个高优先级冲突、2 个中优先级可维护性问题和 2 个低优先级文档歧义/格式问题，详见 `verification-report.md`。
