# 20260802 HEAD 仅测试服发布

## Task Goal

基于当前分支发布开始时记录的最新已提交 HEAD 构建维护控制台和测试发布包，并仅发布到测试服务器。未提交改动不得进入构建产物；不得执行 mark-tested、promote-prod 或 promote-backup。

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
- 发布包根 manifest、release 信息、版本号和变更说明均能回溯到目标 HEAD。
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
- 冻结 HEAD 门禁：维护仓与主程序仓主工作区 dirty 时必须创建本轮专用 clean release worktree；构建开始后以冻结 worktree 提交为来源基线，不追逐后续提交。
- Manifest 门禁：构建后以发布包根目录 `manifest.json` 为权威，校验 `releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、变更说明和 artifact SHA256。
- 发布参数门禁：`build-release` 必须显式 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；`publish-test` preview 必须结构化证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`。
- 运行态门禁：发布后必须同时检查 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、`release-info.json`、release lock/migration 状态和运行控制台版本变更说明。
- PowerShell/SSH 门禁：中文、SSH 多行脚本、release-info、MySQL 查询和页面验收均使用 UTF-8 明确路径；SSH 多行脚本使用 UTF-8 bytes + LF，不用 `ssh -n`，不提交含凭据原始日志。
- Worktree 清理门禁：发布验证完成后先标记 `ready_for_closeout`，恢复 48181 到主维护路径；仅清理本任务 release worktree/state dir，并验证 Git 注册和物理目录均不存在后才标记 `completed`。
- 凭据日志门禁：`config/runtime-control.local.yaml` 与 NAS/SSH/MySQL 密钥只允许本地使用，任务记录和提交只写脱敏摘要。

## Release Boundary

- 发布范围：仅测试服务器。
- 禁止动作：mark-tested、promote-prod、promote-backup、正式服操作、备份服操作。
- 代码来源：发布开始时记录的当前分支 HEAD；后续主分支继续更新也不追逐新提交。
- 构建策略：如主工作区存在未提交改动，创建干净临时 release worktree 并只基于目标 HEAD 构建。

## Frozen Baseline

- 维护仓主工作区：branch=`int_main`，HEAD=`dbc80bc678ae299f419b61c6264601477ea95410`，工作区存在无关脏改和未跟踪文件；不得直接构建。
- 主程序仓 `E:\IntRuoyi`：branch=`int_main`，HEAD=`baf59590f11907efae992cd65d48c067c2f3e572`，工作区存在无关脏改和未跟踪文件；不得直接构建。
- 本轮计划 release id：`r260802a`。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802a\m`。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260802a-release-app`。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802a-state\runtime-control`。
- 最终 releaseTag：`release-20260802-intmain-head-test-r260802a-r1`。
- build operation：`op-2026-08-01T164440373170300Z-e1e28b57-392e-4329-9a0f-7c6e1541cbe9`，状态 `SUCCESS`。
- publish-test operation：`op-2026-08-01T170326581868700Z-f11be1e5-4e3b-4335-9730-2c989e8800f5`，状态 `SUCCESS`。

## Completion Summary

- 维护控制台构建通过：前端依赖恢复、typecheck、build 通过；Maven tests `26` passed；Jar 位于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802a\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- 发布包构建通过：`manifest.json` 校验 `MANIFEST_VALIDATION_PASSED`；artifact hash bad count `0`；sourceRepos 均为主程序冻结 HEAD `baf59590f11907efae992cd65d48c067c2f3e572` 且 `dirty=false`。
- 版本与变更说明通过：manifest changeSet、前端镜像内 `/usr/share/nginx/html/release-info.json`、运行控制台 release-status 均显示同一 releaseTag、`发布包：release-20260802-intmain-head-test-r260802a-r1`、`组件范围：intruoyi`。
- 测试服发布通过：仅执行 `build-release` 和 `publish-test`，未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 测试服真实运行态通过：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP=`200`、页面标题、release lock=`APPLIED`、本 releaseTag migration failed/running=`0`。
- 页面验收通过：Playwright 使用 Chrome 打开 `http://172.30.30.58:8081/` 并截图 `frontend-page-r260802a-r1.png`，页面显示登录界面。
- 收口清理通过：task-closeout preview/apply 无删除、无阻塞；维护 worktree、主程序 worktree、state dir 物理路径和 Git worktree 注册均已清理；`127.0.0.1:48181` 已恢复到任务开始无监听状态。

## Cleanup Candidates

无仓库内额外候选。外部 release worktree 与 state dir 使用固定 allowlist 手工清理并在 `execution-log.md` 记录，不交给 task-closeout 脚本按路径删除。

## Cleanup Keep

- `doc/tasks/20260802-head-test-only-release/manifest-validation-r260802a-r1.json`
- `doc/tasks/20260802-head-test-only-release/manifest-summary-r260802a-r1.json`
- `doc/tasks/20260802-head-test-only-release/remote-runtime-verification-r260802a-r1.json`
- `doc/tasks/20260802-head-test-only-release/runtime-control-release-status-r260802a-r1.json`
- `doc/tasks/20260802-head-test-only-release/frontend-page-r260802a-r1.png`
