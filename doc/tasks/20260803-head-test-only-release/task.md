# 20260803-head-test-only-release

## Task Goal

仅基于当前分支开始发布时冻结的 HEAD 已提交代码，构建维护控制台与测试发布包，并只发布到测试服务器；未提交改动不得进入构建产物，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 构建前 Git / worktree 冻结：确认当前分支、目标提交、脏工作区状态，创建本次专用干净临时发布 worktree 并记录构建目录。
- [x] 发布前经验门禁：读取命中的发布、worktree、PowerShell、服务器访问和登录经验，记录强制门禁并完成高风险动作前 `experience-preflight`。
- [x] 构建维护控制台与测试发布包：基于冻结 worktree 执行构建，检查发布包、manifest、版本号和变更说明均可回溯目标提交。
- [x] 测试服发布：仅执行 `publish-test`，记录 releaseTag / operation，并确认未触发正式服或备份服动作；operation 最终 FAILED。
- [x] 真实运行态验收：失败后已冻结远端状态并恢复 `.env IMAGE_TAG` 到失败前运行 tag；目标 releaseTag 未完成验收。
- [x] 问题记录与阶段复盘：按现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次避免方式记录全部问题和耗时点。
- [x] 经验沉淀与收口：已沉淀失败门禁；因发布失败，本任务保持 blocked，不执行 completed closeout，不删除证据 worktree/state。

## Expected Verification

- `git status --short --branch`、`git branch --show-current`、`git rev-parse HEAD` 记录发布起点。
- 临时发布 worktree 指向目标 HEAD，且 `git status --short --branch` 干净。
- 构建包根 `manifest.json`、release 信息、版本号和变更说明均证明构建来源为目标 HEAD。
- `publish-test` 成功，且同一 releaseTag 不执行正式服或备份服动作。
- 测试服远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health=UP、frontend HTTP 200、页面可访问、运行控制台版本号和变更说明全部通过。
- 所有问题已记录，可前置化问题已沉淀为经验门禁。

## Current Status

blocked

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。本任务必须 fail fast，不用 mock、默认成功或降级验收掩盖发布失败。
- 是否从根因和长期维护角度解决：是。若发布链路失败，先冻结证据并定位 manifest / migration / 脚本契约 / 环境根因，再决定是否需要代码或脚本修复并重新构建新 releaseTag。
- 是否存在临时补丁或绕过：否。未获用户明确授权时，不做临时脚本绕过、不跳过发布或运行态验收。

## 经验门禁

- 测试服发布门禁：仅允许同一 releaseTag 走 `build-release -> publish-test`；目标主机固定 `172.30.30.58`、远端目录 `/opt/intruoyi/runtime`，禁止 `mark-tested`、`promote-prod`、`promote-backup`。
- 冻结 HEAD 门禁：维护仓与主程序仓主工作区 dirty 时必须创建本轮专用 clean release worktree；构建开始后只认冻结 worktree HEAD，不追逐后续提交。
- Manifest 门禁：构建后以发布包根 `manifest.json` 为权威，校验 `releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、变更说明和 artifact SHA256。
- 构建参数门禁：`build-release` 必须显式 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；发布包不得包含非本次范围的 Website/showroom 目录。
- 发布参数门禁：`publish-test` 请求使用最小有效 payload；preview 必须结构化证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，且无正式/备份/mark-tested 动作。
- 真实运行态门禁：operation=SUCCESS 后仍必须核远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP=200、`release-info.json`、release lock=APPLIED、当前 releaseTag migration failed/running=0。
- 运行控制台门禁：页面验收必须用真实页面打开版本/变更说明，确认 releaseTag、发布包、组件范围和变更说明可见；source commit 和 dirty=false 由 manifest / release-info 独立证明。
- PowerShell / SSH 门禁：不用 `&&` 或 Bash heredoc；中文与多行脚本使用 UTF-8；SSH `bash -s` 使用 UTF-8 bytes + LF，不用 `ssh -n`；carrier warning 不覆盖结构化 stdout 断言。
- Worktree 清理门禁：发布验证完成后先标记 `ready_for_closeout`；停止或恢复本任务 48181 运行控制台后，仅清理本任务 release worktree/state dir，验证 Git 注册和物理目录均不存在后才标记 `completed`。
- 凭据日志门禁：`config/runtime-control.local.yaml`、NAS/SSH/MySQL 密钥只允许本地使用，任务记录和提交只写命令意图、退出码和脱敏摘要。

## Release Baseline

- 维护仓：branch=`int_main`，HEAD=`ed7ef820d57fc0185e5c16a8be2e820a13384b15`，主工作区 dirty。
- 主程序仓：branch=`int_main`，HEAD=`1606947b7598eca15e904362759a7236a255dbbf`，主工作区 dirty；后端与前端目录同属 `E:\IntRuoyi` Git root。
- 构建策略：创建 clean release worktree 后基于冻结 HEAD 构建，不使用主工作区未提交改动。
- 本轮 release id：`r260803a`。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803a\m`。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260803a-release-app`。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803a-state\runtime-control`。
- releaseTag：`release-20260803-intmain-head-test-r260803a-r1`。
- build operation：`op-2026-08-02T164907897014700Z-a76bd666-e3b7-449a-b77f-e4541826cd8f`，status=`SUCCESS`。
- publish-test operation：`op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241`，status=`FAILED`，原因是 required SQL `20260513_dcc_base_schema.sql` 报 MySQL `ERROR 1062 Duplicate entry '6813' for key 'system_menu.PRIMARY'`。

## Blocker

- `preflight-plan.json` 对 `20260513_dcc_base_schema` 给出 `APPLY`，原因是目标库记录 checksum `9c6d4004565813ebfc8b1ad0454c6eb7d27302a348f426f1ad94795774c2bd33` 与本轮 manifest checksum `4751b23cf28e932d936f3c6a81d9aee109afbd6fa509189dd50d589ac6abfe28` 不一致；发布脚本执行该 SQL 时在 `system_menu.id=6813` 处遇到主键重复。
- 测试服 release lock 已标记 `FAILED`，目标 releaseTag migration `FAILED=1`、`RUNNING=0`；未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- publish 失败后远端 `.env IMAGE_TAG` 一度被写入本轮失败 releaseTag，但 backend/frontend 容器仍运行上一轮 `release-20260802-feedback-fix-test-r260802h-r1`；已按失败收束将 `.env IMAGE_TAG` 恢复为实际运行 tag，并复核 backend health=UP、frontend HTTP=200、远端 release-info 仍为上一轮成功 release。
- 不复用失败 releaseTag；继续完成发布需要先修复 required SQL/checksum 漂移的根因，提交后创建新的 clean release worktree 与新 releaseTag 重走 `build-release -> publish-test`。

## Cleanup Candidates

无仓库内额外候选。外部 release worktree 与 state dir 使用固定 allowlist 手工清理并在 `execution-log.md` 记录，不交给 task-closeout 脚本按路径删除。

## Cleanup Keep

- `doc/tasks/20260803-head-test-only-release/task.md`
- `doc/tasks/20260803-head-test-only-release/execution-log.md`
- `doc/tasks/20260803-head-test-only-release/verification-report.md`
