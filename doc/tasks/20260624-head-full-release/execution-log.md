# Execution Log

## BDD

BDD: 干净 HEAD 构建 -> Given 根工作区存在未提交改动 When 创建干净 worktree 并从 HEAD 构建 Then 发布包 sourceRepos 显示 dirty=false 且 commit 为 552a9dafac759012e1a199c2a9106d25372c1769。

BDD: 测试服先行发布 -> Given 发布包 manifest 校验通过 When 部署测试服 Then 远端 .env、前后端镜像 tag、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。

BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过 When 发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。

## Preflight

GREEN: experience-preflight -> PASS，已读取 experience-index、release-build-preflight-lessons、project-error-prevention、release-backup-restore、server-access、login-access、worktree-memory；用户当前任务明确授权发布测试服、正式服和备份服；正式服访问细节在文档中为脱敏状态，若本机缺少可执行凭据或脚本目标，后续必须 fail fast。

GREEN: git-preflight -> PASS，当前分支 `int_main`，HEAD `552a9dafac759012e1a199c2a9106d25372c1769`，提交信息 `任务: 增加当前版本变动说明`；根工作区存在未提交改动，禁止直接作为构建来源。

## RED

RED: dirty-root-build-source-check -> FAIL，`git status --short --branch` 显示根工作区存在已修改、删除和未跟踪文件；按发布门禁必须使用干净 HEAD worktree 或等效干净提交来源。

RED: python -X utf8 ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260624-head\sql\mysql -> FAIL，干净后端 HEAD 中 `sql/mysql/20260623_dcc_view_matrix_independent_source.sql` 缺少 `release-migration` 元数据。

RED: python -X utf8 -m pytest script\tests\test_dcc_view_matrix_independent_source_sql.py -q -> FAIL，新增测试要求 `20260623_dcc_view_matrix_independent_source.sql` 声明 `release-migration` 合同，当前 SQL 文件缺失该元数据。

RED: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -> FAIL，干净维护控制台 worktree 缺少 `doc/tasks/20260620-prod-release-current-latest/prod-target-config.json`，Maven 测试无法解析正式目标配置。

RED: mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace -DtrimStackTrace=false test -> FAIL，干运行净化工作区未携带发布包 `resources/resource-reference-manifest.json`，正式预检无法校验资源引用清单。

RED: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -> FAIL，基于维护仓提交 `36f4fb136856fba932f1a66a22db0e88466e75c0` 的干净 worktree 构建失败；深层 worktree 路径下 PowerShell 预检读取 `resources/resource-reference-manifest.json` 报路径不存在，暴露 dry-run 临时工作区路径过长风险。

## GREEN

GREEN: clean-worktree-preflight -> PASS，已创建维护控制台、业务后端、业务前端三个 detached HEAD 干净 worktree；初始 `git status --short --branch` 均无未提交改动。

GREEN: migration-metadata-missing-scan -> PASS，只读全量扫描 `20*.sql`，缺少 `release-migration` 元数据文件数量为 1：`20260623_dcc_view_matrix_independent_source.sql`。

GREEN: python -X utf8 -m pytest script\tests\test_dcc_view_matrix_independent_source_sql.py -q -> PASS，`3 passed`，后端 SQL 元数据测试通过。

GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS，`migrationCount=188`，后端发布迁移门禁通过。

GREEN: backend-release-metadata-commit -> PASS，后端已提交 `bdf2e35a30a1b679c59b6253f2a62250b62ffd43`，提交信息 `任务: 补齐DCC查看矩阵发布元数据`。

GREEN: mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace -DtrimStackTrace=false test -> PASS，维护控制台干运行净化工作区携带 `resources/` 证据目录，targeted TDD 通过。

GREEN: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -> PASS，维护控制台主工作区完整构建通过；前端 typecheck/build 成功，后端 `Tests run: 23, Failures: 0, Errors: 0, Skipped: 0`，jar 打包成功。

GREEN: mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace -DtrimStackTrace=false test -> PASS，正式 dry-run 临时净化工作区改为系统短临时路径后，深层 worktree 路径不再导致 PowerShell 读取资源 manifest 失败。

GREEN: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -> PASS，维护控制台路径长度修复后主工作区完整构建通过；前端 typecheck/build 成功，后端 `Tests run: 23, Failures: 0, Errors: 0, Skipped: 0`，jar 打包成功。

GREEN: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1 -> PASS，维护控制台干净 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-0736fb7` 基于 HEAD `0736fb715451a4f88829880a39272db0d7ea4f2c` 完整构建通过。

RED: build-release release-20260624-head-full-v1 -> FAIL，干净前端 worktree 缺少 `node_modules/vite/bin/vite.js`，前端 Vite CLI 前置依赖缺失。

GREEN: pnpm install --frozen-lockfile -> PASS，在干净前端 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260624-head` 补齐 node_modules，不改变已提交源码。

RED: build-release release-20260624-head-full-v2 -> FAIL，误开启 Smart Release report-only，但本次请求未提供 `SmartReleaseBaselineManifestPath`，脚本按前置条件失败。

GREEN: build-release release-20260624-head-full-v3 -> PASS，operation `op-2026-06-23T173205500308500Z-280a1cfd-ce31-4016-a2e5-45a71886e6c6` 成功；发布包上传 NAS `Backup/ReleasePackage/release-20260624-head-full-v3`。

GREEN: manifest-check release-20260624-head-full-v3 -> PASS，`releaseTag=release-20260624-head-full-v3`，`publishScope=code-only`，`component=intruoyi`，后端 `bdf2e35a30a1b679c59b6253f2a62250b62ffd43 dirty=false`，前端 `317056aa6a2db9dc1cf51e5bbf5e00d9e163729d dirty=false`，镜像 tar 存在。

GREEN: publish-test release-20260624-head-full-v3 -> PASS，operation `op-2026-06-23T174444462635200Z-f8253075-3157-4647-8588-eed209b0a9da` 成功；测试服 `.env`、容器镜像、健康检查、前端页面均为 v3。

GREEN: playwright-test-frontend -> PASS，Playwright 打开 `http://172.30.30.58:8081`，页面标题 `瑛泰管理系统 - 登录`，截图 `output/playwright/release-20260624-head-full-v3-test-frontend.png`。

GREEN: mark-release-tested release-20260624-head-full-v3 -> PASS，operation `op-2026-06-23T180242570470700Z-d7a4ccad-d746-498b-a353-019e38749182` 成功，恢复集 `restore:20260621-063218`。

GREEN: promote-prod release-20260624-head-full-v3 -> PASS，operation `op-2026-06-23T180402319749900Z-96551295-7c9b-49e6-b5d7-66af9943671e` 成功；正式服 `.env`、容器镜像、健康检查、前端页面均为 v3。

GREEN: promote-backup release-20260624-head-full-v3 -> PASS，operation `op-2026-06-23T181552882833300Z-bae3d087-739d-4269-be02-e6cd7eb7c9b9` 成功；备份服 `.env`、容器镜像、健康检查、前端页面均为 v3，发布目录使用 `/mnt/intruoyi-data`。

GREEN: release-status-final -> PASS，运行控制台 test/prod/backup 当前版本均为 `release-20260624-head-full-v3`，三环境 release notes 均能看到 manifest、summary、sourceRepos。

GREEN: task-closeout-cleanup --mode preview -> PASS，`status=ready`，保留 `task.md` 与 `execution-log.md`，无删除项、无阻塞、无警告。

## BLOCKER

BLOCKER: release-migration-policy-gate -> `sql/mysql/20260623_dcc_view_matrix_independent_source.sql` 缺少发布迁移元数据；根据发布文档，`code-only` / `SkipDatabaseSync` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁。本次发布包未构建，未触发测试服、正式服或备份服发布。该阻塞已通过后端提交 `bdf2e35a30a1b679c59b6253f2a62250b62ffd43` 解除。

## Closeout

GREEN: task-closeout-cleanup --mode preview -> PASS，保留 `task.md` 与 `execution-log.md`，无待删项，无 worktree closeout 动作。
