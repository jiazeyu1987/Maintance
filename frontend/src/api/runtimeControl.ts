const API_BASE = '/admin-api'
const RUNTIME_CONTROL_OVERVIEW_URL = '/admin-api/infra/runtime-control/overview'

export type RuntimeControlDateTime = string | number | number[]
export type RuntimeOpsInspectionStatus = 'PASS' | 'WARN' | 'BLOCKED' | 'NO_GO'
export type RuntimeControlCandidateStatus = 'AVAILABLE' | 'BLOCKED'
export type RuntimeControlPublishScope = 'code-only' | 'with-data'
export type RuntimeControlTargetEnvironment = 'test' | 'prod' | 'backup'

export interface ApiResult<T> {
  code: number
  data: T
  msg: string
}

export interface PageResult<T> {
  list: T[]
  total: number
}

export interface RuntimeControlOperationVO {
  operationId: string
  requestedBy: string
  requestedAt: RuntimeControlDateTime
  environment: string
  component: string
  action?: string
  actionLabel?: string
  parameters?: Record<string, string>
  reason: string
  status: string
  summary?: string
  resultLogPath?: string
}

export interface RuntimeControlLogVO {
  operationId: string
  status: string
  content: string
  length: number
  truncated: boolean
  logPath?: string
}

export interface RuntimeControlStatusVO {
  status: string
  httpStatus?: string
  runtimeState?: string
  url?: string
  port?: number
  currentReleaseTag?: string
  lastOperation?: RuntimeControlOperationVO
  actionEnabled: boolean
  blockedReason?: string
}

export interface RuntimeControlOverviewVO {
  environments: string[]
  components: string[]
  statuses: Record<string, Record<string, RuntimeControlStatusVO>>
}

export interface RuntimeControlActionReqVO {
  action: string
  reason: string
  prodConfirmText?: string
  targetEnvironment?: RuntimeControlTargetEnvironment
  backupKind?: 'FULL' | 'INCREMENTAL'
  publishScope?: RuntimeControlPublishScope
  includeOnlyOffice?: boolean
  includeShowroomBuildPackage?: boolean
  enableSmartReleaseReport?: boolean
  releaseTag?: string
  testConclusion?: string
  sqlPath?: string
  selectedImageCandidateId?: string
  selectedRecoverySetCandidateId?: string
  prodDryRunEvidencePath?: string
  sourceSnapshotToken?: string
}

export interface RuntimeControlRestartReqVO {
  environment: string
  component: string
  reason: string
  prodConfirmText?: string
}

export interface RuntimeControlActionPreviewVO {
  action: string
  actionLabel?: string
  environment: string
  component: string
  scriptPath: string
  arguments: string[]
  parameters?: Record<string, string>
  enableSmartReleaseReport: boolean
  summary?: string
  sourceSnapshotToken?: string
}

export interface RuntimeControlReleasePackageVO {
  releaseTag: string
  packageDirectoryName?: string
  manifestPath?: string
  builtAt?: string
  publishScope?: RuntimeControlPublishScope
  component?: string
  includeShowroomBuildPackage?: boolean
  onlyOfficeIncluded?: boolean
  imageTag?: string
  checksumPresent?: boolean
  tested?: boolean
  testedAt?: string
  operatorName?: string
  testedRecoverySetCandidateId?: string
  testedRecoverySetId?: string
  testedRecoverySetManifestHash?: string
  status?: RuntimeControlCandidateStatus
  blockedReasons?: string[]
}

export interface RuntimeControlReleaseSourceRepoVO {
  name?: string
  pathRole?: string
  commit?: string
  branch?: string
  dirty?: boolean
}

export interface RuntimeControlReleaseNotesVO {
  environment: RuntimeControlTargetEnvironment
  releaseTag: string
  packageDirectoryName?: string
  manifestPath?: string
  builtAt?: string
  publishScope?: RuntimeControlPublishScope
  component?: string
  summary?: string
  changes?: string[]
  sourceRepos?: RuntimeControlReleaseSourceRepoVO[]
  status?: RuntimeControlCandidateStatus
  blockedReasons?: string[]
}

export interface RuntimeControlReleaseStatusVO {
  releasePackages: RuntimeControlReleasePackageVO[]
  targetStates: Record<string, Record<string, RuntimeControlStatusVO>>
  recentOperations: RuntimeControlOperationVO[]
  testCurrentReleaseTag?: string
  prodCurrentReleaseTag?: string
  backupCurrentReleaseTag?: string
  testCurrentReleaseNotes?: RuntimeControlReleaseNotesVO
  prodCurrentReleaseNotes?: RuntimeControlReleaseNotesVO
  backupCurrentReleaseNotes?: RuntimeControlReleaseNotesVO
  latestTestedReleaseTag?: string
}

export interface RuntimeControlCapacityStatusVO {
  status: string
  sampledAt?: RuntimeControlDateTime
  metrics?: Array<{
    code: string
    name: string
    status: string
    usedBytes?: number
    availableBytes?: number
    usagePercent?: number
    reason?: string
  }>
}

export interface RuntimeControlInspectionCheckVO {
  code: string
  name: string
  status: RuntimeOpsInspectionStatus | string
  required: boolean
  evidence?: string
  reason?: string
  sampledAt?: RuntimeControlDateTime
}

export interface RuntimeControlInspectionRunVO {
  id: number
  status: RuntimeOpsInspectionStatus | string
  summary?: string
  startedAt?: RuntimeControlDateTime
  completedAt?: RuntimeControlDateTime
  checks: RuntimeControlInspectionCheckVO[]
}

export interface RuntimeControlBusinessHealthItemVO {
  code: string
  name: string
  status: RuntimeOpsInspectionStatus | string
  evidence?: string
  reason?: string
  sampledAt?: RuntimeControlDateTime
}

export interface RuntimeControlBusinessHealthVO {
  status: RuntimeOpsInspectionStatus | string
  sampledAt?: RuntimeControlDateTime
  items: RuntimeControlBusinessHealthItemVO[]
}

export interface RuntimeControlProbeVO {
  environment: string
  component: string
  probeType?: string
  url?: string
  status: RuntimeOpsInspectionStatus | string
  httpStatusCode?: number
  durationMillis?: number
  error?: string
  sampledAt?: RuntimeControlDateTime
}

export interface RuntimeControlProbeLatestVO {
  status: RuntimeOpsInspectionStatus | string
  sampledAt?: RuntimeControlDateTime
  probes: RuntimeControlProbeVO[]
  alert?: RuntimeControlAlertVO
}

export interface RuntimeControlCandidateVO {
  candidateId: string
  backupId?: string
  releaseTag?: string
  imageTag?: string
  manifestPath?: string
  status: RuntimeControlCandidateStatus
  blockedReasons?: string[]
}

export interface RuntimeControlRollbackCandidateVO extends RuntimeControlCandidateVO {
  prodHistoryPath?: string
  compatibilityStatus?: string
  compatibilityEvidencePath?: string
  compatibilityCheckedAt?: string
  compatibilitySummary?: string
}

export interface RuntimeControlRestoreCandidateVO extends RuntimeControlCandidateVO {
  recoverySetId?: string
  recoverySetStatus?: RuntimeControlCandidateStatus
  programVersion?: string
  redisPolicy?: string
  configurationManifestPath?: string
  configurationComposePath?: string
  recoverySetManifestHash?: string
  componentSummary?: Record<string, string>
  dccBackupMode?: string
  dccChainStatus?: string
  dccChangeSummary?: Record<string, string>
  checksumPath?: string
  rehearsalReportPath?: string
  snapshotPath?: string
}

export interface RuntimeControlBackupPointVO {
  backupId: string
  manifestPath?: string
  checksumPath?: string
  rehearsalReportPath?: string
  snapshotPath?: string
  lastVerifiedAt?: RuntimeControlDateTime
  imageTag?: string
  backupMode?: string
  retentionKeepLast?: number
  retentionKeepDays?: number
  retentionMaxNasUsedPercent?: number
  objectAddedCount?: number
  objectModifiedCount?: number
  objectDeletedCount?: number
  objectReusedCount?: number
  recoverabilityStatus?: RuntimeControlCandidateStatus | string
  dccBackupMode?: string
  dccChainStatus?: string
  dccChangeSummary?: Record<string, string>
  rehearsalStatus?: string
  unrecoverableReasons?: string[]
}

export interface RuntimeControlOwnerMatrixReqVO {
  environment: string
  action: string
  role: string
  required: boolean
  ownerUserId?: number
  ownerName?: string
  escalationPath?: string
}

export interface RuntimeControlOwnerMatrixVO extends RuntimeControlOwnerMatrixReqVO {
  id: number
  updatedAt?: RuntimeControlDateTime
}

export interface RuntimeControlWizardScenarioVO {
  scenario: string
  label: string
  recommendedAction: string
  recommendedActionLabel: string
  symptoms?: string[]
  requiredEvidence?: string[]
  requiredOwnerRoles?: string[]
  blockingConditions?: string[]
}

export interface RuntimeControlWizardRecommendationReqVO {
  scenario: string
}

export interface RuntimeControlWizardRecommendationVO {
  scenario: string
  recommendedAction: string
  recommendedActionLabel: string
  requiredEvidence?: string[]
  requiredOwnerRoles?: string[]
  blockingReasons?: string[]
  rollbackCandidates?: RuntimeControlRollbackCandidateVO[]
  restoreCandidates?: RuntimeControlRestoreCandidateVO[]
}

export interface RuntimeControlAlertReqVO {
  environment: string
  action: string
  severity: string
  title: string
  content: string
  notifyTemplateCode?: string
  templateParams?: Record<string, unknown>
}

export interface RuntimeControlAlertVO extends RuntimeControlAlertReqVO {
  id: number
  siteMessageStatus: string
  notifyMessageId?: number
  siteMessageFailureReason?: string
  createdAt?: RuntimeControlDateTime
  sentAt?: RuntimeControlDateTime
  acknowledgedBy?: string
  acknowledgedAt?: RuntimeControlDateTime
}

export interface RuntimeControlIncidentReqVO {
  environment: string
  action: string
  severity: string
  title: string
  description: string
  sourceType: 'DIRECT' | 'ALERT' | 'HIGH_RISK_OPERATION'
  sourceId?: string
}

export interface RuntimeControlIncidentActionReqVO {
  action: string
  verificationResult: string
  evidence: string
}

export interface RuntimeControlIncidentCloseReqVO {
  ownerGateResult: string
  verificationResult: string
  remainingRisk: string
  postmortemStatus: string
  closeReason: string
}

export interface RuntimeControlIncidentActionVO extends RuntimeControlIncidentActionReqVO {
  operator?: string
  actedAt?: RuntimeControlDateTime
}

export interface RuntimeControlIncidentVO extends RuntimeControlIncidentReqVO {
  id: number
  status: 'OPEN' | 'CLOSED' | string
  createdBy?: string
  createdAt?: RuntimeControlDateTime
  actions?: RuntimeControlIncidentActionVO[]
  ownerGateResult?: string
  verificationResult?: string
  remainingRisk?: string
  postmortemStatus?: string
  closeReason?: string
  closedBy?: string
  closedAt?: RuntimeControlDateTime
}

export interface RuntimeControlRemoteRootDiskStatusVO {
  targetEnvironment: RuntimeControlTargetEnvironment
  serverHost?: string
  availableBytes?: number
  usagePercent?: number
  inodeUsagePercent?: number
  backupTempBytes?: number
  tmpBytes?: number
  sampledAt?: RuntimeControlDateTime
}

export interface RuntimeControlRemoteRootCleanupReqVO {
  targetEnvironment: RuntimeControlTargetEnvironment
  reason: string
  prodConfirmText?: string
}

export interface RuntimeControlRemoteRootCleanupVO {
  deletedEntryCount: number
  before?: RuntimeControlRemoteRootDiskStatusVO
  after?: RuntimeControlRemoteRootDiskStatusVO
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const tokenEntry = localStorage.getItem('ACCESS_TOKEN')
  const tenantEntry = localStorage.getItem('tenantId')
  let accessToken = ''
  let tenantId = ''
  if (tokenEntry) {
    try {
      const parsed = JSON.parse(tokenEntry) as { v?: string }
      const rawValue = parsed.v || ''
      accessToken = rawValue.startsWith('"') ? JSON.parse(rawValue) : rawValue
    } catch {
      throw new Error('登录状态无效，请重新登录')
    }
  }
  if (tenantEntry) {
    try {
      const parsed = JSON.parse(tenantEntry) as { v?: string | number }
      tenantId = parsed.v === undefined ? '' : String(parsed.v)
    } catch {
      throw new Error('租户登录状态无效，请重新登录')
    }
  }
  const response = await fetch(url.startsWith(API_BASE) ? url : `${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(tenantId ? { 'tenant-id': tenantId } : {}),
      ...(init?.headers ?? {})
    },
    ...init
  })
  const body = (await response.json()) as ApiResult<T>
  if (!response.ok || body.code !== 0) {
    throw new Error(body.msg || `HTTP ${response.status}`)
  }
  return body.data
}

export const getRuntimeControlOverview = () => {
  return request<RuntimeControlOverviewVO>(RUNTIME_CONTROL_OVERVIEW_URL)
}

export const getRuntimeControlOperations = () => {
  return request<RuntimeControlOperationVO[]>('/infra/runtime-control/operations')
}

export const getRuntimeControlOperationLog = (operationId: string, maxBytes = 65536) => {
  return request<RuntimeControlLogVO>(
    `/infra/runtime-control/operations/${encodeURIComponent(operationId)}/log?maxBytes=${maxBytes}`
  )
}

export const previewRuntimeControlAction = (data: RuntimeControlActionReqVO) => {
  return request<RuntimeControlActionPreviewVO>('/infra/runtime-control/actions/preview', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const executeRuntimeControlAction = (data: RuntimeControlActionReqVO) => {
  return request<RuntimeControlOperationVO>('/infra/runtime-control/actions', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const restartRuntimeControl = (data: RuntimeControlRestartReqVO) => {
  return request<RuntimeControlOperationVO>('/infra/runtime-control/restart', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const getRuntimeControlReleaseStatus = () => {
  return request<RuntimeControlReleaseStatusVO>('/infra/runtime-control/release-status')
}

export const getRuntimeControlReleasePackages = () => {
  return request<RuntimeControlReleasePackageVO[]>('/infra/runtime-control/release-packages')
}

export const getRuntimeControlRollbackCandidates = () => {
  return request<RuntimeControlRollbackCandidateVO[]>('/infra/runtime-control/rollback-candidates')
}

export const getRuntimeControlRestoreCandidates = () => {
  return request<RuntimeControlRestoreCandidateVO[]>('/infra/runtime-control/restore-candidates')
}

export const runRuntimeControlInspection = () => {
  return request<RuntimeControlInspectionRunVO>('/infra/runtime-control/inspection-runs', {
    method: 'POST'
  })
}

export const getRuntimeControlInspectionRun = (id: number) => {
  return request<RuntimeControlInspectionRunVO>(`/infra/runtime-control/inspection-runs/${id}`)
}

export const getRuntimeControlBusinessHealth = () => {
  return request<RuntimeControlBusinessHealthVO>('/infra/runtime-control/business-health')
}

export const runRuntimeControlProbes = () => {
  return request<RuntimeControlProbeLatestVO>('/infra/runtime-control/probes/run', {
    method: 'POST'
  })
}

export const getRuntimeControlLatestProbes = () => {
  return request<RuntimeControlProbeLatestVO>('/infra/runtime-control/probes/latest')
}

export const getRuntimeControlBackupPoints = () => {
  return request<RuntimeControlBackupPointVO[]>('/infra/runtime-control/backup-points')
}

export const getRuntimeControlBackupPoint = (backupId: string) => {
  return request<RuntimeControlBackupPointVO>(
    `/infra/runtime-control/backup-points/${encodeURIComponent(backupId)}`
  )
}

export const getRuntimeControlAlertsPage = () => {
  return request<PageResult<RuntimeControlAlertVO>>('/infra/runtime-control/alerts/page')
}

export const createRuntimeControlAlert = (data: RuntimeControlAlertReqVO) => {
  return request<RuntimeControlAlertVO>('/infra/runtime-control/alerts', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const resendRuntimeControlAlertSiteMessage = (id: number) => {
  return request<RuntimeControlAlertVO>(`/infra/runtime-control/alerts/${id}/resend-site-message`, {
    method: 'POST'
  })
}

export const acknowledgeRuntimeControlAlert = (id: number) => {
  return request<RuntimeControlAlertVO>(`/infra/runtime-control/alerts/${id}/acknowledge`, {
    method: 'POST'
  })
}

export const getRuntimeControlOwnerMatrix = (params?: { environment?: string; action?: string }) => {
  const query = new URLSearchParams()
  if (params?.environment) query.set('environment', params.environment)
  if (params?.action) query.set('action', params.action)
  const suffix = query.toString() ? `?${query}` : ''
  return request<RuntimeControlOwnerMatrixVO[]>(`/infra/runtime-control/owner-matrix${suffix}`)
}

export const createRuntimeControlOwnerMatrix = (data: RuntimeControlOwnerMatrixReqVO) => {
  return request<RuntimeControlOwnerMatrixVO>('/infra/runtime-control/owner-matrix', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const updateRuntimeControlOwnerMatrix = (id: number, data: RuntimeControlOwnerMatrixReqVO) => {
  return request<RuntimeControlOwnerMatrixVO>(`/infra/runtime-control/owner-matrix/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export const getRuntimeControlWizardScenarios = () => {
  return request<RuntimeControlWizardScenarioVO[]>('/infra/runtime-control/wizard/scenarios')
}

export const getRuntimeControlWizardRecommendation = (
  data: RuntimeControlWizardRecommendationReqVO
) => {
  return request<RuntimeControlWizardRecommendationVO>('/infra/runtime-control/wizard/recommendation', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const getRuntimeControlCapacityStatus = () => {
  return request<RuntimeControlCapacityStatusVO>('/infra/runtime-control/capacity/status')
}

export const getRuntimeControlIncidentsPage = () => {
  return request<PageResult<RuntimeControlIncidentVO>>('/infra/runtime-control/incidents/page')
}

export const createRuntimeControlIncident = (data: RuntimeControlIncidentReqVO) => {
  return request<RuntimeControlIncidentVO>('/infra/runtime-control/incidents', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const recordRuntimeControlIncidentAction = (
  id: number,
  data: RuntimeControlIncidentActionReqVO
) => {
  return request<RuntimeControlIncidentVO>(`/infra/runtime-control/incidents/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const closeRuntimeControlIncident = (id: number, data: RuntimeControlIncidentCloseReqVO) => {
  return request<RuntimeControlIncidentVO>(`/infra/runtime-control/incidents/${id}/close`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export const getRuntimeControlRemoteRootDiskStatus = (
  targetEnvironment: RuntimeControlTargetEnvironment
) => {
  return request<RuntimeControlRemoteRootDiskStatusVO>(
    `/infra/runtime-control/remote-root-disk/status?targetEnvironment=${encodeURIComponent(targetEnvironment)}`
  )
}

export const cleanupRuntimeControlRemoteRootTemporaryFiles = (
  data: RuntimeControlRemoteRootCleanupReqVO
) => {
  return request<RuntimeControlRemoteRootCleanupVO>('/infra/runtime-control/remote-root-disk/cleanup', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}
