# execution-log

BDD: build and publish test no-data evening -> Given current committed backend/frontend release source and runtime-control is healthy, When building a no-data release package and publishing it to test, Then test server runs the new image tag with backend health UP and frontend HTTP 200.

GREEN: experience-preflight -> PASS, matched=PowerShell/release-build/server-access/release-backup-restore/worktree-memory, scope=no-data build-release + publish-test only, target=172.30.30.58.
GREEN: release-worktree-create -> PASS, backendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2151-nodata-evening, backendCommit=f87b8485ea992674727ee7b32b96ca07a365e70b, frontendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2151-nodata-evening, frontendCommit=4decbf980d55f01ab64ca6c46b79fe62d9ab3071, branch=int_main/int_main.

GREEN: runtime-control-config-update -> PASS, repo-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2151-nodata-evening, frontend-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2151-nodata-evening.
RED: build-preview-contract -> FAIL, initial request with targetEnvironment rejected as expected by current backend contract.

GREEN: build-preview-contract -> PASS, releaseTag=release-20260702-2151-nodata-evening, arguments=-Mode build-release -ReleaseTag release-20260702-2151-nodata-evening -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260702-2151-nodata-evening -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260702-2151-nodata-evening -WebsiteRepo D:/ProjectPackage/Website -BackendRuntimeBaseMode offline-tar -BackendRuntimeBaseTarPath D:/ProjectPackage/Int/BaseImages/intruoyi-backend-runtime-base-2026.06.05-jre21-noble-docker29.2.1.tar -BackendRuntimeBaseTarSha256 5bcd568b46ba9f28bfa7ac8ee67e283aea95bd585a89842a14cc40827fa71603 -BackendRuntimeBaseImage intruoyi-backend-runtime-base:2026.06.05-jre21-noble-docker29.2.1 -BackendRuntimeBaseDigest sha256:b4f7d85f325665c3b372379e6d352c3c8be2d3a08add68ac0dc151f720160be7 -BackendRuntimeBaseVersion 2026.06.05-jre21-noble-docker29.2.1.

GREEN: build-release-start -> PASS, releaseTag=release-20260702-2151-nodata-evening, operation=op-2026-07-02T135829207129300Z-6f5119c6-67c2-47c9-9de7-c1fb276781b4.

GREEN: build-release -> PASS, releaseTag=release-20260702-2151-nodata-evening, operation=op-2026-07-02T135829207129300Z-6f5119c6-67c2-47c9-9de7-c1fb276781b4, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260702-2151-nodata-evening\manifest.json, sourceRepos=backend:HEAD:f87b8485ea992674727ee7b32b96ca07a365e70b:dirty=False; admin-frontend:HEAD:4decbf980d55f01ab64ca6c46b79fe62d9ab3071:dirty=False, no database/minio dirs present.

GREEN: publish-test-preview-contract -> PASS, releaseTag=release-20260702-2151-nodata-evening, arguments=-Mode deploy-release -Environment test -ReleaseTag release-20260702-2151-nodata-evening -ServerHost 172.30.30.58 -ServerUser root -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1 -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260702-2151-nodata-evening -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260702-2151-nodata-evening -WebsiteRepo D:/ProjectPackage/Website.

GREEN: publish-test-start -> PASS, releaseTag=release-20260702-2151-nodata-evening, operation=op-2026-07-02T141345993699500Z-bfbbb8ce-aad0-473e-b268-fc1c9f95a3ae.

BLOCKER: publish-test -> status=FAILED, operation=op-2026-07-02T141345993699500Z-bfbbb8ce-aad0-473e-b268-fc1c9f95a3ae, summary=å½ä»¤éåºç é 0: 1, logTail=260626_showroom_product_current_bu_normalization.sql', 'ff9fa70b19534d88e345ceb2c8039083a1c7a12604c1ca16fe8a54e7160ff519', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260618_mes_edhr_flow_intervention_log', '20260618_mes_edhr_flow_intervention_log.sql', '77a044d267610ae3bbc2ef7311ddd63c01942d053d81fff1e25fbf9efbf70925', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260618_post_release_role_e2e_gate_smoke_contract', '20260618_post_release_role_e2e_gate_smoke_contract.sql', 'd4ae726feba4f94acfb1cf6f28498583fe35c4f94d2b159b7aba6d96d6202a53', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260620_srm_d10_1_tender', '20260620_srm_d10_1_tender.sql', 'b4d0adcf04542d41c8421279d15e285a15039c27e471552b6ab68657b1e180a0', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260621_srm_phase3_purchase_order', '20260621_srm_phase3_purchase_order.sql', '02a5877f6d4e55c9afa8b2dc2b4aed117bd61317d43e391c3b63ef9a6f620991', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260626_mes_edhr_flow_intervention_runtime', '20260626_mes_edhr_flow_intervention_runtime.sql', '5a7112b9dd127a81bd22313a70bb8495a148ae1dbcb9146a0a7c62c9d168de36', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260619_post_release_role_e2e_gate_smoke_username_fix', '20260619_post_release_role_e2e_gate_smoke_username_fix.sql', 'f0c21644fd0f078b280744bd10ee09a5329d2c695d31332971fbf878155d3095', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260620_srm_d9_1_contract', '20260620_srm_d9_1_contract.sql', '4520438739426b5917dbe1cdbd6fbef43245983a2675c2f0c87058ffbe051d71', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260621_srm_phase45_simulated_execution', '20260621_srm_phase45_simulated_execution.sql', 'a41369e2f5406d0868cd164672fa2a5bdbbd644eb936434b1c3cd714e31264d0', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix', '20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix.sql', '8f98d9df5c03b48903aecf7baa0876f69d919c82d1f939790eed71e5e4bbfaad', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260628_srm_t6_nas_locator', '20260628_srm_t6_nas_locator.sql', '2a0792284179479272b68f4871d2bd4afd3db59abd3c538d266cf6749aaabad1', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix', '20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix.sql', 'b90028109c29d054598952b65c04e17fe8e7f6170d2ab3b0c1e604fa926a554b', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260701_srm_t6_nas_locator_blacklist_config', '20260701_srm_t6_nas_locator_blacklist_config.sql', '2e59012517b267fe0a6060ae57149b96342509459f819097d9f2926ff2a4c3fd', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix', '20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix.sql', 'c0d37b742489ad4cc397f557618ababcfd1a600f5e18b69804f9fc0f0ce167b6', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260619_post_release_role_e2e_gate_smoke_route_900026_line_fix', '20260619_post_release_role_e2e_gate_smoke_route_900026_line_fix.sql', '121858c6276712b0afda85f212b7df11dddfbb5446bdca77a5ffd4fc9e4d4720', 'test', 'SKIPPED_ALREADY_APPLIED', NOW(), CASE WHEN 'SKIPPED_ALREADY_APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Skipping required database SQL outside target environment: 20260625_dcc_fvm_matrix_retain_other_completion
[INFO] Applying required database SQL: 20260513_dcc_base_schema.sql
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 test -f '/var/lib/docker/intruoyi-releases/release-20260702-2151-nodata-evening/required-sql/20260513_dcc_base_schema.sql' && echo REQUIRED_SQL_EXISTS
REQUIRED_SQL_EXISTS
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260513_dcc_base_schema', '20260513_dcc_base_schema.sql', 'c33898c52a5cd6321e2205ba3c51095bd0d6c4254efe83050c5792856be925b7', 'test', 'RUNNING', NOW(), CASE WHEN 'RUNNING' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat '/var/lib/docker/intruoyi-releases/release-20260702-2151-nodata-evening/required-sql/20260513_dcc_base_schema.sql' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260513_dcc_base_schema', '20260513_dcc_base_schema.sql', 'c33898c52a5cd6321e2205ba3c51095bd0d6c4254efe83050c5792856be925b7', 'test', 'APPLIED', NOW(), CASE WHEN 'APPLIED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Applying required database SQL: 20260515_dcc_runtime_schema_repair.sql
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 test -f '/var/lib/docker/intruoyi-releases/release-20260702-2151-nodata-evening/required-sql/20260515_dcc_runtime_schema_repair.sql' && echo REQUIRED_SQL_EXISTS
REQUIRED_SQL_EXISTS
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260515_dcc_runtime_schema_repair', '20260515_dcc_runtime_schema_repair.sql', '2f922ef40a5947d572a751afd909005c350aafc61f60106a469ed6d7af48fe1c', 'test', 'RUNNING', NOW(), CASE WHEN 'RUNNING' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat '/var/lib/docker/intruoyi-releases/release-20260702-2151-nodata-evening/required-sql/20260515_dcc_runtime_schema_repair.sql' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
mysql: [Warning] Using a password on the command line interface can be insecure.
ERROR 1644 (45000) at line 87: DCC category lifecycle_stage backfill incomplete
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 ruoyi-vue-pro
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('release-20260702-2151-nodata-evening', '20260515_dcc_runtime_schema_repair', '20260515_dcc_runtime_schema_repair.sql', '2f922ef40a5947d572a751afd909005c350aafc61f60106a469ed6d7af48fe1c', 'test', 'FAILED', NOW(), CASE WHEN 'FAILED' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('Command failed with exit code 1: ssh
mysql: [Warning] Using a password on the command line interface can be insecure.
ERROR 1644 (45000) at line 87: DCC category lifecycle_stage backfill incomplete', ''), 'release-20260702-2151-nodata-evening', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
SQL
mysql: [Warning] Using a password on the command line interface can be insecure.
[INFO] Run: ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@172.30.30.58 cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro | grep '^LOCK_RELEASED$'
UPDATE infra_release_operation_lock
SET status = 'FAILED',
    finished_at = NOW(),
    error_message = NULLIF('Command failed with exit code 1: ssh
mysql: [Warning] Using a password on the command line interface can be insecure.
ERROR 1644 (45000) at line 87: DCC category lifecycle_stage backfill incomplete', ''),
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = 'test'
  AND operation_id = 'test-release-20260702-2151-nodata-evening'
  AND status = 'RUNNING';
SELECT CASE WHEN status = 'FAILED' THEN 'LOCK_RELEASED' ELSE CONCAT('LOCK_RELEASE_FAILED:', operation_id, ':', status) END
FROM infra_release_operation_lock
WHERE target_environment = 'test';
SQL
LOCK_RELEASED
mysql: [Warning] Using a password on the command line interface can be insecure.
Command failed with exit code 1: ssh
mysql: [Warning] Using a password on the command line interface can be insecure.
ERROR 1644 (45000) at line 87: DCC category lifecycle_stage backfill incomplete
ï¿½ï¿½ï¿½ï¿½Î»ï¿½ï¿½ D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1:1023 ï¿½Ö·ï¿½: 9
+         throw "Command failed with exit code $($result.ExitCode): ssh ...
+         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (Command failed ...fill incomplete:String) [], RuntimeException
    + FullyQualifiedErrorId : Command failed with exit code 1: ssh
mysql: [Warning] Using a password on the command line interface can be insecure.
ERROR 1644 (45000) at line 87: DCC category lifecycle_stage backfill incomplete
 
ERROR: å½ä»¤éåºç é 0: 1


BLOCKER: publish-test -> required SQL failed at 20260515_dcc_runtime_schema_repair.sql line 87, reason=DCC category lifecycle_stage backfill incomplete; read-only root-cause query started.

GREEN: publish-failure-readonly-db-query -> PASS, queried dcc_file_category lifecycle_stage gaps through intruoyi-mysql container.

RED: mvn -pl yudao-module-dcc -Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages test -> FAIL, expected missing QMSFC/CODEX legacy category lifecycle mapping. exit=1

BLOCKER: qmsfc-lifecycle-test -> FAIL, exit=1

GREEN: mvn -pl yudao-module-dcc -Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages test -> PASS

GREEN: python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql -> PASS

GREEN: backend-commit -> PASS, commit=f87b8485ea992674727ee7b32b96ca07a365e70b, message=任务: 修复DCC分类生命周期发布门禁

GREEN: backend-commit -> PASS, commit=f87b8485ea992674727ee7b32b96ca07a365e70b, message=任务: 修复DCC分类生命周期发布门禁

GREEN: mvn -pl yudao-module-dcc -Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages test -> PASS

GREEN: python -X utf8 -m pytest script/tests/test_dcc_category_lifecycle_stage_sql.py -> PASS

GREEN: python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql -> PASS

GREEN: backend-commit -> PASS, commit=989082b5d588265c62ebd3dfe5a267ff1b6fd159, message=任务: 修复DCC分类生命周期发布门禁

GREEN: release-worktree-recreate-after-sql-fix -> PASS, backendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2240-nodata-evening-fix, backendCommit=989082b5d588265c62ebd3dfe5a267ff1b6fd159, frontendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2240-nodata-evening-fix, frontendCommit=aaa3e204c8fdd5df5725f7d67bead4cf80b22b09.

GREEN: runtime-control-config-update-after-sql-fix -> PASS, repo-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2240-nodata-evening-fix, frontend-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2240-nodata-evening-fix.

GREEN: runtime-control-restart-after-sql-fix -> PASS, pid=24468, config=D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml.

GREEN: rebuild-preview-contract -> PASS, releaseTag=release-20260702-2240-nodata-evening-fix, arguments=-Mode build-release -ReleaseTag release-20260702-2240-nodata-evening-fix -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 -NasServer 172.30.30.4 -NasShare ITå±äº« -NasReleaseRoot Backup/ReleasePackage -BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260702-2240-nodata-evening-fix -FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260702-2240-nodata-evening-fix -WebsiteRepo D:/ProjectPackage/Website -BackendRuntimeBaseMode offline-tar -BackendRuntimeBaseTarPath D:/ProjectPackage/Int/BaseImages/intruoyi-backend-runtime-base-2026.06.05-jre21-noble-docker29.2.1.tar -BackendRuntimeBaseTarSha256 5bcd568b46ba9f28bfa7ac8ee67e283aea95bd585a89842a14cc40827fa71603 -BackendRuntimeBaseImage intruoyi-backend-runtime-base:2026.06.05-jre21-noble-docker29.2.1 -BackendRuntimeBaseDigest sha256:b4f7d85f325665c3b372379e6d352c3c8be2d3a08add68ac0dc151f720160be7 -BackendRuntimeBaseVersion 2026.06.05-jre21-noble-docker29.2.1.

GREEN: rebuild-release-start -> PASS, releaseTag=release-20260702-2240-nodata-evening-fix, operation=op-2026-07-02T143945123221100Z-7991466d-c09e-40ca-9b06-d497f7141dcf.

GREEN: rebuild-release-complete -> PASS, operation=op-2026-07-02T143945123221100Z-7991466d-c09e-40ca-9b06-d497f7141dcf, releaseTag=release-20260702-2240-nodata-evening-fix, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260702-2240-nodata-evening-fix\manifest.json, publishScope=code-only, sourceRepos dirty=false, dataDirs absent.
GREEN: publish-test-preview-contract -> PASS, releaseTag=release-20260702-2240-nodata-evening-fix, target=172.30.30.58, remoteDir=/opt/intruoyi/runtime, no prod/backup/rollback action.
GREEN: publish-test-start -> PASS, releaseTag=release-20260702-2240-nodata-evening-fix, operation=op-2026-07-02T145759644222300Z-0554b4e6-1388-42a6-8237-32ee512f7057.
BLOCKER: publish-test -> required SQL failed at 20260515_dcc_runtime_schema_repair.sql line 106, reason=Invalid use of NULL value; remaining null lifecycle categories are INTAUTH-* (48) and NASCAT-* (99).
RED: mvn -pl yudao-module-dcc -Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages test -> FAIL, expected missing INTAUTH/NASCAT legacy category lifecycle mapping. exit=1
RED: python -X utf8 -m pytest script/tests/test_dcc_category_lifecycle_stage_sql.py -> FAIL, expected missing INTAUTH/NASCAT SQL tokens. exit=1
RED: mvn -pl yudao-module-dcc '-Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages' test -> FAIL, expected missing INTAUTH/NASCAT legacy category lifecycle mapping. exit=1
GREEN: mvn -pl yudao-module-dcc '-Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest#mysqlRuntimeRepairSchemaShouldBackfillLegacyQmsfcAndE2eCategoryStages' test -> PASS
GREEN: python -X utf8 -m pytest script/tests/test_dcc_category_lifecycle_stage_sql.py -> PASS
GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS
GREEN: remote-dcc-lifecycle-readonly-coverage -> PASS, INTAUTH/NASCAT/QMSFC/CODEX mapping leaves 0 lifecycle_stage gaps before NOT NULL alter.
GREEN: backend-commit -> PASS, commit=44c8253a7fb1a8ee432ec11f3870d7756a7d12a3, message=任务: 补齐DCC历史分类生命周期映射
GREEN: backend-commit -> PASS, commit=05423754a91780c87083d9d645e179fe3288cdbc, message=任务: 补齐DCC历史分类生命周期映射
GREEN: backend-commit-scope-repair -> PASS, reset mixed-scope commit and recommitted DCC-only lifecycle mapping, commit=fecc851406ded8cfaaa19de64dbc21f3c24c1462.
GREEN: release-worktree-recreate-after-intauth-nascat-fix -> PASS, backendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2316-nodata-evening-fix2, backendCommit=fecc851406ded8cfaaa19de64dbc21f3c24c1462, frontendWorktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2316-nodata-evening-fix2, frontendCommit=5b24c21fc4b5d1cd70cf9ab2ad747676a8e9edfb.
GREEN: runtime-control-config-update-after-intauth-nascat-fix -> PASS, repo-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2316-nodata-evening-fix2, frontend-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2316-nodata-evening-fix2.
GREEN: runtime-control-config-yaml-repair-fix2 -> PASS, repo-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260702-2316-nodata-evening-fix2, frontend-root=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2316-nodata-evening-fix2.
GREEN: runtime-control-start-fix2 -> PASS, pid=64908, script=D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\start.ps1.
GREEN: rebuild-preview-contract-fix2 -> PASS, releaseTag=release-20260702-2316-nodata-evening-fix2, includes -SkipDatabaseSync -SkipMinioSync, target test host 172.30.30.58.
GREEN: rebuild-release-start-fix2 -> PASS, releaseTag=release-20260702-2316-nodata-evening-fix2, operation=op-2026-07-02T152901793738600Z-b8a09402-567e-49cb-965b-a0ae98699775.
GREEN: rebuild-release-complete-fix2 -> PASS, operation=op-2026-07-02T152901793738600Z-b8a09402-567e-49cb-965b-a0ae98699775, releaseTag=release-20260702-2316-nodata-evening-fix2, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260702-2316-nodata-evening-fix2\manifest.json, publishScope=code-only, sourceRepos dirty=false, dataDirs absent.
GREEN: publish-test-preview-contract-fix2 -> PASS, releaseTag=release-20260702-2316-nodata-evening-fix2, target=172.30.30.58, remoteDir=/opt/intruoyi/runtime, no prod/backup/rollback action.
GREEN: publish-test-start-fix2 -> PASS, releaseTag=release-20260702-2316-nodata-evening-fix2, operation=op-2026-07-02T154941189790700Z-5c394fc0-0748-46fe-bfec-517ee25af9a2.
BLOCKER: publish-test -> required SQL failed at 20260515_dcc_runtime_schema_repair.sql line 120, reason=Invalid use of NULL value; checking all rows including deleted categories before NOT NULL alter.

## 2026-07-03 00:08:06 +08:00 DCC 已删除历史分类生命周期迁移修复
- BDD: 已删除历史分类归档行归一化 -> Given 测试库存在 deleted=1 且 lifecycle_stage 为空的 DCC 历史分类行 / When 发布迁移将 dcc_file_category.lifecycle_stage 改为 NOT NULL / Then 迁移先将已删除历史分类归一化为 TRANSFER，再执行全表非空门禁，失败时明确报错。
- RED: python -X utf8 -m pytest script/tests/test_dcc_category_lifecycle_stage_sql.py -> FAIL，缺少 WHERE `deleted` <> 0 的已删除历史分类归一化契约。
- 修复: sql/mysql/20260515_dcc_runtime_schema_repair.sql 在 ALTER TABLE dcc_file_category MODIFY lifecycle_stage NOT NULL 前补充已删除历史分类 TRANSFER 归一化，并新增全表 ensure_dcc_category_lifecycle_stage_not_null_ready 门禁。
- GREEN: python -X utf8 -m pytest script/tests/test_dcc_category_lifecycle_stage_sql.py -> PASS，2 passed。
- GREEN: mvn -pl yudao-module-dcc "-Dtest=cn.iocoder.yudao.module.dcc.DccBaseSchemaTest" test -> PASS，24 tests, 0 failures, 0 errors。
- GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS，238 migrations。
- 远端只读确认: 测试库剩余 lifecycle_stage 空值均为 deleted=1 历史归档行，共 147 条；活动行为空数为 0。
## 2026-07-03 00:09:26 +08:00 无数据发布 fix3 worktree 准备
- releaseTag: $releaseTag
- backend worktree: $backendWt
- backend target commit: $backendCommit
- frontend worktree: $frontendWt
- frontend target commit: $frontendCommit
- 验证: 两个发布 worktree 均为目标提交且 git status --porcelain 为空。
## 2026-07-03 00:14:04 +08:00 runtime-control YAML 修复并切换 fix3 worktree
- releaseTag: release-20260703-0009-nodata-evening-fix3
- 修复: runtime-control.local.yaml 的 repo-root/frontend-root 缩进恢复到 runtime-control 层级。
- runtime-control PID: 76164
- GREEN: Invoke-RestMethod http://127.0.0.1:48181/actuator/health -> PASS，status=UP。
- 配置校验: repo-root: D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260703-0009-nodata-evening-fix3; frontend-root: D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260703-0009-nodata-evening-fix3

## 2026-07-03 00:15:41 +08:00 fix3 build-release 启动
- releaseTag: release-20260703-0009-nodata-evening-fix3
- GREEN: build-release-preview-contract -> PASS，参数包含 -Mode build-release、-SkipDatabaseSync、-SkipMinioSync，不包含部署/正式服/备份/恢复/回滚动作。
- GREEN: build-release-start -> PASS，operation=op-2026-07-02T161541001144800Z-e41fd403-d2ff-4b9c-83a7-fc1f4225577d。

## 2026-07-03 00:39:20 +08:00 fix3 build-release 完成精确核验
- GREEN: build-release -> PASS，operation=op-2026-07-02T161541001144800Z-e41fd403-d2ff-4b9c-83a7-fc1f4225577d，releaseTag=release-20260703-0009-nodata-evening-fix3。
- GREEN: manifest-source-repos -> PASS，backend=8b9b0bd7450413202423b1a61aea5530f14a6436 dirty=false；frontend=4a89359a739ba69f5d1ce348e324455968fb28cb dirty=false。
- GREEN: package-no-data -> PASS，publishScope=code-only，发布目录未包含 database/db-dump/mysql-dump/minio/files/runtime-data/data/docker-build-context；目录=required-sql, resources, runtime-env, smoke。

## 2026-07-03 00:40:12 +08:00 fix3 publish-test 启动
- releaseTag: release-20260703-0009-nodata-evening-fix3
- GREEN: publish-test-preview-contract -> PASS，参数包含 -Mode deploy-release、-Environment test、172.30.30.58、/opt/intruoyi/runtime，不包含 mark-tested/promote/restore/rollback 动作。
- GREEN: publish-test-start -> PASS，operation=op-2026-07-02T163956246337200Z-32587742-51dc-4f73-9f5a-8b84ce3e2d9e。

## 2026-07-03 00:58:21 +08:00 fix3 publish-test 完成与运行态核验
- GREEN: publish-test -> PASS，operation=op-2026-07-02T163956246337200Z-32587742-51dc-4f73-9f5a-8b84ce3e2d9e，releaseTag=release-20260703-0009-nodata-evening-fix3，日志显示 Publish completed for test。
- GREEN: remote-image-tag -> PASS，/opt/intruoyi/runtime/.env IMAGE_TAG=release-20260703-0009-nodata-evening-fix3。
- GREEN: remote-images -> PASS，backend=intruoyi-backend:release-20260703-0009-nodata-evening-fix3；frontend=intruoyi-frontend:release-20260703-0009-nodata-evening-fix3。
- GREEN: runtime-smoke -> PASS，backend health={"status":"UP"}；frontend HTTP=200；pdf.worker.mjs HTTP=200 application/javascript。
- GREEN: dcc-lifecycle-stage-db -> PASS，dcc_file_category.lifecycle_stage blank count=0，column IS_NULLABLE=NO，COLUMN_TYPE=varchar(32)。
- GREEN: publish-scope -> PASS，本轮只执行 build-release 与 publish-test，未执行 mark-tested、正式服、备份服、备份、恢复或回滚。
- 数据库迁移状态摘要：
ssh : mysql: [Warning] Using a password on the command line interface can be insecure.
At line:29 char:20
+ ... = ($query | ssh -o BatchMode=yes -o ConnectTimeout=15 root@172.30.30. ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (mysql: [Warning...an be insecure.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
blank_lifecycle_stage_count
0
COLUMN_NAME	IS_NULLABLE	COLUMN_TYPE
lifecycle_stage	NO	varchar(32)
status	cnt
APPLIED	5
SKIPPED_ALREADY_APPLIED	236
close - IO is still pending on closed socket. read:1, write:0, io:0000023624D9C640

## 2026-07-03 01:07:42 +08:00 发布临时目录清理最终确认
- GREEN: release-worktree-cleanup-final -> PASS，git worktree remove 删除 1 个；属性归一化/robocopy 镜像清空删除残留目录 4 个。
- 删除 worktree: D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260703-0009-nodata-evening-fix3
- 删除残留目录: D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2151-nodata-evening; D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2240-nodata-evening-fix; D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260702-2316-nodata-evening-fix2; D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260703-0009-nodata-evening-fix3
- 跳过: 
- runtime-control 配置保持主工作区: repo-root: D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro; frontend-root: D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3
- runtime-control health: UP
- 后端 worktree list:
D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro                                             39733316a6 [int_main]
D:/ProjectPackage/Int/IntRuoyiWorktrees/edhr_table_jingxi/ruoyi-vue-pro                  f87b8485ea [codex/edhr_table_jingxi]
E:/Int/CacheData/IntRuoyi/runtime/clean-build-worktrees/backend-restart-20260702-230145  44c8253a7f (detached HEAD)
- 前端 worktree list:
D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3                             e4dfc86d8 [int_main]
D:/ProjectPackage/Int/IntRuoyiWorktrees/edhr_table_jingxi/yudao-ui-admin-vue3  4decbf980 [codex/edhr_table_jingxi]

## 2026-07-03 01:08:41 +08:00 任务文档收口
- GREEN: task-doc-closeout -> PASS，task.md 已将里程碑、当前状态、fix3 releaseTag、build/publish operation 和运行态证据更新为最终真实值。
