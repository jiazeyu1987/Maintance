# 20260703-codeonly-three-env-release execution log

REQUEST: 执行 IntRuoyi 不带数据完整三环境发布闭环，使用当前 int_main 已提交 HEAD，创建干净临时发布 worktree，测试服/正式服/备份服全部发布并验证。

BDD: code-only three-environment release -> Given 后端、前端、维护仓当前 int_main 已提交 HEAD 作为唯一发布输入，且主工作区脏内容不得进入发布包；When 在本轮专用干净临时发布 worktree 中执行 build-release、publish-test、mark-tested、promote-prod、promote-backup；Then 同一 releaseTag 的五个 operation 均为 SUCCESS，三环境运行态验证全部通过，manifest 为 code-only 且 sourceRepos dirty=false。
BDD: backup environment data mount verification -> Given 备份服发布必须显式使用 /mnt/intruoyi-data；When promote-backup 完成；Then .env IMAGE_TAG、镜像 tag、后端健康、前端 HTTP、PDF worker HTTP 和 /mnt/intruoyi-data 挂载全部验证通过。
GREEN: experience-preflight -> PASS, read and extracted gates from docs/experience-index.md, docs/release-build-preflight-lessons.md, docs/release-agent-checklist.md, D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md, D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md, D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md
GREEN: release-input-baseline -> PASS, target commits recorded; dirty main workspaces will be excluded by clean release worktrees.

## Previous task check

- `20260703-build-publish-test-again`：- 状态：已完成。

## Repository baseline

| repo | path | branch | commit | dirty | status |
| --- | --- | --- | --- | --- | --- |
| backend | `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` | `int_main` | `4ef9206881465189f06d4dd8db30c4bacf03b5d8` | true | M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/md/autocode/MesMdAutoCodeRecordServiceImpl.java<br> M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordDocParser.java<br> M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordParsedCell.java<br> M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordReportJsonBuilder.java<br> M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordReportLayoutCalibrator.java<br> M yudao-module-mes/src/main/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordRouteBRecognizer.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/md/autocode/MesMdAutoCodeRecordServiceImplTest.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordDocParserTest.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordJingxiTableStructureVerificationTest.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordReportJsonBuilderTest.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordReportLayoutCalibratorTest.java<br> M yudao-module-mes/src/test/java/cn/iocoder/yudao/module/mes/service/pro/batchrecordreport/MesProBatchRecordRouteBRecognizerTest.java<br>?? LOG_FILE_IS_UNDEFINED |
| frontend | `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` | `int_main` | `0587b626a86a570016a53dae350a4a4bbea2e81f` | true | ?? doc/tasks/20260703-edhr-remove-redundant-review-copy/<br>?? tests/e2e/edhr-remove-redundant-review-copy-static.spec.js |
| maintenance | `D:\ProjectPackage\Int\IntRuoyiMaintance` | `int_main` | `14fcac2349d79a33351dca1ed65d99bfe9b40982` | true | M doc/tasks/20260701-dcc-batch-recognition-five-workers/execution-log.md<br> M doc/tasks/20260701-rebuild-publish-all-after-fvm-message-fix/execution-log.md<br>?? config/runtime-control.local.before-20260701-205043.yaml<br>?? config/runtime-control.local.before-category-20260701-221522.yaml<br>?? config/runtime-control.local.before-fix3-20260703-001013.yaml<br>?? config/runtime-control.local.before-mes-scheduler-20260701-230707.yaml<br>?? config/runtime-control.local.before-nodata-evening-20260702-2151.yaml<br>?? config/runtime-control.local.before-nodata-evening-fix-20260702-2240.yaml<br>?? config/runtime-control.local.before-nodata-evening-fix2-20260702-2316.yaml<br>?? runtime/ |

- 2026-07-03 23:21:20 Task initialized.

## Worktree creation evidence - 2026-07-03 23:24:52 +08:00

GREEN: release-worktree-create -> PASS, created clean detached worktrees from planned committed HEADs.

| repo | worktree | commit | branch | dirty |
| --- | --- | --- | --- | --- |
| maintenance | $wtMaint | $maintHead | HEAD | false before local config copy; local config copy is release-runtime-only and gitignored |
| backend | $wtBackend | $backendHead | HEAD | false |
| frontend | $wtFrontend | $frontendHead | HEAD | false |

Runtime config copied into maintenance release worktree and points repo-root/frontend-root/ops-root/state-dir to this release worktree set.
## Runtime control build failure evidence - 2026-07-03 23:29:55 +08:00

BLOCKER: runtime-control-worktree-build -> pnpm blocked frontend build scripts (`ERR_PNPM_IGNORED_BUILDS` for esbuild/vue-demi), so `scripts/build.ps1` did not produce the maintenance jar.
Impact: release runtime control cannot be started from the clean maintenance worktree yet; build-release/publish-test/promote steps have not started.
Evidence file: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\runtime-control-worktree-build-failure-20260703.md`

## Preflight lesson update - 2026-07-03 23:30:47 +08:00

GREEN: release-preflight-lesson-update -> PASS, recorded pnpm approve-builds gate after runtime-control worktree build failure evidence.
- Updated: `docs/release-build-preflight-lessons.md`
- Updated: `docs/experience-index.md`

## Runtime control release worktree switch completed - 2026-07-03 23:30:47 +08:00

GREEN: runtime-control-worktree-start -> PASS, approved pnpm build scripts, rebuilt maintenance runtime control in release worktree, started 48181 from release worktree, and verified health UP.
- health: `{"status":"UP"}`
- jar: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- stdout log: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release\IntRuoyiMaintance\runtime-control-release.out.log`
- stderr log: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release\IntRuoyiMaintance\runtime-control-release.err.log`
- owner: `PID=5920 CMD="C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe" -jar D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`

## build-release preview - 2026-07-03 23:34:05 +08:00

GREEN: build-release-preview -> PASS, command includes code-only switches and expected test/backup host guards; no backup/restore/rollback action in preview.
- releaseTag: `release-20260703-2335-codeonly-three-env`
- preview arguments: `-Mode build-release -ReleaseTag release-20260703-2335-codeonly-three-env -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/IntRuoyiWorktrees/20260703-codeonly-three-env-release/ruoyi-vue-pro -FrontendRepoRoot D:/ProjectPackage/Int/IntRuoyiWorktrees/20260703-codeonly-three-env-release/yudao-ui-admin-vue3 -WebsiteRepo D:/ProjectPackage/Website -BackendRuntimeBaseMode offline-tar -BackendRuntimeBaseTarPath D:/ProjectPackage/Int/BaseImages/intruoyi-backend-runtime-base-2026.06.05-jre21-noble-docker29.2.1.tar -BackendRuntimeBaseTarSha256 5bcd568b46ba9f28bfa7ac8ee67e283aea95bd585a89842a14cc40827fa71603 -BackendRuntimeBaseImage intruoyi-backend-runtime-base:2026.06.05-jre21-noble-docker29.2.1 -BackendRuntimeBaseDigest sha256:b4f7d85f325665c3b372379e6d352c3c8be2d3a08add68ac0dc151f720160be7 -BackendRuntimeBaseVersion 2026.06.05-jre21-noble-docker29.2.1`

## build-release operation - 2026-07-03 23:49:28 +08:00

GREEN: build-release-operation -> PASS, operation `op-2026-07-03T153405744077400Z-02fbe71d-f709-4364-b21c-90821b63c934` completed SUCCESS for `release-20260703-2335-codeonly-three-env`.
- operation evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\build-release-op-2026-07-03T153405744077400Z-02fbe71d-f709-4364-b21c-90821b63c934-operation.json`
- log evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\build-release-op-2026-07-03T153405744077400Z-02fbe71d-f709-4364-b21c-90821b63c934-log.txt`

## manifest validation failure - 2026-07-03 23:51:34 +08:00

BLOCKER: release-manifest-validation -> generated manifest is missing required `sourceRepos`; this releaseTag cannot proceed to publish-test/promote.
- rejected releaseTag: `release-20260703-2335-codeonly-three-env`
- manifest evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\failed-manifest-missing-sourceRepos.json`
- failure summary: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\manifest-validation-failure-20260703.md`

## Manifest v1 validation - 2026-07-03 23:52:51 +08:00

GREEN: release-manifest-v1-validation -> PASS, repository validator/compact checks passed; Manifest v1 has publishScope=code-only, changeSet.component=intruoyi, sourceRepos backend/admin-frontend dirty=false with expected commits, and no data payload directories.
- releaseTag: `release-20260703-2335-codeonly-three-env`
- manifestV1: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260703-2335-codeonly-three-env\manifest.json`
- maintenance source: release runtime control and script path were verified from clean maintenance worktree HEAD `14fcac2349d79a33351dca1ed65d99bfe9b40982`; Manifest v1 sourceRepos schema records backend/admin-frontend only.
- correction: prior legacy `release-manifest.json` sourceRepos blocker is superseded by Manifest v1 validation.

## Manifest validator rerun - 2026-07-03 23:53:19 +08:00

GREEN: release-manifest-validator -> PASS, validator output captured after correcting parameter handling.
- validator evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\manifest-v1-validator-output.txt`

## publish-test preview - 2026-07-03 23:54:49 +08:00

GREEN: publish-test-preview -> PASS, deploy-release test command targets 172.30.30.58 and /opt/intruoyi/runtime; no prod/backup/restore/rollback action in preview.
- releaseTag: `release-20260703-2335-codeonly-three-env`
- preview arguments: `-Mode deploy-release -Environment test -ReleaseTag release-20260703-2335-codeonly-three-env -ServerHost 172.30.30.58 -ServerUser root -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/IntRuoyiWorktrees/20260703-codeonly-three-env-release/ruoyi-vue-pro -FrontendRepoRoot D:/ProjectPackage/Int/IntRuoyiWorktrees/20260703-codeonly-three-env-release/yudao-ui-admin-vue3 -WebsiteRepo D:/ProjectPackage/Website`

## publish-test operation - 2026-07-04 00:07:35 +08:00

GREEN: publish-test-operation -> PASS, operation `op-2026-07-03T155449725216100Z-adc5802d-1d2e-4199-8635-81110bf97774` completed SUCCESS for `release-20260703-2335-codeonly-three-env`.
- operation evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\publish-test-op-2026-07-03T155449725216100Z-adc5802d-1d2e-4199-8635-81110bf97774-operation.json`
- log evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\publish-test-op-2026-07-03T155449725216100Z-adc5802d-1d2e-4199-8635-81110bf97774-log.txt`

## test server verification final - 2026-07-04 00:08:47 +08:00

GREEN: publish-test-remote-verification -> PASS, verified test server .env IMAGE_TAG, backend/frontend actual image tags, backend health, frontend HTTP, and PDF worker HTTP.
- operation: `op-2026-07-03T155449725216100Z-adc5802d-1d2e-4199-8635-81110bf97774`
- backend image: `intruoyi-backend|intruoyi-backend:release-20260703-2335-codeonly-three-env|Up 3 minutes`
- frontend image: `intruoyi-frontend|intruoyi-frontend:release-20260703-2335-codeonly-three-env|Up 3 minutes`
- evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\test-server-verification-final.txt`

## 2026-07-04 00:12:50 +08:00 mark-tested 预览失败证据冻结

- BLOCKER: mark-tested-preview -> selectedRecoverySetCandidateId is required for action: mark-release-tested
- Failure evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\mark-tested-preview-failure-selectedRecoverySetCandidateId.json`
- 处理：先查维护仓 API/动作契约，补齐真实 recovery set 候选 ID 后重试；不手工标绿。

## 2026-07-04 00:33:58 +08:00 mark-tested 轮询失败证据冻结

- BLOCKER: mark-tested-poll -> operation not found before timeout: `op-2026-07-03T161333772184700Z-06061413-1db6-43a9-97e5-863ca79e0f97`
- 处理：直接查 runtime-control state-dir、operation 文件和日志，不假定成功。

## 2026-07-04 00:34:34 +08:00 mark-tested 成功证据补录

- Operation: `op-2026-07-03T161333772184700Z-06061413-1db6-43a9-97e5-863ca79e0f97` status=`SUCCESS`
- Operation evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\mark-tested-op-2026-07-03T161333772184700Z-06061413-1db6-43a9-97e5-863ca79e0f97-operation.json`
- Operation log: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\mark-tested-op-2026-07-03T161333772184700Z-06061413-1db6-43a9-97e5-863ca79e0f97-log.txt`
- GREEN: mark-tested -> SUCCESS

## 2026-07-04 00:34:34 +08:00 promote-prod

- Preview evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-prod-preview.json`
- Execute evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-prod-execute-response.json`
- Operation: `op-2026-07-03T163511316141200Z-89e50181-d9b3-4874-8c72-893e90ac8c48` status=`SUCCESS`
- Operation evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-prod-op-2026-07-03T163511316141200Z-89e50181-d9b3-4874-8c72-893e90ac8c48-operation.json`
- Operation log: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-prod-op-2026-07-03T163511316141200Z-89e50181-d9b3-4874-8c72-893e90ac8c48-log.txt`
- GREEN: promote-prod -> SUCCESS

## 2026-07-04 00:50:15 +08:00 正式服验证失败证据冻结

- BLOCKER: prod-verification -> backend health curl failed with connection refused on 127.0.0.1:48080.
- Diagnostic evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\prod-server-verification-failure-diagnostic.txt`
- stdout: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\prod-server-verification-failure-diagnostic.stdout.txt`
- stderr: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\prod-server-verification-failure-diagnostic.stderr.txt`
- 处理：先确认容器状态和日志，再决定是否等待重验或按真实错误处理；不继续备份服发布。

## 2026-07-04 00:51:04 +08:00 正式服验证（真实端口）

- Host: `172.30.30.57`
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\prod-server-verification-final.txt`
- .env IMAGE_TAG: `release-20260703-2335-codeonly-three-env`
- Backend image: `intruoyi-backend:release-20260703-2335-codeonly-three-env`
- Frontend image: `intruoyi-frontend:release-20260703-2335-codeonly-three-env`
- Backend health(host 48081): `{"status":"UP"}`
- Backend health(container 48080): `{"status":"UP"}`
- Frontend HTTP(host 8081): `200`
- PDF worker HTTP(host 8081/pdfjs/pdf.worker.mjs): `200`
- GREEN: prod-verification -> PASS

## 2026-07-04 01:06:41 +08:00 promote-backup

- Preview evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-backup-preview.json`
- Execute evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-backup-execute-response.json`
- Preview confirmed: `/mnt/intruoyi-data` / `/mnt/intruoyi-data/intruoyi-releases` / `/mnt/intruoyi-data/runtime-data` / `172.30.30.59` / `PROD` / `RequireTested`
- Operation: `op-2026-07-03T165324146656100Z-83717ddc-3a40-41f3-bb28-ae4b1e9d3dba` status=`SUCCESS`
- Operation evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-backup-op-2026-07-03T165324146656100Z-83717ddc-3a40-41f3-bb28-ae4b1e9d3dba-operation.json`
- Operation log: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\promote-backup-op-2026-07-03T165324146656100Z-83717ddc-3a40-41f3-bb28-ae4b1e9d3dba-log.txt`
- GREEN: promote-backup -> SUCCESS

## 2026-07-04 01:07:15 +08:00 备份服验证

- Host: `172.30.30.59`
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\backup-server-verification-final.txt`
- .env IMAGE_TAG: `release-20260703-2335-codeonly-three-env`
- Backend image: `intruoyi-backend:release-20260703-2335-codeonly-three-env`
- Frontend image: `intruoyi-frontend:release-20260703-2335-codeonly-three-env`
- Backend health(host 48081): `{"status":"UP"}`
- Backend health(container 48080): `{"status":"UP"}`
- Frontend HTTP(host 8081): `200`
- PDF worker HTTP(host 8081/pdfjs/pdf.worker.mjs): `200`
- Mount: `/mnt/intruoyi-data /dev/mapper/cl-home ext4   rw,relatime,seclabel,data=ordered`
- Path check: `EXISTS /mnt/intruoyi-data
EXISTS /mnt/intruoyi-data/intruoyi-releases
EXISTS /mnt/intruoyi-data/runtime-data
EXISTS /mnt/intruoyi-data/intruoyi-releases/release-20260703-2335-codeonly-three-env`
- GREEN: backup-verification -> PASS

## 2026-07-04 01:08:35 +08:00 运行控制台主路径恢复

- Stopped temp runtime-control process(es): `1`
- Started main runtime-control PID: `20628`
- Main jar: `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- Health: `{"status":"UP"}`
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\runtime-control-main-restore-verification.json`
- GREEN: runtime-control-main-restore -> PASS

## 2026-07-04 01:10:06 +08:00 运行控制台主路径最终复核更正

- Health: `{"status":"UP"}`
- Prior false negative: JSON 转义后的命令行匹配导致误判；直接命令行已确认主维护仓路径。
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\runtime-control-main-restore-final-check-corrected.json`
- GREEN: runtime-control-main-path-final-check -> PASS

## 2026-07-04 01:10:29 +08:00 临时发布 worktree 清理失败证据冻结

- BLOCKER: release-worktree-cleanup -> git worktree remove reported directory not empty for temp maintenance worktree.
- Boundary verified: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release`
- Inspection evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\temporary-release-worktree-cleanup-failure-inspection.json`
- 处理：确认残留均在本次临时发布目录内后再清理，不删除主工作区。

## 2026-07-04 01:12:09 +08:00 临时发布 worktree 清理仍失败

- BLOCKER: release-worktree-cleanup-final -> temp root still exists after reparse/.NET cleanup.
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\temporary-release-worktree-cleanup-final-retry.json`

## 2026-07-04 01:14:43 +08:00 临时发布 worktree 长路径最终清理

- Temp root: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release`
- Boundary verified: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release`
- Evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\temporary-release-worktree-cleanup-longpath-final.json`
- GREEN: release-worktree-cleanup-final -> PASS

## 2026-07-04 01:16:34 +08:00 最终收口验证

- GREEN: final-release-closeout -> PASS
- releaseTag: `release-20260703-2335-codeonly-three-env`
- Operations checked: build-release / publish-test / mark-tested / promote-prod / promote-backup all SUCCESS from evidence.
- Runtime verifications checked: test/prod/backup all PASS from evidence.
- task-closeout-cleanup preview: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\task-closeout-cleanup-preview.txt`
- Final closeout evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260703-codeonly-three-env-release\evidence\final-release-closeout-verification.json`
