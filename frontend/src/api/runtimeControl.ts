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
  publishScope?: RuntimeControlPublishScope
  includeOnlyOffice?: boolean
  includeShowroomBuildPackage?: boolean
  enableSmartReleaseReport?: boolean
  releaseTag?: string
  testConclusion?: string
  sqlPath?: string
  selectedImageCandidateId?: string
  selectedRecoverySetCandidateId?: string
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

export interface RuntimeControlReleaseStatusVO {
  releasePackages: RuntimeControlReleasePackageVO[]
  targetStates: Record<string, Record<string, RuntimeControlStatusVO>>
  recentOperations: RuntimeControlOperationVO[]
  testCurrentReleaseTag?: string
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

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url.startsWith(API_BASE) ? url : `${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
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

export const resendRuntimeControlAlertSiteMessage = (id: number) => {
  return request<unknown>(`/infra/runtime-control/alerts/${id}/resend-site-message`, {
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
