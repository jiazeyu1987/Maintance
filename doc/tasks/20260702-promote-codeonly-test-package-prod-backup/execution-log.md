# execution-log

BDD: promote tested package to prod and backup -> Given releaseTag release-20260702-0738-codeonly-test was built code-only and published to test successfully, When marking it tested and promoting the same releaseTag to prod and backup, Then prod and backup run the same backend/frontend image tag with backend health UP and frontend HTTP 200.

GREEN: experience-preflight -> PASS, matched=PowerShell/release-build/release-backup-restore/server-access/worktree-memory, scope=mark-tested + promote-prod + promote-backup for releaseTag release-20260702-0738-codeonly-test only.
GREEN: test-server-release-verification -> PASS, releaseTag=release-20260702-0738-codeonly-test, env/image/backend/frontend all match test server running state.

RED: mark-tested-preview-request-shape -> FAIL, preview API rejected mark-tested body with targetEnvironment; retry with minimal request body required by backend contract.

GREEN: restore-candidate-selection -> PASS, selectedRecoverySetCandidateId=restore:20260621-063218, recoverySetId=20260621-063218, recoverySetStatus=COMPLETE, manifestHash=6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66

GREEN: mark-tested-preview-contract -> PASS, releaseTag=release-20260702-0738-codeonly-test, selectedRecoverySetCandidateId=restore:20260621-063218, arguments=-Mode mark-tested -ReleaseTag release-20260702-0738-codeonly-test -TestConclusion æµè¯æåå¸éªè¯éè¿ï¼build-release ä¸ publish-test å SUCCESSï¼æµè¯æå½å IMAGE_TAG/åç«¯éå/åç«¯éååå¹é release-20260702-0738-codeonly-testï¼backend health=UPï¼frontend HTTP 200ã -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 -RecoverySetManifestHash 6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66 -RecoverySetProgramVersion release-20260620-current-head-prod-target-v7 -RecoverySetRedisPolicy CLEAR_AND_REBUILD -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler -WebsiteRepo D:/ProjectPackage/Website

GREEN: mark-tested-start -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T003519305152700Z-acc9b02b-d803-4e60-9dd7-74f9f670cca4

GREEN: mark-tested -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T003519305152700Z-acc9b02b-d803-4e60-9dd7-74f9f670cca4

GREEN: user-package-confirmation -> PASS, user confirmed using same package releaseTag=release-20260702-0738-codeonly-test; no rebuild or tag change allowed.

RED: promote-prod-preview-contract -> FAIL expected before preview validation, prod preview must use same releaseTag, RequireTested, ConfirmText PROD, ProdDryRunEvidencePath, and no backup/rollback/restore action.

GREEN: promote-prod-preview-contract -> PASS, releaseTag=release-20260702-0738-codeonly-test, arguments=-Mode deploy-release -Environment prod -ReleaseTag release-20260702-0738-codeonly-test -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260702-0738-codeonly-test-preflight-release-dry-run.json -ServerHost 172.30.30.57 -ServerUser root -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -ProdServerHost 172.30.30.57 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler -WebsiteRepo D:/ProjectPackage/Website

GREEN: promote-prod-start -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T003717687464900Z-3af49870-1fdc-4484-be01-19d90747ce36

GREEN: promote-prod -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T003717687464900Z-3af49870-1fdc-4484-be01-19d90747ce36

GREEN: prod-runtime-verification -> PASS, releaseTag=release-20260702-0738-codeonly-test, envImageTag=release-20260702-0738-codeonly-test, backendImage=intruoyi-backend:release-20260702-0738-codeonly-test, frontendImage=intruoyi-frontend:release-20260702-0738-codeonly-test, backendHealth=UP, frontendHttp=200, pdfWorkerHttp=200

RED: promote-backup-preview-contract -> FAIL expected before preview validation, backup preview must use same releaseTag, RequireTested, ConfirmText PROD, backup host 172.30.30.59 and /mnt/intruoyi-data paths, and no prod/rollback/restore action.

GREEN: promote-backup-preview-contract -> PASS, releaseTag=release-20260702-0738-codeonly-test, arguments=-Mode deploy-release -Environment backup -ReleaseTag release-20260702-0738-codeonly-test -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -ServerUser root -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home -RemoteMinioContainer intruoyi-minio -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler -WebsiteRepo D:/ProjectPackage/Website

GREEN: promote-backup-start -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T005123161454400Z-1f1b4219-b991-43da-b37a-8d5e5e14a9b2

GREEN: promote-backup -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T005123161454400Z-1f1b4219-b991-43da-b37a-8d5e5e14a9b2

GREEN: backup-runtime-verification -> PASS, releaseTag=release-20260702-0738-codeonly-test, envImageTag=release-20260702-0738-codeonly-test, backendImage=intruoyi-backend:release-20260702-0738-codeonly-test, frontendImage=intruoyi-frontend:release-20260702-0738-codeonly-test, backendHealth=UP, frontendHttp=200, pdfWorkerHttp=200, dataMount=/dev/mapper/cl-home

GREEN: release-status-three-env-verification -> PASS, testCurrentReleaseTag=release-20260702-0738-codeonly-test, prodCurrentReleaseTag=release-20260702-0738-codeonly-test, backupCurrentReleaseTag=release-20260702-0738-codeonly-test

GREEN: task-closeout-doc-update -> PASS, task marked COMPLETED at 2026-07-02 09:07:31 +08:00
