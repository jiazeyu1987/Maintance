# 任务: 维护仓构建并发布到测试服务器

## 任务目标

- 从 `D:\ProjectPackage\Int\IntRuoyiMaintance` 维护仓发布入口构建新的 IntRuoyi `code-only` 发布包。
- 将新发布包部署到测试服务器 `172.30.30.58` 的 `/opt/intruoyi/runtime`。
- 发布后验证 operation、manifest、远端 `IMAGE_TAG`、backend/frontend 运行镜像、健康检查、required SQL / schema 门禁和真实浏览器前端入口。

## 授权范围

- 用户需求：“构建发布到测试服务器”。
- 允许：使用维护仓运行控制台/发布脚本构建发布包，发布到测试服务器，重建测试服 backend/frontend 容器，执行只读远端验证。
- 禁止：备份服、正式服、备份、恢复、回滚、数据库整库同步、MinIO/NAS 业务数据同步、手工补表替代发布契约。

## 上一任务检查

- 上一维护仓任务：`doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/`。
- 状态：`completed`。
- 处理：上一任务已完成，本任务可以开始。

## 经验门禁

- 来源：`docs/experience-index.md`。
- 命中文档：
  - `docs/release-build-preflight-lessons.md`：构建发布必须通过维护仓运行控制台真实前端或等价前端操作；发布前确认预览命令边界；发布完成不能只看健康检查。
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布入口必须是维护仓；`code-only` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁；构建成功以 Manifest v1 与 NAS 包为准。
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服 IP `172.30.30.58`，远端运行目录 `/opt/intruoyi/runtime`；远端凭据不得写入仓库。
  - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：本次仅验证测试服登录入口加载，不登录写入业务数据。
- 适用强制门禁：
  - 高风险发布动作前必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。
  - 预览命令不得包含正式服、备份服、备份、恢复、回滚或生产发布动作。
  - 维护仓发布脚本必须包含本次已知展厅奖项 SQL 门禁，否则不得构建发布。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少发布契约、manifest、required SQL、远端 schema 或 operation 成功证据时 fail fast。
- `是否从根因和长期维护角度解决`：是。先补维护仓发布入口缺失的 `sql/showroom` 奖项 schema 门禁，再构建发布。
- `是否存在临时补丁或绕过`：否。不手工 SSH 补表，不用测试服运行时手工改动替代发布脚本。

## BDD 场景

- `BDD: 维护仓发布包含展厅奖项 SQL 门禁 -> Given 后端代码查询 showroom_award When 从维护仓 build-release Then required SQL / manifest / migration gate 包含 sql/showroom/20260613_showroom_award_and_hall_item_schema.sql。`
- `BDD: 测试服部署前 schema preflight -> Given deploy-release 到测试服 When required SQL 执行完成 Then 后端启动前只读校验 showroom_award、showroom_award_revision、showroom_hall_item 和关键索引，缺失即失败。`
- `BDD: 构建发布到测试服 -> Given 维护仓发布入口和目标测试服授权 When 使用真实前端操作构建并部署 code-only 发布包 Then build/deploy operation 均 SUCCESS，远端 backend/frontend 运行新 releaseTag 且健康。`

## 里程碑

- [x] M1 建立任务文档、读取经验门禁并确认上一任务完成。
- [x] M2 RED/GREEN：补齐维护仓展厅奖项 SQL 发布门禁。
- [x] M3 发布前 preflight：运行控制台、Docker 基础镜像、迁移策略、远端测试服状态。
- [x] M4 使用真实前端操作构建发布包。
- [x] M5 使用真实前端操作部署到测试服务器。
- [x] M6 发布后验证、任务证据、提交任务记录。

## 预期验证

- `python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q`
- `python -X utf8 -m pytest scripts\tests -q`
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1`
- 构建 operation `SUCCESS`，发布包 `AVAILABLE`，Manifest v1 存在。
- 测试服 deploy operation `SUCCESS`。
- 测试服 `.env` 的 `IMAGE_TAG=<releaseTag>` 与 backend/frontend 镜像 tag 一致。
- 后端健康 HTTP 200，前端入口 HTTP 200，Playwright 真实打开测试服登录页 console error 为 0。

## 当前状态

completed

## Current Status

completed

## 进展记录

- M2 完成：新增 `scripts/tests/test_showroom_release_sql_contract.py`，维护仓发布脚本已纳入 `sql/showroom/20260613_showroom_award_and_hall_item_schema.sql`、manifest metadata、migration policy gate 和服务启动前 schema preflight。
- M2 验证：`python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` PASS；`python -X utf8 -m pytest scripts\tests -q` PASS；PowerShell AST parse PASS；维护仓 CLI 和后端真实 `sql/showroom` 文件 migration gate PASS。
- M3 完成：修复调度冒烟 npm 运行时环境固化、showroom SQL 20260606/20260613 依赖入包、测试服旧失败锁收口；修复发布预检“同一发布包内前置 APPLY 迁移不能满足后置 dependsOn”的误判。
- M4 完成：通过维护控制台真实前端构建 `release-20260618-1742-showroom-sql-vite`，operation `op-2026-06-18T094150771556100Z-0c41d8dd-8879-42b1-b068-4e0457975aa7` SUCCESS，发布包大小 `813535256 bytes` / `775.85 MiB`，不包含 `docker-build-context`。
- M5 完成：通过维护控制台真实前端部署测试服，operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` SUCCESS。
- M5 远端验证：测试服 `.env` `IMAGE_TAG=release-20260618-1742-showroom-sql-vite`；`intruoyi-backend` 与 `intruoyi-frontend` 镜像均为该 tag 且运行中；后端健康 `{"status":"UP"}`；前端 HTTP 200。
- M5 schema 验证：`20260606_showroom_hall_product_canvas_layout`、`20260613_showroom_award_and_hall_item_schema`、`20260618_showroom_publicity_role_menu_scope` 均为 `APPLIED`；`showroom_award`、`showroom_award_revision`、`showroom_hall_item` 和关键索引存在。
- M5 浏览器验证：Playwright 打开 `http://172.30.30.58:8081/`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0，截图 `doc/tasks/20260618-build-deploy-test-server-maintenance/test-server-frontend-after-deploy.png`。
- M6 完成：维护仓测试、业务仓发布预检测试、前端构建契约测试、PowerShell AST、CI/CD/bug/database 证据校验均通过。

## Cleanup Keep

- `doc/tasks/20260618-build-deploy-test-server-maintenance/ci-cd-evidence.md`
- `doc/tasks/20260618-build-deploy-test-server-maintenance/bug-regression-evidence.md`
- `doc/tasks/20260618-build-deploy-test-server-maintenance/database-schema-evidence.md`
- `doc/tasks/20260618-build-deploy-test-server-maintenance/test-server-frontend-after-deploy.png`
