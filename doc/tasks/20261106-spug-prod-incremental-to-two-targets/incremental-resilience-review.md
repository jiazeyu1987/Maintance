# 自动增量独立韧性审查

## Current Status
in_progress — 只读产品审查完成；两个本地 HTTP/文件复现已 RED，桥接预算接线已独立 GREEN，历史扫描优化与七个 epoch 用例尚待整体验证。正式修复由控制后端与 epoch 子任务负责，本审查没有修改产品代码。

## 目标与设计约束检查
- 核对 UI → entry → HttpBridge → Native/Ledger/planner 以及 replacement → source epoch 的实际调用链。
- 是否引入 fallback/降级/吞异常：否；发现问题必须显式记录，不通过跳过原始终态证明、伪造成功或重复恢复规避。
- 是否从根因和长期维护角度解决：是；关注可界定的计划预算、已终态证据读取范围、成功收据与终态日志之间的持久化窗口。
- 是否存在临时补丁或绕过：否；审查只新增独立复现测试，不改产品共享文件。

## 经验门禁
- 本地文件/HTTP 单元场景不能称为真实 MySQL 观察、服务器恢复或 E2E。
- Linux flock 必须在真实 Linux 执行，Windows skip 不能作为成功证据。
- 终态恢复只能在持有同一物理锁后，按不可变原件可信追加终态，不能自动重复执行数据恢复。
- 性能结论按真实读取路径和字节计数，不能把 JSON 中引用的 payload 错说为已重读 SQL/tar。

## 发现 1：同步预览重复读取所有历史原件，外层期限没有涵盖内层预算
触发条件：同来源存在多代完整成功备份，即使只选择最新 FULL，计划仍先扫描历史 Ledger 的每个状态，随后展开所有 points。

审查时调用链：`recovery_control_incremental_plan.build_plan` → 新 Ledger 的 `require_source_idle` → 每条 `status` → `Native.reconcile` → `owner_result/operation_output` → `executor.verify(originalResultPins)`；随后 planner `read_point` → `Native.point` 再次验证同一 originalResultPins。

已终态分支验证 owner stdout/stderr、owner result、originalResultPins（实际备份包含 readback-original 元数据）。普通已终态分支不递归重读 SQL/tar payload；只有 RUNNING 的 refresh_original 成功处理还递归检查 output.data 的 pin。`executor.pinned_read` 每次完整读取并计算摘要，没有本次请求内复用。

本地真实 HTTP 复现：24 个完整 FULL 代际，每个关联 1 MiB readback 元数据，计划选中最后一代。结果为 829 次 pinned_read、50,788,703 bytes，其中 readback 48 次、50,335,584 bytes；SQL payload 读取 0 次。请求实际耗时 0.92–1.00 秒，其中 pin 读取约 0.55–0.61 秒。fixture 构造/清理另占时间，不能计入 HTTP 性能。

`HttpBridge.call` 固定 `timeout=10`；生产 `incremental_source_observation` 允许 `min(querySeconds, 10)`，位于上述历史读取之后。即使单次 live probe 在自身支持期限内完成，整个请求也可能超出桥接期限；大历史量会进一步放大。需要正式限定同步验证范围及完整调用链预算，不能只用前端延长等待掩盖无界扫描。

BDD：Given 多代已成功终态且最新一代可用；When 请求增量计划；Then 历史代际不得逐次重哈希所有 readback，且外层预算必须覆盖计划及 live probe。

RED：`python -B -X utf8 -m pytest scripts/tests/test_automatic_incremental_resilience.py -q -s -p no:cacheprovider` → 2 failed。`readbackReads=48 > 2`；`bridgeTimeout=10 <= 10 + measuredMetadataSeconds`。没有人为 sleep 模拟超时，且未声称本次 24 代请求实际超时。

预算接线 GREEN：改用公开 `HttpBridge.incremental_plan` 路径后，`python -B -X utf8 -m pytest scripts/tests/test_automatic_incremental_resilience.py -q -s -k http_budget -p no:cacheprovider` → 1 passed。主任务接线后的实测 bridgeTimeout=40、计划1.062秒；当时历史读取仍为829次/48次readback，属于另一待修项。fixture还补充真实 Python no-op 子进程、native-intent/native-process/exit/selection 的闭合原件，证明进程退出协议，不声称它执行了备份。

## 发现 2：恢复终态收据已落盘，epoch 未追加终态时无法日常自助继续
触发条件：`recovery_replace.execute` 写入 `replacement-result.json` 的 SUCCEEDED 收据后，在 `complete_restore` 发布 READY 事件之前遇到存储错误或进程退出。

审查时成功收据会保留，但 epoch 仍为 REPLACING。下次 replacement 入口只允许 READY/FAILED_RETAINED，`Native.source_epoch` 只允许 READY；因此原始恢复已有成功收据时，后续恢复与所有备份仍永久受阻。旧逻辑没有可信地从已落盘收据追加终态的产品路径。

BDD：Given 原始操作固定 intent 与成功收据已落盘、epoch 仍 REPLACING；When 重启后重新获得同一物理锁并核对原件；Then 仅追加对应终态，不重放恢复，不改 epoch ID/原收据，重复核对幂等。失败收据只能完成到 FAILED_RETAINED；缺失或身份不符的收据不得推进。

独立测试已写入 `test_automatic_incremental_resilience.py`：SUCCEEDED/FAILED_RETAINED × 终态目录 open 的真实 OSError/子进程真实 os._exit(73)，以及缺收据、错 target、错 database UUID，共七项。只在存储边界注入中断，使用真实 journal、收据和 Linux flock；不连接数据库。Windows 当前为 7 skipped，尚无有效 RED/GREEN，必须由主任务 Linux runner 验证。

修复接口已与 epoch 子任务约定：`begin_restore(..., intent_pin=...)`、`reconcile_completed_restore(policy, lock_fd)`，由该子任务实现正式接线。
