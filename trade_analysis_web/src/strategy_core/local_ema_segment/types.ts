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

export type EmaSegment = {
  direction: SegmentDirection
  end: SegmentPoint
  start: SegmentPoint
}

export type EmaSegmentBuildState = {
  activeSegment: EmaSegment | null
  historicalSegments: EmaSegment[]
  processedBarCount: number
  seedDirection: SegmentDirection | null
  seedExtreme: SegmentPoint | null
}

export type UpsertBarResult = {
  index: number
  type: 'append' | 'insert_historical' | 'replace_existing' | 'replace_last'
}

export type SegmentMetrics = {
  barSpan: number
  high: SegmentPoint
  low: SegmentPoint
  priceRange: number
  strength: number
}

export type MomentumExhaustionSignal = {
  direction: SegmentDirection
  point: SegmentPoint
}

export type EmaSegmentStudyState = {
  bars: EmaSegmentBar[]
  emittedInitialStartKey: string | null
  lastSettingsKey: string | null
  segmentBuildState: EmaSegmentBuildState
}
