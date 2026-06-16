package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.*;

@Service
public class RuntimeControlService {

    private static final String LOCAL_OPERATOR = "local-operator";
    private static final String PROD_CONFIRM_TEXT = "PROD";

    private final RuntimeControlProperties properties;
    private final RuntimeControlOperationStore operationStore;
    private final RuntimeControlCommandExecutor commandExecutor;
    private final RuntimeControlNasBrowser nasBrowser;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public RuntimeControlService(RuntimeControlProperties properties,
                                 RuntimeControlOperationStore operationStore,
                                 RuntimeControlCommandExecutor commandExecutor,
                                 RuntimeControlNasBrowser nasBrowser) {
        this.properties = properties;
        this.operationStore = operationStore;
        this.commandExecutor = commandExecutor;
        this.nasBrowser = nasBrowser;
    }

    public RuntimeControlOverviewRespVO getOverview() {
        Map<String, Map<String, RuntimeControlStatusRespVO>> statuses = new LinkedHashMap<>();
        LinkedHashSet<String> components = new LinkedHashSet<>();
        properties.getEnvironments().values().forEach(environment -> components.addAll(environment.getTargets().keySet()));
        for (Map.Entry<String, RuntimeControlProperties.Environment> envEntry : properties.getEnvironments().entrySet()) {
            Map<String, RuntimeControlStatusRespVO> envStatuses = new LinkedHashMap<>();
            for (Map.Entry<String, RuntimeControlProperties.Target> targetEntry : envEntry.getValue().getTargets().entrySet()) {
                envStatuses.put(targetEntry.getKey(), inspectTarget(envEntry.getKey(), envEntry.getValue(),
                        targetEntry.getKey(), targetEntry.getValue()));
            }
            statuses.put(envEntry.getKey(), envStatuses);
        }
        return new RuntimeControlOverviewRespVO(new ArrayList<>(properties.getEnvironments().keySet()),
                new ArrayList<>(components), statuses);
    }

    public RuntimeControlOperationRespVO restart(RuntimeControlRestartReqVO req) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment(req.environment());
        RuntimeControlProperties.Target target = properties.requireTarget(req.environment(), req.component());
        guardWrite(req.environment(), req.reason(), req.prodConfirmText());
        Path scriptPath = commandExecutor.resolveScriptPath(target.getRestartScript());
        if (!Files.isRegularFile(scriptPath)) {
            throw new RuntimeControlException("重启脚本不存在: " + scriptPath);
        }
        String operationId = nextOperationId();
        Path logPath = operationStore.operationLogPath(operationId);
        RuntimeControlCommand command = new RuntimeControlCommand(req.environment(), req.component(),
                target.getRestartScript(), target.restartArguments(environment, operationStore.operationPath(operationId).toString()));
        return startOperation(operationId, req.environment(), req.component(), "restart", "重启运行组件",
                Map.of("component", req.component()), req.reason(), command, logPath);
    }

    public RuntimeControlOperationRespVO executeAction(RuntimeControlActionReqVO req) {
        String operationId = nextOperationId();
        PreparedAction prepared = prepareAction(req, operationId, false);
        Path logPath = operationStore.operationLogPath(operationId);
        return startOperation(operationId, prepared.environment(), prepared.component(), prepared.action(),
                prepared.actionLabel(), prepared.parameters(), req.reason(), prepared.command(), logPath);
    }

    public RuntimeControlActionPreviewRespVO previewAction(RuntimeControlActionReqVO req) {
        PreparedAction prepared = prepareAction(req, "preview", true);
        return new RuntimeControlActionPreviewRespVO(prepared.action(), prepared.actionLabel(), prepared.environment(),
                prepared.component(), prepared.command().scriptPath(), prepared.command().arguments(),
                prepared.parameters(), Boolean.TRUE.equals(req.enableSmartReleaseReport()),
                "本机操作者 " + properties.getOperatorId() + " 将执行 " + prepared.actionLabel());
    }

    private PreparedAction prepareAction(RuntimeControlActionReqVO req, String operationId, boolean previewOnly) {
        RuntimeControlOperationAction action = RuntimeControlOperationAction.require(req.action());
        action.validateRequest(req);
        String environment = action.resolveEnvironment(req);
        guardWrite(environment, req.reason(), req.prodConfirmText(), action.requiresProductionGuard(req));
        RuntimeControlCommand command = action.buildCommand(req, properties);
        appendNasReleaseArguments(action, command, operationId, previewOnly);
        appendManagedSourceArguments(action, command);
        appendBackendRuntimeBaseArguments(action, command);
        Path scriptPath = commandExecutor.resolveScriptPath(command.scriptPath());
        if (!Files.isRegularFile(scriptPath)) {
            throw new RuntimeControlException("脚本不存在: " + scriptPath);
        }
        RuntimeControlCommand resolvedCommand = new RuntimeControlCommand(command.environment(), command.component(),
                scriptPath.toString(), command.arguments());
        return new PreparedAction(action.action(), action.label(), environment, action.action(),
                action.safeParameters(req), resolvedCommand);
    }

    private void appendNasReleaseArguments(RuntimeControlOperationAction action, RuntimeControlCommand command,
                                           String operationId, boolean previewOnly) {
        if (!action.requiresNasReleaseRepository()) {
            return;
        }
        RuntimeControlProperties.ReleasePackage releasePackage = properties.getReleasePackage();
        String nasServer = requireText(releasePackage.getNasServer(), "releasePackage.nasServer");
        String nasShare = requireText(releasePackage.getNasShare(), "releasePackage.nasShare");
        String nasReleaseRoot = requireText(releasePackage.getNasReleaseRoot(), "releasePackage.nasReleaseRoot");
        requireText(releasePackage.getNasUsername(), "releasePackage.nasUsername");
        requireText(releasePackage.getNasPassword(), "releasePackage.nasPassword");
        if (!previewOnly) {
            Path nasConfigPath = writeNasReleaseConfig(operationId, releasePackage);
            command.arguments().add("-NasConfigPath");
            command.arguments().add(nasConfigPath.toString());
        }
        command.arguments().add("-NasServer");
        command.arguments().add(nasServer);
        command.arguments().add("-NasShare");
        command.arguments().add(nasShare);
        command.arguments().add("-NasReleaseRoot");
        command.arguments().add(nasReleaseRoot);
    }

    private Path writeNasReleaseConfig(String operationId, RuntimeControlProperties.ReleasePackage releasePackage) {
        Path configPath = properties.stateDirPath().resolve("nas-release-config").resolve(operationId + ".json");
        Map<String, String> payload = new LinkedHashMap<>();
        payload.put("server", requireText(releasePackage.getNasServer(), "releasePackage.nasServer"));
        payload.put("share", requireText(releasePackage.getNasShare(), "releasePackage.nasShare"));
        payload.put("username", requireText(releasePackage.getNasUsername(), "releasePackage.nasUsername"));
        payload.put("password", requireText(releasePackage.getNasPassword(), "releasePackage.nasPassword"));
        try {
            Files.createDirectories(configPath.getParent());
            Files.writeString(configPath, objectMapper.writeValueAsString(payload), StandardCharsets.UTF_8);
            return configPath;
        } catch (JsonProcessingException ex) {
            throw new RuntimeControlException("无法序列化 NAS 发布包配置", ex);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法写入 NAS 发布包配置: " + configPath, ex);
        }
    }

    private void appendManagedSourceArguments(RuntimeControlOperationAction action, RuntimeControlCommand command) {
        if (!action.requiresNasReleaseRepository()) {
            return;
        }
        appendRequiredArgument(command.arguments(), "-BackendRepoRoot", properties.getRepoRoot());
        appendRequiredArgument(command.arguments(), "-FrontendRepoRoot", properties.getFrontendRoot());
        appendRequiredArgument(command.arguments(), "-WebsiteRepo", properties.getWebsiteRoot());
    }

    private void appendBackendRuntimeBaseArguments(RuntimeControlOperationAction action, RuntimeControlCommand command) {
        if (action != RuntimeControlOperationAction.BUILD_RELEASE) {
            return;
        }
        RuntimeControlProperties.ReleasePackage releasePackage = properties.getReleasePackage();
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseMode",
                releasePackage.getBackendRuntimeBaseMode());
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseTarPath",
                releasePackage.getBackendRuntimeBaseTarPath());
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseTarSha256",
                releasePackage.getBackendRuntimeBaseTarSha256());
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseImage",
                releasePackage.getBackendRuntimeBaseImage());
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseDigest",
                releasePackage.getBackendRuntimeBaseDigest());
        appendRequiredArgument(command.arguments(), "-BackendRuntimeBaseVersion",
                releasePackage.getBackendRuntimeBaseVersion());
    }

    private static void appendRequiredArgument(List<String> arguments, String name, String value) {
        arguments.add(name);
        arguments.add(requireText(value, name));
    }

    private static String requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new RuntimeControlException(name + " is required");
        }
        return value.trim();
    }

    public List<RuntimeControlOperationRespVO> getOperations() {
        return operationStore.listLatest(50);
    }

    public RuntimeControlLogRespVO getOperationLog(String operationId, Integer maxBytes) {
        RuntimeControlOperationRespVO operation = operationStore.findById(operationId);
        if (operation == null) {
            throw new RuntimeControlException("operation not found: " + operationId);
        }
        Path logPath = operationStore.operationLogPath(operationId);
        int limit = maxBytes == null || maxBytes <= 0 ? 65536 : maxBytes;
        try {
            if (Files.notExists(logPath)) {
                return new RuntimeControlLogRespVO(operationId, operation.status(), "", 0, false, logPath.toString());
            }
            byte[] bytes = Files.readAllBytes(logPath);
            boolean truncated = bytes.length > limit;
            int start = truncated ? bytes.length - limit : 0;
            String content = new String(bytes, start, bytes.length - start, StandardCharsets.UTF_8);
            return new RuntimeControlLogRespVO(operationId, operation.status(), content, bytes.length, truncated,
                    logPath.toString());
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取操作日志: " + operationId, ex);
        }
    }

    public List<RuntimeControlReleasePackageRespVO> getReleasePackages() {
        RuntimeControlProperties.ReleasePackage release = properties.getReleasePackage();
        List<RuntimeControlNasBrowser.NasEntry> entries = nasBrowser.listDirectories(new RuntimeControlNasBrowser.NasConfig(
                release.getNasServer(), release.getNasShare(), release.getNasUsername(), release.getNasPassword(),
                release.getNasDomain(), release.getNasReleaseRoot()));
        return entries.stream()
                .map(entry -> new RuntimeControlReleasePackageRespVO(entry.name(), entry.name(), entry.path(), null,
                        null, null, null, null, null, null, null, null, null, null, null, null,
                        "AVAILABLE", List.of()))
                .toList();
    }

    public RuntimeControlReleaseStatusRespVO getReleaseStatus() {
        return new RuntimeControlReleaseStatusRespVO(getReleasePackages(), getOverview().statuses(), getOperations(),
                null, null);
    }

    public List<RuntimeControlCandidateRespVO> getRollbackCandidates() {
        return getBackupCandidates();
    }

    public List<RuntimeControlCandidateRespVO> getRestoreCandidates() {
        return getBackupCandidates();
    }

    public List<RuntimeControlCandidateRespVO> getBackupPoints() {
        return getBackupCandidates();
    }

    public RuntimeControlCandidateRespVO getBackupPoint(String backupId) {
        return getBackupCandidates().stream()
                .filter(candidate -> backupId.equals(candidate.backupId()) || backupId.equals(candidate.candidateId()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("backup point not found: " + backupId));
    }

    public RuntimeControlInspectionRunRespVO runInspection() {
        Instant now = Instant.now();
        List<RuntimeControlInspectionCheckRespVO> checks = List.of(
                pathCheck("repo-root", "后端源码路径", properties.repoRootPath(), true),
                pathCheck("frontend-root", "前端源码路径", properties.frontendRootPath(), true),
                pathCheck("website-root", "展厅源码路径", properties.websiteRootPath(), true),
                pathCheck("ops-root", "运维脚本路径", properties.opsRootPath(), true)
        );
        String status = checks.stream().allMatch(check -> "PASS".equals(check.status())) ? "PASS" : "BLOCKED";
        return new RuntimeControlInspectionRunRespVO(System.currentTimeMillis(), status, "本机配置前置检查完成",
                now, Instant.now(), checks);
    }

    public RuntimeControlInspectionRunRespVO getInspectionRun(Long id) {
        throw new RuntimeControlException("独立控制台未持久化巡检历史: " + id);
    }

    public RuntimeControlBusinessHealthRespVO getBusinessHealth() {
        Instant now = Instant.now();
        List<RuntimeControlBusinessHealthItemRespVO> items = List.of(
                new RuntimeControlBusinessHealthItemRespVO("runtime-control", "独立控制台进程", "PASS",
                        "Spring Boot process is serving requests", null, now)
        );
        return new RuntimeControlBusinessHealthRespVO("PASS", now, items);
    }

    public RuntimeControlProbeLatestRespVO runProbes() {
        return getLatestProbes();
    }

    public RuntimeControlProbeLatestRespVO getLatestProbes() {
        Instant now = Instant.now();
        List<RuntimeControlProbeRespVO> probes = new ArrayList<>();
        for (Map.Entry<String, RuntimeControlProperties.Environment> envEntry : properties.getEnvironments().entrySet()) {
            for (Map.Entry<String, RuntimeControlProperties.Target> targetEntry : envEntry.getValue().getTargets().entrySet()) {
                RuntimeControlStatusRespVO status = inspectTarget(envEntry.getKey(), envEntry.getValue(),
                        targetEntry.getKey(), targetEntry.getValue());
                probes.add(new RuntimeControlProbeRespVO(envEntry.getKey(), targetEntry.getKey(),
                        normalizeProbeStatus(status.status()), status.url(), status.blockedReason(), now));
            }
        }
        return new RuntimeControlProbeLatestRespVO(now, probes);
    }

    public RuntimeControlCapacityStatusRespVO getCapacityStatus() {
        Instant now = Instant.now();
        List<RuntimeControlStorageMetricRespVO> metrics = List.of(storageMetric("state-dir", "运行态目录",
                properties.stateDirPath()), storageMetric("ops-root", "脚本目录", properties.opsRootPath()));
        String status = metrics.stream().allMatch(metric -> "PASS".equals(metric.status())) ? "PASS" : "BLOCKED";
        return new RuntimeControlCapacityStatusRespVO(status, now, metrics, null);
    }

    public RuntimeControlRemoteRootDiskStatusRespVO getRemoteRootDiskStatus(String targetEnvironment) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment(targetEnvironment);
        if (!environment.isAccessEnabled()) {
            throw new RuntimeControlException("远程根分区状态检查未授权: " + environment.getAccessDisabledReason());
        }
        throw new RuntimeControlException("远程根分区状态需要执行 SSH 只读脚本，本次独立抽取未自动执行远程命令");
    }

    public RuntimeControlRemoteRootCleanupRespVO cleanupRemoteRootTemporaryFiles(RuntimeControlRemoteRootCleanupReqVO req) {
        guardWrite(req.targetEnvironment(), req.reason(), req.prodConfirmText(), true);
        throw new RuntimeControlException("远程清理属于高风险动作，需另行授权后执行");
    }

    public PageResult<RuntimeControlAlertRespVO> getAlertsPage() {
        return PageResult.of(List.of());
    }

    public RuntimeControlAlertRespVO createAlert(RuntimeControlAlertCreateReqVO req) {
        return new RuntimeControlAlertRespVO(System.currentTimeMillis(), req.environment(), req.action(), req.severity(),
                req.title(), req.content(), req.notifyTemplateCode(), req.templateParams(), "BLOCKED", null,
                "独立本机控制台未接入站内信", Instant.now(), null, null, null);
    }

    public RuntimeControlAlertRespVO acknowledgeAlert(Long id) {
        throw new RuntimeControlException("独立控制台未持久化告警确认记录: " + id);
    }

    public PageResult<RuntimeControlIncidentRespVO> getIncidentsPage() {
        return PageResult.of(List.of());
    }

    public RuntimeControlIncidentRespVO createIncident(RuntimeControlIncidentCreateReqVO req) {
        return new RuntimeControlIncidentRespVO(System.currentTimeMillis(), req.environment(), req.severity(),
                req.title(), req.summary(), "OPEN", Instant.now(), null, null);
    }

    public RuntimeControlIncidentRespVO recordIncidentAction(Long id, RuntimeControlIncidentActionReqVO req) {
        throw new RuntimeControlException("独立控制台未持久化事故动作记录: " + id + ", action=" + req.action());
    }

    public RuntimeControlIncidentRespVO closeIncident(Long id, RuntimeControlIncidentCloseReqVO req) {
        return new RuntimeControlIncidentRespVO(id, null, null, null, null, "CLOSED", null, Instant.now(),
                req.conclusion());
    }

    private RuntimeControlOperationRespVO startOperation(String operationId, String environment, String component,
                                                         String action, String actionLabel,
                                                         Map<String, String> parameters, String reason,
                                                         RuntimeControlCommand command, Path logPath) {
        operationStore.initializeLog(logPath);
        RuntimeControlOperationRespVO operation = new RuntimeControlOperationRespVO(operationId, properties.getOperatorId(),
                Instant.now(), environment, component, action, actionLabel, parameters, reason, "RUNNING",
                "命令已提交到本机执行队列", logPath.toString());
        operationStore.save(operation);
        executor.submit(() -> {
            try {
                operationStore.appendLog(logPath, "operator=" + properties.getOperatorId() + System.lineSeparator());
                operationStore.appendLog(logPath, "command=" + String.join(" ", commandExecutor.executableCommand(command))
                        + System.lineSeparator());
                commandExecutor.run(command, logPath);
                operationStore.updateStatus(operationId, "SUCCESS", "命令执行完成");
            } catch (RuntimeException ex) {
                operationStore.appendLog(logPath, "ERROR: " + ex.getMessage() + System.lineSeparator());
                operationStore.updateStatus(operationId, "FAILED", ex.getMessage());
            }
        });
        return operation;
    }

    private RuntimeControlStatusRespVO inspectTarget(String environmentKey,
                                                     RuntimeControlProperties.Environment environment,
                                                     String component,
                                                     RuntimeControlProperties.Target target) {
        RuntimeControlOperationRespVO lastOperation = operationStore.findLatest(environmentKey, component);
        boolean enabled = environment.isAccessEnabled() && target.isActionEnabled();
        if ("prod".equals(environmentKey) && !properties.isProductionWriteEnabled()) {
            enabled = false;
        }
        String blockedReason = firstText(target.getBlockedReason(), environment.getAccessDisabledReason());
        if ("prod".equals(environmentKey) && !properties.isProductionWriteEnabled()) {
            blockedReason = "正式服写动作默认禁用，需显式配置 maintenance.runtime-control.production-write-enabled=true";
        }
        if (!environment.isLocal()) {
            return new RuntimeControlStatusRespVO("UNKNOWN", null, "REMOTE_NOT_PROBED", target.getUrl(), target.getPort(),
                    null, lastOperation, enabled, blockedReason);
        }
        return localHttpStatus(target, lastOperation, enabled, blockedReason);
    }

    private RuntimeControlStatusRespVO localHttpStatus(RuntimeControlProperties.Target target,
                                                       RuntimeControlOperationRespVO lastOperation,
                                                       boolean enabled,
                                                       String blockedReason) {
        if (target.getUrl() == null || target.getUrl().isBlank()) {
            return new RuntimeControlStatusRespVO("UNKNOWN", null, "MISSING_URL", null, target.getPort(),
                    null, lastOperation, enabled, "target url is required");
        }
        try {
            HttpURLConnection connection = (HttpURLConnection) URI.create(target.getUrl()).toURL().openConnection();
            connection.setConnectTimeout((int) properties.statusTimeout().toMillis());
            connection.setReadTimeout((int) properties.statusTimeout().toMillis());
            connection.setRequestMethod("GET");
            int status = connection.getResponseCode();
            String normalized = status >= 200 && status < 400 ? "RUNNING" : "DEGRADED";
            return new RuntimeControlStatusRespVO(normalized, String.valueOf(status), normalized, target.getUrl(),
                    target.getPort(), null, lastOperation, enabled, blockedReason);
        } catch (IOException | IllegalArgumentException ex) {
            return new RuntimeControlStatusRespVO("STOPPED", null, ex.getClass().getSimpleName(), target.getUrl(),
                    target.getPort(), null, lastOperation, enabled, firstText(blockedReason, ex.getMessage()));
        }
    }

    private List<RuntimeControlCandidateRespVO> getBackupCandidates() {
        RuntimeControlProperties.BackupOps backup = properties.getBackupOps();
        List<RuntimeControlNasBrowser.NasEntry> entries = nasBrowser.listDirectories(new RuntimeControlNasBrowser.NasConfig(
                backup.getNasServer(), backup.getNasShare(), backup.getNasUsername(), backup.getNasPassword(),
                backup.getNasDomain(), backup.getNasBackupPointsRoot()));
        return entries.stream()
                .map(entry -> new RuntimeControlCandidateRespVO(entry.name(), entry.name(), null, null,
                        entry.path(), "AVAILABLE", List.of()))
                .toList();
    }

    private RuntimeControlInspectionCheckRespVO pathCheck(String code, String name, Path path, boolean required) {
        boolean exists = Files.exists(path);
        return new RuntimeControlInspectionCheckRespVO(code, name, exists ? "PASS" : "BLOCKED", required,
                path.toString(), exists ? null : "路径不存在", Instant.now());
    }

    private RuntimeControlStorageMetricRespVO storageMetric(String code, String name, Path path) {
        try {
            Files.createDirectories(path);
            FileStore store = Files.getFileStore(path);
            long total = store.getTotalSpace();
            long usable = store.getUsableSpace();
            long used = total - usable;
            double usagePercent = total <= 0 ? 0D : (used * 100D / total);
            return new RuntimeControlStorageMetricRespVO(code, name, "PASS", used, usable, usagePercent, null);
        } catch (IOException ex) {
            return new RuntimeControlStorageMetricRespVO(code, name, "BLOCKED", null, null, null, ex.getMessage());
        }
    }

    private void guardWrite(String environment, String reason, String prodConfirmText) {
        guardWrite(environment, reason, prodConfirmText, "prod".equals(environment));
    }

    private void guardWrite(String environment, String reason, String prodConfirmText, boolean productionGuard) {
        if (reason == null || reason.isBlank()) {
            throw new RuntimeControlException("操作原因 reason is required");
        }
        if (!properties.getEnvironments().containsKey(environment)) {
            if (productionGuard) {
                throw new RuntimeControlException("生产级动作目标环境不存在: " + environment);
            }
            return;
        }
        RuntimeControlProperties.Environment targetEnvironment = properties.requireEnvironment(environment);
        if (!targetEnvironment.isAccessEnabled()) {
            throw new RuntimeControlException("环境未授权执行写动作: " + firstText(targetEnvironment.getAccessDisabledReason(), environment));
        }
        if (productionGuard) {
            if (!properties.isProductionWriteEnabled()) {
                throw new RuntimeControlException("正式服/生产级写动作默认禁用，需显式启用 production-write-enabled");
            }
            if (!PROD_CONFIRM_TEXT.equals(prodConfirmText)) {
                throw new RuntimeControlException("生产级动作必须提交确认文案 PROD");
            }
        }
    }

    private static String normalizeProbeStatus(String status) {
        return switch (status) {
            case "RUNNING" -> "PASS";
            case "DEGRADED", "UNKNOWN" -> "WARN";
            default -> "BLOCKED";
        };
    }

    private static String nextOperationId() {
        return "op-" + Instant.now().toString().replace(":", "").replace(".", "") + "-" + UUID.randomUUID();
    }

    private static String firstText(String first, String second) {
        return first != null && !first.isBlank() ? first : second;
    }

    private record PreparedAction(
            String action,
            String actionLabel,
            String environment,
            String component,
            Map<String, String> parameters,
            RuntimeControlCommand command
    ) {
    }
}
