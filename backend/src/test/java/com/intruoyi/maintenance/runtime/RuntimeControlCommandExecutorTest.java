package com.intruoyi.maintenance.runtime;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RuntimeControlCommandExecutorTest {

    @TempDir
    Path tempDir;

    @Test
    void interruptionTerminatesTheRunningProcess() throws Exception {
        Path script = tempDir.resolve("wait.ps1");
        Path pidFile = tempDir.resolve("process.pid");
        Path logFile = tempDir.resolve("process.log");
        Files.writeString(script, "[IO.File]::WriteAllText($args[0], [string]$PID); Start-Sleep -Seconds 60",
                StandardCharsets.UTF_8);
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setOpsRoot(tempDir.toString());
        properties.setCommandTimeoutSeconds(120);
        RuntimeControlCommandExecutor executor = new RuntimeControlCommandExecutor(properties);
        RuntimeControlCommand command = new RuntimeControlCommand(
                "release", "test", script.toString(), List.of(pidFile.toString()));
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread runner = new Thread(() -> {
            try {
                executor.run(command, logFile);
            } catch (Throwable ex) {
                failure.set(ex);
            }
        });
        runner.start();
        long pid = waitForPid(pidFile, Duration.ofSeconds(10));

        try {
            runner.interrupt();
            runner.join(Duration.ofSeconds(10).toMillis());

            assertThat(runner.isAlive()).isFalse();
            assertThat(failure.get()).isInstanceOf(RuntimeControlException.class)
                    .hasMessageContaining("命令执行被中断");
            assertThat(waitUntilStopped(pid, Duration.ofSeconds(5))).isTrue();
        } finally {
            ProcessHandle.of(pid).ifPresent(ProcessHandle::destroyForcibly);
        }
    }

    @Test
    void startupFailureRedactsLeaseTokenFromException() throws Exception {
        Path invalidExecutable = tempDir.resolve("invalid.exe");
        Files.writeString(invalidExecutable, "not an executable", StandardCharsets.UTF_8);
        RuntimeControlProperties properties = new RuntimeControlProperties();
        properties.setOpsRoot(tempDir.toString());
        RuntimeControlCommandExecutor executor = new RuntimeControlCommandExecutor(properties);
        RuntimeControlCommand command = new RuntimeControlCommand(
                "test", "recover-test-release-lock", invalidExecutable.toString(),
                List.of("-ExpectedLeaseToken", "lease-secret-value"));

        assertThatThrownBy(() -> executor.run(command, tempDir.resolve("invalid.log")))
                .isInstanceOf(RuntimeControlException.class)
                .hasMessageContaining("<redacted>")
                .hasMessageNotContaining("lease-secret-value");
    }

    private static long waitForPid(Path pidFile, Duration timeout) throws Exception {
        Instant deadline = Instant.now().plus(timeout);
        while (Instant.now().isBefore(deadline)) {
            if (Files.isRegularFile(pidFile) && Files.size(pidFile) > 0) {
                return Long.parseLong(Files.readString(pidFile, StandardCharsets.UTF_8).trim());
            }
            Thread.sleep(25);
        }
        throw new AssertionError("child process pid was not written");
    }

    private static boolean waitUntilStopped(long pid, Duration timeout) throws InterruptedException {
        Instant deadline = Instant.now().plus(timeout);
        while (Instant.now().isBefore(deadline)) {
            if (ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false) == false) {
                return true;
            }
            Thread.sleep(25);
        }
        return false;
    }
}
