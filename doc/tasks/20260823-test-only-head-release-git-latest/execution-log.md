# Execution Log

## User Intent

用户要求使用最新 Git 版本执行本次仅测试服发布；发布输入必须是发布开始时冻结的当前分支最新已提交代码，未提交改动不得进入产物，仅允许测试服务器 `172.30.30.58`，禁止正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。

## BDD

BDD: latest Git test-only release -> Given the release tool must use the current official Git for Windows version and source workspaces may be dirty, When the latest Git is verified and a clean worktree at one frozen HEAD builds and publishes one releaseTag to test, Then artifact provenance, manifest, runtime tags, health, page and console release-info must identify that HEAD; any missing source or tool evidence fails fast.

## Preflight Evidence

- GREEN: experience-preflight -> PASS：已读取 `docs/experience-index.md` 命中路由、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-restrictions.md`、`E:\IntRuoyi\docs\worktree-memory.md` 和 `E:\IntRuoyi\docs\powershell-memory.md`。
- CI/CD contract read：已读取 `ci-cd-environment-delivery` 技能及 `references/cicd-contract.md`。
- Previous task check：`20260823-test-only-head-release-r3` 已明确标记 `blocked`，阻塞为目标 app HEAD 的 0 字节 Vue SFC；不复用其 worktree、包或 releaseTag。
- Scope locked：仅测试服务器 `172.30.30.58`；禁止正式服、备份服、推广动作。

## Stage 1: Latest Git Tool

- Official release：Git for Windows `v2.55.0.windows.5`，published=`2026-08-20T16:21:31Z`，asset=`Git-2.55.0.5-64-bit.exe`，size=`65343712`，SHA256=`D065A4E23C3D9A6B5073D609B5BE0830227EC3CA053C083BA385061DDFAF94C6`。
- Installed path：`D:\Programs\Git-2.55.0.5`；`D:\Programs\Git-2.55.0.5\cmd\git.exe --version` -> `git version 2.55.0.windows.5`。旧 `D:\Programs\Git` 未覆盖。
- P001: 现象=官方安装包下载耗时较长且首次命令在 30 秒窗口返回时尚未输出最终结果；阶段=Git 工具准备；影响=不能把进程启动误判为安装完成；原因判断=下载/安装为异步长操作；处理动作=等待进程结束，核对安装目录、版本输出和 SHA256；结果=安装成功，版本可用；是否可前置检查=是；是否可自动化=是；下次如何避免=记录 asset size/hash，使用 bounded wait 并以 `git.exe --version` 和路径存在性作为唯一成功条件。
- Latest Git repository probe：使用新 Git 读取 app `int_main@a0025c94278790badeefdc624af4372399e1207a`；已有 `origin/int_main@a6574c3631dfa3c5f8381596fcef5c91acd98db0`，本地 ahead=`1`；主工作区 dirty。未执行 fetch，冻结使用当前本地分支 HEAD。

## Stage 2: Source Freeze and Build

- 当前 app HEAD `a0025c94278790badeefdc624af4372399e1207a` 的 `TrainingRulesReadonlyTab.vue` Git blob=`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`、size=`0`；空 Vue SFC 阻塞仍存在。维护 HEAD 仍需在新 worktree 创建前复核。
- 使用最新 Git 创建 worktree：maintenance=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823e\m` at `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，app=`D:\IntRuoyiWorktree\r260823e\a` at `a0025c94278790badeefdc624af4372399e1207a`；两者 `git status --porcelain --untracked-files=all` 为空。
- RED: latest-Git frozen Vue SFC scan -> FAIL，`git ls-tree -r -l HEAD -- IntRuoyiFronted` found `zero-byte-vue-count=1`，目标文件 Git/worktree size=`0`。
- P002: 现象=升级到官方最新 Git 后，最新本地 app HEAD 仍含 0 字节 tracked Vue SFC；阶段=源码冻结/构建前；影响=无法运行可靠前端构建或确认 package、manifest、版本号/变更说明，后续测试服发布全部禁止；原因判断=已提交源代码缺陷，与 Git 客户端版本无关；处理动作=用最新 Git 新建 clean worktree并静态 fail fast，未修改源码、未复用旧包/tag、未访问服务器；结果=blocked；是否可前置检查=是；是否可自动化=是；下次如何避免=提交合入和发布前固定执行 `git ls-tree -r -l HEAD` 的 `.vue` 非空及 template/script 合同扫描。

## Stage 3-6: Build, Publish, Runtime, Closeout

- 未进入：未安装项目依赖、未运行 `pnpm build:test`、维护控制台构建、Maven package、`build-release`、`publish-test`、服务器写入、镜像/容器切换、health/HTTP/page/release-info 验收或推广动作。
- 本任务 blocked，两个 `r260823e` release worktree 保留作为证据；未执行 cleanup preview/apply。

## Stage 3: Publish-Test and Runtime

待构建门禁通过后记录 build/publish operation、manifest、远端运行态和页面/控制台证据；任何 blocker 立即停止。

## Issues

每个问题记录：现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免。
