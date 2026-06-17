# Candidate Error Prevention Evidence

- Generated At: 2026-06-17T18:03:01
- Project Root: D:\ProjectPackage\Int\IntRuoyiMaintance
- Source Files Scanned: 3
- Files With Matches: 3
- Context Lines: 1
- Keywords: 错误, 失败, 阻塞, 问题, 风险, 修复, 原因, 影响, 不得, 必须, 告警, 回归, fail, failed, error, blocked, root cause, regression, risk, must, should not, do not

Review these snippets before writing any durable project rule.

## doc/tasks/20260617-e2e-build-publish-test/execution-log.md

### Match 1 (lines 4-6)

```text
- `BDD: 真实 E2E 构建发布到测试服 -> Given 本机运行控制台可访问且目标为测试服 172.30.30.58, When 操作者通过前端预览并执行 code-only 构建发布包后再执行发布到测试服, Then 构建和发布 operation 均成功，发布包 manifest 与远端 IMAGE_TAG 一致，测试服后端健康且管理前端真实路径可访问。`
- `BDD: 禁止越界环境 -> Given 本次任务只授权测试服, When 执行构建、发布和验证, Then 不得提交 targetEnvironment=prod，不得访问 172.30.30.57 或 172.30.30.59，不得执行备份、恢复、回滚或正式服动作。`
- 前置读取：`docs/experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`。
```

### Match 2 (lines 8-10)

```text
- 授权记录：用户当前任务明确要求发布到测试服务器；本任务服务器动作仅限测试服 `172.30.30.58` 和远端目录 `/opt/intruoyi/runtime`。
- 范围记录：沿用当前发布基线和上次用户要求，构建发布范围为 `code-only`，不得同步数据库或 MinIO/NAS 业务数据。
- `GREEN: experience-preflight -> PASS`，已读取发布/服务器/登录门禁；本任务只授权测试服 `172.30.30.58`，目标目录 `/opt/intruoyi/runtime`，发布范围 `code-only`；禁止正式服 `172.30.30.57`、备用服 `172.30.30.59`、备份、恢复、回滚、正式发布和数据同步。
```

### Match 3 (lines 19-22)

```text
- `GREEN: build-release-submit -> PASS，Playwright 点击预览弹窗“执行”，后端返回 operationId=op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef，初始状态 RUNNING。`
- `RED: build-release-operation -> FAIL，operationId=op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef 最终状态 FAILED；后端 Maven 打包、前端 Vite build、后端 Docker 镜像构建均已完成，前端 Docker 镜像构建在拉取 nginx:1.27-alpine 元数据时失败。`
- `BLOCKER: docker-nginx-base-image -> docker build 失败：failed to fetch anonymous token for docker.io/library/nginx:1.27-alpine，dial tcp 199.59.149.136:443 connect timeout。发布包未成功生成，不得进入测试服发布。`
- `GREEN: docker-nginx-base-image -> PASS，docker pull nginx:1.27-alpine 成功，digest=sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10。`
```

### Match 4 (lines 24-32)

```text
- `GREEN: build-release-submit-retry -> PASS，Playwright 点击预览弹窗“执行”，后端返回 operationId=op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300，初始状态 RUNNING。`
- `RED: build-release-operation-retry -> FAIL，operationId=op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300 最终状态 FAILED；Maven 打包、Vite build、后端镜像和前端镜像均成功，发布迁移策略门禁失败。`
- `BLOCKER: migration-policy-gate -> dependsOn missing migration '20260513_dcc_base_schema.sql' for migrationId '20260617_dcc_browser_performance_indexes'。发布包未生成 manifest，禁止继续发布测试服。`
- `GREEN: migration-policy-gate-fix -> PASS，在 ruoyi-vue-pro 中修正 sql/mysql/20260617_dcc_browser_performance_indexes.sql 的 dependsOn 元数据为 20260513_dcc_base_schema；重新运行 script/release/run-release-migration-policy-gate.py 通过，migrationCount=147。`
- `GREEN: database-schema-evidence -> PASS，运行 database-schema-delivery validate_database_schema.py 校验迁移修复证据通过。`
- `GREEN: build-preview-scope-third -> PASS，Playwright 使用新 releaseTag=release-20260617-1627-codeonly-e2e 重新预览构建命令；命令包含 -Mode build-release、-Component intruoyi、-SkipDatabaseSync、-SkipMinioSync、-TestServerHost 172.30.30.58；未包含 172.30.30.57、promote-prod、backup-now、rollback、restore-data。`
- `GREEN: build-release-submit-third -> PASS，Playwright 点击预览弹窗“执行”，后端返回 operationId=op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73，初始状态 RUNNING。`
- `RED: build-release-operation-third -> FAIL，operationId=op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73 最终状态 FAILED；Maven clean 在 yudao-module-dcc 删除 target 目录失败。发布包未生成，禁止继续发布测试服。`
- `GREEN: dcc-target-clean-precondition -> PASS，单独运行 mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean 通过，DCC target 清理前置恢复。`
```

### Match 5 (lines 34-36)

```text
- `GREEN: build-release-submit-fourth -> PASS，Playwright 点击预览弹窗“执行”，后端返回 operationId=op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990，初始状态 RUNNING。`
- `RED: build-release-operation-fourth -> FAIL，operationId=op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990 最终状态 FAILED；Maven 打包、Vite build 和后端 Docker 镜像成功，前端 Docker 镜像在解析 nginx:1.27-alpine 元数据时 Docker Hub 返回 EOF。发布包未生成，禁止继续发布测试服。`
- `GREEN: docker-nginx-base-image-retry -> PASS，docker pull nginx:1.27-alpine 成功，digest=sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10，本地 docker image inspect 通过。`
```

### Match 6 (lines 38-42)

```text
- `GREEN: build-release-submit-fifth -> PASS，Playwright 点击预览弹窗“执行”，后端返回 operationId=op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a，初始状态 RUNNING。`
- `RED: build-release-operation-fifth -> FAIL，operationId=op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a 最终状态 FAILED；发布脚本在 Maven clean 前检测到本机 Java 进程锁定 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\target\yudao-server.jar。发布包未生成，禁止继续发布测试服。`
- `BLOCKER: local-backend-jar-lock -> 需要先释放本机占用 yudao-server.jar 的 Java 进程，脚本已明确建议重启本机后端让其运行在复制出来的 runtime jar 上。`
- `GREEN: local-backend-runtime-restart-attempt -> PASS，本机 restart-ruoyi-backend.bat 已切换后端到 E:\Int\CacheData\IntRuoyi\runtime\backend-20260617-164706.jar；虽然应用因定时任务同步失败退出，但 target\yudao-server.jar 锁已解除。`
- `GREEN: local-yudao-server-clean-after-restart -> PASS，mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean 通过，确认 jar 锁前置已恢复。`
```

### Match 7 (lines 52-54)

```text
- `GREEN: remote-migration-status -> PASS，测试服 infra_release_migration 中 migration_id=20260617_dcc_browser_performance_indexes 的最新 status=APPLIED。`
- `GREEN: remote-playwright-entry -> PASS，Playwright 打开 http://172.30.30.58:8081/ 返回 HTTP 200 并跳转到 /login?redirect=/index；页面标题“瑛泰管理系统 - 登录”，页面文案包含“瑛泰数字化平台”“登录”，console error 为 0。`
- `INFO: remote-login-scope -> login-access.md 未提供远端测试服可用账号；本任务未冒用本机测试租户密码登录远端，仅验证测试服真实前端入口可达并加载登录页。`
```

### Match 8 (lines 56-57)

```text
- `GREEN: task-closeout-cleanup-apply -> PASS，为释放临时日志文件锁，停止本任务启动的本机维护控制台 127.0.0.1:48181 后执行 apply，成功删除两个临时日志；未清理测试服或发布产物。`
- `GREEN: independent-verification-gate -> PASS，现时复验 curl 后端健康 HTTP 200、前端 HTTP 200、测试服 IMAGE_TAG 与前后端镜像均为 release-20260617-1654-codeonly-e2e、迁移 20260617_dcc_browser_performance_indexes 为 APPLIED、Playwright 真实浏览器打开测试服登录页且 console error 为 0。`
```
## doc/tasks/20260617-e2e-build-publish-test/task.md

### Match 1 (lines 18-23)

```text

- `docs/experience-index.md`：涉及发布、服务器写入和真实 E2E，执行高风险动作前必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台前端按钮提交；提交前必须预览命令并确认 `code-only`、`-SkipDatabaseSync`、`-SkipMinioSync`、目标环境和禁止正式服动作；发布成功必须以 operation、manifest、远端 `.env`/镜像 tag 和健康检查共同证明。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：本次用户已明确授权测试服发布；服务器动作仅限 `172.30.30.58` 和 `/opt/intruoyi/runtime`，不得写入凭据，优先使用仓库封装脚本/运行控制台。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：真实 E2E 前先验证登录或运行控制台入口；测试服验证使用真实前端路径，登录失败必须报告实际入口、租户、账号和影响。

```

### Match 2 (lines 25-27)

```text

- `是否引入 fallback/降级/吞异常`：否。缺少运行控制台、发布包 manifest、测试服访问、登录凭据或验证证据时直接阻塞。
- `是否从根因和长期维护角度解决`：是。通过既有运行控制台前端路径提交构建和发布 operation，以 manifest、operation、远端状态和真实页面验证闭环。
```

### Match 3 (lines 32-34)

```text
- `BDD: 真实 E2E 构建发布到测试服 -> Given 本机运行控制台可访问且目标为测试服 172.30.30.58, When 操作者通过前端预览并执行 code-only 构建发布包后再执行发布到测试服, Then 构建和发布 operation 均成功，发布包 manifest 与远端 IMAGE_TAG 一致，测试服后端健康且管理前端真实路径可访问。`
- `BDD: 禁止越界环境 -> Given 本次任务只授权测试服, When 执行构建、发布和验证, Then 不得提交 targetEnvironment=prod，不得访问 172.30.30.57 或 172.30.30.59，不得执行备份、恢复、回滚或正式服动作。`

```
## doc/tasks/20260617-e2e-build-publish-test/verification-report.md

### Match 1 (lines 28-32)

```text
| 管理前端可访问 | `curl.exe -s -o NUL -w "%{http_code}" http://172.30.30.58:8081/` 返回 `200` | PASS |
| 真实浏览器入口可用 | Playwright Chromium 打开 `http://172.30.30.58:8081/`，`responseStatus=200`，跳转到 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，包含“瑛泰数字化平台”和“登录”，console error 为 0 | PASS |
| 发布迁移已应用 | SSH 测试服查询 `infra_release_migration` 返回 `20260617_dcc_browser_performance_indexes APPLIED` | PASS |
| 发布前迁移依赖问题已闭环 | 原后端仓库提交 `c6b549c3e7 任务: 修复DCC浏览索引迁移依赖`；迁移策略门禁与 `script/tests/test_release_migration_policy_gate.py` 均通过 | PASS |
| 正式服/备用服/备份恢复回滚未越界 | 构建和部署预览日志记录未包含 `172.30.30.57`、`promote-prod`、`backup-now`、`rollback`、`restore-data`；本次现时验证仅访问测试服 `172.30.30.58` | PASS |
```

### Match 2 (lines 40-47)

```text
- 迁移状态查询 -> `20260617_dcc_browser_performance_indexes APPLIED`
- Playwright 浏览器验证 -> `responseStatus=200`，`finalUrl=http://172.30.30.58:8081/login?redirect=/index`，`consoleErrorCount=0`

## 边界与残余风险

- 未执行远端测试服登录。原因：`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md` 未提供远端测试服可用账号，且明确要求缺少凭据时不得静默切换账号或环境。本次以真实浏览器验证测试服管理前端入口可达并加载登录页。
- 后端仓库仍存在与本任务无关的既有未提交改动和 runtime 临时文件；本次提交只包含构建发布闭环所需的迁移依赖修复与证据。
- 维护仓库仍有未跟踪 `.codex/` 目录；该目录不是本任务产物，未纳入提交。
```
