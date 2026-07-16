<script lang="ts" setup>
import type { FutureContractSignalResult, FutureContract } from '@/api/modules'
import { formatDateTime } from '@/utils/date'

defineProps<{
  contracts: FutureContract[]
  result: FutureContractSignalResult | null
  loading: boolean
}>()

const symbol = defineModel<string>('symbol', { required: true })
const interval = defineModel<number>('interval', { required: true })
defineEmits<{ query: [] }>()

const intervalOptions = [
  { label: '5 分钟', value: 300 },
  { label: '15 分钟', value: 900 },
  { label: '1 小时', value: 3600 },
  { label: '日线', value: 86400 },
]
</script>

<template>
  <div class="summary">
    <div class="title">{{ result ? `${result.symbol} · ${result.name}　共扫描 ${result.bar_count} 根，入场信号 ${result.entry_signals.length} 个` : '请选择合约并查询信号' }}</div>
    <div class="filters">
      <el-select v-model="symbol" filterable placeholder="选择合约" class="symbol-select">
        <el-option v-for="contract in contracts" :key="contract.contract_id" :label="contract.symbol" :value="contract.symbol" />
      </el-select>
      <el-select v-model="interval" class="interval-select">
        <el-option v-for="item in intervalOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button type="primary" :loading="loading" @click="$emit('query')">查询</el-button>
    </div>
  </div>

  <div class="grid">
    <section class="panel">
      <h3>MACD 信号（{{ result?.macd_signals.length ?? 0 }}）</h3>
      <el-table :data="result?.macd_signals ?? []" size="small" border height="40rem">
        <el-table-column label="时间" width="150"><template #default="{ row }">{{ formatDateTime(row.date_time) }}</template></el-table-column>
        <el-table-column label="信号"><template #default="{ row }">{{ row.signal_type === 'long' ? '多头' : '空头' }}</template></el-table-column>
      </el-table>
    </section>
    <section class="panel">
      <h3>ADX 信号（{{ result?.adx_signals.length ?? 0 }}）</h3>
      <el-table :data="result?.adx_signals ?? []" size="small" border height="40rem">
        <el-table-column label="时间" width="150"><template #default="{ row }">{{ formatDateTime(row.date_time) }}</template></el-table-column>
        <el-table-column label="ADX" min-width="80"><template #default="{ row }">{{ Number(row.adx).toFixed(2) }}</template></el-table-column>
        <el-table-column label="斜率" min-width="80"><template #default="{ row }">{{ row.adx_slope === 'negative' ? '小于0' : '大于等于0' }}</template></el-table-column>
        <el-table-column label="阈值" width="80"><template #default="{ row }">{{ row.above_threshold ? '高于' : '低于' }}</template></el-table-column>
      </el-table>
    </section>
    <section class="panel">
      <h3>入场信号（{{ result?.entry_signals.length ?? 0 }}）</h3>
      <el-table :data="result?.entry_signals ?? []" size="small" border height="40rem">
        <el-table-column label="MACD 信号时间" min-width="150"><template #default="{ row }">{{ formatDateTime(row.date_time) }}</template></el-table-column>
        <el-table-column label="MACD 信号" width="80"><template #default="{ row }">{{ row.signal_type === 'long' ? '多头' : '空头' }}</template></el-table-column>
        <el-table-column label="ADX 信号时间" min-width="150"><template #default="{ row }">{{ formatDateTime(row.adx_signal_date_time) }}</template></el-table-column>
        <el-table-column label="ADX" min-width="80"><template #default="{ row }">{{ Number(row.adx).toFixed(2) }}</template></el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style lang="less" scoped>
.symbol-select { width: 180px; }
.interval-select { width: 120px; }
.summary { padding: 12px 16px; margin-bottom: 16px; background: #fff; border: 1px solid #ebeef5; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; }
.title { color: #909399; font-size: 13px; }
.filters { display: flex; column-gap: .5rem; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.panel { padding: 16px; background: #fff; border: 1px solid #ebeef5; border-radius: 8px; }
.panel h3 { margin: 0 0 12px; font-size: 16px; }
@media (max-width: 1400px) { .grid { grid-template-columns: 1fr; } }
</style>
