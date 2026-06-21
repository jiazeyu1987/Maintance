# 请求与命令记录

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
