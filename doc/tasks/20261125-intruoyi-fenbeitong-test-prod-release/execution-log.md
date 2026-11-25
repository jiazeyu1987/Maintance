# 执行记录

- 用户需求：发布 intruoyi 到测试服务器和正式服务器。
- 前序任务：20261125-fenbeitong-runtime-url-fix，completed；应用实现 158f4fed30dd4995b0a2501c07216ce07972d421，维护实现 87faa54b57af43016043bd465adba0c2f88ec77e，均已合入 int_main。
- 初始范围：单包测试到正式，不发布审查服务器，不重发分贝通助手；尚未执行服务器写入、构建或发布。
- BDD: 同包跨环境运行 -> Given 已提交的分贝通运行时配置修复及各服显式地址，When 同一 releaseTag 先通过测试再晋级正式，Then 两服版本一致且页面分别使用本服分贝通地址，正常登录与健康检查通过。
- 任务属于已验证实现的部署，沿用前序 RED/GREEN 证据；不为部署改动生产代码。新增行为如有必要先补 BDD 与 RED。

- 门禁文档已读取：server-access、login-access、release-backup-restore、release-agent-checklist（多机器接管、当前数据库契约、普通执行器安装、构建与两服验收）、worktree-memory、worktree-restrictions、powershell-memory、release-page-acceptance、next-release-menu-repair、invoice-print-runtime-config。旧盘符限制按用户当前可移植路径规则及已验证实际配置执行。
- 只读本机：执行器 PID 21804，稳定入口 C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py，端口 18112；SQLite 无 queued/running 任务。公开/内部地址配置 test/prod 均已齐全；实际安装 runtime agent 摘要仍旧，必须先安装已提交维护修复后再发新应用。
- 应用主线已前进至 e1ccafbc6，包含 158f4fed3 修复及后续已提交 MES/DCC 更新；主工作区既有 verification.md 修改不进入发布包。
- GREEN: experience-preflight -> PASS（创建本次专用维护执行 worktree）。维护目标 ea06ce8983d2330f9fab478551209582c11582fe；只核已提交文件，工作路径 C:/SpugHandoff/release/intruoyi-fenbeitong-release-20261125；源码构建 worktree 由正式 build-release 入口另行新建。纯构建不启动本地主程序、不登记业务端口。
- GREEN: configuration-regression -> PASS。独立维护 worktree 的 24 项分贝通/打印/网络配置测试通过。
- GREEN: experience-preflight -> PASS（两服真实登录基线）。账号从受保护 loginCredentials.json 进程内读取；Playwright 真实填写登录，预声明拦截认证所需路径以外的写请求，记录全部观察。本阶段只登录，不进行业务写入。
- 执行器安装计划：复用已审阅的正式原子安装程序，仅更新已提交 intruoyi_runtime_agent.py；先核旧字节对应 87faa54 父版本，备份源码/配置/SQLite，原子替换与 ACL 探针通过且仍空闲才停止旧 PID；保持配置和历史字节、非目标源码摘要不变，恢复原稳定入口。
- GREEN: experience-preflight -> PASS（本机执行器配套安装）。24 项回归已通过；安装程序内置停机前同卷原子替换/ACL/备份读回探针与空闲复查，任何失败都不进入停机。只更新一项运行脚本，不改私密配置与业务包。
- 冻结应用目标 e1ccafbc6638e64f544e609f9072096f529e45b2，维护目标 ea06ce8983d2330f9fab478551209582c11582fe。prepare.py 初次仅因路径分隔符断言失败，未安装/发布；改用 Path.resolve 比较后准备成功。旧 D:/ProjectPackage/AGENTS.md 在本机不存在；当前确认的 IntRuoyiE2E Playwright 实际为 1.63.0、Edge 实际浏览器，沿用现有已配置页面探针并记录实际版本，不冒报为历史 1.60.0。
- GREEN: executor-install -> PASS。原子/ACL/备份读回通过；PID 21804 -> 29472，仍在稳定 source 目录；仅替换运行 agent，477 个非目标文件、私密配置全部字节和 463 项任务历史 payload 保持。安装实际提交字节 SHA256 9ab3ff40bc838a7c711308a6f762ff2528d5ccd86da1ea6e5164a5f417333f83。
- GREEN: login-baseline -> real-login PASS（test/prod）；各 3 项观察留在私密报告，尚不将其记为完整页面验收。
- GREEN: experience-preflight -> PASS（build-release）。固定 e1ccafbc6638e64f544e609f9072096f529e45b2，正式入口自动新建干净 detached 构建 worktree，先核已提交源码/SQL全登记、迁移与数据库合同、GxP配置和容量；仅构建不部署、不实时访问审查服。正式外部恢复策略继承已登记的 direct-three-server-v1，具体目标预检仍必须通过。
- BLOCKER: build-release JOB-b2f69a51ce / 2026-11-25-23-53-05 -> FAILED，migration-policy-and-history：SQL catalog mismatch; unregistered: 20261125_registration_certificate_config_menu_parent.sql。未部署两服；不跳过登记或修改旧迁移。原失败目录保留。
- BDD: 新增前向菜单迁移进入正式发布 -> Given 已提交 20261125_registration_certificate_config_menu_parent.sql，When 实际全量 SQL 收集器构造本包迁移输入，Then 该 SQL 有明确归宿、目标预检与验证合同且收集成功；移除其登记应准确失败。
- 修复范围只补正式登记及必要合同；先在固定失败源码上运行真实收集器记录 RED，再最小实现、GREEN 与回归，不修改菜单业务范围或服务器数据。
- RED: python -X utf8 scripts/preflight/test_release_source_registration.py（失败构建 worktree）-> FAIL，2 项中 1 失败，精确缺少 20261125_registration_certificate_config_menu_parent.sql。另核其 type=menu，缺同名 target-preflight；只补登记仍不能发布，须同时补只读前置合同。
- GREEN: experience-preflight -> PASS（独立源码修复 worktree）。新路径 C:/SpugHandoff/release/registration-config-release-fix-20261126，分支 codex/registration-config-release-fix-20261126，基于已固定 e1ccafbc6638e64f544e609f9072096f529e45b2。旧失败目录只读保留；修改前核真实 system_menu/system_tenant_package 字段，新增预检只镜像现有不可变迁移的全部准入断言，不改变原 SQL。
- 创建首次因 Windows 长路径 checkout 失败，Git 自动注销并移除该失败目录；确认注册清单后，在同一批准路径以 core.longpaths=true、core.autocrlf=false 重新创建成功，无来源业务改动。源码修复登记 slot9/8090/48090；未启动服务。
- RED: verify-plan.py -> FAIL，真实 migration_inputs 收集器准确拒绝同一个未登记 SQL。
- GREEN: SQL-source-registration -> PASS（2 项）；menu-migration 全量633项检查 exit0；branch-runtime-port-guard PASS。
- GREEN: verify-plan.py -> PASS，919 迁移、1244 资产，新迁移的只读 targetPreflight 实际绑定，test/prod 的原真实账本计划均能构造。
- GREEN: real-target-readonly-preflight -> PASS（test/prod）；DESCRIBE 核对三张真实表后执行，不写数据库。wrong-permission 反向查询 -> 正确 BLOCKED:CONFIG_IDENTITY，未更改真实菜单或权限。
- GREEN: experience-preflight -> PASS（实现提交与主线融合）。仅提交 release-sources.json 与新 target-preflight 两文件；原 SQL 字节不改。主线必须仍为 e1ccafbc6 才 fast-forward，既有 verification.md 修改逐字节保持，融合后比对提交文件并执行相关 guard；若漂移则停止，不覆盖。
- GREEN: source-integration -> PASS。实现 6a099294a0b045f59b4f3896e06c20f1486a35e3 已合入 int_main；仅两项文件、无关修改保持，主线 branch-runtime-port-guard PASS。构建目标重新固定为此提交。
- GREEN: experience-preflight -> PASS（build-release r2）。原未登记/缺预检问题已解决，保留 JOB-b2f69a51ce 失败原件；正式入口新建新 tag 对应 worktree，不复用旧发布目录，不接入未提交内容；仍仅测试/正式范围。
- GREEN: build-release JOB-96771f31e9 / 2026-11-26-00-12-02 -> SUCCEEDED。后端 Maven clean package、前端 Vite prod build、镜像内 release-info 与打包后端合同、原始包封存/NAS 归档均通过。build worktree 自动清理验证25300文件、3128生成链接，registeredAfter=false/physicalPathExists=false，无新提交，无需融合。
- 只读目标预检：check-prerequisites JOB-673d2e3c98，operation=publish-test，同一 tag；尚未替换服务器容器。
- GREEN: test-prerequisites JOB-673d2e3c98 -> SUCCEEDED，真实测试起点、健康/维护、空间/恢复资源及目标迁移计划通过。
- GREEN: experience-preflight -> PASS（publish-test）。同一不可变包 2026-11-26-00-12-02，明确目标58；正式入口持锁重核起点、停写与恢复点后执行迁移和双容器替换，任何失败保留原 operation。页面验收预声明为真实登录、排产菜单读取、分贝通状态/票据/本服认证 iframe、版本及变更说明；禁止业务写入，认证外自动写请求拦截并逐项记录，未知错误阻断晋级。
- 测试服原 operation OP-330d447de29fee777503 已完成候选容器切换，技术版本、剩余迁移0、健康UP、HTTP200及真实登录检查 passed；继续等待发布任务终态。
- GREEN: experience-preflight -> PASS（测试服真实页面验收）。Playwright 1.63.0 / 实际 Edge，固定候选 tag/commit，使用受保护配置的芋道源码/admin；按已声明范围验证排产真实数据、分贝通真实票据和本服 iframe、可见版本及变更说明，全部观察留档并逐项判断后才能晋级。
- GREEN: publish-test JOB-7143335ebc -> SUCCEEDED；独立运行态核验 PASS：远端 operation succeeded、manifest、IMAGE_TAG、镜像ID、UP/HTTP200、实际JVM内分贝通内外地址和前端版本均与候选一致。真实排产菜单/列表响应及可见版本说明通过，返回实际空列表，未创建测试业务数据。
- BLOCKER: test-business-page -> 分贝通真实认证 iframe 的 /auth/callback 返回503，未通过必需页面路径；暂停 mark-tested/正式晋级。原始8项观察与失败截图保留，不忽略该业务错误；进一步只读检查助手与ERP认证连接。页面探针错误输出已去掉URL查询参数，避免票据进入公开诊断。
- 根因证据：助手原镜像/环境未变，共享网络DNS正确、容器内后端health=UP；同一页面观察窗口的后端堆栈准确定位 AuthController.validateFenbeitongAssistantTicket:386，读取金蝶配置时 TenantContextHolder 不存在租户编号。现有票据只含用户/权限/期限；打印助手已采用可信票据租户上下文模式，可直接沿用。
- BDD: 分贝通票据按签发租户验证 -> Given 租户169的用户通过真实ERP入口获得票据，When 无租户头或其它租户上下文的助手回调校验该票据，Then 只在169读取金蝶配置、保留权限/一次性票据合同并恢复来访上下文；无租户、负租户票据拒绝，不读取配置；配置失败也恢复上下文。
- GREEN: experience-preflight -> PASS（第二项正式源码修复 worktree）。固定6a099294a0b045f59b4f3896e06c20f1486a35e3，新路径 C:/SpugHandoff/release/fenbeitong-ticket-tenant-20261126，分支codex/fenbeitong-ticket-tenant-20261126；仅后端票据和测试，不发布助手，不改业务/租户配置，不启动本地服务；实现前先复现上下文缺失失败。
- RED: Maven -q -pl yudao-module-system -am -Dtest=AuthControllerTest -Dsurefire.failIfNoSpecifiedTests=false test -> exit1，44项中4失败3错误；缺租户上下文复现与线上相同NullPointer，错误来访租户0/999未被切换，非法票据仍读取配置，签发payload无tenantId。原始Surefire XML保留于私密证据。首条准备命令因相对cwd错误未执行已中止，不计为RED；以绝对路径准备后的本次结果为准。
- GREEN: tenant-context-regression -> PASS，Maven AuthControllerTest=44、FenbeitongAssistantServiceImplTest=8、InvoiceVoucherPrintAssistantServiceImplTest=15，共67项，失败/错误/跳过均0。实现只改可信payload租户与配置读取上下文，不改助手或数据库。Maven控制台RED中文异常曾因JVM缺UTF8属性显示乱码，原XML保留；GREEN命令显式file.encoding/sun.jnu.encoding=UTF-8。
- GREEN: experience-preflight -> PASS（租户修复提交/融合）。核67项真实JUnit，精确三文件提交，不包含主线新增无关文档/JFR；只允许6a099294a为当前主线才fast-forward，保留全部既有状态和未提交diff，融合后核文件字节及端口guard。
- GREEN: tenant-source-integration -> PASS。实现eb866bbaf4ea1b1c6db93daa63e77576766c3684，三文件已合入int_main；主线既有状态/diff保持，三文件与已通过67项回归的修复提交一致，融合后的int_main端口guard PASS。新自有worktree登记slot10/8091/48091，未启动服务。
- GREEN: experience-preflight -> PASS（build-release r3）。固定eb866bbaf4ea1b1c6db93daa63e77576766c3684，新建新tag专用构建worktree；旧包2026-11-26-00-12-02页面BLOCKED保留，不mark-tested或晋级。新包必须重新完成测试部署和全部页面门禁，不拼接旧包证据。
- 新构建 JOB-1486fa339e / 2026-11-26-01-52-12，worktree C:/SpugHandoff/release/build/2026-11-26-01-52-12；后端编译及前端依赖安装通过，正在前端编译。
- 新包前端编译02:39:55完成（正式2700秒超时内，未调高时限），前后端镜像和封包后端合同、镜像内版本核验通过，正在NAS原始包归档。PowerShell进度查询延迟期间使用Node只读SQLite核原任务，未重复投递、修改任务状态或停止其它进程。
- GREEN: build-release JOB-1486fa339e / 2026-11-26-01-52-12 -> SUCCEEDED。原始包/NAS封存完成，构建worktree核25300文件/3128生成链接并删除，registeredAfter=false、physicalPathExists=false、无新提交。最终源码eb866bbaf4ea1b1c6db93daa63e77576766c3684。
- 新包测试只读预检：必须以当前测试服2026-11-26-00-12-02为真实起点，保持旧包页面BLOCKED事实，同一新tag重新执行全部测试门禁。
- GREEN: test-prerequisites JOB-441ead6542 -> SUCCEEDED，新包2026-11-26-01-52-12的真实目标起点、迁移计划、空间和恢复资源检查通过。
- GREEN: experience-preflight -> PASS（publish-test r3）。测试服58，固定同一新包/eb866bba提交，旧包证据已归档；正式入口重新持锁创建本轮恢复点后切换，无额外业务配置或助手发布。部署成功后重新进行真实页面全范围验收，未知错误继续阻断正式。
- 独立已知配置事项：测试服日志还出现租户169注册证提醒配置缺失；正式服尚未升级、仍为2026-11-25-10-22-04时，只读核到租户163已有相同类型提醒失败（前一小时日志480处匹配）。这是既有负责人/期限配置缺口，非分贝通认证异常，本次不写业务配置；最终报告保留未修状态，不将页面冒烟冒充提醒任务或完整业务验收。
- publish-test r3 过程观察：同一原任务 JOB-ea115d06b9、远端 OP-a0ba82e7c8e1222f67c0 持续running，SQL快照7196018108字节后进入数据卷归档，已观察recovery-volume-0.tar及增长中的recovery-volume-1.tar。旧容器按正式流程停止、restartCount=0；进程I/O持续增加。未重复投递、改写状态或把停止态误判为崩溃。
- 新包测试远端 OP-a0ba82e7c8e1222f67c0 已于19:29:34Z succeeded，实际双容器均为候选镜像，backend healthy、双容器running、restartCount=0；本机任务继续技术版本/登录验收，尚不提前声明完整成功。
- GREEN: experience-preflight -> PASS（r3测试服真实页面验收）。固定2026-11-26-01-52-12/eb866bbaf4ea1b1c6db93daa63e77576766c3684；使用既定真实前端路径和芋道源码/admin，只允许登录和分贝通票据认证所需请求，其它写请求拦截并全部记录。重新验证排产、分贝通本服认证iframe、可见版本和变更说明；每条观察显式归因，未知错误阻断正式晋级。
- GREEN: publish-test JOB-ea115d06b9 -> SUCCEEDED，technicalVerification passed；独立实际运行态、唯一manifest、IMAGE_TAG、双镜像ID、实际JVM内外助手地址、UP/HTTP200、非维护及三阶段数据库合同PASS。
- 测试页面认证回调503已消失，真实票据成功进入助手；新增配置GET 400暂阻晋级并做只读诊断。实际响应REQUEST_FAILED/configuration is missing，未改动的助手routes.js:121-125读取本地字段映射无记录时明确返回此错误；app.js:507-520显示未保存映射状态。真实前端打开字段对应关系面板验证NOT_CONFIGURED；未保存、同步或记账。该配置缺口保留为财务使用前置问题，不将ERP入口验收称为完整助手业务通过。
- 配置诊断探针首轮关闭按钮误用“关闭”文本定位超时，属于探针定位错误，失败JSON独立保留；按实际源码#closeFieldMappingButton修正后重新真实登录及全部检查通过，未隐藏HTTP400或重写旧结果。
- GREEN: test-page-acceptance -> PASS_WITH_OBSERVATIONS。排产6项、分贝通8项观察逐条审阅；统计网络关闭、装饰头像ORB、预声明只读拦截工作台POST、助手未保存字段映射均有具体归因和影响范围。当前原始证据SHA绑定见test-observation-review.json及test-page-acceptance.json；必需认证/排产/版本路径全部PASS，财务写入和工作台初始化未验证。
- GREEN: experience-preflight -> PASS（mark-tested及正式目标只读预检）。测试运行态与真实页面证据仅使用最终同一tag/eb866提交；保留全部观察及业务范围限制，正式起点必须重新核验。用户本轮明确授权测试服和正式服发布，不扩大审查服或助手发布。
- GREEN: mark-tested JOB-b458ccb56f -> SUCCEEDED，重新技术验证passed；正式目标预检 JOB-34739b13c4 -> SUCCEEDED，NAS能力探针、空间/资源、真实起点和目标迁移计划通过。
- GREEN: experience-preflight -> PASS（promote-prod）。用户明确授权正式服发布，固定2026-11-26-01-52-12与eb866bbaf4ea1b1c6db93daa63e77576766c3684，不重构建、不换包；沿已登记direct-three-server-v1及正式external恢复责任确认执行，不冒称新全备已验证。正式目标57，原始起点/manifest/迁移/恢复依据门禁已通过，正式入口持锁重核后切换；先保持维护并走登记验收入口，真实页面通过才accept-prod开放。公司/mnt/nas和其它任务资源保持。
- 正式远端 OP-968efedbe5fbf6f10546 -> succeeded（19:53:17Z），本机JOB-9bf24c43bb继续技术验收。此阶段正常前端停止属于维护流程，不能冒报正常入口已开放；登记专用验收入口http://172.30.30.57:38084。
- GREEN: experience-preflight -> PASS（正式维护入口真实页面验收）。真实Playwright登录芋道源码/admin，仅使用已登记57:38084，不猜测其它入口；按测试服相同范围读取排产、分贝通本服票据和认证iframe、可见版本及变更说明。只读保护与全部观察保留，未知问题不accept-prod；助手字段映射状态必须按正式真实结果归因，不能照抄测试服结论。
- BDD: 分贝通验收按可观察完成条件判断 -> Given 真实登录、票据/助手iframe、请求已结束且版本控件可见，When 完成版本及变更说明读取，Then 依据真实响应、可见页面和全部错误进行验收，不重复等待与实际请求状态不符的整页networkidle事件。
- RED: 正式维护入口真实分贝通探针两次失败于第二次page.waitForLoadState(networkidle)，原失败均保留；真实认证和iframe已PASS。第二次增加context request lifecycle只读诊断，超时结束inFlight=[]，最后已完成请求为/api/.../process（19:58:01Z），45秒等待期间没有新请求；不存在所谓持续未结束业务请求。排产探针及正式技术登录已PASS。修复只针对验收脚本的冗余全页事件等待，保留iframe自己的加载检查、全部响应/error观察，并强制当前跟踪请求结束、可见版本及说明实际读取，不改产品或扩大范围。
- GREEN: page-readiness-probe -> PASS；同一新探针重新真实登录测试服和正式维护入口，两处观察到pendingRequests=0、真实认证iframe、可见版本和变更说明全部通过。旧test验收及原始JSON按at-mark-tested独立封存，新窗口重新逐条审阅并绑定SHA，未改写mark-tested时的证据。
- GREEN: promote-prod JOB-9bf24c43bb -> SUCCEEDED，technicalVerification passed；正式维护入口排产和分贝通验收PASS_WITH_OBSERVATIONS（14项），正式也实际GET config400且真实映射面板显示NOT_CONFIGURED；两服实际助手routes.js/api.js/app.js逐字节一致，未改动助手或财务配置。必需ERP页面路径全部PASS，财务生成/记账/同步仍未验证。
- GREEN: experience-preflight -> PASS（accept-prod）。固定同一tag及包摘要，正式维护入口真实页面已完成并逐项审阅，accept-prod仅执行本轮既有开放流程：正常后端/前端、IMAGE_TAG和备份来源绑定同步、验收资源收口。随后必须重新从普通8081入口登录验证，独立核全部运行态及三阶段数据库合同；不把维护入口成功当作普通入口已成功。
- GREEN: accept-prod JOB-65c04bddbe -> SUCCEEDED，technicalVerification passed，正常双容器已运行。
- GREEN: experience-preflight -> PASS（正式普通入口及两服最终运行态核验）。从57:8081重新真实登录走排产和分贝通路径，沿既定只读保护留全部观察；不复用维护入口结果冒充普通入口。独立读取同包manifest、远端IMAGE_TAG、实际双镜像、UP/HTTP200、实际JVM地址和全部三阶段数据库合同，确认维护及来源绑定pending已消费；测试服同时复核最终状态，防止并发漂移。
- GREEN: final-runtime -> PASS（test/prod），同一包SHA/manifestSHA、双镜像ID完全相同，实际IMAGE_TAG匹配，实际JVM内外助手地址正确，后端UP、前端200、maintenance=false、runtimeOpeningPending=false、backupSourceBindingPending=false，三阶段数据库合同均PASS。
- GREEN: prod-normal-page-acceptance -> PASS_WITH_OBSERVATIONS，真实普通8081入口排产、分贝通认证和可见版本说明均通过。三个入口每条错误观察均已审阅；末尾刚发起的/workbench/sources GET在报告中单独保留为out-of-scope-unverified，源码registry.ts已核实归属工作台初始化，不捏造成功响应。已验证路径与未验证业务范围明确分开。
- GREEN: final-report.py -> PASS，最终同包五阶段任务全部succeeded，两服所核5菜单行一致，5580/991503直接角色关联保持，正式必要祖先关联各补1；菜单待办据当前事实关闭，不重建其它机器历史变更时点。
- 任务状态 ready_for_closeout。GREEN: experience-preflight -> PASS（本任务自有worktree清理）。源码两项实现已提交、融合并验证；最终两服独立运行态及真实页面报告已PASS。仅清理本任务4个剩余工作区，成功构建的2个目录已自动删除；逐项以目标提交、已融合分支、完整归属/链接/消费者保护和持久清理证明调用正式cleanup_build_worktree，不删除其它任务或/mnt/nas，不停止其它控制台。删除后释放本任务slot9/10并核实际稳定执行器PID/argv/cwd、配置摘要及Git/物理目录均无残留。

- GREEN: source-fix-cleanup -> PASS，25300项受控文件校验、Git remove exit0，物理路径和Git登记无残留；原实现6a099294a已融合int_main。
- GREEN: release-slot.ps1 -> PASS，仅释放本任务已删除SQL修复worktree的slot9/8090/48090，端口无监听，其它登记保持；租户与维护工作区继续使用原清理流程。

- GREEN: final-records-readonly-precheck -> PASS，当前任务归档文件按UTF-8解码，私钥标记与真实受保护配置凭据扫描通过；未暂存共享日志或其它任务改动。最终提交前仍由commit-records.py核完成状态、收尾证明和暂存范围。

- GREEN: tenant-fix-cleanup -> PASS，25300项受控文件校验、Git remove exit0，物理路径和Git登记无残留；实现eb866bbaf已融合int_main。
- GREEN: release-tenant-slot.ps1 -> PASS，仅释放本任务已删除租户修复worktree的slot10/8091/48091，端口无监听，其它登记保持；继续等待最后维护工作区清理完成。

- BLOCKER: maintenance-cleanup -> 正式清理器拒绝ops/release/__pycache__/release_readonly_sql.cpython-312.pyc（不在其build脚本缓存白名单）；目录保留，未扩大删除规则。failed-build/source-fix/tenant-fix均已passed，slot9/10已释放。影响仅为本地收尾，远端发布验收不回写失败；先核本任务维护测试生成物来源与原源码/pyc字节，再只删除可证明的派生缓存，不接触未知文件。原清理进程exit1，后续PID读取NoSuchProcess属于其正常退出后的诊断结果。

- GREEN: experience-preflight -> PASS（维护生成缓存精确清理及正式收尾）。仅2个ignored pyc，头部magic/时间/大小、tracked源码和完整marshal编译结果逐字节相同；无额外尾随数据、无链接、无消费者，detached/目标提交/Git洁净核验通过。缓存原字节另存私密证据后精确unlink，再调用原正式清理器；不扩大其白名单或跳过任何归属校验。

- GREEN: maintenance-generated-cache-proof -> 2项ignored缓存与已提交源码重编译marshal结果逐字节相同，无尾随数据/链接；原字节私密保留后精确删除。finish-maintenance-cleanup.py --apply调用原清理器PASS，5348个受控文件已核，Git remove exit0、Git/物理目录均无残留。未修改正式清理模块或扩大白名单。
- GREEN: final-local-proof.py -> PASS，六个本任务worktree均已删除、slot9/10 inactive、最终提交已在int_main；稳定执行器PID29472的入口/argv/cwd、已安装agent和私密配置摘要符合既定值。
- 经验前移：维护Python命令使用-B、清理前核全部ignored，精确缓存来源检查及未知保护已写docs/worktree-memory.md，索引和发布checklist同步。三个经验文件事前均Git洁净，最终提交仅包含本任务新增门禁。

- GREEN: owned-worktree-cleanup -> PASS（cleanup.py前三项；finish-maintenance-cleanup.py证明两个ignored pyc精确派生后调用原清理器完成maintenance）。原始缓存保护失败保留，未扩大白名单；四项正式清理证明均为passed，Git登记及物理路径无残留；两项实现先提交、融合和验证，另外两次成功构建目录先前自动清理。
- GREEN: release-slot.ps1 / release-tenant-slot.ps1 -> PASS，仅释放本任务slot9/10，端口无监听，其它注册保持。
- GREEN: final-local-proof.py -> PASS，六个自有worktree均无残留，最终源码在int_main；稳定执行器PID 29472的argv/cwd和受保护配置、已安装agent摘要核验通过。
- completed: 2026-11-26T05:00:36+08:00；同包两服运行态和真实页面验收、任务自有资源清理全部完成。最终任务记录单独提交，不暂存共享request-command-log的其它并发修改。
