# Worktree Memory

> 路径约定：`docs/...` 相对本维护仓根目录；`IntRuoyiBackend/...`、`IntRuoyiFronted/...` 及其源码命令相对当次已验证配置确定的主程序根目录。不依赖盘符，不猜测源码目录。此文件沿用交接资料中的规则；当前用户授权和 AGENTS.md 优先。

## 归档前保存任务记录与跨会话归属

- 归档或清理 managed worktree 前，核对 Git 注册、附件归属及是否有原会话、分叉会话或子 Agent仍在使用同一目录；未完成的实现和验证不得按空闲目录清理。
- 源码快照只证明实际进入快照树的内容。先用 `git check-ignore` 和快照路径清单核对任务记录、验证日志及关键资源是否被忽略；必要记录须保存在任务外的明确持久位置并校验，不能假定源码快照包含它们。
- 恢复时记录快照对象、父提交、时间、文件清单及快照之后的未保存修改。任务分支仍指向基线不代表未提交实现已有备份，前端残留存在也不代表工作区可用。
- 分叉会话的附件未同步为归档状态时，原生恢复工具可能找不到目标。准确记录阻塞，不把失败改写为恢复完成；切换恢复路径遵守当前用户授权与项目规则，不重建旧基线来掩盖缺失。
- 恢复后重新冻结源码并运行相应验证；丢失日志只记录会话中的历史结果及来源，不重造 PASS 记录，不把旧快照的验证沿用到后续补丁。

## 取消隔离环境后的清理边界

- 用户取消隔离验证时，先撤回共享导入预约并停止仅归属本任务的写入；将恢复、构建和E2E改为取消，保留真实失败与未运行事实，不把取消当作验收通过。
- 清理清单分别覆盖checkout与端口登记、任务进程、专用Redis、数据库副本/用户、临时dump、对象存储副本/IAM及私有配置；只删任务路径和精确身份，保留原环境测试账号及共享服务。
- managed worktree优先通过Codex归档保存可恢复源码快照后清理，不把弃用checkout中的混合输入自动提交或合并主分支。路径确认不存在、任务记录与分支归档已处理后，使用同一端口登记mutex原子释放该任务槽位。
- 对象副本清理先全量核对精确version清单与retainUntil/hold；普通环境删除授权不代替解除hold的明确授权。有效COMPLIANCE保留期不绕过，不能用delete marker或只删IAM伪装底层对象已释放。

## 用户取消验证后融合

- 用户明确取消后续验证时，同步任务范围并保留已有失败、未运行和半成品事实，不以授权代替通过证据。
- 先停止任务内并行写入，再准备精确提交；主线未提交改动仍需保全，不能把“直接融合”解释为覆盖、丢弃或提交无关工作。

## Worktree 前端依赖与类型检查门禁

- Trigger: 附加 worktree 需要运行前端 `pnpm ts:check`、构建或静态检查，但该 worktree 是新 checkout 或未曾安装前端依赖。
- Preflight check: 先确认 `IntRuoyiFronted\pnpm-lock.yaml` 存在、`pnpm --version` 可用、`IntRuoyiFronted\node_modules\.bin\cross-env.cmd` 或对应脚本依赖存在；缺失时使用 `pnpm install --frozen-lockfile` 按锁文件补齐当前 worktree 依赖，再运行目标检查。
- Blocker: `pnpm install --frozen-lockfile` 失败、锁文件缺失、依赖脚本需要额外 approval 但目标检查依赖该脚本产物，或类型检查仍失败且无法区分是否当前任务引入时，必须停止并记录影响；不得改用 API-only、跳过类型检查或把缺依赖写成代码通过。
- Verification: 记录依赖安装命令退出码、`pnpm ts:check` 退出码、是否存在 build-script approval 警告及其影响；合并前再次确认 `node_modules` 为 ignored 产物且未进入提交清单。
- Forbidden action: 禁止提交 `node_modules`、禁止静默降级到只跑 `node --check` 替代类型检查、禁止把主工作区已有依赖目录复制到附加 worktree。
- Evidence: `doc/tasks/20260909-form-parser-json-editor-frontline-preview/execution-log.md`，`jiexi123` 新 worktree 首次 `pnpm ts:check` 失败于 `cross-env` 缺失，按锁文件执行 `pnpm install --frozen-lockfile` 后类型检查通过且 lockfile 未变；`doc/tasks/20260918-production-batch-record-json-publish-implementation/verification-report.md`，`20260918_gongyiluxian` worktree 首次因缺少 `node_modules/cross-env` 未进入 TypeScript 分析，按锁文件安装依赖后复跑进入类型分析，但暴露既有 `BatchExecutionListPage.vue` 导入缺失错误，任务按类型门禁阻塞记录而未静默降级。

- 跨盘加速依赖安装时，保留任务自有标准 `node_modules/.pnpm` 结构。只外置 virtual-store 可能破坏包内 require 的祖先目录解析，即使 frozen install exit0，Vite/ESLint仍可能缺模块；不得用 NODE_PATH、alias 或修改解析配置把该失败计为通过。
- 从任务自有物理SSD目录安装后用 junction 消费前，逐字节核对 manifest/lock/workspace 配置，并确认相对 file/link/workspace依赖、生命周期脚本和额外配置不会使复制少量配置文件丢失安装上下文；不满足即停止。安装、实际模块解析、定向验证、真实页面就绪分别记证据；保留中断/失败轮，收尾核对消费者已停止后再清理确切自有物理目录与链接。
## 同类需求 Worktree 复用门禁

- Trigger: 用户要求在 worktree 中继续一个业务功能，且 `D:\IntRuoyiWorktree\` 下可能已有同类分支或半成品分支。
- Preflight check: 新建前先用 `git worktree list`、分支名和 `doc/tasks/<task-id>` 语义检索同类 worktree；若已有同类分支包含目标代码、任务文档和验证证据，优先在该 worktree 继续，不要重复创建新分支。
- Blocker: 新建过程中被中断并留下 `locked initializing`、大量 staged deletion 或半 checkout 目录时，必须先确认路径属于当前任务且在 worktree 根目录内，再按 Git worktree 注册状态清理或改用既有同类 worktree；不得把半初始化目录当作可用工作区。
- Verification: 记录最终采用的 worktree 路径、分支、端口槽位和 `git status --short --branch`；若放弃新建的半成品，需要记录 Git 注册、物理目录和端口登记的后续清理状态。
- Forbidden action: 禁止在已有同类实现分支可复用时继续造重复分支；禁止直接递归删除仍有 Git 注册的 initializing worktree。

## Worktree 补丁路径归属门禁

- Trigger: 用户明确要求在某个附加 worktree（如 `TR2`）继续修复、验证或收尾，但当前 Codex/补丁工具默认工作区可能仍是主工作区。
- Preflight check: 写入前用目标 worktree 的 `git status --short --branch` 和 `Test-Path` 确认目标文件只存在于指定 worktree；使用补丁工具时优先写绝对路径，或在写后立刻复扫主工作区同路径是否误落新文件。
- Blocker: 目标路径不是用户指定 worktree、补丁误落主工作区且无法安全撤销、或主工作区同路径已有并行未跟踪/脏文件无法区分归属时必须停止。
- Verification: 写入后分别检查指定 worktree 与主工作区的同路径存在性和 `git status --short --branch`；若发生误落，先用精确补丁删除误落文件，再重新写入指定 worktree，并在任务日志记录无残留。
- Forbidden action: 禁止在用户指定 worktree 的任务中把主工作区误落文件继续当作任务产物；禁止用 `git add -A` 或整目录复制掩盖路径归属错误。

## Codex 临时 Worktree 提交迁移门禁

- Trigger: 当前工作区位于 `C:\Users\<user>\.codex\worktrees\...`、处于 detached HEAD，或切到任务分支后 `branch-runtime-port-guard.ps1` 报当前路径属于 `int_main` 但分支不是 `int_main`。
- Preflight check: 不在 C 盘临时 worktree 用 `--no-verify` 绕过提交钩子；先从最新 `int_main` 在 `D:\IntRuoyiWorktree\` 创建任务专属 worktree，运行 `reserve-worktree-slot.ps1` 登记 profile、slot、前后端端口，再迁移当前任务最小 diff。
- Blocker: C 盘临时 worktree 混有其它任务 dirty/untracked、主工作区 dirty、或新 worktree 未登记端口槽位时，只能记录阻断并保留现场；不得把无关 dirty 整体提交、stash、reset 或混入任务分支。
- Verification: 记录 C 盘 guard 失败摘要、D 盘 worktree 路径、分支、slot、`branch-runtime-port-guard.ps1` PASS、最小 diff 清单和后续 Maven/静态验证。
- Forbidden action: 禁止在 profile 不匹配的临时 worktree 上 `git commit --no-verify`，禁止为通过 closeout 把 C 盘混合 dirty 改动全量提交，禁止绕过 D 盘 worktree 根目录和端口登记规则。

## 运行时 smoke 进程归属与日志时间窗门禁

- 触发场景：验证需要启动后端端口，但目标端口已经被长期 runtime-control 服务监听，或共享日志包含多次启动记录。
- 经验规则：启动前用命令行、PID、创建时间和 runtime-control 标识确认进程归属；只停止本任务实际启动且可证明归属的 PID。为本次 smoke 使用独立日志目录，健康检查和启动成功判断只看本次启动时间窗，不能把历史 APPLICATION FAILED 当作当前结果，也不能把当前成功覆盖历史失败。
- 经验规则：已监听但 health 短暂失败时，先结合日志最新写入时间和 PID 归属判断是否仍在启动窗口，复测 health 后再决定是否重启；命令行可能包含 datasource password、token 等敏感参数，任务日志只记录脱敏摘要和归属证据，不复制原始秘密。
- 排查顺序：先记录端口监听和 PID，再请求 /actuator/health，随后按启动时间窗扫描 Started YudaoServerApplication、APPLICATION FAILED、Bean 缺失和结构化 blocker，最后停止自有 PID 并复扫端口；既有服务不在本任务范围时保留并记录。
- 禁止做法：禁止按端口盲杀其它任务服务、复用混杂历史日志宣称启动通过、用健康接口单点结果掩盖最新启动失败，或因前台等待而留下自有服务。

## Worktree 端口段与原子槽位门禁

- Trigger: 新建、登记、启动、提交或推送 `D:\IntRuoyiWorktree\` 下的 worktree；出现 `slot >= 101`、基准端口碰撞、重复活动槽位、重复活动端口、`No worktree port registry entry is registered`，或 `<主程序根目录>` 被识别为 `int_main_d`。
- Preflight check: 附加 worktree 创建后，在首次启动、提交、推送或运行 `branch-runtime-port-guard.ps1` 前运行 `scripts\runtime\reserve-worktree-slot.ps1`，由脚本在跨进程互斥锁内读取登记表并分配所属 profile 的最低空闲 `slot 1..100`；槽位 `1..19` 保持原映射，`20..30`、`31..40`、`41..50`、`51..60`、`61..70`、`71..80`、`81..90` 和 `91..100` 分别使用集中定义的八段扩展端口。随后运行 `show-branch-runtime.ps1` 或提交前钩子确认 profile、slot 和前后端端口。长期任务分支还必须先核对自身 guard/profile 合同与当前 `docs\branch-runtime-ports.md` 的槽位范围一致；若旧分支仍只接受旧槽位范围，应先以任务相关的独立 Git 变更同步守卫，再判断共享登记是否合法。
- Blocker: 槽位不在 `1..100`、登记端口不符合集中映射、计算端口命中任一 profile 基准端口、活动登记项复用 `profile/slot` 或前后端端口、基准工作区请求非零槽位、路径与 profile 无法唯一匹配、提交钩子提示缺少当前 worktree registry active entry，或目标分支 guard 合同落后于共享登记合同且尚未完成范围可证明的同步时必须 fail fast。
- Verification: `python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_branch_runtime_profile.py`、`pwsh -NoProfile -File scripts\preflight\branch-runtime-port-guard.ps1`、目标工作区 `show-branch-runtime.ps1` 输出，或 `reserve-worktree-slot.ps1 -AsJson` 返回当前路径、分支、profile、slot、frontendPort、backendPort 且后续 `git commit` 钩子通过。
- Forbidden action: 禁止手工猜测槽位、并发直接改写登记表、使用 `slot >= 101`、自行推算扩展端口、基准工作区借用 worktree 槽位、冲突时随机换端口或按分支名猜测歧义 profile；禁止为迁就旧分支守卫而删除或改写其它任务的合法登记，也禁止整体复制混有无关业务内容的提交来同步守卫。
- Evidence: `doc/tasks/20260726-harden-worktree-port-slot-allocation/verification-report.md`；`doc/tasks/20260803-pqc-equipment-standard-method-design/execution-log.md`，PQC 文档 worktree 未启动服务但提交钩子仍要求 registry，补跑 `reserve-worktree-slot.ps1` 登记 slot 15 后解除阻塞；`doc/tasks/20260815-expand-worktree-slots-30/verification-report.md`，保留既有 1–19 映射并用独立扩展段把容量扩至 30；`doc/tasks/20260814-production-release-flow-implementation/verification-report.md`，长期 PQC 分支的 v3 `1..19` 守卫拒绝共享登记中的 v4 合法 slot 20，任务保持阻塞且未修改并发登记。

## Worktree 重命名与端口登记原子同步门禁

- Trigger: 重命名 `D:\IntRuoyiWorktree\` 下已经具有活动端口登记项的 worktree，或要求只修改 worktree 显示名称和目录而保留原分支、slot 与端口。
- Preflight check: 先读取 `docs\worktree-restrictions.md`，逐个确认旧目录存在、目标目录不存在、目标绝对路径仍是固定 worktree 根目录的子路径；用 `git worktree list --porcelain`、目标分支和登记表旧路径唯一匹配每个活动项。执行时使用 `git worktree move` 更新 Git 元数据，并取得与 `reserve-worktree-slot.ps1` 相同的登记表 mutex，在同一受控操作中更新登记项 `name/path/updatedAt`；保留 `branch/profile/slot/frontendPort/backendPort/createdAt`。
- Blocker: 任一目标名已占用、旧目录或 Git 注册缺失、登记项按旧路径和分支不能唯一命中、路径越界、登记表 mutex 超时、任一步移动或登记表校验失败时必须停止；多项批量重命名出现中途失败时必须报告并恢复已移动项和原登记内容，不能留下半完成状态。
- Verification: 重命名后重新运行 `git worktree list --porcelain`，确认新目录存在、旧目录不存在；逐个核对分支、HEAD、`git status --short`、活动登记项唯一性以及原 slot/前后端端口未变化。任务证据同时记录 Git 路径和登记表最终名称、路径、槽位、端口。
- Forbidden action: 禁止用文件系统直接移动代替 `git worktree move`，禁止无锁直接改写 `worktree-ports.json`，禁止把重命名误做成删除重建，禁止重新分配槽位、随机换端口或顺带重命名用户未要求变更的分支。
- Evidence: `doc/tasks/20260901-rename-worktrees-tr1-tr5/verification-report.md`，五个 `int_main` worktree 批量改名为 `TR1..TR5` 时保留原分支、slot `1..5` 和端口，并同步通过 Git 注册、物理路径和端口登记复核。

## Worktree 旧无监听槽位释放门禁

- Trigger: 用户明确要求清理 `D:\IntRuoyiWorktree\.ports\worktree-ports.json` 中旧 active slot、无监听 slot、过期 runtime slot 或 slot 1..100 全占用但多数端口未监听。
- Preflight check: 先读取 `docs\worktree-restrictions.md`、`docs\branch-runtime-ports.md` 和端口登记表；用 `Get-NetTCPConnection -State Listen` 复扫登记端口；释放前必须取得同 `reserve-worktree-slot.ps1` 一致的登记表 mutex；历史登记项可能缺少 `profile` 等字段，脚本必须显式可选读取字段并 fail fast。
- Blocker: 未获得用户明确授权、端口仍有监听、创建时间不满足用户给定条件、登记表校验失败、active 项释放后出现重复 active slot/端口、或无法确认修改只影响用户指定范围时必须停止。
- Verification: 重新读取登记表确认目标 active 项已变为 inactive；复扫 worktree 端口监听；运行 `pwsh -NoProfile -File scripts\preflight\branch-runtime-port-guard.ps1`；在任务日志记录清理和保留清单。
- Forbidden action: 禁止把“无监听”误当作可删除目录或可停止进程；禁止未持锁并发改写登记表；禁止把今天创建、仍有监听或不在用户条件内的 slot 一并释放；禁止用随机端口绕过 slot 全占用。
- Evidence: `doc/tasks/20260805-worktree-slot-registry-cleanup/verification-report.md`，按用户条件释放创建于 2026-08-05 之前且前后端端口均无监听的 `int_main` active slot，并保留今天创建或仍监听的 slot。

## 主工作区 Maven Target 冲突时的隔离验证 Worktree 门禁

- Trigger: 主工作区目标模块 `target` 已损坏、`mvn clean` 卡在 `WinNTFileSystem.delete0`、存在其它任务 Maven 正在写同一模块输出目录，但当前任务仍需要运行定向 Maven 回归。
- Preflight check: 先读取 `docs\worktree-restrictions.md` 并确认目标路径是 `D:\IntRuoyiWorktree\` 子路径；只创建 task-owned detached worktree（`git worktree add --detach`），不启动前后端服务时不登记端口；把当前任务的最小源码 diff 精确应用到该 worktree，并用 `git diff -- <path>` 复核。
- Blocker: 目标路径不在 `D:\IntRuoyiWorktree\`、需要启动服务但未登记 slot、无法证明 applied diff 只含当前任务改动、或 isolated Maven 仍无法到达目标 Surefire 时必须停止；不得继续清理主工作区共享 `target`。
- Verification: 记录 detached worktree 路径、HEAD、applied diff、目标 Maven PASS 摘要、未启动服务/未使用端口的说明；验证后从主工作区执行 `git worktree remove --force <path>`，并确认 `Test-Path <path>` 为 false。
- Forbidden action: 禁止强杀其它任务 Maven/Java 进程、删除共享模块 `target`、改用随机 Maven 输出目录、把 isolated worktree 未验证 diff 的结果当作主工作区验证、或遗漏 worktree 删除记录。
- Evidence: `doc/tasks/20260803-dcc-docx-preview-system-exception/verification-report.md`，主工作区 DCC target 与并发 Maven 冲突时，创建 detached verification worktree、应用单个 service diff、通过 focused/adjacent preview Maven 测试后删除 worktree。

### 隔离验证 Worktree Sparse 初始化门禁

- Trigger: `git worktree add --detach <path> HEAD` 长时间停留在 `locked initializing`，或全量 checkout 因旧 target/残留目录拖慢但当前只需后端定向 Maven。
- Preflight check: 先确认卡住的 git 进程命令行只属于当前任务目标路径；停止当前任务自己的 git 进程后，用 `git worktree remove -f -f <path>` 清理 initializing 登记，再改用 `git worktree add --detach --no-checkout`、`sparse-checkout init --cone`、`sparse-checkout set IntRuoyiBackend doc docs`、`checkout HEAD`。
- Blocker: 卡住进程无法证明属于当前任务、目标路径不在 `D:\IntRuoyiWorktree\`、或 sparse 范围不足以运行目标验证时必须停止；不得停止其他任务 git 进程或扩大删除范围。
- Verification: 记录首次 initializing 清理、sparse worktree 路径、checkout 后 `git status --short --branch`、目标 Maven PASS 和删除后 `Test-Path=False`。
- Forbidden action: 禁止把 initializing 目录直接当普通目录递归删除；禁止跳过 Git 注册清理；禁止用 sparse checkout 缺文件导致的编译失败冒充业务失败。
- Evidence: `doc/tasks/20260805-ac-m18-progress-repair/verification-report.md`，AC-M18 首次全量 detached worktree 卡在 initializing，清理当前任务登记后改用 sparse checkout，应用目标 diff 和最小编译基线后 90 个 JUnit PASS 并删除 worktree。

### 隔离验证 Worktree 编译基线差异门禁

- Trigger: 隔离验证 worktree 应用当前任务 diff 后，Maven 在目标 Surefire 前被非当前任务源码或测试编译错误阻塞；常见于主工作区已有并行 compile baseline 但新 worktree 基于较旧 HEAD。
- Preflight check: 先用目标 Maven 失败日志定位阻塞文件，再从主工作区读取该文件的精确 diff；只允许同步已存在于主工作区、且为到达当前任务目标测试所必需的最小编译基线，并在任务日志中标注为 verification unblocker。隔离源码范围还必须包含后端根级构建配置，例如 `lombok.config`；缺少该文件会让正式的链式 setter 在隔离编译中变成 `void`，产生大面积伪编译错误。若必须临时覆盖 dirty 基线，应用前必须生成逐文件清单，至少记录相对路径、原文件是否存在、原始 SHA-256 和覆盖 SHA-256；运行验证后按清单精确恢复原有文件、删除覆盖新增文件，并再次逐项验证原始哈希或不存在状态。
- Blocker: 编译阻塞需要业务语义判断、主工作区没有对应已验证 diff、基线 diff 会改变当前任务目标行为、无法区分当前任务 deliverable 与验证环境补丁，或隔离目录缺少根级构建配置时必须停止；不得继续扩大同步范围或把隔离前置缺失写成源码失败。
- Verification: 记录每个 baseline patch 的来源文件、`git apply --check` 结果、根级构建配置清单、首次失败摘要、补齐后的目标 Maven PASS 摘要，以及验证 worktree `git status --short --branch` 中这些差异仍被标注为非当前 deliverable。使用覆盖清单时还必须记录总项数、恢复原有文件数、删除覆盖新增文件数、哈希/存在性错误数和最终端口/进程状态。
- Forbidden action: 禁止把无关 compile baseline 混入当前任务实现结论、禁止用整仓 patch 或 `git add -A` 复制并行改动、禁止把未到达 Surefire 的编译通过写成目标测试通过、禁止在最终提交时不区分当前任务和 verification unblocker；禁止依赖人工记忆恢复、整目录覆盖或在未通过清单核验时提交/清理 worktree。
- Evidence: `doc/tasks/20260805-ac-m19-deterministic-backfill/verification-report.md`，AC-M19 新 worktree 验证中先后同步主工作区 QA/PQC 最小编译基线，解除非 AC-M19 编译阻塞后目标 Maven 两组 JUnit 均 PASS；`doc/tasks/20260805-ac-m18-progress-repair/verification-report.md`，AC-M18 隔离 worktree 先补主工作区 QA/PQC 编译前置，再到达并通过目标 AC-M18 Surefire；`doc/tasks/20260813-concurrent-regression-repair-reverify/verification-report.md`，隔离源码首次漏掉根级 `lombok.config` 时产生大面积链式 setter 伪错误，补齐正式配置后 2654 个主源码编译和 26 项定向测试全部通过；`doc/tasks/20260814-frontline-active-order-submit-allocation-docs/execution-log.md`，临时运行覆盖 36 项在真实 E2E 后恢复 13 个原有文件并删除 23 个覆盖新增文件，逐项核验错误数为 0。
- 本次流程7复验补充：先核对 Maven 绝对路径与 PATH，工具存在不等于命令可用；定向 Surefire PASS 只证明 validator slice，不能升级为跨流程、数据库或 E2E GREEN。任务仍为 `blocked` 且 linked worktree 有未提交代码时，不得 apply cleanup、merge 或删除 worktree。

### Maven 环境刷新与受限测试证据门禁

- Trigger: 用户更新 Maven 安装位置，或隔离 worktree 的定向测试需要区分工具环境问题与源码编译问题。
- Preflight check: 同时核对当前进程 `$env:MAVEN_HOME`、用户级 `[Environment]::GetEnvironmentVariable('MAVEN_HOME','User')` 和新路径下 `mvn.cmd -version`；用户级变量已更新但当前 Codex 进程仍可能继承旧值，验证命令必须使用已确认的绝对路径并记录 Java/Maven 版本。
- Blocker: reactor 或目标模块在进入当前任务 Surefire 前被其它模块/既有源码编译错误阻断时，目标任务只能记为 BLOCKED；缺少正式跨流程适配器时必须由端口 fail-fast，不能用 mock、默认进度或合成来源把失败变成成功。
- Verification: 可记录受限 `javac`/JUnit 的类级通过作为局部证据，但只有同一 Maven 命令进入目标 Surefire 且 `BUILD SUCCESS` 才能标记模块级 GREEN；提交、融合和 cleanup 必须等待完整证据。
- Forbidden action: 禁止修改无关编译错误来解阻、把受限测试通过升级为完整回归通过、在适配器缺失时提交默认成功实现，或在任务仍 blocked/in_progress 时 commit/merge/remove worktree。
- Evidence: `doc/tasks/20260821-flow-repair-04-active-order-complete-unified-backfill/execution-log.md` 与 `verification-report.md`（Maven 3.9.16 环境、ERP/MES 首错、Flow4 受限 9/9 边界）。

## 前置源码缺失与 Maven GREEN 复验门禁

- Trigger: 目标 worktree 基线缺少当前测试所需的 Java 源码，而源码只作为另一个 worktree 的 untracked 文件存在；或 Maven 命令超时但目标目录已经生成了部分 Surefire 报告。
- Preflight check: 在源 worktree 确认 staged 区为空，逐文件检查归属、风险词和 `git diff --check`；为前置源码形成精确 Git 提交后，通过 Git 提交接入目标 worktree，并复核祖先链、工作区和 staged 文件清单。Maven 超时后先确认没有同模块并发编译，再用同一 `-pl ... -am` 命令延长超时复跑。
- Blocker: 发现秘密、fallback/临时逻辑、无法解释的 staged 文件、前置提交混入无关文件、目标编译仍缺类，或复跑命令没有真实退出码时必须停止；超时前生成的旧报告只能作为诊断线索，不能作为 GREEN 证据。
- Verification: 记录前置提交 hash、`git show --name-status --oneline -1`、目标 worktree `git status --short --branch`、完整 Maven 命令和本次退出输出；只接受本次命令进入 Surefire 且 `BUILD SUCCESS` 的结果。
- Forbidden action: 禁止复制未提交文件绕过 Git，禁止使用旧 `target`/静态扫描/API-only 冒充 Maven GREEN，禁止用 `git add -A` 将其它任务文件带入前置提交，也禁止在并发 Maven 未释放时叠加复跑。

## 多 Worktree 批量融合门禁

- Trigger: 将 `D:\IntRuoyiWorktree\` 下多个功能分支批量合入 `int_main`，尤其是 worktree 存在 dirty 状态、多个分支修改同一服务/API/测试文件，或合并后需要立即删除 worktree。
- Preflight check: 先冻结 `int_main` 的 dirty 基线；逐个 worktree 记录 branch、HEAD、`git status --short`、任务文档 `## Current Status`、验证报告结论和目标验证命令；dirty 内容必须在原分支形成独立可追溯提交。按依赖和冲突风险顺序逐分支 merge，每次冲突修复后运行该分支目标测试，不得等全部 merge 完才判断冲突语义。
- Blocker: 任一 dirty 内容无法归属或验证、分支 tip 未正式保存、任务文档仍为 `blocked` 或验证报告明确存在未达成目标、冲突只能靠整文件覆盖解决、目标回归失败、或无法证明 `git merge-base --is-ancestor <branch> int_main` 时必须停止，不得复制目录内容、跳过分支或直接删除 worktree。
- Stale branch guard: 分支 clean 只代表文件已提交，不代表适合合并；若 `git diff int_main..<branch>` 会删除大量主线已存在任务证据、发布脚本门禁或其它与该任务无关的新主线文件，先按任务状态和验证报告判定合并资格，禁止把 clean-but-blocked 的旧分支强行合入主线。
- Verification: 所有分支合入后逐项验证 ancestor 与 worktree clean；运行覆盖全部目标分支的聚焦组合回归。扩大到旧完整测试类时若出现失败，必须用 `git log`/`git diff <baseline>..HEAD -- <paths>` 判断是否由本批分支引入，并同时保留宽回归失败和目标回归结果，禁止把窄测通过冒充全量通过。
- Forbidden action: 禁止把多个 dirty worktree 内容直接复制到主工作区；禁止用 `--force` merge、整文件 `ours/theirs`、静默跳过失败测试、或在首次推送和分支 ancestor 验证前删除 worktree。
- Evidence: `doc/tasks/20260726-merge-worktrees-into-int-main/verification-report.md`，六个 worktree 在 dirty 内容独立提交、逐分支 merge、冲突后聚焦回归和 ancestor 验证后进入删除阶段。

### 主线同路径未跟踪任务目录融合门禁

- Trigger: 任务分支已形成独立提交，但 `int_main` 同时存在同路径未跟踪任务目录、同路径未提交文件或其它并行 dirty 改动。
- Preflight check: 除了比较 task commit 与主线已跟踪文件的重叠，还必须用 `git status --porcelain`、`git ls-files --others --exclude-standard` 核对提交将新增的每个路径；逐项确认主线未跟踪目录不会被 fast-forward 覆盖，并记录当前 `int_main` HEAD 与任务基线的祖先关系。
- Blocker: 任务提交新增路径在主线已存在为未跟踪目录，主线同路径文件有未提交修改，或主线 HEAD 已领先任务基线且无法在不改写 dirty 主线的隔离环境完成语义重放时，必须停止受保护融合；不得用 `git add -A`、stash、reset、checkout、clean 或删除未跟踪目录绕过保护。
- Verification: 记录 task commit hash、主线 HEAD、tracked/untracked overlap 清单、`git merge-base --is-ancestor` 结果；只有主线工作树安全且 fast-forward 前置关系成立后，才能执行 merge 并在主线重跑目标测试和 `git diff --check`。
- Evidence: 流程修复任务收尾中，独立 worktree 的条件损耗 commit 与主线定向代码未形成 tracked overlap，但主线存在同路径未跟踪流程任务目录及大量并行 dirty 改动，因此保留 commit、停止融合并将主线程验证记为 NOT RUN。

### 跨分支运行时契约复验门禁

- Trigger: 多个子分支分别实现相邻功能，且一个分支新增接口、Service、Mapper、模板或授权链路，另一个分支在运行时应调用它；典型现象是各分支单测都通过，但主线合并后 Spring 注入、接口实现、构造器参数或调用顺序仍可能缺失。
- Preflight check: 每次合并依赖分支后，先用 `rg` 查找新增接口的生产实现和调用点，再为跨分支调用链补一个最小 RED/GREEN 测试；测试必须证明调用发生在任何写库、状态推进或外部副作用之前。
- Blocker: 新接口只有测试 mock 或空接口、生产服务未注入、调用点只在前端/API payload 中体现、跨分支依赖靠默认值/空实现/可选 bean 运行，或无法证明失败会阻止后续写入时必须停止。
- Verification: 运行跨分支最小 JUnit/静态合同和合并后的组合回归；记录 RED 原因、GREEN 命令、调用顺序断言和 `git diff --check`。
- Forbidden action: 禁止把各分支独立 PASS 当作整体 PASS；禁止用 optional/autowired fallback、空实现、默认模板、默认员工或 API-only 验证掩盖运行时链路缺口；禁止等全部分支合完后才第一次看跨分支注入关系。
- Evidence: `doc/tasks/20260730-production-line-process-pool-implementation/execution-log.md`，F2 报工提交与 F4 设备账号员工授权各自通过后，主线新增 RED/GREEN，确保 `MesProFrontlineFeedbackSubmitServiceImpl` 在创建报工/记录本/工序池事件前调用 `MesFrontlineSubmitAuthorizationService`。

### 子 Agent 主工作区溢出基线门禁

- Trigger: 并行子 agent 本应只写 `D:\IntRuoyiWorktree\`，但主工作区出现同一任务的新增/修改文件，且这些文件会被后续分支 merge 覆盖或触发 untracked overwrite。
- Preflight check: 子 agent 开始后先确认 shell `workdir` 是目标 worktree；凡使用 `apply_patch` 修改文件，文件路径必须写目标 worktree 下的绝对路径，不能使用相对路径。合并任何子分支前运行主工作区 `git status --short --branch`、`git diff --name-status`、`git ls-files --others --exclude-standard`，按任务范围判断溢出文件是否属于当前任务；属于当前任务的先形成单独“spillover baseline”提交并记录文件列表和提交 hash。
- Blocker: 溢出文件无法确认归属、包含 unrelated 用户改动、包含 secret-bearing 输出、或与待合并分支语义冲突且无法证明保留策略时必须停止。
- Verification: baseline 提交后重新运行 `git status --short --branch`，再执行目标分支 merge；若发生 add/add 冲突，必须语义合并并运行该分支目标测试。
- Forbidden action: 禁止删除 untracked 文件来绕过 merge 保护；禁止用整文件 `ours/theirs` 覆盖任务日志；禁止把溢出内容混入后续实现提交。
- Evidence: `doc/tasks/20260730-production-line-process-pool-implementation/execution-log.md`，F2 子任务溢出文件先独立提交为 `028e2904`，随后再合并 F1/F2 分支并运行目标测试。

### 并行子 Agent 控制权隔离门禁

- Trigger: 多个子 Agent 并行执行实现、修复、独立验证或收尾，尤其是 reviewer/tester/finisher 同时存在；出现同级 Agent 误中断、误恢复、误调度其它任务，或把其它 Agent 的无输出误判为当前任务阻塞。
- Preflight check: 子 Agent 只能汇报本任务状态、运行本任务命令、读写本任务 worktree 和任务文档；需要中断、恢复、重新派发或等待其它 Agent 时必须交给 root/supervisor 统一执行。root/supervisor 在恢复长任务前先用 `list_agents` 核对所有 Agent 状态，用 `wait_agent` 等待结果；不得用 exec 嵌套协作工具或用普通命令轮询替代协作状态。
- Blocker: 子 Agent 已经中断或调度了非本任务 Agent、无法确认其它 Agent 是否还有长跑命令、或同一 worktree 出现两个写入 owner 时，必须停止该子 Agent 的调度动作并由 root/supervisor 重新建立唯一 owner。
- Verification: supervisor 记录每个 Agent 的最终状态、最后真实命令结果和是否存在长跑 session；被误中断的任务必须重新触发独立验证并取得 PASS/FAIL 报告后才能继续合并或收尾。
- Forbidden action: 禁止 reviewer/tester/worker 主动 interrupt、followup 或重派同级 Agent；禁止把其它 Agent 的 interrupted 状态当作任务失败或成功；禁止在未确认唯一 owner 前继续写同一 worktree。
- Evidence: `doc/tasks/20260812-frontline-pqc-dcc-qa-delivery-supervision/execution-log.md`，DF10/DF11 round-4 复审中 DF11 独立验证误中断 DF10；supervisor 重新恢复 DF10 并等待两条独立验证都 PASS 后才进入合并决策。

## 并行主工作区远端快进融合门禁

- Trigger: 主工作区持续被并行任务写入，任务分支已在干净 worktree 中完成实现、验证和推送，但本地 `int_main` 无法保持 clean 以接收 `task_closeout.py` 的 ff-only merge。
- Preflight check: 在任务 worktree 中先 `git fetch origin int_main`，确认 `origin/int_main` 是当前任务分支 HEAD 的祖先；若不是祖先但任务分支干净且需要解除 closeout 的非 fast-forward blocker，先在隔离 worktree 内语义合入 `origin/int_main`，解决冲突后再重跑该任务的目标后端、前端、迁移或端口守卫验证，并记录远端主线 hash、任务 HEAD 和验证结果。若 `<主程序根目录>` 主工作区持续 dirty，不要反复抢主工作区 clean 状态；可从 `origin/int_main` 新建一个 `D:\IntRuoyiWorktree\` 下的集成 worktree，登记 slot 后在该 worktree 内合并功能分支、验证、提交，并用 `git push origin HEAD:int_main` 更新远端主线。
- Blocker: `origin/int_main` 不是任务 HEAD 的祖先且合入主线冲突无法语义解决、目标验证失败、远端主线又前进导致非快进推送被拒、任务分支存在未提交改动、或缺少可用 `origin` push remote 时必须停止。若目标验证使用 `mvn -pl <module> -am`，上游依赖模块的 compile/testCompile 失败也属于目标验证失败；必须阻塞并记录缺失类/Mapper/测试文件，不得因为当前任务源码未改该依赖模块就跳过、排除或降级验证。
- Verification: `git merge-base --is-ancestor origin/int_main HEAD` 通过，目标验证命令 PASS，`git push origin HEAD:int_main` 成功，随后 `git fetch origin int_main` 并确认 `origin/int_main` 指向已验证 HEAD 或其后续已融合提交。若集成时触发相邻功能静态合同失败，必须先判断是否为当前融合后主线回归；可在同一集成提交中做最小语义修复并复跑相邻静态合同，禁止把失败静态合同记为无关后继续推送。
- Forbidden action: 禁止为了 closeout 强行清理、回滚或提交并行任务文件；禁止 force push；禁止在未验证融合后 HEAD 的情况下直接更新 `int_main`；禁止把本地 dirty 主工作区清洁失败当作远端主线已集成。
- Evidence: `doc/tasks/20260727-codex-test-node-chain/verification-report.md`、`doc/tasks/20260728-node-chain-route-filter/verification-report.md`，主工作区持续并行写入时，任务分支先融合 `origin/int_main`、完成目标验证，再按远端快进路径集成；`doc/tasks/20260730-edhr-frontline-fill-tabs/verification-report.md`，eDHR 集成在远端主线新增 DCC testCompile 缺失类后阻塞，未跳过依赖模块门禁。

### 已含内容的零差异融合判定门禁

- Trigger: 任务 worktree 已完成实现和验证，但合入最新 `int_main` 后出现 `git diff --quiet int_main HEAD` 为零差异，或主线已有其它提交把同一功能内容带入，导致再次 merge 只会产生无内容合并提交。
- Preflight check: 先在干净 worktree 中合入最新 `int_main` 并重跑目标验证；再记录 `git status --short`、`git diff --quiet int_main HEAD`、目标功能关键字的 `git grep <int_main>` 结果，以及 `branch-runtime-port-guard.ps1`。若要声明“已融合”，必须证明 `int_main` 当前树已包含目标 SQL/API/前端入口/测试或等价交付物。
- Blocker: worktree 合入最新主线后仍有树差异、关键交付物只存在于任务分支不在 `int_main`、目标验证失败、零差异仅由整文件覆盖或回滚造成、或无法解释任务提交与主线同内容不同祖先关系时必须停止。
- Verification: `git diff --quiet int_main HEAD` 返回 0，`git grep` 在 `int_main` 命中目标交付物，目标后端/前端/静态合同/类型检查 PASS，端口守卫 PASS，并把“内容已在 `int_main` 当前树，无需有内容合并”的判断写入任务验证报告。
- Forbidden action: 禁止为制造祖先关系而在脏主工作区强行无内容 merge、`update-ref`、reset、amend 或 force push；禁止只凭分支名、记忆或 `git status clean` 宣称已融合；禁止跳过合入最新主线后的目标复验。
- Evidence: `doc/tasks/20260814-batch-record-repeat-row-link-implementation/verification-report.md`，重复行组任务在 worktree 合入最新 `int_main` 后目标验证通过，`git diff --quiet int_main HEAD` 返回零差异，`git grep int_main` 证明主线已含重复行组 SQL、后端保存接口、前端入口和静态合同。

### 并行脏主工作区手工三方融合门禁

- Trigger: 已验证任务分支需要合入本地 `int_main`，但主工作区存在并行未提交改动，且其中部分路径与任务分支 incoming diff 重叠；用户明确授权手工三方融合并要求保留并行改动。
- Preflight check: 先记录 `int_main` HEAD、任务分支 HEAD、主工作区全部 dirty 路径和 `incoming ∩ dirty` 精确交集；任务分支先提交并语义合入当前 `int_main` 已提交基线，解决冲突后复跑目标验证。主工作区只允许按路径暂存交集文件，记录 stash 引用和路径清单；非交集 dirty 文件不得进入 stash、暂存区或任务提交。
- Blocker: 未取得用户明确授权、交集包含无法归属的未跟踪文件或敏感文件、任务分支未通过验证、路径级 stash 无法完整保存、stash apply 冲突无法语义保留双方修改、或恢复后无法证明并行改动仍在工作区时必须停止。
- Verification: `git merge-base --is-ancestor <old-int-main> <task-head>` 与融合后 `git merge-base --is-ancestor <task-head> int_main` 均通过；路径级 stash apply 后检查冲突标记、原交集路径、`git diff --check` 和目标回归。只有确认并行改动已恢复且未被暂存/提交后才允许删除 stash。
- Forbidden action: 禁止全工作区 stash、整文件 `ours/theirs`、提交并行改动、直接 `update-ref` 移动已检出的脏 `int_main`、先删除重叠文件再 merge、或在未验证恢复结果前 drop stash。
- Evidence: `doc/tasks/20260810-pqc-leader-form-edit-release-flow/execution-log.md`，PQC 分支与本地 `int_main` 的 4 个并行脏文件重叠，取得用户授权后按路径保存、语义融合并恢复并行改动。

### 无独有提交的镜像 Worktree 收尾门禁

- Trigger: 额外 worktree 基于较旧的 clean HEAD 开发，但目标文件在脏 `int_main` 中已有并行演进；最终实现以 `int_main` 当前文件为基线完成语义融合，并把融合后文件同步回 worktree 做隔离验证，因此 worktree dirty diff 已不再是纯任务补丁。
- Preflight check: 必须先取得用户对语义融合策略的明确授权；逐项列出 worktree 的全部 tracked/untracked dirty 文件，确认每个文件在主工作区均存在且 SHA-256 完全一致；确认 `git rev-list --count int_main..HEAD = 0`、主工作区目标回归通过、目标端口无监听且没有进程引用 worktree 路径。
- Blocker: 任一 dirty 文件在主工作区缺失或哈希不同、分支存在独有提交、无法证明主工作区已通过目标验证、存在运行进程/端口监听、或 dirty 文件包含无法归属内容时必须停止；不得把“不想提交”解释为“可以丢弃”。
- Verification: 记录逐文件哈希相等结果、独有提交数、目标验证、端口和进程检查；移除后确认 Git 注册与物理目录均不存在，并在目录删除后再持登记表 mutex 将对应 slot 标记为 inactive。
- Forbidden action: 禁止把包含主工作区并行改动的整文件 diff 提交成任务分支；禁止只比较一个组件就忽略 worktree 的其它 untracked 文件；禁止目录删除前释放 slot，或用强制删除掩盖尚未融合的独有内容。

## D-Main 本地主线滞后远端融合门禁

- Trigger: `D:\ProjectPackage\IntRuoyi\IntRuoyiAll` 的本地 `int_main` 在 `git fetch origin int_main` 后同时 `ahead` 和 `behind`，需要把远端 `origin/int_main` 融合回本地主线。
- Preflight check: 先记录 `git status --short --branch`、`git rev-list --left-right --count HEAD...origin/int_main`、本地 ahead 提交清单和远端 behind 数量；融合前确认未跟踪/脏文件仅属于当前任务文档或已形成基线提交。
- Blocker: 冲突文件无法通过语义合并保留双方门禁、当前任务文件可能被远端同名覆盖、远端更新后端口 guard 失败、或本地 ahead 提交无法解释时必须停止。
- Verification: 冲突解决后先用 `rg -n "^(<<<<<<<|=======|>>>>>>>)" <冲突文件或 staged 文件>` 清除真正的 Git 冲突标记，再运行 `scripts\preflight\branch-runtime-port-guard.ps1`、受影响前端/后端验证和 `git status --short --branch`；不要用未锚定的 `=======` 全仓扫描判断冲突残留，因为大量 Java 注释分隔线会产生假阳性。若 `git diff --cached --check` 命中远端历史已存在的 whitespace，必须用 scoped diff 证明冲突解决文件和当前任务文件未新增 whitespace，再记录上游遗留项。
- Forbidden action: 禁止用整文件 `ours/theirs` 覆盖经验门禁文档；禁止因为上游 whitespace 遗留就静默改写大量远端历史文件；禁止在未重跑端口 guard 和目标验证前提交或推送融合结果。
- Evidence: `doc/tasks/merge-int-main-code-20260728/verification-report.md`，本地 `int_main` 领先 5、落后 445 后融合 `origin/int_main`，保留远端新增前端经验门禁并通过前端 `ts:check`、后端 `compile` 和端口 guard。

## Worktree 前端依赖启动门禁

- Trigger: 在 `D:\IntRuoyiWorktree\` 下新增或恢复 worktree 后启动前端、运行 Vite、执行前端 `pnpm` 脚本、执行真实 E2E，或日志出现 `Command "vite" not found`、`node_modules\.bin\vite` 缺失、`cross-env is not recognized`。
- Preflight check: 启动前端或运行前端脚本前先检查目标 worktree 的 `IntRuoyiFronted\package.json`、`pnpm-lock.yaml` 和目标命令需要的 `node_modules\.bin\<tool>.cmd`；例如 Vite/E2E 检查 `vite.cmd`，`pnpm ts:check` 检查 `cross-env.cmd` 与 `vue-tsc`。若依赖缺失，在目标 worktree 前端目录执行 `pnpm install --frozen-lockfile`，不得复制其他工作区的 `node_modules`。若首次 install 超时但 `node_modules\.pnpm` 已有包而顶层 `.bin` 未链接，可在同一目标 worktree 中执行 `pnpm install --offline --frozen-lockfile --ignore-scripts --child-concurrency=2 --reporter append-only` 补齐链接；不得因此改锁文件或跳过类型检查。安装独立依赖后还要检查前端根目录是否残留 `node_modules.*` 目录联接或符号链接；即使 Vite watcher 已忽略该命名，源码扫描插件仍可能递归进入。
- Blocker: `pnpm install --frozen-lockfile` 或离线补链失败、修改 lockfile、依赖目录仍缺目标脚本工具、目标路径不是当前任务 worktree，或页面长期停在启动页且 `/@id/@purge-icons/generated` 等虚拟模块请求不返回时必须停止。后者先核对前端根目录 reparse point 和请求状态，不得换端口、复用旧前端进程、直接调用残缺 `.pnpm` 内部包冒充完整脚本，或把后端/API 验证冒充真实页面 E2E。
- Verification: 记录 `pnpm install --frozen-lockfile` 或离线补链命令退出码、目标 `node_modules\.bin\<tool>.cmd` 存在性、前端根目录不存在任务遗留依赖联接、目标前端脚本或前端入口 HTTP 200、关键虚拟模块请求完成、Vite 进程命令行指向目标 worktree，以及任务结束后登记端口是否释放。
- Forbidden action: 禁止复制 `node_modules`、在前端根目录保留指向主工作区依赖的 `node_modules.*` 联接、使用主工作区 Vite 进程冒充 worktree 前端、改共享 `.env` 抢端口、或在依赖缺失时切换到 API-only。
- Evidence: `doc/tasks/20260726-edhr-release-dossier-requirement-switches/execution-log.md`，slot 5 worktree 首次启动前端失败于 `Command "vite" not found`，补跑 `pnpm install --frozen-lockfile` 后 8086 前端真实启动并通过 E2E；`doc/tasks/20260804-qa-regulation-tab/execution-log.md`，`2020804_qa` worktree 首次 `pnpm ts:check` 失败于 `cross-env` 缺失，确认 worktree 与主工作区锁文件哈希不同后，没有复用主工作区 `node_modules`，改在目标 worktree 执行 `pnpm install --frozen-lockfile` 后类型检查通过。

## Worktree Java 21 后端低内存启动门禁

- Trigger: `D:\IntRuoyiWorktree\` 下附加 worktree 启动后端 jar、运行真实 E2E、或日志出现 `There is insufficient memory for the Java Runtime Environment to continue`、`Chunk::new`、`C2 CompilerThread`、Surefire fork 超时。
- Preflight check: 先确认后端端口来自已登记 profile/slot，端口未被未知进程占用，jar 来自当前 worktree 构建产物；再确认当前 `java -version` 是否为 Java 21 且项目编译目标仍为 Java 17。若 Java 21 fork/C2 native 内存失败，只允许在当前任务运行命令中收敛 JVM 资源参数，例如 `-Xms128m -Xmx768m -Xss512k -XX:ActiveProcessorCount=4 -XX:-TieredCompilation -XX:ReservedCodeCacheSize=64m -XX:MaxMetaspaceSize=512m -XX:+UseSerialGC`。
- Blocker: 端口归属不明、jar 非当前 worktree、低内存参数后 health 仍不上线、测试 fork 仍卡死且无同等目标验证可执行、或需要切换端口/数据源/旧 jar 才能继续时必须停止并记录；不得冒充运行态成功。
- Verification: 记录启动命令、PID、端口监听命令行、`/actuator/health` 为 `UP`、前端入口 HTTP 200；若 Maven `-am` fork 在本机资源下超时，需保留 dumpstream 证据，并用同模块目标测试或禁用 fork 的目标测试完成复核，明确说明不是 API-only 或跳过测试。
- Forbidden action: 禁止随机换端口、改共享 `application-local.yaml`、复用旧 jar、强杀未知 Java 进程、把 `health` 未达 `UP` 当通过、或把超时的 fork 测试静默忽略。
- Evidence: `doc/tasks/20260726-codex-test-process-route-case/verification-report.md`，slot 1 worktree 后端首次 Java 21 C2 native memory crash，使用当前 jar 与登记端口 48082 加低内存 JVM 参数恢复，真实页面 E2E 写入 4 个测试项后通过。

## Worktree Server-Only 打包旧本地仓库模块门禁

- Trigger: 附加 worktree 中为避开无关模块 `testCompile` 或全 reactor 卡顿，改用 `mvn -pl yudao-server "-Dmaven.test.skip=true" package` 只打 server；运行态 health 为 `UP`，但新接口返回 `404 请求地址不存在`。
- Preflight check: 如果当前任务改动在业务模块内，server-only 打包前必须先把该 worktree 的业务模块及其 reactor 依赖执行 `mvn -pl <module> -am "-Dmaven.test.skip=true" install`，并用 `jar tf` 或等价方式确认本地仓库模块 jar 含目标 Controller/Service；server fat jar 只需确认嵌入 `BOOT-INF/lib/<module>-*.jar`。
- Blocker: server-only package 直接复用本机 Maven 仓库旧 SNAPSHOT、目标 Controller 只存在于 worktree `target` 但未 install、未登录或真实 E2E 返回 404、或只看 `/actuator/health=UP` 就宣称运行态加载成功时必须停止。
- Verification: 记录模块 install 命令、目标类在 installed module jar 中存在、server package PASS、运行 jar SHA256、后端 health、前端 HTTP 200、真实页面 E2E 命中目标写接口且不再 404。
- Forbidden action: 禁止为了绕过全 reactor 编译失败复用旧本地仓库业务模块；禁止手工解压替换 nested jar、拼混合 jar、复制主工作区旧 jar、或用 API-only/health-only 替代目标页面 E2E。
- Evidence: `doc/tasks/20260803-dcc-product-onboarding-flow/verification-report.md`，slot 15 worktree 首次 server-only 打包后产品建档接口 404，安装 worktree `yudao-module-dcc`/`yudao-module-mdm` 依赖链并重打 server 后，8096/48096 真实 Playwright E2E 通过。

## Worktree 真实 E2E 运行产物门禁

- Trigger: 在 `D:\IntRuoyiWorktree\` 下执行真实 Playwright E2E，尤其需要通过登记 slot 启动前端与后端。
- Preflight check: 创建 worktree 前先判断是否需要启动真实前后端；需要运行态时必须取得具名任务分支，并确认 `git branch --show-current` 非空，因为当前 `start-branch-backend.ps1` 与 `start-branch-frontend.ps1` 会先解析分支名，detached worktree 会在端口解析前失败。若当前 Git 策略要求用户明确授权创建分支，应在创建 worktree 前取得授权。启动前还要同时检查目标 worktree 的后端可执行 Jar（如 `IntRuoyiBackend\yudao-server\target\yudao-server-exec.jar`）、前端 Vite 依赖（`IntRuoyiFronted\node_modules\.bin\vite.cmd`）、端口登记项、目标端口监听状态和 worktree 本地前端 env；`.env.local` 或等效启动环境必须显式指向登记后端端口，并关闭无人值守 E2E 需要关闭的验证码开关。
- Blocker: worktree 处于 detached HEAD 且启动脚本无法解析分支、未获授权创建具名任务分支、Jar 不存在、Vite 依赖不存在、端口未按登记 slot 成对启动、构建/安装失败、端口被非当前 worktree 占用、登录页验证码仍开启、或前端实际代理到其它后端端口时必须停止，不得静默切回 8081/48081、复用其他 worktree 进程、API-only 代替真实页面路径。
- Verification: 记录 worktree 具名分支、Jar 存在性或构建命令退出码、Vite 依赖存在性、worktree env 中的前后端端口与验证码开关、前后端端口监听 PID 和命令行归属、前端 HTTP 200、后端 health UP，以及真实 E2E 命令和结果。
- Forbidden action: 禁止在 detached worktree 中手工复制启动脚本参数绕过分支解析；禁止把缺运行产物或验证码开启解释为功能失败；禁止随机换端口、强杀未知进程、复制 node_modules、复用旧 Jar、只靠命令行临时 env 但未验证页面实际关闭验证码，或只跑静态合同冒充真实 E2E。
- Evidence: `doc/tasks/20260817-qa-word-template-import-verification/execution-log.md`，QA Word 导入验证在 detached worktree 完成构建后才发现标准启动脚本无法解析空分支名，本轮仅保留为已记录的一次性验证绕过；后续真实运行态 worktree 必须在创建前取得具名分支条件。

### 任务目录 Playwright 脚本依赖解析门禁

- Trigger: 真实 E2E 脚本位于 `doc/tasks/<task-id>/...`，但依赖安装在 `IntRuoyiFronted\node_modules`，运行时报 `Cannot find module 'playwright'` 或其它前端 devDependency 缺失。
- Preflight check: 先确认 `IntRuoyiFronted\node_modules` 和目标依赖真实存在，再用 `NODE_PATH=<worktree>\IntRuoyiFronted\node_modules` 或从前端工作目录的正式脚本入口运行；这只修正 Node 模块解析，不改变 E2E 的真实页面路径。
- Blocker: 前端依赖目录不存在、`pnpm install --frozen-lockfile` 失败、目标脚本必须从任务目录读取相对 artifact 但命令切换工作目录会改写证据路径，或需要新增依赖/复制 node_modules 才能运行时必须停止并记录工具链前置缺口。
- Verification: 记录实际脚本路径、`NODE_PATH` 或工作目录策略、前端依赖存在性、Playwright 真实页面命令和结果 JSON；不要把首次模块解析失败写成产品业务失败。
- Forbidden action: 禁止复制 `node_modules` 到任务目录、把依赖解析失败当作页面不可达、或改用 API-only/静态合同替代真实 Playwright 验收。
- Evidence: `doc/tasks/20260903-dcc-product-catalog-registration-binding/execution-log.md`，产品目录绑定跳转 E2E 在 slot 17 worktree 中首次因任务目录脚本无法解析 `playwright` 失败，显式指向前端依赖后真实页面复跑通过。

### 主工作区端口被并行任务占用时的成对运行态门禁

- Trigger: 主工作区 `8081/48081` 被无关任务、旧 Jar 或无法替换的共享运行态占用，但当前任务仍需要真实前端路径 E2E 验证。
- Preflight check: 先确认占用进程命令行、Jar 路径、端口和任务归属；若不是当前任务运行态，不得停止或覆盖。随后在 `D:\IntRuoyiWorktree\` 使用 `scripts\runtime\reserve-worktree-slot.ps1` 取得正式 slot，并用同一 worktree 的后端 Jar 与前端 Vite 组成成对端口运行态。
- Blocker: 主端口占用进程归属不明、worktree 未登记 slot、前端代理仍指向主工作区后端、后端 Jar 不是当前修复产物、或无法证明前后端 PID 均来自当前 worktree 时必须停止。
- Verification: 记录 slot、前端端口、后端端口、前后端 PID 和命令行归属；确认后端 health 为 `UP`、前端 HTTP 200、真实 Playwright 使用 worktree 前端 URL，并验证目标列表和业务进度输出。
- Forbidden action: 禁止强杀并行任务进程、把旧 `48081` Jar 当作修复验证、只替换嵌套 class 拼混合 Jar、前端走 worktree 但后端仍代理到主工作区、或在未确认运行态成对归属前宣称真实 E2E 通过。
- Evidence: `doc/tasks/20260802-third-party-feedback-import-list-progress/verification-report.md`，第三方报工导入修复在主 `48081` 被 DCC 任务占用时，使用 slot 9 的 `8090/48090` 成对运行态完成真实导入验证。

## 任务分支快进融合的同名未跟踪文档门禁

- Trigger: task-owned 分支需要快进合入 `int_main`，而主工作区已存在同路径未跟踪任务文档或并行任务记录。
- Preflight check: 先记录主线 dirty/untracked 清单和分支 task-owned 文件清单；代码/测试提交只纳入当前任务文件。若同名未跟踪文件会阻止快进，不能删除、覆盖或整目录复制；应从最新主线重建最小代码提交，保留主线已有文档，再在主线程单独核对任务记录。
- Blocker: 无法区分文件归属、需要覆盖主线未跟踪文件、或快进会改变并行任务内容时必须停止；不能用 `reset`、`checkout`、`stash`、`clean` 或强制合并绕过。
- Verification: 记录 task-owned commit、`git merge --ff-only` 结果、主线 HEAD 是否包含 commit、主线程目标编译/测试/`git diff --check`/runtime guard；任务文档保留在主线原路径并准确区分局部代码完成与跨流程 blocker。
- Forbidden action: 禁止把“文档未能随代码提交”误报为生产代码未合入，也禁止把局部合同测试 PASS 升级为全链路放行。

## Worktree 删除门禁

- Trigger: 删除、清理、合并后移除、修复残留目录、处理 `git worktree remove` 失败、`Directory not empty`、`Invalid argument`、或断链 worktree。
- Preflight check: 先读取 `docs\worktree-restrictions.md`，确认目标绝对路径位于 `D:\IntRuoyiWorktree\` 下；用 `git worktree list --porcelain` 确认 Git 注册状态；用 `git status --short` 记录每个目标 worktree 的未提交变更；用 `git merge-base --is-ancestor <branch> int_main` 或等效命令确认分支提交是否已合入目标基线。
- Blocker: 目标不在 `D:\IntRuoyiWorktree\` 下、目标不是用户明确指定的当前任务对象、分支仍有未合入提交、存在未提交变更但用户未明确授权丢弃、目录被运行进程占用、或端口登记表需要释放但无法验证目录已删除。
- Verification: 删除后必须重新运行 `git worktree list --porcelain`，并对每个目标执行 `Test-Path`；若存在端口登记项，只有在目录已删除且任务记录完成后才允许将槽位标记为可复用；验证结果写入当前 `doc\tasks\<task-id>\execution-log.md`。
- Forbidden action: 禁止用 `Remove-Item -Recurse` 替代正常 `git worktree remove` 作为首选路径；禁止删除未指定 worktree；禁止因为 `Directory not empty` 就扩大清理范围；禁止静默丢弃未提交变更；禁止删除或释放其他任务的端口登记项。
- Evidence: 2026-07-26 删除已合入 worktree 前补齐长期经验门禁，要求先确认合入状态、未提交变更授权、路径边界和删除后注册状态。

### task-closeout 主线 worktree 可见性门禁

- Trigger: 在 linked worktree 中运行 `task_closeout.py --mode preview/apply`，输出 `No checked-out worktree for main branch <branch> was found`，或当前任务需要自动 cleanup、快进合并、删除附加 worktree。
- Preflight check: 执行 closeout 前先运行 `git worktree list --porcelain`，确认目标主线分支如 `int_main` 已有 checked-out worktree；若主线未检出，先定位正确主工作区或显式切换为非自动合并收尾。
- Blocker: 找不到主线 checked-out worktree、主线 worktree 脏、任务分支未完成目标验证、或当前任务仍有未解释 blocker 时必须停止 apply，不得伪造 completed 状态。
- Verification: `task_closeout.py --task-id <task-id> --mode preview` 至少能列出 `worktree: linked=True current_branch=<task> main_branch=<main>` 且无 blocked；apply 后再验证 `git worktree list --porcelain`、主线 `git status --short` 和任务记录状态。
- Forbidden action: 禁止在 preview blocked 时继续 apply；禁止手动复制改动到任意主线目录冒充 ff-only merge；禁止为了 closeout 创建临时主线 worktree 后不记录路径和验证。
- Evidence: `doc/tasks/nonconformance-review-mvp-implementation/verification-report.md`，linked worktree closeout preview 因未找到 `int_main` checked-out worktree 阻塞，任务未执行 apply/合并/删除。

### Dirty Worktree 删除保全门禁

- Trigger: 用户要求删除一个或多个 worktree，但 `git -C <path> status --short --untracked-files=all` 显示源码、SQL、测试或任务文档未提交，尤其是当前目标看起来属于其它并行任务。
- Preflight check: 删除前先记录 dirty 文件清单并扫描敏感词；若用户只授权“删除 worktree”而未明确授权丢弃未提交工作，优先在目标 worktree 自身分支创建独立保全提交，再删除 worktree；若目标没有分支或 detached HEAD 无引用保护，必须先创建可追踪分支或取得明确丢弃授权。
- Blocker: 发现明文密钥、无法确认 dirty 文件归属、目标 worktree 正在被其它进程写入、保全提交失败、detached HEAD 没有任何 branch/tag 包含，或用户明确要求不得提交当前脏改动时必须停止。
- Verification: 记录保全提交 hash、`git show --name-status --oneline -1` 文件清单、删除后 `git worktree list --porcelain` 不含该路径、目标物理目录 `Test-Path=False`；若保全分支需要远端保存，还要记录 `git push origin <branch>` 结果。
- Forbidden action: 禁止因已有“删除 worktree”授权就静默丢弃可提交源码；禁止把 dirty worktree 的代码混入主工作区基线提交；禁止在保全提交后忘记复跑 `git worktree remove`，也禁止删除分支引用来掩盖未合入状态。
- Evidence: `doc/tasks/20260805-remove-non-main-worktrees/execution-log.md`，批量删除时 `profile-erp-table-auto-sync` 仍有 31 个未提交实现/测试/任务文件，先提交 `35c583ce5` 到其自身分支后再移除 worktree。

### 按更新时间批量删除的只读盘点与保全门禁

- Trigger: 用户明确授权按最近若干天未更新的条件批量删除 worktree，而非按分支合入状态做常规任务收尾。
- Preflight check: 固定带时区的滚动时间阈值；同时检查目录内部文件、目录及 worktree 专属 Git 元数据最新写入时间，不能只看根目录时间或最后提交时间。使用 `git --no-optional-locks status` 避免检查本身刷新索引；进程扫描排除当前 PID，记录路径归属，不按端口盲停进程。先核对聊天附件；仅对本聊天可管理的托管附件使用归档工具，其余真实 linked worktree 必须核对所属 common Git 目录、注册路径和显式绝对路径边界。
- Preservation rule: 删除授权不等于丢弃源码授权；未授权提交时不得用保全提交绕过最近层级 AGENTS。删除前保存 binary patch、变更/未跟踪文件及核心任务记录到独立恢复目录，逐文件核对 SHA-256；没有 surviving ref 覆盖的 detached HEAD 必须生成完整 bundle 并 verify。保留既有分支与恢复包，不顺手合并、推送或创建备份分支。忽略文件不自动进入保全包，需先识别仍有用途的内容。
- Source archive: 大量小文件可流式写入每目标独立 ZIP，分别核对源码、解包成员和归档整体 SHA-256；可再生成的依赖与构建目录按明确清单排除，链接只记录目标时必须称为源码恢复包，不宣称完整文件系统备份。复用既有包仍须在删除前重检源目录。
- Inventory invariant: Windows 目录的 st_size 反映目录索引分配，可能因 API 或索引整理发生变化，不能当作源码内容大小。删除前比较完整路径集合、类型、全部条目写入时间、普通文件字节数与 SHA-256、reparse 目标；不要因为目录索引字节变化而跳过真正的源码差异。
- Read-only Git diff: 生成补丁时同时使用 `--no-optional-locks` 与 `-c diff.autoRefreshIndex=false`；仅前者不保证 `git diff` 不创建、删除索引锁，从而刷新专属 Git 目录时间。若检查自带副作用已发生，须复现同一命令并证明元数据文件集合、时间、哈希、恢复索引、HEAD 和 status 全部不变，才能只排除已证实的目录时间变化；不明来源的更新仍须保留目标。
- Classification: `.git` 为目录的独立仓库不属于 linked worktree；无 `.git` 的残留也须确认所有相关 common Git 目录均无精确路径或子路径登记，才能按已授权残留清单删除。父目录内普通备份、状态目录和正式恢复资产不自动纳入工作树清理。
- Blocker: 近期更新、运行中、locked/index.lock、扫描拒绝访问、缺失 Git 元数据、物理路径与注册路径不同、或保全核验失败时停止该目标。不得把异常 worktree 静默降级成普通目录递归删除。
- Explicit exception: 仅在用户明确批准“异常目录完整备份后按普通目录删除”时，对固定清单执行该方案；不修复或重写 `.git` 指针，不调用可能误删有效外部注册的 `git worktree remove`。检查外部有效 worktree 的精确注册、HEAD 和专属元数据哈希；并行任务使总注册表变化时，不冻结或回滚无关注册。
- Full snapshot gate: 普通目录清理的“完整备份”须明确隐藏/忽略文件、空目录和 reparse 链接的范围。Windows tar 可能将 junction 展开，即使未显式启用跟随链接，也必须通过实际解包、重建链接和逐文件 SHA-256/结构比对确认；文件包加链接清单不能仅凭打包成功放行。删除前再核对源快照与包/清单哈希，发现差异即停。
- Link boundary: 不沿 reparse point 盘点或递归删除；先精确移除目录内链接，再删除已验证的目标根。原始绝对链接指向不随换位置恢复而自动迁移；ACL/ADS/硬链接拓扑、缺失外部 Git 元数据及单盘灾难恢复必须单独说明，不能夸大恢复承诺。正式恢复资产保留到用户另行授权，不纳入 task-closeout 的临时资产清理。
- Verification: 逐项核对物理目录不存在、所属仓库注册不存在、HEAD 有引用或已验证 bundle、具名分支仍包含原 HEAD；只对已删除且登记端口无监听的目标持同一 registry mutex 置 inactive，并验证其他登记项不变。批量完整证据保存为任务报告，终端仅输出汇总，避免输出截断掩盖遗漏。
- Forbidden action: 禁止只凭最后提交时间判旧、因盘满跳过保全、对 worktree 父目录批量递归删除、将扫描失败记为清理成功、释放有监听或其他任务的槽位、或清理独立恢复目录。
- Evidence: `doc/tasks/20261001-delete-stale-d-worktrees/verification-report.md`；`doc/tasks/20261008-stale-worktrees-cleanup/verification-report.md`。

### Git 注册已移除但物理目录被运行态锁住

- Trigger: `git worktree remove <path>` 返回 `Invalid argument`、Git 注册列表已不再显示目标 worktree，但物理目录仍存在，或残留目录内 `runtime-backend.err.log` / Vite / Java / esbuild 文件被占用。
- Preflight check: 先确认 `git worktree list --porcelain` 已无该路径、残留目录没有 `.git` 文件、目标绝对路径仍在 `D:\IntRuoyiWorktree\` 下；再按命令行和端口定位只属于该残留 worktree 的进程，例如 `Get-CimInstance Win32_Process` 匹配目标路径，`Get-NetTCPConnection` 核对登记端口；进程扫描脚本必须排除当前 PowerShell PID，避免命令行中的目标路径导致自杀式停止。
- Blocker: 若仍有 Git 注册、残留目录存在 `.git`、占用进程无法证明属于目标 worktree、占用端口属于其他 profile/任务、或目录路径越界，必须停止，不得删除目录或停止进程。
- Verification: 记录被停止进程的 PID、名称、命令行、端口和归属依据；停止后确认目标端口不再监听、目标路径 `Test-Path` 为 `False`、端口登记项仅对该目标标记 `active=false/deletedAt/cleanupTask`。
- Forbidden action: 禁止因残留目录删除失败就强杀未知 Java/Node/PowerShell；禁止用父目录批量删除；禁止在未确认 `.git` 已消失前把注册 worktree 当普通目录删除；禁止释放其他 active worktree 的端口登记项。
- Evidence: `doc/tasks/20260727-merge-d-worktrees/verification-report.md`，`20260727_pici` 在 Git 注册移除后被 8084/48084 运行态锁住，确认 PID 和命令行归属后停止目标进程并删除残留目录。

### Git 注册已移除但空目录删除被当前进程占用

- Trigger: `task-closeout-cleanup --mode apply` 已完成 ff-only merge 和 cleanup commit，但 `git worktree remove --force <path>` 返回 `Permission denied`；`git worktree list` 已不再显示目标 worktree，残留目录为空且没有 `.git`。
- Preflight check: 从主工作区或目标外部目录执行核对，确认 `git worktree list` 无该路径、`Test-Path <path>\.git` 为 false、`Get-ChildItem -Force <path>` 计数为 0、目标绝对路径仍在 `D:\IntRuoyiWorktree\` 下。
- Blocker: 残留目录非空、存在 `.git`、仍有 Git 注册、路径越界、或目录内有无法归属文件时必须停止；不得用递归删除扩大清理范围。
- Verification: 仅对确认空目录执行 `Remove-Item -LiteralPath <path>`，随后记录 `Test-Path <path>` 为 false、`git worktree list` 不含该路径、主工作区 `git status --short --branch` clean 或仅 ahead。
- Cleanup rule: 若执行策略拒绝 `Remove-Item`，但已证明目录为空、无 `.git`、无 Git 注册且路径在目标 worktree 根下，可从主工作区使用 `[System.IO.Directory]::Delete(<resolvedPath>, $false)` 删除空目录；删除后仍必须按登记表 mutex 将目标 slot 标记为 `active=false/deletedAt/cleanupTask` 并运行 registry 校验。
- Forbidden action: 禁止从残留 worktree 当前目录反复运行删除；禁止把 `Permission denied` 直接升级为 `Remove-Item -Recurse`；禁止删除父级 `D:\IntRuoyiWorktree\` 或其他任务目录。
- Evidence: `doc/tasks/20260731-dcc-file-category-rules/execution-log.md`，cleanup apply 已创建清理提交并从 Git 注册移除 worktree，但 Windows 因当前目录占用留下空目录，确认无 `.git` 且子项计数 0 后从 `E:\IntRuoyi` 删除空目录；`doc/tasks/20260914-edhr-static-025-multi-inspection-backfill/execution-log.md`，cleanup apply 已移除 Git 注册但物理目录 `Permission denied`，随后确认空目录、无 `.git`、无非当前进程引用，用 `.NET Directory.Delete` 删除残留并将 slot 23 标记 inactive。

### Git 注册已移除但前端依赖目录残留

- Trigger: `git worktree remove <path>` 已移除 Git 注册，但返回 `Directory not empty`、`Result too large`，且残留主要位于 `IntRuoyiFronted\node_modules`、pnpm/esbuild 依赖目录、或 Windows 报 `Access to the path '<name>' is denied`。
- Preflight check: 先确认 `git worktree list --porcelain` 已无该路径、残留目录没有 `.git` 文件、目标绝对路径仍在 `D:\IntRuoyiWorktree\` 下、目标登记端口没有监听、且 `Get-CimInstance Win32_Process` 未发现命令行指向该目标路径的 Node/Java/PowerShell 进程。
- Blocker: 若仍有 Git 注册、残留目录存在 `.git`、仍有归属不明进程或端口、路径越界、或拒绝访问文件不在当前目标目录内，必须停止，不得扩大删除范围。
- Cleanup rule: 若 PowerShell `Remove-Item -Recurse` 或 `cmd /c rmdir /s /q <path>` 对 pnpm `node_modules` 输出大量 `The system cannot find the path specified`、`Could not find a part of the path` 或留下空壳目录，先用当前任务专用空目录对目标 `node_modules` 执行 `robocopy <empty-dir> <target-node_modules> /MIR /R:0 /W:0`，确认子项计数为 0 后再逐层删除 `node_modules`、`IntRuoyiFronted` 和目标 worktree 根目录。若删除仅因目标依赖文件的 `ReadOnly` 属性报 `Access denied`，可在上述路径、注册、进程和端口门禁全部通过后，只清除目标目录树内的 `ReadOnly` 属性再重试；不得修改目标外文件属性。若当前执行环境策略拒绝递归删除，记录 Git 登记已移除、路径边界、端口登记和残留范围，停止自动清理并等待人工或明确授权的同等边界清理方式。
- Verification: 仅对目标残留目录清理属性或空目录镜像后删除，之后重新验证 `Test-Path <path>` 为 `False`、`git worktree list --porcelain` 不含该路径、目标登记项已标记 `active=false/deletedAt/cleanupTask`。
- Forbidden action: 禁止为了处理 `node_modules` 残留删除父级 worktree 根目录；禁止跳过进程和端口核验；禁止在 Git 注册仍存在时把 worktree 当普通目录强删。
- Evidence: `doc/tasks/20260727-merge-remaining-worktrees/verification-report.md`，`codex-test-process-route` 在 Git 注册移除后残留前端依赖目录，确认无 `.git`、无目标进程和 8082/48082 监听后仅清理目标目录并复核不存在；`doc/tasks/20260730-worktree-prune-keep-banzuzhang/verification-report.md`，多个 worktree 的 pnpm `node_modules` 残留需先用空目录 `robocopy /MIR` 清空再删除空目录链；`doc/tasks/20260813-scheduler-seven-issues-closure/verification-report.md`，验证 worktree 的 Git 注册移除后仅残留 pnpm 依赖目录，清理目标只读属性后删除成功，并复核端口、物理路径和 slot 登记全部释放；`doc/tasks/20260920-delete-stale-worktrees/verification-report.md`，批量删除 2026-09-17 前 worktree 时，先用 `git worktree remove --force --force` 移除 Git 注册，再逐项核对无 `.git`、候选路径仍在 `D:\IntRuoyiWorktree` 下、无 Git 注册残留，最后清理 pnpm `gen-mapping` 等依赖残留并将登记表候选 active 项置为 inactive。

### 发布 release worktree 物理根复核门禁

- Trigger: 仅测试服或三环境发布完成后清理临时 release worktree，尤其路径位于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r*\m`、`D:\IntRuoyiWorktree\r*-release-app` 或对应 state dir。
- Preflight check: 分别在维护仓和主程序仓运行 `git worktree list --porcelain`，确认本轮 release 标识已无 Git 注册；再检查固定物理根、子目录和 state dir `Test-Path`；同时用进程命令行确认没有 Java/Node/PowerShell/Playwright 仍引用待删路径。
- Blocker: Git 注册已删除但物理根仍存在、state dir 未删、路径不在本轮 allow-list、仍有归属不明进程引用、或残留目录中存在 `.git` 时必须停止，不得标记任务 `completed`。
- Cleanup rule: 对确认属于本任务、无 Git 注册、无 `.git`、无进程引用的 ignored `node_modules` 残留，可用长路径安全删除或先清属性后删除；如果本地策略拒绝递归删除，改用同等 allow-list 和绝对路径边界校验的删除方式，不扩大到父目录或其他 release worktree。
- Verification: closeout 记录必须同时包含 Git 注册不存在、物理根 `Test-Path=False`、state dir `Test-Path=False`、运行控制台已恢复稳定主路径且 health=`UP`。
- Forbidden action: 禁止只凭 `git worktree list` 无记录判定清理完成；禁止删除其他 r260731a/b/c 等并发发布 worktree；禁止在运行控制台仍指向待删 worktree 时删除目录。
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260730-head-test-only-release\execution-log.md`，`r260731d` Git 注册已删但 ignored `node_modules` 物理目录残留，最终按固定 allow-list 删除并复核所有路径不存在。

### 主工作区融合 worktree 切片后的合同复核门禁

- Trigger: 将一个或多个已验证 worktree 切片同步回 `<主程序根目录>` 的 `int_main`，尤其主工作区已存在并行脏改动、后续补丁或相邻业务测试。
- Preflight check: 先冻结来源 allow-list，并排除不属于本次切片的旧模型、临时证据和相邻问题；复制后对 allow-list 做 source/current hash 复核，区分“漏同步”和“主线后续上下文补丁”。如果 `int_main` 已经有相同修复但还叠着别的任务补丁，先用逐文件 diff 证明哪些内容已存在、哪些是本次切片的额外差异，只提交本次任务的 allow-list 文件，禁止为了统一基线而整文件覆盖或 `git add -A`。随后必须运行目标模块 `testCompile` 或聚焦 Surefire，让整个测试源码先编译；若相邻已有测试因被覆盖的生产合同无法编译，应恢复正式生产行为和测试夹具，而不是删除测试、调低 `failIfNoSpecifiedTests` 或只跑单个已编译类。
- Blocker: source/current 存在未解释差异、同表双模型同时出现、主线已有测试合同编译失败、H2 夹具缺正式列、前端类型导出名和投影层不一致、或发布迁移门禁被已跟踪 SQL 缺元数据阻断时必须停下修正；不得宣称已融合完成。
- Verification: 记录 copied/missing/different 计数、被排除路径、聚焦后端测试数、前端静态合同、`pnpm ts:check`、迁移策略门禁、`git diff --check` 和 staged 为空。发布 SQL 仅补元数据时也要重跑迁移门禁，证明不是绕过。
- Forbidden action: 禁止用整分支 merge、ours/theirs、宽泛复制或 `git add -A` 处理局部切片；禁止把主线后续补丁覆盖成旧来源；禁止因测试编译失败就把失败归类为“无关”而跳过；禁止在未区分当前任务和并行任务文件前提交。

### 流程任务主线程复验与收尾证据门禁

- Trigger: task-owned worktree 已完成实现和隔离验证，准备提交并快进融合到 `int_main`。
- Preflight check: 在来源 worktree 逐文件冻结提交 allow-list；先运行 branch-runtime-port-guard，再提交实现/测试，随后从主工作区实际执行目标模块 `testCompile`、聚焦回归和 `git diff --check`。
- Blocker: 主工作区存在未解释的同路径改动、提交未能 fast-forward、目标测试未进入 Surefire、或只引用隔离 worktree 结果而缺少主线程复验时，必须保持未完成并记录阻断原因。
- Verification: 记录 task-owned commit hash、fast-forward 后的 `int_main` HEAD、主线程测试摘要、目标路径 diff-check 结果；并明确未运行服务、数据库和写入型 E2E 的边界。
- Forbidden action: 禁止用“任务文档 completed”替代代码融合证据，禁止清理或覆盖并行 dirty 改动，禁止把窄测通过升级为全链路 GREEN。

### Detached HEAD linked worktree 收尾门禁

- Trigger: linked worktree 的 `git status --short --branch` 显示 `HEAD (no branch)`，且 `task_closeout.py --mode preview` 返回 `Current worktree branch could not be resolved.`。
- Preflight check: 先记录 `git rev-parse --git-dir`、`git rev-parse --git-common-dir`、`git status --short --branch --untracked-files=all` 和 cleanup preview JSON；若任务限制禁止 commit/push，保持 `ready_for_closeout` 或明确 `blocked`，不要执行 cleanup apply。
- Blocker: 当前 worktree 无可解析分支、用户未授权创建具名任务分支、任务规则禁止 Git 提交/推送、或 cleanup apply 会触发自动提交/合并/删除 worktree 时必须停止并记录冲突。
- Verification: 任务日志记录实现验证 PASS、bug/evidence validator PASS、cleanup preview 的 keep/delete/blocked/warnings，以及未运行 apply/commit/push/remove 的原因。
- Forbidden action: 禁止在 detached HEAD 下强行 cleanup apply、临时创建分支绕过授权、把 `ready_for_closeout` 改写成 `completed`，或删除仍承载未提交实现 diff 的 worktree。

## 主线程复验时的主线漂移与 PowerShell 参数门禁

- Trigger: 定向 Maven 验证期间并行提交推进 `int_main`，或 PowerShell 将逗号分隔的 `-Dtest` 值拆成参数，导致命令尚未进入 Maven。
- Preflight check: 在编译和测试前记录 `git rev-parse HEAD`；将逗号分隔的 Surefire 类名作为一个带引号的参数传给 Maven；每次验证阶段结束后重新读取 HEAD，并用 `git merge-base --is-ancestor <task-integration> HEAD` 确认切片仍在最新主线。
- Blocker: 测试运行前后 HEAD 发生未解释变化、Maven 命令因未引用逗号而在 PowerShell 解析阶段失败、或无法区分并行任务失败与当前任务失败时，必须重跑或记录阻断，不得把旧 HEAD 的结果冒充最新主线证据。
- Verification: 在最终 HEAD 重跑目标模块 compile 和定向 JUnit，记录 Surefire 测试数/失败数；随后运行 `git diff --check` 与 `branch-runtime-port-guard.ps1`，并保留主工作区其它 dirty/untracked 改动。
- Forbidden action: 禁止为追赶主线漂移而 reset、checkout、stash、clean 或覆盖并行改动；禁止使用未加引号的逗号测试参数、随机更换登记端口或把 PowerShell ParserError 误报为业务测试失败。

## 删除操作顺序

1. 阶段 1：目标确认
   必查项：用户指定路径、绝对路径、Git worktree 注册、当前分支、HEAD、是否在 `D:\IntRuoyiWorktree\` 下。
   推荐命令：`git worktree list --porcelain`、`Resolve-Path`、`git -C <path> status --short`。
   Fail Fast：路径越界、路径不存在但仍有 Git 注册残留、或目标不是当前任务指定对象。
   必须记录：路径、分支、HEAD、dirty 文件数量。

2. 阶段 2：合入与脏变更检查
   必查项：目标分支是否已合入 `int_main`，是否存在未提交变更，用户是否授权丢弃。
   推荐命令：`git merge-base --is-ancestor <branch> int_main`、`git rev-list --count int_main..<branch>`、`git -C <path> status --short`。
   Fail Fast：未合入提交数量大于 0，或 dirty worktree 未获得明确删除授权。
   必须记录：是否已合入、未合入提交数、dirty 文件数量和授权依据。

3. 阶段 3：删除与残留处理
   必查项：优先使用 `git worktree remove <path>`；dirty worktree 仅在已获授权时使用 `--force`。
   推荐命令：`git worktree remove --force <path>`、`git worktree prune`。
   Fail Fast：删除失败且原因不是当前目标自身残留；不要扩大到父目录或其他 worktree。
   必须记录：删除命令、退出码、失败文本或成功结果。

4. 阶段 4：收尾验证
   必查项：Git 注册列表、物理目录、端口登记项、任务日志。
   推荐命令：`git worktree list --porcelain`、`Test-Path <path>`、读取 `D:\IntRuoyiWorktree\.ports\worktree-ports.json`。
   Fail Fast：任一目标仍注册、物理目录仍存在、或端口登记状态无法解释。
   必须记录：最终 worktree 列表、目录存在性、端口登记表处理结果。

## Maven 用户级环境刷新与当前进程继承差异

- Trigger: 用户更换 Maven 安装位置，或同一桌面会话中需要使用新 Maven 运行编译/测试。
- Preflight check: 同时读取用户级 MAVEN_HOME/Path、当前进程 $env:MAVEN_HOME，并直接执行新路径下的 mvn.cmd -version；用户级变量更新不会刷新已启动的 Codex/PowerShell 进程。
- Verification: 对本次命令显式设置进程级 MAVEN_HOME 与 Path，记录 mvn.cmd -version 的 Maven/Java 版本；新终端或新任务再复核当前进程变量。
- JDK evidence: 分开记录 pom.xml 的 source/target 或 release 编译目标、mvn -v 的实际 JDK 版本/路径和 Surefire 执行结果；编译目标 Java 17 不能证明测试运行于 JDK 17。要求 JDK 17 验证时，先检查已有工具链并仅在任务进程内设置 JAVA_HOME/Path，再复核 mvn -v；不得把 JDK 21 结果标为 JDK 17。
- Test compile precondition: Maven 的 -Dtest 只筛选执行测试，仍会编译模块全部测试源码。既有测试引用目标 JDK 不支持的 API 时，应记录具体文件/行、基线证据和编译阻塞；经任务范围授权作等价测试修正后重跑，不以跳过编译、切换 JDK 或降低断言冒充通过。
- Forbidden action: 禁止因当前进程仍显示旧路径就修改无关项目配置，禁止把绝对路径 Maven 已通过误写成系统环境已刷新，禁止下载/安装第二份 Maven 作为旁路。

### 全量回归工件分类与工具阻断门禁

- Trigger: 全量 MES/JUnit 回归已产生 Surefire XML，但主工作区重跑受 Maven 参数解析、JVM 内存、fixture 或并行编译影响，或需要把失败分派给相邻流程 owner。
- Preflight check: 只读扫描目标 worktree 的 `target/surefire-reports/TEST-*.xml`，先用 suite 聚合核对 tests/failures/errors/skipped，再保留每条 testcase 的 class、method、原始 F/E 和最短错误摘要；将流程 gate、相邻流程、并行模块和环境/fixture 作为互斥 primary 分类，环境问题仅作二次标记。
- Blocker: XML 工件缺失、聚合数与报告基线不一致、无法取得逐条 class/method、Maven 尚未进入 Surefire、或失败根因只能靠猜测时必须停在分类/阻断，不能把 skipped、fixture、PowerShell ParserError、JVM native memory failure 写成业务 RED，也不能以局部定向绿证替代全量回归。
- Verification: 记录只读工件路径、suite/test/failure/error/skip 聚合、逐条清单与 owner 矩阵；对每个 failure/error 提供原命令的 `-Dtest=Class#method` 最小复现和后续动作；重新运行时必须使用真实 fixture/JUnit，保留原始退出码和工具错误。
- 多轮报告绑定：target/surefire-reports 会保留未重跑类的旧 XML，也会被下一轮覆盖。逐类报告必须核对本次命令开始/结束时间、完成日志中的类名及计数和当前 XML 的时间、计数；其中任一不匹配，只能记录为未绑定证据，不能宣布该场景通过。编译失败或尚在运行时，不得拿目录里的 XML 作为本次运行结果。
- 证据封存：稳定交付后先绑定源码、选择器及运行命令，再在下一次重跑前保存完成日志和报告摘要、SHA256。日志与 XML 相互印证后才汇总通过数；中间单类通过、整批通过、独立验收通过与已融合须分别记录。
- Forbidden action: 禁止让流程 gate owner 修复跨模块失败，禁止 API-only、mock、默认成功或跳过测试掩盖缺口，禁止把合法 runtime slot 当业务失败，禁止覆盖并行 worktree 或修改其它任务代码来“清零”分类。

### 发布 worktree 与控制台身份一致性门禁

- Trigger: 每次 build-release/publish-test 创建新的临时 release worktree，或运行控制台端口仍由上一轮任务占用。
- Preflight check: 记录 maintenance/app worktree 绝对路径、冻结 HEAD、clean 状态、控制台 config/state-dir/PID；preview 输出的 source roots、releaseTag 和 state dir 必须与本轮 worktree 完全一致。
- Blocker: preview 命中旧 worktree/旧配置、operation 进程已退出但状态仍 RUNNING、worktree 注册/物理路径/端口归属无法解释时停止，不构建或发布。
- Verification: 使用 git worktree list --porcelain、git status --short --branch、进程命令行和 preview JSON 交叉验证；operation final 后再允许清理。
- Forbidden action: 禁止跨仓库错误执行 git worktree add、复用旧控制台 state、删除未确认归属的 worktree、用本地 JSON 手工伪造 SUCCESS。
- Evidence: IntRuoyiMaintance task 20260823-fix-training-rules-sfc-test-release execution-log.md ISSUE-014/015。

### 主工作区大规模 Dirty/Untracked 分类门禁

- Trigger: 主工作区同时出现大量 tracked dirty、untracked 任务文档、运行快照、迁移包或本地 Office 输入，且需要恢复主线可集成状态。
- Preflight check: 先用 git status --porcelain=v1 --untracked-files=all 或 NUL 分隔输出冻结基线；处理包含中文的路径时必须使用 Git 的 NUL 输出或正确解码，不能把 Git 的引号/八进制转义误判为实际路径。按“主干代码/测试、正式项目文档、并行任务记录、可再生生成物、敏感本地数据、未知业务输入”分类。
- Commit rule: 只对归属明确且已通过 staged 文件清单、git diff --cached --check 和定向验证的文件选择性暂存；禁止整体 git add -A、把并行任务半成品并入主线，或用提交掩盖未知业务输入。
- 主干快照提交：用户仅要求提交推送时，冻结起始路径与 SHA-256，暂存前后核对源码、索引内容和 HEAD；冻结后的新改动保留原处。任务应明确 Git 完整性核验与业务验证的边界，不把提交或推送通过记作构建、业务回归或 E2E 通过。
- Ignore rule: 可再生的 tmp-*、编译输出、运行时快照、测试依赖、备份目录、review 运行目录和本地迁移包进入项目 .gitignore；并行任务工作记录和本机 Office 输入只在当前机器的 .git/info/exclude 中排除，保留实体文件且不改变团队共享规则。
- Index lock rule: 遇到 .git/index.lock 时先检查活动 Git 进程和锁文件时间；活动进程结束后重新读取 HEAD、状态和 ancestry，再决定是否需要处理 stale lock，禁止直接删除可能仍被使用的锁。
- Blocker: 已跟踪的设计表格、业务资源或其他不可再生输入无法确认归属时，必须保留 dirty 并单独交由业务负责人审阅；不能通过 restore、reset 或宽泛 ignore 隐藏修改。
- Verification: 最终同时记录提交 hash、分支 HEAD、git ls-files --others --exclude-standard 数量、git status --short --branch、git diff --check 和仍需业务确认的 tracked 文件清单；未跟踪归零不等于业务文件已经获准提交。
- Forbidden action: 禁止删除并行任务实体文件，禁止将数十 GB 的数据库/MinIO 备份提交到仓库，禁止把 OfficeCLI 的格式或 Schema 问题当作可安全提交的业务变更。

### 运行时融合后的版本与端口交叉核验

- 触发场景：功能 worktree 已融合到 `int_main`，需要用本机长期运行态做真实页面验证，且运行态目录可能同时保留多个历史 jar。
- 隔离完整构建：旧运行包包含未提交但已经验证的前期修复时，干净 HEAD 加本次补丁可能退回这些修复。先冻结旧包对应的最小源码基线和本次补丁白名单，逐文件记录来源、相对路径、字节数与 SHA-256，独立审查后复制到自有隔离 checkout；不从共享脏目录直接打包，不携带无来源旧 class。
- 构建证据：标准完整 package 与同一输入的实际测试执行分别记录；跳过测试执行的 BUILD SUCCESS 不能替代回归 PASS。新包关键 class 和伴随 class 须与自身已验证 target 核对，稳定副本再次核对整体 SHA-256；尚未加载目标 PID、健康检查及真实业务复验的包只能记为构建通过。
- 经验规则：先核对 `int_main` 的祖先链和分支端口门禁，再按 PID、启动命令、jar 文件名和独立日志确认端口归属；只在新 jar 的健康检查和启动成功时间窗均通过后宣称运行态已切换。
- 经验规则：如果两个已验证运行包分别覆盖不同模块，优先以最新且已验证的运行包为底，逐个替换缺失的 nested module jar，再用 `jar tf` 复核关键 class 同时存在；不要直接把单个 class、`target/classes` 或未核对的模块拼成 fat jar。
- 经验规则：若完整打包被无关模块阻断且只能做本机定向恢复，hotfix Jar 必须单独命名并记录原 Jar 哈希、hotfix Jar 哈希、外层 nested module `compress_type=0`、替换 class 哈希、旧/新 PID、health 和登录态目标接口业务码；同时把完整构建阻断点单独列为非任务 blocker，避免把 hotfix 运行态写成发布构建通过。
- 经验规则：启动参数中的日志文件路径、超时等关键配置，尽量用完整单参数或环境变量传递；不要让命令行出现 `key= value` 这种被空格拆开的写法，否则 Spring Boot 可能拿到空值或错误值，导致日志不落盘或配置未生效。
- 排查顺序：记录旧 PID/新 PID，确认新 PID 独占 `48081`，请求 `/actuator/health`，再扫描本次日志中的启动成功或失败标记；不要只凭端口可访问或历史日志判断版本。
- 禁止做法：禁止按端口盲杀不属于当前任务的 Java 进程，禁止把 worktree 构建成功写成 `int_main` 已验证，禁止在主工作区 dirty 时清理或覆盖并行任务文件。

### 融合前主线二次漂移与 Dirty 阻断

- 三方整合未提交代码时，须分别记录共同提交、两来源HEAD及逐文件SHA256；隔离目录内的主线参考副本不是本任务资产，不能整体提交。合并工具输入先统一换行再比较，原文件仍只读；出现真实内容冲突后由分工worker处理，禁止重跑机械同步覆盖worker结果。最终合入前再次核对来源摘要，漂移时停止并重建验证基线。

- 触发场景：用户要求把附加 worktree 融合进 `int_main`，但 rebase/验证期间主分支又被其它任务推进，或主工作区保留并行任务 dirty/untracked 文件。
- 经验规则：融合前重新执行 `git log --left-right --cherry-pick int_main...<branch>`；若出现 `<` 侧提交，先在附加 worktree 再 rebase 到当前 `int_main` 并重跑目标验证。即使分支已可 fast-forward，主工作区仍需 clean 后才能运行 closeout apply。
- 阻断处理：主工作区 dirty 属于其它任务时，只记录文件清单和阻断原因，不做 stash、restore、clean、reset，也不手工绕过 closeout guard。
- 验证方式：记录最终分支领先提交数、任务提交 hash、目标静态/单测结果、`git diff --check` 和 closeout preview 输出。
- Evidence: `doc/tasks/20260918-production-batch-record-json-publish-implementation/verification-report.md`，`20260918_gongyiluxian` closeout preview 保留任务证据但阻塞于 `E:\IntRuoyi` 主 worktree dirty，未执行 cleanup apply、commit、merge 或 worktree remove。

### Worktree 绝对路径补丁门禁

- 触发场景：当前 shell 已在附加 worktree，但补丁或工具调用使用了主工作区相对路径、默认仓库根或混合盘符路径。
- 经验规则：对附加 worktree 改文件时，补丁目标必须使用当前任务 worktree 下的绝对路径；首次补丁后立即用 `git -C <worktree> status --short -- <path>` 和 `git -C <主程序根目录> status --short -- <path>` 交叉确认没有误写主工作区。
- 阻断处理：发现误写主工作区时，只能删除或回滚本次误创建且未跟踪的明确文件；若误改已存在 tracked 文件，必须停止并报告，不能用 restore/reset 隐藏。
- 验证方式：记录误写路径清单、清理方式、主工作区 `git status --short -- <path>` 为空，以及目标 worktree 中对应文件存在并通过定向验证。
- Evidence: `doc/tasks/20260909-epassword-compliance-hardening/execution-log.md`，在 `D:\IntRuoyiWorktree\20260909_epassword` 继续补 4.10 文档时，首次相对路径补丁默认解析到 `E:\IntRuoyi` 并失败，随后改用 worktree 绝对路径写入并复核主工作区无误落文件；`doc/tasks/20260909-form-parser-json-editor-frontline-preview/execution-log.md`，`jiexi123` 表单解析任务中首次补丁误落主工作区后，按任务文件精确删除误建文档并精确 restore 本任务误改测试，再用目标 worktree 绝对路径重写并复核主工作区同路径 diff 为空。

### 干净 Worktree 与主工作区未跟踪证据分离门禁

- Trigger: 用户要求使用干净 worktree 修复，但缺陷清单、设计草稿或验收证据只存在于 `<主程序根目录>` 主工作区的未跟踪文件中，目标 clean worktree 不包含该文件。
- Preflight check: 只读读取主工作区证据文件并记录 `git -C <主程序根目录> status --short -- <path>`；同时在目标 worktree 运行 `git status --short`，确认后续代码补丁只落入目标 worktree。不得把主工作区未跟踪证据复制进 clean worktree 来冒充基线文件。
- Blocker: 用户要求更新该共享证据文件但目标 clean worktree 不包含它，或无法判断证据文件是正式基线还是并行任务未跟踪资产时，先停止并请用户确认更新归属。
- Verification: 任务日志记录主工作区证据路径、主工作区文件状态、目标 worktree 路径、目标 dirty 文件清单，以及未编辑主工作区证据文件的原因。

### Detached HEAD 收尾分支门禁

- Trigger: 附加 worktree 处于 detached HEAD，且需要运行 `task-closeout-cleanup` preview/apply、提交、推送、融合或删除 worktree。
- Preflight check: 在收尾前先运行 `git status --short --branch` 与 `git branch --show-current`；若当前分支为空，只允许记录 preview 结果和阻塞原因，不执行 cleanup apply、commit、push、merge 或 worktree remove。
- Blocker: cleanup preview 输出 `current_branch=None` 或当前分支无法解析时，必须保持任务非 completed；先由用户明确选择应绑定的分支或允许建立正确分支后才能继续集成收尾。
- Verification: 记录 detached 状态、cleanup preview 的 blocked 行、任务最终状态以及未执行 commit/push/apply 的原因。
- Forbidden action: 禁止在 detached HEAD 上猜测分支名、强行提交、手工绕过 closeout guard、直接删除 worktree 或把 blocked preview 写成 cleanup PASS。
- Evidence: `doc/tasks/20260914-edhr-static-021-inventory-evidence-chain/verification-report.md`，EDHR-STATIC-021 在 linked worktree 中 cleanup preview 阻塞于 `Current worktree branch could not be resolved`，任务按规则停在 blocked。


## 测试夹具随融合提交门禁
- 触发：测试引用 doc/tasks 下被忽略的策略草案、样例或快照，源工作区通过而新 checkout 缺文件。
- 规则：将测试必需且不含敏感信息的原始夹具归入对应模块 src/test/resources，并更新测试读取路径；生产策略与未批准测试草案必须保持隔离。不得用编造内容或跳过断言掩盖缺文件。
- 验证：以 Git 跟踪清单确认夹具随实现提交，重新执行实际消费夹具的测试；不要把源工作区忽略文件存在当作合并后可复现的证据。


## 交付清单与完整构建来源分开封存

- 修复交付同时核对任务差异清单与实际完整构建输入清单；后者应覆盖被忽略但真实参与编译的源码、根构建配置及二进制资源，并关联编译器输入。两份清单不能互相代替。
- 发现调用方已交付而Mapper、状态消费者或测试依赖漏入清单时，退回原修复线程完整盘点并重新封存；整改后按最终源码重新运行回归，不沿用整改前日志或旧XML。
- 隔离索引核对基线和修复差异各自的精确路径及内容；临时索引预演不等于实际提交或主干融合通过。


## 隔离索引保留文件元数据

- 触发：精确融合或单独提交任务记录使用隔离索引，重新read-tree后Git反复扫描大量未改文件。
- 规则：主索引没有已暂存改动且与当前HEAD一致时，可把已核验的主索引原字节复制到任务隔离索引，再仅暂存授权路径，以保留文件元数据；真实主索引和并行任务资产保持保护。
- 门禁：提交前核对HEAD、主索引SHA、精确暂存路径和候选树差异；提交后核对实际来源、无关资产和暂存状态。保留索引缓存不能替代源码指纹或省略内容核验。
