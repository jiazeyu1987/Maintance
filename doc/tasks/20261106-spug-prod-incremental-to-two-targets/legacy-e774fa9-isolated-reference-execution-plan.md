# e774fa9 隔离 SQL 参考实验执行计划

## Current Status

completed（输入原件及有限计划完成，实验未执行）。父 2b/session83248 独占 Docker；本轮没有 SQL/Docker/产品测试，不修改产品或此前冻结报告/设计，不访问远端。执行仍须父审核及排他窗口释放，不能据本计划启动实验。

## 目标、里程碑与验证

- 核精确 602 B images 原文与该点原 material.versionPins，绑定显式 MySQL role/versionPath。
- 固定原 271 B 设置契约、正式 importer/observer 代码来源与 pin。
- 列清真实 image inspect/版本门禁、隔离资源/预算、原生退出/超时留存及只清理实验资源的范围，交父审核后才允许执行。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；原 pin、镜像或设置/工具不满足即阻断，不按 tag/名称猜测。
- 是否从根因和长期维护角度解决：是；对单点精确原输入复用正式 importer/observer，补真实回放参考而不伪造旧源证据。
- 是否存在临时补丁或绕过：否；不改 SQL/旧设置/manifest，不扩展产品或创建通用转换平台。

## 经验门禁

- Trigger：补齐 e774fa9 原版本文件后，准备一轮有限隔离 MySQL SQL 参考实验。
- Preflight check：父审核、Docker 排他窗口、所有输入与正式代码 pin、精确 image ID/实际版本、原空库设置/UUID及资源预算。
- Blocker：任一原件不符、镜像未预装/身份或实际版本不符、父资源仍占用、原生终态不明或实验清理归属不明。
- Verification：本阶段只核本机元数据及计划；后续实际 importer/observer、原生退出、schema/data 观察与清理证据分别验收。
- Forbidden action：本轮无 SQL/Docker/远端/产品测试；不启动业务、不接 MAIN，不操作既有容器/数据，不重写冻结证据。
- Evidence：父 `small-registered-program-version-readback-20261110-r1.json`、602 B images 原文、原 material/setting/SQL pin 与当前正式工具源文件。

## 1. 原版本 / MySQL 角色已核等

父公开收据 `small-registered-program-version-readback-20261110-r1.json` 为 1547 B / SHA256 `a50161435f0deb0677799b2adadfb8622c5fe6fc4301de2d7e8a63885bfef0dd`，声明源只读原 exit=0。其 `legacy-e774fa9-images` 副本 `PRIVATE/legacy-e774fa9-images-original-read-20261110-r1.private.json` 实际 602 B / SHA256 `2a7f56897cd7c3789a36c038ddcc5abcca762fa4d9b0cf764d36ff14314d2fae`，与本点原 material.versionPins 唯一项 `/mnt/intruoyi-data/smallapp-safe-20261022/configuration/images.json` 的 bytes/SHA 完全相同。

原 material 本机副本 `PRIVATE/legacy-database-originals-r4/smallapp-e774fa9f6f544aea8d3cbc9208d05938/material.json` 为 44034 B / SHA256 `db3b1e53bb5583c0413b171c01ce6df4b73760a5e80df7f5c565f54f00c1f606`，本轮核等。原文 role 绑定不依赖容器名猜测：

- role：`mysql`；显式 versionPath：`["images", "rehearsal-smallapp-20261022-mysql"]`。
- image ID：`sha256:f5da8fc4b539c8ff9005b316b41b09d99b6ef6cdf55b5abbfcfd40dd3547f845`。
- releaseTag：`2026-10-22-22-00-44`，只作为原件字段，不把 tag 当 image 身份。
- 原 SQL header 与 material.endPosition 均声明 MySQL `8.0.39`；这仍须实验实例实际 `SELECT VERSION()` 证明，不能代替运行观察。

本轮元数据核验命令 Python `-X utf8 -` 实际 exit 0；没有导入/执行这些产品 Python 模块。父对 44 点的独立 session63224 复核结论为 191 显式元数据/33,431,880 B、43 前缀闭包/44 ID 通过；本计划不将其改称 SQL/程序运行通过。

## 2. 原设置 / SQL 契约保持

原 expectedDataPin 必须保留完整路径：`/mnt/intruoyi-backup-nas/Backup/BackupPackage/smallapp-normal-fast-20261023/59/archives/prod-lightweight-aea4990d9a8f1a6d338f1b71948fc0ab99ea100fc3d96a2315067d8765d07bd1/payload/011-source-data.json`，271 B / SHA256 `8300791c523497930a3df5b7d3f60abe63fe2253a31e91cf9f372a90b683e6d0`。

本机已核的同内容副本是 `PRIVATE/archive-program-contracts-r3/smallapp-5e52bf1ab0724e17b889fa039fbb1fbd/011-source-data.json`。本点 material 的原 pin、payload membership 及本机正文 SHA 一致，故可复用其内容而不改原路径/身份，不称该代表就是本点。

原文严格形状为四键 `database/definition/schemaVersion/verificationState`：数据库 `rehearsal`；`LightweightDatabaseSettings/v1`；`verificationState=NOT_PERFORMED`；definition 是 `["rehearsal", CREATE DATABASE 定义]`，其中明确 `utf8mb4`、`utf8mb4_0900_ai_ci`、`DEFAULT ENCRYPTION='N'`。实验只按这些设置建立隔离空库并用 SHOW CREATE DATABASE 读回，对比现有 `recovery_data.database_settings` 解析结果。原 SQL 没有 CREATE DATABASE/USE，必须通过 client 参数选择该原名数据库；不做替换/改库/补表。

原 gzip 1552 B / SHA256 `6b5d759739aa4032f0c4c93df1ea19c3409c640ad89d4dc230249396fd959840`；本机父补取副本和先前 4514 B 展开 SQL（SHA256 `ba80438b813a18c7838865081f3cce121c8233d944cd25cd78ad09978c02562b`）均保留。正式实验重新通过有界 importer 展开到新的独占私密文件，不覆盖先前原文。三条 CREATE TABLE 只是先前静态声明，实际完整观察后才知道回放结果。

## 3. 正式工具来源与代码 pin

本次只读时 HEAD 为 `a255c97d5b9499ed0a15eee0d3bb094e1275b1ce`；下列是实际工作区 UTF-8 文件 bytes/SHA，入口三文件当时 Git status 无改动。它们不是已交付 SAFE 包成员的等价声明，也未进行构建。实验必须使用同字节副本并记录其 `__file__`/SHA；执行前任一变化即停止重审，不自动切换“最新”代码。

| 正式源文件 | bytes | SHA256 |
| --- | ---: | --- |
| `ops/backup_engine/formal/formal_sql_restore.py` | 27351 | `889e3cc0d3f96c88a8d4c267ed318c6b091f19a6396419548135c16f722fc66e` |
| `ops/backup_engine/formal/formal_data_evidence.py` | 25483 | `d954bffadf0baf929814bec0977101dffb30069b17aef58d1ac04fa2bc0bdcca` |
| `ops/backup_engine/formal/formal_schema_evidence.py` | 25242 | `e7649b2f52a8ef12238ca3a1c22f706bb5587a885ac4b6665e0b5963d764c7f8` |
| `ops/backup_engine/formal/formal_snapshot_linux.py` | 80121 | `8e2801fd7618ffebae181144547e3d90e4303089b1e24fd6fa8f98b34b089d9f` |
| `ops/backup_engine/formal/formal_capture_producer.py` | 222372 | `130a28b470365b52660dbc9ce0f1c23eb1ca35fd26d3eb9a88a01de9bf91f1c5` |
| `ops/backup_engine/formal/formal_source_migration_ledger.py` | 19340 | `7ff64307bd54a87fad515ee9c8b74fe88dcdcfbf653093a807b62b1ba9df0344` |
| `ops/backup_engine/formal/formal_filesystem_watchdog.py` | 22955 | `e877489911c48c17e37abcc84e946667e4bc7b36bd811d6a8d5b661af5bb6576` |
| `ops/backup_engine/formal/formal_replica_gate.py` | 25206 | `5128318ecfe13e652ca1d93dbdacc2ed9a762e379885da70e5affac28601b455` |
| `ops/backup_engine/formal/formal_s3_export.py` | 41113 | `1352f17c0c37f05dee884a19b1c3700d0647b80406e1375a881b21ad47fbefb2` |
| `ops/backup_engine/formal/formal_capture_budget.py` | 17819 | `dcb12bb965b2d260036dbad3810fa30a9b8781aa4ea404f2a6c842330115cc62` |
| `ops/recovery/recovery_data.py`（设置解析/原 importer 记录方式参照） | 66742 | `4e67ed93fbcd0229a0d3daeba159ce860c50c8c8304612b72b8ba8d4549d6b59` |

实际调用边界仅 `IsolatedTargetMySql`、`bound_target`、`empty_database`、`database_state/import_database_state`、`expand_checked`、`stream_import`、`observe_data/compare_data` 与设置解析；不调用 `formal_sql_restore.main` 的源侧台账/源快照验证来伪造此旧点。执行前生成小型实验 runner 的固定输入/工具清单及实际 import 传递依赖清单，再审阅；上表只是已核入口/直接依赖，不冒称完整传递闭包。runner 不能导入并启动 source 捕获/backup 入口。

已核当前接口限制，实验层须显式承担而不改产品：

- `expand_checked(...expected_digest...)` 当前实现未对原 gzip 校验该参数；`stream_import(...expected_sha...)` 当前也未在入口再次核展开内容。实验 guard 必须独立核原 gzip 和展开 pin，按同一打开文件/不可变私密副本贯穿前后；不能靠传参声称已经验证。
- `stream_import` 要求 callable guard、远端 coreutils timeout 和 `RECOVERY_SQL_EXIT` 确认，但内部 stderr=DEVNULL，且不向调用方返回子进程退出对象。实验 runner 的真实 subprocess 记录接缝必须事先审阅：只给真实 Popen 附加私密 stderr 文件和真实 PID/returncode/开始结束收据，保持原 argv/stdin/stdout及 helper 的确认/unknown 判定；不能伪造 native 成功或吞异常。此记录接缝尚未写/测，未审好就阻断实验。
- observer 支持真实 `process_observer.before/started/finished`，须记录实际查询进程；其完整收据与私密日志不同于导入器专用退出确认。没有原 stderr 时只能记“未采集”，不能造空 stderr SHA；本实验要求新导入时接好私密留存。

## 4. 执行准入与隔离资源

执行前父必须明确排他窗口已释放，记录一次独占 operation ID、实验代码/全部输入 pin 及 `GREEN: experience-preflight -> PASS`。原 2b/session83248 或当前 FULL/UI 仍在占用即不启动。不等待超时后擅自认为资源空闲。

只用预装的上述 image ID。先真实 `docker image inspect <精确 ID>`，要求返回 Id 完全相同、Linux/amd64、入口与实际 MySQL image config 原件可核。保存完整 inspect 私密 pin及工具版本；镜像未预装就报告，不拉取 tag、不导入历史程序 tar、不触碰原容器。新实例启动后实测 `SELECT VERSION()` 必须为 `8.0.39`，记录 `@@server_uuid`、server/session设置、coreutils timeout/mysql client 实际版本。SQL header/releaseTag不能取代这一步。

仅新建一个带本次随机 operation label 的容器，`--network none`、无端口、非 privileged、无 bind/named volume、无 Docker socket。`/var/lib/mysql` 使用独占 tmpfs，runner 在新独占私密目录，经 docker stdin 输入原 SQL；不挂载 NAS/旧SQL目录/MAIN数据。`bound_target` 须验证 container ID/image/标签/网络/挂载，guard 每阶段保持。拟硬上限如下，失败不自动增额重跑：

- 容器 1 CPU、2 GiB RAM、memory-swap=2 GiB、pids=128；tmpfs MySQL 512 MiB，临时/tmp 32 MiB；不写持久数据卷。
- MySQL 只为实验设置 buffer pool 64 MiB、redo capacity 64 MiB、event_scheduler=OFF、binlog关闭、performance_schema关闭；实际启动参数与配置全文固定到 referenceRuntime 原件，不谎称源环境相同。
- 宿主 scratch 16 MiB（必须在有实际 quota/tmpfs 限额的 Linux 环境，无法硬限额则先阻断），独立日志总上限 2 MiB；SQL 展开 262144 B；观察 max_rows=10000、max_nodes=100000、max_bytes=1048576。
- 数据采集总预算 120 秒：startup<=60 秒、expand<=5 秒、import<=20 秒、完整 observe<=30 秒，其余在总预算内；单次普通 native 命令<=5秒。清理独立<=20秒，不扩展采集预算掩盖超时。
- 成功只运行一次完整 observe_data，真实 self-compare 仅验证观察自身完整性，不称独立回放等价；若需要“两次独立空库回放等价”，另行批准，不能本轮悄悄再跑一遍。

## 5. 执行次序、原生终态与清理

1. 核所有本机原 pin/工具副本；固定 runner/input 清单。真实 image inspect/排他准入通过后才创建独占容器，保存创建原退出及 container ID。凭据随机生成，仅 PRIVATE；不进入 argv/公开输出。
2. readiness 有界等待，取真实 UUID、版本/配置；按原 definition 创建 `rehearsal`，读回 settings；`database_state` 要求唯一用户库及事件/事务状态，`empty_database` 要求无表/触发器/例程/事件。所有 guard 绑定新 ID、UUID及唯一 operation。
3. 原 gzip 在新的 Linux私密目录0600副本核 SHA后 `expand_checked`；核展开 4514 B / 已知 SHA 一致。记录原 SQL pin、展开 pin及导入 intent，再 `stream_import`，明确 client 参数 database=`rehearsal`。guard 在导入期间只查可用的 import_database_state，不以 importer 自身事务为违规。
4. 导入成功必须 helper 原 `RECOVERY_SQL_EXIT=0` 确认与实际子进程 exit=0 均存在，完成后 `database_state`/UUID不变；记录私密 stderr 原 pin。再正式完整观察 schema/typed row-multiset、原生过程收据和观察原件；不发布行值/账号或 SQL 正文。
5. 任何错误/超时保存真实 code/native exit/是否收到确认/terminalUnknown、started/finished 时间与私密 stdout/stderr pin。124/137/143、断连或仅杀本地 Docker client均不能当远端 importer 已停止；不重试、不新建下一实例。先针对本实验精确 container ID 确认真正终止/移除，再结束；未证实终态就报告阻断，不能宣布清理成功。
6. finally 仅检查并停止/移除该实验唯一 ID且 operation label/image匹配；新 tmpfs随容器移除。禁止按名称模式批删、`docker prune`、删除任意既有 volume 或重启 Docker。先保全原始失败/输出收据到 PRIVATE，保留证据不改写；只清理已核绝对路径下本实验 scratch（不删输入/父文件）。真实 list/inspect证明本容器和自有进程已消失、既有父容器清单未改，才记清理 PASS。20秒清理期限未达成则单独阻断，不把 observation 完成冒充实验完成。

## 6. 有限 BDD 与产出

- **隔离参考事实：** Given 精确版本文件/image inspect/实测8.0.39、原设置和 SQL pin 与空库/UUID guard；When 一次真实正式 importer+完整 observer；Then 保全实际结果/退出/观察，basis仅 `ARCHIVE_SQL_REPLAY_REFERENCE`，sourceSnapshotVerified=false。这个实验不是产品 GREEN，也不是 MAIN 演练。
- **首产品 RED（参考形成、另获准后）：** 实际 standard 包读取本点旧 expectedDataPin + 新参考 pin，经 `validate_material` / 真 NativeData 构造至 FULL 读回；预期当前严格 typed 入口拒绝旧格式。保留真实失败再实施，不用 mock 或手填解析后对象跳过入口。
- **独立负例：** 原 SQL/参考 pin 或 UUID 任一改变就拒绝写入；三表演练观察即便成功也不能放行 MAIN 版本结构要求。这些负例本轮不运行，也不额外造前端入口。

产出只限本点隔离 reference 的真实运行输入/收据/观察原件与无秘密投影；原 expectedDataPin、manifest、SQL、此前冻结44点报告/设计均不变。MAIN15表或任何版本的业务 schema 仍须独立确证，不能把三条静态 CREATE TABLE 或本实验观察包装成备份时点源证明、MAIN兼容或三服恢复通过。

## 本轮收口证据

本轮仅本机原件/源文件读取与独立计划写入。原版本/设置/material核等 exit0；正式文件只做 UTF-8读取/AST静态解析，没有 import/执行产品模块。未调用 Docker/SQL/SSH或pytest；执行计划本身不是实验已批准或已执行凭据。

最终静态复核 Python `-X utf8 -` exit 0 / 0.443 秒：表列 11 个源代码 bytes/SHA 保持；44 点清单、原108 map、补充合同设计、SQL静态投影四份冻结证据保持；602 B版本及显式MySQL角色值核等。此计划为 UTF-8 无 BOM。不得把该本机断言 PASS 当实验或产品测试 GREEN。
