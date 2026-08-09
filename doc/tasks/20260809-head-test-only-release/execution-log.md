# 2026-08-09 当前 HEAD 仅测试服发布执行日志

## BDD Scenarios

- BDD: 已提交 HEAD 独占构建输入 -> Given 维护仓或主程序仓可能存在未提交改动，When 从任务启动时冻结 HEAD 创建本轮专用干净临时 worktree 并构建，Then 发布包 sourceRepos 只包含冻结提交且 dirty=false。
- BDD: 仅测试服发布 -> Given 已验证的单一 releaseTag 构建包，When 执行发布，Then 只调用 `publish-test`，不调用 `mark-tested`、`promote-prod` 或 `promote-backup`。
- BDD: 真实运行态验收 -> Given `publish-test` operation 成功，When 检查测试服真实服务与运行控制台，Then 镜像、容器、健康、HTTP、页面、版本号和变更说明全部与本轮 releaseTag 一致。
- BDD: 关键证据失败即阻塞 -> Given 构建来源、manifest、版本、变更说明或运行态任一项不可确认，When 到达发布或完成判定门禁，Then 停止后续动作并记录问题，不降级或默认成功。

## Execution Evidence

- 2026-08-09：已创建任务文档；尚未执行构建、发布或服务器写入。
- `BOOTSTRAP: utf8-read-rules -> PASS`，已读取适用 AGENTS、上一同类任务状态、经验索引、PowerShell 共同规则和 CI/CD evidence contract。
- `PREVIOUS_TASK: doc/tasks/20260808-head-test-only-release/task.md -> completed`，上一轮同类发布已完成，本任务可继续。
- `GREEN: experience-preflight -> PASS`，已读取 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`worktree-restrictions.md`、`release-backup-restore.md`、`server-access.md`、`login-access.md`；仅允许 `build-release -> publish-test`，禁止 `mark-tested`、`promote-prod`、`promote-backup`。
- `GIT: maintenance-main -> branch=int_main, HEAD=1978562394fbc722f8b534988ddf1e3f0e4f8846, dirtyCount=164, statusSha256=5b7666ec61de601aff2ff326015eabddc184f372b8108a2cf8d1596261652ec7`。
- `GIT: app-main -> branch=int_main, HEAD=199836c5fc105033898c2df59fb8ca22ac005625, dirtyCount=897, statusSha256=9d96b2fe48924ae434523b83948289357711d2d14f2a9d6da5d8ea80ca597fd2`；后端和前端共用 `E:\IntRuoyi` Git root。
- `BOUNDARY: release-freeze -> maintenance HEAD=1978562394fbc722f8b534988ddf1e3f0e4f8846, app HEAD=199836c5fc105033898c2df59fb8ca22ac005625, releaseId=r260809a, planned releaseTag=release-20260809-intmain-head-test-r260809a-r1`；本轮不 fetch，不追逐后续提交。
- `LOCAL_PORTS: 48181/48182/48183 -> no listener`；后续运行控制台使用任务自有隔离端口，启动前再次核对。
- `GREEN: maintenance release worktree -> PASS`，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a\m` 指向 `1978562394fbc722f8b534988ddf1e3f0e4f8846`，detached 且 dirty count=0。
- `GREEN: app release worktree -> PASS`，`D:\IntRuoyiWorktree\r260809a-release-app` 指向 `199836c5fc105033898c2df59fb8ca22ac005625`，detached 且 dirty count=0。

## Problems

### I001 主工作区存在大量未提交改动

- 现象：维护仓 dirty count=164，主程序仓 dirty count=897。
- 阶段：构建前 Git 状态检查。
- 影响：直接从主工作区构建会让未提交内容进入产物，违反冻结 HEAD 边界。
- 原因判断：系统持续开发且存在多个并发任务、构建产物和未跟踪文件。
- 处理动作：冻结两仓 HEAD，使用 `r260809a` 专用 detached clean release worktree 构建。
- 结果：两个专用 release worktree 均已创建，HEAD 匹配且 clean。
- 是否可前置检查：是，发布入口先执行 branch/HEAD/status 快照。
- 是否可自动化：是，dirty 时强制拒绝主工作区构建并生成 worktree 基线 JSON。
- 下次如何避免：每次发布先冻结 HEAD 和专用 worktree；构建开始后不追逐主分支更新。

### I002 主程序 Git status 扫描旧 target_corrupt 目录产生告警

- 现象：`git status --porcelain` 退出码为 0，但扫描 `IntRuoyiBackend/yudao-module-mes/target_corrupt_m4_20260802_1327` 时多次提示子目录不存在。
- 阶段：构建前 Git 状态检查。
- 影响：不影响 HEAD 冻结，但主工作区状态噪音大，不能作为构建输入。
- 原因判断：主工作区存在旧损坏/并发变动构建目录，Git 遍历时遇到消失的子路径。
- 处理动作：保留告警证据，不修改主工作区；以冻结提交创建全新 clean worktree。
- 结果：待在 worktree 中复核无同类告警且状态 clean。
- 是否可前置检查：是，记录 status 退出码和 stderr，并区分退出失败与 warning。
- 是否可自动化：是，Git 快照脚本可单独捕获 stderr 和状态哈希。
- 下次如何避免：发布输入始终使用 clean worktree；主工作区残留清理由归属任务处理。

## Stage Reviews

- 当前进度：Git / worktree 门禁。
- 已完成步骤：读取适用规则与经验门禁，确认上一任务 completed，冻结维护仓和主程序仓 branch/HEAD/status，锁定 release id/tag/path。
- 阻塞点：无。
- 耗时原因：主程序 Git status 遍历 897 项 dirty 内容并产生旧 target_corrupt 路径告警，但命令退出码为 0。
- 下一步动作：创建并验证两个 detached clean release worktree，配置任务自有 state dir。

## Build And Publish Evidence

- `GREEN: migration-policy-gate -> PASS, migrationCount=453`；构建前 required SQL 元数据和依赖策略通过。
- `GREEN: app-frontend-dependency-restore -> PASS, pnpm ignored-builds=none`；依赖安装真实子进程退出后复核，临时 `onlyBuiltDependencies` 配置已移除，主程序 release worktree clean。
- `GREEN: maintenance-dependency-restore -> PASS, pnpm ignored-builds=none`；维护前端待构建脚本已执行，临时配置与构建测试产生的 4 个 runtime JSON 已精确移除，维护 release worktree clean。
- `GREEN: maintenance-build -> PASS, Maven tests=26 passed, JAR SHA256=054c79ff442ccad4b5fbfd8f55958131b5b7ebdbbf0650098511bf52065ebfd3`。
- `GREEN: runtime-control-isolation -> PASS, url=http://127.0.0.1:48182, PID=26248`；repo/frontend/ops/state 均只指向 `r260809a` clean worktree 或任务 state dir。
- `GREEN: build-release -> PASS, operation=op-2026-08-09T154417143232100Z-1cbd9f9c-35e8-4b3f-9cda-1646af3f808f, status=SUCCESS`；只执行构建发布包动作。
- `GREEN: manifest-validation -> PASS, releaseTag=release-20260809-intmain-head-test-r260809a-r1, artifacts=467, missing=0, hashMismatch=0`；`manifest.json`、legacy manifest、frontend `release-info.json` 均存在；backend/frontend commit=`199836c5fc105033898c2df59fb8ca22ac005625`、dirty=false；changeSet 完整。
- `GREEN: remote-precheck -> PASS`；发布前测试服旧版本运行态、目标迁移 failed/running=0 和现有 release lock 已冻结，未发现阻塞。
- `GREEN: publish-test-preview -> PASS`；Environment=`test`、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`，无正式服、备份服、`mark-tested` 或 promote 动作。
- `GREEN: publish-test -> PASS, operation=op-2026-08-09T155709667969700Z-6d3f54cc-4892-4b0e-8c49-624bacd79bfe, status=SUCCESS`；同一 releaseTag 完成仅测试服发布。
- `GREEN: remote-runtime-postcheck -> PASS`；`.env IMAGE_TAG`、backend/frontend image tag 均匹配本轮 releaseTag；两容器 running；backend health=`UP`；frontend HTTP=`200`；release-info source dirty=false；release lock=`APPLIED`；migration status=`APPLIED:8, SKIPPED_ALREADY_APPLIED:411`、failed/running=`0`。
- `GREEN: playwright-test-frontend -> PASS`；真实浏览器打开 `http://172.30.30.58:8081/`，HTTP 200，最终登录页标题=`瑛泰管理系统 - 登录`，console error=0，failed request=0。
- `GREEN: playwright-runtime-console -> PASS`；真实浏览器打开 `http://127.0.0.1:48182/` 并点击 `查看变更`，页面显示本轮 releaseTag、发布包和 `组件范围：intruoyi`，build/publish operation 均为 SUCCESS，console error=0，failed request=0。
- `REGRESSION: release-scope -> PASS`；操作记录只有本轮 `build-release` 与 `publish-test`，未执行 `mark-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。

## Additional Problems

### I003 pnpm 启动进程返回但任务子进程仍在运行

- 现象：两次 `corepack pnpm@10.25.0 install` 的承载进程已返回，但 PID 36852、30364 的 Node 子进程仍并发安装，不能用承载进程退出判断依赖完成。
- 阶段：主程序 release worktree 前端依赖恢复。
- 影响：若直接进入构建，可能读到未完成或互相争用的 `node_modules`，破坏可重复构建。
- 原因判断：Corepack/终端承载层先于实际 pnpm 子进程结束，且重复启动造成两个任务自有安装进程并发。
- 处理动作：核实命令行和 worktree 归属后仅停止两个任务自有子进程，改为单一 TTY 直连 pnpm 并等待真实退出。
- 结果：单次安装约 11 分 9 秒后正常退出，依赖可执行文件和 `ignored-builds` 后置检查通过。
- 是否可前置检查：是，进入 build 前枚举目标 worktree 下残留 pnpm/node/esbuild 进程。
- 是否可自动化：是，以进程树、命令行路径、退出码和关键二进制存在性组成 dependency-ready gate。
- 下次如何避免：同一 worktree 只允许一个依赖恢复进程；不得以外层 shell/corepack 返回替代真实子进程完成证据。

### I004 pnpm 安全策略忽略原生依赖构建脚本

- 现象：主程序初始有 7 个 ignored builds，维护前端有 `esbuild`、`vue-demi` ignored builds。
- 阶段：依赖恢复后置检查。
- 影响：Vite/esbuild 或运行控制台构建可能缺少必要生成物，构建来源虽 clean 但依赖状态不完整。
- 原因判断：冻结提交未声明当前 pnpm 版本需要的 `onlyBuiltDependencies` 批准列表。
- 处理动作：仅在隔离 worktree 临时声明实际待构建包，执行 `pnpm rebuild --pending`，随后移除临时字段并恢复文件字节状态。
- 结果：两个前端 `ignored-builds=none`，临时改动未进入 Git，两个 release worktree clean。
- 是否可前置检查：是，dependency restore 后强制运行 `pnpm ignored-builds`。
- 是否可自动化：是，维护统一、可审计的 allowlist 输入并在退出时强制复核 Git clean。
- 下次如何避免：将依赖构建批准作为发布依赖恢复的正式门禁，不在生产源码或发布 manifest 中留下临时配置。

### I005 PowerShell 复合表达式出现解析错误

- 现象：一次内联对象/表达式命令报 `Missing closing ')'`。
- 阶段：依赖和 worktree 状态汇总。
- 影响：该次只读汇总未执行成功；未修改代码、构建产物或服务器。
- 原因判断：PowerShell 5.1 复合表达式括号层级过深，转义可读性不足。
- 处理动作：拆分为单一职责命令逐项执行，并分别核退出码。
- 结果：后续检查全部完成，未降级或跳过证据。
- 是否可前置检查：是，可先执行 parser-only 或使用脚本文件。
- 是否可自动化：是，把结构化检查固化为受测脚本，避免长 inline 表达式。
- 下次如何避免：PowerShell 风险命令不拼装多层内联对象，拆分命令并保留独立退出码。

### I006 publish-test 长时间运行且摘要没有实时表达细粒度进度

- 现象：operation 在约 24 分钟内持续 RUNNING，摘要文本变化有限，但日志持续上传 required SQL、写入 migration 状态并推进。
- 阶段：仅测试服发布。
- 影响：若只看摘要，容易误判卡死并重复提交，导致并发发布和 release lock 风险。
- 原因判断：required SQL 数量较多，operation 摘要粒度低于实时日志粒度。
- 处理动作：保持唯一 operation，按 operation id 轮询，同时检查日志增长和 migration 文件推进；未重提发布。
- 结果：第 74 次轮询获得 SUCCESS，随后远端运行态全部通过。
- 是否可前置检查：是，发布前统计 required SQL 数量并估算阶段时长。
- 是否可自动化：是，控制台可展示当前文件、已处理/总数、日志最后推进时间和预计剩余时间。
- 下次如何避免：长 operation 只要日志和状态表持续推进就等待；无超时证据前禁止重复点击或重复提交。

### I007 运行控制台监听端口与页面静态说明不一致

- 现象：任务控制台实际监听 `48182`，页面标题区仍显示 `本机运维台 · 127.0.0.1:48181`；实例矩阵同时显示本机 backend 48081 STOPPED。
- 阶段：Playwright 运行控制台验收。
- 影响：静态端口文案可能误导观察者；本机实例矩阵不代表测试服远端运行态。
- 原因判断：页面说明使用固定默认端口，实例矩阵按本机默认服务探测，未根据当前监听端口和远端发布目标动态表达。
- 处理动作：按实际 URL/HTTP 和页面 release-info 验证控制台；测试服容器、health、HTTP 另用远端结构化 postcheck 独立验收。
- 结果：控制台版本/变更说明与远端测试服运行态均通过；该文案差异不影响本次发布结论。
- 是否可前置检查：是，浏览器结果同时记录实际 URL、静态标题和目标环境。
- 是否可自动化：是，标题端口从运行时请求派生，并在 UI 区分本机实例矩阵与远端环境版本。
- 下次如何避免：不得用本机实例矩阵代替测试服验收；控制台验收必须与远端 postcheck 组合判定。

### I008 阶段性耗时表述换算错误并已立即更正

- 现象：一次阶段更新将第 60 次、20 秒间隔轮询误述为“约一小时”，随后立即更正为约 20 分钟。
- 阶段：publish-test 长时间过程沟通。
- 影响：不影响命令或发布状态，但会干扰耗时判断。
- 原因判断：人工口算未使用 operation 请求时间与当前时间的精确差值。
- 处理动作：立即更正；最终复盘按 operation 时间戳计算。
- 结果：构建约 12 分钟、发布约 24 分钟的记录与 operation 时间一致。
- 是否可前置检查：是，状态汇报前由时间戳自动计算 duration。
- 是否可自动化：是，轮询脚本直接输出 elapsed 和 last-progress-age。
- 下次如何避免：耗时只引用自动计算值，不用轮询次数进行人工估算。

### I009 维护构建测试生成任务态 runtime JSON

- 现象：维护构建后出现 4 个未跟踪 runtime 测试 JSON。
- 阶段：维护控制台构建后 worktree clean 复核。
- 影响：若不清理会破坏 release worktree clean 证据，并可能干扰 state-dir 来源判断。
- 原因判断：测试生成运行态文件但未在测试退出时清理。
- 处理动作：确认文件均为本轮测试生成后精确删除，并重新核对 Git 状态。
- 结果：维护 release worktree 恢复 clean，未删除任何其他任务或用户文件。
- 是否可前置检查：是，构建前后对 worktree status 做差异比对。
- 是否可自动化：是，测试使用临时目录并在 finally 清理，或构建脚本声明精确输出 allowlist。
- 下次如何避免：runtime 测试输出必须写到 task state/temp，不得落在 release source tree。

## Long-running Stage Reviews

- 依赖恢复：主程序 pnpm 单一真实安装约 11 分 9 秒；主要耗时为 1165 个包的链接/硬链接和 ignored build 后置处理。阻塞点无；下一步为 maintenance build。
- 构建发布包：23:44 左右提交、23:55 完成，约 12 分钟；Maven 多模块构建、前端 production build 和两镜像构建持续推进。阻塞点无；下一步为 manifest fail-fast 校验。
- 测试服发布：23:57 左右提交、00:21 完成，约 24 分钟；required SQL 上传与 419 条 migration 状态处理为主要耗时。日志持续推进，未重复提交；下一步为远端结构化验收和 Playwright 页面验收。
- 验收：远端 postcheck 与两页面 Playwright 全部通过。当前无发布阻塞；下一步为经验沉淀、任务态切换、清理 task-owned worktree/state 并再次远端复核。

## Experience Consolidation

- 已更新 `docs/release-build-preflight-lessons.md`：新增 pnpm 真实子进程完成、ignored-builds 清零与构建后 clean worktree 门禁。
- 已更新 `docs/test-release-preflight.md`：新增 r260809a 成功闭环和长时间 publish-test 唯一 operation 进度门禁。
- 已更新 `docs/experience-index.md`：新增对应关键词路由。
- `GREEN: experience-consolidation -> PASS`；复用既有长期经验文档，未新建未经授权的长期文档。

## Closeout Evidence

- `GREEN: task-closeout-preview -> PASS`；keep 仅为 `task.md`、`execution-log.md`、`verification-report.md`，一次性任务证据和 `output/playwright/r260809a-release` 列为 delete，blocked/warnings 均为 none。
- `GREEN: runtime-control-stop -> PASS`；任务控制台 PID 26248 已 graceful shutdown，48182 listener=0，进程不存在。
- `GREEN: release-worktree-clean -> PASS`；移除前维护 worktree HEAD=`1978562394fbc722f8b534988ddf1e3f0e4f8846`、主程序 worktree HEAD=`199836c5fc105033898c2df59fb8ca22ac005625`，两者 `git status --porcelain` 均为空，未产生新提交，无需合回 `int_main`。
- `GREEN: release-worktree-registry-remove -> PASS`；两个 `git worktree list --porcelain` 均不再包含 `r260809a`。
- `GREEN: release-worktree-physical-remove -> PASS`；维护/app worktree 物理根、state dir 和空父目录均已删除；删除前确认无 `.git`、无进程引用且目标位于任务 allowlist；其它 worktree 未触碰。
- `GREEN: final-remote-runtime-postcheck -> PASS`；worktree/state 清理后测试服 `.env`、实际镜像、容器、backend health、frontend HTTP、release-info、release lock 和 migration 仍全部通过。

### I010 worktree Git 注册移除后 ignored 构建目录导致物理删除失败

- 现象：两个 `git worktree remove --force` 均先撤销 Git 注册，但返回 `Directory not empty`；原生 `Remove-Item` 又被本机命令策略拒绝。
- 阶段：发布成功后的 worktree closeout。
- 影响：若只检查 Git registry，会遗留任务专用 `node_modules`、构建输出和 state 物理目录，不能标记 completed。
- 原因判断：Git 不管理 ignored 依赖/构建输出；命令策略对递归 `Remove-Item` 做了额外拦截。
- 处理动作：确认 Git 注册消失、`.git` 不存在、没有进程引用、绝对路径属于 `r260809a` allowlist 后，使用 Node `fs.rmSync` 精确删除两个物理根和 state dir，再删除已验证为空的父目录。
- 结果：三个目标路径与空父目录均不存在，Git registry 无 r260809a，48182 无监听，其它 worktree 未触碰。
- 是否可前置检查：是，closeout 固定检查 registry、physical path、`.git`、process reference 和 ignored 输出。
- 是否可自动化：是，task-closeout 可在 Git remove 返回 Directory not empty 时执行 allowlist/registration/process guards 后清理 residual。
- 下次如何避免：依赖与构建输出尽量放 task cache/state；物理残留清理必须使用精确绝对路径和删除后复核，禁止扩大到 worktree 根父目录。

## Final Closeout

- `GREEN: task-closeout-apply -> PASS`；status=`applied`，keep=3，blocked=`none`，warnings=`none`；一次性 helper/evidence 与 `output/playwright/r260809a-release` 均已删除。
- `GREEN: closeout-filesystem -> PASS`；`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a\m`、`D:\IntRuoyiWorktree\r260809a-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260809a-state` 和空父目录均不存在。
- `GREEN: closeout-runtime -> PASS`；PID 26248 不存在，48182 listener=0，进程扫描无 `r260809a` 引用。
- `GREEN: closeout-git -> PASS`；维护仓与主程序仓 worktree registry 均无 `r260809a`；两个 release worktree 无新提交，无需合回 `int_main`；其它 worktree 未触碰。
- `GREEN: final-verdict -> PASS`；目标 releaseTag 的构建来源、manifest、版本变更说明、仅测试服 operation、真实运行态、页面验收、问题记录、经验沉淀和清理全部满足验收标准，任务状态=`completed`。
