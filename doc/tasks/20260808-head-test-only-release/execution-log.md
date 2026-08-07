# Execution Log

## BDD Scenarios

- `BDD: fixed HEAD test-only release -> Given 当前分支存在最新已提交 HEAD 且允许仅测试服发布, When 从该 HEAD 创建干净临时 worktree 并构建发布包后执行 publish-test, Then 构建产物只包含该 HEAD 已提交代码且测试服真实运行态显示对应版本和变更说明`
- `BDD: fail-fast release provenance -> Given 构建来源、manifest、版本号或变更说明任一无法确认, When 准备进入测试服发布, Then 必须停止发布并记录问题，不得继续部署或降级验证`

## Command And Evidence Log

- `BOOTSTRAP: utf8-read-rules -> PASS`，确认存在 `AGENTS.md`、`docs/experience-index.md`、`E:\IntRuoyi\docs\powershell-memory.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`。
- `PREVIOUS_TASK: doc/tasks/20260806-head-test-only-release/task.md -> completed`，上一任务文档最终状态为 completed，本任务可继续。
- `GREEN: experience-preflight -> PASS`，命中 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`；本轮只允许 build-release -> publish-test，禁止 mark-tested/promote-prod/promote-backup。
- `GIT: maintenance-main -> branch=int_main, HEAD=c1b10cc3a20fd5f4f5d228219ae4c046ad320256, dirty tracked count=21`；主工作区 dirty，必须用 clean release worktree 构建。
- `GIT: app-main -> branch=int_main, HEAD=a6bc1f0cff77fe18e45212ce539c4f76fec65b64, dirty tracked count=160`；主程序 Git 顶层为 `E:\IntRuoyi`，后端/前端子目录共用该 Git root，必须用 clean release worktree 构建。
- `BOUNDARY: release-freeze -> maintenance HEAD=c1b10cc3a20fd5f4f5d228219ae4c046ad320256, app HEAD=a6bc1f0cff77fe18e45212ce539c4f76fec65b64, planned releaseTag=release-20260808-intmain-head-test-r260808a-r1, maintenance worktree=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260808a\m, app worktree=D:\IntRuoyiWorktree\r260808a-release-app`。
- `GREEN: maintenance release worktree -> PASS`，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260808a\m` 指向 `c1b10cc3a20fd5f4f5d228219ae4c046ad320256` 且 clean。
- `GREEN: app release worktree -> PASS`，`D:\IntRuoyiWorktree\r260808a-release-app` 指向 `a6bc1f0cff77fe18e45212ce539c4f76fec65b64` 且 clean。
- `GREEN: migration-policy-gate-r260808a -> PASS`，`migration-policy-gate-r260808a.json`，`status=passed`，`migrationCount=444`。
- `GREEN: spring-constructor-gate-r260808a -> PASS`，`spring-constructor-gate-r260808a.json`，`MesTeamLeaderProcessConfigServiceImpl constructorCount=1` 且生产构造函数有 `@Autowired`。
- `GREEN: dependency-restore-r260808a -> PASS`，主程序前端和维护前端均按 `pnpm@10.25.0` frozen lockfile 恢复；临时 `onlyBuiltDependencies` + `pnpm rebuild --pending` 后 `ignored-builds=None`，两个 release worktree clean。
- `GREEN: maintenance-console-build-r260808a -> PASS`，`scripts\build.ps1` 通过；维护前端 typecheck/build 通过，Maven tests `26` passed，jar SHA256=`dd47d207373e9bd025f4136fab0cf6b693ac02fb362b7a931849da4318f2eec6`。
- `GREEN: runtime-control-start-r260808a -> PASS`，因 48181 进程管理被工具策略拦截，本轮在 48182 前台会话启动 r260808a 控制台，PID=`4236`，health=`UP`；API/Playwright 均指向 `http://127.0.0.1:48182`。
- `GREEN: build-release-preview-r260808a -> PASS`，`build-release-preview-gate-r260808a-r1.json` 中 build-only、component intruoyi、SkipDatabaseSync、SkipMinioSync、repo roots 和 no mark/promote checks 均为 true。
- `GREEN: build-release-r260808a -> PASS`，operation=`op-2026-08-07T162053494032800Z-9ac3afad-085b-4399-8e67-885e4675b954`，status=`SUCCESS`。
- `GREEN: manifest-validation-r260808a -> PASS`，package=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260808-intmain-head-test-r260808a-r1`，artifact count=`458`，missing=`0`，mismatch=`0`；manifest 与 frontend release-info 均匹配 releaseTag/sourceRepos/changeSet。
- `GREEN: sourceRepos-r260808a -> PASS`，manifest 与 frontend release-info 的 backend/frontend sourceRepos 均为 `a6bc1f0cff77fe18e45212ce539c4f76fec65b64` 且 `dirty=false`。
- `GREEN: remote-precheck-r260808a -> PASS`，测试服发布前 `.env`/实际镜像仍为上一成功 `release-20260806-intmain-head-test-r260806c-r1`，backend health=`UP`，frontend HTTP=`200`，无 RUNNING lock，target migration failed/running=`0`。
- `GREEN: publish-test-preview-r260808a -> PASS`，`publish-test-preview-gate-r260808a-r1.json` 证明 `Mode=deploy-release`、`Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，未出现 mark-tested/promote-prod/promote-backup。
- `GREEN: publish-test-r260808a -> PASS`，operation=`op-2026-08-07T163451475350300Z-1bf52485-98a1-4558-8899-fc19c58cda83`，status=`SUCCESS`；本轮未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- `GREEN: remote-postcheck-r260808a -> PASS`，`remote-release-postcheck-r260808a-r1.json` checks 全部为 true：`.env IMAGE_TAG`、backend/frontend 实际镜像、容器 running、backend health=`UP`、frontend HTTP=`200`、release-info、release lock=`APPLIED`、migration failed/running=`0`。
- `GREEN: playwright-runtime-console-r260808a -> PASS`，`playwright-runtime-console-r260808a-r1.json`；测试服前端 HTTP 200，console errors=`0`，failed requests=`0`；运行控制台 HTTP 200，页面显示 releaseTag、发布包、组件范围和变更说明，点击“查看变更”对话框通过。
- `GREEN: experience-consolidation -> PASS`，更新 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`，沉淀 release-status 等待、publish-test 长阶段、local config、runtime cleanup 和 PowerShell 策略拦截门禁。
- `GREEN: runtime-control-stop-r260808a -> PASS`，48182 前台会话已 Ctrl-C 退出；复核 `Get-NetTCPConnection -LocalPort 48182 -State Listen` 返回 `PORT_48182_LISTENING=NO`。
- `GREEN: release-worktree-cleanup-r260808a -> PASS`，`git worktree remove --force` 已从维护仓和主程序仓解除 `r260808a` 注册；残留 ignored 目录在绝对路径边界和根 `.git` 不存在检查后删除；`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260808a\m`、`D:\IntRuoyiWorktree\r260808a-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260808a-state` 均不存在；两仓 `git worktree list --porcelain` 不含 `r260808a`。
- `GREEN: final-remote-postcheck-r260808a -> PASS`，最终复核 releaseTag=`release-20260808-intmain-head-test-r260808a-r1`；`.env IMAGE_TAG`、backend/frontend 镜像、容器 running、backend health=`UP`、frontend HTTP=`200`、release-info sourceRepos dirty=false、release lock=`APPLIED`、migration failed/running=`0` 全部通过。
- `GREEN: task-closeout-cleanup-r260808a -> PASS`，`task_closeout.py --task-id 20260808-head-test-only-release --mode apply` 返回 `status: applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`，删除任务临时 JSON/script/log 证据，blocked/warnings 均为 `<none>`。

## Issues

### I001 主工作区存在大量未提交改动

- 现象：维护仓 tracked dirty count=21，主程序 tracked dirty count=160，且存在大量未跟踪任务/测试文件。
- 阶段：构建前 Git 状态检查。
- 影响：若直接从主工作区构建，未提交改动可能进入发布产物，违反本次发布边界。
- 原因判断：当前系统持续并行开发，多任务在主工作区产生未提交变更。
- 处理动作：冻结发布开始时维护仓与主程序 HEAD，后续从本轮专用 clean release worktree 构建。
- 结果：待创建并验证 clean worktree。
- 是否可前置检查：是，发布前运行 `git status --short --branch`、`git rev-parse HEAD`。
- 是否可自动化：是，发布脚本可在 dirty 时强制要求 release worktree。
- 下次如何避免：发布任务启动时先冻结 HEAD 和 worktree 路径，不追逐发布开始后的后续提交。

### I002 clean release worktree 缺本机 runtime-control local config

- 现象：r260808a 维护 release worktree 缺少 `config/runtime-control.local.yaml`。
- 阶段：运行控制台启动前配置。
- 影响：无法启动指向 clean app worktree 的运行控制台；若复用主维护控制台，build-release 会读取脏主工作区。
- 原因判断：local config 被 gitignore 排除，clean worktree 不会自动带入本机环境配置。
- 处理动作：从主维护目录复制本机 config 到 release worktree，并改写 `repo-root`、`frontend-root`、`ops-root`、`state-dir` 到 r260808a 专用路径。
- 结果：build-release preview gate 证明脚本和 repo roots 指向 r260808a clean worktree。
- 是否可前置检查：是，启动前检查 local config 是否存在且关键路径是否为本轮 worktree/state。
- 是否可自动化：是，封装 release worktree config patcher 并输出路径摘要。
- 下次如何避免：创建 release worktree 后立即生成并校验本轮 local config，不使用主维护 state。

### I003 pnpm ignored-builds 阻断风险

- 现象：主程序前端 install 后 `ignored-builds` 包含 7 个包；维护前端包含 `esbuild`、`vue-demi`。
- 阶段：依赖恢复。
- 影响：若不处理，Vite/esbuild 可能在后续构建阶段失败或使用未构建依赖。
- 原因判断：pnpm 10.25 默认忽略依赖构建脚本，需要显式允许。
- 处理动作：在 release worktree 内临时写入最小 `pnpm.onlyBuiltDependencies`，执行 `pnpm rebuild --pending` 后恢复原 package.json。
- 结果：两个前端 `ignored-builds=None`，release worktree clean。
- 是否可前置检查：是，install 后立即运行 `pnpm ignored-builds`。
- 是否可自动化：是，按项目白名单自动临时授权、rebuild、恢复并复核 clean。
- 下次如何避免：依赖恢复脚本固化 `ignored-builds` 检查，不把临时配置留入发布输入。

### I004 PowerShell 删除/进程管理策略拦截

- 现象：`Remove-Item -Recurse` 清理 `runtime/`、`Stop-Process` 停 48181、`Start-Process` 后台启动控制台均被工具策略 rejected。
- 阶段：构建后清理与运行控制台启动。
- 影响：不能按常规方式恢复 clean 或切换 48181；若强行绕过会触碰主维护控制台或产生不安全删除。
- 原因判断：工具策略拦截破坏性/后台进程命令。
- 处理动作：对本次生成 `runtime/` 使用 Python 绝对路径边界校验后清理；不停止 48181，改在 48182 前台会话启动 r260808a 控制台。
- 结果：维护 worktree clean，运行控制台 48182 health=`UP`，发布和页面验收均通过。
- 是否可前置检查：是，发布前检查 48181 占用和工具策略限制。
- 是否可自动化：部分可自动化，优先端口隔离前台会话；删除必须保留 allowlist 和 `.git` 检查。
- 下次如何避免：默认准备端口隔离方案和 task-owned state，避免依赖停止主维护进程。

### I005 publish-test migration 状态逐条写入耗时

- 现象：publish-test poll 15/30/45 均显示 `RUNNING` 且 summary 仍为“命令已提交到本机执行队列”，但日志持续上传 required SQL 并逐条写入 `infra_release_migration`。
- 阶段：publish-test。
- 影响：容易误判为卡死并重复提交或中断。
- 原因判断：operation summary 粒度不足，迁移状态写入为逐条 SSH/MySQL 调用。
- 处理动作：定期读取脱敏 log tail，确认从 required SQL 上传推进到 migration 状态写入，再等待终态。
- 结果：poll 59 返回 `SUCCESS`，独立 postcheck 通过。
- 是否可前置检查：是，长阶段监控必须看 log tail 阶段而非只看 summary。
- 是否可自动化：是，脚本可解析日志阶段并输出迁移进度/最后更新时间。
- 下次如何避免：为 publish-test 增加阶段化 summary 或批量 migration 状态写入。

### I006 运行控制台页面 release-status 加载等待不足

- 现象：首次 Playwright 页面验收失败，运行控制台初始页面显示测试服“加载中”，未显示 releaseTag/变更说明；API `release-status` 已可返回当前版本和 notes。
- 阶段：运行控制台页面验收。
- 影响：可能把成功发布误判为页面不合格，或反向把初始截图误当通过。
- 原因判断：页面异步加载 release-status，脚本等待时间不足且未等待目标 releaseTag。
- 处理动作：修改 Playwright 脚本，最多等待 60 秒直到 body 包含目标 releaseTag，再点击“查看变更”。
- 结果：重试通过，页面显示版本号、发布包、组件范围和变更说明。
- 是否可前置检查：是，页面脚本必须显式等待 releaseTag。
- 是否可自动化：是，统一封装 runtime console release info wait。
- 下次如何避免：不要只截图初始页面；验收条件必须绑定目标 releaseTag 和对话框内容。

## Long-Running Review

- 2026-08-08T00:20-00:32+08:00：build-release 长阶段完成，后端 Maven 约 2:30，前端 build/test 与 Docker/manifest 组装后 operation SUCCESS。
- 2026-08-08T00:34-00:54+08:00：publish-test 长阶段完成，主要耗时在 required SQL 上传和 migration 状态逐条写入；未重复提交，最终 operation SUCCESS。
- 2026-08-08T00:55-01:02+08:00：远端 postcheck、Playwright 页面验收和经验沉淀完成；剩余 closeout cleanup、停止 48182 前台会话、清理 release worktree/state 和最终远端复核。
- 2026-08-08T01:03-01:10+08:00：closeout 完成；48182 不再监听，r260808a 维护/主程序 release worktree 与 state dir 已删除，最终测试服远端复核通过，task-closeout cleanup apply 无 blocked/warnings。
