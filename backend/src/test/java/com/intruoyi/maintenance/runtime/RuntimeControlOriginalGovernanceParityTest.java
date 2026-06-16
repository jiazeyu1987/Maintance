package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import org.springframework.test.web.servlet.MvcResult;

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
        "maintenance.runtime-control.state-dir=../runtime/runtime-control-original-governance-parity-test",
        "maintenance.runtime-control.status-timeout-millis=50",
        "maintenance.runtime-control.production-write-enabled=true",
        "maintenance.runtime-control.backup-ops.execution-mode=linux-local",
        "maintenance.runtime-control.backup-ops.linux-script-path=backup-ops/linux/backup-ops-linux.sh",
        "maintenance.runtime-control.backup-ops.linux-config-path=/opt/intruoyi/ops/backup-ops/linux-native/backup-ops.linux-local.runtime.json",
        "maintenance.runtime-control.backup-ops.nas-server=unit-nas",
        "maintenance.runtime-control.backup-ops.nas-share=unit-share",
        "maintenance.runtime-control.backup-ops.nas-username=test-user",
        "maintenance.runtime-control.backup-ops.nas-password=test-password",
        "maintenance.runtime-control.backup-ops.nas-backup-points-root=Backup/BackupPackage",
        "maintenance.runtime-control.release-package.nas-server=unit-nas",
        "maintenance.runtime-control.release-package.nas-share=unit-share",
        "maintenance.runtime-control.release-package.nas-username=test-user",
        "maintenance.runtime-control.release-package.nas-password=test-password",
        "maintenance.runtime-control.release-package.nas-release-root=Backup/ReleasePackage"
})
@AutoConfigureMockMvc
class RuntimeControlOriginalGovernanceParityTest {

    private static final Path NAS_ROOT = Path.of("target/runtime-control-original-governance-parity-nas")
            .toAbsolutePath().normalize();

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private RuntimeControlOperationStore operationStore;

    @BeforeEach
    void setUp() throws Exception {
        resetDirectory(NAS_ROOT);
        resetDirectory(operationStore.stateDir());
        Files.createDirectories(NAS_ROOT.resolve("Backup/ReleasePackage"));
        Files.createDirectories(NAS_ROOT.resolve("Backup/BackupPackage"));
    }

    @Test
    void linuxLocalBackupPreviewUsesOriginalDashDashArguments() throws Exception {
        createRollbackPackage("release-rollback");

        String preview = mockMvc.perform(post("/admin-api/infra/runtime-control/actions/preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "rollback-app",
                                  "reason": "linux local preview",
                                  "targetEnvironment": "test",
                                  "selectedImageCandidateId": "rollback:release-rollback"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(preview)
                .contains("backup-ops-linux.sh", "--mode", "rollback-app", "--config",
                        "backup-ops.linux-local.runtime.json", "--non-interactive",
                        "--target-environment", "test", "--selected-image-tag", "release-rollback")
                .doesNotContain("-Mode", "-NonInteractive", "-SelectedImageTag", "-OperatorName");
    }

    @Test
    void governanceEndpointsPersistLocalFactsLikeOriginalStores() throws Exception {
        MvcResult inspection = mockMvc.perform(post("/admin-api/infra/runtime-control/inspection-runs"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn();
        long inspectionId = dataId(inspection);
        mockMvc.perform(get("/admin-api/infra/runtime-control/inspection-runs/{id}", inspectionId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.id").value(inspectionId));

        String scenarios = mockMvc.perform(get("/admin-api/infra/runtime-control/wizard/scenarios"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        assertThat(scenarios).contains("app-exception", "data-exception", "pre-release-check",
                "post-release-observation", "backup-drill", "disk-risk");

        MvcResult owner = mockMvc.perform(post("/admin-api/infra/runtime-control/owner-matrix")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "role": "release-owner",
                                  "required": true,
                                  "ownerUserId": 42,
                                  "ownerName": "qa-owner",
                                  "escalationPath": "本机值班"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andReturn();
        long ownerId = dataId(owner);
        mockMvc.perform(get("/admin-api/infra/runtime-control/owner-matrix")
                        .queryParam("environment", "test")
                        .queryParam("action", "publish-test"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data[0].ownerName").value("qa-owner"));
        mockMvc.perform(put("/admin-api/infra/runtime-control/owner-matrix/{id}", ownerId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "role": "release-owner",
                                  "required": true,
                                  "ownerUserId": 43,
                                  "ownerName": "qa-owner-2",
                                  "escalationPath": "本机复核"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.ownerName").value("qa-owner-2"));

        MvcResult alert = mockMvc.perform(post("/admin-api/infra/runtime-control/alerts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "severity": "WARN",
                                  "title": "测试告警",
                                  "content": "需要确认",
                                  "templateParams": {"source": "test"}
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.siteMessageStatus").value("BLOCKED"))
                .andReturn();
        long alertId = dataId(alert);
        mockMvc.perform(get("/admin-api/infra/runtime-control/alerts/page"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.list[0].id").value(alertId));
        mockMvc.perform(post("/admin-api/infra/runtime-control/alerts/{id}/acknowledge", alertId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.acknowledgedBy").value("local-operator"));

        MvcResult incident = mockMvc.perform(post("/admin-api/infra/runtime-control/incidents")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "environment": "test",
                                  "action": "publish-test",
                                  "severity": "P2",
                                  "title": "测试事故",
                                  "description": "接口异常",
                                  "sourceType": "DIRECT"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.status").value("OPEN"))
                .andReturn();
        long incidentId = dataId(incident);
        mockMvc.perform(post("/admin-api/infra/runtime-control/incidents/{id}/actions", incidentId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "action": "CHECK_LOG",
                                  "verificationResult": "PASS",
                                  "evidence": "log evidence"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.actions[0].action").value("CHECK_LOG"));
        mockMvc.perform(post("/admin-api/infra/runtime-control/incidents/{id}/close", incidentId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "ownerGateResult": "PASSED",
                                  "verificationResult": "PASSED",
                                  "remainingRisk": "无",
                                  "postmortemStatus": "DONE",
                                  "closeReason": "已恢复"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.status").value("CLOSED"));
        mockMvc.perform(get("/admin-api/infra/runtime-control/incidents/page"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.list[0].id").value(incidentId));
    }

    private long dataId(MvcResult result) throws IOException {
        JsonNode root = objectMapper.readTree(result.getResponse().getContentAsString(StandardCharsets.UTF_8));
        return root.path("data").path("id").asLong();
    }

    private void createRollbackPackage(String directoryName) throws IOException {
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
                  "artifacts": [{"name": "image.tar", "sha256": "abc123"}]
                }
                """.formatted(directoryName, directoryName), StandardCharsets.UTF_8);
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
