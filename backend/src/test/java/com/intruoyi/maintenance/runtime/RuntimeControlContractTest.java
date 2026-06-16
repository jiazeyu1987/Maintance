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
        "maintenance.runtime-control.status-timeout-millis=50"
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
}
