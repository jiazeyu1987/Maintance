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

# 后续核查：前端补丁发布逻辑

- 用户询问前端补丁发布逻辑；先写 frontend-patch-flow.md，只读核对现用 frontend_patch_build/frontend_patch/frontend_patch_agent 与最终清理触发。
- VERIFY: 一次完整前端镜像构建，已提交源码只允许前端目录变化；基础主版本及后端镜像绑定；同一包逐服 deploy/accept，测试验收后正式、正式验收后备份。
- VERIFY: 只停止/替换前端，保留原容器；后端/数据库身份保持，未执行迁移；自动技术检查不包含真实 Playwright 登录或业务回归；失败采用显式 restore，不在异常分支自动恢复。
- 活跃副本缺少 frontend_patch_baseline.py，而仓库有现场基线登记扩展，本次据现用副本说明，不将仓库能力冒称已运行。未触发构建/登录/远端动作，未触碰 task.md 现有其他扩展记录。详细证据见 frontend-patch-flow.md。

# 后续核查：后端补丁可行性

- 用户询问“可以做后端补丁包吗”；只读核现用执行器与维护仓，未发现后端补丁动作。现有前端补丁限定 frontend 镜像并绑定后端 ID，不能直接承载后端镜像。
- 结论：可以建设兼容当前前端/数据库/配置的后端代码专用补丁；建议一次构建完整后端 JAR/镜像，同包逐服部署验收、保留原程序显式恢复，GxP 保持关闭。数据库/菜单/权限/配置迁移或不兼容数据/API变更仍用完整发布。程序回退不等于撤销业务数据。
- 需同步组合版本、前后端补丁互相绑定、完整包接续、任务/UI及清理保护；未将此方案声称为已实现能力。详见 backend-patch-feasibility.md。本轮没有行为修改、远端动作或构建测试。

# 后续核查：仅投递 JAR

- 用户询问能否只替换一个 JAR；现用构建确认为 `/yudao-server/app.jar` 及 java -jar 启动，可以建设 JAR-only 发布。后端镜像并非每次投递的必需制品。
- 建议固定运行镜像、版本目录 JAR 及清单、SHA/实际挂载和运行身份验证，保留原容器显式恢复，同一 JAR 逐服验收；不直接覆盖旧进程正在使用的文件，不以镜像 tag 冒充挂载 JAR 版本。仍为完整后端 JAR，需兼容数据库/配置/前端/Java及业务数据。
- 详见 jar-only-feasibility.md。仅本机只读代码核查及文档，无行为修改、构建或远端动作，现用执行器尚未实现 JAR-only。
