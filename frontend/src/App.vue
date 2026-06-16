<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CircleCheck,
  Monitor,
  Refresh,
  Search,
  Warning,
  VideoPlay
} from '@element-plus/icons-vue'
import {
  executeRuntimeControlAction,
  getRuntimeControlCapacityStatus,
  getRuntimeControlOperations,
  getRuntimeControlOverview,
  getRuntimeControlReleaseStatus,
  previewRuntimeControlAction,
  restartRuntimeControl,
  type RuntimeControlActionPreviewVO,
  type RuntimeControlOperationVO,
  type RuntimeControlOverviewVO,
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
  { action: 'mark-release-tested', label: '标记测试通过', level: 'normal', targetEnvironment: 'test' },
  { action: 'promote-prod', label: '上线正式服', level: 'danger', targetEnvironment: 'prod' },
  { action: 'promote-backup', label: '上线备份服', level: 'warning', targetEnvironment: 'backup' },
  { action: 'backup-now', label: '立即备份', level: 'warning', targetEnvironment: 'prod' },
  { action: 'rollback-app', label: '回滚应用', level: 'danger', targetEnvironment: 'prod' },
  { action: 'restore-data', label: '恢复数据', level: 'danger', targetEnvironment: 'prod' },
  { action: 'rehearsal', label: '恢复演练', level: 'normal', targetEnvironment: 'test' }
]

const overview = ref<RuntimeControlOverviewVO>()
const operations = ref<RuntimeControlOperationVO[]>([])
const releaseError = ref('')
const apiError = ref('')
const loading = ref(false)
const previewLoading = ref(false)
const previewDialogVisible = ref(false)
const preview = ref<RuntimeControlActionPreviewVO>()
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
  sqlPath: '',
  selectedImageCandidateId: '',
  selectedImageTag: '',
  selectedRecoverySetCandidateId: '',
  selectedBackupId: '',
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

const selectedStatus = computed(() => {
  return overview.value?.statuses?.[restartTarget.environment]?.[restartTarget.component]
})

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

function handleActionChange(value: string | number | boolean) {
  selectedActionKey.value = String(value)
  actionForm.targetEnvironment = selectedAction.value.targetEnvironment || 'test'
  actionForm.publishScope = selectedAction.value.publishScope || actionForm.publishScope
}

function requestPayload() {
  return {
    action: selectedAction.value.action,
    reason: actionForm.reason,
    prodConfirmText: actionForm.prodConfirmText || undefined,
    targetEnvironment:
      selectedAction.value.action === 'build-release'
        ? undefined
        : actionForm.targetEnvironment || selectedAction.value.targetEnvironment,
    publishScope:
      selectedAction.value.action === 'build-release' ? actionForm.publishScope : undefined,
    includeOnlyOffice: actionForm.includeOnlyOffice,
    includeShowroomBuildPackage: actionForm.includeShowroomBuildPackage,
    enableSmartReleaseReport: actionForm.enableSmartReleaseReport,
    releaseTag: actionForm.releaseTag || undefined,
    sqlPath: actionForm.sqlPath || undefined,
    selectedImageCandidateId: actionForm.selectedImageCandidateId || undefined,
    selectedImageTag: actionForm.selectedImageTag || undefined,
    selectedRecoverySetCandidateId: actionForm.selectedRecoverySetCandidateId || undefined,
    selectedBackupId: actionForm.selectedBackupId || undefined,
    testConclusion: '独立控制台验证记录'
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
  try {
    await getRuntimeControlReleaseStatus()
  } catch (error) {
    releaseError.value = error instanceof Error ? error.message : String(error)
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

onMounted(loadData)
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">127.0.0.1:48181</p>
        <h1>运行控制台</h1>
      </div>
      <div class="toolbar">
        <el-tag :type="statusType(capacityStatus || 'UNKNOWN')" effect="plain">
          容量 {{ capacityStatus || 'UNKNOWN' }}
        </el-tag>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
      </div>
    </header>

    <el-alert
      v-if="apiError"
      class="alert"
      :title="apiError"
      type="error"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="releaseError"
      class="alert"
      :title="`发布包接口返回：${releaseError}`"
      type="warning"
      show-icon
      :closable="false"
    />

    <section class="layout">
      <div class="panel status-panel">
        <div class="section-title">
          <el-icon><CircleCheck /></el-icon>
          <span>实例状态</span>
        </div>
        <el-table :data="flattenedStatuses" size="small" height="340" empty-text="暂无状态">
          <el-table-column prop="environment" label="环境" width="92" />
          <el-table-column prop="component" label="组件" min-width="150" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" effect="plain">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="httpStatus" label="HTTP" width="82" />
          <el-table-column prop="url" label="地址" min-width="220" show-overflow-tooltip />
          <el-table-column label="动作" width="104">
            <template #default="{ row }">
              <el-tooltip :content="row.blockedReason || '可提交重启请求'" placement="top">
                <el-button
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
      </div>

      <div class="panel action-panel">
        <div class="section-title">
          <el-icon><Monitor /></el-icon>
          <span>运维动作</span>
        </div>
        <el-segmented
          v-model="selectedActionKey"
          class="action-segment"
          :options="actions"
          :props="{ label: 'label', value: 'action' }"
          @change="handleActionChange"
        />

        <el-form label-position="top" class="action-form">
          <el-form-item label="操作原因">
            <el-input v-model="actionForm.reason" type="textarea" :rows="3" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="目标环境">
              <el-select v-model="actionForm.targetEnvironment">
                <el-option label="测试服" value="test" />
                <el-option label="正式服" value="prod" />
                <el-option label="备份服" value="backup" />
              </el-select>
            </el-form-item>
            <el-form-item label="发布范围">
              <el-select v-model="actionForm.publishScope">
                <el-option label="仅代码" value="code-only" />
                <el-option label="含数据" value="with-data" />
              </el-select>
            </el-form-item>
            <el-form-item label="发布标签">
              <el-input v-model="actionForm.releaseTag" placeholder="release-YYYYMMDD-HHmm" />
            </el-form-item>
            <el-form-item label="生产确认">
              <el-input v-model="actionForm.prodConfirmText" placeholder="PROD" />
            </el-form-item>
            <el-form-item label="SQL 路径">
              <el-input v-model="actionForm.sqlPath" />
            </el-form-item>
            <el-form-item label="镜像标签">
              <el-input v-model="actionForm.selectedImageTag" />
            </el-form-item>
            <el-form-item label="镜像候选">
              <el-input v-model="actionForm.selectedImageCandidateId" />
            </el-form-item>
            <el-form-item label="备份点">
              <el-input v-model="actionForm.selectedBackupId" />
            </el-form-item>
            <el-form-item label="恢复集候选">
              <el-input v-model="actionForm.selectedRecoverySetCandidateId" />
            </el-form-item>
          </div>
          <div class="switch-row">
            <el-checkbox v-model="actionForm.includeOnlyOffice">包含 OnlyOffice</el-checkbox>
            <el-checkbox v-model="actionForm.includeShowroomBuildPackage">包含展厅包</el-checkbox>
            <el-checkbox v-model="actionForm.enableSmartReleaseReport">智能发布报告</el-checkbox>
          </div>
          <div class="command-row">
            <el-button
              :icon="Search"
              :loading="previewLoading"
              :type="actionButtonType(selectedAction.level)"
              @click="previewAction"
            >
              预览命令
            </el-button>
          </div>
        </el-form>
      </div>
    </section>

    <section class="panel operations">
      <div class="section-title">
        <el-icon><Warning /></el-icon>
        <span>操作记录</span>
      </div>
      <el-table :data="operations" size="small" empty-text="暂无操作记录">
        <el-table-column prop="operationId" label="编号" min-width="220" show-overflow-tooltip />
        <el-table-column prop="requestedBy" label="操作者" width="120" />
        <el-table-column prop="environment" label="环境" width="92" />
        <el-table-column prop="actionLabel" label="动作" width="150" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="summary" label="结果" min-width="220" show-overflow-tooltip />
      </el-table>
    </section>

    <el-dialog v-model="previewDialogVisible" title="命令预览" width="720px">
      <div v-if="preview" class="preview-box">
        <p>{{ preview.summary }}</p>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="动作">{{ preview.actionLabel }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ preview.environment }}</el-descriptions-item>
          <el-descriptions-item label="脚本" :span="2">{{ preview.scriptPath }}</el-descriptions-item>
          <el-descriptions-item label="参数" :span="2">
            <code>{{ preview.arguments.join(' ') }}</code>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
        <el-button type="danger" :loading="previewLoading" @click="executeAction">执行</el-button>
      </template>
    </el-dialog>
  </main>
</template>
