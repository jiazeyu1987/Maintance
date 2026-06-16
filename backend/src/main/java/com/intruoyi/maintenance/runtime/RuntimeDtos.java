package com.intruoyi.maintenance.runtime;

import jakarta.validation.constraints.NotBlank;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class RuntimeDtos {
    private RuntimeDtos() {
    }

    public record RuntimeControlOverviewRespVO(
            List<String> environments,
            List<String> components,
            Map<String, Map<String, RuntimeControlStatusRespVO>> statuses
    ) {
    }

    public record RuntimeControlStatusRespVO(
            String status,
            String httpStatus,
            String runtimeState,
            String url,
            Integer port,
            String currentReleaseTag,
            RuntimeControlOperationRespVO lastOperation,
            boolean actionEnabled,
            String blockedReason
    ) {
    }

    public record RuntimeControlRestartReqVO(
            @NotBlank String environment,
            @NotBlank String component,
            @NotBlank String reason,
            String prodConfirmText
    ) {
    }

    public record RuntimeControlActionReqVO(
            @NotBlank String action,
            @NotBlank String reason,
            String prodConfirmText,
            String targetEnvironment,
            String publishScope,
            Boolean includeOnlyOffice,
            Boolean includeShowroomBuildPackage,
            Boolean enableSmartReleaseReport,
            String releaseTag,
            String testConclusion,
            String sqlPath,
            String selectedImageCandidateId,
            String selectedImageTag,
            String selectedRecoverySetCandidateId,
            String selectedBackupId,
            String recoverySetId,
            String recoverySetManifestHash,
            String recoverySetProgramVersion,
            String recoverySetRedisPolicy
    ) {
    }

    public record RuntimeControlActionPreviewRespVO(
            String action,
            String actionLabel,
            String environment,
            String component,
            String scriptPath,
            List<String> arguments,
            Map<String, String> parameters,
            boolean enableSmartReleaseReport,
            String summary
    ) {
    }

    public record RuntimeControlOperationRespVO(
            String operationId,
            String requestedBy,
            Instant requestedAt,
            String environment,
            String component,
            String action,
            String actionLabel,
            Map<String, String> parameters,
            String reason,
            String status,
            String summary,
            String resultLogPath
    ) {
    }

    public record RuntimeControlLogRespVO(
            String operationId,
            String status,
            String content,
            int length,
            boolean truncated,
            String logPath
    ) {
    }

    public record RuntimeControlReleasePackageRespVO(
            String releaseTag,
            String packageDirectoryName,
            String manifestPath,
            String builtAt,
            String publishScope,
            String component,
            Boolean includeShowroomBuildPackage,
            Boolean onlyOfficeIncluded,
            String imageTag,
            Boolean checksumPresent,
            Boolean tested,
            String testedAt,
            String operatorName,
            String testedRecoverySetCandidateId,
            String testedRecoverySetId,
            String testedRecoverySetManifestHash,
            String status,
            List<String> blockedReasons
    ) {
    }

    public record RuntimeControlReleaseStatusRespVO(
            List<RuntimeControlReleasePackageRespVO> releasePackages,
            Map<String, Map<String, RuntimeControlStatusRespVO>> targetStates,
            List<RuntimeControlOperationRespVO> recentOperations,
            String testCurrentReleaseTag,
            String latestTestedReleaseTag
    ) {
    }

    public record RuntimeControlCandidateRespVO(
            String candidateId,
            String backupId,
            String releaseTag,
            String imageTag,
            String manifestPath,
            String status,
            List<String> blockedReasons
    ) {
    }

    public record RuntimeControlInspectionRunRespVO(
            Long id,
            String status,
            String summary,
            Instant startedAt,
            Instant completedAt,
            List<RuntimeControlInspectionCheckRespVO> checks
    ) {
    }

    public record RuntimeControlInspectionCheckRespVO(
            String code,
            String name,
            String status,
            boolean required,
            String evidence,
            String reason,
            Instant sampledAt
    ) {
    }

    public record RuntimeControlBusinessHealthRespVO(
            String status,
            Instant sampledAt,
            List<RuntimeControlBusinessHealthItemRespVO> items
    ) {
    }

    public record RuntimeControlBusinessHealthItemRespVO(
            String code,
            String name,
            String status,
            String evidence,
            String reason,
            Instant sampledAt
    ) {
    }

    public record RuntimeControlProbeLatestRespVO(
            Instant sampledAt,
            List<RuntimeControlProbeRespVO> probes
    ) {
    }

    public record RuntimeControlProbeRespVO(
            String environment,
            String name,
            String status,
            String evidence,
            String reason,
            Instant sampledAt
    ) {
    }

    public record RuntimeControlCapacityStatusRespVO(
            String status,
            Instant sampledAt,
            List<RuntimeControlStorageMetricRespVO> metrics,
            RuntimeControlAlertRespVO alert
    ) {
    }

    public record RuntimeControlStorageMetricRespVO(
            String code,
            String name,
            String status,
            Long usedBytes,
            Long availableBytes,
            Double usagePercent,
            String reason
    ) {
    }

    public record RuntimeControlRemoteRootDiskStatusRespVO(
            String targetEnvironment,
            String serverHost,
            Long availableBytes,
            Double usagePercent,
            Double inodeUsagePercent,
            Long backupTempBytes,
            Long tmpBytes,
            Instant sampledAt
    ) {
    }

    public record RuntimeControlRemoteRootCleanupReqVO(
            @NotBlank String targetEnvironment,
            @NotBlank String reason,
            String prodConfirmText
    ) {
    }

    public record RuntimeControlRemoteRootCleanupRespVO(
            int deletedEntryCount,
            RuntimeControlRemoteRootDiskStatusRespVO before,
            RuntimeControlRemoteRootDiskStatusRespVO after
    ) {
    }

    public record RuntimeControlAlertCreateReqVO(
            @NotBlank String environment,
            @NotBlank String action,
            @NotBlank String severity,
            @NotBlank String title,
            @NotBlank String content,
            String notifyTemplateCode,
            Map<String, Object> templateParams
    ) {
    }

    public record RuntimeControlAlertRespVO(
            Long id,
            String environment,
            String action,
            String severity,
            String title,
            String content,
            String notifyTemplateCode,
            Map<String, Object> templateParams,
            String siteMessageStatus,
            Long notifyMessageId,
            String siteMessageFailureReason,
            Instant createdAt,
            Instant sentAt,
            String acknowledgedBy,
            Instant acknowledgedAt
    ) {
    }

    public record RuntimeControlIncidentCreateReqVO(
            @NotBlank String environment,
            @NotBlank String severity,
            @NotBlank String title,
            @NotBlank String summary
    ) {
    }

    public record RuntimeControlIncidentActionReqVO(@NotBlank String action, @NotBlank String content) {
    }

    public record RuntimeControlIncidentCloseReqVO(@NotBlank String conclusion) {
    }

    public record RuntimeControlIncidentRespVO(
            Long id,
            String environment,
            String severity,
            String title,
            String summary,
            String status,
            Instant createdAt,
            Instant closedAt,
            String conclusion
    ) {
    }
}
