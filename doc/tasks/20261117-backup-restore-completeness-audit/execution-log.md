# Execution Log

- 用户需求：检查正式服备份是否漏数据、备份服恢复是否遗漏。
- 前序任务20261117-inspect-process-thread已completed；本任务是独立完整性审计，不接管正在执行的发布任务。
- 只读UTF-8 bootstrap完成，读取AGENTS、前序任务状态、experience-index、powershell-memory。
- BDD: 备份覆盖 -> Given 正式源业务数据和实际备份链，When 比较冻结范围与清单，Then 明确遗漏、范围排除和已验证覆盖。
- BDD: 恢复覆盖 -> Given 同一备份点及.59恢复结果，When 比较schema/data pin和对象清单，Then 明确恢复遗漏与运行配置必要差异，不以少数表样本替代全量。
- 本任务无产品行为变更，不适用实现RED/GREEN；检查命令必须如实记录原始结果。

## Read-only Preflight
- 读取命中经验：docs/server-access.md、docs/release-backup-restore.md、docs/release-agent-checklist.md中的自动增量链与恢复周期、Spug恢复包接口、原始回读/全量数据门禁。生产仅只读，未触发高风险写入执行。
- 前序自有任务completed；当前检测进程线程正在新发布/验收/旧操作查询。先使用read_thread取历史身份，后用wait_threads(timeoutMs=0)取紧凑即时状态；不发送消息或接管并发执行器。
- 命令入口：本机固定Python UTF-8执行remote_read.py；使用server-access已确认的SSH identity和known_hosts，StrictHostKeyChecking/BatchMode/IdentitiesOnly。通过Python stdin传递只读probe，不在服务器创建脚本，不输出凭据。已验证源MySQL UUID、目标UUID、准确容器名与运行状态。

## Milestone 1 / Chain
- GREEN: probe_source_metadata.py、probe_source_scope.py、probe_target_metadata.py、probe_target_verification.py -> PASS，读取原result/manifest/point/recovery-material/readback，关键JSON pin重算bytes与SHA-256。
- FULL smallapp-8d9db80d8f1e4531ba9a0234335d0dcb -> INCREMENTAL smallapp-bf67a867d3ec4e369ca31657c45e62c6 -> RESTORE smallapp-9ddf6a1391f14bddb7af731a53f69a5e；同一个generation/parent身份及恢复点9d106914...。
- FULL终点与增量起点binlog.000033:117969259，增量终点121470445。归档迁移后引用有效；成功后的原capture staging载荷清理不是漏备份。

## Milestone 2 / Backup Coverage
- GREEN: probe_source_coverage.py、probe_source_boundary.py、probe_source_scope_gaps.py -> PASS。仅docker inspect安全字段、数据库只读schema/count查询、文件stat、Redis INFO keyspace、目录计数；没有停止服务或读取业务行值。
- FULL 14,359 payload refs/26,106,043,182 bytes；增量91 refs/2,125,525,741 bytes。引用缺失0、大小不符0；所有MinIO实际顶层scope均入配置。
- 907张冻结表、15957字段、62触发器；源业务库当前909张，2张mes_pro_loss_reason相关表在新发布后创建。备份范围未含发票助手3,006,098,356 bytes、分贝通75,788,418 bytes、OnlyOffice独立卷等。详情见source-scope-gaps.json。
- 原仓库最小路径payloadContentVerified=false、serverDurabilityVerified=false；本机实际代码repository_minimal.py明确payload_content=False/verify_content=False。作为证据缺口暴露，不当成有数据丢失的证明。

## Milestone 3 / Restore Verification
- GREEN: probe_target_counts.py -> PASS，单只读一致性事务核907表行数。0缺表/0额外表；901表一致，6日志/令牌表增加。
- GREEN: probe_target_schema.py -> PASS，SHOW CREATE和information_schema逐项核907表/15957列/62触发器；6表DDL不同仅AUTO_INCREMENT，结构目录与其余定义一致。
- GREEN: probe_target_files.py batches 0..4，以及batch2尾段5541..6000 -> PASS，9413预期物理文件均访问检查；9370现存文件哈希、43缺失临时文件；业务9342物理文件全部哈希一致，缺失/不符均0。全部差异仅在.minio.sys临时回收/heal/统计状态。总读取9,656,139,956 bytes，单次限制48秒，batch2部分读取后明确completeBatch=false再补尾段；不把部分读取计完整。
- GREEN: probe_target_data.py batches 0/1/2/3a/3b-before/3b-after/3c/4 -> PASS，906表typed-row-multiset内容观察完成；9表指纹与冻结点不同。大表showroom_release_asset独立分段处理，尚未完成前不计PASS。
- GREEN: probe_target_large_table.py -> PASS，0..4870范围连续无重叠，所有4870行完整多重集SHA-256与冻结证据3ebcbdac...完全相同。前期有界分段也曾超时，失败不计入输出；最终直接类型单元编码行哈希分段均完成。
- GREEN: aggregate_evidence.py -> PASS，最终907表内容证据齐全，898表完全相同、6表历史记录完全相同、1表配置适配、2表运行内容差异未完全归因；9413物理文件核对覆盖完整，业务9342文件无缺失/哈希差异。审计验证通过指证据聚合与事实核查完成，不代表被审系统的完整性缺口已修复。
- GREEN: probe_target_data.py --historical -> PASS，6日志/令牌表按id取冻结点数量的原记录，6/6完整内容多重集指纹与源一致，新增数据不掩盖原有记录。
- GREEN: probe_target_adaptation.py -> PASS，原prepared-file-storage回执明确id28变更endpoint/accessKey/accessSecret；1个用户恢复后登录。未读取或输出密钥值。system_users/qrtz_triggers行数相同但内容不同，运行写入是合理解释，未获得旧行级差异证据前保留未归因范围。
- 原数据库回执fullSchemaDataEquivalenceVerified=false、incrementalReplayAndAffectedDataVerified=false、verificationState=NOT_PERFORMED；原对象payloadContentVerified=false/physical comparison NOT_PERFORMED/completeTreeReadback=false。Redis独立回读确认DB1原0 key恢复0 key，valuesVerified/absoluteExpiryVerified=true。

## Probe Failures and Corrections
- 辅助脚本初次输出了过大的形状/文件路径清单，后改为聚合计数并收敛输出；读取目录错误与Windows rg通配符错误均已暴露并修正，未据此产生通过结论。
- 大表所在初次全批查询触发MySQL ERROR 3024或进程timeout124，输出未采信。按表范围拆分确认其余表；showroom_release_asset无JSON节点但含大体积二进制内容，改用相同_cell类型编码的直接行哈希和有界主键排序范围读取，免去窗口CTE开销。
- 分段首次读取了0..1000、1000..1250、1250..1500；后续1500..4870按250行有界读取。最终聚合必须验证范围无间断/重叠、总4870行和完整多重集哈希一致，不能用分段数量代替内容证明。
- 没有添加fallback、mock、跳过错误或修改原验收状态；失败的完整批次不生成可计入聚合的成功JSON。

## Closeout
- 没有产品代码、远程业务数据、NAS、worktree、控制台配置变更；未启动后台服务或真实E2E。
- 所有本任务有界SSH/SELECT/hash辅助进程结束后，才完成聚合、记录和最终提交。其他线程、进程及worktree均保留。
- GREEN: UTF-8重读63文件、全部JSON解析、单文件体积检查、907表证据齐全、9413文件核查覆盖、9342业务SHA-256无差异 -> PASS。
- 本任务无实现提交；只读审计交付与最终任务记录独立提交。request-command-log使用HEAD基线仅暂存本任务追加条目，保留已有其他任务未提交变更。
- Current Status: completed。备份范围缺口和两表内容未完全归因作为审计发现交付，不伪装成修复或完整性验收PASS。
