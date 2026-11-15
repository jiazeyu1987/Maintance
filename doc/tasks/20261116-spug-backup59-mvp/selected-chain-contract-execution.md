# 已提交轻量恢复计划合同核对

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
父任务确认远端恢复准入反复扫描约 70GB 载荷，并在 14339 个归档路径租约处以 ARCHIVE_LEASE_FD_BUDGET_EXCEEDED 自然失败，mutationDispatched=false。通过既有 standard_fixes.py 正式构建入口，只复用已提交 selected_chain 函数、移除 runtime 准入/结束重复载荷哈希和全载荷 FD 租约；保留元数据、执行器、目标身份、真实互斥及实际导入/复制/启动流程。里程碑为实际安装与正式构建同源核对、最小 RED/GREEN 回归、交父任务审查及后续部署。恢复正确性由父任务真实 UI、附件样本与数据库验收证明；本子任务不部署、不执行恢复。

## 经验门禁
- 原全量恢复已自然失败并释放锁，本子任务仍不替换远端加载文件；安装由父任务安排。
- 用户明确要求最小实现与去重，取消恢复前后额外全载荷扫描及全路径租约，不提高 FD 预算、不用递归 stat 替代哈希；实际数据处理错误及现有恢复结果检查保持。
- 固定本任务 integration-worktree，UTF-8 显式读取，私密服务器资料不提交；只记录必要合同证据。
- 前一 counts helper 已提交交父任务，真实验收仍由父任务负责；本次只修改正式构建中计划/runtime 的指定边界，不整套切换轻量引擎。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；不改变错误语义或增加旁路。
- 是否从根因和长期维护角度解决：是；安装输入必须使用已提交的正式轻量准入实现，避免反复附件全量读取。
- 是否存在临时补丁或绕过：否；以正式提交和实际依赖合同为依据，若不相容则明确报告。

## 验证场景
- BDD: Given 已登记 FULL→I1→I2 的元数据链，When 调用正式包 selected_chain，Then 保持顺序及原 tuple 合同，不调用 archived_tree、object_index_chain 或 physical_chain_inputs。
- BDD: Given 成千上万载荷与少量元数据，When 正式包初始化恢复，Then 只租约/哈希元数据、执行器与输入，FD 数量不随载荷数量增长；缺失实际执行器仍报错。
- BDD: Given 恢复已执行真实数据库、附件、启动步骤，When 到达 archive-verification，Then 检查现有有限元数据 guard，不再重新逐个打开载荷。

## 已确认依据
- standard_sources()+standard_fixes.apply 的两模块 SHA 与实际安装精确相同：plan 4ad57e24c506401672c6e910584fd8e3ced767f38739f7ea5fff597f409b2951，runtime 381dc955d276b4cf63d2d49d7d00a847d1c8732ab562e5036428ed642b0e74d0。
- 此为已有正式构建变换入口，不新增临时私密补丁；只改两模块，其他 SAFE 读取、MAIN 支持与共享互斥保留。

## 执行与验证
- 测试环境：已有 Docker `python:3.12-bookworm`，只读挂载本任务工作树和既有 `C:/Spug/runtime/private/full-to-prod-20261105/local-test-deps`；`--network none --rm`，未安装组件，未触碰业务容器或远端。
- RED: 首轮 3 failed / 1 passed；物理复制 fixture 的 Python pin 碰到镜像 `/usr/local/bin/python` 符号链接，属测试载体问题，不能冒充业务 RED。修正为真实 executable 后，以既有正式构建跳过本次新增 transform 重跑同一 4 项，3 failed / 1 passed，精确为 ARCHIVE_LEASE_FD_BUDGET_EXCEEDED、duplicate archive scan、duplicate final payload scan。
- GREEN: `python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_backup_variants.py -k 'safe_registered_main_archive_inputs or standard_selected_chain_avoids or standard_final_archive_step or standard_keeps_original_code_except_reviewed_fixes_and_archive_names'` → 5 passed, 31 deselected（6.98s）。
- 真实 Linux guard 在 RLIMIT_NOFILE=1024 下处理 15000 个未打开载荷引用，实际元数据/工具有租约，修改元数据触发 ARCHIVED_PAYLOAD_CHANGED；缺少实际 iptables 仍失败。
- 真实 standard 包 FULL→I1 物理文件复制得到 new.bin 的准确字节并删除 old.bin。只在准入被禁止的重复扫描边界使用失败探针，复制与文件检查均为真实执行。
- REGRESSION: 已有标准包生成/内容清单契约通过；native 25 项通过，详见同目录 program-entry-execution.md。未扩展全仓回归。
- 审查：父任务已确认 standard_fixes 34 行及 native 16 行产品差异范围；生成 runtime 相对实际安装仅两个区块变化，configuration/target/MAIN 和数据读写方法均未改变。MinimalData.guard 已覆盖 NativeData.guard，生成 runtime 除初始化外没有 payload_signatures 读取，不产生载荷缺项 KeyError。
- 构建输入：本次只跑本地测试生成包，不是部署包；正式安装必须在本次提交后的独立 release worktree 构建。父任务负责安装、真实恢复及融合收口。此记录不代表 .59 恢复成功。

## 父任务追加的已知冲突收敛
- 第一段实现已提交 0b1a037，记录 e97c388；父任务批准在下一次真实恢复前继续消除已证实的执行合同冲突。
- Given 新目标明确登记三项 dataRoot 下的数据 bind，When 标准运行时检查并恢复，Then 允许这些精确数据目录，拒绝未声明、越界或源/NAS 重叠，保留真实目标身份与共享检查；不改回 Docker volume。
- Given PHYSICAL_FILES 链，When 复制文件，Then 每份实际载荷只为复制读取，保留相对路径、源目标分离、空目标与实际 I/O 失败；不再复制前后哈希、重新导出全部 S3 内容或内容读回。结果明确 payloadContentVerified=false，不冒充核验通过。
- 最终正确性由父任务通过真实 UI、11 表计数、3 个附件样本及登录验证，非本地测试成功即宣称恢复成功。
- 追加 RED: 两个物理测试失败，分别为正式包缺 verify_content 参数、实际物理路径仍执行全量 S3 导出/比较。GREEN: 2 passed（5.98s）。实际 FULL→I1 调用 verify_content=False；check_pin/pin 探针遇调用即失败，真实 Path.open 记录每个载荷仅一次读取；最终真实字节和删除正确，非空目标与缺失源仍失败。
- 最终 REGRESSION: 同一隔离 Linux 命令运行 test_backup_target_mounts.py 和 test_backup_variants.py 的上述受影响筛选集合 → 11 passed, 31 deselected（10.40s）。包含正式构建接入、有限元数据 guard、实际文件复制、bind/标记合同及明确未核验字段。native 25 tests、显式 target 验收 helper 2 tests 另均 PASS。
- 实际 standard configuration_contract 允许附加 target 字段，target_configuration 使用必需键子集检查，不拒绝 preparedEmptyTarget。标记由 native 生成，非浏览器请求输入；下一轮需重新准备生成新 owner，不能仅替换引擎后使用旧 target。
- 最终生成安装模块精确为 common/recovery_minimal_plan.py、common/recovery_minimal_runtime.py、common/recovery_data_files.py、common/recovery_data.py，另 native 源文件 ops/spug/prepare_target_native.py；安装方同步 package.json 的这四项摘要及 packageSha256，不动旧引擎目录。
- 真实恢复与最终融合仍交父任务，未新增远端读取、清理或恢复执行。git diff --check PASS。
