import type { FutureChartKLineItem, FutureContract } from '@/api/modules'
import { buildBaseSegments } from '../base_segment_builder'
import type { BaseSegment, EmaSegmentBar, SegmentDirection } from '../types'

export const FIVE_MINUTE_INTERVAL_SECONDS = 5 * 60
export const THIRTY_MINUTE_INTERVAL_SECONDS = 30 * 60

export const DEFAULT_ANALYSIS_LIMIT = 600
export const DEFAULT_SEGMENT_EMA_LENGTH = 20
export const DEFAULT_SEGMENT_MIN_BARS = 4
export const DEFAULT_HIGHER_SEGMENT_EMA_LENGTH = 120
export const DEFAULT_HIGHER_SEGMENT_MIN_BARS = 24

export type OpenOpportunityType = 'five_minute_against_higher' | 'thirty_minute_against_higher'

export type SegmentAnalysisOptions = {
  emaLength?: number
  minSegmentBars?: number
}

export type OpenOpportunityAnalysisOptions = {
  base?: SegmentAnalysisOptions
  higher?: SegmentAnalysisOptions
}

export type TimeframeSegmentAnalysis = {
  barsCount: number
  baseSegmentCount: number
  higherSegmentCount: number
  latestBaseSegment: BaseSegment | null
  latestHigherSegment: BaseSegment | null
}

export type OpenOpportunityMatch = {
  barsCount: number
  baseSegment: BaseSegment
  baseSegmentCount: number
  higherSegment: BaseSegment
  higherSegmentCount: number
  intervalSeconds: number
  modeName: string
  type: OpenOpportunityType
}

export type OpenOpportunityAnalysisInput = {
  contract: FutureContract
  fiveMinuteKlines: FutureChartKLineItem[]
  thirtyMinuteKlines: FutureChartKLineItem[]
  options?: OpenOpportunityAnalysisOptions
}

export type OpenOpportunityResult = {
  contract: FutureContract
  fiveMinute: TimeframeSegmentAnalysis
  thirtyMinute: TimeframeSegmentAnalysis
  matches: OpenOpportunityMatch[]
}

const isFinitePrice = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

const calculateEmaSeries = (values: number[], length: number) => {
  const emaValues = Array<number>(values.length).fill(Number.NaN)

  if (length <= 0 || values.length < length) {
    return emaValues
  }

  let seedSum = 0
  for (let index = 0; index < length; index += 1) {
    seedSum += values[index] ?? 0
  }

  const multiplier = 2 / (length + 1)
  emaValues[length - 1] = seedSum / length

  for (let index = length; index < values.length; index += 1) {
    const close = values[index] ?? Number.NaN
    const previousEma = emaValues[index - 1] ?? Number.NaN
    emaValues[index] = (close - previousEma) * multiplier + previousEma
  }

  return emaValues
}

const normalizeKlines = (klines: FutureChartKLineItem[]) => {
  return [...klines]
    .filter((item) => (
      isFinitePrice(item.time)
      && isFinitePrice(item.open)
      && isFinitePrice(item.high)
      && isFinitePrice(item.low)
      && isFinitePrice(item.close)
    ))
    .sort((first, second) => first.time - second.time)
}

export const toEmaSegmentBars = (
  klines: FutureChartKLineItem[],
  emaLength = DEFAULT_SEGMENT_EMA_LENGTH,
): EmaSegmentBar[] => {
  const normalizedKlines = normalizeKlines(klines)
  const emaValues = calculateEmaSeries(
    normalizedKlines.map((item) => item.close),
    emaLength,
  )

  return normalizedKlines.map((item, index) => ({
    close: item.close,
    high: item.high,
    index,
    low: item.low,
    time: item.time,
    ema: emaValues[index] ?? Number.NaN,
  }))
}

const getLatestSegment = (segments: BaseSegment[]) => segments[segments.length - 1] ?? null

export const buildTimeframeSegmentAnalysis = (
  klines: FutureChartKLineItem[],
  options: OpenOpportunityAnalysisOptions = {},
): TimeframeSegmentAnalysis => {
  const baseEmaLength = Math.max(1, options.base?.emaLength ?? DEFAULT_SEGMENT_EMA_LENGTH)
  const baseMinSegmentBars = Math.max(1, options.base?.minSegmentBars ?? DEFAULT_SEGMENT_MIN_BARS)
  const higherEmaLength = Math.max(1, options.higher?.emaLength ?? DEFAULT_HIGHER_SEGMENT_EMA_LENGTH)
  const higherMinSegmentBars = Math.max(1, options.higher?.minSegmentBars ?? DEFAULT_HIGHER_SEGMENT_MIN_BARS)

  const baseBars = toEmaSegmentBars(klines, baseEmaLength)
  const higherBars = toEmaSegmentBars(klines, higherEmaLength)
  const baseSegments = buildBaseSegments(baseBars, baseEmaLength, baseMinSegmentBars)
  const higherSegments = buildBaseSegments(higherBars, higherEmaLength, higherMinSegmentBars)

  return {
    barsCount: baseBars.length,
    baseSegmentCount: baseSegments.length,
    higherSegmentCount: higherSegments.length,
    latestBaseSegment: getLatestSegment(baseSegments),
    latestHigherSegment: getLatestSegment(higherSegments),
  }
}

const isOppositeDirection = (
  firstDirection: SegmentDirection | undefined,
  secondDirection: SegmentDirection | undefined,
) => {
  return Boolean(firstDirection && secondDirection && firstDirection !== secondDirection)
}

const createMatch = (
  type: OpenOpportunityType,
  modeName: string,
  intervalSeconds: number,
  analysis: TimeframeSegmentAnalysis,
): OpenOpportunityMatch | null => {
  if (!analysis.latestBaseSegment || !analysis.latestHigherSegment) {
    return null
  }

  if (!isOppositeDirection(analysis.latestBaseSegment.direction, analysis.latestHigherSegment.direction)) {
    return null
  }

  return {
    barsCount: analysis.barsCount,
    baseSegment: analysis.latestBaseSegment,
    baseSegmentCount: analysis.baseSegmentCount,
    higherSegment: analysis.latestHigherSegment,
    higherSegmentCount: analysis.higherSegmentCount,
    intervalSeconds,
    modeName,
    type,
  }
}

export const analyzeOpenOpportunity = ({
  contract,
  fiveMinuteKlines,
  thirtyMinuteKlines,
  options,
}: OpenOpportunityAnalysisInput): OpenOpportunityResult => {
  const fiveMinute = buildTimeframeSegmentAnalysis(fiveMinuteKlines, options)
  const thirtyMinute = buildTimeframeSegmentAnalysis(thirtyMinuteKlines, options)
  const matches = [
    createMatch('five_minute_against_higher', '模式①', FIVE_MINUTE_INTERVAL_SECONDS, fiveMinute),
    createMatch('thirty_minute_against_higher', '模式②', THIRTY_MINUTE_INTERVAL_SECONDS, thirtyMinute),
  ].filter((item): item is OpenOpportunityMatch => item !== null)

  return {
    contract,
    fiveMinute,
    thirtyMinute,
    matches,
  }
}

export const hasOpenOpportunity = (result: OpenOpportunityResult) => result.matches.length > 0
