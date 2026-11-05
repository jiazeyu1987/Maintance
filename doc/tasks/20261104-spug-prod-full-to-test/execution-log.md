# Execution log

- 2026-11-04 当前目标续行：正式服真实全量备份一次并通过Spug恢复到测试服。上一目标轮为progress，安装任务独立的正式“目的地”阻塞不等同来源备份阻塞，重新核当前状态。
- Bootstrap：以显式UTF-8读取适用AGENTS、上一自有任务、经验索引及现存PowerShell规则副本；先建立本目录，再读取当前目标/操作及运行证据。尚未提交备份或恢复。
- BDD: prod-full-to-test -> Given 正式源与测试目标真实合同/资源/锁通过，When 在Spug提交唯一正式全量备份并以该新包恢复到测试服，Then 原操作终态/完整归档/源服务恢复/目标一致性/真实页面均可验。
- GREEN: experience-preflight -> PASS（仅当前状态只读核验）：按已授权三服只读范围，只查询.57来源控制与.58已登记目标的配置身份、认证selections、操作ledger、精确容器及/proc相关PID。严格SSH身份/known_hosts；原始配置落本机任务私密目录，公开记录只投影非秘密字段。无远端文件写入、无任务提交、无服务停启、无NAS更改。
- 只读载体首轮失败：系统Python3.6不支持subprocess.run(capture_output=...)，未取得完整观察结果；改用显式stdout/stderr PIPE后重跑相同只读观察。该载体错误不表示业务任务终态，也不触发任何操作重启。
- 2026-11-05 01:11（北京时间）只读观察完成：observe_current_state.py、observe_source_details.py、observe_source_runtime.py、source_host_diagnostics.py、verify_exact_source.py、verify_original_operation.py；均经严格 SSH 传入只读 Python，未执行服务器文件写入、备份/恢复提交、业务停启或 NAS 修改。原始配置与日志留在本机 private/prod-full-to-test-20261104，公开文件仅保留非凭据投影。
- .58：认证所选目标准入通过、控制服务 active，恢复操作和 claim 为空；五个绑定容器运行，backend/frontend healthy。未因目标就绪而跳过来源门禁。
- .57：source 控制 selections 的 fullReady=true 为配置能力信息，不能代替运行准入。五个绑定容器中后端精确 ID inspect 5 秒超时，健康 HTTP 3 秒超时；其 Docker 持久状态 Restarting=true/Pid=0/ExitCode=137 仅作辅助证据，不据此推断 OOM。MySQL StartedAt=2026-11-04T16:18:31Z，不归因于本轮操作；本轮全部远端只读。
- .57 NAS：约 1576 个 Python D 状态进程，样本等待 smb2_reconnect，栈经 cifs_statfs/smb2_queryfs；NAS:445 TCP 可连接，但不据此判 SMB 健康。只读 /proc/mountinfo、/proc/fs/cifs/DebugData，未触碰受保护共享盘挂载。样本 SSH 来源 192.168.112.214，与本机 192.168.109.82 不同；已发事实确认问题，未请求或执行不明确的生产修复。
- 历史句柄：源控制 ledger 的 worker-completion exit=2 不能作为整个备份终态。进一步按源码合同 SHA256(operationId) 查原仓储目录，smallapp-3d4c7ab0f65841b8892e4a640a53176d 的原 result.json=FAILED_RETAINED，failureCode=ARCHIVE_LEASE_FD_BUDGET_EXCEEDED；原 worker PID29516、capture PID2113、最后查询 PID15197 均已不存在。capture 阶段成功与仓储失败分别记录，未改写原终态。
- 只读输出修正：首次原仓储诊断展示全部 4787 个文件名和 953 个查询回执，输出超出必要范围；已将脚本及公开记录收窄为计数、原终态与有限关键句柄，原始数据仅保留私密目录。本项无远端修改。
- BLOCKER: experience-preflight -> 正式源后端实时身份/健康不可核且 CIFS 重连阻塞，不能保证全量采集及源写入恢复；不提交新 FULL、不恢复旧包替代、不跨过准入。当前任务状态 blocked、活跃目标保持 active（首次相同来源阻塞轮，未满足三轮 blocked 阈值）；开发 worktree 与证据保留，无实现提交或清理。
- 本轮文档/诊断校验：14 个文本文件显式 UTF-8 重读通过、6 个 JSON 可解析、6 个诊断 Python 源码 AST 可解析，git diff --check 通过（仅既有行尾 CRLF 提示）。这不是业务备份/恢复验收，不改变阻塞结论。
- 续行轮 2 开始：沿用原任务与完整目标。上一轮新增正式源精确健康/存储故障和原仓储终态证据，分类 progress；当前复验仍仅在既有三服只读授权范围。GREEN: experience-preflight -> PASS（只读状态复验，不提交任务/停启服务/修改 NAS）。
- 续行轮 2 载体纠正：本机 runpy 包装未设置诊断脚本模块路径，ModuleNotFoundError 在 SSH 之前失败；改为用同一 UTF-8 Python 直接启动既有脚本，未修改来源或重启任何原操作。
- 2026-11-05 01:15:15 北京时间：exact-source-recheck-2.json 证实同一 backend 精确 ID inspect 5 秒超时、health HTTP 超时；MySQL/MinIO/Redis/frontend 实时 inspect 返回，frontend HTTP200，锁无已观察内核 owner。保存 initial 和本轮时间戳回执，不用时间超时推断原业务操作终态。
- 2026-11-05 01:16:02 北京时间：observe_backend_wait.py 只读 /proc 与最近80条 Docker 系统日志；dockerd PID4794、113线程，其中1线程等待 smb2_reconnect，无该后端ID对应shim。系统日志无匹配后端ID，仅辅助观察，不据此断言无异常；原始日志只在私密目录，公开仅类别计数。未触发 daemon 调试信号/重启/kill，也未进行挂载或NAS I/O探测。
- BLOCKER: experience-preflight -> 同一正式源实时身份/健康与 CIFS 异常仍在。新增 daemon 等待证据说明单后端重启未必解除根因；现有授权不能扩为 Docker整机重启、NAS会话/挂载处理或其它应用变更。本轮无 FULL/restore 提交，连续同类阻塞第2轮，尚未达到 goal blocked 阈值；目标保持 active，任务保留 blocked。
- 续行轮 3 开始：上一轮取得 daemon 线程等待的新增证据，分类 progress（将下一步限制为先解除存储/运行态故障，不能假定单独重启后端有效）；同一来源准入阻塞已连续两轮。本轮复验最小精确来源检查；若仍失败且无可安全执行的下一步，将按三轮阻塞规则更新 goal 状态。GREEN: experience-preflight -> PASS（仅既有授权的只读复验，零提交/停启/挂载更改）。
- 2026-11-05 01:18:47 北京时间第三轮精确复验：exact-source-recheck-3.json，后端精确 ID inspect 5秒超时、health HTTP超时；其它四个配置容器实时 inspect 返回，前端HTTP200，共同锁未见内核 owner。本轮无新动作，仅再次确认同一阻塞，分类 no progress；不将探测超时当成原任务终态。
- BLOCKER: experience-preflight -> 同一正式源实时身份/健康及存储故障连续3轮阻断，未找到可在当前范围内安全直接执行的解除步骤；不重启Docker、不操作受保护NAS、不重复或改目标提交。完整目标的 FULL、新包、Spug真实恢复、最终数据/运行验收均未完成。任务保留blocked、原始目标不变；提交 goal blocked 状态更新，等待生产状态恢复或明确可执行的故障处理范围。
- 用户后续答复：旧来源电脑192.168.112.214“已停止或已关机”。当前只做有界只读确认，不把客户端关闭推断成服务器既有D进程退出；不把事实答复扩大成生产修复授权。GREEN: experience-preflight -> PASS（复核/proc进程来源/时间及精确后端健康；零远端写入/停启/挂载操作）。
- 2026-11-05 09:08–09:10 北京时间：observe_after_client_stop.py经严格SSH仅读/proc，约12秒双采样；旧SSH来源192.168.112.214的Python D进程1973个、当前来源192.168.109.82为1个，两采样Python进程无新增/离开。公开仅计数、有限PID及时间、SSH来源地址，不输出其它环境变量。未进行statfs/NAS路径访问或信号/停启。
- 同轮精确来源检查首次SSH banner握手超时（业务未观察），对同一只读脚本重试成功：exact-source-after-client-stop.json，Redis与后端精确ID inspect超时、backend health超时、frontend HTTP200；MySQL healthy，StartedAt=2026-11-05T01:08:17Z。记录启动变化但不推断是谁或何因触发；本轮未执行任何restart/start/stop。
- 已用异步问题核实正式服是否正在并行维护，避免在他人现场操作时追加变更。旧客户端关停不等同NAS/后端故障解除；已有blocked目标未标记完成、未更换旧包/小样本替代目标，本轮零新FULL/restore提交。
- 用户确认并行维护已关闭，“现在只有你处理”。继续同一目标的来源诊断，确认无已知并行维护，不视为整机/Docker/业务停启、NAS变更或数据恢复前置豁免。GREEN: experience-preflight -> PASS（仅读取NAS会话摘要、Docker线程栈、资源与精确服务观察；不访问NAS业务路径、不改变挂载/服务/内核设置）。
- 深化只读诊断未完成：diagnose_source_storage.py 的SSH载体40秒超时，未取得完整结果；随后仅核对Python句柄的SSH ps观察25秒超时。两者均不证明远端诊断进程退出，不重复提交该诊断，不宣称已取得容器挂载/内存或完整CIFS状态。保留未知，无服务器变更。
- 用户询问是否需要重启服务器：结合现有CIFS等待、daemon线程阻塞、后端不可达，形成prod57-normal-reboot-plan.md供复核；建议受控正常重启，但NAS服务端/网络与控制台前置必须通过，不能保证重启修复外部故障。未执行重启、强制停机、挂载变更或数据恢复。
- 技术依据核对：Linux kernel CIFS usage说明连接无响应时可能重试；Red Hat SMB重连D状态与CIFS挂起文档支持该类现象存在，不将公开案例等同于当前主机已确诊同一内核bug。推荐重启属于结合现场的恢复判断，非已证实唯一方案。
- 用户最新确认“重启好了”。恢复同一完整FULL→Spug→测试服目标；先验证真实重启/资源/精确容器/后端健康、来源/目标控制及NAS门禁，不能只凭用户报告认定成功。GREEN: experience-preflight -> PASS（既有三服只读授权，先执行有界真实状态观察，不提交备份/恢复、不改挂载或服务）。
- 2026-11-05 09:28–09:37 北京时间：verify_exact_source.py与observe_current_state.py、post_boot_inventory.py、read_boot_conflicts.py、measure_boot_repair.py真实只读证据表明.57/.58均已重启，D进程为0、可用内存约29GB、swap全空。旧NAS挂起阻塞已解除；新的准入缺口是.57原NAS挂载缺失、backend 48081端口冲突/frontend upstream缺失、源控制未自动启动，以及.58四个原目标容器停机和mountId登记随启动变化。
- 初轮容器库存超100个的只读安全上限拒绝，未写服务器；改为观察运行/重启中的容器、绑定目标和48081相关容器，仍保留总量上限。源有195个、测试459个历史容器，不逐一启动或清理。
- .57端口代理PID6860/6868由dockerd4374持有，转发172.21.0.7:48081；该地址目前为ERP助手，但该助手无48081映射。归属未完全证明，禁止停止ERP或盲杀代理。已记录所有配置48081的历史IntRuoyi容器供下一阶段精确核验。
- .58只读数据身份测量PASS：三个原数据目录dev/inode等均不变，仅mountId 116→119；不删除严格校验或伪装准入成功，需重新签发本次启动的新配置代次。当前目标服务准入仍失败。
- 本轮零远端写入、零服务停启、零NAS挂载/数据修改、零FULL/restore提交。已将可审阅的最小修复范围、禁止动作和验收写入post-boot-repair-plan.md；生产启动与NAS恢复超出此前明确安装授权，需一次明确范围确认。
- 已通过异步问题请求本计划的明确PROD授权。等待期间进一步只读核原fstab/systemd与目标目录：.57三个原NAS目标均为空、无NAS fstab项和automount定义，不能把当前本地目录当NAS写入。诊断未执行mount/umount、kill、start/stop或其它服务器写入。等待明确授权；未用原安装许可推断新增业务/NAS恢复许可。
- 用户明确回复“授权按此范围恢复（PROD）”。执行边界为post-boot-repair-plan.md；不重复询问已授权范围，不扩大为整机/Docker重启或其它业务停止。先核原始挂载/凭据/端口归属和资源锁，再逐项恢复；每个写入前记录相应PASS或精确BLOCKER，失败保留同一操作证据。
- BDD: 原NAS重启恢复 -> Given 同一共享和原凭据、三个空的原挂载目录；When 恢复原只读/读写挂载并登记持久启动；Then 原归档根目录在正确CIFS来源上可有界读取，前两处保持只读，第三处保持读写，不改NAS内容。
- RED: boot-definitions.json -> FAIL，三个原NAS挂载缺失，不能写备份；repair-preflight.json及私密credential-custody证明/root/.smbcredentials属root且0600，账号与三个历史挂载一致。
- GREEN: experience-preflight -> PASS（仅执行用户明确PROD批准的原NAS恢复；历史mountinfo确认第二处原root=/Backup/BackupPackage，避免误挂共享根；新建专属mount units，原fstab不变，不删除/卸载，不探测未知业务目录；凭据只用服务器原文件，SSH UTF-8 stdin，退出码和有界读回必须通过）。
- GREEN: restore_original_nas.py -> PASS，原三挂载来源/子目录/读写模式均正确且active；原archiveRoot存在，NAS可用约11.78TB（nas-restored.json）。新增持久mount units；未改fstab及NAS内容。
- BDD: 原测试目标启动 -> Given 已登记精确四容器停止、原数据绑定存在；When 依次start原mysql/minio/redis/backend；Then ID/镜像/配置/挂载不变，真实状态运行，随后独立健康和归属检查。
- RED: .58-post-boot.json -> FAIL，精确四容器均exited255。GREEN: experience-preflight -> PASS（仅start用户批准的四个精确ID；其它业务和原frontend不动，不创建/重建/更改镜像/业务数据；启动失败立即停止后续步骤）。
- 首次启动mysql成功，随后验证载体因Mounts数组顺序改变而拒绝，未启动其它三容器。只读对比原始boot库存证明Config/Image及按Destination排序的Mounts完全相同，仅Docker返回顺序变化；已修正为无序挂载身份对比，继续前先与原boot快照核四容器身份，不重复启动已运行mysql。该失败不属于业务身份漂移，不吞错误。
- GREEN: start_original_test_services.py -> PASS，.58四原容器全部running，身份/镜像/配置/挂载与boot前快照相同（original-test-started.json）；健康仍需独立验证。
- BDD: 原后端网络恢复 -> Given 原backend退出且48081残留代理匹配其原静态172.21.0.7，该IP已被ERP动态占用、所有其它运行容器无48081绑定；When 仅解除原backend失败的网络登记，再按实际结果处理原端口残留并启动原backend；Then backend保持原ID/镜像/数据，获得有效网络，所有其它运行容器StartedAt不变。
- RED: repair-preflight.json -> FAIL，原backend静态IP请求与运行ERP冲突且48081残留；全部11个48081配置候选均为IntRuoyi当前/历史后端，历史容器均停止且无网络，确认端口残留属于原后端。GREEN: experience-preflight -> PASS（只解除精确c4385604…的失败网络登记，保存原配置私密快照；不触碰ERP端点、不删容器/数据、不重启Docker，结果单独读取后再决定后续）。
- repair_backend_endpoint.py -> PASS，解除原backend失效的容器网络配置，未改变其它运行容器StartedAt；48081代理仍存在。只读network local-kv快照进一步找到孤立endpoint 0574b25a…，name=intruoyi-backend、dnsNames含原c4385604…，portmap明确48081，sandbox与当前任何运行容器均不一致；未写Docker数据库。
- 核对Docker官方Moby container_operations.go及network.go：停止容器disconnect只删容器配置；force且找不到容器时才按同名Endpoint删除孤立网络对象。采用Docker正式CLI删除已确认原endpoint：仅对停止的同一后端短暂改名以使原endpoint名可定位，finally恢复原名，然后连接同一网络中已核空闲的172.21.0.11及原backend别名，start原ID。该步骤不手改network数据库、不kill未知代理、不删除整个网络；其它容器/IP不变。
- GREEN: experience-preflight -> PASS（原孤立endpoint与48081归属已证明；核空闲IP、无其它端口owner，保留原快照和步骤回执；只处理用户批准的原后端网络残留，原ID/镜像/Config/数据绑定保持，失败停止且恢复原名）。
- Docker正式API拒绝endpoint删除：endpoint intruoyi-backend not found。原容器名已在finally恢复，未连接/启动，不重试删除。该结果说明local-kv原始字节中的0574…可能是历史页面，不能把二进制检索当成活跃endpoint证据。保留失败并修正判断：已确认当前两个残留代理及原48081绑定归属，尚无可删除的活跃网络endpoint。
- GREEN: experience-preflight -> PASS（按批准范围仅向PID6860/6868发SIGTERM；逐一复验argv/PPID/启动ticks完全一致、所有其它运行容器无48081绑定、原backend确为停止；不强杀未知进程。端口释放后连接原backend至同一网络空闲172.21.0.11及原别名，start同一ID；若Docker仍拒绝端口则保留失败，不重启daemon）。
- 原两个代理已退出且ss确认48081无监听；原backend已重新登记同一网络空闲172.21.0.11/原别名，但start仍被Docker内部端口分配器拒绝48081，未启动。Docker26.1.3、LiveRestoreEnabled=false；未重启整个Docker。该新阻塞超出已批准修复范围，需要正式方案及额外授权；先完成已批准的控制服务/测试目标登记恢复。
- BDD: 重启后目标存储重新证明 -> Given .58原数据dev/inode/source/root/options完全一致、仅boot导致mountId116→119；When 新建owner/control不可变代次并重载本任务控制服务；Then 严格校验保留、旧配置/服务定义/receipt保留，目标ref不变，未执行恢复。
- GREEN: experience-preflight -> PASS（.58 bootId精确绑定、三处差异仅mountId、无操作/claim；新文件xb创建、旧pin复核、替换服务精确旧pin、只重启本任务spug-main-restore-58-20261104-v3.service，不改应用数据或其它服务）。
- 重新证明载体首轮在导入前因profile默认Python3.6不支持引擎语法而失败，尚未写入配置或服务。改为.58已安装独立Python3.12后重跑同一未开始步骤，不修改引擎或绕过校验。
- .58配置重新证明前的整数mountId断言载体纠正后，reattest_test_mounts.py -> PASS。三处dev/inode及其它mountIdentity不变，严格校验保留；新owner/control pin和旧service/receipt均持久保留，控制服务active（test-postboot-attestation.json）。没有恢复操作或数据覆盖。
- BDD: 正式来源控制持久恢复 -> Given 原已安装入口/解释器摘要相符且NAS已恢复、32657无监听；When 复制相同Python到本任务独立系统可执行目录并登记source控制systemd；Then 原源配置/程序/凭据保持、API启动且开机持久，未提交FULL。
- GREEN: experience-preflight -> PASS（仅本任务源控制安装；独立Python副本逐文件摘要验证与restorecon，不改共享解释器标签；新配置只改pythonPin路径且相同二进制摘要，旧配置保留；unit依赖原NAS，不动主程序或其它控制服务）。
- GREEN: restore_source_control.py -> PASS，source控制systemd active，独立Python3603文件摘要一致。认证来源selections恢复、4个历史点可读；fullReady仅表示目录资格，正式backend仍exited，不据此提交FULL。
- .58原五服务running、backend/MinIO/frontend healthy，真实backend /actuator/health UP，http://172.30.30.58:8081首页及healthz HTTP200；127.0.0.1:8081不是原frontend绑定地址，初次通用主机探测失败不代表原容器失败。
- .58认证目标预检在mount门禁通过后明确拒绝MAIN_NETWORK_CONFIGURATION_CHANGED。只读test-network-differences.json证明同一bridge ID/subnet/driver/internal/options/labels/members完全一致，唯一差异为Docker重启后IPAM显式新增Gateway=172.29.235.1，host网络无变化；服务配置摘要和网络附件验证已通过。按已批准“恢复控制登记”范围为该真实观测另签不可变r2，不改Docker网络，不移除严格网络校验。
- BDD: 重启后网络登记 -> Given 同一原bridge身份及服务附件、唯一差异为IPAM显式默认Gateway；When 仅重新证明该字段并保留旧代次；Then 目标严格预检使用精确新网络观测，所有应用身份/网络/数据保持。
- GREEN: experience-preflight -> PASS（.58同一boot，IPAM差异白名单精确限定为172.29.235.0/24的172.29.235.1，任何其它差异拒绝；核全部服务配置摘要/附件不变，无operation/claim，仅新不可变配置与本任务control reload）。
- Docker额外处理计划已完成只读配置验证和服务保活条件审阅，写入docker-port-reservation-repair-plan.md。已请求新增PROD授权；等待时不写daemon配置、不reload/restart Docker，继续原范围目标登记核验。
- GREEN: reattest_test_gateway.py -> PASS，同一internal=true bridge仅重新证明显式Gateway；严格网络/存储身份校验保留。认证GET所选目标准入HTTP200，freshTargetConfigRefs包含原intruoyi-main-58-safe-restore-20261104-v1（test-preflight-postboot.json）；未创建operation或claim。
- GREEN: 其它业务保护验证 -> PASS（other-applications-preserved.json），12个受保护容器PID/StartedAt/镜像均相对本轮修复前保持；仅原frontend自身的既有restart loop单独记录，未主动停止其它业务。source控制is-enabled=enabled。
- BLOCKER: experience-preflight -> 正式backend start仍被Docker内部48081端口分配状态拒绝，ss已无该端口监听。已批准范围内可独立完成的NAS/控制/测试目标恢复及验证完成；待新增daemon方案明确授权。本轮无新FULL/restore提交，任务未完成、不提交未通过全目标的实现、不清理开发worktree。原goal保持未完成，不把新阻塞与已解除的旧CIFS故障混为一谈。
- 用户明确回复“授权按新计划处理（PROD）”。授权范围为docker-port-reservation-repair-plan.md，继续同一FULL→Spug→测试恢复完整目标，不再次询问该范围。
- BDD: Docker管理进程保活修复 -> Given 原48081无监听但分配器拒绝、原12个其它业务运行；When 先仅增live-restore并reload、核实际启用与PID不变，再restart dockerd；Then 原12容器PID/StartedAt/镜像/配置/挂载不变，Docker新PID与live-restore生效，原backend可恢复。
- RED: 原backend精确start -> FAIL/port is already allocated，ss无48081监听。GREEN: experience-preflight -> PASS（用户新增PROD授权、官方保活路径和配置只读验证已通过；实际写入前强制复验原daemon摘要、无Swarm、unit KillMode=process/无ExecStop、源共同锁独占和12受保护容器稳定。先单独执行enable，读回通过后才允许restart；任一失败不进入后续阶段）。
- GREEN: repair_docker_reservation.py enable -> PASS，Docker实际LiveRestoreEnabled=true、daemon仍PID4374，原12容器PID/StartedAt/镜像/配置/挂载均未变；原配置私密备份和候选已保存，新配置只增加live-restore。
- GREEN: experience-preflight -> PASS（进入已批准的restart阶段前再次强制复验enable回执/当前配置SHA/live-restore/单位安全属性/12容器身份与共同锁；仅restart docker.service，不重启整机/containerd、不stop其它业务、不删除任何载荷或网络数据库）。
- GREEN: repair_docker_reservation.py restart -> PASS，daemon PID4374→10191，12容器PID/StartedAt/镜像/配置/挂载均保持，live-restore=true。GREEN: experience-preflight -> PASS（随后仅对原backend/frontend精确ID核原快照并按需start，已运行或自身重试中的不重复提交start；保留ID/镜像/Config/挂载，后续独立验health/HTTP/源目标资格）。
# 2026-11-05 Docker管理进程修复后准入

GREEN: 用户新PROD授权 -> live-restore启用与热加载、仅dockerd重启成功，12个受保护容器PID/StartedAt/身份保持，证据docker-enable-result.json、docker-restart-result.json。原正式backend/frontend自动恢复启动；exact-source.json后端HTTP200/UP、前端HTTP200，原五服务运行、共同锁无owner。

BDD: 归档守护容量 -> Given 正式主程序历史全量包约14346文件、含祖先目录24104路径；When 控制服务启动备份/恢复子进程；Then 显式资源预算能容纳完整路径租约且继续保留原路径身份/内容守护。

RED: 真实容量预检 -> FAIL，.57来源与.58目标控制服务软上限1024/硬4096，历史清单所需含预留24232；不能开始新FULL。历史registry另证实旧smallapp-3d4点存在nas-finalization-retry成功结果；早期原repository-operation仍FAILED_RETAINED，二者必须区分，且均不能替代本轮新包。

资源配置方案：只给本任务已授权安装的两个控制服务增加持久systemd drop-in LimitNOFILE=65536，核cgroup无工作子进程后仅重启两个控制服务，核真实/proc limits继承与认证selections；不改内核全局限制、不改业务服务、不降低守护。预算基于固定清单SHA验证及路径数量，保留约2.7倍容量。预算仍不足时原守护继续真实失败。

GREEN: experience-preflight -> PASS；作用于已授权控制组件安装/登记范围，正式原程序health=UP，无活动共同锁；控制服务重启前再次核无worker并保存原unit/limits与五容器运行态。

GREEN: configure_archive_budget.py -> 两服实际/proc limits均65536/65536，认证selections可读且目标ref通过，业务running集合保持。首次来源控制restart后的立即HTTP探测遇启动窗口ConnectionRefused；已核配置成功且仅补有界启动等待/读回，未重复重启来源控制，未提交业务操作。

BDD: 本机正式来源通道合同 -> Given 已安装稳定源控制隧道在本机42657，而Spug旧来源route仍32657、进度SSH18557缺监听；When 仅对同一来源route三URL绑定42657，并在原57监督通道增加18557、进度使用已验证独立Python；Then 同一来源真实页面准入及进度通道恢复，.58/.59和其它route保持。

RED: Playwright真实登录/选择正式safe/FULL -> BRIDGE_NETWORK_UNREACHABLE，零operations POST；docker内到host.docker.internal:42657 TCP成功、Windows42657监听，而32657/18557无监听。原因是旧显示route与稳定控制通道未对齐。

GREEN: experience-preflight -> PASS（本机Spug更新和本任务控制组件/通道持久配置已获授权；只变intruoyi-57-safe-20261024-v1源route、对应progress python及自有57监督脚本，原值私密备份；精确验证监督/ssh PID归属后只重启57通道，不重启Spug容器、不改其它route或业务）。

GREEN: 实际页面通道回归 -> Playwright1.63.0/Chrome真实登录、选择正式服safe/FULL，显示“已连接Spug执行器”、开始备份按钮启用、零operations POST；18557/42657同一新57 SSH进程监听，旧监督和子进程按准确PID/命令归属退出，其它监督保持。共同Playwright路径D:/ProjectPackage/AGENTS.md在本机迁移后不存在，沿本线程已使用且验证的IntRuoyiE2E/node_modules/playwright及Chrome路径，不下载替代版本、不mock。

GREEN: experience-preflight -> PASS（进入已授权真实Spug FULL；正式精确五容器运行、backend UP/frontend200，原NAS三挂载恢复且归档根可读、存储容量已核，源共同锁无owner；两控制服务65536预算且空闲，.58精确原目标健康及严格认证准入通过；真实页面safe/FULL按钮启用。只提交一次，先保存实际POST请求编号，失联只查该编号；不重用旧包）。

RED: 首次新FULL页面POST -> HTTP409 ORIGINAL_BRIDGE_BINDING_CHANGED，原编号smallapp-73cd541a95d84d6a86f9d693e4053c75。原因：历史同来源受理记录固定原32657 URL身份，改为42657虽恢复当前连通但破坏历史指纹核验。未创建新受理记录/worker的结论仍需原编号absence验证；不换编号、不改历史指纹/终态、不绕过保护。首次UI脚本仅报告自动化流程PASS而非业务成功，现更正该次结果为FAIL/HTTP409。

纠正方案：恢复源route原始bytes，在本任务57持久SSH监督增加本机32657别名，同一远端32657；保留42657供目标控制回源，18557及独立Python进度配置保留。原bridge URL历史身份保持，随后仅通过真实UI“核对原编号是否未受理”读回三方absence、原编号重试。GREEN: experience-preflight -> PASS（仍属已授权本机控制通道安装范围，仅原57监督重启，业务保持；无历史文件篡改）。

GREEN: preserve_source_route_identity.py及57监督精确重启 -> 原route字节恢复；Windows32657/42657/18557同一SSH进程51612监听。真实Spug UI原编号absence返回retryAllowed=true、完整request一致（full-original-unaccepted-proof.json），随后原编号重试一次HTTP202/RUNNING、SPUG_DISPATCH_RESERVED。唯一新FULL=smallapp-73cd541a95d84d6a86f9d693e4053c75；不把保留/派发当作已完成，继续查询真实原操作。

真实进度：Spug History=350，10:50:18备份前置通过并进入source-capture，10:50:42 WRITERS_STOPPED_DATABASE_FENCED。浏览器首个monitor误点当前隐藏的进度面板按钮而超时，已按实际部署页面点击“执行进度”tab后查询；查询无POST，原worker持续运行。watch_spug_operation.cjs保持真实页面并保存原操作GET/可见步骤，不提交其它业务请求。

11:00/11:02只读/proc与同一capture文件观察：worker17097及dump docker子进程24017存在且IO递增，database.sql.gz.pending 713115284→1330824661 bytes；没有将等待误判失败或重新提交。restore-target-baseline.json：.58原五容器健康，backend UP/frontend200；归档绑定前后端imageId分别d72ca84.../359ab3...，与正式源一致；无恢复ledger/claim，严格目标准入仍通过。

BDD: 恢复后的真实页面验收 -> Given 本轮新全量包恢复终态及一致性已确认；When 通过实际.58:8081登录页使用已登记私密凭据登录并只读访问首页/现有页面；Then 页面用户/租户、权限响应和实际运行版本可核，无API或SQL替代页面登录、不创建业务测试数据。现有login-access权威副本改为芋道源码/admin最终只读验收，与用户允许admin只验证范围一致；不将其计为aoteman测试写入验收。

GREEN: experience-preflight -> PASS（已批准测试主程序恢复与验收；以下仅准备实际前端登录/只读检查，凭据从私密JSON读取不输出，不做错误密码探针、不改租户/权限/默认文件配置、不绕过验证码）。

GREEN: verify_target_business_ui.cjs before-restore -> PASS，实际Chrome/Playwright从.58:8081登录页提交登记凭据，实际登录HTTP200/code0，权限响应userId1/admin、24角色/15菜单，首页/index显示版本2026-11-03-12-15-42及主要业务菜单，业务mutation=0。只作恢复前基线，不当作本轮恢复验收；公开回执及截图不含密码/token。

2026-11-05 11:10只读采集观察：同一worker17097及docker dump24017存活，database.sql.gz.pending=3030195017 bytes（11:05约1896950285），Spug实际UI同一History350仍RUNNING/source-capture，查询writes=0。原写入者暂停属于正在运行的备份合同，不另行start/restart。继续同一编号，不重新提交FULL。

验收准备：verify_full_point.py依据安装中真实engine的RepositoryMinimumReadback/ArchiveClose/EXITED三种原始文档核pin；首次按其它正式发布schema编写的草稿在历史元数据只读校验中明确失败，已据安装原代码纠正。历史实际文档仅作helper schema校验PASS，不计本轮新点/恢复成功。安装合同保留point.controlledRestoreEligible=false、blockedReason=REPOSITORY_RECOVERY_NOT_RUN；已登记主目标由源实时catalogue及精确目标链准入独立授权，不改写该标志。源restoration.restored仅表示原start命令完成，仍必须独立health/HTTP验收。

2026-11-05 11:27：本轮同一采集目录database.sql.gz已正式完成，6127989396 bytes，原dump子进程退出；worker17097继续后续数据库观测/物理附件采集。Spug History350仍RUNNING，不能将SQL完成当作全包成功，尚无恢复提交。

页面基线补充：真实导航DCC项目代码页显示暂无数据，等待真实行失败；保留target-before-restore-dcc-baseline-missing.json，不伪造数据或将空列表算作记录验收。此任务未要求DCC业务行为变更，不改产品/权限/矩阵或创建记录；改用已有系统用户管理列表建立可观察记录基线，恢复后重复同一路径。验证码get的POST归属认证流程，单独排除于业务mutation统计，未禁用或绕过验证码。

GREEN: 真实用户管理列表基线 -> PASS，Chrome实际登录并依次点击系统管理/用户管理，URL/system/user，2117条/当前20行，业务mutation=0。版本2026-11-03-12-15-42，target-before-restore-navigation-business.json为公开摘要；包含员工姓名/手机号的完整页面文本和截图仅存本机任务private目录，不提交业务人员信息。恢复后以同一菜单路径验收；此前DCC空基线失败仍保留，不算通过。

2026-11-05 11:36只读观察：同一worker17097及连续更换的Docker查询子进程仍活跃，scratch-after直接条目41→161→306，IO继续增加，证明SQL导出后核对仍在推进。该数量不是完成比例，不由历史包大小推算ETA或提前启动恢复。

2026-11-05 11:52：885张表的source-data证据3571773 bytes生成，转MinIO物理附件采集；11:59:26原MinIO启动，首次readiness记录503/NOT_READY，随后继续实际内容读取。12:07:50出现CAPTURE_MATERIAL_COMPLETE_SOURCE_RESTORED，采集worker17097退出，父监督17095继续归档处理。

12:08:42独立source-after-capture-starting.json：原五容器均running、身份/镜像保持，frontend200，backend刚启动约52秒首次HTTP ConnectionReset；保留真实未就绪，不当作health通过、不重复start，按有界启动等待再查。source-after-full-preservation.json：11个其它受保护容器PID/StartedAt保持，配置/镜像/挂载全保持；唯一MinIO生命周期变化属于本轮已批准物理采集停启，明确记录，不冒称12个全程PID不变。

GREEN: 正式来源采集后独立运行态 -> PASS。12:10:26启动日志已有Tomcat/Started标记，12:11容器内health UP；source-after-capture-health.json另从主机实际访问backend HTTP200/UP、frontend200。五服务running且原ID/镜像保持，原backend PID5420自12:07:50未重启，整个启动过程未追加任何start/restart。sourceLock无owner；仓储worker16086继续原新备份的归档处理，不将来源恢复健康当作备份终态。

2026-11-05 12:12:03 材料校验通过，真实Spug History350进入“上传NAS”。12:17同一仓储worker16086仍running，rchar=58410073789并持续增加；采集worker已按合同退出，无第二FULL。真实UI查询writes=0，仍RUNNING/ORIGINAL_OWNER_RESULT_NOT_READY，后者仅说明最终原结果尚未生成。等待原操作上传和完整读回；不从历史大小推算完成比例，不提交测试恢复。

验收准备只读核对已安装目标执行器：其数据库恢复实际执行完整schema/逐表多重集数据比较，物理附件实际执行完整inventory/apply_tree及独立S3版本导出比对，Redis实际独立读回；安装版本的start_application包含health与隔离检查。当前开发树另有轻量化代码，不能用其行为替代本轮冻结安装合同，也不因此修改安装中执行器。最终仍须检查本轮真实pins及独立业务页面。

12:30采集清单摘要：capture-file-inventory含9421个物理文件/9656201379 bytes及9515目录；archive entries总24156路径。该数字仅物理采集清单，不含最终包全部数据库/镜像/语义附件等，不当作总包大小或进度百分比。12:38只读/proc原worker16086：rchar=100099523849，存在NAS归档文件读取位置，真实UI仍nas-upload/RUNNING。未递归探测NAS、未重新提交或改安装执行器。

准备验收helper verify_restored_runtime.py/verify_restore_evidence.py，只读核精确注册实例和本轮原始终态/pins；真实恢复后才运行，尚不能计为PASS。Python AST 38文件、Node语法、git diff --check通过；当前公开任务116文件约2.7MB，JSON凭据字段扫描无可疑明文值。只读安装源码定位的一个临时PowerShell包装曾解析失败、另一次未命中nas-upload文本而StopIteration，均未写服务器/未触及原worker，不计为产品失败或备份结果。

12:41来源独立健康复核仍HTTP200/UP、frontend200，五原容器及启动时间保持。12:42:33真实Spug原History350显示NAS上传完成（30分29秒）、索引生成完成（0.720秒），进入NAS独立读回；仍RUNNING，未提交恢复。

13:10:41真实UI确认NAS独立读回完成（28分7秒），13:10:43进入归档最终核验。原worker16086持续处理同一任务；已生成独立readback-originals，保留其与最终结果的区别。没有新FULL或恢复提交。

13:42:24同一真实UI确认归档最终核验完成（31分41秒），13:42:25执行器进入清理本次采集临时文件；该清理是本次原执行器的既定合同，不是Agent额外NAS删除。尚无最终操作成功，继续同编号观察。

GREEN: 本轮正式新FULL -> SUCCEEDED，14:17:28原结果实际退出0，无failureCode；真实Spug History350终态及截图保存。new-full-point-verified.json核13个小文档pins、原manifest/point/readback/close/exit，载荷14378文件/26090562595 bytes，integrity COMPLETE，commonRecoveryPoint=sha256:e94ad09d511f2b9ebb576e8b8f460a04087ddfbf3d2ed92b6391bb658b59d3c4。原生完整读回已通过；辅助核验不重新全量hash、不宣称NAS服务器落盘耐久性。

GREEN: 新点实时目录与恢复前准入 -> 源认证selections HTTP200包含本轮smallapp-73cd541a95d84d6a86f9d693e4053c75，无historyErrorCode；.58严格selected-target仍包含原主目标，原五容器running、backend UP/frontend200、镜像绑定相同、ledger仅service.lock且无claim；正式源14:18复查UP/200，原容器身份及启动时间保持。

GREEN: experience-preflight -> PASS（执行已授权真实Spug正式新FULL到测试主程序覆盖恢复；仅选本轮新点与intruoyi-main-58-safe-restore-20261104-v1，源.57/目标.58，safe/replace；新包及原始全读回已通过、实时目标准入/资源身份/独占性及65536预算仍适用。恢复会覆盖已批准目标实例数据库、MinIO及Redis范围；保持原容器/镜像/登记配置，使用实际页面确认。只提交一次，先保存真实请求编号，未知态沿原编号查，不绕过保护或重建目标）。

14:21:08真实Chrome/Spug登录后，选择正式safe、恢复/覆盖、刚完成的新FULL、测试服.58；确认摘要核源ref/新恢复点/精确目标ref并勾选覆盖确认。operations POST仅1次，HTTP202/RUNNING，恢复编号smallapp-ba0bca490ac243768c8b759fa14a8bbd，证据restore-ui-submission.json/restore-ui-result.json/restore-ui-confirm.png。已开启真实页面GET-only观察原恢复编号；HTTP202仅受理，不当作恢复完成。


### 2026-11-05 14:32 北京时间：首次恢复 admission 失败及原挂载恢复门禁
- FULL History 350 / smallapp-73cd541a95d84d6a86f9d693e4053c75：SUCCEEDED，原进程 exit 0，14378 files / 26090562595 bytes；元数据 pin 与源实时准入 PASS。
- RESTORE History 351 / smallapp-ba0bca490ac243768c8b759fa14a8bbd：FAILED ARCHIVE_ROOT_UNAVAILABLE，未生成执行 worker/completion/replacement claim；五个原容器 PID/StartedAt 与14:18基线一致。
- BDD: 原归档挂载恢复 -> Given 原只读路径重启丢失、原NAS共享和新FULL可读；When 恢复原canonical只读挂载并建立持久依赖；Then 同一新FULL元数据解析通过，业务容器不启停。
- RED: 实际Spug恢复 -> FAIL, ARCHIVE_ROOT_UNAVAILABLE；真实环境前置故障，不宣称产品测试RED。
- GREEN: experience-preflight -> PASS；按用户既有原NAS挂载恢复授权，现有fstab共享自动挂载正常，目标原目录为空无链接，新FULL point SHA256吻合，失败操作未执行；具体方案 target-archive-mount-repair-plan.md。仅新增原路径只读bind与systemd依赖，无NAS内容写入、无业务启停。

### 2026-11-05 14:35 北京时间：原归档挂载验收与下一次真实恢复
- GREEN: restore_target_archive_mount.py -> PASS，原路径 CIFS ro，systemd active/enabled，五个业务容器 PID/StartedAt 完全不变。
- 只读验证脚本首次因安装模块目录 engine/control 引用错误失败；纠正本机检查脚本目录后继续，未改服务器代码。
- GREEN: verify_target_archive_admission.py -> PASS；调用已安装 source_admits/bind_archive_chain，只读核新 FULL 实时准入、6份证据 pins、单点FULL链及同一point SHA256。
- 首次失败的本地恢复回执/截图/终态原样归入 restore-attempt-1，SHA256前后相同，远端History351和ledger不变。根目录 restore-* 将记录第二次真实UI操作；不会把第一次失败改成成功。
- GREEN: experience-preflight -> PASS；用户原真实FULL→测试服恢复授权有效，精确目标intruoyi-main-58-safe-restore-20261104-v1、同一新FULL点、真实UI确认覆盖。归档路径前置已修复，下一步仅由Spug页面提交新operationId一次。

- 2026-11-05 14:35:48 第二次真实 Spug UI 恢复 POST 一次，HTTP202，operationId=smallapp-af9fb80256c0417f86f2741686950823；精确point为本轮新FULL smallapp-73cd541a95d84d6a86f9d693e4053c75，精确目标为 .58 MAIN。202仅为受理，当前未验收成功。

### 2026-11-05 15:08 北京时间：真实恢复失败及打包契约修复
- History352 / smallapp-af9fb80256c0417f86f2741686950823 于14:53:57 FAILED_RETAINED / RESTORE_TYPEERROR，原worker退出1。已核同一DB UUID应用库表数0，原MySQL/Redis仍运行；MinIO/backend/frontend停止。没有执行MinIO清空/Redis FLUSHDB。保持停写，不启动空库主程序、不清failed claim/host reservation。
- 根因：standard_fixes把当前recovery_replace.py注入冻结safe包，但该文件使用 inventory(content=False)/apply_tree(verify_content=False)，冻结safe函数没有这些参数。数据库DROP/CREATE在inventory之前已返回0，随后发生TypeError；native-063将该SQL误记mutation=false，此审计缺口也需正式修复，不能据此否认数据清空。
- BDD: SAFE/FAST实际包替换契约 -> Given 从正式builder得到两种实际文件包及真实本机文件树；When 各包执行目标准备；Then 两者函数调用均兼容，SAFE完整哈希/readback保持，FAST既有行为保持；不以源码字符串或mock E2E代替。
- BDD: 破坏性SQL审计 -> Given目标准备执行DROP/CREATE；When实际包装MySQL调用；Then invocation mutation=true，失败不能被错误归类为无写入。
- 修复方案：仅对安全包已审核注入点转换为冻结safe完整验证接口；冻结原库文件与验证算法不改。为查询包装增加显式mutation参数并在DROP/CREATE传true。实现前先加入实际包组件回归并保留RED。
- 设计约束：无fallback/吞错，无临时绕过；失败记录与原点保持不可变。正式续恢复尚未执行，须完成修复、验证和可审阅计划。

### 2026-11-05 失败恢复正式机制与回归
- 本机初始pytest/jsonschema依赖缺失属于环境失败，未记业务RED；依赖安装到本任务私密test-dependencies，不改变应用运行环境。
- RED: 实际包组件测试 -> SAFE复现 inventory unexpected keyword content；FAST复现破坏性SQL未标mutation；2 FAIL。
- GREEN: SAFE仅转换注入调用到冻结完整验证接口，mysql.query显式传播mutation；实际包组件2 PASS。
- REGRESSION: package/replacement/main/storage -> 133 PASS，7 Windows不具备的POSIX用例待Linux，不伪装通过。
- BDD: 保留失败的显式续恢复 -> 见 retained-recovery-plan.md；先新增用例RED（模块缺失），实现追加clearance/ready/release/consumption；原FAILED结果不可变、同点同目标一次性绑定、未知结果/漂移/新失败保持阻塞。
- GREEN: 核心续恢复12 PASS；扩展Windows相关回归145 PASS，7 POSIX待Linux。新增3个实际POSIX flock/宿主预约文件组件用例，将与原7项一起在本机Linux独立容器运行；不是服务器或E2E替代。
- GREEN: experience-preflight -> PASS（仅本机Linux组件测试）：只读挂本任务源码，无docker.sock、无端口；使用本任务新容器spug-retained-retry-unit-20261105和唯一local volume spug-retained-retry-unit-20261105。结束确认名称与无引用后清理自有容器/卷，不影响其它实例。

### 2026-11-05 15:38 北京时间：修复验证与严格只读准入
- REGRESSION: Windows最终相关回归145 PASS /10 POSIX skip；本机Linux真实flock/宿主预约/挂载相关142 PASS /0 skip。原7项及新增3项POSIX均实际通过。SAFE/FAST实际包均执行真实本机文件树准备，并额外执行实际包BoundMySql.query，证实mutation=true传播。
- 只读目标观察第一次因未加载既有控制服务PYTHONPATH缺jsonschema而失败，无写服务器；改为继承安装服务环境后严格原身份/配置/网络/挂载/数据库UUID校验通过。retained-readonly-preflight.json：同一UUID、表数0、仅mysql/redis运行，其余三容器停止。未启空库主程序，未释放保留预约。
- 下一阶段：实现单独提交，创建本次专属临时release worktree从该提交构建；只安装新引擎/新配置代次、重载本任务控制服务。旧执行器和失败历史保留原字节，显式准许仅绑定同一新FULL及同一目标。

GREEN: experience-preflight -> PASS（本次组件修复隔离发布）：实现提交9176b3cea6cf203db7b28d1efdfba209c634bb5d已通过必要回归；新建专属release worktree C:/Users/D01021/.codex/worktrees/spug-retained-recovery-release-20261105/Maintance，分支codex/release-spug-retained-recovery-20261105，从精确提交构建。只使用提交内容，构建输出置本任务private；不复用开发或旧release目录。服务器安装仅同一.58控制组件/新配置代次及原失败准许审计，依用户既有授权继续同一新FULL恢复；主程序保持停写至正常恢复器阶段。

GREEN: 隔离发布构建 -> PASS；release worktree精确9176b3c，构建standard文件清单1536427e009f00b0ee59cb1da205ef13ee586d0a068382aec1a65cd1bcab6371，tgz SHA256 ce77d9f2d5ae9dff72f3b0f05e773f980bed87f2186d3f35c64d2d98786e643c；该干净checkout实际包/续恢复25 PASS、3已在Linux通过的POSIX本轮Windows skip；构建前后git status为空。无新提交，待完成后删除。
GREEN: .58 新组件代次安装 -> PASS；engine-retained-9176b3c，原失败6份pins逐字节保持，宿主预约完全保持，目标字典完全相同。只重载本任务控制服务，无业务服务启动。retained-recovery-install.json保存新配置及组件摘要。
GREEN: experience-preflight -> PASS（显式续恢复准许）：同一原FAILED_RETAINED/exit1、无原活动进程、原physical锁与宿主预约精确绑定；严格预检同一DB UUID/0表且三写入服务停止。使用新已校验模块按retained-recovery-plan.md只追加原失败准许及释放审计，保留失败/claim/原预约文件，下一次恢复仍由真实Spug UI新编号提交同一新FULL及.58 MAIN。准许CLI不执行数据恢复。

GREEN: .58续恢复准许追加并精确释放原宿主active指针 -> PASS；原失败6份pins保持，原claim/原预约文件/History352不变。retained-recovery-authorize.json。已保存第二次失败UI七份文件到restore-attempt-2并逐字节SHA校验。
GREEN: experience-preflight -> PASS（第三次真实UI恢复）：来源同一已完成新FULL、目标同一.58 MAIN、原点归档不变、新安全包及限定准许已通过；仅一次正常Spug页面确认提交，新编号沿原查询，不启动空库程序或改历史。

2026-11-05 第三次真实Spug UI恢复：2026-11-05T07:46:32.851Z，POST仅1次 HTTP202，operationId=smallapp-91cc5c0b4b054cb38075681f1aca7d4a；同一新FULL→原.58 MAIN。202仅受理，沿此唯一新编号观察。Windows测试自有Linux volume已核label及无引用后删除，不影响其它容器/卷。

GREEN: experience-preflight -> PASS（仅本次临时release worktree删除）：路径与分支精确匹配、HEAD9176b3c、无dirty/untracked/新提交；构建与安装控制服务实际校验通过，运行态位于服务器新引擎代次，无本机进程引用此发布目录。只由git删除本次目录，保留开发worktree、其它任务与原失败现场。

GREEN: 本轮临时release worktree删除 -> PASS；无新提交，无需融合发布副本，Git登记及物理目录均消失；实现提交仍保留于本任务开发分支。实际数据恢复仍在原History353运行，不宣称整体完成。

2026-11-05 16:04:14真实History353进入target-replacement；16:06:16完成PREPARED（2分1秒）。retained-real-native-preparation.json核实际native-063清库mutation=true/exit0，native-088后续变更exit0；实际SAFE文件inventory/apply_tree已越过原TypeError。旧FAILED_RETAINED保持，新准许消费于07:47:07Z并绑定smallapp-91cc5c0b4b054cb38075681f1aca7d4a，同一宿主新预约已生成。16:06:16开始restore-preflight，原编号继续RUNNING，恢复终态及业务验收仍待完成。
长期经验已归入现有release-agent-checklist并在experience-index增加关键词路由；包括实际封包合同、mutation审计、原归档挂载准入、清库后停写及显式同点同目标续恢复门禁。最终验收脚本按已安装MAIN合同核REGISTERED_MAIN_RESOURCE_CUSTODY/programImagesChanged=false，不更改引擎证据。


### 2026-11-05 16:44 第三次恢复的真实失败与配置合同
- History353 / smallapp-91cc5c0b4b054cb38075681f1aca7d4a：目标清理PREPARED、SQL导入实际exit0；16:40:37回读FORMAL_DATA_LIMITS_REQUIRED，整体FAILED_RETAINED/exit1。885表、UUID不变，三业务容器仍停止；对象与Redis阶段未执行。
- 根因证据readback-limits-contract.json：dataLimits.max_bytes=64GiB超出实际正式16GiB上限。该限额计算数据库摘要输出，与maxExpandedBytes SQL展开容量不同，不应提高正式合同掩盖非法配置。
- BDD: 提前拒绝非法数据校验预算 -> Given 实际SAFE/FAST包和64GiB非法dataLimits，When 构造恢复执行器，Then 在任何归档扫描、数据库查询和目标清理之前报FORMAL_DATA_LIMITS_REQUIRED；16GiB有效预算通过此门禁并到达下一配置阶段。
- BDD: 合法独立容量合同 -> Given SQL展开上限64GiB与摘要校验16GiB，When 正式安装配置，Then 实际formal校验通过且独立SQL上限不变；禁止扩大正式16GiB合同。
- 修复范围仅同一源/点/目标、控制组件和配置；已有用户安装/测试恢复授权继续有效。第三次原失败和所有保留依据不可变，新操作仍只由真实Spug UI发起。

- RED: pytest test_backup_variants.py -k data_limits -> 2 FAIL，实际SAFE/FAST非法预算均越过前置检查到达target.services。
- GREEN: 同命令 -> 2 PASS；实际构造器及实际formal.validate_limits在目标访问前生效。
- Windows扩展回归中误纳入要求/proc的native-retained模块：53 FAIL/13 ERROR均须Linux核对，未记录为业务回归通过；其余119 PASS/10 POSIX skip。下步同套Linux真实执行，不跳过失败。
- GREEN: experience-preflight -> PASS（本机Linux组件验证）：唯一容器/卷spug-readback-limits-unit-20261105，仅只读挂本任务源码；无docker.sock/端口/远端连接，volume唯一label已固定。完成检查退出并只清自有资源。

- Linux首轮181 PASS、14 package fixture ERROR：Windows Git worktree .git绝对路径在容器不可解析，未视为产品通过。准备在同一自有卷复制仅组件所需源码、创建真实本地Git快照并复跑全部，子进程显式继承PYTHONPATH；不修改服务器或发布包。

- REGRESSION: Windows适用package/retained/storage/smallapp -> 118 PASS /10 POSIX skip；Linux真实源码副本与真实Git快照执行同套加native retained -> 195 PASS /0 skip（含Windows不适用的全部项和实际SAFE/FAST新增limits构造用例）。首轮Git路径错误已修复，不掩盖失败。
- GREEN: readback-configuration-audit -> 实际正式16GiB合同通过，SQL独立64GiB；885表/512156行；同一FULL、PHYSICAL_FILES、原Redis DB1绝对过期适配器。审阅SAFE后续物理文件apply_tree签名、独立版本校验、引用与Redis路径，无新增接口不匹配。

- GREEN: experience-preflight -> PASS（本任务自有只读诊断进程收尾）：此前audit selected_chain触发冻结SAFE完整归档扫描，SSH60秒超时留下PID30112。已只读核实精确python -B -及该唯一FULL对象文件，停止仅此自有诊断读进程；不停止控制器、业务或其它PID6387。后续审阅只读取小型已pin元数据，不重复全包扫描。
- GREEN: experience-preflight -> PASS（修复隔离发布与安装）：实现04f5f9ce958b52479c0c729fe32dbb69669e73fb已通过Windows118与Linux195必要回归。新专用路径C:/Users/D01021/.codex/worktrees/spug-readback-limits-release-20261105/Maintance，分支codex/release-spug-readback-limits-20261105，从精确已提交内容构建，输出置private/readback-limits-release-04f5f9c。无主程序构建/发布或新环境范围；仅原.58自有控制服务新引擎和合法预算，保留原失败字节。

- GREEN: readback隔离发布构建 -> 精确04f5f9c、实际包/retained 27 PASS，3项POSIX已在Linux通过；构建前后git status为空，无新提交。SAFE manifest 7474080922c85c5a03ab514176f9fcd32af6a585a657ae25eb07c20c66839b7b，原完整验证保留。安装仅新engine-readback-04f5f9ce、合法owner和控制指针，核原History353六pins和预约不变。

- GREEN: .58合法预算组件安装 -> 实际新engine-readback-04f5f9ce及控制/owner pins回读通过；正式dataLimits=16GiB，maxExpandedBytes=64GiB，target/source配置不变。原History353六份结果/配置/请求/预约/claim指纹完全不变，原预约仍在；只重启自有控制器，未启动业务或派发恢复。
- GREEN: experience-preflight -> PASS（第三次失败的显式同点准许）：采用已验证的retained CLI；原exit1/timeout=false/FAILED_RETAINED、原进程退出、同一DB UUID/885表/停写严格校验；追加准许仅原FULL→原MAIN，历史原件不动，下一实际UI操作消费一次。

- GREEN: 第三次失败显式准许 -> 原结果保持FAILED_RETAINED、6pins原字节不变，追加clearance/release，未派发恢复。第三次10份本地UI/终态/进度文件逐字节复制至restore-attempt-3并SHA固定，仅移除已保全的本地submission防重入口，远端历史不动。
- GREEN: experience-preflight -> PASS（第四次真实Spug恢复）：仅同一新FULL smallapp-73cd541a95d84d6a86f9d693e4053c75→同一.58 MAIN；使用原真实前端选择/确认，页面提交一次；不得API或SQL直接恢复，HTTP202不等于成功。保持追踪新唯一operationId至终态及最终验收。

- GREEN: experience-preflight -> PASS（本次发布与本机组件环境收尾）：精确worktree 04f5f9c、构建/验证后无脏状态与新提交；仅删除本次spug-readback-limits-release-20261105/Maintance，核Git登记与物理路径均消失。仅清理本任务两已退出Linux组件容器及唯一无引用卷，保留测试回执，不删镜像或其它任务资源。

- 第四次实际Spug POST一次：smallapp-2f4e3cd6b481402085838015c44e5cae，HTTP202/RUNNING；真实登录/选择/确认通过。原第三次失败保留，目标及新FULL不变；启动只读真实UI watcher，继续至终态，未宣称成功。

- 第四次History354：SOURCE_CATALOGUE_UNAVAILABLE准入失败，无owner操作目录、worker、claim或新宿主预约，原第三次clearance未消费；目标未再变更。失败8份本地证据保存在restore-attempt-4，原远端历史不变。
- GREEN: live source catalogue检查3次每次约0.76秒，实际source_admits全部通过；新FULL实际安装resolver/point SHA匹配准入通过。仅能证实先前请求时不可用、现在恢复，未伪造过去原因。
- GREEN: experience-preflight -> PASS（第五次真实Spug同点请求）：第四次为明确准入失败且零变更，原第三次准许仍未消费；已完成当前源/目标准入，真实UI同点同目标只提交一次，不改变超时或自动重试策略。

- 第五次真实UI一次POST：smallapp-6cb9423086fe4b62ad21505e189bc36b，实际04f5f9c owner/worker已启动并读取归档，原第三次准许被新claim消费，旧FAILED不变。保持追踪同一编号，不重复提交；终态及业务验收仍待完成。

- 17:27第五次恢复checkpoint：真实新操作配置dataLimits16GiB/SQL64GiB，提前构造校验已通过；原完整归档校验后目标准备39.123秒completed=true/PREPARED，恢复前置检查开始。实际破坏性调用mutation=true并exit0，证据fifth-preparation-checkpoint.json；业务仍保持停止，未把准备完成当恢复成功。

- 17:49 History355 checkpoint：restore-admission/target-checks/sql-stage/sql-expand均completed=true，数据库恢复继续运行。真实恢复未到终态，数据库全数据回读、对象/Redis及业务页面未验收。证据fifth-database-phase-checkpoint.json。
- 源引用基线只读摘要：9074条数据库引用行、8786对象引用、sourceMissingReferenceCount=0，Redis为必需RESTORE/绝对过期适配器；不把源基线摘要当作目标验收。正式源五服务运行/UP/HTTP200，未在测试恢复期间重启源。

- 18:02 History355 SQL import completed=true，独立sql-readback开始；合法16GiB配置未再次触发FORMAL_DATA_LIMITS_REQUIRED，数据库整体恢复仍RUNNING。17:53只读核对同一数据库UUID、750张表；后续完整表数/行数/哈希以最终原生比较证据为准。未启动三业务服务，未重复提交或直接执行SQL恢复。

- 18:04只读确认同一目标UUID已885表。18:12–18:15仅观察当前worker身份、直属子进程及readback临时文件元数据（不读取业务值、不查询额外行内容）：回读表目录由327→348→417→532持续增长，证明独立数据回读实际推进；目录计数不是已校验通过数。复核.57的12个受保护容器配置/挂载不变，11个PID及启动时间不变，唯一MinIO变化属于本轮已授权采集生命周期，source-after-full-preservation.json PASS。

- GREEN: 18:29 History355 database-restore/sql-readback completed=true；独立读取实际database-comparison.json核SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF、fullSchemaDataEquivalenceVerified=true、885表/512156行、目标原UUID和容器ID。源observation SHA814bbdcc9ae339e8e8ee164cab83886fe55a3b9ce1d9017d4eebfc8299f6e988与本轮新FULL基线一致；原比较文件pin记录于fifth-database-comparison.json。对象恢复已开始，后续Redis/引用/应用/真实页面及整体终态未完成，不将数据库通过当整体恢复成功。
- 本机验收准备检查：46个Python辅助脚本AST及128份公开JSON解析通过；公开JSON凭据字段无明文字段值命中。首次git检查误关闭换行规范化，将既有CRLF误判为全文件尾随空白；按仓库实际设置并显式cr-at-eol重验exit0，无改动文件换行或编码。

- 18:29后object-restore实际运行，读写持续。附件进度只读观察首轮rglob/stat碰到恢复器原子改名临时文件而失败；次轮错误假定changedPaths全为文件，实际合同含目录而断言失败。均为诊断脚本失败，未修改目标或实际恢复结果。按真实inventory合同只统计清单最终节点及lstat元数据后，18:43 observed 9369文件/9463目录/104尚未出现节点，共18936节点，文件9656139401字节；这仅是复制进展，不是内容/对象版本验收。objects-copy-live-summary.json保留该摘要。

- 更正上述18:43元数据观察的进度推断：原生文件完整readback已生成，MinIO实际已于18:41:42启动；因此104清单节点“当前未见”不能推断尚未复制，运行服务可改变临时/系统节点。摘要字段已明确为currentlyAbsentPlannedNodeCount并附限制，保留原统计数；复制/内容结论以原生physical-step-000-readback及对象比较为准。当前是S3对象层独立回读，非重复恢复，后端/前端仍停止。

- GREEN: 18:50 History355 object-restore completed=true；实际physical-comparison.json为PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF、exactVersionIdentityVerified=true，5916版本、0删除标记、4920唯一内容、9653189892字节。comparison pin和版本历史SHA保存在fifth-object-comparison.json；正在consistency，尚未宣称整体成功。文件复制进度摘要仅观察值，正式附件验收以此独立比较为准。

- 18:52 consistency和Redis恢复阶段completed=true；18:56只读实探backend health=UP/docker healthy。18:56:57原生application-start completed=true、原五服务全运行，进入最终archive-verification；整体仍RUNNING。
- BDD: 启动后真实只读页面验收 -> Given 同一新FULL到原.58 MAIN的数据/附件/引用/Redis阶段完成且application-start通过，When Playwright按既有凭据真实登录并从系统管理进入用户管理，Then 身份/菜单/版本可核、真实列表非空、businessMutations=0。最终整体成功仍须原进程exit0及完整回执，不以页面通过替代。
- GREEN: experience-preflight -> PASS（应用启动后真实只读页面验证）：原五服务均运行、backend实际UP、原生application-start已通过；只在http://172.30.30.58:8081按文档既有芋道源码/admin最终只读验证，无业务创建/编辑/删除、无API或SQL写入。登录/验证码仅走真实前端；完整人员数据和截图仅私密目录，公开结果只摘要。当前最终归档核验仍运行，页面结论不得冒充恢复终态。

- GREEN: 18:58真实Chrome登录后按菜单进入用户管理 -> PASS，2117条/当前20行，version=2026-11-03-12-15-42，businessMutations=0，真实权限身份核验通过。target-after-restore-business.json只摘要；页面及人员内容仅private。该验证在已通过application-start之后进行，与最终只读归档核验并行，不替代native终态。
- 18:59正式来源最终只读观察：原5个ID/镜像/PID/启动时间维持采集后状态，backend UP/frontend200、source共同锁无kernel owner；不曾在测试恢复期间再启停源服务。History355最终archive-verification仍RUNNING，等待原exit及完整结果/清理pins。

- GREEN: History355最终SUCCEEDED，原生finishedAt=2026-11-05T11:04:19.902442Z、actualExitCode=0，archive-verification及restore-cleanup完成，工作进程退出。真实UI原编号终态和截图保留，观察过程POST=0。
- 最终资源释放验收初版错误要求外层execute/result.json与内层worker-result.json为同一路径；实际合同为外层originalResultPins引用内层。只读核清后修正验收脚本为精确pin引用、内层成功/exit0及data逐值一致，再核exit/预约/active。未改结果、原引擎或历史。
- GREEN: verify_restore_evidence.py -> PASS，21个小型证据pins、同一新FULL、885表/512156行、5916对象版本/4920内容、全部引用及约束通过，原第三次失败6pins原字节保持，VALIDATED_CHILD_SUCCESS释放宿主预约、active不存在。本轮Redis DB1原快照0键，恢复及独立校验0键，非空Redis案例不在本轮证明范围。
- GREEN: verify_restored_runtime.py -> PASS，五个原容器/镜像、UUID保持，backend UP、frontend200、replacement SUCCEEDED。独立真实页面PASS补充native businessAcceptance=NOT_PERFORMED，不修改原字段、不冒充完整业务回归。完整结论及限制见acceptance-report.md。

- GREEN: task-closeout -> PASS。final-release-worktrees-readonly.json复核两专属发布目录物理路径/注册均不存在，无新提交无需合并发布副本；readback-limits-cleanup.json记录自有Linux两容器和无引用卷已清理。19:14 stable-control-paths.json复核.57/.58自有控制服务均active/enabled、配置pins通过，python/工作目录/PYTHONPATH和C:/Spug通道不依赖已删除worktree。实现提交9176b3c/04f5f9c保留，按清单不自动融合int_main；开发目录仍供原三服登记任务使用，不删其它任务资源。本轮从ready_for_closeout转completed，最终记录单独提交。
