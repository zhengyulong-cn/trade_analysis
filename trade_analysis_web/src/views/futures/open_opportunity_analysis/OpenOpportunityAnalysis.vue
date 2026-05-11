<script lang="ts" setup>
import {
  getFutureOpportunityAnalysisAllApi,
  type FutureOpportunityAnalysisItem,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

const TEXT = {
  pageTitle: '开仓机会分析',
  pageSubtitle: '按 4H / 30F / 5F 结构、交易区间和动能状态汇总当前机会。',
  refresh: '刷新分析结果',
  symbolFilter: '合约筛选',
  segmentTypeFilter: '30F线段类型',
  allSymbols: '全部合约',
  allSegmentTypes: '全部类型',
  totalContracts: '合约总数',
  opportunityContracts: '机会合约数',
  longContracts: '做多视角',
  shortContracts: '做空视角',
  tableEmpty: '暂无开仓机会分析结果',
  contract: '合约',
  latestPrice: '最新价',
  direction4h: '4H方向',
  direction30f: '30F方向',
  segmentType: '30F线段类型',
  direction5f: '5F方向',
  mode: '模式',
  momentum30f: '30F动能判断',
  momentum5f: '5F动能判断',
  openSide: '操作视角',
  tradingRange: '30F交易区间',
  opportunity: '机会判断',
  unknown: '-',
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
    return '做多'
  }
  if (value === 'short') {
    return '做空'
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

const formatRangePosition = (value?: string | null) => {
  if (value === 'upper_third') {
    return '上1/3'
  }
  if (value === 'lower_third') {
    return '下1/3'
  }
  if (value === 'middle_third') {
    return '中1/3'
  }
  return TEXT.unknown
}

const formatPriceRange = (low?: number | null, high?: number | null) => {
  if (low === null || low === undefined || high === null || high === undefined) {
    return TEXT.unknown
  }
  return `${formatNumber(low)} ~ ${formatNumber(high)}`
}

const formatMode = (value?: string | null) => {
  if (value === 'mode_1') {
    return '模式一'
  }
  if (value === 'mode_2') {
    return '模式二'
  }
  if (value === 'mode_3') {
    return '模式三'
  }
  if (value === 'mode_4') {
    return '模式四'
  }
  return TEXT.unknown
}

const modeTagType = (value?: string | null) => {
  if (value === 'mode_1') {
    return 'danger'
  }
  if (value === 'mode_2') {
    return 'success'
  }
  if (value === 'mode_3') {
    return 'warning'
  }
  if (value === 'mode_4') {
    return 'info'
  }
  return ''
}

const formatTradingRangeState = (row: FutureOpportunityAnalysisItem) => {
  const rangeText = formatPriceRange(row.trading_range_bottom, row.trading_range_top)
  if (rangeText === TEXT.unknown) {
    return TEXT.unknown
  }
  const enteredText = row.is_in_30f_trading_range ? '已进入' : '未进入'
  const positionText = row.is_in_30f_trading_range ? ` / ${formatRangePosition(row.trading_range_position)}` : ''
  return `${rangeText} / ${enteredText}${positionText}`
}

const formatMomentumState = (checkDirection?: string | null, exhausted?: boolean | null) => {
  if (!checkDirection || exhausted === null || exhausted === undefined) {
    return TEXT.unknown
  }
  const checkText = checkDirection === 'up' ? '检查上涨段' : '检查下跌段'
  const stateText = exhausted ? '已衰竭' : '未衰竭'
  return `${checkText} / ${stateText}`
}

const formatOpportunityAction = (row: FutureOpportunityAnalysisItem) => {
  if (!row.has_opportunity || !row.opportunity_action) {
    return '不操作'
  }
  if (row.opportunity_action === 'open_long_wait_5f_down_end') {
    return '开多机会：等待5F下跌段结束'
  }
  if (row.opportunity_action === 'open_short_wait_5f_up_end') {
    return '开空机会：等待5F上涨段结束'
  }
  if (row.opportunity_action === 'open_long_follow_5f_up') {
    return '开多机会：顺5F上涨段参与'
  }
  if (row.opportunity_action === 'open_short_follow_5f_down') {
    return '开空机会：顺5F下跌段参与'
  }
  if (row.opportunity_action === 'open_long_reverse_5f_down_structure') {
    return '开多机会：逆5F下跌结构操作'
  }
  if (row.opportunity_action === 'open_short_reverse_5f_up_structure') {
    return '开空机会：逆5F上涨结构操作'
  }
  return '不操作'
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
      label: `${row.symbol} / ${row.name}`,
      value: row.symbol,
    })),
  ]
})

const totalContracts = computed(() => filteredRows.value.length)
const opportunityContracts = computed(() => filteredRows.value.filter((row) => row.has_opportunity).length)
const longContracts = computed(() => filteredRows.value.filter((row) => row.open_side === 'long').length)
const shortContracts = computed(() => filteredRows.value.filter((row) => row.open_side === 'short').length)

const loadData = async () => {
  loading.value = true
  try {
    const result = await getFutureOpportunityAnalysisAllApi()
    rows.value = [...result.items].sort((first, second) => {
      if (first.has_opportunity !== second.has_opportunity) {
        return first.has_opportunity ? -1 : 1
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
        <span class="summary-label">{{ TEXT.opportunityContracts }}</span>
        <strong class="summary-value summary-value--up">{{ opportunityContracts }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">{{ TEXT.longContracts }}</span>
        <strong class="summary-value">{{ longContracts }}</strong>
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

        <el-table-column prop="opportunity_mode" :label="TEXT.mode" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.opportunity_mode" :type="modeTagType(row.opportunity_mode)">
              {{ formatMode(row.opportunity_mode) }}
            </el-tag>
            <span v-else>{{ TEXT.unknown }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.tradingRange" min-width="210">
          <template #default="{ row }">
            {{ formatTradingRangeState(row) }}
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum30f" min-width="190">
          <template #default="{ row }">
            {{ formatMomentumState(row.current_30f_momentum_check_direction, row.current_30f_momentum_exhausted) }}
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum5f" min-width="190">
          <template #default="{ row }">
            {{ formatMomentumState(row.current_5f_momentum_check_direction, row.current_5f_momentum_exhausted) }}
          </template>
        </el-table-column>

        <el-table-column prop="open_side" :label="TEXT.openSide" width="100">
          <template #default="{ row }">
            <span :class="row.open_side === 'long' ? 'text-up' : row.open_side === 'short' ? 'text-down' : ''">
              {{ formatOpenSide(row.open_side) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.opportunity" min-width="220">
          <template #default="{ row }">
            {{ formatOpportunityAction(row) }}
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
