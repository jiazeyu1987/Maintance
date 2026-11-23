# 执行记录

- GREEN: closeout -> PASS。五个列明自有临时路径再次确认不存在；正式cleanup回执均通过，维护新提交已合回int_main并验证，应用发布worktree未产生新提交。执行器PID14268确认稳定source路径，未停止其它任务进程。状态由ready_for_closeout转completed，最终记录单独提交；仅暂存本任务文件和共享请求日志本任务段，不提交历史脏改动或私密证据。

- GREEN: 第五轮最终运行态、真实登录、排产工单、版本变更说明、打印status/新票据/认证后iframe全部PASS。两个页面脚本各6条已归因非阻断观察，按统一规则PASS_WITH_OBSERVATIONS；本轮无callback403，关闭已复现根因阻断。最终范围不含完整打印/导入写入或线上跨租户安全矩阵。状态转ready_for_closeout。

- GREEN: publish-test JOB-2b57a4ae44 -> succeeded，technical-login通过，同包2026-11-23-22-02-22。恢复点数据库7182425153字节，数据卷28979200/9676124160字节，远端部署OP-113e9adb5fc1b089895a。
- GREEN: experience-preflight -> PASS（第五轮最终真实只读页面验收）。重新登录并从现有菜单/菜单搜索进入，取得新票据；不重放旧票据，不做业务写入；仅认证票据在非GET白名单，工作台主动拦截保留观察。独立校验本轮manifest/.env/images/health/version，异常按既定规则逐项判定。

- GREEN: build-release JOB-f8f6510f3c -> succeeded（2026-11-23-22-02-22 / 275c87011），清理verifiedTrackedFiles=25191、generatedLinksDetached=3128、gitRemovalExitCode=0、无新提交、Git登记和物理目录均不存在。GREEN: check-prerequisites JOB-bf46cd3d69 -> succeeded，仅test。
- GREEN: experience-preflight -> PASS（第五轮publish-test）。同包构建、封存、目标起点和迁移路径已通过；队列空，用户已确认无并发发布。本次正式恢复点后替换测试容器，维持运行期打印配置和内部host。命令action publish-test publish-r5.json，只派发一次；随后独立核运行态并以新登录/新票据复测，禁止晋级正式服及备用服。

- 第五轮JOB-f8f6510f3c / 2026-11-23-22-02-22，目标275c870118f8096328d94bd38700455de3e76fc0，专用worktree C:/SpugHandoff/release/build/2026-11-23-22-02-22。构建命令正式build-release；验证命令正式check-prerequisites/publish-test及menu-page-check.cjs/print-page-check.cjs。该工作区不作源码修改，是否新提交与最终删除须核正式回执。

- 应用验票根因修复275c870118f8096328d94bd38700455de3e76fc0已推送；本机fetch确认HEAD=origin/int_main，tracked工作区干净。应用报告后端62项/前端10项PASS，修复仅可信票据租户绑定、上下文恢复和原子消费，无新增迁移/助手变更。此前线上403仍保留，须新包真实复测关闭。
- GREEN: experience-preflight -> PASS（第五轮仅test构建）。执行器无活动任务，上轮正式publish-test成功；新目标275c87011以全新releaseTag专用临时worktree构建，不混入未跟踪文件，不复用旧包/旧worktree。命令test-release-20261123-tools.py action build-release build-r5.json；构建和清理命令由正式执行器记录。新包须完整manifest/迁移/运行态/页面验收，禁止mark-tested/promote-prod/promote-backup。

- BLOCKER: 最终打印真实页面 -> status与ticket成功，iframe /auth/callback HTTP403，正文“系统异常”。后端真实日志定位TenantContextHolder缺租户编号：TenantConfigService.scope -> ErpKingdeeConfigServiceImpl -> AuthController.validateInvoiceVoucherPrintTicket。已交IntRuoyi修复；验票目标确认为当前backend，公开/内部地址均正确。原始日志/票据仅私密留存，不提交。
- GREEN: 独立运行态final-runtime-verification.json PASS；releaseTag 2026-11-23-20-22-13，d9022d50a，JOB-fd39bacc82，manifest/.env/images/UP/200/开放状态一致。菜单页面真实登录、排产工单数据接口code0（真实空列表）、版本及变更说明PASS。
- 页面观察：菜单6项=外部统计资源连接关闭及console 2项、头像ORB 1项、事前只读工作台POST拦截及对应请求/console 3项；不影响已验排产与版本路径，工作台功能未验。打印另2项为callback403及console，属于必需路径阻断。脚本先错误定位侧栏ERP及搜索placeholder，保留失败；最终以现有菜单搜索真实进入，无强制点击、直跳路由或产品改动。
- 收尾复核：maint-print-config-20261123、preflight-20261123-bd01f08、build/2026-11-23-20-04-45、build/2026-11-23-20-22-13物理目录均不存在，正式清理回执及Git登记核对PASS；维护新提交已融合验证，应用发布worktree无新提交。稳定执行器PID14268仍在稳定source路径。因应用验收阻断，当前不得标记completed或提交成功收口记录。

- GREEN: publish-test JOB-fd39bacc82 -> succeeded，technical-login通过；同包2026-11-23-20-22-13。恢复点包含数据库快照7182134349字节及数据卷28549120/9676093440字节；未对正式服发布。三个自有额外worktree清理均passed、Git登记与物理目录均不存在。
- GREEN: experience-preflight -> PASS（最终真实只读页面与运行态验收）。按此前声明的页面/认证票据白名单执行；不写租户业务数据，不创建/上传/打印，不切换权限。独立核manifest/.env/实际双镜像/UP/200/无维护/版本说明；异常保留且逐项归因。命令menu-page-check.cjs与print-page-check.cjs，固定tag与d9022d50a。

- 维护清理第一次被自身PowerShell参数消费者门禁拒绝，使用外置固定参数包装器调用原清理函数后发现3个ops路径pyc不在发布构建缓存白名单。未扩大工具白名单；逐一核tracked源、Python magic/header、co_filename及code对象与原源编译完全一致，私密外置封存原字节/SHA后仅移除已证明的3个派生缓存，再运行完整原清理门禁。未知文件不删除。

- GREEN: experience-preflight -> PASS（已验证自有worktree收尾）。维护工作区075c841已融合int_main且同结果101项PASS；旧预检bd01与失败构建d140的迁移阻断已被d902真实构建/目标预检解决，三工作区均无未提交改动。仅清理本任务maint-print-config-20261123、preflight-20261123-bd01f08、build/2026-11-23-20-04-45，使用正式ownership/consumer/逐文件校验工具与外置proof，不清其它任务worktree。远端发布沿JOB-fd39bacc82独立继续。

- GREEN: check-prerequisites JOB-0836154dfc -> succeeded，仅test、同tag2026-11-23-20-22-13。GREEN: experience-preflight -> PASS（publish-test）。已封存原包续办通过、登记实际基线与迁移计划通过，实际minute_tick只读预检PASS。按正式发布建立恢复依据后替换测试双容器，运行期公开地址来自已安装配置，内部地址保留。只派发一次publish-r4.json，不执行mark-tested/promote-prod/promote-backup。

- GREEN: 原包续办JOB-29a5c45b86 -> succeeded，releaseTag=2026-11-23-20-22-13；完整封包重验、工作区清理确认及NAS封存通过。原构建超时失败保留并以retry记录关联，不追改原状态。进入同包仅test目标预检JOB-0836154dfc。

- 构建JOB-ce67f865b9已完成编译/双镜像/合同校验并封存本地release.tar=742062080字节，但cleanup git worktree remove超180秒失败，NAS未完成。原buildWorktreeCleanup保存ownershipVerified与固定commit。只读复核：该tag工作区已不在git登记、.git不存在、无自有node/java消费者；不能将失败直接写成功。
- GREEN: experience-preflight -> PASS（原包续办）。使用正式resolve-task/retry，绑定JOB-ce67f865b9与2026-11-23-20-22-13，先核完整封包每成员SHA与原固定commit，再按原ownership proof处理残留和NAS封存；不重新编译、不改包、不重新部署、不删除其它worktree。当前用户继续核查发布授权覆盖本次必要收尾。

- 本轮构建JOB-ce67f865b9 / 2026-11-23-20-22-13，worktree=C:/SpugHandoff/release/build/2026-11-23-20-22-13，目标d9022d50a7bec74dec707ce40aa5efb12b53b495；migration-policy-and-history通过，进入compile-backend。无源码修改或新提交，最终按执行器清理回执验证。
- 真实页面计划：同包技术登录、智能排产/排产工单只读页面与实际数据、版本说明；打印页面通过现有菜单、status公开URL、真实票据和已认证iframe验证。使用芋道源码admin仅最终只读，不启动/关闭助手，不上传或生成打印作业；允许认证票据请求，其他非读取拦截并逐项归因。不把此范围宣称完整打印业务或ERP全量回归。脚本menu-page-check.cjs/print-page-check.cjs均语法通过。

- 应用分钟迁移预检修复f0806c282及验证记录d9022d50a已推送，重新fetch核HEAD=origin/int_main=d9022d50a7bec74dec707ce40aa5efb12b53b495。原SQL未改，912迁移输入、三环境登记台账合同及负向缺预检拦截通过（应用证据）；实际助手3文件SHA绑定部署镜像，桥接契约2项通过。
- GREEN: experience-preflight -> PASS（build第4轮）。仅使用新固定提交；队列空、正式test登记JOB-5253b19346成功，历史失败未篡改。新tag专用worktree自动创建；不部署原失败包，目标只读预检仍须正式publish-test前执行。命令test-release-20261123-tools.py action build-release build-r4.json。

- 历史登记门禁安装前发现模块版本混合：installed target_registration.py精确匹配已提交5dc247b，包含现executor未引用的旧registration_failure_blocks；executor本体匹配075c841父版。源码全目录只发现定义无调用。按已验证两个原SHA封存后整体安装075c841两个模块；未强行忽略未知漂移，不改变私密配置或历史payload。GREEN: experience-preflight -> PASS（第二次稳定执行器安装，构建已失败终止、队列空）。

- BLOCKER: build-release JOB-3684c6abbf / 2026-11-23-20-04-45 / d14032e99 -> migration-policy-and-history失败：test: required target preflight missing (1): 20261123_dcc_registration_certificate_reminder_minute_tick。新迁移合同交应用线程修复，未部署。
- RED: test_registration_history -> 原实际submit拒绝已有更晚完整证明的登录失败。GREEN/REGRESSION：101项PASS；真实历史只读函数核三条均绑定JOB-05b93f6100。维护075c841提交并融合int_main，相同结果独立worktree再次101项PASS。只作登记历史覆盖证明，不改原失败。

- 新构建已派发JOB-3684c6abbf，固定d14032e99；登记未执行：API明确409 Failed remote effects require reconciliation before registration。只读核到3条旧test发布均停在technical-login，版本/迁移已通过；其中1条已有同包技术复核，另2条后续已有新版本成功发布。当前实现登记门禁不区分历史登录失败与未完成迁移。禁止手改SQLite/伪造原成功。
- BDD: 历史登录失败不永久阻断基线接管 -> Given 原test发布的部署/版本/迁移有成功证据且仅登录失败，后续同test更晚成功发布具有同包身份绑定的完整技术证明；When 显式登记test；Then 保留原失败，仅记录更晚发布证明作为历史覆盖依据。缺证明、迁移失败、跨环境/跨包/早于原任务或仍维护则拒绝。此为正式登记门禁一致性修复，不恢复旧版本，不授予旧包验收。

- GREEN: 维护915ffca已提交并fast-forward合入int_main；相同融合结果在独立worktree回归94项PASS。稳定执行器安装同提交runtime_agent，475个其它文件保持、426条job/状态payload保持；仅新增targets.test.invoiceVoucherPrintAssistantUrl，配置ACL保留，控制台仍在稳定路径。
- GREEN: experience-preflight -> PASS（仅test基线登记及新构建）。用户明确无并发发布；前次只读核镜像/清单/台账/恢复边界，现无活动任务，新登记只描述真实当前状态，不追认未知更新历史、不修改旧包/失败记录。应用最新origin/int_main=d14032e9919d5e08af5184eac732e066e4e31f22，本机一致，仅既有jfr未跟踪不入包。新build由正式执行器创建新tag专用worktree，原18:31旧包保留但不部署。

- RED: test_invoice_print_runtime_config 实际 replace 调用 -> FAIL，缺少 public-url JVM 属性；GREEN: 最小配置注入后5项PASS；REGRESSION: runtime/fenbeitong/network/reopen相关94项PASS。额外确认内部assistant-host保持用例PASS。
- 真实只读配置核查：原JAVA_OPTS已有assistant-host=erp-invoice-voucher-print-assistant；原前缀环境变量检查不完整，本次纠正。backend共享网络请求助手根路径403且文案符合健康探针，PASS。宿主公开IP从内部网络不可达，不据此改内部host。仅注入显式public-url。
- GREEN: experience-preflight -> PASS（维护提交融合及安装准备）。变更限runtime agent、对应测试与配置说明；94项回归通过，主工作区已有其他脏文件保持。只修改稳定执行器本模块及私密targets.test公开URL；安装前再次核无活动任务，保留配置ACL/状态/原件与精确进程身份，不重载其他组件。

- BDD: 打印助手运行期配置随发布保持 -> Given 测试目标显式注册合法公开URL；When 正常后端替换/开放；Then 注入正确JVM属性且保留其它环境，未配置目标不被改变，非法/演练配置停服前拒绝。
- GREEN: experience-preflight -> PASS（维护修复worktree创建）。主仓a0e2f0d683983c8a246fcb89a62efbbcb8fefbed，目标 C:/SpugHandoff/release/maint-print-config-20261123，仅修改本任务发布配置代码/测试，不动历史脏文件。

- 用户续办确认：没有其他发布，请继续核查并发布。并发确认解除；继续受控基线接管和打印助手配置修复协调，不覆盖未确认配置或改旧包绕过版本门禁。

- IntRuoyi只读复核：该外部前端补丁非其本任务实施；现有打印入口仅读取构建变量，无正式运行期地址配置；release-info.configuration不是产品读取来源。不能把测试IP写入跨环境通用包或覆盖后称功能保留。继续部署依赖并发确认及正式配置方案。
- 构建工作区正式清理回执 passed：verifiedTrackedFiles=25165、generatedLinksDetached=3128、producedNewCommits=false、registeredAfter=false、physicalPathExists=false；维护独立确认路径不存在。先前失败预检worktree仍保留，任务尚未completed。

- 新阻断：publish-test 定向预检 JOB-3d8e65c605 failed，仅 target-plan=STALE_RELEASE；测试服实际前端已被外部更新到 2026-11-23-18-42-53。未执行 publish-test。
- 多机器接管只读证据：后端镜像保持 cb780db5…，前端由 c4a72f72… 改为 28aa65d4…，创建于10:52:34Z；schema/ledger摘要保持。release-info的sourceCommit仍83a856c19，change为Configure invoice voucher print assistant URL，配置地址为测试服18733。当前绑定staging及release根未找到同tag包目录。真实UP/200、无maintenance/opening pending。
- 目标修复提交 .env.prod 的 VITE_INVOICE_VOUCHER_PRINT_ASSISTANT_URL 为空，而 .env.test 为测试地址；正常同包构建 --mode prod，不可直接覆盖而忽略当前功能配置。已询问用户是否仍有并发发布，并让IntRuoyi只读核查现有正式配置方案；未改包、镜像、版本号、SQLite或基线，未重建规避版本门禁。

- GREEN: build-release JOB-09df3abe43 -> succeeded，2026-11-23-18-31-20。实际构建工作区 HEAD=4f528e1cd、干净，登记测试再次1项通过；910条迁移、完整双镜像和后端产物合同、NAS原件均由正式构建通过。继续同包 publish-test 定向预检。

- 构建 JOB-09df3abe43；releaseTag=2026-11-23-18-31-20，worktree=C:/SpugHandoff/release/build/2026-11-23-18-31-20，目标 4f528e1cdd5568d911a3f2144ddb90d6f93181df。正式执行器自动创建/验证/构建/清理；本任务跟踪最终结果。

- GREEN: 测试服 CE 目标数据只读预检 -> TARGET_PREFLIGHT_PASS:20261123_dcc_registration_certificate_ce_release_preflight。先 DESCRIBE 三张实际表核字段，再执行最终提交内原只读预检，未修改数据库。
- GREEN: experience-preflight -> PASS（build-release）。目标 origin/int_main=4f528e1cdd5568d911a3f2144ddb90d6f93181df 已重新 fetch 核实；正式迁移解析通过，目标数据通过；由稳定执行器创建本次 tag 专用干净 worktree，只消费已提交内容。原 Docker 超时复核通过，通用预检审查服失败不用于测试服放行；测试部署还须同包 test 定向预检通过。构建命令：test-release-20261123-tools.py action build-release private/update-test-release-20261123/build-r2.json。

- 应用交付：4f528e1cdd5568d911a3f2144ddb90d6f93181df；登记1项通过、正式 migration_inputs 910迁移/1227资产、Maven相关21项通过（应用线程报告，维护继续独立核验发布范围）。原三条SQL不变，新增schema检查与停服前只读检查。

- 用户追加授权：通知 IntRuoyi 修复，然后继续发布。已向应用线程“执行初始化步骤并修复问题 (2)”发送具体阻断、修复范围和提交推送要求；等待应用修复，不代改业务或重派失败构建。
- GREEN: experience-preflight -> PASS（测试服真实只读登录基线）。使用既有私密凭据，Playwright 真实登录，提前监听页面/请求异常，预设只读边界拦截非认证写入。此阶段仅验证登录，不操作业务数据，不将其当发布完成验收。脚本 private/update-test-release-20261123/menu-page-check.cjs 已 node --check 通过。

- 用户需求：更新 IntRuoyi 到最新 Git 已提交代码，然后发布测试服务器。
- 前序 owned 任务 20261121-promote-tested-prod 已 completed。
- BDD: 最新提交测试发布 -> Given 已验证 Git 目标和测试环境；When 从新专用 worktree 构建并发布；Then 同包运行态、真实登录页面和版本说明通过，正式服不变。
- 当前阶段：只读前置核对，尚未构建或远端写入。
- Git 通过 127.0.0.1:7890 fetch origin int_main 后 fast-forward 成功；目标 bd01f08cdf8c36a443664d750842705d41cb3632。仅保留原有未跟踪 hs_err_pid51176.jfr，不进入构建输入。
- 当前测试服 2026-11-23-08-35-27，backend UP、frontend 200、maintenance=false、runtimeOpeningPending=false；开始前发布队列无活动任务。
- 当前正式执行器配置确认 repo=C:/Users/D01021/Documents/ChatGPT/IntRuoyi，buildWorktreeRoot=C:/SpugHandoff/release/build；预检 JOB-77bc13d7d9，尚未派发构建/发布。
- GREEN: experience-preflight -> PASS（仅本次专用 worktree 创建及迁移登记验证）。路径 C:/SpugHandoff/release/preflight-20261123-bd01f08，固定目标 bd01f08cdf8c36a443664d750842705d41cb3632；不得据此放行服务器写入。
- 已发现目标 Git 树内 3 个 20261123 SQL 不在 release-sources.json，继续执行隔离登记测试确认阻断。
- worktree 创建命令：git -c core.autocrlf=false -C <确认主仓> worktree add --detach C:/SpugHandoff/release/preflight-20261123-bd01f08 bd01f08cdf8c36a443664d750842705d41cb3632；退出 0。验证前 git status --porcelain 无输出。
- BLOCKER: python -X utf8 -B scripts/preflight/test_release_source_registration.py -> FAIL，1 test/1 failure，三条新 SQL 无归宿。
- BLOCKER: python -X utf8 -B C:/SpugHandoff/release/source/ops/release/release_source_catalog.py --sql-root <本次worktree>/IntRuoyiBackend/sql/mysql -> exit 1，SQL catalog mismatch; unregistered 三条同名文件。
- 构建命令未执行、部署未派发。无新提交、不需合回 int_main；验证失败，worktree 保留未删除，任务 blocked。未启动或修改运行控制台。
- 通用构建预检 JOB-77bc13d7d9 最终 failed，队列无活动任务；独立附加失败为本机 Docker info 超时、审查服 SSH/暂存目录与相关依赖检查失败。该通用预检会检查三服，审查服失败不冒充测试服失败；本次未对三服执行部署。SQL 输入失败独立成立。
- 末次测试服只读观察仍为 2026-11-23-08-35-27，UP/200、非维护、无 opening pending。专用 worktree 状态仍干净。
- Docker 超时定向复核：docker info --format '{{.ServerVersion}}' exit 0，返回 29.9.1；未重启引擎。只能证明当前引擎可响应，不追认原预检成功。修复应用后继续发布仍需重新通过相应前置检查。
