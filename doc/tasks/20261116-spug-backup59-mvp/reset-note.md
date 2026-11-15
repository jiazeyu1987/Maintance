# 准备目标的失败恢复重置

## Current Status
ready_for_closeout。本地实现和必要测试完成，交父任务统一提交与部署；未进行远端写入、清锁、停服或恢复。

## 目标与里程碑
核对现有 active/result/child exit 与进程身份记录；定义只针对本工具当前 prepared 目标的终态重置；RED→GREEN→必要回归。运行中、退出未知或其它目标仍拒绝。

## 经验门禁
- 沿已有共享host lock和真实终态文件，不新增恢复重试或兼容框架。
- 只操作本工具last-target精确资源范围；源/NAS保留、原记录保留。
- UTF-8、私密记录只读取必要状态/路径/进程字段；不输出环境或凭据。
- 本子任务不清远端锁、不停服、不恢复、不部署。只读证据优先复用父任务已有本机文件。
- 前序bind适配已交父并提交，当前只改native文件、其测试和本记录，不改standard_fixes。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。失败目标预约由明确重置流程回收，运行目标仍互斥。
- 是否存在临时补丁或绕过：否。

## BDD
- Given本工具当前prepared目标的恢复已FAILED_RETAINED且原子进程真实退出，When用户确认新准备且持有同一host lock，Then记录旧预约并解除它，继续原清理范围。
- Given恢复运行、退出未知、其它目标或非本工具当前目标，When再次准备，Then拒绝且active记录不变。

## 已验证的真实合同
- 只读证据：`reset-terminal-fields.private.json`、`reset-contract-check.private.json`（位于本机私密运行目录，不提交）。当前恢复的 result/worker-result 均为 FAILED_RETAINED、actualExitCode=1；child-exit 为 W04_RESTORE_CHILD、actualExitCode=1、timedOut=false。
- `recovery_minimal.run_child` 在 `process.wait` 和 `process.poll` 后写 child-exit；无需猜测 PID、扫描历史或增加新进程证明体系。
- active.operationRoot 必须位于当前配置 stateRoot 内、本工具确定的 prepare hash/recovery-operations/operationId；prepare result 必须为 INITIALIZED；生成目标名、active/request、last-target 的唯一数据目录一致。
- 仅验证三份已有小记录 pin：worker-result、child-exit、resource-reservation；不遍历 originalResultPins 的大文件与所有历史。
- 新请求确认和预览匹配后，在同一共享锁内验证旧预约；依赖阶段成功后写本次 restore-reset.json，再解除该预约、进入原 cleanup。旧恢复记录保持原样。

## TDD 与验证
- RED: 三个定向 unittest → FAIL，现有 execute 对任何 active 一律 PREPARE_RESTORE_ACTIVE，正向重置无法进入依赖阶段。
- GREEN: 三个定向 unittest → PASS。覆盖当前失败且退出目标可重置；运行、未知退出、其它目标、非当前目标拒绝；未确认和依赖失败不解除预约。
- REGRESSION: `python -X utf8 -m unittest ops.spug.test_prepare_target_native` → 28 tests PASS。
- 当前实际记录只读合同核对：preparedHashMatches、exitAndWorkerAndReservationReferenced、activePinMatches 均 true，serverWrites=false。
- 本轮只改 prepare_target_native.py、test_prepare_target_native.py 与本记录；父任务同步总 execution-log/request-command-log 并统一提交。
