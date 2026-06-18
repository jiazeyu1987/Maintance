# 任务: 部署瘦身发布包到测试服并验证

## 任务目标

将已构建并通过真实 E2E 验证的 `code-only` 发布包 `release-20260618-1006-slim-e2e` 部署到测试服务器，并完成测试服版本一致性、健康检查和真实浏览器入口验证。

## 任务边界

- 本次只部署测试服务器 `172.30.30.58`。
- 不部署备份服或正式服。
- 不执行备份、恢复、回滚、数据库整库同步或 MinIO/NAS 业务数据同步。
- 发布包固定为 `release-20260618-1006-slim-e2e`，组件固定为 `intruoyi`，发布范围为 `code-only`。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：测试服部署预览必须包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`；不得包含 `172.30.30.57`、`promote-prod`、`backup-now`、`rollback`、`restore-data`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布必须通过运行控制台真实前端入口提交 operation；发布完成不能只看健康检查，还必须核 operation、manifest、远端 `IMAGE_TAG`、运行镜像和迁移状态。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服务器 IP 为 `172.30.30.58`，远端运行目录为 `/opt/intruoyi/runtime`；服务器写入和重启必须有当前任务授权，本任务授权来自用户“部署到测试服务器进行验证”。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：涉及测试环境 E2E 时必须有当前任务授权；本轮只验证管理前端入口加载，不做登录写入。
- `docs/agent-memory/project-error-prevention.md`：环境发布验证不能只看健康，必须核 operation SUCCESS、manifest、远端 IMAGE_TAG/镜像、迁移状态和真实浏览器入口。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。预览边界、发布 operation、远端版本或健康检查任一失败即阻断。
- `是否从根因和长期维护角度解决`：是。复用已构建发布包和运行控制台正式部署链路，不手工 SSH 替代部署。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 测试服部署瘦身发布包 -> Given NAS 中存在 release-20260618-1006-slim-e2e 且状态 AVAILABLE, When 使用 Playwright 真实点击运行控制台“部署测试服”并执行, Then 发布 operation 最终 SUCCESS，预览命令指向 test/172.30.30.58//opt/intruoyi/runtime，且不包含正式服、备份、恢复或回滚动作。`
- `BDD: 测试服版本一致性验证 -> Given 测试服部署 operation 成功, When 读取远端 .env、docker compose 状态、后端健康检查和前端入口, Then backend/frontend 均运行 release-20260618-1006-slim-e2e，健康检查 HTTP 200 且管理前端真实浏览器入口可加载。`

## 里程碑

- [x] 创建任务文档并读取经验门禁。
- [x] 完成部署前 preflight，并在执行日志记录 `GREEN: experience-preflight -> PASS`。
- [x] 用 Playwright 真实前端预览并执行测试服部署 operation。
- [x] 完成测试服远端版本、健康、迁移和浏览器验证。
- [x] 更新证据、收尾清理并提交任务记录。

## 预期验证

- 本机运行控制台后端/前端可访问。
- `release-status` 可读回 `release-20260618-1006-slim-e2e`，状态 `AVAILABLE`。
- 测试服部署预览边界正确。
- 部署 operation 最终 `SUCCESS`。
- 测试服 `.env` 中 `IMAGE_TAG=release-20260618-1006-slim-e2e`。
- 测试服 `docker compose ps` 中 backend/frontend 镜像 tag 为 `release-20260618-1006-slim-e2e` 且运行中。
- 测试服后端健康检查 HTTP 200 且返回 `UP`。
- Playwright 真实打开 `http://172.30.30.58:8081/`，进入登录页，console error 为 0。
- `validate_cicd_environment.py` 通过。

## 当前状态

completed

## Current Status

completed

## 当前验证

- `npx` 可用：`D:\Programs\npx.ps1`，Node `v24.12.0`，npm `11.6.2`。
- 本机运行控制台后端 `48181` 与前端 `48182` 均返回 HTTP 200。
- `release-status` 可读回 `release-20260618-1006-slim-e2e`，状态 `AVAILABLE`，`checksumPresent=true`，`publishScope=code-only`，`component=intruoyi`。
- 测试服发布前健康检查：后端 `48081` HTTP 200，前端 `8081` HTTP 200。
- SSH 测试服 `172.30.30.58` 可达；`/opt/intruoyi/runtime` 存在且可写，`/mnt/nas` 存在且可写，`/mnt/nas/Backup/ReleasePackage` 可读。
- 测试服容量：根分区 `/` 可用约 `27G`，`/mnt/nas` 可用约 `19T`。
- 发布前测试服当前 `IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 均运行该旧 tag。
- Playwright 真实前端预览 `部署测试服` PASS：`-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`、`-RemoteReleaseRoot /var/lib/docker/intruoyi-releases`、`-RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data`；未包含正式服、备份、恢复或回滚动作。
- Playwright 真实前端提交部署 operation `op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e`，最终状态 `SUCCESS`。
- 测试服部署后 `.env` 为 `IMAGE_TAG=release-20260618-1006-slim-e2e`。
- 测试服 backend 镜像 `intruoyi-backend:release-20260618-1006-slim-e2e`，frontend 镜像 `intruoyi-frontend:release-20260618-1006-slim-e2e`，两者均 `running`。
- 测试服后端健康检查 `http://172.30.30.58:48081/actuator/health` 返回 HTTP 200，内容 `{"status":"UP"}`；前端入口 `http://172.30.30.58:8081/` 返回 HTTP 200；`/pdfjs/pdf.worker.mjs` 返回 HTTP 200 `application/javascript`。
- 关键迁移记录 `20260617_dcc_browser_performance_indexes`、`20260617_erp_kingdee_event_callback`、`20260617_mes_scheduler_role_smart_scheduling_tab` 在测试环境均为 `SKIPPED_ALREADY_APPLIED`。
- Playwright 真实打开测试服前端，进入 `http://172.30.30.58:8081/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，页面包含登录入口与 `瑛泰数字化平台`，console error `0`，failed request `0`。
- 额外只读登录探针：测试服 `测试租户/aoteman` 登录返回业务 `code=500`、提示 `登录失败，账号密码不正确`；该探针不是本任务验收项，本任务未切换账号伪装通过，也未执行任何业务写入。
- `validate_cicd_environment.py --evidence doc\tasks\20260618-deploy-test-slim-release\ci-cd-evidence.md` PASS。
- `task-closeout-cleanup --mode preview` PASS：保留 `task.md`、`execution-log.md`、`ci-cd-evidence.md`，无删除项、阻塞项或警告。
- `task-closeout-cleanup --mode apply` PASS：无删除项、阻塞项或警告。

## Cleanup Keep

- `doc/tasks/20260618-deploy-test-slim-release/ci-cd-evidence.md`
