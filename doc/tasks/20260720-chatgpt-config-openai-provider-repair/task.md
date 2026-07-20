# 20260720 ChatGPT Config OpenAI Provider Repair

## Task Goal

- 修复本机 `C:\Users\BJB110\.codex\config.toml` 中缺失的 `OpenAI` provider 定义，消除 `Model provider "OpenAI" not found`，并在保存后重新打开当前对话串。

## Milestones

- M1: completed - 建立任务记录并摘取本任务适用的经验门禁。
- M2: completed - 只读核对当前 `config.toml`，确认缺失项与影响范围。
- M3: completed - 以最小改动补齐 `OpenAI` provider 定义并保存备份。
- M4: completed - 验证 TOML 可解析且 `OpenAI` provider 已可被识别，然后重新打开当前对话串。

## Expected Verification

- `C:\Users\BJB110\.codex\config.toml` 中存在 `[model_providers.OpenAI]`。
- 使用本机解析命令可成功读取 TOML，且 `model_providers` 包含 `OpenAI`。
- 当前对话串已重新打开。

## Current Status

- completed

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## 经验门禁

### PowerShell UTF-8 与退出码门禁

- Trigger: 本任务使用 PowerShell 读取和写入本机配置文件，并输出含中文的任务记录。
- Preflight check: 读取 UTF-8 文件时显式使用 `-Encoding utf8` 或 UTF-8 aware runtime；写配置文件后必须回读或重新解析验证；若原生命令后还有收尾动作，需保留真实退出码。
- Blocker: 若无法确认目标配置文件路径、无法以 UTF-8 读取/写回、或保存后解析失败，必须立即停止并报告影响。
- Verification: 回读 `config.toml` 的 provider 段，并使用 `python -X utf8` + `tomllib` 解析确认 `OpenAI` provider 存在。
- Forbidden action: 禁止使用默认编码重写中文文件；禁止靠兜底 provider、静默跳过或未验证保存结果来宣称修复完成。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`

## Final Verification Result

- `C:\Users\BJB110\.codex\config.toml` 已补齐 `[model_providers.OpenAI]`。
- `python -X utf8` + `tomllib` 解析通过，`DEFINED_PROVIDERS=OpenAI,asxs`。
- 本任务创建的临时备份已删除，当前对话串已重新打开。
