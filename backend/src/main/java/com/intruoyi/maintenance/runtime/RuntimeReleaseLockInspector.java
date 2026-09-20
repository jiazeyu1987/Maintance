package com.intruoyi.maintenance.runtime;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Component
public class RuntimeReleaseLockInspector {

    private static final String OWNER_PREFIX = "LOCK_OWNER\t";

    private final RuntimeControlProperties properties;

    public RuntimeReleaseLockInspector(RuntimeControlProperties properties) {
        this.properties = properties;
    }

    public ReleaseOperationLockOwner requireTestLockOwner(String releaseTag) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment("test");
        String operationId = "test-" + requireText(releaseTag, "releaseTag");
        String sql = """
                SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
                SELECT CONCAT_WS('\\t', 'LOCK_OWNER',
                  COALESCE(executor_host, ''),
                  COALESCE(executor_pid, ''),
                  COALESCE(executor_identity, ''),
                  COALESCE(lease_token, '')
                )
                FROM infra_release_operation_lock
                WHERE target_environment = 'test'
                  AND operation_id = '%s'
                  AND release_tag = '%s'
                  AND status = 'RUNNING'
                ORDER BY id DESC
                LIMIT 1;
                """.formatted(sqlLiteral(operationId), sqlLiteral(releaseTag));
        String remote = """
                set -eu
                MYSQL_ROOT_PASSWORD=$(grep -E '^MYSQL_ROOT_PASSWORD=' '%s/.env' | head -n 1 | cut -d= -f2-)
                if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
                  echo 'LOCK_OWNER_BLOCKED_MISSING_DB_CREDENTIAL' >&2
                  exit 42
                fi
                export MYSQL_ROOT_PASSWORD
                docker exec -i -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro <<'SQL'
                %s
                SQL
                """.formatted(requireText(environment.getRemoteAppDir(), "test.remoteAppDir"), sql);
        List<String> command = sshCommand(environment, remote);
        ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
        try {
            Process process = builder.start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            boolean completed = process.waitFor(Duration.ofSeconds(30).toMillis(), TimeUnit.MILLISECONDS);
            if (!completed) {
                process.destroyForcibly();
                throw new RuntimeControlException("恢复锁所有权读取超时");
            }
            if (process.exitValue() != 0) {
                throw new RuntimeControlException("恢复锁所有权读取失败: exit=" + process.exitValue());
            }
            return parseOwner(output, operationId);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取远端发布锁所有权", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new RuntimeControlException("读取远端发布锁所有权被中断", ex);
        }
    }

    private ReleaseOperationLockOwner parseOwner(String output, String operationId) {
        String ownerLine = output.lines()
                .filter(line -> line.startsWith(OWNER_PREFIX))
                .reduce((first, second) -> second)
                .orElseThrow(() -> new RuntimeControlException("未找到 RUNNING 测试服发布锁: " + operationId));
        String[] parts = ownerLine.split("\\t", -1);
        if (parts.length != 5 || isBlank(parts[1]) || isBlank(parts[2]) || isBlank(parts[3]) || isBlank(parts[4])) {
            throw new RuntimeControlException("测试服发布锁缺少执行器身份或租约字段: " + operationId);
        }
        return new ReleaseOperationLockOwner(parts[1], parts[2], parts[3], parts[4]);
    }

    private List<String> sshCommand(RuntimeControlProperties.Environment environment, String remote) {
        String payload = Base64.getEncoder().encodeToString(remote.getBytes(StandardCharsets.UTF_8));
        List<String> command = new ArrayList<>();
        command.add("ssh");
        command.add("-n");
        command.add("-o");
        command.add("BatchMode=yes");
        command.add("-o");
        command.add("ConnectTimeout=10");
        command.add("-o");
        command.add("ConnectionAttempts=1");
        command.add("-o");
        command.add("StrictHostKeyChecking=no");
        command.add(requireText(environment.getServerUser(), "test.serverUser") + "@"
                + requireText(environment.getHost(), "test.host"));
        command.add("PAYLOAD='" + payload + "'; printf '%s' \"$PAYLOAD\" | base64 -d | bash");
        return command;
    }

    private static String sqlLiteral(String value) {
        return requireText(value, "sql literal").replace("'", "''");
    }

    private static String requireText(String value, String name) {
        if (isBlank(value)) {
            throw new RuntimeControlException(name + " is required");
        }
        return value;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
