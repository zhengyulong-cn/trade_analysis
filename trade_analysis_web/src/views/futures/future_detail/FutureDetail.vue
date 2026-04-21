<script lang="ts" setup>
import KLineSection from '@/components/charts/KLineSection.vue'
import { getFutureContractList, getFutureDataApi, type FutureContract, type FutureKlineData } from '@/api/modules'
import { ElMessage } from 'element-plus'
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { computed, onMounted, ref, watch } from 'vue'

const DEFAULT_PERIOD = 60 * 5
const PAGE_TITLE = '\u671f\u8d27 K \u7ebf'
const PAGE_SUBTITLE = '\u9009\u62e9\u5408\u7ea6\u548c\u5468\u671f\uff0c\u67e5\u770b\u5bf9\u5e94\u7684 K \u7ebf\u8d70\u52bf\u3002'
const CONTRACT_PLACEHOLDER = '\u8bf7\u9009\u62e9\u5408\u7ea6'
const CONTRACT_LIST_ERROR = '\u83b7\u53d6\u5408\u7ea6\u5217\u8868\u5931\u8d25'
const KLINE_DATA_ERROR = '\u83b7\u53d6 K \u7ebf\u6570\u636e\u5931\u8d25'
const EMPTY_DESCRIPTION = '\u5f53\u524d\u6761\u4ef6\u4e0b\u6682\u65e0 K \u7ebf\u6570\u636e'
const UNAVAILABLE_DESCRIPTION = '\u8bf7\u5148\u5728\u5408\u7ea6\u7ba1\u7406\u4e2d\u521b\u5efa\u671f\u8d27\u5408\u7ea6'
const LABEL_OPEN = '\u5f00\u76d8'
const LABEL_CLOSE = '\u6536\u76d8'
const LABEL_HIGH = '\u6700\u9ad8'
const LABEL_LOW = '\u6700\u4f4e'

const PERIOD_OPTIONS = [
  { label: '5F', value: DEFAULT_PERIOD },
  { label: '30F', value: 60 * 30 },
  { label: '4H', value: 60 * 60 * 4 },
]

const createEmptyChartData = (): FutureKlineData => ({
  contract_id: 0,
  symbol: '',
  exchange: '',
  name: '',
  kline_data: [],
  kLineList: [],
})

const contracts = ref<FutureContract[]>([])
const selectedSymbol = ref('')
const selectedPeriod = ref(DEFAULT_PERIOD)
const contractsLoading = ref(false)
const chartLoading = ref(false)
const chartData = ref<FutureKlineData>(createEmptyChartData())
const activeKLineBar = ref<FutureKlineData['kLineList'][number] | null>(null)

const hasContracts = computed(() => contracts.value.length > 0)
const contractOptions = computed(() => {
  return contracts.value.map((contract) => ({
    label: `${contract.symbol} \u00b7 ${contract.name}`,
    value: contract.symbol,
    description: contract.name,
  }))
})
const latestBar = computed(() => {
  return chartData.value.kLineList[chartData.value.kLineList.length - 1]
})
const summaryBar = computed(() => {
  return activeKLineBar.value ?? latestBar.value
})
const summaryTone = computed<'up' | 'down' | 'neutral'>(() => {
  const bar = summaryBar.value

  if (!bar) {
    return 'neutral'
  }

  if (bar.close > bar.open) {
    return 'up'
  }

  if (bar.close < bar.open) {
    return 'down'
  }

  return 'neutral'
})
const summaryItems = computed(() => {
  return [
    {
      label: LABEL_OPEN,
      value: formatPrice(summaryBar.value?.open),
      tone: summaryTone.value,
    },
    {
      label: LABEL_CLOSE,
      value: formatPrice(summaryBar.value?.close),
      tone: summaryTone.value,
    },
    {
      label: LABEL_HIGH,
      value: formatPrice(summaryBar.value?.high),
      tone: summaryTone.value,
    },
    {
      label: LABEL_LOW,
      value: formatPrice(summaryBar.value?.low),
      tone: summaryTone.value,
    },
  ]
})
const chartOptions = computed<DeepPartial<ChartOptions>>(() => ({
  grid: {
    vertLines: { color: '#f0f2f5' },
    horzLines: { color: '#f0f2f5' },
  },
  rightPriceScale: {
    borderColor: '#ebeef5',
  },
  timeScale: {
    borderColor: '#ebeef5',
    timeVisible: true,
    secondsVisible: false,
  },
  localization: {
    locale: 'zh-CN',
  },
}))

let latestRequestId = 0

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '--'
  }

  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })
}

const loadContracts = async () => {
  contractsLoading.value = true
  try {
    const response = await getFutureContractList()
    contracts.value = response

    if (!response.length) {
      selectedSymbol.value = ''
      chartData.value = createEmptyChartData()
      activeKLineBar.value = null
      return
    }

    const firstContract = response[0]
    if (!firstContract) {
      return
    }

    const currentSymbolExists = response.some((item) => item.symbol === selectedSymbol.value)
    if (!currentSymbolExists) {
      selectedSymbol.value = firstContract.symbol
    }
  } catch {
    ElMessage.error(CONTRACT_LIST_ERROR)
  } finally {
    contractsLoading.value = false
  }
}

const loadKLineData = async () => {
  if (!selectedSymbol.value) {
    chartData.value = createEmptyChartData()
    activeKLineBar.value = null
    return
  }

  const requestId = ++latestRequestId
  chartLoading.value = true

  try {
    const response = await getFutureDataApi({
      symbol: selectedSymbol.value,
      period: selectedPeriod.value,
    })

    if (requestId !== latestRequestId) {
      return
    }

    chartData.value = response
    activeKLineBar.value = null
  } catch {
    if (requestId !== latestRequestId) {
      return
    }

    chartData.value = createEmptyChartData()
    activeKLineBar.value = null
    ElMessage.error(KLINE_DATA_ERROR)
  } finally {
    if (requestId === latestRequestId) {
      chartLoading.value = false
    }
  }
}

watch([selectedSymbol, selectedPeriod], () => {
  void loadKLineData()
})

onMounted(() => {
  void loadContracts()
})
</script>

<template>
  <div class="pageBox future-detail">
    <header class="page-header">
      <div>
        <h2 class="title">{{ PAGE_TITLE }}</h2>
        <p class="subtitle">{{ PAGE_SUBTITLE }}</p>
      </div>
    </header>

    <KLineSection
      :loading="chartLoading"
      :available="hasContracts"
      :selected-contract="selectedSymbol"
      :selected-period="selectedPeriod"
      :contract-options="contractOptions"
      :period-options="PERIOD_OPTIONS"
      :contract-loading="contractsLoading"
      :contract-disabled="!hasContracts"
      :contract-placeholder="CONTRACT_PLACEHOLDER"
      :chart-data="chartData"
      :summary-items="summaryItems"
      :chart-options="chartOptions"
      :empty-description="EMPTY_DESCRIPTION"
      :unavailable-description="UNAVAILABLE_DESCRIPTION"
      @update:selected-contract="selectedSymbol = $event"
      @update:selected-period="selectedPeriod = Number($event)"
      @hover-kline-change="activeKLineBar = $event"
    />
  </div>
</template>

<style lang="less" scoped>
.future-detail {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
