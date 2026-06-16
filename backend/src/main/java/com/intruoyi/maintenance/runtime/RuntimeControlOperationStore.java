package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Comparator;
import java.util.List;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.RuntimeControlOperationRespVO;

@Component
public class RuntimeControlOperationStore {

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
                return stream.filter(path -> path.getFileName().toString().endsWith(".json"))
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
        save(new RuntimeControlOperationRespVO(
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
        ));
    }

    public Path stateDir() {
        return properties.stateDirPath();
    }

    private RuntimeControlOperationRespVO read(Path path) {
        try {
            return objectMapper.readValue(path.toFile(), RuntimeControlOperationRespVO.class);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取操作记录: " + path, ex);
        }
    }
}
