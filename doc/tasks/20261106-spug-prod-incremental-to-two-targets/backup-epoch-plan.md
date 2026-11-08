# 恢复后源备份周期

## Current Status
in_progress — 初版 Linux 真实 flock 与控制器边界已验证；独立审查新增终态元数据收口缺口，按正式 reconcile 合同继续 RED/GREEN。

## 目标与里程碑
- [x] 定义固定来源、数据库和共享物理锁绑定的恢复周期策略。
- [x] 真实文件 RED：旧实现没有恢复周期，无法令恢复前备份失效。
- [x] 在首次数据库破坏性写入之前追加不可变恢复边界；完整恢复成功及写入后失败均留终态。
- [ ] 覆盖路径逃逸、符号链接、错误锁、跨源、改写历史、并发及未闭合周期拒绝（跨平台文件测试通过；Linux 特有项待统一执行）。
- [ ] 与后端计划模块集成后由根任务完成实际封包、安装和真实流程验证。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。启用策略但记录缺失、损坏或恢复未闭合时明确阻塞，旧备份不会被猜测为新周期。
- 是否从根因和长期维护角度解决：是。数据库 UUID 在原实例恢复中不变，因此使用正式、持久、不可变的恢复边界。
- 是否存在临时补丁或绕过：否。旧归档不改写，绑定保存于原生控制登记，由捕获前后相同周期与点摘要共同约束。

## 合同
`SourceBackupEpochPolicy/v1` 固定 root、sourceIdentity、databaseUuid、sourceLockPath。root 由安装阶段显式创建；读取不创建初始化记录。恢复流程在已经持有同一物理锁时，于首次 DROP/CREATE 之前追加 REPLACING 事件；成功后追加 READY，写入后失败追加 FAILED_RETAINED。事件包含严格递增序号、前事件摘要、固定策略摘要和证据 pin，文件只追加、不覆盖。

源控制配置可选 sourceEpochPolicies[sourceConfigRef]；启用后备份点的控制登记绑定 policySha256 与 epochId，必须由捕获前后 READY 且 epochId 相同来签发。缺旧点绑定时明确要求新 FULL。该侧绑定由后端分工实现，归档载荷格式保持。

## BDD
- Given 已初始化的 READY 周期和旧全量绑定；When 正式恢复即将首次改库；Then 先持久化 REPLACING，新周期与旧基线不同。
- Given 已开始恢复；When 数据恢复成功；Then 同一周期追加 READY，并绑定原恢复完成回执。
- Given 已开始恢复且后续失败；When 捕获异常；Then 同一周期追加 FAILED_RETAINED，自动增量不能把旧点当可用。
- Given 准入在任何数据写入前失败；When 退出；Then 不产生新的恢复周期。
- Given 错误锁描述符、来源/数据库变化、目录链接、记录缺段或摘要改变；When 读取或追加；Then 明确拒绝，不重建历史。

## 经验门禁与验证
固定来源、UUID、共享物理锁和不可变原件；编码为 UTF-8；本地真实临时文件与独立进程验证，不操作服务器、不执行数据库恢复。先 RED，再 GREEN；Linux 锁与权限验证不能用 Windows 跳过结果冒充实际通过，最终由根任务统一实测和记录。STANDARD 冻结包必须纳入新增模块和实际 replacement 入口，不能只验证源码。

## 实现与启用合同
- 新增 `ops/recovery/recovery_backup_epoch.py`，仅依赖标准库。`validate_policy`、`read_current`、`initialize(policy, lock_fd)`、`begin_restore(policy, operation_id, lock_fd)`、`complete_restore(policy, operation_id, epoch_id, state, evidence_pin, lock_fd)` 是正式入口。
- 读取验证所有不可变事件、相邻摘要、策略身份、状态转换、完成回执 pin；初始化也返回非空 eventPin。未初始化、缺段、篡改、未结束或证据缺失都不会推断为 READY。
- 写入仅在 Linux 且 `/proc/self/fdinfo` 证明调用者描述符持有同一物理源文件的排他 flock 后执行。使用 fsync 加排他硬链接发布，不覆盖既有事件；中断产生的未提交记录明确阻塞，不静默修复。
- 新目标可嵌入 `replacement.backupEpoch`；有旧历史的现有安装应使用 owner 顶层 `targetBackupEpochPolicies[targetRef]`，保证原 target 完全不变。两种来源均必须与 replacement 的 databaseUuid 和 lockPath 相同；目录不能与操作 stateRoot、任何注册服务可写卷或源锁发生危险重叠。
- `prepare` 在最终 quiescence 后、首次 DROP/CREATE 前持久化 REPLACING；execute 在原成功或失败回执落盘后追加终态。成功回执已经写出时，周期发布失败不能再覆写该原件。
- 控制配置 `sourceEpochPolicies[sourceRef]` 使用相同策略；后端分工负责 point-epochs 侧绑定。启用既有安装时，在没有活动捕获/恢复且持同一源锁期间显式初始化，然后登记两端配置。已有归档与旧点不重写、不追认 epoch；新 FULL 成功后才可自动选择新周期增量。
- 未配置策略的旧目标保持现有行为。运行中 `.59` 的冻结配置、请求与归档不修改。待根任务选定安装窗口后统一实施。

## BDD 与 TDD 证据
- BDD: 固定来源与恢复前后周期 -> Given 已初始化真实 journal；When 发生恢复开始与完成；Then epoch 改变、完成仍属于同一新 epoch，旧点失效。
- RED: `pytest scripts/tests/test_backup_epoch.py -q -p no:cacheprovider` -> 14 failed, 7 skipped。旧 replacement 拒绝新增正式字段，且恢复周期模块不存在。
- GREEN: 同上加 `scripts/tests/test_smallapp_replacement.py` -> 初次 25 passed, 7 skipped。Windows 未执行 Linux 特有项。
- BDD: 周期存储不得被自身恢复删除 -> Given epoch root 位于操作目录或注册 RW 卷；When 验证目标；Then 在变更服务之前拒绝。
- RED: `pytest scripts/tests/test_backup_epoch.py -q -p no:cacheprovider -k 'cannot_be_inside or cannot_be_erased'` -> 2 failed（原实现未拒绝重叠）。GREEN -> 对应两项通过。
- BDD: 丢失完成原件必须是明确周期错误 -> Given 已发布终态但完成回执被移走；When 读取；Then 报 BACKUP_EPOCH_EVIDENCE_UNAVAILABLE，不被公共层降成普通文件错误。
- RED: `pytest scripts/tests/test_backup_epoch.py -q -p no:cacheprovider -k missing_terminal` -> 1 failed（原实现抛 FileNotFoundError）。GREEN -> 对应测试通过。
- REGRESSION: `pytest scripts/tests/test_backup_epoch.py scripts/tests/test_smallapp_replacement.py -q -p no:cacheprovider` -> **28 passed, 11 skipped**。Python 为任务指定的独立运行时，PYTHONPATH 为任务私有 test-dependencies，未修改全局依赖。
- 11 个 Linux-only 场景包含实际持锁、争锁进程、软链接与权限、错误描述符、重复初始化，以及 replacement 控制器在写前失败/写后失败/成功三条路径。外部数据库和容器适配器仅是记录型单元测试替身；周期、文件、锁、回执为真实调用，不能作为真实数据库恢复或 E2E 证据。
- Linux 首轮实跑 `run_automatic_incremental_tests.py stream-epoch --attempt 1` -> epoch **25 passed, 3 failed**；三条控制器夹具缺少正式 `replacement.services[*].id`，在 prepare 写入原意图时失败，尚未到达目标边界。原日志与输入摘要保留在 `automatic-incremental-stream-epoch-1.log/.json`，SQL 扫描 106 项已通过；容器已清理、输入未变。仅补全夹具的 MySQL/MinIO id，不放宽产品服务登记校验。
- Linux 第二轮 `run_automatic_incremental_tests.py stream-epoch --attempt 2` -> SQL **106 passed**、epoch **28 passed**、replacement **11 passed**，无跳过，测试退出码 0，精确容器已清理。但整体 runner 返回 1：并行后端编辑改变了 `recovery_control_incremental_plan.py` 与 `recovery_control_smallapp_native.py`，全量输入不变门禁失败，不能将此轮登记为最终 GREEN。epoch/replacement 自身输入未变；等待并行模块稳定后重跑正式报告。
- GREEN: Linux 第三轮 `run_automatic_incremental_tests.py stream-epoch --attempt 3` -> SQL **106 passed**、epoch **28 passed**、replacement **11 passed**，无跳过，退出码 0、输入摘要未变、精确容器已清理。日志/报告 `automatic-incremental-stream-epoch-3.log/.json`。

## 终态元数据收口补充设计与 BDD
独立审查发现：实际 SUCCEEDED 回执已持久化但 READY 事件写入失败时，原实现永久停在 REPLACING。正式修复不重放恢复，也不根据进程消失猜成功。
- 开始事件的 evidencePin 固定原 replacement intent；intent 增加 schemaVersion=ReplacementBackupEpochIntent/v1、operationId、databaseUuid、targetConfigRef 和唯一 replacementReceiptPath。开始记录已写出后，调用者不能替换收据位置或身份。
- `reconcile_completed_restore(policy, lock_fd)` 仅在持同一真实源锁时按固定 intent 验证实际 terminal receipt，再追加 READY 或 FAILED_RETAINED。不存在或损坏的 receipt 明确阻塞；失败终态仍阻塞备份，不启动服务或解停写。
- `try_reconcile_current(policy)` 为日常计划提供正式收口：仅对 REPLACING 非阻塞争用原源锁；锁忙返回仍在恢复的快照，其他异常不吞；拿锁后只做上述控制元数据收口。read_current 保持只读。
- Given 已固定恢复 intent 且真实 SUCCEEDED receipt 存在；When 完成事件写入曾失败、下一次点击在源锁空闲时触发收口；Then 同一 epoch 追加 READY，原收据与 intent 不变，无数据库或服务动作。
- Given 已固定恢复 intent 且真实 FAILED_RETAINED receipt 存在；When 收口；Then 同一 epoch 追加 FAILED_RETAINED，保持备份阻塞。
- Given 原恢复仍持有源锁；When 计划尝试收口；Then 返回 REPLACING，不重复恢复。
- Given 缺收据、错误 operation/target/UUID、收据位置变化或 intent pin 改变；When 收口；Then 明确阻塞且不追加终态。
- 旧纯存储测试中没有 intent 的开始记录仍可读，但不能推断收据位置或自动收口；正式 replacement 入口始终写绑定 intent。

## 旧目标历史兼容设计与 BDD
正式服存在已消费且最终成功的旧失败记录，历史配置与现目标必须仍完全相等。安装不能把新策略直接塞进旧目标，更不能在历史比较时忽略字段。
- 正式 owner 配置增加可选顶层 `targetBackupEpochPolicies[targetRef]`。`replacement_value(configuration, target_ref)` 完整验证原目标，再验证独立策略的 UUID、锁及目录边界，返回仅运行时派生副本。原目标、原配置历史、clearance 摘要与比较不变。
- 新登记仍可使用嵌入的 `replacement.backupEpoch`；双重配置不同必须明确拒绝，不能选一方覆盖另一方。
- 安装准入必须成对核对 Native `sourceEpochPolicies[sourceRef]` 与 owner `targetBackupEpochPolicies[targetRef]` 使用完全相同策略；只启用源侧而漏配恢复侧不得判定安装完成，否则旧目标兼容路径不会更新 epoch。先持源锁初始化并登记恢复侧，再启用源侧自动计划。
- `recovery_minimal_plan.configuration_contract` 当前没有顶层字段白名单，新增正式字段不需要放松验证；实际入口在 replacement 层对映射与绑定严格验证。STANDARD 使用相同正式 replacement 模块，无须额外改变冻结配置格式。
- Given 真实已闭合旧 MAIN 历史与完全相同的原 target；When owner 单独登记 epoch 策略；Then 运行时启用 epoch，原 target 与历史文件字节保持不变，原 validate_clearance 严格通过。
- Given owner 策略指向错误目标/锁/UUID 或与嵌入策略冲突；When 解析；Then 在任何恢复/服务操作前拒绝，不修改原目标。
- RED: `pytest scripts/tests/test_backup_epoch.py -q -p no:cacheprovider -k owner_policy` -> **5 failed**（正式 owner 解析入口缺失）。GREEN：新增真实 closed_main 原目标/历史字节完全不变验证与四类错误绑定拒绝，全部通过。
- RED: `pytest scripts/tests/test_backup_epoch.py -q -p no:cacheprovider -k 'fixed_restore_intent or started_intent'` -> **4 failed**（原实现没有固定 intent 合同）。GREEN：固定 intent、receipt 唯一路径和目标 UUID/引用绑定验证通过。
- 更新后的 Windows REGRESSION -> **37 passed, 16 skipped**（`test_backup_epoch.py` 与原 `test_smallapp_replacement.py`）。16 项 Linux 测试包含 owner/embedded 双路径控制器、实际锁及自动 metadata reconcile；独立审查另有 7 条真实进程退出/存储异常 resilience 测试，需要根任务在最终代码上重跑。此前 attempt3 的 Linux 结果只对应当时输入，不能替代本次新增实现验证。
- 自动 reconcile 的持久证据（原 intent、最终 replacement receipt、journal）必须长期保留；不得由普通操作日志清理删掉仍被 epoch 链引用的文件。任何损坏、未知文件或不完整发布仍明确阻塞，不猜测或改写原始证明。
- BDD: Given 已调度破坏性写入且原恢复异常；When 失败回执落盘后，FAILED_RETAINED 事件追加也因存储异常失败；Then 二次异常仍携带原 native 上下文，原失败回执可在下次持锁收口成 FAILED_RETAINED，绝不解除停写。为 embedded 与 owner 两条控制器路径分别注入真实目录 open 故障验证。
- Linux RED: `run_automatic_incremental_tests.py stream-epoch --attempt 4` -> SQL **107 passed**，epoch **42 passed, 2 failed**，两条均准确失败在二次存储异常缺 `native`；输入摘要未变、容器已清。产品随后在任何失败元数据写入之前保留原 native，并将其附到二次证据异常，保留原异常链，等待最终 Linux GREEN。

## 待根任务完成
1. 在隔离 Linux 环境执行完整测试，记录真实 flock 与 replacement 控制器结果。
2. STANDARD 封包登记新模块，并验证冻结入口包含 replacement hook；由根任务维护 files.json / standard_fixes.py。
3. 后端控制登记与 planner 联调及后续按授权安装，保留实际安装配置 pin 和初始化证据。
