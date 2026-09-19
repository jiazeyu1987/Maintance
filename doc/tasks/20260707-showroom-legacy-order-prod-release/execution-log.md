# 执行日志

BDD: 干净发布输入构建排序修复包 -> Given 主工作区存在无关未提交 SQL 和 MES 脏改 / When 为 `52e2fd70c3` 创建干净后端 worktree 并执行 code-only build-release / Then 发布包 manifest 必须指向排序修复提交，且不得包含无关 draft SQL。
GREEN: experience-preflight -> PASS，已读取发布/服务器/PowerShell 门禁；本次正式服动作仅限排序修复 code-only 发布，先测试服后正式服。
BLOCKER: build-release-main-worktree -> FAIL，主工作区 `sql/mysql/20260705_showroom_legacy_product_code_auto_confirmable_draft.sql` 缺 release-migration 元数据，不能作为发布输入。
## 2026-07-07T21:48:43
- GREEN: release-contract-fix -> PASS, 补齐 20260707_mes_feedback_import_record_allow_repeat_source_row.sql 发布迁移元数据并通过脚本测试。
- GREEN: build-release-submit -> RUNNING, releaseTag=release-20260707-showroom-legacy-order-8284cf7b1b。

## 2026-07-07T22:17:06
- GREEN: build-release -> PASS, releaseTag=release-20260707-showroom-legacy-order-4d45de47f5。
- GREEN: publish-test -> FAILED。

## 2026-07-07T22:32:35
- GREEN: migration-collation-fix -> PASS, 表单槽位回填显式使用 utf8mb4_general_ci 并通过脚本测试。
- GREEN: build-release -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-36ff30f582。

## 2026-07-07T22:44:20
- GREEN: publish-test -> FAILED, releaseTag=release-20260707-showroom-legacy-order-36ff30f582。

## 2026-07-07T22:59:05
- GREEN: migration-empty-collation-fix -> PASS, 表单槽位执行表空值判断显式使用 utf8mb4_general_ci 并通过脚本测试。
- GREEN: build-release -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-c0a67d13ee。

## 2026-07-07T23:10:54
- GREEN: publish-test -> FAILED, releaseTag=release-20260707-showroom-legacy-order-c0a67d13ee。

## 2026-07-07T23:30:05
- GREEN: migration-string-collation-fix -> PASS, 表单槽位迁移字符串比较统一使用 utf8mb4_bin 并通过脚本测试。
- GREEN: build-release -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-c7de28b234。

## 2026-07-07T23:43:24
- GREEN: publish-test -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-c7de28b234。

## 2026-07-07T23:59:20
- GREEN: publish-test-runtime-image -> PASS, 测试服 `intruoyi-backend` 与 `intruoyi-frontend` 均运行 `release-20260707-showroom-legacy-order-c7de28b234`。
- GREEN: test-server-db-order-evidence -> PASS, 测试服 `tenant_id=1` 展厅产品 149 条、135 条具备旧产品编号；按 `legacy_product_code ASC, id ASC` 查询首批为 `product_010`、`product_011`、`product_012`...，证明正式数据存在旧编号排序基础。
- BLOCKER: test-admin-page-readonly-e2e -> 测试服 `芋道源码/admin` 使用已知默认密码登录失败；`测试租户/aoteman` 可登录但产品列表为空，不能作为产品排序验收数据。当前继续以已部署镜像 + 单元测试 + 测试服数据库只读排序证据作为推进依据。
## 2026-07-08T00:04:10
- GREEN: mark-release-tested -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-c7de28b234, operationId=op-2026-07-07T155242642501500Z-b2e1686a-e4f7-4779-8466-09215fd0df47。

## 2026-07-08T00:10:00
- GREEN: promote-prod -> SUCCESS, releaseTag=release-20260707-showroom-legacy-order-c7de28b234, operationId=op-2026-07-07T155411982654300Z-7b279975-2c1c-4640-887d-154217a3e1c3。

## 2026-07-08T00:24:30
- GREEN: prod-health -> PASS, 正式服 backend `/actuator/health` 与 frontend `:8081/` 均可访问。
- GREEN: prod-runtime-image -> PASS, 正式服 `intruoyi-backend` 与 `intruoyi-frontend` 均运行 `release-20260707-showroom-legacy-order-c7de28b234`。
- GREEN: prod-db-order-evidence -> PASS, 正式服 `tenant_id=1` 产品数据可按 `legacy_product_code ASC, id ASC` 查询，旧编号为空的数据统计在尾部规则覆盖范围内。
## 2026-07-08T00:28:00
- GREEN: closeout-config-restore -> PASS, 已恢复 runtime-control.local.yaml 到本次发布前配置。
- GREEN: task-status -> COMPLETED, 正式服产品管理旧产品编号排序发布与验证完成。
