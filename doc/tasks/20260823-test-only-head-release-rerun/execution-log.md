# Execution Log

## User Intent

用户授权仅测试服发布；目标是使用发布开始时冻结的三仓 HEAD 构建并发布到 `172.30.30.58`，不追逐后续提交，不执行正式服、备份服或推广动作。

## BDD

BDD: frozen HEAD test-only release -> Given dirty development workspaces and a frozen HEAD for each source repository, When a dedicated clean release worktree builds and publishes one releaseTag to test, Then every artifact, manifest, runtime tag, health result, page and console release-info must identify that same releaseTag and commits; any missing or mismatched evidence fails fast.

## Preflight Evidence

- GREEN: experience-preflight -> PASS. Read `docs/test-release-preflight.md`, `docs/release-build-preflight-lessons.md`, `E:\IntRuoyi\docs\release-backup-restore.md`, `E:\IntRuoyi\docs\server-access.md`, `E:\IntRuoyi\docs\login-access.md` and `E:\IntRuoyi\docs\worktree-memory.md`.
- Scope locked: test server `172.30.30.58` only; no production/backup/mark-tested/promote actions.
- Frozen source inputs at task start: maintenance `int_main@66c4ea05dda04459433bc22471ea2b6f4f3dfc32`; app root `int_main@ef217fe2ca8887e5b4242d0823f203179d6b059e`.
- Dirty status: maintenance `56` entries; app root `576` entries. No dirty content will be used directly.
- Command intent recorded: create dedicated clean worktrees, build one releaseTag, independently validate artifacts and manifest, then publish only test and verify real runtime/page state.
- P001: 现象=首次选择的 app release worktree 路径在长时间创建过程中被并发任务占用，当前登记为 `codex/release-smoke-node-image-export-v2`，HEAD 不等于本轮冻结提交；阶段=worktree 创建；影响=该路径不能作为本轮构建输入；原因判断=并发任务与本轮路径选择发生竞争，且首次 PowerShell 存在路径条件表达式错误；处理动作=不覆盖、不清理该 worktree，改用新的唯一绝对路径并重新核验；结果=待新路径创建后确认；是否可前置检查=是；是否可自动化=是；下次如何避免=路径检查必须使用括号化布尔表达式，并在 `git worktree list` 与物理路径双重确认后再创建。

## Build Attempt

- GREEN: maintenance-console-build -> PASS；维护控制台前端 install/typecheck/build、Maven 26 tests、JAR package 均成功。维护 worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823b\m`，HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`。
- GREEN: app-release-worktree -> PASS；app worktree=`D:\IntRuoyiWorktree\r260823c\a`，HEAD=`ef217fe2ca8887e5b4242d0823f203179d6b059e`，依赖按 lockfile 安装完成，worktree status 仍 clean。
- RED: `pnpm --dir D:\IntRuoyiWorktree\r260823c\a\IntRuoyiFronted build:test` -> FAIL，Vite 在 `TrainingRulesReadonlyTab.vue` 报 `At least one <template> or <script> is required`。
- Evidence: 该文件在冻结 HEAD 中 tracked、0 bytes、blob=`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`，当前 worktree 未修改该文件；release package `release-20260823-intmain-head-test-r260823b-r1` 不存在。
- 长过程复盘：当前进度=三仓冻结、专用 worktree、维护控制台构建完成；阻塞点=app 前端冻结 HEAD 本身无法通过构建；耗时原因=维护端依赖安装约 3 分钟、app 依赖恢复约 8 分 43 秒，Vite 在约 46 秒后暴露空组件；下一步=等待提交包含有效组件实现后，重新冻结新 HEAD、创建新 worktree 和新 releaseTag，不复用本轮半成品。

## Issues

尚未开始构建；所有后续问题追加记录，字段必须包含：现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免。

- P002: 现象=冻结 app HEAD 的 `TrainingRulesReadonlyTab.vue` 为 0 字节，`pnpm build:test` 在 Vite 解析阶段失败；阶段=构建前端；影响=无法生成维护发布包、manifest、版本号/变更说明，也不能执行 `build-release` 或 `publish-test`；原因判断=当前最新已提交 HEAD 包含空的 Vue SFC，属于源提交阻塞而非 worktree 脏内容；处理动作=保留 clean worktree 和失败证据，未修改文件、未复用旧包、未发布服务器；结果=阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=构建前扫描 tracked `.vue` 文件并对 0 字节/SFC 缺少 template/script fail fast。

## Continuation Check

- 当前主线已前进到 `2cf830d7bbf2d3f88d062a56693d53490480ccdd`，但该 HEAD 中同一 tracked Vue 文件仍为 0 bytes，且主工作区对此文件无未提交修复。
- 既有失败 release worktree 仍保留为证据，未修改、未删除；未创建新发布包或执行服务器写入。
- P003: 现象=继续检查后最新主线提交仍保留同一 0 字节 Vue SFC；阶段=发布重试前置复核；影响=重新冻结并构建仍会在同一 Vite 解析点失败，不能安全进入 build-release/publish-test；原因判断=阻塞尚未被提交修复解除；处理动作=只读复核最新 HEAD、文件大小、Git 状态和历史，保持 NO-GO；结果=仍阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=提交合入前执行前端 SFC 完整性扫描和 `pnpm build:test`。
