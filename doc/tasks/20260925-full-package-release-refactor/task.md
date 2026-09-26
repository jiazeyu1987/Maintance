# 完整程序包发布合同与逐目标升级改造

## Current Status
ready_for_closeout

当前进度（2026-09-26）：全部T任务独立通过，gpt-5.6-luna/xhigh最终判定发布流程合同PASS。C7新轮次845/845、Node7/PS/AST/diff和C6-J122/122通过；114源、固定应用切片及隔离资源一致。实现与必要验证完成，进入任务范围提交/清理；维护仓缺origin仍限制推送和最终Git收尾。当前主程序main、当次候选构建与实际部署均不属于本轮范围。

## 当前验收边界（CR-20260926-PROCESS）

用户明确主程序主仓持续变化，要求专注建立发布流程。本轮不再追踪、改写或合并当前主程序main，也不把当前候选构建、三服实时预检及实际部署作为完成条件。保留既有T图、AC-01～AC-12、TC-01～TC-14、完整C7及Node/PS/AST/diff、冻结应用接口切片C6-J。应用af5acd保留为已验证接口切片交接；实际任意版本部署后续按此流程另行授权和验收。下文较早的当前版本发布就绪门槛被本节取代，不能再次据其扩大本轮工作。

## 2026-09-26 T6 续接检查
本次“继续”后旧子代理已不在活动树；已核对保留代码、任务日志、JUnit和任务容器，两台隔离容器均running/network none/任务标签一致。进程检查未发现旧T6测试进程，仅当前检查shell。继续现有T6实现和有限故障矩阵，已完成T1～T5/T2P/T6J不重新规划；现有T6片段证据不等于整阶段通过。使用新权限上下文恢复唯一执行者，保持独立验收。

## 2026-09-26 接管记录
- 用户授权当前任务接管后续开发并继续执行；原任务 01a0d754-73b2-72a3-a08e-ad8b83ab16db 已核对为 idle / interrupted。
- 已按用户授权将 dev-plan.md 原样更名为 development-plan.md。计划的 T1～T7、T2P、T6J 和 AC 编号保持不变。
- 之前选择的 development-plan-supervisor 解析器只支持 P 系列顺序里程碑，与本任务已批准的任务图不匹配；两次恢复失败均未改写状态。继续使用匹配原状态合同的 supervised-complex-delivery，计划文件入口采用用户已授权名称，不重建计划或重跑已验收阶段。
- 当前仅恢复 T4 执行者；独立测试通过后才解锁 T5。官方镜像取得已有 PASS 回执，但真实 Linux 载荷 T2P 未通过，不提前标完成。
- 接管门禁：只使用既有任务 worktree 和隔离容器；先核对资源归属及中断进程；跨沙箱写入走正式权限审批；不访问服务器，不打印运行配置中的凭据，不清理并行任务。

## 用户授权与目标
用户明确要求在现有发布体系上实施此前分析方案：每次完整程序安装包，保留业务数据；同一个不可变包和同一个执行器按三台服务器真实基线生成升级计划；明确每台实际版本；修正预检顺序和失败状态。范围为本地代码、测试、文档与必要的本地隔离验证，不执行服务器发布、重启、迁移、恢复或业务数据写入。

## 前置任务
本线程分析任务 `20260925-three-server-package-portability` 的分析已完成；因维护仓缺 origin，其文档Git收尾明确为 blocked。该限制继续记录，不伪造推送成功，不阻断本次独立本地实施。

## 里程碑
1. M1：核对正在进行的发布任务、主线/隔离分支差异、适用规则和实际执行源；形成PRD、验收和开发计划。
2. M2：以BDD/RED约束完整包组件、包内控制文件和实际镜像身份，实施最小改造。
3. M3：逐目标只读预检及状态绑定前移到首次运行配置/数据写入之前，保留受保护持久资源。
4. M4：完善执行阶段、实际版本回执、失败写保护与恢复边界，贯通已有工作流。
5. M5：独立验证、必要集成回归、任务自有改动提交与收尾；受缺失前置条件阻断的门禁明确记录。

## 预期验证
- 每项行为先BDD、再RED、最小实现、GREEN、受影响回归；保留精确命令与结果。
- 完整包不能缩窄组件；控制文件缺失立即失败；目标预检失败无业务/运行配置写入；未知基线/迁移失败/摘要漂移拒绝；实际镜像ID/digest不一致拒绝；中断产生可解释写保护状态。
- 同包针对不同起点生成不同待执行清单，升级后满足同一目标合同；业务数据与附件不被重置。
- 测试运行于任务自有隔离工作区；本地真实集成前确认资源归属；E2E只走真实前端和测试租户。
- 不将源码字符串检查、JSON模拟或旧报告当作真实远端执行/回滚证明。

## 经验门禁
- 固定已提交来源及执行器SHA；不修改既有不可变发布包、不放宽摘要/源清洁度/测试证明门禁。
- 包内不得混入目标IP、凭据、目标证据或业务快照；目标计划存包外并绑定包/目标/执行器/状态。
- app-release必须保留业务数据，禁止清库/覆盖MinIO、修改protected file config=28或审核矩阵。
- 不复用失败releaseTag；本次不创建实际发布tag、不触碰远端锁或服务器。
- 首次远端写入取锁、失锁拒绝后续写入；本次需验证真实生产SQL/命令载体，不以副本代替。
- 先核对worktree经验及同文件并行改动；不接管其它任务、不合入其未提交改动、不停止其进程。
- PowerShell显式UTF-8，不用&&；逐命令检查退出码；日志脱敏。
- AST/故障注入先核真实入口初始化、数据形状和实际命中阶段；必须观察前置真实SQL结果，不以SQL包含FAILED或载体错误冒充产品RED。
- pytest进度100%不等于完成；必须核进程退出码与有效JUnit。报告卡收尾时核有界platform.node/WMI与宿主commit余量，资源恢复后重型套件串行，不伪造hostname/修改stdlib或跳过必跑项。
- 完整包与可重建回归按维护worktree中的release-agent-checklist/test-release-preflight新门禁执行；新旧引擎ID不能代替官方内容身份，配置必须显式、隔离/独占/工具/归档不符在fixture首写前拒绝，独立C7必须在新ID完整执行。
- 用户已授权本次重构，按Subagent-Driven Development执行，独立验证后推进。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否；清除与完整包合同冲突的包外补齐路径。
- 是否从根因和长期维护角度解决：是；统一制品、目标状态、部署边界和运行身份合同，复用既有基础能力。
- 是否存在临时补丁或绕过：否；不自动释放异常锁，不跳过真实数据/前端验收，不伪造恢复成功。

## 当前工作
T1/T2/T2P/T3/T4/T5/T6J 已独立通过；T5最新独立C5 48项、C2 165项、C4 230项通过，哈希稳定且任务资源清零。T6已正式独立通过194/194与合同检查；当前进入T7最终集成及可重建复跑，三服发布就绪尚未完成。

## 执行工作区与隔离资源
- 维护worktree：`D:/IntRuoyiWorktree/full-package-release-maintenance`，分支`codex/full-package-release-refactor`，起点`3f3aabdc82ab5e85e2f872173a665a361f022725`。
- 必要应用联动已确认：`D:/IntRuoyiWorktree/full-package-release-application`，相同分支，基线840b9ef；仅T6J的4生产类/3测试类，保持四参数acceptTest。两入口任务worktree保持只读，不接管其P4/P5。
- 应用任务slot35，前端8210/后端48210，guard通过；本轮不启动服务。最初注册命令工作目录错误导致登记到维护仓；误登记修正首次File.Replace因空backup参数失败后，使用明确同目录backup参数完成原子替换，只移除本任务误登记并保留其它2条记录。
- 测试容器：`release-fullpkg-8bea35`，卷`release-fullpkg-8bea35-data`，标签`codex.task=20260925-full-package-release-refactor`，无网络/宿主端口；MySQL8.0.39已就绪。
- 本地运行配置（含测试凭据，禁止提交/打印）：`E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json`。只允许测试驱动读取，最终按本任务归属清理。

## 阻塞项
维护仓缺 origin 仍是已记录推送限制，已向用户询问远程地址或本地收尾安排。完全访问已解除当前执行权限阻塞；旧镜像下载问题已通过真实 T2P 解决。实际三服发布前提须在后续现场门禁核验，当前不作就绪承诺。

## 2026-09-26 当前阻塞
自动审批服务 HTTP 503 导致 Docker 隔离资源和进程只读检查未执行；沙箱内 Docker/CIM 拒绝访问。T4 保留未完成，不提交、不清理、不推进 T5。执行者确认中断前未运行工具，没有本轮遗留测试进程。本轮只更新任务记录，未修改生产代码或运行测试。恢复前提为审批服务可用并完成相同资源归属检查。

## 历史发布就绪目标确认（已被CR-20260926-PROCESS限定）
- 用户要求持续开发至可以发布到测试、正式、审核服务器；已确认“审核服务器”就是原备份服务器。按当前 server-access.md，人称审查服务器，技术环境码 backup 保留。
- 目标映射：test=172.30.30.58，prod=172.30.30.57，backup=172.30.30.59。不得因称呼变化切换主机或重命名技术接口。
- 交付门槛：T4、T2P、T5、T6、T7 均通过独立验收，任务改动完成必要提交与集成验证；冻结同一来源提交的完整包，三目标真实只读预检均有当前证据，明确平台准备和恢复前提，才可判断发布就绪。
- “可以发布”与“已经发布成功”分开记录。当前没有完整候选包或三服当前计划，不能宣称就绪；具体发布动作仍须走既有受控工作流。
- 本轮再次申请本地 Docker 镜像/任务容器只读检查，自动审批仍返回 HTTP 503（request id 39d18aff-5e41-4f44-82bc-e1911dd694ff）；未执行检查，未越权修改 worktree 或操作服务器。

## 审批服务恢复子步骤
- 用户明确要求先恢复审批服务再继续开发；本步骤归属当前任务，不新建无关任务。
- 目标：定位 39.106.23.28:8080/responses 上游 503 原因，恢复实际审批请求并保留安全审批。
- 顺序：脱敏读取本机配置/近期日志 → 核对服务归属与故障点 → 在明确可用的授权运维入口修复 → 用原 Docker 只读申请验证 → 恢复 T4。
- 约束：不关闭审批、不改成自动放行、不借终端/外部工具绕过权限；不输出 API key、token、完整环境或原始请求载荷；若服务器管理入口或权限缺失，报告精确缺项。

## 审批通路恢复结果
用户要求改用 gpt-6-astra；已通过正式审批只改 C:/Users/BJB110/.codex/config.toml 的 review_model（原 gpt-5.6-luna），保留其他配置、审批与沙箱。随后原 Docker/CIM 只读申请获批并 exit 0：官方镜像身份一致；release-fullpkg-8bea35 running/network none/codex.task 与 MySQL 任务卷匹配。当前进程查询仅观察到本次检查 shell，无匹配历史测试进程。恢复 T4，不把原 503 当作继续阻塞。

## T2P 真实缺陷修复写所有权
- T2P 新增真实集成测试复现生产准备器的 Windows 多行 shell 参数边界缺陷。现有任务授权涵盖本缺陷的正式修复，不能以代码合同 PASS 代替真实载荷。
- T4 已明确暂停 PS 修改及加载测试，交接脚本 SHA256=223162ba797cdeb8a0ed745d82fa3a425a5285731293ca30fc686ac6345a7d74。
- 暂时由 T2P 执行者独占生产脚本中 New-SchedulerSmokeRunnerPackage 和必要的已有参数传递函数，以及治理模块中真实 Docker 归档身份核对函数；只允许围绕已复现 TC-14 缺陷修复，不触碰 T4 的容量/目标采集/数据预检区段。
- 新增最小行为 RED 后再修改；如归档身份问题被真实证据复现，保持 descriptor/config/layer 的精确身份校验，不忽略校验、不重打包真实官方输入掩盖问题。真实 C2P、受影响 C2 和独立验收前 T2P/AC02 不可标完成。
- 结束写入后把新 SHA 和改动函数清单交还 T4，再允许其继续加载/修改该脚本。

## T4 容量与数据库身份审查决定
- 独立只读审查指出按 tar 总长估算不能覆盖小文件实际块占用；批准在既有容量 helper 中以标准库只读扫描依赖 tar 与镜像 layer 成员，按实际目标文件系统块大小分别预算暂存和展开，不解包到宿主、不跟随归档链接。
- 数据盘保留空间采用明确命名的 1 GiB 平台最低门槛，诊断与交付文档必须说明它只约束最低余量，不证明任意 DDL 临时增长已满足。1 KiB/低于门槛必须拒绝，不用一字节探针替代容量门禁。
- 当前正式支持的目标镜像存储为可核验路径的 classic overlay2；containerd/未知驱动在无法核验实际存储路径时明确拒绝，不以 DockerRootDir 猜测镜像路径。T7 必须写清支持边界，实际三服是否满足需现场预检证明。
- 预检绑定数据库与实际锁/迁移载体必须使用同一经验证 TargetMySqlDatabase。批准复用现有安全 MySQL 命令 helper 统一实际载体并补双库/特殊字符凭据行为 RED；不得在测试运输边界替换目标数据库来掩盖生产错位。

## T5 镜像身份已知验收事项
- TC14 已实测本机构建端 containerd 将 image.Id 记录为 manifest descriptor 摘要，config 摘要另有身份；不可假设两者相等。
- T5 的同包跨环境目标应校验已验证归档内容身份，区分 build imageId、descriptorDigest、configDigest、目标存储模式、加载 imageId 与实际容器 Image；不得任意 OR 放行或只比较标签。
- 后续实现优先由归档治理返回已校验内容身份，不改写冻结包。目标模式选择唯一合同后再核实镜像与容器；smoke 引用也必须绑定目标实际身份。
- classic 目标的真实加载与运行尚未验证，不能将构建端禁网测试冒充跨模式通过；缺少所需独立真实引擎时明确记录验证缺口。
- 原三服只读报告记录 Docker 26.1.3/26.1.4；本机本轮实测 Docker 29.2.1、containerd snapshotter，无现成 docker:dind 镜像。为必要验证准备官方 docker.io/library/docker:26.1.4-dind，固定 linux/amd64 并记录实际摘要，禁止 latest/替代源；镜像取得与实际引擎启动分别验证。
- 若启动独立引擎，只使用 release-fullpkg-8bea35- 前缀容器/任务卷，network none、不发布端口、不挂宿主 Docker socket 或业务目录；持久数据与现有 Docker 隔离。启动前记录精确命令与 experience-preflight，审批拒绝或前提不满足则保持缺口，不切换宿主存储后端冒充验证。
- 基于真实跨 daemon 证据，主管批准 T5 增加治理模块的最小返回合同范围：Assert-ReleaseArchiveImageIdentity / Assert-ReleaseInstallationContract / Test-ReleasePackageIntegrity 及必要对应合同测试，输出已校验的 verifiedImageContent；不改写冻结包、不另建身份框架、不使用任意 OR 放行。该范围仍映射现有 AC-08/AC-09，须等 T4 独立放行后实施。
- Website 文件事实采集使用已有 find/stat/sha256sum/base64/tr 与本机严格解析，避免新增未声明的远端 Python 依赖。批准仅在 Read-ReleaseTargetSnapshot 的 full 分支增加这些工具的首写前 command -v 只读门禁及缺工具负例；不改变 T4 容量/数据库语义，仍须完整 C4 回归，不能让管道末端成功掩盖采集失败。

## T6 尝试身份事前决定

T6 事前身份核对已发现现有 DB operationId 由环境和 releaseTag 确定，不能直接作为单次尝试文件名。主管按独立审查建议将计划内文件身份明确为 lockOperationId+lease 派生 attemptId，保留外部参数/数据库合同；同标签历史不得覆盖，新增有限负例同步 TC-10。T6 仍须等 T5 独立通过才执行。

T5 放行后，T6 准备合同明确为预置 gate.json（READY revision=0 且 operations 空）及 gate.lock，以区别首次初始化与历史证据丢失；缺件一律阻断，常规预检不能补齐。采用目标侧 flock 与同文件系统 tmp→mv、摘要绑定和锁内版本/当前 attempt 校验；读门禁不创建锁文件。首次创建新尝试先提交阻断 gate，再放 operation，避免新孤立记录被旧完成 gate 掩盖；同尝试更新的多文件中间态因摘要不一致而阻断，不宣称多文件事务。外部工具先只读核验，不引入远端 Python。批准测试 helper 安全支持连字符 schema 并正确 shell 引用，以及既有 readonly/SQL AST 载体加入正式依赖，保留原业务断言。T7 必须补明确授权后的初始化 runbook。

T6 真实 SQL 与文件同 shell 验证的测试依赖：任务 MySQL 镜像缺 flock，批准只从已验证官方 dind 固定镜像提取 busybox 与 musl 到任务 MySQL 的 /tmp/release-fullpkg-8bea35-t6-tools；先验证归属、源/目标摘要、依赖与真实锁竞争。单次测试命令显式使用此目录，不改系统 PATH、不联网、不挂宿主 socket、不改生产；缺件失败，不提供替代分支。任务结束精确删除并回读，证据注明实际 BusyBox flock 的验证范围。

T6 零写入状态规则：PREPARED/writeAttempted=false 不能被普通部署直接越过；仅沿原显式恢复确认、执行器终止、所有权与过期心跳条件处理，数据库 UPDATE 与同 lease 的 FAILED 回读成功后才持久 ZERO_WRITE_FAILED。后续部署须同时核对绑定文件和数据库事实，不因单个 false 字段、超时或缺失文件放行。STARTED/FINALIZING/RECOVERY_REQUIRED 仍阻断，即使数据库终态为 APPLIED/FAILED。writeAttempted 只能 false→true；旧内存状态或失败处理不得将持久 true 降为 false。

T6 完成确认丢失规则：同标签/包双摘要的后续调用可在只读核对 COMMITTED、绑定 receipt、同 lease 的数据库 APPLIED、历史与实际运行身份/配置/健康均一致后，返回已有完成事实，不取新租约或重放。校验持久原计划内部绑定，不用成功迁移后的新 SKIP 计划覆盖旧 APPLY 计划。批准 Website helper 增加显式 receipt 期望输入及必要 C5 回归；该输入须来自经校验的绑定 receipt，并与同一包 artifact 集合对账，空/非法输入不得回退到本地临时文件或默认成功。

不同新包的旧完成事实按旧receipt实际选中组件核对，不能要求新加入的Website/OnlyOffice已存在；新增组件前提仍由新包正常预检检查。校验末尾重新核gate摘要和同lease数据库终态，漂移必须拒绝。旧NAS程序载荷（镜像/archive/manifest）不构成读取前提；允许继续读取既有正式路径的审计history，不要求删除历史后仍成功，不为本任务扩展历史存储结构。

## Cleanup Keep

- doc/tasks/20260925-full-package-release-refactor/task.md
- doc/tasks/20260925-full-package-release-refactor/execution-log.md
- doc/tasks/20260925-full-package-release-refactor/verification-report.md
- doc/tasks/20260925-full-package-release-refactor/test-report.md
- doc/tasks/20260925-full-package-release-refactor/task-state.json
- doc/tasks/20260925-full-package-release-refactor/development-plan.md
- doc/tasks/20260925-full-package-release-refactor/test-plan.md
- doc/tasks/20260925-full-package-release-refactor/prd.md
- doc/tasks/20260925-full-package-release-refactor/request-analysis.md

## 历史验证停点（完全访问前）
T2P独立2/2及身份10/10通过；执行者最终C4 206/206、Node与PS摘要合同通过。新增TC07载体在PS5.1出现数组嵌套，20个用例未形成有效行为验证；正式修正写入被审批服务503拒绝执行，request fd9089f4-ec70-44e8-a5c0-43fd78311b04。最终C2两次审批超时亦未执行，已请求用户指导。生产保持PS8f398d1527e71f3ecea0233d1e4773aba9521618dec175170bed8e570fb7e56c，独立T4动态门禁未通过，不能解锁T5产品实现。新建classic任务引擎/卷暂保留，由主管后续精确清理；服务器未操作。

## 用户切换完全访问后恢复
当前用户已将权限设为完全访问，宿主下发 danger-full-access / approval never；后续命令不传 sandbox_permissions。原审批503/超时障碍解除，直接恢复尚未执行的TC07载体修正、最终C2和独立验证。此权限变化不扩大产品范围或服务器写入授权。

## T6 续接审查与待验收缺口

当前37项故障矩阵仍在执行；中间通过数不作最终结论。新增真实负例已复现持久operation先写后gate失败造成的CAS窗口、gate.lock检查后消失被追加打开重建、operation与gate的receiptDigest不一致。锁内摘要复核覆盖更新、从已完成状态创建新尝试及回执写入；READY无operation时单独处理。ZERO_WRITE_FAILED必须在同lease的DB FAILED落盘/回读后提交。执行者按既定BDD/RED/GREEN修复，随后独立测试者重新验收；T7保持pending。

## 历史前置阻塞：Windows WMI（本轮已恢复）

本机Python platform.node()独立进程10秒超时，pytest生成JUnit的platform.node→platform.uname→CPU Architecture WMI查询停滞；CIM CPU查询亦不能完成。sc queryex显示Winmgmt RUNNING、PID5860，sc enumdepend无依赖服务；任务缓存写入/回读/删除探针121ms完成。当前令牌administrator=false，需管理员恢复WMI。当前pytest进程及0字节报告保留，不以100%进度条判通过，不改stdlib、不跳过JUnit。仅终止本任务新增并卡住的诊断pip进程59880（核名称及启动时间），不终止pytest/WMI/业务进程。

已准备 `E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/diagnostics/restart-task-wmi.ps1`：要求管理员，只重启Winmgmt，重新核无活动依赖服务，不Force、不杀provider或测试进程；AST PASS，尚未执行。恢复后先验证CIM与platform.node，再收取原会话结果，修复已确认问题并完整回归，然后独立验收。

## 用户操作后WMI恢复与串行验证

用户Restart-Service报StopServiceFailed，但后续实测服务RUNNING/PID13156（原5860），platform.node独立进程0.25秒exit0，旧pytest已退出且报告落盘；无需再次重启。当前物理内存可用13.12GiB、commit可用15.75GiB；旧C2记录PowerShell 800705af、C4记录Go heap OOM，不能归为业务缺陷。T6继续按精确失败分类和-x定向验证，重型C6/C4/C5/C2串行，保留全部必跑用例。未修改系统内存配置、未重启Docker或操作服务器。

## T7 回归可复跑合同补充
主审已核准分解者只改development-plan/test-plan的窄补充：集中显式配置一次性classic实例ID、卷、归档路径及flock目录，保持官方内容身份/隔离前提。T7仅新增runtime_identity与durable两测试消费路径，不新增生产范围、AC或任务依赖；T6冻结期间不实施。T6独立通过后主管重建不同真实ID，最终C7及独立验收证明可重建复跑，正式报告保留，临时引擎仍按任务清理。

## T6 独立放行与T7交接
T6正式独立C6 194/194、Node7/PS向量/3AST/diff通过，11源文件哈希未变；主审已复读正式报告和JUnit，T6标为completed。T7依赖全部满足，唯一执行者t7_executor；主审负责外层classic重建/私有运行配置与资源生命周期，执行者仅写批准八个路径和T7日志。已批准补充保持原AC/TC和业务断言，最终需新ID完整C7及独立验收，未提前进入收尾或发布。

## T7 新引擎已就绪
主管已删除旧classic容器/独占卷并按原官方镜像与隔离参数重建，当前ID `1243a95b18bfe7819c396d22f5502676680bd84cb1469360d38c16fe81835ddf`，卷名不变但为新卷。原归档传输后stat/SHA一致，真实load得到官方config ID ab853f51...，禁网Node探针v24.15.0成功并删除探针/传输文件。mysql-runtime.json新增显式配置并回读，不含凭据的重建全过程证据在t7-classic-rebuild.json。MySQL及真实flock目录未替换；旧/tmp recovery任务根已精确移除。
