# Spug 接入

## 三服当前版本查询（2026-10-20）

任务计划中的「三服 IntRuoyi 实际版本（只读）」：更多→执行测试→确定，查看三服登记主系统的前端、后端镜像与摘要、MySQL实际版本、表/视图数量及查询时间。更多→历史记录→详情可重新查看。

该任务仅手动运行，不构建、不部署、不备份、不恢复。Spug容器无法直连服务器时，本功能明确采用本机Windows SSH查询服务（127.0.0.1:18086，经host.docker.internal访问），没有自动备用路径。此电脑及查询服务须在线；当前用户登录自启已配置。查询失败明确报错，不取旧记录冒充当前版本。三服主实例更名后更新原私密目录 `runtime-versions.private.json` 中登记；版本名称按真实镜像摘要匹配。详见 `doc/tasks/20261020-spug-runtime-versions/task.md`。

入口：http://127.0.0.1:18080/schedule 。官方 v4.0.1 独立实例，镜像固定 digest。
已完成平台配置、TEST 手动检查入口、原部署操作查询和真实页面历史读回；**Spug 触发实际部署尚未验证**。

## 用户操作

1. 登录。通过本机或私有地址访问出现“未能获取到访问者的真实 IP”时，点击“知道了”继续。
2. 打开“任务计划”，找到“发布测试服”或“发布状态查询”。
3. 点击“更多 → 执行测试”，查看明确版本、原操作和部署/验收结果。这是实际执行当前只读脚本，不是模拟发布。
4. 使用“更多 → 历史记录 → 详情”查看持久记录。

四个原任务全部未激活，publishEnabled=false、productionPaused=true。不要激活定时任务。
“发布测试服”当前默认检查；“发布备份服”“发布正式服”显示关闭或暂停原因，不提交部署。
下一候选由正常发布主链产出、明确选择并核定。接入任务不会自动选择最新包、构建或重新部署。

本机 IP 警告来自已安装 Spug 的 account/views.py：默认 verify_ip=true 时，has_real_ip 要求来源 IP 满足 ipaddress.ip_address(...).is_global。本机/私有地址不满足该条件；警告不表示登录失败。已用 Playwright 真实登录、关闭提示并进入任务页面；没有伪造公网 IP、关闭检查或修改 Spug 源码。

## 当前真实结果（2026-10-12）

明确绑定的历史成功包：release-20261011-203440-3d567df9857d-app，工作流 rw-5d206b23d31a，原 TEST 操作 bf37637e-1059-4255-be00-36bc46818cde。身份来自监督提供的真实前端部署证据，并与正常后端原操作逐项核对。

- 原操作当前 succeeded，实际目标和包/manifest/源码身份匹配，显示“部署：已成功”。这属于既有后端部署，不是 Spug 本轮提交。
- 切换控制台构建模式前，原工作流为 FAILED / TEST_ACCEPTANCE；部署成功与完整验收失败分开记录。
- 控制台已按用户授权切换正常构建模式。旧工作流详情目前返回业务错误编号 500；页面显示“完整验收：当前详情不可查，未证实”，原操作仍单独显示。查询以 exit=2 失败结束，未用历史缓存代替实时详情。
- 正常构建模式不提供旧 existingPackageBindingSha256 / executorPublisherSha256 批准。这只关闭“接纳已有包”动作，不阻止登录、原操作查询和检查入口。
- BACKUP 入口在网络请求和部署预留前拒绝 TARGET_PUBLISH_DISABLED；PROD 拒绝 PRODUCTION_PAUSED。

Spug 将非 0 退出显示为“执行失败”。本轮 TEST/状态查询的标记表示详情查询失败，原部署成功单独展示。不能改数据库补绿，也不能把查询成功或请求受理当完整发布验收。

## 已安装命令与 API 契约

| 原任务 | 安装命令 |
| --- | --- |
| 发布状态查询 | python3 /opt/intruoyi-spug/release_adapter.py --target ALL --mode status |
| 发布测试服 | python3 /opt/intruoyi-spug/release_adapter.py --target TEST --mode check |
| 发布备份服 | python3 /opt/intruoyi-spug/release_adapter.py --target BACKUP --mode publish |
| 发布正式服 | python3 /opt/intruoyi-spug/release_adapter.py --target PROD --mode publish |

适配器只调用已有正常后端 /admin-api，无裸 SSH、SQL、Docker socket 或自行切容器。
只读客户端仅允许认证 POST /system/auth/login，其他写请求在发出前拒绝。

| 入口 | 当前行为 |
| --- | --- |
| GET /infra/runtime-control/operations | 按明确原操作编号、动作、目标和包身份核对，不取最新操作 |
| GET /infra/runtime-control/release-workflows/{workflowId} | 查询所选工作流，实际错误必须显示 |
| GET /infra/runtime-control/release-workflows/creation-context | 检查当前模式和来源；缺旧批准不阻止原操作查询 |
| --mode admit | 未启用；对应已有 admit-existing-package {reason, sourceSelectionId, expectedSelectionDigest}，独立批准匹配后单次接纳，绝不自动部署 |
| --mode publish --target TEST | 未启用；对应已有 publish-test {reason}，要求合法 READY 候选、服务端选定身份和发布开关 |
| BACKUP / PROD 发布 | 本轮保持关闭，正式维护暂停 |

本轮未调用接纳、构建、发布、mark-tested、恢复或失败处置接口。后续实际发布顺序和授权由正常后端主链负责，本接入不扩大窗口。

## 明确候选、私密输入与持久记录

仓库外私密目录：E:/Int/CacheData/IntRuoyi/spug-integration-20261010/，ACL 限当前用户和 SYSTEM。管理员、数据库、控制台合法账号分别存于已有 private 文件，不能打印或提交。
candidate.private.json 必须包含明确的 workflowId、releaseTag、packageDigest、manifestDigest、applicationCommit。
历史查询可另行明确 observedTestOperationId 和 TEST 目标三项绑定；后续新候选必须重新核定，不能沿用旧操作编号。
模板故意留空必需值，不提供默认成功输入。setup_private.py 只初始化缺失配置，不覆盖已有输入。

查询快照位于独立卷 /var/lib/intruoyi-spug/queries/，原子写盘、fsync、读回，保留实际组件错误和请求路径，不保存凭据。Spug 原任务历史由其数据库保存，重新登录从真实页面读回。查询快照不是部署提交回执。

未来提交先按后端/租户/工作流/目标独占预留，再单次 POST，随后持久绑定原 operation。换 attempt、并发、超时或响应未知不能重 POST；未知状态保留原预留，仅查原任务。
接纳已有包另按后端/租户/包/批准来源独占预留，接纳成功与部署是两个明确动作。
本轮部署提交回执数量为 0，未接纳新工作流，未解除失败或暂停。

## 验证、证据与有限待项

- python ops/spug/local_checks.py：契约、真实文件 IO、并发预留、子进程读回和拒绝路径；Windows 与实际 Spug 容器运行，不 mock 后端。
- node ops/spug/browser_test.mjs schedule-live-configure：真实 UI 配置四个原任务，可用 --targets=TEST 限定自有改动。
- node ops/spug/browser_test.mjs schedule-live-test：真实登录、执行检查/查询和关闭拒绝路径，不是部署测试。
- node ops/spug/browser_test.mjs schedule-live-history：重新登录读回原历史，不重新执行任务。
- python ops/spug/audit_readonly.py --live --output doc/tasks/20261010-spug-integration/live-final-audit-20261012.json：最终只读核对原任务 ID、未激活、匿名 401、持久查询和零部署回执。

本轮原件在 doc/tasks/20261010-spug-integration/：live-backend-binding-20261012.json、live-backend-context-changed-20261012.json、live-real-ui-20261012.json、live-real-ui-persistence-20261012.json、真实 history 截图及 live-entry-handoff-20261012.json。旧记录保留。

有限待项：新正常候选冻结后的明确身份绑定与完整只读联调；有明确手动部署授权后验证实际提交和原任务终态。当前不绑定构建中候选，不恢复旧控制台，不要求执行者停工或回复。
三服实际发布、正式自动 NAS 备份和完整应用验收由原发布职责推进，不能把平台接通当作这些验收通过。

compose 项目 intruoyi-spug，数据库/应用/历史独立命名卷，代码与私密输入只读挂载。本轮未重启本实例、共享 Docker 或执行者控制台，未操作三服/NAS，未激活调度。

## 2026-10-14 主机登记与独立备份恢复入口

三服经真实页面登记、重新打开编辑框读回及只读 SSH 核验：TEST 172.30.30.58 为 hostId 1，BACKUP 172.30.30.59 为 hostId 2，PROD 172.30.30.57 为 hostId 3。使用现有独立密钥，仅连接认证；没有追加远端 authorized_keys、创建账号或执行部署。证据见 hosts-registration-20261014.json。

新增 smallapp_adapter.py 是 W01 现有执行桥的客户端，不另写备份或恢复器。FULL、INCREMENTAL、RESTORE 使用同一请求/结果契约和适配器，应用只通过已登记配置引用选择；不以小程序分支代替真实备份引擎。

入口代码与三个新手动任务配置已完成：FULL taskId 7、INCREMENTAL taskId 8、RESTORE taskId 9。三个任务均未激活，重新打开编辑框、刷新页面及最终只读 API 核对通过，未执行业务操作。smallapp_tasks.mjs 不改原发布任务 1–4，已有同名任务会核对并复用，不重复创建。

配置过程中曾返回“账户已被系统禁用”；用户随后确认账号恢复。只读核实 admin/id=1 当前启用、当前合法私密凭据匹配，再经真实页面成功登录。原 admin.private.json 凭据已不匹配当前账号，本任务没有修改密码或启用状态。配置程序显式选择现有 build-test-spug-login.private.json，命令为 node ops/spug/smallapp_tasks.mjs build-test-spug-login.private.json；只传私密文件名，不传密码，不能自动尝试多个凭据。

执行桥连接仍缺 W01 实际交付。客户端要求已存在的私密 smallapp-bridge.private.json，明确 submitUrl、带一个 {operationId} 的 queryUrlTemplate、credentialRef，以及 sourceConfigRefs/targetConfigRefs。认证只从同一私密目录引用读取，不进入页面、命令或日志。没有创建猜测地址或空认证配置；实际 W01 传输方式须与交付一致后才能标接通。登记引用不代表实际源/新目标已验收，W01 服务端必须核定资源、授权及同一执行引擎。

计划的三个手动入口：

| 操作 | 必需输入 | 当前状态 |
| --- | --- | --- |
| FULL | 当前已登记源引用和稳定 operationId | 任务 7 已保存；执行桥未绑定 |
| INCREMENTAL | 上述输入及真实 FULL 产生的 parentChainRef | 任务 8 已保存；真实父链尚未产生 |
| RESTORE | 真实 FULL+I1 recoveryPointRef 及已登记全新目标引用 | 任务 9 已保存；恢复点及目标事实待交付 |

首次保存的任务命令原件继续保留为历史证据。当前接入使用下面的业务选择页面，用户无需编辑命令。真实父链、恢复点及全新目标由已安装执行器的只读选择接口核定；缺输入直接拒绝。同编号和同请求只允许一次持久提交；重复点击、响应未知或并发只查询原编号。换请求复用编号拒绝，不自动补发。

原任务和执行快照保存在 /var/lib/intruoyi-spug/smallapp，采用真实独占写入、fsync、原子更新和读回。输出仅有状态、符号错误码、日志引用及结果引用。CREATED/RUNNING/UNKNOWN 均不是成功；Spug 的非零执行标记须结合明确原状态阅读。执行桥 SUCCEEDED 仍不能代替 W06 的实际业务页面验收。

Windows 和实际 Spug 容器的 7 项相关验证通过，覆盖契约、真实并发 IO、原编号仅 GET 查询、错误及凭据拒绝；未模拟执行桥成功。实际容器缺连接配置时拒绝 W01_TRANSPORT_BINDING_REQUIRED，submissionIssued=false。真实 FULL/I1/RESTORE 三次业务触发均为 0，整体备份恢复未验收。新独立演练不改变原发布 HOLD、正式暂停或定时状态。

### 2026-10-14 小程序 r2 业务页面接线

业务页面：`http://127.0.0.1:18080/backup-restore/`。沿用 Spug 登录和权限、任务 7/8/9 的原派发器及原生执行历史。页面选择已登记应用/来源、真实已接受父链或恢复点和全新独立目标，不允许输入路径、凭据或 shell。FULL 只要求当前来源与本次执行条件，不等待未来父链、恢复点或完整恢复目标。小程序与 IntRuoyi 共用适配器和原执行器，只按登记资料选择应用，不另写备份引擎。

`smallapp_registration_settings.py` 消费 W08 现有纯校验器及 `delivery.json.artifacts` 的真实字节/SHA，保存登记原件快照并产生四字段公共设置。程序拒绝交付摘要和实时文件不一致；不读取变化中的文件并冒充已冻结版本。设置只代表登记元数据，不代表已安装或可执行。`smallapp_entry.py` 每次读取当前设置；设置缺失时页面如实未就绪。

W01 源码已有原 `GET /selections`；实际部署和本容器可达性仍待核。私密 `smallapp-bridge.private.json` 在原字段之外使用同源 `/selections` 的 `selectionUrl`，以及实际安装原件的最小 `registrationBindings` 数组。每项精确三字段为 `applicationId`、`registrationSha256`、`engineSelectionRef`，来自 W05/W01 实际安装回执，不能填推测值。该投影只绑定原登记版本，不是新授权框架，不改变公共请求/结果和 W01 八字段选择接口。缺少投影或版本不一致拒绝新提交；旧原编号仍可查询。首次 FULL 允许 `targetConfigRefs` 为空。

页面意图先写本机持久原件，再由原 dispatcher 调用静态任务模板及唯一 `--prepared-operation` 编号。新派发前再核登记 SHA、来源和原桥身份。响应未知、换页、重复点击和子进程重复调用不会另执行；相同来源未解决的原操作不能通过新编号绕开。未来真正新业务使用新 operationId。

当前任务模板接线未完成：真实页面读回发现 taskId 7 的 `is_active=true`，与原已核未激活基线冲突；8/9 未激活且仍为原命令。本轮预检全部三项后立即拒绝，修改数 0，没有停用或重写任务 7。`smallapp-template-conflict-20261014.json` 是准确原件，不能把旧配置通过当当前页面可执行。实际接口也要求任务未激活且命令精确匹配后才可新派发。保留的旧参数命令只有 `--query` 可以查询原件，缺业务页面持久选择的新执行直接拒绝；将来私密桥到达也不会使原已激活命令突然执行 FULL。

本轮只给本实例 Nginx 增加有限路由并 reload，启动自有 loopback 页面服务；未重启 Spug、MariaDB、Docker 或原 API/调度进程。原启动配置已追加自有程序，compose 自有 bootstrap 可在下次正常容器启动恢复路由；未为验证重建或重启容器。配置和持久原件位于既有 integration_records 卷。

真实 Playwright 登录、三个操作页、桌面及手机布局、未就绪禁止执行、匿名 401 已验证；浏览器未产生登录之外的 POST。一次实际缺登记页面切换报错已修复并仅重验此路径。追加真实子进程核对原已激活命令的拒绝路径后，Windows/实际容器各 13 项相关短验通过，未模拟可用引擎。原件见 `smallapp-business-ui-20261014.json` 及 `smallapp-business-*.png`。

2026-10-14 18:55 已完成本地配置接线：沿用原私密目录和只读挂载，`smallapp-bridge.private.json` 引用 W05 合法交付的 `smallapp-bridge-headers-r2.private.json`；三个接口同源绑定 `http://host.docker.internal:18083`。现有解析器真实读取并校验私密引用，未输出凭据或凭据摘要，网络调用为 0。W05 已通过原 dispatcher 配对实测本任务 Windows 私有 SSH 到 `.59:18083` 的路径，原生接受的 peer 为 `172.30.30.59`；探测监听和转发已经关闭，该记录不代表当前执行桥在线。

当前 W08 登记 29922 字节、摘要 `47fb0cbaba7fba26a533ef7c13f2af9d6dee302e74204ddcbd83aad55ef69d38` 已经由原校验器消费。公共四字段设置、登记原件快照已保存至原持久卷并用原 `settings()` 读回，显示逻辑应用 `smallapp-20261014-r1`、来源 `smallapp-20261014-source-r1`、版本 `smallapp-20261014-r2-redis`、执行器 `common-engine-smallapp-r2-20261014`。本地登记映射是当前预期身份，不能代替实际签名登记导入或业务准入。公共目标列表仅为登记元数据；私有 `targetConfigRefs` 暂为空，不提前放行恢复，也不阻塞 FULL 接线。

剩余为 W05/W01 当前签名安装、实际登记导入和服务准入后恢复私有转发，再从原 caller 完成一次 authenticated `GET /selections`；若最终登记身份更新，先消费新的真实原件。任务 7 活动态归属及原三模板仍未改变，旧 FULL 新提交拒绝继续保留。只读拒绝页面和本地解析通过均不是实际应用选择、FULL/I1/RESTORE 或完整恢复验收；真实业务仍等待 root 的分阶段授权。

## 2026-10-14 Spug 实际构建、上传及测试服部署

`release_build_test.py` 通过原发布后端提交固定来源、标准构建、NAS 上传和同包 TEST 部署。当前自有手动任务为“构建并发布测试服” taskId 5、“本次构建发布结果” taskId 10、“继续本次构建发布” taskId 11，均未激活。任务受理返回 `SUBMITTED_NOT_PASSED`；只有原构建、部署和托管浏览器验收都通过才返回 `BUILD_NAS_TEST_BROWSER_PASSED`。

本次工作流 `rw-fab1d0d20f70`，releaseTag `release-20261014-014655-fab1d0d20f70-app`，实际已完成一次构建和 NAS 上传，同包部署到 `http://172.30.30.58:29081`。原构建和 TEST 操作都 succeeded；部署 COMMITTED，镜像身份匹配，后端 UP、前端 200，原有 4 条数据和 3 条迁移记录未变。不是原查询任务读出的旧部署。

首轮响应超时的原件完整保留，限定关联原构建后继续，无第二次构建或重复部署。status 对已绑定原操作实时读回；worker 丢失时，continue 只允许明确的 BUILDING/DEPLOYING 身份，使用跨进程文件锁。未知提交、STOPPED、失败或恢复状态均拒绝重 POST。专用检查 11 项、原适配器检查 18 项在真实 Spug 容器通过。

当前完整托管验收 NOT_PASSED：原工作流 RECOVERY_REQUIRED / APPLICATION_BROWSER_ACCEPTANCE，浏览器启动前因正常五字段 controlSource 与两字段审批记录整体比较而失败。通用校验修复在独立控制程序候选内，16 项 Java 检查通过；当前旧工作流、失败回执和旧包没有改写。Spug 历史 24 返回状态 2，重新登录后读回通过；提交历史绿色只代表受理。

详细状态与证据见 `doc/tasks/20261014-spug-build-test/task.md`。真实测试页面只读登录及重新登录也已通过，不能代替托管业务验收。正式服、备用服和备份恢复不属于这次构建发布验证范围。
