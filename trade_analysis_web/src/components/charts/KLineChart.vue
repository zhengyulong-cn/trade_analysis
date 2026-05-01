<script setup lang="ts">
import { INITIAL_VISIBLE_K_LINE_COUNT } from '@/constants/chart'
import { ElMessage } from 'element-plus'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import ChartSidebar from '@/components/charts/sidebar_panel/ChartSidebar.vue'
import type { ContractOption, KLineItem, PeriodOption } from '@/components/charts/chartModels'
import {
  type ChartDatafeedController,
  createDatafeed,
  getBarResolution,
  getPersistenceInterval,
  getTimeFrames,
  getTradingViewBars,
  normalizeTimeToMilliseconds,
  normalizeTimeToSeconds,
  periodValueFromResolution,
} from '@/components/charts/chartDatafeed'
import {
  getDrawingsStateContent,
  loadChartPersistence,
  restoreChartPersistence,
  saveChartPersistence,
  saveLocalStudyTemplate,
  type FutureChartPersistence,
} from '@/components/charts/chartPersistence'
import {
  addDefaultCustomStudies,
  getCustomIndicators,
  getWhitelistedStudyTools,
} from '@/components/charts/customStudies'
import type {
  TradingViewWidget,
} from '@/components/charts/tradingViewTypes'

const TRADING_VIEW_LIBRARY_PATH = '/charting_library/'
const DEFAULT_SYMBOL = 'FUTURES'
const SCRIPT_ID = 'tradingview-charting-library-script'

const props = withDefaults(
  defineProps<{
    data: {
      kLineList: KLineItem[]
      symbol?: string
      name?: string
    }
    selectedContract?: string
    selectedPeriod?: number | string
    contractOptions?: ContractOption[]
    periodOptions?: PeriodOption[]
    autosize?: boolean
    commonChartOptions?: Record<string, unknown>
  }>(),
  {
    selectedContract: '',
    selectedPeriod: '',
    contractOptions: () => [],
    periodOptions: () => [],
    autosize: true,
    commonChartOptions: () => ({}),
  },
)

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:selectedPeriod': [value: number | string]
  'crosshair-move': [value: KLineItem | null]
}>()

const chartContainer = ref<HTMLDivElement | null>(null)
const hoveredKLine = ref<KLineItem | null>(null)
const isReplayMode = ref(false)
const replayCursorIndex = ref<number | null>(null)

let widget: TradingViewWidget | null = null
let crossHairHandler: ((params: { time?: number }) => void) | null = null
let onDataLoadedHandler: (() => void) | null = null
let onSymbolChangedHandler: ((symbol: { name: string; ticker?: string }) => void) | null = null
let onIntervalChangedHandler: ((interval: string, timeFrameParameters: Record<string, unknown>) => void) | null = null
let onAutoSaveNeededHandler: (() => void) | null = null
let createWidgetToken = 0
let libraryPromise: Promise<void> | null = null
let chartAutoSaveTimeoutId: number | null = null
let isRestoringPersistence = false
let chartRestoreToken = 0
let datafeedController: ChartDatafeedController | null = null
const realtimeSubscriptionIntervals = new Map<string, number>()

const symbolName = computed(() => {
  return props.selectedContract?.trim() || props.data.symbol?.trim() || props.data.name?.trim() || DEFAULT_SYMBOL
})

const getSortedKLineList = () => {
  return [...(props.data.kLineList ?? [])].sort((first, second) => first.time - second.time)
}

const displayedKLineList = computed(() => {
  const sortedList = getSortedKLineList()
  if (!isReplayMode.value) {
    return sortedList
  }

  const cursorIndex = replayCursorIndex.value
  if (cursorIndex === null || cursorIndex < 0) {
    return sortedList
  }

  return sortedList.slice(0, cursorIndex + 1)
})

const replayCursorBar = computed(() => {
  if (!isReplayMode.value) {
    return null
  }

  const cursorIndex = replayCursorIndex.value
  if (cursorIndex === null || cursorIndex < 0) {
    return null
  }

  return getSortedKLineList()[cursorIndex] ?? null
})

const hasReplayNext = computed(() => {
  const cursorIndex = replayCursorIndex.value
  if (!isReplayMode.value || cursorIndex === null) {
    return false
  }

  return cursorIndex < getSortedKLineList().length - 1
})

const replayTimeLabel = computed(() => {
  const targetBar = replayCursorBar.value
  if (!targetBar) {
    return ''
  }

  const targetDate = new Date(normalizeTimeToMilliseconds(targetBar.time))
  const year = targetDate.getFullYear()
  const month = String(targetDate.getMonth() + 1).padStart(2, '0')
  const day = String(targetDate.getDate()).padStart(2, '0')
  const hour = String(targetDate.getHours()).padStart(2, '0')
  const minute = String(targetDate.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hour}:${minute}`
})

const clearRealtimeSubscriptions = () => {
  realtimeSubscriptionIntervals.forEach((intervalId) => {
    window.clearInterval(intervalId)
  })
  realtimeSubscriptionIntervals.clear()
}

const loadChartingLibrary = () => {
  if (window.TradingView?.widget) {
    return Promise.resolve()
  }

  if (libraryPromise) {
    return libraryPromise
  }

  libraryPromise = new Promise<void>((resolve, reject) => {
    const existingScript = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Failed to load charting_library')), {
        once: true,
      })
      return
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = `${TRADING_VIEW_LIBRARY_PATH}charting_library.js`
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load charting_library'))
    document.head.appendChild(script)
  })

  return libraryPromise
}

const clearChartAutoSaveTimeout = () => {
  if (chartAutoSaveTimeoutId === null) {
    return
  }

  window.clearTimeout(chartAutoSaveTimeoutId)
  chartAutoSaveTimeoutId = null
}

const saveCurrentChartState = async (token: number, symbol: string, interval: string) => {
  const currentWidget = widget
  if (!currentWidget || token !== createWidgetToken || isRestoringPersistence) {
    return
  }

  saveLocalStudyTemplate(currentWidget)

  const drawingsContent = getDrawingsStateContent(currentWidget)
  if (!drawingsContent || token !== createWidgetToken) {
    return
  }

  await saveChartPersistence({
    symbol,
    interval,
    drawings_content: drawingsContent,
  })
}

const scheduleChartAutoSave = (token: number, symbol: string, interval: string) => {
  if (isRestoringPersistence) {
    return
  }

  clearChartAutoSaveTimeout()
  chartAutoSaveTimeoutId = window.setTimeout(() => {
    chartAutoSaveTimeoutId = null
    void saveCurrentChartState(token, symbol, interval)
  }, 800)
}

const restoreWidgetPersistence = async (
  currentWidget: TradingViewWidget,
  persistence: FutureChartPersistence | null,
  token: number,
) => {
  const restoreToken = ++chartRestoreToken
  isRestoringPersistence = true
  try {
    if (token !== createWidgetToken || widget !== currentWidget) {
      return { appliedLocalStudyTemplate: false }
    }

    return await restoreChartPersistence(currentWidget, persistence)
  } finally {
    if (restoreToken === chartRestoreToken) {
      isRestoringPersistence = false
    }
  }
}

const resetWidgetHandlers = () => {
  crossHairHandler = null
  onDataLoadedHandler = null
  onSymbolChangedHandler = null
  onIntervalChangedHandler = null
  onAutoSaveNeededHandler = null
}

const teardownWidget = () => {
  const currentWidget = widget
  widget = null
  datafeedController = null
  clearChartAutoSaveTimeout()
  clearRealtimeSubscriptions()

  if (!currentWidget) {
    resetWidgetHandlers()
    return
  }

  try {
    const activeChart = currentWidget.activeChart()

    if (crossHairHandler) {
      activeChart.crossHairMoved().unsubscribe(null, crossHairHandler)
    }
    if (onDataLoadedHandler) {
      activeChart.onDataLoaded().unsubscribe(null, onDataLoadedHandler)
    }
    if (onSymbolChangedHandler) {
      activeChart.onSymbolChanged().unsubscribe(null, onSymbolChangedHandler)
    }
    if (onIntervalChangedHandler) {
      activeChart.onIntervalChanged().unsubscribe(null, onIntervalChangedHandler)
    }
    if (onAutoSaveNeededHandler) {
      currentWidget.unsubscribe('onAutoSaveNeeded', onAutoSaveNeededHandler)
    }
  } catch {
    // Ignore disposal races when the library has already torn down its internals.
  } finally {
    resetWidgetHandlers()
  }

  try {
    currentWidget.remove()
  } catch {
    // Ignore repeated widget disposal during route changes.
  }
}

const applyVisibleRange = async () => {
  if (!widget) {
    return
  }

  const kLineList = displayedKLineList.value
  if (!kLineList.length) {
    return
  }

  const visibleBars = kLineList.slice(-INITIAL_VISIBLE_K_LINE_COUNT)
  const firstBar = visibleBars[0]
  const lastBar = visibleBars[visibleBars.length - 1]

  if (!firstBar || !lastBar) {
    return
  }

  try {
    await widget.activeChart().setVisibleRange(
      {
        from: normalizeTimeToSeconds(firstBar.time),
        to: normalizeTimeToSeconds(lastBar.time),
      },
      {
        percentRightMargin: 6,
      },
    )
  } catch {
    // Ignore chart range adjustments that fail during widget teardown/rebuild.
  }
}

const emitCrosshairBar = (time?: number) => {
  if (!time) {
    hoveredKLine.value = null
    emit('crosshair-move', null)
    return
  }

  const targetTime = normalizeTimeToMilliseconds(time)
  const matchedItem = getSortedKLineList().find((item) => normalizeTimeToMilliseconds(item.time) === targetTime)

  hoveredKLine.value = matchedItem ?? null
  emit('crosshair-move', matchedItem ?? null)
}

const enterReplayMode = () => {
  const targetBar = hoveredKLine.value
  if (!targetBar) {
    ElMessage.warning('请先把十字光标移动到要开始回放的 K 线上')
    return
  }

  const targetTime = normalizeTimeToMilliseconds(targetBar.time)
  const targetIndex = getSortedKLineList().findIndex(
    (item) => normalizeTimeToMilliseconds(item.time) === targetTime,
  )

  if (targetIndex < 0) {
    ElMessage.warning('未找到对应的 K 线，暂时无法进入回放')
    return
  }

  replayCursorIndex.value = targetIndex
  isReplayMode.value = true
}

const stepReplayForward = () => {
  if (!isReplayMode.value) {
    return
  }

  const cursorIndex = replayCursorIndex.value
  const sortedList = getSortedKLineList()
  if (cursorIndex === null || cursorIndex >= sortedList.length - 1) {
    return
  }

  const nextCursorIndex = cursorIndex + 1
  const nextBar = sortedList[nextCursorIndex]
  if (!nextBar) {
    return
  }

  replayCursorIndex.value = nextCursorIndex
  hoveredKLine.value = nextBar
  emit('crosshair-move', nextBar)

  const replayBar = getTradingViewBars([nextBar])[0]
  if (replayBar) {
    datafeedController?.pushBar(replayBar)
    widget?.resetCache?.()
    widget?.activeChart().resetData?.()
  }
}

const exitReplayMode = () => {
  isReplayMode.value = false
  replayCursorIndex.value = null
}

const createWidget = async () => {
  if (!chartContainer.value) {
    return
  }

  const token = ++createWidgetToken
  const kLineList = displayedKLineList.value

  await loadChartingLibrary()

  if (token !== createWidgetToken || !chartContainer.value || !window.TradingView?.widget) {
    return
  }

  teardownWidget()
  chartContainer.value.innerHTML = ''

  const bars = getTradingViewBars(kLineList)
  const resolution = getBarResolution(kLineList, props.selectedPeriod)
  const persistenceSymbol = symbolName.value
  const persistenceInterval = getPersistenceInterval(resolution, props.selectedPeriod)
  const persistence = await loadChartPersistence(persistenceSymbol, persistenceInterval)

  if (token !== createWidgetToken || !chartContainer.value || !window.TradingView?.widget) {
    return
  }

  const datafeed = createDatafeed({
    bars,
    resolution,
    name: persistenceSymbol,
    selectedPeriod: props.selectedPeriod,
    currentSymbol: symbolName.value,
    availableContracts: props.contractOptions,
    periodOptions: props.periodOptions,
    sortedKLineList: kLineList,
    onSelectedPeriodChange: (value) => emit('update:selectedPeriod', value),
    enableRealtime: !isReplayMode.value,
    realtimeSubscriptionIntervals,
  })
  datafeedController = datafeed.controller

  widget = new window.TradingView.widget({
    container: chartContainer.value,
    library_path: TRADING_VIEW_LIBRARY_PATH,
    datafeed,
    symbol: persistenceSymbol,
    interval: resolution,
    time_frames: getTimeFrames(props.periodOptions),
    locale: 'zh',
    timezone: 'Asia/Shanghai',
    autosize: props.autosize,
    fullscreen: false,
    theme: 'Light',
    auto_save_delay: 1,
    disabled_features: [
      'header_compare',
      'popup_hints',
      'long_press_floating_tooltip',
    ],
    enabled_features: ['move_logo_to_main_pane', 'saveload_separate_drawings_storage'],
    custom_indicators_getter: getCustomIndicators,
    // 仅仅保留EMA和MACD指标
    studies_access: {
      type: 'white',
      tools: getWhitelistedStudyTools(),
    },
    overrides: {
      'mainSeriesProperties.candleStyle.upColor': '#F23645',
      'mainSeriesProperties.candleStyle.downColor': '#089981',
      'mainSeriesProperties.candleStyle.borderUpColor': '#F23645',
      'mainSeriesProperties.candleStyle.borderDownColor': '#089981',
      'mainSeriesProperties.candleStyle.wickUpColor': '#F23645',
      'mainSeriesProperties.candleStyle.wickDownColor': '#089981',
      'mainSeriesProperties.showPriceLine': true,
      'mainSeriesProperties.priceLineWidth': 1,
      'mainSeriesProperties.priceAxisProperties.autoScale': true,
    },
  })

  widget.onChartReady(() => {
    const currentWidget = widget
    if (!currentWidget || token !== createWidgetToken) {
      return
    }
    const shouldApplyInitialVisibleRange = true

    crossHairHandler = (params) => {
      emitCrosshairBar(params.time)
    }
    currentWidget.activeChart().crossHairMoved().subscribe(null, crossHairHandler)

    if (shouldApplyInitialVisibleRange) {
      onDataLoadedHandler = () => {
        void applyVisibleRange()
      }
      currentWidget.activeChart().onDataLoaded().subscribe(null, onDataLoadedHandler, true)
    }

    onSymbolChangedHandler = (symbol) => {
      const nextSymbol = symbol.ticker || symbol.name
      if (nextSymbol && nextSymbol !== props.selectedContract) {
        emit('update:selectedContract', nextSymbol)
      }
    }
    currentWidget.activeChart().onSymbolChanged().subscribe(null, onSymbolChangedHandler)

    onIntervalChangedHandler = (interval) => {
      const nextPeriod = periodValueFromResolution(interval)
      if (String(nextPeriod) !== String(props.selectedPeriod)) {
        emit('update:selectedPeriod', nextPeriod)
      }
    }
    currentWidget.activeChart().onIntervalChanged().subscribe(null, onIntervalChangedHandler)

    onAutoSaveNeededHandler = () => {
      scheduleChartAutoSave(token, persistenceSymbol, persistenceInterval)
    }
    currentWidget.subscribe('onAutoSaveNeeded', onAutoSaveNeededHandler)

    void (async () => {
      const restoreResult = await restoreWidgetPersistence(currentWidget, persistence, token)
      if (token !== createWidgetToken || widget !== currentWidget) {
        return
      }
      if (!restoreResult?.appliedLocalStudyTemplate) {
        addDefaultCustomStudies(currentWidget)
      }
      if (
        shouldApplyInitialVisibleRange
        && token === createWidgetToken
        && widget === currentWidget
      ) {
        void applyVisibleRange()
      }
    })()
  })
}

onMounted(() => {
  void createWidget()
})

onUnmounted(() => {
  createWidgetToken += 1
  teardownWidget()
})

watch(
  () => [
    props.data.kLineList,
    props.data.symbol,
    props.data.name,
    props.selectedPeriod,
    props.contractOptions,
    props.periodOptions,
  ],
  () => {
    hoveredKLine.value = null
    emit('crosshair-move', null)
    if (isReplayMode.value || replayCursorIndex.value !== null) {
      exitReplayMode()
      return
    }
    void createWidget()
  },
  { deep: true },
)

watch(
  () => props.autosize,
  () => {
    void createWidget()
  },
)

watch(
  () => props.commonChartOptions,
  () => {
    void createWidget()
  },
  { deep: true },
)

watch(
  () => isReplayMode.value,
  () => {
    emit('crosshair-move', replayCursorBar.value)
    void createWidget()
  },
)

defineExpose({
  getChart: () => widget,
  getKSeries: () => null,
  getEma20Series: () => null,
  getEma120Series: () => null,
})
</script>

<template>
  <div class="tv-chart-wrap">
    <div class="replay-toolbar">
      <template v-if="isReplayMode">
        <div class="replay-status">
          <span class="replay-status__tag">历史回放</span>
          <span class="replay-status__time">{{ replayTimeLabel }}</span>
        </div>
        <div class="replay-actions">
          <el-button size="small" type="primary" :disabled="!hasReplayNext" @click="stepReplayForward">
            下一根
          </el-button>
          <el-button size="small" @click="exitReplayMode">退出回放</el-button>
        </div>
      </template>
      <template v-else>
        <el-button size="small" @click="enterReplayMode">进入回放</el-button>
      </template>
    </div>
    <div ref="chartContainer" class="tv-chart"></div>
    <ChartSidebar
      :contract-options="contractOptions"
      :selected-contract="selectedContract"
      @update:selected-contract="emit('update:selectedContract', $event)"
    />
  </div>
</template>

<style lang="less" scoped>
.tv-chart-wrap {
  width: 100%;
  // height: 50rem;
  height: calc(100vh - 3.5rem);
  position: relative;
  background: #ffffff;
}

.replay-toolbar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.replay-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1f2937;
  font-size: 12px;
  line-height: 1;
}

.replay-status__tag {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-weight: 600;
}

.replay-status__time {
  font-variant-numeric: tabular-nums;
}

.replay-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tv-chart {
  width: 100%;
  height: 100%;
}
</style>
