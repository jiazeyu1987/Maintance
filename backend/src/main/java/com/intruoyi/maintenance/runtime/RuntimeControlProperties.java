package com.intruoyi.maintenance.runtime;

import jakarta.annotation.PostConstruct;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.nio.file.Path;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@ConfigurationProperties(prefix = "maintenance.runtime-control")
public class RuntimeControlProperties {

    private String operatorId = "local-operator";
    private String repoRoot;
    private String frontendRoot;
    private String websiteRoot;
    private String opsRoot = "ops";
    private String stateDir = "runtime/runtime-control";
    private long commandTimeoutSeconds = 1800;
    private long statusTimeoutMillis = 1500;
    private boolean productionWriteEnabled;
    private Map<String, Environment> environments = new LinkedHashMap<>();
    private BackupOps backupOps = new BackupOps();
    private ReleasePackage releasePackage = new ReleasePackage();

    @PostConstruct
    public void validate() {
        requireText(repoRoot, "maintenance.runtime-control.repo-root");
        requireText(frontendRoot, "maintenance.runtime-control.frontend-root");
        requireText(websiteRoot, "maintenance.runtime-control.website-root");
        requireText(opsRoot, "maintenance.runtime-control.ops-root");
        requireText(stateDir, "maintenance.runtime-control.state-dir");
        requireDirectory(repoRootPath(), "maintenance.runtime-control.repo-root");
        requireDirectory(frontendRootPath(), "maintenance.runtime-control.frontend-root");
        requireDirectory(websiteRootPath(), "maintenance.runtime-control.website-root");
        requireDirectory(opsRootPath(), "maintenance.runtime-control.ops-root");
        if (environments.isEmpty()) {
            throw new IllegalArgumentException("maintenance.runtime-control.environments must not be empty");
        }
    }

    public Path repoRootPath() {
        return Path.of(repoRoot).toAbsolutePath().normalize();
    }

    public Path frontendRootPath() {
        return Path.of(frontendRoot).toAbsolutePath().normalize();
    }

    public Path websiteRootPath() {
        return Path.of(websiteRoot).toAbsolutePath().normalize();
    }

    public Path opsRootPath() {
        return Path.of(opsRoot).toAbsolutePath().normalize();
    }

    public Path stateDirPath() {
        return Path.of(stateDir).toAbsolutePath().normalize();
    }

    public Duration commandTimeout() {
        return Duration.ofSeconds(commandTimeoutSeconds);
    }

    public Duration statusTimeout() {
        return Duration.ofMillis(statusTimeoutMillis);
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " is required");
        }
    }

    private static void requireDirectory(Path path, String name) {
        if (!java.nio.file.Files.isDirectory(path)) {
            throw new IllegalArgumentException(name + " directory does not exist: " + path);
        }
    }

    public Environment requireEnvironment(String environment) {
        Environment value = environments.get(environment);
        if (value == null) {
            throw new RuntimeControlException("未知环境: " + environment);
        }
        return value;
    }

    public Target requireTarget(String environment, String component) {
        Environment env = requireEnvironment(environment);
        Target target = env.target(component);
        if (target == null) {
            throw new RuntimeControlException("未知运行组件: " + environment + "/" + component);
        }
        return target;
    }

    public String getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(String operatorId) {
        this.operatorId = operatorId;
    }

    public String getRepoRoot() {
        return repoRoot;
    }

    public void setRepoRoot(String repoRoot) {
        this.repoRoot = repoRoot;
    }

    public String getFrontendRoot() {
        return frontendRoot;
    }

    public void setFrontendRoot(String frontendRoot) {
        this.frontendRoot = frontendRoot;
    }

    public String getWebsiteRoot() {
        return websiteRoot;
    }

    public void setWebsiteRoot(String websiteRoot) {
        this.websiteRoot = websiteRoot;
    }

    public String getOpsRoot() {
        return opsRoot;
    }

    public void setOpsRoot(String opsRoot) {
        this.opsRoot = opsRoot;
    }

    public String getStateDir() {
        return stateDir;
    }

    public void setStateDir(String stateDir) {
        this.stateDir = stateDir;
    }

    public long getCommandTimeoutSeconds() {
        return commandTimeoutSeconds;
    }

    public void setCommandTimeoutSeconds(long commandTimeoutSeconds) {
        this.commandTimeoutSeconds = commandTimeoutSeconds;
    }

    public long getStatusTimeoutMillis() {
        return statusTimeoutMillis;
    }

    public void setStatusTimeoutMillis(long statusTimeoutMillis) {
        this.statusTimeoutMillis = statusTimeoutMillis;
    }

    public boolean isProductionWriteEnabled() {
        return productionWriteEnabled;
    }

    public void setProductionWriteEnabled(boolean productionWriteEnabled) {
        this.productionWriteEnabled = productionWriteEnabled;
    }

    public Map<String, Environment> getEnvironments() {
        return environments;
    }

    public void setEnvironments(Map<String, Environment> environments) {
        this.environments = environments;
    }

    public BackupOps getBackupOps() {
        return backupOps;
    }

    public void setBackupOps(BackupOps backupOps) {
        this.backupOps = backupOps;
    }

    public ReleasePackage getReleasePackage() {
        return releasePackage;
    }

    public void setReleasePackage(ReleasePackage releasePackage) {
        this.releasePackage = releasePackage;
    }

    public static class Environment {
        private String label;
        private boolean local;
        private String host;
        private String serverUser = "root";
        private String remoteAppDir;
        private String remoteReleaseRoot;
        private String remoteDataRoot;
        private String remoteDataDiskMount;
        private String remoteDataDiskDevice;
        private String remoteMinioContainer;
        private boolean accessEnabled;
        private String accessDisabledReason;
        private Map<String, Target> targets = new LinkedHashMap<>();

        public Target target(String component) {
            return targets.get(component);
        }

        public String getLabel() {
            return label;
        }

        public void setLabel(String label) {
            this.label = label;
        }

        public boolean isLocal() {
            return local;
        }

        public void setLocal(boolean local) {
            this.local = local;
        }

        public String getHost() {
            return host;
        }

        public void setHost(String host) {
            this.host = host;
        }

        public String getServerUser() {
            return serverUser;
        }

        public void setServerUser(String serverUser) {
            this.serverUser = serverUser;
        }

        public String getRemoteAppDir() {
            return remoteAppDir;
        }

        public void setRemoteAppDir(String remoteAppDir) {
            this.remoteAppDir = remoteAppDir;
        }

        public String getRemoteReleaseRoot() {
            return remoteReleaseRoot;
        }

        public void setRemoteReleaseRoot(String remoteReleaseRoot) {
            this.remoteReleaseRoot = remoteReleaseRoot;
        }

        public String getRemoteDataRoot() {
            return remoteDataRoot;
        }

        public void setRemoteDataRoot(String remoteDataRoot) {
            this.remoteDataRoot = remoteDataRoot;
        }

        public String getRemoteDataDiskMount() {
            return remoteDataDiskMount;
        }

        public void setRemoteDataDiskMount(String remoteDataDiskMount) {
            this.remoteDataDiskMount = remoteDataDiskMount;
        }

        public String getRemoteDataDiskDevice() {
            return remoteDataDiskDevice;
        }

        public void setRemoteDataDiskDevice(String remoteDataDiskDevice) {
            this.remoteDataDiskDevice = remoteDataDiskDevice;
        }

        public String getRemoteMinioContainer() {
            return remoteMinioContainer;
        }

        public void setRemoteMinioContainer(String remoteMinioContainer) {
            this.remoteMinioContainer = remoteMinioContainer;
        }

        public boolean isAccessEnabled() {
            return accessEnabled;
        }

        public void setAccessEnabled(boolean accessEnabled) {
            this.accessEnabled = accessEnabled;
        }

        public String getAccessDisabledReason() {
            return accessDisabledReason;
        }

        public void setAccessDisabledReason(String accessDisabledReason) {
            this.accessDisabledReason = accessDisabledReason;
        }

        public Map<String, Target> getTargets() {
            return targets;
        }

        public void setTargets(Map<String, Target> targets) {
            this.targets = targets;
        }
    }

    public static class Target {
        private String label;
        private Integer port;
        private String url;
        private String actionComponent;
        private String statusScript;
        private String restartScript;
        private boolean actionEnabled;
        private String blockedReason;

        public List<String> restartArguments(Environment environment, String operationRecordPath) {
            if (environment.isLocal()) {
                return List.of("-Component", actionComponent, "-OperationRecordPath", operationRecordPath);
            }
            return List.of(
                    "-ServerHost", text(environment.getHost()),
                    "-ServerUser", text(environment.getServerUser()),
                    "-RemoteAppDir", text(environment.getRemoteAppDir()),
                    "-RemoteDataRoot", text(environment.getRemoteDataRoot()),
                    "-RemoteDataDiskMount", text(environment.getRemoteDataDiskMount()),
                    "-RemoteDataDiskDevice", text(environment.getRemoteDataDiskDevice()),
                    "-RemoteMinioContainer", text(environment.getRemoteMinioContainer()),
                    "-Component", actionComponent,
                    "-OperationRecordPath", operationRecordPath
            );
        }

        private static String text(String value) {
            return value == null ? "" : value;
        }

        public String getLabel() {
            return label;
        }

        public void setLabel(String label) {
            this.label = label;
        }

        public Integer getPort() {
            return port;
        }

        public void setPort(Integer port) {
            this.port = port;
        }

        public String getUrl() {
            return url;
        }

        public void setUrl(String url) {
            this.url = url;
        }

        public String getActionComponent() {
            return actionComponent;
        }

        public void setActionComponent(String actionComponent) {
            this.actionComponent = actionComponent;
        }

        public String getStatusScript() {
            return statusScript;
        }

        public void setStatusScript(String statusScript) {
            this.statusScript = statusScript;
        }

        public String getRestartScript() {
            return restartScript;
        }

        public void setRestartScript(String restartScript) {
            this.restartScript = restartScript;
        }

        public boolean isActionEnabled() {
            return actionEnabled;
        }

        public void setActionEnabled(boolean actionEnabled) {
            this.actionEnabled = actionEnabled;
        }

        public String getBlockedReason() {
            return blockedReason;
        }

        public void setBlockedReason(String blockedReason) {
            this.blockedReason = blockedReason;
        }
    }

    public static class BackupOps {
        private String executionMode = "powershell";
        private String configPath;
        private String linuxScriptPath;
        private String linuxConfigPath;
        private String nasServer;
        private String nasShare;
        private String nasUsername;
        private String nasPassword;
        private String nasDomain;
        private String nasBackupPointsRoot;

        public boolean isLinuxLocal() {
            return "linux-local".equals(executionMode);
        }

        public String getExecutionMode() {
            return executionMode;
        }

        public void setExecutionMode(String executionMode) {
            this.executionMode = executionMode;
        }

        public String getConfigPath() {
            return configPath;
        }

        public void setConfigPath(String configPath) {
            this.configPath = configPath;
        }

        public String getLinuxScriptPath() {
            return linuxScriptPath;
        }

        public void setLinuxScriptPath(String linuxScriptPath) {
            this.linuxScriptPath = linuxScriptPath;
        }

        public String getLinuxConfigPath() {
            return linuxConfigPath;
        }

        public void setLinuxConfigPath(String linuxConfigPath) {
            this.linuxConfigPath = linuxConfigPath;
        }

        public String getNasServer() {
            return nasServer;
        }

        public void setNasServer(String nasServer) {
            this.nasServer = nasServer;
        }

        public String getNasShare() {
            return nasShare;
        }

        public void setNasShare(String nasShare) {
            this.nasShare = nasShare;
        }

        public String getNasUsername() {
            return nasUsername;
        }

        public void setNasUsername(String nasUsername) {
            this.nasUsername = nasUsername;
        }

        public String getNasPassword() {
            return nasPassword;
        }

        public void setNasPassword(String nasPassword) {
            this.nasPassword = nasPassword;
        }

        public String getNasDomain() {
            return nasDomain;
        }

        public void setNasDomain(String nasDomain) {
            this.nasDomain = nasDomain;
        }

        public String getNasBackupPointsRoot() {
            return nasBackupPointsRoot;
        }

        public void setNasBackupPointsRoot(String nasBackupPointsRoot) {
            this.nasBackupPointsRoot = nasBackupPointsRoot;
        }
    }

    public static class ReleasePackage {
        private String nasServer;
        private String nasShare;
        private String nasUsername;
        private String nasPassword;
        private String nasDomain;
        private String nasReleaseRoot;
        private String backendRuntimeBaseMode;
        private String backendRuntimeBaseTarPath;
        private String backendRuntimeBaseTarSha256;
        private String backendRuntimeBaseImage;
        private String backendRuntimeBaseDigest;
        private String backendRuntimeBaseVersion;

        public String getNasServer() {
            return nasServer;
        }

        public void setNasServer(String nasServer) {
            this.nasServer = nasServer;
        }

        public String getNasShare() {
            return nasShare;
        }

        public void setNasShare(String nasShare) {
            this.nasShare = nasShare;
        }

        public String getNasUsername() {
            return nasUsername;
        }

        public void setNasUsername(String nasUsername) {
            this.nasUsername = nasUsername;
        }

        public String getNasPassword() {
            return nasPassword;
        }

        public void setNasPassword(String nasPassword) {
            this.nasPassword = nasPassword;
        }

        public String getNasDomain() {
            return nasDomain;
        }

        public void setNasDomain(String nasDomain) {
            this.nasDomain = nasDomain;
        }

        public String getNasReleaseRoot() {
            return nasReleaseRoot;
        }

        public void setNasReleaseRoot(String nasReleaseRoot) {
            this.nasReleaseRoot = nasReleaseRoot;
        }

        public String getBackendRuntimeBaseMode() {
            return backendRuntimeBaseMode;
        }

        public void setBackendRuntimeBaseMode(String backendRuntimeBaseMode) {
            this.backendRuntimeBaseMode = backendRuntimeBaseMode;
        }

        public String getBackendRuntimeBaseTarPath() {
            return backendRuntimeBaseTarPath;
        }

        public void setBackendRuntimeBaseTarPath(String backendRuntimeBaseTarPath) {
            this.backendRuntimeBaseTarPath = backendRuntimeBaseTarPath;
        }

        public String getBackendRuntimeBaseTarSha256() {
            return backendRuntimeBaseTarSha256;
        }

        public void setBackendRuntimeBaseTarSha256(String backendRuntimeBaseTarSha256) {
            this.backendRuntimeBaseTarSha256 = backendRuntimeBaseTarSha256;
        }

        public String getBackendRuntimeBaseImage() {
            return backendRuntimeBaseImage;
        }

        public void setBackendRuntimeBaseImage(String backendRuntimeBaseImage) {
            this.backendRuntimeBaseImage = backendRuntimeBaseImage;
        }

        public String getBackendRuntimeBaseDigest() {
            return backendRuntimeBaseDigest;
        }

        public void setBackendRuntimeBaseDigest(String backendRuntimeBaseDigest) {
            this.backendRuntimeBaseDigest = backendRuntimeBaseDigest;
        }

        public String getBackendRuntimeBaseVersion() {
            return backendRuntimeBaseVersion;
        }

        public void setBackendRuntimeBaseVersion(String backendRuntimeBaseVersion) {
            this.backendRuntimeBaseVersion = backendRuntimeBaseVersion;
        }
    }
}
