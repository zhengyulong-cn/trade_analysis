import { getBaseSegmentHighPoint, getBaseSegmentLowPoint } from './base_segment_builder'
import { getOffsetFromCurrentBar } from './base_fenxing_builder'
import type {
  BaseSegment,
  BaseSegmentMetrics,
  FenxingBar,
  HigherLevelSegment,
  MomentumExhaustionSignal,
  SegmentDirection,
  TradingRange,
} from './types'

const MOMENTUM_EXHAUSTION_OVERLAP_THRESHOLD = 0.4
/**
 * 当当前段的绝对价差小于前一同向段的 80% 时，直接判定为动能衰竭。
 *
 * 这里强调的是“priceRange 优先级高于 barSpan”：
 * 即使当前段耗时更短，只要推进价差明显缩小，也更倾向于认为它的动能已经弱了。
 * 这样可以避免把“走得更少，只是走得快一点”的段误判成不衰竭。
 */
const MOMENTUM_EXHAUSTION_PRICE_RANGE_EXHAUSTED_RATIO = 0.8
/**
 * 当当前段与前一同向段的价差比例达到这个阈值后，才认为两者“价差足够接近”，
 * 可以把 `strength = priceRange / barSpan` 作为最后一道辅助判断。
 *
 * 也就是说，barSpan 只在 priceRange 已经比较接近时才参与裁决；
 * 它不能轻易推翻 priceRange 已经给出的直觉结论。
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
 * 这套规则的核心偏好是：
 * 1. `priceRange` 是主因子，优先反映“这一段到底走了多远”；
 * 2. `barSpan` 是辅助因子，只在两个价差已经比较接近时才参与判断；
 * 3. 不能让“时间更短”轻易掩盖“价差更小”，也不能让“时间更长”轻易否定“价差更大”。
 *
 * 因此判断顺序分成四层：
 * 1. 先过滤掉本来就不该判衰竭的情况
 *    - `direction === 'up'` 时，如果 `previousMetrics.low.price > currentMetrics.low.price`，
 *      说明当前上涨段把低点压得更低，这不符合这里要判断的上涨衰竭结构，直接返回 `false`；
 *    - `direction === 'down'` 时，如果 `previousMetrics.high.price < currentMetrics.high.price`，
 *      说明当前下跌段把高点抬得更高，这不符合这里要判断的下跌衰竭结构，直接返回 `false`。
 *
 * 2. 再看关键极值有没有突破失败
 *    - 上涨里，段3高点没有超过段1高点，直接判衰竭；
 *    - 下跌里，段3低点没有低于段1低点，直接判衰竭。
 *
 * 3. 然后看绝对价差谁更占优
 *    - 如果当前段价差更大，直接判定为“不衰竭”；
 *      即使它耗时更长，也更像是节奏变慢，而不是动能真的衰竭。
 *    - 如果当前段价差明显更小，则直接判定为“衰竭”；
 *      即使它耗时更短，也不应轻易翻案。
 *
 * 4. 只有在价差足够接近时，才比较 `strength = priceRange / barSpan`
 *    - 这一步只负责处理灰区，不负责推翻前面由价差主导得出的明显结论。
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

const getOverlapRange = (
  firstLow: number,
  firstHigh: number,
  secondLow: number,
  secondHigh: number,
) => Math.max(0, Math.min(firstHigh, secondHigh) - Math.max(firstLow, secondLow))

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

const shouldJudgeMomentumExhaustion = (
  currentSegment: BaseSegment,
  lastTradingRange: TradingRange | null,
) => {
  if (!lastTradingRange) {
    return true
  }

  const currentHigh = Math.max(currentSegment.start.price, currentSegment.end.price)
  const currentLow = Math.min(currentSegment.start.price, currentSegment.end.price)
  const currentRange = Math.max(0, currentHigh - currentLow)
  if (currentRange <= 0) {
    return true
  }

  const overlapRange = getOverlapRange(
    currentLow,
    currentHigh,
    lastTradingRange.bottom,
    lastTradingRange.top,
  )

  return overlapRange / currentRange < MOMENTUM_EXHAUSTION_OVERLAP_THRESHOLD
}

export const buildMomentumExhaustionSignals = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  higherSegments: HigherLevelSegment[],
  tradingRanges: TradingRange[],
) => {
  const signals: MomentumExhaustionSignal[] = []
  const lastTradingRange = tradingRanges[tradingRanges.length - 1] ?? null

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

    if (!shouldJudgeMomentumExhaustion(currentSegment, lastTradingRange)) {
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
