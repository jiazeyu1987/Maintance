# 下一次发布：菜单漂移修复

## 状态与授权

pending_next_release。用户2026-11-20明确要求“更新IntRuoyi的代码，然后在下次发布的时候帮我修复菜单问题”。菜单修复已纳入下次发布范围，无需重复询问同一范围授权；本记录不触发立即发布或服务器写入。

代码已更新至合并提交46c87dd2c29de07734d467df9ead10eed7b1c77b，包含远端9783f8fc2和原本地发布修复。此次远端更新未新增针对5580漂移的修复迁移。**菜单尚未修复，不得把Git更新或旧迁移SKIPPED当作修复成功。**

## 执行门禁

- Trigger：下次IntRuoyi测试服/正式服构建发布，或菜单账本成功但现值漂移。
- Preflight check：按实际配置与目标已提交版本重新只读核两服system_menu、相关角色/套餐及迁移账本。先DESCRIBE；固定受管菜单目标与完整差异表。确认新前向修复迁移、目标预检、验证规则实际入包。历史证据见[菜单分析](../doc/tasks/20261120-menu-alignment-analysis/findings.md)。
- Blocker：只有旧迁移记录而无可执行修复；父菜单/权限身份冲突；无法确定目标结构；需要越权扩大全角色/全租户权限；缺恢复依据；测试后菜单仍漂移。必须在停正式服前暴露问题。
- Verification：同releaseTag先测试再正式。无论相关历史迁移APPLY或SKIP，分别检查目标版本最终菜单结构、父子关系、路径、组件和权限；真实登录验证目标角色可见菜单及页面入口；核再启动/重复发布不会回退。正常发布运行态验收同样必须通过。保存修复前后差异、迁移执行证据及页面结果。
- Forbidden action：不删除账本、不改已执行SQL/摘要、不全量重跑历史SQL、不复制整张本机菜单/角色表、不直接按prod环境标记断言测试服迁移执行史、不把静态入包检查冒充真实菜单验收。
- Evidence：本次更新任务doc/tasks/20261120-update-intruoyi-menu-next-release；实际执行时补releaseTag、应用修复提交、迁移ID/SHA、测试/正式验收与恢复依据。当前没有这些执行证据，不得提前关闭本待办。

## 阶段必查与实施顺序

1. 构建前：基于最新目标提交核IntRuoyi是否已交付正式修复；没有则先完成新增前向迁移及必要验证，再构建，不在服务器临时手改凑通过。推荐`git log -1`、`git diff <上次目标>..<本次目标> -- IntRuoyiBackend/sql/mysql config/menu-migrations.json`，并运行既有菜单入包检查。
2. 目标预检：重点复核5580。已确认旧态为排产工单池/parent=5700/path=schedule-order/permission空；源码目标为排产工单/parent=900120/path=/mes/pro/schedule-order/permission=mes:pro-schedule-order:query/sort=1。保留900120当前根级/mes/smart-scheduling；对其它差异同样从当前版本定义确认，不能仅修这一个就声称全量一致。
3. 权限核验：按实际业务角色和租户套餐确定必要关联，不把环境差异一律当错误。仅移动目录不应新增无依据授权。
4. 实施：使用本次专用发布worktree、已提交输入和同一releaseTag。发布前留存受影响行与关联权限及恢复依据；新增迁移受身份/旧值/冲突预检保护。应用定义菜单规则，维护仓负责执行和最终状态校验。
5. 收口：两服真实结果通过后将状态改completed，记录证据并按正式worktree/控制台收口规则完成；某一服未修复时保留明确未完成项。
