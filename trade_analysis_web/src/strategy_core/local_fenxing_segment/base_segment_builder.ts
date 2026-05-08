import { isFiniteNumber } from './base_fenxing_builder'
import type {
  BaseSegment,
  BaseSegmentBuildState,
  FenxingBar,
  FenxingPoint,
  FenxingSignal,
  SegmentDirection,
} from './types'

/** 本级别线段状态机入口。 */
export const createEmptyBaseSegmentBuildState = (): BaseSegmentBuildState => ({
  activeBaseSegment: null,
  historicalBaseSegments: [],
  processedFenxingSignalCount: 0,
  seedBottomFenxingSignal: null,
  seedTopFenxingSignal: null,
})

/** 线段绘制和对外读取都使用拷贝，避免直接篡改活动状态。 */
const clonePoint = (point: FenxingPoint): FenxingPoint => ({ ...point })

const cloneBaseSegment = (segment: BaseSegment): BaseSegment => ({
  direction: segment.direction,
  end: clonePoint(segment.end),
  endFenxingSignalIndex: segment.endFenxingSignalIndex,
  start: clonePoint(segment.start),
  startFenxingSignalIndex: segment.startFenxingSignalIndex,
})

const createBaseSegment = (
  direction: SegmentDirection,
  startSignal: FenxingSignal,
  endSignal: FenxingSignal,
): BaseSegment => ({
  direction,
  end: clonePoint(endSignal.point),
  endFenxingSignalIndex: endSignal.index,
  start: clonePoint(startSignal.point),
  startFenxingSignalIndex: startSignal.index,
})

/** 分型点所在原始 K 线上的 EMA20，用来判断起点/终点是否跨过均线。 */
const getSignalEma20 = (bars: FenxingBar[], signal: FenxingSignal) => {
  return bars[signal.point.index]?.ema20
}

const isTopAboveEma20 = (bars: FenxingBar[], signal: FenxingSignal) => {
  const ema20 = getSignalEma20(bars, signal)
  return signal.type === 'top' && isFiniteNumber(ema20) && signal.point.price > ema20
}

const isBottomBelowEma20 = (bars: FenxingBar[], signal: FenxingSignal) => {
  const ema20 = getSignalEma20(bars, signal)
  return signal.type === 'bottom' && isFiniteNumber(ema20) && signal.point.price < ema20
}

/** 线段最小间距要求看的是顶底极值所在原始 K 线之间的距离。 */
const hasEnoughExtremeBarDistance = (
  startSignal: FenxingSignal,
  endSignal: FenxingSignal,
  minExtremeBarDistance: number,
) => {
  return Math.abs(endSignal.point.index - startSignal.point.index) > minExtremeBarDistance
}

/** 强反转场景下允许跳过最小距离约束。 */
const canBypassExtremeBarDistanceForDownReversal = (activeSegment: BaseSegment, endSignal: FenxingSignal) => {
  return activeSegment.direction === 'up' && endSignal.point.price < activeSegment.start.price
}

const canBypassExtremeBarDistanceForUpReversal = (activeSegment: BaseSegment, endSignal: FenxingSignal) => {
  return activeSegment.direction === 'down' && endSignal.point.price > activeSegment.start.price
}

/** 校验上涨段：底分型在 EMA20 下，顶分型在 EMA20 上，且区间内部没有更坏极值。 */
const isValidUpSegment = (
  bars: FenxingBar[],
  signals: FenxingSignal[],
  startSignal: FenxingSignal,
  endSignal: FenxingSignal,
  minExtremeBarDistance: number,
  allowDistanceBypass = false,
) => {
  if (
    !isBottomBelowEma20(bars, startSignal)
    || !isTopAboveEma20(bars, endSignal)
    || (!allowDistanceBypass && !hasEnoughExtremeBarDistance(startSignal, endSignal, minExtremeBarDistance))
  ) {
    return false
  }

  for (let index = startSignal.index; index <= endSignal.index; index += 1) {
    const signal = signals[index]
    if (!signal) {
      continue
    }

    if (signal.type === 'top' && signal.point.price > endSignal.point.price) {
      return false
    }

    if (signal.type === 'bottom' && signal.point.price < startSignal.point.price) {
      return false
    }
  }

  return true
}

/** 校验下跌段：顶分型在 EMA20 上，底分型在 EMA20 下，且区间内部没有更坏极值。 */
const isValidDownSegment = (
  bars: FenxingBar[],
  signals: FenxingSignal[],
  startSignal: FenxingSignal,
  endSignal: FenxingSignal,
  minExtremeBarDistance: number,
  allowDistanceBypass = false,
) => {
  if (
    !isTopAboveEma20(bars, startSignal)
    || !isBottomBelowEma20(bars, endSignal)
    || (!allowDistanceBypass && !hasEnoughExtremeBarDistance(startSignal, endSignal, minExtremeBarDistance))
  ) {
    return false
  }

  for (let index = startSignal.index; index <= endSignal.index; index += 1) {
    const signal = signals[index]
    if (!signal) {
      continue
    }

    if (signal.type === 'top' && signal.point.price > startSignal.point.price) {
      return false
    }

    if (signal.type === 'bottom' && signal.point.price < endSignal.point.price) {
      return false
    }
  }

  return true
}

/** 活动段延伸时，只更新终点极值。 */
const updateActiveBaseSegmentEnd = (segment: BaseSegment, signal: FenxingSignal) => {
  segment.end = clonePoint(signal.point)
  segment.endFenxingSignalIndex = signal.index
}

/** 还未成段时，先积累种子顶/底分型，直到能构成第一条活动段。 */
const processSeedState = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  signal: FenxingSignal,
  minExtremeBarDistance: number,
) => {
  if (isBottomBelowEma20(bars, signal)) {
    const seedTop = buildState.seedTopFenxingSignal
    if (seedTop && isValidDownSegment(bars, signals, seedTop, signal, minExtremeBarDistance)) {
      buildState.activeBaseSegment = createBaseSegment('down', seedTop, signal)
      buildState.seedBottomFenxingSignal = null
      buildState.seedTopFenxingSignal = null
      return
    }

    if (!buildState.seedBottomFenxingSignal || signal.point.price < buildState.seedBottomFenxingSignal.point.price) {
      buildState.seedBottomFenxingSignal = signal
    }
    return
  }

  if (!isTopAboveEma20(bars, signal)) {
    return
  }

  const seedBottom = buildState.seedBottomFenxingSignal
  if (seedBottom && isValidUpSegment(bars, signals, seedBottom, signal, minExtremeBarDistance)) {
    buildState.activeBaseSegment = createBaseSegment('up', seedBottom, signal)
    buildState.seedBottomFenxingSignal = null
    buildState.seedTopFenxingSignal = null
    return
  }

  if (!buildState.seedTopFenxingSignal || signal.point.price > buildState.seedTopFenxingSignal.point.price) {
    buildState.seedTopFenxingSignal = signal
  }
}

/**
 * 已有活动段后的推进规则：
 * 同向更优极值先延伸；
 * 反向分型只有满足成段条件时才会切换新段。
 */
const processActiveBaseSegment = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  signal: FenxingSignal,
  minExtremeBarDistance: number,
) => {
  const activeSegment = buildState.activeBaseSegment
  if (!activeSegment) {
    return
  }

  if (activeSegment.direction === 'up') {
    if (isTopAboveEma20(bars, signal) && signal.point.price > activeSegment.end.price) {
      updateActiveBaseSegmentEnd(activeSegment, signal)
      return
    }

    const startSignal = signals[activeSegment.endFenxingSignalIndex]
    if (
      startSignal
      && isBottomBelowEma20(bars, signal)
      && isValidDownSegment(
        bars,
        signals,
        startSignal,
        signal,
        minExtremeBarDistance,
        canBypassExtremeBarDistanceForDownReversal(activeSegment, signal),
      )
    ) {
      buildState.historicalBaseSegments.push(cloneBaseSegment(activeSegment))
      buildState.activeBaseSegment = createBaseSegment('down', startSignal, signal)
    }
    return
  } else if (activeSegment.direction === 'down') {
    if (isBottomBelowEma20(bars, signal) && signal.point.price < activeSegment.end.price) {
      updateActiveBaseSegmentEnd(activeSegment, signal)
      return
    }

  const startSignal = signals[activeSegment.endFenxingSignalIndex]
  if (
    startSignal
    && isTopAboveEma20(bars, signal)
    && isValidUpSegment(
      bars,
      signals,
      startSignal,
      signal,
      minExtremeBarDistance,
      canBypassExtremeBarDistanceForUpReversal(activeSegment, signal),
    )
  ) {
    buildState.historicalBaseSegments.push(cloneBaseSegment(activeSegment))
    buildState.activeBaseSegment = createBaseSegment('up', startSignal, signal)
    }
  }
}

/** 统一入口：当前可能处于种子阶段，也可能已经进入活动段阶段。 */
const processBaseSegmentFenxingSignal = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  signal: FenxingSignal,
  minExtremeBarDistance: number,
) => {
  if (buildState.activeBaseSegment) {
    processActiveBaseSegment(buildState, bars, signals, signal, minExtremeBarDistance)
    return
  }

  processSeedState(buildState, bars, signals, signal, minExtremeBarDistance)
}

/** 按分型信号索引推进一次线段状态。 */
export const advanceBaseSegmentStateByIndex = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  signalIndex: number,
  minExtremeBarDistance: number,
) => {
  const signal = signals[signalIndex]
  if (!signal) {
    return getAllBaseSegments(buildState)
  }

  processBaseSegmentFenxingSignal(buildState, bars, signals, signal, minExtremeBarDistance)
  buildState.processedFenxingSignalCount = Math.max(buildState.processedFenxingSignalCount, signalIndex + 1)
  return getAllBaseSegments(buildState)
}

/** 从 processedFenxingSignalCount 继续增量构建线段。 */
export const advanceBaseSegmentState = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  minExtremeBarDistance: number,
) => {
  for (let index = buildState.processedFenxingSignalCount; index < signals.length; index += 1) {
    advanceBaseSegmentStateByIndex(buildState, bars, signals, index, minExtremeBarDistance)
  }

  buildState.processedFenxingSignalCount = signals.length
  return getAllBaseSegments(buildState)
}

/** 完整回放全部分型信号，重建本级别线段状态。 */
export const rebuildBaseSegmentState = (
  bars: FenxingBar[],
  signals: FenxingSignal[],
  minExtremeBarDistance: number,
) => {
  const buildState = createEmptyBaseSegmentBuildState()
  advanceBaseSegmentState(buildState, bars, signals, minExtremeBarDistance)
  return buildState
}

/** 历史分型有变动时，线段状态直接按保留分型数量整体重建。 */
export const truncateBaseSegmentBuildState = (
  buildState: BaseSegmentBuildState,
  bars: FenxingBar[],
  signals: FenxingSignal[],
  signalIndex: number,
  minExtremeBarDistance: number,
) => {
  const preservedSignals = signals.slice(0, signalIndex)
  const rebuiltState = rebuildBaseSegmentState(bars, preservedSignals, minExtremeBarDistance)
  buildState.activeBaseSegment = rebuiltState.activeBaseSegment
  buildState.historicalBaseSegments = rebuiltState.historicalBaseSegments
  buildState.processedFenxingSignalCount = rebuiltState.processedFenxingSignalCount
  buildState.seedBottomFenxingSignal = rebuiltState.seedBottomFenxingSignal
  buildState.seedTopFenxingSignal = rebuiltState.seedTopFenxingSignal
}

/** 对外读取时返回“历史段 + 当前有效活动段”。 */
export const getAllBaseSegments = (buildState: BaseSegmentBuildState) => {
  if (!buildState.activeBaseSegment) {
    return buildState.historicalBaseSegments.map(cloneBaseSegment)
  }

  return [
    ...buildState.historicalBaseSegments.map(cloneBaseSegment),
    cloneBaseSegment(buildState.activeBaseSegment),
  ]
}

/** 图上优先显示活动段，没有活动段时才显示最后一条历史段。 */
export const getLatestDrawableBaseSegment = (buildState: BaseSegmentBuildState) => {
  if (buildState.activeBaseSegment) {
    return buildState.activeBaseSegment
  }

  return buildState.historicalBaseSegments[buildState.historicalBaseSegments.length - 1] ?? null
}

/** 线段高点/低点统一从方向语义推导，供大级别线段和交易区间复用。 */
export const getBaseSegmentHighPoint = (segment: BaseSegment): FenxingPoint => (
  segment.direction === 'up' ? clonePoint(segment.end) : clonePoint(segment.start)
)

export const getBaseSegmentLowPoint = (segment: BaseSegment): FenxingPoint => (
  segment.direction === 'up' ? clonePoint(segment.start) : clonePoint(segment.end)
)

export const getBaseSegmentKey = (segment: BaseSegment) => {
  return `${segment.start.time}-${segment.direction}`
}
