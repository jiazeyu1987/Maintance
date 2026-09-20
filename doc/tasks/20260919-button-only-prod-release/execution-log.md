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
