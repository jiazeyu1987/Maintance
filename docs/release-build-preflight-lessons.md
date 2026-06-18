# 构建发布耗时问题预防清单

## 适用范围

当任务涉及 IntRuoyi 运行控制台真实 E2E 构建发布包、发布到测试服、发布包候选验收或构建发布失败重试时，先读本文。

本文只沉淀可复用经验；正式发布规则仍以 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md` 和 `login-access.md` 为准。

## 通用发布验证基线

适用场景：任何功能修改、配置修改、脚本修改、菜单/权限调整、构建发布包和部署服务器。

### 六条通用规则

1. 唯一发布源头：所有发布链路只认一个维护仓发布入口和产物来源，本机源码通过不等于发布已通过。
2. 配置必须代码化：发布相关的环境变量、路径、参数、菜单权限、脚本和构建开关优先写入仓库和发布脚本，不把服务器手工改动当最终方案。
3. 验证发布产物：每次构建都要检查发布包、manifest、打包内容和关键文件是否与本次变更一致，不能只看编译成功。
4. 环境差异显式检查：本机、构建机、测试服、备份服、正式服的镜像 tag、目录、挂载、数据库和账号基线都要明确核对，不能默认一致。
5. 目标环境真实运行态：到服务器必须看真实运行中的镜像、进程、健康、页面和权限响应，不能只验健康检查或接口单点。
6. 故障补成门禁：凡是本机正常、服务器失败、发布后暴露、或构建后才发现的问题，都要补成 preflight、测试或脚本门禁，不能只修一次就结束。

### 分阶段验证强度

- 功能修改阶段：先确认修改会进入正确的发布源头和打包范围。
- 构建发布包阶段：确认产物、manifest、依赖和配置在包内完整且一致。
- 部署服务器阶段：确认真实运行态、真实权限、真实页面和真实数据路径。
- 线上或测试服暴露的问题：必须回写到门禁或经验，不要停留在口头提醒。

## 发布前必做预检

1. 先确认运行控制台是当前版本。
   - 本机控制台入口：`http://127.0.0.1:48181/`。
   - 如果刚改过维护控制台后端或发布脚本，必须重新构建并重启控制台，再用实际接口或页面确认候选列表、预览命令和门禁行为已生效。
   - 不要把“代码已编译”当作“当前 48181 进程已加载新逻辑”。

2. 先预拉 Docker 基础镜像。
   - 构建前扫描 Dockerfile 中的 `FROM`：
     `rg -n "^FROM " D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 -g Dockerfile*`
   - 对每个基础镜像执行 `docker pull <image>` 和 `docker image inspect <image>`。
   - 本次已证明 `nginx:1.27-alpine` 拉取超时或 EOF 会让前端镜像构建在后半程失败，必须在真实 E2E 提交前提前发现。

3. 先跑迁移策略门禁。
   - 后端仓库执行：
     `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`
   - `release-migration dependsOn` 必须写 migrationId，即 SQL 文件名 stem，不带 `.sql` 后缀。
   - `code-only` 和 `-SkipDatabaseSync` 只表示不做数据同步，不表示跳过 schema、required SQL、迁移元数据或发布 manifest 门禁。

4. 先释放 Maven target 和 jar 锁。
   - 构建前至少验证：
     `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean`
     `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean`
   - 如果 `yudao-server\target\yudao-server.jar` 被 Java 进程占用，先让本机后端运行在复制出的 runtime jar 上，释放 target jar 后再构建。
   - 不要在 target jar 被锁时反复点构建按钮。

5. 先验证真实 E2E 预览边界。
   - 构建预览必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`。
   - 测试服部署预览必须包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`。
   - 预览命令不得包含 `172.30.30.57`、`promote-prod`、`backup-now`、`rollback`、`restore-data`。

6. 先确认提交门禁再提交修复。
   - 如果修改 `sql/mysql` 或 `script`，提交前跑：
     `python -X utf8 tool\verify_tdd_compliance.py --task-dir <task-dir>`
   - `execution-log.md` 需要裸 `RED:` / `GREEN:` 证据行；不要只把证据包在反引号里。
   - `sql/mysql` 变更必须配 `script/tests` 下的测试，否则后端仓库 pre-commit 会阻止提交。

## 发布完成判定

不得只用健康检查判断发布完成。至少同时具备：

- 构建 operation `SUCCESS`，记录 operation ID、状态和日志路径。
- 发布 operation `SUCCESS`，记录 operation ID、状态和日志路径。
- 发布包 manifest 存在，且 `releaseTag`、`component`、`publishScope` 与本次目标一致。
- 测试服 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG=<releaseTag>`。
- `docker compose ps` 中 `intruoyi-backend` 和 `intruoyi-frontend` 镜像 tag 与 `releaseTag` 一致且 running。
- 后端健康检查 HTTP 200 且返回 `UP`。
- 管理前端 HTTP 200，并用 Playwright 真实浏览器打开入口，确认登录页加载且 console error 为 0。
- 本次 required SQL 或迁移在测试服状态为 `APPLIED`。

## 重试规则

- 每次修复前置条件后使用新的 `releaseTag` 重跑构建，失败的半成品只能作为排障证据，不得作为候选发布包。
- 本地 Docker image、缓存目录、旧 `release-manifest.json` 都不能替代 Manifest v1 或 NAS 发布包证据。
- operation 长时间失败或 failed 时先读 operation JSON、result log、脚本进程和产物状态，不要仅凭页面或健康检查继续下一步。

## 本次证据

- 任务文档：`doc/tasks/20260617-e2e-build-publish-test/task.md`
- 执行日志：`doc/tasks/20260617-e2e-build-publish-test/execution-log.md`
- 验收报告：`doc/tasks/20260617-e2e-build-publish-test/verification-report.md`
- 候选证据：`doc/tasks/20260617-release-experience-consolidation/candidate-error-evidence.md`
