# Execution log

- 缺模块根因已实际trace为jsonschema：已有site-packages完整，control.environment.PYTHONPATH正确但systemd unit未传。仅诊断进程加现有路径后selections PASS。d52c205父审通过，生成0600 control.env并由unit引用，不在unit/log公开环境值，不安装组件；43/43定向测试PASS。GREEN: experience-preflight -> PASS。新release-v7仅更新native/pin，原配置不变，无本机重载；原prepare已FAILED，部署后真实新prepare重建空目标。

- prepare-339744c6三阶段SUCCEEDED但publish最终FAILED SMALLAPP_MODULENOTFOUNDERROR；客户端白名单拒绝已解除，当前在实际空目标select/admission导入路径缺依赖。不得将三阶段成功视为READY；子agent只读定位精确模块，优先复用已安装引擎，不安装新组件或重跑清理以猜测。仍未进行全量恢复。

- v6远端native/config及Spug两pin安装exit0；实际新页面任务 prepare-339744c6-76c7-427e-9f16-71828ffa314f 已受理，PID16245真实存活，依赖约33秒成功、清理上次空目标约2秒成功、initialize RUNNING。此轮验证失败后重新准备的真实路径，旧任务记录保留。

- 真实Spug TCP peer=192.168.109.82，已用短连接和远端ss确认，不是假设NAT地址。1750f29父审通过：control.allowedClientAddresses显式覆盖旧模板仅loopback名单，保留auth引用，42项定向验证PASS。GREEN: experience-preflight -> PASS。当前原任务FAILED/原生已结束，新release-v6仅安装native与该单IP配置并更新两pin；不修改已失败目标状态、不重启本机entry，再真实页面新建prepare。

- 第二次prepare三阶段全部SUCCEEDED，native target=spug-empty59-733c9c2fe019；但Spug注册准入FAILED TRANSPORT_CLIENT_FORBIDDEN。已确认模板继承allowedClientAddresses仅127.0.0.1而新服务直连，正在修正显式来源设置并保留认证，不手改失败状态。为后续只读业务验收启动本任务隐藏SSH隧道PID38408，本机127.0.0.1:18089→.59 loopback18089，未公开业务端口；收尾须停止此自有隧道。

- 新任务 prepare-4a8d0c7c-ade9-4d80-ac06-5424e8715f9b 真实页面受理；remote PID12009存活。页面原任务查询依赖SUCCEEDED（约33秒）、cleanup SUCCEEDED（约53秒）、initialize RUNNING，零pageerror；prepare-state.png已保存私密目录。真实清理成功，尚待空目标READY和恢复验收。

- v5 实际安装两段均exit0：远端native/config及Spug两pin回读一致；本机两文件更新，entry PID727→897，启动短暂无进程/拒连后HTTP401恢复。再次真实页面发起新prepare，不对8ae30807旧任务续跑；新预览明确列入3个本地bind源/目标，其余授权清理范围不变。

- f0b143a 父审通过：显式3个本地bind的目标必须属于待清卷、来源必须为数据盘本地同设备/root且不触保护目录；正常umount后原volume rm，已消失挂载不重复卸载。failure安全动作/对象/退出码/错误类型贯通native→后台→页面，不传秘密argv/stderr。Python37/37、JS92/92；发布HEAD8beac1a。GREEN: experience-preflight -> PASS。准备任务已FAILED且进程确认退出；本次新release-v5只更新native、后台、页面及明确3条bind配置，两pin回读；不重装Python/引擎、不续跑旧任务，部署后由真实页面新建准备任务。

- prepare-8ae30807 实际 FAILED：依赖成功，cleanup 失败；远端进程已退出，active.json不存在。201容器及前28个卷已删除，第29卷 intruoyi-prod-nas-restore59-20261020-native-minio 的 _data 为OS bind，Docker journal报告 device or resource busy；网络与84路径尚未清理。只读核所有待清卷恰有 minio/mysql/redis 三个该类本地bind，来源均为 /mnt/intruoyi-data/prod-nas-restore-prep-20261020/native-target-data/{role}，无fstab条目。源目录/NAS保留，修复显式3挂载的普通卸载，不force/lazy、不重试整个失败任务；通过后由页面新建准备任务。失败已在页面展示，尚无空目标或恢复成功。

- 新任务 prepare-8ae30807-c31d-4682-b245-a1d5ac2291e7 已由真实页面成功受理。页面原任务查询 RUNNING；远端只读进程核实 PID726 实际存活，依赖阶段约42秒 SUCCEEDED，当前 cleanup RUNNING。观察证据 prepare-process-latest.private.json，仅查询原任务，未重复派发。

- v4 安装实际 exit0：固定f2cff77，两文件替换；entry PID9→727，启动数秒连接拒绝后HTTP401恢复，容器/DB未重启。旧 prepare-5b489...已收到明确拒绝且store确认不存在，本轮从全新真实登录会话再走选源/选点/预览/确认，不修改旧历史或伪造状态。清理范围与上述preview一致，原生实际互斥保留。

- 旧busy精确根因及正式修复：smallapp-afdb2b25c4334477a40969587d44af0d 的旧目标离线、历史RUNNING，不是当前 worker。e322457 删除整段历史可达性检查，保留 native 宿主lock/active.json、本机prepare ACTIVE/源提交锁/新RESTORE保护。明确409 busy才清未受理provisional，其它网络未知保留。父审通过，Python31/31、JS91/91；记录f2cff77。GREEN: experience-preflight -> PASS。本次固定新release-v4仅安装prepare_target.py与prepare-target.js，当前prepare store为空；安装前核live摘要与entry PID身份，SIGTERM仅entry由已确认supervisor autorestart重载，不重建容器/DB。

- 首次真实页面提交 prepare-5b48923e-c05f-49c9-896b-ab1924f65aba 返回 PREPARATION_TARGET_BUSY，页面暂记 UNKNOWN；同一原任务自动查询返回 PREPARATION_OPERATION_NOT_FOUND，证明本机任务未受理。没有据此重新提交或删除浏览器记录。正在核查 submit 旧恢复历史检查命中的确切记录、实际 worker 与共享锁；尚未清理旧环境。--query 辅助脚本点击被页面锁禁用的标签超时，不能据此判断远端进程已停止。

- 真页面 preview PASS：完整备份 smallapp-3c2395ff88bd474e9fc007649565b848，零 pageerror；确认 84 路径/201 容器/97 普通卷/36 网络的既定清理范围，保留 NAS 三归档根、recovery-tools、recovery-preparation。GREEN: experience-preflight -> PASS。用户已明确授权 .59 旧环境清空，实际身份由 native preview 核验；任务互斥在 native execute 加锁，未发现恢复 worker；必要端口来源限定规则已通过。本次通过真实页面确认并提交准备操作，随后只追踪原 operationId，不因观察超时重复清理。

- GREEN: experience-preflight -> PASS。三点 point.backupId 与 capture.backupId 已逐项一致，父审 fix_point_keys.py 只替换 native points 三个字典键、更新配置 pin；值和其它配置不变，写前旧 pin 比较、写后字节回读。没有准备/恢复 worker；本次仅配置更正与 Spug 私密配置同步，不执行清理或恢复。

- 真页面 catalog 已显示完整 3c2395 与增量 20a1bb/e7b668。恢复点选择值是 smallapp operationId，前期配置生成误用了 capture.recoveryPoint 的 sha256 导致 runner 等待错误选项；正在按实际接口修正三项配置键及配置 pin，不修改备份内容。此次没有执行清理。

- v3 静态安装实际 exit 0：固定 1bea149，仅 app.js/prepare-target.js，未重启容器。真实页面再次选 .59 fresh 时请求已不带旧 targetConfigRef，safe 源返回 15 点，正在执行准备预览。

- 143f361 修复已父审：仅 fresh .59 草稿尚无匹配未消费 READY 时读取源；未 READY 恢复按钮保持禁用，READY 后请求仍带新目标，源/目标错误不吞掉。三脚本定向测试 90/90 PASS，记录 1bea149；未改后端。GREEN: experience-preflight -> PASS。本次新建固定提交 release-v3，安装仅两份静态 JS；实际 live 九文件先核 44cc4bb 摘要，保留并发修改，不重启服务。随后重新执行真实页面 preview；确认范围后才准备空目标。

- GREEN: experience-preflight -> PASS（43059网络依赖）。父任务授权范围内，已只读核 .59 ens18=172.30.30.59，实际活动zone public；既有SSH连接来源192.168.109.82。仅增加 public 的来源192.168.109.82/32、tcp43059 runtime/permanent rich rule，不reload、不关闭firewalld、不修改其它规则；执行后query回读两层。新服务尚未启动，无43059监听不视为网络放行失败。

- 新证据：真实 safe 源 selections 返回 15 个恢复点；选 fresh .59 后请求带旧 targetConfigRef=intruoyi-59-int04-safe-from57-20261025-r2，旧目标不可达导致备份选项清空。这是准备入口对旧目标存活的错误依赖，已派 prepare_target_impl 最小修复并保留实际恢复准入。仅显式 safe 不足以消除该问题。
- .59 当前只读确认无恢复/准备 worker，共享 active reservation 不存在；新控制服务尚未创建，43059 未监听。firewalld 未放行 43059；本机 SSH_CONNECTION 来源 192.168.109.82。子任务只允许增加该 /32 的 tcp43059 规则并分别回读 runtime/permanent，不关闭防火墙或 reload 全规则；实际容器连通仍需服务启动后证明。

- 实际 UI 错误定位：失败时 simple-mode=fast、application=intruoyi-57-fast-20261024-v1；runner 未明确切换 safe。新容器实际 safe 源 32657 与目标 33659 TCP/真实 selections 均成功。修正 runner 通过真实 selectOption('safe') 选定本次备份链来源，不改产品网络、不启动旧 18083 桥。此前将 18083 无监听视为原因已撤回。

- 2026-11-16 continuation: 前一目标执行轮完成本机实际安装，属于 progress；随后用户提示词请求只交付文字，未推进运行态。本轮继续真实页面验收。固定 44cc4bb 安装 exit 0，新 Spug 容器 0c578f706938，入口进程正常、准备配置已读取；真实登录成功，但备份点读取 BRIDGE_NETWORK_UNREACHABLE，尚未执行清理或恢复。继续核查实际 selectionConnections 覆盖后的执行桥，不能以根配置 18083 无监听误判原因；实际 .57 读取端口为 32657。

- 用户目标已 active；此前只有方案说明，当前开始真实实现与验收，不视为已完成。
- BDD: Given .59 可清空且 NAS/工具保留，When 页面准备，Then 新空目标可恢复。
- BDD: Given 选定全量，When 页面恢复，Then 数据、附件、登录真实可用；通过后才进行增量链阶段。
- BDD: Given 准备/恢复失败且任务已停止，When 重新准备，Then 可重新得到空目标，不要求旧现场保全。
- GREEN: experience-preflight -> PASS。用户已授权固定 .59 实际恢复闭环，先进行本机 Spug 真实登录与只读页面核对；server-access/login-access/release-backup-restore已读。使用现有私密账号，不输出凭据；本次页面只读，不提交准备或恢复。运行 Spug 为 f615a60c76f4，18080；18081为另一handoff实例不修改。原开发线程仍活跃，.59实际worker由只读安装勘察确认。
- 只读实际确认：18080 挂载 C:/Spug/runtime/ops/spug 和只读私密目录；部署入口为 C:/Spug/Spug-complete-20261022-151627/compose.transfer.json。尚未安装新按钮。
- 浏览器真实登录：第一轮 locator('#captcha') 重复匹配属于脚本选择器错误；改 input#captcha 后提交登录，原 admin.private.json 被返回“用户名或密码错误”，未猜测/重置账号。停止重复尝试，查现有正确配置引用。
- 子agent .59实际只读：201个容器，可用131019137024字节；没有active.json，进程仅control_entry，无recovery/repository执行worker。原件在私密 inventory59.private.json，不提交。
- 已实现停止后重置：3156318；记录5aeaaf1。Python83/83、JS86/86 PASS，见reset-execution.md；尚未真实安装验收。两个安装子任务分别准备远端.59配置、本机Spug最小安装，父任务审核后执行。
- 凭据引用已从现有 execute_spug_restore.cjs 确认到受保护spug-login.private.json；真实Playwright登录18080成功，进入/backup-restore/，页面title为备份与恢复·Spug，prepareButtonCount=0。登录问题已解除。
- 安装比对发现live入口/adapter/simple/UI等有并发线程修复，index与旧基线相同；禁止用本分支旧文件覆盖。安装子任务继续解析live对应已提交来源并合并本次差异，构造正式发布输入。
- GREEN: experience-preflight -> PASS。.59 bootstrap安装仅复制完整Python/引擎至/mnt/intruoyi-data/recovery-tools并写本任务私密配置，不调用清理/初始化/恢复。写前machineId核验，现有依赖引用与清理目录祖先交集为0，NAS保留。安装来源为本次独立发布release-v2固定44cc4bb，已提交native；复制后执行新Python --version。用户已授权此最小依赖准备。
- bootstrap真实exit0，原生full3c2395只读preview PASS。GREEN: experience-preflight -> PASS。本机18080 Spug任务History status=0实际查询为空，进程无执行worker；准备安装固定44cc4bb九个功能文件及rw私密挂载，只重建spug，DB/卷/18081保留。安装脚本逐文件比较原live与compose摘要，防并发覆盖。随后安装真实prepare-target配置，再真实页面操作。
# 续接核验
- v10第二次full760a8c7c23594a4dbb40ee0f0748b394真实UI受理history394，restore-admission仅1.508s成功，target-checks0.536s失败ARCHIVED_IMAGE_VERSIONS_INCOMPLETE。实际imageBindings为空，镜像已在prepare按选定roleImages加载并创建；无mutation/worker已退出/锁释放。重复读取问题真实解除，不能将该失败称为完整恢复通过。
- v10新control实际PID29612、programPins recovery/repository与PYTHONPATH前三段均指tools engine；owner preparedEmptyTarget=true。原worker持久argv也指tools control worker。v11仅对本功能已核实际镜像的新目标去除旧版本映射重复校验，不搭兼容旧映射体系。
- v10父实际安装exit0，4common+package/native pin一致，wrapperVerified，oldEngineUntouched；控制服务停止后真实新prepare-0fc424ef-4730-46a9-aaf2-fe22cae04743 READY，目标spug-empty59-d4e8388b78a9，总约69秒。
- GREEN: experience-preflight -> PASS。沿用授权与NAS/工具保护，当前新空目标READY，核新执行入口后通过真实页面恢复同一full3c2395；不复用失败c7107编号、不提前增量。
- 最终v10正式实现508f378、记录393be43；四common模块(plan/runtime/data_files/data)+native。Linux合并定向11/11、native25/25、counts2/2通过，父审通过；无mock恢复冒充真实验收。小文件全量+增量复制证明每payload单次真实读取、删除正确、空目标和I/O错误仍阻断。
- GREEN: experience-preflight -> PASS。原full已FAILED且无mutation/无worker/锁释放，安装只在宿主互斥下停止本任务spug-prepare59-restore.service，更新tools专属4模块+package摘要+native/pin，不改旧共享引擎或失败记录；由新prepare重建controller，校验新实际entry路径后真实全量恢复。
- 正式去重/entry修复已提交0b1a037、记录e97c388：5项Linux真实构建/文件恢复定向验证和25项native通过，父审通过；尚未部署。
- 预先确认下一轮必冲突并纳入同轮最小修复：native使用3个dataRoot下已声明RW bind，旧runtime仅允许volume；旧iptablesPin为不存在的测试服路径且规则不适用。仅native生成preparedEmptyTarget标记允许精确已声明bind并取消旧演练iptables约束，保留machine/docker/container/network身份和NAS保护。
- 物理复制还含重复全量hash/export/readback，父批准复用verify_content=False、保留真实复制/删除/路径保护与I/O错误，明确NOT_PERFORMED，最终由11表/3附件/真实登录验收。不会先部署已知仍会失败的中间版本。
- full c7107 原任务正式 FAILED_RETAINED，19:42:31Z；failureCode ARCHIVE_LEASE_FD_BUDGET_EXCEEDED，restore-admission 993.284秒；mutationDispatched=false，resource-no-mutation-release.json明确PROVEN_NO_MUTATION并19:42:32释放。三worker消失、active.json不存在，父真实页面查询FAILED同错误。没有人工kill/删锁/伪造终态。
- 执行源进一步定位：control.programPins.recovery仍指旧root entry；该wrapper基于__file__决定common与package，新workingDirectory不能改变它。正式修复须把本任务工具目录入口及package pins一致绑定，不改旧共享root。不能只部署无人执行的副本。
- 全量实际worker链21493→22698→22808→22819持续存活；真实阶段restore-admission。页面进度短暂读取失败后已正确显示该阶段，不新增进度修复。
- 执行源差异已实证：远端旧 common/recovery_minimal_plan.py 150行，selected_chain调用archived_tree/object_index_chain/physical_chain_inputs；check_pin(content=False)仍全量读并SHA。选定full载荷清单26,090,718,750字节，当前仓已提交轻量实现无此扫描。仅核小元数据及/proc，不另起载荷扫描；当前worker不替换代码，终态后针对正式源最小同步，避免后续重复全量校验。
- 附件真实页面验收脚本已准备node --check PASS；full/I2私密基线均补11表，其中3差异表用于证明DB增量实际应用。选定链附件增删改均0，只能验证附件保留与读取，不能宣称非空附件变更场景已验收。
- v9后真实UI全量提交202：smallapp-c7107c08b98a457caef62280e9a7a04c，history393，目标spug-empty59-9ad0f898afb1。原任务GET200/RUNNING，远端control21493的子worker22698存活；不重复提交。步骤读取STEP_TELEMETRY_READ_FAILED单独定位，不能据此认定恢复失败。
- v9 实际安装exit0：entry PID897→1395，启动短暂拒连后HTTP401恢复；两文件固定f6ffee1，容器/DB及远端空目标未重建。继续真实页面全量恢复。
- v9 8c33b36 父审通过，必要68项定向验证通过；仅最新READY未使用新目标跳过不同目标旧RESTORE历史，保留原备份历史规则/同目标预约/实际锁/admit_selection。首条实际阻断候选为旧 .58 恢复 smallapp-1fd7a5899db54511bee4daec85e271f8。
- GREEN: experience-preflight -> PASS。固定 f6ffee1/release-v9 仅安装 prepare_target.py、smallapp_entry.py，entry PID897/PPID1及无准备worker已核；只重载 entry，不重建容器/DB、不重跑空目标准备。原拒绝请求无本地entry/journal，随后真实新页面提交仍用 spug-empty59-9ad0f898afb1。
- 全量恢复首次真实页面提交 smallapp-8a878479abcd41649cad37c20ce4b679 返回409 ORIGINAL_OPERATION_STILL_UNRESOLVED。本机ui entry与adapter journal均不存在，未执行恢复。新空目标保留READY。
- 代码证据：smallapp_entry.reserve按相同source遍历全部历史，旧备份/其它目标未决会拒绝新空目标。此次修复仅解除已准备READY新目标对无关历史依赖，保留同目标限制和真实互斥；不重跑准备、不清理历史、不伪造旧任务成功。
- 实际 v8 安装 exit0；真实 UI prepare-261bf06f-3c35-404d-8c86-c6a42dbdf701 READY，开始19:08:05、结束19:09:13 UTC，三阶段成功且登记spug-empty59-9ad0f898afb1。准备按钮与失败后重建已实际通过。
- GREEN: experience-preflight -> PASS。通过真实 Spug 页面将 full smallapp-3c2395ff88bd474e9fc007649565b848 恢复到上述 .59 新空目标；备份源保持只读，不提前执行增量链。实际记录 operationId 后只查询原任务，失败不自动重试。
- v8 父审 e5d5594：仅 EnvironmentFile 无引号绝对路径；43 项定向验证通过。原 prepare 页面 FAILED，远端 native INITIALIZED 且 worker 已退出，唯一 Python PID19546为控制服务；restoreReservation=false。
- GREEN: experience-preflight -> PASS。本次固定 f3eb4b5/release-v8，仅替换 native 与 pin，配置和依赖不变；随后真实页面重新准备，仍保护 NAS、工具、凭据，只操作 .59。
- 实际 UI 查询：prepare-a1b08336-e0eb-4c5e-8003-5109d19d7516 三阶段成功，最终登记 FAILED/SMALLAPP_MODULENOTFOUNDERROR；不得标记空目标完成。
- 安装 agent 只读证据：systemd 219 将 EnvironmentFile 的双引号视为路径字符，拒绝加载；现有 jsonschema 路径仍存在。v8 仅修正此生成语法，不新增依赖。
- 验收 runner 增加原恢复编号的页面查询和选定增量点参数；node --check PASS，尚未执行增量恢复。
- 上一目标轮已安装 v7 启动环境修复并发起实际准备，属于进展；上一普通问答仅交付目标提示词。
- 本轮先查询同一准备任务和进程，禁止因会话过期重复提交。沿用 task.md 经验门禁，后续恢复以真实页面及终态为准。



### 附件浏览器验收脚本准备
BDD: 附件真实恢复 -> Given 完整恢复完成并真实登录，When 文件管理页搜索及打开本次三个基线附件，Then 目标同源HTTP200、字节与SHA256一致且无业务写入。
GREEN: node --check verify_attachment_ui.cjs -> PASS（仅语法检查；真实E2E未执行，等待父任务确认恢复完成）。

## v9 发布载体准备（子任务）
- 新建 worktree：C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v9；目标提交 f6ffee15b9f7a2a27b127c72bb7e1700dad1008c。命令 git worktree add -b codex/spug-backup59-mvp-release-v9 <path> <commit> 成功。
- 构建：从已提交 HEAD 提取 prepare_target.py、smallapp_entry.py，仅两文件payload，compile PASS。验证 python -X utf8 .../local-install/apply_entry_v9.py 返回preflight PASS；entry897/PPID1，无child/activePrepare。未apply。
- worktree无新提交，无需合回新提交；尚未删除，保留待父任务实际验收与统一收尾。


### I2 只读验收基线
RED: 首次元数据比较 -> DUPLICATE_REFERENCE_IDENTITY；实际8786对象引用行包含内容相同的重复引用，唯一对象5001。
GREEN: prepare_incremental_baseline.py -> PASS；13份pin元数据最终成功轮28,312,705字节，885表最终预期；I1/I2链连续，附件每段增删改全部0。载荷读取0，服务器写入0，增量恢复未执行。


### 实际引擎去重与执行路径只读审查
已核live plan/runtime/tree/check_pin和program wrapper；content=False仍全SHA，单plan不足；actual control programPins仍旧root。最小正式方案为tools专属两模块+package摘要，以及native新control入口/PYTHONPATH精确映射。未替换运行文件、未杀进程。证据live-engine-*.private.json；父确认原任务自然无mutation失败后方可安装与新prepare。
# v10 安装准备子任务追加证据

- GREEN: 私密 update_engine_native_v10.py 本机/嵌入远端 AST -> PASS；未 apply、未停服务、未创建 release-v10。
- 只读核实际 recovery.json 和五容器 Mounts -> 三个数据目录 RW bind 全在 dataPaths，八个配置 bind 只读；旧 bound/fresh_target 的 volume-only 合同不兼容。证据 v10-target-mount-contract.private.json，已交父及实现 Agent。
- retained_dependencies 已有 manifest 路径直接返回；实际依赖无 engine/package pin，不会在下一 prepare 覆盖 tools 修复。父要求等待补充正式合同提交后固定最终 release。


- GREEN: v10 fixed release 393be43f8e6c7ae5b7413b0fbe3754917110aae2, four-common/native carrier read-only preflight -> PASS. Path C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v10; build=standard_sources()+safe_fixes(); modules=plan/runtime/data_files/data; no new commit, no merge, no deletion yet. No apply/service stop/payload scan. Parent received exact apply command; expected package SHA f2a40e9e9644ce3cc2d69099363c25bb4db5962660df53481fb06521d74ee38a.

### v11 真实恢复续接
- 上一普通问答只提供目标提示词；本轮复核实际 Spug 原操作 smallapp-760a8c7c23594a4dbb40ee0f0748b394 为 FAILED/ARCHIVED_IMAGE_VERSIONS_INCOMPLETE，未重提原操作。
- 父审 d804311：preparedEmptyTarget 复用 native 创建和 bound 实际镜像/挂载，保留 startOrder 集合及重复检查；旧目标保持原合同。6 项定向验证 PASS，最终 3dca5a9。
- GREEN: experience-preflight -> PASS。release-v11 为本次新建干净发布工作区，固定 3dca5a9；只读 preflight 实证 v10 pin/package 匹配、无 active/恢复 worker。只写 tools 引擎 runtime/package，不改 NAS、native、凭据或 .57/.58；锁内停止任务自有控制服务，随后真实页面重新准备并执行 FULL。
- GREEN: release-v11 3dca5a9ced5ec26e1d973b84661a2c8d5d66d5d6; standard_sources()+safe_fixes() runtime diff six added lines, native unchanged; carrier read-only preflight PASS. New worktree ROOT/local-install/release-v11 clean, no new commits/merge/removal. No apply. Parent received command and runtime-v11.diff.
- v11 apply exit0：仅 runtime/package，nativeChanged=false，wrapperVerified=true，源提交3dca5a9。真实 Spug prepare-eef801e3-a115-48eb-9373-45175d11544b READY（21:03:54→21:05:06 UTC），新目标 spug-empty59-bd096098f1d3。
- 真实 FULL 请求 smallapp-bc9aafdc3b284a9582f6dd09f6bc9816 / history395 已接受；实际 worker 360→469→480 全走 tools 引擎。入场1.470秒、目标检查1.020秒成功；数据库 sql-stage 105.354秒完成，21:08:56开始解压；尚无终态，未重启或重复提交。
- 当前 FULL sql-expand 成功231.444秒，expanded.sql 12,476,249,490 bytes；sql-import 21:12:54 UTC开始。只读进程证据：worker480/子docker2478存活，目标mysql running，Query状态waiting for handler commit，管道累计约9.20GB。无SQL正文或秘密输出，不做全表检查。
- 真实progress HTTP200已含6步骤；验收runner原来只等待operation响应，可能在progress渲染前取DOM；改为等待progress响应及steps子节点数量，node --check及真实页面重查通过。产品不变，未追加轮询机制。
### v11 完整恢复真实终态与下一最小修复
- 真实 Spug 原操作 smallapp-bc9aafdc3b284a9582f6dd09f6bc9816 / history395 FAILED；原生 FAILED_RETAINED、ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED，21:39:54 UTC，child exit1、非超时、mutationDispatched=true。页面已显示对象步骤失败及具体错误。
- 数据库阶段成功1587.179秒：SQL导入775.530秒、旧全库回读467.763秒。对象阶段376.422秒后健康检查失败，命令回执53个，无历史命令爆量。原worker已退出，共享active保留；未手工清锁/重启或重复提交。
- v12已完成并提交31a670f：prepared数据库成功应用后仅SELECT1，NOT_PERFORMED/完整等价false，保留同操作同目标连续增量与真实错误；10项回归通过，尚未部署。
- v13必要缺口：prepared容器无Docker Healthcheck，需复用真实服务就绪探测；native不得永久拒绝本工具目标已终态、worker已退出的旧reservation，应在共享锁内允许用户重新准备。仅修此两项，不新增回滚、续跑或通用兼容。
- 本地最终融合c799b20/72897d5已准备和定向验证，未合int_main；release-v12预检ACTIVE未安装，保留等最终修复。当前目标未完成全量验收，增量未开始。
- GREEN: experience-preflight -> PASS。v13 c4fa257 父审：仅prepared真实就绪探测与当前失败目标预约重置，15+28定向通过。新release-v13干净，carrier只读核四份终态原件pins与实际无worker，TERMINAL_RETAINED_ALLOWED。仅data/runtime/native/package更新tools，原active及旧失败证据不改；配置pin同步Spug，随后由真实准备按钮解除已终态预约并重建。
- v13实际apply exit0，activeReservationPreserved=true，wrapperVerified=true，原失败证据/active未手动改变；只写tools data/runtime/native/package，配置pin同步Spug。
- 真实按钮 prepare-110aeac5-8e06-45ef-8139-c1679f9e5de9 READY，22:06:24→22:07:35 UTC，约71秒；dependencies成功后旧失败预约已解除，cleanup和initialize成功，新目标spug-empty59-73fa820ee324。失败有写入后重新准备已实际通过。正在真实页面提交同一完整备份。
- v13真实FULL smallapp-80eac03c768c47268e65141e22ad1468 已接受并实际运行，worker15731→15800→15809；入场1.359秒、目标检查1.048秒、SQL暂存108.458秒成功，22:11:56 UTC进入解压。未重启或重复提交；待原终态后验收。

- v13 FULL80eac03c 实际数据库导入成功745.346秒，prepared最小sql-readback成功1.424秒（上一轮467.763秒）；22:28:31 UTC已进入object-restore。worker15731/15800/15809存活，未产生终态。

- GREEN: experience-preflight -> PASS。Spug FULL80eac03c已真实SUCCEEDED（约28分22秒），原目标spug-empty59-73fa820ee324；现在仅该目标进行11表只读计数、真实页面登录及三附件读取校验。凭据仅读私密配置、不改账号/业务数据。完整验收通过前不准备增量目标。

### Full acceptance runner correction
- Parent authorized runner-only corrections after real FULL success and 11 matching tables. Prohibited writes remain aborted; blockedWriteAttempts is recorded once, request events no longer count as actual business mutations. Browser service workers are blocked.
- PDF uses an isolated private persistent Edge profile with plugins.always_open_pdf_externally=true; the real preview link click produces a browser download, saveAs bytes/SHA and PDF signature are checked. Images keep response byte checks; no API substitutes the page.
- GREEN: node --check verify_business_ui.cjs and verify_attachment_ui.cjs -> PASS. No real run, product/service/baseline change, or server write; parent runs acceptance. Private browser profile is retained as task-owned temporary evidence until final closeout.

- PDF runner hang diagnosed: native download 9198354887566 completed at 206586 bytes, PDF signature and baseline SHA matched, but response.body() for download navigation remained pending inside Promise.all, blocking the loop deadline. Parent explicitly authorized stopping exact verified Node PID37156 with its own Edge PID38440 subtree; identity rechecked, taskkill /T exited both, no restore services touched. Download/profile evidence preserved.
- Minimal runner fix: only jpg/jpeg/png response bodies enter pending; PDF bytes exclusively use native download. node --check verify_attachment_ui.cjs -> PASS. Original interrupted run is not a completed acceptance; parent reruns the corrected script.

- FULL80eac03c Spug真实SUCCEEDED，11表匹配，真实业务登录与用户管理页PASS（2117条可见用户总数，20行当前页）。工作台context POST已阻断，actual business writes=0；本地源核该请求有DB初始化/Redis签发副作用，不列只读白名单。
- 本机验收隧道原38408至远端loopback18089拒连；仅替换任务自有SSH到实际frontend172.29.238.36:80，新PID32632。服务器容器/网络不改。
- 附件浏览器首轮PDF取得viewer合成body未匹配；实际目标GET为206586bytes且hash一致，独立浏览器真实预览下载也生成相同PDF。runner等待缺口仍在定位，不把部分附件读取视为完整三附件验收。完整验收前不清空目标、不开始增量。
- Second attachment wait root cause confirmed by inspector: sole Playwright callback Page.close (id237), remaining nonbusiness page edge://downloads-hub/. Exact Node26160 and own browser subtree stopped after identity check with parent authorization. Runner now closes only http(s) preview pages; context closes at end. No timeout framework or service change.
- First traced rerun exited normally after 2 verified attachments; third image path belonged to two real records, causing strict text locator ambiguity. Runner now binds the exact baseline recordId to its real search response list index, checks UI row count and path, then clicks that row. Baseline unchanged.
- GREEN: authorized real full rerun session67326 -> exit0, login verified, three attachments bytes/SHA match (9198354890359 image,9198354887566 PDF native download,9198354890358 image), target origin http://127.0.0.1:18089, actual businessMutations0, blockedWriteAttempts1; browser closed. Private detailed hashes: target-59-full-attachments.private.json. Parent notified to proceed incremental preparation.

- FULL完整验收PASS：11表baseline计数全匹配；真实登录/用户页PASS；三附件9198354890359/9198354887566/9198354890358通过真实页面预览/下载，HTTP200、bytes与SHA全部匹配。actual业务写入0，工作台context写请求被阻断1。PDF下载脚本只关闭业务预览页，避免Edge内置下载页close等待；重复path通过真实列表唯一id定位。未更改恢复数据或基线。
- GREEN: experience-preflight -> PASS。完整验收已完成，现按用户顺序通过Spug准备新空目标，再选I2 smallapp-e7b668792c8f4bce945a52f984d3c660恢复FULL+I1+I2；仍固定.59，NAS/工具/凭据保留，仅清本目标，不手工清锁。
- 完整验收后新prepare681e546d已READY（约119秒），target spug-empty59-e4261b44a5f3。真实I2恢复 smallapp-f0c503e401204fd0a2d263937e1d3b13 已202接受，worker31437→31540→31548实际运行。入场1.494秒、target1.016秒成功，23:08:47 UTC进入FULL数据库暂存；仅原任务查询，不重复提交。

- GREEN: experience-preflight -> PASS。续接已核Spug I2真实SUCCEEDED、11表I2计数与真实登录用户页PASS；现仅使用原验收隧道对当前.59目标进行三附件真实页面读取，禁止业务写入，不重复恢复。

- 增量附件真实验收 session75010 exit0：三附件通过真实页面点击，图片response/PDF原生下载的bytes与SHA匹配；登录成功、actual业务写入0、阻断工作台写入1，浏览器正常关闭。所选I1/I2附件变更为0，不宣称覆盖附件增删改增量。
- GREEN: experience-preflight -> PASS。全部页面验收结束，精确核PID32632是本任务SSH 18089→.59 frontend隧道后停止，仅释放临时验收入口；保留Spug及恢复后的远端服务。
- GREEN: stop owned SSH PID32632 -> PASS；本机18089已无监听。恢复后的.59服务保留，验收隧道不是产品常驻入口。

## 最终融合验证记录（独立融合工作区）


- GREEN: 真实FULL完成后父授权同步指定7个缺失文件、当前父日志快照及本节13条独立融合证据；请求日志仅附本任务7个非空行，主线dirty不动。另仅取b11977f的workbench-context-review.md；task状态in_progress，I2请求f0c503e401204fd0a2d263937e1d3b13仍运行未验收。三runner node --check与git diff --check均PASS；本次不部署、不合main、不清worktree。

- GREEN: experience-preflight -> PASS；固定int_main25fe7ed及任务bcaf0e3，仅迁入0bbf939之后任务差异，工作区final-integration，禁止部署/合主线/清理。
- BDD: 主线已有首版入口和独立修复 -> Given主线基线，When迁入后续空目标/恢复去重实现，Then只含本任务增量且主线既有语义保留。
- `git worktree add -b codex/spug-backup59-mvp-final-integration C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/final-integration 25fe7edc47ee1cba9a4b85bcdc892d7819ea107e` -> PASS。
- `standard_sources()+safe_fixes()` -> PASS；两冲突精确解决，未导入部署base额外改动。
- GREEN: Python `-B -X utf8 -m unittest ops.spug.test_prepare_target ops.spug.test_prepare_target_http ops.spug.test_prepare_target_native ops.spug.test_prepare_target_registration`，PYTHONPATH=ops/spug -> 46 tests PASS。
- GREEN: Node `--test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs` -> 82 PASS。
- GREEN: Python `-B -X utf8 -m unittest discover -s doc/tasks/20261116-spug-backup59-mvp -p test_verify_restored_counts.py` -> 2 PASS。
- Linux已有python:3.12-bookworm，--network none --rm，源码/Git/既有local-test-deps只读挂载，无组件安装。首次载体未设GIT_DIR导致Git路径错误，修正容器映射后进入实际测试。
- REGRESSION: pytest test_backup_target_mounts.py及test_backup_variants.py筛选target_mounts、safe_registered_main_archive_inputs、standard_selected_chain_avoids、standard_final_archive_step、standard_keeps_original_code_except_reviewed_fixes_and_archive_names、standard_physical_result -> 11 PASS/1 FAIL；唯一失败为主线原HEAD可复现的10项构建allowlist遗漏。
- GREEN: 父批准精确补齐已生成模块allowlist，复跑test_standard_keeps_original_code_except_reviewed_fixes_and_archive_names -> 1 PASS；之前11项无新增受影响变化，无重复运行。
- `git diff --cached --check` -> PASS。工作区产生本任务融合提交后保留待审，不合回int_main、不删除；父后续v12增量另行合入本工作区。
- GREEN: v12差异bcaf0e3..31a670f精确三文件通过bytes传递git apply --3way --index -> PASS无冲突。现有Linux隔离载体test_prepared_database_readback.py -> 4 passed in 3.26s，其他已PASS组未重跑。实际恢复健康检查失败待后续修复，最终融合/发布仍未完成。
- GREEN: v13差异31a670f..c4fa257通过bytes传递git apply --3way --index -> PASS无冲突。Linux test_prepared_service_health.py -> 5 passed in 4.22s；Python unittest ops.spug.test_prepare_target_native -> 28 tests PASS。未重复数据库或其它已PASS组；只提交独立融合工作区，不部署/合主线/清理。


## 最终融合与工作区清理

- GREEN: experience-preflight -> PASS；双方真实恢复验收通过，独立只读审查PASS；仅清理本任务13个固定release工作区及已融合clean的final-integration。无本任务发布目录进程消费者，原integration及受保护父工作区保留。
- GREEN: int_main以ff-only从25fe7ed融合fd0b45d；精确脏日志补丁预验证及恢复成功，1699项原状态集合与原index均未变化。
- GREEN: 融合结果50个任务文件一致，正式生成154模块，runtime/data编译PASS，3个runner node --check PASS；未重复历史测试矩阵。

- GREEN: closeout_worktrees.py -> exit0；13/13自有发布工作区与已融合final-integration逐项git remove成功，目录及登记不存在。未使用force，未删除原integration/父managed工作区。
- completed：真实FULL/增量验收、独立审查、精确融合与最小验证、工作区清理及运行控制台恢复均已完成；逐路径提交与删除结果见closeout.md。
