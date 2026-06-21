# 任务：三台服务器配置 Codex CLI 运行环境

## 任务目标

在测试服务器 `172.30.30.58`、正式服务器 `172.30.30.57`、备份服务器 `172.30.30.59` 上配置好 Codex CLI 的运行环境，使其连接参数与本机一致，并分别通过真实 `codex exec` 验证。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\task.md`
- 状态：`BLOCKED`
- 处理：该任务已因用户切换目标显式阻塞，不再与本任务并行推进；当前新任务单独建档并接管线程执行。

## 用户要求与执行边界

- 用户要求：
  - 在测试服务器、正式服务器、备份服务器配置好 Codex CLI
  - 连接参数与本机相同
  - 三台服务器都必须实际跑通才算完成
- 当前任务授权：
  - 允许通过 SSH 对三台服务器执行安装、配置和必要写入
  - 允许读取本机 `C:\Users\BJB110\.codex\config.toml` 与 `auth.json`，并以不入仓的方式同步远端认证文件
- 禁止范围：
  - 不把 SSH 凭据、API key 或认证文件内容写入仓库、任务文档、可提交脚本或最终答复
  - 不顺带执行发布、重启、备份、恢复、数据库写入或业务容器改动
  - 不复制 Windows 专用的桌面/MCP/通知配置到 Linux 服务器

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 测试服、正式服、备份服写入必须有用户当前任务授权；本任务已获得明确授权。
  - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
  - 服务器动作前必须确认目标主机、目标目录和授权范围；本任务目标仅限 Codex CLI 安装与 `~/.codex` 配置。
  - 备份服与正式服按同等级高门禁处理，即使只是安装 CLI，也必须逐台记录目标与关键输出。
  - 环境级操作前先核对本机有效配置、认证来源与远端前置条件；任一缺失直接阻塞。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。优先确认最小可复制配置、统一安装方式和真实冒烟口径，而不是临时在某台机器单独凑环境。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 三台服务器可用同一本机连接参数跑通 Codex CLI -> Given 本机已存在可工作的 Codex CLI 配置与文件型认证 / When 在测试服、正式服、备份服安装 Codex CLI 并同步最小连接配置 / Then 三台服务器都必须通过真实 codex exec 冒烟验证。`
- `BDD: 前置条件缺失必须直接阻塞 -> Given 任一服务器缺少 SSH、安装网络、认证文件或写权限 / When 尝试进入远端安装 / Then 必须先记录具体缺口并停止，不得用 mock、占位配置或静默降级继续。`

## 里程碑

1. 收口上一任务并建立本任务文档、执行日志、测试计划和请求记录。`DONE`
2. 明确本机有效连接参数、认证来源、官方安装方式与远端最小同步集。`DONE`
3. 完成高风险动作前的 `experience-preflight` 与三台服务器只读预检。`DONE`
4. 在测试服务器安装 Codex CLI、落地最小配置并完成真实冒烟。`DONE`
5. 在正式服务器安装 Codex CLI、落地最小配置并完成真实冒烟。`DONE`
6. 在备份服务器安装 Codex CLI、落地最小配置并完成真实冒烟。`DONE`
7. 汇总最终状态、执行收尾预览并整理提交范围。`DONE`

## 预期验证

- `execution-log.md` 中存在 `GREEN: experience-preflight -> PASS`
- 三台服务器上 `codex --version` 都成功
- 三台服务器上 `~/.codex/config.toml` 与 `auth.json` 都到位
- 三台服务器上真实 `codex exec` 冒烟都返回 `OK`
- 仓库提交范围内不包含任何密钥值

## 当前状态

COMPLETED：测试服务器 `172.30.30.58`、正式服务器 `172.30.30.57`、备份服务器 `172.30.30.59` 均已完成 Codex CLI 环境配置，并通过真实 `codex exec` 冒烟返回 `OK`；其中备份服因直连 GitHub release 超时，改为中转同版官方二进制完成安装，最终运行验证通过。

## Current Status

COMPLETED
