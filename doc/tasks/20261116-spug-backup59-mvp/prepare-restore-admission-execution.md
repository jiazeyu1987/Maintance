# 新空目标恢复准入

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
v8 的真实准备任务 prepare-261bf06f-3c35-404d-8c86-c6a42dbdf701 已 READY，新目标 spug-empty59-9ad0f898afb1。父任务从页面提交全量恢复却被旧恢复历史 ORIGINAL_OPERATION_STILL_UNRESOLVED 拒绝。先精确取实际命中证据，再只对本功能明确 READY 且未消费新目标跳过无关旧目标历史准入；同目标未决、选择身份及实际互斥保持。里程碑：只读证据、BDD/RED、最小实现、定向回归及提交。

## 经验门禁
- 前一 v8 准备已实际验收 READY；本轮属于同一闭环任务，远端恢复及最终收口由父任务负责。
- 不删除/改写旧历史，不解除实际工作锁，不将旧失败改成功；本地登记证据必须精确属于新目标与对应来源。
- 仅本地产品改动与必要只读诊断；不自行提交恢复、重启或部署。UTF-8 显式读写，凭据不输出/提交。
- 按 BDD/RED/GREEN/REGRESSION 记录；共享命令日志由父任务统一收口。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；限定新的独立目标与无关目标旧历史，真实任务互斥不变。
- 是否从根因和长期维护角度解决：是；新空目标的恢复准入不能依赖不相关旧目标仍可访问。
- 是否存在临时补丁或绕过：否；使用本功能真实 READY 登记证据，保留同目标未决与恢复准入。

## BDD 与执行证据
- BDD: 独立新目标 -> Given 本功能新目标真实 READY 且未消费，来源有其他目标无法查询的旧恢复历史，When 首次恢复该新目标，Then 无关旧目标历史不阻挡，同目标未决仍拒绝。
- 只读证据：实际 source 为 intruoyi-57-safe-20261024-v1；按 entry 枚举前 14 条有 terminal 或终态记录，第一条无终态候选为 smallapp-1fd7a5899db54511bee4daec85e271f8，目标 intruoyi-main-58-safe-restore-20261104-v1，Spug history 392，创建 2026-11-15T11:30:55Z；journal RUNNING，terminal 文件不存在。未请求旧远端。
- 父任务确认本次被拒绝的 smallapp-8a878479abcd41649cad37c20ce4b679 没有 UI entry 或 adapter journal，尚未实际恢复。
- RED: 用例首次夹具将配置 JSON 放入任务记录根导致 startedAt 缺失，修正夹具后重跑；有效 RED 为独立新目标准入被 ORIGINAL_OPERATION_STILL_UNRESOLVED 拒绝，其他同目标/未READY/来源备份场景仍正确拒绝。
- GREEN / REGRESSION: `python -X utf8 -m unittest test_prepare_target test_prepare_target_http test_prepare_target_registration test_smallapp_safety test_smallapp_cross_route test_smallapp_display_context test_automatic_incremental_entry -q` -> PASS 68/68；`git diff --check` -> PASS。
- 补充尝试 `python -m pytest test_takeover_selection.py -q` 未进入测试：当前 runtime 未安装 pytest，不计为 PASS，不安装新组件。父审确认必要范围为上述 68 项，不继续扩大。
- 父审通过最小范围：最新 READY、精确来源/应用/目标、三阶段成功且该目标没有预约时，只跳过其他目标 RESTORE 历史。FULL/INCREMENTAL、同目标未决、原实际锁与最终 admit_selection 保持。

## 工作区与交付
- 工作区 `C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`，基线 `f3eb4b5271b56a4d119e22066070f7f5ca8d5cf5`。
- 产品仅 prepare_target.py、smallapp_entry.py，另一个定向测试文件；发布 v9 只更新本机入口文件，不操作远端目标。提交后由 prepare59_install 准备固定 release-v9，父任务执行真实页面恢复验收与最终融合收口。
