import type { EmaSegment, EmaSegmentBar, SegmentDirection, SegmentPoint } from './types'

export const isFiniteNumber = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

export const upsertBar = (bars: EmaSegmentBar[], bar: Omit<EmaSegmentBar, 'index'>) => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || bar.time > lastBar.time) {
    bars.push({
      ...bar,
      index: bars.length,
    })
    return
  }

  if (bar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...bar,
      index: lastBar.index,
    }
    return
  }

  const existingIndex = bars.findIndex((item) => item.time === bar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...bar,
      index: existingIndex,
    }
    return
  }

  bars.push({
    ...bar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((item, index) => {
    item.index = index
  })
}

export const getSegmentExtreme = (bar: EmaSegmentBar, direction: SegmentDirection): SegmentPoint => ({
  index: bar.index,
  price: direction === 'up' ? bar.high : bar.low,
  time: bar.time,
})

const createSegment = (
  direction: SegmentDirection,
  start: SegmentPoint,
  end: SegmentPoint,
): EmaSegment => ({
  direction,
  start: { ...start },
  end: { ...end },
})

const updateLastSegmentEnd = (segments: EmaSegment[], end: SegmentPoint) => {
  const lastSegment = segments[segments.length - 1]
  if (!lastSegment) {
    return
  }

  lastSegment.end = { ...end }
}

/**
 * 根据EMA构建线段
 * @param bars K线
 * @param emaLength EMA长度
 * @param minSegmentBars 线段最小间距
 * @returns 
 */
export const buildEmaSegments = (bars: EmaSegmentBar[], emaLength: number, minSegmentBars: number) => {
  const segments: EmaSegment[] = []
  let activeDirection: SegmentDirection | null = null
  let activeEnd: SegmentPoint | null = null
  let hasDrawableActiveSegment = false

  bars.forEach((bar) => {
    if (bar.index + 1 < emaLength || !isFiniteNumber(bar.ema)) {
      return
    }

    if (activeDirection === null || activeEnd === null) {
      if (bar.close < bar.ema) {
        activeDirection = 'down'
        activeEnd = getSegmentExtreme(bar, 'down')
      } else if (bar.close > bar.ema) {
        activeDirection = 'up'
        activeEnd = getSegmentExtreme(bar, 'up')
      }
      return
    }

    if (activeDirection === 'down') {
      if (bar.low < bar.ema && bar.low < activeEnd.price) {
        activeEnd = getSegmentExtreme(bar, 'down')
        if (hasDrawableActiveSegment) {
          updateLastSegmentEnd(segments, activeEnd)
        }
        return
      }

      if (bar.high > bar.ema && bar.index - activeEnd.index >= minSegmentBars) {
        const nextEnd = getSegmentExtreme(bar, 'up')
        const nextSegment = createSegment('up', activeEnd, nextEnd)

        segments.push(nextSegment)
        activeDirection = 'up'
        activeEnd = nextEnd
        hasDrawableActiveSegment = true
      }
      return
    }

    if (bar.high > bar.ema && bar.high > activeEnd.price) {
      activeEnd = getSegmentExtreme(bar, 'up')
      if (hasDrawableActiveSegment) {
        updateLastSegmentEnd(segments, activeEnd)
      }
      return
    }

    if (bar.low < bar.ema && bar.index - activeEnd.index >= minSegmentBars) {
      const nextEnd = getSegmentExtreme(bar, 'down')
      const nextSegment = createSegment('down', activeEnd, nextEnd)

      segments.push(nextSegment)
      activeDirection = 'down'
      activeEnd = nextEnd
      hasDrawableActiveSegment = true
    }
  })

  return segments
}

export const getSegmentKey = (segment: EmaSegment) => {
  return `${segment.start.time}-${segment.direction}`
}

export const getOffsetFromCurrentBar = (bars: EmaSegmentBar[], point: SegmentPoint) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}
