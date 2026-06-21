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
            String recoverySetRedisPolicy,
            String prodDryRunEvidencePath
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

    public record RuntimeControlRollbackCandidateRespVO(
            String candidateId,
            String backupId,
            String releaseTag,
            String imageTag,
            String manifestPath,
            String status,
            List<String> blockedReasons,
            String prodHistoryPath,
            String compatibilityStatus,
            String compatibilityEvidencePath,
            String compatibilityCheckedAt,
            String compatibilitySummary
    ) {
    }

    public record RuntimeControlRestoreCandidateRespVO(
            String candidateId,
            String backupId,
            String releaseTag,
            String imageTag,
            String manifestPath,
            String status,
            List<String> blockedReasons,
            String recoverySetId,
            String recoverySetStatus,
            String programVersion,
            String redisPolicy,
            String configurationManifestPath,
            String configurationComposePath,
            String recoverySetManifestHash,
            Map<String, String> componentSummary,
            String dccBackupMode,
            String dccChainStatus,
            Map<String, String> dccChangeSummary,
            String checksumPath,
            String rehearsalReportPath,
            String snapshotPath
    ) {
    }

    public record RuntimeControlBackupPointRespVO(
            String backupId,
            String manifestPath,
            String checksumPath,
            String rehearsalReportPath,
            String snapshotPath,
            Instant lastVerifiedAt,
            String imageTag,
            String backupMode,
            Integer retentionKeepLast,
            Integer retentionKeepDays,
            Double retentionMaxNasUsedPercent,
            Integer objectAddedCount,
            Integer objectModifiedCount,
            Integer objectDeletedCount,
            Integer objectReusedCount,
            String recoverabilityStatus,
            String dccBackupMode,
            String dccChainStatus,
            Map<String, String> dccChangeSummary,
            String rehearsalStatus,
            List<String> unrecoverableReasons
    ) {
    }

    public record RuntimeControlOwnerMatrixSaveReqVO(
            @NotBlank String environment,
            @NotBlank String action,
            @NotBlank String role,
            Boolean required,
            Long ownerUserId,
            String ownerName,
            String escalationPath
    ) {
    }

    public record RuntimeControlOwnerMatrixRespVO(
            Long id,
            String environment,
            String action,
            String role,
            Boolean required,
            Long ownerUserId,
            String ownerName,
            String escalationPath,
            Instant updatedAt
    ) {
    }

    public record RuntimeControlWizardScenarioRespVO(
            String scenario,
            String label,
            String recommendedAction,
            String recommendedActionLabel,
            List<String> symptoms,
            List<String> requiredEvidence,
            List<String> requiredOwnerRoles,
            List<String> blockingConditions
    ) {
    }

    public record RuntimeControlWizardRecommendationReqVO(@NotBlank String scenario) {
    }

    public record RuntimeControlWizardRecommendationRespVO(
            String scenario,
            String recommendedAction,
            String recommendedActionLabel,
            List<String> requiredEvidence,
            List<String> requiredOwnerRoles,
            List<String> blockingReasons,
            List<RuntimeControlRollbackCandidateRespVO> rollbackCandidates,
            List<RuntimeControlRestoreCandidateRespVO> restoreCandidates
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
            String status,
            Instant sampledAt,
            List<RuntimeControlProbeRespVO> probes,
            RuntimeControlAlertRespVO alert
    ) {
    }

    public record RuntimeControlProbeRespVO(
            String environment,
            String component,
            String probeType,
            String url,
            String status,
            Integer httpStatusCode,
            Long durationMillis,
            String error,
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
            @NotBlank String action,
            @NotBlank String severity,
            @NotBlank String title,
            @NotBlank String description,
            @NotBlank String sourceType,
            String sourceId
    ) {
    }

    public record RuntimeControlIncidentActionReqVO(
            @NotBlank String action,
            @NotBlank String verificationResult,
            @NotBlank String evidence
    ) {
    }

    public record RuntimeControlIncidentCloseReqVO(
            @NotBlank String ownerGateResult,
            @NotBlank String verificationResult,
            @NotBlank String remainingRisk,
            @NotBlank String postmortemStatus,
            @NotBlank String closeReason
    ) {
    }

    public record RuntimeControlIncidentActionRespVO(
            String action,
            String operator,
            String verificationResult,
            String evidence,
            Instant actedAt
    ) {
    }

    public record RuntimeControlIncidentRespVO(
            Long id,
            String environment,
            String action,
            String severity,
            String title,
            String description,
            String sourceType,
            String sourceId,
            String status,
            String createdBy,
            Instant createdAt,
            List<RuntimeControlIncidentActionRespVO> actions,
            String ownerGateResult,
            String verificationResult,
            String remainingRisk,
            String postmortemStatus,
            String closeReason,
            String closedBy,
            Instant closedAt
    ) {
    }
}
