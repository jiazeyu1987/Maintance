# 20260724 推送维护仓到 GitHub

## Task Goal

将维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 的 `int_main` 历史清理后推送到 `https://github.com/jiazeyu1987/IntRuoyiMaintance.git`，并记录远端、分支、验证和结果。

## Milestones

- [x] 创建任务记录并摘取适用门禁。
- [x] 检查当前 Git 状态、分支、远端和待推送提交。
- [x] 执行非强制推送并捕获远端拒绝原因。
- [x] 经用户授权，在隔离克隆中重写历史，移除 GitHub 超限 evidence 文件。
- [x] 扫描清理后的 `int_main` 历史，确认无超过 100 MB 的可达 blob。
- [x] 推送清理后的 `int_main` 到目标 GitHub 仓库并验证远端引用。

## Expected Verification

- `git status --short --branch` 显示当前分支状态。
- `git ls-remote --heads https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main` 显示远端 `int_main`。
- 可达 blob 扫描无超过 GitHub 100 MB 限制的文件。
- `git push https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main:int_main` 成功。

## 经验门禁

### PowerShell / Git 命令与 UTF-8 输出门禁

- Trigger: Windows PowerShell 下执行 Git 推送、状态检查、任务记录写入或输出含中文的命令。
- Preflight check: 设置 PowerShell 输入/输出编码为 UTF-8；中文文件读写使用 UTF-8；不用 `&&` 串联命令。
- Blocker: 必需的状态检查无法读取、远端 URL 不匹配、当前分支无法确定、认证失败、远端拒绝或存在未确认的本任务相关待提交内容。
- Verification: 记录 `git status --short --branch`、`git push` 结果和远端引用。
- Forbidden action: 禁止用 fallback 远端、强推、静默忽略未提交改动、改写凭据、重置工作区或跳过推送失败。
- Evidence: 用户请求“推送到 jiazeyu1987/IntRuoyiMaintance.git”；`docs/experience-index.md` 的 PowerShell / 命令编排路由；本任务 `execution-log.md`。

### GitHub 推送前历史大文件门禁

- Trigger: 将维护仓推送到 GitHub、迁移远端或首次初始化远端仓库。
- Preflight check: 推送前扫描已提交历史中的 blob 大小，确认没有超过 GitHub 100 MB 单文件限制的对象。
- Blocker: `git push` 返回 `GH001: Large files detected`、`pre-receive hook declined`，或本地历史扫描发现任一 blob 超过 100 MB。
- Verification: 记录 `git ls-tree -l` 或等价历史扫描、目标远端 URL、分支和 `git push` 退出码。
- Forbidden action: 禁止未经用户明确授权就强推、静默改写历史、自动迁移 Git LFS 或创建无历史快照分支替代推送。
- Evidence: `docs/release-build-preflight-lessons.md#2026-07-24-github-推送前历史大文件门禁`；本任务 `execution-log.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，移除远端拒绝的历史超限对象并补充推送前门禁。
- 是否存在临时补丁或绕过：否。

## Current Status

completed
