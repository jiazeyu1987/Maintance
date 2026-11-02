# 执行记录

- 用户授权修改发布后旧包/旧恢复载荷自动清理；已先建任务文档。前序说明任务completed，无遗留执行进程。
- Bootstrap读取适用规则和经验索引；绝对路径Join-Path首读报路径格式错误，随后按绝对路径成功读取powershell-memory，未发生写入或外部动作。后续路径先判断绝对/相对，避免包装错误。
# BDD 与实现工作副本

- 工作副本：`C:/Users/D01021/.codex/worktrees/spug-post-release-cleanup/Maintance`；分支 `codex/post-release-auto-cleanup-20261102`。
- 基线：8797d66（配套完整发布/补丁/手动清理代码）与当前 int_main c470b9a 在独立副本正常合并，无冲突。没有覆盖主工作区脏改动；运行副本仍含独立修复，后续仅同步本任务定向改动。
- BDD: Given 同一完整包或前端补丁已完成三服最终验收，When 收尾，Then 自动清理已知失效旧载荷，保留当前包及本次恢复点、清单与历史。
- BDD: Given 发布失败、仅部署未验收、未完成三服、存在活动/未解决任务或演练引用，When 收尾，Then 不触发清理或保护对应版本。
- BDD: Given 已登记的旧包与恢复记录，When 清理，Then 逐普通文件复核身份和SHA，保留凭据、记录、当前恢复点及未知资料；不删除NAS、数据卷或容器。
- BDD: Given 部分删除后遇到摘要/磁盘错误，When 清理停止，Then 清理单独标记失败并保留已删清单，发布成功状态不被篡改，后续可从真实剩余文件继续。
- RED: `python -X utf8 -m unittest test_post_release_cleanup -q` -> FAIL，预期缺少 post_release_cleanup 模块。
- GREEN: experience-preflight -> PASS（本地临时普通文件删除测试；没有三服写入、发布或业务E2E）。

- REGRESSION: 已对齐8797d66与6e36019配套分支，文档并集及UI直发流程/现场版本参数冲突已审阅解决。569项Python测试通过（2项已有skip），Windows服务专用模块因普通脚本运行环境无pywin32明确排除；未伪装服务测试通过。Node远端UI合同通过。
- Linux真实测试：8项PASS（7项真实临时文件删除、安全保留与失败记录，加1项真实多进程flock；重试子目录和规范暂存根共锁）。Linux容器无psutil，控制器全套测试在Windows实际依赖环境执行，不以Linux缺依赖失败充当成功。
- 载体错误记录：早期两次命令工作目录重复前缀/错误测试模块名导致非业务失败，已更正实际路径与模块；未修改产品以适应错误载体。
- GREEN: experience-preflight -> PASS，允许在0活动发布任务时备份7个代码文件并定向更新本机普通脚本执行器。保留配置SHA与SQLite逻辑状态完整一致、所有历史/包绑定和三服状态不写入；不安装服务、不做真实三服发布或删除测试。

- GREEN: 最终源码定向184项PASS，匹配现有运行器的候选副本同样184项PASS。已在0运行任务时停止唯一已核身份的18112普通Python、备份代码、精确更新7个文件并由原稳定start-local.ps1隐藏启动；没有服务安装。
- GREEN: apply-runtime-update.py verify -> PASS，Spug18081 HTTP200，18112认证state正常；私密配置和SQLite逻辑SHA不变，271任务/28完整包/1补丁。未调用三服，不把本地测试称作真实三服清理验收。
- Current Status: ready_for_closeout；后续只剩实现提交、int_main融合复验、独立worktree收口与最终记录提交。

- GREEN: int_main 已快进融合bd88c22554e54fae44bc6e8982cb2ea97e3eb6c2；在融合结果执行定向184项PASS及Node页面合同PASS。实现提交只含本任务18个文件；已提交的历史配套分支通过独立合并引入，没有提交本机原有脏文件。
- 保留既有改动：3个共享文档原修改以并集恢复；73个原未跟踪历史资料恢复原字节（CRLF差异继续作为本地状态保留，其中push-maintenance.json与入站内容不同也保留原字节）。既有AGENTS、应用配置、启动脚本和其他任务内容未被重置。私有原件与SHA证据在main-preservation，未上传。
- GREEN: experience-preflight -> PASS，待最终回归结束后只归档本任务独立worktree；HEAD已被int_main包含，工作副本无改动，无运行控制台引用该路径；其他worktree/进程不清理。构建命令：无（本任务不构建业务发布包）。验证命令见上；产生新提交：是，bd88c22及基线整合；已合回int_main：是。

- REGRESSION FINAL: 最终提交内容全量Python 569项PASS、2项既有skip；耗时145.633s。
- CLOSEOUT: archive_worktree -> REFUSED (primary checkout cannot be removed)；attach原主工作区 -> REFUSED (not a managed worktree)。开发worktree干净、HEAD已包含在int_main；不强制删除当前会话主检出，ready_for_closeout保留。没有自动审批拒绝或新的远端执行。
# 后续核查：四类操作的资料保留范围

- 用户询问当前三服发布、前端补丁、备份、恢复是否仍留下旧包/旧恢复资料。沿用本任务只读核查，不触发发布、备份、恢复或删除，不扩大自动清理范围。
- 前序收尾限制保持：应用拒绝归档当前主检出，任务仍ready_for_closeout；本轮先核本机实际代码，再按四类流程说明覆盖边界。
- 验证计划：检查活跃代码的最终验收触发、保护集合、恢复/独立备份入口与保留策略；无需远端连接或真实E2E。
- 核查结果：自动清理eligible仅accept-backup与frontend-patch-accept(backup)，且当前包stage=completed；备份/恢复不是触发入口。清理只覆盖登记暂存目录的release.tar/images.tar及归属完整的旧recovery.sql[.gz]/recovery-volume-*.tar，保留当前包和本次恢复点、镜像、旧容器、清单、历史、凭据、未知资料和引用中的资料。
- 独立备份保留：repository_retention按retainNewestPoints/minValidFullPoints/retentionSeconds/legalHold及完整依赖链规划，RETENTION_PLAN与RETENTION_EXECUTE是独立动作，不随本次发布清理自动执行。恢复保留原归档、失败资料、retainedData和容器证据，未纳入本轮自动清理。不能声称四类操作全部无旧资料积累。
- Evidence：活跃post_release_cleanup.py eligible/perform；活跃artifact_files.py inventory/automatic_cleanup；活跃intruoyi_recovery_agent.py retainedData/retained容器；ops/recovery/repository_retention.py:142与repository_cli.py RETENTION_PLAN/RETENTION_EXECUTE。只读本机代码，无服务器连接、备份、恢复、删除或运行状态修改；结论是机制核查，不是实时三服库存核验。

# 后续核查：四类产物的产生入口

- 用户要求检查旧镜像、旧容器、旧包及旧恢复资料分别由哪些操作产生；先写 artifact-origins.md，沿用本任务和当前目录收尾限制。
- 只读核对活跃执行器的 stage/deploy/replace/reopen/capture/recover/rollback/patch/rehearsal，以及维护仓独立备份、恢复、构建与 retention 调用；无私密配置读取、无远端连接或删除。
- VERIFY: 完整发布保留原前后端与维护后端容器；补丁保留原前端；发布失败恢复保留失败数据库、数据目录及容器；历史隔离演练产生独立容器/数据卷/种子副本。新镜像导入和新版本包跨轮保留后成为旧资料；失败/中断及新部署尝试可能留副本，但 resume 不应概括为必然全量重造。
- VERIFY: 独立备份入口和恢复入口不同，不能把配置快照称为全量数据备份。旧计划备份另有 retention 调用；本轮自动清理不接管它。完整来源矩阵及行号见 artifact-origins.md。
- 本轮仅文档核查，无行为改动、不需要 TDD/E2E，也未执行发布、备份、恢复或清理；主任务仍 ready_for_closeout。

# 扩展实现：旧容器、镜像及已核销恢复现场

- 用户同意优化方案；沿用当前独立 worktree，快进到1f1df8a，主目录扩展任务记录同步到本工作副本。无业务包构建或业务发布。
- GREEN: experience-preflight -> PASS。已读发布/备份恢复、服务器访问、worktree与UTF-8经验；本地Docker Linux引擎可用，使用任务独有资源验证，不停止现有业务容器；共享NAS、独立备份、在用卷、未核销任务保持保护。
- BDD: 成功发布收尾 -> Given当前/恢复版本与精确原容器快照，When三服最终验收成功，Then先删更早且已停止、身份不变的业务容器，再删无任何容器引用的登记镜像标签，保留当前及最近恢复点。
- BDD: 未核销与漂移保护 -> Given未知容器/运行中/配置漂移/当前检查点引用/恢复未验收，When生成清单，Then保留并显示原因，不能用名字或年龄替代归属。
- BDD: 已核销恢复 -> Given远端opened回执及本机accepted与原任务restored核销一致，When该旧版本不再受保护，Then允许精确回收失败数据库和已退役数据副本；保留回执和原历史。
- BDD: 中断重试 -> Given精确计划与逐对象pending回执，When执行中断或删除失败，Then发布成功不被改写，清理失败可见且重试重新采样，不删除当前/未知对象。
- RED -> GREEN: 缺少 runtime_resource_cleanup 模块、镜像删除函数、独立清理重试入口及两个页面报告函数的失败测试分别复现后实现；续接恢复 openingJobId 与未来版本保护新增失败测试后修复。测试载体首次使用 MagicMock 未导入的 NameError 已更正为 Mock，再取得真实预期 KeyError；不以载体错误充当产品 RED。
- GREEN: 本机真实 Docker 集成1项PASS：任务自有已停止容器、登记镜像和旧包按顺序删除，当前容器和恢复点保持，重复执行幂等；finally只清理本任务资源。原 `docker inspect --size` 扫描全部容器会超时，改为身份检查并以磁盘可用变化呈现空间，不扫描业务可写层。
- REGRESSION: 全量586项通过，4项skip（Linux专用2项、真实Docker显式开关1项、既有1项）；Windows服务专用模块明确排除，普通脚本不安装服务。Linux容器13项通过，包含真实跨进程锁；源代码Node页面合同通过。真实Docker测试另已显式执行通过。候选运行副本172项通过。
- 运行同步预检：0活动任务，271任务/28完整包/1补丁；计划7个文件，私密配置和SQLite已离线一致备份。逐Git差异应用在候选副本时因活跃运行源与Git配套版本不同而拒绝，未触碰活跃代码；改为逐修改块精确原文匹配、唯一锚点及特定旧补丁事件入口适配，保留运行源既有修复，不引入无关功能。
- REGRESSION FINAL: 最终587项PASS（4项明确skip）；Node两组合同PASS；Linux14项PASS；显式本机真实Docker1项PASS（62.190s）；匹配活跃运行源的候选173项PASS。未来版本保护测试先FAIL后PASS，防止仅按登记资源误将更晚版本作为旧资源。
- GREEN: experience-preflight -> PASS（本机执行器定向同步）。0活动任务、精确PID/启动路径和私密配置SHA/SQLite逻辑SHA已核，7个候选文件SHA已冻结；仅停止本任务核实的稳定普通脚本执行器，安装后由原稳定入口隐藏启动，不安装Windows服务，不调用三服业务发布/删除，保留所有其他任务进程。随后真实Playwright登录只读验证页面，不点击发布/恢复/清理。
