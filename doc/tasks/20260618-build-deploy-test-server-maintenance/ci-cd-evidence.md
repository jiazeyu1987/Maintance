# CI/CD 证据

## Environment

- Windows maintenance host: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Target environment: `test`
- Target host: `172.30.30.58`
- Remote runtime directory: `/opt/intruoyi/runtime`

## Commands

- `python -X utf8 -m pytest scripts\tests -q`
- `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py script\tests\test_showroom_release_sql_contract.py -q`
- `node tests\e2e\vite-release-build-plugin-contract-static.spec.js`
- Playwright real UI build-release and deploy-release operations.

## Secrets

- No secret values were written to repository files or task evidence.
- Remote access used existing documented SSH/runtime configuration.

## Pipeline

- Build release package from maintenance runtime control frontend.
- Deploy release package to test server from maintenance runtime control frontend.
- Verify operation status, manifest, remote runtime, schema, and browser entry.

## Verification

- Build operation `op-2026-06-18T094150771556100Z-0c41d8dd-8879-42b1-b068-4e0457975aa7` -> `SUCCESS`.
- Deploy operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` -> `SUCCESS`.
- Remote backend health and frontend browser load both passed.

## Rollback

- No rollback was executed or required.
- Release lock and migration state allow a future explicit rollback/deploy action through the maintained release workflow if authorized.

## Blockers

- Resolved: stale test release lock from an older failed deploy.
- Resolved: preflight planner dependency handling for parent migration applied earlier in the same release plan.

## 环境和目标

- 发布入口：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端源码输入：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 管理前端源码输入：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 目标环境：test
- 目标主机：`172.30.30.58`
- 远端运行目录：`/opt/intruoyi/runtime`
- 发布范围：`code-only` / `intruoyi`

## RED/GREEN 发布契约

- RED：`python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` 失败，维护仓发布脚本缺少 `sql/showroom` 奖项 SQL 门禁，维护仓 migration policy gate 导入错误且不支持指定 SQL 文件。
- GREEN：`python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` 通过，3 passed。
- GREEN：`python -X utf8 -m pytest scripts\tests -q` 通过，8 passed。
- GREEN：PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- GREEN：后端真实 `sql/showroom/20260613_showroom_award_and_hall_item_schema.sql` migration policy gate 通过，`migrationCount=1`。
- GREEN：维护仓 `ops\release\run-release-migration-policy-gate.py` 对同一真实 SQL 文件通过，确认维护仓 CLI 参数能力一致。

## 构建发布证据

- releaseTag：`release-20260618-1742-showroom-sql-vite`
- 构建 operation：`op-2026-06-18T094150771556100Z-0c41d8dd-8879-42b1-b068-4e0457975aa7`
- 构建状态：`SUCCESS`
- 发布包路径：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260618-1742-showroom-sql-vite`
- 发布包大小：`813535256 bytes` / `775.85 MiB`
- 包内容：包含 `required-sql`、`resources`、`runtime-env`、`smoke`、`docker-compose.yml`、镜像 tar、`manifest.json`、`release-manifest.json`；不包含 `docker-build-context`。
- manifest：包含 `20260606_showroom_hall_product_canvas_layout` 和依赖它的 `20260613_showroom_award_and_hall_item_schema`。

## 测试服部署证据

- 部署 operation：`op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a`
- 部署状态：`SUCCESS`
- 日志结果：`Publish completed for test.`
- 测试服 `.env`：`IMAGE_TAG=release-20260618-1742-showroom-sql-vite`
- 容器镜像：
  - `intruoyi-backend intruoyi-backend:release-20260618-1742-showroom-sql-vite running`
  - `intruoyi-frontend intruoyi-frontend:release-20260618-1742-showroom-sql-vite running`
- 后端健康：`http://172.30.30.58:48081/actuator/health` -> HTTP 200，`{"status":"UP"}`
- 前端入口：`http://172.30.30.58:8081/` -> HTTP 200
- 浏览器验证：Playwright 打开测试服前端，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0。

## 中途阻塞和处置

- 旧锁阻塞：旧 `test-release-20260618-1437-showroom-sql-smoke-env` 锁为 `RUNNING`，已按事实收口为 `FAILED` 后重试。
- 预检误判阻塞：旧逻辑不把同一发布包内前置 `APPLY` 的迁移视为满足依赖，导致 20260613 被误判缺 20260606；已通过 TDD 修复并再次部署成功。
