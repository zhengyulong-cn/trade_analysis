<script lang="ts" setup>
import {
  deleteFutureKlinesApi,
  deleteFutureKlineItemsApi,
  getFutureContractList,
  getFutureKlinePageApi,
  syncFutureKlinesApi,
  type FutureContract,
  type FutureKlineQueryItem,
} from '@/api/modules'
import {
  createRecentDateRange,
  formatDateTime as formatDateTimeByDayjs,
  getLatestDateTime,
} from '@/utils/date'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

interface OverviewRow {
  rowKey: string
  symbol: string
  name: string
  exchange: string
  interval: number
  intervalName: string
  total: number
  latestTime: string
}

const TEXT = {
  pageTitle: '期货K线管理',
  pageSubtitle: '左侧展示合约-周期汇总，右侧展示对应 K 线明细。',
  refreshOverview: '刷新合约汇总数据',
  batchUpdate: '批量更新',
  overviewTitle: '合约汇总数据',
  detailTitle: 'K 线明细',
  detailPlaceholder: '点击左侧汇总表某行查看明细',
  detailSelectedPrefix: '当前查看：',
  latestTimePrefix: '最近数据时间：',
  emptyLatestTime: '暂无最近时间',
  emptyOverview: '暂无期货数据概览',
  emptyDetail: '请先点击左侧合约周期查看 K 线明细',
  contract: '合约',
  interval: '周期',
  total: '数据总数',
  latestTime: '最近时间',
  action: '操作',
  update: '更新',
  delete: '删除',
  timeRange: '时间筛选',
  startTime: '开始时间',
  endTime: '结束时间',
  rangeSeparator: '至',
  search: '查询',
  reset: '重置',
  time: '时间',
  open: '开盘价',
  high: '最高价',
  low: '最低价',
  close: '收盘价',
  volume: '成交量',
  hold: '持仓量',
  totalCountPrefix: '共 ',
  totalCountSuffix: ' 条',
  loadOverviewError: '获取期货数据概览失败',
  loadDetailError: '获取 K 线明细失败',
  syncError: '更新 K 线数据失败',
  deleteError: '删除 K 线数据失败',
  syncSuccessPrefix: '更新完成：新增 ',
  syncSuccessMiddle: ' 条，覆盖 ',
  syncSuccessSuffix: ' 条',
  deleteSuccessPrefix: '删除完成：已删除 ',
  deleteSuccessSuffix: ' 条',
  deleteConfirmTitle: '确认删除',
  deleteConfirmPrefix: '确定删除 ',
  deleteConfirmMiddle: ' ',
  deleteConfirmSuffix: ' 的全部 K 线数据吗？',
  bulkSyncSuccess: '一键更新完成：新增 {inserted} 条，覆盖 {updated} 条',
  bulkSyncPartialSuccess: '一键更新完成：新增 {inserted} 条，覆盖 {updated} 条，失败 {failed} 项',
  batchDelete: '批量删除',
  batchDeleteSelectedPrefix: '已选 ',
  batchDeleteSelectedSuffix: ' 条',
  batchDeleteConfirmMessage: '确定删除选中的 K 线数据吗？',
  batchDeleteError: '批量删除 K 线数据失败',
} as const

const DEFAULT_DETAIL_PAGE_SIZE = 50
const STORAGE_INTERVAL_SECONDS = 300
const STORAGE_INTERVAL_NAME = '5F'
const SYNC_KLINE_LIMIT = 5000

const overviewRows = ref<OverviewRow[]>([])
const detailRows = ref<FutureKlineQueryItem[]>([])
const overviewLoading = ref(false)
const detailLoading = ref(false)
const selectedSymbol = ref('')
const selectedInterval = ref<number>()
const selectedOverviewKey = ref('')
const detailPage = ref(1)
const detailPageSize = ref(DEFAULT_DETAIL_PAGE_SIZE)
const detailTotal = ref(0)
const updatingKeys = ref<string[]>([])
const deletingKeys = ref<string[]>([])
const bulkUpdateLoading = ref(false)
const batchDeleteLoading = ref(false)
const selectedDetailRows = ref<FutureKlineQueryItem[]>([])
const detailTimeRange = ref<[string, string] | []>([])

const createShortcutRange = (days: number) => {
  return createRecentDateRange(days)
}

const shortcuts = [
  {
    text: '\u6700\u8fd1\u4e00\u5929',
    value: () => createShortcutRange(1),
  },
  {
    text: '\u6700\u8fd1\u4e00\u5468',
    value: () => createShortcutRange(7),
  },
  {
    text: '\u6700\u8fd1\u4e24\u5468',
    value: () => createShortcutRange(14),
  },
  {
    text: '\u6700\u8fd1\u4e00\u4e2a\u6708',
    value: () => createShortcutRange(30),
  },
]

const hasDetailSelection = computed(() => Boolean(selectedSymbol.value && selectedInterval.value))

const selectedOverviewRow = computed(() => {
  return overviewRows.value.find((row) => row.rowKey === selectedOverviewKey.value) ?? null
})

const detailDescription = computed(() => {
  if (!selectedOverviewRow.value) {
    return TEXT.detailPlaceholder
  }

  return `${TEXT.detailSelectedPrefix}${selectedOverviewRow.value.symbol} \u00b7 ${selectedOverviewRow.value.intervalName}`
})

const getOverviewKey = (symbol: string, interval: number) => `${symbol}-${interval}`

const formatDateTime = (value?: Parameters<typeof formatDateTimeByDayjs>[0]) => {
  return formatDateTimeByDayjs(value)
}

const formatNumber = (value: number | string) => {
  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return '-'
  }

  return numericValue.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  })
}

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'object' && error !== null) {
    const response = error as { data?: { detail?: string; msg?: string } }
    if (response.data?.detail) {
      return response.data.detail
    }
    if (response.data?.msg) {
      return response.data.msg
    }
  }

  return fallback
}

const getDetailTimeParams = () => {
  if (detailTimeRange.value.length !== 2) {
    return {}
  }

  const [startTime, endTime] = detailTimeRange.value
  return {
    start_time: startTime,
    end_time: endTime,
  }
}

const queryKlinePage = (symbol: string, interval: number, page = 1, pageSize = 1) => {
  return getFutureKlinePageApi({
    symbol,
    interval,
    page,
    page_size: pageSize,
  })
}

const buildOverviewRows = async (
  contractList: FutureContract[],
) => {
  const rows = await Promise.all(
    contractList.map(async (contract) => {
      const pageResult = await queryKlinePage(contract.symbol, STORAGE_INTERVAL_SECONDS)
      const latestItem = pageResult.items[pageResult.items.length - 1]

      return {
        rowKey: getOverviewKey(contract.symbol, STORAGE_INTERVAL_SECONDS),
        symbol: contract.symbol,
        name: contract.name,
        exchange: contract.exchange,
        interval: STORAGE_INTERVAL_SECONDS,
        intervalName: STORAGE_INTERVAL_NAME,
        total: pageResult.total,
        latestTime: latestItem?.date_time ?? '',
      } satisfies OverviewRow
    }),
  )

  return rows.sort((first, second) => {
    return first.symbol.localeCompare(second.symbol, 'zh-CN')
  })
}

const syncDetailSelectionFromOverview = (row?: OverviewRow) => {
  if (!row) {
    return
  }

  selectedSymbol.value = row.symbol
  selectedInterval.value = row.interval
  selectedOverviewKey.value = row.rowKey
}

const ensureDefaultSelection = () => {
  const matchedRow = overviewRows.value.find((row) => row.rowKey === selectedOverviewKey.value)
  const fallbackRow = matchedRow ?? overviewRows.value[0]
  syncDetailSelectionFromOverview(fallbackRow)
}

const resetDetail = () => {
  detailRows.value = []
  detailTotal.value = 0
  selectedDetailRows.value = []
}

const loadOverview = async () => {
  overviewLoading.value = true

  try {
    const contractList = await getFutureContractList()

    if (!contractList.length) {
      overviewRows.value = []
      resetDetail()
      selectedSymbol.value = ''
      selectedInterval.value = undefined
      selectedOverviewKey.value = ''
      return
    }

    overviewRows.value = await buildOverviewRows(contractList)
    ensureDefaultSelection()
  } catch (error) {
    overviewRows.value = []
    resetDetail()
    ElMessage.error(extractErrorMessage(error, TEXT.loadOverviewError))
  } finally {
    overviewLoading.value = false
  }
}

const loadDetail = async (page = detailPage.value) => {
  if (!hasDetailSelection.value || !selectedInterval.value) {
    resetDetail()
    return
  }

  detailLoading.value = true
  detailPage.value = page
  selectedDetailRows.value = []

  try {
    const pageResult = await getFutureKlinePageApi({
      symbol: selectedSymbol.value,
      interval: selectedInterval.value,
      page: detailPage.value,
      page_size: detailPageSize.value,
      ...getDetailTimeParams(),
    })

    detailRows.value = pageResult.items
    detailTotal.value = pageResult.total
  } catch (error) {
    resetDetail()
    ElMessage.error(extractErrorMessage(error, TEXT.loadDetailError))
  } finally {
    detailLoading.value = false
  }
}

const refreshOverviewRow = async (symbol: string, interval: number) => {
  const latestPage = await queryKlinePage(symbol, interval)
  const latestItem = latestPage.items[latestPage.items.length - 1]
  const rowKey = getOverviewKey(symbol, interval)

  overviewRows.value = overviewRows.value.map((row) => {
    if (row.rowKey !== rowKey) {
      return row
    }

    return {
      ...row,
      total: latestPage.total,
      latestTime: latestItem?.date_time ?? '',
    }
  })
}

const handleOverviewRowClick = (row: OverviewRow) => {
  syncDetailSelectionFromOverview(row)
  detailPage.value = 1
  void loadDetail(1)
}

const handleTimeRangeSearch = () => {
  if (!hasDetailSelection.value) {
    return
  }

  detailPage.value = 1
  void loadDetail(1)
}

const handleTimeRangeReset = () => {
  detailTimeRange.value = []
  if (!hasDetailSelection.value) {
    return
  }

  detailPage.value = 1
  void loadDetail(1)
}

const handleDetailPageChange = (page: number) => {
  void loadDetail(page)
}

const handleDetailPageSizeChange = (pageSize: number) => {
  detailPageSize.value = pageSize
  detailPage.value = 1
  void loadDetail(1)
}

const handleDetailSelectionChange = (rows: FutureKlineQueryItem[]) => {
  selectedDetailRows.value = rows
}

const handleSync = async (row: OverviewRow) => {
  const rowKey = row.rowKey
  updatingKeys.value = [...updatingKeys.value, rowKey]

  try {
    const result = await syncFutureKlinesApi({
      symbol: row.symbol,
      interval: row.interval,
      limit: SYNC_KLINE_LIMIT,
    })

    await refreshOverviewRow(row.symbol, row.interval)

    if (selectedSymbol.value === row.symbol && selectedInterval.value === row.interval) {
      detailPage.value = 1
      await loadDetail(1)
    }

    ElMessage.success(
      `${TEXT.syncSuccessPrefix}${result.inserted}${TEXT.syncSuccessMiddle}${result.updated}${TEXT.syncSuccessSuffix}`,
    )
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, TEXT.syncError))
  } finally {
    updatingKeys.value = updatingKeys.value.filter((item) => item !== rowKey)
  }
}

const handleBulkSync = async () => {
  const rows = [...overviewRows.value]
  if (!rows.length) {
    return
  }

  bulkUpdateLoading.value = true
  updatingKeys.value = Array.from(new Set([...updatingKeys.value, ...rows.map((row) => row.rowKey)]))

  let inserted = 0
  let updated = 0
  let failed = 0

  try {
    for (const row of rows) {
      try {
        const result = await syncFutureKlinesApi({
          symbol: row.symbol,
          interval: row.interval,
          limit: SYNC_KLINE_LIMIT,
        })
        inserted += result.inserted
        updated += result.updated
      } catch {
        failed += 1
      }
    }

    await loadOverview()

    if (hasDetailSelection.value) {
      detailPage.value = 1
      await loadDetail(1)
    }

    if (failed > 0) {
      ElMessage.warning(
        TEXT.bulkSyncPartialSuccess
          .replace('{inserted}', String(inserted))
          .replace('{updated}', String(updated))
          .replace('{failed}', String(failed)),
      )
    } else {
      ElMessage.success(
        TEXT.bulkSyncSuccess
          .replace('{inserted}', String(inserted))
          .replace('{updated}', String(updated)),
      )
    }
  } finally {
    const rowKeySet = new Set(rows.map((row) => row.rowKey))
    updatingKeys.value = updatingKeys.value.filter((item) => !rowKeySet.has(item))
    bulkUpdateLoading.value = false
  }
}

const handleDelete = async (row: OverviewRow) => {
  const rowKey = row.rowKey

  try {
    await ElMessageBox.confirm(
      `${TEXT.deleteConfirmPrefix}${row.symbol}${TEXT.deleteConfirmMiddle}${row.intervalName}${TEXT.deleteConfirmSuffix}`,
      TEXT.deleteConfirmTitle,
      {
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deletingKeys.value = [...deletingKeys.value, rowKey]

  try {
    const result = await deleteFutureKlinesApi({
      symbol: row.symbol,
      interval: row.interval,
    })

    await refreshOverviewRow(row.symbol, row.interval)

    if (selectedSymbol.value === row.symbol && selectedInterval.value === row.interval) {
      detailPage.value = 1
      await loadDetail(1)
    }

    ElMessage.success(`${TEXT.deleteSuccessPrefix}${result.deleted}${TEXT.deleteSuccessSuffix}`)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, TEXT.deleteError))
  } finally {
    deletingKeys.value = deletingKeys.value.filter((item) => item !== rowKey)
  }
}

const handleBatchDetailDelete = async () => {
  if (!hasDetailSelection.value || !selectedInterval.value || !selectedDetailRows.value.length) {
    return
  }

  try {
    await ElMessageBox.confirm(TEXT.batchDeleteConfirmMessage, TEXT.deleteConfirmTitle, {
      type: 'warning',
    })
  } catch {
    return
  }

  batchDeleteLoading.value = true

  try {
    const result = await deleteFutureKlineItemsApi({
      kline_ids: selectedDetailRows.value.map((row) => row.kline_id),
    })

    await refreshOverviewRow(selectedSymbol.value, selectedInterval.value)

    const nextPage = selectedDetailRows.value.length >= detailRows.value.length && detailPage.value > 1
      ? detailPage.value - 1
      : detailPage.value
    await loadDetail(nextPage)

    ElMessage.success(`${TEXT.deleteSuccessPrefix}${result.deleted}${TEXT.deleteSuccessSuffix}`)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, TEXT.batchDeleteError))
  } finally {
    batchDeleteLoading.value = false
  }
}

const isRowUpdating = (rowKey: string) => {
  return updatingKeys.value.includes(rowKey)
}

const isRowDeleting = (rowKey: string) => {
  return deletingKeys.value.includes(rowKey)
}

const overviewRowClassName = ({ row }: { row: OverviewRow }) => {
  return row.rowKey === selectedOverviewKey.value ? 'overview-row-selected' : ''
}

const latestOverviewUpdateText = computed(() => {
  const latestTime = getLatestDateTime(overviewRows.value.map((row) => row.latestTime))

  if (!latestTime) {
    return TEXT.emptyLatestTime
  }

  return `${TEXT.latestTimePrefix}${formatDateTime(latestTime)}`
})

onMounted(async () => {
  await loadOverview()
  if (hasDetailSelection.value) {
    await loadDetail(1)
  }
})
</script>

<template>
  <div class="pageBox future-data-manager">
    <header class="page-header">
      <div>
        <h2 class="title">{{ TEXT.pageTitle }}</h2>
        <p class="subtitle">{{ TEXT.pageSubtitle }}</p>
      </div>
      <div class="page-actions">
        <el-button :loading="overviewLoading" @click="loadOverview">{{ TEXT.refreshOverview }}</el-button>
        <el-button
          type="primary"
          :loading="bulkUpdateLoading"
          :disabled="overviewLoading || !overviewRows.length"
          @click="handleBulkSync"
        >
          {{ TEXT.batchUpdate }}
        </el-button>
      </div>
    </header>

    <div class="content-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">{{ TEXT.overviewTitle }}</h3>
            <p class="panel-subtitle">{{ latestOverviewUpdateText }}</p>
          </div>
        </div>

        <el-table
          v-loading="overviewLoading"
          :data="overviewRows"
          border
          row-key="rowKey"
          highlight-current-row
          :row-class-name="overviewRowClassName"
          :empty-text="TEXT.emptyOverview"
          @row-click="handleOverviewRowClick"
          max-height="38rem"
        >
          <el-table-column :label="TEXT.contract" min-width="120">
            <template #default="{ row }">
              <div class="contract-cell">
                <span class="contract-symbol">{{ row.symbol }}</span>
                <span class="contract-name">{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="intervalName" :label="TEXT.interval" width="80" />
          <el-table-column prop="total" :label="TEXT.total" min-width="120">
            <template #default="{ row }">
              {{ row.total.toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column prop="latestTime" :label="TEXT.latestTime" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.latestTime) }}
            </template>
          </el-table-column>
          <el-table-column :label="TEXT.action" min-width="140" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                :loading="isRowUpdating(row.rowKey)"
                @click.stop="handleSync(row)"
              >
                {{ TEXT.update }}
              </el-button>
              <el-button
                type="danger"
                link
                :loading="isRowDeleting(row.rowKey)"
                @click.stop="handleDelete(row)"
              >
                {{ TEXT.delete }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-header panel-header--detail">
          <div>
            <h3 class="panel-title">{{ TEXT.detailTitle }}</h3>
            <p class="panel-subtitle">{{ detailDescription }}</p>
          </div>
          <div class="detail-tools">
            <span class="tool-label">{{ TEXT.timeRange }}</span>
            <el-date-picker
              v-model="detailTimeRange"
              type="daterange"
              unlink-panels
              class="time-range-picker"
              :start-placeholder="TEXT.startTime"
              :end-placeholder="TEXT.endTime"
              :range-separator="TEXT.rangeSeparator"
              value-format="YYYY-MM-DDTHH:mm:ss"
              :shortcuts="shortcuts"
            />
            <el-button type="primary" :disabled="!hasDetailSelection" @click="handleTimeRangeSearch">
              {{ TEXT.search }}
            </el-button>
            <el-button :disabled="!hasDetailSelection" @click="handleTimeRangeReset">
              {{ TEXT.reset }}
            </el-button>
            <el-button
              type="danger"
              :loading="batchDeleteLoading"
              :disabled="!selectedDetailRows.length"
              @click="handleBatchDetailDelete"
            >
              {{ TEXT.batchDelete }}
            </el-button>
            <span class="tool-label">{{ `${TEXT.batchDeleteSelectedPrefix}${selectedDetailRows.length}${TEXT.batchDeleteSelectedSuffix}` }}</span>
          </div>
        </div>

        <el-table
          v-loading="detailLoading"
          :data="detailRows"
          border
          :empty-text="TEXT.emptyDetail"
          max-height="35rem"
          @selection-change="handleDetailSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="date_time" :label="TEXT.time" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.date_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="open" :label="TEXT.open" min-width="110">
            <template #default="{ row }">
              {{ formatNumber(row.open) }}
            </template>
          </el-table-column>
          <el-table-column prop="high" :label="TEXT.high" min-width="110">
            <template #default="{ row }">
              {{ formatNumber(row.high) }}
            </template>
          </el-table-column>
          <el-table-column prop="low" :label="TEXT.low" min-width="110">
            <template #default="{ row }">
              {{ formatNumber(row.low) }}
            </template>
          </el-table-column>
          <el-table-column prop="close" :label="TEXT.close" min-width="110">
            <template #default="{ row }">
              {{ formatNumber(row.close) }}
            </template>
          </el-table-column>
          <el-table-column prop="volume" :label="TEXT.volume" min-width="120">
            <template #default="{ row }">
              {{ formatNumber(row.volume) }}
            </template>
          </el-table-column>
          <el-table-column prop="hold" :label="TEXT.hold" min-width="120">
            <template #default="{ row }">
              {{ formatNumber(row.hold) }}
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <span class="pagination-summary">
            {{ `${TEXT.totalCountPrefix}${detailTotal.toLocaleString('zh-CN')}${TEXT.totalCountSuffix}` }}
          </span>
          <el-pagination
            :current-page="detailPage"
            :page-size="detailPageSize"
            :page-sizes="[20, 50, 100, 200]"
            layout="sizes, prev, pager, next"
            :total="detailTotal"
            @current-change="handleDetailPageChange"
            @size-change="handleDetailPageSizeChange"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<style lang="less" scoped>
.future-data-manager {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header,
.panel-header,
.panel-header--detail,
.contract-cell,
.pagination,
.detail-tools,
.page-actions {
  display: flex;
}

.page-header,
.panel-header,
.pagination {
  align-items: center;
  justify-content: space-between;
}

.panel-header--detail {
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.title,
.panel-title {
  margin: 0;
  color: #303133;
}

.title {
  font-size: 20px;
  font-weight: 600;
}

.subtitle,
.panel-subtitle,
.contract-name,
.pagination-summary,
.tool-label {
  color: #909399;
}

.subtitle,
.panel-subtitle {
  margin-top: 6px;
  font-size: 13px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(640px, 1.4fr);
  gap: 16px;
}

.panel {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background-color: #fff;
}

.detail-tools {
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.page-actions {
  gap: 12px;
}

.tool-label {
  font-size: 13px;
  white-space: nowrap;
}

.time-range-picker {
  width: 380px;
}

.contract-cell {
  flex-direction: column;
}

.contract-symbol {
  color: #303133;
  font-weight: 600;
}

.contract-name {
  font-size: 12px;
}

.pagination {
  margin-top: 16px;
}

:deep(.overview-row-selected) {
  --el-table-tr-bg-color: #f0f7ff;
}

@media (max-width: 1400px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-header,
  .panel-header--detail,
  .pagination {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-tools {
    width: 100%;
  }

  .time-range-picker {
    width: 100%;
  }
}
</style>

