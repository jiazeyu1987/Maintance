package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.RuntimeControlOperationRespVO;
import static org.assertj.core.api.Assertions.assertThat;

class RuntimeControlOperationStoreTest {

    @TempDir
    Path stateDir;

    @Test
    void listLatestIgnoresNonOperationJsonFilesInStateRoot() throws Exception {
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setStateDir(stateDir.toString());
        RuntimeControlOperationStore store = new RuntimeControlOperationStore(properties);
        RuntimeControlOperationRespVO operation = new RuntimeControlOperationRespVO(
                "op-2026-09-02T010203Z-release",
                "tester",
                Instant.parse("2026-09-02T01:02:03Z"),
                "test",
                "intruoyi-backend",
                "build-release",
                "构建发布包",
                Map.of("releaseTag", "release-20260902-test-r1"),
                "state-dir contract test",
                "SUCCESS",
                "ok",
                stateDir.resolve("logs/op-2026-09-02T010203Z-release.log").toString()
        );

        store.save(operation);
        Files.writeString(stateDir.resolve("migration-policy.json"), "{not an operation json", StandardCharsets.UTF_8);

        List<RuntimeControlOperationRespVO> operations = store.listLatest(20);

        assertThat(operations)
                .extracting(RuntimeControlOperationRespVO::operationId)
                .containsExactly(operation.operationId());
    }
}
