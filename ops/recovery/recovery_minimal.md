# W04 单人最小恢复入口

主入口为 `recovery_minimal.py --configuration <绝对路径> --request <绝对路径> --output <绝对路径>`。
本模块执行 `RESTORE`；同一 UI 的 `FULL`、`INCREMENTAL` 由 W01 路由到 W03 捕获/归档模块。
传错模块会返回 `CAPTURE_ACTION_REQUIRES_W03_ENTRY`，不会调用旧签发入口。

请求保持现有七字段，不增加租约、授权签名或执行上下文字段：

```json
{
  "schemaVersion": "SmallAppBackupUiRequest/v1",
  "operationId": "existing-ui-operation-id",
  "action": "RESTORE",
  "sourceConfigRef": "existing-source-config-ref",
  "parentChainRef": null,
  "recoveryPointRef": "existing-recovery-point-ref",
  "targetConfigRef": "existing-new-target-config-ref"
}
```

配置是 W01/W05 从已有应用、源配置、归档与新目标解析出的本地执行投影，不建立第二套应用注册表。
所有 Ref 保持原值；所有路径必须为本机绝对路径。`Pin` 沿用 `{path,bytes,sha256}`，用于内容校验。
配置不得包含明文口令，只引用私有凭据文件。W05 负责唯一远程安装和目标准备。

## 本地执行配置

`schemaVersion` 为 `RecoveryMinimalConfiguration/v1`。字段如下：

| 字段 | 内容 |
| --- | --- |
| `operationsRoot` | 本任务的私有操作日志目录，与源、归档和目标数据目录分离 |
| `deadlineMilliseconds` | 整个恢复子进程的期限，1–7200000 毫秒 |
| `pythonPin` | 实际 Python 可执行文件的 Pin；其环境已安装现有正式模块依赖 |
| `maxChainLength` | 允许的链长度，1–10000 |
| `formalModuleDirectory` | 现有 `backup-ops/linux` 正式 SQL、S3 与读回模块目录 |
| `environmentMysqlClientPath` | MySQL 容器内的实际客户端绝对路径 |
| `maxExpandedBytes` | SQL 解压上限，沿用正式 SQL 恢复引擎的配置 |
| `dataLimits` | 现有 `formal_data_evidence.validate_limits` 的 `max_rows/max_nodes/max_bytes/seconds` |
| `sources` | 按现有 `sourceConfigRef` 索引的已解析源配置 |
| `targets` | 按现有 `targetConfigRef` 索引的已解析新目标配置 |

源配置的字段：

- `sourceScopePin`：现有源范围原件，其 `sourceIdentityPin` 含真实 `sourceFingerprint/databaseUuid`，`endpointHosts` 含源端点。
- `archiveRoots`、`sourcePaths`：归档根和受保护源路径的绝对路径数组。
- `sourceContainerIds`、`sourceNetworkIds`、`sourceVolumeNames`：受保护源资源标识数组。
- `repositoryPointPins`：现有 W03 点目录；`repositoryBindingPinsByManifestSha256`：现有 manifest SHA 到 `RecoveryRepositoryBinding/v1` Pin 的映射。
- `recoveryPoints`：UI 恢复点 Ref 到 RepositoryPoint Pin 的映射。
- `parentChains`：UI 父链 Ref 到完整父点 Pin 数组的映射。RESTORE 的 `parentChainRef=null` 时从所选恢复点读取父链；传值时必须与实际父前缀完全相同。

继续消费 W03 的 `RepositoryPoint/v1`、`RepositoryManifest/v1`、`RecoveryRepositoryBinding/v1`、
`RecoveryMaterial/v1`、`backup-capture-object-index/v1`、目录树和版本/删除记录，未建立新材料格式。
FULL 必须为真实 SQL 全量；I1 必须为真实 binlog，数据库位置、完整父前缀、generation、源身份、对象索引父项和文件删除增量均校验。
不要求 `ownerCloseEvidencePin`、签名 completed 回执、grant/lease 或 Pin 递归证明闭环。

## 新目标配置

### 通用数据盘配置

新环境使用 `storage-environment.example.json` 登记实际 `dataRoot`（数据盘目录）和
`repositoryRoot`（该环境的 NAS 仓库），由 `storage_environment.py` 生成路径：

```text
python storage_environment.py --environment /实际目录/environment.json --target target-唯一编号
```

配置生成器消费输出：采集 `archiveRoot` 和仓库源 `stagingRoot` 使用 `captureStagingRoot`，
仓库 `operationRoot` 使用 `repositoryOperationsRoot`，恢复 `operationsRoot` 使用
`recoveryOperationsRoot`，目标 `dataRoot` 使用 `targetRoot`。目标 MySQL、MinIO、Redis
使用输出 `mounts` 的直接 bind 挂载；`dataPaths` 登记这些实际宿主目录。
不要把 Docker `/var/lib/docker/volumes/.../_data` 当作数据盘路径：local driver 的 bind
volume 在容器停止后会卸载，离线恢复写入该路径会占用系统盘。直接 bind 的宿主源目录
在停止容器后仍可写，已完成本次备份服实际恢复验证。

该配置只供新环境准备和配置生成使用，不迁移已有系统、不重写历史恢复点或自动更改正在运行的配置。
不增加逐文件校验、全库扫描或容量预算。NAS 仓库保持各环境独立。

新目标须已经由 W05 创建专用容器、卷、镜像、内部网络、凭据及只读配置挂载；本模块导入数据并启动它们。
缺目标只阻塞 RESTORE，不影响 W03 的 FULL 捕获。

| 字段 | 内容 |
| --- | --- |
| `sourceConfigRef`, `targetId` | 原源配置 Ref 与独立的新目标标识 |
| `dataRoot` | 本任务新目标的私有状态目录；写入永久 `.recovery-operation.json` 预留标记 |
| `dataPaths` | 目标实际数据卷挂载点和只读配置/代码目录白名单，与源及归档路径分离 |
| `machineId`, `dockerEngineId`, `networkId` | 当前 Linux 主机、Docker daemon、专用内部 bridge 网络的实际标识 |
| `database`, `buckets` | 恢复数据库名称和完整目标 bucket 列表；数据库名遵循现有数据读回比较约束 |
| `dockerPin`, `iptablesPin` | 本机实际 Docker、iptables 可执行文件 Pin |
| `redisClientPath` | Redis 容器内的实际 redis-cli 绝对路径 |
| `services` | 服务数组，每项为 `role/id/imageId/ip`；id 为完整 64 位容器 ID，imageId 为实际镜像 ID |
| `secrets` | `角色 -> 环境变量含义 -> 私有文件 Pin`，见下文 |
| `bucketProtection` | `RecoveryBucketProtection/v1` 的期望版本化、锁定、ACL 与策略原始哈希；或显式使用 `v2`，为每个桶增加 `policyDocument`（原始 UTF-8 JSON 字符串或无策略时的 null），其字节 SHA-256 必须等于原有 `policySha256`，只忽略 Statement 内 Action 数组的顺序，保留其他字段及重复项的精确比较；直接配置，不要求签发 |
| `dataPolicy` | 现有实际数据恢复参数，见下文 |
| `application` | 版本、配置、代码挂载与启动顺序，见下文 |
| `redisRebuild` | 材料要求 Redis 重建时的应用适配配置 |

依赖角色固定为 `mysql/minio/redis`，其他角色是应用容器。容器均需具有实际标签
`intruoyi.recovery.target=<targetId>`，禁 privileged、额外设备/capability、host pid/ipc/network 和自动重启。
依赖不得暴露宿主端口，应用只允许绑定 `127.0.0.1`。只读 bind 只能位于目标 `dataPaths`。
轻量版新目标按上述通用配置使用数据盘的直接 bind 挂载；下列专用 volume 约束是完整验收路径的原有约束：
可写数据使用专用 local volume，
volume 同样带目标标签、无 driver options，且不能被其他容器共享。实际网络成员必须恰为当前运行的目标服务。
MySQL 与 Redis 应运行，应用应停止；物理对象恢复时 MinIO 应停止且数据卷**实际为空**，不接受已初始化 `.minio.sys`。
SQL 全量前检查目标库无表、例程、触发器或事件，数据库 UUID 必须不同于源；Redis 全库 DBSIZE 必须为 0。
MySQL 数据目录初始化前须核对源库的 `lower_case_table_names`，目标使用相同值，并在空库阶段读回确认。
该参数不能在已初始化目录上切换；大小写语义不一致会使 Flowable 等应用误判已有表并触发重复建表。

新目标网络必须是一个 IPv4 子网、禁 IPv6、`Internal=true`。W05 在隔离网络创建后安装以下两条防火墙规则，
分别成为 INPUT 与 DOCKER-USER 的第一条规则；执行器只执行真实 `-C/-S` 检查，不修改防火墙：

```text
INPUT -s <实际子网> -m conntrack --ctstate NEW -j REJECT
DOCKER-USER -s <实际子网> ! -d <实际子网> -m conntrack --ctstate NEW -j REJECT
```

这阻断新发起的宿主访问及子网外流量，允许目标内部依赖通信与已建立连接返回。
MinIO 与各应用容器必须配置真实 Docker healthcheck；只进行健康状态轮询，不重复 start。

凭据项为 `secrets.mysql.MYSQL_ROOT_PASSWORD`、`secrets.minio.MINIO_ROOT_USER`、
`secrets.minio.MINIO_ROOT_PASSWORD`、`secrets.redis.REDIS_PASSWORD`。
每个 Pin 指向权限不向 group/other 开放的、无换行和 NUL 的非空 UTF-8 文件。
MySQL 客户端凭据文件由 W05 只读挂载到 `/run/recovery/mysql-client.cnf`；查询和导入均强制容器内 socket。
Redis 认证通过 stdin 传递，不将口令写入命令参数或日志。

`dataPolicy` 沿用现有恢复实现所需参数：

- `bucketMapping`：源到目标 bucket 映射；物理恢复只接受同名映射。
- `bucketSettings`：逻辑全量恢复的 bucket 创建参数，每个 bucket 为 `{versioning:"Enabled",objectLockEnabled:<bool>}`。
- `minioDataMount`、`minioFileOwnership`：容器 MinIO 数据挂载路径及实际 `[uid,gid]`。
- `referenceQueries`：现有引用清单的实际 `{table,columns}` 查询配方。
- `businessInvariants`：实际只读 SQL 校验 `{queryPin,expectedOutput}`；无额外规则时为 `[]`。
- `mysqlbinlogPin`：仅当已有材料方法为 `MYSQL_BINLOG` 时提供实际工具 Pin；`BINLOG_SQL` 复用归档 SQL。

## 应用版本、配置与启动

`application.startOrder` 为应用角色的完整有序数组。每个角色只执行一次 Docker start，并等待真实健康状态。
`imageBindings` 覆盖所有依赖和应用角色，每项为：

```text
{role, versionPin, valuePath, imageId}
```

`versionPin` 必须属于最终材料的现有 `versionPins`；`valuePath` 是 JSON 键/数组下标路径，
其实际值必须等于当前容器镜像 ID。这样使用归档版本启动，不需要源安装 bootstrap 包作为通用门槛。

`configurationBindings` 每个应用至少一项，`artifactBindings` 是脚本类应用需要的实际代码文件列表；纯镜像应用可为 `[]`。
两者每项均为 `{role,archivePin,targetPin,destination}`。归档 Pin 须属于最终材料的 payload，
配置位于现有 `original-configs` 目录。目标 Pin 必须实际挂载到指定容器位置且为只读。
代码文件字节/hash 必须与归档一致。目标配置由 W05 明确改为新目标地址、私有 secretRef 和受保护启动设置，
保留原配置归档与新配置 Pin 以便核查。执行器不复制源连接配置到新目标，也不自动改写配置。

现有 smallapp 的 Redis REBUILD 适配为 `redisRebuild`：

```text
{kind:"SMALLAPP_SESSIONS",moduleDirectory,configurationPin,secretsPin,versionPin,versionValuePath}
```

复用实际 `core.Store.rebuild_redis_from_database` 与独立 Redis 读回；配置须为 TARGET/PROTECTED，
绑定本次 MySQL/MinIO/Redis 的实际地址，Redis >=7，应用版本须与归档版本值一致。
core.py/redis_cache.py 必须作为实际归档代码挂载项。`secretsPin` 为现有私有 smallapp 凭据 JSON，非签发凭据链。
校验 SQL 原始会话绝对过期时间、Redis PEXPIRETIME、已过期键不存在，禁止延长登录有效期。
材料声明 `NOT_PRESENT` 时必须确实非业务必需；其他未配置的 Redis/MQ 分类直接报缺适配器，不返回模拟成功。

## 结果、查询与验证边界

结果沿用 `backup-restore-operation-result/v1`：
`operationId/requestId/action/state/failureCode/message/data/originalResultPins/startedAt/finishedAt/actualExitCode`，
其中 requestId 等于原 operationId。仅实际恢复子进程 exit 0、完整结果及材料/阶段输出校验通过后返回 SUCCEEDED。
成功代表数据恢复和隔离健康启动，`businessAcceptance=NOT_PERFORMED`，浏览器业务验收由后续流程完成。

失败保留原目标和操作目录，不自动清理、不重新申请或重跑。同一请求和 operationId 再调用只查询该目录，
可从原子进程退出记录重建结果，绝不重新派发；超时/缺原退出或输出为 TERMINAL_UNKNOWN。
实际退出码、stdout/stderr 的私有文件 Pin 和原始 worker result 留在操作目录。

全量与 BINLOG_SQL 增量的压缩 SQL 均先从 NAS 校验读取到本操作独占的 0600 暂存文件，
再使用原有严格解压和导入检查；不修改 NAS 挂载权限，错误哈希及已有目的文件均拒绝。

成功后清理本操作的数据暂存：全量和增量备份在 NAS 独立 SMB 读回及 COMPLETE 发布后，
删除本地捕获的 payload、配置/代码副本、语义导出和数据库比较 scratch；删除前再次核对归档文件的大小和哈希。
恢复在数据库、对象、一致性、Redis 和隔离应用启动全部成功后，删除所有数据库步骤的压缩 SQL、
展开 SQL/binlog、比较 scratch，以及物理恢复校验导出的对象内容。运行中的源/目标数据、NAS 归档、
操作回执、日志、比较结果和版本映射保留。每次清理先持久化 staging-cleanup-intent.json，
实际删除成功后生成 staging-cleanup.json，并以 stagingCleanupPin 返回；失败向上报错，不能返回操作成功。
输入、输出或源/目标路径校验失败时不向不安全路径写结果；CLI stderr 输出错误码并 exit 1。

新 operationId 也不能复用已预留目标。W05 应为下一次恢复准备另一个空目标，保留失败目标供排查。
本模块没有远程安装操作、技术审批、角色签名、租约、源 bootstrap 通用门槛或自动重试路径。

本地检查：`python -m unittest discover -s ops/recovery -p test_recovery_minimal.py -v`。
这些是临时目录材料/哈希/文件增量与真实本地子进程测试，**不是** Linux MySQL/MinIO/Redis 或 Playwright 验收。
