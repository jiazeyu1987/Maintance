const API_BASE = '/admin-api'
const RUNTIME_CONTROL_OVERVIEW_URL = '/admin-api/infra/runtime-control/overview'

export type RuntimeControlDateTime = string | number | number[]
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
  selectedImageTag?: string
  selectedRecoverySetCandidateId?: string
  selectedBackupId?: string
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
  status?: string
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

export const getRuntimeControlCapacityStatus = () => {
  return request<RuntimeControlCapacityStatusVO>('/infra/runtime-control/capacity/status')
}
