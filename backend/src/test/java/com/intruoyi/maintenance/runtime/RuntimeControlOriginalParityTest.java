package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "maintenance.runtime-control.ops-root=../ops",
        "maintenance.runtime-control.state-dir=../runtime/runtime-control-original-parity-test",
        "maintenance.runtime-control.local-cache-root=target/runtime-control-original-parity-local-cache",
        "maintenance.runtime-control.status-timeout-millis=50",
        "maintenance.runtime-control.production-write-enabled=true",
        "maintenance.runtime-control.environments.prod.access-enabled=true",
        "maintenance.runtime-control.release-package.nas-server=unit-nas",
        "maintenance.runtime-control.release-package.nas-share=unit-share",
        "maintenance.runtime-control.release-package.nas-username=test-user",
        "maintenance.runtime-control.release-package.nas-password=test-password",
        "maintenance.runtime-control.release-package.nas-release-root=Backup/ReleasePackage",
        "maintenance.runtime-control.release-package.smart-release-target-config-path=../doc/tasks/20260620-prod-release-current-latest/prod-target-config.json",
        "maintenance.runtime-control.release-package.backend-runtime-base-mode=offline-tar",
        "maintenance.runtime-control.release-package.backend-runtime-base-tar-path=D:/ProjectPackage/Int/BaseImages/runtime-base.tar",
        "maintenance.runtime-control.release-package.backend-runtime-base-tar-sha256=abc123",
        "maintenance.runtime-control.release-package.backend-runtime-base-image=intruoyi-backend-runtime-base:test",
        "maintenance.runtime-control.release-package.backend-runtime-base-digest=sha256:test",
        "maintenance.runtime-control.release-package.backend-runtime-base-version=test",
        "maintenance.runtime-control.backup-ops.nas-server=unit-nas",
        "maintenance.runtime-control.backup-ops.nas-share=unit-share",
        "maintenance.runtime-control.backup-ops.nas-username=test-user",
        "maintenance.runtime-control.backup-ops.nas-password=test-password",
        "maintenance.runtime-control.backup-ops.nas-backup-points-root=Backup/BackupPackage"
})
@AutoConfigureMockMvc
class RuntimeControlOriginalParityTest {

    private static final Path NAS_ROOT = Path.of("target/runtime-control-original-parity-nas")
            .toAbsolutePath().normalize();
    private static final Path LOCAL_CACHE_ROOT = Path.of("target/runtime-control-original-parity-local-cache")
            .toAbsolutePath().normalize();

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private RuntimeControlOperationStore operationStore;

    @BeforeEach
    void setUp() throws Exception {
        resetDirectory(NAS_ROOT);
        resetDirectory(LOCAL_CACHE_ROOT);
        resetDirectory(operationStore.stateDir());
        Files.createDirectories(NAS_ROOT.resolve("Backup/ReleasePackage"));
        Files.createDirectories(NAS_ROOT.resolve("Backup/BackupPackage"));
        Files.createDirectories(LOCAL_CACHE_ROOT.resolve("publish-int-ruoyi"));
    }

    @Test
    void originalRuntimeControlEndpointsAreExposedWithoutSecurity() throws Exception {
        String controller = Files.readString(Path.of("src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlController.java"),
                StandardCharsets.UTF_8);
        String pom = Files.readString(Path.of("pom.xml"), StandardCharsets.UTF_8);

        for (String endpoint : List.of(
                "/admin-api/infra/runtime-control/owner-matrix",
                "/admin-api/infra/runtime-control/wizard/scenarios",
                "/admin-api/infra/runtime-control/wizard/recommendation",
                "/admin-api/infra/runtime-control/alerts/{id}/resend-site-message"
        )) {
            assertThat(controller).contains(endpoint);
        }
        assertThat(controller).doesNotContain("@PreAuthorize", "SecurityFrameworkUtils");
        assertThat(pom).doesNotContain("spring-boot-starter-security");

        mockMvc.perform(get("/admin-api/infra/runtime-control/owner-matrix"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(post("/admin-api/infra/runtime-control/owner-matrix")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "role": "owner",
                                  "required": true,
                                  "ownerName": "local-operator"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(put("/admin-api/infra/runtime-control/owner-matrix/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "role": "owner",
                                  "required": true,
                                  "ownerName": "local-operator"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(get("/admin-api/infra/runtime-control/wizard/scenarios"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(post("/admin-api/infra/runtime-control/wizard/recommendation")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"scenario\":\"app-exception\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(post("/admin-api/infra/runtime-control/alerts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "severity": "WARN",
                                  "title": "测试告警",
                                  "content": "端点契约验证"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(post("/admin-api/infra/runtime-control/alerts/1/resend-site-message"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
    }

    @Test
    void publishTestPreviewAcceptsMatchingTargetEnvironmentFromFrontend() throws Exception {
        createRollbackPackage("release-publish-test-target", true, false, false);

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "publish-test",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "releaseTag": "release-publish-test-target"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("-Mode", "deploy-release", "-Environment", "test",
                        "-ReleaseTag", "release-publish-test-target", "-ServerHost", "172.30.30.58",
                        "-RemoteReleaseRoot", "/var/lib/docker/intruoyi-releases",
                        "-RemoteDataRoot", "/var/lib/docker/intruoyi-data/runtime-data",
                        "-RemoteDataDiskMount", "/var/lib/docker",
                        "-RemoteDataDiskDevice", "/dev/vdb",
                        "-RemoteMinioContainer", "ragflow_compose-minio-1")
                .doesNotContain("172.30.30.57", "backup-now", "restore-data", "rollback-app");

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "publish-test",
                                  "reason": "contract preview",
                                  "targetEnvironment": "backup",
                                  "releaseTag": "release-publish-test-target"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("targetEnvironment")));
    }

    @Test
    void highRiskCandidateValuesAreServerResolvedOnly() throws Exception {
        createRollbackPackage("release-rollback", true, true, true);
        createRestorePoint("backup-20260616");

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "rollback-app",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "selectedImageCandidateId": "rollback:release-rollback",
                                  "selectedImageTag": "manual-injected-tag"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("selectedImageTag")));

        String rollbackPreview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "rollback-app",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "selectedImageCandidateId": "rollback:release-rollback"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(rollbackPreview).contains("-SelectedImageTag", "release-rollback");

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "restore-data",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "selectedRecoverySetCandidateId": "restore:backup-20260616",
                                  "selectedBackupId": "manual-injected-backup"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("selectedBackupId")));

        String restorePreview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "restore-data",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "selectedRecoverySetCandidateId": "restore:backup-20260616"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(restorePreview).contains("-SelectedBackupId", "backup-20260616");
    }

    @Test
    void releasePackageValidationMatchesOriginalGate() throws Exception {
        createRollbackPackage("release-tested", true, false, true);
        createTestedMetadata("release-tested");
        createRollbackPackage("release-untested", true, false, false);
        createRollbackPackage("release-no-checksum", false, false, false);
        Files.createDirectories(NAS_ROOT.resolve("Backup/ReleasePackage/release-no-manifest"));

        String packages = mockMvc.perform(get("/admin-api/infra/runtime-control/release-packages"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(packages)
                .contains("release-tested", "release-untested")
                .doesNotContain("release-no-checksum", "release-no-manifest");

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "publish-test",
                                  "reason": "contract preview",
                                  "releaseTag": "release-no-checksum"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("manifest/checksum")));

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "promote-backup",
                                  "reason": "contract preview",
                                  "prodConfirmText": "PROD",
                                  "releaseTag": "release-untested"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("尚未测试通过")));
    }

    @Test
    void promoteBackupAcceptsCodeOnlyReleaseAfterSuccessfulTestDeployment() throws Exception {
        createRollbackPackage("release-code-only-test-passed", true, false, false);
        saveSuccessfulOperation("op-publish-test-pass", "test", "publish-test", "publish-test",
                Map.of("releaseTag", "release-code-only-test-passed"));

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "promote-backup",
                                  "reason": "contract preview",
                                  "prodConfirmText": "PROD",
                                  "releaseTag": "release-code-only-test-passed"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("-Mode", "deploy-release", "-Environment", "backup",
                        "-ReleaseTag", "release-code-only-test-passed", "-ConfirmText", "PROD",
                        "-RequireTested", "-ServerHost", "172.30.30.59",
                        "-RemoteReleaseRoot", "/mnt/intruoyi-data/intruoyi-releases",
                        "-RemoteDataRoot", "/mnt/intruoyi-data/runtime-data",
                        "-RemoteDataDiskMount", "/mnt/intruoyi-data",
                        "-RemoteDataDiskDevice", "/dev/mapper/cl-home",
                        "-RemoteMinioContainer", "intruoyi-minio")
                .doesNotContain("172.30.30.57", "backup-now", "restore-data", "rollback-app");
    }

    @Test
    void promoteBackupRejectsWithDataReleaseWithoutTestedMetadataEvenAfterTestDeployment() throws Exception {
        createReleasePackage("release-with-data-test-passed", "with-data", true, false, false);
        saveSuccessfulOperation("op-publish-test-with-data-pass", "test", "publish-test", "publish-test",
                Map.of("releaseTag", "release-with-data-test-passed"));

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "promote-backup",
                                  "reason": "contract preview",
                                  "prodConfirmText": "PROD",
                                  "releaseTag": "release-with-data-test-passed"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("尚未测试通过")));
    }

    @Test
    void promoteProdPreviewAutoGeneratesDryRunEvidence() throws Exception {
        String releaseTag = "release-20260621-prod-dry-run-fixture";
        createRollbackPackage(releaseTag, true, false, true);
        Path localCacheReleaseDir = LOCAL_CACHE_ROOT.resolve("publish-int-ruoyi")
                .resolve(releaseTag);
        resetDirectory(localCacheReleaseDir);
        Files.createDirectories(localCacheReleaseDir.resolve("resources"));
        Files.writeString(localCacheReleaseDir.resolve("docker-compose.yml"), "services: {}\n", StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("resources").resolve("resource-reference-manifest.json"), """
                {
                  "schemaVersion": "1.0",
                  "releaseTag": "%s",
                  "generatedAt": "2026-06-20T00:00:00Z",
                  "resourcePayloadMode": "reference-check-only",
                  "dccObjectInventory": null
                }
                """.formatted(releaseTag), StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("manifest.json"), """
                {
                  "manifestVersion": "1.0",
                  "packageId": "%s",
                  "releaseTag": "%s",
                  "packageType": "full-release",
                  "createdAt": "2026-06-20T00:00:00Z",
                  "createdBy": "test",
                  "sourceRepos": [],
                  "changeSet": {
                    "summary": "test release package",
                    "component": "intruoyi",
                    "includeShowroomBuildPackage": false,
                    "includeOnlyOffice": false
                  },
                  "publishScope": "code-only",
                  "components": ["runtime-env", "packaging-manifest"],
                  "artifacts": [
                    {
                      "artifactId": "docker-compose.yml",
                      "componentName": "runtime-env",
                      "artifactType": "release-package-file",
                      "path": "docker-compose.yml",
                      "includedInPackage": true,
                      "artifactCacheUri": null,
                      "sha256": "sha256:%s"
                    }
                  ],
                  "database": {
                    "schemaMigrations": [],
                    "requiredDataSets": []
                  },
                  "schemaVersion": "not-included",
                  "schemaDigest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
                  "migrationPlan": [],
                  "requiredSql": [],
                  "buildModules": [],
                  "compatibilityMatrix": [],
                  "operationEvidencePolicy": {
                    "requiredOperationTypes": ["manifest-validation"],
                    "failOnMissingOperationEvidence": true,
                    "failOnIntermediateFailure": true
                  },
                  "resources": {
                    "resourcePayloadMode": "reference-check-only",
                    "resourceReferenceManifest": "resources/resource-reference-manifest.json",
                    "resourceSnapshotId": null,
                    "resourceDeltaId": null,
                    "resourceDeltaPrepared": false,
                    "resourceDeltaProofPath": null
                  },
                  "targetRequirements": {
                    "environmentCodes": ["prod"],
                    "serverConfigSchemaVersion": "1.0",
                    "dockerProfileId": "intruoyi-docker-compose",
                    "storageProfileIds": ["minio-yudao-default"],
                    "requiresDatabaseMigrationPrecheck": false,
                    "requiresRequiredDataPrecheck": false,
                    "requiresResourceDeltaProof": false
                  },
                  "buildContract": {
                    "mode": "report-only",
                    "intakeReportPath": "intake/intake-result.json",
                    "manifestValidationResultPath": "manifest-validation-result.json",
                    "changesBuildExitCode": false,
                    "writesDatabase": false,
                    "syncsResources": false
                  },
                  "deployContract": {
                    "mode": "report-only",
                    "deployPrecheckResultPath": "deploy-precheck-result.json",
                    "changesDeployExitCode": false,
                    "targetConfigSource": "server-side-runtime-control-config",
                    "allowsRemoteMutation": false,
                    "allowsRemoteReadOnlyProbe": "authorized-only"
                  },
                  "precheckPlan": {
                    "checks": ["manifest", "artifact-hash"]
                  },
                  "verifyPlan": {
                    "checks": ["manifest"]
                  },
                  "rollbackPlan": {
                    "mode": "manual",
                    "requiresCompatibilityEvidence": true,
                    "restoresBusinessData": false
                  },
                  "forbiddenFieldsCheck": {
                    "status": "pending-validation",
                    "hardcodedIpMatches": [],
                    "secretPatternMatches": [],
                    "packageExternalPathReferences": []
                  },
                  "manifestChecksum": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
                }
                """.formatted(releaseTag, releaseTag, sha256(localCacheReleaseDir.resolve("docker-compose.yml"))),
                StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("release-manifest.json"), """
                {
                  "releaseTag": "%s",
                  "packageDirectoryName": "%s",
                  "builtAt": "2026-06-20T00:00:00Z",
                  "publishScope": "code-only",
                  "component": "intruoyi",
                  "includeShowroomBuildPackage": false,
                  "onlyOfficeIncluded": false,
                  "artifacts": [{"name":"image.tar","sha256":"abc123"}]
                }
                """.formatted(releaseTag, releaseTag), StandardCharsets.UTF_8);

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "promote-prod",
                                  "reason": "contract preview",
                                  "prodConfirmText": "PROD",
                                  "releaseTag": "%s"
                                }
                                """.formatted(releaseTag)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("-Mode", "deploy-release", "-Environment", "prod",
                        "-ReleaseTag", releaseTag,
                        "-ProdDryRunEvidencePath");
        assertThat(Files.exists(operationStore.stateDir().resolve("prod-preflight-release-evidence")
                .resolve(releaseTag + "-preflight-release-dry-run.json"))).isTrue();
    }

    @Test
    void promoteProdPreviewUsesSanitizedPackageWorkspace() throws Exception {
        String releaseTag = "release-20260621-prod-dry-run-polluted-workspace";
        createRollbackPackage(releaseTag, true, false, true);
        Path localCacheReleaseDir = LOCAL_CACHE_ROOT.resolve("publish-int-ruoyi")
                .resolve(releaseTag);
        resetDirectory(localCacheReleaseDir);
        Files.createDirectories(localCacheReleaseDir.resolve("resources"));
        Files.writeString(localCacheReleaseDir.resolve("docker-compose.yml"), "services: {}\n", StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("resources").resolve("resource-reference-manifest.json"), """
                {
                  "schemaVersion": "1.0",
                  "releaseTag": "%s",
                  "generatedAt": "2026-06-20T00:00:00Z",
                  "resourcePayloadMode": "reference-check-only",
                  "dccObjectInventory": null
                }
                """.formatted(releaseTag), StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("manifest.json"), """
                {
                  "manifestVersion": "1.0",
                  "packageId": "%s",
                  "releaseTag": "%s",
                  "packageType": "full-release",
                  "createdAt": "2026-06-20T00:00:00Z",
                  "createdBy": "test",
                  "sourceRepos": [],
                  "changeSet": {
                    "summary": "test release package",
                    "component": "intruoyi",
                    "includeShowroomBuildPackage": false,
                    "includeOnlyOffice": false
                  },
                  "publishScope": "code-only",
                  "components": ["runtime-env", "packaging-manifest"],
                  "artifacts": [
                    {
                      "artifactId": "docker-compose.yml",
                      "componentName": "runtime-env",
                      "artifactType": "release-package-file",
                      "path": "docker-compose.yml",
                      "includedInPackage": true,
                      "artifactCacheUri": null,
                      "sha256": "sha256:%s"
                    }
                  ],
                  "database": {
                    "schemaMigrations": [],
                    "requiredDataSets": []
                  },
                  "schemaVersion": "not-included",
                  "schemaDigest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
                  "migrationPlan": [],
                  "requiredSql": [],
                  "buildModules": [],
                  "compatibilityMatrix": [],
                  "operationEvidencePolicy": {
                    "requiredOperationTypes": ["manifest-validation"],
                    "failOnMissingOperationEvidence": true,
                    "failOnIntermediateFailure": true
                  },
                  "resources": {
                    "resourcePayloadMode": "reference-check-only",
                    "resourceReferenceManifest": "resources/resource-reference-manifest.json",
                    "resourceSnapshotId": null,
                    "resourceDeltaId": null,
                    "resourceDeltaPrepared": false,
                    "resourceDeltaProofPath": null
                  },
                  "targetRequirements": {
                    "environmentCodes": ["prod"],
                    "serverConfigSchemaVersion": "1.0",
                    "dockerProfileId": "intruoyi-docker-compose",
                    "storageProfileIds": ["minio-yudao-default"],
                    "requiresDatabaseMigrationPrecheck": false,
                    "requiresRequiredDataPrecheck": false,
                    "requiresResourceDeltaProof": false
                  },
                  "buildContract": {
                    "mode": "report-only",
                    "intakeReportPath": "intake/intake-result.json",
                    "manifestValidationResultPath": "manifest-validation-result.json",
                    "changesBuildExitCode": false,
                    "writesDatabase": false,
                    "syncsResources": false
                  },
                  "deployContract": {
                    "mode": "report-only",
                    "deployPrecheckResultPath": "deploy-precheck-result.json",
                    "changesDeployExitCode": false,
                    "targetConfigSource": "server-side-runtime-control-config",
                    "allowsRemoteMutation": false,
                    "allowsRemoteReadOnlyProbe": "authorized-only"
                  },
                  "precheckPlan": {
                    "checks": ["manifest", "artifact-hash"]
                  },
                  "verifyPlan": {
                    "checks": ["manifest"]
                  },
                  "rollbackPlan": {
                    "mode": "manual",
                    "requiresCompatibilityEvidence": true,
                    "restoresBusinessData": false
                  },
                  "forbiddenFieldsCheck": {
                    "status": "pending-validation",
                    "hardcodedIpMatches": [],
                    "secretPatternMatches": [],
                    "packageExternalPathReferences": []
                  },
                  "manifestChecksum": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
                }
                """.formatted(releaseTag, releaseTag, sha256(localCacheReleaseDir.resolve("docker-compose.yml"))),
                StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("release-manifest.json"), """
                {
                  "releaseTag": "%s",
                  "packageDirectoryName": "%s",
                  "builtAt": "2026-06-20T00:00:00Z",
                  "publishScope": "code-only",
                  "component": "intruoyi",
                  "includeShowroomBuildPackage": false,
                  "onlyOfficeIncluded": false,
                  "artifacts": [{"name":"image.tar","sha256":"abc123"}]
                }
                """.formatted(releaseTag, releaseTag), StandardCharsets.UTF_8);

        Files.writeString(localCacheReleaseDir.resolve(".env"), "IMAGE_TAG=" + releaseTag + "\n",
                StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("preflight-plan.json"), """
                {"status":"passed","items":[]}
                """, StandardCharsets.UTF_8);
        Files.writeString(localCacheReleaseDir.resolve("post-import.sql"), "update demo set host='172.30.30.58';\n",
                StandardCharsets.UTF_8);

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "promote-prod",
                                  "reason": "contract preview",
                                  "prodConfirmText": "PROD",
                                  "releaseTag": "%s"
                                }
                                """.formatted(releaseTag)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("-Mode", "deploy-release", "-Environment", "prod",
                        "-ReleaseTag", releaseTag,
                        "-ProdDryRunEvidencePath");
        assertThat(Files.exists(operationStore.stateDir().resolve("prod-preflight-release-evidence")
                .resolve(releaseTag + "-preflight-release-dry-run.json"))).isTrue();
    }

    @Test
    void backupNowPreviewPassesProductionBackupConfirmTextToScript() throws Exception {
        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "backup-now",
                                  "reason": "contract preview",
                                  "targetEnvironment": "prod",
                                  "prodConfirmText": "PROD-BACKUP-172.30.30.57"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("-Mode", "backup-now",
                        "-TargetEnvironment", "prod",
                        "-ProductionBackupConfirmText", "PROD-BACKUP-172.30.30.57")
                .doesNotContain("-ConfirmText");
    }

    @Test
    void applyTestDbSqlRequiresRealSqlFile() throws Exception {
        Path sqlRoot = Path.of("target/runtime-control-original-parity-sql").toAbsolutePath().normalize();
        resetDirectory(sqlRoot);
        Files.createDirectories(sqlRoot);
        Path goodSql = sqlRoot.resolve("good.sql");
        Path badText = sqlRoot.resolve("bad.txt");
        Files.writeString(goodSql, "select 1;", StandardCharsets.UTF_8);
        Files.writeString(badText, "select 1;", StandardCharsets.UTF_8);

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "apply-test-db-sql",
                                  "reason": "contract preview",
                                  "sqlPath": "%s"
                                }
                                """.formatted(badText.toString().replace("\\", "\\\\"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString(".sql")));

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "apply-test-db-sql",
                                  "reason": "contract preview",
                                  "sqlPath": "%s"
                                }
                                """.formatted(goodSql.toString().replace("\\", "\\\\"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(preview).contains("-SqlPath", "good.sql", "-ServerHost", "172.30.30.58");
    }

    @Test
    void releaseStatusAndMarkTestedUseCurrentTestReleaseTagLikeOriginal() throws Exception {
        createRollbackPackage("release-current", true, false, false);
        createRollbackPackage("release-tested", true, false, true);
        createRestorePoint("backup-20260616");
        saveSuccessfulOperation("op-current-test-release", "test", "ops", "publish-test",
                Map.of("releaseTag", "release-current"));

        mockMvc.perform(get("/admin-api/infra/runtime-control/release-status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.testCurrentReleaseTag").value("release-current"))
                .andExpect(jsonPath("$.data.latestTestedReleaseTag").value("release-tested"));

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "mark-release-tested",
                                  "reason": "contract preview",
                                  "releaseTag": "release-forged",
                                  "testConclusion": "回归通过，允许上线正式服",
                                  "selectedRecoverySetCandidateId": "restore:backup-20260616"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(preview).contains("-ReleaseTag", "release-current").doesNotContain("release-forged");
    }

    @Test
    void releaseStatusExposesCurrentReleaseTagsForTestBackupAndProdLikeOriginal() throws Exception {
        createRollbackPackage("release-test-current", true, false, false);
        createRollbackPackage("release-backup-current", true, false, false);
        createRollbackPackage("release-prod-current", true, false, false);
        saveSuccessfulOperation("op-current-test-release", "test", "ops", "publish-test",
                Map.of("releaseTag", "release-test-current"));
        saveSuccessfulOperation("op-current-backup-release", "backup", "ops", "promote-backup",
                Map.of("releaseTag", "release-backup-current"));
        saveSuccessfulOperation("op-current-prod-release", "prod", "ops", "promote-prod",
                Map.of("releaseTag", "release-prod-current"));

        mockMvc.perform(get("/admin-api/infra/runtime-control/release-status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.testCurrentReleaseTag").value("release-test-current"))
                .andExpect(jsonPath("$.data.prodCurrentReleaseTag").value("release-prod-current"))
                .andExpect(jsonPath("$.data.backupCurrentReleaseTag").value("release-backup-current"));
    }

    @Test
    void releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly() throws Exception {
        createReleasePackageWithNotes("release-old-history", "历史版本不应展示",
                List.of("历史版本变动不应进入当前说明"));
        createReleasePackageWithNotes("release-test-notes", "测试服当前版本：随机 ERP 建单修复",
                List.of("修复随机 ERP 建单物料选择", "补充运行控制台版本栏"));
        createReleasePackageWithNotes("release-prod-notes", "正式服当前版本：页面全链路发布",
                List.of("完成页面全链路正式发布"));
        createReleasePackageWithNotes("release-backup-notes", "备份服当前版本：备份环境同步",
                List.of("同步正式服已验证版本到备份服"));
        saveSuccessfulOperation("op-old-history-release", "test", "ops", "publish-test",
                Map.of("releaseTag", "release-old-history"));
        saveSuccessfulOperation("op-current-test-release", "test", "ops", "publish-test",
                Map.of("releaseTag", "release-test-notes"));
        saveSuccessfulOperation("op-current-prod-release", "prod", "ops", "promote-prod",
                Map.of("releaseTag", "release-prod-notes"));
        saveSuccessfulOperation("op-current-backup-release", "backup", "ops", "promote-backup",
                Map.of("releaseTag", "release-backup-notes"));

        String response = mockMvc.perform(get("/admin-api/infra/runtime-control/release-status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.releaseTag").value("release-test-notes"))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.summary").value("测试服当前版本：随机 ERP 建单修复"))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.changes[0]").value("修复随机 ERP 建单物料选择"))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.sourceRepos[0].pathRole").value("backend"))
                .andExpect(jsonPath("$.data.prodCurrentReleaseNotes.releaseTag").value("release-prod-notes"))
                .andExpect(jsonPath("$.data.backupCurrentReleaseNotes.releaseTag").value("release-backup-notes"))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(response).doesNotContain("历史版本变动不应进入当前说明");
    }

    @Test
    void releaseStatusSanitizesGarbledChangeItemsAndKeepsOnlyReleaseNotesFields() throws Exception {
        createReleasePackageWithRawItems("release-garbled-notes", "Release package release-garbled-notes",
                List.of("发布包锛?PackageTag", "组件范围锛?Component"));
        saveSuccessfulOperation("op-current-garbled-release", "test", "ops", "publish-test",
                Map.of("releaseTag", "release-garbled-notes"));

        mockMvc.perform(get("/admin-api/infra/runtime-control/release-status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.releaseTag").value("release-garbled-notes"))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.changes[0]").value("发布包：release-garbled-notes"))
                .andExpect(jsonPath("$.data.testCurrentReleaseNotes.changes[1]").value("组件范围：intruoyi"));
    }

    @Test
    void unsupportedActionFieldsAreRejectedLikeOriginal() throws Exception {
        createRollbackPackage("release-current", true, false, false);
        Path sqlRoot = Path.of("target/runtime-control-original-parity-sql").toAbsolutePath().normalize();
        resetDirectory(sqlRoot);
        Files.createDirectories(sqlRoot);
        Path goodSql = sqlRoot.resolve("good.sql");
        Files.writeString(goodSql, "select 1;", StandardCharsets.UTF_8);

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "publish-test",
                                  "reason": "contract preview",
                                  "releaseTag": "release-current",
                                  "includeOnlyOffice": false
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("includeOnlyOffice")));

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "apply-test-db-sql",
                                  "reason": "contract preview",
                                  "targetEnvironment": "test",
                                  "sqlPath": "%s"
                                }
                                """.formatted(goodSql.toString().replace("\\", "\\\\"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("targetEnvironment")));

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview",
                                  "publishScope": "code-only"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("includeOnlyOffice")));
    }

    @Test
    void restoreCandidateRequiresCompleteDccChainLikeOriginal() throws Exception {
        createRestorePoint("backup-broken-dcc", "BROKEN");

        mockMvc.perform(get("/admin-api/infra/runtime-control/restore-candidates"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].candidateId").value("restore:backup-broken-dcc"))
                .andExpect(jsonPath("$.data[0].status").value("BLOCKED"))
                .andExpect(jsonPath("$.data[0].blockedReasons[0]")
                        .value(org.hamcrest.Matchers.containsString("chainStatus 不是 COMPLETE")));
    }

    @Test
    void restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints() throws Exception {
        createRestorePoint("20260621-063218");
        Files.createDirectories(NAS_ROOT.resolve("Backup/BackupPackage/object-store"));

        mockMvc.perform(get("/admin-api/infra/runtime-control/restore-candidates"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].candidateId").value("restore:20260621-063218"))
                .andExpect(jsonPath("$.data[0].status").value("AVAILABLE"));
    }

    private void createRollbackPackage(String directoryName, boolean withChecksum,
                                       boolean withRollbackEvidence, boolean withTestedEvidence) throws IOException {
        createReleasePackage(directoryName, "code-only", withChecksum, withRollbackEvidence, withTestedEvidence);
    }

    private void createReleasePackageWithNotes(String directoryName, String summary, List<String> changes)
            throws IOException {
        createReleasePackage(directoryName, "code-only", true, false, false, summary, changes);
    }

    private void createReleasePackageWithRawItems(String directoryName, String summary, List<String> changes)
            throws IOException {
        createReleasePackage(directoryName, "code-only", true, false, false, summary, changes);
    }

    private void createReleasePackage(String directoryName, String publishScope, boolean withChecksum,
                                      boolean withRollbackEvidence, boolean withTestedEvidence) throws IOException {
        createReleasePackage(directoryName, publishScope, withChecksum, withRollbackEvidence, withTestedEvidence,
                "Release package " + directoryName, List.of());
    }

    private void createReleasePackage(String directoryName, String publishScope, boolean withChecksum,
                                      boolean withRollbackEvidence, boolean withTestedEvidence, String summary,
                                      List<String> changes) throws IOException {
        Path root = NAS_ROOT.resolve("Backup/ReleasePackage").resolve(directoryName);
        Files.createDirectories(root);
        Files.writeString(root.resolve("release-manifest.json"), """
                {
                  "releaseTag": "%s",
                  "packageDirectoryName": "%s",
                  "builtAt": "2026-06-16T00:00:00Z",
                  "publishScope": "%s",
                  "component": "intruoyi",
                  "includeShowroomBuildPackage": false,
                  "onlyOfficeIncluded": false,
                  "artifacts": [%s]
                }
                """.formatted(directoryName, directoryName, publishScope,
                withChecksum ? "{\"name\":\"image.tar\",\"sha256\":\"abc123\"}" : ""),
                StandardCharsets.UTF_8);
        Files.writeString(root.resolve("manifest.json"), """
                {
                  "manifestVersion": "1.0",
                  "releaseTag": "%s",
                  "packageId": "%s",
                  "createdAt": "2026-06-16T00:00:00Z",
                  "sourceRepos": [
                    {"name": "ruoyi-vue-pro", "pathRole": "backend", "commit": "backend-%s", "branch": "test", "dirty": false},
                    {"name": "yudao-ui-admin-vue3", "pathRole": "admin-frontend", "commit": "frontend-%s", "branch": "test", "dirty": false}
                  ],
                  "changeSet": {
                    "summary": %s,
                    "items": %s
                  },
                  "targetRequirements": {
                    "dockerProfileId": "intruoyi-docker-compose",
                    "storageProfileIds": ["minio-yudao-default"]
                  }
                }
                """.formatted(directoryName, directoryName, directoryName, directoryName, jsonString(summary),
                jsonArray(changes)), StandardCharsets.UTF_8);
        if (withRollbackEvidence) {
            Files.writeString(root.resolve("prod-latest.json"), """
                    {"releaseTag":"%s","packageDirectoryName":"%s","environment":"prod"}
                    """.formatted(directoryName, directoryName), StandardCharsets.UTF_8);
            Files.writeString(root.resolve("rollback-compatibility.json"), """
                    {
                      "schemaVersion": "v1",
                      "packageDirectoryName": "%s",
                      "status": "COMPATIBLE",
                      "checkedAt": "2026-06-16T00:00:00Z",
                      "summary": "compatible"
                    }
                    """.formatted(directoryName), StandardCharsets.UTF_8);
        }
        if (withTestedEvidence) {
            createTestedMetadata(directoryName);
        }
    }

    private void createTestedMetadata(String directoryName) throws IOException {
        Path root = NAS_ROOT.resolve("Backup/ReleasePackage").resolve(directoryName);
        Files.createDirectories(root);
        Files.writeString(root.resolve("tested.json"), """
                {
                  "testedAt": "2026-06-16T00:10:00Z",
                  "operatorName": "local-operator",
                  "recoverySet": {
                    "selectedRecoverySetCandidateId": "restore:backup-20260616",
                    "recoverySetId": "backup-20260616",
                    "recoverySetManifestHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                  }
                }
                    """, StandardCharsets.UTF_8);
    }

    private static String jsonArray(List<String> values) {
        return "[" + String.join(",", values.stream().map(RuntimeControlOriginalParityTest::jsonString).toList()) + "]";
    }

    private static String jsonString(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private void createRestorePoint(String backupId) throws IOException {
        createRestorePoint(backupId, "COMPLETE");
    }

    private void createRestorePoint(String backupId, String dccChainStatus) throws IOException {
        Path root = NAS_ROOT.resolve("Backup/BackupPackage").resolve(backupId);
        Files.createDirectories(root.resolve("deploy"));
        Files.createDirectories(root.resolve("manifest"));
        Files.writeString(root.resolve("deploy/image-tag.txt"), "release-rollback", StandardCharsets.UTF_8);
        Files.writeString(root.resolve("deploy/runtime.env"), "IMAGE_TAG=release-rollback\n", StandardCharsets.UTF_8);
        Files.writeString(root.resolve("deploy/docker-compose.yml"), "services: {}\n", StandardCharsets.UTF_8);
        Files.writeString(root.resolve("manifest/checksums.txt"), "sha256 deploy/runtime.env\n", StandardCharsets.UTF_8);
        Files.writeString(root.resolve("manifest/dcc-backup-manifest.json"), """
                {
                  "schemaVersion": "dcc-backup-manifest-v1",
                  "backupMode": "target-dataset",
                  "chainStatus": "%s",
                  "changeSummary": {"added": "0", "modified": "0", "deleted": "0", "reused": "1"}
                }
                """.formatted(dccChainStatus), StandardCharsets.UTF_8);
        Files.writeString(root.resolve("manifest/manifest.json"), """
                {
                  "schemaVersion": "v2",
                  "backupId": "%s",
                  "status": "success",
                  "deploy": {"imageTag": "release-rollback"},
                  "backupStrategy": {"mode": "full", "mysqlBackupMode": "full"},
                  "validation": {"rehearsalStatus": "PASSED", "lastRehearsedAt": "2026-06-16T00:00:00Z"},
                  "recoverySet": {
                    "id": "%s",
                    "status": "COMPLETE",
                    "program": {"imageTag": "release-rollback"},
                    "redis": {"policy": "CLEAR_AND_REBUILD"},
                    "configuration": {"manifestPath": "deploy/runtime.env", "composePath": "deploy/docker-compose.yml"},
                    "checksums": {"path": "manifest/checksums.txt", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                    "dcc": {"manifestPath": "manifest/dcc-backup-manifest.json"}
                  }
                }
                """.formatted(backupId, backupId), StandardCharsets.UTF_8);
    }

    private void saveSuccessfulOperation(String operationId, String environment, String component, String action,
                                         Map<String, String> parameters) {
        operationStore.save(new RuntimeDtos.RuntimeControlOperationRespVO(operationId, "local-operator",
                Instant.now(), environment, component, action, action, parameters, "contract fixture",
                "SUCCESS", "success", "target/runtime-control-original-parity.log"));
    }

    private static String sha256(Path path) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return java.util.HexFormat.of().formatHex(digest.digest(Files.readAllBytes(path)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 algorithm unavailable", ex);
        }
    }

    private static void resetDirectory(Path path) throws IOException {
        if (Files.notExists(path)) {
            return;
        }
        try (var stream = Files.walk(path)) {
            List<Path> paths = stream.sorted(Comparator.reverseOrder()).toList();
            for (Path current : paths) {
                try {
                    Files.deleteIfExists(current);
                } catch (java.nio.file.DirectoryNotEmptyException ex) {
                    try (var retry = Files.walk(current)) {
                        List<Path> retryPaths = retry.sorted(Comparator.reverseOrder()).toList();
                        for (Path retryPath : retryPaths) {
                            Files.deleteIfExists(retryPath);
                        }
                    }
                }
            }
        }
    }

    @TestConfiguration
    static class LocalNasTestConfiguration {
        @Bean
        @Primary
        RuntimeControlNasBrowser runtimeControlNasBrowser() {
            return new LocalRuntimeControlNasBrowser(NAS_ROOT);
        }
    }

    static class LocalRuntimeControlNasBrowser extends RuntimeControlNasBrowser {
        private final Path root;

        LocalRuntimeControlNasBrowser(Path root) {
            this.root = root;
        }

        @Override
        public List<NasEntry> listDirectories(NasConfig config) {
            return list(config.root()).stream()
                    .filter(entry -> Files.isDirectory(toLocal(entry.path())))
                    .toList();
        }

        @Override
        public List<NasEntry> listFiles(NasConfig config, String path) {
            return list(path);
        }

        @Override
        public boolean isRegularFile(NasConfig config, String path) {
            Path local = toLocal(path);
            Path parent = local.getParent();
            if (parent != null && Files.notExists(parent)) {
                throw new RuntimeControlException("local NAS directory not found: " + toNasPath(parent));
            }
            return Files.isRegularFile(local);
        }

        @Override
        public String readText(NasConfig config, String path) {
            try {
                return Files.readString(toLocal(path), StandardCharsets.UTF_8);
            } catch (IOException ex) {
                throw new RuntimeControlException("local NAS read failed: " + path, ex);
            }
        }

        private List<NasEntry> list(String path) {
            Path local = toLocal(path);
            if (!Files.isDirectory(local)) {
                throw new RuntimeControlException("local NAS directory not found: " + path);
            }
            try (var stream = Files.list(local)) {
                return stream
                        .map(item -> new NasEntry(item.getFileName().toString(), toNasPath(item), Files.isDirectory(item)))
                        .sorted(Comparator.comparing(NasEntry::name).reversed())
                        .toList();
            } catch (IOException ex) {
                throw new RuntimeControlException("local NAS list failed: " + path, ex);
            }
        }

        private Path toLocal(String nasPath) {
            Path result = root;
            for (String part : nasPath.replace("\\", "/").split("/")) {
                if (!part.isBlank() && !".".equals(part)) {
                    result = result.resolve(part);
                }
            }
            return result.normalize();
        }

        private String toNasPath(Path localPath) {
            return root.relativize(localPath).toString().replace("\\", "/");
        }
    }
}
