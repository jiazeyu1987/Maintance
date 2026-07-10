# 测试服发布完成性验证报告

## 结论

`release-20260709-current-head-test-v9` 的仅测试服发布验收通过。构建产物只包含冻结的已提交代码，测试服真实运行态、运行控制台版本号和变更说明均已验证。正式服、备份服、`mark-tested` 和 promote 动作未执行。

独立验收、任务级临时产物清理和 worktree 收尾均已通过，任务状态为 `completed`。

## 冻结发布输入

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Maintenance commit | PASS | `1fe4d64a6d4a8840aca061aca3c0c6d72a07d280` |
| Backend commit | PASS | `f1ef04912951ef15ae0d2881c974c964c182d76e` |
| Frontend commit | PASS | `d33339bd7e29f705d12d92d8409d7bc37d314566` |
| Worktree clean | PASS | `r260710v9audit\m`、`\b`、`\f` 的 porcelain count 均为 0 |
| 未提交改动进入构建 | PASS | Manifest v1 双仓 `dirty=false` |

## 构建包

| 检查项 | 结果 |
| --- | --- |
| releaseTag | `release-20260709-current-head-test-v9` |
| publishScope / component | `code-only` / `intruoyi` |
| change summary | `Release package release-20260709-current-head-test-v9` |
| build operation | `op-2026-07-10T005259232612400Z-cb2a74e8-4ae2-4b97-a24a-ae0398d266b2` / SUCCESS |
| publish-test operation | `op-2026-07-10T011318297410400Z-dbee4822-c99c-40ff-894c-71f75679440a` / SUCCESS |
| artifact integrity | 281 项；missing=0、sizeMismatch=0、badHashFormat=0、hashMismatch=0 |
| 禁止数据目录 | `database`、`db-dump`、`mysql-dump`、`minio`、`files`、`runtime-data`、`data`、`docker-build-context` 均不存在 |

## 测试服真实运行态

| 检查项 | 结果 |
| --- | --- |
| `.env IMAGE_TAG` | v9 |
| compose backend/frontend | v9 |
| 实际 backend/frontend 镜像 | v9 |
| 容器状态 | backend/frontend 均 running |
| backend health | HTTP 200，`{"status":"UP"}` |
| frontend | HTTP 200，3807 bytes |
| release-info | v9、摘要、双仓提交、`dirty=false`、`code-only`、`intruoyi` 全匹配 |
| 活动发布进程 | 0 |
| release lock | test / v9 / APPLIED |
| migration | 270 条 `SKIPPED_ALREADY_APPLIED`，失败 0 |
| 目标唯一索引 | unique，列为 `tenant_id,route_version_id,route_process_id,deleted` |
| 活动冲突组 | 0 |

## 真实页面

- Playwright 从真实测试服登录页使用测试租户 `aoteman` 登录。
- 最终页面为 `/infra/monitors/runtime-control`。
- 全局版本角标显示 v9。
- “版本变更说明”显示 v9、摘要、backend/frontend commit、`code-only` 和 `intruoyi`。
- 浏览器 `consoleErrorCount=0`。

## 环境边界

- 修复发布只连接测试服务器 `172.30.30.58`。
- 正式服 `172.30.30.57` 连接次数为 0。
- 备份服 `172.30.30.59` 连接次数为 0。
- `mark-tested`、`promote-prod`、`promote-backup` 执行次数均为 0。

## 已知问题

- 运行控制台 Linux 后端仍调用 `powershell.exe`，导致运维矩阵 `ERROR/unknown`。该问题不用于覆盖独立真实运行态；若后续验收明确要求矩阵健康，必须作为阻塞缺陷修复。
- 修复发布原始 stdout 含 274 处明文 MySQL 密码命令。原始日志不得提交，完成摘要后必须删除；发布日志器需后续实现源头脱敏。
- Windows text 模式向 SSH bash 发送脚本会引入 CRLF；已改用 UTF-8 bytes + LF 并固化门禁。
- Manifest SHA256 字段含 `sha256:` 前缀；校验器必须按 schema 规范化后比较。

## 验收判定

- 构建产物只包含当前冻结 HEAD 已提交代码：PASS。
- 测试服务器发布成功：PASS。
- 测试服真实运行态检查通过：PASS。
- 运行控制台显示当前版本号和变更说明：PASS。
- 所有问题已记录：PASS。
- 问题已沉淀为前置经验：PASS。
- 本任务临时产物与 worktree 清理：PASS；仅保留 `task.md`、`execution-log.md`、`verification-report.md`，三个冻结 worktree 的 Git 注册和物理目录均已删除。
