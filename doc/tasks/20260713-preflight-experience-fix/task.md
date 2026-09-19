# 20260713 前置经验问题修复

## Task Goal

修复 `20260713-preflight-experience-audit` 发现的前置经验错误和冲突，包括过期 migration gate 参数、PowerShell bootstrap 与 task-doc-first 顺序冲突、测试服主门禁 Evidence 缺失、索引锚点漂移、仅测试服/完整发布表述歧义和少量格式残留。

## Milestones

- [x] 创建任务目录和任务记录。
- [x] 修复维护仓测试服发布、构建发布、PowerShell、经验索引和 AGENTS 规则。
- [x] 修复主项目 AGENTS、experience-index 和 PowerShell 共同规则中的启动顺序冲突。
- [x] 更新请求命令日志和验证证据。
- [x] 运行 UTF-8、diff check、关键词路由和脚本参数验证。

## Expected Verification

- `run-release-migration-policy-gate.py` 推荐命令不再使用不支持的 `--json`，改为当前 `--output` 契约，并要求先读冻结 worktree 的 `--help`。
- PowerShell/Windows shell 任务明确允许唯一只读 UTF-8 bootstrap 作为 task-doc-first 的前置例外。
- 测试服发布主门禁摘要包含 `Evidence`。
- 经验索引不再依赖已漂移的脆弱锚点。
- 仅测试服发布和完整三环境发布范围表述不再互相误导。
- `git diff --check`、UTF-8 回读和关键词检查通过。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，直接修正规则来源、命令契约和索引路由。
- 是否存在临时补丁或绕过：否。

## BDD Scenarios

- BDD: migration gate command matches frozen script -> Given 当前冻结后端脚本只支持 `--output`, When 发布前置经验给出推荐命令, Then 文档不得推荐 `--json`，且必须要求先检查 `--help`。
- BDD: PowerShell bootstrap order is executable -> Given Windows 任务需要 PowerShell, When 任务启动, Then 唯一只读 UTF-8 bootstrap 可以先于任务文档写入执行，随后必须立即创建任务文档并提取经验门禁。
- BDD: test-only release scope remains bounded -> Given 用户只授权测试服发布, When 读取完整发布经验文档, Then 文档必须指向 `test-release-preflight.md` 作为仅测试服范围权威，禁止误导执行 mark-tested/prod/backup。

## 经验门禁

### 前置经验修复门禁

- Trigger: 修复前置经验、发布经验、PowerShell 经验或经验索引路由。
- Preflight check: 依据 `20260713-preflight-experience-audit/verification-report.md` 逐项修复；每项必须保留可执行检查、阻塞条件和证据来源。
- Blocker: 修复后仍存在过期命令、无法执行的规则顺序、缺失六字段摘要、允许降级/跳过验证或仅测试服误发 prod/backup 的表述。
- Verification: `git diff --check`、UTF-8 回读、关键词 `rg`、脚本 `--help` 与索引路由复查。
- Forbidden action: 不得只改任务报告而不改长期入口；不得把历史失败命令继续保留为主推荐命令；不得引入 fallback。
- Evidence: 本任务 `execution-log.md`、`verification-report.md` 和修改后的经验文档。

## Current Status

completed - 已修复审查报告列出的高/中/低优先级前置经验问题；验证通过，未执行发布或服务器操作。
