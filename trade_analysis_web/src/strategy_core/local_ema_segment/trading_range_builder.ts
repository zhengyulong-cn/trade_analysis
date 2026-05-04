import type {
  BaseSegment,
  SegmentDirection,
  SegmentPoint,
  TradingRange,
  TradingRangeBuildState,
  TradingRangeFeatureSegment,
} from './types'

const INITIAL_OVERLAP_THRESHOLD = 0.6
const EXTENSION_OVERLAP_THRESHOLD = 0.5

const clonePoint = (point: SegmentPoint): SegmentPoint => ({
  index: point.index,
  price: point.price,
  time: point.time,
})

const cloneBaseSegment = (segment: BaseSegment): BaseSegment => ({
  direction: segment.direction,
  end: clonePoint(segment.end),
  start: clonePoint(segment.start),
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

export const createEmptyTradingRangeBuildState = (): TradingRangeBuildState => ({
  activeTradingRange: null,
  historicalTradingRanges: [],
  lastFeatureSegment: null,
  pendingGraphicsRefresh: false,
  processedBaseSegmentCount: 0,
})

const getOppositeDirection = (direction: SegmentDirection): SegmentDirection => (
  direction === 'up' ? 'down' : 'up'
)

const getSegmentHigh = (segment: BaseSegment) => Math.max(segment.start.price, segment.end.price)

const getSegmentLow = (segment: BaseSegment) => Math.min(segment.start.price, segment.end.price)

const getSegmentRange = (segment: BaseSegment) => getSegmentHigh(segment) - getSegmentLow(segment)

const getOverlapRange = (
  firstLow: number,
  firstHigh: number,
  secondLow: number,
  secondHigh: number,
) => Math.max(0, Math.min(firstHigh, secondHigh) - Math.max(firstLow, secondLow))

const getSecondValue = (values: number[], direction: 'asc' | 'desc') => {
  const sortedValues = [...values].sort((first, second) => (
    direction === 'asc' ? first - second : second - first
  ))

  return sortedValues[Math.min(1, sortedValues.length - 1)]
}

export const calculateTradingRangeFromFeatures = (
  features: TradingRangeFeatureSegment[],
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

  return {
    bottom,
    features: features.map(cloneFeatureSegment),
    left: clonePoint(firstFeature.segment.start),
    right: clonePoint(lastFeature.segment.end),
    top,
  }
}

const findHigherDirectionForBaseSegment = (
  baseSegment: BaseSegment,
  higherSegments: BaseSegment[],
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

  const middleRange = getSegmentRange(middleSegment)
  if (middleRange <= 0) {
    return false
  }

  const overlapRange = getOverlapRange(
    getSegmentLow(previousFeature.segment),
    getSegmentHigh(previousFeature.segment),
    getSegmentLow(currentFeature.segment),
    getSegmentHigh(currentFeature.segment),
  )

  return overlapRange / middleRange >= INITIAL_OVERLAP_THRESHOLD
}

const canExtendTradingRange = (range: TradingRange, feature: TradingRangeFeatureSegment) => {
  const rangeHeight = range.top - range.bottom
  if (rangeHeight <= 0 || feature.higherDirection !== range.features[range.features.length - 1]?.higherDirection) {
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

const finalizeActiveTradingRange = (buildState: TradingRangeBuildState) => {
  if (!buildState.activeTradingRange) {
    return
  }

  buildState.historicalTradingRanges.push(cloneTradingRange(buildState.activeTradingRange))
  buildState.activeTradingRange = null
  buildState.pendingGraphicsRefresh = true
}

const processConfirmedBaseSegment = (
  buildState: TradingRangeBuildState,
  baseSegments: BaseSegment[],
  higherSegments: BaseSegment[],
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
    ])

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
    const nextTradingRange = calculateTradingRangeFromFeatures([previousFeature, feature])
    if (nextTradingRange) {
      buildState.activeTradingRange = nextTradingRange
      buildState.pendingGraphicsRefresh = true
    }
  }

  buildState.lastFeatureSegment = feature
}

export const rebuildTradingRangeState = (
  baseSegments: BaseSegment[],
  higherSegments: BaseSegment[],
) => {
  const buildState = createEmptyTradingRangeBuildState()
  advanceTradingRangeState(buildState, baseSegments, higherSegments)
  return buildState
}

export const advanceTradingRangeState = (
  buildState: TradingRangeBuildState,
  baseSegments: BaseSegment[],
  higherSegments: BaseSegment[],
) => {
  for (let index = buildState.processedBaseSegmentCount; index < baseSegments.length; index += 1) {
    processConfirmedBaseSegment(buildState, baseSegments, higherSegments, index)
  }

  buildState.processedBaseSegmentCount = baseSegments.length
  return buildState.activeTradingRange
}

export const getAllTradingRanges = (buildState: TradingRangeBuildState) => {
  if (!buildState.activeTradingRange) {
    return [...buildState.historicalTradingRanges].map(cloneTradingRange)
  }

  return [
    ...buildState.historicalTradingRanges.map(cloneTradingRange),
    cloneTradingRange(buildState.activeTradingRange),
  ]
}

export const consumeTradingRangeGraphicsRefresh = (buildState: TradingRangeBuildState) => {
  const shouldRefresh = buildState.pendingGraphicsRefresh
  buildState.pendingGraphicsRefresh = false
  return shouldRefresh
}
