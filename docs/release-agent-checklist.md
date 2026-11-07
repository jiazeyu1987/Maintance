# IntRuoyi Codex 发布执行检查清单

## 包清单身份与桥接期限门禁

- Trigger：Spug 包清单、发布桥接 504、身份探测随历史体积增长、迁移执行器更新或新增 `/identity`。
- Preflight check：先固定真实 nginx→bridge→executor 链和精确 PID/进程创建时间/配置摘要，分测身份、正文、目录；从 Git 已提交内容核对运行目录模块原 SHA，保留已运行路由、文件存在性检查、全分支提交选择和 `/state`。不得将展示 repo 当隐式运行根；仅既有 app id/固定 origin 合同强制校验。
- Blocker：原进程不唯一、配置/文件漂移、活动发布或重载会改写未决历史、目录功能不能从干净提交重建、身份缺失/不符、重定向、正文超限或预算耗尽，停止对应安装/请求。源码回归 PASS 不代表真实页面已通过。
- Verification：真实本地 Executor/SQLite/HTTP 证明目录只读 identity+catalog；错误密钥/身份/重定向不转发，旧状态历史保持；慢 header/持续小字节 body 不能重置共享期限，超限和原 HTTP 错误可见。Windows 与独立 network-none Linux 回归均核源 SHA、零 skip、临时容器移除；安装后真实 Spug 登录页面目录 200、原操作终态和历史摘要保持。
- Forbidden action：禁止仅增大 nginx 超时、清历史、回退 `/state` 校验、默默截断响应、跟随重定向携密钥、复制整份私密快照覆盖或按端口盲杀；不得重载无关 18081/数据库/业务服务，操作系统 DNS 等未覆盖阶段不得伪称已强制总期限。
- Evidence：`doc/tasks/20261106-spug-prod-incremental-to-two-targets/catalogue-identity-plan.md`、`catalogue-504-*-timings.json`、`catalogue-identity-regression.json`、`catalogue-identity-linux.json`及安装/实际页面原件；保留原 504。

阶段必查与推荐命令：诊断先读精确容器 `nginx -T`/error log（完整原件仅 PRIVATE），用实际 registry 分解 `/state` 与清单时间。代码阶段运行 `python -X utf8 -B -m unittest test_release_identity test_applications test_package_catalog test_package_presence test_state test_commit_catalog test_current_versions test_database_versions`；测试缺依赖单列环境失败，不当 RED。安装前读取 `state.sqlite3` 的业务 payload/jobs 摘要、活动/启动会改写 job 集合、原 exe/argv/cwd/env 与 supervisor 归属，先从本任务新建的干净已提交 worktree 安装 executor，认证 identity 200 后才安装 bridge；禁止先桥后端或运行时拼接函数。重载只用精确身份的本组件，配置与数据原件不替换。Fail Fast 按上述 Blocker；必须记录源提交/文件 SHA、安装前后 PID/配置 pins、保护进程保持、SQLite 原备份及 payload/jobs 前后相等、实际目录/页面状态和旧错误证据。正文预算分别为身份 4 KiB、普通元数据 16 MiB、状态兼容 128 MiB；常规共享 20 秒，既有数据库检查 60 秒；DNS 使用系统 resolver，必须区分已连接 socket 期限。

## 自动增量链与恢复周期门禁

- Trigger：增量按钮自动选父链、控制重启、全库恢复、日志清理或新增备份周期策略；异步launcher退出2、immutable RUNNING completion与独立owner终态并存，或历史计划扫描导致超时。
- Preflight check：先区分同步终态与异步等待回执；异步FULL/INCREMENTAL必须核同一request/intent/selection/completion、launcher实际exit2且timedOut=false、固定operationDirectory/resultRef、owner request/start/config、最终SUCCEEDED或FAILED_RETAINED以及对应worker已停止。FAILED必须核非空失败码、最后child原pin/operation/pid/终态与实际退出；其actualExitCode可为0，表示捕获child成功但归档后续失败，不能要求exit1或解释为owner成功。明确取消的None退出须绑定原SIGTERM intent/observation；捕获前失败无child也不伪造退出码。FAILED仅证明终止，后续来源实际健康、epoch及物理锁准入仍必需。再核同来源不可变原生成功结果/退出/point/manifest/capture父链、最新唯一全量根及唯一完整链尾；冻结内容中的sourceRestored=false须核同操作成功捕获结果、原内容摘要与固定source-restoration成功回执及时间顺序，不把冻结时状态当最终恢复结果。实际容器身份/UUID、日志保留及位置连续性；持久未决任务与同一物理源锁。计划摘要绑定稳定配置/点/周期，不绑定不断前进的实时日志末尾。
- Blocker：缺或失效基线明确要求新FULL；异步等待回执/owner身份或路径错配、原worker仍在同operation-root运行、缺终态或TERMINAL_UNKNOWN，均不能快判空闲。分叉、损坏、配置/身份/权限/连接错误、未决任务与未知提交阻断。不能将未知结果标成未受理；只有持锁确认未发布该ID预约的错误才返回精确accepted=false证明。
- Verification：BDD/RED/GREEN分别覆盖真实异步launcher/worker及15项成功/失败历史闭合、错误PID/等待回执/owner绑定、存活worker和详细原编号仍核大原件；连续两次增量、过期计划、同编号/同源并发、重启原件、恢复epoch、日志purge/缺段、成功收据后崩溃收口；真实Linux锁/进程/存储失败、真实HTTP、UI、实际双包构造与完整代理预算。启用epoch须覆盖已登记socket链接、未登记/漂移/数据卷别名与bind/nested mount物理重叠。最终真实Spug登录执行并核原生终态与父子点。
- Forbidden action：不把异步exit2当最终失败或将RUNNING completion重写成功，不只信UI/query状态放行，不重hash全部退休历史或只增加预算掩盖真实异步合同缺口，不跳过当前代完整性/来源健康；不按浏览器历史时间猜父点，不自动补发未知POST，不把全量记成增量，不追认旧点epoch，不修改旧target或放宽旧失败clearance比较，不忽略丢失日志或删除raw/gzip载荷绕过旧合同。
- Evidence：`doc/tasks/20261106-spug-prod-incremental-to-two-targets/automatic-incremental-plan.md`、`backup-epoch-plan.md`、`incremental-resilience-review.md`、automatic-plan-timeout-closure.json、automatic-async-originals.json、automatic-async-plan-fourth.json及实际Linux/HTTP/封包及安装验收回执。

阶段必查与推荐命令：先运行test_automatic_incremental_async_closure、test_automatic_incremental_plan、test_backup_epoch、test_automatic_incremental_resilience和test_backup_variants；Spug的test_automatic_incremental_entry/http/proxy及UI真实状态测试一起运行。单次计划避免重复哈希已闭合历史的大回读文件；异步调度闭合只读小型原件且结束复核身份，原编号详细GET及当前链完整验证保持。诊断先固定原超时，逐阶段统计实际原件读取/在线查询耗时；真实15项历史必须在原30秒预算内完成，并从同一FULL父点继续，不重做全量或改历史。只读缓存结束复核身份。安装只用新专属干净提交worktree，读取实际新进程配置/文件摘要及认证计划。启用周期时无活动操作、持来源锁显式初始化，原target通过owner顶层targetBackupEpochPolicies保持原字节，旧点先建立新FULL。Fail Fast按上述Blocker；必须记录实际命令/退出/零skip/包pins/唯一操作号/实际类型/父链及原服务、挂载、失败原件保持。

挂载必查：v3已登记非数据保留挂载必须完整匹配mount及实时observe_preserved_mount身份，之后才对canonical路径执行epoch/lock隔离；数据卷、旧合同与未登记别名仍严格拒绝。所有可写挂载及嵌套挂载按实时mountinfo设备和物理路径检查重叠，不跳过docker.sock或只检查词法前缀。缺失/漂移恢复回执、身份漂移或物理重叠立即停止激活；记录原始候选失败、新包只读构造与实际服务健康证明。

## 实际封包构造配置传递门禁

- Trigger：owner 新增运行配置、冻结标准包的 reviewed transforms 变更，或配置存在但实际 runtime 缺失字段。
- Preflight check：分别确定当前源码与冻结基线加 transforms 的交付路径；两个实际封包均在独立进程加载真实模块并运行完整构造函数到首次数据库访问边界，确认按 request.targetConfigRef 绑定所选配置、缺失时保持 None。
- Blocker：真实构造路径未到达边界、字段未传递、读取其它目标配置、交付文件摘要变化，立即阻断安装及恢复。
- Verification：先以实际标准包缺失配置复现 RED，再最小补齐正式 transform，GREEN 与受影响完整回归通过；安装激活前用新封包真实构造函数读取实际 owner，并对该构造对象执行原生只读 inspect 解析全部健康端点。数据库访问边界停止，不能启动停写服务来做预检。
- Forbidden action：不得用手动赋值 SimpleNamespace、字符串存在检查或仅源码单元测试替代交付构造路径；不得修改旧目标摘要、失败记录或跳过健康检查。
- Evidence：doc/tasks/20261106-spug-prod-incremental-to-two-targets/packaged-frontend-readiness-plan.md、实际 RED/GREEN/REGRESSION、精确提交/新专属 worktree/包摘要及实装构造边界证据。

阶段必查与推荐命令：实现前运行 `pytest scripts/tests/test_backup_variants.py::test_packaged_constructor_binds_only_requested_frontend_readiness`；完整回归后独立提交，新建干净专属 worktree 构建。激活前执行上述实际 owner 构造检查并保持原容器、数据与挂载；Fail Fast 按 Blocker 保留旧安装、原错误和停写状态。必须记录各阶段真实命令、退出码、构造边界、实际端点和所有交付 pins。

## 旧MAIN续办历史兼容门禁

- Trigger：控制升级后旧MAIN/v1已消费clearance缺mainProtectionRecoveryPin，目标selections返回500。
- Preflight check：先只读固定真实调用堆栈、旧clearance/ready/release/consumption、原配置与当前相等、后继请求同来源/点/目标及真实worker/child/replacement终态；检查全部旧保护目录，缺字段不能直接当可用。新封包激活前必须以实际历史执行Native.selections，不只验证配置和imports。
- Blocker：旧记录未消费、后续未闭合、消费循环/深度超限、原配置或pins变更、MAIN/v2、任何新保护配置/记录、未知或不一致的退出和终态，均明确拒绝。当前新流程完整保护凭证不得省略。
- Verification：真实Linux运行test_legacy_main_clearance.py，包含两个实际封包新进程、旧单链/多链成功及配置/跨点/退出/缺件/保护/循环/深度反向测试；相关retained/scheduler/封包回归通过后独立提交、干净新构建。再以真实只读selections验证目标可选及旧原件字节不变。
- Forbidden action：改写旧FAILED/clearance、删除消费或stateRoot、笼统捕获KeyError放行、未验收启动应用、使用API代替真实UI恢复、把测试或目标可选当恢复完成。
- Evidence：doc/tasks/20261106-spug-prod-incremental-to-two-targets/legacy-clearance-plan.md、真实错误/配置/历史链摘要、RED/GREEN/回归、精确提交封包、实装selections及最终恢复验收。

阶段必查：安装前查真实全部旧历史与原件；激活前用新封包在新进程执行实际目标selections；提交前查未消费新clearance和当前准入；完成后查新旧关联和原件。推荐命令为上述Linux pytest与只读Native.selections/HTTP GET /selections?targetConfigRef=已登记目标。Fail Fast采用上述Blocker；必须记录真实历史版本、配置摘要、链终态、文件pins、实际入口结果与唯一新操作编号。

## 增量恢复冻结自增状态门禁

- Trigger: BINLOG_SQL增量恢复，或原生导入exit0但FORMAL_SCHEMA_MISMATCH仅显示AUTO_INCREMENT不同。
- Preflight check: 从同一不可变expectedDataPin核完整schema证明；目标仍停写且UUID/全部writer/原容器/锁和归档保护有效。先完整观察实际schema，验证全部catalog和除顶层自增计数以外的所有定义一致；表选项必须绑定真实整数自增列，不识别注释、默认字面量或嵌套文本为选项。所有表都检查，不能只看行事件影响表。
- Blocker: 非计数结构差异、无效/重复/溢出选项、表列/身份/证明漂移、原生SQL失败或回读不符，立即保留失败并阻断启动和下一目标；实际测试载体失败不算业务RED。
- Verification: 隔离MySQL 8.0.39通过实际ROW日志复现已提交行相同而计数不同，再以冻结值恢复并保持严格compare_schema通过；未变化计数不写。真实运行在增量导入之后、独立数据回读之前，写意图/冻结源摘要/实际原生mutation退出/前后值和结果pins；最终完整结构/数据、对象/引用/Redis/应用验收不变。
- Forbidden action: 不归一化或移除AUTO_INCREMENT比对，不用MAX(id)+1重算、不手工修改单个业务表后宣称原操作成功；不改冻结归档或历史失败，不删除保留失败、锁或预约。禁止未验收目标启动应用。
- Evidence: `doc/tasks/20261106-spug-prod-incremental-to-two-targets/allocator-real-red.json`、`allocator-real-green-3.json`、`allocator-real-frozen-plan.json`。真实History368仅一个表30384/30376不符；隔离真实日志复现11/3且两行一致。

入口依赖必查：通用NativeData与MAIN使用的MinimalData模块加载器分别核对；在两个实际封包的新进程中调用真实modules_from，确认formal_schema_evidence来自封包路径且MySQL客户端继承SchemaMySql，不能只用预填modules的单方法测试或AST字符串判断代表实际入口。安装激活前也运行该加载检查。缺项立即阻断恢复，保留旧安装，修复后新提交/新封包；证据为allocator-entry-red-1.json和allocator-entry-green-1.json。

阶段必查项与推荐命令：先读取原失败/worker/导入器退出，固定全部原件并只读核真实完整差异；执行`pytest scripts/tests/test_frozen_auto_increment.py scripts/tests/test_backup_variants.py`及原生导入/保留失败回归，Linux测试须使用可解析真实Git提交对象的载体。完整包行为与原生mutation审计验证通过后单独提交，新建干净专属构建worktree，限定安装新控制代次、保留旧代次；按上述保留失败续恢复入口精确交接保护，再真实Spug同点同目标产生新编号。Fail Fast：任一证明、测试、封包、保护交接或实际回读缺失不重试、不启动。必须记录RED/GREEN/回归、精确提交/工作区/包/实际安装pins、原失败和新编号、最终结构数据验证与清理结果。

## 增量父输入流检查成本与持续保护门禁

- Trigger: 增量语义采集出现FORMAL_CAPTURE_PIPE_DEADLINE，或父点内容验证读取字节远高于实际载荷、每缓冲回调重读大型父元数据/扫描全部父文件。
- Preflight check: 原失败终态、源writer及数据库全局状态独立恢复通过后，只读分别测量原查询、一次父元数据读取和完整身份扫描；核实际安装SAFE源码与回调次数。父内容必须初始完整SHA核验，使用覆盖全部父文件和祖先的连续Linux路径租约；小型原输入用身份检查，最后仍完整核原字节。阶段边界完整核父元数据原字节和全部文件/祖先身份，不能假定CIFS远端写入会产生本地事件。
- Blocker: 每缓冲工作随整个父点大小增长、租约未覆盖完整路径/祖先、实际FD或inotify预算不足、任何写入/替换/监控溢出、完整SHA或阶段复核缺失，均阻塞新的最终提交；原失败和原安装保留。
- Verification: 真实Linux原生管道在原期限内完成；反复检查不重读父元数据或扫描全部父路径；写入/替换/祖先改变/无事件的阶段变动/预算不足均拒绝，初始核验失败和正常关闭无FD泄漏。独立验证实际STANDARD封包字节、严格原内容核验及最终originals.check(full=True)保持，再安装独立已提交代次并核实际文件SHA和原业务保持。
- Forbidden action: 禁止单纯增大查询超时、按时间跳过检查、忽略事件/身份失败、弱化父内容SHA，禁止热改活动worker或以无guard的诊断查询充当冻结点验收；不得重写原失败为成功。
- Evidence: `doc/tasks/20261106-spug-prod-incremental-to-two-targets/reference-stream-diagnosis.json`、`parent-guard-red.json`及后续真实测试、安装和原生验收记录。

阶段必查项与推荐命令：先观察原编号终态和源恢复，执行任务内只读引用对照；修复先`run_parent_guard_tests.py --phase red`，再GREEN、原归档租约/FD和SAFE封包回归。提交实现后新建专属干净构建worktree，安装时持原排他锁、无活动worker，仅重载自有控制服务，实测FD继承及原容器/共享盘保持。Fail Fast：任一保护或真实测试未通过不安装、不停写、不重试旧代次。必须记录原查询/扫描成本、RED/GREEN、实际提交/包/文件SHA、预算、两代安装和新旧唯一操作号；真实增量及两服整链恢复单独验收。

## 增量导出工具实际运行门禁

- Trigger: 任何INCREMENTAL最终提交，尤其整机/Docker/MySQL重启后，或出现MINIMAL_BINLOG_TOOL_CHANGED、FORMAL_CAPTURE_STDERR_LIMIT、mysqlbinlog临时文件只读错误及socket errno13。
- Preflight check: 从当前实际生效capture配置的mysqlbinlog-exporter材料pin读取登记，核containerId/imageId、Running、ReadonlyRootfs、NetworkMode/PidMode绑定当前源MySQL及可执行SHA。必须核User/Group、安全选项与原工具完整合同；使用原私密stdin/socket、no-defaults及登录文件隔离，真实导出父点到明确终点的全部非空区间，记录逐段exit0/stderr0/输出字节和摘要；SELECT/SHOW范围审计另行通过。空范围仅证明连接，不能证明真实日志处理。只读根工具需要真实可写、受容量限制且noexec/nosuid/nodev的隔离tmpfs，禁止接入源数据卷作为工作目录；同时核内存/pids及实际/tmp写入、清理与用户身份。
- Blocker: 工具停止、身份/绑定/文件SHA漂移、临时目录缺失、User不匹配、实际认证或任一非空区间导出失败，均在耗时父链读取及停写前阻塞提交。先保留失败终态、来源真实恢复/健康和全部原件证据；只在授权范围恢复原工具或安装新不可变工具/capture/owner/control代次，旧工具和旧配置保留；已受理请求只查原编号。
- Verification: 当前实际安装的MinimalSeries.binlog_container严格校验及实际导出连接通过；若启动原工具，前后固定全部原容器定义/镜像，逐项比较其它容器PID/启动时间，fstab及原保护挂载保持。Mounts按Destination排序；允许的新增挂载只能精确对应已授权启动容器的原GraphDriver.MergedDir，不能忽略其它差异。
- Forbidden action: 不重建未知替代、不擅改原工具重启策略、不重启主程序/MySQL/Docker，不放宽零stderr或严格工具检查；不以额外cap代替核准原User，不用源数据卷或可写根绕过tmpfs合同，不把空范围、镜像存在、配置pin或日志事件可读冒充实际非空导出可用。
- Evidence: `doc/tasks/20261106-spug-prod-incremental-to-two-targets/incremental-364-failure.json`、`registered-binlog-tool-restored.json`和`incremental-2-preflight.json`。原工具70c048在11月4日停止，History364于STOP_WRITERS之前失败；原工具恢复后原SHA/实际连接通过，195定义及其它194运行态保持。

阶段必查项与推荐命令：先核`docker inspect <登记工具ID>`的User/CapDrop/Tmpfs/Memory/PidsLimit/源绑定及`docker exec <登记工具ID> sha256sum /usr/local/bin/mysqlbinlog`；按当前任务工具核真实/tmp写入，再以私密stdin导出所有已严格审计的非空区间。现有执行参考`provision_binlog_tmpfs_tool.py`、`verify_binlog_tmpfs_full_export.py`与`activate_binlog_tmpfs_control.py`，复制到新任务时重新固定当前真实身份/容量/旧配置，不能重跑旧代次。目标恢复前另核实际安装的增量scope协议和SQL读取方式；现有整文件读取路径须在新点准入时以最终rawSqlBytes核/proc/meminfo实时MemAvailable，保留其它进程余量，并同时满足maxExpandedBytes与磁盘预算，不能只看压缩包大小或旧内存快照。Fail Fast：任一非空导出、临时目录、身份、范围、容量或前后保持不通过，不停写、不提交；必须记录原失败、BDD/真实RED、配置GREEN/全段回归、实际User和tmpfs/资源约束、逐段导出摘要、授权、原件及旧/新配置pins与唯一操作号。History366失败及v3全部12段真实17211499419字节SQL/零stderr证据位于同一任务目录，不能把该只读回归当新增量点成功。

## 恢复后增量日志范围门禁

- Trigger: 原MAIN恢复后继续增量，或范围校验出现FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN，尤其日志含完整库重建、外键动作、生成列、CHECK及审计触发器。
- Preflight check: 固定父point/capture pins、当前UUID/版本/日志模式与完整保留位置；在任何停写前通过受限SELECT/SHOW对精确起止范围逐事件严格校验。恢复导入是否写binlog须从实际已安装程序与实际事件证明，不能仅凭UUID相同或日志文件存在推断连续。诊断扫描可单独收集不支持的原始DDL，但必须标DIAGNOSTIC_ONLY，含SQL原件私密保存。
- Blocker: 缺日志、父链或源身份漂移，任何未知/跨库/未证明范围语法、完整事件未审完、诊断跳过被当作PASS，均阻塞增量最终提交；先形成正式有界解析方案及RED/GREEN，不能在停写窗口临时试错。
- Verification: 记录连续段及原始事件摘要、事件数、范围proof和实际模块SHA；表达式只接受本列、常量及明确MySQL内建函数，触发器逐FROM/JOIN验证本库，写效果限定NEW行赋值及SIGNAL。跨库、任意UDF/系统变量、CALL/动态SQL/未知表写入/注入必须负向测试；实际封包和真实全段零跳过审计须通过，再真实页面单次增量与整链恢复独立验收。
- Forbidden action: 不过滤/略过失败事件、不静默全量、不仅扩大正则通配或删安全检查，不从当前表结构推断历史日志范围，不把本地源码当已安装程序。日志正文可能含敏感内容，不输出到公开任务或提交。
- Evidence: `doc/tasks/20261106-spug-prod-incremental-to-two-targets/`，实际旧解析器在137101事件中拒绝1742处/871唯一DDL，候选全段只读审计零跳过通过；具体最终结果仍以该任务原生操作及验收为准。

阶段必查项与推荐命令：先运行任务内`inspect_incremental_lineage.py`核真实登记和日志，再运行`audit_binlog_scope.py`严格只读审计；修复时`pytest scripts/tests/test_smallapp_binlog_ddl.py scripts/tests/test_backup_variants.py`验证范围和实际SAFE封包，混用不同源码根的测试文件必须独立进程运行避免模块缓存污染。提交、专属干净发布worktree封包、安装文件SHA和新配置pins核验后，再真实页面确认固定父链。Fail Fast：任何拒绝先保留错误与当前服务健康，不启动备份、不停写。必须记录原拒绝、补齐边界、负向测试、候选及实际安装全段审计和最终唯一操作号。

## 多机器发布接管与缺失记录分析门禁

- Trigger: 不同机器轮流发布、本机Spug记录缺失或落后、服务器版本新于交接资源包，或前端补丁不在本机历史中。
- Preflight check: 在已授权目标上只读核实际release-info、主版本/前端补丁绑定、源码提交、前后端镜像ID及真正生效的启动配置；交叉核对服务器或共享存储中现存manifest、包摘要、部署回执、迁移台账及schema、当前任务锁和恢复依据。先检查现存证据，不能仅凭页面tag判断完整发布过程或要求重传整个资源包。
- Blocker: 本机历史缺失本身不是阻塞，不强制重新导出最新资源包。存在活动发布/恢复或无法排除并发时阻塞远端写入；版本/镜像/清单冲突、缺少待执行动作必需的不可变包或迁移/恢复证据、无法确认真实起点时，只阻塞依赖该缺口的阶段，并记录精确缺项和影响。构建、空间、GxP及恢复门禁继续独立生效。
- Verification: 生成带采集时间和目标身份的差异报告，列出原本机登记、远端观察、证据路径及摘要、已证实与未知事项。核实后可用实际状态生成当前基线/新一轮逐目标计划；正式登记更新仅走已有受控入口及其校验，不直接改SQLite或冒填旧任务成功。没有可用入口时单列配套能力缺口，不自动恢复“必须重新导出”的要求。
- Forbidden action: 禁止猜测最新状态、伪造历史发布/验收成功、改旧包或迁移摘要、丢弃旧失败记录、用Git模板覆盖凭据/历史/绑定、覆盖正在发布的目标，或把只读当前状态核验冒充过去完整发布验收。单项证据缺失时优先获取对应原件或分析缺口，不默认要求整包重导出。
- Evidence: 用户2026-11-02明确修订；`doc/tasks/20261101-full-then-frontend-release/execution-log.md`及该任务当前基线分析报告。此前停止并要求重导出的记录只表示当时规则，后续按本门禁执行。

### 阶段必查项与推荐命令

1. 采集：本机SQLite只读连接`mode=ro`查任务及版本；使用配置绑定的`Runtime.observe(env)`核远端镜像/配置/schema/台账，并GET真实入口`/release-info.json`；以实际主版本和补丁版本分别比较，不把合法前端补丁误判为主程序漂移。
2. 分析：按差异定位现存远端manifest、包及部署回执，使用`Get-FileHash -Algorithm SHA256`或`sha256sum`核原件；只记录安全字段和证据摘要，凭据留在私有目录。确认旧机器/其他发布者与服务器任务锁均不争用当前目标；无法排除并发只停止写入，不停止独立只读分析。
3. 续办：将可证实起点绑定新一轮计划，不补造历史成功；重跑原发布前置检查，测试→正式→审查顺序及原包不可变规则继续适用。缺少恢复原包时先列包名、摘要或路径等具体缺口，不直接用新编译包代替。

Fail Fast：证据相互冲突或目标发生变化时保留原观察，重新采集分析；只对依赖该身份的写入/晋级暂停，不无条件要求重新导出资源包。

必须记录：本机/远端主版本与补丁版本、源码、镜像及配置/schema/ledger指纹、证据来源与时间、并发检查、未知事项、恢复条件、被阻塞的具体动作及解除依据；记录缺失不等于发布失败或成功。
## 三服同版本同结构发布门禁

- Trigger：同一发布包依次升级测试服、正式服和审查服，或发现程序同版本但数据库缺表、缺字段、缺索引。
- Preflight check：先只读采集真实表、列、索引、约束及可编程对象；差异必须有明确原因。读取真实迁移台账，已 APPLIED 的历史迁移保持原字节。需要补齐结构时新增独立前向迁移，使用真实 MySQL 验证重复执行及现有行保留，发布输入必须来自已提交内容。
- Blocker：未知结构差异、历史摘要冲突、非预期待执行迁移、包摘要不符、有效启动配置与镜像不符、GxP 未关闭、恢复条件不满足、远端任务状态未知或三服升级后结构不一致，均不得记发布完成。
- Verification：同一 releaseTag 的测试升级、测试验收、正式升级和开放、审查升级和开放闭合。逐服核远端 operation=SUCCESS、manifest、实际生效配置、前后端镜像、backend health=UP、frontend HTTP 200、真实 Playwright 登录，以及 GxP 保存和运行均关闭。独立对照三服表名、字段、索引、约束，不能只比较表数。
- Forbidden action：不得修改旧 SQL 摘要或台账，不得删除测试服现有表凑齐数量，不得同步业务行来冒充结构一致，不得创建未被读取的旧 .env 凑齐格式，不得把只读页面核验称为完整业务回归。用户已取消的全量演练不重新加入门槛；正式独立恢复机制不重复采集。
- Evidence：本任务 schema-before.json、真实 MySQL 验证、源提交 fb88105a、维护提交 15b2f5c/43e4d3e、531 项回归、Spug 固定包及任务回执。最终结果以 release-result.json 为准，本文不预先宣称通过。

### 阶段必查项与推荐命令

1. 构建前：通过 Spug 真实页面选择固定提交并检查 GxP 配置来源；静态 migration-readiness 只证明计划检查。所有环境本轮 APPLY 应仅为新增修复迁移。
2. 封包后：校验 manifest、每个成员、release.tar 和 NAS 副本摘要。已封包后的上传或清理失败，保留原失败，用 Spug 原包重传入口校验续接，不重新编译。
3. 升级前：核实际起点、包身份、可用空间及本环境恢复条件。逐环境使用自身历史台账，不要求升级前结构或业务行相同。
4. 升级后：`verify-deployed-phase.py <env> [open]` 核运行态，`verify-target-gxp.cjs <env> <tag> [acceptance]` 走真实登录；正式和审查启动前、部署回执及开放验收均核同包上游已验收 schema。
5. 最终：`collect-schema.py schema-after.json` 与 `final-release-report.py` 核完整结构和同包闭环，随后清理本任务 checkout/槽位、保留独立分支并单独提交任务记录。

Fail Fast：任何未确认远端效果、原包冲突或真实验证失败必须保留证据并停止后续晋级，先查迁移、清单和脚本契约。不得手改服务器 SQL、改摘要或直接改任务状态绕过。

必须记录：目标、tag、提交、worktree、构建/验证命令、每阶段任务和操作号、恢复策略、失败及续接关联、实际镜像和 schema 摘要、GxP、验证范围及最终工作副本删除结果。

## Spug 构建产物与安全清理门禁

- Trigger: IntRuoyi构建/构建预检、封包后清理、NAS原包重传或普通执行器更新。
- Preflight check: 选择包含完整发布配套的Git已提交内容；构建预检与正常构建均先执行`validate_source_contract`，不能用工作区未提交修复替代。配置可登录的`gxpConfigurationSourceUrl`，关闭要求显式设置`requiredGxpAuditMode=DEVELOPMENT_DISABLED`；真实页面保存及运行模式一致、auditEnabled=false、无待重启。
- 阶段必查项与推荐命令: 在独立维护修复副本运行`python -X utf8 -m unittest test_build_recurrence_guards test_build_worktree_cleanup test_intruoyi_login test_nas_package_retry test_release_precheck`。正常构建在docker save/封包前从实际镜像提取JAR并运行断网、只读、无数据库凭据的Boot CLI，验证退出码3、报告身份和类唯一归属；不能仅检查源码或release-info。完整封包后使用`cleanup_sealed_build`，删除前保存归属检查点；NAS重传沿同入口验证原包并完成清理，不能重新编译。
- Blocker / Fail Fast: 缺源码契约、镜像JAR与冻结产物不同、类加载失败/超时/报告身份不符、GxP不一致、工作副本提交/登记漂移、未知文件、嵌套Git、未核实链接或进程引用，停止相应阶段并保留证据。Git移除非零不等同于物理删除失败或成功，必须分别核对登记和真实目录。
- Verification: 真实已有镜像离线验证和真实GxP页面通过；Windows临时真实Git、>260字符目录及junction验证必须保留外部哨兵。仅从已核定生成目录移除链接自身再交给Git，绝不跟随到外部目标；残留删除再次核对源码字节及未知文件。安装前后完整校验工作资源包、唯一普通执行器入口及SQLite payload；凭据仅新增已批准非敏感策略字段，其余字段保持。
- Forbidden action: 禁止通过改摘要掩盖原校验失败、重新编译解决已封包上传失败、任意递归删除、自动融合int_main、恢复已取消演练、固定64GiB门槛、重复正式全量备份或将单元测试称为真实业务验收。
- 必须记录 / Evidence: 目标/维护提交、RED/GREEN/REGRESSION、实际JAR及封包摘要、原校验及更新清单、工作副本归属/检查点/Git退出码/物理删除、普通PID/入口/文件摘要、私有历史保持证据；见`doc/tasks/20261101-release-recurrence-guards/execution-log.md`及该任务脱敏JSON。

## Spug 恢复包接口合同与保留失败续恢复门禁

- Trigger: SAFE/FAST 组件注入、覆盖恢复准备、`RESTORE_TYPEERROR`、`ARCHIVE_LEASE_FD_BUDGET_EXCEEDED`，或写入前/清库后 `FAILED_RETAINED`。
- Preflight check: 在独立发布 worktree 从精确已提交目标构建，测试实际 tgz 内的调用方、文件引擎和 MySQL 包装；SAFE 保持完整哈希与读回，FAST 专用参数不得进入冻结 SAFE 接口。DROP/CREATE 等破坏性 SQL 必须实际记录 `mutation=true`。恢复前核 NAS 原 canonical 路径、只读挂载/持久依赖与新点 pins，不能只验证来源机可读。
- Blocker: 包接口不兼容、审计把写入误记为只读、目标身份/挂载/版本漂移、原 worker 活动或未知终态、缺少明确恢复授权、保留预约属于其它操作，均停止相应阶段。清库后失败时保持业务写入服务停止，禁止启动空库主程序。
- Verification: 实际包组件测试与 POSIX 文件锁/预约用例通过；新安装代次逐文件摘要、新配置 pins、原失败字节不变。真实 Spug 新编号恢复需终态成功，并核数据库全结构/数据、附件版本、Redis、原容器镜像与 UUID、health/HTTP及真实登录后页面；单测和 HTTP202 不代替恢复验收。
- Forbidden action: 不删除 failed claim/原预约证据，不改 FAILED 为成功，不建新 stateRoot 绕过保留，不自动重试、不用接口或 SQL 绕过正常页面执行恢复，不用旧点代替用户要求的新全量包。
- Evidence: `doc/tasks/20261104-spug-prod-full-to-test/retained-recovery-plan.md`、`execution-log.md`、`retained-recovery-install.json`、`retained-recovery-authorize.json`、`restore-attempt-1/`、`restore-attempt-2/`；修复提交 `9176b3c`。

阶段 1：封包合同与环境准入。必查实际 SAFE/FAST 包内 `prepare`、`inventory/apply_tree` 和嵌套 `BoundMySql.query`，先 RED 再 GREEN。推荐执行 `python -B -m pytest -q scripts/tests/test_backup_variants.py scripts/tests/test_retained_replacement_retry.py`，POSIX 专属用例必须在 Linux 实际运行。Fail Fast：依赖/挂载缺失是环境失败，不能冒充业务 RED 或静默跳过。必须记录提交、临时工作区、包双摘要、测试环境与通过/跳过数量。

阶段 1a：完整归档租约预算。每个实际来源/目标控制服务均核 `systemctl show <本任务unit> -p MainPID -p LimitNOFILE` 和 `/proc/<MainPID>/limits`，不能只核配置文本或别台服务器。按完整FULL/增量链所有文件与祖先路径租约，加当前已用句柄及至少64工作保留计算；`soft`不足即Fail Fast。为自有且无worker的控制服务设置持久 `LimitNOFILE`，仅在明确安装/修复授权下重载该服务，实测继承值并核全业务PID/启动/配置和历史pins不变。禁止提高全局限制、削弱归档保护或以硬限制代替软限制；记录路径数量、软/硬预算、drop-in和重载前后证据。

阶段 1b：MAIN与演练执行依赖。实际SAFE初始化按已选择的登记MAIN合同仅绑定实际使用的Docker执行文件；演练的网络隔离仍必须绑定并验证iptables。所有归档、版本及请求/配置输入pins必须在两种路径完整租约/哈希；测试实际封包O_PATH/inotify初始化块，MAIN缺演练文件可通过、演练缺文件必须失败。Fail Fast：任何实际执行文件/归档/输入缺失或摘要变化，不得制造旧演练路径替身或关闭保护；登记MAIN仍须通过严格容器/镜像/存储/UUID/writer归属合同。必须记录实际缺失pin、运行模式、封包RED/GREEN与保护回归。

阶段 1c：MAIN动态附加网络停启。Trigger：`MAIN_SERVICE_NETWORK_CHANGED`、docker stop后bridge地址清空、应用附加动态地址重新分配。Preflight check：保全原运行及停止后的NetworkSettings/IPAMConfig、配置摘要、固定业务端点或loopback登记应用的固定宿主发布端口（合法HostIp及1..65535端口，HostConfig完整摘要保持）、真实network inspect成员；只允许非数据服务、另一不变静态网络绑定存在且动态地址不作为注册访问端点的附加分配。推荐执行 `pytest scripts/tests/test_main_restore_target.py -k dynamic_attachment`；停止时仅空分配，运行时必须与同一真实网络中原容器的IPv4/IPv6分配精确一致。Blocker / Fail Fast：数据端点或静态IPAM漂移、无其它固定绑定、未证明的新分配、别名/网络ID/成员/配置漂移继续拒绝。Verification：RED复现正常停启误报，GREEN与固定/数据/成员负向场景及实际封包回归；安装后对真实停写原目标只读观察。Forbidden action：不通过固定一个新的临时动态IP、修改原目标摘要或删除失败来规避；已清空目标必须走阶段2且保持停写。必须记录 / Evidence：原/现附件字段、实际数据库表数与UUID、失败pins、测试和新操作；见 `doc/tasks/20261105-spug-prod-full-to-review/dynamic-network-recovery-plan.md`。

阶段 2：已变更目标的显式续恢复。先保全原请求、配置、worker-result、child-exit、replacement-result 和宿主预约 pins，并只读核真实 DB UUID/表数与停写状态。新组件保留旧代次，使用已校验的 `common/recovery_retained_retry.py --operation-root <原操作目录> --authorization <既有明确授权及方案摘要> --expected-table-count <已核实表数> --authorize-retained-replacement`。该入口仅追加准许/观察/释放回执，不恢复业务数据；持原物理锁与宿主预约锁，精确释放同一预约当前指针。Fail Fast：未知/活动/漂移/其它预约/证据变化不准许。必须记录原失败保持、新回执 pins、准许期限及同来源/同点/同目标约束。

阶段 2a：写入前失败的显式续恢复。只有原worker实际exit1、mutationDispatched=false、无replacement-intent/importer且所有native审计均无mutation，原宿主预约已留下精确 `PROVEN_NO_MUTATION` 释放pin、当前无预约时，才可用 `--authorize-no-mutation-replacement` 代替阶段2的选项。严格核原容器/存储/UUID、全部目标服务仍运行、实际表数及全原失败pins，不能停止业务来套用阶段2。持相同两把锁只追加v2准许/观察/ready，不删除或释放任何新预约；新UI编号仅消费同来源/同点/同目标一次。Fail Fast：释放缺失/漂移、存在intent或mutation、原进程仍活跃/未知、其它预约或目标漂移。必须记录两种模式的明确选择、原失败与释放pins、真实观察、授权与方案摘要、新旧编号关联。

阶段 3：正常页面新恢复与验收。通过真实 Spug 页面重新确认同一点和目标，生成新 operationId；执行器只消费一次准许并追加新旧关联。新失败继续保留，不能再次自动解锁。沿原编号查终态，按完整原生一致性和真实业务页面验收；必须分别记录原失败和新结果、启动边界、清理回执与临时发布工作区删除结果。

- 容量合同前置：`maxExpandedBytes` 计量SQL展开大小，`dataLimits.max_bytes` 计量数据库摘要查询输出，不能复用同一大值。安装配置必须调用实际formal.validate_limits（当前max_bytes硬上限16GiB）；实际SAFE/FAST构造器在目标访问/清理前再次校验。推荐运行 `pytest scripts/tests/test_backup_variants.py -k data_limits`，非法64GiB必须在target.services边界前失败，独立SQL64GiB+摘要16GiB必须通过该门禁。必须记录实际安装限额及原失败证据；禁止扩大正式限额掩盖配置错误。证据：`doc/tasks/20261104-spug-prod-full-to-test/readback-configuration-audit.json`。

### 覆盖前保留备份完整读回门禁

- Trigger: 为覆盖原实例而新建当前数据保留全备，尤其同一工程同时存在冻结standard和本地lightweight源码，或读回声明为payloadContentVerified=false。
- Preflight check: 从原worker的实际命令定位程序与封包清单，核variant、完整文件SHA、实际publish调用及reader实现；不能仅查本地同名源码。先等同一备份真实原生SUCCEEDED/exit0、来源服务恢复，固定请求、来源配置、manifest/point/tree和原originalRecordsPin。独立验收只追加自有控制证据，绝不修改归档、来源程序或历史声明。
- Blocker: 原备份仍活动或终态未知、任一pin/文件集/内容漂移、未证明的新连接安全、读回超时或连接断开，阻止原实例覆盖；保留原观察和失败证据，不重派备份掩盖。
- Verification: 已固定SAFE实现确实逐文件实读并比较SHA/大小、前后树、签名加密与私有缓存时，审核原生成功及originalRecordsPin全部实际生成pins与manifest/tree完全相同、保留原始副本和元数据SHA；无需再起一轮重复全量读回。若实际为轻量路径，则必须补齐明确的独立全内容读回后才能覆盖。记录文件数/总字节、实际封包身份及原操作关联；不声称NAS服务端持久化。
- Forbidden action: 不把关键记录读回、成功状态、声明中的payload pins或本机源暂存哈希当作NAS完整内容证据；不从无payloadContentVerified字段推断未完整读回，不把本地lightweight函数参数套进冻结SAFE，不改原schema、不用mock或抽样替代，不在保留依据未通过时覆盖。
- Evidence: `doc/tasks/20261105-spug-full-to-prod/verify_preservation_payload.py`及其实际运行后产生的preservation-full-payload-readback.json；脚本存在或语法通过本身不构成内容验收。

阶段必查项与推荐命令：先定位实际运行包；原生成功后运行verify_preservation_point.py，随后verify_preservation_payload.py审核真实完整读回原始凭据及verify_preservation_admission.py真实准入，再复核来源原服务和真实业务页面。Fail Fast：任何失败立即停止后续覆盖，沿原编号/原读回worker查证，不自动重试。必须记录：精确原备份操作、实际封包/程序、配置和元数据pins、连接安全与独立身份、文件/字节总量、完整比较、原schema保持、原始退出与失败材料位置。

### 阶段1d：保留原 MAIN 的存储与发布端口

- Trigger: 原应用含可写 runtime 父目录、Docker socket、共享备份挂载、停止历史消费者，或原 MinIO 发布端口、Redis 无认证、来源与目标同机。
- Preflight check: 显式 MAIN/v2 + storage/v3，三个数据路径单独登记；全部原应用挂载物理身份/只读内容、全部重叠历史容器配置及停止/PID0/无exec逐项固定。核全部真实 writer、IAM 账号独占、MySQL/Redis 当前连接、原网络成员与完整发布绑定；无认证固定 ACL 摘要且无发布/host 网络。来源目录控制独立于停写主程序，源目标使用实际同一物理锁，覆盖前核当前数据保留依据和所选完整归档 pins。
- Blocker: 未知 writer、未登记消费者、挂载/配置/ACL/程序摘要/端口/网络漂移、围栏缺失或失效、数据库事件仍启用、外部数据库/Redis 客户端未退，均在 DROP 前失败；失败后保留停止状态、围栏及证据。
- Verification: 在真实 Linux 运行 `scripts/tests/test_retained_application_storage.py`、`test_main_retained_authentication.py`、`test_main_published_endpoint.py` 和 `test_published_write_fence_linux.py`；实际 IPv4 DNAT、IPv6 代理、root/非root、已有链首 ACCEPT、其它端口、漂移拒绝及释放原表保持均通过。实际 SAFE/FAST 包逐文件核验并确认保护 hook 顺序。
- Forbidden action: 不把保留挂载列入清理范围，不忽略全部停止容器，不虚构 Redis 密码，不把发布端口保护称为整个网络隔离，不 flush/重写原防火墙表，不自动移除失败围栏或重复派发恢复，不删除/卸载公司 NAS。
- Evidence: `doc/tasks/20261105-spug-full-to-prod/design.md`、`execution-log.md` 及 Linux 原始日志；实际安装、运行和恢复结果须另行留证，不能以本地测试代替。

阶段必查项：登记前只读核身份、归属及共同锁；安装从精确提交的新专属发布 worktree 构建，仅更新自有控制；执行器安装独立操作 mangle/PREROUTING、OUTPUT 链首规则并复核原表保持，再停止原 writer、核连接和事件、进入清库；危险阶段再次核实际规则；原生成功及读回后只移除本操作规则并核原表恢复。Fail Fast 与必须记录：精确源点/目标/提交/包双摘要、实际 xtables pin、原有序表摘要、所有者证明、停写检查、围栏意图/active/release pins、真实 UI 操作号与退出结果、其它业务保持。恢复中失败沿已有保留失败准许流程，不另建 stateRoot 绕过。

### 阶段1e：同机可写来源的归档视图保护

- Trigger: 同机来源备份需要可写 CIFS/NFS 归档视图，而覆盖恢复要求所选归档只读。
- Preflight check: 显式 MAIN/v2 archiveMountProtection，完整实际 mountinfo 和 mount 程序 pin；所有 archiveRoots 严格位于登记视图下，与目标 DATA/保留应用挂载不重叠且不是公司 /mnt/nas。公司保护目录须按事前 mountinfo 固定全部子挂载及覆盖它的祖先文件系统；实际可能仅有 /mnt/nas/Backup/BackupPackage 子挂载，不得假定 /mnt/nas 本身必有独立挂载。先完成当前数据保留全备；备份和恢复持实际同一物理锁。安装阶段仅只读 preflight，不提前改变备份的写入视图。
- Blocker: 锁冲突、归档/挂载/程序身份漂移、作用范围不明确、保护后原挂载身份或其它 flags 改变，立即停止相应动作；失败保留只读状态和原操作证据。
- Verification: 真实 Linux 运行 test_archive_view_protection_linux.py，确认目标视图 EROFS、同存储另一视图仍可写、漂移拒绝、成功恢复完整原 mountinfo；test_main_archive_view.py 核先保护再停写/清库、原生成功后释放；实际 SAFE/FAST 包包含相同模块。独立验收严格比较公司目录的原子挂载和覆盖祖先完整身份/参数，任何增删或变化失败；同时核 fstab SHA。父目录无独立挂载而原子挂载完全保持时应通过，不得为满足验收假设新增或修改生产挂载。
- Forbidden action: 不卸载、不改 fstab、不重挂底层 superblock、不对 /mnt/nas 执行保护、不用新状态根绕过失败、不在备份执行时抢锁或改变其写入视图、不把单视图只读称为共享存储全局不可变。
- Evidence: doc/tasks/20261105-spug-full-to-prod 的设计、Linux 原始日志、构建与安装证据；实际执行须记录原 mountinfo、操作号、意图/active/release pins、源备份终态及其它视图保持。推荐命令采用 mount -i -n -o remount,bind,ro/rw -- 精确视图，由正式执行器持锁调用。

阶段必查：安装前只读固定原 mountinfo，恢复后逐项比较；推荐只读命令读取 /proc/self/mountinfo 和 sha256sum /etc/fstab。Fail Fast：原始基线缺失、保护目录子挂载或祖先变化即停止验收，不修改挂载补证。必须记录原始基线私密 pin、实际挂载路径、比较结果、原失败验收日志及修正后验证。任务 test_protected_mount_verification.py 的5项回归覆盖子挂载保持、参数漂移、新增挂载、祖先变化和无关挂载。

### 阶段1f：原MAIN资源观察身份

- Trigger: 恢复到已登记原MAIN，或资源观察出现RESTORE_RESOURCE_MYSQL_IDENTITY_INVALID而原容器无演练专用标签。
- Preflight check: 先核实际已提交封包中的observe_resources，显式完整MAIN/v1或v2必须核原MySQL id/image、replacement登记的labels/mounts与完整Path/Args/HostConfig/Config摘要及非privileged状态；普通空目标继续核intruoyi.recovery.target。运行/PID、实际父cgroup、宿主RAM和各设备累计磁盘预算均独立检查。
- Blocker: 原实例身份/配置/挂载/MAIN合同漂移、未知容器或运行状态、实际内存/磁盘不足均阻止安装或恢复；仅缺演练专用标签不能代替MAIN身份判断。
- Verification: Linux执行`python -B -m pytest -q scripts/tests/test_recovery_resource_budget.py scripts/tests/test_recovery_resource_reservation.py scripts/tests/test_main_restore_target.py`，覆盖MAIN两个版本无标签实测准入、配置/挂载/镜像/登记漂移拒绝、512MiB cgroup拒绝和普通无标签目标拒绝。安装后读取实际资源准入结果，不把单元fixture当远端测量。
- Forbidden action: 不重建或改原容器标签凑通过，不删除资源门槛，不仅凭mainApplication存在绕过完整登记，不以新stateRoot或删除原失败配置续办。
- Evidence: `doc/tasks/20261105-spug-full-to-prod/main-resource-admission-diagnosis.json`、`linux-resources-red.log`和后续GREEN/回归及安装资源回执。

阶段顺序：先只读固定原身份与安装失败现场，再RED/GREEN及受影响回归、限定提交；从新专属精确提交worktree构建安装新代次，旧组件/配置保持。Fail Fast：实际身份不符时不更新登记摘要。必须记录原错误、旧配置/服务/预约/锁状态、目标提交/包双摘要和真实资源观测值。

### 阶段1h：原MAIN语义健康与已启动存储续办

- Trigger: 原MAIN MinIO/backend/frontend没有Docker HEALTHCHECK，或物理复制后报ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED。
- Preflight check: 先核原容器完整id/image/Path/Args/HostConfig/Config摘要与登记IP、实际ExposedPorts。MAIN固定语义策略分别使用MinIO 9000/minio/health/ready、后端48081/actuator/health的JSON status=UP、前端80/的HTTP200；禁代理和重定向，响应有界、启动等待有界。已有Docker Health声明是额外条件。非MAIN原严格Docker合同保持。失败后若存储仍运行，必须核原worker实际exit1且无活动进程、原失败全部pins与预约保持、原Docker start命令摘要/成功退出/本操作号、当前StartedAt位于原命令起止内、全部业务writer已停止、归档/端口/调度器保护仍有效。
- Blocker: 未声明端口、未知/漂移IP或原配置、错误协议、超时、Docker unhealthy/声明无状态、未知启动者或重启时间、仍活动worker/writer、保护或历史pins漂移，阻止健康通过或续办停写/clearance。
- Verification: `pytest -q scripts/tests/test_main_readiness.py scripts/tests/test_main_restore_target.py scripts/tests/test_backup_variants.py`及真实原MinIO只读探测，真实SAFE/FAST封包包含相同组件；恢复成功核三角色RegisteredMainSemanticReadiness/v1的精确身份/配置/端点/返回值pins及真实页面。续办精确stop意图、实际exit、停止观察、其它194运行态保持及原失败pins保持缺一不可。
- Forbidden action: 不改原容器/镜像制造HEALTHCHECK，不把running当healthy、不跳过后端UP、不跟随重定向/环境代理、不宽放普通演练检查、不自动重复stop未知终态、不覆盖旧失败、不手工删除预约、不操作公司/mnt/nas。
- Evidence: `doc/tasks/20261105-spug-full-to-prod/main-health-recovery-plan.md`、原失败诊断、真实探测、RED/GREEN、精确停写/安装/clearance和新独立操作完整验收。

阶段必查项：破坏性恢复前先校验正式语义端口合同；启动后验证真实协议并固定成功证据；失败续办先保全原件，持原来源锁和宿主预约锁，只停证明由该失败操作启动且身份/配置未变的原MinIO，追加意图及退出记录，再按阶段1g签发同点同目标clearance。推荐命令为只读`docker inspect`选定id（敏感Env不公开）、无代理/无重定向HTTP探测和新增测试。比较Docker挂载定义前按Destination排序；Docker返回的Mounts列表顺序不稳定，不得把裸列表摘要变化当作运行态变化。定义差异须与PID/StartedAt/实际挂载逐项核对；停止已实际exit0而后置比较失败时仅只读核销，不重复stop。Fail Fast按上述Blocker执行；必须记录实际状态、原声明、完整固定摘要、探测次数/HTTP/语义状态、原生退出、失败/保护pins、续办前后原容器状态和其它业务保持。

### 阶段1g：MAIN事件调度器与失败保护交接

- Trigger: 登记MAIN原MySQL event_scheduler=ON、清库后FORMAL_SQL_DATABASE_CHANGED、SET OFF返回后线程仍在，或保留失败带归档视图/发布端口保护。
- Preflight check: 先只读核UUID、read_only/super_read_only、仅系统四库与登记应用库、事件调度器原状态；清库前停止全部原writer，独占记录原状态，ON暂停为OFF，最多15秒等待事件线程与活动事务都为0，等待中重核身份/范围/暂停状态。导入和完整读回边界继续核暂停。保留失败准许必须持原来源锁和预约锁，核原真实exit1/无worker、目标writer仍停止、身份及失败pins不变，全部旧保护先验证再精确释放、追加原pins和释放pins；有调度器custody则保持暂停并将首次原状态传至同点同目标新操作。
- Blocker: 未知原状态、其它应用库、身份/范围/调度器漂移、线程/事务到期不归零、旧保护或失败证据漂移、writer运行或未知终态，立即阻止清理/clearance/新派发，不释放其它预约。
- Verification: 实际Linux运行`pytest -q scripts/tests/test_main_mysql_scheduler.py scripts/tests/test_retained_replacement_retry.py scripts/tests/test_backup_variants.py`；再用独立断网、无发布端口、临时数据的真实MySQL核启用事件停写、导入新启用事件仍不执行、失败保持暂停、续恢复继承首次ON和原OFF保持。真实恢复成功后核mysqlSchedulerReleasePin及当前全局状态、全部原数据/对象/业务和其它服务，不将fixture或SET成功当最终验收。
- Forbidden action: 不允许ON通过专用演练SQL检查，不跳过线程归零，不在失败时自动启用调度器，不改旧FAILED/active记录，不新建stateRoot绕过，不删除旧保护规则整体表或操作公司/mnt/nas，不用API代替真实Spug新操作。
- Evidence: `doc/tasks/20261105-spug-full-to-prod/scheduler-retained-recovery-plan.md`、原History361及205文件pins、Linux RED/GREEN/回归、真实MySQL结果、新提交/精确构建安装、正式保护交接clearance及后续真实UI/原生验收。

阶段必查项与推荐命令：安装前保存`SELECT @@server_uuid,@@GLOBAL.read_only,@@GLOBAL.super_read_only,@@GLOBAL.event_scheduler`、`SHOW DATABASES`及原失败/预约pins；仅正式执行器在停写后调用`SET GLOBAL event_scheduler=OFF`并等待`information_schema.PROCESSLIST`的event_scheduler计数和`innodb_trx`计数为0。成功先完成其它保护释放，再精确恢复原状态；释放异常重新暂停并报错。Fail Fast按上述Blocker执行。必须记录原状态、原身份/库范围、意图/active/custody/release pins、真实线程等待结果、原失败保持、新旧操作关联及最后当前状态。真实MySQL容器测试须等待PID1已为最终mysqld，不能以首次初始化临时mysqld的ping作为就绪；--rm删除也须有界确认完成。

## Spug 直接三服策略与普通脚本安装门禁

- Trigger: 用户明确取消三服主流程演练，或切换已迁移的普通脚本执行器及发布页面。
- Preflight check: 记录用户范围；私密配置显式选择`direct-three-server-v1`，正式使用独立恢复必须有明确确认。仅空闲时同步已提交维护代码；先完整校验工作资源包、备份SQLite/私密配置，并确认唯一执行器身份。封存业务包及原资源包不改。每个正式目标使用自身登记起点和只读计划，同包测试成功后升级正式，正式验收开放后再升级审查。升级前结构可以不同；用户要求三服结构一致后，升级后必须对齐同包上游已验收结构，并在新程序启动前、回执、开放验收时强制核对。不能要求业务行或历史台账相同，也不能改旧SQL或补造历史来消除差异。
- 阶段必查项与推荐命令: 代码层运行直接链路、失败恢复责任、目标漂移及UI门禁回归；普通启动器用真实`powershell.exe -File ... -SourceStopped`验证UTF-8无BOM配置，`Get-Content`必须显式`-Encoding utf8`。安装后分别核对执行器实际入口/PID/配置、SQLite payload保持和工作包全清单；读取Nginx唯一有效include/alias并比较实际HTTP `app.js`摘要，不能只核挂载source文件。逐服部署核`operation=SUCCESS`、manifest、真正生效配置、实际镜像、health、HTTP、真实页面登录及保存/运行GxP关闭。
- SQL前停服复查: 停服前绑定真实网页版本、原镜像、配置fingerprint、schema/ledger和计划；停服后先核写入进程全停及fence，再核原镜像/完整fingerprint/schema/ledger。原前端已明确停止时允许网页版本不可读，但绑定版本必须存在；运行中缺版本或任何身份漂移仍失败，不为通过检查启动writer。
- 尝试与失败核销: 每次`promote-prod`独占`attempts/JOB-*`目录，后续检查/验收/核销继承对应部署目录，不覆盖旧责任确认或回执。外部恢复模式仅在原worker终结、无本tag迁移和容器替换、原容器/身份完整一致且旧版健康开放后，才允许`external-pre-migration`原容器恢复核销；明确`snapshotComplete=false/databaseRestored=false`，真实Spug核销保留失败状态。
- 验收来源必查: 执行器迁移到另一台电脑后，停服前运行现有`check-executor-acceptance-ingress`真实nonce探测，分别核验每台目标到当前来源IP的路由、验收端口监听和firewalld精确允许规则。旧电脑可访问不证明新电脑可访问；仅需来源规则时不得关闭防火墙、扩大到整个网段或重载影响现有连接。先保留失败原任务和零副作用证据，再按既有Spug核销/重试入口续办。
- Blocker / Fail Fast: 未授权外部恢复、错包、起点或迁移计划漂移、未知策略、运行中热换、工作包原校验失败、秘密字段变化、UI仍旧版、无真实页面证据均必须停止相应阶段并记录原因。测试任务正在运行时页面禁用属于正确互斥，等待原任务终结，不重复提交。
- Verification: 同一tag闭环；正式external模式不调用全量capture、不伪造recoveryPoint且失败保持关闭，测试/审查检查点能力保留。保存/运行模式均`DEVELOPMENT_DISABLED`、`auditEnabled=false`、无待重启须有实际来源证据，缺字段不能当false。
- Forbidden action: 禁止篡改旧封包/摘要/历史、伪造演练成功、把独立恢复责任确认称为外部备份验证、绕过真实Spug按钮直接改状态、删除旧演练或资料、自动合并int_main、把只读登录称为完整业务回归、打印凭据或为通过检查伪造无效.env。
- 必须记录 / Evidence: 目标提交、维护提交、测试命令及RED/GREEN、原包与工作包校验、实际UI摘要、普通执行器身份、策略采用记录、逐目标计划与任务ID；本次见`doc/tasks/20261031-spug-three-server-release/execution-log.md`及`direct-workflow-install.json`、`direct-spug-ui-sync.json`。
## 完整包、逐目标计划与持久恢复门禁

- Trigger: 构建或部署 `full-app-release/v1`，或处理部署中断、失败重试。
- Preflight check: `intruoyi` 固定 backend/frontend；`full` 另含 Website；OnlyOffice 在构建时决定。核对唯一 manifest、全部制品、来源提交、包双摘要及 tested v2；目标端不能覆盖组件或用工作区模板补包。旧包缺少新合同必须重新构建。
- Blocker: 历史 FAILED/RUNNING、未知状态、摘要漂移、缺控制 schema/工具/持久挂载、未解决 operation、锁内事实变化均拒绝；常规部署不自动准备平台、不补目录/表/存储过程、不重新派发可能写入的失败。
- Verification: 先本地验包，再目标只读采集/目标数据检查/规划，再持久门禁和既有租约锁，锁内重采复核后才能执行 APPLY。SKIP 历史不重写。保存逐目标计划与期望/实际内容身份、配置、完整台账及健康结果；最终化、历史、回执和锁终态全部成功才完成。
- Forbidden action: 禁止源库 dump 覆盖、MinIO 快照导入、重建平台数据服务、自动回滚或清理失败证据；过期 heartbeat 不是恢复授权。标签相同不能替代 imageId/configDigest、静态文件集合及 SHA 校验。
- Evidence: 包外控制目录中的计划；目标 `$RemoteAppDir/.release-state/$Environment/` 的 `gate.json`、`gate.lock`、`operations/<attemptId>.json` 与回执；数据库原 operationId/lease fence。只保留 leaseTokenDigest，日志不保存凭据或租约明文。

### 独立的平台准备（需要后续目标环境明确授权）

1. 核对目标服务器、部署用户/组和正式 RemoteAppDir；持久状态根不能在每版临时目录，也不能在受保护 `/mnt/nas` 共享盘。确认父目录、所有权、0700 权限、备份/保留约定以及受支持控制 schema。
2. 经授权后使用目标配置中的真实值执行 `install -d -m 0700 -o <部署用户> -g <部署组> -- <已核对的持久控制路径>/operations`；占位值禁止原样执行。由部署用户复核属主、可写性、非符号链接，并独立建立同属主可用的 `gate.lock`。
3. 只有核实没有旧 operation/未决恢复事实后，才可在单独的受审准备动作中原子初始化 `gate.json`：schemaVersion=`release-deployment-gate/v1`、revision=0、state=`READY`、attemptId/operationDigest/receiptDigest=null；scope 必须采用真实 environment/host/machineId/database/serverUuid。不能覆盖已有 gate 或用新 READY 遮蔽历史故障。普通发布不会初始化这些文件。
4. 当前容量/存储支持限定可核验路径的 Docker classic `overlay2`；containerd/未知驱动明确拒绝。数据库 1 GiB 是最低预留，不是任意 DDL 足够空间的承诺；按真实迁移增长另行提高并核对所有实际目的文件系统。

### 中断与恢复

先保全包双摘要、目标身份、gate/operation/receipt/历史及数据库锁/完整台账；核实已执行 SQL、配置和容器实际内容、未知观测及原始错误。执行过或可能执行过写入时保持 `RECOVERY_REQUIRED`，不得直接重试或按超时清锁。显式恢复入口 `ops/deploy/recover-release-operation-lock.ps1` 会消费同一持久门禁，仅满足其零运行写入、身份、旧租约与锁内复核条件时才可按后续批准流程执行；它不是自动回滚或数据恢复工具。人工修复、数据恢复或现场 bootstrap 必须另立授权任务。

本任务的本机 MySQL/classic 集成只证明相应 SQL、文件、计划、身份与失败合同；不代表三台服务器旧基线可升级、真实 backend UP、产品 E2E 或远端发布完成。

## 触发条件

当任务涉及以下任一事项时，Codex 必须先读本文，再决定是否进入真实发布动作：

- 运行控制台 `build-release`
- 发布到测试服
- `mark-tested`
- 发布到正式服
- 发布到备份服
- 发布失败后的重试

本文面向 Codex 执行，不替代正式规则。正式边界仍以以下文档为准：

- `E:\IntRuoyi\docs\release-backup-restore.md`
- `E:\IntRuoyi\docs\server-access.md`
- `E:\IntRuoyi\docs\login-access.md`
- 仅测试服发布还必须先读：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md`

## 执行模型

- Windows 发布测试显示100%但JUnit未落盘时，先执行 `docs/powershell-preflight-lessons.md` 的“Python JUnit 收尾与 Windows WMI”检查；缺进程退出码/有效报告不得放行，宿主OOM恢复后重型套件串行运行。

- 发布函数通过 AST 抽取测试时，先执行 `docs/powershell-preflight-lessons.md` 的“AST 测试载体与生产入口前提一致性”门禁，核对真实 UTF-8 初始化、JSON 数组形状及故障注入实际命中阶段；SQL 包含 FAILED 不等于正在更新 FAILED。载体失败不得充当产品 RED 或驱动未经验证的生产修改。

Codex 必须把完整发布任务视为以下严格顺序：

1. `build-release`
2. `publish-test`
3. 测试服运行态验证
4. `mark-tested`
5. `promote-prod`
6. 正式服运行态验证
7. `promote-backup`
8. 备份服运行态验证

以上八步仅适用于用户明确授权的完整发布。仅测试服任务必须以 `docs/test-release-preflight.md` 为范围权威，在第 3 步测试服运行态验证通过后停止；不得执行 `mark-tested`、`promote-prod`、`promote-backup` 或任何正式服、备份服动作。

任何一步失败，都必须先记录真实证据，再修复，再从合适步骤重新执行；不得把不同 releaseTag 的成功结果拼接成一次完成。

## 0. 开始前必做

### 必做动作

- 创建或识别任务目录。
- 读取 `docs/experience-index.md`。
- 命中并读取：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md`（仅测试服发布或 publish-test 任务）
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `E:\IntRuoyi\docs\release-backup-restore.md`
  - `E:\IntRuoyi\docs\server-access.md`
  - 如涉及登录验证，再读 `E:\IntRuoyi\docs\login-access.md`
- 在 `execution-log.md` 先写 `GREEN: experience-preflight -> PASS` 或明确 blocker。
- 在 `docs/request-command-log.md` 记录用户需求与关键命令。

### 放行条件

- 任务目录存在。
- 命中文档已读取并在任务文档写出 `经验门禁`。
- 高风险动作前已有 `experience-preflight` 记录。

### 阻塞条件

- 没有任务目录。
- 没有 experience-preflight 记录。
- 正式服或备份服操作缺少当前任务授权。

## 1. 构建前检查

### 必做动作

- 确认发布源头在 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 确认后端、前端、维护仓三方主分支名、当前提交与 dirty 状态。
- 每次发布一律先创建本次专用的临时发布 `worktree`，禁止直接在主工作区执行构建、验证或发布。
- 必须先核对测试服当前 releaseTag/manifest 与本次目标提交是否一致；不一致时不能复用旧发布结论。
- 必须显式核对 runtime-control 当前 `repo-root` / `frontend-root` 指向的就是本次最新临时发布 worktree，而不是主工作区或旧 worktree。
- 在临时发布 worktree 上先过前端 lockfile / 依赖恢复与后端目标模块构建门禁；未通过时，先提交修复再重建 worktree。
- `build-release` 前先用脱敏/白名单方式核对本地 Docker 可用性和必需容器存在；不得直接打印 `docker inspect` 的完整 env。
- 运行控制台指向 release worktree 后，再查一次三仓 `git status --porcelain --ignored=no`；`state-dir`、logs、operation state 和 cache 不得落在 release worktree 内造成 `dirty=true`。
- 先跑发布门禁或契约测试，尤其是：
  - migration policy gate
  - 影响发布链路的 SQL 契约测试
  - 影响产物契约的发布脚本测试
- required SQL 静态门禁必须覆盖 MySQL 64 字符标识符限制；约束、索引、触发器、过程、函数和事件名超长时必须在 build-release 前失败。
- 运行控制台 `state-dir` 根目录不得放任务自定义证据 JSON；operation 列表只应读取 `op-*.json`，其他证据放入 `evidence/`、`logs/` 或约定子目录。
- 快速、只读、可 fail-fast 的 migration/manifest/脚本契约门禁必须先于依赖恢复、前端构建、Maven 打包等耗时步骤；门禁失败后只停止本任务进程，不继续等待或并发重启无发布价值的构建。
- 确认本机运行控制台是当前版本，必要时重启后再核对。
- 核对构建预览命令包含：
  - `-Mode build-release`
  - `-Component intruoyi`
  - 本次目标 `releaseTag`
- 校验 preview arguments 时必须兼容 `-RequireTested`、`-SkipDatabaseSync`、`-SkipMinioSync` 等 switch flag；不得用简单偶数配对解析。

### 放行条件

- migration / manifest / 脚本契约未报错。
- 本次使用的后端、前端、维护仓输入关系清晰。
- 三仓主分支状态、本次目标提交与临时发布 worktree 路径已明确记录。
- 运行控制台预览命令指向正确 repo-root / frontend-root / scriptPath。

### 阻塞条件

- SQL 缺少 `release-migration` 元数据。
- `dependsOn` 错误。
- 发布脚本仍引用旧产物名、旧变量、旧路径。
- 运行控制台仍加载旧 worktree 或旧逻辑。
- 临时发布 worktree 自身无法通过 frozen-lockfile、依赖恢复或目标模块构建门禁。

### 2026-07-19 r260719k 发布失败复发防止清单

- Trigger: 完整三环境 code-only 发布在 clean release worktree 中执行 `build-release`、`publish-test`、`promote-prod` 或 `promote-backup`。
- Preflight check: `build-release` 前必须同时跑迁移元数据全量门禁、近期 SQL 静态测试、MES companion contract 编译门禁、前端 API export 静态门禁、`pnpm build:test`、Docker CLI/BuildKit 健康检查；required SQL 静态测试必须覆盖结构化 `release-migration`、`dependsOn` 无 `.sql` 后缀、单值 `type`、字符串 collation、动态角色 ID、DCC `OBSOLETE_CHAIN`、`content_key` CAST collation、`system_tenant_package.menu_ids` 扩容顺序。
- Blocker: 出现 `missing release-migration metadata`、`unknown release-migration metadata key`、`dependsOn missing migration`、`invalid type`、MES/前端 companion export 编译失败、MySQL `ERROR 1267`、`ERROR 1644`、`dcc master points to obsolete revision`、`ERROR 1406 Data too long for column 'menu_ids'`，或 Docker build 日志长时间不推进且 Docker CLI/BuildKit 同步异常。
- Verification: 失败时先冻结 operation JSON、脱敏日志、preview 参数、manifest 状态、远端关键输出和失败时间；修复后必须用新的 releaseTag 重新 `build-release`，并在同一 releaseTag 上完成测试服、正式服、备份服运行态验证。
- Forbidden action: 不得手工改测试库/正式库/备份库、手工更新发布锁或迁移状态、跳过 SQL/编译/BuildKit 门禁、复用失败 releaseTag，或拼接不同 releaseTag 的环境结果。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；最终 releaseTag `release-20260719-intmain-codeonly-three-env-r260719k-r1`。

### release worktree 路径长度门禁

- 创建 release worktree 时，临时根目录必须短而稳定；推荐 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><短标识>`。
- 维护仓、后端仓、前端仓子目录优先使用 `m`、`b`、`f`；不要使用完整任务 ID + 完整仓库名的深层嵌套路径。
- 若 checkout 报 `Filename too long`，必须冻结证据、清理已部分创建的 worktree、`git worktree prune`，再用短路径重建；不得继续沿用部分成功的 worktree。

## 2. 构建完成判定

### 必做动作

- 检查 build operation 最终状态。
- 读取 manifest。
- 核对：
  - `releaseTag`
  - backend commit
  - frontend commit
  - `sourceRepos.dirty=false`
  - manifest 中 `branch` 仍是本轮计划分支，且未在构建过程中漂移到新的未计划 commit
- 若任务要求“只发布 Git 已提交版本”，必须把 manifest 视为最终发布输入证明；构建前的 `git status clean` 不能替代构建后的 manifest 校验。

### 放行条件

- build operation=`SUCCESS`
- manifest 存在
- manifest 与本次目标 releaseTag、提交、发布范围一致

### 阻塞条件

- 只看到页面成功提示，但无 manifest
- manifest 与本次提交或 releaseTag 不一致
- `dirty=true`
- 构建完成后 manifest 记录的 commit 与构建前计划值不一致

## 3. 测试服发布与验证

### 必做动作

- 预览测试服发布命令，确认：
  - `-Environment test`
  - `-ServerHost 172.30.30.58`
  - `-RemoteAppDir /opt/intruoyi/runtime`
- 真实写入前检查本地/远端发布进程和 `infra_release_operation_lock`；存在活动发布或 `RUNNING` 锁时阻塞，不与其他任务重叠发布同一测试环境。
- 执行 `publish-test`
- 只读核对测试服：
  - `.env IMAGE_TAG`
  - compose 解析后的 backend/frontend 镜像
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - `release-info.json`
  - `infra_release_operation_lock`
  - operation 最终状态
- 最终判定前重新执行上述运行态检查，确认未被并发任务的新 releaseTag 覆盖。
- 保存或提交发布日志前扫描明文凭据；日志含密码、token、私钥、连接串或 `mysql -p...` 时先脱敏并删除原始秘密日志。

### 放行条件

- test operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- operation 未成功
- `.env` 已变但容器镜像仍是旧版本
- `.env`、compose、实际镜像、`release-info.json` 或 operation lock 指向不同 releaseTag
- 存在其他任务的活动发布进程或目标版本在最终验收前被覆盖
- 待保留或待提交日志含明文凭据
- health 不通
- frontend 不通

## 4. mark-tested 放行规则

### 必做动作

- 只有在测试服验证通过后，才允许执行 `mark-tested`
- 预览和执行 `mark-tested` 时不得传 `targetEnvironment`。
- 必须从 `/restore-candidates` 或真实页面候选中选择 `selectedRecoverySetCandidateId`，不得省略候选。
- 记录 operation ID、结果与 recovery candidate

### 放行条件

- 测试服运行态验证已完成
- `mark-tested` operation=`SUCCESS`

### 阻塞条件

- 测试服未验证就尝试 mark-tested
- 预览返回 `targetEnvironment` 或 `selectedRecoverySetCandidateId is required`
- 手工改 tested 状态代替 action

## 5. 正式服发布与验证

### 5.0 “已测试包发布正式服”按钮入口门禁

- Trigger: 运行控制台新增或使用“发布到正式服务器/晋级正式服”按钮。
- Preflight check: 按钮必须绑定服务端 `TESTED` release workflow、同一 `releaseTag`、package digest、manifest digest、测试 operation/验收证据和服务端正式目标；运行配置必须与本次冻结 worktree 的批准提交、绝对发布器路径和实际文件 SHA 一致。点击后先生成只读 production preview，目标 host/目录/访问开关变化使旧预览失效；再由服务端签发短时一次性授权；确认请求只能携带 workflow/preview/grant/状态版本/幂等键/原因/精确 `PROD`，不得由客户端传 host、path、targetEnvironment、releaseTag 或 evidence path。
- 本地页面审阅前还必须确认运行控制台 mount 自动读取的 overview、release-status 和远端磁盘状态是否触发 SSH；禁写开关不等于禁读，缺少本轮远端只读边界时不得启动该页面 E2E。只用本任务 PID/端口，使用真实测试租户凭据，不能以 admin 只读对照替代权限验收。
- Blocker: 维护 standalone console 或通用动作选择器仍允许手填 releaseTag/目标环境直接调用旧 `/actions` 生产动作；缺少专用 production 权限、preview blockers、执行器字节 SHA、同包双摘要、幂等键、最终运行态证据或 `RECOVERY_REQUIRED` 隔离时，不得放行按钮。
- Verification: Playwright 从真实工作流页面选择 `TESTED` 包，核对 preview checks、摘要、测试验收和确认顺序；最终只在 operation、manifest、正式 `.env IMAGE_TAG`、实际镜像、backend health、frontend HTTP、页面版本和生产锁全部一致时显示成功；不自动执行 promote-backup。
- Forbidden action: 禁止把旧 generic `promote-prod` radio/手填包入口当成新按钮；禁止 API-only/mock 代替真实按钮路径；禁止在派发或写入不明后释放生产隔离或允许普通重试；禁止重新构建已测试包。
- Evidence: `doc/tasks/20260918-prod-promotion-button-design/`；应用候选 `IntRuoyiFronted/src/views/infra/runtime-control/index.vue` 与 `RuntimeControlController` 的现状审计；维护 standalone `frontend/src/App.vue` 的 generic action 风险审计。

### 必做动作

- 预览正式服发布命令，逐项核对：
  - `-Environment prod`
  - `-ConfirmText PROD`
  - `-TestOperationId`、`-TestOperationEvidencePath`
  - `-ExpectedPackageDigest`、`-ExpectedManifestDigest`（与 TESTED 工作流相同）
  - 目标 host、目录、数据路径、MinIO 参数
- 执行 `promote-prod`
- 只读核对正式服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- prod operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 正式服未带 `PROD`
- 正式服缺少 TESTED 测试 operation/evidence 或工作流批准双摘要
- operation 未成功
- `/mnt/nas`、数据盘、MinIO、挂载状态异常

## 6. 备份服发布与验证

### 必做动作

- 预览备份服发布命令，逐项核对：
  - `-Environment backup`
  - `-ServerHost 172.30.30.59`
  - `-RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases`
  - `-RemoteDataRoot /mnt/intruoyi-data/runtime-data`
  - `-RemoteDataDiskMount /mnt/intruoyi-data`
  - `-RemoteDataDiskDevice /dev/mapper/cl-home`
  - `-RemoteMinioContainer intruoyi-minio`
- 执行 `promote-backup`
- 只读核对备份服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - 数据盘挂载
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- backup operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- `/mnt/intruoyi-data` 挂载正确
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 备份服未显式使用 `/mnt/intruoyi-data`
- 备份服误继承 Docker 根目录路径或正式服参数
- operation 未成功

## 7. 失败时的排查优先级

Codex 必须按这个顺序排查：

1. migration / manifest / required SQL 契约
2. 维护仓发布脚本与业务仓产物契约
3. 运行控制台当前加载版本
4. 测试服 / 正式服 / 备份服环境状态

禁止在第 1、2 层未排干净前，直接把问题归因到服务器。

若失败点在 required SQL：

1. 先只读回查真实库状态、主键占用、历史数据与 tenant 范围
2. 再决定修 SQL、修迁移契约还是修发布脚本
3. 禁止手工改测试库绕过发布门禁

## 8. 2026-07-01 新增前置门禁

### 发布输入与 releaseTag

- 修复任何发布 blocker 后，必须重新执行 `build-release` 并生成新的 `releaseTag`。
- 禁止用旧失败包继续 `publish-test`、`mark-tested`、`promote-prod` 或 `promote-backup`。
- 禁止拼接不同 `releaseTag` 的测试服、正式服、备份服结果。
- `build-release` 成功后必须复核 manifest 中 backend/frontend `commit` 与 `dirty=false`。

### 测试服参数

- `publish-test` 预览必须显式核对测试服真实参数：
  - `ServerHost=172.30.30.58`
  - `RemoteAppDir=/opt/intruoyi/runtime`
  - Docker root 不得误套备份服路径
  - 数据盘设备、MinIO 容器名必须与 `server-access.md` 一致
- 如果预览中出现备份服或正式服参数，必须先修正维护控制台配置、脚本或文档，不得继续真实发布。

### required SQL 与真实库基线

- 发布前对新增或改动的 required SQL 做可重入检查，重点检查：
  - `ADD COLUMN` 是否有存在性保护
  - 菜单插入是否有冲突检测
  - 角色绑定是否兼容真实角色编码
  - 租户包与菜单权限是否同步
  - DCC 分类、编码、字段长度和唯一性是否有前置校验
  - 被后续迁移重命名的 legacy 表是否有双表或 `table exists` 守卫，尤其是 `mes_pro_route_use_process_batch_record` 与 `mes_pro_route_use_process_batch_record_legacy_20260709`
- SQL 依赖角色、菜单、租户或账号时，先只读查真实库，不能只按历史角色码或文档推断。
- 如果真实库基线不满足 SQL 契约，必须阻塞并修 SQL/迁移/数据契约；禁止手工改测试库帮助发布过关。

### DCC promote 前检查

- `promote-prod` 前必须对正式服 live data 做只读 DCC 质量预检。
- 至少覆盖分类重复、分类编码缺失、字段长度超限、必填关系缺失。
- 任一 DCC 质量预检失败时，不得推进正式服发布；失败 releaseTag 只保留为排障证据。

### 自动经验候选

- 发布类 operation 完成后必须生成 `runtime/runtime-control/release-experience-candidates.md`。
- 候选内容至少包含 operationId、action、environment、releaseTag、status、summary、候选前置经验和关键日志摘录。
- 如果候选文件缺失，任务收口不得视为完成；如果运行控制台写候选失败，operation 必须 fail fast。
- 任务收尾时读取候选文件，将稳定、可复用经验正式写入 `release-build-preflight-lessons.md` 或本清单。

## 8.1 2026-07-03 不带数据发布新增前置门禁

### code-only 不跳过 SQL

- `code-only`、`-SkipDatabaseSync`、`-SkipMinioSync` 只表示不携带业务数据和文件，不表示跳过 schema、required SQL、migration 或字段约束变更。
- 不带数据发布在 `build-release` 后仍必须核验 required SQL、migration 门禁和真实库约束变更结果。

### DCC lifecycle_stage / NOT NULL

- DCC 分类 `lifecycle_stage` 或任何字段改为 `NOT NULL` 前，必须先查全表空值，不能只查 `deleted=0` 活动行。
- `deleted=1` 历史归档行同样会阻塞 `NOT NULL`，必须在可重复 SQL 中定义归档归一化规则和注释。
- required SQL 报 `Invalid use of NULL value` 时，先只读按 `deleted` 等关键维度统计空值分布，再修 SQL、迁移顺序或数据契约；禁止手工改测试库绕过。

### 远端 MySQL 查询

- 测试服业务库名以真实容器为准；当前确认业务库为 `ruoyi-vue-pro`，不得默认写成 `yudao_ruoyi`。
- MySQL root 密码必须在容器内展开，优先使用 `docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro'` 并通过标准输入传 SQL。
- PowerShell、SSH、sh、mysql 多层引号失败时，改用标准输入、临时脚本或 here-doc，并记录 `$LASTEXITCODE`；不得把查询失败误判为数据库无数据。

### runtime-control 配置

- 修改 `runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 后，必须回读确认 YAML 缩进、实际路径和 `http://127.0.0.1:48181/actuator/health`。
- 配置指向临时发布 worktree 后，收尾前必须恢复稳定主路径，或明确确认该 worktree 不会被删除。
- 运行控制台启动入口以维护仓当前脚本为准；本轮确认入口是 `scripts\start.ps1`。

### no-data manifest

- 标准一键 without-data 发布必须验证 manifest `publishScope=app-release`；历史 `code-only` 只作为旧链路兼容术语，不得作为新 workflow 放行条件。
- 发布包不得包含 `database`、`db-dump`、`mysql-dump`、`minio`、`files`、`runtime-data`、`data`、`docker-build-context` 等数据目录。
- 允许存在 `required-sql`、`resources`、`runtime-env`、`smoke` 等代码发布必要目录；operation `SUCCESS` 不能替代 manifest 与目录检查。
- `target-data-preflight.json` 等目标服务器证据不得写入不可变包；`ops-runtime` 不得携带 `backup-ops.config*.json`、secret 示例或 `manage-int-ruoyi-remote-root-disk.ps1` 等 target-bound 文件。

### promote-prod 目标库迁移依赖

- Trigger: 对测试服已验证包执行 `promote-prod`，尤其是 `publishScope=code-only`。
- Preflight check: 在任何远程应用容器切换前，必须针对正式库生成 target-bound `preflight-plan.json`，检查 `status=passed`，并展开所有 `BLOCKED_SCOPE_DEPENDENCY` 的依赖链。
- Blocker: code-only 不代表跳过 schema/required SQL；正式库缺失依赖、依赖路径被 scope 排除或 checksum 不一致时必须 fail fast，不能把预览 PASS 或旧容器健康误判为新包可发布。
- Verification: 失败后确认正式服 `.env`、实际容器镜像、backend health、frontend HTTP 和 release lock 已恢复/保持发布前状态；记录失败 operation 与恢复动作。
- Forbidden action: 禁止手工补迁移、更新迁移状态/lock/tested、修改已构建包或用 `-SkipDatabaseSync` 绕过 scope dependency。
- Evidence: 保存 target preflight report、operation 日志、远端旧运行态检查和下一次放行前的依赖修复证据。

## 9. 完成判定

Codex 只有在以下条件同时成立时，才能判定完整发布完成：

- 同一 `releaseTag` 已走完 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`
- 五个 operation 都有明确结果证据
- 测试服、正式服、备份服三环境都已验证：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health=`UP`
  - frontend HTTP=`200`
- 任务日志与请求命令日志已回写
- 发布和运行态验证完成后，任务先进入 `ready_for_closeout`
- `task-closeout-cleanup` preview/apply 已通过，`verification-report.md` 位于默认 keep 集
- 所有临时 worktree 的 Git 注册和物理目录均已清理，运行控制台已恢复稳定主路径
- 只有上述 closeout 证据全部通过后，任务状态才更新为 `completed`

任何缺项都不得宣称“完整发布已完成”。

## 8.2 2026-07-11 仅测试服发布补充检查

### publish-test preview 稳定性

- 对单一 releaseTag 发布，先直接校验目标 manifest，不让候选包全量扫描成为唯一门禁。
- preview/submit 任一步导致运行控制台断连且无 operationId 时，必须记录失败并停止；不得把脚本执行或旧 operation 当成本次成功。

### 运行态验收

- 测试服成功判定必须同时具备：build operation SUCCESS、publish-test operation SUCCESS、manifest sourceRepos clean、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health UP、frontend HTTP 200、`release-info.json`、运行控制台 release-status、真实页面版本对话框。
- 运行控制台有历史 dead RUNNING operation 时，必须证明它不是本次 releaseTag 且不占用发布锁；否则阻塞。

### PowerShell/SSH/Playwright

- Host:port URL 用 `${hostIp}` 写法。
- bash `$()`/`||` 不放入 PowerShell 双引号。
- Playwright 先检查模块与浏览器路径；可用已安装 Chrome/Edge，不在发布验收中临时安装浏览器。
- 同一 Playwright CLI 会话的 `open/resize/snapshot/click/find/console/close` 必须串行执行；出现 `ECOMPROMISED Lock compromised` 时本轮组合结果不可放行，改为串行重验并取得页面字段与 console errors=0。
- release-info 中文说明以 UTF-8 parser 或浏览器页面为准；PowerShell mojibake 只记录为采集问题。

### 独立探针与稳定控制台收尾

- 远端数据库探针必须先从冻结 migration 和真实库 `DESCRIBE` 确认表/字段；容器未定义 Docker healthcheck 时只核 `state=running`，应用健康必须独立核 Actuator HTTP 200/UP。
- 删除 release worktree 前，48181 PID/命令行/JAR 必须指向主维护路径，完整 `/admin-api/infra/runtime-control/release-status` 必须显示目标 tag、notes 和 changes；只看 health=UP 不足以收尾。
- 同 HEAD 重新构建的 Spring Boot JAR 可能因归档元数据产生不同 hash；必须记录并验证本次实际产物 hash，不得用历史重建 hash 作为当前复制/恢复门禁。
- 外部 release worktree/state 先按 `E:\IntRuoyi\docs\worktree-memory.md` 验证 Git 注册、物理路径、进程和 allowlist 后清理；再运行仓库内 task-closeout preview/apply，禁止绕过 workspace 边界。

## 8.3 2026-08-31 code-only target plan 与历史 ADD COLUMN 幂等门禁

### publish-test 提交前

- 最终 manifest 生成后，先针对测试服当前 target state 运行 `release_preflight_plan.py`；必须 `status=passed`、`BLOCKED*=0`，并记录 APPLY/SKIP 数量和目标 migration action。
- 校验 manifest 的 `requiredSql`、`migrationPlan`、`database.schemaMigrations` 三份投影对同一 migrationId 的 type/dependsOn/sha256 一致。
- 对 APPLY 中的历史 `ALTER TABLE ADD COLUMN`，只读查询 live `information_schema.COLUMNS` 与 ledger；列已存在但 ledger/checksum 不一致时，SQL 必须逐列可重放。
- 以上 gate 必须在远端 `.env IMAGE_TAG` 修改、镜像上传和 release lock 获取前通过；当前脚本若尚未自动前移，Agent 必须手工完成并保存结构化证据。

### Fail Fast

- `BLOCKED_SCOPE_DEPENDENCY`、schema 依赖 scope-excluded data、裸多列 ADD 命中已存在列、target state 过期、manifest 三投影不一致、或 `.env` 已改但 actual image 未切换。
- 失败 tag 立即判废；禁止 with-data/手工 SQL/ledger 修改绕过。修复需独立 worktree、严格 TDD、提交融合、新 releaseTag 重建。

### 发布后

- 核 lock=APPLIED、FAILED/RUNNING=0、target migration APPLIED/checksum；`.env`、compose/actual image、containers、health、HTTP、release-info、release-status、Playwright 和 final gate 全通过。
- 运行控制台发布标签输入框可能有历史默认值，preview/submit 必须始终显式传入并结构化核对本轮 tag，不得信任 UI 默认值。
- 日常 backend `build-release` 在 Maven 前必须完成 schema-only 临时库迁移演练；不得复制完整业务数据或 MinIO。最终计划中的非 schema APPLY 必须存在 `sql/mysql/target-preflight/<migrationId>.preflight.sql`，通过只读合同校验和测试服只读断言；缺失或失败即废弃 releaseTag。
# 发布验收后旧载荷回收门禁

- Trigger: 完整包三服最终验收或前端补丁三服最终验收成功，自动回收旧包和旧恢复资料。
- Preflight check: 同一版本最终验收成功；三服真实主版本/补丁、镜像和健康/开放状态一致；无本机并发运行任务；远端公共操作锁、活动执行器和每个文件的挂载/链接/设备/归属/SHA复核通过。使用 `post_release_cleanup.py` 与 `artifact-auto-clean`，不按目录年龄盲删。
- Blocker: 发布未完成/验收失败、版本漂移、维护/恢复未结束、远端进程/锁冲突、摘要/归属不明时不删对应载荷；清理失败需核对原回执，不把发布验收改成失败或伪装清理成功。
- Verification: 核对 `postReleaseCleanup` 和 `.cleanup/<任务>.json` 的具体计划、逐项删除、保留原因、错误和文件字节/磁盘可用变化。先移除有原始快照及精确身份的已停止旧业务容器，再删无任何容器/恢复点引用的登记镜像标签，最后处理旧载荷。失败现场须原任务 restored 核销、本机成功恢复验收及远端 opened 回执三方一致；接续验收绑定原 openingJobId。推荐运行 `test_post_release_cleanup`、`test_runtime_resource_cleanup`、Linux `test_post_release_cleanup_lock`，本机专用 Docker 资源用 `SPUG_REAL_CLEANUP_TEST=1 ... test_cleanup_resources_integration` 验证。必须记录代码版本、任务号及逐服实际结果，清理失败通过独立重试入口重新采样，不重新发布或开放业务。
- Forbidden action: 不删当前包及最近有效恢复点、在用演练、未解决任务的恢复起点、清单/凭据/历史、业务在用数据、NAS、独立备份链；不自动停业务容器，不带卷删除容器、不强制删镜像、不全局 prune、不递归删除、不在有活动发布时热换执行器代码。未知归属的历史演练必须另行确认退役后处理。
- Evidence: `doc/tasks/20261102-post-release-auto-cleanup/`、发布最终验收任务日志和逐服清理回执。
## 原MAIN前端网络与继承停写门禁

- Trigger：原前端回环登记配合宿主网络/动态bridge，或已消费续办在写前失败。
- Preflight check：恢复前先解析所有语义健康端点。host前端通过owner层frontendReadiness/v1绑定原容器、完整配置摘要、只读nginx配置pin和明确IPv4/端口，核原配置的精确listen；bridge前端只取登记且唯一的固定IPv4附加网络，核原网络身份与80/tcp声明。所有历史targets保持。写前续办先证实原native全部mutation=false、无replacement-intent/importer、实际exit1及正式no-mutation释放，再核精确消费和前次clearance、同点同目标、全服务id/image/running/StartedAt与表数/UUID一致；若继承scheduler custody，验证原暂停状态并继续传递。
- Blocker：原身份/配置/挂载/端口/网络漂移、地址歧义、未知模式、原文件未固定、消费关系或前次观察变化、调度器保护无法验证、活动worker/预约，均停止对应操作。
- Verification：真实Linux运行test_main_readiness.py、test_retained_replacement_retry.py及封包/MAIN/调度器回归；安装前实际新进程解析两服全部端点，运行服务实测协议，停写服务不为预检而启动。完成恢复后核原生语义健康证明、实际HTTP及业务页面。
- Forbidden action：不默认所有前端用127.0.0.1:80、不猜nginx第一个监听、不把running当healthy、不改历史targets摘要、不为无写续办启动尚未验收writer、不重复提交原失败或删除预约/失败记录。
- Evidence：doc/tasks/20261106-spug-prod-incremental-to-two-targets/main-frontend-readiness-plan.md、main-health-endpoint-58.json、frontend-readiness-candidate-58.json、inherited-quiescence-candidate-58.json及RED/GREEN/REGRESSION原始日志。

阶段必查项：只读原配置与失败原件 -> BDD/RED -> 实现及完整回归 -> 限定提交/新专属精确构建 -> 原件完整SHA及仅控制安装 -> 正式续办 -> 新鲜准入/真实Spug单次提交。推荐命令：docker inspect精确原id、读取已pin nginx配置、候选只读endpoint解析、verify_no_mutation/inherited_quiescence/observe、实际语义HTTP探测。Fail Fast按上述Blocker；必须记录真实网络模式、endpoint、文件与配置SHA、各失败操作及消费关系、原服务状态、实际退出/写标记、测试原始失败与新安装代次。

## 授权控制升级的活动回执历史保全

- Trigger: 控制升级轮转target-installation.json，且原历史不变清单包含该活动回执。
- Preflight check: 固定原清单、唯一活动回执pin和明确授权的全部安装报告；逐代核previousReceiptPin/currentReceiptPin字节身份，首个归档必须等于原清单pin，最后活动回执必须等于当前选择的实装。全量读取历史owner/control及dropin pins，核来源、目标定义不变。
- Blocker: 缺失/乱序安装、任何pin不符、归档到活动链断裂、未知激活、来源/目标漂移，或其它原历史路径变化。
- Verification: 对除唯一活动回执以外的全部原路径逐SHA核对；对活动回执验证原字节归档及每代完整链。分别记录原文件数、原字节总数、不变路径数、授权活动回执数、代数；原生验收和收尾都必须实际通过。真实只读输入上验证缺失、篡改、乱序均拒绝。
- Forbidden action: 不重写原清单、不泛化排除活动文件、不丢弃失败原件、不把授权变化路径宣称原路径不变、不用安装报告代替真实归档字节读取。
- Evidence: doc/tasks/20261106-spug-prod-incremental-to-two-targets/installation-history-custody-plan.md、history-receipt-custody-red.json、history-receipt-custody-green-58/59.json及protected-history-custody-preflight-58/59.json。

阶段1安装前：必查原清单和完整授权代次；推荐读取每个回执的size/SHA及owner/control绑定；原始基线只读保存。阶段2安装后：只读逐代读取归档和当前原件，精确核首尾及相邻字节、定义和配置pins，任何Blocker立即停止验收。阶段3最终收尾：在全部业务操作结束后重跑完整历史和回执链验证。必须记录各阶段时间、真实命令、原始失败、原清单身份、具体变化路径及两类保全结论；此审计问题可前置并由严格pin链自动核验。
