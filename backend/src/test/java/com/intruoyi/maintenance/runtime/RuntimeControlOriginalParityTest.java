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
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "maintenance.runtime-control.ops-root=../ops",
        "maintenance.runtime-control.state-dir=../runtime/runtime-control-original-parity-test",
        "maintenance.runtime-control.status-timeout-millis=50",
        "maintenance.runtime-control.production-write-enabled=true",
        "maintenance.runtime-control.release-package.nas-server=unit-nas",
        "maintenance.runtime-control.release-package.nas-share=unit-share",
        "maintenance.runtime-control.release-package.nas-username=test-user",
        "maintenance.runtime-control.release-package.nas-password=test-password",
        "maintenance.runtime-control.release-package.nas-release-root=Backup/ReleasePackage",
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

    @Autowired
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() throws Exception {
        resetDirectory(NAS_ROOT);
        Files.createDirectories(NAS_ROOT.resolve("Backup/ReleasePackage"));
        Files.createDirectories(NAS_ROOT.resolve("Backup/BackupPackage"));
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
                        .content("{\"scenario\":\"rollback-app\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
        mockMvc.perform(post("/admin-api/infra/runtime-control/alerts/1/resend-site-message"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
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

    private void createRollbackPackage(String directoryName, boolean withChecksum,
                                       boolean withRollbackEvidence, boolean withTestedEvidence) throws IOException {
        Path root = NAS_ROOT.resolve("Backup/ReleasePackage").resolve(directoryName);
        Files.createDirectories(root);
        Files.writeString(root.resolve("release-manifest.json"), """
                {
                  "releaseTag": "%s",
                  "packageDirectoryName": "%s",
                  "builtAt": "2026-06-16T00:00:00Z",
                  "publishScope": "code-only",
                  "component": "intruoyi",
                  "includeShowroomBuildPackage": false,
                  "onlyOfficeIncluded": false,
                  "artifacts": [%s]
                }
                """.formatted(directoryName, directoryName,
                withChecksum ? "{\"name\":\"image.tar\",\"sha256\":\"abc123\"}" : ""),
                StandardCharsets.UTF_8);
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

    private void createRestorePoint(String backupId) throws IOException {
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
                  "chainStatus": "COMPLETE",
                  "changeSummary": {"added": "0", "modified": "0", "deleted": "0", "reused": "1"}
                }
                """, StandardCharsets.UTF_8);
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

    private static void resetDirectory(Path path) throws IOException {
        if (Files.notExists(path)) {
            return;
        }
        try (var stream = Files.walk(path)) {
            List<Path> paths = stream.sorted(Comparator.reverseOrder()).toList();
            for (Path current : paths) {
                Files.deleteIfExists(current);
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
            return Files.isRegularFile(toLocal(path));
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
