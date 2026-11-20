# IntRuoyi PowerShell / Git 共同前置经验

> 路径约定：`docs/...` 相对本维护仓根目录；`IntRuoyiBackend/...`、`IntRuoyiFronted/...` 及其源码命令相对当次已验证配置确定的主程序根目录。不依赖盘符，不猜测源码目录。此文件沿用交接资料中的规则；当前用户授权和 AGENTS.md 优先。

## 适用场景

- PowerShell、Git、提交推送或清理问题按需查阅本文件，已读且未变化的规则不重复读取。
- 中文编码及收尾问题按需查阅相关说明；不要求固定读取顺序、任务目录或额外预检回执。

## Git 提交与推送门禁

### 停进程前验证文件原子替换与权限保全

- Trigger: Windows普通脚本执行器安装，需要停止旧进程并替换源码或私密配置。
- Preflight check: 停止前使用同一Python/PowerShell、同一目标卷的自有临时文件，实测原子替换、字节读回及ACL SDDL前后相等；检查调用者继承的模块路径。不能假定powershell.exe可以自动加载Get-Acl。使用.NET File.Replace时给出明确备份路径，避免Windows PowerShell把空备份参数转换为非法空路径。
- Blocker: 替换能力、ACL或备份读回未通过，禁止先停执行器。已停止后失败必须先核完整安装文件pins、配置及SQLite payload，确认实际成功前缀，不按异常推断完全未写入。
- Verification: 推荐在独立工作区准备安装输入，使用System.IO.File.GetAccessControl的SDDL及File.Replace验证原权限、原字节备份、新字节；实际安装后逐文件读回、非本次文件SHA不变、原稳定路径新PID与payload保持。
- Forbidden action: 不为通过检查去掉ACL验证，不忽略PowerShell错误退出码，不覆盖原备份或重派已经完成的替换；未核成功前缀不继续或盲目回滚。
- Evidence: doc/tasks/20261120-install-release-version-acceptance/execution-log.md；本次Get-Acl模块加载失败发生在首次替换前，复核全量原件保持后，用原生文件替换与SDDL验证完成安装。

阶段必查：停机前完成无副作用替换探针；停止后保全原件并逐项原子更新；启动后核源码、配置、任务历史及实际入口。Fail Fast按Blocker保留现场。必须记录探针退出码、替换集、成功前缀、ACL和SHA验证、原/新进程身份及恢复依据，私密原件不进Git。

### 合并前确认分支和远端版本

- Trigger: 跨分支融合、用户询问分支是否最新、目录名称与实际分支可能不同。
- Preflight check: 在实际工作目录运行 `git branch --show-current`、`git status --short --branch`，再通过 `git ls-remote --heads origin <分支>` 或 fetch 确认远端提交；功能核查注明代码所在分支与提交号。合并前按既有规则保存未提交改动，并单独记录部分实现的验证范围。
- Blocker: 分支身份不明、远端版本未确认、修改无法归属或工作区存在未处理冲突。
- Verification: 合并后用 `git merge-base --is-ancestor <已确认来源提交> HEAD` 验证来源已包含；重跑冲突文件的行为测试和端口守卫；推送后本地分支与远端一致。
- Forbidden action: 禁止用文件夹名判断分支、用本地远端跟踪引用冒充已查询远端、批量选择一侧冲突而丢失修复，或把基线保存误称为全部功能完成。
- Evidence: `doc/tasks/20260914-dcc-20-remediation/execution-log.md`。

### 按授权执行 Git 操作

- 仅在用户已授权范围内提交、推送或保存基线；不要求每个任务推送或拆分基线、实现、收尾提交。
- 执行前核对当前仓库、分支和暂存文件；仅推送任务才要求可用远端、凭据及网络，本地提交不因缺少 origin 阻塞。
- 只纳入本任务改动，不能混入其他任务、临时产物或秘密文件；不通过强制推送、破坏性重置或丢弃他人改动绕过失败。
- 实际命令失败如实报告；所要求的推送完成后核对目标远端结果，不强制固定记录文件或额外收尾提交。

### Git index.lock 陈旧锁恢复门禁

- Trigger: `git add`、`git commit`、`git merge` 或其它索引写操作报 `Unable to create '.git/index.lock': File exists`。
- Preflight check: 检查 `.git/index.lock` 的绝对路径、长度和最后写入时间，并只读枚举活动 `git` / `git-lfs` 进程；只有锁文件为 0 字节、超过 60 秒未更新且不存在活动 Git 进程时，才允许删除该精确锁文件。
- Blocker: 存在活动 Git 进程、锁文件非空、锁文件不足 60 秒、目标不是当前仓库精确 `.git/index.lock`，或删除后仍无法正常读取 Git 状态时必须停止。
- Verification: 删除后确认锁文件不存在，重新运行 `git status --short --branch`、原失败的索引写操作和 staged 文件清单检查；记录未停止任何运行进程。
- Forbidden action: 禁止看到 `index.lock` 就直接删除、强杀全部 Git/IDE 进程、删除其它 `.lock` 文件、清空 `.git` 或用新仓库绕过当前索引状态。
- Evidence: `doc/tasks/20260728-commit-int-main-frontend-backend-code-round2/execution-log.md`，基线暂存前确认零字节陈旧锁且无活动 Git 进程后恢复。

### 提交前 stale blocker 复验门禁

- Trigger: 准备提交时任务文档仍标记 `blocked`，但阻塞项可能已被其它并行改动修复。
- Preflight check: 不得直接按旧文档状态提交；先重跑旧 blocker 对应的最小门禁，例如 Maven compile、目标 JUnit、`pnpm ts:check` 或静态合同。
- Blocker: 复验仍失败、命令被沙箱/ACL 拦截且无法按审批重跑、或无法证明 blocker 已解除时，保持 blocked 并停止提交。
- Verification: 复验通过后更新 `task.md`、`execution-log.md` 和 `verification-report.md`，记录旧 blocker 解除、命令输出摘要和新的收尾状态。
- Forbidden action: 禁止只因用户要求提交就绕过 `blocked` 状态；禁止把旧 blocker 当作已解决而不重跑原门禁。
- Evidence: `doc\tasks\20260724-batch-fda-audit-log-coverage\execution-log.md`，2026-07-25 提交前重跑 Maven compile、目标 JUnit、`pnpm ts:check` 后解除旧阻塞；`doc\tasks\20260829-bpm-formcenter-compile-fix\verification-report.md`，BPM FormCenter 旧 `IOException` 编译 blocker 在当前源码中不可复现，使用 BPM clean compile、主应用 clean package 和 FormCenter 定向测试确认解除。

### 脏工作区基线门禁

- Trigger: 开始当前任务或准备提交/推送时，`git status --short --branch` 显示 tracked、untracked 或 staged 脏改动。
- Preflight check: 先识别当前任务自有文件；提交基线前查看 staged 文件清单，确保当前任务实现文件未进入基线提交，除非用户明确要求。
- Blocker: 无法区分当前任务文件和既有脏改动、发现敏感凭据、发现超大文件、存在合并冲突、或用户未授权把既有脏改动作为独立基线保存。
- Verification: 基线提交完成后记录 commit hash、`git show --name-status --oneline -1` 文件清单、以及新的 `git status --short --branch`。
- Forbidden action: 禁止为了获得 clean worktree 而删除、回滚、覆盖或静默忽略别人/并发任务的脏改动。
- Evidence: 用户授权记录、基线提交 hash、任务日志中的文件清单。

### 共享分支并发基线提交门禁

- Trigger: 多个任务共用同一分支或主工作区时，最近一次提交不是当前任务发起，且 `git show --name-status -1` 包含当前任务文件、其它任务文档、非当前模块源码或运行产物。
- Preflight check: 每次实现改动后、提交前、cleanup 前都运行 `git log --oneline -5`、`git show --name-status --oneline -1`、`git status --short --branch` 和当前任务文件的 `git diff HEAD -- <paths>`，确认当前任务改动是否已被并发基线提交吞入。
- Blocker: 当前任务实现被并发基线提交混入且需要严格任务独立提交、最近提交包含敏感文件/超大产物、或同一文件还有未区分 hunks 时，必须停止并让用户决定是否重建独立提交历史；不得继续用宽泛 `git add -A`。
- Verification: 若用户允许继续，任务日志必须记录并发提交 hash、混入范围、保留/不触碰的非任务文件、已通过的目标验证和后续只选择性暂存的文件清单。
- Forbidden action: 禁止把并发基线提交伪装成本任务实现提交；禁止因为 HEAD 已包含代码就跳过验证、任务文档或冲突记录；禁止擅自 amend、reset、force-push 或用新提交覆盖他人并发改动。
- Evidence: `doc\tasks\20260730-dcc-product-catalog-remove-toolbar-buttons\execution-log.md`，共享分支基线提交曾把 DCC 按钮删除任务文件和其它任务文件一起提交，后续只能记录异常并选择性收尾；`doc\tasks\20260804-approval-center-applicant-column\execution-log.md`，审批中心申请人列实现被并行基线提交吞入，后续保留验证证据并仅选择性提交收尾记录。

### 同文件并行改动选择性暂存门禁

- Trigger: 基线提交后继续出现并行改动，且当前任务与非本任务改动落在同一个源码或测试文件。
- Preflight check: 提交当前任务前先用 `git diff -- <path>` 区分本任务 hunks 与并行 hunks；使用选择性暂存或 cached patch，只暂存本任务变更。
- Blocker: 无法可靠区分 hunks、同一逻辑块互相覆盖、或测试只能在混入并行改动后通过时，必须停止并报告冲突。
- Verification: 提交前记录 `git diff --cached --name-status` 和目标文件 staged diff，确认 staged 内容只包含本任务改动；提交后用 `git status --short --branch` 确认并行改动仍留在工作区而未混入当前任务提交。
- Forbidden action: 禁止把同文件并行改动混进当前任务实现提交；禁止为了 clean 状态回滚、覆盖或删除并行改动。
- Evidence: `doc\tasks\20260726-route-flow-form-slot-count-badge\execution-log.md`，`RouteFlowGraphDesigner.vue` 在徽标任务中与并行表单配置改动同文件共存，需选择性暂存本任务 hunks。

### 文档目录精确暂存门禁

- Trigger: 用户询问或授权将 `scripts`、`doc`、`docs` 纳入 Git，且工作区同时存在源码、测试或并行任务改动。
- Preflight check: 先用 `git status --short --untracked-files=all -- scripts doc docs` 盘点候选文件，再用显式路径 `git add -- <paths>` 暂存；暂存后必须运行 `git diff --cached --name-status`。
- Blocker: 暂存区出现非本次授权范围的源码、测试、超大产物、临时日志、pid 或无法归属文件时，必须停止提交并清理暂存边界。
- Verification: 对误入暂存区但仍需保留工作区内容的文件，只使用 `git restore --staged -- <path>` 移出暂存区，并再次复核 cached 清单只剩授权目录。
- Forbidden action: 禁止用 `git add doc docs scripts` 或 `git add -A` 代替候选清单；禁止为了修正暂存区而回滚、删除或覆盖工作区改动。
- Evidence: 2026-07-28 文档目录加入 Git 前，复核发现前端源码/测试误在暂存区，使用 `git restore --staged` 保留工作区内容并只留下 `doc`、`docs` 文档文件。

### Ignored 路径暂存失败复核门禁

- Trigger: `git add` 大量路径时提示 `The following paths are ignored by one of your .gitignore files`，尤其命中 `doc/tasks/<task-id>`、临时测试目录或生成证据目录。
- Preflight check: 不要假设本次 `git add` 完全失败或完全成功；立即运行 `git diff --cached --name-status` 和 `git status --short --branch --untracked-files=all`，确认哪些文件已经部分进入暂存区，哪些 ignored 文件仍未暂存。
- Blocker: ignored 路径包含当前任务必须保留的任务记录、验证证据或正式测试，但尚未精确确认归属；暂存区已经混入临时目录、运行日志、PID、秘密文件或无法归属产物时必须停止。
- Verification: 对确需提交且被忽略规则挡住的任务记录使用 `git add -f -- <exact-files>`，随后复跑 `git diff --cached --name-status`、`git diff --cached --check` 和排除项扫描，确认暂存区只包含授权范围。
- Forbidden action: 禁止看到 ignored 提示后直接继续 `git commit`；禁止用更宽的 `git add -f -A` 把 ignored 临时产物一起带入；禁止为了清理暂存区回滚或删除工作区内容。
- Evidence: `doc/tasks/20260830-commit-current-code-push/execution-log.md`，批量暂存当前代码时旧任务目录被 `.gitignore` 提示拦截但其它文件已部分暂存，随后先复核 staged 清单、排除 `.pytest-temp/` 和 `LOG_FILE_IS_UNDEFINED`，再对本任务记录单独使用精确 `git add -f`。

### 批量暂存脚本被拦截时的显式路径门禁

- Trigger: 准备提交大量前后端、文档和证据文件，复杂 PowerShell 脚本或 `pathspec-from-file` 暂存命令被 Codex/终端策略拦截。
- Preflight check: 不继续扩大脚本权限；改用明确目录和文件路径分批 `git add -- <paths>`，随后用 `git restore --staged -- <paths>` 移出当前任务记录、`.pid`、`diff --check` 失败文件和明显临时产物。
- Blocker: 无法列出明确路径、暂存区混入当前任务收尾记录、PID、超大文件、敏感文件、`git diff --cached --check` 失败项，或提交后仍有同一源码文件持续被并行任务写入且无法稳定归属。
- Verification: 每批暂存后运行 `git diff --cached --name-status` 和 `git diff --cached --check`；每次提交后运行 `git status --short --branch` 与 `git diff --name-status`，直到只剩明确不可提交项或当前任务收尾文件。
- Forbidden action: 禁止因批量脚本被拦截就改用宽泛 `git add -A`；禁止为了通过 `diff --check` 修改无关任务证据文件或 PDF；禁止把 `.pid` 运行态文件混入提交。
- Evidence: `doc/tasks/20260802-commit-current-frontend-backend-code/execution-log.md`，批量 pathspec 暂存被策略拦截后改用显式路径、移出 PID 和 `diff --check` 失败证据文件，并对多轮提交后残余改动逐轮复扫提交。

### 提交后残余改动复扫门禁

- Trigger: 执行基线提交、实现提交或收尾提交后，准备继续下一步提交或推送前。
- Preflight check: 每次提交后立即运行 `git status --short --branch` 与 `git diff --name-status`，确认是否还有延迟保存、并行任务或新生成的源码/测试/文档改动。
- Blocker: 发现新的已修改源码、测试、任务文档或生成物且无法确认归属；发现新改动属于当前用户“全部提交”范围但尚未提交；发现不属于当前任务的并行目录将被 `git add -A` 混入。
- Verification: 对归属明确的残余改动单独暂存、提交并记录 commit hash；对并行任务目录保持未暂存并在任务日志说明未触碰原因。
- Forbidden action: 禁止只看最近一次 `git commit` 成功就直接推送；禁止在未复扫状态时使用宽泛 `git add -A`；禁止把提交后新出现的并行任务目录混入当前任务收尾提交。
- Evidence: `doc\tasks\20260727-commit-frontend-backend-code\execution-log.md`，提交前后端代码时两次提交后复扫分别发现前端 Runner 残余改动、后端批记录报表残余改动，并拆分提交保留边界。

### 脏工作区功能分支融合增量门禁

- Trigger: 在 `int_main` 或共享分支上融合远端功能分支，同时工作区存在并行未暂存改动、残余基线、或 `git diff HEAD..branch` 显示大量非本分支文件。
- Preflight check: 先用 `git merge-base HEAD <branch>` 取真实分叉点，再运行 `git diff --name-status "<merge-base>..<branch>"` 获取该分支实际增量；同时用 `git diff --name-only` 列出当前未暂存文件，只按两个列表的交集判断是否需要先基线提交或阻塞。
- Blocker: 实际增量与未暂存文件有同文件重叠且无法可靠区分 hunks、工作区存在未解决冲突、或待融合分支会删除/覆盖主线证据文件时必须停止并让用户决定。
- Verification: 任务日志记录 merge-base、实际增量文件列表、未暂存交集、merge commit hash、目标回归命令和最终 `git status --short --branch`。
- Forbidden action: 禁止只看 `git diff HEAD..branch` 的宽泛差异就误判分支会改动所有主线新增文件；禁止为继续融合而使用 `git add -A` 混入并行改动；禁止用 reset、checkout 或 rebase 清空脏工作区。
- Evidence: `doc/tasks/20260806-commit-frontend-backend-merge-int-main/execution-log.md`，融合 `origin/codex/replan-current-route-after-feedback` 前通过 merge-base 确认实际增量仅为排产服务、测试和经验文档，与并行残余无重叠后安全合并。

### 路径限定 stash 的共享索引快照门禁

- Trigger: 在共享主工作区已有其它任务 staged 变更时，准备使用 `git stash push -- <paths>` 或 `git stash push -u -- <paths>` 暂存待融合分支的少量重叠文件。
- Preflight check: 不得假设 pathspec 会限制 stash 提交中的索引快照；创建后立即用 `git diff --name-status 'stash@{0}^1' 'stash@{0}'` 审计 tracked 内容，并用 `git ls-tree -r --name-only 'stash@{0}^3'` 审计 untracked 内容，同时确认主工作区其它 staged 文件仍保留。
- Blocker: stash 包含其它任务文件、stash 身份或父提交无法确认、主工作区 staged 内容已被移除、或无法证明待融合分支已覆盖重叠语义时，必须保留 stash 并停止 pop/drop；优先改用干净集成 worktree 或明确文件补丁完成后续融合。
- Verification: 记录 stash 名称、tracked/untracked 文件审计、融合后目标路径状态和其它 staged 文件数量；只在 stash 内容完全属于当前任务且已被正式提交覆盖时才允许删除。
- Forbidden action: 禁止因为命令带 pathspec 就盲目 `git stash pop` 或 `git stash drop`；禁止用 stash 覆盖融合后的正式实现；禁止为了清理 stash 删除其中的并行任务快照。
- Evidence: `doc/tasks/20260810-dcc-project-code-assignment-scope/execution-log.md`，融合 DCC 分配范围修复时，路径限定 stash 仍包含共享主工作区其它 staged 索引快照，因此保留 stash 且未 pop/drop。

### GitHub 推送大文件门禁

- Trigger: 推送到 GitHub remote、处理 `GH001`、`Large files detected`、`pre-receive hook declined`、Git LFS 或历史大文件问题。
- Preflight check: 推送前扫描待推送历史中的对象大小，至少确认没有超过 GitHub 100 MB 限制的 blob；必要时检查敏感文件和发布 evidence 是否误入 Git 历史。
- Blocker: 扫描发现超过 100 MB 的 blob，或 `git push` 返回 `GH001: Large files detected` / `pre-receive hook declined`。
- Verification: 记录对象扫描结果、`git push origin <branch>` 退出码、以及推送后的 `git status --short --branch`。
- Forbidden action: 禁止未经用户明确授权就执行历史重写、Git LFS 迁移、快照分支替代、force push 或删除远端历史。
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md#2026-07-24-github-推送前历史大文件门禁`。

### GitHub HTTPS 443 本地代理门禁

- Trigger: `git push`、`git fetch`、`git ls-remote` 或 GitHub HTTPS remote 报 `Failed to connect to github.com port 443 via 127.0.0.1`、`Could not connect to server`、`Connection timed out`、`Recv failure: Connection was reset`。
- Preflight check: 先运行 `git config --show-origin --list | Select-String -Pattern 'proxy|127\.0\.0\.1|7890|insteadOf|http'`，不要只依赖窄正则，因为 `http.https://github.com.proxy` 这类 URL 级代理可能被漏掉；再运行 `Test-NetConnection 127.0.0.1 -Port <proxyPort>`、`Test-NetConnection github.com -Port 443`、`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer` 和 `/v ProxyEnable`。如果用户有 FlClash/Clash/VPN，再确认其配置端口、Windows 用户代理端口和实际监听端口一致。
- Blocker: Git 配置指向本地代理但代理端口未监听、GitHub HTTPS 直连 443 不通、代理客户端仅 helper 进程在线但核心未监听、或 SSH 443 可达但 GitHub 不接受当前 SSH key。
- Verification: `git ls-remote origin HEAD` 成功返回 HEAD；如果 Git 全局代理端口陈旧但 Windows 用户代理端口正在监听，可先用一次性 `git -c http.https://github.com.proxy=http://127.0.0.1:<actualPort> ls-remote origin HEAD` 验证，再用同样一次性 `-c` 推送；如果 Git URL 级代理端口未监听但 `Test-NetConnection github.com -Port 443` 直连通过且 Windows `ProxyEnable=0`，可用一次性 `git -c http.https://github.com.proxy= ...` 清空本次命令代理完成 `ls-remote/fetch`，不得修改全局配置；若改用 SSH 443，必须先用 `ssh -T -o BatchMode=yes git@ssh.github.com -p 443` 验证账号认证成功，再改 remote 或 pushurl。
- Forbidden action: 禁止把删除 Git proxy 当作修复，除非已证明 GitHub HTTPS 直连 443 可用；禁止静默切换到 SSH remote，除非当前 SSH key 已被 GitHub 接受；禁止把 helper 服务监听端口误当作 HTTP/SOCKS 代理端口。
- Evidence: `doc\tasks\20260731-git-443-push-fix\execution-log.md`，GitHub HTTPS 直连失败、Git 全局代理指向 `127.0.0.1:7890` 但 FlClash 核心未监听，SSH 443 网络可达但公钥未授权；`doc\tasks\20260804-approval-center-applicant-column\execution-log.md`，窄正则漏掉 URL 级 GitHub proxy，完整 config 发现 `7890` 陈旧、Windows 用户代理实际为 `8902` 且监听，使用一次性 `-c` 对齐代理后 push 成功。

## PowerShell 编排门禁

### PowerShell 命令编排

- Trigger: 需要在 PowerShell 中串联 Git、构建、测试、清理、SSH、MySQL、Node、Python 或多行命令。
- Preflight check: 明确 `workdir`、命令退出码、输入输出编码和敏感信息脱敏方式；串联命令用分行或分号。
- Blocker: 命令依赖未确认、路径未解析、退出码不可见、可能输出凭据、或需要中文 stdin/文件但未设计 UTF-8 路径。
- Verification: 每个关键命令记录退出码和必要摘要；中文文件写入后使用 UTF-8 方式重新读取。
- Forbidden action: 禁止使用 `&&`、默认编码 `Set-Content`/`Out-File` 写中文、吞掉错误、或记录密码/token/私钥。
- Evidence: `docs\powershell-encoding.md`、`doc\tasks\<task-id>\execution-log.md`。

### Docker sh -lc 单参数与迁移回读门禁

- Trigger: PowerShell 通过 `docker exec <container> sh -lc` 执行 MySQL 迁移、重定向 SQL 文件或使用容器内环境变量。
- Preflight check: 先把完整 shell 命令组装为一个字符串参数，再作为 `sh -lc` 的单一命令参数传入；不得让 PowerShell 把环境变量赋值、`mysql` 参数和重定向拆成多个位置参数。执行后必须回读目标列、索引或菜单行。
- Blocker: `sh -lc` 实际只执行了环境变量赋值、SQL 文件未生效、回读状态与迁移目标不一致，或命令输出可能泄露容器密钥时必须停止。
- Verification: 同时记录迁移退出码、目标 schema/数据回读和临时 SQL 文件删除结果；schema 变更回读 `information_schema` 或 `SHOW COLUMNS/INDEX`，菜单变更回读 `permission/path/component/type`。
- Forbidden action: 禁止用“命令返回 0”替代数据库状态证明；禁止在命令行展开或输出容器密码；禁止迁移未生效时继续重启并把旧库异常归因于业务代码。

### PowerShell 分号串联测试退出码门禁

- Trigger: 在 PowerShell 中用分号串联多个 Node、Python、Maven、pnpm 或静态合同测试命令。
- Preflight check: 每个会影响验收结论的测试命令必须单独执行，或在每条命令后检查 `$LASTEXITCODE` 并失败即停止。
- Blocker: 前一个测试输出断言失败、异常栈或非零退出码，但后续命令继续执行并让最终命令返回 0。
- Verification: 对目标测试逐条记录退出码；批量命令必须证明中间失败不会被最后一条 PASS 掩盖。
- Forbidden action: 禁止把 `cmd1; cmd2; cmd3` 的最终退出码 0 当作全部测试通过；禁止只引用最后一条 PASS 输出；禁止在 `pnpm/node` 测试后直接跟 `Remove-Item Env:\...` 等清理命令并用清理命令的 0 退出码覆盖测试失败。
- Evidence: `doc\tasks\20260728-edhr-detail-assist-preview-switch\execution-log.md`，相邻静态合同串联运行时 `edhr-assist-fill-mode-static.spec.js` 断言失败被后续 PASS 命令掩盖，改为单独复跑后正确记录失败。
- Evidence: `doc\tasks\20260829-registration-certificate-upload-production-fields\execution-log.md`，注册证上传审批 E2E 首次用 `$env:REG_CERT_E2E_REQUEST_ID='102'; pnpm exec node ...; Remove-Item Env:\REG_CERT_E2E_REQUEST_ID` 串联运行，注册部经理登录失败被最后环境变量清理命令掩盖为退出码 0；改为保存 `$LASTEXITCODE`、清理环境变量后 `exit $approvalExit`，后续请求 103 审批脚本正确返回失败码 1。

### 任务状态脚本串行写入门禁

- Trigger: 同一任务内运行会修改 `task-state.json`、`task.md`、`test-report.md` 或其它状态文件的脚本，例如 `record_phase_review.py`、`record_test_review.py`、`check_completion.py --apply`、cleanup apply，尤其准备并行执行以节省时间时。
- Preflight check: 先区分只读校验命令和状态写入命令；只读命令可以并行，任何会写同一状态文件的命令必须顺序执行。每次状态写入后立即运行 `render_task_status.py` 或等价只读状态检查，确认阶段状态、整体状态、`test_status` 和 `blocking_prereqs` 未被覆盖。
- Blocker: 并行状态写入后出现阶段状态回退、整体状态与阶段状态不一致、`blocking_prereqs` 丢失、`test_status` 被旧值覆盖，或无法确认哪个命令最后写入状态文件时必须停止并按预期状态顺序重放写入脚本。
- Verification: 记录顺序重放命令、重放后的 `render_task_status.py` 输出、结构 validator PASS 和 `git diff --check`；必要时在执行日志中说明并行写入造成的覆盖风险已修正。
- Forbidden action: 禁止把多个状态写入脚本放进 `multi_tool_use.parallel`、PowerShell background job 或同一异步批次；禁止只看单个写入脚本成功输出就跳过最终状态渲染；禁止手改 JSON 掩盖 race，除非脚本不可用且已记录阻塞原因。
- Evidence: `doc/tasks/20260805-production-leader-process-config-unification/execution-log.md`，P4 阻塞记录中并行运行 `record_phase_review.py` 与 `record_test_review.py` 后 P4 阶段状态被旧快照覆盖为 `pending`，顺序重跑阶段状态脚本并复核 `render_task_status.py` 后恢复为 `blocked`。

### Codex 文件 ACL 受限写入门禁

- Trigger: `apply_patch`、Node、Python 或普通 PowerShell 对已存在源码/测试/任务文档返回 `apply deny-read ACLs`，但任务必须继续进行受控修改或验证。
- Preflight check: 先确认目标文件属于当前任务范围，并优先用 `rg`/`git diff -- <path>` 读取最小片段；若必须提升权限，命令必须限定到明确文件和单一验证命令。
- Blocker: 无法确认目标文件归属、需要修改并发任务文件、提升命令可能触碰任务外路径、或写入后无法用静态合同/类型检查验证时，停止并报告。
- Verification: 写入后立即执行目标片段搜索、`git diff -- <path>`、相关静态测试或类型检查，并在任务日志记录 ACL 原因、提升范围和验证结果。
- Forbidden action: 禁止因 ACL 拦截改用宽泛脚本批量扫描/重写目录；禁止跳过 diff 与测试直接宣称完成。
- Evidence: `doc\tasks\20260725-codex-test-method-target-items\execution-log.md`，前端测试管理页面方法项/目标项展示改造遇到 ACL 后采用限定文件 UTF-8 写入并通过静态测试与类型检查。
### Codex Windows PowerShell 精确前缀门禁

- Trigger: Codex 普通 PowerShell、Node REPL 或 apply_patch 因 Windows helper ACL 报错，但需要继续创建任务目录、写任务文档或更新 AGENTS.md。
- Preflight check: 优先使用已批准精确前缀 C:\windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command ...，并显式设置 workdir=<主程序根目录>；脚本内容用单引号保护，避免外层 shell 展开变量，不额外夹 -NoProfile。
- Blocker: 精确前缀仍失败、目标路径不属于当前任务、需要触碰并发任务文件、或写入后无法 UTF-8 回读时停止，不得随机换 shell。
- Verification: 先做 smoke：创建任务目录临时文件、显式 UTF-8 写入、UTF-8 回读、删除并确认无残留；正式写入后复核目标 baseline 或片段出现次数。
- Forbidden action: 禁止把 ACL/helper 故障误写成业务代码失败；禁止用默认编码写中文文档；禁止在未指定 workdir 时操作项目文件。
- Evidence: doc/tasks/20260821-stable-tool-chain-agents-baseline/execution-log.md。
### PowerShell 命令文本管道字符门禁

- Trigger: 在 PowerShell 命令参数、字符串替换、TypeScript 类型联合、正则或 Markdown 内容中需要出现字面 `|`、`||`、尖括号、中文或多行文本，并且命令会通过 Codex sandbox/approval 执行。
- Preflight check: 不要把包含字面 `|` 的长脚本直接放进命令字符串；先改用 `apply_patch`，若 ACL 阻断，再用 `[char]124` 或占位符在 PowerShell 运行时组装目标文本，并在写入前后检查文件长度与 `git diff -- <path>`。不要用 `-replace` 拼接 `` `r`n`` 写源码 import 或测试文件；这类写法容易把反引号序列按字面写入文件。
- Blocker: `apply_patch` 或 PowerShell 写入出现 ACL、timeout、文件长度变 0、BOM/编码漂移、或 diff 显示超出目标行的变化时，必须立即停止后续写入并先从 Git/source worktree 恢复文件。
- Verification: 写入后运行 `Get-Item <path> | Select-Object Length`、目标片段只读检查、`git diff -- <path>`、相关类型检查或静态合同，并把恢复证据写入 `doc\tasks\<task-id>\execution-log.md`。
- Forbidden action: 禁止在未确认 diff 和文件长度前继续提交；禁止用默认编码 `Set-Content`/`Out-File` 写中文或源码；禁止把工具截断、反引号字面量、BOM 漂移造成的文件异常当成正常业务改动。
- Evidence: `doc\tasks\merge-jiluben-residual-20260725\execution-log.md`，`BatchRecordCellRulesConfirmDialog.vue` 一次 ACL 后 PowerShell 替换超时截断并恢复；`doc\tasks\20260726-route-start-batch-record-attachments\execution-log.md`，测试 import 追加时 `` `r`n`` 被写成字面量，改回 `apply_patch` 并复跑 Maven 通过。

### PowerShell UTF-8 无 BOM 脚本执行门禁

- Trigger: 通过 `apply_patch` 生成含中文文件名、中文工作表名、中文参数或中文业务文本的 `.ps1` 脚本，并准备在 Windows PowerShell 5.1 或未确认版本的 PowerShell 中执行。
- Preflight check: 优先使用 `pwsh -NoProfile -ExecutionPolicy Bypass -File <script.ps1>` 执行 UTF-8 无 BOM 脚本；如果必须使用 Windows PowerShell 5.1，脚本文件必须带 BOM 或改为 ASCII 脚本加 UTF-8 数据文件，并在执行前用 UTF-8 方式回读关键中文参数。
- Blocker: 输出出现 mojibake、中文文件名中的 `.xlsx` 等扩展名被破坏、外部工具报不支持的文件类型、或中文 sheet/cell 参数被写空时，必须停止并改用 UTF-8 安全执行路径，不得继续沿用损坏产物。
- Verification: 记录失败命令、改用 `pwsh` 或 UTF-8 安全路径后的命令、关键中文文件名/路径回读结果，以及最终目标文件的结构化校验。
- Forbidden action: 禁止把 Windows PowerShell 5.1 对 UTF-8 无 BOM 脚本的乱码输出当作正常工具失败；禁止发现乱码后继续生成 Office、JSON、SQL 或任务证据。
- Evidence: `doc/tasks/20260819-dcc-windchill-comparison-excel/execution-log.md`，首次用 `powershell -File` 执行含中文 `.xlsx` 文件名的脚本时文件名变成 mojibake 且 officecli 误判扩展名，改用 `pwsh -File` 后工作簿生成成功。

### OfficeCLI XLSX 导入后内容复核门禁

- Trigger: 使用 `officecli import`、TSV/CSV 或批处理生成 `.xlsx`，特别是含中文工作表名、中文表头或已预置格式的 Excel 交付物。
- Preflight check: 导入命令返回成功后，必须立即用 `officecli get <file> '/<sheet>/A1:<end>' --json` 或 `officecli view <file> text` 复核关键表头和前几行真实 cell text；不能只看 `Imported N rows x M cols`、`outline` 行列数或 `validate` 结果。
- Blocker: `outline` 显示行列存在但 `get`/`view text` 为空、单元格仍为 `empty=true`，或 HTML 预览没有业务内容时，必须停止并重写单元格值；不得把空工作簿交付给用户。若已对同一范围执行 `add table`，不得再对该范围设置 sheet `autoFilter`；表格自带筛选，重复设置会触发 OfficeCLI 原子回滚，必须去掉重复筛选后重建或重跑格式批处理。若 `officecli validate` 因 WPS 表格自定义属性 `etc:filterBottomFollowUsedRange` 报 schema error，必须确认业务内容和表格 `ref` 后用 raw-set 替换该 `autoFilter` 节点为标准 `ref`，不得把校验失败的 xlsx 交付。
- Verification: 记录写入方式、关键单元格 `get` 输出、`officecli view issues`、`officecli validate`、错误单元格查询和 HTML 预览占位符检查；必要时用 `officecli batch` 对 TSV/CSV 逐单元格写值后再次复核；若处理过 WPS 自定义属性，记录 raw-set 前后的 table XML 片段和 validate PASS。
- Forbidden action: 禁止把 OfficeCLI import 成功消息、结构验证通过或格式存在当作内容已写入；禁止跳过首行/样例行读取；禁止在发现空值后只修样式不修数据。
- Evidence: `doc/tasks/20260819-iso13485-electronic-system-gap-analysis/execution-log.md`，ISO13485 差距分析工作簿首次显示 18x9/5x3 且 validate 通过，但 `view text` 与 `get` 证实单元格为空；改用 UTF-8 TSV 读取并 `officecli batch` 写入 177 个单元格后，表头、前两行、评分说明和 HTML 预览均复核通过。
- Evidence: `doc/tasks/20260827-edhr-customer-requirement-excel/execution-log.md`，客户需求 Excel 导出完成后用 `outline`、`view text`、`get`、`issues`、`validate` 和 `html` 复核，确认导出的 `.xlsx` 不是空工作簿。
- Evidence: `doc/tasks/edhr-requirements-classification-20260827/execution-log.md`，eDHR 用户需求分类工作簿写入后，`validate` 因 WPS `etc:filterBottomFollowUsedRange` 自定义属性失败；确认表格范围为 `A1:F41` 后用 raw-set 替换 `/xl/tables/table1.xml` 的 `autoFilter` 节点，复跑 `validate` 和 `view issues` 均通过。

### PowerShell Maven -D 参数引号门禁

- Trigger: 在 PowerShell 中运行 Maven 且参数包含带点属性名或方法选择符的 `-D`，例如 `-Dsurefire.failIfNoSpecifiedTests=false`、`-Dtest=ClassName#methodName`。
- Preflight check: 将每个 Maven `-D...` 参数整体加引号，单引号或双引号均可，例如 `'-Dtest=CodexTestCaseServiceImplTest'`、`"-Dtest=MesTeamLeaderActiveOrderSimulationServiceTest#numericSimulationParameterTextShouldUseGeneratedValueInsteadOfStandardRange"` 与 `'-Dsurefire.failIfNoSpecifiedTests=false'`；多模块目标测试继续保留 `-pl <module> -am`。不要把 PowerShell `--%` 与带引号的 `'-D...'` 同用，否则引号会原样传给 Maven 并触发 `Unknown lifecycle phase "'-D...'"`。
- Blocker: Maven 报 `Unknown lifecycle phase ".<property>=..."`、未进入期望 Surefire 目标测试，或未加引号命令疑似造成 testCompile 误报时，必须先按 PowerShell 参数解析问题复跑，不得直接归因于 Java 代码、Mapper 缺失或业务逻辑。
- Verification: 复跑加引号后的 Maven 命令，记录原失败与复跑 PASS、Surefire 实际执行的测试类/方法数量、Failures/Errors/Skipped 摘要；若上游 reactor 模块不含目标测试类，同时记录 `surefire.failIfNoSpecifiedTests=false` 的依据。
- Forbidden action: 禁止把 PowerShell 参数拆分或 `#` 注释截断误判为产品编译失败；禁止移除 `-am`、跳过目标 JUnit 或改成更宽测试作为绕过。
- Evidence: `doc\tasks\20260726-codex-test-case-project-column\execution-log.md`，目标 JUnit 首次因 PowerShell 拆分 `-Dsurefire.failIfNoSpecifiedTests=false` 失败，整体加引号后通过；`doc\tasks\20260726-work-order-field-cell-link\execution-log.md`，目标 MES JUnit 需同时整体加引号 `"-Dtest=MesProBatchRecordCellLinkServiceImplTest,MesProBatchRecordCellLinkSchemaTest"` 与 `"-Dsurefire.failIfNoSpecifiedTests=false"`，并保留 `-am` 编译依赖模块源码；`doc\tasks\20260830-system-user-generic-account-governance\execution-log.md`，System 用户服务目标测试首次因未引用 `-Dsurefire.failIfNoSpecifiedTests=false` 被拆成 Maven lifecycle phase，改用单引号包裹 `'-Dtest=AdminUserServiceImplTest'` 与 `'-Dsurefire.failIfNoSpecifiedTests=false'` 后进入真实 RED/GREEN；`doc/tasks/20260906-mes-testcompile-replenishment-mapper-blocker/execution-log.md`，Stage1 参数定向 Java 测试中未加引号的 `-Dtest=...#...` 造成误判，加引号后目标测试执行 1 个用例并 PASS；`doc/tasks/bulk-clear-production-test-data/execution-log.md`，MES 编译命令中 `--%` 与 `'-DskipTests'` 同用导致 Maven 把带引号参数当 lifecycle phase，移除 `--%` 后同命令 compile PASS。

### Maven 编译结论与行为测试失败分层门禁

- Trigger: 增量 `package` 显示 `BUILD SUCCESS`，但工作区存在大量源码改动、模块显示 `Nothing to compile`，或 clean reactor 在某个上游模块的 Surefire 行为测试阶段失败。
- Preflight check: 先用受影响模块的 clean reactor 强制重编生产源码和测试源码，再用同一 reactor 的 `-DskipTests` 继续验证后续模块；分别记录 javac/testCompile、Surefire 和 repackage 阶段，不把测试失败倒推成编译失败。
- Blocker: clean 后出现 javac/testCompile 错误才判定为编译阻塞；若生产/测试编译已通过、仅行为测试断言失败，则保持编译结论独立，并按失败模块另立行为回归任务。
- Verification: 主应用执行 `mvn -pl yudao-server -am "-DskipTests" package`；受影响模块执行 `mvn -pl <module> -am clean test` 或同一 clean 状态下的 `-DskipTests`；目标合同测试必须进入 Surefire 并记录实际测试数。
- Forbidden action: 禁止以增量 `Nothing to compile` 作为源码已验证的唯一证据，禁止把 `Surefire` 行为失败写成 javac RED，禁止为绕过行为失败使用 `maven.test.skip` 或修改无关测试。
- Evidence: `doc/tasks/20260826-fix-backend-compile-errors/execution-log.md`，clean reactor 编译通过、`yudao-module-infra` 行为测试另有 39 failures/1 error，随后主应用 clean `-DskipTests` 构建和 MES Stage 6 9/9 定向测试通过；`doc/tasks/20260829-bpm-formcenter-compile-fix/verification-report.md`，增量 BPM 和主应用打包先通过但存在 `Nothing to compile`，随后 BPM clean compile 与主应用 clean package 均通过，确认不是旧 target 掩盖。

### PowerShell JDBC/JShell 中文证据输出门禁

- Trigger: 在 PowerShell 中通过 JShell、JDBC 或 Java 小脚本读取 MySQL 中文业务数据，并把结果作为任务证据或迁移源核对。
- Preflight check: 终端输出即使设置 `$OutputEncoding` 与 `-J-Dfile.encoding=UTF-8` 仍可能出现中文乱码；关键证据必须由 Java 端用 `Files.writeString(..., StandardCharsets.UTF_8)` 写入任务文件，再用 `Get-Content -Encoding utf8` 或 Node UTF-8 API 读取复核。
- Blocker: 只看到终端乱码且未生成 UTF-8 文件证据时，不得据此编写中文迁移、判断业务名称或记录验收结论。
- Verification: 记录 UTF-8 证据文件路径、文件大小、关键中文字段复读结果，以及最终 SQL/任务文档未出现乱码。
- Forbidden action: 禁止把 JShell/PowerShell 乱码输出直接复制进 SQL、Markdown 或验收报告；禁止用乱码等价匹配替代正式中文业务键。
- Evidence: `doc/tasks/20260812-dcc-qa-idi-backend-persistence/execution-log.md`，IDI QA 固化中 JDBC 终端输出乱码，改为写入 `idi-db-source-dump.tsv` 与 `idi-db-apply-verification.txt` 后复核中文业务键。

### Maven 单模块陈旧依赖门禁

- Trigger: 在多模块 Maven 项目中只运行单模块目标测试，失败发生在测试启动前，错误指向上游模块 API、DTO、枚举、Mapper 或 service contract 缺失/签名不一致。
- Preflight check: 对依赖其它 reactor 模块的目标 JUnit 使用 `mvn -pl <module> -am "-Dtest=..." "-Dsurefire.failIfNoSpecifiedTests=false" test`；如果为了诊断先运行了不带 `-am` 的命令，必须确认失败是否来自本地仓库陈旧依赖而不是业务断言。
- Blocker: 不带 `-am` 的单模块命令在 testCompile/compile 阶段失败且未进入 Surefire 时，不得把它记录为业务 RED/GREEN，也不得缩小测试范围绕过上游依赖编译。
- Verification: 使用带 `-am` 的 reactor 命令复跑，确认目标测试进入 Surefire 且 PASS/FAIL 反映真实业务行为；任务日志记录原单模块失败原因和最终 reactor 验证命令。
- Forbidden action: 禁止把本地 `.m2` 陈旧产物导致的编译失败误判为产品逻辑失败；禁止删除 `-am` 来节省时间后宣称目标 JUnit 已验证；禁止用旧 surefire 报告冒充当前命令结果。
- Evidence: `doc\tasks\20260806-schedule-default-shift-hours\execution-log.md`，排产班次小时默认值修复中不带 `-am` 的单模块 Maven 因本地 `system` API 依赖陈旧在测试前失败，最终使用 `-pl yudao-module-mes -am` 的目标 JUnit 命令通过 4 个用例。
- Evidence: `doc\tasks\20260915-mes-bpm-interface-compile-fix\execution-log.md`，MES clean testCompile 因未带 `-am` 无法解析同仓 BPM 的 `FormActionExecutionContext`，而 `-pl yudao-module-mes -am clean test-compile` 重建 BPM 后 562 个 MES 测试源文件全部通过；后续接口定向测试 20/20 与 BPM 上下文回归 1/1 通过。

### Pytest 任务自有 basetemp 门禁

- Trigger: Windows 上 `pytest` 使用默认 `%TEMP%\pytest-of-<user>` 时 setup 阶段报 `PermissionError: [WinError 5]`，但测试本身尚未执行失败。
- Preflight check: 先确认失败发生在 pytest 临时目录创建阶段；复跑同一测试集时可使用当前任务自有目录 `--basetemp .pytest-tmp\<task-id>`，并把首次环境失败和复跑命令都写入任务日志。
- Blocker: 指定 basetemp 后仍失败、失败进入业务断言、或临时目录不属于当前任务可清理范围时，不得写成 GREEN。
- Verification: 记录同一测试集的最终 `passed` 数量，并在 cleanup candidates 中列出任务自有 `.pytest-tmp`。
- Forbidden action: 禁止把默认临时目录权限错误写成产品回归失败；禁止改用更少测试或删除系统临时目录来绕过。

### PowerShell 测试报告路径与本次执行证据

- 构造嵌套仓库和带完整类名、随机后缀的报告前，计算最长绝对路径；PowerShell 5.1 夹具使用短编号目录并显式校验路径预算。超限应在写入前说明前置条件，不静默换目录或吞掉文件异常。
- 同一测试须覆盖 PowerShell 5.1 与 7；保留首次路径失败和修复后的相同测试集结果，不把夹具初始化失败记为业务 RED，也不以单项通过替代组合失败。
- Surefire 报告归档可能混有历史 XML；总数仅统计本次日志实际运行的目标及对应报告。自动门禁使用本次唯一报告后缀，逐目标核对报告身份、执行数、失败和跳过数；零执行、缺报告及全跳过不得判通过。
- 脚本替身测试仅证明调用及结果处理；真实 Maven、覆盖扫描与生产审批必须分别验证，不能互相替代。

### yudao-server reactor unpack 测试门禁

- Trigger: `mvn -pl yudao-server -am ... test` 在 `maven-dependency-plugin:unpack` 阶段报 `Artifact has not been packaged yet`，且目标测试只是 server 模块自身静态/配置测试。
- Preflight check: 先确认同一命令已经让受影响兄弟模块到达 Surefire 并通过；再单独运行 `mvn -pl yudao-server "-Dtest=<目标类>" "-Dsurefire.failIfNoSpecifiedTests=false" test`，让 yudao-server 使用已存在的正式 report jar 进入自身 Surefire。
- Blocker: 单独 server 命令仍无法进入 Surefire、目标测试依赖当前兄弟模块未安装的新接口、或失败来自业务断言时，不得把 reactor unpack 阻断降级为 PASS。
- Verification: 任务日志同时记录 reactor 命令的 DCC/MES Surefire 结果、unpack 阻断摘要、单独 server 目标测试计数和最终结果。
- Forbidden action: 禁止跳过 yudao-server 目标测试、关闭插件执行或把 `-am` reactor unpack 的生命周期阻断写成业务失败。

### Maven 同模块 target/classes 陈旧门禁

- Trigger: 已修改当前模块 main 源码的方法签名、构造器参数、新增 mapper 或 mapper 默认方法，但 `mvn -pl <module> -am "-Dtest=..." test` 在 testCompile / Surefire 阶段仍报旧签名、旧构造器、`ClassNotFoundException` 缺少刚新增 mapper class，或“找不到刚新增的方法”，且日志显示 main `compile` 为 `Nothing to compile - all classes are up to date`。
- Preflight check: 先确认生产源码确实包含新签名，再只对当前目标模块运行 `mvn -pl <module> clean test "-Dtest=..." "-Dsurefire.failIfNoSpecifiedTests=false"`；不得清理无关模块 target。
- Preflight check: 若目标测试已进入 Surefire 但异常行为与当前源码明显不一致，必须检查 `target/test-classes` 是否残留与 `target/classes` 同路径的生产 `.class`；Surefire 会优先加载测试输出目录，旧生产类会覆盖当前正式编译结果。确认污染后优先精确清除重复生产类；若安全策略或并发写入不允许精确删除，则只对当前模块运行标准 `mvn clean` 并重新验证。
- Blocker: 当前模块 `clean` 后仍看见旧签名、`target` 删除失败、或存在并行 Maven 写同一模块 target 时，必须停止并按目标目录异常门禁处理。
- Verification: 记录第一次未重编译或旧类覆盖的失败、缺失 class 的源码路径与 `target/classes` 检查结果、重复生产类计数、`clean test` 或当前模块强制重编译是否进入 Surefire、目标测试数量和 PASS/FAIL。
- Forbidden action: 禁止把同模块陈旧 class 的 testCompile 失败当成业务失败；禁止把 `target/test-classes` 旧生产类覆盖导致的 Surefire 失败当成当前源码缺陷；禁止靠修改测试绕过旧 class；禁止用全仓清理替代当前模块最小 clean。
- Evidence: `doc\tasks\20260808-active-order-product-search\execution-log.md`，活跃订单产品搜索新增 `MesMdItemMapper` 构造器依赖和 mapper 方法后，`-pl yudao-module-mes -am` testCompile 仍看到旧 class；仅清理 `yudao-module-mes` 后 main 重新编译，43 个目标测试 PASS。`doc/tasks/20260811-process-pool-report-cell-link-config/execution-log.md`，报工字段映射验证中 Surefire 已进入目标测试但仍执行旧动态表单逻辑，最终定位 `target/test-classes` 残留 19 个生产类覆盖 `target/classes`；执行当前模块 `mvn clean` 后批记录链接全类 19/19 和相邻回归 15/15 PASS。`doc/tasks/20260811-dcc-qa-backend-persistence/execution-log.md`，DCC-QA 定向测试异常堆栈与当前源码不一致时再次确认同类污染，当前 MES 模块标准 `mvn clean` 后生产/测试编译及 19 个核心测试通过。`doc/tasks/20260826-edhr-pdf-signature-compliance/verification-report.md`，eDHR PDF 签名修复中 Surefire 上下文加载报缺少源码已存在的 `MesProBatchRecordVersionMigrationItemMapper.class`，确认 `target/classes` 缺 class 后等待同仓 Maven 释放，当前模块重编译恢复 class，复跑定向回归 14/14 PASS。

### Maven 静态源码合同工作目录门禁

- Trigger: JUnit 静态合同通过 `Files.readString`、`Path.of` 或 `readSource` 读取源码文件，且命令使用 `mvn -pl <module> -am "-Dtest=..." test`；失败文本包含 `NoSuchFileException`、重复模块路径如 `yudao-module-mes\yudao-module-mes\src`，或断言没有命中实际生产实现类。
- Preflight check: 静态合同读取源码前先按 Surefire 实际 `user.dir` 兼容模块根和仓库根两种工作目录；若被测职责已拆到独立 validator/service，不要只断言入口 service 源码字符串，需读取真正承载业务约束的实现类。
- Blocker: 测试在目标 Surefire 前因源码路径错误失败、合同断言落在错误类导致误判业务实现缺失、或为了通过测试把生产代码塞回入口类时必须停止并修正测试合同。
- Verification: 复跑原 Maven 命令，确认目标测试类已进入 Surefire 且 PASS；任务日志同时记录原路径/断言失败和修正后的目标类。
- Forbidden action: 禁止把 `NoSuchFileException` 写成业务 RED；禁止改 Maven 工作目录、复制源码到重复模块目录、或为了静态字符串断言破坏正式服务分层。
- Evidence: `doc/tasks/20260806-production-reporting-submit-implementation/execution-log.md`，报工提交参数明细实现中 `MesFrontlineRuntimeConfigProcessScopeTest` 首次在 Surefire 模块目录下读取 `yudao-module-mes\src` 失败，随后静态合同改为兼容模块根并读取 `MesFrontlineDeviceParameterValidatorImpl`，目标 Maven 2 个用例 PASS。

### Maven 目标目录文件系统异常门禁

- Trigger: Maven 编译或 `clean` 报 `target\classes` `NoSuchFileException`、同模块类大量缺失、或 `jcmd` 显示 `WinNTFileSystem.delete0` / `getBooleanAttributes0` 长时间停在目标目录。
- Preflight check: 先枚举同模块 Maven/Java 进程并确认是否属于当前任务；只停止当前任务或同一测试命令的陈旧 PID，停止后复查没有同模块 Maven 正在写 `target`，再尝试一次标准 `-pl <module> -am` 验证。
- Blocker: `mvn clean` 也卡在 `WinNTFileSystem.delete0`、目标目录无法安全删除、或同模块编译持续报 `target\classes` 缺失时，必须标记验证阻塞；不得继续叠加 Maven 命令、不得用单模块非 `-am` 编译失败替代业务 RED/GREEN。
- Verification: 记录 PID、`jcmd Thread.print` 关键栈、失败命令、是否停止了任务自有进程、以及后续标准 Maven 命令是否到达 Surefire。
- Forbidden action: 禁止强杀全部 Java/Maven、禁止删除无关模块 `target`、禁止在目标目录损坏时提交实现、禁止把环境编译失败写成业务测试失败。
- Evidence: `doc\tasks\20260803-dcc-docx-preview-system-exception\execution-log.md`，DCC 预览任务中同模块 Maven 卡在 `WinNTFileSystem.delete0`，后续 DCC 编译出现大量 `target\classes` `NoSuchFileException`，最终保持 blocked 未提交。
- Supplementary evidence: `doc/tasks/20260808-remove-pqc-extra-restrictions/verification-report.md`，一线 PQC 额外限制移除任务中，同一工作区多轮并发 Maven/`clean test`/`compile` 重建 `yudao-module-mes\target`，导致目标测试复跑在 testCompile 阶段出现大量 `target\classes` class 文件缺失；最终仅记录前端类型和静态合同 PASS，后端 Maven 动态验证保持 blocked，待无并发 Maven 窗口复跑。
- Supplementary evidence: `doc/tasks/20260808-frontline-pqc-requirement-alignment/execution-log.md`，一线 PQC 需求口径对齐任务中，目标 Maven 首轮在 testCompile 前报 `yudao-module-mes\target\classes` 大量 class 缺失；确认源文件存在、等待同模块 Maven 释放并运行 `mvn -pl yudao-module-mes -DskipTests compile` 重建主类后，复跑标准目标 JUnit 到达 Surefire 且 7 个测试 PASS。
- Supplementary evidence: `doc/tasks/20260908-data-integrity-remediation/execution-log.md`，数据完整性整改中，`-pl yudao-module-mes -am` 目标 JUnit 先后卡在 `IncrementalBuildHelper.beforeRebuildExecution`/`WinNTFileSystem.delete0` 与 `JavacFileManager`/`FSInfo.getJarClassPath`；任务仅中断自有 Maven，保留并行任务 Java，记录前端静态合同与后端源码合同 PASS，并把标准 Maven lifecycle 保持 blocked。
- Supplementary evidence: `doc/tasks/20260911-commit-frontend-backend/execution-log.md`，提交门禁中 DCC `mvn clean` 因另一 Maven PID 正在写同一模块 target 而无法删除 `target/classes`；先只读确认 PID 与命令行，等待其自然退出，不强杀并行任务，再重跑同一 clean 定向命令取得 PASS。

### Maven javac/Lombok class 写入长时间运行门禁

- Trigger: Maven 目标测试或编译长时间无 surefire 报告，`jcmd <pid> Thread.print` 显示主线程在 `java.io.FileDescriptor.close0`、`lombok.core.PostCompiler$1.close`、`ClassWriter.writeClass`、`JavaCompiler.generate/compile`，但仍处于 `RUNNABLE`。
- Preflight check: 先枚举同一 `maven.multiModuleProjectDirectory` 的 Maven/Java 进程，区分当前任务 PID 与并行任务 PID；不要在同一模块 `target` 上继续叠加 Maven。若当前任务 PID 已超过命令超时且无 surefire 报告，只停止当前任务 PID，并记录未触碰的并行 PID。
- Blocker: 同仓并行 Maven 仍写同一 `target`、目标测试没有生成 surefire、或标准 `-pl <module> -am` 编译仍长时间停在 javac/Lombok 写 class 阶段时，必须把验证标记为 blocked；不得宣称 JUnit 通过。
- Verification: 记录目标命令、超时秒数、PID、`jcmd` 关键栈、已停止的任务自有 PID、未停止的并行 PID、是否生成目标 surefire，以及后续释放并行 Maven 后的复跑结果。
- Forbidden action: 禁止把 `RUNNABLE` 状态误判为业务测试失败；禁止强杀并行任务 Maven；禁止在未释放同仓 Maven 时提交实现或继续跑更多 Maven；禁止用旧 surefire 报告冒充本次目标命令结果。
- Evidence: `doc\tasks\20260805-role-matrix-code-repair\execution-log.md`，AC-M22 放行预检修复中目标 Maven 多次停在 javac/Lombok 写 class 阶段，本任务仅停止自有超时 PID，保留同仓并行 Maven；并行阻塞释放后复跑标准 `-pl ... -am` 目标 JUnit 并以 Surefire PASS 作为最终 GREEN。
- Supplementary evidence: 若必须在 Maven 阻塞时证明 RED/GREEN，可用 JUnit Console 或“显式 javac 参数文件编译目标测试类 + `mvn ... surefire:test`”运行任务目标测试，但只能记录为补充证据；必须把 classpath 隔离清楚（旧实现 RED、新实现 GREEN）、同时保留标准 Maven lifecycle 为 blocked，禁止把该补充结果写成完整 Maven lifecycle 通过。
- Supplementary evidence: `doc/tasks/20260826-edhr-pdf-signature-compliance/verification-report.md`，eDHR PDF 签名修复中标准 `-pl yudao-module-mes -am` 目标测试被无关 testCompile 失败阻塞且一次 Maven 主编译触发 JVM native memory OOM；在主代码 `compile` PASS 后，用 `dependency:build-classpath` 生成 classpath、显式 javac 参数文件只编译 `ExecutionArchiveRendererTest`，再执行 `mvn -pl yudao-module-mes -Dtest=ExecutionArchiveRendererTest surefire:test` 获得 11/11 PASS，并继续把标准 lifecycle 记录为 blocked。

### PowerShell Maven 心跳包装器门禁

- Trigger: Maven `compile/test/package` 在 javac、testCompile、Surefire 启动或 repackage 阶段长时间无输出，导致 Codex 工具会话断开、但命令本身可能仍在运行。
- Preflight check: 首选前台执行并保留 Maven 原始输出；若需要避免空输出断链，可用 `System.Diagnostics.Process` 前台包装 Maven 绝对路径，并每 15 秒打印一次心跳。不要用 PowerShell 异步 `OutputDataReceived` 脚本块写控制台，容易因无 Runspace 崩溃并留下孤儿 Maven。
- Blocker: 出现重复 Maven PID、父 PowerShell 已崩溃但子 `mvn.cmd/java.exe` 仍在跑、或同模块存在非当前任务 Maven 写同一 `target` 时，必须先归属 PID；只停止当前任务自有重复进程，不得强杀并行任务或运行态 Java。
- Verification: 记录 Maven 绝对路径、PID、心跳区间、重复进程处置、最终 `BUILD SUCCESS/FAILURE` 和目标 Surefire 摘要；旧 surefire 报告只能作为历史证据，不能代替本次命令结果。
- Forbidden action: 禁止因会话断开就宣称 Maven 失败或通过；禁止继续叠加多个同模块 Maven；禁止把 PowerShell 包装器异常写成业务 RED。
- Evidence: `doc/tasks/20260901-sync-registration-change-mvp-to-main/execution-log.md`，注册证变更审批同步验证中，异步输出包装器触发 Runspace 崩溃并留下重复 Maven，最终仅停止本任务重复 PID，使用简单前台心跳包装器取得目标后端测试 PASS。

### Windows Maven 页面文件不足门禁

- Trigger: Maven 编译或测试报 JVM native memory allocation / `G1 virtual space` / Windows `页面文件太小，无法完成操作`，或同仓存在多个并发 Maven/Java 编译测试进程且工作集持续增长。
- Preflight check: 先用 `Get-Process -Name java,mvn -ErrorAction SilentlyContinue` 识别当前任务 PID、同仓并发 Maven PID 和常驻运行态；只停止当前任务启动且已超时/失控的 PID，不停止其它任务或运行态进程。
- Blocker: 页面文件不足、并发 Maven 持续占用内存、或低内存 `MAVEN_OPTS` 重试仍超时时，必须把目标 JUnit 标记为环境阻塞；不得继续叠加 Maven 重试、不得把静态检查写成 JUnit PASS、不得强杀全部 Java 进程腾内存。
- Verification: 记录原 Maven 命令、内存失败摘要、低内存重试命令、停止的任务自有 PID、保留的其它 PID，以及后续需要重跑的精确测试命令。
- Forbidden action: 禁止用更小测试范围冒充目标验证通过；禁止在未达到 Surefire 测试结果时宣称业务 GREEN；禁止因为环境阻塞而提交未记录的验证缺口。
- Evidence: `doc\tasks\20260805-ac-m19-deterministic-backfill\verification-report.md`，AC-M19 聚合回填修复中目标 Maven 首次因页面文件不足失败，低内存重试超时，仅停止本任务 PID 55008 并记录剩余阻塞。
- Evidence: `doc/tasks/20260805-ac-m20-pqc-review-fix/execution-log.md`，AC-M20 PQC 复核修复中，标准 Maven 先因 JVM native memory/pagefile 失败，低内存参数后仍长时间处于 Lombok/Javac 编译且并发 Java 任务较多，最终停止本任务 Maven PID 并保持后端 JUnit blocked，待资源释放后复跑标准 Maven 取得 GREEN。
- Evidence: `doc/tasks/20260826-edhr-pdf-signature-compliance/verification-report.md`，eDHR PDF 签名修复中一次 `mvn -pl yudao-module-mes -am ... test` 在主编译阶段报 JVM native memory allocation failure；后续仅记录窄范围补充验证 PASS，标准 lifecycle 仍保持 blocked。
## 执行顺序

### 主机缓存删除多次复核门禁

- 触发：用户授权清理主机缓存，尤其要求避免大范围误删或排除某应用数据。
- 规则：先固定绝对路径白名单和排除项，再保存逐文件路径、字节、修改时间与清单指纹；删除前再次核对路径祖先无 reparse point、文件仍在白名单且未变化。通配符只用于只读筛选，删除命令仅用 LiteralPath 普通文件，不递归删除目录。
- 运行依赖不能仅凭 cache 目录名判可删除；用户后续排除某应用时，连该应用的运行环境、旧安装残留、日志和崩溃转储都必须排除。
- 占用、修改、目录链接和权限异常须明确保留或阻塞；重复个人资料须核对内容指纹并保留另一份。
- 安全策略若拒绝删除或 WhatIf，不得改用脚本 Apply、其它 shell/语言/工具规避；记录具体拒绝和实际零删除，不把预览字节当作已释放空间。
- 验证：逐文件结果和卷可用空间分别记录；运行中的应用会再生成缓存，不能把外部变化算作本任务删除量。

1. 阶段 1：任务提交/推送预检
   必查项: 当前分支、remote、工作区脏状态、staged 文件清单、用户授权边界。
   推荐命令: `git status --short --branch`、`git branch --show-current`、`git remote -v`。
   Fail Fast: 缺 Git 仓库、缺 `origin`、分支错误、发现无法归属的敏感文件。
   必须记录: 分支、remote、脏文件摘要、是否需要基线提交。

2. 阶段 2：基线提交
   必查项: 当前任务文件不得混入基线；所有既有脏改动必须可追踪。
   推荐命令: `git diff --cached --name-status`、`git status --short`、`git diff --name-status`、`git show --name-status --oneline -1`。
   Fail Fast: 无法安全分离当前任务文件、存在冲突、存在秘密或大文件风险。
   必须记录: 基线提交 hash、文件清单和提交后残余改动复扫结果。

3. 阶段 3：任务提交与推送
   必查项: 当前任务实现、收尾记录、经验沉淀状态、GitHub 大文件门禁。
   推荐命令: `git diff --check`、对象大小扫描命令、`git push origin <branch>`、`git status --short --branch`。
   Fail Fast: verification 未通过、推送被拒、仍然 ahead、或缺凭据/网络。
   必须记录: 实现提交 hash、收尾提交 hash、推送结果和最终状态。

### 重启后融合状态复核门禁

- Trigger: git merge --ff-only、git add 或 git commit 曾因 .git/index.lock 阻塞，随后电脑重启、终端重开或外部 Git 进程自然结束。
- Preflight check: 不要直接按旧 blocker 删除锁或重复合并；先只读运行 git worktree list --porcelain、git log --oneline --decorate -n <N>、git rev-parse <main> <integration> HEAD 和 git merge-base --is-ancestor <integration> <main>，确认目标提交是否已经被其它成功路径或 post-merge 流程带入主线。
- Blocker: 主线、集成分支和 HEAD 不一致，存在 MERGE_HEAD/rebase/cherry-pick 状态，index 非空，或任务增量与当前脏文件出现精确/目录前缀重叠时必须停止；不得用旧会话的阻塞状态继续操作。
- Verification: 若三者已经一致且 ancestry 通过，再运行 scripts\preflight\branch-runtime-port-guard.ps1，记录最终 HEAD、guard 输出和任务状态更新；如果仍需删除 stale lock，必须重新满足零字节、超过 60 秒且无活动 Git 进程的原门禁。
- Forbidden action: 禁止重启后跳过实际 HEAD 复核，禁止对可能已经完成的 fast-forward 再次合并、rebase、reset 或清理锁文件，禁止把旧 blocker 继续写成当前阻断。
- Evidence: doc/tasks/20260816-registration-certificate-full-business-delivery/execution-log.md，T10-C 首次融合被外部 Git index.lock 阻塞；重启后只读复核发现 int_main、集成分支和 HEAD 已同为目标提交，随后只更新收尾记录并运行端口 guard。

### PowerShell Maven -D 参数引用门禁

- Trigger: PowerShell 中运行 Maven 定向测试，参数包含 `-Dtest=...`、`-Dsurefire.failIfNoSpecifiedTests=false` 等带点号的系统属性。
- Preflight check: 用单引号包裹每个 `-D...` 参数，例如 `'-Dtest=FooTest'` 和 `'-Dsurefire.failIfNoSpecifiedTests=false'`，避免 PowerShell 把点号属性截断后让 Maven 收到伪 lifecycle phase。
- Blocker: Maven 报 `Unknown lifecycle phase ".failIfNoSpecifiedTests=false"` 或类似属性残片时，应记录为命令包装错误并立即用引用后的同一目标命令重跑；不得写成业务 RED/GREEN。
- Verification: 复跑引用后的标准 Maven 命令，必须到达 Surefire 并记录测试计数。
- Forbidden action: 禁止把未引用 `-D` 导致的 Maven 参数解析失败当作产品测试失败，禁止改 POM 或测试名绕过参数问题。
- Evidence: `doc/tasks/20260914-edhr-static-021-inventory-evidence-chain/execution-log.md`，EDHR-STATIC-021 首次未引用 `-Dsurefire.failIfNoSpecifiedTests=false` 被 PowerShell 截断，随后用单引号包裹 `-Dtest` 与 `-Dsurefire...` 后目标 Maven 进入 Surefire 并通过 19 个测试。

### 本机 Codex 历史清理门禁

- Trigger: 用户要求删除 Codex 已归档会话或清理本机历史以释放磁盘空间。
- Preflight check: 先核对运行中桌面后端的 ExecutablePath 与版本，不能默认全局 npm CLI 和桌面版本一致；只读核对归档索引、历史文件元数据、spawn 后代及 fork history_base 引用。迁移文件末尾 UUID 可能是 rollout ID，不能直接当稳定会话 ID。引用核验应遍历当前与旧版 rollout 文件，仅读取索引中的当前 rollout_path 会漏掉旧版历史引用；先用 session_meta 确认文件归属，再将 rollout ID 映射回稳定会话 ID。
- Safe strategy: 按明确授权冻结归档清单与未归档保护清单，优先用匹配版本的原生删除 API；有未归档引用的源历史必须保留。共享名称索引使用固定临时文件和进程内锁，多客户端删除存在竞争；出现名称索引冲突或 SQLite 锁竞争，应停止任务客户端的新请求并核查结果，不得显示默认成功。
- Verification: 分别核对桌面归档列表、索引、历史文件与受保护会话；删除文件字节数和卷空闲量分开报告，不把其他任务产生的空间变化算成本任务释放量。
- Evidence: `doc/tasks/20261008-codex-archived-sessions-cleanup/execution-log.md`，全局 CLI 0.147.0 与桌面 0.158.0-alpha.2.1 不一致，改用桌面配套二进制处理迁移历史；发现两条归档源历史被未归档会话引用。
