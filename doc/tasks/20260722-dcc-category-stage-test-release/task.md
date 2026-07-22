# DCC 类别阶段测试服前端发布

## Task Goal

将当前已提交的 DCC 文件分类阶段统一前后端代码发布到测试服务器 `172.30.30.58`，解决测试服类别列表“阶段”列仍显示旧 `01 plan / 02 input` 文案的问题。发布范围仅限测试服。

## Scope

- 源提交：维护仓、后端仓、前端仓当前已提交 HEAD。
- 目标环境：测试服务器 `172.30.30.58`。
- 发布范围：`build-release -> publish-test -> 测试服运行态和页面验证`。
- 禁止动作：不执行 `mark-tested`、`promote-prod`、`promote-backup`；不操作正式服或备份服。

## Milestones

- P0 前置门禁：读取发布、PowerShell、服务器、登录和 worktree 门禁。
- P1 冻结输入：创建本轮维护/后端/前端干净 release worktree 并记录提交。
- P2 构建发布包：通过运行控制台执行 code-only `build-release`。
- P3 发布测试服：执行 `publish-test`，确认 operation 成功。
- P4 运行态验证：确认测试服 `.env`、实际镜像、health、HTTP 入口和 release-info。
- P5 页面验证：重新执行 DCC 类别阶段页面 E2E，确认阶段列显示新分类阶段。

## BDD Scenarios

- BDD: 测试服前端使用新阶段逻辑 -> Given 测试服已绑定 `file_type_taxonomy_id`; When 发布当前前端到测试服; Then 类别列表阶段列显示 DCC 文件分类阶段名。
- BDD: 仅测试服发布边界 -> Given 用户只要求测试服与本机一致; When 发布完成; Then 不执行正式服、备份服或 mark-tested 动作。

## Expected Verification

- GREEN: release-worktrees-clean -> PASS。
- GREEN: build-release -> SUCCESS。
- GREEN: publish-test -> SUCCESS。
- GREEN: runtime-test-verify -> PASS。
- GREEN: dcc-category-stage-page-e2e -> PASS。

## 经验门禁

- 测试服发布：只走 `build-release -> publish-test`，发布后验证真实运行态和页面；禁止拼接不同 releaseTag。
- 临时 worktree：构建输入必须来自干净 release worktree，主工作区脏改不得进入发布包。
- code-only：`SkipDatabaseSync` / `SkipMinioSync` 不跳过 schema 与 required SQL 门禁，manifest 必须证明 publishScope。
- PowerShell/SSH：显式 UTF-8，避免 here-string 和复杂多层引号；输出不得泄露凭据。
- 运行态：成功判定必须同时看 operation、manifest、远端 `.env IMAGE_TAG`、实际镜像、health、HTTP、release-info 和页面 E2E。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布已提交的新阶段派生逻辑，而不是临时改静态文件。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Progress

- P0: completed，已确认页面 E2E 失败根因是测试服前端旧构建，发布边界限定为测试服。
- P1: completed，已使用 release worktree 输入，前端提交 `a0dd9098fb3b9177fd3c6b516bd94ee400952bd0`。
- P2: completed，frontend-only `build-release` 已通过，发布包为 `release-20260722-dcc-category-stage-test-r260722b-r1`。
- P3: completed，测试服 frontend-only `deploy-release` 已成功。
- P4: completed，测试服 `.env IMAGE_TAG`、前端镜像、首页、`release-info.json` 和后端 health 已验证。
- P5: completed，真实页面 E2E 已通过，阶段列无旧 `01 plan / 02 input` 值。
