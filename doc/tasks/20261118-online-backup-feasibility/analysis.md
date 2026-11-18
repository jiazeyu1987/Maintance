# 不停服备份可行性

结论：全量和增量都可以设计成服务保持在线的备份。当前实现尚不具备此能力，需要同时调整数据库、附件捕获和共同恢复点合同；不能直接删除stop或数据库只读步骤。

## 当前实现边界
- minimal_capture_worker.capture_locked无条件停止writerContainerIds并设置MySQL read_only/super_read_only，保护持续覆盖capture_protected_materials。
- recovery_capture_materials._capture_database对FULL执行导出前后逐表内容观察；INCREMENTAL观察受影响表，仍使用同一停写保护。
- capture_protected_materials还会停止MinIO，复制minioDataPath下的物理数据，再启动MinIO并复核对象和数据库位置。仅使MySQL在线不能消除整个流程的停服。
- 当前严格校验假定源数据在整个窗口不变；在线化必须改为校验被冻结的同一视图，并保留真实恢复验收。

## 两种可用性目标
| 目标 | 设计要求 | 边界 |
|---|---|---|
| 服务在线，建立恢复点时短暂限制写入 | 应用继续提供读取；建立覆盖全部writer的写屏障，等待在途事务和对象操作完成；冻结数据库视图及附件版本清单/一致快照，固定日志坐标；解除屏障后从独立可保留视图复制、压缩、校验 | 所有HTTP、后台任务、外部writer都必须受控；必须证明解除屏障后旧视图不会改变或被清理；短暂程度需实测，不保证秒数 |
| 服务在线，业务全程继续写入 | 数据库一致快照及连续binlog；附件不可变版本、版本保留和删除记录；业务记录绑定对象版本，或具备等价共同检查点协议，选定可恢复的共同截止点 | 数据库和对象各自在线或复制成功不足以证明跨存储一致；需要正式设计、兼容旧数据和并发恢复验证 |

对现阶段，优先评估第一种目标：把大文件复制与逐表校验从业务停写窗口移到独立不可变视图。若业务要求全程持续写入，再按第二种目标设计版本/检查点协议。底层一致组快照、版本化对象读或专用副本是待评估机制，不能直接假定现网已具备；专用副本也不能代替独立备份和共同恢复点。

## 官方能力与限制
- MySQL手册说明mysqldump --single-transaction可在InnoDB上以一致读导出而不阻塞应用；该保证不覆盖MyISAM/MEMORY等非事务表，导出期间还必须控制ALTER/CREATE/DROP/RENAME/TRUNCATE等DDL。该能力只解决数据库视图，不自动覆盖附件。来源：[Oracle MySQL 8.0官方手册](https://docs.oracle.com/cd/E17952_01/mysql-8.0-en/mysqldump.html)。现网版本和表引擎本次未核实。
- MinIO AIStor官方文档提供对象版本ID，支持按指定版本读取；无版本ID的删除生成delete marker，但按版本ID删除会永久移除该版本。因此版本化方案还必须保护备份依赖版本和删除语义，不能只开启versioning。来源：[MinIO对象版本官方文档](https://docs.min.io/aistor/administration/objects-and-versioning/versioning/)。该文档证明产品能力，未验证现网MinIO版本、发行版和bucket配置兼容性。

## 实施前必须验证
数据库版本/引擎、DDL与日志保留、全部writer、对象版本及生命周期、底层存储拓扑/快照或副本容量、恢复点与恢复时间目标。测试须覆盖并发写入和附件增改删、在途操作、日志/版本丢失、全量及连续增量链恢复；以共同截止点的数据库、附件及真实页面一致作为验收。

## 本次范围
只做分析和文档记录，未操作服务器、未中止或恢复现有备份、未改变产品行为。未承诺当前已能不停服或任何未经实测的停写时长。
