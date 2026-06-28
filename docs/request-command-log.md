# 请求与命令记录

## 2026-06-28 提交并推送代码

- 用户需求：提交并推送当前“发布说明变更项乱码修复”任务的代码。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`。
- 命令记录：核对当前提交范围归属 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260628-release-change-items-garbled-fix\task.md`，避免混入其他历史残留改动。
- 命令记录：执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> PASS。
- 命令记录：执行 `node D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\publish_release_info_contract.test.mjs` -> PASS。
- 命令记录：预检查 `git remote -v`，当前维护仓 Git 根目录未配置远端；可执行本地提交，但推送前置条件缺失。

## 2026-06-21 主程序合并后重新走页面发布全链路

- 用户需求：主程序合并修改了部分代码，担心原来的发布链路已经不对，要求重新通过页面前端点击操作完整走一遍 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：重新读取 `supervised-complex-delivery` 与 `playwright` 技能，以及 `artifact-contract.md`、`task-state-schema.md`，按新一轮高风险真实页面发布任务重新建档。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260621-frontend-release-full-flow-rerun/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/`。
- 命令记录：检查当前基线：后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 为干净 `int_main`，最新提交 `b83918fb22`；前端仓 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 最新提交 `37359a074`，仅有未跟踪 `.env.merged-e2e`；维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前分支 `int_main`，存在 `backup-ops` 相关未提交改动，但 `ops/deploy` 与页面发布链路未见未提交更改。
- 命令记录：确认 `npx` 来源为 `D:\Programs\npx.ps1`；本机运行控制台健康接口 `http://127.0.0.1:48181/actuator/health` 当前可访问。
- 结论记录：已新建 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\` 并写入 `task.md`、`request-analysis.md`、`prd.md`、`dev-plan.md`、`test-plan.md`、`task-state.json`、`execution-log.md`、`test-report.md`；下一步先记录 `experience-preflight`，再从页面真实执行新 releaseTag 的 build-release。

## 2026-06-21 再次按页面真实流程走构建发布测试服/正式服/备份服

- 用户需求：再次正式按“页面前端点击操作”的真实流程，完整走一遍构建发布到测试服、正式服、备份服；禁止直接调接口替代页面动作；每遇到问题先记录任务文档，修复后继续从页面走，直到整条流程能够一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：读取 `C:\Users\BJB110\.codex\skills\supervised-complex-delivery\SKILL.md`、`artifact-contract.md`、`review-gates.md`、`task-state-schema.md` 与 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`，确认本轮需要先把任务状态、计划和测试制品落盘。
- 命令记录：检查维护仓 `doc/tasks` 最新任务，发现 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\task.md` 仍为 `IN_PROGRESS`；按仓库规则先将其显式改为 `BLOCKED`，原因是用户当前线程优先级切换。
- 命令记录：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\{task.md,execution-log.md}` 与 `docs/request-command-log.md`，确认同类页面真实发布链路已在 `release-20260621-page-full-flow-v6` 上完整走通并提交。
- 命令记录：检查当前工作树：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 为干净 `int_main`；`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 仅有未跟踪 `.env.merged-e2e`；维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 仍保留上一个备份恢复任务的 `backup-ops` 脏改动。
- 结论记录：已新建 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-rerun\` 并落地 `task.md`、`request-analysis.md`、`prd.md`、`dev-plan.md`、`test-plan.md`、`task-state.json`、`execution-log.md`、`test-report.md`；当前主阻塞是“本轮到底重跑哪套发布基线”尚未明确，在此之前不得进入新的测试服/正式服/备份服真实写入。
- 命令记录：改为按完成审计核现状，而不是直接重跑；读取 `20260620-frontend-release-full-flow` 任务文档、`runtime/runtime-control` 下 v6 五个 operation JSON/日志、`release-manifest.json`、`manifest.json`、`tested.json` 与正式 dry-run 证据，确认既有 v6 页面链路证据闭合。
- 命令记录：通过只读 SSH 分别复核测试服 `172.30.30.58`、正式服 `172.30.30.57`、备份服 `172.30.30.59` 的 `/opt/intruoyi/runtime/.env`、`docker ps`、`127.0.0.1:48081/actuator/health`、`127.0.0.1:8081/` 与 `127.0.0.1:8081/pdfjs/pdf.worker.mjs`，三套环境当前均为 `release-20260621-page-full-flow-v6` 且入口健康。
- 命令记录：运行 `python C:\\Users\\BJB110\\.codex\\skills\\task-closeout-cleanup\\scripts\\task_closeout.py --task-id 20260621-frontend-release-full-flow-rerun --mode preview`，结果 `status: ready`，默认保留 `task.md`、`execution-log.md`，其余新建计划/分析制品为可清理附属物，无阻塞项。
- 结论记录：基于当前文件证据和三套环境运行态，已确认用户要求的真实页面发布链路目标实际上已经由 `release-20260621-page-full-flow-v6` 完成，并且当前状态仍保持该结果；本轮因此以完成审计收口，不再额外触发新的真实写入。

## 2026-06-20 当前最新程序发布任务复盘

- 用户需求：执行 `$fupan`，把本轮“测试服发布 + 三角色真实验收 + 正式服预发布阻塞”沉淀为可复用经验，避免后续重复踩坑。
- 命中技能：`C:\Users\BJB110\.codex\skills\fupan\SKILL.md`。
- 命令记录：读取 `SKILL.md`、当前任务 `task.md`、`execution-log.md`，确认本轮已有足够证据支撑复盘。
- 命令记录：读取 `references/project-memory-template.md`、既有 `docs/agent-memory/project-error-prevention.md` 与 `docs/request-command-log.md`，按“项目级规则 / 任务专项细节”拆分候选经验。
- 命令记录：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\collect_error_evidence.py --project-root D:\ProjectPackage\Int\IntRuoyiMaintance --glob doc\tasks\20260620-prod-release-current-latest\task.md --glob doc\tasks\20260620-prod-release-current-latest\execution-log.md --glob AGENTS.md --output D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\candidate-error-evidence.md`，生成本轮候选证据。
- 命令记录：尝试运行 `update_project_memory.py` 追加“正式服 Smart Release prod preflight 证据闭合”规则，被脚本拒绝，原因是该条目目前仍偏本次发布链专项规则，不属于项目级通用短记忆。
- 结论记录：本轮 `$fupan` 接受的长期经验仍是“发布前预检”“发布验证多证据闭环”“先全量记录失败再统一修复复测”三类；`ProdDryRunEvidencePath / target config / NasConfigPath` 保留在当前任务文档，不提升到 `AGENTS.md` 或项目级记忆；页面脚本细节不进入长期记忆。

## 2026-06-20 前端页面走完整发布测试服/正式服/备份服全流程

- 用户需求：正式按页面前端点击操作的真实流程，完整走一遍构建发布到测试服、正式服、备份服；过程中禁止直接调接口替代页面动作；遇到问题先记录任务文档，修复后继续从页面重走，直到整条流程一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260620-fupan-prod-release-v7/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260620-frontend-release-full-flow/`。
- 命令记录：读取并确认当前任务 `task.md`、`execution-log.md` 已落地 `BDD` 场景、`设计约束检查`、`经验门禁` 与 `GREEN: experience-preflight -> PASS`。
- 命令记录：尝试按 `control-in-app-browser` 技能接入应用内浏览器，`node_repl/js` 返回环境级错误 `missing field sandboxPolicy`；该问题已记录到当前任务 `execution-log.md`，不属于页面业务链路问题。
- 命令记录：只读验证 `http://127.0.0.1:48181/` 返回 `200`；核对维护仓前端打包产物与源码，确认运行控制台真实存在“构建发布包 / 部署测试服 / 上线正式服 / 上线备份服”按钮、预览命令弹窗和执行弹窗。
- 结论记录：应用内浏览器工具层暂不可用，但页面入口和页面动作契约正常；后续改用 Playwright 包装器执行同一真实页面点击流，不用接口直调替代按钮。

## 2026-06-17 真实 E2E 构建并发布到测试服务器

- 用户需求：用真实的 E2E 操作构建发布到测试服务器。
- 计划边界：仅发布测试服 `172.30.30.58`，远端目录 `/opt/intruoyi/runtime`；发布范围为 `code-only`，不访问正式服/备用服，不执行备份、恢复、回滚或正式服动作。
- 命中经验：`release-backup-restore.md`、`server-access.md`、`login-access.md`；真实 E2E 和服务器写入前必须记录 `experience-preflight`。
- 命令记录：检查 `npx` 可用，路径为 `D:\Programs\npx.ps1`。
- 命令记录：检查上一任务 `20260617-restart-frontend-backend-bat` 已完成。
- 命令记录：`GREEN: experience-preflight -> PASS`，目标限定测试服 `172.30.30.58` 与 `code-only` 发布。
- 命令记录：本机维护控制台 `127.0.0.1:48181` 初始未监听；测试服后端健康检查 `http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`。
- 命令记录：记录原 IntRuoyi 前后端 `int_main` HEAD 与既有未提交改动状态；本任务不回滚、不清理这些改动。
- 命令记录：启动本机维护控制台后 `http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`。
- 命令记录：Playwright 打开运行控制台，填入 release tag `release-20260617-1500-codeonly-e2e`，确认 OnlyOffice/展厅包/智能报告均未勾选。
- 命令记录：构建发布包预览 PASS，命令包含 `-Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58`，不包含正式服 IP、生产发布、备份、恢复、回滚动作。
- 命令记录：Playwright 点击构建发布包“执行”，operation `op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef` 初始状态 `RUNNING`。
- 命令记录：构建 operation 最终 `FAILED`；后端 Maven、前端 Vite build、后端 Docker 镜像构建成功，前端 Docker 镜像构建失败，原因是拉取 `nginx:1.27-alpine` 元数据时 Docker Hub token 请求超时。
- 阻塞记录：发布包未成功生成，禁止继续发布测试服；下一步先补齐/验证 Docker 基础镜像 `nginx:1.27-alpine`。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`。
- 命令记录：Playwright 使用新 release tag `release-20260617-1538-codeonly-e2e` 重新预览构建发布包，范围检查 PASS。
- 命令记录：Playwright 点击第二次构建发布包“执行”，operation `op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300` 初始状态 `RUNNING`。
- 命令记录：第二次构建 operation 仍 `FAILED`；Maven、Vite、后端镜像和前端镜像成功，发布迁移策略门禁失败，原因是 `20260617_dcc_browser_performance_indexes` 依赖缺失 `20260513_dcc_base_schema.sql`。
- 阻塞记录：发布包 manifest 未生成，禁止继续发布测试服；需要先修复迁移元数据/扫描集合。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 修正 `sql/mysql/20260617_dcc_browser_performance_indexes.sql` 首行 `dependsOn` 为清单实际使用的迁移 ID `20260513_dcc_base_schema`。
- 命令记录：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 通过，`status=passed`，`migrationCount=147`。
- 命令记录：`python -X utf8 C:\Users\BJB110\.codex\skills\database-schema-delivery\scripts\validate_database_schema.py --evidence doc\tasks\20260617-dcc-browser-migration-dependency\database-schema-evidence.md` 通过。
- 命令记录：Playwright 使用新 release tag `release-20260617-1627-codeonly-e2e` 预览第三次构建发布包，范围检查 PASS。
- 命令记录：Playwright 点击第三次构建发布包“执行”，operation `op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73` 初始状态 `RUNNING`。
- 命令记录：第三次构建 operation `FAILED`；Maven 在 `yudao-module-dcc` 执行 clean 时无法删除 `target`，发布包未生成，禁止发布测试服。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS，DCC target 清理前置恢复。
- 命令记录：Playwright 使用新 release tag `release-20260617-1632-codeonly-e2e` 预览第四次构建发布包，范围检查 PASS。
- 命令记录：Playwright 点击第四次构建发布包“执行”，operation `op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990` 初始状态 `RUNNING`。
- 命令记录：第四次构建 operation `FAILED`；Maven、Vite build、后端 Docker 镜像成功，前端 Docker 镜像解析 `nginx:1.27-alpine` 元数据时 Docker Hub 返回 EOF，发布包未生成，禁止发布测试服。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，本地 `docker image inspect` PASS。
- 命令记录：Playwright 使用新 release tag `release-20260617-1645-codeonly-e2e` 预览第五次构建发布包，范围检查 PASS。
- 命令记录：Playwright 点击第五次构建发布包“执行”，operation `op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a` 初始状态 `RUNNING`。
- 命令记录：第五次构建 operation `FAILED`；发布脚本在 Maven clean 前检测到本机 `yudao-server.jar` 被 Java 进程锁定。
- 命令记录：`restart-ruoyi-backend.bat` 已把本机后端切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260617-164706.jar`，尽管应用最终因定时任务同步失败退出，但目标 jar 锁已解除。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS，确认 `yudao-server.jar` 锁前置已恢复。
- 命令记录：Playwright 使用新 release tag `release-20260617-1654-codeonly-e2e` 预览第六次构建发布包，范围检查 PASS。
- 命令记录：Playwright 点击第六次构建发布包“执行”，operation `op-2026-06-17T085414727300800Z-8359c878-baa8-4ccd-abd4-65e3f2f03ca4` 初始状态 `RUNNING`。
- 命令记录：第六次构建 operation `SUCCESS`；发布包上传至 NAS `Backup/ReleasePackage/release-20260617-1654-codeonly-e2e`。
- 命令记录：`curl http://127.0.0.1:48181/admin-api/infra/runtime-control/release-packages` 显示发布包 `release-20260617-1654-codeonly-e2e` 为 `AVAILABLE`，`publishScope=code-only`，`component=intruoyi`，`checksumPresent=true`。
- 命令记录：Playwright 选择“部署测试服”，填写 release tag `release-20260617-1654-codeonly-e2e` 并预览部署命令，范围检查 PASS：`-Mode deploy-release -Environment test -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime`，无正式服、备份、恢复、回滚动作。
- 命令记录：Playwright 点击部署预览弹窗“执行”，operation `op-2026-06-17T090710635870700Z-11dabe12-ebbe-4311-98da-00b614aec4ec` 初始状态 `RUNNING`。
- 命令记录：部署 operation `SUCCESS`；日志输出 `Publish completed for test`。
- 命令记录：测试服 `/opt/intruoyi/runtime/.env` 返回 `IMAGE_TAG=release-20260617-1654-codeonly-e2e`，`docker compose ps` 显示 `intruoyi-backend` 和 `intruoyi-frontend` 均 running。
- 命令记录：`curl http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`，`curl -I http://172.30.30.58:8081/` 返回 `HTTP/1.1 200 OK`。
- 命令记录：测试服 `infra_release_migration` 中 `20260617_dcc_browser_performance_indexes` 最新状态为 `APPLIED`。
- 命令记录：Playwright 打开 `http://172.30.30.58:8081/`，HTTP 200，跳转到 `/login?redirect=/index`，页面标题为 `瑛泰管理系统 - 登录`，未发现 console error。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅计划删除 `runtime-control-start.out.log` 与 `runtime-control-start.err.log`。
- 命令记录：停止本任务启动的本机维护控制台 `127.0.0.1:48181` 以释放日志文件锁；`task-closeout-cleanup --mode apply` PASS，已删除两个临时日志。

## 2026-06-17 新增本机前后端重启 bat

- 用户需求：创建一个 bat 文件，双击可以重启前后端；用户随后要求继续。
- 计划边界：只新增本机双击入口；不执行真实重启、不操作服务器、不 SSH、不写入数据库或对象存储。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，正式服默认禁止操作，远端重启必须有当前任务授权；本任务仅本机入口。
- 命令记录：读取 `scripts\start.ps1`、`scripts\dev-frontend.ps1`、`scripts\dev-backend.ps1`、`ops\deploy\restart-int-ruoyi-local.ps1` 与远端 bat，确认现有脚本入口。
- 命令记录：只读解析当前维护仓库 `ops\deploy\worktree-port-map.ps1` 失败，错误为缺少 `D:\ProjectPackage\Int\yudao-ui-admin-vue3`。
- 命令记录：只读解析原 IntRuoyi `worktree-port-map.ps1` 成功，`int_main` 映射到 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`、`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`、端口 `8081/48081`。
- 命令记录：`RED` 检查 `restart-frontend-backend.bat` 不存在，按预期失败。
- 命令记录：新增 `restart-frontend-backend.bat`，默认调用原 IntRuoyi 本机重启脚本 `-Component full`。
- 命令记录：`cmd /d /c restart-frontend-backend.bat cancel` PASS，未触发真实重启。
- 命令记录：PowerShell 静态检查 bat 必含原 IntRuoyi 重启脚本路径、`-Component full` 和 `cancel` 分支，PASS。
- 命令记录：`git diff --check` PASS，仅有既有换行提示。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 结论记录：已完成本机双击重启入口；验证阶段未执行真实重启、远端操作或数据写入。

## 2026-06-16 当前运行控制台与原版一致性审计

- 用户需求：分析当前独立维护应用代码与 `yintruoyi`（按上下文理解为 `D:\ProjectPackage\Int\IntRuoyi`）下原运行控制台逻辑一致性。
- 计划边界：只做静态审计和本地契约验证；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，运行控制台相关发布包、tested、恢复候选、DCC 链和 manifest/checksum 证据必须 fail fast；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，本次不改 UI，只审计前端契约。
- 命令记录：结构化解析 controller mapping，standalone 与 original 均为 33 个规范化 HTTP 路径，差异集为空。
- 命令记录：`rg` 对比 service/action/frontend payload，核心动作校验、release-status、mark-tested、候选服务端绑定、DCC chainStatus、前端 payload 均已对齐。
- 命令记录：脚本 hash 对比显示 `apply-test-db-sql.ps1`、`backup-ops.ps1`、`show-int-ruoyi-local-status.ps1`、`restart-int-ruoyi-local.ps1` 字节一致；`publish-int-ruoyi.ps1` 独立版有 64 行差异，来自显式源码根、UTF-8 捕获、DCC inventory base64 JSON 后续修复。
- 命令记录：发现条件性差异：原版 `backupOps.executionMode=linux-local` 会生成 Linux 风格参数，独立版只切换脚本路径但仍生成 PowerShell 风格参数；默认 `powershell` 配置不触发。
- 命令记录：发现治理面差异：owner matrix / alert / incident / inspection / probe / capacity / remote-root 与完整前端治理界面为独立版简化或 fail-fast 实现。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，7 tests, failures 0。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 命令记录：`task-closeout-cleanup --mode apply` PASS，无删除项、无阻塞、无警告。
- 结论记录：核心运行控制台动作契约 PASS；若要求原版完整治理能力 1:1 复制，则为 PARTIAL。

## 2026-06-16 运行控制台剩余差异改成原版一致

- 用户需求：继续将独立运行控制台改成与原版 IntRuoyi 运行控制台一致。
- 计划边界：只修改本机独立维护应用；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，发布包、测试通过标记和恢复候选必须使用真实 manifest/checksum/tested/recoverySet/DCC 证据并 fail fast；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，前端保持紧凑运维控制台风格。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` RED，复现 `release-status` 版本字段为空、非动作字段未被拒绝、DCC `chainStatus=BROKEN` 未阻断。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` RED，复现前端 payload 未按动作裁剪。
- 命令记录：补齐后 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，7 tests, failures 0。
- 命令记录：补齐后 `python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS，Vite 仅提示现有大 chunk 体积。
- 命令记录：`mvn -f backend/pom.xml test` PASS，12 tests, failures 0。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 命令记录：`task-closeout-cleanup --mode apply` PASS，无删除项、无阻塞、无警告。

## 2026-06-16 运行控制台逻辑一致性审计

- 用户需求：分析当前独立维护应用代码与 `D:\ProjectPackage\Int\IntRuoyi` 下原运行控制台逻辑一致性；本次按用户写法 `yintruoyi` 理解为原 IntRuoyi 项目。
- 计划边界：只读静态审计；不执行发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，发布包、候选、恢复、操作证据与 `code-only`/`with-data` 边界必须按真实逻辑判断。
- 命令记录：`rg --files` 定位当前独立应用 `backend/src/main/java/com/intruoyi/maintenance/runtime`、`frontend/src` 与原 IntRuoyi runtimecontrol 后端、前端文件。
- 命令记录：修正端点提取脚本，对比公共路径；独立版 27 个接口，原版 33 个接口，独立版无额外路径，原版额外包含 owner-matrix、wizard、alerts resend site message 6 个治理接口。
- 命令记录：`rg -n "selectedImageTag|selectedBackupId|apply-test-db-sql|owner-matrix|wizard|resend-site-message"` PASS，确认候选字段、SQL 动作入口、治理接口差异。
- 命令记录：`rg -n "PreAuthorize|SecurityFrameworkUtils|getLoginUserId|CommonResult|ApiResult"` PASS，确认独立版已移除芋道登录权限依赖，响应外形为本地最小等价类型。
- 命令记录：`rg -n "code-only|with-data|SkipDatabaseSync|SkipMinioSync|BackendRepoRoot|FrontendRepoRoot|WebsiteRepo|opsRoot|script/|ops/"` PASS，确认 code-only 参数一致，脚本路径和源码根参数为独立化差异。
- 结论记录：当前独立版与原运行控制台基础路径、动作枚举和构建发布包命令骨架部分一致；候选服务端绑定、发布包 manifest/checksum/tested 校验、恢复候选丰富度、负责人/向导治理、前端 `apply-test-db-sql` 入口和状态枚举存在逻辑不一致。

## 2026-06-16 运行控制台改成与原版一致

- 用户需求：将独立运行控制台改成与原版，也就是 `D:\ProjectPackage\Int\IntRuoyi` 的运行控制台逻辑一致。
- 计划边界：保留独立应用本机运行与不接入芋道登录/角色/菜单权限；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，发布包、回滚候选和恢复候选必须读取真实 manifest/checksum/tested 证据；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，前端保持紧凑运维控制台风格。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` RED，前端缺少原版 `apply-test-db-sql` 动作入口；补齐后同命令 PASS。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` RED，原版一致性测试要求 NAS browser 提供 `listFiles`、`isRegularFile`、`readText`；补齐候选解析和 NAS 文件读取后 PASS。
- 命令记录：`mvn -f backend/pom.xml test` PASS，9 tests, failures 0, errors 0。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS。
- 命令记录：`.\scripts\build.ps1` 首次因本机旧维护应用 jar 占用目标文件失败；确认占用进程监听 `127.0.0.1:48181` 且命令行为本仓库 jar 后停止该本机进程，重跑 PASS。
- 命令记录：启动本地应用后 `GET http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`。
- 命令记录：内置 Browser 打开 `http://127.0.0.1:48181/`，DOM 显示 `运行控制台`，动作入口包含 `构建发布包`、`测试服数据库快应用`、`回滚应用`、`恢复数据`，页面显式提示 `backupOps.nasUsername is required`，console error 为 0。
- 命令记录：Playwright CLI 默认 Chromium 缺失，改用系统 Chrome channel 截图：`pnpm --dir frontend exec playwright screenshot --channel chrome --wait-for-timeout=3000 --viewport-size="1280,720" http://127.0.0.1:48181/ ...\runtime-control-standalone-e2e.png` PASS。
- 命令记录：`python ...\validate_test_report.py --expected-outcome passed ...` PASS；`python ...\check_completion.py --apply` PASS，任务状态 completed。
- 命令记录：`git diff --check` PASS，仅有 Windows 换行提示。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，blocked/warnings 均无；因预览会删除本次 spec-driven 任务的 PRD/test-plan/test-report/task-state 与 E2E 截图证据，未执行 apply。

## 2026-06-16 运行控制台前端视觉优化

- 用户需求：使用 `design-taste-frontend` 技能，让独立运行控制台前端设计更好看。
- 计划边界：仅优化本机独立控制台前端视觉与可扫描性；不执行发布、备份、恢复、回滚、重启、远端清理或真实写入动作；不引入未验证依赖，不改现有 Vue 3 + Element Plus 技术栈。
- 命中经验：`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，按 IntPP 生产订单列表风格做安静、紧凑、灰蓝边框、表格优先的运维控制台。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` 先 RED 后 GREEN，新增前端设计 marker 与 token 契约。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS；Vite 仅提示现有大 chunk 体积。
- 命令记录：`.\scripts\build.ps1` PASS，随后本机维护应用 `http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`。
- 命令记录：Playwright 桌面与 390x844 移动视口打开 `http://127.0.0.1:48181/`，确认页面显示新版运行控制台、动作区无重叠、console error 为 0；未点击执行发布、备份、恢复、回滚、重启或远端清理动作。
- 命令记录：`task-closeout-cleanup` 预览 PASS，无删除项、无阻塞、无警告；`apply` 也 PASS，无删除项、无阻塞、无警告。

## 2026-06-16 拆分运行控制台独立应用

- 用户需求：把 IntRuoyi 的运行控制台拆成 `D:\ProjectPackage\Int\IntRuoyiMaintance` 下的独立本机应用，复制 `AGENTS.md`，初始化 Git 管控；独立应用不用芋道权限，默认本机访问，一键启动，管理现有 IntRuoyi 源码。
- 计划边界：不删除或改造原 IntRuoyi 运行控制台入口/API；本次验证不执行真实发布、备份、恢复、回滚、重启或远端清理。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` RED 失败后实现代码，最终 PASS。
- 命令记录：`mvn -f backend/pom.xml test` PASS。
- 命令记录：`pnpm --dir frontend install --lockfile-only` 生成 lockfile。
- 命令记录：`pnpm --dir frontend install --frozen-lockfile` PASS。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS。
- 命令记录：`.\scripts\build.ps1` PASS。
- 命令记录：`.\scripts\start.ps1` 后 `curl.exe -s http://127.0.0.1:48181/actuator/health` PASS，返回 `{"status":"UP"}`。
- 命令记录：Playwright 打开 `http://127.0.0.1:48181/`、检查 snapshot、console、requests，并点击“预览命令”；页面可见且 console error 为 0，未执行真实动作。

## 2026-06-16 真实数据构建发布包 E2E 验证

- 用户需求：使用 E2E 测试，用真实的数据构建一次发布包，不要发布。
- 计划边界：仅允许触发 `build-release`；不得执行 `publish-test`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`restore-data`、`restart` 或任何远端清理动作。
- 计划命令：检查任务文档与经验门禁，检查本机运行控制台健康状态、构建脚本和被管理源码路径，使用 Playwright 打开 `http://127.0.0.1:48181/` 预览并执行 `build-release`，轮询操作结果并核验发布包 manifest/日志证据。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest test` RED 失败，发现独立控制台漏掉 `build-release` 的 NAS 发布仓库和后端运行基座参数；修复后同命令 PASS。
- 命令记录：`mvn -f backend/pom.xml test` PASS。
- 命令记录：`.\scripts\build.ps1` 首次因旧 jar 被本机控制台进程占用失败，停止 `127.0.0.1:48181` 旧进程后重跑 PASS。
- 命令记录：本机生成被 `.gitignore` 排除的 `config/runtime-control.local.yaml`，只用于本机真实配置，不提交敏感凭据。
- 命令记录：Playwright 打开 `http://127.0.0.1:48181/`，选择 `构建发布包`、`含数据`，填写发布标签 `release-20260616-112813-e2e`，点击“预览命令”；预览命令无发布、晋级、正式服主机、备份、恢复、回滚或重启动作。
- 命令记录：Playwright 执行 `build-release` 标签 `release-20260616-112813-e2e` 后失败，日志显示脚本误从独立仓库推断 `sql\mysql`；修复为显式传入 `-BackendRepoRoot/-FrontendRepoRoot/-WebsiteRepo`。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test` 对源码路径参数先 RED 后 GREEN。
- 命令记录：重新执行 `mvn -f backend/pom.xml test` 与 `.\scripts\build.ps1`，均 PASS，并重启 `http://127.0.0.1:48181/`。
- 命令记录：Playwright retry 预览发布标签 `release-20260616-113500-e2e`，确认命令包含被管理源码路径且仍无发布、晋级、正式服主机、备份、恢复、回滚或重启动作。
- 命令记录：Playwright 执行 `build-release` 标签 `release-20260616-113500-e2e` 后失败，脚本已复制 `23.46 GiB` 真实 MinIO 数据，随后因 DCC 对象清单 tab 分隔解析被真实特殊文件名打坏而失败。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` 对 DCC inventory JSON 行协议先 RED 后 GREEN；发布脚本改为 `JSON_OBJECT` + `ConvertFrom-Json`。
- 命令记录：Playwright third retry 执行 `build-release` 标签 `release-20260616-121500-e2e` 后失败；真实后端构建、前端构建、Docker 镜像、本机 MySQL dump 与 `23.46 GiB` MinIO 同步均完成，随后 DCC inventory 在真实中文文件名行因 PowerShell 5.1 stdout 编码破坏而 malformed。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` 对 DCC inventory base64 传输协议先 RED 后 GREEN；发布脚本改为 `TO_BASE64(JSON_OBJECT)` 单列输出、PowerShell `FromBase64String` + 严格 UTF-8 解码，并为进程捕获设置 `StandardOutputEncoding`。
- 命令记录：只读查询真实问题行 `fileId=9198354896134`，base64 JSON 可解码为合法对象，路径为 `dcc/original/20260615/@最终版规程@ - 快捷方式.lnk.重命名`。
- 命令记录：PowerShell AST parse `ops/deploy/publish-int-ruoyi.ps1` PASS；`mvn -f backend/pom.xml test` PASS。
- 风险记录：只读进程检查发现原 IntRuoyi 运行控制台存在并发 `deploy-release -Environment backup` 进程，不属于本次维护应用 E2E；本次任务不干预该进程，并在后续验收中按操作来源区分。
- 用户变更：用户明确“发布不要带数据 / 构建不要带数据”，最新范围改为 `code-only` 构建发布包，不包含数据库 dump 或 MinIO 快照。
- 命令记录：中止本次维护应用正在运行的 `with-data` 构建操作 `op-2026-06-16T045827746415700Z-ab581284-205e-4d11-8e87-4434e44255cd`；后台状态为 `FAILED`，本地半成品无 `release-manifest.json`。
- 命令记录：删除本任务生成的带数据半成品目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-125800-e2e`，删除前校验目标位于发布缓存根目录内，删除后目录不存在。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewSkipsDatabaseAndMinioData test` PASS；`python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：Playwright 预览发布标签 `release-20260616-152022-codeonly-e2e`，页面发布范围为“仅代码”；参数包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`，不包含发布、晋级、正式服主机、备份、恢复、回滚、重启、数据库 dump 或 MinIO 同步动作。
- 命令记录：Playwright 执行 `code-only build-release`，操作 `op-2026-06-16T072304860538200Z-0d13eb24-9a16-47b9-aed7-68b9b3e71f21` 最终 `SUCCESS`；日志显示 `Release package built: release-20260616-152022-codeonly-e2e`，NAS 路径 `Backup/ReleasePackage/release-20260616-152022-codeonly-e2e`。
- 命令记录：发布包本地核验 PASS，`release-manifest.json` 为 `publishScope=code-only`，镜像 tar `811197440` bytes，不存在 `ruoyi-vue-pro-current.sql`、`minio`、`manifest\dcc-object-inventory.json`。
- 命令记录：`GET /admin-api/infra/runtime-control/release-packages` 可见 `release-20260616-152022-codeonly-e2e` 且状态 `AVAILABLE`；维护应用操作记录中未出现发布、晋级、备份、恢复、回滚、重启动作。
- 命令记录：Playwright 最终页面快照显示最新操作 `SUCCESS`，浏览器 console error 为 0，请求列表仅包含运行控制台读接口、预览和执行接口。
- 命令记录：`mvn -f backend/pom.xml test` PASS；`python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：`task-closeout-cleanup` 预览 PASS，无删除项、无阻塞、无警告。

## 2026-06-16 运行控制台原版一致性修复

- 用户需求：把独立维护应用里的运行控制台改成与原版 IntRuoyi 一致，重点补 Linux-local 备份参数、运行治理持久化和前端日志入口。
- 计划边界：保留独立本机运行和不接入芋道登录/角色/菜单权限；不执行真实发布、备份、恢复、回滚、重启或远端清理。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalGovernanceParityTest test` 先 RED 后 GREEN，Linux-local 备份命令改为原版 `--mode/--config/--non-interactive` 参数，巡检/告警/责任矩阵/事故改为本地 `runtime-ops/*.json` 持久化。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` 先 RED 后 GREEN，前端补齐原版运行治理 API wrapper 与操作日志入口。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，旧的一致性测试改为原版向导场景和先创建告警再重发。
- 命令记录：`mvn -f backend/pom.xml test` PASS，14 tests。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS。
- 命令记录：`task_closeout.py --task-id 20260616-runtime-control-full-original-parity-fix --mode preview` PASS，无删除项、无阻塞、无警告；`--mode apply` PASS，无删除项。
- 结论记录：独立版运行控制台已对齐原版在 Linux-local 参数、治理持久化、向导场景和前端日志入口上的核心语义；本次仍保持独立本机边界，不回接芋道权限体系。

## 2026-06-16 运行控制台原版逻辑一致性再审计

- 用户需求：继续分析当前独立维护应用代码与 `yintruoyi`（按上下文理解为 `D:\ProjectPackage\Int\IntRuoyi`）下原运行控制台逻辑一致性。
- 计划边界：本次只做源码、契约、测试和构建审计；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：发布/备份/恢复门禁要求 manifest/checksum/tested/恢复链证据 fail fast；前端门禁要求运行控制台保持紧凑、清晰、可扫描。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：`mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，7 tests / 0 failures。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`mvn -f backend\pom.xml test` PASS，14 tests / 0 failures。
- 命令记录：`pnpm --dir frontend build` PASS，Vite 仅提示现有单 chunk 体积超过 500 kB。
- 命令记录：静态接口/动作比对 PASS，独立版与原版均为 33 个 HTTP 接口、10 个 action id。
- 命令记录：脚本哈希比对显示 `apply-test-db-sql.ps1`、`backup-ops.ps1`、`show-int-ruoyi-local-status.ps1`、`restart-int-ruoyi-local.ps1` 字节级一致；`publish-int-ruoyi.ps1` 保留独立应用路径与 DCC inventory UTF-8/base64 修正差异。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，task.md / execution-log.md / verification-report.md 将保留；随后手动删除测试残留目录 `runtime/runtime-control-original-governance-parity-test`。
- 结论记录：当前独立运行控制台在公开接口、核心动作、候选门禁、前端 payload 和主要脚本契约上与原版一致；权限体系、操作者、监听地址、配置来源、运行态目录和正式服默认禁写属于用户要求的独立化差异。

## 2026-06-17 构建发布目标独立验收

- 用户需求：继续完成“构建发布的目标”。
- 计划边界：只复验测试服 `172.30.30.58` 当前发布状态和任务证据；不访问正式服、备用服，不执行备份、恢复、回滚或再次发布。
- 命中经验：构建发布任务必须以 operation、manifest、远端 `.env`/镜像 tag、健康检查和真实页面证据共同判定，不得只用健康检查替代发布完成。
- 命令记录：读取 `ci-cd-environment-delivery`、`independent-verification-gate`、`playwright` 技能，以及 `release-backup-restore.md`、`server-access.md`、`login-access.md`。
- 命令记录：复查任务文档与执行日志，确认发布包 `release-20260617-1654-codeonly-e2e`、构建 operation `op-2026-06-17T085414727300800Z-8359c878-baa8-4ccd-abd4-65e3f2f03ca4`、部署 operation `op-2026-06-17T090710635870700Z-11dabe12-ebbe-4311-98da-00b614aec4ec`。
- 命令记录：现时验证 `curl.exe` 后端健康 HTTP 200、前端 HTTP 200。
- 命令记录：SSH 测试服读取 `.env` 与 `docker compose ps`，确认 `IMAGE_TAG=release-20260617-1654-codeonly-e2e`，前后端镜像均为该 tag 且 running。
- 命令记录：SSH 测试服查询迁移状态，`20260617_dcc_browser_performance_indexes` 为 `APPLIED`。
- 命令记录：SSH 测试服读取发布包 manifest，确认 `releaseTag=release-20260617-1654-codeonly-e2e`、`component=intruoyi`、`publishScope=code-only`、`includeShowroomBuildPackage=false`、`onlyOfficeIncluded=false`。
- 命令记录：Playwright Chromium 打开 `http://172.30.30.58:8081/`，HTTP 200，跳转到登录页，标题 `瑛泰管理系统 - 登录`，console error 为 0。
- 结论记录：已新增 `doc/tasks/20260617-e2e-build-publish-test/verification-report.md`，独立验收结论 PASS；远端登录未执行，原因是登录文档未提供远端测试服账号。

## 2026-06-17 构建发布耗时经验沉淀

- 用户需求：将经验沉淀到文档里，下次不要遇到同样的问题。
- 计划边界：只更新维护仓库经验文档、项目记忆、任务文档和请求命令日志；不执行发布、重启、备份、恢复、回滚、SSH 写入或数据库写入。
- 命中经验：发布任务必须提前确认运行控制台版本、发布命令预览、迁移门禁、manifest、operation、远端 tag 和真实页面证据。
- 命令记录：使用 `fupan` 技能，从 `20260617-e2e-build-publish-test` 的 task、execution-log、verification-report 生成 `candidate-error-evidence.md`。
- 命令记录：新增 `docs/release-build-preflight-lessons.md`，沉淀 Docker 基础镜像预拉、迁移策略门禁、Maven target/jar 锁、E2E 预览边界、TDD 提交门禁、发布完成判定和重试规则。
- 命令记录：新增 `docs/agent-memory/project-error-prevention.md`，项目短记忆 309 字，覆盖发布前预检、SQL/script 提交门禁和发布完成联合验证。
- 命令记录：更新 `docs/experience-index.md`，为“构建发布耗时 / 真实 E2E 发布预检”和“项目错误预防短记忆”增加路由。
- 结论记录：采纳可复用预检经验；未把具体 releaseTag、operationId、Docker digest、测试服实时容器运行时长升级为长期规则。

## 2026-06-17 再次构建发布测试服并发布备份服

- 用户需求：再次构建发布到测试服务器，然后发布到备份服务器。
- 计划边界：拟通过运行控制台真实前端 E2E 构建 `code-only` 发布包，先发布测试服 `172.30.30.58` 验收，再发布备份服 `172.30.30.59`；不访问正式服 `172.30.30.57`，不执行备份、恢复、回滚、数据库同步或 MinIO/NAS 同步。
- 命中经验：读取维护仓库发布预检清单、项目错误预防短记忆、原 IntRuoyi 发布/服务器/登录基线、CI/CD 技能和 Playwright 技能。
- 命令记录：创建任务目录 `doc/tasks/20260617-build-test-backup-release/`，写入 `task.md` 和 `execution-log.md`。
- 阻塞记录：备份服与正式服同等级门禁；当前缺少发布责任人和字面 `PROD` 确认，未执行构建、发布或远端写入动作。
- 用户补充：责任人 `admin`。
- 阻塞记录：已记录发布责任人；仍缺少字面 `PROD` 确认，因此备份服发布继续阻塞。测试服构建发布链路可先执行。
- 命令记录：`rg -n "^FROM "` 扫描原 IntRuoyi 前后端 Dockerfile，预拉并 inspect `nginx:1.27-alpine`、`eclipse-temurin:21-jre-noble`、`eclipse-temurin:21-jre` 通过。
- 命令记录：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` PASS，扫描 148 个迁移。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS；`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS。
- 命令记录：本机运行控制台健康检查 PASS；Playwright 打开运行控制台前端，console error 为 0。
- 命令记录：Playwright 预览 `build-release`，发布标签 `release-202606172114-codeonly-e2e`，参数包含 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不包含正式服、备份、恢复、回滚或数据同步动作。
- 命令记录：Playwright 执行构建发布包，operation `op-2026-06-17T131517885961100Z-bb182f13-642c-4709-8d97-866b2237a06b` 最终 `SUCCESS`；日志显示 `Release package built: release-202606172114-codeonly-e2e`，NAS 路径 `Backup/ReleasePackage/release-202606172114-codeonly-e2e`。
- 命令记录：本机运行控制台前端端口 `48182` 已停止，使用 `pnpm --dir frontend dev` 重启，`http://127.0.0.1:48182/` 返回 HTTP 200。
- 命令记录：Playwright 默认 Chromium headless shell 缺失，改用本机已安装 `ms-playwright\chromium-1224\chrome-win64\chrome.exe` 执行真实浏览器 E2E。
- 命令记录：Playwright 预览 `publish-test`，参数包含 `-Mode deploy-release`、`-Environment test`、`-ReleaseTag release-202606172114-codeonly-e2e`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`，不包含正式服、备份、恢复、回滚或数据同步动作。
- 命令记录：Playwright 执行测试服部署，operation `op-2026-06-17T133605613176400Z-d009458b-b6f9-4979-8f3a-03f72c24b0ae` 最终 `SUCCESS`；发布日志显示远端 required SQL `20260617_erp_kingdee_event_callback.sql` 已 `APPLIED`，后端/前端远端 HTTP readiness 均通过。
- 命令记录：`curl.exe` 验证测试服后端健康与前端入口均为 HTTP 200。
- 命令记录：SSH 测试服读取 `.env` 与 `docker compose ps`，确认 `IMAGE_TAG=release-202606172114-codeonly-e2e`，backend/frontend 镜像均为该 tag 且 `Up`。
- 命令记录：SSH 测试服查询 `infra_release_migration`，`20260617_dcc_browser_performance_indexes=SKIPPED_ALREADY_APPLIED`、`20260617_erp_kingdee_event_callback=APPLIED`。
- 命令记录：Playwright Chromium 打开 `http://172.30.30.58:8081/`，HTTP 200，最终进入登录页 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 为 0。
- 阻塞记录：`GET /admin-api/infra/runtime-control/restore-candidates` 返回 `backupOps.nasUsername is required`；代码在 `mark-release-tested` 前强制解析恢复集候选，因此无法标记测试通过，备份服发布未执行。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅列出本任务四个临时启动日志；因任务未完成未执行 apply。
- 用户补充：`这个intruoyi里有,我不动代码,你来找`；本轮只读定位原 IntRuoyi 中的 backup-ops/NAS 配置来源，避免暴露密码，不修改代码。
- 命令记录：读取原 IntRuoyi `RuntimeBackupNasRepository` / `NasSettingsServiceImpl`，确认原运行控制台从 `infra_config` 的 `infra.nas.username` / `infra.nas.password` 读取 NAS 凭据，再使用 runtime-control 自身 `nasShare`。
- 命令记录：只读查询本机 Docker MySQL `infra_config`，确认 NAS 服务地址、用户名键与密码键均存在；未在日志记录凭据明文。
- 命令记录：将原 IntRuoyi NAS 凭据写入 gitignored 的 `config/runtime-control.local.yaml` 的 `backup-ops` 段；该文件未纳入 Git 跟踪，未修改代码。
- 命令记录：重启本机维护控制台后端，PID `45080`，健康检查 `/actuator/health` 返回 `UP`。
- 命令记录：`GET /admin-api/infra/runtime-control/restore-candidates` 不再报 `backupOps.nasUsername is required`，但返回 `data=[]`。
- 阻塞记录：只读检查测试服 `/mnt/nas/backup/BackupPackage` 无最终可用备份点，历史 `20260611-231633` 仅存在于测试服临时目录 `/opt/intruoyi/runtime/data/backup-ops/tmp`，不能作为恢复集候选；因此仍无法标记测试通过，备份服发布未执行。
- 命令记录：再次执行 `task-closeout-cleanup --mode preview` PASS，最新删除候选为六个本任务临时启动日志；任务未完成未执行 apply。
- 用户澄清：不要备份恢复，只要构建发布到测试服务器和备份服务器；询问是否实现。
- 状态回答：测试服构建发布已实现，备份服发布尚未实现；缺少字面 `PROD` 确认且运行控制台标记测试通过入口仍受恢复集候选约束。
- 用户确认：`PROD`。
- 命令记录：记录备份服发布责任人 `admin` 与字面 `PROD` 确认；本轮继续只做 code-only 发布，不执行备份、恢复、回滚、恢复集标记或数据同步。
- 复现记录：Playwright 真实前端预览“上线备份服”首次返回 `releaseTag 尚未测试通过`，定位为运行控制台后端只认 `tested.json`，不能识别 code-only 测试服成功部署 operation。
- 命令记录：新增后端回归测试 `RuntimeControlOriginalParityTest#promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment`，修复前 RED，期望 code=0、实际 code=400。
- 命令记录：修复 `RuntimeControlService.validateReleasePackageAvailability`，仅对 `PROMOTE_BACKUP + code-only + 同 releaseTag 的成功 publish-test operation` 放行；`PROMOTE_PROD`、`with-data` 和未测试发布包仍保持阻断。
- 命令记录：`mvn -Dtest=RuntimeControlOriginalParityTest#promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment test` PASS；`mvn -Dtest=RuntimeControlOriginalParityTest test` PASS。
- 命令记录：维护控制台后端重新 package，因 Windows jar 文件锁先停止旧 PID，再启动新 PID；本地 gitignored 配置补充 `production-write-enabled: true`，不提交敏感配置。
- 命令记录：Playwright 真实前端重新预览“上线备份服” PASS，命令指向 `172.30.30.59` 与 `/mnt/intruoyi-data`，不包含正式服、备份、恢复或回滚动作。
- 命令记录：Playwright 真实前端执行“上线备份服”，operation `op-2026-06-17T153827586237800Z-17bdf7a0-5639-4967-a9dd-87296756bc45` 最终 `SUCCESS`。
- 命令记录：`curl.exe` 验证备份服后端健康与前端入口均为 HTTP 200。
- 命令记录：SSH 备份服读取 `.env` 与 `docker compose ps`，确认 `IMAGE_TAG=release-202606172114-codeonly-e2e`，backend/frontend 镜像均为该 tag 且 `Up`。
- 命令记录：SSH 备份服查询 `infra_release_migration`，`20260617_dcc_browser_performance_indexes=APPLIED`、`20260617_erp_kingdee_event_callback=APPLIED`，target environment 均为 `backup`。
- 命令记录：Playwright Chromium 打开 `http://172.30.30.59:8081/`，HTTP 200，最终进入登录页 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 为 0，请求失败数为 0。
- 命令记录：`mvn test` PASS，后端 16 个测试通过；`validate_bug_regression.py --evidence ...bug-regression-evidence.md` PASS。

## 2026-06-18 构建发布测试服并发布备份服

- 用户需求：构建发布到测试服务器和备份服务器，授权 `PROD`。
- 授权记录：本轮备份服发布责任人沿用本线程已确认的 `admin`；用户本条消息已提供 `PROD` 授权。
- 计划边界：通过运行控制台真实前端 E2E 构建新的 `code-only` 发布包，先发布测试服 `172.30.30.58` 验收，再发布备份服 `172.30.30.59`；不访问正式服 `172.30.30.57`，不执行备份、恢复、回滚、数据库同步或 MinIO/NAS 同步。
- 命中经验：读取维护仓库发布预检清单、项目错误预防短记忆、原 IntRuoyi 发布/服务器/登录基线、CI/CD 技能和 Playwright 技能。
- 命令记录：创建任务目录 `doc/tasks/20260618-build-test-backup-release/`，写入 `task.md` 和 `execution-log.md`。
- 命令记录：本机运行控制台后端 `48181` 与前端 `48182` 健康；当前维护仓库 HEAD 为 `f8c1d57`。
- 命令记录：预拉并 inspect `nginx:1.27-alpine`、`eclipse-temurin:21-jre-noble`、`eclipse-temurin:21-jre` 通过。
- 命令记录：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` PASS，扫描 149 个迁移。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS；`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS。
- 命令记录：`GREEN: experience-preflight -> PASS`，本轮只允许测试服与备份服 code-only 发布，禁止正式服、备份、恢复、回滚和数据同步。
- 命令记录：Playwright 真实前端预览“构建发布包” PASS，发布标签 `release-20260618-0056-codeonly-e2e`，参数包含 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不包含正式服、备份、恢复、回滚或数据同步动作。
- 命令记录：Playwright 真实前端执行“构建发布包”，operation `op-2026-06-17T165758289152Z-e82db887-1754-41df-bf3d-7e2bf9f840c9` 最终 `SUCCESS`；manifest 确认 `publishScope=code-only`、`component=intruoyi`、`includeShowroomBuildPackage=false`、`onlyOfficeIncluded=false`。
- 命令记录：Playwright 真实前端预览“部署测试服” PASS，参数包含 `-Mode deploy-release`、`-Environment test`、`-ReleaseTag release-20260618-0056-codeonly-e2e`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`，不包含正式服、备份、恢复或回滚动作。
- 阻塞记录：Playwright 真实前端执行“部署测试服”，operation `op-2026-06-17T171309722400800Z-72fd40ab-f703-496f-999d-c9011b2a9c8d` 最终 `FAILED`；必需 SQL `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 报错 `Missing enabled MES scheduler/planner role with smart scheduling tenant package; cannot grant scheduler role tab`。
- 命令记录：只读核对测试服数据库，核心菜单 `900120/5590/5580/5262/5540` 与租户包 `900120` 条件存在，但缺少启用的 MES 排产/计划目标角色。
- 命令记录：只读核对备份服数据库，核心菜单与租户包 `900120` 条件存在，满足 MES 排产/计划目标角色条件的记录数为 0。
- 阻塞记录：测试服 `.env` 已写入 `IMAGE_TAG=release-20260618-0056-codeonly-e2e`，但 backend/frontend 容器仍运行上一版 `release-202606172114-codeonly-e2e`；迁移表中 `20260617_mes_scheduler_role_smart_scheduling_tab` 为 `RUNNING`。因测试服发布未完成且备份服前置条件同样缺失，未执行备份服发布。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅保留本任务 `task.md` 与 `execution-log.md`，无删除项、阻塞项或警告；任务未完成，未执行 apply。
- 用户补充：`授权`。
- 命令记录：按 `database-schema-delivery` 与真实库结构核对 `system_tenant`、`system_tenant_package`、`system_role`、`infra_release_operation_lock`、`infra_release_migration`，确认测试服与备份服 `tenant_id=122` 均缺少 `mes_scheduler` 角色且智能排程菜单树缺失 4 个子菜单。
- 命令记录：测试服执行受控 SQL，克隆 `tenant_id=122` 当前套餐并切换到套餐 `114`，创建/启用 `mes_scheduler/排产员` 角色；将上一轮失败遗留的 release lock 与 migration `RUNNING` 状态改为 `FAILED`。
- 命令记录：测试服只读校验 PASS，`mes_scheduler` 角色数为 1，智能排程菜单树缺失数为 0。
- 命令记录：备份服执行受控 SQL，克隆 `tenant_id=122` 当前套餐并切换到套餐 `113`，创建/启用 `mes_scheduler/排产员` 角色。
- 命令记录：备份服只读校验 PASS，`mes_scheduler` 角色数为 1，智能排程菜单树缺失数为 0，`tenant_id=121` 仍保持原套餐 `111`。
- 命令记录：`validate_database_schema.py --evidence doc\tasks\20260618-build-test-backup-release\database-schema-evidence.md` PASS。
- 命令记录：Playwright 真实前端重新预览并执行“部署测试服”，operation `op-2026-06-18T010137328120900Z-1f312235-29b4-4954-b631-3f09874801a4` 最终 `SUCCESS`。
- 命令记录：测试服 required SQL `20260617_mes_scheduler_role_smart_scheduling_tab` 成功执行并标记 `APPLIED`。
- 命令记录：`curl.exe` 验证测试服后端健康和前端入口均为 HTTP 200；SSH 验证 `.env` 与 backend/frontend 镜像 tag 均为 `release-20260618-0056-codeonly-e2e`。
- 命令记录：Playwright Chromium 打开 `http://172.30.30.58:8081/`，最终 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0。
- 命令记录：Playwright 真实前端预览并执行“上线备份服”，参数包含 `-ConfirmText PROD`、`-RequireTested`、`172.30.30.59`、`/mnt/intruoyi-data` 与 `intruoyi-minio`，不包含正式服、备份、恢复或回滚动作；operation `op-2026-06-18T011250606902100Z-4ca1df68-7dc0-4e79-a9a5-16f9e1e76bd3` 最终 `SUCCESS`。
- 命令记录：备份服 required SQL `20260617_mes_scheduler_role_smart_scheduling_tab` 成功执行并标记 `APPLIED`。
- 命令记录：`curl.exe` 验证备份服后端健康和前端入口均为 HTTP 200；SSH 验证 `.env` 与 backend/frontend 镜像 tag 均为 `release-20260618-0056-codeonly-e2e`。
- 命令记录：Playwright Chromium 打开 `http://172.30.30.59:8081/`，最终 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0。
- 命令记录：`validate_cicd_environment.py --evidence doc\tasks\20260618-build-test-backup-release\ci-cd-evidence.md` PASS。
- 结论记录：测试服与备份服均已发布 `release-20260618-0056-codeonly-e2e` 并通过验证。
- 命令记录：`task-closeout-cleanup --mode preview` 与 `--mode apply` PASS，无删除项、阻塞项或警告，保留本任务四个记录/证据文件。

## 2026-06-18 缩小 code-only 发布包

- 用户需求：低风险缩小发布包，只保留部署必需内容，去掉 `docker-build-context`。
- 计划边界：修改本机维护仓库构建脚本和测试；不执行真实服务器发布、远端写入、备份、恢复或回滚。
- 命中经验：读取发布预检清单、原 IntRuoyi 发布/备份恢复基线、项目错误预防短记忆和 CI/CD 技能。
- 命令记录：创建任务目录 `doc/tasks/20260618-shrink-release-package/`，写入 `task.md` 与 `execution-log.md`。
- 命令记录：新增 `scripts/tests/test_release_package_slimming.py`，RED 运行 `python -m pytest scripts\tests\test_release_package_slimming.py` 失败，证明当前脚本未清理最终发布包中的 `docker-build-context`。
- 命令记录：修改 `ops/deploy/publish-int-ruoyi.ps1`，在 `Write-ReleaseManifest` 前调用 `Remove-ReleaseDockerBuildContextFromPackage`，删除构建上下文并在残留时 fail fast。
- 命令记录：GREEN 运行 `python -m pytest scripts\tests\test_release_package_slimming.py` PASS，2 个测试通过；PowerShell 解析检查 PASS。
- 命令记录：`validate_cicd_environment.py --evidence doc\tasks\20260618-shrink-release-package\ci-cd-evidence.md` PASS。
- 结论记录：后续 build-release 发布包会在 manifest 生成前去掉 `docker-build-context`；未改写已部署历史发布包，避免 manifest 审计记录漂移。
- 命令记录：`task-closeout-cleanup --mode preview` 与 `--mode apply` PASS，无删除项、阻塞项或警告。

## 2026-06-18 真实 E2E 验证发布包瘦身

- 用户需求：进行真实的 E2E 测试。
- 计划边界：通过运行控制台真实前端 E2E 触发新的 `code-only` 构建发布包并验证产物瘦身；不部署测试服、备份服或正式服，不执行备份、恢复、回滚、数据库同步或 MinIO/NAS 业务数据同步。
- 命中经验：读取发布预检清单、原 IntRuoyi 发布/备份恢复基线、服务器访问基线、项目错误预防短记忆、CI/CD 技能和 Playwright 技能。
- 命令记录：创建任务目录 `doc/tasks/20260618-e2e-release-package-slimming/`，写入 `task.md`、`execution-log.md` 和 `ci-cd-evidence.md`。
- 命令记录：本机运行控制台后端 `48181` 与前端 `48182` HTTP 200；`npx` 可用。
- 命令记录：预拉并 inspect `nginx:1.27-alpine`、`eclipse-temurin:21-jre-noble`、`eclipse-temurin:21-jre` 通过。
- 命令记录：`python -m pytest scripts\tests\test_release_package_slimming.py` PASS，2 个测试通过；`ops\deploy\publish-int-ruoyi.ps1` PowerShell 解析 PASS。
- 命令记录：发布迁移策略门禁 PASS，扫描 149 个迁移；`yudao-module-dcc` 与 `yudao-server` Maven clean 均 PASS。
- 命令记录：`GREEN: experience-preflight -> PASS`，本轮只允许构建并验证 code-only 发布包，不部署、不备份、不恢复、不回滚、不做数据同步。
- 命令记录：Playwright 真实前端打开 `http://127.0.0.1:48182/`，选择 `构建发布包`，填写 releaseTag `release-20260618-1006-slim-e2e`。
- 命令记录：Playwright 真实前端 `预览命令` PASS，参数包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；不包含正式服、部署、备份、恢复或回滚动作。
- 命令记录：Playwright 真实前端执行构建，operation `op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e` 最终 `SUCCESS`。
- 命令记录：发布包已上传 NAS 路径 `Backup/ReleasePackage/release-20260618-1006-slim-e2e`；`release-status` 可读回候选，状态 `AVAILABLE`，`checksumPresent=true`。
- 命令记录：本地发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260618-1006-slim-e2e` 大小 `775.98 MiB`，递归路径和 manifest 均未命中 `docker-build-context`。
- 命令记录：与旧包 `release-20260618-0056-codeonly-e2e` 的 `1,392.39 MiB` 对比，新包减少 `616.42 MiB`。
- 命令记录：`validate_cicd_environment.py --evidence doc\tasks\20260618-e2e-release-package-slimming\ci-cd-evidence.md` PASS。
- 命令记录：Playwright Chromium 浏览器已关闭；`task-closeout-cleanup --mode preview` PASS，保留本任务三份记录/证据文件，无删除项、阻塞项或警告。
- 阻塞记录：首次 `task-closeout-cleanup --mode apply` 读任务状态为 `unknown`，原因是任务文档只有中文 `当前状态`；已补充英文 `Current Status=completed` 后重试。
- 命令记录：第二次 `task-closeout-cleanup --mode apply` PASS，无删除项、阻塞项或警告。
- 结论记录：真实 E2E 构建发布包已完成；本轮未部署测试服、备份服或正式服，未执行备份、恢复、回滚或数据同步。

## 2026-06-18 部署瘦身发布包到测试服并验证

- 用户需求：部署到测试服务器进行验证。
- 计划边界：只部署测试服 `172.30.30.58`，发布包固定为 `release-20260618-1006-slim-e2e`；不部署备份服或正式服，不执行备份、恢复、回滚、数据库整库同步或 MinIO/NAS 业务数据同步。
- 命中经验：读取发布预检清单、原 IntRuoyi 发布/备份恢复基线、服务器访问基线、登录访问基线、项目错误预防短记忆、CI/CD 技能和 Playwright 技能。
- 命令记录：创建任务目录 `doc/tasks/20260618-deploy-test-slim-release/`，写入 `task.md`、`execution-log.md` 和 `ci-cd-evidence.md`。
- 命令记录：本机运行控制台后端 `48181` 与前端 `48182` HTTP 200；`release-status` 可读回 `release-20260618-1006-slim-e2e`，状态 `AVAILABLE`，`checksumPresent=true`。
- 命令记录：测试服发布前健康检查后端 `48081` 与前端 `8081` 均 HTTP 200；SSH 只读 preflight 确认 `/opt/intruoyi/runtime` 与 `/mnt/nas` 可写、`/mnt/nas/Backup/ReleasePackage` 可读、容量满足。
- 命令记录：测试服发布前当前版本为 `IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 均运行旧 tag。
- 命令记录：`GREEN: experience-preflight -> PASS`，本轮只允许部署 `release-20260618-1006-slim-e2e` 到测试服 `172.30.30.58`，禁止备份服、正式服、备份、恢复、回滚和数据同步。
- 命令记录：Playwright 真实前端打开运行控制台，预览 `部署测试服` 命令 PASS，参数包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58` 和 `/opt/intruoyi/runtime`；不包含正式服、备份、恢复或回滚动作。
- 命令记录：Playwright 真实前端提交部署，operation `op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e` 最终 `SUCCESS`。
- 命令记录：部署后测试服 `.env` 为 `IMAGE_TAG=release-20260618-1006-slim-e2e`；backend/frontend 镜像分别为 `intruoyi-backend:release-20260618-1006-slim-e2e`、`intruoyi-frontend:release-20260618-1006-slim-e2e`，均为 `running`。
- 命令记录：测试服健康检查 PASS：后端 `48081` HTTP 200 且 `UP`，前端 `8081` HTTP 200，`pdf.worker.mjs` HTTP 200 `application/javascript`。
- 命令记录：测试服关键迁移状态只读查询 PASS，三条 `20260617_*` 迁移在当前 release/test 下均为 `SKIPPED_ALREADY_APPLIED`。
- 命令记录：Playwright 真实打开测试服前端入口，进入 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error `0`，failed request `0`。
- 观察记录：额外只读登录探针显示测试服 `测试租户/aoteman` 当前返回“登录失败，账号密码不正确”；本任务未切换账号伪装通过，也未执行业务写入。
- 命令记录：`validate_cicd_environment.py --evidence doc\tasks\20260618-deploy-test-slim-release\ci-cd-evidence.md` PASS。
- 命令记录：`task-closeout-cleanup --mode preview` 与 `--mode apply` PASS，无删除项、阻塞项或警告。

## 2026-06-18 维护仓智能排产冒烟发布配置固化

- 用户需求：发布现在从 `D:\ProjectPackage\Int\IntRuoyiMaintance` 进行，修改内容必须是维护仓发布会实际用到的；不再从 `D:\ProjectPackage\Int\IntRuoyi` 构建发布。
- 命令记录：读取 `ci-cd-environment-delivery`、`quality-assurance-test-suite` 技能与契约。
- 命令记录：读取 `AGENTS.md`、`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`docs/agent-memory/project-error-prevention.md`。
- 命令记录：检查上一任务 `doc/tasks/20260618-deploy-test-slim-release/task.md`，确认状态为 `completed`。
- 命令记录：创建任务目录 `doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/`，写入 `task.md`、`execution-log.md`、`ci-cd-evidence.md`、`qa-evidence.md`。
- 命令记录：新增 RED 契约测试 `scripts/tests/test_scheduler_smoke_release_config.py`，要求维护发布脚本使用维护仓 compose 模板并打包智能排产 smoke runner/config。
- 命令记录：`python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> RED，3 failed，确认维护发布链路缺少智能排产 smoke 固化。
- 命令记录：修改 `ops/deploy/publish-int-ruoyi.ps1`，改用维护仓 `ops/deploy/int-ruoyi-test/docker-compose.yml`；新增 smoke runner 打包、远端复制、运行态断言和 `.env` smoke 默认项。
- 命令记录：修改 `ops/deploy/int-ruoyi-test/docker-compose.yml`，新增 backend smoke 环境变量、Spring smoke 参数和 `/opt/intruoyi/runtime/smoke/bin/npm` 挂载。
- 命令记录：`python -X utf8 -m pytest scripts\tests\test_scheduler_smoke_release_config.py -q` -> PASS，3 passed；PowerShell AST parse -> PASS；`python -X utf8 -m pytest scripts\tests -q` -> PASS，5 passed；Docker Compose config -> PASS。
- 命令记录：`validate_cicd_environment.py` -> PASS；`validate_quality_assurance.py` 首次因缺少证据标记失败，补齐后 -> PASS；`git diff --check` 限定本任务文件 -> PASS；`task-closeout-cleanup --mode preview` -> PASS。
- 命令记录：`task-closeout-cleanup --mode apply` -> PASS，无删除项、阻塞项、警告或删除路径。

## 2026-06-18 发布验证通用经验沉淀

- 用户需求：将前面归纳的 1-6 条经验补充到经验或者基线里，要求能长期复用。
- 命令记录：读取 `project-experience-consolidation` 技能、`docs/release-build-preflight-lessons.md`、`docs/agent-memory/project-error-prevention.md`、任务文档和请求命令日志。
- 命令记录：`rg -n "唯一发布源头|配置必须代码化|验证发布产物|环境差异显式检查|目标环境真实运行态|故障补成门禁" docs\\release-build-preflight-lessons.md docs\\agent-memory\\project-error-prevention.md` -> 退出码 1，确认长期经验文档尚未包含六条通用规则。
- 命令记录：`apply_patch` 已更新发布预检经验文档、短记忆、任务文档和本日志。
- 命令记录：再次运行 `rg -n "唯一发布源头|配置必须代码化|验证发布产物|环境差异显式检查|目标环境真实运行态|故障补成门禁" docs\\release-build-preflight-lessons.md docs\\agent-memory\\project-error-prevention.md` -> PASS，六条基线可被命中。
- 命令记录：`git diff --check -- docs/release-build-preflight-lessons.md docs/agent-memory/project-error-prevention.md doc/tasks/20260618-release-validation-experience-baseline docs/request-command-log.md` -> PASS，无空白错误。
- 命令记录：`task-closeout-cleanup --mode preview` 与 `--mode apply` -> PASS，无删除项、阻塞项、警告或删除路径。

## 2026-06-18 维护仓构建发布到测试服务器

- 用户需求：构建发布到测试服务器。
- 命中经验：读取维护仓任务规范、发布预检经验、IntRuoyi 发布/备份恢复基线、服务器访问基线和登录访问基线；本次授权仅限测试服 `172.30.30.58`，禁止备份服、正式服、备份、恢复、回滚和数据同步。
- 命令记录：创建任务目录 `doc/tasks/20260618-build-deploy-test-server-maintenance/`，写入 `task.md`、`execution-log.md`、`ci-cd-evidence.md`、`bug-regression-evidence.md`。
- 命令记录：`python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> RED，3 failed，确认维护仓缺少 `sql/showroom` 奖项 SQL 发布契约和 schema preflight。
- 命令记录：修改 `ops/deploy/publish-int-ruoyi.ps1`，新增 `sql/mysql` + 指定 `sql/showroom/20260613_showroom_award_and_hall_item_schema.sql` 发布根、release metadata 读取、migration policy gate 参数和远端 `showroom_award` schema preflight。
- 命令记录：修改 `ops/release/release_migration_manifest.py`、`ops/release/release_migration_policy_gate.py`、`ops/release/run-release-migration-policy-gate.py`，支持 `sql_paths` / `file_prefix` / `--sql-file` / `--file-prefix`，并改为导入维护仓 `ops.release`。
- 命令记录：`python -X utf8 -m pytest scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS，3 passed；PowerShell AST parse -> PASS；`python -X utf8 -m pytest scripts\tests -q` -> PASS，8 passed。
- 命令记录：业务仓真实 `sql/showroom/20260613_showroom_award_and_hall_item_schema.sql` migration policy gate -> PASS，`migrationCount=1`；维护仓 CLI 对同一 SQL 文件 -> PASS。
- 命令记录：补充 `20260606_showroom_hall_product_canvas_layout` dependsOn 契约，业务仓两个 showroom SQL 均补 release metadata；维护仓发布脚本纳入两个 SQL 并保持顺序。
- 命令记录：修复智能排产冒烟 npm 运行时环境从远端 `.env` 导出 `MES_SMOKE_NODE_IMAGE`，避免部署覆盖测试服手工配置。
- 命令记录：前端 release build 真实失败于 `vite-plugin-top-level-await` / Rollup/SWC `Cannot set property code`；新增静态回归测试后移除该插件，真实 Vite 构建 PASS。
- 命令记录：维护控制台真实部署预览先后暴露前端未携带目标环境、后端拒绝匹配目标环境；新增前端静态测试与后端契约测试，`scripts\build.ps1` PASS。
- 命令记录：真实前端 build-release operation `op-2026-06-18T094150771556100Z-0c41d8dd-8879-42b1-b068-4e0457975aa7` -> SUCCESS；releaseTag `release-20260618-1742-showroom-sql-vite`；发布包 `813535256 bytes` / `775.85 MiB`，无 `docker-build-context`。
- 命令记录：首次测试服部署因旧 `release-20260618-1437-showroom-sql-smoke-env` 锁仍为 `RUNNING` 失败；只将该旧锁按事实收口为 `FAILED`，`updated_rows=1`。
- 命令记录：第二次测试服部署因 `preflight-plan.json status=blocked` 失败，阻塞项为 `20260613_showroom_award_and_hall_item_schema` 缺依赖 `20260606_showroom_hall_product_canvas_layout`。
- 命令记录：新增 RED 用例 `test_preflight_accepts_dependency_applied_earlier_in_same_plan`，修复 `release_preflight_plan.py` 按 manifest 顺序累积同包前置 `APPLY` 迁移；业务仓测试 `python -X utf8 -m pytest script\tests\test_release_preflight_plan.py -q` -> PASS，9 passed；维护仓/业务仓脚本哈希一致。
- 命令记录：只将本次失败的 `test-release-20260618-1742-showroom-sql-vite` 锁收口为 `FAILED`，`updated_rows=1`，随后通过 Playwright 真实前端再次点击“部署测试服”。
- 命令记录：最终部署 operation `op-2026-06-18T111139027664400Z-8c8c1cd0-b797-4b05-ba38-56190a4fb52a` -> SUCCESS；日志显示 `Publish completed for test`。
- 命令记录：测试服验证 PASS：`.env` `IMAGE_TAG=release-20260618-1742-showroom-sql-vite`；backend/frontend 镜像 tag 匹配并 running；后端健康 `UP`；前端 HTTP 200。
- 命令记录：schema 验证 PASS：`20260606_showroom_hall_product_canvas_layout`、`20260613_showroom_award_and_hall_item_schema`、`20260618_showroom_publicity_role_menu_scope` 均 `APPLIED`；展厅奖项表、混合展厅项表、布局列和 6 个关键索引存在。
- 命令记录：Playwright 真实打开测试服前端 `http://172.30.30.58:8081/`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0，截图保存到任务目录。
- 命令记录：维护仓测试、业务仓发布预检测试、前端构建契约测试、PowerShell AST、CI/CD/bug/database evidence validators 均 PASS。
- 命令记录：`task-closeout-cleanup --mode preview` 与 `--mode apply` PASS，无删除项、阻塞项、警告或删除路径。

## 2026-06-18 发布后角色 E2E 门禁

- 用户需求：每次发布后在测试服务器用芋道源码租户真实账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证角色页签隔离、子页访问和智能排产冒烟测试；遇到错误先全部记录，再统一修复、重新构建发布到测试服务器并复测直到满足目标。
- 命中经验：读取发布预检经验、服务器访问基线、登录访问基线、备份/发布/恢复基线和项目错误预防短记忆；本次高风险动作授权仅限测试服 `172.30.30.58` 和指定三账号真实 E2E。
- 命令记录：创建任务目录 `doc/tasks/20260618-post-release-role-e2e-gate/`，写入 `task.md`、`execution-log.md`、`qa-evidence.md`、`bug-regression-evidence.md`，记录 `GREEN: experience-preflight -> PASS`。
- 命令记录：读取前端 Playwright E2E 脚本、智能排产冒烟测试脚本、展厅和 DCC 菜单 SQL 线索，确认前端仓 `playwright` 依赖可解析。
## 2026-06-18 post-release-role-e2e-gate continuation

- 用户需求：继续构建发布到测试服务器，并把三角色真实 E2E 暴露的问题修复到通过。
- 执行命令：`python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q`
- 执行命令：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql`
- 执行命令：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\showroom --sql-file sql\showroom\20260605_showroom_product_revision_attachment_schema.sql --sql-file sql\showroom\20260606_showroom_hall_product_canvas_layout.sql --sql-file sql\showroom\20260613_showroom_award_and_hall_item_schema.sql --sql-file sql\showroom\20260615_showroom_hall_canvas_background.sql --file-prefix sql/showroom`
- 执行命令：`git diff --check -- <current task files>`
# 2026-06-19 正式服务器发布注意事项确认

- 用户需求：当前的正式服务器发布需要注意什么。
- 执行命令：读取 `docs/experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\SKILL.md`、`C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\references\cicd-contract.md`；创建 `doc/tasks/20260619-prod-release-notes/` 任务记录。

# 2026-06-19 发布后三角色 E2E 门禁新线程接续

- 用户需求：继续上个坏掉线程跑到一半的目标：每次发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证权限页签、子页访问和智能排产冒烟；失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- 执行命令：读取 `bug-regression-fix-loop`、`quality-assurance-test-suite`、`playwright` 技能与契约；读取 `doc/tasks/20260618-post-release-role-e2e-gate/` 任务文档、执行日志、QA/缺陷证据和最新 evidence 列表；读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`。
- 执行命令：摘要读取 `post-release-role-e2e-1781826823171.json` 与 `runtime-console-build-deploy-1781803561178.json`，确认最新发布成功但三角色 E2E 仍有 4 个失败。
- 执行命令：新增并运行 RED 契约 `MesProAutoScheduleControllerContractTest`、`tests/e2e/mes-auto-schedule-dependency-post-static.spec.js`；运行 `test_scheduler_smoke_release_contract.py` 暴露 smoke 用户名契约失败。
- 执行命令：修改后端 `/mes/pro/auto-schedule/dependencies` 增加 POST body、前端依赖查询改 POST、SQL/发布测试统一合法 smoke 用户名；`mvn -pl yudao-module-mes -Dtest=MesProAutoScheduleControllerContractTest test` PASS；`node tests\e2e\mes-auto-schedule-dependency-post-static.spec.js` PASS；`python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py script\tests\test_post_release_role_e2e_gate_sql.py -q` PASS。
- 执行命令：只读核对测试服数据库 154 条 `infra_file.config_id=28` 产品封面引用与 MinIO 对象缺口；从已有真实对象 evidence 生成 `minio-showroom-cover-20260602-repair-1781842832636.tar`，同步到测试服 MinIO 默认 `yudao` bucket，补齐对象数到 154，并用 `curl -I` 验证失败样例返回 `image/png`。
- 执行命令：运行本地门禁、构建并发布 `release-20260619-1229-role-e2e-gate-post-deps-smoke-user` 到测试服；证据 `runtime-console-build-deploy-1781844498623.json` 为 PASS，测试服 `.env`、镜像 tag、后端 health、前端 HTTP 200 和 smoke username 迁移状态均通过。
- 执行命令：运行三角色真实 E2E，证据 `post-release-role-e2e-1781844737245.json` 为 FAIL；记录 `gaomin`/`wangsiyu` 已通过，`zhaojie` smoke 失败根因为 smoke 账号密码过期，另有未读消息请求 `net::ERR_ABORTED` 被 E2E 脚本误判。
- 执行命令：新增 smoke 密码新鲜度 SQL 迁移和 E2E 请求失败静态回归测试；`python -X utf8 -m pytest ... -q` -> PASS，114 passed；`node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> PASS；迁移策略门禁 -> PASS，包含 `20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix`。
- 执行命令：准备重新构建发布测试服修复版 `release-20260619-1301-role-e2e-gate-smoke-password-freshness`；命令为设置 `RUNTIME_CONSOLE_RELEASE_TAG`、`RUNTIME_CONSOLE_REASON`、`RUNTIME_CONSOLE_TIMEOUT_MS`、`RUNTIME_CONSOLE_POLL_INTERVAL_MS` 后运行 `node doc/tasks/20260618-post-release-role-e2e-gate/scripts/runtime-console-build-deploy.cjs`。
- 执行命令：发布后只读核验测试服 `release-20260619-1301-role-e2e-gate-smoke-password-freshness` 的后端 health、前端 HTTP 200、远端 `.env`、backend/frontend 镜像 tag、`20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix` 迁移状态与 smoke 账号 `password_update_time`。
- 执行命令：准备以 `POST_RELEASE_ROLE_E2E_PASSWORD=111111` 运行 `node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs`，在测试服完整复测 `gaomin`、`zhaojie`、`wangsiyu`。
- 执行命令：解析 `post-release-role-e2e-1781846902055.json` 与远端 `smoke-report.json`，确认第三轮失败只剩 `zhaojie` 智能排产 smoke，根因为默认 ERP 计划完工时间 `2026-06-20 17:27:00` 落在周六，被 Kingdee 车间工作日历拒绝。
- 执行命令：新增 RED 静态合同并修复 `tests/e2e/smart-scheduling-smoke-real-flow.e2e.js`，将默认 `MES_SMOKE_ERP_PLANNED_FINISH_TIME` 改为下一个工作日；`node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` -> PASS。
- 执行命令：准备重新构建发布测试服修复版 `release-20260619-1335-role-e2e-gate-weekday-smoke-finish`；命令为设置 `RUNTIME_CONSOLE_RELEASE_TAG`、`RUNTIME_CONSOLE_REASON`、`RUNTIME_CONSOLE_TIMEOUT_MS`、`RUNTIME_CONSOLE_POLL_INTERVAL_MS` 后运行 `node doc/tasks/20260618-post-release-role-e2e-gate/scripts/runtime-console-build-deploy.cjs`。
- 执行命令：读取最新证据 `post-release-role-e2e-1781848897783.json` 与截图 `zhaojie-smoke-job-trigger-failure-1781848897783.png`，确认 `gaomin`/`wangsiyu` 已通过，`zhaojie` 仅剩 ERP 金蝶同步运行页生产工单“执行一次”按钮不可见。
- 执行命令：只读查询测试服 `system_users`、`system_role`、`system_role_menu`、`system_menu`、`system_tenant`、`system_tenant_package`，并用 Playwright 真实登录 `messmokeerp` 读取 `get-permission-info`；确认旧 `infra:job:trigger` 绑定在定时任务父链下，被 `filterDisableMenus()` 因缺父链过滤出登录态权限。
- 执行命令：新增 RED 契约 `test_post_release_role_gate_smoke_erp_job_permission_fix_surfaces_manual_trigger_button`，要求新增迁移在 ERP 同步菜单 `6013` 下补齐 `infra:job:query` 与 `infra:job:trigger` 按钮权限并绑定 ERP smoke 角色；首次运行 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，缺少迁移文件。
- 执行命令：新增 `sql/mysql/20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix.sql`；`python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，8 passed。
- 执行命令：`python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，115 passed。
- 执行命令：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，migrationCount=157，包含 `20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix`。
- 执行命令：读取 `runtime-console-build-deploy-20260619-142434.out.log`、operation JSON 和部署日志，确认 `release-20260619-1430-role-e2e-gate-erp-job-permission` 构建与测试服部署 PASS，证据为 `runtime-console-build-deploy-1781851424303.json`。
- 执行命令：测试服核验 `.env` `IMAGE_TAG`、docker compose backend/frontend 镜像 tag、后端 health HTTP 200、前端 HTTP 200、迁移 `20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix` 状态 `APPLIED`。
- 执行命令：`POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `post-release-role-e2e-1781851764170.json`，三账号页面验收仅剩 `zhaojie` 智能排产 smoke 失败。
- 执行命令：读取远端 `output/artifacts/smoke-report.json`、`backend-runner.log`、`created-erp-production-order.json`、`production-order-sync-trigger.json`、`synced-mes-work-order.json` 和后端日志，确认 ERP 工单创建、MES 同步、手动触发任务均已通过，失败在工单不在 `READY_TO_ADMIT` 入池差异列表。
- 执行命令：只读查询测试服 `mes_pro_work_order`、`mes_pro_route_product`、`mes_pro_route`、`mes_pro_route_version`、`mes_pro_route_process`、`mes_md_item`、`mes_md_unit_measure`，确认旧默认产品 `AW.106.03.08.1007` 无路线绑定；候选 `YXN.069.001.1003` 为路线就绪产品，单位 `zhi`。
- 执行命令：读取 smoke Excel 和导入解析/归属代码，确认远端 runner 依赖残留静态 Excel，且 Excel 写死旧产品和旧工单号，后续必须改为每次运行动态生成。
- 执行命令：新增 RED 契约后运行 `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL，发布脚本仍保留旧默认产品且 runner package 缺 `xlsx`。
- 执行命令：新增 RED 静态契约后运行 `node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> FAIL，runner 仍要求固定 `MES_SMOKE_EXCEL_FILE`。
- 执行命令：修改业务仓和维护仓发布脚本，默认 smoke 产品改为 `YXN.069.001.1003`、单位 `zhi`，并显式迁移旧 `AW.106.03.08.1007` / `PCS`；runner package 增加 `xlsx`。
- 执行命令：修改 `smart-scheduling-smoke-real-flow.e2e.js`，运行前动态生成 `feedback-workbook-<smokeRunId>.xlsx`，写入本次工单号、产品编码、B010 工序和 `sourceFileSha256`。
- 执行命令：`python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> PASS；`node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> PASS；`node --check tests\e2e\smart-scheduling-smoke-real-flow.e2e.js` -> PASS；维护仓发布契约和两份 PowerShell AST -> PASS。
- 执行命令：完整本地回归 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，115 passed；MySQL migration policy -> PASS，157；post-release-role E2E static、dependency POST static、smart scheduling smoke static -> PASS。

# 2026-06-19 发布后三角色 E2E 门禁终轮复测

- 用户需求：每次发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证角色页签、子页访问和智能排产冒烟；失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- 执行命令：读取最新部署 evidence `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781854878582.json` 与输出 `runtime-console-build-deploy-20260619-152237.out.log`，确认 `release-20260619-1518-role-e2e-gate-route-ready-smoke` 已成功构建并部署测试服，准备直接运行三角色真实 E2E。

## 2026-06-19 排产工序快照缺列修复

- 用户需求：继续同一任务，修复测试服最新发布后仅剩的 `zhaojie` 智能排产 smoke 失败，并在修复后重新构建发布到测试服、再跑三账号真实 E2E。
- 执行命令：读取 `bug-regression-fix-loop` 与 `playwright` 技能、`doc/tasks/20260618-post-release-role-e2e-gate/task.md`、`execution-log.md`、`bug-regression-evidence.md`、`qa-evidence.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，接续本轮发布后角色 E2E 修复闭环。
- 执行命令：摘要读取 `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781856280345.json`，确认 `gaomin` 与 `wangsiyu` 已通过，仅剩 `zhaojie` 智能排产 smoke 失败。
- 执行命令：`git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro show HEAD:sql/mysql/20260619_mes_schedule_order_process_snapshot_identity_p8.sql` -> FAIL，确认当前 `HEAD` 尚未包含排产工序快照缺列修复迁移。
- 执行命令：`python -X utf8 -m pytest script\tests\test_mes_scheduling_closed_loop_sql.py -q` -> PASS，6 passed。
- 执行命令：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，migrationCount=158，包含 `20260619_mes_schedule_order_process_snapshot_identity_p8`。

## 2026-06-19 A03388 设备工序产能冲突发布修复

- 用户需求：继续同一任务，修复 `release-20260619-1638-role-e2e-gate-process-snapshot` 发布后仅剩的 `zhaojie` 智能排产 smoke 失败，并再次构建发布到测试服、复跑三账号真实 E2E。
- 执行命令：`$env:RUNTIME_CONSOLE_RELEASE_TAG='release-20260619-1638-role-e2e-gate-process-snapshot'; $env:RUNTIME_CONSOLE_REASON='post-release role E2E gate: add mes schedule order process snapshot schema fix'; $env:RUNTIME_CONSOLE_TIMEOUT_MS='7200000'; $env:RUNTIME_CONSOLE_POLL_INTERVAL_MS='30000'; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/runtime-console-build-deploy.cjs` -> PASS，证据 `runtime-console-build-deploy-1781858207843.json`。
- 执行命令：`$env:POST_RELEASE_ROLE_E2E_PASSWORD='111111'; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `post-release-role-e2e-1781858432621.json`，仅剩 `zhaojie` smoke 失败。
- 执行命令：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json"`，确认远端失败点为 `/admin-api/mes/pro/auto-schedule/preview`，错误 `设备工序产能存在冲突: machineryId=47, processId=900370`。
- 执行命令：`ssh root@172.30.30.58 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env"`，确认测试服已运行 `release-20260619-1638-role-e2e-gate-process-snapshot`。
- 执行命令：读取 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260608-admin-resource-capacity-unify\task.md` 与 `execution-log.md`，确认本机曾对 admin 租户 A03388 的重复高产能做过手工治理，但未沉淀为正式发布迁移。
- 执行命令：修改 `script\tests\test_post_release_role_e2e_gate_sql.py` 新增 `20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix.sql` 契约；首次运行 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，缺少迁移文件。
- 执行命令：新增 `sql/mysql/20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix.sql`，再次运行 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，9 passed。
- 执行命令：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，migrationCount=159，包含 `20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix`。

## 2026-06-19 自动编码流水恢复与展厅误报收敛

- 用户需求：继续发布后三角色 E2E 门禁，先完整记录剩余失败，再统一修复并重新构建发布测试服。
- 执行命令：读取 `bug-regression-fix-loop` 技能、`docs/experience-index.md`、维护仓/业务仓当前任务文档与最新 E2E 证据，确认 `gaomin` 仅剩 `/showroom/company` 的 `dict-data/simple-list` 中止误报，`zhaojie` 仅剩智能排产 `apply` 的 `编码生成失败`。
- 执行命令：只读核对测试服 `172.30.30.58` 的自动编码数据与运行态，包括 `mes_md_auto_code_rule`、`mes_md_auto_code_part`、`mes_md_auto_code_record`、`redis-cli GET mes:md:auto_code:900070` 与 `docker logs intruoyi-backend --since 45m | grep 'MesMdAutoCodeRecordServiceImpl\|编码生成失败'`，确认规则存在、Redis key 缺失、历史记录停在 `PT-0006/PT-0007`，失败堆栈命中 `generateAutoCode(...:90)`。
- 执行命令：修改 `doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e-static.test.cjs` 与 `post-release-role-e2e.cjs`；首次运行 `node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e-static.test.cjs` -> FAIL，脚本尚未将 `GET /admin-api/system/dict-data/simple-list` 的 `net::ERR_ABORTED` 归为 benign request failure；修复后同命令 -> PASS。
- 执行命令：在业务仓新增自动编码恢复契约与实现：更新 `MesMdAutoCodeSerialNumberPartStrategyTest`、`MesMdAutoCodeRedisDAO`、`MesMdAutoCodeRecordMapper`、`MesMdAutoCodeSerialNumberPartStrategy`；首次运行 `mvn -pl yudao-module-mes -Dtest=MesMdAutoCodeSerialNumberPartStrategyTest test` -> FAIL，缺少 `selectLatestSerialRecord(...)` 契约；修复后运行 `mvn -pl yudao-module-mes "-Dtest=MesMdAutoCodeSerialNumberPartStrategyTest,MesProAutoScheduleServiceImplTest" test` -> PASS，28 个测试通过。

## 2026-06-19 eDHR 批次触发门禁修复

- 用户需求：继续同一任务，修复自动编码问题后的新真实阻塞 `排产完成创建 eDHR 批次缺少前置条件：工序与批记录绑定`，再重新构建发布测试服并复跑三角色真实 E2E。
- 执行命令：读取维护仓最新 E2E 证据 `post-release-role-e2e-1781869546155.json`、业务仓旧任务 `20260619-post-release-role-e2e-gate-autocode-counter-recovery`、当前调度与 eDHR 服务代码、相关测试 `MesProAutoScheduleServiceImplTest`、`MesProAutoScheduleAlgorithmContractTest`、`MesProEdhrBatchExecutionServiceTest`，确认阻塞已从自动编码推进到 eDHR 触发门禁。
- 执行命令：只读核对测试服路线 `900026` 的 `mes_pro_route_use_process_config`、`mes_pro_route_use_process_batch_record` 与全局 `mes_pro_edhr_work_task_assignment_rule`，确认当前 smoke 路线没有任何启用中的 `BATCH` 配置和批记录绑定，不能被当成 eDHR 路线强制建批次。
- 执行命令：修改 `MesProAutoScheduleServiceImpl`，新增“仅对存在启用中 `BATCH` 工序配置的路线触发 eDHR 批次创建”的正式门禁；同步补 `MesProAutoScheduleServiceImplTest` 回归用例，覆盖“普通路线跳过”和“已启用 eDHR 路线继续 fail fast”，并为 `MesProAutoScheduleAlgorithmContractTest`、`MesProAutoScheduleContractTest` 补齐新的 mapper 依赖。
- 执行命令：`mvn -pl yudao-module-mes "-Dtest=MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> 先因测试类型声明缺失与 Mockito 严格桩校验失败，修正后 -> PASS，35 passed。
- 执行命令：`mvn -pl yudao-module-mes "-Dtest=MesProEdhrBatchExecutionServiceTest,MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> PASS，72 passed；确认本次改动没有放宽 eDHR 服务内部 fail-fast 契约。

## 2026-06-19 报工审批人身份解析门禁修复

- 用户需求：继续同一任务，在 `release-20260619-2055-role-e2e-gate-edhr-trigger` 发布后记录 `zhaojie` 智能排产 smoke 的新失败，统一修复后重新构建发布测试服并完整复测三账号。
- 执行命令：读取 `bug-regression-fix-loop` 技能、`D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、维护仓当前任务文档，以及后端上一任务 `20260619-post-release-role-e2e-gate-edhr-batch-trigger-gate/task.md`，建立新的后端任务 `20260619-post-release-role-e2e-gate-feedback-approver-identity`。
- 执行命令：`ssh root@172.30.30.58 "grep -n 'MES_SMOKE_' /opt/intruoyi/runtime/.env"` -> PASS，确认测试服当前存在 `MES_SMOKE_SUPERVISOR_USERNAME=messmokesupervisor`，但没有 `MES_SMOKE_FEEDBACK_APPROVER_NAME`。
- 执行命令：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json"` -> FAIL，确认最新真实 smoke 失败点为 `/admin-api/mes/pro/feedback/import-record/attribute`，错误 `第三方报工导管报工第 2 行工段长匹配到多名用户：eDHR矩阵-审批人`。
- 执行命令：只读查询测试服 `system_users`、`system_user_role`、`system_role`，确认 `tenant_id=1` 下 `mes_smoke_supervisor(id=910253)` 与 `messmokesupervisor(id=910260)` 均启用且共用 nickname `eDHR矩阵-审批人`，角色同为 `报工冒烟审批员`。
- 执行命令：修改后端 `MesProFeedbackImportRecordServiceImpl` 与测试 `MesProFeedbackImportRecordServiceImplTest`，让审批人解析优先按 exact username 命中，未命中再按 exact nickname 保持原契约，同时对重复 nickname 继续 fail fast。
- 执行命令：修改维护仓 `ops/deploy/publish-int-ruoyi.ps1`、`ops/deploy/int-ruoyi-test/docker-compose.yml` 与 `doc/tasks/20260618-post-release-role-e2e-gate/scripts/validate-maintenance-publish-contract.cjs`，显式输出并校验 `MES_SMOKE_FEEDBACK_APPROVER_NAME=$effectiveMesSmokeSupervisorUsername`。
- 执行命令：`mvn -pl yudao-module-mes "-Dtest=MesProFeedbackImportRecordServiceImplTest" test` -> 先因负例存在未执行路径的多余 stub 导致 Mockito `UnnecessaryStubbingException`，删除多余 stub 后 -> PASS，6 passed。
- 执行命令：`node D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，确认维护发布契约包含 `MES_SMOKE_FEEDBACK_APPROVER_NAME` 与 supervisor username 绑定。
- 执行命令：`$env:RUNTIME_CONSOLE_RELEASE_TAG='release-20260619-2143-role-e2e-gate-feedback-approver'; ...; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/runtime-console-build-deploy.cjs` -> PASS，证据 `runtime-console-build-deploy-1781877791317.json`。
- 执行命令：`$env:POST_RELEASE_ROLE_E2E_PASSWORD='111111'; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `post-release-role-e2e-1781877963367.json`；`gaomin` 与 `wangsiyu` 通过，`zhaojie` 仍失败。
- 执行命令：`ssh root@172.30.30.58 "grep -n 'MES_SMOKE_FEEDBACK_APPROVER_NAME\|MES_SMOKE_SUPERVISOR_USERNAME' /opt/intruoyi/runtime/.env"`、`cat .../output/artifacts/config.json`、`cat .../smoke-report.json` -> PASS/FAIL，确认测试服 `.env` 已有 `MES_SMOKE_FEEDBACK_APPROVER_NAME=messmokesupervisor`，但 smoke `config.json` 仍是 `feedbackApproverName=eDHR矩阵-审批人`，失败仍落在 `/admin-api/mes/pro/feedback/import-record/attribute`。
- 执行命令：读取 `MesProSchedulerWorkbenchSmokeTestServiceImpl.java`、`MesProSchedulerWorkbenchSmokeProcessControllerImpl.java`、维护仓/业务仓 `publish-int-ruoyi.ps1` 中 `New-SchedulerSmokeNpmWrapperContent`，确认 scheduler smoke 容器环境变量白名单缺少 `MES_SMOKE_FEEDBACK_APPROVER_NAME`。
- 执行命令：修改维护仓/业务仓发布脚本的 smoke wrapper 白名单、业务仓 compose 契约与 `script/tests/test_scheduler_smoke_release_contract.py`，补齐 `MES_SMOKE_FEEDBACK_APPROVER_NAME` 透传并加严静态门禁。
- 执行命令：`python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> 先 FAIL（业务仓发布脚本仍未写出 `$effectiveMesSmokeFeedbackApproverName`），补齐后 -> PASS，3 passed。
- 执行命令：`node D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，确认维护仓 wrapper 白名单也已包含 `MES_SMOKE_FEEDBACK_APPROVER_NAME`。
- 执行命令：`$env:RUNTIME_CONSOLE_RELEASE_TAG='release-20260619-2230-role-e2e-gate-feedback-approver-wrapper'; ...; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/runtime-console-build-deploy.cjs` -> PASS，证据 `runtime-console-build-deploy-1781882335880.json`。
- 执行命令：`ssh root@172.30.30.58 "grep -n 'MES_SMOKE_FEEDBACK_APPROVER_NAME\|MES_SMOKE_SUPERVISOR_USERNAME' /opt/intruoyi/runtime/.env"` -> PASS，确认测试服运行态包含 `MES_SMOKE_FEEDBACK_APPROVER_NAME=messmokesupervisor`。
- 执行命令：`$env:POST_RELEASE_ROLE_E2E_PASSWORD='111111'; node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> PASS，证据 `post-release-role-e2e-1781882555897.json`，三账号全部通过。
- 执行命令：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/config.json"` -> PASS，当前 PASS 产物显示 `feedbackApproverName=messmokesupervisor`。
- 执行命令：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json"` -> PASS，当前 PASS 产物显示 `approverName=messmokesupervisor`、`approveUserId=910260`、`status=PASS`。

# 2026-06-20 发布后三角色 E2E 门禁收尾

- 用户需求：继续把已通过的发布后三角色测试服验收任务做完收尾，清理附属产物、补齐任务归档，并在维护仓/后端仓做选择性提交。
- 执行命令：读取 `task-closeout-cleanup` 技能与 `references/closeout-rules.md`，重新核对维护仓主任务 `doc/tasks/20260618-post-release-role-e2e-gate/task.md`、`execution-log.md` 与两个仓库 `git status --short`。
- 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260618-post-release-role-e2e-gate --mode preview` -> PASS，确认主任务仅应保留 `task.md`、`execution-log.md` 与最终 PASS 的构建/三角色 E2E evidence。
- 执行命令：手工删除维护仓主任务 `Cleanup Candidates` 中的 `bug-regression-evidence.md`、`qa-evidence.md`、`scripts/`、中间 build/E2E evidence、screenshots、MinIO 同步附属目录与压缩包；对长路径残留目录改用 `\\?\\` 长路径删除后复核当前目录树仅剩 `task.md`、`execution-log.md` 和两份最终 evidence。
- 执行命令：核对后端仓四个已完成子任务目录状态均为 `COMPLETED`，并盘点剩余未挂任务的发布契约/SQL/排产链路改动，准备补充后端收口任务目录后再做选择性提交。

# 2026-06-20 当前最新程序测试服后再正式服发布

- 用户需求：在不影响正式服 `website` 数据前提下，把当前最新程序先发布到测试服，再发布到正式服；用户已明确授权访问和修改正式服务器。
- 执行命令：读取维护仓 `AGENTS.md`、`docs/experience-index.md`，确认本次为高风险发布任务，必须先建 `doc/tasks/<task-id>/`、补齐经验门禁并在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`，之后才能进入服务器写入或发布动作。
- 执行命令：读取 `$fupan` 技能说明、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`docs/agent-memory/project-error-prevention.md`，提炼本次发布强制门禁与正式服 `website` 数据保护边界。
- 执行命令：核对上一维护仓任务 `doc/tasks/20260620-fupan-post-release-role-e2e-gate/task.md` 状态为 `COMPLETED`，允许开启新任务 `doc/tasks/20260620-prod-release-current-latest/`。
- 执行命令：创建 `doc/tasks/20260620-prod-release-current-latest/`，新增 `task.md` 与 `execution-log.md`，记录用户授权、发布顺序、正式服数据边界、经验门禁与高风险动作前置状态；当前尚未执行测试服或正式服写入/发布动作。

- 用户需求：继续。
- 执行命令：读取正式服阻塞 SQL `20260617_mes_scheduler_role_smart_scheduling_tab.sql`、维护仓当前任务文档/执行日志、服务器访问基线与 `$fupan` 技能说明，明确下一步聚焦正式服真实阻塞排查。
- 执行命令：通过 `ssh root@172.30.30.57` 只读查询正式服 `intruoyi-mysql`，核对 `system_tenant_package` 表结构、`system_menu` 中 `900120/5590/5580/5262/5540`、正式租户 `package_id` 绑定与排产/计划角色基线 -> PASS；确认正式服阻塞根因是“无目标排产角色”被错误当成迁移失败。
- 执行命令：在后端仓建立任务 `20260620-mes-scheduler-role-prod-baseline-gate`，先补 RED 契约测试，再将 `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 改成“无目标角色时 no-op 并清理临时表”；执行 `python -X utf8 -m pytest script\\tests\\test_mes_scheduler_role_smart_scheduling_tab_sql.py -q` -> 先 `1 failed, 4 passed`，修复后 `5 passed`；随后 `python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` -> PASS。
- 执行命令：后端仓按任务目录设置 `TDD_TASK_DIR`，将 DCC 依赖修复、preflight planner 修复与当前“无目标角色 no-op”修复一起提交为 `9667a05ff2 任务: 修复正式发布迁移阻塞`。
- 执行命令：在维护仓执行 `publish-int-ruoyi.ps1 -Mode build-release ... -ReleaseTag release-20260620-current-head-prod-target-v7 -SkipDatabaseSync -SkipMinioSync` -> PASS，生成并上传 `Backup/ReleasePackage/release-20260620-current-head-prod-target-v7`。
- 执行命令：执行 `run-deploy-precheck-report.ps1 -PackagePath ...release-20260620-current-head-prod-target-v7 -Environment prod -Mode report-only -OutputPath ...prod-deploy-precheck-report-v7.json` -> PASS，并补齐 `prod-preflight-release-dry-run-v7.json`。
- 执行命令：执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260620-current-head-prod-target-v7 ... -ProdDryRunEvidencePath ...prod-preflight-release-dry-run-v7.json -SkipDatabaseSync -SkipMinioSync` -> PASS；日志确认正式服发布锁最终 `LOCK_RELEASED`、后端/前端真实启动成功。
- 执行命令：发布后只读核对 `grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env`、`docker ps | grep intruoyi-website` 与 `show-int-ruoyi-remote-status.ps1 -Component full -Json` -> PASS；正式服当前 `IMAGE_TAG=release-20260620-current-head-prod-target-v7`，HTTP 健康检查均为 `200`，`intruoyi-website` 仍为 `nginx:1.27-alpine` 且保持 `Up 2 weeks`。
- 当前结论：当前最新程序已按 `code-only` 边界先测试服验证、后正式服发布成功，正式服 `website` 运行态未被影响；下一步仅剩维护仓任务文档收尾、清理预览与必要提交。

## 2026-06-20 前端页面走完整发布测试服/正式服/备份服全流程

- 用户需求：正式走一遍构建发布到测试服务器、发布到正式服务器和备份服务器的全流程；全程使用页面前端进行操作，禁止直接调用接口；遇到问题先记录、修复后继续，直到全流程一次性走通。
- 执行命令：读取 `docs/experience-index.md`，命中并读取 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`docs/agent-memory/project-error-prevention.md`，确认本任务必须通过运行控制台页面按钮触发 build/deploy，不能命令行或接口替代。
- 执行命令：创建维护仓任务 `doc/tasks/20260620-frontend-release-full-flow/`，写入 `task.md` 与 `execution-log.md`，记录页面流、环境边界、备份服 `/mnt/intruoyi-data` 门禁和“先记录失败再修复重走”的约束。
- 执行命令：只读核对 `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java`、`RuntimeControlOperationAction.java`、`frontend/src/App.vue`、`frontend/src/api/runtimeControl.ts`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 与历史请求日志；确认“标记测试通过”的恢复集候选来自 NAS `Backup/BackupPackage` 最终备份点，当前页面 `No data` 的根因是缺少最终可用恢复点，不是前端下拉异常，也不能手填旧候选 ID 绕过。
- 执行命令：Playwright 在同一真实页面链路切换到“立即备份”并点击“预览命令”；页面返回 `环境未授权执行写动作: 正式环境写动作未授权，当前独立控制台默认禁止写入、重启、发布、回滚或恢复正式服务器`。
- 执行命令：只读核对 `RuntimeControlService#guardWrite`、`backend/src/main/resources/application.yaml`、gitignored 的 `config/runtime-control.local.yaml`、`Get-NetTCPConnection -LocalPort 48181` 与当前 `java -jar backend\\target\\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 进程；确认本地 `production-write-enabled: true` 已存在，但 `prod.access-enabled` 仍沿用基础配置 `false`，因此正式环境写动作在页面预览前即被统一阻断。
- 执行命令：在本机 `config/runtime-control.local.yaml` 补齐 `maintenance.runtime-control.environments.prod.access-enabled: true` 并重启 `127.0.0.1:48181`，随后用 Playwright 重新预览“立即备份”；页面已进入真实备份脚本预览，命令为 `backup-ops.ps1 -Mode backup-now -NonInteractive -TargetEnvironment prod -OperatorName local-operator`。
- 执行命令：Playwright 在真实页面点击“立即备份”执行后，operation `op-2026-06-20T164241687774200Z-08e3c043-8037-4198-a9d1-78a653d80739` 立即失败；页面日志与本机 `runtime/runtime-control/logs/op-2026-06-20T164241687774200Z-08e3c043-8037-4198-a9d1-78a653d80739.log` 一致返回 `INTBK-1001`，原因是缺少本机启动前置文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\config\backup-ops.secrets.json`。
- 执行命令：只读核对 `ops/backup-ops/scripts/backup-ops.ps1`、`modules/Core/Config.psm1`、`backup-ops.secrets.example.json`，并在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\backup-ops\config\backup-ops.secrets.json` 找到同名本机私有 secrets 来源；结构比示例模板多出 `credentialSources`，说明当前阻塞是维护仓本机私有备份凭据文件缺失，不能用示例模板或空值代替。
- 执行命令：在维护仓 `.gitignore` 增加 `ops/backup-ops/config/backup-ops.secrets.json`，随后把原 IntRuoyi 后端仓 `ruoyi-vue-pro\script\backup-ops\config\backup-ops.secrets.json` 恢复到维护仓同路径；只校验存在性、加载成功与 Git 忽略状态，不在日志中回显敏感内容。
- 执行命令：Playwright 回到真实运行控制台页面，重新选择“立即备份”，填写操作原因与页面确认文本后预览/执行；新 operation `op-2026-06-20T165254350585600Z-ba3295d1-f71e-4945-ac40-cd5911b1dd2c` 已成功提交到本机执行队列，不再报缺少 secrets 文件。
- 执行命令：只读查看新 operation 日志与状态文件，确认新的真实页面阻塞变为 `INTBK-1003`：`backup-ops.ps1` 要求显式传入 `-ProductionBackupConfirmText 'PROD-BACKUP-172.30.30.57'`；而运行控制台预览参数只传 `-Mode backup-now -NonInteractive -TargetEnvironment prod -OperatorName local-operator`，页面输入框值没有透传到脚本。
- 执行命令：新增后端 RED 用例 `backupNowPreviewPassesProductionBackupConfirmTextToScript`，首次运行 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#backupNowPreviewPassesProductionBackupConfirmTextToScript test` -> FAIL；先暴露测试环境默认 `prod.access-enabled=false` 的授权前置，补齐测试授权后再次运行，继续 FAIL 于控制台统一只接受 `prodConfirmText=PROD`，而正式备份脚本实际要求 `PROD-BACKUP-172.30.30.57`。
- 执行命令：修复运行控制台正式备份契约：后端对 `backup-now` 保留正式写动作授权门禁，但不再强制复用通用 `PROD` 校验；同时在 `backup-now/prod` 预览与执行命令中透传 `-ProductionBackupConfirmText <页面输入值>`，前端同步将该动作确认输入提示改为 `PROD-BACKUP-172.30.30.57`。
- 执行命令：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#backupNowPreviewPassesProductionBackupConfirmTextToScript test` -> PASS；`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS；`pnpm --dir frontend typecheck` -> PASS。
- 执行命令：停止占用 `127.0.0.1:48181` 的旧 Java 进程，执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` 与 `scripts/start.ps1`，确认 `http://127.0.0.1:48181/actuator/health` 返回 `200`；Playwright 重新打开本地运行控制台，核对“立即备份”表单确认标签/占位已更新为 `正式备份确认` / `PROD-BACKUP-172.30.30.57`。
- 执行命令：Playwright 在真实页面重新选择“立即备份”，填写原因“页面真实发布全链路验证：立即备份生成恢复集”和确认文本 `PROD-BACKUP-172.30.30.57`，预览命令确认已包含 `-ProductionBackupConfirmText PROD-BACKUP-172.30.30.57`，随后点击“执行”生成 operation `op-2026-06-20T170847988455500Z-6d597657-15b5-4356-9d19-078af36fd74c`。
- 执行命令：只读跟踪该 operation 的本机日志、状态文件、Playwright 页面刷新结果及测试服 NAS 落盘证据；确认真实页面链路已完整跑过 MySQL 导出与对象备份，`/mnt/nas/Backup/BackupPackage/20260621-010849/mysql/ruoyi-vue-pro.sql.gz` 成功生成，对象阶段也已生成 `objects/manifest-object-copy-plan.tsv` 与 `manifest-object-copy.sh`。
- 执行命令：operation `op-2026-06-20T170847988455500Z-6d597657-15b5-4356-9d19-078af36fd74c` 最终 `FAILED`；只读打开 `D:\IntRuoyi-BackupOps\tmp\20260621-010849\manifest\dcc-backup-manifest.json`、`D:\IntRuoyi-BackupOps\logs\202606\20260621_010849_backup-now_blocked.report.md` 与 `.log`，确认新的真实阻塞为 `INTBK-6001`：DCC 备份 manifest 校验发现 `dcc_object_inventory_missing` 共 `384` 条，唯一缺失对象 `288` 个，集中在 `codex-e2e/...pdf.original.pdf|published.pdf|stamped.pdf`；下一步需先排查对象是否真实缺失、inventory 是否漏采，或 DCC 快照是否残留脏引用，再从页面重走“立即备份”。
- 执行命令：只读读取主仓历史任务 `D:\ProjectPackage\Int\IntRuoyi\doc\tasks\20260613-prod-data-backup\task.md`、`database-schema-evidence.md`、`affected-dcc-codex-e2e-records.csv` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\request-command-log.md`；确认 2026-06-14 已存在同类正式备份阻塞处理记录：96 条测试租户 `122` 的 `CODEX-E2E%` 历史残留记录经导出回滚 SQL 后最小软删除，随后正式备份成功。
- 执行命令：把当前最新正式备份快照 `D:\IntRuoyi-BackupOps\tmp\20260621-010849\manifest\dcc-database-snapshot.json` 中的 `tenant_id=122`、`CODEX-E2E-T4-*` 记录与历史 `affected-dcc-codex-e2e-records.csv` 进行集合比对 -> `EXACT_MATCH`；旧清单 `96` 条与当前快照 `96` 条完全一致，无新增、无缺失，说明当前正式服阻塞命中的正是历史已授权的同一批测试残留。
- 用户追加授权：明确授权在正式服沿用 2026-06-14 历史同一路径，对当前这 96 条测试租户 `CODEX-E2E-T4-*` 历史残留记录执行最小软删除修复；修复后继续真实页面链路“立即备份 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
- 当前结论：已把“恢复集候选为空”的根因与下一步决策写入任务文档；后续必须继续走运行控制台页面真实动作“立即备份”，待候选生成后再继续“标记测试通过 -> 上线正式服 -> 上线备份服”。
- 当前结论：任务已建档并进入页面入口确认阶段；后续发布动作必须通过运行控制台前端页面真实执行。
- 用户追加授权：`明确授权`，允许在正式服沿用 2026-06-14 历史同一路径，对 96 条测试租户 `CODEX-E2E-T4-*` 历史残留记录执行最小软删除修复，用于解除正式备份 manifest 阻塞。
- 执行命令：通过远端只读导出正式服修复前回滚 SQL，生成 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\prod-dcc-repair-before-20260621.sql` -> PASS；内容覆盖 `tenant_id=122 AND status='ACTIVE' AND deleted=0 AND file_number LIKE 'CODEX-E2E-T4-%'` 的当前 `dcc_controlled_file` 行快照。
- 执行命令：在正式服执行最小软删除 `UPDATE dcc_controlled_file SET deleted=1, updater='codex-prod-backup-20260621', update_time=NOW() WHERE tenant_id=122 AND status='ACTIVE' AND deleted=0 AND file_number LIKE 'CODEX-E2E-T4-%';` -> PASS；返回 `repair_result=96`。
- 执行命令：只读复核正式服修复后统计 -> PASS；返回 `post_deleted_summary 96 96 0`，确认 96 条目标记录已全部转为 `deleted=1`，无剩余 `ACTIVE AND deleted=0` 测试残留。
- 执行命令：Playwright 回到运行控制台真实页面，再次执行“立即备份”，填写原因“页面真实发布全链路验证：立即备份生成恢复集（修复DCC测试残留后重试）”与确认文本 `PROD-BACKUP-172.30.30.57`，提交 operation `op-2026-06-20T223216314028100Z-b7fa2fe1-41f1-4818-b3a9-36058c47e64a` -> PASS。
- 执行命令：只读跟踪本机 operation JSON、`backup-now_running.log`、NAS 备份目录与页面刷新结果 -> PASS；确认本轮正式库导出属于真实大体量长时任务，`mysql/ruoyi-vue-pro.sql.gz` 持续从约 `2.4G` 增长至约 `4.0G` 后完成，不是卡死或旧阻塞复发。
- 执行命令：只读核对成功日志 `D:\IntRuoyi-BackupOps\logs\202606\20260621_063217_backup-now_success.log` 与 NAS 备份点 `20260621-063218` 目录 -> PASS；确认本轮“立即备份”最终 `SUCCESS`，并已生成 `manifest/dcc-backup-manifest.json`、`manifest/manifest.json`、`objects/manifest-object-inventory.json` 等关键恢复产物。
- 执行命令：只读直接请求 `http://127.0.0.1:48181/admin-api/infra/runtime-control/restore-candidates`，并对照 NAS `Backup/BackupPackage` 根目录仅有 `object-store`、`20260621-063218`、`20260621-010849` 三项 -> FAIL；确认候选接口错误把 `object-store` 也当成恢复点目录参与构建，真实环境因此在读取 `\\172.30.30.4\IT共享\Backup\BackupPackage\object-store\manifest\manifest.json` 时抛出 `STATUS_OBJECT_NAME_NOT_FOUND (0xc0000034)`。
- 执行命令：读取维护仓 `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java`、`RuntimeControlNasBrowser.java` 与 `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`，确认当前 `getRestoreCandidates()` 直接对所有 NAS 子目录 `map(buildRestoreCandidate)`，缺少“恢复点目录”识别门禁。
- 执行命令：新增 RED 回归测试 `restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints`，运行 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints test` -> FAIL；返回结果同时包含 `restore:object-store` 和 `restore:20260621-063218`，证明当前逻辑确实把对象仓根目录错误暴露为恢复候选。
- 执行命令：最小修复 `RuntimeControlService#getRestoreCandidates()`，改为仅当目录下存在 `manifest/manifest.json` 时才参与恢复候选构建；保留真正恢复点进入 `buildRestoreCandidate` 后的完整阻断校验，不引入 fallback。
- 执行命令：将本地 NAS 测试夹具 `isRegularFile()` 行为补齐到真实 SMB 语义后，再次运行 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints test` -> FAIL；错误升级为 `local NAS directory not found: Backup/BackupPackage/object-store/manifest`，对应真实环境 `STATUS_OBJECT_NAME_NOT_FOUND`，证明过滤逻辑本身仍会被“父目录不存在”打断。
- 执行命令：补强 `RuntimeControlService#isRestorePointDirectory()`，把 `isRegularFile()` 对缺失父目录抛出的 `RuntimeControlException` 视为“非恢复点目录”，继续只保留真正含 `manifest/manifest.json` 的目录参与候选构建。
- 执行命令：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints test` -> PASS。
- 执行命令：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS。
- 执行命令：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` -> PASS，重新构建并更新维护控制台前后端产物，确保恢复候选修复进入当前本地页面实例。
- 执行命令：重启本地维护控制台后，只读核对 `http://127.0.0.1:48181/admin-api/infra/runtime-control/restore-candidates` -> PASS；接口已恢复 HTTP `200`，且候选仅返回真实恢复点 `restore:20260621-063218`，不再把 `object-store` 暴露为候选。
- 执行命令：Playwright 重新接入当前真实页面会话 `frontend-release-full-flow`，在“标记测试通过”表单展开“恢复集候选”下拉 -> PASS；页面已显示 `20260621-063218 · AVAILABLE`，说明此前 `No data` 阻塞已解除，后续继续按页面动作执行“标记测试通过 -> 上线正式服 -> 上线备份服”。
- 执行命令：Playwright 在真实页面选择恢复点 `20260621-063218`，将“生产确认”改回 `PROD`，点击“预览命令” -> PASS；弹窗确认执行的是 `publish-int-ruoyi.ps1 -Mode mark-tested`，并已绑定 `-SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218` 等真实恢复集参数。
- 执行命令：Playwright 在真实页面点击“标记测试通过”执行，生成 operation `op-2026-06-20T231058149703700Z-a3e87030-a2c9-45fb-bbea-01cf147a8da9`；随后只读查看本机 operation log -> FAIL，脚本报 `[FAIL] Release migration metadata missing: D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260621_srm_phase1_supplier_portal.sql`。
- 执行命令：只读用 `rg --files` 与 `rg -n` 核对原仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` -> PASS；确认 `sql\mysql\20260621_srm_phase1_supplier_portal.sql` 文件实际存在，且 `20260621_srm_phase3_purchase_order.sql` 与相关测试仍引用该迁移 ID。当前结论是页面链路已进入真实 `mark-tested` 脚本层，但迁移元数据校验对现有 SQL 发生误判，需先修复根因后再回页面重走。
- 执行命令：在原仓 `script\tests\test_srm_phase1_schema_sql.py` 新增 RED 断言，要求 `20260621_srm_phase1_supplier_portal.sql` 首行必须声明 `release-migration` 元数据；运行 `python -X utf8 -m pytest script\\tests\\test_srm_phase1_schema_sql.py -q` -> FAIL，确认该 SQL 当前直接从 `CREATE TABLE` 开始。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260621_srm_phase1_supplier_portal.sql` 补齐首行 `-- release-migration: allowedEnvironments=test,backup,prod; dependsOn=20260620_srm_phase1_supplier_access_profile; type=schema; riskLevel=medium`。
- 执行命令：`python -X utf8 -m pytest script\\tests\\test_srm_phase1_schema_sql.py -q` -> PASS。
- 执行命令：`python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` -> PASS；门禁输出已包含 `20260621_srm_phase1_supplier_portal` 与 `20260621_srm_phase3_purchase_order` 的正确依赖链。
- 执行命令：Playwright 回到同一真实页面会话 `frontend-release-full-flow`，重新抓取页面快照确认“标记测试通过”最新 operation `op-2026-06-20T231610219440500Z-62163986-e842-4cf2-ace5-cb1a65954752` 已显示为 `SUCCESS / 命令执行完成`；页面当前动作仍为“标记测试通过”，恢复点候选为 `20260621-063218 · AVAILABLE`。
- 当前结论：`mark-tested` 的真实脚本阻塞根因是 SQL 缺失正式迁移元数据，不是页面问题、也不是文件不存在；修复后页面真实“标记测试通过”链路已经走通，接下来继续页面动作“上线正式服 -> 上线备份服”。
- 执行命令：Playwright 在真实页面切换到“上线正式服”，将“操作原因”改为“页面真实发布全链路验证：上线正式服”，把错误遗留的旧“发布标签”修正为 `release-20260620-page-full-flow-v1`，预览命令确认本次将执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260620-page-full-flow-v1 -ConfirmText PROD -RequireTested ...`，目标仍为正式服 `172.30.30.57`，未漂移到回滚/恢复动作。
- 执行命令：Playwright 在预览弹窗点击“执行”，真实页面生成 operation `op-2026-06-20T232011628082400Z-19f06c06-8815-4e57-83eb-39d0b7aba973`；刷新页面后该 operation `FAILED`，本机 log 明确报 `Production deploy-release requires -ProdDryRunEvidencePath from a passed preflight-release dry-run.`。
- 执行命令：只读核对 `frontend/src/App.vue`、`frontend/src/api/runtimeControl.ts`、`backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeDtos.java`、`RuntimeControlOperationAction.java`、`RuntimeControlService.java` 与 `ops/deploy/publish-int-ruoyi.ps1` -> PASS；确认正式发布脚本门禁本身正确，但当前运行控制台页面没有 `preflight-release` 入口，也没有把 `ProdDryRunEvidencePath` 这类正式 dry-run 证据路径纳入预览/执行契约，导致用户严格走页面也无法满足正式服发布门禁。
- 执行命令：继续只读核对 `ops/release/run-deploy-precheck-report.ps1`、`ops/release/lib/DeployPrecheckReport.psm1`、`ops/release/lib/ReleaseManifestValidator.psm1`、`ops/deploy/publish-int-ruoyi.ps1`，并直接读取真实页面构建产物 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-page-full-flow-v1\manifest.json` -> FAIL；确认当前 build 产物里的 `manifest.json` 仍是极简版本，只包含 `manifestVersion/releaseTag/packageId/targetRequirements`，与正式 `report-only` 所需的完整 Manifest v1 契约不一致，因此即使后端自动补做正式 dry-run，当前构建产物也无法直接产出可通过的 dry-run 证据。
- 执行命令：继续只读对照 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-current-head-prod-target-v7`、`release-20260616-152022-codeonly-e2e` 与当前 `release-20260620-page-full-flow-v1` 的本地目录结构 -> FAIL；确认前两者都保留完整 Manifest v1 和完整发布包目录，而 `release-20260620-page-full-flow-v1` 仅剩 `manifest.json/preflight-plan.json/release-manifest.json` 三个文件，且时间戳为 `2026-06-21 07:33`。根因不是 2026-06-20 页面 build 天生只产极简包，而是此前后端单测夹具曾错误复用这个真实 release tag，污染了本地缓存目录。
- 执行命令：修复 `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`，将 `promoteProdPreviewAutoGeneratesDryRunEvidence` 改为独立测试 tag `release-20260621-prod-dry-run-fixture`，并补齐最小可通过 Manifest v1 夹具；随后运行 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，确认自动 dry-run 证据逻辑已可回归，且后续不会继续污染真实页面 release tag。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，在“构建发布包”表单填写新的 `releaseTag=release-20260621-page-full-flow-v2` 与原因“页面真实发布全链路验证：重建干净发布包并重走测试服-正式服-备份服”，预览命令确认参数为 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v2 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行”；只读查询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations` -> FAIL，确认新的页面构建 operation `op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b` 已真实生成，但状态立即变为 `FAILED`。
- 执行命令：只读读取 `runtime/runtime-control/logs/op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b.log` -> FAIL；精确根因为 `Backend jar is locked before Maven clean: D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\target\yudao-server.jar`，日志点名锁定进程 `pid=48576 name=java.exe; pid=45732 name=java.exe`，并要求先让本机后端改为“从复制出的 runtime jar 运行”后再重试真实页面 build-release。
- 执行命令：执行 `D:\ProjectPackage\Int\IntRuoyi\restart-ruoyi-backend.bat` -> PASS（解除源码仓 `yudao-server.jar` 锁）；只读确认运行 jar 已切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260621-075408.jar`，虽然 `48081` 因既有 Quartz/JobStartupSyncRunner 问题退出，但不再直接占用源码仓 target jar。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow` 再次点击“构建发布包”；只读查询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations` -> PASS，确认新 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 已生成并保持 `RUNNING`。
- 执行命令：只读跟踪 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea.log` -> PASS；确认本轮页面构建已完成 `docker info`、backend runtime base image load 与 `mvn -f ... -pl yudao-server -am -DskipTests clean package`，得到 `BUILD SUCCESS`，随后进入 `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js build --mode test`。
- 执行命令：Playwright 抓取真实页面快照、只读轮询 operation 接口、检查 operation log 文件时间戳/大小与本机相关进程 -> FAIL；页面与接口仍显示 `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 为 `RUNNING`，日志文件自 `2026-06-21 08:01:52` 起不再增长，且本机存在对应进程 `node.exe (PID 16260)` 执行 `vite.js build --mode test`，当前新阻塞已转为“前端 vite 构建阶段疑似卡住/静默无进度”。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 独立复现前端构建，显式设置 `NODE_OPTIONS=--max-old-space-size=8192`、`VITE_BASE_URL=''`、`VITE_BASE_PATH='/'`、`VITE_OUT_DIR='dist-intruoyi-test-repro'` 后运行 `node node_modules\vite\bin\vite.js build --mode test` -> FAIL/TIMEOUT；244 秒后命令仍未结束，被外层超时回收，证明当前问题在前端 `test` 模式 Vite 构建链本身，而不是页面提交或运行控制台调度。
- 执行命令：追加 `DEBUG='vite:*'` 启动独立前端构建并重定向到 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\vite-test-debug.stderr.log` -> PASS；日志显示构建经历长时间 `vite:resolve` 资源解析后，最终输出 `Build successful. Please see dist-intruoyi-test-debug directory`，说明此前“永久卡死”判断过早。
- 执行命令：重新只读查询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations` 并读取 operation log 尾部 -> PASS；确认真实页面 build operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 已变为 `SUCCESS`，日志尾部显示 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-v2` 与 `Release package built: release-20260621-page-full-flow-v2`。
- 当前结论：真实页面链路在“上线正式服”处暴露产品级缺口，必须先补齐前端/后端正式 dry-run 证据入口与透传，再返回页面重走正式服与备份服。
- 执行命令：Playwright 在运行控制台真实页面切换到“部署测试服”，预览命令确认目标环境仍为 `test`、发布标签为 `release-20260621-page-full-flow-v2`，参数未漂移到 `prod/backup/rollback/restore`。
- 执行命令：Playwright 在真实页面点击“部署测试服”执行，生成 operation `op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215`。
- 执行命令：只读读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215.log` -> FAIL；确认 required SQL `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260619_srm_d7_2_supplier_access_risk.sql` 执行时返回 MySQL `ERROR 1644 (45000) at line 321: Missing SRM supplier-profile route menu for get-permission-info`，但同一 operation 尾部已释放测试服发布锁 `LOCK_RELEASED`。
- 执行命令：基于真实页面失败日志进入严格 TDD 修复；在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_d7_d10_sql_contract.py` 新增回归测试 `test_srm_t1_route_menu_guards_do_not_confuse_query_buttons_with_pages`，要求 D7-2 SQL 的三个二级页面路由守卫不得把 `type=3` 查询按钮误判为页面已存在。
- 执行命令：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_d7_d10_sql_contract.py -q` -> FAIL；新断言命中旧守卫：
  - `(`id` = 991011 OR `component` = 'srm/supplier-access/index' OR `permission` = 'srm:supplier-access:query')`
  - `(`id` = 991020 OR `component` = 'srm/supplier-risk/index' OR `permission` = 'srm:supplier-risk:query')`
  - `(`id` = 991024 OR `component` = 'srm/supplier-profile/index' OR `permission` = 'srm:supplier-profile:query')`
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260619_srm_d7_2_supplier_access_risk.sql` 修复三个页面路由守卫，统一收窄为仅接受同 `id`、同 `component`，或同 `permission` 且 `type=2` 的页面菜单，不再让查询按钮阻断页面路由插入。
- 执行命令：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_d7_d10_sql_contract.py -q` -> PASS，13 项测试全部通过。
- 执行命令：`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，确认 D7-2 SQL 修复后发布迁移 metadata 仍完整可用。
- 当前结论：`release-20260621-page-full-flow-v2` 已在本次修复之前构建完成，不包含新的 D7-2 SQL；不能直接继续页面部署测试服。下一步必须通过真实页面重新构建新的 release tag，再从页面重走测试服/正式服/备份服链路。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，在页面上重新填写 `releaseTag=release-20260621-page-full-flow-v3` 并触发“构建发布包”预览/执行，生成 operation `op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d`。
- 执行命令：只读轮询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations`、operation 状态文件与 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d.log` -> PASS；确认本轮真实页面构建先完成 backend `mvn ... clean package`，后续前端 `vite build --mode test` 处于长耗时解析阶段但 `node.exe` CPU 持续增长，最终于 2026-06-21 10:58:27 收口为 `SUCCESS`，并把发布包上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v3`。
- 当前结论：新的真实页面构建包 `release-20260621-page-full-flow-v3` 已就绪，下一步继续在页面执行“部署测试服”，不得用接口替代按钮提交。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“部署测试服”，将操作原因改为“页面真实发布全链路验证：部署测试服（v3）”，预览命令确认环境为 `test`、发布标签为 `release-20260621-page-full-flow-v3`，随后点击“执行”生成 operation `op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96`。
- 执行命令：只读轮询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations`、Playwright 页面快照与 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96.log` -> FAIL；确认该真实页面测试服发布先成功执行 `20260619_srm_d7_2_supplier_access_risk.sql`，随后在 required SQL `20260620_srm_phase1_supplier_access_profile.sql` 阶段被真实 MySQL `ERROR 1064 (42000)` 阻断，报错位置为 `ADD COLUMN IF NOT EXISTS \`portal_contact_name\``，并且同一 operation 尾部已释放测试服发布锁 `LOCK_RELEASED`。
- 当前结论：新的真实页面阻塞已经从 D7-2 菜单守卫推进到 `20260620_srm_phase1_supplier_access_profile.sql` 的 MySQL 语法契约问题；下一步必须先记录并用严格 TDD 修复该 SQL，再回到页面重走测试服发布。
- 执行命令：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_phase1_schema_sql.py -q` -> PASS，返回 `10 passed`；确认 access-profile SQL 正式幂等加列写法与 portal metadata 断言现已全部通过。
- 执行命令：`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，返回 `status=passed`，依赖链正确保留 `20260620_srm_phase1_supplier_access_profile -> 20260621_srm_phase1_supplier_portal -> 20260621_srm_phase3_purchase_order`。
- 执行命令：在后端仓创建任务目录 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260621-srm-release-page-flow-sql-blockers\`，写入 `task.md`、`execution-log.md` 与 `bug-regression-evidence.md`，把 D7-2 路由守卫、Phase 1 portal metadata、Phase 1 access-profile syntax 三个页面发布阻塞统一收口到源码任务文档。
- 当前结论：页面链路暴露的 SRM 发布输入阻塞已在源码仓通过 TDD 收口；维护仓下一步必须通过真实页面重新构建新 tag `release-20260621-page-full-flow-v4`，再重走测试服/正式服/备份服链路。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，在“构建发布包”表单填写 `releaseTag=release-20260621-page-full-flow-v4` 与原因“页面真实发布全链路验证：Phase1 access-profile语法修复后重建发布包并重走测试服-正式服-备份服”，预览命令确认参数为 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v4 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0`；随后只读轮询页面、`/admin-api/infra/runtime-control/operations`、operation 状态文件、本地 log、进程树以及本地/NAS 发布目录。
- 当前结论：`op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0` 已最终 `SUCCESS`；虽然中途和前几轮一样在 `vite build --mode test` 阶段长时间无新日志，但后续已继续进入 backend image `docker build`、本地包落盘和 NAS 上传。已确认本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4` 生成 `intruoyi-images_release-20260621-page-full-flow-v4.tar`、`release-manifest.json`、`manifest.json`，NAS 目录 `\\172.30.30.4\IT共享\Backup\ReleasePackage\release-20260621-page-full-flow-v4` 也已落盘。下一步继续用真实页面点击“部署测试服”。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“部署测试服”，将操作原因改为“页面真实发布全链路验证：部署测试服（v4）”，预览命令确认目标环境为 `test`、发布标签为 `release-20260621-page-full-flow-v4`，参数未漂移到 `prod/backup/rollback/restore`。
- 执行命令：Playwright 在真实页面点击“部署测试服”执行，生成 operation `op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5`；随后只读轮询页面、`/admin-api/infra/runtime-control/operations`、operation 状态文件与本机 log。
- 执行命令：只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5.log` -> PASS；确认该真实页面测试服发布已成功执行 `20260620_srm_phase1_supplier_access_profile.sql`、`20260621_srm_phase1_supplier_portal.sql`、`20260621_srm_phase3_purchase_order.sql`，随后完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。
- 执行命令：只读核对测试服 `172.30.30.58` 的远端版本与入口 -> PASS；`ssh root@172.30.30.58 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env"` 返回 `IMAGE_TAG=release-20260621-page-full-flow-v4`，`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v4`，`http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/` 与 `http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。
- 当前结论：`release-20260621-page-full-flow-v4` 已真实通过“构建发布包 -> 部署测试服”两步页面链路，且测试服只读核验与页面 operation 证据一致。下一步继续复用真实页面会话 `frontend-release-full-flow` 执行“标记测试通过 -> 上线正式服 -> 上线备份服”。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，在“标记测试通过”表单填写原因“页面真实发布全链路验证：标记测试通过（v4）”、生产确认 `PROD`、验证结论“回归通过，允许上线正式服”，并通过页面下拉真实选中恢复点 `20260621-063218 · AVAILABLE`。
- 执行命令：Playwright 在真实页面点击“预览命令” -> PASS；弹窗确认本次执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v4 -TestConclusion 回归通过，允许上线正式服 -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18`；随后只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18.json` 与本机 log。
- 执行命令：只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18.log` -> PASS；确认该真实页面 `mark-tested` 已最终 `SUCCESS`，日志输出 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-v4`，并记录 `rollback-compatibility.json status=BLOCKED` 元数据。
- 当前结论：`release-20260621-page-full-flow-v4` 已在真实页面链路完成“构建发布包 -> 部署测试服 -> 标记测试通过”。下一步继续复用同一页面会话执行“上线正式服”，若出现新阻塞，先写入任务文档再修复重走。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“上线正式服”，确认页面表单显示 `targetEnvironment=正式服`、`releaseTag=release-20260621-page-full-flow-v4`、`prodConfirmText=PROD`，并点击“预览命令”。
- 执行命令：只读核对页面返回 -> FAIL；页面未进入执行弹窗成功态，而是直接提示 `正式 deploy precheck report-only 失败: status=failed mode=report-only output=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json`。
- 执行命令：只读打开 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json` -> FAIL；确认根因是发布包 manifest 契约不完整，报告含大量 `PACKAGE_UNDECLARED_FILE`，例如 `.env`、`post-import.sql`、`preflight-plan.json`、`preflight-target-state-test.json`、`ops-runtime/actions/*.bat`、`ops-runtime/scripts/modules/Core/*.psm1` 等文件都在包内但未被 manifest 声明。
- 当前结论：新的真实页面阻塞已从“缺 dry-run 入口”推进到“自动 dry-run 已跑，但 `report-only` 因未声明包文件而 fail-fast”。下一步必须先做严格 TDD 修复发布包/manifest 契约，再回页面重走“上线正式服 -> 上线备份服”。
- 执行命令：读取 `bug-regression-fix-loop` 技能与 `doc/tasks/20260620-frontend-release-full-flow/bug-regression-evidence.md`，补充本次正式服预检阻塞的缺陷合同与 root cause；同时只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4` 的文件时间戳，确认 `manifest.json/release-manifest.json` 写于 `11:51`，而 `.env/post-import.sql/preflight-plan.json/preflight-target-state-test.json/ops-runtime` 均由测试服部署后的真实页面动作在 `11:56-12:00` 期间写回同一本地缓存目录。
- 执行命令：在 `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java` 新增严格回归 `promoteProdPreviewUsesSanitizedPackageWorkspace`，构造一个 manifest 完整的本地发布包目录后，再故意写入 `.env`、`preflight-plan.json` 与带目标 IP 的 `post-import.sql`，要求 `promote-prod` 页面预览自动生成 dry-run 证据时必须忽略这些部署期污染文件。
- 执行命令：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace test` -> FAIL；旧逻辑稳定返回 `{"code":400,"msg":"正式 deploy precheck report-only 失败: ..."}`，证明正式 dry-run 确实直接复用了被污染的本地缓存目录。
- 执行命令：在 `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java` 修复正式 dry-run 工作区：`generateProdDryRunEvidence` 不再把 `local-cache/publish-int-ruoyi/<releaseTag>` 直接交给 `run-deploy-precheck-report.ps1`，而是先读取 `manifest.json`，仅按 manifest 声明复制 package 文件与 `manifest.json/release-manifest.json` 到 `state-dir/prod-preflight-release-workspaces/<releaseTag>-*` 隔离副本，再对该副本执行 `report-only`，最后清理临时副本。
- 执行命令：`mvn -f backend/pom.xml "-Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace+RuntimeControlOriginalParityTest#promoteProdPreviewAutoGeneratesDryRunEvidence" test` -> PASS，确认“污染目录回归”与“原有自动 dry-run 证据生成”同时通过。
- 执行命令：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，14 项运行控制台一致性/契约测试全部通过。
- 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\bug-regression-evidence.md` -> PASS，缺陷证据结构与 RED/GREEN 标记有效。
- 当前结论：新的正式服页面阻塞根因已精确收口为“自动正式 dry-run 复用了被测试服部署动作污染的本地缓存目录”；现已按长期方案修复为“基于 manifest 声明文件生成隔离工作区再预检”。下一步必须重建本地维护控制台并回到真实页面继续重试“上线正式服 -> 上线备份服”。
- 执行命令：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` -> FAIL；前端 `pnpm typecheck/build` 与后端测试均通过，但 Maven `spring-boot:repackage` 无法将 `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 改名为 `.original`。
- 执行命令：只读核对 `Get-NetTCPConnection -LocalPort 48181` 与 `Get-CimInstance Win32_Process` -> FAIL；确认旧维护控制台进程 `PID 59068` 正直接以 `java -jar D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 运行并监听 `127.0.0.1:48181`，导致新 jar 无法覆盖。
- 当前结论：正式 dry-run 根因修复已完成，但本机维护控制台仍运行旧 jar，必须先停掉 `PID 59068` 后重跑 `scripts/build.ps1` 与 `scripts/start.ps1`，新逻辑才能真正进入页面链路。
- 执行命令：在本机完成维护控制台重建与重启后，Playwright 复用真实页面会话 `frontend-release-full-flow` 回到“上线正式服”，重新点击页面预览与执行 -> PASS；正式服真实 operation `op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b` 已由页面按钮提交。
- 执行命令：只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b.json`、operation log 与 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4\preflight-plan.json` -> FAIL；确认新的真实页面阻塞不是预览失败，也不是远端 SQL 实际执行失败，而是 prod deploy 在读取 `preflight-plan.json` 时直接因 `status=blocked` fail-fast。
- 执行命令：只读对比 `release-20260621-page-full-flow-v4\manifest.json` 与历史成功正式包 `release-20260620-current-head-prod-target-v7\manifest.json` -> FAIL；确认当前包额外带入 8 个 `allowedEnvironments=test,backup` 的 `post_release_role_e2e_gate*` 迁移，而旧成功正式包没有。下一步必须在 `ruoyi-vue-pro` 按严格 TDD 修复发布包环境契约和 `release_preflight_plan.py` 的跨环境跳过语义，再回到页面重走全链路。
- 执行命令：跟进源码任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260621-release-preflight-environment-contract\`，同步查看其 RED/GREEN 证据、四组目标测试、`run-release-migration-policy-gate.py --sql-root sql\mysql` 结果，以及维护仓 `ops\deploy\publish-int-ruoyi.ps1`/`ops\release\*.py` 的脚本同步核对 -> PASS。
- 当前结论：正式服 preflight 环境契约阻塞已在源码仓与维护仓实际运行脚本中完成正式修复；下一步必须回到真实页面，从新的 release tag 重新执行 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服` 全链路。

## 2026-06-21 页面发布全链路 v5 重跑前置确认

- 用户需求：`这次要正式按“页面前端点击操作”的真实流程，完整走一遍构建发布到测试服、再到正式服、再到备份服，过程中禁止直接调接口替代页面动作；每遇到问题要先记录到任务文档，修复后继续从页面走，直到整条流程能够一次性走通视作目标完成`。
- 执行命令：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\{task.md,execution-log.md}`、`docs\experience-index.md`、命中的 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`project-error-prevention.md`，并补读 `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md` -> PASS。
- 执行命令：`Get-Command npx`、`Invoke-WebRequest http://127.0.0.1:48181/`、`npx --yes --package @playwright/cli playwright-cli -s=frontend-release-full-flow snapshot` -> PASS；确认 `npx`、本机运行控制台与真实页面会话都仍可用。
- 执行命令：Playwright 在真实页面点击“刷新”并切回“构建发布包”，填写原因“页面真实发布全链路验证：v13环境契约修复后重建发布包并从测试服-正式服-备份服重跑”、`releaseTag=release-20260621-page-full-flow-v5`，点击“预览命令” -> PASS；弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-v5 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行” -> PASS；页面生成 operation `op-2026-06-21T063453670081300Z-d06ecbd1-508c-4014-a2fc-eb97e0b749e6`，状态为 `RUNNING / 命令已提交到本机执行队列`。
- 执行命令：只读轮询 operation 状态文件、`runtime-control` 本机 log、`manifest.json` 和 Playwright 刷新后的页面操作记录 -> PASS；确认 `op-2026-06-21T063453670081300Z-d06ecbd1-508c-4014-a2fc-eb97e0b749e6` 已最终 `SUCCESS`，并完成 backend `BUILD SUCCESS`、前端 `Build successful. Please see dist-intruoyi-test directory`、backend/frontend 镜像构建、`docker save` 导出以及 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-v5`。
- 当前结论：`release-20260621-page-full-flow-v5` 已在真实页面链路重新完成“构建发布包”并通过候选包核验；下一步继续在同一页面链路执行“部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`，随后只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355.json` 与 Playwright 页面快照，确认真实页面“部署测试服（v5）” operation 已成功创建并处于 `RUNNING`。
- 执行命令：只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355.log`，确认远端已依次完成 required SQL 登记/执行、Quartz/showroom schema 检查、容器重建、readiness、scheduler smoke runtime 核对和发布锁释放，最终收口为 `SUCCESS`。
- 执行命令：只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、`docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'` 与 `http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/`、`http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` -> PASS；确认运行态 `IMAGE_TAG` 与 backend/frontend 镜像都已切到 `release-20260621-page-full-flow-v5`，三条入口均返回 HTTP `200`。
- 当前结论：`release-20260621-page-full-flow-v5` 已在真实页面链路完成“构建发布包 -> 部署测试服”；下一步在补齐文档后继续复用同一页面会话执行“标记测试通过 -> 上线正式服 -> 上线备份服”。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“标记测试通过”，把操作原因改为“页面真实发布全链路验证：标记测试通过（v5）”、验证结论改为“回归通过，允许上线正式服（v5）”，并展开“恢复集候选”下拉。
- 执行命令：Playwright 在真实页面恢复点下拉中真实选中 `20260621-063218 · AVAILABLE`，点击“预览命令” -> PASS；弹窗确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v5 -TestConclusion 回归通过，允许上线正式服（v5） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行” -> PASS；页面生成 operation `op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5`，状态为 `RUNNING / 命令已提交到本机执行队列`。
- 执行命令：只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5.json` 与对应本机 log -> PASS；确认该真实页面 `mark-tested` 已最终 `SUCCESS`，并把 `release-20260621-page-full-flow-v5` 标记为测试通过，同时写入 `rollback-compatibility.json status=BLOCKED`。
- 当前结论：`release-20260621-page-full-flow-v5` 已在真实页面链路完成“构建发布包 -> 部署测试服 -> 标记测试通过”；下一步继续在同一页面会话执行“上线正式服 -> 上线备份服”。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`，随后只读轮询正式服 operation 状态文件、对应本机 log、`release-20260621-page-full-flow-v5-preflight-release-dry-run.json` 与 Playwright 页面快照 -> FAIL；确认真实页面“上线正式服（v5）” operation `op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff` 已最终 `FAILED`，但正式 dry-run 证据仍为 `status=passed`。
- 执行命令：通过只读 SQL 查询正式服 `infra_release_operation_lock` -> FAIL；确认当前 `target_environment='prod'` 仅有 1 条锁记录，且仍停留在旧链路 `operation_id=prod-release-20260621-page-full-flow-v4`、`release_tag=release-20260621-page-full-flow-v4`、`status=RUNNING`、`started_at=2026-06-21 13:04:44`、`finished_at=NULL`。
- 当前结论：`release-20260621-page-full-flow-v5` 的真实页面正式服失败根因不是 dry-run 证据缺失，也不是发布包内容前置门禁，而是被旧 `v4` 失败链路残留的正式服发布锁阻断。下一步必须先修复正式服发布锁生命周期并清理陈旧锁，再回到真实页面继续“上线正式服 -> 上线备份服”。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\SKILL.md`、新增 `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py` 回归场景，并执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` -> FAIL；稳定复现“持锁后 fail-fast 遗留正式服发布锁”的旧问题。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 修复 `Fail()` 的锁释放路径，并执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q`、`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_scheduler_smoke_release_config.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS；相关回归共 `10 passed`。
- 执行命令：只读确认当前无活跃中的同类本地发布进程后，手动将正式库残留锁 `prod-release-20260621-page-full-flow-v4` 从 `RUNNING` 收口为 `FAILED`，并补写 `finished_at` 与 `error_message='manual stale-lock cleanup after release lock fail-fast bug fix for page-flow v5'` -> PASS。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，回到“上线正式服（v5）”预览弹窗再次点击“执行”，生成 operation `op-2026-06-21T073844572460600Z-694fba69-6b1c-4507-994e-9aac8f490123`；随后只读轮询状态文件与本机 log -> PASS，确认该正式服真实页面发布已最终 `SUCCESS`。
- 执行命令：只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、`docker ps --format '{{.Names}} {{.Image}}'`、`http://172.30.30.57:48081/actuator/health`、`http://172.30.30.57:8081/`、`http://172.30.30.57:8081/pdfjs/pdf.worker.mjs`，以及真实库 `config_id=28 AND path LIKE 'showroom/%'` 的受保护 URL 边界 -> PASS；确认 `IMAGE_TAG` 与 backend/frontend 镜像都为 `release-20260621-page-full-flow-v5`、三条入口均返回 HTTP `200`、`url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`、`url LIKE 'http://172.30.30.57:9000/yudao/%'` 的记录数为 `1434`。
- 当前结论：`release-20260621-page-full-flow-v5` 的真实页面正式服发布与只读运行态核验已完成，下一步继续在同一页面会话执行“上线备份服”，然后汇总单次完整链路证据。
- 执行命令：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f.json` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f.log -Tail 80` -> FAIL；确认真实页面“上线备份服（v5）” operation 已最终 `FAILED`，失败点位于 required SQL `20260618_post_release_role_e2e_gate.sql`，远端 MySQL 返回 `ERROR 1644 (45000) at line 226: Missing enabled scheduler role; cannot prepare zhaojie smart scheduling E2E account`。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`、`C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\SKILL.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\task.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\execution-log.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md` -> PASS；继续按“先记录阻塞、再区分环境前置条件和代码缺陷”的门禁推进本任务。
- 当前结论：新的真实页面主阻塞已收敛到备份服 `20260618_post_release_role_e2e_gate.sql` 的角色前置条件/环境契约问题；下一步先做只读根因定位，确认这是备份环境数据缺前置角色，还是迁移 SQL 在 `backup` 环境不应硬失败。
- 执行命令：切到业务仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，读取 `AGENTS.md`、创建任务目录 `doc/tasks/20260621-post-release-role-e2e-gate-backup-scheduler-role/`、补读 `docs/experience-index.md` 命中的 `release-backup-restore.md` 与 `server-access.md`，并只读对比测试服/备份服 `tenant_id=1 / 芋道源码` 的 `system_role/system_users/system_tenant` 基线 -> PASS；确认测试服有启用中的 `排产员` 角色，备份服仅有 `showroom_publicity` 与 `wenkong`。
- 执行命令：业务仓更新 `script/tests/test_post_release_role_e2e_gate_sql.py`，新增“缺排产员角色时必须自补齐”的 RED 契约；执行 `python -X utf8 -m pytest script\\tests\\test_post_release_role_e2e_gate_sql.py -q` -> FAIL；旧 SQL 稳定缺少 `INSERT INTO system_role` 自补齐逻辑。
- 执行命令：业务仓更新 `sql/mysql/20260618_post_release_role_e2e_gate.sql`，使其在 `tenant_id=1` 缺排产员角色时插入新的 `排产员` 角色，在命中历史角色时统一启用并复用；执行 `python -X utf8 -m pytest script\\tests\\test_post_release_role_e2e_gate_sql.py -q`、`python -X utf8 -m pytest script\\tests\\test_post_release_role_e2e_gate_sql.py script\\tests\\test_mes_scheduler_role_smart_scheduling_tab_sql.py -q`、`python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` -> PASS。
- 执行命令：业务仓新增并校验 `doc/tasks/20260621-post-release-role-e2e-gate-backup-scheduler-role/bug-regression-evidence.md`，执行 `python C:\\Users\\BJB110\\.codex\\skills\\bug-regression-fix-loop\\scripts\\validate_bug_regression.py --evidence D:\\ProjectPackage\\Int\\IntRuoyi\\ruoyi-vue-pro\\doc\\tasks\\20260621-post-release-role-e2e-gate-backup-scheduler-role\\bug-regression-evidence.md` -> PASS。
- 当前结论：备份服阻塞已在业务仓按严格 TDD 收口，但该修复改变了发布包输入，现有 `release-20260621-page-full-flow-v5` 不能继续使用；下一步必须回到真实页面重新构建新 release tag，并从测试服开始整链重走。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md` 与 `references\cli.md/references\workflows.md`，确认继续使用 Playwright CLI 复用真实页面会话 `frontend-release-full-flow`；同时核对 `Get-Command npx`、`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow snapshot` -> PASS，确认 `http://127.0.0.1:48181/` 页面会话与 `releaseTag=release-20260621-page-full-flow-v6` 表单状态仍然可用。
- 执行命令：Playwright 在真实页面点击“预览命令”“执行”，并轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10.json`、`D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10.log`、Playwright 页面快照与本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v6` -> PASS；确认页面真实生成并完成 operation `op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10`，且本地已生成 `required-sql/`、`resources/`、`runtime-env/`、`smoke/`、`manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-v6.tar`。
- 执行命令：只读核对 operation 尾部日志 -> PASS；确认本轮真实页面 `build-release` 已完成 backend `BUILD SUCCESS`、前端 `Build successful. Please see dist-intruoyi-test directory`、Docker build 和 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-v6`，最终状态为 `SUCCESS / 命令执行完成`。
- 当前结论：修复备份服角色 gate 后，新的 `release-20260621-page-full-flow-v6` 候选包已通过真实页面重新构建成功；下一步继续在同一页面会话执行“部署测试服（v6） -> 标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\{task.md,execution-log.md}`，并重新核对 `Get-Command npx` -> PASS；确认继续按 Playwright CLI + 真实页面链路推进，且 `npx` 来源为 `D:\Programs\npx.ps1`。
- 执行命令：只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517.json`、对应本机日志尾部以及 `npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow snapshot` -> PASS；确认真实页面“部署测试服（v6）” operation 已创建且仍处于 `RUNNING`，链路当时已推进到 required SQL、Quartz/showroom schema 检查、`backend/frontend` 容器重建和 `Waiting for remote HTTP readiness` 阶段。
- 执行命令：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517.json` 直到终态 -> PASS；确认该真实页面测试服发布 operation 已于 2026-06-21 17:12:58 收口为 `SUCCESS / 命令执行完成`。
- 执行命令：只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、`docker ps --format '{{.Names}} {{.Image}}' | grep intruoyi-` 与 `http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/`、`http://172.30.30.58:8081/pdfjs/pdf.worker.mjs`，并读取 operation log 尾部 -> PASS；确认运行态 `IMAGE_TAG` 与 `intruoyi-backend/intruoyi-frontend` 镜像都已切到 `release-20260621-page-full-flow-v6`，三条入口均返回 HTTP `200`，日志同时记录 scheduler smoke runtime 核对、测试服发布锁释放 `LOCK_RELEASED` 与远端临时文件清理完成。
- 当前结论：`release-20260621-page-full-flow-v6` 已在真实页面链路完成“构建发布包 -> 部署测试服”，且测试服只读运行态核验通过；下一步继续在同一页面会话执行“标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“标记测试通过”，真实填写操作原因“页面真实发布全链路验证：标记测试通过（v6）”、验证结论“回归通过，允许上线正式服（v6）”，展开“恢复集候选”下拉并选中 `20260621-063218 · AVAILABLE`，随后点击“预览命令” -> PASS；弹窗确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v6 -TestConclusion 回归通过，允许上线正式服（v6） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`。
- 执行命令：Playwright 在真实页面预览弹窗点击“执行” -> PASS；页面生成 operation `op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2`，状态为 `RUNNING / 命令已提交到本机执行队列`。
- 执行命令：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2.json`，并读取对应本机日志尾部 -> PASS；确认该真实页面 `mark-tested` operation 已于 2026-06-21 17:18:58 收口为 `SUCCESS / 命令执行完成`，日志记录 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-v6` 与 `rollback-compatibility.json status=BLOCKED`。
- 当前结论：`release-20260621-page-full-flow-v6` 已在真实页面链路完成“构建发布包 -> 部署测试服 -> 标记测试通过”；下一步继续在同一页面会话执行“上线正式服（v6） -> 上线备份服（v6）”。
- 执行命令：读取 `C:\Users\BJB110\.codex\skills\playwright\references\cli.md` 与 `references\workflows.md`，确认当前弹窗场景下可继续使用 Playwright CLI 复用会话 `frontend-release-full-flow` 完成真实页面点击；随后执行 `npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow snapshot`、`click e125`、`screenshot` 与 `view_image` -> PASS，确认“上线正式服（v6）”预览弹窗实际展示 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath ...release-20260621-page-full-flow-v6-preflight-release-dry-run.json ...`。
- 执行命令：由于 Playwright 快照未直接暴露弹窗内按钮 ref，改用 `playwright-cli eval` 在真实页面 DOM 中点击弹窗“执行”按钮 -> PASS；页面新增 operation `op-2026-06-21T092843334367500Z-223e010b-722c-4d05-ba35-887515eba339`，状态为 `RUNNING / 命令已提交到本机执行队列`。
- 执行命令：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T092843334367500Z-223e010b-722c-4d05-ba35-887515eba339.json` 与对应本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T092843334367500Z-223e010b-722c-4d05-ba35-887515eba339.log` -> PASS；确认该正式服真实页面发布最终 `SUCCESS`，并完成 required SQL、Quartz/showroom schema 检查、容器重建、HTTP readiness、scheduler smoke、发布锁释放、NAS 发布历史与远端临时文件清理。
- 执行命令：只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、`docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'` 与 `http://172.30.30.57:48081/actuator/health`、`http://172.30.30.57:8081/`、`http://172.30.30.57:8081/pdfjs/pdf.worker.mjs` -> PASS；确认运行态 `IMAGE_TAG` 与 backend/frontend 镜像都已切到 `release-20260621-page-full-flow-v6`，三条入口均返回 HTTP `200`。
- 执行命令：只读核对展厅受保护 URL 边界时，先对正式库执行 `DESCRIBE infra_file_config`，确认该表不含 `config_id/path/url`，随后改为对真实表 `infra_file` 执行 `DESCRIBE infra_file` 与边界计数查询 -> PASS；确认 `config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.57:9000/yudao/%'` 的记录数为 `1434`。
- 当前结论：`release-20260621-page-full-flow-v6` 已在真实页面链路完成“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服”，且正式服只读运行态与展厅受保护边界核验通过。下一步继续在同一页面会话执行“上线备份服（v6）”，以收齐最终一次性走通证据。
- 执行命令：Playwright 复用真实页面会话 `frontend-release-full-flow`，先点击“刷新”，再切换到“上线备份服”，把操作原因改为“页面真实发布全链路验证：上线备份服（v6）”，点击“预览命令”并截图核对 -> PASS；确认真实页面预览弹窗执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`。
- 执行命令：由于 Playwright 快照仍未直接暴露弹窗内按钮 ref，继续使用 `playwright-cli eval` 在真实页面 DOM 中点击弹窗“执行”按钮 -> PASS；页面新增 operation `op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2`，状态为 `RUNNING / 命令已提交到本机执行队列`。
- 执行命令：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2.json` 与对应本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2.log` -> PASS；确认该备份服真实页面发布最终 `SUCCESS`，并完成此前阻断 v5 的 `20260618_post_release_role_e2e_gate.sql` 及一整组 `post_release_role_e2e_gate_smoke_*` required SQL、容器重建、HTTP readiness、scheduler smoke、发布锁释放、NAS 发布历史与远端临时文件清理。
- 执行命令：只读核对备份服 `172.30.30.59` 的 `/opt/intruoyi/runtime/.env`、`docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'` 与 `http://172.30.30.59:48081/actuator/health`、`http://172.30.30.59:8081/`、`http://172.30.30.59:8081/pdfjs/pdf.worker.mjs` -> PASS；确认运行态 `IMAGE_TAG` 与 backend/frontend 镜像都已切到 `release-20260621-page-full-flow-v6`，三条入口均返回 HTTP `200`。
- 执行命令：只读核对备份服展厅受保护 URL 边界，执行 `DESCRIBE infra_file` 与边界计数查询 -> PASS；确认 `config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.59:9000/yudao/%'` 的记录数为 `1434`。
- 当前结论：`release-20260621-page-full-flow-v6` 已在真实页面链路一次性完整走通 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，过程中未用接口替代页面提交；接下来进入任务收尾，先运行 `task-closeout-cleanup` 预览，再按本任务范围提交相关改动。
- 2026-06-21 用户请求：`$fupan`。
- 2026-06-21 执行记录：按 fupan 技能从真实页面发布全链路任务证据中提炼项目级防错短记忆；先创建 `doc/tasks/20260621-fupan-frontend-release-full-flow-v6/`，再采集候选证据、更新项目短记忆并提交本任务文档改动。
- 2026-06-21 用户请求：`/goal 在备份服走一遍备份恢复的流程，如果出现错误进行修改并且记录，直到可以一次性走完一套完整的备份恢复流程`。
- 2026-06-21 执行记录：读取 `backup-disaster-recovery-readiness` 技能与 `references/recovery-contract.md`，核对上一维护仓任务 `20260621-fupan-frontend-release-full-flow-v6` 已 `COMPLETED`；随后读取 `docs/experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`，准备建立本次备份恢复演练任务文档。
- 2026-06-21 用户请求：`重新再走一遍，主程序合并修改了部分代码，怕已经不对了`。
- 2026-06-21 执行记录：读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`、维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,task-state.json,test-report.md}`，并只读轮询运行态文件 `runtime\runtime-control\op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209.json` 与对应 log，承接已由真实页面提交的 `build-release(v3)`。
- 2026-06-21 执行记录：补读 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`，随后持续轮询 operation `op-2026-06-21T152405848956Z-1ef14677-9eb1-4068-8859-7613a7f23209` 直到收口为 `SUCCESS`。
- 2026-06-21 执行记录：只读核对本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v3`、其中 `manifest.json` 的 `releaseTag`，并回写维护仓任务文档 `task.md`、`execution-log.md`、`task-state.json`、`test-report.md`，准备继续通过真实页面执行“部署测试服”。
- 2026-06-21 执行记录：Playwright 复用真实页面会话 `frontend-release-full-flow-mainmerge`，切换到“部署测试服”，填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v3）”，点击“预览命令”核对 `-Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v3` 后，再在真实弹窗点击“执行”，生成 operation `op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0`。
- 2026-06-22 执行记录：用户恢复“主程序合并后重新走页面发布全链路”任务后，重新读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md` 与维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,task-state.json,test-report.md}`，并只读核对 `op-2026-06-21T160352403091200Z-0fa6c660-0ec3-4f8d-aaee-c211f9ce39ed` 的 operation JSON、对应 log 尾部与本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v4\manifest.json`。
- 2026-06-22 执行记录：确认真实页面 `build-release(v4)` 已最终 `SUCCESS`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v4`，且 `manifest.json` 记录的后端源提交已更新为 `74f505d86b7cf7be9fe2d481d36ca5a7fe45f68a`、前端源提交为 `37359a074cedcc0a341f17cb0abdd1a71f838731`。
- 2026-06-22 执行记录：回写维护仓任务文档 `task.md`、`execution-log.md`、`task-state.json`、`test-report.md`，将任务状态从暂停恢复为进行中，下一步继续通过真实页面执行“部署测试服（v4）”。
- 2026-06-22 执行记录：Playwright 复用真实页面会话 `frontend-release-full-flow-mainmerge`，先点击“刷新”，再切换到“部署测试服”，填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v4）”，点击“预览命令”核对 `-Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v4`，随后在真实弹窗点击“执行”，生成 operation `op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e`。
- 2026-06-22 执行记录：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T162151191084700Z-02589c3a-5079-454a-b336-9b1fa37c588e.json` 与对应本机 log；确认该真实页面测试服部署先成功跨过 `20260619_mes_edhr_deployment_license_interface.sql`，随后在 `20260618_mes_edhr_label_print_queue.sql` line 126 因 `Duplicate entry '900273' for key 'system_menu.PRIMARY'` 失败。
- 2026-06-22 执行记录：按任务门禁先回写维护仓任务文档 `task.md`、`execution-log.md`、`task-state.json`、`test-report.md`，把当前阻塞更新为 `20260618_mes_edhr_label_print_queue.sql` 的 `system_menu` 主键冲突；下一步转入业务仓定位并修复该新根因。
- 2026-06-22 执行记录：读取 `bug-regression-fix-loop` 技能、`bug-contract.md`、业务仓上一任务 `20260621-edhr-deployment-menu-id-collision-fix/task.md` 与 `20260621-post-release-role-e2e-gate-backup-scheduler-role/task.md`，确认上一后端任务已 `COMPLETED`，随后在业务仓新建任务目录 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\` 并落地 `task.md`、`execution-log.md`。
- 2026-06-22 执行记录：只读搜索源码与测试服真实 `system_menu`，确认 `20260618_mes_edhr_label_print_queue.sql` 复用了 `900272-900283`；其中 `900272-900279` 已被 `20260618_mes_edhr_form_instance.sql`/真实库“eDHR独立表单*”菜单占用，`900280-900283` 又被“eDHR报表目录 / 报表查询 / 报表导出审计 / 交付驾驶舱”占用；同时源码和测试库都未发现 `900320-900331` 冲突。
- 2026-06-22 执行记录：先在 `script\\tests\\test_edhr_label_print_queue_schema_sql.py` 补 RED 回归，要求 label print 菜单切到独立 `900320-900331` 且不再复用 `900272-900283`；执行 `python -X utf8 -m pytest ...test_edhr_label_print_queue_schema_sql.py -q` -> FAIL。
- 2026-06-22 执行记录：最小修改 `sql\\mysql\\20260618_mes_edhr_label_print_queue.sql`，把 label print 菜单整段从 `900272-900283` 切换到 `900320-900331`；执行 `python -X utf8 -m pytest script\\tests\\test_edhr_label_print_queue_schema_sql.py script\\tests\\test_edhr_form_schema_sql.py -q`、`python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` 与 `python C:\\Users\\BJB110\\.codex\\skills\\bug-regression-fix-loop\\scripts\\validate_bug_regression.py --evidence D:\\ProjectPackage\\Int\\IntRuoyi\\ruoyi-vue-pro\\doc\\tasks\\20260622-edhr-label-print-menu-id-collision-fix\\bug-regression-evidence.md` -> PASS。
- 2026-06-22 执行记录：回写维护仓主任务文档，明确 `release-20260621-page-full-flow-mainmerge-v4` 已失效，下一步必须通过真实页面重新构建新的 `release-20260621-page-full-flow-mainmerge-v5`，再从测试服开始重走整条发布链路。
- 2026-06-21 执行记录：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T153931119750100Z-4bd5851f-51cf-4e9e-bdcb-706e455f8fa0.json` 与对应本机 log；确认真实页面测试服部署最终 `FAILED`，失败点为 `20260619_mes_edhr_deployment_license_interface.sql` line 327 抛出 `Missing eDHR deployment system_menu rows; cannot merge tenant package menu_ids`，随后按任务门禁先回写维护仓任务文档。
- 2026-06-21 执行记录：切到业务仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，读取 `20260619_mes_edhr_deployment_license_interface.sql`、`script\tests\test_edhr_deployment_schema_sql.py` 与既有任务 `doc\tasks\20260621-edhr-deployment-menu-id-collision-fix\{task.md,execution-log.md}`；随后通过只读 SSH 查询测试服 `system_menu`，确认当前仅有 `900315-900318` 四条 deployment 菜单、旧 `900300` 已不存在。
- 2026-06-21 执行记录：在业务仓新增 RED 契约 `test_deployment_schema_cleans_legacy_rows_before_inserting_new_menu_ids`，执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_edhr_deployment_schema_sql.py -q` -> FAIL；随后把 legacy cleanup 前移到 `900315-900319` 菜单插入之前，再执行同一 pytest -> PASS（6 passed），并执行 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS。
- 2026-06-21 执行记录：回写业务仓任务 `20260621-edhr-deployment-menu-id-collision-fix` 与维护仓主任务 `20260621-frontend-release-full-flow-main-merge-rerun`，明确本次修复再次改变发布包输入，下一步必须通过真实页面重新构建新的 `release-20260621-page-full-flow-mainmerge-v4` 并从测试服开始重走全链路。
- 2026-06-21 用户请求：`在测试服务器，正式服务器，备份服务器配置好codex cli的运行环境，连接参数与本机相同，全部跑通视为目标完成`。
- 2026-06-21 执行记录：读取 `spec-driven-delivery`、`ci-cd-environment-delivery`、`openai-docs` 技能；读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 命中的 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；检查上一维护仓任务 `20260621-frontend-release-full-flow-main-merge-rerun`，并将其显式转为 `blocked`。
- 2026-06-21 执行记录：执行本机只读核对 `codex --version`、读取 `C:\Users\BJB110\.codex\config.toml` / `auth.json` / `version.json`，并在临时移除当前 shell 的 `OPENAI_API_KEY` / `OPENAI_BASE_URL` 后执行 `codex -a never -s read-only exec --skip-git-repo-check -c model_reasoning_effort='"low"' --color never -o <temp> "Respond with exactly OK and nothing else."` -> PASS；确认最小可复制连接方案为 `auth.json + config.toml`。
- 2026-06-21 执行记录：只读 SSH 预检三台服务器，执行 `uname -a`、`cat /etc/os-release`、`command -v curl/tar/node/npm/sudo`；确认测试服 `172.30.30.58` 与备份服 `172.30.30.59` 无 `node/npm`，正式服 `172.30.30.57` 已有 `node v22.22.2 / npm 10.9.7`，因此本任务统一采用官方 standalone installer。
- 2026-06-21 执行记录：创建维护仓任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-codex-cli-three-server-setup\`，补齐 `task.md`、`prd.md`、`test-plan.md`、`execution-log.md`、`test-report.md`、`task-state.json` 与 `remote-config.toml`，并执行 `python C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_artifacts.py --cwd D:\ProjectPackage\Int\IntRuoyiMaintance --task-id 20260621-codex-cli-three-server-setup` -> PASS。
- 2026-06-22 用户请求：`在测试服务器，正式服务器，备份服务器配置好codex cli的运行环境，连接参数与本机相同，全部跑通视为目标完成`。
- 2026-06-22 执行记录：继续推进 `20260621-codex-cli-three-server-setup`，依次执行 `ssh root@172.30.30.57/58/59` 的目录准备、`scp` 同步 `remote-install-codex-cli.sh` / `remote-smoke-codex.sh` / `remote-config.toml` / `auth.json`、`yum install -y bubblewrap`（test/prod）、`/root/codex-cli-setup/remote-smoke-codex.sh`（三台），并对备份服执行 `curl -I -L --max-time 60` 直连 release 资产检查与 `scp -3 root@172.30.30.58:/usr/local/bin/codex root@172.30.30.59:/usr/local/bin/codex` 受控中转 -> PASS。
- 2026-06-22 执行记录：确认测试服、正式服、备份服均返回 `codex-cli 0.128.0` 且真实 `codex exec` 冒烟返回 `OK`；备份服因 GitHub release 直连超时，最终以测试服验证过的同版官方二进制中转完成安装，仍可正常运行。
- 2026-06-22 执行记录：执行 `python C:\Users\BJB110\.codex\skills\spec-driven-delivery\scripts\validate_artifacts.py --cwd D:\ProjectPackage\Int\IntRuoyiMaintance --task-id 20260621-codex-cli-three-server-setup`、`validate_test_report.py`、`record_phase_review.py`、`record_test_review.py`、`check_completion.py --apply` -> PASS；随后按 `task-closeout-cleanup` 先预览、再在 `task.md` 补充英文 `## Current Status` 元数据后执行 `task_closeout.py --task-id 20260621-codex-cli-three-server-setup --mode apply`，仅保留 `task.md` 与 `execution-log.md`。
- 2026-06-21 用户请求：`/goal 在备份服走一遍备份恢复的流程，如果出现错误进行修改并且记录，直到可以一次性走完一套完整的备份恢复流程`。
- 2026-06-21/22 执行记录：读取 `backup-disaster-recovery-readiness`、`bug-regression-fix-loop` 技能与 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`release-backup-restore.md`、`login-access.md`；创建/继续维护 `doc\tasks\20260621-backup-server-backup-restore-rehearsal\`，运行 `Invoke-Pester -Path ops\backup-ops\tests\BackupTargetEnvironment.Tests.ps1 -EnableExit` 与 `Invoke-Pester -Path ops\backup-ops\tests -EnableExit` 多轮 RED/GREEN，修复 backup 环境在 FileOps/DockerOps/MySqlOps/ObjectOps/DCC/Rehearsal 链路中的 test 硬编码。
- 2026-06-21/22 执行记录：只读执行备份服状态脚本 `show-int-ruoyi-remote-status.ps1 -ServerHost 172.30.30.59 ... -Json`，并通过 SSH preflight 核对 `/mnt/intruoyi-data` 数据盘、`/mnt/intruoyi-data/Backup/BackupPackage`、`/mnt/intruoyi-data/backup-ops/rehearsal/runtime`、`/mnt/intruoyi-data/runtime-data/backup-ops/tmp`、`IMAGE_TAG=release-20260621-page-full-flow-v6` 与 `intruoyi-minio` 等容器；发现目录缺失后仅在数据盘下最小创建受保护目录并重跑 preflight -> PASS。
- 2026-06-21/22 执行记录：执行 `backup-ops.ps1 -Mode backup-now -TargetEnvironment backup -NonInteractive -OperatorName codex`，先后记录 `20260621-185935` MinIO credential ValidateSet 失败、`20260621-191229` DCC manifest gate 阻塞，并在备份服测试租户 `tenant_id=122` 精确软删除 96 条 active 且引用 `/codex-e2e/%` 缺失对象的 DCC 测试残留主记录；最终备份点 `20260621-202814` 成功，产物 `manifest.json`、`dcc-backup-manifest.json`、`checksums.txt`、MySQL dump、object inventory 与 deploy 元数据均非空。
- 2026-06-21/22 执行记录：执行 `backup-ops.ps1 -Mode rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814 -NonInteractive -OperatorName codex`，先后记录 DCC chain validator、MySQL rehearsal repository proof、rehearsal evidence 写回三处 backup 环境缺陷并按 RED/GREEN 修复；最终 `20260621_224143_rehearsal_success.log` 成功，校验 `backendHealth/frontendHttp200/loginReachable/fileDownloadSample` 均 `pass`，远端 manifest 更新为 `rehearsalStatus=PASSED`。
- 2026-06-22 执行记录：执行 `backup-ops.ps1 -Mode restore-data -TargetEnvironment backup -SelectedBackupId 20260621-202814 -NonInteractive -OperatorName codex` -> PASS；恢复报告 `20260621_235941_restore-data_success.report.md` 记录 pre-restore 快照 `20260621_235953_pre-restore`，恢复后状态脚本确认备份服 `backend/frontend/pdfWorker/OnlyOffice=HTTP 200` 且 `currentReleaseTag=release-20260621-page-full-flow-v6`。
- 2026-06-22 执行记录：执行 `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit` -> PASS，13/13；执行 `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\bug-regression-evidence.md` -> PASS；执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --workspace D:\ProjectPackage\Int\IntRuoyiMaintance --task-id 20260621-backup-server-backup-restore-rehearsal --mode preview --json` -> PASS，保留任务文档、执行日志和缺陷证据，无删除项。
- 2026-06-22 用户请求：`再进行一次备份恢复`。
- 2026-06-22 执行记录：创建维护仓任务 `doc\tasks\20260622-backup-server-backup-restore-rerun\`，读取 `backup-disaster-recovery-readiness`、`docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md` 与项目错误预防短记忆；目标限定为备份服 `172.30.30.59` 再次执行 `backup-now -> rehearsal -> restore-data`，高风险动作前需先记录 `experience-preflight`。
- 2026-06-22 执行记录：执行备份服再次备份恢复演练 -> PASS；新备份点 `20260622-063253` 完成 `backup-now -TargetEnvironment backup`、`rehearsal -TargetEnvironment backup -SelectedBackupId 20260622-063253`、`restore-data -TargetEnvironment backup -SelectedBackupId 20260622-063253 -NonInteractive`；恢复报告 `D:\IntRuoyi-BackupOps\logs\202606\20260622_080523_restore-data_success.report.md` 记录结果 `success`，恢复后状态脚本确认 `backend/frontend/pdfWorker/OnlyOffice=HTTP 200` 且 `currentReleaseTag=release-20260621-page-full-flow-v6`。
- 2026-06-22 执行记录：最终验证 `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit` -> PASS，13/13；执行 `task_closeout.py --workspace D:\ProjectPackage\Int\IntRuoyiMaintance --task-id 20260622-backup-server-backup-restore-rerun --mode preview --json` -> PASS，仅保留本轮 `task.md` 与 `execution-log.md`，无删除项。
- 2026-06-22 用户请求：`重新再走一遍，主程序合并修改了部分代码，怕已经不对了`。
- 2026-06-22 执行记录：重新读取 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`；业务仓标签打印冲突修复已提交为 `6d96efef31`，随后复用真实页面会话 `frontend-release-full-flow-mainmerge` 在 `http://127.0.0.1:48181/` 上完成 `build-release(v5)` 预览、提交与成功收口，发布包路径为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v5`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，先 `snapshot` 确认 `build-release(v5)` 成功页态，再点击“部署测试服”、填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v5）”、点击“预览命令”。
- 2026-06-22 执行记录：真实页面 `deploy-test(v5)` 预览阶段先把 `-RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1` 误判为参数漂移；随后立即只读核对 `backend/src/main/resources/application.yaml`、`ops/deploy/publish-int-ruoyi.ps1`、历史真实通过任务证据，并执行 `show-int-ruoyi-remote-status.ps1 -ServerHost 172.30.30.58 ... -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 -Json`，确认这组值是测试服当前真实基线，状态返回 `running`、`currentReleaseTag=release-20260621-page-full-flow-mainmerge-v4`；随后回写主任务文档更正结论，继续沿真实页面链路推进。
- 2026-06-22 执行记录：在同一真实预览弹窗点击“执行”，生成 operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50`；随后持续只读轮询 `runtime/runtime-control/op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50.json` 与对应 log，确认测试服部署先成功跨过 `20260618_mes_edhr_label_print_queue.sql`，随后在 `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 357 因 `Invalid eDHR OQ/PQ button menu definition; cannot merge tenant package menu_ids` 失败。
- 2026-06-22 执行记录：按任务门禁先回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md}`，把当前阻塞更新为 OQ/PQ 菜单定义冲突；下一步转入业务仓定位并修复该新根因。
- 2026-06-22 执行记录：读取 `C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\SKILL.md`、`references\bug-contract.md`、`D:\ProjectPackage\Int\IntRuoyi\AGENTS.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md`，并复核业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\{task.md,execution-log.md,bug-regression-evidence.md}` 与三项已通过验证命令 -> PASS。
- 2026-06-22 执行记录：在业务仓只暂存 `script/tests/test_edhr_oq_pq_schema_sql.py`、`sql/mysql/20260618_mes_edhr_oq_pq_execution_deviation.sql`、`doc/tasks/20260622-edhr-oq-pq-menu-definition-fix/task.md`、`execution-log.md`，设置 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix` 后执行 `git commit -m "任务: 修复OQ/PQ菜单定义冲突"` -> PASS，提交 `0d82319b98`。
- 2026-06-22 执行记录：发现 `bug-regression-evidence.md` 被 `.gitignore` 拦截后，执行 `git add -f -- doc/tasks/20260622-edhr-oq-pq-menu-definition-fix/bug-regression-evidence.md`，继续沿用 `TDD_TASK_DIR=...20260622-edhr-oq-pq-menu-definition-fix` 执行 `git commit -m "任务: 补充OQ/PQ回归证据"` -> PASS，提交 `3ace5094ec`；随后回写维护仓主任务 `task.md` 与 `execution-log.md`，明确当前后端发布输入已更新到 `3ace5094ec7768237e7249b876a4eca67dad5e2a`，旧 `release-20260621-page-full-flow-mainmerge-v5` 已失效。
- 当前结论：主程序合并后这轮真实页面发布链路当前停在“修复已提交、等待重新 build-release”状态；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，用新标签 `release-20260621-page-full-flow-mainmerge-v6` 重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：复用真实页面会话 `frontend-release-full-flow-mainmerge`，切回“构建发布包”，填写原因“主程序合并后重新验证页面发布全链路：oq-pq-menu修复后重建发布包（v6）”与 `releaseTag=release-20260621-page-full-flow-mainmerge-v6`，点击“预览命令”确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v6 -Component intruoyi -SkipDatabaseSync -SkipMinioSync ...`，随后在真实弹窗点击“执行”，生成 operation `op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb`。
- 2026-06-22 执行记录：只读轮询 `runtime\runtime-control\op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb.json` 与对应 log，确认 v6 真实页面构建依次完成 backend `mvn ... clean package`、frontend `vite build --mode test`、backend image 构建和 NAS 上传，最终 `SUCCESS`；本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v6` 生成 `manifest.json`、`release-manifest.json`、`intruoyi-images_release-20260621-page-full-flow-mainmerge-v6.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v6`。
- 2026-06-22 执行记录：继续只读核对 `manifest.json` 与 `release-manifest.json`，确认 backend 源提交为 `3ace5094ec7768237e7249b876a4eca67dad5e2a`、admin frontend 源提交为 `37359a074cedcc0a341f17cb0abdd1a71f838731`；随后执行 `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro status --short` 与 `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short`，发现 backend/front 都存在 DCC 识别相关未提交改动，对应 `manifest.json sourceRepos` 也标记为 `dirty=true`。
- 当前结论：`build-release(v6)` 已真实页面成功，但当前候选包不是 clean merged-main 基线，而是混入未提交 DCC 工作树改动的 dirty baseline；在用户未明确这些未提交 DCC 改动是否应纳入本轮发布链路前，不能继续 `deploy-test(v6) -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：按 worktree 门禁新建成对 clean release worktree，后端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro` 与前端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3` 均切到 branch `codex/20260622-page-full-flow-mainmerge-release-clean`，分别停留在 `3ace5094ec` 与 `37359a074`，`git status --short` 为空 -> PASS。
- 2026-06-22 执行记录：将本机运维台局部配置 `D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 切换到上述 clean worktree，准备重启 `48181` 运维控制台后继续通过页面按钮推进 `deploy-test(v6)`；当前旧脏工作区保留不动，未做回滚或删除。
- 2026-06-22 执行记录：复用维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\`，只读读取 `control-in-app-browser`、`playwright`、`bug-regression-fix-loop`、`database-schema-delivery` 技能和当前 `task.md` / `execution-log.md` / `task-state.json`，确认当前 clean release worktree 基线与 v8 真实页面构建成功证据。
- 2026-06-22 执行记录：只读核对维护仓 operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e` 日志，确认真实页面 `deploy-test(v8)` 已提交到测试服并在 `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 399 因 `Missing eDHR OQ/PQ system_menu rows; cannot merge tenant package menu_ids` 失败；此前 `20260613_dcc_file_view_matrix_seed`、`20260615_showroom_hall_canvas_background`、`20260618_mes_edhr_label_print_queue`、`20260618_post_release_role_e2e_gate` 均已成功跨过。
- 2026-06-22 执行记录：只读读取 `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`、`release-backup-restore.md`、`server-access.md` 与 `login-access.md`，并通过 `ssh root@172.30.30.58` + `docker exec intruoyi-mysql mysql ...` 的受控 SQL 文件查询核对测试服真实 `system_menu` 现场：`900332-900337` 仅存在 `900335-900337`，`900332-900334` 缺失，旧 OQ/PQ `900290-900292` 也已不存在。
- 当前结论：`deploy-test(v8)` 的真实新阻塞不是旧 OQ/PQ 按钮定义冲突，而是 `20260618_mes_edhr_oq_pq_execution_deviation.sql` 的 cleanup 顺序缺陷。当前脚本会先因旧 `path/permission` 残留而跳过 `900332-900334` 新插入，再删除 legacy `900290-900292`，最终把页面/查询/创建三条删空，只剩 `900335-900337`；下一步必须在业务后端新建任务按严格 TDD 修复正式 SQL，然后回真实页面用 `release-20260621-page-full-flow-mainmerge-v9` 重新执行 `build-release -> deploy-test`。
- 当前结论：业务后端已完成 cleanup 顺序修复并通过 `pytest`、迁移策略门禁与 bug regression validator；维护仓下一步需要改用新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v9` 重新构建发布包，然后继续真实页面 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 用户请求：重新再走一遍，主程序合并修改了部分代码，怕已经不对了。执行记录：已确认当前任务保持在 T4，下一步用 `release-20260621-page-full-flow-mainmerge-v9` 从真实页面继续重跑 `build-release -> deploy-test`。
- 2026-06-22 执行记录：复用真实页面会话 `frontend-release-full-flow-mainmerge`，将 `操作原因` 改为 `主程序合并后重新验证页面发布全链路：oq-pq-cleanup-order修复后重建发布包（v9）`，将 `发布标签` 改为 `release-20260621-page-full-flow-mainmerge-v9`，并在“命令预览”确认脚本仍为 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v9 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`。
- 2026-06-22 执行记录：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T010042891831400Z-d59751ca-ab81-4136-b128-0f98537c2cd5.json` 与对应 log，确认真实页面 `build-release(v9)` 最终 `SUCCESS`；候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v9` 与 NAS 目录 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v9` 均已生成，`manifest.json` 记录 backend/frontend commit 为 `3ace5094ec` / `37359a074` 且 `dirty=false`。
- 2026-06-22 执行记录：继续复用真实页面会话切到“部署测试服”，填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v9）”，在预览弹窗确认 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v9 -ServerHost 172.30.30.58 ...` 后点击“执行”，生成 operation `op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a`。
- 2026-06-22 执行记录：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a.json` 与对应 log，确认测试服部署先成功跨过 `20260618_mes_edhr_oq_pq_execution_deviation.sql`，随后在 `20260618_mes_edhr_print_policy_reissue_void.sql` line 103 因 `Duplicate entry '900285' for key 'system_menu.PRIMARY'` 失败；已按门禁先回写维护仓主任务文档，下一步转入业务仓定位并修复该新的 `system_menu` 主键冲突根因。
- 2026-06-22 执行命令：`git -C D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro cherry-pick fd63921684d44f5f942befeeded64f2eb55348e7`、`git -C D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro cherry-pick db411a242d9f97ffe94c8682c0fcf087961ccf97` -> PASS；已将 print policy 菜单冲突修复及回归证据并入 clean release backend worktree，当前 HEAD 为 `a72602e2f0`。
- 2026-06-22 执行记录：回写维护仓任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md}`，将 clean release backend 基线更新为 `a72602e2f0`，并明确下一步必须以新标签 `release-20260621-page-full-flow-mainmerge-v10` 通过真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge click e154`、`click e70`、`fill e85 "主程序合并后重新验证页面发布全链路：print-policy修复后重建发布包（v10）"`、`fill e104 "release-20260621-page-full-flow-mainmerge-v10"`、`click e125`、`snapshot` -> PASS；真实页面已回到“构建发布包”，并在预览弹窗确认 `publish-int-ruoyi.ps1 -Mode build-release` 的 `BackendRepoRoot/FrontendRepoRoot` 继续指向 clean release worktree。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge click e1346`、`snapshot` -> PASS；已在真实页面预览弹窗点击“执行”，生成 `build-release(v10)` operation `op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7`，当前状态为 `RUNNING / 命令已提交到本机执行队列`。
- 2026-06-22 执行命令：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7.json` 与对应 log，确认真实页面 `build-release(v10)` 最终 `SUCCESS`；随后只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v10\manifest.json`、`release-manifest.json` 与候选目录，确认 backend/front commit 为 `a72602e2f0` / `37359a074`，两仓 `dirty=false`，NAS 路径为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v10`。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge click e71`、`fill e85 "主程序合并后重新验证页面发布全链路：部署测试服（v10）"`、`fill e104 "release-20260621-page-full-flow-mainmerge-v10"`、`click e125`、`snapshot` -> PASS；真实页面已切到“部署测试服”，并在预览弹窗确认 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v10 ...`，目标仍为测试服 `172.30.30.58`。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge click e1346`、`snapshot`，随后只读核对最新 operation `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3.json` -> PASS；确认已在真实页面提交 `deploy-test(v10)`，operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3` 当前为 `RUNNING`。
- 2026-06-22 用户请求：`继续`。
- 2026-06-22 执行记录：只读核对维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,task-state.json,test-report.md}`、运行态文件 `runtime\runtime-control\op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3.json` 与对应 log 尾部，确认真实页面 `deploy-test(v10)` 已最终 `FAILED`，新失败点切换为 `20260618_mes_edhr_dhr_template_lifecycle.sql` line `120` 的 `Duplicate entry '900293' for key 'system_menu.PRIMARY'`。
- 2026-06-22 执行记录：按“先记录再修复”门禁，先回写维护仓主任务 `task.md`、`execution-log.md`、`task-state.json`、`test-report.md` 与本日志，明确 `release-20260621-page-full-flow-mainmerge-v10` 已失效，下一步必须在业务后端修复 DHR 模板菜单冲突后，用新的 `releaseTag` 从真实页面重新 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：在业务仓新建任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix\`，按严格 TDD 修复 `20260618_mes_edhr_dhr_template_lifecycle.sql` 的菜单冲突：只读确认测试服 `900293-900299` 被 `eDHR统一变更` 占用后，先在 `script/tests/test_edhr_dhr_template_schema_sql.py` 补 RED 契约要求 DHR 模板按钮改用 `900347-900352`，执行 `python -X utf8 -m pytest ...test_edhr_dhr_template_schema_sql.py -q` -> FAIL；随后最小修改 SQL，把按钮段与 fail-fast/菜单合并列表整体切到 `900347-900352`，再执行同一 pytest、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 `validate_bug_regression.py --evidence ...20260622-edhr-dhr-template-menu-id-collision-fix\\bug-regression-evidence.md` -> PASS。
- 2026-06-22 执行记录：在业务仓只暂存 `script/tests/test_edhr_dhr_template_schema_sql.py`、`sql/mysql/20260618_mes_edhr_dhr_template_lifecycle.sql` 与任务目录 `doc/tasks/20260622-edhr-dhr-template-menu-id-collision-fix/`，设置 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix` 后执行 `git commit -m "任务: 修复DHR模板菜单冲突"` -> PASS，提交 `e7a11af216`。
- 2026-06-22 执行记录：执行 `git -C D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro cherry-pick e7a11af216206d78dc698b0a52b6c3bac7f03281` -> PASS；已将 DHR 模板菜单冲突修复并入 clean release backend worktree，当前 HEAD 为 `d9606a65df`。随后回写维护仓主任务，明确下一步必须以新标签 `release-20260621-page-full-flow-mainmerge-v11` 通过真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：只读核对真实页面 `build-release(v11)` operation `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f.json` 与对应 log，确认本机构建在 Maven/Vite 打包前被维护仓 SQL 预检门禁误报拦下，错误为 `system_menu.id must be an integer literal for release preflight: .../20260520_system_nas_management_menu.sql:11 -> \`name\``。
- 2026-06-22 执行记录：按“先记录再修复”门禁，先回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,task-state.json,test-report.md}`，将当前阶段回拨到 `build-release` 并明确旧标签 `release-20260621-page-full-flow-mainmerge-v11` 已失效；下一步必须先在维护仓按严格 TDD 修复 `ops/release/release_sql_contract_gate.py` 对 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 的误解析，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：继续在维护仓任务 `doc/tasks/20260622-sql-preflight-gate/` 按严格 TDD 收口该误报；先在 `scripts/tests/test_release_sql_preflight_gate.py` 新增 `test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause`，执行 `python -X utf8 -m pytest ...test_release_sql_preflight_gate.py -q` -> FAIL，复现 `` `name` `` 被误解析为 `system_menu.id`。
- 2026-06-22 执行记录：最小修改 `ops/release/release_sql_contract_gate.py` 的 `_extract_value_tuples()`，使其只连续解析真正的顶层 `VALUES (...)` 插入元组，遇到 `ON DUPLICATE KEY UPDATE` 这类非逗号分隔后续内容立即停止；随后执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> PASS（4 passed）、`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS（3 passed）、`python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro\sql\mysql` -> PASS（`migrationCount=186`）。
- 2026-06-22 执行记录：补写维护仓 `doc/tasks/20260622-sql-preflight-gate/{task.md,execution-log.md,bug-regression-evidence.md}` 与主发布链路任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，明确维护仓 SQL 预检误判已收口；下一步将只提交本次维护仓修复后，回真实页面以新标签 `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：继续读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,test-report.md,task-state.json}`、轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T040752788980600Z-65f35dd8-4afa-4a4e-a9ee-5f04a5dd500a.json` 与对应 log，并只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v12\manifest.json` -> PASS；确认真实页面 `build-release(v12)` 已最终 `SUCCESS`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v12`，backend/front source commit 为 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，两仓 `dirty=false`。
- 2026-06-22 执行记录：回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md}`，将里程碑 T3 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `deploy-test(v12)`，再根据结果继续 `mark-tested -> prod -> backup` 或按门禁记录新阻塞后修复重走。
- 2026-06-22 执行记录：复用真实页面会话 `frontend-release-full-flow-mainmerge`，先点击“刷新”，再切换到“部署测试服”，填写原因“主程序合并后重新验证页面发布全链路：部署测试服（v12）”与 `releaseTag=release-20260621-page-full-flow-mainmerge-v12`，在“命令预览”中只读确认脚本仍为 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v12 -ServerHost 172.30.30.58 ...`，随后在真实弹窗点击“执行”，生成 operation `op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388`。
- 2026-06-22 执行记录：持续只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388.json` 与对应 log，确认真实页面 `deploy-test(v12)` 已最终 `FAILED`；本轮已成功跨过镜像加载、测试服 `mysql/redis` 启动、`post-import.sql` 执行和 `20260613_infra_release_migration_state.sql` bootstrap，但随后在 `infra_release_operation_lock` 的测试环境锁获取步骤中，本机脚本通过 `grep '^LOCK_ACQUIRED$'` 断言锁获取结果时收到退出码 `1`，导致当前测试服部署提前中断。
- 2026-06-22 执行记录：按“先记录再修复”门禁，先回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md}`，将本轮新阻塞更新为测试环境发布锁获取失败；下一步仅做只读核对测试服 `infra_release_operation_lock` 当前真实状态与维护仓锁契约，再决定是否需要在维护仓按严格 TDD 修复根因。
- 2026-06-22 执行记录：执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` -> PASS（`2 passed`），确认维护仓此前修复过的“持锁后 fail-fast 必须先释放 `infra_release_operation_lock` 再退出”契约未回退，本轮锁阻塞不是旧的发布锁释放代码回归。
- 2026-06-22 执行记录：只读 SSH 审计测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、`infra_release_operation_lock`、`infra_release_migration`、`/var/lib/docker/intruoyi-releases` 与 `docker ps` -> PASS；确认此前阻断 `deploy-test(v12)` 的 `target_environment='test'` 锁实际来自外部链路 `test-20260622_121338 / 20260622_121338`，并已被其他流程收口为 `FAILED`（`finished_at=2026-06-22 12:45:12`，`error_message='Recovered stale RUNNING lock after 20260622 DCC preview release failures; later fixes require retry.'`）。同时确认测试服共享环境已发生漂移：`.env` 当前 `IMAGE_TAG=20260622_123255`，但运行容器仍混杂为 backend `release-20260621-page-full-flow-mainmerge-v10`、frontend `release-20260621-page-full-flow-v6`，说明当前主阻塞已切换为共享测试环境被外部失败发布链路改写成半切换态。
- 2026-06-22 执行记录：回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，明确本轮发布包输入未变化、维护仓锁释放回归已通过；下一步不重新 `build-release`，而是继续通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重试 `deploy-test`，待测试服重新回到本任务候选包后再继续 `mark-tested -> prod -> backup`。
- 2026-06-22 用户请求：`现在有没有类似个人中心的页签，可以看到所有的任务`。
- 2026-06-22 执行记录：创建维护仓任务 `doc/tasks/20260622-task-tab-inventory/`，只读核对 `docs/experience-index.md`、`docs/agent-memory/project-error-prevention.md`、上一任务 `doc/tasks/20260622-sql-preflight-gate/task.md` 完成状态，并登记本次盘点边界。
- 2026-06-22 执行命令：`rg -n --hidden -S "待办|已办|我的任务|任务中心|个人中心|工作流|审批|流程" D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src`、`rg -n --hidden -S "todo|done|my task|task center|workflow|bpm" D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src`、`rg -n --hidden -S "待办|已办|我的任务|工作流|审批|流程" D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` -> PASS；定位到 BPM、DCC、eDHR、展厅等多套任务/审批入口。
- 2026-06-22 执行记录：只读核对前端路由 `src/router/modules/remaining.ts`、`src/router/modules/showroom.ts`，确认标准 `Profile` 页面仅含基础信息/改密/社交绑定；BPM `我的申请/待办任务`、DCC `工作台`、展厅 `审批中心` 为独立入口，不挂在个人中心下。
- 2026-06-22 执行记录：只读核对前端页面 `src/views/Profile/Index.vue`、`src/views/bpm/task/{todo,done}/index.vue`、`src/views/bpm/processInstance/index.vue`、`src/views/dcc/controlled-file/{workbench,approval-tasks}/index.vue`、`src/views/mes/pro/edhr-work-task/WorkTaskBoardPage.vue`，确认：
  - 个人中心无任务页签；
  - BPM 审批中心可看 `我的流程 / 待办任务 / 已办任务 / 抄送我的`；
  - DCC 工作台含“我的审批待办”，可跳转到 `DCC审批任务`；
  - eDHR 工作任务页含 `我的待办 / 候选审核 / 逾期任务 / 我已处理`。
- 2026-06-22 执行记录：只读核对菜单 SQL `sql/mysql/ruoyi-vue-pro.sql`、`sql/mysql/20260513_dcc_base_schema.sql`、`sql/mysql/20260611_mes_edhr_work_task_flow.sql`，确认 `审批中心`、`待办任务`、`已办任务`、`DCC审批任务`、`DCC我的文件`、`eDHR工作任务` 均已登记为真实菜单入口。
- 2026-06-22 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-task-tab-inventory --mode preview` -> PASS；预览结果仅保留 `task.md` 与 `execution-log.md`，无额外清理项。
- 2026-06-22 用户请求：`$fupan`。
- 2026-06-22 执行记录：创建维护仓复盘任务 `doc\tasks\20260622-fupan-backup-restore-rerun\`，读取 `C:\Users\BJB110\.codex\skills\fupan\SKILL.md`、`references\project-memory-template.md`、备份恢复再次演练任务 `task.md/execution-log.md`、本请求日志与 `docs\agent-memory\project-error-prevention.md`。
- 2026-06-22 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\update_project_memory.py --memory-file D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md --max-file-chars 800 --entry "备份/恢复 preflight 用 UTF-8无BOM、LF 脚本；核数据盘/备份根/对象存储/IMAGE_TAG；证据: 20260622-backup-rerun"` -> PASS；短记忆长度为 `760` 字符，保留在默认 800 上限内。
- 2026-06-22 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\collect_error_evidence.py --project-root D:\ProjectPackage\Int\IntRuoyiMaintance --glob doc/tasks/20260622-backup-server-backup-restore-rerun/task.md --glob doc/tasks/20260622-backup-server-backup-restore-rerun/execution-log.md --glob docs/request-command-log.md --glob docs/agent-memory/project-error-prevention.md --output doc/tasks/20260622-fupan-backup-restore-rerun/candidate-error-evidence.md --context-lines 1 --max-matches-per-file 8` -> PASS；候选证据确认采纳规则具备项目级泛化价值，本次未提升到 `AGENTS.md`。
- 2026-06-22 执行记录：继续推进主任务 `20260621-frontend-release-full-flow-main-merge-rerun`，先重读 `task.md`、`execution-log.md`、`test-report.md`、`task-state.json`、`docs/experience-index.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\{release-backup-restore.md,server-access.md,login-access.md}`，确认本轮仍须坚持“先记证据，再恢复，再回页面”的门禁。
- 2026-06-22 执行命令：只读核对测试服 `172.30.30.58` 当前进程与运行控制目录，执行 `ssh -o BatchMode=yes root@172.30.30.58 "pgrep -af 'publish-int-ruoyi|backup-ops|runtime-control|deploy-release|20260622_124533'; echo __SEP__; grep -R --line-number --fixed-strings '20260622_124533' /opt/intruoyi/runtime/data/runtime-control 2>/dev/null | head -20"` -> PASS；结果仅见长期驻留的运行控制 Java 进程，未发现可归属 `20260622_124533` 的活跃发布 shell，运行控制目录也未命中该 releaseTag。
- 2026-06-22 执行命令：只读核对测试服运行态与外部残留目录，执行 `ssh -o BatchMode=yes root@172.30.30.58 "echo ENV; grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env; echo CONTAINERS; docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'; echo RELEASE_DIR; stat -c '%y %n' /var/lib/docker/intruoyi-releases/20260622_124533"` -> PASS；确认 `.env=release-20260621-page-full-flow-mainmerge-v12`、backend 容器已是 `release-20260621-page-full-flow-mainmerge-v12`、frontend 仍为 `release-20260621-page-full-flow-v6`，且残留目录 `/var/lib/docker/intruoyi-releases/20260622_124533` 的时间戳为 `2026-06-22 12:55:59 +0800`。
- 2026-06-22 执行命令：只读核对测试服数据库现场，执行 `ssh -o BatchMode=yes root@172.30.30.58 "docker exec intruoyi-mysql mysql -N -B -uroot -p123456 -e \"SHOW DATABASES;\""`、`ssh -o BatchMode=yes root@172.30.30.58 "docker exec intruoyi-mysql mysql -N -B -uroot -p123456 -D ruoyi-vue-pro -e \"SELECT operation_id,release_tag,target_environment,status,started_at,finished_at,IFNULL(error_message,'') FROM infra_release_operation_lock WHERE target_environment='test' ORDER BY started_at DESC LIMIT 5;\""`、`ssh -o BatchMode=yes root@172.30.30.58 "docker exec intruoyi-mysql mysql -N -B -uroot -p123456 -D ruoyi-vue-pro -e \"SELECT COUNT(*) FROM infra_release_migration WHERE status='RUNNING';\""` 与 `SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING';` -> PASS；确认数据库名为 `ruoyi-vue-pro`，测试环境当前仅剩 `test-20260622_124533 / 20260622_124533 / RUNNING / 2026-06-22 12:56:16 / NULL` 这一条发布锁，`infra_release_migration` 的 RUNNING 数量为 `0`，测试环境 RUNNING 锁数量为 `1`。
- 2026-06-22 执行记录：在主任务目录新增 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/database-schema-evidence.md`，记录本次仅对测试服单条 stale `RUNNING` 锁做恢复性收口的目标、风险分析、回滚计划与验证要求；并同步回写主任务 `task.md`、`execution-log.md`、`test-report.md`、`task-state.json`，将最新阻塞更新为“先恢复性收口 `test-20260622_124533`，再回真实页面继续 deploy-test(v12)”。
- 2026-06-22 执行命令：`python -X utf8 C:\Users\BJB110\.codex\skills\database-schema-delivery\scripts\validate_database_schema.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\database-schema-evidence.md` -> PASS；结果 `Database schema evidence is valid.`。
- 2026-06-22 执行命令：在确认无活跃发布进程、无 runtime-control operation、且 `infra_release_migration` 无 RUNNING 后，对测试服 `infra_release_operation_lock` 执行最小恢复性回写：`UPDATE infra_release_operation_lock SET status='FAILED', finished_at=NOW(), error_message='Recovered stale RUNNING lock during 2026-06-22 main-merge rerun after confirming no active publish process or runtime-control operation evidence.', updater='codex', update_time=NOW() WHERE operation_id='test-20260622_124533' AND release_tag='20260622_124533' AND target_environment='test' AND status='RUNNING'; SELECT ROW_COUNT();` -> PASS；`ROW_COUNT()=1`。
- 2026-06-22 执行命令：回读验证测试服锁与迁移状态，执行 `SELECT operation_id,release_tag,target_environment,status,started_at,finished_at,IFNULL(error_message,'') FROM infra_release_operation_lock WHERE target_environment='test' ORDER BY started_at DESC LIMIT 5; SELECT COUNT(*) FROM infra_release_operation_lock WHERE target_environment='test' AND status='RUNNING'; SELECT COUNT(*) FROM infra_release_migration WHERE status='RUNNING';` -> PASS；确认 `test-20260622_124533` 已变为 `FAILED`、`finished_at=2026-06-22 13:22:21`，测试环境 `RUNNING` 锁数量为 `0`，迁移 `RUNNING` 数量也为 `0`。同时再次只读核对 `.env` 与 `docker ps`，确认测试服当前仍是 `.env=v12`、backend=v12、frontend=v6` 的半切换态，下一步应立即回真实页面继续第三次 `deploy-test(v12)`。
- 2026-06-22 执行记录：继续接管真实页面会话 `frontend-release-full-flow-mainmerge`，只读核对页面快照、运行态 JSON `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a.json`、对应本机日志与测试服 `.env/docker ps/HTTP` 运行态；确认恢复 stale 锁后的第三次 `deploy-test(v12)` 已最终 `SUCCESS`，测试服 `/opt/intruoyi/runtime/.env` 与 `intruoyi-backend/intruoyi-frontend` 镜像都已切到 `release-20260621-page-full-flow-mainmerge-v12`，`48081/8081` 均返回 HTTP `200`。
- 2026-06-22 执行记录：同步回写主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，将里程碑 T4 更新为已完成，并把下一步推进为继续通过真实页面执行 `mark-tested(v12)`，之后再走 `prod -> backup`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，在“标记测试通过”表单保持原有值不变，点击“预览命令”确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v12 -TestConclusion 回归通过，允许上线正式服（v12） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，随后在真实弹窗点击“执行”，生成 operation `op-2026-06-22T063134275225600Z-e0e3d514-ea55-432e-a8bd-c14693a7a321`。
- 2026-06-22 执行记录：只读核对该 operation JSON 与本机 log 后确认本轮 `mark-tested(v12)` 已真实 `FAILED`，根因为 `publish-int-ruoyi.ps1` 解析 `BackendRepoRoot=D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro` 时路径不存在。随后按 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md` 先只读核对 `config/runtime-control.local.yaml`、`git worktree list` 与 clean release 目录，再以原分支 `codex/20260622-page-full-flow-mainmerge-release-clean`、原提交 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5` 最小补回缺失的后端 worktree 到原路径，`git status --short` 为空；下一步回真实页面重试同一 `mark-tested(v12)`。- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，在补回旧目录后再次点击“预览命令 -> 执行”重试 `mark-tested(v12)`，生成 operation `op-2026-06-22T064955263916Z-b55872da-49c6-4fae-a56a-1c3d6af01689`；随后只读核对 operation log，并直接执行 `Resolve-Path -LiteralPath 'D:/ProjectPackage/Int/IntRuoyi/worktrees/20260622-page-full-flow-mainmerge-release-clean/ruoyi-vue-pro'` 与宿主机目录检查，确认当前失败根因是本机 `runtime-control.local.yaml` 仍指向宿主机上并不存在的 `D:/ProjectPackage/Int/IntRuoyi/worktrees/...` 旧 worktree 根，而不是发布包或恢复点参数问题。
- 2026-06-22 执行记录：在宿主机真实 worktree 根 `D:\ProjectPackage\Int\IntRuoyiWorktrees\` 成对创建 clean release worktree：后端 `ruoyi-vue-pro-mainmerge-release-clean`（HEAD `d9606a65dfb4bfd4151970e3393e77be5f13a0c5`）与前端 `yudao-ui-admin-vue3-mainmerge-release-clean`（HEAD `37359a074cedcc0a341f17cb0abdd1a71f838731`），随后把 `D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 改指向这两条真实宿主机路径，并仅重启命中 `runtime-control-maintenance-2026.06-SNAPSHOT.jar` 的本地 Java 进程；健康检查 `http://127.0.0.1:48181/actuator/health` 已恢复 `UP`，下一步回真实页面继续第三次重试 `mark-tested(v12)`。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge snapshot`、`click e125`、`snapshot` -> PASS；真实页面确认 `mark-tested(v12)` 预览参数中的 `-BackendRepoRoot/-FrontendRepoRoot` 已改为 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- 2026-06-22 执行命令：`npx --yes --package @playwright/cli playwright-cli --session frontend-release-full-flow-mainmerge click e1359`、`snapshot`，随后只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3.json` 与对应 log -> PASS；确认真实页面第三次重试 `mark-tested(v12)` 已最终 `SUCCESS`，发布包 `release-20260621-page-full-flow-mainmerge-v12` 已被标记测试通过，下一步继续从页面执行 `上线正式服`。
- 2026-06-22 执行记录：继续接管正式服页面链路，先只读核对任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}` 与运行态 `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83.json`；确认真实页面 `上线正式服(v12)` 已由前序页面点击提交，当前只需轮询正式服收口结果。
- 2026-06-22 执行命令：普通沙箱读取正式服 operation 状态与日志尾部时触发 `windows sandbox: helper_unknown_error: apply deny-read ACLs`；随后以只读提权方式执行 `Start-Sleep -Seconds 10; Get-Content -Encoding utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83.json` 与对应 log `-Tail 120` -> PASS。
- 2026-06-22 执行记录：只读轮询确认真实页面 `上线正式服(v12)` operation `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83` 最终 `FAILED`；日志显示正式服在成功跨过多条 required SQL 后，于 `20260618_mes_edhr_release_transaction_lifecycle.sql` line `341` 抛出 `Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`，且正式环境发布锁已被脚本恢复性释放为 `LOCK_RELEASED`。
- 2026-06-22 执行记录：按“先记录再修复”门禁，先回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志，明确正式服首次真实暴露了新的业务 SQL 根因；下一步转入业务后端按严格 TDD 修复 `20260618_mes_edhr_release_transaction_lifecycle.sql`，修复后再用新的 `releaseTag` 从真实页面重走 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 用户请求：`继续`。
- 2026-06-22 执行记录：复核业务后端修复任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix\`、维护仓主任务与 clean release worktree 状态，确认正式服失败根因为 legacy `900263/900264` release transaction permission 漂移；随后在业务后端设置 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix` 执行 `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro commit -m "任务: 修复放行提交审批权限漂移"` -> PASS，提交 `314ebb2204`。
- 2026-06-22 执行命令：`git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean cherry-pick 314ebb2204` -> PASS；clean release backend worktree HEAD 更新为 `5c52f2ec42`，发布输入已发生变化。
- 2026-06-22 执行记录：回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，明确旧 `release-20260621-page-full-flow-mainmerge-v12` 结果已失效；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新标签（建议 `release-20260621-page-full-flow-mainmerge-v13`）从 `build-release` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行命令：复用真实页面会话 `frontend-release-full-flow-mainmerge` 切回“构建发布包”，填写原因 `主程序合并后重新验证页面发布全链路：release-transaction修复后重建发布包（v13）` 与 `releaseTag=release-20260621-page-full-flow-mainmerge-v13`，在预览弹窗确认 `publish-int-ruoyi.ps1 -Mode build-release` 的 `BackendRepoRoot/FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`，随后在真实弹窗点击“执行”，生成 operation `op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06`。
- 2026-06-22 执行记录：只读轮询 `runtime\\runtime-control\\op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06.json` 与对应 log，确认真实页面 `build-release(v13)` 最终 `FAILED`；clean backend Maven 打包已 `BUILD SUCCESS`，但随后在 clean frontend 打包前直接因 `D:\\ProjectPackage\\Int\\IntRuoyiWorktrees\\yudao-ui-admin-vue3-mainmerge-release-clean\\node_modules\\vite\\bin\\vite.js` 缺失而失败。已按门禁先回写维护仓主任务，下一步先恢复 clean frontend worktree 依赖并做本地 `pnpm build:test` 回归，再回真实页面以新标签重试 `build-release`。
- 2026-06-22 执行命令：在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 先只读确认 `node_modules` 与 `node_modules\\vite\\bin\\vite.js` 均不存在，随后执行 `pnpm install --frozen-lockfile` -> PASS，依赖现场恢复。
- 2026-06-22 执行命令：继续在同一 clean frontend worktree 执行 `pnpm build:test` -> PASS，输出 `Build successful. Please see dist-test directory`；已回写维护仓主任务，下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新标签（建议 `release-20260621-page-full-flow-mainmerge-v14`）重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 切回“构建发布包”，原因填写为“主程序合并后重新验证页面发布全链路：frontend依赖恢复后重建发布包（v14）”，发布标签填写为 `release-20260621-page-full-flow-mainmerge-v14`；页面预览已确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- 2026-06-22 执行记录：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9`；随后只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9.json` 与对应 log，确认 `build-release(v14)` 已最终 `SUCCESS`，并输出 `Release package built: release-20260621-page-full-flow-mainmerge-v14`、`NAS release path: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14`。
- 2026-06-22 执行记录：只读核对本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v14\manifest.json`，确认 backend/frontend source commit 分别为 `5c52f2ec4268212e71070d57a14f006202f337c8` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，两仓 `dirty=false`，且同目录下已存在 `release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v14.tar`。
- 2026-06-22 执行记录：同步回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，将里程碑 T3 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `deploy-test(v14)`，再继续 `mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，切换到“部署测试服”，原因填写为“主程序合并后重新验证页面发布全链路：部署测试服（v14）”，发布标签填写为 `release-20260621-page-full-flow-mainmerge-v14`；页面预览已确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment test -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- 2026-06-22 执行记录：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7`；随后只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7.json` 与对应 log，确认 `deploy-test(v14)` 已最终 `SUCCESS`，并输出 `Publish completed for test.`。
- 2026-06-22 执行记录：只读核对测试服 `172.30.30.58` 当前运行态，确认 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v14`，`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-mainmerge-v14`，`http://127.0.0.1:48081/actuator/health` 与 `http://127.0.0.1:8081/` 均返回 HTTP `200`。
- 2026-06-22 执行记录：同步回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，将里程碑 T4 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `mark-tested(v14)`，之后再继续 `prod -> backup`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，切换到“标记测试通过”，填写原因“主程序合并后重新验证页面发布全链路：标记测试通过（v14）”、验证结论“回归通过，允许上线正式服（v14）”，并从页面真实选择恢复集候选 `20260621-063218 · AVAILABLE`；预览弹窗已确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 -TestConclusion 回归通过，允许上线正式服（v14） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktrees。
- 2026-06-22 执行记录：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280`；随后只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280.json` 与对应 log，确认 `mark-tested(v14)` 已最终 `SUCCESS`，日志输出 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14`，并同步记录 `rollback-compatibility.json status=BLOCKED`。
- 2026-06-22 执行记录：同步回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}`，将里程碑 T5 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `上线正式服(v14)`，之后再继续 `上线备份服(v14)`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，切换到“上线正式服”，填写原因“主程序合并后重新验证页面发布全链路：上线正式服（v14）”；页面预览已确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-mainmerge-v14-preflight-release-dry-run.json ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。
- 2026-06-22 执行记录：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1`；随后只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1.json` 与对应 log，确认 `上线正式服(v14)` 已最终 `FAILED`。
- 2026-06-22 执行记录：正式服失败日志确认 `20260618_mes_edhr_release_transaction_lifecycle.sql` 在 line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`，且正式环境发布锁已被脚本收口为 `LOCK_RELEASED`。按“先记录再修复”门禁，已立即回写维护仓主任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志；下一步转入业务后端按严格 TDD 修复该正式 SQL 根因，修复后再以新的 `releaseTag` 从真实页面重走 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

## 2026-06-22 DCC 受控预览项目名称识别回写

- 用户需求：DCC 受控预览“识别基础信息”需要能识别并回写文件名，且文件名必须是 DCC 基础数据里的项目名称；本机没有 DCC 文件，可结合测试服务器真实数据处理。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。
- 执行记录：在隔离后端 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-release` 上继续推进，确认先前 `20260622_dcc_preview_codex_release_fix_2` 已解决 Codex CLI 120 秒超时，新的真实根因是样本 `dcc_controlled_file.id=2054545668044050095` 的源文件名只唯一命中项目名称 `PTCA球囊扩张导管`，旧实现只支持“文件名先识别项目编码”。
- 执行命令：新增并回归 `源文件名唯一项目名称直连识别`，通过 `mvn -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-release\pom.xml -pl yudao-module-dcc "-Dtest=DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_uniqueProjectNameInSourceFileNameSkipsCodexAndFileContentRead,DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_uniqueProjectCodeInSourceFileNameSkipsCodexAndFileContentRead,DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_sourceFileNameUsesLongestUniqueProjectCodeBeforeCodex" test`、`mvn -f ... -pl yudao-module-dcc -am "-Dtest=DccControlledFileProjectCodeRecognitionServiceTest,DccProjectCodeCodexCliClientImplTest" "-Dsurefire.failIfNoSpecifiedTests=false" test`、`python -X utf8 -m pytest ...test_publish_int_ruoyi_to_test_tooling.py -q`（87 passed）、`python -X utf8 -m pytest ...test_edhr_release_transaction_schema_sql.py -q`（4 passed）与 `python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...\\sql\\mysql`。
- 执行命令：构建并部署测试服 backend 发布包 `20260622_dcc_preview_codex_release_fix_3`，使用 `publish-int-ruoyi.ps1 -Mode build-release ... -ReleaseTag 20260622_dcc_preview_codex_release_fix_3 ... -DccProjectCodeCodexCliCommand /opt/intruoyi/runtime/tools/codex -DccProjectCodeCodexHome /opt/intruoyi/runtime/backend-codex-home` 与 `publish-int-ruoyi.ps1 -Mode deploy-release ... -ReleaseTag 20260622_dcc_preview_codex_release_fix_3 ...` -> PASS。
- 执行命令：使用测试租户真实接口验证，`POST http://172.30.30.58:48081/admin-api/system/auth/login` 携带 header `tenant-id: 122` 与 `aoteman/111111` 登录成功；随后 `POST http://172.30.30.58:48081/admin-api/dcc/controlled-files/2054545668044050095/recognize-project-code` 返回 `code=0`，`dccProjectCodeId=1`、`projectCode=PTCABC`、`projectName=PTCA球囊扩张导管`、`matchType=PROJECT_NAME`。
- 执行命令：通过 `ssh -o BatchMode=yes root@172.30.30.58` + `docker exec intruoyi-mysql mysql --default-character-set=utf8mb4 ...` 真实回读测试服数据库，确认 `dcc_controlled_file.id=2054545668044050095` 已写回 `file_name/title/product_name=PTCA球囊扩张导管`、`product_code=PTCABC`、`dcc_project_code_id=1`、`project_code_recognition_type=PROJECT_NAME`，并且其 `master_id=2054545668044045220` 对应的 `dcc_controlled_file_master.file_name` 也同步为 `PTCA球囊扩张导管`。
- 结论记录：测试服 DCC 受控预览后端识别链路已跑通，当前会优先用源文件名中的唯一项目编码或唯一项目名称命中 DCC 基础数据，并把正确项目名称同步回写到受控文件与主链文件名；本轮未触碰正式服。
- 2026-06-22 用户进一步确认：`D:\ProjectPackage\Int\IntRuoyi` 下项目后续都要按 `int_main` 方向融合。执行记录：只读核对后发现原始主工作区 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 虽处于 `int_main`，但存在大量未提交改动，且与本次 DCC 修复同文件重叠，不能直接把当前任务硬合进去。随后创建干净成对 worktree：后端 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean`、前端 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean`，分支同为 `codex/20260622-dcc-preview-int-main-clean`，基线分别来自 `int_main`。
- 执行命令：在新的后端 `int_main` 集成 worktree 上执行 `git cherry-pick c31b0fd21b26ceb2e7e11b7a454a828c9c9ed591` -> PASS，生成集成提交 `6588218e8f`；随后重跑 `mvn -f ...\\pom.xml -pl yudao-module-dcc "-Dtest=DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_uniqueProjectNameInSourceFileNameSkipsCodexAndFileContentRead,DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_uniqueProjectCodeInSourceFileNameSkipsCodexAndFileContentRead,DccControlledFileProjectCodeRecognitionServiceTest#recognizeProjectCode_sourceFileNameUsesLongestUniqueProjectCodeBeforeCodex" test`、`python -X utf8 -m pytest ...\\script\\tests\\test_publish_int_ruoyi_to_test_tooling.py -q`（87 passed）、`python -X utf8 -m pytest ...\\script\\tests\\test_edhr_release_transaction_schema_sql.py -q`（4 passed）-> PASS。
- 结论记录：这次 DCC 修复已经验证可在 `int_main` 基线上独立成立；当前未直接回灌到原始 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 的唯一原因，是那份 `int_main` 工作现场仍有未提交且与本任务重叠的脏改，需待主工作区整理后再做最终融合。
- 执行记录：继续按“真正收口到 `int_main`”推进时，先将原始后端主工作区 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 从 `int_main` 改挂到 holding 分支 `codex/20260622-ruoyi-vue-pro-int-main-hold`，不改任何未提交文件内容，只释放 `int_main` 分支占用；随后在干净后端集成 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean` 上执行 `git switch int_main` 与 `git merge --ff-only codex/20260622-dcc-preview-int-main-clean` -> PASS，实际把 `int_main` 快进到 `d88ea30af4`。
- 结论记录：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 这次 DCC 修复已经不是“准备并回 `int_main`”，而是已经实际进入真正的 `int_main` 分支；原始主工作区里的其他未提交内容继续保留在 `codex/20260622-ruoyi-vue-pro-int-main-hold` 上，后续再单独处理。
- 执行记录：为保持 `D:\ProjectPackage\Int\IntRuoyi` 下前后端 `int_main` 现场一致，继续将原始前端主工作区 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 从 `int_main` 改挂到 holding 分支 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，同样不改任何未提交文件内容；随后将干净前端 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean` 切回 `int_main` -> PASS。
- 结论记录：当前 `IntRuoyi` 下前后端两个原始主工作区都已不再占用 `int_main`；真正的 `int_main` 分别由干净 worktree `ruoyi-vue-pro-dcc-preview-int-main-clean` 与 `yudao-ui-admin-vue3-dcc-preview-int-main-clean` 持有，原始主工作区中的未提交现场则分别保留在各自 holding 分支上，便于后续单独整理。

## 2026-06-22 按阶段一次性融合进 int_main

- 用户需求：`D:\ProjectPackage\Int\IntRuoyi` 下的改动后续真正要收口到 `int_main`，并要求这次按阶段执行、一次性融合。
- 命中技能与经验：`supervised-complex-delivery`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：读取 `experience-index.md`、`worktree-memory.md`、`project-error-prevention.md` 与 `supervised-complex-delivery` 的 `artifact-contract.md`、`task-state-schema.md`、`review-gates.md`，把本轮定位为“holding 现场分组 + clean int_main 基线重放”的收口任务。
- 命令记录：复核维护仓 `doc/tasks`，确认最近已完成任务为 `20260622-task-tab-inventory`；同时发现 `20260621-frontend-release-full-flow-main-merge-rerun` 实际仍处于进行中，因此先将其按“用户优先级切换到 int_main 融合”显式改为 `BLOCKED`。
- 命令记录：盘点 backend 原始工作区 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 当前分支 `codex/20260622-ruoyi-vue-pro-int-main-hold` 与 `git diff --stat`，确认未提交改动混有三组：`DCC 审阅矩阵`、`已进入 int_main 的 DCC 文件名识别残留`、`MES 自动排产/preflight`。
- 命令记录：盘点 frontend 原始工作区 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 当前分支 `codex/20260622-yudao-ui-admin-vue3-int-main-hold` 与 `git diff --stat`，确认未提交改动主要为一组 `DCC 审阅矩阵页签`，另带 `.env.merged-e2e` 非主线文件。
- 命令记录：只读核对真正持有 `int_main` 的 clean worktree：backend `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean` 最新提交包含 `a66fea0db6` / `d88ea30af4` / `6588218e8f`；frontend `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean` 当前 `int_main` 头部为 `31618c856`。
- 结论记录：已新建维护总任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-int-main-one-shot-integration\`；下一步在 clean `int_main` 基线上逐组重放 DCC 审阅矩阵与 MES 改动，不能直接从 holding 脏工作区整仓合并。
- 命令记录：在成对集成 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\{ruoyi-vue-pro,yudao-ui-admin-vue3}-int-main-one-shot-integration` 重放 DCC 审阅矩阵组，并分别执行 backend `mvn --% -f ...\\pom.xml -pl yudao-module-dcc -Dtest=DccCategoryApprovalMatrixAdminServiceImplTest,DccCategoryPermissionAdminServiceImplTest,DccControlledFileWorkflowServiceImplTest,DccControlledFileQueryServiceTest -Dsurefire.failIfNoSpecifiedTests=false test` 与 frontend `pnpm install --frozen-lockfile`、4 个 `dcc-*.spec.js` 静态校验、`pnpm ts:check` -> PASS；随后提交 `90159e05ca`、`5cd728100`、`2cec13de0` 并把真正主线快进到这些结果。
- 命令记录：在 backend 集成 worktree 先用 `mvn --% -f ...\\pom.xml -pl yudao-module-mes -Dtest=MesProAutoSchedulePreflightGateContractTest test` 记录 RED 失败，再精确复制 7 个 `yudao-module-mes` 文件并执行 `mvn --% -f ...\\pom.xml -pl yudao-module-mes -Dtest=MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProScheduleOrderPreflightServiceTest -Dsurefire.failIfNoSpecifiedTests=false test` -> PASS（36 通过）；随后提交 `843851bf38`、`d9ba8afae5` 并将 backend 真正的 `int_main` 快进到 `d9ba8afae5`。
- 命令记录：回读原始工作区状态，确认 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 与 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 仍分别停在 `codex/20260622-ruoyi-vue-pro-int-main-hold` 与 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，holding 现场未被本轮主线收口覆盖。
- 命令记录：执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-one-shot-integration --mode preview` -> PASS；预览结果 `ready`，默认 `keep={task.md, execution-log.md}`，`delete={dev-plan.md, prd.md, request-analysis.md, task-state.json, test-plan.md, test-report.md}`，`blocked=<none>`。
- 结论记录：本轮“按阶段一次性融合进 int_main”目标已完成；真正主线收口以前后端 clean `int_main` worktree 为准，原始 holding 工作区继续保留供后续单独整理。
- 命令记录：继续执行 task-closeout-cleanup 时，backend 集成 worktree 预览再次因 `origin/HEAD -> master-jdk17` 被错误识别为主分支而阻塞。随后只在本机 backend Git 元数据执行 `git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/int_main`，把 cleanup 主线识别对齐到真正的 `int_main`，未改远端默认分支。
- 命令记录：backend 集成 worktree 先分别执行 `python -X utf8 ...task_closeout.py --task-id 20260622-dcc-review-matrix-tab --mode apply --worktree-closeout off` 与 `--task-id 20260622-mes-auto-schedule-preflight-gate --mode apply --worktree-closeout off`，删除两份 `backend-api-evidence.md`；随后设置 `TDD_TASK_DIR=...\\20260622-mes-auto-schedule-preflight-gate`，提交 cleanup `20e2e70305 任务: 清理DCC与MES收尾产物`，并在 backend 真正主线 worktree 执行 `git merge --ff-only codex/20260622-int-main-one-shot-integration` 与 `git worktree remove --force ...\\ruoyi-vue-pro-int-main-one-shot-integration` -> PASS。
- 命令记录：frontend 集成 worktree 执行 `python -X utf8 ...task_closeout.py --task-id 20260622-dcc-review-matrix-tab --mode apply`，已删除 `dcc-review-matrix-tab-real-evidence.json` 与 `frontend-feature-evidence.md`，并生成 cleanup 提交 `db289300f 任务: 清理任务收尾产物 20260622-dcc-review-matrix-tab`；该提交已快进进入 frontend 真正的 `int_main`。随后因目录内 `node_modules` 长路径残留导致 `git worktree remove --force` 目录清空失败，经确认该路径已不再是 Git worktree 后，使用 Node `fs.rmSync(path,{recursive:true,force:true,maxRetries:10,retryDelay:200})` 删除剩余普通目录 -> PASS。
- 结论记录：前后端本轮集成 worktree 已全部关闭，真正 `int_main` 分别停在 backend `20e2e70305`、frontend `db289300f`；当前只剩维护仓 `20260622-int-main-one-shot-integration` 任务目录自身按 keep/delete 计划执行 apply cleanup。
- 命令记录：维护仓执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-one-shot-integration --mode preview` 与 `--mode apply` -> PASS；已按默认规则保留 `task.md`、`execution-log.md`，并删除 `dev-plan.md`、`prd.md`、`request-analysis.md`、`task-state.json`、`test-plan.md`、`test-report.md`。
- 结论记录：这次“按阶段一次性融合进 int_main”已经从分组收口走到真正收尾结束，前后端主线结果、holding 现场保留与维护台账清理三件事都已闭环。

## 2026-06-22 恢复原始工作区并清理 int_main 临时承载

- 用户问题：`ruoyi-vue-pro-dcc-preview-int-main-clean`、`codex/20260622-ruoyi-vue-pro-int-main-hold`、`codex/20260622-yudao-ui-admin-vue3-int-main-hold` 分别是做什么的，融合进 `int_main` 后能不能删。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`，并按门禁先做 `experience-preflight`。
- 命令记录：复核后发现前端原始目录 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 当前只剩 `.env.merged-e2e` 未跟踪文件，而 backend 原始目录 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 仍有 11 个脏文件与 `doc/tasks/20260622-dcc-preview-file-name-recognition/` 本地任务文档。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 执行 `git switch --ignore-other-worktrees int_main` -> PASS，随后删除分支 `codex/20260622-yudao-ui-admin-vue3-int-main-hold`，再执行 `git worktree remove --force D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-int-main-clean` -> PASS。结果：原始前端目录现在直接承载 `int_main`，原有本地改动 `RouteUsePage.vue`、3 个 `tests/e2e/*` 文件与 `.env.merged-e2e` 继续保留，没有丢失。
- 命令记录：对 backend 原始目录的 11 个脏文件逐个与真正 `int_main` 内容做 SHA256 和 `git diff --ignore-cr-at-eol` 比对，确认其中 9 个仅剩行尾差异，但 `DccControlledFileProjectCodeRecognitionServiceImpl.java`、`DccControlledFileProjectCodeRecognitionServiceTest.java` 为真实语义差异；再与 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-release` 比对后，确认这两处代码及 `doc/tasks/20260622-dcc-preview-file-name-recognition/{task.md,execution-log.md}` 也不等于现有 release worktree。
- 命令记录：尝试在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 执行 `git switch --ignore-other-worktrees int_main` 时，Git 明确报错“当前 11 个本地改动和 `doc/tasks/20260622-dcc-preview-file-name-recognition/{task.md,execution-log.md}` 会被 int_main 覆盖”，因此 backend 原始目录不能安全切到 `int_main`，`codex/20260622-ruoyi-vue-pro-int-main-hold` 也不能删。
- 命令记录：由于 backend 原始目录未能接管真正主线，立即执行 `git worktree add D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean int_main` 恢复 backend clean `int_main` worktree，保持真正主线仍有稳定承载目录。
- 结论记录：当前可删并已删除的是 frontend holding 分支与 frontend clean int_main worktree；backend holding 分支当前必须保留，backend clean int_main worktree 也必须保留，否则会丢失“真实主线目录”与原始 backend 本地现场之间的隔离。

## 2026-06-22 恢复主程序页面发布全链路

- 用户请求：`继续`。
- 执行记录：恢复维护仓主任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\`，先只读核对 `v14` 正式服失败证据、clean release backend worktree 当前 HEAD 与业务任务 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix\` 的既有状态，确认需要继续在同一业务任务内补第二阶段根因。
- 执行记录：补读 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 后，只读对比正式服/测试服 `system_menu` 现场；确认正式库 `900266/900267/900268` 仍是 traveler 菜单，而测试库对应放行事务已是 `900353/900354/900355`。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 更新 `script\tests\test_edhr_release_transaction_schema_sql.py`，新增“放行事务必须使用独立号段且不得复用 traveler 号段”的 RED 契约；执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean\script\tests\test_edhr_release_transaction_schema_sql.py -q` -> FAIL，断言 `SELECT 900353, 'eDHR放行驳回'` 缺失。
- 执行命令：更新 `sql\mysql\20260618_mes_edhr_release_transaction_lifecycle.sql`，将 `eDHR放行驳回 / eDHR放行撤回 / eDHR放行事务事件查询` 从 `900266/900267/900268` 切换到 `900353/900354/900355`，并同步更新 menu merge / role_menu 合并逻辑；随后执行 `python -X utf8 -m pytest ...test_edhr_release_transaction_schema_sql.py -q`（5 passed）、`python -X utf8 -m pytest ...test_edhr_traveler_schema_sql.py -q`（4 passed）、`python -X utf8 -m pytest ...test_edhr_release_precheck_schema_sql.py -q`（6 passed）、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...\sql\mysql` 与 `python C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence ...bug-regression-evidence.md` -> PASS。
- 执行命令：`git -C D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean add doc/tasks/20260622-edhr-release-transaction-permission-rows-fix/bug-regression-evidence.md doc/tasks/20260622-edhr-release-transaction-permission-rows-fix/execution-log.md doc/tasks/20260622-edhr-release-transaction-permission-rows-fix/task.md script/tests/test_edhr_release_transaction_schema_sql.py sql/mysql/20260618_mes_edhr_release_transaction_lifecycle.sql` 后，首次 `git commit -m "任务: 修复放行事务菜单号段冲突"` 因未设置 `TDD_TASK_DIR` 被钩子阻断；随后设置 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix` 再执行 `git commit -m "任务: 修复放行事务菜单号段冲突"` -> PASS，提交 `49248d9f20`。
- 结论记录：backend clean 发布输入已从 `5c52f2ec42` 更新到 `49248d9f20`，frontend clean worktree 仍为 `37359a074`；旧 `release-20260621-page-full-flow-mainmerge-v14` 证据已失效，下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v15`）从页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
- 2026-06-22 执行记录：收到用户继续指令后，刷新本机运行控制台并确认旧 `v14` 正式服 operation 已为 `FAILED`，随后将页面切回“构建发布包”，更新原因为“主程序合并后重新验证页面发布全链路：release-transaction traveler号段修复后重建发布包（v15）”，发布标签更新为 `release-20260621-page-full-flow-mainmerge-v15`，预览弹窗再次核对 `-BackendRepoRoot/-FrontendRepoRoot` 仍指向 clean release worktrees。
- 2026-06-22 执行命令：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T121006967109700Z-6dc95b22-9d29-4a00-b432-9cdd4e34bc51`；随后轮询运行态 JSON 与日志，确认 `build-release(v15)` 已最终 `SUCCESS`，本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v15\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v15.tar`，且 manifest 已核对 backend commit=`49248d9f20db9e3100bc5f492c7027d4de065f32`、frontend commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`、两仓 `dirty=false`。
- 2026-06-22 用户请求：`继续`。
- 2026-06-22 执行记录：承接真实页面已提交的 `deploy-test(v15)`，补读 `playwright` 与 `ci-cd-environment-delivery` 技能、主任务 `task.md/execution-log.md/test-report.md/task-state.json` 以及当前 operation JSON/log，确认本轮必须先把 `deploy-test(v15)` 终态与只读运行态证据写回文档，再继续页面点击 `mark-tested(v15)`。
- 2026-06-22 执行命令：持续轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T124343427998700Z-ff404f87-2e5b-4ec1-9e04-cab7342d49a3.json` 与 `runtime\runtime-control\logs\op-2026-06-22T124343427998700Z-ff404f87-2e5b-4ec1-9e04-cab7342d49a3.log` -> PASS；确认 `deploy-test(v15)` 在测试服已真实跨过 `20260618_mes_edhr_release_transaction_lifecycle.sql` 应用、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 校验、测试服发布锁释放与远端临时文件清理，最终输出 `Publish completed for test.`。
- 2026-06-22 执行命令：只读核对测试服运行态，执行 `Invoke-WebRequest -UseBasicParsing -Uri http://172.30.30.58:48081/actuator/health -TimeoutSec 10`、`Invoke-WebRequest -UseBasicParsing -Uri http://172.30.30.58:8081/ -TimeoutSec 10` 与 `ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env; docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'"` -> PASS；确认测试服 `.env`、`intruoyi-backend`、`intruoyi-frontend` 均已切到 `release-20260621-page-full-flow-mainmerge-v15`，`48081/8081` 返回 HTTP `200`。
- 2026-06-22 执行记录：按“先记文档再继续页面”门禁，已同步回写维护仓主任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志，将里程碑 T4 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `mark-tested(v15)`，之后再继续 `prod -> backup`。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，切换到“标记测试通过”，将操作原因改为“主程序合并后重新验证页面发布全链路：标记测试通过（v15）”，验证结论改为“回归通过，允许上线正式服（v15）”，并从页面真实选择恢复集候选 `20260621-063218 · AVAILABLE`。
- 2026-06-22 执行记录：打开真实页面“命令预览”弹窗并只读核对参数，确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v15 -TestConclusion 回归通过，允许上线正式服（v15） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktrees。
- 2026-06-22 执行命令：在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-22T130722457390300Z-2411caa4-7048-451b-bbc4-a5448ee35343`；随后读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T130722457390300Z-2411caa4-7048-451b-bbc4-a5448ee35343.json` 与对应 log -> PASS，确认 `mark-tested(v15)` 已最终 `SUCCESS`，日志输出 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v15`，并同步记录 `rollback-compatibility.json status=BLOCKED`。
- 2026-06-22 执行记录：按“先记文档再继续页面”门禁，已同步回写维护仓主任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志，将里程碑 T5 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `上线正式服(v15)`，之后再继续 `上线备份服(v15)`。
- 2026-06-22 执行记录：尝试按 `development-plan-supervisor` 续跑当前任务时，执行 `python C:\Users\BJB110\.codex\skills\development-plan-delivery\scripts\init_or_resume_task.py --cwd D:\ProjectPackage\Int\IntRuoyiMaintance --task-dir D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun` 与 `render_plan_status.py`；结果确认该旧任务目录缺少 `development-plan.md` 且 `task-state.json` 不含 `current_phase`，因此不适用该 skill，继续按现有 `task.md/task-state.json` 续跑而不重建计划。
- 2026-06-22 执行记录：通过真实页面会话 `frontend-release-full-flow-mainmerge` 抓取 `snapshot`，确认当前动作已切到“上线正式服”，原因仍为“主程序合并后重新验证页面发布全链路：上线正式服（v15）”，发布标签为 `release-20260621-page-full-flow-mainmerge-v15`，生产确认文本为 `PROD`；操作记录显示新 operation `op-2026-06-22T131359664055200Z-033d12b4-2e7d-467d-8c3e-50f7d312ac4b` 已提交。
- 2026-06-22 执行命令：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T131359664055200Z-033d12b4-2e7d-467d-8c3e-50f7d312ac4b.json` 与对应 log -> PASS，确认 `promote-prod(v15)` 已最终 `SUCCESS`，日志输出 `Publish completed for production.`，并包含 `SHOWROOM_FILE_CONFIG_28_PROTECTED` 保护标记。
- 2026-06-22 执行命令：只读核对正式服运行态，执行 `ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.57 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env; echo __CONTAINERS__; docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'; echo __HEALTH__; curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' http://172.30.30.57:48081/actuator/health; curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' http://172.30.30.57:8081/"` -> PASS；确认正式服 `.env`、`intruoyi-backend`、`intruoyi-frontend` 均已切到 `release-20260621-page-full-flow-mainmerge-v15`，`48081/8081` 返回 HTTP `200`。
- 2026-06-22 执行命令：只读核对 showroom 受保护边界，先执行 `SELECT id,name,storage,master,config FROM infra_file_config WHERE id=28;`，再执行 `SELECT COUNT(*) FROM infra_file WHERE config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%';` 与 `SELECT COUNT(*) FROM infra_file WHERE config_id=28 AND path LIKE 'showroom/%' AND url LIKE 'http://172.30.30.57:9000/yudao/%';` -> PASS；确认 `infra_file_config.id=28` 仍为 `bucket=yudao`、`domain=http://172.30.30.57:9000/yudao`，且计数分别为 `0` 与 `1434`。
- 2026-06-22 执行记录：按“先记文档再继续页面”门禁，已同步回写维护仓主任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志，将里程碑 T6 更新为已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `上线备份服(v15)`，之后再继续任务收尾。
- 2026-06-22 执行记录：继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，先点击页面“刷新”确认 `promote-prod(v15)` 操作记录已显示 `SUCCESS`，再切换到“上线备份服”，将操作原因改为“主程序合并后重新验证页面发布全链路：上线备份服（v15）”。
- 2026-06-22 执行记录：打开真实页面“命令预览”弹窗并只读核对参数，确认执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-mainmerge-v15 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 clean release worktrees；随后在页面点击“执行”，生成 operation `op-2026-06-22T134349739402400Z-5f5507e8-cd79-4630-b9fb-2e2e6fc6d3b8`。
- 2026-06-22 执行命令：持续轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-22T134349739402400Z-5f5507e8-cd79-4630-b9fb-2e2e6fc6d3b8.json` 与对应 log -> PASS；确认 `promote-backup(v15)` 已最终 `SUCCESS`，日志输出 `Publish completed for backup.`，并包含 `Showroom file storage config 28 is protected and target-bound` 保护标记。
- 2026-06-22 执行命令：只读核对备份服运行态，执行 `ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.59 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env; echo __CONTAINERS__; docker ps --format '{{.Names}} {{.Image}}' | grep -E 'intruoyi-(backend|frontend)'; echo __HEALTH__; curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' http://172.30.30.59:48081/actuator/health; curl -s -o /dev/null -w '%{http_code} %{url_effective}\n' http://172.30.30.59:8081/"` -> PASS；确认备份服 `.env`、`intruoyi-backend`、`intruoyi-frontend` 均已切到 `release-20260621-page-full-flow-mainmerge-v15`，`48081/8081` 返回 HTTP `200`。
- 2026-06-22 执行命令：只读核对备份服 showroom 受保护边界，执行 `SELECT id,name,storage,master,config FROM infra_file_config WHERE id=28;`、`SELECT COUNT(*) FROM infra_file WHERE config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%';` 与 `SELECT COUNT(*) FROM infra_file WHERE config_id=28 AND path LIKE 'showroom/%' AND url LIKE 'http://172.30.30.59:9000/yudao/%';` -> PASS；确认 `infra_file_config.id=28` 仍为 `bucket=yudao`、`domain=http://172.30.30.59:9000/yudao`，且计数分别为 `0` 与 `1434`。
- 2026-06-22 执行记录：同步回写维护仓主任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-main-merge-rerun\{task.md,execution-log.md,test-report.md,task-state.json}` 与本日志，将里程碑 T7/T8 更新为已完成，并把任务总状态标记为 `completed`。
- 2026-06-22 执行命令：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260621-frontend-release-full-flow-main-merge-rerun --mode preview` -> PASS；预览结果 `status=ready`、`blocked=<none>`，默认保留 `task.md` 与 `execution-log.md`，其余任务附属文档列为可删除候选。本轮仅保留预览证据，不在当前回合执行 apply 删除。

## 2026-06-22 提交当前前后端代码

- 用户请求：`提交当前前后端的所有代码`
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`，按门禁先核对真实前后端仓库而不是维护仓根目录 Git。
- 执行记录：审计 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 与 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 当前状态，确认前端当前仅有未跟踪本地环境文件 `.env.merged-e2e`，没有可提交的前端业务代码；后端当前为 staged/unstaged 混合现场，包含 DCC 预览文件名识别、DCC 浏览权限矩阵切换、MES 排产预检等多组改动，必须按任务边界拆分验证后再提交。
- 执行记录：恢复提交任务后，后端按任务边界完成并提交 `229e73aadb 任务: 修复DCC预览文件名识别`、`04f9833379 任务: 收紧DCC浏览查阅矩阵权限`、`f87816f049 任务: 切换eDHR BPM站内信通知`、`8047435b62 任务: 新增eDHR演练预检`、`407259799e 任务: 增加eDHR演练预检门禁`；前端提交 `62e82ff58 任务: 补齐智能排产smoke的xlsx依赖`。
- 验证记录：后端 DCC/BPM/MES 定向测试与 backend API evidence 校验均 PASS；前端 `node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` PASS，真实 smoke 已越过 `xlsx` 依赖缺口但因缺少 `MES_SMOKE_BASE_URL` 按前置条件 fail fast。
- 结论记录：后端 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 工作区已干净；前端 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 仅剩未跟踪 `.env.merged-e2e` 本地环境文件，未纳入提交。

## 2026-06-22 保留 DCC 改动并把 backend 收口到 int_main 只留一个 worktree

- 用户请求：保留 DCC 改动，同时把后端内容都融合进 `int_main`，并只保留一个 backend worktree。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`；收尾前再读取 `C:\Users\BJB110\.codex\skills\task-closeout-cleanup\SKILL.md`，按门禁先做 preview 再决定清理。
- 执行记录：只读审计 backend clean `int_main` worktree、backend 原始目录与 `git worktree list`；确认 `39b2d15f6b 任务: 修正eDHR BPM通知迁移依赖` 需先在 clean `int_main` 上正式提交，随后把 `8047435b62 任务: 新增eDHR演练预检` 并入主线。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean` 运行 `python -X utf8 -m pytest ...test_edhr_bpm_notify_to_inbox_sql.py -q`（3 passed）、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...\\sql\\mysql`（`status=passed`, `migrationCount=187`），再设置 `TDD_TASK_DIR` 提交 `39b2d15f6b 任务: 修正eDHR BPM通知迁移依赖`。
- 执行命令：继续在 clean `int_main` worktree 执行 `git cherry-pick 8047435b62` -> PASS，得到 `9a96ca4f68 任务: 新增eDHR演练预检`；随后运行 `mvn --% -f ...\\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileQueryServiceTest,DccControlledFileReviewMatrixAccessServiceTest,DccControlledFilePreviewProtectionTest,DccOnlyOfficeControlledPreviewTest -Dsurefire.failIfNoSpecifiedTests=false test`（65 通过）、`mvn --% -f ...\\pom.xml -pl yudao-module-mes -Dtest=MesProScheduleOrderPreflightServiceTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProEdhrRehearsalReadinessServiceTest,MesProEdhrBatchExecutionControllerTest -Dsurefire.failIfNoSpecifiedTests=false test`（46 通过）、`mvn --% -f ...\\pom.xml -pl yudao-module-bpm -Dtest=BpmMessageServiceImplTest -Dsurefire.failIfNoSpecifiedTests=false test`（9 通过）。
- 执行记录：将原始 backend 目录 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 切回 `int_main` 并移除 `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-release`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-preview-int-main-clean` 后，发现最后一组尾部现场 `20260622-edhr-readiness-template-bpm-hardening` 已有代码和任务档但尚未完全收口。
- 执行命令：在原始 backend 目录先用 `mvn -f ...\\pom.xml -pl yudao-module-mes \"-Dtest=MesProEdhrRehearsalReadinessServiceTest\" test` 暴露真实失败，再用 `mvn --% -f ...\\pom.xml -pl yudao-module-mes clean -Dtest=MesProEdhrRehearsalReadinessServiceTest,MesProEdhrBatchExecutionControllerTest -Dsurefire.failIfNoSpecifiedTests=false test` 强制重编译，确认模板/BPM 门禁硬化测试 9 项通过；随后跑 `mvn --% -f ...\\pom.xml -pl yudao-module-mes -Dtest=MesProScheduleOrderPreflightServiceTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest,MesProAutoScheduleServiceImplTest,MesProEdhrRehearsalReadinessServiceTest,MesProEdhrBatchExecutionControllerTest -Dsurefire.failIfNoSpecifiedTests=false test`（48 通过）与 `python C:\\Users\\BJB110\\.codex\\skills\\backend-api-delivery\\scripts\\validate_backend_api.py --evidence ...\\backend-api-evidence.md` -> PASS。
- 结论记录：backend `int_main` 最终包含 `39b2d15f6b`、`9a96ca4f68`、`2b538ad5dd`、`fffbba0c89` 等收口提交；当前 `git worktree list` 仅剩 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro [int_main]` 这一份 backend worktree，`codex/20260622-ruoyi-vue-pro-int-main-hold` 只保留为 branch 指针。
- 执行命令：在维护仓执行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260622-int-main-workspace-normalization --mode preview` -> PASS，结果 `status=ready`、`blocked=<none>`，默认保留 `task.md` 与 `execution-log.md`，并将 `task-state.json` 标记为可删除。

## 2026-06-23 DCC 识别后续实现

- 用户请求：`继续`
- 执行记录：先在 backend 仓只读核对上一任务文档，发现 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-int-main-workspace-normalization\task.md` 仍为 `IN_PROGRESS`；随后补齐完成态描述，确保满足“上一任务先收口再开新任务”的仓库门禁。
- 执行记录：在主 backend 工作区新增短编码误命中回归测试后，首次执行 `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test` 时，被当前主工作区其他未收口 DCC 改动的编译错误阻断；为避免覆盖用户现场，改按 `worktree-memory` 规则创建 clean backend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-short-code-recognition-hardening`，后端分支 `codex/20260623-dcc-short-code-recognition-hardening`，并在 frontend 仓补同名分支占位。
- 执行命令：在 clean backend worktree 建立任务目录 `doc/tasks/20260623-dcc-short-code-recognition-hardening/`，新增 3 个 RED 用例覆盖：
  - 短编码 `IN` 嵌入普通长 token `INT-培训记录.pdf`
  - 两位短编码 `EC` 独立片段 `EC-现场记录.pdf`
  - 长编码 `CODE-A` 嵌入更长 ASCII token `XCODE-AX审批单.pdf`
- 执行命令：运行 `mvn --% -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-short-code-recognition-hardening\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test` -> FAIL，3 个新增回归用例均证明当前实现没有调用 `fileService.getFileContent(...)` 和 `codexCliClient.recognizeProjectCode(...)`。
- 执行命令：在 clean backend worktree 更新 `DccControlledFileProjectCodeRecognitionServiceImpl.java`，把文件名直连收紧为“高置信度 + 完整 ASCII token 边界”规则：短编码有效字符长度不足 4 时不再文件名直连，其余编码需满足完整边界后才允许跳过内容识别。
- 执行命令：回归 `mvn --% -f D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-short-code-recognition-hardening\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test` -> PASS（16/16）；继续执行 `mvn --% -f ... -Dtest=DccControlledFileProjectCodeRecognitionServiceTest,DccProjectCodeCodexCliClientImplTest -Dsurefire.failIfNoSpecifiedTests=false test` -> PASS（20/20）；再执行 `python C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence ...\bug-regression-evidence.md` -> PASS。
- 执行命令：在 clean backend worktree 以 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-dcc-short-code-recognition-hardening\doc\tasks\20260623-dcc-short-code-recognition-hardening` 提交两笔：
  - `baea65092e 任务: 收紧DCC短编码文件名识别`
  - `2bc28d3941 任务: 补充DCC短编码回归证据`
- 结论记录：backend 第一个后续任务已完成，短编码和嵌入长 ASCII token 的误命中不再直接跳过内容识别；最终测试服联动验证留给后续“内容识别运行时跑通”任务继续。
- 执行记录：随后按维护仓本地发布链路修复继续第二个后续任务；因主维护仓工作区同样存在大量无关脏现场，按 `worktree-memory` 规则创建 clean maintenance worktree `D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable`，分支 `codex/20260623-test-server-dcc-content-recognition-enable`。
- 执行命令：在 clean maintenance worktree 建立任务目录 `doc/tasks/20260623-test-server-dcc-content-recognition-enable/` 与合同测试 `scripts/tests/test_publish_dcc_codex_runtime_contract.py`；首次执行 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> FAIL，明确暴露维护仓 `publish-int-ruoyi.ps1` 和 `ops/deploy/int-ruoyi-test/docker-compose.yml` 缺少 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND`、`DCC_PROJECT_CODE_CODEX_HOME`、`CODEX_HOME`、识别命令参数与挂载。
- 执行命令：更新 clean maintenance worktree 中的 `ops/deploy/publish-int-ruoyi.ps1` 与 `ops/deploy/int-ruoyi-test/docker-compose.yml`，补齐：
  - 脚本参数 `DccProjectCodeCodexCliCommand`、`DccProjectCodeCodexHome`
  - effective 默认值 `/opt/intruoyi/runtime/tools/codex`、`/opt/intruoyi/runtime/backend-codex-home`
  - `.env` 输出 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND`、`DCC_PROJECT_CODE_CODEX_HOME`
  - compose 环境变量 `DCC_PROJECT_CODE_CODEX_HOME`、`CODEX_HOME`
  - JVM 参数 `--yudao.dcc.project-code-recognition.codex-cli-command=${DCC_PROJECT_CODE_CODEX_CLI_COMMAND}`
  - 挂载 `/opt/intruoyi/runtime/tools/codex` 与 `/opt/intruoyi/runtime/backend-codex-home`
- 执行命令：回归 `python -X utf8 -m pytest ...test_publish_dcc_codex_runtime_contract.py -q` -> PASS（2 passed）；继续执行 `python -X utf8 C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\doc\tasks\20260623-test-server-dcc-content-recognition-enable\ci-cd-evidence.md` -> PASS。
- 执行命令：在 clean maintenance worktree 以 `TDD_TASK_DIR=D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\doc\tasks\20260623-test-server-dcc-content-recognition-enable` 提交 `94d0837 任务: 补齐DCC Codex发布运行时合同`。
- 结论记录：第二个后续任务的“本地合同修复”阶段已完成并提交；当前仍缺测试服写入、容器重建和真实内容识别联调的当前授权，因此不能把本地合同通过直接等同为“测试服内容识别已跑通”。

## 2026-06-22 删除剩余两个前端 worktree

- 用户请求：删除 `yudao-ui-admin-vue3-dcc-preview-release` 与 `yudao-ui-admin-vue3-mainmerge-release-clean`，让前后端只保留一个 `int_main` worktree。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`；同时读取 `C:\Users\BJB110\.codex\skills\task-closeout-cleanup\SKILL.md` 与 `references\closeout-rules.md`。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-frontend-worktree-final-cleanup\`，记录 `experience-preflight`、目标 worktree、清理边界和验证命令。
- 执行命令：在 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 执行 `git worktree remove D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-release` -> PASS；执行 `git worktree remove D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 后 Git 登记已移除，但目录因 `node_modules` 长路径残留未自动删除。
- 执行命令：校验残留路径确认为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 后，使用空目录镜像方式清理残留目录，结果 `residual directory removed`。
- 结论记录：前端 `git worktree list` 仅剩 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 [int_main]`；后端 `git worktree list` 仅剩 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro [int_main]`。前端主目录和后端主目录仍有新的本地现场，本任务未处理。

## 2026-06-22 测试服 DCC Codex 文件识别能力只读核验

- 用户请求：判断当前测试服务器是否可以实现用 Codex 识别文件的产品名称和产品编码，以及通过产品编码对应产品名称。
- 命中经验：读取维护仓 `AGENTS.md`、`docs/experience-index.md`、IntRuoyi `docs/server-access.md` 与 `docs/login-access.md`；本任务限定为测试服只读核验，不发布、不重启、不写库、不触发写入接口。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\`，记录 BDD 场景、门禁、里程碑和验证报告。
- 执行命令：本机只读检索 DCC 识别代码，确认存在 `DccControlledFileProjectCodeRecognitionServiceImpl`、`DccProjectCodeCodexCliClientImpl`、`DccProjectCodeRecognitionProperties`、`DccControlledFileController` 和对应测试；识别逻辑为文件名唯一最长编码优先，失败后读取源文件内容调用 Codex CLI。
- 执行命令：只读检查测试服健康、容器与镜像，确认 `172.30.30.58:48081/actuator/health` 为 `UP`，主后端镜像为 `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v15`。
- 执行命令：只读检查测试服后端镜像包，确认 `/yudao-server/app.jar` 嵌套 DCC jar 包含识别服务、Codex CLI 客户端、配置类和 `recognize-project-code` 控制器入口。
- 执行命令：只读查询测试服 MySQL，确认 `dcc_project_code` 与受控文件识别字段存在；启用项目编码基础数据 `248` 条，编码和名称完整 `242` 条，带源文件受控文件 `34667` 条。
- 执行命令：只读采样文件名编码命中情况，测试租户按“最长且唯一项目编码”规则可直接命中 `923` 条，但样本暴露短编码如 `IN` 容易误命中文件名。
- 结论记录：测试服可支持“文件名唯一编码 -> 基础数据项目名称”的直接识别路径；但后端容器内未发现 `codex` / `codex.cmd`，compose 未配置 Linux 识别命令覆盖，代码默认 `cmd.exe /c codex.cmd` 不适配 Linux 容器，因此内容级 Codex 识别当前不能视为已跑通。

## 2026-06-23 DCC Codex 识别后续任务包化

- 用户请求：`先1后2`
- 需求拆解：
  - `1`：先把“短编码如 IN/OC/EC 容易误命中文件名”的风险整理成明确修复方案。
  - `2`：再补一个“测试服内容识别跑通改造”的正式任务文档。
- 执行命令：只读定位并核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\{task.md,execution-log.md,verification-report.md}`，确认上一核验任务状态为 `COMPLETED`，其验证结论为 `BLOCKED_FOR_FULL_CODEX_CONTENT_RECOGNITION`。
- 执行命令：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，按命中门禁拆分后续任务范围。
- 执行命令：只读核对后端识别代码与测试 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-dcc\src\main\java\cn\iocoder\yudao\module\dcc\service\file\DccControlledFileProjectCodeRecognitionServiceImpl.java`、`...DccProjectCodeCodexCliClientImpl.java`、`...DccProjectCodeRecognitionProperties.java`、`...DccControlledFileProjectCodeRecognitionServiceTest.java`、`...DccProjectCodeCodexCliClientImplTest.java`；确认当前文件名直连使用 `containsIgnoreCase` + 最长唯一编码规则，存在短编码误命中风险。
- 执行命令：对比业务后端仓与维护仓发布链路：
  - 业务后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\deploy\int-ruoyi-test\docker-compose.yml` 与 `publish-int-ruoyi.ps1` 已包含 `DCC_PROJECT_CODE_CODEX_CLI_COMMAND`、`DCC_PROJECT_CODE_CODEX_HOME`、`CODEX_HOME`、`/opt/intruoyi/runtime/tools/codex`、`/opt/intruoyi/runtime/backend-codex-home`。
  - 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\int-ruoyi-test\docker-compose.yml` 当前缺少同等 DCC Codex 运行时合同，是测试服内容识别未跑通的关键候选根因。
- 执行命令：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-dcc-short-code-recognition-hardening-plan\` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\`；随后对两个空目录执行 `python -X utf8 C:\Users\BJB110\.codex\skills\roadmap-node-dev-plan\scripts\validate_node_dev_plan.py --task-dir <task-dir>`，两次都按预期返回 `ERROR: Missing required file: task.md`。
- 执行记录：补齐两个任务的 `task.md`、`prd.md`、`development-plan.md`、`test-plan.md`、`task-state.json` 与 `execution-log.md`，分别固化：
  - 短编码风险硬化建议：边界感知匹配 + 低置信度短编码不再文件名直连。
  - 测试服内容识别跑通主线：修复维护仓发布链路缺少 DCC Codex 运行时合同的问题，再重建测试服 backend 并做真实内容识别验收。
- 执行命令：分别对 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-dcc-short-code-recognition-hardening-plan` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan` 再次执行 `python -X utf8 C:\Users\BJB110\.codex\skills\roadmap-node-dev-plan\scripts\validate_node_dev_plan.py --task-dir <task-dir>` -> PASS，两个任务包结构均校验通过。

## 2026-06-23 整理集团与璞润时间分配领导文档

- 用户需求：将“集团任务与子公司任务时间安排”和“集团内部项目阶段性投入比例”整理成一份可以直接交付给领导的正式文档。
- 命中技能：`C:\Users\BJB110\.codex\skills\doc\SKILL.md`。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务为本机文档整理，不涉及服务器、发布或真实 E2E。
- 执行记录：按仓库规则先检查上一任务，发现 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\task.md` 与 `...20260623-dcc-short-code-recognition-hardening-plan\task.md` 仍未完成，已在两个任务文档和执行日志中显式标记为 `BLOCKED`，原因是当前线程切换为领导文档交付。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-leader-time-allocation-document\`，并先写入 `task.md`、`execution-log.md`；同时创建输出目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\` 与预览目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\tmp\docs\20260623-leader-time-allocation-document\`。
- 执行命令：读取 `C:\Users\BJB110\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` 环境并验证 `python-docx`、`pdf2image` 可用；确认本机可通过 Word COM 导出 PDF，`pypdfium2` 可渲染预览页。
- 执行记录：生成最终源稿 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.md`，内容包含工作日/周末排班、集团阶段性项目占比、每周工时折算和特殊情况说明。
- 执行命令：运行内联 Python 脚本基于 `python-docx` 生成 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\group-subsidiary-time-allocation-20260623.docx`，并通过 Word COM 导出 `D:\ProjectPackage\Int\IntRuoyiMaintance\tmp\docs\20260623-leader-time-allocation-document\group-subsidiary-time-allocation-20260623.pdf`。
- 执行命令：使用 `pypdfium2` 渲染 PDF 为 `page-1.png`、`page-2.png`，人工核对标题、表格、分页和中文显示正常。
- 执行命令：先运行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260623-leader-time-allocation-document --mode preview` -> PASS，确认仅计划删除 `D:\ProjectPackage\Int\IntRuoyiMaintance\tmp\docs\20260623-leader-time-allocation-document\`；随后执行同命令 `--mode apply` -> PASS，已删除该临时预览目录并保留正式交付物。
- 结论记录：已交付可直接转发给领导的 Markdown 与 DOCX 文档；当前阶段对“5月15日至20周年期间”按用户语义闭合整理为“智能排产 10%、批记录 EDHR 10%”，如后续口径调整可在现有源稿上快速改版。

## 2026-06-23 整理四大业务功能模块 Excel 附录

- 用户需求：附录一个 Excel 工作簿，把当前展厅、eDHR、DCC、智能排产的功能内容分别整理到独立 sheet 中，并要求“不要加函数名、模块名这种针对程序员的描述，要所有人都能看懂的”。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务为本机盘点与 Excel 交付，不涉及服务器、发布或真实 E2E。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-functional-module-excel-appendix\`，先写入 `task.md`、`execution-log.md`，并在 `output/doc/` 预留正式交付路径。
- 执行命令：定向盘点 `D:\ProjectPackage\Website`、`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`、`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 中与展厅、eDHR、DCC、智能排产直接相关的视图目录、API 目录和后台控制器，确认当前能力边界。
- 执行记录：根据用户追加要求，将交付口径改为全业务语言表达，Excel 内统一使用 `一级工作 / 二级工作 / 具体内容 / 主要使用场景 / 补充说明`，不直接出现函数名、接口名、控制器名或程序员式模块名。
- 执行命令：使用 `openpyxl 3.1.5` 生成 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx`，包含 `展厅`、`eDHR`、`DCC`、`智能排产` 四个 sheet。
- 执行命令：复核 workbook 结构，确认 `sheetnames=['展厅','eDHR','DCC','智能排产']`，行列规模分别为 `展厅(22,6)`、`eDHR(27,6)`、`DCC(24,6)`、`智能排产(22,6)`。
- 执行命令：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260623-functional-module-excel-appendix --mode preview` -> PASS，仅计划删除 `tmp/docs/20260623-functional-module-excel-appendix/`；随后执行同命令 `--mode apply` -> PASS，已删除该临时目录。
- 结论记录：已生成一份适合直接附给领导的 Excel 附录，四个业务分别独立成 sheet，内容均按非技术人员可读方式整理。

## 2026-06-23 为功能模块 Excel 追加璞润 Sheet

- 用户需求：在现有功能模块 Excel 中增加 `璞润` sheet，内容基于 `D:\Vein` 和 `D:\ocr3` 今年范围内的提交总结，并继续保持和其他 sheet 一样的非技术表达方式。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务仅做本机 Git 提交盘点与 Excel 更新。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-functional-module-excel-purun-sheet\`，写入 `task.md`、`execution-log.md`，并确认上一任务 `20260623-functional-module-excel-appendix` 已完成。
- 执行命令：只读获取 `D:\Vein` 与 `D:\ocr3` 在 `2026-01-01` 至 `2026-06-23` 期间的提交主题，按业务语言归并为治疗流程优化、图像与判定、算法与连接、机械臂与设备、水路与压力、界面与交互、报告与记录、诊断与发布等工作条目。
- 执行记录：用户明确要求“不要加函数名、模块名这种针对程序员的描述，要所有人都能看懂的”，因此 `璞润` sheet 只保留业务工作语言，不直接写函数名、接口名、控制器名或提交哈希。
- 执行命令：尝试直接写回 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx` 时，`openpyxl` 返回 `PermissionError`；随后生成中间文件 `functional-module-appendix-20260623.tmp.xlsx`，并复制出可用替代交付文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-purun.xlsx`。
- 执行命令：复核替代文件，确认 workbook sheetnames 为 `展厅 / eDHR / DCC / 智能排产 / 璞润`，其中 `璞润` sheet 为 `20` 行 `6` 列。
- 执行命令：删除中间文件 `functional-module-appendix-20260623.tmp.xlsx`，并运行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260623-functional-module-excel-purun-sheet --mode preview` -> PASS；预览提示的删除候选已提前手动清理。
- 阻塞记录：原始文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx` 当前被其他进程占用，暂时不能原地覆盖；如需回写原路径，需要先关闭占用该文件的程序。
- 结论记录：当前已生成一份可直接使用的替代交付文件 `functional-module-appendix-20260623-purun.xlsx`，内容已补齐 `璞润` sheet；待原始文件释放锁定后，可再覆盖回原文件名。

## 2026-06-23 补充 QMS 文控重点与瑛泰系统 Sheet

- 用户需求：继续补充 Excel，要求“QMS 里面与浏览功能、浏览权限功能之外的功能标灰色，浏览功能和浏览权限功能细化”；同时补充 QMS 里的 `NAS 管理`、`从 NAS 平移数据到文控中心`，并额外增加 `瑛泰系统` sheet，整理运行控制台里的内容。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务仅做本机盘点与 Excel 更新。
- 执行记录：识别到原始文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623.xlsx` 仍存在锁文件 `~$functional-module-appendix-20260623.xlsx`，说明原文件持续被其他进程占用；因此本轮继续以替代交付文件方式产出，不直接覆盖原文件名。
- 执行命令：定向检索 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src\views\infra\runtime-control\index.vue` 与相关组件，提取运行控制台里的构建发布、测试部署、正式上线、备份恢复、状态查看、探针与风险、事故闭环等内容；同时检索 `DCC` 受控浏览、访问规则、权限预览、OnlyOffice 只读预览、NAS 权限快照、NAS 主体映射和 NAS 平移到文控中心相关证据。
- 执行记录：按用户要求把 `DCC` sheet 改成“重点突出浏览功能与浏览权限功能”的样式，浏览相关与权限相关条目细化展开，其余 QMS 文控条目标为灰色；同时把 `NAS 管理` 和 `NAS 平移到文控中心` 补充到 QMS 文控范围内。
- 执行命令：基于 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-purun.xlsx` 生成最新替代交付文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-qms-yingtai.xlsx`。
- 执行命令：复核最新替代文件，确认 workbook sheetnames 为 `展厅 / eDHR / DCC / 智能排产 / 璞润 / 瑛泰系统`，其中 `DCC` 为 `17` 行 `6` 列，`瑛泰系统` 为 `17` 行 `6` 列；`DCC` 中第 `12-17` 行为灰色。
- 结论记录：当前已生成一份最新可用替代交付文件 `functional-module-appendix-20260623-qms-yingtai.xlsx`，已补齐 QMS 文控重点样式和 `瑛泰系统` sheet；若后续关闭原始 Excel，可再覆盖回原文件名。

## 2026-06-23 整理后续工作内容汇报表述

- 用户需求：将“展厅、QMS、eDHR、智能排产、瑛泰系统、璞润”的后续工作内容整理成更适合向领导汇报的正式表述，并优化“后续工作怎么加合适”的表达方式。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务仅做本机文字整理，不涉及代码、服务器或真实 E2E。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-followup-work-content-wording\`，写入 `task.md`、`execution-log.md`，并确认上一任务 `20260623-functional-module-excel-qms-yingtai-sheets` 已完成。
- 执行记录：将原始较口语化内容统一整理为“当前进展 + 后续工作 + 依赖事项”风格，补齐展厅、QMS、eDHR、智能排产、瑛泰系统、璞润六个模块的正式汇报版口径。
- 执行命令：生成交付文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\followup-work-content-20260623.md`。
- 结论记录：已形成一份可直接用于领导汇报的后续工作内容文字稿；如需进一步增强管理视角，可在此基础上继续增加“负责人、时间节点、风险依赖”三列信息。

## 2026-06-23 将后续工作内容整合进现有 Excel

- 用户需求：希望把刚整理好的“后续工作内容”整合进刚才生成的 Excel 或 Word 中，由 Agent 选择更合适的形式。
- 处理判断：选择整合进现有 Excel，更适合与前面各模块 sheet 放在同一份工作簿内统一查看。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 后命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务仅做本机 Excel 更新。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-integrate-followup-sheet\`，写入 `task.md`、`execution-log.md`，并确认上一任务 `20260623-followup-work-content-wording` 已完成。
- 执行命令：直接更新 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-qms-yingtai.xlsx`，新增 `后续工作` sheet，按与现有 sheet 一致的 `序号 / 一级工作 / 二级工作 / 具体内容 / 主要使用场景 / 补充说明` 六列表头整理展厅、QMS、eDHR、智能排产、瑛泰系统、璞润的后续工作安排。
- 执行命令：复核更新后的 workbook，确认 sheetnames 为 `展厅 / eDHR / DCC / 智能排产 / 璞润 / 瑛泰系统 / 后续工作`，其中 `后续工作` 为 `12` 行 `6` 列。
- 执行命令：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260623-integrate-followup-sheet --mode preview` -> PASS；随后执行同命令 `--mode apply` -> PASS，当前任务无删除项。
- 结论记录：后续工作内容已成功整合进现有 Excel 工作簿，当前使用的最新文件仍为 `D:\ProjectPackage\Int\IntRuoyiMaintance\output\doc\functional-module-appendix-20260623-qms-yingtai.xlsx`。

## 2026-06-23 只发布随机 ERP 建单改动到测试服

- 用户需求：`把这个改动发布到测试服务器,只发布这个改动就可以,不然太慢了`
- 计划边界：只允许通过维护控制台真实页面执行 `build-release` 与 `deploy-test`；目标环境仅测试服 `172.30.30.58`；发布范围固定 `code-only`；禁止触发 `mark-tested`、正式服、备份服、备份、恢复、回滚或数据同步动作。
- 命令记录：已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`；运行控制台 `http://127.0.0.1:48181/` 返回 `200`。
- 命令记录：只读确认测试服当前 `.env` 为 `IMAGE_TAG=20260623_dcc_content_recognition_gateway_timeout_fix_1`；本地缓存发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\20260623_dcc_content_recognition_gateway_timeout_fix_1\manifest.json` 显示当前测试服基线为 backend `23c596d1e2ba97ef06b4854b53e80b0e88ec25ed`、frontend `4ed836cf016975fa6cca74d99b152b9b5ee3891c`。
- 命令记录：为保证“只发本次改动”，已创建 clean release worktree：
  - backend：`D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean`
  - frontend：`D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`
  - 两仓分支同为 `codex/20260623-test-randomized-erp-order-release`
- 命令记录：backend release worktree 已仅重放本次代码改动并提交 `aa13420c67513224bebe114d090f0cfffb8388ab`；`mvn -pl yudao-module-mes clean -Dtest=MesKingdeeProductionOrderCreateServiceImplTest test` PASS。
- 命令记录：frontend release worktree 已仅重放本次代码改动并提交 `e301a67af7acca887c60d1625d34b87d17409e9f`；`node tests/e2e/workorder-create-erp-order-static.spec.js` PASS；`pnpm ts:check` PASS。
- 阻塞记录：frontend release worktree 在 `pnpm install --frozen-lockfile` 时暴露坏锁文件：`Broken lockfile: no entry for 'adler-32@1.3.1' in pnpm-lock.yaml`。继续执行 `pnpm install --no-frozen-lockfile` 后虽补齐 `node_modules`，但 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean\pnpm-lock.yaml` 产生实际 diff（`1 file changed, 166 insertions(+), 131 deletions(-)`）。在用户明确批准是否允许把这 1 个锁文件修复一并带入测试服发布前，页面 `build-release` 与 `deploy-test` 均不得继续。
- 用户确认：允许把这 1 个前端锁文件修复一并带入本次测试服发布。
- 命令记录：页面 `build-release` 预览 PASS，命令指向 `release-20260623-random-erp-test-v1`，并确认 `-BackendRepoRoot/-FrontendRepoRoot` 为本次 clean release worktree。
- 命令记录：页面真实提交 `build-release`，operation `op-2026-06-23T072156013940200Z-4e4291e1-3c74-4f26-8cda-8c116760c505` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260623-random-erp-test-v1\` 已生成 `manifest.json`、`release-manifest.json`、镜像 tar、`runtime-env/`、`resources/` 与 `required-sql/`。
- 命令记录：manifest 核对 PASS，backend commit=`aa13420c67513224bebe114d090f0cfffb8388ab`，frontend commit=`e301a67af7acca887c60d1625d34b87d17409e9f`，`publishScope=code-only`；frontend `dirty=true` 仅来自用户已批准带入的 `pnpm-lock.yaml` 修复。
- 命令记录：页面 `deploy-test` 预览 PASS，命令确认 `-Mode deploy-release -Environment test -ReleaseTag release-20260623-random-erp-test-v1 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime`，且 `-BackendRepoRoot/-FrontendRepoRoot` 仍为本次 clean release worktree。
- 命令记录：页面真实提交 `deploy-test`，operation `op-2026-06-23T074133159825800Z-f54c26d2-d986-42bb-8c53-485f509c8c06` 最终 `SUCCESS`。
- 命令记录：只读复核测试服运行态 PASS：
  - `/opt/intruoyi/runtime/.env` => `IMAGE_TAG=release-20260623-random-erp-test-v1`
  - `docker compose ps` => `intruoyi-backend` / `intruoyi-frontend` 都为 `release-20260623-random-erp-test-v1`
  - `http://172.30.30.58:48081/actuator/health` => `{"status":"UP"}`
  - `http://172.30.30.58:8081/` => HTTP `200`
- 结论记录：本轮已按用户要求仅通过页面真实执行 `build-release -> deploy-test`，把随机 ERP 建单测试改动发布到测试服；未触发 `mark-tested`、正式服、备份服、备份、恢复或回滚动作。

## 2026-06-23 运行控制台左下角增加版本号

- 用户需求：在软件左下角增加版本号，版本号要与构建包一致，并能在软件上看到测试服务器和备份服务器是什么版本。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`，命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`、`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`；本任务不执行服务器写入、发布或真实 E2E。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-version-dock\`，写入 `task.md`、`execution-log.md`、`frontend-feature-evidence.md`、`backend-api-evidence.md`。
- RED 记录：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_frontend_version_badge_contract.py -q` 失败，前端未注入 `__APP_VERSION__`；`mvn -f D:\ProjectPackage\Int\IntRuoyiMaintance\backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal test` 失败，release-status 缺少正式服/备份服当前版本字段。
- 实现记录：前端通过 Vite 从 `frontend/package.json` 注入构建版本 `2026.06.0`，页面左下角新增版本栏；后端 `release-status` 扩展 `testCurrentReleaseTag/prodCurrentReleaseTag/backupCurrentReleaseTag`，按最近成功发布操作解析当前发布包标签。
- GREEN 记录：前端契约 pytest PASS；后端 MockMvc 单测 PASS；`pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend typecheck` PASS；`pnpm --dir D:\ProjectPackage\Int\IntRuoyiMaintance\frontend build` PASS；`python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\verify_contracts.py` PASS。
- 视觉验证：Playwright 打开 `http://127.0.0.1:48182/`，左下角显示软件版本 `2026.06.0`、测试服版本 `release-20260623-random-erp-test-v1`、正式服/备份服 `未上报`；临时截图已目视检查并在收尾清理。
- 收尾记录：执行 `task-closeout-cleanup` preview/apply，保留本任务 `task.md` 与 `execution-log.md`，清理 Vite 临时日志和本次 Playwright 临时截图。

## 2026-06-23 更新本机运行控制台到提交后版本

- 用户需求：`帮我更新到提交后的版本`
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`，命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；本任务只重建并重启本机 48181，不执行远端服务器写入。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-restart-to-commit\`，写入 `task.md` 与 `execution-log.md`。
- RED 记录：当前 48181 旧 JS 资源不含 `console-version-dock` 与 `2026.06.0`，`release-status` 只有 `testCurrentReleaseTag`，没有 `prodCurrentReleaseTag/backupCurrentReleaseTag`。
- 执行记录：停止旧 48181 进程 PID `29548`，随后运行 `powershell -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\build.ps1`，前端 typecheck/build 与 Maven 22 个测试均通过，jar 重新打包成功。
- 阻塞与处理：首次启动失败，原因是本机 `runtime-control.local.yaml` 的 `repo-root/frontend-root` 指向已删除 clean release worktree；已按项目固定路径改回 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 与 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`。
- GREEN 记录：重新启动 48181 成功，最终保留运行 PID `35752`；`http://127.0.0.1:48181/` 已加载新资源 `index-BVR1hDry.js`，该 JS 包含 `console-version-dock` 与 `2026.06.0`。
- 验证记录：`release-status` 已返回 `test/prod/backupCurrentReleaseTag`；Playwright 页面快照左下角显示软件版本 `2026.06.0`、测试服 `release-20260623-random-erp-test-v1`、正式服 `release-20260621-page-full-flow-mainmerge-v15`、备份服 `release-20260621-page-full-flow-mainmerge-v15`。
- 收尾记录：最终复核 PID `35752` 仍监听 `48181`，首页与 `release-status` 均 HTTP 200；运行日志转存到本机 `runtime/runtime-control/`，不占用任务目录。
- 收尾记录：执行 `task-closeout-cleanup` preview/apply，保留本任务 `task.md` 与 `execution-log.md`，清理旧启动临时日志。


## 2026-06-23 运行控制台展示当前版本变动说明

- 用户需求：只展示“当前测试服 / 正式服 / 备份服正在运行版本”的变动说明，不先做复杂历史版本库。
- 命中经验：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`，命中 `release-build-preflight-lessons.md`、`project-error-prevention.md` 与 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`；本任务只修改并验证本机维护控制台，不执行远端服务器写入或发布。
- 执行记录：创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-current-release-notes\`，写入 `task.md`、`execution-log.md`、前后端 evidence，并完成 RED/GREEN 记录。
- 实现记录：后端 `release-status` 增加 `testCurrentReleaseNotes/prodCurrentReleaseNotes/backupCurrentReleaseNotes`，从当前运行 releaseTag 对应发布包 `manifest.json` 的 `changeSet.summary` 与 `items/changes` 读取说明；缺失时返回 `status=BLOCKED` 与 `blockedReasons`，不伪造说明。
- 实现记录：前端左下角版本栏为测试服、正式服、备份服增加 `查看变更` 入口，弹窗显示版本号、构建时间、发布范围、组件、摘要、变动明细、源码提交和缺失信息。
- 验证记录：新增后端契约测试 PASS，原 test/prod/backup 版本字段回归 PASS；前端契约 pytest PASS；`pnpm typecheck` PASS；`pnpm build` PASS；前后端 evidence 校验 PASS。
- 运行态记录：执行 `scripts/build.ps1` PASS，Maven 全量测试 `23` 个通过；已重启本机 48181，当前 PID `46892`，首页加载 `assets/index-BriPWzK2.js`，接口已返回三个 notes 字段。
- 收尾记录：执行 `task-closeout-cleanup` preview/apply，保留本任务 `task.md` 与 `execution-log.md`，清理 evidence 临时交付文件。
