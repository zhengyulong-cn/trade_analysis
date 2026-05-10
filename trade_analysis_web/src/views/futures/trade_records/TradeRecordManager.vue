<script lang="ts" setup>
import {
  createTradeRecordApi,
  deleteTradeRecordApi,
  getFutureContractList,
  getTradeRecordListApi,
  resolveTradeRecordScreenshotUrl,
  updateTradeRecordApi,
  uploadTradeRecordScreenshotApi,
  type FutureContract,
  type TradeRecord,
  type TradeRecordCreateParams,
  type TradeRecordScreenshotUploadResult,
  type TradeRecordSegmentType,
  type TradeRecordUpdateParams,
} from '@/api/modules'
import { formatDateTime } from '@/utils/date'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
  type UploadFile,
  type UploadProps,
  type UploadRequestOptions,
} from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

interface TradeRecordFilters {
  contract: string
  segment_type: '' | TradeRecordSegmentType
  open_time_range: string[]
  close_time_range: string[]
}

interface TradeRecordForm {
  trade_record_id?: number
  contract: string
  lots: number
  open_time: string
  open_price: number
  close_time: string
  close_price: number
  segment_type: TradeRecordSegmentType
  actual_pnl: number
  screenshot_path: string | null
  screenshot_original_name: string | null
  screenshot_content_type: string | null
  screenshot_size: number | null
  comment: string
  remove_screenshot: boolean
}

const SEGMENT_PUSH = '\u8d8b\u52bf\u63a8\u52a8\u6bb5' as const
const SEGMENT_PULLBACK = '\u8d8b\u52bf\u56de\u8c03\u6bb5' as const
const SEGMENT_RANGE = '\u533a\u95f4\u5185\u90e8\u6bb5' as const

const segmentTypeOptions: Array<{ label: TradeRecordSegmentType; value: TradeRecordSegmentType }> = [
  { label: SEGMENT_PUSH, value: SEGMENT_PUSH },
  { label: SEGMENT_PULLBACK, value: SEGMENT_PULLBACK },
  { label: SEGMENT_RANGE, value: SEGMENT_RANGE },
]

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const contracts = ref<FutureContract[]>([])
const records = ref<TradeRecord[]>([])
const uploadFileList = ref<UploadFile[]>([])

const filters = reactive<TradeRecordFilters>({
  contract: '',
  segment_type: '',
  open_time_range: [],
  close_time_range: [],
})

const form = reactive<TradeRecordForm>({
  contract: '',
  lots: 1,
  open_time: '',
  open_price: 0,
  close_time: '',
  close_price: 0,
  segment_type: SEGMENT_PUSH,
  actual_pnl: 0,
  screenshot_path: null,
  screenshot_original_name: null,
  screenshot_content_type: null,
  screenshot_size: null,
  comment: '',
  remove_screenshot: false,
})

const rules = reactive<FormRules<TradeRecordForm>>({
  contract: [{ required: true, message: '\u8bf7\u8f93\u5165\u5408\u7ea6', trigger: 'blur' }],
  lots: [{ required: true, message: '\u8bf7\u8f93\u5165\u624b\u6570', trigger: 'change' }],
  open_time: [{ required: true, message: '\u8bf7\u9009\u62e9\u5f00\u4ed3\u65f6\u95f4', trigger: 'change' }],
  open_price: [{ required: true, message: '\u8bf7\u8f93\u5165\u5f00\u4ed3\u4ef7\u683c', trigger: 'change' }],
  close_time: [{ required: true, message: '\u8bf7\u9009\u62e9\u5e73\u4ed3\u65f6\u95f4', trigger: 'change' }],
  close_price: [{ required: true, message: '\u8bf7\u8f93\u5165\u5e73\u4ed3\u4ef7\u683c', trigger: 'change' }],
  segment_type: [{ required: true, message: '\u8bf7\u9009\u62e930F\u7ebf\u6bb5\u7c7b\u578b', trigger: 'change' }],
  actual_pnl: [{ required: true, message: '\u8bf7\u8f93\u5165\u5b9e\u9645\u76c8\u4e8f', trigger: 'change' }],
})

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '\u65b0\u589e\u4ea4\u6613\u8bb0\u5f55' : '\u4fee\u6539\u4ea4\u6613\u8bb0\u5f55',
)

const resetForm = () => {
  form.trade_record_id = undefined
  form.contract = ''
  form.lots = 1
  form.open_time = ''
  form.open_price = 0
  form.close_time = ''
  form.close_price = 0
  form.segment_type = SEGMENT_PUSH
  form.actual_pnl = 0
  form.screenshot_path = null
  form.screenshot_original_name = null
  form.screenshot_content_type = null
  form.screenshot_size = null
  form.comment = ''
  form.remove_screenshot = false
  uploadFileList.value = []
  formRef.value?.clearValidate()
}

const buildListParams = () => {
  return {
    contract: filters.contract.trim() || undefined,
    segment_type: filters.segment_type || undefined,
    open_time_start: filters.open_time_range[0] || undefined,
    open_time_end: filters.open_time_range[1] || undefined,
    close_time_start: filters.close_time_range[0] || undefined,
    close_time_end: filters.close_time_range[1] || undefined,
  }
}

const loadTradeRecords = async () => {
  loading.value = true
  try {
    records.value = await getTradeRecordListApi(buildListParams())
  } catch {
    ElMessage.error('\u83b7\u53d6\u4ea4\u6613\u8bb0\u5f55\u5931\u8d25')
  } finally {
    loading.value = false
  }
}

const loadContracts = async () => {
  try {
    contracts.value = await getFutureContractList()
  } catch {
    ElMessage.error('\u83b7\u53d6\u5408\u7ea6\u5217\u8868\u5931\u8d25')
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (record: TradeRecord) => {
  dialogMode.value = 'edit'
  form.trade_record_id = record.trade_record_id
  form.contract = record.contract
  form.lots = record.lots
  form.open_time = record.open_time
  form.open_price = Number(record.open_price)
  form.close_time = record.close_time
  form.close_price = Number(record.close_price)
  form.segment_type = record.segment_type
  form.actual_pnl = Number(record.actual_pnl)
  form.screenshot_path = record.screenshot_path
  form.screenshot_original_name = record.screenshot_original_name
  form.screenshot_content_type = record.screenshot_content_type
  form.screenshot_size = record.screenshot_size
  form.comment = record.comment ?? ''
  form.remove_screenshot = false
  uploadFileList.value = record.screenshot_path
    ? [
        {
          name: record.screenshot_original_name || '\u64cd\u4f5c\u622a\u56fe',
          url: resolveTradeRecordScreenshotUrl(record.screenshot_path),
          status: 'success',
        },
      ]
    : []
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

const buildPayload = (): TradeRecordCreateParams => {
  return {
    contract: form.contract.trim(),
    lots: form.lots,
    open_time: form.open_time,
    open_price: form.open_price,
    close_time: form.close_time,
    close_price: form.close_price,
    segment_type: form.segment_type,
    actual_pnl: form.actual_pnl,
    screenshot_path: form.screenshot_path,
    screenshot_original_name: form.screenshot_original_name,
    screenshot_content_type: form.screenshot_content_type,
    screenshot_size: form.screenshot_size,
    comment: form.comment.trim() || null,
  }
}

const submitForm = async () => {
  if (!formRef.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (new Date(form.close_time).getTime() < new Date(form.open_time).getTime()) {
    ElMessage.error('\u5e73\u4ed3\u65f6\u95f4\u4e0d\u80fd\u65e9\u4e8e\u5f00\u4ed3\u65f6\u95f4')
    return
  }

  submitting.value = true
  try {
    const payload = buildPayload()
    if (dialogMode.value === 'create') {
      await createTradeRecordApi(payload)
      ElMessage.success('\u65b0\u589e\u4ea4\u6613\u8bb0\u5f55\u6210\u529f')
    } else if (form.trade_record_id) {
      const updatePayload: TradeRecordUpdateParams = {
        trade_record_id: form.trade_record_id,
        ...payload,
        remove_screenshot: form.remove_screenshot,
      }
      await updateTradeRecordApi(updatePayload)
      ElMessage.success('\u4fee\u6539\u4ea4\u6613\u8bb0\u5f55\u6210\u529f')
    }
    dialogVisible.value = false
    await loadTradeRecords()
  } catch {
    ElMessage.error(
      dialogMode.value === 'create'
        ? '\u65b0\u589e\u4ea4\u6613\u8bb0\u5f55\u5931\u8d25'
        : '\u4fee\u6539\u4ea4\u6613\u8bb0\u5f55\u5931\u8d25',
    )
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (record: TradeRecord) => {
  try {
    await ElMessageBox.confirm(
      `\u786e\u8ba4\u5220\u9664 ${record.contract} \u7684\u8fd9\u6761\u4ea4\u6613\u8bb0\u5f55\u5417\uff1f`,
      '\u5220\u9664\u786e\u8ba4',
      {
        type: 'warning',
      },
    )
    await deleteTradeRecordApi(record.trade_record_id)
    ElMessage.success('\u5220\u9664\u4ea4\u6613\u8bb0\u5f55\u6210\u529f')
    await loadTradeRecords()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error('\u5220\u9664\u4ea4\u6613\u8bb0\u5f55\u5931\u8d25')
  }
}

const applyUploadedScreenshot = (result: TradeRecordScreenshotUploadResult) => {
  form.screenshot_path = result.path
  form.screenshot_original_name = result.original_name
  form.screenshot_content_type = result.content_type
  form.screenshot_size = result.size
  form.remove_screenshot = false
  uploadFileList.value = [
    {
      name: result.original_name,
      url: result.url,
      status: 'success',
    },
  ]
}

const handleUploadRequest = async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeRecordScreenshotApi(options.file)
    applyUploadedScreenshot(result)
    options.onSuccess?.(result)
    ElMessage.success('\u622a\u56fe\u4e0a\u4f20\u6210\u529f')
  } catch (error) {
    options.onError?.(error as Error)
    ElMessage.error('\u622a\u56fe\u4e0a\u4f20\u5931\u8d25')
  }
}

const beforeScreenshotUpload: UploadProps['beforeUpload'] = (rawFile) => {
  const isImage = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error('\u4ec5\u652f\u6301 JPG\u3001PNG\u3001WEBP\u3001GIF \u56fe\u7247')
    return false
  }

  const isLt10Mb = rawFile.size / 1024 / 1024 < 10
  if (!isLt10Mb) {
    ElMessage.error('\u56fe\u7247\u5927\u5c0f\u4e0d\u80fd\u8d85\u8fc7 10MB')
    return false
  }

  return true
}

const handleUploadRemove = () => {
  uploadFileList.value = []
  form.screenshot_path = null
  form.screenshot_original_name = null
  form.screenshot_content_type = null
  form.screenshot_size = null
  form.remove_screenshot = true
}

const formatCurrency = (value?: number | string | null, fractionDigits = 2) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

const handleSearch = async () => {
  await loadTradeRecords()
}

const handleResetFilters = async () => {
  filters.contract = ''
  filters.segment_type = ''
  filters.open_time_range = []
  filters.close_time_range = []
  await loadTradeRecords()
}

onMounted(() => {
  void loadContracts()
  void loadTradeRecords()
})
</script>

<template>
  <div class="pageBox trade-record-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">{{ '\u4ea4\u6613\u8bb0\u5f55' }}</h2>
        <p class="subtitle">{{ '\u7ef4\u62a4\u4ea4\u6613\u8bb0\u5f55\u3001\u76c8\u4e8f\u590d\u76d8\u548c\u64cd\u4f5c\u622a\u56fe' }}</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">{{ '\u65b0\u589e\u4ea4\u6613\u8bb0\u5f55' }}</el-button>
    </div>

    <div class="filter-card">
        <el-form :inline="true" class="filter-form">
        <el-form-item :label="'\u5408\u7ea6'">
          <el-select
            v-model="filters.contract"
            filterable
            clearable
            :placeholder="'\u8bf7\u9009\u62e9\u5408\u7ea6'"
            style="width: 180px"
          >
            <el-option
              v-for="contractItem in contracts"
              :key="contractItem.contract_id"
              :label="contractItem.symbol"
              :value="contractItem.symbol"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="'30F\u7ebf\u6bb5\u7c7b\u578b'">
          <el-select v-model="filters.segment_type" :placeholder="'\u5168\u90e8'" clearable style="width: 180px">
            <el-option
              v-for="option in segmentTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="'\u5f00\u4ed3\u65f6\u95f4'">
          <el-date-picker
            v-model="filters.open_time_range"
            type="datetimerange"
            :range-separator="'\u81f3'"
            :start-placeholder="'\u5f00\u59cb\u65f6\u95f4'"
            :end-placeholder="'\u7ed3\u675f\u65f6\u95f4'"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item :label="'\u5e73\u4ed3\u65f6\u95f4'">
          <el-date-picker
            v-model="filters.close_time_range"
            type="datetimerange"
            :range-separator="'\u81f3'"
            :start-placeholder="'\u5f00\u59cb\u65f6\u95f4'"
            :end-placeholder="'\u7ed3\u675f\u65f6\u95f4'"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">{{ '\u67e5\u8be2' }}</el-button>
          <el-button @click="handleResetFilters">{{ '\u91cd\u7f6e' }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      v-loading="loading"
      :data="records"
      border
      row-key="trade_record_id"
      :empty-text="'\u6682\u65e0\u4ea4\u6613\u8bb0\u5f55'"
    >
      <el-table-column prop="trade_record_id" label="ID" width="80" />
      <el-table-column prop="contract" :label="'\u5408\u7ea6'" min-width="120" />
      <el-table-column prop="lots" :label="'\u624b\u6570'" width="90" />
      <el-table-column prop="open_time" :label="'\u5f00\u4ed3\u65f6\u95f4'" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.open_time) }}</template>
      </el-table-column>
      <el-table-column prop="open_price" :label="'\u5f00\u4ed3\u4ef7\u683c'" min-width="120" align="right">
        <template #default="{ row }">{{ formatCurrency(row.open_price, 1) }}</template>
      </el-table-column>
      <el-table-column prop="close_time" :label="'\u5e73\u4ed3\u65f6\u95f4'" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.close_time) }}</template>
      </el-table-column>
      <el-table-column prop="close_price" :label="'\u5e73\u4ed3\u4ef7\u683c'" min-width="120" align="right">
        <template #default="{ row }">{{ formatCurrency(row.close_price, 1) }}</template>
      </el-table-column>
      <el-table-column prop="segment_type" :label="'30F\u7ebf\u6bb5\u7c7b\u578b'" min-width="140" />
      <el-table-column prop="actual_pnl" :label="'\u5b9e\u9645\u76c8\u4e8f'" min-width="120" align="right">
        <template #default="{ row }">
          <span :class="Number(row.actual_pnl) >= 0 ? 'pnl-positive' : 'pnl-negative'">
            {{ formatCurrency(row.actual_pnl) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column :label="'\u64cd\u4f5c\u622a\u56fe'" min-width="130" align="center">
        <template #default="{ row }">
          <el-image
            v-if="row.screenshot_path"
            :src="resolveTradeRecordScreenshotUrl(row.screenshot_path)"
            :preview-src-list="[resolveTradeRecordScreenshotUrl(row.screenshot_path)]"
            preview-teleported
            fit="cover"
            class="screenshot-thumb"
          />
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="comment" :label="'\u64cd\u4f5c\u8bc4\u4ef7'" min-width="220" show-overflow-tooltip />
      <el-table-column prop="updated_at" :label="'\u66f4\u65b0\u65f6\u95f4'" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column :label="'\u64cd\u4f5c'" fixed="right" width="140">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">{{ '\u4fee\u6539' }}</el-button>
          <el-button type="danger" link @click="handleDelete(row)">{{ '\u5220\u9664' }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="48rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="8rem" class="trade-form">
        <div class="form-grid">
          <el-form-item :label="'\u5408\u7ea6'" prop="contract">
            <el-select
              v-model="form.contract"
              filterable
              :placeholder="'\u8bf7\u9009\u62e9\u5408\u7ea6'"
              style="width: 100%"
            >
              <el-option
                v-for="contractItem in contracts"
                :key="contractItem.contract_id"
                :label="contractItem.symbol"
                :value="contractItem.symbol"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="'\u624b\u6570'" prop="lots">
            <el-input-number v-model="form.lots" :min="1" :step="1" :precision="0" style="width: 100%" />
          </el-form-item>
          <el-form-item :label="'\u5f00\u4ed3\u65f6\u95f4'" prop="open_time">
            <el-date-picker
              v-model="form.open_time"
              type="datetime"
              :placeholder="'\u8bf7\u9009\u62e9\u5f00\u4ed3\u65f6\u95f4'"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item :label="'\u5f00\u4ed3\u4ef7\u683c'" prop="open_price">
            <el-input-number v-model="form.open_price" :min="0" :precision="1" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item :label="'\u5e73\u4ed3\u65f6\u95f4'" prop="close_time">
            <el-date-picker
              v-model="form.close_time"
              type="datetime"
              :placeholder="'\u8bf7\u9009\u62e9\u5e73\u4ed3\u65f6\u95f4'"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item :label="'\u5e73\u4ed3\u4ef7\u683c'" prop="close_price">
            <el-input-number v-model="form.close_price" :min="0" :precision="1" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item :label="'30F\u7ebf\u6bb5\u7c7b\u578b'" prop="segment_type">
            <el-select v-model="form.segment_type" :placeholder="'\u8bf7\u9009\u62e930F\u7ebf\u6bb5\u7c7b\u578b'" style="width: 100%">
              <el-option
                v-for="option in segmentTypeOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="'\u5b9e\u9645\u76c8\u4e8f'" prop="actual_pnl">
            <el-input-number v-model="form.actual_pnl" :precision="2" :step="1" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item :label="'\u64cd\u4f5c\u622a\u56fe'">
          <el-upload
            :file-list="uploadFileList"
            :limit="1"
            list-type="picture-card"
            accept=".jpg,.jpeg,.png,.webp,.gif"
            :auto-upload="true"
            :before-upload="beforeScreenshotUpload"
            :http-request="handleUploadRequest"
            :on-remove="handleUploadRemove"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>

        <el-form-item :label="'\u64cd\u4f5c\u8bc4\u4ef7'">
          <el-input
            v-model="form.comment"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            :placeholder="'\u8bf7\u8f93\u5165\u64cd\u4f5c\u8bc4\u4ef7'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ '\u53d6\u6d88' }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">{{ '\u786e\u8ba4' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="less" scoped>
.trade-record-manager {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.filter-card {
  margin-bottom: 16px;
  padding: 16px 16px 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
}

.trade-form {
  padding-right: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.screenshot-thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
}

.empty-text {
  color: #c0c4cc;
}

.pnl-positive {
  color: #f56c6c;
  font-weight: 600;
}

.pnl-negative {
  color: #67c23a;
  font-weight: 600;
}

@media (max-width: 960px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
