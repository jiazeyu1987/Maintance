# Execution Log

## User Intent

用户授权本次仅测试服发布：基于发布开始时冻结的当前分支最新已提交代码构建并发布到 `172.30.30.58`，不得让未提交改动进入产物，不追逐后续提交，不执行正式服、备份服或推广动作。

## BDD

BDD: frozen HEAD test-only release -> Given the maintenance and app workspaces may be dirty, When a dedicated clean worktree at the frozen HEAD builds and publishes one releaseTag to test, Then all artifacts, manifest fields, runtime tags, health, page and console release-info must identify that same frozen commit; missing or mismatched evidence fails fast.

## Preflight Evidence

- GREEN: experience-preflight -> PASS：已读取适用的 `AGENTS.md`、`docs/experience-index.md` 命中路由、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md` 和 `E:\IntRuoyi\docs\powershell-memory.md`。
- Scope locked：仅测试服务器 `172.30.30.58`；禁止正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。
- Previous owned task check：`20260823-test-only-head-release-rerun` 为 `blocked`，其阻塞为冻结 app HEAD 空 Vue SFC；本任务不复用其 worktree、包或 releaseTag。

## Stage 1: Git Freeze

- Maintenance main: branch=`int_main`, HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`, dirty entries=`57`。
- App main at freeze: branch=`int_main`, HEAD=`0002767c0486f11d82bd82666bf8b0f164aee597`, dirty workspace；冻结后主线推进到 `a6574c3631dfa3c5f8381596fcef5c91acd98db0`，未追逐该提交。
- Dedicated worktrees: maintenance=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823d\m`; app=`D:\IntRuoyiWorktree\r260823d\a`。两者 detached、HEAD 与冻结值一致、`git status --porcelain --untracked-files=all` 为空。
- Build directory/releaseTag：未生成。由于构建前契约阻塞，不创建发布包或 releaseTag。

## Stage 2: Build-Preflight Contract

- RED: zero-byte Vue SFC scan -> FAIL, frozen app worktree contains one 0-byte tracked Vue SFC: `IntRuoyiFronted/src/views/dcc/controlled-file/training/components/TrainingRulesReadonlyTab.vue`。
- Evidence: frozen Git blob size=`0`; worktree file length=`0`; static scan=`zero-byte-vue-count=1`。
- P001: 现象=维护主工作区与 app 主工作区均 dirty；阶段=Git freeze；影响=不能直接从主工作区构建；原因判断=持续开发工作区包含并行任务/历史产物，非本轮发布输入；处理动作=从发布开始时冻结 HEAD 创建两个一次性 clean worktree；结果=worktree 均 clean，未提交内容未进入输入；是否可前置检查=是；是否可自动化=是；下次如何避免=发布脚本前置固定校验主工作区 dirty 后自动要求专用 worktree，并记录 commit/path/status。
- P002: 现象=冻结 app HEAD 的 Vue SFC 为 0 字节；阶段=构建前契约；影响=Vite 无法解析 SFC，无法确认构建来源、artifact、manifest、版本号或变更说明，后续发布全部禁止；原因判断=问题存在于已提交 HEAD 的 tracked blob，不是 worktree 脏内容；处理动作=静态扫描 fail fast，未运行 build、未复用旧包、未写测试服务器；结果=阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=构建前扫描所有 tracked `.vue` 文件非空且至少含 `<template>` 或 `<script>`，失败即停止。
- P003: 现象=worktree 创建期间 app 主线出现新提交 `a6574c3...`；阶段=冻结后主线漂移；影响=若追逐会破坏本轮“发布开始时”输入可审计性；原因判断=并行开发正常推进；处理动作=保持已创建 worktree 的 `0002767c...` 基线，不读取新提交作为本轮构建源；结果=冻结输入稳定；是否可前置检查=是；是否可自动化=是；下次如何避免=先记录冻结提交，再将所有构建/验证命令限定到绝对 worktree 路径。

## Continuation Check 2026-08-23 16:32

- 当前 app `int_main@a6574c3631dfa3c5f8381596fcef5c91acd98db0` 已与 `origin/int_main` 同步，但 `TrainingRulesReadonlyTab.vue` 仍为 0 字节；本轮阻塞条件未解除。
- P004: 现象=历史有效文件在提交 `5f0138e4c3bd6cabfef97f45dbd287e4b3072aa2` 中从 248 行被删除为 0 行；阶段=构建前根因诊断；影响=当前分支所有新冻结 worktree 都会重复 Vite SFC 阻塞；原因判断=已提交源代码删除，不是 dirty worktree 或依赖问题；处理动作=只读比对父提交 blob/diff，未恢复文件、未修改分支、未选择旧提交发布；结果=根因确认，继续 blocked；是否可前置检查=是；是否可自动化=是；下次如何避免=合入/发布前对 tracked Vue SFC 做非空与 template/script 结构扫描，提交删除关键组件时必须有对应构建验证。
- 长过程复盘：当前进度=已复核最新 app HEAD、origin 同步状态和删除根因；阻塞点=目标分支仍无有效 SFC；耗时原因=主线在上一冻结后有文档提交但未修复源文件；下一步=等待有效修复提交后重新冻结，期间不构建、不发布、不复用旧包。

## Stage 3-6: Build, Publish, Runtime, Closeout

- 未进入。由于 P002 在构建前阻塞，未生成 package/manifest/releaseTag，未执行 `build-release`、`publish-test`、数据库/服务器写入、镜像切换、页面或运行控制台验收。
- 当前不能设置 `ready_for_closeout` 或删除发布 worktree；worktree 保留作为本轮阻塞证据，待用户提供包含有效 Vue SFC 的新已提交基线后重新启动新任务/新冻结。

## Experience Consolidation

- 已调用 `project-experience-consolidation` 工作流，将可复用的空 Vue SFC 构建前门禁合并到现有 `docs/release-build-preflight-lessons.md`，并在 `docs/experience-index.md` 增加关键词路由；未新建长期经验文档。
- 仅沉淀前置检查和禁止动作，不写入“发布成功”结论；本轮仍为 blocked。

## Issues

每个问题必须记录：现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免。

## Long-Process Review

- 当前进度：完成规则读取、任务记录、Git 冻结和专用 worktree 创建；阻塞点：冻结 HEAD 含空 Vue SFC。
- 耗时原因：app 仓 worktree 检出约 30 秒以上，期间主线并行推进；未继续依赖安装或构建，避免在已知不满足前置条件时浪费时间。
- 下一步动作：停止本轮发布，等待有效的已提交 Vue SFC 基线；不重试本轮输入、不复用旧发布包或旧 releaseTag。
