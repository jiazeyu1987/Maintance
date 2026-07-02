# execution-log

BDD: build and publish test no-data -> Given committed backend/frontend release source and runtime-control is healthy, When building a no-data release package and publishing it to test, Then test server runs the new image tag with backend health UP and frontend HTTP 200.

GREEN: experience-preflight -> PASS, matched=PowerShell/release-build/server-access/release-backup-restore, scope=no-data build-release + publish-test only, target=172.30.30.58, old with-data operation will be stopped because user changed scope.

RED: build-preview-contract -> FAIL expected before preview validation, no-data build must include -SkipDatabaseSync/-SkipMinioSync and exclude prod/backup/restore/rollback.

GREEN: build-preview-contract -> PASS, releaseTag=release-20260702-0738-codeonly-test, arguments=-Mode build-release -ReleaseTag release-20260702-0738-codeonly-test -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler -WebsiteRepo D:/ProjectPackage/Website -BackendRuntimeBaseMode offline-tar -BackendRuntimeBaseTarPath D:/ProjectPackage/Int/BaseImages/intruoyi-backend-runtime-base-2026.06.05-jre21-noble-docker29.2.1.tar -BackendRuntimeBaseTarSha256 5bcd568b46ba9f28bfa7ac8ee67e283aea95bd585a89842a14cc40827fa71603 -BackendRuntimeBaseImage intruoyi-backend-runtime-base:2026.06.05-jre21-noble-docker29.2.1 -BackendRuntimeBaseDigest sha256:b4f7d85f325665c3b372379e6d352c3c8be2d3a08add68ac0dc151f720160be7 -BackendRuntimeBaseVersion 2026.06.05-jre21-noble-docker29.2.1

GREEN: build-release-start -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-01T235523602125100Z-ce23456f-d0f7-415a-a575-2e1ca7228f23

GREEN: build-release -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-01T235523602125100Z-ce23456f-d0f7-415a-a575-2e1ca7228f23, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260702-0738-codeonly-test\manifest.json, publishScope=code-only, no database dump or minio directory present

RED: publish-test-preview-request-shape -> FAIL, preview API rejected publish-test body with includeOnlyOffice/includeShowroomBuildPackage fields; retry with deploy minimal request body required by backend contract.

GREEN: publish-test-preview-contract -> PASS, releaseTag=release-20260702-0738-codeonly-test, minimalBody=true, target=172.30.30.58, arguments=-Mode deploy-release -Environment test -ReleaseTag release-20260702-0738-codeonly-test -ServerHost 172.30.30.58 -ServerUser root -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler -WebsiteRepo D:/ProjectPackage/Website; note BackupServerHost is inert shared config and Environment/ServerHost remain test-only.

GREEN: publish-test-start -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T001015631437900Z-571f3f40-9ade-41b1-b681-13abd4c035b6

GREEN: publish-test -> PASS, releaseTag=release-20260702-0738-codeonly-test, operation=op-2026-07-02T001015631437900Z-571f3f40-9ade-41b1-b681-13abd4c035b6

GREEN: remote-test-runtime-verification -> PASS, releaseTag=release-20260702-0738-codeonly-test, envImageTag=release-20260702-0738-codeonly-test, backendImage=intruoyi-backend:release-20260702-0738-codeonly-test, frontendImage=intruoyi-frontend:release-20260702-0738-codeonly-test, backendHealth=UP, frontendHttp=200, pdfWorkerHttp=200

GREEN: task-closeout-doc-update -> PASS, task marked COMPLETED at 2026-07-02 08:23:55 +08:00
