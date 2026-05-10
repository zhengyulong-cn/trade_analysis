<script lang="ts" setup>
import {
  getFutureOpportunityAnalysisAllApi,
  type FutureOpportunityAnalysisItem,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { computed, onMounted, ref } from 'vue'

const TEXT = {
  pageTitle: '开仓机会分析',
  pageSubtitle: '聚焦最新 K 线所处的开仓区域状态，支持按合约与 30F 线段类型筛选。',
  refresh: '刷新分析结果',
  symbolFilter: '合约筛选',
  segmentTypeFilter: '30F线段类型',
  allSymbols: '全部合约',
  allSegmentTypes: '全部类型',
  totalContracts: '合约总数',
  openZoneContracts: '处于开仓区',
  longContracts: '多单机会',
  shortContracts: '空单机会',
  tableEmpty: '暂无开仓机会分析结果',
  contract: '合约',
  latestPrice: '最新价',
  latestTime: '最新30F时间',
  segmentType: '30F线段类型',
  direction30f: '30F方向',
  direction4h: '4H方向',
  direction5f: '5F方向',
  momentum30f: '30F动能衰竭',
  momentum5f: '5F动能衰竭',
  openSide: '开仓方向',
  openZoneStatus: '当前开仓区',
  zonePrice: '开仓区域',
  tradingRange: '30F交易区间',
  unknown: '-',
  noZone: '否',
  inZone: '是',
  loadError: '获取开仓机会分析失败',
} as const

const SEGMENT_TYPE_OPTIONS = [
  { label: TEXT.allSegmentTypes, value: '' },
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
]

const rows = ref<FutureOpportunityAnalysisItem[]>([])
const loading = ref(false)
const selectedSymbol = ref('')
const selectedSegmentType = ref('')

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

const formatNumber = (value?: number | null) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return TEXT.unknown
  }

  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  })
}

const formatUnixTime = (value?: number | null) => {
  if (!value) {
    return TEXT.unknown
  }

  return dayjs.unix(value).format('YYYY-MM-DD HH:mm:ss')
}

const formatDirection = (value?: string | null) => {
  if (value === 'up') {
    return '上涨'
  }
  if (value === 'down') {
    return '下跌'
  }
  return TEXT.unknown
}

const formatOpenSide = (value?: string | null) => {
  if (value === 'long') {
    return '多'
  }
  if (value === 'short') {
    return '空'
  }
  return TEXT.unknown
}

const formatSegmentType = (value?: string | null) => {
  if (value === 'trend_push') {
    return '趋势推动段'
  }
  if (value === 'trend_pullback') {
    return '趋势回调段'
  }
  if (value === 'range_internal') {
    return '区间内部段'
  }
  return TEXT.unknown
}

const formatPriceRange = (low?: number | null, high?: number | null) => {
  if (low === null || low === undefined || high === null || high === undefined) {
    return TEXT.unknown
  }

  return `${formatNumber(low)} ~ ${formatNumber(high)}`
}

const formatMomentumExhaustion = (
  direction?: string | null,
  time?: number | null,
  price?: number | null,
) => {
  if (!direction || !time) {
    return TEXT.unknown
  }

  const directionText = direction === 'up' ? '上涨衰竭' : direction === 'down' ? '下跌衰竭' : TEXT.unknown
  const priceText = price === null || price === undefined ? TEXT.unknown : formatNumber(price)
  return `${directionText} @ ${formatUnixTime(time)} · ${priceText}`
}

const statusTagType = (row: FutureOpportunityAnalysisItem) => {
  if (row.analysis_status !== 'ok') {
    return 'info'
  }
  return row.in_open_zone ? 'danger' : 'success'
}

const filteredRows = computed(() => {
  return rows.value.filter((row) => {
    if (selectedSymbol.value && row.symbol !== selectedSymbol.value) {
      return false
    }
    if (selectedSegmentType.value && row.current_30f_segment_type !== selectedSegmentType.value) {
      return false
    }
    return true
  })
})

const symbolOptions = computed(() => {
  return [
    { label: TEXT.allSymbols, value: '' },
    ...rows.value.map((row) => ({
      label: `${row.symbol} · ${row.name}`,
      value: row.symbol,
    })),
  ]
})

const totalContracts = computed(() => filteredRows.value.length)
const openZoneContracts = computed(() => filteredRows.value.filter((row) => row.in_open_zone).length)
const longContracts = computed(() => {
  return filteredRows.value.filter((row) => row.analysis_status === 'ok' && row.open_side === 'long').length
})
const shortContracts = computed(() => {
  return filteredRows.value.filter((row) => row.analysis_status === 'ok' && row.open_side === 'short').length
})

const loadData = async () => {
  loading.value = true

  try {
    const result = await getFutureOpportunityAnalysisAllApi()
    rows.value = [...result.items].sort((first, second) => {
      if (first.in_open_zone !== second.in_open_zone) {
        return first.in_open_zone ? -1 : 1
      }
      if (first.analysis_status !== second.analysis_status) {
        return first.analysis_status === 'ok' ? -1 : 1
      }
      return first.symbol.localeCompare(second.symbol, 'zh-CN')
    })
  } catch (error) {
    rows.value = []
    ElMessage.error(extractErrorMessage(error, TEXT.loadError))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="pageBox opportunity-analysis">
    <header class="page-header">
      <div>
        <h2 class="title">{{ TEXT.pageTitle }}</h2>
        <p class="subtitle">{{ TEXT.pageSubtitle }}</p>
      </div>
      <el-button type="primary" :loading="loading" @click="loadData">
        {{ TEXT.refresh }}
      </el-button>
    </header>

    <section class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">{{ TEXT.totalContracts }}</span>
        <strong class="summary-value">{{ totalContracts }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">{{ TEXT.openZoneContracts }}</span>
        <strong class="summary-value summary-value--danger">{{ openZoneContracts }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">{{ TEXT.longContracts }}</span>
        <strong class="summary-value summary-value--up">{{ longContracts }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">{{ TEXT.shortContracts }}</span>
        <strong class="summary-value summary-value--down">{{ shortContracts }}</strong>
      </div>
    </section>

    <section class="panel">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">{{ TEXT.symbolFilter }}</span>
          <el-select v-model="selectedSymbol" filterable clearable class="filter-select">
            <el-option
              v-for="option in symbolOptions"
              :key="option.value || 'all-symbols'"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-label">{{ TEXT.segmentTypeFilter }}</span>
          <el-select v-model="selectedSegmentType" clearable class="filter-select">
            <el-option
              v-for="option in SEGMENT_TYPE_OPTIONS"
              :key="option.value || 'all-types'"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        border
        stripe
        :empty-text="TEXT.tableEmpty"
      >
        <el-table-column :label="TEXT.contract" min-width="150" fixed="left">
          <template #default="{ row }">
            <div class="contract-cell">
              <span class="contract-symbol">{{ row.symbol }}</span>
              <span class="contract-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="latest_price" :label="TEXT.latestPrice" min-width="120">
          <template #default="{ row }">
            {{ formatNumber(row.latest_price) }}
          </template>
        </el-table-column>

        <el-table-column prop="current_4h_segment_direction" :label="TEXT.direction4h" width="100">
          <template #default="{ row }">
            <span :class="row.current_4h_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatDirection(row.current_4h_segment_direction) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="current_30f_segment_direction" :label="TEXT.direction30f" width="100">
          <template #default="{ row }">
            <span :class="row.current_30f_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatDirection(row.current_30f_segment_direction) }}
            </span>
          </template>
        </el-table-column>
        
        <!-- <el-table-column prop="latest_30f_time" :label="TEXT.latestTime" min-width="170">
          <template #default="{ row }">
            {{ formatUnixTime(row.latest_30f_time) }}
          </template>
        </el-table-column> -->

        <el-table-column prop="current_30f_segment_type" :label="TEXT.segmentType" min-width="140">
          <template #default="{ row }">
            {{ formatSegmentType(row.current_30f_segment_type) }}
          </template>
        </el-table-column>

        <el-table-column prop="current_5f_segment_direction" :label="TEXT.direction5f" width="100">
          <template #default="{ row }">
            <span :class="row.current_5f_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatDirection(row.current_5f_segment_direction) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum30f" min-width="220">
          <template #default="{ row }">
            {{
              formatMomentumExhaustion(
                row.latest_30f_momentum_exhaustion_direction,
                row.latest_30f_momentum_exhaustion_time,
                row.latest_30f_momentum_exhaustion_price,
              )
            }}
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum5f" min-width="220">
          <template #default="{ row }">
            {{
              formatMomentumExhaustion(
                row.latest_5f_momentum_exhaustion_direction,
                row.latest_5f_momentum_exhaustion_time,
                row.latest_5f_momentum_exhaustion_price,
              )
            }}
          </template>
        </el-table-column>

        <el-table-column prop="open_side" :label="TEXT.openSide" width="100">
          <template #default="{ row }">
            <span
              :class="row.open_side === 'long' ? 'text-up' : row.open_side === 'short' ? 'text-down' : ''"
            >
              {{ formatOpenSide(row.open_side) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="in_open_zone" :label="TEXT.openZoneStatus" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row)">
              {{
                row.analysis_status === 'ok'
                  ? row.in_open_zone
                    ? TEXT.inZone
                    : TEXT.noZone
                  : row.analysis_status
              }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.zonePrice" min-width="160">
          <template #default="{ row }">
            {{ formatPriceRange(row.zone_low, row.zone_high) }}
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.tradingRange" min-width="160">
          <template #default="{ row }">
            {{ formatPriceRange(row.trading_range_bottom, row.trading_range_top) }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style lang="less" scoped>
.opportunity-analysis {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header,
.filter-bar,
.filter-item,
.contract-cell {
  display: flex;
}

.page-header {
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.subtitle,
.summary-label,
.filter-label,
.contract-name {
  color: #909399;
}

.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card,
.panel {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.summary-card {
  padding: 16px;
}

.summary-label {
  display: block;
  font-size: 13px;
}

.summary-value {
  display: block;
  margin-top: 10px;
  font-size: 28px;
  line-height: 1;
  color: #303133;
}

.summary-value--danger {
  color: #c45656;
}

.summary-value--up,
.text-up {
  color: #cf4444;
}

.summary-value--down,
.text-down {
  color: #2d8a57;
}

.panel {
  padding: 16px;
}

.filter-bar {
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}

.filter-item {
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 13px;
  white-space: nowrap;
}

.filter-select {
  width: 240px;
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

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .filter-item,
  .filter-select {
    width: 100%;
  }
}
</style>
