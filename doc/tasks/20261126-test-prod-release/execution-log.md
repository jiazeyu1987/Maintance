# 执行记录
本轮进展：构建JOB-2bd47a96f1/tag2026-11-27-13-02-27从compile-frontend推进build-complete-images；之前已实际核node44440/esbuild37384的创建时间与任务记录相同且CPU持续增加，编译完成后进程结束符合阶段推进，未重启构建。测试预检/发布r3载荷已准备未提交。正式只读调查新增：API日志52655在证书创建同秒成功执行目录工作簿导入，52633此前工作表数量失败；上传正文及响应未留存。历史导入实现含证书/版本/快照迁移而明确不迁移审批附件，提供机制依据但未核当次部署字节。161行证据矩阵已生成，所有批准归属仍UNCONFIRMED，不据当前名称或关系猜测；详见prod-certificate-evidence.md。上一目标轮属进展，本轮亦有构建推进及新增来源证据，非相同阻塞空转。
用户新增指示已落实为只读调查：先自行查161张证书批准/导入/本机依据，不要求用户逐张核对，不猜测补造，正式保持阻断。实际DESCRIBE后精确范围READ ONLY查询，已确认tenant163=测试A，161主档/186版本/193快照同批创建且部分含E2E标识；申请/附件/项目导入批次缺项，审计仅页面查看。调查仍进行中，见prod-certificate-evidence.md。测试新构建JOB-2bd47a96f1/tag2026-11-27-13-02-27已通过迁移策略、后端编译，当前compile-frontend，未发布；自有构建路径C:/SpugHandoff/release/build/2026-11-27-13-02-27，固定41811b51e。
GREEN: experience-preflight -> PASS（新包构建）。真实58回填后observe：tag2026-11-26-01-52-12、backendHealth.status=UP、frontendHttpStatus=200、maintenance=false、runtimeOpeningPending=false。原恢复/验收均成功，精确修复全字段与新multi预检通过。执行发布中心build-release，payload build-r3.json固定已提交41811b51e376e7019f4b6df0071723c4ef55c20d；平台为新releaseTag创建本次专用源码worktree，维护执行目录仍C:/SpugHandoff/release/test-prod-20261126，禁止主工作区脏内容入包。无新代码提交、未操作正式57或59，正式业务归属缺口仍待解决。
2026-11-27恢复与专项保留已实做通过：accept JOB-adbf48e6ce / OP-9a7125549d736f11af5b succeeded/stopped，原receipt JOB-a727c820e0 phase=opened；原失败记录由正式accept核销为restored而非成功迁移。runner固定operation test58-preserved-repair-20261127-v1：inspect-original exit0 ORIGINAL，quiesce exit0 QUIESCED，apply exit0 COMPLETED/originalTriggerRestored=true/exactCompletedRowsVerified=true，inspect-completed exit0 COMPLETED且TARGET_PREFLIGHT_PASS:20261127_dcc_registration_certificate_multi_products，resume-writers exit0 WRITERS_RESTORED。同一前端98132267d0f8、后端82543a8522c2均running；尚待后端健康就绪，未开始新构建。私密各步JSON为preserved-inspect-original/quiesce/apply/inspect-completed/resume-writers.json，未把业务原文或凭据写入仓库。
GREEN: experience-preflight -> PASS（恢复验收与封存修复）。确认任务JOB-64bd45e9c7 succeeded，复用原restored回执JOB-a727c820e0；远端原恢复OP终态成功、旧tag/UP/200/maintenance=true通过。执行accept-recovery绑定原失败JOB-a2775541ef，随后封存runner固定恢复receipt JOB-a727c820e0依次inspect-original/quiesce/apply/inspect-completed/resume-writers，每步exitCode=0且状态正确才继续；原失败证据保留，不改账本，不涉及57/59。verify-bundle本轮再次通过，摘要未变。
GREEN: experience-preflight -> PASS（恢复终态确认）。原OP-c4691600cb704b625d2a已succeeded/stopped，04:44:13Z回执restored/succeeded；真实test旧tag2026-11-26-01-52-12、UP、HTTP200、maintenance=true。客户端1小时等待超时使本地JOB-a727c820e0为interrupted。已检查intruoyi_recovery_agent.recover的prior.phase=restored分支：仅health/observe/运行配置及旧schema/ledger/images核验后返回原receipt，不恢复SQL或数据卷。通过新的正式recover-release确认请求绑定原失败部署，沿既有原receipt接收结果；随后accept使用原receipt.jobId JOB-a727c820e0，禁止重建恢复点或改账本。
本续轮恢复阶段已推进：JOB-a727c820e0/OP-c4691600cb704b625d2a从restoring-database进入restoring-data-volumes，证明restore_database的检查点导入及第一轮全表校验通过；脚本随后执行第二轮checksums，尚未完成数据卷和程序恢复。只读核共911张基础表，worker7712持续running，最新rchar98670293547/syscr4866911、短时docker子30829；无失败回执。本轮属于verified wait且有阶段进展，未重复恢复、未accept、未执行精确回填或新构建。目标仍active，正式归属依据待用户答复；继续原操作。
最新续轮为verified wait/阶段推进：原恢复OP持续running，原导入23767输入累计从7528593437增至19096025118后退出，主worker7712仍活且连续创建后续docker检查进程；最新主rchar98577544004/syscr4696661，当前子25962。回执仍restoring-database/status running，不能认定完整恢复成功，未accept/回填/构建。只读SQL阶段采样当时无活动业务库语句，不据此宣称已校验完成。沿原JOB-a727c820e0继续等待，不重派。
后续目标轮仍为verified wait：原OP-c4691600cb704b625d2a实际worker=running，恢复7712与导入23767持续存在，输入rchar从5460539420经6020282397、6474414109、6853605405增至7242725405；阶段restoring-database，尚无终态回执。未重派、未重启、未accept、未回填；正式归属依据问题仍待用户答复。当前不是无进展阻塞，不能把持续运行任务标作失败或重新开始。
续轮运行等待：对原JOB-a727c820e0/OP-c4691600cb704b625d2a连续实时轮询，worker7712及导入子进程23767均running，阶段restoring-database；docker rchar从2848372764依次增至3612358684、4541069340、5071157276。属于已验证活进程等待，未重启、未重派恢复、未提前accept。新构建请求build-r3.json已固定41811b51e，仅准备未提交；待恢复和精确回填及健康验证后才构建。
2026-11-27本轮进展：正式recover JOB-a727c820e0 / OP-c4691600cb704b625d2a已进入restoring-database；failedDatabase备份7196359848字节，远端worker7712与docker导入23767实时运行，docker rchar2461808667。本轮属于实际状态推进+已验证运行等待，不是无进展。最新HEAD=origin/int_main=41811b51e376e7019f4b6df0071723c4ef55c20d，经7890 fetch确认；975d82300包含4份SQL登记，真实57四项READ ONLY预检全部PASS。57新多证仍因161条历史身份问题阻断，已向用户询问批准归属依据，未扩展写入授权。下一步按原recover任务观察，成功restored后accept，再用封存runner绑定JOB-a727c820e0依次inspect-original/quiesce/apply/inspect-completed/resume-writers，各exit0才继续。当前尚未accept、回填或新build，不重复恢复提交。
GREEN: experience-preflight -> PASS（测试58正式恢复）。runner-v1封存交付，run SHA03b3619427ebf96acafe6c4324031a8dee056b1c648506a3a67853d1f49402a0、worker11caad33e3dcef94a57fc5c4c1bdd4412aa2cbb5afd4a2962eb9cdd20ddcec45、manifest5e00e85a3e48b7e6da45d558692d647311e2310a814c1e110d809ee93b6722f6；真实隔离MySQL8项通过，包含实际Docker客户端超时且MySQL仍运行的保护保留实验。verify-bundle通过；真实58 inspect-current exit0 COMPLETED、全字段一致、preflight PASS、写者停止。恢复资产、原worker停止、原任务身份已核，使用正式recover-release绑定JOB-a2775541ef/tag2026-11-26-23-54-25；正式流程保全failedDatabase后恢复旧全库/数据卷，随后accept并同窗停写精确回填。不得清FAILED、不得重放原迁移、不操作57/59。请求文件recover-preserved-20261127.json，后续每步核回执再继续。
2026-11-27本轮续办：正式57只读确认旧版2026-11-26-01-52-12、UP、HTTP200、maintenance=false、runtimeOpeningPending=false。新多证预检失败精确汇总为tenant163共102条产品来源缺失；已通知IntRuoyi，不补正式业务数据。测试58私密runner-v1已生成并正在验证；审阅发现docker exec调用超时不等于mysql会话退出，已要求标签会话关闭证明与未知状态保持停写，应用线程正在修复测试。恢复/验收请求JSON已准备但未提交；本轮无恢复、部署或数据库写入。稳定执行器仍PID29472。下一步取得runner测试证据后先inspect-current，再正式recover→accept→停写精确回填→新包发布。此轮获得并解决新执行器疑点，协作线程仍active，不是三轮无进展阻塞。
目标续办进展：用户active goal为测试58及正式57发布。已读取04e39c9eb所带preserved-recovery-plan与验证；正式恢复后原ID回填方案已隔离演练，但尚未执行远端恢复。5个恢复平台源码摘要与演练记录一致。delta原文件摘要deafd09d069613230a7b283c63e17666c68431adf9db2d6090cb9905b551cab6（1027444字节/420CRLF），LF规范化摘要才为报告40e29590cafcf75b062cee2e4e7e1ae7ba18c0f55c80d978bf35a09b0b33a377；未静默改文件。已通知应用线程提供已验证私密串行执行入口及双摘要、原态/完成态校验、保护恢复与writer停写路径；明确禁止其操作58以避免并发。前序目标回合属取得新证据的进展，本轮也取得可用恢复方案及摘要边界，非单纯重复状态。
2026-11-27续发：HEAD=origin/int_main=5051212638acf78f293931f9ed234ea4e0344600。应用线程有用户授权的165张可丢弃证件临时匹配记录，本线程未执行数据修改。真实新多证预检PASS。正式只读inspect-release-recovery JOB-ad7dfb9e9e成功：原菜单applied，产品failed-or-unknown，后续3pending，recoveryAvailable=true。BLOCKER：现行续办仅允许零待迁移，FAILED不能前向发布；旧检查点恢复会覆盖新修复，不擅自执行。已通知应用线程提供保留新修复的正式恢复方案，测试仍维护、正式未动。
BLOCKER: 77d4f35f新迁移实际只读目标预检 -> TARGET_PREFLIGHT_BLOCKED:20261127_dcc_registration_certificate_multi_products:UNRESOLVED_PRODUCT。证据私密multi-preflight-query.json。多证规则修复未消除历史身份问题，未新构建/重放/部署、未改数据；原失败与维护状态保持，已反馈IntRuoyi。仅测试范围生效，禁止mark-tested/promote-prod/promote-backup。
用户2026-11-27要求修复后仅发布测试58，正式晋级从本次范围移除。7890 fetch核HEAD=origin/int_main=77d4f35f88208875200b729201adb8322177dac2。应用修复为多证共享产品，但身份缺失及快照不一致仍阻断，FAILED账本不可跳过。先只读执行新预检核当前真实状态，不重放失败、不补数据；旧任务保持blocked直到恢复依据与准入核实。
BLOCKER: publish-test JOB-a2775541ef / OP-0cedda93cd80e6cab84e -> failed/stopped，20261125_dcc_registration_certificate_products ERROR1644 SQLSTATE45000。恢复资料SQL7196341458字节、volume0 53954560字节、volume1 9684920320字节、recovery-record327010字节完整保存。旧容器停止，测试维护；正式未动。配套只读查询338行：UNRESOLVED_PRODUCT102、SNAPSHOT_PRODUCT_MISMATCH140、MULTIPLE_CERTIFICATES2、RELATION_CERTIFICATE_MISMATCH94，非去重业务数量。已通知IntRuoyi线程修复强制预检绑定缺口及提供不补数据方案/旧版恢复兼容证据，不擅自清理数据、重放SQL或启动混合状态。保留所有自有worktree，无完成提交。
GREEN: experience-preflight -> PASS（测试部署）。build JOB-e7c8f64f25 succeeded，tag2026-11-26-23-54-25，package6742a31a17a5761481fb4b0b362222275403347568a9ff334f75f4a034619fe2，manifest6cc30f31dff34816c765b7c91c8d4cbce6083cc386579c8aff668c2a4f0b0068。真实test预检JOB-9fb8ac2ed9 succeeded；执行publish-test，仅58。页面沿既定只读边界，真实登录、排产、版本和打印入口，业务写入与补数不在范围。
GREEN: experience-preflight -> PASS（恢复构建）。用户确认修复完成并继续授权58/57。7890 fetch核HEAD=origin/int_main=469b95273494aa59b84644a1ad0e495596a51e6d；修复8e8b4cf7登记4份SQL及3项预检，真实维护工具输入924迁移、1252资产、936SQL登记一致，两环境各5APPLY/3预检且缺失0，46项本机MySQL用例与历史摘要通过。目标真实数据预检仍须执行，不补业务数据。继续本任务维护worktree，build-release将创建新tag对应专用源码worktree，旧失败不改写。
BLOCKER: build-release JOB-fbf7db2cc2 / 2026-11-26-22-25-01 -> SQL catalog mismatch，未登记20261125_dcc_folder_template_menu.sql、20261125_dcc_registration_certificate_products.sql、20261126_dcc_registration_certificate_remove_ce_materials.sql、20261126_dcc_registration_fda_change_no_approval_date.sql。未部署58/57。已按用户持续授权通知IntRuoyi线程01a20836-968a-7f72-82df-3b2ddb1b3837修复并验证。失败源码worktree C:/SpugHandoff/release/build/2026-11-26-22-25-01及维护worktree保留，无本任务新增提交；阻塞未通过不提交完成记录。
GREEN: experience-preflight -> PASS（构建）。7890 fetch成功，远端df9746da3与本机两修复分叉；自动合并无冲突，保留原脏文件。hook首次缺Python未提交；显式配置现有Python后菜单迁移和端口守卫通过，合并提交1fedb340e。最近分贝通发布任务completed，当前两服版本2026-11-26-01-52-12；执行器PID29472稳定source路径，最新任务均成功。本次维护worktree C:/SpugHandoff/release/test-prod-20261126，目标aee01b67ad7624c97ca34362cfe4831d159d5b0e；构建固定新合并提交，自动专用源码worktree，不带未提交文件。
用户授权同步最新int_main并发布58/57。继承7890代理、不发布59、不补业务数据。前序已completed。
# 2026-11-27 继续发布：实时复核

- 用户确认已修复、继续发布；沿当前目标测试58与正式57，排除59。
- 原JOB-a2775541ef仍failed，OP-0cedda93cd80e6cab84e worker=stopped，backend/frontend均停止；恢复SQL和两个数据卷归档仍存在，未执行恢复或重启。
- 固定04e39c9eb新multi_products SQL在正式57通过READ ONLY事务预检：BLOCKED / UNRESOLVED_PRODUCT。正式服未写入；已通知IntRuoyi只读定位，测试165条任意匹配授权不得扩展到正式服。
- 保全恢复计划已核，等待同一协作线程交付带原始/LF双SHA、精确原值核验及失败闭合的串行执行入口；不重放失败SQL、不改FAILED账本。


## 2026-11-27 新包测试部署
GREEN: experience-preflight -> PASS；构建 JOB-2bd47a96f1 成功，测试发布预检 JOB-21940d9346 passed，固定 releaseTag 2026-11-27-13-02-27、提交 41811b51e376e7019f4b6df0071723c4ef55c20d，包和 manifest 摘要匹配；健康、空间、写者、恢复配置和起点计划通过。预检不替代停写后迁移数据复查与页面验收。下一步仅提交同包 publish-test，正式保持阻断且不补业务数据。

## 证书删除授权及只读入口核对
用户确认正式161张（tenant163）、测试165张（tenant169），保留审计及原始附件。精确ID清单已冻结于private/test-prod-20261126/certificate-deletion/scope.json。BDD: Given 两服已确认清单且无并发迁移，When 真实前端执行系统删除，Then 只软删除范围内主档、保留版本快照附件审计、逐条核成功/失败及重跑迁移预检。
GREEN: experience-preflight -> PASS（正式页面只读入口核对）；使用受保护admin凭据及既有真实登录路径，仅检查租户访问/注册证删除入口，不提交删除。本轮登录不改变业务数据，私密证据不提交。测试服仍在原部署中，不执行测试写入。

### 删除准备状态
正式范围tenant163=测试A，161；测试范围tenant169=测试A，165（真实查询，创建人910251=yingtaigroupadmin）。已从原诊断与原修复完成态抽取scope.json，不按同ID跨环境套用。用户已确认两批逻辑删除并保留审计和原始附件。现行命令服务deleteCertificate仅软删主档、检查行版本/公司访问与待处理变更/上传/延续，版本快照附件保持；迁移候选限定c.deleted=0。
实际prod页面以受保护芋道源码/admin成功登录，但无租户切换入口；已请求现有测试A私密凭据位置或已登录标签页，不重复请求删除授权。BLOCKER: deletion-login -> 无可用目标租户登录态；删除执行0。正式部署仍阻断。
测试原部署OP-0595eff9c7de1f328880正在进行；原恢复数据库7196377851字节，附件卷9684899840字节，Redis卷54016000字节。已观测候选后端运行，after-migrations与before-backend-open数据库契约PASS；不以此代替任务终态和页面验收。

页面核对补记：首次附加日志误用worktree相对路径导致写入失败，脚本仍运行；如实保留该执行错误，不回填伪造时间。此前本轮部署GREEN已记录页面只读边界。实际menu页面登录、空数据查询、同tag版本说明通过；6条观察待逐条归因。GREEN: experience-preflight -> PASS（打印真实页面）。固定JOB-9ac07e7db3/tag2026-11-27-13-02-27，已审阅脚本只允许登录与打印票据POST，其余写入拦截，保留异常。

## 测试部署及基础页面验收结果
2026-11-27-13-02-27：JOB-9ac07e7db3 succeeded，远端OP-0595eff9c7de1f328880 succeeded/stopped；manifest SHA5915efb31e2cf628db2af87be2c75f48d696b00caa921f395ecce0263ca79034，IMAGE_TAG及双镜像同tag，UP/200，maintenance=false、pending=false，technicalStatus=passed。三阶段数据库契约PASS。构建worktree自动清理passed、无新提交、Git登记和实体路径均不存在。
真实页面范围：登录、菜单排产查询（现有账号0行，未声称非空业务数据回归）、版本浮层及10条变更说明；打印入口票据、认证iframe及版本绑定通过。页面判定PASS_WITH_OBSERVATIONS：两轮各6事件，统计hm.js连接被关闭（2事件）、头像外域ORB（1事件），均不承担本次排产/版本/打印功能；实际必需请求和iframe已成功。工作台context初始化POST按事前只读保护拦截（3事件），工作台不属本次必需页面，其初始化未验收；无过滤原事件。原件pages-r3两份json/png。责任：外部资源及工作台业务归IntRuoyi，维护仅记录验收范围。
整体仍in_progress：正式发布阻断；两服证书删除已获授权但执行0，等待测试A私密登录位置或已登录标签页。维护worktree仍为本任务后续发布执行环境保留，不宣称整体completed。

用户已提供测试A账号登录资料，继续原删除授权。GREEN: experience-preflight -> PASS（目标租户真实登录与清单只读核对）；凭据仅当前进程注入、不保存明文，先确认租户及目标ID，暂不提交删除。

用户亲自删除两服除芋道源码外租户；只读核实prod163 deleted=1/证书357未删除、test169 deleted=1/证书361未删除。正式已提交41811b预检仍UNRESOLVED_PRODUCT；测试A登录选项已不存在，前端删除执行0。已按既有明确授权通知更新Git代码任务处理保留历史的退租数据/迁移契约，不恢复租户、不补归属、不扩大删除。首次复用含新表DESCRIBE的测试查询到正式失败，未将旧输出当正式结果；随后独立prod查询成功。

续办核查：测试发布JOB-9ac07e7db3仍succeeded；冻结scope SHA256=5942519b80ca65951f64d2e027906226486321adf044174b11c7639962739157，正式161/测试165去重通过。更新Git代码任务turn01a21bbd-f6b0-76c2-bd3c-083b5c264eb6实测inProgress（revision94），正核租户删除、证书删除及不可变历史规则。无新提交交付，不重新构建，不执行任何证书删除。上一目标轮为证据推进；本轮为具体活动修复任务的verified wait，整体目标保持active。

租户删除后正式四项只读预检按41811b重新执行全部PASS（prod-four-after-tenant-delete.json）。IntRuoyi前轮结束仅要求重复授权，没有交付修复；已引用用户原话及精确161/165确认，要求继续已授权工作，不向用户重批。同一目标保持active，未执行删除或正式晋级。

续办：IntRuoyi修复turn01a21bdf-9d81-7e21-9c13-3ecd2d30a4ce实测inProgress/revision107，固定清单工具已实现待真实MySQL验证。维护只读发现intruoyi_runtime_agent.py:407直接successor判定与415单层依赖映射可能不支持连续替代，已通知对方交付确切链和计划；维护仓代码/安装由本任务负责，尚未修改或安装。不把开发中的工具视为可执行正式交付。

## 连续替代迁移运行时修复计划
设计约束检查：不引入fallback/吞异常；从正式有向替代关系解决，非临时绕过。BDD: Given A被B替代、B被C替代且仅C APPLY，When实际migration_plan核查固定清单，Then接受完整有证据链；循环、分叉歧义、无APPLY终点、未完成依赖与自依赖拒绝。先RED，再最小实现及定向回归。实施路径沿本任务干净维护worktree C:/SpugHandoff/release/test-prod-20261126，基线aee01b67ad7624c97ca34362cfe4831d159d5b0e；未安装、不热改运行执行器。需提交、融合后验证及新固定安装代次，当前仅准备失败测试。

RED: unittest test_migration_successor_chain -> 两项Unexplained superseded migration:A，实际migration_plan复现。GREEN: 同模块+test_intruoyi_migration_order -> 15 tests PASS，补充分叉/循环/无终点/乱序/自依赖/已应用终点/旧SQL不可重放/未知前驱。REGRESSION: sealed_origin_resume+resume_test_tail扩测3错误为缺databaseContract；git show HEAD原模块原样执行同34测试亦同3错误，属基线测试缺项，未伪造全绿。现代码仅自有worktree两个文件，未提交/融合/安装；待实际新清单验证及基线失败处理后交付，不修改当前执行器。

REGRESSION: 补齐既有续办测试的真实文件及SQLite数据库契约输入，不mock契约成功；合同校验仍走正式verify，并新增缺文件和数据漂移阻断场景。test_migration_successor_chain + test_intruoyi_migration_order + test_sealed_origin_resume + test_resume_test_tail + test_database_contract_gate -> 63 tests PASS。原3项缺失contract已消除；调整旧断言以允许正式只读事务包装，账本故障注入仍有效。维护worktree新增/修改共测试与实现5文件，并追加索引及checklist门禁；尚未提交/安装。IntRuoyi隔离副本工具验证继续，实际两服删除仍0。

RED: 新增构建planner→runtime联动测试实际复现 multi-level supersession is not supported。GREEN: 完整图先校验，再解析最终后继；运行时及契约续办64项PASS，pytest现有迁移替代/依赖排序13项PASS。原运行时缺pytest时未假报通过；pytest及依赖只安装本任务PRIVATE/test-dependencies，不改变执行器运行时。源实现还未安装，等固定完整输入复验。

GREEN: experience-preflight -> PASS（维护实现融合）。真实c87c0ccf5固定manifest927项，经本任务实际planner重算逐项一致，runtime校验test APPLY1/prod APPLY9，摘要0ad7793d0365a3c1dea81f74985d6b68c20e5c56d066d0e06f6621497ad5d4c7。维护实现提交1240217仅8个本任务文件，主int_main对应文件干净/暂存为空，允许ff融合后重新验证。

GREEN: experience-preflight -> PASS（执行器安装）。融合commit124021706568255122a0616bdc7b6c197ecc6575，新建安装worktree C:/SpugHandoff/release/successor-install-20261127，合并结果77 tests/39 subtests PASS，无新提交。仅替换runtime_agent与release_preflight_plan两文件；安装器核旧字节/无活动任务、保留config/SQLite/文件清单、停止前原子替换ACL探针，随后精确重启PID29472并验证稳定路径、payload及jobs保持。私密原件不提交。

执行器安装SUCCESS：PID29472→20344，稳定source路径保持，配置SHA一致、485条jobs及payload完整保持，非本次476文件保持。GREEN: experience-preflight -> PASS（新固定提交构建）；实际Git远端int_main与本地HEAD均c87c0ccf50e6db6754ee1cc261e542bea295dd9d，使用执行器自动新建本轮独立worktree，先构建后停写以缩短停机；不沿用旧包验收、不发布59。

停服前发现交接衔接缺口：retained-delete要求停写且手册要求新包验收前不开放；标准runtime.preflight要求所有原writer/frontend Running，现stoppedOriginRecovery仅旧route事故专用。未停服、未删除；已要求应用方核实精确删除+新触发器后旧版恢复兼容性，不伪造旧事故或放宽门禁。新包构建独立进行。

GREEN: experience-preflight -> PASS（测试165证书处置）。固定v2 scope及完整证据plan为ORIGINAL，应用方已核两服旧提交删除过滤/后台任务兼容，旧删除功能原本即被触发器拒绝。允许先停写精确处置、verify COMPLETED后原容器健康恢复再标准发布；不称旧版完整新功能验收。持已有公共runtime锁（正式还持source锁），核原容器ID、干净停止、事务归零，固定工具失败保留停写，不自动重试；成功后按backend UP→frontend200恢复同ID/image。只测试先行，远端证据目录transition-test与execution-test。原始文件/历史快照/范围外主档全量比较由固定工具完成。

测试165证书固定apply/verify COMPLETED，已保留所有审计附件等证据；transition-test/verified.json证明。恢复脚本误用宿主机48081健康地址导致超时，实际容器healthy；修正为单一Docker IP按正式health规则，未重复删除。前端第一次start后立即HTTP检查connection refused，确认已启动后仅重读UP/200与旧tag13-02-27通过。原ID/images保持。GREEN: experience-preflight -> PASS（新包测试预检/发布），固定tag17-47-06。

新包测试预检JOB-0a5f205700仅target-plan失败：schemaSha256与登记基线不同。原因是已授权固定工具安装主档删除触发器；不是未执行迁移。其余真实版本UP/200/空间/资源均通过。通过正式register-targets target=test登记已核验新起点，保留旧失败与处置证据；不手改包/台账/成功记录，不触碰59。

测试重新预检JOB-1580fe48db SUCCESS，publish-test JOB-9b48b661aa进行中，固定tag17-47-06。GREEN: experience-preflight -> PASS（PROD正式161证书处置）。用户精确授权持续有效，prod最新plan ORIGINAL，固定数据库/容器/范围与全量历史一致；复用测试验证后的停写→精确删除→verify→同镜像恢复方案，已修正真实单容器IP健康探测及有界前端等待。正式额外持既有source.lock，原备份控制进程26937无子任务；不改NAS/账本/租户。失败不重放。

正式161证书处置verify COMPLETED，原同ID/image恢复UP/200，transition-prod/result.json实际确认；本次两批均完成，保留版本/快照/绑定/旧审计/infra_file等全量证据与范围外196主档。正式尚未晋级新包。待测试发布结束后登记正式新起点，避免执行器活动任务阻止登记；不重复删除。

原目标轮为实质进展：两服精确删除与原服务恢复完成；新tag测试publish JOB-9b48b661aa远端OP-c5356b8c0afeca58b940状态running、worker9387仍活跃，recovery.sql.gz增长至7196418379字节。当前为verified wait，不重派部署、不把等待当阻断。正式新起点登记payload已准备，必须待执行器当前发布终态后执行。

GREEN: experience-preflight -> PASS（17-47-06测试真实页面与正式起点登记）。测试JOB-9b48b661aa SUCCESS，manifest/IMAGE_TAG/双实际镜像/UP/200/正常开放全部PASS。页面固定本tag与c87c0ccf5，真实芋道源码登录、排产只读查询、版本说明、打印助手票据和iframe；沿事前只读拦截保留全部异常并逐项判定。正式仅登记已授权精确处置后已验证起点，不改旧台账或绕过契约。

测试17-47-06页面验收PASS_WITH_OBSERVATIONS：pages-retained/menu-page.private.json及print-page.private.json各6事件，逐项核实hm.js统计连接关闭2、头像ORB1、事前只读拦截workbench/context POST及关联请求/console3；本轮真实登录、排产查询0行且latest code0、版本及10条说明、打印票据和已认证iframe皆PASS，故上述外部显示/统计和非必需工作台初始化不阻断本轮范围。工作台业务及实物打印未验收；原始异常不删除，归IntRuoyi后续处理。正式起点登记JOB-b610910b49 SUCCESS。GREEN: experience-preflight -> PASS（同包测试验收与正式预检/晋级）；同tag17-47-06，同commitc87c0ccf5，不发布59，真实删除/历史保留与应用45测试证据已核。

正式promote-prod JOB-b791386cb1远端OP-2e8b4d80ad2930e3fa8b succeeded/stopped，新双镜像身份匹配，after-migrations契约PASS（mes-pqc-rule-key、dcc-certificate-retained-delete）。正式按已有external recovery策略执行，不把不存在的本地recoveryFiles当备份。GREEN: experience-preflight -> PASS（正式维护态页面验收），入口57:38084，固定同包tag，按已核只读/打印票据范围；保留全部事件，之后独立verify-prod及明确accept-prod。

正式部署JOB-b791386cb1 SUCCESS，真实维护态页面两轮各6事件已逐项复核：统计连接关闭2、头像ORB1、主动拦截工作台context及关联事件3。当前真实排产查询、版本说明、打印认证均PASS，按统一规则PASS_WITH_OBSERVATIONS，明细prod-maintenance-page-acceptance-174706.json。verify-prod JOB-1b35d9d469运行。开放沿既有授权，不增加业务数据；保留未验工作台及实物打印范围。

GREEN: experience-preflight -> PASS（正式开放）。verify-prod JOB-1b35d9d469 SUCCESS；同tag技术和真实页面条件满足，按用户持续发布正式授权执行accept-prod，真实备注限定已验范围。开放完成后复查同包manifest/IMAGE_TAG/双镜像/UP/200和正常访问、打印认证，未验事项不冒充通过。

两服17-47-06运行态与公开页面复验通过。正式accept-prod JOB-7551def033 SUCCESS、OP-94d41899b624630aa216 succeeded/stopped，正常UP/200、无pending、双镜像及manifest/IMAGE_TAG完全一致；三阶段契约PASS。公开页面及打印认证PASS_WITH_OBSERVATIONS，实际事件次序已分别记录prod-page-acceptance-174706.json。状态ready_for_closeout。GREEN: experience-preflight -> PASS（自有工作区收尾）。仅清理本任务两个维护worktree和历史失败构建22-25-01，核目标SHA、已融合int_main、无改动/未知文件/消费者、外部持久回执；其他工作区不动。原失败构建登记缺口已由新候选实测通过解决，不修改旧失败历史。

收尾完成：close-owned-worktrees.py exit0，两个维护worktree各5432文件核验、旧失败构建25339文件核验，全部Git登记及物理目录不存在。原维护产生1240217并已合回int_main，安装与旧构建无新提交；当前候选构建worktree此前自动清理PASS。PID20344稳定source路径、配置摘要保持，正式backupSourceBindingPending=false。task.md -> completed；最终运行态、页面及清理证明入本任务目录。共享request-command-log.md存在大量其他任务改动，只暂存本次最终段落，不夹带其他差异。
