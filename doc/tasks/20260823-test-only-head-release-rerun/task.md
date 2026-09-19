# 20260823 仅测试服 HEAD 发布重试

## Task Goal

冻结本次开始时三个仓库的最新已提交 HEAD，在专用干净 release worktree 中构建维护控制台和 IntRuoyi 测试发布包，仅发布 `172.30.30.58`；未提交改动不得进入产物，禁止 `mark-tested`、`promote-prod`、`promote-backup`。

## Milestones

1. 发布授权、经验门禁和三仓 Git 输入冻结。
2. 创建并验证本轮专用干净 release worktree，记录目标提交、构建目录和状态。
3. 构建维护控制台和发布包，验证 manifest、artifact、版本号、变更说明与冻结提交一致。
4. 仅执行 `publish-test`，验证 operation、远端 tag、镜像、容器、health、HTTP 和页面。
5. 用 Playwright 验证运行控制台版本号和变更说明，记录所有问题并沉淀前置经验。
6. `ready_for_closeout` 后清理本任务 worktree，完成最终证据。

## Expected Verification

- 三仓冻结 HEAD 与 release worktree clean 状态可审计。
- `manifest.json`、legacy manifest、artifact SHA256、版本号和变更说明均绑定冻结提交。
- 测试服 operation=`SUCCESS`，`.env`、实际镜像 tag、容器、health、frontend HTTP 及真实页面全部通过。
- 运行控制台显示本次 releaseTag、版本号、变更说明和冻结提交。
- 任务问题记录包含现象、阶段、影响、原因、动作、结果、前置检查、自动化和避免措施。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；任一关键来源或验证缺失立即停止。
- 是否从根因和长期维护角度解决：是；使用现有发布脚本和正式测试服门禁。
- 是否存在临时补丁或绕过：否；不修改业务代码、不手工改远端状态、不跳过验证。

## 经验门禁

- Trigger：仅测试服 HEAD 发布、build-release、publish-test、运行态和运行控制台验收。
- Preflight check：先读取发布、服务器、登录、worktree、PowerShell 和经验索引；冻结三仓 HEAD；脏主工作区只能使用本轮专用 clean worktree。
- Blocker：来源提交、manifest、版本/变更说明、operation、远端 tag、镜像、容器、health、HTTP 或页面无法证明时停止。
- Verification：任务日志记录 worktree、构建目录、releaseTag、manifest、publish operation、远端运行态和 Playwright 证据。
- Forbidden action：禁止从脏主工作区构建、拼接 releaseTag、发布正式/备份服、mark-tested、手工改库/`.env`/lock、API-only 代替真实页面。
- Evidence：`task.md`、`execution-log.md`、`verification-report.md`、构建 manifest、发布 operation 和远端/页面证据。

## Current Status

blocked

## Blocker

冻结 app HEAD `ef217fe2ca8887e5b4242d0823f203179d6b059e` 中的 `IntRuoyiFronted/src/views/dcc/controlled-file/training/components/TrainingRulesReadonlyTab.vue` 是 0 字节 tracked 文件，Vite 报 `At least one <template> or <script> is required`。因此没有发布包、manifest 或 releaseTag 可发布，本轮未执行 `build-release`、`publish-test` 或任何测试服写操作。
