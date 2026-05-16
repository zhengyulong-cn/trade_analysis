<script lang="ts" setup>
import { getFutureOpportunityAnalysisAllApi, type FutureOpportunityAnalysisItem } from '@/api/modules'
import { useContractsStore } from '@/stores/contracts'
import {
  formatOpportunityAction,
  formatOpportunityDirection,
  formatOpportunityMode,
  formatOpportunityMomentumState,
  formatOpportunityNumber,
  formatOpportunityOpenSide,
  formatOpportunitySegmentType,
  formatOpportunityTradingRangeState,
  opportunityModeTagType,
  OPPORTUNITY_UNKNOWN_TEXT,
} from '@/utils/opportunity'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { computed, onMounted, ref } from 'vue'

const STORAGE_KEY = 'futures-open-opportunity-analysis-cache'

const TEXT = {
  pageTitle: '开仓机会分析',
  pageSubtitle: '按 4H / 30F / 5F 结构、交易区间和动能状态汇总当前机会。',
  refresh: '刷新分析结果',
  symbolFilter: '合约筛选',
  segmentTypeFilter: '30F线段类型',
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
  unknown: OPPORTUNITY_UNKNOWN_TEXT,
  loadError: '获取开仓机会分析失败',
} as const

const SEGMENT_TYPE_OPTIONS = [
  { label: TEXT.allSegmentTypes, value: '' },
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
]

interface OpportunityAnalysisCache {
  lastUpdatedAt: number
  analysisData: FutureOpportunityAnalysisItem[]
}

const contractsStore = useContractsStore()
const { contracts } = storeToRefs(contractsStore)

const rows = ref<FutureOpportunityAnalysisItem[]>([])
const loading = ref(false)
const selectedSymbols = ref<string[]>([])
const selectedSegmentType = ref('')
const only30fExhausted = ref(false)
const only5fExhausted = ref(false)
const onlyFavoriteContracts = ref(false)
const lastUpdatedAt = ref<number | null>(null)

const favoriteSymbols = computed(() => {
  return new Set(
    contracts.value.filter((contract) => contract.is_favorite === 1).map((contract) => contract.symbol),
  )
})

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

const filteredRows = computed(() => {
  return rows.value.filter((row) => {
    if (selectedSymbols.value.length > 0 && !selectedSymbols.value.includes(row.symbol)) {
      return false
    }
    if (selectedSegmentType.value && row.current_30f_segment_type !== selectedSegmentType.value) {
      return false
    }
    if (only30fExhausted.value && !row.current_30f_momentum_exhausted) {
      return false
    }
    if (only5fExhausted.value && !row.current_5f_momentum_exhausted) {
      return false
    }
    if (onlyFavoriteContracts.value && !favoriteSymbols.value.has(row.symbol)) {
      return false
    }
    return true
  })
})

const symbolOptions = computed(() => {
  return rows.value.map((row) => ({
    label: `${row.symbol} / ${row.name}`,
    value: row.symbol,
  }))
})

const totalContracts = computed(() => filteredRows.value.length)
const opportunityContracts = computed(() => filteredRows.value.filter((row) => row.has_opportunity).length)
const longContracts = computed(() => filteredRows.value.filter((row) => row.open_side === 'long').length)
const shortContracts = computed(() => filteredRows.value.filter((row) => row.open_side === 'short').length)
const lastUpdatedAtText = computed(() => {
  if (!lastUpdatedAt.value) {
    return TEXT.unknown
  }
  return new Date(lastUpdatedAt.value).toLocaleString('zh-CN', {
    hour12: false,
  })
})

const sortRows = (items: FutureOpportunityAnalysisItem[]) => {
  return [...items].sort((first, second) => {
    if (first.has_opportunity !== second.has_opportunity) {
      return first.has_opportunity ? -1 : 1
    }
    return first.symbol.localeCompare(second.symbol, 'zh-CN')
  })
}

const loadCache = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return
    }
    const parsed = JSON.parse(raw) as Partial<OpportunityAnalysisCache>
    if (!Array.isArray(parsed.analysisData) || typeof parsed.lastUpdatedAt !== 'number') {
      return
    }
    rows.value = sortRows(parsed.analysisData as FutureOpportunityAnalysisItem[])
    lastUpdatedAt.value = parsed.lastUpdatedAt
  } catch {
    localStorage.removeItem(STORAGE_KEY)
  }
}

const saveCache = (items: FutureOpportunityAnalysisItem[], updatedAt: number) => {
  const payload: OpportunityAnalysisCache = {
    lastUpdatedAt: updatedAt,
    analysisData: items,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}

const loadData = async () => {
  loading.value = true
  try {
    const result = await getFutureOpportunityAnalysisAllApi()
    const sortedRows = sortRows(result.items)
    const updatedAt = Date.now()
    rows.value = sortedRows
    lastUpdatedAt.value = updatedAt
    saveCache(sortedRows, updatedAt)
  } catch (error) {
    rows.value = []
    ElMessage.error(extractErrorMessage(error, TEXT.loadError))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCache()
})
</script>

<template>
  <div class="pageBox opportunity-analysis">
    <header class="page-header">
      <div>
        <h2 class="title">{{ TEXT.pageTitle }}</h2>
        <p class="subtitle">{{ TEXT.pageSubtitle }}</p>
      </div>
      <div class="header-actions">
        <span class="last-updated">最后更新：{{ lastUpdatedAtText }}</span>
        <el-button type="primary" :loading="loading" @click="loadData">
          {{ TEXT.refresh }}
        </el-button>
      </div>
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
        <div class="filter-item filter-item--checkbox">
          <el-checkbox v-model="onlyFavoriteContracts">仅看收藏合约</el-checkbox>
        </div>
        <div class="filter-item">
          <span class="filter-label">{{ TEXT.symbolFilter }}</span>
          <el-select
            v-model="selectedSymbols"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            clearable
            class="filter-select"
          >
            <el-option
              v-for="option in symbolOptions"
              :key="option.value"
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

        <div class="filter-item filter-item--checkbox">
          <el-checkbox v-model="only30fExhausted">仅看30F已衰竭</el-checkbox>
        </div>

        <div class="filter-item filter-item--checkbox">
          <el-checkbox v-model="only5fExhausted">仅看5F已衰竭</el-checkbox>
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
            {{ formatOpportunityNumber(row.latest_price) }}
          </template>
        </el-table-column>

        <el-table-column prop="current_4h_segment_direction" :label="TEXT.direction4h" width="100">
          <template #default="{ row }">
            <span :class="row.current_4h_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatOpportunityDirection(row.current_4h_segment_direction) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="current_30f_segment_direction" :label="TEXT.direction30f" width="100">
          <template #default="{ row }">
            <span :class="row.current_30f_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatOpportunityDirection(row.current_30f_segment_direction) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="current_30f_segment_type" :label="TEXT.segmentType" min-width="140">
          <template #default="{ row }">
            {{ formatOpportunitySegmentType(row.current_30f_segment_type) }}
          </template>
        </el-table-column>

        <el-table-column prop="current_5f_segment_direction" :label="TEXT.direction5f" width="100">
          <template #default="{ row }">
            <span :class="row.current_5f_segment_direction === 'up' ? 'text-up' : 'text-down'">
              {{ formatOpportunityDirection(row.current_5f_segment_direction) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="opportunity_mode" :label="TEXT.mode" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.opportunity_mode" :type="opportunityModeTagType(row.opportunity_mode)">
              {{ formatOpportunityMode(row.opportunity_mode) }}
            </el-tag>
            <span v-else>{{ TEXT.unknown }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.tradingRange" min-width="210">
          <template #default="{ row }">
            {{ formatOpportunityTradingRangeState(row) }}
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum30f" min-width="190">
          <template #default="{ row }">
            <span :class="{ 'momentum-exhausted': row.current_30f_momentum_exhausted }">
              {{ formatOpportunityMomentumState(row.current_30f_momentum_check_direction, row.current_30f_momentum_exhausted) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="TEXT.momentum5f" min-width="190">
          <template #default="{ row }">
            <span :class="{ 'momentum-exhausted': row.current_5f_momentum_exhausted }">
              {{ formatOpportunityMomentumState(row.current_5f_momentum_check_direction, row.current_5f_momentum_exhausted) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="open_side" :label="TEXT.openSide" width="100">
          <template #default="{ row }">
            <span :class="row.open_side === 'long' ? 'text-up' : row.open_side === 'short' ? 'text-down' : ''">
              {{ formatOpportunityOpenSide(row.open_side) }}
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
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
  font-size: 12px;
}

.last-updated {
  font-size: 12px;
  color: #909399;
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
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  column-gap: 16px;
  padding: 16px;
}

.summary-label {
  display: block;
  font-size: 12px;
}

.summary-value {
  display: block;
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

.momentum-exhausted {
  color: #dc2626;
  font-weight: 700;
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

.filter-item--checkbox {
  min-height: 32px;
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

  .header-actions {
    width: 100%;
    justify-content: space-between;
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
