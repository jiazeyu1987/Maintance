package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
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
        "maintenance.runtime-control.status-timeout-millis=50",
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
    void missingConfigurationFailsFast() {
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setRepoRoot("");
        properties.setFrontendRoot("D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3");
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
                .contains("-Mode", "build-release", "-SkipDatabaseSync", "-SkipMinioSync",
                        "-NasServer", "-NasShare", "-NasReleaseRoot")
                .doesNotContain("-ProdServerHost")
                .doesNotContain("test-password");
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
                        "-BackendRepoRoot", "D:/ProjectPackage/Int/IntRuoyi/ruoyi-vue-pro",
                        "-FrontendRepoRoot", "D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3",
                        "-WebsiteRepo", "D:/ProjectPackage/Website",
                        "-BackendRuntimeBaseMode", "-BackendRuntimeBaseTarPath",
                        "-BackendRuntimeBaseTarSha256", "-BackendRuntimeBaseImage",
                        "-BackendRuntimeBaseDigest", "-BackendRuntimeBaseVersion");
        assertThat(response)
                .doesNotContain("-SkipDatabaseSync")
                .doesNotContain("-SkipMinioSync")
                .doesNotContain("-ProdServerHost")
                .doesNotContain("test-password");
    }
}
