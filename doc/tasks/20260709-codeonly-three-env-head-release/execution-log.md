# Execution Log - 20260709-codeonly-three-env-head-release

- 创建时间：2026-07-09 13:12:23 +0800
- 用户需求：执行 IntRuoyi 不带数据的完整三环境发布闭环，使用当前三个仓库 int_main 已提交 HEAD，在干净临时发布 worktree 中构建发布，SkipDatabaseSync + SkipMinioSync，同一 releaseTag 完成测试服、正式服、备份服发布验证。

BDD: code-only 三环境发布闭环 -> Given 当前后端/前端/维护仓 int_main 已提交 HEAD 且发布在干净临时 worktree 执行，When 执行 build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup，Then 同一 releaseTag 的五个 operation 均 SUCCESS，三环境验证 IMAGE_TAG、镜像 tag、health、frontend、PDF worker 成功，备份服额外验证 /mnt/intruoyi-data。

GREEN: task-document-created -> PASS, task.md 与 execution-log.md 已创建。
GREEN: preflight-documents-read -> PASS, 已读取并摘录指定前置文档，完整读取副本保存到 evidence/preflight-read-*.txt。
GREEN: experience-preflight -> PASS, 已按经验索引与指定发布前置文档摘录本任务强制门禁；高风险发布动作前置检查通过。

## 命令记录
- 2026-07-09 13:12:23 +0800 创建任务目录：D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260709-codeonly-three-env-head-release
- 2026-07-09 13:12:23 +0800 读取前置文档：docs/experience-index.md、docs/release-build-preflight-lessons.md、docs/release-agent-checklist.md、IntRuoyi release-backup-restore/server-access/worktree-memory。

## 初始仓库状态
```json
[
    {
        "path":  "D:\\ProjectPackage\\Int\\IntRuoyi\\ruoyi-vue-pro",
        "branch":  "int_main",
        "head":  "c1ae4d0a82a423656131913c8d92c31e2923464c",
        "dirty":  true,
        "status":  " M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordRouteERecognizer.java\n M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordRouteERecognizerTest.java"
    },
    {
        "path":  "D:\\ProjectPackage\\Int\\IntRuoyi\\yudao-ui-admin-vue3",
        "branch":  "int_main",
        "head":  "0931b8dc3725b34689ee36e68cc4dd3a7aacea3b",
        "dirty":  true,
        "status":  "?? doc/tasks/20260708-schedule-order-export-columns/e2e-diagnostics/\n?? doc/tasks/20260708-schedule-order-export-columns/e2e-export/\n?? output-frontend-8081-start.err.log\n?? output-frontend-8081-start.out.log\n?? output-yudao-8081-restart-frontend.err.log\n?? output-yudao-8081-restart-frontend.out.log\n?? output-yudao-ui-8081-restart-report-import.err.log\n?? output-yudao-ui-8081-restart-report-import.out.log\n?? output-yudao-ui-8081-restart-workorder-link.err.log\n?? output-yudao-ui-8081-restart-workorder-link.out.log\n?? output-yudao-ui-8081-start.err.log\n?? output-yudao-ui-8081-start.out.log\n?? showroom-vue-tsc-after-freeze-removal.log\n?? tests/output/20260707-edhr-t6-batch-action-diagnostic/\n?? tests/output/20260707-edhr-t6-batch-page-diagnostic/\n?? tests/output/20260707-edhr-t6-detail-api-diagnostic/\n?? tests/output/20260707-edhr-t6-detail-diagnostic/\n?? tests/output/20260707-edhr-t6-login-diagnostic/\n?? tests/output/20260707-edhr-t6-open-create-diagnostic/\n?? tests/output/20260709-schedule-order-process-route-unified-list-login-diagnostic-2/\n?? tests/output/20260709-schedule-order-process-route-unified-list-login-diagnostic/\n?? tests/output/20260709-schedule-order-process-route-unified-list-real/\n?? tests/output/edhr-cell-rule-toggle-real-e2e.cjs\n?? tests/output/edhr-cell-rule-toggle-real/\n?? tests/output/iot-ota-task-pause-resume/\n?? tests/output/mes-replan-feedback-remaining-candidate-scan/\n?? tests/output/mes-replan-feedback-remaining-diagnostic/\n?? tests/output/mes-schedule-route-production-factor-real/\n?? tests/output/pro-workorder-batch-real-e2e.cjs\n?? tests/output/replan-date-data-diagnostic/\n?? tests/output/replan-date-login-probe.png\n?? tests/output/replan-date-page-probe/\n?? yudao-ui-admin-vue3/"
    },
    {
        "path":  "D:\\ProjectPackage\\Int\\IntRuoyiMaintance",
        "branch":  "int_main",
        "head":  "140b253731f5b7520dd32e5fa5de30313484a2c3",
        "dirty":  true,
        "status":  " M doc/tasks/20260701-dcc-batch-recognition-five-workers/execution-log.md\n M doc/tasks/20260701-rebuild-publish-all-after-fvm-message-fix/execution-log.md\n?? \" + repr($local) + r\"\n?? config/runtime-control.local.before-20260701-205043.yaml\n?? config/runtime-control.local.before-category-20260701-221522.yaml\n?? config/runtime-control.local.before-dccfix-20260708.yaml\n?? config/runtime-control.local.before-fix3-20260703-001013.yaml\n?? config/runtime-control.local.before-mes-scheduler-20260701-230707.yaml\n?? config/runtime-control.local.before-nodata-evening-20260702-2151.yaml\n?? config/runtime-control.local.before-nodata-evening-fix-20260702-2240.yaml\n?? config/runtime-control.local.before-nodata-evening-fix2-20260702-2316.yaml\n?? config/runtime-control.local.before-showroom-legacy-order.yaml\n?? doc/tasks/20260707-showroom-legacy-order-prod-release/\n?? doc/tasks/20260709-codeonly-three-env-head-release/\n?? frontend/pnpm-workspace.yaml\n?? runtime/"
    }
]
```

GREEN: release-worktrees-created -> PASS, 2026-07-09 13:13:48 +08:00，已创建本次专用临时发布 worktree：backend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709ce\b，frontend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709ce\f，maintenance=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709ce\m；三者均为 detached HEAD 且 dirty=false。证据：evidence/release-worktrees-created.json。
RED: runtime-control-worktree-build -> FAIL, 2026-07-09 13:15:22 +08:00，维护仓 worktree 无 .\\mvnw.cmd，运行控制台尚未启动；发布 build-release 尚未执行，未生成 releaseTag。证据：evidence/runtime-control-worktree-start-failure-missing-mvnw.txt。

GREEN: runtime-control-worktree-health-v2 -> PASS, 2026-07-09 13:19:08 +08:00，改用系统 Maven 构建维护仓 worktree 后端 JAR 并启动，http://127.0.0.1:48181/actuator/health=UP。证据：evidence/runtime-control-worktree-maven-direct-build.out.log、evidence/runtime-control-worktree-java-start-v2-verification.txt。

RED: build-release-preview-v1 -> FAIL, 2026-07-09 13:20:12 +08:00，预览请求携带 targetEnvironment 被接口参数契约拒绝（code=400,msg=targetEnvironment）；未执行 build operation，未生成发布包，v1 不进入发布闭环。证据：evidence/build-release-v1-preview-response.json、evidence/build-release-v1-preview-failure-targetEnvironment.txt。

RED: build-release-preview-v2 -> FAIL, 2026-07-09 13:21:44 +08:00，预览命令缺少 ProdServerHost=172.30.30.57；未执行 build operation，未生成发布包，v2 不进入发布闭环。证据：evidence/build-release-v2-preview-response.json、evidence/build-release-v2-preview-local-checks.json、evidence/build-release-v2-preview-failure-missing-prodserverhost.txt。

GREEN: runtime-control-prodhost-config -> PASS, 2026-07-09 13:21:44 +08:00，已在临时控制台配置补齐 prod host=172.30.30.57 并重启，health=UP。证据：evidence/runtime-control-worktree-config-prod-host-patch.txt、evidence/runtime-control-worktree-restart-after-prodhost-verification.txt。

RED: build-release-preview-v3 -> FAIL, 2026-07-09 13:23:09 +08:00，运行控制台 API 预览仍缺少 ProdServerHost=172.30.30.57；未执行 build operation，未生成发布包，v3 不进入发布闭环。下一轮改用同一维护仓 worktree 的 publish-int-ruoyi.ps1，显式传入 Test/Prod/BackupServerHost。证据：evidence/build-release-v3-preview-response.json、evidence/build-release-v3-preview-local-checks.json、evidence/build-release-v3-preview-failure-missing-prodserverhost.txt。

GREEN: build-release-direct-preflight-v4 -> PASS, 2026-07-09 13:23:09 +08:00，直接脚本命令门禁通过，含 SkipDatabaseSync、SkipMinioSync、TestServerHost=172.30.30.58、ProdServerHost=172.30.30.57、BackupServerHost=172.30.30.59，且不含 promote/backup/rollback/restore。releaseTag=release-20260709-codeonly-three-env-head-v4。证据：evidence/build-release-v4-direct-preflight.json。

RED: build-release-command-v4 -> FAIL, 2026-07-09 13:23:12 +08:00，releaseTag=release-20260709-codeonly-three-env-head-v4，exitCode=。失败证据已冻结：evidence/build-release-v4-command-summary.txt、evidence/build-release-v4-operation.out.log、evidence/build-release-v4-operation.err.log。

RED: build-release-command-v4-root-cause -> FAIL, 2026-07-09 13:23:49 +08:00，releaseTag=release-20260709-codeonly-three-env-head-v4 在构建门禁失败：SQL release migration metadata type 不合法，文件 sql/mysql/20260708_mes_balloon_process_device_capacity.sql；未生成发布包，v4 判废。证据：evidence/build-release-v4-failure-invalid-migration-type.txt。

RED: migration-policy-balloon-type -> FAIL, 2026-07-09 13:26:30 +08:00，复现 sql/mysql/20260708_mes_balloon_process_device_capacity.sql 的 release migration metadata type=schema-data 不在允许值内。证据：evidence/migration-policy-balloon-type-red.json、evidence/migration-policy-balloon-type-red.stderr.txt。

GREEN: migration-policy-balloon-with-dependency -> PASS, 2026-07-09 13:27:43 +08:00，将依赖 20260513_mes_dv_machinery_extend 与球囊 SQL 一起验证后，type=schema 元数据通过发布迁移门禁。证据：evidence/migration-policy-balloon-with-dependency-green.json。

RED: metadata-fix-script-array-bug -> FAIL, 2026-07-09 13:28:18 +08:00，上一轮补齐 20260708_mes_batch_record_version_phase_one.sql 元数据后，脚本在构造依赖文件数组时误用 Join-Path 多参数中断；未提交，继续以已补丁文件验证门禁。证据：evidence/metadata-fix-script-array-bug-freeze.txt。

GREEN: migration-policy-metadata-fixes-focused -> PASS, 2026-07-09 13:28:20 +08:00，球囊迁移与批记录版本 phase-one 迁移均已连同依赖通过发布迁移门禁。证据：evidence/migration-policy-balloon-with-dependency-green-final.json、evidence/migration-policy-batch-record-version-phase-one-green-final.json。

GREEN: migration-policy-full-after-metadata-fixes-final -> PASS, 2026-07-09 13:28:21 +08:00，全量 SQL 发布迁移门禁通过。证据：evidence/migration-policy-full-after-metadata-fixes-final.json。

### 2026-07-09 迁移元数据门禁修复

- RED: build-release-v4 -> FAIL，`20260708_mes_balloon_process_device_capacity.sql` 使用非法 `type=schema-data`。
- RED: migration-policy-full -> FAIL，`20260708_mes_batch_record_version_phase_one.sql` 缺少 `release-migration` 元数据。
- GREEN: migration-policy-full-after-metadata-fixes-final -> PASS，证据 `evidence/migration-policy-full-after-metadata-fixes-final.json`。
- GREEN: python -X utf8 -m pytest script/tests/test_release_migration_metadata_sql_20260708.py -> PASS，证据 `evidence/backend-release-migration-20260708-pytest.out.log`。
- 经验沉淀：已更新 `docs/release-build-preflight-lessons.md` 与 `docs/experience-index.md`，后续 build-release 前必须先过全量迁移元数据策略门禁。
### 2026-07-09 publish-test v5 失败冻结

- RED: publish-test-v5 -> FAIL，20260708_mes_balloon_process_device_capacity.sql 执行到 line 763 报 ERROR 1137 (HY000): Can't reopen table: 'seed'。
- 冻结证据：evidence/publish-test-v5-operation.out.log、evidence/publish-test-v5-operation.err.log、evidence/publish-test-v5-result.json、evidence/publish-test-v5-preflight.json、evidence/build-release-v5-manifest-validation.json。
- 远端快照：evidence/publish-test-v5-failure-remote-snapshot.txt，包含 release dir、required-sql checksum、operation lock、migration 失败行、.env IMAGE_TAG 与容器状态。
- 经验沉淀：已更新 docs/release-build-preflight-lessons.md 与 docs/experience-index.md；后续修复后必须重新构建新的 releaseTag，不能复用 v5 继续闭环。
### 2026-07-09 球囊 required SQL MySQL 1137 根因修复

- GREEN: python -X utf8 -m pytest script/tests/test_release_migration_metadata_sql_20260708.py -> PASS，证据 `evidence/backend-balloon-1137-pytest-final.out.log`。
- GREEN: python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql --output <evidence> -> PASS，证据 `evidence/migration-policy-full-after-balloon-1137-fix-final-output.json`。
- 修复内容：`20260708_mes_balloon_process_device_capacity.sql` 移除 `WHERE NOT EXISTS` 相关临时表 reopen 模式，并为 next route process 使用独立 `tmp_balloon_route_process_next_seed` 临时表副本。
### 2026-07-09 publish-test v6 失败冻结

- RED: publish-test-v6 -> FAIL，20260709_mes_rt000006_batch_record_mapping.sql 执行到 line 325 报 ERROR 1644 (45000): Missing RT000006 pressure pump route。
- 冻结证据：evidence/publish-test-v6-operation.out.log、evidence/publish-test-v6-operation.err.log、evidence/publish-test-v6-result.json、evidence/publish-test-v6-preflight.json、evidence/build-release-v6-manifest-validation.json。
- 远端快照：evidence/publish-test-v6-failure-remote-snapshot.txt，包含 release dir、required-sql checksum、operation lock、migration 失败行、RT000006/pressure pump 相关业务表快照、.env IMAGE_TAG 与容器状态。
- 经验沉淀：已更新 docs/release-build-preflight-lessons.md 与 docs/experience-index.md；后续修复后必须重新构建新的 releaseTag，不能复用 v6 继续闭环。

## 维护脚本 code-only/data SQL 修复（2026-07-09 14:46:36）
- 失败证据已冻结：`publish-test-v6-operation.out.log`、`publish-test-v6-operation.err.log`、`publish-test-v6-result.json`、`publish-test-v6-preflight.json`、`publish-test-v6-failure-remote-snapshot.txt`。
- BDD: code-only 发布不执行数据迁移 -> Given release manifest `publishScope=code-only` 且 preflight plan 含 `type=data` APPLY 项 / When deploy-release 应用 required SQL / Then data required SQL 必须在远端 MySQL 执行前被跳过，schema/menu/config/permission/seed 仍按计划执行。
- GREEN: python -X utf8 -m pytest tests/test_code_only_required_sql_contract.py -q -> PASS，输出 `evidence/maintenance-codeonly-required-sql-contract-pytest.out.log`。
- GREEN: code-only-required-sql-contract-fix -> PASS，汇总 `evidence/maintenance-codeonly-required-sql-contract-fix-summary.json`。
- 结论：需要使用维护脚本修复后的新 releaseTag 继续闭环，禁止拼接 v6 的失败结果。


## v7 manifest 范围失败冻结（2026-07-09 15:06:02）
- RED: build-release-v7-manifest-validation -> FAIL，build operation 虽 SUCCESS，但 manifest sourceRepos 包含 dirty Website 仓，超出本次 IntRuoyi 后端/前端发布范围，v7 判废。
- 冻结证据：`evidence/build-release-v7-result.json`、`evidence/build-release-v7-direct-preflight.json`、`evidence/build-release-v7-manifest-validation.json`、`evidence/build-release-v7-manifest-scope-failure-freeze.json`。
- 根因：build-release 命令未显式传 `-Component intruoyi`，脚本默认 `Component=full`，在当前环境变量存在 WebsiteRepo 时会把 Website 纳入发布包与 sourceRepos。
- 经验沉淀：已新增 code-only IntRuoyi 发布必须显式 `-Component intruoyi` 的门禁；下一轮必须重新生成 v8，禁止复用 v7。


## v8 manifest 校验修正（2026-07-09 15:22:45）
- GREEN: build-release-v8-manifest-validation -> PASS，按现有 manifest 契约校验：publishScope=code-only，sourceRepos 仅后端/前端且 dirty=false，无 Website 仓/website 目录/数据目录命中，证据 `evidence/build-release-v8-manifest-validation.json`。
- 说明：`manifest.json` 当前不定义 `component` 字段；范围以 `-Component intruoyi` 构建命令、sourceRepos、topEntries 和 `release-manifest.json`（如存在）校验。


## v8 publish-test 失败冻结与过滤修复 v2（2026-07-09 15:38:14）
- RED: publish-test-v8 -> FAIL，releaseTag=release-20260709-codeonly-three-env-head-v8，远端仍执行 `20260709_mes_rt000006_batch_record_mapping.sql` 并报 `Missing RT000006 pressure pump route`。
- 冻结证据：`evidence/publish-test-v8-result.json`、`evidence/publish-test-v8-operation.out.log`、`evidence/publish-test-v8-operation.err.log`、`evidence/publish-test-v8-failure-remote-snapshot.txt`、`evidence/publish-test-v8-preflight-item-inspect.json`。
- 根因：`preflight-plan.json` 的 APPLY item 不携带 `type`，旧过滤逻辑读取 `$item.type`，导致 `type=data` 项未被跳过。
- 修复：code-only 过滤改为从 manifest 派生的 `$requiredDatabaseSqlScripts` 建立 `migrationId -> type` 映射；缺 migrationId/type 直接 fail fast；`type=data` 在远端 MySQL 执行前跳过。
- GREEN: python -X utf8 -m pytest tests/test_code_only_required_sql_contract.py -q -> PASS，证据 `evidence/maintenance-codeonly-required-sql-contract-v2-pytest.out.log`。
- GREEN: PowerShell Parser.ParseFile publish-int-ruoyi.ps1 -> PARSE_OK，证据 `evidence/maintenance-codeonly-required-sql-contract-v2-parse.txt`。
- 结论：v8 判废，下一轮重新构建 v9，禁止复用 v8 拼接后续环境。
