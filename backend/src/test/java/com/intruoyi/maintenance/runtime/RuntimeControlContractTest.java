package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "maintenance.runtime-control.ops-root=../ops",
        "maintenance.runtime-control.state-dir=../runtime/runtime-control-test",
        "maintenance.runtime-control.status-timeout-millis=5000",
        "maintenance.runtime-control.release-package.nas-server=172.30.30.4",
        "maintenance.runtime-control.release-package.nas-share=IT共享",
        "maintenance.runtime-control.release-package.nas-username=test-user",
        "maintenance.runtime-control.release-package.nas-password=test-password",
        "maintenance.runtime-control.release-package.nas-release-root=Backup/ReleasePackage",
        "maintenance.runtime-control.release-package.backend-runtime-base-mode=offline-tar",
        "maintenance.runtime-control.release-package.backend-runtime-base-tar-path=D:/ProjectPackage/Int/BaseImages/intruoyi-backend-runtime-base-2026.06.05-jre21-noble-docker29.2.1.tar",
        "maintenance.runtime-control.release-package.backend-runtime-base-tar-sha256=5bcd568b46ba9f28bfa7ac8ee67e283aea95bd585a89842a14cc40827fa71603",
        "maintenance.runtime-control.release-package.backend-runtime-base-image=intruoyi-backend-runtime-base:2026.06.05-jre21-noble-docker29.2.1",
        "maintenance.runtime-control.release-package.backend-runtime-base-digest=sha256:b4f7d85f325665c3b372379e6d352c3c8be2d3a08add68ac0dc151f720160be7",
        "maintenance.runtime-control.release-package.backend-runtime-base-version=2026.06.05-jre21-noble-docker29.2.1"
})
@AutoConfigureMockMvc
class RuntimeControlContractTest {

    @Autowired
    private MockMvc mockMvc;

    @TestConfiguration
    static class LockInspectorTestConfig {
        @Bean
        @Primary
        RuntimeReleaseLockInspector runtimeReleaseLockInspector(RuntimeControlProperties properties) {
            return new RuntimeReleaseLockInspector(properties) {
                @Override
                public ReleaseOperationLockOwner requireTestLockOwner(String releaseTag) {
                    return new ReleaseOperationLockOwner("HOST-A", "12345", "operator@HOST-A",
                            "lease-token-from-remote-lock");
                }
            };
        }
    }

    @Test
    void noSpringSecurityDependency() throws Exception {
        String pom = Files.readString(Path.of("pom.xml"), StandardCharsets.UTF_8);
        String controller = Files.readString(Path.of(
                "src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlController.java"), StandardCharsets.UTF_8);

        assertThat(pom).doesNotContain("spring-boot-starter-security");
        assertThat(controller).doesNotContain("@PreAuthorize");
        assertThatThrownBy(() -> Class.forName("org.springframework.security.access.prepost.PreAuthorize"))
                .isInstanceOf(ClassNotFoundException.class);
    }

    @Test
    void releasePackageCandidateUsesManifestV1AsTheOnlyAuthority() throws Exception {
        String service = Files.readString(Path.of(
                "src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java"), StandardCharsets.UTF_8);
        assertThat(service).contains("childPath(packagePath, \"manifest.json\")");
        assertThat(service).contains("readJson(nasConfig, manifestPath, \"manifest.json\", blockedReasons)");
        assertThat(service).doesNotContain("缺少 release-manifest.json");
    }

    @Test
    void releasePackageValidationChecksRequestedTagDirectly() throws Exception {
        String service = Files.readString(Path.of(
                "src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java"), StandardCharsets.UTF_8);
        int start = service.indexOf("private void validateReleasePackageAvailability");
        String body = service.substring(start, service.indexOf("\n    private ", start + 1));
        assertThat(body).contains("buildReleasePackageResponse(nasConfig,")
                .contains("new RuntimeControlNasBrowser.NasEntry(releaseTag, packagePath, true)");
        assertThat(body).doesNotContain("getReleasePackages()");
    }

    @Test
    void exposesExplicitTestReleaseLockRecoveryAction() throws Exception {
        String action = Files.readString(Path.of(
                "src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java"),
                StandardCharsets.UTF_8);
        assertThat(action).contains("RECOVER_TEST_RELEASE_LOCK(\"recover-test-release-lock\", \"恢复测试服发布锁\"");
        assertThat(action).contains("deploy/recover-release-operation-lock.ps1");
        assertThat(action).contains("RECOVER-TEST-LOCK");
    }

    @Test
    void recoverTestReleaseLockPreviewUsesRemoteLockOwnerContractWithoutExposingLeaseToken() throws Exception {
        String response = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "recover-test-release-lock",
                                  "reason": "contract preview",
                                  "releaseTag": "release-lock-contract"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(response)
                .contains("-ExpectedOperationId", "test-release-lock-contract",
                        "-ExpectedReleaseTag", "release-lock-contract",
                        "-ExpectedExecutorHost", "HOST-A",
                        "-ExpectedExecutorPid", "12345",
                        "-ExpectedExecutorIdentity", "operator@HOST-A",
                        "-ExpectedLeaseToken", "<resolved-from-remote-lock>",
                        "-ExecutorTerminalState", "TERMINATED",
                        "-ConfirmText", "RECOVER-TEST-LOCK")
                .doesNotContain("lease-token-from-remote-lock");
    }

    @Test
    void missingConfigurationFailsFast() {
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setRepoRoot("");
        properties.setFrontendRoot("E:/IntRuoyi/IntRuoyiFronted");
        properties.setWebsiteRoot("D:/ProjectPackage/Website");
        properties.setEnvironments(Map.of());

        assertThatThrownBy(properties::validate)
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("maintenance.runtime-control.repo-root is required");
    }

    @Test
    void runtimeControlEndpointsAreExposed() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));

        mockMvc.perform(get("/admin-api/infra/runtime-control/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.environments[0]").value("local"));

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview only",
                                  "publishScope": "code-only",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.action").value("build-release"))
                .andExpect(jsonPath("$.data.scriptPath").exists());
    }

    @Test
    void buildReleaseCodeOnlyPreviewSkipsDatabaseAndMinioData() throws Exception {
        String response = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview code only",
                                  "publishScope": "code-only",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(response)
                .contains("-Mode", "build-release", "-PublishScope", "code-only",
                        "-SkipDatabaseSync", "-SkipMinioSync",
                        "-NasServer", "-NasShare", "-NasReleaseRoot",
                        "-TestServerHost", "172.30.30.58",
                        "-BackupServerHost", "172.30.30.59",
                        "-ProdServerHost", "172.30.30.57")
                .doesNotContain("test-password");
    }

    @Test
    void buildReleaseCodeOnlyPreviewForwardsApprovedSourceCommits() throws Exception {
        String response = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview code only source approval",
                                  "publishScope": "code-only",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false,
                                  "releaseTag": "release-source-approval"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(response)
                .contains("-ExpectedMaintenanceCommit")
                .contains("-ExpectedApplicationCommit")
                .contains("-ExpectedFrontendCommit")
                .contains("-SourceSelectionId", "release-source-approval");
    }

    @Test
    void buildReleaseExecutionRequiresPreviewSourceSnapshotToken() throws Exception {
        String previewResponse = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview source snapshot",
                                  "publishScope": "code-only",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false,
                                  "releaseTag": "release-source-snapshot"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.sourceSnapshotToken").isString())
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(previewResponse).contains("sourceSnapshotToken");

        mockMvc.perform(post("/admin-api/infra/runtime-control/actions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract execute without source snapshot",
                                  "publishScope": "code-only",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false,
                                  "releaseTag": "release-source-snapshot"
                                }
                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg").value(org.hamcrest.Matchers.containsString("sourceSnapshotToken")));
    }

    @Test
    void buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments() throws Exception {
        String response = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "build-release",
                                  "reason": "contract preview with real data",
                                  "publishScope": "with-data",
                                  "includeOnlyOffice": false,
                                  "includeShowroomBuildPackage": false
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(response)
                .contains("-Mode", "build-release", "-NasServer", "-NasShare", "-NasReleaseRoot",
                        "-BackendRepoRoot", "E:/IntRuoyi/IntRuoyiBackend",
                        "-FrontendRepoRoot", "E:/IntRuoyi/IntRuoyiFronted",
                        "-WebsiteRepo", "D:/ProjectPackage/Website",
                        "-BackendRuntimeBaseMode", "-BackendRuntimeBaseTarPath",
                        "-BackendRuntimeBaseTarSha256", "-BackendRuntimeBaseImage",
                        "-TestServerHost", "172.30.30.58",
                        "-BackupServerHost", "172.30.30.59",
                        "-ProdServerHost", "172.30.30.57",
                        "-BackendRuntimeBaseDigest", "-BackendRuntimeBaseVersion");
        assertThat(response)
                .contains("-PublishScope", "with-data", "-ConfirmText", "WITH-DATA")
                .doesNotContain("-SkipDatabaseSync", "-SkipMinioSync");
        assertThat(response)
                .doesNotContain("-SkipDatabaseSync")
                .doesNotContain("-SkipMinioSync")
                .doesNotContain("test-password");
    }
}
