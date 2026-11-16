# 私密安装准备

目标：只读核实 .59 与 Spug，形成可供父任务审查的真实配置和安装载体；不执行服务器写入、清理或恢复。

里程碑：读取真实配置及活动任务；生成保留路径与精确清理配置；交付父任务安装。

经验门禁：UTF-8；读 server-access/release-backup-restore；只连接 .59，凭据不输出、不提交；保留 NAS、工具、Docker 根；高风险写入由父任务另行记录并执行。

设计约束检查：无 fallback/吞异常；复用现有引擎和接口，长期维护；无临时绕过。

状态：ready_for_parent_review。仅只读服务器核实及本机私密载体准备，未执行安装/删除/恢复。

## 证据与交付
- .59 实际 201 个容器，数据盘可用 131019137024 字节；共享恢复 active.json 不存在，进程核实仅旧控制服务，无恢复/仓库 worker。
- 三个原有备份点（full 3c2395、I1 20a1bb、I2 e7b668）及映像包元数据可读；未重扫附件内容。
- 生成私密配置：固定新工具 `/mnt/intruoyi-data/recovery-tools`、状态 `/mnt/intruoyi-data/recovery-preparation`；保留现有 Python/引擎/小配置依赖 home，精确清理 84 目录、201 容器、97 普通卷及旧专用网络。NAS 保留。
- 依赖路径祖先比较 43379 条，清理交集为零；Python 1048 个 symlink 的目标与删除目录交集为零。新网段已有旧演练网络占用，该网络 ID 已包含明确清理集合。
- 安装载体 `C:/Spug/runtime/private/spug-backup59-mvp-20261116/install59.py`：要求本次已提交发布 checkout，从 Git HEAD 读取 native；写入前 machine-id/源目录检查，复制完整 Python/engine，写配置后执行新 Python --version。载体不执行清理、初始化、恢复或服务重启。
- 交付配置/观测/边界核对位于同一私密目录，不提交。`py_compile` 本地载体通过。父任务负责最终 review、部署和真实页面验收；未伪报 READY。

## 父安装后的只读核对
- 父任务安装回执已生成后，使用实际新 Python 和已安装 native 执行 full3c2395 的 preview，返回 PASS；没有 execute。
- 从实际 Spug 容器读取 entry/simple/bridge 与旧 .59 路由，生成本机待安装 prepare-target.private.json，引用既有认证文件，不复制凭据正文。安装命令交于私密 spug_live_install.md；子任务未修改运行容器。

## 必要网络依赖
- 经父任务明确派发、execution-log GREEN 后，向 .59 public zone 增加仅来源 192.168.109.82/32 的 tcp43059 rich rule；runtime/permanent 均 query 成功，未 reload、未关闭防火墙或修改其它规则。
- 新控制服务尚未由页面准备启动，端到端连通仍待父任务页面操作后确认。证据 firewall43059-installed.private.json。

## 全量恢复后的验收入口准备（仅只读，未执行登录或恢复）
- 当前 native 配置 frontendPort=18089；frontend 仅绑定服务器 127.0.0.1:18089→80。backend 内网 172.29.238.35:48081、MinIO 内网 172.29.238.33:9000，均无宿主公开端口。验收复用 SSH 将本机 127.0.0.1:18089 转发至 .59 的 127.0.0.1:18089，不需额外开放应用端口。
- 现有登录凭据文件 C:/SpugHandoff/release/private/loginCredentials.json 存在，用户标签为芋道源码/admin，密码字段存在但未输出；恢复后的实际有效性尚待真实页面确认，失败不猜测或重置。
- 可复用 C:/Users/D01021/Documents/ChatGPT/Maintance/doc/tasks/20261106-spug-prod-incremental-to-two-targets/verify_business_ui.cjs 的真实登录及用户管理只读列表流程；须将硬编码旧 .59:38081 改为本机转发入口后运行，不能直接执行旧脚本。只允许登录/验证码 POST，其余业务写入阻止。
- 附件入口 /infra/file/file。旧 watch57-target-business.cjs 展示页面首屏附件响应字节/SHA256观察方式，可复用方法，但旧目标、9074总数与旧20条基线均不能用作本次 full3c2395 的期望值。最小验收取本次全量点对应少量附件清单，确认列表存在、实际附件 HTTP200、字节数/摘要匹配；不扫全部附件。
- 实际模板 nginx.published.conf 的 /admin-api/ 指向 backend:48081，/yudao/ 指向 MinIO:9000；源 .57:9000/yudao URL 在响应中改为当前前端同源 URL。native 初始化会把旧容器 IP 换成新内部 IP，数据库 URL 不变。验收必须确认附件请求来自新目标同源路径，避免误读源服务器。
- 缺口：当前还未生成新目标，未确认实际登录、业务数据与附件成功；本次全量点的少量附件基线需在恢复选定点确定后取元数据，旧演练基线不可替代。

## 准备配置的备份点键修正
- 父任务真实页面发现三点选项 value 为 backupId（smallapp-*）。本子任务生成器错误地使用 capture.recoveryPoint（sha256:* 数据一致性标识）作为 native.points 键；此前 native preview 仅证明内部配置自洽，不证明 UI 选择契约一致。
- 三份 point.backupId 与 capture.backupId 一一相同：FULL=smallapp-3c2395ff88bd474e9fc007649565b848、I1=smallapp-20a1bb9b78ac402693289675d16c63dd、I2=smallapp-e7b668792c8f4bce945a52f984d3c660。不是备份缺失或源目录错误。
- 已修私密生成器及 preview 请求；精确修正载体 fix_point_keys.py 的只读 dry-run PASS。载体仅替换远端 native.points 三个键并更新本机配置 pin，不修改备份载荷、不执行准备或恢复；已交父任务审查，尚未执行 apply。

## full3c2395 最小验收基线
- 已从该全量点归档现有 011-source-data.json 与 references.json 读取证据，并对这两份小型元数据核对原 pin；未读取/解压 SQL 或对象载荷，服务器零写入。
- 私密基线：C:/Spug/runtime/private/spug-backup59-mvp-20261116/full3c2395-acceptance-baseline.private.json；可复用采集脚本 prepare_full_baseline.py。这次独立采集确认为 infra_file=9074、system_users=2155、system_tenant=4、mes_pro_work_order=19091、mes_pro_batch_record_execution=53、mes_pro_batch_record_template=11、dcc_product_catalog=213、erp_product=15996。
- 上述为备份时全库物理表计数，不是租户过滤/逻辑删除过滤后的页面总数，不可强制拿页面总数逐一相等。真实页面只读验证登录、列表存在及少量记录；必要时最终只读校验再使用对应全库计数。
- 从该点 references.json 中选取 config_id=28、未删除、元数据与 yudao 对象对应的两个 JPEG 和一个 PDF，共1086960字节。私密文件保存真实记录ID/路径/字节数/SHA256及前端同源路径；没有复用旧20条样本，未请求附件载荷。恢复后从 /infra/file/file 搜索对应文件并观察真实页面下载/图片响应，与这三项比较即可。
- 基线只能证明备份中预期内容，尚未证明恢复成功；目标附件需实际同源返回200并匹配字节/SHA256。

## 首次真实 prepare 清理失败定位（只读）
- 操作 prepare-8ae30807-c31d-4682-b245-a1d5ac2291e7 停在配置 volumeNames index28：intruoyi-prod-nas-restore59-20261020-native-minio。当前旧容器已为0、前28个配置卷已删、配置卷剩69；网络与目录清理尚未开始。
- Docker daemon 2026-11-16 02:13:45 +08 明确错误为删除该卷 _data 时 device or resource busy。findmnt 与 /proc/self/mountinfo 证实该目录是 OS bind 挂载，源为数据盘 /prod-nas-restore-prep-20261020/native-target-data/minio。Docker卷 Options=null 并不能证明没有 OS 挂载。
- 同一配置中仅这组 minio/mysql/redis 三个卷 _data 有这种挂载，分别指向 native-target-data/minio、mysql、redis；/etc/fstab 无这三个目标的条目。未重试删除、未卸载、未改资源。
- 最小修正建议：正式配置显式列出这3个旧目标bind挂载，清卷前核对目标与来源后正常卸载，再执行原volume rm；保留实际数据来源目录和NAS，不使用force/lazy卸载或泛化清全部挂载。命令失败应返回安全的动作/对象/exit及截断错误摘要，避免只有generic error。
- 私密证据 cleanup-failure-position.private.json、cleanup-failure-volume.private.json、cleanup-failure-mounts.private.json。

## v5 精确挂载配置及安装载体
- 父任务授权上述3个旧本地bind纳入清理，已与实现agent约定 cleanup.bindMounts 每项 target/source。generate_config.py 已同步；prepare-target59-v5.private.json 仅比当前配置增加这3项，不重新枚举或扩大清理范围。
- update_native_v5.py 要求指定 clean 发布checkout及完整提交hash，从 Git HEAD 取 native；默认只读 preflight，--apply 才写入。先核远端/Spug现有pin及机器标识，再逐文件原子替换 native/config，更新本机receipt/配置两pin，docker cp Spug私密配置并回读。无Python/引擎复制，无卸载/删除/恢复调用。
- 载体语法验证PASS；等待实现提交及 release-v5 固定输入后执行只读preflight，父审查后才执行安装。
- release-v5 已固定提交 8beac1a8529daf426bfbfa3663a7898a40eff091，路径 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v5。update_native_v5.py 不带 --apply 的只读 preflight PASS：clean HEAD、当前远端及Spug两pin、machine-id、仅3bind配置差异均符合。新native预期36693字节、新配置49754字节；未执行安装。

## v6 控制客户端白名单修正
- 父执行v5后，prepare-4a8d0c7c-ade9-4d80-ac06-5424e8715f9b 三阶段均成功，新目标 spug-empty59-733c9c2fe019；发布受理报 TRANSPORT_CLIENT_FORBIDDEN。
- 只读证实 control.json 的监听地址已为172.30.30.59:43059，但 allowedClientAddresses 仍从旧template继承127.0.0.1；既有authCredentialRef未变化。
- 父批准真实Spug容器短TCP连接观察；容器0c578f706938连接8秒，远端ss证实peer=192.168.109.82、控制服务PID15463。无HTTP请求或凭据发送。
- 与实现agent约定control_document从setting.allowedClientAddresses写入生成配置；私密生成器及prepare-target59-v6.private.json仅加入control.allowedClientAddresses=[192.168.109.82]，不改认证、不放行网段。
- update_native_v6.py沿v5最小载体，仅替换native/config并更新pins；语法PASS，等待正式提交/release-v6后只读preflight。父会通过新页面prepare，不手改失败实例或READY。

## v6 生成控制服务的导入错误定位
- 父执行v6并真实prepare-339744c6-76c7-427e-9f16-71828ffa314f三阶段成功；发布阶段变为 SMALLAPP_MODULENOTFOUNDERROR。
- 用实际新control pin仅调用 selections 的诊断trace确认缺失模块为 jsonschema：recovery_control_smallapp_native.selections → recovery_program_evidence → recovery_engine import。服务journal没有保留Python异常细节。
- 既有jsonschema存在于保留目录 /mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07/source/smallapp-20261014-r1/installation-r2-redis/context/runtime/lib/python3.12/site-packages；config.environment.PYTHONPATH已引用该目录，但新systemd unit未给控制服务设置此环境，实际PID17384环境无PYTHONPATH。
- 只在独立诊断进程sys.path加入新engine control/common/formal及该已有site-packages，使用同一真实control pin调用 selections 返回PASS。没有新组件安装、准备/清理重试、配置或状态写入。
- 建议修正正式服务生成阶段传递已配置的运行路径环境；不能仅修失败实例或绕过导入。证据 v6-import-failure.private.json、v6-import-trace.private.json、v6-import-existing-path-proof.private.json。

## v7 仅 native 安装准备
- 已向实现agent确认实际control.environment仅LANG、PATH、PYTHONDONTWRITEBYTECODE、PYTHONPATH四键；此次control导入必需PYTHONPATH，既有四段全部在保留目录内。没有凭据环境值输出。
- update_native_v7.py已准备，语法PASS。固定clean提交输入，先核现有远端/Spug两pin与机器标识；--apply仅原子替换native脚本、更新本机receipt和Spug nativeProgramPin并回读。nativeConfigurationPin/配置文件内容不变，不复制engine/Python、不重载entry、不清理目标。
- 等待正式提交和release-v7固定输入后执行只读preflight，交父审核安装。

## v7 真实 systemd 219 环境文件解析问题
- 父安装v7后新prepare-a1b08336-e0eb-4c5e-8003-5109d19d7516三阶段成功，发布仍报ModuleNotFoundError。只读实际PID19546的环境确认仍无PYTHONPATH/PYTHONDONTWRITEBYTECODE；同一真实control pin的selections trace仍缺jsonschema。
- control.env存在、527字节、四个物理行及四个预期键，未写成字面\\n。根因由journal明确指出：EnvironmentFile中的双引号被systemd 219视为路径字符，Path '"/mnt/.../control.env"' is not absolute, ignoring。并非原环境目录或jsonschema未保留。
- 最小修正是生成systemd 219可接受的EnvironmentFile绝对路径（当前路径无空格），保持依赖/配置/认证不变；已告知父和实现agent。不安装组件、不修改服务器或重试清理。
- 证据：v7-import-trace.private.json、v7-environment-diagnosis.private.json。

## v8 最小载体准备
- update_native_v8.py沿用v7的仅native+对应pin更新方式，配置保持原样；语法PASS，未apply。等待实现正式提交及release-v8，仅做只读preflight并交父执行，不重新盘点环境、不自行prepare。
- release-v8固定f3eb4b5271b56a4d119e22066070f7f5ca8d5cf5后，只读preflight PASS：clean提交、remote/Spug现有pin、machine-id均相符。新native37805字节，配置仍49819字节及原pin不变；applied=false，命令已交父审核。
- 父任务随后审核并执行v8 apply，exit0，native sha256=22b3f9b5a0df6b0456d2c9d957cc8d6b3d805db915c204a07d17d8b721c87fb1，配置原样。安装成功，等待父任务真实页面prepare验收；子任务不重复安装或预检，载体保留。

## v9 本机全量提交门禁安装准备
- 父确认v8真实READY成功；全量提交被本机旧source历史门禁拒绝，未派发恢复、空目标未消费。实现agent负责正式修复，子任务仅准备发布与安装载体。
- 已读worktree-memory：本轮新建独立release-v9 checkout，固定本轮正式提交；只从已提交内容生成精确产品文件payload，保留live其它文件。记录路径/提交/命令/验证/新提交及最终收尾，不重用旧release。
- 安装前核entry PID897及父PID1、无entry子进程/准备worker；仅替换本轮实际变更文件，SIGTERM该entry由既有supervisor拉起，并核新PID及HTTP401。子任务只preflight，父审核后apply；不重做远端prepare。
- 设计约束：无fallback/吞异常、无临时绕过；正式修复与精确更新可持续维护。当前等待实现正式提交。
- 已新建release-v9：C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v9，分支codex/spug-backup59-mvp-release-v9，固定HEAD f6ffee15b9f7a2a27b127c72bb7e1700dad1008c，clean。该发布worktree没有新提交；最终融合/删除由父统一收尾，当前保留。
- 构建载体：从该HEAD git show仅提取ops/spug/prepare_target.py及smallapp_entry.py到entry-v9-payload，两文件compile PASS；生成entry-v9-plan.json与apply_entry_v9.py，保留其它live文件。
- 验证命令：python -X utf8 .../local-install/apply_entry_v9.py（不带--apply）返回preflight PASS；entry897/PPID1、prepareRows5、activePrepare=false、无entry子进程，9项live基线与2项payload hash符合。父审核安装命令已交付，子任务未apply。

## 首次全量真实运行与进度读取
- 父安装v9成功，entry897→1395；UI提交smallapp-c7107c08b98a457caef62280e9a7a04c真实202受理，目标spug-empty59-9ad0f898afb1。子任务只读观察，未重启/重提/清理。
- 实际进程21493→22698→22808→22819，最终recovery_minimal_worker运行；19:25:58Z开始restore-admission。读取/proc显示worker正在读取选定归档内minio-physical附件，rchar从约11.16GB增长至27.65GB。
- 真实旧引擎调用为restore-admission→selected_chain→archived_tree→每个payload check_pin(content=False)。该旧check_pin的content=False仅不保留内容，仍逐1MB读取并SHA256；同时archived_tree执行目录os.walk。故当前先做全量载荷校验，尚不能把它称为SQL/附件恢复写入。已知该点14339载荷、26090718750字节；进程rchar包括其它读取，不能当精确百分比或剩余时间。
- progressRoot与真实recovery-operations及Spug新target绑定一致；直接运行现有progress投影读取实际ledger request成功，返回restore-admission RUNNING。一次STEP_TELEMETRY_READ_FAILED已自行消失，未证实持续链路错误，不扩展修复。
- 私密证据full-running-location、full-progress-paths、full-worker-current、full-progress-direct、full-admission-scan-proof（均.private.json）。已向父报告旧引擎的全量hash行为，不中断当前操作或另起载荷扫描。
- 第二次只读观测：原PID22819无子孙、D磁盘等待，rchar37445170853字节，仍打开本次full的minio-physical附件part.1；/proc内核栈明确cifs_strict_readv。无Python用户栈证据，不attach或发信号。
- 从真实已安装旧源码和现有小元数据确认admission共4组读取：archived_tree全payload26090718750字节；object_index_chain逻辑对象8191188264字节；physical_chain_inputs物理附件9656153995字节；MinimalData._initialize再次全payload26090718750字节。合计70028779759字节，另有小元数据/执行文件读取；不是26GB只读一遍。
- 37.45GB累计读量+physical文件描述符高度符合第3组，尚有第4组约26.09GB；这属于基于源码和观测的推断，不把它写成精确阶段堆栈。证据full-admission-second-observation、admission-call-sites、full-admission-read-budget（.private.json）。已交父及安装agent，未干扰原恢复。
- 父要求只读评估停止路径时，原任务已自然终止：19:42:31Z FAILED_RETAINED / ARCHIVE_LEASE_FD_BUDGET_EXCEEDED，restore-admission耗993.284秒；worker-result明确mutationDispatched=false，child-exit=1且timedOut=false。正式resource-no-mutation-release.json reason=PROVEN_NO_MUTATION，19:42:32Z释放。
- 原worker22698/22808/22819均已退出、共享active.json不存在；控制父保留。无需人工终止、删锁或伪造终态，已通知父查询原UI终态。70.03GB为源码完整admission预期读量；实际本轮在ArchivePathGuard.capture预算失败，不能宣称第四遍全量读取已执行。证据full-stop-readonly-assessment、full-original-failed-released（.private.json）。

## 下一轮必要运行配置短名单
- 只读inspect及小配置核实：Docker网络为internal bridge、172.29.238.0/24；mysql/redis运行，minio/backend/frontend为created，符合空目标预期。MySQL /run/recovery/mysql-client.cnf可读，使用既有客户端执行SELECT @@server_uuid成功。
- MinIO数据挂载/data明确来自新目标minio目录，配置ownership=0:0、3个bucket原名映射；MinIO/mysql/redis引用的secret文件全部存在，未输出内容。附件载荷未读取。
- 确定旧契约缺项：target.iptablesPin引用旧test58路径在.59不存在；真实iptables为/usr/sbin/iptables，INPUT/DOCKER-USER无新目标子网规则。因此保留旧_initialize执行文件check_pin或旧bound必失败。已告父和实现：应明确正式轻量runtime是否已移除此旧契约；若坚持旧bound，则需生成真实pin和对应精确规则，不能仅修数据bind。
- bind契约由实现agent负责，未重复修改。证据runtime-shortlist.private.json；此处未部署或变更规则/容器。

## v10 新目标准备后的路径核验
- 父已安装v10并通过UI使prepare-0fc424ef-4730-46a9-aaf2-fe22cae04743达到READY，新目标spug-empty59-d4e8388b78a9。
- 小型只读observer确认：owner.targets[target].preparedEmptyTarget=true；control programPins recovery/repository均指向recovery-tools/engine下的新入口；配置及实际control PID29612的PYTHONPATH前三均为新tools的control/common/formal，实际入口亦为新tools/control_entry.py。
- 此时恢复worker尚未派发，明确未验证未来worker运行路径；父负责UI恢复提交，子任务不重复操作。证据prepared-runtime-prepare-0fc424ef-4730-46a9-aaf2-fe22cae04743.private.json，observer未读取任何payload。
- 新全量smallapp-760a8c7c23594a4dbb40ee0f0748b394真实受理后迅速FAILED_RETAINED/ARCHIVED_IMAGE_VERSIONS_INCOMPLETE；restore-admission1.508秒成功、target-checks0.536秒失败，mutationDispatched=false、exit1、共享active不存在。旧重复扫描阻塞已消除，未把失败写成恢复成功。
- 元数据明确新target.application.imageBindings为空数组，而services有mysql/minio/redis/backend/frontend五角色；已报告父。持久worker-process回执证明control worker为新tools/control/recovery_control_smallapp.py；子进程已退出，未伪报捕获recovery子进程实际/proc路径。证据v10-full-worker-once、v10-full-image-binding-diff（.private.json）。

## v11 全量实际数据库阶段观察
- 父v11安装及prepare-eef801e3-a115-48eb-9373-45175d11544b READY后，真实UI受理smallapp-bc9aafdc3b284a9582f6dd09f6bc9816，target spug-empty59-bd096098f1d3。
- 本子任务一次只读观察：restore-admission1.470秒成功、target-checks1.020秒成功；database-000/database-restore与sql-stage已开始（21:07:10/11Z）。无终态文件，不将当前mutation状态猜为false或成功。
- 实际进程32674→360→469→480；control worker、recovery_entry、recovery_minimal_worker均为recovery-tools/engine路径。共享active存在符合运行中。未扫描载荷或干预。
- 可复用私密observer：observe_restore_once.py <prepare-id> <operation-id>，仅读精确任务小回执及/proc程序路径。证据restore-observation-smallapp-bc9aafdc3b284a9582f6dd09f6bc9816.private.json。

## 最终增量原生回执核查
- 指定操作 smallapp-f0c503e401204fd0a2d263937e1d3b13 原生 SUCCEEDED、退出码 0；实际链顺序 FULL3c2395 → I1 20a1bb → I2 e7b668，与恢复点父 pin 一致。
- 准备三阶段均成功，保护路径仍存在、NAS 挂载保留；恢复暂存清理成功，共享资源已按 VALIDATED_CHILD_SUCCESS 正式释放，无恢复 worker 和共享 active.json。
- 已生成可提交脱敏摘要 [final-native-audit.md](final-native-audit.md)。仅只读小元数据与路径/进程状态，不增加全量扫描或载荷读回；业务页面及附件验收沿用父任务独立证据。
