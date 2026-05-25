<script lang="ts" setup>
import {
  createTradeRecordApi,
  deleteTradeRecordApi,
  getFutureContractList,
  getTradeRecordListApi,
  importTradeRecordsApi,
  mergeTradeRecordsApi,
  resolveTradeRecordScreenshotUrl,
  updateTradeRecordApi,
  type FutureContract,
  type TradeRecord,
  type TradeRecordCreateParams,
  type TradeRecordOpenDirection,
  type TradeRecordOpenSignal,
  type TradeRecordSegmentType,
  type TradeRecordUpdateParams,
} from '@/api/modules'
import { formatDateTime } from '@/utils/date'
import { ElMessage, ElMessageBox, type TableInstance, type UploadRequestOptions } from 'element-plus'
import { computed, reactive, ref } from 'vue'
import MergeTradeRecordsDialog from './MergeTradeRecordsDialog.vue'
import TradeRecordFormDialog from './TradeRecordFormDialog.vue'

interface TradeRecordFilters {
  contract: string
  open_direction: '' | TradeRecordOpenDirection
  segment_type: '' | TradeRecordSegmentType
  open_time_range: string[]
  close_time_range: string[]
}

interface TradeRecordFormModel {
  trade_record_id?: number
  contract: string
  open_direction: TradeRecordOpenDirection
  lots: number
  open_time: string
  open_price: number
  close_time: string
  close_price: number | null
  segment_type: TradeRecordSegmentType
  open_signal: TradeRecordOpenSignal | null
  fee: number
  actual_pnl: number | null
  screenshots: Array<{
    path: string
    original_name: string
    content_type: string
    size: number
  }>
  comment: string
}

interface MergePreview {
  contract: string
  openDirectionLabel: string
  recordCount: number
  totalLots: number
  earliestOpenTime: string
  latestCloseTime: string
  totalFeeText: string
  totalPnlText: string
}

const SEGMENT_PUSH = 'trend_push' as const
const OPEN_DIRECTION_LONG = 'long' as const

const segmentTypeOptions: Array<{ label: string; value: TradeRecordSegmentType }> = [
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
  { label: '（假突破）回调转区间段', value: 'false_break_range_transition' },
  { label: '（真突破）区间转推动段', value: 'true_break_trend_push_transition' },
]

const segmentTypeLabelMap: Record<TradeRecordSegmentType, string> = {
  trend_push: '趋势推动段',
  trend_pullback: '趋势回调段',
  range_internal: '区间内部段',
  false_break_range_transition: '（假突破）回调转区间段',
  true_break_trend_push_transition: '（真突破）区间转推动段',
}

const openSignalOptions: Array<{ label: string; value: TradeRecordOpenSignal }> = [
  { label: 'EMA20阻力+站稳关键位', value: 'ema20_resistance_key_level_confirmed' },
  { label: 'EMA120阻力+头肩顶/头肩底', value: 'ema120_resistance_head_shoulders' },
  { label: 'EMA120阻力+三推楔形', value: 'ema120_resistance_three_push_wedge' },
  { label: 'EMA120阻力+突破交易区间然后回拉', value: 'ema120_resistance_range_break_pullback' },
  { label: '区间边界附近+两次以上尝试突破受阻', value: 'range_edge_multiple_breakout_failures' },
  { label: '不符合开仓信号', value: 'not_matching_open_signal' },
]

const openSignalLabelMap: Record<TradeRecordOpenSignal, string> = {
  ema20_resistance_key_level_confirmed: 'EMA20阻力+站稳关键位',
  ema120_resistance_head_shoulders: 'EMA120阻力+头肩顶/头肩底',
  ema120_resistance_three_push_wedge: 'EMA120阻力+三推楔形',
  ema120_resistance_range_break_pullback: 'EMA120阻力+突破交易区间然后回拉',
  range_edge_multiple_breakout_failures: '区间边界附近+两次以上尝试突破受阻',
  not_matching_open_signal: '不符合开仓信号',
}

const openDirectionOptions: Array<{ label: string; value: TradeRecordOpenDirection }> = [
  { label: '多单', value: 'long' },
  { label: '空单', value: 'short' },
]

const openDirectionLabelMap: Record<TradeRecordOpenDirection, string> = {
  long: '多单',
  short: '空单',
}

const sourceLabelMap: Record<TradeRecord['source'], string> = {
  manual: '手动',
  import: '导入',
}

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const merging = ref(false)
const dialogVisible = ref(false)
const mergeDialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const tableRef = ref<TableInstance>()
const contracts = ref<FutureContract[]>([])
const records = ref<TradeRecord[]>([])
const selectedRecords = ref<TradeRecord[]>([])
const mergePreview = ref<MergePreview | null>(null)

const filters = reactive<TradeRecordFilters>({
  contract: '',
  open_direction: '',
  segment_type: '',
  open_time_range: [],
  close_time_range: [],
})

const emptyFormModel = (): TradeRecordFormModel => ({
  contract: '',
  open_direction: OPEN_DIRECTION_LONG,
  lots: 1,
  open_time: '',
  open_price: 0,
  close_time: '',
  close_price: null,
  segment_type: SEGMENT_PUSH,
  open_signal: null,
  fee: 0,
  actual_pnl: null,
  screenshots: [],
  comment: '',
})

const dialogInitialValue = ref<TradeRecordFormModel>(emptyFormModel())

const canMerge = computed(() => selectedRecords.value.length >= 2)

const buildListParams = () => ({
  contract: filters.contract.trim() || undefined,
  open_direction: filters.open_direction || undefined,
  segment_type: filters.segment_type || undefined,
  open_time_start: filters.open_time_range[0] || undefined,
  open_time_end: filters.open_time_range[1] || undefined,
  close_time_start: filters.close_time_range[0] || undefined,
  close_time_end: filters.close_time_range[1] || undefined,
})

const toUploadError = (message: string, options: UploadRequestOptions): Parameters<NonNullable<typeof options.onError>>[0] => ({
  name: 'UploadError',
  message,
  status: 500,
  method: 'POST',
  url: '',
})

const formatCurrency = (value?: number | string | null, fractionDigits = 2) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

const formatSegmentType = (segmentType: TradeRecordSegmentType | null) => {
  if (!segmentType) {
    return '-'
  }
  return segmentTypeLabelMap[segmentType] ?? segmentType
}

const formatOpenSignal = (openSignal: TradeRecordOpenSignal | null) => {
  if (!openSignal) {
    return '-'
  }
  return openSignalLabelMap[openSignal] ?? openSignal
}

const formatOpenDirection = (openDirection: TradeRecordOpenDirection) => {
  return openDirectionLabelMap[openDirection] ?? openDirection
}

const formatSource = (source: TradeRecord['source']) => {
  return sourceLabelMap[source] ?? source
}

const formatStatus = (record: TradeRecord) => {
  return record.close_time ? '已平仓' : '未平仓'
}

const getPreviewScreenshotUrls = (screenshots: TradeRecord['screenshots']) => {
  return screenshots.map((item) => resolveTradeRecordScreenshotUrl(item.path))
}

const loadTradeRecords = async () => {
  loading.value = true
  try {
    records.value = await getTradeRecordListApi(buildListParams())
    selectedRecords.value = []
    tableRef.value?.clearSelection()
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
  dialogInitialValue.value = emptyFormModel()
  dialogVisible.value = true
}

const openEditDialog = (record: TradeRecord) => {
  dialogMode.value = 'edit'
  dialogInitialValue.value = {
    trade_record_id: record.trade_record_id,
    contract: record.contract,
    open_direction: record.open_direction,
    lots: record.lots,
    open_time: record.open_time,
    open_price: Number(record.open_price),
    close_time: record.close_time ?? '',
    close_price: record.close_price === null ? null : Number(record.close_price),
    segment_type: record.segment_type ?? SEGMENT_PUSH,
    open_signal: record.open_signal,
    fee: Number(record.fee),
    actual_pnl: record.actual_pnl === null ? null : Number(record.actual_pnl),
    screenshots: [...record.screenshots],
    comment: record.comment ?? '',
  }
  dialogVisible.value = true
}

const submitTradeRecord = async (payload: TradeRecordCreateParams | TradeRecordUpdateParams) => {
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createTradeRecordApi(payload as TradeRecordCreateParams)
      ElMessage.success('新增交易记录成功')
    } else {
      await updateTradeRecordApi(payload as TradeRecordUpdateParams)
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

const validateMergeSelection = (items: TradeRecord[]) => {
  if (items.length < 2) {
    return '请至少选择 2 条交易记录'
  }

  const contract = items[0]!.contract
  const openDirection = items[0]!.open_direction
  for (const item of items) {
    if (item.contract !== contract) {
      return '仅支持合并相同合约的记录'
    }
    if (item.open_direction !== openDirection) {
      return '仅支持合并相同开仓方向的记录'
    }
    if (!item.close_time || item.close_price === null) {
      return '仅支持合并已平仓的记录'
    }
  }

  return ''
}

const openMergeDialog = () => {
  const validationError = validateMergeSelection(selectedRecords.value)
  if (validationError) {
    ElMessage.error(validationError)
    return
  }

  const totalLots = selectedRecords.value.reduce((sum, item) => sum + item.lots, 0)
  const totalFee = selectedRecords.value.reduce((sum, item) => sum + Number(item.fee), 0)
  const totalPnl = selectedRecords.value.reduce((sum, item) => sum + Number(item.actual_pnl ?? 0), 0)
  const openTimes = selectedRecords.value.map((item) => item.open_time).sort()
  const closeTimes = selectedRecords.value
    .map((item) => item.close_time)
    .filter((value): value is string => Boolean(value))
    .sort()

  mergePreview.value = {
    contract: selectedRecords.value[0]!.contract,
    openDirectionLabel: formatOpenDirection(selectedRecords.value[0]!.open_direction),
    recordCount: selectedRecords.value.length,
    totalLots,
    earliestOpenTime: formatDateTime(openTimes[0]),
    latestCloseTime: closeTimes.length ? formatDateTime(closeTimes.at(-1)!) : '-',
    totalFeeText: formatCurrency(totalFee),
    totalPnlText: formatCurrency(totalPnl),
  }
  mergeDialogVisible.value = true
}

const confirmMergeRecords = async () => {
  if (!mergePreview.value) {
    return
  }

  merging.value = true
  try {
    await mergeTradeRecordsApi({
      trade_record_ids: selectedRecords.value.map((item) => item.trade_record_id),
    })
    ElMessage.success('合并交易记录成功')
    mergeDialogVisible.value = false
    mergePreview.value = null
    await loadTradeRecords()
  } catch {
    ElMessage.error('合并交易记录失败')
  } finally {
    merging.value = false
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
    options.onError?.(toUploadError(error instanceof Error ? error.message : '上传交易记录失败', options))
    ElMessage.error('上传交易记录失败')
  } finally {
    importing.value = false
  }
}

const handleSelectionChange = (items: TradeRecord[]) => {
  selectedRecords.value = items
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

void loadContracts()
void loadTradeRecords()
</script>

<template>
  <div class="pageBox trade-record-manager">
    <div class="toolbar">
      <div>
        <h2 class="title">交易记录</h2>
        <p class="subtitle">维护交易记录、导入成交数据、补充截图与复盘评价</p>
      </div>
      <div class="toolbar-actions">
        <el-button type="warning" :disabled="!canMerge" @click="openMergeDialog">合并选中记录</el-button>
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

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="records"
      border
      row-key="trade_record_id"
      empty-text="暂无交易记录"
      max-height="35rem"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="52" />
      <el-table-column prop="trade_record_id" label="ID" width="50" fixed="left" />
      <el-table-column prop="contract" label="合约" min-width="80" fixed="left" />
      <el-table-column prop="open_direction" label="开仓方向" width="100">
        <template #default="{ row }">{{ formatOpenDirection(row.open_direction) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ formatStatus(row) }}</template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="90">
        <template #default="{ row }">{{ formatSource(row.source) }}</template>
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
      <el-table-column prop="open_signal" label="开仓信号" min-width="220">
        <template #default="{ row }">{{ formatOpenSignal(row.open_signal) }}</template>
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
      <el-table-column label="操作" fixed="right" width="120">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditDialog(row)">修改</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <TradeRecordFormDialog
      v-model:visible="dialogVisible"
      :mode="dialogMode"
      :submitting="submitting"
      :contracts="contracts"
      :open-signal-options="openSignalOptions"
      :initial-value="dialogInitialValue"
      @submit="submitTradeRecord"
    />

    <MergeTradeRecordsDialog
      v-model:visible="mergeDialogVisible"
      :loading="merging"
      :preview="mergePreview"
      @confirm="confirmMergeRecords"
    />
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
  flex-wrap: wrap;
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
  }
}
</style>
