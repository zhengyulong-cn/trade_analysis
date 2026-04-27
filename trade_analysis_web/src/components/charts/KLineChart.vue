<script setup lang="ts">
import {
  getFutureChartPersistenceApi,
  saveFutureChartPersistenceApi,
  type FutureChartPersistence,
  type FutureChartPersistenceSaveParams,
} from '@/api/modules'
import { INITIAL_VISIBLE_K_LINE_COUNT } from '@/constants/chart'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import ChartSidebar from './ChartSidebar.vue'

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
  createStudyTemplate?: (options?: { saveSymbol?: boolean; saveInterval?: boolean }) => object
  applyStudyTemplate?: (template: object) => void
  getLineToolsState?: () => TradingViewLineToolsAndGroupsState
  applyLineToolsState?: (state: TradingViewLineToolsAndGroupsState) => Promise<void>
  setVisibleRange: (range: { from: number; to: number }, options?: Record<string, unknown>) => Promise<void>
}

interface TradingViewWidget {
  onChartReady: (callback: () => void) => void
  subscribe: (event: string, callback: () => void) => void
  unsubscribe: (event: string, callback: () => void) => void
  activeChart: () => TradingViewActiveChart
  remove: () => void
}

interface TradingViewLineToolsAndGroupsState {
  sources: Map<string, unknown | null> | null
  groups: Map<string, unknown | null>
  symbol?: string
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
const LOCAL_STUDY_TEMPLATE_KEY = 'trade-analysis:charting-library:study-template'

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
let onAutoSaveNeededHandler: (() => void) | null = null
let createWidgetToken = 0
let libraryPromise: Promise<void> | null = null
let chartAutoSaveTimeoutId: number | null = null
let isRestoringPersistence = false
let chartRestoreToken = 0

const symbolName = computed(() => {
  return props.selectedContract?.trim() || props.data.symbol?.trim() || props.data.name?.trim() || DEFAULT_SYMBOL
})

const MAP_SERIALIZATION_TYPE = '__tradingViewMap'

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const isMapLike = (value: unknown): value is Map<unknown, unknown> => {
  return (
    Object.prototype.toString.call(value) === '[object Map]'
    && typeof (value as Map<unknown, unknown>).entries === 'function'
  )
}

const stringifyChartJson = (value: unknown) => {
  try {
    return JSON.stringify(value, (_key, item) => {
      if (isMapLike(item)) {
        return {
          type: MAP_SERIALIZATION_TYPE,
          entries: Array.from(item.entries()),
        }
      }

      return item
    })
  } catch (error) {
    console.warn('Failed to stringify chart persistence content', error)
    return null
  }
}

const parseChartJson = <T,>(content?: string | null): T | null => {
  if (!content) {
    return null
  }

  try {
    return JSON.parse(content, (_key, item) => {
      if (
        isRecord(item)
        && item.type === MAP_SERIALIZATION_TYPE
        && Array.isArray(item.entries)
      ) {
        return new Map(item.entries as Array<[unknown, unknown]>)
      }

      return item
    }) as T
  } catch (error) {
    console.warn('Failed to parse chart persistence content', error)
    return null
  }
}

const getPersistenceInterval = (resolution: string) => {
  if (props.selectedPeriod !== '' && props.selectedPeriod !== undefined && props.selectedPeriod !== null) {
    return String(props.selectedPeriod)
  }

  return resolution
}

const loadChartPersistence = async (symbol: string, interval: string) => {
  try {
    return await getFutureChartPersistenceApi({ symbol, interval })
  } catch (error) {
    console.warn('Failed to load chart persistence', error)
    return null
  }
}

const saveChartPersistence = async (payload: FutureChartPersistenceSaveParams) => {
  try {
    await saveFutureChartPersistenceApi(payload)
  } catch (error) {
    console.warn('Failed to save chart persistence', error)
  }
}

const loadLocalStudyTemplate = () => {
  try {
    return parseChartJson<object>(window.localStorage.getItem(LOCAL_STUDY_TEMPLATE_KEY))
  } catch (error) {
    console.warn('Failed to load local study template', error)
    return null
  }
}

const saveLocalStudyTemplate = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  const createStudyTemplate = activeChart.createStudyTemplate
  if (!createStudyTemplate) {
    return
  }

  try {
    const content = stringifyChartJson(
      createStudyTemplate.call(activeChart, {
        saveSymbol: false,
        saveInterval: false,
      }),
    )
    if (content) {
      window.localStorage.setItem(LOCAL_STUDY_TEMPLATE_KEY, content)
    }
  } catch (error) {
    console.warn('Failed to save local study template', error)
  }
}

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

const clearChartAutoSaveTimeout = () => {
  if (chartAutoSaveTimeoutId === null) {
    return
  }

  window.clearTimeout(chartAutoSaveTimeoutId)
  chartAutoSaveTimeoutId = null
}

const getDrawingsStateContent = (currentWidget: TradingViewWidget) => {
  const activeChart = currentWidget.activeChart()
  if (!activeChart.getLineToolsState) {
    return null
  }

  try {
    return stringifyChartJson(activeChart.getLineToolsState())
  } catch (error) {
    console.warn('Failed to collect chart drawings state', error)
    return null
  }
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

const restoreChartPersistence = async (
  currentWidget: TradingViewWidget,
  persistence: FutureChartPersistence | null,
  token: number,
) => {
  const restoreToken = ++chartRestoreToken
  isRestoringPersistence = true
  try {
    const activeChart = currentWidget.activeChart()
    const localStudyTemplate = loadLocalStudyTemplate()
    const applyStudyTemplate = activeChart.applyStudyTemplate
    if (
      localStudyTemplate
      && token === createWidgetToken
      && widget === currentWidget
      && applyStudyTemplate
    ) {
      applyStudyTemplate.call(activeChart, localStudyTemplate)
    }

    const applyLineToolsState = activeChart.applyLineToolsState
    const drawingsState = parseChartJson<TradingViewLineToolsAndGroupsState>(persistence?.drawings_content)
    if (
      drawingsState
      && token === createWidgetToken
      && widget === currentWidget
      && applyLineToolsState
    ) {
      await applyLineToolsState.call(activeChart, drawingsState)
    }
  } catch (error) {
    console.warn('Failed to restore chart persistence', error)
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
  clearChartAutoSaveTimeout()

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

  await loadChartingLibrary()

  if (token !== createWidgetToken || !chartContainer.value || !window.TradingView?.widget) {
    return
  }

  teardownWidget()
  chartContainer.value.innerHTML = ''

  const bars = getTradingViewBars(kLineList)
  const resolution = getBarResolution(kLineList)
  const persistenceSymbol = symbolName.value
  const persistenceInterval = getPersistenceInterval(resolution)
  const persistence = await loadChartPersistence(persistenceSymbol, persistenceInterval)

  if (token !== createWidgetToken || !chartContainer.value || !window.TradingView?.widget) {
    return
  }

  const datafeed = createDatafeed(bars, resolution, persistenceSymbol)

  widget = new window.TradingView.widget({
    container: chartContainer.value,
    library_path: TRADING_VIEW_LIBRARY_PATH,
    datafeed,
    symbol: persistenceSymbol,
    interval: resolution,
    time_frames: getTimeFrames(),
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
    // 仅仅保留EMA和MACD指标
    studies_access: {
      type: 'white',
      tools: [
        { name: 'EMA Cross' },
        { name: 'MACD' },
      ],
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
      await restoreChartPersistence(currentWidget, persistence, token)
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

.tv-chart {
  width: 100%;
  height: 100%;
}
</style>
