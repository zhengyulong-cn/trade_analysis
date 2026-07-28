<script setup lang="ts">
import {
  getFutureDataApi,
  type FutureContract,
  type FutureChartKLineItem,
} from "@/api/modules"
import { init, dispose, type Chart, type KLineData, type PeriodType } from "klinecharts"
import { ElMessage } from "element-plus"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { storeToRefs } from "pinia"
import { useRealtimeMarketStore, type RealtimeBar } from "@/stores/realtimeMarket"
import { usePositionOverlayStore } from "@/stores/positionOverlays"
import ChartSideBar from "./ChartSideBar.vue"
import { chartStylesConfig } from "./config.ts"
import PineIndicatorSelector from "./PineIndicatorSelector.vue"
import PineLabelTooltip from "./overlay/label/PineLabelTooltip.vue"
import { usePineLabelTooltip } from "./overlay/label/usePineLabelTooltip.ts"
import { registerPineDrawingOverlays } from "./overlay/pine-drawing-overlays.ts"
import { registerPositionTextOverlay } from "./overlay/position-text-overlay.ts"
import { usePineIndicators } from './composables/usePineIndicators'
import { usePositionChartOverlays } from './composables/usePositionChartOverlays'
import { useWatchlists } from './composables/useWatchlists'

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
const DEFAULT_PERIOD_OPTION = PERIOD_OPTIONS[0] as PeriodOption

const chartRef = ref<HTMLDivElement>()
const chartShellRef = ref<HTMLDivElement>()
const selectedSymbol = ref("")
const selectedPeriod = ref(DEFAULT_PERIOD_OPTION.value)
const chartLoading = ref(false)
const hasLoadedOnce = ref(false)
const klineCount = ref(0)
const latestClosePrice = ref<number | undefined>()
const {
  tooltip: pineLabelTooltip,
  hide: hidePineLabelTooltip,
  show: showPineLabelTooltip,
  scheduleHide: schedulePineLabelTooltipHide,
} = usePineLabelTooltip(chartShellRef)
let chart: Chart | null = null
let resizeObserver: ResizeObserver | null = null
let latestRequestId = 0
let isInitializingChart = false
let realtimeBarSubscriber: ((data: KLineData) => void) | null = null
const realtimeMarketStore = useRealtimeMarketStore()
const { bars: realtimeBars } = storeToRefs(realtimeMarketStore)
const positionOverlayStore = usePositionOverlayStore()
const { positions } = storeToRefs(positionOverlayStore)
const {
  watchlists,
  activeWatchlistId,
  watchlistContracts,
  loadWatchlists,
  switchWatchlist,
  createWatchlist,
  deleteWatchlist,
  addContractToWatchlist,
  removeContractFromWatchlist,
  reorderWatchlistContracts,
} = useWatchlists()
const { clear: clearPositionOverlays, render: renderPositionOverlays } = usePositionChartOverlays(
  () => chart,
  selectedSymbol,
  positions,
)
const {
  selectedPineIndicatorIds,
  pineIndicatorLoadingIds,
  clear: clearPineIndicatorOverlays,
  reload: reloadSelectedPineIndicators,
  update: updateSelectedPineIndicators,
} = usePineIndicators(
  () => chart,
  selectedSymbol,
  selectedPeriod,
  {
    onEnter: showPineLabelTooltip,
    onMove: showPineLabelTooltip,
    onLeave: hidePineLabelTooltip,
  },
)

const sortedContracts = computed(() => watchlistContracts.value)
const selectableContracts = computed(() => {
  return [...props.contracts].sort((first, second) => first.symbol.localeCompare(second.symbol, 'zh-CN'))
})

const currentContract = computed(() => {
  return props.contracts.find((item) => item.symbol === selectedSymbol.value)
})
const currentLatestPrice = computed(() => {
  const realtimePrice = Number(realtimeBars.value[`${selectedSymbol.value}:${selectedPeriod.value}`]?.close)
  return Number.isFinite(realtimePrice) ? realtimePrice : latestClosePrice.value
})

const isChartUnavailable = computed(() => !props.loading && !watchlistContracts.value.length)
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

const toRealtimeKLineData = (bar: RealtimeBar): KLineData => ({
  timestamp: new Date(bar.date_time).getTime(),
  open: Number(bar.open),
  high: Number(bar.high),
  low: Number(bar.low),
  close: Number(bar.close),
  volume: Number(bar.volume),
})

const publishRealtimeBar = (bar: RealtimeBar | undefined) => {
  if (!bar || bar.symbol !== selectedSymbol.value || bar.interval !== selectedPeriod.value) {
    return
  }
  latestClosePrice.value = Number(bar.close)
  realtimeBarSubscriber?.(toRealtimeKLineData(bar))
  renderPositionOverlays()
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
    latestClosePrice.value = chartData.at(-1)?.close
    callback(chartData, false)
    publishRealtimeBar(realtimeBars.value[`${selectedSymbol.value}:${selectedPeriod.value}`])
    renderPositionOverlays()
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
  registerPositionTextOverlay()

  chart?.setDataLoader({
    getBars: ({ callback }) => {
      void loadChartBars(callback)
    },
    subscribeBar: ({ callback }) => {
      realtimeBarSubscriber = callback
      publishRealtimeBar(realtimeBars.value[`${selectedSymbol.value}:${selectedPeriod.value}`])
    },
    unsubscribeBar: () => {
      realtimeBarSubscriber = null
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
  clearPositionOverlays()
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
  latestClosePrice.value = undefined
  if (!isInitializingChart) {
    void refreshChartSymbol()
  }
})

watch(selectedPeriod, () => {
  if (!isInitializingChart) {
    void refreshChartPeriod()
  }
})

watch(
  () => realtimeBars.value[`${selectedSymbol.value}:${selectedPeriod.value}`],
  (bar) => publishRealtimeBar(bar),
)

watch(positions, () => renderPositionOverlays(), { deep: true })

watch(
  () => [...watchlistContracts.value.map((contract) => contract.symbol), selectedSymbol.value],
  (symbols) => realtimeMarketStore.subscribe(symbols.filter(Boolean)),
  { immediate: true },
)

onMounted(() => {
  void (async () => {
    // Set the period before a symbol is assigned so only setSymbol loads initial bars.
    isInitializingChart = true
    await loadWatchlists()
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
  realtimeBarSubscriber = null
  realtimeMarketStore.disconnect()
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chart) {
    clearPineIndicatorOverlays()
    clearPositionOverlays()
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
            v-for="contract in selectableContracts"
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
        :contracts="contracts"
        :watchlists="watchlists"
        :active-watchlist-id="activeWatchlistId"
        :watchlist-contracts="sortedContracts"
        :selected-contract="selectedSymbol"
        :latest-price="currentLatestPrice"
        @update:selected-contract="selectedSymbol = $event"
        @update:active-watchlist-id="switchWatchlist"
        @create-watchlist="createWatchlist"
        @delete-watchlist="deleteWatchlist"
        @add-contract="addContractToWatchlist"
        @remove-contract="removeContractFromWatchlist"
        @reorder-contracts="reorderWatchlistContracts"
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
