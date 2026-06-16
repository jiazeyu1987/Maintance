# 不带数据构建发布包 E2E 验证执行记录

## BDD

BDD: 通过运行控制台真实数据构建发布包 -> Given 独立运行控制台在本机启动且发布包构建配置完整，When 操作者通过 Playwright 打开运行控制台页面、选择构建发布包、发布范围选择含数据并执行预览后提交，Then 系统应只触发 `build-release` 操作并生成可核验的发布包构建证据。

BDD: 禁止发布动作 -> Given 用户仅授权构建发布包且明确不要发布，When 本次 E2E 操作与结果核验完成，Then 本次任务不得触发 `publish-test`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`restore-data`、`restart` 等动作。

BDD: 构建包不带数据 -> Given 用户最新要求构建不要带数据，When 操作者通过 Playwright 预览并执行 `build-release`，Then 命令必须使用 `publishScope=code-only` 并包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`，发布包不得包含数据库 dump、MinIO 快照或 DCC 对象清单。

## TDD / Verification Evidence

- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest test` -> FAIL, `build-release` 预览缺少 `-NasServer`、`-NasShare`、`-NasReleaseRoot` 与后端运行基座参数，独立抽取漏掉原运行控制台发布包配置注入。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest test` -> PASS，`build-release with-data` 预览包含 NAS 发布仓库和后端运行基座参数，且不包含 `-SkipDatabaseSync`、`-SkipMinioSync`、`-ProdServerHost`。
- GREEN: `mvn -f backend/pom.xml test` -> PASS。
- GREEN: `.\scripts\build.ps1` -> PASS，首次因旧 jar 被 `127.0.0.1:48181` 进程占用失败，停止旧本机控制台进程后重跑成功。
- GREEN: `curl.exe -s http://127.0.0.1:48181/actuator/health` -> PASS，返回 `{"status":"UP"}`。
- GREEN: Playwright 打开 `http://127.0.0.1:48181/` -> PASS，页面显示运行控制台，操作记录为空。
- GREEN: Playwright 预览 `build-release` 命令 -> PASS，发布标签 `release-20260616-112813-e2e`，发布范围为含数据；参数包含 `-Mode build-release`、`-TestServerHost 172.30.30.58`、`-BackupServerHost 172.30.30.59`、`-NasServer 172.30.30.4`、`-NasShare IT共享`、`-NasReleaseRoot Backup/ReleasePackage` 与后端运行基座参数；不包含 `-SkipDatabaseSync`、`-SkipMinioSync`、`-ProdServerHost`。
- GREEN: experience-preflight -> PASS，用户仅授权真实数据构建发布包且明确不要发布；本机健康、脚本存在、被管理源码路径存在、Docker/运行基座 tar 与镜像存在、NAS 发布包配置存在且本机配置文件已被 `.gitignore` 排除；预览命令只触发 `build-release`，不触发发布、晋级、备份、恢复、回滚、重启或远端清理。
- RED: Playwright 执行 `build-release`，发布标签 `release-20260616-112813-e2e` -> FAIL，脚本退出码 1；日志显示 `Release database SQL directory missing: D:\ProjectPackage\Int\IntRuoyiMaintance\sql\mysql`，根因是独立抽取后的发布脚本仍从 `ops` 位置推断业务源码根。
- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test` -> FAIL，预览缺少 `-BackendRepoRoot`、`-FrontendRepoRoot`、`-WebsiteRepo`。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test` -> PASS，预览显式传入被管理源码路径。
- GREEN: `mvn -f backend/pom.xml test` -> PASS。
- GREEN: `.\scripts\build.ps1` -> PASS，重新打包独立控制台并重启到 `127.0.0.1:48181`。
- GREEN: Playwright retry 预览 `build-release` 命令 -> PASS，发布标签 `release-20260616-113500-e2e`，参数包含 `-BackendRepoRoot D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro`、`-FrontendRepoRoot D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3`、`-WebsiteRepo D:/ProjectPackage/Website`；不包含 `-SkipDatabaseSync`、`-SkipMinioSync`、`-ProdServerHost`。
- GREEN: experience-preflight -> PASS，retry 仍仅执行 `build-release`，源码根、前端根、展厅根、NAS 发布仓库、Docker/运行基座、本机健康和禁发布边界已重新确认。
- RED: Playwright 执行 retry `build-release`，发布标签 `release-20260616-113500-e2e` -> FAIL，脚本复制真实 MinIO 数据 `23.46 GiB` 后在生成 `manifest/dcc-object-inventory.json` 阶段失败；错误为 `DCC object inventory row is malformed`，根因是 DCC 对象清单查询仍使用 MySQL batch tab 分隔行协议，真实数据中特殊文件名破坏列边界。
- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL，脚本仍包含 tab 分隔 DCC inventory parser。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS，DCC inventory 查询改为单列 `JSON_OBJECT` 输出并用 `ConvertFrom-Json` 解析。
- GREEN: experience-preflight -> PASS，third retry 仅执行 `build-release`，修复不跳过真实数据、不清理或发布，不触发发布、晋级、备份、恢复、回滚、重启或远端清理。
- RED: Playwright 执行 third retry `build-release`，发布标签 `release-20260616-121500-e2e` -> FAIL，真实后端构建、前端构建、Docker 镜像导出、本机 MySQL dump 与真实 MinIO `23.46 GiB` 同步完成后，在 DCC inventory 生成阶段失败；错误为 `DCC object inventory JSON row is malformed`，根因是 PowerShell 5.1 进程 stdout 捕获未显式 UTF-8，真实中文文件名 JSON 行被编码破坏。
- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL，脚本缺少 DCC inventory base64 传输协议。
- GREEN: 只读查询 `fileId=9198354896134` -> PASS，`REPLACE(TO_BASE64(CAST(JSON_OBJECT(...) AS CHAR CHARACTER SET utf8mb4)), '\n', '')` 可解码为合法 UTF-8 JSON，`objectPath=dcc/original/20260615/@最终版规程@ - 快捷方式.lnk.重命名`。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS，契约要求 DCC inventory 使用 base64 行协议、`FromBase64String` 解码与显式 `StandardOutputEncoding`。
- GREEN: PowerShell AST parse `ops/deploy/publish-int-ruoyi.ps1` -> PASS。
- GREEN: `mvn -f backend/pom.xml test` -> PASS。
- NOTE: 并发观察 -> 机器上存在原 IntRuoyi 运行控制台父进程触发的独立 `deploy-release -Environment backup` 进程；该进程不属于本次维护应用 E2E 操作，本次任务未中断该发布类进程，后续验证仅以本次维护应用操作记录为准。
- GREEN: experience-preflight -> PASS，fourth retry 仍仅允许通过维护应用前端触发 `build-release`；已确认修复不跳过真实数据、不清理或发布，不触发发布、晋级、备份、恢复、回滚、重启或远端清理；同时记录存在外部并发发布进程，验证时区分来源。
- RED: Playwright 执行 fourth retry `build-release`，发布标签 `release-20260616-125800-e2e` -> ABORTED，用户最新要求“发布不要带数据 / 构建不要带数据”，该操作为 `with-data`，因此本机中止 PowerShell 构建进程；后台操作状态变为 `FAILED`，本地目录没有 `release-manifest.json` 或 `manifest`。
- GREEN: 清理 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-125800-e2e` -> PASS，删除前校验目标路径位于发布缓存根目录下，清理后 `targetExists=false`，避免留下数据库 dump 和 MinIO 快照半成品。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewSkipsDatabaseAndMinioData test` -> PASS，契约确认 `code-only` 预览包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS。
- GREEN: Playwright 预览 `code-only build-release` 命令 -> PASS，发布标签 `release-20260616-152022-codeonly-e2e`，页面发布范围为“仅代码”；参数包含 `-Mode build-release`、`-SkipDatabaseSync`、`-SkipMinioSync`、NAS 发布仓库、被管理源码路径与后端运行基座参数；不包含发布、晋级、恢复、回滚、重启、`-ProdServerHost`、数据库 dump 或 MinIO 同步参数。
- GREEN: experience-preflight -> PASS，用户最新授权仅允许不带数据构建发布包且不要发布；预览命令已确认 `publishScope=code-only`，包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`，不触发发布、晋级、备份、恢复、回滚、重启、远端清理、数据库 dump 或 MinIO 同步。
- GREEN: Playwright 执行 `code-only build-release` -> PASS，操作 `op-2026-06-16T072304860538200Z-0d13eb24-9a16-47b9-aed7-68b9b3e71f21` 最终状态 `SUCCESS`，参数为 `publishScope=code-only`、`releaseTag=release-20260616-152022-codeonly-e2e`。
- GREEN: 发布包本地产物核验 -> PASS，目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-152022-codeonly-e2e` 包含 `release-manifest.json`、`manifest.json`、镜像 tar `811197440` bytes；`release-manifest.json` 中 `releaseTag=release-20260616-152022-codeonly-e2e`、`publishScope=code-only`、`component=intruoyi`、`onlyOfficeIncluded=false`。
- GREEN: 不带数据产物核验 -> PASS，本地发布包不存在 `ruoyi-vue-pro-current.sql`、`minio` 目录、`manifest\dcc-object-inventory.json`。
- GREEN: NAS 发布包列表核验 -> PASS，`GET /admin-api/infra/runtime-control/release-packages` 返回 `release-20260616-152022-codeonly-e2e`，`manifestPath=Backup/ReleasePackage/release-20260616-152022-codeonly-e2e`，`status=AVAILABLE`。
- GREEN: 禁止发布动作核验 -> PASS，维护应用操作记录中本次最新操作为 `build-release/SUCCESS`，不存在 `publish-test`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`restore-data`、`restart`。
- GREEN: Playwright 最终页面快照 -> PASS，页面操作记录显示 `op-2026-06-16T072304860538200Z-0d13eb24-9a16-47b9-aed7-68b9b3e71f21` 为 `SUCCESS`，浏览器 console error 为 0；请求列表仅包含 overview、operations、capacity/status、release-status、actions/preview、actions。
- GREEN: `mvn -f backend/pom.xml test` -> PASS。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS。
- GREEN: `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260616-runtime-control-build-release-e2e --mode preview` -> PASS，预览无删除项、无阻塞、无警告。

## Blockers

- 暂无，已通过高风险执行前门禁。
