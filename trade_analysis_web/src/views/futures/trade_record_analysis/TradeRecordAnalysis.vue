<script lang="ts" setup>
import {
  getFutureContractList,
  getTradeRecordAnalysisApi,
  type FutureContract,
  type TradeRecordAnalysisParams,
  type TradeRecordAnalysisPeriod,
  type TradeRecordAnalysisPeriodItem,
  type TradeRecordAnalysisResult,
  type TradeRecordAnalysisLossStreakItem,
  type TradeRecordOpenDirection,
  type TradeRecordOpenSignal,
  type TradeRecordSegmentType,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'

interface AnalysisFilters {
  period_type: TradeRecordAnalysisPeriod
  contract: string
  open_direction: '' | TradeRecordOpenDirection
  segment_type: '' | TradeRecordSegmentType
  open_signal: '' | TradeRecordOpenSignal
  open_time_range: string[]
}

const segmentTypeOptions: Array<{ label: string; value: TradeRecordSegmentType }> = [
  { label: '趋势推动段', value: 'trend_push' },
  { label: '趋势回调段', value: 'trend_pullback' },
  { label: '区间内部段', value: 'range_internal' },
  { label: '（假突破）回调转区间段', value: 'false_break_range_transition' },
  { label: '（真突破）区间转推动段', value: 'true_break_trend_push_transition' },
]

const openDirectionOptions: Array<{ label: string; value: TradeRecordOpenDirection }> = [
  { label: '多单', value: 'long' },
  { label: '空单', value: 'short' },
]

const openSignalOptions: Array<{ label: string; value: TradeRecordOpenSignal }> = [
  { label: 'EMA20阻力+站稳关键位', value: 'ema20_resistance_key_level_confirmed' },
  { label: 'EMA120阻力+头肩顶/头肩底', value: 'ema120_resistance_head_shoulders' },
  { label: 'EMA120阻力+三推楔形', value: 'ema120_resistance_three_push_wedge' },
  { label: 'EMA120阻力+突破交易区间然后回拉', value: 'ema120_resistance_range_break_pullback' },
  { label: '区间上下轨附近+两次以上尝试突破受阻', value: 'range_edge_multiple_breakout_failures' },
  { label: '真突破+反包', value: 'real_breakout_with_engulfing' },
  { label: '不符合开仓信号', value: 'not_matching_open_signal' },
]

const riskFlagLabelMap: Record<string, { label: string; type: 'info' | 'warning' | 'danger' }> = {
  high_frequency: { label: '高频交易', type: 'danger' },
  win_rate_down: { label: '胜率下降', type: 'warning' },
  execution_worse: { label: '执行变差', type: 'danger' },
}

const loading = ref(false)
const contracts = ref<FutureContract[]>([])
const analysis = ref<TradeRecordAnalysisResult | null>(null)
const activeBreakdownTab = ref('signal')

const filters = reactive<AnalysisFilters>({
  period_type: 'half_month',
  contract: '',
  open_direction: '',
  segment_type: '',
  open_signal: '',
  open_time_range: [],
})

const toNumber = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  return Number(value)
}

const formatNumber = (value?: number | string | null, fractionDigits = 2) => {
  const numericValue = toNumber(value)
  if (numericValue === null || Number.isNaN(numericValue)) {
    return '-'
  }
  return numericValue.toLocaleString('zh-CN', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

const formatInteger = (value?: number | string | null) => formatNumber(value, 0)

const formatPercent = (value?: number | null) => {
  if (value === null || value === undefined) {
    return '-'
  }
  return `${(value * 100).toFixed(1)}%`
}

const formatChange = (value?: number | string | null, fractionDigits = 2) => {
  const numericValue = toNumber(value)
  if (numericValue === null || Number.isNaN(numericValue)) {
    return '-'
  }
  const prefix = numericValue > 0 ? '+' : ''
  return `${prefix}${formatNumber(numericValue, fractionDigits)}`
}

const formatPercentChange = (value?: number | null) => {
  if (value === null || value === undefined) {
    return '-'
  }
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${(value * 100).toFixed(1)}%`
}

const getChangeClass = (value?: number | string | null) => {
  const numericValue = toNumber(value)
  if (numericValue === null || Number.isNaN(numericValue) || numericValue === 0) {
    return ''
  }
  return numericValue > 0 ? 'value-positive' : 'value-negative'
}

const buildAnalysisParams = (): TradeRecordAnalysisParams => ({
  period_type: filters.period_type,
  contract: filters.contract.trim() || undefined,
  open_direction: filters.open_direction || undefined,
  segment_type: filters.segment_type || undefined,
  open_signal: filters.open_signal || undefined,
  open_time_start: filters.open_time_range[0] || undefined,
  open_time_end: filters.open_time_range[1] || undefined,
})

const loadContracts = async () => {
  try {
    contracts.value = await getFutureContractList()
  } catch {
    ElMessage.error('获取合约列表失败')
  }
}

const loadAnalysis = async () => {
  loading.value = true
  try {
    analysis.value = await getTradeRecordAnalysisApi(buildAnalysisParams())
  } catch {
    ElMessage.error('获取交易分析失败')
  } finally {
    loading.value = false
  }
}

const handleResetFilters = async () => {
  filters.period_type = 'half_month'
  filters.contract = ''
  filters.open_direction = ''
  filters.segment_type = ''
  filters.open_signal = ''
  filters.open_time_range = []
  await loadAnalysis()
}

const getRiskFlags = (row: TradeRecordAnalysisPeriodItem) => {
  return row.risk_flags.map((flag) => riskFlagLabelMap[flag] ?? { label: flag, type: 'info' as const })
}

const getCurrentBreakdownData = () => {
  if (!analysis.value) {
    return []
  }
  if (activeBreakdownTab.value === 'contract') {
    return analysis.value.by_contract
  }
  if (activeBreakdownTab.value === 'direction') {
    return analysis.value.by_direction
  }
  if (activeBreakdownTab.value === 'segment') {
    return analysis.value.by_segment_type
  }
  return analysis.value.by_open_signal
}

const formatLossStreakRange = (row: TradeRecordAnalysisLossStreakItem) => {
  if (row.start_period_label === row.end_period_label) {
    return row.start_period_label
  }
  return `${row.start_period_label} ~ ${row.end_period_label}`
}

void loadContracts()
void loadAnalysis()
</script>

<template>
  <div class="pageBox trade-record-analysis">
    <div class="toolbar">
      <div>
        <h2 class="title">交易分析</h2>
        <p class="subtitle">基于已平仓交易，观察盈亏、胜率、频率和开仓信号执行情况</p>
      </div>
    </div>

    <div class="filter-panel">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="统计周期">
          <el-radio-group v-model="filters.period_type" @change="loadAnalysis">
            <el-radio-button label="day">按日</el-radio-button>
            <el-radio-button label="week">按周</el-radio-button>
            <el-radio-button label="half_month">按半月</el-radio-button>
            <el-radio-button label="month">按月</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="合约">
          <el-select v-model="filters.contract" filterable clearable placeholder="全部" style="width: 160px">
            <el-option
              v-for="contractItem in contracts"
              :key="contractItem.contract_id"
              :label="contractItem.symbol"
              :value="contractItem.symbol"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓方向">
          <el-select v-model="filters.open_direction" clearable placeholder="全部" style="width: 120px">
            <el-option
              v-for="option in openDirectionOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="30F线段类型">
          <el-select v-model="filters.segment_type" clearable placeholder="全部" style="width: 180px">
            <el-option
              v-for="option in segmentTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开仓信号">
          <el-select v-model="filters.open_signal" clearable placeholder="全部" style="width: 260px">
            <el-option
              v-for="option in openSignalOptions"
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
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadAnalysis">查询</el-button>
          <el-button @click="handleResetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <template v-if="analysis">
      <div class="summary-grid">
        <div class="metric-item">
          <span class="metric-label">已平仓交易数</span>
          <strong class="metric-value">{{ formatInteger(analysis.summary.trade_count) }}</strong>
        </div>
        <div class="metric-item">
          <span class="metric-label">净盈亏</span>
          <strong class="metric-value" :class="getChangeClass(analysis.summary.net_pnl)">
            {{ formatNumber(analysis.summary.net_pnl) }}
          </strong>
        </div>
        <div class="metric-item">
          <span class="metric-label">胜率</span>
          <strong class="metric-value">{{ formatPercent(analysis.summary.win_rate) }}</strong>
        </div>
        <div class="metric-item">
          <span class="metric-label">日均交易数</span>
          <strong class="metric-value">{{ formatNumber(analysis.summary.avg_trades_per_day) }}</strong>
        </div>
        <div class="metric-item">
          <span class="metric-label">信号覆盖率</span>
          <strong class="metric-value">{{ formatPercent(analysis.summary.signal_coverage_rate) }}</strong>
        </div>
        <div class="metric-item">
          <span class="metric-label">违规占比</span>
          <strong class="metric-value">{{ formatPercent(analysis.summary.invalid_signal_rate) }}</strong>
        </div>
      </div>

      <section class="analysis-section">
        <div class="section-header">
          <h3>周期表现</h3>
        </div>
        <el-table v-loading="loading" :data="analysis.period_series" border row-key="period_label" max-height="30rem">
          <el-table-column prop="period_label" label="周期" min-width="150" fixed="left" />
          <el-table-column prop="trade_count" label="交易数" width="90" align="right" />
          <el-table-column prop="total_lots" label="手数" width="90" align="right" />
          <el-table-column prop="net_pnl" label="净盈亏" width="120" align="right">
            <template #default="{ row }">
              <span :class="getChangeClass(row.net_pnl)">{{ formatNumber(row.net_pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="win_rate" label="胜率" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.win_rate) }}</template>
          </el-table-column>
          <el-table-column prop="avg_net_pnl" label="平均净盈亏" width="120" align="right">
            <template #default="{ row }">{{ formatNumber(row.avg_net_pnl) }}</template>
          </el-table-column>
          <el-table-column prop="empty_signal_count" label="空信号" width="90" align="right" />
          <el-table-column prop="invalid_signal_count" label="不符合信号" width="110" align="right" />
          <el-table-column prop="valid_signal_count" label="有效信号" width="100" align="right" />
          <el-table-column prop="signal_coverage_rate" label="覆盖率" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.signal_coverage_rate) }}</template>
          </el-table-column>
          <el-table-column prop="invalid_signal_rate" label="违规占比" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.invalid_signal_rate) }}</template>
          </el-table-column>
          <el-table-column prop="trade_count_change" label="交易数变化" width="110" align="right">
            <template #default="{ row }">{{ formatChange(row.trade_count_change, 0) }}</template>
          </el-table-column>
          <el-table-column prop="win_rate_change" label="胜率变化" width="110" align="right">
            <template #default="{ row }">{{ formatPercentChange(row.win_rate_change) }}</template>
          </el-table-column>
          <el-table-column label="状态提示" min-width="220">
            <template #default="{ row }">
              <div v-if="row.risk_flags.length" class="risk-tags">
                <el-tag
                  v-for="flag in getRiskFlags(row)"
                  :key="flag.label"
                  :type="flag.type"
                  size="small"
                >
                  {{ flag.label }}
                </el-tag>
              </div>
              <span v-else class="empty-text">正常</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="filters.period_type === 'day'" class="analysis-section">
        <div class="section-header">
          <h3>分组归因</h3>
          <el-tabs v-model="activeBreakdownTab" class="breakdown-tabs">
            <el-tab-pane label="开仓信号" name="signal" />
            <el-tab-pane label="30F线段" name="segment" />
            <el-tab-pane label="开仓方向" name="direction" />
            <el-tab-pane label="合约" name="contract" />
          </el-tabs>
        </div>
        <el-table :data="getCurrentBreakdownData()" border row-key="label">
          <el-table-column prop="label" label="分组" min-width="220" />
          <el-table-column prop="trade_count" label="交易数" width="90" align="right" />
          <el-table-column prop="total_lots" label="手数" width="90" align="right" />
          <el-table-column prop="net_pnl" label="净盈亏" width="120" align="right">
            <template #default="{ row }">
              <span :class="getChangeClass(row.net_pnl)">{{ formatNumber(row.net_pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="win_rate" label="胜率" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.win_rate) }}</template>
          </el-table-column>
          <el-table-column prop="avg_net_pnl" label="平均净盈亏" width="120" align="right">
            <template #default="{ row }">{{ formatNumber(row.avg_net_pnl) }}</template>
          </el-table-column>
          <el-table-column prop="signal_coverage_rate" label="覆盖率" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.signal_coverage_rate) }}</template>
          </el-table-column>
          <el-table-column prop="invalid_signal_rate" label="违规占比" width="100" align="right">
            <template #default="{ row }">{{ formatPercent(row.invalid_signal_rate) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="analysis-section">
        <div class="section-header">
          <h3>连续亏损</h3>
        </div>
        <div class="risk-grid">
          <div>
            <h4>连续亏损时间区间</h4>
            <el-table :data="analysis.continuous_loss_periods" border size="small" max-height="18rem">
              <el-table-column label="区间" min-width="180">
                <template #default="{ row }">
                  {{ formatLossStreakRange(row) }}
                </template>
              </el-table-column>
              <el-table-column prop="streak_length" label="连续数" width="90" align="right" />
              <el-table-column prop="net_pnl" label="净盈亏" width="110" align="right">
                <template #default="{ row }">{{ formatNumber(row.net_pnl) }}</template>
              </el-table-column>
            </el-table>
          </div>
          <div>
            <h4>高频交易周期</h4>
            <el-table :data="analysis.high_frequency_periods" border size="small" max-height="18rem">
              <el-table-column prop="period_label" label="周期" min-width="140" />
              <el-table-column prop="trade_count" label="交易数" width="90" align="right" />
            </el-table>
          </div>
          <div>
            <h4>执行变差周期</h4>
            <el-table :data="analysis.execution_worse_periods" border size="small" max-height="18rem">
              <el-table-column prop="period_label" label="周期" min-width="140" />
              <el-table-column prop="invalid_signal_rate" label="违规占比" width="100" align="right">
                <template #default="{ row }">{{ formatPercent(row.invalid_signal_rate) }}</template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style lang="less" scoped>
.trade-record-analysis {
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

.filter-panel,
.analysis-section {
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-item {
  padding: 14px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.metric-label {
  display: block;
  margin-bottom: 8px;
  color: #909399;
  font-size: 12px;
}

.metric-value {
  display: block;
  color: #303133;
  font-size: 20px;
  line-height: 1.2;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.section-header h3,
.risk-grid h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.breakdown-tabs {
  margin-bottom: -12px;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  padding-bottom: 16px;
}

.risk-grid h4 {
  margin-bottom: 10px;
}

.risk-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-text {
  color: #c0c4cc;
}

.value-positive {
  color: #f56c6c;
  font-weight: 600;
}

.value-negative {
  color: #67c23a;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .risk-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
