# 旧格式数据库恢复合同只读评估

## Current Status

completed（本轮只读评估）。整体 108 点三服恢复目标仍未完成。仅评估本机已有原件与当前正式代码；未修改实现、测试、安装输入、归档或运行配置，未查询服务器、读取业务 SQL 载荷或执行恢复。当前 45/r6 控制已激活、Spug c772 尚未安装的事实由父任务记录，本评估不代替安装验收。后续正式合同须父审后才进入 TDD。

## 目标、里程碑与预期验证

1. 核对 108 个备份点与现有 13 个代表组的真实覆盖关系。
2. 逐点定位数据库、程序及原件证据，明确代表观察与逐点证明的界限。
3. 依据当前正式恢复合同，提出旧格式支持的最小可维护 API、BDD 与后续验证路径。父任务审查后才进入 TDD。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。原件缺失、pin 不符及未知兼容性保留为明确缺口。
- 是否从根因和长期维护角度解决：是。将归档数据格式、SQL 派生事实与恢复验收事实分开定义，避免将当前状态反写为历史事实。
- 是否存在临时补丁或绕过：否。不修改原归档、清单和已有严格校验。

## 经验门禁

- Trigger：历史点跨三服恢复的数据库及程序合同尚未闭合。
- Preflight check：仅读取公开报告及其明确指向的本机私密原件；逐文件记录 pin，禁止递归扫描 PRIVATE。
- Blocker：原始 pin 不符、缺失原件、逐点映射不完整或需真实 SQL/服务器动作才能证明的事实。
- Verification：108 点唯一计数、与分组逐项交叉核对、正式代码调用边界、证据来源和未验证项。
- Forbidden action：不联网、不操作服务器/Docker/归档、不执行旧任务脚本、不公开私密正文、不把代表组通过提升成全部点通过。
- Evidence：父计划、现有目录/分组原件、本文及专属无秘密映射 JSON。

## 已确认的统计问题

`archive-source-program-assessment-r1/r2/r3.json` 均声明 `backupCount=108`，但其 13 组 `groupPointIds` 只有 86 个唯一点。后续逐点映射将以完整目录和 15 组原始 inventory 为准，保留原报告的统计差异。

## 证据范围与原件路径

逐点文件为 `legacy-schema-restoration-point-map.json`，schema `LegacySchemaRestorationPointMap/v1`。全部 108 点各有目录状态、原 identity/scope 摘要、原报告是否列入、代表组、数据库声明 pin、可用的程序验核、三个目标绑定和明确缺口。`inputPins` 固定 411 个本机输入文件；`sourceCodePins` 固定本轮审阅的 12 个正式源码。该映射不包含 SQL、凭据、环境变量或私密配置正文。

本轮只读明确路径如下；PRIVATE 固定为 `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106`，未递归扫描该目录。

- 目录原件：`PRIVATE/goal-audit-readonly-r7/catalogue-11.private.json`，141286 B，SHA256 `1e23bbad3af8cc4111e3a2b152ba5b2567a6ca7d52d98c9c699b3e69b68ff1d4`。原 pin 来自补充观察的 `inputPins`，本轮实际核等。它与公开 r6 目录报告的原件是不同快照，不混用其 SHA。
- 来源分组：`archive-source-inventory-r1.json`；代表评估：`archive-source-program-assessment-r3.json`；代表原件比较：`archive-program-contract-evidence-r3.json`。
- 逐点本机元数据副本：`PRIVATE/archive-source-inventory-r1/<packageId>/manifest.json`、`point.json`、`recovery-repository-binding.json`。依据目录和 inventory 的明确 108 个 ID 逐个访问，不搜索其它路径。
- 代表数据库/程序元数据：`PRIVATE/archive-program-contracts-r3/complete.private.json`，58721 B，SHA256 `44205c3bed67f580fb80b0b691bc9cda706097ea2d232e7c0ce91b35064109d6`；及其 13 个明确 ID 下的 `capture-recovery-inputs.json`、`011-source-data.json`（如存在）、`050-original-images.json`、`capture-content-point.json`。
- 三个补充 expected-data 原件：`PRIVATE/archive-expected-data-r1/complete.private.json`，11531 B，SHA256 `69d9d62b93f51201154b647c06ac3e26bc5e0bcc751ea68aa5e537d08c581287`；以及该记录明确指向的 `9d5ed210…`、`e5c20b88…`、`de5f072c…` 本机 JSON。
- 当前较新程序证据：`historical-program-archive-inspection-matrix-r1.json` 的 7 个精确 evidencePin、`historical-program-bindings-matrix-r5.json` 的 21 个精确 evidencePin，均重新核本机 bytes/SHA。较早 `historical-program-archive-verification-r1.json` 只覆盖 3 个具体点/历史程序版本，不能替代较新的 7 点记录。
- 原件损坏及搜索范围：`archive-84563-original-metadata-r1.json`、`archive-original-metadata-local-search-r1.json`、`archive-original-metadata-nas-search-r2.json`。本轮仅阅既有报告，不执行搜索或 NAS 访问。

## 108 点、15 组、13 代表和 86 列点的关系

完整目录与 inventory 的备份 ID 集合完全一致：108 个唯一点，其中 FULL 48、INCREMENTAL 60；indexed 106、unpublished 2。13 个代表是从 15 个 identity/scope 摘要组中抽取的样本；它既不是 108 点逐点验核，也不是 13 种程序或数据库版本。

下表的组号为映射 JSON 的 `inventoryGroup`，从 0 开始；代表 ID 省略共同的 `smallapp-` 前缀，仅表中显示短前缀，完整 ID 在 JSON。S 为代表有 schema/data 观察；L 为代表仅数据库设置；M 为代表原件 pin 不符。类别只描述该代表。

| inventory 组 | 代表前缀 | inventory 点数 | r3 实际列点 | 代表数据库类别 |
|---|---|---:|---:|---|
| 0 | 9d5ed210 | 10 | 10 | S |
| 1 | 52517f29 | 26 | 26 | L |
| 2 | 811ed843 | 1 | 1 | L |
| 3 | 无 | 2 | 0 | 未评估；scope 缺失、未发布 |
| 4 | c3b76ae9 | 3 | 3 | L |
| 5 | e5c20b88 | 7 | 7 | S |
| 6 | bfbc98ae | 20 | 1 | S；其余 19 点被漏列 |
| 7 | b664bd8f | 10 | 10 | L |
| 8 | de5f072c | 8 | 8 | S |
| 9 | 5e52bf1a | 13 | 13 | L |
| 10 | ae839bce | 1 | 1 | S |
| 11 | 0f8eb295 | 1 | 1 | S |
| 12 | 84563ace | 3 | 3 | M；不意味着其余两点损坏 |
| 13 | 441bd02f | 2 | 2 | S |
| 14 | 无 | 1 | 0 | 旧 inventory 元数据不可读 |
| 合计 | 13 个代表 | 108 | 86 | 7S + 5L + 1M |

漏列 22 点的原因是：组 6 原有 20 点而 r3 只列代表 1 点，少 19 点（8 FULL、11 INCREMENTAL）；组 3 两个未发布 FULL 未列；组 14 一个 FULL 未列。它们是“r3 代表分组报告未覆盖”，不是“备份不存在或损坏”。

两个未发布点为 `smallapp-9695bf3fb95d4ec4a19eb6fbe6329066` 和 `smallapp-d62276cdb402499d9586871439765989`。旧目录分别没有 repository binding，其中后者目录 issues 含 `BACKUP_VERSION_PIN_MISMATCH`；仍需原始发布/操作依据，不能补造 point。`smallapp-be26b59281a4464dac816d61f76f0443` 在旧 inventory 缺少本机 manifest/point/binding 副本，但较新程序证据已经对它做过归档验核和三服元数据绑定；因此只将“本轮 inventory 副本缺失”记为缺口，不宣布其归档不可读。

r3 的 `unresolvedGroups=4` 不是当前剩余组数。r1 中三个代表的数据库观察尚未补读，加上一个 pin 不符代表，能对应该旧计数；r2/r3 已补回三个观察，却保留该字段为 4。本轮不修改旧报告，以明确类别 7S/5L/1M 和逐点缺口取代这个不能代表现状的聚合值。

## 逐点能证明和不能证明的内容

本机存在 107 份 manifest，全部原字节 SHA 与各自目录 `manifestSha256` 相同；105 点还具有 binding 和 point 副本。本轮核其 manifest/point 的实际 bytes/SHA 与 binding 一致，所有已列 parent pin 均能对应本机原副本并核等。按当前 lightweight `selected_chain` 的“取最后父点”规则，这 105 点的元数据路径均可到 FULL：链长 1/2/3/4/5/6/7 分别为 45/27/17/6/5/4/1。

这只是本机原件与父引用的一致性观察。未读取其 recovery material 正文、源侧/归档实际载荷、SQL、对象文件或实时保护，未调用正式 selected_chain/preflight，不能宣称正式整链准入或恢复就绪。

来源 identity/scope 相同不保证每点数据库证据格式相同。对 107 份 manifest 的明确 expected-data 载荷 pin 分类，得出以下互斥计数；这里的“匹配”指 manifest 声明的内容摘要匹配已读本机代表原件，不是 NAS 载荷本轮重新读回。

精确边界：逐点载荷候选按 manifest 中唯一的 `011-source-data.json` 或 `source-affected-data.json` 定位；13 个代表另有 capture 输入证明，其他点尚未读取 recovery material 正文。因此 JSON 中 `expectedDataPayloadPinDeclared` 表示明确 manifest 载荷候选，不表示已核 recovery material 的 `database.expectedDataPin` 与之相等。下一步必须沿 binding 的原 `recoveryMaterialPin` 核等该关系；无 binding 的未发布点不能靠文件名建立正式合同。

| 逐点声明类别 | 点数 | 精确含义 |
|---|---:|---|
| 匹配已读旧设置内容 pin | 44 | 16 FULL、28 INCREMENTAL；内容格式已知为 LightweightDatabaseSettings/v1 |
| 匹配已读 typed 观察内容 pin | 8 | 原件中有相应观察；仍未证明该点全部数据载荷或恢复 |
| affected-data pin，正文未评估 | 27 | 只知道明确归档 pin，不能按文件名就断言内容合法 |
| 其它 expected-data pin，正文未评估 | 27 | 格式和完整性需逐点原件进一步核验 |
| 代表原 expected-data pin 不符 | 1 | 84563ace 代表，保留失败 |
| 本机 inventory manifest 缺失 | 1 | be26b592；另有较新程序证据 |
| 合计 | 108 | 所有点均没有被本轮标记恢复已验证 |

五个 L 代表所在组共列 53 点，但不能说这 53 点都只有旧设置。例如 52517f29 所在组的 26 点中，17 点声明的 expected-data pin 匹配旧设置内容，另有 5 点声明独立 affected-data pin、4 点的其它 expected-data 正文未评估。同样，7 个 S 代表也不能证明其所属组全部点都有同等观察。

84563ace 的三份旧 capture 元数据仍保持原 pin 不符：`011-source-data.json`、`050-original-images.json`、`capture-content-point.json`；而 `capture-recovery-inputs.json` 匹配。现存读取报告记录预期原路径 FileNotFoundError/ENOENT；本机已扫描副本及既有 NAS 搜索未找到匹配原件，但搜索存在错误且明确 `globalAbsenceProven=false`。不据此宣布全局无原件，不重算 pin 接受现存替代字节，也不把同组另外两点一并判坏。

## 五个旧设置代表的真实数据库证据

五份内容均是 `LightweightDatabaseSettings/v1`，只有 `database`、两元素 `definition`（数据库名和 SHOW CREATE DATABASE 文本）、`verificationState=NOT_PERFORMED`；没有表、列、索引、触发器、行数据、typed multiset、源侧 schema observation 或 allocator 冻结观察。

| 代表前缀 | 该组列点 | 代表类型/方法 | 数据库 | 原 expected-data 大小 | 已声明 sqlPin 大小 |
|---|---:|---|---|---:|---:|
| 52517f29 | 26 | INCREMENTAL / BINLOG_SQL | rehearsal | 271 B | 3593 B |
| 811ed843 | 1 | FULL / FORMAL_SQL_FULL | ruoyi-vue-pro | 283 B | 6428017136 B |
| c3b76ae9 | 3 | INCREMENTAL / BINLOG_SQL | rehearsal | 271 B | 4023 B |
| b664bd8f | 10 | INCREMENTAL / BINLOG_SQL | rehearsal | 271 B | 3415 B |
| 5e52bf1a | 13 | FULL / FORMAL_SQL_FULL | rehearsal | 271 B | 2629 B |

SQL 大小来自 pin 声明，未读取/解压或检查 SQL 内容，不以压缩大小猜表数或数据量。前述三个增量代表还声明 raw SQL pin；准确原路径/bytes/SHA 均在逐点 JSON 的代表证据中。

已读旧设置能确定数据库名称和原记录中的 charset/collation/encryption。四个 rehearsal 样本为 utf8mb4/utf8mb4_0900_ai_ci/N，811ed843 为 utf8mb4/utf8mb4_general_ci/N；这只说明这五个代表的原数据库设置。

从经过原 pin 校验的完整 FULL SQL，加上精确、有序、闭合的增量 SQL，可以在已绑定版本的独立隔离 MySQL 中重放，再用正式 schema/typed-row 观察器得到“这些归档 SQL 的执行结果”：实际存在的表/列/索引/约束、被 SQL 包含并成功重放的 view/routine/trigger/event 定义、最终行的 typed multiset、SQL 执行后 allocator 等。不能靠正则提取 CREATE TABLE 就声称等同完整 MySQL 语义；BINLOG/base64 行事件还依赖对应表映射、基线及实际兼容 MySQL。

无法从 SQL 单独补出的历史事实包括：备份瞬间源库全部 schema/行与 SQL 一致、导出确实覆盖所有源对象/所有行、未导出的 routine/event/权限、源 UUID 与实际一致性锁持有过程、未记录的失败自增分配造成的 allocator 状态、SQL 与附件的真实同一时点、未捕获业务/对象引用及应用兼容性。尤其 ROW 日志可不含未使用的 AUTO_INCREMENT 分配号；不能以 MAX(id)+1 或重放后计数冒充历史冻结计数。若验收要求逐字段等同原源快照，必须找到独立原始观察，缺失信息不能由代码制造。

## 当前正式实现边界

本节依据 `sourceCodePins` 中当前源码，不以旧 `archived-program-restoration-plan.md` 的阶段状态推断实现缺失；也不把本地 lightweight 同名函数当实际 standard 包中的实现。

1. `recovery_minimal_runtime.MinimalData.restore_database_settings` 已显式支持 LightweightDatabaseSettings/v1，并复用 `recovery_data.database_settings` 的严格数据库定义解析。其 `full_database`/`incremental_database` 已能回放归档 SQL；`database_readback` 明确 `verificationState=NOT_PERFORMED`、全 schema/data 和增量受影响数据验核标记为 false，worker 成功消息也明确“不作验证”。因此不能说旧格式在两种模式都不能执行，更不能把轻量执行成功当安全验收通过。
2. 标准校验所用 `recovery_plan.validate_material` 要求 expected-data 的明确 typed encoding 和 source UUID 绑定；未知/旧设置 JSON 没有该结构。`NativeData.restore_database_settings` 要完整 schema 中的 DATABASE 定义，`restore_allocator_state` 要同一 expectedDataPin 的完整 schema，`database_readback` 使用完整或 affected-table typed row 观察，`formal_data_evidence.compare_data` 严格比较 schema、表集合、行 multiset 和自校验摘要。现有旧格式缺少这些证据，不能删除检查或填伪造 encoding/UUID 通过。
3. standard 构建来自认证冻结基线和 `ops/backup_engine/standard_fixes.py` 的限定 transforms。该文件明示“without replacing its data checks”，并保持 SAFE 读回/配置传递。本轮没有执行 transform、构建或从未安装包推断运行态；后续行为修改必须在两个实际交付包中分别验证。
4. MAIN 历史程序恢复已经接入：`recovery_program_restore.execute` 调用 `resolve_source_program` 绑定所选点最后 material 的五角色显式 versionPath 和原 `payload/original-application-images.tar`；随后完整 tar/config/layer 验核发生在保护/停止应用/导入与数据重置写入之前。已有独立 import、protection custody、generation/epoch、SQL staging/cleanup 和保留失败传递，不需要重写一套恢复编排。
5. 当前编排明确要求 archived mysql/minio/redis image ID 与目标实际登记服务相等，否则 `PROGRAM_DATA_IMAGE_BINDING_CHANGED`；切换仅 backend/frontend。五角色都必须绑定和验 tar，不代表允许启动五个历史数据服务。旧目标政策、历史 pin、实际 UUID、端口、writer、原归档保护和失败续办边界应全部保持。
6. `recovery_program_source` 的返回值只是 source material 合同，文档已明确不替代 lineage/source-scope/readback admission；轻量 `selected_chain` 也明确不验证 lineage/source/payload。因此页面有点、元数据可读、程序 resolver 成功与可恢复是不同证据阶段。

现有程序完整验核矩阵覆盖 7 个确切点：811ed843、84563ace、e98f0f55、9d1df93e、441bd02f、355910d5、be26b592。全部原 tar SHA、image config、layer 和五角色都经该已有报告验核；矩阵为 7 个 archive 文件、5 种唯一内容，不能说 7 种程序版本，也不能推到余下 101 点。r5 绑定矩阵有这些点 × 三服 = 21 对，明确 metadata-only，target runtime preflight/retained-history validation/真实 selections/业务恢复均 false。本轮重新核的是这些报告原字节 pin，没有再次读取 tar，也没有将程序 tar 成功用来修复 84563ace 的数据库/capture 元数据失败。

## 建议的最小正式合同与重构 API（待父审）

正式支持应按实际原 JSON 格式分派，拒绝把未知或损坏 typed evidence 自动转换成 legacy。源策略明确允许旧格式；默认缺此策略仍失败。未来按钮执行可自动识别已支持格式，但不能自动降低验收语义。

建议新增一个独立、可测试的数据库证据模块，复用原 SQL 导入、schema/data 观察和既有 MAIN 编排：

```text
resolve_database_evidence(material, *, read_original, guard, policy)
    -> CapturedTypedDatabaseEvidence | LegacyArchiveSqlInputs

derive_archive_sql_expectation(ordered_inputs, *, isolated_reference, runtime_pins,
                               guard, limits, output_root)
    -> ArchiveSqlDerivedDatabaseExpectation/v1 + original input/result pins

compare_archive_sql_replay(expectation_pin, actual_target_observation, *, guard)
    -> ArchiveSqlReplayComparison/v1
```

`resolve_database_evidence` 严格绑定 selected point、material/manifest、原 expectedDataPin、database 名、原数据库设置、完整基线及全部增量 SQL/raw/scope/capture pin；必须验证格式、点类型、UUID/位置、数据库范围及父链，不只接受文件名。Captured 分支保持原合同和原失败；legacy 分支保留原 `NOT_PERFORMED` 记录，不修改 material、归档、原 schema 或 targetProgramPolicies/v1。

`derive_archive_sql_expectation` 必须在独立空的参考实例，按实际已支持 MySQL image/client 与数据库设置，有界完整校验/解压/重放全部 SQL，再用现有正式观察器读取结构和 typed rows。不能从将要验证的目标自己生成 expected 再与自己比较，也不能凭 SQL import exit0 就产生合格 expectation。参考实例无来源/外部网络、无主程序 writer；SQL 中的数据库越界、DEFINER/权限/不支持语法、事件调度、警告/失败及非确定外部依赖均须正式约束或明确拒绝。

上述 expectation 是明确命名的“从归档 SQL 派生的补充数据证据”：独立新文件和 `supplementPin`，其原件链仍引用 manifest 中原 `expectedDataPin`；两者不替换、不相互冒充。补充证据放操作自有的私密证据目录，不写回归档 payload/manifest。原 typed 合同不增加“缺什么就从 SQL 补什么”的隐式路径。

派生记录最少绑定：所选点和有序链 pin、原 settings pin、每段 compressed/raw/scope pin、runtime/formal module/policy/budget pins、真实参考 UUID、原生执行退出、实际观察/比较 pin。派生身份必须标 `ARCHIVE_SQL_REPLAY_REFERENCE`，而不能伪造为备份时源观察的 UUID、时间或 source snapshot proof。缓存如需加入，键必须覆盖这些实际内容及版本，不能按“同一来源组”复用；缺失/漂移即拒绝，不回退为当前库观察。

`compare_archive_sql_replay` 证明“目标与受验归档 SQL 的独立重放结果一致”。建议返回明确 `archiveReplaySchemaDataEquivalenceVerified` 和 `verificationBasis`，同时保留 `sourceSnapshotEquivalenceVerified=false`、应用/生产证据的实际状态。现有依赖上一段 full/affected-data proof 的增量准入需要一个显式 tagged union：只允许同一严格链下的有效 archive-replay proof 继续，不能把旧标记强制填 true 或无条件放过上一段验证。原 typed-source 语义与未知终态处理保持不变。

若业务验收仍要求“原源全部冻结结构/数据/allocator 等同”，archive replay 不能补齐信息损失；该具体点保持阻塞，需独立原件。采用 SQL 重放结果作为旧格式的正式验收范围属于需父任务审定的业务合同，不是默认 fallback。本评估没有批准更弱成功语义。

最小集成位置为：统一 evidence resolver、标准 `validate_material` 的显式分派、NativeData 设置/allocator/读回的同一 tagged contract、增量前态证明以及对外结果的验证依据展示。已有程序来源/镜像、目标准入、protection custody、清库/停写、资源预算、SQL 导入审计、generation/epoch、失败保留和后续自动增量均复用，不另造旁路。轻量模式继续明确“不验证”，不把这次新增标准验收悄悄塞成轻量默认。

## 最小下一动作

1. 用本映射替代旧“13 组即覆盖 108 点”的 audit 聚合。保留 r1/r2/r3 原件；先把 22 点补入逐点待验列表，不触碰归档。
2. 针对 54 个正文未评估的 expected-data pin，及旧 inventory 缺失的 be26b592，设计一次有界、逐 pin、只读元数据核验；优先已有本机原件，若确需 NAS 由父任务按授权独立执行。只读核验记录格式、原 sha、source UUID/点绑定、完整/affected 范围，不读全量附件来做页面选择。
3. 对 44 个声明旧设置内容 pin 的点逐点核其完整链：16 FULL 和 28 INCREMENTAL。五个来源组仅作工作分批，不能复用代表结论。先选一个最小真实 FULL+增量链做合同 RED，保留 811ed843 的 6428017136 B SQL 资源/时间预算为单独大数据验证，不能用小样本覆盖。
4. 84563ace 原三个 metadata pin 失败单独保持；两未发布点单独核原发布/版本合同。没有原件不得补造 selector、manifest、version 或成功历史；其它点可独立推进。
5. 父审通过后才实施下节 TDD。新逻辑需实际 SAFE/FAST 双包验证、精确干净提交构建与新代次安装；当前 45/r6 和 c772 安装输入本轮完全冻结。任何真实数据恢复/三服矩阵均仍走原授权、经验门禁、Spug UI 与保留失败流程。

可立即由父任务安排的下一验证动作是：只根据映射中 `AFFECTED_OBSERVATION_PIN_BODY_NOT_REVIEWED` / `EXPECTED_DATA_PIN_BODY_NOT_REVIEWED` 的 54 个确切 expected-data pin，准备显式只读清单并逐 pin 保存独占本机副本、核 bytes/SHA、严格识别原格式；加核 be26b592 新程序绑定报告已指向的 point/manifest/material/binding 是否已有受验本机副本。每个对象采用既有公共 JSON reader 的有界约束及总预算；读取失败原样记录，不回退到同组代表。此动作不需下载大 SQL/tar/附件或运行 SQL，本评估未执行它。

有原 binding 的点同时沿其精确 `recoveryMaterialPin` 读取/复核 material，确认候选确为原 `database.expectedDataPin`、已归档 payload 成员及同点数据库输入。无 binding 的点先记录原合同缺口，不加入正式可执行材料。该绑定核对也适用于只命中已知内容 SHA、尚无逐点 material 正文的点。

真正需要补齐的原件与独立副本分四类：

- 54 个正文未评估的 declared expected-data JSON：目前只有原 pin，不得说原件不存在；先复用能按 pin 核等的既有本机副本，缺副本才按明确路径独立只读采集。
- be26b592 的旧 inventory 副本缺口：新程序绑定证据已证明有较新的元数据读取链，应优先定位它所绑定的原件副本，不按旧不可读状态重新定罪。
- 84563ace 三个预期原字节：本机已审副本不符、既有精确路径读取缺失，已有搜索不足以证明全局不存在；需原 expected SHA 的独立原件，现存替代字节或新程序 tar 不能修复。两未发布点缺正式 binding/发布依据属于另一类原操作合同缺口，不能造一份新 JSON 充当旧证据。
- 对精确源快照等同的要求：旧设置文件缺少源侧 schema/typed-row/allocator 观察，只有找到原始独立来源证据才能证明；新的 SQL 派生补充只能证明 archive replay，不是历史原件副本。

最后，数据库可重放与程序兼容须分开计量。已有部分 rehearsal 代表观察只有 3 张表，不能因归档中也有 backend/frontend 镜像就断言 MAIN 可以启动；五个 L 代表本轮甚至未读 SQL，不能推断它们都只有 3 表。对每个选择点仍须核应用数据库名/所需迁移与表、原程序配置/依赖、数据服务版本及三目标实际启动/业务健康。SQL 派生或比较通过不自动设置 applicationVerified，也不替代这些程序验证。

## BDD 与后续 RED / GREEN / REGRESSION 路径

以下为待实施场景；本轮没有运行测试，也没有以静态检查冒充 RED/GREEN。

| 场景 | Given / When / Then |
|---|---|
| 逐点覆盖 | Given 原 108 点目录和漏列 r3，When 构造 audit，Then 精确 108 唯一点且暴露 22 漏列，不复制代表 PASS。 |
| 正式格式分派 | Given pin 匹配的 typed evidence 或精确旧设置，When resolver 分类，Then 仅支持各明确格式；无策略/未知格式/错误字段/typed 自摘要损坏即拒绝，不能转 legacy。 |
| FULL 独立重放 | Given 真实有界 SQL 与旧设置，When 独立参考 MySQL 重放并观察，Then 得到真实 schema/data expectation 和原生/输入 pins，旧原件字节不变，源快照证明仍 false。 |
| 增量链 | Given FULL→多个实际 ROW/DDL 增量，When 选择末点，Then 精确按原链重放，绑定每段/endPosition/父证明；缺段、跨 UUID、分叉、越库、日志模式或 scope 不符均在目标写前拒绝。 |
| 不循环自证 | Given 目标与参考差一行、一列、索引、trigger 或 allocator，When 比较，Then 明确失败；不以目标生成 expected，不用 MAX(id)+1，不移除自增比较。 |
| 信息不可恢复 | Given 增量中未记录的失败分配号或 dump 未包含对象，When 无独立历史证据，Then 不产生源快照一致性声明，按正式验收范围显示具体未知/阻塞。 |
| 原件失败 | Given 84563ace 原 pin 不符、未发布点或输入运行中改变，When prepare/execute，Then 保留原失败和原件，拒绝重算 pin、自动补发或 silent fallback。 |
| 故障/资源 | Given 导入超时/警告/空间耗尽/参考退出未知/guard 漂移，When 派生或目标恢复，Then 原生事实和 pins 可追踪、目标保留且禁止自动重试；无伪造 expectation/READY。 |
| 实际双包入口 | Given SAFE/FAST 实际包新进程，When 走 resolver→constructor→worker，Then SAFE 传递并校验显式证据，FAST 保持既有未验证语义，模块来源、147 成员/输入 pins、结果字段与退出一致。 |
| 三服运行验收 | Given 每个具体点的原链、程序、保护与目标独立准入均通过，When 在真实 Spug 选择并恢复，Then 三服分别记录原生结果、结构/数据依据、附件/引用、Redis、程序/页面和实际失败保全，不用目录/镜像 PASS 代替。 |

建议测试顺序：先纯 resolver 的真实临时文件拒绝场景 RED；再实际隔离 MySQL 小型 FULL/ROW+DDL 链的真实行为 RED；最小实现 GREEN；随后现有 typed observation、allocator、SQL stream/import lifecycle、程序来源/镜像、protection/epoch/worker 及实际双包回归。真实服务器安装/恢复另行留证，缺依赖不得 skip 或 mock 成功。本轮仅提出路径，未编写或执行这些测试。

## 本轮执行证据与冻结

本轮命令仅为显式 UTF-8 本机 JSON/源码读取、`rg` 定位、标准库 SHA/唯一计数/父引用一致性核对，以及写本评估与专属映射。首次映射构造将报告的相对 `localFile` 当绝对位置读取，因 FileNotFoundError 在写出前停止；明确相对其所属 `archive-program-contracts-r3/<id>/` 解析后重新执行，未修改任何输入。最终本机一致性命令使用指定 Python `-X utf8 -`，实际 exit0，标记 `READ_ONLY_CONSISTENCY_PASS`，不是测试通过或恢复通过。

最终断言包括：108 唯一备份 ID 与 inventory 集合相等；13 代表/86 列点/22 漏列；107 manifest 的目录 SHA 相等；105 manifest/point/binding 及全部父引用 pin 相等；105 元数据路径到 FULL；7 点程序完整验核报告/21 目标绑定报告 pin 相等；411 个本机输入文件前后 bytes/SHA 保持；映射写后按 UTF-8 重读、108 点唯一。无网络、Docker、服务器、业务 SQL、归档载荷、运行配置写入、构建或提交。

父任务另行独立验证记录为 `legacy-point-map-parent-verification-r1.json`：423 个 pin（411 输入 + 12 当前源码）、共 198816263 B，逐字节/SHA 与身份核验 PASS，映射前后不变；实际 exit0、0.468 秒。父验证同样没有执行 SQL/payload/业务，105 条元数据链仍不代表载荷完整或恢复通过。

映射冻结：921197 B，SHA256 `96a43267c5409cf2f277f4f5e21570f5c83442aa8b5a2201f243f5aabc9a86e4`。现有 reader、生产/测试、原安装输入和共享日志不改。后续审查若要求扩大合同，另写事前设计与真实 TDD，不把本评估当实施授权。

适用经验归宿：`docs/experience-index.md`；`docs/release-agent-checklist.md` 的“覆盖前保留备份完整读回门禁”“增量恢复冻结自增状态门禁”“自动增量链与恢复周期门禁”。落实为：实际包与本地同名源码必须区分；归档声明/抽样不得代替完整读回；冻结 allocator 不得以重放猜测值替代；旧点与 epoch/保留失败原件不追认、不重写；后续服务器高风险动作前仍须父任务单独记录 experience-preflight。
