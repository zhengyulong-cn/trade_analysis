import { getBaseSegmentHighPoint, getBaseSegmentLowPoint } from './base_segment_builder'
import { getOffsetFromCurrentBar } from './base_fenxing_builder'
import type {
  BaseSegment,
  BaseSegmentMetrics,
  FenxingBar,
  HigherLevelSegment,
  MomentumExhaustionSignal,
  SegmentDirection,
} from './types'

/**
 * 当当前段的绝对价差小于前一同向段的 80% 时，直接判定为动能衰竭。
 *
 * 这里强调的是“priceRange 优先于 barSpan”：
 * 即使当前段耗时更短，只要推进价差明显缩小，也更倾向于认为它的动能已经弱了。
 */
const MOMENTUM_EXHAUSTION_PRICE_RANGE_EXHAUSTED_RATIO = 0.8

/**
 * 当当前段与前一同向段的价差比例达到这个阈值后，才认为两者价差足够接近，
 * 可以把 `strength = priceRange / barSpan` 作为最后一道辅助判断。
 */
const MOMENTUM_EXHAUSTION_PRICE_RANGE_CLOSE_RATIO = 0.9

const getSegmentMetrics = (
  bars: FenxingBar[],
  baseSegment: BaseSegment,
): BaseSegmentMetrics | null => {
  const startIndex = Math.min(baseSegment.start.index, baseSegment.end.index)
  const endIndex = Math.max(baseSegment.start.index, baseSegment.end.index)
  const high = getBaseSegmentHighPoint(baseSegment)
  const low = getBaseSegmentLowPoint(baseSegment)
  const priceRange = Math.max(0, high.price - low.price)
  const barSpan = Math.max(1, endIndex - startIndex + 1)

  if (!bars[startIndex] || !bars[endIndex]) {
    return null
  }

  return {
    barSpan,
    high,
    low,
    priceRange,
    strength: priceRange / barSpan,
  }
}

/**
 * 判断前一同向段(段1)与当前同向段(段3)之间是否构成动能衰竭。
 *
 * 规则：
 * 1. `priceRange` 是主因子，`barSpan` 只在价差接近时参与辅助判断；
 * 2. 当前段价差更小，即使更快，也更偏向衰竭；
 * 3. 当前段价差更大，即使更慢，也更偏向不衰竭。
 */
const isMomentumExhausted = (
  direction: SegmentDirection,
  previousMetrics: BaseSegmentMetrics,
  currentMetrics: BaseSegmentMetrics,
) => {
  if (direction === 'up' && previousMetrics.low.price > currentMetrics.low.price) {
    return false
  }

  if (direction === 'down' && previousMetrics.high.price < currentMetrics.high.price) {
    return false
  }

  if (direction === 'up' && previousMetrics.high.price >= currentMetrics.high.price) {
    return true
  }

  if (direction === 'down' && previousMetrics.low.price <= currentMetrics.low.price) {
    return true
  }

  if (previousMetrics.priceRange <= 0) {
    return false
  }

  if (currentMetrics.priceRange > previousMetrics.priceRange) {
    return false
  }

  const currentPriceRangeRatio = currentMetrics.priceRange / previousMetrics.priceRange

  if (currentPriceRangeRatio < MOMENTUM_EXHAUSTION_PRICE_RANGE_EXHAUSTED_RATIO) {
    return true
  }

  if (currentPriceRangeRatio < MOMENTUM_EXHAUSTION_PRICE_RANGE_CLOSE_RATIO) {
    return false
  }

  return previousMetrics.strength >= currentMetrics.strength
}

const getHigherDirectionForBaseSegment = (
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

export const buildMomentumExhaustionSignals = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  higherSegments: HigherLevelSegment[],
) => {
  const signals: MomentumExhaustionSignal[] = []

  for (let index = 2; index < baseSegments.length; index += 1) {
    const currentSegment = baseSegments[index]
    const previousSameDirectionSegment = baseSegments[index - 2]
    if (!currentSegment || !previousSameDirectionSegment) {
      continue
    }

    if (currentSegment.direction !== previousSameDirectionSegment.direction) {
      continue
    }

    const higherDirection = getHigherDirectionForBaseSegment(currentSegment, higherSegments)
    if (!higherDirection || currentSegment.direction !== higherDirection) {
      continue
    }

    const previousHigherDirection = getHigherDirectionForBaseSegment(previousSameDirectionSegment, higherSegments)
    if (previousHigherDirection !== higherDirection) {
      continue
    }

    const previousMetrics = getSegmentMetrics(bars, previousSameDirectionSegment)
    const currentMetrics = getSegmentMetrics(bars, currentSegment)
    if (!previousMetrics || !currentMetrics) {
      continue
    }

    if (!isMomentumExhausted(currentSegment.direction, previousMetrics, currentMetrics)) {
      continue
    }

    signals.push({
      currentStrength: currentMetrics.strength,
      direction: currentSegment.direction,
      point: currentSegment.direction === 'up' ? currentMetrics.high : currentMetrics.low,
      previousStrength: previousMetrics.strength,
    })
  }

  return signals
}

export const getMomentumExhaustionOutput = (
  bars: FenxingBar[],
  signals: MomentumExhaustionSignal[],
) => {
  const latestSignal = signals[signals.length - 1]

  if (!latestSignal) {
    return [Number.NaN, Number.NaN, Number.NaN, Number.NaN]
  }

  const offset = getOffsetFromCurrentBar(bars, latestSignal.point)

  if (latestSignal.direction === 'up') {
    return [latestSignal.point.price, offset, Number.NaN, Number.NaN]
  }

  return [Number.NaN, Number.NaN, latestSignal.point.price, offset]
}
