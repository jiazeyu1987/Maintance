# 正式备份与备份服恢复完整性审计

## 核查范围

用户要求分别检查正式服备份遗漏和备份服恢复遗漏。此次仅执行只读审计，没有启动备份、清空、恢复、重启、业务写入或NAS操作。另一线程同时推进新发布；本报告固定上一条已成功恢复的链，不能与新发布或新备份结果拼接。

- 正式源：172.30.30.57；业务库 `ruoyi-vue-pro`。
- FULL：`smallapp-8d9db80d8f1e4531ba9a0234335d0dcb`，manifest生成时间2026-11-16 15:30:57 UTC。
- INCREMENTAL：`smallapp-bf67a867d3ec4e369ca31657c45e62c6`，manifest生成时间2026-11-16 18:19:56 UTC。
- 恢复：`smallapp-9ddf6a1391f14bddb7af731a53f69a5e`，2026-11-16 22:25:52 UTC完成，目标172.30.30.59 / `spug-empty59-a029c09a7b8b`。
- 恢复点：`sha256:9d106914764c9e72cee2dd992c5a8c991a4ea2a36759f9d63aec438bdaa37c4e`。
- 实际补核窗口：2026-11-17 UTC；逐表事务、文件哈希与分段大表读取分别观察，目标未停写，不能把多次观察称为同一个全局快照。

## 1. 正式服备份有没有遗漏

**这条链覆盖主程序数据，但不是整台正式服务器的全量备份；存在明确的范围外持久化数据。**

已核实链内包括：业务库907张表、15,957个字段、62个触发器；MySQL全量与无断点增量；MinIO全部3个bucket及`.minio.sys`；Redis DB1快照；应用镜像与配置。FULL结束与增量起点都是`binlog.000033:117969259`，增量结束`121470445`。源端业务库以外仅有MySQL系统schema；MinIO实际顶层目录与配置范围吻合。

归档逐项stat：FULL 14,359个载荷引用、26,106,043,182字节，增量91个引用、2,125,525,741字节，**清单引用缺失0、大小不符0**。原暂存目录的载荷已按成功后的staging-cleanup删除，归档迁移后的引用仍存在，不能误判成漏备份。源文件引用清单9074行、8786个对象引用，已记录的源缺失对象0。对象版本清单5916项；实体物理文件与对象版本数量不是相同统计口径。

| 正式机现存数据 | 本链覆盖情况 | 只读盘点 |
|---|---|---|
| 发票助手runtime/uploads/results | 未纳入数据库或MinIO物理范围 | 27,050个文件，3,006,098,356字节 |
| 分贝通助手本地/data | 未纳入本链 | 4个文件，75,788,418字节 |
| OnlyOffice独立PostgreSQL/RabbitMQ/Redis/Data等卷 | 未纳入本链，恢复目标也未配置该服务 | 容器实际挂载已核实；未递归读取这些卷的业务内容 |
| 后端运行日志、展厅独立静态目录等宿主目录 | 不属于本链的业务库/MinIO数据范围 | 挂载已盘点；静态目录35文件、7,153,171字节 |

上述是**本条备份链的范围缺口**，不等于断言机器上不存在其他独立备份，也不把所有OnlyOffice缓存判为不可重建业务主数据。若验收目标是整台正式服灾难恢复，需要逐项确定owner、权威数据、备份归宿与恢复验证。

还存在时间点差异：正式库现有909张表，新增`mes_pro_loss_reason`、`mes_pro_loss_reason_sequence`，创建时间2026-11-17 12:59:54（服务器返回值）；旧冻结点只有907张表，备份服没有这2张。它们晚于旧备份点，属于新发布尚未覆盖的变化，不能归因于恢复漏表。

备份原回执的`payloadContentVerified=false`、`serverDurabilityVerified=false`。实际最小仓库路径明确禁用了全载荷回读；清单完整和SUCCEEDED不能单独证明全部载荷内容、独立持久化与灾难恢复能力。本次补做了所有清单引用的存在/大小检查及目标业务附件全量内容检查，没有重读所有镜像和SQL归档内容。

## 2. 备份服恢复有没有遗漏

**已完成的核对未发现缺表、字段、触发器或业务附件漏恢复。原流水线存在明确的全量校验缺口，不能把恢复SUCCEEDED直接写成全量等价。**

- 数据库907张表全部存在，0缺表、0额外表；901张行数与冻结点相同，另外6张是访问/错误/登录日志及OAuth令牌表，行数增加。按主键取冻结点原有记录重新计算完整行多重集指纹，6张均与冻结点完全相同，证明原有记录仍在，新增记录来自恢复后的运行。
- 结构目录逐项相同，所有907张表和62个触发器定义已比较。6张新增日志/令牌表的定义差异均仅为AUTO_INCREMENT变化；没有字段、索引、触发器定义遗漏。历史`SHOW CREATE TRIGGER.Created`依既有协议不参与比较。
- MinIO冻结点9,413个物理文件全部核过：9,370个现存文件读取SHA-256，9,342个业务bucket物理文件全部一致，业务文件缺失0、内容不符0。其余43个缺失、10个指纹变化均在`.minio.sys`临时回收站、heal或用量统计状态，不是业务附件缺失。空bucket `edhr-protected-storage`无业务物理文件。全量文件清单及增量52个变更、61个删除与最终清单的载荷覆盖已核对。
- Redis原快照DB1有0个key，恢复回读同为0，值及绝对过期时间校验通过；当前正式Redis已有新key，不能用当前数量倒推旧快照漏数据。队列在本链声明NOT_PRESENT，不把OnlyOffice自己的RabbitMQ混入该主程序声明。
- `infra_file_config`恢复时有明确适配回执：配置28的endpoint、accessKey、accessSecret改为目标MinIO。`system_users`与`qrtz_triggers`行数相同而内容指纹不同；已确认恢复后有用户登录，目标调度器运行。登录字段/触发时间变化是合理解释，但本次没有旧行级差异证据，仍保留这两表的内容差异未完全归因，不能无条件判全库完全等价。

完整内容指纹补核已结束：**907张表中898张与冻结点完全相同，6张日志/令牌表原有记录完整保留，1张文件配置有明确目标适配，2张运行表的差异尚未完全归因。** 最后一张`showroom_release_asset`的4,870行按连续范围读取，聚合后行多重集SHA-256也与源冻结证据完全相同。最终结果见`audit-summary.json`。没有把超时或部分读取预先写为PASS。

## 原流程的证据缺口

数据库两个恢复步骤都写明`verificationState=NOT_PERFORMED`、`fullSchemaDataEquivalenceVerified=false`、`incrementalReplayAndAffectedDataVerified=false`。附件比较也写明`state=NOT_PERFORMED`、`payloadContentVerified=false`、两步`completeTreeReadback=false`。原来只有8张表计数和附件样本的验收不足以支持“没有遗漏”；本报告的全结构、907表行数、全业务附件哈希和补做内容指纹是新增证据，不回填或修改历史回执。

## 证据与限制

`source-boundary.json`、`source-scope-gaps.json`、`source-coverage.json`对应备份范围与载荷检查；`target-schema.json`、`target-all-counts.json`、`target-historical-data.json`、`target-data-*.json`、`target-large-*.json`、`target-files-*.json`、`target-adaptation.json`为只读补核。`target-verification.json`保留原恢复验证状态。各probe和`aggregate_evidence.py`保留可复核命令意图，输出只含元数据/计数/哈希，不导出业务行值、密码、token或私钥。

结论仅适用于上述冻结链与检查时目标；新一轮发布和备份需按自己的备份点另行验收。此次审计不修复范围缺口，不补备份或重跑恢复。
