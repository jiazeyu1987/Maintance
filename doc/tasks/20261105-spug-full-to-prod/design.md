# 正式原MAIN恢复合同扩展

## 已核事实
- UTC22:20–22:25 .57原五服务运行，后端UP/前端200，885表，UUID保持；195容器，无宿主活动恢复预约。原来源独立unit spug-intruoyi-source-57-20261105.service active，PID20619，软/硬预算65536待实际/proc复核；之前查询不存在旧unit的inactive不是来源服务故障。
- 原backend有可写Docker socket、/mnt/nas/Backup/BackupPackage、/opt/intruoyi/runtime及其日志/Codex目录、/opt/intruoyi/ops、/backup；两个只读工具经后续stat证实均为普通可执行文件。原runtime父目录包含mysql/minio/redis数据，因此必须明确“保留应用运行挂载”与“只替换登记的数据目录”，不能把全部RW当清理数据。
- 原minio只有默认bridge动态172.17.0.2，原9000/9001对外发布；mysql/redis原数据端点在172.21静态网络中当前分配.6/.2且不停止，backend固定.11/frontend固定.3。现MAIN/v1拒绝数据动态生命周期和发布主机端点，不能直接解禁。
- source/target应共同使用capture实际sourceLockPath /var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock。来源归档在共享NAS；目标本地数据在/opt/intruoyi/runtime/data，SQL暂存/控制证据必须在/var/lib/docker数据盘（当前约1.46TB余量），不能占仅约43.89GB余量的根分区进行重复SQL展开。
- 当前MySQL非本次查询连接均为backend 172.21.0.11；Redis无密码，CLIENT LIST仅该backend DB1与本次容器loopback只读查询；当前DB1有1个带到期缓存键。仅能证明当前连接，不替代全部writer归属；恢复源History350 DB1为0键，不能由现1键改变所选源。
- 102个其它容器配置文件只读扫描发现两个运行中的hostIP引用（展厅nginx与旧演练backend），需进一步区分主程序HTTP引用和直接数据引用；所有停止历史容器对原runtime的重叠挂载也必须精确登记并保持停止，不以停止为由静默忽略。

## 正式方案与阶段门禁

### 原MAIN资源观察身份合同修复（UTC03:04）

实际安装在observe_resources拒绝原MySQL，错误RESTORE_RESOURCE_MYSQL_IDENTITY_INVALID；原登记id/image/labels精确相同，但观察器只接受新建演练容器的intruoyi.recovery.target标签。正式方案对显式RegisteredMainApplication/v1或v2先验证完整MAIN合同，再核MySQL的原id/image、replacement登记labels/mounts与MAIN登记的完整Path/Args/HostConfig/Config摘要；运行/PID及实际cgroup/RAM/磁盘预算继续严格执行。普通空目标继续强制专用标签，不能只凭mainApplication字段跳过身份验证，不给原容器补标签或重建。

Given 原MAIN没有演练标签但登记完整且原容器/镜像/labels/mounts/全部配置保持；When 执行资源观察；Then 允许测量真实内存/磁盘但不声明业务成功。任何身份、配置、挂载或MAIN合同漂移拒绝，512MiB实际内存/空间不足仍拒绝，普通无标签空目标继续拒绝。先写RED，再最小实现与资源/MAIN/storage/包装/预约回归；修复提交后新建本次专用干净发布副本构建新代次，旧已追加引擎和失败配置原样保留，不换replacement状态根。安装助手对已有本任务完全一致的配置仅复用，配置漂移立即停止。
1. 显式新增版本化存储合同v3：数据挂载沿用v2物理设备/inode/mount与归档隔离检查；新增保留的应用bind挂载和精确停止历史消费者。只允许已登记原应用role的完整mount/配置身份；目录、文件、socket分别核真实类型/设备/inode/父路径，不能把socket当目录，不遍历或改写共享NAS。保留挂载可以包含登记数据目录，但绝不列入清理目标；任何其它活跃消费者或未登记历史消费者重叠仍拒绝。原v1/v2行为不变。
2. MAIN版本化v2显式消费上述保留挂载，固定原HostConfig/Config/Path/Args及只读工具/配置内容；不用删除原挂载或更换容器凑准入。已登记应用之外的挂载、配置或inode/type漂移均拒绝。
3. 发布MinIO通过精确原HostConfig发布端口和主机端点绑定；动态数据附件仅该显式发布端点情形可按真实Docker网络成员验证。恢复全过程建立精确访问围栏，容器停写、物理恢复及独立读回前保持；未经登记的端口/源/成员或围栏失效拒绝，失败保留停写和证据。不得泛化现有附加应用网络例外。围栏命令必须先在真实Linux网络隔离环境验证并给出原规则保持证据，未完成不装/不恢复。
4. 同机来源控制/目录准入不得依赖将被停止的业务后端，来源live UUID/数据检查仅恢复前执行；归档与不可变材料全程独立固定。共同源锁阻止恢复与备份并发，原来源控制历史保持。正式覆盖前先经Spug生成当前数据的新全备作为恢复前保留依据，仍恢复已验收的History350点；新备份原生成功与独立读回后才允许覆盖。
5. writer归属补全：原MinIO三个账号与三bucket实际配置/IAM政策、原backend凭据关系和其它运行配置及主机连接检查，明确所有writer；若仍缺所有权证据仅阻塞相应写入并向用户询问具体缺口。mysql/redis停写应由原backend停止加真实连接复核，MinIO端口围栏独立核验。

### 对外端口保护的正式设计
- 使用独立操作命名的mangle/PREROUTING与mangle/OUTPUT链，在DNAT和用户态代理之前拦截目标发布端口；IPv4/IPv6均处理，规则必须位于对应链首。不能仅检查DOCKER-USER，Docker端口DNAT与IPv6代理必须包含在实际Linux验证中。
- 原宿主机全地址发布9000/9001仅允许已登记后端固定源地址和本机root到loopback的恢复客户端；其它来源DROP。规则只匹配明确发布端口和LOCAL目的地，不影响其它业务端口；端口所有权和HostConfig发布绑定必须精确固定。原MiniO bridge内部的直接地址依赖完整IAM独占证据和实时网络成员合同，不能把发布端口保护称为整个网络隔离。
- 安装前保存原表有序规则，新增独立链填好终止DROP再插首规则；每次危险步骤核实际规则完整、首位置有效。操作失败保留围栏与证据；原生成功并完成应用启动和数据验证后只删除本操作的规则/链并核原规则顺序，禁止flush或重写原表。

## BDD / TDD
- 同机只读归档新增前置：实际.57 canonical CIFS专用视图为rw（来源备份需要写入），先前只读假设已被安装预检否定，未启动控制/停服/清库。正式方案在共同源锁内，对明确登记的本任务CIFS视图执行每挂载只读 `remount,bind,ro`，不改变底层共享superblock、不卸载或修改/mnt/nas/fstab；恢复成功后精确恢复原rw标志，失败保持ro和证据。原挂载ID/source/root/device和其它flags必须保持，其它业务挂载不得落在该视图下。此为持续恢复器能力，不由人工临时操作补准入。
- Given 独立Linux真实挂载和同存储另一rw视图；When 精确登记归档视图并在共同锁内保护；Then 目标视图实际写入EROFS、另一视图可写、失败保留、配置/挂载漂移拒绝，成功后原mountinfo和读写能力恢复；未通过不执行正式恢复。
- Given 真实应用有RW父目录、socket和NAS备份挂载；When 使用明确v3保留合同；Then 原数据挂载仍严格校验，应用挂载只保留不清理，v2继续拒绝。
- Given 已登记停止历史容器共享父目录；When 保持原配置且Stopped/PID0/无exec；Then 允许原MAIN覆盖；未登记、启动或任何身份漂移必须在破坏性动作前失败。
- Given MinIO发布端点固定而bridge分配在stop时清空；When 精确端点合同和真实网络成员一致、外围停写保护有效；Then 允许恢复；数据端点/发布配置/围栏漂移仍失败。
- Given 同机来源与目标；When 持共同源锁并保持独立控制与只读归档；Then 恢复可完成且不会同时启动备份，失败不删原记录。
- 所有行为先实际RED，最小实现后GREEN，再运行现MAIN/storage/SAFE-FAST包和保留失败/资源预约回归；Linux涉及真实stat/socket/挂载/iptables的验证不能用Windows跳过或mock替代。当前未执行任何服务器写入/业务停启。

## 当前数据保留的完整内容验收

以实际运行的封包程序为准：UTC01:27按worker29314定位来源116文件standard引擎，全部文件SHA通过，full reader SHA80abab1d31c9e6b6ef922ea7e93e6aa510037cfe6708ea6228bf5a6a13d5f61c与已审完整实现一致，publish精确调用完整verify；此包不使用本地轻量payload_content分支。原SAFE的RepositoryMinimumReadback/v1没有payloadContentVerified字段，不添加或改写。终态后独立审核原originalRecordsPin全部实际文件pins与manifest/tree一致、保留原始副本SHA、原元数据与来源程序pins；已固定的完整reader在原生执行中逐文件读取/比较、核前后完整树、签名加密及私有连接缓存，成功结果与原始凭据共同证明全部内容读回。无需另起一轮重复全量读取，原档案和历史不修改，serverDurabilityVerified仍为false。

BDD: Given 新360已原生成功且实际116文件SAFE程序与全部原pins稳定；When 独立审核完整SMB reader的原始读回记录和全部生成pins；Then 全部实际字节/摘要、目录集合、元数据和保留原始副本吻合，才准许350覆盖。缺少原始记录、摘要/文件集合/程序漂移均阻止覆盖，不以声明替代实读记录，不把轻量源码混入SAFE运行判断。
