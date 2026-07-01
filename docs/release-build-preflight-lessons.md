# 构建发布耗时问题预防清单

## 适用范围

当任务涉及 IntRuoyi 运行控制台真实 E2E 构建发布包、发布到测试服、发布包候选验收或构建发布失败重试时，先读本文。

本文只沉淀可复用经验；正式发布规则仍以 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md` 和 `login-access.md` 为准。

如任务目标是让 Codex 直接照清单执行，请同时读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`。

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

7. 每次发布统一走临时发布 worktree。
   - “构建并发布到测试服务器”等所有发布命令，一律先创建本次专用的临时发布 `worktree`，禁止直接在主工作区执行构建、验证或发布。
   - 临时发布 `worktree` 必须检出本次发布目标提交；构建发布输入固定为该目标提交对应的 Git 已提交内容。
   - 主工作区未提交改动、未跟踪文件和脏工作区内容一律不得进入发布包；临时发布 `worktree` 的存在就是为了隔离这些内容。
   - 发布前必须分别核对维护仓、后端仓、前端仓主工作区当前分支名、目标提交与 dirty 状态，并显式记录本次临时发布 `worktree` 路径和目标提交。
   - 仅在构建前检查主工作区 clean 或目标提交还不够；`build-release` 成功后必须立即复核发布包 `manifest.json` 的 `sourceRepos`，确认 `branch`、`commit` 与本轮计划一致，且所有仓库 `dirty=false`。若 manifest 已记录 `dirty=true` 或 commit 漂移到非计划值，该发布包必须直接判废，不得继续 `publish-test`。

8. 临时发布 worktree 必须先过构建前置门禁。
   - 前端至少先过 `pnpm install --frozen-lockfile` 或等价依赖恢复。
   - 后端至少先过目标模块构建门禁，例如 `yudao-server` 或本次受影响模块。
   - 若临时发布 `worktree` 本身过不了锁文件、依赖或目标模块构建门禁，说明本次目标提交还不可发布；先把修复正式提交，再重建临时发布 `worktree`。

9. 发布失败优先做只读根因定位，不要手工改库绕过。
   - required SQL 在测试服失败时，先回查真实库状态、历史数据、主键占用和租户范围，再决定修复位置。
   - 禁止先手工改测试库、手工补菜单或手工改角色来“帮助发布过关”。
   - 这类问题要么回到 SQL 契约修复，要么回到发布脚本 / manifest / migration 门禁修复。

10. 测试服远端参数不能照搬备份服或正式服。
   - 测试服发布前，至少只读核对一次目标主机的真实数据盘挂载、release/data 目录和 MinIO 容器名；不要按备份服 `/mnt/intruoyi-data` 或 `intruoyi-minio` 经验直接覆盖测试服参数。
   - 2026-07-01 已验证：测试服 `172.30.30.58` 当前仍使用 `/var/lib/docker`、设备 `/dev/vdb`、MinIO 容器 `ragflow_compose-minio-1`；若维护控制台、脚本或文档漂移到其他参数，必须先修正契约再重新发起发布。

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

## 2026-06-24 发布前阻塞经验

- 真实出包前先在干净后端 HEAD 上独立执行迁移策略门禁；不要等运行控制台 build-release 后半段才暴露 SQL 元数据问题。
- `code-only`、`SkipDatabaseSync` 仍必须通过 `release-migration` 元数据门禁；缺失元数据表示发布契约不完整，不是可忽略的数据库同步事项。
- 当门禁 fail fast 只报首个 SQL 文件时，立即做只读全量扫描，记录完整缺失清单；本次缺失清单为 `sql/mysql/20260623_dcc_view_matrix_independent_source.sql`。
- 根工作区或业务源码工作区 dirty 时，必须分别创建维护控制台、后端、前端干净 HEAD worktree，并显式传入这些路径作为发布输入。
- 维护控制台完整构建依赖正式目标配置测试样本；`doc/tasks/20260620-prod-release-current-latest/prod-target-config.json` 必须进入已提交代码，否则 clean worktree 构建会失败。
- 正式干运行净化工作区必须包含发布包 `resources/` 证据目录；缺失 `resources/resource-reference-manifest.json` 会让正式预检无法证明资源引用清单，必须在 `RuntimeControlOriginalParityTest.promoteProdPreviewUsesSanitizedPackageWorkspace` 中保持门禁。
- Windows 深层 release worktree 可能让 PowerShell 5.1/.NET 在 `ReadAllText` 时误报资源文件不存在；正式 dry-run 的临时净化工作区必须使用短路径临时根，证据报告再写回 stateDir。
- 干净前端 worktree 创建后必须先执行 `pnpm install --frozen-lockfile` 或等价依赖恢复；否则运行控制台构建会在 Vite CLI 缺失处等待数分钟后失败。
- 不要默认勾选 Smart Release report-only；若启用，必须在构建前显式提供 baseline manifest、local database config、ownership registry 和 target config。缺少 `SmartReleaseBaselineManifestPath` 时应直接阻塞。
- 当前发布脚本 `changeSet.summary` 仅写默认 releaseTag，未提供显式变更说明参数；后续应增加 `-ChangeSummary` / `-ChangeItem` 并由运行控制台传入，减少发布后人工对照 sourceRepos 的成本。
- 运行控制台 release-status / release-packages 扫描 NAS 通常耗时约 9-10 秒；发布页面可增加缓存或分页，减少每次状态刷新等待。

## 2026-06-28 全链路发布收敛经验

- 真实发布必须沿单一 `releaseTag` 一次性走完 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；不要拼接多轮版本结果，也不要拿旧测试服成功 + 新正式服成功混成“本轮完成”。
- 发布失败优先按“契约层 -> 脚本层 -> 环境层”排查：先查 migration/manifest/required SQL/产物契约，再查维护仓发布脚本与业务仓产物是否一致，最后才查服务器状态；连 manifest 或迁移门禁都没过时，不要先怀疑服务器。
- SQL 要按“可发布”而不是“能执行”编写：`release-migration` 元数据、`dependsOn`、环境变量前置、tenant 上下文和动态菜单字面量规则都必须提前通过门禁或测试，不要等到页面 `build-release` 或 `promote-prod` 才暴露。
- 维护仓发布脚本必须和业务仓产物合同同步维护；后端 jar 命名、Docker build context、required SQL 排序、空集合处理、prod/backup 变量注入等，只要业务仓契约改了，维护仓脚本和测试必须一起改。
- 测试服不是形式流程，而是正式服唯一前置筛选器；正式服前至少要先在测试服确认：manifest 正确、`.env IMAGE_TAG` 正确、backend/frontend 镜像 tag 正确、health `UP`、前端 `200`、required SQL/operation 最终 `SUCCESS`。
- 正式服 / 备份服发布前必须先看预览参数，不允许靠默认值猜：至少逐项确认 `ServerHost`、`RemoteAppDir`、`RemoteReleaseRoot`、`RemoteDataRoot`、`RemoteDataDiskMount`、`RemoteDataDiskDevice`、`RemoteMinioContainer`、`RequireTested`、`ConfirmText=PROD`。
- 备份服固定要显式核对 `172.30.30.59`、`/mnt/intruoyi-data`、`/mnt/intruoyi-data/runtime-data`、`/mnt/intruoyi-data/intruoyi-releases`、`/dev/mapper/cl-home`、`intruoyi-minio`；任何继承正式服默认值或 Docker 根目录路径的情况都要 fail fast。
- 正式服问题必须拆成三类证据分别验证：脚本参数是否正确、SQL/迁移是否真实通过、环境前提是否满足。像 `/mnt/nas`、MinIO、数据盘、`.env IMAGE_TAG`、容器镜像和 Docker bind mount 都属于环境契约，不能把环境坏状态误判成业务代码回归。
- 发布成功判定必须同时看 operation、manifest、`.env`、运行镜像、health 和前端入口；只看 HTTP 200 或只看页面显示成功都不够。

## 2026-06-29 已提交版本发布收敛经验

- 发布口径已切换为“每次发布统一走临时发布 worktree，并且只发布目标提交对应的 Git 已提交内容”；不得再按“主工作区默认直发、dirty 时再询问方案”的旧规则执行。
- 发布前必须先核对测试服当前运行版本和本次目标提交差异；如果 manifest 中 commit 落后于本轮计划值，必须重新走真实 `build-release -> publish-test`，不能沿用旧结论。
- `build-release SUCCESS` 只代表打包流程完成，不代表发布输入仍然满足“只发布已提交版本”。如果构建期间主分支又出现未提交改动，manifest 会把对应仓库记为 `dirty=true`；此时即使 NAS 包已上传，也只能保留为排障证据，不能继续发测试服。
- `runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 必须显式切到最新干净 worktree；若仍指向旧 worktree，即使主仓已有新提交，真实 `build-release` 也不会包含这些提交。
- 前端 lockfile、pnpm build scripts 放行、后端测试依赖等“只在临时发布 worktree 才暴露”的问题，本质上都属于“目标提交还不可发布”；修复后要先最小提交，再重建临时发布 worktree，不能把主工作区未提交修复混进发布输入。
- required SQL 在测试服失败时，优先只读回查真实库状态确认是历史数据冲突、主键占用还是 tenant 范围问题；不要手工改测试库绕过门禁。

## 2026-06-30 主分支真实发布收敛经验

- 主分支发布不仅要在构建前检查三仓 clean，还要在 `build-release` 成功后立刻复核 `manifest.json` 的 `sourceRepos.branch/commit/dirty`；只要任一仓库为 `dirty=true`，该包直接判废，不得继续 `publish-test`。
- required SQL 要按“真实环境可重入、可重复发布”来写；像 `20260624_mes_schedule_issue_structured_backflow.sql` 这种重复加列报错的问题，必须补成幂等 SQL 与自动测试，不能靠“测试服当前只跑一次”侥幸通过。
- 菜单/权限 SQL 不能只改菜单树本身；若发布门禁依赖租户包或角色包，必须同步维护 `tenant package menu_ids` 等派生契约，否则会在测试服 required SQL 阶段才暴露。
- 发布后角色门禁必须兼容真实基线角色编码；如果环境里真实启用的是 `doc_control` 或 `wenkong_download`，就不能把 required SQL 硬写死成只认旧 `wenkong`。
- `publish-test` 长时间 `RUNNING` 不等于卡死；要同时看 operation log 是否持续推进到 NAS 下载、required SQL、容器重建、HTTP readiness、runtime smoke 和 `LOCK_RELEASED`。只有状态停滞且日志不再推进时，才按卡死方向排障。

## 本次证据

- 当前主分支测试服发布闭环任务：`doc/tasks/20260630-main-branch-build-publish-test-server/task.md`
- 当前主分支测试服发布闭环执行日志：`doc/tasks/20260630-main-branch-build-publish-test-server/execution-log.md`
- 任务文档：`doc/tasks/20260617-e2e-build-publish-test/task.md`
- 执行日志：`doc/tasks/20260617-e2e-build-publish-test/execution-log.md`
- 验收报告：`doc/tasks/20260617-e2e-build-publish-test/verification-report.md`
- 候选证据：`doc/tasks/20260617-release-experience-consolidation/candidate-error-evidence.md`
- 本轮新增证据：`doc/tasks/20260625-head-full-release/task.md`、`doc/tasks/20260625-head-full-release/execution-log.md`、`doc/tasks/20260628-release-flow-fupan/release-flow-fupan.md`
