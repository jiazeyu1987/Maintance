# 20260713 当前 HEAD 仅测试服发布执行日志

## Initial Request

- REQUEST: 用户要求仅基于当前分支最新已提交代码构建并发布到测试服务器；未提交改动不得进入构建产物。
- SCOPE: 仅测试服；允许 `build-release` 与 `publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服和备份服发布。
- HARD RULE: 构建来源、manifest、版本号或变更说明无法确认即 fail fast；不得复用旧 releaseTag 拼接成功证据。
- STARTED: 2026-07-13T18:45:00+08:00。

## Milestone 1 - Task Bootstrap

- GREEN: previous-owned-task -> PASS，上一当前线程任务 `20260713-project-experience-consolidation` 已标记 completed 并完成隔离提交。
- GREEN: task-directory -> PASS，创建 `doc/tasks/20260713-current-head-test-only-release/`。
- GREEN: task-doc-bootstrap -> PASS，写入任务目标、里程碑、预期验证、BDD、设计约束和经验门禁。

## Milestone 2 - Experience Preflight

- COMMAND: 读取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`。
- GREEN: experience-preflight -> PASS，当前任务命中仅测试服发布范围、干净 release worktree、Manifest v1、PowerShell/SSH/日志脱敏、真实运行态和页面版本说明验收门禁。

## Milestone 3 - Git Baseline And Release Worktree

- GREEN: main-workspace-git-status -> PASS，维护仓 `int_main` HEAD=`efa0cfd79c75a48de807a40e1e80deefff63e6ee`，后端 `int_main` HEAD=`bc38e943d6c7648ed10347dcfe64796c6348f085`，前端 `int_main` HEAD=`07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa`。
- NOTE: main-workspace-dirty -> 主工作区均存在未提交/未跟踪改动；按门禁不得直接构建，必须使用冻结 release worktree。
- ISSUE: stale-release-worktree -> 现象：计划路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t` 已存在，维护仓 worktree 为当前维护 HEAD，但后端=`cc34722db2b6d5dbadb9c931f78f8fdc4f6e6c39`、前端=`f55c37c5adb14a33b4ba2e127a7910f5d78a53fb`，落后本轮用户请求开始时的当前 HEAD。阶段：Git/worktree。影响：旧 releaseTag `release-20260713-current-head-test-r260713t-r2` 即使 build 成功也不能作为本轮验收产物。原因判断：上一轮中断后留下已冻结但未完成的 release worktree。处理动作：停止引用旧 worktree 的 48181 控制台，废弃旧 r1/r2 releaseTag，重建后端/前端 worktree 到本轮冻结 HEAD。结果：后端/前端 worktree 已重新检出到当前 HEAD 且 clean。是否可前置检查：是。是否可自动化：是，发布开始时自动比对 worktree HEAD 与主分支冻结 HEAD。下次如何避免：如任务续跑，必须先复核已有 release worktree 提交，不匹配即废弃并重建。
- GREEN: release-worktree-freeze -> PASS，维护仓 worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\m` HEAD=`efa0cfd79c75a48de807a40e1e80deefff63e6ee` clean；后端 worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\b` HEAD=`bc38e943d6c7648ed10347dcfe64796c6348f085` clean；前端 worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\f` HEAD=`07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa` clean。
- GREEN: runtime-control-config-boundary -> PASS，运行控制台外部配置 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t-state\runtime-control.local.yaml` 指向本轮 release worktree，state-dir 位于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t-state\runtime-control`，不污染 Git worktree。

## Milestone 4 - Runtime Control Cleanliness Repair

- ISSUE: runtime-dir-dirty-after-resume -> 现象：恢复任务后维护 release worktree 出现未跟踪 `runtime/`，`git status --porcelain --ignored=no` 返回 `?? runtime/`。阶段：Git/worktree 构建前复核。影响：若继续构建，可能导致 sourceRepos dirty 或无法证明维护控制台只来自冻结 HEAD。原因判断：前一轮运行控制台曾把运行态目录写入 release worktree，外部 `state-dir` 配置未覆盖历史残留。处理动作：停止本任务 48181 Java 进程 PID `33416`，仅在固定安全路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\m\runtime` 内删除未跟踪残留，再以外部 state 配置重启运行控制台。结果：维护 worktree `git status` 为空，48181 health=`UP`，PID=`59088`。是否可前置检查：是。是否可自动化：是，启动控制台后立即执行三仓 `git status --porcelain --ignored=no`。下次如何避免：运行控制台 state/log/cache 必须位于 release worktree 外部；发现 `?? runtime/` 必须先清理或阻塞。
- ISSUE: config-read-secret-output -> 现象：直接读取 `runtime-control.local.yaml` 时终端输出包含 NAS 凭据字段。阶段：运行控制台配置复核。影响：原始输出不得写入任务证据或提交，后续配置读取必须使用字段 allowlist 或脱敏。原因判断：配置文件本身含凭据，普通 `Get-Content` 不适合作为证据采集命令。处理动作：后续任务记录只保留路径、repo-root、frontend-root、state-dir 等非敏感字段，不保存原始配置输出。结果：未提交 secret-bearing 原始输出。是否可前置检查：是。是否可自动化：是，配置证据采集脚本默认脱敏 secret key。下次如何避免：禁止打印完整 runtime-control 配置、`.env` 或 runtime-env。
- GREEN: runtime-control-restart -> PASS，运行控制台从 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 重新启动，配置使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t-state\runtime-control.local.yaml`，`http://127.0.0.1:48181/actuator/health=UP`，维护 worktree clean。

## Milestone 5 - Build Artifact And Manifest Verification

- GREEN: build-operation -> PASS，采用已在本轮冻结 worktree 内完成的 `build-release` operation `op-2026-07-13T114933441747800Z-ea18fdef-4abd-44e8-a712-8615a67b95bf`，releaseTag=`release-20260713-current-head-test-r260713t-r3`，status=`SUCCESS`；旧 r1 failed 与旧 r2 不作为本次验收产物。
- GREEN: manifest-v1 -> PASS，发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-current-head-test-r260713t-r3\manifest.json` 存在；`publishScope=code-only`；`changeSet.summary=Release package release-20260713-current-head-test-r260713t-r3`；backend commit=`bc38e943d6c7648ed10347dcfe64796c6348f085` dirty=false；frontend commit=`07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa` dirty=false；artifact count=`295` 且抽样/清单 sha256 校验通过；未发现 forbidden data directories。
- ISSUE: manifest-maintenance-source-gap -> 现象：Manifest v1 `sourceRepos` 仅记录后端和管理前端，不记录维护仓 commit。阶段：Manifest 来源校验。影响：发布包业务来源可由 manifest 证明，但维护控制台/脚本来源需用 release worktree HEAD、进程命令行和任务日志单独证明。原因判断：当前 Manifest 契约聚焦发布包内容，未纳入维护仓执行器来源。处理动作：将维护仓 HEAD=`efa0cfd79c75a48de807a40e1e80deefff63e6ee`、运行 Jar 路径和 clean 状态记录为补充证据。结果：本次构建来源仍可证明，长期可考虑把 maintenance source 写入 build evidence。是否可前置检查：是。是否可自动化：是。下次如何避免：Manifest 校验器区分“发布包 sourceRepos”和“维护执行器来源证据”。

## Milestone 6 - Publish-Test

- ISSUE: release-status-timeout -> 现象：`/release-status` 与 `/release-packages` API 在候选扫描时 30 秒超时。阶段：发布包候选/状态查询。影响：不能依赖候选列表作为本轮目标包可用性的唯一证据。原因判断：历史发布包较多，候选扫描耗时不稳定。处理动作：改为直接校验目标 releaseTag 的本地发布包和 Manifest，再执行 publish-test preview。结果：未阻塞发布，候选扫描超时作为可优化项记录。是否可前置检查：是。是否可自动化：是，指定 releaseTag 时优先 direct manifest lookup。下次如何避免：运行控制台候选接口增加指定 tag 快路径或分页缓存。
- GREEN: publish-test-preview -> PASS，preview action=`publish-test`、environment=`test`、script=`ops\deploy\publish-int-ruoyi.ps1`、`-Mode deploy-release`、`-Environment test`、`-ReleaseTag release-20260713-current-head-test-r260713t-r3`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`；未出现 `mark-tested`、`promote-prod`、`promote-backup` 或正式/备份实际目标动作。
- GREEN: publish-test-operation -> PASS，operation `op-2026-07-13T121325438123300Z-549989ce-c0b2-4cab-bc66-e7dfc0630394` status=`SUCCESS`；仅执行测试服发布，未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- ISSUE: publish-test-log-secret -> 现象：publish-test operation log 中出现 `mysql -p...` 明文参数形态。阶段：发布日志采集。影响：原始 operation log 不得保存到任务证据或提交。原因判断：发布脚本调用 MySQL CLI 时完整命令进入 stdout/stderr。处理动作：工具输出后续展示统一脱敏，任务记录只保存 operationId 和结构化结果，不保存原始日志。结果：无 secret-bearing 原始日志进入仓库。是否可前置检查：是。是否可自动化：是，operation log 保存前强制 secret scan。下次如何避免：发布脚本日志器默认脱敏 `mysql -p<secret>`。

## Milestone 7 - Test Runtime Verification

- ISSUE: ssh-stdin-n-flag -> 现象：首次远端验证使用 `ssh -n ... bash -s`，stdin 脚本未发送，采集结果为空。阶段：运行态独立验证。影响：所有断言初次失败，但不能据此判定服务器运行态失败。原因判断：`-n` 会将 SSH stdin 指向空输入，与 `bash -s` 传脚本冲突。处理动作：移除 `-n` 后重跑。结果：脚本进入远端执行。是否可前置检查：是。是否可自动化：是，检测 `ssh -n ... bash -s` 组合直接阻断。下次如何避免：需要传 stdin 的 SSH 禁用 `-n`。
- ISSUE: windows-textmode-crlf -> 现象：Python `subprocess.run(..., text=True, input=script)` 在 Windows 下将 LF 转为 CRLF，远端 bash 报 `set: -\r invalid option`、`cd: /opt/intruoyi/runtime\r`。阶段：运行态独立验证。影响：远端验证脚本未执行，不能作为运行态失败证据。原因判断：Windows 文本模式 stdin 自动换行转换。处理动作：改为 `input=script.encode('utf-8')` 二进制 stdin，并强制 LF。结果：远端 `.env`、compose、容器和 release-info 采集正常。是否可前置检查：是。是否可自动化：是。下次如何避免：Windows -> SSH -> bash 多行脚本统一用 UTF-8 bytes + LF。
- ISSUE: mysql-double-quote-filter -> 现象：远端 MySQL 只读验证里用双引号字符串过滤 `target_environment="test"` 时结果为空。阶段：发布锁/迁移状态核验。影响：锁和 migration 初次断言失败。原因判断：当前 MySQL SQL mode/解析习惯下双引号不可靠，且多层引号容易污染。处理动作：改用 stdin heredoc + 单引号 SQL 查询。结果：`infra_release_operation_lock` 返回 `test APPLIED test-release-20260713-current-head-test-r260713t-r3`，migration failed count=`0`。是否可前置检查：是。是否可自动化：是。下次如何避免：远端 SQL 核验用 heredoc/stdin 和单引号字面量，不用多层双引号过滤。
- GREEN: test-runtime-verification -> PASS，测试服 `172.30.30.58` 验证通过：`.env IMAGE_TAG=release-20260713-current-head-test-r260713t-r3`；backend image=`intruoyi-backend:release-20260713-current-head-test-r260713t-r3`；frontend image=`intruoyi-frontend:release-20260713-current-head-test-r260713t-r3`；backend/frontend containers running；backend health HTTP 200 `UP`；frontend HTTP 200 且 HTML 非空；PDF worker HTTP 200；`/release-info.json` releaseTag、publishScope、backend/frontend commits、dirty=false 均匹配；release lock=`APPLIED`；migration failures=`0`。

## Milestone 8 - Runtime Console Page Verification

- GREEN: maintenance-frontend -> PASS，从本轮维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t\m\frontend` 启动前端 dev server 到 `http://127.0.0.1:48182/`，proxy 指向 48181，health/page HTTP 200。
- GREEN: runtime-console-page -> PASS，Playwright 使用已安装 Chrome 打开 `http://127.0.0.1:48182/`，页面显示 `release-20260713-current-head-test-r260713t-r3`，点击“查看变更”后“版本变更说明”对话框包含 releaseTag 和变更说明，console errors=`0`，warnings=`0`。

## Milestone 9 - Experience Consolidation

- GREEN: release-experience-candidates -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t-state\runtime-control\release-experience-candidates.md`，候选项覆盖 manifest sourceRepos dirty=false 与目标环境基线核对。
- GREEN: experience-consolidation -> PASS，本次新增/强化门禁写入 `docs/powershell-preflight-lessons.md`、`docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md` 和 `docs/experience-index.md`：覆盖 SSH stdin 禁用 `-n`、Windows binary stdin LF、远端 SQL heredoc 单引号、配置/日志脱敏、运行控制台 state-dir/`runtime/` dirty 复核、候选列表超时时的 direct manifest lookup。

## Milestone 10 - Ready For Closeout

- GREEN: verification-report -> PASS，`verification-report.md` 已记录发布链路、Manifest、测试服运行态、页面版本说明和问题清单。
- GREEN: runtime-control-main-restore -> PASS，已停止本轮 release worktree 48181/48182 进程，从主工作区 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 重启 48181，`/actuator/health=UP`，长运行日志位于主仓 `logs/`。
- RED_THEN_GREEN: release-worktree-remove -> 初次 `git worktree remove` 维护 worktree 返回 `Directory not empty`，后端删除成功，前端注销后物理目录残留；按门禁确认三仓注册项均消失、无进程引用、路径位于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713t` 后清理只读属性并删除物理残留。最终 `r260713t` root exists=false，`r260713t-state` exists=false。
- GREEN: task-closeout-preview -> PASS，keep=`task.md/execution-log.md/verification-report.md`，delete=`migration-policy-gate-r260713t.json/runtime-console-r260713t-r3.png`，blocked=<none>，warnings=<none>。
- GREEN: task-closeout-apply -> PASS，临时 JSON 与 Playwright screenshot 已删除，核心任务记录保留。
- GREEN: final-closeout -> PASS，无非当前进程命令行引用 `IntRuoyiWorktrees\r260713t`；维护/后端/前端 worktree registrations absent；主运行控制台 health=`UP`；任务状态已更新为 `completed`。
