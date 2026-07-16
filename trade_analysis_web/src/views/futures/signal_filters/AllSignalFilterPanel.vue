<script lang="ts" setup>
import type {
  FutureAllContractSignalResult,
  FutureHoldingWarningSignalItem,
} from '@/api/modules'
import { formatDateTime } from '@/utils/date'
import { computed } from 'vue'
import { formatEmaTrendState } from './signalFilterLabels'

const props = defineProps<{
  result: FutureAllContractSignalResult | null
  loading: boolean
}>()

const interval = defineModel<number>('interval', { required: true })
defineEmits<{ query: [] }>()

const intervalOptions = [
  { label: '5 分钟', value: 300 },
  { label: '15 分钟', value: 900 },
  { label: '1 小时', value: 3600 },
  { label: '日线', value: 86400 },
]

type EntrySignal = FutureAllContractSignalResult['entry_signals'][number] & {
  continuousCount: number
}
type WarningSignal = FutureHoldingWarningSignalItem & {
  symbol: string
  exchange: string
  name: string
  interval: number
  continuousCount: number
}

const markContinuous = <T extends { date_time: string }>(
  signals: T[],
  keyOf: (signal: T) => string,
): Array<T & { continuousCount: number }> => {
  const grouped = new Map<string, T[]>()
  for (const signal of signals) {
    const group = grouped.get(keyOf(signal)) ?? []
    group.push(signal)
    grouped.set(keyOf(signal), group)
  }

  const marked: Array<T & { continuousCount: number }> = []
  for (const group of grouped.values()) {
    group.sort((first, second) => Date.parse(first.date_time) - Date.parse(second.date_time))
    let count = 1
    group.forEach((signal, index) => {
      if (index > 0) {
        const previousSignal = group[index - 1]
        if (previousSignal) {
          const gapSeconds = (Date.parse(signal.date_time) - Date.parse(previousSignal.date_time)) / 1000
          count = gapSeconds <= interval.value * 2 ? count + 1 : 1
        }
      }
      marked.push({ ...signal, continuousCount: count })
    })
  }
  return marked
}

const timeRows = computed(() => {
  if (!props.result) return []
  const entrySignals = markContinuous(props.result.entry_signals, (signal) => `${signal.symbol}|${signal.signal_type}`)
  const warningSignals = markContinuous(props.result.holding_warning_signals, (signal) => `${signal.symbol}|${signal.position_direction}`)
  const signalsByTime = new Map<string, EntrySignal[]>()
  const warningsByTime = new Map<string, WarningSignal[]>()
  for (const signal of entrySignals) {
    const values = signalsByTime.get(signal.date_time) ?? []
    values.push(signal)
    signalsByTime.set(signal.date_time, values)
  }
  for (const warning of warningSignals) {
    const values = warningsByTime.get(warning.date_time) ?? []
    values.push(warning)
    warningsByTime.set(warning.date_time, values)
  }
  const dateTimes = new Set(props.result.items.flatMap((item) => item.ema_trend_signals.map((signal) => signal.date_time)))
  return [...dateTimes]
    .sort((first, second) => Date.parse(second) - Date.parse(first))
    .map((dateTime) => ({ dateTime, signals: signalsByTime.get(dateTime) ?? [], warnings: warningsByTime.get(dateTime) ?? [] }))
})
</script>

<template>
  <section class="all-signals-panel">
    <header class="panel-header">
      <div>
        <h3>多品种信号预警</h3>
        <span>共 {{ result?.contract_count ?? 0 }} 个品种，入场 {{ result?.entry_signals.length ?? 0 }} 个，持仓预警 {{ result?.holding_warning_signals.length ?? 0 }} 个</span>
      </div>
      <div class="actions">
        <el-select v-model="interval" class="interval-select">
          <el-option v-for="item in intervalOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="$emit('query')">查询全部</el-button>
      </div>
    </header>
    <el-table v-loading="loading" :data="timeRows" size="small" border height="45rem" empty-text="暂无交易时间数据">
      <el-table-column label="时间" width="180"><template #default="{ row }">{{ formatDateTime(row.dateTime) }}</template></el-table-column>
      <el-table-column label="入场信号" min-width="420">
        <template #default="{ row }">
          <span v-if="!row.signals.length" class="empty-signal">无</span>
          <div v-else class="signal-list">
            <div v-for="signal in row.signals" :key="`${signal.symbol}-${signal.signal_type}`" :class="['signal-item', { continuous: signal.continuousCount >= 2 }]">
              {{ signal.name }}【{{ signal.signal_type === 'long' ? '多头' : '空头' }}｜{{ formatEmaTrendState(signal.ema_trend_state) }}｜ADX {{ Number(signal.adx).toFixed(2) }}<template v-if="signal.continuousCount >= 2">｜连续{{ signal.continuousCount }}次</template>】
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="持仓预警信号" min-width="380">
        <template #default="{ row }">
          <span v-if="!row.warnings.length" class="empty-signal">无</span>
          <div v-else class="signal-list">
            <div v-for="warning in row.warnings" :key="`${warning.symbol}-${warning.position_direction}`" :class="['warning-item', { continuous: warning.continuousCount >= 2 }]">
              {{ warning.name }}【{{ warning.position_direction === 'long' ? '多头持仓预警' : '空头持仓预警' }}｜{{ formatEmaTrendState(warning.ema_trend_state) }}｜MACD {{ warning.macd_signal_type === 'long' ? '多头' : '空头' }}<template v-if="warning.continuousCount >= 2">｜连续{{ warning.continuousCount }}次</template>】
            </div>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<style lang="less" scoped>
.all-signals-panel { padding: 16px; margin-bottom: 16px; background: #fff; border: 1px solid #ebeef5; border-radius: 8px; }
.panel-header, .actions { display: flex; align-items: center; }
.panel-header { justify-content: space-between; margin-bottom: 12px; }
.panel-header h3 { margin: 0 0 4px; }
.panel-header span { color: #909399; font-size: 13px; }
.actions { gap: 8px; }
.interval-select { width: 120px; }
.signal-list { display: flex; flex-direction: column; row-gap: .5rem; }
.signal-item, .warning-item { color: #303133; }
.continuous { color: #f56c6c; font-weight: 600; }
.empty-signal { color: #c0c4cc; }
</style>
