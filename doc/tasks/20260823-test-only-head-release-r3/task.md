# 20260823 仅测试服 HEAD 发布（r3）

## Task Goal

冻结本次发布开始时维护仓与 IntRuoyi 主程序仓的最新已提交 HEAD，在本轮专用干净 release worktree 中构建维护控制台和测试发布包，仅发布测试服务器 `172.30.30.58`。未提交改动不得进入构建产物；禁止 `mark-tested`、`promote-prod`、`promote-backup`。

## Milestones

1. 完成发布授权、经验门禁和当前分支 Git 输入冻结。
2. 创建并验证本轮专用 clean release worktree，记录目标提交、构建目录和状态。
3. 构建维护控制台和发布包，核对 manifest、artifact、版本号和变更说明与冻结提交一致。
4. 仅执行 `publish-test`，验证 operation、远端 tag、镜像、容器、health、HTTP 和页面。
5. 用真实页面验证运行控制台版本号和变更说明，记录全部问题并沉淀前置经验。
6. `ready_for_closeout` 后执行 cleanup preview/apply，删除本任务临时 worktree 并完成最终证据。

## Expected Verification

- 冻结 HEAD、分支、dirty 状态、worktree 路径和构建目录可审计。
- 发布包 `manifest.json`、legacy manifest、artifact hash、版本号和变更说明均绑定冻结提交。
- 同一 releaseTag 的 `build-release -> publish-test` 成功；不执行正式/备份/推广动作。
- 测试服真实运行态满足 operation=`SUCCESS`、`.env IMAGE_TAG`、实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、真实页面和运行控制台 release-info。
- 所有问题记录现象、阶段、影响、原因判断、处理动作、结果、前置检查、自动化和避免措施。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；缺任何来源、manifest、版本/变更说明或运行态证据立即停止。
- 是否从根因和长期维护角度解决：是；使用现有发布脚本、正式测试服入口和冻结 worktree。
- 是否存在临时补丁或绕过：否；不修改业务代码、不复用旧发布包、不手工改远端状态、不跳过门禁。

## 经验门禁

- Trigger：仅测试服 HEAD 发布、build-release、publish-test、真实运行态和运行控制台验收。
- Preflight check：读取 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、PowerShell、服务器、登录和 worktree 文档；冻结维护/app HEAD；脏主工作区只能使用本轮专用 clean worktree。
- Blocker：来源提交、worktree clean、manifest、版本/变更说明、operation、远端 tag、镜像、容器、health、HTTP 或真实页面无法证明时停止；冻结 HEAD 含空 Vue SFC 时禁止进入构建。
- Verification：`execution-log.md` 记录 `GREEN: experience-preflight -> PASS` 或 blocker、worktree、构建命令、releaseTag、manifest、发布 operation、远端运行态和 Playwright 证据。
- Forbidden action：禁止从脏主工作区构建、拼接 releaseTag、追逐构建开始后的提交、发布正式/备份服、`mark-tested`、手工改库/`.env`/lock、API-only 代替真实页面。
- Evidence：本任务 `task.md`、`execution-log.md`、`verification-report.md`、构建 manifest、operation 和页面/远端证据。

## Current Status

blocked

## Blocker

冻结 app HEAD `0002767c0486f11d82bd82666bf8b0f164aee597` 的 tracked 文件 `IntRuoyiFronted/src/views/dcc/controlled-file/training/components/TrainingRulesReadonlyTab.vue` 为 0 字节。专用 clean worktree 中静态扫描得到 `zero-byte-vue-count=1`，该文件的 Git blob size 也为 `0`；Vite SFC 合同不满足，不能生成可靠的前端构建、发布包、manifest、版本号或变更说明。构建、`build-release`、`publish-test` 和远端写入均未执行，旧包/旧 releaseTag/旧运行态证据不得复用。

## Worktree Evidence

- Maintenance worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823d\m`, detached HEAD `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`, clean。
- App worktree: `D:\IntRuoyiWorktree\r260823d\a`, detached HEAD `0002767c0486f11d82bd82666bf8b0f164aee597`, clean。
- Main workspaces were dirty at freeze; no dirty content entered either worktree.
- During worktree creation, app main branch advanced to `a6574c3631dfa3c5f8381596fcef5c91acd98db0`; this post-freeze drift was not followed, consistent with the user instruction to keep the release-start worktree baseline.
- Continuation check 2026-08-23 16:32：当前 app `int_main` 已为 `a6574c3631dfa3c5f8381596fcef5c91acd98db0` 且与 `origin/int_main` 同步，但目标 SFC 仍为 0 字节；因此没有解除本任务的构建前阻塞。

## Milestone Status

- Milestone 1: completed，发布范围、经验门禁和冻结 HEAD 已记录。
- Milestone 2: completed，两个专用 detached worktree 已创建并验证 clean。
- Milestone 3: blocked，冻结 app HEAD 含 0 字节 tracked Vue SFC，构建前契约失败。
- Milestone 4-6: not started，未生成 releaseTag，未执行测试服发布、运行态验收或 closeout。

## Root Cause Evidence

`TrainingRulesReadonlyTab.vue` 在提交 `5f0138e4c3bd6cabfef97f45dbd287e4b3072aa2` 中由 248 行（blob `ae4079ae3`）变为 0 行（blob `e69de29bb`）；当前 `int_main` 的 `a6574c363...` 只是后续文档提交，未恢复该文件。解除条件是有效 Vue SFC 内容以新的已提交提交进入目标分支，再从该新 HEAD 建立新发布 worktree 和新 releaseTag；本任务不得自行修复或选择旧提交绕过“当前 HEAD”要求。
