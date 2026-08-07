import type {
  BaseSegment,
  FenxingBar,
  HigherLevelSegment,
  SegmentDirection,
  TradingRange,
  TradingRangeBuildState,
  TradingRangeFeatureSegment,
} from './types'

/** 初次成区间时，对两段特征序列重叠程度的要求。 */
const INITIAL_OVERLAP_THRESHOLD = 0.4
/** 区间已存在后，新增特征序列继续并入的重叠要求。 */
const EXTENSION_OVERLAP_THRESHOLD = 0.4
/** 单根特征序列太大时，不允许拿它继续扩展交易区间。 */
const EXTENSION_FEATURE_RANGE_LIMIT_MULTIPLIER = 2

const clonePoint = <T extends { index: number; price: number; time: number }>(point: T): T => ({
  ...point,
})

const cloneBaseSegment = (segment: BaseSegment): BaseSegment => ({
  direction: segment.direction,
  end: clonePoint(segment.end),
  endFenxingSignalIndex: segment.endFenxingSignalIndex,
  start: clonePoint(segment.start),
  startFenxingSignalIndex: segment.startFenxingSignalIndex,
})

const cloneFeatureSegment = (feature: TradingRangeFeatureSegment): TradingRangeFeatureSegment => ({
  baseSegmentIndex: feature.baseSegmentIndex,
  higherDirection: feature.higherDirection,
  segment: cloneBaseSegment(feature.segment),
})

const cloneTradingRange = (range: TradingRange): TradingRange => ({
  bottom: range.bottom,
  features: range.features.map(cloneFeatureSegment),
  left: clonePoint(range.left),
  right: clonePoint(range.right),
  top: range.top,
})

/** 交易区间状态机构造函数。 */
export const createEmptyTradingRangeBuildState = (): TradingRangeBuildState => ({
  activeTradingRange: null,
  historicalTradingRanges: [],
  lastFeatureSegment: null,
  pendingGraphicsRefresh: false,
  processedBaseSegmentCount: 0,
})

/** 交易区间只关心与大级别方向相反的本级别线段。 */
const getOppositeDirection = (direction: SegmentDirection): SegmentDirection => (
  direction === 'up' ? 'down' : 'up'
)

const getSegmentHigh = (segment: { start: { price: number }; end: { price: number } }) => (
  Math.max(segment.start.price, segment.end.price)
)

const getSegmentLow = (segment: { start: { price: number }; end: { price: number } }) => (
  Math.min(segment.start.price, segment.end.price)
)

const getSegmentRange = (segment: BaseSegment) => getSegmentHigh(segment) - getSegmentLow(segment)

const getOverlapRange = (
  firstLow: number,
  firstHigh: number,
  secondLow: number,
  secondHigh: number,
) => Math.max(0, Math.min(firstHigh, secondHigh) - Math.max(firstLow, secondLow))

/** 交易区间上下边界取特征序列高低值的“次高 / 次低”，避免被单一极值拉坏。 */
const getSecondValue = (values: number[], direction: 'asc' | 'desc') => {
  const sortedValues = [...values].sort((first, second) => (
    direction === 'asc' ? first - second : second - first
  ))

  return sortedValues[Math.min(1, sortedValues.length - 1)]
}

/**
 * 由特征序列反推出矩形区间。
 * 首次成区间时，左边界还会按原始 K 线向左回溯扩展，
 * 直到左侧 K 线不再与区间价格带发生交集。
 */
export const calculateTradingRangeFromFeatures = (
  features: TradingRangeFeatureSegment[],
  bars?: FenxingBar[],
): TradingRange | null => {
  if (features.length === 0) {
    return null
  }

  const highs = features.map((feature) => getSegmentHigh(feature.segment))
  const lows = features.map((feature) => getSegmentLow(feature.segment))
  const top = getSecondValue(highs, 'desc')
  const bottom = getSecondValue(lows, 'asc')
  const firstFeature = features[0]
  const lastFeature = features[features.length - 1]

  if (!firstFeature || !lastFeature || top === undefined || bottom === undefined || top <= bottom) {
    return null
  }

  const leftPoint = (() => {
    if (!bars) {
      return clonePoint(firstFeature.segment.start)
    }

    let leftBar = bars[firstFeature.segment.start.index]
    if (!leftBar) {
      return clonePoint(firstFeature.segment.start)
    }

    for (let index = firstFeature.segment.start.index - 1; index >= 0; index -= 1) {
      const bar = bars[index]
      if (!bar) {
        break
      }

      const isInsideTradingRange = bar.high >= bottom && bar.low <= top
      if (!isInsideTradingRange) {
        break
      }

      leftBar = bar
    }

    return {
      index: leftBar.index,
      price: firstFeature.segment.start.price,
      time: leftBar.time,
    }
  })()

  return {
    bottom,
    features: features.map(cloneFeatureSegment),
    left: leftPoint,
    right: clonePoint(lastFeature.segment.end),
    top,
  }
}

/** 给本级别线段匹配一个所属的大级别方向。 */
const findHigherDirectionForBaseSegment = (
  baseSegment: BaseSegment,
  higherSegments: HigherLevelSegment[],
): SegmentDirection | null => {
  const baseStartIndex = Math.min(baseSegment.start.index, baseSegment.end.index)
  const baseEndIndex = Math.max(baseSegment.start.index, baseSegment.end.index)

  const containingHigherSegment = [...higherSegments].reverse().find((higherSegment) => {
    const higherStartIndex = Math.min(higherSegment.start.index, higherSegment.end.index)
    const higherEndIndex = Math.max(higherSegment.start.index, higherSegment.end.index)
    return higherStartIndex <= baseStartIndex && higherEndIndex >= baseEndIndex
  })

  if (containingHigherSegment) {
    return containingHigherSegment.direction
  }

  const latestStartedHigherSegment = [...higherSegments].reverse().find((higherSegment) => {
    const higherStartIndex = Math.min(higherSegment.start.index, higherSegment.end.index)
    return higherStartIndex <= baseStartIndex
  })

  return latestStartedHigherSegment?.direction ?? higherSegments[higherSegments.length - 1]?.direction ?? null
}

/** 三段结构是否足以首次确认一个交易区间。 */
const canCreateTradingRange = (
  previousFeature: TradingRangeFeatureSegment,
  middleSegment: BaseSegment | undefined,
  currentFeature: TradingRangeFeatureSegment,
) => {
  if (!middleSegment) {
    return false
  }

  if (
    previousFeature.higherDirection !== currentFeature.higherDirection
    || previousFeature.segment.direction !== currentFeature.segment.direction
    || middleSegment.direction === currentFeature.segment.direction
  ) {
    return false
  }

  const structureHigh = Math.max(
    getSegmentHigh(previousFeature.segment),
    getSegmentHigh(middleSegment),
    getSegmentHigh(currentFeature.segment),
  )
  const structureLow = Math.min(
    getSegmentLow(previousFeature.segment),
    getSegmentLow(middleSegment),
    getSegmentLow(currentFeature.segment),
  )
  const structureRange = structureHigh - structureLow
  if (structureRange <= 0) {
    return false
  }

  const overlapRange = getOverlapRange(
    getSegmentLow(previousFeature.segment),
    getSegmentHigh(previousFeature.segment),
    getSegmentLow(currentFeature.segment),
    getSegmentHigh(currentFeature.segment),
  )

  return overlapRange / structureRange >= INITIAL_OVERLAP_THRESHOLD
}

/** 已有交易区间后，新特征序列是否还能继续扩展这个区间。 */
const canExtendTradingRange = (range: TradingRange, feature: TradingRangeFeatureSegment) => {
  const rangeHeight = range.top - range.bottom
  if (rangeHeight <= 0 || feature.higherDirection !== range.features[range.features.length - 1]?.higherDirection) {
    return false
  }

  const featureRange = getSegmentRange(feature.segment)
  if (featureRange >= rangeHeight * EXTENSION_FEATURE_RANGE_LIMIT_MULTIPLIER) {
    return false
  }

  const overlapRange = getOverlapRange(
    range.bottom,
    range.top,
    getSegmentLow(feature.segment),
    getSegmentHigh(feature.segment),
  )

  return overlapRange / rangeHeight >= EXTENSION_OVERLAP_THRESHOLD
}

/** 活动区间失效后转入历史，同时通知主入口刷新矩形图形。 */
const finalizeActiveTradingRange = (buildState: TradingRangeBuildState) => {
  if (!buildState.activeTradingRange) {
    return
  }

  buildState.historicalTradingRanges.push(cloneTradingRange(buildState.activeTradingRange))
  buildState.activeTradingRange = null
  buildState.pendingGraphicsRefresh = true
}

/**
 * 只处理“符合大级别反向条件”的本级别线段。
 * 它们要么作为新区间的特征序列起点，要么继续扩展已有区间。
 */
const processConfirmedBaseSegment = (
  buildState: TradingRangeBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  higherSegments: HigherLevelSegment[],
  baseSegmentIndex: number,
) => {
  const baseSegment = baseSegments[baseSegmentIndex]
  if (!baseSegment) {
    return
  }

  const higherDirection = findHigherDirectionForBaseSegment(baseSegment, higherSegments)
  if (!higherDirection || baseSegment.direction !== getOppositeDirection(higherDirection)) {
    return
  }

  const feature: TradingRangeFeatureSegment = {
    baseSegmentIndex,
    higherDirection,
    segment: cloneBaseSegment(baseSegment),
  }

  let didExtendActiveRange = false

  if (buildState.activeTradingRange && canExtendTradingRange(buildState.activeTradingRange, feature)) {
    const extendedRange = calculateTradingRangeFromFeatures([
      ...buildState.activeTradingRange.features,
      feature,
    ], bars)

    if (extendedRange) {
      buildState.activeTradingRange = extendedRange
      didExtendActiveRange = true
      buildState.pendingGraphicsRefresh = true
    }
  } else if (buildState.activeTradingRange) {
    finalizeActiveTradingRange(buildState)
  }

  const previousFeature = buildState.lastFeatureSegment
  if (
    !didExtendActiveRange
    && previousFeature
    && previousFeature.baseSegmentIndex + 2 === feature.baseSegmentIndex
    && canCreateTradingRange(previousFeature, baseSegments[previousFeature.baseSegmentIndex + 1], feature)
  ) {
    const nextTradingRange = calculateTradingRangeFromFeatures([previousFeature, feature], bars)
    if (nextTradingRange) {
      buildState.activeTradingRange = nextTradingRange
      buildState.pendingGraphicsRefresh = true
    }
  }

  buildState.lastFeatureSegment = feature
}

/** 整体重建交易区间状态。 */
export const rebuildTradingRangeState = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  higherSegments: HigherLevelSegment[],
) => {
  const buildState = createEmptyTradingRangeBuildState()
  advanceTradingRangeState(buildState, bars, baseSegments, higherSegments)
  return buildState
}

/** 从 processedBaseSegmentCount 继续增量推进交易区间。 */
export const advanceTradingRangeState = (
  buildState: TradingRangeBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  higherSegments: HigherLevelSegment[],
) => {
  for (let index = buildState.processedBaseSegmentCount; index < baseSegments.length; index += 1) {
    processConfirmedBaseSegment(buildState, bars, baseSegments, higherSegments, index)
  }

  buildState.processedBaseSegmentCount = baseSegments.length
  return buildState.activeTradingRange
}

/** 对外返回可绘制的全部区间。 */
export const getAllTradingRanges = (buildState: TradingRangeBuildState) => {
  if (!buildState.activeTradingRange) {
    return buildState.historicalTradingRanges.map(cloneTradingRange)
  }

  return [
    ...buildState.historicalTradingRanges.map(cloneTradingRange),
    cloneTradingRange(buildState.activeTradingRange),
  ]
}

/** 图形层按需刷新，避免每根 K 线都重发矩形。 */
export const consumeTradingRangeGraphicsRefresh = (buildState: TradingRangeBuildState) => {
  const shouldRefresh = buildState.pendingGraphicsRefresh
  buildState.pendingGraphicsRefresh = false
  return shouldRefresh
}
