# 更新主程序路径描述

## Task Goal

将维护仓中面向后续任务的“主程序 / IntRuoyi 根目录”描述从旧 `D:\ProjectPackage\Int\IntRuoyi` 更新为 `E:\IntRuoyi`，并记录当前实际目录映射：

- 主程序根目录：`E:\IntRuoyi`
- 后端目录：`E:\IntRuoyi\IntRuoyiBackend`
- 前端目录：`E:\IntRuoyi\IntRuoyiFronted`

本任务只更新长期规则、门禁和预检入口中的前瞻性路径描述，不修改运行控制台实际配置、发布脚本、测试契约或历史任务日志。

## Milestones

- [x] 创建任务记录，明确只做文档描述变更。
- [x] 读取经验索引并摘取本任务适用门禁。
- [x] 更新长期规则和预检入口中的主程序路径描述。
- [x] 定向检索验证旧路径描述已从目标文档中移除，并确认新路径映射存在。
- [x] 标记任务完成并记录最终验证结果。

## Expected Verification

- 使用 UTF-8 读取/写入中文 Markdown 和 `AGENTS.md`。
- 定向检索 `AGENTS.md` 与 `docs`，排除 `docs/request-command-log.md` 和历史任务目录后，确认旧主程序根目录不再作为前瞻性描述出现。
- 定向检索确认 `E:\IntRuoyi`、`E:\IntRuoyi\IntRuoyiBackend`、`E:\IntRuoyi\IntRuoyiFronted` 均已记录。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，更新长期规则和门禁入口，避免后续任务继续引用旧主程序路径。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- Trigger: 修改包含中文的长期规则、Markdown 预检入口、路径说明或任务文档。
- Preflight check: 先创建任务目录，读取 `docs/experience-index.md`，命中 PowerShell / 中文编码门禁时读取 `docs/powershell-preflight-lessons.md`；所有中文读写显式使用 UTF-8。
- Blocker: 使用默认 `Get-Content` / `Set-Content` / `Out-File` / `>` / `>>` 处理中文，或命令依赖 `&&` 串联。
- Verification: UTF-8 回读目标文件，运行定向 `rg` 结构性检索和 `git diff --check`。
- Forbidden action: 不得批量替换历史任务日志或运行配置，不得用默认编码继续处理中文文件。
- Evidence: `docs/experience-index.md` 写入规范与 `docs/powershell-preflight-lessons.md` 门禁摘要。

## Current Status

completed

## Verification Result

- GREEN: targeted-old-path-search -> PASS，`rg -n --hidden --glob '!**/.git/**' --glob '!doc/tasks/**' --glob '!docs/request-command-log.md' "D:\\ProjectPackage\\Int\\IntRuoyi\\|D:/ProjectPackage/Int/IntRuoyi/" AGENTS.md docs` 返回 `NO_MATCH`。
- GREEN: new-path-structure-search -> PASS，已确认目标文档包含 `E:\IntRuoyi`、`E:\IntRuoyi\IntRuoyiBackend`、`E:\IntRuoyi\IntRuoyiFronted`。
- GREEN: diff-check -> PASS，`git diff --check -- <task-owned-files>` 退出码为 0；仅输出 Git 换行规范 warning，不影响内容校验。
