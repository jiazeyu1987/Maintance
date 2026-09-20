<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CircleCheck,
  Document,
  Monitor,
  Refresh,
  Search,
  Warning,
  VideoPlay
} from '@element-plus/icons-vue'
import {
  executeRuntimeControlAction,
  getRuntimeControlCapacityStatus,
  getRuntimeControlOperationLog,
  getRuntimeControlOperations,
  getRuntimeControlOverview,
  getRuntimeControlRollbackCandidates,
  getRuntimeControlRestoreCandidates,
  getRuntimeControlReleaseStatus,
  previewRuntimeControlAction,
  restartRuntimeControl,
  type RuntimeControlReleaseNotesVO,
  type RuntimeControlReleaseStatusVO,
  type RuntimeControlActionPreviewVO,
  type RuntimeControlLogVO,
  type RuntimeControlOperationVO,
  type RuntimeControlOverviewVO,
  type RuntimeControlRollbackCandidateVO,
  type RuntimeControlRestoreCandidateVO,
  type RuntimeControlStatusVO
} from './api/runtimeControl'

interface RuntimeAction {
  action: string
  label: string
  level: 'normal' | 'warning' | 'danger'
  targetEnvironment?: 'test' | 'prod' | 'backup'
  publishScope?: 'code-only' | 'with-data'
}

const actions: RuntimeAction[] = [
  { action: 'build-release', label: '构建发布包', level: 'normal', publishScope: 'code-only' },
  { action: 'publish-test', label: '部署测试服', level: 'normal', targetEnvironment: 'test' },
  { action: 'apply-test-db-sql', label: '测试服数据库快应用', level: 'warning', targetEnvironment: 'test' },
  { action: 'mark-release-tested', label: '标记测试通过', level: 'normal', targetEnvironment: 'test' },
  { action: 'promote-backup', label: '上线备份服', level: 'warning', targetEnvironment: 'backup' },
  { action: 'backup-now', label: '立即备份', level: 'warning', targetEnvironment: 'prod' },
  { action: 'rollback-app', label: '回滚应用', level: 'danger', targetEnvironment: 'prod' },
  { action: 'restore-data', label: '恢复数据', level: 'danger', targetEnvironment: 'prod' },
  { action: 'rehearsal', label: '恢复演练', level: 'normal', targetEnvironment: 'test' }
]

const overview = ref<RuntimeControlOverviewVO>()
const releaseStatus = ref<RuntimeControlReleaseStatusVO>()
const operations = ref<RuntimeControlOperationVO[]>([])
const rollbackCandidates = ref<RuntimeControlRollbackCandidateVO[]>([])
const restoreCandidates = ref<RuntimeControlRestoreCandidateVO[]>([])
const releaseError = ref('')
const apiError = ref('')
const loading = ref(false)
const releaseStatusLoading = ref(false)
const previewLoading = ref(false)
const previewDialogVisible = ref(false)
const preview = ref<RuntimeControlActionPreviewVO>()
const operationLogDialogVisible = ref(false)
const operationLogLoading = ref(false)
const operationLogLoadingId = ref('')
const operationLog = ref<RuntimeControlLogVO>()
const releaseNotesDialogVisible = ref(false)
const selectedReleaseNotes = ref<RuntimeControlReleaseNotesVO>()
const selectedActionKey = ref(actions[0].action)
const selectedAction = computed(() => {
  return actions.find((item) => item.action === selectedActionKey.value) || actions[0]
})
const restartTarget = reactive({ environment: 'local', component: 'intruoyi-backend' })
const capacityStatus = ref('')

const actionForm = reactive({
  reason: '独立控制台本机验证，仅预览命令',
  prodConfirmText: '',
  releaseTag: '',
  publishScope: 'code-only' as 'code-only' | 'with-data',
  targetEnvironment: 'test' as 'test' | 'prod' | 'backup',
  backupKind: 'FULL' as 'FULL' | 'INCREMENTAL',
  sqlPath: '',
  testConclusion: '回归通过，允许上线正式服',
  selectedImageCandidateId: '',
  selectedRecoverySetCandidateId: '',
  includeOnlyOffice: false,
  includeShowroomBuildPackage: false,
  enableSmartReleaseReport: false
})

const flattenedStatuses = computed(() => {
  const result: Array<RuntimeControlStatusVO & { environment: string; component: string }> = []
  const source = overview.value?.statuses ?? {}
  for (const [environment, components] of Object.entries(source)) {
    for (const [component, status] of Object.entries(components)) {
      result.push({ environment, component, ...status })
    }
  }
  return result
})

const runningStatusCount = computed(() => {
  return flattenedStatuses.value.filter((item) => item.status === 'RUNNING' || item.status === 'PASS').length
})

const blockedStatusCount = computed(() => {
  return flattenedStatuses.value.filter((item) => item.status !== 'RUNNING' && item.status !== 'PASS').length
})

const latestOperation = computed(() => operations.value[0])

const statusSummary = computed(() => [
  { label: '运行实例', value: String(runningStatusCount.value), tone: 'success' },
  { label: '异常/停止', value: String(blockedStatusCount.value), tone: blockedStatusCount.value > 0 ? 'danger' : 'muted' },
  { label: '操作记录', value: String(operations.value.length), tone: 'info' },
  { label: '容量状态', value: capacityStatus.value || 'UNKNOWN', tone: statusType(capacityStatus.value || 'UNKNOWN') }
])

const actionDescriptions: Record<string, string> = {
  'build-release': '生成发布包，不直接部署到任何环境',
  'publish-test': '将已构建发布包部署到测试服',
  'apply-test-db-sql': '只应用明确 SQL，不同步数据库整库、MinIO 或发布包状态',
  'mark-release-tested': '记录发布包测试通过结论',
  'promote-backup': '备份服写入动作，必须满足确认条件',
  'backup-now': '触发目标环境备份任务',
  'rollback-app': '按候选镜像回滚应用',
  'restore-data': '按候选备份恢复数据',
  rehearsal: '在测试环境执行恢复演练'
}

const selectedActionSummary = computed(() => {
  return actionDescriptions[selectedAction.value.action] || '本机运维动作'
})

const prodConfirmPlaceholder = computed(() => {
  return selectedAction.value.action === 'backup-now' ? 'PROD-BACKUP-172.30.30.57' : 'PROD'
})

const prodConfirmLabel = computed(() => {
  return selectedAction.value.action === 'backup-now' ? '正式备份确认' : '生产确认'
})

const selectedStatus = computed(() => {
  return overview.value?.statuses?.[restartTarget.environment]?.[restartTarget.component]
})

const buildVersion = __APP_VERSION__

const runtimeVersionItems = computed(() => [
  {
    label: '软件版本',
    value: buildVersion,
    tone: 'build',
    notes: undefined
  },
  {
    label: '测试服',
    value: releaseVersionValue(releaseStatus.value?.testCurrentReleaseTag),
    tone: releaseStatus.value?.testCurrentReleaseTag ? 'info' : 'muted',
    notes: releaseStatus.value?.testCurrentReleaseNotes
  },
  {
    label: '正式服',
    value: releaseVersionValue(releaseStatus.value?.prodCurrentReleaseTag),
    tone: releaseStatus.value?.prodCurrentReleaseTag ? 'warning' : 'muted',
    notes: releaseStatus.value?.prodCurrentReleaseNotes
  },
  {
    label: '备份服',
    value: releaseVersionValue(releaseStatus.value?.backupCurrentReleaseTag),
    tone: releaseStatus.value?.backupCurrentReleaseTag ? 'success' : 'muted',
    notes: releaseStatus.value?.backupCurrentReleaseNotes
  }
])

const selectedReleaseNotesChanges = computed(() => selectedReleaseNotes.value?.changes || [])

const selectedReleaseNotesDisplayChanges = computed(() => {
  if (selectedReleaseNotesChanges.value.length) {
    return selectedReleaseNotesChanges.value
  }
  const summary = selectedReleaseNotes.value?.summary?.trim()
  return summary ? [summary] : []
})

function openReleaseNotes(item: { label: string; notes?: RuntimeControlReleaseNotesVO }) {
  if (!item.notes) return
  selectedReleaseNotes.value = item.notes
  releaseNotesDialogVisible.value = true
}

function statusType(status: string) {
  if (status === 'RUNNING' || status === 'PASS') return 'success'
  if (status === 'UNKNOWN' || status === 'DEGRADED' || status === 'WARN') return 'warning'
  return 'danger'
}

function actionButtonType(level: RuntimeAction['level']) {
  if (level === 'danger') return 'danger'
  if (level === 'warning') return 'warning'
  return 'primary'
}

function actionLevelLabel(level: RuntimeAction['level']) {
  if (level === 'danger') return '高危'
  if (level === 'warning') return '警告'
  return '常规'
}

function operationSupportsPublishScope(action: string) {
  return action === 'build-release'
}

function operationSupportsSmartReleaseReport(action: string) {
  return ['build-release', 'publish-test', 'promote-backup'].includes(action)
}

function operationRequiresTargetEnvironment(action: string) {
  return [
    'publish-test',
    'promote-backup',
    'backup-now',
    'rollback-app',
    'restore-data'
  ].includes(action)
}

function operationUsesReleaseTag(action: string) {
  return ['build-release', 'publish-test', 'promote-backup'].includes(action)
}

function operationUsesTestConclusion(action: string) {
  return action === 'mark-release-tested'
}

function operationUsesSqlPath(action: string) {
  return action === 'apply-test-db-sql'
}

function operationUsesImageCandidate(action: string) {
  return action === 'rollback-app'
}

function operationUsesRecoverySetCandidate(action: string) {
  return ['mark-release-tested', 'rehearsal', 'restore-data'].includes(action)
}

function statusClass(status: string) {
  if (status === 'RUNNING' || status === 'PASS' || status === 'SUCCESS') return 'status-pill--success'
  if (status === 'UNKNOWN' || status === 'DEGRADED' || status === 'WARN' || status === 'RUNNING') {
    return 'status-pill--warn'
  }
  if (status === 'FAILED' || status === 'STOPPED' || status === 'DOWN') return 'status-pill--danger'
  return 'status-pill--muted'
}

function toneClass(tone: string) {
  if (tone === 'success') return 'summary-card--success'
  if (tone === 'danger') return 'summary-card--danger'
  if (tone === 'warning') return 'summary-card--warning'
  return 'summary-card--info'
}

function releaseVersionValue(value?: string) {
  return value?.trim() || (releaseStatusLoading.value ? '加载中' : '未上报')
}

function handleActionChange(value: string | number | boolean) {
  selectedActionKey.value = String(value)
  actionForm.targetEnvironment = selectedAction.value.targetEnvironment || 'test'
  actionForm.publishScope = selectedAction.value.publishScope || actionForm.publishScope
  actionForm.sqlPath = ''
  actionForm.selectedImageCandidateId = ''
  actionForm.selectedRecoverySetCandidateId = ''
}

function requestPayload() {
  const action = selectedAction.value.action
  const releaseTag = actionForm.releaseTag.trim()
  return {
    action,
    reason: actionForm.reason,
    prodConfirmText: actionForm.prodConfirmText || undefined,
    targetEnvironment: operationRequiresTargetEnvironment(selectedAction.value.action)
      ? actionForm.targetEnvironment || selectedAction.value.targetEnvironment
      : undefined,
    backupKind: action === 'backup-now' ? actionForm.backupKind : undefined,
    publishScope: operationSupportsPublishScope(selectedAction.value.action)
      ? actionForm.publishScope
      : undefined,
    includeOnlyOffice: operationSupportsPublishScope(action) ? actionForm.includeOnlyOffice : undefined,
    includeShowroomBuildPackage: operationSupportsPublishScope(action)
      ? actionForm.includeShowroomBuildPackage
      : undefined,
    enableSmartReleaseReport: operationSupportsSmartReleaseReport(action)
      ? actionForm.enableSmartReleaseReport
      : undefined,
    releaseTag: operationUsesReleaseTag(selectedAction.value.action) && releaseTag ? releaseTag : undefined,
    sqlPath: operationUsesSqlPath(action) ? actionForm.sqlPath.trim() || undefined : undefined,
    selectedImageCandidateId: operationUsesImageCandidate(action)
      ? actionForm.selectedImageCandidateId || undefined
      : undefined,
    selectedRecoverySetCandidateId: operationUsesRecoverySetCandidate(action)
      ? actionForm.selectedRecoverySetCandidateId || undefined
      : undefined,
    testConclusion: operationUsesTestConclusion(selectedAction.value.action)
      ? actionForm.testConclusion.trim() || undefined
      : undefined
  }
}

async function loadData() {
  loading.value = true
  apiError.value = ''
  releaseError.value = ''
  try {
    const [overviewResp, operationResp, capacityResp] = await Promise.all([
      getRuntimeControlOverview(),
      getRuntimeControlOperations(),
      getRuntimeControlCapacityStatus()
    ])
    overview.value = overviewResp
    operations.value = operationResp
    capacityStatus.value = capacityResp.status
  } catch (error) {
    apiError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
  releaseStatusLoading.value = true
  try {
    const [releaseStatusResp, rollbackResp, restoreResp] = await Promise.all([
      getRuntimeControlReleaseStatus(),
      getRuntimeControlRollbackCandidates(),
      getRuntimeControlRestoreCandidates()
    ])
    releaseStatus.value = releaseStatusResp
    rollbackCandidates.value = rollbackResp
    restoreCandidates.value = restoreResp
    if (!actionForm.releaseTag && releaseStatusResp.latestTestedReleaseTag) {
      actionForm.releaseTag = releaseStatusResp.latestTestedReleaseTag
    }
  } catch (error) {
    releaseError.value = error instanceof Error ? error.message : String(error)
  } finally {
    releaseStatusLoading.value = false
  }
}

async function previewAction() {
  previewLoading.value = true
  apiError.value = ''
  try {
    preview.value = await previewRuntimeControlAction(requestPayload())
    previewDialogVisible.value = true
  } catch (error) {
    apiError.value = error instanceof Error ? error.message : String(error)
  } finally {
    previewLoading.value = false
  }
}

async function executeAction() {
  previewLoading.value = true
  apiError.value = ''
  try {
    const operation = await executeRuntimeControlAction(requestPayload())
    operations.value = [operation, ...operations.value]
    previewDialogVisible.value = false
  } catch (error) {
    apiError.value = error instanceof Error ? error.message : String(error)
  } finally {
    previewLoading.value = false
  }
}

async function restartSelected() {
  apiError.value = ''
  try {
    const operation = await restartRuntimeControl({
      environment: restartTarget.environment,
      component: restartTarget.component,
      reason: actionForm.reason,
      prodConfirmText: actionForm.prodConfirmText || undefined
    })
    operations.value = [operation, ...operations.value]
  } catch (error) {
    apiError.value = error instanceof Error ? error.message : String(error)
  }
}

async function showOperationLog(row: RuntimeControlOperationVO) {
  operationLogLoading.value = true
  operationLogLoadingId.value = row.operationId
  apiError.value = ''
  operationLogDialogVisible.value = true
  operationLog.value = undefined
  try {
    operationLog.value = await getRuntimeControlOperationLog(row.operationId)
  } catch (error) {
    apiError.value = error instanceof Error ? error.message : String(error)
  } finally {
    operationLogLoading.value = false
    operationLogLoadingId.value = ''
  }
}

onMounted(loadData)
</script>

<template>
  <main class="console-shell">
    <header class="console-header">
      <div class="console-title-block">
        <p class="eyebrow">本机运维台 · 127.0.0.1:48181</p>
        <h1>运行控制台</h1>
        <p class="console-subtitle">local-operator</p>
      </div>
      <div class="console-header-actions">
        <span class="status-pill" :class="statusClass(capacityStatus || 'UNKNOWN')">
          <span class="status-dot" />
          容量 {{ capacityStatus || 'UNKNOWN' }}
        </span>
        <el-button class="console-refresh" :icon="Refresh" :loading="loading" @click="loadData">
          刷新
        </el-button>
      </div>
    </header>

    <section class="status-summary-grid" aria-label="运行摘要">
      <article
        v-for="item in statusSummary"
        :key="item.label"
        class="summary-card"
        :class="toneClass(item.tone)"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <el-alert
      v-if="apiError"
      class="console-alert"
      :title="apiError"
      type="error"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="releaseError"
      class="console-alert"
      :title="`发布包接口返回：${releaseError}`"
      type="warning"
      show-icon
      :closable="false"
    />

    <section class="workbench-grid">
      <section class="control-surface status-surface">
        <div class="surface-head">
          <div class="section-title">
            <el-icon><CircleCheck /></el-icon>
            <span>实例状态</span>
          </div>
          <span class="surface-meta">{{ flattenedStatuses.length }} 项</span>
        </div>

        <div v-if="loading" class="skeleton-table" aria-label="实例状态加载中">
          <div v-for="index in 5" :key="index" class="skeleton-row">
            <span class="skeleton-line skeleton-line--short" />
            <span class="skeleton-line" />
            <span class="skeleton-line skeleton-line--tiny" />
          </div>
        </div>
        <el-table
          v-else
          class="console-table"
          :data="flattenedStatuses"
          size="small"
          height="350"
          empty-text="暂无状态"
        >
          <el-table-column prop="environment" label="环境" width="92" />
          <el-table-column prop="component" label="组件" min-width="160" show-overflow-tooltip />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="httpStatus" label="HTTP" width="82" />
          <el-table-column prop="url" label="地址" min-width="230" show-overflow-tooltip />
          <el-table-column label="动作" width="88" align="center">
            <template #default="{ row }">
              <el-tooltip :content="row.blockedReason || '可提交重启请求'" placement="top">
                <el-button
                  class="table-icon-button"
                  :icon="VideoPlay"
                  size="small"
                  :disabled="!row.actionEnabled"
                  @click="
                    restartTarget.environment = row.environment;
                    restartTarget.component = row.component;
                    restartSelected()
                  "
                />
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="control-surface action-surface">
        <div class="surface-head">
          <div class="section-title">
            <el-icon><Monitor /></el-icon>
            <span>运维动作</span>
          </div>
          <span class="surface-meta">{{ actionLevelLabel(selectedAction.level) }}</span>
        </div>

        <div class="command-summary">
          <div>
            <span>当前动作</span>
            <strong>{{ selectedAction.label }}</strong>
          </div>
          <p>{{ selectedActionSummary }}</p>
        </div>

        <div class="action-choice-grid" role="radiogroup" aria-label="运维动作">
          <button
            v-for="item in actions"
            :key="item.action"
            type="button"
            class="action-choice"
            :class="{ 'is-active': item.action === selectedActionKey }"
            role="radio"
            :aria-checked="item.action === selectedActionKey"
            @click="handleActionChange(item.action)"
          >
            {{ item.label }}
          </button>
        </div>

        <el-form label-position="top" class="action-form">
          <el-form-item label="操作原因">
            <el-input v-model="actionForm.reason" type="textarea" :rows="3" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item v-if="operationRequiresTargetEnvironment(selectedAction.action)" label="目标环境">
              <el-select v-model="actionForm.targetEnvironment">
                <el-option label="测试服" value="test" />
                <el-option label="正式服" value="prod" />
                <el-option label="备份服" value="backup" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="operationSupportsPublishScope(selectedAction.action)" label="发布范围">
              <el-select v-model="actionForm.publishScope">
                <el-option label="仅代码" value="code-only" />
                <el-option label="含数据" value="with-data" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="selectedAction.action === 'backup-now'" label="备份类型">
              <el-segmented
                v-model="actionForm.backupKind"
                :options="[
                  { label: '全量', value: 'FULL' },
                  { label: '增量', value: 'INCREMENTAL' }
                ]"
              />
            </el-form-item>
            <el-form-item v-if="operationUsesReleaseTag(selectedAction.action)" label="发布标签">
              <el-input v-model="actionForm.releaseTag" placeholder="release-YYYYMMDD-HHmm" />
            </el-form-item>
            <el-form-item :label="prodConfirmLabel">
              <el-input v-model="actionForm.prodConfirmText" :placeholder="prodConfirmPlaceholder" />
            </el-form-item>
            <el-form-item v-if="operationUsesSqlPath(selectedAction.action)" label="SQL 路径">
              <el-input v-model="actionForm.sqlPath" />
            </el-form-item>
            <el-form-item v-if="operationUsesTestConclusion(selectedAction.action)" label="验证结论">
              <el-input v-model="actionForm.testConclusion" />
            </el-form-item>
            <el-form-item v-if="operationUsesImageCandidate(selectedAction.action)" label="镜像候选">
              <el-select
                v-model="actionForm.selectedImageCandidateId"
                filterable
                placeholder="选择可用回滚候选"
              >
                <el-option
                  v-for="item in rollbackCandidates"
                  :key="item.candidateId"
                  :label="`${item.imageTag || item.candidateId} · ${item.status}`"
                  :value="item.candidateId"
                  :disabled="item.status !== 'AVAILABLE'"
                />
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="operationUsesRecoverySetCandidate(selectedAction.action)"
              label="恢复集候选"
            >
              <el-select
                v-model="actionForm.selectedRecoverySetCandidateId"
                filterable
                placeholder="选择可恢复备份点"
              >
                <el-option
                  v-for="item in restoreCandidates"
                  :key="item.candidateId"
                  :label="`${item.backupId || item.candidateId} · ${item.status}`"
                  :value="item.candidateId"
                  :disabled="item.status !== 'AVAILABLE'"
                />
              </el-select>
            </el-form-item>
          </div>
          <div class="switch-row">
            <el-checkbox
              v-if="operationSupportsPublishScope(selectedAction.action)"
              v-model="actionForm.includeOnlyOffice"
            >
              包含 OnlyOffice
            </el-checkbox>
            <el-checkbox
              v-if="operationSupportsPublishScope(selectedAction.action)"
              v-model="actionForm.includeShowroomBuildPackage"
            >
              包含展厅包
            </el-checkbox>
            <el-checkbox
              v-if="operationSupportsSmartReleaseReport(selectedAction.action)"
              v-model="actionForm.enableSmartReleaseReport"
            >
              智能发布报告
            </el-checkbox>
          </div>
          <div class="command-row">
            <el-button
              class="primary-command"
              :icon="Search"
              :loading="previewLoading"
              :type="actionButtonType(selectedAction.level)"
              @click="previewAction"
            >
              预览命令
            </el-button>
          </div>
        </el-form>
      </section>
    </section>

    <section class="control-surface operation-table-shell">
      <div class="surface-head">
        <div class="section-title">
          <el-icon><Warning /></el-icon>
          <span>操作记录</span>
        </div>
        <div v-if="latestOperation" class="latest-operation">
          <span class="status-pill" :class="statusClass(latestOperation.status)">
            {{ latestOperation.status }}
          </span>
          <span>{{ latestOperation.actionLabel }}</span>
        </div>
      </div>
      <div v-if="loading" class="skeleton-table" aria-label="操作记录加载中">
        <div v-for="index in 4" :key="index" class="skeleton-row">
          <span class="skeleton-line" />
          <span class="skeleton-line skeleton-line--short" />
          <span class="skeleton-line skeleton-line--tiny" />
        </div>
      </div>
      <el-table v-else class="console-table" :data="operations" size="small" empty-text="暂无操作记录">
        <el-table-column prop="operationId" label="编号" min-width="240" show-overflow-tooltip />
        <el-table-column prop="requestedBy" label="操作者" width="126" />
        <el-table-column prop="environment" label="环境" width="92" />
        <el-table-column prop="actionLabel" label="动作" width="150" />
        <el-table-column label="状态" width="112">
          <template #default="{ row }">
            <span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="结果" min-width="230" show-overflow-tooltip />
        <el-table-column label="日志" width="82" align="center">
          <template #default="{ row }">
            <el-tooltip content="查看操作日志" placement="top">
              <el-button
                class="table-icon-button"
                :icon="Document"
                size="small"
                :loading="operationLogLoading && operationLogLoadingId === row.operationId"
                @click="showOperationLog(row)"
              />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="previewDialogVisible" class="preview-dialog" title="命令预览" width="760px">
      <div v-if="preview" class="preview-box">
        <p>{{ preview.summary }}</p>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="动作">{{ preview.actionLabel }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ preview.environment }}</el-descriptions-item>
          <el-descriptions-item label="脚本" :span="2">{{ preview.scriptPath }}</el-descriptions-item>
          <el-descriptions-item label="参数" :span="2">
            <code class="preview-command-code">{{ preview.arguments.join(' ') }}</code>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
        <el-button type="danger" :loading="previewLoading" @click="executeAction">执行</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="operationLogDialogVisible"
      class="operation-log-dialog"
      title="操作日志"
      width="860px"
    >
      <div v-loading="operationLogLoading" class="operation-log-panel">
        <template v-if="operationLog">
          <div class="operation-log-meta">
            <span class="status-pill" :class="statusClass(operationLog.status)">
              {{ operationLog.status }}
            </span>
            <span>{{ operationLog.operationId }}</span>
            <span>{{ operationLog.length }} bytes</span>
            <span v-if="operationLog.truncated">已截断</span>
          </div>
          <pre class="operation-log-content">{{ operationLog.content || '日志文件暂无内容' }}</pre>
        </template>
      </div>
    </el-dialog>

    <el-dialog
      v-model="releaseNotesDialogVisible"
      class="release-notes-dialog"
      title="版本变更说明"
      width="640px"
    >
      <section v-if="selectedReleaseNotes" class="release-notes-content">
        <div class="release-notes-version">
          <span>版本号</span>
          <strong>{{ selectedReleaseNotes.releaseTag }}</strong>
        </div>
        <div class="release-notes-section">
          <span class="release-notes-section-title">变更说明</span>
          <ul v-if="selectedReleaseNotesDisplayChanges.length" class="release-notes-list">
            <li v-for="change in selectedReleaseNotesDisplayChanges" :key="change">{{ change }}</li>
          </ul>
          <p v-else class="release-notes-empty">该版本未写入变更说明</p>
        </div>
      </section>
    </el-dialog>

    <footer class="console-version-dock" aria-label="版本信息">
      <div
        v-for="item in runtimeVersionItems"
        :key="item.label"
        class="console-version-item"
        :class="`console-version-item--${item.tone}`"
      >
        <div class="console-version-copy">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
        <el-button
          v-if="item.notes"
          class="console-version-change-button"
          size="small"
          link
          :icon="Document"
          @click="openReleaseNotes(item)"
        >
          查看变更
        </el-button>
      </div>
    </footer>
  </main>
</template>
