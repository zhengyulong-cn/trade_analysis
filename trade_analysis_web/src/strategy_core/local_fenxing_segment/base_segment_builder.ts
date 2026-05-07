import { isFiniteNumber } from './base_fenxing_builder'
import type {
  BaseSegment,
  BaseSegmentBuildState,
  FenxingBar,
  FenxingPoint,
  FenxingSignal,
  SegmentDirection,
} from './types'

export const createEmptyBaseSegmentBuildState = (): BaseSegmentBuildState => ({
  activeBaseSegment: null,
  historicalBaseSegments: [],
  processedFenxingSignalCount: 0,
  seedBottomFenxingSignal: null,
  seedTopFenxingSignal: null,
})

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

const hasEnoughExtremeBarDistance = (
  startSignal: FenxingSignal,
  endSignal: FenxingSignal,
  minExtremeBarDistance: number,
) => {
  return Math.abs(endSignal.point.index - startSignal.point.index) > minExtremeBarDistance
}

const canBypassExtremeBarDistanceForDownReversal = (activeSegment: BaseSegment, endSignal: FenxingSignal) => {
  return activeSegment.direction === 'up' && endSignal.point.price < activeSegment.start.price
}

const canBypassExtremeBarDistanceForUpReversal = (activeSegment: BaseSegment, endSignal: FenxingSignal) => {
  return activeSegment.direction === 'down' && endSignal.point.price > activeSegment.start.price
}

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

const updateActiveBaseSegmentEnd = (segment: BaseSegment, signal: FenxingSignal) => {
  segment.end = clonePoint(signal.point)
  segment.endFenxingSignalIndex = signal.index
}

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

export const rebuildBaseSegmentState = (
  bars: FenxingBar[],
  signals: FenxingSignal[],
  minExtremeBarDistance: number,
) => {
  const buildState = createEmptyBaseSegmentBuildState()
  advanceBaseSegmentState(buildState, bars, signals, minExtremeBarDistance)
  return buildState
}

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

export const getAllBaseSegments = (buildState: BaseSegmentBuildState) => {
  if (!buildState.activeBaseSegment) {
    return buildState.historicalBaseSegments.map(cloneBaseSegment)
  }

  return [
    ...buildState.historicalBaseSegments.map(cloneBaseSegment),
    cloneBaseSegment(buildState.activeBaseSegment),
  ]
}

export const getLatestDrawableBaseSegment = (buildState: BaseSegmentBuildState) => {
  if (buildState.activeBaseSegment) {
    return buildState.activeBaseSegment
  }

  return buildState.historicalBaseSegments[buildState.historicalBaseSegments.length - 1] ?? null
}

export const getBaseSegmentHighPoint = (segment: BaseSegment): FenxingPoint => (
  segment.direction === 'up' ? clonePoint(segment.end) : clonePoint(segment.start)
)

export const getBaseSegmentLowPoint = (segment: BaseSegment): FenxingPoint => (
  segment.direction === 'up' ? clonePoint(segment.start) : clonePoint(segment.end)
)

export const getBaseSegmentKey = (segment: BaseSegment) => {
  return `${segment.start.time}-${segment.direction}`
}
