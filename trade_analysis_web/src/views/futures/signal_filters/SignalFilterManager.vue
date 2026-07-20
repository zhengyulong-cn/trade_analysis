<script lang="ts" setup>
import {
  getAllFutureSignalsApi,
  getFutureContractList,
  getFutureSignalsApi,
  type FutureAllContractSignalResult,
  type FutureContract,
  type FutureContractSignalResult,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AllSignalFilterPanel from './AllSignalFilterPanel.vue'
import SignalFilterResultPanel from './SignalFilterResultPanel.vue'

const contracts = ref<FutureContract[]>([])
const symbol = ref('')
const interval = ref(300)
const loading = ref(false)
const result = ref<FutureContractSignalResult | null>(null)
const allInterval = ref(300)
const allSymbols = ref<string[]>([])
const allLoading = ref(false)
const allResult = ref<FutureAllContractSignalResult | null>(null)
const autoRefreshing = ref(false)
const remainingSeconds = ref(0)
let refreshTimer: ReturnType<typeof setTimeout> | undefined
let countdownTimer: ReturnType<typeof setInterval> | undefined

const loadAllSignals = async () => {
  allLoading.value = true
  try {
    allResult.value = await getAllFutureSignalsApi({ interval: allInterval.value, limit: 50 })
  } catch {
    allResult.value = null
    ElMessage.error('加载全品种信号失败')
  } finally {
    allLoading.value = false
  }
}

const scheduleAutoRefresh = () => {
  if (!autoRefreshing.value) return
  remainingSeconds.value = 5 * 60
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    remainingSeconds.value = Math.max(0, remainingSeconds.value - 1)
  }, 1000)
  refreshTimer = setTimeout(async () => {
    if (countdownTimer) clearInterval(countdownTimer)
    await loadAllSignals()
    scheduleAutoRefresh()
  }, 5 * 60 * 1000)
}

const handleAutoRefreshChange = async (enabled: boolean) => {
  if (refreshTimer) clearTimeout(refreshTimer)
  if (countdownTimer) clearInterval(countdownTimer)
  autoRefreshing.value = enabled
  if (!enabled) {
    remainingSeconds.value = 0
    return
  }
  scheduleAutoRefresh()
  await loadAllSignals()
}

const loadSignals = async () => {
  if (!symbol.value) return
  loading.value = true
  try {
    result.value = await getFutureSignalsApi({ symbol: symbol.value, interval: interval.value, limit: 50 })
  } catch {
    result.value = null
    ElMessage.error('加载信号失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    contracts.value = await getFutureContractList()
    allSymbols.value = contracts.value.map((contract) => contract.symbol)
    symbol.value = contracts.value[0]?.symbol ?? ''
    await loadSignals()
    await loadAllSignals()
  } catch {
    ElMessage.error('加载合约失败')
  }
})

onBeforeUnmount(() => {
  if (refreshTimer) clearTimeout(refreshTimer)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<template>
  <div class="pageBox signal-page">
    <header class="page-header">
      <h2>信号筛选器</h2>
      <p>单个品种最近 50 根 K 线信号</p>
    </header>
    <AllSignalFilterPanel
      v-model:interval="allInterval"
      v-model:symbols="allSymbols"
      v-model:auto-refreshing="autoRefreshing"
      :contracts="contracts"
      :result="allResult"
      :loading="allLoading"
      :remaining-seconds="remainingSeconds"
      @query="loadAllSignals"
      @update:auto-refreshing="handleAutoRefreshChange"
    />
    <SignalFilterResultPanel
      v-model:symbol="symbol"
      v-model:interval="interval"
      :contracts="contracts"
      :result="result"
      :loading="loading"
      @query="loadSignals"
    />
  </div>
</template>

<style lang="less" scoped>
.signal-page { padding: 16px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0; }
.page-header p { margin-bottom: 0; color: #909399; font-size: 13px; }
</style>
