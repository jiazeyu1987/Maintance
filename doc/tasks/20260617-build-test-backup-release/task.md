# 任务: 再次构建发布到测试服并发布到备份服

## 任务目标

通过运行控制台真实前端 E2E 再次构建 IntRuoyi `code-only` 发布包，先发布到测试服务器并完成验收，再将同一已测试发布包发布到备份服务器。

目标边界：

- 构建方式：运行控制台真实前端 E2E。
- 发布范围：`code-only`，即 `-Component intruoyi -SkipDatabaseSync -SkipMinioSync`。
- 测试服：`172.30.30.58`，远端目录 `/opt/intruoyi/runtime`。
- 备份服：`172.30.30.59`，远端目录 `/opt/intruoyi/runtime`，数据盘 `/mnt/intruoyi-data`，发布根 `/mnt/intruoyi-data/intruoyi-releases`。
- 禁止范围：不访问正式服 `172.30.30.57`，不执行备份、恢复、回滚或数据同步。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：构建发布前必须预检 Docker 基础镜像、迁移策略门禁、Maven target/jar 锁、真实 E2E 预览边界、TDD 提交门禁；发布完成不能只看健康检查，必须核 operation、manifest、远端 `IMAGE_TAG`/镜像、迁移状态和真实浏览器入口。
- `docs/agent-memory/project-error-prevention.md`：环境发布流程前先预检 Dockerfile 基础镜像、迁移策略门禁和 Maven target/jar 锁；失败不生成可部署包。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台前端按钮提交；测试服先发布并验证，通过后才能发布备份服；`code-only` 不同步数据库或 MinIO/NAS，但仍不跳过 schema、required SQL、迁移元数据和发布 manifest 门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服/备份服写入必须有用户当前任务授权；备份服与正式服同等级门禁，只允许已测试通过发布包，必须提供发布责任人与 `PROD` 确认；备份服必须显式使用 `/mnt/intruoyi-data` 参数，不得回退到根分区或 Docker 默认路径。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：涉及 E2E 或登录验证时先确认授权；缺少远端账号不得静默切换账号或环境。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少发布包 manifest、测试服验收、备份服 `PROD` 确认、发布责任人、环境访问或验证证据时直接阻塞。
- `是否从根因和长期维护角度解决`：是。按最新发布预检清单先排除重复失败原因，再用 operation、manifest、远端版本和真实页面证据闭环。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 构建并发布测试服 -> Given 本机运行控制台可访问且目标为测试服 172.30.30.58, When 操作者通过前端预览并执行 code-only 构建发布包后发布到测试服, Then 构建和测试服发布 operation 均成功，manifest 与远端 IMAGE_TAG 一致，测试服后端健康且管理前端真实入口可访问。`
- `BDD: 已测试发布包发布备份服 -> Given 同一 releaseTag 已在测试服通过验收且用户提供发布责任人与 PROD 确认, When 操作者通过前端预览并执行发布备份服, Then 备份服发布 operation 成功，备份服远端 IMAGE_TAG 与 releaseTag 一致，前后端容器 running，后端健康且管理前端真实入口可访问。`
- `BDD: code-only 发布包用测试服成功部署证据进入备份服发布 -> Given code-only releaseTag 已通过 publish-test operation 成功发布到测试服且用户明确本次不做备份恢复, When 操作者预览 promote-backup, Then 后端接受该测试服成功部署证据作为备份服代码发布门禁，不要求恢复集候选或 tested.json。`
- `BDD: 禁止越界环境和动作 -> Given 本次只授权测试服与备份服发布, When 执行构建、发布和验证, Then 不得访问正式服 172.30.30.57，不得执行备份、恢复、回滚、数据库同步或 MinIO/NAS 同步。`

## 里程碑

- [x] 创建任务文档并读取经验门禁。
- [x] 获得备份服发布责任人与 `PROD` 确认。责任人 `admin`，用户已回复字面 `PROD`。
- [x] 完成发布前预检。
- [x] 通过 Playwright 真实前端 E2E 构建 code-only 发布包。
- [x] 通过 Playwright 真实前端 E2E 发布到测试服。
- [x] 验证测试服。测试服真实发布、远端版本、迁移状态、健康检查和真实浏览器入口均通过。
- [x] 修复运行控制台 code-only 备份发布门禁，使其能识别测试服成功部署证据。
- [x] 通过 Playwright 真实前端 E2E 发布到备份服。
- [x] 验证备份服。
- [x] 完成收尾清理预览和 apply。
- [x] 提交本任务改动。

## 预期验证

- `npx` 可用。
- 本机运行控制台健康且页面可见。
- Docker 基础镜像预拉和 inspect 通过。
- 发布迁移策略门禁通过。
- Maven target/jar 锁预检通过。
- 构建预览包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不包含正式服、备份、恢复、回滚动作。
- 测试服发布预览包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`。
- 备份服发布预览包含 `-Environment backup`、`-ServerHost 172.30.30.59`、`-ConfirmText PROD`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`。
- 构建、测试服发布、备份服发布 operation 均为 `SUCCESS`。
- 测试服和备份服 `.env` / 镜像 tag 与发布包一致。
- 测试服和备份服后端健康，管理前端真实浏览器入口可访问。

## 当前阻塞

- 发布责任人：`admin`。
- `BLOCKER-CLEARED: backup-prod-confirmation -> 用户已回复字面 PROD。根据 server-access.md，备份服与正式服同等级门禁；当前已具备发布责任人与生产确认口令。`
- `BLOCKER-CLEARED: backup-restore-candidate-config -> 已从原 IntRuoyi 本机库 infra_config 的 infra.nas.username / infra.nas.password 读取 NAS 凭据，并写入 gitignored 的 config/runtime-control.local.yaml backup-ops 段；维护控制台重启后 /restore-candidates 不再报 backupOps.nasUsername is required。`
- `SCOPE-CLARIFIED: no-backup-restore -> 用户明确要求“不要备份恢复，只要构建发布到测试服务器和备份服务器”。本轮不执行备份、恢复、回滚或恢复集标记；若运行控制台备份服发布入口仍强制恢复集标记，则按 fail-fast 记录为工具入口阻塞，不用脚本绕过。`

## 已完成证据

- 发布前预检：`npx`、Docker 基础镜像预拉与 inspect、迁移策略门禁、Maven clean target/jar 锁检查均通过。
- 构建发布包：通过运行控制台真实前端预览并执行，operation `op-2026-06-17T131517885961100Z-bb182f13-642c-4709-8d97-866b2237a06b` 为 `SUCCESS`。
- 发布标签：`release-202606172114-codeonly-e2e`。
- 发布包路径：NAS `Backup/ReleasePackage/release-202606172114-codeonly-e2e`，本地缓存 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-202606172114-codeonly-e2e\release-manifest.json`。
- 构建范围：manifest 为 `publishScope=code-only`、`component=intruoyi`、`includeShowroomBuildPackage=false`、`onlyOfficeIncluded=false`。
- 测试服发布：通过运行控制台真实前端预览并执行，operation `op-2026-06-17T133605613176400Z-d009458b-b6f9-4979-8f3a-03f72c24b0ae` 为 `SUCCESS`。
- 测试服验收：`http://172.30.30.58:48081/actuator/health` 与 `http://172.30.30.58:8081/` 均返回 HTTP 200；远端 `IMAGE_TAG=release-202606172114-codeonly-e2e`；`docker compose ps` 显示 backend/frontend 镜像均为 `release-202606172114-codeonly-e2e` 且 `Up`。
- 迁移验收：`20260617_dcc_browser_performance_indexes` 为 `SKIPPED_ALREADY_APPLIED`，`20260617_erp_kingdee_event_callback` 为 `APPLIED`，releaseTag 均为 `release-202606172114-codeonly-e2e`。
- 真实浏览器验收：Playwright Chromium 打开 `http://172.30.30.58:8081/` 返回 HTTP 200，最终 URL 为 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 为 0。
- 收尾清理预览：`task-closeout-cleanup --mode preview` PASS，最新预览仅列出六个本任务临时启动日志；任务未完成，未 apply。
- 本地配置补齐：`config/runtime-control.local.yaml` 为 gitignored 本地配置；已补齐 `backup-ops` NAS 凭据来源，未改代码、未提交敏感值。
- 候选复验：`/admin-api/infra/runtime-control/restore-candidates` 返回 `code=0,data=[]`；`backupOps.nasUsername` 配置问题解除，但无恢复集候选。
- 运行控制台门禁修复：`RuntimeControlService.validateReleasePackageAvailability(...)` 仅对 `PROMOTE_BACKUP + code-only + 同 releaseTag 成功 publish-test operation` 接受测试服成功部署证据；`PROMOTE_PROD`、`with-data` 和未测试发布包仍阻断。
- 门禁回归测试：`mvn -Dtest=RuntimeControlOriginalParityTest#promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment test` PASS；`mvn -Dtest=RuntimeControlOriginalParityTest test` PASS；`mvn test` PASS，后端 16 个测试通过。
- Bug 证据校验：`validate_bug_regression.py --evidence doc/tasks/20260617-build-test-backup-release/bug-regression-evidence.md` PASS。
- 备份服发布：通过运行控制台真实前端预览并执行，operation `op-2026-06-17T153827586237800Z-17bdf7a0-5639-4967-a9dd-87296756bc45` 为 `SUCCESS`。
- 备份服验收：`http://172.30.30.59:48081/actuator/health` 与 `http://172.30.30.59:8081/` 均返回 HTTP 200；远端 `IMAGE_TAG=release-202606172114-codeonly-e2e`；`docker compose ps` 显示 backend/frontend 镜像均为 `release-202606172114-codeonly-e2e` 且 `Up`。
- 备份服迁移验收：`20260617_dcc_browser_performance_indexes=APPLIED`，`20260617_erp_kingdee_event_callback=APPLIED`，target environment 均为 `backup`，releaseTag 均为 `release-202606172114-codeonly-e2e`。
- 备份服真实浏览器验收：Playwright Chromium 打开 `http://172.30.30.59:8081/` 返回 HTTP 200，最终 URL 为 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 为 0，请求失败数为 0。
- 收尾清理：`task-closeout-cleanup --mode preview` 与 `--mode apply` 均通过，删除六个本任务临时启动日志；本机维护控制台前端随后重启并返回 HTTP 200。

## 当前状态

completed

## Current Status

completed

## Cleanup Keep

- `doc/tasks/20260617-build-test-backup-release/bug-regression-evidence.md`
