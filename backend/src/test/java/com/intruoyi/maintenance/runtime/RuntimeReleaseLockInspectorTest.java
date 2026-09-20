package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RuntimeReleaseLockInspectorTest {

    @Test
    void parsesRawMysqlTsvOwnerAndRejectsEscapedTabProtocol() {
        RuntimeReleaseLockInspector inspector = new RuntimeReleaseLockInspector(new RuntimeControlProperties());

        ReleaseOperationLockOwner owner = inspector.parseOwner(
                "noise\nLOCK_OWNER\tHOST-A\t12345\toperator@HOST-A\tlease-token\n",
                "test-release-a");

        assertThat(owner.executorHost()).isEqualTo("HOST-A");
        assertThat(owner.executorPid()).isEqualTo("12345");
        assertThat(owner.executorIdentity()).isEqualTo("operator@HOST-A");
        assertThat(owner.leaseToken()).isEqualTo("lease-token");
        assertThatThrownBy(() -> inspector.parseOwner(
                "LOCK_OWNER\\tHOST-A\\t12345\\toperator@HOST-A\\tlease-token\n",
                "test-release-a"))
                .isInstanceOf(RuntimeControlException.class)
                .hasMessageContaining("未找到 RUNNING 测试服发布锁");
    }

    @Test
    void remoteReaderUsesRawMysqlOutputAndWaitsBeforeReadingProcessOutput() throws Exception {
        String source = Files.readString(Path.of(
                "src/main/java/com/intruoyi/maintenance/runtime/RuntimeReleaseLockInspector.java"),
                StandardCharsets.UTF_8);

        assertThat(source).contains("--batch --raw --skip-column-names");
        assertThat(source.indexOf("process.waitFor(Duration.ofSeconds(30).toMillis(), TimeUnit.MILLISECONDS)"))
                .isLessThan(source.indexOf("process.getInputStream().readAllBytes()"));
        assertThat(source).doesNotContain("CONCAT_WS('\\\\t'");
    }
}
