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

## 2026-07-01 三环境发布前置门禁沉淀

- 每轮完整发布必须从同一个 `releaseTag` 开始闭环；修复任意 blocker 后必须重新 `build-release` 得到新的 `releaseTag`，不得把旧失败包、旧测试服成功结果和新正式服/备份服结果拼成一次完成记录。
- 发布输入门禁必须前后各查一次：构建前确认维护仓、后端仓、前端仓目标提交与临时发布 worktree；构建后立即读取 manifest，确认 backend/frontend `commit` 是本轮计划值且 `dirty=false`。任一 dirty、commit 漂移或 manifest 缺失时，该包只能作为排障证据。
- `publish-test` 失败先按真实日志分层定位：manifest / required SQL / migration / 脚本契约优先，其次才查 SSH、Docker、磁盘、MinIO 等环境问题；不要先假设测试服坏。
- 测试服参数必须按 `server-access.md` 的真实基线预检，不能套用正式服或备份服口径。测试服当前已确认基线包括 `/var/lib/docker`、`/dev/vdb`、`ragflow_compose-minio-1`、`/opt/intruoyi/runtime`；预览参数不一致必须先修脚本或配置后再发布。
- required SQL 必须按“真实库可重复发布”设计：`ADD COLUMN`、菜单插入、角色绑定、租户包写入、数据准备和 DCC 分类修复都必须具备幂等保护、依赖声明和真实库前置校验；不能依赖测试库当前只执行一次。
- 角色、菜单、租户基线不能凭历史记忆硬编码。发布前若 SQL 依赖关键角色或菜单，必须只读核验真实库中角色编码、启用状态、菜单 ID、租户绑定和账号归属；例如旧 `wenkong` 与真实 `doc_control` / `wenkong_download` 漂移必须在 SQL 契约中兼容或明确阻塞。
- DCC 数据质量要前移为 promote 前预检：正式服或测试服 live data 中的分类重复、编码缺失、字段长度超限、必填关系缺失，都应在 promote 前通过只读 SQL 检出；发现数据不满足契约时阻塞并修根因，不手工绕过。
- 测试服成功不等于完整发布成功；继续正式服和备份服前必须先完成 `mark-tested`，并在每个环境分别核 operation、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health、frontend HTTP。
- 运行控制台在 `build-release`、`publish-test`、`mark-tested`、`promote-prod`、`promote-backup` 完成后，会自动把发布经验候选追加到 `runtime/runtime-control/release-experience-candidates.md`；任务收口时必须读取该候选文件，把可复用项正式前移到本文或 `release-agent-checklist.md`。
- 自动经验候选生成是发布闭环的一部分；如果候选文件无法写入，operation 必须 fail fast，不允许静默跳过经验沉淀。

## 2026-07-03 不带数据测试服发布前置门禁

- `code-only` / `-SkipDatabaseSync` / `-SkipMinioSync` 只表示不同步业务数据和文件，不表示跳过 schema、required SQL、migration 或约束变更；构建成功后仍必须按真实库执行 required SQL 并检查迁移结果。
- DCC 分类 `lifecycle_stage` 迁移在执行 `ALTER ... NOT NULL` 前必须做全表非空门禁，不能只校验 `deleted=0` 活动行；`deleted=1` 的历史归档行同样会阻塞 `NOT NULL` 约束变更。
- DCC 历史分类补值必须按根因写进可重复执行的 SQL 和测试：活动行按确认的业务阶段映射，已删除历史行必须有明确归档归一化规则和注释；禁止手工改测试库来让发布过关。
- required SQL 如果报 `Invalid use of NULL value`，优先只读查询目标字段全表空值分布，例如按 `deleted` 分组统计，再定位是活动数据未映射、归档历史行未归一化，还是字段约束顺序错误。
- 测试服业务库名以真实容器查询为准；当前测试服 MySQL 容器内业务库为 `ruoyi-vue-pro`，不要默认写成 `yudao_ruoyi`。
- 远端 MySQL 查询容器内环境变量时，不要让本地 PowerShell 或远端宿主机提前展开 `$MYSQL_ROOT_PASSWORD`；优先用 `docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro'` 并通过标准输入传 SQL。
- 跨 PowerShell、SSH、sh、mysql 多层引号失败时，不要继续堆嵌套转义；改用标准输入、临时脚本或 here-doc，并显式记录 `$LASTEXITCODE`，避免把查询失败误判成数据库无数据。
- 修改 `runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 时必须写后校验 YAML 缩进、实际路径和 `http://127.0.0.1:48181/actuator/health`；配置指向临时 worktree 后，收尾前必须恢复到稳定主路径或确认该 worktree 不会被删除。
- 运行控制台启动入口以维护仓当前脚本为准；本轮确认应使用 `scripts\start.ps1`，不要凭旧路径猜测 `ops\runtime-control\start-runtime-control.ps1`。
- 不带数据发布的 manifest 必须显式验证 `publishScope=code-only`，并确认发布包中不存在 `database`、`mysql`、`minio`、`files` 等数据目录；仅看到 operation `SUCCESS` 不足以证明“不带数据”。

## 本次证据

- 当前主分支测试服发布闭环任务：`doc/tasks/20260630-main-branch-build-publish-test-server/task.md`
- 当前主分支测试服发布闭环执行日志：`doc/tasks/20260630-main-branch-build-publish-test-server/execution-log.md`
- 任务文档：`doc/tasks/20260617-e2e-build-publish-test/task.md`
- 执行日志：`doc/tasks/20260617-e2e-build-publish-test/execution-log.md`
- 验收报告：`doc/tasks/20260617-e2e-build-publish-test/verification-report.md`
- 候选证据：`doc/tasks/20260617-release-experience-consolidation/candidate-error-evidence.md`
- 本轮新增证据：`doc/tasks/20260625-head-full-release/task.md`、`doc/tasks/20260625-head-full-release/execution-log.md`、`doc/tasks/20260628-release-flow-fupan/release-flow-fupan.md`
- 不带数据测试服发布证据：`doc/tasks/20260702-build-publish-test-nodata-evening/task.md`、`doc/tasks/20260702-build-publish-test-nodata-evening/execution-log.md`
- 前置经验沉淀证据：`doc/tasks/20260703-release-preflight-experience-nodata-dcc/task.md`、`doc/tasks/20260703-release-preflight-experience-nodata-dcc/execution-log.md`

## 2026-07-03 维护控制台临时 worktree 构建前置

- 新建维护仓临时发布 worktree 后，`frontend/node_modules` 不存在或由 pnpm 11 首次恢复时，必须先在维护仓 `frontend` 目录执行 `pnpm approve-builds --all`，确认 `esbuild`、`vue-demi` 等前端构建脚本被显式允许，再执行 `scripts/build.ps1`。
- 若出现 `ERR_PNPM_IGNORED_BUILDS`，不得跳过前端构建、不得复用主工作区 `dist` 或旧 jar；先冻结失败证据，再补齐 approve-builds 前置条件并重跑完整维护控制台构建。
- 运行控制台切换到 release worktree 前，必须确认 48181 归属；旧主工作区进程停止后若构建失败，记录 48181 无监听影响，补齐前置条件后再启动 release worktree 控制台。

### 2026-07-04 pnpm approve-builds 空结果仍可能阻断 install

- 在干净维护仓 release worktree 中，`pnpm approve-builds --all` 可能返回 "There are no packages awaiting approval"，但随后的 `pnpm install --frozen-lockfile` 仍因 `ERR_PNPM_IGNORED_BUILDS` 阻断 `esbuild`、`vue-demi`。
- 前置门禁不能只看 `approve-builds --all` 退出码；必须紧接着执行一次 `pnpm --dir <maintenance-worktree>\frontend install --frozen-lockfile`，并以该命令真实通过作为 frontend build scripts approval 证据。
- 若 install 仍报 `ERR_PNPM_IGNORED_BUILDS`，必须先冻结 stdout/stderr，再查 pnpm approval state、ignored builds 清单和 workspace 配置；不得复用主工作区 `node_modules`、`dist` 或旧 jar。
## 2026-07-03 mark-release-tested 必须携带 recovery set 候选

- 触发条件：code-only 发布在测试服验证通过后执行 mark-release-tested。
- 失败现象：预览接口返回 `selectedRecoverySetCandidateId is required for action: mark-release-tested`。
- 前置门禁：mark-tested 前必须从当前 releaseTag/测试服发布结果对应的真实候选来源取得 `selectedRecoverySetCandidateId`，不得省略、不得手工标绿。
- 处理要求：冻结预览失败证据，补齐真实候选 ID 后重新预览并执行 mark-tested。

## 2026-07-05 release-migration dependsOn 必须引用真实 migrationId

- 触发条件：构建前执行 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`。
- 失败现象：`dependsOn missing migration '20260519_showroom_v1_schema' for migrationId '20260704_showroom_product_target_market_text'`。
- 前置门禁：新增 SQL 的 `dependsOn` 必须引用 `sql\mysql` 中真实存在的 SQL 文件 stem / migrationId；不得凭表名、历史记忆或业务模块名称编造依赖。
- 处理要求：先冻结门禁失败 JSON 和目标 SQL 首行，再只读列出同域 SQL 的 release-migration 元数据，确认最小真实依赖后修复 SQL 元数据；修复后必须重跑 migration policy gate，生成新提交后重建 release worktree，不得把临时 worktree 未提交修复混入发布包。

## 2026-07-04 正式服验证必须读取 docker compose 端口映射

- 触发条件：promote-prod 后执行远端健康检查。
- 失败现象：直接访问宿主 `127.0.0.1:48080` 和 `127.0.0.1:80` 返回拒绝连接，但 `docker compose ps` 显示正式服实际映射为 `48081->48080`、`8081->80`，容器内服务已正常启动。
- 前置门禁：正式服/备份服验收不得硬编码宿主端口；必须先以 `docker compose ps` 或发布配置为准确认宿主端口，再验证 backend health、frontend HTTP 和 PDF worker。
- 处理要求：先冻结错误端口的失败证据，再使用真实端口重验；不得把端口映射差异误判为发布失败。

## 2026-07-05 发布 manifest sourceRepos 校验入口
- 现象：code-only build 成功后，`release-manifest.json` 只记录兼容概要字段（例如 `gitCommit`），不承载完整 `sourceRepos`；若用它校验前后端 commit，会误判“前端 commit 缺失”。
- 前置门禁：构建后必须以发布包根目录的 `manifest.json` 作为完整契约入口，校验 `publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、`releaseTag` 与包目录一致；`release-manifest.json` 只用于兼容概要存在性/摘要校验。
- 失败处理：若 `manifest.json` 缺失或 `sourceRepos` 不完整，发布包判废并重新构建；不得用 `release-manifest.json` 或运行日志手工补齐字段后继续发布。

## 2026-07-05 deploy action preview 参数契约
- 现象：对 `publish-test` 这类部署动作发送 `publishScope/includeOnlyOffice/includeShowroomBuildPackage` 会触发接口参数校验失败（例如 `msg=publishScope`），预览不会返回部署命令。
- 前置门禁：`build-release` 使用 `publishScope=code-only`、`SkipDatabaseSync`、`SkipMinioSync`；后续 `publish-test/promote-prod/promote-backup` 必须复用已构建 releaseTag，只发送部署动作必需字段：`action`、`reason`、`releaseTag`、`targetEnvironment`，生产级动作再加 `prodConfirmText=PROD`。
- 失败处理：预览返回 4xx 时不得执行 action；冻结 preview JSON，修正参数契约并重新预览，确认命令包含 `-Mode deploy-release`、目标环境、目标主机与 releaseTag 后再执行。

## 2026-07-06 Windows 发布 worktree 长路径门禁

- 触发场景：构建发布前为维护仓、后端仓、前端仓创建本轮专用 release worktree。
- 失败现象：使用完整任务 ID 和完整仓库名组成深层 worktree 路径时，维护仓 checkout 历史 evidence 或构建产物路径可能触发 `Filename too long` 和 `fatal: Could not reset index file to revision 'HEAD'`，导致维护仓未完成检出而后端/前端已部分创建。
- 前置门禁：发布 worktree 根路径必须采用短目录名，例如 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce`；三仓子目录使用短名 `m`、`b`、`f`，并在任务文档记录短路径与完整 taskId 的映射。
- 处理要求：一旦发生长路径失败，先冻结 git 输出、failure JSON、三仓 `git worktree list --porcelain` 和残留目录清单；只清理本次失败路径下的部分 worktree，执行 `git worktree prune`，再用短路径重建并确认三仓 `dirty=false` 后才能继续构建或发布。

## 2026-07-06 build-release 目标主机参数必须一次性显式传齐

- 触发场景：code-only `build-release` 生成测试服和备份服 runtime env / 包 URL / 存储检查配置。
- 失败现象：仅传 `-TestServerHost` 时脚本返回 [FAIL] Missing -BackupServerHost; release target host for environment 'backup' must be configured and passed explicitly so package URLs and storage checks are bound to the selected publish target.
- 前置门禁：`build-release` 即使尚未部署备份服，也必须显式传入 `-TestServerHost 172.30.30.58` 与 `-BackupServerHost 172.30.30.59`；涉及三环境闭环时同时传入 `-ProdServerHost 172.30.30.57`，避免后续 runtime env 和发布目标不一致。
- 处理要求：缺少目标主机参数时先冻结 stdout/stderr/preflight/summary；不得复用失败 releaseTag，补齐主机参数后用新的 releaseTag 重新构建。
## 2026-07-06 publish-int-ruoyi NasConfigPath 必须是 NAS JSON

- 触发场景：直接调用 ops/deploy/publish-int-ruoyi.ps1 执行 build-release、deploy-release、mark-tested 或 promote 动作。
- 失败现象：将 config/runtime-control.local.yaml 传给 -NasConfigPath 时，脚本在 Read-NasReleaseConfig 中按 JSON 解析并报 ConvertFrom-Json: Invalid JSON primitive: maintenance，构建已完成但 operation 失败，releaseTag 必须判废。
- 前置门禁：-NasConfigPath 必须指向 runtime/runtime-control/nas-release-config/*.json 形态的 NAS 发布配置，且包含 server、share、username、password 四个字段；runtime-control.local.yaml 只用于运行控制台配置，不可直接作为发布脚本 NasConfigPath。
- 处理要求：先冻结 stdout/stderr/preflight/summary 和半成品发布包快照；补齐 NAS JSON 后使用新的 releaseTag 重建，不得继续使用失败 releaseTag。
## 2026-07-06 required SQL 菜单硬编码 ID 必须先查真实占用

- 触发场景：code-only deploy-release 执行 required SQL，SQL 需要新增 system_menu 按钮、权限或租户菜单绑定。
- 失败现象：SQL 硬编码菜单 ID（例如 900301/900302）在目标库已被其他权限占用，触发 SIGNAL 并导致 deploy-release 失败，operation lock 标记 FAILED。
- 前置门禁：required SQL 涉及 system_menu.id、permission、parent_id、system_role_menu 或 system_tenant_package_menu 时，构建/发布前必须只读核验目标环境真实占用；硬编码 ID 必须证明未占用或与同一业务权限完全一致。若目标库存在漂移，必须修正 SQL 为可重复、可审计、不会覆盖其他权限的根因方案后重新构建 releaseTag。
- 处理要求：先冻结 operation stdout/stderr、目标 SQL、远端 system_menu 占用查询、infra_release_migration/operation_lock 状态；不得手工删除/改写目标库权限来绕过门禁。

## 2026-07-06 mark-tested 本地启动参数引号门禁

- 触发场景：使用 Start-Process -ArgumentList 数组启动 PowerShell 脚本时，如果 -TestConclusion 等自由文本参数包含空格或中文标点，子进程命令行可能被重新拆词，后续词会被误绑定到位置参数，例如 Component，导致 ValidateSet 失败。
- 前置门禁：发布脚本参数中凡包含空格、中文说明、括号或其它自由文本时，优先使用无空格的结论文本，或生成临时 .ps1 包装脚本并在包装脚本内用 call operator 传参；不得直接依赖 Start-Process -ArgumentList 自动保留复杂字符串边界。
- 证据要求：若发生此类失败，必须冻结 stdout/stderr 与参数摘要，记录实际失败参数名和被误绑定值后再重试。

## 2026-07-08 排序类 code-only 正式发布经验

- 产品列表、管理列表、排序规则这类看似纯后端逻辑的 code-only 发布，仍必须按完整发布闭环执行：干净发布输入 `build-release`、测试服 `publish-test`、`mark-release-tested`、正式服 `promote-prod`，不得因为“不改数据”跳过测试服或 mark-tested。
- 如果主工作区存在无关 dirty SQL、草稿脚本或其它模块改动，必须使用临时干净后端/前端 release worktree 出包，并在构建预览中确认 `repo-root` / `frontend-root` 指向该干净路径；发布完成后必须恢复 `runtime-control.local.yaml` 到稳定主路径。
- 构建或发布过程中 required SQL 暴露的 `release-migration` 元数据、`dependsOn`、collation 或可重复执行问题，即使不是本次业务目标，也属于发布契约阻塞；修复后必须提交、重建 releaseTag、重新 `publish-test`，不能复用失败包继续 promote。
- 测试服页面 E2E 如果被账号密码或租户数据为空阻塞，应把阻塞原因写入执行日志，并改用可重复的只读证据补强：运行镜像 tag、健康检查、真实库目标租户数据分布、目标排序 SQL 查询结果；不得把空测试租户页面当成业务通过证据。
- 正式服发布完成后，排序类需求不能只验证 HTTP 200；至少核验 backend/frontend 镜像 tag、backend health、frontend HTTP、目标租户记录数量、排序字段非空数量、按新排序规则查询的首批记录和空排序字段尾部规则。
- 只读数据库核验应打印目标环境、目标租户、主键、当前编号和排序字段，避免把测试租户或其它租户的同码数据误当成正式租户结果。
- 运行控制台预览参数中若出现 `ProdDryRunEvidencePath`、`RequireTested`、`ConfirmText=PROD`、正式服 host/data disk/release root 等关键项，执行前必须逐项确认；缺一项即阻塞。

## 2026-07-09 测试服 HEAD 发布前置经验（任务 20260709-head-test-server-release）

### 发布前必查项

- 构建来源必须固定为当前分支 HEAD 已提交内容：记录维护仓、后端仓、前端仓当前分支、HEAD、`git status --short`；工作区脏时必须创建干净临时 worktree，或用可复核命令证明构建只读取 HEAD。
- 发布 worktree 必须记录路径、目标提交、是否产生新提交、是否已合回主工作区、最终删除结果；一次发布只允许使用单一 `releaseTag` 的闭环结果。
- Node/pnpm 必须与 `packageManager` 声明一致；本次维护控制台前端需要 `corepack pnpm@10.25.0`，发现 pnpm 11 生成的 `pnpm-workspace.yaml` 或 `ERR_PNPM_IGNORED_BUILDS` 必须 fail fast 并清理后重装。
- 后端 SQL 发布前必须跑 release migration metadata gate；SQL metadata 必须包含并符合 `allowedEnvironments`、`dependsOn`、`type`、`riskLevel` 等契约，禁止构建阶段才发现格式错误。
- build-release 预检必须区分“构建配置包含 BackupServerHost”和“执行备份服发布动作”；不得因配置字段存在误判为备份发布。
- Smart Release report-only 模式必须显式提供 baseline manifest、candidate manifest 和 smart-release config；缺任一输入必须 fail fast，不得继续构建不可确认来源的包。

### 可自动化项

- 自动检查三仓 HEAD、dirty 状态、releaseTag、manifest sourceRepos、dirty=false、changeSet、package 路径、tar 大小和 NAS 归档一致性。
- 自动检查测试服远端磁盘、inode、目标 releaseTag 目录是否存在同名残留、远端 `.env IMAGE_TAG`、镜像 tag、容器状态、后端 health、前端 HTTP 200、OnlyOffice health。
- 自动对大于 1GB 的 image tar 使用分块上传，并逐块校验远端字节数、最终校验远端文件大小；禁止盲目反复 scp。
- 自动用 UTF-8 原始 JSON 或结构化字段校验 runtime-control `release-status`；中文摘要不可通过默认编码输出直接做判断。
- 自动把 SSH 多行输出 join 后再做正则判断；PowerShell 数组直接 `-match/-notmatch` 会造成 false negative。

### 高风险步骤

- 大镜像包上传：scp 可能因 `Timeout, client not responding` 产生远端 partial tar；必须先检查本地/NAS tar 首尾可读、大小一致，再使用带远端校验的分块上传。
- 本地 runtime-control jar 重建：旧 Java 进程会锁定 jar 导致 Maven repackage 失败；重启前必须只匹配 `java.exe` 且命令行包含目标 worktree/runtime 路径，禁止误杀当前 PowerShell。
- runtime-control API 直连：测试服发布动作接口为 `/admin-api/infra/runtime-control/actions`，预览接口为 `/admin-api/infra/runtime-control/actions/preview`，请求体必须包含 `reason`。
- 临时 worktree 清理：清理前必须确认相关提交已合回主工作区、工作区无未确认归属改动、验证已通过；阻塞状态下不得删除 worktree。

### 常见失败原因与推荐检查命令

- pnpm 版本漂移：`corepack pnpm@10.25.0 --version`、`git status --short`、检查是否存在非预期 `frontend/pnpm-workspace.yaml`。
- SQL metadata 不合规：`python -X utf8 -m pytest script/tests/test_mes_route_process_alignment_sql.py -q`；构建前先执行 release migration policy gate。
- 发布包来源不可确认：检查 `manifest.json` 的 `releaseTag`、`sourceRepos.backend.commit`、`sourceRepos.frontend.commit`、`dirty=false`、`changeSet`。
- 大包传输中断：检查本地 tar 与 NAS tar 大小、远端 partial 文件大小、`/var/log/auth.log` 中 `Timeout, client not responding`。
- 运行态误判：使用 UTF-8 WebClient/结构化 JSON；SSH 输出 join 后再正则检查 `.env IMAGE_TAG`、镜像 tag 和容器状态。

### 必须 fail fast 的条件

- manifest 缺失、releaseTag 不一致、sourceRepos commit 与目标 HEAD 不一致、dirty 不是 false、changeSet/版本说明无法确认。
- build-release 预览无法确认仅构建、不发布正式服/备份服，或 Smart Release report-only 缺少必要输入。
- SQL 发布契约检查失败，或数据库迁移风险级别/环境范围不可判定。
- 测试服发布后任一项失败：operation != SUCCESS、远端 `.env IMAGE_TAG` 不等于 releaseTag、实际镜像 tag 不一致、容器未运行、后端 health 不是 UP、前端 HTTP 不是 200、运行控制台版本号或变更说明不匹配。
- 发现 PowerShell 编码、数组匹配或 API 路径造成误判时，必须改为结构化/原始 UTF-8 校验后再下结论，不得降级跳过验证。
