<script lang="ts" setup>
import KLineSection from '@/components/charts/KLineSection.vue'
import {
  buildFutureSegmentAnalysisApi,
  createFutureStrategySegmentApi,
  deleteFutureStrategySegmentsApi,
  getFutureContractList,
  getFutureDataApi,
  getFutureStrategySegmentListApi,
  getFutureStrategyAnalysisApi,
  updateFutureStrategySegmentApi,
  type FutureContract,
  type FutureIntervalStrategy,
  type FutureKlineData,
  type FutureStrategySegmentItem,
  type FutureStrategySegmentRole,
  type FutureTrendSegment,
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

const BUILD_SEGMENT_SUCCESS = '构建段分析完成，已打印接口返回'
const BUILD_SEGMENT_ERROR = '构建段分析失败'
const LOAD_SEGMENT_SUCCESS = '构建段已载入K线图'
const LOAD_SEGMENT_ERROR = '载入构建段失败'
const LOAD_SEGMENT_EMPTY = '当前周期暂无已构建的线段数据'
const UPDATE_SEGMENT_SUCCESS = '线段已更新'
const UPDATE_SEGMENT_ERROR = '修改线段失败'
const CREATE_SEGMENT_SUCCESS = '线段已创建'
const CREATE_SEGMENT_ERROR = '创建线段失败'
const DELETE_SEGMENT_SUCCESS = '线段已删除'
const DELETE_SEGMENT_ERROR = '删除线段失败'

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
  lineStyle?: 'solid' | 'dashed'
  segmentRole?: string
  segmentIndex?: number
  direction?: string
}

interface SegmentLineChange {
  segment: ChartSegmentLineItem
  endpoint: 'start' | 'end'
  points: Array<{
    time: number
    value: number
  }>
}

interface SegmentLineCreate {
  startPoint: {
    time: number
    value: number
  }
  endPoint: {
    time: number
    value: number
  }
}

interface SegmentLineDelete {
  segment: ChartSegmentLineItem
}

const contracts = ref<FutureContract[]>([])
const selectedSymbol = ref('')
const selectedPeriod = ref(DEFAULT_PERIOD)
const contractsLoading = ref(false)
const chartLoading = ref(false)
const buildSegmentLoading = ref(false)
const loadSegmentLoading = ref(false)
const updateSegmentLoading = ref(false)
const chartData = ref<FutureKlineData>(createEmptyChartData())
const loadedSegmentLines = ref<ChartSegmentLineItem[]>([])
const activeKLineBar = ref<FutureKlineData['kLineList'][number] | null>(null)

const hasContracts = computed(() => contracts.value.length > 0)
const canBuildSegments = computed(() => Boolean(selectedSymbol.value))
const canLoadSegments = computed(() => Boolean(selectedSymbol.value))
const contractOptions = computed(() => {
  return contracts.value.map((contract) => ({
    label: `${contract.symbol} · ${contract.name}`,
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

const isSegmentRole = (value?: string): value is FutureStrategySegmentRole => {
  return value === 'confirmed' || value === 'current' || value === 'pending'
}

const findKLineDateTimeByChartTime = (time: number) => {
  const matchedItem = chartData.value.kline_data.find((item) => {
    return toChartTimestampSeconds(item.date_time) === time
  })

  return matchedItem?.date_time ?? null
}

const createChartSegmentLine = (
  id: string,
  startTime: string,
  startPrice: number | string,
  endTime: string,
  endPrice: number | string,
  lineStyle: 'solid' | 'dashed',
  segmentRole: FutureStrategySegmentRole,
  segmentIndex: number,
  direction: string,
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
    segmentRole,
    segmentIndex,
    direction,
  }
}

const createChartSegmentLineFromManagedSegment = (segment: FutureStrategySegmentItem) => {
  return createChartSegmentLine(
    `${segment.segment_role}-${segment.segment_index}`,
    segment.start_time,
    segment.start_price,
    segment.end_time,
    segment.end_price,
    segment.segment_role === 'confirmed' ? 'solid' : 'dashed',
    segment.segment_role,
    segment.segment_index,
    segment.direction,
  )
}

const createChartSegmentLineFromStrategySegment = (
  segment: FutureTrendSegment,
  segmentRole: FutureStrategySegmentRole,
  lineStyle: 'solid' | 'dashed',
) => {
  return createChartSegmentLine(
    `${segmentRole}-${segment.segment_index}`,
    segment.start_time,
    segment.start_price,
    segment.end_time,
    segment.end_price,
    lineStyle,
    segmentRole,
    segment.segment_index,
    segment.direction,
  )
}

const mapIntervalStrategyToChartSegments = (intervalStrategy?: FutureIntervalStrategy | null) => {
  if (!intervalStrategy) {
    return []
  }

  const segmentLines = intervalStrategy.confirmed_segments
    .map((segment) => {
      return createChartSegmentLineFromStrategySegment(segment, 'confirmed', 'solid')
    })
    .filter((item): item is ChartSegmentLineItem => item !== null)

  if (intervalStrategy.current_segment) {
    const buildingSegment = createChartSegmentLine(
      `current-${intervalStrategy.current_segment.segment_index}`,
      intervalStrategy.current_segment.start_time,
      intervalStrategy.current_segment.start_price,
      intervalStrategy.current_segment.end_time,
      intervalStrategy.current_segment.end_price,
      'dashed',
      'current',
      intervalStrategy.current_segment.segment_index,
      intervalStrategy.current_segment.direction,
    )
    if (buildingSegment) {
      segmentLines.push(buildingSegment)
    }
  }

  return segmentLines
}

const mapManagedSegmentsToChartSegments = (items: FutureStrategySegmentItem[]) => {
  return items
    .map(createChartSegmentLineFromManagedSegment)
    .filter((item): item is ChartSegmentLineItem => item !== null)
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

const handleSegmentLineChange = async (change: SegmentLineChange) => {
  if (!selectedSymbol.value || updateSegmentLoading.value) {
    return
  }

  if (!isSegmentRole(change.segment.segmentRole) || !change.segment.segmentIndex) {
    ElMessage.error(UPDATE_SEGMENT_ERROR)
    return
  }

  const [startPoint, endPoint] = [...change.points].sort((first, second) => first.time - second.time)
  if (!startPoint || !endPoint) {
    return
  }

  const startTime = findKLineDateTimeByChartTime(startPoint.time)
  const endTime = findKLineDateTimeByChartTime(endPoint.time)
  if (!startTime || !endTime) {
    ElMessage.error(UPDATE_SEGMENT_ERROR)
    return
  }

  updateSegmentLoading.value = true
  try {
    const response = await updateFutureStrategySegmentApi({
      symbol: selectedSymbol.value,
      interval: Number(selectedPeriod.value),
      original_segment_role: change.segment.segmentRole,
      original_segment_index: change.segment.segmentIndex,
      segment_role: change.segment.segmentRole,
      direction: endPoint.value >= startPoint.value ? 'up' : 'down',
      start_time: startTime,
      start_price: startPoint.value,
      end_time: endTime,
      end_price: endPoint.value,
    })

    loadedSegmentLines.value = mapManagedSegmentsToChartSegments(response.items)
    ElMessage.success(UPDATE_SEGMENT_SUCCESS)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, UPDATE_SEGMENT_ERROR))
  } finally {
    updateSegmentLoading.value = false
  }
}

const refreshManagedSegments = async () => {
  const response = await getFutureStrategySegmentListApi({
    symbol: selectedSymbol.value,
    interval: Number(selectedPeriod.value),
  })
  loadedSegmentLines.value = mapManagedSegmentsToChartSegments(response.items)
}

const handleSegmentLineCreate = async (payload: SegmentLineCreate) => {
  if (!selectedSymbol.value || updateSegmentLoading.value) {
    return
  }

  const startTime = findKLineDateTimeByChartTime(payload.startPoint.time)
  const endTime = findKLineDateTimeByChartTime(payload.endPoint.time)
  if (!startTime || !endTime) {
    ElMessage.error(CREATE_SEGMENT_ERROR)
    return
  }

  updateSegmentLoading.value = true
  try {
    const response = await createFutureStrategySegmentApi({
      symbol: selectedSymbol.value,
      interval: Number(selectedPeriod.value),
      segment_role: 'confirmed',
      direction: payload.endPoint.value >= payload.startPoint.value ? 'up' : 'down',
      start_time: startTime,
      start_price: payload.startPoint.value,
      end_time: endTime,
      end_price: payload.endPoint.value,
    })

    loadedSegmentLines.value = mapManagedSegmentsToChartSegments(response.items)
    ElMessage.success(CREATE_SEGMENT_SUCCESS)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, CREATE_SEGMENT_ERROR))
  } finally {
    updateSegmentLoading.value = false
  }
}

const handleSegmentLineDelete = async (payload: SegmentLineDelete) => {
  if (!selectedSymbol.value || updateSegmentLoading.value) {
    return
  }

  if (payload.segment.segmentRole !== 'confirmed' || !payload.segment.segmentIndex) {
    ElMessage.error(DELETE_SEGMENT_ERROR)
    return
  }

  updateSegmentLoading.value = true
  try {
    await deleteFutureStrategySegmentsApi({
      symbol: selectedSymbol.value,
      interval: Number(selectedPeriod.value),
      items: [
        {
          segment_role: 'confirmed',
          segment_index: payload.segment.segmentIndex,
        },
      ],
    })
    await refreshManagedSegments()
    ElMessage.success(DELETE_SEGMENT_SUCCESS)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, DELETE_SEGMENT_ERROR))
  } finally {
    updateSegmentLoading.value = false
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
      :can-build-segments="canBuildSegments && !buildSegmentLoading"
      :can-load-segments="canLoadSegments && !loadSegmentLoading"
      :summary-items="summaryItems"
      :chart-options="chartOptions"
      :empty-description="EMPTY_DESCRIPTION"
      :unavailable-description="UNAVAILABLE_DESCRIPTION"
      @update:selected-contract="selectedSymbol = $event"
      @update:selected-period="selectedPeriod = Number($event)"
      @hover-kline-change="activeKLineBar = $event"
      @segment-line-change="handleSegmentLineChange"
      @segment-line-create="handleSegmentLineCreate"
      @segment-line-delete="handleSegmentLineDelete"
      @segment-build-request="handleBuildSegments"
      @segment-load-request="handleLoadSegments"
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
