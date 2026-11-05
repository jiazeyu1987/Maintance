# 正式服全量备份并经 Spug 恢复到测试服

## Current Status
completed

2026-11-05 19:14 收尾完成：本轮FULL和History355恢复真实成功，最终原生/运行/页面验收通过；两个本次临时发布worktree的Git登记及物理目录均缺失、自有Linux测试环境已清理。实际.57/.58控制服务active/enabled，配置pins和稳定运行路径验证通过，C:/Spug守护通道不引用发布worktree。实现已单独提交9176b3c/04f5f9c；本记录独立收尾提交，不自动融合int_main。原三服登记任务仍独立保留续作，不扩大本轮成功范围。

2026-11-05 19:08 最新：History355 / smallapp-6cb9423086fe4b62ad21505e189bc36b真实SUCCEEDED，原生finishedAt=19:04:19、actualExitCode=0；21个证据pins/原第三次失败6pins/宿主预约释放均独立通过。885表/512156行、5916对象版本、引用完整性通过；Redis本次受控DB1快照0键，值与绝对过期校验为空集合通过。原五容器/镜像/UUID保持，backend UP/frontend200，真实登录/用户列表2117条PASS且businessMutations=0。必要实现验证已完成，记录最终验收并完成任务记录提交及本任务发布目录/稳定运行路径收尾复核；原三服登记任务剩余项仍保留，不以本轮路径成功宣称三目标全就绪。

2026-11-05 18:59 最新：History355 consistency/Redis/application-start均完成，原五服务全运行。真实Playwright登录及用户管理页面PASS：2117条/20行、版本2026-11-03-12-15-42、businessMutations=0。正式源仍五服务正常/UP/frontend200，当前恢复仍RUNNING于最终archive-verification；完整原始终态、证据pin及清理验收尚待完成，暂不能标记成功或completed。

2026-11-05 18:50 最新：History355数据库和object-restore均完成；对象比较PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF/exactVersionIdentityVerified=true，5916版本/4920唯一内容/9653189892字节。MinIO已启动，正在consistency；Redis、应用启动、整体终态和真实页面仍待完成。

2026-11-05 18:29 最新：History355数据库恢复及独立全数据回读已完成；实际比较885表/512156行，fullSchemaDataEquivalenceVerified=true，原测试DB UUID不变。fifth-database-comparison.json固定实际比较123480字节/SHA256。已进入object-restore，附件、Redis、引用一致性、业务启动与真实页面尚待完成。

2026-11-05 18:02 最新：History355 SQL import completed=true，实际进入sql-readback；database-restore仍运行。合法16GiB预算已越过原延迟拒绝位置，独立全数据比较结果尚待完成，不能以SQL导入完成代替恢复成功。原两基础服务运行，三业务服务仍停止。

2026-11-05 17:49 最新：History355同一新FULL→原MAIN，目标准备、完整恢复前置检查和target-checks均通过；SQL stage及展开完成，正在数据库恢复流程。原生worker持续，业务三服务停止；数据库独立回读、附件、Redis和真实页面尚待完成。

2026-11-05 17:10 最新：History354仅来源目录准入失败，零worker/目标变更，连续3次源鉴权与精确新FULL准入恢复通过。真实Spug第五次 smallapp-6cb9423086fe4b62ad21505e189bc36b 已在新04f5f9c实际worker运行，正在完整归档校验；同一新FULL→原MAIN。恢复/页面最终成功尚未确认。

2026-11-05 17:02 最新：04f5f9c提前校验修复及合法16GiB预算已安装，Windows118/Linux195通过，精确release无新提交且已清理。第三次失败10份证据已保全，显式同点准许追加、原6pins不变。真实Spug第四次操作 smallapp-2f4e3cd6b481402085838015c44e5cae（同一FULL→原.58 MAIN）HTTP202，仅受理，等待完整终态与验收。

2026-11-05 16:44 最新：History353 FAILED_RETAINED，数据库885表已导入但独立回读因非法64GiB dataLimits失败；业务仍停止，对象/Redis未恢复。正式修复配置并提前校验，保留失败后继续同点同目标。

2026-11-05 15:47 最新进展：修复提交9176b3c与SAFE/FAST实际包回归通过，Linux142 PASS；新安全组件代次安装，原失败结果/claim/6份pins保持字节不变，显式同点同目标准许追加。已由真实Spug页面提交第三次恢复 smallapp-91cc5c0b4b054cb38075681f1aca7d4a（同一新FULL→原.58 MAIN），HTTP202仅受理，最终恢复和业务验收尚未完成。测试服主程序仍按停写状态等待恢复器。

2026-11-05 15:06 最新进展：History352 已 FAILED / RESTORE_TYPEERROR，原worker实际exit1且已退出；MySQL同一UUID的应用库已被清空（tableCount=0），MinIO/Redis清空尚未执行；后端/前端/MinIO按恢复准备已停止，保持停止防止空库启动。根因已定位到安全包注入的 recovery_replace.prepare 使用 lightweight-only content/verify_content 参数，与冻结安全版 recovery_data_files 签名不兼容。进入本机正式构建契约修复与RED/GREEN验证，随后准备保留FAILED_RETAINED及资源保留记录的显式恢复计划；不得直接清claim、改历史或重试。

2026-11-05 14:50 最新权威状态：新 FULL `smallapp-73cd541a95d84d6a86f9d693e4053c75` 已 SUCCEEDED（History350，14:17:28）。NAS归档14378个载荷文件、26090562595 bytes；完整性COMPLETE、独立回读、原退出0及元数据pins通过，正式源服务UP/HTTP200。

首次恢复 `smallapp-ba0bca490ac243768c8b759fa14a8bbd`（History351）在admission失败 ARCHIVE_ROOT_UNAVAILABLE，无worker或replacement claim，五原容器未变化；全部失败证据原样保存在 restore-attempt-1。已按用户原NAS恢复授权恢复 .58 原canonical只读挂载及持久systemd依赖，来源和新point SHA256匹配，已安装resolver只读准入通过。

第二次真实Spug恢复 `smallapp-af9fb80256c0417f86f2741686950823`（History352）于14:35:48提交一次，精确指向同一新FULL与 .58 MAIN。真实worker已启动并持续读取NAS材料；截至14:49:58尚在写入前校验阶段，五原容器仍运行、启动时间不变。该操作仍RUNNING，未宣称恢复成功，继续跟踪同一编号。

已批准的PROD恢复及Docker管理进程修复已通过：原NAS三挂载/持久启动恢复，源控制和测试目标重启登记恢复，live-restore热加载/仅dockerd重启通过且原12受保护容器保持。备份前正式backend UP/frontend200；两个自有控制服务实际65536文件描述符预算通过，原路径守护保留。源原32657 URL身份及32657/42657/18557持久通道恢复。初次HTTP409、原编号未受理证明和同编号重试均如实留证，不改历史终态。

测试服恢复前基线：原五服务运行，backend UP/frontend200，严格目标准入及原targetConfigRef通过，ledger无活动任务。真实浏览器登录首页/权限/版本通过；实际点击系统管理/用户管理，2117条、当前20行，业务mutation=0。DCC项目代码页暂无记录的失败基线另存，不算数据记录验收。公开回执仅摘要，人员数据/完整页面仅私密存储。恢复后的独立验收尚未执行。

历史CIFS阻塞已随用户重启解除，当前是实际运行任务，goal已恢复active。以下历史阻塞/授权记录按时间保留，不能视为最新状态。上一安装任务的.57恢复目的地仍未启用，本轮仅正式来源到测试目的地，不宣称三服全部可恢复。

## 目标与边界
当前活跃目标原文：“实现在正式服全脸备份一次，通过Spug恢复到测试服”。按全量备份理解；完成定义为真实正式来源全量备份成功、原包及证据完整，经 Spug 真实页面选择该新备份并恢复到测试服，恢复执行终态和目标业务运行/数据一致性验收均通过。不能以登记成功、选择取消、单测或旧恢复点代替目标。

先核当前任务/操作句柄、正式来源配置和共同锁、.58 实际目标身份及占用、用户授权边界。已运行操作沿用原 operationId 查询；超时不当终态、不自动重启或重复提交。只在来源与目标全部前置通过后推进真实执行；不顺带修复正式服异常或清理共享NAS/其它任务资源。

上一自有任务 20261104-spug-selectable-restore-targets 的授权安装已完成且验证、融合及临时发布目录清理通过；其剩余 blocked 为“.57作为恢复目的地身份不稳定”。该阻塞已报告并保留原任务，不能宣称三服全就绪。本轮目标仅要求正式来源→测试目的地，需独立核验来源备份能否执行。上一目标轮分类为 progress：两目标真实安装、页面验收、融合和临时发布目录清理均改变权威状态。

## 里程碑
1. [x] 核活跃目标、最新来源/目标、历史操作及当前进程句柄，冻结本轮操作范围与BDD场景。证据见 current-state.json、exact-source.json、source-runtime.json、original-operation.json。
2. [x] 正式来源全量备份准入及真实页面提交；唯一operationId真实SUCCEEDED，full-terminal-record.json。
3. [x] 新全量包NAS完整性、原始manifest/pins及源实时恢复资格通过，new-full-point-verified.json/new-full-admission.json。
4. [x] Spug真实页面选择该新包与测试服精确目标、确认恢复；逐次保留失败，最终History355同点同目标真实exit0/SUCCEEDED。
5. [x] 测试服运行态、数据库/附件/Redis一致性及真实页面验收；业务边界、发布副本无新提交/无需融合、稳定运行路径和最终清理均验证，acceptance-report.md及final-verification.json。

## 经验门禁
- Trigger：正式服务器备份、测试服务器覆盖恢复、真实Spug长链路与当前操作接续。
- Preflight check：按 docs/experience-index.md 读取命中的 release-backup-restore、server-access、login-access 与 PowerShell 规则现存权威副本；核实际配置、源码/安装摘要、任务锁、活动句柄、来源/目标资源独占性、容量和版本合同。高风险动作前先写 experience-preflight PASS。
- Blocker：来源身份/写入停写范围不可核、活动任务冲突、存储或版本pin漂移、准入拒绝、无真实前端入口、凭据或数据前提缺失，均停止对应动作并保留原始失败；不得改目标绕过。
- Verification：真实原operationId及进程/服务证据、源服务恢复、备份终态/manifest/归档读回、恢复终态/实际目标、数据一致性和业务页面分别记录；原包必须为本轮新全量包。
- Forbidden action：禁止用旧备份或小应用演练冒充正式主程序全量恢复；禁止mock/API/SQL提交代替Spug用户路径，禁止删除失败保留/锁强行重跑，禁止清理NAS或其它并发任务资源，禁止无依据重启主程序。
- Evidence：本目录 execution-log.md、脱敏的操作/验收回执；凭据与原始私密运行态只放 C:/Spug/runtime/private/ 下任务目录。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否，准入失败真实暴露。
- 是否从根因和长期维护角度解决：是，沿已验证正式接口与执行器，必要修复先BDD/TDD并保留运行契约。
- 是否存在临时补丁或绕过：否。

## 预期验证
Given 当前正式主实例与测试主实例身份和资源合同可核验且无冲突操作；When 在Spug发起正式全量备份，再选择该新备份恢复到测试服；Then 两操作分别有真实成功证据，正式源服务恢复正常，测试目标数据与备份一致、页面可用，未影响无关服务器/租户/共享盘。

本轮新FULL已开始且有唯一真实编号；安装回执、历史恢复点及恢复前页面基线均不能替代本轮备份终态和实际恢复验收。

## 本轮核验结论与续行条件
- 续行轮 2：上一轮取得了精确来源故障和原仓储终态的新证据，分类为 progress，但来源故障已首次阻断真实执行。本轮只复验该同一来源阻塞，若仍存在则继续保留原目标，不重复提交、不把检查当作备份成功。
- 测试目标 .58：认证 selected-target 预检通过，控制服务 active，未发现恢复 operation/claim；相关五个容器运行、后端/前端 healthy。该结论不代表数据恢复已经执行。
- 正式来源 .57：配置绑定的五个精确容器中，MySQL、MinIO、Redis、前端实时 inspect 返回；后端精确 ID inspect 5 秒超时，48081 健康接口 3 秒超时。Docker 持久记录为 Restarting=true、Pid=0、ExitCode=137；持久记录不是实时状态，137 不能单独证明 OOM。
- 来源存储：约 1576 个不可中断等待的 Python 进程，样本栈为 cifs_statfs / smb2_queryfs / smb2_reconnect；NAS TCP 445 可达不证明当前 CIFS 会话健康。仅从 /proc 读取，未执行 df/statfs、卸载、重新挂载或 fstab 更改。样本 SSH 连接源为 192.168.112.214，本机当前地址为 192.168.109.82；已询问前者是否仍有旧任务，尚未获答。
- 旧操作 smallapp-3d4c7ab0f65841b8892e4a640a53176d：按仓储合同 SHA256(operationId) 定位原目录；原始 result.json 为 FAILED_RETAINED / ARCHIVE_LEASE_FD_BUDGET_EXCEEDED（2026-11-03T12:15:22Z），原仓储 worker、初次 capture 子进程及最后一次查询子进程均不存在。采集阶段另有成功回执，不能据此改写整个仓储操作结果，也不能把旧点当成本轮新备份。
- 继续条件：正式后端实时身份与 health=UP 可验证、来源 NAS 会话/容量检查可在有界时间内完成、共同锁和所有写入者/活动操作归属通过；然后才可经 Spug 提交唯一新 FULL，再恢复该新包到 .58 并验收。
- 当前没有可安全直接执行的正式服修复步骤。未擅自 kill 旧进程、重启 Docker/主程序、操作 NAS 或更改历史终态。诊断记录保留在本工作区；因必需前置未通过，不提交实现或宣称 completed。
- 目标审计：本轮在最新安装 progress 之后首次证实来源异常，属于 first blocked-preflight turn；活跃目标保持 active，尚未满足连续三轮相同阻塞的 goal blocked 条件。
- 续行轮 2 结果（2026-11-05 01:16 北京时间）：复验同一精确后端仍 inspect 5 秒超时、health 3 秒超时；其它四个配置容器实时 inspect 返回，前端 HTTP 200，共同锁未见内核 owner。新增只读 /proc 证据显示 dockerd PID4794 的 113 个线程中有 1 个等待 smb2_reconnect，当前无该后端 ID 对应 shim。该证据进一步限制直接重启方案，不证明故障已恢复。保留 NAS 挂载，不重启 Docker 或业务容器；需要来源存储/后端运行状态实际恢复后才能继续。连续同类准入阻塞计数为 2，目标仍 active。

## 第三轮完成与阻塞审计
后续用户补充：192.168.112.214“已停止或已关机”。已确认该旧客户端当前不再运行；这不证明正式服已有 D 状态进程退出或 CIFS 会话恢复。仅按既有只读授权复核来源健康与 /proc 进程来源/时间；不将此答复视为 Docker、主程序或 NAS 修复授权。
2026-11-05 01:18:47（北京时间）exact-source-recheck-3.json：同一后端精确 ID inspect 5 秒超时、后端健康 HTTP 超时；其它四个配置容器 inspect 返回、前端 HTTP200。最小必要准入仍失败。

| 原始目标要求 | 当前权威证据 | 审计结论 |
| --- | --- | --- |
| 本轮正式来源真实 FULL 成功 | 三轮来源身份/health 准入失败，无新 FULL operationId | 未完成 |
| 本轮新全量包完整、可恢复 | 无本轮新包或完整归档回读证明；旧操作不能替代 | 缺失 |
| 通过 Spug 将该新包恢复到测试服 | 仅先前目标选择/取消证据，无实际恢复 operationId | 未完成 |
| 正式源恢复运行、测试目标数据及页面通过验收 | 正式后端 health 超时；测试目标仅安装准入通过，无本轮数据恢复验收 | 未完成 |

同一正式源故障连续阻塞三轮，当前轮仅证实未恢复，分类 no progress。不存在确认仍运行、值得继续等待的本轮备份或恢复句柄；不将历史 RUNNING 文件或单次超时当成活进程。现有可安全执行的只读核验已完成；下一步依赖正式服 NAS/后端运行状态实际恢复及相应生产故障处理范围明确，不能靠追加本地改动、重复探测、旧包或跳过门禁达成目标。满足 goal blocked 审计条件，完整目标保持不变，不能标记完成。开发 worktree 和全部证据保留。

## 旧客户端停止后的复核
用户后续确认：“已关闭了，现在只有你处理”。据此确认无已知并行维护，可继续本任务来源排障；不把确认单一处理者扩大为整机/Docker重启或NAS变更授权。先通过有界只读证据确定具体修复范围与影响，再处理需要额外授权的生产变更。
2026-11-05 09:08–09:10 北京时间，用户已确认192.168.112.214停止或关机。after-client-stop.json两次/proc采样相隔约12秒：来自该地址的1973个Python D状态进程仍存在，另外1个Python D进程来自192.168.109.82；两次采样间未观察到Python D进程新增或离开，只能证明该短时窗口，不能外推长期无新探测。旧来源最新遗留进程开始于北京时间09:02左右，关停准确时间未知，不据此否定用户答复。

精确来源复核第一次SSH banner握手超时，未取得业务观察；同一只读检查重试后取得exact-source-after-client-stop.json：后端与Redis精确ID inspect均5秒超时，后端健康HTTP超时，前端HTTP200；MySQL当前healthy，但StartedAt更新为2026-11-05T01:08:17Z（北京时间11月5日09:08）。本轮全部远端只读，不能将启动变化归因于本轮或认定为人工重启。已询问正式服是否有并行维护，未收到答复前不干预现场。用户停止旧电脑的确认没有解除当前来源故障，也不授权业务/Docker/NAS修复；目标继续blocked，未执行新备份或恢复。

## 重启后的真实状态与待执行范围
证据：172.30.30.57-post-boot.json、172.30.30.58-post-boot.json、两服boot-conflicts与boot-repair-measurement.json、boot-definitions.json。完整原始Docker/服务/配置日志保留于本机私密目录，不进入Git。

已确认两服重启、0个D进程、充足内存；.57原MySQL/Redis/MinIO运行，但backend已退出、frontend循环重启、NAS三挂载目标为空且fstab无NAS项/无NAS automount、源控制无启动项。.58原目标数据容器四个停止，原三处数据目录仅mountId变化，其余身份不变。未向无NAS挂载的本地目录写入。

已发出一次明确PROD修复授权问题，范围见post-boot-repair-plan.md；等待答复期间仅进一步读取已有挂载/启动定义，不执行服务或存储变更。只读docker ps publish过滤未返回历史停止容器，不将其误判为无端口配置；完整配置端口匹配证据以boot-repair-measurement为准。目标仍为真实本轮FULL→Spug恢复新包到测试服，当前未完成，保留开发worktree及原始证据，不提交未通过验证的实现。


## 2026-11-05 16:44 第三次恢复失败与正式修复范围

Current Status: in_progress。第三次真实 Spug 恢复 smallapp-91cc5c0b4b054cb38075681f1aca7d4a / History 353 在数据库导入完成后，独立回读以 FORMAL_DATA_LIMITS_REQUIRED 失败；目标同一数据库 UUID、885 张表，MinIO/后端/前端停止。对象和 Redis 恢复未完成，禁止宣称恢复成功或启动业务。原失败、资源占用、任务记录必须保留。

根因：owner dataLimits.max_bytes 配置为 64 GiB，而 formal_data_evidence.validate_limits 的正式合同上限是 16 GiB；该参数计量查询摘要输出，不是原始 SQL 大小。maxExpandedBytes=64 GiB 为独立 SQL 展开上限，不应混用或扩大校验合同。

修复里程碑：先实际发行包组件 RED；将 dataLimits 校验提前到 MinimalData 初始化、任何清理目标数据之前；配置修正为正式 16 GiB；SAFE/FAST 与 Linux 回归；提交实现；从新专用发布 worktree 构建安装；第三次失败追加式保留授权；同一个已成功全量备份点经真实 Spug UI 再恢复到同一个 MAIN；独立一致性和真实页面验收。

### 经验门禁（本轮补充）

- Trigger: FAILED_RETAINED 后继续同源同点恢复，或修改 dataLimits/SQL 展开上限。
- Preflight check: 实际 SAFE/FAST 包构造器提前调用实际正式 limits 校验；独立核对 maxExpandedBytes 与 dataLimits 的含义及上限；保留第三次失败全部指纹；确认原 worker 退出、目标身份和 885 表状态。
- Blocker: 任何非法 limits、活跃旧 worker、目标身份漂移、失败证据变化、未经授权的目标或备份点。
- Verification: 实际发行包 RED/GREEN、Linux POSIX 回归、安装回读、追加式 clearance 消费、真实 UI 终态及数据库/对象/Redis/运行态和页面验证。
- Forbidden action: 不扩大正式 16 GiB 合同、不吞异常、不手工 SQL 续导、不删除失败记录或占用依据、不以导入完成代替恢复成功。
- Evidence: restore-terminal-record.json、readback-limits-contract.json、restore-database-import-progress.json、restore-third-failure.private.json（私密、不提交）。

### 设计约束检查（本轮）

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，分离两个容量合同，并把配置有效性检查前移。
- 是否存在临时补丁或绕过：否，保持实际正式校验、失败保留和真实 Spug 操作路径。
