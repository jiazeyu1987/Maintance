package com.intruoyi.maintenance.runtime;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.RuntimeControlActionReqVO;

public enum RuntimeControlOperationAction {

    BUILD_RELEASE("build-release", "构建发布包", "release", false,
            "deploy/publish-int-ruoyi.ps1",
            RuntimeControlOperationAction::buildReleaseArguments),
    PUBLISH_TEST("publish-test", "部署发布包到测试服", "test", false,
            "deploy/publish-int-ruoyi.ps1",
            req -> deployReleaseArguments("test", req)),
    RECOVER_TEST_RELEASE_LOCK("recover-test-release-lock", "恢复测试服发布锁", "test", false,
            "deploy/recover-release-operation-lock.ps1",
            RuntimeControlOperationAction::recoverTestReleaseLockArguments),
    APPLY_TEST_DB_SQL("apply-test-db-sql", "测试服数据库快应用", "test", false,
            "deploy/apply-test-db-sql.ps1",
            RuntimeControlOperationAction::applyTestDbSqlArguments),
    MARK_RELEASE_TESTED("mark-release-tested", "标记测试通过", "test", false,
            "deploy/publish-int-ruoyi.ps1",
            RuntimeControlOperationAction::markReleaseTestedArguments),
    PROMOTE_PROD("promote-prod", "上线已验证发布包", "prod", true,
            "deploy/publish-int-ruoyi.ps1",
            req -> deployReleaseArguments("prod", req)),
    PROMOTE_BACKUP("promote-backup", "上线备份服务器", "backup", true,
            "deploy/publish-int-ruoyi.ps1",
            req -> deployReleaseArguments("backup", req)),
    BACKUP_NOW("backup-now", "立即备份", "prod", true,
            "backup-ops/scripts/backup-ops.ps1",
            req -> backupArguments("backup-now", req)),
    ROLLBACK_APP("rollback-app", "回滚版本", "prod", true,
            "backup-ops/scripts/backup-ops.ps1",
            req -> backupArguments("rollback-app", req)),
    REHEARSAL("rehearsal", "恢复演练", "test", false,
            "backup-ops/scripts/backup-ops.ps1",
            req -> backupArguments("rehearsal", req)),
    RESTORE_DATA("restore-data", "恢复数据", "prod", true,
            "backup-ops/scripts/backup-ops.ps1",
            req -> backupArguments("restore-data", req));

    public static final String PUBLISH_SCOPE_CODE_ONLY = "code-only";
    public static final String PUBLISH_SCOPE_WITH_DATA = "with-data";

    private final String action;
    private final String label;
    private final String environment;
    private final boolean productionGuardRequired;
    private final String scriptPath;
    private final Function<RuntimeControlActionReqVO, List<String>> argumentsBuilder;

    RuntimeControlOperationAction(String action, String label, String environment, boolean productionGuardRequired,
                                  String scriptPath,
                                  Function<RuntimeControlActionReqVO, List<String>> argumentsBuilder) {
        this.action = action;
        this.label = label;
        this.environment = environment;
        this.productionGuardRequired = productionGuardRequired;
        this.scriptPath = scriptPath;
        this.argumentsBuilder = argumentsBuilder;
    }

    public static RuntimeControlOperationAction require(String action) {
        for (RuntimeControlOperationAction value : values()) {
            if (value.action.equals(action)) {
                return value;
            }
        }
        throw new RuntimeControlException("未知运行控制台动作: " + action);
    }

    public String action() {
        return action;
    }

    public String label() {
        return label;
    }

    public String defaultEnvironment() {
        return environment;
    }

    public String resolveEnvironment(RuntimeControlActionReqVO req) {
        if (this == BACKUP_NOW || this == ROLLBACK_APP || this == RESTORE_DATA) {
            return textOrDefault(req.targetEnvironment(), environment);
        }
        return environment;
    }

    public boolean requiresProductionGuard(RuntimeControlActionReqVO req) {
        if (this == BACKUP_NOW) {
            return "prod".equals(resolveEnvironment(req));
        }
        if (this == ROLLBACK_APP || this == RESTORE_DATA) {
            return "prod".equals(resolveEnvironment(req)) || "backup".equals(resolveEnvironment(req));
        }
        return productionGuardRequired;
    }

    public boolean requiresProdConfirmText(RuntimeControlActionReqVO req) {
        if (this == BACKUP_NOW) {
            return false;
        }
        return requiresProductionGuard(req);
    }

    public RuntimeControlCommand buildCommand(RuntimeControlActionReqVO req, RuntimeControlProperties properties) {
        boolean linuxBackup = isBackupAction() && properties.getBackupOps().isLinuxLocal();
        List<String> args = linuxBackup
                ? linuxBackupArguments(action, req, properties)
                : new ArrayList<>(argumentsBuilder.apply(req));
        if (deploysReleasePackage()) {
            appendRemoteDeployTargetArguments(args, resolveEnvironment(req), properties);
        }
        if (this == APPLY_TEST_DB_SQL) {
            appendApplyTestDbSqlTargetArguments(args, properties);
        } else if (this == RECOVER_TEST_RELEASE_LOCK) {
            appendRecoverTestReleaseLockTargetArguments(args, properties);
        }
        if (this == BUILD_RELEASE) {
            appendReleaseTargetHostArguments(args, properties, true);
        } else if (deploysReleasePackage()) {
            appendReleaseTargetHostArguments(args, properties, "prod".equals(resolveEnvironment(req)));
        }
        if (Boolean.TRUE.equals(req.enableSmartReleaseReport())) {
            if (!supportsSmartReleaseReport()) {
                throw new RuntimeControlException("动作不支持智能发布报告: " + action);
            }
            args.add("-EnableSmartReleaseReport");
        }
        if (isBackupAction() && !linuxBackup) {
            args.add("-OperatorName");
            args.add(properties.getOperatorId());
        }
        String script = linuxBackup
                ? requireText(properties.getBackupOps().getLinuxScriptPath(), "backupOps.linuxScriptPath")
                : scriptPath;
        return new RuntimeControlCommand(resolveEnvironment(req), action, script, args);
    }

    public Map<String, String> safeParameters(RuntimeControlActionReqVO req) {
        Map<String, String> parameters = new LinkedHashMap<>();
        switch (this) {
            case BUILD_RELEASE -> {
                parameters.put("publishScope", text(req.publishScope()));
                parameters.put("includeOnlyOffice", String.valueOf(Boolean.TRUE.equals(req.includeOnlyOffice())));
                parameters.put("includeShowroomBuildPackage",
                        String.valueOf(Boolean.TRUE.equals(req.includeShowroomBuildPackage())));
                parameters.put("releaseTag", text(req.releaseTag()));
            }
            case PUBLISH_TEST, PROMOTE_PROD, PROMOTE_BACKUP, RECOVER_TEST_RELEASE_LOCK ->
                    parameters.put("releaseTag", text(req.releaseTag()));
            case APPLY_TEST_DB_SQL -> parameters.put("sqlPath", text(req.sqlPath()));
            case MARK_RELEASE_TESTED -> {
                parameters.put("releaseTag", text(req.releaseTag()));
                parameters.put("testConclusion", text(req.testConclusion()));
                parameters.put("selectedRecoverySetCandidateId", text(req.selectedRecoverySetCandidateId()));
            }
            case BACKUP_NOW -> parameters.put("targetEnvironment", text(req.targetEnvironment()));
            case ROLLBACK_APP -> {
                parameters.put("selectedImageCandidateId", text(req.selectedImageCandidateId()));
                parameters.put("selectedImageTag", text(req.selectedImageTag()));
                parameters.put("targetEnvironment", text(req.targetEnvironment()));
            }
            case REHEARSAL -> {
                parameters.put("selectedRecoverySetCandidateId", text(req.selectedRecoverySetCandidateId()));
                parameters.put("selectedBackupId", text(req.selectedBackupId()));
            }
            case RESTORE_DATA -> {
                parameters.put("selectedRecoverySetCandidateId", text(req.selectedRecoverySetCandidateId()));
                parameters.put("selectedBackupId", text(req.selectedBackupId()));
                parameters.put("targetEnvironment", text(req.targetEnvironment()));
            }
        }
        if (Boolean.TRUE.equals(req.enableSmartReleaseReport())) {
            parameters.put("enableSmartReleaseReport", "true");
        }
        if (this == PROMOTE_PROD && !isBlank(req.prodDryRunEvidencePath())) {
            parameters.put("prodDryRunEvidencePath", text(req.prodDryRunEvidencePath()));
        }
        return parameters;
    }

    public void validateRequest(RuntimeControlActionReqVO req) {
        if (this == BUILD_RELEASE && !supportsPublishScope(req.publishScope())) {
            throw new RuntimeControlException("publishScope 必须是 code-only 或 with-data");
        }
        if (requiresReleaseTag() && isBlank(req.releaseTag())) {
            throw new RuntimeControlException("releaseTag is required for action: " + action);
        }
        if (this == APPLY_TEST_DB_SQL && isBlank(req.sqlPath())) {
            throw new RuntimeControlException("sqlPath is required for action: " + action);
        }
        if (this == ROLLBACK_APP && isBlank(req.selectedImageCandidateId())) {
            throw new RuntimeControlException("selectedImageCandidateId is required for rollback-app");
        }
        if ((this == REHEARSAL || this == RESTORE_DATA) && isBlank(req.selectedRecoverySetCandidateId())) {
            throw new RuntimeControlException("selectedRecoverySetCandidateId is required for " + action);
        }
        if (this == MARK_RELEASE_TESTED && isBlank(req.testConclusion())) {
            throw new RuntimeControlException("testConclusion is required for action: " + action);
        }
        if (this == MARK_RELEASE_TESTED && isBlank(req.selectedRecoverySetCandidateId())) {
            throw new RuntimeControlException("selectedRecoverySetCandidateId is required for action: " + action);
        }
    }

    private boolean deploysReleasePackage() {
        return this == PUBLISH_TEST || this == PROMOTE_PROD || this == PROMOTE_BACKUP;
    }

    public boolean requiresNasReleaseRepository() {
        return this == BUILD_RELEASE || this == PUBLISH_TEST || this == MARK_RELEASE_TESTED
                || this == PROMOTE_PROD || this == PROMOTE_BACKUP;
    }

    private boolean isBackupAction() {
        return this == BACKUP_NOW || this == ROLLBACK_APP || this == REHEARSAL || this == RESTORE_DATA;
    }

    private boolean requiresReleaseTag() {
        return this == PUBLISH_TEST || this == MARK_RELEASE_TESTED || this == PROMOTE_PROD
                || this == PROMOTE_BACKUP || this == RECOVER_TEST_RELEASE_LOCK;
    }

    public boolean requiresResponsibilityGate() {
        return this == PROMOTE_PROD || this == PROMOTE_BACKUP || this == ROLLBACK_APP || this == REHEARSAL
                || this == RESTORE_DATA;
    }

    private boolean supportsSmartReleaseReport() {
        return this == BUILD_RELEASE || deploysReleasePackage();
    }

    private boolean supportsPublishScope(String publishScope) {
        return PUBLISH_SCOPE_CODE_ONLY.equals(publishScope) || PUBLISH_SCOPE_WITH_DATA.equals(publishScope);
    }

    private static List<String> buildReleaseArguments(RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-Mode");
        args.add("build-release");
        if (!isBlank(req.releaseTag())) {
            args.add("-ReleaseTag");
            args.add(req.releaseTag().trim());
        }
        args.add("-Component");
        args.add(Boolean.TRUE.equals(req.includeShowroomBuildPackage()) ? "full" : "intruoyi");
        if (Boolean.TRUE.equals(req.includeOnlyOffice())) {
            args.add("-IncludeOnlyOffice");
        }
        if (PUBLISH_SCOPE_CODE_ONLY.equals(req.publishScope())) {
            args.add("-PublishScope");
            args.add(PUBLISH_SCOPE_CODE_ONLY);
            args.add("-SkipDatabaseSync");
            args.add("-SkipMinioSync");
            return args;
        }
        if (PUBLISH_SCOPE_WITH_DATA.equals(req.publishScope())) {
            args.add("-PublishScope");
            args.add(PUBLISH_SCOPE_WITH_DATA);
            args.add("-ConfirmText");
            args.add("WITH-DATA");
            return args;
        }
        throw new RuntimeControlException("Invalid publishScope: " + req.publishScope());
    }

    private static List<String> applyTestDbSqlArguments(RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-SqlPath");
        args.add(text(req.sqlPath()));
        args.add("-Reason");
        args.add(text(req.reason()));
        return args;
    }

    private static List<String> deployReleaseArguments(String environment, RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-Mode");
        args.add("deploy-release");
        args.add("-Environment");
        args.add(environment);
        args.add("-ReleaseTag");
        args.add(text(req.releaseTag()));
        if ("prod".equals(environment) || "backup".equals(environment)) {
            args.add("-ConfirmText");
            args.add("PROD");
        }
        if ("prod".equals(environment) && !isBlank(req.prodDryRunEvidencePath())) {
            args.add("-ProdDryRunEvidencePath");
            args.add(text(req.prodDryRunEvidencePath()));
        }
        return args;
    }

    private static List<String> recoverTestReleaseLockArguments(RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-ExpectedOperationId");
        args.add("test-" + text(req.releaseTag()));
        args.add("-ExpectedReleaseTag");
        args.add(text(req.releaseTag()));
        args.add("-ConfirmText");
        args.add("RECOVER-TEST-LOCK");
        return args;
    }

    private static List<String> markReleaseTestedArguments(RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-Mode");
        args.add("mark-tested");
        args.add("-ReleaseTag");
        args.add(text(req.releaseTag()));
        args.add("-TestConclusion");
        args.add(text(req.testConclusion()));
        args.add("-SelectedRecoverySetCandidateId");
        args.add(text(req.selectedRecoverySetCandidateId()));
        args.add("-RecoverySetId");
        args.add(text(req.recoverySetId()));
        args.add("-RecoverySetManifestHash");
        args.add(text(req.recoverySetManifestHash()));
        args.add("-RecoverySetProgramVersion");
        args.add(text(req.recoverySetProgramVersion()));
        args.add("-RecoverySetRedisPolicy");
        args.add(text(req.recoverySetRedisPolicy()));
        return args;
    }

    private static List<String> backupArguments(String mode, RuntimeControlActionReqVO req) {
        List<String> args = new ArrayList<>();
        args.add("-Mode");
        args.add(mode);
        args.add("-NonInteractive");
        if ("backup-now".equals(mode) || "rollback-app".equals(mode) || "restore-data".equals(mode)) {
            args.add("-TargetEnvironment");
            args.add(textOrDefault(req.targetEnvironment(), "prod"));
        }
        if ("backup-now".equals(mode) && "prod".equals(textOrDefault(req.targetEnvironment(), "prod"))
                && !isBlank(req.prodConfirmText())) {
            args.add("-ProductionBackupConfirmText");
            args.add(text(req.prodConfirmText()));
        }
        if ("rollback-app".equals(mode)) {
            args.add("-SelectedImageTag");
            args.add(text(req.selectedImageTag()));
        }
        if ("rehearsal".equals(mode) || "restore-data".equals(mode)) {
            args.add("-SelectedBackupId");
            args.add(text(req.selectedBackupId()));
        }
        return args;
    }

    private static List<String> linuxBackupArguments(String mode, RuntimeControlActionReqVO req,
                                                     RuntimeControlProperties properties) {
        List<String> args = new ArrayList<>();
        args.add("--mode");
        args.add(mode);
        args.add("--config");
        args.add(requireText(properties.getBackupOps().getLinuxConfigPath(), "backupOps.linuxConfigPath"));
        args.add("--non-interactive");
        if ("backup-now".equals(mode)) {
            args.add("--target-environment");
            args.add(text(req.targetEnvironment()));
        }
        if ("rollback-app".equals(mode)) {
            args.add("--target-environment");
            args.add(text(req.targetEnvironment()));
            args.add("--selected-image-tag");
            args.add(text(req.selectedImageTag()));
        }
        if ("rehearsal".equals(mode)) {
            args.add("--selected-backup-id");
            args.add(text(req.selectedBackupId()));
        }
        if ("restore-data".equals(mode)) {
            args.add("--target-environment");
            args.add(text(req.targetEnvironment()));
            args.add("--selected-backup-id");
            args.add(text(req.selectedBackupId()));
        }
        return args;
    }

    private static void appendRemoteDeployTargetArguments(List<String> args, String targetEnvironment,
                                                          RuntimeControlProperties properties) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment(targetEnvironment);
        if (environment.isLocal()) {
            throw new RuntimeControlException("远程发布目标不能是本机环境: " + targetEnvironment);
        }
        addRequiredArgument(args, "-ServerHost", environment.getHost());
        addRequiredArgument(args, "-ServerUser", environment.getServerUser());
        addRequiredArgument(args, "-RemoteAppDir", environment.getRemoteAppDir());
        addRequiredArgument(args, "-RemoteReleaseRoot", environment.getRemoteReleaseRoot());
        addRequiredArgument(args, "-RemoteDataRoot", environment.getRemoteDataRoot());
        addRequiredArgument(args, "-RemoteDataDiskMount", environment.getRemoteDataDiskMount());
        addRequiredArgument(args, "-RemoteDataDiskDevice", environment.getRemoteDataDiskDevice());
        addOptionalArgument(args, "-RemoteMinioContainer", environment.getRemoteMinioContainer());
    }

    private static void appendApplyTestDbSqlTargetArguments(List<String> args, RuntimeControlProperties properties) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment("test");
        if (environment.isLocal()) {
            throw new RuntimeControlException("测试服 SQL 应用目标不能是本机环境");
        }
        addRequiredArgument(args, "-ServerHost", environment.getHost());
        addRequiredArgument(args, "-ServerUser", environment.getServerUser());
        addRequiredArgument(args, "-RemoteAppDir", environment.getRemoteAppDir());
        addRequiredArgument(args, "-ExpectedServerHost", environment.getHost());
    }

    private static void appendRecoverTestReleaseLockTargetArguments(List<String> args,
                                                                     RuntimeControlProperties properties) {
        RuntimeControlProperties.Environment environment = properties.requireEnvironment("test");
        if (environment.isLocal()) {
            throw new RuntimeControlException("测试服发布锁恢复目标不能是本机环境");
        }
        addRequiredArgument(args, "-ServerHost", environment.getHost());
        addRequiredArgument(args, "-ServerUser", environment.getServerUser());
        addRequiredArgument(args, "-RemoteAppDir", environment.getRemoteAppDir());
    }

    private static void appendReleaseTargetHostArguments(List<String> args, RuntimeControlProperties properties,
                                                         boolean includeProd) {
        addRequiredArgument(args, "-TestServerHost", properties.requireEnvironment("test").getHost());
        addRequiredArgument(args, "-BackupServerHost", properties.requireEnvironment("backup").getHost());
        if (includeProd) {
            addRequiredArgument(args, "-ProdServerHost", properties.requireEnvironment("prod").getHost());
        }
    }

    private static void addRequiredArgument(List<String> args, String name, String value) {
        if (isBlank(value)) {
            throw new RuntimeControlException("Missing " + name);
        }
        args.add(name);
        args.add(value.trim());
    }

    private static void addOptionalArgument(List<String> args, String name, String value) {
        if (!isBlank(value)) {
            args.add(name);
            args.add(value.trim());
        }
    }

    private static String text(String value) {
        return value == null ? "" : value.trim();
    }

    private static String textOrDefault(String value, String defaultValue) {
        return isBlank(value) ? defaultValue : value.trim();
    }

    private static String requireText(String value, String name) {
        if (isBlank(value)) {
            throw new RuntimeControlException(name + " is required");
        }
        return value.trim();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
