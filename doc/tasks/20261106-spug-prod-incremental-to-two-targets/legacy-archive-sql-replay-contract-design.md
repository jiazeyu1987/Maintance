# 旧设置点的归档 SQL 补充证据最小合同

## Current Status

completed（限定设计完成，未实施）。承接旧 schema 只读评估及父任务新的本机读回衔接；原 108 点映射冻结，不修改产品、测试、原件、登记配置或运行环境，不访问 SQL/NAS/Docker/远端。当前真实 UI/回归运行资源由父任务独占。

## 目标与验证

为 44 个 manifest 声明命中旧设置内容的点定义有限 `ARCHIVE_SQL_REPLAY_REFERENCE` 合同，保留原 expectedDataPin，明确数据库可回放与 MAIN 程序/业务兼容的不同准入。给出当前正式入口、必要传播字段、逐点阻断条件与后续 BDD/TDD 次序。先核父衔接报告原 pin 和当前代码，再完成设计；本轮不实施或运行测试。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。只显式支持经核原格式及点/程序/目标组合，不以旧设置为自动放行条件。
- 是否从根因和长期维护角度解决：是。单一补充证据、有限准入分派、复用现有 SQL 和数据观察器。
- 是否存在临时补丁或绕过：否。不重签旧证据、不改原 pin、不建立通用转换平台。

## 经验门禁

- Trigger：旧设置不含 SAFE typed schema/data 证据，需要明确支持归档回放验证。
- Preflight check：核父新报告 SHA、原 108 点映射及当前 SAFE/FAST 接缝，区分历史真实读回与新采集，不重复读取 NAS。
- Blocker：原件不符/缺失、未发布合同、格式未知、参考重放未知、程序/目标不兼容或实际入口未传播。
- Verification：本文只产出可执行设计和有限 BDD；真实 RED/GREEN/双包及 UI 验证由后续批准实施阶段执行。
- Forbidden action：不改 frozen map、产品/测试/运行配置，不下载/运行 SQL，不用代表/3 表演练库冒充 MAIN 兼容，不重复已验完整读回。
- Evidence：`legacy-unreviewed-readback-reconciliation-20261110-r1.json`、旧评估与映射、当前源码；经验归宿为 `docs/release-agent-checklist.md` 的实际封包配置传递、覆盖前完整读回、allocator 和保留失败门禁。

## 当前事实与边界

本轮核等父报告 `legacy-unreviewed-readback-reconciliation-20261110-r1.json`：149203 B，SHA256 `fa1c1f745630ef45ab55a9f7f31e50c9ed7ad092fa71b761bd2bc1e16d63d888`。原 54 个待评估正文中，50 个 typed 正文通过、53 个 material 及其 expectedDataPin 引用匹配；4 个原正文不符。父已核验的 155 个完整读回原件继续作为既有证据，无需为本设计重读 NAS。正文通过也没有证明备份时点源快照或真实恢复。

4 个正文失败点为 `smallapp-d62276cdb402499d9586871439765989`、`smallapp-d314a62839b84934934ce80bca8c66ce`、`smallapp-e98f0f55896c445dac1d4eefe31713c5`、`smallapp-9d1df93e86b549c08b0c6286f7a35b7d`。它们不是本次旧设置分支的入口；不得用派生参考替换损坏 typed 原件。首点同时缺完整 material 匹配，另外三点的 material 匹配不能抵消正文失败。

原冻结映射的 44 个旧设置候选是 16 FULL、28 INCREMENTAL，声明 `LightweightDatabaseSettings/v1`，只含数据库定义。42 个声明同一 rehearsal 设置内容，2 个声明另一业务库设置内容；这不是 44 个 SQL 内容已核或已恢复。`smallapp-9695bf3fb95d4ec4a19eb6fbe6329066` 仍是 unpublished 且缺原 binding 的独立阻断点，其余 43 个有旧 binding 副本也不等于逐点全部准入通过。部分历史演练观察仅 3 张表，不能外推全部 42 点均为 3 表。

原 108 点映射保持 921197 B / SHA256 `96a43267c5409cf2f277f4f5e21570f5c83442aa8b5a2201f243f5aabc9a86e4`。父 `legacy-point-map-parent-verification-r1.json` 已核 423 个输入 pin；105 条 metadata chain 仍不等于 payload、SQL 回放或 MAIN 业务恢复通过。

## 唯一补充合同（拟实施，当前不存在）

新增有限模块 `ops/recovery/recovery_archive_sql_reference.py`，不改旧 manifest/material/expectedDataPin，不生成“替代 expectedDataPin”。每个旧点显式登记一个独立私密文件 pin：`owner.sources[sourceRef].archiveSqlReplayReferencePins[pointRef]`。同一设置 SHA 或同组代表不能代替逐点记录。文件固定 schema `ArchiveSqlReplayReference/v1`，未知键/类型/方法拒绝，最小字段如下。

| 字段 | 严格内容与用途 |
| --- | --- |
| `schemaVersion`, `verificationBasis`, `sourceSnapshotVerified` | 固定 `ArchiveSqlReplayReference/v1`、`ARCHIVE_SQL_REPLAY_REFERENCE`、`false`；无“备份时点源观察通过”字段 |
| `sourceConfigRef`, `recoveryPointRef` | 与请求及原 point 身份完全相等 |
| `orderedStepBindings` | FULL 至该点的完整有序前缀；每项固定原 `pointPin/manifestPin/materialPin/originalExpectedDataPin`，不得只存 ID/SHA 或改变原件 |
| `referenceRuntimePin` | 实际隔离回放的 MySQL 镜像 ID、版本/配置、导入器/观察器代码与限额的固定运行输入原件；不使用当前 live 源数据库 |
| `referenceExecutionPin` | 该前缀实际执行收据原件；逐步绑定 material 中原 SQL/rawSql/capture/scope 或 binlog segment pins、展开 SHA/bytes、导入终态、起止位置及前一步结果 pin；不得仅自述 PASS |
| `observedDataPin` | 该前缀真实结束状态的完整 typed schema/row-multiset 观察，使用现有 `formal_data_evidence.observe_data` 原格式及自身校验；其 observationIdentity 是隔离参考库真实 UUID/container，不伪装为 sourceDatabaseUuid |

`orderedStepBindings` 固定原件后，SQL/capture/binlog 等有效字段从已核 material 读取并与执行收据逐项核等，不再建立另一份可漂移的 SQL 清单。每个 legacy 前缀都有自己的参考记录和观察；不是只给最终点一份参考而跳过中间增量读回。已核 typed 点仍走原分支。仅支持当前正式 importer 已支持的 FULL/BINLOG_SQL/MYSQL_BINLOG 方法、原数据库名和原 SQL；未知方法、跨库改名/改写 SQL、缺旧原件均拒绝。

参考必须在获准、空且隔离的环境中用原 SQL/原顺序真实生成，再固定 pin。SQL 可以证明其实际重放得到的 schema/行/数据库设置和 allocator；它不能补回备份时未采集的源端行状态、未落 SQL 的 AUTO_INCREMENT 预留或源端业务健康。不能用 `MAX(id)+1` 猜 allocator，也不能把参考 UUID 代入原 material/source identity。若要求精确原源 allocator 而原件缺失，该要求仍阻断；回放参考只能声明 SQL 可重建的状态。

拟正式 API 为 `resolve_archive_sql_reference(source, request, chain, *, guard, reader)`：无 Docker、无 SQL、无自动搜索，校验显式映射及所有 pin/前缀/运行收据，返回固定 basis、原 expectedDataPin、参考 observation pin 与解析值。typed 原件失败不会调用它；必须先核原件，只有精确识别且显式登记的旧设置才分派。补充原件缺失/不符、位置不连续、参考未成功或超限，在目标数据写入前失败。

## 精确产品接缝与传播

| 当前入口 | 必要最小改动边界（后续 TDD） |
| --- | --- |
| `recovery_plan.resolve_chain` / `validate_material`（101 / 187） | 保留现全部原件、完整载荷、scope、lineage、版本与对象校验；显式传入已核 step 证据选择。原 typed encoding/UUID 校验原样；legacy 仅从上述 resolver 获取独立参考，不覆写 material |
| `recovery_data.NativeData.restore_database_settings`（398） | legacy 用原旧设置定义并核其数据库名/内容，引用参考 schema 交叉核等；保留空库、真实 UUID、ALTER 意图与读回；不能继续把旧设置当 typed proof |
| `NativeData.database_readback` / `restore_allocator_state`（608 / 582） | legacy 完整 observe_data/compare_data 对照派生参考，保留真实两端 UUID 与原始观察 pin；allocator 操作必须标同一回放 basis、先核其它完整 schema，不冒充源 frozen 状态；typed 路径原样 |
| `NativeData.incremental_database`（473）及 `incremental_captured_sql`（504） | 前序结果仍须属于当前操作/精确前点、同一目标 UUID、end=start；只新增严格验证 `archiveReplaySchemaDataEquivalenceVerified=true`、basis、参考 pin/前序结果 pin 的显式分支，不放宽原两个验证布尔，不接受任意 true |
| SAFE 构建 `ops/backup_engine/standard_fixes.py` / 实际封包 `common/recovery_minimal_runtime.py` | SAFE 使用已认证冻结 baseline，不等同工作区 lightweight 同名源码；必须将证据选择传进真正 NativeData 构造、每步 material 和结果，再验证实际 standard/lightweight 封包新进程。不能只改源模块声称 SAFE 支持 |

legacy 数据步骤及最终聚合新增 `verificationBasis=ARCHIVE_SQL_REPLAY_REFERENCE`、`archiveSqlReplayReferencePin`、`archiveReplaySchemaDataEquivalenceVerified`、`sourceSnapshotVerified=false`。原 `fullSchemaDataEquivalenceVerified` / `incrementalReplayAndAffectedDataVerified` 源观察准入布尔在该分支不冒充 true；`applicationVerified` 继续独立。链中任一步用补充参考，最终结果必须保留此限定，不因后续 typed 点而隐去。原 typed、旧失败、custody/generation/epoch、SQL cleanup/超时/保留部分目标规则保持。

轻量现状：`recovery_minimal_runtime.MinimalData.restore_database_settings`（155）已有旧设置读取，`database_readback`（206）明确 `NOT_PERFORMED` 且两个验证布尔 false；不能据此称 SAFE 已支持旧 schema。`recovery_control_smallapp_native.Native.resolve`（317，MAIN 检查 364）仍要求 `supports_registered_main_targets=true`，不得开启 lightweight MAIN。

路由只传播 pin：`recovery_control_restore_catalogue._bind_archive_chain`（161）与 `for_request`（310）已经深拷贝 source/owner；新 source 字段应保留进 immutable request owner 并受 guard 监控。`archive_references`（343）的 `archiveRestoreCatalogues[sourceRef].source` 和三目标 restore owner 的同一 source 必须携带同一显式映射，部署时验证全等。最终 owner CLI 为准，浏览器不能传参考/证明布尔。七字段 UI request、`sourceConnections/selectionConnections/targetConnections`、旧查询指纹/认证和 `recovery_target_sources.admit_target_source` 合同不变，尤其不能改目标原 `sourceConfigRef` 来接旧库。

当前 `Native.selections`（1436）提供每源点列表及目标可用列表，未表达逐点 MAIN schema 兼容，`freshTargetConfigRefs` 不能当所有历史点都已通过。最小执行准入由选中点的 owner 解析返回明确失败码；如需页面提前说明，只给既有点行增加只读 basis/blockedReason，沿同一显式目录连接读取固定参考元数据，不在页面选择时运行 SQL 或全载荷检查，也不新增连接/通用转换入口。完整载荷校验仍保留在真实执行写入前。

## MAIN 兼容是另一道门

3 表演练库即便 SQL 回放与参考完全相等，也不满足父当前核实的 MAIN 15 表业务基线；不得新建缺表、改库名或灌入当前数据使其变成 MAIN。15 也不是“表数等于 15 即通过”：必须由所选归档 backend/frontend 与原配置/迁移要求确定表名、字段/约束、必要数据和依赖，核实际参考完整 schema。未有该版本精确业务结构合同的点保持 `MAIN_SCHEMA_COMPATIBILITY_UNPROVEN`，不得从代表或当前版本猜测。

这里不新增通用兼容 profile 平台。后续在 `recovery_program_restore.execute`（231 起，原程序解析/数据服务绑定 244–246）取得原五角色程序材料后、保护/停服/导入/重置前增加一个有限 `require_main_schema_compatibility` 检查；输入为所选点参考 schema pin、该点归档程序及配置 pins、目标原登记的业务要求原件，缺任一原件即拒绝。MAIN 当前 `recovery_main_health.preflight`（100）检查服务端点，`wait_healthy`（143）检查 HTTP/backend UP，不能代替这一结构门禁；真实启动/页面业务验收仍必需。SQL 回放证明不自动设置 applicationVerified，不弱化现有 `PROGRAM_DATA_IMAGE_BINDING_CHANGED`、原 tar 全验或目标隔离。

## 有限 BDD / 首 RED 与后续验证

本轮只设计，未运行下列测试。先固定场景，再 RED → 最小实现 → GREEN → 原合同回归。

1. **首 RED：真实旧设置 FULL 到 SAFE 读回。** Given 精确 point/material/旧 expectedDataPin、真实小 SQL 隔离回放参考及受限空目标，When 走实际 standard 包配置/构造与 FULL，Then 原 pin 不变、设置/行/DDL 与参考全等，结果 basis 限定且 sourceSnapshotVerified=false。当前 SAFE 的 typed encoding/格式要求会拒绝该输入；记录这一真实失败，不在测试先造新模块成功。
2. **增量前序不可伪造。** Given 同一原 FULL+increment 链及每个前缀参考，When 实际 SAFE 按序回放，Then 每步 UUID/end/start/前序结果/参考 pin 完全绑定；删一项、换目标 UUID、换前点参考或自报 true 均写前拒绝。保留 typed→legacy、legacy→typed 的有限混合链边界。
3. **原 typed 失败不降级。** Given 原 typed pin 内容不符或编码/UUID 非法，即使目录含同名补充 pin，When resolve/validate_material，Then 保留原失败，不启动参考回放、不写目标；四个本次正文失败点不能被此功能“修复”。
4. **3 表回放不等于 MAIN。** Given 真实旧演练 3 表参考与已核 MAIN 15 表结构要求，When 走 MAIN 程序入口，Then 结构门禁在保护/停服/数据库与对象写入之前拒绝，原目标保持；无精确程序要求原件也拒绝。另用实际兼容业务库正例证明完整门禁后仍须真实健康/业务验收。
5. **逐点原件与来源不可替代。** Given 同设置 SHA 的两个不同 point/source 或缺 binding 的 unpublished 点，When 换用代表参考、缺 pin、改 SQL/runtime/前缀任一字节，Then 原件/内容绑定失败且不写；原 point/manifest/material/设置副本均保持。
6. **实际路由/封包不丢证据。** Given 显式三来源/三目标登记，When 正式 catalogue→Native.resolve→immutable owner→实际 SAFE 新进程→首 DB 边界，Then 参考映射和 guard 到达真实构造，旧路由/历史/认证保持。lightweight 仍拒 MAIN，原 typed/source strict 回归全部保持；不得用 SimpleNamespace/手填已解析对象证明配置已贯穿。

下一验证动作仅需现有本机原件：逐点对 44 候选核旧正文、material 引用及完整前缀，先剔除独立缺件/未发布点；从实际业务库 FULL 选择结构/程序原件齐全的一点作为正例，真实 3 表演练作为负例。此前读回已经核等的原件复用，不为 metadata 缺分类重读 NAS。仅当某点确实缺 SQL/程序/原 setting 独立副本时列出该 pin 的精确路径、SHA 和缺口，再单独申请所需采集；不据目录代表推断所有点可用。父当前自动 FULL、UI 与 r10 独占资源期间，本设计不派发 SQL、Docker、NAS 或远端动作。

## 本轮完成证据

完成父新报告/冻结映射身份核对、现有产品接缝只读检查及此独立设计。未改实现/测试/原映射，未执行测试或恢复，未重签旧证据。实施仍需上述逐点缺件清单、精确 MAIN 版本结构要求及隔离真实回放条件，并经父审后启动严格 TDD。本设计完成不表示 44 点或 108 点已可恢复。
