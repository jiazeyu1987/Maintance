# 指定 Codex 任务执行方式审查

证据快照：2026-09-20 12:48 +08:00。目标任务仍在运行，后续结果可能变化。
审查范围：原始对话授权、任务记录、当前实现和本地运行证据；未访问服务器，未运行备份/恢复，未修改产品代码。

## 结论
目标任务在实现并真实验证测试服按钮化备份、隔离恢复演练和受控恢复。用户后续明确要求开发、E2E、一次成功备份/恢复，以及每次备份前删除上次备份，因此不能按最早的“方案介绍”认定后续执行越权。

总体流程方向正确，但当前实现存在实质缺陷，验证不足，不能认定完整恢复能力或六个原始里程碑完成。当前一次新的隔离演练正在进行，不应强行打断；其结束后仍需先处理下列问题，再考虑受控覆盖恢复。

## 当前在做什么
- 已成功封存 FULL 备份 `20260920-004254`，operation `2951d7fb-4825-4595-9487-d818ead370b5`，报告结果 `INTBK-0000`。
- 之后连续修复：缺少 mysqlbinlog 的前置检查、陈旧启动探针、长任务超时、镜像探测字面换行、大 dump 校验窗口、PowerShell 模块私有函数不可见。
- 上轮演练 `461d2b3f-1a9b-49e6-b6b8-6dd6ec2a4b83` 从 08:58 运行至 11:34，报告 backendHealth/frontendHttp200/loginReachable/fileDownloadSample 均 pass，但最后证据摘要调用 `ConvertTo-BackupBashSingleQuotedString` 不存在，整体 fail。探针通过不等同于完整业务验收。
- 修复提交 `f1fc8f434` 后，新 operation `2ebe8812-bb45-43a5-9757-2e1b361e711d` 于 12:02 发起，当前记录 running；12:43 对话执行记录仍在确认 MySQL 导入进程。
- 没有找到本轮成功恢复演练报告或受控覆盖恢复成功证据。历史登录阻塞已被 08:56 的“已登录”和之后真实执行取代。

## 已确认问题

### P1：通用备份入口无条件清空仓库，破坏增量链
`BackupNow.psm1:100` 在 FULL/INCREMENTAL 分支之前调用 `Invoke-BackupOpsRemoteRepositoryReset`，随后才在 109 行检查增量工具。`FileOps.psm1:555` 遍历根目录，删除所有匹配日期格式的备份目录，以及 object-store 和 .restore-stage，没有按“上一份”、来源环境或恢复链引用筛选。

`MySqlOps.psm1:706` 的增量逻辑需要从同一仓库查找成功父点，目录为空便在 726 行阻断。因此，在无并发新写入的正常情况下，选择 INCREMENTAL 会先删除基线，再因找不到父点失败；即使缺少 mysqlbinlog，也是在删除之后才发现。此结论来自当前源码路径，未执行破坏性复现。

用户明确授权“备份前删除上一次数据”，所以删除动作本身不是无授权；但把它扩成通用入口的全仓清理，与仍然提供的增量功能不相容。应明确限定一次性测试全量重置模式，或按完整链管理保留；不得静默把增量变成全量。若仍要求每次先删旧包，则必须明确只支持独立 FULL，并接受新包失败时旧恢复点已不存在的结果。更安全的常规保留方式须在改变该明确要求前与用户对齐。

证据：
- `E:/IntRuoyi/IntRuoyiBackend/script/backup-ops/scripts/modules/UseCases/BackupNow.psm1:100`
- `E:/IntRuoyi/IntRuoyiBackend/script/backup-ops/scripts/modules/Infra/FileOps.psm1:555`
- `E:/IntRuoyi/IntRuoyiBackend/script/backup-ops/scripts/modules/Infra/MySqlOps.psm1:725`

### P1：延长超时缓解症状，未消除控制进程中断后的停服风险
记录已证实两小时超时曾杀掉备份脚本，留下 .creating 半成品和停止的 backend/frontend。当前 `RuntimeControlCommandExecutorImpl.java:119` 仍在超时时终止进程，仅把时间改成 12 小时；`BackupNow.psm1:131` 的服务恢复依赖被终止脚本的 finally。进程强杀不能依赖脚本 finally 完成恢复。

应验证控制台重启、超时、SSH 断开等失败路径，并由持续存在的执行器/恢复责任方对真实运行态、停写租约和最终状态负责。不得只因本次小于 12 小时就宣称故障恢复设计完成。

### P2：失败报告与 operation 持久化状态不一致
`20260920_085809_rehearsal_fail.report.md` 已明确 fail，但同一 operation JSON 在本次审查时仍为 running，前一轮 blocked 演练也有类似现象。服务源码 `getOperations()` 直接返回存储记录，日志读取接口才调用 `reconcileTerminalOperationStatus`；补偿依赖读取日志，并不保证列表状态主动收束。

尚未证明具体是哪次控制台重启造成状态遗失，不能据此断言仍存在两个实际恢复进程；但不能只读 JSON running 就继续报告“还在执行”。应按任务归属核对执行器、报告和最终服务状态，持久化一致终态，再验证与发布/恢复的互斥。

### P2：新增测试偏重源码字符串，缺少能提前发现问题的执行测试
`BackupNowCleanupContract.Tests.ps1:14` 只断言清理调用位于工作目录创建之前，并检查源文本包含目录名及 12 小时常量；没有检验 INCREMENTAL 的父链被保留、失败前置条件不删除有效备份、删除范围归属。
`RehearsalModuleContract.Tests.ps1:6` 只检验源码存在函数定义，不执行模块中的证据摘要生成路径。真实演练耗时两个多小时后才暴露辅助函数不可见，说明“静态检查已通过”不足以验证模块组合行为。

应先补模块加载/调用与证据生成、清理策略及中断收束的行为测试，再运行昂贵的真实全链验证。必须保留真实恢复验收，不能以静态检查或测试替身代替。

### P2：共享主工作区反复整套编译重启，隔离不足
对话记录中多次从 `E:/IntRuoyi/IntRuoyiBackend` 执行 `restart-int-ruoyi-local.ps1 -Component full`，并承认整仓编译会经过其他并发任务的代码。任务规则要求隔离工作区和不干扰其他任务资源；即使将这些动作视为本机调试而非正式发布，共享源码和控制台也使运行版本与进程归属更难证明。

不能仅凭本地重启认定已违规发布服务器；问题是当前执行隔离不足，应在任务专属工作区验证改动，并明确长期控制台的恢复路径与来源提交。

## 做对的部分
- 使用真实页面触发操作，通过 operation、报告、manifest 和 checksum 追踪执行结果。
- 将演练和受控恢复候选分开，未把 NOT_RUN 或失败演练伪装成 PASSED。
- 没有把 .creating 半成品用于覆盖恢复。
- 真实失败有报告、有针对性修复和提交；没有把全量备份成功宣称为全量恢复成功。

## 建议的下一顺序
1. 让当前已启动的隔离演练正常收敛，核对其实际终态及测试服服务状态；本审查不干预该任务。
2. 修正全量重置与增量链冲突，补充失败前置检查、真实删除范围与进程中断的行为验证。
3. 收束历史 running 状态，确认共享环境没有相冲突的发布/恢复操作。
4. 演练 PASSED、目标指纹/链摘要/保护点及互斥均通过后，才能做已授权的受控恢复。
5. 六里程碑还需真实增量链、中间点恢复、升级/降级/换机支持矩阵、持续运行和 RTO/RPO 证据；当前不能一并宣称完成。

## 审查验证与限制
- 已交叉核对对话原始用户指令、任务文档、当前源码及本地报告/operation 文件。
- 没有重跑产品测试，没有新建远程连接，没有执行删除、停服、备份或恢复。
- 运行数据属于时间快照；源码缺陷与建议是审查结果，不是本任务完成的修复。
- 凭据未写入本报告。

## 第二轮复审：2026-09-20 14:50–14:56 +08:00

### 总体判断
目标任务仍在真实推进全量恢复演练，但没有把上次整改作为完整执行顺序落地。它继续采用“完整大数据量演练 -> 最后遇到模块错误 -> 增加一个导出/字符串测试 -> 主工作区打包重启 -> 再次演练”的方式。新修复对当前异常有针对性，但缺少对报告生成调用链的完整验证，主要安全缺口仍未关闭，不能放行覆盖恢复。

### 整改消息送达核对
- 前次工具返回成功只能证明提交成功；本轮进一步检查精确 threadId 的 rollout，确认 12:55:43 的 `function_call_output` 包含完整 `<codex_delegation>` 指令及本审查线程来源。
- 因此消息已进入目标执行上下文，不只是“可能仍在排队”。普通 role=user 消息列表未显示该消息，是消息载体不同，不能据此否认送达。
- 在已检查的后续执行中，未发现按八项整改重排任务、阅读完整审查报告或切入隔离 worktree 的证据；原 task/execution-log 仍停留 M12，未同步本轮 M13 异常和整改清单。
- 不推断其主观意图，只评价可见行为与代码。

### 当前真实状态
- operation `2ebe8812-bb45-43a5-9757-2e1b361e711d` 的演练从 12:02:53 运行到 14:30:12，约 2 小时 27 分钟，整体 fail。
- 报告 backendHealth/frontendHttp200/loginReachable/fileDownloadSample 为 pass，但证据写回调用 `Get-BackupOpsRemoteFileText` 不可见。该报告不能作为 PASSED 恢复证明，也不能把 loginReachable 探针等同于完整业务登录流程。
- 14:38 提交 `70d5b8792`，只修改 DockerOps.psm1 的导出列表和 RehearsalModuleContract.Tests.ps1，合计 2 个文件、8 行新增、1 行删除。
- 14:43 从 `E:/IntRuoyi/IntRuoyiBackend` 执行 `mvn -pl yudao-server -am -DskipTests package`，并准备替换本地 48081 后端进程。最新可见执行正处于打包及进程检查阶段，不是还在导入数据库。
- 审查时两轮已失败演练的 operation JSON 均仍 running；没有新的演练成功或受控恢复成功报告。

### 第一轮问题复核
| 问题 | 本轮结果 |
| --- | --- |
| 通用清理先删除父链，导致增量失败 | 未修复：BackupNow.psm1:101 仍在分支前调用仓库重置，增量工具检查仍在 109 行之后 |
| 超时强杀与服务恢复责任不闭合 | 未修复：执行器仍为 12 小时 waitFor，超时 terminateCommandProcess，服务恢复仍依赖脚本 finally |
| 失败报告与 operation running 不一致 | 仍可观察到：12:02 和 08:58 两轮均已生成 fail 报告，记录仍 running |
| 静态字符串检查代替调用链行为测试 | 有一点改进：额外执行 Import-Module + Get-Command 检查导出成功；仍未实际执行完整证据生成路径 |
| 共享主工作区编译重启 | 仍存在：14:43 的 Maven package 工作目录是主工作区，当前有大量其他任务 DCC/MES 未提交修改 |

### 新增明确问题：仅脚本修复却重新打包 Java
本轮提交没有 Java 代码变更。RuntimeControlOperationAction.java:50 指定演练脚本 `script/backup-ops/scripts/backup-ops.ps1`；RuntimeControlCommandExecutorImpl.java:95 从配置 repoRoot 解析外部脚本并启动新进程；backup-ops.ps1:324 从磁盘逐个 `Import-Module -Force`。

按这条 Windows 执行链，外部模块修复应在下一次新脚本进程启动时加载，不需要仅为该变更重新构建 Java Jar。若实际运行指向另一脚本副本，应先核对当前 repoRoot、入口绝对路径、脚本/模块哈希，再以受控方式同步相应运行产物；未见本轮有必须 Java 打包的依赖证据。反复全 reactor package 会额外消耗时间，混入并发源码，并增加共享控制台重启和状态遗失风险。

### 为什么本轮方式仍不正确
前一轮 08:58–11:34 因私有转义函数不可见失败，本轮 12:02–14:30 又因文件读取函数未导出失败，连续两次耗时全量恢复在同一报告生成阶段触发同类问题。新增正则只验证导出名字出现；Get-Command 的导出可见性检查是进步，但不足以证明 Rehearsal 模块实际调用、远端摘要读取、manifest/chain 绑定和报告写回完整执行。

### 当前建议
1. 当前数据恢复阶段已结束，不应立即再开始第三次同类全量重放；先核对残留执行器、报告和服务状态并收束失败记录。
2. 在隔离工作区对“从 Rehearsal 模块实际调用到证据报告写回”的整条路径做行为验证，连同上次清理/增量和中断状态问题一起修复。验证替身只可用于局部控制流测试，不能替代真实恢复验收。
3. 明确实际脚本路径和加载方式，按变更内容决定是否重启/构建，避免为外部脚本变更打包 Java。
4. 前置与行为测试通过后，再进行一次完整真实演练；既有 fail 报告不得补写成 PASSED，只有新验证完成才能产生新的有效恢复证据。
5. 受控恢复必须继续等待清理链、互斥、终态、保护点及目标指纹等门禁通过，不因四个探针 pass 提前放行。

### 本轮证据
- `D:/IntRuoyi-BackupOps/logs/202609/20260920_120253_rehearsal_fail.report.md`
- `D:/IntRuoyi-BackupOps/logs/202609/20260920_085809_rehearsal_fail.report.md`
- `E:/IntRuoyi/IntRuoyiBackend/runtime/runtime-control/2ebe8812-bb45-43a5-9757-2e1b361e711d.json`
- `E:/IntRuoyi/IntRuoyiBackend/runtime/runtime-control/461d2b3f-1a9b-49e6-b6b8-6dd6ec2a4b83.json`
- 提交 `70d5b8792`、对应模块/测试现状、目标任务 12:55 指令与 14:34–14:45 执行记录。
- 本轮为只读审查，未重新运行产品测试、未操作服务器或目标任务进程；失败与修复结果均按本地真实记录核对。

## 第三轮复审：2026-09-20，15:58 后核对

### 当前状态与结论
目标任务现名“备份恢复”，应用状态为 idle，15:57 最新答复交付了前置整改分支。它已经按纠偏方向采取实质行动，执行方式明显改善；但这只是部分前置整改，不是用户要求的“点击按钮完成备份恢复”已成功。

- 15:04 用户在原任务直接列出六项整改，任务随后明确暂停新的真实演练和覆盖恢复。
- 15:21 建立独立 worktree `D:/IntRuoyiWorktree/backup-restore-remediation/backend`，分支 `codex/backup-restore-remediation-20260920`。
- 15:51 提交 `e00d22cc7`（修复备份链和演练状态收束），实际涉及 5 个文件。
- 15:57 任务停止，报告 ready_for_closeout；尚未合并、部署或执行新的真实演练。
- `git merge-base --is-ancestor e00d22cc7 int_main` 返回 1，证明整改提交尚未进入主线；worktree 状态干净。
- 最新真实恢复报告仍是 14:30 的 fail；历史 operation JSON 仍 running。不能用尚未部署的代码宣称现场状态已修复。

### 做法已经改正的部分
1. 不再重复启动耗时恢复来逐个暴露问题，也没有人工改历史报告为成功。
2. 真正在独立 worktree 编码、验证并提交，没有继续修改共享主工作区的这些实现文件。
3. `BackupNow.psm1` 将 reset 放进 FULL 分支，INCREMENTAL 不再无条件清空父链和 object-store，关闭了第一轮明确指出的增量必然失去基线问题（代码级，未真实链验收）。
4. 增加实际调用 `Write-BackupOpsRehearsalEvidence` 的 Pester 测试，从纯文本检查进步到验证本地证据产物及调用顺序。
5. `getOperations()` 读取已注册日志并更新可识别的终态，使列表读取可收束旧 running；执行器返回 timeout/interruption/cleanup failed 时持久化为 unknown，保留既有写保护。
6. 已核对 Windows 的实际 repoRoot 为 `E:/IntRuoyi/IntRuoyiBackend`，理解 PowerShell-only 变更无需 Java 构建，而新 Java 状态逻辑需要后续部署。

### 验证证据核对
- 15:28 `RuntimeControlServiceImplTest`：68 tests，2 failures；15:32 同类 68 tests，0 failures，形成有效行为 RED/GREEN。
- 15:40 Surefire XML：执行器 7 tests + 服务层 68 tests，failures/errors/skipped 均 0；共 75 个 Java 定向测试通过。
- Pester 多轮执行结果通过，新增证据调用链测试确实执行真实函数；没有把本地测试替代真实恢复验收。
- 增量保护新增测试依然是源码正则及位置检查，没有实际运行 FULL -> INCREMENTAL 并证明链与对象可恢复。
- 证据生成用例只验证成功路径，测试内重定义文件读取与 SSH/传输函数；作为局部单元测试可以使用这些替身，但它不证明正式模块导出集成，也不覆盖读取/摘要/传输失败时不得出现有效 PASSED 的要求。

### 仍应补齐的问题

**P1：FULL 清理仍未限定到精确授权集合。**
生产修改只是把 reset 包在 FULL 条件下。FileOps 的实现未改，仍遍历日期目录并删除 object-store/.restore-stage；没有新增本次显式重置选项、来源归属/链引用/正在演练占用检查，也没有先完整验证删除集合再执行。全量入口在新工作目录、当前镜像标签与后续工具检查前即调用 reset。不能把“增量不再删除”扩大为“备份清理整体安全”。用户要求删除上一份数据，不等同于自动删除所有历史恢复链。

**P1：UNKNOWN 分类不是完整中断恢复机制。**
新提交没有修改命令执行器和备份脚本的服务恢复逻辑，只在服务层匹配异常文本，将 timeout/interruption/cleanup failed 标记 unknown。已有测试证明 timeout 分类正确；未证明进程强杀后自有服务恢复、远端执行器/子进程退出、控制台进程崩溃后恢复责任、没有终态日志时的状态收束。控制台崩溃可能根本无法进入当前 catch；getOperations 缺日志或缺终态时依旧保留 running。写保护是进步，不能等同于完整生命周期已完成。

**P2：证据生成测试仍欠缺失败分支与正式加载集成。**
新增一个成功用例直接在 Rehearsal 模块作用域定义 `Get-BackupOpsRemoteFileText` 等替身，会绕过之前实际发生的跨模块可见性问题。应在正式模块加载顺序下验证导出与真实调用衔接，并覆盖 digest/manifest 错误、远程发送失败和不完整报告不能成为恢复授权等行为，再开展下一轮昂贵演练。

**交付缺口：整改尚未进入运行态，前端按钮闭环未验收。**
本轮 15:04 后没有新浏览器操作记录，没有新的备份/演练/恢复 operation。作为先整改后演练的阶段，这是正确顺序；但不能当作按钮功能交付完成。任务仍需完成代码审查、集成后验证、部署新运行控制台，再通过真实页面操作验收。

### 按用户明确要求的下一验收顺序
1. 关闭 FULL 精确清理、证据失败路径和中断责任缺口，并修正对应完成声明。
2. 安全集成任务提交，验证合并结果并部署需要更新的 Java 状态逻辑；先在页面操作列表验证历史终态能按真实日志收束。
3. 用 Playwright 登录真实页面，通过“立即备份”及必要选项发起备份，核对页面进度、参数和结果；不得用手工 SSH、脚本或 API 提交替代按钮。
4. 从页面选择有效备份包并点击“恢复演练”，取得当前目标绑定的真实 PASSED。
5. 保护点/空目标、容量、互斥等全部通过后，再点击“恢复数据”并确认，核对页面最终结果、实际业务数据和文件一致性。
6. 清理本任务资源并完成文档收尾。当前只有前置整改阶段，用户的最终目标尚未完成。

### 证据入口
- `D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260920-backup-restore-remediation/task.md`
- `D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260920-backup-restore-remediation/execution-log.md`
- `D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260920-backup-restore-remediation/verification-report.md`
- `e00d22cc7` 实际 diff、独立 worktree 的 Surefire XML 和目标任务最后答复。
- 本审查未重跑产品测试、未干预目标任务或服务器。

## 第四轮复审：2026-09-20 22:10–22:15 +08:00

### 当前结论
目标任务正在按用户要求的前端按钮流程执行，整改方式较前三轮有实质改善。新的 FULL 备份已成功，随后页面触发的恢复演练仍在运行；没有受控恢复成功证据。不能继续把“还没部署修复”作为当前结论：e20b77d50 已部署到隔离运行态，但尚未合入主线。

本轮新发现是 Windows detached runner 产生非 UTF-8 的操作日志，与服务层 UTF-8 读取合同冲突；该缺陷直接关系页面操作状态读取，必须在完整按钮验收前关闭。

### 实际按钮证据与授权
- 17:13:29 Playwright 工具输出包含 `page.getByRole('button', { name: '立即备份' }).click()`，对话框展示 FULL 选项；17:13:54 输出包含点击“确认执行”。
- FULL operation `87da58cc-96e0-4b00-b631-f6b191071024` 当前状态 succeeded，参数为 targetEnvironment=test、backupKind=FULL，备份点 `20260920-171349`。任务已记录远端正式目录、manifest、对象计划、dump 和 SHA-256 校验。
- 用户在原任务于 21:05 明确回复“允许使用芋道源码”；随后使用该租户进行本次恢复写入验证符合该追加授权，不应再按默认租户规则判为越权。
- 21:09:33 Playwright 输出包含点击“恢复演练”；21:10:19 输出包含选择 `rehearsal:20260920-171349` 并点击“确认执行”，页面出现“恢复演练 dispatched”。因此这次按钮路径有工具证据，非仅文档自述。
- 新演练 operation `cb1cfa1f-48bc-49bc-8cdd-087b7bef9847` 于 21:10 创建；22:15 JSON 仍 running，本机 runner/子脚本 PID 27760、63684 仍存在。目标任务最近的远端只读记录显示 21:40 已启动演练 MySQL，22:00 容器仍 running；本审查没有额外访问服务器，不将“进程存在”扩大为完整恢复已成功。
- 尚无本轮新的成功演练报告，尚未点击“恢复数据”。当前继续观察同一 operation、等待真实终态是正确做法。

### 本轮已修正的实现
- e20b77d50 将全量预清理收窄到当前 backupId 的 `.creating` 目录，要求 `.backup-ops-owner.json` 标记匹配；不再全仓删除成功点、object-store 和恢复阶段目录。
- 证据报告先写 `.uploading`，远端发布成功后才形成本地正式报告；补充模块加载、读取/传输失败测试。
- Windows 备份/演练/恢复使用 detached PowerShell runner，Java 调度不再用 12 小时同步等待直接终止整段脚本。
- 在隔离 worktree 中构建并运行新 Java，后端 48082、实际前端 8083；运行 repoRoot 指向整改 worktree。此次 Java 执行器有实际变更，构建是必要的，不同于第二轮的 PowerShell-only 重打包。
- Surefire XML 确认执行器 8 tests、服务层 68 tests，全为 0 failures/errors/skipped，共 76 tests。任务记录 Pester 22 tests 通过。
- `git merge-base --is-ancestor e20b77d50 int_main` 返回 1，尚未合入主线；在隔离运行态验收后再集成是合理阶段顺序。

### 新发现 P1：操作日志编码违反页面读取合同
`RuntimeControlCommandExecutorImpl.java:230` 的 Windows runner 用 `>> $LogPath 2>&1` 追加输出，254 行起明确启动 `powershell.exe`，没有为重定向输出设置显式 UTF-8。日志前置内容由 Java UTF-8 写入，后续追加方式与其不一致。

本轮直接读取实际文件原始字节并严格 UTF-8 解码，结果为：
- `state/logs/87da58cc-96e0-4b00-b631-f6b191071024.log`：1997 bytes，在 offset 643 失败（invalid continuation byte），含 519 个 NUL 字节。
- `state/logs/cb1cfa1f-48bc-49bc-8cdd-087b7bef9847.log`：643 bytes，在 offset 543 失败（invalid start byte），含 31 个 NUL 字节。

`RuntimeControlServiceImpl.java:414` 对 running operation 使用 `Files.readString(logPath, StandardCharsets.UTF_8)`，读取异常会在 416 行抛出操作存储错误。因此当前 active rehearsal 的日志已不满足列表读取前提，存在页面操作列表/状态轮询失败的确定代码路径。审查未新开浏览器重现 HTTP 错误，应区分“已确认日志编码缺陷”和“尚待页面复验的呈现结果”。本审查没有尝试默认编码/替换字符来掩盖读取失败，也未改写原日志。

建议由执行器统一写出 UTF-8，保留受影响日志原始证据；增加带中文输出的真实 Windows runner 测试，并验证 `getOperations()` 和页面日志读取成功。仅看 JSON succeeded 或后台进程不能证明前端用户能正常看结果。

### 新发现 P2：operation 文件未原子发布
同一执行器 223–226 行先写临时文件，却又直接 WriteAllText 覆盖正式 operation JSON，随后删除临时文件，没有以原子替换方式发布。并发页面读取可能撞到部分 JSON，崩溃时也可能留下不完整状态文件。该问题是代码风险，本轮没有观察到具体 JSON 损坏。

detached runner 已改善 Java 生命周期耦合，但独立 runner 自身被终止/主机重启时如何恢复 running、确认远端写入者及安全收束，仍需要明确验证，不能仅用成功子进程测试宣称全部中断场景通过。

### 当前正确的下一步
1. 保持本次正常运行中的演练，不因审查发现重启或强杀自有执行器；继续核对真实阶段、终态报告和服务状态。
2. 将日志 UTF-8 和 operation 原子写入列为按钮验收缺口，在隔离代码与测试中修复；先证明前端列表、进度和日志可以稳定读取。
3. 演练确实 PASSED 且链摘要、目标指纹、保护点、容量与互斥门禁通过后，再从页面点击“恢复数据”，验证数据、文件和最终页面结果。
4. 只有真实按钮完整闭环、合并结果验证和本任务运行态/资源收尾通过后，才标记总体完成；当前仍为在执行中的演练。

### 本轮审查边界
仅只读检查目标对话、代码、测试 XML、本地 operation、进程及日志字节；未重跑产品测试，未访问服务器，未触发任何按钮或改动运行资源。之前三轮结论作为历史快照保留，不覆盖本轮进展。

## 追加深入审查：2026-09-20 22:21 后，基线 e20b77d50

以下为新增的代码级问题，不重复第四轮日志编码和状态文件原子写入问题。审查开始时整改 worktree 干净、HEAD=e20b77d50；未执行覆盖恢复或破坏性复现。

### P1：演练成功路径会使自己的 manifestDigest 失效
调用顺序明确为：
1. `Rehearsal.psm1:357` 调用 Write-BackupOpsRehearsalEvidence；该函数在 173–182 行计算并记录当前 manifest.json 的 SHA-256。
2. 紧接着 358 行调用 Set-BackupOpsRehearsalVerificationState。
3. `DockerOps.psm1:1941` 修改同一 manifest 的 rehearsalStatus，1942 行写入新的 lastRehearsedAt，1956–1959 行重新序列化并上传覆盖原文件。
4. `RuntimeOpsCandidateServiceImpl.java:483` 为页面候选重新计算修改后 manifest 的 SHA-256，366 行要求它与旧报告 manifestDigest 完全相等。

因此按当前正常成功路径，报告绑定的是修改前的 manifest，候选读取的是修改后的 manifest，即使数据恢复和探针都通过，CONTROLLED_RESTORE 仍会因摘要不一致阻断。这是跨模块调用顺序的确定性矛盾，局部证据生成成功用例没有覆盖“写报告 -> 更新状态 -> 页面重新列候选”。

修正方向：保持备份 manifest 不可变，将演练状态、时间及验证结果移到独立证据中；让生产者和候选消费者使用相同不可变对象。不得删除或放松 hash 比对来使按钮可用。

### P1：恢复前“保护快照”只保存配置，无法保护被覆盖数据
`DockerOps.psm1:1155` 的 New-BackupOpsPreRestoreSnapshot 完整实现仅下载 runtime.env 与 docker-compose.yml，再生成 snapshot.json；没有数据库导出、对象数据副本、存储快照或可恢复的数据保护点。

`RestoreData.psm1:270` 将它作为“pre-restore 保护快照”，取得 SnapshotId 后在 275 行停服务、278 行导入 MySQL、281 行恢复对象。该快照本身不能找回恢复前现有的业务数据与文件；较早生成的 FULL 也不自动等于覆盖前最新的一致保护点。

修正方向：覆盖前创建并验证数据库与对象共同一致的恢复保护点；若使用空目标模式，必须有当前目标确为空且不覆盖业务数据的明确证据。仅配置副本不得作为数据恢复放行门禁。

### P1：演练支持增量链，但“恢复数据”仍走单个 FULL dump
`DockerOps.psm1:2006` 的演练路径先导入 candidate.baseBackupId 的 FULL，再在 2007 行 Replay-BackupOpsMySqlBinlogChain 到所选目标点。

而正式受控恢复路径存在两处不同：
- `DockerOps.psm1:993–1009` 的 Get-BackupOpsRestoreCandidates 要求所选 BackupId 自身目录有 mysql/<database>.sql.gz，否则剔除；正常增量点主要包含增量段，并不重复保存完整 FULL dump。
- `RestoreData.psm1:278` 将所选 BackupId 直接传入 Import-BackupOpsMySqlDump；`MySqlOps.psm1:1217` 构造该 ID 下的完整 dump 路径，受控恢复流程没有调用整链重放。

因此“增量不再删父链”和“增量演练可能通过”不等于“恢复数据按钮支持该增量恢复点”。当前实现会拒绝正常增量候选；即便放松候选检查，也仍没有正确整链恢复执行路径。不能靠补放一个全量文件或隐藏增量选项掩盖合同差异。

修正方向：演练与受控恢复共享同一份经校验的 FULL+增量恢复计划，差异仅为目标槽位、保护点及执行授权；对中间点和最新点分别做真实按钮验收。

### P1：目标指纹比较的是两份备份元数据，不是当前目标环境
`Rehearsal.psm1:186–187` 从备份 manifest 的 targetEnvironment、targetHost、deploy.imageTag 拼出 targetFingerprint；`RuntimeOpsCandidateServiceImpl.java:454–463` 同样从同一备份 manifest 重建指纹，再与报告字符串比较。这里没有采集当前目标主机身份、实际 schema、数据库/对象存储版本或运行镜像摘要。

`RestoreData.psm1:77–82` 确实额外读取当前 IMAGE_TAG 并做相等校验，因此不能说完全没有现场检查；但标签相同无法证明同 IP 换机、数据库结构漂移、存储/配置变化仍与演练目标相同。当前 targetFingerprint 不能承担设计中“绑定当前恢复目标”的职责。

修正方向：在预览和执行前获取目标实际身份与兼容性指纹，绑定当前演练证据；目标变化后将候选置为 STALE/阻断并要求重新验证。元数据自洽不等于现场兼容。

### 尚未作为本轮已确认缺陷的范围
已看到本机 `Global\IntRuoyi-BackupOps` mutex，覆盖 backup-now、backup-scheduled、rehearsal、restore-data；因此不作“完全没有互斥”的结论。跨控制台、跨主机、发布和应用回滚的共享环境租约仍需进一步核验，本轮不以单一目录未搜索到锁就断言全系统没有保护。

### 放行意见
当前正常演练可继续收束并保留真实结果；在上述证据绑定和覆盖前数据保护等缺口关闭前，不应执行受控覆盖恢复。它们是源码审查发现，尚未在本轮通过破坏性实验复现，更没有观察到实际数据丢失。

## 第二次追加审查：2026-09-20 22:30 后，基线 e20b77d50

以下四项是本轮新确认的代码路径缺口。未执行恢复、回滚、并发操作或破坏性复现，不声称已发生数据事故。

### P1：对象完整性校验晚于数据库破坏性覆盖
`RestoreData.psm1:278` 先导入数据库，281 行才恢复对象。`MySqlOps.psm1:440–451` 明确构造 DROP DATABASE / CREATE DATABASE 与导入命令，565–571 行按该顺序执行。`ObjectOps.psm1:1212–1243` 在对象恢复阶段才读取对象清单、检查 SHA-256、读取仓库对象并校验实际内容。

恢复前候选检查仅证明必要文件存在和部分元数据合格，`RestoreData` 未在数据库覆盖之前调用已有 Test-BackupOpsObjectBucketIntegrity。若备份对象已丢失或损坏，当前流程可能先替换数据库，再发现附件无法恢复，留下数据库与对象不一致的现场。先前演练通过不能代替此次覆盖前对实际载荷的完整检查。

修正方向：在任何 DROP/覆盖动作之前完成整个恢复集的数据库、对象、配置和依赖载荷校验，并固定执行计划和仓库引用；不能只逐阶段发现下一部分不可用。

### P1：破坏性恢复失败后没有持续环境隔离
`RestoreData.psm1:314` 统一转入 New-RestoreDataFailureResult，默认状态 fail，主要写报告和通知；没有按是否已经执行 DROP/导入/对象覆盖区分“未写入失败”与“现场部分恢复”。外层 `backup-ops.ps1:374–377` 不论是否已进入破坏性阶段都会释放本机 mutex。

Windows detached runner 在 `RuntimeControlCommandExecutorImpl.java:236–239` 将非零退出或异常标为 failed。`RuntimeControlServiceImpl.java:1079–1098` 的持续写保护只拦 unknown，不拦上述部分恢复的 failed。因此一旦恢复中途失败，下次操作不会因“目标处于不一致恢复现场”而持续被该门禁阻断；普通 restart/rollback 可能重新启动未恢复完整的环境。

修正方向：持久化破坏性执行阶段及独立的环境隔离/恢复责任状态，故障后保持写保护，直到确认远端写入者退出、数据一致并完成明确处置。禁止把“任何失败都启动服务”当作修复，也不能仅靠进程存活期 mutex 承担故障后隔离。

### P1：应用回滚没有进入与数据恢复相同的互斥范围
`backup-ops.ps1:338` 的互斥动作集包含 backup-now、backup-scheduled、rehearsal、restore-data，却遗漏 rollback-app。同一入口仍在 361–362 行执行 RollbackApp use case；`RollbackApp.psm1:143–146` 会更新 IMAGE_TAG 并重启 backend/frontend。

Java service 使用可并发执行的 operationExecutor；环境门禁只检查 unknown，不检查活动 running 的备份/恢复。对于其他参数和候选均有效的同目标回滚请求，这条实现路径没有与正在进行的数据恢复共享互斥，存在恢复数据库期间回滚程序并启动业务写入的风险。

这比上一轮“跨环境锁尚待核验”更具体：本轮已确认同一个 PowerShell 入口内 rollback-app 被明确排除。仍不据此推断所有部署子系统均无锁。

修正方向：备份、恢复、回滚及会修改同一目标运行态的操作必须共享目标环境级互斥/租约，在服务端原子取得执行权；前端按钮禁用只能作为辅助。

### P1：UNKNOWN 写保护会被操作历史数量挤出
`RuntimeControlServiceImpl.java:1095` 使用 `operationStore.listLatest(200)` 搜索 unknown。`RuntimeControlOperationStore.java:65–69` 是先按所有状态文件修改时间排序并截取 200 条，再做环境和状态过滤；它不是查询全部未解决的 unknown。

另外 `executeAction` 在 209–224 行先保存新的 operation，228 行才运行门禁，失败后又保存 blocked。因此即使只是后续被阻断的尝试，也会产生更新的历史记录。当未处理 unknown 落到最近 200 条之外时，该方法返回 null，写保护未经人工确认便失效；其他环境的新操作同样能占用这个窗口。

修正方向：环境安全状态必须由独立持久记录或所有未解决操作的完整查询决定，不能复用 UI 历史分页。增加“超过 200 条后 unknown 仍阻断”及“blocked 尝试不能解除隔离”的行为测试。

### 本轮排除项与审查边界
已确认当前数据库恢复确实先 DROP/CREATE，不能再提出“导入后残留旧表”的未经证实问题；当前主对象恢复路径使用 `mc mirror --overwrite --remove`，不能仅凭其他归档辅助路径缺少 --remove 就认定主路径必然残留对象。

本轮仍是静态路径核对。前面所有发现应作为一张整改清单统一复审和验证，而不是每发现一项就再执行一次完整恢复。当前日志编码、manifest 证据绑定、真实数据保护点、整链恢复及本轮并发/失败隔离等放行缺口尚未共同关闭。

## 2026-09-21 08:50 复审：原任务与续接任务

### 任务身份与最新阶段
- 用户指定的原任务 `01a0b4b4-93c0-71a1-9725-6224628cb1fb` 最后在 00:57 被中断，其 rollout 已位于 archived_sessions；应用返回 notLoaded。不能说原任务本身仍在持续采样执行。
- 后续工作由“备份恢复 (2)”（`01a0bfc0-5616-74f2-8e7e-de290a9e3c09`）继续，沿用相同 worktree 和任务目录。用户明确授权其重启/迁移、继续修复、完成真实备份恢复，并要求 NAS 最多两份；按完整恢复链组织保留方向合理。
- 续接任务 08:44 被中断，目前应用状态 idle；后台 detached FULL operation 仍 running。区分“Agent 已暂停”和“后台备份仍在运行”，不能误报整个备份已经停止或完成。

### 新的实际证据
1. 昨晚页面演练 `cb1cfa1f-48bc-49bc-8cdd-087b7bef9847` 于 23:27 结束，operation=succeeded，并有 `20260920_211018_rehearsal_success.report.md`。其报告探针通过代表一次演练执行成功，不自动证明受控恢复候选合同或 P01–P10 全部通过。
2. 03:30 FULL `730e3281-2d79-4f94-8011-164881d1d9e2` 于 06:03 失败。具体阻断为保留算法遇到旧点 `20260920-004254` 没有 successful manifest。它没有把该轮结果改成成功。
3. 06:59 INCREMENTAL `ba250998-37e8-4393-904f-6c15900f8544` 在 mysqlbinlog 可用性检查失败；真实增量前提仍缺失，不能因后续改点 FULL 就把增量能力写成完成。续接记录明确说明重新通过 FULL 按钮提交，而非同一个增量请求静默降级。
4. 07:10 新 FULL `c2265d0a-7678-472f-9b84-ed1a3e712848` 正在执行。08:50 operation 仍 running，最新日志阶段为 MinIO 对象备份；续接任务 08:07 曾记录约 24 GB 对象读取及 CPU/网络活动。本审查没有额外连接服务器，不能凭旧流量估计当前完成百分比。
5. 新运行 Java PID 44764，启动于 07:06，Jar 明确为 `yudao-server-exec-3a245aabb.jar`。新 FULL 日志严格 UTF-8 可读，中文正常。此前文档“修复尚未提交/部署”已经过时。
6. worktree HEAD 为 `3a245aabb`，前一提交 `4c6c08787`，工作区干净。Surefire 06:18 报告：执行器 8 tests、服务层 68 tests，errors/failures 均 0。Pester 31 passed 来自执行日志记录，本轮未重跑。

### 方法判断
它已经沿统一清单整改，在独立 worktree 开发并部署明确版本，通过真实页面发起新备份，对失败保留真实终态，对增量缺工具 fail-fast；这些做法正确。当前主要问题是修复没有贯通报告生产、候选生成、恢复入口和数据一致性的完整合同，控制台定向测试通过仍未捕获下列阻塞。

### P01–P10 最新复核
| 编号 | 当前判断 |
| --- | --- |
| P01 | 部分修正：将 Set-RehearsalState 放在 Write-Evidence 前，消除了原先“计算后立即修改”的顺序错误；manifest 仍被改写，尚未落实不可变备份 manifest 与可变证据分离 |
| P02 | 部分修正：快照已包含 MySQL dump 和对象数据；但在停止业务写入之前分别导出，缺少跨存储共同一致点 |
| P03 | 部分修正：RestoreData 已调用 base FULL 导入与 binlog 重放；候选入口仍先要求目标增量目录自身存在完整 dump，正常增量点依旧进不来 |
| P04 | 未闭合且出现格式冲突：报告使用 64 位十六进制现场指纹，Java 候选仍生成 environment/host/imageTag 旧字符串并要求相等 |
| P05 | 代码已补停服/覆盖前的 dump、增量链及对象完整性检查；真实损坏拒绝及最终执行计划仍需验证 |
| P06 | 已新增持久 restore-isolation.json、同恢复点重试、失败停服、健康通过后清除；尚无完整故障注入验收，不再说完全缺少实现 |
| P07 | rollback-app 已加入 launcher mutex，原遗漏已修正；更广泛的发布/跨控制台互斥仍不能据此一并放行 |
| P08 | 已改为 findLatestUnknown 全目录扫描，移除了最近 200 条限制 |
| P09 | StreamWriter、控制台/子进程编码已修改；最新 07:10 FULL 日志 UTF-8 与中文均正常。旧坏日志作为历史证据保留 |
| P10 | 已采用临时文件+File.Replace，并处理短暂文件访问竞争；原直接覆盖缺陷已修正，完整并发/中断验证仍需补充 |

### 当前最明确的三个阻塞

**R1（P04）：报告指纹与页面候选格式必然不相等。**
`Rehearsal.psm1:186` 从 Context 读取现场 targetFingerprint，并在 187 行要求 64 位十六进制；`DockerOps.psm1:955` 从当前运行配置/容器计算 SHA-256。
但 `RuntimeOpsCandidateServiceImpl.java:454–463` 没改，仍返回 `environment=...;host=...;imageTag=...`，372 行仍与 reportTargetFingerprint 严格相等比较。新的演练即使成功，恢复候选也会因格式不同被阻断。生产者已经改变，消费者及对应 Java 候选测试没有同步，不能把 P04 标为已修复。现场采集目前还是演练配置中的运行态，后续还必须明确演练槽位与覆盖目标之间的兼容身份关系。

**R2（P03）：增量重放逻辑被旧候选筛选挡住。**
`DockerOps.psm1:1157–1166` 在读取 backupKind/baseBackupId 前检查目标目录中的完整 MySQL dump；正常增量目录没有这个文件，会先被跳过。直到 1191 行才开始读取链身份。虽然后面的 RestoreData 已调用 Replay-BackupOpsMySqlBinlogChain，真实增量恢复入口仍不可达。并且 06:59 真实增量仍缺 mysqlbinlog，V03 未通过。

**R3（P02）：保护快照有数据但没有共同一致时点。**
`RestoreData.psm1:319` 先调用 New-BackupOpsPreRestoreSnapshot，326 行才 Stop-BackupOpsFrontendBackend。快照函数 `DockerOps.psm1:1374–1380` 依次导出 MySQL 和对象；该函数本身不建立停写/事务排空屏障。因此业务仍可在两次导出之间改变数据库或附件，不能只因两份数据都存在就认定保护点可可靠回退。应先建立统一写入屏障并验证一致性，或采用有正式一致性证据的快照机制；本审查没有执行并发写入实验。

### 文档与实际状态漂移
原 task.md 仍写“当前改动尚未提交、尚未重新部署”，同时 git 已有 4c6c08787/3a245aabb，运行 Jar 为 3a245aabb；部分执行日志仍写旧 rehearsal running，但 operation 和真实报告早已 success。需要更新当前状态入口，以免下一轮继续按旧 blocker 重复操作。保留历史日志可以，不能让历史段落充当当前状态。

### 建议与边界
当前 FULL 可安全继续观察，不应因 Agent 任务中断就强杀后台执行器。下一步应先闭合 R1–R3、确认 mysqlbinlog 前提及 NAS 两链清理真实结果，再统一验证“新报告→真实候选→页面恢复预览→受控恢复”。当前没有“恢复数据”成功证据，旧演练成功也不能替代新修复版本的完整按钮验收。

本轮只读复核原任务、明确续接任务、源码、日志、测试报告和本机运行进程，未操作远程环境或修改产品代码。
