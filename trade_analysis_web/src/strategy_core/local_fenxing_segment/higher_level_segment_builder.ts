import { getBaseSegmentHighPoint, getBaseSegmentLowPoint } from './base_segment_builder'
import { isFiniteNumber } from './base_fenxing_builder'
import type {
  BaseSegment,
  FenxingBar,
  FenxingPoint,
  HigherLevelSegment,
  HigherLevelSegmentBuildState,
  SegmentDirection,
} from './types'

type CrossRelation = 'above' | 'below'

const getRelationDirection = (relation: CrossRelation): SegmentDirection => (
  relation === 'above' ? 'up' : 'down'
)

const clonePoint = (point: FenxingPoint): FenxingPoint => ({ ...point })

const cloneHigherLevelSegment = (segment: HigherLevelSegment): HigherLevelSegment => ({
  direction: segment.direction,
  end: clonePoint(segment.end),
  start: clonePoint(segment.start),
})

const createHigherLevelSegment = (
  direction: SegmentDirection,
  start: FenxingPoint,
  end: FenxingPoint,
): HigherLevelSegment => ({
  direction,
  end: clonePoint(end),
  start: clonePoint(start),
})

const isValidHigherLevelSegment = (
  segment: HigherLevelSegment,
  minBarDistance: number,
) => {
  return Math.abs(segment.end.index - segment.start.index) + 1 >= minBarDistance * 6
}

const isValidHigherLevelSegmentRange = (
  start: FenxingPoint,
  end: FenxingPoint,
  minBarDistance: number,
) => {
  return Math.abs(end.index - start.index) + 1 >= minBarDistance * 6
}

const getCrossRelation = (bar: FenxingBar): CrossRelation | null => {
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

const getLastHistoricalEndIndex = (buildState: HigherLevelSegmentBuildState) => {
  return buildState.historicalHigherLevelSegments[buildState.historicalHigherLevelSegments.length - 1]?.end.index ?? null
}

const getRangeExtremePoint = (
  baseSegments: BaseSegment[],
  fromIndex: number,
  toIndex: number,
  selector: (segment: BaseSegment) => FenxingPoint,
  comparator: (nextPrice: number, currentPrice: number) => boolean,
) => {
  let selectedPoint: FenxingPoint | null = null

  for (const baseSegment of baseSegments) {
    const candidatePoint = selector(baseSegment)
    if (candidatePoint.index < fromIndex || candidatePoint.index > toIndex) {
      continue
    }

    if (!selectedPoint || comparator(candidatePoint.price, selectedPoint.price)) {
      selectedPoint = candidatePoint
    }
  }

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

const getRangeStartIndex = (
  buildState: HigherLevelSegmentBuildState,
  baseSegments: BaseSegment[],
) => {
  const lastHistoricalEndIndex = getLastHistoricalEndIndex(buildState)
  const firstAvailableBaseSegmentIndex = getFirstAvailableBaseSegmentIndex(baseSegments)

  if (buildState.lastCrossBarIndex === null) {
    return lastHistoricalEndIndex ?? firstAvailableBaseSegmentIndex
  }

  if (lastHistoricalEndIndex === null) {
    return Math.max(buildState.lastCrossBarIndex, firstAvailableBaseSegmentIndex ?? buildState.lastCrossBarIndex)
  }

  return Math.max(lastHistoricalEndIndex, buildState.lastCrossBarIndex)
}

const startUpHigherLevelSegment = (
  buildState: HigherLevelSegmentBuildState,
  baseSegments: BaseSegment[],
  crossBarIndex: number,
) => {
  const rangeStartIndex = getRangeStartIndex(buildState, baseSegments)
  if (rangeStartIndex === null) {
    return
  }

  const startPoint = getRangeLowPoint(baseSegments, rangeStartIndex, crossBarIndex)
  if (!startPoint) {
    return
  }

  const endPoint = getRangeHighPoint(baseSegments, startPoint.index, crossBarIndex) ?? startPoint
  buildState.activeHigherLevelSegment = createHigherLevelSegment('up', startPoint, endPoint)
}

const startDownHigherLevelSegment = (
  buildState: HigherLevelSegmentBuildState,
  baseSegments: BaseSegment[],
  crossBarIndex: number,
) => {
  const rangeStartIndex = getRangeStartIndex(buildState, baseSegments)
  if (rangeStartIndex === null) {
    return
  }

  const startPoint = getRangeHighPoint(baseSegments, rangeStartIndex, crossBarIndex)
  if (!startPoint) {
    return
  }

  const endPoint = getRangeLowPoint(baseSegments, startPoint.index, crossBarIndex) ?? startPoint
  buildState.activeHigherLevelSegment = createHigherLevelSegment('down', startPoint, endPoint)
}

const startHigherLevelSegmentForRelation = (
  buildState: HigherLevelSegmentBuildState,
  relation: CrossRelation,
  baseSegments: BaseSegment[],
  barIndex: number,
) => {
  if (relation === 'above') {
    startUpHigherLevelSegment(buildState, baseSegments, barIndex)
    return
  }

  startDownHigherLevelSegment(buildState, baseSegments, barIndex)
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

  const nextEnd = activeHigherLevelSegment.direction === 'up'
    ? getRangeHighPoint(baseSegments, activeHigherLevelSegment.start.index, toIndex)
    : getRangeLowPoint(baseSegments, activeHigherLevelSegment.start.index, toIndex)

  if (!nextEnd) {
    return
  }

  activeHigherLevelSegment.end = nextEnd
}

const tryReverseHigherLevelSegment = (
  buildState: HigherLevelSegmentBuildState,
  currentRelation: CrossRelation,
  baseSegments: BaseSegment[],
  barIndex: number,
  minBarDistance: number,
) => {
  const activeHigherLevelSegment = buildState.activeHigherLevelSegment
  if (!activeHigherLevelSegment) {
    return false
  }

  const candidateStart = clonePoint(activeHigherLevelSegment.end)
  const candidateEnd = currentRelation === 'above'
    ? getRangeHighPoint(baseSegments, candidateStart.index, barIndex)
    : getRangeLowPoint(baseSegments, candidateStart.index, barIndex)

  if (!candidateEnd || !isValidHigherLevelSegmentRange(candidateStart, candidateEnd, minBarDistance)) {
    return false
  }

  if (isValidHigherLevelSegment(activeHigherLevelSegment, minBarDistance)) {
    buildState.historicalHigherLevelSegments.push(cloneHigherLevelSegment(activeHigherLevelSegment))
  }

  buildState.activeHigherLevelSegment = createHigherLevelSegment(
    getRelationDirection(currentRelation),
    candidateStart,
    candidateEnd,
  )
  return true
}

export const createEmptyHigherLevelSegmentBuildState = (): HigherLevelSegmentBuildState => ({
  activeHigherLevelSegment: null,
  historicalHigherLevelSegments: [],
  lastCrossBarIndex: null,
  lastCrossRelation: null,
  processedBarCount: 0,
})

export const advanceHigherLevelSegmentStateByIndex = (
  buildState: HigherLevelSegmentBuildState,
  bars: FenxingBar[],
  barIndex: number,
  baseSegments: BaseSegment[],
  minBarDistance: number,
) => {
  const bar = bars[barIndex]
  if (!bar) {
    return getAllHigherLevelSegments(buildState, minBarDistance)
  }

  const currentRelation = getCrossRelation(bar)
  if (!currentRelation) {
    buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
    return getAllHigherLevelSegments(buildState, minBarDistance)
  }

  if (!buildState.activeHigherLevelSegment) {
    if (buildState.lastCrossRelation !== null && buildState.lastCrossRelation !== currentRelation) {
      startHigherLevelSegmentForRelation(buildState, currentRelation, baseSegments, bar.index)
      buildState.lastCrossBarIndex = bar.index
    }
  } else if (buildState.activeHigherLevelSegment.direction === getRelationDirection(currentRelation)) {
    updateActiveHigherLevelSegmentEnd(buildState, baseSegments, bar.index)
  } else {
    const reversed = tryReverseHigherLevelSegment(
      buildState,
      currentRelation,
      baseSegments,
      bar.index,
      minBarDistance,
    )

    if (reversed && buildState.lastCrossRelation !== currentRelation) {
      buildState.lastCrossBarIndex = bar.index
    }
  }

  if (buildState.lastCrossBarIndex === null) {
    buildState.lastCrossBarIndex = bar.index
  }

  buildState.lastCrossRelation = currentRelation
  buildState.processedBarCount = Math.max(buildState.processedBarCount, barIndex + 1)
  return getAllHigherLevelSegments(buildState, minBarDistance)
}

export const advanceHigherLevelSegmentState = (
  buildState: HigherLevelSegmentBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  minBarDistance: number,
) => {
  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    advanceHigherLevelSegmentStateByIndex(buildState, bars, index, baseSegments, minBarDistance)
  }

  buildState.processedBarCount = bars.length
  return getAllHigherLevelSegments(buildState, minBarDistance)
}

export const rebuildHigherLevelSegmentState = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  minBarDistance: number,
) => {
  const buildState = createEmptyHigherLevelSegmentBuildState()
  advanceHigherLevelSegmentState(buildState, bars, baseSegments, minBarDistance)
  return buildState
}

export const truncateHigherLevelSegmentBuildState = (
  buildState: HigherLevelSegmentBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  rawBarIndex: number,
  minBarDistance: number,
) => {
  const preservedBars = bars.slice(0, rawBarIndex)
  const preservedBaseSegments = baseSegments.filter(
    (segment) => Math.max(segment.start.index, segment.end.index) < rawBarIndex,
  )
  const rebuiltState = rebuildHigherLevelSegmentState(preservedBars, preservedBaseSegments, minBarDistance)
  buildState.activeHigherLevelSegment = rebuiltState.activeHigherLevelSegment
  buildState.historicalHigherLevelSegments = rebuiltState.historicalHigherLevelSegments
  buildState.lastCrossBarIndex = rebuiltState.lastCrossBarIndex
  buildState.lastCrossRelation = rebuiltState.lastCrossRelation
  buildState.processedBarCount = rebuiltState.processedBarCount
}

export const getAllHigherLevelSegments = (
  buildState: HigherLevelSegmentBuildState,
  minBarDistance: number,
) => {
  if (
    !buildState.activeHigherLevelSegment
    || !isValidHigherLevelSegment(buildState.activeHigherLevelSegment, minBarDistance)
  ) {
    return buildState.historicalHigherLevelSegments.map(cloneHigherLevelSegment)
  }

  return [
    ...buildState.historicalHigherLevelSegments.map(cloneHigherLevelSegment),
    cloneHigherLevelSegment(buildState.activeHigherLevelSegment),
  ]
}

export const getLatestDrawableHigherLevelSegment = (
  buildState: HigherLevelSegmentBuildState,
  minBarDistance: number,
) => {
  if (
    buildState.activeHigherLevelSegment
    && isValidHigherLevelSegment(buildState.activeHigherLevelSegment, minBarDistance)
  ) {
    return buildState.activeHigherLevelSegment
  }

  return buildState.historicalHigherLevelSegments[buildState.historicalHigherLevelSegments.length - 1] ?? null
}

export const getHigherLevelSegmentKey = (segment: HigherLevelSegment) => {
  return `${segment.start.time}-${segment.direction}`
}

export const rebuildHigherLevelSegmentStateInto = (
  buildState: HigherLevelSegmentBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  minBarDistance: number,
) => {
  const rebuiltState = rebuildHigherLevelSegmentState(bars, baseSegments, minBarDistance)
  buildState.activeHigherLevelSegment = rebuiltState.activeHigherLevelSegment
  buildState.historicalHigherLevelSegments = rebuiltState.historicalHigherLevelSegments
  buildState.lastCrossBarIndex = rebuiltState.lastCrossBarIndex
  buildState.lastCrossRelation = rebuiltState.lastCrossRelation
  buildState.processedBarCount = rebuiltState.processedBarCount
}
