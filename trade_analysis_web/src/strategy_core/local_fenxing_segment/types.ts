export type PineJsLike = {
  Std: {
    close: (context: unknown) => number
    ema: (source: unknown, length: number, context: unknown) => number
    high: (context: unknown) => number
    low: (context: unknown) => number
    open: (context: unknown) => number
    time: (context: unknown) => number
  }
}

export type PineContextLike = {
  new_var: (value?: number) => {
    get: (offset: number) => number
  }
  symbol?: {
    isLastBar?: boolean
  }
}

export type FenxingType = 'top' | 'bottom'

export type FenxingBar = {
  close: number
  ema20: number
  ema120?: number
  high: number
  index: number
  low: number
  open: number
  time: number
}

export type MergedFenxingBar = {
  firstBarCloseBelowEma20: boolean
  high: number
  highSourceIndex: number
  highSourceTime: number
  index: number
  low: number
  lowSourceIndex: number
  lowSourceTime: number
  sourceEndIndex: number
  sourceEndTime: number
  sourceStartIndex: number
  sourceStartTime: number
  time: number
}

export type FenxingPoint = {
  index: number
  price: number
  time: number
}

export type FenxingSignal = {
  index: number
  mergedBarIndex: number
  point: FenxingPoint
  sourceEndIndex: number
  sourceEndTime: number
  sourceStartIndex: number
  sourceStartTime: number
  type: FenxingType
}

export type FenxingBuildState = {
  confirmedFenxingSignals: FenxingSignal[]
  mergedBars: MergedFenxingBar[]
  processedBarCount: number
}

export type UpsertFenxingBarResult = {
  index: number
  type: 'append' | 'insert_historical' | 'replace_existing' | 'replace_last'
}

export type SegmentDirection = 'up' | 'down'

export type BaseSegment = {
  direction: SegmentDirection
  end: FenxingPoint
  endFenxingSignalIndex: number
  start: FenxingPoint
  startFenxingSignalIndex: number
}

export type BaseSegmentBuildState = {
  activeBaseSegment: BaseSegment | null
  historicalBaseSegments: BaseSegment[]
  processedFenxingSignalCount: number
  seedBottomFenxingSignal: FenxingSignal | null
  seedTopFenxingSignal: FenxingSignal | null
}

export type HigherLevelSegment = {
  direction: SegmentDirection
  end: FenxingPoint
  start: FenxingPoint
}

export type HigherLevelSegmentBuildState = {
  activeHigherLevelSegment: HigherLevelSegment | null
  historicalHigherLevelSegments: HigherLevelSegment[]
  lastCrossBarIndex: number | null
  lastCrossRelation: 'above' | 'below' | null
  processedBarCount: number
}
