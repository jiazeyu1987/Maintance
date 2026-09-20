# Execution Log

## 2026-09-20

- BDD: 测试服发布锁恢复按钮 -> Given 测试服存在旧 `RUNNING` 发布锁且无迁移写入证据，When 运维人员在 worktree 运行控制台真实页面点击“恢复测试服发布锁”，Then 后端必须只对匹配 `test-<releaseTag>` 与同一 `releaseTag` 的锁执行恢复，并在确认无远端发布执行器和无迁移证据后才将锁标记为 `FAILED`。
- BDD: 恢复脚本 Windows SSH 传输噪音 -> Given 远端 SQL 已返回 `LOCK_RECOVERED`，When Windows OpenSSH 在会话关闭时额外输出 `close - IO is still pending on closed socket`，Then 操作可判定成功；若存在 `RECOVER_BLOCKED_*`、SQL ERROR、权限或连接错误，则必须失败。
- GREEN: experience-preflight -> PASS；本轮只在 `D:\IntRuoyiWorktree\r260917-button-publish7\m` worktree 操作，恢复锁、后续构建、测试服和正式服写入均必须通过真实页面按钮触发。
- GREEN: recover-test-release-lock-ui-preview -> PASS；真实页面按钮预览脚本为 `ops\deploy\recover-release-operation-lock.ps1`，参数包含 `-ExpectedOperationId test-release-20260919-button-prod-r4 -ExpectedReleaseTag release-20260919-button-prod-r4 -ConfirmText RECOVER-TEST-LOCK`。
- BLOCKER: recover-test-release-lock-first-attempt -> FAIL；按钮操作 `op-2026-09-20T053707366529700Z-f416d7bb-6be3-4c7e-ac31-48ae6065018d` 因 PowerShell stdin 管道调用 ssh 出现 `close - IO is still pending on closed socket` 失败，远端锁仍为 `RUNNING`。
- RED: recover-script-stdin-ssh-transport -> FAIL；恢复脚本通过本机 stdin 管道喂给 ssh 的方式在 Windows OpenSSH 下不稳定。
- GREEN: recover-script-base64-transport -> PASS；改为 base64 远端载荷命令，不再依赖本机 stdin 管道；PowerShell AST PASS。
- BLOCKER: recover-test-release-lock-second-attempt -> FAIL；按钮操作 `op-2026-09-20T053857480531200Z-bf8661fc-0ad6-4e73-bcff-e472dd8d1155` 进入远端 SQL 后失败于 MySQL `ERROR 1267 Illegal mix of collations`。
- RED: recover-script-collation -> FAIL；恢复脚本字面量默认排序规则与锁表列排序规则不一致。
- GREEN: recover-script-collation -> PASS；恢复脚本 SQL 显式设置 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;`。
- PARTIAL: recover-test-release-lock-third-attempt -> REMOTE_RECOVERED；按钮操作 `op-2026-09-20T053959200981200Z-0f23216b-cee5-4405-8bfe-59b753d5433a` 在远端成功将旧 r4 锁从 `RUNNING` 改为 `FAILED`，只读核对 `finished_at=2026-09-20 13:40:00`、`error_message=RECOVERED_BY_EXPLICIT_BUTTON_AFTER_EXECUTOR_AND_MIGRATION_CHECK`、旧 r4/r14 迁移证据为 0；但本地 operation 因 Windows OpenSSH socket close 噪音仍标记 FAILED。
- GREEN: recover-script-ssh-close-noise-regression -> PASS；恢复脚本仅在 `LOCK_RECOVERED` 明确出现且无真实阻塞/SQL/权限/连接错误时接受 `close - IO is still pending on closed socket` 噪音；`python -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_sql_preflight_gate.py -q`，65 passed。
- BLOCKER: build-release-r15 -> FAIL；真实按钮 operation `op-2026-09-20T054706396356800Z-a6aca932-3e18-4f7a-bd9c-f143b48d12b0` 在 source approval 阶段发现控制台仍使用旧期望维护提交 `84852f5...`，而当前 worktree 已提交为 `48fa0b7...`；未进入 Maven、Docker、NAS 或测试服写入，r15 判废。
- GREEN: worktree-console-source-freeze-refresh -> PASS；仅重启本任务 worktree 控制台并绑定 `INT_RUOYI_EXPECTED_MAINTENANCE_COMMIT=48fa0b7...`，后端/前端端口健康均为 200。
- GREEN: build-release-r16-ui-submit -> PASS；真实页面按钮提交 `release-20260920-button-prod-r16`，operation `op-2026-09-20T055055390621100Z-e5f2d8d3-8d3e-4689-b99b-924b37d470a6`。
- GREEN: build-release-r16 -> PASS；Maven BUILD SUCCESS、前端 `build:test` 成功、Docker 镜像构建/导出、manifest/checksum、迁移策略、NAS 上传均通过；NAS 路径 `Backup/ReleasePackage/release-20260920-button-prod-r16`。
- GREEN: local-manifest-validator-r16 -> PASS；正式 validator `ops/release/validate-release-manifest.ps1` 返回 `MANIFEST_VALIDATION_PASSED`，package declarations 与 sha256 checks passed，forbidden content scan passed。
- GREEN: publish-test-r16-ui-submit -> PASS；真实页面按钮提交 `release-20260920-button-prod-r16` 到测试服，operation `op-2026-09-20T061528541045600Z-22fe2a5c-06e5-4c87-8dff-7972fb6855f3`；镜像分片、required SQL、ops-runtime、Docker load、MySQL/Redis、目标 SQL 前置均通过。
- BLOCKER: publish-test-r16 -> FAIL；迁移 `20260830_dcc_registration_certificate_notification_role_scope_backfill` 在测试服第 284 行触发 `ERROR 1644 Missing registration certificate notification role scope source`。只读核对显示 `infra_job.registrationCertificateReminderDailyJob.handler_param={"actorId":1}`，源码期望 `[910218,910231]`；真实 `system_role` 只有 910218，910231 在当前迁移源码中没有任何创建记录。r16 operation lock 已回写 FAILED，r16 迁移台账为 FAILED，未切换 `.env`/backend/frontend 运行版本。
- BLOCKER: notification-role-source-contract -> NEEDS_BUSINESS_DECISION；不能未经批准地过滤缺失角色、补造未知角色或修改已执行迁移来掩盖通知授权数据缺失。需要正式确定 910231 的业务角色身份/创建迁移，或批准将通知角色契约改为现有角色集合后，才能继续新 releaseTag 发布。
- BDD: 晋级正式服按钮只部署同一已测包 -> Given 工作流已处于 TESTED 且绑定测试 operation/evidence，When 用户点击“晋级正式服/上线已验证发布包”，Then 后端只生成 `deploy-release -Environment prod -ReleaseTag <same>`，必须携带测试 operation/evidence，不得重新 build-release 或 publish-test。
- BDD: 发布锁恢复行为约束 -> Given 一个测试服发布锁仍为 RUNNING，When 恢复流程或旧执行器尝试写入，Then 只有本机执行器已终止且 operation、执行身份、租约完全匹配的恢复者能收口为 FAILED；活跃慢任务、并发恢复输家、旧执行器和未持锁释放都必须失败。
- BDD: 通知角色迁移写入路径回滚 -> Given 已存在批准角色和证书公司且 scope 写入后发生数据库异常，When 执行迁移，Then `mdm_role_company_scope` 与 `infra_job.handler_param` 都必须保持原状。
- RED: release-button-prod-review-gap -> FAIL；复审指出原证据不足以证明正式晋级按钮主链路、发布锁并发所有权行为和 SQL 写入后失败回滚。
- GREEN: release-lock-and-migration-behavior-tests -> PASS；`python -X utf8 -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_operation_lock_behavior.py .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，17 passed。
- GREEN: promote-prod-button-contract -> PASS；`mvn -pl yudao-module-infra '-Dtest=RuntimeControlOperationActionPromotionTest,ReleaseWorkflowOrchestratorTest' '-Dsurefire.failIfNoSpecifiedTests=false' test`，27 tests passed，BUILD SUCCESS；新增测试证明正式晋级只调用 deploy-release/prod/同一 releaseTag/测试 operation evidence，不包含 build-release 或 publish-test。
- NOTE: recover-lock-button-contract -> 当前应用前后端未发现真实“恢复发布锁”后端入口；旧任务记录中的 `recover-release-operation-lock.ps1` 参数预览不能作为当前按钮契约证据。若后续要把恢复锁做成页面按钮，必须新增服务端 DTO/状态元数据并用行为测试证明五项必填所有权参数来自真实锁记录，缺失时阻塞。
- CORRECTION: recover-lock-button-contract -> 上一条 NOTE 只查了主程序仓，遗漏维护仓独立控制台；维护仓 `frontend/src/App.vue` 存在“恢复测试服发布锁”，维护仓后端 `RuntimeControlOperationAction.recoverTestReleaseLockArguments` 仍只传旧参数。该问题真实存在，不能关闭。
- BDD: 恢复锁按钮必须接真实远端锁所有权 -> Given 维护控制台用户选择 `recover-test-release-lock` 和 releaseTag，When 后端预览或执行，Then 后端必须从测试服 `infra_release_operation_lock` 的 RUNNING 记录读取 executor_host、executor_pid、executor_identity、lease_token，并传给 `recover-release-operation-lock.ps1`；预览不得泄露真实 lease token，执行日志也必须脱敏。
- RED: recover-lock-button-missing-owner-params -> FAIL；维护仓后端旧参数构建只包含 `ExpectedOperationId/ExpectedReleaseTag/ConfirmText`，缺少 `ExpectedExecutorHost/ExpectedExecutorPid/ExpectedExecutorIdentity/ExpectedLeaseToken/ExecutorTerminalState`。
- GREEN: recover-lock-button-owner-contract -> PASS；新增 `RuntimeReleaseLockInspector` 通过 SSH 只读查询远端测试服锁表，后端准备恢复动作时接入五项所有权参数；预览中 lease token 显示 `<resolved-from-remote-lock>`，operation 命令日志对 `-ExpectedLeaseToken` 脱敏。`mvn '-Dtest=RuntimeControlContractTest#recoverTestReleaseLockPreviewUsesRemoteLockOwnerContractWithoutExposingLeaseToken' test` PASS。
- BDD: 真实 MySQL 发布锁所有权 -> Given 发布锁记录包含 executor 和 lease，When 错误身份、旧操作或旧租约尝试释放/恢复，Then MySQL 更新必须 `ROW_COUNT()=0` 且当前 RUNNING 锁不变；只有精确所有权匹配才能改变锁状态。
- GREEN: release-lock-real-mysql-behavior -> PASS；`python -X utf8 -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_operation_lock_behavior.py .\scripts\tests\test_release_operation_lock_mysql_behavior.py .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，19 passed。
- GREEN: maintenance-backend-contract-regression -> PASS；`mvn '-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest' test`，11 tests passed，BUILD SUCCESS。
- GREEN: powershell-ast -> PASS；`recover-release-operation-lock.ps1`、`publish-int-ruoyi.ps1` 均通过 PowerShell AST parse。
- BLOCKER: maintenance-original-parity-baseline -> FAIL；`mvn '-Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest,RuntimeControlOriginalGovernanceParityTest' test` 中 `RuntimeControlOriginalParityTest` 仍 9 failures，主要表现为测试夹具 release package manifest/checksum 字段缺失导致 package 列表为空或 promote preview 返回 400。该失败不由本轮恢复锁契约改动触发，但仍阻止声明维护控制台完整回归通过。
- BDD: 远端锁读取协议必须稳定 -> Given MySQL client 以 `--batch` 输出查询结果，When 锁字段中需要字段分隔，Then 查询必须使用 `--raw` 多列 TSV 协议，Java 只解析真实 Tab，不得依赖字段内 `\t` 转义。
- BDD: 远端锁读取必须受超时约束 -> Given SSH/远端 MySQL 命令不退出，When 后端读取锁所有权，Then 必须先 waitFor 限时并在超时后 kill 进程，不得在 `readAllBytes()` 上无限阻塞。
- RED: lock-inspector-protocol-timeout-review -> FAIL；复审指出 `CONCAT_WS('\\t', ...)` 在 `mysql --batch` 下会转义 Tab，且读取器先 `readAllBytes()` 后 `waitFor`，存在误报无锁和无限等待风险。
- GREEN: lock-inspector-protocol-timeout -> PASS；`RuntimeReleaseLockInspector` 改为 `SELECT 'LOCK_OWNER', ...` 多列输出并添加 `--raw`，且先 `waitFor(30s)` 再读取 stdout；`RuntimeReleaseLockInspectorTest` 覆盖 raw TSV 解析、拒绝字面量 `\\t` 协议、源码断言 `--raw` 和 wait-before-read。
- GREEN: maintenance-original-parity-baseline -> PASS；升级 `RuntimeControlOriginalParityTest` 发布包夹具的 `manifest.json`，补齐当前包读取器要求的 `publishScope/component/includeShowroomBuildPackage/onlyOfficeIncluded/artifacts.sha256`；`mvn '-Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest,RuntimeControlOriginalGovernanceParityTest,RuntimeReleaseLockInspectorTest' test`，32 tests passed，BUILD SUCCESS。
- GREEN: release-lock-real-mysql-regression-rerun -> PASS；`python -X utf8 -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_operation_lock_behavior.py .\scripts\tests\test_release_operation_lock_mysql_behavior.py .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，19 passed；`recover-release-operation-lock.ps1`、`publish-int-ruoyi.ps1` AST PASS。
- BDD: 注册证通知角色收口为 910218 -> Given 业务确认注册证通知只发送给现有角色 `910218`，When 迁移修正 `registrationCertificateReminderDailyJob` 的 `handler_param.roleIds` 并回填角色公司范围，Then SQL 必须写入 `[910218]`，不得使用 query-current 权限推断通知角色，不得包含或要求 `910231`。
- BDD: 通知角色修正事务回滚 -> Given `infra_job.handler_param` 只有 `actorId` 且 role-company scope 写入后发生数据库异常，When 执行 `20260830_dcc_registration_certificate_notification_role_scope_backfill.sql`，Then `infra_job.handler_param` 与 `mdm_role_company_scope` 必须一起回滚到执行前状态。
- RED: notification-role-business-decision -> FAIL；r16 测试服发布失败证据显示正式库只有角色 `910218`，旧 SQL 仍要求 `[910218,910231]` 并触发 `ERROR 1644 Missing registration certificate notification role scope source`。
- GREEN: notification-role-910218-real-mysql -> PASS；用户选择方案 2 后，`python -X utf8 -m pytest .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，5 passed，覆盖正常执行、缺失角色、租户隔离、写入后失败完整回滚、重复执行幂等。
- GREEN: notification-role-910218-app-static -> PASS；`python -X utf8 -m pytest .\script\tests\test_dcc_registration_certificate_notification_role_scope_backfill_sql.py -q`，3 passed；`rg -n "910231" ...` 仅剩测试中的禁止出现断言，SQL 不再包含 `910231`。
- GREEN: notification-role-910218-junit -> PASS；`mvn -pl yudao-module-dcc '-Dtest=DccRegistrationCertificateReminderSchemaTest' '-Dsurefire.failIfNoSpecifiedTests=false' test`，6 tests passed，BUILD SUCCESS。
- GREEN: migration-policy-gate -> PASS；`python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql` 返回 `status=passed`、`migrationCount=620`。
- GREEN: app-main-promotion-contract-integration -> PASS；应用远程 `origin/int_main` 基于最新 `64f45c958` 叠加正式晋级按钮合同测试并推送 `014b45832`；测试按当前主干合同校验 `deploy-release/prod/同一 ReleaseTag/-RequireTested`，不传旧 `TestOperationId/TestOperationEvidencePath`，不触发 `build-release/publish-test`。
- GREEN: final-integrated-sql-real-mysql -> PASS；`DCC_NOTIFICATION_ROLE_SCOPE_MIGRATION=D:\IntRuoyiWorktree\r260920-main-integrate-promotion\a\IntRuoyiBackend\sql\mysql\20260830_dcc_registration_certificate_notification_role_scope_backfill.sql python -X utf8 -m pytest .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，5 passed；这是最终应用主干集成 SQL 的正常执行、缺角色、租户隔离、后续失败完整回滚、重复执行幂等证据。
- GREEN: maintenance-release-lock-regression -> PASS；`mvn '-Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest,RuntimeControlOriginalGovernanceParityTest,RuntimeReleaseLockInspectorTest' test`，32 tests passed；`python -X utf8 -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_operation_lock_behavior.py .\scripts\tests\test_release_operation_lock_mysql_behavior.py .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q`，19 passed。
- BLOCKER: maintenance-int-main-fusion -> FAIL；维护仓主工作区 `D:\ProjectPackage\Int\IntRuoyiMaintance` 的 `int_main` 当前存在 21 项未提交/未跟踪改动（含备份恢复任务记录、frontend 新控制台文件、多个任务目录与 docs/releases），按工作区保护规则不得在该目录强行合并或覆盖；维护修复链已保留在 `codex/r260920-button-prod-release-final-verification`。
## 2026-09-20 18:23 CST — r18 按钮发布前置门禁

- BDD: button-only prod promotion -> Given 应用主干提交 `014b45832133848077a39ec163596d9fc1d63369` 已推送且本地最终 SQL/发布锁修复验证通过, When 运行控制台通过页面按钮构建/部署/标记测试/晋级正式服, Then 同一 `releaseTag=release-20260920-button-prod-r18` 必须贯穿 `build-release -> publish-test -> mark-tested -> promote-prod`，且所有写入动作只由页面按钮触发。
- GREEN: maintenance-console-restart -> PASS, 停止旧维护控制台 PID `59460` 后在 `D:\IntRuoyiWorktree\r260917-button-publish7\m` 前台启动 PID `62688`，health=`UP`。
- GREEN: build-release-preview -> PASS, Playwright 页面“预览命令”显示 `-BackendRepoRoot D:/IntRuoyiWorktree/r260920-main-integrate-promotion/a/IntRuoyiBackend` 与 `-FrontendRepoRoot D:/IntRuoyiWorktree/r260920-main-integrate-promotion/a/IntRuoyiFronted`，releaseTag=`release-20260920-button-prod-r18`。
- GREEN: release-status-preflight -> PASS, `/release-status` 返回成功；`release-20260920-button-prod-r18` 尚不存在，recent operations 未显示 RUNNING，`latestTestedReleaseTag=null`，测试/正式运行态等待实际部署后验收。
- GREEN: experience-preflight -> PASS, 本轮高风险写入前已核对单一 releaseTag、应用目标提交、维护控制台实际加载路径、无 RUNNING 本机 operation；维护仓 `int_main` 仍因主工作区脏改动未融合，继续作为收尾阻塞记录，不用脏主工作区执行发布。

## 2026-09-20 18:30 CST — r18 失败与源码批准按钮契约修复

- RED: r18-build-release-button -> FAIL, 页面按钮执行 `release-20260920-button-prod-r18` 后 operation `op-2026-09-20T102335995748100Z-f21115c7-30d7-4976-bc9a-985f2d5f0ebe` 失败，日志为 `SOURCE_APPROVAL_REQUIRED: ExpectedMaintenanceCommit`；构建前门禁阻断，未形成新发布包，r18 判废。
- BDD: source approval contract -> Given 用户通过按钮构建发布包, When 后端生成 `publish-int-ruoyi.ps1 -Mode build-release` 参数, Then 必须从当前维护/应用 git HEAD 自动传递 `ExpectedMaintenanceCommit`、`ExpectedApplicationCommit`、`ExpectedFrontendCommit` 和 `SourceSelectionId`，禁止依赖人工环境变量。
- RED: `mvn -f backend\pom.xml '-Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewForwardsApprovedSourceCommits' '-Dsurefire.failIfNoSpecifiedTests=true' test` -> FAIL, 预览响应缺少 `-ExpectedMaintenanceCommit`。
- GREEN: `mvn -f backend\pom.xml '-Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewForwardsApprovedSourceCommits' '-Dsurefire.failIfNoSpecifiedTests=true' test` -> PASS, 后端预览已自动加入源码批准参数。
- GREEN: `mvn -f backend\pom.xml '-Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest,RuntimeControlOriginalGovernanceParityTest,RuntimeReleaseLockInspectorTest' test` -> PASS, 33 tests。
- GREEN: `python -X utf8 -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_operation_lock_behavior.py .\scripts\tests\test_release_operation_lock_mysql_behavior.py .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q` -> PASS, 19 passed。
- GREEN: `mvn -f backend\pom.xml test package` -> PASS, 33 tests and maintenance jar rebuilt.
- GREEN: maintenance-fix-commit -> PASS, `59c4c41 任务: 自动传递发布源码批准提交`。

## 2026-09-20 18:36 CST — r19 前端合同测试缺失修复

- RED: r19-build-release-button -> FAIL, 页面按钮执行 `release-20260920-button-prod-r19` 后 operation `op-2026-09-20T103240115196400Z-e7b6081b-1ed6-4632-81a7-aeac78990cff` 越过源码批准门禁并完成后端发布合同测试，但前端合同阶段失败：`Cannot find module 'D:\IntRuoyiWorktree\r260920-main-integrate-promotion\a\IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs'`；r19 判废，未形成可用发布包。
- BDD: frontend one-button contract -> Given 发布脚本要求运行 `runtime-control-one-button-static.spec.cjs`, When 应用前端主干包含运行控制台页面, Then 该静态合同必须验证构建、测试服部署、标记测试通过和正式晋级按钮均存在且绑定 releaseTag/publishScope/PROD/testConclusion/recoverySet 参数。
- GREEN: `node IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs` -> PASS, 应用前端补回合同测试。
- GREEN: app-main-push -> PASS, 应用主干推送 `aff15aad8 任务: 补回发布按钮前端合同测试`；下一轮必须使用新 tag `release-20260920-button-prod-r20` 和应用批准提交 `aff15aad8e...`。

## 2026-09-20 19:10 CST — r20 前端依赖门禁修复

- BDD: deterministic frontend dependency install for release worktree -> Given 按钮发布在临时应用 worktree 中执行 `pnpm install --frozen-lockfile` 和 `pnpm ts:check`, When 依赖包含需要构建脚本的包, Then 构建脚本审批必须由源码配置显式声明，不能依赖人工交互或被 pnpm 自动忽略。
- RED: r20-build-release-button -> FAIL, operation `op-2026-09-20T103835358200500Z-c344ca3a-d791-46d8-bb05-21065acb11d0` 已通过后端发布合同和前端静态合同，但 `corepack pnpm --dir ... ts:check` 因 `'cross-env' is not recognized` 失败；发布包未形成，r20 判废。
- RED: frontend-dependency-preflight -> FAIL, `corepack pnpm ignored-builds` 报告 `core-js`, `esbuild`, `@parcel/watcher`, `vue-demi`, `@swc/core`, `core-js-pure`, `es5-ext` 被自动忽略。
- GREEN: frontend-dependency-approval-config -> PASS, 应用前端 `package.json` 增加 pnpm `onlyBuiltDependencies` 显式允许列表；`corepack pnpm install --frozen-lockfile` 完成且相关 postinstall/build 脚本实际执行。
- GREEN: frontend-dependency-preflight-rerun -> PASS, `corepack pnpm ignored-builds` 返回 `None`；`cross-env`, `vite`, `vue-tsc` 二进制均存在。
- GREEN: frontend-ts-check-r20-regression -> PASS, 在应用 worktree 执行 `corepack pnpm ts:check` 退出码 0，已越过 r20 的原始失败点。
- GREEN: frontend-one-button-static-contract-r20-regression -> PASS, `node IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs` 返回 `PASS: runtime-control one-button release static contract is wired`。
- GREEN: app-main-push-dependency-approval -> PASS, 应用主干提交 `7576d8292 任务: 固定前端发布依赖构建审批` 已通过 branch runtime port guard 并推送到 `origin/int_main`。
- BLOCKER: maintenance-int-main-fusion -> STILL_BLOCKED, 主工作区存在与本任务无关的脏改动，继续禁止在脏主工作区强行融合；发布继续使用专用维护 worktree。

## 2026-09-20 20:xx CST — r21 目标数据预检阻断与修复

- BDD: release target preflight source completeness -> Given 发布计划包含需要目标数据核验的迁移, When 真实按钮开始 build-release, Then 应用发布 worktree 必须携带每个 migrationId 对应的版本化只读 `.preflight.sql`，缺失时在 SSH 前阻断。
- GREEN: experience-preflight -> PASS；r21 继续使用专用维护 worktree 和应用批准提交，未绕过页面按钮，未手工修改测试服/正式服数据库、锁、`.env` 或成功状态。
- RED: `release-20260920-button-prod-r21` build-release -> FAIL；operation `op-2026-09-20T110404074517700Z-90bbf866-7f72-4b87-888f-573b108e19aa` 通过 Maven、前端静态合同、`ts:check`、141 项发布脚本测试、Docker、迁移策略和依赖门禁后，在目标数据预检阶段报 `TARGET_PREFLIGHT_MISSING`，28 个计划迁移全部缺失检查文件，报告 `sshStarted=false`，未产生远程写入。
- ROOT-CAUSE: 应用发布 worktree `D:\IntRuoyiWorktree\r260920-main-integrate-promotion\a\IntRuoyiBackend\sql\mysql\target-preflight` 原先不存在；当前 Git 分支 `codex/r82-reg-cert-preflight-fix` 提供了与当前迁移契约匹配的 60 个版本化检查文件，不能从旧脏 worktree 复制。
- GREEN: target-preflight-contract-regression -> PASS；`python -X utf8 -m pytest scripts/tests/test_release_target_data_preflight.py scripts/tests/test_release_migration_preflight_matrix.py -q`，38 passed；`python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_package_governance.py -q`，132 passed。
- GREEN: app-target-preflight-integration -> PASS；使用 `git restore --source=codex/r82-reg-cert-preflight-fix -- IntRuoyiBackend/sql/mysql/target-preflight` 恢复 60 个受版本控制文件，提交 `86463ae96 任务: 补齐发布目标数据预检`，branch runtime port guard 通过并推送 `origin/int_main`。
- BLOCKER: r21-retired -> NEEDS_NEW_RELEASE_TAG；r21 不得复用，必须在目标预检通过且控制台实际加载应用提交 `86463ae96` 后使用新的 releaseTag 重走按钮链路。

## 2026-09-20 20:xx CST — r22 目标预检收敛与新增缺口

- BDD: complete target migration preflight coverage -> Given 发布计划包含 28 个待执行迁移, When 按钮构建在 SSH 前执行目标数据预检, Then 每个 migrationId 都必须有真实只读 `.preflight.sql`，且检查其迁移前置条件与幂等后置状态。
- RED: `release-20260920-button-prod-r22` build-release -> FAIL；operation `op-2026-09-20T114339055753500Z-119f74f1-29e1-4545-858e-847f2286ce81` 通过构建、前端合同、类型检查、141 项发布测试、Docker 和迁移门禁后，在目标数据预检阶段报 `TARGET_PREFLIGHT_MISSING`，28 个迁移中仍缺 7 个检查文件，`sshStarted=false`，未产生远程写入；r22 判废。
- ROOT-CAUSE: 应用主干虽已集成 60 个历史目标预检文件，但以下当前迁移没有对应检查：`20260915_mes_team_leader_cleanup_permission_menu`、`20260917_mes_edhr_batch_execution_admin_visible`、`20260918_mes_edhr_batch_execution_upload_permission`、`20260918_mes_edhr_label_print_menu_removal`、`20260918_mes_management_representative_admin_permission`、`20260918_mes_pqc_release_owner_admin_assignment`、`20260919_dcc_dual_version_download_permissions`。
- GREEN: seven-target-preflight-tests -> PASS；新增 7 个基于实际迁移前置条件和后置状态的只读检查文件，发布合同、迁移矩阵、SQL 预检和包治理测试共 `170 passed`。
- GREEN: app-target-preflight-commit -> PASS；应用提交 `e8f30e8bb 任务: 补齐近期迁移目标预检` 已通过 branch runtime port guard；首次推送因 GitHub TLS `unexpected eof` 失败，未宣称已推送，需在新 release 前重试并核对远端提交。
- BLOCKER: r22-retired -> NEEDS_NEW_RELEASE_TAG；必须先确认 `e8f30e8bb` 已进入 `origin/int_main`，再用全新 releaseTag 通过真实按钮重走构建与后续发布门禁。

## 2026-09-20 21:xx CST — r23 发现并修正预检语义错误

- RED: `release-20260920-button-prod-r23` build-release -> FAIL；operation `op-2026-09-20T130651803709600Z-e97e2979-235e-4881-9374-a7f1f9039aba` 已实际进入远端只读目标预检，`sshStarted=true`，21/28 检查通过，首个失败为 `20260915_mes_team_leader_cleanup_permission_menu`，报告 `TARGET_PREFLIGHT_FAILED`；未执行迁移写入。
- ROOT-CAUSE: 新增检查错误地要求“迁移后状态”在迁移执行前已存在，未区分可执行的前置条件与已完成的幂等状态，导致合法待执行迁移被错误阻断。
- GREEN: preflight semantics regression -> PASS；7 个检查改为校验真实迁移前置条件、冲突安全和已完成状态可重复执行，既不放宽角色/租户范围，也不伪造成功；四组发布预检测试 `170 passed`。
- GREEN: app-main-push -> PASS；应用提交 `4568e1c1b 任务: 修正迁移前置预检语义` 已通过 branch runtime port guard 并推送 `origin/int_main`。
- BLOCKER: r23-retired -> NEEDS_NEW_RELEASE_TAG；r23 已停止在远端写入前的只读预检阶段，禁止复用；下一轮必须以维护提交、应用提交 `4568e1c1b` 和全新 releaseTag 重新点击构建按钮。

## 2026-09-20 21:xx CST — r24 目标环境真实前置条件阻断

- BDD: target preflight must reflect executable migration prerequisites -> Given 目标测试服存在待执行迁移, When 通过按钮构建发布包, Then 只读预检必须阻断真实不满足迁移前置条件的数据状态，且不得继续 SSH 写入。
- GREEN: `release-20260920-button-prod-r24` 预览确认维护提交 `d66b2ba22422e1251664eb5d37dfe392d45563a6`、应用/前端提交 `4568e1c1b7be15ee75e5981908c32edb288ca51d`，随后由真实页面按钮执行。
- GREEN: r24 已通过 Maven、前端合同、类型检查、141 项发布测试、Docker、依赖、构建证据和迁移台账计划；目标预检实际连接测试服，`sshStarted=true`，24/28 检查通过。
- BLOCKER: r24 在 `20260918_mes_edhr_label_print_menu_removal` 的目标数据前置检查失败，operation `op-2026-09-20T132451702289300Z-7ea53a64-e53a-4f42-9d7e-81d617ac1252` 终态 FAILED，未执行迁移写入；该迁移明确拒绝部分退休状态，必须先由正式数据负责人确认并通过按钮提供受控修复/恢复方案，禁止手工改库或伪造预检通过。
- BLOCKER: r23 与 r24 操作记录一度同时显示 RUNNING，说明控制台在前一构建终态刷新前仍允许提交下一操作；本任务停止继续发布，待确认两者真实终态并修复并发门禁后再重试。

## 2026-09-20 22:xx CST — 标签打印退休预检修正

- BDD: label print retirement preflight follows local baseline -> Given 本机基准要求 eDHR 标签打印入口退休, When 测试服仍处于 21 个标签打印菜单全部 active 的待迁移状态, Then 目标预检应允许正式迁移执行退休；若目标已全部 retired 则允许幂等重跑；若处于部分退休则阻断。
- RED: remote-label-preflight-r24-current -> FAIL；直接在测试服只读执行当前预检返回 `TARGET_PREFLIGHT_BLOCKED:20260918_mes_edhr_label_print_menu_removal`，而只读核对显示 `system_menu` 21/21 行存在且全部 active、`system_tenant_package.menu_ids` JSON 有效，说明阻断来自预检残留的“必须已退休”条件。
- GREEN: remote-label-preflight-fixed -> PASS；预检改为 `active_count IN (0, 21)`，直接在测试服只读执行返回 `TARGET_PREFLIGHT_PASS:20260918_mes_edhr_label_print_menu_removal`。
- GREEN: preflight-contract-regression -> PASS；四组发布预检/迁移矩阵/SQL 合同/包治理测试 `170 passed`。
- GREEN: app-main-push -> PASS；应用提交 `13c2517a5 任务: 修正标签打印退休预检` 已通过 branch runtime port guard 并推送 `origin/int_main`。

## 2026-09-20 22:xx CST — r25 管理者代表菜单预检修正

- BDD: management representative permission preflight follows local baseline -> Given 本机和测试服均存在两个 active `mes:pro-edhr-release:query` 菜单和一个 active `mes:pro-edhr-release:approve` 菜单, When 管理者代表权限迁移为现有管理者代表角色授权, Then 预检应要求每个业务权限至少存在一个有效菜单，并由迁移绑定所有匹配菜单；不得删除、合并或手工改写目标环境菜单。
- RED: `release-20260920-button-prod-r25` build-release -> FAIL；operation `op-2026-09-20T140509483300100Z-fe2ea217-0ce0-4054-9117-a3ed83084020` 已通过前序构建门禁并进入测试服只读目标预检，失败于 `20260918_mes_management_representative_admin_permission`，`sshStarted=true`；未执行迁移写入，r25 判废不得复用。
- ROOT-CAUSE: 原预检与迁移要求 `query/approve` 两个权限合计恰好 2 个有效菜单；真实本机基准与测试服均为 `query=2`、`approve=1`。该差异不是目标脏数据，而是历史菜单树中父/子查询入口共用同一权限。
- GREEN: remote-management-preflight-fixed -> PASS；修正后直接在测试服只读执行 `20260918_mes_management_representative_admin_permission.preflight.sql` 返回 `TARGET_PREFLIGHT_PASS:20260918_mes_management_representative_admin_permission`。
- GREEN: preflight-contract-regression -> PASS；`python -X utf8 -m pytest -q scripts/tests/test_release_target_data_preflight.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_package_governance.py` -> `170 passed in 45.56s`。
- INFO: migration-policy-targeted -> historical dependency chain blocks local ad-hoc targeted gate；手工局部运行 `run-release-migration-policy-gate.py` 会沿 `20260814_mes_production_release_roles` 追到历史依赖 `20260611_mes_edhr_work_task_flow`，当前源码中无同名迁移文件。该问题非本次 SQL 差异引入，且 r25 构建路径已通过发布脚本内置迁移门禁后才进入目标预检；本轮不扩大为历史迁移元数据整改。
- GREEN: app-main-push -> PASS；应用提交 `c5dd152dc 任务: 放宽管理者代表菜单预检` 已通过 branch runtime port guard 并推送 `origin/int_main`。

## 2026-09-20 23:xx CST — 13 项审阅问题第一轮根因修复

- BDD: migration rollback safety -> Given 标签打印退休和管理者代表权限迁移包含多步写入, When 任一后续 SQL 失败, Then 所有业务表写入必须由同一显式事务回滚并原样抛出错误。
- RED: `python -X utf8 -m pytest -q script\tests\test_edhr_label_print_menu_removal_sql.py script\tests\test_mes_management_representative_admin_permission_sql.py` -> FAIL, 新增事务合同 2 项失败，两个 SQL 均无 `START TRANSACTION`/`COMMIT`/异常 `ROLLBACK`。
- GREEN: 同一命令 -> PASS，`7 passed`；两个迁移均加入 `DECLARE EXIT HANDLER FOR SQLEXCEPTION`、`START TRANSACTION`、`COMMIT`、`ROLLBACK`、`RESIGNAL`。
- BDD: release lock and command lifecycle -> Given 发布脚本已取得锁并执行上传/镜像/环境/HTTP/历史记录验收, When 任一步骤抛错或正常完成, Then 统一 try/catch 必须清理本操作锁，且锁保持到强制验收和历史记录完成；命令超时必须独立于日志 EOF 计时并终止进程树。
- GREEN: `mvn -q -Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest,RuntimeControlOriginalGovernanceParityTest,RuntimeReleaseLockInspectorTest test` -> PASS。
- GREEN: `python -X utf8 -m pytest -q scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_operation_lock_behavior.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_release_package_governance.py` -> `146 passed`。
- GREEN: PowerShell AST -> PASS；发布脚本取得锁后的完整部署段已纳入统一 try/catch，APPLIED 释放移动到 HTTP/PDF/历史记录验收之后；命令执行器改为独立超时等待、异步日志泵、进程树终止及租约 token 脱敏；经验归档失败不再改写已持久化执行终态。
- BLOCKER: 13 项中的真实 PowerShell/SSH/MySQL 端到端失权写入验证、预览快照绑定、维护仓主干融合和真实“晋级正式服”按钮验收尚未完成；在这些证据补齐前不得发布。
