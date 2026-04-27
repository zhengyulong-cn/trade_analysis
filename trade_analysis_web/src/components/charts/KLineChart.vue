<script setup lang="ts">
import { INITIAL_VISIBLE_K_LINE_COUNT } from '@/constants/chart'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface KLineItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  ema20?: number
  ema120?: number
  volume?: number
}

interface SegmentLineItem {
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
  segment: SegmentLineItem
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
  segment: SegmentLineItem
}

interface ContractOption {
  label: string
  value: string
  description?: string
  isFavorite?: boolean
}

interface PeriodOption {
  label: string
  value: number | string
}

interface TradingViewBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

interface TradingViewSubscription<TArgs extends unknown[]> {
  subscribe: (context: object | null, handler: (...args: TArgs) => void, singleshot?: boolean) => void
  unsubscribe: (context: object | null, handler: (...args: TArgs) => void) => void
}

interface TradingViewActiveChart {
  crossHairMoved: () => TradingViewSubscription<[{
    time?: number
  }]>
  onDataLoaded: () => TradingViewSubscription<[]>
  onSymbolChanged: () => TradingViewSubscription<[{
    name: string
    ticker?: string
  }]>
  onIntervalChanged: () => TradingViewSubscription<[string, Record<string, unknown>]>
  setVisibleRange: (range: { from: number; to: number }, options?: Record<string, unknown>) => Promise<void>
}

interface TradingViewWidget {
  onChartReady: (callback: () => void) => void
  activeChart: () => TradingViewActiveChart
  remove: () => void
}

type TradingViewConstructor = new (options: Record<string, unknown>) => TradingViewWidget

declare global {
  interface Window {
    TradingView?: {
      widget: TradingViewConstructor
    }
  }
}

const TRADING_VIEW_LIBRARY_PATH = '/charting_library/'
const DEFAULT_SYMBOL = 'FUTURES'
const DEFAULT_RESOLUTION = '5'
const DEFAULT_PRICE_SCALE = 100
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
    segmentLines?: SegmentLineItem[]
    autosize?: boolean
    canBuildSegments?: boolean
    canLoadSegments?: boolean
    autoLoadSegments?: boolean
    commonChartOptions?: Record<string, unknown>
  }>(),
  {
    selectedContract: '',
    selectedPeriod: '',
    contractOptions: () => [],
    periodOptions: () => [],
    segmentLines: () => [],
    autosize: true,
    canBuildSegments: true,
    canLoadSegments: true,
    autoLoadSegments: false,
    commonChartOptions: () => ({}),
  },
)

const emit = defineEmits<{
  'update:selectedContract': [value: string]
  'update:selectedPeriod': [value: number | string]
  'crosshair-move': [value: KLineItem | null]
  'segment-line-change': [value: SegmentLineChange]
  'segment-line-create': [value: SegmentLineCreate]
  'segment-line-delete': [value: SegmentLineDelete]
  'segment-build-request': []
  'segment-load-request': []
  'segment-auto-load-toggle': []
}>()

const chartContainer = ref<HTMLDivElement | null>(null)

let widget: TradingViewWidget | null = null
let crossHairHandler: ((params: { time?: number }) => void) | null = null
let onDataLoadedHandler: (() => void) | null = null
let onSymbolChangedHandler: ((symbol: { name: string; ticker?: string }) => void) | null = null
let onIntervalChangedHandler: ((interval: string, timeFrameParameters: Record<string, unknown>) => void) | null = null
let createWidgetToken = 0
let libraryPromise: Promise<void> | null = null

const symbolName = computed(() => {
  return props.selectedContract?.trim() || props.data.symbol?.trim() || props.data.name?.trim() || DEFAULT_SYMBOL
})

const normalizeTimeToMilliseconds = (value: number) => {
  return value >= 1_000_000_000_000 ? value : value * 1000
}

const normalizeTimeToSeconds = (value: number) => {
  const milliseconds = normalizeTimeToMilliseconds(value)
  return Math.floor(milliseconds / 1000)
}

const getSortedKLineList = () => {
  return [...(props.data.kLineList ?? [])].sort((first, second) => first.time - second.time)
}

const resolutionFromPeriodValue = (value: number | string) => {
  const period = Number(value)
  if (!Number.isFinite(period) || period <= 0) {
    return DEFAULT_RESOLUTION
  }

  const minutes = Math.round(period / 60)
  if (minutes <= 0) {
    return DEFAULT_RESOLUTION
  }

  if (minutes % (60 * 24) === 0) {
    const days = minutes / (60 * 24)
    return days === 1 ? '1D' : `${days}D`
  }

  return String(minutes)
}

const periodValueFromResolution = (resolution: string) => {
  const normalized = resolution.trim().toUpperCase()

  if (/^\d+$/.test(normalized)) {
    return Number(normalized) * 60
  }

  const match = normalized.match(/^(\d+)([DWM])$/)
  if (!match) {
    return props.selectedPeriod || DEFAULT_RESOLUTION
  }

  const amount = Number(match[1])
  const unit = match[2]
  if (!Number.isFinite(amount) || amount <= 0) {
    return props.selectedPeriod || DEFAULT_RESOLUTION
  }

  if (unit === 'D') {
    return amount * 24 * 60 * 60
  }
  if (unit === 'W') {
    return amount * 7 * 24 * 60 * 60
  }
  return amount * 30 * 24 * 60 * 60
}

const getSupportedResolutions = () => {
  const resolutions = props.periodOptions
    .map((option) => resolutionFromPeriodValue(option.value))
    .filter((value, index, list) => Boolean(value) && list.indexOf(value) === index)

  if (resolutions.length) {
    return resolutions
  }

  return ['1', '5', '15', '30', '60', '120', '240', '1D']
}

const getTimeFrames = () => {
  const fallbackTexts = ['1D', '5D', '1M', '3M', '6M', '12M']

  return props.periodOptions.map((option, index) => ({
    text: fallbackTexts[index] ?? '12M',
    resolution: resolutionFromPeriodValue(option.value),
    title: option.label,
    description: option.label,
  }))
}

const getBarResolution = (kLineList: KLineItem[]) => {
  if (props.selectedPeriod !== '' && props.selectedPeriod !== undefined) {
    return resolutionFromPeriodValue(props.selectedPeriod)
  }

  if (kLineList.length < 2) {
    return DEFAULT_RESOLUTION
  }

  const durations: number[] = []
  for (let index = 1; index < kLineList.length; index += 1) {
    const previousItem = kLineList[index - 1]
    const currentItem = kLineList[index]

    if (!previousItem || !currentItem) {
      continue
    }

    const duration = currentItem.time - previousItem.time
    if (Number.isFinite(duration) && duration > 0) {
      durations.push(duration)
    }
  }

  if (!durations.length) {
    return DEFAULT_RESOLUTION
  }

  const duration = durations[Math.floor(durations.length / 2)] ?? 300
  const minutes = Math.round(duration / 60)

  if (minutes <= 0) {
    return DEFAULT_RESOLUTION
  }

  if (minutes % (60 * 24) === 0) {
    const days = minutes / (60 * 24)
    return days === 1 ? '1D' : `${days}D`
  }

  return String(minutes)
}

const getPriceScale = (kLineList: KLineItem[]) => {
  let maxDecimals = 0

  for (const item of kLineList) {
    for (const value of [item.open, item.high, item.low, item.close]) {
      const decimalPart = String(value).split('.')[1] ?? ''
      maxDecimals = Math.max(maxDecimals, decimalPart.length)
    }
  }

  if (maxDecimals <= 0) {
    return 1
  }

  return 10 ** Math.min(maxDecimals, 8)
}

const getTradingViewBars = (kLineList: KLineItem[]): TradingViewBar[] => {
  return kLineList.map((item) => ({
    time: normalizeTimeToMilliseconds(item.time),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
    volume: item.volume,
  }))
}

const getRequestedSymbol = (symbolInfo: Record<string, unknown>) => {
  const ticker = typeof symbolInfo.ticker === 'string' ? symbolInfo.ticker : ''
  const name = typeof symbolInfo.name === 'string' ? symbolInfo.name : ''
  return ticker || name
}

const getIntradayMultipliers = (resolutions: string[]) => {
  return resolutions.filter((resolution) => /^\d+$/.test(resolution))
}

const getDailyMultipliers = (resolutions: string[]) => {
  return resolutions
    .filter((resolution) => /^\d+D$/i.test(resolution))
    .map((resolution) => resolution.replace(/D$/i, ''))
}

const getBarsInRange = (
  sourceBars: TradingViewBar[],
  periodParams: { from: number; to: number; countBack?: number },
) => {
  const fromMilliseconds = periodParams.from * 1000
  const toMilliseconds = periodParams.to * 1000
  const barsBeforeTo = sourceBars.filter((bar) => bar.time <= toMilliseconds)
  const barsInRange = barsBeforeTo.filter((bar) => bar.time >= fromMilliseconds)
  const countBack = Number(periodParams.countBack)

  if (Number.isFinite(countBack) && countBack > barsInRange.length) {
    const missingCount = countBack - barsInRange.length
    const barsBeforeRange = barsBeforeTo.filter((bar) => bar.time < fromMilliseconds)
    return [...barsBeforeRange.slice(-missingCount), ...barsInRange]
  }

  if (barsInRange.length) {
    return barsInRange
  }

  if (Number.isFinite(countBack) && countBack > 0 && barsBeforeTo.length) {
    return barsBeforeTo.slice(-countBack)
  }

  return []
}

const createDatafeed = (bars: TradingViewBar[], resolution: string, name: string) => {
  const priceScale = getPriceScale(getSortedKLineList()) || DEFAULT_PRICE_SCALE
  const supportedResolutions = getSupportedResolutions()
  const intradayMultipliers = getIntradayMultipliers(supportedResolutions)
  const dailyMultipliers = getDailyMultipliers(supportedResolutions)
  const currentSymbol = symbolName.value
  const availableContracts = props.contractOptions

  return {
    onReady(callback: (config: Record<string, unknown>) => void) {
      window.setTimeout(() => {
        callback({
          supported_resolutions: supportedResolutions,
          supports_marks: false,
          supports_timescale_marks: false,
          supports_time: false,
          has_intraday: intradayMultipliers.length > 0,
          intraday_multipliers: intradayMultipliers,
          has_daily: dailyMultipliers.length > 0,
          daily_multipliers: dailyMultipliers,
        })
      }, 0)
    },
    searchSymbols(
      userInput: string,
      _exchange: string,
      _symbolType: string,
      onResult: (items: Array<Record<string, string>>) => void,
    ) {
      const keyword = userInput.trim().toLowerCase()
      const candidates = (availableContracts.length ? availableContracts : [{ value: name, description: name }])
        .filter((contract) => {
          if (!keyword) {
            return true
          }

          const description = contract.description?.toLowerCase() ?? ''
          return contract.value.toLowerCase().includes(keyword) || description.includes(keyword)
        })
        .map((contract) => ({
          symbol: contract.value,
          full_name: contract.value,
          description: contract.description ?? contract.value,
          exchange: 'LOCAL',
          ticker: contract.value,
          type: 'futures',
        }))

      onResult(candidates)
    },
    resolveSymbol(
      requestedSymbol: string,
      onResolve: (symbolInfo: Record<string, unknown>) => void,
      _onError: (reason: string) => void,
    ) {
      const matchedContract = availableContracts.find((contract) => contract.value === requestedSymbol)

      window.setTimeout(() => {
        onResolve({
          ticker: requestedSymbol,
          name: requestedSymbol,
          description: matchedContract?.description ?? requestedSymbol,
          type: 'futures',
          session: '24x7',
          timezone: 'Asia/Shanghai',
          exchange: 'LOCAL',
          minmov: 1,
          pricescale: priceScale,
          has_intraday: intradayMultipliers.length > 0,
          intraday_multipliers: intradayMultipliers,
          has_daily: dailyMultipliers.length > 0,
          daily_multipliers: dailyMultipliers,
          has_weekly_and_monthly: false,
          visible_plots_set: 'ohlc',
          supported_resolutions: supportedResolutions,
          volume_precision: 0,
          data_status: 'endofday',
        })
      }, 0)
    },
    getBars(
      symbolInfo: Record<string, unknown>,
      requestedResolution: string,
      periodParams: { from: number; to: number; countBack?: number },
      onResult: (history: TradingViewBar[], meta: { noData?: boolean }) => void,
      onError: (reason: string) => void,
    ) {
      if (getRequestedSymbol(symbolInfo) !== currentSymbol) {
        onResult([], { noData: true })
        return
      }

      const normalizedRequestedResolution = requestedResolution.trim().toUpperCase()
      if (normalizedRequestedResolution && normalizedRequestedResolution !== resolution.toUpperCase()) {
        const requestedPeriod = periodValueFromResolution(normalizedRequestedResolution)
        if (String(requestedPeriod) !== String(props.selectedPeriod)) {
          emit('update:selectedPeriod', requestedPeriod)
        }

        onResult([], { noData: true })
        return
      }

      const filteredBars = getBarsInRange(bars, periodParams)

      if (filteredBars.length) {
        onResult(filteredBars, { noData: false })
        return
      }

      onResult([], { noData: true })
    },
    subscribeBars() {
      return undefined
    },
    unsubscribeBars() {
      return undefined
    },
    _resolution: resolution,
  }
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

const resetWidgetHandlers = () => {
  crossHairHandler = null
  onDataLoadedHandler = null
  onSymbolChangedHandler = null
  onIntervalChangedHandler = null
}

const teardownWidget = () => {
  const currentWidget = widget
  widget = null

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

  const kLineList = getSortedKLineList()
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
    emit('crosshair-move', null)
    return
  }

  const targetTime = normalizeTimeToMilliseconds(time)
  const matchedItem = getSortedKLineList().find((item) => normalizeTimeToMilliseconds(item.time) === targetTime)

  emit('crosshair-move', matchedItem ?? null)
}

const createWidget = async () => {
  if (!chartContainer.value) {
    return
  }

  const token = ++createWidgetToken
  const kLineList = getSortedKLineList()

  if (!kLineList.length) {
    teardownWidget()
    return
  }

  await loadChartingLibrary()

  if (token !== createWidgetToken || !chartContainer.value || !window.TradingView?.widget) {
    return
  }

  teardownWidget()
  chartContainer.value.innerHTML = ''

  const bars = getTradingViewBars(kLineList)
  const resolution = getBarResolution(kLineList)
  const datafeed = createDatafeed(bars, resolution, symbolName.value)

  widget = new window.TradingView.widget({
    container: chartContainer.value,
    library_path: TRADING_VIEW_LIBRARY_PATH,
    datafeed,
    symbol: symbolName.value,
    interval: resolution,
    time_frames: getTimeFrames(),
    locale: 'zh',
    timezone: 'Asia/Shanghai',
    autosize: props.autosize,
    fullscreen: false,
    theme: 'Light',
    disabled_features: [
      'use_localstorage_for_settings',
      'display_market_status',
      'compare_symbol',
      'header_compare',
      'header_undo_redo',
      'header_screenshot',
      'header_saveload',
      'show_object_tree',
      'go_to_date',
    ],
    enabled_features: ['move_logo_to_main_pane'],
    overrides: {
      'paneProperties.background': '#ffffff',
      'paneProperties.vertGridProperties.color': '#f0f2f5',
      'paneProperties.horzGridProperties.color': '#f0f2f5',
      'paneProperties.crossHairProperties.color': '#9ca3af',
      'scalesProperties.lineColor': '#ebeef5',
      'scalesProperties.textColor': '#606266',
      'mainSeriesProperties.candleStyle.upColor': '#f56c6c',
      'mainSeriesProperties.candleStyle.downColor': '#67c23a',
      'mainSeriesProperties.candleStyle.borderUpColor': '#f56c6c',
      'mainSeriesProperties.candleStyle.borderDownColor': '#67c23a',
      'mainSeriesProperties.candleStyle.wickUpColor': '#f56c6c',
      'mainSeriesProperties.candleStyle.wickDownColor': '#67c23a',
      'mainSeriesProperties.showPriceLine': true,
      'mainSeriesProperties.priceLineWidth': 1,
      'mainSeriesProperties.priceAxisProperties.autoScale': true,
    },
  })

  widget.onChartReady(() => {
    if (!widget || token !== createWidgetToken) {
      return
    }

    crossHairHandler = (params) => {
      emitCrosshairBar(params.time)
    }
    widget.activeChart().crossHairMoved().subscribe(null, crossHairHandler)

    onDataLoadedHandler = () => {
      void applyVisibleRange()
    }
    widget.activeChart().onDataLoaded().subscribe(null, onDataLoadedHandler)

    onSymbolChangedHandler = (symbol) => {
      const nextSymbol = symbol.ticker || symbol.name
      if (nextSymbol && nextSymbol !== props.selectedContract) {
        emit('update:selectedContract', nextSymbol)
      }
    }
    widget.activeChart().onSymbolChanged().subscribe(null, onSymbolChangedHandler)

    onIntervalChangedHandler = (interval) => {
      const nextPeriod = periodValueFromResolution(interval)
      if (String(nextPeriod) !== String(props.selectedPeriod)) {
        emit('update:selectedPeriod', nextPeriod)
      }
    }
    widget.activeChart().onIntervalChanged().subscribe(null, onIntervalChangedHandler)

    void applyVisibleRange()
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
    emit('crosshair-move', null)
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

defineExpose({
  getChart: () => widget,
  getKSeries: () => null,
  getEma20Series: () => null,
  getEma120Series: () => null,
})
</script>

<template>
  <div class="tv-chart-wrap">
    <div ref="chartContainer" class="tv-chart"></div>
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

.tv-chart {
  width: 100%;
  height: 100%;
}
</style>
