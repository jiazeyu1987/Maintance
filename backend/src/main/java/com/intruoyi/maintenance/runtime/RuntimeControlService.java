package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.InvalidPathException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.*;

@Service
public class RuntimeControlService {

    private static final String LOCAL_OPERATOR = "local-operator";
    private static final String PROD_CONFIRM_TEXT = "PROD";
    private static final String STATUS_AVAILABLE = "AVAILABLE";
    private static final String STATUS_BLOCKED = "BLOCKED";
    private static final String ROLLBACK_PREFIX = "rollback:";
    private static final String RESTORE_PREFIX = "restore:";

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
        RuntimeControlActionReqVO resolvedReq = validateAndResolveAction(action, req);
        String environment = action.resolveEnvironment(resolvedReq);
        guardWrite(environment, resolvedReq.reason(), resolvedReq.prodConfirmText(), action.requiresProductionGuard(resolvedReq));
        RuntimeControlCommand command = action.buildCommand(resolvedReq, properties);
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
                action.safeParameters(resolvedReq), resolvedCommand);
    }

    private RuntimeControlActionReqVO validateAndResolveAction(RuntimeControlOperationAction action,
                                                               RuntimeControlActionReqVO req) {
        action.validateRequest(req);
        if (action == RuntimeControlOperationAction.ROLLBACK_APP) {
            if (hasText(req.selectedImageTag())) {
                throw new RuntimeControlException("selectedImageTag 只能由服务端候选解析");
            }
            RuntimeControlRollbackCandidateRespVO candidate = requireAvailableRollbackCandidate(req.selectedImageCandidateId());
            return copyActionReq(req, candidate.imageTag(), null, null, null, null, null);
        }
        if (action == RuntimeControlOperationAction.REHEARSAL || action == RuntimeControlOperationAction.RESTORE_DATA) {
            if (hasText(req.selectedBackupId())) {
                throw new RuntimeControlException("selectedBackupId 只能由服务端候选解析");
            }
            RuntimeControlRestoreCandidateRespVO candidate = requireAvailableRestoreCandidate(req.selectedRecoverySetCandidateId());
            return copyActionReq(req, null, candidate.backupId(), candidate.recoverySetId(),
                    candidate.recoverySetManifestHash(), candidate.programVersion(), candidate.redisPolicy());
        }
        if (action == RuntimeControlOperationAction.MARK_RELEASE_TESTED) {
            RuntimeControlRestoreCandidateRespVO candidate = requireAvailableRestoreCandidate(req.selectedRecoverySetCandidateId());
            return copyActionReq(req, null, candidate.backupId(), candidate.recoverySetId(),
                    candidate.recoverySetManifestHash(), candidate.programVersion(), candidate.redisPolicy());
        }
        if (action == RuntimeControlOperationAction.APPLY_TEST_DB_SQL) {
            return copyActionReqWithSqlPath(req, validateSqlPath(req.sqlPath()));
        }
        validateReleasePackageAvailability(action, req.releaseTag());
        return req;
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
        RuntimeControlNasBrowser.NasConfig nasConfig = releaseNasConfig();
        return nasBrowser.listDirectories(nasConfig).stream()
                .map(entry -> buildReleasePackageResponse(nasConfig, entry))
                .filter(item -> STATUS_AVAILABLE.equals(item.status()))
                .sorted(Comparator.comparing(RuntimeControlReleasePackageRespVO::builtAt,
                                Comparator.nullsLast(Comparator.reverseOrder()))
                        .thenComparing(RuntimeControlReleasePackageRespVO::releaseTag, Comparator.reverseOrder()))
                .toList();
    }

    public RuntimeControlReleaseStatusRespVO getReleaseStatus() {
        return new RuntimeControlReleaseStatusRespVO(getReleasePackages(), getOverview().statuses(), getOperations(),
                null, null);
    }

    public List<RuntimeControlRollbackCandidateRespVO> getRollbackCandidates() {
        RuntimeControlNasBrowser.NasConfig nasConfig = releaseNasConfig();
        return nasBrowser.listDirectories(nasConfig).stream()
                .limit(5)
                .map(entry -> buildRollbackCandidate(nasConfig, entry))
                .toList();
    }

    public List<RuntimeControlRestoreCandidateRespVO> getRestoreCandidates() {
        RuntimeControlNasBrowser.NasConfig nasConfig = backupNasConfig();
        return nasBrowser.listDirectories(nasConfig).stream()
                .limit(5)
                .map(entry -> buildRestoreCandidate(nasConfig, entry))
                .toList();
    }

    public List<RuntimeControlBackupPointRespVO> getBackupPoints() {
        return getRestoreCandidates().stream()
                .map(this::toBackupPoint)
                .toList();
    }

    public RuntimeControlBackupPointRespVO getBackupPoint(String backupId) {
        return getBackupPoints().stream()
                .filter(candidate -> backupId.equals(candidate.backupId()))
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

    public RuntimeControlAlertRespVO resendAlertSiteMessage(Long id) {
        return new RuntimeControlAlertRespVO(id, null, null, "INFO", "站内信重发", "独立本机控制台未接入站内信",
                null, Map.of(), "BLOCKED", null, "独立本机控制台未接入站内信", Instant.now(), null, null, null);
    }

    public RuntimeControlAlertRespVO acknowledgeAlert(Long id) {
        throw new RuntimeControlException("独立控制台未持久化告警确认记录: " + id);
    }

    public List<RuntimeControlOwnerMatrixRespVO> getOwnerMatrix(String environment, String action) {
        return List.of(defaultOwnerMatrix(environment, action));
    }

    public RuntimeControlOwnerMatrixRespVO createOwnerMatrix(RuntimeControlOwnerMatrixSaveReqVO req) {
        return ownerMatrixResponse(System.currentTimeMillis(), req);
    }

    public RuntimeControlOwnerMatrixRespVO updateOwnerMatrix(Long id, RuntimeControlOwnerMatrixSaveReqVO req) {
        return ownerMatrixResponse(id, req);
    }

    public List<RuntimeControlWizardScenarioRespVO> getWizardScenarios() {
        return List.of(
                new RuntimeControlWizardScenarioRespVO("publish-test", "部署测试服", "publish-test", "部署发布包到测试服",
                        List.of("测试环境需要更新"), List.of("发布包 manifest", "测试服目标主机"), List.of("owner"),
                        List.of("发布包不可用")),
                new RuntimeControlWizardScenarioRespVO("rollback-app", "回滚应用", "rollback-app", "回滚版本",
                        List.of("应用版本异常"), List.of("rollback-compatibility.json", "prod-latest.json"), List.of("owner"),
                        List.of("缺少可用回滚候选")),
                new RuntimeControlWizardScenarioRespVO("restore-data", "恢复数据", "restore-data", "恢复数据",
                        List.of("数据需要恢复"), List.of("备份 manifest", "checksum", "恢复演练证据"), List.of("owner"),
                        List.of("缺少可恢复备份点"))
        );
    }

    public RuntimeControlWizardRecommendationRespVO recommendWizardAction(RuntimeControlWizardRecommendationReqVO req) {
        String scenario = req.scenario();
        RuntimeControlWizardScenarioRespVO selected = getWizardScenarios().stream()
                .filter(item -> item.scenario().equals(scenario))
                .findFirst()
                .orElse(getWizardScenarios().get(0));
        return new RuntimeControlWizardRecommendationRespVO(selected.scenario(), selected.recommendedAction(),
                selected.recommendedActionLabel(), selected.requiredEvidence(), selected.requiredOwnerRoles(),
                selected.blockingConditions(), getRollbackCandidates(), getRestoreCandidates());
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

    private RuntimeControlReleasePackageRespVO buildReleasePackageResponse(RuntimeControlNasBrowser.NasConfig nasConfig,
                                                                           RuntimeControlNasBrowser.NasEntry entry) {
        String directoryName = entry.name();
        String packagePath = normalizeNasPath(entry.path());
        String manifestPath = childPath(packagePath, "release-manifest.json");
        List<String> blockedReasons = new ArrayList<>();
        List<String> packageFileNames = listFileNames(nasConfig, packagePath, blockedReasons);
        JsonNode manifest = packageFileNames.contains("release-manifest.json")
                ? readJson(nasConfig, manifestPath, "release-manifest.json", blockedReasons)
                : null;
        if (!packageFileNames.contains("release-manifest.json")) {
            blockedReasons.add("缺少 release-manifest.json");
        }

        String releaseTag = directoryName;
        String packageDirectoryName = directoryName;
        String builtAt = null;
        String publishScope = null;
        String component = null;
        Boolean includeShowroomBuildPackage = null;
        Boolean onlyOfficeIncluded = null;
        boolean checksumPresent = false;

        if (manifest != null) {
            releaseTag = blankToDefault(text(manifest, "releaseTag"), directoryName);
            packageDirectoryName = text(manifest, "packageDirectoryName");
            builtAt = text(manifest, "builtAt");
            publishScope = text(manifest, "publishScope");
            component = text(manifest, "component");
            includeShowroomBuildPackage = booleanValue(manifest, "includeShowroomBuildPackage");
            onlyOfficeIncluded = booleanValue(manifest, "onlyOfficeIncluded");
            if (isBlank(component)) {
                blockedReasons.add("release-manifest.json 缺少 component");
            } else if (!List.of("full", "intruoyi", "backend", "frontend", "website").contains(component)) {
                blockedReasons.add("release-manifest.json component 非法");
            }
            if (includeShowroomBuildPackage == null) {
                blockedReasons.add("release-manifest.json 缺少 includeShowroomBuildPackage");
            }
            if (onlyOfficeIncluded == null) {
                blockedReasons.add("release-manifest.json 缺少 onlyOfficeIncluded");
            }
            if (isBlank(packageDirectoryName)) {
                blockedReasons.add("release-manifest.json 缺少 packageDirectoryName");
            } else if (!directoryName.equals(packageDirectoryName)) {
                blockedReasons.add("release-manifest packageDirectoryName 与目录不一致");
            }
            checksumPresent = hasReleasePackageChecksum(manifest);
            if (!checksumPresent) {
                blockedReasons.add("release-manifest.json 缺少 artifact sha256");
            }
        }

        TestedMetadata tested = readTestedMetadata(nasConfig, packagePath, packageFileNames);
        return new RuntimeControlReleasePackageRespVO(releaseTag, packageDirectoryName, manifestPath, builtAt,
                publishScope, component, includeShowroomBuildPackage, onlyOfficeIncluded, packageDirectoryName,
                checksumPresent, tested.tested(), tested.testedAt(), tested.operatorName(),
                tested.selectedRecoverySetCandidateId(), tested.recoverySetId(), tested.recoverySetManifestHash(),
                blockedReasons.isEmpty() ? STATUS_AVAILABLE : STATUS_BLOCKED, blockedReasons);
    }

    private RuntimeControlRollbackCandidateRespVO buildRollbackCandidate(RuntimeControlNasBrowser.NasConfig nasConfig,
                                                                         RuntimeControlNasBrowser.NasEntry entry) {
        String directoryName = entry.name();
        String packagePath = normalizeNasPath(entry.path());
        String manifestPath = childPath(packagePath, "release-manifest.json");
        String prodHistoryPath = childPath(packagePath, "prod-latest.json");
        String compatibilityPath = childPath(packagePath, "rollback-compatibility.json");
        List<String> blockedReasons = new ArrayList<>();
        JsonNode manifest = readJsonIfRegular(nasConfig, manifestPath, "release-manifest.json", blockedReasons);
        String releaseTag = blankToDefault(text(manifest, "releaseTag"), directoryName);
        String packageDirectoryName = text(manifest, "packageDirectoryName");
        String imageTag = "";
        if (isBlank(packageDirectoryName)) {
            blockedReasons.add("release-manifest.json 缺少 packageDirectoryName");
        } else if (!directoryName.equals(packageDirectoryName)) {
            blockedReasons.add("release-manifest packageDirectoryName 与目录不一致");
        } else {
            imageTag = packageDirectoryName;
        }

        validateProdHistory(nasConfig, directoryName, prodHistoryPath, blockedReasons);
        RollbackCompatibility compatibility = readRollbackCompatibility(nasConfig, directoryName,
                compatibilityPath, blockedReasons);
        return new RuntimeControlRollbackCandidateRespVO(ROLLBACK_PREFIX + directoryName, directoryName, releaseTag,
                imageTag, manifestPath, blockedReasons.isEmpty() ? STATUS_AVAILABLE : STATUS_BLOCKED, blockedReasons,
                prodHistoryPath, compatibility.status(), compatibilityPath, compatibility.checkedAt(),
                compatibility.summary());
    }

    private RuntimeControlRestoreCandidateRespVO buildRestoreCandidate(RuntimeControlNasBrowser.NasConfig nasConfig,
                                                                       RuntimeControlNasBrowser.NasEntry entry) {
        String backupId = entry.name();
        String backupPath = normalizeNasPath(entry.path());
        String manifestPath = childPath(backupPath, "manifest", "manifest.json");
        String checksumPath = childPath(backupPath, "manifest", "checksums.txt");
        String dccManifestPath = childPath(backupPath, "manifest", "dcc-backup-manifest.json");
        String rehearsalReportPath = childPath(backupPath, "manifest", "rehearsal-report.json");
        String snapshotPath = childPath(backupPath, "manifest", "现场快照.md");
        List<String> blockedReasons = new ArrayList<>();
        ManifestEvidence manifest = readManifestEvidence(nasConfig, manifestPath, blockedReasons);
        JsonNode root = manifest.node();
        JsonNode recoverySet = node(root, "recoverySet");
        String recoverySetId = text(recoverySet, "id");
        String recoverySetStatus = text(recoverySet, "status");
        String programVersion = text(node(recoverySet, "program"), "imageTag");
        String redisPolicy = text(node(recoverySet, "redis"), "policy");
        String configurationManifestPath = text(node(recoverySet, "configuration"), "manifestPath");
        String configurationComposePath = text(node(recoverySet, "configuration"), "composePath");
        String recoverySetManifestHash = text(node(recoverySet, "checksums"), "sha256");
        if (isBlank(recoverySetId)) {
            blockedReasons.add("recoverySet.id 缺失");
        } else if (!backupId.equals(recoverySetId)) {
            blockedReasons.add("recoverySet.id 与备份目录不一致");
        }
        if (!"COMPLETE".equals(recoverySetStatus)) {
            blockedReasons.add("recoverySet.status 不是 COMPLETE");
        }
        if (isBlank(programVersion)) {
            blockedReasons.add("recoverySet.program.imageTag 缺失");
        }
        if (isBlank(redisPolicy)) {
            blockedReasons.add("recoverySet.redis.policy 缺失");
        }
        if (isBlank(configurationManifestPath)) {
            blockedReasons.add("recoverySet.configuration.manifestPath 缺失");
        }
        if (isBlank(configurationComposePath)) {
            blockedReasons.add("recoverySet.configuration.composePath 缺失");
        }
        if (isBlank(recoverySetManifestHash)) {
            blockedReasons.add("recoverySet.checksums.sha256 缺失");
        }
        if (!nasBrowser.isRegularFile(nasConfig, checksumPath)) {
            blockedReasons.add("缺少 checksum 清单");
        }
        DccRestoreSummary dccSummary = readDccRestoreSummary(nasConfig, dccManifestPath, blockedReasons);
        String imageTag = blankToDefault(programVersion, text(node(root, "deploy"), "imageTag"));
        if (isBlank(imageTag)) {
            imageTag = readOptionalText(nasConfig, childPath(backupPath, "deploy", "image-tag.txt"));
        }
        if (isBlank(imageTag)) {
            blockedReasons.add("恢复候选缺少 imageTag");
        }
        return new RuntimeControlRestoreCandidateRespVO(RESTORE_PREFIX + backupId, backupId, null, imageTag,
                manifestPath, blockedReasons.isEmpty() ? STATUS_AVAILABLE : STATUS_BLOCKED, blockedReasons,
                recoverySetId, recoverySetStatus, programVersion, redisPolicy, configurationManifestPath,
                configurationComposePath, manifest.sha256(), componentSummary(recoverySet), dccSummary.backupMode(),
                dccSummary.chainStatus(), dccSummary.changeSummary(), checksumPath, rehearsalReportPath, snapshotPath);
    }

    private RuntimeControlBackupPointRespVO toBackupPoint(RuntimeControlRestoreCandidateRespVO candidate) {
        return new RuntimeControlBackupPointRespVO(candidate.backupId(), candidate.manifestPath(), candidate.checksumPath(),
                candidate.rehearsalReportPath(), candidate.snapshotPath(), null, candidate.imageTag(), null, null,
                null, null, null, null, null, null, candidate.status(), candidate.dccBackupMode(),
                candidate.dccChainStatus(), candidate.dccChangeSummary(), null,
                STATUS_AVAILABLE.equals(candidate.status()) ? List.of() : candidate.blockedReasons());
    }

    private RuntimeControlRollbackCandidateRespVO requireAvailableRollbackCandidate(String candidateId) {
        if (isBlank(candidateId)) {
            throw new RuntimeControlException("selectedImageCandidateId is required");
        }
        RuntimeControlRollbackCandidateRespVO candidate = getRollbackCandidates().stream()
                .filter(item -> candidateId.equals(item.candidateId()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("selectedImageCandidateId 候选不存在: " + candidateId));
        if (!STATUS_AVAILABLE.equals(candidate.status())) {
            throw new RuntimeControlException("selectedImageCandidateId 候选被阻断: "
                    + String.join("；", candidate.blockedReasons()));
        }
        return candidate;
    }

    private RuntimeControlRestoreCandidateRespVO requireAvailableRestoreCandidate(String candidateId) {
        if (isBlank(candidateId)) {
            throw new RuntimeControlException("selectedRecoverySetCandidateId is required");
        }
        RuntimeControlRestoreCandidateRespVO candidate = getRestoreCandidates().stream()
                .filter(item -> candidateId.equals(item.candidateId()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("selectedRecoverySetCandidateId 候选不存在: " + candidateId));
        if (!STATUS_AVAILABLE.equals(candidate.status())) {
            throw new RuntimeControlException("selectedRecoverySetCandidateId 候选被阻断: "
                    + String.join("；", candidate.blockedReasons()));
        }
        return candidate;
    }

    private void validateReleasePackageAvailability(RuntimeControlOperationAction action, String releaseTag) {
        if (action != RuntimeControlOperationAction.PUBLISH_TEST
                && action != RuntimeControlOperationAction.PROMOTE_PROD
                && action != RuntimeControlOperationAction.PROMOTE_BACKUP) {
            return;
        }
        RuntimeControlReleasePackageRespVO releasePackage = getReleasePackages().stream()
                .filter(item -> releaseTag.equals(item.releaseTag()) || releaseTag.equals(item.packageDirectoryName()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("releaseTag 发布包缺少 manifest/checksum 或不存在: " + releaseTag));
        if ((action == RuntimeControlOperationAction.PROMOTE_PROD
                || action == RuntimeControlOperationAction.PROMOTE_BACKUP)
                && !Boolean.TRUE.equals(releasePackage.tested())) {
            throw new RuntimeControlException("releaseTag 尚未测试通过: " + releaseTag);
        }
        if (action == RuntimeControlOperationAction.PROMOTE_BACKUP
                && hasText(releasePackage.testedRecoverySetCandidateId())) {
            RuntimeControlRestoreCandidateRespVO candidate =
                    requireAvailableRestoreCandidate(releasePackage.testedRecoverySetCandidateId());
            if (!blankToDefault(releasePackage.testedRecoverySetId(), "").equals(candidate.recoverySetId())) {
                throw new RuntimeControlException("tested.json recoverySetId 与当前恢复集候选不一致");
            }
            if (!blankToDefault(releasePackage.testedRecoverySetManifestHash(), "").equals(candidate.recoverySetManifestHash())) {
                throw new RuntimeControlException("tested.json recoverySetManifestHash 与当前恢复集候选不一致");
            }
        }
    }

    private String validateSqlPath(String value) {
        if (isBlank(value)) {
            throw new RuntimeControlException("sqlPath is required");
        }
        Path sqlPath;
        try {
            sqlPath = Path.of(value.trim()).toAbsolutePath().normalize();
        } catch (InvalidPathException ex) {
            throw new RuntimeControlException("sqlPath 路径不合法: " + ex.getInput(), ex);
        }
        String fileName = sqlPath.getFileName() == null ? "" : sqlPath.getFileName().toString();
        if (!fileName.toLowerCase(Locale.ROOT).endsWith(".sql")) {
            throw new RuntimeControlException("sqlPath must point to a .sql file");
        }
        if (!Files.isRegularFile(sqlPath)) {
            throw new RuntimeControlException("sqlPath 文件不存在或不是普通文件: " + sqlPath);
        }
        try {
            if (Files.size(sqlPath) <= 0) {
                throw new RuntimeControlException("SQL file is empty");
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("sqlPath 文件不可读: " + sqlPath, ex);
        }
        return sqlPath.toString();
    }

    private RuntimeControlNasBrowser.NasConfig releaseNasConfig() {
        RuntimeControlProperties.ReleasePackage release = properties.getReleasePackage();
        return new RuntimeControlNasBrowser.NasConfig(requireText(release.getNasServer(), "releasePackage.nasServer"),
                requireText(release.getNasShare(), "releasePackage.nasShare"),
                requireText(release.getNasUsername(), "releasePackage.nasUsername"),
                requireText(release.getNasPassword(), "releasePackage.nasPassword"),
                release.getNasDomain(), requireText(release.getNasReleaseRoot(), "releasePackage.nasReleaseRoot"));
    }

    private RuntimeControlNasBrowser.NasConfig backupNasConfig() {
        RuntimeControlProperties.BackupOps backup = properties.getBackupOps();
        return new RuntimeControlNasBrowser.NasConfig(requireText(backup.getNasServer(), "backupOps.nasServer"),
                requireText(backup.getNasShare(), "backupOps.nasShare"),
                requireText(backup.getNasUsername(), "backupOps.nasUsername"),
                requireText(backup.getNasPassword(), "backupOps.nasPassword"),
                backup.getNasDomain(), requireText(backup.getNasBackupPointsRoot(), "backupOps.nasBackupPointsRoot"));
    }

    private List<String> listFileNames(RuntimeControlNasBrowser.NasConfig nasConfig, String path, List<String> blockedReasons) {
        try {
            return nasBrowser.listFiles(nasConfig, path).stream()
                    .filter(item -> !item.directory())
                    .map(RuntimeControlNasBrowser.NasEntry::name)
                    .toList();
        } catch (RuntimeControlException ex) {
            blockedReasons.add("目录读取失败: " + ex.getMessage());
            return List.of();
        }
    }

    private JsonNode readJsonIfRegular(RuntimeControlNasBrowser.NasConfig nasConfig, String path, String name,
                                       List<String> blockedReasons) {
        if (!nasBrowser.isRegularFile(nasConfig, path)) {
            blockedReasons.add("缺少 " + name);
            return null;
        }
        return readJson(nasConfig, path, name, blockedReasons);
    }

    private JsonNode readJson(RuntimeControlNasBrowser.NasConfig nasConfig, String path, String name,
                              List<String> blockedReasons) {
        try {
            return objectMapper.readTree(nasBrowser.readText(nasConfig, path));
        } catch (RuntimeControlException ex) {
            blockedReasons.add(name + " 读取失败: " + ex.getMessage());
            return null;
        } catch (IOException ex) {
            blockedReasons.add(name + " 解析失败: " + ex.getMessage());
            return null;
        }
    }

    private ManifestEvidence readManifestEvidence(RuntimeControlNasBrowser.NasConfig nasConfig, String path,
                                                  List<String> blockedReasons) {
        if (!nasBrowser.isRegularFile(nasConfig, path)) {
            blockedReasons.add("缺少 manifest/manifest.json");
            return new ManifestEvidence(null, "");
        }
        try {
            String content = nasBrowser.readText(nasConfig, path);
            return new ManifestEvidence(objectMapper.readTree(content), sha256(content));
        } catch (RuntimeControlException ex) {
            blockedReasons.add("manifest/manifest.json 读取失败: " + ex.getMessage());
            return new ManifestEvidence(null, "");
        } catch (IOException ex) {
            blockedReasons.add("manifest/manifest.json 解析失败: " + ex.getMessage());
            return new ManifestEvidence(null, "");
        }
    }

    private TestedMetadata readTestedMetadata(RuntimeControlNasBrowser.NasConfig nasConfig, String packagePath,
                                              List<String> fileNames) {
        if (!fileNames.contains("tested.json")) {
            return TestedMetadata.empty();
        }
        List<String> ignored = new ArrayList<>();
        JsonNode tested = readJson(nasConfig, childPath(packagePath, "tested.json"), "tested.json", ignored);
        if (tested == null) {
            return TestedMetadata.empty();
        }
        JsonNode recoverySet = node(tested, "recoverySet");
        return new TestedMetadata(true, text(tested, "testedAt"), text(tested, "operatorName"),
                text(recoverySet, "selectedRecoverySetCandidateId"), text(recoverySet, "recoverySetId"),
                text(recoverySet, "recoverySetManifestHash"));
    }

    private void validateProdHistory(RuntimeControlNasBrowser.NasConfig nasConfig, String directoryName,
                                     String prodHistoryPath, List<String> blockedReasons) {
        JsonNode history = readJsonIfRegular(nasConfig, prodHistoryPath, "正式服发布历史记录", blockedReasons);
        if (history == null) {
            return;
        }
        String packageDirectoryName = text(history, "packageDirectoryName");
        if (isBlank(packageDirectoryName)) {
            blockedReasons.add("prod-latest.json 缺少 packageDirectoryName");
        } else if (!directoryName.equals(packageDirectoryName)) {
            blockedReasons.add("prod-latest packageDirectoryName 与目录不一致");
        }
        String environment = text(history, "environment");
        if (hasText(environment) && !"prod".equals(environment)) {
            blockedReasons.add("prod-latest environment 不是 prod");
        }
    }

    private RollbackCompatibility readRollbackCompatibility(RuntimeControlNasBrowser.NasConfig nasConfig,
                                                            String directoryName, String path,
                                                            List<String> blockedReasons) {
        JsonNode compatibility = readJsonIfRegular(nasConfig, path, "rollback-compatibility.json", blockedReasons);
        if (compatibility == null) {
            return new RollbackCompatibility("", "", "");
        }
        String status = text(compatibility, "status");
        if (!"COMPATIBLE".equals(status)) {
            blockedReasons.add("rollback-compatibility.json status 不是 COMPATIBLE");
        }
        String packageDirectoryName = text(compatibility, "packageDirectoryName");
        if (isBlank(packageDirectoryName)) {
            blockedReasons.add("rollback-compatibility.json 缺少 packageDirectoryName");
        } else if (!directoryName.equals(packageDirectoryName)) {
            blockedReasons.add("rollback-compatibility packageDirectoryName 与目录不一致");
        }
        String checkedAt = text(compatibility, "checkedAt");
        if (isBlank(checkedAt)) {
            blockedReasons.add("rollback-compatibility.json 缺少 checkedAt");
        }
        String summary = text(compatibility, "summary");
        if (isBlank(summary)) {
            blockedReasons.add("rollback-compatibility.json 缺少 summary");
        }
        return new RollbackCompatibility(status, checkedAt, summary);
    }

    private DccRestoreSummary readDccRestoreSummary(RuntimeControlNasBrowser.NasConfig nasConfig, String path,
                                                    List<String> blockedReasons) {
        JsonNode dccManifest = readJsonIfRegular(nasConfig, path, "DCC backup manifest", blockedReasons);
        if (dccManifest == null) {
            return DccRestoreSummary.empty();
        }
        String schemaVersion = text(dccManifest, "schemaVersion");
        if (!"dcc-backup-manifest-v1".equals(schemaVersion)) {
            blockedReasons.add("DCC backup manifest schemaVersion 不支持: " + schemaVersion);
        }
        String backupMode = text(dccManifest, "backupMode");
        String chainStatus = text(dccManifest, "chainStatus");
        if (isBlank(backupMode)) {
            blockedReasons.add("DCC backup manifest 缺少 backupMode");
        }
        if (isBlank(chainStatus)) {
            blockedReasons.add("DCC backup manifest 缺少 chainStatus");
        }
        return new DccRestoreSummary(backupMode, chainStatus, stringMap(node(dccManifest, "changeSummary")));
    }

    private boolean hasReleasePackageChecksum(JsonNode manifest) {
        JsonNode artifacts = node(manifest, "artifacts");
        if (artifacts == null || !artifacts.isArray() || artifacts.isEmpty()) {
            return false;
        }
        for (JsonNode artifact : artifacts) {
            if (hasText(text(artifact, "sha256"))) {
                return true;
            }
        }
        return false;
    }

    private RuntimeControlOwnerMatrixRespVO defaultOwnerMatrix(String environment, String action) {
        return new RuntimeControlOwnerMatrixRespVO(1L, blankToDefault(environment, "test"),
                blankToDefault(action, "publish-test"), "owner", true, null, properties.getOperatorId(),
                "local-only", Instant.now());
    }

    private RuntimeControlOwnerMatrixRespVO ownerMatrixResponse(Long id, RuntimeControlOwnerMatrixSaveReqVO req) {
        return new RuntimeControlOwnerMatrixRespVO(id, req.environment(), req.action(), req.role(),
                req.required() == null || req.required(), req.ownerUserId(), req.ownerName(),
                req.escalationPath(), Instant.now());
    }

    private RuntimeControlActionReqVO copyActionReq(RuntimeControlActionReqVO req, String selectedImageTag,
                                                    String selectedBackupId, String recoverySetId,
                                                    String recoverySetManifestHash,
                                                    String recoverySetProgramVersion,
                                                    String recoverySetRedisPolicy) {
        return new RuntimeControlActionReqVO(req.action(), req.reason(), req.prodConfirmText(),
                req.targetEnvironment(), req.publishScope(), req.includeOnlyOffice(),
                req.includeShowroomBuildPackage(), req.enableSmartReleaseReport(), req.releaseTag(),
                req.testConclusion(), req.sqlPath(), req.selectedImageCandidateId(), selectedImageTag,
                req.selectedRecoverySetCandidateId(), selectedBackupId, recoverySetId, recoverySetManifestHash,
                recoverySetProgramVersion, recoverySetRedisPolicy);
    }

    private RuntimeControlActionReqVO copyActionReqWithSqlPath(RuntimeControlActionReqVO req, String sqlPath) {
        return new RuntimeControlActionReqVO(req.action(), req.reason(), req.prodConfirmText(),
                req.targetEnvironment(), req.publishScope(), req.includeOnlyOffice(),
                req.includeShowroomBuildPackage(), req.enableSmartReleaseReport(), req.releaseTag(),
                req.testConclusion(), sqlPath, req.selectedImageCandidateId(), req.selectedImageTag(),
                req.selectedRecoverySetCandidateId(), req.selectedBackupId(), req.recoverySetId(),
                req.recoverySetManifestHash(), req.recoverySetProgramVersion(), req.recoverySetRedisPolicy());
    }

    private Map<String, String> componentSummary(JsonNode recoverySet) {
        Map<String, String> result = new LinkedHashMap<>();
        result.put("program", text(node(recoverySet, "program"), "imageTag"));
        result.put("redis", text(node(recoverySet, "redis"), "policy"));
        result.put("configuration", text(node(recoverySet, "configuration"), "manifestPath"));
        return result;
    }

    private Map<String, String> stringMap(JsonNode node) {
        Map<String, String> result = new LinkedHashMap<>();
        if (node == null || !node.isObject()) {
            return result;
        }
        node.fields().forEachRemaining(entry -> result.put(entry.getKey(), entry.getValue().asText()));
        return result;
    }

    private JsonNode node(JsonNode node, String fieldName) {
        return node == null ? null : node.get(fieldName);
    }

    private String text(JsonNode node, String fieldName) {
        JsonNode field = node(node, fieldName);
        return field == null || field.isNull() ? "" : field.asText();
    }

    private Boolean booleanValue(JsonNode node, String fieldName) {
        JsonNode field = node(node, fieldName);
        return field != null && field.isBoolean() ? field.booleanValue() : null;
    }

    private String readOptionalText(RuntimeControlNasBrowser.NasConfig nasConfig, String path) {
        if (!nasBrowser.isRegularFile(nasConfig, path)) {
            return "";
        }
        return nasBrowser.readText(nasConfig, path).trim();
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new RuntimeControlException("无法计算 manifest sha256", ex);
        }
    }

    private static String childPath(String basePath, String... segments) {
        List<String> parts = new ArrayList<>();
        appendPathParts(parts, basePath);
        for (String segment : segments) {
            appendPathParts(parts, segment);
        }
        return String.join("/", parts);
    }

    private static String normalizeNasPath(String path) {
        return childPath(path);
    }

    private static void appendPathParts(List<String> parts, String path) {
        if (path == null) {
            return;
        }
        for (String part : path.replace("\\", "/").split("/")) {
            String token = part.trim();
            if (token.isBlank() || ".".equals(token)) {
                continue;
            }
            if ("..".equals(token)) {
                throw new RuntimeControlException("NAS path must not contain ..");
            }
            parts.add(token);
        }
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String blankToDefault(String value, String defaultValue) {
        return hasText(value) ? value.trim() : defaultValue;
    }

    private record TestedMetadata(
            boolean tested,
            String testedAt,
            String operatorName,
            String selectedRecoverySetCandidateId,
            String recoverySetId,
            String recoverySetManifestHash
    ) {
        private static TestedMetadata empty() {
            return new TestedMetadata(false, null, null, null, null, null);
        }
    }

    private record RollbackCompatibility(String status, String checkedAt, String summary) {
    }

    private record ManifestEvidence(JsonNode node, String sha256) {
    }

    private record DccRestoreSummary(String backupMode, String chainStatus, Map<String, String> changeSummary) {
        private static DccRestoreSummary empty() {
            return new DccRestoreSummary("", "", Map.of());
        }
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
