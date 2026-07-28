<script setup lang="ts">
import {
  executePineIndicatorApi,
  getFutureDataApi,
  type FutureContract,
  type FutureChartKLineItem,
  type PineIndicatorExecuteResult,
} from "@/api/modules"
import { init, dispose, type Chart, type KLineData, type PeriodType } from "klinecharts"
import { ElMessage } from "element-plus"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import ChartSideBar from "./ChartSideBar.vue"
import { chartStylesConfig } from "./config.ts"
import PineIndicatorSelector from "./PineIndicatorSelector.vue"
import PineLabelTooltip from "./overlay/label/PineLabelTooltip.vue"
import { usePineLabelTooltip } from "./overlay/label/usePineLabelTooltip.ts"
import { createPineDrawingOverlays, registerPineDrawingOverlays } from "./overlay/pine-drawing-overlays.ts"

interface PeriodOption {
  label: string
  value: number
  type: PeriodType
  span: number
}

const props = withDefaults(
  defineProps<{
    contracts: FutureContract[]
    loading?: boolean
  }>(),
  {
    loading: false,
  },
)

const PERIOD_OPTIONS: PeriodOption[] = [
  { label: "5分", value: 60 * 5, type: "minute", span: 5 },
  { label: "30分", value: 60 * 30, type: "minute", span: 30 },
  { label: "1小时", value: 60 * 60, type: "hour", span: 1 },
]
const DEFAULT_PERIOD_OPTION = PERIOD_OPTIONS[1] as PeriodOption

const chartRef = ref<HTMLDivElement>()
const chartShellRef = ref<HTMLDivElement>()
const selectedSymbol = ref("")
const selectedPeriod = ref(DEFAULT_PERIOD_OPTION.value)
const chartLoading = ref(false)
const hasLoadedOnce = ref(false)
const klineCount = ref(0)
const selectedPineIndicatorIds = ref<number[]>([])
const pineIndicatorLoadingIds = ref<number[]>([])
const {
  tooltip: pineLabelTooltip,
  hide: hidePineLabelTooltip,
  show: showPineLabelTooltip,
  scheduleHide: schedulePineLabelTooltipHide,
} = usePineLabelTooltip(chartShellRef)
let chart: Chart | null = null
let resizeObserver: ResizeObserver | null = null
let latestRequestId = 0
let latestPineIndicatorRequestId = 0
let isInitializingChart = false
const renderedPineIndicatorIds = new Set<number>()

const pineIndicatorGroupId = (scriptId: number) => `pine-indicator-${scriptId}`

const setPineIndicatorLoading = (scriptId: number, loading: boolean) => {
  const ids = new Set(pineIndicatorLoadingIds.value)
  if (loading) {
    ids.add(scriptId)
  } else {
    ids.delete(scriptId)
  }
  pineIndicatorLoadingIds.value = [...ids]
}

const removePineIndicatorOverlays = (scriptId: number) => {
  chart?.removeOverlay({ groupId: pineIndicatorGroupId(scriptId) })
  renderedPineIndicatorIds.delete(scriptId)
}

const clearPineIndicatorOverlays = () => {
  hidePineLabelTooltip()
  for (const scriptId of new Set([...renderedPineIndicatorIds, ...selectedPineIndicatorIds.value])) {
    removePineIndicatorOverlays(scriptId)
  }
}

const renderPineIndicator = (result: PineIndicatorExecuteResult) => {
  if (!chart) {
    return
  }

  removePineIndicatorOverlays(result.script_id)
  const overlays = createPineDrawingOverlays(pineIndicatorGroupId(result.script_id), result.drawings, {
    onEnter: showPineLabelTooltip,
    onMove: showPineLabelTooltip,
    onLeave: hidePineLabelTooltip,
  })
  if (overlays.length) {
    chart.createOverlay(overlays)
    renderedPineIndicatorIds.add(result.script_id)
  }
}

const loadPineIndicator = async (scriptId: number) => {
  const symbol = selectedSymbol.value
  const interval = selectedPeriod.value
  if (!chart || !symbol || !selectedPineIndicatorIds.value.includes(scriptId)) {
    return
  }

  const requestId = ++latestPineIndicatorRequestId
  setPineIndicatorLoading(scriptId, true)
  try {
    const result = await executePineIndicatorApi({
      script_id: scriptId,
      symbol,
      interval,
      limit: 1000,
    })
    const isStillCurrent = chart
      && selectedSymbol.value === symbol
      && selectedPeriod.value === interval
      && selectedPineIndicatorIds.value.includes(scriptId)
    if (!isStillCurrent) {
      return
    }
    renderPineIndicator(result)
  } catch {
    if (selectedSymbol.value === symbol && selectedPeriod.value === interval) {
      ElMessage.error(`Failed to load Pine indicator #${scriptId}.`)
    }
  } finally {
    if (requestId <= latestPineIndicatorRequestId) {
      setPineIndicatorLoading(scriptId, false)
    }
  }
}

const reloadSelectedPineIndicators = () => {
  for (const scriptId of selectedPineIndicatorIds.value) {
    void loadPineIndicator(scriptId)
  }
}

const updateSelectedPineIndicators = (scriptIds: number[]) => {
  const nextIds = [...new Set(scriptIds)]
  const nextIdSet = new Set(nextIds)
  for (const scriptId of selectedPineIndicatorIds.value) {
    if (!nextIdSet.has(scriptId)) {
      removePineIndicatorOverlays(scriptId)
    }
  }

  const currentIdSet = new Set(selectedPineIndicatorIds.value)
  selectedPineIndicatorIds.value = nextIds
  for (const scriptId of nextIds) {
    if (!currentIdSet.has(scriptId)) {
      void loadPineIndicator(scriptId)
    }
  }
}

const sortedContracts = computed(() => {
  return [...props.contracts].sort((first, second) => {
    if (first.is_favorite !== second.is_favorite) {
      return second.is_favorite - first.is_favorite
    }
    return first.symbol.localeCompare(second.symbol, "zh-CN")
  })
})

const currentContract = computed(() => {
  return props.contracts.find((item) => item.symbol === selectedSymbol.value)
})

const isChartUnavailable = computed(() => !props.loading && !props.contracts.length)
const isChartEmpty = computed(() => hasLoadedOnce.value && !chartLoading.value && klineCount.value === 0)
const selectedPeriodOption = computed(() => {
  return PERIOD_OPTIONS.find((item) => item.value === selectedPeriod.value) ?? DEFAULT_PERIOD_OPTION
})

const toKLineChartsData = (items: FutureChartKLineItem[]): KLineData[] => {
  return items.map((item) => ({
    timestamp: item.time * 1000,
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
    volume: item.volume,
  }))
}

const loadChartBars = async (callback: (data: KLineData[], more?: boolean) => void) => {
  if (!selectedSymbol.value) {
    callback([], false)
    klineCount.value = 0
    return
  }

  const requestId = ++latestRequestId
  chartLoading.value = true
  hasLoadedOnce.value = true

  try {
    const response = await getFutureDataApi({
      symbol: selectedSymbol.value,
      period: selectedPeriod.value,
      limit: 1000,
    })
    if (requestId !== latestRequestId) {
      return
    }

    const chartData = toKLineChartsData(response.kLineList)
    callback(chartData, false)
    klineCount.value = chartData.length
    reloadSelectedPineIndicators()
  } catch {
    if (requestId !== latestRequestId) {
      return
    }
    callback([], false)
    klineCount.value = 0
    ElMessage.error("获取 K 线数据失败")
  } finally {
    if (requestId === latestRequestId) {
      chartLoading.value = false
    }
  }
}

const ensureChart = async () => {
  await nextTick()
  if (!chartRef.value || chart) {
    return
  }

  chart = init(chartRef.value, {
    locale: "zh-CN",
    timezone: "Asia/Shanghai",
    styles: chartStylesConfig,
  })
  registerPineDrawingOverlays()

  chart?.setDataLoader({
    getBars: ({ callback }) => {
      void loadChartBars(callback)
    },
  })

  resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

const clearChart = () => {
  chart?.resetData()
  clearPineIndicatorOverlays()
  klineCount.value = 0
}

const refreshChartSymbol = async () => {
  if (!selectedSymbol.value) {
    clearChart()
    return
  }

  await ensureChart()
  const contract = currentContract.value
  if (chart?.getSymbol()?.ticker === selectedSymbol.value) {
    return
  }

  clearPineIndicatorOverlays()
  chart?.setSymbol({
    ticker: selectedSymbol.value,
    name: contract?.name ?? selectedSymbol.value,
    shortName: selectedSymbol.value,
  })
}

const refreshChartPeriod = async () => {
  await ensureChart()
  const nextPeriod = selectedPeriodOption.value
  const currentPeriod = chart?.getPeriod()
  if (currentPeriod?.type === nextPeriod.type && currentPeriod.span === nextPeriod.span) {
    return
  }

  clearPineIndicatorOverlays()
  chart?.setPeriod({
    type: nextPeriod.type,
    span: nextPeriod.span,
  })
}

watch(
  sortedContracts,
  (items) => {
    if (!items.length) {
      selectedSymbol.value = ""
      clearChart()
      return
    }

    if (!items.some((item) => item.symbol === selectedSymbol.value)) {
      selectedSymbol.value = items[0]?.symbol ?? ""
    }
  },
  { immediate: true },
)

watch(selectedSymbol, () => {
  if (!isInitializingChart) {
    void refreshChartSymbol()
  }
})

watch(selectedPeriod, () => {
  if (!isInitializingChart) {
    void refreshChartPeriod()
  }
})

onMounted(() => {
  void (async () => {
    // Set the period before a symbol is assigned so only setSymbol loads initial bars.
    isInitializingChart = true
    const initialSymbol = selectedSymbol.value
    selectedSymbol.value = ""
    await ensureChart()
    await refreshChartPeriod()
    selectedSymbol.value = initialSymbol
    await refreshChartSymbol()
    isInitializingChart = false
  })()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chart) {
    clearPineIndicatorOverlays()
    dispose(chart)
    chart = null
  }
})
</script>

<template>
  <section class="klinecharts-panel">
    <div class="chart-main">
      <header class="chart-toolbar">
        <div class="chart-controls">
          <el-select
            v-model="selectedSymbol"
            filterable
            :loading="loading"
            :disabled="loading || !sortedContracts.length"
            placeholder="选择合约"
            class="contract-select"
          >
            <el-option
              v-for="contract in sortedContracts"
              :key="contract.contract_id"
              :label="`${contract.symbol} ${contract.name}`"
              :value="contract.symbol"
            />
          </el-select>

          <el-segmented v-model="selectedPeriod" :options="PERIOD_OPTIONS" class="period-segmented" />
          <PineIndicatorSelector
            :model-value="selectedPineIndicatorIds"
            :loading-ids="pineIndicatorLoadingIds"
            :disabled="!selectedSymbol"
            @update:model-value="updateSelectedPineIndicators"
          />
        </div>
      </header>
      <div
        ref="chartShellRef"
        v-loading="chartLoading"
        class="chart-shell"
        @mousemove.capture="schedulePineLabelTooltipHide"
        @mouseleave="hidePineLabelTooltip"
      >
        <div ref="chartRef" class="chart-container"></div>
        <PineLabelTooltip v-bind="pineLabelTooltip" />
        <el-empty v-if="isChartUnavailable" description="暂无合约数据" class="chart-empty" />
        <el-empty v-else-if="isChartEmpty" description="当前合约和周期暂无 K 线数据" class="chart-empty" />
      </div>
    </div>
    <aside class="chart-side-bar">
      <ChartSideBar
        :contracts="sortedContracts"
        :selected-contract="selectedSymbol"
        @update:selected-contract="selectedSymbol = $event"
      />
    </aside>
  </section>
</template>

<style scoped lang="less">
.klinecharts-panel {
  display: flex;
  flex-direction: row;
  height: calc(100vh - 3.5rem);
  column-gap: .5rem;
}

.chart-main {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.chart-side-bar {
  height: 100%;
}

.chart-toolbar {
  display: flex;
}

.contract-meta {
  min-width: 0;
}

.contract-title {
  color: #1f2937;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
}

.contract-subtitle {
  margin-top: 4px;
  color: #667085;
  font-size: 13px;
}

.chart-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.contract-select {
  width: 240px;
}

.period-segmented {
  flex-shrink: 0;
}

.chart-shell {
  position: relative;
  flex: 1;
  min-height: 560px;
  overflow: hidden;
  border: 1px solid #dfe5ef;
  border-radius: 6px;
  background: #fff;

  display: flex;
}

.chart-container {
  width: 100%;
  flex: 1;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.78);
}

@media (max-width: 900px) {
  .klinecharts-panel {
    min-height: calc(100vh - 64px);
    padding: 10px;
  }

  .chart-toolbar {
    flex-direction: column;
  }

  .chart-controls,
  .contract-select,
  .period-segmented {
    width: 100%;
  }

  .chart-shell,
  .chart-container {
    height: calc(100vh - 190px);
    min-height: 460px;
  }
}
</style>
