import type {
  BaseSegment,
  BaseSegmentMetrics,
  EmaSegmentBar,
  MomentumExhaustionSignal,
  SegmentDirection,
} from './types'
import { getBaseSegmentExtreme, getOffsetFromCurrentBar } from './base_segment_builder'

const getBaseSegmentMetrics = (bars: EmaSegmentBar[], baseSegment: BaseSegment): BaseSegmentMetrics | null => {
  const startIndex = Math.min(baseSegment.start.index, baseSegment.end.index)
  const endIndex = Math.max(baseSegment.start.index, baseSegment.end.index)
  const baseSegmentBars = bars.filter((bar) => bar.index >= startIndex && bar.index <= endIndex)
  const firstBar = baseSegmentBars[0]

  if (!firstBar) {
    return null
  }

  let high = getBaseSegmentExtreme(firstBar, 'up')
  let low = getBaseSegmentExtreme(firstBar, 'down')

  baseSegmentBars.forEach((bar) => {
    if (bar.high > high.price) {
      high = getBaseSegmentExtreme(bar, 'up')
    }

    if (bar.low < low.price) {
      low = getBaseSegmentExtreme(bar, 'down')
    }
  })

  const priceRange = high.price - low.price
  const barSpan = Math.max(1, endIndex - startIndex + 1)

  return {
    barSpan,
    high,
    low,
    priceRange,
    strength: priceRange / barSpan,
  }
}

const getStructureTrend = (
  previousMetrics: BaseSegmentMetrics,
  currentMetrics: BaseSegmentMetrics,
): SegmentDirection | null => {
  if (currentMetrics.high.price > previousMetrics.high.price && currentMetrics.low.price > previousMetrics.low.price) {
    return 'up'
  }

  if (currentMetrics.high.price < previousMetrics.high.price && currentMetrics.low.price < previousMetrics.low.price) {
    return 'down'
  }

  return null
}

export const buildMomentumExhaustionSignals = (bars: EmaSegmentBar[], baseSegments: BaseSegment[]) => {
  const signals: MomentumExhaustionSignal[] = []
  let activeTrend: SegmentDirection | null = null

  for (let index = 2; index < baseSegments.length; index += 1) {
    const currentBaseSegment = baseSegments[index]
    const previousSameDirectionBaseSegment = baseSegments[index - 2]

    if (!currentBaseSegment || !previousSameDirectionBaseSegment) {
      continue
    }

    if (currentBaseSegment.direction !== previousSameDirectionBaseSegment.direction) {
      continue
    }

    const previousMetrics = getBaseSegmentMetrics(bars, previousSameDirectionBaseSegment)
    const currentMetrics = getBaseSegmentMetrics(bars, currentBaseSegment)

    if (!previousMetrics || !currentMetrics) {
      continue
    }

    const structureTrend = getStructureTrend(previousMetrics, currentMetrics)

    if (activeTrend === null) {
      if (structureTrend === null) {
        continue
      }

      activeTrend = structureTrend
    } else if (structureTrend !== null) {
      activeTrend = structureTrend
    }

    if (currentBaseSegment.direction !== activeTrend) {
      continue
    }

    if (currentMetrics.strength >= previousMetrics.strength) {
      continue
    }

    signals.push({
      direction: currentBaseSegment.direction,
      point: currentBaseSegment.direction === 'up' ? currentMetrics.high : currentMetrics.low,
    })
  }

  return signals
}

export const getMomentumExhaustionOutput = (bars: EmaSegmentBar[], signals: MomentumExhaustionSignal[]) => {
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
