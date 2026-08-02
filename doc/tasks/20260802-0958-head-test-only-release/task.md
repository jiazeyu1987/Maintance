# 20260802 09:58 后 HEAD 仅测试服重新发布

## Task Goal

不考虑 2026-08-02 09:58 之前的发布实现；从本次发布开始时当前分支最新已提交 HEAD 冻结构建维护控制台和测试发布包，并仅发布到测试服务器。未提交改动不得进入构建产物，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 启动门禁：确认上一任务状态、经验门禁、发布文档、服务器访问文档和 PowerShell 编排规则。
- [x] Git / worktree 门禁：记录当前分支、目标提交号、工作区状态、构建目录、临时 worktree 路径，证明构建只来自目标 HEAD。
- [x] 构建门禁：在干净临时 worktree 中构建维护控制台和测试发布包，检查发布包、manifest、版本号和变更说明。
- [x] 测试服发布：仅执行 publish-test，并记录 operation、releaseTag、脚本参数和发布结果。
- [x] 运行态验收：验证测试服镜像 tag、容器状态、后端 health、前端 HTTP 200、前端页面、运行控制台版本号和变更说明。
- [x] 问题记录与复盘：记录 Git、worktree、构建、manifest、发布脚本、镜像、容器、健康检查、页面、控制台、文档流程和耗时问题。
- [x] 经验沉淀：将可前置检查的问题沉淀到长期经验文档并更新索引或 checklist。
- [x] 收口清理：任务状态置为 ready_for_closeout 后执行 cleanup preview/apply，清理本任务临时发布 worktree，并最终标记 completed。

## Expected Verification

- `git status --short --branch`、`git rev-parse HEAD`、`git branch --show-current` 记录目标 HEAD 和工作区状态。
- 临时 release worktree 指向目标 HEAD，且构建目录不包含主工作区未提交改动。
- 发布包根 `manifest.json`、release 信息、版本号和变更说明均能回溯到目标 HEAD。
- publish-test 成功，且未执行正式服或备份服动作。
- 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP 200、前端页面、运行控制台版本号和变更说明全部通过。
- `execution-log.md` 记录 BDD、门禁、命令证据、问题记录、阶段性复盘和最终验证。
- 长期经验文档完成前置经验沉淀并通过索引关键词可定位。

## Current Status

completed

## Design Constraint Check

- 是否引入 fallback/降级/吞异常：否。本任务只允许按现有发布文档构建并发布到测试服；任一关键来源、manifest、版本、变更说明或运行态无法确认即失败。
- 是否从根因和长期维护角度解决：是。发布过程问题必须记录原因判断，并将可前置检查项沉淀为长期门禁。
- 是否存在临时补丁或绕过：否。不得为完成发布临时绕过构建、manifest、脚本、健康检查或页面验证。

## Experience Gate

- 测试服发布门禁：只允许 `build-release -> publish-test`，目标主机固定 `172.30.30.58`，禁止 `mark-tested`、`promote-prod`、`promote-backup`；任一 operation 非 `SUCCESS` 或运行态缺项必须 fail fast。
- 09:58 后重新发布门禁：本次完成证据不得引用 2026-08-02 09:58 之前的 releaseTag、operation、运行态截图或 closeout 结论；必须重新冻结当前 HEAD、重新构建、重新 publish-test、重新验收。
- 冻结 HEAD 门禁：维护仓与主程序仓主工作区 dirty 时必须创建本轮专用 clean release worktree；构建开始后以冻结 worktree 提交为来源基线，不追逐后续提交。
- Manifest 门禁：构建后以发布包根目录 `manifest.json` 为权威，校验 `releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、变更说明和 artifact SHA256。
- 发布参数门禁：`build-release` 必须显式 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；`publish-test` payload 必须使用最小有效字段，preview 证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`。
- 运行态门禁：发布后必须同时检查 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、`release-info.json`、release lock/migration 状态和运行控制台版本变更说明。
- PowerShell/SSH 门禁：中文、SSH 多行脚本、release-info、MySQL 查询和页面验收均使用 UTF-8 明确路径；SSH 多行脚本使用 UTF-8 bytes + LF，不用 `ssh -n`，不提交含凭据原始日志。
- Worktree 清理门禁：发布验证完成后先标记 `ready_for_closeout`，恢复 48181 到主维护路径；仅清理本任务 release worktree/state dir，并验证 Git 注册和物理目录均不存在后才标记 `completed`。
- 凭据日志门禁：`config/runtime-control.local.yaml` 与 NAS/SSH/MySQL 密钥只允许本地使用，任务记录和提交只写脱敏摘要。

## Release Boundary

- 发布时间边界：本次重新发布不引用 2026-08-02 09:58 之前的发布实现作为完成证据。
- 发布范围：仅测试服务器。
- 禁止动作：mark-tested、promote-prod、promote-backup、正式服操作、备份服操作。
- 代码来源：发布开始时记录的当前分支 HEAD；后续主分支继续更新也不追逐新提交。
- 构建策略：如主工作区存在未提交改动，创建干净临时 release worktree 并只基于目标 HEAD 构建。

## Frozen HEAD And Worktree Evidence

- 维护仓发布起点：`int_main` / `b25214b3de563aa83e3bac9eacf401da49c5f476`；主工作区存在既有脏改动，未直接用于构建。
- 主程序发布起点：`int_main` / `b99246f58ff7d556caee24307ec89b662d0427e3`；主工作区存在既有脏改动，未直接用于构建。
- 维护仓 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b\m`，detached HEAD 指向 `b25214b3de563aa83e3bac9eacf401da49c5f476`，构建后清理测试生成 `runtime/` 并复核 clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260802b-release-app`，后端与前端 detached HEAD 均指向 `b99246f58ff7d556caee24307ec89b662d0427e3`，复核 clean。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b-state\runtime-control`；本次临时配置显式指向 clean app worktree 的后端/前端路径，避免读取主工作区未提交内容。

## Build And Package Evidence

- ReleaseTag：`release-20260802-intmain-head-test-r260802b-r1`。
- 维护控制台构建：`scripts\build.ps1` 成功，Maven tests `26` run / `0` failures / `0` errors，Jar 为 `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- migration policy gate：`status=passed`，`migrationCount=406`，证据 `migration-policy-gate-r260802b.json`。
- build-release operation：`op-2026-08-02T021129767983200Z-e204dce2-6be8-4a13-9428-063c4070ae40`，状态 `SUCCESS`。
- 发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260802-intmain-head-test-r260802b-r1`。
- Manifest：`releaseTag`、`component=intruoyi`、`publishScope=code-only`、sourceRepos commit `b99246f58ff7d556caee24307ec89b662d0427e3`、`dirty=false` 均通过；`artifactCount=420`、`artifactHashChecked=420`、`missing=0`、`sizeMismatch=0`、`hashMismatch=0`。
- 版本号和变更说明：manifest、前端镜像 `release-info.json`、远端 `/release-info.json`、运行控制台 release-status 和页面均显示 `release-20260802-intmain-head-test-r260802b-r1`、`发布包：release-20260802-intmain-head-test-r260802b-r1`、`组件范围：intruoyi`。

## Test Publish Evidence

- publish-test preview：`Mode=deploy-release`、`Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，未包含 `mark-tested`、`promote-prod` 或 `promote-backup`。
- publish-test payload：仅使用 `action`、`reason`、`releaseTag` 最小字段。
- publish-test operation：`op-2026-08-02T022945019393Z-852720a9-61ba-4c79-8cc5-245ced64c078`，状态 `SUCCESS`。
- 发布前远端只读检查：测试服原先运行 `release-20260802-intmain-head-test-r260802a-r1`；`running_locks=0`，目标 r260802b `FAILED/RUNNING=0`，历史旧失败 migration `3` 条已记录但不阻塞当前目标。

## Runtime Acceptance Evidence

- 测试服 `.env IMAGE_TAG=release-20260802-intmain-head-test-r260802b-r1`。
- backend 镜像：`intruoyi-backend:release-20260802-intmain-head-test-r260802b-r1|running`。
- frontend 镜像：`intruoyi-frontend:release-20260802-intmain-head-test-r260802b-r1|running`。
- backend health：`{"status":"UP"}`；frontend HTTP：`200`；前端页面标题：`瑛泰管理系统`。
- release lock：`test|release-20260802-intmain-head-test-r260802b-r1|APPLIED`；目标 release migration `FAILED/RUNNING=0`，状态 `SKIPPED_ALREADY_APPLIED=374`。
- runtime-control release-status：`testCurrentReleaseTag=release-20260802-intmain-head-test-r260802b-r1`，summary / changes / sourceRepos clean 均可见，`forbiddenActionsPresent=[]`。
- 运行控制台页面：Playwright 打开 `http://127.0.0.1:48181/`，标题 `运行控制台`，releaseTag、发布包、组件范围和版本变更说明均可见，console errors 和 failed requests 均为空。

## Cleanup Keep

- `doc/tasks/20260802-0958-head-test-only-release/build-release-operation-final-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/build-release-operation-id-r260802b-r1.txt`
- `doc/tasks/20260802-0958-head-test-only-release/build-release-preview-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/build-release-submit-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/frontend-image-release-info-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/frontend-page-r260802b-r1.png`
- `doc/tasks/20260802-0958-head-test-only-release/manifest-summary-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/manifest-validation-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/migration-policy-gate-r260802b.json`
- `doc/tasks/20260802-0958-head-test-only-release/publish-test-operation-final-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/publish-test-operation-id-r260802b-r1.txt`
- `doc/tasks/20260802-0958-head-test-only-release/publish-test-preview-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/publish-test-submit-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/remote-prepublish-r260802b-r1.err.txt`
- `doc/tasks/20260802-0958-head-test-only-release/remote-prepublish-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/remote-prepublish-r260802b-r1.out.txt`
- `doc/tasks/20260802-0958-head-test-only-release/remote-runtime-verification-r260802b-r1.err.txt`
- `doc/tasks/20260802-0958-head-test-only-release/remote-runtime-verification-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/remote-runtime-verification-r260802b-r1.out.txt`
- `doc/tasks/20260802-0958-head-test-only-release/remote-schema-describe-r260802b-r1.txt`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-console-page-probe-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-console-page-r260802b-r1.png`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-control-release-status-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-control-release-status-r260802b-r1.raw.json`
- `doc/tasks/20260802-0958-head-test-only-release/remote-final-recheck-r260802b-r1.json`
- `doc/tasks/20260802-0958-head-test-only-release/worktree-cleanup-r260802b-r1.json`

## Cleanup Candidates

- `doc/tasks/20260802-0958-head-test-only-release/runtime-control-r260802b.pid`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-control-r260802b.out.log`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-control-r260802b.err.log`
- `doc/tasks/20260802-0958-head-test-only-release/runtime-console-page-probe-r260802b-r1.mjs`

## Final Closeout Evidence

- task-closeout-cleanup preview/apply：均无 blocked/warnings；apply 删除本任务临时 `runtime-control` pid/log 和 Playwright 探针脚本。
- 运行控制台恢复：本任务 r260802b parent PID `40980` 和 Java PID `43716` 已停止，`127.0.0.1:48181` 恢复为 `NO_LISTENER`。
- worktree 清理：维护仓和主程序 r260802b worktree Git 注册均不存在；`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b`、`D:\IntRuoyiWorktree\r260802b-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b-state` 物理路径均不存在。
- 最终远端复核：`remote-final-recheck-r260802b-r1.json` 显示 `.env`、backend/frontend image、health、HTTP、release-info、release lock 和 migration 检查全部通过。
