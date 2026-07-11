# 20260711 当前 HEAD 仅测试服发布

## 任务目标

冻结维护仓当前分支 `int_main` 在任务开始时的最新已提交提交 `266f0ae7349348dbeeac4fe553ac404da714dbd6`，仅以该提交创建干净临时发布 worktree，构建维护控制台和测试发布包，仅发布到测试服务器并完成真实运行态、页面、版本号和变更说明验收。未提交改动不得进入构建产物；不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## 里程碑

- [x] M1：完成任务文档、经验门禁、Git/环境/流程前置检查。
- [x] M2：创建并记录 HEAD 固定的干净临时发布 worktree。
- [x] M3：维护控制台构建已通过；发布包 `release-20260711-current-head-test-r4` 生成并通过 manifest/sourceRepos/changeSet 校验。
- [x] M4：仅执行 `publish-test`，operation、镜像、容器、健康、HTTP、前端页面和运行控制台版本说明均已验证。
- [x] M5：问题、耗时、处理结果和可执行前置经验已记录。
- [x] M6：cleanup preview/apply、运行控制台主路径恢复、本任务临时 worktree 删除均已完成；任务标记 `completed`。

## 预期验证

- 维护仓发布输入固定为 `int_main@266f0ae7349348dbeeac4fe553ac404da714dbd6`，临时 worktree 创建后保持 clean。
- 构建过程只引用任务开始时冻结 worktree，不追逐后续分支提交。
- 发布包根 `manifest.json` 可证明 sourceRepos 提交、分支、路径及 `dirty=false`，并与版本号和变更说明一致。
- build-release 与 publish-test 使用同一 releaseTag，两个 operation 均为 `SUCCESS`。
- 测试服 `.env IMAGE_TAG`、compose 解析镜像、实际 backend/frontend 镜像均等于 releaseTag。
- backend health=`UP`，frontend HTTP 200，真实页面可登录并显示本次版本号和变更说明。
- 发布日志和运行态证据仅涉及测试服；正式服、备份服及 tested/promote 动作均未执行。
- 所有问题按现象、阶段、影响、原因判断、处理动作、结果、可前置检查、可自动化、避免方式记录。

## 经验门禁

- 构建输入必须来自本任务专用干净 worktree，并检出冻结提交 `266f0ae7349348dbeeac4fe553ac404da714dbd6`；主工作区脏文件不得复制或进入产物。
- build-release 前记录维护仓、后端仓、前端仓目标提交、分支、worktree 路径和 `git status --porcelain`。
- build-release 预览不得传 `targetEnvironment`；执行时按现有契约显式提供 Test/Prod/Backup 主机参数，但这不授权正式服或备份服发布。
- 只允许 `build-release -> publish-test`；禁止执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 使用单一 releaseTag；任一构建、manifest、required SQL 或发布阻塞导致包无效后，必须判废旧 tag 并使用新 tag 重建。
- 发布包根 `manifest.json` 是 sourceRepos 权威入口；任何提交不符、`dirty=true`、路径不符、manifest 缺失、版本或变更说明不一致均立即停止。
- 发布前必须按权威文档核对服务器目标、脚本参数、NAS 配置、required SQL、迁移元数据和 releaseTag。
- 高风险动作前必须记录 `GREEN: experience-preflight -> PASS`；缺失则不得构建、发布、远端写入或清理 worktree。
- 发布完成必须同时验证 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、真实页面版本和变更说明。
- PowerShell 5.1 禁止 `&&`；中文、SSH、多行脚本和关键外部命令必须显式 UTF-8 并检查退出码。
- 临时发布 worktree 未产生提交时，发布和运行控制台恢复完成后直接删除；若产生提交，必须先合回 `int_main` 并验证，未合并或状态不明时阻塞且不得删除。
- 不修改或停止无关并发任务的 worktree、进程、控制台和任务文件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；以冻结提交、权威 manifest、单一 releaseTag 和完整运行态证据构成可审计发布链。
- 是否存在临时补丁或绕过：否；任何前置条件或验证失败均 fail fast，不手工伪造成功、不跳过验证、不改用其他提交或数据源。

## 发布冻结信息

- 任务开始时间：`2026-07-11T00:22:57+08:00`
- 维护仓主工作区：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 当前分支：`int_main`
- 冻结提交：`266f0ae7349348dbeeac4fe553ac404da714dbd6`
- 提交说明：`任务: 补记最终核验误判`
- 后端分支与冻结提交：`int_main@2714df1ccb99d60b27cdf8b5236c0e21b78f824b`
- 前端分支与冻结提交：`int_main@f3edb4202a8c8acd1ffa39c180a203bafbbc2ddf`
- 后端/前端主工作区状态：均 dirty；本任务不读取或复制其中未提交内容。
- 主工作区状态：dirty；存在其他任务已修改和未跟踪文件，本任务必须使用新建干净临时发布 worktree。
- 临时发布 worktree 根：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t`。
- 维护仓 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\m`，detached `266f0ae7349348dbeeac4fe553ac404da714dbd6`，clean。
- 后端 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\b`，detached `2714df1ccb99d60b27cdf8b5236c0e21b78f824b`，clean。
- 前端 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\f`，detached `f3edb4202a8c8acd1ffa39c180a203bafbbc2ddf`，clean。
- 构建目录：维护控制台与发布脚本固定使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\m`，业务源码根固定为 `b` 与 `f` worktree。
- 维护控制台 Jar：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- 维护控制台 Jar SHA256：`5fe32b4ca4a9893a8b84e05b194ed9e06ea166deed3aa5c80fa05d492e65e24a`
- 维护控制台 Jar 大小：`35141807`
- releaseTag：`release-20260711-current-head-test-r4`；build-release operation `op-2026-07-11T020116790952700Z-a56e7120-5a78-45a4-a2a3-a1016359d0f1` SUCCESS；publish-test operation `op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d` SUCCESS。

## 问题记录

### P001 主工作区存在未提交改动

- 现象：维护仓 `int_main` 主工作区存在已修改和未跟踪文件。
- 阶段：构建前 Git 检查。
- 影响：直接构建无法证明发布包只包含冻结 HEAD 已提交内容。
- 原因判断：并发任务和历史运行产物共用主工作区。
- 处理动作：从冻结提交创建本任务专用干净临时发布 worktree，所有构建和发布输入仅指向该 worktree。
- 结果：已创建并验证三个 detached clean worktree；主工作区未提交内容未进入 worktree。
- 是否可前置检查：是，构建前执行 `git status --porcelain=v1 -uall`。
- 是否可自动化：是，发布任务固定创建 HEAD-pinned worktree 并校验 clean。
- 下次如何避免：禁止从主工作区直接构建；任务启动即冻结提交并创建独立 worktree。

### P002 PowerShell 启动 bootstrap 顺序未一次完成

- 现象：最初只读探查先读取了 release skill、目录和 Git 状态，之后才完整读取共同 `powershell-memory.md`。
- 阶段：任务启动前置检查。
- 影响：未执行写文件、构建、发布、远端服务或环境变更，但不满足“所有非引导 PowerShell 前先读共同 PowerShell 记忆”的最严格顺序。
- 原因判断：将技能读取和 Git 只读探查误归类为可并行启动探查。
- 处理动作：在任何 worktree、构建、发布、SSH 或 E2E 前补读权威 PowerShell 门禁，并将后续命令统一为显式 UTF-8、无 `&&`、检查原生命令退出码。
- 结果：已纠正；高风险动作尚未开始。
- 是否可前置检查：是。
- 是否可自动化：是，可将固定 bootstrap 封装为任务启动命令。
- 下次如何避免：启动首条命令只执行 UTF-8 设置并读取 AGENTS、上一任务状态、experience-index 和 powershell-memory。

### P003 detached 分支校验对空输出调用 Trim

- 现象：首次 worktree 校验使用 `git branch --show-current` 后直接调用 `.Trim()`；detached HEAD 正常返回空输出，触发三次 PowerShell 非终止错误。
- 阶段：worktree 创建后校验。
- 影响：worktree 创建实际成功且命令最终退出 0，但首次校验日志含噪声，不能单独作为严格无错误证据。
- 原因判断：校验脚本未按 detached HEAD 的合法空输出处理。
- 处理动作：改用 `git rev-parse --abbrev-ref HEAD` 并断言结果为 `HEAD`，重新验证三仓 HEAD、detached、clean 与子模块状态。
- 结果：复验全部 PASS。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：detached 校验使用明确非空契约，禁止对可能为 null 的原生命令输出直接调用字符串方法。

### P004 rg 直接接收 README* 路径通配符失败

- 现象：使用 `rg ... <worktree>\README*` 时 Windows 报“文件名、目录名或卷标语法不正确”。
- 阶段：维护控制台构建契约探查。
- 影响：该次检索未覆盖 README 文件，其余文件检索和端口检查继续完成。
- 原因判断：将 shell 通配符作为 Windows 路径参数直接传给 `rg`，未使用 `-g` glob。
- 处理动作：后续按明确文件路径读取，并使用 `rg -g 'README*'` 规则。
- 结果：已纠正。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：Windows 下文件模式统一通过 `-g` 传给 `rg`，不把 `*` 拼入路径。

### P005 Java 版本输出到 stderr 被 PowerShell 误判失败

- 现象：`java -version` 正常退出 0，但在 `$ErrorActionPreference='Stop'` 与 `2>&1` 下被包装为 `NativeCommandError`。
- 阶段：工具链预检。
- 影响：首次工具链预检提前停止，未进入构建。
- 原因判断：Java 按惯例把版本输出写入 stderr，PowerShell 5.1 将其升级为错误记录。
- 处理动作：改为显式捕获原生命令 stdout/stderr，并只按 `$LASTEXITCODE` 判定。
- 结果：Java 21.0.10、Maven 3.9.9、Node 24.12.0、Docker 29.2.1、OpenSSH 9.5 均验证通过。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：工具链和构建命令统一使用退出码契约，不按 stderr 是否非空判失败。

### P006 维护前端实际 pnpm 与 packageManager 不一致

- 现象：系统 `pnpm --version` 为 `11.7.0`，维护前端声明 `packageManager=pnpm@10.25.0`。
- 阶段：维护控制台构建前置。
- 影响：直接运行 `scripts/build.ps1` 会使用错误 pnpm 版本，可能生成非预期 workspace/config 或依赖状态。
- 原因判断：全局 pnpm 已升级，构建脚本仍调用 PATH 中的 `pnpm`。
- 处理动作：所有维护前端 install/typecheck/build 使用 `corepack pnpm@10.25.0`；确认 `package.json` 与 `pnpm-lock.yaml` 未变化。
- 结果：已纠正，版本契约通过。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：构建脚本直接使用 packageManager 声明或由 Corepack 固定版本。

### P007 `approve-builds --all` 与 pnpm 10.25.0 实际 CLI 不一致

- 现象：前置经验推荐 `pnpm approve-builds --all`，实际 pnpm 10.25.0 返回 `Unknown option: 'all'`。
- 阶段：维护前端依赖恢复。
- 影响：首次依赖审批步骤退出 1，完整构建未开始。
- 原因判断：经验命令与当前 pnpm 10.25.0 CLI 契约不一致；该版本的 `approve-builds` 仅提供交互式审批。
- 处理动作：先真实执行 frozen install 并冻结 ignored build 结果，再使用任务外部 `onlyBuiltDependenciesFile` 配置和 `pnpm rebuild --pending` 明确允许 `esbuild`、`vue-demi`，不修改冻结 worktree 的 `package.json` 或 lockfile。
- 结果：`ignored-builds` 返回 `None`，依赖脚本构建通过。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：经验文档按 pnpm 版本记录非交互审批契约，执行前先读取 `pnpm help approve-builds`。

### P008 pnpm 审批辅助命令存在三次参数/捕获误判

- 现象：一次辅助函数把命令输出与退出码一起捕获导致假失败；一次 `Start-Process` 参数组合把 frontend 路径误识别为命令；一次向 `rebuild/ignored-builds` 直接传 `--only-built-dependencies` 返回 Unknown option。
- 阶段：维护前端依赖审批。
- 影响：增加重复操作和诊断时间，未修改业务源码。
- 原因判断：混淆 pnpm 全局配置键、命令级可用选项和 PowerShell 函数输出流。
- 处理动作：检查 pnpm 10.25.0 本地源码与 config 解析，改用环境作用域 `npm_config_only_built_dependencies_file` 指向任务 JSON，再执行 `rebuild --pending`。
- 结果：依赖审批完成，冻结源码文件未变化。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：提供已验证的 pnpm 10.25.0 非交互审批脚本并对参数做最小自测。

### P009 release migration gate 文档参数 `--json` 已失效

- 现象：按经验命令执行 `run-release-migration-policy-gate.py ... --json` 返回 unrecognized arguments。
- 阶段：业务后端构建前 migration policy gate。
- 影响：首次 gate 命令未执行策略扫描。
- 原因判断：脚本当前 CLI 使用 `--output`，经验文档仍保留旧 `--json` 参数。
- 处理动作：改用 `--output <task-json>` 重新执行。
- 结果：命令契约已纠正，随后暴露真实 metadata 阻塞。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：前置命令从脚本 `--help` 或契约测试生成，避免文档参数漂移。

### P010 后端已提交 SQL 缺少 release-migration metadata

- 现象：全量 migration policy gate 失败：`sql/mysql/20260710_mes_pro_replan_explanation_snapshot.sql` 首行直接为 `CREATE TABLE`，缺少 `release-migration` metadata。
- 阶段：测试发布包 build-release 前置门禁。
- 影响：无法确认 allowedEnvironments、dependsOn、type、riskLevel；禁止生成 releaseTag、manifest 和发布包，禁止执行 publish-test。
- 原因判断：SQL 由提交 `3fbd7535a04ec86b2c6490991d50984ed1090d6f`（`任务: 增加重排说明快照`）引入时未同步发布元数据。
- 处理动作：冻结失败证据并停止发布；未修改该 SQL，未使用未提交改动或其他提交绕过。
- 结果：BLOCKED。后端冻结 HEAD=`2714df1ccb99d60b27cdf8b5236c0e21b78f824b`，目标 SQL SHA256=`3d01185d757f29a24962016300754280181941d52f2b160dba22967cf1b0399f`。
- 是否可前置检查：是。
- 是否可自动化：是，SQL 提交和 CI 必须强制运行全量 migration policy gate。
- 下次如何避免：新增 `sql/mysql/*.sql` 必须同提交补 metadata 与 gate 测试，缺失时禁止进入 `int_main`。

### P011 维护控制台 Maven 测试生成四个未跟踪 runtime JSON

- 现象：维护控制台 `mvn test package` 后 worktree 出现 `runtime-control-original-governance-parity-test/runtime-ops/*.json` 四个未跟踪测试状态文件。
- 阶段：维护控制台构建。
- 影响：维护 worktree 不再为零变更；文件属于测试运行产物，不在 Jar 和业务源码输入中，但阻塞状态下必须保留并在后续收尾归属确认后清理。
- 原因判断：治理一致性测试将临时运行状态写入 worktree 下的 runtime 目录。
- 处理动作：记录确切路径，不提交、不复制到发布包；当前任务阻塞，不删除 worktree。
- 结果：已识别为本任务生成产物；backend/frontend worktree 仍 clean。
- 是否可前置检查：是。
- 是否可自动化：是。
- 下次如何避免：测试 state-dir 指向任务临时目录，或测试结束自动清理且验证工作区状态。

## 长时间过程复盘

- `2026-07-11T00:22:57+08:00`：完成目标冻结、主工作区 Git 检查和经验索引读取。
- `2026-07-11T00:22:57+08:00` 后续前置阶段：完成发布、构建、服务器、worktree、PowerShell、仅测试服验收规则与前次同类任务核对；维护/后端/前端冻结提交均已记录。当前无发布阻塞，下一步创建三个 clean detached worktree。
- worktree 阶段：三个短路径 detached worktree 已创建并通过 HEAD/clean 复验；首次 detached 分支校验产生非终止错误后已改用可靠契约复验。下一步确定维护控制台构建和 runtime 配置契约。
- 维护控制台构建阶段：`corepack pnpm@10.25.0` install/typecheck/build 与 Maven test/package 均通过，Jar SHA256=`5fe32b4ca4a9893a8b84e05b194ed9e06ea166deed3aa5c80fa05d492e65e24a`。
- 发布包前置阶段：全量 migration policy gate 被 `20260710_mes_pro_replan_explanation_snapshot.sql` 缺 metadata 阻塞。未生成 releaseTag，未启动 worktree 运行控制台，未停止主路径运行控制台，未连接或写入任何服务器。

## Resolved Blocker

- Blocker：冻结后端提交中的 `sql/mysql/20260710_mes_pro_replan_explanation_snapshot.sql` 缺少强制 `release-migration` metadata。
- Diagnostic proof：在独立诊断 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260711t\bd` 按 RED/GREEN 验证候选 metadata：`allowedEnvironments=test,backup,prod; dependsOn=; type=schema; riskLevel=medium`；10 个定向测试和包含 278 个迁移的全量 policy gate 均通过。
- Authorization：用户于 2026-07-11 明确授权把已验证的两文件修复纳入业务后端仓，并以新提交重新冻结后继续仅测试服发布。
- Required action：提交已验证修复，融合后验证，以新后端提交重新冻结发布输入；不得把诊断 worktree 的未提交改动直接作为发布输入。
- Scope impact：正式修复只允许包含迁移 metadata 首行和对应发布契约测试，不得带入后端主工作区的其他未提交改动。
- Safety state：主路径维护控制台 PID `53856` 仍引用 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\...jar` 且 health=`UP`；运行中 operation=0；测试服、正式服、备份服均未操作。

## Current Status

completed

## Latest Progress

- R2 build-release operation `op-2026-07-11T012551984912300Z-8f939bd8-65fb-48f8-a613-93d94c68594d` is not publishable: runtime console port 48181 is down, operation state remained `RUNNING`, no build subprocess remains, and package directory lacks manifest/artifacts.
- Frozen release inputs remain clean: maintenance `266f0ae7349348dbeeac4fe553ac404da714dbd6`、backend `29cf684450849adc49433a6fb97fe44ec872d580`、frontend `f3edb4202a8c8acd1ffa39c180a203bafbbc2ddf`。
- Next action: restart the task-owned runtime console from the frozen maintenance Jar/config and rerun build-release with a new releaseTag `release-20260711-current-head-test-r3`; do not reuse R1/R2 partial packages.

## Cleanup Candidates

- 本任务构建、发布和页面验证生成的临时日志、截图及一次性辅助脚本。
- `doc/tasks/20260711-current-head-test-only-release/maintenance-*.out.log`
- `doc/tasks/20260711-current-head-test-only-release/maintenance-*.err.log`
- `doc/tasks/20260711-current-head-test-only-release/release-migration-policy-gate.*`
- `doc/tasks/20260711-current-head-test-only-release/pnpm-only-built-dependencies.json`
- `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/m/runtime/runtime-control-original-governance-parity-test/`
- `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/bd/`（已验证候选修复，阻塞期间保留）

## Final Release Evidence

- Maintenance commit: `266f0ae7349348dbeeac4fe553ac404da714dbd6` from `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/m`.
- Backend commit: `29cf684450849adc49433a6fb97fe44ec872d580` from `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/b` after authorized migration metadata repair and ff-only merge to backend `int_main`.
- Frontend commit: `f3edb4202a8c8acd1ffa39c180a203bafbbc2ddf` from `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/f`.
- ReleaseTag: `release-20260711-current-head-test-r4`.
- build-release: `op-2026-07-11T020116790952700Z-a56e7120-5a78-45a4-a2a3-a1016359d0f1` -> SUCCESS; package root `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260711-current-head-test-r4`; NAS path `Backup/ReleasePackage/release-20260711-current-head-test-r4`.
- Manifest verification: `manifestVersion=1.0`, `publishScope=code-only`, backend/frontend commits match, both `dirty=false`, changeSet summary/items present, artifact checks passed.
- publish-test: `op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d` -> SUCCESS; no mark-tested/promote-prod/promote-backup operation executed.
- Test server `172.30.30.58`: `.env IMAGE_TAG=release-20260711-current-head-test-r4`, backend image `intruoyi-backend:release-20260711-current-head-test-r4`, frontend image `intruoyi-frontend:release-20260711-current-head-test-r4`, both containers up, backend health=`UP`, frontend HTTP=`200`.
- Test frontend: `http://172.30.30.58:8081/` HTTP 200; `/release-info.json` contains releaseTag, changeSet, backend commit and frontend commit.
- Maintenance console: `http://127.0.0.1:48181/` release-status current test release is `release-20260711-current-head-test-r4`; Playwright verified version dock and `版本变更说明` dialog with releaseTag and change summary.

## Cleanup Candidates

- `doc/tasks/20260711-current-head-test-only-release/build-release-operation-latest.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-operation-tail.log`
- `doc/tasks/20260711-current-head-test-only-release/build-release-preview-approved.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-submit-approved.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r2-operation-latest.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r2-operation-tail.log`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r2-preview.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r2-real-log-tail.log`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r2-submit.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-manifest-focused-inspection.log`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-manifest-validation.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-operation-latest.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-operation-tail.log`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-preview.json`
- `doc/tasks/20260711-current-head-test-only-release/build-release-r4-submit.json`
- `doc/tasks/20260711-current-head-test-only-release/diagnostic-migration-policy-gate.json`
- `doc/tasks/20260711-current-head-test-only-release/maintenance-*.log`
- `doc/tasks/20260711-current-head-test-only-release/pnpm-only-built-dependencies.json`
- `doc/tasks/20260711-current-head-test-only-release/post-merge-migration-policy-gate.json`
- `doc/tasks/20260711-current-head-test-only-release/publish-test-r4-*.json`
- `doc/tasks/20260711-current-head-test-only-release/release-migration-policy-gate*.json`
- `doc/tasks/20260711-current-head-test-only-release/release-migration-policy-gate*.log`
- `doc/tasks/20260711-current-head-test-only-release/remote-*.json`
- `doc/tasks/20260711-current-head-test-only-release/remote-runtime-state-r4.txt`
- `doc/tasks/20260711-current-head-test-only-release/runtime-control-release*.log`
- `doc/tasks/20260711-current-head-test-only-release/playwright-release-info/`
- `doc/tasks/20260711-current-head-test-only-release/playwright-runtime-console/`

## Cleanup Keep

- `doc/tasks/20260711-current-head-test-only-release/task.md`
- `doc/tasks/20260711-current-head-test-only-release/execution-log.md`
- `doc/tasks/20260711-current-head-test-only-release/verification-report.md`

## Completion Evidence

- Completed at: `2026-07-11 11:04:09 +0800`.
- ReleaseTag: `release-20260711-current-head-test-r4`.
- build-release operation: `op-2026-07-11T020116790952700Z-a56e7120-5a78-45a4-a2a3-a1016359d0f1` -> SUCCESS.
- publish-test operation: `op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d` -> SUCCESS.
- Runtime console restored: `D:/ProjectPackage/Int/IntRuoyiMaintance/backend/target/runtime-control-maintenance-2026.06-SNAPSHOT.jar`, health=`UP`, config points to stable main backend/frontend paths.
- task-closeout apply: PASS; only `task.md`, `execution-log.md`, `verification-report.md` remain in the task directory.
- Task worktree root removed: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t` no longer exists and has no Git worktree registrations.
- Diagnostic backend branch `codex/20260711-release-migration-metadata` was merged into backend `int_main` and deleted.
- Scope boundary preserved: no `mark-release-tested`, `promote-prod`, `promote-backup`, formal-server publish, or backup-server publish.
