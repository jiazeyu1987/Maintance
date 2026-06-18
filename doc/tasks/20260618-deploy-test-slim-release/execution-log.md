# 执行日志: 部署瘦身发布包到测试服并验证

## BDD

BDD: 测试服部署瘦身发布包 -> Given NAS 中存在 release-20260618-1006-slim-e2e 且状态 AVAILABLE, When 使用 Playwright 真实点击运行控制台“部署测试服”并执行, Then 发布 operation 最终 SUCCESS，预览命令指向 test/172.30.30.58//opt/intruoyi/runtime，且不包含正式服、备份、恢复或回滚动作。

BDD: 测试服版本一致性验证 -> Given 测试服部署 operation 成功, When 读取远端 .env、docker compose 状态、后端健康检查和前端入口, Then backend/frontend 均运行 release-20260618-1006-slim-e2e，健康检查 HTTP 200 且管理前端真实浏览器入口可加载。

## 执行记录

- 2026-06-18：用户要求部署到测试服务器进行验证。
- 2026-06-18：任务边界确认：只部署测试服 `172.30.30.58`，发布包固定为 `release-20260618-1006-slim-e2e`；不部署备份服或正式服，不执行备份、恢复、回滚或数据同步。
- 2026-06-18：读取经验索引并命中发布预检、发布/备份恢复基线、服务器访问基线、登录访问基线和项目错误预防短记忆。
- 2026-06-18：`npx` 可用，Node `v24.12.0`，npm `11.6.2`。
- 2026-06-18：本机运行控制台后端 `http://127.0.0.1:48181/actuator/health` 返回 HTTP 200，前端 `http://127.0.0.1:48182/` 返回 HTTP 200。
- 2026-06-18：`GET /admin-api/infra/runtime-control/release-status` 可读回 `release-20260618-1006-slim-e2e`，状态 `AVAILABLE`，`checksumPresent=true`，`publishScope=code-only`，`component=intruoyi`，无阻塞原因。
- 2026-06-18：测试服发布前健康检查：`http://172.30.30.58:48081/actuator/health` 返回 HTTP 200，`http://172.30.30.58:8081/` 返回 HTTP 200。
- 2026-06-18：SSH 测试服 `172.30.30.58` 可达；`/opt/intruoyi/runtime` 存在且可写，`/mnt/nas` 存在且可写，`/mnt/nas/Backup/ReleasePackage` 可读。
- 2026-06-18：测试服容量：根分区 `/` 可用约 `27G`，`/mnt/nas` 可用约 `19T`。
- 2026-06-18：测试服发布前当前版本为 `IMAGE_TAG=release-20260618-0056-codeonly-e2e`；backend/frontend 镜像均为旧 tag 且 running。
- 2026-06-18：Playwright 真实打开运行控制台前端 `http://127.0.0.1:48182/`，标题 `运行控制台`，console error `0`，failed request `0`。
- 2026-06-18：Playwright 填写 `release-20260618-1006-slim-e2e` 和发布原因，点击 `部署测试服` 并预览命令；预览参数包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`、`-RemoteReleaseRoot /var/lib/docker/intruoyi-releases`、`-RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data`。
- 2026-06-18：预览命令边界检查通过：未包含正式服 `172.30.30.57`、`promote-prod`、`backup-now`、`restore-data` 或 `rollback-app`。
- 2026-06-18：Playwright 真实前端提交测试服部署 operation `op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e`。
- 2026-06-18：部署 operation 最终 `SUCCESS`；日志显示远端 `.env` 已写入新 tag、backend/frontend 重新创建并启动、远端 HTTP readiness 通过、operation lock `LOCK_RELEASED`、测试服后端和前端 HTTP 200。
- 2026-06-18：部署后远端 `.env` 为 `IMAGE_TAG=release-20260618-1006-slim-e2e`。
- 2026-06-18：部署后 `docker compose ps --format json` 显示 backend 镜像 `intruoyi-backend:release-20260618-1006-slim-e2e`、frontend 镜像 `intruoyi-frontend:release-20260618-1006-slim-e2e`，两者状态均为 `running`。
- 2026-06-18：测试服健康检查：后端 `http://172.30.30.58:48081/actuator/health` HTTP 200 且返回 `{"status":"UP"}`；前端 `http://172.30.30.58:8081/` HTTP 200；`http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` HTTP 200，content-type `application/javascript`。
- 2026-06-18：关键迁移记录只读查询通过：`20260617_dcc_browser_performance_indexes`、`20260617_erp_kingdee_event_callback`、`20260617_mes_scheduler_role_smart_scheduling_tab` 在 `release-20260618-1006-slim-e2e` / `test` 下均为 `SKIPPED_ALREADY_APPLIED`。
- 2026-06-18：Playwright 真实打开测试服前端入口 `http://172.30.30.58:8081/`，自动进入 `http://172.30.30.58:8081/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，页面包含 `瑛泰数字化平台` 与 `登录`，console error `0`，failed request `0`。
- 2026-06-18：额外只读登录探针发现测试服 `测试租户/aoteman` 登录失败，后端返回业务 `code=500` 和提示 `登录失败，账号密码不正确`；本任务未把该登录探针列为验收项，未切换账号伪装通过，未执行业务写入。
- 2026-06-18：`validate_cicd_environment.py --evidence doc\tasks\20260618-deploy-test-slim-release\ci-cd-evidence.md` PASS。
- 2026-06-18：`task-closeout-cleanup --mode preview` PASS，保留 `task.md`、`execution-log.md`、`ci-cd-evidence.md`，无删除项、阻塞项或警告。
- 2026-06-18：`task-closeout-cleanup --mode apply` PASS，无删除项、阻塞项或警告。

GREEN: experience-preflight -> PASS，本轮只允许通过真实前端触发 `deploy-release` 到测试服务器 `172.30.30.58` 的 `/opt/intruoyi/runtime`；禁止备份服、正式服、备份、恢复、回滚、数据库整库同步和 MinIO/NAS 业务数据同步。

## 待执行门禁

- `experience-preflight` 已通过，可以触发测试服部署 operation。

## GREEN

GREEN: npx prerequisite -> PASS
GREEN: runtime-control local health -> PASS
GREEN: release-status candidate release-20260618-1006-slim-e2e AVAILABLE -> PASS
GREEN: test server read-only preflight -> PASS
GREEN: runtime-control Playwright deploy preview boundary -> PASS
GREEN: runtime-control deploy operation op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e -> PASS
GREEN: test server image tag release-20260618-1006-slim-e2e -> PASS
GREEN: test server backend/frontend health -> PASS
GREEN: test server release migration status -> PASS
GREEN: test server Playwright frontend entry smoke -> PASS
GREEN: ci-cd evidence validation -> PASS
GREEN: task-closeout-cleanup preview -> PASS
GREEN: task-closeout-cleanup apply -> PASS

## 非验收探针

RED: optional test tenant login probe -> FAIL, 测试服 `测试租户/aoteman` 返回“登录失败，账号密码不正确”；该探针用于判断是否能继续做登录后 E2E，不属于本任务部署验收项，后续若要求登录后 E2E 需要先提供或确认测试服有效账号。
