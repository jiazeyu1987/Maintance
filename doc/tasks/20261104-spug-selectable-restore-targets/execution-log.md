# 执行记录

- 续行授权：用户要求“进行补齐”，本轮进入正式本机实现；恢复执行本身和正式服修复不在范围。现有 volume-only 合同需扩展，配置登记生成器需补齐；这些属于待实现项，不当成本机开发阻塞。按 RED -> GREEN -> REGRESSION 完成后再提交；远端安装先准备可审核计划。

- 用户授权范围：开发 Spug 中按次选择测试/备份/正式服务器的恢复功能；未授权执行实际恢复、远程目标变更或覆盖。
- 前序说明任务已完成；本轮先创建任务文档。E:/IntRuoyi/docs/powershell-memory.md、worktree-memory.md 前序已确认缺失，继续定位现存权威资料，未执行高风险动作。
- 已知证据：localhost:18080 为 transfer 容器，源挂载 C:/Spug/runtime/ops/spug；当前 IntRuoyi .57 safe 覆盖映射为空。目标选择需求不能通过伪造映射解决。
- 现存规则副本定位到 C:/SpugHandoff/release/repository/docs/{powershell-memory,worktree-memory,release-backup-restore,server-access}.md；读取命中章节。server-access 明确三服当前任务授权要求；E: 路径不伪造。
- 源码归属：运行 UI 在 codex/spug-backend-jar-patch-20261102=a6d500c 的相关清单/UI 提交中；该分支工作副本存在独立侧栏任务脏文件，未改动或整体合入。int_main=9a62391，未创建新 worktree 或修改生产代码。
- 调用链：package-catalog.js -> simple.js -> smallapp_entry.admit_selection/reserve -> smallapp_adapter.HttpBridge -> recovery_control_smallapp_native.Native.resolve -> recovery_minimal_runtime -> recovery_replace.execute/verify_services/prepare。Native.resolve 必须同时匹配来源登记、restoreConfigurations 及恢复点；替换实现目前只接受独占 local named volume，拒绝共享或 bind 类型，实际数据范围为业务数据库、MinIO物理存储和Redis DB。
- BDD：三服逐次选择、包固定、覆盖确认、空目标独立、目标漂移拒绝、异常可见与重复编号场景记录于 design.md；尚未进入 TDD RED 或产品实现，不把代码审阅当行为验收。
- BLOCKER: experience-preflight -> 生产主实例的实际资源定义/恢复适配范围尚不明，按项目规则请求三服只读检查授权；pending，不连接远端，不执行恢复/停止/修改。只读服务与资源核查结果决定正式实现边界，不能用 mock 成功或把 freshRef 复制为 replaceRef 代替。
- 本机完整设计已形成，可审阅；后续独立工作已完成当前可推进范围，等待只读核查许可后继续。任务文档 blocked 不表示原说明任务未完成，也不表示任何恢复已经执行。
- 用户明确答复“允许只读检查三台服务器”，解除授权阻塞；范围为 .57/.58/.59 只读资源、实例及恢复执行器检查，不包含恢复、停服或写入。继续同一任务。
- GREEN: experience-preflight -> PASS（仅三服只读核查）：已核 server-access 当前任务授权；SSH 使用现存密钥和 strict host key；通过标准输入执行只读 Python，仅读 Docker 身份、挂载、监听及预定恢复目录，不输出环境变量/凭据，不执行恢复、SQL 写入、停服或远端文件写入。固定 E: 资料缺失，以现存交接副本核对；如主机身份或命令失败，保留失败，不切换目标。
- 执行器使用 bundled Python 的绝对路径；系统 python.exe 为 WindowsApps alias，未把空输出视为查询成功。SSH默认密钥认证三服均失败；定位已有交接 sshIdentityFile/sshKnownHostsFile 后保持 StrictHostKeyChecking=yes、IdentitiesOnly=yes 完成授权检查，未输出凭据。
- READONLY: inspect_remote.py -> .58/.59运行容器与挂载清单取得；.57大范围docker inspect超时。缩小登记主实例范围仍在backend inspect上超时，失败证据保留，不把超时写成目标不存在。
- READONLY: read_main_resources.py -> 三服返回；.57/.59 safe服务restoreConfigurations均为空。.58/.59主库端点分别为172.29.235.22/172.29.239.22，数据库ruoyi-vue-pro；Redis各为相应网络.24，DB=1。
- READONLY: read_restore_preconditions.py -> 三服返回；.58/.59 MySQL SELECT元数据成功（8.0.39、log_bin=1、业务库存在）；.57 MySQL/Redis/MinIO为bind目录，backend精确inspect仍超时。未读取业务记录，未执行SQL修改。
- 运行异常证据：正式docker ps显示intruoyi-backend Restarting (137)，uptime load average约1279，swap几乎耗尽；没有取得OOMKilled证据，不判断137根因，不擅自重启或停止历史演练容器。
- 设计收敛：复用现有服务器选择/确认入口，采用一次正式基础登记后按次选择；不要求每次人工改文件，也不凭空扩大为新的动态登记页面。正式服bind与现有volume-only合同不兼容，需要正式设计、BDD/TDD及真实环境前提；.58/.59资源类型匹配不等于完整恢复就绪。
- BLOCKER: experience-preflight -> 三服完整恢复接入的正式服存储合同及稳定运行态前提未满足。当前只读核查完成，功能实现/安装/真实恢复均未完成；按AGENTS fail fast，不开始半成品生产修改或提交。assessment.md已给出可审查事实、未知项及正式接入步骤。未创建任务worktree，无自有进程/控制台需恢复；无远端写入。
- LOCAL VERIFICATION: 12项任务文件显式UTF-8读取、JSON解析与只读脚本compile语法检查PASS；docs/request-command-log.md定向git diff --check PASS。不是BDD/TDD/E2E或恢复验收；未提交阻塞功能实现。
### 动态恢复点解析 BDD / TDD
- BDD: future-backup-selection -> Given 一次登记的来源及归档目录，When 新全量或增量包出现并按原编号选择，Then 自动绑定完整祖先链且不修改来源配置或原清单。
- BDD: source-authority -> Given 来源隔离或取消该恢复点，When 目标预检，Then 必须通过来源当前认证目录核准，否则拒绝；目标不能凭一份旧清单绕过来源资格。
- RED: python -X utf8 -m unittest discover -s scripts/tests -p test_restore_archive_catalogue.py -> FAIL, 新的动态目录模块尚不存在。
- GREEN: 同命令 -> PASS, 7 tests；真实临时文件验证新点发现、完整父前缀、重复ID、原始字节漂移、来源及退出证据；不代表真实恢复验收。
### 目标登记、按目标检查与整体回归
- BDD: one-time-registration -> Given 三服真实目标配置，When 生成登记计划，Then 同步形成simple/entry/bridge/registration/control的对应引用，保留历史路由；输出PLAN_ONLY，不安装或恢复。
- RED: unittest test_restore_target_registration -> FAIL，登记计划模块不存在；GREEN -> PASS，3 tests。先行草稿移出代码树，RED后再恢复并验证。
- BDD: selected-target-preflight -> Given 某台主实例异常，When 查询来源备份或其他目标，Then 不探测该无关主实例；When 选择异常目标，Then 请求带targetConfigRef并显示真实异常。
- RED: source-catalogue skip-main-probe TypeError及selected target URL断言失败；GREEN -> PASS，16 catalogue/registration tests及11 cross-route tests。
- Windows扩展回归发现原Linux专用/proc、POSIX custody测试不可在Windows执行（63 failed/31 errors）；未当业务RED或伪装通过。现改在Linux真实文件系统验证。Spug合同unittest 44 PASS。
- Linux首次合并回归：227 PASS，7 FAIL、10 ERROR；缺redis依赖、Docker测试容器内Windows worktree .git路径不可解析、两个真实目录测试落在overlay而非local volume，并发修改期间主实例新用例失败。记录这些为测试环境/集成失败，修复环境后重跑，不删除保护检查。
- GREEN: experience-preflight -> PASS（仅本机Linux单测）：只读挂载本任务源码，不挂docker.sock；任务容器spug-restore-root-unit-20261104-v2、唯一local volume spug-restore-root-tests-20261104；临时写入仅该volume，结束核名称/无人占用后删除。无服务器修改、业务写入、备份或恢复。
- 三服只读复查：.58/.59后端frontend healthy；.57 load=1376.64且backend inspect仍3秒超时，未确认根因，不修复不重启。来源身份/范围canonical路径在三服均存在，但内容pin一致性和归档完整访问仍必须实际安装预检。
- REGRESSION: 本机Linux专属local volume +真实Linux依赖 -> 234 tests PASS，0skip；包含既有Linux进程/失败保留/宿主预约合同。两项新增主实例边界随后单独Windows/Linux各29 PASS。
- REGRESSION: Windows平台支持的safe package构建/主实例/catalogue/登记合同 -> 55 PASS；安全/轻量包均验证真实文件清单与共享control代码。Linux容器无法解析Windows worktree .git 的包构建验证在Windows原Git环境完成，未伪造Git历史。
- REGRESSION: Spug unittest discover -> 44 PASS；node --test smallapp_ui_safety.test.cjs smallapp_restore_result.test.cjs -> 42 PASS。未改前端控件或覆盖当前运行UI。
- REGRESSION: test_restore_target_http -> 1 PASS；真实本地HTTP通信验证认证、所选target参数、重复/空/未知参数拒绝。仅合成合同数据，不是Spug用户E2E。
- REGRESSION: git diff --check -> PASS；中文文档显式UTF-8重读核对。
- Closeout pending：确认专用测试volume为local且无容器占用后已精确删除spug-restore-root-tests-20261104；本任务测试容器--rm退出。未启动或改动产品控制台；保留含未提交实现的自有worktree，不清理其他任务。
- 当前交付（上轮历史）：本地实现与必要合同验证完成，安装计划可审查；三服服务和本地Spug均尚未更新，无真实恢复。按“未解决前置不得提交”保持未提交，等待安装授权与正式服稳定/实际writer/存储证明；不标completed。
- AUTHORIZATION 2026-11-04：用户明确答复“允许安装控制组件和登记配置，不执行恢复”。范围为三服控制组件与目标登记、本地18080 Spug定向更新，仅重载本任务控制服务；禁止实际恢复及主程序/数据库/MinIO/Redis重启。正式服未通过前置仍禁用。立即续作同一任务，不重复索取已授予的安装权限。
- READONLY install-preflight：.58核459容器、.59核201容器的完整inspect；主实例MySQL/MinIO/Redis写卷无其他RW消费者。真实MySQL/Redis连接均指向各自主backend IP；网络含onlyoffice/外部集成，继续核依赖，不把网络共享等同数据资源共享。正式服load=1413.27且backend inspect仍4秒超时，按已批准范围仅安装组件、保持目标不启用，不修复主程序。
- READONLY archive-dependencies：三服canonical source identity/scope SHA相同；当前NAS含4个正式来源点，.57认证目录返回4个原编号、historyErrorCode=null。最新点smallapp-a54a05be9dab45e490a3979551536b0c引用source私密目录的version-v2/images.json，.58/.59缺该非秘密元数据；安装时仅按原绝对路径和原pin复制相同字节，绝不改原归档或pin。当前backend/frontend镜像与该版本元数据一致。
- 本轮修正只读脚本变量替换载体两次SyntaxError（替换命中正则/字符串）；改为前缀赋值，不再文本替换业务代码，三服最终退出码0。该载体失败不记为业务测试RED或伪装远程成功。
- 实现验证阶段已PASS；安装授权已收到。正式目标禁用是本次明确要求的结果，不阻塞可验证实现快照提交；后续包仅由该已提交目标在新临时发布worktree构建。没有宣称正式服可恢复。
- GREEN: experience-preflight -> PASS（组件构建与隔离）：实现提交f36ff55；专用临时发布worktree=C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104/Maintance，detached f36ff55，非复用开发区；构建命令bundled Python -X utf8 ops/backup_engine/build_variants.py --output-directory C:/Spug/runtime/private/restore-targets-20261104/packages-f36ff55。只使用Git已提交文件；输出在私密目录，不进入源码包。验证命令git status --porcelain、脚本导入/manifest逐文件SHA核对及现有包合同回归；本worktree预期无新提交，收尾核clean后删除。
- BDD: installed-targets -> Given 正式来源认证目录当前freshTargetConfigRefs为空（真实RED），When 安装本任务控制组件与经过核验的.58/.59目标，Then 真实认证目标目录出现对应唯一引用，Spug选择/取消不产生操作；.57前置失败保持不启用。
- GREEN: experience-preflight -> PASS（首次远程写入，仅控制组件安装）：明确授权已保存；唯一新根分别为.57/.58 /var/lib/docker/intruoyi-data/spug-main-restore-20261104-v1、.59 /mnt/intruoyi-data/spug-main-restore-20261104-v1，存在即失败，不覆盖旧安装。安装前内存验证standard包完整manifest和每个文件SHA，解包仅普通相对文件，所有目录700/文件600；先仅写新根，不改任何运行控制或业务程序、镜像、卷、NAS、fstab。回滚保留新根组件证据，未登记时不影响原路由。stage阶段不启动服务。
- GREEN stage -> 三服同一standard包SHA0791fc624df95a9b181d8221d711836030afea83052e0787b99cbc4490dc3faa，manifest65ad3484587449de2952896cf6e4b2fc76b4fb17de3871e461550e546f5e28d9，每服121程序文件逐项校验。服务未启动、未恢复。
- GREEN: experience-preflight -> PASS（.58/.59目标配置及自有控制服务启动）：写入仅新安装根、两个精确canonical images.json原字节与两个专属systemd单元；先真实复核五角色ID/镜像/health、所有容器与配置的端点引用、MySQL/Redis实际连接、数据服务无公开端口、MinIO桶/身份列表、只读应用配置pins与local存储身份。任一不通过立即保留证据并停止对应目标，不补造writer证明。配置后真实调用动态归档解析、程序版本兼容、主实例观察、资源预算；通过后才daemon-reload并enable --now专属单元，禁止调用任何业务容器stop/start/restart、恢复operations POST、NAS写入或删除。锁引用须有正式归属；同一主实例后续备份必须共锁，不将当前来源备份路由转到目标。正式服只留组件安装，不生成可执行目标。
- FAIL install-preflight（无服务启动）：首次缺jsonschema依赖路径即停止，随后按既有控制配置补显式site-packages。外部资源引用扫描命中历史已停backend/frontend；没有运行外部直接端点引用，历史保留、启动会触发主实例network成员漂移拒绝。随后真实MinIO IAM检查发现.58有3个、.59有4个enabled账号；其中两服各3个EDHR账号拥有s3:PutObject/DeleteObject/DeleteObjectVersion权限，均未与当前主程序env/只读properties/infra_file_config/infra_config配置建立对应。.59另1个文档账号与infra_file_config.id=28对应。当前仅证实DB/Redis连接来自backend，不足以证明MinIO所有writer归属。
- BLOCKER: experience-preflight -> INSTALL_ADDITIONAL_OBJECT_WRITERS_REQUIRE_REVIEW。保留两个安装目录的external-references.json与object-iam-review.private.json；未写writer-evidence=true、目标owner/control/registration、canonical版本文件、systemd单元；未daemon-reload/启动/重载服务。mc来自各服已有minio容器/usr/bin/mc，仅读admin user list/info及policy info；写入仅新控制根private工具/配置/证据，无账号、策略或对象修改。已向用户询问3个EDHR账号是否还有其他系统直连，未请求重复安装授权。
- BDD: legacy-control-compatibility -> Given 已安装旧HTTP控制服务只认识/selections，When 查询旧目标，Then 保留原URL；只有新连接显式selectedTargetPreflight=true才追加目标参数。RED: unittest cross-route/registration -> 1 FAIL+1 ERROR（旧URL被改变、新登记缺能力标志）；GREEN/REGRESSION -> Spug45 PASS、registration3 PASS，diff --check PASS。该显式协议能力保持旧合同，不是失败时静默降级或重试。
- FINAL VERIFY（仅组件stage）：verify_component_installation.py三服返回121文件checksum全部相同，serviceUnitExists=false、target/controlConfigurationExists=false、registrationExists=false、operationCount=0。结果保存installation-status.json。没有实际数据恢复、主程序或数据容器停启、NAS/共享盘修改；localSpugUpdated=false，未把单测当页面验收。
- 当前阻断结论：代码提交f36ff55、兼容性df9c3f8已保存；开发worktree与临时发布worktree保留。临时发布worktree目标f36ff55、无新提交、git status --porcelain为空；安装未完成，未合回int_main、未删除，不清理他人进程/工作区。用户确认writer归属后须补共同锁、真实配置/资源及来源传输核验，再继续对应安装，不重复已授权范围。
- USER FACT CONFIRMATION：用户答复“这些账号仅供 IntRuoyi 主程序使用”。该确认是对象writer归属依据；与真实IAM账号/策略清单及当前DB/Redis连接/网络/端口观察共同记录，不能替代存储、程序pin和执行前漂移校验。解除.58/.59人工归属前提，继续安装，不索取重复安装权限；.57身份前提不变。
## 继续安装：账号归属确认后的准入
- 用户明确确认 MinIO 所列 EDHR 账号仅供 IntRuoyi 主程序使用；将实际账号与策略摘要绑定到安装证据，任何新增账号或策略漂移继续阻断。
- GREEN: experience-preflight -> PASS：沿用已授权的控制组件和登记安装，继续只读核对共同任务锁；不执行恢复，不重启业务及数据容器，正式服身份不可验证时保持禁用。
- 配置审查：replacement-state 仅允许操作 claim；安装预建的空 runtime 子目录会被判为未完成 claim。运行时由引擎在独立操作 claim 下创建 runtime，安装脚本应不创建占位目录；只删除本任务已验证为空的该占位目录，不改变引擎安全检查。
- REGRESSION: 存储修正后 safe/lightweight包、main、catalogue及登记合同 Windows56 PASS；实现提交08045c1，仅3个本任务文件。
- GREEN: experience-preflight -> PASS（新版本隔离构建）：新建临时发布worktree C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104-v2/Maintance，检出08045c125c6a3e6f4ff229181802c5ee3d75fc5d；build_variants.py仅使用该Git提交输入。旧f36ff55安装worktree保留直到收口，不从脏目录打包。新版安装目录使用独立v2，不覆盖已有不可变预检证据。
- BDD/RED/GREEN补充：.59 Docker卷Options为空，宿主另有真实bind；使用显式volume_backing_paths固定真实底层目录，不推断、不改Docker options。Linux98项全通过，Windows91通过/7 POSIX项目转Linux全部验证；包回归11项通过。
- 本机真实Spug登录/恢复选择基线：登录成功，来源4个原备份包可读，三目标目前均未登记，只有登录POST、无恢复提交。前两次脚本在安全警告确认顺序上超时，修正为真实页面确认后再等token；没有修改登录设置或伪造会话。
- GREEN: experience-preflight -> PASS（同一安装任务版本迭代）：继续使用本任务全新创建的v2临时发布worktree，先核clean后切换本轮最新已提交实现；重新构建到新输出目录，新安装根v3不覆盖v2不可变配置。没有跨任务复用或混入未提交输入。
- GREEN: experience-preflight -> PASS（目标控制通道）：只启动本任务稳定目录的SSH通道supervisor，精确占用33658/33659和当前空闲18558/18559；远端仅127.0.0.1:34657回连现有来源32657。固定身份/known_hosts，隐藏窗口、互斥及自动重连；不停止现有50392来源通道或其它进程，不开放服务到公网。
- GREEN: experience-preflight -> PASS（本机18080定向接入）：.58/.59认证selections真实可用、source catalogue4点且ledger仅service.lock/无claim。安装计划保存私密spug-route-plan.private.json，比较现有simple/entry/bridge canonical SHA与adapter原SHA后，仅增加两个目标及原有adapter的已提交选择预检逻辑；保留全部历史routes/fresh映射/其它来源及新UI，备份原文件，SIGTERM仅精确own smallapp_entry.py让supervisord重启，不重启Spug容器/数据库/其它桥接服务。
- GREEN: experience-preflight -> PASS（本任务实现融合）：int_main与任务base9a62391一致，待融合19个实现/测试文件与主工作区脏文档及其它并行任务无路径重叠；index空，先执行--ff-only，再在合并结果验证。只融合实现提交，不纳入主工作区现有脏记录，不清理其他任务worktree/进程。

## 合并验证与临时发布目录收尾
- REGRESSION: int_main=e1389aa，Python 合同 137 PASS；Windows 的 7 项 POSIX 检查已由相同已提交实现的 Linux 98 PASS/0 skip 覆盖；Spug 45 PASS、JS 42 PASS。
- GREEN: experience-preflight -> PASS（仅本任务两个临时发布 checkout 清理）：目标路径精确位于 Codex worktrees 根目录，HEAD 分别 f36ff55/45b4e3e，无未提交改动、无新提交，均为已验证 int_main 的祖先；无引用这些路径的业务/构建进程，稳定控制通道不使用这些目录。使用 git worktree remove，不使用 force，不处理其它任务目录、进程或 NAS；本任务开发 worktree 为正式服准入后续保留。
- GREEN: release-worktree-cleanup -> PASS；两个临时发布 checkout 的 Git 注册与物理路径均已移除，无新提交需合回。详见 release-worktree-cleanup.json。未清理开发 worktree 或任何并发任务资源。

## 最终安装与验收记录（取代旧阶段结论）
- GREEN: .58/.59安装 -> PASS；最终包commit45b4e3e/121files，main运行合同、真实storage-v2、IAM身份/策略pin及用户归属确认、共同锁、程序版本和完整来源目录均通过。控制服务只监听loopback；.58旧Python SELinux执行失败后使用独立/usr/local/libexec/spug-main-restore-20261104/python，918文件逐SHA相同、标准restorecon及ssl/json/sys验证，不关闭SELinux或改业务路径标签。
- .58初选33658/33758端口已有其它归属，未停止占用者；改为实查空闲43658，.59为33659。Windows固定来源42657转远端原32657，两目标反向34657通过该新独立来源通道，不依赖旧来源进程；当前用户登录启动三项任务均Running，未进行操作系统重启测试。
- LOCAL INSTALL: 保留当前18080运行UI及原路由，只补已提交adapter选择预检与两目标登记；SIGTERM仅本任务smallapp_entry由supervisor接续，其它bridge PID及业务/Spug容器未重启；18081未触及。原配置备份及私密生成计划留存私密目录。
- GREEN: Playwright真实Chrome/真实Spug登录 -> PASS；当前4原备份点；.58/.59可选，确认摘要绑定server和精确targetRef，覆盖勾选前不可最终执行；返回修改取消。仅login POST，无恢复POST/blocked requests，详见browser-choice.json及confirm-58/59.png。入口重载后首次配置读取曾遇短暂HTML/JSON失败，等待入口就绪后重跑PASS，未隐藏错误或修改页面。
- GREEN: final-readonly-installation -> PASS（两个启用目标）；.58/.59 active、pins有效、operationCount=0、claimCount=0、所有业务StartedAt不变。三服121文件SHA一致。正式服.57 EXACT_BACKEND_INSPECT_TIMEOUT_4S、load1553.51，保持disabled/no controller；该前置未通过，不记录正式目标准入PASS。
- FINAL SCOPE: 控制组件及本机接入本轮安装已完成；正式目标未启用，原三服均可恢复需求剩余blocked。没有任何实际数据恢复、业务/数据库/MinIO/Redis停启、NAS/fstab或租户数据修改。开发worktree保留用于同任务后续，干净临时发布worktree清理已完成。
- 收尾记录工具：首次复杂PowerShell内联凭据扫描因引号载体SyntaxError未执行，改为UTF-8脚本；扫描器首次把自身私钥标记检测代码误判，收紧为独立完整PEM头行后复核。两次均为记录工具失败，不记业务RED/GREEN；未输出凭据值、未暂存或提交。
- GREEN: experience-preflight -> PASS（单独保存最终任务记录）：本轮实现已分项提交并完成融合验证；正式目标准入阻塞已向用户明确报告。仅暂存本任务目录及request-command-log的两段本任务记录，后者使用HEAD正文加精确自有条目生成索引blob，保留工作文件中其它任务内容；核空索引、HEAD、UTF-8、无凭据、staged scope和diff --check。提交前后比较无关脏文件摘要，不修改/暂存并发任务资产，不执行推送或实际恢复。
- RECORDS COMMIT: fdcb608b41a0816b3844d028b40276bc1e187c88，40个自有记录文件，提交前后9940个无关脏文件内容摘要相同，工作区请求日志其余内容保留，索引为空。
- GREEN: experience-preflight -> PASS（截图原入口补充验收）：核运行native BackupRestore实际嵌入同一backup-restore页面；补验真实登录后/backup-center的“全部包清单→恢复”第一条已核对备份，绑定该包并分别选择.58/.59，确认后取消。只允许登录POST，任何恢复/其它写入请求都会阻断并判失败；不使用mock、不执行最终确认，不改产品代码。
- GREEN: node verify_spug_choice.cjs catalog -> PASS；实际/backup-center原入口、全部包清单第一条可恢复包→弹框→.58/.59真实准入→确认摘要绑定原包编号和各自精确目标→返回修改→关闭弹框。仅/api/account/login/ POST，无blocked请求，无恢复提交。browser-catalog-choice.json与catalog-confirm-58/59.png留证，正式服仍disabled。没有产品代码修改，无需重复已通过的实现回归。

## 2026-11-05 接续原三服登记
- 已完成后续正式FULL History350→测试原MAIN History355，真实终态、全结构数据/对象/引用/Redis、运行态及真实业务页面验收通过；f867174保存completed记录。此处仅继续先前明确授权的三服控制安装和目标登记，不重复恢复。
- BDD: 备份服控制配置正式合同 -> Given原.59业务保持运行且无活动恢复，When核实际安装容量和SAFE调用合同，Then非法64GiB摘要预算在目标访问前拒绝；合法16GiB摘要与独立64GiB SQL展开可共存，组件更新只重载自有控制服务。
- BDD: 正式目的地资源准入 -> Given正式服现在已健康，When复核真实实例、存储和外部消费者，Then只按当前完整独占证据启用；若共享资源前提未满足，保留明确阻塞，不以历史负载解释当前状态。
- BDD: 三服可选范围真实呈现 -> Given目标实际准入结论，When真实登录Spug从全部包清单恢复入口选择目标并确认后返回，Then包与精确目标绑定，未通过的目标继续禁用，全程零恢复提交。
- GREEN: experience-preflight -> PASS（接续只读复核）：已识别原任务、更新目标和里程碑，按experience-index命中发布包接口/容量合同及PowerShell/服务器规则；复核现有用户授权，不扩至.57/.59数据恢复或业务停启。远端原始配置/凭据只写私密目录，公开报告只保留身份与门禁结论。
- 当前只读观察：.57 load0.60，inspect成功，旧超时门禁已解除；实际backend可写挂载与MinIO9000/9001暴露不满足现有MAIN安装合同，不能删除检查后强行启用。.59旧包121文件完整，owner摘要64GiB非法，SQL64GiB独立保留；登记五服务只有frontend运行，原backend及三数据服务停止。第一次观察工具使用formalModuleDir错误字段失败，修正为真实formalModuleDirectory；这是只读工具错误，非业务RED，未改任何远端文件。
- GREEN: experience-preflight -> PASS（.59控制同步隔离构建）：新建专属C:/Users/D01021/.codex/worktrees/spug-review-control-release-20261105/Maintance，检出04f5f9ce958b52479c0c729fe32dbb69669e73fb，当前实现已提交且必要Windows/Linux/真实恢复验证通过。构建/合同验证只读取该已提交输入，私密输出单独目录；无业务运行端口、无新提交、无自动int_main融合，完成后核clean/注册/物理路径清理。
- GREEN: 专属发布checkout build_variants.py --output-directory C:/Spug/runtime/private/restore-targets-20261104/review-control-release-04f5f9ce -> PASS，SAFE文件清单摘要7474080922c85c5a03ab514176f9fcd32af6a585a657ae25eb07c20c66839b7b；pytest scripts/tests/test_backup_variants.py -> 15 PASS（34.04s），含实际SAFE/FAST非法预算早拒绝、prepare与破坏SQL审计合同；无本轮生产代码变更，不重复已通过的Linux195项回归。
- GREEN: experience-preflight -> PASS（.59自有恢复控制服务切换）：按resumption-control-plan.md执行原已授权控制组件安装，19:30只读当前receipt/owner/control/unit与全部业务完整身份已留证；无operation/claim/active。持原目标共同锁及宿主预约锁，安装新不可变代次，只修改owner formal目录/摘要16GiB及control程序指针，target/source/SQL64GiB不变；只重载spug-main-restore-59-20261104-v3.service，不触及业务、数据、NAS或失败历史。实际预检失败则原样报告，不手工启服务使其通过。
- 首次安装在任何文件写入前报BUSINESS_DRIFT并停止；只读逐字段比较确认Docker Mounts列表顺序无语义变化。验收工具与正式MAIN既有方式一致，按Destination排序后比较完整Mounts，所有业务ID/PID/StartedAt/配置均无差异；未修改业务或降低字段检查。review-business-drift.json留证，然后接续原计划。
- GREEN: .59控制组件同步 -> PASS；新122程序文件全SHA一致，实际Native配置验证、正式16GiB预算通过，SQL64GiB保留，target/source完全不变；仅自有控制重载，全部业务ID/PID/StartedAt/配置保持，零operation/claim/active。review-control-install.json留证。
- 当前认证GET：.58 -> HTTP200且精确MAIN可用；.59 -> HTTP500/REPLACEMENT_STORAGE_DIRECTORY_CHANGED。进一步只读定位三数据目录/真实backing的device/inode、完整物理语义保持，只有卷bind的mountId由132/136/140变52/50/51；backing mountIdentity逐字段未变。另原canonical归档路径不存在，原backend与三数据服务停止。本轮未挂载NAS、未启业务。
- GREEN: experience-preflight -> PASS（.59仅登记重启mountId）：依照已授权“控制组件和登记配置”，持原共同锁及宿主预约锁，无operation/claim/active，仅发布独立owner/control代次，将三个已证实唯一差异的mountId更新为当前值；device/inode/backing/其它mountIdentity、数据与所有业务配置不改，严格存储检查保留，只重载自有控制服务。原副本/证据保留，不能自动扩大至挂载或启动业务。
- GREEN: .59postboot登记 -> PASS；仅mysql132→52、minio136→50、redis140→51，全部物理及backing身份保持；原业务ID/PID/启动时间/配置保持，control active。实际GET现在明确MAIN_TARGET_OBSERVATION_FAILED，原业务停止及归档canonical未挂载前不得声明可执行。
- GREEN: experience-preflight -> PASS（接续真实Spug选择/取消验收）：真实Chrome登录后走/backup-center全部包清单恢复入口；核.58精确目标确认/返回，.59当前准入失败显示且禁止提交，.57未登记禁用。路由仅允许登录POST，任何其它写入拦截并判FAIL；不mock、不改产品，不执行恢复。
- GREEN: verify_resumed_choice.cjs -> PASS；真实登录、全部包清单恢复弹框、.58精确目标确认后返回、.59显示MAIN_TARGET_OBSERVATION_FAILED并禁最终提交、.57未登记禁用；仅登录POST、blocked=0、恢复POST=0。截图与resumed-browser-choice.json留证，原成功恢复记录未变。
- .59补充只读预检：三原数据服务及backend处于stopped，restartPolicy=no；原frontend38081运行。CIFS /mnt/intruoyi-backup-nas已存在且新FULL point SHA正确；canonical nas根存在/空/未挂载。原服务启动及新增只读bind计划见review-original-services-plan.md，未执行，须单独授权（先前原业务恢复只含.57/.58）。
- GREEN: experience-preflight -> PASS（接续专属发布worktree清理）：C:/Users/D01021/.codex/worktrees/spug-review-control-release-20261105/Maintance精确位于已核实worktrees根，HEAD=04f5f9ce、status clean，无新提交、无需融合；所有构建/测试会话已exit0且无自有运行控制台依赖。仅git worktree remove本次路径，不用force，不触及原开发或其他并发checkout；完成后分别核Git登记和物理路径。
- GREEN: verify_resumed_closeout.py -> PASS_FOR_COMPONENT_SCOPE；专属发布worktree注册与物理路径均不存在、无新提交无需融合；.59新122文件及16GiB正式限额通过，原全部业务ID/PID/StartedAt/配置保持，零operation/claim/active；.57/.58/.59控制均active/enabled，.59python/PYTHONPATH/工作目录不依赖已删checkout。整体threeDestinationGoalComplete=false保留，不把控制收尾说成全部三目的地完成。
- IMPLEMENTATION COMMIT: 773310d，仅本接续9个安装/只读/验收脚本，实际生产组件修复仍为此前已提交04f5f9ce；无新产品功能修改。组件scope已验证，独立记录正式目的地合同缺口和.59启动/归档挂载授权阻塞；未推送或自动融合主工作区。
- GREEN: experience-preflight -> PASS（接续记录单独保存）：实现773310d已提交，当前索引无其它任务项；仅保存本接续报告、当前task/execution-log、两个计划和真实Spug选择取消截图，以及本线程使用说明/请求命令记录的精确自有条目。重读UTF-8、检查JSON、secret字段无明文凭据、git diff --check及staged精确范围。旧原任务其它文件已在int_main fdcb608/e2e894保存，保持工作区原样，不顺手暂存复制旧记录或清除未知文件。整体task保持blocked等待具体前提，不标completed。
