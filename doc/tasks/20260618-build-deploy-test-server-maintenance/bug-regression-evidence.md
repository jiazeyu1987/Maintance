# 回归证据: 维护仓缺展厅奖项 SQL 发布门禁

## Bug

- Maintenance release path could build/deploy code that queries showroom award tables while the release contract missed required showroom schema SQL.
- Release preflight could incorrectly block child migrations that depend on an earlier migration in the same package.

## Expected

- Required SQL, manifest, migration gate, and deploy preflight must include showroom award schema and dependencies.
- A child migration can depend on a parent migration that is planned earlier in the same passed release plan.

## Reproduction

- `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` failed before the release contract fix.
- `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` failed before same-package dependency handling was fixed.

## Root Cause

- Maintenance release scripts did not include the relevant `sql/showroom` migrations.
- `release_preflight_plan.py` checked dependencies only against target `APPLIED` state, not against earlier successful plan items.

## Verification

- Test server deploy operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` succeeded.
- Remote migration state and schema verification passed.

## Blockers

- Resolved: stale failed deployment lock.
- Resolved: preflight dependency planner bug.

## Bug 摘要

- 已知测试服曾出现 `ShowroomAwardDO` 查询 `showroom_award`，但目标库缺表。
- 业务源码仓已修正对应发布契约，但当前实际发布入口是维护仓。
- 维护仓发布脚本若不包含相同门禁，后续从维护仓构建发布仍可能复发。

## 期望行为

- 从维护仓构建发布时，`sql/showroom/20260613_showroom_award_and_hall_item_schema.sql` 必须进入 required SQL、manifest 和 migration policy gate。
- deploy-release 到测试服时，后端启动前必须只读检查三张表和关键索引。

## 根因

- 维护仓实际发布入口 `ops/deploy/publish-int-ruoyi.ps1` 只扫描 `sql/mysql`，未纳入后端代码已依赖的 `sql/showroom/20260613_showroom_award_and_hall_item_schema.sql`。
- 维护仓自带 `ops/release` migration 工具仍导入不存在的 `script.release`，且不支持 `--sql-file` / `--file-prefix`，无法表达“只纳入指定展厅 SQL 文件”的发布契约。

## 回归测试

- 新增：`scripts/tests/test_showroom_release_sql_contract.py`。
- RED: `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> FAIL，确认维护仓缺少发布契约与 schema preflight。
- GREEN: 同一命令 -> PASS，3 passed。
- 回归范围：维护仓发布脚本、维护仓 migration policy gate、后端真实展厅 SQL policy gate、发布脚本 PowerShell AST、维护仓 `scripts/tests`。

## 风险

- 该修复不手工补表，不引入 fallback；若后端 SQL 文件缺少 metadata、文件不存在或远端 schema 缺表/缺索引，发布会 fail fast。

## 新增回归: 同一发布包内迁移依赖误判

- 现象：发布包同时包含 `20260606_showroom_hall_product_canvas_layout` 和依赖它的 `20260613_showroom_award_and_hall_item_schema`，但测试服预检仍输出 `BLOCKED_DEPENDENCY_MISSING`。
- 根因：`release_preflight_plan.py` 只检查目标库已 `APPLIED` 的迁移，没有按 manifest 顺序把本次计划中前置 `APPLY` 的迁移加入已满足集合。
- RED: `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` -> FAIL，`test_preflight_accepts_dependency_applied_earlier_in_same_plan` 复现 `blocked`。
- GREEN: 同一命令 -> PASS，9 passed；维护仓与业务仓 `release_preflight_plan.py` 文件哈希一致。
- 生产验证：测试服部署 operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` SUCCESS，20260606 与 20260613 均 `APPLIED`。

## 新增回归: 维护控制台部署预览目标环境契约

- 现象：真实 Playwright 操作“部署测试服”预览时，前端未携带或后端拒绝匹配的 `targetEnvironment=test`，返回 `code=400`。
- 根因：部署类动作没有完整纳入前端目标环境要求；后端校验也未允许 deploy action 携带与默认环境一致的 targetEnvironment。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_runtime_control_frontend_deploy_contract.py -q` PASS。
- GREEN: `mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#publishTestPreviewAcceptsMatchingTargetEnvironmentFromFrontend test` PASS。
- 生产验证：真实页面预览参数包含 `-Mode deploy-release -Environment test ... -ReleaseTag release-20260618-1742-showroom-sql-vite`，执行成功。
