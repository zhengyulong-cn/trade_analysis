import {
  advanceBaseSegmentStateByIndex,
  createEmptyBaseSegmentBuildState,
  getAllBaseSegments,
  getBaseSegmentHighPoint,
  getBaseSegmentLowPoint,
  isFiniteNumber,
} from './base_segment_builder'
import type {
  BaseSegment,
  EmaSegmentBar,
  HigherLevelSegment,
  HigherLevelSegmentBuildState,
  SegmentDirection,
  SegmentPoint,
} from './types'

type CrossRelation = 'above' | 'below'

const clonePoint = (point: SegmentPoint): SegmentPoint => ({
  index: point.index,
  price: point.price,
  time: point.time,
})

const cloneHigherLevelSegment = (segment: HigherLevelSegment): HigherLevelSegment => ({
  direction: segment.direction,
  end: clonePoint(segment.end),
  start: clonePoint(segment.start),
})

const createHigherLevelSegment = (
  direction: SegmentDirection,
  start: SegmentPoint,
  end: SegmentPoint,
): HigherLevelSegment => ({
  direction,
  start: clonePoint(start),
  end: clonePoint(end),
})

const getCrossRelation = (bar: EmaSegmentBar): CrossRelation | null => {
  if (!isFiniteNumber(bar.ema20) || !isFiniteNumber(bar.ema120)) {
    return null
  }

  return bar.ema20 >= bar.ema120 ? 'above' : 'below'
}

const getFirstAvailableBaseSegmentIndex = (baseSegments: BaseSegment[]) => {
  const firstBaseSegment = baseSegments[0]
  if (!firstBaseSegment) {
    return null
  }

  return Math.min(firstBaseSegment.start.index, firstBaseSegment.end.index)
}

const getRangeExtremePoint = (
  baseSegments: BaseSegment[],
  fromIndex: number,
  toIndex: number,
  selector: (baseSegment: BaseSegment) => SegmentPoint,
  comparator: (nextPrice: number, currentPrice: number) => boolean,
) => {
  let selectedPoint: SegmentPoint | null = null

  baseSegments.forEach((baseSegment) => {
    const candidatePoint = selector(baseSegment)
    if (candidatePoint.index < fromIndex || candidatePoint.index > toIndex) {
      return
    }

    if (!selectedPoint || comparator(candidatePoint.price, selectedPoint.price)) {
      selectedPoint = candidatePoint
    }
  })

  return selectedPoint ? clonePoint(selectedPoint) : null
}

const getRangeHighPoint = (baseSegments: BaseSegment[], fromIndex: number, toIndex: number) => (
  getRangeExtremePoint(
    baseSegments,
    fromIndex,
    toIndex,
    getBaseSegmentHighPoint,
    (nextPrice, currentPrice) => nextPrice > currentPrice,
  )
)

const getRangeLowPoint = (baseSegments: BaseSegment[], fromIndex: number, toIndex: number) => (
  getRangeExtremePoint(
    baseSegments,
    fromIndex,
    toIndex,
    getBaseSegmentLowPoint,
    (nextPrice, currentPrice) => nextPrice < currentPrice,
  )
)

const getHigherLevelSegmentEndPoint = (
  direction: SegmentDirection,
  baseSegments: BaseSegment[],
  startIndex: number,
  toIndex: number,
) => {
  if (direction === 'down') {
    return getRangeLowPoint(baseSegments, startIndex, toIndex)
  }

  // Inference: an up higher-level segment should extend to the range high.
  return getRangeHighPoint(baseSegments, startIndex, toIndex)
}

const syncDerivedState = (
  buildState: HigherLevelSegmentBuildState,
  activeHigherLevelSegment: HigherLevelSegment | null,
) => {
  buildState.activeHigherLevelSegment = activeHigherLevelSegment
  buildState.currentCycleDirection = activeHigherLevelSegment?.direction ?? null
  buildState.currentCycleExtremePoint = activeHigherLevelSegment ? clonePoint(activeHigherLevelSegment.end) : null
  buildState.currentCycleStartIndex = activeHigherLevelSegment?.start.index ?? null
}

const updateActiveHigherLevelSegmentEnd = (
  buildState: HigherLevelSegmentBuildState,
  baseSegments: BaseSegment[],
  toIndex: number,
) => {
  const activeHigherLevelSegment = buildState.activeHigherLevelSegment
  if (!activeHigherLevelSegment) {
    return
  }

  const nextEnd = getHigherLevelSegmentEndPoint(
    activeHigherLevelSegment.direction,
    baseSegments,
    activeHigherLevelSegment.start.index,
    toIndex,
  )

  if (!nextEnd) {
    return
  }

  activeHigherLevelSegment.end = nextEnd
  syncDerivedState(buildState, activeHigherLevelSegment)
}

const finalizeActiveHigherLevelSegment = (
  buildState: HigherLevelSegmentBuildState,
  baseSegments: BaseSegment[],
  toIndex: number,
) => {
  const activeHigherLevelSegment = buildState.activeHigherLevelSegment
  if (!activeHigherLevelSegment) {
    return
  }

  updateActiveHigherLevelSegmentEnd(buildState, baseSegments, toIndex)
  if (!buildState.activeHigherLevelSegment) {
    return
  }

  buildState.historicalHigherLevelSegments.push(cloneHigherLevelSegment(buildState.activeHigherLevelSegment))
}

const startHigherLevelSegmentFromCross = (
  buildState: HigherLevelSegmentBuildState,
  nextDirection: SegmentDirection,
  baseSegments: BaseSegment[],
  crossBarIndex: number,
) => {
  const previousHigherLevelSegment = buildState.historicalHigherLevelSegments[buildState.historicalHigherLevelSegments.length - 1] ?? null
  const defaultRangeStartIndex = getFirstAvailableBaseSegmentIndex(baseSegments)
  const rangeStartIndex = previousHigherLevelSegment?.end.index ?? defaultRangeStartIndex

  if (rangeStartIndex === null) {
    syncDerivedState(buildState, null)
    return
  }

  const startPoint = nextDirection === 'down'
    ? getRangeHighPoint(baseSegments, rangeStartIndex, crossBarIndex)
    : getRangeLowPoint(baseSegments, rangeStartIndex, crossBarIndex)

  if (!startPoint) {
    syncDerivedState(buildState, null)
    return
  }

  const endPoint = getHigherLevelSegmentEndPoint(nextDirection, baseSegments, startPoint.index, crossBarIndex) ?? startPoint
  syncDerivedState(buildState, createHigherLevelSegment(nextDirection, startPoint, endPoint))
}

const handleCrossTransition = (
  buildState: HigherLevelSegmentBuildState,
  currentRelation: CrossRelation,
  baseSegments: BaseSegment[],
  crossBarIndex: number,
) => {
  finalizeActiveHigherLevelSegment(buildState, baseSegments, crossBarIndex)

  if (currentRelation === 'above') {
    startHigherLevelSegmentFromCross(buildState, 'up', baseSegments, crossBarIndex)
    return
  }

  startHigherLevelSegmentFromCross(buildState, 'down', baseSegments, crossBarIndex)
}

export const createEmptyHigherLevelSegmentBuildState = (): HigherLevelSegmentBuildState => ({
  activeHigherLevelSegment: null,
  currentCycleDirection: null,
  currentCycleExtremePoint: null,
  currentCycleStartIndex: null,
  historicalHigherLevelSegments: [],
  lastCrossRelation: null,
  processedBarCount: 0,
})

export const advanceHigherLevelSegmentStateByIndex = (
  buildState: HigherLevelSegmentBuildState,
  bars: EmaSegmentBar[],
  barIndex: number,
  baseSegments: BaseSegment[],
) => {
  const bar = bars[barIndex]
  if (!bar) {
    return getAllHigherLevelSegments(buildState)
  }

  const currentRelation = getCrossRelation(bar)
  if (!currentRelation) {
    buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
    return getAllHigherLevelSegments(buildState)
  }

  if (buildState.lastCrossRelation !== null && buildState.lastCrossRelation !== currentRelation) {
    handleCrossTransition(buildState, currentRelation, baseSegments, bar.index)
  } else {
    updateActiveHigherLevelSegmentEnd(buildState, baseSegments, bar.index)
  }

  buildState.lastCrossRelation = currentRelation
  buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
  return getAllHigherLevelSegments(buildState)
}

export const rebuildHigherLevelSegmentState = (
  bars: EmaSegmentBar[],
  baseSegmentEmaLength: number,
  minBaseSegmentBars: number,
) => {
  const baseSegmentBuildState = createEmptyBaseSegmentBuildState()
  const higherLevelSegmentBuildState = createEmptyHigherLevelSegmentBuildState()

  for (let index = 0; index < bars.length; index += 1) {
    advanceBaseSegmentStateByIndex(baseSegmentBuildState, bars, index, baseSegmentEmaLength, minBaseSegmentBars)
    advanceHigherLevelSegmentStateByIndex(
      higherLevelSegmentBuildState,
      bars,
      index,
      getAllBaseSegments(baseSegmentBuildState),
    )
  }

  return higherLevelSegmentBuildState
}

export const getAllHigherLevelSegments = (buildState: HigherLevelSegmentBuildState) => {
  if (!buildState.activeHigherLevelSegment) {
    return [...buildState.historicalHigherLevelSegments]
  }

  return [...buildState.historicalHigherLevelSegments, cloneHigherLevelSegment(buildState.activeHigherLevelSegment)]
}

export const getLatestDrawableHigherLevelSegment = (buildState: HigherLevelSegmentBuildState) => {
  if (buildState.activeHigherLevelSegment) {
    return buildState.activeHigherLevelSegment
  }

  return buildState.historicalHigherLevelSegments[buildState.historicalHigherLevelSegments.length - 1] ?? null
}

export const getHigherLevelSegmentKey = (segment: HigherLevelSegment) => {
  return `${segment.start.time}-${segment.direction}`
}
