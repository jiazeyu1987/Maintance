# 磁盘准入策略重构与 TDD

## Current Status

ready_for_closeout。四个运行模块已冻结，父任务已审查接受；本机实现和必要资源/配置回归已通过，交父任务独立提交和构建。用户已明确不扩容、不再因固定 178 GiB 预留阻断；本子任务未执行任何服务器操作或业务数据恢复。完整候选保全补充测试因既有 180 秒 fixture 到时而 FAIL，正式已提交包的 sealed producer 由父任务另行验收，不把 FAIL、pending 或 deselected 记成 PASS。

## 目标、里程碑及预期验证

1. 核实四个资源准入模块所有配置最大量相加的磁盘检查。
2. 向父任务报告正式版本化策略设计，再写 BDD 失败测试。
3. 最小实现显式模式，回归旧严格行为及内存、路径、实际写入错误行为。
4. 本机和隔离 Linux 验证；父任务审查后集成，不自行提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。模式由配置显式选定，未知配置直接拒绝。
- 是否从根因和长期维护角度解决：是。所有运行阶段共享同一磁盘准入合同，旧版本保持精确严格含义。
- 是否存在临时补丁或绕过：否。不伪造可用空间、不改变实际写入/包大小上限、不吞写入错误。

## 经验门禁

- Trigger：原 MAIN 资源预算调整；Preflight check：真实资源观察逻辑和容器/路径身份检查保持；Blocker：模式未贯通任一阶段、旧严格行为变化、异常被隐藏；Verification：BDD、RED -> GREEN -> REGRESSION，有限单元测试与真实隔离 Linux 载体；Forbidden action：服务器访问、改原回执、降内存/完整性门槛、降低实际写入上限或伪造成功；Evidence：本文件及父任务 execution-log.md。
- Trigger：Windows 跨层测试命令；Preflight check：明确 UTF-8 与原生退出码；Blocker：编码或退出码不可信；Verification：固定解释器、原始日志私密保存；Forbidden action：含凭据日志提交、默认编码与 shell 插值；Evidence：本文件仅脱敏摘要。

## BDD

- Given 显式 OBSERVE_ONLY 且空闲空间小于配置最大量之和；When 恢复、程序投影和覆盖前保全准入；Then 记录实际空闲及预计量且不因预计量拒绝，仍核内存及有效观测。
- Given 原 v1 或显式 RESERVE；When 空闲不足；Then 原严格空间错误保持。
- Given OBSERVE_ONLY 且写入发生 ENOSPC；When 真实写入异常到达业务层；Then 异常原样进入既有失败路径，禁止成功回执。
- Given 未知、缺失或歧义的 v2 模式；When 加载预算；Then 明确拒绝，不回退。
- Given 原物理目标及程序基线保持 v1；When owner 顶层 `targetResourceAdmissionPolicies[targetConfigRef]` 显式选择 v2；Then 四个运行模块读取同一策略，物理目标与基线字节不变。
- Given 顶层策略存在但缺少当前目标、含未知目标或改变原内存/磁盘预算；When 选择运行预算；Then 明确拒绝，不以原目标预算继续。

## 配置归属设计（实施前补充）

运行准入模式独立于不可变物理目标：增加纯 helper `configured_budget(configuration, request)`。无顶层策略字段时只接受原 `target.resourceBudget` v1；字段存在时要求当前目标已配置、键均为已知目标，每份 v2 完整预算除 schemaVersion 和 diskAdmissionMode 外须逐值等于对应原 v1 预算。返回独立副本，不修改目标、程序 baselineTargetPin 或原证据。`admit`、程序投影、目标捕获和归档保全均从完整 owner 选策略；纯 `check_budget(v2)` 与 `enforce_disk_capacity` 合同不变。配置策略错误使用 `RESTORE_RESOURCE_ADMISSION_POLICY_INVALID`，原预算错误保持 `RESTORE_RESOURCE_BUDGET_INVALID`。此项按新增 BDD 先 RED 后最小实现，不是失败后的自动切换。

## TDD 证据

- 设计：父任务已确认 v1 精确严格合同，v2 增必填 `diskAdmissionMode=RESERVE|OBSERVE_ONLY`；共享 `disk_admission_mode(policy)` 与 `enforce_disk_capacity(policy, required_bytes, available_bytes, failure_code, *, minimum_free_bytes=0, details=None)`。OBSERVE_ONLY 仅不预留预计最大量；2 GiB 最低余量、真实 NAS 待写 total+余量、实际写入上限及 OS 错误保留。
- 环境前置失败：默认本机 Python 无 pytest（`No module named pytest`），未执行测试，不计为业务 RED；改用已有固定 wheel 与固定 Python 3.12 Linux 镜像的隔离载体，不访问网络。
- RED：`run-disk-admission-policy-linux.py red-r1` -> native 1，15 failed / 9 passed / 0 errors / 0 skipped；失败为预期 v2 合同、共享 helper 及发布准入入口缺失。真实 1 MiB tmpfs 写入 ENOSPC 用例已通过。源快照 373 件、SHA `58698a90a161e62bbe453a2efcdbb108a51698212268c7d49d34ba42c1063090`，输入保持，容器移除。
- GREEN：同载体 `green-r1` -> native 0，24 passed / 0 failed / 0 errors / 0 skipped，1.61 秒 pytest / 25.235 秒完整载体；源快照 SHA `0aae8d0b9fa4ba24c087b92f93f5c673ec6b918bf97e3b83f7339db4972c4c57`，输入保持，stderr 0，容器移除。
- 实现：四个运行模块统一策略；原 capture/preservation 的容量异常类型保持，原 v1 证据字段和返回不变。v2 记录是否预留预计量、实际空闲、最低余量；真实归档发布额外记录 actualArchiveBytes 及不可跳过的真实写入需求。
- 首轮纯资源 REGRESSION：`pure-regression-r1` -> 161 passed / 0 failed / 0 errors / 0 skipped，native 0；源 SHA `80504f74c84a239e0ea34034b3b7fb4a2fb84e14d8d3ffeef721271cf8975d54`。含原严格资源、预约、捕获配置/材料及当时的新 24 项。
- 配置解耦 RED：`selection-red-r2` -> 20 failed / 21 passed / 0 errors / 0 skipped，native 1；预期失败为 helper 缺失、owner admission/capture/preservation 尚读原严格物理预算、真实 MAIN 程序上下文未记录顶层策略。此前 `selection-red-r1` 的程序输入在 owner 写后增字段，导致 `PROGRAM_EXECUTION_OWNER_CHANGED`；已只修正新测试在首次 owner 写入前配置策略，r2 的程序 RED 为预期 `forecastReservationsEnforced` 未记录。
- 配置解耦 GREEN：`selection-green-r1` -> 41 passed / 0 failed / 0 errors / 0 skipped，native 0；0.67 秒 pytest / 12.156 秒载体，源 SHA `cbe9061a8be5ef33826c1298a9a840ee286adef6e80ef07a81cce1250f6191a2`。含未知/缺失覆盖、内存或磁盘预算变更拒绝、真实 owner 证据与 MAIN 程序预约/上下文、捕获/保全两个阶段和实际 ENOSPC。
- 最终资源 REGRESSION：`selection-regression-r1` -> 178 passed / 0 failed / 0 errors / 0 skipped，native 0；9.85 秒 pytest / 17.141 秒载体，633 件输入，源 SHA `ca652702413068d8e29641653571828129f66d0fa185bc5454e3930d22e0f6f7`。新策略 41 项加原严格资源/预约/程序资源/捕获配置/捕获合同 137 项全部通过。完整候选保全节点明确 deselected 1 项，另以专用 full payload 载体验证，不混计此组通过数。
- 父任务指定的配置/安装接线 REGRESSION：`bindings-r2` 对 `test_main_target_disk_policy_binding.py`、`test_main_program_target_control_candidate.py`、`test_main_program_target_control_staging.py` -> 105 passed / 0 failed / 0 errors / 0 skipped，native 0；3.08 秒 pytest / 15.109 秒载体，源 SHA `fffe7b23edc75637bd63d6f4dbe8baaa66509aa8c2204affeb1cd7b6fa3664c9`。该快照已包含父任务最终顶层策略实现，原始 bindings-r1 的 105 PASS 证据另留存。
- 各 PASS 载体均固定镜像 `sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735` 与已核对 12 个 wheel；network=none、只读根、cap-drop ALL、独立 tmpfs、明确 1 MiB ENOSPC 文件系统；输入字节保持、stderr 0、任务容器移除，actualBusinessRestore=false、remoteActions=0。原始 manifest、stdout、stderr 和 result 均按 revision 独立保存在本机私密载体目录，不覆盖旧结果。

## 原失败保留与独立基线复现

- `regression-r1` 原结果保留：176 PASS / 5 FAIL / 12 ERROR。载体最初未携带 frozen baseline tgz，导致 12 个保全 setup ERROR；子进程缺 wheel PYTHONPATH 导致预约测试一例失败；其余为源 LIGHT 语义与旧 MAIN 捕获 fixture 不匹配。未将这些结果记为成功。
- 补齐载体输入后的 `regression-r2`：75 PASS / 1 FAIL，仍为子进程依赖路径；修正仅载体 PYTHONPATH 的 `regression-r3`：161 PASS / 1 FAIL，首个原正例 `test_main_actual_full_materials_hold_without_releasing_original_protections` 在真实 SAFE 语义读取有限 S3 fixture 时报 `S3Protocol.absent_configuration` 缺失。
- 按父任务要求，`baseline-capture-r1` 在同一冻结载体、相同首个失败节点下，将本任务四源码换为原 HEAD `346b47069a172966c0cd462fd546420e96ffa2c1` 的精确 Git blob：0 PASS / 1 FAIL，复现相同 `S3Protocol.absent_configuration` AttributeError，native 1。输入 632 件，源 SHA `fca1ecc3470399a38ce4171f391af7c18a67fc366cf58b9ffa8fa9069fe20cc8`；四个原 blob 的字节数和 SHA 已写入私密 sourceOverrides，工作区未被替换。此证据证明该首个失败独立于本次四源码修改；不外推其它失败也已证明无关。
- `safe-regression-r1`：5 PASS / 1 FAIL，原 source reader 用例与实际候选 reader 合同不同（`verify_environment` 不存在）；缩为只加载 SAFE 语义的 `safe-regression-r2`：15 PASS / 1 FAIL，旧保全正例在 source capture guard 与实际 SAFE 语义混合路径发生 `FORMAL_DATA_DEADLINE`。未改原 fixture、未提高限时、未修改业务完整性门槛；父任务已同意拆纯资源与实际封包验证，停止追修旧混合组。
- 上述旧组失败、ERROR 与原始日志完整保留。它们不属于最终 178 项纯资源 PASS 或 105 项配置接线 PASS；本记录不声称原整组全部通过。

## 完整候选保全补充验证（明确失败）

`v2-full-r1` 只选择新增 `test_full_v2_preservation_archives_and_reads_back_under_original_custody`；完整真实 `safe_fixes` payload 经现有 `candidate_imports` 全清单路由认证，模块均从候选正式合同路径加载，未修改旧 fixture 或提高任何限时。结果为 0 PASS / 1 FAIL / 0 ERROR / 0 SKIP，native 1；184.22 秒 pytest / 200.031 秒载体。捕获 52.867 秒、真实归档 stream 37.120 秒、完整 SMB 回读 58.816 秒后，在原 publication fixture 的 180 秒总期限触发 `PRESERVATION_DEADLINE`，没有生成成功保全结论。源 SHA `fffe7b23edc75637bd63d6f4dbe8baaa66509aa8c2204affeb1cd7b6fa3664c9`；全部输入保持、stderr 0、容器移除。

此结果已即刻报告父任务，不作为 PASS，也不推断父任务将使用的正式已提交包 sealed producer 会成功或失败。已停止此补充路径，不再追修或扩大旧组；父任务既定 producer fixture 自带明确完整流程预算与原断言，最终完整保全和恢复证明仍须由该真实封包验证给出。四个运行模块继续保持冻结。

## 接口与交付边界

- `configured_budget(configuration, request)`：从完整 owner 选择与原 v1 相同资源量的独立 v2 准入策略；旧 owner 返回原 v1 的独立副本。未知覆盖/缺项/改变资源量明确失败，原物理 target 和 baseline 不变。
- `enforce_disk_capacity(policy, required_bytes, available_bytes, failure_code, *, minimum_free_bytes=0, details=None)`：纯合同返回 `diskAdmissionMode`、`forecastReservationsEnforced`、`requiredBytes`、`minimumFreeBytes`、`availableBytes`。RESERVE 按 requiredBytes；OBSERVE_ONLY 按 minimumFreeBytes。实际发布空间仍强制 actualArchiveBytes+既有余量，内存、路径与真实写入上限均保留。
- 四源码已交父任务冻结审查；本子任务未修改配置生成器、安装器、standard_fixes 或已有包，未提交 Git。新完整候选测试只使用新文件的 fixture 封装，不改旧测试 fixture；正式提交、正式包重建与 sealed producer 由父任务执行。
