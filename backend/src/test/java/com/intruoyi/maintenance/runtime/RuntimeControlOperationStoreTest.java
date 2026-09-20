package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Map;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.RuntimeControlOperationRespVO;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RuntimeControlOperationStoreTest {

    @TempDir
    Path tempDir;

    @Test
    void buildLeaseIsAtomicAcrossStoreInstancesAndOwnedByOperationId() {
        RuntimeControlOperationStore first = store(tempDir);
        RuntimeControlOperationStore second = store(tempDir);

        assertThat(first.tryAcquireBuildLease("operation-a")).isTrue();
        assertThat(second.tryAcquireBuildLease("operation-b")).isFalse();
        assertThat(second.releaseBuildLease("operation-b")).isFalse();
        assertThat(first.releaseBuildLease("operation-a")).isTrue();
        assertThat(second.tryAcquireBuildLease("operation-b")).isTrue();
        assertThat(second.releaseBuildLease("operation-b")).isTrue();
    }

    @Test
    void staleLeaseMarkerWithoutAnOperatingSystemLockDoesNotBlockRestart() throws Exception {
        Files.writeString(tempDir.resolve("build-release.lease"), "dead-operation");
        RuntimeControlOperationStore restarted = store(tempDir);

        assertThat(restarted.tryAcquireBuildLease("operation-after-restart")).isTrue();
        assertThat(restarted.releaseBuildLease("operation-after-restart")).isTrue();
    }

    @Test
    void terminalStatusPersistsBeforeDiagnosticLogFailure() throws Exception {
        RuntimeControlOperationStore store = store(tempDir);
        Path blockedLogParent = tempDir.resolve("blocked-log-parent");
        Files.writeString(blockedLogParent, "not-a-directory");
        Path impossibleLog = blockedLogParent.resolve("operation.log");
        RuntimeControlOperationRespVO running = new RuntimeControlOperationRespVO(
                "operation-failure", "operator", Instant.now(), "release", "build-release",
                "build-release", "构建发布包", Map.of("releaseTag", "release-test"), "test",
                "RUNNING", "running", impossibleLog.toString());
        store.save(running);

        assertThatThrownBy(() -> store.completeOperation(
                "operation-failure", "FAILED", "command failed", impossibleLog, "ERROR: command failed"))
                .isInstanceOf(RuntimeControlException.class)
                .hasMessageContaining("无法写入操作日志");

        assertThat(store.findById("operation-failure").status()).isEqualTo("FAILED");
    }

    private static RuntimeControlOperationStore store(Path stateDir) {
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setStateDir(stateDir.toString());
        return new RuntimeControlOperationStore(properties);
    }
}
