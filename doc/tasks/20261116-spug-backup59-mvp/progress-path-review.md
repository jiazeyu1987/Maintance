# 新目标步骤回执只读定位

## Current Status
completed

## 目标、里程碑与预期验证
父任务确认 v11 全量恢复已到 database-000/sql-stage 且 worker 存活，但 Spug 进度页显示尚无步骤时间回执。本轮只读核对新 prepare operationsRoot、已发布 telemetry 与现有步骤回执查找合同，报告最小代码修法；不改引擎、不部署、不触碰当前恢复。

## 经验门禁
- 前一应用输入修复已提交交父任务；本次继续同一任务链，只读定位进度显示，不重复执行恢复或校验数据。
- 以实际准备结果、登记进度根和现有回执格式为依据，不新增探测协议或重复全链检查。
- 只读本地既有证据与源码，秘密不输出；若需远端由父任务安排。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否，本轮不修改产品。
- 是否从根因和长期维护角度解决：是，依据现有路径合同及真实页面回执确认是否存在缺陷，不为未证实问题增加机制。
- 是否存在临时补丁或绕过：否。

## 场景
Given 新目标恢复已经写入真实步骤回执，When 通过现有进度入口查看，Then 应显示实际运行/失败步骤，不因为查错根目录而展示空回执。

## 只读结论与验证
- 新目标登记将 `progressRoot` 写入该目标专用 `restoreProgressBindings`；`smallapp_simple.progress_binding` 按恢复请求的精确 `targetConfigRef` 选取此路径，远端投影读取其 `recovery-operations/<operationId>` 及一层子目录的既有 timing 回执。未发现指向旧目标根目录的源码合同问题。
- 父任务从真实页面再次查询后成功显示步骤；本地只读核对 `progress-responses-latest.private.json`，响应 HTTP 200、操作 `smallapp-bc9aafdc3b284a9582f6dd09f6bc9816`、状态 RUNNING，共 6 个步骤。准入 1.47 秒，目标检查 1.02 秒，SQL 暂存 105.354 秒，SQL 展开 231.444 秒，SQL 导入运行中。
- GREEN: 现有真实页面进度接口与步骤投影 -> PASS。证据位于私密目录 `C:/Spug/runtime/private/spug-backup59-mvp-20261116/` 的 `progress-responses-latest.private.json` 与 `restore-query-latest.private.json`，原始证据不提交。
- 初次空回执的具体瞬时原因尚未证实；当前证据已证明新路径与显示链实际可用，不据此声称已修复缺陷。
- 本轮没有产品、配置、服务或服务器写入，也没有启动新的恢复或数据检查。按父任务指示结束排查，不新增显示机制。只读审查无需行为变更测试，无新的部署或 worktree 收尾事项。
