# 当前提交仅测试服发布完成性审计与修复

## 任务目标

对 `release-20260709-current-head-test-v9` 的原仅测试服发布执行完成性审计，重新验证冻结提交、发布包、测试服真实运行态、运行控制台版本与变更说明、问题记录和经验沉淀。若发现由后续并发任务造成的测试服状态漂移，仅使用原冻结发布提交和既有 v9 包修复测试服，不重新追逐源分支后续提交，不操作正式服或备份服。

## 里程碑

- [x] M1：读取发布、构建、PowerShell、worktree 和独立验证门禁。
- [x] M2：核对原发布任务、冻结提交、发布包和临时 worktree 收口。
- [x] M3：重新校验 Manifest v1、legacy manifest 和 281 项产物。
- [x] M4：修复测试服由后续并发发布造成的目标版本漂移，恢复冻结 v9。
- [x] M5：重新验证镜像、容器、健康、HTTP、真实页面、版本号和变更说明。
- [x] M6：复核问题记录、经验沉淀、环境边界并完成独立验证和收尾。

## 预期验证

- v9 发布包来源提交为 backend `f1ef0491`、frontend `d33339bd` 且 `dirty=false`。
- 281 个发布产物大小和 SHA256 全部匹配。
- 测试服 `.env IMAGE_TAG`、compose 解析镜像、实际前后端镜像和 `release-info.json` 全部为 v9。
- 后端 health=`UP`，前端 HTTP 200，真实页面可登录并显示 v9 版本与变更说明。
- 正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup` 均不执行。
- 并发任务 `r260710dccpg` 的 worktree、进程和任务文件不被停止、删除或提交。

## 经验门禁

- 发布完成性不能仅依赖历史 `COMPLETED`；发布证据目录已清理时必须从发布包和当前远端状态重建证据。
- 发现 `.env`、compose 与实际镜像不一致必须 fail fast，不得把健康检查单点当作发布完成。
- 修复只允许使用原冻结提交对应的发布脚本和既有 releaseTag，不重新构建或混用后续源码提交。
- 远端写入前确认没有活动发布进程，并记录 `GREEN: experience-preflight -> PASS`。
- 只允许目标 `172.30.30.58`，禁止连接或操作 `172.30.30.57`、`172.30.30.59`。
- 临时审计/修复 worktree 必须记录提交、路径、状态和最终清理结果。
- 全局、父目录、维护仓和业务仓 `AGENTS.md` 必须按“更近层级限定同主题、任务归属隔离、仅测试服范围优先、日志凭据脱敏”消除冲突，避免后续发布误判或误清理并发任务。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；通过原冻结发布流程恢复完整版本契约，而不是只忽略 `.env` 漂移。
- 是否存在临时补丁或绕过：否；不手工伪造成功状态，不改正式服/备份服，不复用并发任务运行控制台。

## Current Status

completed

## Current Result

- 冻结发布输入：maintenance=`1fe4d64a6d4a8840aca061aca3c0c6d72a07d280`、backend=`f1ef04912951ef15ae0d2881c974c964c182d76e`、frontend=`d33339bd7e29f705d12d92d8409d7bc37d314566`，三个审计 worktree 均 clean。
- 发布包：`release-20260709-current-head-test-v9`，`publishScope=code-only`，组件 `intruoyi`，双仓 `dirty=false`，281/281 artifact 的大小与 SHA256 全部通过。
- 原始 operation：build=`op-2026-07-10T005259232612400Z-cb2a74e8-4ae2-4b97-a24a-ae0398d266b2` SUCCESS；publish-test=`op-2026-07-10T011318297410400Z-dbee4822-c99c-40ff-894c-71f75679440a` SUCCESS。
- 测试服最终状态：`.env`、compose、实际前后端镜像、`release-info.json`、release lock 均为 v9；容器 running；后端 HTTP 200/UP；前端 HTTP 200。
- 真实页面：测试租户 `aoteman` 登录运行控制台成功，版本角标与“版本变更说明”显示 v9、摘要和双仓提交，console error=0。
- 环境边界：修复发布日志仅连接 `172.30.30.58`；未连接 `.57` 或 `.59`，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 已知非降级缺陷：运行控制台 Linux 后端仍尝试 `powershell.exe`，矩阵显示 `ERROR/unknown`；真实运行态和版本对话框已独立验证，缺陷已公开记录。
- 规则与经验提交：维护仓 `a2dbeaeac78197850d740a95c342f5c5d79f2988`；业务仓 AGENTS 冲突修复 `a3aa3a06f35f6d89b321983845975c675cb12ab0`；全局 AGENTS 同步增加规则优先级、任务归属和日志脱敏边界。
- 收尾：task-closeout preview/apply 通过；只保留三份核心任务记录；三个冻结 worktree 注册和物理目录均已删除；任务状态 `completed`。

## Cleanup Candidates

- `doc/tasks/20260710-current-head-test-only-release-completion-audit/repair-publish-v9-20260710-144948.out.log`
- `doc/tasks/20260710-current-head-test-only-release-completion-audit/repair-publish-v9-20260710-144948.err.log`
- `doc/tasks/20260710-current-head-test-only-release-completion-audit/runtime-console-v9-ui-check.mjs`
- `doc/tasks/20260710-current-head-test-only-release-completion-audit/runtime-console-v9-release-dialog.png`
