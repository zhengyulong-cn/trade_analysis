<script lang="ts" setup>
import KLineSection from '@/components/charts/KLineSection.vue'
import {
  getFutureContractList,
  getFutureDataApi,
  type FutureContract,
  type FutureKlineData,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { computed, onMounted, ref, watch } from 'vue'

const DEFAULT_PERIOD = 60 * 5
const CONTRACT_PLACEHOLDER = '请选择合约'
const CONTRACT_LIST_ERROR = '获取合约列表失败'
const KLINE_DATA_ERROR = '获取 K 线数据失败'
const EMPTY_DESCRIPTION = '当前条件下暂无 K 线数据'
const UNAVAILABLE_DESCRIPTION = '请先在合约管理中创建期货合约'

const PERIOD_OPTIONS = [
  { label: '5F', value: DEFAULT_PERIOD },
  { label: '30F', value: 60 * 30 },
  { label: '1H', value: 60 * 60 },
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

const hasContracts = computed(() => contracts.value.length > 0)
const contractOptions = computed(() => {
  return contracts.value.map((contract) => ({
    label: `${contract.symbol} 路 ${contract.name}`,
    value: contract.symbol,
    description: contract.name,
  }))
})
const sortedContractOptions = computed(() => {
  return [...contractOptions.value].sort((first, second) => {
    const firstContract = contracts.value.find((contract) => contract.symbol === first.value)
    const secondContract = contracts.value.find((contract) => contract.symbol === second.value)
    const firstFavorite = firstContract?.is_favorite ?? 0
    const secondFavorite = secondContract?.is_favorite ?? 0

    if (firstFavorite !== secondFavorite) {
      return secondFavorite - firstFavorite
    }
    return first.value.localeCompare(second.value, 'zh-CN')
  }).map((option) => {
    const contract = contracts.value.find((item) => item.symbol === option.value)
    return {
      ...option,
      isFavorite: contract?.is_favorite === 1,
    }
  })
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

const loadContracts = async () => {
  contractsLoading.value = true
  try {
    const response = await getFutureContractList()
    contracts.value = response

    if (!response.length) {
      selectedSymbol.value = ''
      chartData.value = createEmptyChartData()
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
  } catch {
    if (requestId !== latestRequestId) {
      return
    }

    chartData.value = createEmptyChartData()
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
    <KLineSection
      :loading="chartLoading"
      :available="hasContracts"
      :selected-contract="selectedSymbol"
      :selected-period="selectedPeriod"
      :contract-options="sortedContractOptions"
      :period-options="PERIOD_OPTIONS"
      :contract-loading="contractsLoading"
      :contract-disabled="!hasContracts"
      :contract-placeholder="CONTRACT_PLACEHOLDER"
      :chart-data="chartData"
      :chart-options="chartOptions"
      :empty-description="EMPTY_DESCRIPTION"
      :unavailable-description="UNAVAILABLE_DESCRIPTION"
      @update:selected-contract="selectedSymbol = $event"
      @update:selected-period="selectedPeriod = Number($event)"
    />
  </div>
</template>

<style lang="less" scoped>
.future-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
