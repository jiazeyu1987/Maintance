# 数据库证据: MES 发布前置数据修复

## Data

### 目标

在用户授权后，补齐测试服 `172.30.30.58` 与备份服 `172.30.30.59` 上 `tenant_id=122` 的 MES 排产/计划角色前置数据，使发布包 `release-20260618-0056-codeonly-e2e` 的 required SQL `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 可以按发布脚本重新执行。

## Migration

### 数据库与工具

- 数据库：MySQL 8.0 容器 `intruoyi-mysql`。
- 发布迁移工具：`ops/deploy/publish-int-ruoyi.ps1` 通过 `infra_release_migration` 与 `infra_release_operation_lock` 管理 required SQL 状态。
- 变更表：`system_tenant_package`、`system_tenant`、`system_role`，以及测试服 stale 状态表 `infra_release_operation_lock`、`infra_release_migration`。

## BDD

- `BDD: 补齐测试租户 MES 前置数据 -> Given tenant_id=122 当前套餐包含 900120 但缺少 5542/5543/5544/5545 且没有启用 mes_scheduler 角色, When 授权数据修复执行, Then tenant_id=122 切换到克隆后的完整菜单套餐并拥有启用的 mes_scheduler 角色。`
- `BDD: 释放测试服发布重试 -> Given 上一次测试服发布失败后 release lock 与 migration 停留 RUNNING, When 将失败态明确写回, Then 下一次 deploy-release 可以重新 APPLY 未完成 required SQL。`

## RED

- `RED: test-role-precondition -> FAIL，测试服 tenant_id=122 目标角色数为 0，智能排程菜单树缺失数为 4。`
- `RED: backup-role-precondition -> FAIL，备份服 tenant_id=122 目标角色数为 0，智能排程菜单树缺失数为 4。`
- `RED: test-release-lock -> FAIL，测试服 infra_release_operation_lock 中 release-20260618-0056-codeonly-e2e 为 RUNNING，阻塞重试。`

## Safety

### 变更策略

- 不直接修改原套餐菜单 JSON；为 `tenant_id=122` 克隆当前套餐，在克隆套餐中补齐 `5542/5543/5544/5545`，再更新 `system_tenant.id=122` 指向克隆套餐。
- 创建或启用 `system_role.code=mes_scheduler`、`tenant_id=122`、`status=0`、`deleted=0` 的正式角色，角色名为 `排产员`。
- 测试服 stale release lock 与 stale migration 状态从 `RUNNING` 改为 `FAILED`，保留失败信息，允许发布脚本重试。

## Rollback

### 回滚/恢复计划

- 若数据修复后发布仍失败，可将 `system_tenant.id=122` 的 `package_id` 改回修复前套餐，并删除或标记删除本次克隆套餐。
- 可将本次新增/启用的 `mes_scheduler` 角色标记为 `deleted=b'1'` 或恢复修复前状态。
- 若发布重试失败，保持 `infra_release_migration` 的失败状态，由下一轮发布按现有脚本重新 APPLY；不得改成成功态掩盖失败。

## GREEN

- `GREEN: test-precondition-repair -> PASS，测试服 tenant_id=122 已切换到克隆套餐 114，mes_scheduler/排产员 角色启用，智能排程菜单树缺失数为 0。`
- `GREEN: backup-precondition-repair -> PASS，备份服 tenant_id=122 已切换到克隆套餐 113，mes_scheduler/排产员 角色启用，智能排程菜单树缺失数为 0；tenant_id=121 仍保持原套餐 111。`
- `GREEN: stale-state-repair -> PASS，测试服 release lock 与 migration 残留 RUNNING 均改为 FAILED，发布脚本可重新 APPLY 未完成 required SQL。`

## Verification

- 数据修复后通过只读 SQL 验证角色数、缺失菜单数、测试服 stale 状态和备份服 tenant_id=121 套餐边界。
- 已通过真实前端重试测试服发布与备份服发布，并验证远端容器、健康检查和浏览器入口。

## Blockers

### 阻塞

- 当前无新阻塞；用户已授权本次数据前置修复。
