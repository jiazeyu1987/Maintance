# 构建发布耗时问题预防清单

## 适用范围

当任务涉及 IntRuoyi 运行控制台真实 E2E 构建发布包、发布到测试服、发布包候选验收或构建发布失败重试时，先读本文。

本文只沉淀可复用经验；正式发布规则仍以 `E:\IntRuoyi\docs\release-backup-restore.md`、`server-access.md` 和 `login-access.md` 为准。

如任务目标是让 Codex 直接照清单执行，请同时读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`。

如果任务是“仅测试服发布”或“当前提交发布到测试服”，先读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md` 作为阶段门禁入口；本文保留详细故障经验和诊断规则。

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
     `rg -n "^FROM " E:\IntRuoyi\IntRuoyiBackend E:\IntRuoyi\IntRuoyiFronted -g Dockerfile*`
   - 对每个基础镜像执行 `docker pull <image>` 和 `docker image inspect <image>`。
   - 本次已证明 `nginx:1.27-alpine` 拉取超时或 EOF 会让前端镜像构建在后半程失败，必须在真实 E2E 提交前提前发现。

3. 先跑迁移策略门禁。
   - 后端仓库执行：
     `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`
   - `release-migration dependsOn` 必须写 migrationId，即 SQL 文件名 stem，不带 `.sql` 后缀。
   - `code-only` 和 `-SkipDatabaseSync` 只表示不做数据同步，不表示跳过 schema、required SQL、迁移元数据或发布 manifest 门禁。

4. 先释放 Maven target 和 jar 锁。
   - 构建前至少验证：
     `mvn -f E:\IntRuoyi\IntRuoyiBackend\pom.xml -pl yudao-module-dcc -DskipTests clean`
     `mvn -f E:\IntRuoyi\IntRuoyiBackend\pom.xml -pl yudao-server -DskipTests clean`
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

- 完整三环境发布必须沿单一 `releaseTag` 一次性走完 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；仅测试服发布以 `docs/test-release-preflight.md` 为范围权威，在 `publish-test` 与测试服真实运行态验收后停止；任何范围都不得拼接多轮版本结果。
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

### 2026-09-14 app-release 无数据部署不得写 eDHR Object Lock 探针

- Trigger: 标准一键发布、without-data、`PublishScope=app-release`、`deploy-release`、用户要求不带业务数据/不做 MinIO 数据同步。
- Preflight check: 发布脚本必须仅校验目标运行环境 `EDHR_S3_*` 配置存在和格式正确；不得在 `app-release deploy-release` 路径调用 `Invoke-EdhrStorageRetentionVerifier` 或任何会写对象存储探针的 verifier。执行前运行 `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "edhr_storage_probe"`。
- Blocker: 标准程序包部署阶段出现 Object Lock 探针对象上传、MinIO/S3 写入、`Invoke-EdhrStorageRetentionVerifier` 调用、或把对象探针失败作为程序包发布阻塞时必须停止并修脚本；不得继续用同一失败 releaseTag 发布。
- Verification: 目标测试必须 RED/GREEN 留证，`publish-int-ruoyi.ps1` AST 解析通过；真实发布日志只允许出现 `eDHR protected storage settings validated`，不得出现 `Verifying eDHR protected storage/Object Lock target before publish`。
- Forbidden action: 禁止把“探针不是 MinIO 同步”作为继续写对象的理由；禁止用 Object Lock verifier 替代无数据发布验证；禁止为了绕过失败关闭 EDHR 配置校验。
- Evidence: `doc/tasks/one-button-app-release-20260911/execution-log.md`；r26 deploy-release 在真正切换版本前写入 eDHR protected object，随后 SQL 失败，证明写探针会给无数据程序发布制造额外副作用。

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
- 2026-07-31 追加门禁：`pnpm@10.25.0` 下 `approve-builds --all` 不可作为通用修复路径；若 `pnpm ignored-builds` 仍列出 `esbuild` / `vue-demi`，可在当前 release worktree 内临时写入最小 `pnpm.onlyBuiltDependencies`，执行 `pnpm rebuild` 后复查 `pnpm ignored-builds=None`，随后必须恢复 `package.json` 并确认 release worktree `git status --porcelain --ignored=no` 为空。不得把临时依赖放行配置留进发布输入或提交。
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
- 2026-07-19 复现证据：任务 `20260719-current-head-codeonly-three-env` 的 `publish-test-preview-r260719i.utf8.json` 返回 `{"code":400,"data":null,"msg":"publishScope"}`，未创建 operation；重新预览前必须删除部署动作请求体中的 `publishScope/includeOnlyOffice/includeShowroomBuildPackage`。

## 2026-07-06 Windows 发布 worktree 长路径门禁

### PowerShell 5.1 构建上下文删除必须验证实际长路径

- Trigger: `Directory.Delete` 或 `Remove-Item` 报 `Could not find a part of the path`，重复失败的前端 bundle 文件名很长，或 PS7 手工删除成功但发布失败。
- Preflight check: 确认发布进程实际 PowerShell 版本、准确的 `LocalCacheRoot/publish-int-ruoyi` 下 context/隔离目录、最长完整路径和残留文件数；在 PowerShell 5.1 执行生产清理函数的真实 >260 字符 fixture，并保留同级哨兵。
- Blocker: 只通过字符串断言、只在 PS7 验证、路径仍超长且未使用长路径 API、未核对真正隔离目录时，不得启动新一轮整包构建。
- Verification: `python -X utf8 -m pytest scripts/tests/test_release_docker_context_cleanup.py -q`；验证 PS5.1、长路径消失、同级保留、文件占用报错、非法目标拒绝。
- Forbidden action: 禁止未复现就把错误归因于并发；禁止换 API/加重试后直接重打整包；禁止把上一级目录没有残留误当子目录已清空；禁止异常被吞后当成功。
- Evidence: `doc/tasks/one-button-app-release-20260911/bug-regression-evidence.md`，r11-r15 清理失败及恢复后的真实 PS5.1 RED/GREEN。

### 目标数据门禁必须执行查询，迁移账本不能替代业务前置检查

- Trigger: 非 schema 迁移，或 schema 迁移声明 `requiresTargetPreflight=true` 并退出空库演练。
- Preflight check: 从同一来源/SQL/目标账本绑定的 APPLY 计划推导检查集合；检查文件、环境、只读 SQL 合同、摘要和实际执行结果全部具备后才进入构建。一次性报告全部缺失文件。
- Blocker: 缺文件、缺执行结果、目标输出为空/多行/错误标记、计划被改动、SQL 含写入/客户端命令/可执行注释时立刻停止。
- Verification: `python -X utf8 -m pytest scripts/tests/test_release_target_data_preflight.py -q --basetemp <task-cache>/target-preflight-tests`；真实运行证据必须含 requiredCount、passedCount、查询摘要、计划指纹及目标环境。
- Forbidden action: 禁止只加 `requiresTargetPreflight` 来绕过演练；禁止凭 ledger APPLIED 或 mock 成功宣称实际数据依赖通过；禁止在 READ ONLY 外执行 mysql 客户端命令。
- Evidence: `doc/tasks/one-button-app-release-20260911/bug-regression-evidence.md` 与 `execution-log.md#resume-audit-after-r15`。

执行 checklist：先做局部真实故障回归，再核整个目标检查集合；任一失败只整改相关合同/输入，记录命令、运行时、退出码和零下游写入，不重复 Maven/Docker/NAS 全流程。

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

## 2026-08-03 required SQL checksum 漂移重放菜单主键门禁

- Trigger: `preflight-plan.json` 中菜单/权限类 required SQL 出现 `action=APPLY` 且原因包含 `target checksum differs from manifest`，尤其是历史 base schema 或包含 `INSERT INTO system_menu ... SELECT ... WHERE NOT EXISTS(permission)` 的 SQL。
- Preflight check: 在镜像加载、远端 `.env IMAGE_TAG` 更新和 MySQL 执行前，只读核对目标环境 `infra_release_migration` 旧 checksum、manifest 新 checksum、SQL 中固定 `system_menu.id`、业务键 `permission/path/component` 与目标库实际占用；若固定 ID 已存在但业务键不完全等价，必须阻塞。
- Blocker: 目标库记录 checksum 与 manifest 不一致且 SQL 不是可重复执行的幂等迁移；目标库存在同一 `system_menu.id` 但 SQL 的 `WHERE NOT EXISTS` 只按 permission/path 判断；远端 MySQL 报 `ERROR 1062 Duplicate entry '<id>' for key 'system_menu.PRIMARY'`。
- Verification: 冻结 `publish-test` preview、operation JSON、脱敏 operation log、`preflight-target-state-<env>.json`、`preflight-plan.json` 摘要、远端 release lock/migration 状态、目标 `system_menu` 占用快照和测试服 `.env`/实际镜像；补 RED 测试后修复 SQL 幂等性或拆分新迁移，运行 migration policy gate，重新 build-release 新 releaseTag 并重新 `publish-test`。
- Forbidden action: 禁止手工把失败 migration 改成 APPLIED/SKIPPED、手工删除/覆盖目标库菜单、复用失败 releaseTag、或把 `.env IMAGE_TAG` 已写入目标 tag 当作发布成功。
- Evidence: `doc/tasks/20260803-head-test-only-release/execution-log.md`；`release-20260803-intmain-head-test-r260803a-r1` 的 `publish-test` operation `op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241` 在 `20260513_dcc_base_schema.sql` line 1298 失败，MySQL `ERROR 1062 Duplicate entry '6813' for key 'system_menu.PRIMARY'`；preflight-plan 对 `20260513_dcc_base_schema` 判定 `APPLY`，原因是 target checksum `9c6d4004565813ebfc8b1ad0454c6eb7d27302a348f426f1ad94795774c2bd33` 与 manifest checksum `4751b23cf28e932d936f3c6a81d9aee109afbd6fa509189dd50d589ac6abfe28` 不一致。

## 2026-07-06 mark-tested 本地启动参数引号门禁

- 触发场景：使用 Start-Process -ArgumentList 数组启动 PowerShell 脚本时，如果 -TestConclusion 等自由文本参数包含空格或中文标点，子进程命令行可能被重新拆词，后续词会被误绑定到位置参数，例如 Component，导致 ValidateSet 失败。
- 前置门禁：发布脚本参数中凡包含空格、中文说明、括号或其它自由文本时，优先使用无空格的结论文本，或生成临时 .ps1 包装脚本并在包装脚本内用 call operator 传参；不得直接依赖 Start-Process -ArgumentList 自动保留复杂字符串边界。
- 证据要求：若发生此类失败，必须冻结 stdout/stderr 与参数摘要，记录实际失败参数名和被误绑定值后再重试。

## 2026-07-08 排序类 code-only 正式发布经验

- 用户授权完整三环境发布时，产品列表、管理列表、排序规则这类看似纯后端逻辑的 code-only 发布，仍必须按完整发布闭环执行：干净发布输入 `build-release`、测试服 `publish-test`、`mark-release-tested`、正式服 `promote-prod`，不得因为“不改数据”跳过测试服或 mark-tested；仅测试服授权时不得执行 `mark-release-tested` 或正式服/备份服动作。
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
'

## 2026-07-09 build-release 预览请求不得携带 targetEnvironment

- 触发场景：通过运行控制台 API `/admin-api/infra/runtime-control/actions/preview` 预览 `build-release`。
- 失败现象：请求体同时包含 `action=build-release` 与 `targetEnvironment=test` 时，接口返回 `code=400,msg=targetEnvironment`，构建不会启动。
- 前置门禁：`build-release` 预览/执行请求只传构建字段：`action`、`reason`、`releaseTag`、`publishScope=code-only`、`includeOnlyOffice=false`、`includeShowroomBuildPackage=false`、`enableSmartReleaseReport=false`；`targetEnvironment` 仅用于 `publish-test/promote-prod/promote-backup` 部署动作。
- 处理要求：冻结失败响应和请求体；该 releaseTag 若仅预览失败且未启动 operation，可更换新 releaseTag 重新预览并执行。
## 2026-07-09 build-release 三环境预览必须含 ProdServerHost

- 触发场景：执行 code-only 三环境完整闭环，运行控制台 `build-release` 预览命令只包含 TestServerHost 与 BackupServerHost。
- 失败现象：本地预览门禁发现命令缺少 -ProdServerHost 172.30.30.57，虽然预览 API 返回成功，但后续正式服 runtime env / manifest 目标参数可能不完整。
- 前置门禁：三环境闭环的 `build-release` 预览必须同时包含 -TestServerHost 172.30.30.58、-ProdServerHost 172.30.30.57、-BackupServerHost 172.30.30.59。
- 处理要求：冻结预览参数；补齐运行控制台本地配置中 maintenance.runtime-control.environments.prod.host 后重启控制台，并使用新 releaseTag 重新预览/构建。

## 2026-07-09 build-release 迁移元数据必须先过全量策略门禁

- 适用场景：执行 IntRuoyi code-only / no-data `build-release` 前，尤其是 HEAD 中包含 `sql/mysql/*.sql` 迁移文件时。
- 强制门禁：先以运行控制台 preview 返回的实际 `scriptPath` 为准定位维护仓 `ops/release/run-release-migration-policy-gate.py`，再对冻结 app backend 的 `sql/mysql` 执行门禁并保存 JSON 证据；只有无法定位实际 ops gate 时，才补跑 app 仓 `script/release/run-release-migration-policy-gate.py` 作为辅助。历史 `--json` 示例不得直接用于冻结 worktree。
- 元数据约束：`type` 只能使用脚本允许枚举 `schema`、`data`、`menu`、`config`、`permission`、`seed`；不得写 `schema-data` 等组合值。
- 依赖约束：`dependsOn` 必须填写真实存在的 migrationId，依赖迁移的 `allowedEnvironments` 必须覆盖子迁移环境；executable 类型（`schema/data/menu/config/permission/seed`）不得直接依赖 evidence-only 类型（`preflight/backfill/postflight/rollback-dry-run`）。
- 失败处理：若 build-release 报 `Invalid type in release migration metadata`、`missing release-migration metadata` 或 `executable migration cannot depend on evidence-only migration`，先冻结 operation 日志与实际 ops gate JSON，再修复 SQL 首行元数据/依赖链并补 `script/tests` 覆盖后重新生成新的 releaseTag。
- 2026-07-15 追加证据：`release-20260715-intmain-codeonly-three-env-r260715v-r1` 在 `build-release` 阶段失败，operation `op-2026-07-14T161447801754900Z-e7e1c3bf-8141-427a-bcf9-fd79544950f7` 日志报 `Release migration metadata missing: ...\sql\mysql\20260714_dcc_personal_file_decommission.sql`。后续遇到 `20260714_dcc_personal_file_decommission.sql` 或其他新增 SQL 文件时，必须在构建前运行全量 migration policy gate；若失败，冻结 operation/manifest 状态，补 SQL 首行 `-- release-migration: ...` 与对应 `script/tests` 后使用新 releaseTag 重建。
- 2026-08-19 追加证据：`release-20260819-intmain-head-test-r260819a-r1` 在 `build-release` 阶段失败，operation `op-2026-08-18T174311645827300Z-818527d7-fab1-4411-9cec-bb27e29acdec` 日志报 `20260814_mes_c015_route_dcc_qa_reconciliation_schema`（`schema`）依赖 `20260814_mes_c015_route_dcc_qa_reconciliation_backfill`（`backfill`）。app 仓 gate 仍返回 PASS，实际维护仓 ops gate 返回 FAIL；后续发布前必须优先执行实际 ops gate，不能只用 app 仓 gate 判定。

## 2026-07-09 publish-test SQL 不得复用同一派生/临时表别名触发 MySQL 1137

- 适用场景：发布脚本执行 `required-sql/*.sql` 时出现 `ERROR 1137 (HY000): Can't reopen table: '<alias>'`。
- 强制门禁：失败后先冻结发布 stdout/stderr、远端 `infra_release_operation_lock`、`infra_release_migration` 失败行、远端 required-sql checksum 与当前 `.env IMAGE_TAG`。
- 根因判断：MySQL 对同一查询中的派生/临时表复用有限制；SQL 中如果将同一 CTE/临时结果别名在嵌套子查询中重复引用，发布执行会失败，不能通过重试或手工标绿绕过。
- 修复要求：把可复用种子结果落到真实临时表，或拆分为互不重复 reopen 的 SQL 片段；修复后必须补 `script/tests` 静态覆盖并重新构建新的 releaseTag。
- 2026-07-29 追加证据：`release-20260729-sqlfix-test-r260729c-r1` 在 `20260726_system_codex_smart_scheduling_test_items.sql` line 313 失败于 `Can't reopen table: 'seed'`；修复时将 checkpoint expected/actual count 拆成独立 `SELECT COUNT(*) INTO`，提交 `919122b6` 后用新 releaseTag `release-20260729-sqlfix-test-r260729d-r1` 重建并 `publish-test` 成功。发布前静态测试应扫描 `tmp_codex_smart_scheduling_checkpoint_seed` / `seed` 等临时表在同一语句或嵌套子查询中重复读取。
- 2026-07-31 追加证据：`release-20260731-smartseed-sqlfix-head-test-r260731c-r2` 在同一智能排产 seed SQL 失败于 `Can't reopen table: 'seed'`；正式修复提交 `fa6137aa24f65bca75714d9b8c497d71ffee5d14` 将 expected/actual checkpoint count 拆成两个 `SELECT COUNT(*) INTO` 变量，目标 pytest `5 passed`、DCC+smart seed pytest `10 passed`、migration policy `400 passed`，新 releaseTag `release-20260731-smartseed-tempfix-head-test-r260731d-r1` `publish-test` 成功。
## 2026-07-09 publish-test required SQL 前置业务数据必须由迁移自给或显式依赖

- 适用场景：发布脚本执行 `required-sql/*.sql` 时，SQL 通过 `SIGNAL SQLSTATE '45000'` 报 `Missing <业务对象>`，例如 `Missing RT000006 pressure pump route`。
- 强制门禁：失败后先冻结发布 stdout/stderr、远端 `infra_release_operation_lock`、`infra_release_migration` 失败行、远端 required-sql checksum、相关业务表查询快照与当前 `.env IMAGE_TAG`。
- 根因判断：code-only 发布不得依赖测试服手工补数据；若 required SQL 需要业务主数据，应在迁移包内通过同一或前置 migration 创建，或在 metadata `dependsOn` 中声明真实前置 migrationId。
- 修复要求：不得手工改测试库绕过。修复 SQL 根因并补 `script/tests` 覆盖后，必须重新构建新的 releaseTag，不能拼接失败 tag 的后续结果。

### Gate: code-only 发布不得执行 `type=data` required SQL
- Trigger: 使用 `SkipDatabaseSync` 与 `SkipMinioSync` 构建或发布 `publishScope=code-only` 包，且 manifest / preflight-plan 包含 required SQL。
- Preflight check: 发布脚本必须在远端 MySQL 执行前按 `publishScope` 过滤 required SQL；`code-only` 只允许执行结构/菜单/配置/权限/种子等代码契约必需迁移，不得执行业务数据迁移 `type=data`。
- Blocker: 若 `preflight-plan.json` 中 `type=data` 项会进入 APPLY 执行队列，必须阻塞并修复发布脚本，重新生成新的 releaseTag。
- Verification: 运行 `python -X utf8 -m pytest tests/test_code_only_required_sql_contract.py -q`，并在发布日志中看到 `Skipping data required database SQL for code-only release` 后再继续三环境发布。
- Forbidden action: 不得手工补测试库业务数据、不得把 data SQL 改成 schema 绕过、不得复用失败 releaseTag 拼接后续环境结果。
- Evidence: `doc/tasks/20260709-codeonly-three-env-head-release/evidence/maintenance-codeonly-required-sql-contract-fix-summary.json`。


### Gate: IntRuoyi code-only 发布必须显式 `-Component intruoyi`
- Trigger: 执行 IntRuoyi 后端/前端 code-only build-release，且本机可能存在 `INT_RUOYI_WEBSITE_REPO` 或 Website 仓路径。
- Preflight check: build-release 命令必须显式传入 `-Component intruoyi`，manifest `sourceRepos` 只能包含 `ruoyi-vue-pro` 与 `yudao-ui-admin-vue3`，不得包含 dirty Website 仓或生成 `website/` 包目录。
- Blocker: 若 manifest 包含 Website、`website/` 顶层目录或任一 sourceRepos dirty=true，当前 releaseTag 判废，必须重新构建新 releaseTag。
- Verification: `build-release-<tag>-manifest-validation.json` 中 `manifestPublishScope=code-only`、后端/前端 dirty=false、无 Website sourceRepo、无 `website/` 顶层目录。
- Forbidden action: 不得把含脏 Website 的包继续发布到测试服、正式服或备份服；不得用后续验证拼接该 releaseTag。
- Evidence: `doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v7-manifest-scope-failure-freeze.json`。


### Gate: code-only required SQL 过滤必须以 manifest 类型为准
- Trigger: `publishScope=code-only` 发布包生成 `preflight-plan.json` 并准备执行 required SQL。
- Preflight check: 发布脚本不得依赖 `preflight-plan.json` item 的 `type` 字段；必须从 manifest requiredSql 建立 `migrationId -> type` 映射，并按该映射跳过 `type=data`。
- Blocker: 若任一 APPLY item 无法在 manifest requiredSql 中找到 migrationId 或 type，必须 fail fast，不得继续执行远端 MySQL。
- Verification: `python -X utf8 -m pytest tests/test_code_only_required_sql_contract.py -q` 通过，并在发布日志中看到 data SQL 的 `Skipping data required database SQL for code-only release`。
- Forbidden action: 不得用手工补测试库 RT000006、手工改 preflight-plan、或把 data SQL 改成 schema 来绕过门禁。
- Evidence: `doc/tasks/20260709-codeonly-three-env-head-release/evidence/maintenance-codeonly-required-sql-contract-v2-fix-summary.json`。


### Gate: build-release 前检查 Java/Maven native memory 余量
- Trigger: 执行 IntRuoyi `build-release`，尤其是连续多轮 Maven/Docker 构建后。
- Preflight check: 构建前记录系统可用物理/虚拟内存；若上轮出现 JVM `Native memory allocation (malloc) failed`，必须释放/降低构建内存压力后再生成新 releaseTag。
- Blocker: 若 Java/Maven 构建阶段出现 `There is insufficient memory for the Java Runtime Environment to continue`，当前 releaseTag 判废，冻结 `hs_err_pid*.log`、operation stdout/stderr、内存快照。
- Verification: 新一轮构建前记录内存快照，构建命令使用受控 JVM/Maven 内存参数，并最终生成 manifest 通过校验。
- Forbidden action: 不得复用失败 releaseTag；不得忽略 JVM native memory 错误继续发布。
- Evidence: `doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v9-java-native-memory-failure-freeze.json`。

### Gate: 正式预检发布包复制不得使用 PowerShell Copy-Item -Recurse

- Trigger: 生成 `prod-preflight-release` dry-run 证据，且需要复制发布包到临时 sanitized package workspace。
- Preflight check: 在复制前确认源发布包目录存在，并优先使用 `robocopy /E` 或 Python `shutil.copytree` 创建完整目录树；不得用 `Copy-Item -Recurse` 复制包含大量 SQL/嵌套目录的发布包作为唯一方式。
- Blocker: 复制阶段出现缺失路径、部分文件未落地、返回码非成功范围，必须冻结复制命令、错误、源目录、目标目录和 dry-run/report 状态。
- Verification: dry-run 证据 JSON 必须 `status=passed`、`mode=preflight-release`、`targetEnvironment=prod`、`releaseTag` 匹配，且 `writeActions=[]`。
- Forbidden action: 不得手写 dry-run 绿灯、不得跳过 `ProdDryRunEvidencePath`、不得在没有完整 sanitized package workspace 的情况下执行正式服发布。
- Evidence: `doc/tasks/20260709-codeonly-three-env-head-release/evidence/prod-preflight-release-dry-run-v10-copyitem-failure-freeze.json`。

## 2026-07-10 构建开始后以冻结发布 worktree 为唯一来源基线

- 触发场景：业务仓持续开发，`build-release` 构建或测试服发布期间源分支继续产生新提交。
- 强制门禁：发布开始前一次性记录维护仓、后端仓、前端仓的目标提交，并将专用 release worktree 检出到这些提交；后续来源一致性只比较 release worktree HEAD、`manifest.json.sourceRepos[*].commit`、`dirty=false` 和发布产物。
- 判定规则：冻结完成后的源分支 HEAD 漂移不使已构建发布包失效，也不要求反复追逐最新提交重建；只有 release worktree HEAD、dirty 状态、Manifest v1 或产物校验发生变化时才判废。
- 自动化项：`build-release` 提交前生成 frozen-baseline JSON；构建后自动比较 worktree HEAD 与 Manifest v1 双仓提交，不再读取持续变化的源分支 HEAD 作为发布门禁。
- 禁止事项：不得把“源分支后来有新提交”误判为包来源漂移；也不得在冻结 worktree 中混入未提交修复后继续使用同一 releaseTag。
- 记录：`doc/tasks/20260709-current-head-test-only-release/execution-log.md` 中的 `release-target-refreeze-v9` 与 `build-release-v9-manifest-package-validation-corrected`。

## 2026-07-10 路线排产配置收敛迁移必须前置检查真实冲突

- 触发场景：required SQL 将 `mes_pro_route_schedule_config` 从产品维度收敛到 `tenant_id + route_version_id + route_process_id` 工序维度。
- 发布前必查：在测试服只读统计活动配置重复组，并输出冲突配置 ID、`item_id`、产能、夜班和日历差异；发现同一工序存在语义不同的配置时，必须在镜像加载、`.env IMAGE_TAG` 更新和 required SQL 执行前阻塞。
- 高风险步骤：业务数据修复必须先确认当前提交的读取/写入契约、真实引用和快照固化逻辑，再执行备份、ROLLBACK 演练和 fail-fast 事务脚本；禁止无业务依据地猜测保留哪一行。
- 自动化项：发布脚本在执行 `20260613_mes_smart_scheduling_t1_schema.sql` 前运行同等冲突查询，并在失败输出 tenant/version/process/config/item 差异。
- 必须 fail fast：冲突组不为 0、修复授权不明确、备份校验失败、引用数量变化、事务演练未恢复原状、目标唯一键仍不可创建。
- 记录：`doc/tasks/20260709-current-head-test-only-release/execution-log.md` 中的测试服冲突数据修复授权、ROLLBACK 演练与正式执行记录。

## 2026-07-10 Manifest v1 与兼容清单必须按各自 schema 校验

- `manifest.json` 是完整发布契约，负责双仓 `sourceRepos`、commit、dirty、changeSet、required SQL、资源模式和全部 artifact。
- `release-manifest.json` 是兼容概要，只要求 releaseTag、packageDirectoryName、component、publishScope、单一 backend `gitCommit` 和 artifact inventory；不得强制其包含 frontend commit。
- 自动化项：校验器先识别 schema/version，再执行对应字段集；Manifest v1 双仓来源校验与 legacy 281 项 artifact 大小/SHA256 校验必须分别保留。
- 必须 fail fast：Manifest v1 缺失、双仓提交或 dirty 无法确认、artifact 校验失败；不得因把 Manifest v1 字段错误强加给 legacy 清单而误判有效包。
- 记录：`doc/tasks/20260709-current-head-test-only-release/execution-log.md` 中的 `v9-legacy-manifest-overstrict-local-validator` 与修正后门禁结果。

## 2026-07-10 Manifest artifact SHA256 前缀门禁

- Trigger: 校验 Manifest v1 或兼容清单中的 artifact SHA256，尤其是字段可能采用 `sha256:<64hex>` 或裸 `<64hex>` 两种表示时。
- Preflight check: 先识别哈希字段 schema；只允许规范化一个开头的 `sha256:` 前缀，再验证剩余值为 64 位十六进制并与文件实际 SHA256 比较。
- Blocker: 哈希格式无法识别、前缀重复、规范化后不是 64 位十六进制、文件缺失、大小或哈希不一致。
- Verification: 输出 artifact 总数、missing、sizeMismatch、hashMismatch；全部必须为 0，且总数与 manifest 一致。
- Forbidden action: 不得把带 `sha256:` 的有效值直接与裸哈希比较后误报全部失败，不得跳过失败项或用文件存在性代替哈希。
- Evidence: `doc/tasks/20260710-current-head-test-only-release-completion-audit/execution-log.md`；初版校验器误报 281 项 hash mismatch，规范化前缀后 281/281 全部通过。
- 2026-07-31 追加证据：`r260731c-r2` 后置自定义断言直接比较 Manifest 的 `sha256:<lowercase>` 与 `Get-FileHash` 大写裸哈希，误报全部 artifact 不一致；标准 validator 已通过，修正为去除单个 `sha256:` 前缀并统一大小写后重跑通过。

## 2026-07-10 发布日志凭据脱敏门禁

- Trigger: 发布脚本、SSH、MySQL、Docker 或运行控制台会把完整命令写入 stdout/stderr、operation 日志或任务证据。
- Preflight check: 发布前确认日志器对密码、token、私钥、连接串和 `mysql -p<redacted>` 类参数脱敏；发布后在保留或提交日志前扫描明文凭据模式，扫描规则必须覆盖 `mysql -uroot -p<redacted>`、`mysql -u<user> -p<secret>`、`/user:<user> <redacted>` 这类无 `password=` 字样的命令参数。
- Blocker: 任一待保留或待提交文件含明文凭据；无法证明日志已脱敏。
- Verification: 脱敏扫描命中数为 0；任务文档只记录命令意图、退出码、计数和脱敏摘要，原始秘密日志已从任务产物中删除。
- Forbidden action: 不得把含明文密码的 stdout/stderr、operation dump 或命令历史提交到 Git，不得为“完整证据”保留凭据原文。
- Evidence: `doc/tasks/20260710-current-head-test-only-release-completion-audit/execution-log.md`；`doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md#p007`；修复发布 stdout 中检测到明文 MySQL 密码命令，完成摘要后必须删除原始日志。

## 2026-07-13 required SQL 兼容路线流迁移重命名顺序

- Trigger: code-only / no-data 发布执行 MES required SQL，且 SQL 仍引用 `mes_pro_route_use_process_batch_record`，目标环境可能已执行 `20260709_mes_route_flow_config_unification` 并将旧表重命名为 `mes_pro_route_use_process_batch_record_legacy_20260709`。
- Preflight check: 发布前只读查询目标环境 `information_schema.tables` 与 `infra_release_migration`，确认当前表、legacy 表、`20260708_mes_batch_record_version_phase_one`、`20260709_mes_route_flow_config_unification` 的真实状态；SQL 中对已被后续迁移重命名的 legacy 表只能使用显式 table-exists 守卫。
- Blocker: required SQL 直接 `ALTER` 或 `CALL add...('mes_pro_route_use_process_batch_record')`，但目标库当前表不存在且 legacy 表存在；或迁移状态显示后续重命名已完成但前序 SQL 尚未应用。
- Verification: `python -X utf8 -m pytest script\tests\test_mes_batch_record_version_sql.py -q` 必须覆盖当前表和 legacy 表双路径；发布失败时保存远端 `information_schema.tables`、`infra_release_migration`、operation lock 与 operation log 的脱敏证据。
- Forbidden action: 不得手工重建测试库表或手工改 `infra_release_migration` 绕过；不得把失败 releaseTag 拼接到后续正式/备份发布。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/evidence/publish-test-failure-db-snapshot-r260713c-r2.json`；后端提交 `fdd93ec98c`。

## 2026-07-10 测试服真实运行态与运行控制台展示必须拆分验证

- 发布成功必查仍以真实运行态为准：远端 `.env IMAGE_TAG`、backend/frontend 实际镜像、容器 running、backend health `UP`、frontend HTTP 200、目标迁移、唯一索引和冲突数。
- 运行控制台的版本验收必须真实登录页面，进入 `基础设施 -> 监控中心 -> 运行控制台`，打开全局 `版本变更说明`，核对 releaseTag、摘要、变更项和双仓提交；不得只读取接口或截图首页角标。
- 测试服后端若在 Linux 容器中仍用 `powershell.exe` 执行 status script，运维矩阵会显示 `ERROR/unknown`，`release-status.testCurrentReleaseTag` 也可能为 null。该问题必须单独记录，不能用错误矩阵覆盖已独立取得的真实运行态。
- 必须 fail fast：用户验收明确要求运维矩阵健康时，出现 Linux/PowerShell 探测错误即阻塞；若验收仅要求版本号与变更说明，则仍须保证 `release-info.json`、页面对话框和维护控制台发布记录一致，同时公开记录矩阵缺陷。
- 推荐检查：`curl /release-info.json`、Playwright 打开版本对话框、维护控制台 `/release-status`、SSH `docker inspect`、远端 HTTP 与数据库只读查询交叉验证。
- 记录：`doc/tasks/20260709-current-head-test-only-release/execution-log.md` 以及 `doc/tasks/20260710-current-head-test-only-release-completion-audit/execution-log.md` 中的 v9 真实运行态、Playwright 页面验收和已知控制台缺陷记录。

## 2026-07-10 发布任务 closeout 状态与清理契约

- Trigger: 任务工作和必要验证已完成，准备清理临时产物、合并分支或删除 worktree。
- Preflight check: 将机器可读 `## Current Status` 写为 `ready_for_closeout`，运行 task-closeout preview，确认 `task.md`、`execution-log.md`、`verification-report.md` 位于 keep，delete/blocked/warnings 与本任务范围一致。
- Blocker: 状态仍为 `in_progress`/`blocked`/`unknown`，验证报告进入 delete，存在未确认改动或未合并提交，主工作区脏改阻止 ff-only 合并。
- Verification: task-closeout apply 成功，合并结果验证通过，Git worktree 注册与物理目录均不存在，运行控制台恢复稳定主路径后，再把状态更新为 `completed`。
- Forbidden action: 不得为通过 apply 提前写 `completed`，不得删除 `verification-report.md`，不得绕过主工作区脏改或扩大删除范围。
- Evidence: `task.md`、`execution-log.md`、`verification-report.md`、task-closeout 输出、合并提交、`git worktree list` 和运行控制台 health。

- task-closeout apply 接受 `ready_for_closeout` 与 `completed`；正常流程必须优先使用 `ready_for_closeout`，只为兼容已完成旧任务保留 `completed`。
- worktree 删除完成必须同时满足：Git 注册不存在、固定任务物理根不存在、运行控制台已恢复到主工作区且 health=`UP`。
- Windows 下 `git worktree remove --force` 返回 Directory not empty 时，必须按 `docs/worktree-memory.md` 先确认已注销、路径受限、无进程引用，再删除残留；不得扩大到其他任务目录。

## 2026-07-11 runtime-control 发布候选扫描与 dead operation 门禁

### Gate: publish-test 目标 releaseTag 必须走直接 manifest 可用性验证

- Trigger: 运行控制台预览或执行 `publish-test`，且历史 release package 数量较多或 release-status/release-packages 接口耗时明显。
- Preflight check: 在 preview 前直接读取目标 `release-20260711-current-head-test-r4` 的本地包和 NAS manifest，确认 releaseTag、publishScope、sourceRepos 和 checksum；候选包列表只作展示，不作为目标包可用性的唯一门禁。
- Blocker: preview 为了校验单一 releaseTag 而触发全量候选扫描、JVM 退出、HTTP 连接关闭或 operation 未创建时，当前发布动作必须停止并记录，不得宣称 publish-test 已提交。
- Verification: health=`UP`、preview 返回 action=`publish-test` / environment=`test` / releaseTag 正确，submit 返回 operationId，最终 operation=SUCCESS。
- Forbidden action: 禁止在 runtime console 崩溃后直接手工跑发布脚本来冒充 operation=SUCCESS；若确需脚本旁路，必须先取得明确授权并记录验收缺口。
- Evidence: `20260711-current-head-test-only-release` 中 P019、`op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d`。

### Gate: dead RUNNING operation 必须与当前 releaseTag 验收拆分

- Trigger: operation 列表中存在历史 `RUNNING`，但本地无对应子进程或日志不再推进。
- Preflight check: 发布前列出 RUNNING operation，核对 operationId、releaseTag、进程、日志最后更新时间和发布锁。
- Blocker: 若 RUNNING operation 属于本次目标 releaseTag 或占用发布锁，不得继续发布；若为历史死状态，必须记录并通过当前 release-status/operation/manifest/远端状态证明本轮发布不受影响。
- Verification: 当前 build-release 与 publish-test operationId 均为 SUCCESS，release-status current test tag、远端 `.env` 和镜像 tag 均指向同一 releaseTag。
- Forbidden action: 禁止只看操作列表存在 SUCCESS 就忽略同一 releaseTag 的死锁或漂移。
- Evidence: `20260711-current-head-test-only-release` P016/P029。

## 2026-07-12 Smart Release 报告基线门禁

- Trigger: build-release 参数启用 `enableSmartReleaseReport` 或需要生成 smart release report。
- Preflight check: 在 preview 前确认 `SmartReleaseBaselineManifestPath` 存在、可读、与目标组件和发布链路匹配。
- Blocker: 启用 smart report 但 baseline manifest 缺失或不可读时必须 fail fast，不得继续构建。
- Verification: preview 参数、baseline manifest 路径和 build operation 结果均记录到任务证据。
- Forbidden action: 不得在 build operation 失败后复用同一失败 releaseTag 发布；不得用禁用报告参数掩盖用户明确要求的报告产物。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P011。

## 2026-07-12 Manifest v1 与 legacy schema 分离校验

- Trigger: 构建发布包后校验 manifest、版本号、变更说明和 sourceRepos。
- Preflight check: Manifest v1 读取发布包根目录 `manifest.json`，按 `sourceRepos`、`changeSet.component`、`changeSet.summary`、`publishScope` 校验；legacy `release-manifest.json` 只作为兼容证据，不得混用字段。
- Blocker: Manifest v1 缺失、字段路径不匹配、sourceRepos commit 与冻结 HEAD 不一致、dirty=true、版本说明无法追溯到 releaseTag。
- Verification: 记录 `manifest.json` 路径、sourceRepos、dirty、publishScope、changeSet summary 和 legacy manifest 的独立校验结果。
- Forbidden action: 不得用 legacy schema 字段判断 Manifest v1 缺字段；不得用旧镜像 tag 替代 Manifest v1 证据。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P014。2026-08-06 追加证据：`doc/tasks/20260806-head-test-only-release/manifest-validation-r260806c-r1.json` 初始校验脚本曾误读顶层 `component`，修正为 Manifest v1 的 `changeSet.component` 后验证通过；`release-20260806-intmain-head-test-r260806c-r1` manifest/sourceRepos/release-info 均证明冻结提交和变更说明一致。

## 2026-07-12 干净 release worktree 依赖恢复门禁

- Trigger: 每次新建短路径 release worktree 并执行前端/后端/维护控制台构建。
- Preflight check: 构建前在 release worktree 内确认依赖目录、lockfile、包管理器版本和离线缓存可用；缺失依赖必须先执行可复现安装命令并记录，不得复制主工作区未提交产物。
- Blocker: clean worktree 缺 `node_modules`、Maven/PNPM 缓存不可用、安装命令会修改冻结 sourceRepos 或 lockfile。
- Verification: 记录安装命令、退出码、lockfile diff、构建命令和最终 manifest sourceRepos dirty=false。
- Forbidden action: 不得把主工作区 `node_modules`、target 或 dist 直接拷入发布包；不得因依赖缺失改为从脏工作区构建。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P012。

## 2026-07-12 长任务 operationId 恢复门禁

- Trigger: build-release、publish-test 或运行态验证耗时较长、HTTP 请求超时、控制台输出中断。
- Preflight check: 提交动作后立即记录 operationId；超时后优先按 operationId 轮询状态和日志，不重复提交同一动作。
- Blocker: 未拿到 operationId、operation releaseTag 与目标不一致、状态无法证明 SUCCESS 或失败原因。
- Verification: 记录 operationId、releaseTag、最终 status、日志摘要和耗时原因。
- Forbidden action: 禁止因前端/HTTP 超时重复触发构建或发布；禁止拼接多轮 releaseTag 结果。
- Evidence: `doc/tasks/20260712-current-head-test-only-release/issues.md` P015；`doc/tasks/20260713-current-head-test-only-release-rerun/task.md` P007。

## 2026-07-12 冻结 worktree 脚本参数契约门禁

- Trigger: 在 release worktree 中执行发布前置脚本、migration policy gate、manifest 校验或维护仓发布契约测试。
- Preflight check: 执行前先读取当前冻结 worktree 中脚本的 `--help` 或测试入口，确认参数契约；历史经验中的命令只能作为候选，不能替代当前脚本契约。
- Blocker: 当前脚本不支持历史参数、参数语义不明确、输出路径未指定且 stdout 不能作为稳定证据。
- Verification: 记录 `--help` 关键参数、最终执行命令、退出码和 `--output` 证据路径。
- Forbidden action: 不得因历史文档写过 `--json` 就直接用于当前脚本；不得在参数错误时把门禁失败误判为迁移内容失败。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P003。

## 2026-07-13 build-release 三环境 Host 完整性门禁

- Trigger: 执行完整三环境 code-only 或 with-data 发布闭环的 `build-release` preview。
- Preflight check: preview arguments 必须同时包含 `-TestServerHost 172.30.30.58`、`-ProdServerHost 172.30.30.57`、`-BackupServerHost 172.30.30.59`；不能只检查 test/backup。
- Blocker: 缺任一 host、host 值与 `server-access.md` 不一致、preview 的 repo/frontend root 不指向本次 release worktree。
- Verification: 记录 preview JSON/raw summary，确认 `BackendRepoRoot`、`FrontendRepoRoot`、三环境 host、`-Component intruoyi` 和 code-only skip 参数。
- Forbidden action: 不得在缺 `-ProdServerHost` 的 releaseTag 上继续 build-release；不得用后续 promote-prod 参数补救 build-release manifest/runtime-env 的目标缺口。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P004，维护仓提交 `367786f`。

## 2026-07-13 release worktree 双前端依赖恢复门禁

- Trigger: fresh release worktree 中执行 IntRuoyi `build-release`，尤其是维护仓和业务前端分属两个 npm/pnpm 项目。
- Preflight check: submit build-release 前分别确认维护仓 frontend 和业务前端 `yudao-ui-admin-vue3` 依赖已按 lockfile 恢复；业务前端至少验证 `node_modules/.bin/cross-env` 或执行 `pnpm install --frozen-lockfile`。
- Blocker: 业务前端 `node_modules` 缺失、frozen install 修改 lockfile、`pnpm build:test` 依赖命令不可解析。
- Verification: 记录业务前端 install 命令、退出码、lockfile diff、`node_modules/.bin/cross-env` 存在性和 build-release 新 releaseTag。
- Forbidden action: 不得用维护控制台前端 install 结果替代业务前端依赖恢复；不得在失败 releaseTag 上继续发布。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P005。

## 2026-07-13 build-release 本地 Docker inspect 与 env 脱敏门禁

- Trigger: `build-release` 需要读取本地 MySQL/MinIO 容器环境变量，或日志/排障命令涉及 `docker inspect --format '{{range .Config.Env}}...'`。
- Preflight check: 提交 build-release 前只读核对 `docker version`、目标本地容器存在、`docker inspect --format '{{.State.Status}}' <container>` 可执行；如需检查 env，只能输出键名存在性或白名单脱敏摘要，不得打印完整 env。
- Blocker: `docker inspect` 返回非 0、抛出 `Exception 0xc0000005`、Docker Desktop/daemon 不可用、本地必需容器缺失，或任何待保存/提交日志包含容器完整 env、密码、token、secret。
- Verification: 记录 Docker client/server 版本、必需容器存在性、env key 存在性计数、build operation id 和失败/成功状态；secret scan 命中数必须为 0。
- Forbidden action: 不得把 `docker inspect` 原始 env 输出粘贴到任务日志、证据或提交中；不得在 Docker inspect 门禁失败后复用失败 releaseTag 继续发布。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P011/P012，operation `op-2026-07-13T020341321200Z-97c25063-2488-4604-aebf-2d62697b2496`。

## 2026-07-19 build-release Docker BuildKit 卡顿诊断门禁

- Trigger: `build-release` 进入 backend/frontend `docker build` 阶段后长时间没有新 operation 日志，或并行执行 `docker version`、`docker ps`、`docker buildx ls` 出现 `_ping` 超时、Docker Desktop Linux engine 500、BuildKit 状态不可用。
- Preflight check: 构建前先执行 `docker version`、`docker buildx ls`、`docker ps` 并记录脱敏摘要；构建中若日志停留在 `docker build`，必须同时检查 operation 状态、log `LastWriteTime`、`docker.exe` / `docker-buildx.exe` 子进程 CPU、Docker CLI 健康命令结果，以及发布包目录/manifest 状态；若 Docker 健康预检刚通过但实际 build 仍卡死，必须把“预检通过后中途失效”作为 Docker Desktop / BuildKit 运行态故障冻结，而不是重提同一 operation。
- Blocker: 构建前 Docker CLI/BuildKit 健康命令超时或 500、Docker Desktop Linux engine `_ping` 不通、或构建中同时满足“日志与文件时间连续无变化、BuildKit 子进程无 CPU/IO 进展、Docker CLI 健康命令失败”并超过本任务记录的等待阈值。
- Verification: 证据必须包含 operation JSON、脱敏 operation log、Docker 健康命令输出、相关进程快照、manifest 存在性和冻结时间；Docker 恢复后必须用新的 releaseTag 重建，不得复用失败或中止的 releaseTag。
- Forbidden action: 不得仅凭 operation 日志暂时无新增就终止构建；不得把 Docker 原始 env、密码或 token 写入任务日志；不得把被终止或 Docker 前置失败的 releaseTag 接入 publish-test / mark-tested / promote-prod / promote-backup。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/build-release-docker-precondition-failure-r260719f.json`、`build-release-operation-r260719f-final.json`、`build-release-operation-r260719f-log-final.sanitized.json`；同任务复发证据 `build-release-docker-precondition-failure-r260719j.json`、`build-release-operation-r260719j-final.json`、`build-release-operation-r260719j-log-freeze.sanitized.json`。

## 2026-07-13 远端发布锁表查询必须先按真实 schema 校验

- Trigger: publish-test、promote-prod、promote-backup 前后只读查询 `infra_release_operation_lock`、`infra_release_migration` 或其他发布治理表。
- Preflight check: 查询前先执行 `SHOW COLUMNS` / `DESCRIBE`，或使用已验证的 schema-aware 查询；`infra_release_operation_lock` 当前字段为 `update_time`，不是 `updated_time`。
- Blocker: 只读 SQL 报 `Unknown column`、表结构与脚本假设不一致、锁状态无法证明为本任务目标 releaseTag 的终态。
- Verification: 证据中记录字段清单、目标环境、releaseTag、operation_id、status 和更新时间字段；查询命令退出码为 0。
- Forbidden action: 不得在锁表查询失败时把环境状态当作已验证，不得继续使用历史字段名反复重试，不得手工更新锁表绕过发布状态。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P014。

## 2026-07-13 mark-tested payload 不得携带 targetEnvironment

- Trigger: 通过运行控制台 API 或页面执行 `mark-release-tested` / `mark-tested`。
- Preflight check: payload 必须包含 `testConclusion` 和来自 `/restore-candidates` 的 `selectedRecoverySetCandidateId`；不得携带 `targetEnvironment`；releaseTag 以测试服当前已验证版本为准。
- Blocker: preview 返回 `targetEnvironment`、`selectedRecoverySetCandidateId is required`、候选 ID 不可用、测试服运行态未验证通过。
- Verification: preview arguments 包含 `-Mode mark-tested`、`-ReleaseTag <releaseTag>`、`-SelectedRecoverySetCandidateId <candidate>`；operation=SUCCESS。
- Forbidden action: 不得手工标绿 tested 状态，不得省略 recovery set 候选，不得把 publish-test 成功直接等同 mark-tested 完成。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P015。

## 2026-07-13 运行控制台 state-dir 不得污染 release worktree

- Trigger: 临时 release worktree 中启动维护控制台并执行 `build-release`、`publish-test`、`promote-prod` 或 `promote-backup`。
- Preflight check: `runtime-control.local.yaml` 的 `state-dir`、logs、cache、operation state 必须位于 Git release worktree 外部，或已确认不会被 `git status --porcelain --ignored=no` 计入 dirty；启动 48181 后必须再次检查维护、后端、前端三个 release worktree clean。
- Blocker: 任一 release worktree 出现 `?? runtime/`、operation state、logs、cache 或其它未跟踪运行态目录；manifest sourceRepos 可能被标记 dirty。
- Verification: 启动运行控制台后记录 `git status --porcelain --ignored=no` 为空，`BackendRepoRoot`/`FrontendRepoRoot` 指向本轮 worktree，state-dir 指向 worktree 外部固定任务目录。
- Forbidden action: 不得在 release worktree dirty 时继续 build-release；不得把未跟踪 state/log/cache 目录混入发布来源证明。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P018；`r260713g` 将 state-dir 移至 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state` 后 manifest dirty=false；`doc/tasks/20260713-current-head-test-only-release/execution-log.md` 的 `runtime-dir-dirty-after-resume`。

## 2026-07-13 clean maintenance worktree local config 与 runtime 输出门禁

- Trigger: 在全新维护仓 release worktree 中构建或启动 runtime-control，尤其主工作区 dirty 或本地配置未提交时。
- Preflight check: 预期 `config/runtime-control.local.yaml` 在 clean worktree 中可能不存在；必须在 worktree 外创建任务专用 state/config，并只记录 repo-root、frontend-root、state-dir、端口、releaseTag 等非敏感字段；维护控制台构建后必须立即执行 `git status --porcelain --ignored=no`。
- Blocker: 无法证明 runtime-control 指向冻结 worktree；构建后出现 `?? runtime/`、operation state、logs/cache 等未跟踪目录；配置采集会输出密码、token、连接串或完整 `.env`。
- Verification: 记录外部 config/state 路径、运行控制台 health=UP、进程命令行指向冻结 Jar，三仓 release worktree `status --porcelain --ignored=no` 为空。
- Forbidden action: 不得把主工作区 local config 复制进 release worktree 并提交/打包；不得在维护 worktree dirty 时继续 build-release。
- Evidence: `doc/tasks/20260713-current-head-test-only-release-rerun/task.md` P001/P002，release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u`。

## 2026-07-13 发布包可用性与历史 migration 失败分层门禁

- Trigger: 指定 releaseTag 执行 `publish-test` 前校验 NAS/本地发布包，或测试服存在历史 failed migration 记录。
- Preflight check: 发布包可用性以目标 `manifest.json`、运行控制台 deploy preview、脚本配置的 NAS/PackageRoot 转换为准；单个手写 UNC `Test-Path` 只能作辅助。migration 查询必须同时区分全局历史失败和本次 target release 失败。
- Blocker: 目标 manifest 不可读、preview 无法解析包、sourceRepos 不匹配、dirty=true、当前 target release 存在 failed migration；不得因历史其他 releaseTag 失败直接误判本轮失败或通过。
- Verification: 记录 manifest 路径、releaseTag、preview package lookup、历史 failed releaseTags 列表、本次 target failed migration count=0。
- Forbidden action: 不得用单个 UNC false negative 阻塞已由脚本配置证明可用的包；不得把历史失败迁移混入本次 releaseTag 的验收结论。
- Evidence: `doc/tasks/20260713-current-head-test-only-release-rerun/task.md` P003/P004，releaseTag `release-20260713-current-head-test-r260713u`。

## 2026-07-13 测试服发布验收配置脱敏与 direct manifest lookup 门禁

- Trigger: 仅测试服发布恢复执行、读取 `runtime-control.local.yaml`、调用 `/release-status`/`/release-packages` 或验证指定 releaseTag 的发布包。
- Preflight check: 配置证据采集只输出 repo-root、frontend-root、state-dir、releaseTag、operationId 等非敏感字段，不得打印完整配置、`.env` 或 runtime-env；指定 releaseTag 时优先直接读取本地包/NAS Manifest，候选列表接口只作展示或补充。
- Blocker: 证据采集输出 NAS/数据库/SSH 密码、token、私钥或连接串；候选扫描超时、JVM 退出或返回空导致无法证明目标包；Manifest 不存在、sourceRepos dirty=true 或 commit 不匹配。
- Verification: secret scan 命中数为 0；目标 `manifest.json` 可读且 releaseTag、publishScope、sourceRepos、artifact hash 通过；候选接口超时时有 direct manifest lookup 证据。
- Forbidden action: 不得把完整 `runtime-control.local.yaml`、operation 原始日志或 secret-bearing 命令输出提交到仓库；不得用 release-status 超时掩盖目标包未校验。
- Evidence: `doc/tasks/20260713-current-head-test-only-release/execution-log.md` 的 `config-read-secret-output`、`release-status-timeout`、`publish-test-log-secret`。

## 2026-07-13 preview 参数解析必须兼容 switch flag

- Trigger: 校验运行控制台 preview arguments，尤其包含 `-RequireTested`、`-SkipDatabaseSync`、`-SkipMinioSync`、`-IncludeOnlyOffice` 等单值 switch flag。
- Preflight check: gate 脚本必须按 flag 语义解析参数；对 switch flag 只检查存在性，对 key/value flag 查找后继值，不得简单按偶数位置 zip。
- Blocker: gate parser 无法识别 switch flag，导致 `ServerHost`、`RemoteDataRoot`、`ConfirmText` 等后续参数错位或误判。
- Verification: preview gate 输出每个关键参数的来源和检查结果，至少覆盖 `ServerHost`、`RemoteAppDir`、`ConfirmText=PROD`、`RequireTested`、`RemoteDataDiskMount`。
- Forbidden action: 不得在 parser 误报后直接跳过 preview gate；必须读取原始 preview 并修正解析器。
- Evidence: `doc/tasks/20260712-intmain-codeonly-three-env-release/issues.md` P020。


## 2026-07-13 release-info 与运行控制台验收解析门禁

### release-info CRLF-safe 解析

- Trigger: 三环境运行态验证读取 `release-info.json`、版本号、变更说明或 sourceRepos commit。
- Preflight check: 使用 JSON parser 或先将远端输出 CRLF 安全规范化；若用 shell 文本压缩，必须同时删除 `\r` 与 `\n`，并校验 releaseTag、backend commit、frontend commit 三项。
- Blocker: 解析结果只得到 `{`、releaseInfoTagOk=false、commit 字段缺失、PowerShell/SSH 输出含 CRLF 导致字段截断。
- Verification: 运行态证据中 `releaseInfoTagOk=true`、`releaseInfoBackendCommitOk=true`、`releaseInfoFrontendCommitOk=true`。
- Forbidden action: 不得因文本解析器失败就手工标绿运行态；不得只用 HTTP 200 替代 release-info 内容校验。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-rerun/execution-log.md#milestone-7a-test-runtime-verification-parser-correction`。

### 运行控制台页面 console 结构化判定

- Trigger: Playwright 或浏览器工具验证运行控制台页面、版本变更说明、operation 列表和 console 输出。
- Preflight check: console 验证以结构化错误计数或精确 `Errors: 0` / `Warnings: 0` 判定；不得用简单字符串包含 `error` 扫描整段输出。
- Blocker: 页面正文或工具统计字段包含 `Errors: 0` 被误判；console 检查无法区分真实 error 与统计标题。
- Verification: 页面证据中 `operationChainVisible=true`、`operationSuccessVisible=true`、`consoleNoError=true`，且版本号和变更说明可见。
- Forbidden action: 不得跳过真实页面验收；不得把误判失败改成忽略 console。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-rerun/runtime-console-page-probe-r260713j.json`。

## 2026-07-13 release worktree 物理根目录复核门禁

- Trigger: 发布完成后删除临时 release worktree、state dir 或执行 task closeout。
- Preflight check: 分别检查维护仓、后端仓、前端仓 `git worktree list --porcelain` 不含本轮 worktree；再检查固定物理根目录、子目录、state dir 是否仍存在；若残留目录不是 Git repo，仍需按固定路径边界删除。
- Blocker: Git 注册已删除但物理根目录仍存在、state dir 仍存在、残留目录在预期根之外、仍有进程命令行引用待删路径。
- Verification: closeout 证据必须同时包含 `afterRootExists=false`、`stateExists=false`、三仓 `Registered=false`，运行控制台 health 仍为 `UP` 且主路径稳定。
- Forbidden action: 不得把 `git worktree list` 无记录等同于物理目录清理完成；不得删除无关并发任务 worktree。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-rerun/worktree-cleanup-r260713j-final.json`；`doc/tasks/20260713-current-head-codeonly-three-env-r260713v/execution-log.md` 的 `git-worktree-remove-maintenance`、`git-worktree-remove-frontend` 与 `release-worktree-cleanup`。
- 2026-07-29 追加证据：`doc/tasks/20260729-head-test-only-release/execution-log.md` closeout 中，`git worktree remove --force` 已移除 `r260729a/b/c/d` 注册，但物理目录因前端 `node_modules` / pnpm 长路径残留返回 `Directory not empty`；最终在确认无 `.git`、无进程引用、路径仅限本任务 release worktree/state 后，用长路径安全删除并复核 `Test-Path=False`。
- 2026-07-31 追加证据：`doc/tasks/20260730-head-test-only-release/execution-log.md` closeout 中，`git worktree remove --force` 已移除 `r260731d` 维护仓和主程序仓注册，但物理目录仍残留 ignored `node_modules` 树；必须同时复核 `git worktree list --porcelain`、固定物理根 `Test-Path=False`、state dir 不存在、无进程引用和运行控制台主路径 health=`UP`，再标记任务 `completed`。


## 2026-07-13 task-closeout 长运行进程日志目录门禁

- Trigger: 发布收尾恢复本地运行控制台、启动长运行进程，随后执行 task-closeout preview/apply 清理任务附属日志和证据。
- Preflight check: 恢复主路径运行控制台时，stdout/stderr 不得重定向到当前任务目录或任何 task-closeout delete 候选；apply 前检查 48181 进程命令行与打开日志位置，必要时先重启到仓库外或稳定主目录日志路径。
- Blocker: task-closeout apply 对 `.log` 返回 `PermissionError WinError 32`、进程仍占用任务目录内文件、日志路径位于待删除 evidence/task 目录。
- Verification: runtime-control health=`UP`，进程命令行指向主工作区 Jar，task-closeout preview/apply blocked=<none> 且 warnings=<none>。
- Forbidden action: 不得强杀后跳过 health 复核；不得为删除日志停止运行控制台后不恢复；不得提交被进程占用的任务附属日志。
- Evidence: `doc/tasks/20260713-current-head-codeonly-three-env-rerun/execution-log.md#milestone-13-task-closeout-cleanup`。
- 2026-07-31 追加门禁：发布验收使用 Playwright CLI daemon 后，closeout 必须扫描任务 ID / releaseTag 对应的 `output\playwright\<task-or-release>\.playwright-cli\page-*.yml` 和 `cliDaemon.js <release>` 进程；若快照可能含登录页输入字段，必须先删除快照目录，目录被锁时仅停止命令行可证明属于本任务的 Playwright daemon 和子进程，禁止误停其他并发 E2E/Playwright 任务。

## 2026-07-16 release preflight 菜单 SQL 解析边界门禁

- Trigger: `build-release` 执行维护仓 `ops.release.release_sql_contract_gate`，扫描菜单类 required SQL，尤其包含 `INSERT INTO system_menu ... SELECT ... ON DUPLICATE KEY UPDATE VALUES(...)`、后续临时表 `VALUES` 或 `system_role_menu` 授权清单。
- Preflight check: `system_menu.id` 静态唯一性门禁只应解析真正的 `INSERT INTO system_menu (...) VALUES (...)` 插入声明；遇到 `INSERT INTO system_menu (...) SELECT ...` 时不得继续吞到后续 `ON DUPLICATE KEY UPDATE VALUES(...)` 或无关临时表 `VALUES`。若报错行号落在临时表、授权清单或更新子句，先按 TDD 修复维护仓解析器并补回归测试。
- Blocker: `system_menu.id must be an integer literal for release preflight` 指向非 `system_menu VALUES` 插入行，或 `duplicate system_menu.id detected across release SQL history` 的第二个位置实际来自临时表/授权清单。
- Verification: 维护仓新增 `scripts/tests/test_release_sql_preflight_gate.py` 回归，证明 `INSERT ... SELECT ... ON DUPLICATE KEY UPDATE VALUES(...)` 加后续临时表不会被当成 `system_menu` 插入；运行 `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q`；再用 clean release worktree 重新运行 migration policy gate 和新的 `build-release`。
- Forbidden action: 不得为迎合误解析器去改业务 SQL 或手工改库；不得跳过 release preflight planner；不得复用失败 releaseTag 继续 `publish-test`、`mark-tested`、`promote-prod` 或 `promote-backup`。
- Evidence: `doc/tasks/20260716-current-head-codeonly-three-env/execution-log.md`，`release-20260716-intmain-codeonly-three-env-r260716a-r1` operation `op-2026-07-15T162751592993800Z-07bd38b2-499b-4708-84a9-7b358734b779` and `release-20260716-intmain-codeonly-three-env-r260716b-r1` operation `op-2026-07-15T164733908318700Z-b740f44f-6170-46ed-910a-63aa3ba1c3b1` both failed before manifest because the parser crossed from `INSERT INTO system_menu ... SELECT` into later non-`system_menu` `VALUES` blocks.

## 2026-07-16 release build 前端 ESLint slot 未使用变量门禁

- Trigger: `build-release` 进入业务前端 `pnpm build:test` / `vite build --mode test`，Vite ESLint 插件扫描 Vue template slot scope。
- Preflight check: 在干净前端 release worktree 执行目标构建命令或至少执行会触发 `vite-plugin-eslint` 的 `pnpm build:test`；重点关注表格列 `#default="{ ... }"`、排序/筛选 slot scope 和组合式函数返回值是否被模板实际使用。
- Blocker: `vue/no-unused-vars`、`no-unused-vars` 或 `vite-plugin-eslint` 报未使用 slot 变量，尤其是发布期间才被 build:test 捕获的 `sortColumnAttrs`、`handleTemplateSortChange` 等。
- Verification: 前端任务补充聚焦测试或构建证据，`pnpm build:test` 在 clean release worktree 通过；随后重新构建新的 releaseTag，原失败 tag 判废。
- Forbidden action: 不得关闭 ESLint、移除 vite-plugin-eslint、用注释绕过规则或跳过前端构建；不得复用失败 releaseTag 继续发布链路。
- Evidence: `doc/tasks/20260716-current-head-codeonly-three-env/execution-log.md`，`release-20260716-intmain-codeonly-three-env-r260716c-r1` operation `op-2026-07-15T170422234564100Z-32d8180b-c6c1-448f-8541-5bf8a9adf666` failed during `pnpm build:test` at `src/views/mes/pro/scheduler-workbench/components/ProcessWipTable.vue:27`.

## 2026-07-19 system entitlement 迁移元数据门禁

- Trigger: code-only / no-data 发布前执行全量 migration policy gate，HEAD 包含 `sql/mysql/20260718_system_entitlement_management.sql` 或其他新增系统权限治理表、策略种子 SQL。
- Preflight check: 每个新增 `sql/mysql/20*.sql` 首行必须是完整 `release-migration` 元数据，至少包含 `allowedEnvironments`、`dependsOn`、`type`、`riskLevel`；`dependsOn` 必须填写迁移 ID，不带 `.sql` 后缀；对应 `script/tests` 必须断言该 SQL 的发布元数据存在且语义与内容一致。
- Blocker: policy gate 输出 `missing release-migration metadata: ...20260718_system_entitlement_management.sql`、`unknown release-migration metadata key`、`dependsOn missing migration`、首行只有说明性短语、`type` 不在脚本允许枚举内，或缺少对应测试断言。
- Verification: 先冻结 gate JSON，再补测试 RED；SQL 首行补齐后运行 `python -X utf8 -m pytest script/tests/test_system_entitlement_policy_sql.py -q` 和 `python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql --output <task-dir>/migration-policy-gate-<id>.json` 均通过。
- Forbidden action: 不得在缺元数据时跳过 migration policy gate、手工标绿发布、手工改目标库或把 `code-only` 解释成跳过 schema/seed 迁移门禁。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`r260719a` preflight failed before `build-release` with `missing release-migration metadata` for `20260718_system_entitlement_management.sql`.

## 2026-07-19 release-migration 结构化字段、类型集合与 dependsOn 后缀门禁

- Trigger: code-only / no-data 发布前执行全量 migration policy gate，SQL 首行仍是描述性短语、把 migrationId 写成普通文本，在 `dependsOn` 中写入带 `.sql` 后缀的文件名、把 `type` 写成复合值，或主程序新增 migration type 但维护仓发布工具尚未支持。
- Preflight check: 先执行 `python -X utf8 <maintenance-worktree>/ops/release/run-release-migration-policy-gate.py --sql-root <app-worktree>/IntRuoyiBackend/sql/mysql --output <task-dir>/migration-policy-gate-<id>.json`；再对比主程序冻结 HEAD 全部 `release-migration type` 去重集合、维护仓 Python gate 的允许集合和 `ops/deploy/publish-int-ruoyi.ps1` parser 允许集合，三者必须一致。新增类型必须同步修改两个维护仓 parser、manifest/required SQL 语义和契约测试并提交。
- Blocker: 门禁输出 `unknown release-migration metadata key ... riskLevel`、`dependsOn missing migration '<id>.sql'`、`invalid type ... schema,menu`、`invalid type ... backfill`，三处类型集合不一致，或测试只检查 `startswith("-- release-migration:")` / `riskLevel` 而未锁定结构化字段。
- Verification: 失败 JSON 先冻结到任务目录；补充/修正 `script/tests` 后先 RED，再修正 SQL 或正式扩展两个 parser；目标 pytest、PowerShell 契约测试与全量 migration policy gate 均通过，并复核三处类型集合一致后，才能进入依赖恢复与 `build-release`。
- Forbidden action: 不得把未知类型临时改写成已有类型、从 release worktree 修改未提交 SQL、为 code-only 发布跳过 SQL 元数据门禁、只改 Python gate 不改正式 PowerShell parser、手工编辑 manifest 或远端迁移状态绕过。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`r260719a` gate failed on描述性 metadata、`type=schema,menu` 和 `.sql` dependsOn。`doc/tasks/2026-08-11-test-only-release-head/execution-log.md`；`r260812a` frozen app HEAD 使用 `type=backfill`，而 frozen maintenance HEAD Python/PowerShell parsers 只接受 `schema/data/menu/config/permission/seed`，因此在 build-release 前 fail fast。

## 2026-07-19 build-release MES companion contract 编译门禁

- Trigger: clean release worktree 执行 `build-release`，后端服务实现已引用新的 MES VO、Mapper 或 Service 方法，但对应合同文件没有进入已提交 HEAD。
- Preflight check: 在提交 `build-release` 前，对冻结后端 worktree 运行窄合同测试，至少覆盖 `EdhrBatchExecutionRespVO.releaseActionLocked`、`EdhrBatchExecutionTaskOpenReqVO.workTaskId`、`EdhrBatchExecutionTaskRespVO.batchRecordVersionNo`、`MesProEdhrRecordChangeService.withdrawVoidBatchExecution`、`MesProRouteVersionMapper.updateApprovalFieldsToDraft`、`MesProBatchRecordParsedCell.isReviewedCellRule`、`MesProBatchRecordParsedCell.getCellRuleSource`，并覆盖新增 `@Override` 实现方法是否仍存在于父接口/父类；随后运行 `mvn.cmd -pl yudao-module-mes -am "-DskipTests" compile`。
- Blocker: Maven 编译日志出现 `setReleaseActionLocked`、`getWorkTaskId`、`setBatchRecordVersionNo`、`withdrawVoidBatchExecution`、`updateApprovalFieldsToDraft`、`isReviewedCellRule`、`getCellRuleSource`，或出现 `@Override` 方法未覆盖/实现父类型方法等同类 companion contract 缺失；manifest 尚未生成时，该 releaseTag 必须判废。
- Verification: 冻结 operation JSON、operation log、preview 参数、manifest absent 状态和失败时间；先沉淀本门禁，再补 RED/GREEN 合同测试和 Maven 编译证据，最后使用新的 releaseTag 重新构建。
- Forbidden action: 不得把主工作区未提交 companion 改动直接混入发布包；不得跳过 Maven 编译、删除 `@Override`、注释实现调用或手工标绿失败 releaseTag。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719b-r1` build operation `op-2026-07-18T174249577677300Z-c5a943af-322e-4b82-b906-1e07637a94de` failed before manifest during `yudao-module-mes` compile.
- Evidence: `doc/tasks/20260723-codeonly-three-env-release-loop/execution-log.md`；`r260723r` build-release 前置 MES companion compile gate 失败，尚未创建 releaseTag，日志命中 `MesProBatchRecordExecutionBusinessApprovalEffectExecutor.java:[65,5]` `@Override` 签名漂移，以及 `MesProBatchRecordParsedCell.isReviewedCellRule()` / `getCellRuleSource()` 缺失。

## 2026-07-19 frontend eDHR companion API export 门禁

- Trigger: clean frontend release worktree 执行 `pnpm build:test`，页面已引用新的 eDHR API 方法，但 `src/api` 没有同步导出。
- Preflight check: 在 `build-release` 前运行相关静态合同和 `pnpm build:test`；对页面 import 的新增 API，测试必须同时断言 API 文件导出方法名和真实后端 URL，例如 `withdrawVoidBatchExecution` -> `/mes/pro/edhr-change/void-batch-execution/withdraw`。
- Blocker: Rollup/Vite 报 `"withdrawVoidBatchExecution" is not exported by "src/api/mes/pro/edhr/change.ts"` 或同类 missing export；该 releaseTag 未生成时必须判废。
- Verification: 冻结 `pnpm build:test` 失败输出、补 RED/GREEN 静态测试、修复 API 导出，再在新的 clean release worktree 运行 `pnpm build:test` 通过后才能提交 `build-release`。
- Forbidden action: 不得删除页面功能、改成通用 BPM 调用、跳过前端 build、关闭 Rollup/Vite 检查或把主工作区未提交 API 直接混入发布包。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`r260719c` frontend preflight failed before `build-release` because `BatchExecutionListPage.vue` imported `withdrawVoidBatchExecution` while `change.ts` lacked the export.

## 2026-07-23 frontend build:test vite progress cache 门禁

- Trigger: clean frontend release worktree 的 `pnpm build:test` / `vite build --mode test` 被工具超时、中断或人工停止后再次重跑。
- Preflight check: 重跑前先冻结失败日志；随后确认该 worktree 下无残留 `node.exe`、`vite`、`esbuild`、`pnpm` 等构建进程，并清理 `node_modules\.progress`、`node_modules\.progress.json`、`dist`、`dist-test` 这些由中断或上次成功构建留下的本地产物。
- Blocker: `vite-plugin-progress` 在 `closeBundle` 中执行 `mkdir node_modules\.progress` 时报 `EEXIST: file already exists`，或存在同一 worktree 的残留前端构建进程仍持有构建目录。
- Verification: 记录进程扫描结果与清理对象；在同一 clean release worktree 重新执行 `pnpm build:test` 并获得 PASS；重跑后再次清理 `node_modules\.progress` / `dist-test` 等输出并确认发布输入 Git `dirty=false`，不得把 build output 或 progress cache 纳入 release sourceRepos。
- Forbidden action: 不得把超时截断的构建当作成功；不得跳过前端构建、删除整个 `node_modules` 作为默认动作、手工标绿失败日志，或带着 `.progress` / `dist` 残留继续 `build-release`。
- Evidence: `doc/tasks/20260723-codeonly-three-env-release-loop/execution-log.md`；`r260723s` frontend preflight first run was interrupted by a 360s timeout, retry failed with `Error: EEXIST: file already exists, mkdir '<frontend>\node_modules\.progress'`; frozen log `doc/tasks/20260723-codeonly-three-env-release-loop/evidence/frontend-build-test-r260723s.log`.

## 2026-07-19 publish-test required SQL collation 门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 required SQL，SQL 将临时表字符串列、用户变量或字面量与真实业务表 `varchar` 字段做 `=` / `JOIN` / `NOT EXISTS` 比较，尤其命中 `20260717_mes_edhr_filler_minimal_permissions.sql`。
- Preflight check: 发布前对新增或近期修改的 required SQL 运行静态门禁，禁止未声明 collation 的临时表字符串列与 `system_*` / `mes_*` 字符字段直接比较；若 SQL 只为历史权限补齐且已被 `system_entitlement_policy` 动态授权替代，应将旧角色/用户/菜单写入迁移改为无副作用 no-op，并用测试断言不再写 `system_user_role` / `system_role_menu`。
- Blocker: 远端 MySQL 报 `ERROR 1267 (HY000): Illegal mix of collations ... for operation '='`，或静态测试发现 required SQL 仍包含临时字符串权限表直接 join `system_menu.permission`、用户变量角色编码 join `system_role.code`、或写入静态角色/用户/菜单绑定。
- Verification: 先冻结 preview、operation JSON、脱敏 operation log、manifest state、远端 `infra_release_operation_lock` / `infra_release_migration` 失败行和 `.env IMAGE_TAG`；补 RED 测试后修复 SQL，运行目标 pytest、migration policy gate、重新构建新 releaseTag 并重新 `publish-test`。
- Forbidden action: 不得手工修改测试库 collation、手工更新 `infra_release_migration` / operation lock、复用失败 releaseTag 继续 `mark-tested` / `promote-prod` / `promote-backup`，或把 `code-only` 解释成可以跳过 required SQL 根因修复。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719d-r1` `publish-test` operation `op-2026-07-18T190202341116900Z-12fbff2a-a9f3-47cd-bff1-a026ba7f4701` failed on `20260717_mes_edhr_filler_minimal_permissions.sql` line 24 with MySQL `ERROR 1267`.

## 2026-07-29 system_codex_test seed collation 门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 `20260726_dcc_codex_test_items_seed.sql`、`20260726_system_codex_smart_scheduling_test_items.sql` 或其他 Codex 测试管理 / 智能排产 seed SQL，SQL 使用临时 seed 表、过程变量或字面量与 `system_codex_test_case` / `system_codex_test_checkpoint` 的 `name`、`status`、`severity` 等字符串列比较。
- Preflight check: 发布前用真实目标库 `information_schema.COLUMNS` 查询 `system_codex_test_case` 与 `system_codex_test_checkpoint` 文本列 collation；若目标列为 `utf8mb4_0900_ai_ci`，seed 临时表字符串列、过程内 checkpoint/name/status/severity 校验、JOIN/NOT EXISTS/COUNT 比较必须显式使用相同 collation，或直接按目标列 collation 声明临时表字段。静态测试必须覆盖 `tmp_*_seed`、`tmp_codex_smart_scheduling_*` 与 `system_codex_test_*` 字段比较。
- Blocker: 远端 MySQL 报 `ERROR 1267 Illegal mix of collations`，尤其包含 `utf8mb4_0900_ai_ci` vs `utf8mb4_unicode_ci` 或 `utf8mb4_general_ci` vs `utf8mb4_0900_ai_ci`，或静态/只读门禁发现 Codex seed 临时表 `DEFAULT COLLATE=utf8mb4_unicode_ci` / `utf8mb4_general_ci` 但目标 `system_codex_test_*` 列为 `utf8mb4_0900_ai_ci` 且比较未显式 `COLLATE`。
- Verification: 冻结 `publish-test` preview、operation JSON、脱敏 operation log、manifest/sourceRepos、远端 `.env IMAGE_TAG`、实际镜像 tag、`infra_release_operation_lock`、`infra_release_migration` 失败行和 `information_schema.COLUMNS` collation 输出；补 RED 测试后修复 SQL，运行目标 SQL 测试、migration policy gate，重新 build-release 新 releaseTag 并重新 `publish-test`。
- Forbidden action: 不得手工修改测试库默认 collation、手工更新 release lock / migration 状态、删除 Codex 测试管理数据、复用失败 releaseTag 继续 `mark-tested` / `promote-prod` / `promote-backup`，或把 `.env IMAGE_TAG` 已变更当作发布成功。
- Evidence: `doc/tasks/20260729-head-test-only-release/execution-log.md`；releaseTag `release-20260729-intmain-head-test-r260729a-r1` failed on `20260726_dcc_codex_test_items_seed.sql` line 291 with MySQL `ERROR 1267`; `release-20260729-sqlfix-test-r260729b-r2` then failed on `20260726_system_codex_smart_scheduling_test_items.sql` with `utf8mb4_general_ci` vs `utf8mb4_0900_ai_ci`; final repaired source commit `919122b6` rebuilt as `release-20260729-sqlfix-test-r260729d-r1` and passed `publish-test`。2026-08-01 追加证据：`doc/tasks/20260801-head-test-only-release/execution-log.md`；`release-20260801-intmain-head-test-r260801a-r2` `publish-test` operation `op-2026-07-31T184648151088Z-d51572f6-9207-44dd-bbab-6f54c347cea4` 再次 failed on `20260726_system_codex_smart_scheduling_test_items.sql` line 313，MySQL `ERROR 1267` 显示 `utf8mb4_general_ci` vs `utf8mb4_0900_ai_ci`，说明静态门禁必须覆盖过程内 checkpoint 计数/校验比较。

## 2026-07-19 publish-test 角色 ID 硬编码占用门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 required SQL，SQL 通过固定 `system_role.id` 创建或更新业务角色，尤其命中 `20260718_bpm_admin_role_assignment.sql`、`bpm_admin`、`910311`。
- Preflight check: 发布前对新增或近期修改的角色/菜单 required SQL 运行静态门禁，禁止在目标环境已有非目标角色占用固定 ID 时直接 `SIGNAL` 中止；正式方案应先按稳定业务键 `tenant_id + code` 查找目标角色，目标角色不存在且首选 ID 空闲时才使用首选 ID，否则由数据库生成新 ID 并把后续 `system_role_menu` / `system_user_role` 写入同一个解析出的角色 ID。
- Blocker: 远端 MySQL 报 `ERROR 1644 (45000): Role id <id> is already occupied by another role`，或静态测试发现角色 SQL 仍以固定 ID 作为唯一身份、存在 “occupied by another role” 失败分支、没有 `LAST_INSERT_ID()` / 等价动态 ID 生成路径。
- Verification: 先冻结 preview、operation JSON、脱敏 operation log、manifest state、远端 `infra_release_operation_lock` / `infra_release_migration` 失败行和占用角色快照；补 RED 测试后修复 SQL，运行目标 pytest、migration policy gate、重新构建新 releaseTag 并重新 `publish-test`。
- Forbidden action: 不得手工删除/改名目标环境已有角色、手工更新发布锁或迁移状态、复用失败 releaseTag 继续后续步骤，或把角色 ID 冲突当作测试服脏数据直接跳过。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719e-r1` `publish-test` operation `op-2026-07-18T195310630559800Z-2b5f6c24-bd91-4ee0-b02c-cb23ba489531` failed on `20260718_bpm_admin_role_assignment.sql` with MySQL `ERROR 1644` because role id `910311` was already used by `electronic_signature_admin`.

## 2026-07-22 publish-test required SQL 权限菜单兼容门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行菜单或角色权限类 required SQL，SQL 同时校验 `system_menu.id` 与 `system_menu.permission`，尤其包含临时权限表、`tmp_*_expected_permission`、`tmp_*_expected_menu`、审计/全量管理员权限集合。
- Preflight check: 发布前静态测试必须覆盖两类兼容性：临时权限表字符串列与 `system_menu.permission` 比较时显式使用目标列 collation，例如 `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`；权限菜单存在旧 ID 但同一 `permission`、`status=0`、`deleted=0` 时，不得再要求偏好 ID 必须存在，主校验应以稳定业务键 `permission` 为准。
- Blocker: 远端 MySQL 报 `ERROR 1267 Illegal mix of collations`，或 required SQL 报 `Missing enabled full-scope admin menu` 且只读核对显示缺失的是偏好菜单 ID、目标权限已由旧 ID 正常存在。
- Verification: 先冻结失败 releaseTag、operation/migration 状态、远端 `system_menu.permission` collation、缺失 ID 与同权限菜单快照；补 RED 测试后修复 SQL，运行目标 pytest、migration policy gate，重新构建新的 releaseTag，并通过测试服真实页面/API 验收。
- Forbidden action: 不得手工改测试库 collation、手工插入偏好 ID 菜单、删除旧权限菜单、手工更新发布锁/迁移状态，或复用失败 releaseTag 继续发布。
- Evidence: `doc/tasks/20260722-dcc-distribution-backend-test-release/execution-log.md`；`release-20260722-dcc-distribution-backend-r260722d-r3` 失败于 `ERROR 1267`，`r4` 失败于缺失偏好菜单 ID `990226`，`r5` 通过后测试服个人工作台 DCC 分发/培训 `my-page` 均返回业务码 `0`。

## 2026-07-19 controlled content 生命周期迁移 OBSOLETE_CHAIN 门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 `20260718_controlled_content_lifecycle.sql` 或其他 DCC controlled content 生命周期迁移，目标库存在 `dcc_controlled_file_master.current_active_controlled_file_id` 指向 `dcc_controlled_file.status='OBSOLETE'` 的历史链。
- Preflight check: 发布前用真实 schema 只读核对 `dcc_controlled_file_master` 与 `dcc_controlled_file` 字段，当前字段名为 `file_number`、`current_active_controlled_file_id`、`status`、`tenant_id`；预检查必须区分两类数据：`master.status='OBSOLETE_CHAIN'` 且无任何 `ACTIVE` 版本的全链作废历史应由迁移跳过；非 `OBSOLETE_CHAIN` master 指向已作废、缺失、删除或多条 active 候选时才阻塞。
- Blocker: MySQL 报 `ERROR 1644 (45000): dcc master points to obsolete revision; repair current active before controlled content lifecycle migration`，且远端只读探针证明受影响 master 不是合法 `OBSOLETE_CHAIN`、存在 active 候选歧义、或 master 与 active/current 关系不满足唯一可修复条件。
- Verification: 先冻结 preview、operation JSON、脱敏 operation log、manifest state、远端 `infra_release_operation_lock` / `infra_release_migration` 失败行、真实表字段清单、受影响 master 状态分布和 active 候选统计；补 RED 测试证明合法 `OBSOLETE_CHAIN` 不应触发失败，再修复 SQL，运行目标 pytest、migration policy gate、重新构建新 releaseTag 并重新 `publish-test`。
- Forbidden action: 不得把 `OBSOLETE_CHAIN` 的测试租户历史数据手工改成 `ACTIVE` 或清空 current 指针；不得使用错误历史表名 `dcc_file` 或字段名 `file_no` 作为判断依据；不得手工更新发布锁/迁移状态、复用失败 releaseTag 继续后续步骤，或跳过 controlled content 生命周期迁移。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719g-r1` `publish-test` operation `op-2026-07-18T215155104007500Z-0ab6f192-96e1-42b9-ab65-bd477895625d` failed on `20260718_controlled_content_lifecycle.sql` while read-only probes showed 181 affected rows were tenant `122`, `master.status=OBSOLETE_CHAIN`, current file status `OBSOLETE`, and `active_count=0`.

## 2026-07-19 controlled content content_key CAST collation 门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 `20260718_controlled_content_lifecycle.sql` 或其他迁移，把 bigint 业务 ID 通过 `CAST(<id> AS CHAR)` 与 `controlled_content_version_ref.content_key` 这类显式 `utf8mb4_unicode_ci` 字段比较。
- Preflight check: 发布前对 controlled content required SQL 运行静态门禁；凡出现 `existing_ref.content_key = CAST(... AS CHAR)`、`ref.content_key = CAST(... AS CHAR)` 或同类 `varchar` 字段与 CAST 字符串比较，CAST 结果必须显式 `COLLATE utf8mb4_unicode_ci`，或使用与目标列完全一致的 collation 表达式；同时用只读远端 `information_schema.COLUMNS` 确认目标列实际 collation。
- Blocker: MySQL 报 `ERROR 1267 (HY000): Illegal mix of collations (utf8mb4_unicode_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT) for operation '='`，或静态测试发现 controlled content `content_key` 比较仍依赖数据库默认 collation。
- Verification: 先冻结 preview、operation JSON、脱敏 operation log、manifest state、远端 `infra_release_operation_lock` / `infra_release_migration` 失败行和目标字段 collation；补 RED 测试后修复 SQL，运行目标 pytest、migration policy gate、重新构建新 releaseTag 并重新 `publish-test`。
- Forbidden action: 不得手工修改目标库默认 collation、手工更新发布锁/迁移状态、删除已生成的 platform lifecycle 表来绕过，或复用失败 releaseTag 继续 `mark-tested` / `promote-prod` / `promote-backup`。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719h-r1` `publish-test` operation `op-2026-07-18T224523125574700Z-b262418e-b298-47f7-86e1-4d6d3cd905c6` failed on `20260718_controlled_content_lifecycle.sql` with `ERROR 1267` after `controlled_content_version_ref.content_key` existed as `utf8mb4_unicode_ci` while `CAST(master.id AS CHAR)` inherited `utf8mb4_0900_ai_ci`.

## 2026-07-19 backup promote tenant package menu_ids 长度门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行新增菜单类 required SQL，SQL 会把新增菜单 ID 合并回 `system_tenant_package.menu_ids`，尤其命中 `20260717_bpm_form_center.sql` 和大量 9 位菜单 ID。
- Preflight check: 发布前静态测试必须识别 `UPDATE system_tenant_package SET menu_ids = JSON_ARRAYAGG(...)` 或同类合并逻辑；若新增菜单集合可能让 JSON 超过现有 `varchar(4096)`，迁移必须先把 `system_tenant_package.menu_ids` 扩为可承载的 `TEXT` / `LONGTEXT`，并用测试断言该 schema 扩容早于合并更新。
- Blocker: 远端 MySQL 报 `ERROR 1406 (22001): Data too long for column 'menu_ids'`，或目标 SQL 对 `system_tenant_package.menu_ids` 做 JSON 合并但没有显式 schema 扩容 / 长度前置检查。
- Verification: 先冻结 preview、operation JSON、脱敏 operation log、manifest state、远端 `.env IMAGE_TAG`、实际镜像 tag、`/mnt/intruoyi-data` 挂载、`infra_release_operation_lock` 和 `infra_release_migration` 失败行；补 RED 测试后修复 SQL，运行目标 pytest、migration policy gate、重新构建新的 releaseTag，并用同一新 releaseTag 重走完整发布链。
- Forbidden action: 不得手工缩短目标库 `menu_ids`、删除套餐菜单、手工改发布锁或迁移状态、直接在备份库修改字段后复用失败 releaseTag，或把 code-only 发布解释成可以跳过菜单 required SQL。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；`release-20260719-intmain-codeonly-three-env-r260719i-r1` `promote-backup` operation `op-2026-07-19T003345411999400Z-e0458e90-7ca3-494c-81ea-08babadccf3b` failed on `20260717_bpm_form_center.sql` line 380 with MySQL `ERROR 1406` while backup `.env IMAGE_TAG` had moved to the new releaseTag but backend/frontend containers still ran the previous release.

## 2026-07-20 展厅图片 smoke gate 中文路径解码门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 的展厅图片 smoke gate 需要从远端 MySQL 读取 `infra_file.path`、`path LIKE 'showroom/%'` 或其他可能包含中文的文件路径，再在本地 PowerShell/Node/HTTP 客户端拼接 URL。
- Preflight check: 发布脚本不得直接使用远端 MySQL stdout 中的中文路径文本；SQL 应返回 `HEX(path)` 或等价字节安全载体，本地显式按 UTF-8 解码，再用 `[uri]::EscapeDataString` 或等价方法逐段 URL 编码。对应契约测试必须覆盖中文路径样例、`showrooms[].products` 发布态索引和代理返回 `image/jpeg`。
- Blocker: smoke gate 返回 JSON/404 而非图片、URL 中出现乱码或 `%EF%BF%BD`、PowerShell 子进程无法证明 stdout 按 UTF-8 还原，或测试只覆盖 ASCII 路径。
- Verification: `python -m pytest scripts/tests/test_deploy_precheck_report_contract.py scripts/tests/test_showroom_release_sql_contract.py` PASS；正式服发布后核 `.env IMAGE_TAG`、backend/frontend image tag、health、Website `/showroom` HTTP 200、受保护展厅图片代理 HTTP 200 `image/jpeg`，并用 Playwright 真实展厅验证英文 `Owner Company` / `License Holder` 为 `int-medical`。
- Forbidden action: 不得跳过图片 smoke gate、手工改服务器文件、手工回填媒体 URL、修改受保护 `infra_file_config.id=28` / `showroom/%` 默认媒体域，或把 200 JSON 响应当作图片成功。
- Evidence: `doc/tasks/20260720-prod-showroom-int-medical-publish/`；维护仓提交 `aba2b9f`；releaseTag `release-20260720-showroom-int-medical-full-r260720p-r2`；正式服 operation `op-2026-07-20T133237626561400Z-df502144-11e9-48a7-92d5-3efa4cbf9f5a`。

## 2026-07-24 GitHub 推送前历史大文件门禁

- Trigger: 将维护仓推送到 GitHub、迁移远端、首次初始化远端仓库，或提交/保留发布 evidence、operation JSON、构建结果 JSON、压缩包、日志归档等可能超过 GitHub 限制的文件。
- Preflight check: 推送前扫描已提交历史中的 blob 大小，至少确认没有超过 GitHub 100 MB 单文件限制的对象；对发布 evidence 只提交必要摘要和可复现索引，超大原始结果应保存在任务外部受控位置并记录路径/校验，不直接进入 Git 历史。
- Blocker: `git push` 返回 `GH001: Large files detected`、`pre-receive hook declined`，或本地历史扫描发现任一 blob 超过 100 MB；此时必须停止推送并取得用户明确授权后再选择历史重写、Git LFS 迁移或快照分支方案。
- Verification: 记录 `git ls-tree -l` 或等价历史扫描结果、目标远端 URL、分支、失败/通过的 `git push` 退出码；修复后再次运行大文件扫描并确认 `git push` 成功。
- Forbidden action: 不得强推、静默改写历史、自动迁移 Git LFS、创建无历史快照分支替代原推送，或删除 evidence 文件后宣称已保留完整历史，除非用户明确授权该具体方案。
- Evidence: `doc/tasks/20260724-push-maintenance-github/`；推送 `int_main` 到 `https://github.com/jiazeyu1987/IntRuoyiMaintance.git` 时，GitHub 拒绝已提交文件 `doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v5-result.json`，本地 blob 大小 `390728434` bytes，远端报告 `372.63 MB`。

## 2026-08-01 required SQL seed 列级 collation 门禁

- Trigger: `publish-test` / `promote-prod` / `promote-backup` 执行 DCC 分类、匹配规则、Codex 测试项或其他 seed SQL，临时表字段会与多个真实表文本列比较。
- Preflight check: 发布前不仅检查临时表 `DEFAULT CHARSET/COLLATE`，还必须读取真实目标列的 `information_schema.COLUMNS.COLLATION_NAME`；同一 seed 临时表如果同时比较 `dcc_file_category.name`、`dcc_file_category_match_rule.match_text`、`match_type` 等列，必须按目标列分别声明列级 `COLLATE`。
- Blocker: 静态测试或真实库只读检查发现 seed 临时列使用统一默认 collation，但目标列 collation 不一致；或远端 MySQL 报 `ERROR 1267 Illegal mix of collations`，尤其是 `utf8mb4_unicode_ci` 与 `utf8mb4_0900_ai_ci` 混用。
- Verification: 目标 SQL 测试必须断言列级声明；发布前运行相关 pytest 和 migration policy gate；发布后核 operation SUCCESS、manifest sourceRepos dirty=false、release lock APPLIED、migration failed/running=0。
- Forbidden action: 不得手工修改测试库默认 collation、手工更新 release lock / migration 状态、删除 seed 数据或复用失败 releaseTag。
- Evidence: `doc/tasks/20260801-head-test-only-release/execution-log.md`；`release-20260801-frozen-dcc-category-collation-r260801d-r1` 因表默认 collation 不足仍失败，最终 commit `f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce` 以列级 collation 修复并发布 `release-20260801-frozen-dcc-column-collation-r260801e-r1` 成功。

## 2026-08-01 release worktree ignored 依赖残留清理门禁

- Trigger: 发布 worktree 执行过前端 dependency restore、`pnpm build:test`、运行控制台 build 或其他会生成 ignored 目录的步骤后，执行 closeout/worktree 删除。
- Preflight check: `git worktree remove --force` 后必须同时检查 Git 注册、物理根目录、state dir 和进程引用；若物理目录仍在，先确认路径在本任务 allowlist 内、无 `.git` 注册、无外部进程引用，再清理 ignored `node_modules` / runtime 残留。
- Blocker: Git 注册已消失但物理目录仍存在；目录在 allowlist 外；进程命令行仍引用待删路径；或 cleanup 证据只记录 `git worktree list` 而未记录物理路径。
- Verification: closeout 证据必须包含每个任务路径 `existsAfter=false`、worktree list 不含本任务 token、48181 仍由主维护路径进程提供 health=UP。
- Forbidden action: 不得把 `Directory not empty` 忽略为成功；不得删除无关并发 worktree；不得在运行控制台仍指向 release worktree 时删除该路径。
- Evidence: `doc/tasks/20260801-head-test-only-release/worktree-cleanup-r260801e-r1.json`；r260801a/r260801b Git 注册已清除后，物理目录因 ignored `node_modules` 和 pnpm 长路径残留，需要固定路径白名单和 Windows 长路径前缀清理。
- 2026-08-03 追加证据：`doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/` closeout 中，r260803b 维护/app release worktree 已 clean，但 `git worktree remove --force` 仍因构建产物返回 `Directory not empty`；维护目录需先确认 Git 已注销、路径在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b` 下，再清只读属性后删除；app release 目录因 pnpm 断链/权限需用 symlink-safe 删除并复核 `existsAfter=false`。

## 2026-08-02 r260802b release worktree 来源、state-dir 与 schema-first 验收门禁

### Trigger

HEAD-only 构建发布在维护仓或主程序仓主工作区 dirty，且需要启动本地 runtime-control、轮询长时间 build/publish operation、查询远端 release lock / migration 状态。

### Preflight check

- `runtime-control.local.yaml` 必须显式指向本轮 clean app worktree 的 backend/frontend，并把 `state-dir` 放到本轮任务专用状态目录；构建后重新核 release worktree `git status --short`。
- build-release 后必须同时校验发布包 `manifest.json`、artifact SHA256、sourceRepos commit/dirty、前端镜像内 `release-info.json` 和本地 Docker image tag。
- 长时间 `RUNNING` operation 不能只看 summary；必须核 operation log 是否继续推进、本地子进程是否存在、远端 `.env`/容器是否已变化。
- 查询 `infra_release_operation_lock`、`infra_release_migration` 等远端表前先 `DESCRIBE` 或用已验证 schema 证据；禁止硬编码历史列名。

### Blocker

- manifest sourceRepos `dirty=true`、commit 与冻结 HEAD 不一致、artifact hash 缺失或 mismatch。
- runtime-control state/log/cache 污染 release worktree，且不能清理到 clean。
- operation 长时间 RUNNING 且日志不推进、发布锁被本轮目标占用或远端实际状态无法确认。
- 远端 SQL 出现 `Unknown column 'lock_key'`、`Unknown column 'updated_time'` 等 schema mismatch 且未先做 schema-first 修正。

### Verification

- 任务记录包含 worktree 路径、目标 HEAD、state-dir、build operation、publish operation、manifest validation、image release-info、operation final、远端 schema describe、release lock、migration status 和运行态 JSON。

### Forbidden action

- 禁止在主工作区 dirty 时直接构建。
- 禁止把 `git worktree list` 或 operation summary 当作唯一证据。
- 禁止在 release lock 查询失败后跳过 lock/migration 验收或手工标绿。

### Evidence

- `doc/tasks/20260802-0958-head-test-only-release/execution-log.md` I002、I004、I007、I009；releaseTag `release-20260802-intmain-head-test-r260802b-r1`；`remote-schema-describe-r260802b-r1.txt` 证明当前锁表使用 `target_environment`、`release_tag`、`status` 字段。

## 2026-08-02 发布脚本 manifest/changeSet 生成门禁

### Trigger

修改或执行 `publish-int-ruoyi.ps1` 的 `build-release`，尤其涉及 `sourceRepos`、`changeSet`、`release-info.json`、Codex 变更说明、空 Git 变更、`NasConfigPath` 或临时 release worktree 提交。

### Preflight check

- 目标 pytest 至少覆盖 `source_repo_identity`、`codex_command_resolver`、`release_change_set`、`empty_git_change_facts` 和 `build_release_writes_frontend_release_info`。
- `sourceRepos` 读取必须兼容普通对象和 `System.Collections.IDictionary` / `[ordered]`；不得只读 `PSObject.Properties`。
- Codex CLI 解析必须优先 `.cmd` / `.exe` 或 native `Application`，不能把 `codex.ps1` 直接交给 `ProcessStartInfo.FileName`。
- 直接执行发布脚本前必须显式确认 `NasConfigPath`，缺失时应在 Maven/Vite/Docker 长构建前 fail fast。
- 空 Git change facts 必须作为合法场景处理，不能因 mandatory collection binding 在函数体前失败。
- 前端 release-info 必须复用 manifest changeSet，至少包含当前 releaseTag、sourceRepos 和 `changeSet.gitChanges`。
- 发布脚本修复应先合入主 `int_main` 或已注册稳定 worktree，再创建新的 clean release worktree；不要从 detached release worktree 或未注册运行 profile 的临时分支直接作为最终发布源。

### Blocker

- build-release 结束后缺少 `manifest.json`、`release-manifest.json` 或 image tar。
- manifest sourceRepos 无法读取 pathRole/name/commit/dirty，或任一 source repo `dirty=true`。
- Codex command resolver 返回 `.ps1` 且无 `.cmd` / `.exe` 替代。
- 前端 release-info 没有 `changeSet.gitChanges`，导致运行控制台版本说明无法证明变更内容。
- release script 修复只存在于临时 dirty worktree，尚未进入目标 `origin/int_main`。

### Verification

- 记录每个失败 releaseTag 的判废原因；修复后使用新 releaseTag 重新 build。
- 记录目标 pytest GREEN、`git diff --check`、目标提交、clean worktree 状态、manifest sourceRepos、frontend release-info changeSet 和最终远端 release-info。
- 临时 worktree 有未提交改动时，比对其 diff 是否已经进入目标 HEAD；未确认前不得删除。

### Forbidden action

- 禁止复用缺 manifest、缺 NAS upload、缺 gitChanges 或 operation 非成功的 releaseTag。
- 禁止把 local manifest 存在解释为 build-release 成功；脚本退出码、operation 成功和 NAS/manifest 证据必须一致。
- 禁止把 detached worktree 的暂存改动静默遗弃；必须确认已进入目标提交或明确阻塞。

### Evidence

- `doc/tasks/20260802-commit-feedback-fix-test-release/`；失败 releaseTags `r260802c-r1/r2/r3`、`r260802d-r1`、`r260802e-r1`、`r260802f-r1`、`r260802g-r1`；最终源提交 `f0c34dfed910f52f9c03b401e976cbd2d0424e00` 和 releaseTag `release-20260802-feedback-fix-test-r260802h-r1` 通过 manifest、release-info 和测试服运行态验证。

## 2026-08-03 发布成功后主线合回必须检查并发索引门禁

- Trigger: 发布修复来自临时 app worktree 或 fix worktree，发布成功后需要把修复提交合回主程序 `int_main` 并清理 worktree。
- Preflight check: 合回前先检查目标主线 `git diff --cached --name-only`、`git status --short -- <task files>`、目标文件是否已有非本任务 hunk；若同一文件有并发未提交内容，只能做 hunk 级比对，不能整文件暂存。
- Blocker: 目标主线存在非本任务已暂存文件；目标文件同时包含非本任务 hunk；`.git/index.lock` 或后台 `git status` 进程正在占用 index；全量 migration gate 被当前主线其它未完成 SQL 或缺元数据阻塞；提交会混入其它任务内容。
- Verification: 记录主线 branch、HEAD、cached 文件列表、目标文件 diff、索引级 hunk 暂存方式、本任务聚焦测试结果、fix commit 与主线目标文件 diff 为空，以及 release/fix worktree 最终删除结果。
- Forbidden action: 禁止为了收口而整文件 `git add`、提交并发暂存文件、重置/清空别人的 index、删除未合回修复 worktree，或把测试服发布成功等同于主线收口完成。
- Evidence: `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/execution-log.md` P006/P007；`E:\IntRuoyi` 的 `int_main` 曾有并发 staged/dirty，且 `20260513_dcc_base_schema.sql` 有非本任务 hunk；最终仅移出非本任务暂存文档、用 index patch 暂存菜单 hunk，提交 `6b1fd19eb` 只包含本任务两文件，聚焦 pytest `15 passed`，fix/release worktree 已在 48181 恢复主路径后清理。

## 2026-08-06 后端 Spring context smoke 与多构造函数 Bean 门禁

- Trigger: 构建发布包、`publish-test`、`promote-prod` 或 `promote-backup` 会部署后端镜像，且后端新增/修改 `@Service`、`@Component`、`@Controller` 或构造器注入类。
- Preflight check: build-release 前至少运行一个后端 Spring context smoke，或静态扫描 Spring bean 类：同一 bean 存在多个构造函数时，必须有唯一 `@Autowired` 构造函数或明确无参构造函数；测试专用构造函数不得让生产构造器注入变得不明确。
- Blocker: 后端日志或 smoke 测试出现 `UnsatisfiedDependencyException`、`BeanCreationException`、`No default constructor found`、`Failed to instantiate`，或静态扫描发现多构造函数 Spring bean 没有显式注入构造函数。
- Verification: 记录 smoke 命令、目标类清单、Maven/ArchUnit/静态检查结果；发布后仍必须核 backend health=`UP`，不能只看 Maven package 成功。
- Forbidden action: 不得把 Maven compile/package 通过等同于后端可启动；不得在测试服 health 失败后手工改 release lock/migration 或复用失败 releaseTag。
- Evidence: `doc/tasks/20260806-head-test-only-release/`；`release-20260806-intmain-head-test-r260806b-r2` build-release 成功但 publish-test health readiness 失败，后端日志显示 `MesTeamLeaderProcessConfigServiceImpl` 有 public 生产构造函数和 package-private 测试构造函数但缺显式 `@Autowired`，Spring 报 `No default constructor found`。2026-08-06 修复后追加证据：`spring-constructor-gate-r260806c.json` 显示同一类 `constructorCount=2` 且 public production constructor 已有 `@Autowired`，随后 `release-20260806-intmain-head-test-r260806c-r1` publish-test 与 backend health 均通过。

### 阶段补充：后端 runtime smoke

1. `阶段：build-release 前`
2. `必查项`：后端 Spring context smoke 或多构造函数 Spring bean 静态检查；新增构造器注入服务必须覆盖运行态启动。
3. `推荐命令`：优先项目内已有 Maven/ArchUnit smoke；无现成命令时先补测试，不用测试服发布代替 smoke。
4. `Fail Fast`：出现 `No default constructor found`、`UnsatisfiedDependencyException` 或 smoke 启动失败时停止构建发布。
5. `必须记录`：目标类、构造器数量、注入标注、smoke 命令、失败 releaseTag 和后端日志证据。

## 2026-08-08 clean release worktree 本机 runtime-control 配置门禁

- Trigger: 维护仓主工作区 dirty，必须从 clean release worktree 构建维护控制台并通过运行控制台执行 `build-release`；clean worktree 中缺少被 `.gitignore` 排除的 `config/runtime-control.local.yaml`。
- Preflight check: 从主维护目录复制本机 runtime-control local config 到本轮维护 release worktree 后，必须显式改写 `repo-root`、`frontend-root`、`ops-root` 和 `state-dir`：前两者指向本轮 app clean worktree，`ops-root` 指向本轮维护 worktree，`state-dir` 指向本轮专用 state 目录；随后运行 preview gate 验证脚本路径和 repo roots。
- Blocker: local config 缺失；任一路径仍指向主工作区、旧 worktree 或主维护 state；复制配置后 Git 状态出现非 ignored dirty；preview gate 中 repoRoot/frontendRoot 不是本轮 clean worktree。
- Verification: 记录配置关键路径只读输出、release worktree `git status --porcelain` 为空、build-release preview gate 全 true、manifest sourceRepos commit 等于冻结 app HEAD 且 dirty=false。
- Forbidden action: 禁止直接用主维护目录运行控制台构建 dirty 主程序；禁止让本轮发布写入主维护 runtime-control state；禁止把 local config 提交进仓库。
- Evidence: `doc/tasks/20260808-head-test-only-release/execution-log.md`；r260808a 配置写入后 `repo-root=D:/IntRuoyiWorktree/r260808a-release-app/IntRuoyiBackend`、`frontend-root=D:/IntRuoyiWorktree/r260808a-release-app/IntRuoyiFronted`、`ops-root=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260808a/m/ops`、`state-dir=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260808a-state`，build preview gate 通过。

## 2026-08-08 build.ps1 生成 runtime 目录清理门禁

- Trigger: 在维护 release worktree 中运行 `scripts/build.ps1` 后，构建成功但 `git status --porcelain` 出现未跟踪 `runtime/`。
- Preflight check: 构建后立即复核维护 release worktree dirty 状态；若仅有本次生成的 `runtime/`，先做绝对路径边界校验、确认目标位于本轮维护 worktree 且不含 `.git`，再清理并复核 clean。
- Blocker: dirty 项不止本次生成目录；目标路径不在本轮 worktree；目录含 `.git`；有非本任务进程引用；清理后 worktree 仍 dirty。
- Verification: 记录 jar hash、Maven tests 结果、删除路径、清理方式、清理后 `git status --porcelain` 为空。
- Forbidden action: 禁止用 dirty release worktree 继续 build-release；禁止宽泛删除 worktree 根或 node_modules；禁止删除未确认归属的并发任务文件。
- Evidence: `doc/tasks/20260808-head-test-only-release/execution-log.md`；维护构建 26 tests passed、jar SHA256=`dd47d207373e9bd025f4136fab0cf6b693ac02fb362b7a931849da4318f2eec6`，清理 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260808a\m\runtime` 后 worktree clean。
## 2026-08-10 pnpm 真实子进程完成与 ignored-builds 清零门禁

- Trigger: clean release worktree 使用 Corepack/pnpm 恢复主程序或维护控制台前端依赖，尤其是外层 shell/工具会异步承载子进程，或 `pnpm ignored-builds` 报出 esbuild、vue-demi、sharp 等待批准脚本。
- Preflight check: 同一 worktree 只允许一个依赖恢复进程；以实际 pnpm/node 子进程退出、命令退出码、关键二进制存在和 `pnpm ignored-builds` 为空共同判定完成。需要批准脚本时使用明确 allowlist 执行 `pnpm rebuild --pending`，随后移除临时配置并复核 `git status --porcelain` 为空。
- Blocker: 外层 corepack/shell 已返回但目标 worktree 仍有 pnpm/node/esbuild 子进程；同一 worktree 有两个安装进程；`ignored-builds` 非空；关键可执行文件缺失；或临时批准配置/测试 runtime 文件让 release worktree 变脏。
- Verification: 记录进程树和命令行归属、真实退出码、ignored-builds=`none`、关键二进制检查以及构建前后 worktree clean；维护控制台还需运行 `scripts/build.ps1` 并核前端 build、Maven tests 和 JAR hash。
- Forbidden action: 不得把承载进程返回当成依赖完成，不得在同一 worktree 并发重启 install，不得跳过 ignored-builds，不得把临时 `onlyBuiltDependencies` 或构建测试生成的 runtime 文件提交或纳入发布包。
- Evidence: `doc/tasks/20260809-head-test-only-release/execution-log.md`；r260809a 主程序安装发现两个遗留 Node 子进程，改为单一真实 pnpm 后约 11 分 9 秒完成；主程序 7 个及维护前端 2 个 ignored builds 清零，两个 worktree 最终 clean，维护 Maven tests 26 passed。

## 2026-08-11 r260811a release worktree 依赖、manifest 与发布日志门禁

- Trigger: 从 dirty 主工作区冻结 HEAD 到 clean release worktree，并在 clean worktree 构建维护控制台、主程序前端和测试发布包。
- Preflight check: 新 app release worktree 在 build-release 前必须确认 `IntRuoyiFronted/node_modules/.bin/cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 存在；`pnpm ignored-builds` 必须清零；manifest 校验统一使用 `ops\release\validate-release-manifest.ps1 -PackagePath <package>`，不要手写 `-ManifestPath`。
- Blocker: node_modules 缺失、cross-env/vite/vue-tsc 缺失、ignored-builds 非空、manifest validator 参数不匹配、sourceRepos commit/dirty 与冻结 HEAD 不一致、发布日志未经脱敏。
- Verification: 记录 app/frontend dependency install 结果、ignored-builds=None、worktree clean、build operation SUCCESS、`MANIFEST_VALIDATION_PASSED`、release-info sourceRepos dirty=false、publish-test 脱敏日志 secret scan=0。
- Forbidden action: 禁止用 r1 失败包继续 publish-test；禁止复用无 manifest 或 manifest 校验无效的包；禁止提交 raw publish log 中的 `mysql -p...` 密码形态。
- Evidence: `doc/tasks/20260811-head-test-only-release/execution-log.md` I005-I007；最终 releaseTag `release-20260811-intmain-head-test-r260811a-r2`。

## 2026-08-13 releaseTag 占用、脱敏辅助与隔离控制台完整配置门禁

- Trigger: 从 clean release worktree 启动 runtime-control 执行 build-release/publish-test，或恢复中断后的长 operation 并读取脱敏日志。
- Preflight check: build submit 前通过 release-status/NAS package candidate 检查目标 releaseTag 目录不存在；隔离配置必须一次复制并 presence-check `release-package` 与 `backup-ops` 两个块，同时覆写本轮 repo/frontend/ops/state 路径；日志脱敏函数先用含 `MYSQL_PWD=`、`mysql -p`、`password=`、`nas-password` 的样例做编译与替换测试。
- Blocker: NAS 已存在同名 releaseTag；任何 local config 路径指向主工作区/旧 worktree；任一 NAS 必填项缺失；脱敏函数编译失败或输出仍含凭据形态。
- Verification: preview gate、config presence summary、两个 release worktree clean、releaseTag candidate absent、脱敏样例 secret scan=0；构建后 manifest sourceRepos commit/dirty 和 artifact hash 全通过。
- Forbidden action: 禁止删除/覆盖 NAS 既有发布包以复用 tag；禁止只复制 release-package 而省略 backup-ops；禁止对脚本源码运行宽泛凭据替换；禁止把 raw operation log 提交为证据。
- Evidence: `doc/tasks/2026-08-11-test-only-release-head/execution-log.md`；r260812b-r1 因同名 NAS 包存在失败，r2 使用相同冻结 clean 输入成功；发布后页面验收因 backup-ops 缺失首次阻塞，补齐配置后通过。

## 2026-08-16 code-only 迁移依赖闭包不能只验证 ID 存在

- Trigger: code-only 发布会跳过 `type=data` required SQL，但 Manifest 中其它可执行迁移通过 `dependsOn` 直接或传递依赖它，或依赖它建立的菜单/配置/权限真实状态。
- Preflight check: policy gate 除了验证 migrationId 存在、无环和 type 合法，还必须按实际 publishScope 与 target preflight action 计算过滤后执行图；任何 APPLY 迁移不得依赖 preflight=APPLY 但会被 scope 过滤的 pending 节点。对于 SQL 中 `SIGNAL` 的固定 ID、parent/path、唯一键或状态断言，应在服务器写入前从冻结 SQL 生成只读 live-state probe，并与 migration ledger 对照。
- Blocker: 出现 `APPLY executable -> pending filtered data` 依赖路径；ledger 表示已应用但真实状态不满足后续迁移；或无法证明正式迁移会在同一新 releaseTag 内自给前置状态。
- Verification: 合同测试覆盖直接和传递依赖、code-only 过滤、最小依赖链输出；发布前证据包含 Manifest 条目、live-state 查询、ledger/真实值差异。修复必须提交后用新冻结 HEAD 和新 releaseTag 完整重建。
- Forbidden action: 禁止手工补数据库后继续失败 tag；禁止修改 ledger、复用失败包、把 `type=data` 随意改成其它类型绕过过滤，或因旧服务 health/HTTP 正常而判发布成功。
- Evidence: `doc/tasks/20260816-test-only-release-head/execution-log.md` P-016；负责移动菜单的 data migration 被 code-only 跳过，后续 menu migration 在真实父级断言处失败。

### 可自动化实现

1. 从 Manifest `migrationPlan` 建立 `migrationId -> {type, dependsOn}` 图，并按 publishScope 标记 executed/skipped。
2. 对每个 APPLY 节点遍历祖先；命中 preflight=APPLY 且 scope 将过滤的节点时立即输出最小路径并使 gate 非零退出。
3. 对包含 `SIGNAL` 的 menu/config/permission migration 输出待核 live-state 字段清单；无法自动解析时要求显式 `requiredPreconditions`，不得静默跳过。
4. publish-test 失败后自动生成脱敏状态摘要，包含 lock/migration counts、env/compose/actual images、health/HTTP/release-info；原始 secret-bearing operation log 不进入任务证据。

## 2026-08-21 r260821h-r4 构建 warning、Spring context 与失败 env 漂移

### 门禁摘要

- Trigger: build-release 生成 Docker warning，或 publish-test 在 route snapshot 运行报告阶段失败，尤其出现 `InvalidDefaultArgInFrom`、`No default constructor found`、`Application run failed`、`.env IMAGE_TAG` 与 actual image 不一致或 raw MySQL password command。
- Preflight check: 构建前扫描 Dockerfile `ARG/FROM` 契约；对 `@Component`/`@Service` Bean 执行 Spring context smoke 或多构造函数静态扫描；发布脚本 logger 先通过 `mysql -p`/`password=`/`token=` 样本脱敏测试；远端 `.env` 写入前保存脱敏 hash、旧内容来源和恢复路径。
- Blocker: warning 未解释、Spring Bean 多构造函数无唯一显式 `@Autowired`、raw log 命中 secret、或无法证明 publish-test 失败后可以恢复旧 `.env`/compose/actual image 一致性。
- Verification: 记录 Docker warning 摘要、Bean/构造函数证据、logger secret scan、operation final、`.env`、`docker compose config --images`、`docker compose images`、`docker inspect`、容器状态、Actuator、frontend HTTP、release-info、lock/migration。
- Forbidden action: 不得把 Maven package 通过当作 Spring runtime 可启动；不得因旧容器 health/HTTP 200 判成功；不得猜测旧 tag 回滚、手工改 release lock/migration、重试失败 releaseTag 或提交 raw operation log。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P026-P029；publish operation `op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b`；releaseTag `release-20260821-intmain-head-test-r260821h-r4`。

### 阶段 1：build-release

1. 阶段名称：构建运行契约。
2. 必查项：Dockerfile 基础镜像 ARG/FROM、Spring Bean 构造函数、维护/app release worktree clean、发布 logger 脱敏。
3. 推荐命令：`rg -n "^FROM |ARG " <backend> <frontend> -g "Dockerfile*"`；Spring context smoke；`docker build` warning 摘要采集；secret-pattern scan。
4. Fail Fast：`InvalidDefaultArgInFrom` 未解释、`No default constructor found`、logger 输出 raw secret 或 worktree 变脏。
5. 必须记录：warning、目标 Bean、测试命令、退出码、worktree、JAR/image digest 与 redaction scan。

### 阶段 2：publish-test 失败收束

1. 阶段名称：失败态版本一致性。
2. 必查项：同一 operation final、`.env IMAGE_TAG`、compose 解析镜像、实际容器镜像、容器 state、health、frontend HTTP、release-info、lock/migration。
3. 推荐命令：`docker compose config --images`、`docker compose images`、`docker inspect`、`curl -fsS http://127.0.0.1:48081/actuator/health`、`curl -fsS http://127.0.0.1:8081/release-info.json`。
4. Fail Fast：env/compose/actual images/release-info 漂移；失败 tag 已写入部分迁移状态；旧 `.env` 基线不可证明。
5. 必须记录：现象、阶段、影响、原因判断、处理动作、结果、是否可前置、是否可自动化、下次避免；失败 tag 判废且不重试。

## 2026-08-22 route snapshot BACKFILL blocker 与异步 operation 状态收束

### 门禁摘要

- Trigger: 后端 route snapshot runner 已修复构造注入并通过单测，但真实 BACKFILL/READINESS 报告仍返回 blocker；或 `docker compose run --rm` 临时 runner 不退出、operation JSON 长期保持 `RUNNING`。
- Preflight check: build-release 前运行真实 Spring context smoke；publish-test 前确认报告要求 `status=READY` 且 `blockerCount=0`；命令执行器必须在读取 stdout 时也可中断超时，并在异常/强制清理时写入明确 FAILED/STOPPED；logger 先做 secret redaction contract test。
- Blocker: report `BLOCKED`/`blockerCount>0`；临时 runner 不退出；operation 没有明确终态；raw log 含 MySQL 密码或其它 secret；失败 tag 产生部分 migration state 且无法证明恢复基线。
- Verification: 记录 smoke 命令、报告摘要、runner `docker inspect`、operation state/API、脱敏日志 scan、live image tags；只有 operation=`SUCCESS` 才能进入运行态验收。
- Forbidden action: 禁止手工改 operation 状态冒充成功；禁止修改业务数据、migration ledger 或 release lock 来消除 blocker；禁止重复提交同一 releaseTag；禁止提交 raw log。
- Evidence: `doc/tasks/20260821-test-only-head-release/execution-log.md` P038-P043；releaseTag=`release-20260822-intmain-head-test-r260822a-r2`。

### 阶段 1：构建与运行报告

1. 必查项：Spring Bean 构造函数、context smoke、Docker warning、route snapshot report contract、logger redaction contract。
2. 推荐命令：Maven `ApplicationContextRunner` smoke；report JSON parser；`rg`/结构化 secret scan；Docker runner command/volume 预览。
3. Fail Fast：context 失败、report 非 READY、blockerCount 非 0、secret scan 命中或 worktree 变脏。
4. 必须记录：commit、worktree、releaseTag、report fields、warning、scan result 和 artifact hash。

### 阶段 2：异步命令执行器

1. 必查项：stdout 读取与 timeout 是否可中断；子进程退出码；异常时 operation state 是否落盘；临时 runner 是否 guaranteed cleanup。
2. 推荐命令：维护控制台命令执行器回归测试；模拟 stdout 长时间不 EOF、子进程非零退出和强制清理；检查 operation 状态文件更新时间。
3. Fail Fast：超时只在 stdout EOF 后触发、异常路径留下 RUNNING、runner 残留或 operation API 无终态。
4. 必须记录：命令执行器线程/子进程状态、timeout、operation final、清理结果和不重复操作结论。

## 2026-08-22 route snapshot BACKFILL blocker 的构建发布前置门禁

- Trigger: 新代码已通过 Spring context smoke，但 build/release 依赖的 required SQL 会在测试服执行 route snapshot BACKFILL/READINESS。
- Preflight check: 将 route snapshot report contract 纳入 build/release 计划；远端写入前用只读报告聚合 blocker reason、租户分布和样本结构；对迁移注释中“禁止从当前投影推断”执行静态合同检查。
- Blocker: 历史快照存在结构或身份 blocker；受保护租户数据需要修改；报告聚合无法证明零 blocker；或发布脚本没有明确的失败态恢复边界。
- Verification: 只读证据必须与 manifest/sourceRepos/releaseTag 绑定；修复不得改验证器放宽约束，必须有正式数据治理方案、备份/回滚证据、BDD/TDD 或迁移合同测试，并从新冻结输入重建。
- Forbidden action: 禁止把数据 blocker 误判为构建问题后改 validator；禁止只为过发布在包里排除迁移、从当前表补历史 snapshot、或把 source tenant 当作可修改测试数据。
- Evidence: `doc/tasks/20260821-test-only-head-release/verification-report.md` 的 Continued Diagnosis；r260822a-r2 report evidence。

## 2026-08-23 冻结 HEAD 的 Vue SFC 完整性门禁

- Trigger: 仅测试服发布、clean release worktree 前端构建、Vite 报 `At least one <template> or <script> is required`，或冻结提交中出现 tracked 0 字节 `.vue` 文件。
- Preflight check: 创建并核对冻结 app worktree 后、恢复依赖前，扫描 tracked `.vue` 文件；每个文件必须非空且至少包含 `<template>` 或 `<script>`。扫描结果必须绑定冻结 commit 和绝对 worktree 路径。
- Blocker: 任一 tracked Vue SFC 为 0 字节、同时缺少 `<template>` 与 `<script>`、文件来自未提交主工作区修复，或无法证明扫描对象就是冻结 HEAD 时立即停止；不得进入依赖安装、前端 build、`build-release` 或 `publish-test`。
- Verification: 记录 `git cat-file -s HEAD:<path>`、worktree file length、SFC 扫描总数/失败数、`git status --porcelain --untracked-files=all` 和冻结 commit；修复后必须提交到主线并由新 worktree/new releaseTag 重新执行门禁。
- Forbidden action: 禁止从 dirty 主工作区复制非空文件覆盖 release worktree，禁止生成空壳组件、跳过前端 build、复用旧包/旧 manifest/旧 releaseTag，或在构建源不完整时继续服务器写入。
- Evidence: `doc/tasks/20260823-test-only-head-release-r3/verification-report.md`；冻结 app commit=`0002767c0486f11d82bd82666bf8b0f164aee597`，`TrainingRulesReadonlyTab.vue` blob/file size=`0`。
- Evidence: `doc/tasks/20260828-test-only-release-head/verification-report.md`；冻结 app commit=`10fecf5caf929d47a385bcbf92fb410da312f8c2`，同一 SFC blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`，size=`0`，构建前 fail fast。

### 阶段补充：前端源码静态完整性

1. 阶段名称：release worktree 创建后、依赖恢复前。
2. 必查项：tracked `.vue` 非空、SFC 至少含 template/script、worktree clean、HEAD 与冻结提交一致。
3. 推荐命令：`git -C <app-worktree> ls-files 'IntRuoyiFronted/**/*.vue'` 配合 `git cat-file -s HEAD:<path>`，或使用等价的 UTF-8 安全结构扫描脚本。
4. Fail Fast：空文件、SFC 结构缺失、worktree dirty、HEAD 不一致。
5. 必须记录：冻结 commit、绝对路径、失败文件数和文件列表；未通过时明确 build/publish 未执行。

## 2026-08-24 发布前置门禁与冻结 worktree 依赖复用实现

### 门禁摘要

- Trigger: `build-release`、维护控制台构建或 required SQL 发生变更，尤其出现 MySQL `ERROR 1137`、`ERROR 1267`、`No default constructor found`、`cross-env`/`vite`/`vue-tsc` 缺失或同一 worktree 重复 `pnpm install`。
- Preflight check: 维护仓 `ops/release/release_sql_contract_gate.py` 对当前迁移基线（`20260801` 起）扫描同一 SQL 语句/表达式的 `tmp_*` 重复引用，并对与非临时表文本列等值比较的临时表要求显式 `COLLATE`；`spring_constructor_contract_gate.py --source-root <backend>` 扫描带 Spring Bean 注解的多构造器类；应用前端构建前检查 `package.json`、`pnpm-lock.yaml`、`node_modules/.bin/{cross-env,vite,vue-tsc}.cmd` 和 `pnpm ignored-builds`；维护构建统一调用 `scripts/prepare-frontend-dependencies.ps1`，按 package/lock SHA-256、Node/pnpm 版本和二进制清单复用 stamp。
- Blocker: SQL gate 报 `MySQL temp table reopen risk` 或 `temporary table collation must be explicit`；Spring gate 报多构造器且无唯一 `@Autowired`/无参构造；依赖输入、stamp、二进制或 ignored-builds 状态缺失/漂移；任何命令非零退出。阻塞发生在 Maven 或前端打包前，不进入服务器写入。
- Verification: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_spring_constructor_contract.py -q --basetemp <task-dir>`；PowerShell AST 解析三个脚本；记录 gate JSON/文本输出、冻结 backend/frontend worktree、commit 和 dirty 状态。当前依赖缺失时只允许一次 `pnpm install --frozen-lockfile`，成功后写入 ignored `node_modules/.release-dependencies.json`。
- Forbidden action: 禁止复用旧 releaseTag/旧 `node_modules`/旧产物掩盖 stamp 漂移，禁止把 Maven package 通过当作 Spring 可启动，禁止忽略 SQL gate、修改服务器/ledger 或吞掉命令异常。
- Evidence: 本任务 `doc/tasks/20260824-release-preflight-build-optimization/execution-log.md`；r7/r8/r9 发布失败日志中的 `ERROR 1267`、`ERROR 1137`、Spring 构造器和重复前端安装证据。

### 阶段补充：构建前执行顺序

1. 阶段名称：冻结 worktree 完整性与依赖状态。
2. 必查项：冻结 commit/clean、frontend SFC 完整性、依赖 stamp、required binaries、`pnpm ignored-builds`。
3. 推荐命令：`python -X utf8 ops/release/run-release-migration-policy-gate.py ...`；`python -X utf8 ops/release/spring_constructor_contract_gate.py --source-root <backend>`；`scripts/prepare-frontend-dependencies.ps1 -FrontendDir <frontend>`。
4. Fail Fast：任一 gate 非零、依赖状态不可证明、前端入口/lockfile 缺失或 worktree 漂移；不进入 Maven、Docker、`build-release` 或 `publish-test`。
5. 必须记录：gate 命令、退出码、输出摘要、依赖 stamp 哈希/版本、冻结路径和未执行的后续阶段。

### 根因修复规则

- Spring Bean 为测试增加辅助构造器时，生产注入构造器必须显式标注 `@Autowired`；只依赖“唯一构造器”推断会在构造器数量变化后退化为启动期 `No default constructor found`。
- MySQL 迭代扩展临时结果集时，禁止同一 `INSERT ... SELECT` 同时读取和写入同一 `tmp_*` 表；每轮先复制到独立 source 快照表，再写入目标表，并在过程末尾清理两者。
- 同一临时表在 `IF EXISTS` 的多个 `OR` 分支中重复读取时，拆成多个独立校验块，避免优化器触发 `Can't reopen table`；门禁通过不等于可以保留原 SQL 结构。
- Evidence: `64fa527f2`（后端 Spring/SQL 修复）、`13c7da2`（维护仓回归测试与任务证据）、`9cdbe89`（收尾记录）。

## 2026-08-28 rollback-migration 混入发布 SQL 根目录门禁

- Trigger: 仅测试服发布或 `build-release` 前，实际维护仓 `ops/release/run-release-migration-policy-gate.py` 扫描冻结 app worktree 的 `IntRuoyiBackend/sql/mysql`。
- Preflight check: 对发布扫描根下每个 `.sql` 文件确认首行是当前发布包 parser 可识别的 `release-migration` 元数据；rollback 专用脚本如果仍放在该扫描根内，必须先确认维护仓 Python gate、PowerShell parser、manifest 语义和契约测试均已正式支持。
- Blocker: 任一 SQL 首行为 `rollback-migration` 或其他非 `release-migration` 元数据，导致 gate 输出 `missing release-migration metadata`；或者尝试用 release worktree 未提交修改替换首行。
- Verification: 先冻结 gate JSON、目标 SQL 首行、目标 app commit 和 clean worktree 状态；正式修复后在主线提交，重新创建 release worktree，并重跑 `python -X utf8 <maintenance-worktree>\ops\release\run-release-migration-policy-gate.py --sql-root <app-worktree>\IntRuoyiBackend\sql\mysql --file-prefix sql/mysql --output <task-dir>\migration-policy-gate.json`。
- Forbidden action: 禁止把 rollback SQL 元数据缺失视为 code-only 可忽略事项，禁止手工编辑 release package/manifest，禁止跳过 migration policy gate 后继续 `build-release` 或 `publish-test`。
- Evidence: `doc/tasks/20260828-test-only-release-head/verification-report.md`；`20260822_mes_process_pool_active_order_completion_receipt_rollback.sql` 首行为 `-- rollback-migration: ...`，实际 ops gate 输出 `missing release-migration metadata`。

## 2026-08-24 r11 迁移临时表、operation 与构建身份门禁

### 门禁摘要

- Trigger: build-release/publish-test 长耗时、required SQL 使用临时表、运行控制台重启或需要从旧失败轮次继续发布。
- Preflight check: 固定 releaseTag、目标提交、maintenance/app worktree、控制台 config/state-dir/PID；运行 SQL temp-table self-read/reopen 与 collation gate；operation 必须有唯一最终状态；manifest 与前端 release-info 必须共同证明 commit/dirty/changeSet。
- Blocker: operation 进程退出后仍为 RUNNING、preview source root 指向旧 worktree、同一 SQL 语句重复读取 tmp_*、临时表字符集/排序规则未显式固定、manifest 或 release-info 无法证明冻结提交时立即停止，不发布服务器。
- Verification: 记录 operation final 与日志尾部、worktree HEAD/clean、manifest validator、package path、远端 .env/actual image/container/health/HTTP/release-info、release lock 最新状态和 migration FAILED/RUNNING 计数。
- Forbidden action: 禁止重复提交同一 operation、复用失败 releaseTag、手工重置 release lock、直接修改远端 env/ledger、把控制台 operation id 与数据库 release lock operation_id 强行当作同一字段、用 SSH 引号猜测替代真实报告。
- Evidence: 本任务 execution-log.md ISSUE-014/015、remote-runtime-r260823f10-r11.json、manifest-validation-r260823f10-r11.json；r7/r8/r9 的 ERROR 1267/1137 失败日志。

## 2026-08-29 publish-test required SQL 批量化与脱敏门禁

- Trigger: `publish-test` 包含大量 required SQL、日志显示逐文件 `scp` / 逐条 `ssh + mysql` 入账、迁移计划多数为 `SKIP_ALREADY_APPLIED`，或 operation log 可能打印 `mysql -p...` / `MYSQL_PWD=...`。
- Preflight check: `publish-int-ruoyi.ps1` 必须将 required SQL staging 后生成单个 tar 归档、一次上传到远端再解包；远端解包 SQL 数必须与本地计划数量一致；`SKIP_ALREADY_APPLIED` 迁移状态必须批量 upsert；`Invoke-SshCommand` / `Invoke-SshCapture` 的显示命令、输出和异常文本必须经过 secret redaction。
- Blocker: required SQL 仍逐文件 `scp`；`SKIP_ALREADY_APPLIED` 仍逐条远端 MySQL 写入；tar 不可用、归档为空或远端解包数量不一致；operation/task 日志命中明文 `mysql -p...`、`MYSQL_PWD=`、password/token/secret。
- Verification: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q` 覆盖归档上传、批量状态写入和 SSH 日志脱敏；PowerShell AST 解析 `ops\deploy\publish-int-ruoyi.ps1`；`git diff --check`；本机 `tar.exe`、`ssh.exe`、`scp.exe` presence check。
- Forbidden action: 禁止为节省时间跳过 required SQL、手工改 migration ledger、复用失败 releaseTag/旧包、降低 manifest/运行态验收标准，或提交 raw secret-bearing operation log。
- Evidence: `doc/tasks/20260829-optimize-test-release-pipeline/verification-report.md`；维护仓实现提交 `9c5d64f`（`任务: 优化测试服发布链路`）。

### 阶段补充：publish-test 耗时前移与批量化

1. 阶段名称：required SQL 上传前。
2. 必查项：本地计划 SQL 数、staging 目录 SQL 数、tar 命令可用、远端目标目录为空或已清理、归档解包数量一致。
3. 推荐命令：发布脚本内置 staging/tar/remote count gate；本机预检 `Get-Command tar,ssh,scp`；合同测试 `test_publish_script_uploads_required_sql_as_single_archive`。
4. Fail Fast：tar 缺失、归档为空、远端文件数不等于计划数、任一 SQL 文件路径无法映射。
5. 必须记录：releaseTag、计划 SQL 总数、归档路径、远端目录、解包数量和失败边界。
6. 优化规则：集中完整性校验通过后，不再在每个 APPLY 项前额外执行 `ssh test -f '$remoteSqlPath'`；缺文件由解包数量门禁或实际 `cat '$remoteSqlPath' | mysql` fail fast 暴露。
7. Evidence: `doc/tasks/20260829-optimize-required-sql-remote-verification/verification-report.md`；维护仓实现提交 `079c6a6`（`任务: 优化required SQL远端校验`）。

1. 阶段名称：migration state 入账前。
2. 必查项：`SKIP_ALREADY_APPLIED` 数量、批量 upsert SQL 行数、单文件执行状态仍保留独立 START/APPLIED/FAILED 证据。
3. 推荐命令：合同测试 `test_publish_script_batches_skip_already_applied_migration_state_updates`；operation log 检查 `Batch updating release migration state`。
4. Fail Fast：跳过态入账退化为逐条远端 MySQL 调用，或批量 SQL 不能证明每个 migrationId/status/checksum/sourceFile。
5. 必须记录：批量数量、目标状态、单条失败处理边界和迁移台账最终计数。
6. 优化规则：APPLY 成功路径可将远端文件检查、`RUNNING`、required SQL 执行、`APPLIED` 合并到单次 SSH 会话；SQL 失败必须由外层 catch 继续写 `FAILED` 并抛出，不得吞异常或标记成功。
7. Evidence: `doc/tasks/20260829-optimize-required-sql-apply-state-ssh/verification-report.md`；维护仓实现提交 `e4bc1e5`（`任务: 优化required SQL状态入账`）。

1. 阶段名称：发布日志脱敏。
2. 必查项：所有 SSH command/capture 输出路径、异常路径和 task 证据路径。
3. 推荐命令：合同测试 `test_ssh_command_logs_and_errors_are_secret_redacted`；secret-pattern scan operation log。
4. Fail Fast：日志或异常含 `mysql -p` 明文密码、`MYSQL_PWD=` 原值、password/token/secret 原值。
5. 必须记录：脱敏测试结果、scan 结果和被拒绝提交的 raw log 路径。

### 阶段补充：runtime-control ops 包上传

1. 阶段名称：ops runtime 上传前。
2. 必查项：本地 staging 必须包含 `linux`、`scripts`、`actions`、`config` 与 `script/deploy/manage-int-ruoyi-remote-root-disk.ps1`；staging 内不得包含 `backup-ops.secrets.json`；本机 `tar` 可用。
3. 推荐命令：合同测试 `test_publish_script_uploads_ops_runtime_package_as_single_archive`；PowerShell AST parse；本机 `Get-Command tar,ssh,scp`。
4. Fail Fast：仍对 `linux/scripts/actions/config` 多次 `Copy-ToServer`、ops tar 未生成、远端解包后关键文件缺失，或归档包含 secrets。
5. 必须记录：归档名、远端 `ops-runtime.tar`、关键文件校验、实现提交和未执行真实发布的边界。
6. 禁止做法：禁止为省时整目录删除 `$remoteOpsRuntimeDir`，避免误删远端 `config` 下现有 secrets；只能清理受控脚本目录和受控 deploy 文件后解包覆盖。
7. Evidence: `doc/tasks/20260829-optimize-test-release-ops-runtime-upload/verification-report.md`；维护仓实现提交 `f33a8ec`（`任务: 优化发布ops运行包上传`）。

## 2026-08-29 r260829j clean HEAD 构建、manifest 与 DCC SQL 合同门禁

### 门禁摘要

- Trigger: 仅测试服 HEAD 发布、dirty 主工作区发布、clean release worktree 构建、注册证 DCC required SQL、manifest/release-info/sourceRepos 校验、`cross-env.cmd`/`vite.cmd`/`vue-tsc.cmd` 缺失、`ERROR 1644` 注册证核心列合同或 CHECK 精确表达式失败。
- Preflight check: 每轮发布必须新建本轮专用 maintenance/app release worktree，记录两个 HEAD、路径和 `git status --short --branch`；构建前运行 Vue SFC 完整性、迁移策略、Spring constructor、注册证核心 SQL 静态契约和必要 Maven 合同；app 前端必须完成 `pnpm install --frozen-lockfile --reporter append-only`、`pnpm rebuild --pending`、`pnpm ignored-builds=None`，并验证 `node_modules\.bin\cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 存在；构建后用 JSON parser 和官方 validator 校验 manifest/sourceRepos/dirty/changeSet/release-info。
- Blocker: 任一 release worktree dirty、HEAD 与冻结记录不一致、manifest/sourceRepos/dirty/changeSet 不能绑定目标提交、前端依赖二进制缺失、`pnpm ignored-builds` 非空、注册证 required SQL 精确合同与目标 MySQL 8 规范化输出不一致，或试图从 dirty 主工作区直接构建。
- Verification: 保存 freeze JSON、构建前 gate 输出、Maven/JAR hash、build operation SUCCESS、`package-manifest-check*.json`、`validate-release-manifest.ps1` 输出、前端镜像内 `/usr/share/nginx/html/release-info.json`；任务日志只记录关键字段和 hash，不打印完整 manifest。
- Forbidden action: 禁止复用失败 releaseTag、旧 worktree、旧 manifest 或旧 node_modules；禁止在 release worktree 临时改 SQL/前端依赖后继续发布；禁止把 MySQL CHECK 语义相同但字符串不匹配的问题通过放宽断言或手工改库绕过；禁止输出完整 manifest 作为证据。
- Evidence: `doc/tasks/20260828-test-only-release-head/execution-log.md` 问题 30、34、37；app 提交 `d3f5d6f13603ae723357cd909022eb1652ab64c0`、`3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`；最终 releaseTag `release-20260829-frozen-head-test-r260829j-r1`；final gate `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\test-release-final-gate-r260829j-r1.json`。

### 阶段 1：冻结 worktree 与构建前 gate

1. 必查项：两个仓库当前分支、HEAD、dirty；本轮专用 release worktree 是否 detached clean；构建开始后是否固定目标提交。
2. 推荐命令：`git status --short --branch`、`git rev-parse HEAD`、`git worktree list --porcelain`、Vue SFC 完整性扫描、`run-release-migration-policy-gate.py --output <state>.json`、`spring_constructor_contract_gate.py --source-root <backend>`。
3. Fail Fast：主工作区 dirty 且未使用 clean worktree；release worktree dirty；gate 非零；目标提交、路径或 state-dir 无法记录。
4. 必须记录：目标提交、worktree 路径、构建目录、state-dir、releaseTag、各 gate 的 status/count。

### 阶段 2：前端依赖与维护控制台构建

1. 必查项：app frontend `package.json`/`pnpm-lock.yaml`、`node_modules\.bin` 三个关键命令、`pnpm ignored-builds`、tracked diff；维护控制台构建后的 JAR hash。
2. 推荐命令：`pnpm install --frozen-lockfile --reporter append-only`、`pnpm rebuild --pending`、`pnpm ignored-builds`、`Test-Path node_modules\.bin\cross-env.cmd`、`scripts\build.ps1`。
3. Fail Fast：关键二进制不存在、ignored-builds 非空、临时 `pnpm.onlyBuiltDependencies` 未恢复、维护构建后 release worktree 出现未解释 dirty。
4. 必须记录：依赖恢复结果、ignored-builds 输出、关键二进制检查、JAR SHA256、构建命令和退出码。

### 阶段 3：manifest 与版本说明

1. 必查项：发布包存在、`manifest.json`、`release-manifest.json`、镜像 tar、manifest `sourceRepos[*].commit/dirty`、`changeSet.summary`、前端镜像 `release-info.json`。
2. 推荐命令：`validate-release-manifest.ps1 -PackagePath <package> -OutputPath <state>.json`，以及读取 manifest 的短 JSON 摘要脚本。
3. Fail Fast：manifest 缺失、validator 失败、source commit 不等于冻结 app HEAD、dirty 非 false、变更说明为空或无法对应提交、release-info 与 manifest 不一致。
4. 必须记录：releaseTag、package path、source commit、dirty、changeSet、artifact SHA256、validator status。

# 2026-09-09 build-release 默认 code-only 与全量数据包显式门禁

### 门禁摘要

- Trigger: build-release 耗时异常、发布日志长时间停在 manifest/integrity/NAS copy、默认打出数据库 dump 与 MinIO 快照、发布包超过 5GB、或用户只要求测试服代码发布。
- Preflight check: 日常测试服发布必须确认 `PublishScope=code-only`，脚本默认等价于 `-SkipDatabaseSync -SkipMinioSync`；只有明确选择 `-PublishScope with-data -ConfirmText WITH-DATA` 才允许导出数据库与 MinIO 快照。manifest 生成后必须记录 `Release package size summary`，NAS 入库必须使用可校验的目录复制并输出 `Release directory copy summary`。
- Blocker: 未明确确认却准备 with-data；with-data 同时传入 `-SkipDatabaseSync` 或 `-SkipMinioSync`；日志无法区分 manifest、integrity、NAS copy 阶段；或为了缩短发布时间跳过 manifest/P0 integrity/NAS 复验。
- Verification: 合同测试必须覆盖默认 code-only、with-data 强确认、长阶段日志、NAS robocopy 复制、manifest artifact 缓存复用和 schema/validator 的 `release-code` / `release-data-snapshot` 包类型；真实发布时另核 publishScope、packageRole、package size、operation=SUCCESS、NAS path 和 releaseTag。
- Forbidden action: 禁止把日常代码发布默认做成 with-data；禁止用 mock/占位文件、跳过 DCC inventory、取消完整性校验、或边复制边宣称 NAS 包可用来换取提速；禁止在正式/备份晋级使用 with-data 包。
- Evidence: `doc/tasks/20260909-release-duration-optimization/execution-log.md`；实现提交 `6639128`。

### 阶段必查项

1. 构建范围：未明确 `WITH-DATA` 确认时必须是 `code-only`，并记录数据库/MinIO 快照被跳过。
2. 数据快照：with-data 只作为显式数据快照包语义出现，manifest 使用 `packageRole=release-data-snapshot`；code-only 使用 `packageRole=release-code`。
3. 完整性校验：本地 build 阶段允许复用刚生成的 artifact hash，但仍必须枚举实际文件防止未声明文件混入；NAS 目标包必须重新校验实际复制结果。
4. 可观察性：manifest、integrity、NAS upload 三个阶段必须有开始、结束、耗时和文件/字节摘要，避免再次出现小时级黑箱等待。
