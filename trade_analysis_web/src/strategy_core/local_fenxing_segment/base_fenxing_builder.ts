import type {
  FenxingBar,
  FenxingBuildState,
  FenxingSignal,
  MergedFenxingBar,
  UpsertFenxingBarResult,
} from './types'

/** 基础数值守卫，主入口会用它过滤 TradingView 计算早期的 NaN。 */
export const isFiniteNumber = (value: unknown): value is number => {
  return typeof value === 'number' && Number.isFinite(value)
}

/** 创建空的分型构建状态。 */
export const createEmptyFenxingBuildState = (): FenxingBuildState => ({
  confirmedFenxingSignals: [],
  mergedBars: [],
  processedBarCount: 0,
})

/**
 * 增量写入原始 K 线。
 * 支持追加、替换最后一根、替换历史同时间 K 线，以及插入历史 K 线。
 */
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

/** 原始 K 线先转换成“可参与包含处理”的初始合成 K 线。 */
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

/** 相邻两根处理后 K 线是否存在包含关系。 */
const hasInclusion = (first: MergedFenxingBar, second: MergedFenxingBar) => {
  return (
    (first.high >= second.high && first.low <= second.low)
    || (first.high <= second.high && first.low >= second.low)
  )
}

/** 递归包含最多只允许覆盖限定数量的原始 K 线。 */
const canMergeWithinIncludedBarLimit = (
  first: MergedFenxingBar,
  second: MergedFenxingBar,
  maxIncludedRawBarCount: number,
) => {
  return second.sourceEndIndex - first.sourceStartIndex + 1 <= maxIncludedRawBarCount
}

/**
 * 包含合成规则：
 * 方向由参与合成序列第一根原始 K 线是否在 EMA20 下方决定，
 * 之后整段递归合成都沿用这套 high/low 规则。
 */
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

/** 截断历史后，需要重排处理后 K 线索引，保证三根结构判断仍连续。 */
const normalizeMergedBarIndexes = (bars: MergedFenxingBar[]) => {
  bars.forEach((bar, index) => {
    bar.index = index
  })
}

/** 在三根处理后 K 线上判断中间一根是否构成顶/底分型。 */
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

/** 每新增一根独立处理后 K 线，只需要检查倒数第二根是否成为新的分型中心。 */
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

/** 推进单根原始 K 线：先做包含处理，再在必要时确认新分型。 */
const processFenxingBar = (
  buildState: FenxingBuildState,
  bar: FenxingBar,
  maxIncludedRawBarCount: number,
) => {
  const nextMergedBar = createMergedBar(bar)
  const previousMergedBar = buildState.mergedBars[buildState.mergedBars.length - 1]

  if (!previousMergedBar) {
    buildState.mergedBars.push(nextMergedBar)
    return null
  }

  if (
    hasInclusion(previousMergedBar, nextMergedBar)
    && canMergeWithinIncludedBarLimit(previousMergedBar, nextMergedBar, maxIncludedRawBarCount)
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

/**
 * 当历史 K 线被替换/插入时，从受影响原始 K 线开始截断分型状态。
 * 返回值是后续线段重建时需要保留到的分型信号数量。
 */
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

/** 按原始 K 线索引推进一次分型状态。 */
export const advanceFenxingStateByIndex = (
  buildState: FenxingBuildState,
  bars: FenxingBar[],
  barIndex: number,
  maxIncludedRawBarCount: number,
) => {
  const bar = bars[barIndex]
  if (!bar) {
    return null
  }

  const signal = processFenxingBar(buildState, bar, maxIncludedRawBarCount)
  buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
  return signal
}

/** 从 processedBarCount 继续向后做增量分型构建。 */
export const advanceFenxingState = (
  buildState: FenxingBuildState,
  bars: FenxingBar[],
  maxIncludedRawBarCount: number,
) => {
  let latestSignal: FenxingSignal | null = null

  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    latestSignal = advanceFenxingStateByIndex(buildState, bars, index, maxIncludedRawBarCount) ?? latestSignal
  }

  buildState.processedBarCount = bars.length
  return latestSignal
}

/** 完整重建分型状态，主要用于历史数据变动后的回放。 */
export const rebuildFenxingState = (bars: FenxingBar[], maxIncludedRawBarCount: number) => {
  const buildState = createEmptyFenxingBuildState()
  advanceFenxingState(buildState, bars, maxIncludedRawBarCount)
  return buildState
}

/** 对外暴露拷贝，避免外部误改内部状态对象。 */
export const getAllMergedFenxingBars = (buildState: FenxingBuildState) => {
  return buildState.mergedBars.map((bar) => ({ ...bar }))
}

/** 对外暴露已确认分型信号拷贝。 */
export const getAllFenxingSignals = (buildState: FenxingBuildState) => {
  return buildState.confirmedFenxingSignals.map((signal) => ({
    ...signal,
    point: { ...signal.point },
  }))
}

/** TradingView dataoffset 需要的是“相对当前最后一根 K 线的偏移”。 */
export const getOffsetFromCurrentBar = (bars: FenxingBar[], point: { index: number }) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}
