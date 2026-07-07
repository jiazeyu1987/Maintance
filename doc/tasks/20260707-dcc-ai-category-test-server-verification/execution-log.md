# Execution Log

GREEN: task-directory -> PASS, created `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260707-dcc-ai-category-test-server-verification`.

GREEN: previous-maintenance-task-status -> PASS, previous latest DCC release task `20260706-dcc-policy-test-server-release` is `completed`.

GREEN: experience-preflight -> PASS, 已按发布/测试服门禁读取并沿用 server-access、login-access、release-backup-restore、release-build-preflight-lessons 与前次测试服发布任务证据；本轮授权范围仅限测试服发布验证，不执行 mark-tested、正式服、备份服、回滚、恢复或数据清理。

BDD: 当前修复必须以新 releaseTag 进入测试服 -> Given 后端 `b51ec5f696` 与前端 `a63713926` 已提交 When 执行测试服验证 Then 必须构建新的 releaseTag 并发布到测试服，不能复用旧测试服运行标签。

BDD: 发布包必须可追溯源码提交 -> Given build-release 完成 When 读取发布包 `manifest.json` Then `sourceRepos` 必须包含后端和前端目标提交且 `dirty=false`。

BDD: 测试服运行态必须匹配 releaseTag -> Given publish-test 成功 When 检查测试服 Then `.env IMAGE_TAG`、后端/前端镜像 tag、后端 health 与前端 HTTP 必须全部通过。

GREEN: release-worktree-create -> PASS, base=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai.
GREEN: release-worktree-backend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai\ruoyi-vue-pro, commit=b51ec5f696780b6f088474c46e0ed3235c5f4cf0, dirty=False.
GREEN: release-worktree-frontend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai\yudao-ui-admin-vue3, commit=a637139266ff15835a427ddb057f55a6776a76da, dirty=False.
GREEN: release-worktree-maintenance -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai\IntRuoyiMaintance, commit=9aaa5fa964e452931d0567ebff8534213ddca345, dirty=False.
GREEN: nas-config-json-preflight -> PASS, NasConfigPath=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\nas-release-config\op-2026-07-03T080239101028700Z-e0b55e76-a62e-4445-be42-248ed979a170.json, contains required server/share/username/password fields.
GREEN: build-release-parameter-contract -> PASS, releaseTag=release-20260707-1405-dcc-ai-category-test-v1, code-only, explicit TestServerHost/ProdServerHost/BackupServerHost, BackendRepoRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai\ruoyi-vue-pro, FrontendRepoRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai\yudao-ui-admin-vue3.

RED: build-release-command-v1 -> FAIL, releaseTag=release-20260707-1405-dcc-ai-category-test-v1, exitCode=1, backend full build failed in yudao-module-showroom before yudao-server packaging.
BLOCKER: build-release-showroom-compile -> FAIL, missing class `cn.iocoder.yudao.module.showroom.content.model.ShowroomProductFreezeResult` imported by `ShowroomApiRuntime.java`; no release package/manifest generated, so publish-test is forbidden until backend committed release baseline compiles.

GREEN: release-input-rebaseline-after-showroom-fix -> PASS, v1 releaseTag 判废；重新基于已修复完整构建前置条件的后端 HEAD 与当前前端 HEAD 创建 v2 干净发布 worktree。
GREEN: release-worktree-v2-backend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai2\ruoyi-vue-pro, commit=489255c936eecccf30798e24e419083397ecaf1b, dirty=False.
GREEN: release-worktree-v2-frontend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai2\yudao-ui-admin-vue3, commit=99222bcf62ce699f92c2df6e6f419791e109fd72, dirty=False.
GREEN: release-worktree-v2-maintenance -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai2\IntRuoyiMaintance, commit=9aaa5fa964e452931d0567ebff8534213ddca345, dirty=False.

RED: build-release-command-v2 -> FAIL, releaseTag=release-20260707-1425-dcc-ai-category-test-v2, exitCode=1, backend build completed but frontend Vite build failed.
BLOCKER: build-release-frontend-compile -> FAIL, `BatchExecutionDetailPage.vue` declares `releasePrecheckLoading` twice in current frontend release baseline; no release package/manifest generated, so publish-test remains forbidden until frontend committed release baseline compiles.

GREEN: frontend-build-after-precheck-duplicate-fix -> PASS, command=`NODE_OPTIONS=--max-old-space-size=8192 pnpm exec vite build --mode test`, duplicate `releasePrecheckLoading` declaration removed and frontend build completed.
GREEN: frontend-compile-fix-commit -> PASS, commit=d0217dffbb2589ac5dbdbdf7a026b6ea4f61c7d4, file=src/views/mes/pro/edhr-batch/BatchExecutionDetailPage.vue.

NOTE: frontend-compile-fix-commit-correction -> previous commit command had no staged change; current frontend HEAD already contained the duplicate declaration fix and was verified by release-memory build.
GREEN: release-input-rebaseline-after-frontend-fix -> PASS, v2 releaseTag 判废；v3 backend=489255c936eecccf30798e24e419083397ecaf1b, frontend=d0217dffbb2589ac5dbdbdf7a026b6ea4f61c7d4, maintenance=9aaa5fa964e452931d0567ebff8534213ddca345.
GREEN: release-worktree-v3-backend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai3\ruoyi-vue-pro, commit=489255c936eecccf30798e24e419083397ecaf1b, dirty=False.
GREEN: release-worktree-v3-frontend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai3\yudao-ui-admin-vue3, commit=d0217dffbb2589ac5dbdbdf7a026b6ea4f61c7d4, dirty=False, releasePrecheckLoadingDeclarations=1.
GREEN: release-worktree-v3-maintenance -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai3\IntRuoyiMaintance, commit=9aaa5fa964e452931d0567ebff8534213ddca345, dirty=False.

GREEN: build-release-command-v3 -> PASS, releaseTag=release-20260707-1455-dcc-ai-category-test-v3, exitCode=0, backend/frontend build completed, Docker images exported, package uploaded to NAS Backup/ReleasePackage/release-20260707-1455-dcc-ai-category-test-v3.
GREEN: build-release-package-validation-v3 -> PASS, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260707-1455-dcc-ai-category-test-v3\manifest.json, publishScope=code-only, backendCommit=489255c936eecccf30798e24e419083397ecaf1b, frontendCommit=d0217dffbb2589ac5dbdbdf7a026b6ea4f61c7d4, sourceRepos dirty=false, no database/mysql/minio/files/data top-level dirs.

GREEN: publish-test-parameter-contract-v3 -> PASS, releaseTag=release-20260707-1455-dcc-ai-category-test-v3, Mode=deploy-release, Environment=test, ServerHost=172.30.30.58, RemoteAppDir=/opt/intruoyi/runtime, SkipDatabaseSync=true, SkipMinioSync=true; no mark-tested/prod/backup/rollback/restore action requested.
GREEN: publish-test-command-v3 -> PASS, releaseTag=release-20260707-1455-dcc-ai-category-test-v3, exitCode=0, target=test 172.30.30.58.

NOTE: remote-test-runtime-verification-first-attempt -> local PowerShell assertion used array `-notmatch` and falsely failed although remote output already showed matching releaseTag; retry joined output before matching.
GREEN: remote-test-runtime-verification-v3 -> PASS, releaseTag=release-20260707-1455-dcc-ai-category-test-v3, envImageTag=release-20260707-1455-dcc-ai-category-test-v3, backendImage=intruoyi-backend:release-20260707-1455-dcc-ai-category-test-v3, frontendImage=intruoyi-frontend:release-20260707-1455-dcc-ai-category-test-v3, backendRunning=true, frontendRunning=true, backendHealth=UP, frontendHttp=200, pdfWorkerHttp=200, releaseLock=APPLIED, sourceRepos backend=489255c936eecccf30798e24e419083397ecaf1b dirty=false frontend=d0217dffbb2589ac5dbdbdf7a026b6ea4f61c7d4 dirty=false.
GREEN: test-server-login-preflight-dcc-project-code -> PASS, baseUrl=http://172.30.30.58:8081, tenant=测试租户, username=aoteman, targetPath=/mdm/project-code, targetText=DCC项目代码, browser=system Chrome.

RED: dcc-ai-category-permission-contract -> FAIL, frontend static test failed before fix because AI分类 button lacked backend-required permissions and migration 20260707_dcc_ai_category_permission_menu.sql was missing; backend DccBaseSchemaTest#mysqlSchemaShouldRepairDccAiCategoryMenuPermissions failed with missing migration.
GREEN: dcc-ai-category-permission-contract -> PASS, frontend `node tests/e2e/dcc-project-code-ai-category-permission-static.spec.js`; backend `mvn -pl yudao-module-dcc '-Dtest=DccBaseSchemaTest#mysqlSchemaShouldRepairDccAiCategoryMenuPermissions' test`; script gate `python -m pytest script/tests/test_dcc_ai_category_permission_menu_sql.py`.
GREEN: dcc-ai-category-focused-regression -> PASS, frontend associated/basic-data/AI-permission static contracts and backend DccBaseSchemaTest,DccProjectCodeControllerTest passed before commit.
GREEN: dcc-ai-category-permission-commits -> PASS, backend=fec88bca85c6292bfff3e1c420f5780443801954, frontend=ce05b5d6d494410bc2c80d358f17c169cf669a5b.
GREEN: release-input-rebaseline-after-permission-fix -> PASS, v3 releaseTag 判废；v4 releaseTag=release-20260707-1525-dcc-ai-category-test-v4, backend=fec88bca85c6292bfff3e1c420f5780443801954, frontend=ce05b5d6d494410bc2c80d358f17c169cf669a5b, maintenance=9aaa5fa964e452931d0567ebff8534213ddca345.
GREEN: release-worktree-v4-backend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai4\ruoyi-vue-pro, commit=fec88bca85c6292bfff3e1c420f5780443801954, dirty=False.
GREEN: release-worktree-v4-frontend -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai4\yudao-ui-admin-vue3, commit=ce05b5d6d494410bc2c80d358f17c169cf669a5b, dirty=False.
GREEN: release-worktree-v4-maintenance -> PASS, path=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai4\IntRuoyiMaintance, commit=9aaa5fa964e452931d0567ebff8534213ddca345, dirty=False.
GREEN: build-release-parameter-contract-v4 -> PASS, releaseTag=release-20260707-1525-dcc-ai-category-test-v4, includes database SQL migration by omitting SkipDatabaseSync, skips Minio only, BackendRepoRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai4\ruoyi-vue-pro, FrontendRepoRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260707ai4\yudao-ui-admin-vue3, TestServerHost=172.30.30.58, ProdServerHost=172.30.30.57, BackupServerHost=172.30.30.59.
GREEN: build-release-command-v4 -> PASS, releaseTag=release-20260707-1525-dcc-ai-category-test-v4, exitCode=0, build completed with database SQL migration included and Minio skipped.

GREEN: build-release-package-validation-v4 -> PASS, releaseTag=release-20260707-1525-dcc-ai-category-test-v4, publishScope=with-data, backendCommit=fec88bca85c6292bfff3e1c420f5780443801954, frontendCommit=ce05b5d6d494410bc2c80d358f17c169cf669a5b, requiredSql=required-sql/20260707_dcc_ai_category_permission_menu.sql.
RED: publish-test-command-v4 -> FAIL, deploy-release was blocked before remote mutation because with-data package built with SkipMinioSync did not contain required MinIO snapshot `minio/yudao`; decision: do not bypass gate, do not fabricate snapshot, rebuild code-only package that still carries required SQL.
GREEN: build-release-command-v5 -> PASS, releaseTag=release-20260707-1605-dcc-ai-category-test-v5, code-only package built from backend=fec88bca85c6292bfff3e1c420f5780443801954 and frontend=ce05b5d6d494410bc2c80d358f17c169cf669a5b.
GREEN: build-release-package-validation-v5 -> PASS, publishScope=code-only, artifactCount=263, requiredSql=required-sql/20260707_dcc_ai_category_permission_menu.sql, no database dump, no MinIO snapshot.
GREEN: publish-test-command-v5 -> PASS, releaseTag=release-20260707-1605-dcc-ai-category-test-v5, deploy-release succeeded for Environment=test, ServerHost=172.30.30.58, SkipDatabaseSync=true, SkipMinioSync=true; no mark-tested/prod/backup/rollback/restore action executed.
GREEN: remote-test-runtime-verification-v5 -> PASS, envImageTag=release-20260707-1605-dcc-ai-category-test-v5, backendImage=intruoyi-backend:release-20260707-1605-dcc-ai-category-test-v5, frontendImage=intruoyi-frontend:release-20260707-1605-dcc-ai-category-test-v5, backendRunning=true, frontendRunning=true, backendHealth=UP, frontendHttp=200, pdfWorkerHttp=200.
GREEN: permission-migration-verification-v5 -> PASS, infra_release_migration migration_id=20260707_dcc_ai_category_permission_menu status=APPLIED releaseTag=release-20260707-1605-dcc-ai-category-test-v5; system_menu contains dcc:project-code:update and dcc:controlled-file:update; tenant_id=122 role binding contains both permissions.
GREEN: test-server-login-preflight-dcc-project-code-v5 -> PASS, baseUrl=http://172.30.30.58:8081, tenant=测试租户, username=aoteman, targetPath=/mdm/project-code, targetText=DCC项目代码, browser=system Chrome.
GREEN: real-ui-ai-category-verification-v5 -> PASS, projectCodeId=1, beforeCandidates=[2054545668044050095], buttonVisible=true, buttonEnabledBefore=true, percentSeen=true, progressTexts=[AI分类中 0%], noProgressBar=true, completionMessageSeen=true, afterCandidates=[], classifiedFileIds=[2054545668044050095], failedResponses=[].
GREEN: database-ai-category-result-v5 -> PASS, fileId=2054545668044050095, dcc_project_code_id=1, project_code_recognition_type=PROJECT_NAME, project_code_recognition_text=PTCA球囊扩张导管, file_type_level1=技术文档, file_type_level2=未分类, file_type_level3=未分类文件类型; remainingCandidates(projectCodeId=1)=0; migration status remains APPLIED.
NOTE: release-scope -> 本轮只完成测试服真实运行态和真实页面验证；未执行 mark-tested，未推进正式服或备份服。
