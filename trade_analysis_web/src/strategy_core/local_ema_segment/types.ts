export type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (source: unknown, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    time: (context: unknown) => number
  }
}

export type PineContextLike = {
  new_var: (value?: number) => unknown
  symbol?: {
    isLastBar?: boolean
  }
}

export type SegmentDirection = 'up' | 'down'

export type EmaSegmentBar = {
  close: number
  ema: number
  ema120: number
  ema20: number
  high: number
  index: number
  low: number
  time: number
}

export type SegmentPoint = {
  index: number
  price: number
  time: number
}

export type BaseSegment = {
  direction: SegmentDirection
  end: SegmentPoint
  start: SegmentPoint
}

export type BaseSegmentBuildState = {
  activeBaseSegment: BaseSegment | null
  historicalBaseSegments: BaseSegment[]
  processedBarCount: number
  seedDirection: SegmentDirection | null
  seedExtreme: SegmentPoint | null
}

export type UpsertBarResult = {
  index: number
  type: 'append' | 'insert_historical' | 'replace_existing' | 'replace_last'
}

export type BaseSegmentMetrics = {
  barSpan: number
  high: SegmentPoint
  low: SegmentPoint
  priceRange: number
  strength: number
}

export type HigherLevelSegment = {
  direction: SegmentDirection
  end: SegmentPoint
  start: SegmentPoint
}

export type HigherLevelSegmentBuildState = {
  activeHigherLevelSegment: HigherLevelSegment | null
  currentCycleDirection: SegmentDirection | null
  currentCycleExtremePoint: SegmentPoint | null
  currentCycleStartIndex: number | null
  historicalHigherLevelSegments: HigherLevelSegment[]
  lastCrossRelation: 'above' | 'below' | null
  processedBarCount: number
}

export type MomentumExhaustionSignal = {
  direction: SegmentDirection
  point: SegmentPoint
}

export type BaseSegmentStudyState = {
  bars: EmaSegmentBar[]
  emittedInitialDrawableSegmentStartKey: string | null
  emittedInitialHigherLevelSegmentStartKey: string | null
  lastSettingsKey: string | null
  baseSegmentBuildState: BaseSegmentBuildState
  higherLevelSegmentBuildState: HigherLevelSegmentBuildState
}
