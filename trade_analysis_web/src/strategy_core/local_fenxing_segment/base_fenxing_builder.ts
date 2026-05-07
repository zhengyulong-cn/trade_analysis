import type {
  FenxingBar,
  FenxingBuildState,
  FenxingSignal,
  MergedFenxingBar,
  UpsertFenxingBarResult,
} from './types'

const MAX_INCLUDED_RAW_BAR_COUNT = 4

export const isFiniteNumber = (value: unknown): value is number => {
  return typeof value === 'number' && Number.isFinite(value)
}

export const createEmptyFenxingBuildState = (): FenxingBuildState => ({
  confirmedFenxingSignals: [],
  mergedBars: [],
  processedBarCount: 0,
})

export const upsertFenxingBar = (
  bars: FenxingBar[],
  bar: Omit<FenxingBar, 'index'>,
): UpsertFenxingBarResult => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || bar.time > lastBar.time) {
    bars.push({
      ...bar,
      index: bars.length,
    })
    return {
      index: bars.length - 1,
      type: 'append',
    }
  }

  if (bar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...bar,
      index: lastBar.index,
    }
    return {
      index: lastBar.index,
      type: 'replace_last',
    }
  }

  const existingIndex = bars.findIndex((item) => item.time === bar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...bar,
      index: existingIndex,
    }
    return {
      index: existingIndex,
      type: 'replace_existing',
    }
  }

  bars.push({
    ...bar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((item, index) => {
    item.index = index
  })

  return {
    index: bars.findIndex((item) => item.time === bar.time),
    type: 'insert_historical',
  }
}

const createMergedBar = (bar: FenxingBar): MergedFenxingBar => ({
  firstBarCloseBelowEma20: bar.close < bar.ema20,
  high: bar.high,
  highSourceIndex: bar.index,
  highSourceTime: bar.time,
  index: bar.index,
  low: bar.low,
  lowSourceIndex: bar.index,
  lowSourceTime: bar.time,
  sourceEndIndex: bar.index,
  sourceEndTime: bar.time,
  sourceStartIndex: bar.index,
  sourceStartTime: bar.time,
  time: bar.time,
})

const hasInclusion = (first: MergedFenxingBar, second: MergedFenxingBar) => {
  return (
    (first.high >= second.high && first.low <= second.low)
    || (first.high <= second.high && first.low >= second.low)
  )
}

const canMergeWithinIncludedBarLimit = (first: MergedFenxingBar, second: MergedFenxingBar) => {
  return second.sourceEndIndex - first.sourceStartIndex + 1 <= MAX_INCLUDED_RAW_BAR_COUNT
}

const mergeIncludedBars = (first: MergedFenxingBar, second: MergedFenxingBar): MergedFenxingBar => {
  const mergedHigh = first.firstBarCloseBelowEma20
    ? Math.min(first.high, second.high)
    : Math.max(first.high, second.high)
  const mergedLow = first.firstBarCloseBelowEma20
    ? Math.min(first.low, second.low)
    : Math.max(first.low, second.low)
  const useSecondHigh = first.firstBarCloseBelowEma20 ? second.high < first.high : second.high > first.high
  const useSecondLow = first.firstBarCloseBelowEma20 ? second.low < first.low : second.low > first.low

  return {
    firstBarCloseBelowEma20: first.firstBarCloseBelowEma20,
    high: mergedHigh,
    highSourceIndex: useSecondHigh ? second.highSourceIndex : first.highSourceIndex,
    highSourceTime: useSecondHigh ? second.highSourceTime : first.highSourceTime,
    index: first.index,
    low: mergedLow,
    lowSourceIndex: useSecondLow ? second.lowSourceIndex : first.lowSourceIndex,
    lowSourceTime: useSecondLow ? second.lowSourceTime : first.lowSourceTime,
    sourceEndIndex: second.sourceEndIndex,
    sourceEndTime: second.sourceEndTime,
    sourceStartIndex: first.sourceStartIndex,
    sourceStartTime: first.sourceStartTime,
    time: first.time,
  }
}

const normalizeMergedBarIndexes = (bars: MergedFenxingBar[]) => {
  bars.forEach((bar, index) => {
    bar.index = index
  })
}

const buildFenxingSignal = (
  left: MergedFenxingBar,
  middle: MergedFenxingBar,
  right: MergedFenxingBar,
): FenxingSignal | null => {
  const isTopFenxing = middle.high >= left.high
    && middle.high >= right.high
    && middle.low >= left.low
    && middle.low >= right.low

  if (isTopFenxing) {
    return {
      index: -1,
      mergedBarIndex: middle.index,
      point: {
        index: middle.highSourceIndex,
        price: middle.high,
        time: middle.highSourceTime,
      },
      sourceEndIndex: right.sourceEndIndex,
      sourceEndTime: right.sourceEndTime,
      sourceStartIndex: left.sourceStartIndex,
      sourceStartTime: left.sourceStartTime,
      type: 'top',
    }
  }

  const isBottomFenxing = middle.high <= left.high
    && middle.high <= right.high
    && middle.low <= left.low
    && middle.low <= right.low

  if (isBottomFenxing) {
    return {
      index: -1,
      mergedBarIndex: middle.index,
      point: {
        index: middle.lowSourceIndex,
        price: middle.low,
        time: middle.lowSourceTime,
      },
      sourceEndIndex: right.sourceEndIndex,
      sourceEndTime: right.sourceEndTime,
      sourceStartIndex: left.sourceStartIndex,
      sourceStartTime: left.sourceStartTime,
      type: 'bottom',
    }
  }

  return null
}

const appendConfirmedSignal = (buildState: FenxingBuildState) => {
  const centerIndex = buildState.mergedBars.length - 2
  if (centerIndex < 1) {
    return null
  }

  const left = buildState.mergedBars[centerIndex - 1]
  const middle = buildState.mergedBars[centerIndex]
  const right = buildState.mergedBars[centerIndex + 1]
  if (!left || !middle || !right) {
    return null
  }

  const signal = buildFenxingSignal(left, middle, right)

  if (signal) {
    signal.index = buildState.confirmedFenxingSignals.length
    buildState.confirmedFenxingSignals.push(signal)
  }

  return signal
}

const processFenxingBar = (buildState: FenxingBuildState, bar: FenxingBar) => {
  const nextMergedBar = createMergedBar(bar)
  const previousMergedBar = buildState.mergedBars[buildState.mergedBars.length - 1]

  if (!previousMergedBar) {
    buildState.mergedBars.push(nextMergedBar)
    return null
  }

  if (
    hasInclusion(previousMergedBar, nextMergedBar)
    && canMergeWithinIncludedBarLimit(previousMergedBar, nextMergedBar)
  ) {
    buildState.mergedBars[buildState.mergedBars.length - 1] = mergeIncludedBars(previousMergedBar, nextMergedBar)
    return null
  }

  buildState.mergedBars.push({
    ...nextMergedBar,
    index: buildState.mergedBars.length,
  })
  return appendConfirmedSignal(buildState)
}

export const truncateFenxingBuildState = (buildState: FenxingBuildState, rawBarIndex: number) => {
  const keepMergedBars = buildState.mergedBars.filter((bar) => bar.sourceEndIndex < rawBarIndex)
  normalizeMergedBarIndexes(keepMergedBars)
  buildState.mergedBars = keepMergedBars
  buildState.processedBarCount = rawBarIndex

  const earliestAffectedSignalIndex = Math.max(1, keepMergedBars.length - 2)
  buildState.confirmedFenxingSignals = buildState.confirmedFenxingSignals.filter(
    (signal) => signal.mergedBarIndex < earliestAffectedSignalIndex,
  )
  buildState.confirmedFenxingSignals.forEach((signal, index) => {
    signal.index = index
  })

  return buildState.confirmedFenxingSignals.length
}

export const advanceFenxingStateByIndex = (
  buildState: FenxingBuildState,
  bars: FenxingBar[],
  barIndex: number,
) => {
  const bar = bars[barIndex]
  if (!bar) {
    return null
  }

  const signal = processFenxingBar(buildState, bar)
  buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
  return signal
}

export const advanceFenxingState = (buildState: FenxingBuildState, bars: FenxingBar[]) => {
  let latestSignal: FenxingSignal | null = null

  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    latestSignal = advanceFenxingStateByIndex(buildState, bars, index) ?? latestSignal
  }

  buildState.processedBarCount = bars.length
  return latestSignal
}

export const rebuildFenxingState = (bars: FenxingBar[]) => {
  const buildState = createEmptyFenxingBuildState()
  advanceFenxingState(buildState, bars)
  return buildState
}

export const getAllMergedFenxingBars = (buildState: FenxingBuildState) => {
  return buildState.mergedBars.map((bar) => ({ ...bar }))
}

export const getAllFenxingSignals = (buildState: FenxingBuildState) => {
  return buildState.confirmedFenxingSignals.map((signal) => ({
    ...signal,
    point: { ...signal.point },
  }))
}

export const getOffsetFromCurrentBar = (bars: FenxingBar[], point: { index: number }) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}
