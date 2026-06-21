package com.intruoyi.maintenance.runtime;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.InvalidPathException;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
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
import java.util.concurrent.TimeUnit;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Function;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.*;

@Service
public class RuntimeControlService {

    private static final String LOCAL_OPERATOR = "local-operator";
    private static final String PROD_CONFIRM_TEXT = "PROD";
    private static final String STATUS_AVAILABLE = "AVAILABLE";
    private static final String STATUS_BLOCKED = "BLOCKED";
    private static final String STATUS_NO_GO = "NO_GO";
    private static final String ROLLBACK_PREFIX = "rollback:";
    private static final String RESTORE_PREFIX = "restore:";
    private static final Long DEFAULT_RELEASE_OWNER_USER_ID = 1L;
    private static final String DEFAULT_RELEASE_OWNER_NAME = "admin";
    private static final List<RuntimeControlOwnerMatrixRespVO> DEFAULT_RELEASE_OWNERS = List.of(
            defaultOwner(-1001L, "prod", "promote-prod", "release-owner", "默认发布责任人"),
            defaultOwner(-1002L, "backup", "promote-backup", "release-owner", "默认发布责任人"),
            defaultOwner(-1003L, "prod", "rollback-app", "release-owner", "默认发布责任人"),
            defaultOwner(-1004L, "test", "rollback-app", "release-owner", "默认回滚发布责任人"),
            defaultOwner(-1005L, "backup", "rollback-app", "release-owner", "默认回滚发布责任人"),
            defaultOwner(-1006L, "test", "restore-data", "data-owner", "默认恢复数据责任人"),
            defaultOwner(-1007L, "backup", "restore-data", "data-owner", "默认恢复数据责任人"),
            defaultOwner(-1008L, "local", "storage-capacity-warning", "ops-owner", "默认容量告警责任人"),
            defaultOwner(-1009L, "test", "storage-capacity-warning", "ops-owner", "默认容量告警责任人"),
            defaultOwner(-1010L, "backup", "storage-capacity-warning", "ops-owner", "默认容量告警责任人"),
            defaultOwner(-1011L, "prod", "storage-capacity-warning", "ops-owner", "默认容量告警责任人"),
            defaultOwner(-1012L, "prod", "backup-now", "ops-owner", "默认备份责任人"),
            defaultOwner(-1013L, "test", "backup-now", "ops-owner", "默认备份责任人"),
            defaultOwner(-1014L, "backup", "backup-now", "ops-owner", "默认备份责任人"),
            defaultOwner(-1015L, "prod", "backup-scheduled", "ops-owner", "默认定时备份责任人"),
            defaultOwner(-1016L, "test", "rehearsal", "ops-owner", "默认恢复演练责任人"),
            defaultOwner(-1017L, "backup", "rehearsal", "ops-owner", "默认恢复演练责任人"),
            defaultOwner(-1018L, "test", "restore-data-started", "data-owner", "默认恢复数据责任人"),
            defaultOwner(-1019L, "backup", "restore-data-started", "data-owner", "默认恢复数据责任人"),
            defaultOwner(-1020L, "test", "restore-data-finished", "data-owner", "默认恢复数据责任人"),
            defaultOwner(-1021L, "backup", "restore-data-finished", "data-owner", "默认恢复数据责任人")
    );

    private final RuntimeControlProperties properties;
    private final RuntimeControlOperationStore operationStore;
    private final RuntimeControlCommandExecutor commandExecutor;
    private final RuntimeControlNasBrowser nasBrowser;
    private final ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());
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
        validateRequiredOwners(action, environment);
        guardWrite(environment, resolvedReq.reason(), resolvedReq.prodConfirmText(),
                action.requiresProductionGuard(resolvedReq), action.requiresProdConfirmText(resolvedReq));
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
        validateActionParameters(action, req);
        RuntimeControlActionReqVO resolvedReq = action == RuntimeControlOperationAction.MARK_RELEASE_TESTED
                ? copyActionReqWithReleaseTag(req, requireCurrentReleaseTag("test"))
                : req;
        action.validateRequest(resolvedReq);
        if (action == RuntimeControlOperationAction.ROLLBACK_APP) {
            if (hasText(resolvedReq.selectedImageTag())) {
                throw new RuntimeControlException("selectedImageTag 只能由服务端候选解析");
            }
            RuntimeControlRollbackCandidateRespVO candidate = requireAvailableRollbackCandidate(resolvedReq.selectedImageCandidateId());
            return copyActionReq(resolvedReq, candidate.imageTag(), null, null, null, null, null);
        }
        if (action == RuntimeControlOperationAction.REHEARSAL || action == RuntimeControlOperationAction.RESTORE_DATA) {
            if (hasText(resolvedReq.selectedBackupId())) {
                throw new RuntimeControlException("selectedBackupId 只能由服务端候选解析");
            }
            RuntimeControlRestoreCandidateRespVO candidate = requireAvailableRestoreCandidate(resolvedReq.selectedRecoverySetCandidateId());
            return copyActionReq(resolvedReq, null, candidate.backupId(), candidate.recoverySetId(),
                    candidate.recoverySetManifestHash(), candidate.programVersion(), candidate.redisPolicy());
        }
        if (action == RuntimeControlOperationAction.MARK_RELEASE_TESTED) {
            RuntimeControlRestoreCandidateRespVO candidate = requireAvailableRestoreCandidate(resolvedReq.selectedRecoverySetCandidateId());
            return copyActionReq(resolvedReq, null, candidate.backupId(), candidate.recoverySetId(),
                    candidate.recoverySetManifestHash(), candidate.programVersion(), candidate.redisPolicy());
        }
        if (action == RuntimeControlOperationAction.APPLY_TEST_DB_SQL) {
            return copyActionReqWithSqlPath(resolvedReq, validateSqlPath(resolvedReq.sqlPath()));
        }
        validateReleasePackageAvailability(action, resolvedReq.releaseTag());
        if (action == RuntimeControlOperationAction.PROMOTE_PROD) {
            return copyActionReqWithProdDryRunEvidencePath(resolvedReq, resolveProdDryRunEvidencePath(resolvedReq));
        }
        return resolvedReq;
    }

    private void validateActionParameters(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        validateActionTargetEnvironment(action, req);
        validatePublishScope(action, req);
        validateSqlParameter(action, req);
        validateReleaseTagParameter(action, req);
        validateSmartReleaseReport(action, req);
    }

    private void validateActionTargetEnvironment(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        if (action == RuntimeControlOperationAction.PUBLISH_TEST
                || action == RuntimeControlOperationAction.PROMOTE_PROD
                || action == RuntimeControlOperationAction.PROMOTE_BACKUP) {
            String targetEnvironment = trimToEmpty(req.targetEnvironment());
            if (hasText(targetEnvironment) && !action.defaultEnvironment().equals(targetEnvironment)) {
                throw new RuntimeControlException("targetEnvironment");
            }
            return;
        }
        if (action != RuntimeControlOperationAction.BACKUP_NOW
                && action != RuntimeControlOperationAction.ROLLBACK_APP
                && action != RuntimeControlOperationAction.RESTORE_DATA) {
            if (hasText(req.targetEnvironment())) {
                throw new RuntimeControlException("targetEnvironment");
            }
            return;
        }
        String targetEnvironment = trimToEmpty(req.targetEnvironment());
        if (isBlank(targetEnvironment)) {
            throw new RuntimeControlException("targetEnvironment is required");
        }
        List<String> allowedTargets = action == RuntimeControlOperationAction.RESTORE_DATA
                || action == RuntimeControlOperationAction.ROLLBACK_APP
                ? List.of("test", "backup")
                : List.of("test", "prod");
        if (!allowedTargets.contains(targetEnvironment)) {
            throw new RuntimeControlException("targetEnvironment");
        }
    }

    private void validatePublishScope(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        if (action != RuntimeControlOperationAction.BUILD_RELEASE) {
            if (hasText(req.publishScope())) {
                throw new RuntimeControlException("publishScope");
            }
            if (req.includeOnlyOffice() != null) {
                throw new RuntimeControlException("includeOnlyOffice");
            }
            if (req.includeShowroomBuildPackage() != null) {
                throw new RuntimeControlException("includeShowroomBuildPackage");
            }
            return;
        }
        if (isBlank(req.publishScope())) {
            throw new RuntimeControlException("publishScope is required");
        }
        if (req.includeOnlyOffice() == null) {
            throw new RuntimeControlException("includeOnlyOffice is required");
        }
        if (req.includeShowroomBuildPackage() == null) {
            throw new RuntimeControlException("includeShowroomBuildPackage is required");
        }
    }

    private void validateSqlParameter(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        if (action != RuntimeControlOperationAction.APPLY_TEST_DB_SQL && hasText(req.sqlPath())) {
            throw new RuntimeControlException("sqlPath");
        }
    }

    private void validateReleaseTagParameter(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        if (action == RuntimeControlOperationAction.MARK_RELEASE_TESTED) {
            return;
        }
        if (action == RuntimeControlOperationAction.PUBLISH_TEST
                || action == RuntimeControlOperationAction.PROMOTE_PROD
                || action == RuntimeControlOperationAction.PROMOTE_BACKUP) {
            validateReleaseTag(req.releaseTag());
            return;
        }
        if (hasText(req.releaseTag())) {
            validateReleaseTag(req.releaseTag());
        }
    }

    private void validateSmartReleaseReport(RuntimeControlOperationAction action, RuntimeControlActionReqVO req) {
        if (!Boolean.TRUE.equals(req.enableSmartReleaseReport())) {
            return;
        }
        if (action != RuntimeControlOperationAction.BUILD_RELEASE
                && action != RuntimeControlOperationAction.PUBLISH_TEST
                && action != RuntimeControlOperationAction.PROMOTE_PROD
                && action != RuntimeControlOperationAction.PROMOTE_BACKUP) {
            throw new RuntimeControlException("enableSmartReleaseReport");
        }
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
        List<RuntimeControlReleasePackageRespVO> releasePackages = getReleasePackages();
        RuntimeControlOverviewRespVO overview = getOverview();
        List<RuntimeControlOperationRespVO> recentReleaseOperations = getOperations().stream()
                .filter(operation -> List.of("build-release", "publish-test", "mark-release-tested",
                        "promote-prod", "promote-backup").contains(operation.action()))
                .limit(10)
                .toList();
        String latestTestedReleaseTag = releasePackages.stream()
                .filter(item -> Boolean.TRUE.equals(item.tested()))
                .map(RuntimeControlReleasePackageRespVO::releaseTag)
                .findFirst()
                .orElse(null);
        return new RuntimeControlReleaseStatusRespVO(releasePackages, overview.statuses(), recentReleaseOperations,
                resolveCurrentReleaseTag(overview, "test"), latestTestedReleaseTag);
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
                .filter(entry -> isRestorePointDirectory(nasConfig, entry))
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
        RuntimeControlInspectionRunRespVO run = new RuntimeControlInspectionRunRespVO(
                nextStateId("inspection-runs.json", RuntimeControlInspectionRunRespVO.class,
                        RuntimeControlInspectionRunRespVO::id),
                status, "本机配置前置检查完成", now, Instant.now(), checks);
        return saveStateItem("inspection-runs.json", RuntimeControlInspectionRunRespVO.class,
                RuntimeControlInspectionRunRespVO::id, run);
    }

    public RuntimeControlInspectionRunRespVO getInspectionRun(Long id) {
        return readStateList("inspection-runs.json", RuntimeControlInspectionRunRespVO.class).stream()
                .filter(run -> id != null && id.equals(run.id()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("巡检报告不存在：" + id));
    }

    public RuntimeControlBusinessHealthRespVO getBusinessHealth() {
        Instant now = Instant.now();
        List<RuntimeControlBusinessHealthItemRespVO> items = List.of(
                blockedBusinessHealth("login", "登录", "缺少登录真实用户路径只读采集器或合成登录探针配置", now),
                blockedBusinessHealth("erp", "ERP", "缺少 ERP 跨模块只读健康采集器配置", now),
                blockedBusinessHealth("mes", "MES", "缺少 MES 跨模块只读健康采集器配置", now),
                blockedBusinessHealth("file-object", "文件对象", "独立控制台未接入芋道文件配置数据库，无法确认文件上传/读取状态", now),
                blockedBusinessHealth("api-error", "API 错误", "独立控制台未接入芋道 API 错误日志，无法读取未处理错误", now),
                blockedBusinessHealth("slow-request", "慢请求", "独立控制台未接入芋道访问日志，无法读取慢请求", now),
                blockedBusinessHealth("job-failure", "任务失败", "独立控制台未接入芋道任务日志，无法读取任务失败", now)
        );
        return new RuntimeControlBusinessHealthRespVO(aggregateStatus(items.stream()
                .map(RuntimeControlBusinessHealthItemRespVO::status).toList()), now, items);
    }

    public RuntimeControlProbeLatestRespVO runProbes() {
        Instant now = Instant.now();
        List<RuntimeControlProbeRespVO> probes = new ArrayList<>();
        for (Map.Entry<String, RuntimeControlProperties.Environment> envEntry : properties.getEnvironments().entrySet()) {
            for (Map.Entry<String, RuntimeControlProperties.Target> targetEntry : envEntry.getValue().getTargets().entrySet()) {
                if (isProbeType(targetEntry.getValue().getActionComponent())) {
                    RuntimeControlStatusRespVO status = inspectTarget(envEntry.getKey(), envEntry.getValue(),
                            targetEntry.getKey(), targetEntry.getValue());
                    probes.add(new RuntimeControlProbeRespVO(envEntry.getKey(), targetEntry.getKey(),
                            targetEntry.getValue().getActionComponent(), targetEntry.getValue().getUrl(),
                            normalizeProbeStatus(status.status()), parseHttpStatus(status.httpStatus()), null,
                            "RUNNING".equals(status.status()) ? null : status.blockedReason(), now));
                }
            }
        }
        if (probes.isEmpty()) {
            probes = List.of(new RuntimeControlProbeRespVO("runtime-control", "backend/frontend/website",
                    "config", null, STATUS_BLOCKED, null, null, "未配置 backend/frontend/website 探针目标", now));
        }
        RuntimeControlAlertRespVO alert = createProbeFailureAlertIfNeeded(probes);
        RuntimeControlProbeLatestRespVO latest = new RuntimeControlProbeLatestRespVO(
                aggregateStatus(probes.stream().map(RuntimeControlProbeRespVO::status).toList()), now, probes, alert);
        writeStateObject("probes-latest.json", latest);
        return latest;
    }

    public RuntimeControlProbeLatestRespVO getLatestProbes() {
        Instant now = Instant.now();
        RuntimeControlProbeLatestRespVO latest = readStateObject("probes-latest.json", RuntimeControlProbeLatestRespVO.class);
        if (latest != null) {
            return latest;
        }
        return new RuntimeControlProbeLatestRespVO(STATUS_NO_GO, now,
                List.of(new RuntimeControlProbeRespVO("runtime-control", "backend/frontend/website",
                        "latest", null, STATUS_BLOCKED, null, null, "尚未执行探针，不能展示 PASS", now)),
                null);
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
        guardWrite(req.targetEnvironment(), req.reason(), req.prodConfirmText(), true, true);
        throw new RuntimeControlException("远程清理属于高风险动作，需另行授权后执行");
    }

    public synchronized PageResult<RuntimeControlAlertRespVO> getAlertsPage() {
        return PageResult.of(readStateList("alerts.json", RuntimeControlAlertRespVO.class).stream()
                .sorted(Comparator.comparing(RuntimeControlAlertRespVO::createdAt,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .toList());
    }

    public synchronized RuntimeControlAlertRespVO createAlert(RuntimeControlAlertCreateReqVO req) {
        Map<String, Object> templateParams = new LinkedHashMap<>();
        if (req.templateParams() != null) {
            templateParams.putAll(req.templateParams());
        }
        templateParams.putIfAbsent("environment", req.environment());
        templateParams.putIfAbsent("action", req.action());
        templateParams.putIfAbsent("severity", req.severity());
        templateParams.putIfAbsent("title", req.title());
        templateParams.putIfAbsent("content", req.content());

        String failureReason = resolveAlertBlockReason(req.environment(), req.action(), req.notifyTemplateCode());
        RuntimeControlAlertRespVO alert = new RuntimeControlAlertRespVO(
                nextStateId("alerts.json", RuntimeControlAlertRespVO.class, RuntimeControlAlertRespVO::id),
                trimToEmpty(req.environment()), trimToEmpty(req.action()), trimToEmpty(req.severity()),
                trimToEmpty(req.title()), trimToEmpty(req.content()), trimToEmpty(req.notifyTemplateCode()),
                templateParams, STATUS_BLOCKED, null, failureReason, Instant.now(), null, null, null);
        return saveStateItem("alerts.json", RuntimeControlAlertRespVO.class, RuntimeControlAlertRespVO::id, alert);
    }

    public synchronized RuntimeControlAlertRespVO resendAlertSiteMessage(Long id) {
        RuntimeControlAlertRespVO alert = requireAlert(id);
        RuntimeControlAlertRespVO updated = new RuntimeControlAlertRespVO(alert.id(), alert.environment(),
                alert.action(), alert.severity(), alert.title(), alert.content(), alert.notifyTemplateCode(),
                alert.templateParams(), STATUS_BLOCKED, null,
                resolveAlertBlockReason(alert.environment(), alert.action(), alert.notifyTemplateCode()),
                alert.createdAt(), null, alert.acknowledgedBy(), alert.acknowledgedAt());
        return saveStateItem("alerts.json", RuntimeControlAlertRespVO.class, RuntimeControlAlertRespVO::id, updated);
    }

    public synchronized RuntimeControlAlertRespVO acknowledgeAlert(Long id) {
        RuntimeControlAlertRespVO alert = requireAlert(id);
        validateRequiredOwners(alert.environment(), alert.action());
        RuntimeControlAlertRespVO updated = new RuntimeControlAlertRespVO(alert.id(), alert.environment(),
                alert.action(), alert.severity(), alert.title(), alert.content(), alert.notifyTemplateCode(),
                alert.templateParams(), alert.siteMessageStatus(), alert.notifyMessageId(),
                alert.siteMessageFailureReason(), alert.createdAt(), alert.sentAt(), properties.getOperatorId(),
                Instant.now());
        return saveStateItem("alerts.json", RuntimeControlAlertRespVO.class, RuntimeControlAlertRespVO::id, updated);
    }

    public synchronized List<RuntimeControlOwnerMatrixRespVO> getOwnerMatrix(String environment, String action) {
        return effectiveOwnerMatrix().stream()
                .filter(owner -> isBlank(environment) || environment.equals(owner.environment()))
                .filter(owner -> isBlank(action) || action.equals(owner.action()))
                .toList();
    }

    public synchronized RuntimeControlOwnerMatrixRespVO createOwnerMatrix(RuntimeControlOwnerMatrixSaveReqVO req) {
        validateOwnerMatrixReq(req);
        RuntimeControlOwnerMatrixRespVO owner = ownerMatrixResponse(
                nextStateId("owner-matrix.json", RuntimeControlOwnerMatrixRespVO.class,
                        RuntimeControlOwnerMatrixRespVO::id), req);
        return saveStateItem("owner-matrix.json", RuntimeControlOwnerMatrixRespVO.class,
                RuntimeControlOwnerMatrixRespVO::id, owner);
    }

    public synchronized RuntimeControlOwnerMatrixRespVO updateOwnerMatrix(Long id, RuntimeControlOwnerMatrixSaveReqVO req) {
        validateOwnerMatrixReq(req);
        if (id == null || readStateList("owner-matrix.json", RuntimeControlOwnerMatrixRespVO.class).stream()
                .noneMatch(owner -> id.equals(owner.id()))) {
            throw new RuntimeControlException("责任人矩阵不存在：" + id);
        }
        RuntimeControlOwnerMatrixRespVO owner = ownerMatrixResponse(id, req);
        return saveStateItem("owner-matrix.json", RuntimeControlOwnerMatrixRespVO.class,
                RuntimeControlOwnerMatrixRespVO::id, owner);
    }

    public List<RuntimeControlWizardScenarioRespVO> getWizardScenarios() {
        return List.of(
                new RuntimeControlWizardScenarioRespVO("app-exception", "应用异常", "rollback-app", "回滚版本",
                        List.of("生产应用启动失败", "发布后接口大面积异常"),
                        List.of("rollback-candidate", "backup-manifest", "operation-reason"),
                        List.of("release-owner"),
                        List.of("无服务端回滚候选", "候选缺 manifest", "缺生产确认 PROD", "缺发布责任人")),
                new RuntimeControlWizardScenarioRespVO("data-exception", "数据异常", "restore-data", "恢复数据",
                        List.of("数据误删", "需要回到指定备份"),
                        List.of("backup-manifest", "checksum"),
                        List.of("data-owner"),
                        List.of("无服务端恢复候选", "缺 manifest", "缺 checksum", "缺数据责任人")),
                new RuntimeControlWizardScenarioRespVO("pre-release-check", "发布前检查", "inspection-run", "执行一键巡检",
                        List.of("准备发布测试服或正式服", "发布前需要确认关键证据"),
                        List.of("inspection-report", "business-health", "probe", "backup-point", "capacity-status"),
                        List.of("release-owner"),
                        List.of("缺关键证据", "业务健康未通过", "核心探针失败", "缺备份演练", "磁盘容量风险未关闭")),
                new RuntimeControlWizardScenarioRespVO("post-release-observation", "发布后观察", "inspection-run", "执行一键巡检",
                        List.of("发布后需要观察系统是否稳定", "发布后接口或页面出现异常反馈"),
                        List.of("inspection-report", "business-health", "probe", "api-error", "slow-request"),
                        List.of("release-owner", "reviewer"),
                        List.of("缺巡检报告", "发布后探针失败", "业务健康 NO_GO", "API 错误或慢请求未确认")),
                new RuntimeControlWizardScenarioRespVO("backup-drill", "备份演练", "backup-points", "查看备份演练",
                        List.of("备份演练失败", "恢复前需要确认备份点可恢复"),
                        List.of("backup-manifest", "checksum", "rehearsal-report", "last-verified-at"),
                        List.of("data-owner"),
                        List.of("缺 manifest", "缺 checksum", "缺演练报告", "最近验证时间缺失")),
                new RuntimeControlWizardScenarioRespVO("disk-risk", "磁盘风险", "capacity-status", "查看容量状态",
                        List.of("日志增长过快", "磁盘容量超过阈值"),
                        List.of("capacity-status", "log-directory-size", "disk-usage", "alert"),
                        List.of("ops-owner"),
                        List.of("磁盘采样阻断", "日志目录超过阈值", "容量告警未确认"))
        );
    }

    public RuntimeControlWizardRecommendationRespVO recommendWizardAction(RuntimeControlWizardRecommendationReqVO req) {
        String scenario = req.scenario();
        RuntimeControlWizardScenarioRespVO selected = getWizardScenarios().stream()
                .filter(item -> item.scenario().equals(scenario))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("scenario 不支持：" + scenario));
        List<RuntimeControlRollbackCandidateRespVO> rollbackCandidates = "rollback-app".equals(selected.recommendedAction())
                ? getRollbackCandidates() : List.of();
        List<RuntimeControlRestoreCandidateRespVO> restoreCandidates = "restore-data".equals(selected.recommendedAction())
                ? getRestoreCandidates() : List.of();
        List<String> blockingReasons = "rollback-app".equals(selected.recommendedAction())
                ? collectRollbackBlockingReasons(rollbackCandidates)
                : "restore-data".equals(selected.recommendedAction())
                ? collectRestoreBlockingReasons(restoreCandidates)
                : selected.blockingConditions();
        return new RuntimeControlWizardRecommendationRespVO(selected.scenario(), selected.recommendedAction(),
                selected.recommendedActionLabel(), selected.requiredEvidence(), selected.requiredOwnerRoles(),
                blockingReasons, rollbackCandidates, restoreCandidates);
    }

    public synchronized PageResult<RuntimeControlIncidentRespVO> getIncidentsPage() {
        return PageResult.of(readStateList("incidents.json", RuntimeControlIncidentRespVO.class).stream()
                .sorted(Comparator.comparing(RuntimeControlIncidentRespVO::createdAt,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .toList());
    }

    public synchronized RuntimeControlIncidentRespVO createIncident(RuntimeControlIncidentCreateReqVO req) {
        validateIncidentCreateReq(req);
        RuntimeControlIncidentRespVO incident = new RuntimeControlIncidentRespVO(
                nextStateId("incidents.json", RuntimeControlIncidentRespVO.class, RuntimeControlIncidentRespVO::id),
                trimToEmpty(req.environment()), trimToEmpty(req.action()), trimToEmpty(req.severity()),
                trimToEmpty(req.title()), trimToEmpty(req.description()), normalizeSourceType(req.sourceType()),
                trimToEmpty(req.sourceId()), "OPEN", properties.getOperatorId(), Instant.now(), List.of(),
                null, null, null, null, null, null, null);
        return saveStateItem("incidents.json", RuntimeControlIncidentRespVO.class, RuntimeControlIncidentRespVO::id,
                incident);
    }

    public synchronized RuntimeControlIncidentRespVO recordIncidentAction(Long id, RuntimeControlIncidentActionReqVO req) {
        RuntimeControlIncidentRespVO incident = requireOpenIncident(id);
        List<RuntimeControlIncidentActionRespVO> actions = new ArrayList<>();
        if (incident.actions() != null) {
            actions.addAll(incident.actions());
        }
        actions.add(new RuntimeControlIncidentActionRespVO(trimToEmpty(req.action()), properties.getOperatorId(),
                trimToEmpty(req.verificationResult()), trimToEmpty(req.evidence()), Instant.now()));
        RuntimeControlIncidentRespVO updated = copyIncident(incident, actions, incident.ownerGateResult(),
                incident.verificationResult(), incident.remainingRisk(), incident.postmortemStatus(),
                incident.closeReason(), incident.closedBy(), incident.closedAt(), "OPEN");
        return saveStateItem("incidents.json", RuntimeControlIncidentRespVO.class, RuntimeControlIncidentRespVO::id,
                updated);
    }

    public synchronized RuntimeControlIncidentRespVO closeIncident(Long id, RuntimeControlIncidentCloseReqVO req) {
        RuntimeControlIncidentRespVO incident = requireOpenIncident(id);
        validateRequiredOwners(incident.environment(), incident.action());
        validateIncidentCloseReq(req);
        RuntimeControlIncidentRespVO closed = copyIncident(incident, incident.actions(),
                trimToEmpty(req.ownerGateResult()).toUpperCase(Locale.ROOT),
                trimToEmpty(req.verificationResult()).toUpperCase(Locale.ROOT), trimToEmpty(req.remainingRisk()),
                trimToEmpty(req.postmortemStatus()).toUpperCase(Locale.ROOT), trimToEmpty(req.closeReason()),
                properties.getOperatorId(), Instant.now(), "CLOSED");
        return saveStateItem("incidents.json", RuntimeControlIncidentRespVO.class, RuntimeControlIncidentRespVO::id,
                closed);
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

    private boolean isRestorePointDirectory(RuntimeControlNasBrowser.NasConfig nasConfig,
                                            RuntimeControlNasBrowser.NasEntry entry) {
        String manifestPath = childPath(normalizeNasPath(entry.path()), "manifest", "manifest.json");
        try {
            return nasBrowser.isRegularFile(nasConfig, manifestPath);
        } catch (RuntimeException ex) {
            return false;
        }
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
            if (action != RuntimeControlOperationAction.PROMOTE_BACKUP
                    || !hasSuccessfulCodeOnlyTestDeployment(releasePackage)) {
                throw new RuntimeControlException("releaseTag 尚未测试通过: " + releaseTag);
            }
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

    private boolean hasSuccessfulCodeOnlyTestDeployment(RuntimeControlReleasePackageRespVO releasePackage) {
        if (!RuntimeControlOperationAction.PUBLISH_SCOPE_CODE_ONLY.equals(releasePackage.publishScope())) {
            return false;
        }
        return operationStore.listLatest(200).stream()
                .filter(operation -> "test".equals(operation.environment()))
                .filter(operation -> "publish-test".equals(operation.action()))
                .filter(operation -> "SUCCESS".equals(operation.status()))
                .map(RuntimeControlOperationRespVO::parameters)
                .filter(parameters -> parameters != null && hasText(parameters.get("releaseTag")))
                .map(parameters -> parameters.get("releaseTag").trim())
                .anyMatch(value -> releaseTagMatchesPackage(releasePackage, value));
    }

    private boolean releaseTagMatchesPackage(RuntimeControlReleasePackageRespVO releasePackage, String value) {
        return value.equals(releasePackage.releaseTag()) || value.equals(releasePackage.packageDirectoryName());
    }

    private String requireCurrentReleaseTag(String environment) {
        String releaseTag = resolveCurrentReleaseTag(getOverview(), environment);
        if (isBlank(releaseTag)) {
            throw new RuntimeControlException(environment + " currentReleaseTag is required");
        }
        validateReleaseTag(releaseTag);
        return releaseTag;
    }

    private String resolveCurrentReleaseTag(RuntimeControlOverviewRespVO overview, String environment) {
        Map<String, RuntimeControlStatusRespVO> statuses = overview.statuses().get(environment);
        if (statuses != null) {
            String statusReleaseTag = statuses.values().stream()
                    .map(RuntimeControlStatusRespVO::currentReleaseTag)
                    .filter(RuntimeControlService::hasText)
                    .findFirst()
                    .orElse(null);
            if (hasText(statusReleaseTag)) {
                return statusReleaseTag.trim();
            }
        }
        return operationStore.listLatest(200).stream()
                .filter(operation -> environment.equals(operation.environment()))
                .filter(operation -> "SUCCESS".equals(operation.status()))
                .filter(operation -> "publish-test".equals(operation.action()))
                .map(RuntimeControlOperationRespVO::parameters)
                .filter(parameters -> parameters != null && hasText(parameters.get("releaseTag")))
                .map(parameters -> parameters.get("releaseTag").trim())
                .findFirst()
                .orElse(null);
    }

    private void validateReleaseTag(String releaseTag) {
        if (isBlank(releaseTag)) {
            throw new RuntimeControlException("releaseTag is required");
        }
        String trimmed = releaseTag.trim();
        if (trimmed.contains("..") || trimmed.contains("/") || trimmed.contains("\\")) {
            throw new RuntimeControlException("releaseTag 不合法: " + trimmed);
        }
    }

    private String resolveProdDryRunEvidencePath(RuntimeControlActionReqVO req) {
        if (hasText(req.prodDryRunEvidencePath())) {
            return validateProdDryRunEvidencePath(req.prodDryRunEvidencePath());
        }
        return generateProdDryRunEvidence(req.releaseTag());
    }

    private String validateProdDryRunEvidencePath(String prodDryRunEvidencePath) {
        try {
            Path path = Paths.get(prodDryRunEvidencePath.trim()).toAbsolutePath().normalize();
            if (!Files.isRegularFile(path)) {
                throw new RuntimeControlException("prodDryRunEvidencePath 文件不存在或不是普通文件: " + path);
            }
            return path.toString();
        } catch (InvalidPathException ex) {
            throw new RuntimeControlException("prodDryRunEvidencePath 路径不合法: " + ex.getInput(), ex);
        }
    }

    private String generateProdDryRunEvidence(String releaseTag) {
        RuntimeControlProperties.ReleasePackage releasePackage = properties.getReleasePackage();
        Path targetConfigPath = Path.of(requireText(releasePackage.getSmartReleaseTargetConfigPath(),
                        "releasePackage.smartReleaseTargetConfigPath"))
                .toAbsolutePath().normalize();
        if (!Files.isRegularFile(targetConfigPath)) {
            throw new RuntimeControlException("正式 Smart Release target config 不存在: " + targetConfigPath);
        }

        Path releaseDir = locateReleasePackageWorkspace(releaseTag);
        Path evidenceDir = properties.stateDirPath().resolve("prod-preflight-release-evidence");
        Path reportPath = evidenceDir.resolve(releaseTag + "-deploy-precheck-report.json");
        Path dryRunEvidencePath = evidenceDir.resolve(releaseTag + "-preflight-release-dry-run.json");
        Path scriptPath = commandExecutor.resolveScriptPath("release/run-deploy-precheck-report.ps1");
        if (!Files.isRegularFile(scriptPath)) {
            throw new RuntimeControlException("deploy precheck 脚本不存在: " + scriptPath);
        }

        Path sanitizedWorkspace = null;
        try {
            sanitizedWorkspace = prepareProdDryRunPackageWorkspace(releaseTag, releaseDir);
            runLocalCommand(List.of(
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    scriptPath.toString(),
                    "-PackagePath",
                    sanitizedWorkspace.toString(),
                    "-Environment",
                    "prod",
                    "-TargetConfigPath",
                    targetConfigPath.toString(),
                    "-Mode",
                    "report-only",
                    "-OutputPath",
                    reportPath.toString()
            ), "正式 deploy precheck report-only");

            Files.createDirectories(evidenceDir);
            ObjectNode root = objectMapper.createObjectNode();
            root.put("status", "passed");
            root.put("mode", "preflight-release");
            root.put("targetEnvironment", "prod");
            root.put("releaseTag", releaseTag);
            ArrayNode writeActions = root.putArray("writeActions");
            root.put("reportPath", reportPath.toString().replace('\\', '/'));
            root.put("targetConfigPath", targetConfigPath.toString().replace('\\', '/'));
            Files.writeString(dryRunEvidencePath,
                    objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(root) + System.lineSeparator(),
                    StandardCharsets.UTF_8);
            return dryRunEvidencePath.toString();
        } catch (IOException ex) {
            throw new RuntimeControlException("无法生成正式 dry-run 隔离工作区或证据: " + dryRunEvidencePath, ex);
        } finally {
            deleteDirectoryIfExists(sanitizedWorkspace);
        }
    }

    private Path locateReleasePackageWorkspace(String releaseTag) {
        Path releaseDir = properties.localCacheRootPath().resolve("publish-int-ruoyi").resolve(releaseTag);
        if (!Files.isDirectory(releaseDir)) {
            throw new RuntimeControlException("本机未找到发布包工作目录，无法生成正式 dry-run 证据: " + releaseDir);
        }
        return releaseDir;
    }

    private Path prepareProdDryRunPackageWorkspace(String releaseTag, Path sourceReleaseDir) throws IOException {
        Path manifestPath = sourceReleaseDir.resolve("manifest.json");
        if (!Files.isRegularFile(manifestPath)) {
            throw new RuntimeControlException("本机发布包缺少 manifest.json，无法生成正式 dry-run 证据: " + manifestPath);
        }
        JsonNode manifest = objectMapper.readTree(Files.readString(manifestPath, StandardCharsets.UTF_8));

        Path workspaceRoot = properties.stateDirPath().resolve("prod-preflight-release-workspaces");
        Files.createDirectories(workspaceRoot);
        Path workspace = Files.createTempDirectory(workspaceRoot, releaseTag + "-");

        LinkedHashSet<String> declaredPaths = collectProdDryRunDeclaredPackagePaths(manifest);
        declaredPaths.add("manifest.json");
        if (Files.isRegularFile(sourceReleaseDir.resolve("release-manifest.json"))) {
            declaredPaths.add("release-manifest.json");
        }
        if (Files.isRegularFile(sourceReleaseDir.resolve("legacy-release-manifest.json"))) {
            declaredPaths.add("legacy-release-manifest.json");
        }

        for (String relativePath : declaredPaths) {
            copyDeclaredPackageFile(sourceReleaseDir, workspace, relativePath);
        }
        return workspace;
    }

    private LinkedHashSet<String> collectProdDryRunDeclaredPackagePaths(JsonNode manifest) {
        LinkedHashSet<String> paths = new LinkedHashSet<>();
        for (JsonNode artifact : array(node(manifest, "artifacts"))) {
            if (artifact.path("includedInPackage").asBoolean(false)) {
                addDeclaredPackagePath(paths, text(artifact, "path"));
            }
        }

        JsonNode database = node(manifest, "database");
        for (JsonNode migration : array(node(database, "schemaMigrations"))) {
            addDeclaredPackagePath(paths, text(migration, "file"));
        }
        for (JsonNode dataSet : array(node(database, "requiredDataSets"))) {
            addDeclaredPackagePath(paths, text(dataSet, "file"));
        }

        JsonNode resources = node(manifest, "resources");
        addDeclaredPackagePath(paths, text(resources, "resourceReferenceManifest"));
        addDeclaredPackagePath(paths, text(resources, "resourceDeltaProofPath"));
        return paths;
    }

    private void addDeclaredPackagePath(LinkedHashSet<String> paths, String relativePath) {
        if (isBlank(relativePath)) {
            return;
        }
        String normalized = normalizeDeclaredPackagePath(relativePath);
        if (!normalized.isEmpty()) {
            paths.add(normalized);
        }
    }

    private String normalizeDeclaredPackagePath(String relativePath) {
        String normalized = relativePath.trim().replace("\\", "/");
        while (normalized.startsWith("./")) {
            normalized = normalized.substring(2);
        }
        while (normalized.startsWith("/")) {
            normalized = normalized.substring(1);
        }
        if (normalized.isEmpty()) {
            return normalized;
        }
        for (String part : normalized.split("/")) {
            if ("..".equals(part)) {
                throw new RuntimeControlException("发布包声明路径不合法: " + relativePath);
            }
        }
        return normalized;
    }

    private void copyDeclaredPackageFile(Path sourceReleaseDir, Path targetReleaseDir, String relativePath) throws IOException {
        String normalized = normalizeDeclaredPackagePath(relativePath);
        if (normalized.isEmpty()) {
            return;
        }
        Path sourcePath = sourceReleaseDir.resolve(normalized.replace("/", java.io.File.separator)).normalize();
        if (!sourcePath.startsWith(sourceReleaseDir)) {
            throw new RuntimeControlException("发布包声明路径越界: " + relativePath);
        }
        if (!Files.isRegularFile(sourcePath)) {
            throw new RuntimeControlException("发布包声明文件缺失，无法生成正式 dry-run 证据: " + sourcePath);
        }

        Path targetPath = targetReleaseDir.resolve(normalized.replace("/", java.io.File.separator)).normalize();
        if (!targetPath.startsWith(targetReleaseDir)) {
            throw new RuntimeControlException("正式 dry-run 工作区路径越界: " + relativePath);
        }
        Path parent = targetPath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.copy(sourcePath, targetPath, StandardCopyOption.REPLACE_EXISTING);
    }

    private void deleteDirectoryIfExists(Path directory) {
        if (directory == null || Files.notExists(directory)) {
            return;
        }
        try (var stream = Files.walk(directory)) {
            List<Path> paths = stream.sorted(Comparator.reverseOrder()).toList();
            for (Path path : paths) {
                Files.deleteIfExists(path);
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法清理正式 dry-run 工作区: " + directory, ex);
        }
    }

    private void runLocalCommand(List<String> command, String description) {
        ProcessBuilder builder = new ProcessBuilder(command)
                .directory(properties.opsRootPath().toFile())
                .redirectErrorStream(true);
        try {
            Process process = builder.start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            boolean completed = process.waitFor(properties.commandTimeout().toMillis(), TimeUnit.MILLISECONDS);
            if (!completed) {
                process.destroyForcibly();
                throw new RuntimeControlException(description + " 超时");
            }
            if (process.exitValue() != 0) {
                throw new RuntimeControlException(description + " 失败: " + output.trim());
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("无法启动 " + description, ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new RuntimeControlException(description + " 被中断", ex);
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
        } else if (!"COMPLETE".equals(chainStatus)) {
            blockedReasons.add("DCC backup manifest chainStatus 不是 COMPLETE");
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

    private RuntimeControlOwnerMatrixRespVO ownerMatrixResponse(Long id, RuntimeControlOwnerMatrixSaveReqVO req) {
        return new RuntimeControlOwnerMatrixRespVO(id, trimToEmpty(req.environment()), trimToEmpty(req.action()),
                trimToEmpty(req.role()), req.required(), req.ownerUserId(), trimToEmpty(req.ownerName()),
                trimToEmpty(req.escalationPath()), Instant.now());
    }

    private static RuntimeControlOwnerMatrixRespVO defaultOwner(Long id, String environment, String action,
                                                                String role, String escalationPath) {
        return new RuntimeControlOwnerMatrixRespVO(id, environment, action, role, true,
                DEFAULT_RELEASE_OWNER_USER_ID, DEFAULT_RELEASE_OWNER_NAME, escalationPath, null);
    }

    private void validateOwnerMatrixReq(RuntimeControlOwnerMatrixSaveReqVO req) {
        requireText(req.environment(), "environment");
        requireText(req.action(), "action");
        requireText(req.role(), "role");
        if (req.required() == null) {
            throw new RuntimeControlException("required is required");
        }
    }

    private List<RuntimeControlOwnerMatrixRespVO> effectiveOwnerMatrix() {
        Map<String, RuntimeControlOwnerMatrixRespVO> owners = new LinkedHashMap<>();
        DEFAULT_RELEASE_OWNERS.forEach(owner -> owners.put(ownerMatrixKey(owner), owner));
        readStateList("owner-matrix.json", RuntimeControlOwnerMatrixRespVO.class)
                .forEach(owner -> owners.put(ownerMatrixKey(owner), mergeOwner(owners.get(ownerMatrixKey(owner)), owner)));
        return owners.values().stream()
                .sorted(Comparator
                        .comparing(RuntimeControlOwnerMatrixRespVO::environment)
                        .thenComparing(RuntimeControlOwnerMatrixRespVO::action)
                        .thenComparing(RuntimeControlOwnerMatrixRespVO::role)
                        .thenComparing(owner -> owner.id() == null ? Long.MAX_VALUE : owner.id()))
                .toList();
    }

    private RuntimeControlOwnerMatrixRespVO mergeOwner(RuntimeControlOwnerMatrixRespVO defaultOwner,
                                                       RuntimeControlOwnerMatrixRespVO configuredOwner) {
        if (defaultOwner == null) {
            return configuredOwner;
        }
        return new RuntimeControlOwnerMatrixRespVO(configuredOwner.id(), configuredOwner.environment(),
                configuredOwner.action(), configuredOwner.role(), true,
                configuredOwner.ownerUserId() == null ? defaultOwner.ownerUserId() : configuredOwner.ownerUserId(),
                isBlank(configuredOwner.ownerName()) ? defaultOwner.ownerName() : configuredOwner.ownerName(),
                configuredOwner.escalationPath(), configuredOwner.updatedAt());
    }

    private String ownerMatrixKey(RuntimeControlOwnerMatrixRespVO owner) {
        return owner.environment() + "/" + owner.action() + "/" + owner.role();
    }

    private void validateRequiredOwners(RuntimeControlOperationAction action, String environment) {
        if (action.requiresResponsibilityGate()) {
            validateRequiredOwners(environment, action.action());
        }
    }

    private void validateRequiredOwners(String environment, String action) {
        String missingReason = findMissingRequiredOwnerReason(environment, action);
        if (missingReason != null) {
            throw new RuntimeControlException("责任人: " + missingReason);
        }
    }

    private String findMissingRequiredOwnerReason(String environment, String action) {
        List<RuntimeControlOwnerMatrixRespVO> requiredOwners = getOwnerMatrix(environment, action).stream()
                .filter(owner -> Boolean.TRUE.equals(owner.required()))
                .toList();
        if (requiredOwners.isEmpty()) {
            return "缺少必填责任人矩阵：" + environment + "/" + action;
        }
        List<String> missingRoles = requiredOwners.stream()
                .filter(owner -> owner.ownerUserId() == null)
                .map(RuntimeControlOwnerMatrixRespVO::role)
                .toList();
        if (!missingRoles.isEmpty()) {
            return "必填责任人缺失：" + environment + "/" + action + "/" + String.join(",", missingRoles);
        }
        return null;
    }

    private String resolveAlertBlockReason(String environment, String action, String notifyTemplateCode) {
        if (isBlank(notifyTemplateCode)) {
            return "站内信模板缺失：" + environment + "/" + action;
        }
        String missingOwnerReason = findMissingRequiredOwnerReason(environment, action);
        return missingOwnerReason == null ? "独立本机控制台未接入站内信" : missingOwnerReason;
    }

    private RuntimeControlAlertRespVO requireAlert(Long id) {
        if (id == null) {
            throw new RuntimeControlException("alertId is required");
        }
        return readStateList("alerts.json", RuntimeControlAlertRespVO.class).stream()
                .filter(alert -> id.equals(alert.id()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("告警不存在：" + id));
    }

    private RuntimeControlAlertRespVO createProbeFailureAlertIfNeeded(List<RuntimeControlProbeRespVO> probes) {
        List<RuntimeControlProbeRespVO> failures = probes.stream()
                .filter(probe -> STATUS_NO_GO.equals(probe.status()) || STATUS_BLOCKED.equals(probe.status()))
                .toList();
        if (failures.isEmpty()) {
            return null;
        }
        RuntimeControlProbeRespVO first = failures.get(0);
        return createAlert(new RuntimeControlAlertCreateReqVO(first.environment(), "probe-failed", STATUS_NO_GO,
                "探针失败", failures.stream()
                .map(probe -> probe.environment() + "/" + probe.component() + " " + probe.status() + " "
                        + blankToDefault(probe.error(), "无错误详情"))
                .reduce((left, right) -> left + "; " + right)
                .orElse("探针失败"), "RUNTIME_OPS_ALERT", new LinkedHashMap<>(Map.of(
                "environment", first.environment(),
                "action", "probe-failed",
                "severity", STATUS_NO_GO
        ))));
    }

    private List<String> collectRollbackBlockingReasons(List<RuntimeControlRollbackCandidateRespVO> candidates) {
        List<String> reasons = new ArrayList<>();
        if (candidates.isEmpty()) {
            reasons.add("无服务端回滚候选");
        }
        candidates.stream()
                .flatMap(candidate -> candidate.blockedReasons().stream())
                .filter(RuntimeControlService::hasText)
                .distinct()
                .forEach(reasons::add);
        return reasons;
    }

    private List<String> collectRestoreBlockingReasons(List<RuntimeControlRestoreCandidateRespVO> candidates) {
        List<String> reasons = new ArrayList<>();
        if (candidates.isEmpty()) {
            reasons.add("无服务端恢复候选");
        }
        candidates.stream()
                .flatMap(candidate -> candidate.blockedReasons().stream())
                .filter(RuntimeControlService::hasText)
                .distinct()
                .forEach(reasons::add);
        return reasons;
    }

    private void validateIncidentCreateReq(RuntimeControlIncidentCreateReqVO req) {
        requireText(req.environment(), "environment");
        requireText(req.action(), "action");
        requireText(req.severity(), "severity");
        requireText(req.title(), "title");
        requireText(req.description(), "description");
        String sourceType = normalizeSourceType(req.sourceType());
        if (!List.of("DIRECT", "ALERT", "HIGH_RISK_OPERATION").contains(sourceType)) {
            throw new RuntimeControlException("sourceType");
        }
        if (!"DIRECT".equals(sourceType) && isBlank(req.sourceId())) {
            throw new RuntimeControlException("sourceId is required");
        }
    }

    private RuntimeControlIncidentRespVO requireOpenIncident(Long id) {
        if (id == null) {
            throw new RuntimeControlException("incidentId is required");
        }
        RuntimeControlIncidentRespVO incident = readStateList("incidents.json", RuntimeControlIncidentRespVO.class)
                .stream()
                .filter(item -> id.equals(item.id()))
                .findFirst()
                .orElseThrow(() -> new RuntimeControlException("事故不存在：" + id));
        if ("CLOSED".equals(incident.status())) {
            throw new RuntimeControlException("事故已关闭：" + id);
        }
        return incident;
    }

    private void validateIncidentCloseReq(RuntimeControlIncidentCloseReqVO req) {
        if (!"PASSED".equals(trimToEmpty(req.ownerGateResult()).toUpperCase(Locale.ROOT))) {
            throw new RuntimeControlException("责任人门禁未通过");
        }
        if (!"PASSED".equals(trimToEmpty(req.verificationResult()).toUpperCase(Locale.ROOT))) {
            throw new RuntimeControlException("验证结果未通过");
        }
        if (!"DONE".equals(trimToEmpty(req.postmortemStatus()).toUpperCase(Locale.ROOT))) {
            throw new RuntimeControlException("复盘状态未完成");
        }
        requireText(req.remainingRisk(), "remainingRisk");
        requireText(req.closeReason(), "closeReason");
    }

    private RuntimeControlIncidentRespVO copyIncident(RuntimeControlIncidentRespVO source,
                                                      List<RuntimeControlIncidentActionRespVO> actions,
                                                      String ownerGateResult,
                                                      String verificationResult,
                                                      String remainingRisk,
                                                      String postmortemStatus,
                                                      String closeReason,
                                                      String closedBy,
                                                      Instant closedAt,
                                                      String status) {
        return new RuntimeControlIncidentRespVO(source.id(), source.environment(), source.action(), source.severity(),
                source.title(), source.description(), source.sourceType(), source.sourceId(), status,
                source.createdBy(), source.createdAt(), actions, ownerGateResult, verificationResult, remainingRisk,
                postmortemStatus, closeReason, closedBy, closedAt);
    }

    private String normalizeSourceType(String sourceType) {
        return trimToEmpty(sourceType).toUpperCase(Locale.ROOT);
    }

    private RuntimeControlBusinessHealthItemRespVO blockedBusinessHealth(String code, String name, String reason,
                                                                         Instant sampledAt) {
        return new RuntimeControlBusinessHealthItemRespVO(code, name, STATUS_BLOCKED, null, reason, sampledAt);
    }

    private String aggregateStatus(List<String> statuses) {
        if (statuses.stream().anyMatch(status -> STATUS_NO_GO.equals(status) || STATUS_BLOCKED.equals(status))) {
            return STATUS_NO_GO;
        }
        if (statuses.stream().anyMatch("WARN"::equals)) {
            return "WARN";
        }
        return "PASS";
    }

    private boolean isProbeType(String actionComponent) {
        return "backend".equals(actionComponent) || "frontend".equals(actionComponent)
                || "website".equals(actionComponent);
    }

    private Integer parseHttpStatus(String httpStatus) {
        if (isBlank(httpStatus)) {
            return null;
        }
        try {
            return Integer.parseInt(httpStatus.trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private <T> long nextStateId(String fileName, Class<T> valueType, Function<T, Long> idGetter) {
        return readStateList(fileName, valueType).stream()
                .map(idGetter)
                .filter(id -> id != null)
                .max(Long::compareTo)
                .orElse(0L) + 1L;
    }

    private <T> T saveStateItem(String fileName, Class<T> valueType, Function<T, Long> idGetter, T item) {
        List<T> items = new ArrayList<>(readStateList(fileName, valueType));
        Long id = idGetter.apply(item);
        if (id == null) {
            throw new RuntimeControlException(fileName + " item id is required");
        }
        items.removeIf(existing -> id.equals(idGetter.apply(existing)));
        items.add(item);
        writeStateList(fileName, items);
        return item;
    }

    private <T> List<T> readStateList(String fileName, Class<T> valueType) {
        Path path = runtimeOpsPath(fileName);
        if (!Files.isRegularFile(path)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(path.toFile(), objectMapper.getTypeFactory()
                    .constructCollectionType(List.class, valueType));
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取运行态文件: " + path, ex);
        }
    }

    private <T> T readStateObject(String fileName, Class<T> valueType) {
        Path path = runtimeOpsPath(fileName);
        if (!Files.isRegularFile(path)) {
            return null;
        }
        try {
            return objectMapper.readValue(path.toFile(), valueType);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法读取运行态文件: " + path, ex);
        }
    }

    private <T> void writeStateList(String fileName, List<T> values) {
        Path path = runtimeOpsPath(fileName);
        try {
            Files.createDirectories(path.getParent());
            Path tmpPath = path.resolveSibling(fileName + ".tmp");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(tmpPath.toFile(), values);
            Files.move(tmpPath, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法写入运行态文件: " + path, ex);
        }
    }

    private void writeStateObject(String fileName, Object value) {
        Path path = runtimeOpsPath(fileName);
        try {
            Files.createDirectories(path.getParent());
            Path tmpPath = path.resolveSibling(fileName + ".tmp");
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(tmpPath.toFile(), value);
            Files.move(tmpPath, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ex) {
            throw new RuntimeControlException("无法写入运行态文件: " + path, ex);
        }
    }

    private Path runtimeOpsPath(String fileName) {
        return properties.stateDirPath().resolve("runtime-ops").resolve(fileName);
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
                recoverySetProgramVersion, recoverySetRedisPolicy, req.prodDryRunEvidencePath());
    }

    private RuntimeControlActionReqVO copyActionReqWithSqlPath(RuntimeControlActionReqVO req, String sqlPath) {
        return new RuntimeControlActionReqVO(req.action(), req.reason(), req.prodConfirmText(),
                req.targetEnvironment(), req.publishScope(), req.includeOnlyOffice(),
                req.includeShowroomBuildPackage(), req.enableSmartReleaseReport(), req.releaseTag(),
                req.testConclusion(), sqlPath, req.selectedImageCandidateId(), req.selectedImageTag(),
                req.selectedRecoverySetCandidateId(), req.selectedBackupId(), req.recoverySetId(),
                req.recoverySetManifestHash(), req.recoverySetProgramVersion(), req.recoverySetRedisPolicy(),
                req.prodDryRunEvidencePath());
    }

    private RuntimeControlActionReqVO copyActionReqWithReleaseTag(RuntimeControlActionReqVO req, String releaseTag) {
        return new RuntimeControlActionReqVO(req.action(), req.reason(), req.prodConfirmText(),
                req.targetEnvironment(), req.publishScope(), req.includeOnlyOffice(),
                req.includeShowroomBuildPackage(), req.enableSmartReleaseReport(), releaseTag,
                req.testConclusion(), req.sqlPath(), req.selectedImageCandidateId(), req.selectedImageTag(),
                req.selectedRecoverySetCandidateId(), req.selectedBackupId(), req.recoverySetId(),
                req.recoverySetManifestHash(), req.recoverySetProgramVersion(), req.recoverySetRedisPolicy(),
                req.prodDryRunEvidencePath());
    }

    private RuntimeControlActionReqVO copyActionReqWithProdDryRunEvidencePath(RuntimeControlActionReqVO req,
                                                                               String prodDryRunEvidencePath) {
        return new RuntimeControlActionReqVO(req.action(), req.reason(), req.prodConfirmText(),
                req.targetEnvironment(), req.publishScope(), req.includeOnlyOffice(),
                req.includeShowroomBuildPackage(), req.enableSmartReleaseReport(), req.releaseTag(),
                req.testConclusion(), req.sqlPath(), req.selectedImageCandidateId(), req.selectedImageTag(),
                req.selectedRecoverySetCandidateId(), req.selectedBackupId(), req.recoverySetId(),
                req.recoverySetManifestHash(), req.recoverySetProgramVersion(), req.recoverySetRedisPolicy(),
                prodDryRunEvidencePath);
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

    private List<JsonNode> array(JsonNode node) {
        if (node == null || !node.isArray()) {
            return List.of();
        }
        List<JsonNode> result = new ArrayList<>();
        node.forEach(result::add);
        return result;
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

    private static String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
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
        guardWrite(environment, reason, prodConfirmText, "prod".equals(environment), "prod".equals(environment));
    }

    private void guardWrite(String environment, String reason, String prodConfirmText, boolean productionGuard) {
        guardWrite(environment, reason, prodConfirmText, productionGuard, productionGuard);
    }

    private void guardWrite(String environment, String reason, String prodConfirmText, boolean productionGuard,
                            boolean requireProdConfirmText) {
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
            if (requireProdConfirmText && !PROD_CONFIRM_TEXT.equals(prodConfirmText)) {
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
