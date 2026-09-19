# 20260823 使用最新 Git 的仅测试服 HEAD 发布

## Task Goal

使用 Git for Windows 最新版本作为本轮发布工具，在发布开始时冻结维护仓与 IntRuoyi 主程序仓的最新已提交 HEAD，建立专用 clean release worktree，构建维护控制台和测试发布包，仅发布测试服务器 `172.30.30.58`。未提交改动不得进入构建产物；禁止正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。

## Milestones

1. 记录上一任务 blocker、读取经验门禁和发布规则，确认 Git 最新版本与安装路径。
2. 安装/切换 Git for Windows 最新版本并验证版本、路径和仓库可用性。
3. 冻结当前分支 HEAD，创建并验证本轮专用 clean release worktree。
4. 构建维护控制台和测试发布包，校验 manifest、artifact、版本号和变更说明。
5. 仅执行 `publish-test`，验证 operation、远端 tag、镜像、容器、health、HTTP、页面和运行控制台。
6. 记录问题与耗时，沉淀经验，`ready_for_closeout` 后执行 cleanup preview/apply 并完成最终证据。

## Expected Verification

- Git 客户端版本、官方最新版本、实际可执行文件路径和版本输出可审计。
- 冻结 HEAD、分支、dirty 状态、worktree 路径和构建目录可审计。
- `manifest.json`、legacy manifest、artifact hash、版本号和变更说明绑定冻结提交。
- 同一 releaseTag 的 `build-release -> publish-test` 成功，测试服真实运行态全部通过。
- 所有问题记录现象、阶段、影响、原因判断、处理动作、结果、前置检查、自动化和避免措施。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；Git 安装、构建来源、manifest、版本/变更说明或运行态证据缺失立即停止。
- 是否从根因和长期维护角度解决：是；使用官方 Git for Windows、现有发布脚本和正式测试服门禁。
- 是否存在临时补丁或绕过：否；不修改业务源码、不复用旧包/旧 releaseTag、不选择旧提交规避当前 HEAD 阻塞。

## 经验门禁

- Trigger：使用最新 Git 执行仅测试服 HEAD 发布、clean worktree 构建和 `publish-test`。
- Preflight check：先验证官方 Git release/asset SHA256、独立安装路径和版本输出，再冻结维护/app HEAD；dirty 主工作区必须使用本轮 clean worktree；构建前扫描 tracked Vue SFC 完整性。
- Blocker：Git 版本/路径/校验不可证明、HEAD/worktree 不一致、空 Vue SFC、构建来源/manifest/版本/变更说明/运行态证据缺失时停止。
- Verification：`execution-log.md` 记录 `GREEN: experience-preflight -> PASS`、Git 工具证据、worktree、build/publish operation 和真实运行态证据。
- Forbidden action：禁止覆盖旧 Git、从 dirty 主工作区构建、追逐冻结后的提交、复用旧包/tag、跳过前端源码扫描或访问正式/备份服。
- Evidence：官方 GitHub release asset、安装器 SHA256、`D:\Programs\Git-2.55.0.5\cmd\git.exe --version`、`r260823e` worktree 和本任务 verification report。

## Current Status

blocked

## Frozen Input Evidence

- Latest Git: `D:\Programs\Git-2.55.0.5\cmd\git.exe`, version `2.55.0.windows.5`。
- Maintenance: `int_main@66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，main worktree dirty；release worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823e\m`，detached clean。
- App: local `int_main@a0025c94278790badeefdc624af4372399e1207a`，main worktree dirty and ahead 1 of existing `origin/int_main@a6574c363...`；release worktree=`D:\IntRuoyiWorktree\r260823e\a`，detached clean。

## Blocker

最新 app HEAD `a0025c94278790badeefdc624af4372399e1207a` 的 tracked 文件 `IntRuoyiFronted/src/views/dcc/controlled-file/training/components/TrainingRulesReadonlyTab.vue` 仍为 0 字节（Git blob=`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`，worktree length=`0`，`zero-byte-vue-count=1`）。Git 客户端升级不能修复已提交源代码；Vite 构建前置契约失败，不能生成包、manifest、版本号或变更说明，也不能发布测试服务器。

## Milestone Status

- Milestone 1: completed，规则、上一任务 blocker、CI/CD contract 和发布范围已记录。
- Milestone 2: completed，官方 Git for Windows `2.55.0.windows.5` 已校验并安装到独立目录，旧 Git 未覆盖。
- Milestone 3: completed，使用最新 Git 创建并验证 `r260823e` 两个 clean release worktree。
- Milestone 4-6: blocked/not started，空 Vue SFC 阻止构建、发布、运行态验收和 closeout。

## Experience Gate Summary

- Trigger：使用最新 Git 执行仅测试服 HEAD 发布。
- Preflight check：官方 Git release/hash、独立安装路径、`git --version`、仓库 HEAD/remote-tracking/dirty 状态、专用 clean worktree、Vue SFC 完整性、manifest 和测试服运行态。
- Blocker：Git 安装或版本不可证明、HEAD/worktree dirty 或不一致、空 Vue SFC、构建来源/manifest/版本/变更说明/运行态证据缺失时停止。
- Verification：`execution-log.md` 记录工具版本、SHA256、安装路径、Git 输出、worktree、build/publish operation 和真实运行态。
- Forbidden action：禁止覆盖旧 Git、直接从 dirty 主工作区构建、追逐冻结后的提交、复用旧包/tag、跳过 SFC/manifest/页面验证或访问正式/备份服。
- Evidence：官方 release API、安装器 SHA256、最新 Git 版本输出和本任务证据目录。
