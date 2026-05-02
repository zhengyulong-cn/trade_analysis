import type {
  BaseSegment,
  BaseSegmentBuildState,
  EmaSegmentBar,
  SegmentDirection,
  SegmentPoint,
  UpsertBarResult,
} from './types'

export const isFiniteNumber = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

export const createEmptyBaseSegmentBuildState = (): BaseSegmentBuildState => ({
  activeBaseSegment: null,
  historicalBaseSegments: [],
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

export const getBaseSegmentExtreme = (bar: EmaSegmentBar, direction: SegmentDirection): SegmentPoint => ({
  index: bar.index,
  price: direction === 'up' ? bar.high : bar.low,
  time: bar.time,
})

const cloneBaseSegment = (baseSegment: BaseSegment): BaseSegment => ({
  direction: baseSegment.direction,
  end: { ...baseSegment.end },
  start: { ...baseSegment.start },
})

const createBaseSegment = (
  direction: SegmentDirection,
  start: SegmentPoint,
  end: SegmentPoint,
): BaseSegment => ({
  direction,
  start: { ...start },
  end: { ...end },
})

const updateActiveBaseSegmentEnd = (baseSegment: BaseSegment, end: SegmentPoint) => {
  baseSegment.end = { ...end }
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

const createPotentialBaseSegment = (
  direction: SegmentDirection,
  referencePoint: SegmentPoint,
  reversalStartPoint: SegmentPoint | null,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
): BaseSegment | null => {
  const startBreakReversal = hasStartBreakReversal(direction, reversalStartPoint, bar)

  if (!startBreakReversal && bar.index - referencePoint.index < minSegmentBars) {
    return null
  }

  if (direction === 'up') {
    if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.high <= bar.ema)) {
      return null
    }

    const candidateEnd = getBaseSegmentExtreme(bar, 'up')

    for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
      const candidateBar = bars[index]
      if (!candidateBar) {
        continue
      }

      if (candidateBar.high > candidateEnd.price || candidateBar.low < referencePoint.price) {
        return null
      }
    }

    return createBaseSegment('up', referencePoint, candidateEnd)
  }

  if (!startBreakReversal && (!isFiniteNumber(bar.ema) || bar.low >= bar.ema)) {
    return null
  }

  const candidateEnd = getBaseSegmentExtreme(bar, 'down')

  for (let index = referencePoint.index + 1; index <= bar.index; index += 1) {
    const candidateBar = bars[index]
    if (!candidateBar) {
      continue
    }

    if (candidateBar.low < candidateEnd.price || candidateBar.high > referencePoint.price) {
      return null
    }
  }

  return createBaseSegment('down', referencePoint, candidateEnd)
}

const processSeedState = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  if (buildState.seedDirection === null || buildState.seedExtreme === null) {
    if (bar.close < bar.ema) {
      buildState.seedDirection = 'down'
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'down')
    } else if (bar.close > bar.ema) {
      buildState.seedDirection = 'up'
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'up')
    }
    return
  }

  if (buildState.seedDirection === 'down') {
    if (bar.low < buildState.seedExtreme.price) {
      buildState.seedExtreme = getBaseSegmentExtreme(bar, 'down')
      return
    }

    const nextActiveBaseSegment = createPotentialBaseSegment('up', buildState.seedExtreme, null, bars, bar, minSegmentBars)
    if (nextActiveBaseSegment) {
      buildState.activeBaseSegment = nextActiveBaseSegment
      buildState.seedDirection = null
      buildState.seedExtreme = null
    }
    return
  }

  if (bar.high > buildState.seedExtreme.price) {
    buildState.seedExtreme = getBaseSegmentExtreme(bar, 'up')
    return
  }

  const nextActiveBaseSegment = createPotentialBaseSegment('down', buildState.seedExtreme, null, bars, bar, minSegmentBars)
  if (nextActiveBaseSegment) {
    buildState.activeBaseSegment = nextActiveBaseSegment
    buildState.seedDirection = null
    buildState.seedExtreme = null
  }
}

const processActiveBaseSegment = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  minSegmentBars: number,
) => {
  const activeBaseSegment = buildState.activeBaseSegment
  if (!activeBaseSegment) {
    return
  }

  if (activeBaseSegment.direction === 'down') {
    if (bar.low < activeBaseSegment.end.price) {
      updateActiveBaseSegmentEnd(activeBaseSegment, getBaseSegmentExtreme(bar, 'down'))
      return
    }

    const nextActiveBaseSegment = createPotentialBaseSegment(
      'up',
      activeBaseSegment.end,
      activeBaseSegment.start,
      bars,
      bar,
      minSegmentBars,
    )
    if (nextActiveBaseSegment) {
      buildState.historicalBaseSegments.push(cloneBaseSegment(activeBaseSegment))
      buildState.activeBaseSegment = nextActiveBaseSegment
    }
    return
  }

  if (bar.high > activeBaseSegment.end.price) {
    updateActiveBaseSegmentEnd(activeBaseSegment, getBaseSegmentExtreme(bar, 'up'))
    return
  }

  const nextActiveBaseSegment = createPotentialBaseSegment(
    'down',
    activeBaseSegment.end,
    activeBaseSegment.start,
    bars,
    bar,
    minSegmentBars,
  )
  if (nextActiveBaseSegment) {
    buildState.historicalBaseSegments.push(cloneBaseSegment(activeBaseSegment))
    buildState.activeBaseSegment = nextActiveBaseSegment
  }
}

const processBaseSegmentBar = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  bar: EmaSegmentBar,
  emaLength: number,
  minSegmentBars: number,
) => {
  if (bar.index + 1 < emaLength || !isFiniteNumber(bar.ema)) {
    return
  }

  if (buildState.activeBaseSegment) {
    processActiveBaseSegment(buildState, bars, bar, minSegmentBars)
    return
  }

  processSeedState(buildState, bars, bar, minSegmentBars)
}

export const advanceBaseSegmentState = (
  buildState: BaseSegmentBuildState,
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  for (let index = buildState.processedBarCount; index < bars.length; index += 1) {
    const bar = bars[index]
    if (!bar) {
      continue
    }

    processBaseSegmentBar(buildState, bars, bar, emaLength, minSegmentBars)
  }

  buildState.processedBarCount = bars.length
  return getAllBaseSegments(buildState)
}

export const rebuildBaseSegmentState = (
  bars: EmaSegmentBar[],
  emaLength: number,
  minSegmentBars: number,
) => {
  const buildState = createEmptyBaseSegmentBuildState()
  advanceBaseSegmentState(buildState, bars, emaLength, minSegmentBars)
  return buildState
}

export const getAllBaseSegments = (buildState: BaseSegmentBuildState) => {
  if (!buildState.activeBaseSegment) {
    return [...buildState.historicalBaseSegments]
  }

  return [...buildState.historicalBaseSegments, cloneBaseSegment(buildState.activeBaseSegment)]
}

export const getLatestDrawableBaseSegment = (buildState: BaseSegmentBuildState) => {
  if (buildState.activeBaseSegment) {
    return buildState.activeBaseSegment
  }

  return buildState.historicalBaseSegments[buildState.historicalBaseSegments.length - 1] ?? null
}

export const buildBaseSegments = (bars: EmaSegmentBar[], emaLength: number, minSegmentBars: number) => {
  return getAllBaseSegments(rebuildBaseSegmentState(bars, emaLength, minSegmentBars))
}

export const getBaseSegmentKey = (baseSegment: BaseSegment) => {
  return `${baseSegment.start.time}-${baseSegment.direction}`
}

export const getOffsetFromCurrentBar = (bars: EmaSegmentBar[], point: SegmentPoint) => {
  const lastBar = bars[bars.length - 1]
  if (!lastBar) {
    return 0
  }

  return point.index - lastBar.index
}
