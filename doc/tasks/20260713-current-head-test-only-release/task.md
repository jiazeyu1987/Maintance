# 20260713 当前 HEAD 仅测试服发布

## Task Goal

基于本轮开始时当前分支最新已提交 HEAD 创建干净临时发布 worktree，构建 IntRuoyi 维护控制台与 code-only 测试发布包，仅发布到测试服务器 `172.30.30.58`，完成真实运行态、页面版本号和变更说明验证，并沉淀可复用前置经验。

## User Constraints

- 当前系统仍在开发中，本轮只允许构建并发布到测试服务器。
- 构建产物只能包含当前分支 HEAD 已提交代码；未提交改动和未跟踪文件不得进入构建产物。
- 主工作区较脏时，必须从当前分支 HEAD 创建干净临时 release worktree，并证明构建只基于该 worktree。
- 程序持续更新时不追逐后续提交；本轮只构建发布开始时 worktree 记录的提交。
- 禁止执行 `mark-tested`、`promote-prod`、`promote-backup`，禁止发布正式服和备份服。
- manifest、版本号、变更说明、构建来源任一无法确认时必须失败，不得继续发布。

## Milestones

- [x] 创建任务目录、任务文档、执行日志和初始请求命令记录。
- [x] 读取并摘录仅测试服发布、worktree、PowerShell、服务器访问和运行态验收门禁。
- [x] 记录维护仓、后端仓、前端仓当前分支、HEAD 和 dirty 状态。
- [x] 从冻结 HEAD 创建本轮专用干净 release worktree 并验证 clean。
- [x] 构建维护控制台和测试发布包。
- [x] 校验 build operation、发布包、manifest、版本号和变更说明。
- [x] 执行 `publish-test`，且确认预览和实际目标仅为测试服。
- [x] 验证测试服真实运行态：镜像 tag、容器状态、health、HTTP、release-info。
- [x] 用真实页面验证运行控制台版本号和变更说明。
- [x] 记录全部问题并沉淀可执行前置经验。
- [x] 恢复运行控制台主路径，清理本轮临时 release worktree。
- [x] task-closeout preview/apply，通过后标记 completed 并提交隔离记录。

## Expected Verification

- 构建产物只来自本轮冻结 release worktree 的已提交代码。
- `build-release` 和 `publish-test` operation 均为 `SUCCESS`。
- 发布包根目录 `manifest.json` 存在，sourceRepos commit 匹配冻结 HEAD，dirty=false，版本号和变更说明可追溯到本次 releaseTag。
- 远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP、release-info 均匹配同一 releaseTag。
- 运行控制台真实页面显示当前版本号和变更说明，console error 为 0。
- 未执行正式服、备份服、mark-tested 或 promote 动作。
- 所有问题已按现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免记录。
- 可复用问题已沉淀到前置经验文档，临时 release worktree 已清理。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布任一门禁失败均 fail fast 并记录问题，不用旧包、旧 tag、手工标绿或 mock 成功替代。
- 是否存在临时补丁或绕过：否。

## BDD Scenarios

- BDD: clean committed release input -> Given 主工作区存在未提交或未跟踪内容, When 本轮测试服发布开始, Then 必须创建专用 release worktree 并只基于冻结 HEAD 构建。
- BDD: test-only deployment boundary -> Given 用户只授权测试服发布, When 构建和发布执行, Then 只允许 `build-release -> publish-test`，不得执行 mark-tested、promote-prod 或 promote-backup。
- BDD: manifest source verification -> Given build-release 完成, When 校验发布包, Then `manifest.json` 必须证明 sourceRepos commit 等于冻结提交且 dirty=false。
- BDD: real test runtime validation -> Given publish-test 成功, When 判定测试发布完成, Then 必须验证远端镜像、容器、health、HTTP、release-info 和运行控制台页面版本说明。

## 经验门禁

### 仅测试服发布范围门禁

- Trigger: 用户要求“仅测试服发布”“publish-test”或测试服运行态验收。
- Preflight check: 明确目标服务器 `172.30.30.58`，preview/submit 不得包含 `mark-tested`、`promote-prod`、`promote-backup`、正式服或备份服动作。
- Blocker: 发布目标无法证明为 test；任一 prod/backup/promote 动作出现；复用旧 releaseTag 拼接证据。
- Verification: 记录 releaseTag、build/publish operation、preview 字段、远端 `.env`、镜像、health、HTTP、release-info 和页面版本证据。
- Forbidden action: 禁止因测试服成功而标记 tested 或推广正式/备份。
- Evidence: `docs/test-release-preflight.md`。

### 干净 release worktree 门禁

- Trigger: 主工作区 dirty 且发布要求只包含 HEAD 已提交代码。
- Preflight check: 在 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/m|b|f` 创建本轮专用 release worktree，记录三仓 branch、commit、dirty=false。
- Blocker: worktree dirty、HEAD 与冻结提交不一致、构建输入来自主工作区或旧 worktree。
- Verification: `git rev-parse HEAD`、`git status --porcelain --ignored=no`、`git worktree list --porcelain`、最终物理目录清理结果。
- Forbidden action: 不得从脏主工作区构建，不得复用旧 release worktree。
- Evidence: `D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`、`docs/release-build-preflight-lessons.md`。

### Manifest 与版本说明门禁

- Trigger: `build-release` 完成后校验发布包、版本号和变更说明。
- Preflight check: 以发布包根目录 `manifest.json` 为权威；按 Manifest v1 校验 sourceRepos、publishScope、component、artifact hash、changeSet summary；legacy manifest 只按 legacy schema。
- Blocker: manifest 缺失、sourceRepos dirty=true、commit 与冻结 HEAD 不一致、版本号或变更说明无法确认、artifact 缺失或 hash 不一致。
- Verification: 记录 manifest 路径、releaseTag、sourceRepos、changeSet summary、artifact 总数和校验结果。
- Forbidden action: 不得用 legacy manifest、镜像缓存或 HTTP 200 替代 Manifest v1 来源证明。
- Evidence: `docs/release-build-preflight-lessons.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/release-backup-restore.md`。

### PowerShell / SSH / 日志脱敏门禁

- Trigger: PowerShell、SSH、Docker、MySQL、Playwright、release-info 或中文变更说明参与发布证据。
- Preflight check: 显式 UTF-8；不用 `&&`；远端多行脚本用 UTF-8 bytes + LF；release-info 用 JSON parser 或 CRLF-safe；保存/提交前扫描凭据。
- Blocker: 中文或 JSON 证据不可读、退出码/结构化结果无法证明状态、日志包含明文密码/token/private key/`mysql -p<secret>`。
- Verification: 记录命令退出码、结构化 JSON、HTTP status、health、脱敏扫描结果。
- Forbidden action: 不得提交 secret-bearing 原始日志，不得用 PowerShell 默认乱码渲染作为唯一证据。
- Evidence: `D:/ProjectPackage/Int/IntRuoyi/docs/powershell-memory.md`、`docs/powershell-preflight-lessons.md`。

### 运行态与页面验收门禁

- Trigger: publish-test 后判定测试发布成功。
- Preflight check: 同时验证 operation=SUCCESS、远端 `.env IMAGE_TAG`、实际镜像、容器 running、backend health=UP、frontend HTTP=200、PDF worker、release-info、运行控制台页面版本和变更说明。
- Blocker: 任一状态不匹配、release-info 解析失败、页面版本号/变更说明不可见、console 判定无法区分统计字段和真实错误。
- Verification: 证据中 releaseTag、backend commit、frontend commit、health、HTTP、页面 dialog 和 console error 均通过。
- Forbidden action: 不得只用 HTTP 200、容器 running 或 operation SUCCESS 替代完整运行态验收。
- Evidence: `docs/test-release-preflight.md`、`D:/ProjectPackage/Int/IntRuoyi/docs/release-backup-restore.md`。

## Current Status

completed - `release-20260713-current-head-test-r260713t-r3` 已仅发布测试服并通过 Manifest、真实运行态、release-info 和运行控制台页面版本变更说明验证；未执行 mark-tested/prod/backup。运行控制台已恢复主工作区 Jar，`r260713t` release worktree 与 state dir 已删除，task-closeout preview/apply 已通过且核心任务记录保留。

## Frozen Release Input

- Release worktree root: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t`
- External state dir: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t-state`
- Maintenance worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/m`
- Backend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/b`
- Frontend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/f`
- Maintenance target HEAD: `efa0cfd79c75a48de807a40e1e80deefff63e6ee`
- Backend target HEAD: `bc38e943d6c7648ed10347dcfe64796c6348f085`
- Frontend target HEAD: `07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa`
- Later source-branch drift is out of scope by user rule; this release remains bound to the frozen `r260713t` input.

## Release Evidence

- Release tag: `release-20260713-current-head-test-r260713t-r3`
- Build operation: `op-2026-07-13T114933441747800Z-ea18fdef-4abd-44e8-a712-8615a67b95bf` = `SUCCESS`
- Publish-test operation: `op-2026-07-13T121325438123300Z-549989ce-c0b2-4cab-bc66-e7dfc0630394` = `SUCCESS`
- Manifest: `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-current-head-test-r260713t-r3/manifest.json`; `publishScope=code-only`; backend/frontend sourceRepos dirty=false; artifact hashes verified.
- Test server: `.env IMAGE_TAG`、backend/frontend image tags、containers、backend health、frontend HTTP、PDF worker HTTP、release-info、release lock and migration failures all passed.
- Runtime console page: `http://127.0.0.1:48182/` displayed the releaseTag and “版本变更说明”; Playwright console errors=0 and warnings=0.

## Cleanup Candidates

- `doc/tasks/20260713-current-head-test-only-release/runtime-console-r260713t-r3.png`

## Closeout Evidence

- Runtime-control main restore: `http://127.0.0.1:48181/actuator/health=UP`，进程命令行指向主工作区 Jar。
- Release worktree cleanup: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t` exists=false；`D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t-state` exists=false；维护/后端/前端 Git worktree registrations absent。
- Task-owned process cleanup: no non-current process command line references `IntRuoyiWorktrees\r260713t`.
- task-closeout: preview/apply `blocked=<none>`、`warnings=<none>`；删除临时 `migration-policy-gate-r260713t.json` 与 Playwright screenshot，保留 `task.md`、`execution-log.md`、`verification-report.md`。
