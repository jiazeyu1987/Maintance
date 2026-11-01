# 执行记录

- 2026-11-01 用户明确授权修复并发布，要求三服程序版本与数据库表一致。已创建任务文档，前序发布和差异诊断已completed。
- 设计：不修改两份已执行历史SQL，改用新增前向迁移补齐生产结构；具体DDL与一致性检查以真实元数据及现有发布契约为依据。开始阶段仅本地读取与远端只读。
- GREEN: experience-preflight -> PASS（专属worktree创建）。源码int_main=3f8e28a3、clean；从上一已发布目标56b96ea新建C:/SpugHandoff/schema-src-20261101。维护仓主检出b4feadc、clean；从已安装5c2bf68新建C:/SpugHandoff/schema-ops-20261101。分支均为codex/three-server-schema-20261101；不启动worktree控制台，不改槽位或8081端口；已发现其他guards-20261101工作副本，非本任务，不修改或清理。

- 实际结构基线schema-before.json：885/882/882，差异仅为3张治理表；其余882张表的列、索引、约束、外键及检查条件一致。
- BDD: 跨环境前向迁移 -> Given 测试已存在治理表而正式/备份缺表；When 新不可变迁移应用；Then 三服结构一致，已有行保留，旧迁移字节不变。
- RED: verify-schema-contracts.py red -> 旧代码未提供三服迁移；正式目标未强制使用同包测试结构，错误结构仍被接收。source-red.log、executor-red.log记录预期失败。
- GREEN: verify-schema-contracts.py green -> 源码2项、执行器96项通过。新增20261101迁移及清单注册，正式/备份部署前携带上游已验收结构，部署回执及开放验收再次强制一致。
- GREEN: experience-preflight -> PASS（任务独有本机MySQL迁移验证）。仅本机隔离容器，无网络、无真实业务行；使用真实远端元数据比较、新建合成标记行验证保留；不访问远端或修改业务数据。
- 首次真实MySQL测试失败原因已查实：测试载体strip()误删最后一行空字段的制表符。diagnose-mysql-check.py保留字段后与远端基线完全一致，mysql-first-failure-diagnosis.json记录差异为空；修正为只去除换行，不修改DDL或期望值。清理已核身份的本任务失败容器后重跑，保留首次失败证据。

- GREEN: verify-real-mysql-migration.py -> PASS，三份本机独立库重复执行一致，既有合成行保留，任务容器已移除。远端无写入。
- REGRESSION: verify-regressions.py -> PASS，529项/0失败/0错误，2项Linux专用skip；已快进整合并发防复发任务提交673395d，不修改其任务或worktree。
- 源码提交首次被WindowsApps的python别名及缺少worktree运行槽位依次阻止；改用已安装Python的进程PATH并调用正式reserve-worktree-slot登记slot3，菜单/端口钩子实际通过。未跳过钩子。保留release-sources.json已有CRLF，diff --check使用cr-at-eol识别既有换行，不整体改编码或旧SQL字节。
- 实现提交：源码fb88105af40e4ee6366a20dae2df721f1de2dcb0；维护15b2f5cc0288e045444fdea66a5083e00db55284。未合入或推送int_main。
- GREEN: install-committed-schema.py -> PASS，原包656项/工作包677项全校验，稳定运行文件与提交一致；历史260任务/27包、私密配置原字节不变；普通执行器12204，未装服务。详见local-install-verification.json。
- GREEN: experience-preflight -> PASS（Spug真实登录、预检和单包构建）。本轮用户已授权三服修复发布，源电脑无后续发布且执行器停止；原包校验/提交输入/工作包校验/运行身份/必要测试通过。通过真实Spug UI选择fb88105a；先前置检查真实GxP关闭和目标状态，再构建；取消演练、正式独立恢复边界不变，不清理未知资料。

- GREEN: experience-preflight -> PASS（已提交三服结构一致性配套安装）。原资源包656项、工作包既有项完整校验PASS；执行器唯一空闲且无子进程，SQLite backup及私密配置/被替换文件保护备份完成。只同步提交15b2f5c的结构校验代码及说明，私密配置原字节不变；原包、原封包、凭据和历史保留，不访问服务器。

- GREEN: Spug check-prerequisites JOB-dd1e3c919b -> succeeded（13:00:21—13:05:45）；三服SSH/健康/磁盘/恢复配置/启动与验收入口均通过。测试约89.35GiB、审查约41.74GiB可用；沿用已批准阶段阈值，无扩容或清理。
- GREEN: 真实Playwright本机配置页 -> PASS；保存/运行均DEVELOPMENT_DISABLED，auditEnabled=false，无待重启，未保存配置或写业务行。
- Spug真实UI构建JOB-161cebeade，候选tag=2026-11-01-13-08-35，源码fb88105af40e4ee6366a20dae2df721f1de2dcb0；构建器创建独立冻结worktree，后续三服只使用该tag原包。

- 冻结构建worktree=C:/SpugHandoff/release/build/2026-11-01-13-08-35，提交fb88105a；migration-readiness实际三服均passed，APPLY仅20261101_dcc_source_governance_all_environments，静态检查不冒充完整数据演练。
- GREEN: verify-programmable-schema.py -> PASS，三服触发器同摘要、无存储过程/事件差异。构建期只读检查，没有修改远端对象。
- 构建命令：Spug build-release fb88105a，后端Maven clean package、前端锁文件pnpm install与vite build；实际命令由提交673395d/15b2f5c配套构建器执行，未引入未提交内容。

- 构建JOB-161cebeade于13:51:04在封包后清理失败：正式构建器导入IntRuoyiBackend/script/release/release_migration_manifest.py，生成合法__pycache__，原清理器只识别根scripts目录缓存。包约692.53MiB及实际镜像已验证并封存，未上传/部署；保留失败与原包，修复后经Spug原包重传入口续接。
- BDD: 构建工具缓存清理 -> Given 冻结提交含后端发布Python模块且真实导入生成缓存；When 封包后验证清理；Then 仅识别已跟踪源模块对应且头部有效的缓存，未知或损坏缓存继续拒绝，原包不重新编译。

## 2026-11-01 续接发布清理修复
继续同一任务和同一封存包 2026-11-01-13-08-35；不重新编译，不修改原失败记录。经验门禁沿用 task.md：仅本任务 worktree、已提交输入、未知文件保留、原包校验后重传、真实 UI 执行、三服同版本同结构、GxP 关闭。
RED: test_real_tracked_backend_release_module_bytecode_can_be_cleaned -> FAIL，真实 Git 工作副本中官方后端发布模块生成的有效 pyc 被错误归类为未知文件；接下来只扩展已跟踪脚本源文件的缓存识别范围。

GREEN/REGRESSION: verify-regressions.py -> PASS，531 tests，0 failures/errors，2 Linux-only skip，71.403s。实际 Git/py_compile 验证合法缓存可清理、损坏缓存及无已提交源文件缓存继续拒绝。

- GREEN: experience-preflight -> PASS（已提交构建缓存清理配套安装）。原资源包656项、工作包既有项完整校验PASS；执行器唯一空闲且无子进程，SQLite backup及私密配置/被替换文件保护备份完成。只同步提交43e4d3e的安全清理代码及测试，私密配置原字节不变；原包、原封包、凭据和历史保留，不访问服务器。

GREEN: install-committed-cleanup.py -> PASS；43e4d3e，原包656项/工作包678项校验通过，262任务27包和私密配置原样保留，普通执行器PID14328。
GREEN: experience-preflight -> PASS（Spug原包重传）。原构建JOB-161cebeade已封存且无部署效果，源提交fb88105a和tag固定，清理修复531项回归通过且已安装。仅通过真实UI选择retry，校验原包并重传，不重新编译、不改失败历史。

原包重传JOB-7fbe1f7c1a于14:19:07失败：Git worktree remove超过180秒；保留失败。随后只读确认本次构建目录已物理删除、Git登记不存在、执行器无子进程；原任务保存ownershipVerified=true及fb88105a身份。不是源码/封包校验失败，不修改摘要。
GREEN: experience-preflight -> PASS（原包重传续接）。现有正式清理器支持已核验目录删除后未写成功回执的续接，531项中已有相应真实测试；本次目录/登记均不存在且所有权证据完整，仅通过Spug retry再次校验同一原包并续传，保留前两次失败记录。

GREEN: 原包重传JOB-c5f0567982 -> succeeded，14:22:34；保留原构建及首次重传失败历史。verify-sealed-package.py -> PASS，1094成员逐项校验，本地/NAS摘要一致，726169600 bytes，packageSha256=00048a4d6ca73fb03eaec01ada6a159ffaa38af97fc689828190126f8b85706e；构建工作副本已删除且登记不存在，未重新编译。
GREEN: experience-preflight -> PASS（测试58发布）。单包2026-11-01-13-08-35已封存且NAS校验通过；只含新增前向建表迁移，531项本地回归/真实MySQL验证/三服前置检查通过，恢复检查点策略与GxP关闭契约不变。通过真实Spug UI publish-test，保留测试业务数据、旧历史及旧演练，不执行正式数据演练。

GREEN: publish-test JOB-e2e390d13f -> succeeded（14:25:10—14:55:13）；远端OP-efb027657c93fff2186f succeeded，原worker退出，完整恢复检查点保留。verify-deployed-phase.py test open及真实GxP页面核验PASS，tag/实际镜像/healthUP/HTTP200/维护关闭一致，保存与运行GxP均DEVELOPMENT_DISABLED，无待重启。
GREEN: experience-preflight -> PASS（测试通过登记）。同包测试升级、迁移与真实登录及GxP均通过，Spug mark-tested再次核验并登记；范围为只读验收，未称完整业务写入回归。

GREEN: mark-tested JOB-4c099c442b -> succeeded（14:57:34—15:00:13），同包stage=tested。
GREEN: experience-preflight -> PASS（正式57晋级）。同包测试部署、真实登录、GxP关闭及mark-tested成功；固定tag=2026-11-01-13-08-35，已提交迁移仅新增3表，升级后强制匹配测试已验schema。沿用用户指定正式独立恢复机制，不重复正式全量检查点，不恢复演练，不改业务行；通过真实Spug UI promote-prod。

正式晋级真实UI已提交JOB-e722d26eb3，15:11:59启动；当前完成原版本核对并准备同一原包，未创建额外全量演练。

GREEN: promote-prod JOB-e722d26eb3 -> succeeded（15:11:59—15:21:12）；远端OP-29df6604606c6207a6e7 succeeded，worker终结，独立恢复责任确认存在且无重复Spug检查点。正式运行结构摘要dc1b23de与测试一致，镜像/固定tag/UP/HTTP200通过，真实GxP页面保存和运行均关闭，无待重启。
GREEN: experience-preflight -> PASS（正式只读验收开放）。verify-deployed-phase.py prod、真实Playwright配置页及Spug技术登录通过；仅接受版本、结构、健康和只读页面范围，不宣称新增/审批业务完整回归，不写业务行。通过真实UI accept-prod开放正常入口。

GREEN: accept-prod JOB-5e16a1ffa1 -> succeeded（15:23:14—15:28:54）；正常入口8081重新实际观测及真实登录/GxP页面PASS，维护false、healthUP、HTTP200、同包同镜像同schema，保存和运行GxP关闭。
GREEN: experience-preflight -> PASS（审查59晋级）。同一tag2026-11-01-13-08-35正式已验收开放，固定NAS原包摘要一致；已授权测试/正式/审查三服，审查恢复检查点保留，按实际数据盘和已批准阈值检查空间，不删除历史/旧演练。通过真实Spug UI promote-backup，升级前后绑定正式已验schema，不改业务行。

GREEN: 本地GxP复核 -> PASS（15:33真实Playwright登录，保存和运行DEVELOPMENT_DISABLED、auditEnabled=false、pendingRestart=false）。
审查发布JOB-bcf335a982于15:32:19启动，远端OP-e7f7ba29df2c09789a37于15:36:06执行；15:57只读观测worker存活，数据库6,428,054,553字节、对象9,687,080,960字节归档已落盘，检查点收尾正常，未发生空间错误。

审查恢复记录于16:03确认存在。16:05独立Runtime.observe只读核对：目标tag及前后端image ID已切换正确，schemaSha256=dc1b23dec9664a58329f5b0ae8bdc5ec09822cfc78b3beee335d45ae248930d1与已验测试/正式一致；维护true，HTTP200；后端启动阶段健康尚未就绪，不提前认定完成。

GREEN: 审查远端OP-e7f7ba29df2c09789a37 -> succeeded（16:05:48），原worker已退出，恢复记录存在，无恢复失败。
GREEN: experience-preflight -> PASS（审查真实只读验收）。目标同包同schema、远端升级成功；仅Playwright真实登录既有配置页面，核版本和GxP保存/运行关闭，不新增、保存、审批业务数据。先使用登记的验收入口，正式技术核验通过后才开放正常入口。

GREEN: promote-backup JOB-bcf335a982 -> succeeded（15:32:19—16:07:51）；verify-deployed-phase.py backup及真实Playwright验收入口配置页均PASS，固定tag/实际镜像/完整schema/UP/HTTP200一致，保存与运行GxP均关闭、无待重启，恢复检查点存在。
GREEN: experience-preflight -> PASS（审查只读验收开放）。同包升级及技术核验成功，真实登录和GxP关闭已确认，仅批准范围只读验收，不称完整业务写入回归；通过真实Spug UI accept-backup开放正常入口。

GREEN: collect-schema.py schema-after.json -> PASS；三服test/prod/backup均885表，全部表名、字段、索引、约束和外键元数据相等，differences.prod={}、differences.backup={}。只读采集，不同步业务行。

16:15审查正常运行态只读观察：维护false、目标tag正确、schema一致、backend UP、frontend HTTP200。
GREEN: experience-preflight -> PASS（审查正常入口真实登录复核）。仅登记的正常入口和既有只读配置页，核同一版本及保存/运行GxP关闭，无业务写入。

GREEN: accept-backup JOB-93573fd19a -> succeeded（16:08:59—16:16:15）；正常入口38081真实Playwright登录、GxP保存及运行关闭、无待重启，verify-deployed-phase.py backup open -> PASS。
GREEN: final-release-report.py -> PASS（16:17:54）；单包2026-11-01-13-08-35三服闭环成功，actual镜像/healthUP/HTTP200/真实登录/GxP/完整885表结构及新迁移APPLIED均符合，NAS与本地原包摘要一致。状态ready_for_closeout，开始仅本任务checkout/slot及脱敏记录收尾。

GREEN: experience-preflight -> PASS（本任务checkout收尾）。三服同包/结构/GxP验收通过；精确路径 C:/SpugHandoff/schema-src-20261101、分支、提交 fb88105af40e4ee6366a20dae2df721f1de2dcb0、干净状态及Git登记已核实；ignored只含合法且有已提交源文件的Python缓存，无链接或消费者。用户明确不自动合入int_main，因此保留独立分支，仅删除本次checkout。

GREEN: experience-preflight -> PASS（本任务checkout收尾）。三服同包/结构/GxP验收通过；精确路径 C:/SpugHandoff/schema-ops-20261101、分支、提交 43e4d3eb6b85d4f54749d721ad4ec977102a4747、干净状态及Git登记已核实；ignored只含合法且有已提交源文件的Python缓存，无链接或消费者。用户明确不自动合入int_main，因此保留独立分支，仅删除本次checkout。

GREEN: experience-preflight -> PASS (release owned slot). Exact checkout absent; mutex, contract, branch, slot3, 8084/48084 verified. Preserve all other entries; mark only this task allocation inactive.

GREEN: task-closeout -> PASS；本任务源码及维护checkout均Git退出0并确认路径/登记不存在，独立分支保留，未合入或推送int_main；slot3已释放，其他登记保留。稳定普通执行器PID14328和稳定目录再次确认，执行器无子进程、无活动发布任务。任务completed，单独提交最终脱敏记录。
