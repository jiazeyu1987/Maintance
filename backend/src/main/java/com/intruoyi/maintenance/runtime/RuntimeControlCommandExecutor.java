package com.intruoyi.maintenance.runtime;

import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

@Component
public class RuntimeControlCommandExecutor {

    private final RuntimeControlProperties properties;

    public RuntimeControlCommandExecutor(RuntimeControlProperties properties) {
        this.properties = properties;
    }

    public List<String> executableCommand(RuntimeControlCommand command) {
        Path scriptPath = resolveScriptPath(command.scriptPath());
        if (!Files.isRegularFile(scriptPath)) {
            throw new RuntimeControlException("脚本不存在: " + scriptPath);
        }
        String fileName = scriptPath.getFileName().toString().toLowerCase();
        List<String> executable = new ArrayList<>();
        if (fileName.endsWith(".ps1")) {
            executable.add("powershell.exe");
            executable.add("-NoProfile");
            executable.add("-ExecutionPolicy");
            executable.add("Bypass");
            executable.add("-File");
            executable.add(scriptPath.toString());
        } else if (fileName.endsWith(".sh")) {
            executable.add("bash");
            executable.add(scriptPath.toString());
        } else if (fileName.endsWith(".py")) {
            executable.add("python");
            executable.add(scriptPath.toString());
        } else {
            executable.add(scriptPath.toString());
        }
        executable.addAll(command.arguments());
        return executable;
    }

    public Path resolveScriptPath(String scriptPath) {
        Path path = Path.of(scriptPath);
        if (!path.isAbsolute()) {
            path = properties.opsRootPath().resolve(scriptPath);
        }
        return path.toAbsolutePath().normalize();
    }

    public void run(RuntimeControlCommand command, Path logPath) {
        List<String> executable = executableCommand(command);
        ProcessBuilder builder = new ProcessBuilder(executable)
                .directory(properties.opsRootPath().toFile())
                .redirectErrorStream(true);
        try {
            Process process = builder.start();
            CompletableFuture<Void> outputPump = CompletableFuture.runAsync(() -> pumpOutput(process, logPath));
            Duration timeout = properties.commandTimeout();
            boolean completed = process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS);
            if (!completed) {
                process.descendants().forEach(ProcessHandle::destroyForcibly);
                process.destroyForcibly();
                outputPump.cancel(true);
                throw new RuntimeControlException("命令执行超时: " + timeout.toSeconds() + " 秒");
            }
            outputPump.join();
            int exitCode = process.exitValue();
            if (exitCode != 0) {
                throw new RuntimeControlException("命令退出码非 0: " + exitCode);
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法启动命令: " + sanitizeCommand(executable), ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new RuntimeControlException("命令执行被中断", ex);
        }
    }

    private void pumpOutput(Process process, Path logPath) {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                Files.writeString(logPath, line + System.lineSeparator(), StandardCharsets.UTF_8,
                        java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.APPEND);
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法写入命令日志: " + logPath, ex);
        }
    }

    private List<String> sanitizeCommand(List<String> command) {
        List<String> sanitized = new ArrayList<>(command);
        for (int index = 0; index < sanitized.size() - 1; index++) {
            if ("-ExpectedLeaseToken".equals(sanitized.get(index))) {
                sanitized.set(index + 1, "<redacted>");
            }
        }
        return sanitized;
    }
}
