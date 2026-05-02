import type {
  EmaSegment,
  EmaSegmentBar,
  EmaSegmentBuildState,
  SegmentDirection,
  SegmentPoint,
  UpsertBarResult,
} from './types'

export const isFiniteNumber = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

export const createEmptyEmaSegmentBuildState = (): EmaSegmentBuildState => ({
  activeSegment: null,
  historicalSegments: [],
  processedBarCount: 0,
  seedDirection: null,
  seedExtreme: null,
})

export const upsertBar = (bars: EmaSegmentBar[], bar: Omit<EmaSegmentBar, 'index'>): UpsertBarResult => {
  const lastBar = bars[bars.length - 1]

  if (!lastBar || bar.time > lastBar.time) {
    bars.push({
      ...bar,
      index: bars.length,
    })
    return {
      index: bars.length - 1,
      type: 'append',
    }
  }

  if (bar.time === lastBar.time) {
    bars[bars.length - 1] = {
      ...bar,
      index: lastBar.index,
    }
    return {
      index: lastBar.index,
      type: 'replace_last',
    }
  }

  const existingIndex = bars.findIndex((item) => item.time === bar.time)
  if (existingIndex >= 0) {
    bars[existingIndex] = {
      ...bar,
      index: existingIndex,
    }
    return {
      index: existingIndex,
      type: 'replace_existing',
    }
  }

  bars.push({
    ...bar,
    index: bars.length,
  })
  bars.sort((first, second) => first.time - second.time)
  bars.forEach((item, index) => {
    item.index = index
  })

  return {
    index: bars.findIndex((item) => item.time === bar.time),
    type: 'insert_historical',
  }
}

export const getSegmentExtreme = (bar: EmaSegmentBar, direction: SegmentDirection): SegmentPoint => ({
  index: bar.index,
  price: direction === 'up' ? bar.high : bar.low,
  time: bar.time,
})

const cloneSegment = (segment: EmaSegment): EmaSegment => ({
  direction: segment.direction,
  end: { ...segment.end },
  start: { ...segment.start },
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

const updateActiveSegmentEnd = (segment: EmaSegment, end: SegmentPoint) => {
  segment.end = { ...end }
}

const hasStartBreakReversal = (
  direction: SegmentDirection,
  reversalStartPoint: SegmentPoint | null,
  bar: EmaSegmentBar,
) => {
  if (!reversalStartPoint) {
    return false
  }

  if (direction === 'up') {
    return bar.high >= reversalStartPoint.price
  }

  return bar.low <= reversalStartPoint.price
}

const createPotentialSegment = (
  direction: SegmentDirection,
  referencePoint: SegmentPoint,
  reversalStartPoint: SegmentPoint | null,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
): EmaSegment | null => {
  const startBreakReversal = hasStartBreakReversal(direction, reversalStartPoint, bar)

  if (!startBreakReversal && bar.index - referencePoint.index < minSegmentBars) {
    return null
  }

  if (direction === 'up') {
    if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.high <= bar.ema)) {
      return null
    }

    const candidateEnd = getSegmentExtreme(bar, 'up')

    for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
      const candidateBar = bars[index]
      if (!candidateBar) {
        continue
      }

      if (candidateBar.high > candidateEnd.price || candidateBar.low < referencePoint.price) {
        return null
      }
    }

    return createSegment('up', referencePoint, candidateEnd)
  }

  if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.low >= bar.ema)) {
    return null
  }

  const candidateEnd = getSegmentExtreme(bar, 'down')

  for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
    const candidateBar = bars[index]
    if (!candidateBar) {
      continue
    }

    if (candidateBar.low < candidateEnd.price || candidateBar.high > referencePoint.price) {
      return null
    }
  }

  return createSegment('down', referencePoint, candidateEnd)
}

const processSeedState = (
  buildState: EmaSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  if (buildState.seedDirection === null || buildState.seedExtreme === null) {
    if (bar.close < bar.ema) {
      buildState.seedDirection = 'down'
      buildState.seedExtreme = getSegmentExtreme(bar, 'down')
    } else if (bar.close > bar.ema) {
      buildState.seedDirection = 'up'
      buildState.seedExtreme = getSegmentExtreme(bar, 'up')
    }
    return
  }

  if (buildState.seedDirection === 'down') {
    if (bar.low < buildState.seedExtreme.price) {
      buildState.seedExtreme = getSegmentExtreme(bar, 'down')
      return
    }

    const nextActiveSegment = createPotentialSegment('up', buildState.seedExtreme, null, bars, bar, minSegmentBars)
    if (nextActiveSegment) {
      buildState.activeSegment = nextActiveSegment
      buildState.seedDirection = null
      buildState.seedExtreme = null
    }
    return
  }

  if (bar.high > buildState.seedExtreme.price) {
    buildState.seedExtreme = getSegmentExtreme(bar, 'up')
    return
  }

  const nextActiveSegment = createPotentialSegment('down', buildState.seedExtreme, null, bars, bar, minSegmentBars)
  if (nextActiveSegment) {
    buildState.activeSegment = nextActiveSegment
    buildState.seedDirection = null
    buildState.seedExtreme = null
  }
}

const processActiveSegment = (
  buildState: EmaSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  const activeSegment = buildState.activeSegment
  if (!activeSegment) {
    return
  }

  if (activeSegment.direction === 'down') {
    if (bar.low < activeSegment.end.price) {
      updateActiveSegmentEnd(activeSegment, getSegmentExtreme(bar, 'down'))
      return
    }

    const nextActiveSegment = createPotentialSegment('up', activeSegment.end, activeSegment.start, bars, bar, minSegmentBars)
    if (nextActiveSegment) {
      buildState.historicalSegments.push(cloneSegment(activeSegment))
      buildState.activeSegment = nextActiveSegment
    }
    return
  }

  if (bar.high > activeSegment.end.price) {
    updateActiveSegmentEnd(activeSegment, getSegmentExtreme(bar, 'up'))
    return
  }

  const nextActiveSegment = createPotentialSegment('down', activeSegment.end, activeSegment.start, bars, bar, minSegmentBars)
  if (nextActiveSegment) {
    buildState.historicalSegments.push(cloneSegment(activeSegment))
    buildState.activeSegment = nextActiveSegment
  }
}

const processEmaSegmentBar = (
  buildState: EmaSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  emaLength: number,
  minSegmentBars: number,
) => {
  if (bar.index + 1 < emaLength || !isFiniteNumber(bar.ema)) {
    return
  }

  if (buildState.activeSegment) {
    processActiveSegment(buildState, bars, bar, minSegmentBars)
    return
  }

  processSeedState(buildState, bars, bar, minSegmentBars)
}

export const advanceEmaSegmentState = (
  buildState: EmaSegmentBuildState,
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    const bar = bars[index]
    if (!bar) {
      continue
    }

    processEmaSegmentBar(buildState, bars, bar, emaLength, minSegmentBars)
  }

  buildState.processedBarCount = bars.length
  return getAllSegments(buildState)
}

export const rebuildEmaSegmentState = (
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  const buildState = createEmptyEmaSegmentBuildState()
  advanceEmaSegmentState(buildState, bars, emaLength, minSegmentBars)
  return buildState
}

export const getAllSegments = (buildState: EmaSegmentBuildState) => {
  if (!buildState.activeSegment) {
    return [...buildState.historicalSegments]
  }

  return [...buildState.historicalSegments, cloneSegment(buildState.activeSegment)]
}

export const getLatestDrawableSegment = (buildState: EmaSegmentBuildState) => {
  if (buildState.activeSegment) {
    return buildState.activeSegment
  }

  return buildState.historicalSegments[buildState.historicalSegments.length - 1] ?? null
}

export const buildEmaSegments = (bars: EmaSegmentBar[], emaLength: number, minSegmentBars: number) => {
  return getAllSegments(rebuildEmaSegmentState(bars, emaLength, minSegmentBars))
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
