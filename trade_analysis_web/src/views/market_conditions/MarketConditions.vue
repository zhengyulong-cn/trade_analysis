<script lang="ts" setup>
import KLineSection from '@/components/charts/KLineSection.vue'
import { getFutureDataApi, updateFutureContract, type FutureKlineData } from '@/api/modules'
import { useContractsStore } from '@/stores/contracts'
import { ElMessage } from 'element-plus'
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'

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

const contractsStore = useContractsStore()
const { contracts, loading: contractsLoading, loadError } = storeToRefs(contractsStore)

const selectedSymbol = ref('')
const selectedPeriod = ref(DEFAULT_PERIOD)
const chartLoading = ref(false)
const chartData = ref<FutureKlineData>(createEmptyChartData())

const hasContracts = computed(() => contracts.value.length > 0)
const contractOptions = computed(() => {
  return contracts.value.map((contract) => ({
    label: contract.name,
    value: contract.symbol,
    description: contract.name,
  }))
})

const sortedContractOptions = computed(() => {
  return [...contractOptions.value]
    .sort((first, second) => {
      const firstContract = contracts.value.find((contract) => contract.symbol === first.value)
      const secondContract = contracts.value.find((contract) => contract.symbol === second.value)
      const firstFavorite = firstContract?.is_favorite ?? 0
      const secondFavorite = secondContract?.is_favorite ?? 0

      if (firstFavorite !== secondFavorite) {
        return secondFavorite - firstFavorite
      }
      return first.value.localeCompare(second.value, 'zh-CN')
    })
    .map((option) => {
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

const handleToggleFavorite = async (symbol: string) => {
  const contract = contracts.value.find((item) => item.symbol === symbol)
  if (!contract) {
    return
  }

  try {
    const updatedContract = await updateFutureContract({
      contract_id: contract.contract_id,
      is_favorite: contract.is_favorite === 1 ? 0 : 1,
    })
    contractsStore.upsertContract(updatedContract)
    ElMessage.success(updatedContract.is_favorite === 1 ? '已加入收藏' : '已取消收藏')
  } catch {
    ElMessage.error('切换合约收藏状态失败')
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

watch(
  contracts,
  (items) => {
    if (!items.length) {
      selectedSymbol.value = ''
      chartData.value = createEmptyChartData()
      return
    }

    const currentSymbolExists = items.some((item) => item.symbol === selectedSymbol.value)
    if (!currentSymbolExists) {
      selectedSymbol.value = items[0]?.symbol ?? ''
    }
  },
  { immediate: true },
)

watch(
  loadError,
  (message) => {
    if (message) {
      ElMessage.error(CONTRACT_LIST_ERROR)
    }
  },
  { immediate: true },
)
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
      @toggle-favorite="handleToggleFavorite"
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
