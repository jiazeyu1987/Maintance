# 20260713 前置经验一致性审查执行日志

## Initial Request

- REQUEST: 用户要求验证当前前置经验是否存在错误或冲突。
- SCOPE: 只读审查前置经验、经验索引和项目基线；不执行发布、不改服务器、不修改现有经验正文。

## Milestone 1 - Task Bootstrap

- GREEN: task-directory -> PASS，创建 `doc/tasks/20260713-preflight-experience-audit/`。
- GREEN: task-doc-bootstrap -> PASS，写入任务目标、里程碑、预期验证、设计约束和经验门禁。

## Milestone 2 - Experience Review

- COMMAND: 读取 `preflight-experience-consolidation` 技能及其 build/release/powershell/worktree 参考。
- COMMAND: 读取维护仓 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`docs/release-agent-checklist.md`。
- COMMAND: 读取主项目 `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`、`docs/worktree-memory.md`、`docs/powershell-memory.md`、`docs/release-backup-restore.md` 和 `AGENTS.md` 相关段落。
- GREEN: source-scope -> PASS，审查覆盖测试服发布、构建 manifest、worktree、PowerShell、运行态验收、经验写入格式和索引路由。

## Milestone 3 - Verification Checks

- GREEN: script-contract-check -> PASS，实际 `run-release-migration-policy-gate.py --help` 仅支持 `--output`，不支持历史 `--json`。
- ISSUE: stale-migration-gate-json -> 现象：主测试服门禁和旧发布经验仍推荐/要求 `--json`；阶段：构建前契约门禁；影响：按文档执行会参数失败或误判门禁类型；原因判断：2026-07-12 已沉淀冻结脚本契约，但旧命令未同步替换；处理动作：记录 PF-AUDIT-001；结果：已列为高优先级修正文档项；是否可前置检查：是；是否可自动化：是；下次如何避免：索引新增脚本参数变更经验时，同步扫描旧命令示例。
- ISSUE: task-doc-vs-powershell-bootstrap -> 现象：任务文档必须先写与 PowerShell 只读 bootstrap 禁止写文件存在顺序冲突；阶段：任务启动；影响：Windows/PowerShell 任务无法字面同时满足两条规则；原因判断：后续新增 PowerShell bootstrap 规则时未显式定义相对 task-doc-first 的优先级；处理动作：记录 PF-AUDIT-002；结果：建议新增明确例外；是否可前置检查：是；是否可自动化：部分可自动化；下次如何避免：新增/更新 AGENTS 基线时跑规则冲突审查。
- ISSUE: preflight-format-and-index-drift -> 现象：测试服主门禁摘要缺 Evidence，部分索引锚点与目标标题不一致；阶段：经验发现与提取；影响：人能搜索到，但机器提取和点击跳转不稳定；原因判断：旧文档在六字段规范前后混合更新；处理动作：记录 PF-AUDIT-003/PF-AUDIT-004；结果：建议批量规范化；是否可前置检查：是；是否可自动化：是；下次如何避免：经验写入后运行字段和锚点 lint。
- GREEN: no-test-only-prod-conflict -> PASS，`release-agent-checklist.md` 已明确仅测试服任务以 `docs/test-release-preflight.md` 为范围权威，禁止 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: no-fallback-allowance-found -> PASS，抽查文档均保持 fail-fast/no mock/no silent downgrade/no dirty release input/no HTTP-only completion 的方向。

## Milestone 4 - Report

- GREEN: verification-report -> PASS，已写入 `verification-report.md`。
- STATUS: completed。
