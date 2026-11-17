# 恢复应用启动阶段契约修复

## Goal
完成既定六步中的恢复和验收。修复SAFE封包在后端启动后仍要求零事务的阶段契约，避免正常应用事务误报数据库身份变化。保留失败原件，不回写成功或绕过恢复入口。

## Milestones
- [x] 核对原生FAILED_RETAINED及原始查询摘要。
- [x] BDD/RED复现实际SAFE封包在应用运行时错误拒绝。
- [x] 最小修复与GREEN/REGRESSION。
- [x] 固定提交、专用构建worktree及真实安装验证。
- [x] 经Spug准备空目标并恢复同一已选备份链，真实验收。

## Expected Verification
停写阶段有事务仍拒绝；应用启动后允许正常事务，UUID、只读模式、事件调度器与库范围不变仍核对；实际封包覆盖，不能只测精简源码。真实恢复成功后核数据、附件和登录。

## 经验门禁
Trigger：FORMAL_SQL_DATABASE_CHANGED发生在START_APPLICATION。Preflight check：原生终态、失败SQL摘要、实际封包与源提交、停止worker及唯一安装归属。Blocker：无法确认运行来源或原操作仍活跃，不安装。Verification：RED/GREEN/封包回归和真实恢复。Forbidden action：不修改历史失败、归档或NAS；不以当前零事务掩盖失败时的一事务；不手工放行前端伪装恢复成功。Evidence：原final/native-900.json输出SHA匹配UUID12e12207-e1f8-11f1-bd69-0242ac1dee20、read_only0、super_read_only0、innodb_trx1、event_scheduler OFF。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，按应用启动生命周期选择数据库状态约束，保留身份与范围核验。
- 是否存在临时补丁或绕过：否。

## BDD
Given恢复停写阶段，When目标存在活跃事务，Then仍拒绝。
Given数据库和文件恢复完成且后端已启动，When后端产生正常事务，Then继续启动前端并验收。
Given应用启动后，When数据库身份、权限模式、事件调度器或库范围改变，Then仍拒绝。

## Current Status
completed：54b0f54修复已融合维护仓并通过回归；本轮9ddf原生恢复SUCCEEDED/actualExitCode0/childExit0，应用启动2分29秒。8表、真实登录、用户管理与版本通过；两图片页面及SHA通过，PDF对象SHA通过但源数据既有缺字段导致页面不可见。用户已确认历史PDF按已有问题记录、不扩展迁移，开发worktree已删除。对应纯构建worktree已安全删除，任务隧道由六步父任务持有。
