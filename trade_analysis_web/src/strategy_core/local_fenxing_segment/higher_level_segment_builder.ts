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

/** EMA20 相对 EMA120 的位置关系，用来判断当前大级别周期方向。 */
type CrossRelation = 'above' | 'below'

/** 大级别方向直接由均线关系翻译而来。 */
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

/** 大级别段的最小 K 线跨度限制。 */
const getMinBarDistance = (minBarDistance: number) => {
  return minBarDistance * 5
}

/** 已生成的大级别段是否达到最小跨度要求。 */
const isValidHigherLevelSegment = (
  segment: HigherLevelSegment,
  minBarDistance: number,
) => {
  return Math.abs(segment.end.index - segment.start.index) + 1 >= getMinBarDistance(minBarDistance)
}

/** 潜在反向段是否已经长到足以真正翻段。 */
const isValidHigherLevelSegmentRange = (
  start: FenxingPoint,
  end: FenxingPoint,
  minBarDistance: number,
) => {
  return Math.abs(end.index - start.index) + 1 >= getMinBarDistance(minBarDistance)
}

/** EMA20/EMA120 的相对位置，决定当前处于上涨周期还是下跌周期。 */
const getCrossRelation = (bar: FenxingBar): CrossRelation | null => {
  if (!isFiniteNumber(bar.ema20) || !isFiniteNumber(bar.ema120)) {
    return null
  }

  return bar.ema20 >= bar.ema120 ? 'above' : 'below'
}

/** 本级别线段不足时，大级别线段无法起段。 */
const getFirstAvailableBaseSegmentIndex = (baseSegments: BaseSegment[]) => {
  const firstBaseSegment = baseSegments[0]
  if (!firstBaseSegment) {
    return null
  }

  return Math.min(firstBaseSegment.start.index, firstBaseSegment.end.index)
}

/** 历史大级别段终点会作为下一段搜索区间的左边界之一。 */
const getLastHistoricalEndIndex = (buildState: HigherLevelSegmentBuildState) => {
  return buildState.historicalHigherLevelSegments[buildState.historicalHigherLevelSegments.length - 1]?.end.index ?? null
}

/** 在指定原始 K 线区间内，从本级别线段极值点中选出最高/最低候选点。 */
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

/** 下一轮大级别周期的搜索左边界：取最近历史段终点和最近交叉边界中的较右者。 */
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

/** 金叉后启动潜在上涨大级别段：先找最低点，再向右找最高点。 */
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

/** 死叉后启动潜在下跌大级别段：先找最高点，再向右找最低点。 */
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

/** 根据当前均线关系，决定潜在新段从上涨起还是从下跌起。 */
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

/** 同方向周期内，只更新当前大级别活动段的终点极值。 */
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

/**
 * 反向均线周期出现时，不会立刻翻段。
 * 只有潜在反向段从“当前活动段终点”开始长够最小跨度，才真正切到新段。
 */
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

/** 创建空的大级别线段状态。 */
export const createEmptyHigherLevelSegmentBuildState = (): HigherLevelSegmentBuildState => ({
  activeHigherLevelSegment: null,
  historicalHigherLevelSegments: [],
  lastCrossBarIndex: null,
  lastCrossRelation: null,
  processedBarCount: 0,
})

/** 按原始 K 线索引推进一次大级别状态。 */
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

/** 从 processedBarCount 继续增量构建大级别线段。 */
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

/** 整体重建大级别线段状态。 */
export const rebuildHigherLevelSegmentState = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  minBarDistance: number,
) => {
  const buildState = createEmptyHigherLevelSegmentBuildState()
  advanceHigherLevelSegmentState(buildState, bars, baseSegments, minBarDistance)
  return buildState
}

/** 原始 K 线或本级别线段发生历史改动时，大级别状态按保留范围重建。 */
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

/** 对外读取时，只有满足最小跨度的大级别活动段才会被暴露。 */
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

/** 图上只显示可绘制的大级别活动段或最后一条历史段。 */
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

/** 给图形绘制做稳定 key。 */
export const getHigherLevelSegmentKey = (segment: HigherLevelSegment) => {
  return `${segment.start.time}-${segment.direction}`
}

/** 把外部状态对象重建填充到当前 buildState，供主入口在截断后复用。 */
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
