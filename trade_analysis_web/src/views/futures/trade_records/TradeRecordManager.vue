<script lang="ts" setup>
import {
  createTradeRecordApi,
  deleteTradeRecordApi,
  getFutureContractList,
  getTradeRecordListApi,
  importTradeRecordsApi,
  resolveTradeRecordScreenshotUrl,
  updateTradeRecordApi,
  uploadTradeRecordScreenshotApi,
  type FutureContract,
  type TradeRecord,
  type TradeRecordCreateParams,
  type TradeRecordOpenDirection,
  type TradeRecordScreenshot,
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
  type UploadRawFile,
  type UploadRequestOptions,
} from 'element-plus'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

interface TradeRecordFilters {
  contract: string
  open_direction: '' | TradeRecordOpenDirection
  segment_type: '' | TradeRecordSegmentType
  open_time_range: string[]
  close_time_range: string[]
}

interface TradeRecordForm {
  trade_record_id?: number
  contract: string
  open_direction: TradeRecordOpenDirection
  lots: number
  open_time: string
  open_price: number
  close_time: string
  close_price: number | null
  segment_type: TradeRecordSegmentType
  fee: number
  actual_pnl: number | null
  screenshots: TradeRecordScreenshot[]
  comment: string
}

const SEGMENT_PUSH = 'trend_push' as const
const SEGMENT_PULLBACK = 'trend_pullback' as const
const SEGMENT_RANGE = 'range_internal' as const
const OPEN_DIRECTION_LONG = 'long' as const
const OPEN_DIRECTION_SHORT = 'short' as const

const segmentTypeOptions: Array<{ label: string; value: TradeRecordSegmentType }> = [
  { label: '趋势推动段', value: SEGMENT_PUSH },
  { label: '趋势回调段', value: SEGMENT_PULLBACK },
  { label: '区间内部段', value: SEGMENT_RANGE },
]

const segmentTypeLabelMap: Record<TradeRecordSegmentType, string> = {
  trend_push: '趋势推动段',
  trend_pullback: '趋势回调段',
  range_internal: '区间内部段',
}

const openDirectionOptions: Array<{ label: string; value: TradeRecordOpenDirection }> = [
  { label: '多单', value: OPEN_DIRECTION_LONG },
  { label: '空单', value: OPEN_DIRECTION_SHORT },
]

const openDirectionLabelMap: Record<TradeRecordOpenDirection, string> = {
  long: '多单',
  short: '空单',
}

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const contracts = ref<FutureContract[]>([])
const records = ref<TradeRecord[]>([])
const uploadFileList = ref<UploadFile[]>([])

const filters = reactive<TradeRecordFilters>({
  contract: '',
  open_direction: '',
  segment_type: '',
  open_time_range: [],
  close_time_range: [],
})

const form = reactive<TradeRecordForm>({
  contract: '',
  open_direction: OPEN_DIRECTION_LONG,
  lots: 1,
  open_time: '',
  open_price: 0,
  close_time: '',
  close_price: null,
  segment_type: SEGMENT_PUSH,
  fee: 0,
  actual_pnl: null,
  screenshots: [],
  comment: '',
})

const rules = reactive<FormRules<TradeRecordForm>>({
  contract: [{ required: true, message: '请选择合约', trigger: 'change' }],
  open_direction: [{ required: true, message: '请选择开仓方向', trigger: 'change' }],
  lots: [{ required: true, message: '请输入手数', trigger: 'change' }],
  open_time: [{ required: true, message: '请选择开仓时间', trigger: 'change' }],
  open_price: [{ required: true, message: '请输入开仓价格', trigger: 'change' }],
  segment_type: [{ required: true, message: '请选择30F线段类型', trigger: 'change' }],
  fee: [{ required: true, message: '请输入手续费', trigger: 'change' }],
})

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增交易记录' : '修改交易记录'))

const disableFutureDateTime = (date: Date) => date.getTime() > Date.now()

const resetForm = () => {
  form.trade_record_id = undefined
  form.contract = ''
  form.open_direction = OPEN_DIRECTION_LONG
  form.lots = 1
  form.open_time = ''
  form.open_price = 0
  form.close_time = ''
  form.close_price = null
  form.segment_type = SEGMENT_PUSH
  form.fee = 0
  form.actual_pnl = null
  form.screenshots = []
  form.comment = ''
  uploadFileList.value = []
  formRef.value?.clearValidate()
}

const buildListParams = () => {
  return {
    contract: filters.contract.trim() || undefined,
    open_direction: filters.open_direction || undefined,
    segment_type: filters.segment_type || undefined,
    open_time_start: filters.open_time_range[0] || undefined,
    open_time_end: filters.open_time_range[1] || undefined,
    close_time_start: filters.close_time_range[0] || undefined,
    close_time_end: filters.close_time_range[1] || undefined,
  }
}

const toUploadFile = (screenshot: TradeRecordScreenshot): UploadFile => {
  const resolvedUrl = resolveTradeRecordScreenshotUrl(screenshot.path)
  return {
    name: screenshot.original_name,
    url: resolvedUrl,
    status: 'success',
    response: {
      ...screenshot,
      url: resolvedUrl,
    },
  }
}

const loadTradeRecords = async () => {
  loading.value = true
  try {
    records.value = await getTradeRecordListApi(buildListParams())
  } catch {
    ElMessage.error('获取交易记录失败')
  } finally {
    loading.value = false
  }
}

const loadContracts = async () => {
  try {
    contracts.value = await getFutureContractList()
  } catch {
    ElMessage.error('获取合约列表失败')
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
  form.open_direction = record.open_direction
  form.lots = record.lots
  form.open_time = record.open_time
  form.open_price = Number(record.open_price)
  form.close_time = record.close_time ?? ''
  form.close_price = record.close_price === null ? null : Number(record.close_price)
  form.segment_type = record.segment_type ?? SEGMENT_PUSH
  form.fee = Number(record.fee)
  form.actual_pnl = record.actual_pnl === null ? null : Number(record.actual_pnl)
  form.screenshots = [...record.screenshots]
  form.comment = record.comment ?? ''
  uploadFileList.value = record.screenshots.map(toUploadFile)
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

const buildPayload = (): TradeRecordCreateParams => {
  const hasCloseInfo = Boolean(form.close_time && form.close_price !== null)
  return {
    contract: form.contract.trim(),
    open_direction: form.open_direction,
    lots: form.lots,
    open_time: form.open_time,
    open_price: form.open_price,
    close_time: hasCloseInfo ? form.close_time : null,
    close_price: hasCloseInfo ? form.close_price : null,
    segment_type: form.segment_type,
    fee: form.fee,
    actual_pnl: form.actual_pnl,
    screenshots: [...form.screenshots],
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

  const hasCloseTime = Boolean(form.close_time)
  const hasClosePrice = form.close_price !== null
  if (hasCloseTime !== hasClosePrice) {
    ElMessage.error('平仓时间和平仓价格需要同时填写，或同时留空')
    return
  }
  if (hasCloseTime && new Date(form.close_time).getTime() < new Date(form.open_time).getTime()) {
    ElMessage.error('平仓时间不能早于开仓时间')
    return
  }

  submitting.value = true
  try {
    const payload = buildPayload()
    if (dialogMode.value === 'create') {
      await createTradeRecordApi(payload)
      ElMessage.success('新增交易记录成功')
    } else if (form.trade_record_id) {
      const updatePayload: TradeRecordUpdateParams = {
        trade_record_id: form.trade_record_id,
        ...payload,
      }
      await updateTradeRecordApi(updatePayload)
      ElMessage.success('修改交易记录成功')
    }
    dialogVisible.value = false
    await loadTradeRecords()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '新增交易记录失败' : '修改交易记录失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (record: TradeRecord) => {
  try {
    await ElMessageBox.confirm(`确认删除 ${record.contract} 的这条交易记录吗？`, '删除确认', {
      type: 'warning',
    })
    await deleteTradeRecordApi(record.trade_record_id)
    ElMessage.success('删除交易记录成功')
    await loadTradeRecords()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error('删除交易记录失败')
  }
}

const handleImportTradeRecords = async (options: UploadRequestOptions) => {
  importing.value = true
  try {
    const result = await importTradeRecordsApi(options.file)
    options.onSuccess?.(result)
    ElMessage.success(result.message)
    await loadTradeRecords()
  } catch (error) {
    options.onError?.(error as Error)
    ElMessage.error('上传交易记录失败')
  } finally {
    importing.value = false
  }
}

const applyUploadedScreenshot = (result: TradeRecordScreenshotUploadResult) => {
  form.screenshots = [
    ...form.screenshots,
    {
      path: result.path,
      original_name: result.original_name,
      content_type: result.content_type,
      size: result.size,
    },
  ]
  uploadFileList.value = [
    ...uploadFileList.value,
    {
      name: result.original_name,
      url: result.url,
      status: 'success',
      response: result,
    },
  ]
}

const validateScreenshotFile = (rawFile: Pick<UploadRawFile, 'type' | 'size'>) => {
  const isImage = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(rawFile.type)
  if (!isImage) {
    ElMessage.error('仅支持 JPG、PNG、WEBP、GIF 图片')
    return false
  }

  const isLt10Mb = rawFile.size / 1024 / 1024 < 10
  if (!isLt10Mb) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }

  return true
}

const handleUploadRequest = async (options: UploadRequestOptions) => {
  try {
    const result = await uploadTradeRecordScreenshotApi(options.file)
    applyUploadedScreenshot(result)
    options.onSuccess?.(result)
    ElMessage.success('截图上传成功')
  } catch (error) {
    options.onError?.(error as Error)
    ElMessage.error('截图上传失败')
  }
}

const beforeScreenshotUpload: UploadProps['beforeUpload'] = (rawFile) => validateScreenshotFile(rawFile)

const resolveUploadPath = (uploadFile: UploadFile) => {
  const response = uploadFile.response as TradeRecordScreenshotUploadResult | TradeRecordScreenshot | undefined
  if (response?.path) {
    return response.path
  }

  if (!uploadFile.url) {
    return ''
  }

  return uploadFile.url.replace(/^.*\/storage\//, '')
}

const handleUploadRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  const removedPath = resolveUploadPath(uploadFile)
  form.screenshots = form.screenshots.filter((item) => item.path !== removedPath)
  uploadFileList.value = uploadFiles
}

const handlePasteScreenshot = async (event: ClipboardEvent) => {
  if (!dialogVisible.value) {
    return
  }

  const items = Array.from(event.clipboardData?.items ?? [])
  const imageFiles = items
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null)

  if (!imageFiles.length) {
    return
  }

  event.preventDefault()

  for (const file of imageFiles) {
    if (!validateScreenshotFile(file)) {
      continue
    }

    try {
      const result = await uploadTradeRecordScreenshotApi(file)
      applyUploadedScreenshot(result)
      ElMessage.success('截图粘贴上传成功')
    } catch {
      ElMessage.error('截图粘贴上传失败')
    }
  }
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

const getPreviewScreenshotUrls = (screenshots: TradeRecordScreenshot[]) => {
  return screenshots.map((item) => resolveTradeRecordScreenshotUrl(item.path))
}

const formatSegmentType = (segmentType: TradeRecordSegmentType | null) => {
  if (!segmentType) {
    return '-'
  }
  return segmentTypeLabelMap[segmentType] ?? segmentType
}

const formatOpenDirection = (openDirection: TradeRecordOpenDirection) => {
  return openDirectionLabelMap[openDirection] ?? openDirection
}

const formatStatus = (record: TradeRecord) => {
  return record.close_time ? '已平仓' : '未平仓'
}

const handleSearch = async () => {
  await loadTradeRecords()
}

const handleResetFilters = async () => {
  filters.contract = ''
  filters.open_direction = ''
  filters.segment_type = ''
  filters.open_time_range = []
  filters.close_time_range = []
  await loadTradeRecords()
}

onMounted(() => {
  void loadContracts()
  void loadTradeRecords()
})

watch(dialogVisible, (visible) => {
  if (visible) {
    window.addEventListener('paste', handlePasteScreenshot)
    return
  }
  window.removeEventListener('paste', handlePasteScreenshot)
})

onBeforeUnmount(() => {
  window.removeEventListener('paste', handlePasteScreenshot)
})
</script>

<template>
  <div class="pageBox trade-record-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">交易记录</h2>
        <p class="subtitle">维护交易记录、盈亏复盘和操作截图</p>
      </div>
      <div class="toolbar-actions">
        <el-upload
          accept=".xlsx,.xls"
          :show-file-list="false"
          :auto-upload="true"
          :http-request="handleImportTradeRecords"
          :disabled="importing"
        >
          <el-button :loading="importing">上传交易记录</el-button>
        </el-upload>
        <el-button type="primary" @click="openCreateDialog">新增交易记录</el-button>
      </div>
    </div>

    <div class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="合约">
          <el-select v-model="filters.contract" filterable clearable placeholder="请选择合约" style="width: 180px">
            <el-option
              v-for="contractItem in contracts"
              :key="contractItem.contract_id"
              :label="contractItem.symbol"
              :value="contractItem.symbol"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓方向">
          <el-select v-model="filters.open_direction" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="option in openDirectionOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="30F线段类型">
          <el-select v-model="filters.segment_type" placeholder="全部" clearable style="width: 180px">
            <el-option
              v-for="option in segmentTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓时间">
          <el-date-picker
            v-model="filters.open_time_range"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="平仓时间">
          <el-date-picker
            v-model="filters.close_time_range"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleResetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table v-loading="loading" :data="records" border row-key="trade_record_id" empty-text="暂无交易记录">
      <el-table-column prop="trade_record_id" label="ID" width="80" />
      <el-table-column prop="contract" label="合约" min-width="120" />
      <el-table-column prop="open_direction" label="开仓方向" width="100">
        <template #default="{ row }">{{ formatOpenDirection(row.open_direction) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ formatStatus(row) }}</template>
      </el-table-column>
      <el-table-column prop="lots" label="手数" width="90" />
      <el-table-column prop="open_time" label="开仓时间" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.open_time) }}</template>
      </el-table-column>
      <el-table-column prop="open_price" label="开仓价格" min-width="120" align="right">
        <template #default="{ row }">{{ formatCurrency(row.open_price, 1) }}</template>
      </el-table-column>
      <el-table-column prop="close_time" label="平仓时间" min-width="170">
        <template #default="{ row }">{{ row.close_time ? formatDateTime(row.close_time) : '-' }}</template>
      </el-table-column>
      <el-table-column prop="close_price" label="平仓价格" min-width="120" align="right">
        <template #default="{ row }">{{ formatCurrency(row.close_price, 1) }}</template>
      </el-table-column>
      <el-table-column prop="segment_type" label="30F线段类型" min-width="140">
        <template #default="{ row }">{{ formatSegmentType(row.segment_type) }}</template>
      </el-table-column>
      <el-table-column prop="fee" label="手续费" min-width="110" align="right">
        <template #default="{ row }">{{ formatCurrency(row.fee) }}</template>
      </el-table-column>
      <el-table-column prop="actual_pnl" label="实际盈亏" min-width="120" align="right">
        <template #default="{ row }">
          <span v-if="row.actual_pnl !== null" :class="Number(row.actual_pnl) >= 0 ? 'pnl-positive' : 'pnl-negative'">
            {{ formatCurrency(row.actual_pnl) }}
          </span>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作截图" min-width="180">
        <template #default="{ row }">
          <div v-if="row.screenshots.length" class="screenshot-list">
            <el-image
              v-for="item in row.screenshots.slice(0, 3)"
              :key="item.path"
              :src="resolveTradeRecordScreenshotUrl(item.path)"
              :preview-src-list="getPreviewScreenshotUrls(row.screenshots)"
              preview-teleported
              fit="cover"
              class="screenshot-thumb"
            />
            <span v-if="row.screenshots.length > 3" class="screenshot-more">+{{ row.screenshots.length - 3 }}</span>
          </div>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="comment" label="操作评价" min-width="220" show-overflow-tooltip />
      <el-table-column prop="updated_at" label="更新时间" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="140">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">修改</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="48rem" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="8rem" class="trade-form">
        <div class="form-grid">
          <el-form-item label="合约" prop="contract">
            <el-select v-model="form.contract" filterable placeholder="请选择合约" style="width: 100%">
              <el-option
                v-for="contractItem in contracts"
                :key="contractItem.contract_id"
                :label="contractItem.symbol"
                :value="contractItem.symbol"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="开仓方向" prop="open_direction">
            <el-select v-model="form.open_direction" placeholder="请选择开仓方向" style="width: 100%">
              <el-option
                v-for="option in openDirectionOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="手数" prop="lots">
            <el-input-number v-model="form.lots" :min="1" :step="1" :precision="0" style="width: 100%" />
          </el-form-item>
          <el-form-item label="开仓时间" prop="open_time">
            <el-date-picker
              v-model="form.open_time"
              type="datetime"
              placeholder="请选择开仓时间"
              value-format="YYYY-MM-DD HH:mm:ss"
              :disabled-date="disableFutureDateTime"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="开仓价格" prop="open_price">
            <el-input-number v-model="form.open_price" :min="0" :precision="1" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item label="平仓时间">
            <el-date-picker
              v-model="form.close_time"
              type="datetime"
              placeholder="未平仓可留空"
              value-format="YYYY-MM-DD HH:mm:ss"
              :disabled-date="disableFutureDateTime"
              clearable
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="平仓价格">
            <el-input-number
              v-model="form.close_price"
              :min="0"
              :precision="1"
              :step="0.5"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="30F线段类型" prop="segment_type">
            <el-select v-model="form.segment_type" placeholder="请选择30F线段类型" style="width: 100%">
              <el-option
                v-for="option in segmentTypeOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="手续费" prop="fee">
            <el-input-number v-model="form.fee" :min="0" :precision="2" :step="0.01" style="width: 100%" />
          </el-form-item>
          <el-form-item label="实际盈亏">
            <el-input-number v-model="form.actual_pnl" :precision="2" :step="1" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item label="操作截图">
          <el-upload
            :file-list="uploadFileList"
            list-type="picture-card"
            accept=".jpg,.jpeg,.png,.webp,.gif"
            :auto-upload="true"
            :before-upload="beforeScreenshotUpload"
            :http-request="handleUploadRequest"
            :on-remove="handleUploadRemove"
            multiple
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持点击上传，也支持在弹窗打开时按 Ctrl+V 粘贴截图</div>
        </el-form-item>

        <el-form-item label="操作评价">
          <el-input
            v-model="form.comment"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请输入操作评价"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确认</el-button>
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

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
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

.screenshot-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.screenshot-thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
}

.screenshot-more {
  color: #909399;
  font-size: 12px;
}

.empty-text {
  color: #c0c4cc;
}

.upload-tip {
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
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

  .toolbar-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
