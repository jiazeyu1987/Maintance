package com.intruoyi.maintenance.runtime;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

import static com.intruoyi.maintenance.runtime.RuntimeDtos.*;

@RestController
public class RuntimeControlController {

    private static final String OPERATOR_IDENTITY = "local-operator";

    private final RuntimeControlService runtimeControlService;

    public RuntimeControlController(RuntimeControlService runtimeControlService) {
        this.runtimeControlService = runtimeControlService;
    }

    @GetMapping("/admin-api/infra/runtime-control/overview")
    public ApiResult<RuntimeControlOverviewRespVO> getOverview() {
        return ApiResult.success(runtimeControlService.getOverview());
    }

    @PostMapping("/admin-api/infra/runtime-control/restart")
    public ApiResult<RuntimeControlOperationRespVO> restart(@Valid @RequestBody RuntimeControlRestartReqVO req) {
        return ApiResult.success(runtimeControlService.restart(req));
    }

    @PostMapping("/admin-api/infra/runtime-control/actions")
    public ApiResult<RuntimeControlOperationRespVO> executeAction(@Valid @RequestBody RuntimeControlActionReqVO req) {
        return ApiResult.success(runtimeControlService.executeAction(req));
    }

    @PostMapping("/admin-api/infra/runtime-control/actions/preview")
    public ApiResult<RuntimeControlActionPreviewRespVO> previewAction(@Valid @RequestBody RuntimeControlActionReqVO req) {
        return ApiResult.success(runtimeControlService.previewAction(req));
    }

    @GetMapping("/admin-api/infra/runtime-control/operations")
    public ApiResult<List<RuntimeControlOperationRespVO>> getOperations() {
        return ApiResult.success(runtimeControlService.getOperations());
    }

    @GetMapping("/admin-api/infra/runtime-control/operations/{operationId}/log")
    public ApiResult<RuntimeControlLogRespVO> getOperationLog(@PathVariable String operationId,
                                                              @RequestParam(required = false) Integer maxBytes) {
        return ApiResult.success(runtimeControlService.getOperationLog(operationId, maxBytes));
    }

    @GetMapping("/admin-api/infra/runtime-control/release-packages")
    public ApiResult<List<RuntimeControlReleasePackageRespVO>> getReleasePackages() {
        return ApiResult.success(runtimeControlService.getReleasePackages());
    }

    @GetMapping("/admin-api/infra/runtime-control/release-status")
    public ApiResult<RuntimeControlReleaseStatusRespVO> getReleaseStatus() {
        return ApiResult.success(runtimeControlService.getReleaseStatus());
    }

    @GetMapping("/admin-api/infra/runtime-control/rollback-candidates")
    public ApiResult<List<RuntimeControlCandidateRespVO>> getRollbackCandidates() {
        return ApiResult.success(runtimeControlService.getRollbackCandidates());
    }

    @GetMapping("/admin-api/infra/runtime-control/restore-candidates")
    public ApiResult<List<RuntimeControlCandidateRespVO>> getRestoreCandidates() {
        return ApiResult.success(runtimeControlService.getRestoreCandidates());
    }

    @PostMapping("/admin-api/infra/runtime-control/inspection-runs")
    public ApiResult<RuntimeControlInspectionRunRespVO> runInspection() {
        return ApiResult.success(runtimeControlService.runInspection());
    }

    @GetMapping("/admin-api/infra/runtime-control/inspection-runs/{id}")
    public ApiResult<RuntimeControlInspectionRunRespVO> getInspectionRun(@PathVariable Long id) {
        return ApiResult.success(runtimeControlService.getInspectionRun(id));
    }

    @GetMapping("/admin-api/infra/runtime-control/business-health")
    public ApiResult<RuntimeControlBusinessHealthRespVO> getBusinessHealth() {
        return ApiResult.success(runtimeControlService.getBusinessHealth());
    }

    @PostMapping("/admin-api/infra/runtime-control/probes/run")
    public ApiResult<RuntimeControlProbeLatestRespVO> runProbes() {
        return ApiResult.success(runtimeControlService.runProbes());
    }

    @GetMapping("/admin-api/infra/runtime-control/probes/latest")
    public ApiResult<RuntimeControlProbeLatestRespVO> getLatestProbes() {
        return ApiResult.success(runtimeControlService.getLatestProbes());
    }

    @GetMapping("/admin-api/infra/runtime-control/capacity/status")
    public ApiResult<RuntimeControlCapacityStatusRespVO> getCapacityStatus() {
        return ApiResult.success(runtimeControlService.getCapacityStatus());
    }

    @GetMapping("/admin-api/infra/runtime-control/remote-root-disk/status")
    public ApiResult<RuntimeControlRemoteRootDiskStatusRespVO> getRemoteRootDiskStatus(
            @RequestParam String targetEnvironment) {
        return ApiResult.success(runtimeControlService.getRemoteRootDiskStatus(targetEnvironment));
    }

    @PostMapping("/admin-api/infra/runtime-control/remote-root-disk/cleanup")
    public ApiResult<RuntimeControlRemoteRootCleanupRespVO> cleanupRemoteRootTemporaryFiles(
            @Valid @RequestBody RuntimeControlRemoteRootCleanupReqVO req) {
        return ApiResult.success(runtimeControlService.cleanupRemoteRootTemporaryFiles(req));
    }

    @GetMapping("/admin-api/infra/runtime-control/backup-points")
    public ApiResult<List<RuntimeControlCandidateRespVO>> getBackupPoints() {
        return ApiResult.success(runtimeControlService.getBackupPoints());
    }

    @GetMapping("/admin-api/infra/runtime-control/backup-points/{backupId}")
    public ApiResult<RuntimeControlCandidateRespVO> getBackupPoint(@PathVariable String backupId) {
        return ApiResult.success(runtimeControlService.getBackupPoint(backupId));
    }

    @GetMapping("/admin-api/infra/runtime-control/alerts/page")
    public ApiResult<PageResult<RuntimeControlAlertRespVO>> getAlertsPage() {
        return ApiResult.success(runtimeControlService.getAlertsPage());
    }

    @PostMapping("/admin-api/infra/runtime-control/alerts")
    public ApiResult<RuntimeControlAlertRespVO> createAlert(@Valid @RequestBody RuntimeControlAlertCreateReqVO req) {
        return ApiResult.success(runtimeControlService.createAlert(req));
    }

    @PostMapping("/admin-api/infra/runtime-control/alerts/{id}/acknowledge")
    public ApiResult<RuntimeControlAlertRespVO> acknowledgeAlert(@PathVariable Long id) {
        return ApiResult.success(runtimeControlService.acknowledgeAlert(id));
    }

    @GetMapping("/admin-api/infra/runtime-control/incidents/page")
    public ApiResult<PageResult<RuntimeControlIncidentRespVO>> getIncidentsPage() {
        return ApiResult.success(runtimeControlService.getIncidentsPage());
    }

    @PostMapping("/admin-api/infra/runtime-control/incidents")
    public ApiResult<RuntimeControlIncidentRespVO> createIncident(@Valid @RequestBody RuntimeControlIncidentCreateReqVO req) {
        return ApiResult.success(runtimeControlService.createIncident(req));
    }

    @PostMapping("/admin-api/infra/runtime-control/incidents/{id}/actions")
    public ApiResult<RuntimeControlIncidentRespVO> recordIncidentAction(@PathVariable Long id,
                                                                        @Valid @RequestBody RuntimeControlIncidentActionReqVO req) {
        return ApiResult.success(runtimeControlService.recordIncidentAction(id, req));
    }

    @PostMapping("/admin-api/infra/runtime-control/incidents/{id}/close")
    public ApiResult<RuntimeControlIncidentRespVO> closeIncident(@PathVariable Long id,
                                                                 @Valid @RequestBody RuntimeControlIncidentCloseReqVO req) {
        return ApiResult.success(runtimeControlService.closeIncident(id, req));
    }

    String operatorIdentityForContract() {
        return OPERATOR_IDENTITY;
    }
}
