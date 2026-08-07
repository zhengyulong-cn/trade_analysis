import { getBaseSegmentHighPoint, getBaseSegmentLowPoint } from './base_segment_builder'
import { getOffsetFromCurrentBar } from './base_fenxing_builder'
import type {
  BaseSegment,
  FenxingBar,
  MomentumExhaustionBuildState,
  MomentumExhaustionSignal,
  SegmentDirection,
} from './types'

type MacdCrossType = 'golden' | 'dead'

type SegmentRange = {
  high: number
  low: number
}

const isGoldenCross = (previousBar: FenxingBar, currentBar: FenxingBar) => {
  return previousBar.macdDiff <= previousBar.macdDea && currentBar.macdDiff > currentBar.macdDea
}

const isDeadCross = (previousBar: FenxingBar, currentBar: FenxingBar) => {
  return previousBar.macdDiff >= previousBar.macdDea && currentBar.macdDiff < currentBar.macdDea
}

const getSegmentClosedInterval = (segment: BaseSegment) => {
  return {
    endIndex: Math.max(segment.start.index, segment.end.index),
    startIndex: Math.min(segment.start.index, segment.end.index),
  }
}

const getRecentThreeSegmentsBeforeIndex = (
  baseSegments: BaseSegment[],
  barIndex: number,
) => {
  const availableSegments = baseSegments.filter((segment) => {
    const { endIndex } = getSegmentClosedInterval(segment)
    return endIndex <= barIndex
  })

  if (availableSegments.length < 3) {
    return null
  }

  return availableSegments.slice(-3)
}

const getSegmentRange = (segment: BaseSegment): SegmentRange => {
  return {
    high: getBaseSegmentHighPoint(segment).price,
    low: getBaseSegmentLowPoint(segment).price,
  }
}

const getSameDirectionMacdArea = (
  bars: FenxingBar[],
  segment: BaseSegment,
) => {
  const { startIndex, endIndex } = getSegmentClosedInterval(segment)
  let area = 0

  for (let index = startIndex; index <= endIndex; index += 1) {
    const bar = bars[index]
    if (!bar) {
      continue
    }

    if (segment.direction === 'up') {
      area += Math.max(bar.macdHistogram, 0)
      continue
    }

    area += Math.abs(Math.min(bar.macdHistogram, 0))
  }

  return area
}

const isValidThreeSegmentStructure = (
  segments: BaseSegment[],
  crossType: MacdCrossType,
) => {
  const [segmentA, segmentB, segmentC] = segments
  if (!segmentA || !segmentB || !segmentC) {
    return false
  }

  if (crossType === 'golden') {
    return segmentA.direction === 'down'
      && segmentB.direction === 'up'
      && segmentC.direction === 'down'
  }

  return segmentA.direction === 'up'
    && segmentB.direction === 'down'
    && segmentC.direction === 'up'
}

const isUpMomentumExhausted = (
  rangeA: SegmentRange,
  rangeC: SegmentRange,
  areaA: number,
  areaC: number,
) => {
  if (rangeA.low <= rangeC.low && rangeA.high < rangeC.high) {
    return areaC < areaA
  }

  if (rangeA.low <= rangeC.low && rangeA.high >= rangeC.high) {
    return true
  }

  if (rangeA.low > rangeC.low && rangeA.high < rangeC.high) {
    return false
  }

  return false
}

const isDownMomentumExhausted = (
  rangeA: SegmentRange,
  rangeC: SegmentRange,
  areaA: number,
  areaC: number,
) => {
  if (rangeA.high >= rangeC.high && rangeA.low > rangeC.low) {
    return areaC < areaA
  }

  if (rangeA.high >= rangeC.high && rangeA.low <= rangeC.low) {
    return true
  }

  if (rangeA.high < rangeC.high && rangeA.low > rangeC.low) {
    return false
  }

  return false
}

const buildSignalFromCross = (
  bars: FenxingBar[],
  crossBarIndex: number,
  direction: SegmentDirection,
  previousArea: number,
  currentArea: number,
): MomentumExhaustionSignal | null => {
  const crossBar = bars[crossBarIndex]
  if (!crossBar) {
    return null
  }

  return {
    currentStrength: currentArea,
    direction,
    point: {
      index: crossBar.index,
      price: direction === 'up' ? crossBar.high : crossBar.low,
      time: crossBar.time,
    },
    previousStrength: previousArea,
  }
}

const appendSignalForBar = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
  barIndex: number,
) => {
  const previousBar = bars[barIndex - 1]
  const currentBar = bars[barIndex]
  if (!previousBar || !currentBar) {
    return null
  }

  let crossType: MacdCrossType | null = null
  if (isGoldenCross(previousBar, currentBar)) {
    crossType = 'golden'
  } else if (isDeadCross(previousBar, currentBar)) {
    crossType = 'dead'
  }

  if (!crossType) {
    return null
  }

  const recentSegments = getRecentThreeSegmentsBeforeIndex(baseSegments, currentBar.index)
  if (!recentSegments || !isValidThreeSegmentStructure(recentSegments, crossType)) {
    return null
  }

  const [segmentA, _, segmentC] = recentSegments
  if (!segmentA || !segmentC) {
    return null
  }

  const areaA = getSameDirectionMacdArea(bars, segmentA)
  const areaC = getSameDirectionMacdArea(bars, segmentC)
  const rangeA = getSegmentRange(segmentA)
  const rangeC = getSegmentRange(segmentC)

  if (crossType === 'dead') {
    if (!isUpMomentumExhausted(rangeA, rangeC, areaA, areaC)) {
      return null
    }

    return buildSignalFromCross(bars, currentBar.index, 'up', areaA, areaC)
  }

  if (!isDownMomentumExhausted(rangeA, rangeC, areaA, areaC)) {
    return null
  }

  return buildSignalFromCross(bars, currentBar.index, 'down', areaA, areaC)
}

export const createEmptyMomentumExhaustionBuildState = (): MomentumExhaustionBuildState => ({
  processedBarCount: 0,
  signals: [],
})

export const advanceMomentumExhaustionState = (
  buildState: MomentumExhaustionBuildState,
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
) => {
  let latestSignal: MomentumExhaustionSignal | null = null
  const startBarIndex = Math.max(1, buildState.processedBarCount)

  for (let barIndex = startBarIndex; barIndex < bars.length; barIndex += 1) {
    const signal = appendSignalForBar(bars, baseSegments, barIndex)
    if (!signal) {
      continue
    }

    buildState.signals.push(signal)
    latestSignal = signal
  }

  buildState.processedBarCount = bars.length
  return latestSignal
}

export const rebuildMomentumExhaustionState = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
) => {
  const buildState = createEmptyMomentumExhaustionBuildState()
  advanceMomentumExhaustionState(buildState, bars, baseSegments)
  return buildState
}

export const buildMomentumExhaustionSignals = (
  bars: FenxingBar[],
  baseSegments: BaseSegment[],
) => {
  return rebuildMomentumExhaustionState(bars, baseSegments).signals.map((signal) => ({
    ...signal,
    point: { ...signal.point },
  }))
}

export const getAllMomentumExhaustionSignals = (buildState: MomentumExhaustionBuildState) => {
  return buildState.signals.map((signal) => ({
    ...signal,
    point: { ...signal.point },
  }))
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
