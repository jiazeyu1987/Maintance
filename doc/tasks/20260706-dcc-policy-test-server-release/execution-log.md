# DCC 覆盖策略测试服发布执行日志

BDD: 测试服发布 DCC 覆盖策略 -> Given DCC 批量识别覆盖策略已在后端与前端提交 When 使用专用临时发布 worktree 构建并发布到测试服 Then 测试服运行态必须匹配本次 releaseTag 且页面展示三种覆盖策略。

GREEN: experience-preflight -> PASS, 已读取维护仓 release-agent-checklist、release-build-preflight-lessons，以及业务仓 server-access、login-access、release-backup-restore；用户已明确授权测试服操作，正式服/备份服不在本次范围。
## M2 临时发布 worktree

- GREEN: release-worktree-create -> PASS, base=D:\ProjectPackage\Int\IntRuoyiWorktrees\20260706-dcc-policy-test-server-release
- backend=D:\ProjectPackage\Int\IntRuoyiWorktrees\20260706-dcc-policy-test-server-release\ruoyi-vue-pro commit=991a4c9264 dirty=False
- frontend=D:\ProjectPackage\Int\IntRuoyiWorktrees\20260706-dcc-policy-test-server-release\yudao-ui-admin-vue3 commit=093cc1a9de dirty=False
- maintenance=D:\ProjectPackage\Int\IntRuoyiWorktrees\20260706-dcc-policy-test-server-release\IntRuoyiMaintance commit=63626395a1 dirty=False

## M3 构建前置门禁

- GREEN: backend-dcc-tests -> PASS
- GREEN: backend-migration-policy-gate -> PASS
- GREEN: backend-dcc-sql-tests -> PASS
- GREEN: frontend-dcc-static-and-eslint -> PASS
- GREEN: maintenance-release-script-tests -> PASS

## M3 门禁阻塞

- BLOCKER: backend-migration-policy-gate -> FAIL, 目标后端提交 991a4c9264 中 sql/mysql/20260705_showroom_legacy_product_code_manual_decision_template.sql 缺少 release-migration 元数据；发布包构建已停止，未执行测试服发布。
- 影响：必须先修复 SQL 发布契约并生成新的已提交后端目标，再重建临时发布 worktree；不得跳过 migration gate 或手工改测试库绕过。

- INSPECT: manual-template-root-cause -> sql/mysql/20260705_showroom_legacy_product_code_manual_decision_template.sql 是 REVIEW ONLY/Do not execute directly 模板，根因是误放入可发布 SQL 目录。

RED: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> FAIL, 可发布 SQL 目录包含人工确认模板或缺少 release-migration 元数据，发布构建必须阻塞。
GREEN: python -X utf8 -m pytest script/tests/test_showroom_legacy_product_code_name_backfill_sql.py script/tests/test_showroom_manual_legacy_mapping_generator.py -q -> PASS, 8 passed。
GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --sql-file <tracked sql files> -> PASS, 已跟踪发布 SQL 契约通过；未跟踪草稿 SQL 不进入本次发布输入。
## M3 发布 worktree 门禁修复完成

- GREEN: scoped-release-contract-fix -> PASS, 发布 worktree 保留 DCC 基线已有展厅 SQL，排除后续 current-empty SQL。
- GREEN: release-worktree-showroom-tests -> PASS, manual/template 相关测试通过。
- GREEN: release-worktree-required-sql-gate -> PASS, 本次发布所需 SQL 通过 migration policy gate。

## M3 发布脚本真实门禁

- GREEN: release-script-mysql-gate -> PASS, 直接运行发布脚本同口径 sql/mysql 迁移门禁通过。
- GREEN: release-script-showroom-gate -> PASS, 发布脚本列入的 sql/showroom 文件迁移门禁通过。

## M3 build-release 首次失败

- RED: publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260706-1130-dcc-policy-test -> FAIL, Maven 与前端构建成功，但 Dockerfile.backend 要求 yudao-server-exec.jar，发布脚本 Docker context 未放入该文件，manifest 未生成，未发布测试服。

RED: publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260706-1130-dcc-policy-test -> FAIL, Dockerfile.backend 复制 `yudao-server-exec.jar`，但发布脚本 Docker context 仍准备 `yudao-server.jar`，后端镜像构建失败。GREEN: python -X utf8 -m pytest script/tests/test_publish_int_ruoyi_to_test_tooling.py script/tests/test_runtime_control_ops_scripts.py -q -> PASS, 发布脚本与 Dockerfile 后端 jar 契约统一为 yudao-server-exec.jar。

## M3 发布脚本 Jar 契约修复

- RED: build-release-backend-docker-context -> FAIL, Dockerfile.backend 复制 yudao-server-exec.jar，发布脚本曾放入 yudao-server.jar，导致后端镜像构建失败。
- GREEN: release-worktree-publish-tooling-tests -> PASS, 干净发布 worktree 中发布脚本契约测试通过，后端 jar 契约统一为 yudao-server-exec.jar。
- NOTE: 主仓同一测试曾被未跟踪草稿 SQL sql/mysql/20260705_showroom_legacy_product_code_auto_confirmable_draft.sql 干扰；该草稿未进入本次发布 worktree。

## M3 build-release 重跑

- GREEN: build-release-v2 -> PASS, releaseTag=release-20260706-1200-dcc-policy-test-v2，code-only 发布包构建成功。
- GREEN: manifest-sourceRepos-v2 -> PASS, manifest releaseTag/publishScope/sourceRepos dirty=false 且 backend/frontend commit 与发布 worktree 一致。

## M3 build-release NAS 上传阻塞

- RED: build-release-v2-finalize -> FAIL, 本地发布包、镜像 tar、manifest 已生成并校验通过，但 build-release 最后上传 NAS 时缺 NasConfigPath，尚不能判定 build-release 完整成功。

- GREEN: build-release -> PASS，2026-07-06 12:24:15 +08:00，发布包 release-20260706-1200-dcc-policy-test-v2 已上传 NAS：Backup/ReleasePackage/release-20260706-1200-dcc-policy-test-v2。

- RED: deploy-release -> FAIL，2026-07-06 12:25:14 +08:00，首次部署缺少 -TestServerHost，按脚本发布目标绑定契约补充参数后重试。

- RED: showroom-name-backfill-sql-syntax -> FAIL，2026-07-06 12:42:05 +08:00，测试服部署执行 sql/mysql/20260705_showroom_legacy_product_code_name_backfill.sql 时发现 6 行产品名称续行未注释，被 MySQL 当作语句解析。
- RED: python -X utf8 -m pytest script/tests/test_showroom_legacy_product_code_name_backfill_sql.py -q -> FAIL，新增裸文本行门禁捕获 line 181/222/243/470/511/532。
- GREEN: showroom-name-backfill-sql-syntax -> PASS，2026-07-06 12:42:07 +08:00，6 行产品名称续行已改为注释，主仓与发布 worktree 回归测试及发布 SQL 门禁通过。

- GREEN: git-commit-sql-syntax-fix -> PASS，2026-07-06 12:42:35 +08:00，已设置 TDD_TASK_DIR 并分别提交主仓与发布 worktree 的 SQL 裸文本修复。

- GREEN: build-release-v3 -> PASS，2026-07-06 12:58:50 +08:00，releaseTag=release-20260706-1305-dcc-policy-test-v3，SQL 裸文本修复已进入发布包，NAS 上传完成，manifest sourceRepos dirty=false。

- GREEN: deploy-release-v3 -> PASS，2026-07-06 13:06:40 +08:00，测试服已部署 releaseTag=release-20260706-1305-dcc-policy-test-v3。

- GREEN: stale-v2-release-lock-cleanup -> PASS，2026-07-06 13:07:47 +08:00，已将测试服 v2 失败部署遗留 RUNNING lock/migration 标记为 FAILED，准备重跑 v3 部署。

- GREEN: deploy-release-v3-retry -> PASS，2026-07-06 13:21:39 +08:00，清理 v2 失败锁后测试服 v3 部署完成，releaseTag=release-20260706-1305-dcc-policy-test-v3。

- GREEN: dcc-policy-dialog-real-e2e -> PASS，2026-07-06 13:27:03 +08:00，测试服真实页面 /dcc/controlled-file/browser 打开批量识别弹窗，展示三种覆盖策略，默认选中跳过已有记录；脚本未点击开始识别。
```json
```

- RED: dcc-policy-dialog-real-e2e -> FAIL，2026-07-06 13:27:44 +08:00，首次只读弹窗脚本点击按钮后未出现确认弹窗，需抓取页面状态后修正验证路径；此前同条 GREEN 记录作废。

- GREEN: dcc-policy-dialog-real-e2e -> PASS，2026-07-06 13:32:40 +08:00，测试服真实页面 /dcc/controlled-file/browser 选中 DCC E2E Documents 后打开批量识别弹窗，展示三种覆盖策略，默认选中跳过已有记录；脚本未点击开始识别。
```json
{
  "status": "PASS",
  "url": "http://172.30.30.58:8081/dcc/controlled-file/browser?pageNo=1&pageSize=10&scope=current&directoryId=906200",
  "selectedDirectory": "DCC E2E Documents",
  "dialogTitle": "识别当前文件夹及子文件夹",
  "policies": [
    "跳过已有记录",
    "跳过成功，重试失败和未识别",
    "覆盖全部已有值"
  ],
  "defaultPolicy": "跳过已有记录",
  "note": "只打开确认弹窗并读取选项，未点击开始识别。"
}
```

- GREEN: task-complete -> PASS，2026-07-06 13:34:07 +08:00，测试服 v3 运行态与 DCC 覆盖策略真实页面验证完成；未执行 mark-tested / 正式服 / 备份服操作。

- GREEN: closeout-status-marker -> PASS，2026-07-06 13:35:17 +08:00，任务文档补充 Status: completed 供清理门禁识别。
