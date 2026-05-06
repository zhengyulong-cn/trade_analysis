<script lang="ts" setup>
import {
  getFutureContractList,
  getFutureDataApi,
  type FutureContract,
} from '@/api/modules'
import {
  DEFAULT_ANALYSIS_LIMIT,
  DEFAULT_HIGHER_SEGMENT_EMA_LENGTH,
  DEFAULT_HIGHER_SEGMENT_MIN_BARS,
  DEFAULT_SEGMENT_EMA_LENGTH,
  DEFAULT_SEGMENT_MIN_BARS,
  FIVE_MINUTE_INTERVAL_SECONDS,
  THIRTY_MINUTE_INTERVAL_SECONDS,
  analyzeOpenOpportunity,
  hasOpenOpportunity,
  type OpenOpportunityMatch,
  type OpenOpportunityResult,
  type OpenOpportunityType,
} from '@/strategy_core/local_ema_segment/outer/open_opportunity_analysis'
import type { BaseSegment, SegmentDirection } from '@/strategy_core/local_ema_segment/types'
import { formatDateTime as formatDateTimeByDayjs } from '@/utils/date'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

type ScopeValue = 'favorite' | 'all'
type ModeFilter = 'all' | OpenOpportunityType
type DirectionFilter = 'all' | SegmentDirection

type AnalysisRow = OpenOpportunityResult & {
  errorMessage?: string
}

type OpportunityTableRow = {
  contract: FutureContract
  match: OpenOpportunityMatch
}

const loading = ref(false)
const contracts = ref<FutureContract[]>([])
const rows = ref<AnalysisRow[]>([])
const scope = ref<ScopeValue>('favorite')
const modeFilter = ref<ModeFilter>('all')
const directionFilter = ref<DirectionFilter>('all')
const klineLimit = ref(DEFAULT_ANALYSIS_LIMIT)
const progressText = ref('')

const candidateContracts = computed(() => {
  const source = scope.value === 'favorite'
    ? contracts.value.filter((contract) => contract.is_favorite === 1)
    : contracts.value

  return [...source].sort((first, second) => first.symbol.localeCompare(second.symbol, 'zh-CN'))
})

const opportunityRows = computed<OpportunityTableRow[]>(() => {
  return rows.value.flatMap((row) => {
    if (!hasOpenOpportunity(row)) {
      return []
    }

    return row.matches.map((match) => ({
      contract: row.contract,
      match,
    }))
  })
})

const filteredOpportunityRows = computed(() => {
  return opportunityRows.value.filter((row) => {
    const matchesMode = modeFilter.value === 'all' || row.match.type === modeFilter.value
    const matchesDirection = directionFilter.value === 'all'
      || row.match.higherSegment.direction === directionFilter.value

    return matchesMode && matchesDirection
  })
})

const failedRows = computed(() => rows.value.filter((row) => row.errorMessage))

const modeOneCount = computed(() => {
  return opportunityRows.value.filter((row) => row.match.type === 'five_minute_against_higher').length
})

const modeTwoCount = computed(() => {
  return opportunityRows.value.filter((row) => row.match.type === 'thirty_minute_against_higher').length
})

const summary = computed(() => ({
  candidates: candidateContracts.value.length,
  opportunities: opportunityRows.value.length,
  modeOne: modeOneCount.value,
  modeTwo: modeTwoCount.value,
  failures: failedRows.value.length,
}))

const formatDirection = (direction?: SegmentDirection) => {
  if (direction === 'up') {
    return '向上'
  }

  if (direction === 'down') {
    return '向下'
  }

  return '未形成'
}

const getDirectionTagType = (direction?: SegmentDirection) => {
  if (direction === 'up') {
    return 'success'
  }

  if (direction === 'down') {
    return 'danger'
  }

  return 'info'
}

const formatInterval = (intervalSeconds: number) => {
  if (intervalSeconds === FIVE_MINUTE_INTERVAL_SECONDS) {
    return '5F'
  }

  if (intervalSeconds === THIRTY_MINUTE_INTERVAL_SECONDS) {
    return '30F'
  }

  return `${intervalSeconds / 60}F`
}

const formatSegmentTime = (value?: number) => {
  if (!value) {
    return '-'
  }

  return formatDateTimeByDayjs(value * 1000)
}

const formatSegmentRange = (segment: BaseSegment | null | undefined) => {
  if (!segment) {
    return '-'
  }

  return `${formatSegmentTime(segment.start.time)} 至 ${formatSegmentTime(segment.end.time)}`
}

const getOpportunityRowKey = (row: OpportunityTableRow) => {
  return `${row.contract.contract_id}-${row.match.type}-${row.match.baseSegment.start.time}-${row.match.higherSegment.start.time}`
}

const loadContracts = async () => {
  contracts.value = await getFutureContractList()
}

const createEmptyAnalysis = (contract: FutureContract): AnalysisRow => ({
  contract,
  errorMessage: 'K线数据获取或分析失败',
  fiveMinute: {
    barsCount: 0,
    baseSegmentCount: 0,
    higherSegmentCount: 0,
    latestBaseSegment: null,
    latestHigherSegment: null,
  },
  matches: [],
  thirtyMinute: {
    barsCount: 0,
    baseSegmentCount: 0,
    higherSegmentCount: 0,
    latestBaseSegment: null,
    latestHigherSegment: null,
  },
})

const analyzeContract = async (contract: FutureContract): Promise<AnalysisRow> => {
  try {
    const [fiveMinuteData, thirtyMinuteData] = await Promise.all([
      getFutureDataApi({
        symbol: contract.symbol,
        period: FIVE_MINUTE_INTERVAL_SECONDS,
        limit: klineLimit.value,
      }),
      getFutureDataApi({
        symbol: contract.symbol,
        period: THIRTY_MINUTE_INTERVAL_SECONDS,
        limit: klineLimit.value,
      }),
    ])

    return analyzeOpenOpportunity({
      contract,
      fiveMinuteKlines: fiveMinuteData.kLineList,
      thirtyMinuteKlines: thirtyMinuteData.kLineList,
      options: {
        base: {
          emaLength: DEFAULT_SEGMENT_EMA_LENGTH,
          minSegmentBars: DEFAULT_SEGMENT_MIN_BARS,
        },
        higher: {
          emaLength: DEFAULT_HIGHER_SEGMENT_EMA_LENGTH,
          minSegmentBars: DEFAULT_HIGHER_SEGMENT_MIN_BARS,
        },
      },
    })
  } catch {
    return createEmptyAnalysis(contract)
  }
}

const runAnalysis = async () => {
  if (!candidateContracts.value.length) {
    rows.value = []
    ElMessage.warning(scope.value === 'favorite' ? '暂无收藏合约可分析' : '暂无合约可分析')
    return
  }

  loading.value = true
  rows.value = []
  progressText.value = ''

  try {
    const nextRows: AnalysisRow[] = []

    for (let index = 0; index < candidateContracts.value.length; index += 1) {
      const contract = candidateContracts.value[index]
      if (!contract) {
        continue
      }

      progressText.value = `${index + 1}/${candidateContracts.value.length} ${contract.symbol}`
      nextRows.push(await analyzeContract(contract))
      rows.value = [...nextRows]
    }

    ElMessage.success(`分析完成，发现 ${opportunityRows.value.length} 个开仓机会`)
  } finally {
    loading.value = false
    progressText.value = ''
  }
}

const reloadAndAnalyze = async () => {
  loading.value = true
  try {
    await loadContracts()
  } catch {
    ElMessage.error('获取期货合约列表失败')
    return
  } finally {
    loading.value = false
  }

  await runAnalysis()
}

onMounted(() => {
  void reloadAndAnalyze()
})
</script>

<template>
  <div class="pageBox opportunity-analysis">
    <div class="toolbar">
      <div>
        <h2 class="title">开仓机会分析</h2>
        <p class="subtitle">模式①看 5F 内部线段反向，模式②看 30F 内部线段反向</p>
      </div>
      <div class="actions">
        <el-button :icon="Refresh" :loading="loading" @click="reloadAndAnalyze">刷新合约</el-button>
        <el-button type="primary" :icon="Search" :loading="loading" @click="runAnalysis">开始分析</el-button>
      </div>
    </div>

    <div class="filters">
      <el-segmented
        v-model="scope"
        :options="[
          { label: '收藏合约', value: 'favorite' },
          { label: '全部合约', value: 'all' },
        ]"
      />
      <el-segmented
        v-model="modeFilter"
        :options="[
          { label: '全部模式', value: 'all' },
          { label: '模式①', value: 'five_minute_against_higher' },
          { label: '模式②', value: 'thirty_minute_against_higher' },
        ]"
      />
      <el-segmented
        v-model="directionFilter"
        :options="[
          { label: '全部方向', value: 'all' },
          { label: '大级别向上', value: 'up' },
          { label: '大级别向下', value: 'down' },
        ]"
      />
      <el-input-number
        v-model="klineLimit"
        :min="120"
        :max="3000"
        :step="120"
        controls-position="right"
      />
      <span v-if="progressText" class="progress-text">{{ progressText }}</span>
    </div>

    <div class="summary-grid">
      <div class="summary-item">
        <span class="summary-label">分析合约</span>
        <strong>{{ summary.candidates }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">机会数量</span>
        <strong>{{ summary.opportunities }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">模式①</span>
        <strong>{{ summary.modeOne }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">模式②</span>
        <strong>{{ summary.modeTwo }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">异常数量</span>
        <strong>{{ summary.failures }}</strong>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="filteredOpportunityRows"
      border
      :row-key="getOpportunityRowKey"
      empty-text="暂无符合条件的开仓机会"
    >
      <el-table-column label="合约" min-width="150">
        <template #default="{ row }">
          <div class="contract-cell">
            <span class="contract-symbol">{{ row.contract.symbol }}</span>
            <span class="contract-name">{{ row.contract.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="模式" width="100">
        <template #default="{ row }">
          <el-tag type="warning">{{ row.match.modeName }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="周期" width="90">
        <template #default="{ row }">
          {{ formatInterval(row.match.intervalSeconds) }}
        </template>
      </el-table-column>
      <el-table-column label="大级别方向" width="130">
        <template #default="{ row }">
          <el-tag :type="getDirectionTagType(row.match.higherSegment.direction)">
            {{ formatDirection(row.match.higherSegment.direction) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="线段方向" width="120">
        <template #default="{ row }">
          <el-tag :type="getDirectionTagType(row.match.baseSegment.direction)">
            {{ formatDirection(row.match.baseSegment.direction) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开仓机会" min-width="230">
        <template #default="{ row }">
          {{ formatInterval(row.match.intervalSeconds) }} 线段与大级别线段方向相反
        </template>
      </el-table-column>
      <el-table-column label="大级别最新段" min-width="320">
        <template #default="{ row }">
          {{ formatSegmentRange(row.match.higherSegment) }}
        </template>
      </el-table-column>
      <el-table-column label="最新线段" min-width="320">
        <template #default="{ row }">
          {{ formatSegmentRange(row.match.baseSegment) }}
        </template>
      </el-table-column>
      <el-table-column label="K线/段数" width="150">
        <template #default="{ row }">
          {{ row.match.barsCount }} / {{ row.match.baseSegmentCount }} / {{ row.match.higherSegmentCount }}
        </template>
      </el-table-column>
    </el-table>

    <el-alert
      v-if="failedRows.length"
      class="failure-alert"
      type="warning"
      :closable="false"
      show-icon
      :title="`${failedRows.length} 个合约分析失败，可刷新后重试`"
    />
  </div>
</template>

<style lang="less" scoped>
.opportunity-analysis {
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

.actions,
.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filters {
  margin-bottom: 16px;
}

.progress-text {
  color: #606266;
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  min-height: 68px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.summary-label {
  color: #909399;
  font-size: 13px;
}

.summary-item strong {
  color: #303133;
  font-size: 22px;
  line-height: 1;
}

.contract-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.contract-symbol {
  font-weight: 600;
  color: #303133;
}

.contract-name {
  color: #909399;
  font-size: 12px;
}

.failure-alert {
  margin-top: 16px;
}

@media (max-width: 1024px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }
}

@media (max-width: 768px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .actions {
    justify-content: flex-start;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
