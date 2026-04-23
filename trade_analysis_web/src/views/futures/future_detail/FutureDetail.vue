<script lang="ts" setup>
import KLineSection from '@/components/charts/KLineSection.vue'
import {
  buildFutureSegmentAnalysisApi,
  getFutureContractList,
  getFutureDataApi,
  getFutureStrategyAnalysisApi,
  type FutureContract,
  type FutureIntervalStrategy,
  type FutureKlineData,
} from '@/api/modules'
import { ElMessage } from 'element-plus'
import type { ChartOptions, DeepPartial } from 'lightweight-charts'
import { toChartTimestampSeconds } from '@/utils/date'
import { computed, onMounted, ref, watch } from 'vue'

const DEFAULT_PERIOD = 60 * 5
const PAGE_TITLE = '期货 K 线'
const PAGE_SUBTITLE = '选择合约和周期，查看对应的 K 线走势。'
const CONTRACT_PLACEHOLDER = '请选择合约'
const CONTRACT_LIST_ERROR = '获取合约列表失败'
const KLINE_DATA_ERROR = '获取 K 线数据失败'
const EMPTY_DESCRIPTION = '当前条件下暂无 K 线数据'
const UNAVAILABLE_DESCRIPTION = '请先在合约管理中创建期货合约'
const LABEL_OPEN = '开盘'
const LABEL_CLOSE = '收盘'
const LABEL_HIGH = '最高'
const LABEL_LOW = '最低'

const BUILD_SEGMENT_TEXT = '构建段分析'
const LOAD_SEGMENT_TEXT = '载入构建段'
const BUILD_SEGMENT_SUCCESS = '构建段分析完成，已打印接口返回'
const BUILD_SEGMENT_ERROR = '构建段分析失败'
const LOAD_SEGMENT_SUCCESS = '构建段已载入K线图'
const LOAD_SEGMENT_ERROR = '载入构建段失败'
const LOAD_SEGMENT_EMPTY = '当前周期暂无已构建的线段数据'

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

interface ChartSegmentLineItem {
  id: string
  points: Array<{
    time: number
    value: number
  }>
  lineStyle: 'solid' | 'dashed'
}

const contracts = ref<FutureContract[]>([])
const selectedSymbol = ref('')
const selectedPeriod = ref(DEFAULT_PERIOD)
const contractsLoading = ref(false)
const chartLoading = ref(false)
const buildSegmentLoading = ref(false)
const loadSegmentLoading = ref(false)
const chartData = ref<FutureKlineData>(createEmptyChartData())
const loadedSegmentLines = ref<ChartSegmentLineItem[]>([])
const activeKLineBar = ref<FutureKlineData['kLineList'][number] | null>(null)

const hasContracts = computed(() => contracts.value.length > 0)
const canBuildSegments = computed(() => Boolean(selectedSymbol.value))
const canLoadSegments = computed(() => Boolean(selectedSymbol.value))
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

const formatPrice = (value?: number) => {
  if (value === undefined) {
    return '--'
  }

  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })
}

const clearLoadedSegments = () => {
  loadedSegmentLines.value = []
}

const createChartSegmentLine = (
  id: string,
  startTime: string,
  startPrice: number | string,
  endTime: string,
  endPrice: number | string,
  lineStyle: 'solid' | 'dashed',
): ChartSegmentLineItem | null => {
  const startTimestamp = toChartTimestampSeconds(startTime)
  const endTimestamp = toChartTimestampSeconds(endTime)
  const startValue = Number(startPrice)
  const endValue = Number(endPrice)

  if (
    startTimestamp === null
    || endTimestamp === null
    || !Number.isFinite(startValue)
    || !Number.isFinite(endValue)
  ) {
    return null
  }

  const points = [
    { time: startTimestamp, value: startValue },
    { time: endTimestamp, value: endValue },
  ].sort((first, second) => first.time - second.time)

  if (points[0] && points[1] && points[0].time === points[1].time) {
    points[1] = {
      ...points[1],
      time: points[1].time + 1,
    }
  }

  return {
    id,
    lineStyle,
    points,
  }
}

const mapIntervalStrategyToChartSegments = (intervalStrategy?: FutureIntervalStrategy | null) => {
  if (!intervalStrategy) {
    return []
  }

  const segmentLines = intervalStrategy.confirmed_segments
    .map((segment) => {
      return createChartSegmentLine(
        `confirmed-${segment.segment_index}`,
        segment.start_time,
        segment.start_price,
        segment.end_time,
        segment.end_price,
        'solid',
      )
    })
    .filter((item): item is ChartSegmentLineItem => item !== null)

  if (intervalStrategy.current_segment) {
    const buildingSegment = createChartSegmentLine(
      `building-${intervalStrategy.current_segment.segment_index}`,
      intervalStrategy.current_segment.start_time,
      intervalStrategy.current_segment.start_price,
      intervalStrategy.current_segment.end_time,
      intervalStrategy.current_segment.end_price,
      'dashed',
    )
    if (buildingSegment) {
      segmentLines.push(buildingSegment)
    }
  }

  return segmentLines
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

const handleBuildSegments = async () => {
  if (!selectedSymbol.value) {
    return
  }

  buildSegmentLoading.value = true

  try {
    const response = await buildFutureSegmentAnalysisApi({
      symbol: selectedSymbol.value,
      interval: Number(selectedPeriod.value),
    })

    console.log('[segment-build-result]', response)
    console.log('[segment-build-strategy]', response.strategy)
    ElMessage.success(BUILD_SEGMENT_SUCCESS)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, BUILD_SEGMENT_ERROR))
  } finally {
    buildSegmentLoading.value = false
  }
}

const handleLoadSegments = async () => {
  if (!selectedSymbol.value) {
    return
  }

  loadSegmentLoading.value = true

  try {
    const response = await getFutureStrategyAnalysisApi({
      symbol: selectedSymbol.value,
    })
    const intervalStrategy = response.strategy.intervals[String(Number(selectedPeriod.value))]
    const nextSegmentLines = mapIntervalStrategyToChartSegments(intervalStrategy)

    loadedSegmentLines.value = nextSegmentLines

    if (!nextSegmentLines.length) {
      ElMessage.warning(LOAD_SEGMENT_EMPTY)
      return
    }

    ElMessage.success(LOAD_SEGMENT_SUCCESS)
  } catch (error) {
    clearLoadedSegments()
    ElMessage.error(extractErrorMessage(error, LOAD_SEGMENT_ERROR))
  } finally {
    loadSegmentLoading.value = false
  }
}

watch([selectedSymbol, selectedPeriod], () => {
  clearLoadedSegments()
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
      <div class="page-actions">
        <el-button
          type="primary"
          :loading="buildSegmentLoading"
          :disabled="!canBuildSegments"
          @click="handleBuildSegments"
        >
          {{ BUILD_SEGMENT_TEXT }}
        </el-button>
        <el-button
          :loading="loadSegmentLoading"
          :disabled="!canLoadSegments"
          @click="handleLoadSegments"
        >
          {{ LOAD_SEGMENT_TEXT }}
        </el-button>
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
      :segment-lines="loadedSegmentLines"
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
  justify-content: space-between;
  gap: 16px;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
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
