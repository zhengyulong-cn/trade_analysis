import { getFutureRealtimeBarApi, mapRealtimeBarToChartData } from '@/api/modules'
import type { ContractOption, KLineItem, PeriodOption, TradingViewBar } from '@/components/charts/chartModels'

const DEFAULT_RESOLUTION = '5'
const DEFAULT_PRICE_SCALE = 100

export const normalizeTimeToMilliseconds = (value: number) => {
  return value >= 1_000_000_000_000 ? value : value * 1000
}

export const normalizeTimeToSeconds = (value: number) => {
  const milliseconds = normalizeTimeToMilliseconds(value)
  return Math.floor(milliseconds / 1000)
}

export const getPersistenceInterval = (resolution: string, selectedPeriod?: number | string) => {
  if (selectedPeriod !== '' && selectedPeriod !== undefined && selectedPeriod !== null) {
    return String(selectedPeriod)
  }

  return resolution
}

export const resolutionFromPeriodValue = (value: number | string) => {
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

export const periodValueFromResolution = (resolution: string, fallback?: number | string) => {
  const normalized = resolution.trim().toUpperCase()

  if (/^\d+$/.test(normalized)) {
    return Number(normalized) * 60
  }

  const match = normalized.match(/^(\d+)([DWM])$/)
  if (!match) {
    return fallback || DEFAULT_RESOLUTION
  }

  const amount = Number(match[1])
  const unit = match[2]
  if (!Number.isFinite(amount) || amount <= 0) {
    return fallback || DEFAULT_RESOLUTION
  }

  if (unit === 'D') {
    return amount * 24 * 60 * 60
  }
  if (unit === 'W') {
    return amount * 7 * 24 * 60 * 60
  }
  return amount * 30 * 24 * 60 * 60
}

export const getSupportedResolutions = (periodOptions: PeriodOption[]) => {
  const resolutions = periodOptions
    .map((option) => resolutionFromPeriodValue(option.value))
    .filter((value, index, list) => Boolean(value) && list.indexOf(value) === index)

  if (resolutions.length) {
    return resolutions
  }

  return ['1', '5', '15', '30', '60', '120', '240', '1D']
}

export const getTimeFrames = (periodOptions: PeriodOption[]) => {
  const fallbackTexts = ['1D', '5D', '1M', '3M', '6M', '12M']

  return periodOptions.map((option, index) => ({
    text: fallbackTexts[index] ?? '12M',
    resolution: resolutionFromPeriodValue(option.value),
    title: option.label,
    description: option.label,
  }))
}

export const getBarResolution = (kLineList: KLineItem[], selectedPeriod?: number | string) => {
  if (selectedPeriod !== '' && selectedPeriod !== undefined) {
    return resolutionFromPeriodValue(selectedPeriod)
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

export const getTradingViewBars = (kLineList: KLineItem[]): TradingViewBar[] => {
  return kLineList.map((item) => ({
    time: normalizeTimeToMilliseconds(item.time),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
    volume: item.volume,
  }))
}

const getTradingViewBar = (item: KLineItem): TradingViewBar => ({
  time: normalizeTimeToMilliseconds(item.time),
  open: item.open,
  high: item.high,
  low: item.low,
  close: item.close,
  volume: item.volume,
})

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

export interface ChartDatafeedController {
  replaceBars: (nextBars: TradingViewBar[]) => void
  pushBar: (nextBar: TradingViewBar) => void
}

const upsertBar = (sourceBars: TradingViewBar[], nextBar: TradingViewBar) => {
  const lastBar = sourceBars[sourceBars.length - 1]
  if (!lastBar) {
    sourceBars.push(nextBar)
    return
  }

  if (nextBar.time > lastBar.time) {
    sourceBars.push(nextBar)
    return
  }

  if (nextBar.time === lastBar.time) {
    sourceBars[sourceBars.length - 1] = nextBar
  }
}

export const createDatafeed = ({
  bars,
  resolution,
  name,
  selectedPeriod,
  currentSymbol,
  availableContracts,
  periodOptions,
  sortedKLineList,
  onSelectedPeriodChange,
  enableRealtime,
  realtimeSubscriptionIntervals,
}: {
  bars: TradingViewBar[]
  resolution: string
  name: string
  selectedPeriod?: number | string
  currentSymbol: string
  availableContracts: ContractOption[]
  periodOptions: PeriodOption[]
  sortedKLineList: KLineItem[]
  onSelectedPeriodChange: (value: number | string) => void
  enableRealtime: boolean
  realtimeSubscriptionIntervals: Map<string, number>
}) => {
  const currentBars = [...bars]
  const priceScale = getPriceScale(sortedKLineList) || DEFAULT_PRICE_SCALE
  const supportedResolutions = getSupportedResolutions(periodOptions)
  const intradayMultipliers = getIntradayMultipliers(supportedResolutions)
  const dailyMultipliers = getDailyMultipliers(supportedResolutions)
  const subscribers = new Map<
    string,
    {
      onRealtimeCallback: (bar: TradingViewBar) => void
      onResetCacheNeededCallback?: () => void
    }
  >()

  const notifySubscribers = (nextBar: TradingViewBar) => {
    subscribers.forEach((subscriber) => {
      subscriber.onRealtimeCallback(nextBar)
    })
  }

  return {
    controller: {
      replaceBars(nextBars: TradingViewBar[]) {
        currentBars.splice(0, currentBars.length, ...nextBars)
        subscribers.forEach((subscriber) => {
          subscriber.onResetCacheNeededCallback?.()
        })
      },
      pushBar(nextBar: TradingViewBar) {
        upsertBar(currentBars, nextBar)
        notifySubscribers(nextBar)
      },
    } satisfies ChartDatafeedController,
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
          data_status: 'streaming',
        })
      }, 0)
    },
    getBars(
      symbolInfo: Record<string, unknown>,
      requestedResolution: string,
      periodParams: { from: number; to: number; countBack?: number },
      onResult: (history: TradingViewBar[], meta: { noData?: boolean }) => void,
    ) {
      if (getRequestedSymbol(symbolInfo) !== currentSymbol) {
        onResult([], { noData: true })
        return
      }

      const normalizedRequestedResolution = requestedResolution.trim().toUpperCase()
      if (normalizedRequestedResolution && normalizedRequestedResolution !== resolution.toUpperCase()) {
        const requestedPeriod = periodValueFromResolution(normalizedRequestedResolution, selectedPeriod)
        if (String(requestedPeriod) !== String(selectedPeriod)) {
          onSelectedPeriodChange(requestedPeriod)
        }

        onResult([], { noData: true })
        return
      }

      const filteredBars = getBarsInRange(currentBars, periodParams)

      if (filteredBars.length) {
        onResult(filteredBars, { noData: false })
        return
      }

      onResult([], { noData: true })
    },
    subscribeBars(
      symbolInfo: Record<string, unknown>,
      requestedResolution: string,
      onRealtimeCallback: (bar: TradingViewBar) => void,
      subscriberUID: string,
      onResetCacheNeededCallback?: () => void,
    ) {
      subscribers.set(subscriberUID, {
        onRealtimeCallback,
        onResetCacheNeededCallback,
      })

      if (!enableRealtime) {
        return undefined
      }

      if (getRequestedSymbol(symbolInfo) !== currentSymbol) {
        return undefined
      }

      const normalizedRequestedResolution = requestedResolution.trim().toUpperCase()
      if (normalizedRequestedResolution && normalizedRequestedResolution !== resolution.toUpperCase()) {
        return undefined
      }

      const selectedInterval = Number(selectedPeriod)
      if (!Number.isFinite(selectedInterval) || selectedInterval <= 0) {
        return undefined
      }

      let lastEmittedTime = currentBars[currentBars.length - 1]?.time ?? 0
      let isFetchingRealtimeBar = false
      let hasRealtimeFetchFailed = false
      const fetchRealtimeBar = async () => {
        if (isFetchingRealtimeBar) {
          return
        }
        isFetchingRealtimeBar = true
        try {
          const response = await getFutureRealtimeBarApi({
            symbol: currentSymbol,
            interval: selectedInterval,
          })
          if (!response.bar) {
            return
          }

          const chartBar = mapRealtimeBarToChartData(response.bar)
          if (!chartBar) {
            return
          }

          const realtimeBar = getTradingViewBar(chartBar)
          if (realtimeBar.time < lastEmittedTime) {
            return
          }

          lastEmittedTime = realtimeBar.time
          hasRealtimeFetchFailed = false
          upsertBar(currentBars, realtimeBar)
          notifySubscribers(realtimeBar)
        } catch {
          if (hasRealtimeFetchFailed) {
            return
          }
          hasRealtimeFetchFailed = true
        } finally {
          isFetchingRealtimeBar = false
        }
      }

      void fetchRealtimeBar()
      const intervalId = window.setInterval(() => {
        void fetchRealtimeBar()
      }, 1000)
      realtimeSubscriptionIntervals.set(subscriberUID, intervalId)
      return undefined
    },
    unsubscribeBars(subscriberUID: string) {
      subscribers.delete(subscriberUID)
      const intervalId = realtimeSubscriptionIntervals.get(subscriberUID)
      if (intervalId !== undefined) {
        window.clearInterval(intervalId)
        realtimeSubscriptionIntervals.delete(subscriberUID)
      }
      return undefined
    },
    _resolution: resolution,
  }
}
