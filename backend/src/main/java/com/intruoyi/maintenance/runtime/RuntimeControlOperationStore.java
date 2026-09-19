package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.RuntimeControlOperationRespVO;

@Component
public class RuntimeControlOperationStore {

    private static final Pattern OPERATION_STATE_FILE_PATTERN = Pattern.compile("^op-[A-Za-z0-9._-]+\\.json$");

    private static final Set<String> RELEASE_ACTIONS = Set.of(
            "build-release",
            "publish-test",
            "mark-tested",
            "promote-prod",
            "promote-backup"
    );

    private final RuntimeControlProperties properties;
    private final ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());

    public RuntimeControlOperationStore(RuntimeControlProperties properties) {
        this.properties = properties;
    }

    public Path operationPath(String operationId) {
        return stateDir().resolve(operationId + ".json");
    }

    public Path operationLogPath(String operationId) {
        return stateDir().resolve("logs").resolve(operationId + ".log");
    }

    public void initializeLog(Path logPath) {
        try {
            Files.createDirectories(logPath.getParent());
            if (Files.notExists(logPath)) {
                Files.writeString(logPath, "", StandardCharsets.UTF_8);
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法初始化操作日志: " + logPath, ex);
        }
    }

    public void appendLog(Path logPath, String content) {
        try {
            Files.createDirectories(logPath.getParent());
            Files.writeString(logPath, content, StandardCharsets.UTF_8,
                    java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.APPEND);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法写入操作日志: " + logPath, ex);
        }
    }

    public void save(RuntimeControlOperationRespVO operation) {
        try {
            Files.createDirectories(stateDir());
            Path tmpPath = stateDir().resolve(operation.operationId() + ".json.tmp");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(tmpPath.toFile(), operation);
            Files.move(tmpPath, operationPath(operation.operationId()),
                    StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法保存操作记录: " + operation.operationId(), ex);
        }
    }

    public List<RuntimeControlOperationRespVO> listLatest(int limit) {
        try {
            if (Files.notExists(stateDir())) {
                return List.of();
            }
            try (var stream = Files.list(stateDir())) {
                return stream.filter(Files::isRegularFile)
                        .filter(RuntimeControlOperationStore::isOperationStateFile)
                        .sorted(Comparator.comparing((Path path) -> path.toFile().lastModified()).reversed())
                        .limit(limit)
                        .map(this::read)
                        .toList();
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取操作记录", ex);
        }
    }

    public RuntimeControlOperationRespVO findLatest(String environment, String component) {
        return listLatest(200).stream()
                .filter(operation -> environment.equals(operation.environment()) && component.equals(operation.component()))
                .findFirst()
                .orElse(null);
    }

    public RuntimeControlOperationRespVO findById(String operationId) {
        Path path = operationPath(operationId);
        return Files.isRegularFile(path) ? read(path) : null;
    }

    public void updateStatus(String operationId, String status, String summary) {
        RuntimeControlOperationRespVO current = findById(operationId);
        if (current == null) {
            throw new RuntimeControlException("operation not found: " + operationId);
        }
        RuntimeControlOperationRespVO updated = new RuntimeControlOperationRespVO(
                current.operationId(),
                current.requestedBy(),
                current.requestedAt(),
                current.environment(),
                current.component(),
                current.action(),
                current.actionLabel(),
                current.parameters(),
                current.reason(),
                status,
                summary,
                current.resultLogPath()
        );
        writeReleaseExperienceCandidate(updated);
        save(updated);
    }

    public Path stateDir() {
        return properties.stateDirPath();
    }

    private static boolean isOperationStateFile(Path path) {
        return OPERATION_STATE_FILE_PATTERN.matcher(path.getFileName().toString()).matches();
    }

    private RuntimeControlOperationRespVO read(Path path) {
        try {
            return objectMapper.readValue(path.toFile(), RuntimeControlOperationRespVO.class);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取操作记录: " + path, ex);
        }
    }

    private void writeReleaseExperienceCandidate(RuntimeControlOperationRespVO operation) {
        if (!RELEASE_ACTIONS.contains(operation.action())) {
            return;
        }
        if (!"SUCCESS".equals(operation.status()) && !"FAILED".equals(operation.status())) {
            return;
        }
        try {
            Path candidatePath = stateDir().resolve("release-experience-candidates.md");
            Files.createDirectories(candidatePath.getParent());
            Files.writeString(candidatePath, releaseExperienceCandidate(operation), StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException ex) {
            save(new RuntimeControlOperationRespVO(operation.operationId(), operation.requestedBy(),
                    operation.requestedAt(), operation.environment(), operation.component(), operation.action(),
                    operation.actionLabel(), operation.parameters(), operation.reason(), "FAILED",
                    "自动生成发布经验候选失败: " + stateDir().resolve("release-experience-candidates.md"),
                    operation.resultLogPath()));
            throw new RuntimeControlException("自动生成发布经验候选失败: " + stateDir()
                    .resolve("release-experience-candidates.md"), ex);
        }
    }

    private String releaseExperienceCandidate(RuntimeControlOperationRespVO operation) {
        String logSample = releaseLogSample(operation);
        String releaseTag = releaseTag(operation.parameters());
        StringBuilder builder = new StringBuilder();
        builder.append(System.lineSeparator()).append("## 发布经验候选 - ").append(operation.operationId())
                .append(System.lineSeparator()).append(System.lineSeparator());
        builder.append("- operationId: ").append(operation.operationId()).append(System.lineSeparator());
        builder.append("- action: ").append(operation.action()).append(System.lineSeparator());
        builder.append("- environment: ").append(operation.environment()).append(System.lineSeparator());
        builder.append("- releaseTag: ").append(isBlank(releaseTag) ? "(未提供)" : releaseTag).append(System.lineSeparator());
        builder.append("- status: ").append(operation.status()).append(System.lineSeparator());
        builder.append("- summary: ").append(trimToEmpty(operation.summary())).append(System.lineSeparator());
        builder.append("- 候选前置经验: ").append(releaseExperienceAdvice(operation, logSample)).append(System.lineSeparator());
        if (!isBlank(logSample)) {
            builder.append("- 日志摘录: ").append(logSample.replace(System.lineSeparator(), " | ")).append(System.lineSeparator());
        }
        return builder.toString();
    }

    private String releaseExperienceAdvice(RuntimeControlOperationRespVO operation, String logSample) {
        String haystack = (trimToEmpty(operation.summary()) + "\n" + trimToEmpty(logSample)).toLowerCase();
        if (haystack.contains("duplicate column") || haystack.contains("required sql")
                || haystack.contains("error 1060") || haystack.contains("error 1644")) {
            return "required SQL 必须前置做真实库可重入检查，覆盖字段存在性、菜单/角色/租户基线和幂等保护。";
        }
        if (haystack.contains("dirty=true") || haystack.contains("manifest")) {
            return "构建后必须复核 manifest 的 sourceRepos commit 与 dirty=false，不合格发布包直接判废。";
        }
        if (haystack.contains("minio") || haystack.contains("docker") || haystack.contains("remote")
                || haystack.contains("serverhost")) {
            return "发布前必须按目标环境真实基线核对远端目录、Docker root、数据盘设备和 MinIO 容器名。";
        }
        if ("SUCCESS".equals(operation.status())) {
            return "发布成功后仍需同时核 operation、manifest、远端 .env IMAGE_TAG、镜像 tag、backend health 与 frontend HTTP。";
        }
        return "将本次失败根因前移到发布前置门禁；修复后必须重新 build-release 生成新的 releaseTag。";
    }

    private String releaseLogSample(RuntimeControlOperationRespVO operation) {
        if (isBlank(operation.resultLogPath())) {
            return "";
        }
        Path logPath = Path.of(operation.resultLogPath());
        if (!Files.isRegularFile(logPath)) {
            return "";
        }
        try {
            List<String> matches = Files.readAllLines(logPath, StandardCharsets.UTF_8).stream()
                    .filter(line -> {
                        String value = line.toLowerCase();
                        return value.contains("error") || value.contains("failed") || value.contains("success")
                                || value.contains("manifest") || value.contains("required sql")
                                || value.contains("duplicate column") || value.contains("minio");
                    })
                    .limit(5)
                    .toList();
            return String.join(System.lineSeparator(), matches);
        } catch (IOException ex) {
            return "";
        }
    }

    private static String releaseTag(Map<String, String> parameters) {
        return parameters == null ? "" : trimToEmpty(parameters.get("releaseTag"));
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
