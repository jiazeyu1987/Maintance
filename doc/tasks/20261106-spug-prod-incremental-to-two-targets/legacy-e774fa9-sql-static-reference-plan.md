# e774fa9 原 SQL 静态投影与有限参考实验计划

## Current Status

completed（本机静态投影及下一实验计划完成，未回放）。仅处理父按明确原 pin 补取的一个 1552 B gzip，在 256 KiB 上限内本机展开、验证 CRC 并私密保全原 SQL；冻结 44 点报告/设计不变，未执行 SQL、Docker、产品测试或远端动作。

## 目标与里程碑

- 核 gzip 原 pin 与父只读补取收据，限量完整展开并核 CRC/EOF。
- 只输出 mysqldump/服务器版本声明、数据库/CREATE TABLE 名及外部载入/改库等指令的静态事实，不输出行值/SQL 正文。
- 明确下一次隔离 MySQL 参考实验的实际镜像/版本原件、最小前置与首 RED；静态声明不代表回放或 MAIN 兼容。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；原 pin、CRC、大小或未知指令不满足就停止并记录。
- 是否从根因和长期维护角度解决：是；绑定单个原 SQL 与现有正式导入/观察器，先给出可验证的有限实验边界。
- 是否存在临时补丁或绕过：否；不改 SQL、不补表/改库、不重签原件，不构建转换平台。

## 经验门禁

- Trigger：仅有旧设置的 FULL 点补齐一个原 SQL 副本，准备隔离参考实验。
- Preflight check：固定 gzip bytes/SHA、父原读回收据、原 material/版本 pin；最大展开 262144 B，原 SQL 私密独占保存。
- Blocker：原 pin/CRC 不符、展开超限、未有明确实际 MySQL 镜像 ID/版本原件、外部输入或改库影响未获准。
- Verification：本阶段只静态投影和 UTF-8/原字节保全；后续获准后才真实隔离参考 BDD/TDD，不能把静态表名当实际 schema/数据证明。
- Forbidden action：无 SQL/Docker/远端/新增产品测试；不输出业务行，不改冻结 map/44 点报告/设计，不将演练库当 MAIN。
- Evidence：父 `small-registered-original-readback-20261110-r1.json`、1552 B 原 SQL gzip、冻结点清单和显式 program 元数据。

## BDD 与执行边界

Given 一个按原 payload pin 补取的 gzip，When 限量本机完整展开，Then 核 CRC/EOF 并保存原字节 SQL，仅发布静态声明，不执行或宣称回放通过。

## 本轮事实

父 `small-registered-original-readback-20261110-r1.json` 的 `legacy-e774fa9-sql` 记录 SSH 原 returnCode=0，并保留 84 B Windows close 诊断 stderr 原 pin；本轮未重跑 SSH。输入 gzip 为 `PRIVATE/legacy-e774fa9-sql-original-read-20261110-r1.private.sql.gz`，1552 B / SHA256 `6b5d759739aa4032f0c4c93df1ea19c3409c640ad89d4dc230249396fd959840`，与该点原 material 的 sqlPin 相同。

有上限展开命令为 Python `-X utf8 -` 本机内存处理：`zlib.decompressobj(16 + MAX_WBITS).decompress(raw, 262145)`，要求输出不超过 262144 B、单 member 完整 EOF、无多余 member/trailing bytes，并核 trailer CRC32 和 ISIZE。实际 exit 0 / 0.872 秒；展开 4514 B，严格 UTF-8 可解码。原 SQL 字节通过 `open('xb')` 独占保存并读回核等：

- `PRIVATE/legacy-e774fa9-sql-original-expanded-20261111-r1.private.sql`
- 4514 B / SHA256 `ba80438b813a18c7838865081f3cce121c8233d944cd25cd78ad09978c02562b`

公开投影 `legacy-e774fa9-sql-static-projection-20261111-r1.json` 只含结构声明/类别和原 pin，不含 INSERT 行值或原 SQL 正文。静态事实如下：

| 项目 | 发现 |
| --- | --- |
| mysqldump 声明 | MySQL dump 10.13，Distrib 8.0.39，Linux x86_64 |
| Server version 声明 | 8.0.39；原 material 的 endPosition.serverVersion 也声明 8.0.39，均不是本轮实测运行版本 |
| 数据库 | header 声明 `rehearsal`；无 USE 或 CREATE/DROP/ALTER DATABASE/SCHEMA，须由隔离 client 明确选择原名数据库 |
| CREATE TABLE 声明 | `lab_attachment`、`lab_record`、`lab_user`，3 个；直接 DROP/CREATE/ALTER/INSERT/LOCK 引用也只有这些未限定库名的表 |
| 其它语句类别 | SET 27、DROP TABLE 3、CREATE TABLE 3、LOCK 3、ALTER TABLE 6、INSERT 3、UNLOCK 3；不公开行内容 |
| 外部或改库类别 | 未发现 SOURCE/客户端 shell 转义、USE、数据库 DDL、LOAD DATA、OUTFILE/DUMPFILE、GRANT/USER、SET GLOBAL、动态 PREPARE/EXECUTE；无跨库限定表名 |

静态扫描保留 MySQL 可执行版本注释，排除引号字面量后归类；它不是通用 SQL 安全验证器。三条 CREATE TABLE 不证明运行后完整 schema/数据或 MAIN 兼容。本点为 FULL，material 中 `rawSqlPin=null` 是不适用项，不是需要补齐的增量 raw SQL；此前冻结清单里的通用 remote-pin 状态不能改变这一原值。

## 实际镜像与版本原件：尚有一个明确缺口

该点原 material 本机副本为 `PRIVATE/legacy-database-originals-r4/smallapp-e774fa9f6f544aea8d3cbc9208d05938/material.json`，44034 B / `db3b1e53bb5583c0413b171c01ce6df4b73760a5e80df7f5c565f54f00c1f606`，本轮核等。其 versionPins 只有：

`/mnt/intruoyi-data/smallapp-safe-20261022/configuration/images.json`，602 B / SHA256 `2a7f56897cd7c3789a36c038ddcc5abcca762fa4d9b0cf764d36ff14314d2fae`。

现有 `historical-program-inputs-r1.json` 七点观察没有这份原 pin 的解析项；已显式引用的相同 version SHA 代表 `050-original-images.json` 也不能按名称猜 MySQL 角色。因此当前不指定镜像 ID。下一步只需父提供这份精确原版本文件的已核本机副本及明确 mysql versionPath/角色绑定；不得扫描/按容器名猜测、以 `mysql:8.0.39` tag 替代 image ID，或从另一代表直接推定此点已验。

实验须将解析出的 `sha256:...` MySQL image ID 与实际 image inspect/原 archive image config 绑定，保全版本输入原件，再在隔离实例实测 `SELECT VERSION()` 与实例 UUID。原程序 tar 为 1103335424 B / `981027aed8b8512685a492dfbc309080b2ec8285070ca6d65fbd6eb9b548e7f7`；本轮不读取或要求重复下载它。若精确 image ID 在实验环境不可用，先列缺口，不自动拉取可变 tag。

## 下一次隔离 MySQL 参考实验（尚未获准执行）

只针对本点，不实施通用转换器，不接 MAIN。前置条件为：

1. 父当前 FULL/UI/r10 的资源排他期结束，并明确批准这次有限实验；实际镜像 ID/版本及必要导入器/观察器代码 pin 齐全，资源/超时有明确预算。
2. 使用新任务独占空 MySQL 数据目录/容器，`--network none`、不发布端口，不挂载 NAS、MAIN 或既有业务目录，不接入源/目标服务；原 gzip/私密 SQL 仅作只读输入，新凭据只保存在 PRIVATE。
3. 原旧 setting expectedDataPin 的 271 B 正文与 material 绑定继续保留；按其定义建立原名 `rehearsal` 空库并读回设置/UUID，不改 SQL、不换库、不补表。显式数据/展开限额、120 秒实验总预算和独占磁盘/内存预算先固定；原生退出码/超时/stderr 保全，失败不自动重试。
4. 复用现有 `formal_sql_restore` 有界展开/导入、`formal_data_evidence.observe_data` / `compare_data` 与实际 UUID guard。记录 SQL 源 pin/展开 pin、空库读回、真实导入原退出、结束完整 schema/row-multiset 观察和所有收据原件；allocator 只声明 SQL 可重建的结果，不声称补回源端未记入 SQL 的预留值。
5. 成功仅产出这一点的真实隔离参考观察及 `ARCHIVE_SQL_REPLAY_REFERENCE` 原件，固定 `sourceSnapshotVerified=false`；程序版本结构/MAIN 兼容/真实业务验收仍未证明。保留失败原件后仅清理本实验新建资源，绝不清理现有业务/父任务资源。

### 首 RED 与有限 BDD

本轮未运行以下实验或测试。原件/镜像条件不齐不得用 mock 补足。

- **参考观察实验：** Given 原 SQL、原旧 setting 和精确 MySQL 镜像均已核，且新隔离空库/UUID 实测通过；When 正式有界 importer 真实导入，再执行完整观察；Then 持久化实际得到的表/DDL/数据 multiset 与原生退出，任何 SQL/UUID/范围/限额异常均失败并保留证据。不得把静态的 3 个表名预制成观察文件，或改数据使其符合预设。
- **首产品 RED（参考原件产生后才跑）：** Given 同一本点原 material/旧 expectedDataPin 和真实参考 pin，When 走实际 standard 包配置→`validate_material`→真实 NativeData 构造与 FULL 读回，Then 应得到显式 replay basis、原 expectedDataPin 不变、sourceSnapshotVerified=false。当前 SAFE 只接受 typed encoding/UUID，旧设置缺 encoding；预期会在原严格入口拒绝，须记录真实失败后才最小实现，不 catch typed 失败降级。此处仅预测失败位置，没有声称已 RED。
- **两个必要负例：** 改 gzip/参考 pin 或运行 UUID 必须在 import/后续写前失败；将该三表演练参考提交 MAIN 必须被独立业务结构门禁拒绝，不能用 SQL 回放成功或 HTTP UP 放行。

## 本阶段收口

本阶段只新增公开静态投影与此短计划，并在 PRIVATE 保全 4514 B 原 SQL。冻结 44 点报告是采集前事实，保持原 SHA；新投影独立说明 e774fa9 原 SQL 副本现已补齐，不重写历史清单。没有实际 MySQL 回放、源快照证明、MAIN 兼容或任何点的登记/放行。

最终有限断言命令 Python `-X utf8 -` exit 0：原 gzip、4514 B 私密 SQL 及静态投影身份核等；44 点报告、原 108 map、补充合同设计三个 frozen 输入 SHA 均保持。没有运行 pytest/SQL/Docker。公开投影 5202 B / SHA256 `9344902d9a61dbcf1672abe0f569a1db045131c34fb2641c75d24a5e25e04d84`，UTF-8 无 BOM。
