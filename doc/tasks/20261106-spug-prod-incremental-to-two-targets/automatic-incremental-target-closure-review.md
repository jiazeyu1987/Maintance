# 自动增量剩余 MAIN 恢复控制闭包只读审查

## Current Status
ready_for_review — MAIN58已由父任务实际finalize PASS，不再触碰。MAIN59首次安装仅stage130包和空epoch目录后失败，旧PID5885/业务保持；同PID初始化与59专用空stage续办已完成，精确封包输入Linux51项/零skip及Windows45项通过。仅TASK helper修改；尚未代父任务续办59，全部失败原件保留。

## 2026-11-08 父进程与执行worker环境职责修正

- 父任务19:04 UTC一次finalize在FINALIZE_PROCESS_ENVIRONMENT_CHANGED退出；19:09只读证明PID23603/新control保持，active receipt仍旧，finalize-1审计/构造/临时receipt/完成回执均未创建。原错误5bc1701ca9a2保留独占pin；失败发生于任何本次远端写入之前。
- 根因：control.environment是Native以subprocess.Popen(env=config['environment'])传给worker和owner的精确执行环境；systemd HTTP父进程只更新已登记PYTHONPATH并继承原LANG/PATH。父进程LANG/PATH与worker不同是实际合同，原finalizer把两个职责误合并。实际PYTHONPATH/PYTHONDONTWRITEBYTECODE均一致。
- BDD: Given父进程模块路径/精确argv/-B正确而LANG/PATH继承systemd，When核控制进程，Then按父进程合同接纳，保留差异键记录；Given工作进程，Then使用完整config.environment真实启动子进程，核精确环境摘要和实际Native模块pin，任何路径/模块/argv或worker环境漂移拒绝。
- 范围仅TASK环境职责校验，不改运行服务、配置、封包、FD/监听/历史保护门禁。仍禁止代父任务重试finalize；纠正后交独立审查。
- 原失败独占记录：automatic-target58-finalize-environment-failure.json，含private错误原件pin及四个收口路径均未存在证明。actual parent环境不输出值，仅差异键与摘要。
- 新automatic_target_runtime_contract.py按父进程模块路径/实际argv/-B核验；真实子进程用精确config.environment导入真正Native并核环境摘要、字节码禁写及实际模块pin。finalizer及59首次共享此核验，GATE环境也保持精确worker配置，不叠加父环境。
- RED→GREEN：新增6项真实env子进程测试先因正式实现缺失失败，后通过；与历史/监听回归共37项Windows及Linux PASS/0skip，输入SHA保持、容器已清。19:16:04 UTC真实58同PID23603的父进程合同及工作进程环境/模块pin实际PASS，不调用Ledger/控制API，不写服务器，证据automatic-target58-runtime-contract-readonly-proof.json。

## 2026-11-08 MAIN59初始化锁归属与精确stage续办

- 父任务已完成58实际finalize PASS，本分工不再访问58。59首次安装报EPOCH_INITIALIZATION_FAILED；旧模板没有保存初始化子进程stderr，原内部异常未知，不能追认日志中有具体内码。
- 19:22 UTC只读事实：59旧PID5885/旧owner/control/receipt保持；旧127和新stage130成员SHA一致；epoch根0700且完全空，候选owner/control及旧receipt归档均不存在，无新dropin；1759旧pins与五业务容器/挂载保持。replacement_value和validate_policy实际PASS，read_current明确UNINITIALIZED。
- 根因待真实Linux验证：父进程flock的fd经pass_fds继承后fdinfo仍记录父PID，而正式epoch._assert_lock要求当前写入PID就是持锁PID。正确方案是在原持锁父进程执行精确新epoch模块，不解锁转移、不放宽_assert_lock。
- BDD: Given真实父flock和继承fd，When子进程尝试initialize，Then保持拒绝且epoch根不写入；Given原持锁PID加载包内精确SHA的新epoch源码及仅stdlib依赖，When initialize，Then只发布一次INITIALIZED，重入或错误fd/module pin拒绝。
- BDD: Given59精确已stage且epoch仍空，When显式resume-epoch-stage，Then绑定失败原件pin、空目录完整身份、130包、旧127/receipt/PID、无dropin/候选配置、业务与历史pins；复用stage与空目录，绝不删除重装或猜测已有epoch。58 resume策略保持原范围。
- RED→GREEN：真实Linux父flock继承fd的子进程初始化实际拒绝BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED，根目录未写入；same-PID新helper在相同锁内成功仅一次INITIALIZED，错误fd/module pin/非stdlib依赖/已有事件拒绝。旧recovery_backup_epoch模块缓存注入不能影响新pin源码执行；不改产品_assert_lock、不解锁转移。
- 新initializer直接读取130包中唯一epoch模块，核规范文件身份/bytes/SHA，AST限制九项实际stdlib依赖并核模块origin；用独立ModuleType执行验证过的源码，不改旧common模块缓存。物理replacement_value仍在精确新worker环境的只读子进程验证，回报实际replacement/epoch模块pin并与130清单逐项对齐；初始化写入只在父持锁PID中发生。
- `automatic-target59-empty-epoch-resume-proof.json` 独立绑定原private错误、公私诊断三个pin，固定空根完整dev/inode/mode/nlink/uid/gid/size/mtime/ctime、全业务定义摘要/运行态、fstab/挂载、旧127新130包pin、1759原件清单摘要、旧PID/receipt/owner/control、全部候选配置/归档/audit/dropin缺失。补充只读验证不调用Ledger/API、不写远端；原诊断不覆写，原内部异常未知继续明确保留。
- 唯一续办命令：`install_automatic_targets.py 59 --activate --resume-epoch-stage`。首次模式继续拒绝已存在generation；58 resume不扩大；59只复用全部成员字节一致的stage和身份完全相同的空根，在持锁下再次核原状态后初始化。任何已出现事件、初始化回执或候选owner/control均拒绝，不能重放。成功会保留epochInitializationPin和resumedEmptyEpochStage，后续仍完整业务/历史/custody/HTTP/构造/健康门禁。
- 最终51项Linux使用现有0d44578 STANDARD包原始CRLF epoch字节，SHA816a5f7d093fc03011d1f9ad2d5512c42551b565a5cdf0fa7a73e1d4fce641b8；工作树仅换行不同，不修改封包。`linux-automatic-target-epoch-exact-package.json`固定所有helper/test输入SHA、零skip、输入未变、无网络只读挂载且容器已清。Windows45项通过；prepare在禁止socket/subprocess的audit hook下通过，内嵌脚本及UTF-8编译通过。

## 2026-11-08 已激活后的HTTP就绪竞态与收口

- 实际18:47:06 UTC已启动新PID23603，18:49:59只读确认其精确新control/owner/130包及43658监听socket归属；旧receipt原件已归档，新dropin已存在，active receipt仍旧，尚无postactivation构造证明或安装PASS。五业务容器及1990受保护原件保持。
- 本次慢点：history before、after、strict三次完整SHA各扫描约66.13GB原恢复载荷，总读约198GB，接近900秒SSH预算；此证据未删除。日常preserved只有整树stat与1990元数据pin校验，不重复大SQL读取。后续收口直接核已落盘strict快照的完整身份/目录/原件，不能重新读取三遍大载荷或任意忽略内容。
- BDD: Given同一已核PID/argv已启动但TCP尚未监听，When最多15秒请求相同只读URL，Then只对ECONNREFUSED等待并逐次复核同一PID/argv；HTTP非200、错误JSON/结构、PID变化立即失败，无自动任务重试。
- BDD: Given已激活精确58代次及resume-1完整原证据，When显式finalize-activated，Then不安装/重启/重跑Ledger；绑定旧receipt归档、dropin、business-before、strict历史、query审计及preactivation构造，并重新核真实选择/语义健康/数据库前构造边界，最后仅一次发布current receipt与custody。
- 设计约束：这是固定进程的启动就绪等待，不是切换来源、吞业务异常或降级。任何证据或当前代次变化明确阻断，原失败/审计/三快照保持不可变。
- 仅父任务审查后可执行 `install_automatic_targets.py 58 --finalize-activated`。该路径独立构造，完全不包含source-idle、解包、epoch初始化、daemon-reload或restart；只核已经运行的PID23603与精确argv/环境/FD/监听归属、原业务及全部历史，执行只读selections及新的数据库前构造证明后，一次原子发布current receipt与第6代custody。
- 收口绑定 `automatic-target58-resume-activation-failure.json` 中原resume-1审计pins、旧receipt归档、新dropin及preactivation构造；保存新的finalize-1审计和postactivation构造，不修改或覆盖旧attempt。原198GB的三个SHA快照以完整dev/inode/mode/nlink/uid/gid/size/mtime/ctime核身份，原payload内容pins只在身份全部不变时复用；1990个登记元数据pins仍实际重新核SHA。增删、同字节替换、恢复mtime后的内容修改均拒绝。
- 后续59首次安装只在第一次完整扫描计算payload SHA，after以完全相同身份复用原pin、新query单独hash，strict在host锁下再次核完整身份后保存同份证明；三阶段证据仍保留，预计不再有66GB×3的重复读取。原58已落盘三份证明保持原样。
- 验证：31项Windows+Linux真实文件/子进程/HTTP监听测试PASS，Linux无skip、输入SHA保持、容器已清理；audit hook证明prepare无网络/子进程，证明稳定payload不重新打开。58于18:57:44 UTC只读预检PASS，8408条历史身份及业务/挂载一致，130新组件和1990旧元数据pins匹配，仅约3秒；未调用控制API或写服务器。

## 2026-11-07 激活失败只读诊断

- 目标：核准确切失败阶段、原控制/业务/挂载是否保持、历史变化是否来自状态查询审计，并交付可审核续办方案。
- BDD：Given 安装在 HISTORICAL_TREE_CHANGED 失败，When 只读核源码调用链、当前服务 argv、旧/新文件 pins 和实际查询审计，Then 区分已证实事实与缺失的安装前目录快照；不得重跑安装或凭 mtime 声称完整未变。
- 经验门禁：保留失败日志与候选代次；旧文件逐项 SHA/目录身份保持，任何允许的新增审计必须限定路径与正式绑定合同；不以移除整树保护绕过门禁，不重复初始化 epoch。

### 正式修复与续办 BDD

- Given physical source flock 已持有、原 reservation 不存在，When 在 host lock 和最终历史快照之前唯一执行新候选 Ledger.require_source_idle，Then 真实原始终态核验仍执行；其正常资源回执检查可自行获取 host lock，不因安装程序自锁得到 RESTORE_HOST_RESOURCE_BUSY。
- Given 三条旧失败操作可能产生查询审计，When 比较该唯一准入前后真实文件快照，Then 原文件 pin/身份全部相同，新增只接受原同来源 operation 的既有 queries 目录内 UUID.json 与正式 request/owner-result/result 合同；任何其它写入、旧文件修改、目录替换或错误绑定明确失败。
- Given 准入完成，When 获取 host lock 后重新核无 worker/reservation 并固化完整快照，Then 前后两次构造 GATE 不再调用 Ledger；后续 preserved 保持完全严格相等，不忽略 queries。
- Given MAIN58 本次代次已准确暂存但尚未激活，When 显式 resume-staged，Then 只复用精确130包与候选pins，并保留旧失败及构造证据；不重新解包、不覆盖 owner/control、不初始化 epoch。MAIN59首次安装仍须拒绝已存在代次。
- 本机 TDD：真实临时目录/真实子进程写审计，覆盖合法追加、旧文件同字节重建、旧文件改变、外国来源/请求摘要/结果pin不匹配、额外非query文件、目录替换、缺原快照、resume输入不符；远端不执行。

### 已证实的失败阶段及限制

- 原错误：18:02 UTC 的安装进程在 candidate GATE 已成功之后、第一次 preserved 的 HISTORICAL_TREE_CHANGED 处退出；该检查之前的同进程全部容器定义/运行态、fstab、受保护挂载、旧 owner/control 和旧127文件包检查已通过。
- 18:12:32 UTC 只读复核：PID仍2043；旧 control/owner/active receipt pins完全一致；旧127包及新暂存130包全SHA匹配，候选owner/control与审阅版本精确相等；没有新dropin、previous-unit、旧receipt归档、新receipt临时文件或完成安装回执。
- 1990个受保护历史原件全部SHA一致；与17:37:44 UTC原快照相比，五业务容器ID、镜像、PID、StartedAt等运行态一致，Mounts按Destination规范排序后完全相等。Docker返回数组顺序差异已与挂载定义变化区分。
- 18:02:19 UTC三条既有FAILED操作新增UUID查询审计，owner result pins全部匹配、ownerActualExitCode=1、resolutionPins=[]。因安装持有host锁，原查询内资源回执检查得到RESTORE_HOST_RESOURCE_BUSY；这不是新恢复执行，也不改变失败操作为RUNNING。
- 第一次安装的完整树before快照未落盘，不能证明所有未知文件/目录的历史状态；这一限制已写入失败诊断，后续不能伪造或追认。当前全部已登记原件SHA可独立证明保持。

### 修复后的固定顺序与一次续办

- physical source flock全程保持。首先核旧服务PID/配置/回执/custody、原业务/挂载和历史pins；58显式resume只接受当前暂存130包、owner/control、原失败构造及三条查询pins，禁止覆盖或重解包；59首次模式仍拒绝已存在代次。
- 新候选唯一source-idle调用发生在host锁之前。调用前后完整历史身份和每个原文件SHA以不可变文件保存在configuration/installation-audit-<attempt>；只允许原同来源操作的既有queries目录内正式UUID.json追加，并核原request摘要、selection固定owner、owner结果路径与pin、查询结果身份及resolution pins。此前旧文件和目录身份保持；任何额外写入均阻断。
- 查询结束后再持host锁，重核无worker和reservation，固定新的完整历史快照。构造GATE只执行selection/健康/真实数据库前边界，完全不再reconcile；之后严格整树身份相等，不忽略queries。业务/挂载/fstab的before快照也永久记录。
- 仅父任务完成审查及经验门禁后使用 `install_automatic_targets.py 58 --activate --resume-staged`；59仍为 `install_automatic_targets.py 59 --activate`。本分工未执行这两个命令。第二次失败也保留其固定attempt审计目录，禁止循环重试同attempt。
- 新回执增加 sourceIdleQueryAuditPin、strictHistorySnapshotPin、originalBusinessSnapshotPin、sourceIdlePerformedBeforeHostLock、resumedStagedGeneration；原历史安装选择器不变。
- 本机17项通过，Linux独立只读挂载/无网络容器17项通过、无skip、源码输入SHA保持、容器已清理。默认prepare-only在禁止subprocess/socket调用的Python audit hook下仍通过。全部内嵌构造、原健康与epoch脚本独立编译通过。Linux实际服务器激活仍未执行，不能把工具验证视作安装成功。

## 目标、范围与里程碑
- 核对现有 PRIVATE/TASK 原件与当前正式实现，区分归档恢复兼容、控制程序升级和物理目标恢复周期三个问题。
- 形成 58/59 的最小必需升级集合，明确不启用旧源、不改历史 targets、不借用 SMALL58 身份的正式策略。
- 必要时通过已授权可信 common.remote 只读当前精确服务、配置 pins 和物理身份；不执行备份、恢复、安装或服务重载。
- 预期验证：逐目标旧/新合同差异、源/目标 UUID 与锁精确配对、当前未完成任务门禁、可执行部署前置条件及仍缺证据。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；缺少真实 MAIN 源身份时明确记录，不能取小程序或来源57代替。
- 是否从根因和长期维护角度解决：是；基于原控制和恢复合同核闭包，不按 IP 或页面模式推断身份。
- 是否存在临时补丁或绕过：否；本文件只作不可执行计划，不改变产品或配置。

## 经验门禁
- Trigger：自动增量新包与剩余 MAIN 恢复控制配对。Preflight check：真实当前服务/配置/引擎 pin、原来源和恢复目标映射形状、旧 targets 完整原件、物理 UUID/锁/源身份、历史失败消费及当前任务终态。
- Blocker：任一活动恢复、物理身份不能唯一证明、旧来源路径漂移、旧终态无法闭合或 target 构造丢失配置，分别阻断对应部署；不扩大为修改历史。
- Verification：当前实际封包对原 targets 和新顶层 targetBackupEpochPolicies 的构造传递、合法保留挂载身份、目标语义健康，以及新归档格式未变化的源码证据。
- Forbidden action：不启用9个旧源、不将 SMALL58 绑定到 MAIN58、不更改旧归档/旧 targets、不追认旧点 epoch、不重启业务或执行恢复。
- Evidence：automatic-incremental-source-inventory.md、现有 target pairing PRIVATE、父任务逐服安装记录，以及本审查记录。

## BDD（只读审查预期）
- Given 58/59 尚运行旧恢复控制但新备份保持原归档合同，When 对照实际输入/程序/配置，Then 分开报告能否读取新链与恢复后 epoch 是否会记录。
- Given MAIN58 无当前捕获来源，When 设计目标 policy，Then 仅接受实际 MAIN58 自身身份合同，缺少来源身份则记录缺口，不使用 SMALL58。
- Given MAIN59 旧捕获配置路径漂移且源控制未运行，When 配对自身恢复周期，Then 不启动旧源或直接沿用未验证路径；保留原 target 和历史，新 policy 只能绑定已证明的实际 MAIN59 身份及原共同锁。

## 后续部署 helper 准备范围
- 父任务追加要求：准备可审阅的 TASK-only `install_automatic_targets.py`；默认仅 prepare-only，只有未来操作者明确传入 `--activate` 和唯一目标才可能远端写入。本分工不执行激活。
- 输入固定已构建提交 0d445782dc06995b3c84b1b45146ea4b75483f92、STANDARD 130 文件；既有历史 targets/sources 必须完全相等。58 不登记 epoch；59 仅 owner 顶层 targetBackupEpochPolicies，不修改 control 中源57元数据或新增 sourceEpochPolicies。
- BDD: Given 默认参数或 prepare-only，When 执行 helper，Then 只生成/核对本机私密候选，无 SSH 或远端写；Given 显式 activate，Then 必须逐目标验证原安装 custody、无活动目标任务、源物理锁、全部容器/挂载/fstab/历史、实际候选构造和语义健康，之后才能重载该控制。
- BDD: Given 原 pins、历史 targets/sources、runtime 或候选准入变化，When 任一门禁失败，Then 停止且保留旧原件/新暂存代次，不自动重试恢复、不启动旧捕获源；不得把 PLAN_ONLY 候选当已安装成功。
- 回执收口：先归档旧 target-installation 原始字节，成功激活且原业务/历史保持后原子更新 active receipt，仅改变 sourceCommit/engine/ownerConfigurationPin/controlConfigurationPin 四项；追加第6代（58）/第3代（59）custody，并运行原完整 verifier，成功后父任务才更新选中安装指针。

## 审查结论

58、59 应升级完整恢复控制包，但原因须分开表述：

1. 新 FULL/I1/I2 继续沿用 RepositoryPoint / RecoveryMaterial / backup-capture-point 既有格式；epoch sidecar 只在来源控制 registry 中，不进入归档。两旧目标已支持 BINLOG_SQL、scoped database DDL v3 与冻结 AUTO_INCREMENT，不能声称它们因新归档格式无法识别。
2. 两台当前实际 `common/recovery_data.py` 完全相同，SHA `067642b6a906253d701219bfe5e4bdf52caceda354f8ef056fcdc51372f53221`；实际 incremental_captured_sql 仍执行 `raw = expanded.read_bytes()`。其资源合同只要求宿主可用内存2GiB，而SQL大小会增长；本轮对大 SQL 的有界流式读取尚未安装。因此为交付持续使用的增量恢复，应升级这两台完整130文件STANDARD包，而不是只改来源按钮。
3. 两旧 `recovery_replace.py` 无 epoch 支持，当前 owner 也无 targetBackupEpochPolicies。59 可以按已证明自身物理源加策略；58 没有已确认与当前 r3 实例配对的 MAIN 捕获来源身份，本轮仅升级组件，明确不启用58 epoch。
4. 这满足当前仅57SAFE进行备份的范围：恢复58/59只替换各自物理实例，不会改变57来源链。57自己的覆盖目标已经与57来源共用epoch。未来启用58或59自身捕获来源前，必须先按实际身份/锁原子配对所有模式和覆盖控制，并以当前周期的新FULL起链；不能启动旧控制后继续旧父链。

## 当前真实输入

| 项目 | MAIN58 | MAIN59 |
|---|---|---|
| 当前控制 PID | 2043 | 5885 |
| 控制服务 | spug-main-restore-58-20261104-v3.service | spug-main-restore-59-20261104-v3.service |
| 当前引擎 | engine-packaged-frontend-0c5828a | engine-frontend-9c93449 |
| 完整清单读回 | 127/127文件SHA一致 | 127/127文件SHA一致 |
| 原 control SHA | 501986f203c9855ccc62b3d4563e57e0e365182486c864ebefa38c01f936a242 | db53eb56a638cb591298f1bb38ef8bc303b64ee679ab9639b9329dc923f6e6e1 |
| 原 owner SHA | 4b5a5c6f10e32a71da68190906774387e438e78104f543440b413bbc2fab2363 | 12853a1def82fe0143f8916329638cb7b219fa17856a55b40c367ac988612ce5 |
| 原 active receipt SHA | 2b3e275d1179d1c137bfbea1f46230ca91aeb68bfa37d794b2f5f9f8292d8772 | 73d7eed2d0366aa70efc96ca19f579ddc7f4d36412f7d56d0fe718c9e8010959 |
| 旧 custody 实际复核 | 5代全部PASS | 2代全部PASS |
| 五服务状态 | 全部 running | 全部 running |
| 前端合同 | 原 owner.frontendReadiness 完整保留 | 原无该映射，保持原桥接端点合同 |

以上为只读快照，不替代真正激活前再次核实时PID、精确配置pin、目标语义健康、空闲状态和全部历史。

## 正确的 epoch 与来源绑定

- 两目标 control.sourceConfigurations 只有来源 `intruoyi-57-safe-20261024-v1`，其值是正式来源元数据副本；它不是本机58/59的捕获来源。两个新 control 保持这项完全相等，也不加 sourceEpochPolicies。RESTORE 的 Native.resolve 选择 restoreConfigurations，不调用 source_epoch。
- MAIN59 新 owner 只增加 `targetBackupEpochPolicies[intruoyi-main-59-safe-restore-20261104-v1]`。精确 sourceIdentity 为 `18f689ead7895a6e6e128a6523b6c60c9024b5a5193f7e355569765352158af9`；databaseUuid `a4f03708-cc74-11f1-9cce-0242ac1def16`；sourceLockPath `/mnt/intruoyi-data/backup59-lightweight-20261022/source-locks/source.lock`；建议根 `/mnt/intruoyi-data/spug-backup-epochs/intruoyi-main-59`。两旧SAFE/FAST原capture pins的身份、UUID、MySQL/MinIO完整ID和锁与当前MAIN59逐一一致。根现场未存在、canonical、与登记数据目录无词法重叠；实际完整mountinfo物理重叠门禁须在持锁安装时通过。
- MAIN59 两旧捕获配置的 MinIO 路径仍漂移，禁止本轮启动、改其配置或把它当活动备份源。只将已证明的稳定身份用于目标恢复边界记录。未来启用来源时必须修复其实际完整合同并复用该policy。
- MAIN58 policy 保持未启用；其 UUID `20ca4c6c-cc31-11f1-9b95-0242ac1deb16`、锁 `/var/lib/docker/intruoyi-data/prod-nas-restore-test58-20261020/target-r3/main-backup-restore.lock` 与 SMALL58 完全不同。31条历史连接中还有2个不可选MAIN58旧引用，但未证明它们与当前r3同一来源，因此不能推导新sourceIdentity或声称所有历史均不存在。
- 每个 owner 的旧 sources、targets 以及 frontendReadiness 必须完全相等；仅新 formalModuleDirectory 和59的顶层策略改变。旧配置/回执/clearance及归档不改，不给历史追认epoch。

## 可审阅的部署工具

- `plan_automatic_targets.py`：只读真实包并生成本机 PRIVATE 中精确新 owner/control/receipt 候选；不含 SSH。候选记录统一 `PLAN_ONLY_NOT_DEPLOYED`。
- `install_automatic_targets.py`：默认或 `--prepare-only` 只本机验证；只有未来明确传入单目标 `58 --activate` 或 `59 --activate` 才调用可信 remote。此分工只运行了 prepare-only。
- `automatic_targets_install_script.py`：供审阅的远端模板，使用候选精确pin，保留旧全部包与targets/sources。激活顺序为：原receipt custody→本机来源锁与host资源锁→无worker/预约→全部容器/挂载/fstab/历史保全→原语义健康→新130包与精确候选→59持锁初始化及replacement_value物理门禁→实际新包构造到首次DB前边界、原历史空闲及selected-target准入→旧receipt字节归档→排序晚于全部既有dropin的新systemd配置→仅重载当前目标控制→精确argv/PID/FD、实际HTTP准入与构造健康复核→业务/历史保全→原子active receipt发布→完整扩展custody verifier。
- 构造验证真实调用 MinimalData.__init__，在 database_uuid 边界停止，核原frontend profile、实际read-only native invocation及三项语义HTTP；不是手动填充对象后宣称构造通过。原健康预检另在新文件写入前执行。
- 新包/候选准入任何失败保留暂存代次，不能循环重跑同代次或自动降级恢复。若控制激活后验证失败，helper报实际失败，不假造PASS或覆盖旧回执；父任务需基于归档unit/receipt与当前真实PID处理，不自行自动rollback。
- 真实PASS输出计划为 `automatic-target-installation-58.json` / `-59.json`，以及对应 `automatic-target-installation-custody-58.json` / `-59.json`。`extend_verified_custody` 只接受实际PASS及匹配全部候选pins的回执；PLAN_ONLY明确拒绝。实际成功后由独立current选择指向新代次，保留原 allocator-selected-installations 及恢复367/372时证据，不重写历史。

## 验证与限制

- 实际只读：58/59当前控制与原包全部成员、五服务完整ID/运行态；59两个捕获身份与目标配对；58既有5代、59既有2代receipt custody，所有原sources/targets与pins完整通过。
- 计划生成：固定0d44578的130文件STANDARD全成员SHA、编译、manifest摘要通过；两候选均保持旧sources/targets与源57metadata，58无epoch、59目标单项policy。
- 工具检查：真实运行 `install_automatic_targets.py --prepare-only`，并通过Python audit hook禁止任何subprocess/socket/connect后再次执行仍成功；模糊无目标activate和prepare/activate同时出现均拒绝；PLAN_ONLY扩展custody被拒绝；全部helper与内嵌远端/构造脚本UTF-8编译通过。
- 未执行 `--activate`，没有新增远端文件、初始化58/59epoch或重载服务。远端激活模板目前只有静态/编译/准备路径验证，实际新组件构造、目标历史准入、stage及activation仍须由父任务审阅后按门禁真实执行，不能据此宣称安装完成。
- 只读过程中两个检查载体错误已明确停止：先误定位控制模块于common而非package实际control目录；随后59旧systemctl不支持--value，改为解析MainPID=。没有将失败计为通过或改变服务。
- 私密证据：`automatic-target-closure-{58,59}.private.json`、`automatic-target-custody-{58,59}.private.json`、`automatic-target-epoch-59-binding.private.json`、`automatic-target-candidate-{58,59}-0d44578.private.json`。公开候选仅pins/状态，原配置和环境不提交。
