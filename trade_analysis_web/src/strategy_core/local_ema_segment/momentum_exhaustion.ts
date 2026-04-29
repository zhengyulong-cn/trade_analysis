import type {
  EmaSegment,
  EmaSegmentBar,
  MomentumExhaustionSignal,
  SegmentDirection,
  SegmentMetrics,
} from './types'
import { getOffsetFromCurrentBar, getSegmentExtreme } from './segment_builder'

const getSegmentMetrics = (bars: EmaSegmentBar[], segment: EmaSegment): SegmentMetrics | null => {
  const startIndex = Math.min(segment.start.index, segment.end.index)
  const endIndex = Math.max(segment.start.index, segment.end.index)
  const segmentBars = bars.filter((bar) => bar.index >= startIndex && bar.index <= endIndex)
  const firstBar = segmentBars[0]

  if (!firstBar) {
    return null
  }

  let high = getSegmentExtreme(firstBar, 'up')
  let low = getSegmentExtreme(firstBar, 'down')

  segmentBars.forEach((bar) => {
    if (bar.high > high.price) {
      high = getSegmentExtreme(bar, 'up')
    }

    if (bar.low < low.price) {
      low = getSegmentExtreme(bar, 'down')
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
  previousMetrics: SegmentMetrics,
  currentMetrics: SegmentMetrics,
): SegmentDirection | null => {
  if (currentMetrics.high.price > previousMetrics.high.price && currentMetrics.low.price > previousMetrics.low.price) {
    return 'up'
  }

  if (currentMetrics.high.price < previousMetrics.high.price && currentMetrics.low.price < previousMetrics.low.price) {
    return 'down'
  }

  return null
}

export const buildMomentumExhaustionSignals = (bars: EmaSegmentBar[], segments: EmaSegment[]) => {
  const signals: MomentumExhaustionSignal[] = []
  let activeTrend: SegmentDirection | null = null

  for (let index = 2; index < segments.length; index += 1) {
    const currentSegment = segments[index]
    const previousSameDirectionSegment = segments[index - 2]

    if (!currentSegment || !previousSameDirectionSegment) {
      continue
    }

    if (currentSegment.direction !== previousSameDirectionSegment.direction) {
      continue
    }

    const previousMetrics = getSegmentMetrics(bars, previousSameDirectionSegment)
    const currentMetrics = getSegmentMetrics(bars, currentSegment)

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

    if (currentSegment.direction !== activeTrend) {
      continue
    }

    if (currentMetrics.strength >= previousMetrics.strength) {
      continue
    }

    signals.push({
      direction: currentSegment.direction,
      point: currentSegment.direction === 'up' ? currentMetrics.high : currentMetrics.low,
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
